"""gp-7 fork gate (plan 3.4 fork procedure, step 2), on the real trunk snapshot.

  PY -m evolved_rules.ops.forkgate7 draws --snapshot DIR [--fork] --out FILE
      The next generation's map seeds, ask() draws and decoded texts from a trunk snapshot (checkpoint.pkl and
      config.json at a generation boundary), exactly as evolve7.generation draws them. With --fork the state and
      space come from evolve7.fork() into a temporary folder, i.e. the gp-7 arm's own start. Run once from the
      trunk's worktree (v1, no --fork) and once from the arm's worktree (v2, --fork), then compare.
  PY -m evolved_rules.ops.forkgate7 compare A.json B.json
      Byte-identical seeds, draws and texts, or exit 1.
  PY -m evolved_rules.ops.forkgate7 games --snapshot DIR --n 8 --workers 4 --out FILE
      Replays the last n (text, seed) jobs of the trunk's cache.jsonl with this code (no cache) and compares
      trips, seconds and commands with the trunk's results. Exit 1 on any difference.
"""
from __future__ import annotations

import argparse
import json
import pickle
import random
import sys
import tempfile
from pathlib import Path


def _draws(snapshot: Path, use_fork: bool) -> dict:
    import numpy as np
    from evolved_rules import evolve7 as E, linear
    from evolved_rules.evolve import text_hash
    conf = json.loads((snapshot / "config.json").read_text())
    if use_fork:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, state, space = E.fork(snapshot, Path(tmp) / "arm", workers=1, stop_at=None)
        if state.get("space") is not None:
            space = linear.Space.from_json(state["space"])
    else:
        with open(snapshot / "checkpoint.pkl", "rb") as f:
            state = pickle.load(f)
        space = linear.Space.from_json(conf["space"])
    random.setstate(state["rng"])
    np.random.set_state(state["np_rng"])
    es = pickle.loads(state["es"])
    seeds = random.sample(range(1, 1000), conf["params"]["maps"])
    xs = es.ask()
    texts = [linear.text_from_x(x, space) for x in xs]
    mean_x = es.boundary_handler.repair(np.asarray(es.mean))
    return {"generation": state["generation"], "seeds": seeds, "draws": [[repr(float(v)) for v in x] for x in xs],
            "texts": texts, "text_hashes": [text_hash(t) for t in texts],
            "mean_text": linear.text_from_x(mean_x, space)}


def cmd_draws(a) -> int:
    d = _draws(Path(a.snapshot), a.fork)
    Path(a.out).write_text(json.dumps(d))
    print(f"generation {d['generation']}: {len(d['texts'])} draws, seeds {d['seeds'][:3]}..., mean text "
          f"{len(d['mean_text'])} chars")
    return 0


def cmd_compare(a) -> int:
    x, y = (json.loads(Path(p).read_text()) for p in (a.a, a.b))
    bad = [k for k in ("generation", "seeds", "draws", "texts", "mean_text") if x[k] != y[k]]
    print(f"{'PASS' if not bad else 'FAIL'}: generation {x['generation']}, {len(x['texts'])} draws and texts, seeds "
          f"and mean text {'byte-identical' if not bad else 'differ in ' + ', '.join(bad)}")
    return 1 if bad else 0


def cmd_games(a) -> int:
    from evolved_rules.engine import Engine
    lines = (Path(a.snapshot) / "cache.jsonl").read_text().splitlines()
    rows = [json.loads(l) for l in lines[-a.n:]]
    with Engine(workers=a.workers) as eng:
        res = eng.play([(r["text"], r["seed"]) for r in rows])
    out = []
    for r, g in zip(rows, res):
        same = all(r["result"][k] == g[k] for k in ("trips", "seconds", "commands"))
        out.append({"seed": r["seed"], "trunk": [r["result"][k] for k in ("trips", "seconds", "commands")],
                    "this": [g[k] for k in ("trips", "seconds", "commands")], "identical": same,
                    "rejected": g["rejected_actions"]})
    ok = all(o["identical"] for o in out)
    Path(a.out).write_text(json.dumps({"pass": ok, "games": out}, indent=1))
    print(f"{'PASS' if ok else 'FAIL'}: {sum(o['identical'] for o in out)}/{len(out)} identical on trips/seconds/"
          f"commands; rejected draws {sum(o['rejected'] for o in out)}")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draws")
    d.add_argument("--snapshot", required=True)
    d.add_argument("--fork", action="store_true")
    d.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    g = sub.add_parser("games")
    g.add_argument("--snapshot", required=True)
    g.add_argument("--n", type=int, default=8)
    g.add_argument("--workers", type=int, default=4)
    g.add_argument("--out", required=True)
    a = p.parse_args()
    return {"draws": cmd_draws, "compare": cmd_compare, "games": cmd_games}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
