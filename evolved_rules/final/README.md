# Final GP rule (locked 2026-11-06)

`gp3_final.txt` is the final evolved rule (`209634e826f274fd`, 24 nodes), from gp-3.3's hall of fame.

Chosen once, on 200 maps no run had used (LA 4000–4199): gp-2's rule and the four re-tested hall leaders each played every map, and the highest mean won (`selection_4000-4199.json`). It must not change after this point. The test maps 7000–7099 and the PPO head-to-head maps have not been played by any GP rule.

| Rule | Mean, 4000–4199 | vs gp-2's rule (± SE) |
|---|---|---|
| gp-2's rule | 238.5 | – |
| **209634e8 (final)** | **257.2** | **+18.7 ± 9.1** |
| 6a4a4540 | 256.0 | +17.5 ± 8.0 |
| 70ddd60b | 253.7 | +15.2 ± 7.7 |
| 1737ea1b | 249.9 | +11.4 ± 8.3 |

Picking the best of five on these maps flatters the winner slightly; the test-set numbers are the ones to report.

## Final CMA-ES rule (locked 2026-11-07)

`cma_final.txt` is CMA-ES's final weight set (`fa7648c7352d9db2`, run `cma-1`, converged after 30 generations, its validation incumbent at 231.8 on 1500–1549). Chosen the same way as the GP rule: its four best validated weight sets played LA 4000–4199 and the highest mean won (`cma_selection_4000-4199.json`).

| CMA-ES candidate | Mean, 4000–4199 |
|---|---|
| **fa7648c7 (final)** | **249.2** |
| f1a6ac88 | 245.5 |
| 31de7d5d | 244.9 |
| d39401f1 | 244.0 |

Expectation written before the test: on 4000–4199 the GP final leads the CMA-ES final by +8.0 ± 9.1 trips. A 100-seed test detects about 25–30 trips, so GP vs CMA-ES will probably not exclude 0 on 7000–7099.
