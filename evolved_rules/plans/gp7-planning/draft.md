# Final plan: gp-7 and cma-7, and closing gp-6/cma-6

The plan builds on the core that four of the five candidate plans share: a CMA-tuned linear head, with GP adding a small, changing set of gated feature terms. It takes three things from the judges:
- **Order of work, from Plan 4:** diagnose the wall first, then add moves, then hand-screen them, then evolve.
- **Engine, from Plan 2:** one harness for both arms, with a fixed number of slots, and a lean critical path.
- **Inference rules, from Plan 1:** each run's final policy is fixed in advance as the distribution mean at stop, and the tracking block is used for monitoring only, never for selection.

Conflicts between the plans are resolved explicitly in the text, marked **[Resolved]**.

I ran no games, edited no repository files and changed no processes. I did three read-only checks:
- `gp.py:205` has `MAX_DEPTH = 6`, and taller trees are reverted at lines 482, 499 and 537.
- pycma's sep-CMA keeps its diagonal state inside the sampler and `sigma_vec` (`.venv/Lib/site-packages/cma/evolution_strategy.py:1305-1320, 1378`). Resetting one coordinate would mean hacking pycma internals, which matters for the slot design in §3.
- I ran a new Monte Carlo of the stop rule. The scripts are `<old-machine scratch folder>\final\stoprule.py` and `<old-machine scratch folder>\final\s2.py`.

---

## 1. Diagnosis: four root causes

**R1. The move set is the ceiling, not the formulas.** This is the biggest cause.
- **Score is survival time.** trips ≈ 1.283e-4·T^2.18, with R² 0.985–0.995.
- **Throughput while alive is the same for every rule.** cma-1, gp-4, the separated rule and even the hand rule all reach 47/175/~377/~686 trips at 300/600/900/1200 s.
- **Every rule dies at a shared wall at 1400–1600 s.** The risk of dying within 200 s there is 0.70–0.93.
- **Removing early deaths is worth almost nothing.** Removing every death before 1200 s is worth about +4.5 trips.
- **Surviving longer at the wall is worth a lot.** +100/+200/+300 s at the wall is worth about +146/+315/+496 trips.
- **Road stock is not the limit.** Games end with 66–95 tiles unused.
- **No move can shorten a route once it is connected.** `coverage_targets` (candidates.py:548-576) only proposes (house, shop) pairs that are not yet connected. The simulator dispatches the lowest-route-cost car (CityDemand.cs:335-341), and A* discounts existing road to 0.15 (candidates.py:26-27), so traffic funnels onto shared trunks.
- **Choosing among today's candidates is saturated.** A 29-node rule ties the 321-node cma-1 (1019.5 vs 1027.7). Ten cma-1 relatives have a true SD of about 23 trips.
- **The largest gain on f34 came from a planner fix** (+154 trips on 12 maps), not from search.

**R2. Chaos makes most decisions noise, and selection follows the noise.**
- **One random stream drives everything.** A single `SimulationRandom` (TrafficWorld.cs:76) serves parking picks (ContinuousJourneys.cs:44, TrafficControl.cs:648) and placement draws that depend on road tiles (OriginalPlacement.cs:118, 205).
- **Pairing on maps barely helps for unrelated rules.** They correlate per map at r ≈ 0.09–0.26, with paired-difference SD 370–530. Close relatives reach r ≈ 0.55–0.7 (paired SD about 230–300).
- **GP rankings are mostly noise.** Among decent rules, 8-map GP rankings are about 72% noise (reliability 0.28).
- **CMA rankings are pure noise from gen 5 on.** cma-6's split-half reliability is about 0, with F = 0.69.
- **Winner's curse in both runs:**
  - gp-6 hall-of-fame leads of +221 and +247 shrank to −8 and −94 on validation;
  - cma-6's best samples lose 99.5 trips from training to validation and average −42 against cma-1;
  - cma-6's incumbent of 1037 shrinks to about 1006 under empirical Bayes.
- **The stop rule has almost no power:** 4–14% for a true +30 to +50. No GP run has ever reached it.

**R3. Both learners are mis-built.**
- **GP:**
  - cma-1's priority tree has height 7, above MAX_DEPTH 6, so 99.8% of priority mutations revert. The strongest seed was frozen.
  - Constants are redrawn rather than stepped (mean jump 1.11 against mean |w| 0.59).
  - 40% of mutations hit the constant remove and place trees.
  - Random immigrants: 0 of 38 reached the racing top.
- **CMA:**
  - 34 of the 81 weights are dead or redundant (agent.py:117-123, 193-214).
  - Term scales differ by about 100×.
  - The full covariance learned nothing (condition number 1.17), and the mean random-walked (drift 6.44 against 5.8 for pure noise).
  - It validates the best sample instead of the distribution mean.
- **The comparison was unfair:**
  - CMA had no light or place head;
  - gp-6 played 2.4× as many games as cma-6;
  - cma-1's 1027.7 was played with clean routes on, while cma-6 plays with them off.

**R4. Throughput and operations.**
- About 450 games/h. The C# hosts use about 81% of busy CPU, and some of that work is provably dead (TrafficControl.cs:344-348).
- Per-game cost grows roughly ∝ trips^1.9.
- Sleep and host timeouts cost hours. Generations took 2–3.7 h.

---

## 2. Pre-work before any long run

**Ground rules:**
- All gp-7 code goes in a new git worktree (e.g. `C:\Projects\490 - Project\mm-gp7`) on branch `gp7`, created from the tip of gp6.
- **Do not touch branch gp6** until both runs show status `budget`. The gp6-watchdog resumes them from gp6 code, so edits there would silently change resumed behaviour.
- Commits follow standing practice: the user's identity, no attribution lines, no push.
- State the game count before any run of more than 20 games.

**[Resolved] Lean critical path vs. full infrastructure.** Judge 3 is right that the schedule risk is real. The launch path below contains only items with strong evidence and low risk. CRN, the deeper C# speedups and motorways are separate side tracks, and launch never waits for them.

### Critical path

| # | Item | Effort | Games | Go / no-go check |
|---|---|---|---|---|
| **C0** | **Close out gp-6/cma-6** (§2.1) | 0.5 dev-day | 1,400 | Always done |
| **C1** | **Operations hardening.** AC power. `powercfg /change standby-timeout-ac 0`; `powercfg /change hibernate-timeout-ac 0`; `powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0`, then `powercfg /setactive SCHEME_CURRENT` (the user runs these). Copy the watchdog script into a new `gp7-watchdog` task (restart cap 8 per 2 h; leaves `budget` and `converged` alone). Keep the 120 s host and 3600 s awake-game timeouts. At most 12 workers in total. | 1 h | 0 | A 2 h lid-closed idle test shows no suspend in the error log |
| **C2** | **Two safe speedups.** (a) Wrap TrafficControl.cs:344-348 in a check for not-OriginalReference (the values are unused on that branch, line 350). (b) Python: cache `route_candidates` per (network key, inventory[0:2], house id, target shop ids, clean). Profile first: time `TrafficHost.dll --verify-replay` on 20 f34 replays and run `dotnet-trace` on one ~1,900 s game. Load the simulator change as a private DLL through `EVOLVED_RULES_HOST_DLL` (host.py:52-57) and offer it upstream to Mohammad as a pure performance PR. | 1 dev-day | about 0.5 h of replays + 20 games | All 900 `runs/f34-*/replays` PASS with identical scores, and 20 games give identical command streams before and after the cache. If either fails, drop that change. Throughput is measured on a fixed 60-game benchmark. **All plans below assume 450 games/h; any speedup is a bonus.** |
| **C3** | **Wall autopsy and decision bank.** Extend `autopsy.py`. Play x0 (cma-1 3-tree and 5-tree) and 7fa4b2: 40 games on 3500-3539. Every 10 s, per shop, log: demand, reserved, overcrowded_for, its colour's cars by stage, journey time against free-flow route cost, stopped car-seconds at junctions vs car-park gates vs driving, coverage-target count, and tiles left. 20 more games on 3540-3559 record a **decision bank**: every decision's candidate feature matrix, globals, offers and light spots, tagged with seconds-to-failure (about 2.5–5k situations). From the bank, compute each term's within-decision spread: across candidates (priority), across decisions (hold), across offers (upgrade), across spots (place). | 0.5–1 dev-day | 60 | Decides which moves to build first (C4). Every live term must have finite, non-zero spread; dead terms are confirmed and dropped. The time-to-failure predictor (C4-d) must have Spearman ≥ 0.5 against actual time to failure in the last 300 s; otherwise redesign it before it becomes a feature. |
| **C4** | **Planner v7: moves and features, flag-gated** (`moves=v6|v7`; v6 stays byte-identical). (a) **Fast A\* cost mode** on simulated lane time: turns ×1.5/×3, entering a junction ×2, no 0.15 reuse discount, junction penalty above 0.5. Kind flag `is_fast`. (b) **Bypass candidates** for connected house–shop pairs whose network route cost (`features._shop_route_cost`) is ≥ 1.33× a fresh fast route (fresh ≤ 0.75 × current). Generated only for the 3 shops with the lowest time-to-failure when one is under 300 s, or when the coverage list is empty. At most 8 per decision. Features `is_bypass`, `seconds_saved`. (c) **Relief route** to a stressed shop's second access cell. **Built only if** C3 shows ≥ 50% of stopped time at car-park gates. (d) **Stress features:** per-shop margin (`margins()` at features.py:315 split by nearest-shop catchment); `colour_busy_share`; `colour_idle_cars`; per-shop `ttf` (see below); globals `demand_ramp` and `worst_ttf_inv`; candidate feature `target_ttf_inv`. (e) **Pre-emptive trigger:** decide when min ttf < 200 s and it has changed since the last decision (fixed, the same for both learners). (f) **Failed-pair memory:** skip a (house, shop) pair for 60 s after a failed draw. (g) **Light-only place head** for both learners. Roundabouts and road removal are off (−42.5 [−68.7, −20.7] on simulator .7; the remove tree never fired). `CODE_VERSION = "gp7-v1"`. | 3 dev-days | 20 | Unit tests pass. With moves off, 20 games reproduce the gp6-v1 cache exactly (trips, seconds, command counts). In a 24-game smoke run with moves on: 0 rejected draws, and Python time per game rises ≤ 25%. |
| **C5** | **Hand screens on dev maps** (§2.2) | 0.5 dev-day | 1,200 | Inclusion rules in §2.2 |
| **C6** | **Learner code:** `linear.py`, `sepcma.py`, `slots.py`, `bank.py`, `evolve7.py`, `stats7.py`, plus the `gp.py` fixes (list in §9) | 3–4 dev-days | 16 | cma-1 → live-coordinate text gives identical decisions on 100% of bank situations and identical trips on 8 maps (16 games). sepcma passes the tests in §4. Unit test: 20k slot-tree mutations, revert rate < 1%. |
| **C7** | **Mock evaluator + smoke runs.** The mock returns synthetic trips with the dossier's variance components (policy SD 22–54, interaction SD 250, map SD 110, collapse rate 5–20%). It checks the per-generation budget, the stop rule's firing rates, σ behaviour under mirroring, and exact kill/resume. Then a real smoke run: 2 generations per arm at λ = 6 and 4 maps, including a forced kill and `--resume`. | 1 dev-day | about 300 | Records after resume are byte-identical. Budget per generation matches the design within ±10%. σ0 broken-candidate check: if more than 20% of gen-0 candidates are cut at σ0 on dev maps, halve σ0 (decided before launch). |
| **C8** | **Pre-registration** `plans/2026-11-xx-gp7-cma7.md`: seed table, stop rule, budgets, inclusion rules, Holm family, test size, concurrency deviation | 2 h | 0 | The user signs off before launch |

**How ttf is defined (C4-d):**
- If the shop is overcrowded: ttf = 50 − overcrowded_for.
- Otherwise: with load ratio ρ = demand rate / delivery rate (from DemandTracker), ttf is the smallest t' at which ρ·ramp(t + t')/ramp(t) ≥ 1, capped at 600 s. Here ramp(day) = 1 + 0.013·max(0, day − 35) (CityDemand.cs:242).
- Terms use ttf_inv = 1/(1 + ttf/100).

### Side tracks (never block launch)

| # | Item | Effort | Games | Go / no-go |
|---|---|---|---|---|
| **S1** | **CRN keyed-stream flag**, training only. Reset field `randomStreams: "keyed"` (default `"shared"`, which stays bit-identical; SimulationChecks.cs:473-496 still passes). Keys: placement weight U(hash(seed, colour, kind, k-th spawn, x, y, layout)); grouping (colour, k); colour pick, double lot and upgrade target by plan-entry Order; offers and shuffle by week; demand phase by colour; parking on its own stream. SplitMix64 hash. Recorded in `AiReplayRecording`. Cache version `gp7-v1@2026-11-10.f34+crn`. Coordinate with Mohammad; the user already owns the fidelity side (fidelity-aya). | 1.5–2 dev-days | 760 pilot on 3600-3799 | **Pilot:** cma-1 × 200 seeds × both modes (400, paired by seed; TOST equivalence of means with margin ±50); 7fa4b2 and hand × 60 × 2 (240); chaos floor = cma-1 vs cma-1 with one extra 1 s wait at t = 0, × 60 × 2 (120). **Adopt** only if TOST passes and (r_unrelated ≥ 0.4 or chaos-floor r ≥ 0.75). **Deadline: launch day.** CRN is all-or-nothing for gp-7/cma-7, because runs are never resumed across modes. Miss the deadline and it moves to gp-8. Validation, selection and test games always run on standard f34. |
| **S2** | **Deeper C# speedups**, only if C2's profile shows them hot: leader search indexed by lane key (TrafficControl.cs:372-390, same visiting order); skip FinishRemovals when nothing is pending (TrafficWorld.cs:354-375); lazy `DisconnectedColorComponents` (TrafficWorld.cs:415) | 1 dev-day | 0 | 900 replays bit-exact. These can be swapped in at launch only, never mid-run (they are behaviour-identical, but the rule is kept simple). |
| **S3** | **Motorways.** Needs the user's approval; excluded 2026-11-07. Hand prototype: "one overpass per motorway offer, from the farthest same-colour cluster to the shop with the lowest ttf". Commands already exist (Program.cs:144-146; AiReplay.cs:85). | 3–4 dev-days | 400 on 3800-3999 | If median survival rises ≥ +50 s, it becomes gp-8 (or gp-7.1) as one more candidate kind. It does not delay gp-7. |
| **S4** | Optional LLM feature proposer for the slot pool | — | shares the budget | Off by default. Needs the user's consent and an API key. Reported separately. |

### 2.1 Closing gp-6 and cma-6 (C0)

1. Let both runs reach max_gens 15. They end with status `budget` (evolve.py:415-416). Then **disable the gp6-watchdog task**. Never resume either run.
2. Log both in EXPERIMENTS.md, every generation with the validated best next to the population average. Label them **budget, not converged**, and state:
   - gp-6 played 2.4× cma-6's games (4,294 vs 1,801); the matched-games comparison is gp-6 at about gen 4–5 against cma-6 at gen 15;
   - gp-6's incumbent was the cma-1 seed for the whole run;
   - cma-6's 1037 is a best-of-10 that shrinks to about 1006 (paired +9 ± 36 against cma-1);
   - the MAX_DEPTH bug froze cma-1's priority tree;
   - the clean-routes mismatch.
3. Extract the cma-6 final distribution mean (`es.mean`) from its checkpoint as a 3-tree text.
4. **Close-out battery on 5100-5299** (n = 200, never played), run from the gp6 worktree with gp6-v1 code before any behaviour change. 7 policies:
   - cma-1 5-tree (clean on; the gp-6 incumbent)
   - cma-1 3-tree (clean off)
   - cma-6 final mean
   - cma-6 incumbent 3d999a2c
   - 7fa4b2 (29 nodes)
   - hand
   - separated

   That is 1,400 games, about 3.3 h overnight. Report paired differences against cma-1 5-tree (BCa, paired-t, Holm over 4 comparisons) and the map / interaction / policy ANOVA under the fixed planner. This settles four things:
   - (a) the gp-6/cma-6 result;
   - (b) **clean routes are on for both learners iff (5-tree − 3-tree) ≥ 0**;
   - (c) whether unrelated rules correlate better under the fixed planner;
   - (d) gp6-v1 baselines.
5. The close-out policy with the highest empirical-Bayes estimate becomes the **legacy row** in the gp-7 test battery. There is no separate test, so the test set is used once.

### 2.2 Hand screens (C5): diagnosis before evolution

All variants use cma-1 route weights under gp7-v1 code. New kinds get a fixed hand preference: `priority += 1.0·is_fast + 3·is_bypass·(seconds_saved/30)`. The light rule is `if_gt(pl_is_light, .5, pl_stopped_near, −1)`, plus an upgrade bonus of +0.8 on light offers.

- **Round 1 (picking)**, 3200-3299, n = 100, 6 variants, 600 games:
  - V0 = x0 with moves off;
  - V1 = V0 + lights;
  - V2 = V0 + fast/bypass;
  - V3 = V2 + trigger + failed-pair memory;
  - V4 = V3 + lights;
  - V5 = V4 + relief (only if built).
- **Round 2 (deciding)**, 3300-3499, n = 200, fresh maps: V0 against the best two variants, 600 games. **Decisions use round 2 only**, so they are not inflated by round 1's pick.
- **Measures:** paired mean trips (BCa), median survival seconds, S(1600), collapse rate, wall time per game.

**Inclusion rules [Resolved: Judge 1's objection to weak bars wins for kinds, which add dimensions and behaviour; features stay cheap]:**

| What | Included in both learners if… | Excluded if… |
|---|---|---|
| Candidate kinds (fast, bypass, relief) | Paired diff ≥ +20 with one-sided p < 0.1, **or** median survival ≥ +20 s, with collapse rate up ≤ 3 points | Anything else. They add dimensions without evidence. |
| Fixed planner changes (trigger, failed-pair memory) | Point estimate ≥ 0 and 90% CI lower bound > −40 | Otherwise |
| Light head | Always included (it is the fairness piece). x0 bias = never place, unless lights are ≥ +20, in which case the hand-rule weights become x0 | Only if significantly negative |
| Stress features | Always included as weight-0 terms. They change nothing at weight 0, and C3 validated ttf. | — |

- **Strong go:** any variant ≥ +100 trips or ≥ +60 s median survival. Its hand weights become x0 for **both** learners, and it is the headline.
- **No-go (nothing positive):** still launch, with expectations cut to "about cma-1 ± 5%". Tell the user before launch and put the motorways decision to them (S3).

---

## 3. gp-7: Dynamic Feature GP (DF-GP)

The policy is a CMA-tuned linear head plus **K = 8 fixed slots**. Each slot holds a small GP-evolved feature tree that can be stress- or phase-gated. It is dynamic in three ways: the structure is replaced during the run, terms can switch behaviour on predicted shop failure, and the number of maps adapts to measured noise.

### 3.1 Representation

```
priority(c) = Σ w_i·x_i(c)  + Σ_{k=1..4} v_k·F_k(c,g)/s_k     x: 23 candidate terms (+is_clean iff clean on) + adopted move terms
hold(g)     = b + Σ u_j·g_j + Σ_{k=5,6}  v_k·F_k(g)/s_k       g: 15 globals (x0: hold_g − prio_g) + demand_ramp, worst_ttf_inv, max colour_busy_share
upgrade(o)  = Σ a_m·o_m     + v_7·F_7(o,g)/s_7                 o: 8 offer terms (the 16 dead upgrade globals are removed)
place(s)    = b_L + Σ p_n·s_n + v_8·F_8(s,g)/s_8               lights only: pl_stopped_near, pl_max_wait_near, pl_mean_wait_near, pl_doorstep, pl_degree, pl_dist_worst_shop
```

- **Slot trees:** at most 15 nodes and depth at most 4. Primitives: add, sub, mul, protected div, min, max, neg, `if_gt`, plus `gate(x, θ) = 1[x > θ]`. Terminals: that head's terms, the globals, and the stress and move features. Constants step by Gaussian moves (σ = 0.2·max(|c|, 0.1)), never by redraw.
- **Normalisation:** s_k is the slot's within-decision spread on the bank, frozen when the slot is filled. So weight steps mean the same thing in every coordinate.
- **Initial slots = the 8 interaction templates that cma-7 has as fixed terms** (pre-registered now, chosen on domain reasoning, not from data):
  - priority:
    - `mul(demand_ramp, path_cost_s)`;
    - `mul(demand_ramp, is_separated)`;
    - `mul(target_ttf_inv, seconds_saved)` if bypass or fast is adopted, else `mul(target_ttf_inv, tiles_needed)`;
    - `mul(stuck_cars, path_cost_s)`;
  - hold: `mul(demand_ramp, road_stock)` and `mul(worst_ttf_inv, unserved_houses)`;
  - upgrade: `mul(type_3, worst_overcrowded)`;
  - place: `mul(pl_stopped_near, worst_ttf_inv)`.

  Exact terminal names get matched to gp.py's lists in C6.
- **Size:** about 65–72 dimensions in total, constant for the whole run.
- **Text:** the policy renders to ordinary TreePolicy text (4-tree layout; remove = −1), so `agent.py`, the cache and `evaluate.py` are unchanged.
- **[Resolved] Fixed slots vs. growing dimension.** Fixed slots won (Judge 3). Replacing a slot resets one coordinate instead of restarting the ES, and the CMA RNG stays aligned with cma-7.

### 3.2 Inner loop (weights): identical to cma-7 (§4.2)

The recommended policy is always the **distribution mean**.

### 3.3 Outer loop (structure): every epoch of E = 5 generations, 0 games

1. **Score each slot:**
   - signal ratio I_k = |m_k| / (σ·√C_kk);
   - effect e_k = |m_k|·(normalised spread), measured on the bank.
2. **Free a slot** if it is at least 2 epochs old and, for 2 epochs in a row, I_k < 1 and e_k < 5% of the head's largest term effect. Free at most 2 slots per epoch. Because e_k is tiny, removing the term barely changes the mean policy. The freed tree goes to the archive.
3. **Propose 200 trees per freed slot.** Proposals use a separate RNG stream, so the CMA draws stay aligned with cma-7.
   - 35% subtree mutation or Gaussian-constant mutation of surviving or archived high-I slots;
   - 15% crossover between slot trees;
   - 15% gate wrapper `mul(gate(stress, θ), F)`, with stress drawn from {min ttf, target_ttf, colour_busy_share, demand_ramp} and θ from bank quantiles;
   - 10% interaction `mul(F, base_term)`;
   - 10% pre-registered templates;
   - 15% random depth-1–3 trees.
   - Operator shares adapt by credit (whether the slot survives 2 epochs with I > 1), deterministically.
4. **Screen on the decision bank** (phenotypic characterisation, Hildebrandt & Branke 2015). Keep a proposal only if all hold:
   - it is finite;
   - for priority and place slots, it varies within decisions in at least 10% of situations;
   - |r| < 0.9 with every active term;
   - adding it at ±1 normalised unit to the current mean changes 3–40% of the bank's chosen actions.

   Rank the survivors by the share of changed decisions that fall in the **last 400 s before failure**, minus the share in the first 600 s. That targets the wall. Ties go to the smaller tree.
5. **Insert** the winner at m_k = 0, set its variance to the initial step, and zero its evolution-path entries.
6. **Bank refresh** every 3 epochs: the current mean plays 10 recording games on 3560-3599, cycling through that block. These games are charged to gp-7.
7. **Structure-value monitor** (Plan 5) every 2 epochs: the mean against the same mean with all v_k = 0, on 32 fresh probe maps from the probe stream (64 games, charged to gp-7). This is logged as the direct in-run measure of GP's added value. **G6:** if it is ≤ 0 at 3 consecutive checks, freeze the slots. gp-7 then becomes cma-7 plus whatever slots it has, and "no structure value" is a reportable result.

### 3.4 What is not in gp-7, and why

- No hall of fame, reference subtraction, 8-map tournament or racing: 8-map rankings are 72% noise, and subtraction adds +38% variance.
- No immigrants: 0 of 38 reached the racing top.
- No lexicase: per-map r ≈ 0.2.
- No separate tree-GP arm: it is unaffordable at ≥ 3 runs. The `gp.py` fixes keep it possible for gp-8.

### 3.5 Seeds, initialisation, budget, stop rule

- **x0** = the cma-1 final rule in live coordinates (clean setting from §2.1), plus the hand weights if C5 gave a strong go. Slot weights start at 0.
- **The same x0 as cma-7.** gp-7 run k and cma-7 run k share the sep-CMA seed and the training-map stream, so they are identical until the first slot replacement (gen 5 at the earliest). The run-level difference is sharply paired.
- **Budget, maps and stop rule** are identical to cma-7 (§4.3, §5.4). gp-7's extra games (structure monitor about 6.4 per generation, bank refresh about 0.7 per generation) come out of its own budget.

---

## 4. cma-7: fixed-structure control, made strong

### 4.1 Search space

The same heads and base terms as gp-7, plus the **same 8 interaction terms as fixed coordinates**: about 65–72 live dimensions.
- The 34 dead or redundant weights are removed: 16 upgrade globals, the 16 priority globals (folded into hold as hold_g − prio_g, which replays cma-1 exactly), `pending_refunds`, and `is_clean` when clean routes are off.
- The comparison therefore asks exactly one question: does **searched** structure beat **hand-chosen** structure on identical inputs, actions, x0, maps and budget? That is PLAN.md's control definition.

### 4.2 Algorithm (shared engine `sepcma.py`, used by both arms)

**[Resolved] In-house sep-CMA vs. pycma.** I chose an in-house sep-CMA-ES: Ros & Hansen 2008 diagonal update plus CSA, about 250 lines of numpy. pycma keeps sep-mode state in its sampler and `sigma_vec`, so a one-coordinate reset would need fragile internal hacks that also risk checkpoint pickling. The in-house engine is checked against pycma `CMA_diagonal=True` on noiseless sphere, ellipsoid and linear functions (n = 70): median evaluations to target must be within ±20% of pycma's.

- **Preconditioning:** per-coordinate initial std ∝ 1/spread from the bank (median 1, clipped to [0.1, 10]). Samples are clipped at ±8 std-units.
- **σ0** is calibrated on the bank so that the median sample changes 25–35% of the bank's decisions, then checked in C7 for broken candidates.
- **λ = 24 as 12 mirrored pairs** (antithetic, on identical maps), with **pairwise selection** (only the better of each pair enters recombination, μ = 6 weighted). This avoids the known step-size bias of unconditional mirroring; Auger, Brockhoff & Hansen, GECCO 2011, cited from memory. If the mock check in C7 shows σ behaving differently from unmirrored sampling by more than 20%, mirroring is switched off for both arms before launch.
- **Rank-based tell** on mean trips over the generation's shared maps. Do not use log, median, seconds, trips per tile or q25: no gain, or harmful.
- **No UH-CMA-ES σ inflation and no IPOP/BIPOP restarts.** Noise is always detected here, and σ cannot converge under it.
- **Mean learning rate:** c_m = 1. Pre-registered switch to 0.5 only if split-half reliability stays below 0.05 at the maximum map count for 5 generations.

### 4.3 Generation protocol (both arms)

1. **Maps:** m = 12 fresh training maps from 1-999, a deterministic function of (run seed, generation), shared by all candidates and the mean.
2. **Early cut:** after the first 4 maps, a candidate whose mean is below 0.6 × the generation's median 4-map mean stops. It is ranked below all survivors, in order of its 4-map mean. The pair partner continues.
3. **Mean games:** `text(es.mean)` plays the same 12 maps. These games are not told to CMA; they are the low-noise monitor, and the population average is reported next to them.
4. **Noise monitor:** split-half rank reliability is logged every generation (35 deterministic 6-vs-6 splits).
   - If the 3-generation moving average is below 0.15: m goes 12 → 16 → 24.
   - If it is above 0.5: m goes down to 8.
   - The rule is deterministic, so resume stays exact.
5. **Guard** [Resolved: this replaces Plan 2's elitist-mean safeguard, which used the tracking block for selection; Judge 2]. Every 10 generations, the current mean and the mean accepted at the previous guard play 50 **fresh probe maps** (100 games). If the current mean is worse at one-sided p < 0.05, the full policy state (weights and slot trees) resets to the previous guard's; σ and C are kept. The comparison is sequential, never against a maximum, and on maps never reused. The tracking block stays clean.
6. **Cost per generation:** about 274 candidate games + 12 mean + 30 tracking + 10 guard ≈ **326** for cma-7, about 333 for gp-7. That is about 44 generations in the 14,500-game backstop.

---

## 5. Evaluation protocol

### 5.1 Seed blocks (pre-registered; confirm with Mohammad that none were played on f34)

| Use | LA seeds | Mode |
|---|---|---|
| Training (stream k shared by gp-7 k and cma-7 k) | 1-999 | CRN if adopted, else standard |
| Hand screens | 3200-3499 | standard (gp7-v1) |
| Autopsy, bank, bank refresh | 3500-3599 | standard |
| CRN pilot | 3600-3799 | both |
| Motorway prototype (if approved) | 3800-3999 | standard |
| **Tracking block** (stop rule and plots only; never selects) | **2100-2249 (150)** | same as training |
| Guard and structure-monitor probes (fresh, consumed by counter, never reused) | 10000-19999; run k uses 10000+3000(k−1) onward | same as training. The smoke run checks that seeds ≥ 10000 behave normally. |
| gp-6/cma-6 close-out | 5100-5299 | standard, gp6-v1 |
| **Validation at stop** (each run's mean vs x0; replicate gate) | 1550-1749 (200), once per run | standard |
| Final selection (project headline rule, only with 3+3 runs) | 4200-4599 (400) | standard |
| **Primary test** | **6100-6599 (500)** | standard, `--verify` with an f34-built verifier |
| Continuity row | 7000-7099 | standard |
| Reserved for PPO head-to-head | 8100-8199 | — |
| Retired for decisions | 1500-1549 | continuity plots only |

### 5.2 Winner's curse controls

- Both learners recommend the distribution mean, which averages hundreds of games. No best sample is ever promoted, and no maximum of noisy validations is taken.
- **The method comparison is fixed in advance: each run's final policy is the mean at stop.** No selection among snapshots or candidates.
- The tracking block monitors and never selects. Validation 1550-1749 is used once per run.
- **Project headline rule** (the "best rule" for the report):
  - with 3+3 runs: picked once on 4200-4599 among the 6 finals and x0 by empirical-Bayes posterior. Its test score comes from the battery, on different maps from the pick, so it is unbiased;
  - with 1+1 runs: the final with the higher empirical-Bayes validation estimate (two candidates, stated in advance).
- Any per-rule number quoted in-run is shrunk by empirical Bayes, with s_pol and s_int re-estimated from that run's ANOVA.

### 5.3 Statistics

- PLAN.md:201-209: paired mean difference, BCa bootstrap (10,000 resamples), paired-t 95% CI, two-sided Wilcoxon.
- Holm correction over the fixed family:
  - gp-7 vs cma-7;
  - gp-7 vs hand;
  - cma-7 vs hand;
  - gp-7 vs x0 (cma-1 under gp7-v1);
  - cma-7 vs x0;
  - headline rule vs the legacy close-out pick.
- **Success (PLAN.md:188):** gp-7 final beats the hand rule and the cma-7 final, each with a paired 95% CI excluding 0.
- **Minimum detectable effect at n = 500:** about 56 trips for unrelated rules (SD 450) and about 31–44 for gp-7 vs cma-7 (relatives from the same x0, SD 250–350).

### 5.4 Stop rule (both arms; achievable, and it means a stated plateau)

- **Snapshots:** the mean plays the tracking block (150 maps) at gen 0 and every 5 generations. Independent snapshot noise is about 14.5 trips.
- **Converged** when g ≥ 25 and the OLS slope over the last 5 snapshots (a 20-generation span) has a **one-sided 80% upper bound below 2 trips per generation**.
- **Backstop:** 14,500 charged games. Stopping there gives status **budget**.
- **Simulated behaviour** (`s2.py`, 2,000 reps, backstop at gen 44):

| True curve | P(labelled converged) | Median generation when it fires |
|---|---|---|
| Flat | 99.8% | 25 |
| Rises to gen 15, then flat | 97% | 35 |
| Rises to gen 25, then flat | 65% | 40 |
| +2 trips/gen throughout | 54% (ambiguous by design) | — |
| +4 trips/gen throughout | 0.5% (false convergence) | — |

- **Reported as:** "converged: no sustained gain ≥ 4 trips/gen detectable (≈ 60 trips over 15 gens)". Logged as supporting evidence but **not** stop conditions: σ trajectory, split-half reliability, F (Plan 4's "cannot distinguish own candidates at maximum maps"), structure-monitor values.
- **At stop:** the final mean against x0 on validation 1550-1749. x0 is played once and cached; 200 + 200 games per run, charged outside the run budgets, equally for both arms.
- `budget` and `converged` are always separate labels.

### 5.5 GP vs CMA, equal budgets, and the ≥ 3-runs rule

- **Budget:** equal **charged simulated games** (14,500 per run). Cache hits count 0 for both. Games, cache hits and CPU-hours are reported per method. Curves use games on the x-axis, with the population average next to the mean or snapshot in every recap.
- **Concurrency:** 6 + 6 workers at the same time. Games are deterministic per (code, simulator, mode, text, seed), so running side by side cannot bias results. This deviates from PLAN.md:238's "not alongside" wording, which was about wall-clock budgets, so it **needs the user's approval**.
- **Phase A:** run 1 of each method.
- **Phase B:** runs 2 and 3 of each, at the same budget, if gate G-rep (§7) passes on **validation** (never on test), or if the user wants the method claim regardless.
  - Run 1 is reported separately, and the gating is disclosed.
  - Method effect = the mean over k of (gp-7_k − cma-7_k) on the test block, plus a mixed model trips ~ method + (1|run) + (1|map). With df = 2, the run-level CI is wide, and the report says so.
- **Without Phase B:** declared a single-run comparison, with run-to-run variance unmeasured (PLAN.md:203).
- **[Resolved] Replicates.** Gated on validation, as Judge 2 requires: never on test, and the test block is never re-looked at.

---

## 6. Compute budget and schedule

**Throughput:** 450 games/h on 12 workers. Add +30% wall time for cost growth if policies reach about 1,200–1,300 trips (wall time ∝ trips^1.9). Speedups are a bonus: a 1.4–1.7× Amdahl bound, because Python is about 19% of CPU.

| Stage | Games | Hours at 450/h | Notes |
|---|---|---|---|
| C0 close-out | 1,400 | 3.3 | overnight, gp6-v1 code |
| C2/C3/C4/C6 checks | about 120 | 0.3 | |
| C5 hand screens | 1,200 | 2.7 | |
| C7 smoke | about 300 | 0.7 | |
| S1 CRN pilot (optional) | 760 | 1.7 | |
| **Phase A:** gp-7 r1 ∥ cma-7 r1 (expected 9–14.5k each) | 18,000–29,000 | 40–64 (52–84 with cost growth) | 6 + 6 workers |
| Validation at stop (2 × 200 + x0 200) | 600 | 1.3 | |
| Phase B (if gated): 2 more pairs | 36,000–58,000 | 80–130 (105–170) | |
| Final selection (3+3 only; 7 × 400) | 2,800 | 6 | |
| Test battery: finals + x0 + hand + separated + legacy, × (500 + 100 continuity) | 3,600 (1+1) / 6,000 (3+3) | 8 / 13 | hand and separated are cheap |
| **Total, 1+1** | **about 27–37k** | **about 3–4.5 days** of machine time | |
| **Total, 3+3** | **about 67–100k** | **about 7–11 days** (about 5–7 with speedups) | |

### Day-by-day timeline (today 2026-11-13; gp-6/cma-6 reach gen 15 about 8 h from now)

- **Day 0 (night of 13th–14th):** both runs reach `budget`. Disable gp6-watchdog. Create the `mm-gp7` worktree and branch `gp7`. Start the C0 battery overnight from the gp6 worktree. User runs the powercfg commands (C1).
- **Day 1:** C0 analysis and EXPERIMENTS.md entry. C2 profiling and the two safe speedups, with the 900-replay check. Write the C3 instrumentation and run the autopsy and bank (60 games) by evening. Send the CRN proposal (S1) to Mohammad.
- **Day 2:** C4 stress features plus ttf (validated on C3 data), fast A*, bypass, and the moves-off identity test (20 games). The autopsy decides whether relief routes get built.
- **Day 3:** C4 trigger, failed-pair memory, light head. Smoke (24 games). Hand-screen round 1 (600 games) in the evening. Start `linear.py`.
- **Day 4:** hand-screen round 2 (600 games, deciding). `sepcma.py` plus the pycma cross-check. `slots.py`, `bank.py`. Fix x0 and the term set.
- **Day 5:** `evolve7.py`, `stats7.py`, mock evaluator. Pre-registration document and user sign-offs. CRN pilot only if S1 is ready (deadline).
- **Day 6:** real smoke run with kill and resume, plus the σ0 check (about 300 games). **Launch Phase A in the evening.**
- **Days 6–10:** Phase A. G4 check at gen 15 (§7). Side tracks S2 and S3 coded meanwhile, but no CPU slots during the runs.
- **About day 10:** validation at stop, gate G-rep. Either Phase B (days 10–17) or straight to the test battery (about 0.5 day). Final report.

### Operational safety

- AC power, no sleep or hibernate, lid set to "do nothing".
- gp7-watchdog with `--resume` only; resume is exact. Checkpoints store the CMA state, both RNG streams, slot trees, archive, bank version, map-count state, the guard reference and the ledger.
- The adaptive rules (map count, slot replacement, guard, structure freeze) are pure functions of cached results and RNG state. This is tested in C7.
- Never resume across code, simulator or CRN modes; the cache key includes the mode.
- At most 12 workers (CoreCLR failed at about 1 GB free).
- Bump CODE_VERSION on any behaviour change.
- Budget in games; the hours backstop counts only checkpointed time.

---

## 7. Expected outcomes, gates, risks

### Honest ranges (my judgement; fresh test maps; x0 ≈ 990–1030)

| Scenario (from C5) | Probability | cma-7 final | gp-7 final | P(gp-7 > cma-7, CI excludes 0) |
|---|---|---|---|---|
| No move passes | about 35% | x0 −10 to +40 (mean recommendation removes the −42 sample loss) | cma-7 ± 30 | about 10% |
| Stress, trigger, lights and fast/bypass add +30–60 s at the wall | about 45% | 1,040–1,150 | 1,040–1,180 | about 20–25% (gated slots are GP's real chance) |
| A move breaks the wall (strong go; motorways in gp-8 if approved) | about 15–20% | 1,150–1,400 | 1,150–1,450 | about 25–30% |

- **Convergence:** both runs reach the stop rule between gen 25 and 44 with about 70–95% probability. That would be the first real GP convergence in the project.

### Decision gates

| Gate | Trigger | Action |
|---|---|---|
| G0 (C2) | 900 replays bit-exact | Adopt that speedup; otherwise drop it |
| G1 (C3) | Autopsy cause | Length → fast/bypass first. Gates ≥ 50% → build relief. Idle cars while a shop starves → per-shop catchment features first. ttf Spearman < 0.5 → fix ttf before it becomes a feature. |
| G2 (S1) | TOST pass and r threshold met by launch day | CRN for training, tracking and probes. Otherwise standard mode (m starts at 12 as designed) and CRN moves to gp-8. |
| G3 (C5) | Inclusion rules (§2.2) | Strong go → hand weights become x0. No-go → launch with reduced expectations and put the motorway decision to the user. |
| G4 (gen 15) | Both tracking curves below x0 − 2 SE | A bug, not search: pause and run an autopsy |
| G6 (gp-7) | Structure monitor ≤ 0 at 3 checks in a row | Freeze the slots; report "no structure value" |
| G-rep (validation at stop) | max(gp-7, cma-7) − x0 ≥ +40, or \|gp-7 − cma-7\| ≥ 30 on 1550-1749 | Run Phase B. Otherwise report the single run and spend the compute on moves (motorways if approved) → gp-8. |

### Top risks and mitigations

1. **No headroom in the moves, so everything ties cma-1.** C3 and C5 measure this before 50+ h of runs; G3 escalates; motorways (S3).
2. **Noise still swamps CMA.** Mean recommendation, λ·m = 288 games per generation, map doubling, mirrored pairs, preconditioning, the guard. CRN if it passes.
3. **The new planner breaks behaviour or slows Python.** The flag-gated v6 path is byte-identical; bypass is capped at 8 and generated only under stress; route cache; rejected-draw counts logged.
4. **Bugs in the in-house sep-CMA.** Cross-check against pycma, mock evaluator, unit tests (pickling, determinism, coordinate reset).
5. **Slot churn destabilises the search.** At most 2 replacements per epoch, a 2-epoch minimum age, insertion at weight 0, one-coordinate resets, the G6 freeze.
6. **Per-game cost rises with quality.** Budgets in games; +30% wall margin.
7. **Simulator coordination stalls.** Private DLL; CRN optional with a hard deadline; reporting always on standard f34.
8. **Sleep or crashes.** C1, watchdog, exact resume.
9. **The protocol change looks like moving the goalposts.** Pre-registration signed off before launch; the 7000-7099 continuity row kept; `budget` and `converged` kept distinct.

---

## 8. What would make this "far above baselines"

- **The arithmetic.** "Far above" (≥ 1,300) means moving median death from about 1,430 s to about 1,630 s (+200 s ≈ +315 trips). Cars per unit of demand level off at about 4.2–4.4 after about 2,000 s, so getting past the wall pays heavily.
- **Search alone cannot do it.** Near cma-1 the true between-policy SD is 22–54 trips, and very different rules tie. Search has produced 0 validated gains on f34; one planner fix produced +154.
- **So the bets are, in order:**
  1. moves that shorten round trips under the demand ramp: fast/bypass routes, lights where cars stop, relief routes if gates dominate, then motorways (approval needed; the largest unused move: 3× speed, no road stock, the most frequent offer in weeks 3–8);
  2. acting 100–300 s before the failure, through ttf features and the trigger;
  3. stress-gated slots that only gp-7 can express;
  4. measurement good enough to keep a real +50 to +100 and reject a lucky one (mean recommendation, a 150-map tracking block, a 500-map test, CRN if it passes).
- **Without a passing move in C5,** the honest expectation is a tie near cma-1. Say so before launch.

---

## 9. Code changes (all in the gp7 worktree)

| File | Change |
|---|---|
| `evolved_rules/gp.py` | Replace `MAX_DEPTH = 6` (line 205; reverts at 482/499/537) with per-tree node limits (slot trees ≤ 15 nodes and depth ≤ 4; full trees ≤ 250 with soft height 12). Gaussian constant mutation instead of `mutEphemeral`. Add terminals: `is_fast`, `is_bypass`, `seconds_saved`, `target_ttf_inv`, `demand_ramp`, `worst_ttf_inv`, `colour_busy_share`, `colour_idle_cars`, per-shop margin. Add a `gate` primitive. Drop immigrants. Tree choice weighted by usefulness. |
| `evolved_rules/candidates.py` | Fast A* cost mode (lane time, turn and junction multipliers, no 0.15 reuse discount); `bypass` kind (≥ 1.33× ratio, top-3 stressed shops, ≤ 8 per decision); optional `relief` kind; kind flags; `moves=v6|v7` gating; `route_candidates` cache. |
| `evolved_rules/features.py` | Per-shop margin by catchment; busy share; idle cars; ttf from DemandTracker and ramp; `seconds_saved`; globals `demand_ramp` and `worst_ttf_inv`. |
| `evolved_rules/agent.py` | Pre-emptive ttf trigger; 60 s failed-pair memory; light-only place head with roundabouts and removal off; flag plumbing. |
| `evolved_rules/engine.py` | `CODE_VERSION = "gp7-v1"`; cache key includes the simulator mode (`+crn`); per-run charged-games ledger hook. |
| `evolved_rules/autopsy.py` | Wall instrumentation, per-decision spreads, bank export. |
| `evolved_rules/bank.py` (new) | Bank storage and loading, spreads, decision-change rate, σ0 calibration. |
| `evolved_rules/linear.py` (new) | Live-coordinate parameterisation, x0 from cma-1 (hold_g − prio_g), slot embedding and normalisation, TreePolicy text writer. |
| `evolved_rules/sepcma.py` (new) | sep-CMA-ES with CSA, mirrored pairs and pairwise selection, per-coordinate init and reset, clipping, picklable state. |
| `evolved_rules/slots.py` (new) | Slot scoring, freeing, proposals (own RNG), bank screen, archive, credit-adapted operator shares. |
| `evolved_rules/evolve7.py` (new) | Unified loop `--slots 8|0`: maps, early cut, mean games, noise monitor, guard, tracking, structure monitor, stop rule, ledger, checkpoint and resume. |
| `evolved_rules/stats7.py` (new) | Empirical Bayes, paired-t, BCa, Wilcoxon, Holm, TOST, slope rule, split-half reliability. |
| `evolved_rules/evaluate.py` | Battery runs with `--verify` using an f34-built verifier. |
| `evolved_rules/tests/*` | Identity tests (moves off; x0 decisions), sepcma vs pycma, slot revert rate, resume determinism, mock evaluator. |
| `simulation/Assets/Simulation/TrafficControl.cs:344-348` | Skip the unused LINQ in OriginalReference mode (private DLL, offered upstream). Optional: lines 372-390, TrafficWorld.cs:354-375 and :415. |
| Simulator CRN (side track) | `randomStreams` reset field, keyed draws at OriginalPlacement.cs:205/316/348-379, OriginalSchedule.cs:96, MaterialInventory.cs:37-45, CityDemand.cs:215, ContinuousJourneys.cs:44, TrafficControl.cs:648, SplitMix64, field in `AiReplayRecording`. |
| Watchdog script | New `gp7-watchdog` task for the gp-7 and cma-7 runs. |
| Docs | `plans/2026-11-xx-gp7-cma7.md` (pre-registration); PLAN.md amendment (seed blocks, stop rule, concurrency, 500-map test); EXPERIMENTS.md (gp-6/cma-6 close-out, then gp-7/cma-7, average next to best). |

---

## 10. Why this beats gp-6/cma-6

| gp-6 / cma-6 | gp-7 / cma-7 | Evidence |
|---|---|---|
| Same moves; search over formulas only | Autopsy, then new moves aimed at the wall, then hand screens before evolving | Throughput identical across rules; shared wall at 1400–1600 s; planner fix +154 vs search 0 |
| GP could not edit its seed (99.8% reverts); constants redrawn | The linear head contains the seed exactly; CMA tunes weights; GP only adds gated features at weight 0 | gp.py:205/482/499/537 |
| Best sample and max-of-10 validations as incumbent | Distribution mean, fixed in advance as each run's final; guard on fresh maps | −42 sample loss; +99.5 optimism; 1037 → about 1006 |
| 8-map racing, hall of fame minus the cma-1 reference | 288+ shared games per generation, rank tell, map doubling | Reliability 0.28 (GP) and about 0 (CMA); subtraction +38% variance |
| Full-covariance CMA over 81 weights, 34 of them dead, unscaled | sep-CMA over about 70 live, bank-preconditioned coordinates with mirrored pairs | cond(C) 1.17; random-walk drift |
| Stop rule with 4–14% power; reuses 1500-1549 | Tracking-slope plateau rule (simulated: 0.5% false convergence at +4/gen); fresh, single-use blocks | Power analysis; reuse bias |
| Unequal games; CMA had no lights; clean-routes mismatch | Equal charged games; identical actions, inputs and x0; paired RNG and maps per run; clean routes settled by data | 4,294 vs 1,801 games |
| Sleep and timeouts cost hours | Ops checklist, watchdog, exact resume | 13 restarts and a 7 h gap on 2026-11-13 |

### Decisions the user must make before launch

1. Approve the protocol amendments: seed blocks, the stop rule, concurrent 6+6 runs at equal games, and the 500-map test.
2. CRN: propose it to Mohammad, or skip it.
3. Motorways: yes or no for the S3 prototype.
4. 1+1 runs (about 3–4.5 days) or 3+3 runs (about 7–11 days).
5. LLM proposer: off unless the user consents.

Stop-rule simulation scripts:
- `<old-machine scratch folder>\final\stoprule.py`
- `<old-machine scratch folder>\final\s2.py`

The investigators' analysis scripts are in `<old-machine scratch folder>`.
