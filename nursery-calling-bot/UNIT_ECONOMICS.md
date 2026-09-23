# Per-enquiry call cost and unit economics (2026-09-23)

Model: `./unit_economics.py`, a Monte Carlo of the call funnel with every input overridable by a
flag. Actuals: `./unit_economics.py --runs runs/` once real runs exist. The tags say where each
number comes from: **[PUBLISHED]** is a vendor price page as of 2026-09-23, and **[ESTIMATE]** is
unverified and should be replaced from the first 5 live runs.

## Per-minute call cost (INR per connected minute)

| Stack | ₹/min | Basis |
|---|---|---|
| Sarvam Voice Agents + rented Sarvam/Vobiz number | **~3.0** | [ESTIMATE]. The Voice Agents per-minute price is not public. The components are [PUBLISHED]: STT ₹30/hr = ₹0.50/min, TTS ₹3 per 1k chars ≈ ₹0.7–1.3/min of agent speech, Sarvam-105B LLM ≈ ₹0.1–0.2/min. Telephony ≈ ₹0.6/min [ESTIMATE, based on Plivo India's published ₹0.60/min]. |
| Sarvam, pessimistic (platform charges 2× components) | 6.0 | [ESTIMATE] |
| Self-hosted Pipecat/LiveKit + Sarvam APIs + Plivo/Exotel SIP | ~2.3 | [ESTIMATE] components only, no platform fee, but you build and host it |
| Retell, GPT-4.1 | 10.1 | [PUBLISHED] $0.055 voice + $0.045 LLM + $0.015 telephony = $0.115 × ₹88 |
| Retell, GPT-4.1-mini | 7.3 | [PUBLISHED] $0.055 + $0.0128 + $0.015 |

Fixed costs: number rental [ESTIMATE ₹500/month]. The Sarvam catalog shows the real price. This only applies if the zero-spend
constraint is lifted; a founder-owned BYO number (FREE_PATHS.md, path 7) adds no fixed cost.
Retell charges $2/month for a US number and $10 for a verified one [PUBLISHED], but a US number
calling Indian mobiles is a poor fit anyway.

## Funnel assumptions [ESTIMATE, all flags]

The customer picks up on 60% of attempts, with up to 3 attempts. 70% of those still want the
service, and the call lasts 2.5 minutes. A gardener picks up 50% of the time and is available 35%
of the time when reached, and that call lasts 1.5 minutes. The pipeline calls up to 6 gardeners
over 2 passes, stops at 2 available, and bills 0 minutes for unanswered dials. 40% of customers who
get an offer pay.

Result: **6.5 dials and 6.1 billable minutes per enquiry. P(at least 1 gardener offer) = 55%.**

## Per enquiry (default: 5-day trip, alternate days = 3 visits)

Revenue per booking = max(₹30 fee × visits, ₹99 minimum) = **₹99**.

| Stack | Call cost / enquiry | Expected revenue / enquiry | Contribution / enquiry | Break-even booking rate |
|---|---|---|---|---|
| Sarvam (est. ₹3/min) | ₹18 | ₹22 | **+₹3.5** | 33% |
| Sarvam pessimistic | ₹36 | ₹22 | −₹15 | 67% |
| Self-hosted + Sarvam APIs | ₹14 | ₹22 | +₹8 | 26% |
| Retell GPT-4.1 | ₹61 | ₹22 | −₹40 | 113% (never) |

**Per booked job**, the first transaction is profitable on any Sarvam scenario: ₹99 revenue − about
₹18 of calls = **about ₹81**, and about ₹63 even at the pessimistic rate. The risk is not the first
transaction. It is enquiries that cost calls and don't book.

## Sensitivity (Sarvam ₹3/min)

| Change | Contribution / enquiry | Takeaway |
|---|---|---|
| No ₹99 minimum (₹90 revenue) | +₹1.6 | the minimum matters on short trips |
| `--want 1` (stop at the first available gardener) | **+₹7.7** | calling for a second option costs about ₹4 per enquiry |
| ₹149 minimum | +₹14.5 | price the booking, not the minutes |
| 10-visit job (2–3 week trip or monthly) | **+₹48** | longer jobs make the model comfortable |
| Pessimistic funnel (gardener connect 30%, available 20%, booking 25%), ₹149 minimum | −₹4 | a better roster (next step #4) matters more than provider price |

## Recommendations

1. Launch on Sarvam with a **₹99 minimum** (already the default) and `--want 1` for short trips.
2. Use the first 5 live runs to replace the estimated ₹/min and funnel rates:
   `./unit_economics.py --runs runs/`, then re-run the model with the measured values.
3. The biggest lever is the roster, not the provider. Gardeners who said yes before will pick up
   and say yes again. A standing roster cuts dials per enquiry by half or more.
