# Road spending and first-route audit

The user noticed excessive construction in the [three overnight city replays](../city-overnight-replays-2026-11-22/README.md). On `Maskable-PPO`, replayed the exact archived actions and checked the ending metrics against the original evaluation. All counts below are native road units spent, excluding free attachments. A unit appears in a trip route if its edge appears in an outbound or return route assigned to a vehicle at any observed decision. This is an indicator of roads related to dispatch. Some assigned legs may remain undriven, and future demand could use roads that do not yet appear in a route.

| Replay | Paid road units | Outside observed assigned routes | First matching round trip possible | First delivery |
| --- | ---: | ---: | ---: | ---: |
| Best, 175 deliveries | 109 | 24 | 6 s | 16 s |
| Near average, 85 deliveries | 95 | 32 | 31 s | 42 s |
| Worst, zero deliveries | 25 | 25 | Never | Never |

The worst replay used all 25 starting units by second 44. The earlier [separate feasibility check](../city-road-diagnostic-2026-11-22/README.md) built a working opening on that same world seed using seven units and got a delivery at second 17. The selected policy has learned working routes in some layouts. It still spends heavily on edges that fail to connect a matching pair in some openings.

## Frozen Wait ablation

Compared the selected checkpoint against the same checkpoint with four times the odds of Wait relative to Build. This multiplies only the Wait probability before renormalization. Conditional road selection is unchanged. Eight fresh cities had an open path in the initial legal edge mask and eight started closed. Each pair used the same frozen weights, simulator and action seed, with the standard 600-second cap. These seeds did not serve as prior training, development or reserved test seeds.

Across all 16 fresh cities, the unmodified policy exhausted initial stock by second 14 in nine games. Higher Wait odds eliminated those early stockouts but reduced mean deliveries from 50.19 to 26.31. On the eight hard openings, two games scored in each condition. The unmodified policy's mean opening Wait probability was 10.6% on closed starts and 36.8% on open starts. These values describe this stratified sample. The frozen comparison provides no justification for a blanket Wait increase.

The next proposed controlled exercise should isolate finishing a matching house-to-destination route with distractor edges and variable starting stock. Include starts where another stock expenditure or waiting cannot score because the route is still unfinished, and starts where holding stock until expansion enables the route. Keep ordinary city comparisons in the evaluation. A road search can supply independent feasibility evidence during development, while the agent still picks every edge from its native mask. No training ran and the original checkpoint remains the reference.

## Reproduce

Use the Linux training checkout and a fresh output directory.

```bash
cd /home/mohammadjaffal/mini_motorways
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -u /home/mohammadjaffal/mini_motorways/training/audit_city_roads.py \
  --dll /home/mohammadjaffal/mini_motorways/output/city-road-preflight-build/bin/TrafficHost/release/TrafficHost.dll \
  --checkpoint /home/mohammadjaffal/mini_motorways/output/training/city-overnight-01/checkpoints/city-006234112-96926793.zip \
  --selection /home/mohammadjaffal/mini_motorways/docs/training/city-overnight-replays-2026-11-22/selection.json \
  --output /home/mohammadjaffal/mini_motorways/output/training/city-road-spending-audit-recheck
```

[Replay audits](replays.json) · [Frozen comparison](comparison.json) · [Summary](summary.json) · [Fresh seeds](suite.json) · [Checksums](manifest.json). Checkpoint and compiled host are local.
