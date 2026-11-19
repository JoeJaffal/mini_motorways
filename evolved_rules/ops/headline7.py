"""gp-7 test headline (plan 2.3), run once on 2026-11-19 after the test completed.

  PYTHONPATH=. PY evolved_rules/ops/headline7.py OUT.json

Reads the validation and test games (C* from ../mm-gp7-final, L and hand from ../mm-gp6-final), calls
stats7.decide_headline(val, val_L, test_c, test_L) and adds the descriptive test stats and headline vs hand.
The plan 2.4 gp-7 vs cma-7 validation secondary (paired_t_two_sided, Holm over 2) was added to
final/gp7/headline7.json in a second step with the same stats7 functions.
"""
import json, statistics, sys
from pathlib import Path
from evolved_rules.stats7 import decide_headline, paired_diffs, paired_t_one_sided, bca_interval, wilcoxon_one_sided
B = Path("/Users/mounir/Desktop/mini_motorways")
CH = B/"mm-gp7-final/output/evolved_rules/runs"; LR = B/"mm-gp6-final/output/evolved_rules/runs"
def games(runs, prefix, rng):
    out = {}
    for d in sorted(runs.glob(f"{prefix}-*")):
        if ".failed" in d.name or not (d/"summary.json").exists(): continue
        for line in (d/"games.jsonl").read_text().splitlines():
            g = json.loads(line); out[int(g["scenario_seed"])] = float(g["trips"])
    return {s: v for s, v in out.items() if s in rng}
VAL, TEST = range(1550,1750), range(6100,7000)
val = {c: games(CH, f"val-{c}", VAL) for c in ("x0star","cma7_final","gp7_final")}
val_L = games(LR, "pre-L-val", VAL)
tc = games(CH, "test-gp7_final", TEST); tL = games(LR, "pre-L-test", TEST); th = games(LR, "pre-hand-test", TEST)
print("counts", {k: len(v) for k, v in val.items()}, len(val_L), len(tc), len(tL), len(th))
r = decide_headline(val, val_L, tc, tL)
# secondary, descriptive: vs hand on test
seeds = list(TEST)
dh = paired_diffs(tc, th, seeds)
r["secondary_vs_hand_test"] = {**paired_t_one_sided(dh), "bca90": list(bca_interval(dh, 0.90)),
    "wilcoxon_p_one_sided": wilcoxon_one_sided(dh), "mean_hand": statistics.fmean(th[s] for s in seeds)}
xs = sorted(tc[s] for s in seeds)
r["test_c_descriptive"] = {"median": statistics.median(xs), "min": xs[0], "max": xs[-1], "sd": statistics.stdev(xs),
    "median_L": statistics.median(tL[s] for s in seeds), "max_L": max(tL[s] for s in seeds),
    "wins_vs_L": sum(tc[s] > tL[s] for s in seeds), "ties_vs_L": sum(tc[s] == tL[s] for s in seeds)}
json.dump(r, open(sys.argv[1], "w"), indent=1, default=float)
print(json.dumps(r, indent=1, default=float))
