# Answer: original junction space, priority and deadlock rules

8 November 2026. Responds to [REQUEST_SPACE_CHECK_RULE.md](REQUEST_SPACE_CHECK_RULE.md). User authorizes this read-only investigation and documentation. Inspected the existing local private extracts of RoadChunkModel, VehicleModel, LaneModel and VehicleMovementProcess, plus the installed SimulationConstantsData numeric asset. No original code reproduced here. [Numeric findings and evidence hashes](measurements/original-space-rule-findings.json). Simulator branch revision reviewed: acdf0ff. No simulator edits or gameplay runs performed.

**Main finding:** the original has conditional shared-exit space checking AND blocking-cycle recovery. It does not implement the proposed unconditional rule “every junction entry requires an empty downstream chunk.” Reproducing only that blanket rule would not reproduce these inspected rules. The available evidence does not establish that adding the space check alone fixes v21.

## 1. What the space check measures

During entry arbitration for a road chunk, inspect vehicles traversing that chunk. If a traversing vehicle and the entering vehicle's chosen lane have the **same output direction**, test whether the **entering vehicle** has space. This is a direction comparison within the arbitrated chunk, not a requirement that the entire next physical tile/chunk be empty. It also applies when both vehicles choose the same lane. The result is cached for this one entry evaluation.

The space calculation starts from the entering vehicle's current obstacle/leader state and follows at most **five vehicle states**, accumulating usable distance:

- No obstacle: return available immediately.
- Target/end of route: add remaining target distance minus one vehicle length, then end the chain.
- Blocking intersection or lane replacement: add distance to that blocking lane, then end the chain.
- Leading vehicle: start with the distance to the leader. If the leader's current lane belongs to the chunk being arbitrated, subtract that lane's remaining distance, retaining a vehicle-length allowance. Then add the nonnegative gap after subtracting a vehicle length, and continue from the leader.

Return available when accumulated usable distance is **strictly greater than two vehicle lengths**. If five states are exhausted, or the chain ends without reaching that threshold, return unavailable. It is an obstacle-chain/gap calculation using distances along routes and lane membership, not a simple Euclidean test or fixed “reserve next tile” rule. Do not substitute the distance from the entering car to the end of its chosen lane for this calculation.

An unavailable result blocks entry because of that shared-exit traversing vehicle. Without such a traversing vehicle, this particular test is not called; other entry rules and following behavior still apply.

## 2. Conditions, order and exceptions

The entry decision has this order in the inspected implementation:

1. Require a registered inbound vehicle and a chosen lane.
2. Apply train-crossing safety/congestion checks, when relevant.
3. A chunk with **two or fewer lanes** accepts at this point. This is lane count, not the number of neighboring road tiles. Do not equate every bend or junction tile with this condition.
4. Reject a traffic-light-blocked direction.
5. Accept a shoving vehicle, but only for its **immediate next planned lane**.
6. Accept after the maximum committed wait, **only if its feature toggle is enabled**.
7. Check traversing vehicles: shared-exit space, release threshold, and geometric conflicts.
8. Compare earlier inbound reservations; allow an entry that has no earlier blocking reservation.

There is no turn-direction-only gate around the shared-exit test. Roundabout chunks use the same entry machinery; a roundabout-specific option can temporarily treat a straight entry as outside the ring. Its installed setting is **off**. If enabled, its boundary is the first **50% of that entrance lane**, with the explicit non-diagonal-input/ordinary-to-roundabout connection conditions. That option also changes whether a traversing vehicle may continue.

The installed `greenLightsIgnoreCollisions` setting is **on**. For a green direction it bypasses the tested geometric collision with traversing lanes, but **does not bypass the shared-exit space test**, which happens first. A red/blocked direction is rejected before shoving or maximum-wait acceptance.

The maximum-wait value is **45 game-clock seconds**, measured from first commitment to the chosen lane, not from the inbound registration timestamp. Runtime enablement of `MaximumWaitTimeAtIntersections` is **unverified**; do not enable a 45s escape solely because the constant exists.

No blanket “motorway/carpark/destination exemption” is visible in this routine. Applicability depends on the actual chunk, lane graph and registered chosen lane. A vehicle with an empty remaining path contributes no traversing obstruction here. Target/end-of-route cases have explicit treatment in the gap calculation rather than an unconditional exemption. The inspected excerpts do not justify separately requiring every parking bay, drive-through segment or motorway lane to pass a new box-clearance test.

Train crossings have additional safeguards, not a general junction rule: closed crossings can deny entry; a tile-corner exception considers whether the crossing is within one vehicle length. For an open crossing, obstructing traffic on/after it can deny entry when its blocker is within three vehicle lengths or the traversing vehicle is stopped. A car already on a closed crossing is handled separately, and mothballed-lane behavior matters. Preserve these as a distinct mechanism.

## 3. Shoving: trigger, effect and end

The movement process records vehicles blocked by intersection entry, including their blocking vehicle. It also records tight leading-vehicle queues when next-frame speed is below the pushing-cycle speed and leader distance is below the minimum gap. It follows blocking-vehicle links and detects an actual cycle; this is **not a generic “wait N seconds, then shove” timer**.

For a detected cycle containing intersection-blocked members, mark those intersection-blocked members as shoving into their next intersection. For a cycle consisting entirely of leading-vehicle obstacles, instead establish a separate pushing relationship to each leader. Do not conflate pushing and shoving, or mark every nearby stopped vehicle as shoving.

Shoving gains priority before roundabout/distance/timestamp ordering and bypasses the later intersection occupancy/space/inbound-reservation arbitration **only for the immediate next lane**. It does not bypass the earlier train or red-light checks. The flag is cleared on moving to a new lane, so it is not a permanent privilege. Separate following/acceleration calculations still exist; this finding is not evidence that an arbitrary body-overlap override is safe or faithful.

## 4. Occupancy and release

Traversing membership is rebuilt from vehicles on the chunk's current lanes. Changing lanes removes the vehicle from the old lane and adds it to the new one. It is not held as traversing merely because some future route once mentioned that chunk.

For traversing-versus-entry conflicts:

- Ignore the entering car itself and traversing vehicles with no remaining path.
- Apply the optional straight-roundabout-entry exception if enabled (off in inspected asset).
- For the **same exit**, perform the space test first. The near-exit release below does not bypass it.
- For a **different exit**, disregard the traversing car once its current-lane distance is **strictly greater than lane length minus one vehicle length**. At equality it still blocks under this test.
- Otherwise apply the connection-intersection geometry, subject to the configured green-light bypass.

Thus the relevant release condition can precede leaving the lane/chunk; it is not universally “wait for the entire chunk to empty.”

## 5. Relation to the simulator's 191e9ad fix

There is a more direct original mechanism than shoving alone: inbound candidates are partitioned before priority sorting. Candidates committed to their chosen lane, not red-light-blocked and not blocked by traversing traffic are promoted into the eligible prefix. Shoving candidates retain eligibility. Other candidates remain behind that prefix. The eligible prefix is sorted by shoving first, then lane-topology roundabout membership, then distance to chosen lane, then registration timestamp. Roundabout membership uses lane connectivity, not simply a current-cell “on ring” flag.

Commit191e9ad's stationary-conflicting-occupant filter therefore resembles part of the original eligibility handling, but is not equivalent:

- Original eligibility calls its full traversing-collision decision, including shared-exit space and configured exceptions; it is not restricted to occupants below our 0.02speed cutoff.
- It includes first-two-lane commitment and traffic-light state.
- It retains shoving eligibility and has explicit blocking-cycle recovery.
- In the subsequent inbound conflict check, an earlier stopped or lane-replacement-blocked candidate changes an argument to the connection-intersection test. The exact geometry semantics of that fourth argument are **not available in the inspected extracts**. Do not describe it as automatically ignoring every stopped candidate.

**Recommendation, not an implemented fix:** independently reproduce this complete arbitration/commitment/cycle behavior, then compare the existing five-car regression and the v21 adjacent-junction case. Evaluate whether191e9ad becomes redundant and remove/replace it only when those checks establish equivalence. Neither “keep both forever” nor “shoving alone certainly fixes it” is established by this audit. No replacement rule or scenario was changed here.

## 6. Registration timestamp and commitment

Inbound registration is **not the moment a car enters the 2.5-tile lookahead**. When assigning/updating an active route, the original registers each newly appended planned lane with that lane's chunk. Its timestamp is current game-clock time plus the integer offset supplied by the path-building call; that call supplies the updated path count. This offset is a synthetic ordering offset, not measured travel time. Existing retained path-prefix entries keep their registration rather than being recreated on every approach.

A chosen lane is committed when it is among the vehicle's **first two remaining planned lanes**. During inbound sorting, the first observed committed time is stored separately. That committed timestamp supplies the optional 45swait limit. Registration for return paths uses a separate returning-inbound list and offset 0, not the same active approach arbitration list. Entering the next lane removes its active inbound reservation.

The 2.5-tile lookahead belongs to movement anticipation; it is not the source of the inbound tie-break timestamp.

## Constants and confidence

Values below are derived from Q32.32 raw values or the inspected numeric asset; tile conversion assumes the existing verified 2 world-units-per-tile convention. Approximate decimal values are shown; use the recorded raw provenance for exact conversion.

| Quantity | Original units | Tile equivalent / state |
| --- | --- | --- |
| Vehicle length | approximately 0.65world units | approximately 0.325tiles |
| Shared-exit accumulated-space threshold | strictly greater than 2 vehicle lengths, approximately 1.3world units | strictly greater than approximately 0.65tiles |
| Space-chain bound | 5 vehicle states | not 5 chunks/tiles |
| Minimum following gap | approximately 0.1world units | approximately 0.05tiles |
| Different-exit release | within last 1 vehicle length, with strict greater-than distance test | final approximately 0.325tiles |
| Stopped threshold in chunk arbitration | approximately 0.001world units/s | approximately 0.0005tiles/s; not our 0.02cutoff |
| Pushing-cycle speed setting | approximately 0.200000003world units/s | approximately 0.1000000015tiles/s |
| Optional maximum committed wait | 45 game-clock seconds | feature enablement unverified |
| Movement lookahead | 5 world units | 2.5 tiles |
| Straight roundabout outside fraction | 0.5 | option off in inspected asset |
| Green-light geometric-conflict bypass | enabled | same-exit space test still runs |

**Limits:** static evidence from the installed private extracts/configuration; no original matched-state execution of v21, no new simulator run, no confirmation of the runtime maximum-wait feature toggle or additional configuration overrides. Raw connection geometry for the stopped/hotswap argument remains unresolved. Private code/assets remain local; only our prose, numeric facts and evidence hashes are archived. These findings supersede the earlier broad suggestion that “don't enter without room to clear” alone describes the original.
