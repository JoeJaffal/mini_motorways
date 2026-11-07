"""Failure autopsy and input statistics: why a rule set's games end, and which inputs ever vary (PLAN.md 8.2).

    PY -m evolved_rules.autopsy --policy SPEC --seeds 1500-1549 --workers 10 --out NAME
    SPEC: hand | separated | clean | cleanrm | seprm | tree:<file> | tree+clean:<file>

Each game is played exactly as agent.play_game plays it (same loop, same policy), with the policy wrapped so
that every feature dict it is shown is tallied. At the end the final observation is read, including fields the
agent never reads (vehicle homeId and the cars' obstacle reasons): this is a diagnostic, never an input. (Since
gp-3 the agent itself reads vehicle stage, shopId, position and speed: features._Analysis.traffic.)

Why the game was lost, for the shop whose overcrowding timer ran out (the failing shop, colour c):
    not_connected     no house reaches the shop
    slow_arrival      every waiting pin already has a car assigned: cars are too slow to arrive (route length,
                      congestion), not too few
    gridlock          pins without a car, every car of colour c is busy, and at least GRIDLOCK_SHARE of its
                      driving cars are nearly stopped: the cars exist but traffic holds them
    car_shortage      pins without a car and every car of colour c is busy, with traffic moving: too few cars
    unreachable_cars  pins without a car, and idle cars of colour c exist, but none lives in a house that reaches
                      this shop
    dispatch_gap      pins without a car while an idle car that can reach the shop is at home (timing)
    cap               the game reached the time cap (not lost)

Output, in output/evolved_rules/autopsy/<out>/: games.jsonl (one row per game), terminals.json (per input:
count, non-zero share, distinct values, min, max, mean) and summary.txt (also printed).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from . import evaluate as ev
from .agent import EventTracker, decide, places
from .gp import TreePolicy
from .host import ROOT, Host
from .rules import CleanHand, CleanRemoveHand, HandRule, SeparatedPreference, SeparatedRemoveHand
from .session import GameSession

AUTOPSY_DIR = ROOT / "output" / "evolved_rules" / "autopsy"
STUCK_SPEED = 0.05  # tiles/s: a driving car slower than this counts as stuck
GRIDLOCK_SHARE = 0.8  # a car shortage with at least this share of the colour's driving cars stuck is gridlock
PARKED = "Parking"  # a parked car has speed 0 by design: not stuck, so left out of the stuck shares
MAX_DISTINCT = 64  # distinct values kept per input

_HOST: Host | None = None


class _Tally:
    """Per-input running statistics of the values a policy was shown."""

    def __init__(self) -> None:
        self.stats: dict[str, dict] = {}

    def add(self, f: dict) -> None:
        for k, v in f.items():
            s = self.stats.setdefault(k, {"n": 0, "nonzero": 0, "min": v, "max": v, "sum": 0.0, "values": []})
            s["n"] += 1
            s["nonzero"] += v != 0
            s["min"], s["max"] = min(s["min"], v), max(s["max"], v)
            s["sum"] += v
            if len(s["values"]) < MAX_DISTINCT and v not in s["values"]:
                s["values"].append(v)


class _Watched:
    """A policy that tallies every feature dict it is shown and otherwise behaves exactly like `inner`."""

    def __init__(self, inner, tally: _Tally) -> None:
        self.inner, self.tally = inner, tally
        self.name = inner.name
        # Every attribute agent.decide / play_game reads from a policy, so the wrapped policy plays identically.
        self.coverage = getattr(inner, "coverage", False)
        self.clean_routes = getattr(inner, "clean_routes", False)
        self.removes = getattr(inner, "removes", False)
        self.places_lights = getattr(inner, "places_lights", False)
        self.places_roundabouts = getattr(inner, "places_roundabouts", False)
        self.wants_globals = getattr(inner, "wants_globals", False)
        self.acts = getattr(inner, "acts", True)

    def priority(self, f):
        self.tally.add(f)
        return self.inner.priority(f)

    def hold(self, g):
        self.tally.add(g)
        return self.inner.hold(g)

    def upgrade(self, f):
        self.tally.add(f)
        return self.inner.upgrade(f)

    def remove(self, f):
        self.tally.add({k: v for k, v in f.items() if k.startswith("rm_")})  # the globals are tallied by hold
        return self.inner.remove(f)

    def place(self, f):
        self.tally.add({k: v for k, v in f.items() if k.startswith("pl_")})  # the globals are tallied by hold
        return self.inner.place(f)


def make_policy(spec: str):
    """hand, separated, clean (CleanHand), tree:<file>, or tree+clean:<file> (the same trees offered clean routes)."""
    if spec == "hand":
        return HandRule()
    if spec == "separated":
        return SeparatedPreference()
    if spec == "seprm":
        return SeparatedRemoveHand()
    if spec == "cleanrm":
        return CleanRemoveHand()
    if spec == "clean":
        return CleanHand()
    if spec.startswith("tree:"):
        return TreePolicy(Path(spec[5:]).read_text(encoding="utf-8"))
    if spec.startswith("tree+clean:"):
        return TreePolicy(Path(spec[11:]).read_text(encoding="utf-8"), clean_routes=True)
    raise ValueError(f"unknown policy {spec!r} (hand, separated, clean, tree:<file> or tree+clean:<file>)")


def classify(state, raw: dict, cap_s: float) -> dict:
    """Why the game ended, from its final state and raw observation (see the module docstring)."""
    if not state.failed:
        return {"cause": "cap"}
    shops = state.shops()
    f = max(shops, key=lambda s: (s.overcrowded_for, -s.id))
    reach = state.component  # BFS over links
    houses = [h for h in state.houses() if h.color == f.color]
    reach_ids = {h.id for h in houses if any(a in reach(h.cell) for a in f.access)}
    cars = [v for v in raw["vehicles"] if int(v["color"]) == f.color]
    home = [v for v in cars if v["stage"] == "Home"]
    home_reach = [v for v in home if int(v["homeId"]) in reach_ids]
    busy = [v for v in cars if v["stage"] != "Home"]
    driving = [v for v in busy if v["stage"] != PARKED]
    all_driving = [v for v in raw["vehicles"] if v["stage"] not in ("Home", PARKED)]

    def stuck_share(vs):
        return (sum(1 for v in vs if float(v["speed"]) < STUCK_SPEED) / len(vs)) if vs else 0.0

    unassigned = f.demand - f.reserved
    if not reach_ids:
        cause = "not_connected"
    elif unassigned <= 0:
        cause = "slow_arrival"
    elif home_reach:
        cause = "dispatch_gap"
    elif home:
        cause = "unreachable_cars"
    elif stuck_share(driving) >= GRIDLOCK_SHARE:
        cause = "gridlock"
    else:
        cause = "car_shortage"

    # Where traffic is held. A stuck car's `obstacle` says what stops it; "Queue ahead" only means another car is
    # in front, so the cars stuck for any other reason are the heads of the queues and their reasons are the
    # causes ("Carpark access occupied" = waiting for a shop's single car-park gate, "Crossing vehicle" /
    # "Approaching vehicle priority" = a junction, and so on). Distances are to the failing shop's nearest
    # entrance, in tiles (Chebyshev).
    stuck_color = [v for v in driving if float(v["speed"]) < STUCK_SPEED]
    stuck_all = [v for v in all_driving if float(v["speed"]) < STUCK_SPEED]

    def head_reasons(vs):
        out: dict[str, int] = {}
        for v in vs:
            reason = v.get("obstacle") or "none"
            if reason != "Queue ahead":
                out[reason] = out.get(reason, 0) + 1
        return dict(sorted(out.items()))

    def dist(v):  # by the car's cell (a position is a float; a cell centre is x + 0.5), as features.traffic
        cx, cy = math.floor(float(v["x"])), math.floor(float(v["y"]))
        return min(max(abs(cx - ax), abs(cy - ay)) for ax, ay in f.access)

    return {
        "cause": cause, "shop": f.id,
        "stuck_color": len(stuck_color), "stuck_color_near_shop": sum(1 for v in stuck_color if dist(v) <= 3),
        "stuck_color_to_shop": sum(1 for v in stuck_color if int(v["shopId"]) == f.id),
        "queued_color": sum(1 for v in stuck_color if v.get("obstacle") == "Queue ahead"),
        "heads_color": head_reasons(stuck_color), "heads_all": head_reasons(stuck_all), "color": f.color, "demand": f.demand, "reserved": f.reserved,
        "capacity": f.capacity, "upgraded": f.upgraded, "shops_of_color": sum(1 for s in shops if s.color == f.color),
        "houses_of_color": len(houses), "houses_reaching": len(reach_ids), "cars_of_color": len(cars),
        "cars_home": len(home), "cars_home_reaching": len(home_reach), "cars_busy": len(busy),
        "cars_to_shop": sum(1 for v in busy if int(v["shopId"]) == f.id),
        "cars_parked": len(busy) - len(driving),
        "stuck_share_color": stuck_share(driving),
        "stuck_share_all": stuck_share(all_driving),
        "mean_wait_color": statistics.fmean(float(v["waiting"]) for v in busy) if busy else 0.0,
    }


def _init() -> None:
    import atexit
    global _HOST
    _HOST = Host()
    atexit.register(_HOST.close)


def play(spec: str, seed: int, cap_s: float = ev.DEFAULT_CAP_S) -> dict:
    """One game, as agent.play_game plays it; returns its autopsy row and the input tally."""
    tally = _Tally()
    policy = _Watched(make_policy(spec), tally)
    session = GameSession(_HOST, seed, cap_s=cap_s, record=False)
    session.reset()
    tracker = EventTracker(places=any(places(policy)))
    while not session.done:
        if policy.acts and tracker.should_decide(session.state):
            decide(session, policy)
        else:
            session.wait()
    state = session.state
    row = {"seed": seed, "trips": state.trips, "seconds": state.time, "road_stock": state.inventory[0],
           "shops": len(state.shops()), "houses": len(state.houses()), "tiles_built": session.tiles_built,
           "removals": session.action_counts.get("Remove", 0),
           **classify(state, session.raw, cap_s)}
    return {"row": row, "tally": tally.stats}


def _merge(total: dict, part: dict) -> None:
    for k, s in part.items():
        t = total.setdefault(k, {"n": 0, "nonzero": 0, "min": s["min"], "max": s["max"], "sum": 0.0, "values": []})
        t["n"] += s["n"]
        t["nonzero"] += s["nonzero"]
        t["min"], t["max"] = min(t["min"], s["min"]), max(t["max"], s["max"])
        t["sum"] += s["sum"]
        for v in s["values"]:
            if len(t["values"]) < MAX_DISTINCT and v not in t["values"]:
                t["values"].append(v)


def summarise(rows: list[dict], terms: dict) -> str:
    lines = [f"{len(rows)} games: trips mean {statistics.fmean(r['trips'] for r in rows):.1f}, "
             f"seconds mean {statistics.fmean(r['seconds'] for r in rows):.1f}"]
    causes = Counter(r["cause"] for r in rows)
    lines.append("causes: " + ", ".join(f"{c} {n}" for c, n in causes.most_common()))
    lost = [r for r in rows if r["cause"] != "cap"]
    if lost:
        def avg(k):
            return statistics.fmean(r[k] for r in lost)
        lines.append(f"at failure (mean): road tiles left {avg('road_stock'):.1f}, houses of colour {avg('houses_of_color'):.1f} "
                     f"({avg('houses_reaching'):.1f} reach the shop), cars of colour {avg('cars_of_color'):.1f} "
                     f"({avg('cars_busy'):.1f} busy, {avg('cars_home'):.1f} home), pins {avg('demand'):.1f} "
                     f"({avg('reserved'):.1f} with a car), stuck share colour {avg('stuck_share_color'):.2f} "
                     f"all {avg('stuck_share_all'):.2f}")
    lines.append("inputs (non-zero share, distinct values, min..max):")
    for k in sorted(terms):
        s = terms[k]
        share = s["nonzero"] / s["n"] if s["n"] else 0.0
        flag = "  DEAD" if len(s["values"]) <= 1 else ("  rare" if share < 0.01 else "")
        lines.append(f"  {k:24s} {share:6.3f}  {len(s['values']):3d}{'+' if len(s['values']) >= MAX_DISTINCT else ' '}  "
                     f"{s['min']:.4g}..{s['max']:.4g}{flag}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m evolved_rules.autopsy", description=__doc__.splitlines()[0])
    p.add_argument("--policy", required=True)
    p.add_argument("--seeds", nargs="+", default=["1500-1549"])
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--out", required=True)
    p.add_argument("--cap", type=float, default=ev.DEFAULT_CAP_S)
    a = p.parse_args(argv)
    ev._check_run_name(a.out)
    make_policy(a.policy)  # fail fast on a bad spec
    seeds = ev.parse_seeds(a.seeds)
    out = AUTOPSY_DIR / a.out
    out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=a.workers, mp_context=ev.MP_CONTEXT, initializer=_init) as pool:
        results = list(pool.map(play, [a.policy] * len(seeds), seeds, [a.cap] * len(seeds)))
    rows = [r["row"] for r in results]
    terms: dict = {}
    for r in results:
        _merge(terms, r["tally"])
    with open(out / "games.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    (out / "terminals.json").write_text(json.dumps(terms, indent=1), encoding="utf-8")
    text = summarise(rows, terms)
    (out / "summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
