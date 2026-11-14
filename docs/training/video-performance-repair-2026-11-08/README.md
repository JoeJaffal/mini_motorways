# Recorded replay performance repair — 8 November 2026

User decision: after watching the draft replay, user authorizes analyzing the large performance difference and tweaking the playground. Supersedes the no-gameplay-change scope of custom seeding (design064). No training, fitting to835, seed search, inventory/demand grants or original parity claim.

## Measured paired result

Same carrier seed, same event prefix, same297.45-second checkpoint:

| Measurement | Before | After v3 |
| --- | ---: | ---: |
| Completed trips |24|30|
| Failed |yes|no|
| Red destination deliveries |2|9|
| Red destination demand |10|3|

After v3 continues to330 seconds with37trips, no failure, all99 scheduled prefix events applied and no car waiting>20s at the checkpoint. This is not a same-time37vs24 comparison. Original HUD49 at video170 and final835 stay historical source observations; unknown original hidden state and invalid later trace prevent an exact parity comparison. The first330s still contain visually inferred events; this fixture demonstrates simulator improvement on identical inputs, not fully verified original choices.

## Causes and engineering changes

1. **Measured code mismatch:** MakeLanes omits zero-length surface lanes at carpark boundaries. Entrance reservations were keyed to the omitted parcel lane, allowing incoming cars to bypass opposing exit reservations. Recognize the final surface lane and also gate it while current, holding an incoming car before the entrance until the reservation clears.
2. **Measured queue cycle:** the first repair exposed two physical merge cars nose-to-side: each could advance into the other's required bay-exit turn, then collision guards stopped both indefinitely. Reserve the short first-two-lane bay departure sweep while underway; following circulation leaves clearance. Vehicles already ahead on a subsequent lane retain priority so a later merge cannot stop the leader clearing it. Existing physical body guards remain active. This is our independently implemented fix, not proof of original merge code equivalence.

Scope: traffic control only plus diagnostics/regression data. Demand, car speed/size, car following constants, supply, material stock, reward choices, original reference score and carrier seed not tuned. Normal and custom scenario playback use the same traffic core. Historical learned results remain tied to their earlier simulator.

## Chronological review / rejected intermediate versions

- Baseline on original draft:24trips, failed297.45s; red served2/demand10. Cars wait142.2s/139.1s on lane clearance/entrance merge; entering car141.9s. State summary archived.
- First entrance-only v1 gets past old video failure but existing roundabout-conversion platoon test fails5/6trips. Diagnostic at400s: cars3and4 block each other at bay merge; car4 owns entrance reservation. Do not ship v1.
- v2 reserves bay sweep but existing eight-car queue test fails: all8deliver, last2cannot return. Exit leader wrongly yields to the later merger's future turn. Do not ship v2.
- v3 retains priority for the leader already ahead of the merge. Existing58 suites pass. Added8 orientation/seed queue cases and1 recorded-prefix regression: total67pass. Queue tests require delivery, return, concurrent parking and physical body separation; recorded fixture requires all inputs applied, survival and no persistent queue, not an exact implementation-dependent score.
- Diagnostic serialization initially failed because Point exposes recursively computed Unit/Right properties; flattened coordinates. Scratch ownership inspection initially had an invalid dictionary cast, corrected to typed dictionary. These tooling failures are not gameplay findings.
- Adapter invocation from repo package names first failed local imports, then missing PATH dotnet. Corrected by unittest discovery with local SDK on PATH:7 environment and6 reward PASS. Ten map/version protocol checks PASS. No checks were relaxed.

## Trace validation remains separate

After the traffic fix, the old full draft first rejects a crossing diagonal at353.05s (video198). The inspected crop shows orthogonal roads/house stub; two CV corner/halo diagonals are false. A separate **v8 diagnostic trace** removes those visible false edges/pair disappearance (before video600), without altering road legality or inventory. v8 then reaches466.65s,64trips,132/777events and rejects another crossing diagonal near bridge(video258). Crop again shows an orthogonal corner.64 is a partial pre-rejection score, NOT a final score or a validated comparison.116 distinct inferred diagonal edges remain in that trace; do not erase them wholesale, skip errors or present a full835 comparison. Later visual events still need review. Production full draft not silently rewritten; separate prefix330 supports watchable bounded validation.

## Verification and reproduction

From repo root:

```powershell
.\tmp\dotnet\dotnet.exe run --project simulation/Headless/TrafficHost.csproj -- --self-test
.\tmp\dotnet\dotnet.exe run --no-build --project simulation/Headless/TrafficHost.csproj -- --run-scenario simulation/Scenarios/recorded-la-prefix330.json
$env:PATH = "$PWD\tmp\dotnet;" + $env:PATH
.\.venv\Scripts\python.exe -m unittest discover -s training -p test_environment.py
.\.venv\Scripts\python.exe -m unittest discover -s training -p test_rewards.py
.\.venv\Scripts\python.exe scripts/verify_five_maps.py --dotnet "$PWD\tmp\dotnet\dotnet.exe"
```

All checks are non-learning; fixture budgets are fixed (queue6000ticks/300simseconds per case; prefix330s; headless custom replay120-second wall cap). No diagnostic learning or long training launched. Unity build pending. Do not replace a running player until it is closed gracefully. Generated players/logs, video/crops and private source assets stay local; archived only own code/numeric measurements. Global repository Markdown checker retains the previously documented pre-existing non-UTF8 historical report blocker; do not claim a global clean check.

## Installed and opened

Unity build/core checks PASS; staged player prefix37/330/99 matches headless, normal Original LA startup20s PASS. Installed at usual simulation/Builds/Windows/TrafficLabOriginal path after gracefully closing the read-only previous replay. Previous build backed up locally at tmp/video-performance-repair-2026-11-08/previous-player. Installed Assembly-CSharp SHA256896AF3A97E05E4450C5A7B0671CA81669BDFFF7D2DA88B2B9C6A93B636260578. Reopened prefix330 visibly, paused at the beginning. Final status supersedes earlier pending-build notes. Generated logs/binaries remain local-only.

Watch: `TrafficLabOriginal.exe --scenario-file <absolute path to simulation/Scenarios/recorded-la-prefix330.json>`, then Play. Normal new/reset city also uses repaired traffic. This is the bounded early repair checkpoint, not the full recorded original game. No commits/pushes/training. v2 source was not separately captured; v2 output and its exact subsequent leader-priority correction are recorded, while before/v1/accepted-v3 source snapshots are preserved.
