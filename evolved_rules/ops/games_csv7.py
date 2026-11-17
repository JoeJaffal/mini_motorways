"""Per-game CSV of the gp-7 / cma-7 training games, rebuilt from the run caches (read-only, plays no games).

  PY -m evolved_rules.ops.games_csv7 [--out DIR]

Reads only the evolve7 training caches (cache.jsonl, generations.jsonl, slots.jsonl) of the two arms. It never
reads validation or test results. gp-7's generations 0-16 are the shared trunk, whose games live in cma-7's cache
(arm "cma-7", shared_trunk=1). They are not repeated.

Writes:
  games7.csv     one row per game: arm, gen, role, policy, policy rank and mean over its games in that generation (12 maps; fewer if cut), seed, every scalar in the
                 cached result, and the action counts (draw / wait / upgrade = choices made).
                 role pending = a generation still being played (assigned on the next rebuild).
                 cars / houses / bridges_built are blank: not stored per game.
  policies7.csv  policy hash -> text.

Self-check (exit 1 on failure): for every finished generation, the rows reproduce trend_monitor.trips in seed
order, population.average, population.best and the completed-candidate count; stopped-early candidates are role candidate_cut.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARMS = {"cma-7": ROOT / "mm-cma7/output/evolved_rules/evolve7/cma-7",
        "gp-7": ROOT / "mm-gp7arm/output/evolved_rules/evolve7/gp-7"}
TRUNK_LAST = 16
SCALARS = ["trips", "seconds", "commands", "rejected_actions", "tiles_built", "trips_per_tile", "road_tiles_at_failure",
           "failed_shop", "mean_car_wait", "max_car_wait", "terminated", "truncated", "city", "simulator_version"]
ACTIONS = ["draw", "wait", "upgrade"]


def text_hash(t: str) -> str:  # same as evolved_rules.evolve.text_hash
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def jsonl(p: Path) -> list[dict]:
    out = []
    if p.exists():
        for line in p.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:  # partial last line while the run writes
                pass
    return out


def flags(t: str) -> dict:
    for line in t.splitlines():
        if line.startswith("flags:"):
            return dict(kv.split("=") for kv in line[6:].split())
    return {}


def build_arm(arm: str, d: Path, texts: dict) -> tuple[list[dict], list[str]]:
    gens = jsonl(d / "generations.jsonl")
    slots = jsonl(d / "slots.jsonl")
    games = defaultdict(dict)  # hash -> seed -> result
    for r in jsonl(d / "cache.jsonl"):
        if "trips" not in r.get("result", {}):
            continue
        h = text_hash(r["text"])
        texts.setdefault(h, r["text"])
        games[h][r["seed"]] = r["result"]
    rows, errors, used = [], [], set()
    if arm == "gp-7":  # gens 0-16 are the shared trunk, whose games are in cma-7's cache
        gens = [g for g in gens if g["gen"] > TRUNK_LAST]
    for g in gens:
        seeds, gn, tm = g["seeds"], g["gen"], g["trend_monitor"]["hash"]
        cands = [h for h, s in games.items() if h != tm and all(x in s for x in seeds)]
        means = {h: sum(games[h][x]["trips"] for x in seeds) / len(seeds) for h in cands}
        rank = {h: i + 1 for i, h in enumerate(sorted(cands, key=lambda h: -means[h]))}
        for h in cands + ([tm] if tm in games else []):
            role = "mean_policy" if h == tm else "candidate"
            m = sum(games[h][x]["trips"] for x in seeds) / len(seeds)
            for x in seeds:
                if x in games[h]:
                    rows.append(row(arm, gn, role, h, rank.get(h, ""), m, x, games[h][x], texts[h]))
                    used.add((h, x))
        # self-check
        if len(cands) != g["completed"]:
            errors.append(f"{arm} gen {gn}: {len(cands)} complete candidates, record says {g['completed']}")
        elif cands:
            avg, best = sum(means.values()) / len(means), max(means.values())
            if abs(avg - g["population"]["average"]) > 1e-6 or abs(best - g["population"]["best"]) > 1e-6:
                errors.append(f"{arm} gen {gn}: average/best {avg:.3f}/{best:.3f} vs record "
                              f"{g['population']['average']:.3f}/{g['population']['best']:.3f}")
        tmt = [games.get(tm, {}).get(x, {}).get("trips") for x in seeds]
        if tmt != g["trend_monitor"]["trips"]:
            errors.append(f"{arm} gen {gn}: mean-policy trips {tmt} vs record {g['trend_monitor']['trips']}")
    epoch_of = {}
    for e in slots:
        if e.get("probes"):
            for p in range(e["probes"][0], e["probes"][1] + 1):
                epoch_of[p] = e["gen"]
    # candidates stopped early (completed < distinct): their few games are a subset of one generation's seeds
    short = [g for g in gens if g["completed"] < g["distinct"]]
    for h, s in games.items():
        left = [x for x in s if (h, x) not in used and x < 10000]
        hits = [g for g in short if left and all(x in g["seeds"] for x in left)]
        if len(hits) == 1:
            m = sum(s[x]["trips"] for x in left) / len(left)
            for x in left:
                rows.append(row(arm, hits[0]["gen"], "candidate_cut", h, "", m, x, s[x], texts[h]))
                used.add((h, x))
    for h, s in games.items():
        for x, res in s.items():
            if (h, x) in used:
                continue
            if x >= 10000:
                rows.append(row(arm, epoch_of.get(x, ""), "race_probe", h, "", "", x, res, texts[h]))
            else:
                rows.append(row(arm, "", "pending", h, "", "", x, res, texts[h]))
    return rows, errors


def row(arm, gen, role, h, rank, mean, seed, res, text) -> dict:
    f = flags(text)
    r = {"arm": arm, "gen": gen, "shared_trunk": int(arm == "cma-7" and gen != "" and gen <= TRUNK_LAST),
         "role": role, "policy": h, "policy_rank": rank,
         "policy_mean": round(mean, 3) if mean != "" else "", "seed": seed}
    for k in SCALARS:
        v = res.get(k)
        r[k] = int(v) if isinstance(v, bool) else round(v, 4) if isinstance(v, float) else v
    ac = res.get("action_counts", {})
    for k in ACTIONS:
        r[f"n_{k}"] = ac.get(k, 0)
    r["lights_flag"], r["roundabouts_flag"] = f.get("lights", ""), f.get("roundabouts", "")
    for k in ("cars", "houses", "bridges_built"):  # not stored per game: blank, not zero
        r[k] = ""
    return r


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(ROOT / "mini_motorways/output/evolved_rules/games"))
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    texts, rows, errors = {}, [], []
    for arm, d in ARMS.items():
        r, e = build_arm(arm, d, texts)
        rows += r
        errors += e
    rows.sort(key=lambda r: (r["arm"], r["gen"] if r["gen"] != "" else 10**9, r["role"],
                             r["policy_rank"] if r["policy_rank"] != "" else 0, r["policy"], r["seed"]))
    with open(out / "games7.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(out / "policies7.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["policy", "text"])
        for h in sorted({r["policy"] for r in rows}):
            w.writerow([h, texts[h]])
    by = defaultdict(int)
    for r in rows:
        by[(r["arm"], r["role"])] += 1
    print(f"{len(rows)} games -> {out / 'games7.csv'}; " + ", ".join(f"{k[0]} {k[1]} {v}" for k, v in sorted(by.items())))
    if errors:
        print("SELF-CHECK FAILED:\n  " + "\n  ".join(errors[:20]) + (f"\n  ... {len(errors)} total" if len(errors) > 20 else ""))
        return 1
    print("self-check PASS: every finished generation reproduces mean-policy trips, population average/best, distinct")
    return 0


if __name__ == "__main__":
    sys.exit(main())
