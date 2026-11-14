"""gp-7 / cma-7 watchdog for macOS: the port of watchdog7.ps1 (HANDOFF.md section 5) to launchd.

Keeps long jobs alive independently of any agent session. launchd runs this script every 10 minutes and at
login (`--install` writes and loads the LaunchAgent; `--uninstall` removes it; `--status` prints its state).
Each pass is idempotent. For every entry of the run list:
  - a job whose process is alive is left alone;
  - a job that is done is left alone (evolve7: status.json says converged/budget/stopped; queue: DoneFile exists);
  - otherwise it is (re)started detached from its RepoDir, in a new session, under `caffeinate -ims`
    (evolved_rules/power.py keeps the machine awake on Windows only);
  - at most 8 starts per job in any 2 hours, then it holds and logs "needs a look".

Run list: JSON, default <main clone>/output/evolved_rules/ops/runs7.json (gitignored). Two kinds of entry:
  evolve7 (the default; same fields as watchdog7.ps1):
    {"Name": "cma-7", "Module": "evolved_rules.evolve7", "RepoDir": "/abs/mm-cma7",
     "Dir": "output/evolved_rules/evolve7/cma-7",              <- run folder, relative to RepoDir
     "Args": "--run cma-7 --workers 10 ...", "ResumeArgs": "--run cma-7 --resume"}
    ResumeArgs is used once <Dir>/checkpoint.pkl exists.
  queue (a restartable shell script, e.g. the L pre-play battery queue):
    {"Name": "pre-queue", "Kind": "queue", "RepoDir": "/abs/mm-gp6-final",
     "Script": "/abs/main/output/evolved_rules/ops/prequeue.sh", "DoneFile": "/abs/.../prequeue.done"}
Optional on both: "Env": {"NAME": "value"} added to the job's environment.

Every job gets PYTHONHASHSEED=0, DOTNET_ROOT=~/.dotnet with ~/.dotnet first on PATH, and no
EVOLVED_RULES_HOST_DLL unless its Env sets one. Python is always the main clone's .venv. A job's stdout and
stderr are appended to <ops>/<Name>.log and <ops>/<Name>.err; this script logs to <ops>/watchdog7.log.
Edit the JSON, not this script.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

LABEL = "com.minimotorways.gp7-watchdog"
INTERVAL_S = 600
MAX_STARTS = 8
WINDOW = dt.timedelta(hours=2)
DONE_STATUSES = ("converged", "budget", "stopped")
STAMP = "%Y-%m-%d %H:%M:%S"

MAIN = Path(__file__).resolve().parents[2]


def ops_dir(main: Path) -> Path:
    d = main / "output" / "evolved_rules" / "ops"
    d.mkdir(parents=True, exist_ok=True)
    return d


def say(main: Path, msg: str, now: dt.datetime | None = None) -> None:
    now = now or dt.datetime.now()
    with open(ops_dir(main) / "watchdog7.log", "a", encoding="utf-8") as f:
        f.write(f"{now.strftime(STAMP)} {msg}\n")


def recent_starts(main: Path, name: str, now: dt.datetime) -> int:
    log = ops_dir(main) / "watchdog7.log"
    if not log.exists():
        return 0
    n = 0
    for line in log.read_text(encoding="utf-8").splitlines():
        if f" start {name} " not in line:
            continue
        try:
            t = dt.datetime.strptime(line[:19], STAMP)
        except ValueError:
            continue
        if t > now - WINDOW:
            n += 1
    return n


def _command_of(pid: int) -> str:
    done = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def is_alive(main: Path, entry: dict) -> bool:
    """Alive if the pid the watchdog recorded still runs this job, or (evolve7) any process runs it."""
    name = entry["Name"]
    pidfile = ops_dir(main) / f"{name}.pid"
    if pidfile.exists():
        try:
            pid = int(pidfile.read_text().strip())
        except ValueError:
            pid = -1
        if pid > 0 and _marker(entry) in _command_of(pid):
            return True
    if entry.get("Kind", "evolve7") == "evolve7":  # a run started by hand counts too
        out = subprocess.run(["ps", "-Ao", "command="], capture_output=True, text=True).stdout
        for cmd in out.splitlines():
            toks = cmd.split()
            if entry["Module"] in toks and _has_run_name(toks, name):
                return True
    return False


def _has_run_name(toks: list[str], name: str) -> bool:
    return any(t == "--run" and i + 1 < len(toks) and toks[i + 1] == name for i, t in enumerate(toks))


def _marker(entry: dict) -> str:
    return entry["Script"] if entry.get("Kind") == "queue" else entry["Module"]


def is_done(entry: dict) -> tuple[bool, str | None]:
    if entry.get("Kind") == "queue":
        return Path(entry["DoneFile"]).exists(), None
    status_file = Path(entry["RepoDir"]) / entry["Dir"] / "status.json"
    status = None
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text(encoding="utf-8")).get("status")
        except (ValueError, OSError):
            status = None
    return status in DONE_STATUSES, status


def job_env(entry: dict) -> dict:
    home = Path.home()
    env = dict(os.environ)
    env.pop("EVOLVED_RULES_HOST_DLL", None)
    env.update(PYTHONHASHSEED="0", DOTNET_ROOT=str(home / ".dotnet"), DOTNET_CLI_TELEMETRY_OPTOUT="1",
               PATH=f"{home / '.dotnet'}:{env.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')}")
    env.update({k: str(v) for k, v in (entry.get("Env") or {}).items()})
    return env


def job_argv(main: Path, entry: dict) -> tuple[list[str], str]:
    if entry.get("Kind") == "queue":
        return ["/bin/bash", entry["Script"]], "queue"
    resume = (Path(entry["RepoDir"]) / entry["Dir"] / "checkpoint.pkl").exists()
    args = entry["ResumeArgs"] if resume else entry["Args"]
    py = main / ".venv" / "bin" / "python"
    return [str(py), "-m", entry["Module"], *shlex.split(args)], ("resume" if resume else "fresh")


def start(main: Path, entry: dict) -> int:
    argv, mode = job_argv(main, entry)
    ops = ops_dir(main)
    with open(ops / f"{entry['Name']}.log", "ab") as out, open(ops / f"{entry['Name']}.err", "ab") as err:
        p = subprocess.Popen(["/usr/bin/caffeinate", "-ims", *argv], cwd=entry["RepoDir"], env=job_env(entry),
                             stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
    (ops / f"{entry['Name']}.pid").write_text(str(p.pid))
    return p.pid


def one_pass(main: Path, runs_file: Path, now: dt.datetime | None = None) -> None:
    now = now or dt.datetime.now()
    if not runs_file.exists():
        say(main, f"no runs file {runs_file}", now)
        return
    try:
        runs = json.loads(runs_file.read_text(encoding="utf-8"))
    except ValueError as e:
        say(main, f"runs file unreadable: {e}", now)
        return
    for entry in runs if isinstance(runs, list) else [runs]:
        name = entry.get("Name", "?")
        try:
            if is_alive(main, entry):
                continue
            done, status = is_done(entry)
            if done:
                continue
            if recent_starts(main, name, now) >= MAX_STARTS:
                say(main, f"hold {name}: {MAX_STARTS} starts in 2 h, status {status}; needs a look", now)
                continue
            mode = job_argv(main, entry)[1]
            pid = start(main, entry)
            say(main, f"start {name} in {entry['RepoDir']} (status {status}, {mode}) pid {pid}", now)
        except Exception as e:  # one broken entry must not stop the others
            say(main, f"error {name}: {type(e).__name__}: {e}", now)


def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def install(main: Path, runs_file: Path) -> int:
    ops = ops_dir(main)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [str(main / ".venv" / "bin" / "python"), str(Path(__file__).resolve()),
                             "--runs-file", str(runs_file)],
        "StartInterval": INTERVAL_S,
        "RunAtLoad": True,
        "AbandonProcessGroup": True,  # never kill the jobs when a pass exits (they also run in their own session)
        "ProcessType": "Background",
        "StandardOutPath": str(ops / "watchdog7.launchd.log"),
        "StandardErrorPath": str(ops / "watchdog7.launchd.log"),
        "WorkingDirectory": str(main),
    }
    path = plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True)
    with open(path, "wb") as f:
        plistlib.dump(plist, f)
    done = subprocess.run(["launchctl", "bootstrap", domain, str(path)], capture_output=True, text=True)
    print(f"wrote {path}; launchctl bootstrap rc {done.returncode} {done.stderr.strip()}")
    return done.returncode


def uninstall() -> int:
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    plist_path().unlink(missing_ok=True)
    print(f"removed {LABEL}")
    return 0


def status() -> int:
    done = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"], capture_output=True, text=True)
    if done.returncode != 0:
        print(f"{LABEL}: not loaded")
        return 1
    keep = ("state =", "runs =", "last exit code", "run interval")
    print("\n".join(l.strip() for l in done.stdout.splitlines() if any(k in l for k in keep)))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs-file", default="")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--install", action="store_true")
    g.add_argument("--uninstall", action="store_true")
    g.add_argument("--status", action="store_true")
    a = p.parse_args()
    runs_file = Path(a.runs_file) if a.runs_file else ops_dir(MAIN) / "runs7.json"
    if a.install:
        return install(MAIN, runs_file)
    if a.uninstall:
        return uninstall()
    if a.status:
        return status()
    one_pass(MAIN, runs_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
