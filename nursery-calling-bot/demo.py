#!/usr/bin/env python3
"""One-command, zero-cost demonstration of the whole enquiry workflow. No network (apart from a
localhost HTTP server), no account, no phone number, no spend.

  python3 demo.py                 # writes demo-output/ and prints a summary
  python3 demo.py --out /tmp/x    # somewhere else

What happens:
  1. starts the intake endpoint (intake.py) on 127.0.0.1, POSTs an invalid enquiry (rejected, 400)
     and then fixtures/demo-enquiry.json (accepted, 202, queued)
  2. runs the queued enquiry through the real Pipeline state machine with deterministic mocked
     calls (fixtures/demo-scenario.json) against a synthetic roster (fixtures/demo-roster.csv).
     The script exercises a busy customer retry, gardener no-answer + retry pass, a decline with a
     referral, an opt-out, a TRAI NDNC rejection, a create-call API error, voicemail and a
     paused (never-called) roster row
  3. writes to --out:
       runs/demo-0001.json           final run state (resumable format)
       runs/demo-0001.events.jsonl   structured event log, one JSON object per line
       do-not-call.txt               numbers added by the opt-out and the NDNC rejection
       outcome.json                  the final outcome in one small object
       whatsapp.md                   the WhatsApp handoff drafts (customer + gardeners)
       unit-economics.md             this run's actual cost/contribution + the funnel model
       summary.md                    everything above in one page
Output is byte-identical across runs: the clock and ids are fixed.
"""
import argparse
import contextlib
import io
import json
import shutil
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Thread

import enquiry_pipeline as EP
import intake
import providers as P
import unit_economics as UE

ROOT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"
DEMO_TODAY = date(2026, 9, 23)
DEMO_START_UTC = datetime(2026, 9, 23, 5, 30, tzinfo=timezone.utc)   # 11:00 IST, inside the calling window
MARKER = ".demo-output"


class FakeClock:
    """Every timestamp the pipeline writes advances by one second, so logs are reproducible."""
    def __init__(self, start):
        self.t = start

    def iso(self):
        self.t += timedelta(seconds=1)
        return self.t.isoformat(timespec="seconds")


def post_json(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        with e:
            return e.code, json.loads(e.read())


def prepare_out(out):
    if out.exists():
        if not (out / MARKER).exists():
            sys.exit(f"{out} exists and wasn't created by demo.py; refusing to overwrite it")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("created by demo.py; safe to delete\n")


def intake_step(out):
    queued = []
    srv = intake.IntakeServer(out / "queue", port=0, today=DEMO_TODAY, on_queued=queued.append, quiet=True)
    Thread(target=srv.serve_forever, daemon=True).start()
    try:
        bad = {**json.loads((FIX / "demo-enquiry.json").read_text()), "id": "demo-bad",
               "pincode": "400001", "consent_source": ""}
        rejected = post_json(srv.url + "/enquiries", bad)
        accepted = post_json(srv.url + "/enquiries", json.loads((FIX / "demo-enquiry.json").read_text()))
    finally:
        srv.shutdown()
        srv.server_close()
    assert rejected[0] == 400 and accepted[0] == 202 and len(queued) == 1, (rejected, accepted, queued)
    return {"rejected": {**rejected[1], "http_status": rejected[0]}, "accepted": {**accepted[1], "http_status": accepted[0]},
            "queued_file": f"queue/{accepted[1]['id']}.json"}


def run_step(out, enquiry):
    clock = FakeClock(DEMO_START_UTC)
    real_now_iso, EP.now_iso = EP.now_iso, clock.iso
    try:
        pipe = EP.Pipeline(P.mock_from_file(FIX / "demo-scenario.json"), mode="test",
                           runs_dir=out / "runs", gardeners_path=FIX / "demo-roster.csv",
                           dnc_path=out / "do-not-call.txt", retry_delay_s=300, sleep=lambda s: None,
                           clock=lambda: DEMO_START_UTC.astimezone(EP.IST), today=DEMO_TODAY, quiet=True)
        return pipe.start(enquiry)
    finally:
        EP.now_iso = real_now_iso


def economics_md(out, log):
    model = io.StringIO()
    with contextlib.redirect_stdout(model):
        UE.table(UE.build_parser().parse_args([]))
    actual = io.StringIO()
    with contextlib.redirect_stdout(actual):
        UE.actuals(out / "runs")
    e, m = log["economics"], log["metrics"]
    return "\n".join([
        "# Unit economics (demo run)", "",
        "## This enquiry (mock rates: Rs 3.0 per connected minute)", "",
        "| Metric | Value |", "|---|---|",
        f"| Calls placed / connected | {m['calls_placed']} / {m['calls_connected']} (connect rate {m['connect_rate']}) |",
        f"| Billable minutes | {m['call_minutes']} |",
        f"| Call cost | Rs {e['call_cost_inr']} |",
        f"| Customer pays (best offer) | Rs {e['customer_total_inr']} |",
        f"| Our revenue if booked | Rs {e['best_offer_revenue_inr']} |",
        f"| **Contribution if booked** | **Rs {e['contribution_if_booked_inr']}** |",
        "", f"_{e['note']}_", "",
        "## `unit_economics.py --runs` over this run", "", "```", actual.getvalue().rstrip(), "```", "",
        "## Funnel model (`unit_economics.py`, default assumptions; see UNIT_ECONOMICS.md)", "",
        model.getvalue().rstrip(), "",
    ])


def whatsapp_md(log):
    parts = ["# WhatsApp handoff drafts", "",
             "Drafts only. A person opens each link, checks it and presses send; the gardener gets the "
             "address only after the customer pays by UPI.", ""]
    for w in log["whatsapp"]:
        parts += [f"## To {w['who']} ({w['to']})", "", "```", w["text"], "```", "", f"<{w['link']}>", ""]
    return "\n".join(parts)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--out", default=str(ROOT / "demo-output"))
    out = Path(a.parse_args().out).resolve()
    prepare_out(out)

    intake_result = intake_step(out)
    enquiry = json.loads((out / intake_result["queued_file"]).read_text())
    log = run_step(out, enquiry)

    events = [json.loads(l) for l in (out / "runs" / f"{enquiry['id']}.events.jsonl").read_text().splitlines()]
    outcome = {"enquiry_id": enquiry["id"], "status": log["status"], "result": log["result"],
               "intake": intake_result, "metrics": log["metrics"], "economics": log["economics"],
               "offers": log["offers"], "referrals": log["referrals"],
               "do_not_call_added": [e["number"] for e in events if e["event"] == "dnc_added"],
               "event_counts": {k: sum(1 for e in events if e["event"] == k)
                                for k in sorted({e["event"] for e in events})}}
    (out / "outcome.json").write_text(json.dumps(outcome, indent=2) + "\n")
    (out / "whatsapp.md").write_text(whatsapp_md(log))
    econ = economics_md(out, log)
    (out / "unit-economics.md").write_text(econ)

    timeline = [f"| {e['ts'][11:19]} | {e['event']} | " +
                ", ".join(f"{k}={v}" for k, v in e.items() if k not in ("ts", "enquiry_id", "event")
                          and v not in (None, "")) + " |" for e in events]
    summary = "\n".join([
        "# Enquiry workflow demo (mocked, zero cost)", "",
        f"**Result: `{log['result']}`** (status `{log['status']}`)", "",
        "## Intake", "",
        f"- invalid enquiry -> HTTP {intake_result['rejected']['http_status']}: "
        + "; ".join(intake_result["rejected"]["errors"]),
        f"- sample enquiry -> HTTP {intake_result['accepted']['http_status']}, queued as `{intake_result['queued_file']}`", "",
        "## Event log", "", "| UTC | Event | Details |", "|---|---|---|", *timeline, "",
        "## Offers", "", "| Gardener | Rate | Our fee | Customer/visit | Visits | Booking fee | Customer total | In budget |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {o['gardener']} ({o['contact_name']}) | {o.get('gardener_rate_per_visit')} | {o.get('our_fee_per_visit')} "
          f"| {o.get('customer_price_per_visit')} | {o.get('visits')} | {o.get('booking_fee')} | {o.get('customer_total')} "
          f"| {o.get('within_budget')} |" for o in log["offers"]], "",
        f"Referrals collected: {', '.join(log['referrals']) or 'none'}  ",
        f"Added to do-not-call: {', '.join(outcome['do_not_call_added']) or 'none'}", "",
        whatsapp_md(log).replace("# WhatsApp", "## WhatsApp", 1).replace("\n## To", "\n### To"),
        econ.replace("\n## ", "\n### ").replace("# Unit economics", "## Unit economics", 1),
    ])
    (out / "summary.md").write_text(summary)

    m, e = log["metrics"], log["economics"]
    print(f"Intake: invalid enquiry rejected (400), demo enquiry queued (202) as {enquiry['id']}")
    print(f"Run: {log['result']} | {m['calls_placed']} calls, {m['calls_connected']} connected, "
          f"{m['call_minutes']} min, Rs {m['call_cost_inr']} | {len(events)} events")
    for o in log["offers"]:
        print(f"  offer: {o['gardener']} Rs {o['customer_price_per_visit']}/visit x {o['visits']} "
              f"+ Rs {o['booking_fee']} booking fee = Rs {o['customer_total']}")
    print(f"Do-not-call added: {', '.join(outcome['do_not_call_added'])} | referrals: {', '.join(log['referrals'])}")
    print(f"Contribution if booked: Rs {e['contribution_if_booked_inr']} "
          f"(revenue Rs {e['best_offer_revenue_inr']} - calls Rs {e['call_cost_inr']})")
    print(f"WhatsApp drafts: {len(log['whatsapp'])} | full report: {out / 'summary.md'}")


if __name__ == "__main__":
    main()
