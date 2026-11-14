"""Restartable, chunked evaluate battery for gp-7 / cma-7 (operative plan section 8.2; HANDOFF.md section 4).

Plays one policy on an inclusive seed range in chunks of --chunk seeds. Each chunk is an ordinary
`python -m evolved_rules.evaluate` run named <prefix>-<first seed of the chunk>, run with the CURRENT WORKING
FOLDER as the code root. So run this script from the worktree whose code must play (e.g. ..\\mm-gp6-final for L).

Idempotent: a chunk whose run folder holds summary.json is skipped; a chunk folder without summary.json
(a crash, a reboot) is renamed to <name>.failed-<n> and the chunk is replayed. Before each chunk the script
checks two things in <main clone>/output/evolved_rules/ops/:
  - queue.pause    : while it exists, wait (poll every 60 s) - used to give the screen all workers;
  - --not-after    : an ISO timestamp; a chunk is not started if now + 1.2 x the last chunk's wall time is later.
It never prints scores (results must stay unlooked-at until used); it logs chunk start/end and wall time to
<main clone>/output/evolved_rules/ops/runs.log.

Example (PowerShell, from ..\\mm-gp6-final):
  $env:PYTHONHASHSEED='0'
  & <main>\\.venv\\Scripts\\python.exe <main>\\evolved_rules\\ops\\battery7.py --policy tree:<main>\\evolved_rules\\seeds\\gp7\\cma1_3tree.txt `
      --seeds 6100-6999 --chunk 100 --prefix pre-L-test --workers 12 --main <main>
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import time
from pathlib import Path


def _log(main: Path, msg: str) -> None:
    ops = main / "output" / "evolved_rules" / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with open(ops / "runs.log", "a", encoding="utf-8") as f:
        f.write(f"{stamp} {msg}\n")
    print(f"{stamp} {msg}", flush=True)


def _pid_alive(pid: int) -> bool:
    """True if a process with this pid exists (Windows: tasklist; never os.kill, which terminates there)."""
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _take_lock(main: Path, prefix: str) -> Path | None:
    """One live instance per prefix: a scheduled re-launch while a battery is running exits at once."""
    lock = main / "output" / "evolved_rules" / "ops" / f"battery7-{prefix}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            pid = int(lock.read_text().strip())
        except ValueError:
            pid = -1
        if pid > 0 and pid != os.getpid() and _pid_alive(pid):
            return None
    lock.write_text(str(os.getpid()))
    return lock


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--policy", required=True)
    p.add_argument("--seeds", required=True, help="inclusive range A-B")
    p.add_argument("--chunk", type=int, default=100)
    p.add_argument("--prefix", required=True)
    p.add_argument("--workers", type=int, required=True)
    p.add_argument("--main", required=True, help="the main clone (for the ops folder: pause flag and runs.log)")
    p.add_argument("--not-after", default="", help="ISO timestamp with UTC offset (T_freeze); optional")
    a = p.parse_args()

    lo, hi = (int(x) for x in a.seeds.split("-"))
    main_dir = Path(a.main)
    lock = _take_lock(main_dir, a.prefix)
    if lock is None:
        print(f"{a.prefix}: another instance is running; exiting", flush=True)
        return 0
    runs_dir = Path.cwd() / "output" / "evolved_rules" / "runs"
    pause = main_dir / "output" / "evolved_rules" / "ops" / "queue.pause"
    not_after = dt.datetime.fromisoformat(a.not_after) if a.not_after else None
    last_wall = 0.0
    env = dict(os.environ, PYTHONHASHSEED="0")

    for start in range(lo, hi + 1, a.chunk):
        end = min(start + a.chunk - 1, hi)
        name = f"{a.prefix}-{start}"
        run = runs_dir / name
        if (run / "summary.json").exists():
            continue
        if run.exists():
            n = 1
            while (runs_dir / f"{name}.failed-{n}").exists():
                n += 1
            run.rename(runs_dir / f"{name}.failed-{n}")
            _log(main_dir, f"{name}: incomplete folder renamed to {name}.failed-{n}; replaying")
        while pause.exists():
            time.sleep(60)
        if not_after is not None:
            now = dt.datetime.now().astimezone()
            if now + dt.timedelta(seconds=1.2 * last_wall) > not_after:
                _log(main_dir, f"{name}: not started (would cross --not-after {a.not_after})")
                return 2
        t = time.time()
        _log(main_dir, f"{name}: start seeds {start}-{end} policy {a.policy} cwd {Path.cwd()}")
        rc = subprocess.run([sys.executable, "-m", "evolved_rules.evaluate", "--policy", a.policy,
                             "--seeds", f"{start}-{end}", "--workers", str(a.workers), "--run", name],
                            env=env, cwd=Path.cwd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        last_wall = time.time() - t
        ok = (run / "summary.json").exists()
        _log(main_dir, f"{name}: {'done' if ok else 'FAILED'} rc {rc} wall {last_wall:.0f} s")
        if not ok:
            return 1  # rerun the script: it replays this chunk
    _log(main_dir, f"{a.prefix}: all chunks complete ({lo}-{hi})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
