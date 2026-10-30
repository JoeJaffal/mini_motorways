# Evolved Rules: plan

Recorded 2026-10-29. This is the plan for a second Mini Motorways agent that is not PPO: a hand-built planner whose decision policy is learned by genetic programming (GP). It will be compared against Mohammad's MaskablePPO model (branch `mohammad` on JoeJaffal/mini_motorways). No code exists yet.

**Status:** DECIDED = agreed by the team. PROPOSED = suggested, not yet confirmed. OPEN = not discussed yet.

## 1. Why this approach

Mohammad's first PPO model (28 Oct, see the update below) learned one map instead of learning to play:

- On its training seed (Los Angeles 1000), the best game scored 73 trips. The mean of its last 100 games was about 52.
- On held-out seeds 2000, 2001 and 2002 it scored 0 to 3 trips (sampled 3/0/0, deterministic 0/2/0) and failed at about 140 s (139.6–140.8 s). Doing nothing at all fails at about 140–154 s (mean 143 s on 2000–2009, 145 s on seed 1000; re-measured 2026-10-29). The '175 s' figure quoted earlier is not in his trained results; it appears to come from his untrained starting policy.
- On held-out maps, its deterministic play repeats about 140 `draw` commands at coordinates learned on seed 1000.
- The policy chooses raw grid cells and must discover by trial and error that roads should join houses to shops. Its only reward is completed trips.

**Update (verified 2026-10-29): Mohammad's work has moved on.** The points above describe his 28 Oct run `seed-1000-parallel-02` (commit `e6119eb`). `upstream/mohammad` now also has a planner-aided agent: a router proposes house-to-shop connections and PPO chooses among them, plus upgrades, waiting and traffic lights (`training/goal_agent.py`, `training/signal_agent.py`). It was trained on seeds 1000–1099 and selected on 2000–2004. On unseen LA seeds 4000–4009 its deterministic mean is 207.4 trips (sampled 188.9), and its best training game is 494 trips (`training/CURRENT_STATUS.md`, `docs/training/signals-fresh-2026-10-29/README.md`). Its checkpoints are only on his machine. That agent already uses the split this plan bets on (hand-written mechanics, learned choice among candidates), so which PPO model is the comparison target is OPEN (decision 14).

This plan bets that separating the mechanics from the strategy fixes this:

- **Mechanics:** reading the map, finding routes and drawing roads. These are hand-written.
- **Strategy:** which route to build, when to save tiles, which upgrade to take and what to remove. This is learned by evolution.

Every input to the learned rules is map-relative (distances, counts, timers). No coordinates are used, so the rules cannot memorise one map.

A quick throwaway prototype of a greedy planner without learning was written during the research phase (scratchpad `greedy.py`). It used only `draw` and `upgrade` commands. **Re-measured 2026-10-29 on a Release host built at 88eb62b (exact match, deterministic):** 128 trips on seed 1000; 131, 119 and 132 on seeds 2000–2002; mean 171.0 on 2000–2009 (median 156, range 119–255); mean 150.45 on 2000–2019 (median 131.5, range 53–291, SD about 72), with mean survival 614 s. Two caveats: when idle it waits in 100-tick steps, so its games are not valid AI replay recordings (every action must be 20 ticks, AiReplay.cs:46); and its upgrade rule is 'most roads, +5 for a bridge offer', not the hand rule's 'most roads'. A prototype-like variant with 20-tick waits, a 4-tile reserve and the most-roads offer scored 150.5 on 2000–2019.

The re-measurement also confirmed that materials are not the limit for an efficient builder: every lost game ended with unused road tiles (23–67 on 2000–2009; 18–73 over 61 games). Most games (8 of 10 on 2000–2009, about 3/4 overall) were lost to car supply: the failing shop had more pins than assigned cars, and no car of that colour was at home. The rest were lost to slow arrival: every pin already had a car on the way, and on seeds 2007 and 2009 linked cars of that colour sat idle at home for the whole last minute. So the rules need a travel-time or route-length term next to the car-supply margin.

## 2. Decisions

| # | Topic | Status | Choice | Notes |
|---|-------|--------|--------|-------|
| 1 | Paradigm | DECIDED | Hand-built planner + decision rules evolved by genetic programming. No PPO. | |
| 2 | Purpose | DECIDED | Head-to-head comparison with Mohammad's PPO, then pick the better model | Which of his models is the target is OPEN, see decision 14. |
| 3 | Rule set and first city | PROPOSED | OriginalReference, Los Angeles; then the other four cities with no retuning | Matches Mohammad's setup |
| 4 | Language and libraries | PROPOSED | Python 3.12; DEAP for GP; pycma for the CMA-ES control; numpy; scipy for statistics | No GPU, no LLM. Tested 2026-10-29 in a fresh 3.12 venv: deap 1.4.4, cma 4.5.0, numpy 2.5.4, scipy 1.18.1. None are installed in system `py -3.12`, so use a venv at a short path (e.g. the repo's `.venv`; Windows long paths are off). Record versions with `pip freeze` (`deap.__version__` prints only '1.4'). PPO evaluation uses a separate venv pinned to Mohammad's versions (section 6). |
| 5 | Simulator access | PROPOSED | Existing headless JSON host, **Release build** (`dotnet build simulation/Headless -c Release` → `simulation/Headless/bin/Release/net8.0/TrafficHost.dll`; bin/obj are gitignored), one process per worker | Release gives identical games and is faster, more so on long games: about 2–2.4× less host CPU on 480–700 s games, about 1.0–1.4× on 200–300 s games (measured on a loaded machine; re-measure before quoting a number). Mohammad's environment defaults to the Debug DLL. No simulator changes needed: the host already supports reset/draw/build(Remove)/upgrade/step/observe. |
| 6 | Commands the agent may send | PROPOSED | `draw`, `build` with `Remove`, `upgrade`, and waiting via `step` | Each command is followed by a host `step` of exactly 20 ticks (1 s), so every game is a valid AI replay recording (AiReplay.cs:45-47). Waiting is a host `step` 20 with no command, but it is **logged as command `wait`**: the replay rejects `step`. Tool names must use exact enum casing (`Remove`): the host ignores case, the replay does not. No `connect`, `reference` or lab scenarios: the replay rejects them (AiReplay.cs:76-89). A `draw` that starts on a house cell also moves that house's driveway (section 3.4). |
| 7 | Observation allowlist | PROPOSED | Same exclusions as Mohammad's PPO (`full-tools-staged-grid-v1`, training/environment.py): no `scheduledSpawns`, `randomAlgorithm`/`randomDraws`, `upgradeAt`, `plannedDemandMultiplier`, upgrade-offer generation fields (`weight`, `firstWeek`, `lastWeek`, `maximum`; read only `type`, `amount`, `roads`), vehicle `route`/`returnRoute`, or `feasibleDemandInterval`/`feasibilityVerified` (computed from the simulator's privileged reference route) | Mohammad's PPO reads a fixed channel list. We additionally read current-state fields he does not use: per-building `demand`, `reserved`, `demandCapacity`, `upgraded`, `entrances`, and possibly vehicle `stage`/`homeId`/`shopId`. Disconnected colour components are computed from `connections`, not read from `disconnectedColorComponents`. The report must list these extra fields and must not claim an identical observation. Whether to use `OriginalDemandInterval` is OPEN, see section 9. |
| 8 | Internal path-finding | DECIDED (delegated to Claude) | The agent runs its own A* internally | A* is the core of the approach: without it, the rules would have to pick raw cells, which is where PPO failed. It uses only the allowed observation and emits only ordinary `draw` commands; never `reference` or hidden information. Mohammad's original PPO contract excluded route planners as policy actions; his newer planner-aided agent uses a router too (decision 14). The report states the design difference either way. The hand-rule row in section 6 separates what A* contributes from what evolution contributes. |
| 9 | Fitness | PROPOSED | Lexicographic DEAP fitness `(mean trips, mean survival seconds)` over the seeds played, weights `(1.0, 1.0)`. Same 3600 s episode cap as Mohammad (`train.py:70`; all his run configs) | Changed 2026-10-29 from `trips + 0.02 × survival`. That term adds 2.8–72 (50 s = 1 trip), so it is a shaping term, not a tie-breaker; it would have flipped only 0.005% of game pairs in his 5,583 games, so either works. Survival now only decides between equal mean trips, mostly among early trees with 0 trips. Trips is the primary reported metric. Parsimony is handled separately (section 4). |
| 10 | Seed sets | PROPOSED | Train: LA 1–999 (rotating). Validation: 1500–1519. Test: **LA 7000–7099** (n = 100). Phase 1 development checks use 2000–2019 | Test seeds are never used for selection or tuning. Changed 2026-10-29: 20 test seeds can only detect a gain of about 43 trips (section 6), and 2000–2019 are no longer fresh: the prototype was measured on them, and Mohammad used 2000–2004 to select his newer models and 3000–3009, 4000–4009, 5000–5009 and 6000–6009 as his test sets. Seed 1000 and 2000–2002 are still reported for the 28 Oct PPO run. His training pool (1000–1099) does not overlap ours. |
| 11 | Motorways, roundabouts, traffic lights, driveway edits | OPEN | Left out of version 1 | This caps the agent. Add them as candidates later if time allows. Note: `draw` can still move a driveway without being asked: a stroke that starts on a house cell re-points its driveway (TrafficWorld.cs:241-242, 262); the executor allows this only for houses with no link yet, where it is harmless (section 3.4). Mohammad's newer agent uses traffic lights, so leaving them out may matter if it is the target. |
| 12 | Extensions | OPEN | Style atlas (section 8.1) and/or failure autopsies (section 8.2) | These raise originality. Decide after Phase 3. |
| 13 | Team split | OPEN | | Example: one person on the skeleton, one on the evolution loop |
| 14 | Which PPO model to compare against | OPEN, deferred (2026-10-30) to the comparison phase; contact Mohammad then for files and his current results | (a) the 28 Oct single-seed run `seed-1000-parallel-02` (needs only `final.zip`); (b) his newer planner-aided model (`signals-night-01` or `signals-context-01` `validation-best.zip`, plus the tip `training/` stack and host); or both | (b) scores about 207 trips (deterministic, LA 4000–4009), above the prototype's ~150. With (b), section 1's argument, the 'nearly certain' line in section 6, the hand-rule bar and decision 11 all need revisiting. |
| 15 | Relationship to Mohammad's router | DECIDED 2026-10-30 | (a) Separate full agent: our own A*, executor and candidates (Phase 1 as written). Do not reuse his router. | (a) mixes 'better mechanics' with 'better learner' in any win; the report must say so. Option (b) (GP on his router, a controlled test of the learner) stays possible later as an extra experiment. |

## 3. Architecture

```text
simulator (C# headless host, Release)
   ^ JSON commands        | JSON observation
   |                      v
+------------------------------------------------+
| HAND-BUILT SKELETON                            |
|  1. Parser       -> road graph, houses, shops  |
|  2. Event check  -> act now, or wait?          |
|  3. Candidates   -> A* routes, removals, offers|
|  4. Executor     -> straight draw strokes      |
+------------------------------------------------+
                  ^ chosen action
+------------------------------------------------+
| LEARNED RULES (evolved formulas)               |
|  Priority, Hold, Upgrade, Remove               |
+------------------------------------------------+
```

### 3.1 Parser

- Read `terrain`, `infrastructure`, `connections`, `pendingRemovals`, `buildingKinds`, `buildingColors`, `buildings`, `inventory`, `upgradeChoices`, the playable bounds (`playableXMin/YMin/XMax/YMax`) and `time` from the observation. Grids are flat with index k = y × 50 + x; cells in JSON are objects `{x, y}`; names are camelCase.
- **Road graph:** `connections` is a symmetric 8-bit link mask per cell. Bit d is direction (dx, dy) in the order E, SE, S, SW, W, NW, N, NE, with +y = increasing row (TrafficWorld.cs:47). It is the surface-road graph once tiles with `pendingRemovals = 1` are dropped: they keep their bits until cars clear, but new routes skip them (TrafficWorld.cs:55-57, 287-309). House and shop access cells appear in it as endpoints with a single driveway link. Motorways are not in it and roundabout rings are one-way; both are out of scope for v1.
- **Houses and shops come from the `buildings` list**, not the grids: `id`, `color`, `isHouse`, `cell`/`width`/`height`, `demand` (waiting pins), `reserved` (pins with a car assigned), `demandCapacity`, `overcrowdedFor`, `upgraded`, `carparkId`, `drivewayDirection`, `entrances[]`/`entranceDirections[]` (fall back to `entrance` when empty). Use `buildingKinds`/`buildingColors` only as an occupancy mask: each cell holds one value and later buildings overwrite earlier ones (TrafficWorld.cs:341-343).
- **Shared lots:** in OriginalReference two shops of different colours can occupy the same footprint (same `carparkId`, 9 shared bays), with two entrances facing opposite ways (SharedCarparks.cs:43-63). The grid shows only the later shop. Treat every entrance as a target and each shop on the lot as a separate colour target. On LA they appear from about 300–400 s (seen on seed 2008 at 395 s).
- **Playable bounds:** a cell is playable iff xMin ≤ x < xMax and yMin ≤ y < yMax (CityExpansion.cs:62-66). The area grows over time and only the current bounds are observable, so re-read them every observation.
- **Inventory** is `[roads, bridges, motorways, trafficLights, roundabouts, unused]`; LA starts at `[25,1,0,0,0,0]`. **Offers** (`upgradeChoices`, up to 2) show `type`, `amount`, `roads`; the other offer fields read as 0 and are excluded. Taking one adds `amount` to `inventory[type]` and `roads` to road tiles, so an offer's road value is `roads + (type == 0 ? amount : 0)`.
- **Vehicles:** `stage` is a string (Home, Outbound, EnteringParking, Parking, LeavingParking, Returning, AligningHome); busy = not `Home`.
- Use breadth-first search over the links to find connected components, and which houses already reach any entrance of a shop of their colour.
- Note: road tiles next to each other are not linked automatically. Links come from `draw` strokes, plus automatic driveway links: (a) a newly built road tile is linked to any house or shop whose driveway or entrance points at it, even when the stroke only passes by (TrafficWorld.cs:170-173); (b) a house or shop that spawns with its driveway facing an existing road is linked straight away (CityDemand.cs:27, SharedCarparks.cs:54). So links can appear without any stroke: always read `connections`, never infer links from adjacency.

### 3.2 Event trigger

Make a decision only when one of these happens; otherwise wait:

- a new house or shop appears;
- a new upgrade offer appears;
- a shop's `overcrowdedFor` timer crosses a threshold;
- a shop is upgraded (`upgraded` turns true: capacity 6 → 9 and its demand rate doubles);
- 10 s pass with no decision (fallback).

A game then needs roughly 50–150 decisions instead of one per second. This is an estimate: a decision can cost several commands, so budget compute in commands. Waiting is sent as `step` 20 ticks at a time so that recordings stay valid: the state is identical to one long step, but each 20-tick wait needs its own `afterTrips`/`afterTime` in the recording. Trigger on observed buildings and offers, not on a clock, because shops follow a jittered schedule (section 3.5). A pending upgrade offer is always taken in the decision where it appears (section 3.5).

### 3.3 Candidate generator

For each house that does not reach a shop of its colour, generate about 3 A* routes over buildable terrain inside the playable area:

- **(a) Attach:** to the nearest cell of an existing road component that reaches a shop of the same colour (online Steiner tree; roads have no colour of their own, so 'same colour' comes from the BFS). Every road cell the route touches or crosses becomes a junction, and junctions of degree 3+ halve lane speed, so count them in the cost.
- **(b) Direct:** to the outside cell of each of the shop's entrances (`entrances[]`; shared lots have two, at opposite ends, possibly shared by two colours). Keep the cheapest.
- **(c) Separated:** a route that penalises cells and junctions used by other colours. Separation comes only from avoiding those cells: a crossing always shares a cell and forms a junction that joins the two networks, and there are no overpasses (bridges are only for water; motorways are excluded). Which colours use a cell is worked out from house-to-shop paths.

Also add:

- removing a road segment that no house-to-shop shortest path uses (vehicle routes are excluded from the observation, so the agent cannot see which tiles active cars are committed to; expect some removals to stay pending, section 3.4);
- taking upgrade offer 0 or 1 (while an offer is pending, one of these is always taken: an untaken offer blocks every later weekly offer);
- waiting.

The A* must follow the rules that `draw` actually enforces (`DrawRoad` → `Build` → `Connect`, TrafficWorld.cs:117-254), or strokes will leave gaps (verified 2026-10-29 by code reading and experiments):

- **Cells:** inside the current playable bounds (upper edge exclusive); not blocked terrain (`terrain == 2`; `1` is water); not a building cell except as the route's first or last cell; not pending removal; not a roundabout cell. One road tile per new cell; existing road cells cost nothing.
- **Links:** a house or shop access cell links only to the one cell in its driveway or entrance direction (`ValidParcelLink`, TrafficWorld.cs:223-231; houses use `drivewayDirection`, shops `entranceDirections[i]`). A diagonal may not cross an existing or planned diagonal in the same 2×2 block (TrafficWorld.cs:215-220).
- **Rails (London only):** roads cross rail only at straight rail cells, orthogonally and at a right angle (Railways.cs:124-133). `terrain` does not mark rails; read `railLines`.
- **Water and bridges:** `draw` builds a Bridge on water (TrafficWorld.cs:247). Each water cell costs 1 road tile, plus 1 bridge item (`inventory[1]`) if no orthogonal neighbour is a Bridge tile, existing or earlier in the same route (MaterialInventory.cs:31, 40-41). Forbid diagonal steps into or out of water (as `PotentialRoute` does), so each contiguous water run is one span costing at most 1 item. Reject routes that need more new spans than `inventory[1]`. On LA the x = 22 river is in play on 20 of 21 test seeds, and buildings across it appear at about 160–290 s.
- **House driveways:** every route's path starts on the house cell. If the house already has a link (`connections` at its cell ≠ 0), the first step must be to the driveway's outside cell (house + direction[`drivewayDirection`]), so its driveway never moves. If the house has no link yet, the first step may go in any direction; the stroke then re-points the unused driveway, which is harmless and is what the prototype did (decided 2026-10-30, Phase 1 plan). End shop routes on the entrance's outside cell. Building a road there links the house or entrance automatically (TrafficWorld.cs:172-173). A stroke that starts on a house cell in another direction is accepted but silently moves the driveway and deletes the old link (TrafficWorld.cs:241-242, 262).
- **Optional, conservative:** the simulator does *not* forbid diagonals that cut a building corner; only `PotentialRoute` does (RoadNetwork.cs:207-211). Keeping that rule is harmless.

`RoadNetwork.cs` `PotentialRoute` (:193-217) is only a template for the terrain/parcel search: it ignores existing roads, playable bounds, pending removals, diagonal crossings, rails and materials. Mohammad's `training/planner_diagnostic.py` (upstream/mohammad) is a visible-state A* with a stroke splitter covering most of these rules (not span-aware bridge cost or rails) and is worth reading before writing `candidates.py`.

### 3.4 Executor

- Split the chosen route into straight segments in the 8 directions (horizontal, vertical, exact 45°). Send each as `draw(from, to)` followed by `step` 20. This is needed because `draw` lays one rounded straight line between its endpoints (`RasterLine`, TrafficWorld.cs:267-272); 8-direction strokes reproduce the planned cells exactly. A stroke links every consecutive pair of cells it covers, including existing roads it passes through, unless `Connect` refuses the link. A cell that cannot be built, or a refused link, leaves a gap and the stroke continues. Check road and bridge stock before sending a stroke.
- `draw` reports `accepted = true` if any tile was built **or** any link along the stroke was made or already existed. A partly successful stroke, and even a no-op redraw, both report `true`; `message` describes only the last sub-step. After each stroke, check `connections` and `infrastructure` in the observation the reply already contains, confirm every intended link (including the house or entrance link), then retry or abandon the route.
- **Driveways:** a stroke may start on a linked house cell only in its current `drivewayDirection`; an unlinked house may be left in any direction (section 3.3). Ending a stroke on a house never changes its driveway.
- **Remove:** one road tile per command, costing 1 s of game time (a roundabout is removed whole; a motorway ending at the cell is retired too; building cells, empty tiles and already-queued tiles are rejected). If no active car has the tile in its remaining lanes or its return route, the tile is released and refunded in the same reply. Otherwise it is closed to new routes at once, but released and refunded only when every car committed to it is home, which can take tens of seconds (55–65 s measured). Drawing through a pending tile is rejected ('Committed trips are still using this road'). Read `pendingRemovals`.
- **Refunds** happen on release, not when queued: a road returns 1 road tile; a traffic light 1 road + 1 light; a bridge tile 1 road, with the bridge item returned only when the last tile of its span is gone (a span split by removal keeps one ID, so rejoining it refunds nothing); a roundabout 1 roundabout. Ignore the host message 'previous spending retained': materials are refunded.
- **Host protocol:** reset with `version = 'OriginalReference'`, `scenario = 'LosAngeles'` and `seed` (variation defaults to SameMap). Commands do not advance time. `step` without `ticks` advances 1 tick, so always send `ticks = 20`. A malformed request returns an `error` with no state change; don't record it. The host's `truncated` means 'scenario rejected', not a time cap, so the agent enforces the 3600 s cap itself. Each reply carries a full observation (about 40–66 KB).
- **Replay log:** log every command + 20-tick pair as one `AiReplayAction` (`AiReplayRecording`, schema version 1): `command`, `tool`, `x`, `y`, `toX`, `toY`, `id`, `choice`, `ticks = 20`, `accepted` (as the host returned it), `afterTrips` and `afterTime` from the observation after the step. Log waits as `wait`, never `step`. Write tool names in exact enum casing (`Remove`). Record every command exactly as sent, including rejected ones: dropping one or turning it into a wait breaks verification, and a rejected draw can still have side effects. Set `version = 'OriginalReference'` and `variation = 'SameMap'`; the final `score`, `duration` and `terminated` must equal the last observation. Use exact camelCase field names (the Unity verifier's JsonUtility is case-sensitive).

### 3.5 Game facts (verified 2026-10-29)

- **Failure:** the game is lost when a shop's `overcrowdedFor` timer exceeds 50 s (CityDemand.cs:208). It grows only while waiting pins exceed capacity, at up to 1 s per second, so continuous overcrowding loses in about 50.5 s. Within capacity it is held at 48 s or below and falls at 2 s per second; each delivery holds it at 48 s or below and cuts min(3 s, 10%). Capacity is 6; 9 after the shop's scheduled automatic upgrade, which also doubles that shop's demand rate; 7 for stations. A new shop has 30 s of grace.
- **Houses:** one house is tried every 20 s from t = 20, for the shop with the weakest estimated supply; a colour is skipped once it has 5 houses per shop. A new shop also brings a supporting house if no house of its colour can reach it. Each house has exactly 2 cars.
- **Shops:** no fixed interval. They follow a per-city schedule drawn at reset with random jitter (OriginalSchedule.cs:15-35); a failed placement retries 20 s later; at most 30 shops. On LA, about 6 shops in 4 colours (red, blue, green, yellow) arrive by about 440 s, purple first at 600–840 s, and more shops up to about 2200 s. Grouping-3 schedule entries are destination upgrades (the first, red, at 320–720 s; more until about 4400 s): demand shocks the rules must notice.
- **Upgrade offers:** the first comes at 140 s. A new offer is generated when time ≥ 140 × (offers granted + 1) and none is pending (MaterialInventory.cs:12). The clock does not pause while an offer is pending, and no week is lost: an overdue offer appears on the tick after acceptance. Offers never expire. LA offers: traffic lights ×2 + 20 roads; roundabout ×1 + 20; bridge ×1 + 20; motorway ×1 + 10 (from the 3rd offer); 30 roads (from the 2nd). Weights and windows are hidden.
- **Dispatch:** each pin is served by the idle car, from any house of that colour, with the lowest route cost, so all shops of a colour share one car pool.
- **Route cost (congestion-free):** Σ max(1, floor(10 × distance ÷ lane speed)) in tenths of a second, +500 per U-turn; lane speed 0.5 tiles/s, × 2/3 for a 90° turn, × 1/3 sharper, × 0.5 at an uncontrolled junction of degree ≥ 3 (RoadNetwork.cs:52-91). Actual travel is slower (car-following, junction yielding, parking, 3 s service).

## 4. The learned rules

Four expression trees are evolved together as one individual:

| Tree | Input | Output | Used for |
|------|-------|--------|----------|
| Priority | features of one candidate | score | choosing the best candidate |
| Hold | global features | threshold | build only if the best score exceeds this; keeps tiles for colours still to come |
| Upgrade | features of one offer | score | which offer to take |
| Remove | features of one road segment | score | which roads to recycle; a removal runs only if its score is above 0, so a constant negative tree means 'never remove' |

**Functions:** `+ − × protected÷ min max if>` and random constants.

**Terminals (inputs, about 25, all map-relative, normalised to about [0, 1]):**

- Route: tiles needed, bridge items needed, path length, turns, new junctions with 3 or more links (each halves lane speed), cells shared with other colours, candidate type (attach, direct or separated).
- Target shop: waiting pins (`demand`), pins with no car assigned (`demand − reserved`), capacity, overcrowding timer, demand rate, houses already serving it, free-flow trip time from its houses.
- **Car-supply margin (per colour):** roughly `Σ over connected same-colour houses of 2 ÷ round-trip time − Σ demand rate of that colour's shops`. Route choice ignores congestion, so the free-flow round-trip time can be computed from the road graph as (route cost out + back) ÷ 10 s plus overhead; use the simulator's own feasibility estimate as a reference (+3 s service +8 s, CityDemand.cs:117-118). Real trips are slower, so treat the margin as an optimistic bound. The demand rate is 1/`OriginalDemandInterval` if that field is allowed (OPEN, section 9); otherwise estimate it from increases in `demand` over a sliding window.
- Offer (Upgrade tree): roads the offer adds (`roads`, plus `amount` if type 0), item amount, a 0/1 flag per item type, current stock of that item.
- Segment (Remove tree): tile count, number of house-to-shop shortest paths using it, colour served, dead-end flag, tiles it would refund.
- Global: road tiles and bridge items in stock, pending refunds (tiles in `pendingRemovals`), seconds until the next upgrade offer (`max(0, 140 × (offers granted + 1) − time)`; the agent counts its own acceptances), game time, disconnected colour components (same definition as the simulator's `disconnectedColorComponents`: separate road networks that each serve a matched house–shop colour, minus 1; 0 if fewer than 2 or only one colour is served; RoadNetwork.cs:237-257; computed by the parser), houses with no route to a same-colour shop, shops with no connected house, distance to the edge of the current playable area.

Non-finite tree outputs score −∞ (the candidate is never chosen).

**Size limits:** depth at most 6 (DEAP `staticLimit`, key = maximum height over the four trees), with lexicographic parsimony pressure: tournaments compare (fitness, −total nodes across all four trees), so smaller individuals win exact ties (Luke & Panait 2002). Ties are common because behaviourally identical trees get identical deterministic scores; break ties only between individuals scored on the same seeds. Do not use DEAP's `selDoubleTournament`: it measures size with `len(ind)`, which is always 4 for a four-tree individual (tested).

**Implementation (DEAP, tested 2026-10-29):** an individual is a list of 4 `PrimitiveTree`s, one `PrimitiveSet` each (the pattern of DEAP's ADF example). Crossover applies `gp.cxOnePoint` to tree i of both parents; mutation picks one tree and applies `mutUniform`, `mutNodeReplacement` or `mutEphemeral`. Define creator classes and primitive sets at module top level so Windows worker processes can import them. Constants reloaded with `from_string` become plain terminals.

## 5. Evolution loop

1. **Population:** 64 individuals; consider 128 later. Seed it with the hand-written rule from Phase 1 plus random trees. The hand rule is written as four tree strings (`gp.PrimitiveTree.from_string`): Priority = −tiles needed (or the attach flag), Hold = 4 − road stock, Upgrade = offer roads, Remove = −1. A unit test checks that this seeded individual plays the same moves as the Python hand rule on seed 1000.
2. **Evaluate (racing, common seeds):** each generation, draw one set S4 of 4 training seeds and one set S12 of 12 more from LA 1–999. Every individual plays all of S4; the top 25% by S4 mean also play all of S12. Because the whole shop schedule is drawn at reset (TrafficWorld.cs:90), shared seeds make seed difficulty cancel out when individuals are compared (in a simulation, the chance of picking a truly top-8 individual rose from 0.50 to 0.84). Invalidate every fitness at the start of each generation, so elites and unchanged clones are re-scored on the new seeds; do not reuse DEAP's `if not ind.fitness.valid` shortcut. Tournaments rank everyone on the S4 mean; the 16-seed mean is used only to choose elites and hall-of-fame candidates. Optionally score each game as fitness minus the cached hand-rule fitness on the same seed. Measure progress only on the fixed validation seeds. Save S4 and S12 for each generation.
3. **Select:** tournament of size 4, with elitism: the top k (about 2–4) individuals by 16-seed mean are copied unchanged into the next generation and re-scored on its new seeds. This needs a custom generation loop in `evolve.py` (about 40 lines) built from DEAP's trees, operators, `selTournament` and `selBest`: DEAP's `eaSimple` has no elitism, and `eaMuPlusLambda` keeps parents' old scores.
4. **Vary:** crossover swaps subtrees between parents, within the same tree type. Mutation replaces a subtree, swaps an operator or changes a constant.
5. **Hall of fame (validation archive):** each generation, add the top 3 individuals by 16-seed mean to an archive (tree text). Every 5 generations, and once at the end, play every not-yet-scored archive entry on the fixed validation seeds (1500–1519), caching scores by tree text. The final model is the archive entry with the best validation mean, not the best on training. Do not rank by training fitness across generations (e.g. DEAP's `tools.HallOfFame` fed training fitness), because seeds rotate and those scores are not comparable.
6. **Repeat** until a wall-clock budget runs out, not for a fixed number of generations (about 20 per night at current game lengths, section 9); checkpoint every generation so a run can resume. Use parallel host processes, one per worker (10 on the team laptop): a `ProcessPoolExecutor` whose initializer starts one long-lived Release host per worker, one job per (tree strings, seed), collected with `as_completed`, with timeouts and restart on hang. Agent code runs in processes, not threads (GIL). Cache results by (tree text, seed).
7. **Save:** each generation's best trees (as text), the full configuration, the seeds used, the simulator commit (`git rev-parse HEAD`) and the package versions.

**Determinism:** the simulator is deterministic: the same seed and the same command sequence give a byte-identical game (checked across parallel Release hosts). A (rule set, seed) score is therefore exact *provided the agent is deterministic too*. In a test, an agent whose candidate order came from iterating a set of strings scored 2–9 trips on one seed across six processes. So: (1) never let iteration over a set of strings, or `hash()` of a string, decide candidate order (dicts and int/tuple keys are fine); (2) break A* and candidate ties with an explicit key, e.g. (score, y, x, candidate id); (3) launch workers with `PYTHONHASHSEED=0` as a backstop; (4) add a test that plays the same (rules, seed) in two processes and asserts identical command logs. The only remaining noise is variation between seeds.

Two different agents on the same seed share the starting map, the planned shop colours with their nominal times, and the 20 s house-spawn cadence. Shop and house locations, lot types, actual shop times (failed spawns retry 20 s later), upgrade offers, demand phases and which shop gets an upgrade can all differ, because the agent's roads block cells and its traffic and choices consume the shared random generator. Paired per-seed comparisons are still valid, but agents correlate less across seeds (section 6).

## 6. Evaluation and comparison

**Rows in the results table, all on the same seeds:**

| Row | Purpose |
|-----|---------|
| Do nothing | floor (about 140 s, 0 trips) |
| Simulator `reference` builder | privileged diagnostic only; not a legal agent and not replayable |
| Hand-written rule (Phase 1) | **main bar**: shows what the skeleton alone achieves |
| CMA-ES-tuned linear weighted sum of the same terminals each tree sees (about 25–40 weights, bounded [−5, 5]), with the same game budget, seed rotation and validation archive as GP | control: does GP structure beat weight tuning on identical inputs? |
| Evolved rules (GP) | this model |
| Mohammad's PPO, sampled and deterministic | the model to compare against |

**Seeds:**

- Report LA test seeds 7000–7099 (decision 10).
- For the 28 Oct PPO run, also report seeds 2000–2002 to match Mohammad's published numbers (sampled 3/0/0, deterministic 0/2/0 trips; `summary.json` `after` and `deterministic_after`).
- Report seed 1000, PPO's training seed, using PPO's deterministic score and last-100 mean as well as its best game. The last-100 mean (52.1) and best game (73) are already in Git (`docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/` on `upstream/mohammad`); they come from sampled training games, so label them 'training'. No deterministic seed-1000 score was ever recorded; it needs `final.zip`.
- Then report seeds 7000–7009 for each other city (descriptive only).

**Metrics:** per game, record the same fields Mohammad's `evaluate` writes into the `after` and `deterministic_after` lists of `summary.json` (training/train.py@e6119eb:36-47, training/environment.py@e6119eb:339-345): `trips`, `seconds`, `rejected_actions`, `commands`, `action_counts` (keyed by tool or command name, e.g. `draw`, `Remove`, `upgrade`, `wait`), `mean_car_wait`, `max_car_wait`, `terminated`, `truncated`, `scenario_seed`, `city`, `deterministic`. Compute them the same way: car wait is the mean and max of every vehicle's `waiting`, sampled after each 20-tick step; `rejected_actions` counts host rejections. Add our own fields with new names: `failed_shop` and `road_tiles_at_failure` (his files have no equivalent). His top-level training keys do not apply.

**Statistics:** for each comparison, compute the paired per-seed difference (agent − baseline) in trips on the 100 test seeds. Report the mean difference with a 95% bootstrap CI (`scipy.stats.bootstrap`, 10,000 resamples) and the paired-t CI, plus a two-sided Wilcoxon signed-rank p-value as a secondary check (it tests a median-type shift, not the mean). Why n = 100: one shared random stream means an agent's actions change all later spawns and traffic. Two near-identical prototype variants correlated only about 0.45 across seeds, with an SD of paired differences of about 65 trips, so the minimum detectable gain (power 0.8) is about 43 trips at n = 20 but about 18 at n = 100. Re-estimate this in Phase 1. Test games are cheap (100 games ≈ 6 min). Per-city results and PPO results on 2000–2002 are descriptive only.

**Success means the final evolved rule set beats the hand-written rule and the best CMA-ES-tuned weights on the test seeds, with a paired 95% interval that excludes 0, not merely beating PPO.** Both must hold, so each is tested at α = 0.05 and no multiplicity correction is needed; any comparison claimed on its own gets a Holm correction. This is a claim about these specific rule sets. To claim that GP *as a method* beats weight tuning, run at least 3 independent GP runs and 3 CMA-ES runs with different RNG seeds and report the spread; if time allows only one GP run, say that run-to-run variance was not measured. Beating the 28 Oct single-seed PPO on held-out seeds is nearly certain for any agent that reads the map, so on its own it proves little. Mohammad's newer planner-aided model (about 207 trips deterministic on LA 4000–4009) is a much harder bar (decision 14).

**Referee:** every reported game is saved as an `AiReplayRecording` (schema 1) and replayed through `AiReplaySession` (simulation/Assets/Simulation/AiReplay.cs), which checks every command's `accepted` flag, trips and time, and the final score and duration:

- **Primary (tested on this machine 2026-10-29):** the headless `--verify-replay` from Mohammad's branch (`upstream/mohammad:simulation/Headless/Program.cs:38-52`; not on this branch). Build it outside the repo without checking out a branch: `git archive e6119eb simulation/Assets/Simulation simulation/Headless | tar -x -C <scratch dir>`, then `dotnet build <scratch dir>/simulation/Headless -c Release`, then `dotnet <scratch dir>/simulation/Headless/bin/Release/net8.0/TrafficHost.dll --verify-replay <file>`. Pass = exit code 0 and result PASS on stdout; about 3 s per replay. The simulation code at e6119eb is identical to this branch. It passed Mohammad's 73-trip `best-game.json` and a recording from our own test client. Do not cherry-pick commit 53b4251 (20 files, touches shared code).
- **Optional, needs a built player:** the Unity Original app. The replay code is on this branch (Viewer/AiReplayViewer.cs), but no player is in Git or on this machine; building one needs Unity 6000.6.0f1 (Traffic Lab > Build Original Windows app). Mohammad has one on his PC. Usage: `simulation/Builds/Windows/TrafficLabOriginal/TrafficLabOriginal.exe --replay <abs.json> --replay-verify -batchmode -nographics -logFile <log>`; wait for exit, then require exit code 0 and `TRAFFIC_AI_REPLAY_PASSED=` in the log.
- Both paths run the same AiReplaySession code: they are independent of our agent, not of each other. The replay does not check `truncated`.

**Needed from Mohammad (for the 28 Oct run):** only `final.zip` from his run folder `output/training/seed-1000-parallel-02/` (his completed 4-hour run at source revision `e6119eb`, resumed from `seed-1000-parallel-01/latest.zip`). It is the trained Stable-Baselines3 MaskablePPO checkpoint: network weights (`policy.pth`), optimizer state, hyperparameters and the observation and action space definitions. It is not in Git: `/output/` is ignored and no branch contains a `.zip`.

**Already in Git, no need to ask:** the other files of that run are archived on `upstream/mohammad` at `docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/` (hashes in `manifest.json`): `config.json` (schema `full-tools-staged-grid-v1`, 3600 s episodes, seeds, package versions, commit e6119eb with dirty = false), `summary.json` (his held-out results), `best-game.json` (his 73-trip replay), `episodes.jsonl`, `progress.csv`, `seed-summary.json` and the worker monitors. Read them with `git show upstream/mohammad:docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/<file>`. `train.py` reads `config.json` only when resuming training; for evaluation it is a provenance record.

**If the newer model is the target (decision 14):** we would need `output/training/signals-night-01/validation-best.zip` (or `signals-context-01/validation-best.zip`) from his machine, and would run it from a `git archive upstream/mohammad` copy outside the repo (it probably needs the tip host's extra commands and its added `DrawDiagnostics.cs`/`UsefulConnectivity.cs`).

**Timing (decided 2026-10-29):** this is not a blocker. Build and train first, and run the PPO comparison once the files arrive. Until then, compare only on seeds 2000–2002. (Update: seed 1000's published training last-100 mean and best game can also be used now; only the deterministic seed-1000 score and the test seeds need `final.zip`. This applies to the 28 Oct run; the newer model would need other files, decision 14.)

With `final.zip`, load the model with `MaskablePPO.load(final.zip, device='cpu')` and call `evaluate` from his `training/train.py` at the tip of `upstream/mohammad` (it needs that whole `training/` folder; extract it with `git archive`, never by checking out a branch). It picks the legacy 50-channel observation for this checkpoint by itself, and in that mode its environment and simulator behaved exactly like revision `e6119eb` (checked step by step in lockstep over 3,873 decisions). Pass `host_dll=` the built TrafficHost.dll. Run it sampled and deterministic on exactly the same test seeds as our agent, calling `torch.manual_seed(43)` once before each seed loop: that is his `train.py` protocol, so sampled results on 2000–2002 should reproduce his published numbers. Do not use `evaluate_checkpoint.py` for sampled runs, because it reseeds every seed. Without `final.zip`, PPO can only be compared on seeds 2000–2002 and seed 1000's training figures, which he already published.

**PPO evaluation environment (not installed yet):** a separate venv outside the repo (root `.gitignore` covers only `.venv/`), e.g. `py -3.12 -m venv <dir>`, with `torch==2.14.1+cpu` from `https://download.pytorch.org/whl/cpu`, then `gymnasium==1.4.0 stable-baselines3==2.9.2 sb3-contrib==2.9.2 numpy==2.5.4` (his `training/requirements.txt`, README and `config.json`). He ran Python 3.12.14; this machine has 3.12.5. Record the difference, and install 3.12.14 if the loaded model gives different scores on 2000–2002.

**Disclose in the report:**

- the agent plans routes internally with A*;
- it decides on events, though still one command per 20 ticks;
- it uses the same exclusion list (no future or RNG information), plus the extra current-state fields listed in decision 7;
- it was trained on many seeds while Mohammad's model used one. Optionally add a fairness control: label PPO as "single-seed PPO", or retrain it on the same seed pool.

**Compute report:** CPU-hours and games played, next to PPO's 4 hours × 4 workers.

## 7. Phases and timeline (about 4 weeks for 2 people)

| Phase | Work | Exit check |
|-------|------|------------|
| 1. Skeleton (week 1) | Host client, parser, A* matching the simulator's draw rules (section 3.3), executor, replay logging, hand-written rule (attach route, keep a reserve of 4 tiles, take the offer with the most roads at once, never remove), tests (link rules, bridge cost and refunds, driveway safety, replay round trip, same result in two processes) | Replays verify with the headless verifier (section 6). Prototype numbers re-measured (done 2026-10-29: 150.45 mean on 2000–2019). The hand rule averages at least about 140 trips on 2000–2019, i.e. within about 10% of the prototype; report median and worst seed too (SD about 72). A mean below 80 means the skeleton is broken. Re-measure throughput with the real agent in game-seconds per wall-second, and estimate the per-seed correlation between hand rule and prototype. |
| 2. Evolution loop (week 2) | DEAP trees, terminals, racing with common seeds, seed rotation, validation archive, result cache, checkpoints. CMA-ES control (`tune_cmaes.py`): one linear weight vector per decision over the full terminal set, about 25–40 weights bounded [−5, 5], popsize about 16, minimising −fitness. | A short run improves validation fitness over generation 0 |
| 3. Full runs (week 3) | One overnight GP run on LA (about 10 h, wall-clock stop). CMA-ES gets the same number of games (about 70–140 generations at popsize 16 × 8 seeds) on a separate night or machine, not alongside GP; run 3+ CMA-ES runs with different RNG seeds, and GP runs 2–3 on later nights if time allows (needed for any method-level claim). Evaluate on the test seeds; run the other four cities | Results table filled in for LA |
| 4. Comparison and write-up (week 4) | PPO comparison, statistics, the evolved formulas explained, limitations | Report draft |

**First 3 days, which test the core idea:**

1. Build the skeleton and hand rule. Run them on seed 1000 and 2000–2019 against do-nothing and the reference builder.
2. Smoke test (not the section 6 control): CMA-ES (population 16, 10 generations, about 1,280 games, about 1.2 h) over 4–6 hand-rule parameters (e.g. tile reserve, attach-vs-direct bias, offer preference) on training seeds 1–8, with all 16 candidates on the same seeds; then evaluate on 2000–2019.
3. The approach is worth continuing if (a) the hand rule averages at least about 140 on 2000–2019 (roughly the re-measured prototype) and (b) tuning improves held-out scores, not just training scores.

## 8. Optional extensions (to raise originality)

### 8.1 Style atlas (quality-diversity)

Instead of keeping one best rule set, keep the best for each play style, for example:

- shared trunk roads or one branch per shop;
- hoarding tiles or spending them;
- how often routes cross other colours.

Use MAP-Elites with the pyribs library (install it with `pip install ribs`; the PyPI package `pyribs` is only a placeholder). Store each individual's four trees as a tuple of strings in a `GridArchive(solution_dim=(), solution_dtype=object)`. The built-in emitters only vary real-valued vectors, so generate offspring with our own DEAP variation, inside a small `EmitterBase` subclass or by calling `archive.add` directly. pyribs needs numba: keep the venv at a short path or set `NUMBA_DISABLE_JIT=1`. Then learn which style suits which map or city. First run a quick test: if the best-style-per-map beats the single generalist by less than about 5% on held-out seeds, skip this extension.

### 8.2 Failure autopsies

After every lost game, record which shop failed and why. A counterfactual replay to about 60 s before failure checks whether the cause was materials, road layout or car supply. Use these labels to bias mutation and to explain results.

### 8.3 Time-to-failure input

Add a terminal for each shop's predicted time to failure, computed from the car-supply model.

## 9. Risks and open questions

- **The skeleton caps performance.** Evolution cannot use moves the candidate generator never proposes, such as bypasses, roundabouts and motorways.
- **Compute.** Measured 2026-10-29 on the team laptop (i7-13620H, 10 parallel Release hosts, prototype planner, games of about 600 s): about 1,100–1,450 games per hour, varying about ±30% with machine load; more than 10 hosts was slower. Budget about 1,100 games per hour. Each game costs one host round trip per simulated second, and wall time grows faster than game length: 700–900 s games took about 30–50 s each (roughly 700–1,000 games per hour), and alone a 410 s game took 6 s against 20–30 s for 780 s. Waiting in 20-tick instead of 100-tick steps costs only about 7%. So the racing loop (64 × 4 + 16 × 12 = 448 games plus validation) costs about 0.4 h per generation at hand-rule game lengths: about 20 generations per night, not 40, and fewer as evolved agents survive longer. To reach 30 or more, cut racing to 4 seeds + top-16 × 4 (about 330 games per generation) or use population 48 with 4 + top-12 × 8 (about 290). Consider capping game length (e.g. 1,200 s) during training only. Keep population sizes modest or use a machine with more CPU cores. A GPU does not help.
- **Periodic slow steps.** About every 20 simulated seconds (per-shop timeout and every building spawn, CityDemand.cs:29, 178), `RefreshFeasibility` runs an uncached terrain Dijkstra for every same-colour house × shop × entrance. Its cost grows superlinearly with buildings: under 100 ms up to about 30 buildings, about 700–1,000 ms at 44–53 buildings (t ≈ 650–820 s) with a host running alone, and about 1.2–1.3 s with 5 hosts in parallel. Long-surviving agents pay most of it. Caching by building set, roundabouts and entrances should keep behaviour unchanged (the route ignores roads; in OriginalReference the result only orders house spawns and appears in `feasibleDemandInterval`), but it changes shared simulator code, so it needs team agreement and a check that replay recordings and observations stay byte-identical.
- **Evolution may only match the hand rule.** The CMA-ES and hand-rule rows make this visible. That would be a legitimate finding.
- **Overfitting to the training pool.** Mitigated by seed rotation, a validation hall of fame and untouched test seeds.
- **Novelty is moderate.** GP-evolved priority rules are established in job-shop scheduling, and a hand-tuned Mini Motorways planner exists (EminnM's "B+" on GitHub). What is new is evolving the policy for this game and testing transfer across seeds and cities. Claim only that. Mohammad's newer planner-aided PPO also separates hand-written mechanics from a learned choice among candidates, so that separation is not new within this project; restate the claim once decision 15 is settled.
- **The 1,000-trip target is unproven** for any method. Estimate a ceiling from car supply against the demand ramp before promising a number.
- **OPEN: `OriginalDemandInterval`.** Decide whether the agent may read a shop's current demand interval, and document the choice. Facts (verified 2026-10-29): it is the shop's exact current seconds per pin, 20 / (1.55 × 0.8 × (upgraded ? 2 : 1) × oscillation × ramp) (CityDemand.cs:157-170); 0 for houses and for shops in the reset response. The oscillation depends on a hidden per-colour phase drawn from the RNG (CityDemand.cs:163), so one or two readings plus the map constants in CityCatalog.cs make that colour's whole future demand-rate curve predictable. It reveals no spawns or upgrades (`plannedDemandMultiplier` is 1.0 in all five cities). Mohammad's agent does not read it. **PROPOSED default until decided:** exclude it, so the exclusion list matches Mohammad's, and estimate the demand-rate terminal from increases in `demand` over a sliding window (those stop while a shop is at capacity + overflow). An exact-rate variant can be an ablation, labelled as using an extra field. Phase 1 does not need it.
- **OPEN: whether to compare against the Custom rule set** at all, or stay on OriginalReference only.

## 10. Proposed folder layout

```text
evolved_rules/
  PLAN.md          this file
  host.py          JSON host client (Release build, timeouts)
  state.py         parser, road graph, components
  candidates.py    A* routes, removals, offers
  executor.py      draw strokes, verification, replay logging
  agent.py         event loop: candidates -> rules -> executor
  rules.py         GP primitive set, terminals, hand-written rule
  evolve.py        DEAP loop, racing, hall of fame
  tune_cmaes.py    CMA-ES control
  evaluate.py      test-seed runs, summary.json, statistics
  tests/           parser, A* link rules, executor, replay checks
```

Generated runs, checkpoints and replays go in `output/evolved_rules/` at the repository root. `.gitignore` already ignores the root `/output/` folder, but an `evolved_rules/output/` folder would not be ignored (checked with `git check-ignore`). `*.log`, `*.dll` and `*.exe` are ignored everywhere, so don't give files that should be committed those names. The replay verifier is built from a `git archive` copy outside the repo (section 6); if the team prefers it in-repo, a small evolved_rules-owned `.csproj` compiling `../simulation/Assets/Simulation/*.cs` avoids touching shared code.
