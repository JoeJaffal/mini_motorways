"""gp-7: from the screen to the cma-7 launch (plan 2026-11-14 sections 4 Blocks C-E, 5, 8.4).

  python -m evolved_rules.ops.launch7 prepare      # screen analysis, x0*, scales, x0.json / space.json (no commit)
  python -m evolved_rules.ops.launch7 gate4        # identity gate (4) with the frozen space (20 close-out maps)
  python -m evolved_rules.ops.launch7 launch       # pre-registration, commit + tag cma7-launch, worktree, watchdog

x0* (plan 5): the route point (gentle, fast, bypass, jam_avoid) with the largest paired difference vs L among those
meeting the rate minimums, if >= 0; otherwise Gentle with its rates halved (difference < -1 SE) or quartered
(< -2 SE): b_t re-solved for 10% x factor pair opens and the is_evo weight lowered for factor x the first-pass evo
rate, both from Gentle's screen records. Lights' head is added if Lights' difference >= 0. New routes never off.
Files: output/evolved_rules/gp7/launch/{x0.json, space.json, scales.json, launch.json}.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT.parent
SCREEN_OUT = DESK / "mm-gp7-screen" / "output" / "evolved_rules" / "gp7" / "screen"
L_RUNS = DESK / "mm-gp6-final" / "output" / "evolved_rules" / "runs"
CAL = ROOT / "output" / "evolved_rules" / "gp7" / "calibration"
POINTS = ROOT / "output" / "evolved_rules" / "gp7" / "screen-points.json"
OUT = ROOT / "output" / "evolved_rules" / "gp7" / "launch"
OPS = ROOT / "output" / "evolved_rules" / "ops"
T_STOP = "2026-11-19T01:22:00+02:00"
WORKTREE = DESK / "mm-cma7"
DLL = ROOT / "simulation" / "Headless" / "bin" / "Release" / "net8.0" / "TrafficHost.dll"


def git(*a, check=True) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=check).stdout.strip()


def cmd_prepare(a) -> int:
    from evolved_rules import linear
    from evolved_rules.evolve import text_hash
    from evolved_rules.ops import screen7
    from evolved_rules.ops.calibrate7 import (L_PATH, load_records, solve_b_t, solve_w_evo)
    from evolved_rules.ops.scales7 import spreads
    screen7.OUT = SCREEN_OUT
    ns = argparse.Namespace(points=str(POINTS), seeds="3300-3599", l_runs=str(L_RUNS))
    screen7.cmd_analyse(ns)
    res = json.loads((SCREEN_OUT / "screen_result.json").read_text())
    doc = json.loads(POINTS.read_text())
    x = res["x0_star"]
    bug_note = None
    if x["bug_gate"]:
        print(f"BUG GATE: {x['bug_gate']} -> 2 h bug check before launch (plan 5)")
        if any("SE" in v for v in x["bug_gate"].values()) or not a.bug_checked:
            return 3  # a point < -3 SE always stops; rejected draws need a written bug check (--bug-checked)
        bug_note = Path(a.bug_checked).read_text()
        print(f"bug check on record: {a.bug_checked}")
    w = dict(doc["weights"][x["route_point"]])
    rate_note = "as screened"
    if x["rate_factor"] < 1.0:
        recs = load_records(SCREEN_OUT / "gentle" / "decisions")
        w["b_t"] = round(solve_b_t(recs, 0.10 * x["rate_factor"]), 4)
        from evolved_rules.ops.calibrate7 import evo_first_rate
        from evolved_rules.agent import _LOG_CAND_TERMS
        base = evo_first_rate(recs, 0.0, _LOG_CAND_TERMS.index("is_evo"))
        w["is_evo"] = solve_w_evo(recs, w.get("is_evo", 0.0), base * x["rate_factor"])
        rate_note = f"Gentle rates x{x['rate_factor']}: b_t {w['b_t']}, is_evo {w['is_evo']}"
    lights = bool(x["lights"])
    if lights:
        w.update(doc["weights"]["lights"])
    L = L_PATH.read_text().strip()
    dirs = sorted(CAL.glob("round*/decisions")) + sorted(SCREEN_OUT.glob("*/decisions"))
    games = [g for d in dirs for g in load_records(d)]
    sp = spreads(games)
    theta = doc["calibration"]["theta"]
    named = {**linear.l_rule_weights(linear.Space(l_text=L)), **linear.SEPARATED_COST, **w}
    scales = linear.scales_for_x0(sp, named)
    space = linear.Space(l_text=L, scales=scales, theta=theta, lights=lights)
    x0 = linear.x_from_l(space, w)
    text = linear.text_from_x(x0, space)
    OUT.mkdir(parents=True, exist_ok=True)
    sj = space.to_json()
    sj.pop("slot_trees", None)  # the v1 decoder's form (cma-7 runs gp7-v1)
    (OUT / "space.json").write_text(json.dumps(sj, indent=1))
    (OUT / "x0.json").write_text(json.dumps({"x": x0, "space": sj, "scale_norm": linear.scale_norm(sp),
                                            "weights": w, "route_point": x["route_point"], "lights": lights}))
    (OUT / "x0_text.txt").write_text(text + "\n")
    (OUT / "scales.json").write_text(json.dumps({"decisions": sum(len(g) for g in games), "games": len(games),
                                                "spreads": {linear.LAYOUT[i][1]: v for i, v in sp.items()},
                                                "scales": dict(zip([n for _, n in linear.LAYOUT], scales))}, indent=1))
    info = {"x0_star": x, "rate_note": rate_note, "weights": w, "lights": lights, "theta": theta,
            "x0_hash": text_hash(text), "space_hash": text_hash(json.dumps(sj, sort_keys=True)),
            "L_hash": text_hash(L), "bug_check": bug_note, "max_abs_x0": max(abs(v) for v in x0), "decisions_for_scales":
            sum(len(g) for g in games), "screen": res["points"]}
    (OUT / "launch.json").write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != "screen"}, indent=1))
    return 0


def cmd_gate4(a) -> int:
    return subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "evolved_rules.ops.identity7", "--gates", "4",
                           "--space", str(OUT / "space.json"), "--workers", str(a.workers)], cwd=ROOT).returncode


def cmd_launch(a) -> int:
    info = json.loads((OUT / "launch.json").read_text())
    rep = json.loads((ROOT / "output/evolved_rules/gp7/identity/report.json").read_text())
    g4 = [v for k, v in rep["gates"].items() if "frozen space" in k]
    if not g4 or not g4[0]["pass"]:
        print("identity gate (4) with the frozen space has not passed: not launching")
        return 4
    stats_commit = git("log", "-1", "--format=%h", "--", "evolved_rules/stats7.py")
    pre = ROOT / "evolved_rules" / "plans" / "2026-11-14-gp7-preregistration.md"
    s = pre.read_text()
    x = info["x0_star"]
    sc = json.loads((OUT / "scales.json").read_text())["scales"]
    vals = sorted(sc.values())
    s = (s.replace("(DRAFT, filled in before launch)", "(frozen at launch)")
          .replace("__L_HASH__", info["L_hash"]).replace("__STATS_COMMIT__", stats_commit)
          .replace("__T_STOP__", T_STOP.replace("T", " "))
          .replace("__SCALES__", f"84 scales, min {vals[0]:.3g}, median {vals[42]:.3g}, max {vals[-1]:.3g}; "
                                 f"from {info['decisions_for_scales']} logged decisions (calibration + screen)")
          .replace("__SPACE_HASH__", info["space_hash"]).replace("__THETA__", repr(info["theta"]))
          .replace("__X0_RESULT__", f"route point **{x['route_point']}** ({info['rate_note']}), lights "
                                    f"{'on' if info['lights'] else 'off'}; eligible {x['eligible_route_points']}; "
                                    f"x0* text hash {info['x0_hash']}, max |x0| {info['max_abs_x0']:.2f}")
          .replace("__BUG_CHECK__", (info.get("bug_check") or "no bug gate").splitlines()[0]
                   + (" (full note: plans/gp7-launch/bug-check.md)" if info.get("bug_check") else ""))
          .replace("__F_STATUS__", "neither: C4-min passed every identity gate and the smoke (no F1, no F2)"))
    s += ("\n## Screen (plan section 5; never quote x0*'s screen number, validation re-measures it)\n\n"
          "| Point | n | Paired diff vs L | SE | Pair opens | Evo built | Rejected draws |\n|---|---|---|---|---|---|---|\n")
    for k, v in info["screen"].items():
        r = v.get("rates") or {}
        s += (f"| {k} | {v['n']} | {v['diff_mean']:+.1f} | {v['diff_se']:.1f} | {r.get('pair_open', 0):.1%} | "
              f"{r.get('evo_built', 0):.1%} | {v['rejected_actions']} |\n")
    pre.write_text(s)
    (ROOT / "evolved_rules" / "plans" / "gp7-launch").mkdir(exist_ok=True)
    if info.get("bug_check"):
        (OUT / "bug-check.md").write_text(info["bug_check"])
    for f in ("x0.json", "space.json", "scales.json", "launch.json", "x0_text.txt") + (("bug-check.md",) if info.get("bug_check") else ()):
        (ROOT / "evolved_rules" / "plans" / "gp7-launch" / f).write_text((OUT / f).read_text())
    git("add", str(pre), "evolved_rules/plans/gp7-launch")
    git("commit", "-q", "-m", f"gp-7 pre-registration and cma-7 launch files (x0* = {x['route_point']}) (gp-7)")
    git("tag", "-f", "cma7-launch")
    head = git("rev-parse", "HEAD")
    if not WORKTREE.exists():
        git("worktree", "add", str(WORKTREE), "cma7-launch")
    x0 = WORKTREE / "evolved_rules" / "plans" / "gp7-launch" / "x0.json"
    runs7 = OPS / "runs7.json"
    entries = [e for e in json.loads(runs7.read_text()) if e.get("Name") != "cma-7"]
    entries.append({"Name": "cma-7", "Module": "evolved_rules.evolve7", "RepoDir": str(WORKTREE),
                    "Dir": "output/evolved_rules/evolve7/cma-7",
                    "Args": f"--run cma-7 --x0 {x0} --stop-at {T_STOP} --workers {a.workers} --popsize 24 --maps 12 "
                            f"--sigma0 0.3 --seed 1 --log-gen0",
                    "ResumeArgs": "--run cma-7 --resume", "Env": {"EVOLVED_RULES_HOST_DLL": str(DLL)}})
    runs7.write_text(json.dumps(entries, indent=1))
    subprocess.run(["launchctl", "kickstart", f"gui/{__import__('os').getuid()}/com.minimotorways.gp7-watchdog"])
    print(f"launched cma-7 from {WORKTREE} at {head}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--bug-checked", default="", help="written bug check for rejected draws (plan 5 bug gate)")
    g = sub.add_parser("gate4")
    g.add_argument("--workers", type=int, default=6)
    l = sub.add_parser("launch")
    l.add_argument("--workers", type=int, default=10)
    a = p.parse_args()
    return {"prepare": cmd_prepare, "gate4": cmd_gate4, "launch": cmd_launch}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
