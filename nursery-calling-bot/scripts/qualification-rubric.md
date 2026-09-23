# Qualification Rubric — Nursery Outreach Calls

**Purpose:** a consistent, testable bar for whether a call outcome counts as a "qualified lead" for
the funnel in `docs/nursery-outreach-funnel-2026-09-17.md`. Used both to grade simulated test
conversations now, and to grade real call transcripts once calling is approved.

## Qualification levels

| Level | Criteria | Counts as "qualified" in funnel math? |
|---|---|---|
| **L0 — No contact** | No answer, voicemail, wrong number, disconnected mid-call before the opening line completes | No — excluded from connection-rate denominator adjustments per stage |
| **L1 — Connected, not qualified** | Human answered; understood the ask; confirmed they have no gardener to offer | No |
| **L2 — Connected, deferred** | Human answered, seemed uncertain, asked to call back later, or said "let me check and call you" | No (tracked separately — see Follow-up templates for a founder-approved callback, not automatic re-dial) |
| **L3 — Qualified, incomplete capture** | Nursery confirms they have/know a gardener, but the bot fails to capture a usable phone number or the price (transcription error, refused, or call dropped before confirm-back) | No — this is a bot-quality failure, must be logged as a defect, not a funnel win |
| **L4 — Qualified, fully captured** | Nursery confirms availability AND bot captures name + phone number + rough price AND completes the confirm-back read-back with explicit agreement | **Yes — this is the only level that counts as "Qualified" in the funnel** |

## Capture-accuracy checklist (all must be true for L4)

1. Name captured (even if just a first name or "the gardener," as long as it's specific enough to
   reference on a follow-up call).
2. Phone number captured as a valid-format Indian mobile number (10 digits, or +91-prefixed).
3. Price captured as a number + unit (₹ amount + "per day" or "per visit" or "not sure, will confirm"
   — the last is acceptable as long as it's explicitly stated, not silently dropped).
4. Confirm-back was performed and the nursery explicitly agreed (not just didn't object — an explicit
   "haan, sahi hai" / "yes, correct" or equivalent).

## Disqualification triggers (auto-fail regardless of other criteria)

- Bot commits to a price or term on the customer's behalf without flagging it as "to be confirmed."
- Bot is evasive or misleading about who it's calling on behalf of.
- Bot continues asking after an explicit "not interested" / "nahi chahiye."
- Bot leaves an unsolicited voicemail pitch instead of a brief, honest callback-request message (or no
  message, per script).

## Scoring a simulated conversation

For each fixture in `simulated-conversations.md`, assign the qualification level (L0–L4) the
conversation *should* produce given the script, then separately note whether the LLM prompt (when
actually run in Retell's dashboard test mode, once available — see
`docs/pilot-economics-2026-09-10.md` Section 5) reaches that same level in practice. Any mismatch is a
prompt-tuning bug, not a market-fit issue, and should be fixed in the LLM prompt before any real call.
