# Enquiry auto-calling: plan and goal (2026-09-23)

## Goal

The enquiry → customer call → nearby-gardener calls → WhatsApp handoff workflow is **technically
launch-ready, measurable, and able to support a profitable first transaction** as soon as a phone
number exists, at **zero cost until then** (founder, 2026-09-23: mocks, free tiers and BYO/free
options only; no card).

It counts as done when all of these are true:
1. Every step runs end to end against a mock provider with no network, and is covered by automated
   tests. That covers validation, ranking, customer and gardener outcomes, consent and do-not-call,
   retries, failure recovery, logs and the WhatsApp handoff. **Done: 31 tests.**
2. The provider is swappable, and the chosen provider (Sarvam) needs only config (`sarvam.json` and
   the API key) plus a phone number, with no code change. **Done. The adapter is untested live.**
3. Each enquiry writes a resumable state file and an event log, with per-call cost, minutes and
   connect rate. `unit_economics.py --runs runs/` rolls them up. **Done.**
4. Each quote the customer sees includes our fee, with a booking-fee floor, so any booked job makes
   money after the calls it took. **Done: fee = max(₹30, 20%) per visit, and at least ₹99 per booking.**
5. There is a launch checklist whose only open blocker is the phone number. **Done: LAUNCH_CHECKLIST.md.**

## Decisions

- **Provider: Sarvam Voice Agents** (founder's call on 2026-09-23, replacing Retell). It has Indian
  voices, Indian numbers without a card, NDNC screening on the provider side, and components that
  cost roughly ⅓ of Retell's per minute (UNIT_ECONOMICS.md). Retell is kept as a fallback adapter.
  Retell costs about ₹10/min, and it would dial Indian customers from a US number.
- **Mock-first.** `MockProvider` plays scripted outcomes: connected with extracted data, no answer,
  busy, voicemail, failed, NDNC, API error, timeout. The pipeline can't tell it from a real
  provider.
- **Human in the loop at the money step.** The bot only drafts WhatsApp messages. A person sends
  them, collects UPI payment, and then shares the address. No automatic messaging, and no payments
  without the founder.
- **Consent.** Every enquiry records how the customer asked us (`consent_source`). Gardeners are
  called only from the curated roster, never from a scraped list. Anyone who opts out, or whom
  the carrier reports as NDNC, goes on `do-not-call.txt` permanently. Live calls happen only between
  09:00 and 21:00 IST.

## How it was built (steps taken)

1. Split calling into `providers.py` with a provider-neutral outcome shape, and added Sarvam,
   Retell and Mock adapters.
2. Rewrote `enquiry_pipeline.py` as a resumable state machine: validate → customer stage (up to 3
   attempts) → rank gardeners → gardener passes (2 passes, stop at `--want`) → price → handoff.
   Every step is saved atomically, so a crash never loses or duplicates a call.
3. Wrote `tests/test_pipeline.py` with 31 end-to-end and unit tests on the mock provider.
4. Wrote `unit_economics.py`, a Monte Carlo of the call funnel with published and estimated
   per-minute rates.
5. Wrote SARVAM_SETUP.md, LAUNCH_CHECKLIST.md, UNIT_ECONOMICS.md and ALTERNATIVES.md.
6. Ran a secret scan, gitignored personal data (roster, prospects, runs, do-not-call list,
   `sarvam.json`), and committed the code and docs under `nursery-calling-bot/` only. Not pushed:
   this repo deploys the public site.

## Ranked next steps

| # | Step | Cost | Owner | Unblocks |
|---|---|---|---|---|
| 1 | **Get a phone number.** Sarvam "Rent from Sarvam": individual KYC, paid from the wallet, no card. Or connect an existing Exotel/Vobiz account. | number rent (price shown in catalog) | founder | everything live |
| 2 | Create a Sarvam account, build both agents from SARVAM_SETUP.md, and test them in the browser "Test agent" plus Sarvam Tests (opt-out, Kannada, no price). | free (₹100 credits) | founder or agent, once account access exists | adapter live test |
| 3 | First TEST-mode run (`enquiry_pipeline.py` without `--live`, rings 8087404471). Play both roles and check that the extracted variables land in `runs/<id>.json`. | a few rupees of credit | founder | confidence in the Sarvam adapter |
| 4 | Enrich `gardeners.csv` with lat/lng and 10–15 more gardeners around 560056, 560060 and 560098. Ranking then uses real distance and P(offer) rises. | free | agent (desk research) | P(≥1 offer) above 55% |
| 5 | Put the ₹99 minimum and the per-visit fee on the site/WhatsApp copy so that quotes match what customers expect. | free | founder approves copy | a profitable first booking |
| 6 | First live enquiry: run `--live` on a real WhatsApp enquiry, send the drafts by hand, collect UPI, and log the result. Then `unit_economics.py --runs runs/` to replace the assumptions. | about ₹15–20 per enquiry | founder | real funnel numbers |
| 7 | Auto-trigger: a small form backend or the WhatsApp Business API posts enquiries to the pipeline. Use Sarvam's webhook (`webhook_url`) instead of polling. | free tier (e.g. a serverless function) | agent | no manual entry |
| 8 | Standing gardener roster: re-use gardeners who said yes, which gives fewer dials per enquiry and lower cost (see `--want 1` in UNIT_ECONOMICS.md). | free | agent | margin |
