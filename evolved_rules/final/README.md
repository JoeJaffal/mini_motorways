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

## Test set, LA 7000–7099 (run once, 2026-11-07)

Four locked policies, 100 maps each, every replay recorded and verified (400/400). Paired per-map differences (PLAN.md section 6); `test_7000-7099.json` has the full record.

| Policy | Mean | Median |
|---|---|---|
| CMA-ES final | 250.6 | 250.0 |
| GP final | 245.9 | 252.5 |
| Separated rule | 216.3 | 207.5 |
| Hand rule | 170.8 | 149.0 |

| Comparison | Mean diff | 95% bootstrap CI | paired-t CI | Wilcoxon p | better / worse |
|---|---|---|---|---|---|
| GP − hand | +75.1 | [+54.8, +95.5] | [+54.4, +95.9] | 3.4e-10 | 83 / 17 |
| GP − separated | +29.6 | [+9.9, +49.5] | [+9.5, +49.7] | 0.0057 | 63 / 36 |
| GP − CMA-ES | −4.7 | [−22.9, +13.1] | [−23.2, +13.7] | 0.64 | 46 / 53 |
| CMA-ES − hand | +79.8 | [+58.8, +100.3] | [+58.8, +100.9] | 3.6e-10 | 80 / 20 |
| separated − hand | +45.5 | [+24.0, +67.3] | [+23.6, +67.5] | 8.9e-05 | 69 / 30 |

**Verdict.** GP beats both hand-written rules with intervals that exclude 0. It does not beat CMA-ES: the two are statistically tied. The PLAN.md success criterion (beat the hand rule and CMA-ES) is met for the hand rule only. Each method was run once (no run-to-run variance), so this compares these two rules, not the methods.

## Head-to-head with PPO, LA 9000–9099 (run once, 2026-11-07)

Maps agreed as fresh for both sides. GP final (replays verified, 100/100) against Mohammad's checkpoint `validation-best.zip` (MaskablePPO, about 100k steps), played with his own evaluator (`training/evaluate_checkpoint.py`, branch `mohammad` at a652042) in both modes. His sampling seed per map follows his protocol (43 + seed offset), split into 5 blocks of 20 seeds. Both sides use a 3600 s cap. His branch's simulator adds only read-only probes; the same three rules on three maps played identical games on both builds (9/9). His evaluator does not verify replays. `h2h_ppo_9000-9099.json` has the full record.

| Agent | Mean | Median |
|---|---|---|
| GP final | 245.3 | 258.0 |
| PPO, sampled | 200.7 | 191.5 |
| PPO, deterministic | 193.4 | 165.5 |

| Comparison | Mean diff | 95% bootstrap CI | paired-t CI | Wilcoxon p | better / worse |
|---|---|---|---|---|---|
| GP − PPO deterministic | +51.9 | [+31.7, +73.3] | [+30.6, +73.2] | 4.0e-06 | 66 / 34 |
| GP − PPO sampled | +44.6 | [+24.9, +64.1] | [+24.4, +64.9] | 2.5e-05 | 70 / 29 |
