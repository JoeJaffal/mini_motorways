# Documentation requirement

The user requires a durable record of every material update, decision, analysis
and performance finding, including findings and graphs delivered in PDFs.
Maintain this as part of the work, not only when reminded.

- Record training work chronologically in `training/EXPERIMENT_HISTORY.md`.
  Simulator/user design decisions belong in
  `simulation/Docs/DESIGN_DECISIONS.md`; cross-link older history.
- Distinguish user decisions, engineering choices, measured results, hypotheses
  and open questions. Include reason, revision/run, checks, outcome, limits and
  superseding changes. Never invent missing facts or rationale.
- Keep current status, commands and indexes up to date.
- Preserve report text, graphs and small measurement sources under
  `docs/training/`, following its archive procedure. Historical reports stay
  historical. Do not leave the only record in ignored output or chat.
- Do not commit weights, generated binaries, private game research or secrets.
  Identify local-only artifacts and missing evidence explicitly.
- Training work stays on `mohammad`; `main` remains the playground. Changing
  documentation/code does not itself authorize another long training run.
