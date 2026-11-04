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
