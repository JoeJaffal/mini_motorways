# Simulator repairs after the emergency stop — 8 November 2026 (in progress)

Successor to the [emergency handoff](../full-replay-review-2026-11-08/EMERGENCY_HANDOFF.md) and the
[resume review](../full-replay-review-2026-11-08/RESUME_REVIEW_FOR_APPROVAL.md). Work by Aya's
session on branch `mohammad`, authorized by the user after Mohammad's
[response](../full-replay-review-2026-11-08/LOCAL_TRANSFER_RESPONSE.md). No training, no deployment
over an installed player, no tuning toward the recorded 835, and no historical fixture overwritten.

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
