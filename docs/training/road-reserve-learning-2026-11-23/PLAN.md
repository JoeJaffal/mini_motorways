# Road reserve learning — 23 November 2026

User authorization: teach saving roads for later connections, run checks and
measure full-city scores. Continue the confirmed Maskable-PPO checkout. Preserve
all earlier files/checkpoints. No overnight run is planned.

Engineering plan: add an opt-in native exercise with an already working network,
limited stock, ordinary legal distractions and a later matching pair. Reward
only actual deliveries. Compare Wait-then-connect and waste-then-connect native
controls before training. Future spawn time/location never enter observations
or policy inputs. Add zero-initialized trainable Wait adjustments over visible
service/stock context while freezing the best calibrated road ranking and
protected opening. This deliberately isolates conservation from route choice.
A new parameter set requires fresh optimizer state, explicitly recorded.

Start from city-five-stage-cold-initial-01/candidate.zip (best measured city
candidate), not the weaker demand-trained candidate. Bounded first pilot:
8,192 decisions,16 workers, actor LR .03, critic .0003; midpoint/final saved.
If mechanics or credit assignment need correction, document adaptive trials.
No planner, teacher actions or imitation. Independent controls are evaluation
only. Curriculum identifiers and future events are not actor inputs.

Checks: native build/suites, ordinary-host parity, exercise feasibility and
reward ledger, zero-initialization distribution parity, opening/road preservation,
finite PPO updates. Development practice uses seeds131M; training130M. Final
practice132M; final city suite RNG940127,32 paired games against exact calibrated
parent (and original reference if useful). No final-suite training. Promotion
requires no fewer scoring cities and mean at least95% of parent; report paired
uncertainty and stock/service metrics, even if no candidate passes.

The final city reference evaluations (original and calibrated parent) begin in
parallel with training, at four workers to limit contention. Their seed/action
suite RNG940127 is fixed above. Do not use their results to tune the candidate;
select from development practice, then evaluate the saved candidate against the
same suite. Comparison may combine matching JSONL files rather than rerunning
unchanged references. All hosts/checkpoint hashes and seeds must match.

## Candidate frozen before independent tests — 24 November 2026

Pilot completed8,192 added decisions,454 episodes,223.7 seconds. Development:
parent/midpoint/final later-target success2/8,3/8,6/8; mean arrival stock
1.125/2.5/3.125. Longer routes remain8/8; delayed targets6/8→8/8; quiet stock
retained0→0.875. Select the final for independent testing without additional
training. Final hash391b1447c53735f6fbd5d0e242f89fe884fec6d7fafb6c62018ec44225f9ead7.
Only six Wait weights and critic changed; conditional roads and opening match.
Run all nine lessons16 times on fresh132M seeds with evaluator controls, and the
candidate on the fixed32-city RNG940127 suite. Reference results were not read
before this selection. No parameter or calibration changes after selection.

## Transfer diagnosis and feature correction — 24 November

The first city suite exposed a feature alias: `1-max(quiet,available)` was named
blocked but also includes unrecognized/longer connections. Two sampled city
replays spent169 and145 decisions in that context, often with>99% Wait despite
211/274 legal builds and no visible driveway blocker. This is a flaw in this
experiment's representation, not evidence that PPO cannot learn conservation.
Preserve the original feature class/checkpoint and all first-suite results.

Added CityVisibleReserveFeatures: the last two inputs are now nonzero only when
the inherited visible blocked-approach detector also agrees. No road is selected
by this detector. All learned weights remain identical; this is an engineering
feature correction with transferred PPO weights, not another training run.
Initial probabilities on all nine probe lessons and protected opening match the
uncorrected candidate; conditional roads remain unchanged. Optimizer moments
are copied but further training would need bounded validation under new inputs.

The first city suite is now diagnostic/selection evidence. Final repair city
confirmation is a separately fixed32-game suite RNG940128, paired against the
calibrated parent; no adaptation to that confirmation is planned. Re-evaluate
repaired policy on all16-case132M lessons; the first practice set is retained.
