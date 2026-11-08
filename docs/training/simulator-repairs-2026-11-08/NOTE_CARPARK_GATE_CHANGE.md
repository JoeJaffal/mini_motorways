# Note for Mohammad: carpark gate change — 8 November 2026

From Aya's session. Thank you for the [space-check answer](ORIGINAL_SPACE_CHECK_RULE_ANSWER.md); it
is implemented as described (simulator `2026-11-08.3`, report section 8). This note covers a
follow-up change to your carpark approach gate (simulator `2026-11-08.4`). If you see a better way,
please tell us and we will change it.

## The problem

With the original junction arbitration in place, the replays stopped deadlocking at junctions. The
next lock was at your approach gate, at shared lot 20 (16,16), gate 19,18, from about t = 973 in v20:

- car 34, passing *through* the lot, was first on the outside approach `20:18:2:4`;
- the gate was owned by car 10, which was going to park and was queued *behind* car 34;
- neither could move.

The cause: an arriving car is gated and ranked at the **start of its outside approach lane**,
your rule from the 74-suite repair, so it never traps a departing car. A car passing through is
gated and ranked at the **entrance connector itself**. The two kinds of car were measured to different
points, so the car behind looked nearer.

## What we changed

1. **One reference point for both kinds of car.** A car passing through a shared lot is now gated at
   the start of the outside road lane that leads into the entrance connector, the same point you
   use for arriving cars. This applies to ranking, to where it stops and to how long it holds the
   gate. Arriving and departing cars are handled exactly as before.
2. **Cycle recovery can see the gate.** A gate refusal now names the owning car, so the original's
   blocking-cycle "shove" can break a cycle that runs through a gate. A shoving car may pass the gate
   for its immediate next lane.

**Why this way.** Your answer says the original orders entry candidates by one distance measure
(distance to the chosen lane), with no carpark exemption visible. We have not removed the gate,
because it fixes real carpark deadlocks and several tests depend on it. We only made it measure
every car the same way, at the point you chose.

**Tried and dropped:**

- Ranking every car by its distance to the entrance itself. Arriving cars then lost the gate more
  often, the queue backed into the hub junction, and ParkingFlow failed with a body overlap.
- Ranking through-cars at the approach start while still stopping them at the connector. A through-car
  then drove up to the entrance and trapped the departing gate owner.

## Evidence

- **New regression:** a reconstruction of the v20 lock at t = 972. It fails on `2026-11-08.3` and
  passes on `2026-11-08.4`; the ranking part alone already fixes it.
- **Checks:** 82 core suites (including shared transit and ParkingFlow), environment, reward and
  five-map checks pass.
- **Replays** (partial diagnostics, not a comparison with 835;
  [results](measurements/carpark-gate-results.json)):
  - v20: 620 trips, game over at 1206.4 s from ordinary overcrowding, no car waiting over 20 s at
    the end.
  - v21: 537 trips, game over at 1147.15 s.

## Questions

1. **Carpark entrances in the original.** Do cars entering or leaving a carpark go through the same
   chunk arbitration (inbound registration, eligibility, distance and timestamp ordering), or is
   there a separate carpark rule? If they use the chunk arbitration, we would replace the gate with
   it rather than keep our gate.
2. **A traffic light that never changes (new finding, not changed).** In v21 the light at 20,13 stays
   on one phase from about t = 1080. The only green-phase car within 0.5 tiles is stopped by the
   shared-exit space rule. Our switching rule changes phase only when 0 or at least
   `SignalMinimumNearbyCars` (3) green-phase cars are nearby, so with 1 stuck car it never switches,
   and the red side waits about 90 s until game over. How does the original decide to switch when
   green-phase cars cannot move? Are the nearby count and the minimum of 3 original values?
3. **Anything else** in this change you would do differently.

Please mark anything not visible in the extracts as uncertain; we will not guess it.
