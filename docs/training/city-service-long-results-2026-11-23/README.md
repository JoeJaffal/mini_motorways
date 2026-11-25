# Eight-hour growing-city service PPO results

The user asked for an assessment after the detached `city-service-long-01` run. It completed on 23 November 2026 in `/home/mohammadjaffal/mini_motorways` on `Maskable-PPO` at `6bd7f71` plus local work. It trained for 28,809.83 active seconds with 32 native Los Angeles workers and delivery-only reward. PPO added 5,230,592 decisions, completed 10,884 training episodes and saved 32 checkpoints. Throughput averaged 181.56 decisions per active second. The learner logged 1,277 updates with finite loss, approximate KL and value loss. The detached process exited after evaluation. [Launch and readiness record](../city-service-readiness-2026-11-23/README.md).

## Paired development results

The review matched scenario and action-sampling seeds across six checkpoints on 24 new Los Angeles cities. Games ran to native game-over or the 600-second review cap. Of 144 games, 111 ended at native game-over and 33 reached the cap. New destinations in this report are arrivals after the first delivery. Their number varies with how each city develops.

| Checkpoint | Mean deliveries | Cities that scored | New destinations served | New arrivals with empty stock | Paid road units per city outside observed routes | Hit time cap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Repaired reference | 89.17 | 23/24 | 76/112 | 60/112 | 38.42 | 5 |
| Exact warm start | 98.54 | 22/24 | 89/108 | 31/108 | 35.04 | 8 |
| Two hours | 89.50 | 21/24 | 80/111 | 36/111 | 34.88 | 5 |
| Four hours | 101.00 | 24/24 | 88/110 | 24/110 | 35.29 | 10 |
| Six hours | 84.46 | 20/24 | 74/104 | 25/104 | 36.92 | 3 |
| Final | 77.13 | 21/24 | 74/96 | 13/96 | 36.79 | 2 |

The roughly four-hour checkpoint is the development candidate. Its 2,760,704-decision save added 2,674,688 decisions beyond the warm start. It scored in every reviewed city and brought more cities to the time cap. Its paired mean gain was 11.83 deliveries versus the repaired reference (95% bootstrap interval −8.67 to +31.92) and 2.46 versus the warm start (−23.75 to +29.13). Against the warm start it won 11 cities, tied one and lost 12. It served one fewer new destination and used roughly the same number of paid units outside observed trips. The small development mean gain does not establish a PPO improvement over the warm start.

The final policy preserved some road stock at more arrivals, while service and score fell. Empty-stock arrivals dropped from 31/108 to 13/96 compared with the warm start. Mean deliveries fell by 21.42 and 15 fewer new destinations were served. Final games also ended sooner and exposed fewer new destinations. Build actions per simulated minute were 14.06 at the final save versus 13.58 at the warm start. Evidence is consistent with poorer timing or choice of spending, and the aggregate does not establish the mechanism. Paid units outside observed routes are measured within the visible review window. [Raw matched games](games.jsonl), [automatic review](review.json) and [matched analysis against the start](analysis.json).

## Candidate and follow-up

Retain the repaired reference and the narrow warm start. The four-hour candidate is local at `output/training/city-service-long-01/checkpoints/city-002760704-bfd5f98e.zip`. It was chosen using this development suite, so an independent paired evaluation should precede any promotion. Include the warm start and repaired reference, and compare service timing, deliveries, empty-stock arrivals and road units outside assigned trips. The older reserved benchmark and any further training were left untouched on this assessment.

The archived review replayed six exact model files. All 32 saved checkpoint hashes, six reviewed model hashes, the native binary hash and six launch source hashes matched. The 24 matched review seeds were distinct from the readiness suites. The analysis resampled the 24 seed pairs 12,000 times with seed 142915. [Checkpoints and seed cursors](state.json), [configuration](config.json), [scenario/action seed pairs](suite.json), [learner progress](progress.csv) and [integrity manifest](manifest.json). The weights, native binary, raw training episode log and console remain in local output.
