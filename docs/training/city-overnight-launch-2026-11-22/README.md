# Eight-hour growing-city run

The launcher uses the verified city construction-transfer checkpoint and the [32-worker CUDA setting](../city-ppo-worker-benchmark-2026-11-22/README.md) on `Maskable-PPO`. One Maskable PPO agent chooses a legal ordinary road or Wait. The reward is the native delivery score. The simulator applies the weekly road award.

## Start the run

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/run_city_overnight.py \
  --hours 8 --output /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01
```

The terminal shows decisions and completed games after each PPO update. Results go into the run directory. To stop from the terminal, press Ctrl+C and wait for the current rollout/update to finish and the launcher to report a saved stop. To resume, repeat the same command with `--resume`. Use a fresh output directory for a new run.

## Checkpoint and review behavior

The eight-hour budget counts active training. The final rollout and update may carry it past the requested time by one rollout. Start-up and the post-run review are outside the training budget. The launcher writes a checkpoint roughly every 15 minutes and at a graceful stop. The saved ZIP includes policy and optimizer state. The run state records decisions, PPO epochs, active time and each worker's next scenario seed. When a process resumes, games that were in progress at the checkpoint restart on the next unused worker seeds. A hard stop between saves restores the most recent published boundary. Checkpoint files use distinct names, and the current state is published atomically after the ZIP has been written.

After training, the launcher evaluates the starting policy, approximately one saved checkpoint per training hour, and the final checkpoint on the fixed 24 development cities. The selected checkpoint must score in at least as many sampled games as the starting policy. Among eligible checkpoints it uses highest mean deliveries and uses the earlier checkpoint on a tie. The reserved comparison then evaluates the selection and the start on the 32 reserved cities, in sampled and greedy modes. If development selects the start, the reserved comparison evaluates it once. The review can be resumed after an interruption with the same command. The launcher writes its selection and reserved summary to `review.json`.

The verified short score pilot supplied the hyperparameters. The eight-hour duration was requested by the user. The 15-minute save interval, roughly hourly development comparisons and checkpoint selection rule are engineering choices for this run. The GPU/CPU resource evidence is from the short worker benchmark.

## Verification

A four-worker smoke stopped once via SIGTERM and once via process-group Ctrl+C. It saved at 4,096 and 5,120 decisions, restored the Adam state and next seed cursors, then reached 8,192 decisions at 64.9 active seconds. A separate 32-worker smoke ran 4,096 decisions and saved successfully. The post-run workflow selected a checkpoint on two disposable development cities before evaluating two different disposable reserved cities. The real development and reserved suites were untouched in these tests. A changed reserved seed checksum was rejected. All 14 existing construction and observation tests passed. The verified starting checkpoint hash was unchanged.

[Resume smoke evidence](resume-verification.json) · [Disposable review summaries](review-verification.json) · [Archive manifest](manifest.json). The smoke weights and compiled simulator remain local.
