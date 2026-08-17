<!-- meta-manager:start -->
## meta-manager status reporting

This repo reports to **meta-manager**. Before ending each turn (or every ~10
min of work): read `.meta-manager/status.json`, act on `managerInstructions.text`
if it's unacknowledged, then update `lastHeartbeat`, `status`,
`currentTask`, `blockers`, and `nextCheckInMinutes`. You don't need to poll
this in the background — meta-manager actively pushes new instructions when
you're idle, this check is just for while you're already working. Full spec:
`.meta-manager/PROTOCOL.md`.
<!-- meta-manager:end -->
