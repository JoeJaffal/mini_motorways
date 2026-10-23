# Motorways Simulation Lab

One Unity app with two separate rule sets: **Original target** (default) and **Your version**. The original target is an unfinished reconstruction, not a certified exact replica. See [Docs/VERSIONS.md](Docs/VERSIONS.md) for current behavior and the original-parity backlog.

## Run

Open Builds/Windows/TrafficLab.exe. Choose Original target or Your version. Switching versions resets the run. Use --custom to launch directly into the custom version.

Choose Los Angeles, Beijing or Tokyo, then choose same-map or different-map runs. New run changes the seed; Reset city repeats the current settings/seed. Terrain and schedules come from installed city data, currently cropped to 50 x 30 cells.

Draw roads from house driveways to matching shop entrances. Road strokes automatically build bridge tiles over water. Right-drag removes construction. Inspect selects a car/building; mouse wheel zooms, middle-drag pans, Space pauses. Reference lab and Build reference roads are debugging helpers, not learned policies or optimal-network guarantees. In original mode the helper can exhaust material stock.

## Your version

Unlimited construction; cumulative spending counts every placement permanently. Road 2, light 5 additional, bridge water tile 10, roundabout 8. No demolition refunds or motorways. Original-style driving/intersection/roundabout rules. New shops get 30 seconds before failure/capacity screening. Infeasible scenarios are rejected instead of lowering demand; the screen is approximate and does not prove network feasibility. Staying alive is the primary objective; less waiting and spending are secondary. No learning algorithm, reward weights or color-separation penalty is implemented.

## Original target - unfinished

Custom prices, 30-second grace and custom feasibility rejection are disabled. Limited city-configured materials and weekly choices are present. Motorways, destination upgrades, exact spawn/upgrade/edit behavior, complete maps/expansion and trace validation remain incomplete. The interface and observations say so. Do not use this reconstruction as an exact-original training baseline yet.

## Headless

Headless/TrafficHost.csproj targets .NET 8 and compiles the same simulation files. Run `dotnet run --project Headless`. Send one JSON object per line.

```json
{"command":"reset","version":"Custom","scenario":"LosAngeles","variation":"SameMap","seed":42}
{"command":"draw","x":18,"y":12,"toX":22,"toY":12}
{"command":"step","ticks":200}
{"command":"observe"}
{"command":"reset","version":"Custom","scenario":"LosAngeles","variation":"DifferentMaps","seed":43}
{"command":"reset","version":"OriginalReference","scenario":"Tokyo","seed":42}
{"command":"upgrade","choice":0}
{"command":"quit"}
```

Build, connect and reference (debug) commands remain available. Tools: Road, Bridge, Roundabout, TrafficLight, Remove. Build places a tile; connect links adjacent tiles; draw does both and may partially succeed. Variation is deterministic by seed. OriginalReference is the default version.

Responses contain accepted/message, trip/spending deltas, terminated (overcrowding failure), truncated (scenario rejection), and observation. Discard rejected runs. Observations include version, map, costs, inventory, upgrade choices, grace, positions, lanes, signals, objectives and explicit fidelity status. `requireExact:true` refuses a reset because exact parity is not yet established. No scalar fitness/reward is invented.

## Validation

`dotnet run --project Headless -- --self-test` runs shared checks, including version isolation, custom prices, original road exhaustion/reuse and weekly packages, bridge stock release, scenario rejection, and seeded map choices. Earlier traffic integration checks remain as explicit legacy fixtures; they are not selectable game modes. Passing checks proves internal consistency, not exact original-game parity.

Unity menu Traffic Lab > Prepare scene and run checks; batch build entry point ProjectSetup.BuildWindows. Core and controls remain separate. The old playground and installed game are not modified.


## Decisions and explanations

| Decision | Meaning |
| --- | --- |
| Two versions | Compare the original-game reconstruction with a separate Custom rule set; switching resets the run. |
| Unlimited Custom construction | Track spending as preparation for possible future budget constraints, rather than rationing inventory. |
| Permanent spending | Building costs remain incurred after demolition; rebuilding costs again. |
| Prices 2 / 5 / 10 / 8 | Road 2, light 5 additional, bridge water tile 10, roundabout 8. These are working comparison weights, not calibrated real costs. |
| No Custom motorways | The user wanted simpler scope and considered the original abstraction unrealistic. |
| Keep colors and two cars | Preserve purposeful trips to matching destinations and the simple reusable household fleet. |
| Original driving rules | Automatic cars, signals, junctions and roundabouts target original behavior; legal alternatives are not selected. |
| Survival first | Keeping the city running is primary; waiting and cost are secondary, without invented reward weights. |
| Reject impossible scenarios | Do not silently lower demand. The current optimistic supply screen is incomplete and may miss impossible cities. |
| 30-second Custom grace | Retain the selected working time for connecting a new shop before failure/supply screening. |
| Deferred removal | Retire the road, clear committed traffic, then remove it. Custom spending is never refunded. |
| Both run options | Vary events on one map or vary maps and events; seeds allow repetition. |
| Failure-only endings | Game loss, scenario rejection and bounded evaluation are separate outcomes. |
| Learning and penalties out of scope | No learner, scalar reward or color-separation penalty is implemented in this task. |

The full approved-answer history is in [DESIGN_DECISIONS.md](Docs/DESIGN_DECISIONS.md); current mode behavior and parity gaps are in [VERSIONS.md](Docs/VERSIONS.md). Later decisions supersede historical prices or provisional choices in earlier entries.
