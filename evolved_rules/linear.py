"""gp-7 live coordinates (plan 2026-11-14 section 3.3): one vector x for cma-7 (and gp-7), and its policy text.

weight_i = x_i * scale_i; x is bounded to [-BOUND, BOUND]. The text keeps L's linear structure so that identity
gate (4) holds bit for bit: the priority tree is add(<L's balanced 40-term sum>, <balanced v7 extras>), the hold
and upgrade trees are L's balanced sums (tune_cmaes.weights_to_text). Coordinates (84):

  rule      23 priority candidate weights (gp.CANDIDATE_TERMS without is_clean), the hold bias and 15 hold global
            weights (gp.GLOBAL_TERMS without pending_refunds), 8 upgrade offer weights (gp.OFFER_TERMS)
  light     9  the light head: bias + 8 placement terms; place = if_gt(pl_is_light, 0.5, sum, -1.0) when lights=1
  cost      9  EvoCost weights (gp.COST_FIELDS without w_qstop)
  target    6  b_t, w_con, w_det, w_dem, w_over, n_t
  newterm   3  priority weights of is_evo, pair_connected, tiles_saved
  template  6  priority mul(worst_overcrowded, path_cost_s), mul(shop_overcrowded, tiles_saved),
               mul(worst_overcrowded, road_stock); place mul(pl_stopped_near, worst_overcrowded); cost w_qstop
               (gate(worst_overcrowded > theta) * stopped_on); target w_ttmpl (shop_overcrowded * detour_ratio)
  slot      4  gp-7 slot coordinates; the decoder multiplies slot k by mask_k (all 0 in cma-7 and gp7-v1)

Engineering choice (recorded in the pre-registration): the plan folds the 16 priority globals into hold
(hold_live = hold - prio). Here the priority global weights, is_clean, the hold's pending_refunds and the 16 upgrade
global weights stay FIXED at L's values and the hold weights are searched freely: the same search space (every
hold_live is reachable), but L's priority sum stays bit-identical. Every weight in a text is rounded to DECIMALS.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import gp
from .tune_cmaes import _balanced, text_to_weights, weights_by_tree

BOUND = 5.0
DECIMALS = 4
LIGHT_TERMS = ("pl_degree", "pl_doorstep", "pl_cars_near", "pl_stopped_near", "pl_max_wait_near",
               "pl_mean_wait_near", "pl_dist_worst_shop", "pl_worst_colour_stuck",
               "pl_placed", "time")  # gp-8: how many of this kind are down, and when in the game
PRIORITY_TEMPLATES = (("worst_overcrowded", "path_cost_s"), ("shop_overcrowded", "tiles_saved"),
                      ("worst_overcrowded", "road_stock"))
PLACE_TEMPLATE = ("pl_stopped_near", "worst_overcrowded")
N_SLOTS = 4

LAYOUT: tuple[tuple[str, str], ...] = (
    tuple(("rule", f"priority.{t}") for t in gp.CANDIDATE_TERMS if t != "is_clean")
    + (("rule", "hold.bias"),) + tuple(("rule", f"hold.{t}") for t in gp.GLOBAL_TERMS if t != "pending_refunds")
    + tuple(("rule", f"upgrade.{t}") for t in gp.OFFER_TERMS)
    + (("light", "bias"),) + tuple(("light", t) for t in LIGHT_TERMS)
    + (("round", "round.bias"),) + tuple(("round", f"round.{t}") for t in LIGHT_TERMS)
    + tuple(("cost", f) for f in gp.COST_FIELDS if f != "w_qstop")
    + tuple(("target", f) for f in gp.TARGET_FIELDS if f != "w_ttmpl")
    + tuple(("newterm", t) for t in gp.V7_CANDIDATE_TERMS)
    + tuple(("template", f"priority.{a}*{b}") for a, b in PRIORITY_TEMPLATES)
    + (("template", f"place.{PLACE_TEMPLATE[0]}*{PLACE_TEMPLATE[1]}"), ("template", "cost.w_qstop"),
       ("template", "target.w_ttmpl"))
    + tuple(("slot", f"slot{k}") for k in range(N_SLOTS))
)
DIM = len(LAYOUT)
INDEX = {name: i for i, (_, name) in enumerate(LAYOUT)}
GROUPS = tuple(g for g, _ in LAYOUT)
# coordinates whose scale is always 1 (plan 3.3): biases, n_t, the cost-head weights and the slots
UNIT_SCALE = frozenset(i for i, (g, n) in enumerate(LAYOUT)
                       if g in ("cost", "slot") or n in ("hold.bias", "bias", "round.bias", "b_t", "n_t"))

SEPARATED_COST = {"w_paid": 1.0, "w_reuse": 0.15, "w_step": 0.05, "w_jn": 0.5, "w_jl": 0.0, "w_ns": 0.0,
                  "w_for": 3.0, "w_car": 0.0, "w_stop": 0.0}


def snap(v: float) -> float:
    return round(float(v), DECIMALS) + 0.0


@dataclass(frozen=True)
class Space:
    """The decoder's frozen settings: L's fixed weights, the scales, theta and the light flag."""

    l_text: str
    scales: tuple[float, ...] = tuple([1.0] * DIM)
    theta: float = 600.0
    lights: bool = False
    roundabouts: bool = False  # gp-8: the roundabout head (round group)
    masks: tuple[float, ...] = tuple([0.0] * N_SLOTS)
    # gp-7-lite (gp7-v2): slot trees (priority over PRIORITY7 terms, hold over HOLD terms, cost over
    # gp.COST_SLOT_TERMS, target over gp.TARGET_SLOT_TERMS); a slot acts only with its tree set and mask 1
    slot_trees: tuple = (None,) * N_SLOTS
    l_weights: dict = field(default=None, compare=False)

    def __post_init__(self):
        if len(self.scales) != DIM:
            raise ValueError(f"scales need {DIM} entries, got {len(self.scales)}")
        if any(not (math.isfinite(s) and s > 0) for s in self.scales):
            raise ValueError("scales must be finite and > 0")
        object.__setattr__(self, "l_weights", weights_by_tree(text_to_weights(self.l_text)))

    def to_json(self) -> dict:
        return {"l_text": self.l_text, "scales": list(self.scales), "theta": self.theta, "lights": self.lights,
                "roundabouts": self.roundabouts, "masks": list(self.masks), "slot_trees": list(self.slot_trees), "layout": [list(x) for x in LAYOUT]}

    @classmethod
    def from_json(cls, d: dict) -> "Space":
        if [tuple(x) for x in d.get("layout", LAYOUT)] != list(LAYOUT):
            raise ValueError("space.json layout differs from linear.LAYOUT")
        return cls(l_text=d["l_text"], scales=tuple(d["scales"]), theta=float(d["theta"]), lights=bool(d["lights"]),
                   roundabouts=bool(d.get("roundabouts", False)), masks=tuple(d.get("masks", [0.0] * N_SLOTS)),
                   slot_trees=tuple(d.get("slot_trees", [None] * N_SLOTS)))

    @classmethod
    def load(cls, path: Path) -> "Space":
        return cls.from_json(json.loads(Path(path).read_text(encoding="utf-8")))


def weights(x, space: Space) -> dict[str, float]:
    """name -> snapped weight (x_i * scale_i), for every coordinate."""
    if len(x) != DIM:
        raise ValueError(f"x needs {DIM} entries, got {len(x)}")
    out = {}
    for i, (_, name) in enumerate(LAYOUT):
        v = float(x[i])
        if not math.isfinite(v):
            raise ValueError(f"x[{i}] ({name}) is not finite")
        out[name] = snap(v * space.scales[i])
    return out


def text_from_x(x, space: Space) -> str:
    """The canonical policy text of x under `space` (3 trees + flags + planner, or 5 trees with lights=1)."""
    w = weights(x, space)
    L = space.l_weights
    pri = []
    for t in gp.PRIORITY_TERMS:
        v = w[f"priority.{t}"] if f"priority.{t}" in w else snap(L["priority"][t])
        pri.append(f"mul({v!r}, {t})")
    extras = [f"mul({w[t]!r}, {t})" for t in gp.V7_CANDIDATE_TERMS]
    extras += [f"mul({w[f'priority.{a}*{b}']!r}, mul({a}, {b}))" for a, b in PRIORITY_TEMPLATES]
    sw = [snap(float(x[INDEX[f"slot{k}"]]) * space.scales[INDEX[f"slot{k}"]] * space.masks[k]) for k in range(N_SLOTS)]
    live = [space.masks[k] != 0 and space.slot_trees[k] is not None for k in range(N_SLOTS)]
    if live[0]:
        extras.append(f"mul({sw[0]!r}, {space.slot_trees[0]})")
    priority = f"add({_balanced(pri)}, {_balanced(extras)})"
    hold = [repr(w["hold.bias"])]
    for t in gp.HOLD_TERMS:
        v = w[f"hold.{t}"] if f"hold.{t}" in w else snap(L["hold"][t])
        hold.append(f"mul({v!r}, {t})")
    upg = []
    for t in gp.UPGRADE_TERMS:
        v = w[f"upgrade.{t}"] if f"upgrade.{t}" in w else snap(L["upgrade"][t])
        upg.append(f"mul({v!r}, {t})")
    hold_text = _balanced(hold)
    if live[1]:
        hold_text = f"add({hold_text}, mul({sw[1]!r}, {space.slot_trees[1]}))"
    lines = [f"priority: {priority}", f"hold: {hold_text}", f"upgrade: {_balanced(upg)}"]
    if space.lights or space.roundabouts:
        a, b = PLACE_TEMPLATE
        items = [repr(w["bias"])] + [f"mul({w[t]!r}, {t})" for t in LIGHT_TERMS]
        items.append(f"mul({w[f'place.{a}*{b}']!r}, mul({a}, {b}))")
        ritems = [repr(w["round.bias"])] + [f"mul({w[f'round.{t}']!r}, {t})" for t in LIGHT_TERMS]
        rnd = f"if_gt(pl_is_roundabout, 0.5, {_balanced(ritems)}, -1.0)" if space.roundabouts else "-1.0"
        place = f"if_gt(pl_is_light, 0.5, {_balanced(items)}, {rnd})" if space.lights else rnd
        lines += [f"remove: {gp.NEVER_REMOVE}", f"place: {place}"]
    lines.append(f"flags: clean=0 lights={int(space.lights)} roundabouts={int(space.roundabouts)}")
    cost = [w[f] for f in gp.COST_FIELDS if f != "w_qstop"] + [w["cost.w_qstop"]]
    target = [w[f] for f in ("b_t", "w_con", "w_det", "w_dem", "w_over")] + [w["target.w_ttmpl"], w["n_t"]]
    cslot = f"mul({sw[2]!r}, {space.slot_trees[2]})" if live[2] else None
    tslot = f"mul({sw[3]!r}, {space.slot_trees[3]})" if live[3] else None
    lines.append(gp.Planner(cost, target, space.theta, cslot, tslot).text())
    return gp.individual_text(gp.individual_from_text("\n".join(lines)))


def x_from_weights(named: dict[str, float], space: Space) -> list[float]:
    """x from named weights (x_i = weight / scale_i); unnamed coordinates are 0."""
    unknown = set(named) - set(INDEX)
    if unknown:
        raise ValueError(f"unknown coordinates: {sorted(unknown)}")
    return [named.get(name, 0.0) / space.scales[i] for i, (_, name) in enumerate(LAYOUT)]


def l_rule_weights(space: Space) -> dict[str, float]:
    """L's live rule weights by coordinate name."""
    L = space.l_weights
    out = {}
    for _, name in LAYOUT[:sum(1 for g in GROUPS if g == "rule")]:
        tree, term = name.split(".", 1)
        out[name] = L[tree][term]
    return out


def x_from_l(space: Space, planner: dict[str, float] | None = None) -> list[float]:
    """L's rule weights, the planner at the separated cost vector (target head off, n_t = 0) unless `planner`
    names other weights, everything else 0: identity gate (4)'s point, and the base of every screen point."""
    named = {**l_rule_weights(space), **SEPARATED_COST, **(planner or {})}
    return x_from_weights(named, space)


def x_from_l_text(l_text: str) -> list[float]:
    """Gate (4) helper with unit scales."""
    return x_from_l(Space(l_text=l_text))


def scale_norm(spreads: dict[int, float]) -> float:
    """The median of 1/spread over the spread-scaled coordinates (the normaliser of scales_for_x0)."""
    raw = sorted(1.0 / s for i, s in spreads.items() if i not in UNIT_SCALE and s > 0 and math.isfinite(s))
    return raw[len(raw) // 2] if raw else 1.0


def scales_for_x0(spreads: dict[int, float], x0_weights: dict[str, float], floor: float = 0.1,
                  cap: float = 10.0, max_abs_x0: float = 4.5) -> tuple[float, ...]:
    """Scales from term spreads (plan 3.3): scale_i proportional to 1/spread_i, normalised to median 1 over the
    spread-scaled coordinates, clipped to [floor, cap]; UNIT_SCALE coordinates and those without a spread get 1.
    Then raised where needed so that |x0_i| = |weight_i| / scale_i <= max_abs_x0 (x0 stays inside the bounds)."""
    raw = {i: 1.0 / s for i, s in spreads.items() if i not in UNIT_SCALE and s > 0 and math.isfinite(s)}
    med = sorted(raw.values())[len(raw) // 2] if raw else 1.0
    out = []
    for i, (_, name) in enumerate(LAYOUT):
        s = 1.0 if i not in raw else min(cap, max(floor, raw[i] / med))
        w = abs(x0_weights.get(name, 0.0))
        if w / s > max_abs_x0:
            s = w / max_abs_x0
        out.append(s)
    return tuple(out)
