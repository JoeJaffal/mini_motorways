import json, pytest
from evolved_rules.evaluate import parse_seeds, evaluate

def test_parse_seeds():
    assert parse_seeds(["1000", "2000-2002", "1000"]) == [1000, 2000, 2001, 2002]

@pytest.mark.host
def test_evaluate_writes_summary(host_dll, verifier, tmp_path, monkeypatch):
    monkeypatch.setattr("evolved_rules.evaluate.RUNS_DIR", tmp_path)
    s = evaluate("hand", [2000, 2001], workers=2, run="t", verify=True)
    assert [g["scenario_seed"] for g in s["games"]] == [2000, 2001]
    assert s["aggregate"]["verified_pass"] == 2
    for k in ["trips", "seconds", "rejected_actions", "commands", "action_counts", "mean_car_wait",
              "max_car_wait", "terminated", "truncated", "scenario_seed", "city", "deterministic",
              "failed_shop", "road_tiles_at_failure"]:
        assert k in s["games"][0]
    assert (tmp_path / "t" / "replays" / "2000.json").exists()


# ---------------------------------------------------------------------------------------------------------
# Focused tests. Non-host ones replace the per-seed job and run it on an in-process thread pool.
# ---------------------------------------------------------------------------------------------------------
import ctypes, importlib.metadata, os, statistics, subprocess, sys, textwrap, threading, time, types
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from evolved_rules import evaluate as ev
from evolved_rules.agent import GameResult
from evolved_rules.evaluate import main, run_reference
from evolved_rules.host import default_host_dll
from evolved_rules.rules import DoNothing, HandRule
from evolved_rules.tests.helpers import make_obs, shop

SUMMARY_KEYS = list(GameResult(*([None] * 15)).summary())


def _fake_game(seed, trips, seconds=100.0):
    return {"trips": trips, "seconds": seconds, "rejected_actions": 0, "commands": 5,
            "action_counts": {"wait": 5}, "mean_car_wait": 0.0, "max_car_wait": 0.0, "terminated": True,
            "truncated": False, "scenario_seed": seed, "city": "LosAngeles", "deterministic": True,
            "failed_shop": 1, "road_tiles_at_failure": 3, "privileged": False}


def _thread_pool(workers, abort):
    """In-process stand-in for the process pool, with the real initializer (the real _run_seed then runs)."""
    return ThreadPoolExecutor(max_workers=workers, initializer=ev._init_worker, initargs=(abort,))


@pytest.fixture
def fake_runs(tmp_path, monkeypatch):
    """RUNS_DIR in tmp_path, an in-process pool, a fake game (trips = seed % 100) and a fake verifier build."""
    calls = []

    def job(policy_name, seed, cap_s, run_dir, verify):
        calls.append((policy_name, seed, cap_s, verify))
        g = _fake_game(seed, seed % 100)
        g["verified"] = True if verify else None
        return g

    monkeypatch.setattr(ev, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(ev, "_make_pool", _thread_pool)
    monkeypatch.setattr(ev, "_ABORT", None)  # set by _init_worker; restored afterwards
    monkeypatch.setattr(ev, "_HOST", None)
    monkeypatch.setattr(ev, "_play_seed", job)
    monkeypatch.setattr(ev, "build_verifier", lambda: calls.append("build"))
    return tmp_path, calls


@pytest.mark.parametrize("spec", [["2003-2001"], ["abc"], ["20-x"], ["1.5"], ["-"], [""], ["1-2-3"]])
def test_parse_seeds_errors(spec):
    with pytest.raises(ValueError):
        parse_seeds(spec)


def test_parse_seeds_single_range_and_order():
    assert parse_seeds(["5-5"]) == [5]
    assert parse_seeds(["7", "3-5", "4"]) == [7, 3, 4, 5]


def test_existing_run_folder_is_refused_before_any_game(fake_runs):
    tmp_path, calls = fake_runs
    (tmp_path / "taken").mkdir()
    with pytest.raises(ev.RunExistsError):
        evaluate("hand", [2000], workers=1, run="taken", verify=True)
    assert issubclass(ev.RunExistsError, FileExistsError)
    assert calls == []
    assert list((tmp_path / "taken").iterdir()) == []


def test_summary_files_and_aggregate_maths(fake_runs):
    tmp_path, calls = fake_runs
    seeds = [2010, 2003, 2007, 2001]
    s = evaluate("hand", seeds, workers=3, run="a", verify=False, cap_s=300.0)
    trips = [10, 3, 7, 1]
    assert [g["scenario_seed"] for g in s["games"]] == seeds  # input order, not completion order
    agg = s["aggregate"]
    assert agg["n"] == 4
    assert agg["trips"] == {"mean": 5.25, "median": 5.0, "min": 1, "max": 10, "sd": statistics.stdev(trips)}
    assert agg["seconds"]["sd"] == 0.0 and agg["seconds"]["mean"] == 100.0
    assert all(type(v) is float for k in ("trips", "seconds") for v in agg[k].values())
    # verify=False: nothing verified, the verifier is never built
    assert agg["verified_total"] == 0 and agg["verified_pass"] == 0
    assert all(g["verified"] is None for g in s["games"]) and "build" not in calls
    cfg = s["config"]
    assert cfg["policy"] == "hand" and cfg["seeds"] == seeds and cfg["cap_s"] == 300.0
    assert cfg["PYTHONHASHSEED"] == "0"
    for k in ["commit", "dirty", "packages", "python", "host_dll"]:
        assert k in cfg
    assert set(cfg["packages"]) == {"numpy", "scipy", "deap", "cma"}
    run = tmp_path / "a"
    assert json.loads((run / "summary.json").read_text()) == s
    lines = (run / "games.jsonl").read_text().splitlines()
    assert [json.loads(l) for l in lines] == s["games"]
    assert not (run / "error.txt").exists()


def test_one_game_has_sd_zero_and_verify_counts(fake_runs):
    tmp_path, calls = fake_runs
    s = evaluate("nothing", [2042], workers=8, run="one", verify=True)
    assert s["aggregate"]["trips"] == {"mean": 42, "median": 42, "min": 42, "max": 42, "sd": 0.0}
    assert all(type(v) is float for v in s["aggregate"]["trips"].values())  # never int, even when exact
    assert s["aggregate"]["verified_pass"] == 1 and s["aggregate"]["verified_total"] == 1
    assert calls[0] == "build"  # built once, before any job
    assert [c for c in calls if c != "build"] == [("nothing", 2042, 3600.0, True)]


def test_failed_verification_counts_in_total_not_pass(fake_runs, monkeypatch):
    tmp_path, _ = fake_runs

    def job(policy_name, seed, cap_s, run_dir, verify):
        g = _fake_game(seed, 1)
        g["verified"] = seed != 2001
        return g

    monkeypatch.setattr(ev, "_play_seed", job)
    s = evaluate("hand", [2000, 2001, 2002], workers=2, run="v", verify=True)
    assert s["aggregate"]["verified_pass"] == 2 and s["aggregate"]["verified_total"] == 3


def test_failing_job_writes_error_and_no_summary(fake_runs, monkeypatch):
    tmp_path, _ = fake_runs

    def job(policy_name, seed, cap_s, run_dir, verify):
        if seed == 2001:
            raise RuntimeError("verifier fault on purpose")
        return {**_fake_game(seed, 1), "verified": None}

    monkeypatch.setattr(ev, "_play_seed", job)
    with pytest.raises(RuntimeError, match="on purpose"):
        evaluate("hand", [2000, 2001, 2002], workers=2, run="bad", verify=False)
    run = tmp_path / "bad"
    assert "verifier fault on purpose" in (run / "error.txt").read_text()
    assert not (run / "summary.json").exists() and not (run / "games.jsonl").exists()


def test_bad_inputs_are_refused_before_the_folder_is_claimed(fake_runs):
    tmp_path, calls = fake_runs
    for kwargs in [dict(policy_name="greedy", seeds=[1]), dict(policy_name="hand", seeds=[]),
                   dict(policy_name="hand", seeds=[1, 1]), dict(policy_name="hand", seeds=[1], run="a/b"),
                   dict(policy_name="hand", seeds=[1], run="..")] + [
                   dict(policy_name="hand", seeds=[1], run=name) for name in BAD_RUN_NAMES]:
        kwargs = {"workers": 1, "run": "x", "verify": False, **kwargs}
        with pytest.raises(ValueError):
            evaluate(**kwargs)
    assert calls == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("cap", [0, 0.0, -1.0, -3600, float("nan"), float("inf"), float("-inf"), None, "60"])
def test_bad_caps_are_value_errors_before_the_folder_is_claimed(fake_runs, cap):
    tmp_path, calls = fake_runs
    with pytest.raises(ValueError, match="cap"):
        evaluate("hand", [1], workers=1, run="x", verify=False, cap_s=cap)
    assert calls == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("cap", ["0", "-1", "-0.5", "nan", "NaN", "inf", "-inf"])
def test_cli_bad_cap_is_a_usage_error(fake_runs, capsys, cap):
    tmp_path, calls = fake_runs
    with pytest.raises(SystemExit) as e:
        main(["--policy", "hand", "--seeds", "1", "--run", "x", f"--cap={cap}"])
    assert e.value.code == 2 and "cap" in capsys.readouterr().err
    assert calls == [] and list(tmp_path.iterdir()) == []


def test_small_positive_caps_are_accepted(fake_runs):
    tmp_path, calls = fake_runs
    assert evaluate("hand", [1], workers=1, run="tiny", verify=False, cap_s=0.5)["config"]["cap_s"] == 0.5
    assert main(["--policy", "hand", "--seeds", "2", "--run", "one", "--cap", "1"]) == 0
    assert sorted(c[2] for c in calls if c != "build") == [0.5, 1.0]


def test_cli_accepts_the_separated_policy(fake_runs):
    tmp_path, calls = fake_runs
    assert main(["--policy", "separated", "--seeds", "2000", "--run", "sep"]) == 0
    assert [c for c in calls if c != "build"] == [("separated", 2000, 3600.0, False)]
    assert json.loads((tmp_path / "sep" / "summary.json").read_text())["config"]["policy"] == "separated"


def test_reference_runs_unrecorded_and_never_verified(fake_runs, monkeypatch):
    tmp_path, calls = fake_runs
    s = evaluate("reference", [2000], workers=1, run="ref", verify=True)
    assert "build" not in calls  # nothing to verify
    assert [c for c in calls if c != "build"] == [("reference", 2000, 3600.0, False)]
    assert not (tmp_path / "ref" / "replays").exists()


def test_cli_parses_and_refuses_existing_run(fake_runs, capsys):
    tmp_path, calls = fake_runs
    assert main(["--policy", "hand", "--seeds", "2000-2001", "7", "--run", "c", "--workers", "4",
                 "--cap", "120"]) == 0
    assert sorted(c[1] for c in calls) == [7, 2000, 2001] and {c[2] for c in calls} == {120.0}
    s = json.loads((tmp_path / "c" / "summary.json").read_text())
    assert s["config"]["seeds"] == [2000, 2001, 7] and s["config"]["cap_s"] == 120.0
    assert s["config"]["workers"] == 3  # clamped to the number of seeds
    n = len(calls)
    assert main(["--policy", "hand", "--seeds", "2000", "--run", "c"]) == 2
    assert len(calls) == n and "already exists" in capsys.readouterr().err
    for bad in [["--seeds", "9-1", "--run", "d"]] + [["--seeds", "1", "--run", name] for name in BAD_RUN_NAMES]:
        with pytest.raises(SystemExit) as e:
            main(["--policy", "hand", *bad])
        assert e.value.code == 2
    assert len(calls) == n and sorted(p.name for p in tmp_path.iterdir()) == ["c"]


BAD_RUN_NAMES = ["", " ", "a/b", "a\b", ".", "..", ".hidden", "-x", "C:x", "D:", "a*b", "a?b", 'a"b', "a<b", "a|b",
                 "ab:c", "trail.", "trail ", "nul", "NUL", "Con", "aux.txt", "com1", "LPT9.log", "a	b", "ré"]


@pytest.mark.parametrize("name", ["run1", "hand_2000-2019", "a.b", "R", "9", "con1", "nul_", "comx", "x.nul"])
def test_good_run_names(name):
    ev._check_run_name(name)


@pytest.mark.parametrize("name", BAD_RUN_NAMES)
def test_bad_run_names_are_value_errors(name):
    with pytest.raises(ValueError):
        ev._check_run_name(name)


@pytest.mark.parametrize("name", ["", "C:x", "D:", "a*b", "nul", "trail.", " "])
def test_run_names_windows_cannot_create_are_refused_before_the_claim(fake_runs, monkeypatch, name):
    tmp_path, calls = fake_runs
    monkeypatch.chdir(tmp_path)  # "C:x" would otherwise land in the cwd
    with pytest.raises(ValueError):
        evaluate("hand", [1], workers=1, run=name, verify=False)
    with pytest.raises(SystemExit) as e:
        main(["--policy", "hand", "--seeds", "1", "--run", name])
    assert e.value.code == 2
    assert calls == [] and list(tmp_path.iterdir()) == []


def test_a_claim_error_other_than_exists_is_not_reported_as_existing(fake_runs, monkeypatch):
    tmp_path, calls = fake_runs
    real_mkdir = Path.mkdir

    def mkdir(self, *a, **k):
        if self.name == "locked":
            raise PermissionError(13, "Access is denied", str(self))
        return real_mkdir(self, *a, **k)

    monkeypatch.setattr(Path, "mkdir", mkdir)
    with pytest.raises(PermissionError) as e:
        evaluate("hand", [1], workers=1, run="locked", verify=False)
    assert not isinstance(e.value, ev.RunExistsError) and calls == []


def test_cli_reports_only_a_claimed_folder_as_existing(fake_runs, monkeypatch):
    def job(policy_name, seed, cap_s, run_dir, verify):
        raise FileExistsError("some other file")

    monkeypatch.setattr(ev, "_play_seed", job)
    with pytest.raises(FileExistsError, match="some other file"):
        main(["--policy", "hand", "--seeds", "1", "--run", "e"])


def test_sd_of_two_games_is_the_sample_sd(fake_runs):
    s = evaluate("hand", [2001, 2009], workers=2, run="sd2", verify=False)
    assert s["aggregate"]["trips"]["sd"] == pytest.approx(statistics.stdev([1, 9])) and s["aggregate"]["trips"]["sd"] > 0


def test_games_in_input_order_when_completion_order_differs(fake_runs, monkeypatch):
    tmp_path, _ = fake_runs
    done, lock = [], threading.Lock()

    def job(policy_name, seed, cap_s, run_dir, verify):
        # finish in reverse input order: 2003, then 2002, then 2001
        while True:
            with lock:
                if seed == 2003 or (seed == 2002 and 2003 in done) or (seed == 2001 and 2002 in done):
                    done.append(seed)
                    break
            time.sleep(0.005)
        return {**_fake_game(seed, seed % 100), "verified": None}

    monkeypatch.setattr(ev, "_play_seed", job)
    s = evaluate("hand", [2001, 2002, 2003], workers=3, run="ord", verify=False)
    assert done == [2003, 2002, 2001] and [g["scenario_seed"] for g in s["games"]] == [2001, 2002, 2003]
    lines = (tmp_path / "ord" / "games.jsonl").read_text().splitlines()
    assert [json.loads(l)["scenario_seed"] for l in lines] == [2001, 2002, 2003]


def test_pythonhashseed_is_set_before_the_pool(fake_runs, monkeypatch):
    monkeypatch.delenv("PYTHONHASHSEED", raising=False)
    seen = {}

    def make_pool(workers, abort):
        seen["env"] = os.environ.get("PYTHONHASHSEED")
        return _thread_pool(workers, abort)

    monkeypatch.setattr(ev, "_make_pool", make_pool)
    s = evaluate("hand", [2000], workers=1, run="hs", verify=False)
    assert seen["env"] == "0" and s["config"]["PYTHONHASHSEED"] == "0"


@pytest.mark.parametrize("asked, seeds, want", [(0, 2, 1), (-3, 2, 1), (10, 3, 3), (2, 5, 2)])
def test_workers_are_clamped(fake_runs, monkeypatch, asked, seeds, want):
    seen = []

    def make_pool(workers, abort):
        seen.append(workers)
        return _thread_pool(workers, abort)

    monkeypatch.setattr(ev, "_make_pool", make_pool)
    s = evaluate("hand", list(range(1, seeds + 1)), workers=asked, run="w", verify=False)
    assert seen == [want] and s["config"]["workers"] == want


def test_real_pool_is_a_spawn_process_pool_with_the_initializer():
    abort = ev._new_abort_flag()
    pool = ev._make_pool(2, abort)
    try:
        assert isinstance(pool, ev.ProcessPoolExecutor)
        assert pool._initializer is ev._init_worker and pool._initargs == (abort,) and pool._max_workers == 2
        assert pool._mp_context.get_start_method() == "spawn"
    finally:
        pool.shutdown(wait=True)


def test_abort_flag_is_shared_with_spawned_workers():
    """The lock-free flag travels through initargs into a real spawned worker and is shared both ways."""
    abort = ev._new_abort_flag()
    assert abort.value == 0
    pool = ev._make_pool(1, abort)
    try:
        assert pool.submit(_probe_abort_value).result(timeout=60) == 0
        abort.value = 1  # the parent's write is seen by the worker
        assert pool.submit(_probe_abort_value).result(timeout=60) == 1
        abort.value = 0
        assert pool.submit(_probe_raise_abort).result(timeout=60) == 0
        assert abort.value == 1  # ... and the worker's write by the parent
    finally:
        _shutdown_or_fail(pool)


def _shutdown_or_fail(pool, timeout_s=30.0):
    """pool.shutdown(wait=True), but fail instead of hanging if a worker cannot exit (non-daemon watchdog)."""
    t = threading.Thread(target=pool.shutdown, kwargs={"wait": True}, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        for p in list((pool._processes or {}).values()):
            p.terminate()
        t.join(10)
        pytest.fail("a pool worker did not exit at shutdown")


def _probe_abort_value():
    return ev._ABORT.value


def _probe_raise_abort():
    before = ev._ABORT.value
    ev._ABORT.value = 1
    return before


def test_abort_flag_takes_no_lock():
    """RawValue: no lock a terminated worker could leave held (a multiprocessing Event or Value has one)."""
    abort = ev._new_abort_flag()
    assert not hasattr(abort, "get_lock") and not hasattr(abort, "is_set")


def test_verifier_build_fault_writes_error_and_no_summary(fake_runs, monkeypatch):
    tmp_path, calls = fake_runs

    def broken_build():
        raise RuntimeError("build fault on purpose")

    monkeypatch.setattr(ev, "build_verifier", broken_build)
    with pytest.raises(RuntimeError, match="on purpose"):
        evaluate("hand", [2000], workers=1, run="bf", verify=True)
    assert calls == []
    run = tmp_path / "bf"
    assert "build fault on purpose" in (run / "error.txt").read_text()
    assert sorted(p.name for p in run.iterdir()) == ["error.txt", "replays"]


def test_failure_leaves_no_partial_games_file(fake_runs, monkeypatch):
    tmp_path, _ = fake_runs

    def job(policy_name, seed, cap_s, run_dir, verify):
        if seed == 2002:
            time.sleep(0.2)
            raise RuntimeError("late fault")
        return {**_fake_game(seed, 1), "verified": None}

    monkeypatch.setattr(ev, "_play_seed", job)
    with pytest.raises(RuntimeError, match="late fault"):
        evaluate("hand", [2000, 2001, 2002], workers=3, run="pf", verify=False)
    assert sorted(p.name for p in (tmp_path / "pf").iterdir()) == ["error.txt", "replays"]


class _GreedyPool(ThreadPoolExecutor):
    """Like ProcessPoolExecutor, queued jobs cannot be cancelled: they were already handed to the workers."""

    def shutdown(self, wait=True, *, cancel_futures=False):
        super().shutdown(wait=wait, cancel_futures=False)


@pytest.mark.parametrize("interrupt", [RuntimeError("first job fails"), KeyboardInterrupt()])
def test_failure_skips_the_jobs_already_handed_out(fake_runs, monkeypatch, interrupt):
    tmp_path, _ = fake_runs
    played = []

    def job(policy_name, seed, cap_s, run_dir, verify):
        played.append(seed)
        if seed == 0:
            raise interrupt
        time.sleep(0.2)
        return {**_fake_game(seed, 1), "verified": None}

    monkeypatch.setattr(ev, "_play_seed", job)
    monkeypatch.setattr(ev, "_make_pool", lambda workers, abort: _GreedyPool(
        max_workers=workers, initializer=ev._init_worker, initargs=(abort,)))
    t = time.perf_counter()
    with pytest.raises(type(interrupt)):
        evaluate("hand", list(range(40)), workers=2, run="ab", verify=False)
    # Seed 0 fails at once; only the game running on the other worker (and at most one more started before
    # the parent saw the failure) is played. Without the abort event all 40 would be (about 4 s).
    assert len(played) <= 4 and time.perf_counter() - t < 2.0
    assert (tmp_path / "ab" / "error.txt").exists() and not (tmp_path / "ab" / "summary.json").exists()


def test_parent_interrupt_skips_the_jobs_already_handed_out(fake_runs, monkeypatch):
    """Ctrl+C in the parent (here: while it waits for results) also stops the workers' queued jobs."""
    tmp_path, _ = fake_runs
    played = []

    def job(policy_name, seed, cap_s, run_dir, verify):
        played.append(seed)
        time.sleep(0.2)
        return {**_fake_game(seed, 1), "verified": None}

    def interrupted_as_completed(futures):
        raise KeyboardInterrupt

    monkeypatch.setattr(ev, "_play_seed", job)
    monkeypatch.setattr(ev, "as_completed", interrupted_as_completed)
    monkeypatch.setattr(ev, "_make_pool", lambda workers, abort: _GreedyPool(
        max_workers=workers, initializer=ev._init_worker, initargs=(abort,)))
    with pytest.raises(KeyboardInterrupt):
        evaluate("hand", list(range(40)), workers=2, run="pi", verify=False)
    assert len(played) <= 4
    assert "KeyboardInterrupt" in (tmp_path / "pi" / "error.txt").read_text()


def test_config_values(fake_runs, monkeypatch):
    def fake_git(*args):
        return {"rev-parse": "abc123\n", "status": " M evolved_rules/x.py\n"}[args[0]]

    monkeypatch.setattr(ev, "_git", fake_git)
    cfg = evaluate("nothing", [2000], workers=1, run="cfg", verify=False, cap_s=123.0)["config"]
    assert cfg["commit"] == "abc123" and cfg["dirty"] is True
    for name in ("numpy", "scipy", "deap", "cma"):
        try:
            want = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            want = None
        assert cfg["packages"][name] == want
    assert cfg["python"] == sys.version and cfg["host_dll"] == str(default_host_dll())
    assert cfg["policy"] == "nothing" and cfg["cap_s"] == 123.0 and cfg["verify"] is False

    monkeypatch.setattr(ev, "_git", lambda *a: {"rev-parse": "abc\n", "status": ""}[a[0]])
    assert evaluate("nothing", [2000], workers=1, run="cfg2", verify=False)["config"]["dirty"] is False
    monkeypatch.setattr(ev, "_git", lambda *a: None)
    c3 = evaluate("nothing", [2000], workers=1, run="cfg3", verify=False)["config"]
    assert c3["commit"] is None and c3["dirty"] is None


def test_missing_package_version_is_none():
    assert ev._package_version("surely-not-an-installed-package-xyz") is None


# ---------------------------------------------------------------------------------------------------------
# The real _run_seed, in process: a dummy host, play_game and verify_recording replaced
# ---------------------------------------------------------------------------------------------------------

class _DummyHost:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _result(seed, recording):
    return GameResult(7, 50.0, 0, 50, {"wait": 50}, 0.0, 0.0, True, False, seed, "LosAngeles", True, 3, 4,
                      recording)


@pytest.fixture
def in_process(tmp_path, monkeypatch):
    calls = {"play": [], "verify": []}
    recording = {"source": "x", "actions": [{"command": "wait", "n": 1}]}

    def play(host, seed, policy, cap_s=3600.0, record=True):
        calls["play"].append((host, seed, type(policy), cap_s, record))
        return _result(seed, recording)

    host = _DummyHost()
    monkeypatch.setattr(ev, "_HOST", host)
    monkeypatch.setattr(ev, "_ABORT", None)
    monkeypatch.setattr(ev, "play_game", play)
    (tmp_path / "replays").mkdir()
    return tmp_path, calls, recording, host


def test_run_seed_rejection_is_false_and_replay_written(in_process, monkeypatch):
    tmp_path, calls, recording, host = in_process

    def verify(path, timeout=None):
        calls["verify"].append(str(path))
        return False, "diverged"

    monkeypatch.setattr(ev, "verify_recording", verify)
    g = ev._run_seed("hand", 2005, 77.0, str(tmp_path), True)
    path = tmp_path / "replays" / "2005.json"
    assert g["verified"] is False and g["privileged"] is False
    assert json.loads(path.read_text()) == recording
    assert calls["verify"] == [str(path)]
    assert calls["play"] == [(host, 2005, HandRule, 77.0, True)]
    assert list(g) == SUMMARY_KEYS + ["privileged", "verified"]
    assert ev._HOST is host and not host.closed  # a rejection is a verdict, not a fault: the host is kept
    # the verifier's output is kept next to the replay, so a failed verification can be diagnosed
    assert (tmp_path / "replays" / "2005.verify.txt").read_text(encoding="utf-8") == "diverged"


def test_run_seed_pass_is_true_and_nothing_plays_do_nothing(in_process, monkeypatch):
    tmp_path, calls, _, _ = in_process
    monkeypatch.setattr(ev, "verify_recording", lambda path, timeout=None: (True, "PASS"))
    g = ev._run_seed("nothing", 2006, 60.0, str(tmp_path), True)
    assert g["verified"] is True and g["privileged"] is False
    assert sorted(p.name for p in (tmp_path / "replays").iterdir()) == ["2006.json"]  # no .verify.txt on a pass
    assert calls["play"][0][2] is DoNothing and calls["play"][0][3:] == (60.0, True)


def test_run_seed_verifier_fault_propagates_and_closes_the_host(in_process, monkeypatch):
    tmp_path, _, _, host = in_process

    def fault(path, timeout=None):
        raise RuntimeError("verifier fault exit 3")

    monkeypatch.setattr(ev, "verify_recording", fault)
    abort = ev._new_abort_flag()
    monkeypatch.setattr(ev, "_ABORT", abort)
    with pytest.raises(RuntimeError, match="exit 3"):
        ev._run_seed("hand", 2007, 60.0, str(tmp_path), True)
    assert host.closed and ev._HOST is None
    assert abort.value == 1  # the worker stops its own queued jobs before the parent has seen the failure


def test_run_seed_interrupt_closes_the_host_and_the_next_job_gets_a_fresh_one(in_process, monkeypatch):
    tmp_path, calls, _, host = in_process

    def interrupted(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(ev, "play_game", interrupted)
    with pytest.raises(KeyboardInterrupt):
        ev._run_seed("hand", 2010, 60.0, str(tmp_path), False)
    assert host.closed and ev._HOST is None
    fresh = _DummyHost()
    monkeypatch.setattr(ev, "Host", lambda: fresh)
    monkeypatch.setattr(ev, "play_game", lambda h, seed, policy, cap_s, record: _result(seed, {"a": h is fresh}))
    ev._run_seed("hand", 2011, 60.0, str(tmp_path), False)
    assert ev._HOST is fresh and json.loads((tmp_path / "replays" / "2011.json").read_text()) == {"a": True}


def test_run_seed_no_verify_is_none(in_process, monkeypatch):
    tmp_path, _, _, _ = in_process

    def never(path, timeout=None):
        raise AssertionError("verify_recording must not be called when verify=False")

    monkeypatch.setattr(ev, "verify_recording", never)
    g = ev._run_seed("hand", 2008, 60.0, str(tmp_path), False)
    assert g["verified"] is None and (tmp_path / "replays" / "2008.json").exists()
    assert not (tmp_path / "replays" / "2008.verify.txt").exists()


def test_run_seed_reference_dispatch(in_process, monkeypatch):
    tmp_path, calls, _, host = in_process
    seen = []
    monkeypatch.setattr(ev, "run_reference", lambda h, seed, cap_s: seen.append((h, seed, cap_s)) or {"x": 1})
    assert ev._run_seed("reference", 2009, 55.0, str(tmp_path), False) == {"x": 1}
    assert seen == [(host, 2009, 55.0)] and calls["play"] == []
    assert list((tmp_path / "replays").iterdir()) == []


def test_run_seed_returns_at_once_when_aborted(in_process, monkeypatch):
    tmp_path, calls, _, _ = in_process
    abort = ev._new_abort_flag()
    abort.value = 1
    monkeypatch.setattr(ev, "_ABORT", abort)
    assert ev._run_seed("hand", 2012, 60.0, str(tmp_path), True) is None
    assert calls["play"] == [] and list((tmp_path / "replays").iterdir()) == []


# ---------------------------------------------------------------------------------------------------------
# run_reference on a fake host
# ---------------------------------------------------------------------------------------------------------

class FakeHost:
    """1 simulated second per 20-tick step. An offer is pending at t=3 (cleared by an upgrade); the reference
    at t=10 is rejected; two vehicles wait 2.0 and 5.0 at t=4; the game terminates at t=end with shops 9 and 4
    tied on overcrowding."""

    def __init__(self, end=25):
        self.t, self.end, self.offer, self.log = 0, end, False, []

    def _obs(self):
        shops = []
        if self.t >= self.end:
            a = shop(9, 0, 10, 10, 2, 2, [(10, 12, 2)])
            b = shop(4, 1, 20, 10, 2, 2, [(20, 12, 2)])
            c = shop(2, 2, 30, 10, 2, 2, [(30, 12, 2)])
            a["overcrowdedFor"], b["overcrowdedFor"], c["overcrowdedFor"] = 30.0, 30.0, 10.0
            shops = [a, b, c]
        vehicles = [{"color": 0, "stage": "Home", "waiting": 2.0},
                    {"color": 1, "stage": "ToShop", "waiting": 5.0}] if self.t == 4 else []
        offers = [{"type": 1, "amount": 1, "roads": 0}, {"type": 2, "amount": 1, "roads": 5}] if self.offer else []
        obs = make_obs(buildings=shops, time=float(self.t), offers=offers, vehicles=vehicles,
                       inventory=(7, 2, 0, 0, 0, 0))
        obs["tripsCompleted"] = 11
        return obs

    def reset(self, seed, scenario="LosAngeles"):
        self.log.append(("reset", seed, scenario))
        return {"observation": self._obs(), "terminated": False, "truncated": False}

    def call(self, **req):
        self.log.append((self.t, dict(req)))
        if req["command"] == "step":
            assert req.get("ticks") == 20
            self.t += 1
            if self.t == 3:
                self.offer = True
            return {"observation": self._obs(), "terminated": self.t >= self.end, "truncated": False}
        if req["command"] == "upgrade":
            self.offer = False
            return {"accepted": True}
        if req["command"] == "reference":
            return {"accepted": self.t != 10}
        raise AssertionError(f"unexpected command {req}")


def test_reference_cadence_offer_and_counters():
    h = FakeHost(end=25)
    r = run_reference(h, 2000, cap_s=3600.0)
    assert h.log[0] == ("reset", 2000, "LosAngeles")
    entries = h.log[1:]
    sent = [(t, q) for t, q in entries if q["command"] != "step"]
    # a reference at the start, then every 10 s; the pending offer is answered with offer 0
    assert sent == [(0, {"command": "reference"}), (3, {"command": "upgrade", "choice": 0}),
                    (10, {"command": "reference"}), (20, {"command": "reference"})]
    # every command is followed by a step of 20 ticks; a wait is a bare step of 20 ticks
    for i, (t, q) in enumerate(entries):
        if q["command"] != "step":
            assert entries[i + 1][1] == {"command": "step", "ticks": 20}
    assert all(q == {"command": "step", "ticks": 20} for _, q in entries if q["command"] == "step")
    assert sum(1 for _, q in entries if q["command"] == "step") == 25
    assert r["action_counts"] == {"reference": 3, "upgrade": 1, "wait": 21}
    assert r["commands"] == 25 and r["rejected_actions"] == 1  # the reference at t=10
    assert r["mean_car_wait"] == 3.5 and r["max_car_wait"] == 5.0
    assert r["terminated"] is True and r["truncated"] is False and r["seconds"] == 25.0 and r["trips"] == 11
    assert r["failed_shop"] == 4 and r["road_tiles_at_failure"] == 7  # tie 9 vs 4 at 30 s -> lower id; inventory[0]
    assert r["privileged"] is True and r["verified"] is None
    assert r["scenario_seed"] == 2000 and r["city"] == "LosAngeles" and r["deterministic"] is True
    assert list(r) == SUMMARY_KEYS + ["privileged", "verified"]


class _RejectingFakeHost(FakeHost):
    """From t = reject_at, every reply says truncated (scenario rejected) and time stops advancing."""

    def __init__(self, reject_at, on_command=False):
        super().__init__(end=10_000)
        self.reject_at, self.on_command = reject_at, on_command

    def call(self, **req):
        assert len(self.log) < 1000, "run_reference kept going after a truncated reply"
        if self.t >= self.reject_at and (req["command"] == "step" or self.on_command):
            self.log.append((self.t, dict(req)))
            return {"accepted": True, "observation": self._obs(), "terminated": False, "truncated": True,
                    "message": "infeasible"}
        return super().call(**req)


@pytest.mark.parametrize("on_command", [False, True])
def test_reference_raises_when_the_scenario_is_rejected_mid_game(on_command):
    from evolved_rules.host import ScenarioRejected
    h = _RejectingFakeHost(reject_at=10, on_command=on_command)
    with pytest.raises(ScenarioRejected, match="truncated reply to 'reference'" if on_command else "'step'"):
        run_reference(h, 2000, cap_s=3600.0)
    assert h.t == 10


def test_reference_truncated_at_cap():
    h = FakeHost(end=10_000)
    r = run_reference(h, 2001, cap_s=15.0)
    assert r["seconds"] == 15.0 and r["truncated"] is True and r["terminated"] is False
    assert r["failed_shop"] is None and r["road_tiles_at_failure"] is None
    assert r["commands"] == 15 and r["mean_car_wait"] == 3.5


# ---------------------------------------------------------------------------------------------------------
# Host tests
# ---------------------------------------------------------------------------------------------------------

@pytest.mark.host
def test_run_reference_is_privileged(host):
    r = run_reference(host, 2000, cap_s=60.0)
    assert list(r) == SUMMARY_KEYS + ["privileged", "verified"]
    assert r["privileged"] is True and r["verified"] is None
    assert r["action_counts"]["reference"] >= 1
    assert set(r["action_counts"]) <= {"reference", "upgrade", "wait"}
    assert sum(r["action_counts"].values()) == r["commands"]
    assert r["truncated"] and not r["terminated"] and r["seconds"] >= 60.0 and r["scenario_seed"] == 2000


@pytest.mark.host
def test_evaluate_reference_writes_no_replay(host_dll, tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "RUNS_DIR", tmp_path)
    s = evaluate("reference", [2000], workers=1, run="r", verify=True, cap_s=60.0)
    g = s["games"][0]
    assert g["privileged"] is True and g["verified"] is None and "reference" in g["action_counts"]
    assert s["aggregate"]["verified_total"] == 0
    assert not (tmp_path / "r" / "replays").exists()
    assert sorted(p.name for p in (tmp_path / "r").iterdir()) == ["games.jsonl", "summary.json"]


@pytest.mark.host
def test_results_do_not_depend_on_worker_count(host_dll, tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "RUNS_DIR", tmp_path)
    one = evaluate("hand", [2000, 2001], workers=1, run="w1", verify=False, cap_s=300.0)
    two = evaluate("hand", [2000, 2001], workers=2, run="w2", verify=False, cap_s=300.0)
    assert one["games"] == two["games"]
    assert one["games"][0]["trips"] > 0
    for seed in (2000, 2001):
        assert ((tmp_path / "w1" / "replays" / f"{seed}.json").read_bytes()
                == (tmp_path / "w2" / "replays" / f"{seed}.json").read_bytes())


@pytest.mark.host
def test_cli_end_to_end(host_dll, verifier, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ev, "RUNS_DIR", tmp_path)
    assert main(["--policy", "hand", "--seeds", "2000", "--workers", "2", "--run", "cli", "--verify",
                 "--cap", "60"]) == 0
    s = json.loads((tmp_path / "cli" / "summary.json").read_text())
    assert s["config"]["cap_s"] == 60.0 and s["config"]["workers"] == 1
    assert s["aggregate"]["verified_pass"] == 1 and s["aggregate"]["verified_total"] == 1
    assert s["games"][0]["verified"] is True and s["games"][0]["truncated"]
    assert s["games"][0]["privileged"] is False
    assert (tmp_path / "cli" / "replays" / "2000.json").exists()
    assert "verified 1/1" in capsys.readouterr().out


# ---------------------------------------------------------------------------------------------------------
# Fix round 2: interrupt and failure timing, parent watchdog
# ---------------------------------------------------------------------------------------------------------

def test_worker_interrupt_also_aborts_the_run(in_process, monkeypatch):
    tmp_path, _, _, host = in_process
    abort = ev._new_abort_flag()
    monkeypatch.setattr(ev, "_ABORT", abort)

    def interrupted(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(ev, "play_game", interrupted)
    with pytest.raises(KeyboardInterrupt):
        ev._run_seed("hand", 1, 60.0, str(tmp_path), False)
    assert abort.value == 1 and host.closed


def test_failure_returns_only_after_running_jobs_finished(fake_runs, monkeypatch):
    """evaluate() re-raises only once the running games are done (no replay can land after error.txt)."""
    running, played = [], []

    def job(policy_name, seed, cap_s, run_dir, verify):
        if seed == 1:
            time.sleep(0.1)  # seed 2 is running by now
            raise RuntimeError("fail")
        running.append(seed)
        played.append(seed)
        time.sleep(0.5)
        running.remove(seed)
        return {**_fake_game(seed, 1), "verified": None}

    monkeypatch.setattr(ev, "_play_seed", job)
    with pytest.raises(RuntimeError, match="fail"):
        evaluate("hand", [1, 2], workers=2, run="w", verify=False)
    assert played == [2] and running == []  # seed 2 was running when seed 1 failed, and finished first


class _FakeParent:
    def __init__(self, log):
        self.log = log

    def join(self, *a):
        self.log.append(("join", a))


class _Exited(BaseException):
    pass


def test_exit_with_parent_joins_the_parent_then_hard_exits(monkeypatch):
    log = []
    monkeypatch.setattr(ev.multiprocessing, "parent_process", lambda: _FakeParent(log))

    def fake_exit(code):
        log.append(("_exit", code))
        raise _Exited

    monkeypatch.setattr(ev.os, "_exit", fake_exit)
    with pytest.raises(_Exited):
        ev._exit_with_parent()
    assert log == [("join", ()), ("_exit", 1)]  # waits for the parent with no timeout, then os._exit(1)


def test_exit_with_parent_is_a_no_op_outside_a_worker(monkeypatch):
    monkeypatch.setattr(ev.multiprocessing, "parent_process", lambda: None)
    monkeypatch.setattr(ev.os, "_exit", lambda code: pytest.fail("must not exit"))
    assert ev._exit_with_parent() is None


def test_init_worker_starts_the_watchdog_as_a_daemon_thread(monkeypatch):
    started = []

    class FakeThread:
        def __init__(self, target=None, name=None, daemon=None):
            self.target, self.daemon = target, daemon

        def start(self):
            started.append((self.target, self.daemon))

    monkeypatch.setattr(ev, "threading", types.SimpleNamespace(Thread=FakeThread))
    monkeypatch.setattr(ev, "_ABORT", None)
    flag = ev._new_abort_flag()
    ev._init_worker(flag)
    assert ev._ABORT is flag
    # daemon: a non-daemon watchdog would keep every worker alive forever and hang pool.shutdown()
    assert started == [(ev._exit_with_parent, True)]


_k32 = ctypes.WinDLL("kernel32", use_last_error=True) if sys.platform == "win32" else None
if _k32 is not None:
    _k32.OpenProcess.restype = ctypes.c_void_p


def _wait_gone(pid, timeout_s):
    """True once process `pid` has exited (or never existed), within timeout_s."""
    h = _k32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not h:
        return True
    try:
        return _k32.WaitForSingleObject(ctypes.c_void_p(h), int(timeout_s * 1000)) == 0
    finally:
        _k32.CloseHandle(ctypes.c_void_p(h))


_PARENT = textwrap.dedent("""
    import os, sys, time
    from evolved_rules import evaluate as ev
    if __name__ == "__main__":
        pool = ev._make_pool(1, ev._new_abort_flag())
        print(os.getpid(), pool.submit(os.getpid).result(timeout=60), flush=True)
        time.sleep(600)
""")


@pytest.mark.skipif(sys.platform != "win32", reason="uses taskkill and kernel32 process handles")
def test_worker_exits_when_its_parent_is_hard_killed(tmp_path):
    """Watchdog, end to end: the real spawned worker of a hard-killed parent is gone within a few seconds."""
    script = tmp_path / "parent.py"
    script.write_text(_PARENT, encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(Path(ev.__file__).resolve().parents[1]))
    parent = subprocess.Popen([sys.executable, str(script)], stdout=subprocess.PIPE, text=True, env=env)
    worker = None
    try:
        # interp is the real interpreter (sys.executable may be the venv launcher)
        interp, worker = map(int, parent.stdout.readline().split())
        assert not _wait_gone(worker, 1.0)  # healthy while the parent lives: the watchdog does not fire early
        subprocess.run(["taskkill", "/F", "/PID", str(interp)], capture_output=True)  # no cleanup in the parent
        assert _wait_gone(interp, 10.0)
        assert _wait_gone(worker, 10.0), "worker outlived its hard-killed parent"
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()
        if worker is not None and not _wait_gone(worker, 0):
            subprocess.run(["taskkill", "/F", "/PID", str(worker)], capture_output=True)


# ---------------------------------------------------------------------------------------------------------
# Phase 2 Task 4: --policy tree:<file>
# ---------------------------------------------------------------------------------------------------------
from evolved_rules.gp import HAND_TEXT, TreePolicy


def _tree_file(tmp_path, text=HAND_TEXT, name="best.txt"):
    f = tmp_path / "src" / name
    f.parent.mkdir(exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


def test_tree_policy_runs_from_a_copy_in_the_run_folder(fake_runs):
    tmp_path, calls = fake_runs
    f = _tree_file(tmp_path, "\n" + HAND_TEXT.replace("\n", "\n\n") + "\n\n")  # canonicalised on the way in
    spec = f"tree:{f}"
    assert main(["--policy", spec, "--seeds", "2000-2001", "--run", "t", "--workers", "2", "--verify"]) == 0
    run = tmp_path / "t"
    assert (run / "policy.txt").read_text(encoding="utf-8") == HAND_TEXT + "\n"
    jobs = [c for c in calls if c != "build"]
    assert sorted(c[1] for c in jobs) == [2000, 2001]
    assert {c[0] for c in jobs} == {f"tree:{run / 'policy.txt'}"}  # never the caller's file
    cfg = json.loads((run / "summary.json").read_text())["config"]
    assert cfg["policy"] == spec and cfg["policy_text"] == HAND_TEXT
    assert "build" in calls  # tree policies are recorded and verified like the named ones


def test_named_policies_have_no_policy_text(fake_runs):
    tmp_path, _ = fake_runs
    assert evaluate("hand", [1], workers=1, run="h", verify=False)["config"]["policy_text"] is None
    assert not (tmp_path / "h" / "policy.txt").exists()


@pytest.mark.parametrize("content", [None, "", "priority: neg(tiles_needed)", "priority: x\nhold: 1.0\nupgrade: 1.0"])
def test_bad_tree_policies_are_refused_before_the_folder_is_claimed(fake_runs, capsys, content):
    tmp_path, calls = fake_runs
    spec = "tree:" if content is None else f"tree:{_tree_file(tmp_path, content)}"
    with pytest.raises(ValueError):
        evaluate(spec, [1], workers=1, run="x", verify=False)
    with pytest.raises(SystemExit) as e:
        main(["--policy", spec, "--seeds", "1", "--run", "x"])
    assert e.value.code == 2 and "policy" in capsys.readouterr().err.lower()
    assert calls == [] and sorted(p.name for p in tmp_path.iterdir()) == (["src"] if content is not None else [])


def test_missing_tree_file_and_unknown_policy_are_usage_errors(fake_runs, capsys):
    tmp_path, calls = fake_runs
    for spec in [f"tree:{tmp_path / 'nope.txt'}", "greedy", "Tree:x"]:
        with pytest.raises(SystemExit) as e:
            main(["--policy", spec, "--seeds", "1", "--run", "x"])
        assert e.value.code == 2
    assert calls == [] and list(tmp_path.iterdir()) == []


def test_make_policy_builds_a_coverage_tree_policy(tmp_path):
    p = ev.make_policy(f"tree:{_tree_file(tmp_path)}")
    assert isinstance(p, TreePolicy) and p.coverage is True and p.text == HAND_TEXT
    assert isinstance(ev.make_policy("hand"), HandRule)


@pytest.mark.host
def test_cli_tree_policy_end_to_end(host_dll, verifier, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ev, "RUNS_DIR", tmp_path / "runs")
    f = _tree_file(tmp_path)
    assert main(["--policy", f"tree:{f}", "--seeds", "2000", "--run", "tree", "--verify", "--cap", "60"]) == 0
    s = json.loads((tmp_path / "runs" / "tree" / "summary.json").read_text())
    assert s["aggregate"]["verified_pass"] == 1 and s["games"][0]["trips"] >= 0
    rec = json.loads((tmp_path / "runs" / "tree" / "replays" / "2000.json").read_text())
    assert rec["source"] == "evolved-rules:tree"
