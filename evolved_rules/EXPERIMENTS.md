# Evolved Rules: experiment log

Newest entry at the bottom. Each entry covers what was tried, the results and the verdict. Scores are mean trips on Los Angeles (OriginalReference), with a 3600 s cap.

**Best and average.** Every evolution table gives both:
- **Best:** a rule set's average trips over the 50 validation maps (1500–1549). This is the score of the top validated rule sets.
- **Average:** the average trips of every rule set in that generation, on that generation's round-1 training maps. The maps change every generation, so this number swings with how hard they are.

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

| Gen | Best validated (50 maps) | Best so far | No-gain count | Average, all 64 rule sets (4 training maps) |
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

**Results:** the full run `gp-2` (b8e82a0) started 2026-11-02 12:46 and was **paused on 2026-11-03 at 08:50 after 16 generations (0–15), not converged**. The user paused it to run gp-3. Its checkpoint is at generation 16 (format 2); resume it with `--resume` using the code of commit b8e82a0.

| Gen | Best validated, top 3 (50 maps) | Best so far | Best paired t (needs 2.68) | No-gain count | Average, all 64 rule sets (8 training maps) | Behaviours / 64 | Time |
|---|---|---|---|---|---|---|---|
| 0 | 174.9, 191.4, 196.8 | 196.8 | – | 0 | 101.3 | 46 | 14 min |
| 1 | 206.6, 206.5, 197.7 | 206.6 | 0.93 | 1 | 170.7 | 44 | 23 min |
| 2 | 219.0, 203.5, 194.5 | 219.0 | 1.35 | 2 | 165.8 | 41 | 18 min |
| 3 | 197.3, 187.9, 197.7 | 219.0 | 0.46 | 3 | 174.5 | 47 | 32 min |
| 4 | 208.1, 218.5, 192.5 | 219.0 | 1.30 | 4 | 188.9 | 52 | 30 min |
| 5 | 206.4, 224.3, 226.5 | 226.5 | 1.80 | 5 | 184.6 | 46 | 20 min |
| 6 | 202.8, 224.3, 203.1 | 226.5 | 1.68 | 6 | 201.6 | 51 | 19 min |
| 7 | 225.6, 236.7, 211.9 | **236.7** | 2.44 | 7 | 176.0 | 50 | 115 min (about 80 of it asleep) |
| 8 | 236.7 (cached), 207.3, 211.1 | 236.7 | 2.44 | 8 | 172.2 | 54 | 95 min (about 74 of it asleep) |
| 9 | 236.7 (cached), 192.9, 193.0 | 236.7 | 2.44 | 9 | 178.1 | 49 | 46 min |
| 10 | 204.6, 195.6, 218.5 | 236.7 | 1.30 | 10 | 176.6 | 51 | 49 min |
| 11 | 221.0, **242.8**, 233.4 | **242.8** | **2.79** (counted) | 0 | 168.5 | 50 | 52 min |
| 12 | 230.9, 233.5, 204.6 (cached) | 242.8 | −0.62 | 1 | 179.6 | 53 | 53 min |
| 13 | 239.5, 221.5, 213.4 | 242.8 | −0.24 | 2 | 185.8 | 50 | 70 min |
| 14 | 228.0, **245.1**, 214.7 | **245.1** | 0.18 | 3 | 169.5 | 54 | 58 min |
| 15 | 235.4, 206.9, 225.9 | 245.1 | −0.59 | 4 | 174.8 | 51 | 495 min (about 7 h asleep, unplugged) |

**At the pause:**
- The final model is 245.1 trips on validation (generation 14, 62 nodes). It is the best of 43 noisy validation means, so its true level is probably a little lower; held-out seeds will tell.
- The anchor is 242.8 (generation 11), and the no-gain count was 4 of 20.
- That is +57.6 over the separated preference and +92.0 over the hand rule on 1500–1549.
- It has not been tested on held-out seeds yet (2000–2019 dev, 7000–7099 test).

## 2026-11-03: gp-3 hand tests, traffic moves (road only)

Plan: `plans/2026-11-03-gp3-traffic.md`. There are no traffic lights, roundabouts or motorways (user decision).

**Diagnosis** (gp-2's best rule, 20 lost games on 1500–1519, `autopsy.py`):
- About 70% of stuck cars wait at junctions and about 27% at a shop's single car-park gate.
- About 6 of the failing colour's 11 stuck cars are within 3 tiles of the failing shop.
- About 40% of road cells are junctions, and the failing shop's doorstep has 3.5 links on average.

**New moves:**
- **Clean routes** avoid junction links near doorsteps.
- **Removal** of a tile that feeds a crowded doorstep, offered only when every connection is kept.
- **Traffic inputs.**

Each move is opt-in, and older rules play exactly as before.

**Hand rules on 1500–1519 (n = 20):**

| Rule | Trips | Notes |
|---|---|---|
| gp-2 best | 213.4 | identical to gp-2's own record of these games |
| gp-2 best + clean routes offered | 210.0 | its priority tree does not know `is_clean` |
| separated + coverage (old moves) | 167.7 | 42 tiles left at the end |
| CleanHand (always a clean route first) | 139.4 | Doorstep links fell from 3.5 to 2.2, junctions near the failing shop roughly halved, and stuck cars near shops fell from 4.3 to 1.1. But it used about 20 tiles more and ran out of tiles in 3 games. Better on 6 of 20 seeds, sometimes by a lot (e.g. 249 vs 166, 161 vs 92). |
| separated + coverage + removal (`seprm`) | 161.9 | About 0.6 removals per game. Equal on 12 seeds, better on 3, worse on 5. |

**Verdict:** neither move helps as a fixed rule. Clean routes help on some maps and hurt on others, and which maps those are is exactly what evolution can learn from the traffic inputs. Next: gp-3, an evolution run with 4-tree individuals, seeded with gp-2's best rule.

**Observations:**
- **The best validated score rose steadily.** It went from 196.8 to 236.7 in 7 generations, above gp-1's 222 and 49 above the separated preference.
- **No gain has passed the paired test yet.** The anchor is still generation 0's 196.8. The closest was generation 7's +40 trips, at t 2.44 against the 2.68 needed.
- **The population keeps improving.** The round-1 average rose from 101 to about 180–200.
- **Plateau forming (generations 8–10).** The generation-7 record holder (236.7) topped the racing in generations 8 and 9, and no new candidate came close to it. The round-1 average has stayed at about 172–200 since generation 4. This fits the gp-1 autopsy: with the current moves, congestion caps the score.
- **Generations are slower now, about 45–50 min.** Better rules survive longer, and long games cost more to simulate.
- **The plateau was not convergence.** Generation 11 found 242.8 trips: +46.1 over the anchor, paired t 2.79 against the 2.68 needed. This is the run's first counted improvement. The anchor moved to 242.8 and the no-gain count went back to 0, so at least 20 more generations are needed before the run can converge. The best rule built 3.17 trips per road tile, the most efficient so far.
- **The sleep fix works.** The lid was closed twice (15:23–16:43 and 17:18–18:32). Both times the run logged `suspend detected` and kept going: no game was killed and nothing crashed.


## 2026-11-03: gp-3, traffic moves under evolution (d80fc8d)

**Setup:** as gp-2, plus 4-tree individuals (remove tree, clean routes, removals, traffic inputs).

**Seeds:** the hand rule, the separated rule, the clean rule, gp-2's best (245.1), and from attempt 2 a never-clean copy of gp-2's best.

**Attempt 1 (stopped after generation 0):**

| | Best validated (50 maps) | Average, all 64 rule sets (8 training maps) |
|---|---|---|
| Generation 0 | 228.1 (the gp-2 seed) | 83.1 |

- With clean routes offered, gp-2's best scored 228.1 against its own 245.1 on the same 50 maps. It was better on 16, worse on 24 and equal on 10. Its trees do not know `is_clean`, so they sometimes pick a clean route by chance.
- That handicaps gp-3 from the start, so attempt 1 was stopped and kept as `evolve/gp-3-attempt1`.

**Attempt 2** (`evolve/gp-3`, started 2026-11-03 10:53):
- **The added seed** is a never-clean copy of gp-2's best. Its priority tree is the same function written without the root `neg` and the double `neg`s (both exact in IEEE arithmetic), minus 1000 × is_clean. All trees stay within depth 6.
- **It plays gp-2's games exactly.** On seeds 1500, 1503, 1511, 1525, 1531 and 1540 it matched every recorded (trips, seconds), including a 606-trip game.
- So gp-3 starts from gp-2's real level, and any gain over it comes from the traffic moves.

**Results:** pending.
