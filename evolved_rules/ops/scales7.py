"""gp-7 coordinate scales from decision records (plan 2026-11-14 section 3.3, "Scaling").

  python -m evolved_rules.ops.scales7 --dirs DIR [DIR ...] --x0 X0_WEIGHTS.json --out SCALES.json

Spread of a coordinate's term, in the units the tree sees (raw / gp.SCALE):
  - candidate terms, the v7 priority terms and the priority templates: within-decision standard deviation over the
    first pass's candidates, median over decisions with at least 2 candidates;
  - hold global terms: standard deviation across decisions;
  - target-head terms (and the target template): within-decision standard deviation over the logged top pairs,
    median over decisions with at least 2 pairs;
  - upgrade offer terms, light terms and the cost template are not logged: no spread (scale 1).
scale_i = 1/spread_i normalised to median 1 over the coordinates with a spread, clipped to [0.1, 10]; biases, n_t,
the cost-head weights and the slots get 1; then raised where needed so that |x0_i| <= 4.5 (linear.scales_for_x0).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from evolved_rules import gp, linear
from evolved_rules.agent import _LOG_CAND_TERMS, _LOG_GLOBAL_TERMS
from evolved_rules.ops.calibrate7 import load_records


def _sd(xs: list[float]) -> float:
    return statistics.pstdev(xs) if len(xs) >= 2 else math.nan


def spreads(games: list[list[dict]]) -> dict[int, float]:
    recs = [r for g in games for r in g]
    ci = {t: i for i, t in enumerate(_LOG_CAND_TERMS)}
    gi = {t: i for i, t in enumerate(_LOG_GLOBAL_TERMS)}
    within: dict[str, list[float]] = {}

    def add(name: str, vals: list[float]):
        s = _sd(vals)
        if math.isfinite(s):
            within.setdefault(name, []).append(s)

    for r in recs:
        rows = r.get("rows") or []
        if len(rows) >= 2:
            for t in _LOG_CAND_TERMS:
                add(f"c.{t}", [row[ci[t]] / gp.SCALE[t] for row in rows])
            g = r.get("g") or []
            if g:
                wo = g[gi["worst_overcrowded"]] / gp.SCALE["worst_overcrowded"]
                rs = g[gi["road_stock"]] / gp.SCALE["road_stock"]
                add("t.wo*pcs", [wo * row[ci["path_cost_s"]] / gp.SCALE["path_cost_s"] for row in rows])
                add("t.wo*rs", [wo * rs for _ in rows])
            add("t.so*ts", [(row[ci["shop_overcrowded"]] / gp.SCALE["shop_overcrowded"])
                            * (row[ci["tiles_saved"]] / gp.SCALE["tiles_saved"]) for row in rows])
        pairs = r.get("pairs_top") or []
        if len(pairs) >= 2:  # [house, shop, t, con, det, dem, over]
            add("p.con", [p[3] for p in pairs])
            add("p.det", [p[4] for p in pairs])
            add("p.dem", [p[5] for p in pairs])
            add("p.over", [p[6] for p in pairs])
            add("p.tt", [p[6] * p[4] for p in pairs])
    med = {k: statistics.median(v) for k, v in within.items() if v}
    across = {}
    for t in gp.GLOBAL_TERMS:
        vals = [r["g"][gi[t]] / gp.SCALE[t] for r in recs if r.get("g")]
        across[t] = _sd(vals)
    out: dict[int, float] = {}
    for i, (grp, name) in enumerate(linear.LAYOUT):
        s = math.nan
        if grp == "rule" and name.startswith("priority."):
            s = med.get(f"c.{name.split('.', 1)[1]}", math.nan)
        elif grp == "rule" and name.startswith("hold.") and name != "hold.bias":
            s = across.get(name.split(".", 1)[1], math.nan)
        elif grp == "newterm":
            s = med.get(f"c.{name}", math.nan)
        elif grp == "target":
            s = {"w_con": med.get("p.con"), "w_det": med.get("p.det"), "w_dem": med.get("p.dem"),
                 "w_over": med.get("p.over")}.get(name, math.nan) or math.nan
        elif grp == "template":
            s = {"priority.worst_overcrowded*path_cost_s": med.get("t.wo*pcs"),
                 "priority.shop_overcrowded*tiles_saved": med.get("t.so*ts"),
                 "priority.worst_overcrowded*road_stock": med.get("t.wo*rs"),
                 "target.w_ttmpl": med.get("p.tt")}.get(name, math.nan) or math.nan
        if s is not None and math.isfinite(s) and s > 0:
            out[i] = s
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dirs", nargs="+", required=True)
    p.add_argument("--x0", required=True, help="JSON {coordinate name: weight} of x0*")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    games = [g for d in a.dirs for g in load_records(Path(d))]
    sp = spreads(games)
    x0w = json.loads(Path(a.x0).read_text())
    scales = linear.scales_for_x0(sp, x0w)
    doc = {"decisions": sum(len(g) for g in games), "games": len(games),
           "spreads": {linear.LAYOUT[i][1]: v for i, v in sp.items()},
           "scales": {name: s for (_, name), s in zip(linear.LAYOUT, scales)}, "scales_list": list(scales)}
    Path(a.out).write_text(json.dumps(doc, indent=1))
    print(f"{len(sp)} coordinates with a spread; scales min {min(scales):.3g} median "
          f"{sorted(scales)[len(scales) // 2]:.3g} max {max(scales):.3g}; wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
