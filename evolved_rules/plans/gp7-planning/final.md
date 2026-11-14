# Final plan: gp-7 and cma-7, and closing gp-6/cma-6

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
- **New stop-rule simulation:** `evolved_rules/analysis/gp7/stop7.py` and `evolved_rules/analysis/gp7/stop7b.py`.

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
| **C3** | **Wall autopsy and decision bank.** Extend `autopsy.py`, which parses the per-vehicle `Obstacle` field in the autopsy only; it is not exposed to learners (PLAN decision 7). Play x0 (cma-1 3-tree and 5-tree) and 7fa4b2, 40 games on 3600-3639. Every 10 s, per shop, log: demand, reserved, overcrowded_for, its colour's cars by stage, per-car journey time against free-flow route cost (tracked across observations), stopped car-seconds split into junction, car-park gate and driving, coverage-target count, and tiles left. 20 more games on 3640-3659 record the **decision bank**: every decision's candidate feature matrix, globals, offers and light spots, tagged with seconds to failure (about 2.5–5k situations). From the bank, compute each term's spread within a decision: across candidates, across decisions, across offers and across spots. | 1–1.5 days | 60 (≈0.3 h) | Decides which moves C4 builds first (gate G1). Every live term must have finite, non-zero spread. |
| **C4** | **Planner v7: flag-gated moves and features** (`moves=v6|v7`; v6 stays byte-identical). (a) **Fast A\*** on simulated lane time: turns ×1.5/×3, entering a junction ×2, no 0.15 reuse discount. Kind flag `is_fast`. (b) **Bypass** candidates for connected house–shop pairs whose network route cost is ≥ 1.33× a fresh fast route. Only for the 3 shops with the lowest time-to-failure (ttf) when one is under 300 s, at most 8 per decision. Features `is_bypass`, `seconds_saved`. (c) **Relief route** to a second access cell, built **only if** C3 shows ≥ 50% of stopped time at car-park gates. (d) **Stress features:** per-shop margin (`margins()` split by catchment), `colour_busy_share`, `colour_idle_cars`, per-shop `ttf`; globals `demand_ramp` and `worst_ttf_inv`; candidate feature `target_ttf_inv`. ttf needs a **new per-shop pickup estimator** from demand decreases plus car-stage transitions; the current tracker only counts increases. Fallback stress features: `overcrowded_for` and demand per same-colour house. (e) **Pre-emptive trigger:** decide when min ttf < 200 s and it changed since the last decision. (f) **Failed-pair memory:** skip a (house, shop) pair for 60 s after a failed draw. (g) **Light-only place head**, written in-tree as `if_gt(pl_is_light, 0.5, <linear>, -1)` so roundabout spots never score above 0. Removal stays off (remove tree = −1). (h) **`flags:` line** in the canonical text (`flags: clean=0|1`), parsed by TreePolicy. It overrides the tree-count default, so it automatically becomes part of the cache key; texts without the line behave as before. `CODE_VERSION = "gp7-v1"`. | 3.5–4 days | 60 | Unit tests pass. **Identity tests:** (1) moves off: 20 games reproduce the gp6-v1 cache exactly (trips, seconds, command counts); (2) 3-tree cma-1 vs 5-tree `flags: clean=0` + remove −1 + place −1: identical games on 8 maps; (3) ttf: Spearman ≥ 0.5 against actual time to failure in the last 300 s on C3 data, else the fallback features replace ttf. **Smoke:** 24 games with moves on, 0 rejected draws, Python time per game up ≤ 25%. |
| **C5** | **Hand screens** (§2.2) | 0.5 day | 2,300 (≈8 h) | Inclusion rules in §2.2 |
| **C5m** | **Motorway prototype, only if the user approves on day 0.** It runs in parallel with C6 and is on the critical path (§2.3). | 3–4 days | 900 (≈3 h) | §2.3 |
| **C6** | **Learner code:** `linear.py`, `sepcma.py`, `slots.py`, `bank.py`, `evolve7.py`, `stats7.py`, plus the `gp.py` fixes (§9) | 4 days | 16 | cma-1 converted to live coordinates gives identical decisions on 100% of bank situations and identical trips on 8 maps. sepcma matches pycma `CMA_diagonal=True` within ±20% median evaluations on noiseless sphere, ellipsoid and linear functions (n = 70). 20k slot-tree mutations revert < 1%. |
| **C7** | **Mock evaluator, then real smoke runs.** The mock produces synthetic trips with policy SD 22–54, interaction SD 250–330, map SD 110 and collapse rate 5–20%. It checks the budget per generation, the stop-rule firing rates against §5.4, σ under mirroring with pairwise selection, the structure race, and exact kill/resume. The real smoke run does 2 generations per arm at λ = 6 and 4 maps, plus one structure race at 4+4 maps, with a forced kill and `--resume`. | 1 day | ≈300 (1 h) | Records after resume are byte-identical. Cost per generation within ±10% of design. Seeds ≥ 10000 behave normally. If more than 20% of gen-0 candidates are cut at σ0, halve σ0. |
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

### 2.2 Hand screens (C5): measure each factor separately

**Setup:**
- Every variant uses cma-1 route weights under gp7-v1, with the clean setting from C0.
- New kinds get a hand preference `priority += α·(is_fast + 3·is_bypass·seconds_saved/30)`.
- Light rule: `if_gt(pl_is_light, .5, pl_stopped_near, −1)`, plus an upgrade bonus of +0.8 on light offers.

**Round 1 (exploratory, used only to pick α).** 3200-3299, n = 100, 8 variants, 800 games:
- V0;
- V0 + clean on (the comparator: fast must beat what already exists);
- V0 + lights;
- V0 + kinds at α ∈ {0.5, 1, 2};
- V0 + trigger/memory;
- all-on.

**Round 2 (deciding).** 3300-3599, n = 300, 5 variants, 1,500 games:
- V0;
- V0 + lights;
- V0 + kinds (α from round 1);
- V0 + trigger/memory;
- all-on.

Each factor is judged by **its own paired contrast against V0 on round-2 maps only**. Paired SD for these relatives is about 250–300, so SE ≈ 16. The decision measure is mean trips: survival carries the same information, r 0.96–0.98. Median survival and S(1600) are reported but are not decision clauses.

**Inclusion rules** (each states the cut-off it implies):

| What | Included in both learners if… | What that means at SE ≈ 16 |
|---|---|---|
| Kinds (fast, bypass, relief) | one-sided p < 0.05, **and** the kinds-vs-clean contrast (round 1, descriptive) is not negative | estimate ≥ about +27 |
| Fixed planner changes (trigger, failed-pair memory; weights cannot switch them off) | estimate > 0 and one-sided p < 0.10 | estimate ≥ about +21 |
| Light head | Always included, so both learners have the same action set. x0 bias = never place, unless the lights contrast has p < 0.05, in which case the hand weights become x0. | ≥ about +27 to switch x0 |
| Stress features | Always included as weight-0 terms. They change nothing at weight 0, and C4 has validated ttf. | — |

Holm over the 3 tested factors is reported. The per-factor α is deliberately unadjusted: a falsely included kind costs little, because CMA can drive its weight to 0, while missing a real move is expensive.
- **Strong go:** any factor or all-on ≥ +100 trips with one-sided p < 0.01. Its hand weights become x0 for both learners.
- **No-go:** nothing passes (gate G3).

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

---

## 3. gp-7: Dynamic Feature GP (DF-GP)

The policy is a linear head tuned by sep-CMA plus **K = 8 fixed slots**. Each slot holds a small GP feature tree that can be gated on stress or game phase. "Dynamic" means three things:
- structure is replaced during the run, but only after a game test;
- terms can switch behaviour on predicted shop failure;
- the CMA covariance turns on only once there is signal.

### 3.1 Representation

```
priority(c) = Σ w_i·x_i(c) + Σ_{k=1..4} v_k·F_k(c,g)/s_k    x: 23 candidate terms (+is_clean iff clean=1) + adopted move kinds/features
hold(g)     = b + Σ u_j·g_j + Σ_{k=5,6} v_k·F_k(g)/s_k      g: 15 globals (x0 = hold_g − prio_g, which replays cma-1 exactly) + demand_ramp, worst_ttf_inv, max colour_busy_share
upgrade(o)  = Σ a_m·o_m + v_7·F_7(o,g)/s_7                  o: 8 offer terms (the 16 dead upgrade globals removed)
place(s)    = if_gt(pl_is_light, .5, b_L + Σ p_n·s_n + v_8·F_8(s,g)/s_8, −1)   s: pl_stopped_near, pl_max_wait_near, pl_mean_wait_near, pl_doorstep, pl_degree, pl_dist_worst_shop
```

- **Slot trees:** at most 15 nodes, depth at most 4. Primitives: add, sub, mul, protected div, min, max, neg, `if_gt`, and `gate(x, θ) = 1[x > θ]`. Terminals: that head's terms, the globals, and the stress and move features. Constants change by Gaussian steps (σ = 0.2·max(|c|, 0.1)), never by redraw.
- **s_k** is the slot's within-decision spread on the bank, frozen when the slot is filled.
- **Initial slots = 8 pre-registered templates, identical to cma-7's fixed interaction terms:**
  - priority: `mul(demand_ramp, path_cost_s)`, `mul(demand_ramp, is_separated)`, `mul(target_ttf_inv, seconds_saved)` (or `mul(target_ttf_inv, tiles_needed)` if no kind is adopted), `mul(stuck_cars, path_cost_s)`;
  - hold: `mul(demand_ramp, road_stock)`, `mul(worst_ttf_inv, unserved_houses)`;
  - upgrade: `mul(type_3, worst_overcrowded)`;
  - place: `mul(pl_stopped_near, worst_ttf_inv)`.
- **Size:** about 65–72 dimensions, constant.
- **Text:** the policy renders to 5-tree TreePolicy text with a `flags:` line (remove = −1). Engine, cache and evaluate work unchanged once C4(h) is in.

### 3.2 Inner loop (weights)

The inner loop is exactly cma-7's (§4.2–4.3). The recommendation is always the distribution mean.

### 3.3 Outer loop (structure): game-tested, every epoch of E = 5 generations

At the end of generations 4, 9, 14, …:

1. **Propose.** 600 trees across the slot heads, using a separate RNG stream so CMA draws stay aligned with cma-7:
   - 35% subtree or Gaussian-constant mutation of current or archived accepted slots;
   - 15% crossover between slot trees;
   - 15% gate wrapper `mul(gate(stress, θ), F)`, with stress ∈ {min ttf, target_ttf, colour_busy_share, demand_ramp} and θ from bank quantiles;
   - 10% interaction `mul(F, base_term)`;
   - 10% pre-registered templates;
   - 15% random depth-1–3 trees.

   Operator shares adapt deterministically to their **game-tested acceptance rate** (Laplace-smoothed).
2. **Bank screen** (0 games; phenotypic characterisation, Hildebrandt & Branke 2015). A proposal survives if all hold:
   - it is finite;
   - for priority and place slots, it varies within a decision in at least 10% of situations;
   - |r| < 0.9 with every active term;
   - at weight w0, it changes 3–40% of the bank's chosen actions, where w0 is the weight at which it changes 10%.

   Rank survivors by the share of changed decisions in the last 400 s before failure, minus the share in the first 600 s. Take the top 3, at most 2 per head.
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

- **x0:** the cma-1 final rule in live coordinates (clean setting from C0), plus hand weights after a strong go (C5) or a passed lights contrast. Slot weights start at 0.
- **Shared trunk.** gp-7 run k and cma-7 run k use the same sep-CMA seed and training-map stream. They are identical through generation 4, so generations 0–4 are run **once** as a shared trunk on 12 workers (about 1,610 games) and charged in full to **both** arms. Then the checkpoint and cache are copied and each arm resumes on 6 workers. gp-7's first structure race happens after the fork.
- **Budget and stop rule:** identical to cma-7 (§4.3, §5.4), in charged games. gp-7's structure races and bank refreshes come out of its own budget, so it reaches about gen 40 at the backstop where cma-7 reaches gen 45. That is the cost of the method, and it is reported.

---

## 4. cma-7: fixed-structure control, made strong

### 4.1 Search space

- The same heads, base terms and stress or move features as gp-7, plus **the 8 templates as fixed coordinates**: about 65–72 live dimensions.
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
- **Project headline rule:** one pick among {gp-7 final, cma-7 final, x0} by empirical-Bayes posterior on validation 1550-1749 (3 × 200 games). It is then tested once on 6100-6999, different maps, so the estimate is unbiased. This is the protection against drift. x0 is always a candidate, so a run that drifted downwards cannot lower the headline.
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
| C5 hand screens | 2,300 | ≈8 |
| C5m motorways (if approved) | 900 | ≈3 |
| C7 smoke | ≈300 | ≈1 |
| CRN pilot (optional, gp-8) | ≈1,400 | ≈3.5 |
| **Phase A: trunk + 2 arms to stop** (charged 8,000–14,800 each) | 14,400–28,000 | 48–93 (67–130 middle scenario; up to ≈185 if a strong go) |
| Validation (gp-7, cma-7 and x0 × 200) | 600 | ≈2–3 |
| Test battery: 4 policies × 1,000 (900 + 100) + ablation 600 + legacy 300 (hand is cheap) | ≈4,900 | ≈14–22 |
| **Total, 1+1** | **≈25–40k** | **≈4–7 days of machine time** |
| Total, 3+3 | ≈55–95k | ≈9–17 days |

### Day-by-day timeline

| Day | Date | Work |
|---|---|---|
| D0 | Fri Nov 14 | gp-6 stops about 04–07:00; start C0 on its 8 workers. cma-6 stops about 07–11:00; C0 gets all 12, done by afternoon, and the C1 lid-closed test runs during it. Disable `gp6-watchdog`. Create the `mm-gp7` worktree. Ask the user the decisions (motorways, 1+1 vs 3+3, CRN, the performance PR). Start C3 code. |
| D1 | Sat Nov 15 | C0 analysis and EXPERIMENTS.md entry. C2 harness, profiling and the two speedups. C3 games (60) in the evening. |
| D2–D5 | Nov 16–19 | C4, including the pickup estimator and the `flags:` line. Identity tests. Smoke (24 games). C5 round 1 on the evening of D5. |
| D6 | Nov 20 | C5 round 2 (1,500 games, overnight). C6 starts with `linear.py` and `sepcma.py`. C5m coding if motorways are approved. |
| D7–D9 | Nov 21–23 | C6 (`slots.py`, `bank.py`, `evolve7.py`, `stats7.py`, `gp.py` fixes). C5m games (900) if approved. G3 decision. |
| D10 | Nov 24 | C7 mock and smoke with kill/resume. C8 sign-off. **Trunk launch in the evening.** Add about 2–3 days if motorways pass and are integrated. |
| D10–D15 | Nov 24–29 | Trunk (≈5.5 h), fork, Phase A. G4 at gen 15. S2 and gp-8 coding meanwhile, but no CPU slots. |
| ≈D15–D17 | ≈Nov 29–Dec 1 | Validation, test battery, report. 3+3 (if pre-committed) adds about 7–11 days. |

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
| Lights, stress, trigger and kinds add +30–60 s at the wall | ≈30–40% | 1,040–1,150 | 1,040–1,180 | ≈10–20% (gated slots are GP's real chance) |
| A move breaks the wall (strong go; motorways raise this if approved) | ≈10% | 1,150–1,400 | 1,150–1,450 | ≈20–25% |

- **Convergence:** both runs reach the converged label with about 60–90% probability, depending on how long they keep improving. That would be the first real GP convergence in this project.
- **H2:** structure value is detectable if the slots are worth ≥ about 30 trips.

### Decision gates

| Gate | Trigger | Action |
|---|---|---|
| G0 (C2) | Replay harness passes on all 902 files; memo identity holds | Adopt; otherwise drop that change |
| G1 (C3) | Autopsy cause | Long journeys → fast/bypass first. Gates ≥ 50% → build relief. Idle cars while a shop starves → catchment features first. ttf Spearman < 0.5 → use the fallback features. |
| G2 (CRN) | Pilot r bounds | Adopt for gp-8 only |
| G3 (C5/C5m) | Inclusion rules | Strong go → new x0. **No-go:** if motorways are approved and untested, finish C5m first; if motorways fail or are not approved, launch anyway with the stated "tie" expectation (user decision 3) |
| G4 (gen 15) | Both tracking snapshots below x0 − 2 SE | Treat as a bug: pause and run an autopsy |
| G5 (stop) | §5.4 | Converged or budget; validation; test |
| Phase B | Only if pre-committed | Never gated on run 1 |

### Top risks and mitigations

1. **No headroom in the moves.** C3, C5 and C5m measure it before launch; the clean comparator; honest expectations given to the user beforehand.
2. **Noise swamps CMA.** Mean recommendation; 288 shared games per generation; mirrored pairs; preconditioning; the covariance freeze. CRN in gp-8.
3. **GP adds nothing.** Game-tested insertion; H2 measures it cleanly; "no structure value" is a reportable result.
4. **The new planner breaks behaviour or slows Python.** Flag-gated byte-identical v6 path; three identity tests; bypass capped at 8 per decision; memo with a full key.
5. **Bugs in sep-CMA or slots.** Cross-check against pycma; mock evaluator; unit tests for pickling, determinism and resets.
6. **Cost grows with quality.** Budgets in games; wall ranges by scenario.
7. **Sleep, crashes or the laptop being needed.** C1 test under load; watchdog; exact resume; downtime reported.
8. **The protocol change looks like moving the goalposts.** Pre-registration signed off before launch; continuity rows (1500-1549 plots, 7000-7099).

---

## 8. What would make this "far above baselines"

- **The arithmetic.** ≥ 1,300 trips means moving median death from about 1,430 s to about 1,630 s (+200 s ≈ +315 trips). The wall is a car-supply squeeze: cars per unit of demand fall from 6.5 to 4.8 between 1,000 and 1,600 s, then level off at 4.2–4.4. Getting past it pays heavily.
- **Search alone cannot get there.** The true spread near cma-1 is 22–54 trips. Search has produced 0 validated gains on f34, while one planner fix gave +154.
- **The bets, in order:**
  1. Moves that shorten round trips: fast and bypass routes (these must beat the existing clean mode), lights where cars stop, relief routes if gates dominate, and **motorways** (3× speed, no road stock, the most common offer in weeks 3–8; prototype now if approved).
  2. Acting 100–300 s before failure, through ttf features and the trigger.
  3. Stress-gated slots that only gp-7 can express, now inserted only after game evidence.
  4. Measurement that keeps a real +50 to +100 and rejects a lucky one: mean recommendation, 900-map test, single-use blocks.
- **Without a passing move, the honest expectation is a tie near cma-1.** This is said before launch.

---

## 9. Code changes (all in the gp7 worktree)

| File | Change |
|---|---|
| `evolved_rules/gp.py` | Replace `MAX_DEPTH = 6` (line 205; reverts at 482/499/537) with node limits per tree (slots ≤ 15 nodes, depth ≤ 4; full trees ≤ 250, soft height 12). Gaussian constant mutation instead of `mutEphemeral`. New terminals: `is_fast`, `is_bypass`, `seconds_saved`, `target_ttf_inv`, `demand_ramp`, `worst_ttf_inv`, `colour_busy_share`, `colour_idle_cars`, shop margin (and `is_motorway` if adopted). `gate` primitive. TreePolicy parses the `flags:` line, which overrides the defaults at lines 442-444. Immigrants dropped. |
| `evolved_rules/candidates.py` | Fast A* cost mode; `bypass` (and optional `relief`) kinds; kind flags; `moves=v6|v7`; `route_candidates` memo with the full key. |
| `evolved_rules/features.py` | Per-shop pickup estimator; per-shop margin by catchment; busy share; idle cars; ttf; `seconds_saved`; `demand_ramp`; fallback stress features. |
| `evolved_rules/agent.py` | ttf trigger; 60 s failed-pair memory; flag plumbing; bank-export hook. |
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
| Same moves; search over formulas only | Autopsy, then moves aimed at the wall, hand-screened per factor before evolving | Same throughput for every rule; shared wall; planner fix +154 vs search 0 |
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

1. **Protocol amendments**: new seed blocks, the paired-slope stop rule, the 900-map test with H1/H2, equal charged games including a shared trunk, and 6+6 concurrency after the trunk (a deviation from PLAN.md:238). **Default: approve.**
2. **Motorways** (excluded 2026-11-07): build the hand prototype now, on the critical path; included in gp-7 only if it passes the screen. **Default: yes**, because it is the largest unused move. It adds about 2–3 days if it passes.
3. **If no move passes C5/C5m**: launch gp-7/cma-7 anyway, expecting a tie, or hold and keep developing moves. **Default: launch** (about 3–4 machine-days) and say so in the report.
4. **Run count**: 1+1, about 4–7 machine-days, with run-to-run variance disclosed; or 3+3, about 9–17 days, with a method CI of ±90–200, pre-committed. **Default: 1+1.**
5. **CRN keyed streams**: propose them to Mohammad and the fidelity work as a default-off, training-only flag for gp-8. **Default: propose now; pilot only when the CPU is free; not in gp-7.**
6. **Simulator performance PR** (the dead LINQ at TrafficControl.cs:344-348): offer it upstream; private DLL until merged. **Default: yes.**
7. **Laptop availability**: docked, on AC, lid action "do nothing", from about Nov 24 to Dec 1 (longer for 3+3). **Default: agree usage windows before launch.**
8. **LLM feature proposer**: needs an API key and consent, since code and feature names leave the machine. **Default: off.**

Analysis scripts: `evolved_rules/analysis/gp7/stop7.py`, `evolved_rules/analysis/gp7/stop7b.py`. The investigators' scripts are in `<old-machine scratch folder>`.