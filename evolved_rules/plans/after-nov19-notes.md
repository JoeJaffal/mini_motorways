# After Nov 19: notes (not a plan)

Started 2026-11-17. These are ideas to develop together **after the gp-7 / cma-7 final test**. The real plan
depends on how the final policy does against cma-1's 1,021.2. Nothing here is approved for the current run.

## 1. Study the stats and find where the model falls short

- Start from the data we already have:
  - `games7.csv` (one row per training game, rebuilt by `evolved_rules/ops/games_csv7.py`);
  - the decision logs (`decisions_tm/`, `decisions_gen0/`);
  - the replays (`output/evolved_rules/replays/`, watchable on the laptop).
- Questions to look at:
  - Why does the same policy score 845 on one map and 2,083 on another? What makes a map hard?
  - How do games end: which shop overflows first, and why?
  - Where do tiles, upgrades and waiting go?
  - What separates the top-ranked candidates from the rest?
- Maybe later: cars, houses and bridges for a subset of games. That needs replays with extra logging. Deferred
  on 2026-11-17 because of the cost.

## 2. Revisit "dynamic GP" and make it as good as possible

- Starting points from the gp-7 diagnostics (EXPERIMENTS.md, 2026-11-17):
  - no tree was inserted in any epoch;
  - the zero-game screen is biased toward the target slot, and the raced trees are mostly "add octile";
  - the race is underpowered: paired SD 160–380 on 24 maps;
  - selection on 12 maps per generation is mostly map luck (reliability about 0.3).
- To rethink: how trees are proposed, screened and raced, and how many maps each generation and race needs.

## 3. Discuss adding traffic lights, roundabouts and possibly motorways

- gp-7 / cma-7 run with lights and roundabouts off and no motorways (plan §11 scope).
- To discuss:
  - what each adds to the game;
  - what the simulator and the rules would need;
  - how to evaluate each one fairly against the current baseline.

## Other open items carried over

- The powered post-T_stop test of the final policy: optional and not approved.
- The final test result and the write-up (due Nov 19 20:00) feed all of the above.

## Found during the run (to fold into section 2)

- 2026-11-18, gp-7 epoch 6: the screen kept a tree with w0 = 4.7e-8. Its race games were identical to the
  baseline (diff 0), very likely because the 4-decimal policy text rounds that weight to 0. The screen should only
  keep trees whose w0 survives text rounding, and the race should skip no-op arms.
- 2026-11-18, gp-7 epoch 7: the same thing again (w0 = 4.66e-8). That value is W_MAX / 2^30, the floor of the w0
  bisection, so these are trees that only break exact ties. Two of the last two epochs' four raced trees were no-ops.
