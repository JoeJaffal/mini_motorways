"""gp-7 validation pick (plan 2.2): C* from the validation games, by stats7.decide_headline, and nothing else.

  PY -m evolved_rules.ops.pick7 --challengers x0star,cma7_final,gp7_final --out FILE

Reads each challenger's validation chunks <CH_RUNS>/val-<name>-<chunk>/games.jsonl and L's pre-played
<L_RUNS>/pre-L-val-<chunk>/games.jsonl (seed = scenario_seed), calls decide_headline(val, val_L, None, {}) and
writes {c_star, validation_seeds, validation_mean_diff, reason} to --out. Exit 0 with a C*, 3 if every
difference is <= 0 (headline L, the test is then the user's call), 2 if validation is incomplete.
It never reads test games.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evolved_rules.stats7 import decide_headline

BASE = Path(__file__).resolve().parents[3]
CH_RUNS = BASE / "mm-gp7-final/output/evolved_rules/runs"
L_RUNS = BASE / "mm-gp6-final/output/evolved_rules/runs"
VAL = range(1550, 1750)


def games(runs: Path, prefix: str) -> dict[int, float]:
    out = {}
    for d in sorted(runs.glob(f"{prefix}-*")):
        if ".failed" in d.name or not (d / "summary.json").exists():
            continue
        for line in (d / "games.jsonl").read_text().splitlines():
            g = json.loads(line)
            out[int(g["scenario_seed"])] = float(g["trips"])
    return {s: v for s, v in out.items() if s in VAL}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--challengers", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    val = {c: games(CH_RUNS, f"val-{c}") for c in a.challengers.split(",")}
    val_L = games(L_RUNS, "pre-L-val")
    missing = {k: len(VAL) - len(v) for k, v in {**val, "L": val_L}.items() if len(v) != len(VAL)}
    if missing:
        print(f"validation incomplete (missing seeds): {missing}")
        return 2
    r = decide_headline(val, val_L, None, {})
    rec = {k: r.get(k) for k in ("c_star", "validation_seeds", "validation_mean_diff", "reason")}
    Path(a.out).write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec))
    return 0 if r.get("c_star") else 3


if __name__ == "__main__":
    sys.exit(main())
