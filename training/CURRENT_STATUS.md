# Current preparation - 31 October 2026

User chose4h training instead of more tests. Opt-in supported-upgrades integrated, checkpoint/eval/resume flag preserved; short checks only, no job launched. Resume protected checkpoint with240min/4workers; source checkpoint preserved and best guard retained. [Exact command/limits](../docs/training/supported-upgrade-training-2026-10-31/README.md), T45. Fresh8000-8009 test pending, not required before user-authorized experiment.

# Latest result - 31 October 2026

Supported-upgrade filter186.4->228.8 on5 development maps (4 wins/1 tie). Engineered improvement, concentrated on2000, not learning/generalization evidence. Prepared identical frozen comparison on8000-8009 (20 games); user runs, no job launched. Protected checkpoint/default training unchanged. [Evidence/command](../docs/training/upgrade-support-results-2026-10-31/README.md), T44.

# Latest preparation - 31 October 2026

Optional supported-upgrade rule comparison ready for user: frozen final policy,5 exposed development maps x2 conditions. Offer information already visible; filter only unsupported-extra packages with a supported alternative/no fewer roads. Training defaults unchanged. Synthetic checks and short smoke passed; full evaluation pending. [Command/protocol](../docs/training/upgrade-support-test-preparation-2026-10-31/README.md), T43.

# Latest result - 31 October 2026

Single first-upgrade intervention recovered final policy83->266 trips on2000, two lights placed autonomously, unchanged weights. This is a total causal effect on one exposed development map, not generalization or isolated light physics. Keep protected checkpoint; investigate upgrade representation/utility before long training. No new job launched. [Evidence](../docs/training/first-upgrade-results-2026-10-31/README.md), T42.

# Latest preparation - 31 October 2026

First-upgrade intervention CLI ready: frozen final baseline versus override only at140s on2000, then normal policy. Short wiring smoke passed; does not reach intervention. User runs full test; no training or full evaluation started. [Command/protocol](../docs/training/first-upgrade-test-preparation-2026-10-31/README.md), T41.

# Latest diagnosis - 31 October 2026

Seed2000 reproduced235 vs83. First divergence is upgrade at140s: protected gets2 lights, final another package. Final builds no lights and dies with crossing queues; later route/wait differences also exist. Causality unproven. Next recommendation: force only first upgrade in frozen final policy, then normal decisions. No job launched. [Evidence](../docs/training/regression-2000-2026-10-31/README.md), T40.

# Training status - 31 October 2026

Prepared user-run seed2000 frozen protected-versus-final diagnostic after continuation regression. Short two-second wiring check passed; full comparison pending, no training started. See T39 and [command/limits](../docs/training/regression-diagnostic-preparation-2026-10-31/README.md).

# Training status - 30 October 2026



Latest: signals-context-02 completed two hours/370 games. Development mean228.0 ->186.4; all periodic checks below starting baseline. Protected validation-best remains the starting228.0 policy. Best training480 is not evidence of improvement. Recommendation: pause long training and diagnose regression on development maps. No job launched. See T38 and [evidence](../docs/training/signal-context-continuation-2026-10-30/README.md).



Earlier status entries below are historical.



V4 light-availability test complete: ON177.5 vs OFF159.1 (+11.6%), three wins/

six ties/one loss on seeds7000-7009. Light actions help this policy's mean on

this set but can still hurt individual maps. Next recommendation is a user-run

two-hour continuation of the same checkpoint/settings, not another architecture

change. No job started. See T37 and

[paired evidence](../docs/training/signal-context-light-results-2026-10-30/README.md).



Next prepared diagnostic: v4 light placement ON/OFF on seeds7000-7009, same

selected228.0-development model, twenty frozen games. User execution pending;

no assistant-run simulation/training. Exact command in TRAFFIC_LIGHT_TEST.md.



V4 fresh-map test complete: deterministic175.9->194.0 (+10.3%), two maps better,

five tied, three worse. Sampled168.7->169.0, nine ties/one+3 gain. Thus additional

learning has an inconsistent point-average benefit, not established broad

improvement or a proven light-placement fix. Forty frozen games, seeds6000-6009;

no further jobs started. See

[full scores and limits](../docs/training/signal-context-fresh-2026-10-30/README.md), T35.



V4 one-hour user trial completed normally: 167 games, validation204.2 ->228.0

(+11.7%), with most gain on one of five maps. Best selected checkpoint is local

output/training/signals-context-01/validation-best.zip. No trainer active.

Next: user-run frozen comparison on new seeds6000-6009; no additional training

or full evaluation launched by the assistant. See SIGNAL_CONTEXT.md and T34.



V4 signal context is prepared: queue causes and current destination pressure,

with a v3->v4 weight-preserving warm start and fresh optimizer. Four short checks

and a tiny no-update CLI wiring smoke passed; no learning benefit is established.

Per user preference, no long job was started/waited on. Use the

[manual one-hour command](SIGNAL_CONTEXT.md), then report completion for analysis.



Seed5009 diagnosis complete: the lights interact. With the ON construction

schedule fixed, both lights score279, first-only374, second-only277, neither276.

The full OFF policy's different command schedule scores475. The second light

was placed by a parking-access queue; current light inputs lack queue-cause

information. This is a diagnostic/input-gap finding, not a trained fix or a

reason to ban all lights. No model/rules/reward changed. See

[evidence and limits](../docs/training/light-failure-5009-2026-10-29/README.md), T32.



Traffic-light ON/OFF test is now complete: ON190.9 vs OFF209.9 mean trips, with

2 wins/5 ties/3 losses. The -19 mean is dominated by seed5009 (-196 trips);

the other nine net+6 for ON. This is inconsistent placement benefit for the

frozen policy, not proof that lights universally harm simulator traffic. See

[paired evidence](../docs/training/light-availability-2026-10-29/README.md), T31.

No new training was started. The preparation note below is historical.



Next diagnostic prepared: [traffic-light ON/OFF comparison](TRAFFIC_LIGHT_TEST.md),

same frozen trained policy on ten paired seeds. Full comparison not started;

only a short startup smoke and mask/observation checks have passed. This is an

evaluation command, not authorization to start more training.



**Fresh-map test complete:** the preselected trained model improved deterministic

mean 161.3 -> 207.4 (+28.6%) on unseen LosAngeles seeds4000-4009, winning9/10.

Secondary sampled mean182.0 -> 188.9 (+3.8%); five wins/two ties/three losses,

with nearly all aggregate gain on one map. This supports deterministic transfer

but remains a ten-map/one-model test with weak sampled evidence. All40 games

were inference only; frozen selection/weights preserved, no retuning. See

[paired results and evidence](../docs/training/signals-fresh-2026-10-29/README.md)

and T27. No training is active; selected local weights remain

`output/training/signals-night-01/validation-best.zip`.



**Latest: user overnight run stopped early, cause unknown.** `signals-night-01`

has no active trainer, final checkpoint or summary; last unfinished status is

4h18m/8h,832 games. Saved best validation mean improved167.4->204.2 (+22%),

latest validation185.4, best completed training recording494 trips on seed1099.

The trained validation-best checkpoint beat its starting policy; the later

fresh-seed result is recorded above. Existing checkpoints are retained locally.

See [raw evidence](../docs/training/signals-overnight-2026-10-29/README.md) and T26.



The following preparation record predates the user-started overnight run.



Traffic-light **v3 is ready for a fresh overnight experiment**, not yet run.

It adds normal-stock legal junction proposals, existing-light observations and

traffic/global context for route choices. Starting-prior temperature 2 permits

more varied sampling; it is not a proven performance improvement. Two controlled

512-decision pilots both regressed slightly (122.67 -> 122.33 mean on three dev

maps), so both retained the starting model as validation best. Baseline/tie

protection now prevents a worse first validation from being selected. The full

overnight run is stopped/not launched. See [command and contract](SIGNALS.md),

[archived audit/pilots](../docs/training/signals-2026-10-29/README.md) and history T25.



Earlier v2 and investigation results below remain historical; old weights and

PDFs were not overwritten.



Latest user-started v2 trials: `congestion-v2-01` and `-02` each finished a

30-minute fresh run (neither resumed). Both recorded **432 trips** on seed 1099.

Development mean started at 167.0 and ended at 142.4/142.2 respectively; best

periodic validation was 167.4 for both. This is no reliable learning gain and

final policies regressed. Both are stopped. See history T24 and the

[two-run assessment](../docs/training/congestion-v2-2026-10-28/two-user-runs.json).

The older investigation results below remain historical.



The authorized investigation is complete. All training and frozen evaluation

have stopped; no recurring run is scheduled. Work is on `mohammad`; `main` remains

the playground. Existing checkpoints and historical PDFs are preserved.



Post-investigation correction: planner-aided candidate traffic and waiting now

refresh at every decision rather than only when route geometry is rebuilt.

Five goal-agent checks pass, including a new fixed-topology traffic regression.

No new performance evaluation or training was started; the scores below and PDF

describe the historical implementation. See history T21 for scope and limits.



The optional congestion v2 model is now ready for a controlled fresh-model trial:

live traffic grid, junction/route load summaries and physical bypass proposals.

Eight goal checks pass, including actual bypass replay and v2 actor/CNN updates

and save/reload. Four-worker startup and frozen evaluator checks passed. A tiny

startup smoke stopped before an optimizer update; it is not performance evidence.

The three-map frozen comparison is mixed (120.3 -> 123.3 mean, two maps worse),

so no reliable gameplay gain is claimed. No long training was started. See

[training command and limits](GOAL_AGENT.md) and history T22. Existing reports

and the 356-trip recording remain historical v1 results.



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

