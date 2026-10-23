# Build Decisions

This file explains how the current simulation is built and why. It is separate from the [user's game-design decision log](simulation/Docs/DESIGN_DECISIONS.md). Architecture choices below are implementation decisions; they are not additional design answers attributed to the user.

## 1. One app, two isolated rule sets

**Choice:** share the traffic engine and select OriginalReference or Custom through `Rules.ForVersion`.

**Reason:** fixes to common traffic behavior should benefit both versions without maintaining two diverging copies. Recreate/reset the world on a version switch so custom prices, grace, rejection and unlimited materials cannot leak into the original target. OriginalReference is the default development target; its name does not certify parity.

**Limits:** the original target is unfinished. Motorways, destination upgrades, exact resource accounting, complete maps/expansion and trace validation remain on the parity backlog.

## 2. Unity viewer, independent C# core

**Choice:** Unity 6000.6.0f1 supplies the interactive viewer. `simulation/Assets/Simulation/` contains plain C# without Unity physics or rendering dependencies.

**Reason:** people need to see cars, queues and construction, while training experiments need to advance the same rules without rendering. The .NET 8 host compiles the same core source files, not a second implementation.

**Limits:** the viewer uses independent drawings and GUI controls, not original game art or UI. The earlier root C++ playground is retained as a separate historical implementation.

## 3. Fixed ticks and seeded runs

**Choice:** advance in 0.05-second simulation ticks and use seeded placement/event randomness. Rendering speed controls how many ticks run, not the rules inside a tick.

**Reason:** tests and experiments should be repeatable. Both fixed-map/varied-event and varied-map/varied-event options are available.

**Limits:** our doubles and seeded random generator differ from the original fixed-point arithmetic and random sequence. Equal seeds are not a claim of equal original-game traces or identical cross-version event histories.

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

**Choice:** use `CityCatalog.cs` for Los Angeles, Beijing and Tokyo terrain, spawn zones, demand curves and schedules. Keep the working grid at 50 x 30.

**Reason:** the same code should run different city layouts and support controlled variations.

**Limits:** these are crops. Exact original city boundaries, expansion, orientation and scheduling are not fully reproduced. The older `OriginalMapProfile.cs` remains as the earlier LA numeric profile; current city selection uses CityCatalog.

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

The output is `simulation/Builds/Windows/TrafficLab.exe`. Launch it normally for the original target or with `--custom` for the Custom version. That output folder is ignored by Git.

## Validation and interpretation

The current record includes 17 shared suites, protocol tests, a Unity Windows build, viewer capture checks and five bounded Custom city runs using a debug road builder. Earlier integration fixtures intentionally use historical parameters; they are fixtures, not selectable production modes. New checks cover the active custom prices, version isolation, rejection, original material limits/reuse and seeded map variation.

These checks establish internal consistency. They do not prove original parity, optimal networks, universal scenario feasibility, or agent performance. The complete remaining work is in [VERSIONS.md](simulation/Docs/VERSIONS.md).
