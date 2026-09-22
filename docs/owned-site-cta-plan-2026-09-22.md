# Owned-site CTA to join.html — plan & rollback — 2026-09-22

Directive (manager, 2026-09-22T03:45Z): make the funnel discoverable via owned-site links (approved for
production) without waiting on community/founder-WhatsApp permissions; start/reset day 1 once at least
one discoverable entry point is live.

## What's changing
Add a small, clearly locality-scoped, consent-based CTA linking to `join.html?ref=<code>` on the two
highest-traffic *relevant* owned pages (per `sitemap.xml` priorities + topical fit — no Umami dashboard
access from this session, so ranked by sitemap priority and topical match, not live numbers):

1. **`index.html`** (sitemap priority 1.0, the homepage — highest-traffic page on the site) — a one-line
   announcement strip above the nav, explicitly scoped to "Bangalore (Jagajyothi Layout, 560056)" so
   pan-India visitors aren't misled into thinking the service is generally available there.
   `ref=own-site` (already reserved in `validation-7day/ref-codes.csv`).
2. **`blog-vacation-care.html`** (sitemap priority 0.8, topically closest content on the site — the pilot
   is literally the "hire a professional plant sitter" step this post already recommends) — one sentence
   appended to that existing section. `ref=own-blog-vacation` (new row added to ref-codes.csv).

No new data collection on these pages themselves — they only link to `join.html`, which already has its
own explicit consent checkbox, STOP opt-out line, and locality/budget/timing fields. Nothing sent to
Umami beyond a click event (no PII).

## Out of scope (unchanged)
No cold calling, no paid promotion, no community/RWA/Nextdoor posts, no founder-operated WhatsApp status
posts, no Google Business Profile post — all still queued as founder-review items per
`validation-7day/ref-codes.csv`.

## Rollback
- Single commit, easily revertible: `git revert <this-commit-sha> && git push`.
- Or manually: remove the `.pilot-banner` block from `index.html` and the one appended `<p>` from
  `blog-vacation-care.html`; `join.html` itself is untouched.
- Trigger: banner/link 404s, `join.html` submit breaks, ref tag missing from the WhatsApp message, or
  founder asks to pull it.

## Smoke test (post-deploy, this session)
1. `index.html` loads 200, banner visible, link resolves to `/join.html?ref=own-site`.
2. `blog-vacation-care.html` loads 200, new sentence visible, link resolves to `/join.html?ref=own-blog-vacation`.
3. From each entry point: `join.html?ref=<code>` loads 200, the ref survives into the page (via
   `URLSearchParams`).
4. Fill the form, submit: WhatsApp deep link opens with `[ref:<code>]` correctly tagged for both codes.
5. Opt-out path: confirm the STOP/delete line is present and unchanged on `join.html`.

## Day-1 reset
Day 1 of the 7-day validation window starts (or resets) from the date this goes live, since it's the
first discoverable owned entry point (previously `join.html` existed but had zero inbound links).
