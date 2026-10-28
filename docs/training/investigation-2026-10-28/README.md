# Completed investigation evidence

The user authorized autonomous changes and training for a three-hour window
starting 28 October 2026 at 10:40:22 UTC. Ten bounded engineering/training arms
completed; all learning stopped before the final tests. No recurring run exists.

The [10-page report](../model-investigation-2026-10-28.pdf),
[current status](../../../training/CURRENT_STATUS.md) and
[full chronological protocol](../../../training/EXPERIMENT_2026_10_28.md) explain
the results. Best recordings: primitive 126 trips, planner-aided 356. The goal
candidate's deterministic fresh-map mean increased 119.1 to 125.7, entirely one
map (56 to 122); nine tied. Sampled inference averaged 130.4 for both policies.
Most improvement over the old primitive model is engineered assistance, not
demonstrated learning. The 1,000-trip target remains unmet.

## Contents and integrity

- [Evidence manifest](manifest.json): 312 archived configs, source snapshots,
  metrics, logs and exact replay files from ten runs and their diagnostics.
- [Frozen selection](experiments/selection.json): checkpoint hashes and
  development-only selection, recorded before seeds 3000-3009 were opened.
- [Final evaluations](experiments/final-tests/complete.json): five deterministic
  policies plus two sampled goal policies, each on ten scenario seeds. No updates.
- [Assessment](assessment.json): derived analysis, paired differences and report
  narrative; it does not replace the underlying measurements.
- [Report text](report-text.txt), [figures](figures) and [report manifest](report-manifest.json):
  searchable content and graph/PDF/source hashes for the new report.
- [Native best verification](experiments/final-best-native.log),
  [headless verification](experiments/final-best-headless.txt),
  [exact 356-trip recording](experiments/final-best-replay.json) and
  [captured map](best-map.png).

`runs/` retains actual per-arm settings, source snapshots, summaries, episode and
optimizer logs, overall best recordings and dedicated initial/final development
replays. Per-seed best duplicates and all model weights are excluded. All original
local checkpoints and raw logs remain under `output/training/` and
`output/experiments/three-hour-20261028/`.

The archive removes duplicated `episode_replay` keys from metric rows/RESULT lines;
dedicated replay files remain byte-for-byte copies. This preserves every remaining
metric, avoids storing the same command history repeatedly, and leaves raw local
sources untouched. Each manifest entry records the original source SHA-256,
archived SHA-256 and transformation. The report manifest additionally covers
derived assets created after the main evidence snapshot. Historical PDFs and
older archives are unchanged. The repository explicitly tracks these selected
evidence logs; ordinary runtime logs remain ignored.

Published Unity build logs redact device/session/licensing/network-debug identifier lines.
Their original source hashes remain recorded and raw local logs remain untouched.
This does not alter build outcomes, scores, metrics or replay commands.
Machine-generated experiment traces preserve raw whitespace and are exempt from
source-style whitespace lint; SHA-256 checks still enforce their exact integrity.

Read-only verification from the repository root:

[Validation record](VALIDATION.md) records the final hash, rendering review,
runtime checks and publication verification.

```powershell
.venv/Scripts/python.exe training/archive_session.py --destination docs/training/investigation-2026-10-28 --verify
```

Rebuild the report with bundled Python containing ReportLab, Matplotlib, Pillow
and pypdf:

```powershell
python docs/training/build_investigation_report.py
```

The builder reads only archived evidence and never runs a policy. It writes the
tracked dated PDF and a local copy under `output/pdf/`. Rebuilds need visual review
and can change PDF metadata. An assessment rebuild must use a fresh archive; the
script intentionally refuses to overwrite an existing derived assessment.

## Limits

These are adaptive pilots, one optimization seed per arm, five development maps
and ten paired final maps, all Los Angeles. Training best is not a selected-policy
evaluation. Planner-aided actions have restricted tools and deterministic route
execution. Different macro timing changes credit/discount semantics; it is not
only a CPU optimization. Numerical reward scaling never changes game scores.

The primitive draw-noop metric compares road-tile/connection arrays, not every
possible driveway or pending-removal effect. The goal router avoids parcels and
demolition but redraws reused paths (438/668 initial-development draw commands).
This executor inefficiency is documented, not silently fixed after comparisons.
No final-test result was used for another update or candidate selection.

OriginalReference is a reconstruction; these checks do not establish perfect
commercial-game fidelity, reliable 1,000-trip play or other-city transfer. Weights,
generated native players, runtime dependencies and private research are not
published by this evidence archive.
