# Where the overnight city policy fails

The frozen [overnight checkpoint at 6,234,112 decisions](../city-overnight-results-2026-11-22/README.md) was tested on `Maskable-PPO`. The diagnostic replayed the four selected-policy zero-score reserved cities with the original action draw and seven alternate action seeds per city. A separate set of 24 fresh Los Angeles cities used a 1,200-second simulation cap. The policy kept the familiar 600-second observation clock, whose remaining-time input reaches zero at second 600. Six matched 600-second runs reproduced the longer runs' score and sampled state up to that limit. All four original zero-score replays matched the archived scores, ending times and road stock. Route and traffic diagnostics were recorded from the simulator for analysis and excluded from the policy observation.

## The opening failures

| City seed | Policy scored | Diagnostic connection built at | Road units used | First diagnostic delivery |
| ---: | ---: | ---: | ---: | ---: |
| 494606252 | 2/8 | 60 s | 5 | 74 s |
| 518055469 | 1/8 | 75 s | 6 | 85 s |
| 577433799 | 7/8 | 0 s | 7 | 17 s |
| 2082947643 | 2/8 | 60 s | 7 | 71 s |

Nineteen of the 20 scoreless opening replays used up their starting stock by second 14. Six never established any matching round-trip route. No scoreless opening recorded a visible vehicle waiting for at least 10 seconds. A separate legal-route check waited for the board to evolve and constructed a scoring connection with 5–7 of 25 starting road units in all four cities. It used an offline search of the legal mask and native single-edge confirmation, including automatic free parcel attachment. The first successful check at a five-second sample is a feasibility witness. It does not establish the earliest possible opening. This search played no part in policy evaluation or training.

## After ten minutes

Nineteen of 24 fresh cities scored. Five survived past 600 seconds and none reached 1,200. Those five added 92–228 deliveries after ten minutes and made a delivery within 2.5 seconds of game-over. In all five, the most overcrowded destination at failure had no matching round-trip supply route. The simulator never showed a visible vehicle waiting at least 10 seconds in those games. Short waits and queues may still affect play. The recorded endings point to unmet service at individual destinations while the rest of the network was delivering.

The next proposed bounded PPO experiment should keep native delivery reward and preserve normal starts while deliberately sampling fresh openings where a matching connection becomes feasible later. Measure early stock depletion, first-route time, first-delivery time and zero-score rate. Also track how quickly a newly spawned destination gets service in longer games. Leave the diagnostic and reserved cities out of checkpoint selection. The selected overnight checkpoint stays frozen as the comparison. No training ran.

## Reproduction

From the Linux training checkout, use a new output directory. Both commands are evaluation-only.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/diagnose_city_policy.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
  --suite /home/mohammadjaffal/mini_motorways/docs/training/city-road-diagnostic-2026-11-22/suite.json \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-road-diagnostic-recheck

PYTHONPATH=/home/mohammadjaffal/mini_motorways/training \
  .venv/bin/python /home/mohammadjaffal/mini_motorways/docs/training/city-road-diagnostic-2026-11-22/opening_witness.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --suite /home/mohammadjaffal/mini_motorways/docs/training/city-road-diagnostic-2026-11-22/suite.json
```

[Per-game traces](games.jsonl) · [Summary](summary.json) · [Feasibility paths](opening-witness.json) · [Seed suite](suite.json) · [Source and data checksums](manifest.json). The checkpoint and native DLL remain local. The existing 14 tests and the seed-2004 native city preflight passed.
