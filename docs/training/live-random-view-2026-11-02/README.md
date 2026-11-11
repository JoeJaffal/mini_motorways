# One random live AI game - 2 November 2026

User requested preparation of one random map game to watch live, no long assistant
execution. Existing native viewer only supports completed replays; no live command
transport. Added watch_live.py and live_view.html: local127.0.0.1 ephemeral HTTP
server, browser canvas polling actual simulator snapshots, one random seed chosen
without outcome filtering, frozen latest upgrades-night-01/validation-best.zip.
This is a simplified browser renderer, not the native Unity viewer. Normal
OriginalReference LosAngeles simulation and saved supported-upgrade flag retained.
No optimizer/training call. Default speed4 simulated seconds per wall second plus
inference overhead, starts paused; browser Play/Pause gates each ordinary command.
Session ends on natural failure or3600simulated-second cap, no auto-reset. Server
stays for inspection until Ctrl+C. Completed replay saved output/live/TIMESTAMP-SEED/game.json.
Browser closing alone does not stop process; Ctrl+C terminal stops it.

Short two-second smoke used random770369501:0trips, cap reached, frozen tensors
unchanged, replay saved. This is wiring evidence only, not skill/performance or a
full live game. No browser visual inspection performed in preparation. Rendering
shows cell terrain/connections/buildings/car positions/light locations, demand and
active overcrowding; it does not show exact native footprint/lane/signal animations.
Play default doesn't change model. Error status reports host problems.

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\watch_live.py
```

Browser opens automatically; press Play. Optional --seed gives reproducibility;
--speed1 slows ordinary command publication, --speed8 speeds it up. Command saves
no weights. Source checkpoint is selected validation-best, not best training game.
No overnight-run analysis was performed; local selected metadata reported239.0
on development maps, not a fresh score claim. Existing uncommitted roadmap/audit
and shared-document edits were present and preserved; commit only new live files.
