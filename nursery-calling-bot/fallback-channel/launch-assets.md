# Non-Call Fallback Channel — Launch-Ready Assets

**Date:** 2026-09-17
**Status:** Copy/design/measurement plan only. Nothing printed, displayed, sent, or posted yet — this
turns the experiment design in `docs/trai-dlt-compliance-2026-09-17.md` Section 3 into assets a founder
could hand to a printer or paste into WhatsApp Business today, with no TRAI/DLT exposure (everything
here is opt-in — the nursery, gardener, or customer initiates contact; nothing is sent to them first).

**Why this now matters more than "a nice parallel option":** the compliance research pass today
(`docs/trai-dlt-compliance-2026-09-17.md` Section 2 update) found that even a fully DLT-registered
140-series setup would not by itself make it legal to cold-call the desk-researched prospect list,
because promotional calls require the recipient's prior consent. **This opt-in channel is therefore the
only currently-viable near-term acquisition path for gardener supply, not a fallback to a call-based
plan that's merely delayed.**

---

## 1. Partner-card brief (physical card, left at/with a nursery's permission)

### Print specs
- **Size:** standard business-card-adjacent, 3.5" × 5" (postcard-ish — big enough to hold a QR code
  legibly and a few lines of text, small enough to sit on a counter without being intrusive).
- **Material:** matte cardstock, 300gsm — durable enough to survive being handled/left on a nursery
  counter for weeks.
- **Quantity for this batch:** 14 unique cards (one per prospect in
  `nursery-calling-bot/prospects/bangalore-jagajyothi-layout-nurseries.csv`), each with its **own QR
  code** (see Section 4, tracking) — do not print one generic card for all 14 locations, or per-nursery
  source tracking is lost.

### Front-side copy (Hinglish primary, matches the voice-script's tone; English secondary line for
readers who prefer it)

```
🌱 Gardener ya Mali ki jaan-pehchaan hai?
Extra kamaane ka mauka!

Hum local plant-watering customers ko trusted
gardeners se connect karte hain — watermyplant.in

WhatsApp karein: [QR CODE]
Ya seedha message karein: 8087404471

(Know a gardener or mali looking for extra work?
We connect local plant-watering customers with
trusted gardeners — scan to WhatsApp us.)
```

### Back-side copy (for the nursery owner, explaining why the card is worth displaying)

```
Namaste! Yeh card free hai apne counter par rakhne ke liye.

Agar koi customer ya gardener isse WhatsApp karta hai,
hum unhe seedha connect karte hain — aapko kuch nahi karna,
bas card ko dikhte rehne dein.

Koi cost nahi, koi commitment nahi.
Sawaal ho toh: 8087404471 par WhatsApp karein.

(This card is free to display at your counter. If a
customer or gardener WhatsApps us from it, we connect
them directly — nothing required from you beyond keeping
it visible. No cost, no commitment.)
```

### Placement instructions (for whoever delivers the cards — founder or a trusted contact)

1. Ask the nursery owner/staff directly for permission to leave the card at the counter — do not leave
   it unattended without asking, even though it's a low-friction physical object (this keeps the
   relationship consent-based on both the display and the future WhatsApp contact).
2. Prioritize nurseries confirmed **open** and phone-verified in `SOURCES.md`'s Maps-lookup pass
   (rows 2, 5, 9, 12, 13 highest confidence; rows 1, 3 medium confidence) — do not spend a visit on
   rows already confirmed **permanently closed** (rows 6, 8).
3. Note the delivery date and nursery name in a simple log (a new column in the prospects CSV,
   `partner_card_delivered_date`, is the natural place — not yet added since no card has been delivered).

---

## 2. QR code destination — WhatsApp click-to-chat with a pre-filled message

Each nursery's QR code encodes a **distinct** `wa.me` link with a pre-filled message containing that
nursery's tracking code (see Section 4), e.g. for prospect id 5 (Noojibail Nursery):

```
https://wa.me/918087404471?text=Hi%2C%20I%27m%20messaging%20about%20the%20gardener%20card%20at%20Noojibail%20Nursery%20%5BREF-05%5D
```

Decoded, the pre-filled message reads: *"Hi, I'm messaging about the gardener card at Noojibail Nursery
[REF-05]"* — the sender can edit or delete this before sending, but a default pre-fill maximizes the
chance the reference code survives so the source can be attributed.

**No separate landing page is needed or recommended for the QR itself** — routing straight to WhatsApp
(a channel that already exists at `wa.me/918087404471` per `docs/pilot-economics-2026-09-10.md`) avoids
building/hosting a new page for a 14-card pilot batch. If this channel scales past this batch, a simple
landing page per Section 5 below becomes worth building.

---

## 3. WhatsApp opt-in reply template (watermyplant.in's side, sent only after the gardener/nursery
messages in first — never sent unsolicited)

```
Namaste! 🌱 Watermyplant.in mein aapka swagat hai.

Hum Bangalore mein plant-watering customers ko local
gardeners se connect karte hain jab woh kuch dino ke liye
bahar jaate hain.

Kya aap gardener ka kaam karte hain, ya kisi ko jaante hain
jo interested ho? Agar haan, toh yeh batayein:
1️⃣ Naam
2️⃣ Area/locality
3️⃣ Rate (per din ya per visit)
4️⃣ Available days/hours

Hum aapki details apne trusted-gardener list mein rakhenge
aur jab koi customer aas-paas hoga, aapse WhatsApp par
contact karenge. Koi cost nahi.

(We connect Bangalore plant-watering customers with local
gardeners for short trips. Are you a gardener, or do you
know one who's interested? If so, share your name, area,
rate, and availability — we'll add you to our trusted list
and reach out on WhatsApp when a nearby customer needs
someone. No cost.)
```

**Consent capture, built into this template:** the gardener volunteering their name/area/rate/hours in
reply to this message — sent only after they messaged in first — is the explicit opt-in consent record
for both the immediate qualification purpose and (per
`docs/trai-dlt-compliance-2026-09-17.md` Section 2's new DPDP flag) for storing that personal data
in the gardener bench list. Log the WhatsApp conversation timestamp as the consent record.

---

## 4. Tracking mechanism (so this channel's conversion is measurable, per-nursery)

| Field | Where it lives | Purpose |
|---|---|---|
| `partner_card_ref_code` | New column, `nursery-calling-bot/prospects/bangalore-jagajyothi-layout-nurseries.csv` (e.g. `REF-01` … `REF-14`, matching the existing `id` column) | Ties every inbound WhatsApp message back to the specific nursery/card that generated it |
| `partner_card_delivered_date` | Same CSV | Start-of-window marker for measuring response time |
| Inbound WhatsApp log (manual, until volume justifies a CRM) | A simple sheet: date, ref code, sender type (nursery staff / gardener / customer), outcome | Feeds the funnel in Section 5 below |

---

## 5. Measurable success criteria (a funnel, comparable to the calling-bot funnel)

Mirrors the structure of `docs/nursery-outreach-funnel-2026-09-17.md` so the two channels can be
compared apples-to-apples once both have real data, per `SOURCES.md`'s note that this was a design
goal from the start.

```
Cards placed / QR displayed
        │  ▼ scan-through rate
Scans / WhatsApp opens
        │  ▼ message-sent rate
Inbound WhatsApp messages received
        │  ▼ qualification rate (same rubric as the calling bot)
Qualified leads
        │  ▼ capture rate
Contact captured & confirmed
        │  ▼ follow-up conversion
Gardener bench entries
```

| Stage | Target (pilot threshold) | Basis |
|---|---|---|
| Scan-through rate (card displayed → scanned) | **1–5%** for passive counter placement; treat 5%+ as a strong result | [BENCHMARK] general QR flyer/poster benchmarks: passive placements typically run 1–5% scan rate, vs. 15–35% for high-intent/staffed placements. A nursery counter with the owner's verbal endorsement sits between these — closer to the passive end unless the owner actively mentions it to customers. Source: [Uniqode — QR Code Marketing Tips & Benchmarks](https://www.uniqode.com/blog/qr-code-marketing-tips/qr-code-campaigns-high-conversion), [QRLynx — QR Code Scan Benchmarks 2026](https://qrlynx.com/blog/qr-code-scan-benchmarks-2026). |
| Message-sent rate (scan → WhatsApp message actually sent) | **[ASSUMPTION] ~50–70%** | No public benchmark found for this specific step; a scan that opens WhatsApp with a pre-filled message has low friction to actually send, so this should be a high-conversion step relative to the scan itself — treat as an early hypothesis to replace with real data after the first ~2 weeks. |
| Qualification rate (message → qualified) | Same **10–30%** range as the calling-bot's revised sensitivity range (`docs/funnel-sensitivity-analysis-2026-09-17.md`) | This step doesn't depend on the acquisition channel, so reuse the same rubric/range rather than inventing a new one. |
| Capture / follow-up conversion | Same as calling-bot funnel (100% / 50%) | Same downstream process regardless of how the lead arrived. |

**Overall success criterion for this 14-card pilot batch (proposed):** at least **1 qualified gardener
lead within 4 weeks** of card placement. Given the 1–5% scan-rate benchmark, 14 cards, and assuming
modest foot traffic (illustrative, not measured — **[ASSUMPTION]**: ~20–50 customers/day per nursery
counter), this is a low-volume channel by design — it should be judged on cost (near-zero) and
regulatory safety (fully consent-based), not on matching the calling bot's theoretical throughput.
**If zero qualified leads arrive from all 14 cards after 4 weeks,** that's a real signal to revisit
placement/copy before assuming the channel doesn't work — check card visibility and whether owners are
actually keeping them out, first.

---

## 6. In-person visit talking points (for the 3–5 highest-priority nurseries, per the compliance doc's
Section 3 option 2 — a live conversation, zero TCCCPR exposure since it's not a telecom communication)

Short, so it doesn't read as a script to memorize:

1. "Hi, main watermyplant.in se hoon — hum log Bangalore mein plant-watering customers ko local
   gardeners se connect karte hain."
2. "Kya aapke paas koi gardener/mali hai jo extra kaam ke liye available ho, ya jaan-pehchaan mein koi
   hai?"
3. If yes → "Kya main unka number le sakta/sakti hoon, ya aap unhe hamara WhatsApp number de sakte
   hain?" (prefer getting the *gardener's* consent to be contacted directly, over taking their number
   third-hand without their knowledge — ask the nursery to have the gardener message in themselves
   where possible, keeping the opt-in principle intact even in person).
4. Leave a partner card either way, with permission (Section 1).

Target list for this visit, ranked by confidence + proximity per `SOURCES.md`: Noojibail Nursery (row
5, confirmed open, closest high-confidence match), the Fruit Plant Nursery already-had-a-number row
(row 2), Hasiru Agro (row 13), and Green Nursery / Green Garden Nursery (row 9, name to be confirmed
on arrival per the existing caveat).
