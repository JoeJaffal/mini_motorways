# Overnight task-mix comparison —25November2026

Both arms resumed the same262144-decision cost.04 policy and added262144decisions. One branch continued practice only; the other used eight native city workers and eight practice workers. Practice reward retained cost.04; city reward was native deliveries only. Optimizer settings and policy architecture remained fixed. No planner or imitation was added.

## Native city results

These are sampled600-second games with bridges enabled on16previously used development cities, two action RNGs each. They measure transfer from practice; the mixed branch trained on different city seeds, not these evaluation episodes.

| Model | Mean deliveries | Cities scoring /32 | Paid roads | Roads outside observed routes |
|---|---:|---:|---:|---:|
| original | 126.09 | 30 | 99.12 | 32.28 |
| parent | 86.97 | 27 | 86.22 | 33.38 |
| lesson-only | 107.44 | 30 | 96.25 | 40.81 |
| mixed-city | 99.16 | 30 | 91.25 | 33.25 |

Paired score differences, clustered by city with both action RNGs retained:

- lesson-only minus parent: +20.47,95%bootstrap interval[-11.56,+51.63].
- mixed-city minus parent: +12.19,95%bootstrap interval[-25.94,+49.47].
- mixed-city minus lesson-only: -8.28,95%bootstrap interval[-44.09,+31.44].
- mixed-city minus original: -26.94,95%bootstrap interval[-57.41,+6.03].
- lesson-only minus original: -18.66,95%bootstrap interval[-40.34,+1.75].

## Practice curves

| Model/budget | Stock | Success | Native deliveries | Paid roads |
|---|---|---:|---:|---:|
| lesson-only-393216 | tight | 64.1% | 2.219 | 7.250 |
| lesson-only-393216 | generous | 87.5% | 2.922 | 10.719 |
| lesson-only-524288 | tight | 60.9% | 2.156 | 7.422 |
| lesson-only-524288 | generous | 84.4% | 2.797 | 11.969 |
| mixed-city-393216 | tight | 59.4% | 2.047 | 7.234 |
| mixed-city-393216 | generous | 73.4% | 2.453 | 10.797 |
| mixed-city-524288 | tight | 57.8% | 2.031 | 7.328 |
| mixed-city-524288 | generous | 71.9% | 2.438 | 11.438 |

## Interpretation and remaining work

Positive mean changes are not automatically reliable gains; assess the paired intervals, scoring reliability and road spending together. A lower practice cost is not a full-city score improvement. Poor critic prediction can be measured without establishing that it is the sole cause of policy failure. These finite budgets do not establish convergence.

No winner is automatically promoted. Independent training-seed replication, unseen-city confirmation and broader tools/weekly-choice competence remain untested here. All checkpoints and the original policy remain preserved. No further run is launched by this controller.

Raw games, source snapshots, recipe, gradients, parameter updates and checkpoint hashes are archived. Weights and simulator binaries remain local-only under output/training/overnight-transfer-comparison-01.
