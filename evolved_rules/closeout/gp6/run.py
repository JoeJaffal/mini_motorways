"""gp-6/cma-6 close-out (plan C0): 7 policies on LA 5100-5299 (200 never-played maps), gp6-v1 code, in-repo f34 host."""
import os, subprocess, sys, time
from evolved_rules.power import keep_awake
A = "output/evolved_rules/analysis/gp6-closeout"
SEEDS = "5100-5299"
RUNS = [
    ("c6-cma1-5tree", f"tree:{A}/rules/cma1_5tree.txt"),    # gp-6 incumbent 1d6a7017 (clean on), the reference
    ("c6-cma1-3tree", f"tree:{A}/rules/cma1_3tree.txt"),    # fa7648c7 (clean off)
    ("c6-cma6-mean", f"tree:{A}/rules/cma6_mean.txt"),      # cma-6 final distribution mean 39954974
    ("c6-cma6-best", f"tree:{A}/rules/cma6_best.txt"),      # cma-6 incumbent 3d999a2c
    ("c6-gp6-7fa4b2ec", f"tree:{A}/rules/gp6_7fa4b2ec.txt"),  # gp-6's closest challenger, 29 nodes
    ("c6-separated", "separated"),
    ("c6-hand", "hand"),
]
env = dict(os.environ, PYTHONHASHSEED="0")
with keep_awake():
    for run, policy in RUNS:
        t = time.time()
        print(f"=== {time.strftime('%H:%M:%S')} {run} ({policy})", flush=True)
        out = subprocess.run([sys.executable, "-m", "evolved_rules.evaluate", "--policy", policy, "--seeds", SEEDS,
                              "--workers", "12", "--run", run], env=env, capture_output=True, text=True)
        text = (out.stdout + out.stderr).strip()
        print(text.splitlines()[-1] if text else "(no output)", f"[{time.time() - t:.0f} s, exit {out.returncode}]",
              flush=True)
        if out.returncode:
            print(text[-3000:], flush=True)
print(f"=== {time.strftime('%H:%M:%S')} done", flush=True)
