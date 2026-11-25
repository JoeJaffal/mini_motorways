# Matched road-cost continuation results

Both learners completed the predeclared budget. These are development evaluations of one training seed per arm, not independent confirmation or proof of convergence. No automatic promotion or further training.

| Decisions | Arm | Stock | Success | Native score | Paid roads | Outside observed routes |
|---:|---|---|---:|---:|---:|---:|
| 65536 | control | tight | 54.7% | 1.953 | 7.000 | 3.938 |
| 65536 | control | generous | 70.3% | 2.422 | 10.328 | 5.906 |
| 65536 | strong | tight | 56.2% | 2.000 | 7.000 | 3.812 |
| 65536 | strong | generous | 70.3% | 2.453 | 10.312 | 5.938 |
| 131072 | control | tight | 54.7% | 1.953 | 7.047 | 3.984 |
| 131072 | control | generous | 67.2% | 2.344 | 10.359 | 6.250 |
| 131072 | strong | tight | 54.7% | 1.938 | 7.047 | 3.938 |
| 131072 | strong | generous | 76.6% | 2.594 | 10.359 | 5.562 |
| 262144 | control | tight | 54.7% | 1.953 | 7.062 | 4.000 |
| 262144 | control | generous | 71.9% | 2.484 | 10.375 | 6.031 |
| 262144 | strong | tight | 57.8% | 2.047 | 7.094 | 3.734 |
| 262144 | strong | generous | 85.9% | 2.875 | 10.438 | 4.828 |

Final .04 minus control, clustered paired 95% bootstrap intervals:

- small-city-offset-single: score: +0.0938 [-0.1406, +0.3281]; first_served: +0.0312 [-0.0312, +0.0938]; paid_units: +0.0312 [+0.0000, +0.0781]; outside_routes: -0.2656 [-0.7656, +0.1875]
- small-city-offset-stock: score: +0.3906 [+0.0312, +0.7656]; first_served: +0.1406 [+0.0312, +0.2500]; paid_units: +0.0625 [+0.0156, +0.1250]; outside_routes: -1.2031 [-2.1562, -0.3594]

A road outside a route observed within60seconds is not proven permanently useless. Raw games, recipe, checkpoints/hashes, seed cursors, gradient and parameter-update records are archived alongside. Weights and compiled host remain local-only under output/training/road-cost-continuation-01. The disposable smoke runs are excluded.

Full-city transfer, independent training-seed replication and untouched confirmation remain pending. The final and intermediate development scores must be reviewed before choosing the next experiment.
