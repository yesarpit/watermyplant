# Ready-to-post copy — WhatsApp Status & Instagram — 2026-09-23

For the founder to paste and post manually. This session cannot post to either account (personal
WhatsApp/Instagram login required). Both channels are already reserved in
`validation-7day/ref-codes.csv` (`own-wa-status` status=ready, `own-insta` status=ready-if-account-exists)
— posting is the only remaining step to activate them.

Both links use the same consent-based `join.html` funnel already live for the other owned channels: no
new data collection, no price commitment, opt-in and STOP-to-delete built into the form itself.

## WhatsApp Status
Post as a text status (24h, visible to your contacts). Swap the link only — do not edit the ref param.

> Piloting a plant-watering service for Jagajyothi Layout, Bangalore (560056) — gauging interest before I commit to running it. Going away and want your plants looked after? Tell me here, no payment now: https://www.watermyplant.in/join.html?ref=own-wa-status

Character count: ~215 (fits a WhatsApp Status text post).

## Instagram bio link
Use as the single bio link, or in a Story with a link sticker if the account has one attached page/site
already.

**Bio link (if only one link slot available):**
`https://www.watermyplant.in/join.html?ref=own-insta`

**Optional bio line above the link (if space allows):**
> 🌿 Piloting plant-sitting for Jagajyothi Layout, Bangalore — tap to register interest (no payment, no spam)

**Story caption (if posting a Story instead of/in addition to the bio link):**
> Piloting a plant-watering pilot for Jagajyothi Layout 📍 Bangalore 560056. Travelling soon and want someone to water your plants? Tap the link to tell us on WhatsApp — we only message you if you message us first, and you can say STOP any time.
> Link: https://www.watermyplant.in/join.html?ref=own-insta

## After posting
Update `validation-7day/ref-codes.csv` status for the posted row(s) from `ready` /
`ready-if-account-exists` to `live-<date>` (matching the pattern already used for `own-site`,
`own-blog-vacation`, `own-locality-page`), so the next daily checkpoint counts it as an active channel.
