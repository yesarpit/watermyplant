# Zero-spend test paths and bring-your-own-number options (2026-09-23)

The constraint is **zero spend**. That rules out buying a number, topping up a wallet or opening a
paid plan, even where no card is involved. Sarvam's "Rent from Sarvam" option is wallet-paid, so
it is **not** zero-cost and is not recommended here.

Nothing below was signed up for or bought while writing this. Rows marked *unverified* come from
vendor pages or search results; check them before relying on them.

## Matrix

| # | Path | Real phone call (PSTN)? | Spend | Needs | What it proves | Status |
|---|---|---|---|---|---|---|
| 1 | **Local mocked demo**: `python3 demo.py` | No | ₹0 | nothing | The whole state machine: intake, customer/gardener calls with every outcome, DNC, retries, pause/resume, event log, WhatsApp drafts, unit economics | **Done.** Deterministic, runs in CI |
| 2 | **Sarvam contract tests**: `tests/test_sarvam_contract.py` | No | ₹0 | nothing | The adapter sends the documented request shape and survives 4xx/5xx, network errors, malformed JSON, timeouts and slow extraction | **Done.** Pinned to Sarvam's published API reference |
| 3 | **Sarvam "Test agent" in the browser** | No (browser voice) | ₹0: free starter credits, no card | a free Sarvam account (founder's decision) | Real voices, prompts and Hinglish/Kannada switching; checks the output-variable names the adapter expects | founder: open an account |
| 4 | **Sarvam Tests** (simulated conversations) | No | ₹0 from free credits | same account as #3 | Opt-out, Kannada and "no price given" scripts run against the real agents | founder: after #3 |
| 5 | **Retell dashboard "Test"** (the agents already exist) | No (browser voice) | ₹0 from the existing $10 trial credit | the Retell account the founder already has | Retell prompt behaviour only; Retell is the fallback | available now |
| 6 | **Self-hosted SIP loop**: Pipecat/LiveKit agent + Sarvam STT/TTS on free credits + Asterisk/FreeSWITCH + a softphone on the LAN | No (SIP on the local network) | ₹0 | a free Sarvam API key and a local machine | End-to-end audio turn-taking over real SIP without any carrier. Only worth it if we move off the hosted Voice Agents | optional, not planned |
| 7 | **BYO: an Exotel, Vobiz, Twilio, Smartflo, Pulse or Intalk account the founder already owns**, connected to Sarvam | **Yes** | ₹0 extra if it already has a number and balance; the calls draw on that existing account | the existing account's credentials ([Sarvam BYO docs](https://docs.sarvam.ai/conversations/deploy/telephony/bring-your-own)) | Live PSTN through the real adapter: `connection_id` and `agent_phone_number` go in `sarvam.json`, with no code change | **founder: do you already have one?** |
| 8 | **Twilio free trial** connected to Sarvam as BYO | Yes, but only to up to 5 verified numbers | ₹0 trial balance, no card ([Twilio trial](https://help.twilio.com/articles/223136107-How-does-Twilio-s-Free-Trial-work-)) | a new free Twilio account (founder's decision) | A live call to the founder's own verified phone | *unverified*: trial calling is limited to your own country by default ([limits](https://help.twilio.com/articles/360036052753-Twilio-Free-Trial-Limitations)). Calling India from a US trial number may need geo-permissions the trial doesn't allow, and the caller ID would be foreign. A self-test only, never for customers |
| 9 | **Exotel or Plivo free trials** | Yes, probably restricted to verified numbers | trial credit (Exotel: a 15-day trial is advertised; Plivo: $10 credit advertised) | a new account, and usually KYC | Same as #8, with an Indian caller ID | *unverified*: trial terms and whether they allow outbound AI calls are not documented publicly. Ask the vendor first |

**Excluded** because they break the zero-spend constraint or the rules:
- Sarvam "Rent from Sarvam": wallet-paid.
- A Retell-rented number: needs a card, and it is a US number.
- Paid Exotel/Vobiz/Plivo plans.
- A personal SIM driven through an Android or GSM gateway: TRAI and carrier terms forbid automated calling from a personal SIM, and it wouldn't reflect production.

## What each path unblocks

- **Paths 1–2 (done)** are the technical POC. Everything except the carrier leg is proven.
- **Paths 3–5** remove prompt and extraction risk at ₹0. They need the founder to open (free)
  accounts.
- **Path 7** is the only zero-spend way to reach live PSTN that is suitable for production.
- **Paths 8–9** can give a single live self-test at ₹0, but they are unverified and not suitable
  for customers.

## Founder decision needed (live PSTN validation)

Pick one:
- **(a)** Supply an existing compatible account and number (path 7). This needs no code change.
- **(b)** Explicitly change the zero-spend constraint, for example to allow a Sarvam-rented
  number (KYC plus wallet top-up; see SARVAM_SETUP.md and UNIT_ECONOMICS.md for costs).

Until one of these happens, live calling stays off. The POC doesn't need it.
