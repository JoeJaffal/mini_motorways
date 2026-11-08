# After the simulator fix: re-evaluate everything (resume plan)

Written 2026-11-08, when gp-4 was paused at generation 21 because a simulator bug was found (EXPERIMENTS.md, "gp-4 evolution paused"). The simulator is being fixed in a separate session on the `mohammad` line (`upstream/mohammad`, worked on in the `C:\Projects\490 - Project\mm-ppo` worktree). This file says what to do on `gp4` once that work is finished.

## State at the pause

- **Branch:** `gp4`, clean, in `C:\Projects\490 - Project\mini_motorways`. Not merged, not pushed. Merge, PR or keep is still the user's decision.
- **Simulator on `gp4`:** `upstream/main` plus `5360118` (Unity rebuild). `upstream/mohammad` adds PPO-side files on top: `UsefulConnectivity.cs`, `DrawDiagnostics.cs`, `SimulationChecks.cs` additions and headless options. The gameplay core is the same.
- **gp-4 run:** `output/evolved_rules/evolve/gp-4/`, checkpoint after generation 21, killed. Its `status.json` still says `running`.
- **Nothing is running.** No evaluation or evolution process is left.

## 1. Bring the fixed simulator into `gp4`

1. Read the fix session's handoff note. It lists commits, gameplay changes, protocol changes and build steps.
2. Ask the user how to integrate: merge the fixed branch into `gp4`, or merge it into `main` first. Do not push.
3. Rebuild and check:
   - `dotnet build simulation/Headless -c Release`. `evolved_rules/host.py` loads `simulation/Headless/bin/Release/net8.0/TrafficHost.dll`, or `EVOLVED_RULES_HOST_DLL` if that is set.
   - `dotnet run --project simulation/Headless -- --self-test`
   - `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/verify_five_maps.py`
4. Check the protocol against `evolved_rules/host.py`, `state.py`, `session.py` and `verify.py`. The fields used include car `stage`, `speed` and `waiting`, the build tools `TrafficLight` and `Roundabout`, and package choices. Fix any break, then run `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest evolved_rules/tests`.
5. **Keep old results out of the cache.** Bump `engine.CODE_VERSION`, for example from `gp4-v2` to `gp4-v3-sim2`.
   - The cache key is (`CODE_VERSION`, text, seed, cap) and does not include the simulator build.
   - Better still, key on a simulator version the host reports, if the fix session added one.
   - No old evolution run (gp-1 to gp-4, cma-1) may be resumed on the new simulator.
   - Old replays will no longer verify, which is expected.

## 2. Round A: re-evaluate the existing rules on the fixed simulator

Use the same policies and seeds as before, with an `-s2` suffix on the run names. This is about 1,560 games, roughly 45–60 minutes on 8 workers. Tell the user the count before starting (standing rule: say how many games before any run of more than 20).

| New run | `--policy` | `--seeds` | Games | Old run (old simulator) |
|---|---|---|---|---|
| `phase1-nothing-s2`, `phase1-hand-s2`, `phase1-separated-s2` | `nothing` / `hand` / `separated` | `1000 2000-2019` | 3 × 21 | `phase1-*` |
| `val-hand-s2`, `val-separated-s2` | `hand` / `separated` | `1500-1549` | 2 × 50 | `val-*` (153.1, 187.5) |
| `test-gp-s2`, `test-cma-s2` | `tree:evolved_rules/final/gp3_final.txt` / `tree:evolved_rules/final/cma_final.txt` | `7000-7099` | 2 × 100 | 245.9, 250.6 |
| `test-separated-s2`, `test-hand-s2` | `separated` / `hand` | `7000-7099` | 2 × 100 | 216.3, 170.8 |
| `h4-*-s2`: the 9 step-1 rules | `separated light round lightround tree: gppkg: gplight: gpround: gplightround:` (gp ones on `evolved_rules/final/gp3_final.txt`) | `3100-3199` | 9 × 100 | `h4-*` |
| `h2h-gp-s2` | `tree:evolved_rules/final/gp3_final.txt` | `9000-9099` | 100 | 245.3 |
| `val-gp4inc-s2` | `tree:output/evolved_rules/evolve/gp-4/best.txt` | `1500-1549` | 50 | 259.7 |
| `val-gp3final-s2` | `tree:evolved_rules/final/gp3_final.txt` | `1500-1549` | 50 | 238.0 |

Command shape: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m evolved_rules.evaluate --policy P --seeds S --workers 8 --run NAME --verify`.

- **Test set 7000–7099:** the new simulator is a new environment, so re-running it is a fresh measurement. Still, never choose or tune anything on it.
- **PPO head-to-head (9000–9099):** needs Mohammad's PPO re-run, probably retrained, on the fixed simulator. Coordinate with the user.

## 3. Decision gate

For each rule, compare the old and new means paired by seed, and write an EXPERIMENTS.md entry with best next to average.

- **Ranking and gaps roughly hold** (GP > separated > hand, and lights ≥ no lights on 3100–3199): continue with step 4.
- **Ranking changes:** the final rules were chosen on the old simulator. Re-run selection or re-evolve first, as gp-3.3-style GP and cma-1-style CMA-ES fresh runs. Ask the user before committing a day or more of compute.

## 4. gp-4b: a fresh gp-4 run on the fixed simulator

Use the same command as gp-4 (EXPERIMENTS.md, gp-4 setup) with `--run gp-4b`, 8 workers and `--max-hours 120`. Expect about 35 minutes per generation and at least 30 generations. Then follow the gp-4 design's steps 3 and 4: CMA-ES control with a place sum, final selection on 5100–5299, test on 6100–6199, and the PPO head-to-head on 8100–8199.

## Standing rules

- Python: `.venv/Scripts/python.exe` with `PYTHONHASHSEED=0`.
- Commits: as Aya <aya2007k@gmail.com>, with no Claude attribution. Never push, and never commit to `main`.
- Selection: never choose or tune on validation (1500–1549 is only for the stop rule) or on held-out maps (2000–2019, 7000–7099).
- Reporting: always give the average next to the best.
