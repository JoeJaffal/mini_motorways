# Second generalization: paired traffic comparison

Reference: Published Brelsford probabilistic reblocking, seed 0; local reference run
Candidate: Engineering candidate: published heuristic seed 1; NOT GP

Synthetic traffic and physical scale. These runs do not reproduce KDD DRL-GNN or establish real-world traffic performance.

| Seed | Reference completed | Candidate completed | Difference | Common completed trips | Paired duration difference (s) |
|---|---:|---:|---:|---:|---:|
| 1001 | 120 / 120 | 120 / 120 | 0 | 120 | -4.079166666666667 |
| 1002 | 120 / 120 | 120 / 120 | 0 | 120 | -3.1375 |
| 1003 | 120 / 120 | 120 / 120 | 0 | 120 | -0.7083333333333334 |

Network exporter reported 8 junction-geometry warnings; review export_warnings in comparison.json before research use. No collision or teleport was observed in accepted runs.

Differences are candidate minus reference. Time differences include only journeys completed by both designs; completion and failure counts must accompany them.

Full failure counts, delays, construction cost, diagnostics, binary versions and input hashes are recorded in comparison.json. All individual requests are accounted for in each seed directory.
A synthetic heuristic candidate is an engineering fixture, not a GP result.
