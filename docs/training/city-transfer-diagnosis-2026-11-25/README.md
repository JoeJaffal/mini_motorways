# City-transfer diagnosis and expansion experiment

[Diagnosis and replay findings](DIAGNOSIS.md) · [Experiment plan](PLAN.md)

The user authorized diagnosis, reward checks, targeted training and city transfer evaluation. Correct reward accounting was verified; no road planner or new reward shaping is introduced. Both experiment arms start from the retained stronger original model.

After launch, monitor:

```bash
tail -F /home/mohammadjaffal/mini_motorways/output/training/expansion-comparison-01/run.log
```

Live status is recorded in that output directory and this archive's status.json. The controller trains both bounded arms, evaluates fixed practice and city checkpoints, writes RESULTS.md/results.json and stops. No automatic promotion or further run follows. Weights and native binaries remain local-only; source, measurements, replay frames and hashes are archived.
