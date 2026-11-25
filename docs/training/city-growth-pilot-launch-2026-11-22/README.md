# One-hour growing-city continuation

This user-run pilot starts from the [verified route repair](../city-route-repair-2026-11-22/README.md) on `Maskable-PPO`. The policy initially reproduces the repaired checkpoint's action probabilities. Its opening decisions stay frozen when the repair applies. A new trainable road score and Wait correction are active in other states. Both initialize to zero. The value network starts from the earlier full-city critic. PPO receives only native completed deliveries and uses learning rate 0.00005. Weekly road stock remains automatic.

Thirty-two native Los Angeles workers start on new training seeds in `[92000000,92500000)`. The launcher runs for one hour of active training and saves around 30 minutes and at the end. The terminal reports completed games and a rolling mean score. Use Ctrl+C for a saved stop, then repeat the same command with `--resume`.

## Start

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/run_city_growth_pilot.py \
  --hours 1 --output /home/mohammadjaffal/mini_motorways/output/training/city-growth-pilot-01
```

After training, a paired review compares the repaired reference and saved states on 24 fresh cities in the `[93000000,93100000)` seed range. The run directory's `review.json` records deliveries, scoring games, early stockouts, paid roads and paid units outside observed assigned trip routes. The review adds a separate evaluation period after training. Use the matched reference in this review to judge change. The earlier result of about 37 paid units outside observed routes describes a different set of cities.

## Checks

A two-worker launch added 512 decisions and wrote both checkpoints and a complete two-city review. A separate smoke started from the first saved boundary and restored 16 Adam entries and the two next seed cursors before finishing. Its review used the same disposable test pair. Neither review seed appears in the 24 one-hour review cities. Tensor checks found that the existing actor matched the repaired source exactly while the new road weights updated. Initial opening and growing-city masked predictions were identical to the repaired checkpoint. Perturbing the new head changed the growing-city predictions while the opening predictions still matched.

The full one-hour pilot is user-run. The model ZIPs and Release host are local artifacts.

[Smoke evidence](smoke-verification.json) · [Resume review](resume-smoke-review.json) · [Archive manifest](manifest.json).
