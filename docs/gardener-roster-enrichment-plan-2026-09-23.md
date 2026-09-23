# Gardener roster enrichment — plan (2026-09-23)

Directive: meta-manager 2026-09-23T06:17Z — "Enrich gardeners.csv with lat/lng + 10-15 more
gardeners near 560056/560060/560098". Zero cost, no external contact.

## Goal and success criterion (checkable)

1. **All 7 existing active rows** in `nursery-calling-bot/gardeners.csv` have `lat`/`lng`, each with a
   stated basis in `notes` (`geo:osm-poi`, `geo:osm-address`, `geo:locality-centroid`).
2. **>= 10 new rows** (target 15) with: a phone number from a public source, `pincode` in or adjacent to
   560056/560060/560098, `lat`/`lng`, and a `source_id` that resolves to a row in the (gitignored)
   prospect sheet with its source URL.
3. `rank_gardeners()` with the Jagajyothi Layout coordinate returns >= 10 rows ranked by real distance
   (`rank_basis == "distance"`), all within the 12 km radius; full test suite still passes.

## Method (all free, public, read-only)

- Coordinates: OpenStreetMap Nominatim (1 req/s, identifying User-Agent, per its usage policy) and
  Overpass for `shop=garden_centre` / nursery POIs around the anchor. Where only a locality resolves,
  use the locality centroid and say so — precision is recorded, not implied.
- New gardeners: public directory pages / search results / business websites / OSM tags only. No
  logins, no paid data, no scraping of bot-blocked pages, **no calls/messages/emails to anyone**.
- Row status: `active` only when the phone number is corroborated (>= 2 independent public sources,
  or the business's own website/OSM tag). Otherwise `status=unverified` so the pipeline never dials
  it (`rank_gardeners` only takes `active`). Closed businesses excluded.
- Dedup against the existing 14-row prospect sheet by normalized phone and name.

## Data handling

`gardeners.csv` and `prospects/` are gitignored (third-party contact data). Only this plan and any
code/test changes are committed; no phone numbers go into git.

## Rollback

Copy of the pre-edit roster saved as `prospects/gardeners.csv.bak-2026-09-23` (gitignored) before editing; restore by copying it back.

## Result (2026-09-23) — success criterion met

| Criterion | Result |
|---|---|
| lat/lng on all 7 existing rows | 7/7. 5 exact Maps pins; Evergreen = probable branch pin (multi-site); Bhoomi + Fruit Plant = Nagadevanahalli locality centroid (OSM, ±1.5 km: Bhoomi's own Maps pin is bogus, Fruit Plant has no Maps listing) |
| >= 10 new gardeners | **13 new** (4 have Maps category "Gardener"/landscaper, 9 are nurseries), pincodes 560056/059/060/061/074/091/098, all with phone + Maps pin + a `source_id` 101–113 in `prospects/roster-additions-2026-09-23.csv` |
| `rank_gardeners()` from Nagadevanahalli (12.9362, 77.4940) | **19 rows, all `rank_basis == "distance"`, 0.0–9.3 km** (18 within 5.3 km) |
| Tests | 56 pass; `python3 demo.py` still runs |

**Method deviation from the plan:** OSM had almost no nurseries with phone numbers here, directory
sites hide numbers or return 403, so phones and pins came from read-only Google Maps business
listings in the browser (the same method as the 2026-09-17 Maps pass). A Google Business Profile
phone is treated as the business's own published number, so these rows are `active`. Ayyappa Gardens
is also confirmed by magicpin. Two existing numbers are now double-sourced (Noojibail, Green Nursery).

**Found while checking:** Hasiru Agro's own website and its Maps listing give numbers that differ
by one digit (both are in the gitignored prospect sheet). Status set to `paused` so the pipeline never dials a possibly wrong number; the
founder should confirm which is right. One pair of Maps listings (Goinflora / Inflorescence) share a
phone number and was merged into one row.

Nobody was called, messaged or emailed; no account was created; cost Rs 0.
