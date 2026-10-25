# Behavioral fidelity

The current implementation and approximation register is in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md). That file supersedes the earlier baseline description: the project now has lane paths, acceleration and following, adaptive signals, directed roundabouts, functional parking, gradual growth and a Los Angeles terrain profile.

The target remains the observable behavior of the user's installed Mini Motorways, within the agreed road-and-car scope. Recovered constants and code structure are evidence, but passing our own tests does not prove exact parity.

## Next reference comparisons

1. Isolated house/shop: departure time, full round-trip time and score timing.
2. Straight queue: stopped spacing, acceleration and discharge rate.
3. T and four-way junctions: priority, simultaneous compatible turns and stalled queues.
4. Signals: phase selection, amber, blocked exits and driveway interactions.
5. Roundabouts: geometric lanes, entry queues and exit behavior.
6. Parking saturation: ingress/egress, full-bay arrivals and early release.
7. Road deletion: rerouting point and final release of retired lanes.
8. Growing city: placements, demand and failure/recovery over several weeks.

Record the installed build, scenario, speed, timestamps and observed results for each comparison. Change this register when evidence supports a narrower or stronger fidelity claim. Original intersection and roundabout rules are selected for both versions. Lebanese legal modes are not part of this task.

## Additional comparisons required for the five-map scope

- Motorway entry/exit, speed profiles, merging, endpoint orientation, replacement while occupied and final stock release.
- City expansion, start-offset selection and deterministic spawn schedules on LA, Beijing, Tokyo, Dar es Salaam and London.
- Destination upgrades and complete parking layouts.
- London station demand, train movement and rail-crossing closures.

The new numeric profile export, motorway implementation, city demand ramps and shared per-color oscillation phases are implementation progress. No side-by-side original-game traces certify them yet.

## Component oracle - 25 October 2026

The middle-square Weyl stream matches 180 values obtained by directly invoking the installed PseudorandomGenerator (five seeds; signed integers, bounded integers and fixed-point fractions). Numeric vectors and the source assembly hash are saved in `Reports/reference-random-vectors.json`; `scripts/ReferenceProbe` reproduces them without modifying or bundling game files.

This isolated match is stronger evidence than internal determinism tests, but it is not an end-to-end spawn comparison. Complete seed initialization, draw ordering, placement weights, arithmetic and process order remain unverified. Single/shared-lot checks establish internal behavior and recovered numeric rules; exact parking traces still need comparison.

The installed rail topology component also matches all 53 ordered London cells, loop status and origin index. Numeric results are in `Reports/reference-london-rail.json`. Trains, stations, batch demand, two-color shared car parks and crossing closures are now functional. Integration checks include cars waiting at a closed crossing and resuming after release. Spline geometry, station placement and movement/demand timing remain unverified against original runs. A live full-game recorder/importer is still missing.

## Live exploratory comparison — 25 October 2026

London Classic was launched and inspected directly through the Windows computer-use skill. The comparison exposed and corrected a station presentation bug: buildings overlapped rail and the lot background hid the track. The updated app was inspected again with visible rail, reserved destination outline and approaching train. See `Reports/live-london-observations.md` for the observations and input limitations; no successful original driving trace was measured.

The original game produced an autosave journal. A private local copy was preserved outside the repository. The sanitized envelope report confirms London Classic at 39.9 simulated seconds, zero trips and 573 serialized objects. `scripts/inspect_reference_journal.py` checks the supported header schema and envelope boundaries and omits device details. Decoding the full simulation graph and collecting synchronized successive states remain unfinished.

## Video comparison and parking update

LA and London Classic footage was inspected through YouTube, then checked against the installed numeric parking geometry and lifecycle rules. Original now has internal outer/inner circulation lanes, diagonal bay midpoint stops, full-lot drive-through paths and earlier bay release. The 31 shared suites include geometry and lifecycle regressions. A rendered LA run completed four trips with the new paths. `Reports/parking-reference-update.md` records video links/timestamps and the remaining entrance-boundary, concurrency and timing approximations. This is structural comparison and implementation progress, not a synchronized original-game trace match.
