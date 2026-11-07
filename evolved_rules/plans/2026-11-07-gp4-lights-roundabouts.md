# gp-4: traffic lights and roundabouts in the planner (design)

Recorded 2026-11-07 on branch `gp4` (from `evolved_rules` at c1d1f0c). This is the design; the step-by-step plan comes after it is approved.

## Why

Phase 2 is finished (`final/README.md`). On the test maps 7000–7099 the final GP rule scored 245.9 trips and the CMA-ES rule 250.6, statistically tied. On 9000–9099 GP beat Mohammad's PPO by 45–52 trips. The user's target is human-level play, which means thousands of trips, so we are about 4× short.

The evidence says the planner's move set caps the score, not the search:
- Autopsies: games end in congestion. About 70% of stuck cars wait at junctions and 27% at a shop's car-park gate, with about 44 road tiles still unused at failure.
- GP has collapsed to a 3–4 term rule. It ignored the gp-3 traffic moves (clean routes, removal), and more generations added nothing detectable.
- Mohammad's PPO places traffic lights. In his test, changing only the first upgrade to two lights took one game from 83 to 266 trips, and lights on vs off was 177.5 vs 159.1 on 7000–7009.

The simulator already supports traffic lights and roundabouts through the headless host. Our planner never places them: they were left out on purpose (PLAN.md decision 11, and again for gp-3). gp-4 adds them and then repeats the Phase 2 protocol.

## Goals

1. The planner can place **traffic lights** and **roundabouts**, and evolved rules decide where and when.
2. Upgrade choice becomes a real decision: a lights or roundabout package is now usable, not just "+20 roads".
3. Repeat the Phase 2 protocol on the new move set: GP evolution to convergence, a CMA-ES control, final selection on unused maps, one test, and a head-to-head with PPO.
4. A clear answer to "how much do lights and roundabouts add?", measured against the locked Phase 2 rules on the same maps.

## Non-goals

- **No motorways** (user decision, 2026-11-07). The agent never places, edits or removes one. Motorway upgrade offers may still be taken for their 10 roads, as now.
- **No simulator changes.** Use the host as it is (`build` with `tool` `TrafficLight` or `Roundabout`).
- **No new learner.** GP and CMA-ES as in Phase 2. MBRL and PPO are handled elsewhere.
- **No moving lights or roundabouts after placement** in version 1 (see "Removal" below).
- Bridges are already handled by the route finder (`candidates.py` counts bridge spans) and need no work.

## Anti-goals (a failure even if it runs)

- **Old rules play differently.** Every Phase 2 text (the locked `final/gp3_final.txt` and `final/cma_final.txt`, gp-2's rule, the hand and separated rules) must play exactly the same games with the new code when the new moves are not enabled. gp-3 kept this invariant and so must gp-4.
- **Test maps used for choosing anything.** The new selection and test blocks below are touched once, in order.
- **A "win" that is selection luck.** Same statistics bar as Phase 2: paired per-map differences, n = 100 on the test, bootstrap CI and Wilcoxon.
- **Breaking separated routes by accident.** A roundabout links its ring to every built neighbour in 8 directions (TrafficWorld.cs:198–203), so it can merge roads that were kept apart. The planner must know this before placing one (see "Roundabout side effects").

## What the simulator does (facts, checked in code)

**Traffic light** (`TrafficWorld.Build`, TrafficWorld.cs:148–156; TrafficControl.cs; MaterialInventory.cs):
- Goes on an existing **ordinary road** tile (infrastructure 1) and turns it into infrastructure 4. Costs one light from stock (inventory index 3), no extra road.
- It does not have to be a junction, but it only does something at one. It pairs opposite approaches and switches between pairs based on waiting cars (`UpdateSignals`, `BestSignalPair`).
- A lit junction **skips the junction slow-down**: junctions of 3 or more links normally run at 0.5× speed (`IntersectionMultiplier`, RoadNetwork.cs:89). A light removes that penalty.
- Not allowed on a motorway endpoint or a roundabout.
- Removing it removes the whole tile (queued until cars clear) and refunds one road and one light. The road would have to be redrawn.

**Roundabout** (`AddRoundabout`, TrafficWorld.cs:181–205):
- Placed at a centre cell. The centre and its 4 orthogonal neighbours must all be in bounds and on land, with no buildings, other roundabouts, motorway endpoints, pending removals or traffic lights. Existing roads on those cells are allowed and get converted.
- Costs one roundabout (inventory index 4). Road tiles it overwrites are **not refunded**, and empty ring cells cost nothing.
- The centre's links are cut. The 4 ring cells become a circle. **Each ring cell links to every built neighbouring tile in 8 directions**, whether or not they were linked before.
- The ring cells are traversable and the centre is not (`CanTraverse`, TrafficWorld.cs:56–58). Ring speed is 1.2× (`RoundaboutMultiplier`), and cars yield on entry.
- Removing it queues the whole footprint and refunds the roundabout.

**Upgrade offers on LA** (PLAN.md section 3): lights ×2 + 20 roads; roundabout ×1 + 20; bridge ×1 + 20; motorway ×1 + 10 (from the 3rd offer); 30 roads (from the 2nd). The first comes at 140 s, and offers never expire.

## What the planner needs

### 1. Placement candidates

At each decision, list possible placements:
- **Light spots:** ordinary road cells (infrastructure 1, not pending removal) with **3 or more links**, while lights are in stock.
- **Roundabout spots:** cells where `AddRoundabout` would succeed (check the same footprint rules locally) and that would help: the centre or a ring cell is on a junction with 3 or more links, or next to a shop doorstep. Only while roundabouts are in stock.

Cap the list at a fixed number per decision (for example, the 32 spots with the most stuck cars nearby, like Mohammad's `SIGNALS = 32`), ordered deterministically.

### 2. Placement features (inputs the rules can read)

Per spot, from the current observation only, within the PLAN.md observation allowlist:
- tool (`is_light`, `is_roundabout`);
- junction links (degree), and whether it is on or next to a shop doorstep;
- cars on the cell and nearby (radius about 2): count, stopped count, maximum and mean waiting time;
- distance to the shop closest to failing (lowest overcrowding margin), and whether the cars stuck nearby belong to that shop's colour;
- for roundabouts: roads it would overwrite (tiles lost), new links it would create, and **whether it would join two colours' separated routes**;
- stock of lights and roundabouts, and road stock.

The global inputs and traffic inputs from gp-3 stay available. Values are raw, and the GP terminal layer scales them by powers of two as before.

### 3. A new rule tree: **place**

A fifth tree, `place`, scores each (spot, tool) candidate. Like `remove`, it acts **only when the best score is above 0**: at most one placement per decision, ties broken by list order, non-finite scores never act.

Order inside a decision: take an offer → build routes → place → remove. Placing changes the network, so routing re-plans at the next decision.

`place` defaults to the constant −1 (never place). That keeps every old text at exactly its old behaviour.

### 4. When to decide

Add one trigger to the event tracker: while a light or roundabout is in stock **and** any car has been stopped longer than a threshold, decide at least every N seconds. **The trigger is active only for policies that can place**, meaning the `place` tree is not a constant ≤ 0, the same way `removes` gates removal. This is required. An extra decision is not harmless: it resets the 10-second fallback clock (`agent.py:49, 53–54`) and runs route building and removal at new times. Old games also often hold light or roundabout stock: the locked GP rule's upgrade tree favours the roundabout package, and the hand rule's 20/20 road tie takes those packages. The current triggers stay as they are.

### 5. Routing with the new infrastructure

- **Session whitelist (amends PLAN.md decision 6):** `session._replayable` today allows only `draw`, `build` with `Remove`, and `upgrade`. Add `build` with `TrafficLight` and with `Roundabout`, using those exact case-sensitive names. The replay verifier (`AiReplaySession.Apply`) already accepts both, so this is Python only.
- **Roundabout centre vs ring:** the centre is also infrastructure 3 (TrafficWorld.cs:195), so `candidates._is_road` (`infra != 0`), the executor and `features.py:263` currently treat it as driveable road. It isn't. Read the observation's `roundabouts` field (centre and ring) to tell them apart; list it in the report as an extra observation field read. The centre is never enterable; ring cells are. Light cells (4) are already handled by `_is_road`. (`CityState.road_cell` is used only by tests and needs no change.)
- **The ring is one-way.** The host only lets cars go ring[i] → ring[i+1] (N → W → S → E, `RoadNetwork.cs` `Neighbors`), although the link bits in `connections` are symmetric. A\* on ring cells must follow the same direction, so planned costs match real trips.
- **Separated / clean / attach logic:** treat a light cell as a road cell and a ring cell as a junction.
- **Executor:** a `draw` into a ring cell works: `DrawRoad` does not build on traversable cells and links into them with `Connect` (TrafficWorld.cs:243–251). A stroke must never pass through a roundabout centre, because the host rejects it and skips the next link. A\* already prevents this once the centre is blocked. **Never use the `connect` command:** the replay verifier rejects it.

### 6. Roundabout side effects

Before placing, compute the links the ring would create, mirroring `AddRoundabout` exactly: 8-direction neighbours that are built, not ring or centre, and not another roundabout's cells. Pending-removal tiles count too, and rail and diagonal-crossing checks are skipped, as the host does. Expose two inputs, "new links" and "joins separated routes", so evolution can learn to avoid harmful placements. Do not forbid them outright. A merge can be fine, and the hand tests will show how often it hurts.

**Exclude roundabout spots whose footprint covers a building's driveway or entrance cell.** The automatic driveway hook-up only runs when a road is built, so such a roundabout would leave the building unlinked.

### 7. Removal

The `remove` tree keeps its gp-3 meaning: ordinary road tiles only. Lights and roundabouts are never removed in version 1, because removing a light costs the road tile and breaks the route until it is redrawn. A later version can add relocation if the autopsies show misplaced lights.

## Steps and checkpoints

**Step 1: moves and hand tests (checkpoint with the user).**
- Build the candidates, features, `place` tree and routing changes. **Switching on:** for tree texts, a 5-tree text turns placement on, the same way gp-3's 4-tree text turned on clean routes and removal (`gp.py:404–406`). Lights and roundabouts are both offered; the `place` tree can learn to use only one, through `is_roundabout`. Hand rules are Python classes and set `places_lights` / `places_roundabouts` directly. No engine or cache change is needed.
- Hand rules to test, on dev maps 3100–3199 (unused by anyone):
  - **LightHand:** the separated rule plus "place a light on the junction with the most stopped cars when a light is in stock".
  - **RoundHand:** the same for roundabouts, skipping spots that would join separated routes.
  - **Both together.**
  - Each also with the final GP rule's priority and hold trees.
- **Upgrade choice in all hand variants:** take the lights or roundabout package when the matching placement is enabled, otherwise the offer with the most roads. The final GP rule's own upgrade tree avoids the 2-light package, so with it the light variants would seldom have a light to place. The GP-tree variants are therefore labelled "GP priority and hold with the package rule".
- Autopsy each one (why games end, stuck cars at junctions, placements per game).
- **Report the results to the user before the long run.** gp-3's hand tests found nothing and evolution then found nothing; if lights and roundabouts show no gain here, decide with the user what to change first.

**Step 2: gp-4 evolution.**
- The gp-3.3 loop: 64 rule sets, racing 8 + 24 maps, hall of fame, probation and reference-relative scores.
- Individuals have 5 trees: priority, hold, upgrade, remove, place.
- Seeds: the locked Phase 2 GP rule (with `place` = −1), gp-2's rule, and the best hand rules from step 1.
- Reference for the hall: the locked Phase 2 GP rule.
- Runs until it converges (PLAN.md Phase 2 goal), with the same stop rule.

**Step 3: CMA-ES control.**
- **Same move set as gp-4 GP:** clean routes, removal and placement. That makes it a true control for GP.
- The linear policy gains two weighted sums: `remove` (over the removal inputs) and `place` (over the placement inputs). Its texts are therefore 5-tree, which also turns clean routes on.
- Tuned and stopped as `cma-1` was.
- Its x0 is the locked `cma_final` weights, with `remove` and `place` sums starting negative (never act).

**Step 4: final selection, test and PPO head-to-head.** As in Phase 2, on fresh blocks (below). The comparisons on the test block 6100–6199 are fixed now, before anything is played, with a Holm correction across them:

| # | Comparison | Question |
|---|---|---|
| 1 | gp-4 GP final − locked Phase 2 GP rule | Did gp-4 improve the agent? (headline) |
| 2 | gp-4 GP final − the same rule with `place` forced to −1 | How much of its score comes from lights and roundabouts? (Goal 4) |
| 3 | gp-4 GP final − gp-4 CMA-ES final | PLAN.md success criterion |
| 4 | gp-4 GP final − hand rule | PLAN.md success criterion |

- Also reported descriptively: the separated rule, the gp-4 CMA-ES final with `place` at −1, and the best step-1 hand rule.
- That makes 7 policies × 100 maps, about 700 games.
- The PPO head-to-head on 8100–8199 is one comparison (sampled and deterministic), as in Phase 2.

## Maps

| Use | Maps | Notes |
|---|---|---|
| Training | LA 1–999 (rotating) | as before |
| Stop-rule validation | LA 1500–1549 | as before, comparable with Phase 2 |
| Hand tests (step 1) | LA 3100–3199 | unused by anyone |
| Final selection | LA 5100–5299 (200) | unused (Mohammad used only 5000–5009) |
| Test, once | LA 6100–6199 (100) | unused (Mohammad used only 6000–6009) |
| PPO head-to-head, once | LA 8100–8199 (100) | unused (Mohammad used only 8000–8009); agree with him before either side plays |

## Constraints

- Deterministic, as now: games are identical across processes, and choices are made by scores, then list order.
- Bump the engine's `CODE_VERSION`, so the cache never mixes old and new games.
- 10 workers for long runs, and the keep-awake handling as in Phase 2.
- Commits under the repo's git identity (Aya), with no Claude attribution, on branch `gp4`, never pushed unless asked. Do not commit the other session's uncommitted files (`EXPERIMENTS.md` edits, `final/RECAP.md`).
- Record everything in EXPERIMENTS.md as before: best (validation) next to average (all 64 rule sets).

## Left to the builder

- Exact feature formulas, radii and thresholds (trigger interval, "stopped" threshold, candidate cap).
- How the "joins separated routes" check is computed.
- Whether `place` is one tree with an `is_roundabout` input or two trees. One tree is the default.
- How the CMA-ES vector is extended.
- Tests: the old-text identity test (required), placement and routing unit tests, and a smoke run.
