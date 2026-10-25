# Verification and reference tools

Run commands below from the repository root. Ordinary simulation builds require .NET 8, not an installation of the original game. Python verification tools use the standard library unless stated otherwise. Use `--dotnet <path-to-dotnet>` for verification scripts when the SDK is not on PATH.

## Five-map protocol checks

`python scripts/check_repository.py` checks local Markdown links, Unity C# metadata and the source files selected for Git. It excludes ignored local caches and flags accidentally selected private binaries or raw journals.

```sh
dotnet build simulation/Headless
python scripts/verify_five_maps.py
```

Exercises both rule sets on all five maps and checks exposed fidelity status, London rail/stations, Custom motorway rejection, weekly choices and refusal of unsupported exact-mode resets. Writes `simulation/Reports/five-map-protocol-checks.json`.

## Regenerate city profiles

```sh
python -m pip install -r scripts/requirements-reference.txt
python scripts/export_reference_profiles.py --game-data "<game>/Mini Motorways_Data"
```

Reads the user's installed bundles without modifying them. Generates `CityCatalog.cs`, `OriginalUpgrades.cs`, `TrainTuning.cs` and `Docs/REFERENCE_DATA.json`. Exported data is numeric terrain/configuration; no original art, code or assemblies are copied into this repository. Review the generated diff and rerun the simulation/protocol checks. A different original game build may produce different data or require exporter changes.

## Installed-assembly component probes

See [ReferenceProbe/README.md](ReferenceProbe/README.md) for random-stream and London rail-topology probes. These run read-only against the user's installed managed assemblies. Committed reports contain numeric results and hashes; original assemblies are not bundled.

`verify_london_rail.py --oracle <probe-output.json>` compares a rail probe result with the built headless host. The optional probe fixture is an array of `{x,y,origin}` cells in original world coordinates. The `cells` array in `simulation/Reports/reference-london-rail.json` provides a reusable numeric London fixture; loop/origin checks do not validate train motion.

## Private original journals

```sh
python scripts/inspect_reference_journal.py "<private>/journal.dat" --output "<private>/envelope.json"
```

Checks the supported header schema and envelope bounds, consumes but omits device strings, and reports city, mode, time, score and object-table counts. It does not decode the full simulation graph or control/replay the original. The sanitized example is `simulation/Reports/reference-london-journal-envelope.json`. Keep raw journals and private captures outside Git.
