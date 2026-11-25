# Maskable PPO restart — read first

The user requires this restart to use `Maskable-PPO` as its source branch.
This supersedes the earlier `mohammad` preference for this experiment; `main`
remains the playground. Preserve existing work when reconciling branches.

Before continuing in a new local or cloud chat, read:

1. `training/CLOUD_START_HERE.md` for portable context and strict user rules.
2. `docs/training/DECISIONS.md` for current decisions and precedence.
3. `training/HANDOFF.md` and `training/PLAN.md` for the last recorded stopping point.

Consult the linked detailed records rather than redesigning already settled
choices. Older specifications/spreadsheets are historical snapshots: their
flat-policy/no-curriculum or old hardware assumptions do not override later
explicit approvals. Compare actual code and any new chat work with the recorded
state; do not assume documentation proves implementation or measured results.

A cloud sandbox is not the user's Linux training computer. Do not treat its CPU,
GPU, storage or installed packages as measurements of the Alienware. Windows
paths in the handoff identify the original local checkout; use repository-relative
paths in cloud. Do not attempt to access the local computer through those paths.

Current publication (26 November): read `training/CURRENT_STATUS.md` and the
linked 25 November session review before using the historical cloud design.
Later approved local implementation and measured results supersede stale setup
and hierarchy assumptions. Checkpoints and native binaries are local-only.

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
- Restart work is based on `Maskable-PPO`. Changing documentation/code does not
  itself authorize another long training run.
