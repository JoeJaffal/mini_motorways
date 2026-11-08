# Simulator repairs after the emergency stop — 8 November 2026

Successor to the [emergency handoff](../full-replay-review-2026-11-08/EMERGENCY_HANDOFF.md) and the
[resume review](../full-replay-review-2026-11-08/RESUME_REVIEW_FOR_APPROVAL.md). Work by Aya's
session on branch `mohammad`, authorized by the user after Mohammad's
[response](../full-replay-review-2026-11-08/LOCAL_TRANSFER_RESPONSE.md). No training, no deployment
over an installed player, no tuning toward the recorded 835, and no historical fixture overwritten.

Short note for the model re-evaluation session: [HANDOFF-2026-11-sim-fix.md](../../../simulation/Docs/HANDOFF-2026-11-sim-fix.md).

## 1. Reward-v4 drift isolated: intended rule-77 join in ordinary play

**Measured.** On the 77-suite source, `reward-fixture-v4.json` ends at 23 trips with no game-over
instead of 13 trips and game-over at 252.95 s. Engine variants built from the same source, each with
one rule disabled, replayed the fixture exactly as `TrafficEnv._advance` does
([script](source/isolate_reward_v4_drift.py), [results](measurements/reward-v4-drift-isolation.json)):

| Variant | Trips | Game-over |
| --- | --- | --- |
| Current source | 23 | no |
| `AttachNativeDrivewaysAt` disabled (75 motorway attach and 77 spawn/turn attach) | 13 | 252.95 s |
| `NativeJoinAt` disabled (77 traversable join cell) | 13 | 252.95 s |
| Only the spawn-time attach call removed | 13 | 252.95 s |
| Dedup edit reverted | 23 | no |

A lockstep comparison of the current source against the spawn-attach-removed variant
([script](source/lockstep_connection_diff.py)) finds exactly one structural difference in the whole
game. From t = 74 s, red house 5 at 10,7 (driveway down) and red destination 3 at 10,9 (top
entrance) are joined through the empty cell 10,8, with no road tile and no stock spent. Without the
join, destination 3 reaches demand 10, overcrowds for 50 s and ends the game.

**Conclusion.** The drift is the rule-77 native common-endpoint join, which needs both the spawn
attach and the traversable join cell. The dedup edit has no effect. Mohammad confirmed (`8a4b447`)
that the 75/77 joins are intended general Original rules, so this is intended ordinary-play
behaviour, not an implementation defect. Whether the original game joins this particular pair is not
independently verified.

**Hypothesis rejected.** The per-action trip counts first differ from v4 at t = 67 s in every
variant, including the variants that reproduce 13 trips/252.95 s exactly. That difference is
therefore not the drift. The reward test checks only the final score and terminal state.

**Change.** New `reward-fixture-v5.json`, recorded with Mohammad's v4 recipe (historical v2 opening
commands, then wait until the actual terminal; [recorder](source/record_reward_fixture_v5.py)). The
cap is 900 s instead of 300 s, because the current rules end this game at 305.15 s with 30 trips.
`training/test_rewards.py` now points at v5, with unchanged assertions. v4 and earlier fixtures stay
unchanged as history. Reward checks: 6/6 PASS.

**Consequence for old results.** Any game in which a house and a same-colour destination spawn with
their native driveway ends meeting at an empty cell now plays differently. Results recorded under
the 69–74 rules (both PPO and Evolved Rules) are valid for that simulator version only.

The environment checks are 7/7 PASS once an empty, git-ignored `tmp/` exists.

## 2. Stale `Waiting` on arrival fixed (agent-reported issue 1)

**Cause (code-level, proven by a failing test).** `Waiting` is updated only in the movement-proposal
loop of `TrafficControl.cs`, before the car advances. Arrival (`FinishHome`, and `EnteringParking`
becoming `Parking`) did not clear it, and non-moving cars get no further proposals. A car
accelerating from standstill gains 0.27 × 0.05 = 0.0135 tiles/s per tick, below the 0.02 waiting
threshold. A queued car released within one creeping tick of its journey end therefore arrives home
or in a bay with its queue wait, keeps it while there, and starts its next trip from it.

**Frequency (measured before the fix).** No stale value occurred in 1,981 home/parked samples
(reward-v5 game), 14,116 samples (reference networks on five cities × two seeds) or 300,697 samples
(replay v20 on the 77-suite source; [WaitProbe](source/WaitProbe.cs),
[results](measurements/waiting-staleness.json)). The defect is real but rare in practice.

**Fix.** Clear `Waiting` on arrival home and on parking in a bay. `TotalWaiting` (cumulative) is
unchanged. New suite "arrival home or in a bay clears the current wait": failed before the fix with
`Home car keeps no stale queue wait: waiting=12.05`; 78 suites PASS after. Reward v5, environment
and five-map checks are unchanged.

**`meanWaiting` / `TotalWaiting`.** The observation's `meanWaiting` is the mean, over every car ever
spawned, of its cumulative `TotalWaiting` in seconds. It includes cars that never left home and only
grows. It is not stale, but it is not a current-queue measure. No code in `training/` or in Evolved
Rules reads it. It is now documented in the headless README, and the field is unchanged.

## 3. Simulator version string (headless protocol, additive)

**Requested by the user** so that result caches never reuse results from another simulator.
Mohammad called it reasonable (`8a4b447`). `SimulatorVersion.Value` in the shared core is
`2026-11-08.1`. The host reports it as top-level `simulatorVersion` on every reply (including errors and
`drawchoices`) and in the `--run-scenario`/`--verify-replay` summaries, and prints it for
`TrafficHost --version`. No existing field changed. Both clients read replies by key: Evolved Rules
`Host.call`/`verify.py` checks `PASS` on stdout, and PPO's `TrafficEnv` reads named keys. The bump rule
and value table are in [VERSIONS.md](../../../simulation/Docs/VERSIONS.md#simulator-version-string).
The headless README documents the field and the `waiting`/`meanWaiting` meanings.

**Test.** `scripts/verify_five_maps.py` now requires `--version` to print a non-empty string, and every
reply to carry the same value. It failed on the previous host (`--version must print the simulator
version`) and passes now. Core suites: 78 PASS. Reward and environment checks: PASS.

## 4. Roundabout 19,9 queue: permanent yield-cycle deadlock, cause proven and fixed

**Reproduced.** On the unfixed source, replay v20 ends at game-over 1185.95 s with 586 trips and
340/406 events, identical to the handoff's 75-suite run. All waits over 20 s begin after t = 1145, on
the approaches and ring around junction 19,7 and roundabout 19,9 (ring 19,8, 18,9, 19,10, 20,9).

**Cause (measured).** A probe ([BlockerProbe](source/BlockerProbe.cs)) recomputes each stopped car's
binding constraint exactly as `UpdateVehicles`/`MayEnter` do (queue gap, conflicting occupant,
approach priority), records the car responsible and extracts the deadlocked set: the greatest set of
stopped cars each held by a member. That set is empty until t = 1163, then never empties and grows to
27 cars by game-over ([evidence](measurements/roundabout-deadlock-v20.json)). At t = 1163:

- cars 28 and 22, leaving the ring at 19,8 northbound, yield **approach priority** to car 6, which is
  closer to junction 19,7;
- car 6 cannot enter, because car 52 is **stopped inside** junction 19,7 on a conflicting lane
  (`Conflicts(19:7:2:0, 19:7:2:2)` is true);
- car 52 queues behind car 15, which cannot enter the ring because car 22 occupies the conflicting
  ring-exit lane (`Conflicts(19:8:2:3, 19:8:5:6)` is true);
- the northbound exit does **not** conflict with car 52 (`Conflicts(19:7:6:6, 19:7:2:2)` is false),
  so only car 6's priority keeps 22 and 28 on the ring.

The handoff's future-junction/yield-cycle hypothesis is therefore confirmed. A car blocked by a
stationary conflicting vehicle kept priority, and the cycle closed through an adjacent junction and
ring. **Correction:** this deadlock did not cause v20's game-over. Red shared destination 35 at 11,18
was already overcrowded from about t = 1116. The 20–38 s waits are the time deadlocked cars spent
before the game ended.

**Fix.** In `MayEnter`'s priority comparison, a car does not hold priority while its own target is
occupied by a **stationary** (speed < 0.02) vehicle on a conflicting lane. Physical conflict checks
are unchanged, so no new overlaps are possible. A broader candidate (ignore any conflicting
occupant, moving or not) also removed the deadlock but changed far more decisions (v20 game-over
1104.3 s, 492 trips), so it was rejected.

**Regression.** New suite "blocked approach priority cannot deadlock a junction beside a roundabout"
rebuilds the five-car configuration at the measured lane offsets. It fails on the unfixed engine
(all five cars stuck after 60 s) and passes with the fix. A first four-car version, without the car
ahead of D, passed on the unfixed engine; it was diagnosed ([trace](source/CarTrace.cs)) and not used.

**Measured effect.** v20 with the fix: no deadlock at any second, game-over 1176.95 s, 580 trips. The
first divergence from the unfixed run is at t = 1007.65, where car 14 near 26,15 no longer yields to a
car held by a stationary vehicle ([Timeline](source/Timeline.cs)). Later differences are chaotic
divergence. Neither replay score is a fidelity target or a validated comparison with 835. Core suites:
79 PASS. Reward v5, environment and five-map checks are unchanged. **Simulator version:
`2026-11-08.2`.**

**Gameplay consequence.** Any game in which an approaching car's conflicting lane is held by a stopped
vehicle can now resolve differently, and permanent junction/roundabout deadlocks of this form no
longer occur. Results from `2026-11-08.1` and earlier are not comparable in heavy traffic.

## 5. Replay input v21: the seven handoff corrections, regenerated from the builder

**Builder equivalence (open question in the handoff, now measured).** Mohammad's
`build_full_trace.py`, with only its output paths redirected so his local working files are not
overwritten, regenerates `replay-candidate-v20.json` exactly: all 406 events and every top-level field
are identical. Its side outputs differ from his local copies only where those predate v20 (yellow
35,12 onset 807 → 799; two motorway-toast native candidates now excluded).

**v21.** [`build_full_trace_v21.py`](source/build_full_trace_v21.py) is that builder plus only the
seven corrections listed in the handoff, each marked in the code. It writes to
`tmp/simulator-repairs-2026-11-08/`. Output: [`replay-candidate-v21.json`](replay-candidate-v21.json),
with 400 events. The diff against v20 is exactly:

- removed: 715 draw 24,12–25,12 (correction 1); 731 draw 9,10–9,11 (2); 841 draws 38,16–38,17 and
  38,17–38,18 (3); 841 draw, 849 erase and 857 draw of 37,20–38,20 (5); 859 draw 43,8–43,9 (7);
- added: 846 driveway turn of green 38,19 to north (4); 855 erase 40,22–40,23 (6).

**Visual check of correction 3.** Boards from 839 to 1007 show that the column-38 white area at rows
16–18 is the new green lot's outline (with the spawn circle drawn over it at 840–841). It persists to
1007, and no vertical road is ever drawn there, so the omission runs from 841 to the end. The same
boards show the green 38,19 north connection at 846 (not at 841) and no horizontal 37,20–38,20 road.
The contact sheet is cropped from the gameplay video and stays local, as `AGENTS.md` requires.

**Not changed.** The green 37,20–37,21 branch onset stays at 858, about 1 s later than the stock
evidence at 857: the handoff noted it but did not list it as a correction. The green north turn has
about 1 s of timing uncertainty.

**Direct topology check** (Mohammad's helper; placement and material only, no traffic or score;
unused edges refunded immediately). Re-running it on v20 reproduces his archived
`direct-topology-allstocks-v20.json` exactly (rejected at source 870, 372/406). **v21 passes all 400
events** ([output](measurements/direct-topology-v21.json)). Road stock against the video's HUD:

| Video s | 720 | 740 | 760 | 790 | 810 | 820 | 830 | 840 | 850 | 860 | 870 | 880 | 890 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Video HUD | 20 | 15 | 19 | 19 | 32 | 25 | 24 | 19 | 14 | 10 | 4 | 13 | 13 |
| v20 | 18 | 12 | 18 | 18 | 29 | 23 | 22 | 16 | 10 | 3 | rejected | – | – |
| v21 | 19 | 14 | 20 | 20 | 31 | 25 | 24 | 18 | 14 | 10 | 5 | 16 | 14 |

The late material shortfall the handoff predicted is resolved through 860. Small differences remain
at 540 (16 against 13), 720–810 (±1–2) and 870–890 (+1 to +3); they may involve delayed retirements or
1–2 s detection lag and have not been investigated.

**Strict scored runs** (`--run-scenario`, existing 120 s wall cap, simulator `2026-11-08.2`;
[summary](measurements/replay-v21-results.json)). These are partial diagnostics, **not** a validated
comparison with the original 835:

| Candidate | Game-over | Trips | Events | Failing destination |
| --- | --- | --- | --- | --- |
| v20 | 1176.95 s | 580 | 336/406 | red 35 at 11,18 |
| v21 | 1166.05 s | 570 | 325/400 | navy 14 at 12,14 |

Only corrections 1 and 2 (game time 980 and 1012) occur before v21's simulated game-over. Corrections
3–7 (game time 1190 or later) are not reached in the scored run.

**New finding: a physical gridlock ends v21 (not fixed, user decision needed).** The wait-for probe,
updated to the current priority rule, finds a deadlocked set from t = 1119 at the adjacent junctions
20,11 and 20,12. Southbound car 41 must turn east across 20,12, where northbound car 17 sits inside
the junction. Car 17 (behind car 12) must enter 20,11, where car 22 sits inside that junction. Car 22
queues behind car 41. Every binding link is physical occupancy; no priority link is needed. The set
grows to 22 cars, 8 of them navy-14 trips, and navy 14 overcrowds from about t = 1116 until the
game-over. Preventing this needs a new rule (do not enter a junction without room to clear it),
which is a gameplay change, so it is left for the user to decide.

**Not done here.** Handoff step 6 (wall-clock playback synchronisation against the video's 1/2× and
pauses) needs viewer work that has not been started. Hidden original demand/parking RNG and exact
action times remain unverified.

## 6. Parallel-host crash (agent-reported issue 2): no host cause found

One host on `2026-11-08.2` uses about 56 MB working set, 30 MB private memory, 177 handles and 8
threads, all flat over a 376 s game ([measurement](measurements/host-resources.json)). Ten hosts need
roughly 0.6 GB and 1,800 handles, and nothing in the host grows with the number of processes. The
0x800705AA (`ERROR_NO_SYSTEM_RESOURCES`) crash is therefore most likely a machine or session limit
(commit memory, or desktop heap from many console processes). It was not reproduced; no 10-host run
was attempted.

## 7. Final verification and what remains open

Source `615f08c` (simulator `2026-11-08.2`), .NET SDK 8.0.427: 79 core suites PASS
([output](measurements/core-79.txt)); environment 7/7 ([output](measurements/environment-final.txt));
reward v5 6/6 ([output](measurements/rewards-final.txt)); five-map protocol 10 runs PASS
([output](measurements/maps-final.txt)); `dotnet build simulation/Headless -c Release` succeeds with
0 warnings and its DLL reports `2026-11-08.2`. The tracked
`simulation/Reports/five-map-protocol-checks.json` is the script's regenerated output for this source
(its previous copy dated from 25 October).

**Open:**

- The physical gridlock at adjacent junctions (section 5): the user decided to replicate the
  original's space-checking logic, including its conditions, and to obtain it from Mohammad's existing
  read-only extracts ([request](REQUEST_SPACE_CHECK_RULE.md)) rather than decompile anything here. Not
  implemented until his answer arrives.
- The Unity Original player has not been rebuilt. The handoff requires a stable source first, and the
  gridlock decision may change the source.
- Wall-clock playback synchronisation (handoff step 6) has not been started.
- v21's late stock differences (540, 720–810, 870–890) have not been investigated.
- Exact original parity, hidden RNG and action times remain unverified, and `exactReplicaValidated`
  stays false.

No training, model evaluation, deployment, push or original-game write was done in this work.


## Original rule response — 8 November2026

[Answer to all six questions](ORIGINAL_SPACE_CHECK_RULE_ANSWER.md), numeric findings/hashes archived. Static read-only audit confirms conditional shared-exit space checking, eligibility partition, commitment/registration timing and cycle-based shoving. No blanket-clearance engine patch or original/v21execution. Runtime timeout feature and stopped-connection geometry remain uncertain.

## 8. Original junction arbitration replicated (simulator `2026-11-08.3`)

**User decision.** For the v21 gridlock, the user chose to replicate the original's space-checking
logic, including its conditions, from Mohammad's read-only extracts. Nothing was decompiled on this
machine. Mohammad's [answer](ORIGINAL_SPACE_CHECK_RULE_ANSWER.md) shows the original has no blanket
"don't block the box" rule. It has a conditional shared-exit space test, committed-candidate
eligibility and blocking-cycle recovery ("shoving").

**Implementation** (`JunctionArbitration.cs`, commit `c1d23d0`, `OriginalReference` only; Custom
keeps the previous logic, including `191e9ad`). Entry order:

1. A chunk with ≤2 lanes accepts at once. This check comes before the light, so a light on a 2-lane
   tile has no effect.
2. A red light rejects.
3. A shoving car is accepted for its immediate next lane.
4. Cars inside the junction, the "traversing" vehicles. Those on their last lane are ignored.
   - **Same exit:** the space test, then the crossing geometry; no near-exit release.
   - **Different exit:** released within the last car length; otherwise the geometry check, which is
     skipped on green (installed `greenLightsIgnoreCollisions`).
5. Inbound reservations. Only committed candidates (chosen lane among the next two) that are neither
   red-blocked nor blocked by traversing vehicles, or that are shoving, can rank earlier. Order:
   shove, then ring membership, then distance, then registration time.

**Space test.** Walks the entering car's previous-tick obstacle chain over at most 5 states: leader,
blocking junction, route end or none. Entry is allowed when usable distance strictly exceeds 2 car
lengths.

**Registration.** Stamped at route assignment as game time plus the path's lane count, kept across
route refreshes and removed on entering the lane.

**Cycle recovery.** Each tick, links are followed from junction-blocked cars to their blocker, and
from tightly queued slow cars (below 0.1 tiles/s) to their leader. Junction-blocked members of an
actual cycle shove. The flag clears on the next lane change.

**Interpretations and omissions (marked in the code).**

- Our follower holds exactly the 0.05-tile minimum gap, so a gap within 0.01 tiles of it counts as
  "below the minimum gap".
- The leader-in-chunk discount subtracts only the leader's remaining in-chunk distance beyond one car
  length.
- Return routes are registered like any route assignment.
- The same-exit geometry is still applied after the space test, because our engine does not follow
  across merging lanes.
- Not implemented: the effect of all-leader "pushing" cycles, the stopped-candidate geometry argument,
  and the 45 s escape (enablement unverified). Train-crossing extras keep the existing mechanism.

**Tests (each fails on the previous engine, passes now).**

| Check | Failure on the previous engine |
| --- | --- |
| A distant junction is registered at departure, at `JourneyStarted` + lane count | not registered |
| A car heading for the same exit as a car stuck inside the junction (held by a red light downstream) waits outside | it drove into the junction |
| The replay-v21 adjacent-junction gridlock, four cars at their t = 1119 offsets, clears | all four stuck after 60 s |

The earlier five-car roundabout regression still passes: the blocked car is now ineligible. Core: 81
suites PASS ([output](measurements/core-81.txt)). Environment 7/7, reward v5 6/6 (the fixture game is
unchanged), five-map 10 runs PASS, Release build 0 warnings.

**Replays** ([results](measurements/original-arbitration-results.json); partial diagnostics, not a
comparison with 835). The deadlock probe now calls the engine's own `MayEnter`.

| Candidate | `2026-11-08.2` | `2026-11-08.3` | Deadlocked seconds |
| --- | --- | --- | --- |
| v20 | 1176.95 s, 580 trips | 1104.2 s, 490 trips | 0 |
| v21 | 1166.05 s, 570 trips (gridlock from 1119) | 1104.2 s, 488 trips | 0 |

25–26 cars shove per replay, the first at t = 803.45 ([ShoveCount](source/ShoveCount.cs)).

**New finding: a carpark gate lock (not fixed).** The `2026-11-08.3` replays now end on red 20 at
16,16, a shared lot that becomes unreachable from about t = 973. Car 34, passing through the lot, is
first on the outside approach `20:18:2:4`, but gate 19,18 is owned by car 10, queued behind it. The
gate rule measures an outbound car's distance to the start of its final road lane (car 10: 0.157)
and a connector user's distance to the connector (car 34: 0.78), so the car behind ranks nearer.
Neither can move. This is Mohammad's engineered approach-gate rule combined with shared transit; the
arbitration change does not touch it, and no link in the lock is a junction decision. It was not
measured on the previous engine. It awaits the user's decision
([GateInspect](source/GateInspect.cs)).
