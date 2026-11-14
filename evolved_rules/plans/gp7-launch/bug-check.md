Rejected draws in the screen: a house spawning on a route while it is being drawn (shared executor, not C4-min); no fix, launch.

# gp-7 screen: bug check (plan section 5 bug gate)

**Trigger.** Point Fast had 1 rejected draw in its first 100 screen games (seed 3332, 1 of 1651 commands).
Every other point had 0, and so did L in its 400 pre-played games (screen 3300-3599, test 6100-6199). No point was
below -3 SE. Started 2026-11-14 20:25, done 21:05 (about 40 min of the 2 h box).

**Reproduction.** Replayed seed 3332 with Fast's policy text from the frozen screen worktree (4453544, gp7-v1), with
the same DLL (f34). Identical game: 1394 trips, 1 rejected action.

**Cause.**
- At t = 522 a pair route (kind evo) was planned through (24,14) -> (25,13) -> (24,13) -> (23,14) -> ... -> (19,14).
  At planning time (23,14) was empty.
- The route is drawn one segment per command, and each command steps 20 ticks. At t = 524, between two segments,
  the game spawned a house on (23,14).
- The next segment (24,13) -> (23,14) ran into the new house ("House driveway moved").
- The segment after that, (23,14) -> (19,14), now started at a house. The simulator's DrawRoad tried to turn that
  house's driveway and refused ("Driveway needs a clear neighboring tile",
  TrafficWorld.cs SetHouseDriveway).
- The route's later segments, and the next decision at t = 527-530, connected the same cells with no rejection.

**Assessment.**
- This is a race between planning and house spawns inside the multi-command executor (`execute_route`). L and
  every earlier policy share that executor, so it is not a C4-min or EvoCost defect.
- The planner's search never enters building cells (`_enterable`), so it can't plan through a house that exists.
- Cost: one refused command (one wasted 20-tick step) and no road tiles. The game state stays valid, and the game
  is deterministic and fully scored.
- New routes make the race slightly more likely because they draw more segments per decision. The observed rate
  (1 in 1,500 screen games) is negligible.

**Decision.**
- No code change. A fix (re-checking each segment against the live state) would change the executor for L as well.
  It would also invalidate the screen and the identity gates two days before T_freeze.
- The finding is recorded. cma-7 launches on gp7-v1 as screened.
- Any further rejected draws in the rest of the screen are listed below and checked the same way. Any other cause
  stops the launch.

**Remaining screen chunks (3400-3599):** no further rejected draws: 0 in all 1,000 games of chunks 3400 and 3500 (5 points x 200 maps). Over the full screen: 1 rejected draw in 1,500 games (Fast, seed 3332).
