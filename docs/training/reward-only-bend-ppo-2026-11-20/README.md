# Reward-only PPO on unfinished bends

The user approved returning to the PPO checkpoint and testing unfinished bends before adding color matching or stop decisions. The parent `shared-edge-pilot-02/latest.pt` was trained through observed rewards. The separate imitation-trained construction checkpoint is excluded from this run. On the prior frozen test the parent passed 100/100 adjacent gaps and 51/100 bends in highest-probability mode. [Frozen reference summary](../construction-five-stage-2026-11-20/legacy-summary.json).

The pilot uses sb3-contrib Maskable-PPO with the same shared-edge actor and critic parameters at initialization, and a fresh Adam optimizer at learning rate 0.0001. The initial state fingerprint exactly matches the PPO parent. The compact observation adapter retains only the native board channels actually used by that network. A CUDA preflight checked exact channel parity and matching initial masked logits on adjacent and bend fixtures.

The model starts with two or three edits and road units depending on the bend fixture. It chooses any one new legal connection per decision, sees the revised board and legal mask, and gets 1 for reaching the matching destination within the action budget or 0 otherwise. All connecting routes receive the same training reward. No reference actions, imitation labels, or plans were read by the trainer; it only queries reset, legal native builds, and the result of its own actions. Scripted routes are limited to the independent feasibility checker. The host and earlier curriculum wrappers were reused unchanged.

The authorized run uses CUDA, 16 workers, 128 steps per worker per rollout, batches of 128, four PPO epochs, gamma=1, trace lambda=1, entropy coefficient 0.01 and target KL 0.02. Budget is 131,072 build decisions or 30 minutes. The run output is `output/training/bend-ppo-pilot-01`. No earlier checkpoint is overwritten.

## Monitor and evaluation

Follow `tail -F output/training/bend-ppo-pilot-01-launch/training.log`. The logger writes one line per completed rollout update. The atomic `latest.zip` includes the saved policy and PPO optimizer state. The next frozen comparison uses `training/bend_ppo.py evaluate` with the trained checkpoint and same native DLL, and rechecks adjacent gaps and bends on the original 100 held-out layouts for each exercise. Native simulation advances after the last paused build and evaluation measures at least three deliveries.

## Completed run and held-out results

The pilot completed 131,072 saved build decisions in 176.36 seconds and logged 64 rollouts and 256 PPO epochs. Training progressed from 141/813 successful connections in its first rollout to 816/818 in its last. The final policy is `output/training/bend-ppo-pilot-01/latest.zip`. [Launch record](launch.json), [configuration](config.json), [progress](progress.jsonl), [terminal status](status.json).

The offline route verifier confirmed at least two distinct native solutions that reached three deliveries on 75/100 probed training boards and 75/100 held-out bends. Each proof used a separate reset and only the native legal moves. The verifier was not imported by the training process. [Route proof](verified-routes.json), [proof source](verify_routes.py).

| Held-out exercise | Before PPO, sampled | After PPO, sampled | Before PPO, highest probability | After PPO, highest probability |
|---|---:|---:|---:|---:|
| Unfinished bends | 22/100 | 100/100 | 51/100 | 100/100 |
| Adjacent gaps | 97/100 | 100/100 | 100/100 | 100/100 |

A pass means at least three native deliveries after automatic advance. Every final layout reached 180 seconds, and bends delivered 10–12 trips with a mean of 11.18. Mean road stock spent was 2.50 units per bend. There were no paired regressions. The successful policy used a different set of edges from the scripted reference on 52/100 sampled and 36/100 highest-probability bends. Of those, 29 sampled and 16 highest-probability choices differed from both saved demonstration-free feasibility solutions. This is evidence of distinct working builds learned from game outcomes on this suite. It does not establish unrestricted planning, autonomous waiting or performance on empty or blocked routes. One training seed and one sampled attempt per held-out layout were used.

[Before PPO, sampled](baseline-sampled.json), [before PPO, highest probability](baseline-greedy.json), [after PPO, sampled](final-sampled.json), [after PPO, highest probability](final-greedy.json), [paired metrics](metrics.json). Checkpoints, full episode log and native binaries remain local. No training is active.
