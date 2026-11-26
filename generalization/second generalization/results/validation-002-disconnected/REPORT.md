# Second generalization: paired traffic comparison

Reference: Published Brelsford probabilistic reblocking, seed 0; local reference run
Candidate: Empty added-road fixture; intentional inaccessible endpoints

Synthetic traffic and physical scale. These runs do not reproduce KDD DRL-GNN or establish real-world traffic performance.

| Seed | Reference completed | Candidate completed | Difference | Common completed trips | Paired duration difference (s) |
|---|---:|---:|---:|---:|---:|
| 1001 | 120 / 120 | 50 / 120 | -70 | 50 | -2.09 |
| 1002 | 120 / 120 | 41 / 120 | -79 | 41 | -2.8292682926829267 |
| 1003 | 120 / 120 | 48 / 120 | -72 | 48 | -2.5625 |

Network exporter reported 8 junction-geometry warnings; review export_warnings in comparison.json before research use. No collision or teleport was observed in accepted runs.

Differences are candidate minus reference. Time differences include only journeys completed by both designs; completion and failure counts must accompany them.

Full failure counts, delays, construction cost, diagnostics, binary versions and input hashes are recorded in comparison.json. All individual requests are accounted for in each seed directory.
A synthetic heuristic candidate is an engineering fixture, not a GP result.
