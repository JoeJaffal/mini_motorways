# Shared-edge pilot results

The first shared-edge pilot completed all 131,072 attempts in 1,399.04 seconds with 256 optimizer steps. It started at 2/2,048 correct in the first rollout and reached 1,480/2,048 (72.3%) in the last. This was a fresh policy on the same one-build stage and reward as the prior whole-board policy. [Configuration](../shared-edge-policy-2026-11-19/pilot-config.json), [progress](progress.jsonl), [status](status.json).

## Frozen evaluation

Each evaluation ran 100 held-out layouts per policy, seeds 20000–20099, with the native action mask. All 600 attempts across the sampled and highest-probability evaluations ended naturally in one build. The fresh initial policy and uniform reference each scored zero in both evaluations.

| Shared-edge checkpoint | Horizontal | Vertical | All |
|---|---:|---:|---:|
| Sampled moves | 44/50 | 40/50 | 84/100 |
| Highest-probability moves | 50/50 | 50/50 | 100/100 |

The [previous whole-board policy](../one-gap-single-build-continuation-2026-11-19/README.md) solved 50/100 either way and solved no horizontal gaps. The new pilot makes a strong improvement on this layout family. This is a single training seed and the new actor and critic representations were changed together. The results apply to one-build connectivity. They do not yet measure delivery performance or transfer to harder variants. [Sampled summary](sampled-summary.json), [sampled games](sampled-games.jsonl), [highest-probability summary](greedy-summary.json), [highest-probability games](greedy-games.jsonl), [orientation totals](metrics.json).

The board-swapping control held each target board's native action mask fixed and applied policy logits from each of the other 99 boards. The exact gap went from top ranked on 100/100 correct-board observations to first in 35.4% of 9,900 mismatches. Mean exact-gap probability fell from 78.64% to 21.06%. Unlike the previous whole-board policy, the action choice benefits substantially from seeing the correct board. The mask still contains target-board information, and this control does not measure out-of-distribution generalization. [Board-swapping results](board-matching.json).

## Follow-up decision

User delegated an additional run if needed. Since sampled accuracy still trailed highest-probability accuracy and the last training rollouts were improving, started a short continuation from the final shared-edge checkpoint. Kept the layouts, task, objective and optimizer settings. The continuation is bounded at 32,768 additional attempts or 10 minutes. Measure sampled and highest-probability accuracy before deciding what to do next. The previous whole-board checkpoints and original shared-edge checkpoints remain local, with full episode logs and binaries.

The resumed run is `shared-edge-pilot-02`. Its first rollout scored 1,622/2,048 and completed four more optimizer steps, bringing the total to 260. It was active when verified. Follow `output/training/shared-edge-pilot-02-launch/training.log`. [Continuation launch and checkpoint provenance](continuation-launch.json).

## Continuation results

Verified on 20 November 2026. The resumed shared-edge pilot completed its 32,768-attempt cap in 352.66 seconds. Final cumulative state is 163,840 attempts, 320 optimizer steps and 80 policy versions. The final training rollout got 2,044/2,048 correct (99.8%). [Saved configuration](continuation-config.json), [resume](continuation-resume.json), [progress](continuation-progress.jsonl), [terminal status](continuation-status.json).

With the same 100 held-out layouts and fixed sampling protocol, sampled accuracy went from 84/100 to 100/100. Sixteen paired layouts improved and none regressed. Highest-probability accuracy held at 100/100. Both evaluation modes scored 50/50 horizontal and 50/50 vertical. All 300 games per mode completed naturally. The comparison uses one sampled attempt per layout and one trained seed. It measures one-build connectivity on this layout family. Longer delivery games and harder layouts remain untested for this checkpoint. No additional training was launched. [Orientation and checkpoint metrics](continuation-metrics.json), [sampled summary](continuation-sampled-summary.json), [sampled games](continuation-sampled-games.jsonl), [highest-probability summary](continuation-greedy-summary.json), [highest-probability games](continuation-greedy-games.jsonl).
