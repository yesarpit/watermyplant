#!/usr/bin/env python3
"""Local enquiry intake endpoint (stdlib only, no network beyond localhost).

  ./intake.py --port 8765 --queue queue/

  POST /enquiries  JSON body with the enquiry_pipeline keys (name, phone, locality, pincode,
                   start_date, end_date, notes, consent_source, optional id, lat, lng)
                   -> 202 {"id", "status": "queued"}   validated, written to <queue>/<id>.json
                   -> 400 {"errors": [...]}            nothing is written, nobody is called
                   -> 409 {"errors": [...]}            that id is already queued
  GET  /health     -> 200 {"ok": true}

Queued files are what `enquiry_pipeline.py --file <queue>/<id>.json` takes. Binds to 127.0.0.1 by
default; put a real form backend or a WhatsApp webhook in front of it before exposing it anywhere.
"""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import enquiry_pipeline as EP

FIELDS = {"id", "name", "phone", "locality", "pincode", "start_date", "end_date", "notes",
          "consent_source", "lat", "lng"}
MAX_BODY = 16 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "wmp-intake/1"

    def reply(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            return self.reply(200, {"ok": True})
        self.reply(404, {"errors": ["not found"]})

    def do_POST(self):
        if self.path != "/enquiries":
            return self.reply(404, {"errors": ["not found"]})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if not 0 < n <= MAX_BODY:
            return self.reply(400, {"errors": [f"body must be 1..{MAX_BODY} bytes of JSON"]})
        try:
            body = json.loads(self.rfile.read(n))
        except ValueError:
            return self.reply(400, {"errors": ["body is not valid JSON"]})
        if not isinstance(body, dict):
            return self.reply(400, {"errors": ["body must be a JSON object"]})
        unknown = sorted(set(body) - FIELDS)
        if unknown:
            return self.reply(400, {"errors": [f"unknown fields: {unknown}"]})
        clean, errors = EP.validate_enquiry(body, self.server.today)
        if errors:
            return self.reply(400, {"errors": errors})
        path = self.server.queue_dir / f"{clean['id']}.json"
        with self.server.lock:
            if path.exists():
                return self.reply(409, {"errors": [f"enquiry {clean['id']} is already queued"]})
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(clean, indent=2) + "\n")
            tmp.replace(path)
        self.server.on_queued(clean)
        self.reply(202, {"id": clean["id"], "status": "queued"})

    def log_message(self, fmt, *args):
        if not self.server.quiet:
            super().log_message(fmt, *args)


class IntakeServer(ThreadingHTTPServer):
    def __init__(self, queue_dir, host="127.0.0.1", port=8765, today=None, on_queued=lambda enq: None,
                 quiet=False):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.today, self.on_queued, self.quiet = today, on_queued, quiet
        self.lock = threading.Lock()
        super().__init__((host, port), Handler)

    @property
    def url(self):
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=8765)
    a.add_argument("--queue", default=str(EP.ROOT / "queue"))
    p = a.parse_args()
    srv = IntakeServer(p.queue, p.host, p.port,
                       on_queued=lambda e: print(f"queued {e['id']} -> ./enquiry_pipeline.py --file "
                                                 f"{Path(p.queue) / (e['id'] + '.json')}", flush=True))
    print(f"intake listening on {srv.url}/enquiries (queue: {p.queue})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
