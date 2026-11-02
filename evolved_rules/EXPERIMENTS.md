# Evolved Rules: experiment log

Newest entry at the bottom. Each entry covers what was tried, the results and the verdict. Scores are mean trips on Los Angeles (OriginalReference), with a 3600 s cap.

## Baselines

| Rule | Validation 1500–1549 (n = 50) | Dev 2000–2019 (n = 20) |
|---|---|---|
| Do nothing | – | 0 |
| Hand rule (Phase 1) | 153.1 (median 133, 56–423) | 152.1 |
| Separated preference | 187.5 (median 177, 73–369) | 251.4 |

## 2026-10-30: Phase 1, skeleton and hand rule (87256e6)

The hand rule scores 152.1 on 2000–2019 (the bar was 140). All 21/21 replays verify. Details are in PLAN.md section 7.

## 2026-11-02: gp-1, first GP run (2f8be14, resumed on 49c8197)

**Setup:**
- Population of 64 individuals, each with 3 trees (Priority, Hold, Upgrade).
- Racing: every individual plays 4 seeds and the top 16 play 8 more.
- One individual is validated on 1500–1549 per generation.
- Stop rule: 20 generations without a gain of at least 2%.

| Gen | Validated | Best so far | No-gain count | Training avg (4 seeds) |
|---|---|---|---|---|
| 0 | 222.0 (new) | 222.0 | 0 | 93.9 |
| 1 | 222.0 (same) | 222.0 | 1 | 190.3 |
| 2 | 222.0 (smaller twin) | 222.0 | 2 | 219.4 |
| 3 | 222.0 (same) | 222.0 | 3 | 304.9 |
| 4 | 221.5 | 222.0 | 4 | 199.4 |
| 5 | 212.1 | 222.0 | 5 | 256.4 |

**Best:** 222.0 trips on validation, which is +34.5 over the separated preference and +68.9 over the hand rule. About 3 trips per road tile.

**Status:** paused after generation 5, at the generation-6 checkpoint. The laptop hard-reset twice while the lid was closed under full load (08:39 and 10:04).

**Findings:**
- **Selection is mostly luck.** One rule's trips vary by SD ≈ 91 from seed to seed, so a 4-seed mean is only good to about ±45 and a 12-seed mean to about ±26. Among the top 16, the rank correlation between the 4-seed and 8-seed scores was between −0.67 and 0.34.
- **The top of the population collapsed.** In generations 2–3, all of the top 16 played identical games.
- **Some inputs are dead.** `pending_refunds` is always 0 because nothing is ever removed. The best rule's Upgrade tree reads it, so it always takes offer 0.

**Verdict:** the run has not converged in any useful sense. The search needs fixing before it runs further.

**Next:** gp-2, with:
- racing on 8 seeds, with the top 16 playing 32 in total;
- 3 individuals validated per generation;
- behavioural de-duplication;
- dead inputs removed;
- a failure autopsy of the best games.
