# Road-cost continuation — begun24November, launch25November2026

[Plan and diagnostic findings](PLAN.md) · [Live machine status](status.json) · [Diagnostic measurements](diagnostic-summary.json)

The user authorized working on the research recommendations. This run tests the existing reward comparison for longer; it does not change the reward, entropy coefficient, critic weight or policy architecture. No planner or imitation is added. Existing checkpoints and dirty work remain preserved in `/home/mohammadjaffal/mini_motorways` on `Maskable-PPO`.

The controller archives all six development evaluations and generates `RESULTS.md` and `results.json` when both arms finish. No candidate is automatically promoted, and no subsequent training is automatically started. Weight files and host binaries remain local-only.

Monitor:

```bash
tail -F /home/mohammadjaffal/mini_motorways/output/training/road-cost-continuation-01/run.log
```

A training line appears after each8192-decision rollout, approximately every2minutes at pilot speed. Evaluation summaries appear when complete. Machine status is in the output folder's `status.json`; arm-specific status files contain latest completed rollouts. Completion and errors are explicit in these files.
