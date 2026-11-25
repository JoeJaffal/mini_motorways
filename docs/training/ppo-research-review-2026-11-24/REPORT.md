# PPO/game reinforcement-learning research and local assessment

24 November 2026. Research and read-only implementation review, not a new training experiment.

## Scope and provenance

User requested primary-source research, lessons from other game agents, and a reassessment of this project after challenging premature judgments of short training. Work stayed in `/home/mohammadjaffal/mini_motorways`, branch `Maskable-PPO`, HEAD `6bd7f7193b26ae0f5aa12563f3dd89769115df6e` plus existing dirty work. The user previously resolved the branch conflict in favor of this checkout; its own AGENTS.md agrees. Desktop/main was untouched. No policy, reward, simulator or checkpoint changed; no training was launched. Process inspection found no matching training/native-host jobs (excluding the inspection command). Local package versions: SB3 2.9.2, sb3-contrib 2.9.2, Gymnasium 1.4.0.

## Judgment

PPO is a defensible algorithm here, and there is direct evidence it has learned. We have not established reliable integrated city strategy. Recent short experiments are useful implementation checks but inadequate evidence to reject learning hypotheses. Conversely, earlier multi-million-decision regressions rule out the claim that more time automatically solves the problem. The next step should be a stable, sufficiently funded experiment with learning curves, followed by explicit transfer testing. Stop treating a promotion gate as a prerequisite for allowing an experimental learner enough experience.

## Primary-source findings and application

1. [Schulman et al., PPO (2017)](https://arxiv.org/abs/1707.06347): PPO alternates environment collection and minibatch optimization, reusing each collected batch for multiple epochs. It was evaluated on Atari as well as locomotion. Application: count fresh decisions, completed episodes and optimizer steps separately. More optimizer passes are not equivalent to more varied experience. No paper supplies a universal sufficient budget for our city.
2. [Official SB3 guidance](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html): model-free RL can require millions of interactions; evaluation should be separate and seed variability matters. Application: 16k decisions is a wiring pilot, not a convergence test. Millions of interactions on a previous task do not make a newly added residual head fully trained.
3. [OpenAI Five (2019), especially sections 3.3 and appendices G/H](https://arxiv.org/html/1912.06680v1): large-scale PPO, structured observations, recurrent neural processing, reward shaping, and continuity-preserving model changes were used. Its sparse-reward ablation learned but was less sample efficient. Application: preserve progress, make credit assignment tractable, and distinguish final game success from auxiliary rewards. Its scale, competitive self-play and detailed reward choices are not a recipe for this single-player simulator. We should not introduce imitation or a road planner to imitate its success.
4. [Engstrom et al. (2020)](https://arxiv.org/abs/2005.12729): implementation choices substantially affect PPO behavior. [Andrychowicz et al. (2020)](https://arxiv.org/html/2006.05990v1) studied over 50 choices; separate actor/value networks helped on four of five continuous-control tasks, and learning rate strongly affected outcomes. Application: investigate effective actor updates and critic interference. These continuous-control findings motivate experiments, not copying hyperparameters or declaring shared encoders wrong for this game.
5. [Huang and Ontañón (2020/2022)](https://arxiv.org/abs/2006.14171) justify invalid-action masking and demonstrate its value in large invalid-action spaces. [Official MaskablePPO docs](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html) require mask-aware evaluation and environment-side masks for subprocess environments. Application: keep legality masks, including during evaluation; do not substitute a mask that secretly selects good routes. Recurrent policies are not directly supported by this implementation, so adding memory would be an engineering experiment, not a checkbox.
6. [Procgen, Cobbe et al. (2020)](https://arxiv.org/abs/1912.01588) demonstrates the importance of varied environments and examines neural capacity/generalization. Application: use varied geometry, stock and demand conditions and unseen layouts; passing a single fixture does not establish transfer. Larger models helped their benchmark, but that does not prove our 16-channel correction network is the bottleneck.
7. [Agarwal et al. (2021)](https://arxiv.org/abs/2108.13264) shows why point estimates from few runs can mislead. Application: preserve per-city outcomes and paired uncertainty; replicate training seeds before claiming a reward/architecture advantage. Many evaluation maps estimate one trained policy's performance, not variability across training runs. An interval crossing zero is uncertainty, not proof of no effect.
8. [Ng, Harada and Russell (1999)](https://people.eecs.berkeley.edu/~pabbeel/cs287-fa09/readings/NgHaradaRussell-shaping-ICML1999.pdf) establishes conditions for policy-invariant potential shaping. Application: a per-road penalty is a changed objective, not automatically invariant shaping. Its finite-task bound must not be extrapolated to an indefinitely growing city. No planner-derived potential is proposed.

## What our evidence actually establishes

| Evidence | Finding | Limit |
|---|---|---|
| [First overnight](../city-overnight-results-2026-11-22/README.md) | Selected 6.23M-decision checkpoint improves reserved sampled mean 32.19 to 95.44; paired gain interval 43.31–82.91 | Road-only Los Angeles, 600-second cap; not every tool or leaderboard competence |
| [Later eight-hour service training](../city-service-long-results-2026-11-23/README.md) | 5.23M added decisions; warm start 98.54, four-hour 101.00, final 77.13 on development cities | More experience did not ensure continued improvement; selected midpoint needs independent confirmation |
| [Road reserve](../road-reserve-learning-2026-11-23/README.md) | Held-out lesson success 2/16 to 13/16, but city mean 81.88 to 54.97 | Real task learning with negative transfer |
| [Small-city practice](../small-city-service-2026-11-24/RESULTS.md) | Offset trial 32,768 decisions; fresh city 121.53 to 123.53, difference interval −16.84 to 20.72 | No reliable city gain; no convergence demonstration |
| [Latest road cost](../road-cost-reward-2026-11-24/RESULTS.md) | 16,384 decisions and 434 games per arm; generous success control 44/64, cost .04 45/64; mean paid units unchanged | One training seed, very early; effectiveness remains inconclusive |

These results come from different checkpoints and evaluation contracts; do not plot them as one comparable score progression. Historical imitation and engineered/calibrated components exist in the inherited prior. Current trials use PPO corrections, not new imitation examples. This is not a clean from-scratch PPO system.

## Code findings and hypotheses

### Trainable scope and effective change

`city_strategy_policy.py` runs the inherited prior under no_grad and enables growth_strategy parameters. `city_wide_strategy_policy.py` adds a learned spatial CNN (16 channels, dilations 1/2/4/8/16), road/Wait corrections and critic. Relative learning rates are Wait 1, roads .3, spatial .1, critic .1. At base .0003 these are .0003/.00009/.00003/.00003 before Adam's adaptation. This protects inherited competence but may slow overturning inherited preferences; that is a hypothesis, not proof of insufficient capacity. The whole-city variant removes the established-service gate, so it is inaccurate to say current opening corrections cannot train.

The latest audit found only about .000130 mean full-action total variation between .04 and control on 16 shared opening states. That is tiny behavioral separation, not an accuracy measurement or a universal bound. Give updates time and log their effect before adding another network. If corrections remain negligible, measure prior-versus-residual logit magnitudes, update norms and gradients before selecting a learning-rate or unfreezing experiment.

### Exploration can favor building: derived concern, not a measured cause

The action distribution normalizes legal road logits separately from Wait. However, MaskablePPO still adds the entropy of the final joint categorical distribution to its objective (confirmed in installed source). Latest checkpoint metadata has ent_coef=.01.

Let p be the total probability of building and q the conditional distribution over legal roads. Joint entropy is H_binary(p) + p H(q). Holding q fixed, maximizing this entropy alone favors p = sigmoid(H(q)); with N equally likely roads this is N/(N+1). Thus separating road normalization removes one action-count effect from the raw logits but does not remove the entropy incentive toward the larger road branch.

This algebra does not establish the actual strength relative to reward gradients, nor prove the observed overbuilding is caused by entropy. First log binary Wait/build entropy, conditional road entropy, and entropy-versus-return gradient contributions on opening and established-service states. If material, compare lower/decaying entropy or separately weighted branch/road exploration in a new matched experiment. Do not silently alter the ongoing reward comparison or remove exploration altogether.

### Critic and time semantics need targeted measurement

Checkpoint metadata confirms gamma=1, GAE lambda=1, vf_coef=1e-5, target_kl=.03, four epochs, batch128. The very low value weight originated in a measured global-gradient-clipping problem on city returns. Its suitability for low-return 60-second lessons has not been established. Assess critic return calibration, explained variance and actual actor/critic update norms; a separate critic optimization/clipping experiment may be cleaner than indefinitely suppressing value learning. Adam scaling means coefficient size alone does not establish update size.

Build decisions consume no simulation time, Wait advances time, and forced waits can be compressed. A default per-decision discount such as .99 would discount long construction sequences even at unchanged game time. Do not copy it from another game without specifying the desired time objective. Audit true terminal versus time-limit bootstrapping and task-horizon observability before mixing finite lessons with continuing-city play.

### Reward and curriculum

The new penalty charges only spent road units, not route shape or distance to a planner's answer. With at most18 units and c=.04, any one-delivery success returns at least .28 while pure waiting returns0. This prevents waiting from being globally better than a successful episode within this fixture, but does not prevent a local optimization trap. Short lessons also cannot teach the eventual value of reserving stock for an arrival that never occurs in them. Success here must be followed by delayed arrivals and mixed city experience.

The deployed action interface still lacks learned use of every tool and weekly selection. Full-city training can proceed before mastering all tools, but this limits eventual strategy. No present evaluation establishes commercial-game fidelity or leaderboard transfer.

## Recommended next program — proposed, not executed

1. Finish a compact instrumentation pass: branch entropy/gradient attribution, residual scale, critic calibration, mask-aware evaluation and finite-horizon handling. Use frozen checkpoints and disposable diagnostic states. No teacher roads, new imitation or hidden future observations. Do not turn this into weeks of unrelated infrastructure.
2. Keep the current reward experiment interpretable. Resume saved control and .04 arms with Adam preserved, identical settings, new nonoverlapping seed cursors, and equal cumulative decision checkpoints. Target 262,144 decisions per arm (32 batches of8192 including the two already completed); evaluate at65,536,131,072 and262,144. This is an engineering budget, not a literature-derived convergence threshold. Estimate roughly2–2.5 additional hours including modest evaluation from measured ~246.5 seconds per16,384 decisions; actual overhead may differ. The current fixed two-rollout launcher needs a real continuation path before execution.
3. Record native success and deliveries first, then road expenditure, stock remaining, time to service, no-build failures, and roads outside observed routes. Never treat fewer roads alone as success. Plot against decisions and wall time. Preserve all checkpoints. Intermediate uncertainty is not an early-stop reason; stop immediately only for invalid rewards/masks, nonfinite learning or process failure. At the budget, classify improving, flat, regressing or uncertain; a flat finite curve is not proof of impossibility. Extend an improving curve under a separately chosen budget.
4. If the audit finds a meaningful entropy/optimizer issue, run it as a separately labeled ablation instead of rewriting the reward comparison. Change one factor and preserve the same start and budget. If recipe-level conclusions matter, repeat with at least three independent training seeds; this is a practical minimum proposal, not a guarantee of statistical power. Different map seeds alone are not training replication.
5. Once connection learning improves, retain it while adding delayed second connections, ample-versus-scarce stock, and native city episodes. Choose and freeze a mixed curriculum for each run; track regressions across earlier skills. Test city transfer early enough to detect reserve-only waiting, without demanding that every intermediate lesson already raise full-city scores.
6. Select candidates on development curves, freeze selection, then evaluate on fresh paired cities using native score and uncertainty. Keep sampled and greedy results separate. Promote only after useful transfer is supported. A long exploratory run may be justified before promotion is proven; a guaranteed large score increase cannot honestly be promised. Add remaining tools/weekly choices incrementally with compatibility checks after the construction/service foundation improves.

## Decision and limits

User decision: request research and review, with no new launch in this turn. Engineering recommendation: keep PPO, preserve the prior and all saves, inspect entropy/critic/update behavior, then fund a stable longer comparison. This supersedes treating short promotion failures as reasons to reject the reward hypothesis. It does not supersede simulator rules or authorize implementation of every suggestion. No new training performance was measured for this report. Existing archives retain original data; this report contains synthesis and explicitly labeled hypotheses. No PDF or new graph was requested or produced.
