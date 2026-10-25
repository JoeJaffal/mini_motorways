# Headless simulation

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

Build places a tile; adjacency alone does not connect tiles. Draw builds and connects a stroke, which may partially succeed. Responses include `accepted`, `message`, trip/spending deltas, `terminated`, `truncated` and `observation`. Invalid requests return `error`.

Observations contain detached destination, vehicle, motorway, train, rail and crossing data, plus costs, inventory and fidelity status. Station/shared-lot metadata includes shared occupancy identity, entrance arrays and platform cells. A rejected Custom scenario sets `truncated=true`; ordinary overcrowding failure sets `terminated=true`. Bounded evaluation tools report duration truncation separately. Discard rejected runs rather than treating them as a policy failure. No scalar reward is invented.

`ReferenceLab` and `EmptyLab` are diagnostic scenarios, not additional selectable city maps. `requireExact:true` rejects reset requests while exact parity is unverified.
