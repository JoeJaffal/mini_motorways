# Five-stage city learning — 23 November 2026

All five experiment stages and eleven bounded PPO runs are complete. **The
capability gates are not all passed. No overnight training was launched.**
Work stayed in the user-confirmed `/home/mohammadjaffal/mini_motorways` checkout
on `Maskable-PPO`. Existing checkpoints and uncommitted work were preserved.

The original protected checkpoint remains the conservative reference. Keep the
calibrated initialization and PPO-trained candidate as separately measured
experimental variants. Do not substitute either into old long-run commands.

## City retention

Sampled native Los Angeles games, maximum 600 simulation seconds. Original,
calibrated zero-initialization and identically calibrated trained candidate use
the same scenario/action seeds within each suite. Development was used to make
choices; independent results were not used for further updates.

| Suite | Original mean / scoring games | Calibration only | Calibration + PPO |
|---|---:|---:|---:|
| development | 85.03 / 31/32 | 97.56 / 31/32 | 93.53 / 30/32 |
| independent | 63.53 / 26/32 | 82.12 / 26/32 | 67.44 / 26/32 |

Paired mean-score changes and 95% bootstrap intervals:

- development, calibrated vs original: +12.53 [-6.97, +31.28].
- development, trained vs original: +8.50 [-12.06, +28.59].
- development, trained vs calibrated: -4.03 [-23.00, +15.38].
- independent, calibrated vs original: +18.59 [+3.12, +35.06].
- independent, trained vs original: +3.91 [-15.94, +23.59].
- independent, trained vs calibrated: -14.69 [-35.12, +4.00].

Cross-suite shared city seeds: []. See [paired data](final-comparison.json).

The trained candidate lost one scoring development city (30/32 versus31/32).
That fails the strict retention gate even though its development mean exceeds
the original. Do not erase this failure by pooling suites. City means are noisy;
controlled practice gains are not evidence that all city regressions are fixed.

## Independent practice

Sixteen fresh cases per lesson; demand combines both location/color variants.
Native evaluator controls confirm feasible choices without supplying training
actions. Numbers below are measured outcomes, not guarantees on unseen cities.

| Measure | Original | Calibration only | Calibration + PPO |
|---|---:|---:|---:|
| One-edge target served /16 | 16 | 16 | 16 |
| Longer-route target served /16 | 5 | 16 | 16 |
| Delayed target served /16 | 10 | 15 | 15 |
| Urgent target served /32 | 16 | 17 | 32 |
| Quiet-board road units left | 0.00 | 0.00 | 0.00 |
| Light-traffic mean score | 11.75 | 11.75 | 13.38 |
| Heavy-traffic mean score | 31.00 | 31.00 | 31.00 |

Construction gains already exist before new PPO: attribute those to calibration.
PPO adds a clear demand-priority gain against that same calibrated initialization.
Light traffic improves but still falls below the fixed feeder control (14.875);
heavy traffic remains similar. Quiet Wait keeps two roads and averages6.4375,
while the trained candidate spends them and also averages6.4375. That exercise
does not reward conservation over its short horizon. Waiting is not solved.

## Every bounded training run

All names below have the prefix `city-five-stage-` under `output/training/`.
Budgets count added decisions. Forced-Wait compression changes the meaning of a
decision; these counts are not comparable measures of simulated time.

| Run | Decisions | Completed episodes | Seconds | Actor LR | Forced Wait compressed |
|---|---:|---:|---:|---:|---|
| stability-01 | 22,528 | 41 | 190.0 | 1e-06 | False |
| connections-01 | 32,768 | 508 | 319.9 | 1e-05 | False |
| waiting-01 | 32,768 | 512 | 294.8 | 1e-05 | False |
| connections-02 | 32,768 | 508 | 314.4 | 0.0003 | False |
| waiting-02 | 16,384 | 256 | 132.5 | 0.0003 | False |
| connections-03 | 4,096 | 359 | 136.5 | 0.0003 | True |
| waiting-03 | 4,096 | 164 | 84.4 | 0.0003 | True |
| traffic-01 | 8,192 | 2,014 | 656.7 | 0.0003 | True |
| mixed-01 | 8,192 | 119 | 149.6 | 1e-05 | True |
| relations-01 | 4,096 | 1,770 | 357.3 | 0.03 | True |
| relations-mixed-01 | 4,096 | 57 | 80.5 | 0.003 | True |

Total added decisions across all branches: 169,984. Relation runs use critic LR equal to 1% of actor LR. Parent paths/hashes are in [run register](run-register.json) and archived configs.

- Stability-01: start/mid/final city means81.59/80.28/75.22 with27/32
  scoring each. Midpoint passes the predeclared retention check; final fails.
- Connections-01: one-edge6/8 and longer2/8, unchanged. Waiting-01:
  delayed3/8 unchanged and quiet spends both units.
- Connections-02: one-edge7/8, longer2/8. Waiting-02: delayed5/8.
- Connections-03: one-edge8/8 but longer falls to1/8. Waiting-03:
  delayed5/8 and quiet builds1.375 on average; no robust conservation result.
- Traffic-01 and mixed-01: broad exploration means18.56 and16.22 on the
  development city suite, versus85.03 original. Rejected. Their fresh practice
  also regressed. Previous checkpoints remain intact.
- Relations-01: narrower native-score learning improves development demand
  from8/16 at zero initialization to12/16 in warm sampling. Mixed continuation
  completes with only relation coefficients and critic changing; old actor
  and opening reference remain frozen.
- Warm relation city means29.34 at initialization,30.03 after traffic and33.00
  after mixed: insufficient. Subsequent *inference* calibration restores route
  selection; compare zero-init and learned versions separately in tables above.
- Retaining the old generic prior while scaling learned corrections is another
  calibration-only variant: development89.50,30/32 scoring, not preferred.

## Five-stage verdict and next work

1. **Stability:** tested, but final checkpoints still regress. Keep retention
   checks and original rollback; more training is not automatically improvement.
2. **Useful connections:** substantial controlled improvement, largely from
   inference calibration. Both calibrated variants pass all16 longer routes.
3. **Waiting:** delayed service improves to15/16; quiet-stock conservation fails.
   Next proposed lesson must make saved stock matter to later native deliveries.
4. **Demand/congestion:** PPO learns the tested demand preference (32/32 fresh).
   Light-traffic adaptation is partial; arbitrary congestion management remains.
5. **Mixed city:** bounded training and independent evaluation completed, but
   robust city-score retention/high-score readiness is not established.

The next work should address the future consequence of unnecessary construction,
then test transfer on city seeds held out from this report. Keep generic service
and demand candidates separate until city retention passes. No new reward
penalty, planner, long training or automatic promotion is authorized by this
report itself.

## Records and local checkpoints

- [Detailed changes, attribution, limitations and checks](REPORT_NOTES.md)
- [Original plan and chronological adaptive decisions](PLAN.md)
- [All small run/evaluation evidence](measurements/output/training/)
- [Checkpoint/binary hashes and local paths](local-artifacts.json)
- [Source context](source-context.json) and [archive checksums](manifest.json)
- [Final seven Python checks](python-final-checks.txt), [99 native suites](native-checks.txt),
  [1,116 legality checks](legality-checks.txt), [364-transition parity](host-parity.json)

Reference (local only):
`output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip`.
Calibration-only candidate: `output/training/city-five-stage-cold-initial-01/candidate.zip`.
Learned demand candidate: `output/training/city-five-stage-cold-final-01/candidate.zip`.
These files are preserved; weights/binaries are deliberately excluded from the
archive. Tests are bounded native simulation, not commercial-game leaderboard
proof. This report supersedes the active-work paragraphs; older reports remain
historical.
