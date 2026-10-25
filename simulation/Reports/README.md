# Validation and reference evidence

Reports establish their stated scope only. Passing reconstruction checks is not proof of original-game equivalence. The current feature/limitation snapshot is [IMPLEMENTATION_STATUS.md](../Docs/IMPLEMENTATION_STATUS.md).

## Current checks

| Report | Scope |
| --- | --- |
| [simulation-checks.txt](simulation-checks.txt) | Latest shared suite run; currently 31 suites |
| [five-map-protocol-checks.json](five-map-protocol-checks.json) | Ten map/version Debug-host runs, status and protocol checks |
| [repository-verification.json](repository-verification.json) | Checks rerun for repository organization and publication |

Reproduce the shared checks with `dotnet run --project simulation/Headless -- --self-test` from the repository root. Then run `python scripts/verify_five_maps.py`. Unity's build entry point also runs the shared suites; it writes `simulation-checks.txt`.

## Original reference evidence

| Report | What it establishes |
| --- | --- |
| [reference-random-vectors.json](reference-random-vectors.json) | 180 values invoked from the installed RNG component; not complete spawn equivalence |
| [reference-london-rail.json](reference-london-rail.json) | 53 ordered cells, loop and origin match the installed topology component; not train timing |
| [reference-london-journal-envelope.json](reference-london-journal-envelope.json) | Sanitized metadata from an original London snapshot; full simulation graph remains undecoded |
| [live-london-observations.md](live-london-observations.md) | Exploratory live comparison, input limitations and station-display correction |
| [parking-reference-update.md](parking-reference-update.md) | Footage links/timestamps, parking changes, checks and remaining approximations |
| [Reference provenance](../Docs/REFERENCE_DATA.json) | Installed assembly/bundle hashes and numeric export scope |

No raw journals, original assemblies, original art or decompiled classes are included. The journal report omits device strings. Reproduction tools are documented in [scripts/README.md](../../scripts/README.md).

## Milestones and archive

`destination-rng-update.txt` and `shared-lots-london-update.txt` describe their dated implementation milestones. Their smaller suite counts describe those milestones, not the latest run.

[archive/2026-10-24/](archive/2026-10-24/) preserves the earlier 17-suite baseline, separate-app and five-map milestones, and bounded Custom evaluations. Historical capture failures and incomplete-feature statements are retained as evidence of what was checked then; they do not supersede current status. Bounded debug-road runs are not learned-agent evaluations.
