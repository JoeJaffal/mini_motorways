# Original traffic lights and carpark entrances: follow-up answer

8 November 2026. For Mohammad/Aya's simulator session. Responds to the user's supplied follow-up and [NOTE_CARPARK_GATE_CHANGE.md](NOTE_CARPARK_GATE_CHANGE.md). Read-only inspection of existing private extracts and the installed numeric configuration; simulator revision read was c27107d. No original code copied, no simulator edits or model runs. [Constants, private evidence hashes and limits](measurements/original-signals-carparks-findings.json).

**Main findings:** the reported nearby distance/count/timing are original values, but the simulator's blocked-car counting and phase-weight formulas are not equivalent to the inspected original. The original carpark uses the road-chunk/lane arbitration machinery; a separate whole-entrance owner gate is not visible in these inspected classes. Neither fact proves that one isolated patch will remove all replay differences or recover the reported 105 trips.

The 408 vs 513 GP result,8/10 maps worse and wait changes are user-reported evidence here; not independently reproduced in this audit. Do not launch the held full re-evaluation on the basis of this note alone.

## A1. Green, extension, amber and phase changes

Installed values, rather than class constructor defaults:

| Setting | Installed value |
| --- | --- |
| Normal green reconsideration delay | 3 game-clock seconds |
| Overtime reconsideration delay | 1 second |
| Amber duration | approximately 0.7seconds (Q32.32 decoded 0.699999988079071) |
| Nearby radius along route | 1 world unit = 0.5 tiles |
| Minimum nearby count | 3 |
| Age for saturated waiting weight | 30 seconds |
| Base age-weight multiplier | 1 |
| Mothballed chosen-lane age multiplier | 4 |
| Non-crossing/right-on-red age modifier | approximately 0.1 |
| Current-lane carpark/parking-space input age multiplier | 10 |
| Active-pair same-chunk-blocked total-weight modifier | approximately 0.1 |
| American red-light rules |on |
| Green traversing-geometry bypass |on |

There is **no maximum-green cap in the inspected alternating process**. It accumulates a timer, reconsiders after the normal delay, and either starts amber or marks overtime. A failed reconsideration resets the timer. While in overtime, reconsideration can happen after the 1 second delay; the process checks the normal-delay condition OR the overtime condition. Comparisons are strict greater-than, so discrete process cadence affects the first eligible tick. Do not turn 3 seconds into an exact always-switch time or 1 second into a maximum extension.

If rotation is required, overtime is cleared, amber begins, and the timer resets. After amber exceeds its delay, select the next valid weighted pair, leave amber and reset the timer. The next pair is selected at rotation time, so it is not necessarily frozen to the pair that looked best before amber. Pair changes caused by changed lane topology can preserve an existing pair, or choose a replacement and reset its duration when it no longer exists.

## A2. Exactly which nearby cars count

The guard that delays rotation for one or two nearby cars is real: when the active pair has a count strictly between 0 and 3, decline rotation before comparing phase weights. A count of 0 or at least 3 merely permits the later decision; it does not force a swap.

Only **committed inbound candidates** count: the chosen lane must be among the vehicle's first two remaining planned lanes. Match its inbound direction to a direction in the pair. Nearness is distance **along the route to the start of the chosen lane**, strictly less than 1 world unit, not Euclidean distance to the signal's center. The general DistanceToLane routine sums the remaining current-lane distance and intervening planned-lane lengths. There is **no moving-only speed filter**; a stopped car can count.

Crucially, the rotation guard requests the original's blocked-candidate handling. The counting routine ignores uncommitted candidates, then, upon reaching a committed candidate whose nearest obstacle is lane replacement OR whose current blocking lane belongs to this signal's owning chunk, it **ends that scan**. This is a literal early termination, not simply skipping that car. The test occurs before matching the requested approach direction, so the existing inbound-list order can affect each direction's count. Previously counted candidates remain counted. Preserve/verify this detail rather than silently replacing it with a per-direction moving-car count.

Thus “stopped” and “excluded by the original count” are not synonyms. A car blocked at another downstream chunk need not satisfy this same-chunk condition. Likewise, a car already traversing the owning chunk is not automatically an inbound candidate for it.

## A3. The stuck green and whether a switch is forced

For your reported case, first inspect the actual blocking-lane chunk and inbound-list position of the stuck green car. If its shared-exit rejection is represented as a blocking lane in signal20,13's own chunk, the original counter does not keep counting that car as an ordinary eligible nearby car. If it is the first relevant committed entry, its count scan ends with 0, which removes the one-car extension guard. This is a source-derived explanation to test, **not a matched-state reproduction** of v21.

The original also reduces a blocked candidate's phase weight, but only when its blocking lane belongs to this same chunk AND it is being counted for the currently active pair. These mechanisms can allow another demanded phase to win. There is no separate hard “green has been stuck 90 seconds, force a switch” branch in the inspected signal code. A car stopped for a different reason may still count, and1–2 counted nearby cars can still cause repeated extensions. Do not add a hard maximum-green or generic stopped-car exclusion and label it original.

The optional 45s intersection waiting escape discussed previously is not a signal phase timer. Its runtime feature state remains unverified, and it does not generally override traffic-light denial.

## A4. Next-phase weights: exact distinctions from our formula

Phase demand is drawn from committed inbound reservations for the requested approach directions. Normal weight comparison is **not restricted to the nearby 0.5 tile radius**, nor to our lookahead window. The timestamp used for age is first commitment to that chosen lane, not accumulated seconds actually stopped.

For each candidate:

1. Clamp commitment age divided by 30 seconds to0–1, then square it. Apply the base age multiplier 1.
2. If its **chosen lane** is mothballed, multiply this age contribution by 4.
3. Apply the non-crossing/right-on-red modifier 0.1 when applicable to the approach's ordered candidates (see below).
4. If the **input type of its current lane** is Carpark or ParkingSpace, multiply the age contribution by 10. This is a lane-type test, not just our LeavingParking stage test.
5. Add the base contribution 1 **after** those multipliers.
6. If this is the active pair and that vehicle's blocking lane belongs to this signal's owning chunk, multiply the **whole resulting contribution** by 0.1.
7. Sum contributions for the pair.

Consequences: an ordinary car at full age has weight 2; a carpark-input car at full age has weight 11 before other modifiers, not 4. A just-committed car contributes 1 even if it is leaving a carpark or on a mothballed chosen lane. Mothball/carpark modifiers do not multiply the base 1. Generic “Queue ahead” does **not** by itself trigger the original0.1penalty; the active-pair/same-chunk blocking-lane condition does.

The non-crossing modifier is also ordered: for each inbound direction, the original starts by discounting the age contribution of candidates whose turn does not cross a relevant lane. Once the scan encounters a crossing connection, the discount is no longer applied to that candidate or later candidates in that direction. It is not simply a universal 0.1 on every right-turning car regardless of queue order.

Weights use a strict-greater winner update, so equal positive weights retain the first winning phase in the stored phase order. All-zero demand falls back to the current valid index (or initial index 0), rather than forcing a fairness rotation. RequiresRotation refuses if current is already the highest weighted pair; otherwise it verifies that a distinct next valid pair exists. There is no independently observed fairness timer here.

## A5. Approach grouping and amber permissions

Phases are built from the chunk's **actual lane input directions**:

- Pair opposites first, in fixed direction-enumeration order.
- From remaining directions, try pairs separated by three eighth-turn steps (135 degrees). At an examined direction, if both +3 and −3 alternatives remain, defer pairing that direction. Otherwise pair an available alternative and remove both from the remaining set.
- Give each leftover direction its own phase.

It is therefore more than opposite pairs plus singles. Enumeration order matters; use the original direction convention when translating indices.

Amber is approximately 0.7 seconds for the ordinary requested pair transition. **Important static finding:** ChangeGreenToAmber sets the amber flag/notifies observers but leaves ActivePair unchanged. The inspected chunk permission checks use the complement of ActivePair and do not test amberLightsOn. The shown entry logic therefore retains the old active pair's permission during amber; it does not implement our current “amber denies every approach” rule. I did not exhaustively inspect external observers/runtime overrides or perform an original execution, so this is a confirmed property of the shown model/chunk code, with that scope. Do not describe the amber interval as proven all-red clearance.

American red-light rules are enabled. A blocked approach can use an allowed non-crossing turn: inspect outbound directions in the three successive negative eighth-turn rotations from its inbound direction; the first present outbound direction determines whether that chosen exit is non-crossing. If no such direction exists, the connection is treated as crossing. This depends on the junction's exits, not a universal “every right turn always goes on red” shortcut. The old active pair remaining selected during amber also matters to the green geometric-conflict bypass.

## A6. Two earlier claims, precisely scoped

**Two or fewer lanes:** yes, the entry function accepts such a chunk before consulting the light. But “the light has no effect at all” is too broad: attaching a traffic-light model also makes a chunk controlled and causes inbound-lane speed limits to be recalculated. This audit confirms the absence of a light-based entry veto in that early branch, not equality of every movement/speed consequence.

**greenLightsIgnoreCollisions:** yes, the installed value is 1/on. It bypasses the specified traversing-connection geometric collision test for the active green direction, **not** the shared-exit space check that occurs first. Other following/entry logic remains relevant.

**Correction to the earlier junction answer:** its categorical description that a red direction is rejected before shoving was shorthand for a direction the light actually blocks after the connection-crossing test. With installed American red-light rules on, a qualifying non-crossing turn is not denied in the first place. Its amber behavior also was not established in that earlier answer. Use this follow-up rather than inferring all-red amber or universal red-turn denial from the earlier summary.

## B1. Carpark entry/exit arbitration

CarparkModel constructs actual entrance and exit bespoke lanes **inside the entrance tile's RoadChunkModel**, plus an internal turn-around/circulation connection in that same chunk. Each bay's outer circulation and inner circulation use their own RoadChunkModel, with parking-entry, parking-exit and circulation-through lanes; the bay itself uses a separate parking chunk. These are registered simulation models and ordinary LaneModels, tagged as carpark lanes.

Vehicle path assignment registers their inbound chosen lanes with those chunks. VehicleMovementProcess consults the next lane's chunk entry arbitration; there is no carpark bypass around that call in the inspected movement path. Therefore these lanes participate in the same machinery: active route registrations, first-two-lane commitment, eligible-prefix ordering, chosen-lane route distance, timestamps, traversing conflicts/shared-exit checks, and relevant cycle shoving. As elsewhere, a chunk with at most 2 lanes takes the simple early-accept branch; merely being labelled a parking lane does not imply full multi-lane arbitration in every segment.

**Separate parking allocation exists.** ParkVehiclesProcess assigns available bays to destination-arriving cars, using the simulation RNG when multiple free bays exist, then assigns a route into that bay. It handles no-bay fallback, dwell and departure. This allocates a parking space; it is not a one-owner lock on the whole entrance. Bay occupation and road-entry priority should not be collapsed into one gate.

## B2. Through-cars versus arrivals and departures

For a vehicle crossing a shared lot to reach somewhere else, destination arrival/parking logic is not what establishes its priority at this lot's entrance. It travels the actual lane graph. A car arriving to park and a car passing through compete for the same chosen entrance lane/chunk when that is their next step; the entry comparator has no “going to park first” classification. Departing vehicles have the actual exit/merge lanes as their chosen lanes, with their own geometry and shared-exit/conflict relations.

The comparator measures **distance along each vehicle's current/planned route to the start of its chosen lane**. It is not Euclidean distance to the entrance, distance to the final destination, or one arbitrary outside-turn reference for all lane types. When two cars choose the same entrance lane, both use that same target lane start. When entry and exit cars target different lanes in the same chunk, lane geometry and their corresponding route distances differ legitimately; do not force them onto one scalar approach point by convention.

No general carpark exit priority multiplier exists in this chunk comparator. The 10 carpark multiplier above is for **traffic-light phase demand**, and affects the age contribution only. Do not apply it as an unrelated parking/through-traffic priority rule. RNG bay assignment and process ordering can still affect which route a destination arrival takes.

## B3. Is there an original equivalent of our gate?

I found **no whole-entrance owner ID, one-car-at-a-time semaphore, or independent “reserve before the outside turn” gate** in the inspected CarparkModel, ParkVehiclesProcess, LaneModel, VehicleModel, RoadChunkModel and movement code. The confirmed mechanism is entrance/exit lane geometry plus chunk arbitration, following and bay allocation. That finding is scoped to those extracts; it is not a proof that every original system has been exhaustively searched.

Entrance chunk layout is important: it includes entering, exiting and circulation/turn-around paths in one arbitrated physical chunk. Merely applying junction arbitration to our reconstructed exterior road tile, while separately bypassing it on all IsParking lanes, is not equivalent. Internal outer/inner bay merges also have real multi-lane chunks. Our gate may currently compensate for missing grouping/merge geometry; deleting it alone can expose overlaps even though the original has no corresponding owner gate.

There is also a general merge-following feature in LaneModel: when enabled, other lanes in the same chunk with the same output direction can supply a leader, based on remaining distance to their common exit. This supplements same-lane following. **Runtime enablement of CheckForVehicleCollisionsWhenMerging is unverified here.** Do not label it always enabled, and do not confuse it with a global carpark mutex.

Parking specifics visible in the inspected code: nominal parked dwell is 3 seconds, with a strict-greater timer check; bay release occurs when a departing car leaves the bay's parking chunk, not when it clears the whole entrance. Available-bay choice can be random. The process also handles destination cars driving through when no bay is available; that destination-service case is distinct from unrelated-color through-routing to another destination.

## B4. What I would do about 7ef4071

The inconsistent target-point ranking reported in NOTE_CARPARK_GATE_CHANGE is a valid defect in **our engineered gate**, and using one target for cars sharing an entrance is a sensible local correction. It is not evidence that our approach-start gate itself is original.

For fidelity, independently map the real entrance/exit/internal lane chunks and their arbitration first; make arrivals, through-cars and departing cars use that graph and the actual chosen-lane start. Keep bay reservation separate. Compare with the existing gate-lock reconstruction, mixed transit/parking cases, all four orientations, simultaneous entrance/exit traffic and physical separation tests before retiring the compensating gate. Carrying two unrelated priority systems indefinitely is not an exact original implementation; equally, removing a protective gate without repairing its underlying lane/chunk mismatch is not justified.

Original cycle shoving bypasses the original chunk entry decision for the immediate next lane, subject to its earlier checks. Letting it bypass our additional owner gate is an engineered adaptation, not a directly observed original gate rule. If that gate is replaced by accurate chunk arbitration, evaluate removal of the extra bypass with it. I have not traced 7ef4071 in a matched original state, and do not claim its fix is harmful or unnecessary with the present geometry.

## Suggested focused verification before any full model re-evaluation

These are proposals, not runs performed here:

- Signal-only deterministic checks: 1 green car blocked by this signal's own chunk; stopped green car blocked at another chunk; HotswappingLane; list-order early termination ; 0/1/2/3 nearby cases; strict radius; commitment-age weights; multiplier order; equal/all-zero demand; ordinary/overtime/amber timing and amber permissions; non-crossing red turns; lane changes during a phase.
- Frozen v21signal trace: record nearby candidates with committed status, chosen-lane route distance, nearest obstacle, blocking-lane chunk, committed timestamp and each phase's original-formula weight. This can test the stuck-green explanation without guessing or training.
- Carpark-only geometry/arbitration checks described above, including a passing-through leader with a parking car behind. Preserve the existing failing case and report whether a gate-free correctly grouped model clears it without overlaps.

Keep historical GP/replay results tied to their simulator versions. The reported 408/513 comparison does not by itself establish which listed mismatch caused the difference. No fixture relaxation, score-fitting, model training or deployment is part of this response.
