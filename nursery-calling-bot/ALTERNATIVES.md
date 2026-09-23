# Lower-cost and bring-your-own-number options

Researched 2026-09-23. No accounts were opened and nothing was bought. Everything the pipeline needs
from a provider is two methods in `providers.py` (`place_call`, `wait`), so any of these can be
added as an adapter without touching the pipeline.

| Option | Card needed? | Indian number? | Per-minute (INR) | Fit |
|---|---|---|---|---|
| Sarvam Voice Agents + Rent from Sarvam (**not zero-cost**: wallet-paid; only if the founder lifts the zero-spend constraint) | No card, but wallet + individual KYC | Yes (Vobiz-managed) | ~3 est. | Indian voices, NDNC screening, no-code agents, REST outbound + attempts API. [docs](https://docs.sarvam.ai/conversations/deploy/telephony/rent-from-sarvam) |
| Sarvam Voice Agents + **BYO Exotel / Vobiz / Twilio / Smartflo / Pulse / Intalk** (zero-spend only if the founder already has the account) | depends on that provider | Yes | telephony billed by that provider | Use this if the founder already has one of these accounts. [docs](https://docs.sarvam.ai/conversations/deploy/telephony/bring-your-own) |
| Self-hosted **Pipecat or LiveKit Agents + Sarvam STT/TTS/LLM APIs + Plivo/Exotel SIP** | Sarvam: no (₹100 free credits); SIP provider: usually a prepaid wallet | Yes | ~2.3 est. (Plivo India ₹0.60/min [published]) | Cheapest per minute and full control, but we must build turn-taking and host a server. Sarvam publishes guides for [Pipecat](https://docs.sarvam.ai/api/integration/build-voice-agent-with-pipecat) and [LiveKit](https://docs.sarvam.ai/api/integration/build-voice-agent-with-live-kit). Worth it at around 500+ enquiries a month. |
| Retell AI + BYO SIP trunk (Plivo/Exotel/DIDWW) | Retell: yes, for credits beyond $10 | Yes via SIP | ~7–10 | Retell charges nothing extra for SIP ([pricing](https://www.retellai.com/pricing)), but its voice and LLM cost stays about 3× Sarvam's. Fallback only. |
| Retell-rented number | **Yes** | No: US numbers | ~10 + international | Rejected: needs a card, and Indian recipients see a foreign caller ID. |

## Zero-cost ways to keep testing before any number

FREE_PATHS.md has the full matrix and status; the short version:

1. **Mock provider**: `./enquiry_pipeline.py --provider mock ...` and the test suite. Costs ₹0.
2. **Sarvam "Test agent"**: a browser voice call to each agent. It uses free credits and needs no number.
3. **Sarvam Tests**: scripted simulated conversations against the agents on free credits. They
   check prompt behaviour (opt-out, Kannada, missing price) before any real call.
4. **Retell dashboard "Test"**: the existing Retell agents can still be heard in the browser on
   Retell's $10 trial credit.

## Compliance notes that apply to every option

- The customer asked us to call (a WhatsApp or website enquiry), so that is a service call made
  with consent. Record `consent_source` on every enquiry.
- Gardener calls are B2B availability checks to a small curated roster. At volume, TRAI DLT and
  140-series rules apply; see `../docs/trai-dlt-compliance-2026-09-17.md`. Sarvam/Exotel reject
  NDNC-registered numbers, and the pipeline then adds them to `do-not-call.txt`.
- Live calls only between 09:00 and 21:00 IST. The pipeline enforces this in `--live`.
