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
