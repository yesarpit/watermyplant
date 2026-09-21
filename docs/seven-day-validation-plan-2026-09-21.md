# Seven-Day Consent-Based Validation Plan — 2026-09-21

Directive (manager, 2026-09-21): no Retell purchase, no waiting on TRAI DLT; opt-in funnel is the primary path.
**Status:** plan + assets built locally. Nothing deployed, posted, or sent yet (see "Needs your OK").

## Test target (7 days from launch)
- **≥10 qualified household opt-ins** — qualified = in/adjacent to the pilot cluster, ≥1 stated trip within 2 months, stated budget ≥ test price floor, opted in via WhatsApp themselves.
- **≥3 explicit paid-pilot commitments** — customer replies "yes" to a written offer at the test price (payment link/UPI ask only after founder approves collecting money).

## Price satisfying route-density economics
From `docs/pilot-economics-2026-09-10.md` (₹250/route payout, ₹1.5 transport **[ASSUMPTION]**): ₹20/visit needs ~13 stops per route — unrealistic at pilot density. Test offers:

| Offer | Price/visit | Break-even stops/route |
|---|---|---|
| A: Trip pack (5 visits, min) | ₹60 | ~4-5 |
| B: Trip pack (5 visits, min) | ₹80 | ~3 |
Commitment counts only at ≥₹60/visit. Ask both variants (alternate per lead) to learn price sensitivity; the form's budget field pre-screens.

## Funnel (built)
- `join.html` (noindex, uses existing styles + Umami): locality, plants, travel timing, budget, explicit consent checkbox → prefilled WhatsApp message carrying `[ref:code]`. Zero-cost, static.
- Per-channel codes: `join.html?ref=<code>`; list in `validation-7day/ref-codes.csv`.
- Daily log: `validation-7day/daily-log.csv` (channel, impressions, visits, opt-ins, locality, willingness to pay, spend, cost per qualified opt-in). Visits/events from Umami; opt-ins tallied from WhatsApp inbox by ref tag.

## Minimum viable geographic cluster
≥8 committed households within ~1.5 km walking/cycling radius (≈ one route), with ≥4 needing visits on overlapping dates in the same 2-week window. Below that, ₹60+ pricing is required and per-route margin is negative.

## Go / pivot / stop (evaluate at end of day 7)
- **GO:** ≥10 qualified opt-ins AND ≥3 paid commitments AND ≥6 of qualified opt-ins in the cluster radius. → onboard 1 gardener via opt-in channel, run first route.
- **PIVOT:** 5-9 qualified opt-ins or 1-2 commitments, or demand present but price median < ₹60 → test bundled/recurring offer, widen to adjacent locality, or a per-plant-count price; extend 7 days once.
- **STOP:** <5 qualified opt-ins AND 0 commitments after ≥150 visits (or all permitted channels exhausted). → shelve locality pilot; revisit positioning before spending anything.

## Daily routine
Post only via permitted channels → log row → check Umami → reply to WhatsApp opt-ins (only those who messaged first) → update `status.json`.

## Founder-review queue (skipped, moved on to next permitted channel)
1. Deploy `join.html` (push to main / GitHub Pages) — outward-facing.
2. Any community/RWA/Nextdoor post — needs rules + admin OK.
3. Google Business Profile (login), printed partner cards (print + nursery permission), collecting payments (UPI link), WhatsApp Business broadcast setup.
Retell and DLT: optional later-stage, off critical path.
