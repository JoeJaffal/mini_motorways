**Model replay review remarks — 5 November 2026**

Reviewed recording: training episode 7, Los Angeles, seed 100006, from `output/mbrl/controlled-20261104-205734`. The game scored 284 completed trips and failed at 873 simulated seconds. These are observations and proposed review directions; reward settings and training behavior were not changed as part of this review.

The proposed implementation order and evaluation criteria are in [RECOMMENDED_CHANGES.md](RECOMMENDED_CHANGES.md).

- **Redundant connection at decision 12:** The agent connected `(17,17)` to `(17,18)`, although the tiles were already connected through existing roads. It added no reachable house–destination pair and did not shorten the existing shortest route. It converted two degree-two road nodes into three-way junctions. Its eventual traffic impact has not yet been measured through a counterfactual replay.
- **Very small construction penalty:** Decision 12 received only `-0.005` for adding one link, equal to 0.5% of the reward for one completed trip. There was no additional immediate waiting penalty on that transition. The reward does not explicitly identify redundant connections or unnecessary junctions.
- **Insufficient alternative-action search:** At decision 12, MCTS visited only one root action. It explored consequences of the selected connection without comparing multiple initial choices, such as connecting versus waiting.
- **Correction concerning the three road strokes around decisions 615–625:** Decisions 621–623 were stages of a route from the new house at `(22,8)`. Decision 624 completed its connection to the existing network, raising reachable house–destination pairs from 69 to 72. These strokes were temporarily incomplete, rather than permanently useless roads.
- **Those strokes did receive penalties:** Construction penalties for decisions 621–623 were `-0.01`, `-0.01` and `-0.02`, in addition to traffic-waiting penalties. A blanket penalty on every temporarily disconnected segment could discourage necessary multi-step routes.
- **A different home was persistently ignored:** House 26 at `(10,22)` appeared at simulated second 380 and had no road links at any subsequent recorded frame, through failure at second 873. It remained isolated for 493 seconds. At decision 625, 35 road tiles were available, so its neglect was not explained by road stock being exhausted at that time.
- **Unconnected homes lack a direct reward signal:** The reward has no explicit penalty for an unconnected house. Cars that never depart do not accumulate traffic-waiting penalties. The opportunity cost is indirect through forgone trips or insufficient destination service; connecting every house is not necessarily beneficial, so useful service should be assessed rather than coverage rewarded indiscriminately.
- **The late purple factory was initially unconnected:** Destination 47 appeared at second 724 and first became connected to matching houses at second 770, a delay of 46 simulated seconds. It was eventually connected, so the problem was not permanent absence of a route.
- **Connection did not provide sufficient service:** The purple factory began accumulating overcrowding time at second 816. By second 873 it had demand 9 against capacity 6 and an overcrowding timer of approximately 50.013 seconds. This exceeded the failure threshold and ended the game.
- **Destination backlog is not directly penalized:** The reward does not explicitly penalize unserved destination demand, the duration of destination disconnection, or increasing overcrowding time. The traffic-waiting term measures a different quantity and may not express an unserved destination's crisis clearly.
- **Congestion shaping is disabled:** The recorded reward weights were `alpha=0.05`, `lambdaCost=0.005` and `betaCongestion=0`. Recorded congestion seconds therefore contributed no direct reward penalty in this run.
- **Failure itself has no explicit penalty:** On the final transition, two completed trips earned `+2`, traffic waiting contributed `-0.69`, and the resulting reward was approximately `+1.31` even though the game failed. Failure still removes future earning opportunities and ends value bootstrapping; the missing piece is an explicit immediate failure penalty, not a complete absence of learning consequences.
- **Global reward can obscure a local emergency:** Trips completed elsewhere can outweigh waiting costs while a particular destination approaches failure. Review whether the reward and value representation sufficiently distinguish destination service risk from aggregate traffic performance.
- **Review action proposals as well as rewards:** Check whether useful routes to neglected houses and urgent destinations are actually offered to the model. An action cannot be selected if it is absent from the bounded candidate set.
- **Proposed next checks:** Compare decision 12 against skipping that connection; inspect why house 26 remained unserved; assess demand-aware service and overcrowding signals; and ensure MCTS compares meaningful alternative initial actions. Calibrate any reward changes through paired experiments rather than assigning arbitrary large penalties.

**Observation encoding reference - 6 November 2026**

Verified against the current [environment.py](environment.py). `GRID_CHANNELS = 39` and `SCALAR_FEATURES = 19`; indices below are zero-based, matching Python. These tables document the implemented representation, not evidence that this feature set is optimal.

**39 grid channels**

Implemented by [`visible_grid()`](environment.py#L86), with the first eight fields ordered by `GRID_FIELDS`. The returned array has shape `39 x 30 x 50`, indexed as `[channel, y, x]`. Every channel is zeroed outside the current playable bounds.

| Index | Information | Encoded value |
| ---: | --- | --- |
| 0 | Terrain | Terrain code / 2 |
| 1 | Infrastructure type | Infrastructure code / 4 |
| 2 | Combined road-connection code | Eight-direction bitfield / 255 |
| 3 | Building color | Color code / 7; negative empty-cell values become 0 |
| 4 | Building kind | Empty 0; house 0.5; destination 1 |
| 5 | Outstanding destination demand | Demand / 9 |
| 6 | Reserved demand | Reservations / 9 |
| 7 | Infrastructure awaiting removal | 1 when pending, otherwise 0 |
| 8 | Railway location | 1 on a railway cell, otherwise 0 |
| 9 | Vehicle density | `min(number of cars in cell / 5, 1)` |
| 10 | Playable area | 1 inside current bounds, otherwise 0 |
| 11 | Road connection toward (+1, 0) | 1 if connected, otherwise 0 |
| 12 | Road connection toward (+1, +1) | 1 if connected, otherwise 0 |
| 13 | Road connection toward (0, +1) | 1 if connected, otherwise 0 |
| 14 | Road connection toward (-1, +1) | 1 if connected, otherwise 0 |
| 15 | Road connection toward (-1, 0) | 1 if connected, otherwise 0 |
| 16 | Road connection toward (-1, -1) | 1 if connected, otherwise 0 |
| 17 | Road connection toward (0, -1) | 1 if connected, otherwise 0 |
| 18 | Road connection toward (+1, -1) | 1 if connected, otherwise 0 |
| 19 | House driveway toward (+1, 0) | 1 at that house's cell, otherwise 0 |
| 20 | House driveway toward (+1, +1) | 1 at that house's cell, otherwise 0 |
| 21 | House driveway toward (0, +1) | 1 at that house's cell, otherwise 0 |
| 22 | House driveway toward (-1, +1) | 1 at that house's cell, otherwise 0 |
| 23 | House driveway toward (-1, 0) | 1 at that house's cell, otherwise 0 |
| 24 | House driveway toward (-1, -1) | 1 at that house's cell, otherwise 0 |
| 25 | House driveway toward (0, -1) | 1 at that house's cell, otherwise 0 |
| 26 | House driveway toward (+1, -1) | 1 at that house's cell, otherwise 0 |
| 27 | Destination entrance facing (+1, 0) | 1 at that entrance's cell, otherwise 0 |
| 28 | Destination entrance facing (+1, +1) | 1 at that entrance's cell, otherwise 0 |
| 29 | Destination entrance facing (0, +1) | 1 at that entrance's cell, otherwise 0 |
| 30 | Destination entrance facing (-1, +1) | 1 at that entrance's cell, otherwise 0 |
| 31 | Destination entrance facing (-1, 0) | 1 at that entrance's cell, otherwise 0 |
| 32 | Destination entrance facing (-1, -1) | 1 at that entrance's cell, otherwise 0 |
| 33 | Destination entrance facing (0, -1) | 1 at that entrance's cell, otherwise 0 |
| 34 | Destination entrance facing (+1, -1) | 1 at that entrance's cell, otherwise 0 |
| 35 | Active motorway endpoint | 1 at each endpoint, otherwise 0 |
| 36 | Opposite motorway endpoint's horizontal coordinate | Other endpoint's x / 50, stored at this endpoint |
| 37 | Opposite motorway endpoint's vertical coordinate | Other endpoint's y / 30, stored at this endpoint |
| 38 | Current waiting at each location | `min(sum of cars' waiting seconds in cell / 10, 1)` |

Direction pairs mean change in `(x, y)`; their order is defined by `TrafficWorld.Directions` in [TrafficWorld.cs](../simulation/Assets/Simulation/TrafficWorld.cs#L47).

Terrain codes are land 0, water 1, blocked 2. Infrastructure codes are none 0, road 1, bridge 2, roundabout 3, traffic light 4. Building color codes are red 0, blue 1, green 2, yellow 3, purple 4, orange 5. Red and empty cells therefore both encode color as 0; building kind distinguishes them. The raw fields are populated in `TrafficWorld.Observe()` in [TrafficWorld.cs](../simulation/Assets/Simulation/TrafficWorld.cs#L311).

Demand, reservations, building kind and color are repeated across a building's footprint. Vehicle density includes cars at home; positions are assigned to cells using `int(x), int(y)`. Motorways awaiting removal are excluded from channels 35-37.

**19 scalar features**

Implemented by [`visible_scalar()`](environment.py#L158). The returned array has shape `(19,)`. For inventory rows, clipped stock means `min(100, max(0, stock))`.

| Index | Information | Encoded value |
| ---: | --- | --- |
| 0 | Elapsed simulated time | Seconds / 1800 |
| 1 | Completed trips | Trips / 100 |
| 2 | Number of motorways, including pending removals | Count / 10 |
| 3 | Total outstanding destination demand | Sum across destinations / 100 |
| 4 | Total buildings | Houses and destinations / 100 |
| 5 | Total vehicles | Count, including cars at home, / 200 |
| 6 | Available road stock | Clipped `inventory[0]` / 100 |
| 7 | Available bridge stock | Clipped `inventory[1]` / 100 |
| 8 | Available motorway stock | Clipped `inventory[2]` / 100 |
| 9 | Available traffic-light stock | Clipped `inventory[3]` / 100 |
| 10 | Available roundabout stock | Clipped `inventory[4]` / 100 |
| 11 | Available tunnel stock | Clipped `inventory[5]` / 100; tunnels are not implemented |
| 12 | Number of current upgrade offers | Count / 2 |
| 13 | First offer's material type | `(type code + 1) / 6` |
| 14 | First offer's material quantity | `amount / 30` |
| 15 | First offer's accompanying road quantity | `roads / 30` |
| 16 | Second offer's material type | `(type code + 1) / 6` |
| 17 | Second offer's material quantity | `amount / 30` |
| 18 | Second offer's accompanying road quantity | `roads / 30` |

An absent offer contributes three zeros. Only the first two offers receive detailed features. Offer type codes follow inventory order: road 0, bridge 1, motorway 2, traffic light 3, roundabout 4, tunnel 5. The material labels are also shown in [TrafficViewer.cs](../simulation/Assets/Viewer/TrafficViewer.cs#L274).

Division alone does not impose a maximum: time, demand and other divided values can exceed 1. Only the explicitly clipped vehicle-density, waiting and inventory values saturate at 1. The fixed time divisor of 1800 does not change when a different episode duration is configured.
