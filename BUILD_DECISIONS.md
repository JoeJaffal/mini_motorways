# Build Decisions

This file explains how the current simulation is built and why. It is separate from the [user's game-design decision log](simulation/Docs/DESIGN_DECISIONS.md). Architecture choices below are implementation decisions; they are not additional design answers attributed to the user.

## 1. Two apps, shared traffic core

**Choice:** build two independent Windows apps from separate scenes. Each scene fixes its rule set through `Rules.ForVersion`; the viewer has no mode switch. The apps have separate product names and application identifiers.

**Reason:** fixes to common traffic behavior should benefit both versions without maintaining two diverging copies. The user chose two separate apps. Each app creates only its own gameplay rule set; shared engine fixes still benefit both. OriginalReference is the default development target; its name does not certify parity.

**Limits:** the original target is unfinished. Exact motorway/parking/rail geometry and rules, resource accounting, expansion validation and trace comparisons remain on the parity backlog. Destination upgrades, shared lots and London trains/stations are functional provisional implementations.

## 2. Unity viewer, independent C# core

**Choice:** Unity 6000.6.0f1 supplies the interactive viewer. `simulation/Assets/Simulation/` contains plain C# without Unity physics or rendering dependencies.

**Reason:** people need to see cars, queues and construction, while training experiments need to advance the same rules without rendering. The .NET 8 host compiles the same core source files, not a second implementation.

**Limits:** the viewer uses independent drawings and GUI controls, not original game art or UI. The earlier C++ playground is isolated in `legacy/cpp/`; root CMake remains a compatible entry point.

## 3. Fixed ticks and seeded runs

**Choice:** advance in 0.05-second simulation ticks and use seeded placement/event randomness. Rendering speed controls how many ticks run, not the rules inside a tick.

**Reason:** tests and experiments should be repeatable. Both fixed-map/varied-event and varied-map/varied-event options are available.

**Limits:** the simulation uses doubles rather than the original fixed-point arithmetic. The Original RNG component now matches the installed numeric stream, but seed initialization and draw ordering remain unverified. Equal seeds are not a claim of equal original-game traces or identical cross-version event histories.

## 4. Explicit links, lanes and persistent cars

**Choice:** adjacent road tiles require explicit connections. Cars follow directed lane paths with turn geometry, acceleration, following gaps, junction conflicts and automatic signals. Each house has two persistent cars with outbound, parking and return stages.

**Reason:** tile colors alone do not explain traffic. The viewer draws the paths that the core actually follows, and the inspector exposes waiting reasons and trip state.

**Limits:** cubic curves, sampled conflicts, parking geometry and some priority/rerouting behavior approximate the recovered original. Internal tests do not establish exactness.

## 5. Read-only reference research; independent implementation

**Choice:** inspect installed managed code and serialized city configuration, then implement the findings independently. Keep private research outside Git.

**Reason:** configured runtime values and actual process logic are stronger evidence than visual guesses or mod defaults. The older BetterMotorways mod helped locate concepts but is not the authority for current original values.

**Included:** numeric city profiles, independently written simulation code, provenance/status descriptions and checks.

**Excluded:** original game assemblies, raw decompiled source, raw bundles, art, local research tools and machine-specific runtime dependencies.

## 6. City profiles are data, not duplicated engines

**Choice:** use `CityCatalog.cs` for Los Angeles, Beijing, Tokyo, Dar es Salaam and London terrain, spawn zones, demand curves and schedules. Keep the working grid at 50 x 30.

**Reason:** the same code should run different city layouts and support controlled variations.

**Limits:** recovered playable bounds and expansion curves are applied within the data canvas, but exact sampling, orientation and scheduling remain unverified. The older `OriginalMapProfile.cs` remains as the earlier LA numeric profile; current city selection uses CityCatalog.

## 7. Separate original inventory from custom spending

**Choice:** original target uses `MaterialInventory.cs` and city-configured starting/weekly material data. Custom has unlimited items and a permanent spending counter: road 2, light 5 additional, bridge water tile 10, roundabout 8.

**Reason:** these are different resource models. Reusing one counter for both would distort the comparison.

**Demolition:** retained traffic clears before release. Original materials become reusable after release; Custom never refunds past spending. Bridge-span reservations prevent returning one bridge multiple times when a span is split/deleted.

**Limits:** exact original bridge validation, roundabout edit accounting and upgrade weighting/history are incomplete. Weekly choices may include original features that are not yet ported; they are labelled accordingly.

## 8. Reject clear shortages; do not reduce Custom demand

**Choice:** after the Custom 30-second new-shop grace, use an optimistic supply-bound screen. Allow potential future supply in growing cities instead of rejecting houses that have not appeared yet. Original target has no custom rejection or 30-second grace.

**Reason:** the user selected rejection of inherently impossible scenarios rather than making them easier by reducing demand. An earlier conservative service estimate is a diagnostic, not proof of impossibility.

**Limits:** the current screen is not a complete feasibility validator and may miss impossible scenarios. Terrain access and supply estimates do not prove joint traffic/parking schedulability. No automatic retry loop or hidden demand reduction is implemented.

## 9. Failure, rejection and evaluation limits are distinct

**Choice:** normal game termination is overcrowding failure. A rejected Custom scenario stops with `scenarioRejected=true`, `terminated=false`, `truncated=true` and a reason. Finite benchmark/evaluation durations are tool limits, not game-ending rules.

**Reason:** an agent should not be blamed for a rejected scenario, and a timed evaluation must not be mistaken for a game loss. Discard rejected runs when preparing training/evaluation data.

## 10. Expose metrics without inventing a learner

**Choice:** record survival time, trips, waiting, spending and raw connectivity diagnostics separately. Describe the approved objective as survival first, waiting/cost secondary; do not invent weights, a learning method or a color penalty.

**Reason:** the user explicitly placed learning-method selection and color-penalty design outside this task. A diagnostic is not a reward.

## 11. Refuse an unsupported exactness claim

**Choice:** expose `exactReplicaValidated=false` and fidelity limitations in observations and the viewer. A headless reset with `requireExact:true` fails while original parity is unfinished.

**Reason:** an original-reconstruction experiment must not be labelled an exact-original training baseline before the remaining mechanics and side-by-side traces are validated.

## 12. Commit reproducible source, not local build caches

**Choice:** keep Unity assets and their `.meta` files, package manifests/lock, project settings, headless source, decision records and selected small validation reports in `simulation/`. Ignore Unity caches, generated IDE files, host build output and standalone binaries.

**Reason:** another teammate should be able to recreate the build with Unity and .NET. Machine-local installation paths and generated caches do not belong in source control.

## Build and check

From the repository root with the .NET 8 SDK:

```powershell
dotnet run --project simulation/Headless -- --self-test
```

In Unity 6000.6.0f1, open `simulation/`, open `Assets/Scenes/TrafficLab.unity`, then press Play. **Traffic Lab > Prepare scene and run checks** regenerates the scene and runs shared checks.

To build the Windows app, use Unity's installed editor executable with these arguments, replacing the paths for your machine:

```text
-batchmode -nographics -quit
-projectPath "C:/path/to/mini_motorways/simulation"
-executeMethod ProjectSetup.BuildWindows
-logFile "C:/path/to/build.log"
```

The outputs are `simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe` and `simulation/Builds/Windows/TrafficLabCustom/TrafficLabCustom.exe`. Each starts directly in its own rules. BuildWindows builds both; BuildOriginalWindows and BuildCustomWindows build individually. Output folders are ignored by Git. The headless development host retains explicit version selection for experiments.

## Validation and interpretation

The current record includes 31 shared suites, protocol tests, Unity Windows builds, viewer checks and five bounded Custom city runs using a debug road builder. Earlier integration fixtures intentionally use historical parameters; they are fixtures, not selectable production modes. New checks cover active custom prices, version isolation, rejection, Original material limits/reuse, seeded map variation, shared lots, trains and parking circulation.

These checks establish internal consistency. They do not prove original parity, optimal networks, universal scenario feasibility, or agent performance. The complete remaining work is in [VERSIONS.md](simulation/Docs/VERSIONS.md).

## 13. Five-map numeric reference data and Original motorways

Original now reads five independently exported numeric profiles, with hashes recorded in `simulation/Docs/REFERENCE_DATA.json`. The fixed 50 x 30 array is a storage canvas containing the selected cities' final playable bounds; recovered zoom curves and starting-offset options determine the current Original play area and viewer framing. Custom retains its fixed area. Starting-offset variance and floating-point curve evaluation are not a claim of original random/fixed-point parity.

Motorways are separate elevated graph edges, not surface tiles or diagonal road bitmasks. They receive independently sampled continuous lane geometry, a recovered 1.5 tiles/s cap, finite stock, retired-state routing and replacement identifiers. Their span consumes no concrete in standard play. On editing, the replacement owns the one motorway slot and old geometry cannot refund it twice. The model preserves old committed round trips before release; exact original ramp geometry, merge priority and release rules still require comparison.

## 14. Original schedules, destinations and component oracle

Original retains full schedule chunk metadata separately from the historical Custom schedule. Circle grouping produces an in-place destination upgrade instead of another shop. Eligibility uses the exported circle masks; weighted age selection and a minimum activation age schedule the change. Capacity changes from six to nine and the demand multiplier doubles, without expanding the lot. Single Original lots have three bays and four supported entrance layouts. Custom remains on its one-size/six-bay baseline. Shared lots and internal parking circulation are implemented; exact entrance boundaries, concurrent traffic and motion timing remain approximate.

The Original RNG is independently expressed and checked against a read-only installed-assembly oracle. Raw numeric results are committed; game binaries and decompiled classes are not. Matching the generator does not establish matching random call order or full simulation behavior.
