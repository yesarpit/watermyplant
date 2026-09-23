# Intake auto-trigger — plan (2026-09-23)

Directive: meta-manager 2026-09-23T06:47Z — "Wire intake.py behind a real form backend / WhatsApp
webhook (auto-trigger)". Zero cost, no paid accounts, no external contact.

## What exists

`nursery-calling-bot/intake.py` accepts JSON on `POST /enquiries`, validates it and writes
`queue/<id>.json`. Somebody then has to run `enquiry_pipeline.py --file queue/<id>.json` by hand.

## What gets built

1. **Form backend** — `GET /enquire` serves a plain HTML form; `POST /enquire` takes
   `application/x-www-form-urlencoded`. Required call-consent checkbox (`consent_source=website_form`),
   hidden honeypot field (bots get a fake success, nothing is queued), 303 to a thanks page on
   success, 400 with the errors listed otherwise.
2. **WhatsApp Cloud API webhook** — `GET /webhooks/whatsapp` answers Meta's verify handshake only
   when `hub.verify_token` matches `WMP_WA_VERIFY_TOKEN`; `POST` requires a valid
   `X-Hub-Signature-256` (HMAC-SHA256 of the raw body with `WMP_WA_APP_SECRET`) — bad/missing → 403,
   no secret configured → 503. Text messages are parsed (pincode, dates, locality — including the
   `Locality:` line join.html pre-fills) and accumulated per sender, so details can arrive over
   several messages. Message ids are de-duplicated (Meta retries deliveries).
   - `STOP` → sender added to `do-not-call.txt`, nothing queued.
   - **Call consent is explicit.** join.html promises WhatsApp contact only, so a WhatsApp enquiry
     is queued for a *call* only once the sender says so (e.g. "ok to call"). Until then — or while
     pincode/dates/locality are missing — it is held in `queue/held/` with the missing items and a
     reply **draft** (sending replies needs a Meta token: founder).
3. **Auto-trigger** — one background worker runs every accepted enquiry through `Pipeline`.
   `--auto-run mock` (default: zero cost, scripted calls), `off`, or `sarvam`/`retell` — always
   **TEST mode** (every call rings the founder's own phone). The server has no `--live` path at all.
   Guards against someone entering a stranger's number: 1 enquiry per phone per 24 h, max N auto-runs
   per day (`--max-runs-per-day`, default 10). On start it drains queued files that have no run yet.

## Success criterion (checkable)

Automated tests (localhost only) prove:
- form POST → 303 + `queue/<id>.json` + run `finished` in `runs/`, no manual step;
- honeypot / missing consent / bad fields → nothing queued;
- signed WhatsApp fixture with consent → queued + run finished; bad or missing signature → 403, nothing queued;
- verify handshake echoes the challenge only with the right token;
- duplicate message id not re-queued; incomplete text → held with missing fields; follow-up completes it;
- STOP → do-not-call; same phone twice in 24 h → rejected; daily cap respected;
- **≥ 10 new tests, all 56 existing pass, `demo.py` output unchanged.**

## Needs the founder (blockers, non-blocking for this build)

- Public exposure: hosting or a tunnel in front of `intake.py` (e.g. a free Cloudflare quick tunnel)
  is outward-facing — not done by the agent.
- WhatsApp: a Meta developer app + WhatsApp Business number to point the webhook at, and the
  app secret / verify token in `.env`. Sending replies automatically needs a Meta access token.

## Rollback

All changes are in `nursery-calling-bot/`; `POST /enquiries` behaves as before except the new
one-enquiry-per-phone-per-24h guard (429). Revert the commit to go back; nothing is deployed.

## Result (2026-09-23)

Built: `intake.py` (form `/enquire`, JSON `/enquiries`, WhatsApp `/webhooks/whatsapp`, `AutoRunner`
worker, `pipeline_runner`), `whatsapp_inbound.py` (HMAC check, parser, per-sender conversations),
`EP.default_mock()` factored out of the CLI, `fixtures/whatsapp-message.json`,
`tests/test_autotrigger.py`.

Criterion check:
- 21 new tests in `tests/test_autotrigger.py`, every bullet above covered; **77/77 pass**
  (`python3 -m unittest discover -s tests`).
- `demo.py` output is byte-identical to before the change (`diff -r` of the two output dirs is empty).
- Manual: `./intake.py --gardeners fixtures/demo-roster.csv`, `curl -d … /enquire` → 303, and the
  server log shows `auto-run …: finished: 2_gardeners_available` with no other step.

Cost Rs 0. Nothing exposed publicly, no Meta app created, nobody contacted.
