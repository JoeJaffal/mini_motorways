# Maskable PPO decision workbook — 16 November 2026

User requested an Excel record of decisions, completion, review, explanations and reasons. [Workbook](Maskable_PPO_Decisions.xlsx) contains 43 records: 18 decisions done, 6 partial and 19 open. Review coverage: 18 reviewed, 20 partly reviewed and 5 not reviewed. These counts describe design discussion, not implemented or tested trainer features.

## Contents and meaning

- **Tracker:** filterable records with independent decision status, user review, implementation, next step and last discussion date. Status dropdowns, conditional formatting, frozen headers/IDs and formula-driven counts support updates to existing records.
- **Decision details:** matching stable IDs with explanation, reason, reason classification, open details and repository-relative source. User reasons are distinguished from reviewed engineering reasons and unadopted proposals. Missing user rationale is explicit.

Sources are the conversation, [current decision ledger](../maskable-ppo-restart-decisions-2026-11-15.md) and [hardware inventory](../maskable-ppo-hardware-2026-11-15.json). Historical proposals are not promoted to approval. New trainer implementation and training remain unstarted. Observations, timing, neighboring roads and incremental bridges are approved in scope; detailed representation/configuration remains open. Generated construction routes remain strictly prohibited. This export adopts no new design decision.

## Durable sources and reproduction

[decisions.json](decisions.json) preserves all record text/statuses, and [build.mjs](build.mjs) preserves the exact authoring source. The archived workbook is byte-identical to the delivered file at `outputs/maskable-ppo-decisions-2026-11-16/Maskable_PPO_Decisions.xlsx`. Keep this dated snapshot historical. Use a new archive directory for later revisions and reconcile workbook edits into the ledger rather than discarding them on regeneration.

Rebuild with the dependency-loader-provided Node executable and `@oai/artifact-tool` package, using a writable scratch directory with a `node_modules` junction pointing to the bundled dependencies. Copy this single builder there, set `DECISION_REPO` to the repository root if needed, then run the scratch `build.mjs`. The existing local scratch location is `tmp/decision-workbook-2026-11-16/`; its junction is local-only. Do not install or modify repository dependencies. For a future separate authoring task, follow the spreadsheet skill's operation-marker instructions before rebuilding. Rebuilding this script overwrites this snapshot, so make a new dated archive/output configuration for new content.

## Verification and limitations

[QA.json](QA.json) records checks. Formula counts matched independent record counts; a temporary status change updated the summary and was restored. No formula errors matched the scan. Both sheets were rendered and visually reviewed at the opening and ending ranges; a clipped summary label was corrected. XLSX ZIP integrity, two tables, three validation ranges, two conditional-format ranges, freeze panes and eight formulas were verified in the exported file. Output/archive bytes match. Preview PNGs and tool-generated inspection output remain local-only under outputs, not the sole evidence.

The Node command returned exit code 1 after successfully writing the complete QA record and export, with no explanatory error text. Export existence, ZIP integrity, expected features and byte identity were independently checked rather than assuming process exit success. Native Microsoft Excel application recalculation/UI was not tested. Adding records beyond the current table requires extending summary/validation/format ranges or regenerating from updated records; no automatic row-extension guarantee is made.

No simulator/trainer source edits, runtime game tests, benchmark, training, branch switch, commit, push, weights or generated players. Current checkout remains dirty codex/driveway-physics; records must be carried into the intended Maskable-PPO workspace before implementation. Manifest hashes cover the archival files; previews are intentionally excluded.
