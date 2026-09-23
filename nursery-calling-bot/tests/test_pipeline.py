"""Provider-mocked end-to-end tests for enquiry_pipeline.py. No network, no calls, no spend.

    cd nursery-calling-bot && python3 -m unittest discover -s tests -v
"""
import csv
import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import enquiry_pipeline as EP  # noqa: E402
import providers as P  # noqa: E402

TODAY = date(2026, 9, 23)
CUSTOMER = "+919876543210"
G = {  # fake roster, nearest first by pincode gap from 560056
    "near": ("Near Nursery", "+919000000001", "560056"),
    "mid": ("Mid Nursery", "+919000000002", "560060"),
    "far": ("Far Nursery", "+919000000003", "560098"),
    "farther": ("Farther Nursery", "+919000000004", "560110"),
}
CUSTOMER_YES = {"still_needs_service": True, "start_date": "2026-10-02", "end_date": "2026-10-06",
                "area": "Jagajyothi Layout", "landmark": "BDA park", "plant_count": "20 pots, balcony",
                "visit_frequency": "alternate_days", "access_arrangement": "key with security",
                "budget_per_visit_inr": 150, "do_not_call": False}


def gardener_yes(rate, name="Anil"):
    return P.answered({"available": True, "can_start_on_date": True, "price_per_visit_inr": rate,
                       "contact_name": name, "contact_number": "", "do_not_call": False}, minutes=1.5)


GARDENER_NO = P.answered({"available": False, "referral": "Green Nursery, Kengeri", "do_not_call": False}, minutes=1)


def enquiry(**over):
    e = {"id": "t-1", "name": "Ravi", "phone": "98765 43210", "locality": "Jagajyothi Layout",
         "pincode": "560056", "start_date": "2026-10-02", "end_date": "2026-10-06",
         "notes": "20 pots", "consent_source": "whatsapp_enquiry"}
    e.update(over)
    return e


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.roster = self.tmp / "gardeners.csv"
        self.write_roster()
        self.slept = []

    def write_roster(self, extra=()):
        with self.roster.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "phone", "pincode", "locality", "lat", "lng", "status", "source_id", "notes"])
            for name, phone, pin in G.values():
                w.writerow([name, phone, pin, "", "", "", "active", "", ""])
            for row in extra:
                w.writerow(row)

    def pipe(self, script, mode="mock", hour=11, provider=None, **kw):
        provider = provider or P.MockProvider(script)
        self.provider = provider
        return EP.Pipeline(provider, mode=mode, runs_dir=self.tmp / "runs", gardeners_path=self.roster,
                           dnc_path=self.tmp / "dnc.txt", retry_delay_s=60, sleep=self.slept.append,
                           clock=lambda: datetime(2026, 9, 23, hour, 0, tzinfo=EP.IST), today=TODAY,
                           quiet=True, **kw)

    def events(self, enquiry_id="t-1"):
        return [json.loads(l) for l in (self.tmp / "runs" / f"{enquiry_id}.events.jsonl").read_text().splitlines()]

    def dialled(self):
        return [to for _, to, _, _ in self.provider.placed]


class HappyPath(Base):
    def test_customer_then_gardeners_until_two_available(self):
        log = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES, minutes=2.5)],
                         G["near"][1]: [P.NO_ANSWER], G["mid"][1]: [gardener_yes(100)],
                         G["far"][1]: [GARDENER_NO], G["farther"][1]: [gardener_yes(120, "Manju")]},
                        gardener_attempts=1).start(enquiry())
        self.assertEqual(log["result"], "2_gardeners_available")
        self.assertEqual(log["status"], "finished")
        self.assertEqual(self.dialled(), [CUSTOMER, G["near"][1], G["mid"][1], G["far"][1], G["farther"][1]])
        # priced: 5 days alternate -> 3 visits; fee = max(30, 20%) -> 30
        best = log["offers"][0]
        # 3 visits x Rs 30 fee = 90 < Rs 99 minimum -> Rs 9 booking fee
        self.assertEqual((best["gardener"], best["customer_price_per_visit"], best["visits"], best["booking_fee"],
                          best["customer_total"]), ("Mid Nursery", 130, 3, 9, 399))
        self.assertTrue(best["within_budget"])
        self.assertEqual(log["economics"]["best_offer_revenue_inr"], 99)
        self.assertEqual(log["referrals"], ["Green Nursery, Kengeri"])
        m = log["metrics"]
        self.assertEqual((m["calls_placed"], m["calls_connected"], m["gardeners_available"]), (5, 4, 2))
        self.assertAlmostEqual(log["economics"]["contribution_if_booked_inr"], 99 - m["call_cost_inr"])
        # WhatsApp: one customer draft + one per priced gardener, all wa.me links
        whos = [w["who"] for w in log["whatsapp"]]
        self.assertEqual(whos, ["customer", "gardener", "gardener"])
        self.assertIn("Rs 130/visit", log["whatsapp"][0]["text"])
        self.assertIn("UPI", log["whatsapp"][0]["text"])
        self.assertTrue(all(w["link"].startswith("https://wa.me/91") for w in log["whatsapp"]))
        # on-disk state matches, and events are valid JSON lines in order
        on_disk = json.loads((self.tmp / "runs" / "t-1.json").read_text())
        self.assertEqual(on_disk["result"], log["result"])
        kinds = [e["event"] for e in self.events()]
        self.assertEqual(kinds[0], "run_started")
        self.assertEqual(kinds[-1], "run_finished")
        self.assertIn("handoff_ready", kinds)

    def test_gardeners_never_receive_customer_identity(self):
        self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)], G["near"][1]: [gardener_yes(100)],
                   G["mid"][1]: [gardener_yes(90)]}).start(enquiry())
        for role, _, variables, _ in self.provider.placed:
            if role == "gardener":
                blob = json.dumps(variables)
                self.assertNotIn("Ravi", blob)
                self.assertNotIn("9876543210", blob)
                self.assertEqual(variables["customer_area"], "Jagajyothi Layout, BDA park")

    def test_over_budget_is_flagged(self):
        log = self.pipe({CUSTOMER: [P.answered({**CUSTOMER_YES, "budget_per_visit_inr": 100})],
                         G["near"][1]: [gardener_yes(150)]}, want=1).start(enquiry())
        self.assertFalse(log["offers"][0]["within_budget"])
        self.assertEqual(log["offers"][0]["our_fee_per_visit"], 30)

    def test_nobody_available(self):
        log = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)],
                         **{g[1]: [GARDENER_NO] for g in G.values()}}).start(enquiry())
        self.assertEqual(log["result"], "no_gardener_available")
        self.assertIn("confirm the price here shortly", log["whatsapp"][0]["text"])


class Validation(Base):
    def check(self, errors_substr, **over):
        _, errors = EP.validate_enquiry(enquiry(**over), TODAY)
        self.assertTrue(any(errors_substr in e for e in errors), errors)

    def test_valid(self):
        clean, errors = EP.validate_enquiry(enquiry(phone="+91 98765-43210"), TODAY)
        self.assertEqual(errors, [])
        self.assertEqual(clean["phone"], CUSTOMER)

    def test_rejections(self):
        self.check("not a 10-digit", phone="12345")
        self.check("not an Indian mobile", phone="044 2345 6789")  # 080 landlines collide with 80xx mobiles
        self.check("outside the service area", pincode="400001")
        self.check("6 digits", pincode="5600")
        self.check("in the past", start_date="2026-09-01", end_date="2026-09-05")
        self.check("before start_date", start_date="2026-10-06", end_date="2026-10-02")
        self.check("YYYY-MM-DD", start_date="2/10/2026")
        self.check("missing consent_source", consent_source="")
        self.check("consent_source must be", consent_source="scraped_list")
        self.check("more than 90 days", start_date="2027-03-01", end_date="2027-03-05")

    def test_invalid_enquiry_places_no_call(self):
        with self.assertRaises(ValueError):
            self.pipe({}).start(enquiry(consent_source=""))
        self.assertEqual(self.provider.placed, [])


class CustomerOutcomes(Base):
    def test_retries_then_connects(self):
        log = self.pipe({CUSTOMER: [P.NO_ANSWER, P.BUSY, P.answered(CUSTOMER_YES)],
                         G["near"][1]: [gardener_yes(100)], G["mid"][1]: [gardener_yes(110)]}).start(enquiry())
        self.assertEqual(len(log["customer"]["attempts"]), 3)
        self.assertEqual(self.slept[:2], [60, 60])
        self.assertEqual(log["result"], "2_gardeners_available")

    def test_never_answers_stops_before_gardeners(self):
        log = self.pipe({CUSTOMER: [P.NO_ANSWER]}).start(enquiry())
        self.assertEqual(log["result"], "customer_not_reached")
        self.assertEqual(self.dialled(), [CUSTOMER] * 3)

    def test_opt_out_is_remembered(self):
        log = self.pipe({CUSTOMER: [P.answered({"do_not_call": True})]}).start(enquiry())
        self.assertEqual(log["result"], "customer_opted_out")
        self.assertIn(CUSTOMER, (self.tmp / "dnc.txt").read_text())
        log2 = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)]}).start(enquiry(id="t-2"))
        self.assertEqual(log2["result"], "customer_on_dnc")
        self.assertEqual(self.provider.placed, [])

    def test_ndnc_rejection_goes_to_dnc(self):
        log = self.pipe({CUSTOMER: [P.NDNC_BLOCKED]}).start(enquiry())
        self.assertEqual(log["result"], "customer_on_ndnc")
        self.assertIn(CUSTOMER, (self.tmp / "dnc.txt").read_text())

    def test_other_stops(self):
        cases = [({"needs_kannada_callback": True}, "customer_needs_kannada_callback"),
                 ({"still_needs_service": False}, "customer_no_longer_needs_service"),
                 ({"still_needs_service": False, "callback_time": "after 6pm"}, "customer_callback_requested:after 6pm")]
        for i, (data, result) in enumerate(cases):
            log = self.pipe({CUSTOMER: [P.answered(data)]}).start(enquiry(id=f"t-{i}"))
            self.assertEqual(log["result"], result)
            self.assertEqual(self.dialled(), [CUSTOMER])


class GardenerOutcomes(Base):
    def test_retry_pass_reaches_unanswered_gardener(self):
        log = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)],
                         G["near"][1]: [P.NO_ANSWER, gardener_yes(100)],
                         G["mid"][1]: [GARDENER_NO], G["far"][1]: [GARDENER_NO], G["farther"][1]: [GARDENER_NO]},
                        want=1).start(enquiry())
        self.assertEqual(log["result"], "1_gardeners_available")
        self.assertEqual(self.dialled().count(G["near"][1]), 2)
        self.assertIn(60, self.slept)

    def test_gardener_opt_out_skipped_next_time(self):
        self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)], G["near"][1]: [P.answered({"do_not_call": True})],
                   G["mid"][1]: [gardener_yes(100)], G["far"][1]: [gardener_yes(100)]}).start(enquiry())
        self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)], G["mid"][1]: [gardener_yes(100)],
                   G["far"][1]: [gardener_yes(100)]}).start(enquiry(id="t-2"))
        self.assertNotIn(G["near"][1], self.dialled())

    def test_timeout_is_recorded_and_run_continues(self):
        log = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)], G["near"][1]: [P.TIMEOUT],
                         G["mid"][1]: [gardener_yes(100)]}, want=1).start(enquiry())
        self.assertEqual(log["gardeners"][G["near"][1]]["attempts"][0]["status"], "unknown")
        self.assertEqual(log["result"], "1_gardeners_available")
        self.assertEqual(self.dialled().count(G["near"][1]), 1)   # never redial a call in unknown state


class FailureRecovery(Base):
    def test_transient_place_error_is_retried(self):
        log = self.pipe({CUSTOMER: [P.PLACE_ERROR, P.answered(CUSTOMER_YES)],
                         G["near"][1]: [gardener_yes(100)]}, want=1).start(enquiry())
        self.assertEqual(log["result"], "1_gardeners_available")
        self.assertIn("call_place_failed", [e["event"] for e in self.events()])

    def test_provider_down_pauses_then_resumes(self):
        log = self.pipe({CUSTOMER: [P.PLACE_ERROR]}).start(enquiry())
        self.assertEqual((log["status"], log["result"]), ("paused", "provider_error"))
        log = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)], G["near"][1]: [gardener_yes(100)],
                         G["mid"][1]: [gardener_yes(100)]}).resume("t-1")
        self.assertEqual((log["status"], log["result"]), ("finished", "2_gardeners_available"))
        self.assertIn("run_resumed", [e["event"] for e in self.events()])

    def test_crash_mid_run_resumes_without_redialling(self):
        class Crash(P.MockProvider):
            def wait(self, call_id):
                if self.placed[-1][1] == G["mid"][1]:
                    raise KeyboardInterrupt  # process killed mid-call
                return super().wait(call_id)

        with self.assertRaises(KeyboardInterrupt):
            self.pipe(None, provider=Crash({CUSTOMER: [P.answered(CUSTOMER_YES)],
                                            G["near"][1]: [GARDENER_NO]})).start(enquiry())
        state = json.loads((self.tmp / "runs" / "t-1.json").read_text())   # still valid JSON
        self.assertIsNotNone(state["job"])
        log = self.pipe({G["mid"][1]: [gardener_yes(100)], G["far"][1]: [gardener_yes(100)]}).resume("t-1")
        self.assertEqual(log["result"], "2_gardeners_available")
        self.assertNotIn(CUSTOMER, self.dialled())
        self.assertNotIn(G["near"][1], self.dialled())

    def test_finished_run_cannot_be_resumed_or_restarted(self):
        self.pipe({CUSTOMER: [P.answered({"do_not_call": True})]}).start(enquiry())
        with self.assertRaises(ValueError):
            self.pipe({}).resume("t-1")
        with self.assertRaises(FileExistsError):
            self.pipe({}).start(enquiry())

    def test_repeated_gardener_provider_errors_pause_run(self):
        log = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)], **{g[1]: [P.PLACE_ERROR] for g in G.values()}}) \
            .start(enquiry())
        self.assertEqual((log["status"], log["result"]), ("paused", "provider_error"))


class CallingRulesAndModes(Base):
    def test_live_mode_respects_calling_window(self):
        log = self.pipe({}, mode="live", hour=22).start(enquiry())
        self.assertEqual((log["status"], log["result"]), ("paused", "outside_calling_window"))
        self.assertEqual(self.provider.placed, [])
        log = self.pipe({CUSTOMER: [P.answered(CUSTOMER_YES)], G["near"][1]: [gardener_yes(100)],
                         G["mid"][1]: [gardener_yes(100)]}, mode="live", hour=10).resume("t-1")
        self.assertEqual(log["result"], "2_gardeners_available")

    def test_test_mode_redirects_every_call_and_caps_gardeners(self):
        class Fake(P.MockProvider):
            name = "fake-real-provider"

        prov = Fake({"+918087404471": [P.answered(CUSTOMER_YES), gardener_yes(100)]})
        log = self.pipe(None, mode="test", provider=prov).start(enquiry())
        self.assertEqual(set(self.dialled()), {"+918087404471"})
        self.assertEqual(log["metrics"]["gardeners_called"], 1)


class Ranking(unittest.TestCase):
    rows = [
        {"name": "A", "phone": "9000000001", "pincode": "560056", "lat": "12.95", "lng": "77.51", "status": "active"},
        {"name": "B", "phone": "9000000002", "pincode": "560060", "lat": "", "lng": "", "status": "active"},
        {"name": "C", "phone": "9000000003", "pincode": "560098", "lat": "12.92", "lng": "77.52", "status": "active"},
        {"name": "Far", "phone": "9000000004", "pincode": "560300", "lat": "13.20", "lng": "77.70", "status": "active"},
        {"name": "Off", "phone": "9000000005", "pincode": "560056", "lat": "", "lng": "", "status": "paused"},
        {"name": "NoPhone", "phone": "", "pincode": "560056", "lat": "", "lng": "", "status": "active"},
        {"name": "DNC", "phone": "9000000006", "pincode": "560056", "lat": "", "lng": "", "status": "active"},
    ]

    def test_distance_first_then_pincode_and_filters(self):
        r = EP.rank_gardeners(self.rows, "560056", 12.955, 77.512, blocked={"+919000000006"})
        self.assertEqual([g["name"] for g in r], ["A", "C", "B"])
        self.assertEqual(r[0]["rank_basis"], "distance")

    def test_pincode_only(self):
        r = EP.rank_gardeners(self.rows, "560056")
        self.assertEqual([g["name"] for g in r], ["A", "DNC", "B", "C"])


class Pricing(unittest.TestCase):
    def test_visits(self):
        self.assertEqual(EP.visits_for("2026-10-02", "2026-10-06", "daily"), 5)
        self.assertEqual(EP.visits_for("2026-10-02", "2026-10-06", "alternate_days"), 3)
        self.assertEqual(EP.visits_for("2026-10-01", "2026-10-14", "twice_weekly"), 4)

    def test_fee_is_max_of_flat_and_pct(self):
        self.assertEqual(EP.price_job(100, 3, 30, 20)["our_fee_per_visit"], 30)
        self.assertEqual(EP.price_job(300, 3, 30, 20)["our_fee_per_visit"], 60)

    def test_booking_fee_tops_up_short_jobs_only(self):
        self.assertEqual(EP.price_job(100, 3, 30, 20, min_revenue=99)["booking_fee"], 9)
        self.assertEqual(EP.price_job(100, 10, 30, 20, min_revenue=99)["booking_fee"], 0)


class ProviderAdapters(unittest.TestCase):
    def test_sarvam_attempt_normalised(self):
        s = object.__new__(P.SarvamProvider)
        o = s._normalise("att_1", {"connectivity_status": "connected", "duration_in_seconds": 90,
                                   "audio_url": "https://x/a.wav", "agent_variables": {
                                       "available": "yes", "price_per_visit_inr": "₹120", "do_not_call": "no",
                                       "contact_name": "Anil", "referral": "NA"}})
        self.assertEqual((o["status"], o["minutes"]), ("connected", 1.5))
        self.assertEqual(o["data"], {"available": True, "price_per_visit_inr": 120.0, "do_not_call": False,
                                     "contact_name": "Anil", "referral": None})

    def test_sarvam_ndnc_failure(self):
        s = object.__new__(P.SarvamProvider)
        o = s._normalise("att_2", {"connectivity_status": "failed",
                                   "failure_reason": "exotel: Phone number is registered under TRAI NDNC"})
        self.assertEqual(o["status"], "ndnc")

    def test_sarvam_requires_config(self):
        import os
        old = os.environ.pop("SARVAM_API_KEY", None)
        try:
            os.environ["SARVAM_API_KEY"] = "x"
            with self.assertRaises(P.NotConfigured):
                P.SarvamProvider(config_path=Path(tempfile.mkdtemp()) / "missing.json")
        finally:
            os.environ.pop("SARVAM_API_KEY", None)
            if old is not None:
                os.environ["SARVAM_API_KEY"] = old

    def test_mock_scenario_file(self):
        f = Path(tempfile.mkdtemp()) / "s.json"
        f.write_text(json.dumps({"default": "busy", "script": {CUSTOMER: ["no_answer", {"connected": {"x": 1}}]}}))
        m = P.mock_from_file(f)
        self.assertEqual(m.wait(m.place_call("customer", CUSTOMER, {}, {}))["status"], "no_answer")
        self.assertEqual(m.wait(m.place_call("customer", CUSTOMER, {}, {}))["data"], {"x": 1})
        self.assertEqual(m.wait(m.place_call("customer", "+919999999999", {}, {}))["status"], "busy")


if __name__ == "__main__":
    unittest.main()
