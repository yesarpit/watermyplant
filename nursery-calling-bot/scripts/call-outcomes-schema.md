# Structured Call Outcomes Schema

**Purpose:** a fixed set of machine-readable outcome codes every call (simulated or, later, real) must
resolve to, so results can be counted consistently against the funnel in
`docs/nursery-outreach-funnel-2026-09-17.md` and the qualification rubric.

## Schema (one record per call)

```json
{
  "call_id": "string — Retell call_id once real, or a local sim-id (e.g. SIM-001) for test fixtures",
  "prospect_id": "int — matches the `id` column in prospects/bangalore-jagajyothi-layout-nurseries.csv",
  "timestamp": "ISO-8601",
  "outcome_code": "NO_ANSWER | VOICEMAIL | WRONG_NUMBER | NOT_QUALIFIED | DEFERRED | QUALIFIED_INCOMPLETE | QUALIFIED_COMPLETE | DECLINED_HOSTILE",
  "qualification_level": "L0 | L1 | L2 | L3 | L4",
  "captured": {
    "gardener_name": "string | null",
    "gardener_phone": "string | null",
    "price_amount": "number | null",
    "price_unit": "per_day | per_visit | unconfirmed | null",
    "confirm_back_completed": "boolean"
  },
  "call_duration_seconds": "number | null",
  "notes": "string — anything the rubric doesn't capture (tone, language switching issues, etc.)",
  "requires_founder_followup": "boolean — true only for QUALIFIED_COMPLETE or DEFERRED"
}
```

## Outcome code → qualification level mapping

| outcome_code | qualification_level | Feeds into funnel stage |
|---|---|---|
| `NO_ANSWER` | L0 | Excluded from "connected" denominator |
| `VOICEMAIL` | L0 | Excluded from "connected" denominator |
| `WRONG_NUMBER` | L0 | Flag row in prospects CSV as `verified: bad_number`, exclude from future re-dial |
| `NOT_QUALIFIED` | L1 | Counts as "connected," not "qualified" |
| `DEFERRED` | L2 | Counts as "connected," tracked in a separate callback queue, not counted as qualified until resolved |
| `DECLINED_HOSTILE` | L1 | Counts as "connected," not "qualified"; flag row `do_not_call: true` |
| `QUALIFIED_INCOMPLETE` | L3 | Counts as "connected" + "qualified" for the qualification-rate numerator, but NOT as "captured" for the capture-accuracy metric — logged as a bot defect |
| `QUALIFIED_COMPLETE` | L4 | Counts fully through "Contact captured & confirmed" in the funnel |

## What happens after each outcome (operational routing, once real calls are approved)

- `QUALIFIED_COMPLETE` → goes into the founder/ops follow-up queue (see
  `follow-up-templates.md`) — a human calls the gardener directly, the bot does not call the gardener.
- `QUALIFIED_INCOMPLETE` → does NOT go to follow-up as-is (unusable data); instead flagged for a
  single retry call to the *same nursery* (not the gardener) to re-capture the missing field, subject
  to the "no re-push after decline" rule in the script.
- `DEFERRED` → scheduled for a founder-approved callback window (not an automatic bot re-dial).
- `WRONG_NUMBER` / `DECLINED_HOSTILE` → prospect row permanently flagged, excluded from all future
  batches.

## Local test log (simulated fixtures only — see simulated-conversations.md)

A CSV/JSON log of simulated-conversation outcomes should be kept at
`nursery-calling-bot/scripts/simulated-outcomes-log.csv` using exactly this schema (flattened) so the
same analysis code path can later be pointed at real Retell call logs with no format change.
