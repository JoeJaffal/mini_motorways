# gp-7 / cma-7 pre-registration (frozen at launch)

Operative plan: `plans/2026-11-14-gp7-cma7-plan.md` (this file records the frozen values and choices it asks for,
plan section 8.4). Machine: Mac mini M4 (see HANDOFF.md section 6). All times are local (UTC+02:00).

## Fixed before any validation game

| Item | Value |
|---|---|
| L | cma-1 3-tree, `evolved_rules/seeds/gp7/cma1_3tree.txt`, text hash fa7648c7352d9db2; played only by `gp6-final` (`f7bf5f5`) code |
| Challenger set | x0\*, cma-7 final (in-bounds mean after the last completed generation before T_stop), gp-7 final if gp-7 runs |
| Frozen-commit rule | validation and test are played with one recorded gp7 commit and the challengers' text hashes; a later code change means headline = L unless the test is re-run on unused maps |
| `decide_headline` | `evolved_rules/stats7.py`, commit 4453544 |
| R0, W | 477.4 games/h, W = 10 (HANDOFF.md section 6) |
| (λ, m) | (24, 12) |
| n_s, n_val, n_test | 300, 200, 900 |
| T_stop | 2026-11-19 01:22:00+02:00 (may only move earlier) |
| T_freeze | 2026-11-19 08:00 |
| Ladder rung | cma-7 trunk + gp-7 fork (R0 > 250) |
| Scales, θ | 84 scales, min 0.1, median 1, max 10; from 233029 logged decisions (calibration + screen) (space.json, hash fc79267c218669ba); θ = 0.0 s |
| x0\* rule and result | route point **fast** (as screened), lights off; eligible ['fast', 'bypass']; x0* text hash 7bf3469481eb3fb9, max |x0| 4.50 |
| Cut-lines | CL1 Nov 16 02:00, CL1b Nov 16 06:00, CL2a Nov 16 12:00, CL2 Nov 16 18:00, CL3 Nov 17 08:00 (plan section 4) |
| Bug gate (plan 5) | Rejected draws in the screen: a house spawning on a route while it is being drawn (shared executor, not C4-min); no fix, launch. (full note: plans/gp7-launch/bug-check.md) |
| F1 / F2 | neither: C4-min passed every identity gate and the smoke (no F1, no F2) |

## Engineering choices made while implementing (not in the plan's text)

1. **Priority globals.** The plan folds the 16 priority globals into hold (hold_live = hold − prio). Instead the
   priority global weights (and is_clean, the hold's pending_refunds and the 16 upgrade globals) stay fixed at L's
   values and every hold weight is searched. Same search space; L's priority sum stays bit-identical, so identity
   gate (4) can hold exactly (`linear.py`).
2. **Light head terms.** b_L plus pl_degree, pl_doorstep, pl_cars_near, pl_stopped_near, pl_max_wait_near,
   pl_mean_wait_near, pl_dist_worst_shop, pl_worst_colour_stuck, plus the template mul(pl_stopped_near,
   worst_overcrowded).
3. **Target-head scaling.** shop_demand/64, shop_overcrowded/1024 (gp's scales), detour_ratio and pair_connected
   raw. detour_ratio = network steps (house cell to the shop's access) / Chebyshev distance.
4. **"Top 8 legacy targets"** = the first 8 non-excluded targets of the pass (coverage order).
5. **tried_target_pairs**: a pair is marked tried as soon as its route is searched in a pass.
6. **Jam-avoid**: w_stop = 0.4 and w_car = 0.1 (a stopped car costs 0.5 in total, a moving one 0.1).
7. **Fast**: is_evo weight 1.0 (absolute); the target head is Gentle's. **Bypass**: Fast's cost head and is_evo,
   w_con = 5, b_t = −5 − c, w_ttmpl = 1.0, n_t = 3, Gentle's w_det and w_over; c = target score (without b_t, w_con)
   of a connected pair at detour 1.33 and the 75th percentile of the logged connected pairs' shop term.
8. **Lights point**: L + light head (pl_stopped_near weight 1, others 0) + 0.8 on the type_3 upgrade weight, planner
   off (separated vector, M_eff = 0).
9. **Screen rate minimums**: evo/pair route built in ≥ 3% of decisions and a pair opened in ≥ 5% of decisions.
10. **Mirrors**: pycma `CMA_mirrors=True` (about 0.16 λ selectively mirrored samples).
11. **σ0 rule** evaluated automatically after generation 0 with decision logging on (`--log-gen0`).

## Screen (plan section 5; never quote x0*'s screen number, validation re-measures it)

| Point | n | Paired diff vs L | SE | Pair opens | Evo built | Rejected draws |
|---|---|---|---|---|---|---|
| gentle | 300 | +102.3 | 22.0 | 5.6% | 2.8% | 0 |
| fast | 300 | +135.1 | 23.4 | 5.2% | 7.1% | 1 |
| bypass | 300 | -31.1 | 30.7 | 88.9% | 10.9% | 0 |
| jam_avoid | 300 | +103.5 | 22.2 | 5.7% | 2.8% | 0 |
| lights | 300 | -9.2 | 14.3 | 0.0% | 0.0% | 0 |
