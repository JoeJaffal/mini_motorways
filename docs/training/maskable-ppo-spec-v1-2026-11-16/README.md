# Completed v1 decisions — 16 November 2026

The user delegated remaining decisions while sleeping, explicitly requiring that new choices not be marked reviewed. [Updated workbook](Maskable_PPO_Decisions_v1.xlsx): **51 selected design records, 0 undecided, 18 earlier user-reviewed choices, 33 new choices Not reviewed**. No new trainer implementation, simulator episodes or training run. The earlier [43-record workbook](../decision-tracker-2026-11-16/README.md) remains an unchanged historical snapshot.

## Review entry points

- Filter **User review = Not reviewed** in Tracker to see the agent selections. Done means a design was selected, not implemented, optimal, tested in-game or approved by the user.
- Read [SPECIFICATION.md](SPECIFICATION.md) for complete controls, timing, schema, architecture, numeric PPO settings, source evidence, seed split, evaluation, budgets and failure handling. Each choice has a reason, evidence or an explicitly identified engineering judgment. Literature does not certify numerical optimality.
- [CONFIG.json](CONFIG.json) contains exact initial settings and `training_authorized: false`. [split_manifest.json](split_manifest.json) lists all city/seed pairs. [decisions.json](decisions.json) contains the workbook's complete records/rationale/provenance.

Key selections: center-based native roundabouts; native motorway endpoints/edit/removal; fine connection erasure plus tile/object deletion; two weekly offer choices; Discrete1501 staged tokens; grid81×30×50/global54/visible motorway pairs; four traffic history frames; CNN/pair/global encoder with900,702parameters; score deltas and gamma1 over the finite3600s benchmark;2hosts/2048-token rollout/batch128/4epochs;CPU initial device on both machines; four training cities,London held out;128training/16validation/50test seeds per training city;3learner seeds; fixed human/replay/evaluation protocols; bounded planned pilot and stopping gates. No curriculum, planner/generated route, hidden future input, reward shaping, live distributed learner or automatic longer run.

Observed integration work required before launch: ordinary headless dispatch and replay lack adjacent road erasure, exact pure physical masks need implementing, wait must poll per tick for weekly choice, and the new schema/encoder requires implementation. These are implementation tasks, not undisclosed undecided defaults. Desktop identity, actual throughput, human scores and useful-play learning remain missing empirical evidence. Higher score is not claimed.

## Verification actually performed

[SPEC_CHECKS.json](SPEC_CHECKS.json): disjoint split arithmetic;51records complete;33agent choices remain Not reviewed; prior reviewed choices/reasons/statuses preserved; channel counts; minibatch/rollout/pilot divisibility;20×.05s wait; random synthetic network forward shapes, empty motorway-pool masking, finite outputs and one-valid-action normalization. Parameter count900,702. No optimizer step, no saved weights, no rollout or simulator benchmark. Estimated rollout array memory is arithmetic (grid995,328,000bytes, pairs73,728,000bytes), not measured peak.

[WORKBOOK_QA.json](WORKBOOK_QA.json) and [EXPORT_CHECKS.json](EXPORT_CHECKS.json): imported and preserved existing two-sheet layout/native tables; added8records; updated only affected data/counts/controls; verified cached counts51/0/18/33; temporary review edit changed formulas then was restored; no formula-error matches; native table bounds, IDs, earlier reviewed choices/reasons/flags and freeze panes checked against original exported XLSX. Source-approved rows have current execution next steps without assigning review to newly selected details. Rendered both sheets (opening,controls and ending ranges) and reviewed them visually. Output and archive are byte-identical. Native Microsoft Excel UI/recalculation is not tested.

The Node artifact runtime returns1 after writing complete export/QA output without explanatory error text, as in the prior workbook task. Independent ZIP/XML/file assertions validate the actual result. An initial text-edit attempt failed on the Windows default codec before writing; rerun with UTF-8 succeeded. Final synthetic/spec/export checks pass. These tool issues did not run training or modify gameplay.

## Reproduction and archive policy

From repository root, run the local pinned Python (or the loader-provided equivalent):

```powershell
.venv/Scripts/python.exe docs/training/maskable-ppo-spec-v1-2026-11-16/select_decisions.py
.venv/Scripts/python.exe docs/training/maskable-ppo-spec-v1-2026-11-16/check_spec.py
```

Workbook authoring source: [update_workbook.mjs](update_workbook.mjs), using the bundled `@oai/artifact-tool`. In a fresh authoring task, first use the spreadsheet skill operation marker (`edit`,1output,xlsx), prepare a writable scratch directory with node_modules junction to the dependency-loader package root, copy this single builder there, and execute with the loader Node executable. Existing local scratch: tmp/decision-workbook-2026-11-16. Verify:

```powershell
.venv/Scripts/python.exe docs/training/maskable-ppo-spec-v1-2026-11-16/verify_export.py
```

Outputs: outputs/maskable-ppo-spec-v1-2026-11-16/Maskable_PPO_Decisions_v1.xlsx and byte-identical archive here. PNG previews/tool inspection files and the scratch dependency junction remain local-only. New content revisions must use a new archive destination rather than regenerating over historical evidence. Preserve any manual workbook edits by reconciling them into the decision source first. Manifest covers this record, sources, configuration, checks and workbook. No weights, players/binaries, private original-game source or secrets included. Current dirty driveway checkout and pre-existing gameplay edits remain; no branch switch, commit, push or deployment.
