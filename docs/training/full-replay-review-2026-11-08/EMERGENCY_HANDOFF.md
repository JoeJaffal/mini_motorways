# Emergency stop checkpoint — 8 November 2026

User explicitly requested emergency stop, save current work and continuation plan on branch `mohammad`. Stop all analysis, edits, builds and diagnostics except saving this checkpoint. No matching active diagnostic/player/Unity processes were found at stop. Do not resume automatically. No training was launched.

## What is saved

Current uncommitted engine source is a 77-suite candidate, ahead of the installed 74-suite player. Initial77suite run PASS. Immediately afterward, a small correction deduplicated shared destination slots by physical access in NativeDriveways.cs; that last deduplication has NOT been rerun through tests. Do not describe current final source as fully verified.

Installed player: `simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe`, 74-suite build, Assembly-CSharp.dll SHA256 `a1acf0c5aa4ffc124f6a47e7ea3066377e31f90e954e7ee95fc16c888d612ed5`. Build74 passed74core,7environment,6reward-v4,10map/version checks. Unity prefix330 matches headless50trips/330s/99events; normal LA seed12345 startup20s PASS. Backup69player local at `tmp/full-replay-review-2026-11-08/previous-player-69`. Source75/77not built/deployed. No player is currently open.

Engine repairs in source:
- Physical transit through shared carparks, with both circulation directions, doubled route cost, no bay/delivery credit for pass-through; gate/clearance tracks actual physical lot, not final destination. Shared tests include bent approaches.
- Gate arriving cars before the outside approach turn; retain gate ownership through that approach. Prevents arrival trapping a departing/transit car.
- Deferred removal of explicitly erased degree-zero road cells retained by an old motorway; cleanup after the motorway clears. Protects deliberately placed unrelated roads.
- Retain traffic-light phases for retired connections until committed traffic clears; refresh on release. Car25previously waited indefinitely at20,13after deleting19,13–20,13, withholding concrete.
- Native motorway attachment (75): adding/moving a motorway onto a native driveway endpoint connects it for free. Missing attachment left far cyan39,7unserved. Isolated delivery/return test passes.
- Native common endpoints (77): two distinct native access stubs meeting at an otherwise blank cell form a traversable free join. Cache by network revision; refresh on spawn/turn; attach all matching native stubs. Includes straight spawn and diagonal driveway-turn delivery/return tests. Last dedup edit avoids counting two destinations sharing the same physical carpark entrance as two stubs; rerun required.

## Input reconstruction state and measured limits

Source video: `C:/Users/moham/Downloads/screen-capture (2).webm`, SHA256 c9762eb1d8c474c328b01f59a4a0ca744a0c8a06e2794e2dafe285712b1d4629. Original final835. Seed-915001679is a video-hash carrier, not recovered original RNG. No trained model makes replay decisions. Do not tune traffic/materials/demand to835 or report partial scores as a final comparison.

Latest saved numeric candidate is406events,55houses: `measurements/replay-candidate-v20.json` (copy of local `tmp/full-replay-review-2026-11-08/trace-v20.json`). v20is manually filtered fromv18; build_full_trace.py is only updated throughv20rules and has NOT been regenerated/diffed against the manual candidate. Earlier failed candidates/results remain historical. Strict gameplay stops at rejection; never allowRejection/grant extra stock.

v20with74rules:489trips, game-over1085.35s,294/406events, far cyan0served (unattached motorway). With75native motorway rule:586trips, game-over1185.95s,340/406events, far cyan16served; fails red shared11,18with50.01overcrowding. Many20–38s waits near roundabout19,9/adjacent junctions; no proven new roundabout root cause yet. These are incomplete diagnostic outputs, NOT a validated586vs835comparison. The77source has NOT rerun v20.

Direct topology-only check invokes actual custom-event actions with no physics/demand/score and immediate unused-edge cleanup,30s cap; v20rejects source870at372/406for road stock. This is only placement/material feasibility, not traffic or a valid score. Earlier step-based topology checks hit30s cap and were not extended; direct event-only alternative completes quickly. Source aliases/projects remain local, source helpers archived.

Known actual inventory (source video seconds):90=21,170=23,240=23,280=15,290=15,300=4,320=23,430=11,480=7;540=13,550=12,560/570/590=8,600=0;620/640=7,650/660/670/680/690=5,700/710=0;720=20,730=21,740/750=15,760/790=19;810=32,820=25,830=24,840=19,850=14,860=10,870=4,880/890=13. At853stock12,85514,85611,85710 (verified by timestamped sequential PyAV decode). Inventory mismatches can involve delayed retirements or1–2s detection lag; do not remove arbitrary edges to fit stock.

## Exact next input corrections identified but NOT applied

These are visually supported; implement only after user resumes, and preserve their evidence/uncertainties:
1. Omit false edge24,12–25,12from715onwards (rounded cyan diagonal side). Already omitted false24,11–24,12at549 and25,11–25,12at608; actual cyan diagonal24,11–25,12stays.
2. Omit false9,10–9,11at731onwards: empty side beside cyan8,11NE native stub to9,10; crop740supports. Keep paid9,10–10,10.
3. Omit38,16–38,17and38,17–38,18at841: new green destination spawn-animation circle, not roads. Inspect source840–845/850for exact interval; local `green-late-roads.png` and `green-turn841.png`.
4. Green38,19turns fromSW toN at about845–846 (first unambiguous846); add explicit driveway direction6 there. It is NOT a turn at849:849adds the real branch37,18–38,18→37,19→37,20. Earlier840–844stillSW. Local `green-turn849.png` and `green-turn841.png` preserve this evidence. Native common endpoint38,18with green destination39,16left entrance needs new77rule. Timing has~1s uncertainty; do not assert exact click time.
5. Omit37,20–38,20for841onwards: false horizontal side beside actual SW native/long SE diagonal. Actual diagonal37,20→38,21→39,22→40,23is real and remains. Its earlier841add/849erase are false, and857addis false.
6. Both temporary vertical edges40,21–40,22and40,22–40,23are genuinely drawn853(stock14→12), BOTH erased by855(stockback14). Detector currently removes only the first. Add explicit erase40,22–40,23at855. Diagonal3roads856(stock14→11) and branch37,20–37,21by857(stock11→10) are real. Current branch onset858is~1s late.
7. Omit43,8–43,9from859: actual source is a blue cursor ring on empty grass, not road. Latest local image `far-right-false859.png` visually confirms858/859/860.
These7corrections should explain the accumulating late material shortfall, but this has NOT been run/measured. Do not invent a resulting score or claim full validity.

Other reviewed changes already in v20: yellow35,12birth799(pre-menu pulse), not807; cyan8,8birth664not665. Motorway error-toast at776–780generated false roads/removals across x18–32,y4–7; exclude those road transitions while preserving existing streets. Motorway3placement775probably accepted closer780within same recorded pause; wall-clock timing unresolved. Cancelled road preview31,15–32,15at700–705removed. Five actual roads nearx15at513preserved after stock verification. Old assumptions that those were false are rejected.

## How to resume safely

1. Read root AGENTS.md and this checkpoint. Check git status/branch, preserve unrelated dirty/untracked training work. No learning/diagnostic learning on user's behalf; normal bounded non-learning tests only.
2. Rerun core77after dedup edit:
   `.\tmp\dotnet\dotnet.exe run --project simulation/Headless/TrafficHost.csproj -- --self-test`
3. Implement the identified replay-data corrections in builder and a new versioned candidate, preservingv20and diagnostics. Builder expects local video boards, camera/clock/house/road data under tmp. If tmpis missing, archived helpers and numericv20remain, but crops/normalized frames must be regenerated from the source video; private reference extracts must never be copied into Git.
4. Regenerate candidate from builder and compare with any manual edits. Run direct topology helper using archived source plus a temporary csproj including `../../simulation/Assets/Simulation/*.cs`; no physics/no score. It rejects illegal inputs;30s cap. Then headless `--run-scenario NEW_JSON` existing120s wall cap, stop at first rejected input or normal failure. Inspect per-destination service, routes, current/future lane waits and material state, not just score.
5. If roundabout queue persists on verified inputs, isolate recorded roundabout+adjacent junction geometry and exact stopped-car interactions. Current suspicion of future-junction/yield cycles is a HYPOTHESIS, not an established cause or authorization to blindly remove controls. Existing77tests do not prove original roundabout throughput or bit identity.
6. Validate actual wall-clock playback separately: current viewer uses game-time1/4/16x and bulk-applies actions sharing a paused plateau. Source has1/2xand long pauses. No recorded-clock viewer synchronization implemented yet. Exact action times, some preview commits/native directions and hidden original demand/parking RNG still unverified. Green30,8nativeSouthpartly motorway-occluded remains explicit assumption.
7. After source stabilizes, run7environment/6reward/10map checks with tmp/dotnet on PATH. Do not relax tests or overwrite historical fixtures. Build Original through Unity6000.6.0f1 `ProjectSetup.BuildOriginalWindows` into a NEW staging root using `--traffic-build-root`, hidden background process. Verify Unity/headless scenario agreement and ordinary startup, then backup installed74and deploy. Current77not built. Do not replace the existing reviewed opening with an uncertified full replay.
8. Update this report, design069, experiment history/current status/index and archive manifest with measured outcomes/limits. No long training, weight promotion, original-game writes or pushes are authorized by this work.

## Saved/local-only distinction

Own independent C# and diagnostic scripts, numeric measurements and candidate JSON are durable in repo. No private decompiled code/art/video or generated executable is committed. Raw video/boards/crops, private reference extracts, projects/logs/builds undertmpare local only. Installed binaries/backups not Git-backed. No PDF/graphs created during this continuation. Earlier historical reports remain unchanged.
