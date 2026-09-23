#!/usr/bin/env python3
"""Enquiry intake server: website form + WhatsApp webhook + JSON API -> queue -> auto-run the pipeline.
Stdlib only.

  ./intake.py                               # 127.0.0.1:8765, queue/, auto-runs with the mock provider
  ./intake.py --auto-run off                # queue only; run enquiry_pipeline.py --file queue/<id>.json by hand
  ./intake.py --auto-run sarvam             # real calls, TEST mode only: every call rings TEST_NUMBER

  GET  /enquire             HTML enquiry form (call-consent checkbox + honeypot)
  POST /enquire             form-encoded -> 303 /enquire/thanks | 400 form with the errors | 429
  POST /enquiries           JSON with the enquiry_pipeline keys (name, phone, locality, pincode, start_date,
                            end_date, notes, consent_source, optional id, lat, lng)
                            -> 202 {"id", "status": "queued"} | 400/409/429 {"errors": [...]}
  GET  /webhooks/whatsapp   Meta verify handshake: echoes hub.challenge iff hub.verify_token matches
  POST /webhooks/whatsapp   WhatsApp Cloud API messages; needs a valid X-Hub-Signature-256 (403 otherwise,
                            503 if no app secret is configured). See whatsapp_inbound.py.
  GET  /health              -> 200 {"ok": true}

Env (or ../.env): WMP_WA_APP_SECRET, WMP_WA_VERIFY_TOKEN.

Every accepted enquiry is written to <queue>/<id>.json and handed to one background worker that runs it
through Pipeline (unless --auto-run off). The server never calls in --live mode. Guards against someone
typing a stranger's number: one enquiry per phone per 24 h, at most --max-runs-per-day auto-runs (the
rest stay queued and are picked up on the next start). Binds to 127.0.0.1; exposing it publicly
(hosting or a tunnel) is a founder decision.
"""
import argparse
import html
import json
import os
import queue
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import enquiry_pipeline as EP
import providers as P
import whatsapp_inbound as WI

FIELDS = {"id", "name", "phone", "locality", "pincode", "start_date", "end_date", "notes",
          "consent_source", "lat", "lng"}
FORM_FIELDS = ("name", "phone", "locality", "pincode", "start_date", "end_date", "notes")
HONEYPOT = "website"
MAX_BODY = 16 * 1024
MAX_WA_BODY = 256 * 1024

FORM_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Plant watering enquiry</title>
<style>body{{font-family:system-ui,sans-serif;max-width:32rem;margin:2rem auto;padding:0 16px}}
label{{display:block;margin-top:.8rem}}input,textarea{{width:100%;padding:.4rem;box-sizing:border-box}}
.hp{{position:absolute;left:-9999px}}.err{{color:#b00020}}.consent input{{width:auto}}</style></head><body>
<h1>Going away? We'll water your plants.</h1>{errors}
<form method="post" action="/enquire">
<label>Your name<input name="name" required maxlength="60" value="{name}"></label>
<label>Mobile number<input name="phone" required inputmode="tel" value="{phone}"></label>
<label>Locality<input name="locality" required value="{locality}" placeholder="e.g. Jagajyothi Layout"></label>
<label>Pincode<input name="pincode" required pattern="[0-9]{{6}}" value="{pincode}"></label>
<label>Away from<input name="start_date" type="date" required value="{start_date}"></label>
<label>Back on<input name="end_date" type="date" required value="{end_date}"></label>
<label>Plants (how many, balcony/garden...)<textarea name="notes" maxlength="500">{notes}</textarea></label>
<label class="hp" aria-hidden="true">Website<input name="website" tabindex="-1" autocomplete="off"></label>
<label class="consent"><input type="checkbox" name="consent_call" value="yes" required>
 I agree to receive a phone call on this number about this enquiry. I can say STOP any time.</label>
<p><button type="submit">Find me a gardener</button></p></form></body></html>"""
THANKS_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Thanks</title></head>
<body style="font-family:system-ui,sans-serif;max-width:32rem;margin:2rem auto;padding:0 16px">
<h1>Thanks!</h1><p>We'll call you shortly to confirm the details, then line up a gardener near you.</p></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "wmp-intake/2"

    def send(self, code, raw, ctype, headers=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def reply(self, code, body):
        self.send(code, json.dumps(body).encode(), "application/json")

    def page(self, code, text, headers=()):
        self.send(code, text.encode(), "text/html; charset=utf-8", headers)

    def form_page(self, code, values=None, errors=()):
        v = {k: html.escape(str((values or {}).get(k) or "")) for k in FORM_FIELDS}
        err = ('<ul class="err">' + "".join(f"<li>{html.escape(e)}</li>" for e in errors) + "</ul>") if errors else ""
        self.page(code, FORM_PAGE.format(errors=err, **v))

    def body(self, limit):
        """The raw request body, or None after replying 400."""
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if not 0 < n <= limit:
            self.reply(400, {"errors": [f"body must be 1..{limit} bytes"]})
            return None
        return self.rfile.read(n)

    # -- routes ---------------------------------------------------------------------------------
    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        if url.path == "/health":
            return self.reply(200, {"ok": True})
        if url.path == "/enquire":
            return self.form_page(200)
        if url.path == "/enquire/thanks":
            return self.page(200, THANKS_PAGE)
        if url.path == "/webhooks/whatsapp":
            q = urllib.parse.parse_qs(url.query)
            token = self.server.wa_verify_token
            if token and q.get("hub.mode") == ["subscribe"] and q.get("hub.verify_token") == [token] \
                    and q.get("hub.challenge"):
                return self.send(200, q["hub.challenge"][0].encode(), "text/plain")
            return self.reply(403, {"errors": ["verification failed"]})
        self.reply(404, {"errors": ["not found"]})

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/enquiries":
            return self.post_json()
        if path == "/enquire":
            return self.post_form()
        if path == "/webhooks/whatsapp":
            return self.post_whatsapp()
        self.reply(404, {"errors": ["not found"]})

    def post_json(self):
        raw = self.body(MAX_BODY)
        if raw is None:
            return
        try:
            body = json.loads(raw)
        except ValueError:
            return self.reply(400, {"errors": ["body is not valid JSON"]})
        if not isinstance(body, dict):
            return self.reply(400, {"errors": ["body must be a JSON object"]})
        unknown = sorted(set(body) - FIELDS)
        if unknown:
            return self.reply(400, {"errors": [f"unknown fields: {unknown}"]})
        self.reply(*self.server.accept(body))

    def post_form(self):
        if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/x-www-form-urlencoded":
            return self.reply(415, {"errors": ["expected application/x-www-form-urlencoded"]})
        raw = self.body(MAX_BODY)
        if raw is None:
            return
        try:
            q = urllib.parse.parse_qs(raw.decode(), keep_blank_values=True, max_num_fields=20)
        except (UnicodeDecodeError, ValueError):
            return self.form_page(400, errors=["could not read the form"])
        v = {k: q.get(k, [""])[0].strip() for k in (*FORM_FIELDS, HONEYPOT, "consent_call")}
        if v[HONEYPOT]:                         # a bot filled the hidden field: look successful, queue nothing
            self.server.say("form: honeypot filled, dropped")
            return self.page(303, "", [("Location", "/enquire/thanks")])
        if v["consent_call"] != "yes":
            return self.form_page(400, v, ["Please tick the box agreeing to a phone call - we need to call "
                                           "you to confirm the details."])
        code, body = self.server.accept({**{k: v[k] for k in FORM_FIELDS}, "consent_source": "website_form"})
        if code == 202:
            return self.page(303, "", [("Location", "/enquire/thanks")])
        self.form_page(400 if code != 429 else 429, v, body["errors"])

    def post_whatsapp(self):
        secret = self.server.wa_app_secret
        if not secret:
            return self.reply(503, {"errors": ["WhatsApp webhook not configured (WMP_WA_APP_SECRET)"]})
        raw = self.body(MAX_WA_BODY)
        if raw is None:
            return
        if not WI.signature_ok(secret, raw, self.headers.get("X-Hub-Signature-256")):
            return self.reply(403, {"errors": ["bad signature"]})
        try:
            payload = json.loads(raw)
        except ValueError:
            return self.reply(400, {"errors": ["body is not valid JSON"]})
        if not isinstance(payload, dict):
            return self.reply(400, {"errors": ["body must be a JSON object"]})
        handled = [self.server.whatsapp_message(*m) for m in WI.text_messages(payload)]
        self.reply(200, {"handled": handled})      # always 200 for a signed payload, or Meta keeps retrying

    def log_message(self, fmt, *args):
        if not self.server.quiet:
            super().log_message(fmt, *args)


class AutoRunner:
    """One background worker: enquiries are run one at a time, in the order they were accepted."""
    def __init__(self, run, max_per_day, today, say):
        self.run, self.max_per_day, self.today, self.say = run, max_per_day, today, say
        self.q, self.results, self.runs_on = queue.Queue(), {}, {}
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def submit(self, enq):
        self.q.put(enq)

    def wait(self):
        self.q.join()

    def stop(self):
        self.q.put(None)

    def _loop(self):
        while True:
            enq = self.q.get()
            try:
                if enq is None:
                    return
                day = self.today()
                if self.runs_on.get(day, 0) >= self.max_per_day:
                    self.results[enq["id"]] = "deferred: daily auto-run cap reached (stays queued)"
                    self.say(f"auto-run {enq['id']}: deferred, {self.max_per_day} runs already today")
                    continue
                self.runs_on[day] = self.runs_on.get(day, 0) + 1
                try:
                    log = self.run(enq)
                    self.results[enq["id"]] = f"{log['status']}: {log['result']}"
                except Exception as e:          # noqa: BLE001 -- a bad run must not kill the worker
                    self.results[enq["id"]] = f"error: {type(e).__name__}: {e}"
                self.say(f"auto-run {enq['id']}: {self.results[enq['id']]}")
            finally:
                self.q.task_done()


def pipeline_runner(provider, *, runs_dir, gardeners_path, dnc_path, today=None, quiet=True):
    """enquiry -> Pipeline(...).start(enquiry), always TEST mode. provider: mock | sarvam | retell."""
    def run(enq):
        if provider == "mock":
            prov, delay, sleep = EP.default_mock(gardeners_path, enq), 0, lambda s: None
        else:
            prov, delay, sleep = (P.SarvamProvider() if provider == "sarvam" else P.RetellProvider()), 300, time.sleep
        return EP.Pipeline(prov, mode="test", runs_dir=runs_dir, gardeners_path=gardeners_path, dnc_path=dnc_path,
                           retry_delay_s=delay, sleep=sleep, today=today, quiet=quiet).start(enq)
    return run


class IntakeServer(ThreadingHTTPServer):
    def __init__(self, queue_dir, host="127.0.0.1", port=8765, today=None, on_queued=lambda enq: None,
                 quiet=False, auto_run=None, runs_dir=None, dnc_path=None, wa_app_secret=None,
                 wa_verify_token=None, phone_window_s=24 * 3600, max_runs_per_day=10):
        """auto_run: None (queue only) or a callable enquiry -> run log (see pipeline_runner)."""
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.today, self.on_queued, self.quiet = today, on_queued, quiet
        self.runs_dir = Path(runs_dir) if runs_dir else EP.ROOT / "runs"
        self.dnc_path = Path(dnc_path) if dnc_path else EP.ROOT / "do-not-call.txt"
        self.wa_app_secret, self.wa_verify_token = wa_app_secret, wa_verify_token
        self.phone_window_s = phone_window_s
        self.lock = threading.Lock()
        self.convos = WI.Conversations(self.queue_dir)
        self.worker = AutoRunner(auto_run, max_runs_per_day, self.run_day, self.say) if auto_run else None
        super().__init__((host, port), Handler)

    @property
    def url(self):
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"

    def say(self, msg):
        if not self.quiet:
            print(msg, flush=True)

    def run_day(self):
        return self.today or datetime.now(EP.IST).date()

    def recently_queued(self, phone):
        cutoff = time.time() - self.phone_window_s
        for f in self.queue_dir.glob("*.json"):
            try:
                if f.stat().st_mtime >= cutoff and json.loads(f.read_text()).get("phone") == phone:
                    return f.stem
            except (OSError, ValueError):
                continue
        return None

    def accept(self, enq):
        """Validate, queue and hand to the worker. Returns (http_status, body)."""
        clean, errors = EP.validate_enquiry(enq, self.today)
        if errors:
            return 400, {"errors": errors}
        path = self.queue_dir / f"{clean['id']}.json"
        with self.lock:
            if path.exists():
                return 409, {"errors": [f"enquiry {clean['id']} is already queued"]}
            if self.recently_queued(clean["phone"]):
                return 429, {"errors": ["we already have an enquiry from this number in the last 24 hours"]}
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(clean, indent=2) + "\n")
            tmp.replace(path)
        self.on_queued(clean)
        if self.worker:
            self.worker.submit(clean)
        return 202, {"id": clean["id"], "status": "queued"}

    def whatsapp_message(self, message_id, wa_id, name, text, ts):
        with self.lock:
            a = WI.handle_message(self.convos, message_id, wa_id, name, text, ts, self.run_day())
            if a["kind"] == "stop":
                dnc = self.dnc_path.read_text() if self.dnc_path.exists() else ""
                if a["phone"] not in dnc:
                    with self.dnc_path.open("a") as f:
                        f.write(f"{a['phone']}  # replied STOP on WhatsApp {EP.now_iso()}\n")
        if a["kind"] == "enquiry":
            code, body = self.accept(a["enquiry"])
            if code == 202:
                self.convos.close(wa_id)
                a = {**a, "kind": "queued", "id": body["id"]}
            else:
                with self.lock:
                    convo = self.convos.load(wa_id)
                    convo["rejected"] = body["errors"]
                    self.convos.save(convo)
                a = {**a, "kind": "rejected", "errors": body["errors"]}
        self.say(f"whatsapp {message_id}: {a['kind']}")
        return {k: a[k] for k in ("kind", "message_id", "id", "missing", "errors") if k in a}

    def drain(self):
        """Hand queued enquiries that have no run yet to the worker (e.g. after a restart). Returns their ids."""
        if not self.worker:
            return []
        ids = []
        for f in sorted(self.queue_dir.glob("*.json"), key=lambda f: f.stat().st_mtime):
            if not (self.runs_dir / f.name).exists():
                self.worker.submit(json.loads(f.read_text()))
                ids.append(f.stem)
        return ids

    def server_close(self):
        if self.worker:
            self.worker.stop()
        super().server_close()


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=8765)
    a.add_argument("--queue", default=str(EP.ROOT / "queue"))
    a.add_argument("--runs", default=str(EP.ROOT / "runs"))
    a.add_argument("--gardeners", default=str(EP.ROOT / "gardeners.csv"))
    a.add_argument("--auto-run", choices=["mock", "off", "sarvam", "retell"], default="mock",
                   help="run each accepted enquiry automatically (default mock: no calls, no spend). "
                        "Real providers run in TEST mode only.")
    a.add_argument("--max-runs-per-day", type=int, default=10)
    p = a.parse_args()
    P.load_env()
    run = None
    if p.auto_run != "off":
        if not Path(p.gardeners).exists():
            sys.exit(f"{p.gardeners} missing -- copy gardeners.example.csv, or use --auto-run off")
        run = pipeline_runner(p.auto_run, runs_dir=p.runs, gardeners_path=p.gardeners,
                              dnc_path=EP.ROOT / "do-not-call.txt", quiet=True)
    srv = IntakeServer(p.queue, p.host, p.port, auto_run=run, runs_dir=p.runs,
                       wa_app_secret=os.environ.get("WMP_WA_APP_SECRET"),
                       wa_verify_token=os.environ.get("WMP_WA_VERIFY_TOKEN"), max_runs_per_day=p.max_runs_per_day,
                       on_queued=lambda e: print(f"queued {e['id']}" + ("" if run else
                                                 f" -> ./enquiry_pipeline.py --file {Path(p.queue) / (e['id'] + '.json')}"),
                                                 flush=True))
    backlog = srv.drain()
    print(f"intake listening on {srv.url} (form /enquire, JSON /enquiries, WhatsApp /webhooks/whatsapp"
          f"{'' if srv.wa_app_secret else ' [disabled: no WMP_WA_APP_SECRET]'}); auto-run: {p.auto_run}"
          + (f"; {len(backlog)} queued enquiries picked up" if backlog else ""), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
