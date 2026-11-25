# Growing-city score-only PPO pilot

This is the first city weight-update milestone on `Maskable-PPO`. The pilot began from the [selected construction-transfer checkpoint](../city-policy-start-2026-11-22/README.md). One policy chose an ordinary road edge or Wait through the simulator's native action mask. Only the change in native completed deliveries gave reward. Weekly road stock remained automatic.

## Run design

The bounded run used 16 native simulator workers, 128 decisions per worker per rollout, batches of 64, four PPO epochs per rollout, learning rate 0.0001, gamma 1, GAE lambda 0.95, entropy coefficient 0.01 and target KL 0.03. These are engineering choices for a first pilot. The optimizer started fresh. Training used interleaved scenario seeds in the training-only range `[78000000, 79000000)`. The pilot saved checkpoints at 12,288 and 24,576 decisions. The 24 fixed development seeds are in a different range. The [32-seed test suite](../city-frozen-baseline-2026-11-22/README.md) was kept out of both training and development evaluation.

The comparison applies each frozen checkpoint, including the start, to the same development scenarios and the same sampling seeds. Sampled and most-probable-action play are evaluated separately. Each sample starts with an empty road network. Candidate selection uses only these development games.

## Training and hardware

The run took 112.64 seconds and processed 218.18 decisions per second end to end, including rollout collection and PPO updates. It logged 48 PPO epochs and 76 completed training games with a mean score of 19.5, a best score of 103 and 29 zero-score games. The first 41 completed games averaged 13.93 and the final 35 averaged 26.03. Those groups used different draws and seeds. The paired development comparison below is the basis for checkpoint selection.

PyTorch peaked at 682 MiB allocated and 846 MiB reserved CUDA memory. Fifteen samples after the halfway save showed 61–70 °C GPU temperature, 21–78% reported GPU utilization and at least 18.3 GiB system RAM available. The sampled CPU control temperature ranged from 57.4 to 69.6 °C, with a separate midpoint spot check of 71 °C. These samples describe this 16-worker run. The 16/24/32-worker sweep with the actual learner remains open.

## Results

| Checkpoint | Sampled mean score | Sampled median | Sampled best | Scoring games | Median survival | Mean roads spent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Starting transfer | 35.46 | 33.5 | 80 | 21/24 | 298.55 s | 67.75 |
| 12,288 decisions | 38.58 | 36.0 | 109 | 21/24 | 303.83 s | 71.54 |
| 24,576 decisions | 34.83 | 33.5 | 94 | 21/24 | 299.95 s | 69.58 |

All 144 frozen development games reached native game-over. The halfway checkpoint improved by 3.13 deliveries on average versus the start, with 11 wins, six ties and seven losses. Its 95% paired bootstrap interval for mean improvement was −7.17 to +13.25. The final checkpoint averaged 0.63 fewer deliveries than the start, with nine wins, six ties and nine losses and an interval of −11.29 to +9.67. Neither candidate improved the number of scoring games. Keep the original transfer checkpoint as the reference and retain the halfway checkpoint as the better of the two pilot candidates. This sample leaves the apparent halfway gain uncertain.

All three greedy evaluations scored zero. The final checkpoint made road edits in two games, while the other greedy checkpoints always waited. On the 24 opening boards the mean probability of Wait was 50.0% at the start, 50.2% halfway and 49.6% at the end. Wait remained the most probable individual opening action on all 24 boards at every checkpoint. [Opening action measurements](opening-diagnostics.json).

The next hardware milestone is to compare actual collection and PPO throughput at 16, 24 and 32 simulator workers. Any longer run should keep the frozen start as its comparison and track score and zero-score frequency before promoting a checkpoint. The reserved test seeds were unused. All 14 existing construction and observation tests passed.

## Reproduce

Run from the Linux training checkout. Use new output directories for training and evaluation. The training command below starts a bounded CUDA learning run.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/train_city_score_pilot.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint /home/mohammadjaffal/mini_motorways/output/training/city-road-start-01/city-start.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-score-pilot-repeat
```

Frozen evaluation of the archived pilot's local checkpoints uses CPU workers.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/evaluate_city_checkpoints.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoints /home/mohammadjaffal/mini_motorways/output/training/city-road-start-01/city-start.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-score-pilot-01/city-0012288.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-score-pilot-01/city-0024576.zip \
  --seed-suite /home/mohammadjaffal/mini_motorways/docs/training/city-score-pilot-2026-11-22/development-seeds.json \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-score-pilot-dev-recheck
```

[Configuration](config.json) · [Run status and checkpoint hashes](status.json) · [Learner log](progress.csv) · [Training episodes](training-episodes.jsonl) · [Second-half hardware samples](hardware-samples.csv) · [Development seeds](development-seeds.json) · [Development summary](development-summary.json) · [Development episodes](development-episodes.jsonl) · [Archive manifest](manifest.json). Model weights and compiled simulator artifacts are local-only.
