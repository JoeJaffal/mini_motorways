# Mini Motorways Simulation Lab

A visual traffic-construction environment for comparing an original-game reconstruction with a custom version. One Unity app contains two isolated rule sets and a shared C# simulation core that also runs without graphics.

**The original-game replica is unfinished.** OriginalReference is the default development target, not a certified exact replica or a ready-to-use exact-original training baseline. The custom version is runnable; no learning algorithm or final reward formula has been implemented.

## What's in this repository

| Location | Purpose |
| --- | --- |
| [simulation/](simulation/) | Current Unity app and shared simulation core |
| [simulation/Headless/](simulation/Headless/) | .NET 8 action/observation interface for future training |
| [BUILD_DECISIONS.md](BUILD_DECISIONS.md) | Build and implementation decisions, explanations, and trade-offs |
| [Design decision log](simulation/Docs/DESIGN_DECISIONS.md) | Full chronological record of the user's answers; later entries supersede earlier ones |
| [Version specification](simulation/Docs/VERSIONS.md) | Current behavior of each version, limitations, and parity backlog |
| Root C++ files | Earlier playground, retained separately from the new Unity implementation |
| [Legacy guide](docs/LEGACY_PLAYGROUND.md) | Historical C++ documentation; not the current simulator specification |

## The two versions

| | Original target | Your version |
| --- | --- | --- |
| Selected rules | OriginalReference (default) | Custom |
| Purpose | Reproduce the installed original game | Explore the team's traffic-planning changes |
| Construction | Limited city-configured materials | Unlimited items, with cumulative spending |
| Weekly materials | Partially implemented original-style choices | None |
| Point prices | No custom construction prices | Road 2; light 5 additional; bridge water tile 10; roundabout 8 |
| New-shop grace | No custom grace period | 30 seconds |
| Feasibility modification | Custom rejection/capping disabled | Reject clear supply shortages; do not lower demand to rescue a scenario |
| Driving rules | Original-game replication target | Same original-game target |
| Motorways | Required for parity; still missing | Deliberately excluded |

The two versions share unresolved traffic/spawning approximations. Changing versions resets the episode so inventory, spending and custom rules do not carry over.

## Confirmed decisions and what they mean

These summarize the user's decisions, including the update of **24 October 2026**. They distinguish approved behavior from the implementation's remaining limitations.

| Decision | Description and explanation |
| --- | --- |
| **Keep the city alive first** | The custom agent's primary goal is keeping the city running. Less waiting and lower construction cost are secondary. No weights or priority between those two secondary goals have been chosen. |
| **Unlimited construction, spending tracked** | Real planning uses a budget rather than a fixed inventory of items. Unlimited items plus a spending counter prepares for a future budget constraint; there is no active budget limit now. |
| **Count all construction ever placed** | Every successful placement adds permanently to spending. Demolition does not erase money already spent; rebuilding costs again. An extra demolition fee is only a future option. |
| **Current prices: 2 / 5 / 10 / 8** | Road tile 2, traffic light 5 additional, bridge water tile 10, roundabout 8. A road plus a light costs 7. These are provisional comparison weights, not calibrated real-world prices. Road 2 supersedes the earlier price of 1. |
| **No motorways in Custom** | The user considered their abstraction unrealistic and wanted simpler scope. They remain a possible later feature; the original target still needs them. |
| **Two reusable cars per house** | Retain the original-style simple city foundation: each car travels to a destination and returns to its own house before another trip. Variable fleets are deferred. |
| **Keep matching colors** | Cars serve matching destinations, preserving an actual goal that may be far away instead of always serving the nearest shop. Designing a color-network penalty is outside the current task. |
| **The agent builds; cars drive themselves** | Infrastructure is the agent's responsibility, as for the original player. Dispatch, route selection, signals and driving are automatic. |
| **Original intersection and roundabout rules** | Both versions target the original behavior. A Lebanese-law alternative is not selected for this task. More realistic signal behavior is also deferred. |
| **One shop size for now** | Custom keeps one destination size. Larger shops/upgrades are outside its current scope; they remain required work for original-game parity. |
| **Reject impossible scenarios** | The user chose rejection instead of reducing demand to make a bad scenario easier. The current optimistic supply screen can reject clear shortages but is not a complete proof of feasibility and may miss impossible scenarios. |
| **Keep 30 seconds for new shops** | Custom retains a 30-second grace period before failure/capacity screening. This is a chosen working setting, not an original-game timing claim. |
| **Retire roads before removing them** | Stop assigning new trips to a deleted road, let committed traffic clear, then remove it. Custom spending is never refunded. Precise original release timing remains under verification. |
| **Both run-variation options** | Run varied events on one selected map, or vary both maps and events. Seeds make a particular setup repeatable. |
| **Original maps, fixed working area** | Current profiles are Los Angeles, Beijing and Tokyo, using 50 x 30 crops of recovered terrain/schedule data. They are not full original maps or original expansion behavior. |
| **Failure-only game endings** | Overcrowding ends a normal episode. Evaluation tools may stop at a chosen duration, which is truncation rather than game failure. Rejected custom scenarios are reported separately and should be discarded. |
| **Separate score from spending** | Trips, time, waiting and spending remain separate metrics. Selecting RL/evolution and constructing a numerical reward/fitness are outside this task. |

Budgets, demolition charges, one-way roads, variable fleets, larger Custom shops, map expansion, Custom motorways and redesigned signals remain postponed. No additional rationale is inferred where the user supplied only a choice.

## Run the viewer

1. Install Unity **6000.6.0f1** and open the `simulation/` folder in Unity Hub.
2. Open `Assets/Scenes/TrafficLab.unity` and press Play.
3. Select **Original target** or **Your version**, choose a map and run-variation option, and draw roads from house driveways to matching shops.

**Controls:** drag to draw, right-drag to remove, mouse wheel to zoom, middle-drag to pan, Space to pause. Inspect selects a car/building; lane routes show the actual paths. New run changes the seed; Reset city repeats the current settings and seed.

The reference lab and reference-road builder are debugging helpers, not trained agents or optimal-network guarantees. In original mode the helper can exhaust materials.

Built binaries are not committed. Build a Windows executable using **Traffic Lab > Prepare scene and run checks**, then the batch entry point described in [Build Decisions](BUILD_DECISIONS.md#build-and-check).

## Run without graphics

Install the .NET 8 SDK. From the repository root:

```powershell
dotnet run --project simulation/Headless -- --self-test
dotnet run --project simulation/Headless
```

The host reads one JSON request per line and returns one JSON response:

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

Commands also include build, connect and reference (debug). A single build does not connect adjacent tiles; draw or connect does. A stroke may partially succeed, so inspect the returned links/state.

Observations identify the version, actual map, costs, grace, inventory, pending upgrades, vehicles, signals, objectives and fidelity status. `terminated` means game failure; `truncated` signals scenario rejection for normal actions. Bounded evaluation reports its own duration truncation. `exactReplicaValidated` is false, and `requireExact:true` refuses a reset rather than certifying unfinished original parity.

## Evidence, tests and remaining work

Mechanics and configured values were inspected read-only from the user's installed original game. Numeric terrain/configuration observations inform the new implementation; original assemblies, raw decompiled source, art and private research files are not part of this repository. See the [fidelity notes](simulation/Docs/FIDELITY.md) and [version specification](simulation/Docs/VERSIONS.md) for the distinction between recovered behavior and approximations.

The recorded checks include **17 simulation suites**, version/protocol checks, a Windows build, and five Custom seeds running for 300 simulated seconds with debug-built roads. These are internal consistency checks and smoke tests, not proof of original-game parity or trained-agent performance. Reports are in [simulation/Reports/](simulation/Reports/).

Original parity still requires motorways, destination upgrades, full maps/expansion, exact parking/lane/spawn/edit/upgrade behavior and controlled comparisons against the running original. These are implementation tasks; the user's current design answers are recorded.
