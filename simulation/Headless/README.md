# Headless simulation

`{"command":"drawchoices","x":6,"y":5}` returns a lightweight read-only
`possibleChanges` array of 1,500 booleans. False proves the ordinary stroke
cannot physically change roads, connections or a driveway; true is only
conservative possibility, not a suggested/valid route. It never steps the world
or changes LastAction. Ordinary responses now include topology `networkVersion`
to invalidate agent-side caches, along with current resources and bounds.
This endpoint supports an optional agent mask; game construction rules are unchanged.

Training may opt into a read-only diagnostic by sending
`"includeConnectivity":true` on reset. Reset/step/observe responses then include
top-level `usefulConnectedHouses`: houses with a current legal same-color
destination route and return route, counted once each. It uses ordinary routing,
excludes retiring links, and does not build or step anything. Other responses
and disabled sessions return null. This diagnostic is not added to the policy's
observation channels. See the [shaping contract](../../training/REWARD_SHAPING.md).

See [the simulation guide](../README.md#headless) and [version behavior](../Docs/VERSIONS.md).

Run `dotnet run --project simulation/Headless -- --self-test` from the repository root. Both versions compile the same C# core as the Unity viewer. OriginalReference is unfinished and is not an exact-original training baseline.

Run `dotnet run --project simulation/Headless -- --evaluate-crossings` for the four seeded diagnostic networks described in [the traffic and scale investigation](../Reports/traffic-and-scale-investigation.md). It replenishes road stock and extends the failure timer deliberately; its trip counts are not normal-play benchmarks.

## Original motorways and five maps

Reset scenarios: LosAngeles, Beijing, Tokyo, DarEsSalaam, London.

- `{"command":"motorway","x":20,"y":12,"toX":30,"toY":12}` creates a motorway, subject to playable bounds, endpoint rules and stock.
- `{"command":"editMotorway","id":0,"x":20,"y":12,"toX":31,"toY":12}` replaces an active motorway while preserving committed old paths.
- `{"command":"removeMotorway","id":0}` retires it and releases stock after clearing.

Observations include `motorways` and `playableXMin`/`playableYMin`/`playableXMax`/`playableYMax` in canvas coordinates. Connecting surface roads remains a separate operation. Original replica validation remains false.

After building this host, run `python scripts/verify_five_maps.py` from the repository root for the five-map protocol smoke checks.

## Request reference

The host reads one JSON object per input line and emits one response per request. `quit` exits. Coordinates use the 50 x 30 canvas. Default version is OriginalReference; pass `version` explicitly when comparing experiments.

| Command | Fields |
| --- | --- |
| `reset` | `version`, `scenario`, `seed`, `variation` (`SameMap` or `DifferentMaps`) |
| `build` | `tool` (`Road`, `Bridge`, `Roundabout`, `TrafficLight`, `Remove`), `x`, `y` |
| `connect` / `draw` | `x`, `y`, `toX`, `toY` |
| `driveway` | House `id`; direction vector from `x`, `y` toward `toX`, `toY` |
| `motorway` / `editMotorway` | Endpoints as above; `id` for edits |
| `removeMotorway` | `id` |
| `upgrade` | `choice` index from the current offers |
| `step` | `ticks` from 0 through 100000 |
| `observe` | No additional fields |
| `reference` | Debug road construction; may exhaust Original stock |

```json
{"command":"reset","version":"OriginalReference","scenario":"London","seed":42}
{"command":"reference"}
{"command":"step","ticks":200}
{"command":"observe"}
{"command":"quit"}
```

Every reply, including errors and `drawchoices`, carries `simulatorVersion` (for example
`"2026-11-08.6"`); `TrafficHost --version` prints the same string, and `--run-scenario` and
`--verify-replay` summaries include it. Key cached results on it: it changes whenever gameplay,
scoring or observation meaning changes ([version table](../Docs/VERSIONS.md#simulator-version-string)).
Hosts built before 8 November 2026 do not send it. The field is additive; no existing field changed.

Vehicle `waiting` is the car's current continuous wait in seconds (speed below 0.02 tiles/s, not
counting time in a bay). It resets when the car moves, and, since `2026-11-08.1`, on arrival home or in
a bay. Observation `meanWaiting` is different: the mean, over every car ever spawned (including cars
that never left home), of each car's cumulative waiting seconds. It only grows and is not a
current-queue measure.

Build places a tile; adjacency alone does not connect tiles. Draw builds and connects a stroke, which may partially succeed. Responses include `accepted`, `message`, trip/spending deltas, `terminated`, `truncated` and `observation`. Invalid requests return `error`.

Observations contain detached destination, vehicle, motorway, train, rail and crossing data, plus costs, inventory and fidelity status. Station/shared-lot metadata includes shared occupancy identity, entrance arrays and platform cells. A rejected Custom scenario sets `truncated=true`; ordinary overcrowding failure sets `terminated=true`. Bounded evaluation tools report duration truncation separately. Discard rejected runs rather than treating them as a policy failure. No scalar reward is invented.

`ReferenceLab` and `EmptyLab` are diagnostic scenarios, not additional selectable city maps. `requireExact:true` rejects reset requests while exact parity is unverified.
