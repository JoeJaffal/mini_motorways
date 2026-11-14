"""evolve7 smoke (plan 2026-11-14 section 4, Block D), on the real host:

  lambda = 6, m = 6, --force-cut (at least one early cut per generation), 3 generations, episode cap 300 s.
  Run A plays uninterrupted. Run B is started by the macOS watchdog (runs7.json entry), killed once during a
  4-map phase (generation 1) and once after it (the phase-B games of generation 2), and resumed by the watchdog
  each time. Pass: generations.jsonl records identical after removing wall_s / cache_hits / games_played, and the
  final pickled CMA mean and sigma equal; the watchdog log shows both resumes.

  python -m evolved_rules.ops.smoke7 [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "output" / "evolved_rules" / "ops"
SMOKE = ROOT / "output" / "evolved_rules" / "gp7" / "smoke"
RUNS = ROOT / "output" / "evolved_rules" / "evolve7"
PY = str(ROOT / ".venv" / "bin" / "python")
LABEL = "com.minimotorways.gp7-watchdog"
STRIP = ("wall_s", "cache_hits", "games_played")


def kick():
    subprocess.run(["launchctl", "kickstart", f"gui/{os.getuid()}/{LABEL}"], check=False)


def lines(p: Path) -> int:
    return len(p.read_text().splitlines()) if p.exists() else 0


def wait_for(cond, timeout=3600, poll=0.3):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(poll)
    raise TimeoutError("smoke: condition not reached")


def kill_b():
    pid = int((OPS / "smoke-b.pid").read_text())
    os.killpg(pid, signal.SIGKILL)
    time.sleep(2)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    from evolved_rules import linear
    from evolved_rules.ops.calibrate7 import L_PATH, gentle_weights
    SMOKE.mkdir(parents=True, exist_ok=True)
    cal = json.loads((ROOT / "output/evolved_rules/gp7/calibration/calibration_final.json").read_text())
    sp = linear.Space(l_text=L_PATH.read_text().strip(), theta=cal["theta"])
    x0 = linear.x_from_l(sp, gentle_weights(cal["b_t"], cal["w_is_evo"]))
    (SMOKE / "x0.json").write_text(json.dumps({"x": x0, "space": sp.to_json()}))
    common = (f"--x0 {SMOKE / 'x0.json'} --stop-at 2099-01-01T00:00:00+00:00 --workers {a.workers} --popsize 6 "
              f"--maps 6 --force-cut --cap 300 --max-gens 3")
    env = dict(os.environ, PYTHONHASHSEED="0")
    for r in ("smoke-a", "smoke-b"):
        if (RUNS / r).exists():
            raise SystemExit(f"{RUNS / r} exists: remove it first")
    t = time.time()
    subprocess.run([PY, "-m", "evolved_rules.evolve7", "--run", "smoke-a", *common.split()], cwd=ROOT, env=env,
                   check=True, stdout=subprocess.DEVNULL)
    print(f"run A: 3 generations uninterrupted in {time.time() - t:.0f} s", flush=True)

    runs7 = OPS / "runs7.json"
    entries = json.loads(runs7.read_text())
    entries = [e for e in entries if e.get("Name") != "smoke-b"]
    entries.append({"Name": "smoke-b", "Module": "evolved_rules.evolve7", "RepoDir": str(ROOT),
                    "Dir": "output/evolved_rules/evolve7/smoke-b", "Args": f"--run smoke-b {common}",
                    "ResumeArgs": "--run smoke-b --resume"})
    runs7.write_text(json.dumps(entries, indent=1))
    b = RUNS / "smoke-b"
    gens, cache = b / "generations.jsonl", b / "cache.jsonl"
    log_before = lines(OPS / "watchdog7.log")
    kick()
    wait_for(lambda: lines(gens) >= 1)
    base = lines(cache)
    wait_for(lambda: lines(cache) >= base + 2)  # inside generation 1's 4-map phase
    kill_b()
    print("run B: killed during generation 1's 4-map phase", flush=True)
    kick()
    wait_for(lambda: lines(gens) >= 2)
    base = lines(cache)
    rec = json.loads(gens.read_text().splitlines()[-1])
    phase_a = rec["distinct"] * 4 + 6  # an upper bound of the next generation's phase-A games
    wait_for(lambda: lines(cache) >= base + phase_a + 1, timeout=7200)  # inside generation 2's phase B
    kill_b()
    print("run B: killed during generation 2's phase B", flush=True)
    kick()
    wait_for(lambda: json.loads((b / "status.json").read_text()).get("status") == "budget"
             and lines(gens) >= 3, timeout=7200)
    entries = [e for e in json.loads(runs7.read_text()) if e.get("Name") != "smoke-b"]
    runs7.write_text(json.dumps(entries, indent=1))
    wd = (OPS / "watchdog7.log").read_text().splitlines()[log_before:]
    resumes = [l for l in wd if "start smoke-b" in l and "resume" in l]

    ra = [{k: v for k, v in json.loads(x).items() if k not in STRIP} for x in (RUNS / "smoke-a" / "generations.jsonl").read_text().splitlines()]
    rb = [{k: v for k, v in json.loads(x).items() if k not in STRIP} for x in gens.read_text().splitlines()]
    sa = pickle.loads((RUNS / "smoke-a" / "checkpoint.pkl").read_bytes())
    sb = pickle.loads((b / "checkpoint.pkl").read_bytes())
    ea, eb = pickle.loads(sa["es"]), pickle.loads(sb["es"])
    import numpy as np
    checks = {"records identical": ra == rb, "mean equal": bool(np.array_equal(ea.mean, eb.mean)),
              "sigma equal": bool(ea.sigma == eb.sigma), "cuts every generation": all(r["cut"] >= 1 for r in rb),
              "watchdog resumed twice": len(resumes) >= 2, "generations": len(rb)}
    (SMOKE / "smoke_result.json").write_text(json.dumps({"checks": checks, "watchdog": wd}, indent=1))
    print(json.dumps(checks, indent=1))
    ok = all(v for k, v in checks.items() if k != "generations") and len(rb) == 3
    print("SMOKE PASS" if ok else "SMOKE FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
