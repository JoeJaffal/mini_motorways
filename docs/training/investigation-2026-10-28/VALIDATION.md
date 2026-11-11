# Final validation record

Validated on 28 October 2026 after all ten bounded training arms and seven frozen
final-evaluation jobs completed. This record is a QA supplement; the main and
report manifests separately identify the underlying evidence and delivered PDF.

## Report

- Ten pages, built with ReportLab and five Matplotlib figures plus a native map
  capture. Text is searchable and preserved in report-text.txt.
- Final PDF SHA-256: `7d39b698cf2352f726d184e040c1faad120db908abfacd3f244fd5e449231625`.
- The tracked PDF and local output/pdf/three_hour_model_investigation.pdf are
  byte-identical.
- All ten pages were rendered by Poppler at a 1,200-pixel maximum dimension and
  visually inspected: readable labels, aligned tables, clear source/method
  distinctions, complete page numbers and no clipped or overlapping content.
- The final wording/cover revision changed only rendered pages 1 and 7. Both
  were inspected again; the other eight final PNG hashes matched their already
  inspected renders exactly. Scratch renders stay local under tmp/pdfs/.

| Render | SHA-256 |
| --- | --- |
| page-01.png | `b0df1a808c0b4efa7df6d94edd1cad4a0e376ca21bcc7f323ffb8eee63790cfa` |
| page-02.png | `0f7d673d512b86b768d3b0043c9ce943424a77f24868b9cd0498aa754ec0203f` |
| page-03.png | `e671e8b11936460f64984f88350bd38b3940d5eb876c2188fcf973bd13180c0c` |
| page-04.png | `a3fc2691bcf4a49e76334dbdbd28cf3ad1e1bccabbe05e543185cb02e77e1016` |
| page-05.png | `3f68080d1cde553eaf8e876c0cc67aa5130a7ece390e8a13f841dc162bf6737e` |
| page-06.png | `ae8f7281c42878149d02a0f0663d9a9e9994b4c5774aae404e9cc49e89e47b21` |
| page-07.png | `2cbb25349418b1d48e022889d873b2d0a832aaafbe9ff350e51d6ead79768ffc` |
| page-08.png | `96eb546b72917325923eda05f3224f8082e8401eed3d8045b8803ff50795201e` |
| page-09.png | `bf0990f10b150457db9bfcc8fd646d3bda94346d97b95a88a1f7e37d87d20a05` |
| page-10.png | `edc080a05b3b30fcdd0772e7d51279f5beb3b590d726eb3163deb8704ea39754` |

## Numerical and runtime checks

- Main evidence: 312 entries. Combined main/report integrity check: 324 entries
  verified. Earlier historical archive: 56 entries verified unchanged.
- All final evaluations contain exactly seeds 3000-3009 in order and verified
  unchanged policy parameters. Selection was frozen before testing.
- Deterministic goal difference: one gain of 66 trips on seed 3006; nine ties.
  Means 119.1 and 125.7. Sampled score pairs were checked individually and tied
  on every map, both means 130.4.
- Frozen initial weights/empty optimizers matched across all four goal arms;
  actor and critic changes were separately observed during training.
- Native/headless best recording: 356 trips, seed 1075, 971.65 seconds, 972
  commands, completed normal failure. Both exact replay checks passed.
- OriginalReference native build succeeded and ran 42 shared simulator suites.
  Five-map protocol checks passed ten runs. Python suites passed 31 checks:
  environment 7, reward 6, workflow 4, parallel 4, shutdown 1, feature/migration 4,
  draw mask 1 and goal adapter 4.
- Four-worker resume smoke inherited .01 scale and choice-only timing, changed
  no weights and repeated the same frozen 161-trip development game.
- Two repeated sampled development evaluations reproduced exact metrics and
  ordinary command histories with requested per-scenario RNG initialization.
- Runtime package versions and binary/source-tree hashes are recorded in
  experiments/runtime-provenance.json. No package installation/upgrade occurred
  during this study.

## Archive and publication hygiene

Dedicated replay files are byte-identical to their raw local sources. Older
metric/RESULT rows omit only duplicated episode_replay payloads; each archive
entry retains source/archived hashes and a transformation description. Unity
runtime identity/licensing/network debug lines were redacted from two published build logs;
raw originals remain local. A scan found no remaining session/correlation/machine
identifier, editor-license argument, player-connection, debugger-agent or IPv4 address lines in the archived runtime logs.

The archive intentionally excludes weights, generated binaries, private research,
runtime caches and per-seed duplicate best replays. Source-control hygiene and
Markdown/Unity metadata checks pass. A scoped ignore exception tracks only the
selected investigation logs; ordinary logs remain ignored. Historical PDFs and
older archive content are preserved. Publication target is origin/mohammad;
main remains the playground. No learner or frozen-evaluation Python process
remained running at final inspection, and no recurring training was scheduled.

Recheck hashes without training or writes:

```powershell
.venv/Scripts/python.exe training/archive_session.py --destination docs/training/investigation-2026-10-28 --verify
.venv/Scripts/python.exe training/archive_documentation.py --destination docs/training/evidence-2026-10-28 --verify
```

Rendering and source/metric checks validate this report's internal consistency;
they do not establish commercial-game fidelity, robust learning or a 1,000-trip
policy. The report explicitly preserves the negative results and limitations.
