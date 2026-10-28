# Training status - completed 28 October 2026

The authorized investigation is complete. All training and frozen evaluation
have stopped; no recurring run is scheduled. Work is on `mohammad`; `main` remains
the playground. Existing checkpoints and historical PDFs are preserved.

**Best recordings:** 126 trips for the primitive all-tools policy; **356 trips**
for the new planner-aided goal agent (seed 1075, 971.65 simulated seconds,
972 ordinary commands, normal failure). Both checked exactly in the native game;
the 356-trip recording also passed headless verification. The 1,000-trip target
has not been reached.

**Learning evidence is limited.** Most improvement comes from engineered action
priors and route planning. The trained goal candidate improved one of ten fresh
deterministic maps; sampled evaluation tied its starting policy. A high training
best does not establish reliable learning or make that final checkpoint the best.

See the [new 10-page report](../docs/training/model-investigation-2026-10-28.pdf),
[full protocol and findings](EXPERIMENT_2026_10_28.md),
[chronological history](EXPERIMENT_HISTORY.md) and
[archived evidence](../docs/training/investigation-2026-10-28/README.md).

## Fresh-map comparison

Selection was frozen using development seeds 2000-2004 before opening final
seeds 3000-3009. Each policy used normal finite OriginalReference materials and
failure rules, a 3,600-second external cap, and no optimizer updates.

| Frozen policy | Deterministic mean trips | Best |
| --- | --- | --- |
| Earlier stopped primitive policy | 0.6 | 4 |
| Informed primitive starting policy | 23.4 | 93 |
| Development-selected trained primitive | 20.7 | 92 |
| Goal policy: frozen informed initial | 119.1 | 270 |
| Goal policy: selected trained candidate | 125.7 | 270 |

The goal-policy gain is entirely seed 3006, from 56 to 122 trips; nine maps tied.
Secondary sampled inference averaged **130.4 for both** policies, using one
trajectory per map and Torch seed 43 plus scenario offset, reset per game.
Ten maps and one training replicate do not establish robust generalization.
No test result triggered further training or checkpoint selection.

## What changed

The original 450,610-parameter, 50-channel all-tools model remains available.
Opt-in connectivity inputs add two channels (450,898 parameters). Explicit
adaptation preserves starting action probabilities by zero-filling new weights.
Spatial residual scoring, informed endpoint priors, conservative productive-draw
masks, no-op diagnostics and longer PPO credit windows were tested separately.
Primitive pilots did not establish a strong learning improvement.

The **separate goal agent has 10,334 parameters**. It selects among visible
matching-color connection proposals; a deterministic router executes ordinary
road/bridge strokes. It also waits and chooses upgrades. It excludes motorways,
roundabouts, traffic lights, demolition and manual driveway edits. Its starting
prior is engineered, not learned. [Full inputs, restrictions and commands](GOAL_AGENT.md).

Primitive reward remains trip delta plus bounded potential shaping, gamma .999.
Goal reward uses the same bounded connection idea but gamma .99 per macro decision.
Numerical reward scale .01 changes optimization, never game score. Choice-only
mode folds forced waits into the preceding decision; it has separate timing/reward
metadata. A frozen test verified identical ordinary command histories with/without
collapsing forced waits at a 180-second cap. The saved timing mode restores at
inference. Resume inherits timing, rate and reward scale unless explicitly changed.

## Goal-agent pilots

All four started from identical policy weights and empty optimizer states, with
five-map development mean 162.6. Each had a 25-minute learner cap and two workers.
Initial/final evaluation adds time; periodic validation consumes learner time.

| Arm | Macro decisions | Games | Best training | Final dev mean |
| --- | --- | --- | --- | --- |
| Scale 1 | 9,450 | 72 | 304 | 162.6 |
| Scale .01 | 8,508 | 63 | 300 | 162.6 |
| Choice only | 2,586 | 70 | 296 | 162.6 |
| Choice + rate .001 | 3,556 | 91 | 356 | 128.0 |

The higher-rate final checkpoint regressed despite recording 356 trips in one
training game. Operational selection conservatively kept the frozen initial
policy on a development tie. The trained comparison is the first goal run's
validation-best checkpoint, not the 356-trip run's final model.

Local operational baseline: `output/training/goal-hybrid-20261028/initial.zip`.
Local trained comparison: `output/training/goal-hybrid-20261028/validation-best.zip`.
Local primitive candidate: `output/training/informed-credit-20261028/validation-best.zip`.
Weights and generated binaries remain local; code, evidence and PDF are in Git.

## Watch the 356-trip recording

```powershell
cd C:\Users\moham\mini_motorways
.\.venv\Scripts\python.exe .\training\watch_best.py --run output/training/goal-rate-20261028
```

Add `--play` to begin paused at the start. The native viewer labels planner-aided
replays. This exact action history can span policy updates and sampled actions;
a checkpoint saved at episode end is only a snapshot, not a guarantee of replaying
the same score. For a future bounded experiment, use [the goal guide](GOAL_AGENT.md)
or [the primitive quickstart](QUICKSTART.md), with a fresh output folder.

## Verification and remaining limits

Checks passed: 42 shared simulator suites; ten five-map protocol runs; 31 Python
checks across environment, rewards, workflow, parallel, shutdown, feature/migration,
draw-mask and goal-adapter suites. Four-worker resume restored .01 scale and
choice-only timing without a weight update. Repeated sampled inference produced
identical metric/action records. Frozen evaluations verified unchanged weights.
The OriginalReference native player rebuilt successfully; generated scene/settings
noise was restored. Reports record command corrections and evidence compaction.

The primitive draw-noop metric means unchanged infrastructure/connection arrays;
it is not proof of no driveway-only or pending-removal change. The goal router
avoids parcels/demolition but redraws reused paths: 438/668 initial-development
draws made no network change. Removing those strokes and offering capacity-aware
route alternatives are future executor experiments, not implemented gains.
Game duration, routing and serialization explain throughput; there is no artificial
0.8-games/second cap. More games or a higher training mean alone is not success.

OriginalReference remains a reconstruction. These results do not demonstrate
commercial-game fidelity, other-city transfer or a reliable 1,000-trip policy.
The earlier 12-page report is a historical pre-investigation snapshot.
