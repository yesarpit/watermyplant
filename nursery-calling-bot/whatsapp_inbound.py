"""WhatsApp Cloud API inbound messages -> enquiries (used by intake.py's /webhooks/whatsapp).

Meta posts a JSON payload signed with the app secret (X-Hub-Signature-256). For each text message:
  STOP / UNSUBSCRIBE           -> the sender goes on do-not-call.txt, nothing is queued
  anything else                -> appended to the sender's conversation in <queue>/held/<wa_id>.json and
                                  re-parsed as a whole, so details can arrive over several messages.
                                  Once pincode, locality, both dates and explicit consent to a *call*
                                  are there, it becomes an enquiry (consent_source=whatsapp_enquiry).
                                  Until then it stays held with the missing items and a reply draft.
Replies are drafts only: sending them needs a Meta access token (founder).
"""
import hashlib
import hmac
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import enquiry_pipeline as EP

MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                      "nov", "dec"), 1)}
MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
DATE_PATTERNS = [
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + MON + r"(?:\s+(\d{4}))?", re.I),
     lambda m: (int(m[3]) if m[3] else None, MONTHS[m[2].lower()], int(m[1]))),
    (re.compile(r"\b" + MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(\d{4}))?", re.I),
     lambda m: (int(m[3]) if m[3] else None, MONTHS[m[1].lower()], int(m[2]))),
    (re.compile(r"\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2}|\d{4}))?\b"),       # Indian order: day/month
     lambda m: ((int(m[3]) + 2000 if len(m[3]) == 2 else int(m[3])) if m[3] else None, int(m[2]), int(m[1]))),
]
PINCODE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
LOCALITY_LINE = re.compile(r"^\s*(?:locality|area|address|location)\s*[:\-]\s*(.+)$", re.I | re.M)
LOCALITY_PHRASE = re.compile(r"\b(?:in|at|near)\s+((?:[A-Z][A-Za-z]+\.?\s?){1,4})")
NO_CALL = re.compile(r"\b(?:don'?t|do not|dont|no|never|can'?t|cannot)\b[^.\n]{0,15}\bcall", re.I)
CALL_OK = re.compile(r"\b(?:ok(?:ay)?|fine|happy|yes|can|may)\b[^.\n]{0,20}\bcall|\bcall me\b|"
                     r"\bcall (?:is |me is )?(?:ok|fine)\b", re.I)
STOP_WORDS = {"stop", "unsubscribe", "stop all", "opt out", "optout"}


def signature_ok(secret, raw, header):
    """X-Hub-Signature-256: 'sha256=' + hex HMAC-SHA256 of the raw request body, keyed by the app secret."""
    if not secret or not header or not header.startswith("sha256="):
        return False
    want = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, header[len("sha256="):].strip().lower())


def sign(secret, raw):
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def text_messages(payload):
    """Yields (message_id, wa_id, profile_name, text, unix_ts) for every text message in a webhook payload.
    Status callbacks, media and other message types are skipped."""
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            names = {c.get("wa_id"): ((c.get("profile") or {}).get("name") or "") for c in value.get("contacts") or []}
            for m in value.get("messages") or []:
                if m.get("type") != "text" or not m.get("id") or not m.get("from"):
                    continue
                yield (m["id"], m["from"], names.get(m["from"], ""), (m.get("text") or {}).get("body") or "",
                       int(m.get("timestamp") or 0))


def parse_dates(text, today):
    found = []
    for rx, build in DATE_PATTERNS:
        for m in rx.finditer(text):
            if any(m.start() < e and s < m.end() for s, e, _ in found):
                continue
            try:
                y, mo, d = build(m)
                found.append((m.start(), m.end(), (y, mo, d)))
            except (KeyError, ValueError):
                pass
    out = []
    for _, _, (y, mo, d) in sorted(found):
        try:
            if y is None:                       # no year given: the next such date on or after today
                y = today.year
                if date(y, mo, d) < today:
                    y += 1
                if out and date(y, mo, d) < out[-1]:
                    y += 1
            out.append(date(y, mo, d))
        except ValueError:
            continue
    return out


def parse_locality(text, pincode):
    m = LOCALITY_LINE.search(text)
    if m:
        loc = PINCODE.sub("", m[1]).strip(" ,.-")
        if loc:
            return loc[:80]
    m = LOCALITY_PHRASE.search(text)
    if m:
        return m[1].strip(" .")[:80]
    return f"pincode {pincode}" if pincode else ""


def call_consent(text):
    if NO_CALL.search(text):
        return False
    return bool(CALL_OK.search(text))


def parse(text, today):
    """Everything we could read out of a conversation's text, plus what's still missing."""
    pins = [p for p in PINCODE.findall(text)]
    pincode = next((p for p in pins if p.startswith(EP.SERVICE_PINCODE_PREFIXES)), pins[0] if pins else "")
    dates = parse_dates(text, today)
    fields = {"pincode": pincode, "locality": parse_locality(text, pincode),
              "start_date": dates[0].isoformat() if dates else "",
              "end_date": dates[1].isoformat() if len(dates) > 1 else (dates[0].isoformat() if dates else ""),
              "call_consent": call_consent(text)}
    missing = [label for k, label in (("pincode", "pincode"), ("start_date", "dates")) if not fields[k]]
    if not fields["call_consent"]:
        missing.append("call_consent")
    return fields, missing


def reply_draft(name, missing):
    asks = {"pincode": "your area and 6-digit pincode",
            "dates": "the dates you'll be away (e.g. 2 Oct to 6 Oct)",
            "call_consent": "whether it's OK for us to call you on this number to confirm details (reply \"ok to call\")"}
    need = [asks[m] for m in missing if m in asks]
    hi = f"Hi {name}, " if name else "Hi, "
    return (hi + "thanks for messaging Water My Plant. To find a gardener near you we need " +
            "; ".join(need) + ". Reply STOP any time to opt out.")


class Conversations:
    """Per-sender conversation state in <queue>/held/, plus the set of message ids already handled."""
    def __init__(self, queue_dir):
        self.dir = Path(queue_dir) / "held"        # created on first use, so a form-only queue stays flat
        self.seen_path = self.dir / "seen-message-ids.txt"

    def seen(self, message_id):
        return self.seen_path.exists() and message_id in self.seen_path.read_text().split()

    def mark_seen(self, message_id):
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.seen_path.open("a") as f:
            f.write(message_id + "\n")

    def path(self, wa_id):
        return self.dir / f"{re.sub(r'[^0-9]', '', wa_id)}.json"

    def load(self, wa_id):
        p = self.path(wa_id)
        return json.loads(p.read_text()) if p.exists() else {"wa_id": wa_id, "texts": [], "message_ids": []}

    def save(self, convo):
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self.path(convo["wa_id"])
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(convo, indent=2) + "\n")
        tmp.replace(p)

    def close(self, wa_id):
        self.path(wa_id).unlink(missing_ok=True)


def handle_message(convos, message_id, wa_id, name, text, ts, today):
    """One inbound text -> an action dict:
      {"kind": "duplicate"}                             already handled (Meta re-delivered it)
      {"kind": "stop", "phone"}                         opt-out: caller adds phone to do-not-call
      {"kind": "held", "missing", "reply_draft"}        not enough yet
      {"kind": "enquiry", "enquiry"}                    ready to validate + queue (caller closes the convo)
    """
    if convos.seen(message_id):
        return {"kind": "duplicate", "message_id": message_id}
    convos.mark_seen(message_id)
    try:
        phone = EP.e164(wa_id)
    except ValueError:
        return {"kind": "ignored", "message_id": message_id, "reason": "not an Indian number"}
    if text.strip().lower().strip(".! ") in STOP_WORDS:
        convos.close(wa_id)
        return {"kind": "stop", "phone": phone, "message_id": message_id}

    convo = convos.load(wa_id)
    convo["name"] = (name or convo.get("name") or "WhatsApp customer")[:60]
    convo["texts"].append(text[:1000])
    convo["message_ids"].append(message_id)
    fields, missing = parse("\n".join(convo["texts"]), today)
    convo.update(parsed=fields, missing=missing, reply_draft=reply_draft(convo["name"], missing) if missing else None,
                 updated_at=datetime.fromtimestamp(ts or 0, timezone.utc).isoformat(timespec="seconds"))
    convos.save(convo)
    if missing:
        return {"kind": "held", "phone": phone, "missing": missing, "reply_draft": convo["reply_draft"],
                "message_id": message_id}
    stamp = datetime.fromtimestamp(ts, EP.IST).strftime("%Y%m%d-%H%M%S") if ts else "undated"
    enquiry = {"id": f"wa-{stamp}-{phone[-4:]}", "name": convo["name"], "phone": phone,
               "locality": fields["locality"], "pincode": fields["pincode"],
               "start_date": fields["start_date"], "end_date": fields["end_date"],
               "notes": ("[whatsapp] " + " | ".join(convo["texts"]))[:500], "consent_source": "whatsapp_enquiry"}
    return {"kind": "enquiry", "phone": phone, "enquiry": enquiry, "message_id": message_id}
