# Score-only PPO continuation for hard city openings

The user approved the next bounded continuation after the [opening and destination coverage diagnostic](../city-road-diagnostic-2026-11-22/README.md). It starts from the selected [overnight checkpoint](../city-overnight-results-2026-11-22/README.md) at 6,234,112 decisions on `Maskable-PPO`. Its Adam state is restored. The learning rate is reduced to 0.00005 for the continuation. Other optimizer settings and the 32-worker CUDA configuration carry over.

Sixteen workers select fresh starts where the opening legal edge mask has no path between the two initial matching parcels. Sixteen workers use ordinary unfiltered starts. The classifier samples scenarios at reset and has no role in choosing road actions. Both cohorts start from time zero with normal road stock. PPO receives only the native delivery score. Every episode can last 1,200 simulated seconds, with the visible observation clock kept on its original 600-second scale. The training pool uses `[79100000, 79500000)`, separate from the overnight, diagnostic, development and reserved seeds.

The continuation is capped at 65,536 additional decisions with a save at 32,768. The parent, midpoint and final checkpoints are evaluated on the same 16 closed openings and 16 unfiltered development cities using fixed sampling seeds. Development metrics include first delivery, early stock exhaustion, zero scores, deliveries after 600 seconds, and whether the most overcrowded destination at a late game-over had a supply route. The development suite is separate from the curriculum. The reserved cities are held back.

## Results

The run ended at the requested 65,536 added decisions after 288.02 seconds. It ran 64 PPO epochs and recorded 201 training episodes. The closed-opening workers accounted for 153 completed episodes with 51 scoring. The ordinary workers completed 48 with 43 scoring. The cohorts reset at different rates. Both checkpoints and the overnight parent matched their recorded hashes. All 14 existing construction and observation tests passed.

| Development measure | Overnight parent | Midpoint | Final |
| --- | ---: | ---: | ---: |
| Hard openings scoring | 2/16 | 3/16 | 2/16 |
| Hard openings exhausting stock by second 14 | 16/16 | 15/16 | 16/16 |
| Hard-opening mean deliveries | 0.38 | 2.38 | 0.69 |
| Ordinary cities scoring | 15/16 | 13/16 | 13/16 |
| Ordinary-city mean deliveries | 133.63 | 91.63 | 86.38 |
| Ordinary cities past ten minutes | 5/16 | 2/16 | 3/16 |
| Ordinary-city mean deliveries after second 600 | 35.81 | 10.69 | 14.00 |

The midpoint's paired mean hard-opening gain was 2.00 deliveries, with a 95% paired bootstrap interval from −0.31 to +5.69. By the final save, the rare gains in hard openings had largely disappeared. The final change on ordinary cities averaged −47.25 deliveries, with a paired interval from −93.63 to −1.81. Both continuations lost late-game deliveries on this suite. The run changes scenario mix, time cap and learning rate together, so it cannot identify the cause of the regression by itself.

Keep the overnight checkpoint as the reference and preserve both continuations for comparison. A more direct next experiment would isolate early Build-or-Wait timing on fresh variants while keeping the existing road scorer and ordinary-city retention checks. A longer repetition of this mixed setup needs stronger evidence. The reserved suite was unused.

## Reproduce

Use fresh output directories in the Linux training checkout. This command starts the bounded CUDA continuation.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/train_city_opening_pilot.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --parent /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-opening-pilot-repeat
```

The evaluation command loads the recorded local checkpoints on CPU.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/evaluate_city_opening_pilot.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --suite /home/mohammadjaffal/mini_motorways/docs/training/city-opening-pilot-2026-11-22/suite.json \
  --checkpoints /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-opening-pilot-01/city-added-0032768.zip \
    /home/mohammadjaffal/mini_motorways/output/training/city-opening-pilot-01/city-added-0065536.zip \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-opening-pilot-dev-recheck
```

[Fixed suite](suite.json) · [Training configuration](config.json) · [Saved checkpoint hashes](status.json) · [Training episodes](training-episodes.jsonl) · [Paired development summary](development-summary.json) · [Per-game city traces](development-games.jsonl) · [Archive manifest](manifest.json). Weight ZIPs and compiled artifacts remain local.
