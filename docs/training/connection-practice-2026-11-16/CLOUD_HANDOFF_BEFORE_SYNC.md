# Maskable-PPO continuation — 16 November 2026

User instruction: prepare Stage 1/hierarchy and maximize training efficiency,
**do not run training sessions**. This restriction remains active.

Read [implementation and evidence](../docs/training/connection-practice-2026-11-16/README.md).
This file is a new cloud-checkout handoff; it does not replace the uncommitted
Windows-local planning files physically saved on C:/Users/moham/mini_motorways-maskable-ppo.

## Current state

Linux PC setup was verified by user-supplied outputs: 87 GiB available, isolated
Python 3.12 environment, PyTorch 2.9.1+cu126 on RTX 2080 Ti with calculation and
gradients passing, SB3/Contrib 2.9.2, .NET 8 builds, 99 core and 7 legacy Python
checks passed. This cloud workspace is a different machine and has CPU-only torch.

Changes are local to `/workspace/mini_motorways-maskable-ppo`, branch Maskable-PPO,
baseline 938b9f80e67ca5341920a10e9e671164a474fc38. No commit/push. They are not yet
on the Linux PC or the Windows checkout. Do not suggest pulling to obtain them.

Implemented opt-in native practice reset, paused adjacent edit environment,
manager focus/optional-secondary/executor scheduling, untrained policy prototype,
frozen gate evaluator, and no-training infrastructure benchmark. Scripted timing
fixtures pass 100 validation layouts (10–13 trips by 180 seconds); these are NOT
learned results. Old simulator core 99 suites pass. See report for final checks.

## Remaining work before any training

- Obtain/reconcile Windows-local detailed network, PPO and observation decisions.
  Preserve the approved no-planner, score-only, paused-edit hierarchy/curriculum.
- Finish exact physical masks; current conservative masks admit native rejections.
- Implement the collector and deliberate manager/executor credit/time-discount
  treatment. Prototype policy is NOT a finished hierarchical PPO trainer.
- Implement the new role/zero-time replay format; do not reuse legacy fixed-tick
  replay assumptions or launch old train.py/train_goal.py for this restart.
- Transfer changes, repeat correctness checks on the Linux PC, then run the
  bounded no-training benchmark there. Select worker/device/batch configuration
  from target-machine evidence, not cloud smoke timings. Do not call learn().

Provisional engineering choices (not newly user-approved): 20 road inventory,
other inventory zero; no Stage 1 growth/weekly offers; disjoint destination-x
train/validation positions; explicit 10,000-decision operational cap; shared CNN
prototype dimensions. All are documented for reconciliation in the report.
