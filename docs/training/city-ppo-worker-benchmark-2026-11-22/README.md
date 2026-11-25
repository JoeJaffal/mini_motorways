# Growing-city PPO worker benchmark

This benchmark compares 16, 24 and 32 native workers with the actual CUDA Maskable PPO learner on `Maskable-PPO`. The earlier [native collection benchmark](../city-throughput-2026-11-22/README.md) measured the simulator interface and masks without learning. The [first city PPO pilot](../city-score-pilot-2026-11-22/README.md) used 16 workers and established a measured starting point for the comparison.

## Method

Each trial runs in a fresh Python process from the same frozen city checkpoint, with a fresh optimizer and the same pilot hyperparameters. It uses 128 decisions per worker per rollout, 64 decisions per optimizer batch, four PPO epochs, and a fixed trial budget of 12,288 decisions. That gives six, four or three rollouts at 16, 24 or 32 workers, respectively. All three settings target the same number of minibatch updates if KL stopping stays inactive. Worker count changes when PPO updates take place and which training scenarios are active concurrently. Interpret the trial scores as operational checks on the workload.

Trials ran in the order 16, 24, 32, 32, 24, 16. The reported rate includes the rollout and learning loop, and excludes simulator startup and checkpoint writing. Rollout times include native steps, masking, actor inference and advantage calculation. Update times are measured with CUDA synchronized. RAM, temperatures and board-level GPU utilization were sampled approximately every two seconds after startup. CUDA allocator peaks are also recorded. The benchmark updates temporary model weights and writes no model ZIPs. It uses the pilot's training-only seed stream and leaves the development and reserved test suites untouched.

## Results

| Workers | Decisions/s, two trials | Mean decisions/s | Collection per trial | PPO updates per trial | Lowest available RAM | Peak sampled GPU temp |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 218.9, 221.6 | 220.2 | 29.8 s | 25.8 s | 18.9 GiB | 72 °C |
| 24 | 236.5, 239.7 | 238.1 | 25.3 s | 26.1 s | 15.5 GiB | 72 °C |
| 32 | 255.4, 258.4 | 256.9 | 21.6 s | 26.0 s | 12.9 GiB | 72 °C |

Use **32 native workers** as the starting overnight setting. It won both repeats and averaged 17% more decisions per second than 16 workers and 8% more than 24. The trial with the lowest available RAM at 32 workers still had 12.9 GiB available. The sampled GPU reached 72 °C and 1,391 MiB used. CPU Tctl reached 71.5 °C in the two 32-worker trials. These short measurements establish relative throughput and sampled headroom. Overnight steady-state temperatures and throughput remain unmeasured.

Collection fell from 29.8 to 21.6 seconds per 12,288 decisions between 16 and 32 workers. PPO updates held at roughly 26 seconds, about 55% of loop time at 32 workers. Across the six trials the learner processed 73,728 decisions and 200 completed training games. The job completed each decision budget, optimizer logs were finite, and all 14 existing construction and observation tests passed. The frozen starting checkpoint hash was verified after the sweep. Use the starting transfer checkpoint for later training and retain the two saves from the separate score pilot.

## Reproduce

From the Linux training checkout, use a fresh output root. The loop runs six bounded sessions that perform real PPO updates.

```bash
cd /home/mohammadjaffal/mini_motorways
benchmark_output=/home/mohammadjaffal/mini_motorways/output/training/city-ppo-worker-benchmark-recheck
mkdir "$benchmark_output"
trial=0
for workers in 16 24 32 32 24 16; do
  trial=$((trial + 1))
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/benchmark_city_ppo.py \
    --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
    --checkpoint /home/mohammadjaffal/mini_motorways/output/training/city-road-start-01/city-start.zip \
    --pilot-config /home/mohammadjaffal/mini_motorways/docs/training/city-score-pilot-2026-11-22/config.json \
    --output "$benchmark_output/trial-${trial}-w${workers}" --workers "$workers" || break
done
```

[Comparison and per-trial summary](summary.json) · [Source and evidence checksums](manifest.json). The trial folders contain hardware samples, optimizer logs and episode records. The starting weights and compiled host remain local artifacts.
