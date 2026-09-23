"""Minimal Retell AI API client (stdlib only). Reads API_KEY_RETELL from the repo-root .env."""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.retellai.com"
ROOT = Path(__file__).resolve().parent
AGENTS_FILE = ROOT / "agents.json"


def _load_env():
    env = ROOT.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def _key():
    _load_env()
    key = os.environ.get("API_KEY_RETELL")
    if not key:
        raise SystemExit("API_KEY_RETELL not set (expected in ../.env)")
    return key


def request(method, path, body=None):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Retell {method} {path} -> {e.code}: {e.read().decode()[:500]}") from None


def load_agents():
    if not AGENTS_FILE.exists():
        raise SystemExit("agents.json missing -- run ./setup_agents.py first")
    return json.loads(AGENTS_FILE.read_text())


def create_phone_call(from_number, to_number, agent_id, dynamic_vars, metadata=None):
    return request("POST", "/v2/create-phone-call", {
        "from_number": from_number,
        "to_number": to_number,
        "override_agent_id": agent_id,
        "retell_llm_dynamic_variables": {k: str(v) for k, v in dynamic_vars.items()},
        "metadata": metadata or {},
    })


def get_call(call_id):
    return request("GET", f"/v2/get-call/{call_id}")


def list_phone_numbers():
    return request("GET", "/list-phone-numbers")
