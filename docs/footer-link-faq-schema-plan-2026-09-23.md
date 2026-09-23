# Sitewide locality-guide footer link + FAQ/JSON-LD — plan & rollback — 2026-09-23

Directive (manager, 2026-09-23T03:45:49Z): execute the ranked autonomous pipeline — sitewide locality-guide
link, FAQ/JSON-LD on the locality page, and final copy for founder-posted WhatsApp Status / Instagram.
Pre-approved for owned-site publication; no new data collection, no new channels beyond what's already
authorized in `validation-7day/ref-codes.csv`.

## What's changing

### 1. Sitewide footer link to `jagajyothi-layout-plant-care.html`
Currently the locality page is linked from only two places (homepage blog grid, `blog-vacation-care.html`
inline CTA). Add one line to the `contact-info` block of every page's existing `<footer>` (footer markup
already present on all four; no new footer created):
- `index.html`
- `blog-indoor-summers.html`
- `blog-potting-mix.html`
- `blog-vacation-care.html`

Link text: "Jagajyothi Layout plant-care guide" → `jagajyothi-layout-plant-care.html` (no ref param — this
is internal site navigation, not a tracked acquisition channel; the page's own CTA already carries
`?ref=own-locality-page` to `join.html`). Uses the existing `.contact-info a` CSS rule (accent color, no
inline styling needed), so it visually matches each page's current footer.

`jagajyothi-layout-plant-care.html` itself is skipped (no self-link in its own footer).

### 2. FAQ section + FAQPage JSON-LD on `jagajyothi-layout-plant-care.html`
Static content only, appended after the existing "Going away" CTA block, before `</main>`. Five questions,
all consistent with claims already live on the page and `join.html` (pilot not confirmed, WhatsApp-only,
opt-in, STOP to delete, no price commitment). Matching `FAQPage` JSON-LD block added to `<head>` for
AEO/search. No new tracked link — the existing `join.html?ref=own-locality-page` CTA is unchanged.

### 3. Ready-to-post copy for `own-wa-status` / `own-insta`
Documentation only (`docs/owned-channel-copy-2026-09-23.md`), no code change. Two short, ref-tagged
`join.html` links for the founder to paste into WhatsApp Status and Instagram bio. This session cannot
post to either account; the founder pastes/posts manually per `validation-7day/ref-codes.csv` (both rows
already `status=ready` / `ready-if-account-exists`).

## Out of scope (unchanged)
No new opt-in fields, no changes to `join.html` itself, no community/RWA/Nextdoor/GBP/partner-card work
(still founder-review only), no change to the 2026-09-28 checkpoint or its ≥10 qualified-opt-in / ≥3
paid-commitment (≥₹60/visit) thresholds.

## Rollback
- Single commit per change (or one combined commit), revertible with `git revert <sha> && git push`.
- Or manually: remove the one `<p>` footer line from each of the four pages; remove the FAQ `<div>` block
  and the `<script type="application/ld+json">` block from `jagajyothi-layout-plant-care.html`.
- Trigger: any page 404s or fails to render post-deploy, the footer link resolves to the wrong file, the
  JSON-LD fails schema validation, or the founder asks to pull it.

## Smoke test (post-deploy, this session)
1. Each of the four pages loads 200 live and the new footer link resolves to
   `/jagajyothi-layout-plant-care.html` (200).
2. `jagajyothi-layout-plant-care.html` loads 200, FAQ section renders, JSON-LD block is present and
   well-formed (parses as JSON).
3. Existing `join.html?ref=own-locality-page` CTA on the locality page is unchanged and still resolves
   with the ref param intact.
4. No change to `join.html` itself — spot check it still loads 200 with STOP/consent copy unchanged.
