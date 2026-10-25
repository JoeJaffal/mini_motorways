# Installed-game reference probes

The probe loads the user's installed managed assemblies read-only and invokes the random generator directly. It does not start the game, modify files, or include game binaries.

Run with .NET 8:

```
dotnet run --project scripts/ReferenceProbe -- "C:/path/to/Mini Motorways_Data/Managed"
```

The output contains the installed assembly hash and 180 reference values across five seeds. The checked-in numeric sample is `simulation/Reports/reference-random-vectors.json`; the shared simulation suites compare against those values.

This validates only the generator's numeric stream. The simulation still has different random call ordering, approximate placement rules and floating-point calculations, so matching a seed does not yet reproduce an entire original run.

Launching London Classic generated a journal, preserved privately outside the repository. `scripts/inspect_reference_journal.py <journal.dat> --output <report.json>` reads the supported envelope and gameplay header, omitting device strings. The sanitized sample report is `simulation/Reports/reference-london-journal-envelope.json`. Its object graph uses factory serialization and a compatibility hash; full decoding and live control/replay remain unfinished. This probe is not a full-game recorder.

## Rail topology oracle

The optional `--rail <fixture.json>` mode invokes the installed rail-network component with a numeric array of `{x,y,origin}` cells in original world coordinates. It returns ordered lines and loop/origin metadata. It does not run the original simulation or validate train motion.

Compare its JSON output with the built headless reconstruction using `scripts/verify_london_rail.py --dotnet <dotnet> --oracle <output.json>`. The recorded London result is in `simulation/Reports/reference-london-rail.json`.

For example, extract the numeric fixture from the committed report, then run the probe:

```sh
python -c "import json,pathlib;d=json.loads(pathlib.Path('simulation/Reports/reference-london-rail.json').read_text());pathlib.Path('tmp').mkdir(exist_ok=True);pathlib.Path('tmp/rail-fixture.json').write_text(json.dumps(d['lines'][0]['cells']))"
dotnet run --project scripts/ReferenceProbe -- "<game>/Mini Motorways_Data/Managed" --rail tmp/rail-fixture.json
```

Write fixtures and probe output in a local ignored work directory such as `tmp/` and pass its path to the commands. The probe never changes installed game files.
