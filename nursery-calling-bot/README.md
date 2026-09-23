# Enquiry Auto-Calling Bot

When an enquiry comes in, the bot:

1. **Validates it.** It checks for an Indian mobile number, a Bangalore pincode, sensible dates, and
   a record of how the customer asked us (`consent_source`).
2. **Calls the customer** in an Indian-English voice, switching to Hindi or Kannada if they do. It
   confirms dates, area and landmark, the plants, how often to visit, access and budget. If nobody
   picks up, it retries up to 3 times.
3. **Calls gardeners near them**, nearest first, in Hinglish. It asks about availability, the start
   date, the rate per visit and a contact number, and stops once `--want` of them say yes. Gardeners
   it couldn't reach get one retry pass.
4. **Prices the job and hands off on WhatsApp.** The price is the gardener's rate plus our fee
   (max(₹30, 20%) per visit, with a ₹99 minimum per booking). The bot writes drafts for the
   customer, where they pick an option and pay by UPI, and for the available gardeners. A person
   sends them.

Gardeners only ever hear the area, never the customer's name, number or address. Anyone who says
"don't call again", or whom the carrier reports as TRAI NDNC, goes on `do-not-call.txt` and is
never dialled again.

## Status (2026-09-23)

| Piece | State |
|---|---|
| Pipeline, mock provider, 31 tests | ✅ `python3 -m unittest discover -s tests` |
| Sarvam adapter (primary) | written against the API docs and unit-tested; **not yet run live** |
| Sarvam agents | spec ready in SARVAM_SETUP.md; build them in the dashboard (free) |
| Retell adapter + 2 agents (fallback) | agents exist; Retell needs a card for a number |
| **Phone number** | **the only launch blocker.** Rent one from Sarvam (KYC, wallet, no card) or bring your own |

See PLAN.md for the goal and ranked next steps, LAUNCH_CHECKLIST.md for launch, UNIT_ECONOMICS.md
for cost per enquiry, and ALTERNATIVES.md for cheaper and bring-your-own-number options.

## Usage

```bash
# No calls, no spend: built-in happy-path mock, or a scripted scenario
./enquiry_pipeline.py --provider mock --name Ravi --phone 98xxxxxxxx --locality "Jagajyothi Layout" \
    --pincode 560056 --start 2026-10-02 --end 2026-10-06 --notes "20 pots, balcony" --consent whatsapp_enquiry
./enquiry_pipeline.py --provider mock --scenario scenarios/customer-busy-then-confirms.json \
    --gardeners gardeners.example.csv --phone 9876543210 ...same args...

# TEST mode (default for real providers): every call rings 8087404471, max 1 gardener
./enquiry_pipeline.py --name Ravi --phone 98xxxxxxxx ... --consent founder_test

# LIVE: real customer + up to --max-gardeners gardeners, 09:00-21:00 IST only
./enquiry_pipeline.py --live ...same args...

# Continue a run that paused (provider outage, outside calling hours, crash)
./enquiry_pipeline.py --resume <enquiry-id>

# Cost model / actuals
./unit_economics.py
./unit_economics.py --runs runs/
```

`--file enquiry.json` takes the same keys: `name, phone, locality, pincode, start_date, end_date,
notes, consent_source`, plus optional `lat, lng`.

Result codes in `runs/<id>.json`:
- `N_gardeners_available`
- `no_gardener_available`
- `no_gardeners_in_range`
- `customer_not_reached`
- `customer_opted_out`
- `customer_on_dnc`
- `customer_on_ndnc`
- `customer_no_longer_needs_service`
- `customer_callback_requested:<when>`
- `customer_needs_kannada_callback`
- paused runs: `provider_error`, `outside_calling_window`, `customer_call_status_unknown`

## Files

- `enquiry_pipeline.py`: the orchestrator (stdlib Python only)
- `providers.py`: the `SarvamProvider`, `RetellProvider` and `MockProvider` adapters, all returning
  one outcome shape
- `tests/test_pipeline.py`: provider-mocked end-to-end tests
- `unit_economics.py`: the funnel and cost model
- `prompts/customer.md`, `prompts/gardener.md`: the agent scripts, shared by both providers
- `SARVAM_SETUP.md`, `sarvam.example.json`: how to build the Sarvam agents, and the config
  template. `sarvam.json` is gitignored.
- `setup_agents.py`, `retell.py`, `agents.json`: the Retell fallback. It reads `API_KEY_RETELL`
  from the repo-root `.env`.
- `gardeners.example.csv`: the roster format. The real `gardeners.csv` holds third-party contact
  numbers and is gitignored. Set `status` to anything other than `active` to skip a row. Fill in
  `lat`/`lng` to rank by real distance.
- `runs/`, `do-not-call.txt`: call results and opt-outs, both gitignored because they hold
  personal details.

Keys live only in the repo-root `.env`, which is gitignored: `SARVAM_API_KEY`, and
`API_KEY_RETELL` for the fallback.

Earlier nursery-outreach prep (scripts, rubric, prospect sourcing) is in `scripts/`, `prospects/`
and `PILOT_CHECKLIST.md`.
