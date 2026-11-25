# Opening retention repair — 23 November 2026

## Decision and scope

The user authorized diagnosis and bounded repairs after the guarded continuation
stopped. The observed failure was that further PPO updates lost scoring openings.
The goal remains stronger full-city play. This experiment tests retention; it is
not evidence of leaderboard readiness.

Work used the existing `/home/mohammadjaffal/mini_motorways` checkout,
`Maskable-PPO`, base revision `6bd7f7193b26ae0f5aa12563f3dd89769115df6e` plus
preserved local changes. Desktop `main` was untouched. The latest supplied
Desktop instructions name `mohammad`, whereas this checkout's AGENTS.md names
`Maskable-PPO`; no branch switch was performed. Resolve that discrepancy before
another training session. No long run was launched here.

## Measured diagnosis

`replay.py` reproduced the three newly scoreless cases from segment two with the
original scenario and sampled-action seeds. All first action divergences were
before a first delivery. Early road stock exhaustion accompanied the failures.
The traces establish the regression and its timing; a first divergence alone is
not a causal explanation for all subsequent decisions.

| City seed | Retained | Regressed midpoint | Regressed final | Repair pilot final |
|---|---:|---:|---:|---:|
| 99161630 | 14 | 0 | 59 | 14 |
| 99312933 | 4 | 0 | 0 | 4 |
| 99324387 | 158 | 169 | 0 | 156 |

Scores are native deliveries in sampled frozen replays. These are deliberately
selected regression cases, not independent validation.

## Engineering change

`training/city_established_policy.py` adds a separately loadable feature class.
A frozen copy of the retained feature extractor determines actions until the
visible road graph contains an attached matching-color home/destination pair in
a city with more than two parcels. The existing graph feature supplies this gate.
Once established, PPO can update the spatial growth actor and service weights.
The graph gate is recomputed each decision and can return to the reference if
service connectivity disappears. It does not inspect delivery rewards or hidden
routes. No new route planner, imitation targets, reward or native simulator
changes were introduced in this repair. Earlier engineered policy preferences
remain inherited and must not be represented as learned from scratch.

**Tradeoff:** the reference's bad openings are frozen too. The gate can become
active before the first actual delivery. It protects weights and action
probabilities in the gated states, not all eventual city outcomes. Improving
openings needs a separately tested reference update. Both feature branches are
computed, so there is additional inference cost; a dedicated throughput
comparison has not been run.

## Bounded pilot and checks

`prepare.py` copies the retained 413,696-decision checkpoint, preserves all 22
Adam state entries exactly, and creates a new local checkpoint. The original
checkpoint's hash is unchanged. `city-established-pilot-01` ran 12,288 additional
decisions, 19 completed episodes, and 101.71 active seconds with 16 workers and
learning rate 0.000001. Native delivery reward remained unchanged.

`check_repair.py` verified exact opening probabilities on 175 encountered states
across the three replays. The frozen reference weights stayed exact. Both pilot
saves changed spatial grid and road weights and preserved all protected weights
(`weight-audit.json`). Four focused Python tests passed, including a mixed batch
where arbitrary growth updates change the established actor but leave opening
output identical and the reference receives no gradients.

The final local candidate is
`output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip`,
SHA-256 `637dcd6f1e05ac61869e7b7ecb9e0a31fb41e8305ae5c89b091218a8a3fd651a`.
Weights and the native DLL stay local-only. Measurement/source hashes are in the
archive manifest. The retained parent is preserved for rollback.

## Broader review and next gate

All four conditions were evaluated on the same 16 scenario/action seed pairs:

| Condition | Mean deliveries | Cities scoring | New targets served | Mean paid units outside observed routes |
|---|---:|---:|---:|---:|
| Older repaired baseline | 99.00 | 15/16 | 57 | 37.06 |
| Exact pilot start | 90.19 | 15/16 | 53 | 40.06 |
| Midpoint | 92.81 | 15/16 | 56 | 37.38 |
| Final | 96.56 | 15/16 | 59 | 36.69 |

The final paired mean gain against its exact start is 6.375 deliveries, with a
95% paired bootstrap interval of -7.81 to +27.69 (12,000 resamples). One city
improved by 147 deliveries, another lost 45. Thus improvement is uncertain and
uneven. The older repaired baseline still averages higher on this suite. Road
units outside observed trip routes are a diagnostic, not a proof of wasted roads.
New-target totals differ with survival; served counts alone do not measure a
fixed-task success rate.

The generator seed reused 563902, but changing suite size produced 16 scenario
seeds with zero overlap with the failed segment's 24. This is a development
comparison with a known generator, not a newly locked independent final test.
The frozen start is behaviorally identical to the retained reference by exact
weight transfer; both branches begin as that same feature extractor.

Retain the final as an experimental repair candidate and preserve both older
references. The targeted opening retention gate passes. High-score capability
and stability over hours remain unproven. Proposed next work: resolve the
checkout/branch instruction discrepancy, then a bounded stability continuation
and a predeclared larger paired suite (including the older repaired reference),
with the three failure replays as mandatory retention checks. Promote only with
retention and repeatable score/service gains. Do not restart the old eight-hour
command unchanged. No trainer or evaluation remains active after this report.
