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
    # Ruling T3: with no roads, attach and direct find the same path and dedup keeps "attach".
    c = route_candidates(s, s.houses()[0], s.shops())[0]
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


# ---------------------------------------------------------------------------------------------
# Fix round 1: discriminating tests (each one fails when its rule is removed; see task-3-report.md)
# ---------------------------------------------------------------------------------------------
import pytest

import evolved_rules.candidates as cand
from evolved_rules.state import DIRS
from evolved_rules.candidates import path_links
N = 6


def _line(cells, extra=None):
    """Road mask dict linking consecutive cells; extra = {cell: mask} OR-ed in."""
    m = {}
    for a, b in zip(cells, cells[1:]):
        d = DIRS.index((b[0] - a[0], b[1] - a[1]))
        m[a] = m.get(a, 0) | (1 << d)
        m[b] = m.get(b, 0) | (1 << ((d + 4) % 8))
    for c, v in (extra or {}).items():
        m[c] = m.get(c, 0) | v
    return m


def _steps(c):
    return list(zip(c.path, c.path[1:]))


def _crosses(c, a, b):
    return (a, b) in _steps(c) or (b, a) in _steps(c)


# --- strokes ------------------------------------------------------------------------------------
def test_split_strokes_turn_at_first_cell():
    assert split_strokes(((0, 0), (1, 0), (2, 1))) == (Stroke(0, 0, 1, 0), Stroke(1, 0, 2, 1))


def test_stroke_request_shape():
    assert Stroke(1, 2, 3, 4).request() == {"command": "draw", "x": 1, "y": 2, "toX": 3, "toY": 4}


def test_path_links_are_order_independent_steps():
    p = ((0, 0), (1, 1), (1, 2))
    assert path_links(p) == frozenset({((0, 0), (1, 1)), ((1, 1), (1, 2))}) == path_links(tuple(reversed(p)))


# --- legality -----------------------------------------------------------------------------------
def test_crossing_rule_changes_the_route():
    b = [house(1, 0, 19, 11, W_), shop(0, 0, 14, 13, 2, 3, [(15, 14, E)])]
    s0 = parse_observation(make_obs(buildings=b))
    assert _crosses(route_candidates(s0, s0.houses()[0], s0.shops())[0], (18, 12), (17, 13))  # not vacuous
    # existing SE diagonal (17,12)->(18,13), both tiles pending removal: the links stay (TrafficWorld.cs:141)
    # but the cells cannot be entered, so cheap road cells cannot lure the route away from the crossing step
    s = parse_observation(make_obs(buildings=b, roads={(17, 12): 1 << 1, (18, 13): 1 << 5},
                                   pending=[(17, 12), (18, 13)]))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs and not any(_crosses(c, (18, 12), (17, 13)) for c in cs)


def _mx(c, mirror):  # x-mirror x' = 31 - x
    return (31 - c[0], c[1]) if mirror else c


def _md(d, mirror):  # mirrored direction: (dx, dy) -> (-dx, dy)
    return DIRS.index((-DIRS[d][0], DIRS[d][1])) if mirror else d


def _mmask(mask, mirror):
    return sum(1 << _md(d, mirror) for d in range(8) if (mask >> d) & 1)


def _two_route_decision(mirror=False):
    # colour 1 network: shop 4 access (12,11) facing E -> road (13,11)-(14,11)-(15,11)
    roads = {(12, 11): 1 << E, (13, 11): (1 << W_) | (1 << E), (14, 11): (1 << W_) | (1 << E), (15, 11): 1 << W_}
    m, md = (lambda c: _mx(c, mirror)), (lambda d: _md(d, mirror))
    o = make_obs(buildings=[house(1, 0, *m((13, 8)), md(1)), house(2, 1, *m((17, 9)), md(3)),
                            shop(3, 0, *m((19, 13)), 1, 1, [(*m((19, 13)), md(W_))]),
                            shop(4, 1, *m((12, 11)), 1, 1, [(*m((12, 11)), md(E))])],
                 roads={m(c): _mmask(v, mirror) for c, v in roads.items()},
                 terrain={m((16, 9)): 2, m((17, 10)): 2})
    return parse_observation(o)


@pytest.mark.parametrize("mirror", [False, True])  # mirrored: the crossing pair is looked up in the other order
def test_second_route_does_not_cross_planned_diagonal(mirror):
    s = _two_route_decision(mirror)
    m = lambda c: _mx(c, mirror)
    h1, h2 = s.houses()
    r1 = route_candidates(s, h1, (s.buildings[2],))[0]
    assert _crosses(r1, m((15, 10)), m((16, 11)))  # route 1 plans the diagonal (15,10)-(16,11) (mirrored)
    planned = frozenset(r1.path[1:])
    free = route_candidates(s, h2, (s.buildings[3],), planned)
    assert any(_crosses(c, m((16, 10)), m((15, 11))) for c in free)  # not vacuous: without links it crosses
    cs = route_candidates(s, h2, (s.buildings[3],), planned, planned_links=path_links(r1.path))
    assert cs and not any(_crosses(c, m((16, 10)), m((15, 11))) for c in cs)


def test_no_diagonal_into_or_out_of_water_when_diagonal_is_shorter():
    b = [house(1, 0, 20, 10, W_), shop(0, 0, 14, 13, 2, 3, [(15, 14, E)])]  # outside (16,14): pure SW diagonal
    s = parse_observation(make_obs(buildings=b, terrain={(18, y): 1 for y in range(30)}))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs
    for c in cs:
        for a, q in _steps(c):
            if s.terrain[a[1], a[0]] == 1 or s.terrain[q[1], q[0]] == 1:
                assert a[0] == q[0] or a[1] == q[1]


def test_playable_bounds_force_detour():
    wall = {(18, y): 2 for y in range(30) if y not in (8, 14)}  # gaps at y=8 (inside) and y=14 (outside)
    s = parse_observation(_layout(terrain=wall, bounds=(9, 7, 22, 14)))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs and all(all(9 <= x < 22 and 7 <= y < 14 for x, y in c.path) and (18, 8) in c.path for c in cs)


def test_pending_cell_not_entered():
    s = parse_observation(_layout(roads={(18, 13): 0}, pending=[(18, 13)]))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs and all((18, 13) not in c.path for c in cs)


def test_roundabout_cell_not_entered():
    s = parse_observation(_layout(roads={(18, 13): 0}, infra={(18, 13): 3}))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs and all((18, 13) not in c.path for c in cs)


def test_other_building_not_entered():
    s = parse_observation(make_obs(buildings=[house(1, 0, 20, 13, W_), house(2, 1, 18, 13, N),
                                              shop(0, 0, 14, 11, 2, 3, [(15, 13, E)])]))
    h = next(x for x in s.houses() if x.id == 1)
    cs = route_candidates(s, h, s.shops())
    assert cs and all((18, 13) not in c.path for c in cs)


def test_linked_house_keeps_driveway_when_shop_is_behind_it():
    b = [house(1, 0, 20, 13, W_), shop(0, 0, 23, 12, 2, 3, [(23, 13, W_)])]  # shop outside (22,13), east
    s = parse_observation(make_obs(buildings=b, roads={(20, 13): 1 << 4, (19, 13): 1 << 0}))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs and all(c.path[1] == (19, 13) for c in cs)


def test_house_driveway_never_onto_water():
    # the only exit is W onto water (19,13); SetHouseDriveway (TrafficWorld.cs:259) rejects a water outside cell
    blocked = {c: 2 for c in [(21, 12), (21, 13), (21, 14), (20, 12), (20, 14)]}
    s = parse_observation(_layout(terrain={**{(19, y): 1 for y in range(30)}, **blocked}))
    assert route_candidates(s, s.houses()[0], s.shops()) == []


def test_two_wide_river_is_one_span():
    s = parse_observation(_layout(terrain={(x, y): 1 for x in (17, 18) for y in range(30)},
                                  inventory=(25, 1, 0, 0, 0, 0)))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert c.bridges_needed == 1 and (17, 13) in c.path and (18, 13) in c.path


def test_orthogonal_existing_bridge_means_no_new_span():
    terrain = {**{(18, y): 1 for y in range(30)}, (19, 14): 2, (17, 14): 2}
    s = parse_observation(_layout(terrain=terrain, inventory=(25, 0, 0, 0, 0, 0),
                                  infra={(18, 14): 2}, roads={(18, 14): 0}))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs and cs[0].bridges_needed == 0 and (18, 13) in cs[0].path


def test_planned_water_cell_counts_as_bridge():
    s = parse_observation(_layout(terrain={(18, y): 1 for y in range(30)}, inventory=(25, 0, 0, 0, 0, 0)))
    cs = route_candidates(s, s.houses()[0], s.shops(), planned=frozenset({(18, 13)}))
    assert cs and cs[0].bridges_needed == 0


# --- junctions ----------------------------------------------------------------------------------
def test_following_existing_links_through_degree_two_cell_is_no_junction():
    # unconnected road (19,13)-(18,13)-(17,13) on the straight line: the path adds links only at its ends
    s = parse_observation(_layout(roads=_line([(19, 13), (18, 13), (17, 13)])))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert c.path == ((20, 13), (19, 13), (18, 13), (17, 13), (16, 13)) and c.tiles_needed == 1
    assert c.new_junctions == 0


def test_riding_into_shop_network_is_no_junction():
    # demo1 case 1a: direct rides (17,13)->(16,13) over an existing link; (16,13) stays at degree 2
    roads = {(15, 13): 1 << 0, (16, 13): (1 << 4) | (1 << 0), (17, 13): 1 << 4}
    s = parse_observation(_layout(roads=roads))
    cs = route_candidates(s, s.houses()[0], s.shops())
    d = next(c for c in cs if c.kind == "direct")
    assert d.path[-2:] == ((17, 13), (16, 13)) and d.new_junctions == 0


def test_passing_through_dead_end_stub_is_one_junction():
    # demo1 case 1b: stub (18,13)-N-(18,12); the path adds links E and W at (18,13) -> degree 3
    s = parse_observation(_layout(roads={(18, 13): 1 << N, (18, 12): 1 << S}))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert (18, 13) in c.path and c.new_junctions == 1


def test_junction_penalty_picks_the_unlinked_road_tile():
    # x=18 is open only at y=12 and y=14, mirror images about the straight line. (18,12) is a road tile
    # with 2 links (to pending cells), so crossing it makes a junction; (18,14) is a bare road tile.
    wall = {(18, y): 2 for y in range(30) if y not in (12, 14)}
    roads = {(18, 12): (1 << 5) | (1 << 7), (17, 11): 1 << 1, (19, 11): 1 << 3, (18, 14): 0}
    s = parse_observation(_layout(terrain=wall, roads=roads, pending=[(17, 11), (19, 11)]))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert (18, 14) in c.path and (18, 12) not in c.path and c.new_junctions == 0


def test_junction_penalty_counts_the_in_link():
    # Same mirror layout, but (18,12) has a single link (NW, to pending (17,11)): only together with the
    # path's in-link AND out-link does it reach degree 3, so the A* charge must include the in-link.
    wall = {(18, y): 2 for y in range(30) if y not in (12, 14)}
    roads = {(18, 12): 1 << 5, (17, 11): 1 << 1, (18, 14): 0}
    s = parse_observation(_layout(terrain=wall, roads=roads, pending=[(17, 11)]))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert (18, 14) in c.path and (18, 12) not in c.path and c.new_junctions == 0


def test_existing_junction_is_not_new():
    # (18,13) already has 3 links (to pending cells N, S and NE): passing through it creates no new junction
    roads = {(18, 13): (1 << 6) | (1 << 2) | (1 << 7), (18, 12): 1 << 2, (18, 14): 1 << 6, (19, 12): 1 << 3}
    s = parse_observation(_layout(roads=roads, pending=[(18, 12), (18, 14), (19, 12)]))
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert (18, 13) in c.path and c.new_junctions == 0


def test_junction_penalty_at_attach_end_cell():
    # The shop network forks at (16,13) into two mirror-image stubs (17,12) and (17,14), equally far from the
    # house. (17,12) has a second link (to pending (17,11)), so ending there makes it a junction: attach must
    # end on (17,14) instead.
    roads = {(15, 13): 1 << 0, (16, 13): (1 << 4) | (1 << 7) | (1 << 1), (17, 12): (1 << 3) | (1 << 6),
             (17, 14): 1 << 5, (17, 11): 1 << 2}
    s = parse_observation(_layout(roads=roads, pending=[(17, 11)]))
    c = next(c for c in route_candidates(s, s.houses()[0], s.shops()) if c.kind == "attach")
    assert c.path[-1] == (17, 14) and c.new_junctions == 0 and c.shop_ids == (0,)


# --- cost model and metrics ---------------------------------------------------------------------
def _sep_layout():
    # colour-1 shop entrance (18,11) facing S; its network (18,12)-(18,13) lies on the colour-0 straight line
    b = [house(1, 0, 20, 13, W_), shop(0, 0, 14, 11, 2, 3, [(15, 13, E)]), shop(2, 1, 17, 10, 2, 2, [(18, 11, S)])]
    roads = {(18, 11): 1 << 2, (18, 12): (1 << 6) | (1 << 2), (18, 13): 1 << 6}
    return parse_observation(make_obs(buildings=b, roads=roads))


def test_separated_avoids_other_colour_network():
    s = _sep_layout()
    same = tuple(x for x in s.shops() if x.color == 0)
    cs = route_candidates(s, s.houses()[0], same)
    by = {c.kind: c for c in cs}
    assert (18, 13) in by["attach"].path and by["attach"].shared_cells == 1 and by["attach"].tiles_needed == 3
    assert (18, 13) not in by["separated"].path and by["separated"].shared_cells == 0
    assert [c.kind for c in cs] == ["attach", "separated"]


def test_separated_survives_merged_red_blue_network():
    # red shop 0's network (15,13)-(16,13) is merged with blue shop 2's trunk (16,9..12); red shop 3 at
    # (27,13) has its own pure-red stub (26,13). Attach takes the nearer merged network; separated pays
    # +3 there (it serves blue too) and goes to the pure-red network instead.
    roads = {**_line([(15, 13), (16, 13), (16, 12), (16, 11), (16, 10), (16, 9)]), **_line([(26, 13), (27, 13)])}
    b = [house(1, 0, 20, 13, W_), shop(0, 0, 14, 11, 2, 3, [(15, 13, E)]), shop(2, 1, 16, 9, 1, 1, [(16, 9, S)]),
         shop(3, 0, 27, 13, 1, 1, [(27, 13, W_)])]
    s = parse_observation(make_obs(buildings=b, roads=roads))
    cs = route_candidates(s, s.houses()[0], tuple(x for x in s.shops() if x.color == 0))
    by = {c.kind: c for c in cs}
    assert by["attach"].path[-1] == (16, 13) and by["attach"].shared_cells == 1 and by["attach"].shop_ids == (0,)
    assert by["separated"].path[-1] == (26, 13) and by["separated"].shared_cells == 0
    assert by["separated"].shop_ids == (3,)
    # the end cells: (16,13) has links W and N, the path adds E -> a T junction; (26,13) goes from 1 to 2 links
    assert by["attach"].new_junctions == 1 and by["separated"].new_junctions == 0


def test_metrics_turns_shop_ids_house_id():
    s = parse_observation(_layout())
    c = route_candidates(s, s.houses()[0], s.shops())[0]
    assert c.turns == 0 and c.shop_ids == (0,) and c.house_id == 1 and c.new_junctions == 0
    b = [house(1, 0, 20, 10, W_), shop(0, 0, 14, 13, 2, 3, [(15, 14, E)])]
    s2 = parse_observation(make_obs(buildings=b, terrain={(18, y): 1 for y in range(30)}))
    c2 = route_candidates(s2, s2.houses()[0], s2.shops())[0]
    assert c2.turns == len(c2.strokes) - 1 >= 1


def test_planned_cells_are_cheap_and_free():
    planned = frozenset({(19, 14), (18, 14), (17, 14)})
    s = parse_observation(_layout())
    c = route_candidates(s, s.houses()[0], s.shops(), planned=planned)[0]
    assert c.path == ((20, 13), (19, 14), (18, 14), (17, 14), (16, 13)) and c.tiles_needed == 1


def test_planned_on_straight_line_not_counted():
    s = parse_observation(_layout())
    c = route_candidates(s, s.houses()[0], s.shops(), planned=frozenset({(19, 13), (18, 13)}))[0]
    assert c.tiles_needed == 2


def test_road_tile_stock_filter():
    s3 = parse_observation(_layout(inventory=(3, 1, 0, 0, 0, 0)))
    assert route_candidates(s3, s3.houses()[0], s3.shops()) == []
    s4 = parse_observation(_layout(inventory=(4, 1, 0, 0, 0, 0)))
    assert route_candidates(s4, s4.houses()[0], s4.shops())[0].tiles_needed == 4


def test_empty_inventory_gives_no_candidates():
    s = parse_observation(_layout(inventory=()))
    assert route_candidates(s, s.houses()[0], s.shops()) == []


def test_direct_differs_from_attach_when_network_exists():
    roads = {(15, 13): 1 << 0, (16, 13): (1 << 4) | (1 << 0), (17, 13): 1 << 4}
    s = parse_observation(_layout(roads=roads))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert any(c.kind == "direct" and c.path[-1] == (16, 13) for c in cs)


def test_attach_ignores_other_colour_network_even_if_passed():
    cells = [(25, y) for y in range(5, 13)] + [(x, 12) for x in range(24, 18, -1)]
    other = _line(cells, {(25, 5): 1 << 6})
    other[(25, 4)] = 1 << 2
    b = [house(1, 0, 20, 13, W_), shop(0, 0, 14, 11, 2, 3, [(15, 13, E)]), shop(2, 1, 25, 3, 2, 2, [(25, 4, S)])]
    s = parse_observation(make_obs(buildings=b, roads=other))
    cs = route_candidates(s, s.houses()[0], s.shops())
    assert cs and all(c.path[-1] != (19, 12) for c in cs)


def test_unreachable_attach_skips_other_searches(monkeypatch):
    calls = []
    real = cand._astar
    monkeypatch.setattr(cand, "_astar", lambda *a, **k: calls.append(1) or real(*a, **k))
    s = parse_observation(_layout(terrain={(18, y): 2 for y in range(30)}))
    assert route_candidates(s, s.houses()[0], s.shops()) == [] and len(calls) == 1


# --- post-processing (sort / dedup / cap), isolated from A* --------------------------------------
def _patch(monkeypatch, results):
    it = iter(results)
    monkeypatch.setattr(cand, "_astar", lambda *a, **k: next(it))


def test_sort_dedup_and_cap(monkeypatch):
    s = parse_observation(_layout(roads={(19, 12): 0, (18, 12): 0, (18, 14): 0}))
    h, sh = s.houses()[0], s.shops()
    A = ((20, 13), (19, 13), (18, 13), (17, 13), (16, 13))             # 4 tiles, len 5
    D = ((20, 13), (19, 12), (18, 12), (17, 13), (16, 13))             # 2 tiles, len 5
    Sp = ((20, 13), (19, 12), (18, 12), (17, 12), (16, 12), (16, 13))  # 3 tiles, len 6
    _patch(monkeypatch, [(A, 0), (D, 0), (Sp, 0)])                     # generated attach, direct, separated
    assert [c.kind for c in route_candidates(s, h, sh)] == ["direct", "separated", "attach"]
    T = ((20, 13), (19, 13), (18, 14), (17, 13), (16, 13))             # 3 tiles, len 5
    D2 = ((20, 13), (19, 12), (18, 13), (17, 13), (16, 13))            # 3 tiles, len 5
    _patch(monkeypatch, [(T, 0), (D2, 0), (T, 0)])                     # separated duplicates attach
    assert [c.kind for c in route_candidates(s, h, sh)] == ["attach", "direct"]
    _patch(monkeypatch, [(T, 0), (D2, 0), (Sp, 0)])                    # equal (tiles,len) -> KIND_ORDER
    assert [c.kind for c in route_candidates(s, h, sh)] == ["attach", "direct", "separated"]
    _patch(monkeypatch, [(Sp, 0), (D2, 0), (T, 0)])                    # (3,6) loses to (3,5) on len
    assert [c.kind for c in route_candidates(s, h, sh)] == ["direct", "separated", "attach"]


# --- unserved_targets ---------------------------------------------------------------------------
def test_unserved_targets_nearest_tie_lowest_id_and_filters():
    # shop A (id 0) at (15,15) is served by both colour-0 houses over the y=14 road; shop B (id 1) is unserved.
    # Both houses are 5 from B's access (15,13): the tie goes to the lower id (3). House 9 has no colour-2
    # shop, and shop 5 (colour 5) has no house: neither produces an entry.
    road = _line([(x, 14) for x in range(10, 21)], {(10, 14): 1 << 6, (20, 14): 1 << 6, (15, 14): 1 << 2})
    road[(10, 13)] = 1 << 2
    road[(20, 13)] = 1 << 2
    road[(15, 15)] = 1 << 6
    b = [house(7, 0, 10, 13, S), house(3, 0, 20, 13, S), house(9, 2, 30, 5, S),
         shop(0, 0, 15, 15, 1, 1, [(15, 15, N)]), shop(1, 0, 14, 11, 2, 3, [(15, 13, E)]),
         shop(5, 5, 40, 20, 1, 1, [(40, 20, N)])]
    s = parse_observation(make_obs(buildings=b, roads=road))
    assert [(h.id, tuple(x.id for x in sh)) for h, sh in unserved_targets(s)] == [(3, (1,))]


def test_unserved_targets_lists_each_house_once():
    # house 1 is connected to shop 0; shops 2 and 4 are unserved and both have house 1 as nearest
    roads = _line([(20, 13), (19, 13), (18, 13), (17, 13), (16, 13)])
    b = [house(1, 0, 20, 13, W_), shop(0, 0, 16, 13, 1, 1, [(16, 13, E)]),
         shop(2, 0, 25, 20, 1, 1, [(25, 20, N)]), shop(4, 0, 25, 5, 1, 1, [(25, 5, S)])]
    s = parse_observation(make_obs(buildings=b, roads=roads))
    assert s.house_connected(s.houses()[0])
    assert [(h.id, tuple(x.id for x in sh)) for h, sh in unserved_targets(s)] == [(1, (2,))]


def test_unserved_targets_skip_does_not_fall_back_to_farther_house():
    # As above, plus a second connected colour-0 house 5 at (16,16), farther from shops 2 and 4. Shop 4's
    # nearest house (1) is already listed, so shop 4 is skipped: it is NOT reassigned to house 5 (ruling 4).
    roads = _line([(20, 13), (19, 13), (18, 13), (17, 13), (16, 13)])
    for c, v in _line([(16, 13), (16, 14), (16, 15), (16, 16)]).items():
        roads[c] = roads.get(c, 0) | v
    b = [house(1, 0, 20, 13, W_), house(5, 0, 16, 16, N), shop(0, 0, 16, 13, 1, 1, [(16, 13, E)]),
         shop(2, 0, 25, 20, 1, 1, [(25, 20, N)]), shop(4, 0, 25, 5, 1, 1, [(25, 5, S)])]
    s = parse_observation(make_obs(buildings=b, roads=roads))
    assert all(s.house_connected(h) for h in s.houses())
    assert [(h.id, tuple(x.id for x in sh)) for h, sh in unserved_targets(s)] == [(1, (2,))]


# --- coverage_targets (Phase 2, task 2) ----------------------------------------------------------------
from evolved_rules.candidates import COVERAGE_TARGET_CAP, coverage_targets, house_reaches


def _ids(targets):
    return [(h.id, tuple(x.id for x in sh)) for h, sh in targets]


def _two_networks():
    """Two colour-0 networks: house 1 -> shop 0 and house 7 -> shop 3. Both shops are served and both houses
    connected, so Phase 1 sees nothing to do. House 9 (colour 0) is unconnected; house 11 (colour 2) has no shop."""
    roads = _line([(20, 13), (19, 13), (18, 13), (17, 13), (16, 13)])
    roads.update(_line([(30, 20), (31, 20), (32, 20), (33, 20), (34, 20)]))
    b = [house(1, 0, 20, 13, W_), house(7, 0, 30, 20, E), house(9, 0, 40, 5, S), house(11, 2, 5, 5, S),
         shop(0, 0, 16, 13, 1, 1, [(16, 13, E)]), shop(3, 0, 34, 20, 1, 1, [(34, 20, W_)])]
    return parse_observation(make_obs(buildings=b, roads=roads))


def test_coverage_targets_add_unreached_same_colour_shops_after_phase1_entries():
    s = _two_networks()
    assert _ids(unserved_targets(s)) == [(9, (0, 3))]
    # Phase 1 entries first, then per shop (id order) each same-colour house that does not reach it.
    assert _ids(coverage_targets(s)) == [(9, (0, 3)), (7, (0,)), (1, (3,))]


def test_coverage_targets_skip_listed_pairs_and_order_houses_by_id():
    # Houses 1 and 5 reach shop 0; shops 2 and 4 are unserved. Phase 1 lists (1, (2,)) only (shop 4's nearest
    # house is already listed). Coverage adds (5, 2), then (1, 4) and (5, 4); (1, 2) is not listed twice.
    roads = _line([(20, 13), (19, 13), (18, 13), (17, 13), (16, 13)])
    for c, v in _line([(16, 13), (16, 14), (16, 15), (16, 16)]).items():
        roads[c] = roads.get(c, 0) | v
    b = [house(5, 0, 16, 16, N), house(1, 0, 20, 13, W_), shop(4, 0, 25, 5, 1, 1, [(25, 5, S)]),
         shop(0, 0, 16, 13, 1, 1, [(16, 13, E)]), shop(2, 0, 25, 20, 1, 1, [(25, 20, N)])]
    s = parse_observation(make_obs(buildings=b, roads=roads))
    assert _ids(unserved_targets(s)) == [(1, (2,))]
    assert _ids(coverage_targets(s)) == [(1, (2,)), (5, (2,)), (1, (4,)), (5, (4,))]


def test_coverage_targets_without_roads_equal_phase1():
    # Nothing is connected: every house already lists all its shops, so coverage adds nothing.
    b = [house(1, 0, 20, 13, W_), house(2, 0, 25, 13, W_), shop(0, 0, 14, 11, 2, 3, [(15, 13, E)]),
         shop(3, 0, 30, 20, 1, 1, [(30, 20, N)])]
    s = parse_observation(make_obs(buildings=b))
    assert _ids(coverage_targets(s)) == _ids(unserved_targets(s)) == [(1, (0, 3)), (2, (0, 3))]


def test_coverage_targets_cap_keeps_order():
    # 30 connected colour-0 houses on one road, all reaching shop 0 only; shop 1 (colour 0) is served by
    # none. Phase 1 lists shop 1's nearest house; coverage adds the other houses in id order, capped at 24.
    assert COVERAGE_TARGET_CAP == 24
    xs = list(range(10, 40))
    roads = _line([(x, 14) for x in xs] + [(40, 14)])
    b = [shop(0, 0, 40, 14, 1, 1, [(40, 14, W_)]), shop(1, 0, 5, 25, 1, 1, [(5, 25, N)])]
    for i, x in enumerate(xs):
        roads[(x, 13)] = roads.get((x, 13), 0) | (1 << 2)
        roads[(x, 14)] |= 1 << 6
        b.append(house(100 + i, 0, x, 13, S))
    s = parse_observation(make_obs(buildings=b, roads=roads, inventory=(0, 0, 0, 0, 0, 0)))
    assert all(s.house_connected(h) for h in s.houses())
    phase1 = _ids(unserved_targets(s))
    assert phase1 == [(100, (1,))]  # (10,13) is nearest to (5,25)
    t = _ids(coverage_targets(s))
    assert len(t) == 24 and t[0] == phase1[0]
    assert t[1:] == [(100 + i, (1,)) for i in range(1, 24)]


def test_coverage_targets_cap_truncates_phase1_entries_too():
    # 30 unconnected houses: Phase 1 lists all 30; the coverage list is its first 24.
    b = [shop(0, 0, 40, 14, 1, 1, [(40, 14, W_)])] + [house(100 + i, 0, 10 + i, 5, S) for i in range(30)]
    s = parse_observation(make_obs(buildings=b))
    assert len(unserved_targets(s)) == 30
    assert _ids(coverage_targets(s)) == _ids(unserved_targets(s))[:24]


def test_house_reaches():
    s = _two_networks()
    h = {b.id: b for b in s.buildings}
    assert house_reaches(s, 1, (h[0],)) and not house_reaches(s, 1, (h[3],))
    assert house_reaches(s, 7, (h[0], h[3])) and not house_reaches(s, 9, (h[0], h[3]))
    assert not house_reaches(s, 1, ())


def test_coverage_route_to_unreached_shop_reaches_it_once_built():
    # A coverage target's candidates end on shop 3's network, so drawing one makes house 1 reach shop 3.
    s = _two_networks()
    h = {b.id: b for b in s.buildings}
    target = next(t for t in coverage_targets(s) if t[0].id == 1)
    cands = route_candidates(s, target[0], target[1])
    assert cands and all(c.shop_ids == (3,) for c in cands)
    end = cands[0].path[-1]
    assert end in s.component(h[3].access[0]) or end in h[3].outside
