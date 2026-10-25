# Traffic and proportions investigation — 26 October 2026

## Trigger and scope

The user supplied one Traffic Lab screenshot showing a long mixed-color queue and a large roundabout, plus two original-game screenshots of Los Angeles. The screenshot network was not replayed exactly: it does not include the full connection graph or vehicle state. These changes address reproduced faults, not a claim that every queue is eliminated or the original game is now identical.

## Local reference research

Read-only inspection of the installed game's `App.dll` examined RoadTileAtlas, Roundabout, RoadChunkModel, LaneModel and IntersectionEvaluatingProcess. The installed assemblies and extracted classes remain outside the repository. Existing assembly provenance is in [REFERENCE_DATA.json](../Docs/REFERENCE_DATA.json).

The atlas uses a road half-width of 0.4 world units and lane offset of 0.2; our tile is two world units. These give a rendered road width of 0.4 tiles and lane offset of 0.1 tiles. A roundabout's normalized diagonal boundary point, relative to a center two world units away, gives a circular centerline radius of `sqrt(5 - 2*sqrt(2))/2` tiles (about 0.737). Our previous path radius was 0.94, and the drawing used an independent radius of 1.13 for the outer road edge.

The renderer now derives both roundabout road edges from the same radius as the sampled circular lanes. Quarter arcs join continuously. Entry and exit connectors remain our cubic approximations. House width changed from 0.52 to 0.70 tiles based on proportions in the supplied screenshots; that is a visual estimate, not an extracted prefab measurement. Road width, borders and lane offset were aligned with the atlas constants. Destination footprints and camera fitting were not recalibrated in this pass.

The local junction implementation also treats a traversing vehicle close to the end of its lane differently from a vehicle still crossing. Traffic Lab instead held its entire conflicting lane and then its previous lane into the next segment. Adjacent intersections could retain each other's crossing reservations. Traffic Lab now releases that crossing reservation in the exit section; same-lane following still enforces vehicle spacing. Experimental changes to future-junction lookahead did not resolve the reproduced waits and were discarded.

## Controlled before/after runs

OriginalReference / Los Angeles, seeds 40–43, 400 simulated seconds. Rebuild debug roads every 200 ticks (10 seconds), replenish road inventory to 1000, extend overcrowding failure to 100000 seconds. These are diagnostic networks, not standard-play scores, an RL policy, or a synchronized comparison to the original game.

| Seed | Before trips | Crossing fix only trips | Final proportions + fix trips |
| --- | ---: | ---: | ---: |
| 40 | 45 | 69 | 70 |
| 41 | 54 | 58 | 56 |
| 42 | 57 | 65 | 65 |
| 43 | 55 | 78 | 78 |

Across the four final snapshots, vehicles waiting longer than 20 seconds decreased from **72 to 0**. This measures those snapshots only; it does not prove that no vehicle waited longer earlier or that all possible networks are deadlock-free.

Reproduce the final diagnostic using the headless host's `--evaluate-crossings` option. The shared suites additionally cover the seed-42 crossing cycle, continuous circular geometry, and a six-car, three-approach roundabout conversion followed until all six deliveries and home returns complete. The full suite is 37 checks.

## Remaining limits

The user's precise stuck network still needs a captured connection/vehicle state to replay. Saturated networks can still queue. Roundabout entry/exit splines, lane transitions during construction, parking access serialization, house art, destination art, map coastline presentation and camera framing remain approximations. These results do not certify original-game parity.
