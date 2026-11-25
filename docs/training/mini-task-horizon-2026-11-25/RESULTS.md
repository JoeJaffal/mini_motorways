# Lesson-duration comparison

One training seed per arm; repeated development evaluations. Both arms are evaluated on the same 300-second small-city lessons and 600-second cities. Longer lesson returns cannot be compared directly with historical 60-second returns. No automatic promotion or generalization claim.

| Added decisions | Arm | City mean | Scoring games | Tight single served | Both pairs served |
|---:|---|---:|---:|---:|---:|
| 65536 | short-control | 110.19 | 28/32 | 43.8% | 18.8% |
| 65536 | long-window | 137.53 | 31/32 | 50.0% | 25.0% |
| 131072 | short-control | 116.75 | 29/32 | 50.0% | 18.8% |
| 131072 | long-window | 146.69 | 31/32 | 56.2% | 18.8% |
| 262144 | short-control | 106.19 | 27/32 | 43.8% | 25.0% |
| 262144 | long-window | 98.47 | 30/32 | 50.0% | 12.5% |

Parent city mean: 126.09; retained original: 126.09.

Final city comparisons against the retained original:

- short-control: -19.91, paired seed-bootstrap 95% interval [-42.90625, 4.46875].
- long-window: -27.62, paired seed-bootstrap 95% interval [-56.0625, 2.1257812499999886].

Inspect behavior and fresh held-out confirmation before claiming readiness. Improving from a regressed parent alone does not establish a better model.
