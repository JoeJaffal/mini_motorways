# Simulation versions - 24 October 2026

One executable and one shared traffic core, with two independently created rule sets. The default is OriginalReference. Selecting another version resets the episode; it does not mutate the rules of an ongoing run.

**OriginalReference is under construction. It is not an exact replica and must not be reported as an exact-original training baseline.** A reset with requireExact=true explicitly refuses to claim parity.

| Rule | OriginalReference (default) | Custom |
|---|---|---|
| Goal | Match the installed original | Keep the city running first; lower waiting and lower cost are secondary |
| Construction | Limited material stock | Unlimited items; permanent cumulative spending |
| Prices | No custom point prices | Road 2; light 5 additional; bridge water tile 10; roundabout 8 |
| Motorways | Required for parity; not implemented yet | Excluded |
| Weekly materials | City-configured package choices, partial port | No grants or inventory limit |
| Demolition | Retire, let committed traffic clear, return released materials | Same clearing approach; never refund past spending |
| New-shop grace | No custom 30-second grace | 30 seconds |
| Demand governor | Off | Off: infeasible scenarios are rejected, not given easier demand |
| Intersections / roundabouts | Original target | Original target |
| Run options | Same map with varied events, or different maps with varied events | Both options |
| Available city data | Los Angeles, Beijing, Tokyo; each currently a 50 x 30 crop | Same |
| Learning method / color penalty | Outside this task | Outside this task; no algorithm or penalty implemented |

Custom demand is left at original-style rates. After each shop's 30-second grace, the optimistic supply-bound screen checks supply. A failing screen rejects the run: scenarioRejected=true, terminated=false, truncated=true, with a reason. The run stops and must be reset. Discard a rejected run rather than treating it as an agent failure. There is no automatic retry loop or silent demand reduction.

The screen uses a generous speed/distance bound and allows potential future houses in growing cities; it avoids rejecting a city merely because houses have not spawned yet. It is not a complete proof of joint network schedulability and may miss impossible scenarios. The original-style gradual household placement remains approximate; rejection does not trigger extra corrective house spawns.

The two secondary objectives are not assigned invented weights or an order relative to each other. Raw time, waiting, spending and trips remain available. RL/evolution and color-network penalties are out of scope, per the user's latest answers. Existing raw connectivity diagnostics are not a reward.

## Original-game evidence applied this update

Read-only inspection of installed App.dll added UpgradeType, UpgradeDatabase, UpgradeDatabaseModel and UpgradeAwardingProcess to the existing research. CityDefinition startingPackages and weeklyChoicePackages were read from the installed losangeles, beijing and tokyo bundles. Numeric terrain, spawn zones, oscillation data and schedules were exported independently into CityCatalog.cs; original code/art was not bundled.

MaterialInventory.cs now applies city starting stocks, road exhaustion/reuse, bridge-span reservations, light/ring inventory, and weekly package selection. Weekly package amounts, initial weights, starting/last week and package caps come from city data. Original weight adjustments, deterministic random sequence, edit accounting and bridge geometry are not completely ported. These are partial reference implementations, not proof of original parity.

## Exact-original parity work still required

1. Motorways: construction, routing, lanes, speeds, editing and inventory.
2. Destination upgrades, complete shop/carpark layouts and orientation rules.
3. Full city bounds and camera/map expansion rather than fixed crops.
4. Exact spawn scheduler, placement, support-house logic, and all city-specific progression modifiers.
5. Original upgrade weighting/history and original random/fixed-point behavior.
6. Exact bridge approach/span validation and edit resource accounting, including roundabout conversions.
7. Exact lane templates, conflict/commit rules, rerouting and queue behavior.
8. Controlled side-by-side original-game traces and regression comparisons. Current self-tests establish internal consistency only.

This list is implementation work and requires no further design answers from the user. Until it is resolved, train on the installed original through a suitable future adapter, or explicitly label experiments as reconstruction experiments. No adapter to train against the installed game has been implemented.

## Current controls and protocol

Viewer: Original target / Your version; map selection; same-map/different-map runs; New run changes the seed. Original target is the default. --custom launches directly into the user's version.

Headless example:

```json
{"command":"reset","version":"Custom","scenario":"LosAngeles","variation":"SameMap","seed":42}
{"command":"reset","version":"Custom","scenario":"LosAngeles","variation":"DifferentMaps","seed":43}
{"command":"reset","version":"OriginalReference","scenario":"Tokyo","seed":42}
{"command":"upgrade","choice":0}
```

Version, actual selected map, seed-repeatable variation, current costs, grace, inventory, pending upgrade choices, rejection status, objective and fidelity status are exposed in observations. exactReplicaValidated is false. requireExact=true rejects resets until parity is actually established.
