# Jagajyothi Layout service-area page — plan & rollback — 2026-09-22

Directive (manager, 2026-09-22T09:23Z): publish one reversible, no-contact organic acquisition
asset — a useful Jagajyothi Layout plant-care/service-area page with a consent-based CTA to
`join.html`, a unique referral code, contextual links from the homepage and the vacation-care
article, and sitemap inclusion. Pre-approved for owned-site production publication once
navigation/attribution/submission/opt-out/metadata/mobile checks pass.

## What's changing
1. **New page `jagajyothi-layout-plant-care.html`** — genuinely useful content (Bangalore/JJ Layout
   climate context, a watering-frequency guide for plants common in Bangalore homes), not just an
   ad. No fabricated testimonials or unsupported claims (per the 2026-09-21 fix where an
   unsupported claim was removed from `join.html` — same bar applies here: every claim about the
   service is hedged as "piloting" / "gauging interest," not an established track record).
   Ends with a consent-based CTA to `join.html?ref=own-locality-page` (new code, reserved below),
   with the same opt-out framing as `join.html` itself repeated inline so the page doesn't imply
   anything `join.html` doesn't already say.
2. **`sitemap.xml`** — add the new page, priority 0.7 (below the homepage/blog posts, since it's a
   narrower locality page), monthly changefreq.
3. **Contextual link from `index.html`** — a 4th card in the existing "Plant Care Guides & Tips"
   blog grid (same pattern as the other three cards), linking to the new page. This is additive to
   the existing pilot banner (unchanged) — the banner sends ready-to-opt-in visitors straight to
   `join.html?ref=own-site`; this card sends browsing visitors to the new content page first.
4. **Contextual link from `blog-vacation-care.html`** — one sentence inside the existing pilot
   paragraph (the one added 2026-09-21/22, `ref=own-blog-vacation`), pointing Bangalore readers to
   the new page for local specifics, before they hit the WhatsApp opt-in link.

## Referral code
`own-locality-page` — added to `validation-7day/ref-codes.csv` as `owned`, channel = "new
Jagajyothi Layout plant-care page → join.html CTA," status `live-2026-09-22`.

## Pre-publish checks (all must pass before push)
- **Navigation**: nav bar links back to `index.html` and to WhatsApp; no dead links; page reachable
  from two contextual links (home, blog).
- **Attribution**: no fabricated reviews/stats for this locality; claims match the "piloting/gauging
  interest" framing used elsewhere in the funnel.
- **Submission**: CTA resolves to `join.html?ref=own-locality-page`; ref survives into the WhatsApp
  message via `join.html`'s existing `URLSearchParams` handling (already verified for the other two
  codes on 2026-09-22; same mechanism, no new code paths).
- **Opt-out**: STOP/consent line visible either on the page itself or restated immediately above the
  CTA, not just buried on `join.html`.
- **Metadata**: `<title>`, meta description, canonical URL, viewport tag, favicon — matching the
  pattern used on `blog-vacation-care.html`.
- **Mobile**: reuses `styles.css`'s existing `.navbar`/`main`/`.content` patterns and the site's two
  existing breakpoints (900px, 480px) rather than introducing new fixed-width layout — same
  approach already proven on `blog-vacation-care.html`.

## Out of scope (unchanged)
No paid promotion, no cold outreach, no automated calls, no community/RWA/Nextdoor/GBP posting —
still founder-review items in `validation-7day/ref-codes.csv`.

## Rollback
- Single commit, easily revertible: `git revert <this-commit-sha> && git push`.
- Or manually: delete `jagajyothi-layout-plant-care.html`, remove its `sitemap.xml` entry, remove
  the 4th blog card from `index.html`, remove the one added sentence from `blog-vacation-care.html`.
  `join.html` itself is untouched.
- Trigger: page 404s, CTA/ref breaks, an unsupported claim is flagged, or founder asks to pull it.
