# First one-build pilot results

The initial and optimized segments comprise one training run on 19 November 2026. The faster collector resumed at 51,200 attempts and 100 optimizer steps with the model and optimizer state intact. The resumed segment stopped at its remaining wall budget. It collected 124,288 cumulative attempts and discarded the final incomplete 1,408-attempt rollout. The final saved checkpoint represents 122,880 attempts, 240 optimizer steps and 60 policy versions. [Training summary and checkpoint counters](training-summary.json), [handoff and configurations](../one-gap-single-build-2026-11-19/README.md#pilot-switched-to-the-faster-collector).

The first training rollout got 2/2,048 builds right. The last full rollout got 994/2,048 (48.5%). The complete original and optimized segments had 912 and 27,966 successful builds respectively. Median collection time for 2,048 attempts fell from 35.13 to 18.95 seconds on the same 16-worker CUDA setup, about 1.85× faster across the two segments. This is an observed comparison across consecutive segments with evolving weights. [Original progress](original-progress.jsonl), [optimized progress](fast-progress.jsonl), [terminal status](fast-status.json).

## Held-out repairs

Each comparison used the same 100 held-out layouts, 20000–20099. All 300 games per comparison ended naturally in one action. Held-out reward is the binary score for connecting the house and destination. The uniform reference samples among all legal builds under either policy evaluation setting.

| Policy | Sampled action | Highest-probability action |
|---|---:|---:|
| Initial | 0/100 | 0/100 |
| Uniform random legal action | 0/100 | 0/100 |
| Trained | 46/100 | 50/100 |

The paired sampled difference against initialization was +46 percentage points (95% bootstrap interval +36 to +56). Each arm used one play per seed per setting. The two comparisons reused the same layout set and are not independent replications. [Sampled summary](sampled-summary.json), [sampled games](sampled-games.jsonl), [highest-probability summary](greedy-summary.json), [highest-probability games](greedy-games.jsonl).

## Did the policy read the board?

At reset, the probability assigned to the exact scripted gap averaged 46.86% with each board's own observation and 46.96% when using observations from the other 99 boards with the target board's unchanged native mask. The exact gap ranked first 50% of the time in both cases. The control suggests the policy's observed success on this set is consistent with action-slot preferences under the legal mask. It provides no evidence that the board observation helps distinguish the correct gap here. This probe does not remove information carried by the legal mask or establish what the model uses outside this layout family. [Board-matching control](board-matching.json).

Engineering recommendation, pending approval: keep the immediate binary reward and test a geometry-focused variant with the gap in more varied arena locations on training and fresh diagnostic layouts. Check performance and the correct-board versus shuffled-board gap against the current policy. A shared local scorer for candidate edges remains a follow-up if diversified layouts and the board-matching check still show reliance on action positions. Do not promote to the longer delivery task on this result. Its native-trip gate was not evaluated. No further training or implementation occurred during this review. The weights and full episode logs remain local.

## User decision after the evaluation

The user chose to keep the current gap placement and improve accuracy first. Layout diversification is deferred. Measure the next authorized continuation against the saved 46/100 sampled and 50/100 highest-probability reference on the same one-build task. No new threshold or training run was authorized by this decision.

## Second pilot started

User authorized continuing the existing one-build task. Resumed the latest saved checkpoint at 122,880 attempts and 240 optimizer steps. The new output is `single-build-pilot-02`; it is capped at 131,072 additional attempts or 30 minutes with the same CUDA and training settings. The first rollout got 978/2,048 correct and advanced to 244 optimizer steps. Follow `output/training/single-build-pilot-02-launch/training.log`. Run active at verification. [Launch and checkpoint details](continuation-launch.json).
