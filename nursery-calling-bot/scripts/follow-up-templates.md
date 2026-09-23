# Follow-Up Templates — After a Qualified Nursery Call

**Scope:** what a human (founder/ops), not the bot, sends/says once a call resolves to
`QUALIFIED_COMPLETE` or `DEFERRED` (per `call-outcomes-schema.md`). The bot's job stops at capturing
and confirming the nursery's referral; a human always makes the actual first contact with the
gardener — this keeps a consent/trust checkpoint between an automated call and a real person being
recruited as supply.
**Status:** templates only, not sent to anyone. For use once real calling is approved.

---

## Template 1 — WhatsApp/call to the referred gardener (Hindi/English)

> Namaste [Gardener name] ji, mera naam [founder/ops name] hai, main watermyplant.in se baat kar raha
> hoon. [Nursery name] ne aapka number diya ki aap plants ko paani dene ka kaam karte hain. Hum
> occasionally customers ko aise gardeners se connect karte hain jab woh trip par jaate hain aur unke
> plants ko dekhbhaal ki zarurat hoti hai. Kya aap iske liye available rehte hain?

(Translation for founder reference: "Hi [name], I'm [name] from watermyplant.in. [Nursery name] gave
me your number, saying you do plant-watering work. We occasionally connect customers with gardeners
like you when they're traveling and need their plants looked after. Would you be open to that?")

**If yes →** move to onboarding questions: service area/radius, availability pattern (daily
availability vs. only certain days), rate expectations, whether they're comfortable with a WhatsApp
photo-confirmation step after each visit (matches the customer-facing trust mechanic in
`docs/pilot-economics-2026-09-10.md`).

**If no / not interested →** thank them, do not push, mark prospect-derived-lead as closed in the
tracking sheet (do not re-contact without a new referral).

## Template 2 — Callback to a `DEFERRED` nursery (after their promised follow-up window)

> Namaste, maine kal/pichle hafte aapse baat ki thi gardener ke baare mein — kya aapko unka number mil
> gaya?

(Translation: "Hi, I spoke with you last [day] about a gardener — were you able to get their number?")

**Cadence rule:** at most one callback attempt per `DEFERRED` outcome. If still no answer/info on the
second attempt, close the row — do not loop indefinitely (this mirrors the "no infinite retry loop"
guardrail from the original bot QA plan).

## Template 3 — Thank-you to a nursery that qualified but the gardener didn't pan out

> Namaste, dhanyavaad ki aapne humein contact diya tha — hum abhi unke saath talk kar rahe hain. Agar
> future mein aur koi zarurat ho toh hum contact karenge.

(Translation: "Thank you for the contact — we're in touch with them now. We'll reach out again if we
need anything in the future.") Keeps the nursery relationship warm for future sourcing rounds without
overpromising.

## Tracking

Every follow-up action (sent, response received, outcome) should be logged against the same
`prospect_id` used in `prospects/bangalore-jagajyothi-layout-nurseries.csv` and the `call_id` from
`simulated-outcomes-log.csv` (or the real Retell call log, later), so the full chain — nursery called
→ gardener referred → gardener contacted → gardener onboarded — stays traceable for the funnel metrics
in `docs/nursery-outreach-funnel-2026-09-17.md`.
