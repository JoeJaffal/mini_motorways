# What the latest city policy can do and where it fails

On 23 November 2026 the user asked for direct evidence of the skills retained by the eight-hour road-only policy. On `Maskable-PPO` tested the repaired reference, exact warm start, four-hour save and eight-hour save using the same frozen checkpoints and native simulator as the [long run](../city-service-long-results-2026-11-23/README.md).

| Frozen check | Repaired reference | Warm start | Four hours | Eight hours |
| --- | ---: | ---: | ---: | ---: |
| Short single-pair route | 16/16 | 16/16 | 16/16 | 16/16 |
| Longer single-pair route | 16/16 | 16/16 | 16/16 | 16/16 |
| Full single-pair route behind a delayed gate | 15/16 | 15/16 | 15/16 | 15/16 |
| Single-pair route with two missing edges and a delayed gate | 16/16 | 16/16 | 16/16 | 16/16 |
| Reach an immediately accessible second destination | 24/24 | 24/24 | 24/24 | 24/24 |
| Reach a second destination after its approach opens | 1/24 | 22/24 | 24/24 | 23/24 |
| Score on the long run’s 24 development cities | 23/24 | 22/24 | 24/24 | 21/24 |
| New destinations that scored in those cities | 76/112 | 89/108 | 88/110 | 74/96 |

These counts require a native delivery. Opening cases use a single matching pair, rotated parcel layouts and limited stock. They use new seed pairs separate from the original route-repair confirmation. The second-destination fixtures reuse a controlled benchmark with an already working network, two colors and one or two paid edges needed. The evidence establishes that the tested checkpoints can build multi-edge routes, conserve stock for a visible obstacle, and extend a working network in a small scenario. The counts include the policy’s engineered observation and soft starting preferences. They do not isolate which behavior the eight-hour PPO continuation learned from experience. [Opening summary](opening-summary.json), [second-destination summary](midgame-summary.json) and [original timing experiment](../city-midgame-service-2026-11-22/README.md).

The three continuation saves retained stock until the delayed approach opened in all 24 cases. The same evaluator also replayed its older, separate 20-city development suite. Mean deliveries in model order were 56.85, 62.20, 44.95 and 53.60, with scoring counts 17/20, 13/20, 12/20 and 13/20. The four-hour save’s higher mean on the long-run development seeds did not carry over to those older city seeds. [Second-destination and city summary](midgame-summary.json).

## An exact miss in a full city

Replayed the eight-hour policy’s 14 unserved destinations with roads available at arrival and at least 90 seconds of follow-up. Each original result reproduced. The offline probe looked for a single legal edge between the destination’s existing component and a matching home’s existing component. It tested five candidate edges on two targets by rerunning the original action prefix, drawing the alternative and waiting up to 90 seconds. Three alternatives served one destination. No route-search logic was added to the actor.

At second 277 on Los Angeles seed `99387707`, destination 7 was still unserved and four road units were in stock. The policy chose `(22,9) → (23,9)`, spending one road unit. Substituting `(20,9) → (21,9)` spent the same amount and produced the destination's first native delivery at second 295. Two alternative diagonals also worked. The original game never served the destination. The final policy assigned the three verified connections a combined 0.068% probability at that board. On the exact same board the repaired, warm-start and four-hour policies each gave the verified edges less than 0.1%. The final checkpoint assigned 57.2% to Wait and 42.8% to the road it drew.

This directly demonstrates a failure to prioritize a one-step matching service connection in a busy network. It also shows the blind spot predates the eight-hour continuation. The single-edge probe does not rule out affordable multi-edge routes or later feasible decisions for the other misses, and this witness does not establish why the final checkpoint regressed overall. [Original actions and native alternatives](one-edge-witness.json), [same-state actor probabilities](same-state-policy-probabilities.json) and [review of the aggregate service decline](../city-service-long-results-2026-11-23/SERVICE_FAILURE_ANALYSIS.md).

## Reproduction

The four saved checkpoints appear in model order in the two evaluation summaries. The opening check used `training/evaluate_city_route_repair.py --cohorts route-short route-long route-delay route-gate-two --practice-games 16 --seed 117061 --zone-offset 800000 --workers 6`. The second-destination check used `training/evaluate_midgame_service.py --workers 8` and retained that script’s 20 frozen city cases as well. Both used the archived native DLL for `--dll` and `--city-dll`, with separate output directories. The [single-edge replay script](check_one_edge.py) uses the completed run archive as `--review` and `PYTHONPATH=training` so it can import the existing simulator adapter. Actor probability comparisons used the recorded 326-action prefix, then evaluated the four checkpoints with the exact same observation and legal mask at decision 326. All evaluation used frozen weights. The model ZIPs and native binary remain local.
