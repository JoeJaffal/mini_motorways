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
