# Phase 2: evolution loop (run to convergence)

> **For agentic workers:** executed task by task (implement, review, fix, commit). Each task's requirements include the Global Constraints below.

**Goal:** evolve rule sets that play far better than the Phase 1 rules (hand 152.1, separated 251.4 trips on LA 2000–2019), running evolution until the validation score stops improving, not until it passes a threshold.

**Why (user, 2026-11-01):** "I wanted not to just beat these because these are very simple things. I wanted to do way better. Stop where it converges, not when it passes a certain threshold." Success means many trips while being efficient (our reading: few wasted road tiles and commands per trip, and a reasonable compute bill).

**Spec:** `evolved_rules/PLAN.md` (sections 3–6) plus the decisions below, which override it where they differ.

**Tech stack:** Python 3.12 (`.venv`), DEAP 1.4.4, cma 4.5.0, numpy, scipy; Release TrafficHost; `PYTHONHASHSEED=0`.

## Decisions made for Phase 2 (my calls, 2026-11-01)

| # | Decision | Why |
|---|----------|-----|
| P2-1 | Stop rule: **converged** when, after at least 30 generations, no generation in the last 20 produced a validation improvement of at least max(3 trips, 2% of the incumbent's validation mean). Backstop: 72 h wall clock or 400 generations, reported as `stopped: budget` (never as converged). | The user asked for convergence, not a threshold. The 2% margin is above the validation noise (paired SD ~100 trips / √50 ≈ 14 trips; 2% of 250 = 5). |
| P2-2 | Validation set: LA **1500–1549** (50 seeds, was 1500–1519). Each generation, the best individual by racing mean is validated if its tree text is new (cache by text). The final model is the best validated individual. | 20 seeds is too noisy to see a plateau. |
| P2-3 | Racing: population 64; every individual plays S4 (4 seeds); the top 16 also play S8 (8 more). Seeds drawn per generation from LA 1–999 by the run's RNG. Generation cost ≈ 384 + ≤ 50 games. Tournament size 4 on the S4 mean with lexicographic parsimony; elitism 3 by S4+S8 mean, re-scored on the new seeds. | Plan section 5 option for ~30+ generations per night. |
| P2-4 | Fitness `(mean trips, mean seconds)` lexicographic, cap 3600 s in training and evaluation. Ties: fewer total nodes. | Plan decision 9. |
| P2-5 | **Remove tree is dropped** for Phase 2 (individual = 3 trees: Priority, Hold, Upgrade). | Every Phase 1 loss ended with unused road tiles: materials are not the limit. Removal can come back if autopsies show tile starvation. |
| P2-6 | **Coverage candidates** are added for evolved policies only: besides unserved houses (Phase 1), every (house, same-colour shop) pair where the house does not reach that shop is a target, so the rules can add car supply to a starving shop. Phase 1 policies keep their exact behaviour (games byte-identical). | ~3/4 of Phase 1 losses were car supply (PLAN.md section 1). |
| P2-7 | Terminals are map-relative and scaled by power-of-two divisors (exact in binary floating point), so the hand rule written as trees plays exactly the hand rule. | Plan section 4; exactness makes the seeded individual testable. |
| P2-8 | `OriginalDemandInterval` stays excluded; the demand rate is estimated from increases in `demand` over a sliding window (plan section 9 default). | Same exclusion list as Mohammad. |
| P2-9 | Population seeded with the hand rule, the separated preference and random trees (ramped half-and-half, depth 2–4). Depth limit 6 per tree. | Plan section 5; open decision from Phase 1 settled: seeding is a starting point, not a target. |
| P2-10 | Workers: 10 hosts (16 logical cores; Phase 1 found >10 slower). | Measured. |

## Global Constraints

- Phase 1 behaviour is frozen: `hand`, `separated`, `nothing` and `reference` produce byte-identical recordings to commit 87256e6 (test: seed 2000 hand = 57 trips, 405 commands; compare whole recordings against ones produced at 87256e6).
- Determinism: no decision may depend on set/hash order of strings; same (individual, seed) gives the same command log in any process.
- Every game is a valid AI replay (20-tick steps, exact enum casing); final reported games are verified with `--verify-replay`.
- Observation allowlist as PLAN.md decision 7. No privileged fields.
- Runs, caches and checkpoints live under `output/evolved_rules/` (git-ignored). Nothing under `simulation/` changes.
- Commits: one per task, on branch `evolved_rules`, author from the repo config, message `<summary> (phase 2, task N)`, no Co-Authored-By or any tool attribution. Never push.
- Tests: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest evolved_rules/tests -q` stays green.

## Review focus

1. Hand rule as trees diverges from `HandRule` at an equality boundary (hold check `best >= hold`) → test whole command logs on several seeds.
2. Demand-rate tracker state leaks across games or across individuals in one worker → fresh tracker per game; test two games in a row.
3. Cache key collisions: same tree text, different code version or cap → key includes a code-version string, cap and seed.
4. Resume after a kill reproduces the same run (RNG state, seeds, cache) → test kill-and-resume on a tiny config gives identical generation records.
5. A hung or crashed host must not stall or silently drop individuals → timeouts, restart, and a failed game is an error that is retried once, then fails the run.

---

### Task 1: Features v2 and game metrics

**Files:** modify `evolved_rules/features.py`, `evolved_rules/agent.py` (pass a per-game `DemandTracker`), `evolved_rules/state.py` (only if new parsed fields are needed: vehicles per colour, home/busy); test `evolved_rules/tests/test_features.py`.

- Keep every Phase 1 key and value unchanged. Add keys (all raw floats; scaling is Task 3's job):
  - candidate: `path_cost_s` (congestion-free one-way route cost in seconds from the house to the target over the planned path plus existing roads, using plan 3.5 lane-speed rules approximately: 2 s per orthogonal tile, 2.83 diagonal, ×1.5 at a 90° turn, ×2 at junctions of degree ≥ 3), `house_served` (0/1, the house already reaches some same-colour shop), and target-shop terms (for the best shop the route reaches, ties by lowest id): `shop_demand`, `shop_unassigned` (`demand − reserved`), `shop_capacity`, `shop_overcrowded` (seconds), `shop_rate` (estimated pins per minute), `shop_houses` (same-colour houses that reach it), `colour_margin` (car-supply margin of the house's colour: cars of connected houses × 60 / estimated round trip s − Σ shop rates per minute of that colour).
  - global: `pending_refunds` (cells with pendingRemovals = 1), `next_offer_s` (`max(0, 140 × (offers taken + 1) − time)`; the agent counts acceptances), `disconnected_components` (plan section 4 definition, computed from connections), `unserved_shops`, `edge_distance` (min distance from any building to the playable border), `worst_overcrowded` (max shop overcrowded_for), `worst_margin` (min colour margin over colours with a shop), `shops`, `houses`.
  - offer: `stock_of_type` (current inventory of the offered item type).
- `DemandTracker`: one per game; `update(state)` after every observation the agent sees; per shop, a 60 s sliding window of positive increases in `demand` → rate per minute; deterministic; no state shared between games.
- Game metrics added to `GameResult` / games.jsonl: `tiles_built` (road tiles placed = road tiles spent, from inventory deltas and accepted draws), `trips_per_tile`.
- Tests: Phase 1 recordings unchanged (seed 2000 hand and separated byte-identical to a recording made at 87256e6 — produce the reference by running the Phase 1 code from `git archive 87256e6` in a temp dir, or by asserting the exact (trips, commands, action_counts) of the Phase 1 run folders: hand 2000 = 57 trips / 405 commands); each new feature on a hand-made CityState; tracker reset between games.

### Task 2: Coverage candidates

**Files:** `evolved_rules/candidates.py` (new `coverage_targets(state)`), `evolved_rules/agent.py` (`decide()` uses `coverage_targets` when `getattr(policy, "coverage", False)`), tests.

- `coverage_targets(state)`: Phase 1 `unserved_targets` entries first (same order), then for each shop in id order, each same-colour house (id order) that does not reach that shop's access cells, as target `(house, (shop,))`; skip pairs already listed; cap at 24 targets per decision, keeping order (log nothing). A route that connects a house to a shop it did not reach counts as success when that house now reaches that shop.
- The excluded-house rule becomes excluded-(house, shop) pairs for coverage policies.
- Phase 1 policies (no `coverage` attribute) are byte-identical.
- Tests: targets on hand-made states (two shops of one colour, house reaching only one), cap, success rule, Phase 1 identity.

### Task 3: GP representation

**Files:** create `evolved_rules/gp.py`, tests `evolved_rules/tests/test_gp.py`.

- Three `PrimitiveSet`s (Priority over candidate+global terminals, Hold over global terminals, Upgrade over offer+global terminals); functions `add sub mul pdiv min max neg if_gt(a,b,c,d)` (if a > b then c else d), ephemeral constants from a module-level function (picklable on Windows) drawing from {−1, −0.5, 0.25, 0.5, 1, 2, 4} and uniform(−1, 1) rounded to 2 decimals. Terminals = scaled feature values: each feature divided by a fixed power of two (tiles, stock, pins /64; seconds /1024 or /4096; counts /64; flags as is). Define creator classes at module top level.
- `Individual` = list of 3 `PrimitiveTree`s with fitness `(1.0, 1.0)` weights; `individual_text(ind) -> str` (canonical, used as cache key), `individual_from_text(text)`.
- `TreePolicy(texts)`: a `Policy` (priority/hold/upgrade, `remove` = −1, `coverage = True` unless constructed with `coverage=False`) that evaluates compiled trees with non-finite → −inf (priority/upgrade) as agent.py already handles; compiled lambdas cached per process.
- `HAND_TEXT`, `SEPARATED_TEXT`: the Phase 1 rules as tree texts. Test: `TreePolicy(HAND_TEXT, coverage=False)` plays byte-identical recordings to `HandRule` on seeds 1000, 2000, 2004; same for separated.
- Variation helpers: `mate(a, b)` (one-point crossover on one random tree index), `mutate(ind)` (one tree; uniform subtree / node replacement / ephemeral), static depth limit 6 per tree, `size(ind)` = total nodes.

### Task 4: Batch evaluation engine with cache

**Files:** create `evolved_rules/engine.py`, tests `evolved_rules/tests/test_engine.py`.

- `Engine(workers, cap_s, cache_path)`: a spawn-context `ProcessPoolExecutor` reusing `evaluate.py`'s worker setup (long-lived host per worker, parent watchdog, abort flag). `engine.play(jobs: list[tuple[str, int]]) -> list[dict]` where a job is (individual text, seed) and the result is the game summary (no recording). Results cached in an append-only JSONL at `cache_path`, keyed by `(CODE_VERSION, text, seed, cap_s)`; `CODE_VERSION` is a constant in engine.py bumped when agent behaviour changes. Duplicate jobs in one batch play once.
- Per-game timeout (default 900 s wall); a timed-out or crashed worker is replaced and the game retried once; a second failure raises.
- `engine.record(text, seed, path, verify)` plays one recorded game and saves/verifies it (for final evaluation).
- `evaluate.py` gains `--policy tree:<file>` reading an individual text file, so any evolved individual can be evaluated and verified with the existing CLI.
- Tests: cache hit avoids replay, key separation by cap/version, duplicate dedup, timeout path with a fake slow job (in-process pool substitute), identical results across two engines.
- *As built (deviation):* one single-process spawn `ProcessPoolExecutor` per worker slot instead of one shared pool, still with `evaluate.py`'s `_init_worker` / `_worker_host` / `_close_host`. A shared pool cannot kill one timed-out worker (with its host tree) or pin a crash on one game, and one game in flight per slot means nothing is queued, so the abort flag has nothing to skip and is not passed (`initargs=(None,)`).

### Task 5: Evolution loop with convergence stop

**Files:** create `evolved_rules/evolve.py`, tests `evolved_rules/tests/test_evolve.py`.

- CLI: `python -m evolved_rules.evolve --run NAME [--resume] [--workers 10] [--pop 64] [--seed 1] [--min-gens 30] [--patience 20] [--min-gain-frac 0.02] [--min-gain-trips 3] [--max-hours 72] [--max-gens 400] [--validation 1500-1549]`.
- Loop per decision P2-3: invalidate all fitnesses each generation; S4 for all, S8 for top 16; tournament (size 4) on S4 mean with parsimony (compare `(fitness, -size)`); elites 3 by S4+S8 mean copied unchanged; crossover prob 0.5, mutation prob 0.3 (per offspring), depth limit 6.
- Validation each generation (P2-2) and the stop rule (P2-1). The run folder `output/evolved_rules/evolve/<run>/` holds: `config.json` (all parameters, git commit, dirty flag, package versions), `generations.jsonl` (per generation: seeds, S4 best/mean/median, best size, validated text hash and its validation mean, incumbent, gens since improvement, wall time, games played, cache hits), `validation.jsonl` (text, per-seed trips and seconds, mean), `best.txt` (incumbent text), `checkpoint.pkl` (population, RNG states via `random.getstate()`, generation, incumbent, counters; written atomically every generation), `status.json` (`running`/`converged`/`budget`, reason).
- `--resume` continues from checkpoint and produces the same subsequent generations as an uninterrupted run (cache makes replayed games free).
- Prints one line per generation.
- Tests: on a fake engine (deterministic synthetic fitness from tree text), the stop rule triggers exactly when specified; budget stop labelled `budget`; resume equivalence; elitism keeps elites; parsimony tie-break.
- *As built (deviation, P2-1):* a generation counts as an improvement when its validated mean is at least `anchor + max(min_gain_trips, min_gain_frac × anchor)` and strictly above the anchor. The anchor is the validated mean at the last counted improvement (generation 0 sets it), not the moving incumbent's mean. Read literally, P2-1 measures each gain from the current incumbent, so a creep of +2 trips a generation (+40 over 20 generations) would stop as converged. With the anchor, small gains add up until one counts, while noise-sized wiggles never reset the counter. The threshold differs from the literal rule by at most about 0.1 trip (2% of the gap between anchor and incumbent). The incumbent (the final model, `best.txt`) is still the best validated individual by `(mean, mean seconds, -size)`, whatever the margin. The strict `> anchor` only matters when both minimum gains are 0. Without it, re-validating the anchor's own cached text would count as an improvement every generation. `Convergence` in `evolve.py` implements the rule; Task 6 (CMA-ES) reuses it unchanged.
- *As built (additions):* `Config.check()` also requires `elites <= racing_top`, since elites are taken from the racing top. Two more status values, `failed` and `interrupted`, record why a run stopped early. `max_hours` sums the wall time of checkpointed generations only.

### Task 6: CMA-ES control

**Files:** create `evolved_rules/tune_cmaes.py`, tests.

- Linear policy: priority = w·candidate+global terminals, hold = w·global terminals + b, upgrade = w·offer+global terminals; weights bounded [−5, 5]; expressed as an individual text (a sum of `mul(const, terminal)` trees) so it runs through the same engine and cache. popsize 16, each candidate on the same 8 training seeds per generation; validation and stop rule identical to evolve.py (shared helper), run folder `output/evolved_rules/cmaes/<run>/`.
- Tests: weight vector ↔ text round trip; stop rule shared with evolve.
- *As built:* 67 weights (31 priority, hold bias + 13, 22 upgrade), each tree a balanced `add` of `mul(w, term)` nodes (depth 6), weights snapped to [−5, 5] and 4 decimals so text ↔ vector is exact (`text_to_weights` is strict). CMA-ES is told ranks (candidates strictly better by `(mean trips, mean seconds)`), which is the lexicographic fitness exactly. Initial mean `--x0 separated` (is_separated 5 instead of 15.625, the same choices while routes need < 317 tiles; tested byte-identical to SeparatedPreference with coverage off), sigma0 0.5. cma's own termination criteria are recorded (`cma_stop`), never obeyed: the validation plateau is the only stop. `evolve.load` gains `config_cls` and `evolve.run_loop` gains `step`/`fmt`, so the run folder, resume rules, stop rule and status handling are evolve.py's own code. The checkpoint holds the pickled strategy, which carries its own copy of the RandomState cma samples from (pickling the bound `np.random.randn` in its options copies the generator), so unpickling it every generation is what makes resume exact; numpy's global RNG state is also saved and restored, only as a safeguard for direct `np.random.*` calls inside cma. `evolve.load` refuses a run folder of another method.

### Task 7: Smoke run, full launch, plan update

- Smoke run: `evolve --run smoke --pop 16 --min-gens 3 --patience 2 --max-gens 6 --validation 1500-1509 --workers 10`; check: validation incumbent improves over generation 0 or equals it, run folder complete, resume works.
- Update PLAN.md section 7 (Phase 2 row and a "Phase 2 status" subsection with the stop rule and decisions P2-1..P2-10).
- Launch the full GP run (`--run gp-1`) in the background; it stops itself at convergence. Then the CMA-ES run (`--run cma-1`), not in parallel with GP (shared CPU).
