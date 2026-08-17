# meta-manager agent protocol

This repo is registered with meta-manager, a local supervisor watching several
projects on this machine. It only knows what's written into
`.meta-manager/status.json` — keeping that current is part of the job.

## How instructions reach you

You do **not** need to run a background loop polling this file. While
you're actively working, checking it at each turn boundary (below) is
enough. When you're idle or between sessions, meta-manager pushes instead of
you pulling: the moment an instruction is issued it tries to actively wake
you (e.g. running a configured command to resume this project, or notifying
a human) rather than waiting for you to happen to check. `managerInstructions.delivery`
records how (or whether) that push worked — you don't need to act on it,
it's just so a human debugging this can tell push vs. self-discovery apart.

## Every check-in (session start, and at least every ~10 min of work)

1. Read the file. If `managerInstructions.text` is set and
   `managerInstructions.acknowledgedAt` is null, that's a pending directive —
   follow it, then set `acknowledgedAt` to now. Leave `text` itself alone;
   only meta-manager sets that.
2. Write your update, keeping fields you're not changing:
   - `lastHeartbeat` — current ISO timestamp, every time.
   - `status` — `healthy` | `attention` | `blocked` | `error` | `done`.
   - `currentTask` — one line, what you're doing right now.
   - `progressNotes` — short free text on what changed.
   - `blockers` — `[{ description, since, needsHuman }]`, empty if none.
     Only `needsHuman: true` for things you truly can't resolve yourself.
   - `nextCheckInMinutes` — how long until your next update. Be honest; it
     sets the threshold meta-manager uses to decide you've gone stale.
   - `detail` — short one-line summary for the dashboard card.
   - `history` — append `{ ts, status, note }`; drop the oldest past ~20.

## Rules

- Only touch `.meta-manager/status.json` for this — it's a reporting
  channel, not your actual task output.
- Keep it valid JSON at all times; a broken write looks identical to stalled.
- Ending your turn/session? Set `status` to `done` or `blocked` — never
  leave it `healthy` if you're not going to keep working. meta-manager has
  no way to know you stopped until the heartbeat goes stale.

## Example

```json
{
  "lastHeartbeat": "2026-08-14T10:32:00.000Z",
  "status": "blocked",
  "currentTask": "waiting on staging API key before running integration tests",
  "progressNotes": "Migrated 6/9 endpoints. Tests pass locally against mocks.",
  "blockers": [
    { "description": "need a staging API key", "since": "2026-08-14T10:30:00.000Z", "needsHuman": true }
  ],
  "nextCheckInMinutes": 15,
  "detail": "Blocked on staging API key"
}
```
