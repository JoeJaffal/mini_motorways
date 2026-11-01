"""Batch evaluation engine (Phase 2 Task 4): cache, key separation, dedup, faults, real workers and hosts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import pytest

from evolved_rules import engine as en
from evolved_rules.engine import CODE_VERSION, Engine, EngineError, cache_key, canonical_text
from evolved_rules.gp import HAND_TEXT, SEPARATED_TEXT

OTHER_TEXT = "priority: neg(path_len)\nhold: sub(0.0625, road_stock)\nupgrade: offer_roads"


def _summary(text: str, seed: int, cap_s: float) -> dict:
    """A deterministic fake game summary (shaped like GameResult.summary())."""
    return {"trips": seed % 100 + len(text) % 7, "seconds": cap_s, "commands": 3, "action_counts": {"wait": 3},
            "mean_car_wait": 0.5, "terminated": True, "scenario_seed": seed, "failed_shop": None,
            "tiles_built": 4, "trips_per_tile": 0.25}


@pytest.fixture
def fake(monkeypatch):
    """In-process worker slots (one-thread executors) and a fake game; records every play and every new slot."""
    log = {"plays": [], "workers": 0}
    lock = threading.Lock()

    def make_worker():
        with lock:
            log["workers"] += 1
        return ThreadPoolExecutor(max_workers=1)

    def job(text, seed, cap_s):
        with lock:
            log["plays"].append((text, seed, cap_s))
        return _summary(text, seed, cap_s)

    monkeypatch.setattr(en, "_make_worker", make_worker)
    monkeypatch.setattr(en, "_play_job", job)
    return log


# --- keys and canonical text ---------------------------------------------------------------------------------

def test_canonical_text_ignores_layout_and_rejects_non_individuals():
    messy = "\n  priority:   neg(tiles_needed)  \n\nhold: sub(0.0625,road_stock)\nupgrade: offer_roads\n"
    assert canonical_text(messy) == HAND_TEXT
    for bad in ["", "priority: neg(tiles_needed)", "priority: nope\nhold: 1.0\nupgrade: 1.0", 42]:
        with pytest.raises(ValueError):
            canonical_text(bad)


def test_cache_key_has_version_text_seed_and_cap():
    assert cache_key(HAND_TEXT, 7, 3600) == (CODE_VERSION, HAND_TEXT, 7, 3600.0)
    assert type(cache_key(HAND_TEXT, 7, 3600)[3]) is float


def test_bad_inputs_play_nothing(fake, tmp_path):
    e = Engine(2, 60.0, tmp_path / "c.jsonl")
    for jobs in ([("nonsense", 1)], [(HAND_TEXT, 1), (HAND_TEXT, "2")], [(HAND_TEXT, True)], [(HAND_TEXT, 1.0)]):
        with pytest.raises(ValueError):
            e.play(jobs)
    assert fake["plays"] == [] and not (tmp_path / "c.jsonl").exists()
    for cap in (0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="cap"):
            Engine(1, cap, None)
    with pytest.raises(ValueError, match="timeout"):
        Engine(1, 60.0, None, timeout_s=0)
    assert e.play([]) == []


# --- cache ---------------------------------------------------------------------------------------------------

def test_results_in_job_order_and_a_cache_hit_avoids_replay(fake, tmp_path):
    path = tmp_path / "cache" / "c.jsonl"  # the folder is created on the first write
    e = Engine(3, 60.0, path)
    jobs = [(HAND_TEXT, 5), (OTHER_TEXT, 2), (HAND_TEXT, 9)]
    first = e.play(jobs)
    assert first == [_summary(t, s, 60.0) for t, s in jobs]
    assert e.games_played == 3 and e.cache_hits == 0 and len(fake["plays"]) == 3
    assert e.play(jobs) == first
    assert e.games_played == 3 and e.cache_hits == 3 and len(fake["plays"]) == 3
    # a new engine on the same file (a resumed run) replays nothing
    again = Engine(1, 60.0, path)
    assert again.play(list(reversed(jobs))) == list(reversed(first))
    assert again.games_played == 0 and again.cache_hits == 3 and len(fake["plays"]) == 3
    assert again.cached(HAND_TEXT, 9) == first[2] and again.cached(HAND_TEXT, 10) is None
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [(d["version"], d["text"], d["seed"], d["cap_s"]) for d in lines] == [
        (CODE_VERSION, t, s, 60.0) for t, s in jobs]


def test_results_are_independent_copies(fake):
    e = Engine(1, 60.0, None)
    a, b = e.play([(HAND_TEXT, 1), (HAND_TEXT, 1)])
    a["trips"] = -1
    a["action_counts"]["wait"] = -1
    assert b == _summary(HAND_TEXT, 1, 60.0) and e.play([(HAND_TEXT, 1)])[0] == b


def test_duplicate_jobs_in_one_batch_play_once(fake):
    e = Engine(4, 60.0, None)
    messy = HAND_TEXT.replace("\n", "\n\n  ")  # the same individual written differently
    res = e.play([(HAND_TEXT, 3), (messy, 3), (HAND_TEXT, 4), (HAND_TEXT, 3)])
    assert sorted(fake["plays"]) == [(HAND_TEXT, 3, 60.0), (HAND_TEXT, 4, 60.0)]
    assert res[0] == res[1] == res[3] and res[2]["scenario_seed"] == 4
    assert e.games_played == 2 and e.cache_hits == 0


def test_key_separation_by_cap_and_code_version(fake, tmp_path, monkeypatch):
    path = tmp_path / "c.jsonl"
    Engine(1, 60.0, path).play([(HAND_TEXT, 1)])
    other_cap = Engine(1, 120.0, path)
    assert other_cap.play([(HAND_TEXT, 1)])[0]["seconds"] == 120.0 and other_cap.games_played == 1
    monkeypatch.setattr(en, "CODE_VERSION", "phase2-v-next")
    bumped = Engine(1, 60.0, path)
    assert bumped.cached(HAND_TEXT, 1) is None
    bumped.play([(HAND_TEXT, 1)])
    assert bumped.games_played == 1 and len(fake["plays"]) == 3
    versions = [json.loads(line)["version"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert versions == [CODE_VERSION, CODE_VERSION, "phase2-v-next"]  # append-only: old lines stay
    monkeypatch.setattr(en, "CODE_VERSION", CODE_VERSION)
    back = Engine(1, 60.0, path)
    back.play([(HAND_TEXT, 1)])
    assert back.games_played == 0 and back.cache_hits == 1


def test_a_torn_last_line_is_skipped_and_the_next_line_starts_fresh(fake, tmp_path):
    path = tmp_path / "c.jsonl"
    Engine(1, 60.0, path).play([(HAND_TEXT, 1), (HAND_TEXT, 2)])
    whole = path.read_bytes()
    path.write_bytes(whole[:-25])  # killed in the middle of writing seed 2
    e = Engine(1, 60.0, path)
    assert e.cached(HAND_TEXT, 1) is not None and e.cached(HAND_TEXT, 2) is None
    e.play([(HAND_TEXT, 2), (HAND_TEXT, 3)])
    assert e.games_played == 2
    fresh = Engine(1, 60.0, path)
    assert all(fresh.cached(HAND_TEXT, s) is not None for s in (1, 2, 3))
    assert fresh.play([(HAND_TEXT, s) for s in (1, 2, 3)]) == [_summary(HAND_TEXT, s, 60.0) for s in (1, 2, 3)]


def test_each_finished_game_is_cached_before_a_later_failure(fake, tmp_path, monkeypatch):
    def job(text, seed, cap_s):
        if seed == 2:
            raise RuntimeError("host fault on purpose")
        return _summary(text, seed, cap_s)

    monkeypatch.setattr(en, "_play_job", job)
    path = tmp_path / "c.jsonl"
    with pytest.raises(EngineError, match="failed twice"):
        Engine(1, 60.0, path).play([(HAND_TEXT, 1), (HAND_TEXT, 2), (HAND_TEXT, 3)])
    e = Engine(1, 60.0, path)
    assert e.cached(HAND_TEXT, 1) is not None and e.cached(HAND_TEXT, 2) is None


def test_a_game_finishing_with_the_fatal_failure_is_still_cached(fake, tmp_path, monkeypatch):
    """Seed 2 fails twice; its second attempt and seed 1 finish together, in one done set, and seed 2 (the
    lower task index) is processed first. Seed 1 must still reach the cache before EngineError propagates."""
    together = threading.Barrier(2, timeout=10)
    attempts = []

    def job(text, seed, cap_s):
        attempts.append(seed)
        if seed == 2 and attempts.count(2) == 1:
            raise RuntimeError("first attempt fails at once")
        together.wait()  # seed 1 and the retry of seed 2 finish at the same moment
        if seed == 2:
            raise RuntimeError("second attempt fails")
        return _summary(text, seed, cap_s)

    real_wait = en.wait

    def slow_wait(fs, timeout=None, return_when=en.FIRST_COMPLETED):
        time.sleep(0.3)  # a busy parent: everything finished meanwhile lands in one done set
        return real_wait(fs, timeout=timeout, return_when=return_when)

    monkeypatch.setattr(en, "_play_job", job)
    monkeypatch.setattr(en, "wait", slow_wait)
    path = tmp_path / "c.jsonl"
    e = Engine(2, 60.0, path)
    with pytest.raises(EngineError, match="seed 2 failed twice"):
        e.play([(HAND_TEXT, 2), (HAND_TEXT, 1)])
    assert sorted(attempts) == [1, 2, 2] and e.games_played == 1
    assert e.cached(HAND_TEXT, 1) == _summary(HAND_TEXT, 1, 60.0)
    assert Engine(1, 60.0, path).cached(HAND_TEXT, 1) == _summary(HAND_TEXT, 1, 60.0)  # on disk too


def test_a_game_done_while_a_second_timeout_raises_is_still_cached(fake, tmp_path, monkeypatch):
    """Seed 1 fails at once, then its retry times out (the fatal failure, raised in the deadline loop). Seed 2
    finishes after wait() returned but before that check: it sits in `running`, done, and must be cached
    rather than killed with the others."""
    release, seed2_go, seed2_done = threading.Event(), threading.Event(), threading.Event()
    attempts = []

    def job(text, seed, cap_s):
        attempts.append(seed)
        if seed == 1:
            if attempts.count(1) == 1:
                raise RuntimeError("first attempt fails at once")
            release.wait(30)  # the retry hangs
        else:
            seed2_go.wait(30)
            seed2_done.set()
        return _summary(text, seed, cap_s)

    real_wait = en.wait
    calls = []

    def wait_then_finish_seed2(fs, timeout=None, return_when=en.FIRST_COMPLETED):
        out = real_wait(fs, timeout=timeout, return_when=return_when)
        calls.append(len(out[0]))
        if len(calls) == 2:  # timed out; seed 2 finishes now, unseen by this wait()
            seed2_go.set()
            seed2_done.wait(10)
            time.sleep(0.15)  # seed 1's retry deadline is past too
        return out

    monkeypatch.setattr(en, "_play_job", job)
    monkeypatch.setattr(en, "wait", wait_then_finish_seed2)
    e = Engine(2, 60.0, tmp_path / "c.jsonl", timeout_s=0.3)
    try:
        with pytest.raises(EngineError, match="seed 1 failed twice"):
            e.play([(HAND_TEXT, 1), (HAND_TEXT, 2)])
    finally:
        release.set()
    assert calls == [1, 0] and e.retries == 1
    assert e.cached(HAND_TEXT, 2) == _summary(HAND_TEXT, 2, 60.0) and e.games_played == 1


# --- faults (in-process slots) -------------------------------------------------------------------------------

def test_an_exception_is_retried_once_on_the_same_worker(fake, monkeypatch):
    attempts = []

    def job(text, seed, cap_s):
        attempts.append(seed)
        if seed == 2 and attempts.count(2) == 1:
            raise RuntimeError("first attempt fails")
        return _summary(text, seed, cap_s)

    monkeypatch.setattr(en, "_play_job", job)
    e = Engine(1, 60.0, None)
    assert e.play([(HAND_TEXT, 1), (HAND_TEXT, 2), (HAND_TEXT, 3)])[1] == _summary(HAND_TEXT, 2, 60.0)
    assert attempts == [1, 2, 2, 3]  # the retry goes first
    assert e.retries == 1 and e.games_played == 3 and fake["workers"] == 1  # the worker closed its own host


def test_a_second_failure_raises_with_both_reasons(fake, monkeypatch):
    calls = []

    def job(text, seed, cap_s):
        calls.append(seed)
        raise RuntimeError(f"fault {len(calls)}")

    monkeypatch.setattr(en, "_play_job", job)
    with pytest.raises(EngineError) as err:
        Engine(1, 60.0, None).play([(HAND_TEXT, 8)])
    assert calls == [8, 8]
    msg = str(err.value)
    assert "seed 8" in msg and "fault 1" in msg and "fault 2" in msg and HAND_TEXT in msg


def test_a_timed_out_game_gets_a_new_worker_and_one_retry(fake, monkeypatch):
    release = threading.Event()
    attempts = []

    def job(text, seed, cap_s):
        attempts.append(seed)
        if seed == 2 and attempts.count(2) == 1:
            release.wait(30)  # a slow game; the engine gives up on it after timeout_s
        return _summary(text, seed, cap_s)

    monkeypatch.setattr(en, "_play_job", job)
    e = Engine(1, 60.0, None, timeout_s=0.3)
    t0 = time.monotonic()
    try:
        res = e.play([(HAND_TEXT, s) for s in (1, 2, 3)])
    finally:
        release.set()
    assert time.monotonic() - t0 < 10
    assert res == [_summary(HAND_TEXT, s, 60.0) for s in (1, 2, 3)]
    assert attempts == [1, 2, 2, 3] and e.retries == 1 and e.games_played == 3
    assert fake["workers"] == 2  # the slot's worker was replaced (a replacement is made when next needed)


def test_two_timeouts_raise(fake, monkeypatch):
    release = threading.Event()
    monkeypatch.setattr(en, "_play_job", lambda text, seed, cap_s: release.wait(30))
    e = Engine(1, 60.0, None, timeout_s=0.2)
    try:
        with pytest.raises(EngineError, match="timed out after 0.2 s"):
            e.play([(HAND_TEXT, 1)])
    finally:
        release.set()
    assert fake["workers"] == 2


def test_a_crashed_worker_is_replaced_and_its_game_retried(fake, monkeypatch):
    attempts = []

    def job(text, seed, cap_s):
        attempts.append(seed)
        if attempts.count(seed) == 1 and seed == 1:
            raise BrokenProcessPool("worker died")
        return _summary(text, seed, cap_s)

    monkeypatch.setattr(en, "_play_job", job)
    e = Engine(1, 60.0, None)
    assert e.play([(HAND_TEXT, 1), (HAND_TEXT, 2)]) == [_summary(HAND_TEXT, s, 60.0) for s in (1, 2)]
    assert attempts == [1, 1, 2] and fake["workers"] == 2 and e.retries == 1


def test_an_interrupt_kills_the_running_workers(fake, monkeypatch):
    killed = []
    monkeypatch.setattr(en, "_kill_worker", lambda ex: (killed.append(ex), ex.shutdown(wait=False)))
    release = threading.Event()

    def job(text, seed, cap_s):
        if seed == 1:
            raise KeyboardInterrupt  # stands in for Ctrl+C reaching the parent while games run
        release.wait(30)
        return _summary(text, seed, cap_s)

    monkeypatch.setattr(en, "_play_job", job)
    e = Engine(3, 60.0, None)
    try:
        with pytest.raises(KeyboardInterrupt):
            e.play([(HAND_TEXT, 1), (HAND_TEXT, 2), (HAND_TEXT, 3)])
    finally:
        release.set()
    assert len(killed) == 2  # the two games still running
    assert e.games_played == 0


# --- real worker processes (spawned; the jobs below are pickled by reference) -----------------------------------

def _marker(name: str) -> Path:
    return Path(os.environ["ENGINE_TEST_DIR"]) / name


def _crash_first_attempt(text, seed, cap_s):
    m = _marker(f"crash-{seed}")
    if not m.exists():
        m.write_text(str(os.getpid()))
        os._exit(3)  # the worker process dies mid-game
    return {"seed": seed, "pid": os.getpid()}


def _hang_first_attempt(text, seed, cap_s):
    m = _marker(f"hang-{seed}")
    if not m.exists():
        m.write_text(str(os.getpid()))
        time.sleep(600)
    return {"seed": seed, "pid": os.getpid()}


def _hang_with_a_busy_child(text, seed, cap_s):
    """First attempt: start a child that never reads stdin (a host stuck mid-step), write its pid, hang."""
    m = _marker(f"child-{seed}")
    if not m.exists():
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"],
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        m.write_text(str(child.pid))
        time.sleep(600)
    return {"seed": seed}


def _hang_with_a_host(text, seed, cap_s):
    """First attempt: start this worker's real host, write its pid, then hang (the host is left idle)."""
    from evolved_rules import evaluate as ev
    m = _marker(f"host-{seed}")
    if not m.exists():
        host = ev._worker_host()
        m.write_text(str(host._proc.pid))
        time.sleep(600)
    return {"seed": seed}


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def test_real_worker_crash_is_replaced(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGINE_TEST_DIR", str(tmp_path))
    monkeypatch.setattr(en, "_play_job", _crash_first_attempt)
    with Engine(1, 60.0, None, timeout_s=120) as e:
        res = e.play([(HAND_TEXT, 1), (HAND_TEXT, 2)])
    first_pid = int((tmp_path / "crash-1").read_text())
    assert [r["seed"] for r in res] == [1, 2] and res[0]["pid"] != first_pid
    assert e.retries == 2  # each seed crashed its worker once


def test_real_worker_timeout_kills_the_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGINE_TEST_DIR", str(tmp_path))
    monkeypatch.setattr(en, "_play_job", _hang_first_attempt)
    t0 = time.monotonic()
    with Engine(1, 60.0, None, timeout_s=5) as e:
        res = e.play([(HAND_TEXT, 5)])
    hung_pid = int((tmp_path / "hang-5").read_text())
    assert res == [{"seed": 5, "pid": res[0]["pid"]}] and res[0]["pid"] != hung_pid
    assert e.retries == 1 and time.monotonic() - t0 < 90
    assert not _pid_alive(hung_pid)


@pytest.mark.skipif(sys.platform != "win32", reason="the tree kill (taskkill /T) is the Windows path")
@pytest.mark.parametrize("tree_kill", [True, False], ids=["taskkill", "taskkill-stubbed"])
def test_a_timed_out_worker_takes_a_busy_child_with_it(tmp_path, monkeypatch, tree_kill):
    """The case taskkill /T exists for: a child of the worker (standing in for a host stuck mid-step) that
    does not read stdin, so it would never see the worker's death. With taskkill stubbed out the child
    survives, which shows this test fails without the tree kill."""
    monkeypatch.setenv("ENGINE_TEST_DIR", str(tmp_path))
    monkeypatch.setattr(en, "_play_job", _hang_with_a_busy_child)
    if not tree_kill:
        no_taskkill = types.SimpleNamespace(run=lambda *a, **k: None, SubprocessError=subprocess.SubprocessError)
        monkeypatch.setattr(en, "subprocess", no_taskkill)  # the engine's taskkill only, not the tests' tasklist
    with Engine(1, 60.0, None, timeout_s=5) as e:
        assert e.play([(HAND_TEXT, 7)]) == [{"seed": 7}]
    child_pid = int((tmp_path / "child-7").read_text())
    try:
        deadline = time.monotonic() + (10 if tree_kill else 3)
        while _pid_alive(child_pid) and time.monotonic() < deadline:
            time.sleep(0.25)
        assert _pid_alive(child_pid) is (not tree_kill)
    finally:
        subprocess.run(["taskkill", "/F", "/PID", str(child_pid)], capture_output=True)


@pytest.mark.host
def test_a_timed_out_worker_takes_its_host_with_it(host_dll, tmp_path, monkeypatch):
    """A real host left idle: it reads stdin, so this covers the EOF path (it would exit with the worker
    even without taskkill /T; the busy-child test above covers the tree kill)."""
    monkeypatch.setenv("ENGINE_TEST_DIR", str(tmp_path))
    monkeypatch.setattr(en, "_play_job", _hang_with_a_host)
    with Engine(1, 60.0, None, timeout_s=8) as e:
        assert e.play([(HAND_TEXT, 6)]) == [{"seed": 6}]
    host_pid = int((tmp_path / "host-6").read_text())
    deadline = time.monotonic() + 20
    while _pid_alive(host_pid) and time.monotonic() < deadline:
        time.sleep(0.5)
    assert not _pid_alive(host_pid)


# --- real games ----------------------------------------------------------------------------------------------

@pytest.mark.host
def test_identical_results_across_engines_and_from_the_cache(host_dll, tmp_path):
    jobs = [(HAND_TEXT, 2000), (SEPARATED_TEXT, 2000), (HAND_TEXT, 2001), (HAND_TEXT, 2000)]
    with Engine(2, 120.0, tmp_path / "a.jsonl") as a:
        ra = a.play(jobs)
    with Engine(1, 120.0, tmp_path / "b.jsonl") as b:
        rb = b.play(jobs)
    assert ra == rb and a.games_played == b.games_played == 3
    assert ra[0] == ra[3] and ra[0]["trips"] > 0 and ra[0]["scenario_seed"] == 2000
    assert ra[0]["truncated"] and ra[0]["seconds"] >= 120.0
    with Engine(2, 120.0, tmp_path / "a.jsonl") as c:
        assert c.play(jobs) == ra and c.games_played == 0 and c.cache_hits == 3


@pytest.mark.host
def test_record_saves_verifies_and_matches_the_cache(host_dll, verifier, tmp_path):
    with Engine(1, 60.0, tmp_path / "c.jsonl") as e:
        played = e.play([(OTHER_TEXT, 2000)])[0]
        summary = e.record(OTHER_TEXT, 2000, tmp_path / "replays" / "2000.json", verify=True)
        assert e.games_played == 2  # the recorded game is counted (it was played) though it matched the cache
        assert len(Path(tmp_path / "c.jsonl").read_text(encoding="utf-8").splitlines()) == 1  # nothing new cached
    assert summary["verified"] is True
    assert {k: v for k, v in summary.items() if k != "verified"} == played
    rec = json.loads((tmp_path / "replays" / "2000.json").read_text(encoding="utf-8"))
    assert rec["actions"] and not (tmp_path / "replays" / "2000.verify.txt").exists()


def test_record_detects_a_cached_result_that_disagrees(fake, tmp_path, monkeypatch):
    path = tmp_path / "c.jsonl"
    e = Engine(1, 60.0, path)
    e.play([(HAND_TEXT, 1)])

    def record_job(text, seed, cap_s, out, verify):
        Path(out).write_text("{}", encoding="utf-8")
        return {**_summary(text, seed, cap_s), "trips": 999, "verified": None}

    monkeypatch.setattr(en, "_record_job", record_job)
    with pytest.raises(EngineError, match="not deterministic"):
        e.record(HAND_TEXT, 1, tmp_path / "r" / "1.json", verify=False)
    # an uncached game is recorded and then cached
    s = e.record(HAND_TEXT, 2, tmp_path / "r" / "2.json", verify=False)
    assert s["verified"] is None and e.cached(HAND_TEXT, 2)["trips"] == 999
