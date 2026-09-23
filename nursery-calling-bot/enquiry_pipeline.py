#!/usr/bin/env python3
"""Enquiry -> call the customer -> call gardeners near them -> WhatsApp handoff.

  1. Validates the enquiry (phone, Bangalore pincode, dates, recorded consent to be called).
  2. Calls the customer ("customer" agent, Indian-English, switches to Hinglish) to confirm dates,
     area, plants, visit frequency, access and budget. Retries no-answer/busy.
  3. If they confirm, calls gardeners from gardeners.csv nearest first ("gardener" agent, Hinglish)
     until --want of them say they're available. Unreached gardeners get one retry pass.
  4. Prices the job (gardener rate + our fee per visit), writes runs/<id>.json (state, resumable),
     runs/<id>.events.jsonl (one line per event) and prints WhatsApp drafts for the customer and
     the available gardeners.

Providers (--provider):
  sarvam  (default) Sarvam Voice Agents -- Indian voices; needs a connected number (FREE_PATHS.md).
  retell  Retell AI (fallback; needs a card for a number).
  mock    No calls, no spend. Scripted outcomes (--scenario file.json, or a built-in happy path).
          For the full one-command demo (intake endpoint + report) run ./demo.py.

Modes (real providers only):
  default   TEST: every call rings TEST_NUMBER (your own phone) instead of the real number, max 1 gardener.
  --live    Calls the real customer and gardener numbers, only between 09:00 and 21:00 IST.

Examples:
  ./enquiry_pipeline.py --provider mock --name Ravi --phone 98xxxxxxxx --locality "Jagajyothi Layout" \
      --pincode 560056 --start 2026-10-02 --end 2026-10-06 --notes "20 pots, balcony" --consent whatsapp_enquiry
  ./enquiry_pipeline.py --resume 20261001-101500-ravi
"""
import argparse
import csv
import json
import math
import re
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import providers as P

ROOT = Path(__file__).resolve().parent
TEST_NUMBER = "+918087404471"
IST = timezone(timedelta(hours=5, minutes=30))
CALL_WINDOW_IST = (9, 21)                  # TRAI: no promotional/cold calls outside 09:00-21:00
SERVICE_PINCODE_PREFIXES = ("560",)        # Bangalore urban
CONSENT_SOURCES = {"whatsapp_enquiry", "website_form", "phone_enquiry", "founder_test"}
FREQUENCIES = {"daily", "alternate_days", "twice_weekly", "other", "unknown"}
RETRYABLE = {P.NO_ANSWER_S, P.BUSY_S, P.VOICEMAIL_S}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def e164(phone, mobile_only=False):
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    digits = digits.lstrip("0")
    if len(digits) != 10:
        raise ValueError(f"not a 10-digit Indian number: {phone!r}")
    if mobile_only and digits[0] not in "6789":
        raise ValueError(f"not an Indian mobile number: {phone!r}")
    return "+91" + digits


# ---------------------------------------------------------------------------------------------
# Enquiry validation

def validate_enquiry(enq, today=None):
    """Returns (clean_enquiry, errors). An enquiry with errors must not be called."""
    today = today or datetime.now(IST).date()
    e, errors = dict(enq), []
    for k in ("name", "phone", "locality", "pincode", "start_date", "end_date", "consent_source"):
        if not str(e.get(k) or "").strip():
            errors.append(f"missing {k}")
    if e.get("name") and len(str(e["name"])) > 60:
        errors.append("name too long")
    if e.get("phone"):
        try:
            e["phone"] = e164(e["phone"], mobile_only=True)
        except ValueError as x:
            errors.append(str(x))
    if e.get("pincode"):
        e["pincode"] = str(e["pincode"]).strip()
        if not re.fullmatch(r"\d{6}", e["pincode"]):
            errors.append(f"pincode must be 6 digits: {e['pincode']!r}")
        elif not e["pincode"].startswith(SERVICE_PINCODE_PREFIXES):
            errors.append(f"pincode {e['pincode']} is outside the service area {SERVICE_PINCODE_PREFIXES}")
    start = end = None
    for k in ("start_date", "end_date"):
        if e.get(k):
            try:
                d = date.fromisoformat(str(e[k]))
                start, end = (d, end) if k == "start_date" else (start, d)
            except ValueError:
                errors.append(f"{k} must be YYYY-MM-DD: {e[k]!r}")
    if start and end:
        if end < start:
            errors.append("end_date is before start_date")
        if start < today:
            errors.append("start_date is in the past")
        if start > today + timedelta(days=90):
            errors.append("start_date is more than 90 days away")
        if (end - start).days > 60:
            errors.append("job longer than 60 days -- quote manually")
    if e.get("consent_source") and e["consent_source"] not in CONSENT_SOURCES:
        errors.append(f"consent_source must be one of {sorted(CONSENT_SOURCES)}")
    for k in ("lat", "lng"):
        if e.get(k) not in (None, ""):
            try:
                e[k] = float(e[k])
            except (TypeError, ValueError):
                errors.append(f"{k} must be a number")
    if not e.get("id") and e.get("name"):
        e["id"] = datetime.now(IST).strftime("%Y%m%d-%H%M%S") + "-" + \
            (re.sub(r"[^a-z0-9]+", "-", str(e["name"]).lower()).strip("-")[:40] or "enquiry")
    if e.get("id") and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", str(e["id"])):
        errors.append("id may only contain letters, digits, '-' and '_'")   # it becomes a file name
    return e, errors


# ---------------------------------------------------------------------------------------------
# Gardener ranking

def haversine_km(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def rank_gardeners(rows, pincode, lat=None, lng=None, blocked=(), radius_km=12, max_pincode_gap=60):
    """Active, callable gardeners nearest first. Uses real distance when both sides have lat/lng,
    otherwise same pincode first then numeric pincode gap (a rough proxy within Bangalore).
    Drops rows on the do-not-call list, without a valid number, or too far away."""
    out = []
    for r in rows:
        if (r.get("status") or "").strip() != "active":
            continue
        try:
            phone = e164(r.get("phone") or "")
        except ValueError:
            continue
        if phone in blocked:
            continue
        g = {**r, "phone": phone}
        if lat is not None and lng is not None and r.get("lat") and r.get("lng"):
            d = haversine_km(lat, lng, float(r["lat"]), float(r["lng"]))
            if d > radius_km:
                continue
            out.append(((0, d), {**g, "distance_km": round(d, 1), "rank_basis": "distance"}))
        else:
            try:
                gap = abs(int(r["pincode"]) - int(pincode))
            except (KeyError, ValueError):
                continue
            if gap > max_pincode_gap:
                continue
            out.append(((1, gap), {**g, "distance_km": None, "rank_basis": f"pincode gap {gap}"}))
    return [g for _, g in sorted(out, key=lambda x: x[0])]


def read_gardeners(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------------------------
# Pricing

def visits_for(start, end, frequency):
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    if frequency == "alternate_days":
        return math.ceil(days / 2)
    if frequency == "twice_weekly":
        return max(1, math.ceil(days * 2 / 7))
    return days  # daily / other / unknown: quote the worst case and confirm on WhatsApp


def price_job(gardener_rate, visits, fee_per_visit, fee_pct, min_revenue=0):
    """Customer pays gardener rate + our fee per visit, plus a booking fee that tops our revenue up
    to `min_revenue` on short jobs (so a 3-visit job still covers the calls it took to fill)."""
    fee = max(fee_per_visit, math.ceil(gardener_rate * fee_pct / 100))
    per_visit = gardener_rate + fee
    booking_fee = max(0, min_revenue - fee * visits)
    return {"gardener_rate_per_visit": gardener_rate, "our_fee_per_visit": fee,
            "customer_price_per_visit": per_visit, "visits": visits, "booking_fee": booking_fee,
            "customer_total": per_visit * visits + booking_fee, "gardener_payout": gardener_rate * visits,
            "our_revenue": fee * visits + booking_fee}


# ---------------------------------------------------------------------------------------------
# Pipeline

class Pipeline:
    def __init__(self, provider, *, mode="test", runs_dir=ROOT / "runs", gardeners_path=ROOT / "gardeners.csv",
                 dnc_path=ROOT / "do-not-call.txt", test_number=TEST_NUMBER, max_gardeners=6, want=2,
                 customer_attempts=3, gardener_attempts=2, retry_delay_s=300, place_retries=3,
                 max_consecutive_provider_errors=3, fee_per_visit=30, fee_pct=20, min_revenue=99, est_inr_per_min=3.0,
                 sleep=time.sleep, clock=lambda: datetime.now(IST), today=None, quiet=False):
        self.provider, self.mode = provider, mode
        self.runs_dir, self.gardeners_path, self.dnc_path = Path(runs_dir), Path(gardeners_path), Path(dnc_path)
        self.test_number = test_number
        self.redirect = mode == "test" and provider.name != "mock"
        self.enforce_window = mode == "live"
        self.max_gardeners = 1 if self.redirect else max_gardeners
        self.want, self.customer_attempts, self.gardener_attempts = want, customer_attempts, gardener_attempts
        self.retry_delay_s, self.place_retries = retry_delay_s, place_retries
        self.max_consecutive_provider_errors = max_consecutive_provider_errors
        self.fee_per_visit, self.fee_pct, self.min_revenue = fee_per_visit, fee_pct, min_revenue
        self.est_inr_per_min = est_inr_per_min
        self.sleep, self.clock, self.today, self.quiet = sleep, clock, today, quiet
        self._provider_errors = 0

    # -- infra ----------------------------------------------------------------------------------
    def say(self, msg):
        if not self.quiet:
            print(msg, flush=True)

    def dnc(self):
        if not self.dnc_path.exists():
            return set()
        return {l.split("#")[0].strip() for l in self.dnc_path.read_text().splitlines() if l.split("#")[0].strip()}

    def add_dnc(self, number, why):
        if number not in self.dnc():
            with self.dnc_path.open("a") as f:
                f.write(f"{number}  # {why} {now_iso()}\n")
            self.event("dnc_added", number=number, reason=why)

    def event(self, kind, **fields):
        with self.events_path.open("a") as f:
            f.write(json.dumps({"ts": now_iso(), "enquiry_id": self.log["enquiry"]["id"], "event": kind,
                                **fields}) + "\n")

    def save(self):
        self.log["updated_at"] = now_iso()
        self.log["metrics"] = self.metrics()
        tmp = self.out_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.log, indent=2) + "\n")
        tmp.replace(self.out_path)          # atomic: a crash never leaves a half-written run file

    def in_window(self):
        h = self.clock().hour
        return CALL_WINDOW_IST[0] <= h < CALL_WINDOW_IST[1]

    # -- one call attempt -----------------------------------------------------------------------
    def attempt(self, role, number, variables, label):
        """Places one call and returns an outcome dict. Never raises: provider failures come back
        as status 'provider_error' / 'unknown' so the run log always records what happened."""
        dialled = self.test_number if self.redirect else number
        self.say(f"\n-> {role} call: {label} ({number}" + (f", redirected to {dialled})" if dialled != number else ")"))
        meta = {"role": role, "label": label, "enquiry_id": self.log["enquiry"]["id"]}
        call_id = None
        for i in range(self.place_retries):
            try:
                call_id = self.provider.place_call(role, dialled, variables, meta)
                break
            except P.NotConfigured:
                raise
            except P.ProviderError as e:
                self.event("call_place_failed", role=role, number=number, try_no=i + 1, error=str(e))
                if i + 1 < self.place_retries:
                    self.sleep(2 ** i * 5)
        if call_id is None:
            self._provider_errors += 1
            return P.outcome(None, "provider_error", failure_reason="could not place call")
        self._provider_errors = 0
        self.event("call_placed", role=role, number=number, dialled=dialled, call_id=call_id)
        try:
            o = self.provider.wait(call_id)
        except (TimeoutError, P.ProviderError) as e:
            o = P.outcome(call_id, "unknown", failure_reason=str(e))
        if o.get("cost_inr") is None:
            o["cost_inr"] = round(o.get("minutes", 0) * self.est_inr_per_min, 2)
            o["cost_estimated"] = True
        o["at"] = now_iso()
        self.event("call_ended", role=role, number=number, call_id=call_id, status=o["status"],
                   minutes=o["minutes"], cost_inr=o["cost_inr"], failure_reason=o.get("failure_reason"))
        if o["status"] == P.NDNC:
            self.add_dnc(number, "provider reported TRAI NDNC")
        if o["data"].get("do_not_call"):
            self.add_dnc(number, f"{role} asked not to be called")
        return o

    # -- stages ---------------------------------------------------------------------------------
    def stop(self, result, status="finished"):
        self.log["result"], self.log["status"] = result, status
        if status == "finished":
            self.log["finished_at"] = now_iso()
        self.event("run_" + status, result=result)
        self.save()
        self.say(f"\n== {status}: {result} (log: {self.out_path})")
        return self.log

    def customer_stage(self):
        enq, cust = self.log["enquiry"], self.log["customer"]
        while not cust["done"]:
            if enq["phone"] in self.dnc():
                return "customer_on_dnc"
            if sum(1 for x in cust["attempts"] if x.get("call_id")) >= self.customer_attempts:
                return "customer_not_reached"
            if self.enforce_window and not self.in_window():
                return "paused:outside_calling_window"
            if cust["attempts"]:
                self.event("retry_wait", role="customer", seconds=self.retry_delay_s)
                self.sleep(self.retry_delay_s)
            o = self.attempt("customer", enq["phone"], {
                "customer_name": enq["name"], "locality": enq["locality"], "pincode": enq["pincode"],
                "start_date": enq["start_date"], "end_date": enq["end_date"],
                "enquiry_notes": enq.get("notes") or "none"}, enq["name"])
            cust["attempts"].append(o)
            self.save()
            if o["status"] == "provider_error":
                return "paused:provider_error"
            if o["status"] == "unknown":
                return "paused:customer_call_status_unknown"
            if o["status"] in RETRYABLE:
                continue
            cust["done"] = True
        final = cust["attempts"][-1]
        d = final["data"]
        if final["status"] == P.NDNC:
            return "customer_on_ndnc"
        if final["status"] != P.CONNECTED:
            return f"customer_call_failed:{final.get('failure_reason')}"
        if d.get("do_not_call"):
            return "customer_opted_out"
        if d.get("needs_kannada_callback"):
            return "customer_needs_kannada_callback"
        if d.get("callback_time") and not d.get("still_needs_service"):
            return f"customer_callback_requested:{d['callback_time']}"
        if not d.get("still_needs_service"):
            return "customer_no_longer_needs_service"
        freq = d.get("visit_frequency") if d.get("visit_frequency") in FREQUENCIES else "unknown"
        self.log["job"] = {
            "customer_area": ", ".join(str(x) for x in (d.get("area") or enq["locality"], d.get("landmark")) if x),
            "pincode": enq["pincode"],
            "start_date": self._date_or(d.get("start_date"), enq["start_date"]),
            "end_date": self._date_or(d.get("end_date"), enq["end_date"]),
            "visit_frequency": freq,
            "plant_count": d.get("plant_count") or enq.get("notes") or "not sure",
            "access_arrangement": d.get("access_arrangement") or "customer will arrange",
            "customer_budget_per_visit_inr": d.get("budget_per_visit_inr"),
        }
        self.save()
        return None

    @staticmethod
    def _date_or(value, fallback):
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError:
            return fallback

    def gardener_vars(self, g):
        job = self.log["job"]
        # Only the area goes to gardeners -- never the customer's name, number or address.
        return {"gardener_name": g["name"], "customer_area": job["customer_area"], "pincode": job["pincode"],
                "start_date": job["start_date"], "end_date": job["end_date"],
                "visit_frequency": job["visit_frequency"].replace("_", " "),
                "plant_count": job["plant_count"], "access_arrangement": job["access_arrangement"]}

    def available(self):
        return [g for g in self.log["gardeners"].values()
                if g["attempts"] and g["attempts"][-1]["status"] == P.CONNECTED
                and g["attempts"][-1]["data"].get("available")]

    def gardener_stage(self):
        enq, log = self.log["enquiry"], self.log
        if not log["gardeners"]:
            ranked = rank_gardeners(read_gardeners(self.gardeners_path), enq["pincode"], enq.get("lat"),
                                    enq.get("lng"), blocked=self.dnc())[:self.max_gardeners]
            for g in ranked:
                log["gardeners"][g["phone"]] = {"name": g["name"], "phone": g["phone"], "pincode": g["pincode"],
                                                "distance_km": g["distance_km"], "rank_basis": g["rank_basis"],
                                                "attempts": [], "done": False}
            self.event("gardeners_ranked", count=len(ranked), order=[g["name"] for g in ranked])
            self.save()
            if not ranked:
                return "no_gardeners_in_range"
        for pass_no in range(self.gardener_attempts):
            todo = [g for g in log["gardeners"].values() if not g["done"] and len(g["attempts"]) <= pass_no]
            if pass_no and todo:
                self.event("retry_wait", role="gardener", seconds=self.retry_delay_s, count=len(todo))
                self.sleep(self.retry_delay_s)
            for g in todo:
                if len(self.available()) >= self.want:
                    return None
                if g["phone"] in self.dnc():
                    g["done"] = True
                    self.event("skipped_dnc", number=g["phone"])
                    continue
                if self.enforce_window and not self.in_window():
                    return "paused:outside_calling_window"
                o = self.attempt("gardener", g["phone"], self.gardener_vars(g), g["name"])
                g["attempts"].append(o)
                if o["status"] == "provider_error" and \
                        self._provider_errors >= self.max_consecutive_provider_errors:
                    self.save()
                    return "paused:provider_error"
                if o["status"] not in RETRYABLE | {"provider_error"} or \
                        len(g["attempts"]) >= self.gardener_attempts:
                    g["done"] = True
                d = o["data"]
                self.say(f"   {o['status']}: available={d.get('available')} "
                         f"rate={d.get('price_per_visit_inr')} referral={d.get('referral') or '-'}")
                self.save()
        return None

    def handoff(self):
        enq, job = self.log["enquiry"], self.log["job"]
        visits = visits_for(job["start_date"], job["end_date"], job["visit_frequency"])
        budget = job.get("customer_budget_per_visit_inr")
        offers = []
        for g in self.available():
            d = g["attempts"][-1]["data"]
            rate = d.get("price_per_visit_inr")
            offer = {"gardener": g["name"], "contact_name": d.get("contact_name") or g["name"],
                     "contact_number": d.get("contact_number") or g["phone"],
                     "can_start_on_date": d.get("can_start_on_date"), "distance_km": g["distance_km"]}
            if isinstance(rate, (int, float)) and rate > 0:
                offer.update(price_job(int(rate), visits, self.fee_per_visit, self.fee_pct, self.min_revenue))
                offer["within_budget"] = None if not budget else offer["customer_price_per_visit"] <= budget
            else:
                offer["needs_rate_confirmation"] = True
            offers.append(offer)
        offers.sort(key=lambda o: (o.get("customer_price_per_visit") is None, o.get("customer_price_per_visit") or 0))
        self.log["offers"] = offers
        self.log["referrals"] = sorted({str(a["data"]["referral"]) for g in self.log["gardeners"].values()
                                        for a in g["attempts"] if a["data"].get("referral")})
        self.log["whatsapp"] = whatsapp_drafts(enq, job, offers)
        self.event("handoff_ready", offers=len(offers), referrals=len(self.log["referrals"]))

        best = next((o for o in offers if "customer_total" in o), None)
        cost = self.metrics()["call_cost_inr"]
        self.log["economics"] = {
            "call_cost_inr": cost,
            "best_offer_revenue_inr": best["our_revenue"] if best else 0,
            "contribution_if_booked_inr": round((best["our_revenue"] if best else 0) - cost, 2),
            "customer_total_inr": best["customer_total"] if best else None,
            "note": "contribution = our fee x visits - call cost; excludes payment fees and refunds",
        }

    def metrics(self):
        calls = self.log["customer"]["attempts"] + [a for g in self.log["gardeners"].values() for a in g["attempts"]]
        placed = [c for c in calls if c.get("call_id")]
        connected = [c for c in calls if c["status"] == P.CONNECTED]
        return {"calls_placed": len(placed), "calls_connected": len(connected),
                "connect_rate": round(len(connected) / len(placed), 2) if placed else None,
                "call_minutes": round(sum(c.get("minutes") or 0 for c in calls), 2),
                "call_cost_inr": round(sum(c.get("cost_inr") or 0 for c in calls), 2),
                "gardeners_called": sum(1 for g in self.log["gardeners"].values() if g["attempts"]),
                "gardeners_available": len(self.available()),
                "provider_errors": sum(1 for c in calls if c["status"] == "provider_error")}

    # -- entry points ---------------------------------------------------------------------------
    def start(self, enq):
        clean, errors = validate_enquiry(enq, self.today)
        if errors:
            raise ValueError("invalid enquiry: " + "; ".join(errors))
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self._open(clean["id"])
        if self.out_path.exists():
            raise FileExistsError(f"run {clean['id']} already exists -- use resume()")
        self.log = {"enquiry": clean, "mode": self.mode, "provider": self.provider.name, "started_at": now_iso(),
                    "status": "running", "customer": {"attempts": [], "done": False}, "job": None,
                    "gardeners": {}, "offers": [], "result": None}
        self.event("run_started", mode=self.mode, provider=self.provider.name)
        return self._run()

    def resume(self, enquiry_id):
        self._open(enquiry_id)
        self.log = json.loads(self.out_path.read_text())
        if self.log.get("status") == "finished":
            raise ValueError(f"run {enquiry_id} already finished: {self.log['result']}")
        self.log["status"] = "running"
        self.event("run_resumed", previous=self.log.get("result"))
        return self._run()

    def _open(self, enquiry_id):
        self.out_path = self.runs_dir / f"{enquiry_id}.json"
        self.events_path = self.runs_dir / f"{enquiry_id}.events.jsonl"

    def _run(self):
        self.save()
        if not self.log["job"]:
            stopped = self.customer_stage()
            if stopped:
                return self.stop(stopped.split("paused:")[-1], "paused" if stopped.startswith("paused:") else "finished")
        stopped = self.gardener_stage()
        if stopped and stopped.startswith("paused:"):
            return self.stop(stopped.split(":", 1)[1], "paused")
        self.handoff()
        n = len(self.log["offers"])
        result = stopped or (f"{n}_gardeners_available" if n else "no_gardener_available")
        self.stop(result)
        for o in self.log["offers"]:
            self.say(f"   {o['gardener']} / {o['contact_name']} {o['contact_number']}  "
                     f"customer Rs {o.get('customer_price_per_visit', '?')}/visit "
                     f"(gardener {o.get('gardener_rate_per_visit', '?')} + fee {o.get('our_fee_per_visit', '?')})")
        for w in self.log["whatsapp"]:
            self.say(f"\nWhatsApp to {w['to']} ({w['who']}):\n{w['link']}")
        return self.log


def wa_link(number, text):
    return f"https://wa.me/{number.lstrip('+')}?text={urllib.parse.quote(text)}"


def whatsapp_drafts(enq, job, offers):
    """Drafts only -- a human opens each link and presses send."""
    drafts = []
    priced = [o for o in offers if "customer_total" in o]
    if not priced:
        text = (f"Hi {enq['name']}, this is Water My Plant. We're lining up a gardener near {job['customer_area']} "
                f"for {job['start_date']} to {job['end_date']} and will confirm the price here shortly.")
    else:
        lines = [f"{i}. {o['contact_name']}: Rs {o['customer_price_per_visit']}/visit, "
                 f"{o['visits']} visits" + (f" + Rs {o['booking_fee']} booking fee" if o["booking_fee"] else "") +
                 f" = Rs {o['customer_total']}" for i, o in enumerate(priced[:3], 1)]
        text = (f"Hi {enq['name']}, this is Water My Plant. We found gardeners near {job['customer_area']} "
                f"for {job['start_date']} to {job['end_date']} ({job['visit_frequency'].replace('_', ' ')}):\n"
                + "\n".join(lines) +
                f"\nReply {' or '.join(str(i) for i in range(1, len(lines) + 1))} to book. We confirm the gardener once the booking is paid by UPI. "
                "Reply STOP if you don't want further messages.")
    drafts.append({"who": "customer", "to": enq["phone"], "text": text, "link": wa_link(enq["phone"], text)})
    for o in priced[:3]:
        t = (f"Namaste {o['contact_name']} ji, Water My Plant se. {job['customer_area']} mein "
             f"{job['start_date']} se {job['end_date']} tak plants ko paani dena hai "
             f"({job['visit_frequency'].replace('_', ' ')}, {o['visits']} visits, Rs {o['gardener_rate_per_visit']}/visit). "
             "Customer confirm karte hi hum address aur details bhejenge.")
        drafts.append({"who": "gardener", "to": o["contact_number"], "text": t, "link": wa_link(o["contact_number"], t)})
    return drafts


# ---------------------------------------------------------------------------------------------
# CLI

def happy_path_mock(gardeners_path, pincode):
    """Built-in mock for --provider mock without --scenario: customer confirms, first gardener
    doesn't pick up, second is available, third isn't (gives a referral), fourth is available."""
    ranked = rank_gardeners(read_gardeners(gardeners_path), pincode)
    script, outcomes = {}, [
        [P.NO_ANSWER],
        [P.answered({"available": True, "can_start_on_date": True, "price_per_visit_inr": 100,
                     "contact_name": "Anil", "contact_number": "", "do_not_call": False}, minutes=1.6)],
        [P.answered({"available": False, "referral": "Green Nursery, Kengeri", "do_not_call": False}, minutes=1.1)],
        [P.answered({"available": True, "can_start_on_date": True, "price_per_visit_inr": 120,
                     "contact_name": "Manju", "contact_number": "", "do_not_call": False}, minutes=1.8)],
    ]
    for g, o in zip(ranked, outcomes):
        script[g["phone"]] = o
    return script


def default_mock(gardeners_path, enq):
    """MockProvider for an enquiry with no scenario file: happy_path_mock, plus the customer
    answering and confirming what they asked for."""
    provider = P.MockProvider(happy_path_mock(gardeners_path, str(enq.get("pincode", "560056"))))
    if enq.get("phone"):
        provider.script[e164(enq["phone"])] = [P.answered({
            "still_needs_service": True, "start_date": enq.get("start_date"), "end_date": enq.get("end_date"),
            "area": enq.get("locality"), "landmark": "near the BDA park", "plant_count": enq.get("notes") or "20 pots",
            "visit_frequency": "alternate_days", "access_arrangement": "key with security",
            "budget_per_visit_inr": 150, "do_not_call": False}, minutes=2.4)]
    return provider


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", help="enquiry JSON (name, phone, locality, pincode, start_date, end_date, "
                                  "notes, consent_source, optional lat, lng)")
    p.add_argument("--name"); p.add_argument("--phone"); p.add_argument("--locality"); p.add_argument("--pincode")
    p.add_argument("--start", dest="start_date"); p.add_argument("--end", dest="end_date"); p.add_argument("--notes")
    p.add_argument("--lat", type=float); p.add_argument("--lng", type=float)
    p.add_argument("--consent", dest="consent_source", help=f"how the customer asked us: {sorted(CONSENT_SOURCES)}")
    p.add_argument("--gardeners", default=str(ROOT / "gardeners.csv"), help="roster CSV (default gardeners.csv)")
    p.add_argument("--resume", metavar="ENQUIRY_ID", help="continue a paused run from runs/<id>.json")
    p.add_argument("--provider", choices=["sarvam", "retell", "mock"], default="sarvam")
    p.add_argument("--scenario", help="mock scenario JSON (see providers.mock_from_file)")
    p.add_argument("--dry-run", action="store_true", help="alias for --provider mock")
    p.add_argument("--live", action="store_true", help="call the real numbers")
    p.add_argument("--max-gardeners", type=int, default=6)
    p.add_argument("--want", type=int, default=2, help="stop after this many available gardeners")
    p.add_argument("--retry-delay", type=int, default=300, help="seconds between retries")
    p.add_argument("--fee-per-visit", type=int, default=30, help="minimum fee we add per visit (INR)")
    p.add_argument("--fee-pct", type=int, default=20, help="fee as %% of gardener rate, if higher")
    p.add_argument("--min-revenue", type=int, default=99, help="minimum we earn per booking; short jobs get a "
                                                                 "booking fee to reach it (INR)")
    p.add_argument("--yes", action="store_true", help="skip the --live confirmation prompt")
    a = p.parse_args()
    if a.dry_run:
        a.provider = "mock"

    enq = json.loads(Path(a.file).read_text()) if a.file else {}
    for k in ("name", "phone", "locality", "pincode", "start_date", "end_date", "notes", "lat", "lng", "consent_source"):
        if getattr(a, k) is not None:
            enq[k] = getattr(a, k)

    roster = Path(a.gardeners)
    if not roster.exists():
        sys.exit(f"{roster.name} missing -- copy gardeners.example.csv to gardeners.csv and add real gardeners")
    try:
        if a.provider == "mock":
            provider = P.mock_from_file(a.scenario) if a.scenario else default_mock(roster, enq)
        elif a.provider == "sarvam":
            provider = P.SarvamProvider()
        else:
            provider = P.RetellProvider()
    except (P.NotConfigured, SystemExit) as e:
        sys.exit(f"{a.provider} not ready: {e}\nUse --provider mock to exercise the flow meanwhile.")

    mode = "live" if a.live else "test"
    pipe = Pipeline(provider, mode=mode, gardeners_path=roster, max_gardeners=a.max_gardeners, want=a.want,
                    retry_delay_s=0 if a.provider == "mock" else a.retry_delay,
                    fee_per_visit=a.fee_per_visit, fee_pct=a.fee_pct, min_revenue=a.min_revenue)
    try:
        if a.resume:
            pipe.resume(a.resume)
            return
        clean, errors = validate_enquiry(enq)
        if errors:
            p.error("; ".join(errors))
        if mode == "live" and a.provider != "mock" and not a.yes:
            if input(f"LIVE: call {clean['name']} ({clean['phone']}) and up to {a.max_gardeners} gardeners? "
                     "type yes: ").strip() != "yes":
                sys.exit("aborted")
        pipe.start(clean)
    except P.NotConfigured as e:
        sys.exit(f"{a.provider} not ready: {e}")
    except (ValueError, FileExistsError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
