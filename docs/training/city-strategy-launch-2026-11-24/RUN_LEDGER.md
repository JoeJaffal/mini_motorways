# Bounded training run ledger — 24 November 2026

Generated from `run-register.json`. This is an alphabetical index; chronological decisions are in `training/EXPERIMENT_HISTORY.md`. Includes interrupted attempts and smoke checks. Saved decisions exclude unsaved work. Midgame continuations start after a recorded native prefix and are not full-start cities. Completed practice episodes can be one decision and are not full cities. Weights/binaries stay local-only. No eight-hour session has been launched.

| Run | Status | Saved decisions | Completed cold cities | Completed midgame continuations | Completed practice episodes | Base LR | Horizon |
|---|---|---:|---:|---:|---:|---:|---:|
| city-strategy-balanced-extension-01/segment-001 | complete | 32,768 | 37 | 0 | 8396 | 0.001 | 600 |
| city-strategy-balanced-fast-01 | complete | 24,576 | 30 | 0 | 6192 | 0.001 | 600 |
| city-strategy-balanced-pilot-01 | Stopped at saved8k for parity-checked acceleration; worker-close hang cleaned up | 8,192 | 12 | 0 | 2084 | 0.001 | 600 |
| city-strategy-bridge-balanced-01/segment-001 | Stopped at saved24576 after longer baseline favored calibrated reference; unsaved tail not carried forward | 24,576 | 19 | 0 | 7967 | 0.0001 | 1200 |
| city-strategy-bridge-reference-city-01/segment-001 | complete | 65,536 | 90 | 0 | 0 | 0.0001 | 1200 |
| city-strategy-bridge-reference-rate-01/segment-001 | complete | 32,768 | 47 | 0 | 0 | 0.001 | 1200 |
| city-strategy-city-only-01/segment-001 | complete | 65,536 | 134 | 0 | 0 | 0.0001 | 600 |
| city-strategy-city-rate-01/segment-001 | complete | 32,768 | 64 | 0 | 0 | 0.0003 | 600 |
| city-strategy-critic-rate-01/segment-001 | complete | 32,768 | 45 | 0 | 0 | 0.0001 | 1200 |
| city-strategy-long-rollout-01/segment-001 | complete | 32,768 | 42 | 0 | 0 | 0.0001 | 1200 |
| city-strategy-longer-pilot-01 | Chat interruption before checkpoint | 0 | 0 | 0 | 0 | 0.003 | 1200 |
| city-strategy-longer-pilot-02 | complete | 32,768 | 93 | 0 | 0 | 0.003 | 1200 |
| city-strategy-mixed-pilot-01 | Stopped at saved32k to correct sample allocation | 32,768 | 77 | 0 | 209 | 0.001 | 600 |
| city-strategy-opening-01/segment-001 | complete | 65,536 | 135 | 0 | 0 | 0.0001 | 600 |
| city-strategy-original-delay-01/segment-001 | complete | 65,536 | 71 | 0 | 16198 | 0.0001 | 600 |
| city-strategy-pilot-01 | complete | 65,536 | 168 | 0 | 0 | 0.003 | inherited |
| city-strategy-recorded-city-01/segment-001 | complete | 65,536 | 22 | 100 | 0 | 0.0001 | 1200 |
| city-strategy-recorded-integration-smoke-01 | Complete integration smoke only; never a performance candidate | 256 | 0 | 0 | 0 | 0.0001 | 1200 |
| city-strategy-return-advantage-01/segment-001 | complete | 32,768 | 34 | 0 | 8349 | 0.001 | 600 |
| city-strategy-runner-smoke-01/segment-001 | complete | 512 | 2 | 0 | 0 | 0.001 | 600 |
| city-strategy-short-delay-01/segment-001 | Stopped at saved16384 midpoint after measured gradient imbalance; unsaved tail not carried forward | 16,384 | 25 | 0 | 5359 | 0.001 | 600 |
| city-strategy-task-batch-01/segment-001 | complete | 32,768 | 42 | 0 | 8340 | 0.001 | 600 |
| city-strategy-value-balance-01/segment-001 | complete | 32,768 | 48 | 0 | 8538 | 0.001 | 600 |
| city-strategy-wide-pilot-01 | Chat interruption; unsaved updates lost | 0 | 70 | 0 | 0 | 0.003 | 600 |
| city-strategy-wide-pilot-02 | Stopped for RAM pressure before first checkpoint | 8,192 | 4 | 0 | 0 | 0.003 | 600 |
| city-strategy-wide-pilot-03 | complete | 65,536 | 150 | 0 | 0 | 0.003 | 600 |

## Main measured findings

| Evidence | Result | Interpretation |
|---|---|---|
| Frozen new native skill cohort | Reservation7/64→32/64;priority67/128→128/128 | Learned skills generalize within these exercise families |
| Fresh road-only city confirmation04 | 85.95→86.19 on64 cities | No substantial city-score gain |
| City-only corrected-optimizer final | 78.22→89.76 on96 reused cities;reservation9/16→4/16 vs own start | Some development gain;skill tradeoff;no promotion |
| Opening-only final | 78.22→84.28 on96 reused cities | No substantial gain;established practice rows retained exactly |
| Bridge interface fix,same unchanged reference | 69.19→124.41 on32 reused cities;paired+55.22[34.03,76.16] | Engineering action-coverage gain,not PPO |
| Bridge-enabled longer PPO continuation | See current status and live run register | Bounded experiment;not a long launch |

See `README.md`, `PLAN.md`, and the measurement JSON files for checkpoint hashes, exact comparisons, limits, failed hypotheses and superseding decisions. The normalized bridge-choice prototype is unused.
