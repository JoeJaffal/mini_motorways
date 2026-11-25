# Reward-only PPO on short clear-land roads

User approved testing whether the reward-trained [bend checkpoint](../reward-only-bend-ppo-2026-11-20/README.md) can start roads with no prebuilt tiles, and training if it does not pass. The frozen checkpoint scored 0/100 highest-probability and 3/100 sampled on the same native clear-land fixtures. It retained 100/100 on adjacent gaps and bends in both modes. The older shared-edge checkpoint had scored 33/100 highest-probability on clear land. The warm-start model is the reward-trained bend policy. The five-stage imitation checkpoint is excluded. [Frozen sampled results](baseline-sampled.json), [frozen highest-probability results](baseline-greedy.json), [distance and offset groups](baseline-groups.json).

The opt-in policy keeps its learned local edge scorer and adds a residual scorer that sees geometric offsets from each candidate's endpoints to the visible house and destination approaches. It does not compute or receive routes, search results, or action labels. The added output starts at zero. Preflight found matching masked logits on clear-road, bend and adjacent examples before training. Training uses Maskable PPO, a fresh Adam optimizer, a reward of 1 for connecting within the native budget and 0 otherwise, gamma/trace lambda of 1, 2,048 decisions per rollout and four epochs. Twelve workers train on empty routes and two each rehearse bends and adjacent repairs. Construction is paused and each action is a single legal native edge. Evaluation advances the simulator automatically to 180 seconds or game over. Three native deliveries on 90/100 layouts is the agreed clear-land gate.

The authorized pilot uses CUDA and runs for a maximum of 131,072 build decisions or 30 minutes. It preserves all earlier checkpoints. Follow `tail -F output/training/clear-road-ppo-pilot-01-launch/training.log`. For live status, the `CLEAR` lines describe empty-road episodes only and the `PPO` lines include rehearsal episodes after the optimizer update.

## Completed pilot

The run saved all 131,072 build decisions in 192.98 seconds over 64 rollouts (256 PPO epochs). The final clear-only rollout connected 204/304 training layouts. Checkpoint: `output/training/clear-road-ppo-pilot-01/latest.zip`. [Configuration](config.json), [launch](launch.json), [progress](progress.jsonl), [terminal status](status.json).

| Held-out stage | Before sampled | After sampled | Before highest-probability | After highest-probability |
|---|---:|---:|---:|---:|
| Short clear-land roads | 3/100 | 66/100 | 0/100 | 66/100 |
| Unfinished bends | 100/100 | 100/100 | 100/100 | 100/100 |
| Adjacent gaps | 100/100 | 100/100 | 100/100 | 100/100 |

The clear-land gate remains unmet. The 34 failures were exactly the boards whose house sits two tiles to either side of the destination approach axis. The policy solved 0/16 in one two-tile direction and 0/18 in the other. All 66 aligned or one-tile-offset boards passed in both modes. There were successful layouts at all tested lengths (3–7 tiles). No paired regressions. Across all 100 clear boards, the policy averaged 7.59 deliveries and used 4.09 road units; all 66 successful builds used a different edge set from the scripted reference, which was used only for this retrospective comparison. [Paired and geometry-grouped metrics](metrics.json), [sampled results](final-sampled.json), [highest-probability results](final-greedy.json).

Proposed next change, pending approval: rebalance reward-only training toward the two-tile lateral-offset layouts while retaining simpler routes, bends and adjacent gaps as rehearsal. Report both offset directions separately. The test demonstrates the fixed offset failure; it does not isolate whether rare successful exploratory sequences or representation limits caused it. No obstacle promotion, additional training, teacher data, or changes to native rules.
