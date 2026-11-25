# Authorized matched continuation and diagnostic record

## User decision and scope

After the research assessment the user said “go ahead work on that.” Implement the focused diagnostics and longer matched control/.04 comparison. Preserve all prior files/checkpoints and optimizer progress. Use the previously confirmed Maskable-PPO checkout; Desktop/main untouched. No pull/reset/commit or patch application. Work started24November and crossed midnight into25November2026. This authorization covers the bounded comparison, not an unlimited run or automatic model promotion.

## Frozen diagnostic results (measured)

Both frozen checkpoints played16complete finite practice games each: eight diagnostic layouts207000000–007, paired tight/generous stock, action RNG271000–015. Uniformly subsampled256states per arm from complete trajectories; compute complete remaining Monte Carlo returns and gradients, with no optimizer step. Parameters and checkpoint hashes were unchanged. All episodes terminated without bootstrapping and native/cost ledgers matched. These are diagnostic states, not a fresh confirmation suite.

Control critic MSE20.67 and explained variance−9.97; .04 MSE20.49 and explained variance−9.48. Predictive quality is poor on these samples. This is not an isolated causal explanation for performance.

Mean entropy-to-policy road-head gradient-norm ratio is .00574(control) and .00613(.04), about0.57% and0.61%. The algebraic entropy pressure toward building exists, but this measurement does not show it dominating the reward gradient. Gradients use normalized Monte Carlo advantages under frozen trajectories, not actual later PPO clipped minibatches; direction, cancellation and state coverage also matter. No entropy change is warranted solely by this result.

Both models average roughly46.8%build probability on102sampled pre-service states and0.099%on154post-service states, all with legal builds available. This suggests that, on these particular single-pair lessons, the mess is primarily before successful service; it is not evidence of universal inability to stop after connecting. These state-weighted samples do not establish full-city behavior or general competence.

## Engineering choice

Keep the recipe stable despite critic concerns. Add actual parameter-update norms and gradient monitoring to establish what changes with additional experience. Changing entropy, critic optimization and road cost simultaneously would confound the comparison. If this longer run remains poor, critic optimization is a separately labeled follow-up target; do not silently alter this comparison.

Continue original control/strong final.zip files at16384decisions and512Adamsteps. Each arm receives245760additional decisions, reaching262144cumulative. Same16workers,512steps, batch128,4epochs, LR.0003, gamma/GAE1, vf1e-5, entropy.01,targetKL.03, relative optimizer rates1/.3/.1/.1. Thirty8192-decision rollouts per arm. Save after every rollout with input hashes, next seed/task cursors, losses, gradient norms and parameter-update norms. Frozen prior equality and finite tensors checked every rollout; raw native versus penalized reward ledger checked every episode.

Continuation restores weights and Adam, then explicitly reseeds sampling with241124 and begins fresh episodes208000000onward for both arms. This is not bitwise continuation of the old simulator trajectories; no old environment/RNG snapshot existed. Partial old episodes are not replayed. Both arms receive the same new seed-stream start, though evolving policies may consume it at different rates. Future manual restarts must use a fresh disjoint seed range or recorded worker cursors; the supplied launcher is not an automatic crash-recovery service.

Evaluate saved cumulative65536,131072,262144checkpoints using the already consumed199000000–031 development layouts, two action RNGs each, tight/generous stock:128games per save,768total. Same suite as the short-pilot report. Evaluate native deliveries, success, spent stock, outside-observed-route units and no-build failures. Six evaluations run through a single background evaluation queue, overlapping learning when possible. This may increase training wall time. Fixed checkpoint selection avoids choosing evaluations based on favorable training windows.

At completion archive raw games, curves and paired .04-minus-control bootstrap intervals clustered by32layouts (both RNGs retained),12000draws. One training RNG per arm; no recipe-level replication, independent confirmation or full-city claim. No fresh test cohort consumed. No promotion or automatic extension, even if the short lesson improves.

## Verification and timing

Two disposable one-rollout smoke continuations use209000000 and209100000streams and are excluded from the experiment. First saves24576cumulative and768Adamsteps; reload verifies768steps and finite optimizer moments. Second resumes that checkpoint and checks the final launcher version, explicit post-load RNG reseed, parameter-update logging and progression to1024Adamsteps. Original two arms still start from their original16384saves, not smoke checkpoints.

Estimate2–2.5additional hours for the comparison from earlier throughput; evaluation overlap and machine load may change this. Judge curves over the chosen budget. Abort for invalid ledgers/masks, nonfinite parameters/losses or process failure. Do not interpret an early uncertain evaluation as a failure or automatic stop. At the full budget report improvement, regression or uncertainty honestly; do not promise convergence or leaderboard gains.

## Evidence and local artifacts

Diagnostic JSON/logs, smoke checks, source snapshots, command arguments, input hashes and measurements stay in this archive. Compiled host and checkpoint ZIPs stay only under output/. Historical reports remain historical. No PDF or graph has been produced at launch. Current plan and status indexes point here.
