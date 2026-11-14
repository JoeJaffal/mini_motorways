"""gp-7 x0 calibration and decision-record analysis (plan 2026-11-14 sections 3.2, 3.1 logging, 5).

Gentle (plan 3.2): L's rule weights; cost head = separated with w_reuse = 0.5 and w_stop = 0.2; target head with
w_det and w_over small and positive, w_con = 0, n_t = 1.2 (at most 1 pair); b_t set so that a pair opens in about
10% of decisions; w_is_evo set so that an evo route is built in about 3-5% of decisions (the "rate minimums").

  python -m evolved_rules.ops.calibrate7 round --round 1 --b-t -0.5 --w-evo 0.0 [--workers 10]
      plays Gentle with decision logging on 8 calibration seeds (5300 + 8*(round-1) ...), then analyses the records
  python -m evolved_rules.ops.calibrate7 analyse DIR [--text FILE]
      rates of any folder of decision records

Rates are per decision (every call of the route step): pair_open = the first pass offers at least one target-head
pair (t > 0); evo_built = an evo or pair route was built in the decision; evo_first = the first pass's built route
was evo/pair. Solves: b_t for pair_open = 10% from the logged max t - b_t, and w_is_evo for evo_first = 4% by
re-ranking the logged first-pass candidates (exact for the logged states; the trajectory changes, so rounds iterate).
Seeds 5300-5399 are the calibration block (not a decision block). Output: output/evolved_rules/gp7/calibration/.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "evolved_rules" / "gp7" / "calibration"
L_PATH = ROOT / "evolved_rules" / "seeds" / "gp7" / "cma1_3tree.txt"
PAIR_OPEN_TARGET = 0.10
EVO_TARGET = 0.04


def gentle_weights(b_t: float, w_evo: float, w_det: float = 0.2, w_over: float = 0.2) -> dict[str, float]:
    return {"w_reuse": 0.5, "w_stop": 0.2, "b_t": b_t, "w_con": 0.0, "w_det": w_det, "w_over": w_over,
            "n_t": 1.2, "is_evo": w_evo}


def point_text(planner: dict[str, float], lights: bool = False, theta: float = 600.0, extra: dict | None = None) -> str:
    from evolved_rules import linear
    L = L_PATH.read_text().strip()
    sp = linear.Space(l_text=L, lights=lights, theta=theta)
    return linear.text_from_x(linear.x_from_l(sp, {**planner, **(extra or {})}), sp)


def load_records(d: Path) -> list[list[dict]]:
    games = []
    for f in sorted(Path(d).glob("*.jsonl.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            games.append([json.loads(line) for line in fh if line.strip()])
    return games


def _quantile(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return math.nan
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def rates(games: list[list[dict]], b_t: float) -> dict:
    recs = [r for g in games for r in g]
    n = len(recs)
    if n == 0:
        return {"decisions": 0}
    opens = sum(1 for r in recs if r.get("pair_tmax_nobias") is not None and r["pair_tmax_nobias"] + b_t > 0)
    evo_built = sum(1 for r in recs if r.get("evo_built"))
    first = sum(1 for r in recs if r.get("built") and r["built"][0] in ("evo", "pair"))
    any_route = sum(1 for r in recs if r.get("built"))
    return {"decisions": n, "games": len(games), "pair_open": opens / n, "evo_built": evo_built / n,
            "evo_first": first / n, "route_decisions": any_route / n}


def solve_b_t(games: list[list[dict]], target: float = PAIR_OPEN_TARGET) -> float:
    """b_t such that a fraction `target` of decisions has max_t - b_t + b_t > 0 (the logged max over pairs)."""
    recs = [r for g in games for r in g]
    tmax = [r["pair_tmax_nobias"] if r.get("pair_tmax_nobias") is not None else -math.inf for r in recs]
    finite = [t for t in tmax if math.isfinite(t)]
    q = _quantile(finite + [-1e9] * (len(tmax) - len(finite)), 1.0 - target)
    return -q


def evo_first_rate(games, delta: float, evo_col: int) -> float:
    """Fraction of decisions whose first-pass winner (after adding delta * is_evo to every priority) is an evo/pair
    candidate at or above hold."""
    n = hit = 0
    for g in games:
        for r in g:
            n += 1
            if not r.get("p"):
                continue
            best = None
            for i, (p, row) in enumerate(zip(r["p"], r["rows"])):
                if p is None or not math.isfinite(p):
                    continue
                q = p + delta * row[evo_col]
                if best is None or q > best[0]:
                    best = (q, i)
            if best is not None and math.isfinite(r.get("hold", math.nan)) and best[0] >= r["hold"] \
                    and r["kind"][best[1]] in ("evo", "pair"):
                hit += 1
    return hit / n if n else 0.0


def solve_w_evo(games, w_now: float, target: float = EVO_TARGET) -> float:
    from evolved_rules.agent import _LOG_CAND_TERMS
    col = _LOG_CAND_TERMS.index("is_evo")
    lo, hi = -5.0, 5.0
    if evo_first_rate(games, hi - w_now, col) < target:
        return hi
    for _ in range(40):
        mid = (lo + hi) / 2
        if evo_first_rate(games, mid - w_now, col) < target:
            lo = mid
        else:
            hi = mid
    return round(hi, 4)


def theta_q(games, q: float = 0.75) -> float:
    from evolved_rules.agent import _LOG_GLOBAL_TERMS
    k = _LOG_GLOBAL_TERMS.index("worst_overcrowded")
    return _quantile([r["g"][k] for g in games for r in g if r.get("g")], q)


def bypass_c(games, w_det: float = 0.2, w_over: float = 0.2, w_tt: float = 1.0, detour: float = 1.33) -> float:
    """Bypass's c (plan 5): the target score (without b_t and w_con) of a connected pair at detour 1.33 at a shop in
    the top quartile of overcrowded_for, approximated by the 75th percentile of the shop term (overcrowded_for/1024)
    over the logged connected pair rows; pairs at or above both thresholds then score t >= 0."""
    overs = [row[6] for g in games for r in g for row in r.get("pairs_top", []) if row[3] == 1.0]
    q = _quantile(overs, 0.75) if overs else 0.0
    return w_det * detour + w_over * q + w_tt * q * detour


def cmd_finalize(a) -> int:
    """calibration.json for the screen: b_t and w_is_evo of the last round (as played), theta = the 75th percentile
    of worst_overcrowded over every calibration round's decisions, Bypass's c from the same records."""
    rounds = sorted(OUT.glob("round*/calibration.json"))
    last = json.loads(rounds[-1].read_text())
    games = [g for d in sorted(OUT.glob("round*/decisions")) for g in load_records(d)]
    w = last["weights"]
    out = {"b_t": w["b_t"], "w_is_evo": w["is_evo"], "theta": round(theta_q(games), 4),
           "bypass_c": round(bypass_c(games, w["w_det"], w["w_over"]), 4), "rounds": len(rounds),
           "last_round": last["round"], "last_rates": last["rates"], "decisions_used": sum(len(g) for g in games)}
    (OUT / "calibration_final.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


def cmd_round(a) -> int:
    from evolved_rules.engine import Engine
    seeds = list(range(5300 + 8 * (a.round - 1), 5300 + 8 * a.round))
    w = gentle_weights(a.b_t, a.w_evo)
    text = point_text(w)
    d = OUT / f"round{a.round}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "policy.txt").write_text(text + "\n")
    with Engine(workers=a.workers, cache_path=OUT / "cache.jsonl") as eng:
        games = eng.play_logged([(text, s) for s in seeds], d / "decisions")
    recs = load_records(d / "decisions")
    r = rates(recs, a.b_t)
    out = {"round": a.round, "seeds": seeds, "weights": w, "rates": r,
           "rejected_actions": sum(g["rejected_actions"] for g in games),
           "solve": {"b_t_for_10pct": solve_b_t(recs), "w_is_evo_for_4pct": solve_w_evo(recs, a.w_evo),
                     "theta_q75_worst_overcrowded": theta_q(recs)}}
    (d / "calibration.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


def cmd_analyse(a) -> int:
    recs = load_records(Path(a.dir))
    print(json.dumps({"rates": rates(recs, a.b_t), "b_t_for_10pct": solve_b_t(recs),
                      "theta_q75": theta_q(recs)}, indent=1))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("round")
    r.add_argument("--round", type=int, required=True)
    r.add_argument("--b-t", type=float, required=True)
    r.add_argument("--w-evo", type=float, required=True)
    r.add_argument("--workers", type=int, default=10)
    s = sub.add_parser("analyse")
    s.add_argument("dir")
    s.add_argument("--b-t", type=float, default=0.0)
    sub.add_parser("finalize")
    a = p.parse_args()
    return {"round": cmd_round, "analyse": cmd_analyse, "finalize": cmd_finalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
