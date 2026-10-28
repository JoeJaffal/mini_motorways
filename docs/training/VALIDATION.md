# Documentation archive validation — 28 October 2026

This audit changed documentation, archived evidence and documentation tooling;
it did not train, evaluate or modify a model policy.

- All 16 pages were text-extracted from the original model PDF. The archived
  PDF matches the original local file byte-for-byte. Its eight standalone graph
  images and complete page text were preserved; the coverage index lists every
  page, including all analyses, proposals and caveats.
- The run archive contains 56 files from seven run folders and the parallel
  benchmark. SHA-256 verification passed for all 56 copies.
- The supplementary manifest verifies 16 report, figure, replay and source
  assets. All hashes passed. It includes before/after retiring-pavement captures.
- Git text normalization is disabled inside this archive so manifest hashes
  remain valid across operating systems. Staged Git blob bytes were checked
  against both manifests, not just the working copies.
- The new performance plot was rebuilt from archived worker monitor CSV and
  visually inspected. It contains 4,549 completed games. Hourly means reproduced
  as 31.9701, 45.9161, 52.6413 and 52.6361. It is a single-seed, resumed-run plot.
- Python syntax checks passed for the archive utility and both plotting/report
  scripts. The adapted historical PDF rebuild script was not executed in this
  audit; a rebuild would need fresh visual review before delivery.
- The 40 shared simulator suites and ten five-map version/protocol checks passed.
- Repository checks passed for 234 selected files and 27 Markdown documents
  before this validation note was added; the final check includes this note.
  No broken local links, selected caches/private binaries, or missing/duplicate
  Unity source metadata were found. Whitespace checks passed with Git line-ending
  normalization notices only.

The archive preserves available evidence, not every unsaved past experiment.
The crashed run has no final summary; checkpoints themselves and the original
user video remain local. Historical findings with only narrative/scratch evidence
are labeled as such in the chronological history. The unchanged PDF is a
historical first-run report, not an updated four-hour results report.
