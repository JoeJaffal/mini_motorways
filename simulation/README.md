# Traffic Lab apps

Original and Custom are separate executables with fixed rules and a shared C# core. [Current status](Docs/IMPLEMENTATION_STATUS.md) describes the implemented systems and remaining differences; [VERSIONS.md](Docs/VERSIONS.md) is the rule-set specification. Original is not yet a validated exact replica.

## Prerequisites

- Unity **6000.6.0f1** for the viewer/editor and Windows builds.
- .NET **8 SDK** for the headless host and shared simulation checks.
- Python **3** for protocol and reference-tool checks. Normal builds do not need the original game or the optional reference-export packages.

## Open in Unity

Open this `simulation/` folder in Unity Hub. Use `Assets/Scenes/TrafficLab.unity` for Original or `Assets/Scenes/TrafficLabCustom.unity` for Custom. Each scene serializes its fixed version; `--custom` does not switch the app.

The selectable cities are Los Angeles, Beijing, Tokyo, Dar es Salaam and London. New run changes the seed; Reset city repeats it. Same-map variation preserves the chosen city; different-map variation selects among those five. Original applies recovered expansion bounds; Custom uses the fixed working area.

## Controls

| Action | Control |
| --- | --- |
| Draw a connected road stroke | Select Road, then left-drag from a house driveway or destination entrance |
| Change a house driveway | Select Road and drag from the house toward its new exit; cardinal and diagonal exits are supported |
| Place a roundabout | Select Roundabout and click a clear footprint; traffic can keep moving during conversion |
| Build across water | Road strokes place bridge tiles, subject to the selected version's rules |
| Remove construction | Right-drag; committed traffic must clear before removal |
| Inspect | Select Inspect, then click a vehicle, building or tile |
| View paths | Enable Lane routes |
| Zoom / pan | Mouse wheel / middle-drag |
| Pause | Space or the Play/Pause button |
| Original motorway | Select Motorway, click two endpoints |
| Edit a motorway | Select an existing endpoint, then its new position; Escape cancels |

Reference lab and Build reference roads are debugging helpers, not trained policies or network-quality guarantees. Original debug construction can exhaust material stock.

## Build both Windows apps

Use **Traffic Lab > Build both Windows apps**. This regenerates both scenes, runs the shared checks and builds:

```text
Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe
Builds/Windows/TrafficLabCustom/TrafficLabCustom.exe
```

Individual menu entries build Original or Custom. **Prepare scene and run checks** prepares/checks without building players.

For a batch build, invoke the installed Unity editor with:

```text
-batchmode -nographics -quit
-projectPath "<repo>/simulation"
-executeMethod ProjectSetup.BuildWindows
-logFile "<local-output>/build.log"
```

Require the successful build marker `TRAFFIC_SIM_BUILD_PASSED: two separate apps` in the log. Unity startup can launch asynchronously; do not infer completion solely from the shell returning. Generated caches, IDE files and player builds are ignored by Git.

## Verify and use the headless host

From the repository root:

```sh
dotnet run --project simulation/Headless -- --self-test
python scripts/verify_five_maps.py
dotnet run --project simulation/Headless
```

The first command builds the Debug host that the Python check uses. There are currently 37 shared suites. Unity builds invoke those same checks. See [Headless/README.md](Headless/README.md) for requests and observations.

Player startup checks use `--smoke-test --map London -batchmode -nographics`; replace London with another supported enum name. A successful run logs `TRAFFIC_APP_SMOKE_PASSED=<version>/<map>/20` and exits. These checks run 20 simulated seconds with debug roads; they do not inspect rendered pixels or prove exact original behavior.

## Documentation and evidence

- [Implementation status](Docs/IMPLEMENTATION_STATUS.md): current behavior and accepted approximations.
- [Version specification](Docs/VERSIONS.md): Original and Custom rules.
- [Design history](Docs/DESIGN_DECISIONS.md): actual user decisions, including later changes.
- [Fidelity notes](Docs/FIDELITY.md): evidence and limits.
- [Reports index](Reports/README.md): current and historical validation.
- [Reference tools](../scripts/README.md): numeric export, component probes and journal envelope inspection.

The core stays in `Assets/Simulation/`; the viewer stays in `Assets/Viewer/`. Shared source does not imply identical event streams between rule sets. Keep original game files and private research outside the repository.
