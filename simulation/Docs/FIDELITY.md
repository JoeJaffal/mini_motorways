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
