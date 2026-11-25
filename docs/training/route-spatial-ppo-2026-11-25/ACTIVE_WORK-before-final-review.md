# Active work: mini-task repair and transfer checks

Updated 25 November 2026, 22:56 Beirut. The duration comparison is complete; only the spatial study continues.

The authoritative checkout is `/home/mohammadjaffal/mini_motorways`, branch `Maskable-PPO`, HEAD `6bd7f7193b26ae0f5aa12563f3dd89769115df6e`. The Desktop checkout on `main` is untouched. The user approved flexible timing for the mini-task audit, necessary repairs, bounded PPO comparisons and a conditional overnight launch. Preserve all existing work and checkpoints. Do not introduce a planner or imitation, pull/reset the repository, or treat an early score increase as overnight readiness.

Continue through the active studies and their reviews. Do not stop merely because learning is running in the background.

## Active road-encoder study

Controller PID **947374** runs `output/training/route-spatial-01`. The archive is `docs/training/route-spatial-run-2026-11-25`. It has reached **163,840 of 262,144 added decisions**. All preservation checks pass so far. Watch:

```bash
tail -F /home/mohammadjaffal/mini_motorways/output/route-spatial-01-launch.log /home/mohammadjaffal/mini_motorways/output/training/route-spatial-01/training.log
```

The parent is the retained Wait01 final checkpoint, SHA `907e1a083b58780bd140d4e258285878ed3534a4c0be6cf9b75070eae7f04826`. This does **not** continue the rejected road-head candidate. The native critic remains in the untouched C1 template, SHA `c86c0db95e28951c3e9ed36d5a29eb94d7faa4cbddbfddaed18700dc70121eb3`.

The study uses 16 workers, 512 steps and 32 rollouts: 12 tight-stock and four generous-stock scenarios, with fresh training seeds beginning at **248100000**. Practice reward remains: actual first delivery earns `1 + .20 * remaining_stock_fraction + .05 / (1 + all_road_actions)`; failure earns zero. Native city reward is unchanged. Forced-Wait compression is allowed only when no construction choice remains; its final timestamp can be later than the actual first delivery.

An independent frozen copy of the starting spatial encoder supplies Wait's visual features. The existing road encoder and conditional road heads may learn. There is still one actor and no teacher route. The 22 trainable parameter tensors comprise 18 road/encoder tensors and four temporary task-critic tensors. Parent actor weights and all 26 actor Adam states are retained. The task critic starts fresh, as in the preceding study; the native critic is restored explicitly at export. The user was told to expect roughly 1½–2 hours including reviews, with flexible timing.

Preflight passed: bit-exact actor migration on 16 states; 128-decision PPO smoke; all 22 trainable Adam counters advance while frozen states remain unchanged; 64 shared-state Wait probes differ by at most `2.03e-7`, while road outputs and encoder weights change. The two encoders have separate storage. Critic gradients do not train actor features. Default native export and lesson resume preserve the required weights/Adam. Other native modes are implemented but were not separately exercised.

The full initial 64-game review exactly repeats the previous study's baseline: 20/32 tight successes and 25/32 generous successes. This is consumed development data, not independent confirmation. This study also has a larger budget than the prior 65k road-head study, so any gain cannot be attributed solely to the encoder change.

A timely read-only review of the65,536 checkpoint completed while learning continued: tight successes20→23/32, generous25→26/32. Successes with remaining stock stayed6/32 and21/32 respectively, so this is a small completion gain without a demonstrated economy gain. Files: `live-outcome-65536/` and `live-quarter-review.json` in the production archive. The controller will repeat this same checkpoint review later; do not count that as independent evidence.

The controller freezes its source and host. It now includes the replay HTML template. After learning it reviews checkpoints at 65,536, 131,072 and 262,144 decisions on the fixed 64-game outcome cohort; then it runs 112 native mini games, 32 city games and native export. Check `status.json`, `training/checkpoints.json` and logs. No automatic extension or overnight promotion is configured.

## Completed duration comparison

Controller PID **807935** completed at22:24. Both arms reached262,144decisions and all reviews finished. Short final city106.19,27/32scoring; long final98.47,30/32scoring. Neither passes readiness; final duration contrast is uncertain. See the archive INTERPRETATION.md and complete-learning-curves.png. No promotion or further duration training.

Both arms started from the same original parent and use the same 8-city/4-pair/4-single mixture with policy-generated prefixes. Only the practice duration differs: 60 versus 300 seconds. The original city mean is 126.09. Long-arm city means were 137.53 at 65k, 146.69 at 131k, and **98.47 at the completed 262k budget**. Short-control means were 110.19 at 65k, 116.75 at 131k and106.19 at the final budget. Matched long-minus-short intervals are positive at both early checkpoints, but the long arm's gain subsequently collapsed. Do not claim a stable duration benefit or readiness from the early points. One training seed per arm; scenario bootstrap intervals do not measure training-seed variation.

Evidence is in `docs/training/mini-task-horizon-2026-11-25`, including `matched-through-midpoint.json`. The declared budget and full comparison are now complete; neither arm is promoted.

## Completed road-head study: rejected

`output/training/route-outcome-01` completed 65,536 decisions, 3,997 episodes and 1,494.58 seconds of learning. Final SHA:

`52de08460ce18e905cbb26acbef38f12053c369f7a47fa5d085b5d6b77e3dfa9`

Lifetime timesteps: 851,968. The frozen practice curve was tight **20→22→21→21/32**, generous **25→24→25→25/32**. Native short geometry reached 16/16 in all four families; tight routes were 7/16 versus the parent's 8, generous routes 14/16 versus 11, and both-pair service 5/16 versus 4.

City mean fell from **141.09 to 122.50**, and scoring games from **31 to 27/32**. The paired mean change was −18.59, with interval [−46.41, 5.84]: the mean decline is uncertain, but four additional zero games fail the declared retention screen. Preserve it; do not promote or continue it. Results, interpretation, raw measurements and the inspected figure are in `docs/training/route-outcome-run-2026-11-25`.

Its first native mini review failed because the frozen package omitted `stage1_replay.html`. Training and checkpoints were intact. `recover_route_reviews.py` preserved failed status/logs/partial output, added the missing asset, reran evaluation in a new directory, and finished city review and native export. Recovery is complete. No training was rerun or original artifact overwritten.

Six selected paired outcome replays exactly reproduce evaluation counters. A gained success still branches; a lost success builds disconnected roads; a retained success takes a different valid six-edit route with the same stock. This is not uniformly cleaner geometry. Selected construction decisions have mean top-road probabilities around .48–.72, which do not support an extreme near-deterministic wrong-prior explanation. The inspected figure and traces are under `outcome-replays/`; a completed evidence manifest is present.

## Earlier results and readiness

Wait02 reached 98k total practice decisions. It improved quiet scenes to 14/16 without construction, but negative cases only to 4/16, 8/16 and 5/16. City mean fell 141.09→120.84 with a negative paired interval, so it was rejected. Wait01 remains a useful parent, not an independently confirmed city improvement.

On 124 selected functional-opening states both Wait versions already assigned >99.98% mean Wait probability; the suspected missing opening-Wait lesson was not supported there. The selected worst city regression instead exhausted stock within five seconds without connecting the opening. See `build-wait-continuation-2026-11-25/INTERPRETATION.md`.

Fresh confirmation seeds **236M/237M** and Wait reserve **247M** remain untouched. The protocol is `mini-task-repair-2026-11-25/CONFIRMATION_PLAN.md`: retain short skills; reach 14/16 tight routes and 8/16 both-pair service; city mean at least the original with at most one extra zero game. Then use fresh 32-per-family mini checks, 64 city plays targeting ≥20% gain with a positive paired scenario interval, and 16 longer plays. No current candidate passes. Never promise that another long session will increase scores.

## Remaining work and commands

1. Finish the active spatial study and inspect its complete curve and actual construction behavior. The duration comparison is complete and rejected.
2. Once the spatial controller is complete, run:

```bash
PYTHONPATH=training .venv/bin/python training/review_city_route_outcome.py --archive docs/training/route-spatial-run-2026-11-25 --parent-archive docs/training/build-wait-ppo-2026-11-25 --original-city docs/training/mini-task-horizon-2026-11-25/evaluation/city-initial
```

3. Adapted sources are ready in `route-spatial-ppo-2026-11-25`: `plot_completed_study.py`, `replay_outcomes.py`, `plot_outcome_replays.py` and `review_economy.py`. Run after completion (Python path `training`; system python3 for matplotlib plots). Inspect figures and paired replays. The economy review also asserts exact agreement with the read-only live quarter/midpoint repeats; those repeats are not independent evidence.
4. The duration controller completed successfully; its results, interpretation, complete curves and final-budget replay are archived. No recovery or further training is needed for that study.
5. Record measured outcomes, limits and the resulting decision in `training/EXPERIMENT_HISTORY.md`, current status/handoff and the archive/index. Do not launch another study or an overnight run before these full results justify it.


Additional coverage finding: the single-pair generator uses three color IDs and no competing pair, while the city profile supports five colors. See `COVERAGE.md`. No active fixture changed, and this is not a proven cause of any regression. Do not claim full color-selection behavior from isolated practice success.

Midpoint review completed: tight 21/32, generous 29/32; successes with stock remaining 6/32 and22/32. Clearest gain remains completion with generous stock, not reliable economy. `live-midpoint-review.json` retains paired counts. `mini-task-repair-2026-11-25/SESSION_REVIEW.md` is a linked draft session synthesis; update the pending spatial row after the final review.
