# Three frozen overnight city replays

The user requested three examples from the road-only model. The source is the 32 sampled reserved games from the [selected overnight checkpoint](../city-overnight-results-2026-11-22/README.md), evaluated on Los Angeles with a 600-second cap. The average was 95.44 deliveries. The middle example is the recorded score closest to that mean. Among zero-score ties, the example with the earliest game-over was chosen.

| Example | City seed | Deliveries | Simulated time | Outcome |
| --- | ---: | ---: | ---: | --- |
| Best | 1720940018 | 175 | 10:00 | Evaluation cap reached |
| Closest to the mean | 1219410182 | 85 | 7:35 | Native game-over |
| Worst | 577433799 | 0 | 2:15 | Native game-over |

The replays use the archived scenario and action seeds, exact checkpoint and native host. Road stock, score, traffic and highlighted build actions come from native replay observations. The HTML viewer needs only a browser. The [action sequences and HTML checksums](selection.json) are archived here. The generated pages, model weights and native DLL are local artifacts under `output/`.

## Reproduce

Run this from the Linux training checkout with a fresh output path. The script reruns the selected frozen games and checks the results against the archived evaluation.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/export_city_replays.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
  --evaluation /home/mohammadjaffal/mini_motorways/docs/training/city-overnight-results-2026-11-22/reserved-episodes.jsonl \
  --summary /home/mohammadjaffal/mini_motorways/docs/training/city-overnight-results-2026-11-22/reserved-summary.json \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-overnight-replays-recheck
```

All three reproduced the archived result, decision counts and end conditions. Headless Chrome verified the opening frame, play, step, timeline seek, ending score and reset on every page. No training ran.
