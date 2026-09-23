"""Mocked contract and error tests for SarvamProvider. No network, no account, no spend.

The contract pinned here is Sarvam's published API reference (checked 2026-09-23):
  POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds
       body {app_config: {app_id, app_version:int, connection_config: {connection_id, agent_phone_number},
             agent_variables}, user_config: {user_phone_number}, webhook_config?: {url, metadata}}
       200 -> {attempt_id}; 422 -> {detail: [{loc, msg, type}]}
  GET  https://apps.sarvam.ai/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/attempts
       ?start_datetime&end_datetime (required, UTC ISO8601)&limit&filter_conditions (JSON array)
       200 -> {items: [{attempt_id, connectivity_status, failure_reason, duration_in_seconds,
                        end_datetime, audio_url, agent_variables, ...}], total, limit, offset}
  Auth: X-API-Key header.
NOT confirmed by the docs, so only assumed here, and to be checked on the first live test call:
the connectivity_status values ("connected", "no_answer", "busy", "failed"), whether attempt_id
is an accepted filter field, and the NDNC wording of failure_reason.

    cd nursery-calling-bot && python3 -m unittest tests.test_sarvam_contract -v
"""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import enquiry_pipeline as EP  # noqa: E402
import providers as P  # noqa: E402

CFG = {"org_id": "org_x", "workspace_id": "ws_y", "connection_id": "conn_z", "agent_phone_number": "+918000000000",
       "webhook_url": "", "agents": {"customer": {"app_id": "app_cust", "app_version": "3"},
                                     "gardener": {"app_id": "app_gard", "app_version": 1}}}
BASE = "https://apps.sarvam.ai/api"
CREATE = f"{BASE}/outbounds/v1/orgs/org_x/workspaces/ws_y/outbounds"


class FakeResp:
    def __init__(self, body, status=200):
        self.raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.status = status

    def read(self):
        return self.raw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code, body):
    """A factory, so every request gets a fresh (unread) error, as with a real server."""
    return lambda: urllib.error.HTTPError("https://apps.sarvam.ai/x", code, "err", {},
                                          io.BytesIO(json.dumps(body).encode()))


class FakeTransport:
    """Stands in for urllib.request.urlopen. `routes` is a list of (method, url_prefix, [responses]);
    a response is a dict/bytes (200 body), an exception instance to raise, or a factory returning
    either. The last one repeats."""
    def __init__(self, routes):
        self.routes = [(m, u, list(rs)) for m, u, rs in routes]
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        for method, prefix, responses in self.routes:
            if req.get_method() == method and req.full_url.startswith(prefix):
                r = responses.pop(0) if len(responses) > 1 else responses[0]
                r = r() if callable(r) else r
                if isinstance(r, BaseException):
                    raise r
                return FakeResp(r)
        raise AssertionError(f"unexpected request {req.get_method()} {req.full_url}")


class FakeTime:
    """time.time()/time.sleep() for SarvamProvider.wait: sleeping advances the clock."""
    def __init__(self):
        self.now = 1_000_000.0

    def time(self):
        return self.now

    def sleep(self, s):
        self.now += s


def attempt(attempt_id="att_1", status="connected", end=True, variables=None, **extra):
    item = {"attempt_id": attempt_id, "connectivity_status": status, "failure_reason": None,
            "duration_in_seconds": 150.0, "end_datetime": "2026-09-23T06:00:00Z" if end else None,
            "audio_url": "https://example.invalid/a.mp3", "agent_variables": variables}
    item.update(extra)
    return {"items": [item], "total": 1, "limit": 5, "offset": 0}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg_path = self.tmp / "sarvam.json"
        self.cfg_path.write_text(json.dumps(CFG))
        env = mock.patch.dict(os.environ, {"SARVAM_API_KEY": "test-key-not-real"})
        env.start()
        self.addCleanup(env.stop)
        self.clock = FakeTime()
        t = mock.patch.object(P, "time", self.clock)
        t.start()
        self.addCleanup(t.stop)

    def provider(self, routes, cfg=None, **kw):
        if cfg is not None:
            self.cfg_path.write_text(json.dumps(cfg))
        self.transport = FakeTransport(routes)
        u = mock.patch.object(P.urllib.request, "urlopen", self.transport)
        u.start()
        self.addCleanup(u.stop)
        kw.setdefault("poll_s", 10)
        kw.setdefault("timeout_s", 600)
        kw.setdefault("analysis_grace_s", 120)
        return P.SarvamProvider(config_path=self.cfg_path, **kw)


class RequestContract(Base):
    def test_create_call_request_shape(self):
        prov = self.provider([("POST", CREATE, [{"attempt_id": "att_1"}])])
        att = prov.place_call("customer", "+919000000099", {"customer_name": "Demo", "budget": 150},
                              {"enquiry_id": "e1"})
        self.assertEqual(att, "att_1")
        req = self.transport.requests[0]
        self.assertEqual((req.get_method(), req.full_url), ("POST", CREATE))
        self.assertEqual(req.get_header("X-api-key"), "test-key-not-real")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        body = json.loads(req.data)
        self.assertEqual(body, {
            "app_config": {"app_id": "app_cust", "app_version": 3,
                           "connection_config": {"connection_id": "conn_z", "agent_phone_number": "+918000000000"},
                           "agent_variables": {"customer_name": "Demo", "budget": "150"}},
            "user_config": {"user_phone_number": "+919000000099"}})
        self.assertIsInstance(body["app_config"]["app_version"], int)

    def test_webhook_config_only_when_configured(self):
        prov = self.provider([("POST", CREATE, [{"attempt_id": "att_1"}])],
                             cfg={**CFG, "webhook_url": "https://hooks.example.invalid/sarvam"})
        prov.place_call("gardener", "+919000000001", {}, {"enquiry_id": "e1", "role": "gardener"})
        body = json.loads(self.transport.requests[0].data)
        self.assertEqual(body["app_config"]["app_id"], "app_gard")
        self.assertEqual(body["webhook_config"], {"url": "https://hooks.example.invalid/sarvam",
                                                  "metadata": {"enquiry_id": "e1", "role": "gardener"}})

    def test_attempts_query_shape(self):
        prov = self.provider([("POST", CREATE, [{"attempt_id": "att_1"}]),
                              ("GET", f"{BASE}/analytics/v1/org_x/ws_y/app_cust/attempts?",
                               [attempt(variables={"still_needs_service": "yes"})])])
        prov.wait(prov.place_call("customer", "+919000000099", {}, {}))
        req = self.transport.requests[1]
        self.assertEqual(req.get_header("X-api-key"), "test-key-not-real")
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
        for k in ("start_datetime", "end_datetime"):
            datetime.strptime(q[k][0], "%Y-%m-%dT%H:%M:%SZ")      # required, UTC ISO8601
        self.assertLess(q["start_datetime"][0], q["end_datetime"][0])
        self.assertEqual(json.loads(q["filter_conditions"][0]),
                         [{"id": "1", "field": "attempt_id", "operator": "equals", "value": "att_1"}])


class ResponseContract(Base):
    def run_call(self, *polls, **kw):
        prov = self.provider([("POST", CREATE, [{"attempt_id": "att_1"}]),
                              ("GET", f"{BASE}/analytics/", list(polls))], **kw)
        return prov.wait(prov.place_call("customer", "+919000000099", {}, {}))

    def test_connected_call_is_normalised(self):
        o = self.run_call(attempt(variables={
            "still_needs_service": "Yes", "budget_per_visit_inr": "₹1,200", "do_not_call": "no",
            "landmark": "BDA park", "plant_count": "N/A", "call_summary": "Confirmed dates"}))
        self.assertEqual(o["status"], P.CONNECTED)
        self.assertEqual(o["minutes"], 2.5)
        self.assertEqual(o["summary"], "Confirmed dates")
        self.assertEqual(o["recording_url"], "https://example.invalid/a.mp3")
        self.assertEqual(o["data"], {"still_needs_service": True, "budget_per_visit_inr": 1200.0,
                                     "do_not_call": False, "landmark": "BDA park", "plant_count": None})
        self.assertIsNone(o["cost_inr"])          # pipeline estimates it from minutes

    def test_status_mapping(self):
        for sarvam, ours in (("no_answer", P.NO_ANSWER_S), ("busy", P.BUSY_S), ("failed", P.FAILED),
                             ("something_new", P.FAILED)):
            with self.subTest(sarvam=sarvam):
                self.setUp()
                o = self.run_call(attempt(status=sarvam, variables=None, duration_in_seconds=None))
                self.assertEqual((o["status"], o["minutes"], o["data"]), (ours, 0.0, {}))

    def test_ndnc_failure_reason(self):
        o = self.run_call(attempt(status="failed", failure_reason="Number is registered under TRAI ndnc",
                                  duration_in_seconds=0))
        self.assertEqual(o["status"], P.NDNC)
        self.assertIn("ndnc", o["failure_reason"])

    def test_keeps_polling_until_the_attempt_is_final(self):
        o = self.run_call({"items": [], "total": 0, "limit": 5, "offset": 0},       # not indexed yet
                          attempt(status=None, end=False),                           # queued
                          attempt(status="connected", end=False),                    # in progress
                          attempt(variables={"available": "yes"}))
        self.assertEqual(o["status"], P.CONNECTED)
        self.assertEqual(len(self.transport.requests), 5)

    def test_waits_for_extraction_then_gives_up_after_grace(self):
        o = self.run_call(attempt(variables={}), analysis_grace_s=30, poll_s=10)
        self.assertEqual((o["status"], o["data"]), (P.CONNECTED, {}))
        polls = len(self.transport.requests) - 1
        self.assertGreaterEqual(polls, 4)          # polled through the 30 s grace window
        self.assertLessEqual(polls, 6)

    def test_ignores_other_attempts_in_the_page(self):
        other = attempt("att_other", variables={"available": "yes"})["items"][0]
        mine = attempt("att_1", status="busy")["items"][0]
        o = self.run_call({"items": [other, mine], "total": 2, "limit": 5, "offset": 0})
        self.assertEqual(o["status"], P.BUSY_S)

    def test_timeout(self):
        with self.assertRaises(TimeoutError):
            self.run_call(attempt(status=None, end=False), timeout_s=60, poll_s=10)


class Errors(Base):
    def place(self, *responses):
        prov = self.provider([("POST", CREATE, list(responses))])
        return prov.place_call("customer", "+919000000099", {}, {})

    def test_http_errors_become_provider_errors_with_detail(self):
        for code, body in ((401, {"detail": "invalid api key"}), (402, {"detail": "insufficient wallet balance"}),
                           (422, {"detail": [{"loc": ["body", "user_config"], "msg": "field required",
                                              "type": "missing"}]}),
                           (429, {"detail": "rate limited"}), (500, {"detail": "internal"})):
            with self.subTest(code=code):
                self.setUp()
                with self.assertRaises(P.ProviderError) as cm:
                    self.place(http_error(code, body))
                self.assertIn(f"HTTP {code}", str(cm.exception))
                self.assertNotIn("test-key-not-real", str(cm.exception))

    def test_network_errors_become_provider_errors(self):
        for exc in (urllib.error.URLError("nodename nor servname provided"), TimeoutError("timed out"),
                    ConnectionResetError("reset by peer")):
            with self.subTest(exc=type(exc).__name__):
                self.setUp()
                with self.assertRaises(P.ProviderError):
                    self.place(exc)

    def test_malformed_responses_become_provider_errors(self):
        for body in (b"<html>502 Bad Gateway</html>", b"[]", {"id": "no attempt id here"}, {"attempt_id": ""}):
            with self.subTest(body=body):
                self.setUp()
                with self.assertRaises(P.ProviderError):
                    self.place(body)

    def test_error_while_polling(self):
        prov = self.provider([("POST", CREATE, [{"attempt_id": "att_1"}]),
                              ("GET", f"{BASE}/analytics/", [http_error(503, {"detail": "unavailable"})])])
        with self.assertRaises(P.ProviderError):
            prov.wait(prov.place_call("customer", "+919000000099", {}, {}))

    def test_not_configured(self):
        with mock.patch.dict(os.environ, {"SARVAM_API_KEY": ""}):
            with self.assertRaises(P.NotConfigured):
                P.SarvamProvider(config_path=self.cfg_path)
        with self.assertRaises(P.NotConfigured):
            P.SarvamProvider(config_path=self.tmp / "missing.json")
        self.cfg_path.write_text(json.dumps({**CFG, "connection_id": "", "agent_phone_number": ""}))
        with self.assertRaises(P.NotConfigured) as cm:
            P.SarvamProvider(config_path=self.cfg_path)
        self.assertIn("connection_id", str(cm.exception))


class PipelineWithSarvam(Base):
    """The real pipeline driving SarvamProvider over the fake transport: provider errors pause the run
    (resumable) instead of crashing it, and a successful pass produces a handoff."""
    CUSTOMER_VARS = {"still_needs_service": "yes", "start_date": "2026-10-02", "end_date": "2026-10-06",
                     "area": "Jagajyothi Layout", "visit_frequency": "alternate_days",
                     "budget_per_visit_inr": "150", "do_not_call": "no"}

    def pipeline(self, prov):
        roster = self.tmp / "roster.csv"
        roster.write_text("name,phone,pincode,locality,lat,lng,status,source_id,notes\n"
                          "Near Nursery,+919000000001,560056,,,,active,,\n")
        return EP.Pipeline(prov, mode="live", runs_dir=self.tmp / "runs", gardeners_path=roster,
                           dnc_path=self.tmp / "dnc.txt", want=1, sleep=lambda s: None,
                           clock=lambda: datetime(2026, 9, 23, 11, 0, tzinfo=EP.IST),
                           today=datetime(2026, 9, 23).date(), quiet=True)

    def enquiry(self):
        return {"id": "s-1", "name": "Demo", "phone": "9000000099", "locality": "Jagajyothi Layout",
                "pincode": "560056", "start_date": "2026-10-02", "end_date": "2026-10-06",
                "consent_source": "website_form"}

    def test_outage_pauses_then_resume_completes(self):
        prov = self.provider([("POST", CREATE, [http_error(503, {"detail": "down"})])])
        log = self.pipeline(prov).start(self.enquiry())
        self.assertEqual((log["status"], log["result"]), ("paused", "provider_error"))
        self.assertEqual(len(self.transport.requests), 3)       # place_retries

        prov = self.provider([("POST", CREATE, [{"attempt_id": "c1"}, {"attempt_id": "g1"}]),
                              ("GET", f"{BASE}/analytics/v1/org_x/ws_y/app_cust/",
                               [attempt("c1", variables=self.CUSTOMER_VARS)]),
                              ("GET", f"{BASE}/analytics/v1/org_x/ws_y/app_gard/",
                               [attempt("g1", variables={"available": "yes", "can_start_on_date": "yes",
                                                         "price_per_visit_inr": "100", "do_not_call": "no"})])])
        log = self.pipeline(prov).resume("s-1")
        self.assertEqual((log["status"], log["result"]), ("finished", "1_gardeners_available"))
        self.assertEqual(log["offers"][0]["customer_price_per_visit"], 130)
        self.assertEqual(log["metrics"]["calls_connected"], 2)

    def test_malformed_poll_marks_status_unknown_and_pauses(self):
        prov = self.provider([("POST", CREATE, [{"attempt_id": "c1"}]),
                              ("GET", f"{BASE}/analytics/", [b"not json"])])
        log = self.pipeline(prov).start(self.enquiry())
        self.assertEqual((log["status"], log["result"]), ("paused", "customer_call_status_unknown"))


if __name__ == "__main__":
    unittest.main()
