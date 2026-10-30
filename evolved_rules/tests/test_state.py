import pytest

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

# Every field the agent must never read (Global Constraints): top level, per building,
# per offer (everything but type/amount/roads), per vehicle.
EXCLUDED = frozenset({
    "scheduledSpawns", "randomAlgorithm", "randomDraws",
    "upgradeAt", "plannedDemandMultiplier", "feasibleDemandInterval",
    "feasibilityVerified", "originalDemandInterval",
    "weight", "firstWeek", "lastWeek", "maximum",
    "route", "returnRoute",
})


class _Guarded(dict):
    """A dict that raises AssertionError as soon as an excluded key is read."""

    def _check(self, k):
        assert k not in EXCLUDED, f"parse_observation read excluded field {k!r}"

    def __getitem__(self, k):
        self._check(k)
        return super().__getitem__(k)

    def get(self, k, default=None):
        self._check(k)
        return super().get(k, default)

    def __contains__(self, k):
        self._check(k)
        return super().__contains__(k)

    def pop(self, k, *default):
        self._check(k)
        return super().pop(k, *default)

    def setdefault(self, k, default=None):
        self._check(k)
        return super().setdefault(k, default)

    def items(self):
        assert not EXCLUDED & self.keys(), "parse_observation iterated a dict holding excluded fields"
        return super().items()

    def values(self):
        assert not EXCLUDED & self.keys(), "parse_observation iterated a dict holding excluded fields"
        return super().values()


def _rebuild(o, wrap):
    """Deep copy of an observation; wrap(dict) -> dict decides what each dict becomes."""
    if isinstance(o, dict):
        return wrap({k: _rebuild(v, wrap) for k, v in o.items()})
    if isinstance(o, list):
        return [_rebuild(v, wrap) for v in o]
    return o


def test_parse_ignores_excluded_fields():
    offers = [{"type": 0, "amount": 3, "roads": 2}]
    vehicles = [{"color": 0, "stage": "Outbound", "waiting": 0.5}]
    o = _layout(offers=offers, vehicles=vehicles)
    # The synthetic observation really carries every excluded field, so the guard below is not vacuous.
    assert {"scheduledSpawns", "randomAlgorithm", "randomDraws"} <= o.keys()
    assert {"upgradeAt", "plannedDemandMultiplier", "feasibleDemandInterval",
            "feasibilityVerified", "originalDemandInterval"} <= o["buildings"][0].keys()
    assert {"weight", "firstWeek", "lastWeek", "maximum"} <= o["upgradeChoices"][0].keys()
    assert {"route", "returnRoute"} <= o["vehicles"][0].keys()

    guarded = _rebuild(o, _Guarded)
    with pytest.raises(AssertionError):  # the guard itself works
        guarded["buildings"][0]["upgradeAt"]
    parse_observation(guarded)  # fails if any excluded field is read

    stripped = _rebuild(o, lambda d: {k: v for k, v in d.items() if k not in EXCLUDED})
    parse_observation(stripped)  # and it does not need them to be present

def test_out_of_grid_cells_are_not_roads():
    s = parse_observation(make_obs(roads={(49, 5): 0}))
    assert s.road_cell((49, 5))
    for c in [(-1, 5), (50, 5), (5, -1), (5, 30)]:
        assert not s.road_cell(c)
        assert s.component(c) == frozenset()

def test_rejects_wrong_grid():
    o = make_obs(); o["width"] = 40
    with pytest.raises(ValueError):
        parse_observation(o)

@pytest.mark.host
def test_parses_real_reset(host):
    s = parse_observation(host.reset(1000)["observation"])
    x0, y0, x1, y1 = s.bounds
    assert 0 <= x0 < x1 <= 50 and 0 <= y0 < y1 <= 30
    assert len(s.houses()) >= 1 and len(s.shops()) >= 1
    assert all(s.playable(b.cell) for b in s.buildings)
