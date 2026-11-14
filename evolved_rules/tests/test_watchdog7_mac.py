"""macOS watchdog (ops/watchdog7_mac.py): start, alive, done, resume, hold, environment. Uses a throwaway main clone."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="launchd/caffeinate watchdog is the macOS path")

_SPEC = importlib.util.spec_from_file_location(
    "watchdog7_mac", Path(__file__).resolve().parents[1] / "ops" / "watchdog7_mac.py")
wd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(wd)


@pytest.fixture
def main(tmp_path):
    m = tmp_path / "main"
    (m / ".venv" / "bin").mkdir(parents=True)
    (m / ".venv" / "bin" / "python").symlink_to(sys.executable)
    return m


def _wait(cond, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.1)
    return False


def _starts(main: Path) -> list[str]:
    log = wd.ops_dir(main) / "watchdog7.log"
    return [l for l in log.read_text().splitlines() if " start " in l] if log.exists() else []


def _kill(main: Path, name: str) -> None:
    pid = int((wd.ops_dir(main) / f"{name}.pid").read_text())
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def _queue(tmp_path, body: str, name="q") -> dict:
    script = tmp_path / f"{name}.sh"
    script.write_text(body)
    return {"Name": name, "Kind": "queue", "RepoDir": str(tmp_path), "Script": str(script),
            "DoneFile": str(tmp_path / f"{name}.done")}


def _runs(main: Path, entries) -> Path:
    f = wd.ops_dir(main) / "runs7.json"
    f.write_text(json.dumps(entries))
    return f


def test_queue_started_then_done_is_left_alone(main, tmp_path):
    e = _queue(tmp_path, f'touch "{tmp_path}/q.done"\n')
    f = _runs(main, [e])
    wd.one_pass(main, f)
    assert _wait(lambda: Path(e["DoneFile"]).exists())
    assert _wait(lambda: not wd.is_alive(main, e))
    wd.one_pass(main, f)
    assert len(_starts(main)) == 1


def test_alive_job_is_not_started_twice(main, tmp_path):
    e = _queue(tmp_path, "sleep 30\n")
    f = _runs(main, [e])
    try:
        wd.one_pass(main, f)
        assert _wait(lambda: wd.is_alive(main, e))
        wd.one_pass(main, f)
        assert len(_starts(main)) == 1
    finally:
        _kill(main, "q")


def test_job_runs_under_caffeinate_in_its_own_session(main, tmp_path):
    e = _queue(tmp_path, "sleep 30\n")
    try:
        wd.one_pass(main, _runs(main, [e]))
        pid = int((wd.ops_dir(main) / "q.pid").read_text())
        # caffeinate runs the utility under the original pid and forks a helper that asserts on its behalf
        helper = lambda: subprocess.run(["pgrep", "-P", str(pid), "caffeinate"], capture_output=True).returncode == 0
        assert _wait(helper)
        assert e["Script"] in wd._command_of(pid)
        assert os.getsid(pid) == pid != os.getsid(0)
    finally:
        _kill(main, "q")


def _evolve_entry(tmp_path, status=None) -> dict:
    repo = tmp_path / "repo"
    (repo / "fakemod").mkdir(parents=True, exist_ok=True)
    (repo / "fakemod" / "__init__.py").write_text("")
    (repo / "fakemod" / "__main__.py").write_text(
        "import json, os, sys\n"
        "open('argv.txt', 'a').write(json.dumps({'argv': sys.argv[1:], 'hash': os.environ.get('PYTHONHASHSEED'),"
        " 'dll': os.environ.get('EVOLVED_RULES_HOST_DLL'), 'x': os.environ.get('X_EXTRA')}) + '\\n')\n")
    run_dir = repo / "out" / "r1"
    run_dir.mkdir(parents=True, exist_ok=True)
    if status:
        (run_dir / "status.json").write_text(json.dumps({"status": status}))
    return {"Name": "r1", "Module": "fakemod", "RepoDir": str(repo), "Dir": "out/r1",
            "Args": "--run r1 --fresh", "ResumeArgs": "--run r1 --resume", "Env": {"X_EXTRA": "1"}}


def _argv_log(e) -> list[dict]:
    f = Path(e["RepoDir"]) / "argv.txt"
    return [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []


def test_evolve_fresh_then_resume_with_clean_environment(main, tmp_path, monkeypatch):
    monkeypatch.setenv("EVOLVED_RULES_HOST_DLL", "/should/not/leak")
    e = _evolve_entry(tmp_path)
    f = _runs(main, [e])
    wd.one_pass(main, f)
    assert _wait(lambda: len(_argv_log(e)) == 1)
    assert _wait(lambda: not wd.is_alive(main, e))
    (Path(e["RepoDir"]) / e["Dir"] / "checkpoint.pkl").write_bytes(b"x")
    wd.one_pass(main, f)
    assert _wait(lambda: len(_argv_log(e)) == 2)
    first, second = _argv_log(e)
    assert first["argv"] == ["--run", "r1", "--fresh"] and second["argv"] == ["--run", "r1", "--resume"]
    assert first["hash"] == "0" and first["dll"] is None and first["x"] == "1"
    assert "fresh" in _starts(main)[0] and "resume" in _starts(main)[1]


@pytest.mark.parametrize("status", ["budget", "converged", "stopped"])
def test_finished_evolve_run_is_not_restarted(main, tmp_path, status):
    e = _evolve_entry(tmp_path, status=status)
    wd.one_pass(main, _runs(main, [e]))
    assert _starts(main) == [] and _argv_log(e) == []


def test_holds_after_eight_starts_in_two_hours(main, tmp_path):
    e = _queue(tmp_path, "exit 1\n")
    f = _runs(main, [e])
    now = dt.datetime.now()
    for i in range(8):
        wd.say(main, f"start q in x (status None, queue) pid {i}", now - dt.timedelta(minutes=10 * i))
    wd.one_pass(main, f, now)
    log = (wd.ops_dir(main) / "watchdog7.log").read_text()
    assert "hold q" in log and len(_starts(main)) == 8


def test_old_starts_do_not_count_toward_the_hold(main, tmp_path):
    e = _queue(tmp_path, f'touch "{tmp_path}/q.done"\n')
    f = _runs(main, [e])
    now = dt.datetime.now()
    for i in range(8):
        wd.say(main, f"start q in x (status None, queue) pid {i}", now - dt.timedelta(hours=3, minutes=i))
    wd.one_pass(main, f, now)
    assert _wait(lambda: Path(e["DoneFile"]).exists())
    assert "hold q" not in (wd.ops_dir(main) / "watchdog7.log").read_text()


def test_broken_entry_does_not_stop_the_others(main, tmp_path):
    good = _queue(tmp_path, f'touch "{tmp_path}/q.done"\n')
    f = _runs(main, [{"Name": "broken", "Kind": "queue"}, good])
    wd.one_pass(main, f)
    assert _wait(lambda: Path(good["DoneFile"]).exists())
    assert "error broken" in (wd.ops_dir(main) / "watchdog7.log").read_text()


def test_missing_runs_file_is_logged(main):
    wd.one_pass(main, main / "nope.json")
    assert "no runs file" in (wd.ops_dir(main) / "watchdog7.log").read_text()
