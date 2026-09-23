# Zero-cost technical POC: plan (2026-09-23)

Directive (meta-manager, 2026-09-23 06:01Z): finish the POC at zero cost. Do not rent a number,
fund a wallet or open a paid account, and do not treat "rent from Sarvam, no card" as compliant.
Renting still spends money, so it breaks the zero-cost rule.

## What "done" means

1. **One command** (`python3 demo.py`) runs the whole flow on this machine with no network,
   no account and no spend:
   - a sample enquiry is POSTed to a local intake endpoint (`intake.py`, stdlib HTTP, bound to
     127.0.0.1), which validates it and queues it
   - deterministic mocked customer and gardener calls go through the real `Pipeline` state
     machine. The script covers a retry, a no-answer, a decline with a referral and a gardener
     opt-out, so every branch that matters appears in one run
   - it writes the structured event log (`events.jsonl`), the final run state and outcome, the
     WhatsApp handoff drafts, and a unit-economics report (actuals from this run plus the model
     table) to `demo-output/`, and prints a summary
   - two runs produce byte-identical output (fixed clock, fixed ids)
2. **Mocked Sarvam contract and error tests** (`tests/test_sarvam_contract.py`). A fake
   transport stands in for `urllib`. The tests pin the request shape the adapter sends
   (URL, method, headers, body), the response fields it reads (attempt polling, output variables,
   NDNC, durations), and what happens on HTTP 4xx/5xx, network errors, malformed JSON, missing
   fields and timeouts. They also check that each error reaches the pipeline as a pause or a
   retry, never as a crash.
3. **A matrix of free paths** (`FREE_PATHS.md`): free sandboxes and bring-your-own-number
   options that need no purchase. Nothing gets registered while writing it.
4. **Docs updated.** README, PLAN and LAUNCH_CHECKLIST no longer recommend renting. The
   technical POC is marked complete. Live PSTN validation becomes a separate founder-review item
   with two options: (a) supply a compatible number or account the founder already has, or
   (b) explicitly change the zero-spend constraint.
5. **Verified, then pushed.** All tests pass, the demo runs twice with identical output, and a
   secret/PII scan passes. Then push `a3f94e9` together with these changes.

## Steps

1. Write this plan.
2. `intake.py`: `POST /enquiries` validates the body with `validate_enquiry`, then returns 202
   with the id or 400 with the errors. `GET /health` responds too. Only the stdlib is used.
3. `demo.py` and `fixtures/demo-enquiry.json`, `fixtures/demo-roster.csv`, `fixtures/demo-scenario.json`.
   All numbers in them are synthetic (`+9190000000xx`, `+919876543210`).
4. Harden `SarvamProvider._request`. Non-JSON bodies and connection resets currently escape as
   `JSONDecodeError`/`OSError`, and a create-call response without `attempt_id` escapes as
   `KeyError`. All of these should raise `ProviderError` so the pipeline retries or pauses.
5. Contract/error tests, plus a demo test (the run is deterministic and its outputs are complete).
6. `FREE_PATHS.md`, then the README/PLAN/LAUNCH_CHECKLIST updates.
7. Run the full suite and the demo twice. Scan for secrets and PII. Commit, push, and check that
   `origin/main` matches.

## Rollback

All changes are under `nursery-calling-bot/` plus `.gitignore` (`demo-output/`). The public site
pages are untouched. To roll back: `git revert <commit>`. The bot is not wired into the site, so
reverting changes nothing for visitors.

## Out of scope (founder review)

- Live PSTN calls. They need either an existing compatible number or account, or a change to the
  zero-spend constraint.
- Building the agents in the Sarvam dashboard. That needs a Sarvam account; the account is free,
  but opening one is still the founder's call.
