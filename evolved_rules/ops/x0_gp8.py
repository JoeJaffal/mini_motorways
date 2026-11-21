"""gp-8 start point: gp-7 final's coordinates in the gp-8 layout, plus the light and roundabout heads.

  PY -m evolved_rules.ops.x0_gp8 --out X0.json [--light-bias B] [--round-bias B] [--shut] [--no-tools]

gp-7 final is cma-7's in-bounds mean after generation 53 (final/gp7/runs/gp-7/final_mean.json, 84 coordinates in
gp-7's layout, which config.json records). Every gp-7 coordinate keeps its value and scale by name. The new ones:
  light  pl_placed, time (new terms of the light head)
  round  the roundabout head: round.bias + the same 10 terms
Head term scales (engineering choice, gp-8 draft section D; placement terms are not logged, so no spreads): one
unit of x is about one "typical" step of the term in the tree's units (raw / gp.SCALE):
  pl_stopped_near, pl_cars_near, pl_worst_colour_stuck, pl_placed 16 (4 cars or tools = 1)
  pl_max_wait_near, pl_mean_wait_near 32 (32 s = 1); pl_dist_worst_shop 4 (16 tiles = 1); pl_degree 2 (4 links = 1)
  time 4 (1024 s = 1); pl_doorstep 1; biases 1.
Head start (both heads): bias B, pl_stopped_near +1, pl_max_wait_near +1, pl_placed -1, every other term 0, so a
head fires only on a queue that is both long and old, less often as tools go down.
The light head's template (place.pl_stopped_near*worst_overcrowded) starts at 0.
--shut: biases -5 and every head term 0 (the identity gate's point: it never places).
--no-tools: lights and roundabouts off (must give gp-7 final's text exactly).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evolved_rules import gp, linear
from evolved_rules.engine import canonical_text

FINAL = Path(__file__).resolve().parents[1] / "final" / "gp7"
HEAD_SCALES = {"pl_stopped_near": 16.0, "pl_cars_near": 16.0, "pl_worst_colour_stuck": 16.0, "pl_placed": 16.0,
               "pl_max_wait_near": 32.0, "pl_mean_wait_near": 32.0, "pl_dist_worst_shop": 4.0, "pl_degree": 2.0,
               "time": 4.0, "pl_doorstep": 1.0}
HEAD_START = {"pl_stopped_near": 1.0, "pl_max_wait_near": 1.0, "pl_placed": -1.0}


def build(light_bias: float, round_bias: float, shut: bool, tools: bool) -> tuple[list[float], linear.Space]:
    cfg = json.loads((FINAL / "runs" / "gp-7" / "config.json").read_text(encoding="utf-8"))
    fm = json.loads((FINAL / "runs" / "gp-7" / "final_mean.json").read_text(encoding="utf-8"))
    old_layout = [tuple(x) for x in cfg["space"]["layout"]]
    old_scales, old_x = cfg["space"]["scales"], fm["x"]
    assert len(old_layout) == len(old_x) == len(old_scales) == 84
    by_name = {n: (old_x[i], old_scales[i]) for i, (_, n) in enumerate(old_layout)}
    x, scales = [], []
    for g, n in linear.LAYOUT:
        if n in by_name and g != "round":
            v, s = by_name[n]
        else:
            term = n.split(".", 1)[1] if n.startswith("round.") else n
            s = 1.0 if term == "bias" else HEAD_SCALES[term]
            v = 0.0
        if g in ("light", "round"):
            term = n.split(".", 1)[1] if n.startswith("round.") else n
            if term == "bias":
                v = -5.0 if shut else (light_bias if g == "light" else round_bias)
            else:
                s = HEAD_SCALES[term]
                v = 0.0 if shut else HEAD_START.get(term, 0.0)
        if n == f"place.{linear.PLACE_TEMPLATE[0]}*{linear.PLACE_TEMPLATE[1]}":
            v = 0.0  # unused in gp-7 (lights off), so its value there is drift
        x.append(float(v))
        scales.append(float(s))
    space = linear.Space(l_text=cfg["space"]["l_text"], scales=tuple(scales), theta=float(cfg["space"]["theta"]),
                         lights=tools, roundabouts=tools)
    if any(abs(v) > linear.BOUND for v in x):
        raise ValueError("x0 outside the bounds")
    return x, space


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--light-bias", type=float, default=-3.0)
    p.add_argument("--round-bias", type=float, default=-3.0)
    p.add_argument("--shut", action="store_true")
    p.add_argument("--no-tools", action="store_true")
    a = p.parse_args(argv)
    x, space = build(a.light_bias, a.round_bias, a.shut, not a.no_tools)
    text = linear.text_from_x(x, space)
    b7 = canonical_text((FINAL / "challengers" / "gp7_final.txt").read_text(encoding="utf-8"))
    off = linear.text_from_x(x, linear.Space(l_text=space.l_text, scales=space.scales, theta=space.theta))
    if off != b7:  # the gp-7 part must decode to gp-7 final exactly
        print("tools-off text differs from gp7_final.txt", file=sys.stderr)
        return 1
    doc = {"x": x, "space": space.to_json(), "scale_norm": 1.0,
           "note": {"light_bias": a.light_bias, "round_bias": a.round_bias, "shut": a.shut, "tools": not a.no_tools}}
    Path(a.out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    Path(a.out).with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
    print(f"{a.out}: dim {len(x)}, text hash {gp.text_hash(text) if hasattr(gp, 'text_hash') else len(text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
