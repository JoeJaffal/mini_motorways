"""gp-7 screen (plan 2026-11-14 section 5): play the screen points on 3300-(3299+n_s) with decision logging, chunked.

  python -m evolved_rules.ops.screen7 run --points POINTS.json --seeds 3300-3599 --workers 10
  python -m evolved_rules.ops.screen7 analyse --points POINTS.json --seeds 3300-3599 --l-runs DIR

`run` is restartable: each (point, 100-seed chunk) writes <out>/<point>/chunk-<first>.json when done and is skipped
afterwards; games are cached (<out>/cache.jsonl). It honours <main>/output/evolved_rules/ops/screen.pause (wait).
Run it from the frozen C4-min worktree (plan section 4), with EVOLVED_RULES_HOST_DLL set to the main clone's DLL.
It never prints scores. `analyse` pairs every point with L's pre-played games (gp6-final code, battery7 chunks
pre-L-screen-*) and applies the x0* rule (plan section 5); it writes <out>/screen_result.json.

POINTS.json: {"points": {name: text}, "space_lights": {...}} as written by `points`:
  python -m evolved_rules.ops.screen7 points --calibration FILE.json --out POINTS.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "evolved_rules" / "gp7" / "screen"
PAUSE = ROOT / "output" / "evolved_rules" / "ops" / "screen.pause"
L_PATH = ROOT / "evolved_rules" / "seeds" / "gp7" / "cma1_3tree.txt"
ROUTE_POINTS = ("gentle", "fast", "bypass", "jam_avoid")
# Rate minimums for screen eligibility (plan 3.2/5), pre-registered: an evo or pair route built in >= 3% of decisions,
# and a target-head pair opened in >= 5% of decisions (half of the 10% calibration target, allowing for trajectory noise).
EVO_MIN, PAIR_MIN = 0.03, 0.05


def make_points(cal: dict) -> dict:
    """The five new-code screen points from the calibration result (plan 5; interpretations in the docstring of
    the pre-registration): every point has L's rule weights."""
    from evolved_rules import linear
    from evolved_rules.ops.calibrate7 import gentle_weights
    L = L_PATH.read_text().strip()
    theta = cal["theta"]
    g = gentle_weights(cal["b_t"], cal["w_is_evo"])
    fast_cost = {"w_reuse": 1.0, "w_jl": 1.0}
    fast = {**g, **fast_cost, "is_evo": 1.0}
    bypass = {**fast, "w_con": 5.0, "b_t": -5.0 - cal["bypass_c"], "target.w_ttmpl": 1.0, "n_t": 3.0}
    jam = {**g, "w_stop": 0.4, "w_car": 0.1}
    pts = {}
    sp = linear.Space(l_text=L, theta=theta)
    for name, w in (("gentle", g), ("fast", fast), ("bypass", bypass), ("jam_avoid", jam)):
        pts[name] = linear.text_from_x(linear.x_from_l(sp, w), sp)
    spl = linear.Space(l_text=L, theta=theta, lights=True)
    lw = linear.l_rule_weights(spl)
    lights = {"pl_stopped_near": 1.0, "upgrade.type_3": linear.snap(lw["upgrade.type_3"] + 0.8)}
    pts["lights"] = linear.text_from_x(linear.x_from_l(spl, lights), spl)
    return {"points": pts, "weights": {"gentle": g, "fast": fast, "bypass": bypass, "jam_avoid": jam,
                                       "lights": lights}, "calibration": cal}


def cmd_points(a) -> int:
    cal = json.loads(Path(a.calibration).read_text())
    doc = make_points(cal)
    Path(a.out).write_text(json.dumps(doc, indent=1))
    print(f"wrote {a.out}: {', '.join(doc['points'])}")
    return 0


def cmd_run(a) -> int:
    from evolved_rules.engine import Engine
    from evolved_rules.evolve import text_hash
    doc = json.loads(Path(a.points).read_text())
    lo, hi = (int(x) for x in a.seeds.split("-"))
    OUT.mkdir(parents=True, exist_ok=True)
    with Engine(workers=a.workers, cache_path=OUT / "cache.jsonl") as eng:
        for start in range(lo, hi + 1, a.chunk):
            seeds = list(range(start, min(start + a.chunk - 1, hi) + 1))
            for name, text in doc["points"].items():
                done = OUT / name / f"chunk-{start}.json"
                if done.exists():
                    continue
                while PAUSE.exists():
                    time.sleep(60)
                t = time.time()
                games = eng.play_logged([(text, s) for s in seeds], OUT / name / "decisions")
                done.parent.mkdir(parents=True, exist_ok=True)
                (OUT / name / "policy.txt").write_text(text + "\n")
                done.write_text(json.dumps({"point": name, "hash": text_hash(text), "seeds": seeds,
                                            "games": games, "wall_s": time.time() - t}))
                print(f"{time.strftime('%F %T')} {name} chunk {start}: done ({time.time() - t:.0f} s)", flush=True)
    (OUT / "run.done").write_text(time.strftime("%F %T"))
    return 0


def _load_point(name: str) -> dict[int, dict]:
    out = {}
    for f in sorted((OUT / name).glob("chunk-*.json")):
        for g in json.loads(f.read_text())["games"]:
            out[int(g["scenario_seed"])] = g
    return out


def _load_l(runs: Path, prefix: str = "pre-L-screen") -> dict[int, dict]:
    out = {}
    for d in sorted(runs.glob(f"{prefix}-*")):
        if ".failed" in d.name or not (d / "games.jsonl").exists():
            continue
        for line in (d / "games.jsonl").read_text().splitlines():
            g = json.loads(line)
            out[int(g["scenario_seed"])] = g
    return out


def cmd_analyse(a) -> int:
    from evolved_rules.ops.calibrate7 import load_records, rates
    doc = json.loads(Path(a.points).read_text())
    lo, hi = (int(x) for x in a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    Lg = _load_l(Path(a.l_runs))
    res = {"seeds": a.seeds, "points": {}}
    for name in doc["points"]:
        P = _load_point(name)
        common = [s for s in seeds if s in P and s in Lg]
        d = [P[s]["trips"] - Lg[s]["trips"] for s in common]
        n = len(d)
        mean = statistics.fmean(d) if d else math.nan
        se = statistics.stdev(d) / math.sqrt(n) if n > 1 else math.nan
        recs = load_records(OUT / name / "decisions")
        b_t = doc["weights"].get(name, {}).get("b_t", 0.0)
        r = rates(recs, b_t) if recs else {}
        res["points"][name] = {
            "n": n, "diff_mean": mean, "diff_se": se, "z": mean / se if se and se > 0 else math.nan,
            "point_mean": statistics.fmean(P[s]["trips"] for s in common) if common else math.nan,
            "L_mean": statistics.fmean(Lg[s]["trips"] for s in common) if common else math.nan,
            "rejected_actions": sum(P[s]["rejected_actions"] for s in common), "rates": r,
            "meets_rate_minimums": bool(r) and name in ROUTE_POINTS and r.get("evo_built", 0) >= EVO_MIN
            and r.get("pair_open", 0) >= PAIR_MIN,
        }
    pts = res["points"]
    elig = [k for k in ROUTE_POINTS if k in pts and pts[k]["meets_rate_minimums"]]
    best = max(elig, key=lambda k: pts[k]["diff_mean"]) if elig else None
    if best is not None and pts[best]["diff_mean"] >= 0:
        route, rate_factor = best, 1.0
    else:
        z = pts.get("gentle", {}).get("z", 0.0)
        route = "gentle"
        rate_factor = 0.25 if z < -2 else (0.5 if z < -1 else 1.0)
    lights = pts.get("lights", {}).get("diff_mean", -1) >= 0
    bug = {k: ("< -3 SE" if v["z"] < -3 else "") + (" rejected draws" if v["rejected_actions"] else "")
           for k, v in pts.items() if v["z"] < -3 or v["rejected_actions"]}
    res["x0_star"] = {"route_point": route, "rate_factor": rate_factor, "lights": lights,
                      "eligible_route_points": elig, "bug_gate": bug}
    (OUT / "screen_result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["x0_star"], indent=1))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("points")
    q.add_argument("--calibration", required=True)
    q.add_argument("--out", required=True)
    r = sub.add_parser("run")
    r.add_argument("--points", required=True)
    r.add_argument("--seeds", default="3300-3599")
    r.add_argument("--chunk", type=int, default=100)
    r.add_argument("--workers", type=int, default=10)
    s = sub.add_parser("analyse")
    s.add_argument("--points", required=True)
    s.add_argument("--seeds", default="3300-3599")
    s.add_argument("--l-runs", required=True)
    a = p.parse_args()
    return {"points": cmd_points, "run": cmd_run, "analyse": cmd_analyse}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
