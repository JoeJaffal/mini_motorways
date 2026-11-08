# Reviewed opening inputs — 8 November 2026

Use **recorded-la-reviewed-opening60.json** for the manually reviewed first60seconds of the source video (~90simulator seconds).16events,7layout/driveway/stock checkpoints match. This corrects native-stub false road draws and the first red driveway turn; it does not certify exact timing, vehicle behavior or full-game parity. Playback is normal simulator time, not wall-clock synchronized with the source pauses/2x. [Evidence](../../docs/training/replay-input-validation-2026-11-08/README.md).

```powershell
& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe --scenario-file "$PWD\simulation\Scenarios\recorded-la-reviewed-opening60.json"
```

# Current movement audit — 8 November 2026

The installed corrected movement rules replay prefix330 to50trips with no failure. Original **event parity still fails**: first3simulated deliveries17.45/32.05/41.15s versus first-visible original estimates17.418/29.826/47.408s. This remains a reconstruction with unknown original hidden state, not an exact seed replay. [Current measured audit](../../docs/training/event-parity-2026-11-08/README.md). Earlier37-trip and24-trip notes below are historical.

# Current carpark repair checkpoint — 8 November 2026

Use `recorded-la-prefix330.json` to watch the bounded early sequence with the traffic repair. It reaches37trips at330s without game-over in verified headless playback. At matched297.45s, before24/game-over becomes30/no game-over. Reference835 is the full original final score, not the prefix target. Full draft remains visually inferred and now encounters later rejected diagonal edits; do not treat it as a valid complete comparison. [Repair evidence](../../docs/training/video-performance-repair-2026-11-08/README.md).

```powershell
& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe --scenario-file "$PWD\simulation\Scenarios\recorded-la-prefix330.json"
```

# Custom seeds and recorded scenarios

Original player sidebar: enter an integer next to **Use seed**, then apply. This restarts the selected simulator city deterministically. The simulator seed is not interchangeable with the Steam game's seed.

To load fixed recorded spawns/actions, paste a JSON path and select **Load custom scenario JSON**. Playback starts paused; Play, Pause, Step and Restart are available. Recorded actions are read-only during playback. The original-game reference score is a label, never an input to scoring.

PowerShell, from repository root:

```powershell
& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe --seed 12345 --map LosAngeles
& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe --scenario-file "$PWD\simulation\Scenarios\example.json"
& .\simulation\Builds\Windows\TrafficLabOriginal\TrafficLabOriginal.exe --scenario-file "$PWD\simulation\Scenarios\recorded-la-draft.json"
.\tmp\dotnet\dotnet.exe run --project simulation/Headless/TrafficHost.csproj -- --run-scenario simulation/Scenarios/recorded-la-draft.json
```

`--scenario-final` advances to the simulated endpoint before displaying it. `--scenario-verify` runs playback and exits with a log marker; a completed playback may end in game-over before all events. It does not certify original parity. Headless playback has a120-second wall limit and stops on rejected events.

`example.json` is a tiny reproducible positive fixture. `recorded-la-draft.json` is an **unvalidated reconstruction**, not a recovered original seed. Approximate1-second video samples and weekly time anchors determine event times. Before the carpark repair, the replay ended early at24 trips; that historical result is a preliminary diagnostic, not a validated same-seed score comparison. The repaired core gets farther but reaches unvalidated trace edits. Full observations/failed detector revisions and limits: [record](../../docs/training/custom-video-scenario-2026-11-08/README.md).

JSON schema1 requires id, city, seed, duration and events. Optional startingInventory has six counts in road/bridge/motorway/light/roundabout/tunnel order; bounds is[xMin,yMin,xMax,yMax]. Events use simulator seconds in `at`; equal times preserve input order. Building IDs must be unique. `house`/`shop` specify x,y,color,direction/layout; `shared`/`join` create shared destinations; `circle` marks a destination upgraded. `draw`/`erase` specify neighboring endpoints x,y,toX,toY (draw also permits longer raster strokes). `build` specifies a BuildTool string; `motorway`, `editMotorway`, `removeMotorway` use stable IDs/targets. `offer` uses lowercase type/amount/roads fields, followed by `choose` with choice index. `driveway` uses target building ID and direction. Errors stop playback rather than relocating buildings or granting material. A different carrier seed can change hidden demand state; do not tune it against the reference score.
