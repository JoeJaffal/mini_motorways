# Handwritten rules in the MBRL model

Verified against the working-tree code on 2026-11-07. This is an inventory of
the human-written rules that determine what the agent observes, what it can
choose, how it searches, what earns reward or punishment, and how it learns
and is selected. Values below are current defaults unless described as fixed.
Saved checkpoints, preserved source snapshots and selected simulator builds
can use different settings.

## 1. Where the rules act

| Mechanism | What it does | Directly changes gameplay reward? |
| --- | --- | --- |
| Reward and punishment | Assign a scalar to the executed action plus its following time interval | Yes |
| Candidate priorities | Rank and prune proposals, select heuristic demonstrations, and provide a policy feature | No |
| Path costs | Prefer some proposed routes over others | No |
| Proposal filters and guards | Prevent actions from reaching the policy/search | No |
| Search rules | Combine policy priors, simulator outcomes and value estimates | Use reward, but add no separate reward term |
| Learning rules | Define targets, losses, sampling and optimizer updates | No |
| Checkpoint ranking | Report validation ranks; continue from the latest checkpoint | No |
| Simulator rules | Determine legality, traffic, inventory, demand and natural failure | Affect transitions and the counters used by reward |

For example, motorway removal priority `-5` is a proposal preference; it does
not mean the model receives a reward penalty of five. A cooldown blocks an
action rather than adding a numerical punishment. Gradient clipping and weight
decay are learning rules rather than gameplay punishments.

Source functions are identified throughout. The companion
[MODEL_INPUTS_AND_LIMITATIONS.md](MODEL_INPUTS_AND_LIMITATIONS.md) contains the
complete indexed input schema and additional compatibility details.

## 2. Every implemented reward and punishment term

Source: `TrafficEnv.step()` in [environment.py](../environment.py).

```text
reward = trip_reward * delta_completed_trips
       + clear_trip_bonus * clear_trip_units
       - congestion_fraction_penalty * congestion_fraction_seconds
       - alpha * delta_waiting_seconds
       - lambda_cost * modification_cost
       - beta_congestion * delta_congestion_seconds
       - failure_penalty * failure
       - unanswered_penalty * unanswered_request_seconds
       - overcrowding_penalty * capacity_pressure_seconds
```

| Term | Default rule | Configuration |
| --- | --- | --- |
| Completed trip | Reward **+10** per newly completed trip | `--trip-reward`, default 10; finite and positive |
| Clear delivery bonus | **+0.1** times completed trips times `(1 - blocked_fraction)` | `--clear-trip-bonus`, default 0.1 |
| Normalized congestion | **-0.02** times blocked fraction times elapsed seconds | `--congestion-fraction-penalty`, default 0.02 |
| Waiting | Punishment **-0.05** per additional accumulated vehicle-waiting second | `--alpha`, default 0.05 |
| Infrastructure modification | Punishment **-0.01** per unit of actual modification cost (increased from 0.005) | `--lambda-cost`, default 0.01 |
| Congestion | `-beta_congestion * delta_congestion_seconds`; default contribution **0** | `--beta-congestion`, default 0 |
| Natural game loss | Punishment **-10** once when `failed` first becomes true | `--failure-penalty`, default 10 |
| Undelivered requests | Punishment **-0.01 per request-second** | `--unanswered-penalty`, default 0.01 |
| Destination at/above capacity | Punishment **-0.05 per capacity-pressure second** | `--overcrowding-penalty`, default 0.05 |

Trip, waiting and congestion terms use deltas over one decision.

`blocked_fraction` is measured at the post-step observation: active cars whose
current `waiting >= 2` seconds divided by all active cars. Exclude `Home`,
`Parking` and missing-stage entries; no active cars gives fraction zero.
`--congestion-wait-threshold` sets the finite positive threshold (default 2).
`clear_trip_units = delta_completed_trips * (1 - blocked_fraction)`;
`congestion_fraction_seconds = blocked_fraction * actual_elapsed_seconds`.
There is no positive idle/no-traffic bonus without a completed delivery.
The bonus is at most 1% of the default trip reward; the new penalty is bounded
by 0.02 per second independently of car count. This is a decision-boundary
approximation, not an integral over every simulator tick. It supplements the
existing waiting penalty and raw congestion coefficient, which defaults to zero.
Config, traces and both branch types retain all three settings. Historical
checkpoints without these bonus/penalty fields evaluate with both weights zero.
Changing the reward requires matching fresh replay or a weights-only warm start.
Waiting is aggregate vehicle waiting: multiple vehicles can accumulate multiple
waiting seconds during one simulated second. The implementation uses the host's
`waitingSeconds` counter; a legacy fallback subtracts `meanWaiting` if that
counter is absent, although normal reset requires the cumulative counter.
Congestion uses the host's cumulative `congestionSeconds`, with fallback zero.

`unanswered_request_seconds` is the sum of nonnegative destination `demand`
at the end of the decision, multiplied by actual elapsed simulated seconds.
It is a decision-boundary approximation of backlog duration, not an exact
within-tick integral. Demand includes reserved requests until delivery; do not
add reservations again. All destinations contribute, including those outside
the 20-destination proposal cutoff. Repeated backlog incurs repeated cost;
short final intervals incur proportionally less. This backlog term is unchanged;
the capacity-pressure term below is additional. No grace period or additional
reward term is added. Capacity, load and timer input channels are documented below.

### Capacity-pressure rule

For each non-house destination, use its own current `demandCapacity`:

```text
pressure = max(0, demand - demandCapacity + 1)
capacity_pressure_seconds = sum(destination pressures) * actual_elapsed_seconds
```

| Demand/capacity | Pressure | Extra reward cost per second at default weight |
| --- | ---: | ---: |
| 5/6 | 0 | 0 |
| 6/6 | 1 | -0.05 |
| 7/6 | 2 | -0.10 |
| 8/6 | 3 | -0.15 |
| 9/9 | 1 | -0.05 |

Charge again every decision while at/above capacity, and stop as soon as the
observed demand falls below capacity. Include reserved requests until delivery
without adding reservations twice. Sum all destinations, independently of
candidate cutoffs. Like backlog, this uses final decision-boundary state times
actual duration, not an exact within-tick integral. No extra timer-based
penalty is included; this is distinct from vehicle congestion.

Active shaping requires positive finite `demandCapacity` for every destination;
missing/invalid capacity raises a protocol error rather than assuming capacity 6.
Setting the coefficient to zero disables it and permits older hosts without
capacity data. Raw pressure is still logged for valid capacities when disabled;
destinations without valid capacity are skipped only in that disabled mode.

Failure is the transition from not failed to failed. A healthy time cutoff,
scenario truncation or protocol exception receives no game-loss penalty. The
failure, unanswered and overcrowding coefficients must be finite/nonnegative;
zero disables the respective term.
They are saved in checkpoint config and trace reward weights, and the raw
components `failure`, `unansweredRequestSeconds` and `capacityPressureSeconds`
are logged separately. Search branches copy all coefficients. Current
evaluation/visualization preserve saved modification and overcrowding weights;
an older checkpoint without `overcrowdingPenalty` defaults to zero for that term.
Evaluation accepts `--lambda-cost` and `--overcrowding-penalty` overrides.
The earlier failure/backlog fallback defaults remain 10/0.01 when absent.
Frozen `--source-dir` controls retain their preserved implementation.

Example with default coefficients and post-step blocked fraction zero: two
completed trips, ten additional waiting seconds, modification cost four, no game
loss and zero outstanding requests give `10*2 + 0.1*2 - 0.05*10 - 0.01*4 = 19.66`.
Four outstanding requests over one second, below capacity, reduce this to 19.62;
a game loss additionally subtracts 10.

### Exact modification-cost rules

Source: `modification_cost()` in [environment.py](../environment.py).
Compare the observation before the command with the observation immediately
after that command, before the following traffic step:

```text
modification_cost = changed_tile_count
                  + changed_connection_bit_count / 2
                  + motorway_set_symmetric_difference_size
                  + changed_house_driveway_count
```

| Component | What is counted |
| --- | --- |
| Tiles | One per cell whose infrastructure code changes, including building, removal and conversion |
| Connections | Bit counts of `before XOR after` summed across cells and divided by 2, because a normal undirected link is represented at both endpoints |
| Motorways | Symmetric difference of sets of `(motorway.id, motorway.pendingRemoval)` |
| Driveways | One per house whose driveway direction changes, comparing paired before/after building records |

A single command can incur multiple components. An accepted partial road draw
is charged for its actual observed changes, not the whole requested stroke.
The motorway component counts a newly appearing/disappearing ID as one set
entry; changing the same ID from active to pending removal changes two set
entries. Moving endpoints while retaining the same active ID does not itself
change that component, though other observed changes can still count.

Material refunds do not produce negative modification cost. `spendingDelta`
and `materialsUsed` are recorded separately and do not enter reward. Deferred
changes during the following traffic step are not included in this immediate
command modification comparison.

### Events with no separate reward or punishment

The current formula contains no explicit term for:

- Survival time, reaching the external time cap, or
  remaining alive for another decision.
- A disconnected house/destination, time spent disconnected, unused houses,
  overcrowding-timer progress or imminent failure beyond the current capacity
  pressure. Outstanding
  requests at disconnected destinations still incur the backlog penalty above.
- Completing a route, increasing reachable pairs, reducing route length,
  serving a new color, accepting an upgrade, or choosing a particular tool.
- A rejected action, a no-effect action, a reversal, unused stock, demolition
  refunds, or the provisional material-use tie-breaker metric.

These events can still change trips, waiting, modification cost, future returns
or action availability. A rejected command still uses its time interval, and
the guard suppresses its immediate retry. Failure removes future earning
opportunities and sets the terminal bootstrap to zero, in addition to the
explicit failure penalty. Sufficient trip gains can still make a terminal reward positive.
Temporarily incomplete roads receive modification penalties without a separate
blanket disconnected-road penalty.

## 3. Decision timing, allowed actions and stopping

Source: `TrafficEnv` in [environment.py](../environment.py), `run_episode()` in
[train.py](../train.py).

1. Reset only a supported city, with `version="OriginalReference"` and
   `variation="SameMap"`. Require finite construction inventory.
2. Offer only `wait`, `draw`, `build`, `connect`, `driveway`, `motorway`,
   `editMotorway`, `removeMotorway`, and `upgrade` to the policy. Reset, debug
   construction, direct stepping, snapshots and future forking are infrastructure
   commands rather than policy actions.
3. Execute one chosen command. For `wait`, skip the construction call.
4. Advance up to **20 ticks**, assuming **0.05 seconds per tick**, normally one
   simulated second. A rejected command also advances time. A multi-cell draw
   takes one decision interval, not one interval per cell.
5. Limit the final step to
   `max(0, round((cap_seconds - before.time) / 0.05))` remaining ticks.
6. Stop on host termination, host truncation, or the configured time cap
   (comparison tolerance `1e-8`). Controlled training/evaluation default to
   **1800 seconds**; the bare environment constructor defaults to **300**.

Supported cities are LosAngeles, Beijing, Tokyo, DarEsSalaam and London.
Timing is tick-quantized; a positive horizon alone does not guarantee alignment
with 0.05-second ticks. The pipeline has no persistent construction commitment:
it can reconsider after each stroke.

## 4. Which service connections are considered

Source: `candidates()`, `_connected()` and `reachable_pairs()` in
[actions.py](../actions.py).

- Treat buildings marked `isHouse` as sources; all others are destinations.
  Match houses and destinations only when their color codes are equal.
- Occupancy includes every cell of each building's width-by-height footprint.
- Sort destinations by descending `demand + reserved`, then increasing ID.
  Only the first **20** enter the main route/motorway loop (`MAX_DESTINATIONS`).
- Pair entrance lists with entrance directions; fall back to the primary
  entrance and driveway direction when the corresponding list is empty.
  Pairing uses `zip`, so unmatched extra entries are ignored.
- For each considered destination, rank matching houses by Manhattan distance
  to its first paired entrance, then by ID. Consider only the first **5**.
- A house serves the destination for this test if its cell is surface-connected
  to any paired entrance. The test follows connection bits, not traffic utility.
- For an already connected pair, skip new ordinary road routes and consider
  only the motorway-shortcut rules below. For a disconnected pair, require
  positive road stock before proposing a route.
- House access is the neighbor in its current driveway direction. Destination
  outside access is the neighbor facing outward from the entrance. Require
  playable, unoccupied land at these access cells.
- Connectivity helpers use the eight-direction surface graph. They do not add
  motorway edges or evaluate queueing, road capacity or actual travel time.
  `reachable_pairs()` counts compatible house/destination pairs with at least
  one connected entrance; the count is diagnostic, not a reward term.

No rule reserves a candidate for every destination, every disconnected house,
every color, an old unserved building or the destination closest to failure.

## 5. Route construction and handwritten path costs

Source: `_path()`, `_crossed_diagonal()`, `_next_stroke()` and `_line_cells()`
in [actions.py](../actions.py).

Direction order is fixed to `(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1),
(0,-1), (1,-1)`. The canvas is fixed at 50 columns by 30 rows.

| Path preference | Cost |
| --- | ---: |
| Enter existing infrastructure | 0.2 |
| Enter empty land | 1.0 |
| Enter empty water | 4.0 |
| Diagonal step surcharge | +0.4 |
| Enter a railway cell | +2.0 |
| Search heuristic | `0.2 * ChebyshevDistanceToGoal` |

These costs select proposed routes; none is directly subtracted from reward.
Cost comparisons use tolerance `1e-9`, and priority-queue ties use the stored
cost/cell ordering.

Paths reject cells outside the canvas or playable bounds, occupied cells except
the goal, the alternate route's excluded cell, roundabout centers, blocked
terrain, pending removals, and diagonals crossing an existing diagonal.
An already existing diagonal link is allowed by the crossing test. Empty water
is rejected when bridge stock is nonpositive. The path search does not use
motorway edges as shortcuts.

For each entrance, find one path from house access to destination outside
access, then append the entrance cell. If that path has **more than 5 cells**,
try one alternate avoiding its midpoint. Keep at most **2** routes per
house/destination, ranked by cell count, and prepend the house cell.

Walk along existing links until the first missing link, then propose one
straight stroke in that direction, at most **8 links** long. The helper's bare
default is 5, but the main proposer explicitly supplies 8. Stroke cells are
enumerated by Chebyshev length with rounded linear interpolation. Reject
crossing house-access diagonals and duplicate endpoint requests.

Estimate new land cells as roads and new water cells as bridges, excluding
occupied cells and existing infrastructure. Require
`new_roads + new_water_cells <= road_stock` and
`new_water_cells <= bridge_stock`. This is a conservative per-water-cell
estimate rather than the simulator's exact bridge-span accounting. Recompute
proposals next decision instead of retaining the rest of the planned route.

## 6. Local construction, connections and demolition

Source: the local-edit loop in `candidates()` in [actions.py](../actions.py).

Build a list of hot locations:

- Each in-canvas vehicle contributes its integer-position cell with urgency
  `2 + vehicle.waiting`; this loop does not filter out home/parking vehicles.
- Each of the top 20 destinations contributes its primary entrance with urgency
  `1 + demand + reserved`.
- Sort by decreasing urgency and inspect only the first **20** entries. Duplicate
  centers can consume that budget. For each, inspect its cell and eight neighbors;
  skip already-inspected cells and cells outside playable bounds.
- Skip occupied cells and pending removals. When multiple centers reach the
  same cell, the first inspection supplies its local urgency.

| Proposed edit | Required handwritten conditions |
| --- | --- |
| Road | Empty infrastructure on land, positive road stock |
| Bridge | Empty infrastructure on water, positive bridge stock and road stock |
| Traffic light | Ordinary road, degree at least 3, available light stock, no motorway endpoint |
| Roundabout | Ordinary road, available roundabout stock, no motorway endpoint, and all four cardinal ring cells playable, unoccupied, land, not pending removal, not traffic lights and not motorway endpoints |
| Remove infrastructure | Existing infrastructure with degree at most 1 |
| Explicit connection | Current infrastructure and neighboring infrastructure, no existing connecting bit, neighbor playable and not pending removal, neither endpoint a roundabout center, and no crossed diagonal |

The proposer does not require an explicit local connection to create new
service or shorten travel. It does not enumerate arbitrary demolition of
high-degree junctions. Native simulator validation can reject proposals that
pass these Python checks.

## 7. Driveway rules

Source: the driveway loop in `candidates()` in [actions.py](../actions.py).

Consider only the first **12 houses in observation order**. For each, consider
the seven directions different from its current driveway. The new outside cell
must be playable, unoccupied land, not pending removal and not a roundabout center.
Offer the change only if at least one of these is true:

| Reason | Exact test |
| --- | --- |
| Blocked access recovery | Current outside access is outside playable bounds, occupied, not land, pending removal or a roundabout center |
| New service | New outside cell has infrastructure or is a motorway endpoint; the house currently serves no matching destination, and the new outside cell is surface-connected to a matching destination entrance |
| Queue relief | New outside cell is traversable, old outside-cell summed waiting is **> 5 seconds**, and new outside-cell summed waiting is **< old waiting / 2** |

New service receives priority 25; recovery/queue relief otherwise receive 5.
Those numbers are proposal priorities, not rewards. Matching destination tests
here use all matching destinations, not just the top-20 route subset.

## 8. Motorway rules

Source: the motorway generation/edit loops in [actions.py](../actions.py).

### Creation

- Require an already surface-connected compatible pair in the top-20/top-5 loop
  and positive motorway stock.
- Use the house's current outside access and a destination entrance's outside
  access as endpoints. Both must be playable unoccupied land with ordinary road
  infrastructure, no pending removal and no existing motorway endpoint.
- Require endpoints already surface-connected and Chebyshev separation **>= 10**.
- Deduplicate endpoint requests. The proposer does not enumerate arbitrary
  endpoint pairs or a motorway as the first connection for a disconnected pair.

### Editing and removal

- For every motorway not pending removal, offer removal with priority -5.
- For editing, keep the start fixed and move the end one cell using only
  `DIRS[:4]`: `(1,0), (1,1), (0,1), (-1,1)`.
- The new endpoint must be playable, unoccupied land, not pending removal or
  another motorway endpoint, an ordinary road, and Chebyshev distance **>= 2**
  from the fixed start. Its surface degree must be strictly greater than the
  old end's degree. Offer with priority -2.
- Existing motorway endpoint exclusion sets include pending-removal motorways.
  Pending motorways are not offered for editing/removal by these loops.

## 9. Every handwritten candidate priority

Source: `candidates()` in [actions.py](../actions.py).

| Action | Priority formula |
| --- | --- |
| Wait | `0` |
| Upgrade offer | `100 + offer.roads + (25 if offer.type == 2 else 0)` |
| Route stroke | `10*u - len(full_path) + (15 if len(full_path) <= 9 else 0) + (4 if stroke starts at house else 0)` |
| Create motorway | `10*u + ChebyshevLength - 15` |
| Local road/bridge | `u - 2` |
| Traffic light | `u` |
| Roundabout | `u - 1` |
| Local removal | `u - 8` |
| Local connection | `u + 2` only if an active vehicle occupies either existing endpoint road; otherwise `u` |
| Driveway change | `25` if it adds service, otherwise `5` |
| Edit motorway | `-2` |
| Remove motorway | `-5` |

For routes/motorways, `u = destination.demand + destination.reserved`.
Connection usage uses the vehicle's integer-position cell and nonzero
infrastructure there. Vehicles with stage `Home`, `Parking` or missing stage
do not qualify; queued vehicles at speed zero do qualify. Traffic elsewhere
near the connection does not qualify. This is current endpoint-road occupancy,
not evidence that the as-yet-unbuilt link will be useful. No recent-use history
or future route lookup is added. The usage rule changes priorities; the current final candidate cap is 48 and raw pool is 128. Reward costs are unchanged.
For local edits, `u` is the hot-location urgency from section 6. Upgrade action
features use urgency 10. Route priority uses the full path's cell count, even
though the actual action may be only its next stroke.

Priority affects three places: candidate pruning/order, the heuristic's chosen
action, and neural candidate feature 25 (`priority / 100`). The learned policy
and MCTS can select a lower-priority retained candidate. Neither can choose a
candidate already removed by pruning.

## 10. Candidate ordering, masks and legality

Source: `candidates()` and `candidate_matrix()` in [actions.py](../actions.py),
`key()` and `proposals()` in [proposals.py](../proposals.py).

1. Always create wait first. Generate one upgrade request for every current offer.
2. Sort non-wait proposals by decreasing priority, then label, then request values.
3. Reserve one candidate for each available `(command, tool)` family, subject
   to the limit. Fill remaining slots in priority order. Keep wait at index zero.
4. Raw mode returns at most **48** proposals. Guarded mode first asks for at most
   **128**, removes canonical duplicates and guard-blocked requests, then asks
   native `validateActions` with limit **48**.
5. Canonical identity sorts dictionary keys; for `connect` and `motorway` it
   additionally sorts endpoints so reversed pairs share an identity.
6. Retain only native checks with both `accepted` and `changed`. Accepted
   partial draws remain eligible. Require wait to survive as the first candidate;
   otherwise raise an error. Keep at most 48 legal candidates.
7. Pad to a `48 x 26` feature matrix. Real rows have a true Boolean mask;
   padding has zero features and a false mask. Reject over-capacity matrices.
8. Set masked logits to **-1e9**, then use softmax over real candidates.

Native preflight handles construction legality on disposable simulator state.
The pipeline does not refill by exhaustively searching after filtered actions.
Safety is enabled in controlled training. Raw heuristic controls or lower-level
`safety=False` bypass guards/native preflight but retain proposal restrictions.

## 11. Cooldowns, rejected requests and reversal tracking

Source: `Cooldowns`, `ActionGuard.allows()` and `ActionGuard.record()` in
[proposals.py](../proposals.py).

| Rule | Default | Behavior |
| --- | ---: | --- |
| Rejected request | **30 seconds fixed** | Record canonical request expiry at `before.time + 30`; block identical requests while expiry is greater than current time |
| Driveway cooldown | 20 seconds | After a recorded driveway change, block another change while elapsed time is less than 20, unless current access is blocked |
| Direct driveway reversal | 60 seconds | Block returning to the previous direction while elapsed time is less than the reversal window, unless current access is blocked |
| Motorway endpoint cooldown | 30 seconds | Lock endpoints involved in observed motorway changes; block creates/edits/removals touching locked endpoints until expiry |
| Tile removal/rebuild reversal | 10 seconds | For a recorded changed tile, block a `build` request that switches between removal and construction inside the window; allow upgrades of existing roads |

The last four durations are configurable in controlled training. Rejection
suppression is fixed in code. These are simulated-time rules, not wall-clock delays.

A `draw` beginning at a house is also driveway-guarded when its initial direction
differs from the current driveway. The guard's blocked-access exception checks
canvas bounds, non-land terrain and pending removal; it does not check every
condition in the proposer's blocked-access test. A recovery proposal can therefore
still be rejected by the guard when only occupancy/playable bounds/roundabouts
make it blocked.

Record changes from before/after observations, so new motorway IDs are tracked.
Tile history records infrastructure changes and accepted explicit removals;
the construction rule is not a blanket ban on all draws/connections at that cell.
History is reset each episode and cloned into hypothetical branches.

Count a driveway reversal when the new direction equals the prior change's
original direction within **<= reversal_window**. For motorways, compare active
undirected endpoint geometries and count active/inactive flips within the same
window. These counters do not add reward penalties or a separate 60-second
motorway ban. Actual observed modifications can still incur modification cost.

## 12. Handwritten search and action-selection rules

Source: `search()` in [alphazero.py](../alphazero.py), `choose()` and
`run_episode()` in [train.py](../train.py), and
[parallel_search.py](../parallel_search.py).

- Policy-only mode uses neural probabilities over retained candidates. Heuristic
  mode chooses maximum priority, breaking ties toward the lower index, and
  supplies a one-hot policy target. Positive simulation budget enables MCTS for
  the learned agent; default training/evaluation search budget is **16**.
- Build a new tree every real decision. Default depth cap is **4 decisions**.
  Before normal PUCT, reserve one rollout each for up to **4 distinct root actions**:
  wait, the highest-prior non-wait action, then other command/tool families by
  decreasing original policy prior. Fill remaining opening slots with other
  distinct requests in prior order if fewer families exist. Canonical request
  identity excludes reversed duplicate connect/motorway pairs. The target is
  limited by rollout budget and unique legal requests; a one-rollout search
  compares only wait when available. This guarantees request diversity, not
  useful service coverage or distinct spatial goals.
  With 16 rollouts and four alternatives, the remaining 12 use normal PUCT.
- At a serial node, select maximum
  `Q/value_scale + 1.5*prior*sqrt(node_visits+1)/(edge_visits+1)`.
  `Q = total_return / visits` for visited actions; initialize unvisited action values
  at the current node value. Break ties by lower index.
  Exploration coefficient 1.5 is a function parameter, not a normal CLI flag.
- During exploratory training, mix root priors with **15%** normalized Gamma
  samples of shape **0.3**, scale 1. No root noise in evaluation.
- Allow at most **2 sampled outcomes per action** by default. When expanding,
  draw a seed uniformly using `randrange(1, 2**31)`, fork the branch future,
  perform one transition, build a child, and stop that rollout's expansion.
- Once the outcome cap is reached, revisit the least-visited outcome using its
  original seed and assert exact resulting-observation equality. Each traversed
  action is executed with its sampled future seed, not the live future RNG stream.
- Clone/update the parent guard for newly expanded children. Terminal children
  have value zero. Externally truncated children stop expansion but retain a
  network bootstrap; their value prediction uses raw candidates.
- Back up single-agent returns as `reward + discount * child_value`, without
  alternating-player sign changes. Default controlled discount is **0.999 per
  decision**; bare `search()` defaults to 0.997 unless overridden.
- In exploratory collection, sample proportional to post-comparison support visits, or probabilities
  in policy-only mode. If all weights are zero, choose a valid action uniformly.
  There is no temperature schedule. Evaluation takes the maximum, with lower-index
  tie-breaking. Policy weights are normalized using denominator `max(1e-12, sum)` for targets.
- Restore an independent branch before each simulation. Snapshot mode uses saved
  root snapshot ID **1** and synchronizes it after real actions. Replay mode resets
  and replays the real history. Divergence raises an error rather than being ignored.

### Optional parallel-search coordination

`--search-workers` and `--torch-threads` both default to **1** and must be
positive. One worker uses the serial search above. More workers create independent
simulator hosts and use batched shared-tree search:

- Share the requested total rollout budget across workers; do not multiply it
  by worker count. Reserve a wave of at most the worker count or remaining budget.
- The coordinator assigns a different reserved root action to each opening job,
  and finishes all opening waves before scheduling ordinary PUCT. Cap opening
  wave size by remaining reserved alternatives, so spare workers cannot repeat
  a comparison before the opening phase finishes. Root selection uses original
  priors before noise; subsequent PUCT uses the existing mixed priors.
- Reserve parallel work at the node-value baseline: effective Q is
  `(total_return + in_flight * node_value) / (visits + in_flight)`, falling
  back to `node_value` when the count is zero. Parent count includes in-flight
  reservations. This avoids optimistic/pessimistic zero baselines as returns shift.
- Count pending outcome expansions toward the two-outcome cap. Existing outcomes
  can be revisited; unavailable reservations are unwound and can reduce wave size.
- Worker threads execute independent branch plans and construct leaf predictions;
  the coordinator reserves work, changes the shared tree and invokes observers.
  Apply results in stable reservation order after a wave, not completion order.
- Remove temporary visits before permanent backup. A failure to reserve any work
  raises an error. Drain submitted tasks before propagating worker exceptions.

This is a different selection schedule from serial search; stable completion
ordering does not promise identical choices across different worker counts.
Mandatory-probe regression fix: subtract one opening visit from each reserved
root action before constructing the search policy. Raw visits and Q still count
all simulator investigations for PUCT and diagnostics. Only subsequent visits
supply action-selection and policy-target weight. For example, raw visits
`[13, 1, 1, 1]` with all four actions reserved yield support visits
`[12, 0, 0, 0]`, rather than giving each probe-only action 1/16 probability.
An alternative that earns more ordinary visits can still dominate the target.
Training continues to sample stochastically from this corrected distribution;
MCTS evaluation takes its maximum. With no reserved comparisons the policy is
ordinary normalized visits, preserving the original behavior. If the budget
ends after the opening, fall back to original policy priors restricted to
visited actions (uniform over visited actions only if those priors sum to zero).
No optimizer, reward or live-inventory behavior is changed by this correction.

Logs include comparison target/completed counts, total root actions visited,
and each visited root action's request, original policy/search priors, raw visits,
support visits, corrected policy weight and mean backed-up return. `rootPolicy`
is the corrected distribution and `rootPolicySource` identifies support visits
or the small-budget prior fallback. Progress prints the most recent comparison counts; episode summaries
include `meanRootActionsVisited`.

## 13. Return targets, losses and optimizer rules

Source: `finish_episode()` and `train_batch()` in [alphazero.py](../alphazero.py),
collection in [train.py](../train.py), setup in [experiment.py](../experiment.py).

| Rule | Implementation |
| --- | --- |
| Natural failure bootstrap | Zero |
| Nonfailed cutoff bootstrap | Network value of final observation; no-model baseline uses zero |
| Return target | Reverse episode recursion `G_t = reward_t + discount*G_(t+1)` |
| Discount | Controlled default 0.999; lower-level `finish_episode()` default 0.997; evaluator uses saved config with 0.997 fallback |
| Policy target | Normalized post-comparison support visits, policy probabilities for policy-only collection, or one-hot heuristic selection |
| Policy loss | Mean `-sum(target_policy * log_softmax(masked_logits))` |
| Value normalization | Divide prediction and return target by `value_scale` |
| Value loss | Huber with default smooth-L1 transition 1, or MSE; controlled default Huber |
| Combined loss | `policy_weight*policy_loss + value_weight*value_loss`, weights both 1 by default |
| Optimizer | Adam with fixed learning rate **3e-4**, weight decay **1e-5** |
| Gradient bound | Clip global norm at **5.0**; reject nonfinite loss or gradients |
| Storage | Replay grid/scalar/action inputs are float16, converted to float32 for training |

There is no entropy bonus, explicit illegal-action learning penalty, advantage
objective, potential-based service shaping or separate terminal-failure loss.
Failure, backlog and capacity-pressure penalties enter the reward/return target instead.
Shared-encoder gradient norms/cosine and value errors are diagnostics, not extra
losses. Value scale defaults to 100 in controlled training and 10 in the bare
network/legacy loading fallback; it also normalizes search Q. Discount is per
decision even when the final decision has a shortened physical interval.

## 14. Demonstrations and replay-sampling rules

Mixed 24-row and 48-row action tensors are zero-padded at batch time, including masks and policy targets.
Spatial replay must use the current 42-channel schema and matching rewards. Legacy 39-channel model
weights can warm-start with zero-initialized risk-channel weights; historical replay is not silently padded.

Source: `ReplayMixture` in [alphazero.py](../alphazero.py) and the training loop
in [experiment.py](../experiment.py).

- Bootstrap defaults to **0 episodes**. Optional heuristic demonstrations use **128 optimizer
  updates after each**. Choose actions by the priorities in section 9, using guarded
  proposals in demonstration collection. Demonstrations inherit all those filters.
- Keep demonstrations permanently. Default self-play is **6 episodes**, with
  **64 updates after each** and batch size **32**. These counts are configurable.
- For every replay sample, choose from demonstration/recent/successful pools with
  fixed weights **0.35 / 0.40 / 0.25**. Redistribute weights when pools are absent.
- Within a chosen pool, choose an episode uniformly, then a state uniformly.
  Sample with replacement; this is not uniform sampling across all stored states.
- Successful replay consists of recent episodes grouped by map, sorted by trips.
  Take the top `max(1, len(group)//2)`, then keep only episodes with trips > 0.
  These are references to recent episodes, not a separate permanent success archive.
- Default recent-state capacity is **6000**. Evict whole oldest episodes until
  within the limit, but retain at least one, so one episode can exceed capacity.
- The alternate plain-episode training path flattens samples and samples with
  replacement, rejecting an empty pool.
- Seed Python, NumPy and PyTorch with **1000** at controlled-run initialization.
  Evaluation search uses `Random(case_seed + 900000)`; raw heuristic baseline
  validation uses `Random(case_seed)`.

## 15. Evaluation, model selection and restart rules

Source: [protocol.py](../protocol.py), [experiment.py](../experiment.py) and
[evaluate.py](../evaluate.py).

- Train, validate and test on **LosAngeles** in new experiments. Other cities in
  the historical split are not used by this protocol.
- Sample distinct random positive signed 32-bit training seeds. Exclude fixed
  validation seed **200000** and fixed test seed **300000** from every draw,
  including optional demonstrations. Save the independent sampler RNG and used
  seed ledger. Validation/test seeds must differ. Training episode offsets plus
  episode counts and optional demonstration counts remain limited to 50000.
- Use exactly one fixed validation seed after every **three** completed agent
  training examples. No initial/baseline validation and no extra final validation
  for an incomplete group of three. Resume preserves this cadence. Default
  validation budget is policy-only `[0]`. The test seed is opened only when the
  user explicitly requests testing. Demonstration collection defaults to zero.
- Rank models lexicographically by **higher mean completed trips**, then **lower
  mean accumulated waiting**, then **lower mean modification cost**. Improved
  shaped return, lower loss or longer survival alone does not override this rule.
  Ranks are diagnostic only: no `checkpoint-best.pt` is saved and no older weights are restored.
  The latest checkpoint is selected; final testing uses the first configured validation budget.
- Stop after the episode budget, or optionally **3** validation rounds without
  improvement once at least **3** self-play episodes in that invocation have run.
  Patience defaults to zero, disabling this stopping rule. Multiple evaluation
  budgets are diagnostic; the first budget identifies latest-model test behavior.
- Access final test from training only with `--final-test`. The evaluator's test
  split forbids multiple search budgets and `--save-best`. Heuristic comparisons
  can still be reported but do not become selectable learned checkpoints.
- Require positive main counts/scales/horizon and replay capacity, nonnegative
  search budgets/penalties/cooldowns/loss weights, `0 < discount <= 1`, and at least
  one positive loss weight. Runtime CLI validation is not a complete check of
  finite values, schema compatibility or tick alignment.
- Require a fresh output directory for training. Save source/config/host provenance
  and use atomic checkpoint replacement. Evaluation reuses a completed output
  only when settings, provenance and requested modes match, unless overwritten.
- `--init-checkpoint` loads weights into fresh optimizer/replay; rescale the final
  value layer by `old_scale/new_scale`. It is a warm start.
- `--resume-demonstration` requires an episode-zero checkpoint with matching value
  scale, a separate demonstration archive, zero new bootstrap episodes and no
  `--init-checkpoint`. Restore optimizer and Python/NumPy/PyTorch CPU RNG states.
  Modification, failure, unanswered and overcrowding weights must also match the saved demonstration
  checkpoint; changing them requires fresh demonstrations with a weight warm start.
  Full new-format continuation uses `--resume`, restoring replay, optimizer, RNG,
  episode position and validation metadata. Schema and reward settings must match.

## 16. Fixed representation and execution rules

Source: encoders in [environment.py](../environment.py), `_features()` and cache
helpers in [actions.py](../actions.py), and `Network` in [alphazero.py](../alphazero.py).

- Select structured current-state data: **42 spatial channels, 19 scalars and
  26 candidate features**. Do not pass future spawn schedules or RNG diagnostics
  to the policy/proposer. Guard history also remains outside the state encoder.
- Zero all grid channels outside current playable bounds. Normalize the first
  eight raw fields by **2, 4, 255, 7, 2, 9, 9, 1** respectively; clamp negative
  color to zero. Split connection/access directions into eight binary channels.
- Rasterize vehicles by integer positions, cap cell density at count/5 = 1 and
  cell summed current waiting at seconds/10 = 1. Exclude pending motorways from
  endpoint channels; normalize opposite-end coordinates by 50 and 30.
- Scale scalars by the fixed time/trip/motorway/demand/building/vehicle divisors
  **1800, 100, 10, 100, 100, 200**. Clamp six inventory counts to 0-100 and divide
  by 100. Encode only two detailed upgrade offers, with zero padding; use offer
  type `(type+1)/6`, amounts/30 and offer count/2. Other divisions do not impose caps.
- Candidate features use nine kind indicators, five tool indicators, four scaled
  coordinates, capped urgency/10, length/20, stock/100 and ID/100, three offer
  features and priority/100. The caps are upper caps only. See the companion
  document for each exact slot, default and omitted candidate field.
- Use two ReLU convolutions (`42 -> 32`, kernel 5/stride 2/padding 2;
  `32 -> 32`, kernel 3/stride 2/padding 1), fixed flatten size `32*8*13`, default
  hidden width 128, a shared grid/scalar state encoder, and separate policy/value
  heads. Score each candidate from state plus its own features; value uses state
  only. There is no recurrent memory or learned simulator transition head.
- Maintain path and connection LRU caches, each capped at **4096** entries and
  cleared at episode start. Cache context includes terrain/infrastructure/links/
  removals, bounds, bridge-stock positivity, occupied cells and railway cells.
  Cache operations are locked for concurrent search. Disable cache lookup with
  `TRAFFIC_DISABLE_PROPOSAL_CACHE=1`.
- Host responses use newline-delimited JSON and default timeout **30 seconds**;
  malformed responses, errors, timeouts and replay divergence raise exceptions.
  Reset checks version, inventory mode and required reward counters. Host DLL
  selection must match the checkpoint/protocol; no automatic migration repairs
  incompatible feature schemas or missing snapshot/preflight/future commands.

## 17. Simulator rules and scope boundary

The agent's handwritten rules above operate on the selected simulator's own
handwritten world. That world separately enforces geometry, terrain, material
stock, construction/edit legality, driveway access, vehicle routing, signals,
parking, railways, demand generation, growth and overcrowding failure. The agent
cannot change those rules through its policy. Tunnel stock has a schema slot,
but no implemented tunnel tool/action is exposed by this model.

The environment rule implementations are linked here so they are not confused
with additional Python reward terms:

| Environment rule family | Source |
| --- | --- |
| Rule constants, dimensions, world reset and observations | [TrafficTypes.cs](../../simulation/Assets/Simulation/TrafficTypes.cs), [TrafficWorld.cs](../../simulation/Assets/Simulation/TrafficWorld.cs) |
| Road/build/connection legality | [RoadNetwork.cs](../../simulation/Assets/Simulation/RoadNetwork.cs) |
| Motorways | [MotorwayNetwork.cs](../../simulation/Assets/Simulation/MotorwayNetwork.cs) |
| Material costs, stock, refunds and weekly choices | [MaterialInventory.cs](../../simulation/Assets/Simulation/MaterialInventory.cs), [OriginalUpgrades.cs](../../simulation/Assets/Simulation/OriginalUpgrades.cs) |
| Pending demolition | [RetiringRoads.cs](../../simulation/Assets/Simulation/RetiringRoads.cs) |
| Demand, service and failure | [CityDemand.cs](../../simulation/Assets/Simulation/CityDemand.cs) |
| Traffic and intersections | [TrafficControl.cs](../../simulation/Assets/Simulation/TrafficControl.cs) |
| Parking and shared lots | [ParkingNetwork.cs](../../simulation/Assets/Simulation/ParkingNetwork.cs), [SharedCarparks.cs](../../simulation/Assets/Simulation/SharedCarparks.cs) |
| Trains and railway crossings | [Railways.cs](../../simulation/Assets/Simulation/Railways.cs), [TrainTuning.cs](../../simulation/Assets/Simulation/TrainTuning.cs) |
| City layouts, growth and schedules | [CityCatalog.cs](../../simulation/Assets/Simulation/CityCatalog.cs), [CityExpansion.cs](../../simulation/Assets/Simulation/CityExpansion.cs), [OriginalSchedule.cs](../../simulation/Assets/Simulation/OriginalSchedule.cs), [OriginalMapProfile.cs](../../simulation/Assets/Simulation/OriginalMapProfile.cs) |
| Random stream and host command dispatch | [ReferenceRandom.cs](../../simulation/Assets/Simulation/ReferenceRandom.cs), [Program.cs](../../simulation/Headless/Program.cs) |

Simulator physics constants/package schedules are a separate inventory from
the model's policy/reward rules. In particular, the preserved recovery host can
differ from checked-in C# sources, so those files alone cannot certify the rules
inside a historical DLL. `OriginalReference` remains an unverified reconstruction;
future sampling and original-game parity are not guaranteed by the agent rules.

Proposed changes in [RECOMMENDED_CHANGES.md](../RECOMMENDED_CHANGES.md), including
extra service-risk inputs and reserved service-coverage candidate slots remain
proposals. The requested initial root comparisons are now implemented, along
with the 20-destination cutoff, natural-loss
and undelivered-request penalties, stronger modification cost and capacity-pressure
penalty are implemented. There is no automatic classification of overlapping
road strokes as useless; genuine tile/link changes incur the stronger cost,
and no-effect proposals continue to be filtered by preflight.


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
