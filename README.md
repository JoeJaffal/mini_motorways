# Mini Motorways Simulation Lab

Two separate traffic-construction apps share one C# simulation core:

- **Traffic Lab Original** reconstructs standard play on Los Angeles, Beijing, Tokyo, Dar es Salaam and London.
- **Traffic Lab Custom** uses the agreed unlimited-construction rules for future planning experiments.

Original is functional but **not a validated exact replica**. A separate experimental MaskablePPO learner on `mohammad` uses completed trips as its reward; see [training status](training/CURRENT_STATUS.md). See [simulator status](simulation/Docs/IMPLEMENTATION_STATUS.md) for implemented features, evidence and remaining differences.

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

The self-test currently runs **42 shared suites**. The Python check exercises both rule sets on all five maps. The host accepts one JSON request per line:

```json
{"command":"reset","version":"OriginalReference","scenario":"London","seed":42}
{"command":"reference"}
{"command":"step","ticks":200}
{"command":"observe"}
{"command":"quit"}
```

`reference` builds debug roads and can exhaust Original materials. A stroke can partially succeed, so inspect the returned state. Game failure, rejected scenarios and bounded evaluation limits are distinct outcomes. `exactReplicaValidated` remains false; `requireExact:true` refuses an unsupported exactness claim.

## Training handoff: OriginalReference

Branch `main` supplies the playground. Branch `mohammad` adds a separate experimental CPU training project: see [training setup and commands](training/README.md). Its learner uses normal OriginalReference gameplay actions and an optional read-only connectivity diagnostic; gameplay rules are unchanged. The handoff below describes the playground/learner boundary. The [readiness audit](simulation/Reports/training-readiness.md) passed 60 bounded episodes/replays across all five maps; it does not certify equivalence to the commercial game.

### 1. Install and verify the playground

Install the **.NET 8 SDK** and **Python 3**. Unity, the commercial game, a GPU and ML packages are not required for the headless playground checks. From the repository root, run:

```sh
dotnet build simulation/Headless
dotnet run --project simulation/Headless --no-build -- --self-test
python scripts/verify_five_maps.py
python scripts/check_training_readiness.py
```

Require all checks to pass. The last command tests OriginalReference without training a model and writes `simulation/Reports/training-readiness.json`. If `dotnet` is not on PATH, use its full executable path and pass that path with `--dotnet` to both Python scripts.

### 2. Connect one simulator process per environment

Launch the already built host as a child process with piped stdin/stdout:

```sh
dotnet simulation/Headless/bin/Debug/net8.0/TrafficHost.dll
```

Send one JSON request followed by a newline, flush stdin, then read exactly one JSON response line. Keep the process alive across decisions and episode resets. Use a response timeout and treat a process crash, timeout or `error` response as an integration error, not a game loss. Send `{"command":"quit"}` and close the process when finished. Parallel environments need separate processes.

Reset each episode explicitly, for example:

```json
{"command":"reset","version":"OriginalReference","scenario":"LosAngeles","seed":1000,"variation":"SameMap"}
```

Assert `observation.version == "OriginalReference"` and `observation.unlimitedConstruction == false`. Keep the normal materials, demand and failure rules. Supported scenario names are `LosAngeles`, `Beijing`, `Tokyo`, `DarEsSalaam` and `London`. Do not enable `requireExact`: exact-original parity is unverified and the host deliberately rejects that request.

### 3. Build the model-facing observations

Use an explicit allowlist rather than passing the raw response into the model. A starter observation can contain the current terrain, infrastructure, road connections, building colors/kinds, demand, reservations, pending removals, inventory, current upgrade offers, time and playable bounds. See [the protocol and state definitions](simulation/Headless/README.md) and `simulation/Assets/Simulation/TrafficTypes.cs` for field names.

- Never expose `scheduledSpawns`, `randomAlgorithm`, `randomDraws`, building `upgradeAt` or `plannedDemandMultiplier` as policy inputs. These include future/diagnostic information.
- If targeting information visible to a player, mask terrain and other cells outside the currently playable bounds. Document any additional current-state information given to the model.
- Encode categorical fields, normalize numeric fields, and pad/mask variable-length lists to fixed shapes appropriate for the chosen model. Do not silently drop overflow entries; define and test the overflow behavior.
- Keep raw observations separately for debugging if useful; they must not bypass the filtered policy input.

### 4. Define actions and advance time

Expose only ordinary gameplay actions: waiting; road/bridge strokes; demolition; traffic lights; roundabouts; house-driveway changes; motorway creation/edit/removal; and a choice from the current upgrade offers. The [command reference](simulation/Headless/README.md#request-reference) lists the exact request fields. The wrapper must encode these requests into the chosen model's action space and validate or mask unavailable choices.

Do not expose `reference`, `reset`, `observe`, `step`, `quit`, lab scenarios, stock grants or diagnostic evaluation modes as model actions. The wrapper controls reset and time advancement. In particular, `reference` constructs roads for the agent and is unsuitable for normal training/evaluation.

For an initial experiment, use **one gameplay command, then 20 simulation ticks per decision** (one simulated second). A wait action sends only the step request:

```json
{"command":"step","ticks":20}
```

Construction requests do not advance time by themselves. Advance the same interval after a rejected gameplay action, so the agent cannot freeze time by repeatedly choosing invalid actions. Inspect `accepted` and the returned state: a road stroke can partially succeed, and adjacency alone does not connect road tiles. Reset responses initialize the wrapper's previous score; do not count them as transitions.

### 5. Add the reward and episode contract

The playground returns score diagnostics, not a scalar reward. A minimal **proposed starter reward**, to be selected/versioned by the model developer, is:

```text
reward = tripsCompleted_after - tripsCompleted_before
```

Compute this over the entire gameplay-command-plus-step transition, not just a single response's `tripsDelta`. Keep survival time and final trip score as separate evaluation metrics. No extra failure, color, waiting or construction penalties are agreed or implemented; document any subsequently chosen shaping.

The user subsequently approved [bounded connectivity shaping](training/REWARD_SHAPING.md).
It adds a discounted potential difference on every policy selection; trip-only
remains selectable, and actual trips still define reported game scores.

End the episode on host `terminated` (game failure). Treat host `truncated` as a rejected scenario and flag/discard it rather than scoring it as failure. For the initial trial, impose a **300-second simulated-time cap** in the wrapper and report this as external truncation if the game has not already failed. The raw host does not enforce that cap. Stop sending gameplay actions after an episode ends; reset before the next episode.

The wrapper should implement its framework's reset/step contract, including distinct termination and truncation signals, episode statistics and deterministic seed handling. The algorithm and its dependencies belong to the model developer's training project, not the simulator core.

### 6. Validate the wrapper, then start training in the training project

Before optimizer updates, run scripted valid-action and random-valid-action episodes through the actual wrapper. Check observation shapes/finite values, action encoding, reward calculation, score reset, time advancement on invalid actions, normal failures, time-limit truncation and same-seed replay. Test all five maps and motorway/upgrade/driveway actions. The existing readiness audit checks the raw host; it does not replace these wrapper checks.

For a reproducible first experiment, use seeds **1000–1099 for training** and reserve **2000–2019 for evaluation**. Start on Los Angeles to debug the integration; evaluate all five maps separately before pooling results. These are suggested experiment settings, not changes to the game's rules. Keep evaluation seeds out of training and report per-map trip score, survival time, failures and capped episodes separately.

Record the simulator Git commit (`git rev-parse HEAD`), dependency versions, map distribution, seeds, observation allowlist/encoder, action encoding, decision interval, reward formula and episode cap with every run. Save model checkpoints and configuration in the training project; keep generated artifacts out of this repository's source files. Run a short trial first, verify it produces legal actions and saved checkpoints, then increase the training budget. Training results apply to this unfinished OriginalReference reconstruction; transfer to the commercial game remains untested.

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
