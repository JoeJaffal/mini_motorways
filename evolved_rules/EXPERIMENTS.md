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
- **Why games end** (`autopsy.py`, best rule on 1500–1549; it reproduces the run's 222.0 exactly):
  - Causes: car shortage 34, slow arrival 11, gridlock 4 (at least 80% of the colour's driving cars nearly stopped), unreachable cars 1.
  - At failure, the failing colour had about 10 houses, all reaching the shop, and about 20 cars. Of those cars, 20 were busy and 0.5 at home.
  - Half of the colour's driving cars, and 41% of all driving cars, were nearly stopped. Parked cars are excluded from these shares.
  - About 44 road tiles were still unused.
  - So the limit is congestion, not tiles or connectivity. The planner has no move that spends tiles to relieve traffic: no bypasses or parallel roads, and it never places traffic lights or roundabouts.

**Verdict:** the run has not converged in any useful sense. The search needs fixing before it runs further.

**Next:** gp-2, which fixes the search (below). After that, add moves that relieve congestion.

## 2026-11-02: gp-2, fixed search

**Changes from gp-1:**
- **Racing:** every individual plays 8 seeds, and the top 16 play 24 more (32 in total).
- **Validation:** the racing top 3 are validated each generation.
- **Behavioural de-duplication:** individuals with identical games count once. Each duplicate frees a slot, and up to 8 per generation go to fresh random immigrants. There are no exact copies.
- **Stop rule:** a gain must also pass a one-sided paired t-test against the anchor on the 50 validation seeds, at α = 0.005. Without this, luck would reset the counter in most generations.
- **Inputs:** `pending_refunds` and `type_5` are dropped. Older texts that read them still load, with each read as the constant 0.0, its only value.

**Notes from the review:**
- **The stop rule is strict.** For two unrelated rules, the paired SD is about 100, so a gain needs about 38 trips to count. For close relatives (SD about 19) it needs about 7. Gains measured from the anchor still accumulate.
- **The final model is the best of many noisy validation means.** Report it on held-out seeds: 2000–2019 for development, 7000–7099 for the final test.

**Smoke test** (`gp2-smoke`: population 12, 4+4 seeds, 10 validation seeds): it ran on real games. Generation 0 had 9 behaviours among 12 texts and 3 immigrants. In generation 1, candidates at +10.6 and +11.2 trips were correctly not counted (t 0.73 and 0.61, critical value 3.25).

**Results so far:** the full run `gp-2` (b8e82a0) started 2026-11-02 12:46 and is still running. Generations 0–7 are below, recorded at 18:47.

| Gen | Validated (top 3) | Best so far | Best paired t (needs 2.68) | No-gain count | Round-1 avg | Behaviours / 64 | Time |
|---|---|---|---|---|---|---|---|
| 0 | 174.9, 191.4, 196.8 | 196.8 | – | 0 | 101.3 | 46 | 14 min |
| 1 | 206.6, 206.5, 197.7 | 206.6 | 0.93 | 1 | 170.7 | 44 | 23 min |
| 2 | 219.0, 203.5, 194.5 | 219.0 | 1.35 | 2 | 165.8 | 41 | 18 min |
| 3 | 197.3, 187.9, 197.7 | 219.0 | 0.46 | 3 | 174.5 | 47 | 32 min |
| 4 | 208.1, 218.5, 192.5 | 219.0 | 1.30 | 4 | 188.9 | 52 | 30 min |
| 5 | 206.4, 224.3, 226.5 | 226.5 | 1.80 | 5 | 184.6 | 46 | 20 min |
| 6 | 202.8, 224.3, 203.1 | 226.5 | 1.68 | 6 | 201.6 | 51 | 19 min |
| 7 | 225.6, 236.7, 211.9 | **236.7** | 2.44 | 7 | 176.0 | 50 | 115 min (about 80 of it asleep) |

**Observations:**
- **The best validated score rose steadily.** It went from 196.8 to 236.7 in 7 generations, above gp-1's 222 and 49 above the separated preference.
- **No gain has passed the paired test yet.** The anchor is still generation 0's 196.8. The closest was generation 7's +40 trips, at t 2.44 against the 2.68 needed.
- **The population keeps improving.** The round-1 average rose from 101 to about 180–200.
- **The sleep fix works.** The lid was closed twice (15:23–16:43 and 17:18–18:32). Both times the run logged `suspend detected` and kept going: no game was killed and nothing crashed.
