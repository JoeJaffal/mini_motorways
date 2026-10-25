# Mini Motorways Simulation Lab

Two separate traffic-construction apps share one C# simulation core:

- **Traffic Lab Original** reconstructs standard play on Los Angeles, Beijing, Tokyo, Dar es Salaam and London.
- **Traffic Lab Custom** uses the agreed unlimited-construction rules for future planning experiments.

Original is functional but **not a validated exact replica**. No learning algorithm or final reward formula is implemented in the active simulator. See [current status](simulation/Docs/IMPLEMENTATION_STATUS.md) for implemented features, evidence and remaining differences.

## Start here

| Task | Guide |
| --- | --- |
| Run or build the two apps | [Simulation guide](simulation/README.md) |
| Understand Original versus Custom | [Version specification](simulation/Docs/VERSIONS.md) |
| Run the JSON interface | [Headless host](simulation/Headless/README.md) |
| Review checks and reference evidence | [Validation reports](simulation/Reports/README.md) |
| Work on the code | [Contributing](CONTRIBUTING.md) |
| Find design decisions and archived documents | [Documentation index](docs/README.md) |

## Run the apps

Open `simulation/` with **Unity 6000.6.0f1**. Open `Assets/Scenes/TrafficLab.unity` for Original or `Assets/Scenes/TrafficLabCustom.unity` for Custom, then press Play.

**Traffic Lab > Build both Windows apps** prepares the scenes, runs the shared checks and creates:

```text
simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe
simulation/Builds/Windows/TrafficLabCustom/TrafficLabCustom.exe
```

Player builds are generated locally and are not committed. Each executable has a fixed rule set; neither has a version switch. The original game is not required to run these apps or the headless host.

Select Road to draw from a house driveway to a matching destination. Right-drag removes construction; the mouse wheel zooms, middle-drag pans and Space pauses. Inspect selects a car or building. Original's Motorway tool uses two endpoint clicks; selecting an existing endpoint allows editing. New run changes the seed; Reset city repeats the selected map/settings and seed. Debug reference roads are a construction helper, not an optimal or learned policy.

## Original and Custom

| Mechanic | OriginalReference | Custom |
| --- | --- | --- |
| Maps | Five selected cities; recovered expansion bounds | Same five profiles; fixed working area |
| Construction | Finite city-configured materials | Unlimited items; cumulative spending |
| Prices | Material stock rather than custom point prices | Road 2; light 5 additional; bridge water tile 10; roundabout 8 |
| Demolition | Deferred clearing and material reuse | Deferred clearing; no spending refund |
| Motorways | Two-way links, inventory, retirement and endpoint editing | Excluded |
| Destinations | Upgrades, three-bay single lots, nine-bay shared/station lots | One size with six bays |
| London trains | Functional movement, station demand and crossing closures | No train simulation |
| Parking | Internal circulation, diagonal bays and full-lot drive-through | Existing simpler parking paths |
| New-shop grace | No custom grace period | 30 seconds |
| Feasibility screen | Custom rejection disabled | Reject estimated clear shortages; never lower demand to rescue a run |

Both use automatic color-matching cars and target original-style driving rules. Custom prioritizes keeping the city alive; waiting and spending are secondary, with no invented reward weights. Its feasibility screen is approximate, not proof that a network can satisfy every demand.

## Run and verify without graphics

Install the **.NET 8 SDK** and **Python 3**, then run from the repository root:

```sh
dotnet run --project simulation/Headless -- --self-test
python scripts/verify_five_maps.py
dotnet run --project simulation/Headless
```

The self-test currently runs **31 shared suites**. The Python check exercises both rule sets on all five maps. The host accepts one JSON request per line:

```json
{"command":"reset","version":"OriginalReference","scenario":"London","seed":42}
{"command":"reference"}
{"command":"step","ticks":200}
{"command":"observe"}
{"command":"quit"}
```

`reference` builds debug roads and can exhaust Original materials. A stroke can partially succeed, so inspect the returned state. Game failure, rejected scenarios and bounded evaluation limits are distinct outcomes. `exactReplicaValidated` remains false; `requireExact:true` refuses an unsupported exactness claim.

## Repository layout

```text
simulation/          Active Unity apps, shared core and .NET host
  Assets/Simulation/ Simulation rules and shared checks
  Assets/Viewer/     Rendering and input
  Assets/Editor/     Scene preparation and Windows builds
  Headless/          JSON action/observation host
  Docs/              Current specifications and user decision history
  Reports/           Scoped validation evidence and historical reports
legacy/cpp/          Separate older C++/OpenGL playground and economy checks
scripts/             Maintained verification and reference-data tools
docs/                Documentation index and archived comparison PDF
BUILD_DECISIONS.md   Architecture and implementation decisions
CONTRIBUTING.md      Development and verification workflow
```

Root CMake and `build.sh` remain entry points for the [legacy C++ playground](legacy/cpp/README.md). It has different rules and is not the active Original or Custom simulator.

## Evidence and remaining work

The Original RNG matches 180 values invoked from the installed game; London's 53 ordered rail cells, loop and origin also match the installed topology component. Live observation and selected LA/London video samples informed visual and parking fixes. These are scoped component/structural comparisons, not proof of complete game equivalence.

Exact spawning, random-call order, fixed-point timing, traffic/motorway behavior, material accounting and full original-run comparisons remain incomplete. The current parking entrance/concurrency approximations are accepted for now. [Fidelity notes](simulation/Docs/FIDELITY.md) explain the practical limits.

Only independent implementation and numeric reference observations are versioned. Original game code, art, bundles, raw journals, private research, build caches and player binaries stay outside Git. [Reference tools](scripts/README.md) document optional reproduction against a user-owned installation.
