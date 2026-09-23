"""Website form + WhatsApp webhook + auto-run tests. Localhost only, mock provider, no spend.

    cd nursery-calling-bot && python3 -m unittest tests.test_autotrigger -v
"""
import http.client
import json
import sys
import tempfile
import unittest
import urllib.parse
from datetime import date
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import intake  # noqa: E402
import whatsapp_inbound as WI  # noqa: E402

FIX = Path(__file__).resolve().parents[1] / "fixtures"
TODAY = date(2026, 9, 23)
SECRET, TOKEN = "test-app-secret", "test-verify-token"
WA = json.loads((FIX / "whatsapp-message.json").read_text())
FORM = {"name": "Form Customer", "phone": "90000 00088", "locality": "Jagajyothi Layout", "pincode": "560056",
        "start_date": "2026-10-02", "end_date": "2026-10-06", "notes": "15 pots", "consent_call": "yes",
        "website": ""}


def wa_payload(text, msg_id="wamid.T1", wa_id="919000000077", ts=1790150400):
    p = json.loads(json.dumps(WA))
    v = p["entry"][0]["changes"][0]["value"]
    v["contacts"][0]["wa_id"] = wa_id
    v["messages"][0].update({"from": wa_id, "id": msg_id, "timestamp": str(ts), "text": {"body": text}})
    return p


class Base(unittest.TestCase):
    auto_run = True
    max_runs_per_day = 10

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.queue, self.runs, self.dnc = self.tmp / "queue", self.tmp / "runs", self.tmp / "do-not-call.txt"
        self.srv = self.start_server()

    def start_server(self):
        run = intake.pipeline_runner("mock", runs_dir=self.runs, gardeners_path=FIX / "demo-roster.csv",
                                     dnc_path=self.dnc, today=TODAY) if self.auto_run else None
        srv = intake.IntakeServer(self.queue, port=0, today=TODAY, quiet=True, auto_run=run, runs_dir=self.runs,
                                  dnc_path=self.dnc, wa_app_secret=SECRET, wa_verify_token=TOKEN,
                                  max_runs_per_day=self.max_runs_per_day)
        Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return srv

    def request(self, method, path, body=b"", headers=None, srv=None):
        """Raw HTTP (no redirect following). Returns (status, headers, text)."""
        host, port = (srv or self.srv).server_address[:2]
        c = http.client.HTTPConnection(host, port, timeout=10)
        try:
            c.request(method, path, body=body, headers=headers or {})
            r = c.getresponse()
            return r.status, dict(r.getheaders()), r.read().decode()
        finally:
            c.close()

    def post_form(self, fields):
        return self.request("POST", "/enquire", urllib.parse.urlencode(fields).encode(),
                            {"Content-Type": "application/x-www-form-urlencoded"})

    def post_wa(self, payload, signature=None, raw=None):
        raw = raw if raw is not None else json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        sig = WI.sign(SECRET, raw) if signature is None else signature
        if sig:
            headers["X-Hub-Signature-256"] = sig
        code, _, text = self.request("POST", "/webhooks/whatsapp", raw, headers)
        return code, json.loads(text)

    def queued(self):
        return sorted(f.stem for f in self.queue.glob("*.json"))

    def run_log(self, enquiry_id):
        self.srv.worker.wait()
        return json.loads((self.runs / f"{enquiry_id}.json").read_text())


class WebsiteForm(Base):
    def test_form_page_has_consent_box_and_honeypot(self):
        code, headers, page = self.request("GET", "/enquire")
        self.assertEqual(code, 200)
        self.assertIn("text/html", headers["Content-Type"])
        for s in ('name="consent_call"', 'name="website"', 'action="/enquire"'):
            self.assertIn(s, page)

    def test_form_post_queues_and_auto_runs_in_test_mode(self):
        code, headers, _ = self.post_form(FORM)
        self.assertEqual((code, headers["Location"]), (303, "/enquire/thanks"))
        [eid] = self.queued()
        saved = json.loads((self.queue / f"{eid}.json").read_text())
        self.assertEqual((saved["phone"], saved["consent_source"]), ("+919000000088", "website_form"))
        log = self.run_log(eid)
        self.assertEqual((log["status"], log["mode"], log["provider"]), ("finished", "test", "mock"))
        self.assertTrue(log["result"].endswith("gardeners_available"), log["result"])
        self.assertTrue(log["whatsapp"])
        self.assertEqual(self.request("GET", "/enquire/thanks")[0], 200)

    def test_missing_call_consent_is_rejected(self):
        code, _, page = self.post_form({**FORM, "consent_call": ""})
        self.assertEqual(code, 400)
        self.assertIn("phone call", page)
        self.assertEqual(self.queued(), [])

    def test_honeypot_looks_successful_but_queues_nothing(self):
        code, headers, _ = self.post_form({**FORM, "website": "http://spam.example"})
        self.assertEqual((code, headers["Location"]), (303, "/enquire/thanks"))
        self.assertEqual(self.queued(), [])

    def test_invalid_form_is_redisplayed_escaped(self):
        code, _, page = self.post_form({**FORM, "name": "<script>x</script>", "pincode": "400001"})
        self.assertEqual(code, 400)
        self.assertIn("outside the service area", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>x", page)
        self.assertEqual(self.queued(), [])

    def test_wrong_content_type_is_415(self):
        code, _, _ = self.request("POST", "/enquire", json.dumps(FORM).encode(), {"Content-Type": "application/json"})
        self.assertEqual(code, 415)


class WhatsAppWebhook(Base):
    def test_verify_handshake_needs_the_right_token(self):
        ok = f"/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token={TOKEN}&hub.challenge=12345"
        self.assertEqual(self.request("GET", ok)[::2], (200, "12345"))
        self.assertEqual(self.request("GET", ok.replace(TOKEN, "wrong"))[0], 403)
        self.assertEqual(self.request("GET", "/webhooks/whatsapp?hub.challenge=1")[0], 403)

    def test_signed_message_with_call_consent_is_queued_and_run(self):
        code, reply = self.post_wa(WA)
        self.assertEqual(code, 200)
        self.assertEqual(reply["handled"][0]["kind"], "queued")
        eid = reply["handled"][0]["id"]
        self.assertEqual(eid, "wa-20260923-133000-0099")
        enq = json.loads((self.queue / f"{eid}.json").read_text())
        self.assertEqual({k: enq[k] for k in ("phone", "pincode", "locality", "start_date", "end_date", "consent_source")},
                         {"phone": "+919000000099", "pincode": "560056", "locality": "Jagajyothi Layout",
                          "start_date": "2026-10-02", "end_date": "2026-10-06", "consent_source": "whatsapp_enquiry"})
        self.assertEqual(self.run_log(eid)["status"], "finished")
        self.assertFalse((self.queue / "held" / "919000000099.json").exists())

    def test_bad_or_missing_signature_is_403_and_nothing_happens(self):
        raw = json.dumps(WA).encode()
        for sig in ("", "sha256=" + "0" * 64, WI.sign("other-secret", raw), "md5=abc"):
            with self.subTest(sig=sig):
                self.assertEqual(self.post_wa(None, signature=sig, raw=raw)[0], 403)
        tampered = raw.replace(b"560056", b"560057")
        self.assertEqual(self.post_wa(None, signature=WI.sign(SECRET, raw), raw=tampered)[0], 403)
        self.assertEqual(self.queued(), [])
        self.assertFalse((self.queue / "held").exists())

    def test_unconfigured_webhook_is_503(self):
        self.srv.wa_app_secret = None
        self.assertEqual(self.post_wa(WA)[0], 503)
        self.assertEqual(self.queued(), [])

    def test_redelivered_message_is_not_requeued(self):
        first, second = self.post_wa(WA)[1], self.post_wa(WA)[1]
        self.assertEqual([first["handled"][0]["kind"], second["handled"][0]["kind"]], ["queued", "duplicate"])
        self.assertEqual(len(self.queued()), 1)

    def test_details_can_arrive_over_several_messages(self):
        _, r1 = self.post_wa(wa_payload("Hi, need someone to water plants in Jagajyothi Layout 560056", "wamid.A"))
        self.assertEqual(r1["handled"][0]["kind"], "held")
        self.assertEqual(r1["handled"][0]["missing"], ["dates", "call_consent"])
        held = json.loads((self.queue / "held" / "919000000077.json").read_text())
        self.assertIn("dates you'll be away", held["reply_draft"])
        self.assertEqual(self.queued(), [])
        _, r2 = self.post_wa(wa_payload("Away 10/10 to 14/10. Yes you can call me", "wamid.B", ts=1790150500))
        self.assertEqual(r2["handled"][0]["kind"], "queued")
        enq = json.loads((self.queue / f"{r2['handled'][0]['id']}.json").read_text())
        self.assertEqual((enq["start_date"], enq["end_date"], enq["locality"]),
                         ("2026-10-10", "2026-10-14", "Jagajyothi Layout"))

    def test_join_page_message_is_held_until_call_consent(self):
        text = ("Hi, I want to join the plant-care pilot.\nLocality: Jagajyothi Layout, 560056\nPlants: 11-30\n"
                "Travel: within-2-weeks\nBudget/visit: 60-100\nI agree to be contacted on WhatsApp. [ref:own-site]")
        _, r = self.post_wa(wa_payload(text))
        self.assertEqual(r["handled"][0], {"kind": "held", "message_id": "wamid.T1", "missing": ["dates", "call_consent"]})
        self.assertEqual(self.queued(), [])

    def test_refusing_a_call_is_never_consent(self):
        _, r = self.post_wa(wa_payload("560056 Jagajyothi Layout, 2 Oct to 6 Oct. Please don't call me, whatsapp only"))
        self.assertEqual(r["handled"][0]["missing"], ["call_consent"])
        self.assertEqual(self.queued(), [])

    def test_stop_goes_on_do_not_call_and_clears_the_conversation(self):
        self.post_wa(wa_payload("Hi, plants in Kengeri 560060", "wamid.S1"))
        _, r = self.post_wa(wa_payload("STOP", "wamid.S2"))
        self.assertEqual(r["handled"][0]["kind"], "stop")
        self.assertIn("+919000000077", self.dnc.read_text())
        self.assertFalse((self.queue / "held" / "919000000077.json").exists())
        self.post_wa(wa_payload("stop", "wamid.S3"))
        self.assertEqual(self.dnc.read_text().count("+919000000077"), 1)

    def test_status_callbacks_and_media_are_ignored(self):
        p = wa_payload("x")
        p["entry"][0]["changes"][0]["value"]["messages"][0]["type"] = "image"
        self.assertEqual(self.post_wa(p), (200, {"handled": []}))
        self.assertEqual(self.post_wa({"object": "whatsapp_business_account", "entry": [
            {"changes": [{"value": {"statuses": [{"id": "wamid.X", "status": "read"}]}}]}]}), (200, {"handled": []}))


class Guards(Base):
    max_runs_per_day = 1

    def test_same_phone_twice_in_24h_is_429(self):
        body = {**FORM, "consent_source": "website_form", "id": "g-1"}
        del body["consent_call"], body["website"]
        self.assertEqual(self.request("POST", "/enquiries", json.dumps(body).encode())[0], 202)
        self.assertEqual(self.request("POST", "/enquiries", json.dumps({**body, "id": "g-2"}).encode())[0], 429)
        code, _, page = self.post_form(FORM)
        self.assertEqual(code, 429)
        self.assertIn("last 24 hours", page)
        self.assertEqual(self.queued(), ["g-1"])

    def test_daily_cap_defers_runs_and_restart_drains_them(self):
        self.post_form(FORM)
        self.post_form({**FORM, "phone": "90000 00066", "name": "Second"})
        self.srv.worker.wait()
        self.assertEqual(len(self.queued()), 2)
        self.assertEqual(len(list(self.runs.glob("*.events.jsonl"))), 1)
        self.assertEqual(sum(r.startswith("deferred") for r in self.srv.worker.results.values()), 1)
        srv2 = self.start_server()                  # e.g. next day / restart: backlog picked up
        self.assertEqual(len(srv2.drain()), 1)
        srv2.worker.wait()
        self.assertEqual(len(list(self.runs.glob("*.events.jsonl"))), 2)


class Parsing(unittest.TestCase):
    def test_date_formats(self):
        cases = {"2026-10-02 to 2026-10-06": ("2026-10-02", "2026-10-06"),
                 "from 2/10 till 6/10/2026": ("2026-10-02", "2026-10-06"),
                 "Oct 2 - Oct 6": ("2026-10-02", "2026-10-06"),
                 "2nd October to 6th Oct": ("2026-10-02", "2026-10-06"),
                 "30 Dec to 3 Jan": ("2026-12-30", "2027-01-03"),
                 "leaving 5 Sep back 9 Sep": ("2027-09-05", "2027-09-09")}
        for text, want in cases.items():
            with self.subTest(text):
                got = WI.parse_dates(text, TODAY)
                self.assertEqual(tuple(d.isoformat() for d in got[:2]), want)

    def test_call_consent(self):
        for text, want in {"ok to call": True, "you can call me after 6": True, "call me": True,
                           "don't call, whatsapp only": False, "no calls please": False, "can't take calls": False,
                           "I agree to be contacted on WhatsApp": False}.items():
            with self.subTest(text):
                self.assertEqual(WI.call_consent(text), want)

    def test_signature(self):
        raw = b'{"a":1}'
        self.assertTrue(WI.signature_ok(SECRET, raw, WI.sign(SECRET, raw)))
        self.assertFalse(WI.signature_ok(SECRET, raw, None))
        self.assertFalse(WI.signature_ok(None, raw, WI.sign(SECRET, raw)))


if __name__ == "__main__":
    unittest.main()
