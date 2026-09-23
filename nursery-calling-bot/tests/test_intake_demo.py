"""Intake endpoint and one-command demo tests. Localhost only, no spend.

    cd nursery-calling-bot && python3 -m unittest tests.test_intake_demo -v
"""
import contextlib
import filecmp
import io
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import demo  # noqa: E402
import intake  # noqa: E402

ENQ = json.loads((demo.FIX / "demo-enquiry.json").read_text())


class Intake(unittest.TestCase):
    def setUp(self):
        self.queue = Path(tempfile.mkdtemp()) / "queue"
        self.queued = []
        self.srv = intake.IntakeServer(self.queue, port=0, today=date(2026, 9, 23),
                                       on_queued=self.queued.append, quiet=True)
        Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def call(self, method, path, raw=None):
        req = urllib.request.Request(self.srv.url + path, data=raw, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def post(self, body):
        return self.call("POST", "/enquiries", json.dumps(body).encode())

    def test_valid_enquiry_is_queued_normalised(self):
        self.assertEqual(self.post(ENQ), (202, {"id": "demo-0001", "status": "queued"}))
        saved = json.loads((self.queue / "demo-0001.json").read_text())
        self.assertEqual(saved["phone"], "+919000000099")
        self.assertEqual([e["id"] for e in self.queued], ["demo-0001"])

    def test_duplicate_id_is_409(self):
        self.post(ENQ)
        self.assertEqual(self.post(ENQ)[0], 409)

    def test_invalid_enquiries_are_rejected_and_not_written(self):
        cases = {
            "bad fields": {**ENQ, "pincode": "400001", "consent_source": ""},
            "unknown field": {**ENQ, "address": "12 Some Road"},
            "path traversal id": {**ENQ, "id": "../../etc/passwd"},
            "past date": {**ENQ, "start_date": "2026-09-01"},
        }
        for name, body in cases.items():
            with self.subTest(name):
                code, reply = self.post(body)
                self.assertEqual(code, 400)
                self.assertTrue(reply["errors"])
        for raw in (b"not json", b"[1, 2]", b""):
            with self.subTest(raw=raw):
                self.assertEqual(self.call("POST", "/enquiries", raw)[0], 400)
        self.assertEqual(list(self.queue.iterdir()), [])
        self.assertEqual(self.queued, [])

    def test_oversized_body_rejected(self):
        self.assertEqual(self.post({**ENQ, "notes": "x" * (intake.MAX_BODY + 1)})[0], 400)

    def test_health_and_404(self):
        self.assertEqual(self.call("GET", "/health"), (200, {"ok": True}))
        self.assertEqual(self.call("GET", "/nope")[0], 404)
        self.assertEqual(self.call("POST", "/nope", b"{}")[0], 404)

    def test_binds_localhost_by_default(self):
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")


class Demo(unittest.TestCase):
    def run_demo(self, out):
        argv, sys.argv = sys.argv, ["demo.py", "--out", str(out)]
        try:
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                demo.main()
        finally:
            sys.argv = argv
        return printed.getvalue()

    def test_one_command_demo_is_complete_and_deterministic(self):
        tmp = Path(tempfile.mkdtemp())
        printed = self.run_demo(tmp / "a")
        self.run_demo(tmp / "b")
        cmp = filecmp.dircmp(tmp / "a", tmp / "b")
        self.assertEqual((cmp.left_only, cmp.right_only, cmp.diff_files), ([], [], []))
        for sub in ("runs", "queue"):
            c = filecmp.dircmp(tmp / "a" / sub, tmp / "b" / sub)
            self.assertEqual((c.left_only, c.right_only, c.diff_files), ([], [], []), sub)

        out = tmp / "a"
        for f in ("outcome.json", "whatsapp.md", "unit-economics.md", "summary.md", "do-not-call.txt",
                  "runs/demo-0001.json", "runs/demo-0001.events.jsonl", "queue/demo-0001.json"):
            self.assertTrue((out / f).stat().st_size > 0, f)
        o = json.loads((out / "outcome.json").read_text())
        self.assertEqual((o["status"], o["result"]), ("finished", "2_gardeners_available"))
        self.assertEqual((o["intake"]["rejected"]["http_status"], o["intake"]["accepted"]["http_status"]), (400, 202))
        self.assertEqual(o["do_not_call_added"], ["+919000000003", "+919000000004"])
        self.assertEqual(o["referrals"], ["Green Nursery, Kengeri"])
        m = o["metrics"]
        self.assertEqual((m["calls_placed"], m["calls_connected"], m["gardeners_available"]), (9, 5, 2))
        self.assertGreater(o["economics"]["contribution_if_booked_inr"], 0)
        for kind in ("run_started", "call_place_failed", "retry_wait", "dnc_added", "handoff_ready", "run_finished"):
            self.assertIn(kind, o["event_counts"])
        events = [json.loads(l) for l in (out / "runs/demo-0001.events.jsonl").read_text().splitlines()]
        self.assertEqual([events[0]["event"], events[-1]["event"]], ["run_started", "run_finished"])
        self.assertEqual([e["ts"] for e in events], sorted(e["ts"] for e in events))
        dialled = {e["number"] for e in events if e["event"] == "call_placed"}
        self.assertNotIn("+919000000007", dialled)                  # paused roster row
        self.assertIn("https://wa.me/919000000099", (out / "whatsapp.md").read_text())
        self.assertIn("Contribution if booked", (out / "unit-economics.md").read_text())
        self.assertIn("2_gardeners_available", printed)

    def test_refuses_to_clobber_a_foreign_directory(self):
        foreign = Path(tempfile.mkdtemp())
        (foreign / "keep.txt").write_text("mine")
        with self.assertRaises(SystemExit):
            self.run_demo(foreign)
        self.assertTrue((foreign / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
