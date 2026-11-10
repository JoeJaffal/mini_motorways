# Original free-play city growth (`fidelity-aya-growth`, 11 November 2026)

Simulator `2026-11-11.g1`, branch `fidelity-aya-growth` (from `fidelity-aya` at f7). Decisions
[085–088](../../../simulation/Docs/DESIGN_DECISIONS.md) give the evidence and choices; this page keeps the
measurements. Linked from the [fidelity-aya report](../fidelity-aya-2026-11-10/README.md).

## What changed (OriginalReference free play only)

Recorded replays force building spawns and disable growth, so this work affects free play, which is what the
learning agents play. Custom is unchanged.

| Item | Before (f7) | Now (g1) |
| --- | --- | --- |
| House placement | random tile of the colour's house zone, first that fits | colour's house weight layer per tile × building influence (Near/Far grouping, suburb curves) × density blur; dead zones around lots and roundabouts; one random draw per placement, highest draw wins if a path away exists |
| House driveway | pointed at the destination that triggered the house | any of N/E/S/W, each its own placement |
| Destination placement | random zone tile, random layout | colour's destination layer over the whole footprint × Near/Far over radius 12; own-colour lots halve weights ring by ring to radius 5; dead zone around houses and lots; no shared driveway tile |
| Edges | playable maximum column and top row excluded; no inset | both edges playable; placement one tile inside |
| Supporting house | every new destination spawned a house or was discarded | houses only from the supply test (one pending per colour, ≥ 10 s apart) |
| Lot spacing | none | 10 s between new lots (joins exempt) |
| Double lots | rolled at every retry; any vacant lot; four orientations; solo only after 10 attempts | rolled once; only the first vacant lot, not for the same colour; two orientations; solo for good after five failures |
| Failed circles | retried forever | become a destination after more than five failures |
| Weight relaxation | none | tiles outside the layer allowed at weight 0 after five failures |
| Supply distance | to the entrance tile inside the lot | to the tile outside the driveway |

Data: [scripts/export_placement_data.py](../../../scripts/export_placement_data.py) writes
`simulation/Assets/Simulation/OriginalPlacementData.cs` (numbers only) from the installed city bundles.

## Free-play statistics

[FreePlay.cs](source/FreePlay.cs) (compiles the simulator source; `--dump <map> <seed> <t>` prints a map)
runs Los Angeles and London, seeds 1–5, OriginalReference rules, no roads, failure timer disabled
(growth does not depend on roads). Means over the five seeds (range); "touching" counts houses inside a
lot's one-tile ring. Raw: [f7](measurements/freeplay-f7.txt), [g1](measurements/freeplay-g1.txt),
[summarise.py](source/summarise.py).

| Map, time | Version | Houses | Destinations | Lots | Upgraded | Mean house → nearest own destination (tiles) | Touching |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Los Angeles, 600 s | f7 | 15.8 (14–17) | 7.4 (7–8) | 7.4 | 0.2 | 6.62 (5.12–8.97) | 4.2 |
| | g1 | 16.2 (15–17) | 7.6 (7–8) | 7.6 | 0.2 | 8.43 (7.10–10.15) | 0 |
| Los Angeles, 1200 s | f7 | 44.4 (39–50) | 11.0 (10–12) | 10.2 | 2.2 | 9.36 (6.91–10.66) | 8.6 |
| | g1 | 50.0 (43–53) | 11.4 (10–13) | 11.0 | 3.0 | 10.74 (8.60–13.35) | 0 |
| London, 600 s | f7 | 15.2 (13–18) | 8.0 (8–8) | 6.4 | 0.6 | 7.69 (6.58–10.78) | 1.2 |
| | g1 | 15.8 (14–17) | 8.6 (8–9) | 7.2 | 0.0 | 8.32 (7.41–10.72) | 0 |
| London, 1200 s | f7 | 34.0 (31–37) | 13.0 (13–13) | 9.4 | 1.4 | 8.38 (7.57–10.12) | 4.2 |
| | g1 | 37.8 (36–40) | 14.2 (14–15) | 11.4 | 0.8 | 8.62 (7.75–10.84) | 0 |

Reading: houses now keep clear of lots and sit further from their own destinations (the original pushes a
house away from its own destinations by 0.425^(7−d)). Each house is worth slightly less supply (further away,
measured from outside the driveway), so more houses spawn. More lots stay separate because a double entry
no longer joins a lot of its own colour; failed circles now become destinations.

## Other checks on g1

- Self-test: 92 suites pass (85 + 7 placement suites; no existing assertion changed).
- `scripts/verify_five_maps.py` (10 runs) and `scripts/check_training_readiness.py` (60 episodes, exact
  replays on all five maps) pass; reports regenerated in `simulation/Reports/`.
- Replay v21 (growth disabled) is bit-identical to f7: `--run-scenario` default run COMPLETED with 353 of 400
  events, 663 trips, game over at 1214.8 s (the same as f7); on the [fixed-phase bench](../fidelity-aya-2026-11-10/README.md#why-the-demand-phases-matter)
  16-phase mean 777.8 (726–819), 8/16 reach the end, fitted phases 799 at 1307 s with 400 of 400 events
  ([data](measurements/bench-g1.txt)), identical to f7.

## Limits

- Our RNG stream is not aligned with the original's, so placements are statistically, not individually, comparable.
- The path-away A* matches the original's costs, heuristic and 300-iteration cap; open-list tie-breaking may differ.
- The first house appears at reset (time 0) instead of after the first tick.
- Failed spawns retry at now + delay (the original adds the delay to the entry time).
- Stations now use the exported station layer and the same dead zones; train-station placement was not compared with the original beyond that.
