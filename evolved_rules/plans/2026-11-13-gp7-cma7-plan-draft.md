# Draft plan: gp-7 and cma-7, and closing gp-6/cma-6

> **Superseded on 2026-11-14 by `2026-11-14-gp7-cma7-plan.md` (the operative plan).** Read this draft as background only: diagnosis, evidence and design reasoning. Where the two differ, the operative plan wins. Its timeline, budgets, stop rule and the full-size gp-7 are replaced there.


**Revision of 2026-11-14 (the user's decision): the planner becomes evolvable.**
- The planner keeps only neutral tools: A* search, legality and stock checks, and connectivity queries.
- Its hand-made choices become learned parameters in **both** learners:
  - **how routes are shaped:** an evolved route-cost head that sets A*'s step cost;
  - **which pairs get routes:** an evolved target head that may also pick already-connected pairs, so bypasses and shortcuts can emerge.
- The hand-coded fast, bypass and relief kinds, the ttf trigger and the 60 s failed-pair memory are **removed** (old C4(a)–(c), (e), (f)). Fast and bypass survive only as hand-set **points** in the evolved parameter space, screened in C5 as possible starting points.
- **New routes are on from the start.** The training start x0 already proposes and builds some evolved routes, at a low rate (§2.5 P4). Exact reproduction of today's planner is kept as a code test ("off" setting) and as the "legacy x0" comparison row. See §2.5. A planner-free (raw tile action) baseline was considered and **dropped** by the user.
- **In a test game nothing learns.** Formulas, slot trees and planner weights are frozen. Behaviour still changes within a game, because their inputs (traffic per cell, ttf, game time) change.

**What changed from the draft after the red-team review.** I accepted most of the red-team issues and rebuilt the parts they hit:
- The per-generation map count is now fixed, so the budget and the stop rule fit together again.
- The stop rule is now a paired per-map slope test. I simulated it again under realistic noise.
- GP's structure step now tests each proposal in games before inserting it, and slots are freed by a statistic whose null distribution is known.
- The GP claim now has two primary tests: a large GP-vs-CMA test and a close-relative ablation.
- The "−42 sample loss" claim is gone.
- Every schedule now uses the measured **300 games/h**.
- The text format gets a `flags:` line.
- The hand screens are one-factor contrasts on 300 maps, with the existing clean mode as a comparator.
- CRN moves to gp-8 by default.
- The motorway question goes to the user on day 0.

The issues I did not adopt are listed, with reasons, in the appendix.

**What I checked myself (read-only):**
- **Throughput.** From generations.jsonl: cma-6 gens 1–9 took 36–49 s of wall time per game on 4 workers, i.e. 145–200 s per game per worker. gp-6 gens 6–11 took 15–25 s per game on 8 workers, i.e. 120–200 s per game per worker, crash downtime included. At x0 quality, 12 workers give about **300 games/h**. The draft's 450/h is wrong.
- **Clean routes and placement are fixed by the tree count.** `gp.py:442` sets `clean_routes = trees >= 4`. `gp.py:444` sets `places_lights = places_roundabouts = trees == 5`. Engine and evaluate build `TreePolicy(text)` with no flags (`engine.py:128,142`, `evaluate.py:132`).
- **`--verify-replay` does not check scores.** It prints PASS with the replayed score and never compares it with the recording (`simulation/Headless/Program.cs:64-75`).
- **`DemandTracker` has no delivery rate.** It records only positive increases in demand (`features.py:59-99`).
- **Depth limit.** `gp.py:205` has `MAX_DEPTH = 6`, and taller trees revert at lines 482, 499 and 537.
- **`pl_is_light` exists** (`gp.py:74`), so light-only placement can be written in-tree.
- **Run status at 22:18 on 2026-11-13.** gp-6 had 12 generations done and cma-6 had 10. At about 2 h per generation, gp-6 reaches 15 around 04:00–07:00 on Nov 14 and cma-6 around 07:00–11:00.
- **New stop-rule simulation:** `evolved_rules/analysis/gp7/stop7.py` and `evolved_rules/analysis/gp7/stop7b.py` (archive; the stop rule is cut in the operative plan).

---

## 1. Diagnosis: four root causes

**R1. The move set sets the ceiling, not the formulas.**
- **Score is survival time.** trips ≈ 1.283e-4·T^2.18, with R² 0.985–0.995.
- **Every rule earns trips at the same rate while alive.** cma-1, gp-4, the separated rule and the hand rule all reach 47/175/~377/~686 trips at 300/600/900/1200 s.
- **Every rule dies at a shared wall at 1400–1600 s.** The risk of dying within 200 s there is 0.70–0.93.
- **Early deaths are not the problem.** Removing every death before 1200 s is worth about +4.5 trips.
- **Surviving longer at the wall is worth a lot.** +100/+200/+300 s at the wall is worth about +146/+315/+496 trips.
- **Road tiles are not the limit.** Games end with 66–95 tiles unused.
- **There is no move that shortens an already-connected route.**
  - `coverage_targets` only proposes unconnected pairs (candidates.py:548-576).
  - A* discounts existing road to 0.15 (candidates.py:26), so traffic funnels onto shared trunks.
- **Choosing among today's candidates is saturated.**
  - The 29-node gp-6 rule ties the 321-node cma-1: 1019.5 vs 1027.7.
  - The true spread among cma-1 relatives is about 23 trips.
- **The only large f34 gain came from a planner fix** (+154 trips on 12 maps).

**R2. Chaos turns most decisions into noise, and selection follows the noise.**
- **One random stream drives everything.** `SimulationRandom` (TrafficWorld.cs:76) serves:
  - parking picks (ContinuousJourneys.cs:44, TrafficControl.cs:648);
  - placement draws, which depend on which tiles hold roads (OriginalPlacement.cs:118, 205).
- **Same-map pairing barely helps for unrelated rules.** They correlate per map at r ≈ 0.09–0.26, with a paired-difference SD of 370–530. Close relatives reach r ≈ 0.55–0.7, with a paired SD of about 230–300.
- **Rankings are mostly noise:**
  - GP: 8-map reliability among decent rules is 0.28.
  - CMA: cma-6 split-half reliability is about 0 from gen 5, with F = 0.69.
- **Winner's curse:**
  - gp-6 hall-of-fame leads of +221 and +247 fell to −8 and −94 on validation.
  - cma-6 best samples lost 99.5 trips from training to validation.
  - cma-6's 1037 incumbent shrinks to about 1006 under empirical Bayes.
- **The stop rule has almost no power:** 4–14% for a true +30 to +50. No GP run has ever reached it.

**R3. Both learners are mis-built, and the comparison was unfair.**
- **GP:**
  - cma-1's priority tree has height 7, above MAX_DEPTH 6, so 99.8% of its mutations revert. The strongest seed was frozen.
  - Constants are redrawn, not stepped: the mean jump is 1.11 against a mean |w| of 0.59.
  - 40% of mutations hit the constant remove and place trees.
  - Random immigrants never reached the racing top (0 of 38).
- **CMA:**
  - 34 of its 81 weights are dead or redundant (agent.py:117-123, 193-214).
  - Term scales differ by about 100×.
  - The covariance learned nothing (condition number 1.17), and the mean drifted like a random walk (6.44 against 5.8 for pure noise).
  - It promotes the best sample.
- **Comparison:**
  - CMA had no light head.
  - gp-6 played 2.4× as many games as cma-6.
  - cma-1's 1027.7 was played with clean routes on, cma-6 with them off.

**R4. Throughput and operations.**
- About **300 games/h** at x0 quality.
- The C# hosts use about 81% of busy CPU, and some of it is provably dead work (TrafficControl.cs:344-348).
- Per-game cost grows roughly with trips^1.9.
- On 2026-11-13: 13 watchdog restarts and a 7 h gap.

---

## 2. Pre-work before any long run

**Ground rules:**
- All work goes in a new worktree `C:\Projects\490 - Project\mm-gp7` on branch `gp7`, created from the gp6 tip.
- Branch gp6 stays untouched until both runs show `budget`.
- Commits use the user's identity, with no attribution lines and no push.
- State the game count before any run of more than 20 games.
- All game costs below assume 300 games/h. Speedups count only once C2 has measured them.

### Critical path

| # | Item | Effort | Games (h at 300/h) | Go / no-go check |
|---|---|---|---|---|
| **C0** | **Close out gp-6/cma-6** (§2.1) | 0.5 day | 1,400 (≈4 h) | Always done |
| **C1** | **Operations hardening.** AC power. The user runs `powercfg /change standby-timeout-ac 0`, `powercfg /change hibernate-timeout-ac 0`, `powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0` and `powercfg /setactive SCHEME_CURRENT`. New scheduled task `gp7-watchdog` (copy of watchdog.ps1: `--resume` only, restart cap 8 per 2 h, leaves `budget` and `converged` alone). Keep the 120 s host and 3600 s awake-game timeouts. At most 12 workers in total. Every run logs wall s/game per generation, plus suspends. | 1 h | runs inside C0 | **Test with the lid closed under the full 12-worker C0 load for 2 h:** no suspend in the logs, and s/game within 15% of an open-lid stretch. If it fails (throttling), the laptop runs open-lid and docked. |
| **C2** | **Profiling and two safe speedups.** (a) Wrap TrafficControl.cs:344-348 in a not-OriginalReference check (the values are unused on that branch, line 350). (b) Memoise `route_candidates`. The key is (network key, `state.infra.tobytes()`, roundabout ring, inventory[0:2], house id, target shop ids, clean, planned, planned_links), or the memo lives within one decision call only. **Harness first:** `replay_check.py` runs `--verify-replay` on all 902 `runs/f34-*/replays` and asserts printed score == recording.score, seconds == duration and commands == len(actions). The simulator alone does not compare them. Build the patched DLL only in mm-gp7's own `bin` folder and point `EVOLVED_RULES_HOST_DLL` at it (host.py:52-57), so the running hosts never see it. Profile 20 replays and run `dotnet-trace` on one ~1,900 s game. Offer (a) upstream to Mohammad as a pure performance PR. | 1.5 days | replays (≈1 h, sim only) + 40 games | (a) is accepted only if the harness passes on all 902 files. (b) is accepted only if 20 games each of cma-1 **and 7fa4b2** (which places lights and builds bridges) give identical command streams with and without the memo. Throughput is re-measured on a fixed 60-game benchmark. |
| **C3** | **Wall autopsy and decision bank.** Extend `autopsy.py`, which parses the per-vehicle `Obstacle` field in the autopsy only; it is not exposed to learners (PLAN decision 7). Play x0 (cma-1 3-tree and 5-tree) and 7fa4b2, 40 games on 3600-3639. Every 10 s, per shop, log: demand, reserved, overcrowded_for, its colour's cars by stage, per-car journey time against free-flow route cost (tracked across observations), stopped car-seconds split into junction, car-park gate and driving, coverage-target count, and tiles left. 20 more games on 3640-3659 record the **decision bank**: every decision's candidate feature matrix, globals, offers and light spots **and the full observation**, tagged with seconds to failure (about 2.5–5k situations). From the bank, compute each term's spread within a decision: across candidates, across decisions, across offers and across spots. | 1–1.5 days | 60 (≈0.3 h) | Decides which moves C4 builds first (gate G1). Every live v6 term must have finite, non-zero spread. |
| **C4** | **Planner v7: the evolvable planner (§2.5) plus features**, behind `moves=v6|v7`; v6 stays byte-identical. (a) **Route-cost head:** A* takes its step cost from a weight vector plus an optional per-decision **cell-cost map**. Today's three cost models are expressed exactly as weight vectors. (b) **Target head:** scores every (house, same-colour shop) pair, connected or not. Its top M_eff ≤ 6 pairs with score > 0 (M_eff learned) get evolved-head routes on top of `coverage_targets`; no-op guards (§2.5 P2). (c) **Per-cell traffic maps** (cars and stopped cars per tile, from `state.cars`) and pair features (`pair_connected`, `detour_ratio`, `pair_failed_recent`), rebuilt with numpy at the start of each route pass that follows an executed route. (d) **Stress features:** per-shop margin (`margins()` split by catchment), `colour_busy_share`, `colour_idle_cars`, per-shop `ttf`; globals `demand_ramp` and `worst_ttf_inv`; candidate feature `target_ttf_inv`. ttf needs a **new per-shop pickup estimator** from demand decreases plus car-stage transitions; the current tracker only counts increases. Fallback stress features: `overcrowded_for` and demand per same-colour house. (e) **Light-only place head**, written in-tree as `if_gt(pl_is_light, 0.5, <linear>, -1)` so roundabout spots never score above 0. Removal stays off (remove tree = −1). (f) **`flags:` line** in the canonical text (`flags: clean=0|1`), parsed by TreePolicy, plus a `planner:` block with the cost and target weights and slot trees. Both are part of the text, so both enter the cache key; texts without them behave as before. `CODE_VERSION = "gp7-v1"`. **Removed from the earlier draft:** fast/bypass/relief kinds, the ttf trigger, failed-pair memory. | 4.5–5 days | 80 | Unit tests pass. **Identity tests:** (1) moves off: 20 games reproduce the gp6-v1 cache exactly (trips, seconds, command counts); (2) 3-tree cma-1 vs 5-tree `flags: clean=0` + remove −1 + place −1: identical games on 8 maps; (3) **planner "off" setting** (cost head = the separated vector, M_eff = 0, all slots 0): identical games to (1) on 20 maps, and on 500 bank states the cost-head A* returns the same path as `_astar(separated=True)`, plus a unit check that every edge cost is bit-identical to candidates.py:381-398 for all 8 directions × paid × junction × foreign. **Then re-record the bank under gp7-v1** (20 games on 3640-3659, observations and tracker state kept) for §3.3 and §4.2 calibration; (4) ttf: Spearman ≥ 0.5 against actual time to failure in the last 300 s on C3 data, else the fallback features replace ttf. **Smoke:** 24 games with the C5 "fast + bypass" point, 0 rejected draws, Python time per game up ≤ 35% (§2.5 cost caps). |
| **C5** | **Hand screens** (§2.2) | 0.5 day | 2,400 (≈8 h) | x0 rules in §2.2 |
| **C5m** | **Motorway prototype, only if the user approves on day 0.** It runs in parallel with C6 and is on the critical path (§2.3). | 3–4 days | 900 (≈3 h) | §2.3 |
| **C6** | **Learner code:** `linear.py`, `sepcma.py`, `slots.py`, `bank.py`, `evolve7.py`, `stats7.py`, plus the `gp.py` fixes (§9) | 4 days | 16 | cma-1 converted to live coordinates gives identical decisions on 100% of bank situations and identical trips on 8 maps. sepcma matches pycma `CMA_diagonal=True` within ±20% median evaluations on noiseless sphere, ellipsoid and linear functions (n = 70). 20k slot-tree mutations revert < 1%. |
| **C7** | **Mock evaluator, then real smoke runs.** The mock produces synthetic trips with policy SD 22–54, interaction SD 250–330, map SD 110 and collapse rate 5–20%. It checks the budget per generation, the stop-rule firing rates against §5.4, σ under mirroring with pairwise selection, the structure race, and exact kill/resume. The real smoke run does 2 generations per arm at λ = 6 and 4 maps, plus one structure race at 4+4 maps, with a forced kill and `--resume`. | 1 day | ≈300 (1 h) | Records after resume are byte-identical. Cost per generation within ±10% of design. Seeds ≥ 10000 behave normally. If more than 20% of gen-0 candidates are cut at σ0, halve σ0. **Planner gates (§2.5 P7):** ≥ 25% of gen-0 samples build new routes in ≥ 2% of bank situations; the mock reaches a planted two-coordinate planner optimum within 20 generations. |
| **C8** | **Pre-registration** `plans/2026-11-xx-gp7-cma7.md`: seed table, stop rule, budgets, inclusion rules, hypotheses, test sizes, the concurrency deviation, and the user's decisions | 2 h | 0 | The user signs off before launch |

**Side tracks (they never block launch):**
- **S1, CRN keyed-stream flag.** Moves to **gp-8 by default** (§2.4).
- **S2, deeper C# speedups:**
  - leader search indexed by lane key (TrafficControl.cs:372-390, same visiting order);
  - skip FinishRemovals when nothing is pending (TrafficWorld.cs:354-375);
  - lazy `DisconnectedColorComponents` (TrafficWorld.cs:415).

  Only if C2's profile shows them hot, they pass `replay_check.py` on all 902 files, and they are ready at launch. Never swapped in mid-run.
- **S4, LLM proposer.** Off unless the user consents.

### 2.1 Closing gp-6 and cma-6 (C0)

1. **Let both runs end.** Both reach max_gens 15 and end with status `budget` (evolve.py:415-416). The watchdog leaves `budget` runs alone. Disable `gp6-watchdog` once both have stopped, and never resume either run.
2. **Start the battery early.** As soon as gp-6 stops, start the battery on its 8 freed workers. cma-6 keeps its 4, then the battery takes all 12. It runs from the gp6 checkout with gp6-v1 code, which is unchanged.
3. **Battery on 5100-5299** (n = 200, never played), 7 policies:
   - cma-1 5-tree (clean on; the gp-6 incumbent);
   - cma-1 3-tree (clean off);
   - cma-6 final distribution mean (`es.mean` from the checkpoint, as a 3-tree text);
   - cma-6 incumbent 3d999a2c;
   - 7fa4b2 (29 nodes);
   - hand;
   - separated.

   1,400 games, about 4 h.
4. **Analysis:**
   - Paired differences against cma-1 5-tree for all **6** comparisons (BCa, paired-t, Wilcoxon), Holm over 6.
   - Map / interaction / policy ANOVA under the fixed planner. This answers whether unrelated rules correlate better with the fixed planner.
   - **Clean-routes default:** x0 keeps clean **off** unless (5-tree − 3-tree) > +1 SE (about +21).
5. **EXPERIMENTS.md entry.** Every generation with the validated best next to the population average, labelled **budget, not converged**. It states:
   - gp-6 played 2.4× cma-6's games (the matched-games view is gp-6 at about gen 4–5 against cma-6 at gen 15);
   - the gp-6 incumbent was the cma-1 seed throughout;
   - cma-6's 1037 is a best-of-10 (empirical Bayes about 1006);
   - the MAX_DEPTH bug;
   - the clean-routes mismatch.
6. **Legacy row.** The close-out policy with the highest empirical-Bayes estimate becomes the gp-7 test battery's legacy row. No separate test is run.

### 2.2 Hand screens (C5): headroom and starting points, not code inclusion

With the evolvable planner, nothing is hard-coded, so the screens no longer decide which code goes in. The cost head, target head, light head and stress features are **always** in both learners, starting from the "new routes on, gently" x0 of §2.5 P4. The screens answer two other questions:
- **Is there headroom in the new space?** This is gate G3 and the honest expectation given to the user.
- **Should x0 move to a better hand-set point?**

**The points tested** (each is just a weight vector in the §2.5 heads; every variant uses cma-1 rule weights under gp7-v1, with the clean setting from C0):
- **V0:** legacy (today's planner, heads off).
- **Gentle:** the §2.5 P4 start point (new routes on at a low rate).
- **Clean:** V0 + clean on. This is the comparator: a new route shape must beat what already exists.
- **Fast:** cost head with no reuse discount (`w_reuse = w_paid`), turns +0.5, any junction link +1.0, and the same targets. Priority gets +α·`is_evo`.
- **Bypass:** target head w_con = 5, b_t = −5 − c, template slot `mul(shop_ttf_inv, detour_ratio)` at v_10 > 0, n_t = 3, with c chosen on the bank to admit roughly the pairs with detour ≥ 1.33 and ttf < 300 s; Fast cost head. (Written in the shared coordinates so it can become x0 in both arms.) Priority gets +α·`is_evo`·(1 + 3·`seconds_saved`/30).
- **Jam-avoid:** cost head adds +0.5 per stopped car on a tile, plus +0.1 per moving car.
- **Lights:** `if_gt(pl_is_light, .5, pl_stopped_near, −1)`, plus an upgrade bonus of +0.8 on light offers.
- **All-on:** Bypass + Jam-avoid + Lights.

**Round 1 (exploratory, used only to pick α).** 3200-3299, n = 100, 10 variants, 1,000 games:
- V0, Gentle, Clean and Lights;
- Fast at α ∈ {0.5, 1, 2};
- Bypass and Jam-avoid at the best Fast α;
- All-on.

**Round 2 (deciding).** 3300-3599, n = 300, 5 variants, 1,500 games: V0, Gentle, Lights, the best route point (Fast, Bypass or Jam-avoid by round-1 estimate), and All-on. (Clean is compared descriptively from round 1.)

Each point is judged by **its own paired contrast against V0 on round-2 maps only**. Paired SD for these relatives is about 250–300, so SE ≈ 16. The decision measure is mean trips: survival carries the same information, r 0.96–0.98. Median survival and S(1600) are reported but are not decision clauses.

**What the screens decide:**

| Result | Decision | What that means at SE ≈ 16 |
|---|---|---|
| A route point beats V0 (one-sided p < 0.05) and Gentle **and** beats Clean (both descriptive) | That point's planner weights become x0 for both learners (only if expressible in cma-7's fixed coordinates; its new-route rates must be ≥ P4's minimums) | estimate ≥ about +27 |
| Lights beat V0 (p < 0.05) | Hand light weights become x0's place head; otherwise x0 never places | ≥ about +27 |
| Strong go: any point ≥ +100 with p < 0.01 | That point becomes x0; expectation raised | — |
| Nothing passes | x0 = Gentle (new routes still on), unless Gentle is worse than V0 at one-sided p < 0.05, in which case its new-route rates are halved (never switched off). Expectation stays "tie" (gate G3) | — |

Holm over the tested points is reported. The screen can only move x0. It can never take a head away or switch new routes off, so a missed point costs nothing more than a slower start. This table is the only rule for moving x0 (§3.5 and G3 refer to it).

### 2.3 Motorway prototype (C5m; only with the user's approval)

- **Hand rule:** on each motorway offer, build one overpass from the farthest same-colour house cluster to the shop with the lowest ttf. Endpoints on clear land or plain road at least 2 apart; ramps follow `MotorwayNetwork.ChooseRampDirections`. Uses the replay-legal `motorway` command (Program.cs:144-146, AiReplay.cs:85).
- **Planner work:** parse `Motorways` from the observation and add motorway edges to the component and cost graphs.
- **Screen:** round 1 on 4600-4699 (V0 against 2 rule variants, 300 games); round 2 on 4700-4999 (V0 against the best variant, 600 games).
- **Include in gp-7** as a candidate kind (`is_motorway`) if one-sided p < 0.05 and the estimate is ≥ +27. That delays launch by about 2–3 days. Otherwise it goes to gp-8.

### 2.4 CRN (S1): gp-8 by default

- **Design (as in the draft):** a `randomStreams: "keyed"` reset field, default `"shared"` and bit-identical. Placement weights U(hash(seed, colour, kind, k-th spawn, x, y, layout)); grouping keyed (colour, k); plan-entry draws keyed by Order; offers keyed by week; demand phase keyed by colour; parking on its own stream; SplitMix64. Recorded in `AiReplayRecording`; cache version `…@f34+crn`.
- **Changed pilot.** The pilot no longer uses paired TOST, which cannot pass at n = 200 because the same seed is a different city in each mode.
  - Unit tests: each keyed draw is U(0,1).
  - Unpaired distribution check: **hand rule** × 400 seeds per mode (cheap). Two-sample KS on trips and seconds, plus a difference in means with a pre-set ±75 margin.
  - The r gain on 3 rule pairs × 100 maps × 2 modes: (cma-1, 7fa4b2), (cma-1, separated), and (cma-1, cma-1 with one extra 1 s wait at t = 0) as the chaos floor.
  - About 1,400 games (about 3.5 h).
- **Adopt for gp-8** if the lower 80% bound of r ≥ 0.4 for unrelated pairs, or ≥ 0.75 for the chaos floor.
- **Reporting** always uses standard f34.
- The pilot runs only if the CPU is free during pre-work.

### 2.5 The evolvable planner (C4; shared by both learners)

**Principle.** The planner keeps **tools** and loses **hand-made decisions**.
- **Tools (kept as code):** A* search; `draw` legality (diagonals, water degree, ring order, driveways); road and bridge stock; connectivity and components; the executor.
- **Decisions (now learned):**
  - A*'s step costs (today's constants at candidates.py:26-30 and 381-398);
  - which (house, shop) pairs get routes (today only unconnected pairs, `coverage_targets`, candidates.py:548-576).

The legacy candidates (attach, direct, separated, clean) stay on the menu.

**New routes are switched on from the start (the user's requirement, 2026-11-14).** The training start point x0 already proposes some new routes, at a deliberately low rate. If x0 instead copied today's planner exactly, small weight changes would produce no new route at all: a flat plateau that neither learner could climb off (review finding, confirmed). Exact reproduction of today's planner is kept only as a **code test**, using a separate "off" setting, and today's planner stays a comparison row ("legacy x0", §5.2).

**P1. Route-cost head ("evo").** For a step u→n of length ℓ (1, or 1.414 diagonal):

```
c(u→n) = max(floor(ℓ),  ℓ·(w_paid·paid + w_reuse·(1−paid)) + w_step
                        + w_jn·[becomes_junction(u; prev,n) + becomes_junction(n; u) if n is a target]
                        + w_jl·junction_link + w_ns·junction_link·near_shop + w_for·foreign(n, colour)
                        + w_turn·turn + w_br·new_crossing + M[n])
floor(1) = _MIN_ORTH = 0.2,  floor(1.414) = _MIN_DIAG = 0.2621        (candidates.py:31-32)
M = w_car·cars_on + w_stop·stopped_on + w_deg·link_degree + v_9·T_9(cell maps)/s_9      (50×30 array)
```

- **Clamp and heuristic.** The floor is set per direction to the two constants the octile heuristic already uses, so A* stays admissible and consistent for every weight vector, and the clamp never binds at today's settings. (A single clamp of 0.2·ℓ would have raised diagonal road reuse from 0.2621 to 0.2828 and broken the identity test; caught in review.) When every step costs well above the floor, for example at the Fast point, the heuristic is loose and searches expand more nodes. The heuristic is therefore scaled by a lower bound for each weight vector (min over paid ∈ {0,1} of ℓ·w + w_step + the negative coefficients + min M, never below the floor).
- **Exact arithmetic.** Terms are added in the legacy order (base, u-junction, n-junction, foreign, then the new terms), so at the "off" setting the costs are bit-identical and A* ties break the same way.
- **Legacy kinds.** Each legacy kind is a cost vector **plus a target mode** (attach / direct / clean-zone). Separated and attach are exact cost vectors. Direct and clean also need their target mode. Clean = (w_paid 1, w_reuse 0.15, w_step 0.05, w_jl 2, w_ns 6, w_for 3).
- **Turns.** A turn is a direction change of at least 45°. It uses u's fixed parent, which makes it approximate and dependent on tie order. If C5 shows w_turn matters, the A* state becomes (cell, incoming direction, spans) when w_turn ≠ 0.
- **Where evo runs.** Each route pass of the build loop (agent.py:190-202; up to 20 passes per decision) runs evo on:
  - the top T = 8 legacy targets, toward attach targets;
  - each target-head pair. A connected pair searches toward the shop's doorstep cells only (`s.outside`), never its whole component.
- **Order.** Evo candidates are checked against the legacy `seen` set and appended after the legacy list, so the legacy cap of 3 and the clean slot are untouched.
- **When M is built.** M and the pair features are rebuilt at the start of every pass after a pass that executed a route, because the state has changed. Otherwise they are reused.

**P2. Target head.** It scores every (house, same-colour shop) pair:

```
t(h,s) = b_t + w_con·pair_connected + w_det·detour_ratio + w_ttf·shop_ttf_inv(s) + w_dem·shop_demand(s)
         + w_dist·octile(h,s)/50 + w_srv·house_serves_other(h) + w_fail·pair_failed_recent + v_10·T_10/s_10
picked = the top M_eff pairs with t > 0,   M_eff = clip(floor(n_t), 0, 6)   (n_t is a learned coordinate)
```

- **Count separated from choice.** `n_t` sets how many pairs may open, and t only ranks them. The first step away from "off" therefore adds one pair, not six.
- **`detour_ratio`.** The pair's current network route length ÷ the octile distance (0 if unconnected). One BFS per shop, only for shops with ttf < 600 s or the top 6 by demand.
- **`seconds_saved`.** Measured in real, congestion-free seconds: the network route time minus the new route's time (features.py:177/219/340), and 0 for unconnected pairs. It is the same for every cost sample. (The earlier "A* units" definition was almost always 0.)
- **`pair_failed_recent`** (1 if this pair's draw failed in the last 60 s) is an input, never a rule. Failure means "the house still does not reach the shop" for an unconnected pair, and "no new link built" for a connected pair.
- **No-op guards.**
  - An evo candidate must build something (`tiles_needed + bridges_needed ≥ 1`), and for a connected pair also `seconds_saved > 0`. Anything else is dropped before scoring.
  - A target-head pair is tried at most once per decision (added to `excluded_pairs` after its pass). This prevents a free 0-tile redraw from repeating 20 times.

**P3. Features for the existing heads.** Priority gains `is_evo`, `pair_connected`, `seconds_saved` and `target_ttf_inv`. Hold gains `demand_ramp`, `worst_ttf_inv` and max `colour_busy_share`.

**P4. The training start point x0 ("new routes on, gently").** Calibrated on the gp7-v1 bank (§3.3) before launch. It is then fixed and pre-registered.
- **Cost head:** halfway between separated and the C5 Fast point. The reuse discount is weakened (w_reuse = 0.5), plus a small `w_stop` = 0.2. That way evo paths differ from legacy paths in a share of situations.
- **Target head:** w_det and w_ttf small and positive (the Bypass direction), w_con = 0, n_t = 1.2 (at most 1 pair), and b_t set so a pair opens in **about 10% of decisions**.
- **Priority:** w_is_evo set so that an evo candidate is **built in about 3–5% of decisions** at the x0 mean. With mirrored σ0 samples, about a quarter of gen-0 samples should build evo routes in ≥ 2% of decisions (C7 gate).
- **If C5 finds a better point**, that point replaces these values (§2.2). Its new-route rates must still be ≥ these minimums.

**P5. Cost caps and memo.**
- At most min(8, #targets) + M_eff ≤ 14 evo searches **per pass**, against today's up to about 24 × 3–4 legacy searches per pass.
- The cross-decision memo covers legacy kinds, and evo only when M ≡ 0. Otherwise evo results are memoised within the decision only, keyed with a hash of `M.tobytes()`.
- The C2 memo identity check is rerun at a point with non-zero w_car and w_stop.
- Smoke gate: Python time per game up by ≤ 35% at x0 and at the Fast point.

**P6. What stays fixed.**
- Decision timing: the existing event tracker (agent.py:42-79); no ttf trigger.
- Removal: off (a removal head is a gp-8 candidate).
- Motorways, if approved: offered as an option (`is_motorway`), never forced.

**P7. Size, scaling and checks.**
- **Size.** About 22 new coordinates: cost head 13, target head 8 + n_t, plus the new priority terms. Both learners go from about 65–72 to **about 87–94 dimensions**.
- **Preconditioning (§4.2).** Each planner weight's initial std is the step that changes the built route in about 10% of the 200 stored situations, the same w0 rule the slot screen uses. Biases (b_t, b_L, hold bias) get their std from the spread of their head's linear part under a σ0 sample. σ0 counts planner coordinates in its 25–35% "decisions changed" calibration.
- **C7 gates (zero games).** On the stored sub-bank, at least 25% of the 24 gen-0 samples must build an evo or target-head route in at least 2% of situations. The mock includes a planted optimum that pays only once two planner coordinates both cross a threshold, and the mean must reach it within 20 generations. If either gate fails, the target head shrinks to (b_t, n_t, w_con, w_det, w_ttf) and x0's new-route rate is doubled.

---

## 3. gp-7: Dynamic Feature GP (DF-GP)

The policy is a set of linear heads tuned by sep-CMA plus **K = 10 fixed slots**. The heads are the four decision heads and the two planner heads of §2.5. Each slot holds a small GP feature tree that can be gated on stress or game phase. "Dynamic" means four things:
- structure is replaced during the run, but only after a game test;
- terms can switch behaviour on predicted shop failure;
- **the planner itself evolves:** two slots shape A*'s route costs and the choice of target pairs, so new route styles can be discovered rather than hand-coded;
- the CMA covariance turns on only once there is signal.

### 3.1 Representation

```
priority(c) = Σ w_i·x_i(c) + Σ_{k=1..4} v_k·F_k(c,g)/s_k    x: 23 candidate terms (+is_clean iff clean=1) + is_evo, pair_connected, seconds_saved, target_ttf_inv
hold(g)     = b + Σ u_j·g_j + Σ_{k=5,6} v_k·F_k(g)/s_k      g: 15 globals (x0 = hold_g − prio_g, which replays cma-1 exactly) + demand_ramp, worst_ttf_inv, max colour_busy_share
upgrade(o)  = Σ a_m·o_m + v_7·F_7(o,g)/s_7                  o: 8 offer terms (the 16 dead upgrade globals removed)
place(s)    = if_gt(pl_is_light, .5, b_L + Σ p_n·s_n + v_8·F_8(s,g)/s_8, −1)   s: pl_stopped_near, pl_max_wait_near, pl_mean_wait_near, pl_doorstep, pl_degree, pl_dist_worst_shop
cost(u→n)   = §2.5 P1, with M[n] += v_9·F_9(cell maps)/s_9          cell terminals only; evaluated once per decision as a 50×30 map
target(h,s) = §2.5 P2, + v_10·F_10(pair terms, g)/s_10
```

- **Slot trees:** at most 15 nodes, depth at most 4. Primitives: add, sub, mul, protected div, min, max, neg, `if_gt`, and `gate(x, θ) = 1[x > θ]`. Terminals: that head's terms, the globals, and the stress and move features. Constants change by Gaussian steps (σ = 0.2·max(|c|, 0.1)), never by redraw.
- **s_k** is the slot's within-decision spread on the bank, frozen when the slot is filled.
- **Initial slots = 10 pre-registered templates, identical to cma-7's fixed interaction terms:**
  - priority: `mul(demand_ramp, path_cost_s)`, `mul(demand_ramp, is_separated)`, `mul(target_ttf_inv, seconds_saved)`, `mul(stuck_cars, path_cost_s)`;
  - hold: `mul(demand_ramp, road_stock)`, `mul(worst_ttf_inv, unserved_houses)`;
  - upgrade: `mul(type_3, worst_overcrowded)`;
  - place: `mul(pl_stopped_near, worst_ttf_inv)`;
  - cost: `mul(gate(worst_ttf_inv, θ_q75), stopped_on)` (avoid jams only under stress);
  - target: `mul(shop_ttf_inv, detour_ratio)` (shortcuts for starving shops).
- **Size:** about 87–94 dimensions, constant (§2.5 P6).
- **Bank storage:** the bank also keeps each situation's observation so planner slots can be screened (§3.3).
- **Text:** the policy renders to 5-tree TreePolicy text with a `flags:` line (remove = −1) and a `planner:` block. Engine, cache and evaluate work unchanged once C4(f) is in.
- **Within a game nothing changes.** The heads, slot trees and planner weights are fixed for the whole game, in training and in testing. Learning happens only between generations. Behaviour within a game varies only through the inputs: traffic maps, ttf, demand_ramp, game time.

### 3.2 Inner loop (weights)

The inner loop is exactly cma-7's (§4.2–4.3). The recommendation is always the distribution mean.

### 3.3 Outer loop (structure): game-tested, every epoch of E = 5 generations

At the end of generations 4, 9, 14, …:

1. **Propose.** 600 trees across the slot heads, using a separate RNG stream so CMA draws stay aligned with cma-7:
   - 35% subtree or Gaussian-constant mutation of current or archived accepted slots;
   - 15% crossover between slot trees;
   - 15% gate wrapper `mul(gate(stress, θ), F)`, with stress ∈ {min ttf, target_ttf, colour_busy_share, demand_ramp} and θ from bank quantiles;
   - 10% interaction `mul(F, base_term)`;
   - (no template operator: proposals that exactly match one of the 10 templates, at any constants, are rejected so a freed template cannot return by another route; each accepted proposal's operator of origin is logged);
   - 15% random depth-1–3 trees.

   Operator shares adapt deterministically to their **game-tested acceptance rate** (Laplace-smoothed).
2. **Bank screen** (0 games; phenotypic characterisation, Hildebrandt & Branke 2015). A proposal survives if all hold:
   - it is finite;
   - for priority and place slots, it varies within a decision in at least 10% of situations;
   - |r| < 0.9 with every active term;
   - at weight w0, it changes 3–40% of the bank's chosen actions, where w0 is the weight at which it changes 10%.

   Rank survivors by the share of changed decisions in the last 400 s before failure, minus the share in the first 600 s. Take the top 3, at most 2 per head.

   **Planner slots (cost, target) screen differently.** A changed cost or target formula changes the candidate set itself, so the screen has to re-run candidate generation:
   - The bank stores the full observation for each situation; `CityState` is rebuilt from it.
   - At most 60 of the 600 proposals go to the planner slots.
   - Each is screened on a fixed 200-situation sub-bank, restricted to the top 3 targets. That is about 600 A* searches per proposal, about 10–15 s, or about 12–15 min per epoch on one core.
   - "Changes the chosen action" means a different route is built.
3. **Structure race on fresh probe maps** (counter from 10000+3000(k−1), never reused):
   - **Stage 1:** 16 maps. The current mean plays, and each proposal plays at +w0 and −w0. That is 16 × 7 = 112 games. Keep each proposal's better side. The top 2 proposals whose better side's paired difference against the mean is > 0 continue.
   - **Stage 2:** 32 more maps, for the mean and the 2 surviving sides: 96 games.
   - **Accept** a proposal if its 48-map paired difference against the mean is > 0 with one-sided p < 0.2 (paired SD ≈ 230, SE ≈ 33, so about ≥ +28). At most 2 per epoch.
   - **Cost:** ≤ 208 games per epoch, about 42 per generation.
4. **Free a slot by a statistic with a known null.**
   - For each slot k and generation g, compute Spearman(z_pk, d_p) over the 12 mirrored pairs, where z_pk is pair p's offset in coordinate k and d_p = f(+) − f(−). Under the null it is ~N(0, 1/11).
   - Accumulate Z_k = Σ_g ρ_gk·√11 / √G_k over the slot's age. Under the null, Z_k ~ N(0,1) whatever the age.
   - A slot is freeable if its age ≥ 1 epoch, |Z_k| < 1, and its effect e_k = |m_k|·spread_k is < 5% of the head's largest term effect.
   - An accepted proposal replaces the freeable slot with the smallest |Z_k|. If none is freeable, the proposal goes to the archive.
5. **Insert at the tested weight.** m_k = ±w0 (the tested side). Initial std from bank spread; evolution-path entries for k set to 0; Z_k reset.
6. **Refresh the bank** every 3 epochs. The mean plays 10 recording games on 3660-3699, cycling. Charged to gp-7.
7. **No in-run structure monitor or G6.** Structure value is measured once, in the test battery, as co-primary hypothesis H2 (§5.3).

### 3.4 What is not in gp-7, and why

- **No hall of fame, reference subtraction, 8-map tournament or racing.** 8-map rankings are 72% noise, and reference subtraction adds 38% variance.
- **No immigrants.** 0 of 38 reached the racing top.
- **No lexicase.** Per-map r ≈ 0.2.
- **No separate tree-GP arm.** It is unaffordable. The `gp.py` fixes (node limits, Gaussian constants) keep it possible for gp-8.

### 3.5 Seeds, initialisation, budget, stop rule

- **x0:** the cma-1 final rule in live coordinates (clean setting from C0), with the planner and light heads at the §2.5 P4 start, moved per the §2.2 table. Slot weights start at 0.
- **Shared trunk.** gp-7 run k and cma-7 run k use the same sep-CMA seed and training-map stream. They are identical through generation 4, so generations 0–4 are run **once** as a shared trunk on 12 workers (about 1,610 games) and charged in full to **both** arms. Then the checkpoint and cache are copied and each arm resumes on 6 workers. gp-7's first structure race happens after the fork.
- **Budget and stop rule:** identical to cma-7 (§4.3, §5.4), in charged games. gp-7's structure races and bank refreshes come out of its own budget, so it reaches about gen 40 at the backstop where cma-7 reaches gen 45. That is the cost of the method, and it is reported.

---

## 4. cma-7: fixed-structure control, made strong

### 4.1 Search space

- The same heads as gp-7, **including the evolvable planner heads (§2.5)**, the same base terms and stress features, plus **the 10 templates as fixed coordinates**: about 87–94 live dimensions. So CMA-ES also evolves the planner, but only through fixed, hand-chosen terms. gp-7 can also search for new planner terms.
- Removed: the 16 upgrade globals, the 16 priority globals (folded into hold as hold_g − prio_g), `pending_refunds`, and `is_clean` when clean = 0.
- The comparison asks exactly one question: does **searched** structure beat **hand-chosen** structure, with identical inputs, actions, x0, maps and budget?

### 4.2 Algorithm (`sepcma.py`, shared by both arms)

- **Engine:** in-house sep-CMA-ES (Ros & Hansen 2008) with CSA, about 250 lines of numpy. It needs one-coordinate resets and picklable state, which pycma's sep mode does not give cleanly (evolution_strategy.py:1305-1320, 1378).
- **Preconditioning:** per-coordinate initial std ∝ 1/spread from the bank (median 1, clipped to [0.1, 10]); samples clipped at ±8 std units.
- **σ0:** calibrated so the median sample changes 25–35% of bank decisions; C7 checks it.
- **Sampling:** λ = 24 as **12 mirrored pairs** on identical maps, with **pairwise selection**: the better member of each pair enters. All 12 winners are recombined with log rank weights (μ_eff ≈ 6.5, against 4.84 in cma-6, which cuts noise-driven drift variance by about 25%).
- **Covariance frozen** (CSA on σ only) until the logged split-half reliability exceeds 0.2 for 3 consecutive generations. Then the diagonal updates switch on, deterministically. Under no signal, the faster rates of sep-CMA would only random-walk the variances.
- **Tell:** rank-based on mean trips over the generation's shared maps. No log, median, seconds, trips/tile or q25 objectives.
- **No UH-CMA σ inflation, no IPOP/BIPOP restarts, c_m = 1** (see the appendix).

### 4.3 Generation protocol (both arms)

1. **Maps:** m = **12, fixed** (no adaptive escalation). Fresh from 1-999 each generation, a deterministic function of (run seed, gen), shared by all candidates and the mean.
2. **Early cut:** after the first 4 maps, a candidate below 0.6 × the generation's median 4-map mean stops and ranks below all survivors. Its partner continues and wins the pair.
3. **Trend monitor:** `text(es.mean)` plays the same 12 maps. These games are not told to CMA. They form the per-generation trend line (SE ≈ 65), reported next to the population average.
4. **Reliability log only:** Spearman–Brown-adjusted split-half reliability over all 462 6-vs-6 splits, plus F. It feeds the covariance switch-on rule and the report, never the map count.
5. **Tracking snapshot:** at gen 0 and every 5 generations, the mean plays the tracking block 2100-2249 (150 games). Used only by the stop rule and gate G4.
6. **Cost per generation:** about 280 candidate games after cuts, +12 mean, +30 amortised tracking ≈ **322** for cma-7; ≈ **364** for gp-7 with races and bank refreshes.
7. **No guard.** The draft's 50-map guard had 20–26% power. Drift protection comes from x0 being a pre-registered candidate for the project headline rule (§5.2).

---

## 5. Evaluation protocol

### 5.1 Seed blocks

Pre-registered. Confirm with Mohammad and the fidelity work that none of these were played on f34.

| Use | LA seeds | Mode / code |
|---|---|---|
| Training (stream k shared by gp-7 k and cma-7 k) | 1-999 | standard f34, gp7-v1 |
| Hand screens | 3200-3299 (round 1), 3300-3599 (round 2) | gp7-v1 |
| Autopsy, bank, bank refresh | 3600-3699 | gp7-v1 |
| CRN pilot (optional) | 3700-3999 | both modes |
| Motorway prototype | 4600-4999 | gp7-v1 |
| **Tracking block** (stop rule and G4 only; never selects) | **2100-2249** | as training |
| Structure-race probes (consumed by counter, never reused) | 10000+; run k from 10000+3000(k−1) | as training |
| gp-6/cma-6 close-out | 5100-5299 | gp6-v1 |
| **Validation at stop** (headline pick only) | 1550-1749 (200) | gp7-v1 |
| Final selection (only if 3+3) | 4200-4599 | gp7-v1 |
| **Primary test** | **6100-6999 (900)** | standard, `--verify` with an f34-built verifier |
| Continuity row | 7000-7099 | same |
| PPO head-to-head (reserved) | 8100-8199 | — |
| Retired for decisions | 1500-1549 | continuity plots only |

### 5.2 Controls against the winner's curse

- **Method finals are fixed in advance:** each run's distribution mean at stop. There is no selection among snapshots, candidates or validations.
- **Project headline rule:** one pick among {gp-7 final, cma-7 final, x0, legacy x0 (today's planner)} by empirical-Bayes posterior on validation 1550-1749 (4 × 200 games). It is then tested once on 6100-6999, different maps, so the estimate is unbiased. This is the protection against drift. x0 is always a candidate, so a run that drifted downwards cannot lower the headline.
- **Single-use blocks.** The tracking block never selects. Probes and validation are used once each.
- **Shrinkage.** Any per-rule number quoted during a run is shrunk by empirical Bayes, with variance components re-estimated from that run's ANOVA.

### 5.3 Hypotheses and statistics

Statistics follow PLAN.md:201-209: paired mean difference, BCa bootstrap (10,000 resamples), paired-t CI and two-sided Wilcoxon.

- **H1 (co-primary):** gp-7 final vs cma-7 final on 6100-6999 (n = 900). Two-sided α = 0.025 (Bonferroni with H2). The finals will have diverged and be effectively unrelated (SD ≈ 450), so the **MDE is ≈ 46 trips** at power 0.8.
- **H2 (co-primary, the structure-value claim):** gp-7 final vs the same final with all v_k = 0, on 6100-6699 (n = 600). The two are close relatives (SD ≈ 230), so SE ≈ 9.4 and the **MDE is ≈ 29**. Caveat: the head weights were co-tuned with the slots, so H2 measures what the slots contribute inside gp-7. It does not measure GP against hand structure; H1 does.
- **Secondary family** (Holm, two-sided α 0.05, 5 tests): gp-7 vs hand; cma-7 vs hand; gp-7 vs x0; cma-7 vs x0; headline vs legacy row. On 6100-6999, except legacy on 6100-6399.
- **Success (PLAN.md:188):** gp-7 beats cma-7 (H1, CI at the 97.5% level) **and** beats the hand rule (95% CI, Holm-adjusted), both excluding 0.

### 5.4 Stop rule (both arms)

- **Snapshots:** the mean on the 150-map tracking block at gen 0 and every 5 generations.
- **Convergence test:** at each snapshot with g ≥ 25, compute each map's OLS slope over the last 5 snapshots (a 20-generation span), then the mean slope across the 150 maps and its SE. Because the test is paired by map, autocorrelation between snapshots and map effects are handled exactly.
- **Converged** when the **one-sided 90% upper bound of the slope is < 2 trips per generation**.
- **Backstop:** 14,800 charged games (cma-7 ≈ gens 0–45, gp-7 ≈ gens 0–40). Stopping there gives status `budget`.
- **Simulated behaviour** (stop7b.py: 1,500 repetitions, 150 maps, map SD 110, interaction SD 250–330, AR(1) ρ = 0.3 between snapshots, backstop gen 45):

| True curve | P(labelled converged) | Median generation when it fires |
|---|---|---|
| Flat | 89–97% | 25–30 |
| +4/gen to g15, then flat (+60) | 79–89% | 35 |
| +4/gen to g25, then flat (+100) | 54–65% | 40 |
| +2/gen throughout | 35–38% | 35 |
| +3/gen throughout | 10–13% (false) | 35 |
| +4/gen throughout | 1–5% (false) | 35–40 |

  For gp-7, the backstop around gen 40 lowers the "rise to g25" row. This is reported.
- **Wording in reports:** "converged: no sustained gain above about 3–4 trips per generation over the last 20 generations (≈60–80 trips)". `budget` and `converged` stay separate labels.
- **Logged but not stop conditions:** σ, reliability, F, structure acceptances.

### 5.5 GP vs CMA, equal budgets, and the ≥ 3-runs requirement

- **Budget:** equal **charged games**, 14,800 per run. The ledger counts every distinct (text, seed) evaluation the algorithm requests. Trunk games are charged to both arms. Resume replays are not new evaluations.
- **Caches:** separate per arm after the fork (each copied from the trunk), so neither arm can get free games from the other.
- **Reporting:** games, cache hits, CPU-hours and downtime per method. Curves use games on the x-axis, with the population average next to the mean or snapshot in every recap.
- **Concurrency:** trunk on 12 workers, then 6 + 6. Games are deterministic per (code, simulator, text, seed), so running side by side cannot bias results. This deviates from PLAN.md:238 and needs the user's approval.
- **Default: 1+1 runs.** The result is reported as a per-rule comparison, with run-to-run variance disclosed as unmeasured (PLAN.md:203).
- **3+3, only if pre-committed before run 1's results** (no gate, all replicates always run). Method effect = mean over k of (gp-7_k − cma-7_k), plus the mixed model trips ~ method + (1|run) + (1|map). The 95% CI half-width with df = 2 is about **±90–200 trips**, so it can only confirm a very large effect. That cost is stated up front.

---

## 6. Compute budget and schedule

**Throughput assumptions:**
- Base: **300 games/h** on 12 workers at x0 quality (measured).
- Cost grows with policy quality: about +40% at 1,200 trips, +65–100% at 1,300–1,450.
- Speedups count only once C2 has measured them. The ceiling is 1.4–1.7×, because Python is about 19% of CPU.

| Stage | Games | Hours at 300/h (with cost growth) |
|---|---|---|
| C0 close-out | 1,400 | ≈4 (hand and separated are cheap) |
| C2/C3/C4/C6 checks | ≈200 + replays | ≈1.5 |
| C5 hand screens | 2,400 | ≈8 |
| C5m motorways (if approved) | 900 | ≈3 |
| C7 smoke | ≈300 | ≈1 |
| CRN pilot (optional, gp-8) | ≈1,400 | ≈3.5 |
| **Phase A: trunk + 2 arms to stop** (charged 8,000–14,800 each) | 14,400–28,000 | 48–93 (67–130 middle scenario; up to ≈185 if a strong go) |
| Validation (gp-7, cma-7, x0 and legacy x0 × 200) | 800 | ≈3–4 |
| Test battery: 4 policies × 1,000 (900 + 100) + ablation 600 + legacy 300 (hand is cheap) | ≈4,900 | ≈14–22 |
| **Total, 1+1** | **≈25–40k** | **≈4–7 days of machine time** |
| Total, 3+3 | ≈55–95k | ≈9–17 days |

### Day-by-day timeline

| Day | Date | Work |
|---|---|---|
| D0 | Fri Nov 14 | gp-6 stops about 04–07:00; start C0 on its 8 workers. cma-6 stops about 07–11:00; C0 gets all 12, done by afternoon, and the C1 lid-closed test runs during it. Disable `gp6-watchdog`. Create the `mm-gp7` worktree. Ask the user the decisions (motorways, 1+1 vs 3+3, CRN, the performance PR). Start C3 code. |
| D1 | Sat Nov 15 | C0 analysis and EXPERIMENTS.md entry. C2 harness, profiling and the two speedups. C3 games (60) in the evening. |
| D2–D6 | Nov 16–20 | C4: cost head, target head, cell maps, pickup estimator, `flags:`/`planner:` text. Identity tests, then the bank re-recorded under gp7-v1. Smoke (24 games). C5 round 1 on the evening of D6. |
| D7 | Nov 21 | C5 round 2 (1,500 games, overnight). C6 starts with `linear.py` and `sepcma.py`. C5m coding if motorways are approved. |
| D8–D10 | Nov 22–24 | C6 (`slots.py`, `bank.py`, `evolve7.py`, `stats7.py`, `gp.py` fixes). C5m games (900) if approved. G3 decision. |
| D11–D12 | Nov 25–26 | C7 mock, planner gates and smoke with kill/resume. C8 sign-off. **Trunk launch.** Add about 2–3 days if motorways pass and are integrated. |
| D12–D17 | Nov 26–Dec 1 | Trunk (≈5.5 h), fork, Phase A. G4 at gen 15. S2 and gp-8 coding meanwhile, but no CPU slots. |
| ≈D17–D19 | ≈Dec 1–3 | Validation, test battery, report. 3+3 (if pre-committed) adds about 7–11 days. |

### Operational safety

- AC power; no sleep or hibernate; lid action "do nothing".
- The laptop stays docked through Phase A; usage windows agreed with the user.
- `gp7-watchdog` uses `--resume` only.
- **Checkpoints store:** the CMA state; both RNG streams; slots and archive; Z_k accumulators; bank version; the covariance switch state; the probe counter; the ledger.
- Every adaptive rule is a pure function of cached results and RNG state, tested in C7.
- Never resume across code, simulator or mode changes.
- At most 12 workers; bump CODE_VERSION on any behaviour change.

---

## 7. Expected outcomes, gates, risks

### Honest ranges (my judgement; fresh test maps; x0 ≈ 990–1030)

| C5 / C5m result | Probability | cma-7 final | gp-7 final | P(H1 significant for gp-7) |
|---|---|---|---|---|
| No move passes | ≈50–60% | x0 ± 30 | cma-7 ± 30 | ≈5% |
| Lights, stress features and evolved routes/targets add +30–60 s at the wall | ≈30–40% | 1,040–1,150 | 1,040–1,180 | ≈10–20% (gated slots are GP's real chance) |
| A move breaks the wall (strong go; motorways raise this if approved) | ≈10% | 1,150–1,400 | 1,150–1,450 | ≈20–25% |

- **Convergence:** both runs reach the converged label with about 60–90% probability, depending on how long they keep improving. That would be the first real GP convergence in this project.
- **H2:** structure value is detectable if the slots are worth ≥ about 30 trips.

### Decision gates

| Gate | Trigger | Action |
|---|---|---|
| G0 (C2) | Replay harness passes on all 902 files; memo identity holds | Adopt; otherwise drop that change |
| G1 (C3) | Autopsy cause | Picks which hand points C5 tests and which cell/pair terminals the planner heads get first. Long journeys → Fast/Bypass points. Junction or gate jams → Jam-avoid point and `stopped_on`. Idle cars while a shop starves → catchment features. ttf Spearman < 0.5 → use the fallback features. |
| G2 (CRN) | Pilot r bounds | Adopt for gp-8 only |
| G3 (C5/C5m) | x0 rules (§2.2) | x0 set per the §2.2 table; strong go also raises the expectation. **No-go:** if motorways are approved and untested, finish C5m first; if motorways fail or are not approved, launch anyway with the stated "tie" expectation (user decision 3) |
| G4 (gen 15) | Both tracking snapshots below x0 − 2 SE | Treat as a bug: pause and run an autopsy |
| G5 (stop) | §5.4 | Converged or budget; validation; test |
| Phase B | Only if pre-committed | Never gated on run 1 |

### Top risks and mitigations

1. **No headroom in the moves.** C3, C5 and C5m measure it before launch; the clean comparator; honest expectations given to the user beforehand.
2. **Noise swamps CMA.** Mean recommendation; 288 shared games per generation; mirrored pairs; preconditioning; the covariance freeze. CRN in gp-8.
3. **GP adds nothing.** Game-tested insertion; H2 measures it cleanly; "no structure value" is a reportable result.
4. **The new planner breaks behaviour or slows Python.** Flag-gated byte-identical v6 path; four identity tests (incl. the planner "off" setting); at most 14 evo A* per pass; no-op guards; cell-cost map rebuilt only after an executed route; evo memo keyed by the M hash or kept per decision.
5. **Bugs in sep-CMA or slots.** Cross-check against pycma; mock evaluator; unit tests for pickling, determinism and resets.
6. **Cost grows with quality.** Budgets in games; wall ranges by scenario.
7. **Sleep, crashes or the laptop being needed.** C1 test under load; watchdog; exact resume; downtime reported.
8. **The protocol change looks like moving the goalposts.** Pre-registration signed off before launch; continuity rows (1500-1549 plots, 7000-7099).

---

## 8. What would make this "far above baselines"

- **The arithmetic.** ≥ 1,300 trips means moving median death from about 1,430 s to about 1,630 s (+200 s ≈ +315 trips). The wall is a car-supply squeeze: cars per unit of demand fall from 6.5 to 4.8 between 1,000 and 1,600 s, then level off at 4.2–4.4. Getting past it pays heavily.
- **Search alone cannot get there.** The true spread near cma-1 is 22–54 trips. Search has produced 0 validated gains on f34, while one planner fix gave +154.
- **The bets, in order:**
  1. **An evolvable planner:** route shapes (cost head) and target pairs (target head, including already-connected pairs) are learned, so shorter round trips, bypasses and jam avoidance can be found by search rather than hand-coded. Also lights where cars stop, and **motorways** as an option (3× speed, no road stock, the most common offer in weeks 3–8; prototype now if approved).
  2. Acting 100–300 s before failure, through ttf features that the heads and the gated slots can use.
  3. Stress-gated slots that only gp-7 can express, now inserted only after game evidence.
  4. Measurement that keeps a real +50 to +100 and rejects a lucky one: mean recommendation, 900-map test, single-use blocks.
- **Without a passing move, the honest expectation is a tie near cma-1.** This is said before launch.

---

## 9. Code changes (all in the gp7 worktree)

| File | Change |
|---|---|
| `evolved_rules/gp.py` | Replace `MAX_DEPTH = 6` (line 205; reverts at 482/499/537) with node limits per tree (slots ≤ 15 nodes, depth ≤ 4; full trees ≤ 250, soft height 12). Gaussian constant mutation instead of `mutEphemeral`. New terminals: `is_evo`, `pair_connected`, `seconds_saved`, `detour_ratio`, cell terminals (`cars_on`, `stopped_on`, `link_degree`, `near_shop`, `foreign`, `water`), `target_ttf_inv`, `demand_ramp`, `worst_ttf_inv`, `colour_busy_share`, `colour_idle_cars`, shop margin (and `is_motorway` if adopted). `gate` primitive. TreePolicy parses the `flags:` line, which overrides the defaults at lines 442-444. Immigrants dropped. |
| `evolved_rules/candidates.py` | `_astar` takes a cost-weight vector and a per-decision cell-cost map (today's models become exact vectors); evo candidates (`is_evo`); target head over all same-colour pairs, with `detour_ratio` by per-shop BFS; `moves=v6|v7`; `route_candidates` memo (evo entries keyed with the M hash, or per decision); per-direction cost floor; no-op guards; `excluded_pairs` for target-head pairs. |
| `evolved_rules/features.py` | Per-shop pickup estimator; per-shop margin by catchment; busy share; idle cars; ttf; `seconds_saved`; `demand_ramp`; fallback stress features. |
| `evolved_rules/agent.py` | Planner-head plumbing (cell maps rebuilt per pass after an executed route); `pair_failed_recent` bookkeeping (an input only); flag plumbing; bank-export hook (observations kept). Decision timing unchanged. |
| `evolved_rules/engine.py` | `CODE_VERSION = "gp7-v1"`; ledger hook. |
| `evolved_rules/autopsy.py` | Obstacle parse (autopsy only); per-shop wall logs; per-decision spreads; bank export. |
| `evolved_rules/replay_check.py` (new) | Runs all 902 replays and asserts score, seconds and command count. |
| `evolved_rules/bank.py` (new) | Bank storage; spreads; decision-change rate; σ0 and w0 calibration. |
| `evolved_rules/linear.py` (new) | Live coordinates; x0 from cma-1 (hold_g − prio_g); slot embedding; text writer with `flags:`. |
| `evolved_rules/sepcma.py` (new) | sep-CMA-ES with CSA, mirrored pairs and pairwise selection, covariance freeze, coordinate reset, clipping, picklable state. |
| `evolved_rules/slots.py` (new) | Proposals (own RNG); bank screen; the two-stage structure race; Z_k freeing; archive; operator credit. |
| `evolved_rules/evolve7.py` (new) | Unified loop with `--slots 8|0` and `--trunk/--fork`: maps, early cut, trend monitor, reliability log, tracking, stop rule, ledger, checkpoint and resume. |
| `evolved_rules/stats7.py` (new) | Empirical Bayes; paired-t; BCa; Wilcoxon; Holm/Bonferroni; per-map slope rule; split-half reliability (462 splits); KS. |
| `evolved_rules/evaluate.py` | Battery mode with `--verify` using an f34-built verifier. |
| `evolved_rules/tests/*` | Identity tests (moves off, flags, x0 decisions); sepcma vs pycma; slot revert rate; resume determinism; mock evaluator. |
| `simulation/Assets/Simulation/TrafficControl.cs:344-348` | Skip the unused LINQ (private DLL in mm-gp7's own bin; PR offered upstream). S2 items optional. |
| Watchdog | New `gp7-watchdog` task. |
| Docs | `plans/2026-11-xx-gp7-cma7.md` (pre-registration); PLAN.md amendment; EXPERIMENTS.md (close-out, then gp-7/cma-7 with the average next to the best). |

---

## 10. Why this beats gp-6/cma-6

| gp-6 / cma-6 | gp-7 / cma-7 | Evidence |
|---|---|---|
| Same moves; search over formulas only; planner choices hand-coded | The planner's route costs and target choice are evolved by both learners; hand ideas enter only as screened starting points | Same throughput for every rule; shared wall; planner fix +154 vs search 0 |
| GP could not edit its seed; constants redrawn | The linear head contains the seed exactly; CMA tunes weights; GP adds gated features only after a game test | gp.py:205/482/499/537 |
| Best sample or max of 10 validations as incumbent | Distribution mean fixed in advance; x0 kept as a headline candidate | +99.5 optimism; 1037 → about 1006 |
| 8-map racing; hall of fame minus the reference | 288 shared games per generation; rank tell; paired structure races | Reliability 0.28 and about 0; subtraction +38% variance |
| Full-covariance CMA over 81 weights, 34 dead, unscaled | sep-CMA over about 70 live, preconditioned coordinates; mirrored pairs; covariance frozen until signal | cond(C) 1.17; random-walk drift |
| Stop rule with 4–14% power; reuses 1500-1549 | Paired per-map slope rule (simulated: converges 79–97% after a plateau, 1–5% false at +4/gen); single-use blocks | stop7b.py |
| Unequal games; no CMA lights; clean-routes mismatch | Equal charged games incl. the shared trunk; identical actions, inputs and x0; clean decided by data | 4,294 vs 1,801 games |
| Planned on 450 games/h; sleep and timeouts | 300 games/h measured; lid test under load; watchdog; exact resume | generations.jsonl wall_s |

---

## Appendix A: red-team issues and how the plan changed

| Issue | Resolution |
|---|---|
| RT1/RT2/RT3: the noise monitor pushes m to 24 and the stop rule can never fire | **Adopted.** m fixed at 12; reliability logged only; backstop 14,800 games (≈gen 45); stop rule re-simulated |
| Snapshot noise too optimistic; autocorrelated snapshots | **Adopted.** Paired per-map slope test (handles autocorrelation exactly); simulated at SD 250–330, ρ 0.3; 90% bound |
| "−42 sample loss removed" unproven | **Adopted.** Claim removed; no-move scenario is x0 ± 30 |
| Guard underpowered | **Adopted.** Guard removed; x0 becomes a pre-registered headline candidate |
| gp-7 vs cma-7 MDE assumed relatives | **Adopted.** Test enlarged to 900 maps; H1 at SD 450, MDE ≈ 46; H2 ablation added |
| 3+3 CI ±90–200; G-rep fires under the null | **Adopted.** Default 1+1; 3+3 only if pre-committed, never gated |
| Hand-screen contrasts not estimable; loopholes | **Adopted.** One-factor contrasts on 300 maps; median-survival clause dropped; cut-offs stated; clean comparator; 3 strengths |
| I_k is a noise statistic | **Adopted.** Z_k with a known null; credit from game-tested acceptance |
| Structure inserted without game evidence | **Adopted.** Two-stage paired structure race; insertion at the tested weight |
| CRN TOST unpassable; schedule | **Adopted.** Unpaired KS / means check; r measured on 3 pairs; CRN moves to gp-8 |
| Structure monitor / G6 cannot resolve effects | **Adopted.** Dropped; replaced by H2 |
| Duplicated games / shared cache | **Adopted.** Shared trunk charged to both arms; separate caches after the fork |
| Clean decided on sign; Holm miscount; "low-noise" mean | **Adopted.** +1 SE rule with default off; Holm over 6; renamed "trend monitor (SE ≈ 65)" |
| 450 games/h too high | **Adopted.** 300/h, re-measured from generations.jsonl |
| Timeline infeasible | **Adopted.** Launch on D10 (Nov 24), +2–3 days with motorways |
| +30% cost growth too small | **Adopted.** Ranges by scenario (+40% to +100%) |
| 4-tree text cannot express clean-off plus lights | **Adopted.** `flags:` line plus in-tree `pl_is_light` gating (verified at gp.py:442-444) |
| Memo key incomplete | **Adopted.** Full key; identity test with 7fa4b2 |
| `--verify-replay` does not compare scores | **Adopted.** `replay_check.py` (verified at Program.cs:64-75); DLL isolated in the worktree |
| No delivery rate for ttf | **Adopted.** Pickup estimator; fallback features; +0.5 day (verified at features.py:59-99) |
| C3 needs the Obstacle parse | **Adopted.** Autopsy-only parse; +0.5 day |
| 462 splits | **Adopted** |
| Lid test under load | **Adopted** |
| sep-CMA covariance rates under no signal | **Adopted.** Covariance frozen until reliability > 0.2 for 3 generations |
| Fast A* resembles clean mode | **Adopted.** Clean comparator in C5 |
| Motorways should be on the critical path; ask on day 0 | **Adopted** (subject to the user's approval) |

## Appendix B: red-team issues not adopted

1. **Trust region ‖m − x0‖ ≤ r0, or c_m = 0.5 from the start (RT1).** Not adopted. A smaller c_m scales signal and noise-driven drift by the same factor, so it does not change the run's SNR; it only slows everything. A trust region caps the gain the user wants. Drift is harmless where the landscape is flat. Where it is not flat, broken regions give a detectable signal. Downside risk is handled by keeping x0 as a headline candidate and by μ_eff 6.5 with pairwise selection.
2. **5+5 runs at about 7k games each (RT1).** Not adopted as the default. That is about 70k games, roughly 10 days. A 7k-game run cannot reach g ≥ 25 at 322 games per generation, so no replicate could converge, which conflicts with the user's "run to real convergence". Offered as an alternative only if the user values a method claim over convergence.
3. **A 150–200-map guard every 15 generations (RT1).** Not adopted. The guard was removed entirely instead (Appendix A).
4. **Do not launch on a no-go (RT3).** Partly adopted: a no-go first triggers the motorway prototype if it is approved and untested. If nothing passes, the plan still launches by default (user decision 3). The project has never had a converged, equal-budget GP-vs-CMA comparison, and that result, even "GP ties CMA", is reportable. The cost is about 3–4 machine-days, stated beforehand.
5. **Base the hand-screen go/no-go on median survival seconds (RT3).** Not adopted as the decision measure. Trips and seconds give identical paired t-statistics (r 0.96–0.98), and trips is the reported objective. Survival is reported alongside. The n = 300 part of the suggestion was adopted.

---

## DECISIONS FOR THE USER (each with a recommended default)

**Decided 2026-11-14:** the planner becomes evolvable in both learners (§2.5); no planner-free baseline.

1. **Protocol amendments**: new seed blocks, the paired-slope stop rule, the 900-map test with H1/H2, equal charged games including a shared trunk, and 6+6 concurrency after the trunk (a deviation from PLAN.md:238). **Default: approve.**
2. **Motorways** (excluded 2026-11-07): build the hand prototype now, on the critical path; included in gp-7 only if it passes the screen. **Default: yes**, because it is the largest unused move. It adds about 2–3 days if it passes.
3. **If no move passes C5/C5m**: launch gp-7/cma-7 anyway, expecting a tie, or hold and keep developing moves. **Default: launch** (about 3–4 machine-days) and say so in the report.
4. **Run count**: 1+1, about 4–7 machine-days, with run-to-run variance disclosed; or 3+3, about 9–17 days, with a method CI of ±90–200, pre-committed. **Default: 1+1.**
5. **CRN keyed streams**: propose them to Mohammad and the fidelity work as a default-off, training-only flag for gp-8. **Default: propose now; pilot only when the CPU is free; not in gp-7.**
6. **Simulator performance PR** (the dead LINQ at TrafficControl.cs:344-348): offer it upstream; private DLL until merged. **Default: yes.**
7. **Laptop availability**: docked, on AC, lid action "do nothing", from about Nov 25 to Dec 3 (longer for 3+3). **Default: agree usage windows before launch.**
8. **LLM feature proposer**: needs an API key and consent, since code and feature names leave the machine. **Default: off.**

Analysis scripts: `evolved_rules/analysis/gp7/stop7.py`, `evolved_rules/analysis/gp7/stop7b.py`. The investigators' reports are in `evolved_rules/plans/gp7-planning/`.