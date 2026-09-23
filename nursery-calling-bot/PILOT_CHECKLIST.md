# Ready-to-Run Pilot Checklist — Nursery Outreach Calling Bot

**Date prepared:** 2026-09-17
**Purpose:** everything needed to start the real pilot the moment the two founder-review blockers
clear, with zero re-planning delay. Items are grouped by what's already done vs. what only happens
after approval.

---

## Already done (no further action needed to start)

- [x] Retell LLM built and prompt-designed: `llm_9ec922e7f5ab140a34b73c6ae708`
- [x] Retell agent built: `agent_512e0d7cadfc0f99ed1ebeabaa` (voice `11labs-Monika`, `language: multi`)
- [x] Outreach script written and branch-logic mapped: `scripts/nursery-outreach-script.md`
- [x] Qualification rubric defined: `scripts/qualification-rubric.md`
- [x] Structured call-outcome schema defined: `scripts/call-outcomes-schema.md`
- [x] Follow-up templates for qualified leads written: `scripts/follow-up-templates.md`
- [x] 6 simulated test conversations scored against the rubric: `scripts/simulated-conversations.md`
      + `scripts/simulated-outcomes-log.csv`
- [x] Prospect dataset: 14 nurseries, deduplicated, sourced, geo-documented:
      `prospects/bangalore-jagajyothi-layout-nurseries.csv` + `prospects/SOURCES.md`
- [x] Pilot funnel + profitability thresholds modeled: `docs/nursery-outreach-funnel-2026-09-17.md`
- [x] TRAI DLT compliance requirements documented + a non-call fallback experiment designed:
      `docs/trai-dlt-compliance-2026-09-17.md`
- [x] Both blockers written up for founder decision with exact action/cost/unlock:
      `docs/founder-review-blockers-2026-09-17.md`

## Founder action needed before Step 1 below (see docs/founder-review-blockers-2026-09-17.md)

- [ ] **Blocker 1:** Add a payment card at dashboard.retellai.com → Billing
- [ ] **Blocker 2:** Resolve the TRAI DLT question — either complete PE/TM registration, or get a
      citable answer that this specific B2B use case is exempt (see
      `docs/trai-dlt-compliance-2026-09-17.md` Section 2)

## Step-by-step once both blockers clear

1. **Purchase the outbound number.** Run the `create-phone-number` call documented in
   `nursery-calling-bot/README.md`. Confirm with Retell/Twilio support whether a 140-series
   (promotional) or 160-series (transactional) number applies to this use case before buying
   (`docs/trai-dlt-compliance-2026-09-17.md` Section 1).
2. **Self-test call.** Run `place_test_call.sh` to the founder's own number (8087404471) — first live
   validation of the full pipeline (LLM + voice + telephony). Compare the live transcript against the
   simulated fixtures in `scripts/simulated-conversations.md` — any mismatch is a prompt bug to fix
   before calling anyone real.
3. **Fill the phone-number gaps in the prospect list.** 11 of 14 rows in
   `prospects/bangalore-jagajyothi-layout-nurseries.csv` are missing a captured phone number —
   resolve via a Maps lookup (not guessed) before those rows are callable.
4. **Small-batch real pilot.** Call the ~14-nursery batch (or however many have confirmed numbers by
   then). Log every call against the schema in `scripts/call-outcomes-schema.md`.
5. **Measure against the funnel model.** Compare actual connection/qualification/capture rates to the
   targets in `docs/nursery-outreach-funnel-2026-09-17.md` Section 2 — update the [ASSUMPTION] tags
   there with real numbers.
6. **Route qualified leads to human follow-up.** Use `scripts/follow-up-templates.md` — the bot never
   contacts a gardener directly, only the nursery.
7. **Expand the prospect list** (next geographic ring — Vijayanagar, Nagarbhavi) once the first batch's
   funnel numbers are in hand, so list size scales with demonstrated yield, not blind volume.
8. **In parallel, run the non-call fallback experiment** from
   `docs/trai-dlt-compliance-2026-09-17.md` Section 3 regardless of calling status, since it's a
   distinct, cheaper acquisition channel worth comparing against the called-lead funnel.

## Definition of "pilot batch complete"

A batch is complete when every row in the current prospect CSV has a logged `outcome_code` (per
`call-outcomes-schema.md`) — no row left uncalled or unresolved — and the funnel/cost metrics for that
batch are written back into `docs/nursery-outreach-funnel-2026-09-17.md` as observed values.
