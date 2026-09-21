# join.html release & rollback — 2026-09-21
Release: commit adding join.html (static, noindex) + validation docs, pushed to main (GitHub Pages).
Pre-checks done: states opt-in purpose; collects locality/plants/timing/budget only; STOP opt-out line; unsupported "trusted gardener" claim removed; locality no longer sent to analytics.
Smoke test: page loads 200; `?ref=<code>` produces `[ref:<code>]` in the wa.me text; submit opens WhatsApp.
Rollback: `git revert <release-sha> && git push` (or delete join.html). Trigger: page 404s, submit fails, or ref tag missing.
