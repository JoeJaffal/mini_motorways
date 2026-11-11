# Original and Custom specification — 25 October 2026

Two separate executables use one shared simulation core. Original's scene fixes `OriginalReference`; Custom's scene fixes `Custom`. Neither viewer offers a version selector or honors a version-switching flag. The headless development host explicitly supports both.

Original is a reconstruction under validation, not a certified exact replica. See [current implementation status](IMPLEMENTATION_STATUS.md), [fidelity evidence](FIDELITY.md) and [scoped reports](../Reports/README.md).

## Rule sets

| Rule | OriginalReference | Custom |
| --- | --- | --- |
| Objective | Reproduce installed standard play | Survival first; less waiting and spending secondary |
| Cities | LA, Beijing, Tokyo, Dar es Salaam, London | Same five city profiles |
| Working area | 50 x 30 data canvas with recovered playable expansion bounds | Fixed working area |
| Construction | Finite city-configured stock | Unlimited items with cumulative spending |
| Point prices | Custom prices disabled | Road 2, light 5 additional, bridge water tile 10, roundabout 8 |
| Weekly materials | City-configured packages; weighting/history partial | No grants or material limit |
| Demolition | Retire, clear committed traffic, release materials | Same clearing approach; never refund spending |
| Motorways | Functional links, two-way lanes, stock, retirement and editing | Excluded |
| New-destination grace | No custom 30-second grace | 30 seconds |
| Feasibility rejection | Custom rejection disabled | Optimistic supply screen; demand is not lowered to rescue a scenario |
| Destinations | Upgrades, three-bay singles, shared nine-bay lots and stations | One size and six bays |
| London trains | Functional motion, station demand and crossing signals | No train simulation |
| Parking | Internal circulation, diagonal bays, drive-through and early bay release | Simpler existing paths |
| Driving | Original-style automatic behavior, still approximate | Same shared original-style driving target |
| Run variation | Same city or varied cities, seeded events | Both options |
| Learning/reward | No learner or scalar reward implemented | No learner, chosen reward weights or color-separation penalty |

Each house has two reusable cars. Matching colors determine destinations; cars return home before another dispatch. Trip score, waiting, survival time and spending remain separate metrics. No budget, demolition fee, variable fleet or redesigned legal driving mode has been added.

## Materials and motorways

Original reads starting stocks and weekly package metadata from the five numeric city profiles. Custom has no resource inventory limits. A motorway uses one motorway slot, with no road tiles for its span; surface connections are separate construction.

Editing a motorway preserves committed old paths while transferring the occupied slot to the replacement. Retirement stops new assignments and releases stock after clearing. Exact ramp/endpoint geometry, merge priority, release timing, bridge accounting and package weighting/history remain unverified.

## Destinations, parking and rail

Circle schedule events select eligible existing destinations with age weighting. Upgrades wait until at least ten seconds after activation, double base demand and raise capacity from six to nine. Single lots retain three bays and four entrance layouts.

Shared lots support two colors, nine shared occupancy slots, two entrances and four orientations. Original parking uses separate circulation and bay branches, diagonal midpoint stops/headings, drive-through paths when full and bay release after leaving the parking segment. The user accepted the current center-based entrance connections and conservative access serialization for now. Exact concurrent behavior and exit selection remain differences.

London uses recovered rail topology, train origin, station-demand zones and tuning. Stations use four rail cells along one edge, do not accumulate ordinary timer demand, and receive bounded batches from train visits. Trains accelerate, brake, wait at stations and close/release crossings. Motion/placement/timing and fixed-point spline behavior are not certified against original traces. Tunnels are not implemented.

## Variation, rejection and endings

New run changes the seed; Reset city repeats settings and seed. `SameMap` preserves the selected city; `DifferentMaps` selects among the five supported maps. Determinism within a reconstruction version does not imply identical event histories between versions or with the original.

After the 30-second grace, Custom's optimistic screen may reject clear supply shortages, allowing future households in growing cities. Rejection stops the run with `scenarioRejected=true`, `terminated=false`, `truncated=true` and a reason. Discard rejected scenarios. There is no automatic retry loop or demand reduction. The screen does not prove full network feasibility.

Normal game failure is destination overcrowding. Bounded evaluation has a separate duration limit; that is truncation, not a game rule.

## Protocol and evidence

See [the headless guide](../Headless/README.md) for commands. Observations include version, chosen map, inventory, costs, destinations, vehicles, motorways, rail, crossings and pending upgrades. `exactReplicaValidated` stays false. Requests with `requireExact:true` fail until parity is established.

The RNG matches 180 installed-component values; London rail ordering, loop and origin match the installed topology component. Read-only live observation, selected footage and a sanitized journal-envelope report supply additional structural evidence. No original driving trace was successfully measured through the UI tool, and the journal's full simulation graph is still undecoded. Component matches and 31 internal suites do not certify full-game equivalence.

The remaining work is summarized in [implementation status](IMPLEMENTATION_STATUS.md). The chronological [design decision log](DESIGN_DECISIONS.md) preserves actual user choices; this current specification supersedes earlier provisional descriptions.

## Simulator version string

`SimulatorVersion.Value` (`simulation/Assets/Simulation/SimulatorVersion.cs`) names the gameplay,
scoring and observation semantics of the shared core. The headless host reports it as
`simulatorVersion` on every reply and prints it for `TrafficHost --version`. Bump it, as
`YYYY-MM-DD.N`, with any change that can alter a game, a score or the meaning of an observation field,
and add a row here. Hosts built before 8 November 2026 report no such field; treat its absence as
"pre-versioning" and never reuse those results as current.

| Value | Source | Meaning |
| --- | --- | --- |
| `2026-11-08.1` | `mohammad` after `f7ce005` | 78-suite source: 77-suite rules (native motorway/common-endpoint joins in ordinary play) plus clearing a car's current wait on arrival |
| `2026-11-08.2` | `mohammad`, roundabout deadlock fix | Adds: an approaching car blocked by a stationary vehicle on a conflicting lane no longer holds entry priority (removes the permanent junction/roundabout yield-cycle deadlock found in replay v20) |
| `2026-11-08.3` | `mohammad`, original junction arbitration | Replaces Original junction entry with the original's documented arbitration: lane-count gate, red light, blocking-cycle shove, shared-exit space test without near-exit release, different-exit release, green geometry bypass, committed-candidate eligibility and route-time inbound registration. Custom is unchanged |
| `2026-11-08.4` | `mohammad`, carpark gate | A car passing through a shared lot is gated (ranked, stopped, held) at the start of the outside approach lane, like an arriving car; gate refusals name their owner for blocking-cycle recovery, and a shoving car may pass a gate |
| `2026-11-08.5` | `mohammad`, original traffic lights | Original phase logic: strict 3 s/1 s reconsideration and 0.7 s amber; the 1-2 nearby-car guard counts committed candidates by route distance to the chosen lane and stops at the first one blocked inside the light's chunk; commitment-age phase weights with the inspected multipliers; amber keeps the old pair's permission; non-crossing turns may go on red; green bypass only for permitted directions. Custom is unchanged |
| `2026-11-08.6` | `mohammad`, carpark chunk arbitration | Carpark lanes are arbitrated as the original's chunks (entrance ends, outer/inner circulation per bay, bays) and registered as inbound lanes; the engineered approach gate stays on because our entrance geometry still needs it |
| `2026-11-08.7` | `mohammad`, carpark gate and red lights | A car held by a red light before its gate lane may not take or keep the engineered carpark gate; the light is checked before the gate |
| `2026-11-10.f1` | `fidelity-aya`, first pin | Every new destination starts its first-pin timer at 4 s (the original's `DelayBeforeFirstPinOfDestination`); previously later destinations waited a full demand interval. `.fN` values belong to the `fidelity-aya` branch so they never collide with `mohammad`'s `.N` |
| `2026-11-10.f2` | `fidelity-aya`, original carparks and continuous trips | OriginalReference trips are one continuous path: the outbound path ends on the carpark entrance lane, the bay (or drive-through) and in-lot lanes are attached on the lane before it, and a car leaving its bay gets one path home, so no car stops at a leg boundary. Removed the engineered carpark gate, the whole-lot bay-departure check and the body-clearance step limiter (none exist in the original). Lanes sharing an exit now block a merging entry after the space test, as the original's connection test does |
| `2026-11-10.f3` | `fidelity-aya`, carpark lane speeds | OriginalReference carpark lanes use the original's lane-speed rule (turn factor 1 / 1/3, times 0.5 where the lane leads to more than one lane) instead of a flat 0.6 of road speed |
| `2026-11-10.f4` | `fidelity-aya`, original movement rules | OriginalReference: intersection factor 0.5 on the approach lane (next tile offers 2+ ways, not signal/roundabout) instead of inside the junction; roundabout speed only on ring-to-ring lanes; no turn factor after a motorway; maximum acceleration chosen from the current or next chunk (roundabout, signal, own driveway, motorway end) and doubled when blocked at a signal within two car lengths; slowdown toward uncontrolled junctions with 3+ real roads (virtual leader at 0.55 of desired speed, exponent 1.6); junction stop offset as the original |
| `2026-11-10.f5` | `fidelity-aya`, 45 s escape and arrival timing | OriginalReference: a car committed to a chunk lane for more than 45 s enters (installed feature MaximumWaitTimeAtIntersections); arrival (pin, score, overcrowd credit, 3 s timer) happens on entering the bay lane; a returning car is dispatchable on entering its house tile lane; a full lot evicts only while a car is on its way (dispatched pins) |
| `2026-11-10.f6` | `fidelity-aya`, pin relocation and failure timer | OriginalReference: a pin that would exceed a full destination moves to the nearest same-colour destination with room, else the nearest of any colour; the overcrowd timer runs after vehicles each tick as the original FailureStateProcess (arrivals banked and applied on an overcrowded frame; game over tests the timer before the update) |
| `2026-11-10.f7` | `fidelity-aya`, U-turns and dispatch details | OriginalReference: routes reverse only on dead-end tiles (no 500 penalty elsewhere, no reversal at all), re-routes keep the car's heading; the last destination in dispatch order sends ceil(n/2) cars per tick; the house-choice cost excludes the driveway step |
| `2026-11-10.f8` | `fidelity-aya`, original lane-conflict test | OriginalReference road lanes conflict by the original's direction rule (same exit yes, same entry no, reversal no, half-turn rotation yes, else one-endpoint crossing test) instead of sample geometry; crossing in front of a stopped candidate is allowed in the priority order; re-routing cars pay 100000 for a retired motorway |
| `2026-11-10.f9` | `fidelity-aya`, roundabout commitment and boost | OriginalReference: a circulating car is committed to a ring tile's lane only from the previous ring tile (the original's corner chunks between ring tiles); roundabouts count as controlled for the blocked-within-two-lengths acceleration boost |
| `2026-11-10.f10` | `fidelity-aya`, original motorway end tiles | OriginalReference: the motorway start tile keeps an ordinary lane to the slot edge facing the other end (arbitrated, turn factor), a straight motorway lane joins the two slot edges, and the end-tile lane runs from its slot edge across the whole tile |
| `2026-11-10.f11` | `fidelity-aya`, signal details and roundabout exits | OriginalReference: signal pairs built starting from North; after amber the current pair is kept while cars are inbound and no other pair has weight; when edits remove the active pair the light switches at once (no amber) to the best-weighted pair and restarts its timer; roundabout exit lanes take the 0.5 approach factor |
| `2026-11-11.g1` | `fidelity-aya-growth`, original free-play placement | OriginalReference free play only (Custom and recorded replays unchanged): houses and destinations are placed from the colour's exported per-tile weight layers, scaled by nearby buildings (Near/Far grouping, suburb curves, density blur, dead zones around lots, houses and roundabouts) with one random draw per placement and a path-away test; house driveways may face any of four directions; placement stays one tile inside the playable area, whose maximum column and top row are now playable (stored maximum bounds stay exclusive, so `playableXMax`/`playableYMin` move by one); destinations no longer bring a house (houses only from the supply test); 10 s between new lots; double-lot roll kept per entry, only the first vacant lot is offered, double entries turn solo after five failures; failing circle entries become destinations; supply distance measured from the tile outside the lot's driveway; pending houses are not listed in `scheduledSpawns`. `.gN` values belong to the `fidelity-aya-growth` branch |
| `2026-11-10.f12` | `fidelity-aya`, merge of `fidelity-aya-growth` | f11 traffic rules plus g1 free-play placement (decisions 089–092) |
| `2026-11-10.f13` | `fidelity-aya`, motorway slots count as roads; circulating cars | OriginalReference: an active motorway's slot counts as a road connection on its end tile (approach-lane 0.5 factor, uncontrolled-junction slowdown count, dead-end U-turn test); a car on a ring tile's exit lane no longer counts as circulating |
| `2026-11-10.f14` | `fidelity-aya`, roundabout placement | OriginalReference: placing a roundabout keeps existing valid exits connected and paid, holds and later refunds only the other footprint links, creates no new links; a link from outside into a ring tile costs 1 concrete |
| `2026-11-10.f15` | `fidelity-aya`, return paths after an erase | OriginalReference: erasing a road connection immediately re-routes the stored way home of cars that used it (when an alternative exists); links from outside into a ring tile can be erased |
| `2026-11-10.f16` | `fidelity-aya`, tile corners | OriginalReference: a diagonal step between ordinary road tiles runs tile lane (ending 0.5 from centre), an unarbitrated corner lane (~0.41 tiles, carrying the intersection factor when the next tile branches), tile lane |
| `2026-11-10.f17` | `fidelity-aya`, bridge crossings | OriginalReference: a stroke starts a bridge crossing (one bridge) only when it goes from land onto a water tile without roads, extends it for free from water already on it, and linking two crossings returns a bridge; a bridge tile left without connections after erases is cleared and the crossing's last tile returns its bridge. The direct bridge-tile tool keeps adjacency grouping |
