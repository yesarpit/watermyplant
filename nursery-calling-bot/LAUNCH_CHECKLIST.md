# Launch checklist: enquiry auto-calling

**Technical POC: complete at ₹0** (`python3 demo.py`, 56 tests). Live launch needs a phone
number, which is a founder decision under the zero-spend constraint: either connect an account the
founder already owns, or explicitly lift the constraint. See FREE_PATHS.md. Nothing gets rented.

## A. Built and verified without a number (done 2026-09-23)

- [x] Enquiry validation: Indian mobile, Bangalore pincode (560xxx), sane dates, `consent_source` required
- [x] Gardener ranking: haversine distance when lat/lng is known, otherwise pincode gap. Radius cap. Skips inactive, do-not-call and invalid numbers
- [x] Customer call outcomes: confirmed / opted out / no longer needed / callback later / Kannada / NDNC / unreachable after 3 tries
- [x] Gardener call outcomes: available + rate / not available + referral / opted out / unreachable → retry pass / timeout (never redialled)
- [x] Consent and do-not-call: DNC checked before every dial, opt-outs and carrier NDNC added automatically, calling window 09:00–21:00 IST enforced in `--live`
- [x] Privacy: gardeners get area-level details only (a test asserts no customer name or number is sent)
- [x] Retries: customer ×3 with a delay; gardener second pass; API placement errors retried with backoff
- [x] Failure recovery: atomic state file; `--resume <id>` continues a paused or crashed run without redialling finished calls; pauses on provider outage or outside the calling window
- [x] Structured logs: `runs/<id>.json` (state, offers, metrics, economics) + `runs/<id>.events.jsonl`
- [x] WhatsApp handoff: priced customer draft (with the UPI step and STOP line) + gardener hold drafts, as wa.me links for a human to send
- [x] Pricing: gardener rate + max(₹30, 20%) per visit, ₹99 minimum per booking
- [x] Test suite: `python3 -m unittest discover -s tests`, 56 passing (pipeline, intake, demo, Sarvam contract/errors)
- [x] One-command demo: `python3 demo.py`, intake → mocked calls → event log, outcome, WhatsApp drafts, unit economics (byte-identical across runs)
- [x] Sarvam adapter: request/response shape pinned to the published API reference; HTTP/network/malformed errors pause the run (resumable) instead of crashing
- [x] Local intake endpoint `intake.py`: validates, rejects unknown fields and unsafe ids, caps body size, binds to 127.0.0.1
- [x] Secrets: API keys only in the repo-root `.env` (gitignored); `sarvam.json`, the roster and runs are gitignored

## B. Free, needs founder account access (no card)

- [ ] Sarvam account + API key in `.env`; `org_id`/`workspace_id` in `sarvam.json`
- [ ] Build the `customer` and `gardener` agents per SARVAM_SETUP.md; put their app ids/versions in `sarvam.json`
- [ ] Browser "Test agent" run of each agent: opt-out, Kannada speaker, no-price gardener
- [ ] Decide the customer-facing fee wording (₹30/visit or 20%, ₹99 minimum)

## C. Live PSTN validation (founder review, separate from the POC)

- [ ] **Phone number:** decide between (a) connecting an Exotel/Vobiz/Twilio/Smartflo/Pulse/Intalk account the founder already owns (₹0 extra), or (b) explicitly lifting the zero-spend constraint. Then put `connection_id` and `agent_phone_number` in `sarvam.json`. Do not rent a number under the current constraint. See FREE_PATHS.md

## D. After the number (same day)

- [ ] TEST-mode run: `./enquiry_pipeline.py --name Test --phone 8087404471 ... --consent founder_test` (every call rings the founder)
- [ ] Check `runs/<id>.json`: statuses, minutes, `data` fields filled, and the WhatsApp link opens correctly
- [ ] If any output variable arrives under a different name or format, fix the agent's output variables in the dashboard, not the code
- [ ] First `--live` run on a real, consented WhatsApp enquiry between 09:00 and 21:00 IST
- [ ] Send the drafts by hand, collect UPI, then share the address with the chosen gardener
- [ ] `./unit_economics.py --runs runs/` after 5 enquiries; update the assumptions in UNIT_ECONOMICS.md

## Stop conditions

Pause live calling and review if any of these happen:
- a complaint
- more than 20% of gardener calls end in an opt-out
- two runs pause with `provider_error` in a day
- the cost per enquiry goes above ₹40
