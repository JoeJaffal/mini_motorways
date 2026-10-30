# Evolved Rules Phase 1 (Skeleton + Hand Rule) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the hand-written Mini Motorways agent that the Phase 2 genetic programming will later evolve. It has a host client, map parser, A* route candidates, draw executor, replay logging, event loop and the hand-written rule. Prove it plays replay-valid games scoring about 140+ trips on LA seeds 2000–2019.

**Architecture:** Python drives one C# headless `TrafficHost` process per worker over line-delimited JSON. Each reply's observation is parsed into an immutable `CityState`. On game events the agent generates A* route candidates and scores them with a `Policy` object. The hand rule now, and evolved trees in Phase 2, both implement the same four methods. The agent executes the chosen routes as straight `draw` strokes, each followed by exactly 20 ticks, and logs every command in the `AiReplayRecording` schema.

**Tech Stack:** Python 3.12 (`py -3.12`), numpy, scipy, pytest, .NET 8 SDK (`dotnet`), headless host Release build. DEAP and cma are installed now but first used in Phase 2.

**Spec:** [evolved_rules/PLAN.md](../PLAN.md). Read sections 3, 3.5, 6 and 7 before starting any task.

**Out of scope (Phase 2 plan):** removal candidates and the Remove decision, the full ~25-terminal feature set, the GP loop, the CMA-ES smoke test and control, and other cities.

## Global Constraints

- **Never commit or stage.** The user commits manually. Every "Checkpoint" step ends with `git status`, nothing more.
- **Do not modify shared code:** nothing under `simulation/`, `scripts/`, `legacy/`, `docs/` or root files. All new code lives in `evolved_rules/`.
- Generated files (runs, replays, verifier build) go in `output/evolved_rules/` at the repo root. `/output/` is gitignored; `evolved_rules/output/` would not be.
- Rules: `version="OriginalReference"`, `scenario="LosAngeles"`, variation `SameMap` (the default). Assert `observation.version == "OriginalReference"` and `unlimitedConstruction == false` after reset.
- Every gameplay command is followed by `{"command":"step","ticks":20}`. Waiting is a bare `step` 20, logged as command `wait`. `step` without `ticks` advances 1 tick, so always send `ticks`.
- Allowed commands: `draw`, `build` with `tool="Remove"` (exact casing), `upgrade`, `step`. Never `connect`, `reference` (except the privileged diagnostic baseline in Task 7, which is never recorded), `driveway`, `motorway` or lab scenarios.
- Do not read these observation fields: `scheduledSpawns`, `randomAlgorithm`, `randomDraws`, `upgradeAt`, `plannedDemandMultiplier`, offer fields other than `type`/`amount`/`roads`, vehicle `route`/`returnRoute`, `feasibleDemandInterval`, `feasibilityVerified`, `originalDemandInterval` (excluded until decided, PLAN section 9).
- Episode cap 3600 simulated seconds, enforced by the agent. Host `terminated` = game lost. Host `truncated` = scenario rejected: raise, never score it.
- Determinism: never let iteration over a `set` of strings or `hash(str)` decide order. Break every tie with an explicit key such as (score, y, x, id). Run workers with `PYTHONHASHSEED=0`.
- Host DLL: `simulation/Headless/bin/Release/net8.0/TrafficHost.dll`, overridable with env var `EVOLVED_RULES_HOST_DLL`. Build with `dotnet build simulation/Headless -c Release`.
- Grid: 50 × 30, flat index `k = y*50 + x`. Directions d = 0..7 are E, SE, S, SW, W, NW, N, NE = `(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)`, with +y going down rows. Playable iff `xMin ≤ x < xMax and yMin ≤ y < yMax`.
- Enum codes: terrain 0 land, 1 water, 2 blocked. Infrastructure 0 None, 1 Road, 2 Bridge, 3 Roundabout, 4 TrafficLight. `buildingKinds` 0 none, 1 house, 2 shop.
- All commands run from the repo root `mini_motorways/`. Python is `.venv\Scripts\python.exe`, written below as `PY`.

## Review Focus

1. **A stroke runs out of road tiles mid-route**, because stock fell between planning and drawing. The executor must stop the route cleanly, keep the partial roads and not loop. Test: `test_execute_route_stops_when_stock_runs_out` (Task 4).
2. **Host hang or crash:** a timeout or broken pipe must raise `HostError`, never count as a lost game. Test: `test_call_times_out_and_raises` (Task 1).
3. **Shared-lot shops:** two shops of different colours on one footprint with two entrances. Each must be routed to only by its own colour, and either entrance counts. Test: `test_shared_lot_entrances_are_per_colour` (Task 2).
4. **A house that spawned already linked to a road:** routing from it must keep its driveway direction and never re-point it. Test: `test_linked_house_keeps_driveway` (Task 3).
5. **Water with zero bridge items in stock:** a route needing a new bridge span must not be proposed, but continuing an existing bridge span must still be allowed. Test: `test_no_new_span_without_bridge_stock` (Task 3).

---

## File Structure

```text
evolved_rules/
  __init__.py
  requirements.txt     pinned packages
  host.py              Host process client (Task 1)
  state.py             CityState, Building, Offer, parse_observation, graph queries (Task 2)
  candidates.py        Stroke, RouteCandidate, unserved_targets, route_candidates, split_strokes (Task 3)
  session.py           GameSession: command/wait/step bookkeeping + Recorder (Task 4)
  executor.py          execute_route, take_offer (Task 4)
  verify.py            build and run the headless replay verifier (Task 5)
  features.py          candidate/global/offer feature dicts (Task 6)
  rules.py             Policy protocol, HandRule, DoNothing (Task 6)
  agent.py             EventTracker, decide, play_game, GameResult (Task 6)
  evaluate.py          CLI: parallel seeds, baselines, summary.json (Task 7)
  tests/
    __init__.py
    conftest.py        `host` marker, `host` fixture (skips if DLL missing)
    helpers.py         make_obs, house, shop synthetic builders (Task 2)
    test_host.py  test_state.py  test_candidates.py  test_session.py
    test_verify.py  test_agent.py  test_evaluate.py
```

---

### Task 1: Environment and host client

**Files:**
- Create: `evolved_rules/__init__.py` (empty), `evolved_rules/requirements.txt`, `evolved_rules/host.py`, `evolved_rules/tests/__init__.py`, `evolved_rules/tests/conftest.py`
- Test: `evolved_rules/tests/test_host.py`

**Interfaces:**
- Produces: `class HostError(RuntimeError)`, `class ScenarioRejected(HostError)`. `default_host_dll() -> pathlib.Path`. `class Host(dll: Path | None = None, timeout: float = 30.0)` with `call(**request) -> dict`, `reset(seed: int, scenario: str = "LosAngeles") -> dict`, `close() -> None` and context-manager support. Pytest marker `host` and a fixture `host` that yields a started `Host` (skipped if the DLL is missing).

- [ ] **Step 1: Create the venv, requirements and Release build**

`evolved_rules/requirements.txt`:
```text
numpy==2.5.4
scipy==1.18.1
deap==1.4.4
cma==4.5.0
pytest
```
Run: `py -3.12 -m venv .venv` then `.venv\Scripts\python.exe -m pip install -r evolved_rules/requirements.txt` then `dotnet build simulation/Headless -c Release`.
Expected: build succeeds, `simulation/Headless/bin/Release/net8.0/TrafficHost.dll` exists, and `git check-ignore .venv simulation/Headless/bin` prints both paths.

- [ ] **Step 2: Write the failing tests**

```python
# evolved_rules/tests/test_host.py
import pytest
from evolved_rules.host import Host, HostError

@pytest.mark.host
def test_reset_returns_original_la(host):
    r = host.reset(1000)
    o = r["observation"]
    assert o["version"] == "OriginalReference" and o["unlimitedConstruction"] is False
    assert o["time"] == 0 and o["inventory"] == [25, 1, 0, 0, 0, 0]
    assert (o["width"], o["height"]) == (50, 30)

@pytest.mark.host
def test_step_20_advances_one_second(host):
    host.reset(1000)
    r = host.call(command="step", ticks=20)
    assert abs(r["observation"]["time"] - 1.0) < 1e-9

@pytest.mark.host
def test_error_reply_raises(host):
    host.reset(1000)
    with pytest.raises(HostError):
        host.call(command="nonsense")

def test_call_times_out_and_raises(tmp_path):
    # A "host" that never answers: python sleeping. Host must raise HostError, not hang.
    h = Host.__new__(Host)
    h._start(["py", "-3.12", "-c", "import time; time.sleep(60)"], timeout=0.5)
    with pytest.raises(HostError):
        h.call(command="observe")
    h.close()
```

`conftest.py` registers marker `host` and defines fixture `host`, which does `pytest.skip` when `default_host_dll()` does not exist, otherwise yields `Host()` and closes it.

- [ ] **Step 3: Run to verify they fail**

Run: `PY -m pytest evolved_rules/tests/test_host.py -v`
Expected: FAIL / ERROR with `ModuleNotFoundError: evolved_rules.host`.

- [ ] **Step 4: Implement `evolved_rules/host.py`**

- `Host.__init__(dll=None, timeout=30.0)` calls `self._start(["dotnet", str(dll or default_host_dll())], timeout)`.
- `_start(argv, timeout)` launches a `Popen` with text pipes and `CREATE_NEW_PROCESS_GROUP` on Windows, as Mohammad's `training/environment.py` does. A daemon reader thread puts stdout lines on a `queue.Queue`.
- `call` writes `json.dumps(request) + "\n"`, flushes, then `queue.get(timeout=...)`. It raises `HostError` on `queue.Empty`, EOF, `BrokenPipeError`/`OSError` or a reply containing `"error"` (include the last stderr lines in the message).
- `reset` sends `command="reset", version="OriginalReference", scenario=..., seed=...`. It raises `ScenarioRejected` if `truncated`, and `HostError` if the version is wrong or construction is unlimited.
- `close` sends `{"command":"quit"}`, waits 5 s, then kills. It is safe to call twice.

- [ ] **Step 5: Run to verify they pass**

Run: `PY -m pytest evolved_rules/tests/test_host.py -v`
Expected: 4 passed.

- [ ] **Step 6: Checkpoint (no commit)**

Run: `git status --short`. Expected: only `?? evolved_rules/` (plus nothing new outside it).

---

### Task 2: Observation parser and road graph

**Files:**
- Create: `evolved_rules/state.py`, `evolved_rules/tests/helpers.py`
- Test: `evolved_rules/tests/test_state.py`

**Interfaces:**
- Consumes: raw observation dicts (from `Host` replies).
- Produces, in `state.py`:
  - `W = 50`, `H = 30`, `DIRS: tuple[tuple[int,int], ...]` (the order in Global Constraints), `Cell = tuple[int, int]`.
  - `@dataclass(frozen=True) Building(id: int, color: int, is_house: bool, cell: Cell, width: int, height: int, access: tuple[Cell, ...], access_dirs: tuple[int, ...], demand: int, reserved: int, capacity: int, overcrowded_for: float, upgraded: bool)`. For a house, `access == (cell,)` and `access_dirs == (drivewayDirection,)`. For a shop, `access` comes from `entrances`, falling back to `(entrance,)` when that list is empty, and `access_dirs` from `entranceDirections`, falling back to `drivewayDirection`. Property `outside -> tuple[Cell, ...]` returns access + DIRS[dir].
  - `@dataclass(frozen=True) Offer(index: int, type: int, amount: int, roads: int)` with property `road_value = roads + (amount if type == 0 else 0)`.
  - `@dataclass(frozen=True) CityState` with:
    - scalars `time: float`, `trips: int`, `failed: bool`, `inventory: tuple[int, ...]`, `offers: tuple[Offer, ...]`, `bounds: tuple[int,int,int,int]`;
    - numpy `(30, 50)` int arrays `terrain`, `infra`, `conn`, `pending`, `kinds`;
    - `buildings: tuple[Building, ...]` sorted by id;
    - `vehicles_busy: dict[int, int]` (colour → cars not `Home`) and `vehicles_waiting: tuple[float, ...]`.
  - `CityState` methods:
    - `playable(c) -> bool`;
    - `houses() / shops() -> tuple[Building, ...]`;
    - `component(c) -> frozenset[Cell]`: BFS over `conn` bits, skipping cells with `pending == 1`;
    - `house_connected(h) -> bool`: the component of `h.cell` contains an access cell of a shop with `h.color`;
    - `shop_served(s) -> bool`: some same-colour house is connected to one of `s.access`;
    - `road_cell(c) -> bool`: infra is 1 or 2 and the cell is not pending.
  - `parse_observation(obs: dict) -> CityState`. It raises `ValueError` if width/height ≠ 50/30 or a colour is outside 0..7. It never reads the excluded fields.
- Produces, in `tests/helpers.py`:
  - `house(id, color, x, y, dir) -> dict` and `shop(id, color, x, y, w, h, entrances: list[tuple[int,int,int]]) -> dict`, both building dicts in host JSON shape;
  - `make_obs(buildings=(), roads: dict[Cell, int] = {}, terrain: dict[Cell, int] = {}, infra: dict[Cell, int] = {}, pending=(), inventory=(25,1,0,0,0,0), bounds=(0,0,50,30), time=0.0, offers=(), vehicles=()) -> dict`. It returns a full observation with consistent `buildingKinds`/`buildingColors`. A key in `roads` is a cell and its value is that cell's link mask. `infra` defaults to 1 for any cell in `roads` that is not a building cell.

- [ ] **Step 1: Write the failing tests**

```python
from evolved_rules.state import parse_observation, DIRS
from evolved_rules.tests.helpers import make_obs, house, shop

E, W_ = 0, 4
# Standard layout used by Tasks 2-3: shop footprint x 14-15, y 11-13, entrance (15,13) facing E -> outside (16,13);
# house (20,13) with driveway W -> outside (19,13). A direct road is (19..16, 13).
def _layout(**kw):
    return make_obs(buildings=[house(1, 0, 20, 13, W_), shop(0, 0, 14, 11, 2, 3, [(15, 13, E)])], **kw)

def test_house_and_shop_access_cells():
    s = parse_observation(_layout())
    h, sh = s.houses()[0], s.shops()[0]
    assert h.access == ((20, 13),) and h.outside == ((19, 13),)
    assert sh.access == ((15, 13),) and sh.outside == ((16, 13),)

def test_connected_via_links():
    roads = {(20, 13): 1 << 4, (15, 13): 1 << 0}
    for x in range(16, 20):
        roads[(x, 13)] = (1 << 0) | (1 << 4)
    s = parse_observation(_layout(roads=roads))
    assert s.house_connected(s.houses()[0]) and s.shop_served(s.shops()[0])

def test_adjacent_unlinked_roads_are_not_connected():
    o = make_obs(roads={(5, 5): 0, (6, 5): 0})
    s = parse_observation(o)
    assert s.component((5, 5)) == frozenset({(5, 5)})

def test_pending_cells_are_skipped():
    o = make_obs(roads={(5, 5): 1 << 0, (6, 5): (1 << 4) | (1 << 0), (7, 5): 1 << 4}, pending=[(6, 5)])
    assert (7, 5) not in parse_observation(o).component((5, 5))

def test_shared_lot_entrances_are_per_colour():
    lot = [shop(0, 0, 10, 10, 3, 3, [(10, 11, W_)]), shop(1, 2, 10, 10, 3, 3, [(12, 11, E)])]
    o = make_obs(buildings=lot + [house(2, 2, 5, 11, E)],
                 roads={(5, 11): 1 << 0, **{(x, 11): (1 << 0) | (1 << 4) for x in range(6, 9)},
                        (9, 11): (1 << 0) | (1 << 4), (10, 11): 1 << 4})
    s = parse_observation(o)
    # colour-2 house reaches the colour-0 entrance only: not connected
    assert not s.house_connected(next(b for b in s.houses()))

def test_parse_ignores_excluded_fields():
    o = _layout()
    for k in ["scheduledSpawns", "randomAlgorithm", "randomDraws"]:
        o.pop(k, None)
    for b in o["buildings"]:
        for k in ["upgradeAt", "plannedDemandMultiplier", "feasibleDemandInterval",
                  "feasibilityVerified", "originalDemandInterval"]:
            b.pop(k, None)
    parse_observation(o)  # must not raise

def test_rejects_wrong_grid():
    o = make_obs(); o["width"] = 40
    import pytest
    with pytest.raises(ValueError):
        parse_observation(o)
```

(`make_obs` must include every non-excluded field that `parse_observation` reads, so these tests pass without the host.)

- [ ] **Step 2: Run to verify they fail**

Run: `PY -m pytest evolved_rules/tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: evolved_rules.state`.

- [ ] **Step 3: Implement `evolved_rules/state.py` and `tests/helpers.py`**

Arrays come from the flat lists via `np.asarray(...).reshape(30, 50)`. Use plain BFS with a deque, visiting neighbours in DIRS order.

- [ ] **Step 4: Add a host-backed test and run all**

```python
@pytest.mark.host
def test_parses_real_reset(host):
    s = parse_observation(host.reset(1000)["observation"])
    x0, y0, x1, y1 = s.bounds
    assert 0 <= x0 < x1 <= 50 and 0 <= y0 < y1 <= 30
    assert len(s.houses()) >= 1 and len(s.shops()) >= 1
    assert all(s.playable(b.cell) for b in s.buildings)
```
Run: `PY -m pytest evolved_rules/tests/test_state.py -v`
Expected: 8 passed.

- [ ] **Step 5: Checkpoint (no commit)** with `git status --short`. Expected: only `?? evolved_rules/`.

---

### Task 3: Route candidates (A* following the draw rules) and stroke splitting

**Files:**
- Create: `evolved_rules/candidates.py`
- Test: `evolved_rules/tests/test_candidates.py`

**Interfaces:**
- Consumes: `CityState`, `Building`, `DIRS` from Task 2.
- Produces:
  - `@dataclass(frozen=True) Stroke(x: int, y: int, to_x: int, to_y: int)` with method `request() -> dict` returning `{"command":"draw","x":..,"y":..,"toX":..,"toY":..}`.
  - `@dataclass(frozen=True) RouteCandidate(kind: str, house_id: int, shop_ids: tuple[int, ...], path: tuple[Cell, ...], tiles_needed: int, bridges_needed: int, turns: int, new_junctions: int, shared_cells: int, strokes: tuple[Stroke, ...])`. `kind` is one of `"attach"`, `"direct"`, `"separated"`. `path[0]` is always the house cell.
  - `unserved_targets(state) -> list[tuple[Building, tuple[Building, ...]]]`. It returns (house, same-colour shops) for every house with `not house_connected` that has at least one same-colour shop. Then, for every shop with `not shop_served` whose colour has houses, it adds (nearest same-colour house by Manhattan distance from `shop.access[0]`, then lowest id, `(shop,)`), skipping houses already listed. The house entries are ordered by house id, then the shop entries by shop id.
  - `route_candidates(state, house, shops, planned: frozenset[Cell] = frozenset()) -> list[RouteCandidate]`. It returns at most 3 candidates, dropping duplicate paths, sorted by `(tiles_needed, len(path), KIND_ORDER[kind])` with `KIND_ORDER = {"attach":0,"direct":1,"separated":2}`. `planned` cells are treated as road already (for later routes in the same decision).
  - `split_strokes(path) -> tuple[Stroke, ...]`: one stroke per maximal run of an identical step direction.

- [ ] **Step 1: Write the failing tests**

```python
from evolved_rules.state import parse_observation
from evolved_rules.candidates import route_candidates, split_strokes, unserved_targets, Stroke
from evolved_rules.tests.helpers import make_obs, house, shop
E, S, W_ = 0, 2, 4

def _layout(**kw):  # same layout as Task 2: entrance (15,13) facing E -> outside (16,13)
    return make_obs(buildings=[house(1, 0, 20, 13, W_), shop(0, 0, 14, 11, 2, 3, [(15, 13, E)])], **kw)

def test_split_strokes_merges_straight_runs():
    path = ((0, 0), (1, 0), (2, 0), (3, 1), (4, 2), (4, 3))
    assert split_strokes(path) == (Stroke(0, 0, 2, 0), Stroke(2, 0, 4, 2), Stroke(4, 2, 4, 3))

def test_direct_route_ends_on_entrance_outside_cell():
    s = parse_observation(_layout())
    c = next(c for c in route_candidates(s, s.houses()[0], s.shops()) if c.kind == "direct")
    assert c.path == ((20, 13), (19, 13), (18, 13), (17, 13), (16, 13)) and c.tiles_needed == 4

def test_blocked_terrain_and_buildings_avoided():
    s = parse_observation(_layout(terrain={(18, y): 2 for y in range(30) if y != 20}))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert (18, 20) in c.path and all(s.terrain[y, x] != 2 for x, y in c.path)
    assert all(s.kinds[y, x] == 0 for x, y in c.path[1:])

def test_attach_prefers_existing_same_colour_road():
    roads = {(15, 13): 1 << 0, (16, 13): (1 << 4) | (1 << 0), (17, 13): 1 << 4}
    s = parse_observation(_layout(roads=roads))
    c = next(c for c in route_candidates(s, s.houses()[0], s.shops()) if c.kind == "attach")
    assert c.path[-1] == (17, 13) and c.tiles_needed == 2  # builds (19,13),(18,13)

def test_no_diagonal_crossing_existing_diagonal():
    # existing SE link (17,12)->(18,13) forbids a NE-SW step (18,12)<->(17,13) in that 2x2 block
    s = parse_observation(_layout(roads={(17, 12): 1 << 1, (18, 13): 1 << 5}))
    for c in route_candidates(s, s.houses()[0], s.shops()):
        steps = list(zip(c.path, c.path[1:]))
        assert ((18, 12), (17, 13)) not in steps and ((17, 13), (18, 12)) not in steps

def test_no_new_span_without_bridge_stock():
    river = {(18, y): 1 for y in range(30)}
    s0 = parse_observation(_layout(terrain=river, inventory=(25, 0, 0, 0, 0, 0)))
    assert route_candidates(s0, s0.houses()[0], s0.shops()) == []
    s1 = parse_observation(_layout(terrain=river, inventory=(25, 0, 0, 0, 0, 0),
                                   infra={(18, 13): 2}, roads={(18, 13): 0}))
    c = route_candidates(s1, s1.houses()[0], s1.shops())[0]
    assert (18, 13) in c.path and c.bridges_needed == 0

def test_new_span_uses_one_bridge_item():
    s = parse_observation(_layout(terrain={(18, y): 1 for y in range(30)}))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert c.bridges_needed == 1

def test_no_diagonal_into_water():
    s = parse_observation(_layout(terrain={(18, y): 1 for y in range(30)}))
    for c in route_candidates(s, s.houses()[0], s.shops()):
        for a, b in zip(c.path, c.path[1:]):
            if s.terrain[a[1], a[0]] == 1 or s.terrain[b[1], b[0]] == 1:
                assert a[0] == b[0] or a[1] == b[1]

def test_linked_house_keeps_driveway():
    # house driveway W, already linked to road at (19,13): first step must be W
    s = parse_observation(_layout(roads={(20, 13): 1 << 4, (19, 13): 1 << 0}))
    for c in route_candidates(s, s.houses()[0], s.shops()):
        assert c.path[1] == (19, 13)

def test_unlinked_house_may_leave_in_any_direction():
    s = parse_observation(make_obs(buildings=[house(1, 0, 20, 13, E), shop(0, 0, 14, 11, 2, 3, [(15, 13, E)])]))
    assert route_candidates(s, s.houses()[0], s.shops())[0].path[1] == (19, 13)

def test_respects_playable_bounds():
    s = parse_observation(_layout(bounds=(9, 7, 22, 14)))
    for c in route_candidates(s, s.houses()[0], s.shops()):
        assert all(9 <= x < 22 and 7 <= y < 14 for x, y in c.path)

def test_unserved_targets_order_and_shop_without_house():
    o = make_obs(buildings=[house(3, 0, 20, 13, W_), house(1, 0, 20, 15, W_),
                            shop(0, 0, 14, 11, 2, 3, [(15, 13, E)])])
    t = unserved_targets(parse_observation(o))
    assert [h.id for h, _ in t] == [1, 3]

def test_deterministic_across_calls():
    s = parse_observation(_layout())
    a = route_candidates(s, s.houses()[0], s.shops()); b = route_candidates(s, s.houses()[0], s.shops())
    assert a == b
```

- [ ] **Step 2: Run to verify they fail**

Run: `PY -m pytest evolved_rules/tests/test_candidates.py -v`
Expected: FAIL with `ModuleNotFoundError: evolved_rules.candidates`.

- [ ] **Step 3: Implement `evolved_rules/candidates.py`**

Use one A* routine with three cost models and three target sets. The search state is `(cell, spans_used)`, where `spans_used ≤ inventory[1]`. Heap entries are `(f, g, y, x, spans_used)` for determinism. Use an admissible octile heuristic with the minimum step cost.

The rules, from PLAN section 3.3, which mirror `TrafficWorld.cs` `DrawRoad`/`Build`/`Connect`:

```text
start: path[0] = house.cell
  if state.conn[house] == 0: first step to any neighbour n
  else: first step only to house.outside[0]
enterable(n): playable(n)
              and terrain[n] != 2
              and kinds[n] == 0
              and pending[n] == 0
              and infra[n] != 3
step u->n diagonal: forbidden if either cell is water,
                    or the other diagonal of the 2x2 block is linked in conn
water n: allowed if infra[n] == 2 (existing bridge), or an orthogonal neighbour is an
         existing bridge or the previous path cell is water (same span);
         otherwise it starts a new span: spans_used + 1 <= inventory[1]
step cost: base = 1.414 if diagonal else 1.0
           x 0.15 if road_cell(n) or n in planned
           + 0.05
           + 0.5 if n is an existing road cell whose link count (popcount of conn) >= 2
                 (it would become a junction of degree >= 3)
           + 3.0 in "separated" mode if n lies in a component serving another colour but not house.color
targets:
  direct   = each shop's outside cells
  attach   = direct targets + every road cell of components that contain an access cell
             of a same-colour shop
  separated = attach targets
tiles_needed   = count of path[1:] cells that are not road and not in planned
bridges_needed = spans_used at the goal
```

`turns` counts direction changes along the path. `new_junctions` counts existing road cells on the path with popcount ≥ 2. `shared_cells` counts path cells in components serving other colours. A component's served colours are the colours of shops whose access cells lie in it.

Drop any candidate with `tiles_needed > inventory[0]`. The Hold rule (Task 6) handles the reserve, not this function.

- [ ] **Step 4: Run to verify they pass**

Run: `PY -m pytest evolved_rules/tests/test_candidates.py -v`
Expected: 13 passed.

- [ ] **Step 5: Checkpoint (no commit)** with `git status --short`.

---

### Task 4: Game session, replay recorder and executor

**Files:**
- Create: `evolved_rules/session.py`, `evolved_rules/executor.py`
- Test: `evolved_rules/tests/test_session.py`

**Interfaces:**
- Consumes: `Host` (Task 1), `parse_observation`/`CityState` (Task 2), `RouteCandidate`/`Stroke` (Task 3).
- Produces:
  - `class Recorder(seed: int, scenario: str = "LosAngeles")` with public `actions: list[dict]` and:
    - `log(request: dict | None, accepted: bool, obs: dict) -> None`. `None` means wait. It appends one action: `command` (`"wait"` for None), `tool` (or `""`), `x`, `y`, `toX`, `toY`, `id`, `choice` (missing → 0), `ticks=20`, `accepted`, `afterTrips=obs["tripsCompleted"]`, `afterTime=obs["time"]`.
    - `recording(final_obs: dict, source: str) -> dict`: schema 1, `version="OriginalReference"`, `scenario`, `variation="SameMap"`, `seed`, `score=final tripsCompleted`, `duration=final time`, `terminated=final failed`, `truncated=False`, `actions`, `source`, `policySchema="evolved-rules-v1"`.
    - `save(path, final_obs, source) -> None`, writing UTF-8 JSON.
  - `class GameSession(host: Host, seed: int, cap_s: float = 3600.0, record: bool = True)` with:
    - `reset() -> CityState`;
    - `command(request: dict) -> tuple[bool, CityState]`: sends the request, then `step` 20, logs, and returns `accepted` from the command reply;
    - `wait() -> CityState`;
    - attributes `state: CityState`, `raw: dict` (last observation), `commands: int`, `rejected: int`, `action_counts: dict[str, int]` (key = `tool` if present, else `command`; waits → `"wait"`), `wait_sum: float`, `wait_n: int`, `max_wait: float` (from every vehicle's `waiting` after each step), `terminated: bool`, `done: bool` (terminated or `time ≥ cap_s`), `recorder: Recorder | None`.
    - Calling `command` or `wait` when `done` raises `RuntimeError`.
  - `execute_route(session, cand: RouteCandidate) -> bool`. It sends `cand.strokes` in order, stopping early if `session.done`, or if the road stock is below the next stroke's new tiles, or if the stroke fails to create its links. It returns `session.state.house_connected(house)` for `cand.house_id`.
  - `take_offer(session, choice: int) -> bool`.

- [ ] **Step 1: Write the failing tests**

```python
import json, pytest
from evolved_rules.session import Recorder, GameSession
from evolved_rules.executor import execute_route, take_offer
from evolved_rules.candidates import unserved_targets, route_candidates, RouteCandidate, Stroke

def test_recorder_logs_wait_and_remove_casing():
    r = Recorder(7)
    r.log(None, True, {"tripsCompleted": 0, "time": 1.0})
    r.log({"command": "build", "tool": "Remove", "x": 3, "y": 4}, False, {"tripsCompleted": 0, "time": 2.0})
    a = r.recording({"tripsCompleted": 0, "time": 2.0, "failed": False}, "test")["actions"]
    assert a[0]["command"] == "wait" and a[0]["ticks"] == 20
    assert a[1]["tool"] == "Remove" and a[1]["accepted"] is False and a[1]["afterTime"] == 2.0

@pytest.mark.host
def test_wait_advances_and_logs(host):
    g = GameSession(host, 1000); g.reset()
    st = g.wait()
    assert st.time == 1.0 and g.commands == 1 and g.action_counts == {"wait": 1}

@pytest.mark.host
def test_first_route_connects_house(host):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    cand = route_candidates(s, h, shops)[0]
    assert execute_route(g, cand) is True
    assert all(a["ticks"] == 20 for a in g.recorder.actions)

@pytest.mark.host
def test_execute_route_stops_when_stock_runs_out(host):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    real = route_candidates(s, h, shops)[0]
    # Fake a candidate whose later strokes need far more tiles than the 25 in stock.
    long = RouteCandidate("direct", h.id, real.shop_ids, real.path, 999, 0, 0, 0, 0,
                          real.strokes + tuple(Stroke(0, y, 49, y) for y in range(3)))
    before = g.commands
    assert execute_route(g, long) in (True, False)
    assert g.commands - before <= len(real.strokes) + 1  # stopped, did not loop
```

- [ ] **Step 2: Run to verify they fail**

Run: `PY -m pytest evolved_rules/tests/test_session.py -v`
Expected: FAIL with `ModuleNotFoundError: evolved_rules.session`.

- [ ] **Step 3: Implement `session.py` and `executor.py`**

Before each stroke, `execute_route` counts the stroke's cells that are not yet road. If that is more than `state.inventory[0]`, it stops. After each stroke it checks that every consecutive pair in the stroke is linked in `conn`, and stops at the first missing link. It never retries automatically: the next decision re-plans.

- [ ] **Step 4: Run to verify they pass**

Run: `PY -m pytest evolved_rules/tests/test_session.py -v`
Expected: 4 passed.

- [ ] **Step 5: Checkpoint (no commit)** with `git status --short`.

---

### Task 5: Replay verifier

**Files:**
- Create: `evolved_rules/verify.py`
- Test: `evolved_rules/tests/test_verify.py`

**Interfaces:**
- Consumes: recordings saved by `Recorder.save` (Task 4).
- Produces: `VERIFIER_COMMIT = "e6119eb"`, `VERIFIER_DIR = <repo>/output/evolved_rules/verifier`. `build_verifier(force: bool = False) -> Path`, which returns the verifier DLL path. `verify_recording(path: Path) -> tuple[bool, str]`, which returns (passed, stdout + stderr).

- [ ] **Step 1: Write the failing tests**

```python
import pytest, subprocess
from pathlib import Path
from evolved_rules.verify import build_verifier, verify_recording
from evolved_rules.session import GameSession
from evolved_rules.executor import execute_route
from evolved_rules.candidates import unserved_targets, route_candidates

@pytest.mark.host
def test_mohammad_best_game_passes(tmp_path):
    p = tmp_path / "best.json"
    p.write_bytes(subprocess.check_output(["git", "show",
        "upstream/mohammad:docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/best-game.json"]))
    ok, out = verify_recording(p)
    assert ok, out

@pytest.mark.host
def test_our_short_game_passes(host, tmp_path):
    g = GameSession(host, 1000); s = g.reset()
    h, shops = unserved_targets(s)[0]
    execute_route(g, route_candidates(s, h, shops)[0])
    for _ in range(60):
        g.wait()
    p = tmp_path / "ours.json"; g.recorder.save(p, g.raw, "test")
    ok, out = verify_recording(p)
    assert ok, out

@pytest.mark.host
def test_tampered_game_fails(host, tmp_path):
    g = GameSession(host, 1000); g.reset(); g.wait(); g.wait()
    rec = g.recorder.recording(g.raw, "test"); rec["actions"][-1]["afterTime"] += 5
    p = tmp_path / "bad.json"; import json; p.write_text(json.dumps(rec))
    assert verify_recording(p)[0] is False
```

- [ ] **Step 2: Run to verify they fail**

Run: `PY -m pytest evolved_rules/tests/test_verify.py -v`
Expected: FAIL with `ModuleNotFoundError: evolved_rules.verify`.

- [ ] **Step 3: Implement `evolved_rules/verify.py`**

`build_verifier` builds only once:
1. Run `git archive --format=tar -o <VERIFIER_DIR>/src.tar e6119eb simulation/Assets/Simulation simulation/Headless`.
2. Extract it with `tarfile` into `VERIFIER_DIR`.
3. Run `dotnet build <VERIFIER_DIR>/simulation/Headless -c Release`.
4. Return `<VERIFIER_DIR>/simulation/Headless/bin/Release/net8.0/TrafficHost.dll`.

`verify_recording` runs `dotnet <dll> --verify-replay <abs path>` with a 120 s timeout. Pass = exit code 0 and `PASS` in stdout (PLAN section 6). Never check out a branch.

- [ ] **Step 4: Run to verify they pass**

Run: `PY -m pytest evolved_rules/tests/test_verify.py -v`
Expected: 3 passed. The first run builds the verifier, which takes about 1 minute. Check `git status --short`: still only `?? evolved_rules/`.

- [ ] **Step 5: Checkpoint (no commit)** with `git status --short`.

---

### Task 6: Features, policies, event trigger and game loop

**Files:**
- Create: `evolved_rules/features.py`, `evolved_rules/rules.py`, `evolved_rules/agent.py`
- Test: `evolved_rules/tests/test_agent.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces:
  - `features.py`:
    - `candidate_features(state, cand) -> dict[str, float]` with keys `tiles_needed`, `bridges_needed`, `path_len`, `turns`, `new_junctions`, `shared_cells`, `is_attach`, `is_direct`, `is_separated`;
    - `global_features(state) -> dict[str, float]` with keys `road_stock`, `bridge_stock`, `time`, `unserved_houses`;
    - `offer_features(offer) -> dict[str, float]` with keys `offer_roads` (= `Offer.road_value`), `amount`, `type_0`..`type_5`.
    - Phase 2 adds keys; it never renames these.
  - `rules.py`:
    - `class Policy(Protocol)` with `name: str` and the methods `priority(f) -> float`, `hold(g) -> float`, `upgrade(f) -> float`, `remove(f) -> float`.
    - `HandRule`: priority = `-tiles_needed`; hold = `4 - road_stock`; upgrade = `offer_roads`; remove = `-1.0`; `name = "hand"`.
    - `DoNothing`: `name = "nothing"`.
  - `agent.py`:
    - `FALLBACK_S = 10.0`, `OVERCROWD_EVENT_S = 20.0`, `MAX_ROUTES_PER_DECISION = 20`.
    - `class EventTracker` with `should_decide(state) -> bool`. It is true on the first call, on a new building id, when offers are present, when any shop's `overcrowded_for` crosses `OVERCROWD_EVENT_S` upward, when `upgraded` flips, when road stock rises, or when at least `FALLBACK_S` has passed since the last true.
    - `decide(session, policy) -> None`.
    - `@dataclass GameResult` with `trips: int`, `seconds: float`, `rejected_actions: int`, `commands: int`, `action_counts: dict`, `mean_car_wait: float`, `max_car_wait: float`, `terminated: bool`, `truncated: bool`, `scenario_seed: int`, `city: str`, `deterministic: bool`, `failed_shop: int | None`, `road_tiles_at_failure: int | None`, `recording: dict | None`. Method `summary() -> dict` returns everything except `recording`.
    - `play_game(host, seed, policy, cap_s=3600.0, record=True) -> GameResult`.

Decision procedure (`decide`):
1. If offers are pending, take the offer with the highest `policy.upgrade(offer_features)`, choosing the lower index on ties. An offer is always taken.
2. Repeat up to `MAX_ROUTES_PER_DECISION` times:
   - Generate candidates for every entry of `unserved_targets(session.state)`.
   - Pick the one with the highest `policy.priority`, breaking ties by target order, then candidate order.
   - Stop if there are none, or if `priority < policy.hold(global_features)`.
   - Otherwise `execute_route`.
3. Phase 1 never removes roads.

`play_game` resets, then loops: decide if `should_decide`, otherwise `wait()`, until `done`. `DoNothing` never decides. On termination, `failed_shop` is the id of the shop with the largest `overcrowded_for`, and `road_tiles_at_failure = inventory[0]`.

- [ ] **Step 1: Write the failing tests**

```python
import os, json, subprocess, sys, pytest
from evolved_rules.rules import HandRule, DoNothing
from evolved_rules.agent import EventTracker, play_game
from evolved_rules.state import parse_observation
from evolved_rules.tests.helpers import make_obs, house, shop

def test_hand_rule_values():
    r = HandRule()
    assert r.priority({"tiles_needed": 6}) == -6 and r.hold({"road_stock": 25}) == -21
    assert r.upgrade({"offer_roads": 30}) > r.upgrade({"offer_roads": 20}) and r.remove({}) < 0

def test_event_tracker():
    t = EventTracker()
    s0 = parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4)], time=5.0))
    assert t.should_decide(s0) is True
    assert t.should_decide(parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4)], time=6.0))) is False
    s2 = parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4), house(2, 0, 25, 13, 4)], time=7.0))
    assert t.should_decide(s2) is True
    assert t.should_decide(parse_observation(make_obs(buildings=[house(1, 0, 20, 13, 4), house(2, 0, 25, 13, 4)], time=17.0))) is True

@pytest.mark.host
def test_do_nothing_loses_around_140s(host):
    r = play_game(host, 2000, DoNothing())
    assert r.trips == 0 and r.terminated and 135 <= r.seconds <= 160

@pytest.mark.host
def test_hand_rule_scores_and_replays(host, tmp_path):
    from evolved_rules.verify import verify_recording
    r = play_game(host, 1000, HandRule(), cap_s=300.0)
    assert r.trips > 0 and all(a["ticks"] == 20 for a in r.recording["actions"])
    p = tmp_path / "g.json"; p.write_text(json.dumps(r.recording))
    assert verify_recording(p)[0]

@pytest.mark.host
def test_same_game_in_two_processes():
    code = ("from evolved_rules.host import Host;from evolved_rules.agent import play_game;"
            "from evolved_rules.rules import HandRule;import json;"
            "h=Host();r=play_game(h,1000,HandRule(),cap_s=200.0);h.close();"
            "print(json.dumps(r.recording['actions']))")
    outs = [subprocess.check_output([sys.executable, "-c", code],
                                    env={**os.environ, "PYTHONHASHSEED": str(s)}) for s in (1, 2)]
    assert outs[0] == outs[1]
```

- [ ] **Step 2: Run to verify they fail**

Run: `PY -m pytest evolved_rules/tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `features.py`, `rules.py`, `agent.py`**

- [ ] **Step 4: Run to verify they pass**

Run: `PY -m pytest evolved_rules/tests/test_agent.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the whole suite**

Run: `PY -m pytest evolved_rules/tests -v`
Expected: all passed.

- [ ] **Step 6: Checkpoint (no commit)** with `git status --short`.

---

### Task 7: Evaluation CLI, baselines and parallel runs

**Files:**
- Create: `evolved_rules/evaluate.py`
- Test: `evolved_rules/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `play_game`, `GameResult`, `HandRule`, `DoNothing`, `verify_recording`.
- Produces:
  - `parse_seeds(spec: list[str]) -> list[int]`: accepts `"1000"` and ranges `"2000-2019"`, inclusive, de-duplicated in order.
  - `run_reference(host, seed, cap_s) -> dict`: the privileged baseline. Every 10 s it sends `{"command":"reference"}`, then `step` 20, and always takes offer 0. It is never recorded and is marked `"privileged": true`.
  - `evaluate(policy_name: str, seeds: list[int], workers: int, run: str, verify: bool) -> dict`. It writes `output/evolved_rules/runs/<run>/summary.json`, `games.jsonl` (one `GameResult.summary()` per line) and `replays/<seed>.json`, and returns the summary.
  - Summary keys:
    - `config`: commit from `git rev-parse HEAD`, `dirty`, packages from `importlib.metadata` (numpy, scipy, deap, cma), `python`, `PYTHONHASHSEED`, `policy`, `seeds`, `cap_s`, `host_dll`;
    - `games`: a list of per-game summaries;
    - `aggregate`: mean, median, min, max and SD of trips and seconds, plus `verified_pass`/`verified_total`.
  - CLI: `PY -m evolved_rules.evaluate --policy {hand,nothing,reference} --seeds 1000 2000-2019 --workers 10 --run NAME [--verify] [--cap 3600]`. It refuses an existing run folder.
  - Parallelism: a `ProcessPoolExecutor(max_workers=workers, initializer=_init_worker)`. Each worker creates one long-lived `Host`. Jobs go one per seed, collected with `as_completed`. The parent sets `os.environ["PYTHONHASHSEED"] = "0"` before creating the pool.

- [ ] **Step 1: Write the failing tests**

```python
import json, pytest
from evolved_rules.evaluate import parse_seeds, evaluate

def test_parse_seeds():
    assert parse_seeds(["1000", "2000-2002", "1000"]) == [1000, 2000, 2001, 2002]

@pytest.mark.host
def test_evaluate_writes_summary(tmp_path, monkeypatch):
    monkeypatch.setattr("evolved_rules.evaluate.RUNS_DIR", tmp_path)
    s = evaluate("hand", [2000, 2001], workers=2, run="t", verify=True)
    assert [g["scenario_seed"] for g in s["games"]] == [2000, 2001]
    assert s["aggregate"]["verified_pass"] == 2
    for k in ["trips", "seconds", "rejected_actions", "commands", "action_counts", "mean_car_wait",
              "max_car_wait", "terminated", "truncated", "scenario_seed", "city", "deterministic",
              "failed_shop", "road_tiles_at_failure"]:
        assert k in s["games"][0]
    assert (tmp_path / "t" / "replays" / "2000.json").exists()
```

- [ ] **Step 2: Run to verify they fail**

Run: `PY -m pytest evolved_rules/tests/test_evaluate.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `evolved_rules/evaluate.py`** with `RUNS_DIR = <repo>/output/evolved_rules/runs`. Order `games` by seed in the input order.

- [ ] **Step 4: Run to verify they pass**

Run: `PY -m pytest evolved_rules/tests/test_evaluate.py -v`
Expected: 2 passed.

- [ ] **Step 5: Checkpoint (no commit)** with `git status --short`.

---

### Task 8: Phase 1 exit check

**Files:**
- Modify: `evolved_rules/PLAN.md`, section 7: add a "Phase 1 results" subsection under the phases table.

- [ ] **Step 1: Run the three baselines on the same seeds**

```text
PY -m evolved_rules.evaluate --policy hand      --seeds 1000 2000-2019 --workers 10 --run phase1-hand --verify
PY -m evolved_rules.evaluate --policy nothing   --seeds 1000 2000-2019 --workers 10 --run phase1-nothing
PY -m evolved_rules.evaluate --policy reference --seeds 1000 2000-2019 --workers 10 --run phase1-reference
```
Expected:
- `phase1-hand`: mean trips on 2000–2019 ≥ about 140, and `verified_pass == verified_total == 21`.
- `phase1-nothing`: 0 trips everywhere, lost at about 140–154 s.
- If the hand rule's mean is below 80, the skeleton is broken: stop and debug (superpowers:systematic-debugging). Between 80 and 140, report it and compare with the prototype per seed before tuning anything.

- [ ] **Step 2: Measure throughput and the hand-vs-prototype correlation**

From `phase1-hand/summary.json`, report games per hour (21 × 3600 ÷ wall seconds) and simulated seconds per wall second. Compute the Pearson correlation of hand-rule trips against the prototype's per-seed trips on 2000–2019. The prototype numbers are recorded in PLAN section 1 per range; if per-seed values are needed, re-run `scratchpad/greedy.py`.

- [ ] **Step 3: Record the results in PLAN.md**

In section 7, add a "Phase 1 results (date)" subsection with:
- a table of mean, median, min and max trips and survival for the hand rule, do-nothing and reference on seed 1000 and 2000–2019;
- the verification count, throughput and correlation;
- the run folder names and `git rev-parse HEAD`.
Mark the Phase 1 exit check as passed or failed.

- [ ] **Step 4: Final checkpoint (no commit)**

Run: `PY -m pytest evolved_rules/tests -q` and `git status --short`.
Expected: all tests pass, and `git status` shows only `?? evolved_rules/`. Then tell the user the phase is ready for them to commit.
