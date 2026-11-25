# Mini-task repair: session review

Status: reviewed after completion, 25 November 2026, 23:49 Beirut. All bounded studies and reviews are complete; no training remains active. This review consolidates the approved flexible-duration work. The evidence does not justify an overnight launch. Refer to each linked archive for exact settings, hashes, raw measurements and uncertainty.

## What the audit established

The retained policy reliably handles short adjacent, bent and clear routes on the inspected native-action fixtures. Obstacles are usually handled. Longer routes with little spare stock and servicing a second arrival remain unreliable. Historical success on the first construction exercises did not establish autonomous timing or full-city strategy: some historical evaluations advanced the simulator automatically after construction.

The model can learn with PPO. It mastered a repeatedly practiced difficult board and learned a stronger Build-versus-Wait preference. The unresolved issue is transferring those changes to varied cities without losing useful behavior. This is narrower than claiming that PPO or neural networks cannot learn strategy.

## Completed experiments

These city means use the consumed 32-game development cohort with a 600-second cap. They are not leaderboard scores or independent confirmation. Different rows have different parents; compare within the stated experiment. Repeated use of the cohort and one training seed limit conclusions.

| Experiment | What changed / budget | What happened | Decision |
|---|---|---|---|
| [Own-policy reset curriculum](RESULTS.md) | Easier starts recreated from the policy's own successful games; 262,144 decisions per arm | Reset final city mean 89.25; cold control 115.25; original 126.09. Useful selected-start practice did not establish empty-board transfer. | Neither promoted. |
| [Native episode duration](../mini-task-horizon-2026-11-25/INTERPRETATION.md) | 60 versus 300 seconds for mini lessons; 262,144 decisions each | Longer arm rose to 146.69 at midpoint but fell to 98.47; short final 106.19. Longer episodes alone did not sustain improvement. | Neither promoted; preserve all checkpoints. |
| [Repeated difficult board](../mini-fixed-route-2026-11-25/RESULTS.md) | Road learning on one tight-stock board; 65,536 decisions | Familiar action draws improved 5/32 to 24/32 successes. City mean 129.25; gain over original uncertain. | Retained as a parent, not confirmed city improvement. |
| [More practice on that board](../mini-fixed-route-continuation-2026-11-25/INTERPRETATION.md) | Another 65,536 decisions | Familiar draws 32/32, fresh action draws on the same board 29/32. City mean fell to 107.47, with four extra zero games versus its parent. | Reject for city continuation. |
| [Build or Wait](../build-wait-ppo-2026-11-25/RESULTS.md) | Binary decision reward; 32,768 decisions; road weights frozen | Appropriate first-choice probabilities improved. Native repeated-choice negative cases still built unnecessarily. City mean 141.09; score gain uncertain, unused construction reduced. | Retained as the route-study parent; not independently confirmed. |
| [Longer Build or Wait](../build-wait-continuation-2026-11-25/INTERPRETATION.md) | Another 65,536 decisions | Quiet scenes improved to 14/16 without construction, but native city mean fell to 120.84, a clear paired development regression versus its parent. | Reject; more time on the same lesson was insufficient. |
| [First-delivery reward, road heads only](../route-outcome-run-2026-11-25/INTERPRETATION.md) | Reward successful delivery plus a bounded stock/edit bonus; 65,536 decisions | Tight practice 20 to 21/32, generous unchanged 25/32. City mean 122.50 with four extra zero games versus the parent. | Reject; no stable economy/transfer improvement. |
| [First-delivery reward, trainable road encoder](../route-spatial-run-2026-11-25/INTERPRETATION.md) | Same reward; independent frozen Wait features, learned road representation; 262,144 decisions | Final practice tight 27/32, generous 31/32; no initial successes lost. Native obstacles regressed, tight routes 9/16, both pairs 6/16; city 128.25 with 28/32 scoring versus parent141.09 with31/32. | Preserve useful practice learning; reject city promotion. |

## Repairs and checks completed

- Native reset/reward accounting was checked so pre-reset deliveries do not become new lesson rewards.
- The critic's gradients were separated from road actor features for the relevant repair studies; this is a tested engineering intervention, not proof of a single causal defect.
- Temporary task critics and native city critics have explicit migration/export rules, preserving the actor and required Adam state. Temporary practice value estimates cannot silently be used as native city values.
- Frozen Wait behavior, frozen optimizer state, changed trainable parameters, checkpoint reloads and native simulator contracts were checked. The current spatial study allows road features to learn without changing Wait's visual input.
- Missing replay-template packaging was fixed after preserving the failed evaluation artifacts. Training was not rerun to conceal the failure.
- Matched replays were inspected, including regressions and typical paired changes. Successful delivery sometimes still coexists with unnecessary branches.

All new training in this work is PPO, with no new action imitation or external road planner. Some starting abilities come from older imitation/calibrated policies; those origins are not reclassified as newly learned PPO skills.

## What remains unproven

Reliable economical routes on varied tight-stock layouts; serving later arrivals while retaining existing service; learned traffic priorities; generalization across color/distractor combinations; and sustained score improvement in longer native city play. The current city interface also does not expose every game tool, and weekly selection still uses an environment rule. One cannot claim full-game tool mastery from these experiments.

The [fresh confirmation protocol](CONFIRMATION_PLAN.md) remains reserved. It must be applied to a frozen candidate only after development gates pass. No candidate passed those gates. Fresh confirmation was not run. An overnight launch is conditional on evidence, not the clock.

## Records and artifact limits

Every material change and run is recorded chronologically in `training/EXPERIMENT_HISTORY.md`. Linked archives retain reports, small measurements, plot sources and replay evidence. Weights, generated hosts and larger runtime artifacts remain local under `output/`; this document does not make them portable or committed. No existing checkpoint or dirty work was discarded.

## Recommended next development step

Preserve the route learner as a useful experimental checkpoint, alongside the stronger retained city parent. Focus the next bounded comparison on retaining route completion while mixing affordable construction, obstacles and later arrivals, with explicit native-city retention checks. First check reward compatibility and critic calibration; earlier mixed curricula also failed, so adding city workers alone is not a proven solution. This follow-up is proposed, not launched. Do not repeat the same narrow lesson all night and assume practice gains will become city strategy.
