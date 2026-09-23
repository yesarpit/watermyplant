"""Call providers used by enquiry_pipeline.py.

Every provider implements:
  place_call(role, to_number, variables, metadata) -> call_id      (raises ProviderError)
  wait(call_id) -> outcome dict                                      (raises TimeoutError / ProviderError)

and returns the same provider-neutral outcome:
  {"call_id", "status", "minutes", "cost_inr", "summary", "data", "recording_url", "failure_reason"}
  status: connected | no_answer | busy | voicemail | failed | ndnc

SarvamProvider  -- primary. Sarvam Voice Agents (Indian voices; number = BYO connection, see FREE_PATHS.md).
RetellProvider  -- fallback, kept for comparison.
MockProvider    -- scripted outcomes, so the whole pipeline can be tested with no number and no spend.
"""
import itertools
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONNECTED, NO_ANSWER_S, BUSY_S, VOICEMAIL_S, FAILED, NDNC = \
    "connected", "no_answer", "busy", "voicemail", "failed", "ndnc"


class ProviderError(RuntimeError):
    """The provider refused or failed to place/fetch a call (network, 4xx/5xx, no credit...)."""


class NotConfigured(ProviderError):
    pass


def load_env():
    env = ROOT.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def outcome(call_id, status, minutes=0.0, cost_inr=None, summary=None, data=None,
            recording_url=None, failure_reason=None):
    return {"call_id": call_id, "status": status, "minutes": round(minutes or 0.0, 3), "cost_inr": cost_inr,
            "summary": summary, "data": data or {}, "recording_url": recording_url,
            "failure_reason": failure_reason}


def normalise_value(v):
    """Sarvam output variables are strings/enums; the pipeline wants bools and numbers."""
    if isinstance(v, str):
        s = v.strip()
        if s.lower() in ("yes", "true"):
            return True
        if s.lower() in ("no", "false"):
            return False
        if s.lower() in ("", "na", "n/a", "none", "null", "unknown"):
            return None
        try:
            return float(s.replace(",", "").replace("₹", "").replace("rs", "").strip())
        except ValueError:
            return s
    return v


# ---------------------------------------------------------------------------------------------
# Sarvam Voice Agents

class SarvamProvider:
    """Places calls with Sarvam's Instant Outbound API and polls the Analytics attempts API for the
    result (no public webhook needed). Agents are built in the Sarvam dashboard from sarvam/*.md;
    their IDs and the phone connection go in sarvam.json (see sarvam.example.json).
    Env: SARVAM_API_KEY (in the repo-root .env)."""
    name = "sarvam"
    BASE = "https://apps.sarvam.ai/api"
    STATUS = {"connected": CONNECTED, "no_answer": NO_ANSWER_S, "busy": BUSY_S, "failed": FAILED}

    def __init__(self, config_path=ROOT / "sarvam.json", poll_s=10, timeout_s=600, analysis_grace_s=120):
        load_env()
        self.key = os.environ.get("SARVAM_API_KEY")
        if not self.key:
            raise NotConfigured("SARVAM_API_KEY not set in ../.env")
        if not Path(config_path).exists():
            raise NotConfigured(f"{Path(config_path).name} missing -- copy sarvam.example.json and fill it in")
        self.cfg = json.loads(Path(config_path).read_text())
        missing = [k for k in ("org_id", "workspace_id", "connection_id", "agent_phone_number") if not self.cfg.get(k)]
        if missing:
            raise NotConfigured("sarvam.json is missing: " + ", ".join(missing) +
                                " (a phone number connection is needed for real calls)")
        self.poll_s, self.timeout_s, self.analysis_grace_s = poll_s, timeout_s, analysis_grace_s
        self._placed = {}   # attempt_id -> (role, placed_at)

    def _request(self, method, url, body=None):
        req = urllib.request.Request(url, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"X-API-Key": self.key, "Content-Type": "application/json"})
        where = f"Sarvam {method} {url.split('/api/')[1][:60]}"
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            with e:
                detail = e.read().decode(errors="replace")[:500]
            raise ProviderError(f"{where} -> HTTP {e.code}: {detail}") from None
        except OSError as e:       # URLError, timeouts, connection resets
            raise ProviderError(f"{where} -> {e}") from None
        try:
            body = json.loads(raw) if raw else {}
        except ValueError:
            raise ProviderError(f"{where} -> non-JSON response: {raw[:200]!r}") from None
        if not isinstance(body, dict):
            raise ProviderError(f"{where} -> unexpected response: {str(body)[:200]}")
        return body

    def place_call(self, role, to_number, variables, metadata):
        agent = self.cfg["agents"][role]
        c = self.cfg
        body = {
            "app_config": {
                "app_id": agent["app_id"], "app_version": int(agent["app_version"]),
                "connection_config": {"connection_id": c["connection_id"],
                                      "agent_phone_number": c["agent_phone_number"]},
                "agent_variables": {k: str(v) for k, v in variables.items()},
            },
            "user_config": {"user_phone_number": to_number},
        }
        if c.get("webhook_url"):
            body["webhook_config"] = {"url": c["webhook_url"], "metadata": metadata or {}}
        r = self._request("POST", f"{self.BASE}/outbounds/v1/orgs/{c['org_id']}/workspaces/"
                                  f"{c['workspace_id']}/outbounds", body)
        if not r.get("attempt_id"):
            raise ProviderError(f"Sarvam create call -> no attempt_id in response: {str(r)[:200]}")
        self._placed[r["attempt_id"]] = (role, datetime.now(timezone.utc))
        return r["attempt_id"]

    def _attempt(self, attempt_id):
        role, placed_at = self._placed[attempt_id]
        c = self.cfg
        q = urllib.parse.urlencode({
            "start_datetime": (placed_at - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_datetime": (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": 5,
            "filter_conditions": json.dumps([{"id": "1", "field": "attempt_id", "operator": "equals",
                                              "value": attempt_id}]),
        })
        r = self._request("GET", f"{self.BASE}/analytics/v1/{c['org_id']}/{c['workspace_id']}/"
                                 f"{c['agents'][role]['app_id']}/attempts?{q}")
        return next((i for i in r.get("items") or [] if isinstance(i, dict) and i.get("attempt_id") == attempt_id), None)

    def wait(self, attempt_id):
        deadline, final_seen = time.time() + self.timeout_s, None
        while time.time() < deadline:
            a = self._attempt(attempt_id)
            status = (a or {}).get("connectivity_status")
            if status and a.get("end_datetime") or status in ("no_answer", "busy", "failed"):
                final_seen = final_seen or time.time()
                variables = a.get("agent_variables") or {}
                # output variables are extracted by the LLM a little after the call ends
                if status != "connected" or variables.get("outcome_ready") or \
                        any(k in variables for k in ("still_needs_service", "available")) or \
                        time.time() - final_seen > self.analysis_grace_s:
                    return self._normalise(attempt_id, a)
            print(f"   ...{status or 'queued'}", flush=True)
            time.sleep(self.poll_s)
        raise TimeoutError(f"call {attempt_id} did not finish in {self.timeout_s}s")

    def _normalise(self, attempt_id, a):
        reason = a.get("failure_reason")
        status = self.STATUS.get(a.get("connectivity_status"), FAILED)
        if reason and "NDNC" in reason.upper():
            status = NDNC
        data = {k: normalise_value(v) for k, v in (a.get("agent_variables") or {}).items()}
        return outcome(attempt_id, status, minutes=(a.get("duration_in_seconds") or 0) / 60,
                       summary=data.pop("call_summary", None), data=data,
                       recording_url=a.get("audio_url"), failure_reason=reason)


# ---------------------------------------------------------------------------------------------
# Retell (fallback)

class RetellProvider:
    name = "retell"
    NOT_CONNECTED = {"dial_no_answer": NO_ANSWER_S, "dial_busy": BUSY_S, "voicemail_reached": VOICEMAIL_S,
                     "dial_failed": FAILED, "invalid_destination": FAILED,
                     "telephony_provider_permission_denied": FAILED, "error_no_audio_received": FAILED}

    def __init__(self, poll_s=10, timeout_s=600, analysis_grace_s=90, usd_inr=88.0):
        import retell  # imported lazily so tests never need the API key
        self.retell = retell
        self.agents = retell.load_agents()
        self.poll_s, self.timeout_s, self.analysis_grace_s, self.usd_inr = poll_s, timeout_s, analysis_grace_s, usd_inr
        self._from = None

    def from_number(self):
        if self._from is None:
            nums = self.retell.list_phone_numbers()
            if not nums:
                raise NotConfigured("No Retell phone number on the account (Retell needs a card to sell one).")
            self._from = nums[0]["phone_number"]
        return self._from

    def place_call(self, role, to_number, variables, metadata):
        try:
            call = self.retell.create_phone_call(self.from_number(), to_number,
                                                 self.agents[role]["agent_id"], variables, metadata)
        except RuntimeError as e:
            raise ProviderError(str(e)) from None
        return call["call_id"]

    def wait(self, call_id):
        deadline, ended_at = time.time() + self.timeout_s, None
        while time.time() < deadline:
            try:
                c = self.retell.get_call(call_id)
            except RuntimeError as e:
                raise ProviderError(str(e)) from None
            status = c.get("call_status")
            if status == "error":
                return outcome(call_id, FAILED, failure_reason=c.get("disconnection_reason"))
            if status == "ended":
                ended_at = ended_at or time.time()
                analysis = c.get("call_analysis") or {}
                if analysis.get("custom_analysis_data") or time.time() - ended_at > self.analysis_grace_s:
                    reason = c.get("disconnection_reason")
                    cents = (c.get("call_cost") or {}).get("combined_cost")
                    return outcome(call_id, self.NOT_CONNECTED.get(reason, CONNECTED),
                                   minutes=((c.get("end_timestamp") or 0) - (c.get("start_timestamp") or 0)) / 60000,
                                   cost_inr=round(cents / 100 * self.usd_inr, 2) if cents is not None else None,
                                   summary=analysis.get("call_summary"),
                                   data=analysis.get("custom_analysis_data") or {},
                                   recording_url=c.get("recording_url"),
                                   failure_reason=reason if reason in self.NOT_CONNECTED else None)
            print(f"   ...{status}", flush=True)
            time.sleep(self.poll_s)
        raise TimeoutError(f"call {call_id} did not finish in {self.timeout_s}s")


# ---------------------------------------------------------------------------------------------
# Mock

def answered(data, minutes=2.0, summary="(mock) call completed"):
    """A connected call whose post-call extraction returned `data`."""
    return {"kind": CONNECTED, "data": data, "minutes": minutes, "summary": summary}


NO_ANSWER = {"kind": NO_ANSWER_S}
BUSY = {"kind": BUSY_S}
VOICEMAIL = {"kind": VOICEMAIL_S, "minutes": 0.3}
DIAL_FAILED = {"kind": FAILED, "reason": "provider: invalid number"}
NDNC_BLOCKED = {"kind": NDNC, "reason": "exotel: Phone number is registered under TRAI NDNC"}
PLACE_ERROR = {"kind": "place_error"}      # create-call API fails (5xx, out of credit, ...)
TIMEOUT = {"kind": "timeout"}              # call never reaches a final state


class MockProvider:
    """Scripted provider. `script` maps the dialled number (E.164) to a list of outcomes, one per
    attempt; the last one repeats. Numbers not in the script get `default` (no answer).
    Cost is charged per connected minute at `inr_per_min`."""
    name = "mock"

    def __init__(self, script=None, default=NO_ANSWER, inr_per_min=3.0):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.default, self.inr_per_min = default, inr_per_min
        self.attempts = {}          # number -> attempts so far
        self.placed = []            # (role, to_number, variables, metadata)
        self._pending = {}
        self._ids = itertools.count(1)

    def _next(self, number):
        n = self.attempts.get(number, 0)
        self.attempts[number] = n + 1
        seq = self.script.get(number) or [self.default]
        return seq[min(n, len(seq) - 1)]

    def place_call(self, role, to_number, variables, metadata):
        o = self._next(to_number)
        if o["kind"] == "place_error":
            raise ProviderError("mock: create call -> 500")
        self.placed.append((role, to_number, dict(variables), dict(metadata or {})))
        call_id = f"mock_{next(self._ids)}"
        self._pending[call_id] = o
        return call_id

    def wait(self, call_id):
        o = self._pending.pop(call_id)
        if o["kind"] == "timeout":
            raise TimeoutError(f"call {call_id} did not finish (mock)")
        minutes = o.get("minutes", 0.0)
        return outcome(call_id, o["kind"], minutes=minutes, cost_inr=round(minutes * self.inr_per_min, 2),
                       summary=o.get("summary"), data=dict(o.get("data") or {}), failure_reason=o.get("reason"))


def mock_from_file(path):
    """Build a MockProvider from a JSON scenario: {"default": "no_answer", "script": {"+91..": [outcome, ...]}}
    where an outcome is "no_answer" | "busy" | "voicemail" | "failed" | "ndnc" | "place_error" | "timeout"
    or {"connected": {...extracted data...}, "minutes": 2}."""
    named = {"no_answer": NO_ANSWER, "busy": BUSY, "voicemail": VOICEMAIL, "failed": DIAL_FAILED,
             "ndnc": NDNC_BLOCKED, "place_error": PLACE_ERROR, "timeout": TIMEOUT}

    def parse(o):
        if isinstance(o, str):
            return named[o]
        return answered(o["connected"], minutes=o.get("minutes", 2.0), summary=o.get("summary", "(mock)"))

    spec = json.loads(Path(path).read_text())
    return MockProvider({num: [parse(o) for o in seq] for num, seq in spec.get("script", {}).items()},
                        default=parse(spec.get("default", "no_answer")))
