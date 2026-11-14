# Working on the repository

## Project boundaries

- `simulation/Assets/Simulation/`: shared, Unity-independent C# simulation.
- `simulation/Assets/Viewer/`: rendering and input. Keep gameplay rules in the core.
- `simulation/Assets/Editor/`: scene preparation, checks and Windows builds.
- `simulation/Headless/`: .NET 8 host using the same core files.
- `legacy/cpp/`: the separate older playground. Root CMake delegates here.
- `scripts/`: maintained verification and reference-data tools, with usage in its README.

Original and Custom are separate apps with fixed scene rule sets. Changes intended only for Original must retain Custom behavior. Never mark `exactReplicaValidated` true merely because internal tests pass.

## Before committing

From the repository root, with .NET 8 and Python 3 installed:

```sh
dotnet run --project simulation/Headless -- --self-test
python scripts/verify_five_maps.py
python scripts/check_repository.py
git diff --check
```

The first command builds the Debug host needed by the second. Currently 42 shared suites cover traffic, materials, version isolation, motorways, shared lots, trains, parking, replay integration, connectivity and draw-effect diagnostics. They test reconstruction behavior, not complete original-game equivalence.

For Unity changes, use Unity 6000.6.0f1 and **Traffic Lab > Build both Windows apps**. This prepares both scenes, runs the shared suites and builds both Windows players. For changes under `legacy/cpp/` or root CMake, also run the legacy CMake build and CTest commands in its README.

When changing reference tools, check their CLI help and syntax; run the relevant component comparison when the installed original game is available. It is optional for ordinary headless builds.

## Documentation

The user requires every material update, decision, analysis and performance
finding to be documented, including PDF content and graphs. Add a chronological
entry to [the training history](training/EXPERIMENT_HISTORY.md) for training
work, with the request, decision, rationale, implementation, checks, measured
outcome, limitations and superseded choices. Distinguish observed facts from
hypotheses. Follow [the evidence procedure](docs/training/README.md) to preserve
reports and measurement sources in Git; ignored run folders alone are not
durable documentation. Update this record during the work, not only at handoff.

- Update [implementation status](simulation/Docs/IMPLEMENTATION_STATUS.md) for current behavior and limits.
- Update [version behavior](simulation/Docs/VERSIONS.md) for rule-set changes.
- Add only actual user decisions to [the decision history](simulation/Docs/DESIGN_DECISIONS.md).
- Put scoped validation evidence in `simulation/Reports/`; distinguish current checks, historical reports, component matches and visual observations.
- Document deferred approximations honestly. The current parking entrance/concurrency approximations were accepted for now; they remain technical limits, not blocking design questions.

## Keep source control clean

Commit Unity source assets with their `.meta` files, package manifests, project settings, maintained tools and small validation reports. Generated city data should be regenerated with the documented exporter rather than hand-edited.

Do not commit Unity caches, player builds, generated IDE projects, .NET output, scratch scripts, credentials, raw game journals, original game binaries/assets or decompiled classes. Private reference research stays outside the repository. `tmp/` and `output/` are ignored local work areas; durable documents belong under `docs/`.
