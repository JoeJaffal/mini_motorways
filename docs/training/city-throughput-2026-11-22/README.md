# Growing-city collection throughput on the Linux PC

The user asked whether the overnight training plan could use the hardware effectively. This check ran on the `mohammad` training checkout on 22 November 2026. The machine has a Ryzen 9 3950X with 16 physical cores and 32 logical CPUs, 31 GiB RAM, and an RTX 2080 Ti with 11 GiB VRAM. PyTorch 2.9.1 with CUDA 12.6 detected the installed GPU.

## Method

The native growing Los Angeles adapter ran through the same SB3 subprocess interface and action-mask query mechanism used for Maskable PPO collection. Each worker issued one randomly selected legal road draw every 12 decision batches when available and used Wait otherwise. Observations, masks, rewards and terminal resets passed through the vector interface. Four warmup batches and process startup were excluded. CPU numerical libraries were limited to one thread per worker. The sweep used eight-second trials, with twelve-second repeats at the higher worker counts. Policy inference and optimization were outside the measurement. The active city checkpoint and learner remain to be prepared.

## Results

| Workers | Decisions/s, initial sweep | Decisions/s, high-worker comparison | Lowest available system RAM during high-worker trial |
| ---: | ---: | ---: | ---: |
| 4 | 319 | — | — |
| 8 | 483 | — | — |
| 12 | 616 | — | — |
| 16 | 762 | — | — |
| 24 | 911 | — | — |
| 32 | 1,054 | 1,070 and 1,084 | 17.0 GiB |
| 40 | — | 1,081 | 14.9 GiB |
| 48 | — | 1,050 | 12.7 GiB |

Collection throughput plateaued around 32–40 workers on this workload. The 40-worker result fell within the run-to-run variation at 32 and used about 2.2 GiB more RAM. Forty-eight workers left less RAM and collected slightly fewer decisions. The 30 × 50 visible state and Maskable PPO mask payload alone occupy roughly 2.08 GiB for 32 workers at 128 decisions per worker, before model state, copies and additional rollout fields.

The vector step occupied roughly 86–87% of collection wall time. A separate single-worker profile of 160 Wait steps in the connected seed-2004 city showed about 1.12 of 1.62 profiled seconds waiting for native host responses. Visible encoding used 0.27 seconds and JSON decoding used 0.19 seconds. These times describe the Python call path and include the native simulator, IPC and scheduling. The collector probe exercised growing boards with simple test actions and its result is a collection-only rate.

## Proposed pilot settings

Use 32 native workers as the starting candidate, cap worker math-library threads, and use CUDA for the actual batched policy and PPO updates. Compare the same starting weights and seeds at 16, 24 and 32 workers once the learner exists. Use end-to-end decisions per second and PPO update time alongside peak system RAM and VRAM, temperature, scoring and survival. Choose the fastest stable setting with the actual rollout buffer and representative later-game traffic. If collection dominates, profile the native observation round trip before adding workers. If learning dominates, tune batch size and GPU utilization against the real policy.

[Initial sweep](worker-sweep.json) · [Higher worker repeats](high-worker-sweep.json) · [Connected game profile](connected-city-profile.txt) · [Host system samples](system-sample.txt).

Reproduce from the training checkout with a Release host built by the [city preflight](../city-road-preflight-2026-11-21/README.md). Use a new output path.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=training \
  .venv/bin/python docs/training/city-throughput-2026-11-22/benchmark_city.py \
  --dll output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --workers 32 40 48 32 --seconds 12 --seed 181020 \
  --output output/training/city-throughput-repeat.json
```

The separate 40-second 32-worker trial collected 48,192 decisions at 1,204 per second and kept 17.0 GiB of system RAM available at the lowest sample. It used a different seed stream and included more resets, so the steady-rate comparison among worker counts uses the matched short trials above. A spot check during the longer collector run showed a 66°C CPU control-sensor temperature. Combined CPU and GPU temperatures still need measuring during the actual pilot. [Longer 32-worker trial](sustained-32.json).
