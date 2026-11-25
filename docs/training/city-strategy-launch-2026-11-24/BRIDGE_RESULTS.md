# Matched bridge-city development results

All rows use32 full-start cities, RNG950241,1200 native seconds and the same bridge-enabled host. Reference mean230.96875,29 scoring cities. These are reused selection data, not independent confirmation. No row establishes the declared substantial-gain gate.

| Candidate | Mean | Scoring | Paired difference (95% interval) | Zero-stock target arrivals |
|---|---:|---:|---|---:|
| bridge-city-only-longer | 220.00 | 29/32 | -10.97 [-74.56, 49.59] | 43 |
| bridge-balanced-saved-longer | 183.69 | 29/32 | -47.28 [-115.19, 16.88] | 8 |
| bridge-reference-midpoint-longer | 231.00 | 29/32 | +0.03 [-61.81, 62.91] | 54 |
| bridge-reference-final-longer | 196.50 | 29/32 | -34.47 [-100.94, 25.62] | 45 |
| bridge-rate-midpoint-longer | 244.44 | 29/32 | +13.47 [-52.69, 75.16] | 50 |
| bridge-rate-final-longer | 181.91 | 29/32 | -49.06 [-116.63, 10.28] | 37 |
| recorded-midpoint-longer | 211.31 | 29/32 | -19.66 [-110.00, 67.97] | 51 |
| recorded-final-longer | 234.91 | 29/32 | +3.94 [-79.75, 84.69] | 104 |
| critic-rate-midpoint-longer | 205.62 | 29/32 | -25.34 [-102.13, 43.13] | 37 |
| critic-rate-final-longer | 220.53 | 29/32 | -10.44 [-75.81, 52.13] | 48 |
| long-rollout-midpoint-longer | 239.16 | 29/32 | +8.19 [-27.84, 42.94] | 49 |
| long-rollout-final-longer | 213.03 | 29/32 | -17.94 [-78.75, 39.72] | 43 |

Reference zero-stock target arrivals44. Counts also depend on how long the city survives; use paired full-city outcomes rather than interpreting stockout totals in isolation.

Higher-rate midpoint additionally fails broader64-city development:231.55 vs262.77, paired−31.22 [−83.00,19.58]. Combined96 cities:235.84 vs252.17. Fresh confirmation950247 and reserved950245 remain unused.

Critic-head-rate trial failed the gain gate. Longer-rollout trial also failed the gain gate. All jobs complete; no long run launched. Weights remain local-only; comparison JSONs retain source run paths and paired measurements.
