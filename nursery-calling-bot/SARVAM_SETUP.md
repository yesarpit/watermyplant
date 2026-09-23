# Sarvam Voice Agents setup (primary provider)

Sarvam is the primary provider. It was chosen by the founder on 2026-09-23 because it is Indian-built,
has native Indian voices (English, Hindi and Kannada among 11 languages), and **rents Indian numbers
with no credit card**. Number rental is paid from the Sarvam wallet after individual KYC. Retell
stays in `providers.py` as a fallback.

Sarvam agents are built in the dashboard ([indus.sarvam.ai](https://indus.sarvam.ai), Build → Agents),
not by API, so this file is the spec to copy in. Everything below is free to set up. You only spend
money on real calls and a rented number.

## 1. Account (free)

1. Sign up at indus.sarvam.ai. New accounts get **₹100 free credits**
   ([docs](https://docs.sarvam.ai/api/getting-started/pricing)).
2. Settings → API Key → create one. Add `SARVAM_API_KEY=...` to the repo-root `.env`, which is
   gitignored. Never commit it.
3. Copy `org_id` and `workspace_id` from the dashboard URL into `sarvam.json`. Start from
   `sarvam.example.json`. `sarvam.json` is gitignored.

## 2. Two agents

Create each one with **Create from Scratch**. Paste the prompt from `prompts/<role>.md` into
Instructions → system prompt. Sarvam inserts variables as chips (type `@`), so replace each
`{{name}}` with the chip of the same name.

### `customer` agent: WaterMyPlants Customer Enquiry Call
- **Greeting:** "Hi, am I speaking with @customer_name? This is Priya from Water My Plant, calling
  about your plant-watering enquiry. Is this a good time for two minutes?"
- **Language:** starting language English. Turn on "Switch language during call" and allow English,
  Hindi and Kannada. With Kannada allowed, the agent can handle Kannada speakers itself; the
  `needs_kannada_callback` flag then becomes a fallback.
- **Voice:** a female Indian-English Bulbul voice.
- **Input variables:** `customer_name`, `locality`, `pincode`, `start_date`, `end_date`, `enquiry_notes`
- **Output variables.** Use exactly these names, because the pipeline reads them.

| name | type | extraction prompt |
|---|---|---|
| still_needs_service | enum yes/no | Did the customer confirm they still want someone to water their plants? |
| start_date | string | Confirmed start date as YYYY-MM-DD |
| end_date | string | Confirmed end date as YYYY-MM-DD |
| area | string | Confirmed locality/area |
| landmark | string | Nearby landmark the customer gave |
| plant_count | string | Approx number of plants/pots and where (indoor/balcony/garden) |
| visit_frequency | enum daily/alternate_days/twice_weekly/other/unknown | How often the gardener should visit |
| access_arrangement | string | How the gardener gets in |
| budget_per_visit_inr | string | Budget per visit in rupees, digits only, or NA |
| callback_time | string | If it was a bad time, when to call back, else NA |
| do_not_call | enum yes/no | Customer asked not to be called again or is not interested |
| needs_kannada_callback | enum yes/no | Customer could only speak Kannada and the call could not continue |
| call_summary | string | Two-line summary of the call |

- **Call goal:** `still_needs_service = yes`

### `gardener` agent: WaterMyPlants Gardener Availability Call
- **Greeting:** "Namaste, kya main @gardener_name ji se baat kar rahi hoon? Main Water My Plant se
  bol rahi hoon. Plants ko paani dene ke ek kaam ke baare mein do minute baat kar sakte hain?"
- **Language:** starting language Hindi. Allow English, Hindi and Kannada, with switching on.
- **Input variables:** `gardener_name`, `customer_area`, `pincode`, `start_date`, `end_date`,
  `visit_frequency`, `plant_count`, `access_arrangement`. These are area-level details only. The
  pipeline never sends the customer's name, number or address.
- **Output variables:**

| name | type | extraction prompt |
|---|---|---|
| available | enum yes/no | They or their staff can do the watering job |
| can_start_on_date | enum yes/no | They can start on the requested start date |
| price_per_visit_inr | string | Quoted charge per visit in rupees, digits only, or NA |
| contact_name | string | Name of the person who would do the job |
| contact_number | string | Phone/WhatsApp number to share, digits only, or NA |
| referral | string | Another gardener/nursery they recommended (name and number), or NA |
| do_not_call | enum yes/no | They asked not to be called again |
| needs_kannada_callback | enum yes/no | They could only speak Kannada and the call could not continue |
| call_summary | string | Two-line summary |

- **Call goal:** `available = yes`

After saving, note each agent's **app_id** and **version** in `sarvam.json`.

## 3. Free testing (no number, no card)

Use **Test agent** in the Canvas (a browser voice call) to play the customer and the gardener
yourself. Use **Tests** (Build → Tests) to run scripted scenarios against the agent: opt-out,
Kannada-only, wrong dates, a gardener with no price. Both run on free credits. Meanwhile
`./enquiry_pipeline.py --provider mock` and `python3 -m unittest discover -s tests` exercise
everything around the calls.

## 4. The one launch blocker: a phone number

Go to Deploy → Phone Numbers → Add Connection → **Rent from Sarvam** → Individual → complete KYC →
Buy Number. There's no card: it is paid from the Sarvam wallet. Rentals last 30 days and auto-renew.
The catalog shows the price, which isn't public, so check it before buying. Put the returned
`connection_id` and number into `sarvam.json`.

Alternatively, **bring your own**: Exotel, Twilio, Vobiz, Smartflo, Pulse or Intalk (see
ALTERNATIVES.md).

Then:

```bash
./enquiry_pipeline.py --name Test --phone 8087404471 --locality "Jagajyothi Layout" --pincode 560056 \
    --start 2026-10-02 --end 2026-10-06 --consent founder_test      # TEST mode: every call rings 8087404471
```

## How the pipeline talks to Sarvam

- Place call: `POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org}/workspaces/{ws}/outbounds`
  with `app_config.agent_variables` and the header `X-API-Key`.
- Result: the pipeline polls `GET https://apps.sarvam.ai/api/analytics/v1/{org}/{ws}/{app_id}/attempts`
  filtered by `attempt_id`, reading `connectivity_status`, `duration_in_seconds` and `agent_variables`.
  No public webhook is needed. If you do run one, set `webhook_url` in `sarvam.json`.
- Yes/no and number outputs arrive as strings. `providers.normalise_value` converts them.
- If Sarvam's telephony rejects a number as TRAI NDNC, the pipeline adds it to `do-not-call.txt`.

The Sarvam adapter is **written against the published API docs and unit-tested on sample payloads.
It has not yet run against a live account.** The first test-mode call is its integration test.
