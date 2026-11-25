# Native-score expansion curriculum comparison

Both branches start from the exact retained original policy. City-only control and expansion curriculum each receive262144additional decisions. The curriculum uses eight city, four later-pair and four single-connection workers, with task-homogeneous minibatches for within-task advantage normalization. This compares a curriculum recipe, not task mix in isolation. Native deliveries are the only reward throughout. No planner, imitation, new road penalty or simulator change.

| Added decisions | Arm | City mean score | City games scoring /32 | Single success | First pair served | Both pairs served |
|---:|---|---:|---:|---:|---:|---:|
| 65536 | city-only | 137.03 | 30 | 51.6% | 67.2% | 18.8% |
| 65536 | expansion | 116.03 | 28 | 51.6% | 67.2% | 23.4% |
| 131072 | city-only | 116.56 | 29 | 51.6% | 62.5% | 21.9% |
| 131072 | expansion | 126.47 | 31 | 51.6% | 65.6% | 20.3% |
| 262144 | city-only | 88.56 | 27 | 51.6% | 60.9% | 21.9% |
| 262144 | expansion | 117.50 | 27 | 53.1% | 75.0% | 25.0% |

Original city mean: 126.09. Fixed final-checkpoint comparisons:

- city-only minus original: -37.53; paired95%interval[-63.91,-10.22].
- expansion minus original: -8.59; paired95%interval[-29.59,+13.28].
- Expansion minus city-only: +28.94; paired95%interval[+3.66,+53.22].

Intervals resample scenario seeds with both action RNGs together. Practice success does not establish city improvement. Compare the entire curve and uncertainty; do not treat an early uncertain point as failure or a single high score as proof. Native city returns and finite lesson returns differ in scale; per-task advantage records preserve the diagnostic evidence.

The prior reward audit found correct native delivery accounting. Repeated deliveries remain legitimate game points. All checkpoints are preserved; no automatic promotion or additional run follows. Any claimed gain needs independent training-seed replication and fresh city confirmation. See DIAGNOSIS.md and PLAN.md for rationale, preflight evidence, sources and limits.
