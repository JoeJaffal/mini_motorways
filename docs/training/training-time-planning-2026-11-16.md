# Training time: planning limits — 16 November 2026

User asks for an estimate based on current design. Distinguish fixed-budget runtime from time to successful/human-level play. Required hierarchy, curriculum and credit settings are unresolved; current workload is not implemented or benchmarked. No credible task-specific numerical estimate of time to human performance exists. A fixed step budget is not a prediction of success.

Illustrative end-to-end learner rates (including collection and optimization, excluding setup/evaluation), NOT measured or predicted machine performance:

| Assumed policy decisions/sec | 1 million decisions | 10 million decisions |
| --- | --- | --- |
| 25 | 11.1 hours | 111.1 hours / 4.6 days |
| 100 | 2.8 hours | 27.8 hours |
| 250 | 1.1 hours | 11.1 hours |

Formula: hours = decisions / rate / 3600. [Small arithmetic source](training-time-scenarios-2026-11-16.json). Decisions may be tool/operand/wait selections, not completed edits or simulated seconds. Hierarchy changes what a decision means, so fixed counts across different interfaces are not automatically equivalent. Multiple learner seeds multiply total work; separate computers can run independent experiments but measured speedup is unavailable. Evaluation and implementation are extra; longer games can make simulation costs grow. Earlier pilot15minute learner/30minute overall ceilings are planning caps from an obsolete full-v1 baseline, not measured completion times or current launch authorization.

Read existing 3November hardware assessment and 6November runtime profile. Different models/tasks (including frozen supervised-style forward/backward timings) do not establish throughput for new hierarchical MaskablePPO. No old throughput substituted. Laptop verified hardware and tentative Alienware specs cannot establish samples required to learn. No CUDA/hardware changes or new benchmarks performed.

Next evidence needed, after interface/hierarchy implementation: bounded workload timing separating host/encoding/masks/inference/update and evaluation, then a short learning pilot with held-out learning curves. Runtime can be estimated from measured rate; time to learning still requires sample-efficiency evidence and repeated runs. Official primary-source guidance: [SB3 RL tips](https://stable-baselines3.readthedocs.io/en/master/guide/rl_tips.html) notes model-free sample inefficiency, run variation and lack of universally good defaults; it gives no game-specific success/time guarantee. No numerical scenario selected as a factual forecast or training budget; no training launched.
