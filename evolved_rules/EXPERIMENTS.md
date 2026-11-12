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

**Seeds:** the hand rule, the separated rule, the clean rule, gp-2's best (245.1), and from gp-3.2 a never-clean copy of gp-2's best.

**gp-3.1 (attempt 1, stopped after generation 0):**

| | Best validated (50 maps) | Average, all 64 rule sets (8 training maps) |
|---|---|---|
| Generation 0 | 228.1 (the gp-2 seed) | 83.1 |

- With clean routes offered, gp-2's best scored 228.1 against its own 245.1 on the same 50 maps. It was better on 16, worse on 24 and equal on 10. Its trees do not know `is_clean`, so they sometimes pick a clean route by chance.
- That handicaps gp-3 from the start, so gp-3.1 was stopped and kept as `evolve/gp-3.1`.

**gp-3.2** (attempt 2, folder `evolve/gp-3.2`, started 2026-11-03 10:21):
- **The added seed** is a never-clean copy of gp-2's best. Its priority tree is the same function written without the root `neg` and the double `neg`s (both exact in IEEE arithmetic), minus 1000 × is_clean. All trees stay within depth 6.
- **It plays gp-2's games exactly.** On seeds 1500, 1503, 1511, 1525, 1531 and 1540 it matched every recorded (trips, seconds), including a 606-trip game.
- So gp-3.2 starts from gp-2's real level, and any gain over it comes from the traffic moves.

**Expectations (2026-11-03, before results):**
- gp-2's gains slowed from about +6 per generation (generations 0–7) to about +1 (generations 7–14), and its average stayed at about 170–185 from generation 4 on. More gp-2 generations would add only a few trips.
- gp-3.2 can do more only if evolution learns when to take a clean route. In the hand tests clean routes won on about 1 map in 3, sometimes by 60–80 trips, and lost on the rest.
- Guess: gp-3.2 ends between gp-2's level and 20–40 trips above it, with the first gains around generations 5–15 if they come.

**What to watch:**
- a counted improvement, meaning a paired t above the critical value against the anchor;
- the average of all 64 rule sets rising above gp-2's 170–185;
- the best trees reading `is_clean`, the traffic inputs, or a remove tree that is not constant.

If nothing counts by about generation 15, the moves themselves are not enough. The next change would then be something other than more generations: more seeds per evaluation (less noise), or new move types.

| Gen | Best validated, top 3 (50 maps) | Best so far | Best paired t | No-gain count | Average, all 64 rule sets (8 training maps) | Behaviours / 64 | Time |
|---|---|---|---|---|---|---|---|
| 0 | 228.1, 245.1, 191.5 | 245.1 | – | 0 | 91.8 | 48 | 51 min |
| 1 | 230.9, 228.1, 245.1 | 245.1 | −1.28 | 1 | 180.1 | 46 | 14 min (resumed after a battery stop; 655 games cached) |
| 2 | 244.2, 244.8, 245.0 | 245.1 | −0.01 | 2 | 201.7 | 52 | 74 min |
| 3 | 228.1, 244.2, 243.3 | 245.1 | −0.25 | 3 | 181.7 | 46 | 53 min |
| 4 | 231.1, 226.2, 227.1 | 245.1 | −1.25 | 4 | 180.1 | 47 | 62 min |
| 5 | 229.2, 228.7, 237.7 | 245.1 | −0.45 | 5 | 206.5 | 45 | 10 min (resumed after the pause; most games cached) |
| 6 | 227.4, 220.2, 229.2 | 245.1 | −1.03 | 6 | 172.8 | 44 | 57 min |
| 7 | 221.1, 220.2, 218.6 | 245.1 | −1.49 | 7 | 197.7 | 44 | 64 min |

**Paused** on 2026-11-03 at 16:10, during generation 5, while the user was offline, and resumed at 20:14. The run folder and logs were renamed from `gp-3` to `gp-3.2` at that pause; the run does not record its folder name.

**Stopped** on 2026-11-03 at 22:31, during generation 8 (no-gain count 7/20), and replaced by gp-3.3. The checkpoint is at generation 8; `--run gp-3.2 --resume` continues it with the gp-3.3 code (the hall of fame is off for it, so it plays exactly as before).

**Why it was stopped: the search drifted.**
- Validated scores fell from about 244 (generation 2) to about 220 (generation 7). The best stayed 245.1 only because the run keeps its validated best.
- gp-2's rule left the elites after generation 1. In generation 2 it scored 289 on that generation's 8 first-round maps, missed the racing top 16, and so never played the other 24 maps. It was not in the elites again.
- Its replacements take clean routes freely and swing from map to map. The best of 16 on 32 maps scored 250–303 there but validated 218–237. Picking the top of noisy scores rewarded luck, not skill.
- Expected outcome if left running: stop as converged around generation 21 at 245.1, adding nothing over gp-2.

## 2026-11-03: gp-3.3, a hall of fame against selection noise

**Changes** (plans/2026-11-03-gp33-hall-of-fame.md, `--hof 8 --reference gp2-best-noclean.txt`):
- **Scores relative to a reference.** gp-2's rule (its never-clean copy) plays every generation's 32 training maps. A rule's score on a map is its trips minus the reference's trips there, so scores from different generations can be pooled.
- **Hall of fame (8 rules).** Members are re-tested on every generation's 32 maps and keep all their per-map differences. They are ranked by mean difference minus one standard error, so a rule that swings needs a bigger lead.
- **Fair entry and exit.**
  - A newcomer from the racing top is scored on the 24 maps it was not picked on.
  - Rules that play identical games count once, the member first.
  - A rule that leaves the hall keeps its record for if it comes back.
- **Probation.** Elites and validation take members that have already been re-tested at least once. The validation maps still never feed selection.
- **Seeds.** gp-2's rule and gp-3.2's five best validated variants (245.0, 244.8, 244.2, 243.3, 237.7). Choosing them by validation is a mild use of the validation maps; final scores come from held-out maps.
- Everything else as gp-3.2: 4-tree rules, 64 rule sets, 8 + 24 training maps, the same stop rule on 1500–1549.

**What to watch:** whether gp-2's rule stays in the hall and among the elites; whether validated scores stop drifting down; a counted improvement over 245.1.

**Results** (`evolve/gp-3.3`, started 2026-11-03 23:07). "Hall top" is the hall's best rule: its mean lead over gp-2's rule on the training maps it has played, and the lower bound the hall ranks by.

| Gen | Best validated, top 3 (50 maps) | Best so far | No-gain count | Average, all 64 rule sets (8 training maps) | Hall top: lead / bound (maps) | gp-2's rule: hall place, elite | Time |
|---|---|---|---|---|---|---|---|
| 0 | 237.7, 244.8, 245.1 | 245.1 | 0 | 88.2 | +51.0 / +29.1 (32), the 237.7 seed | 4th, yes | 47 min |
| 1 | 245.1, 244.8, 237.7 (all re-used) | 245.1 | 1 | 188.2 | gp-2's rule itself, 0 / 0 (63); the 237.7 seed fell to +14.7 / −2.0 (63) | 1st, yes | 65 min |
| 2 | 245.1, 244.2, 244.8 | 245.1 | 2 | 165.8 | gp-2's rule itself, 0 / 0 (92); best newcomers +10 / −8 (24–48, on probation) | 1st, yes | 55 min |
| 3 | 231.2, 245.1 (only 2 re-tested members) | 245.1 | 3 | 178.6 | newcomer +29.5 / +14.3 (24), on probation; 7 rules above gp-2's rule. The one re-tested climber, +21.0 / +7.8 (54), validated 231.2 | 8th, yes | 40 min |
| 4 | 245.1, 231.2, 232.1 | 245.1 | 4 | 176.5 | gp-2's rule itself, 0 / 0 (146). The generation-3 challengers fell to +0 to +8 when re-tested; the top four left the hall | 1st, yes | 45 min |
| 5 | 231.6, 231.2, 245.1 | 245.1 | 5 | 195.3 | newcomer +29.5 / +9.3 (24), on probation. Two re-tested members are now ahead of gp-2's rule: +13.3 / +1.6 (103 maps, 25 nodes) and +7.9 / +1.9 (79); both validated about 231 | 5th, yes | 48 min |
| 6 | 235.4, 240.5, 243.0 | 245.1 | 6 | 165.2 | small rules (24–35 nodes) fill the hall. Re-tested ones lead by +30 / +14 to +17 (56 maps); the 25-node one by +15.4 / +5.9 (132) | out, no | 48 min (slower: a check shared the CPU) |
| 7 | 240.5, 235.4, 228.3 | 245.1 | 7 | 200.9 | small rules hold: +30.2 / +18.1 (85 maps); 7 of 8 re-tested, all leading by +16 to +30 | out, no | 42 min |
| 8 | 240.5, 235.4, 236.1 | 245.1 | 8 | 217.8 | +25.4 / +14.6 (113 maps); all 8 lead by +13 to +25 (84–186 maps) | out, no | 44 min |
| 9 | 240.5, 235.4, 236.1 (all re-used) | 245.1 | 9 | 174.1 | newcomer +43.0 / +18.8 (24), on probation; re-tested leaders +21 / +11 (140 maps) | out, no | 35 min |
| 10 | 230.2, 240.5, 238.0 | 245.1 | 10 | 196.3 | generation 9's newcomer held: +38.1 / +24.4 (56 maps), yet 230.2 on 1500–1549; +25 / +16 (169–171 maps) behind it | out, no | 43 min |
| 11 | 230.2, 240.5, 238.0 (all re-used) | 245.1 | 11 | 185.7 | +39.5 / +28.3 (88 maps); +24 / +16 (196–200 maps) behind it | out, no | 36 min |

**Check on 100 never-used maps (3000–3099, after generation 5).** Every challenger that led gp-2's rule on training maps scored about 13 trips below it on 1500–1549. So gp-2's rule and the three leading hall members played 100 maps that no run had used:

| Rule | 1500–1549 (validation) | 3000–3099 (fresh) | vs gp-2's rule on fresh maps | Training lead in the hall |
|---|---|---|---|---|
| gp-2's rule (62 nodes) | 245.1 | 240.2 | – | – |
| `f9390485` (25 nodes) | 231.2 | **254.6** | **+14.4** (t 1.39; better on 52, worse on 42) | +15.4 (132 maps) |
| `48ee52f2` (70 nodes) | 231.2 | 251.7 | +11.5 (t 1.12) | +7.8 (80) |
| `12c41676` (61 nodes) | 231.6 | 238.7 | −1.6 (t −0.43) | +7.9 (79) |

- **The fresh maps agree with the training maps, not with validation.** The 25-node rule is about +14 to +15 ahead of gp-2's rule on both (232 maps together), but 14 behind on 1500–1549.
- **gp-2's rule is flattered by 1500–1549.** It was chosen as the best of about 43 rule sets on exactly those 50 maps, and it scores 5 trips lower on fresh ones. The stop rule measures every gp-3 challenger against that inflated 245.1.
- **The evidence for +14 is moderate,** not certain: about t 2 when training and fresh maps are pooled. With per-map swings of about ±100 trips, 50 maps can only confirm gains of about 38 trips for rules this different.

**Paused** on 2026-11-04 at 08:30, during generation 12 (no-gain count 11/20), at the user's request. The checkpoint is at generation 12; `--run gp-3.3 --resume` continues it.

**Where it stands at the pause:**
- **The best rule found is not gp-2's.** The hall's leader (`1737ea1b`, 28 nodes) leads gp-2's rule by **+39.5 trips over 88 training maps** (lower bound +28.3), and two others by about +24 over about 200 maps each. On 1500–1549 they score 230–240, the bias shown by the check above.
- **The stop rule cannot see this progress.** It still anchors to gp-2's 245.1 on 1500–1549, so left alone the run would stop as converged at generation 20 with gp-2's rule as its final model.
- **Proposed next step (not yet approved):** resume with the validation switched to 200 never-used maps (4000–4199) at sig_alpha 0.01. The `--revalidate` option is committed on branch `revalidate-prep` (97859ba), not merged.

**Outcome of the pause:** gp-3.3 was not resumed, and the `--revalidate` option was not used. Instead the final rule was picked once on 200 unused maps (entry below).

## 2026-11-06 to 2026-11-07: final rules, test set and PPO head-to-head

Summary in `final/RECAP.md`; every table is in `final/README.md`.

- **Final GP rule** `209634e8` (24 nodes, from gp-3.3's hall), chosen on 4000–4199: 257.2, against 238.5 for gp-2's rule. **Final CMA-ES weights** `fa7648c7` (run `cma-1`, converged after 30 generations, best 231.8 on validation, average of its 16 candidates 238.5 in generation 29), chosen the same way: 249.2.
- **Test, 7000–7099, run once, 400/400 replays verified:** GP 245.9, CMA-ES 250.6, separated 216.3, hand 170.8. GP − hand +75.1 (+54.8, +95.5); GP − separated +29.6 (+9.9, +49.5); GP − CMA-ES −4.7 (−22.9, +13.1), a tie. The success criterion is met for the hand rule only.
- **PPO head-to-head, 9000–9099:** GP 245.3, PPO sampled 200.7, PPO deterministic 193.4. GP − PPO deterministic +51.9 (+31.7, +73.3); GP − PPO sampled +44.6 (+24.9, +64.1).
- **Autopsy, 3000–3019:** mean 255.8. Car shortage 13, slow arrival 5, unreachable cars 2; 22.8 tiles left; a third of the failing colour's cars stuck; the remove tree never fires.
- **Not done:** run-to-run variance and other cities. Each method was run once.

## 2026-11-07: gp-4 step 1, lights and roundabouts (hand tests)

Plan: `plans/2026-11-07-gp4-lights-roundabouts.md`. Code at `a6025c5` (branch `gp4`). The planner can now place traffic lights and roundabouts. Nothing is evolved here, so the tables give means and medians, not best and average. The step-2 decision (evolve with these moves or not) is the user's.

**Setup:**
- **Maps:** LA 3100–3199 (100 dev maps), 3600 s cap, every replay recorded and verified: **900/900**.
- **Run:** `evaluate --policy <spec> --seeds 3100-3199 --verify`, one policy after the other, `--workers 6`. A first try at 10 workers crashed in its first run (`separated`) with `Failed to create CoreCLR, HRESULT 0x800705AA` (the host could not start; the machine had about 1 GB of free memory). Its partial folder is kept as `h4-separated.crashed1`. The rerun at 6 workers finished all 9 runs and both autopsies with no crash and no 4-worker retry. Games are deterministic per (policy, seed), so the worker count changes only the time.
- **Package upgrade rule:** take an offer for an enabled tool (traffic lights or roundabout) before anything else, and otherwise the offer with the most roads (the hand rule's upgrade). With no tool enabled it is just "most roads".
- **Placement rule (all policies that place):** a spot scores the number of cars stopped within 2 tiles of it. One tool is placed per decision, only when the best score is above 0 and the tool is in stock. Lights go on live junctions (link degree 3 or more). A roundabout that would merge networks serving different colours is skipped. Every decision looks for a spot. A placing policy also makes a decision when a tool is in stock and some car has waited 3 s, at most once per 5 s. Placed tools are never removed.

| Policy | What it is |
|---|---|
| `separated` | The Phase 1 separated preference. Baseline for the three hand rules. |
| `light`, `round`, `lightround` | Separated routes, hold and remove, plus the package upgrade rule, plus placement of lights, roundabouts, or both. |
| `tree:F` (`gp`) | The final GP rule (`209634e8`, `final/gp3_final.txt`), unchanged, with its own evolved upgrade tree. |
| `gppkg:F` | The GP rule's priority, hold and remove trees; its upgrade tree replaced by the package rule; no placement. Baseline for the three GP variants. |
| `gplight:F`, `gpround:F`, `gplightround:F` | `gppkg` plus placement of lights, roundabouts, or both. |

**Results** (100 maps each). Placements are counted from the accepted `build` actions with tool TrafficLight or Roundabout in each game's recording. This equals the count of those commands in `games.jsonl`, so no placement was rejected (2,284 placed in all; the only rejected commands in 900 games were 11 `draw`s). "Mean car wait" is, per game, the mean over all vehicles and all command steps of the host's per-car stopped time (cars that are moving count as 0), from `games.jsonl`; the table averages it over games.

| Policy | Mean | Median | Lights / game | Roundabouts / game | Games with a placement | Game length (s) | Mean car wait (s) | Verified |
|---|---|---|---|---|---|---|---|---|
| `separated` | 209.5 | 191.0 | 0 | 0 | 0 | 713 | 0.59 | 100/100 |
| `light` | 213.4 | 199.0 | 4.09 | 0 | 93 | 720 | 1.39 | 100/100 |
| `round` | 207.7 | 204.5 | 0 | 2.06 | 95 | 711 | 1.86 | 100/100 |
| `lightround` | 201.7 | 197.0 | 3.24 | 1.69 | 100 | 703 | 2.08 | 100/100 |
| `gp` | 250.3 | 253.0 | 0 | 0 | 0 | 778 | 0.65 | 100/100 |
| `gppkg` | 250.0 | 254.0 | 0 | 0 | 0 | 779 | 0.72 | 100/100 |
| `gplight` | 254.0 | 256.5 | 4.42 | 0 | 89 | 784 | 0.92 | 100/100 |
| `gpround` | 221.8 | 209.5 | 0 | 1.93 | 93 | 731 | 1.61 | 100/100 |
| `gplightround` | 237.2 | 233.0 | 3.56 | 1.85 | 100 | 759 | 1.81 | 100/100 |

**Paired comparisons** (per-map difference, A − B, 100 maps paired by scenario seed; descriptive, these are dev maps). Bootstrap CI: `scipy.stats.bootstrap` (BCa, 10,000 resamples, `random_state` 0), the same call that reproduces `final/test_7000-7099.json`. Wilcoxon is two-sided.

| A − B | Mean diff | 95% bootstrap CI | paired-t CI | Wilcoxon p | better / worse / equal |
|---|---|---|---|---|---|
| `light` − `separated` | +3.9 | [−14.0, +20.9] | [−13.8, +21.6] | 0.22 | 55 / 35 / 10 |
| `round` − `separated` | −1.9 | [−21.1, +17.3] | [−21.6, +17.9] | 0.79 | 45 / 47 / 8 |
| `lightround` − `separated` | −7.8 | [−29.3, +12.8] | [−29.0, +13.3] | 0.74 | 52 / 47 / 1 |
| `gplight` − `gppkg` | +4.0 | [−13.0, +21.4] | [−13.5, +21.5] | 0.53 | 45 / 40 / 15 |
| `gpround` − `gppkg` | −28.2 | [−48.3, −8.4] | [−48.3, −8.2] | 0.009 | 36 / 54 / 10 |
| `gplightround` − `gppkg` | −12.8 | [−33.0, +7.1] | [−33.2, +7.5] | 0.29 | 45 / 54 / 1 |
| `gppkg` − `gp` (the package rule alone) | −0.3 | [−10.0, +8.3] | [−9.5, +9.0] | 0.73 | 29 / 32 / 39 |

- **Spread.** The SD of the per-map differences is 88–107 trips for the placement comparisons (46.6 for `gppkg` − `gp`), so each 100-map interval is about ±17–21 wide. Differences of +4 are not resolved either way.
- **Lights.** +3.9 on the hand rule and +4.0 on the GP rule. `gplight` has the highest mean, 254.0, against 250.3 for `gp` (+3.7; not one of the planned comparisons, so no interval).
- **Roundabouts.** −1.9 on the hand rule and −28.2 on the GP rule, the one interval that excludes 0. Median difference −5.5 (worse on 54 maps, better on 36). `gpround` games are shorter: 731 s against 779 s for `gppkg`. For `round` against `separated` the lengths are 711 s and 713 s.
- **Both tools.** −7.8 on the hand rule and −12.8 on the GP rule.
- **Car wait.** Paired difference in each game's mean car wait, same bootstrap. Roundabouts raise it: `round` − `separated` +1.28 s [+0.90, +1.74] (0.59 to 1.86 s) and `gpround` − `gppkg` +0.89 s [+0.45, +1.46] (0.72 to 1.61 s). So do both tools: `lightround` − `separated` +1.50 s [+1.10, +2.01] and `gplightround` − `gppkg` +1.09 s [+0.62, +1.66]. Lights alone: `light` − `separated` +0.80 s [+0.49, +1.24], and `gplight` − `gppkg` +0.21 s [−0.04, +0.49], which includes 0.
- **Package rule alone.** Swapping the GP rule's upgrade tree for "most roads" changes the mean by −0.3. The two rules score the same trips on 39 of 100 maps (correlation of per-map trips 0.88), and play games identical in trips, seconds, commands and action counts on 33.
- **Placements are not rare.** Every both-tool game placed something (100/100). The both-tool rules place 4.9 and 5.4 tools per game (3.24 + 1.69 and 3.56 + 1.85).

**Autopsy** (`lightround` and `gplightround` on LA 3100–3119, 20 games each, `autopsy.py`; outputs `autopsy/an-h4-lightround` and `autopsy/an-h4-gplightround`). Each row's trips equal the evaluation run's on all 20 maps. Lights and roundabouts at the end are `lights_end` and `roundabouts_end` from the final state: 68 and 33 for `lightround`, 56 and 35 for `gplightround`, equal to the numbers placed, so none was removed.

| | `lightround` | `gplightround` |
|---|---|---|
| Mean trips (20 maps) | 217.9 | 223.1 |
| Games lost / reached the cap | 20 / 0 | 20 / 0 |
| Cause: car shortage | 8 | 9 |
| Cause: slow arrival | 6 | 4 |
| Cause: gridlock | 5 | 5 |
| Cause: unreachable cars | 0 | 2 |
| Cause: not connected | 1 | 0 |
| Road tiles left at the end (mean) | 52.1 | 43.5 |
| Lights / roundabouts at the end (mean) | 3.40 / 1.65 | 2.80 / 1.75 |
| Failing colour: cars (busy, home) | 20.9 (19.8, 1.1) | 23.4 (22.6, 0.8) |
| Failing colour: stuck share of driving cars | 0.51 | 0.59 |
| All colours: stuck share | 0.42 | 0.43 |
| Failing colour: stuck cars (within 3 tiles of the shop, heading to it) | 9.8 (7.0, 7.3) | 13.5 (9.0, 8.8) |

Queue heads of the failing colour's stuck cars (the cars not just queued behind another), summed over the 20 games: 183 for `lightround`, 263 for `gplightround`. A car stopped at a red light counts as stuck here.

| Held by | `lightround` | `gplightround` |
|---|---|---|
| Junction priority (approaching or crossing vehicle) | 82 (45%) | 144 (55%) |
| Traffic light | 37 (20%) | 36 (14%) |
| Roundabout (entry yield, or yield to circulating traffic) | 30 (16%) | 39 (15%) |
| Shop car-park gate | 33 (18%) | 43 (16%) |
| No obstacle reported (`none`) | 1 (<1%) | 1 (<1%) |

- **What differs from the earlier autopsy.** The earlier autopsy of the GP final (maps 3000–3019, not these) had car shortage 13, slow arrival 5, unreachable cars 2, no gridlock, 22.8 tiles left and about a third of the failing colour's cars stuck. Here, with both tools: gridlock in 5 of 20 games for each policy, 43.5–52.1 tiles left, and a stuck share of 0.51–0.59.
- **Tiles left.** The lost games ended with 52.1 (`lightround`) and 43.5 (`gplightround`) road tiles unused on average. The failing colour has nearly all its cars out (busy 19.8 of 20.9 and 22.6 of 23.4).
- **Stuck cars sit at junctions and shops.** Junction priority holds 45–55% of the queue heads and the shop's car-park gate 16–18%. Traffic lights and roundabouts hold 37% (`lightround`) and 29% (`gplightround`) of them.
- **Not compared.** No autopsy of `separated` or `gppkg` on 3100–3119 was run, so the autopsy does not say what the tools changed in the causes of loss.

**Verdict:** On LA 3100–3199 (100 maps, 900/900 replays verified, no placement rejected) traffic lights moved the mean by +3.9 [−14.0, +20.9] on the separated rule and +4.0 [−13.0, +21.4] on the GP rule's package version; both intervals include 0. Roundabouts moved it by −1.9 [−21.1, +17.3] and −28.2 [−48.3, −8.4] (worse on 54 maps, better on 36, Wilcoxon p 0.009). Both tools moved it by −7.8 [−29.3, +12.8] and −12.8 [−33.0, +7.1]. The package rule alone moved the GP rule by −0.3 [−10.0, +8.3]. Each placing-versus-base difference bundles three changes: the placements, the package choice, and the extra decisions from the placement trigger (a placing rule with stock also decides every 5 s while any car has waited 3 s). This test does not separate them. Means: `separated` 209.5, `light` 213.4, `round` 207.7, `lightround` 201.7; `gp` 250.3, `gppkg` 250.0, `gplight` 254.0, `gpround` 221.8, `gplightround` 237.2. Both-tool rules place about 5 tools per game and raise the mean car wait to 1.8–2.1 s from 0.6–0.7 s. All 40 autopsied both-tool games were lost (none reached the cap): car shortage 17, slow arrival 10, gridlock 10, unreachable cars 2, not connected 1. A 100-map test resolves about ±17–21 trips here, and each rule played each map once. The step-2 decision is the user's.

Files (git-ignored, under `output/evolved_rules/`): runs `runs/h4-*`, autopsies `autopsy/an-h4-*`, comparison script and tables `analysis/h4_compare.py`, `h4_compare.json`, `h4_compare.md`, run log `analysis/h4_runs.log`.

## 2026-11-07: gp-4 evolution (step 2), setup and generation 0

Plan: `plans/2026-11-07-gp4-step2-plan.md`. Code at `7152eb5` (branch `gp4`), `CODE_VERSION` `gp4-v2`, config recorded clean.

**Setup:** The gp-3.3 loop with a fifth tree, `place`, over the 15 `pl_*` placement inputs plus the global inputs. A 5-tree text places both tools when its place tree is not a constant ≤ 0, and it can learn to use one tool through `pl_is_light` / `pl_is_roundabout`.
- **Loop:** 64 rule sets, racing on 8 + 24 maps, a hall of fame of 8, probation, and the paired-t stop rule (gain ≥ max(3 trips, 2%), alpha 0.005, min 30 generations, patience 20).
- **Reference:** `final/gp3_final.txt`, with place −1.0.
- **Seeds:** gp-2's rule (`seeds/gp4/gp2.txt`, its never-clean copy) and the step-1 hand rules written as trees: `light`, `lightround`, `gplight` and `gplightround`. With the hand, separated and clean rules, generation 0 has 8 fixed texts and 56 random ones.
- **Code changes since step 1:** only driving cars count as near a spot, and only driving cars' waits fire the placement trigger, because the host never resets a parked car's wait.
- **Run settings:** 8 workers (the user's choice) and `--max-hours 120`. That is raised from 72, because convergence needs at least 50 generations.
- **Checks before launch:** a 2-generation smoke run (`gp4-smoke`) placed tools in 18 of 56 games, and a run resumed after generation 1 gave identical records (`gp4-smoke-r`).

Command:
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m evolved_rules.evolve --run gp-4 --workers 8 --max-hours 120 \
  --remove-tree --place-tree --hof 8 --reference evolved_rules/final/gp3_final.txt \
  --seed-text evolved_rules/seeds/gp4/gp2.txt --seed-text evolved_rules/seeds/gp4/light.txt \
  --seed-text evolved_rules/seeds/gp4/lightround.txt --seed-text evolved_rules/seeds/gp4/gplight.txt \
  --seed-text evolved_rules/seeds/gp4/gplightround.txt
```

**Generation 0** (1,102 games, 27.8 min):

| | Best on validation (1500–1549) | Average, all 64 rule sets (8 round-1 maps) |
|---|---|---|
| Generation 0 | 259.7 (`gplight` seed, `9c5940ad`) | 98.9 (median 119.8; the 56 random rule sets pull it down) |

Validated this generation (lights / roundabouts sent per game):

| Rule | Validation mean | Lights | Roundabouts |
|---|---|---|---|
| `gplight` seed | 259.7 | 4.76 | 0 |
| `gplightround` seed | 243.2 | 3.84 | 1.78 |
| Reference (gp3_final, place −1) | 238.0 | 0 | 0 |

- On the 32 training maps the reference averaged 240.1.
- The +21.7 of `gplight` over the reference is the best of three validated means, so it is biased upwards. On 3100–3199 the same rule was +4.0 [−13.0, +21.4] over its package-only version. The stop rule's paired test, and the final test on fresh maps, decide whether this holds.

## 2026-11-08: gp-4 evolution paused at generation 21 (simulator bug)

**Status: paused, not converged.** The user stopped the run on 2026-11-08 at 12:20 because a bug was found in the simulator. Fixing it is happening on another branch. Every number below comes from the **old simulator** (the host built from `gp4`'s `simulation/`, last changed at `5360118`). Treat them as provisional until they are re-run on the fixed one. Next steps: `plans/2026-11-08-after-simulator-fix.md`.

**Where it stopped:**
- Generations 0–21 are complete: 22,993 games in 12.6 h of wall time.
- Generation 22 was killed half way, and its games are lost.
- The checkpoint at `output/evolved_rules/evolve/gp-4/checkpoint.pkl` is from the end of generation 21. The run's `status.json` still says `running`, because the process was killed rather than stopped.
- **Do not `--resume` this run on a fixed simulator.** The game cache is keyed on (`CODE_VERSION`, text, seed, cap) and not on the simulator build. A resume would reuse games played on the old simulator, and so would the incumbent, the hall of fame and the validation scores.

**Every generation.** Best = the incumbent's validation mean (1500–1549, n = 50). Average = the mean of all 64 rule sets on that generation's 8 round-1 maps.

| Gen | Best on validation | Average, all 64 | Round-1 best | Newly validated (validation mean) | Minutes |
|---|---|---|---|---|---|
| 0 | 259.7 | 98.9 | 239.5 | `9c5940ad` 259.7, `19c396bd` 238.0, `b6100b46` 243.2 | 28 |
| 1 | 259.7 | 179.1 | 290.8 | – | 25 |
| 2 | 259.7 | 173.8 | 287.2 | `a30d7ab8` 232.1 | 31 |
| 3 | 259.7 | 190.8 | 284.6 | `9e46a6d8` 239.1 | 35 |
| 4 | 259.7 | 203.8 | 315.1 | – | 36 |
| 5 | 259.7 | 230.2 | 306.1 | – | 42 |
| 6 | 259.7 | 208.3 | 311.1 | `97326c56` 237.0 | 37 |
| 7 | 259.7 | 219.1 | 289.2 | `ed2428a0` 225.1, `4a1ed298` 235.0 | 41 |
| 8 | 259.7 | 211.1 | 336.0 | `1862fb95` 234.2 | 34 |
| 9 | 259.7 | 204.9 | 287.4 | – | 33 |
| 10 | 259.7 | 218.2 | 311.1 | `d8303498` 255.4 | 39 |
| 11 | 259.7 | 187.3 | 253.1 | `6db8c43d` 225.9 | 35 |
| 12 | 259.7 | 175.5 | 264.1 | – | 31 |
| 13 | 259.7 | 219.0 | 309.0 | – | 35 |
| 14 | 259.7 | 189.6 | 283.8 | `fed61277` 244.3 | 34 |
| 15 | 259.7 | 185.4 | 274.6 | – | 36 |
| 16 | 259.7 | 219.0 | 307.4 | – | 37 |
| 17 | 259.7 | 177.0 | 291.0 | `fc995843` 232.4 | 34 |
| 18 | 259.7 | 193.0 | 346.1 | – | 32 |
| 19 | 259.7 | 191.7 | 302.4 | – | 32 |
| 20 | 259.7 | 204.4 | 340.2 | – | 36 |
| 21 | 259.7 | 208.4 | 336.5 | – | 34 |

The incumbent never changed. It is the `gplight` seed `9c5940ad`: gp3_final's routes and hold, the lights package upgrade, and place `if_gt(pl_is_light, 0.5, pl_stopped_near, -1.0)`. After generation 21 there had been 21 generations without improvement, so the stop rule would have ended the run at generation 30 (about 16:30 on 2026-11-08).

**Every validated rule** (lights and roundabouts are commands sent per game, averaged over the 50 validation maps):

| Rule | Gen | Validation | Lights | Roundabouts | Place tree |
|---|---|---|---|---|---|
| `9c5940ad` (`gplight` seed, incumbent) | 0 | 259.7 | 4.76 | 0 | `if_gt(pl_is_light, 0.5, pl_stopped_near, -1.0)` |
| `d8303498` | 10 | 255.4 | 4.52 | 0 | `if_gt(pl_is_light, 0.5, 0.5, -1.0)` |
| `fed61277` | 14 | 244.3 | 3.48 | 0.58 | `if_gt(pl_is_light, 0.5, pl_stopped_near, 0.72)` |
| `b6100b46` (`gplightround` seed) | 0 | 243.2 | 3.84 | 1.78 | `if_gt(mul(pl_joins_separated, pl_is_roundabout), 0.5, -1.0, pl_stopped_near)` |
| `9e46a6d8` | 3 | 239.1 | 0 | 0 | `-1.0` |
| `19c396bd` (reference, gp3_final) | 0 | 238.0 | 0 | 0 | `-1.0` |
| `97326c56` | 6 | 237.0 | 4.36 | 0 | `if_gt(pl_is_light, 0.5, pl_stopped_near, -1.0)` |
| `4a1ed298` | 7 | 235.0 | 4.04 | 0 | `if_gt(pl_is_light, 0.5, pl_is_light, -1.0)` |
| `1862fb95` | 8 | 234.2 | 4.20 | 0 | `if_gt(pl_is_light, 0.5, pl_is_light, -1.0)` |
| `fc995843` | 17 | 232.4 | 0 | 0 | `if_gt(pl_is_light, pl_is_light, …)` (never places) |
| `a30d7ab8` | 2 | 232.1 | 4.04 | 0 | `if_gt(pl_is_light, 0.5, pl_stopped_near, -1.0)` |
| `6db8c43d` | 11 | 225.9 | 4.18 | 0 | `if_gt(pl_is_light, 0.5, pl_stopped_near, -1.0)` |
| `ed2428a0` | 7 | 225.1 | 3.68 | 0 | `if_gt(pl_is_light, 0.5, pl_cars_near, -1.0)` |

**Hall of fame after generation 21** (per-map difference from the reference on training maps; lcb = mean − SE):

| Rule | Maps | Mean diff | lcb |
|---|---|---|---|
| `9c5940ad` (incumbent) | 508 | +7.1 | +3.6 |
| `a30d7ab8` | 486 | +5.0 | −0.5 |
| `02fe0b60` | 290 | +1.2 | −2.9 |
| 4 more evolved rules | 84–167 | −15.9 to −1.4 | all < 0 |

**Provisional reading (old simulator):**
- **Lights help a little.** The incumbent is +7.1 (lcb +3.6) over the same rule without placement across 508 training maps, and +21.8 on validation (t 2.36 against 2.68 needed at alpha 0.005, so not significant).
- **Roundabouts do not help.** Only two validated rules placed any. Both were below the incumbent.
- **Evolution did not improve on the hand-written placement rule.**
  - The population churned without climbing. From generation 3 on, the average stayed between 175 and 230 with no trend.
  - Every evolved rule that led on the racing maps lost on validation, the same pattern as gp-3.3.

## 2026-11-09: gp-4 closed, superseded by gp-5 on simulator 2026-11-08.6

gp-4 stays stopped at generation 21 (entry above) and is **not** resumed. Its run folder's `status.json` now says `stopped`.
- **What replaces it:** gp-5, a fresh run with the same setup on the repaired simulator. That is `mohammad` at `1fb8f0a`, `simulatorVersion` `2026-11-08.6`, documented in `simulation/Docs/HANDOFF-2026-11-sim-fix.md` on that branch.
- **Results now valid for the old simulator only:** gp-4's 22 generations, incumbent, hall of fame and validation scores, and every earlier result in this log.
  - All of them were played on the engine `gp4` carried, which matches `e6119eb` (28 October).
  - The new simulator changes car speed, construction prices, demand timing, parking, junction arbitration and traffic lights.
- **Not run for gp-4:** its CMA-ES control, final selection, test and PPO head-to-head (the gp-4 design's steps 3–4).

**A first look at the new simulator** (simulator session's measurements and our 30 `sim2-*` games; GP final rule, LA 3100–3109, deterministic, replays not verified):

| Simulator | gp3_final with lights (`gplight:`) | gp3_final without lights (`tree:`) | Separated |
|---|---|---|---|
| Old (e6119eb, the `h4-*` runs) | 309.2 | 293.3 | 257.4 |
| 2026-11-08.4 | 408.4 | 513.2 | 449.5 |
| 2026-11-08.5 | 510.5 | 513.2 | – |
| 2026-11-08.6 | 529.7 | 535.5 | – |

The 105-trip loss with lights on `.4` came from stuck traffic lights, which `.5` fixes. On `.6` the hand light rule still loses on 6 of 10 maps. In gp-5 the evolved place and upgrade trees decide light use.

## 2026-11-09: Round A, the existing rules on simulator 2026-11-08.7

**Setup:** code at `4d73f0b` on `gp4`, with `main` 8025a60 merged. `CODE_VERSION` `gp5-v1`, cache keyed on `simulatorVersion`.
- 1,563 games, every replay verified (1,563/1,563), run by `output/evolved_rules/analysis/round-a.sh` in 2 h 43 min on 8 workers.
- Each run repeats an old one with the same policy and maps, with `-s2` added to its name.
- The PPO head-to-head was skipped, because PPO needs retraining first. Tables come from `output/evolved_rules/analysis/round-a-compare.py`.

| Rule | Maps | Old simulator | Simulator .7 (median) | New − old [95% CI] | Lights/game |
|---|---|---|---|---|---|
| Do nothing | 1000, 2000–2019 | 0.0 | 0.6 (0) | +0.6 | 0 |
| Hand | 1000, 2000–2019 | 149.1 | 351.1 (347) | +202.0 [+146.9, +272.4] | 0 |
| Separated | 1000, 2000–2019 | 241.0 | 485.0 (499) | +243.9 [+169.2, +311.1] | 0 |
| Hand | validation | 153.1 | 388.1 (384) | +235.0 [+195.6, +274.2] | 0 |
| Separated | validation | 187.5 | 457.8 (465) | +270.3 [+234.2, +305.1] | 0 |
| GP final (gp3_final) | validation | 238.0 | 488.0 (481) | – | 0 |
| gp-4 incumbent (`gplight` seed) | validation | 259.7 | 510.2 (508) | – | 5.48 |
| GP final | test 7000–7099 | 245.9 | 470.8 (490) | +224.9 [+194.6, +252.7] | 0 |
| CMA-ES final | test | 250.6 | 477.7 (478) | +227.1 [+199.9, +251.0] | 0 |
| Separated | test | 216.3 | 474.9 (486) | +258.6 [+231.3, +284.8] | 0 |
| Hand | test | 170.8 | 364.8 (368) | +194.1 [+171.2, +217.7] | 0 |
| separated | 3100–3199 | 209.5 | 459.2 (460) | +249.7 [+222.8, +276.8] | 0 |
| light | 3100–3199 | 213.4 | 480.3 (478) | +266.9 [+237.1, +294.1] | 5.06 |
| round | 3100–3199 | 207.7 | 406.9 (418) | +199.2 [+171.3, +228.0] | 0 |
| lightround | 3100–3199 | 201.7 | 424.2 (430) | +222.5 [+191.2, +253.5] | 3.70 |
| gp (tree) | 3100–3199 | 250.3 | 483.3 (491) | +233.0 [+201.9, +261.7] | 0 |
| gppkg | 3100–3199 | 250.0 | 493.0 (490) | +242.9 [+214.7, +268.6] | 0 |
| gplight | 3100–3199 | 254.0 | 513.5 (528) | +259.5 [+231.8, +286.5] | 5.20 |
| gpround | 3100–3199 | 221.8 | 450.4 (452) | +228.7 [+201.5, +255.2] | 0 |
| gplightround | 3100–3199 | 237.2 | 465.5 (475) | +228.3 [+195.4, +258.6] | 4.00 |

Every rule gains about 200–270 trips. The simple rules gain the most: separated gains 250–270, the GP and CMA-ES finals about 225.

**Gaps between rules (paired by map):**

| Gap | Old simulator | Simulator .7 |
|---|---|---|
| GP final − separated, test | +29.6 [+9.9, +49.5] | **−4.1 [−29.4, +19.9]** |
| GP final − hand, test | +75.1 [+54.8, +95.5] | +106.0 [+81.2, +130.6] |
| GP final − CMA-ES final, test | −4.7 [−22.9, +13.1] | −6.9 [−31.6, +15.7] |
| Separated − hand, test | +45.5 [+24.0, +67.3] | +110.0 [+87.3, +131.4] |
| gp − separated, 3100–3199 | +40.7 [+18.5, +66.3] | +24.0 [+0.3, +48.3] |
| gplight − gppkg (lights), 3100–3199 | +4.0 [−13.0, +21.4] | +20.6 [−1.1, +43.2] |
| gpround − gppkg (roundabouts), 3100–3199 | −28.2 [−48.3, −8.4] | −42.5 [−68.7, −20.7] |
| light − separated, 3100–3199 | +3.9 [−14.0, +20.9] | +21.1 [+4.2, +36.6] |
| gp-4 incumbent − GP final, validation | +21.8 (unpaired) | +22.2 [−17.1, +55.8] |

**Decision gate (criteria set before the results):**
1. The ranking GP final > separated > hand holds on the test maps, with paired intervals above zero. **Fails.** Separated still beats hand, by more than before. But the GP final no longer beats separated on the test maps (−4.1), though it still does on 3100–3199 (+24.0, lower bound +0.3).
2. Lights do not hurt on 3100–3199. **Passes:** lights now help, +20.6 with GP and +21.1 with the separated rule. Roundabouts still hurt (−42.5).

**Reading:** the old simulator's evolved advantage over the simple separated rule mostly does not carry over. The GP final and CMA-ES final were evolved and chosen on the old simulator, so re-evolving on the new one is the remedy, and gp-5 is that re-evolution. Per the plan, the user decides before a run of a day or more.

## 2026-11-09: gp-5 paused at generation 4 (simulator .7)

gp-5 is gp-4's setup on simulator .7 (`gp5-v1`). It completed generations 0–3 and was paused by the user on 2026-11-09 at 15:30, during generation 4. It is not resumed: it is superseded by gp-6 on simulator f34 (below).

| Gen | Best on validation (1500–1549) | Average, all 64 (8 round-1 maps) | Round-1 best |
|---|---|---|---|
| 0 | 510.2 (`gplight` seed `9c5940ad`) | 261.0 | 510.9 |
| 1 | 510.2 | 341.4 | 561.1 |
| 2 | 510.2 | 383.8 | 558.5 |
| 3 | 510.2 | 400.2 | 548.0 |

The incumbent never changed, so gp-5's best rule is gp-4's. The racing best of generation 3 (`01e8a18f`) was never validated.

## 2026-11-12: every version on simulator f34 (upstream main 938b9f8)

**Setup:** simulator `2026-11-10.f34`, a clean `git archive upstream/main simulation` build. The gp4 code (`gp5-v1` agent) was played through `EVOLVED_RULES_HOST_DLL`, on LA 7000–7099, with 100 games per rule.
- 900/900 replays pass `--verify-replay` on the same f34 build. The pinned verifier was still .7, so `--verify` was off and the replays were verified afterwards.
- Files: `output/evolved_rules/analysis/f34-eval/` (`run.py`, `compare.py`, `results.md`, `verify.txt`); runs in `runs/f34-*`.
- These are fixed rules, not populations, so there is no average column.

| Rule | Old sim, test | Sim .7, test | **f34, test** [95% CI] | f34 median | Rejected draws/game |
|---|---|---|---|---|---|
| gp-1 best `36fc30a3` | – | – | **710.6** [662.6, 759.8] | 705 | 3.8 |
| gp-2 best `7dea530b` (= gp-3.1 best) | – | – | **811.3** [738.9, 881.6] | 860 | 6.4 |
| gp-3.3 best `4f9e0cba` (identical games to gp-2) | – | – | **811.3** | 860 | 6.4 |
| gp-3 final `209634e8` | 245.9 | 470.8 | **831.9** [760.4, 904.2] | 824 | 7.8 |
| gp-4 best `9c5940ad` (= gp-5 best) | – | – | **840.6** [760.1, 920.1] | 878 | 8.7 |
| gp-5 gen-3 racing best `01e8a18f` | – | – | **659.8** [604.3, 725.0] | 640 | 7.4 |
| CMA-ES final `fa7648c7` | 250.6 | 477.7 | **981.3** [909.5, 1047.9] | 1016 | 5.1 |
| Separated | 216.3 | 474.9 | **733.3** [669.9, 793.3] | 764 | 3.8 |
| Hand | 170.8 | 364.8 | **524.0** [489.4, 560.5] | 498 | 3.7 |

**Paired gaps on f34:**
- gp-4 − separated +107.3 [+7.8, +206.0]
- gp-3 final − separated +98.5 [−0.5, +196.7]
- CMA-ES − separated +248.0 [+154.5, +339.0]
- CMA-ES − gp-3 final +149.5 [+54.1, +235.9]
- gp-4 − gp-3 final +8.7 [−95.4, +109.0]
- separated − hand +209.3 [+134.9, +276.9]

**Reading:**
- Scores roughly double again (gp-3 final: 246 → 471 → 832).
- The GP rules lead separated again, by about +80 to +107.
- The old-simulator CMA-ES weights are the best rule on f34, by about 150 trips.

**Rejected draws:** every rule loses 4–9 draws per game on f34 (0 on .7). The messages are "Bridge requires an available bridge" and "No road tiles remaining for this connection". The planner still used the old cost rules:
- f34 charges road stock per new link between two non-building cells (`MaterialInventory.RoadConnectionCost`), not per new tile;
- a step from land onto unbuilt water always starts a crossing (`bridgeFrom`), even next to an existing bridge;
- a water tile holds at most two roads (`WaterLinkViolation`).

## 2026-11-12: gp-6 and cma-6 on simulator f34

**Planner fix** (`94c9f18`, branch `gp6` off `gp4`, simulator copied from upstream main in `b96d98d`; `CODE_VERSION` `gp6-v1`):
- the A* and the executor count paid links, crossings and water degree as f34 does;
- `tiles_needed` is now the road stock a route spends.

On LA 7000–7011 the gp-4 rule goes from 811.6 to 965.2 trips with 0 rejected draws (before: up to 30 per game). Its two collapsed games, 119 and 212 trips, become 844 and 1048.

`0d0cb20` fixes the host-version pattern, which rejected `2026-11-10.f34` and made the engine refuse every game.

**Budget (user, 2026-11-12):**
- Both runs go to at least 30 generations. If not converged, they continue under the stop rule (patience 20, gain ≥ max(3 trips, 2%), paired t at α 0.005), with a 72 h backstop.
- The user chose moderate settings over gp-5's, because an f34 game takes about 3× longer (about 450 games per hour on 12 workers).

| | gp-6 (GP) | cma-6 (CMA-ES) |
|---|---|---|
| Rule sets per generation | 32 | 16 |
| Maps | 8 each; top 8 play 8 more | 8 each |
| Validation | top 2 on 1500–1549 | best on 1500–1549 |
| Trees | priority, hold, upgrade, remove, place | linear priority, hold, upgrade (81 weights) |
| Start | hand, separated, clean + `seeds/gp6/`: gp-4 best, gp-3 final, CMA-ES final, gp-2; 4 immigrants; hall of fame 4 | `--x0 cma1` (cma-1's final weights) |
| Reference (hall of fame) | CMA-ES final | – |
| Workers | 8 | 4 |

**Commands** (run by the watchdog):

```
python -m evolved_rules.evolve --run gp-6 --workers 8 --pop 32 --first-seeds 8 --more-seeds 8 --racing-top 8 \
  --validate-top 2 --immigrants 4 --hof 4 --max-hours 72 --remove-tree --place-tree \
  --reference evolved_rules/seeds/gp6/cma1_final.txt --seed-text evolved_rules/seeds/gp6/gp4_best.txt \
  --seed-text evolved_rules/seeds/gp6/gp3_final.txt --seed-text evolved_rules/seeds/gp6/cma1_final.txt \
  --seed-text evolved_rules/seeds/gp6/gp2.txt
python -m evolved_rules.tune_cmaes --run cma-6 --workers 4 --x0 cma1 --max-hours 72
```

**Watchdog:** the scheduled task `gp6-watchdog` runs `output/evolved_rules/analysis/gp6/watchdog.ps1` every 10 minutes and at logon.
- A run with no live process whose status is not `converged`, `budget` or `stopped` is restarted, with `--resume` once a checkpoint exists.
- It stops restarting after 4 restarts in 2 hours.
- Log: `analysis/gp6/watchdog.log`; run logs `analysis/gp-6.{log,err}` and `analysis/cma-6.{log,err}`.

Launched 2026-11-12 at 23:06.
