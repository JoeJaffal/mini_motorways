# Model inputs and hardcoded limitations

Verified against the working-tree implementation on 2026-11-07. This describes
the current simulator-search AlphaZero model, including its encoder, action
proposer, guards, search, reward and training/evaluation protocol. Historical
checkpoints and preserved `output/.../source/` implementations can differ.

The inventories below cover every neural-network input and the restrictions
imposed by the MBRL pipeline. Simulator physics, city schedules and material
package tables are separate environment rules, not learned model parameters;
their boundary and compatibility limitations are recorded at the end.

Source of truth:

- [environment.py](../environment.py): `visible_grid`, `visible_scalar`,
  `TrafficEnv`, `Host`, `ReplayBranch`, `SnapshotBranch`.
- [actions.py](../actions.py): `DIRS`, `TOOLS`, `_features`, `candidates`,
  `_path`, `_next_stroke`, `candidate_matrix`.
- [proposals.py](../proposals.py): `Cooldowns`, `ActionGuard`, `proposals`.
- [alphazero.py](../alphazero.py): `Network`, `search`, `ReplayMixture`,
  `finish_episode`, `train_batch`.
- [parallel_search.py](../parallel_search.py): optional shared-tree worker pool.
- [train.py](../train.py), [experiment.py](../experiment.py),
  [protocol.py](../protocol.py), [evaluate.py](../evaluate.py).

## 1. Complete neural-network input signature

`Network.forward(grid, scalar, actions, mask)` receives four tensors. `B` is the
batch size and `A` the padded candidate count, normally 48.

| Argument | Normal shape | Type | Meaning |
| --- | --- | --- | --- |
| `grid` | `(B, 42, 30, 50)` | Float | Current spatial state; indices are `[channel, y, x]` |
| `scalar` | `(B, 19)` | Float | Current global state |
| `actions` | `(B, 48, 26)` | Float | Features of each proposed action |
| `mask` | `(B, 48)` | Boolean | `True` for a real candidate; `False` for padding |

The encoders and candidate matrix return `float32`. Collected grid, scalar and
action features are stored in replay as `float16`, then converted to `float32`
for training. The mask remains Boolean. Replay also stores policy targets,
rewards and return targets; these are supervision, not forward-pass inputs.

The outputs are one state value per batch item and one logit per candidate.
Padding logits become `-1e9`. `predict()` applies softmax to real candidates.
The value head uses state features only; action features enter the policy head.

## 2. All 42 spatial channels

Raw flat arrays use index `y * 50 + x`. All channels are multiplied by the
current playable-area mask. Playable bounds are minimum-inclusive and
maximum-exclusive, clipped to the 50 by 30 canvas.

Direction order is fixed throughout the encoder and proposer:

| Direction index | `(dx, dy)` |
| ---: | --- |
| 0 | `(+1, 0)` |
| 1 | `(+1, +1)` |
| 2 | `(0, +1)` |
| 3 | `(-1, +1)` |
| 4 | `(-1, 0)` |
| 5 | `(-1, -1)` |
| 6 | `(0, -1)` |
| 7 | `(+1, -1)` |

| Index | Input | Exact encoding before playable masking |
| ---: | --- | --- |
| 0 | Terrain | `terrain / 2`: land 0, water 0.5, blocked 1 |
| 1 | Infrastructure | `infrastructure / 4`: none 0, road 0.25, bridge 0.5, roundabout 0.75, traffic light 1 |
| 2 | Combined connections | Eight-direction connection bitfield `/ 255` |
| 3 | Building color | `max(buildingColors / 7, 0)` |
| 4 | Building kind | `buildingKinds / 2`: empty 0, house 0.5, destination 1 |
| 5 | Destination demand | `demand / 9` |
| 6 | Reserved demand | `reservations / 9` |
| 7 | Pending infrastructure removal | `pendingRemovals / 1` |
| 8 | Railway occupancy | 1 at cells listed in `railLines[].cells`, otherwise 0 |
| 9 | Vehicle density | `min(number of vehicles in cell / 5, 1)` |
| 10 | Playable area | 1 within current playable bounds, otherwise 0 |
| 11 | Connection in direction 0 | Bit 0 of `connections` |
| 12 | Connection in direction 1 | Bit 1 |
| 13 | Connection in direction 2 | Bit 2 |
| 14 | Connection in direction 3 | Bit 3 |
| 15 | Connection in direction 4 | Bit 4 |
| 16 | Connection in direction 5 | Bit 5 |
| 17 | Connection in direction 6 | Bit 6 |
| 18 | Connection in direction 7 | Bit 7 |
| 19 | House driveway direction 0 | 1 at a house's cell when `drivewayDirection == 0` |
| 20 | House driveway direction 1 | Same for direction 1 |
| 21 | House driveway direction 2 | Same for direction 2 |
| 22 | House driveway direction 3 | Same for direction 3 |
| 23 | House driveway direction 4 | Same for direction 4 |
| 24 | House driveway direction 5 | Same for direction 5 |
| 25 | House driveway direction 6 | Same for direction 6 |
| 26 | House driveway direction 7 | Same for direction 7 |
| 27 | Destination entrance direction 0 | 1 at each entrance cell paired with direction 0 |
| 28 | Destination entrance direction 1 | Same for direction 1 |
| 29 | Destination entrance direction 2 | Same for direction 2 |
| 30 | Destination entrance direction 3 | Same for direction 3 |
| 31 | Destination entrance direction 4 | Same for direction 4 |
| 32 | Destination entrance direction 5 | Same for direction 5 |
| 33 | Destination entrance direction 6 | Same for direction 6 |
| 34 | Destination entrance direction 7 | Same for direction 7 |
| 35 | Active motorway endpoint | 1 at each endpoint of a motorway not pending removal |
| 36 | Opposite endpoint x | Other endpoint's `x / 50`, stored at this endpoint |
| 37 | Opposite endpoint y | Other endpoint's `y / 30`, stored at this endpoint |
| 38 | Current vehicle waiting | `min(sum(vehicle.waiting in cell) / 10, 1)` |
| 39 | Destination capacity | `demandCapacity / 10` across the destination footprint |
| 40 | Destination load relative to capacity | `max(0, demand) / demandCapacity` across the footprint |
| 41 | Overcrowding timer | `overcrowdedFor / 50` across the footprint; 50 is the OriginalReference failure threshold |

Additional encoding constraints:

- The canvas must be exactly `50 x 30`; other dimensions raise `ValueError`.
  Each of the first eight raw fields must contain exactly 1,500 values.
- Colors are numeric codes, not one-hot features: red 0, blue 1, green 2,
  yellow 3, purple 4, orange 5. Empty raw color `-1` becomes 0, so red and
  empty share the color value; building kind supplies the distinction.
- Kind, color, demand and reservations are repeated over building footprints
  by the simulator. They do not identify separate buildings within the tensor.
- Vehicle positions are assigned using `int(x), int(y)`. Counts include vehicles
  at home. Density loses distinctions above five vehicles per cell; waiting
  loses distinctions above ten accumulated current waiting seconds per cell.
  Vehicle identities, colors, stages and routes are not separate grid features.
- Entrance cells and directions are paired with `zip`. Empty lists fall back
  to `[entrance]` and `[drivewayDirection]`; mismatched list lengths silently
  use only the paired entries.
- Pending motorways disappear from channels 35-37. Endpoint features do not
  include IDs, removal progress or drawn motorway geometry. If endpoints
  overlap, coordinate assignments overwrite earlier ones at that cell.
- Masking discards all spatial information outside the playable area. Global
  scalars are computed from the full observation rather than this masked grid.
- Except for the explicit color clamp, vehicle-density cap and waiting cap,
  division does not clip channels to `[0, 1]`. For example, demand can exceed 1.

## 3. All 19 scalar features

Inventory order is fixed: road, bridge, motorway, traffic light, roundabout,
tunnel. Exactly six inventory values are required.

| Index | Input | Exact encoding |
| ---: | --- | --- |
| 0 | Elapsed simulated time | `time / 1800` |
| 1 | Completed trips | `tripsCompleted / 100` |
| 2 | Motorway count | `len(motorways) / 10`, including pending removals |
| 3 | Total destination demand | `sum(b.demand for non-house buildings) / 100` |
| 4 | Building count | `len(buildings) / 100` |
| 5 | Vehicle count | `len(vehicles) / 200`, including vehicles at home |
| 6 | Road stock | `min(100, max(0, inventory[0])) / 100` |
| 7 | Bridge stock | Same clipping for `inventory[1]` |
| 8 | Motorway stock | Same clipping for `inventory[2]` |
| 9 | Traffic-light stock | Same clipping for `inventory[3]` |
| 10 | Roundabout stock | Same clipping for `inventory[4]` |
| 11 | Tunnel stock | Same clipping for `inventory[5]`; no tunnel action exists |
| 12 | Upgrade-offer count | `len(upgradeChoices) / 2` |
| 13 | First offer type | `(type + 1) / 6` |
| 14 | First offer material amount | `amount / 30` |
| 15 | First offer road amount | `roads / 30` |
| 16 | Second offer type | `(type + 1) / 6` |
| 17 | Second offer material amount | `amount / 30` |
| 18 | Second offer road amount | `roads / 30` |

Missing offers contribute three zeros each. Only the first two offers receive
scalar details, even if the observation contains more. Offer types use the
inventory indices 0-5. Stock above 100 is indistinguishable from 100; negative
stock is indistinguishable from zero. Other scalar divisions do not clip.
The fixed time divisor remains 1800 when the episode horizon is changed.

## 4. All 26 features per candidate and the mask

Candidate slots are temporary proposals, not persistent global action IDs.
`_features()` creates 25 features; `candidate_matrix()` appends priority.

| Index | Input | Exact encoding |
| ---: | --- | --- |
| 0 | Wait kind | `float(kind == 0)` |
| 1 | Draw kind | `float(kind == 1)` |
| 2 | Upgrade kind | `float(kind == 2)` |
| 3 | Create motorway kind | `float(kind == 3)` |
| 4 | Build/remove tile kind | `float(kind == 4)` |
| 5 | Connect kind | `float(kind == 5)` |
| 6 | Driveway kind | `float(kind == 6)` |
| 7 | Edit motorway kind | `float(kind == 7)` |
| 8 | Remove motorway kind | `float(kind == 8)` |
| 9 | Road tool | `float(tool == "Road")` |
| 10 | Bridge tool | `float(tool == "Bridge")` |
| 11 | Traffic-light tool | `float(tool == "TrafficLight")` |
| 12 | Roundabout tool | `float(tool == "Roundabout")` |
| 13 | Removal tool | `float(tool == "Remove")` |
| 14 | Start x | `start.x / 50` |
| 15 | Start y | `start.y / 30` |
| 16 | End x | `end.x / 50` |
| 17 | End y | `end.y / 30` |
| 18 | Urgency | `min(1, urgency / 10)` |
| 19 | Length | `min(1, length / 20)` |
| 20 | Available stock | `min(1, stock / 100)` |
| 21 | Upgrade type | `(offer.type + 1) / 6`; missing type defaults to -1 |
| 22 | Upgrade amount | `offer.amount / 30`; absent offer gives 0 |
| 23 | Upgrade roads | `offer.roads / 30`; absent offer gives 0 |
| 24 | Object identifier | `min(1, id / 100)` |
| 25 | Handwritten priority | `candidate.priority / 100`; can be negative or exceed 1 |

Unspecified coordinates, urgency, length, stock and identifier default to zero;
an unspecified tool gives five zeros. Features 18-20 and 24 have upper caps
only, not lower clamps. Not every candidate populates every applicable feature:
for example, lights/roundabouts omit stock, driveway changes omit urgency and
ID-based motorway edits omit length. Their zeros do not necessarily mean zero
physical stock, urgency or length.

Request dictionaries additionally carry the actual `command`, `tool`, `x`, `y`,
`toX`, `toY`, `id` or `choice` needed for execution. Labels and the complete
request are not passed directly to the network. Upgrade choice index is not a
dedicated feature; the offer's content represents it. Object IDs at/above 100
collapse to 1. No house/destination target ID or complete planned route is
encoded for a road stroke.

The standard matrix pads to 48 rows with zero features and `False` mask values;
more than 48 candidates raises `ValueError`. The network can score another
candidate count, but the normal collection/replay pipeline fixes new samples at 48; historical 24-row replay is padded when mixed into a wider batch.

## 5. Current state used outside the network, and omitted information

The proposer also reads building IDs, colors, footprints, entrances, driveway
directions, demand and reservations; vehicle positions/waiting; terrain,
infrastructure, explicit connections, pending removals, playable bounds,
rail cells, roundabout centers, motorway IDs/endpoints/removal flags, inventory,
upgrade offers and game version. These influence availability and priority even
when not represented directly in the state tensors.

Guards separately use simulated time, requests, acceptance, and before/after
building, motorway and infrastructure observations. This history is cloned for
search branches but is not an input to `Network`. Consequently, identical
network state features can have different available actions because of history.

The state encoder has no explicit input for:

- Spawn age, station/shared-lot identity, parking occupancy or service rate.
  Capacity, load ratio and overcrowding timer are now explicit channels 39–41.
- Per-house service coverage or reachability, per-destination compatible supply,
  route distances, or time spent disconnected. Some connectivity can be inferred
  from the grid, but these quantities are not supplied as dedicated features.
- Vehicle speed, heading, acceleration, trip stage, color, home/destination IDs,
  route, return route or obstacle. Local vehicle waiting is aggregated.
- Traffic-signal phase/timer, train position/speed/direction/waiting, or currently
  closed rail crossings. Static railway locations are encoded.
- Explicit map identity, day/week/hour, rule coefficients, failure flag,
  remaining episode time, or the configured horizon. Time is the only direct
  time scalar; failure is handled by the environment/search control flow.
- Guard cooldown timers, rejected-action history or persistent construction intent.
- Future spawn schedules, pending upgrade timing, RNG state/draw counts and
  other future/diagnostic fields. These are deliberately excluded from policy
  encoding and proposal generation, even though the host can expose them.

The value estimate therefore does not receive every observable factor that can
affect a transition or failure risk. There is no recurrent state to recover
history. Search uses simulator state beyond these compressed neural inputs.

## 6. Hardcoded action-space restrictions

### Candidate selection and coverage

| Restriction | Current implementation and consequence |
| --- | --- |
| Version | `candidates()` accepts only `OriginalReference` |
| Allowed commands | `wait`, `draw`, `build`, `connect`, `driveway`, `motorway`, `editMotorway`, `removeMotorway`, `upgrade`; policy cannot reset, step directly, use debug `reference`, or call simulator-control commands |
| Tools | Road, bridge, traffic light, roundabout, removal; no tunnel or independent signal-timing action |
| Main route destinations | Only the first **20** destinations after sorting by descending `demand + reserved`, then ascending ID (`MAX_DESTINATIONS`) |
| Houses per destination | Only the **5** closest compatible-color houses by Manhattan distance to the destination's first entrance, then ID |
| Route variants | Per entrance, one weighted path plus an alternate only when the first path has more than 5 cells; alternate avoids its midpoint. Keep at most **2** routes per house/destination, sorted by cell count |
| Road-stroke length | Main route generation calls `_next_stroke(..., max_length=8)`: at most **8 links** in one straight directional stroke. The helper's unused default is 5 |
| Route start/end | Start through the house's existing driveway; destination through an entry's outward neighbor. Access/outside cells must be playable, unoccupied land |
| Stock gate | No new route proposal if road stock is zero. Estimated new land/water cells must fit road stock, and estimated water cells must fit bridge stock; this is a conservative per-cell bridge estimate rather than exact span accounting |
| Already connected pairs | Skip ordinary route proposals for graph-connected house/destination pairs; only consider the motorway shortcut logic for that pair |
| Local-edit centers | Vehicles contribute urgency `2 + waiting`; the top 20 destinations' primary entrances contribute `1 + demand + reserved`. Sort by urgency and inspect only the first **20** centers |
| Local-edit area | Each center's own cell plus its eight immediate neighbors, with duplicate inspected cells skipped. This is not a scan of all 1,500 cells |
| Driveway coverage | Only the first **12 houses in observation order**, regardless of later houses' urgency |
| Final candidates | Wait is slot 0. Sort others by descending priority, label, then request values. Reserve one per `(command, tool)` family, then fill by priority. No reserved slot for each destination, house, color or service emergency |
| Guarded pipeline | Generate at most **128** raw candidates, canonicalize/deduplicate, apply guards, ask host `validateActions` with limit **48**, retain accepted actions that changed state, then slice to 48 |
| Raw pipeline | `candidates()` defaults to **48** without native preflight or history filtering. Turning safety off still retains all other proposal heuristics |
| Wait | Always generated and must survive preflight as the first legal candidate, otherwise raise an error |

These are proposer limits, not maximum numbers of buildings the simulator can
contain. An excluded destination/house can still be affected by incidental local
construction, but the network cannot choose a useful action absent from its
candidate list. Family reservation also happens before legality filtering;
the pipeline does not replenish candidates by searching the entire action space.

Path and connectivity caches each retain at most **4,096 entries**, evicting the
least recently used entry, and are cleared at each episode reset. Cache context
hashes terrain, infrastructure, connections, pending removals, playable bounds,
whether bridge stock is positive, occupied cells and rail cells. It is not a
full-state hash. `TRAFFIC_DISABLE_PROPOSAL_CACHE=1` disables their use. This is a
computation setting, not a larger action space or learned memory.

### Path-search costs and geometric filters

- Weighted eight-neighbor path search uses heuristic
  `0.2 * ChebyshevDistanceToGoal`. Entering existing infrastructure costs 0.2;
  empty land costs 1; empty water costs 4; a diagonal adds 0.4 and a railway
  cell adds 2. These preferences are handwritten, not learned traffic costs.
- Paths reject cells outside the canvas/playable area, occupied cells except
  the goal, the alternate's avoided cell, roundabout centers, blocked terrain,
  pending removals and crossing diagonals. Empty water is rejected when bridge
  inventory is nonpositive. Paths use surface links, not motorway travel edges.
- Surface `_connected()` and `reachable_pairs()` use the eight-direction
  connection graph, without adding motorway edges. Their connectivity tests do
  not model traffic capacity, queueing, travel time or full vehicle routing.
- `_next_stroke()` skips existing links and returns the first missing straight
  segment, not a complete route. No persistent route plan is retained between
  decisions; the proposer recomputes from the next state.
- Local building skips occupied/pending-removal cells. New bridge tiles require
  positive bridge and road stock; new road tiles require road stock.
- Traffic lights are proposed only on ordinary road cells with degree at least
  3, available stock and no motorway endpoint.
- Roundabouts are proposed only on ordinary road cells with stock and no
  motorway endpoint. All four cardinal ring cells must be playable, unoccupied,
  land, not pending removal, not traffic lights and not motorway endpoints.
- Local removal is proposed only for infrastructure cells of degree at most 1;
  the proposer does not freely demolish busy junctions or arbitrary route segments.
- Local connects require neighboring infrastructure, no existing link, no
  pending removal at the neighbor, no roundabout-center endpoint and no crossed
  diagonal. They are not required to improve service or reduce travel time.

### Driveway and motorway filters

- A driveway candidate must face playable unoccupied land, not pending removal
  or a roundabout center, and differ from the current direction. It is offered
  only if the old access is blocked, it adds service to a matching destination,
  or it relieves a queue. Queue relief requires old-cell waiting **> 5 seconds**,
  new-cell waiting **< half** the old waiting, and traversable new access.
- New motorways are proposed only for already surface-connected compatible
  pairs considered by the top-20/top-5 loops, with positive motorway stock.
  Endpoints must be the house-access and destination-outside cells, playable,
  unoccupied, ordinary roads on land, not pending removal and not existing
  motorway endpoints. Their Chebyshev separation must be **at least 10** and
  those endpoint cells must already be surface-connected. No general proposal
  connects arbitrary regions or first serves a disconnected pair by motorway.
- Motorway removal is offered for each motorway not pending removal.
- Motorway edits keep the start endpoint fixed and move only the end endpoint
  by one of `DIRS[:4]`: `(+1,0)`, `(+1,+1)`, `(0,+1)`, `(-1,+1)`.
  The other four moves and edits of the start endpoint are not enumerated.
  The new endpoint must be playable unoccupied land, not pending removal or
  already a motorway endpoint, an ordinary road with strictly greater surface
  degree than the old endpoint, and at least 2 cells from the fixed start by
  Chebyshev distance. Native preflight applies further legality checks.

### Handwritten candidate priorities

Priorities govern pruning and heuristic demonstrations, and priority `/100`
is itself a neural input. Let `u` be urgency and `L` the relevant length.

| Candidate | Priority |
| --- | --- |
| Wait | 0 |
| Upgrade | `100 + offer.roads + (25 if type == 2 else 0)`; encoded urgency is 10 |
| Route stroke | `10*u - len(full_path) + (15 if len(full_path) <= 9 else 0) + (4 if stroke starts at house else 0)`; `u = demand + reserved` |
| New motorway | `10*u + ChebyshevLength - 15`; `u = demand + reserved` |
| Local road/bridge | `u - 2` |
| Traffic light | `u` |
| Roundabout | `u - 1` |
| Local removal | `u - 8` |
| Local connection | `u + 2` if either existing endpoint road is currently occupied by an active vehicle; otherwise `u` |
| Driveway | 25 when adding service, otherwise 5 |
| Motorway edit | -2 |
| Motorway removal | -5 |

The urgency and length supplied to the neural features can describe a stroke,
while its priority uses a full route. The priority formula does not use
destination capacity, overcrowding progress or age of an unserved building.
Priority ties and candidate order can favor the same buildings repeatedly.

The connection bonus checks current integer-position vehicle occupancy at either
endpoint with nonzero infrastructure. `Home`, `Parking` and absent stages do
not qualify; stopped/queued active traffic does. Nearby traffic on other cells
does not qualify. This does not establish usefulness of the new link or record
historical road use. The proposer now reads vehicle stage for this bonus;
there is still no vehicle-stage neural input channel.

## 7. History guards and preflight restrictions

| Guard | Default | Exact behavior |
| --- | ---: | --- |
| Driveway cooldown | 20 simulated seconds | Blocks another driveway change, including a draw that changes the house's driveway, while current access is not blocked |
| Driveway reversal window | 60 seconds | Blocks returning to the previous direction within this window when access is not blocked |
| Motorway cooldown | 30 seconds | Locks endpoints touched by motorway changes; blocks create/edit/remove requests involving locked endpoints |
| Construction reversal cooldown | 10 seconds | Blocks local `build` removal/rebuild reversals at a recorded tile; road upgrades are allowed. It is not a blanket cooldown on every draw/connect command |
| Rejected request suppression | **30 seconds fixed in code** | Suppresses the same canonical rejected request until its expiry |

The first four values are configurable via training CLI flags. Reversal
counters also use the configured reversal window, including motorway history;
motorway reversal counting does not add a separate 60-second blocking rule.

The guard's blocked-driveway exception checks canvas bounds, non-land terrain
and pending removal. It does not use the proposer's fuller blocked-access test
(which also checks playable bounds, occupied cells and roundabout centers).
Thus an action proposed as recovery can still be cooldown-filtered.

Deduplication treats reversed endpoints as equivalent for `connect` and
`motorway`, but not every other request. Native preflight requires both
`accepted` and `changed`; accepted partial draws remain eligible. Legal
zero-immediate-change actions other than the host's special wait handling can
therefore be excluded. Guard safety is enabled unconditionally by the current
training entry point; lower-level `run_episode(safety=False)` and raw heuristic
controls can bypass it. Existing checkpoint config can also enable it in evaluation.

## 8. Network architecture limitations

- Two spatial convolutions: `42 -> 32`, kernel 5, stride 2, padding 2; then
  `32 -> 32`, kernel 3, stride 2, padding 1; ReLU after each.
- Flatten size is hardcoded to `32 * 8 * 13`, binding the architecture to the
  30 by 50 canvas and those convolutions. A linear layer maps to hidden width
  128 by default. `hidden` is a constructor parameter but has no training CLI flag.
- State encoder concatenates the grid embedding with exactly 19 scalars.
  Policy is `hidden + 26 -> hidden -> 1` per candidate; value is
  `hidden -> hidden -> 1`. Hidden nonlinearities are ReLU.
- There is no learned transition model, recurrent memory, graph neural network,
  attention over vehicles/buildings, or interaction layer between candidates.
  Policy logits are scored independently from the same state embedding and
  each candidate's own feature vector, then normalized together.
- Output value is unbounded and multiplied by `value_scale`. Constructor default
  is **10**; current controlled training default is **100**. Loading uses saved
  `config.valueScale` with legacy fallback 10. Q normalization and value-loss
  normalization depend on this scale.
- Input widths, direction/tool/category orders and normalization constants are
  not inferred from a checkpoint schema. Shape/order changes require compatible
  weights and regenerated/migrated replay; there is no automatic feature-schema migration. Candidate-row count is variable: increasing 24 to 48 does not change network parameter shapes, and training zero-pads options/masks/policy targets when mixing those historical row counts.

## 9. Search and action-selection limitations

| Setting or rule | Current behavior |
| --- | --- |
| Search budget | Training default 16 simulations per decision; configurable |
| Depth cap | Default 4 decisions; configurable, with no guarantee of reaching the cap |
| Exploration coefficient | PUCT coefficient **1.5**, function argument but no training/evaluation CLI flag |
| Stochastic outcomes | At most **2** sampled outcomes per action by default, function argument but no CLI flag |
| PUCT | `Q/value_scale + 1.5*prior*sqrt(node_visits + 1)/(edge_visits + 1)`; unvisited Q is 0; ties favor lower candidate index |
| Expansion | A simulation stops after adding one new outcome and bootstraps its child value; the full depth is not expanded immediately |
| Outcome reuse | After the outcome cap, revisit the least-visited outcome, reusing its seed and asserting exact observation equality |
| Future seed | `rng.randrange(1, 2**31)` for each new outcome; re-fork the host future on each branch transition |
| Training root noise | Fixed mixture **0.15**, with normalized Gamma draws of shape **0.3**, scale 1; evaluation uses none |
| Root coverage | Reserve one rollout for each of up to 4 distinct initial actions: wait, highest-prior alternative, then favor other command/tool families. Limit by legal unique requests and budget; normal PUCT follows |
| Training action selection | Sample proportional to root support visits after subtracting mandatory opening visits, or policy probabilities without search; no temperature schedule. If all weights are zero, choose uniformly among valid candidates |
| Evaluation selection | Maximum corrected search-policy weight or policy probability; ties favor the lower index |
| Tree reuse | Rebuild the root/tree each real decision; no persistent search tree |
| Execution | One search worker by default; `--search-workers` enables independent simulator workers sharing the total rollout budget. `--torch-threads` defaults to 1 |

The supplied simulator is the transition model. Snapshot mode restores snapshot
ID **1** before each simulation and keeps it synchronized after real decisions.
Replay mode resets and replays the entire real action history before each
simulation. Both modes require exact equality checks; divergence raises errors.
Snapshot mode does not eliminate the cost of simulator transitions.

With multiple workers, search reserves waves using temporary node-value visits
and pending outcome counts, then backs up completed work in reservation order.
Opening comparisons are reserved without duplicates and completed before normal
PUCT begins. A smaller opening wave is used when fewer alternatives remain than
workers. One-rollout searches use wait when available. Family diversity is
preferred, but fallback alternatives can share a family or affect nearby cells;
there is no guarantee of diverse service goals or comparison of every candidate.
Visited root requests, original policy/search priors, raw visits, Q/mean return,
and comparison target/completion counts are logged, alongside mean root coverage
per episode. Mandatory visits are subtracted once per reserved action from the
selection/learning weights, not from actual visit/Q accounting. `rootPolicy`
normalizes the remaining support visits. A probe-only action has zero policy
weight when ordinary search support exists; a revisited alternative can earn
positive weight. If only probes fit in a tiny budget, use original priors among
visited actions, with uniform visited fallback only for zero prior mass.
Training still samples, and MCTS evaluation takes the maximum of the corrected
policy. Setting the comparison count to zero in a control recovers ordinary
visit-proportional selection and targets. Record `rootPolicyMode` in run config
and `rootPolicySource`/`searchSupportVisits`/`policyWeight` in diagnostics.
Worker count can therefore change the selection schedule. See
[HANDWRITTEN_RULES.md](HANDWRITTEN_RULES.md) for the coordination rules.

Natural terminal nodes have value 0. Externally truncated nodes stop expansion
but bootstrap a network value. Truncated/bootstrap prediction uses raw
`candidates()` rather than guarded proposals. Search discounts by decision,
not physical seconds, including shorter final intervals. Future sampling is an
approximation, not evidence of a calibrated distribution of original-game futures;
see [README.md](../README.md) and [ONBOARDING.md](../ONBOARDING.md).

## 10. Time, reward and termination limitations

`TrafficEnv` executes one allowed command, then advances time even if the
command was rejected. `wait` skips the construction call but advances time.

- Decision duration defaults to **20 ticks**, with a fixed assumed tick duration
  of **0.05 seconds**, normally one simulated second per decision. Tick count is
  a constructor parameter, not exposed by the training/evaluation CLI.
- Remaining ticks are `max(0, round((cap_seconds - before.time) / 0.05))`;
  the final step takes the smaller of this and 20. Horizons therefore have tick
  resolution. Arbitrary positive horizons not aligned to 0.05 seconds can leave
  a sub-tick remainder that rounds to zero; training/evaluation do not enforce
  tick alignment, so callers should use aligned horizons.
- Bare environment horizon defaults to **300 seconds**; training and evaluation
  default to **1800 seconds**. The latter is configurable and is an external
  cutoff, not a learned lifetime limit. Evaluation's default overrides a saved
  horizon; its expression falls back to config only for a falsy supplied value.
- A natural host termination ends the episode; host truncation or the time cap
  also ends it. The cap comparison uses tolerance `1e-8`.

Per-decision reward is fixed to this family of formulas:

```text
trip_reward * delta_completed_trips
  + clear_trip_bonus * clear_trip_units
  - congestion_fraction_penalty * congestion_fraction_seconds
  - alpha * delta_waiting_seconds
  - lambda_cost * modification_cost
  - beta_congestion * delta_congestion_seconds
  - failure_penalty * failure
  - unanswered_penalty * unanswered_request_seconds
  - overcrowding_penalty * capacity_pressure_seconds
```

Current defaults: `trip_reward=10`, `alpha=0.05`, `lambda_cost=0.01`, `beta_congestion=0`.
Additionally, `clear_trip_bonus=0.1` and `congestion_fraction_penalty=0.02`.
At the end of each decision, compute the fraction of active cars waiting at
least two seconds, excluding Home/Parking/missing-stage entries. No active cars
means zero. Clear-trip units are completed trips times `(1 - fraction)`;
fraction-seconds are fraction times actual elapsed seconds. Quiet roads with
no deliveries earn no positive bonus. Threshold is configurable with
`--congestion-wait-threshold` (default 2); no new neural input is introduced.
The original raw `congestionSeconds`/beta coefficient remains separate.
Log `blockedFraction`, `clearTripUnits`, `congestionFractionSeconds`, and the
episode's time-weighted `meanBlockedFraction`. Legacy checkpoint evaluation
defaults the new coefficients to zero, preserving recorded reward settings.
`--trip-reward` must be finite and positive. Raw trip counters remain unscaled.
The modification weight increased from 0.005; actual modification accounting
and proposal legality rules remain the same.
New defaults: `failure_penalty=10`, `unanswered_penalty=0.01`, exposed as
`--failure-penalty` and `--unanswered-penalty`. Both must be finite/nonnegative;
zero disables a term. Failure counts once when the observation first becomes
failed, excluding healthy cutoffs and protocol errors. Request-seconds are
the final observed sum of nonnegative destination demand times actual elapsed
simulated seconds: a boundary approximation rather than a within-tick integral.
Demand includes requests assigned to vehicles until delivery, so reservations
are not added again. All destinations count, independently of proposal coverage.
Log `failure` and `unansweredRequestSeconds` separately and save both coefficients
in checkpoints/traces. Branches inherit the same reward weights.

`--overcrowding-penalty` defaults to 0.05. Add
`capacity_pressure_seconds = elapsed * sum(max(0, demand - demandCapacity + 1))`
across non-house destinations, using final observed demand and each destination's
actual capacity. This adds -0.05/second at 6/6, -0.10 at 7/6 and -0.15 at 8/6,
then stops below capacity. It supplements backlog cost, includes reservations
until delivery without double-counting, and scales shortened intervals. Log raw
`capacityPressureSeconds` and save `overcrowdingPenalty`; branch rewards match.
Active shaping requires positive finite capacities. Zero disables it, allowing
legacy hosts to omit capacities; raw pressure is logged where valid data exists.
No capacity channels or overcrowding-timer features were added to the network.

Modification cost is the sum of changed infrastructure cells, changed connection
bits divided by 2, the symmetric difference of motorway `(id, pendingRemoval)`
sets, and house driveway-direction changes. Changing the endpoints of an active
motorway with the same ID does not itself change that motorway-set component.
The cost compares pre-command and immediate post-command observations; traffic
waiting and congestion cover the full command-plus-step interval. Inventory
refunds and `spendingDelta` do not give reward credits.

There is no explicit reward term for survival time, connectivity itself,
overcrowding-timer progress or useful route completion.
Failure also removes future rewards/bootstrap. Waiting penalizes accumulated
vehicle waiting, while the new backlog term penalizes undelivered destination
requests. Congestion is logged but
has zero direct weight by default. Global trip gains can outweigh a local crisis.

Episode returns use a fixed discount per decision; current training default is
**0.999**. Lower-level `search()` and `finish_episode()` defaults remain
**0.997**; `run_episode()` passes its own default 0.999, and evaluation falls
back to saved-config discount 0.997 if absent. Natural failure uses zero
bootstrap; a nonfailed cutoff bootstraps network value, not zero.

## 11. Training and replay restrictions

| Item | Current implementation |
| --- | --- |
| Optimizer | Adam, learning rate **3e-4**, weight decay **1e-5**; hardcoded in `experiment.py` |
| Gradient clipping | Global parameter norm **5.0**; nonfinite loss/gradient raises an error |
| Policy loss | Mean cross entropy against corrected MCTS search-policy weights or one-hot heuristic choices; no entropy bonus or smoothing |
| Value loss | Huber (`smooth_l1_loss`, default transition 1) or MSE on value/target divided by `value_scale`; default Huber |
| Loss weights | Policy 1 and value 1 by default; nonnegative and at least one positive |
| Batch size | 32 by default; configurable; sampling with replacement |
| Demonstrations | Default 3 heuristic episodes; 128 optimizer updates after each; permanent replay |
| Self-play updates | Default 64 optimizer updates after each episode |
| Replay mixture | Fixed weights **35% demonstration / 40% recent / 25% successful**; absent pools redistribute weights |
| Successful pool | Per map, top `max(1, recent_episode_count // 2)` by completed trips, then keep only episodes with trips > 0; references recent episodes rather than a permanent archive |
| Sampling within pools | Choose an episode uniformly, then a state uniformly; this does not sample all stored states uniformly |
| Recent capacity | Default 6,000 states; evict whole oldest episodes, but keep at least one episode, so a single long episode can exceed the nominal cap |
| Permanent capacity | Demonstration replay has no corresponding state cap |
| Initialization RNG | Python, NumPy and PyTorch seeds fixed to **1000**, no seed CLI flag |
| Evaluation search RNG | Per case, `Random(seed + 900000)`; raw heuristic validation uses `Random(seed)` |
| Precision | Replay inputs compressed to float16; model training uses float32 |

The model learns to rank the bounded proposal set and fit returns under the
specified shaping; it cannot repair missing action coverage through weights
alone. Demonstrations inherit the handwritten priorities and restrictions.
Changing proposal code changes the effective policy even with identical weights.

`--init-checkpoint` restores model weights only into a fresh optimizer/replay,
with value-head rescaling for the old/new value scale. The supported
`--resume-demonstration` restores only an **episode-zero** checkpoint, matching
value scale, optimizer, Python/NumPy/PyTorch CPU RNG state and a separately
provided demonstration archive; it requires `--bootstrap-episodes 0` and cannot
be combined with `--init-checkpoint`.
Modification, failure, unanswered and overcrowding weights must match the saved demonstration checkpoint
(missing historical coefficients mean zero for this compatibility check).
Changing rewards requires fresh demonstration targets, using a weight warm start.

`--resume <checkpoint-last.pt> --bootstrap-episodes 0` restores new-format
model, optimizer, full replay, RNG, validation metadata and episode position.
Schema, reward, search, training and host settings must match. Legacy states
without replay require a weights-only warm start; they cannot be exact resumes.
CUDA RNG state is not saved by the current checkpoint helper.
Training requires a new output directory rather than appending to an existing run.

## 12. Fixed experiment protocol and configurable defaults

| Setting | Current value or constraint |
| --- | --- |
| Supported environment maps | LosAngeles, Beijing, Tokyo, DarEsSalaam, London; no arbitrary map or lab through `TrafficEnv.reset()` |
| Rules/variation | Always `OriginalReference`, finite inventory, `SameMap`; reject unlimited construction or another version |
| Training maps | LosAngeles only by default (`--city`) |
| Validation map | Same city as training |
| Held-out test map | Same city as training |
| Training seeds | Random distinct positive signed 32-bit integers; exclude both held-out seeds |
| Demonstration seeds | Optional demonstrations use the same disjoint random sampler; zero demonstration episodes by default |
| Validation/test seeds | Fixed 200000 / 300000 by default; exactly one distinct seed for each split |
| Count cap | Controlled training requires `episode_offset + episodes <= 50000` and demonstrations <= 50000; historical seed blocks apply only to legacy helpers |
| Training budget | 6 episodes by default; configurable |
| Validation frequency | After every three completed training examples; no initial/baseline or incomplete-final-group validation; cadence survives resume |
| Validation search budgets | `[0]` by default: policy-only; independent of the training budget 16 |
| Validation/test case counts | Exactly one fixed seed each in the single-city protocol |
| Early stopping | Disabled by default (`--patience 0`); optional nonzero patience waits for at least 3 collected training episodes |
| Checkpoint selection | Latest weights, with no best-model save/rollback. Validation ranks report mean trips, then lower waiting, then lower modification cost |
| Test access | Training runs test only with `--final-test`; evaluator requires `--split test` and disallows multiple test budgets or `--save-best` |
| Device | Training defaults to CPU with `--device` override; current evaluator constructs a CPU network |
| Evaluation branch | Evaluator always uses snapshots; training offers snapshot (default) or replay |

The CLI enforces positive main counts/scales/horizon, nonnegative search budgets,
penalties/cooldowns/loss weights and replay capacity at least 1; discount must be
`0 < discount <= 1`. These checks do not comprehensively validate finite numeric
values or tick alignment. Two validation seeds are a development default, not
evidence of broad generalization. Mean-based selection can hide weak individual
cities/seeds, and repeated tuning can overfit the fixed validation city.

For completeness, the model-affecting controlled-training parameters and defaults
are listed below. These are runtime settings, distinct from the tensors above.

| CLI parameter(s) | Default |
| --- | --- |
| `--episodes`, `--episode-offset` | 6, 0 |
| `--validation-seeds`, `--test-seeds`, `--validate-every` | 1, 1, 3 |
| `--city`, `--validation-seed`, `--test-seed` | LosAngeles, 200000, 300000 |
| `--seed-sequence-seed` | Fresh random sampler seed, recorded in config; optional explicit seed for reproducibility |
| `--evaluation-budgets` | 0 |
| `--simulations`, `--search-depth`, `--branch` | 16, 4, snapshot |
| `--search-workers`, `--torch-threads` | 1, 1 |
| `--bootstrap-episodes`, `--bootstrap-updates` | 0, 128 |
| `--updates-per-episode`, `--batch-size`, `--replay-states` | 64, 32, 6000 |
| `--value-loss`, `--value-scale` | huber, 100 |
| `--value-weight`, `--policy-weight`, `--discount` | 1, 1, 0.999 |
| `--cap-seconds` | 1800 |
| `--alpha`, `--lambda-cost`, `--beta-congestion` | 0.05, 0.01, 0 |
| `--failure-penalty`, `--unanswered-penalty` | 10, 0.01 |
| `--overcrowding-penalty` | 0.05 |
| `--driveway-cooldown`, `--motorway-cooldown` | 20, 30 |
| `--construction-cooldown`, `--reversal-window` | 10, 60 |
| `--patience`, `--min-episodes`, `--final-test` | 0, 3, false |
| `--device`, `--dotnet`, `--host-dll` | cpu, dotnet, `HOST_DLL` |
| `--init-checkpoint`, `--resume`, `--resume-demonstration`, `--demonstrations` | Unset |
| `--output` | New timestamped `output/mbrl/controlled-...` directory |

Evaluation additionally accepts checkpoint/source selection, `--budgets`,
`--split`, `--guarded` and heuristic comparison modes. Its `--simulations`
default is 16 and depth default 4. New single-city checkpoints evaluate exactly
one saved validation/test seed. For historical city-split checkpoints,
`--validation-seeds` also controls the number of test cases. A frozen `--source-dir` can load a
different implementation, so its inputs/limits must be audited separately.
Current evaluation accepts overrides for modification/failure/backlog/overcrowding weights and otherwise
uses checkpoint values, falling back to 10/0.01 when absent. Visualization and
search benchmarks also use those saved values/defaults. Frozen source controls
retain their historical implementation and do not accept these overrides.
For overcrowding specifically, a saved checkpoint without the field defaults
to zero in evaluation, visualization and benchmarks; saved modification weights
are also preserved. New training uses the current defaults. Changing reward
settings does not retrain existing weights or re-label stored replay automatically.
Output/reuse/runtime-note and live-view flags affect execution/recording rather
than adding neural features. Viewer pacing adds wall time without adding game
time or policy inputs.

## 13. Simulator and host boundary

- `Host` requires a .NET host DLL, uses a line-delimited JSON subprocess protocol
  and a default **30-second response timeout**. Timeout is a constructor argument,
  not a training CLI option. There is no automatic timeout retry or host recovery;
  shutdown waits 3 seconds before killing an unresponsive process.
- Default DLL is `simulation/Headless/bin/Debug/net8.0/TrafficHost.dll`.
  `TRAFFIC_HOST_DLL` is read when `environment.py` is imported; explicit
  `--host-dll` overrides it in training/evaluation/visualization.
- Reset requires observation fields `tripsDispatched`, `waitingSeconds`,
  `congestionSeconds`. Guarded proposals also require `validateActions`; search
  requires `forkFuture`, and snapshots require `saveSnapshot`/`loadSnapshot`.
  A reset-field check alone is not a complete capability negotiation.
- The checked-in [headless dispatcher](../../simulation/Headless/Program.cs) lacks
  these newer search/preflight commands, and the checked-in observation schema
  lacks the required counters. Rebuilding it does not by itself supply the MBRL
  protocol. Recovery runs use the preserved
  `output/mbrl/recovery-20261101/host/TrafficHost.dll`; use the host matching the
  checkpoint/source and recorded hashes.
- The Python adapter assumes fixed direction/category codes, six materials and
  0.05-second ticks. The simulator's [rules](../../simulation/Assets/Simulation/TrafficTypes.cs)
  and [world](../../simulation/Assets/Simulation/TrafficWorld.cs) separately fix
  the canvas, two cars per house, traffic mechanics, construction legality,
  inventory behavior and overcrowding failure. These are not policy-controlled
  inputs; changing them requires a compatible environment and evaluation.
- Tunnel stock exists in the six-slot schema but tunnels are not implemented in
  the current infrastructure/tool types or model action generator.
- `OriginalReference` is an unverified reconstruction. Its own observation
  reports `ExactReplicaValidated=false` and names remaining motorway, inventory
  weighting, destination upgrade, train, spawn and traffic-parity approximations.
  Search and evaluation results therefore apply to the selected simulator build,
  not a certified exact replica of the commercial game.

Suggested improvements in [RECOMMENDED_CHANGES.md](../RECOMMENDED_CHANGES.md),
such as timer-based service-risk shaping and reserved service-coverage candidate
slots remain proposals. Capacity, load and timer input features are implemented.
The requested destination cutoff of 20, explicit failure/backlog penalties,
stronger modification cost and capacity-pressure penalty are now implemented;
the three additional input features are indexed above.
Initial comparison of up to four root actions is also implemented, with
parallel reservation and coverage/visit/return diagnostics.


## Current learning update — 7 November 2026

- New training rewards each completed trip with **10**, configurable with
  `--trip-reward`; other reward coefficients are unchanged. Raw trip counters and
  displayed scores remain unscaled. Traces/config record `tripReward`.
  Historical checkpoints without this field evaluate with trip reward 1 unless
  explicitly overridden; frozen-source runs retain their original behavior.
- Schema **traffic-risk-v3** has **42 grid channels**, 19 scalars and 26 candidate
  features. Channels 39–41 are destination capacity / 10, demand / capacity, and
  overcrowdedFor / 50, rasterized across destination footprints, zero on houses
  and masked outside playable bounds. Ratios are not clipped at 1. Positive
  capacity and a finite nonnegative timer are required. Only current observations
  are used. The divisor 50 matches OriginalReference; another ruleset needs an
  explicit schema review.
- Serial and parallel PUCT use the current node value for unvisited actions;
  parallel pending work also uses that baseline. Raw measured Q/visit logging and
  the opening-visit policy correction remain in place.
- Warm-start migration copies all 39 historical first-convolution input weights
  and zero-initializes the three added channel weights. Existing predictions are
  preserved initially, and the added weights remain trainable. All other layer
  shapes are unchanged. Reward changes require fresh matching replay; legacy
  tensors are not silently reinterpreted as risk-aware observations.
- Training saves `checkpoint-last.pt` and per-episode full states, selects the
  latest weights, and creates no best-model checkpoint. Validation rank history
  remains diagnostic. Patience defaults to 0. Existing historical files are kept.
- `--resume <checkpoint-last.pt> --bootstrap-episodes 0` restores complete replay,
  optimizer, Python/NumPy/PyTorch RNG and episode position with compatible schema,
  reward, search, training and simulator settings. Successful replay is derived
  from restored recent episodes; city ordering is sorted for reproducible draws.
  `--init-checkpoint` remains an explicit weights-only warm start.

Checks: return-offset invariance and useful construction in serial/parallel search,
feature sensitivity/masking, legacy prediction preservation, trainable new input
weights, reward multiplier, replay/optimizer restoration and native split-versus-
uninterrupted training equality. These checks do not establish a 300-trip score.
