# Mini-task reset curriculum comparison

Single training seed per recipe; repeated development evaluation; fresh empty-board/city confirmation required. Selected reset bank performance is not transfer evidence.

| Decisions | Recipe | City score | Scoring /32 | Tight single | Later pair |
|---:|---|---:|---:|---:|---:|
| 65536 | cold-control | 115.66 | 27 | 43.8% | 12.5% |
| 65536 | reset-curriculum | 113.78 | 30 | 43.8% | 12.5% |
| 131072 | cold-control | 131.78 | 31 | 50.0% | 12.5% |
| 131072 | reset-curriculum | 100.06 | 28 | 43.8% | 12.5% |
| 262144 | cold-control | 115.25 | 29 | 50.0% | 18.8% |
| 262144 | reset-curriculum | 89.25 | 24 | 50.0% | 12.5% |

Final checkpoint city comparisons versus original:

- cold-control: -10.84; paired95% interval [-36.21875, 14.84375].
- reset-curriculum: -36.84; paired95% interval [-61.65625, -15.15625].

No automatic promotion or overnight extension. Inspect trajectories, hard-layout performance and fresh confirmation before selecting a candidate.
