"""Evaluation: play many games in parallel, verify their replays and write the result tables.

    PY -m evolved_rules.evaluate --policy {hand,nothing,separated,reference} --seeds 1000 2000-2019 --workers 10 \
        --run NAME [--verify] [--cap 3600]

A run writes output/evolved_rules/runs/<run>/: replays/<seed>.json (recorded policies only; a replay that fails
verification also gets replays/<seed>.verify.txt, the verifier's output), games.jsonl (one game summary per
line, in input seed order) and summary.json (config, games, aggregate). summary.json is
written last, so a run folder without it is not a result; a failed run leaves error.txt (the traceback)
instead. Each worker process keeps one long-lived Host and plays one seed per job; a (policy, seed) game is
deterministic, so the results do not depend on the worker count.

Process robustness: a worker exits when its parent process is gone (its host then sees EOF on stdin and
exits too), a failed or interrupted run tells every worker to skip the jobs it has not started, and a job
that raises closes its worker's host so the next job starts on a fresh one.
"""
from __future__ import annotations

import argparse
import atexit
import importlib.metadata
import json
import math
import multiprocessing
import os
import re
import statistics
import subprocess
import sys
import threading
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .agent import play_game, trips_per_tile
from .host import ROOT, Host, default_host_dll
from .rules import DoNothing, HandRule, SeparatedPreference
from .session import DEFAULT_SCENARIO, TICKS, raise_if_rejected
from .state import parse_observation
from .verify import build_verifier, verify_recording

RUNS_DIR = ROOT / "output" / "evolved_rules" / "runs"  # /output/ is git-ignored
POLICIES = {"hand": HandRule, "nothing": DoNothing, "separated": SeparatedPreference}
REFERENCE = "reference"  # the privileged baseline: the host's own network builder, never recorded
POLICY_NAMES = (*POLICIES, REFERENCE)
REFERENCE_EVERY_S = 10.0
PACKAGES = ("numpy", "scipy", "deap", "cma")
DEFAULT_CAP_S = 3600.0
EXISTING_RUN_EXIT_CODE = 2


class RunExistsError(FileExistsError):
    """The run folder already exists (raised by the folder claim, before any game)."""


def parse_seeds(spec: list[str]) -> list[int]:
    """"1000" and inclusive ranges "2000-2019" -> seeds, de-duplicated in first-seen order.

    ValueError for anything that is not an integer or a range a-b with a <= b.
    """
    seeds: list[int] = []
    seen: set[int] = set()  # membership only; the order comes from the list
    for item in spec:
        text = str(item).strip()
        lo_text, sep, hi_text = text.partition("-")
        try:
            lo = int(lo_text)
            hi = int(hi_text) if sep else lo
        except ValueError:
            raise ValueError(f"not a seed or a seed range a-b: {item!r}") from None
        if lo > hi:
            raise ValueError(f"empty seed range {item!r}: {lo} > {hi}")
        for seed in range(lo, hi + 1):
            if seed not in seen:
                seen.add(seed)
                seeds.append(seed)
    return seeds


# ---------------------------------------------------------------------------------------------------------
# The privileged reference baseline
# ---------------------------------------------------------------------------------------------------------

def run_reference(host: Host, seed: int, cap_s: float = DEFAULT_CAP_S) -> dict:
    """Privileged diagnostic baseline: the host's debug network builder, played under the normal finite road stock.

    It is not an upper bound (it usually scores below HandRule): `reference` (world.BuildReferenceNetwork) tries
    to build a route for every house / same-colour shop pair and soon runs out of road. A rejected reference is
    a call where BuildReferenceNetwork returned false: the network is still incomplete, usually because the
    stock ran out (such a call may still have built some roads). Never recorded and never verified.

    Loop until terminated or at cap_s: a pending offer is answered with offer 0; otherwise, every
    REFERENCE_EVERY_S simulated seconds (first at the start), {"command": "reference"}; otherwise a wait.
    Every command is followed by step 20 and a wait is a bare step 20, as in GameSession, whose counters
    (commands, rejections, action_counts, car-wait stats over all vehicles after each step) are mirrored here.
    tiles_built is the road-stock drop over each reference command and its step (accepted or not: a rejected
    reference may still have built roads); trips_per_tile as play_game.
    Returns the keys of GameResult.summary() plus "privileged": True and "verified": None.
    """
    reply = host.reset(seed, DEFAULT_SCENARIO)
    state = parse_observation(reply["observation"])
    terminated = bool(reply["terminated"])
    commands = rejected = 0
    action_counts: dict[str, int] = {}
    wait_sum, wait_n, max_wait = 0.0, 0, 0.0
    tiles_built = 0
    last_reference: float | None = None

    while not terminated and state.time < cap_s:
        if state.offers:
            request = {"command": "upgrade", "choice": 0}
        elif last_reference is None or state.time - last_reference >= REFERENCE_EVERY_S:
            request = {"command": "reference"}
            last_reference = state.time
        else:
            request = None
        if request is None:
            accepted = True
        else:  # a truncated reply (scenario rejected mid-game) raises: time would stop and this loop never end
            reply = host.call(**request)
            raise_if_rejected(reply, request["command"], seed, DEFAULT_SCENARIO)
            accepted = bool(reply["accepted"])
        step = host.call(command="step", ticks=TICKS)
        raise_if_rejected(step, "step", seed, DEFAULT_SCENARIO)
        before, state = state, parse_observation(step["observation"])
        terminated = bool(step["terminated"])
        if request is not None and request["command"] == "reference":
            tiles_built += max(0, (before.inventory[0] if before.inventory else 0)
                               - (state.inventory[0] if state.inventory else 0))
        commands += 1
        if not accepted:
            rejected += 1
        key = "wait" if request is None else request["command"]
        action_counts[key] = action_counts.get(key, 0) + 1
        for w in state.vehicles_waiting:
            wait_sum += w
            wait_n += 1
            max_wait = max(max_wait, w)

    failed_shop = road_tiles_at_failure = None
    if terminated:  # as play_game: the most overcrowded shop (lowest id on ties) and the road stock
        shops = state.shops()
        if shops:
            failed_shop = max(shops, key=lambda s: (s.overcrowded_for, -s.id)).id
        road_tiles_at_failure = state.inventory[0]
    return {
        "trips": state.trips,
        "seconds": state.time,
        "rejected_actions": rejected,
        "commands": commands,
        "action_counts": action_counts,
        "mean_car_wait": wait_sum / wait_n if wait_n else 0.0,
        "max_car_wait": max_wait,
        "terminated": terminated,
        "truncated": not terminated and state.time >= cap_s,
        "scenario_seed": seed,
        "city": DEFAULT_SCENARIO,
        "deterministic": True,
        "failed_shop": failed_shop,
        "road_tiles_at_failure": road_tiles_at_failure,
        "tiles_built": tiles_built,
        "trips_per_tile": trips_per_tile(state.trips, tiles_built),
        "privileged": True,
        "verified": None,
    }


# ---------------------------------------------------------------------------------------------------------
# Worker side (module-level and picklable: workers are spawned on Windows)
# ---------------------------------------------------------------------------------------------------------

_HOST: Host | None = None  # the worker's long-lived host, created on first use by _worker_host
_ABORT = None  # the run's abort flag (shared, lock-free; see _new_abort_flag), set by _init_worker
_ATEXIT_REGISTERED = False


def _close_host() -> None:
    global _HOST
    host, _HOST = _HOST, None
    if host is not None:
        host.close()


def _worker_host() -> Host:
    global _HOST
    if _HOST is None:
        _HOST = Host()
    return _HOST


def _exit_with_parent() -> None:
    """Watchdog thread: end this worker as soon as its parent process is gone, even if it was hard-killed.

    os._exit skips atexit, but the host needs no goodbye: its stdin closes with this process and TrafficHost
    exits on EOF. A verifier subprocess already running finishes its replay and exits by itself.
    """
    parent = multiprocessing.parent_process()
    if parent is None:  # not a multiprocessing child (an in-process test pool)
        return
    parent.join()  # returns once the parent process has exited (Windows: waits on its process handle)
    os._exit(1)


def _init_worker(abort=None) -> None:
    """Pool initializer: keep the run's abort flag, watch the parent, close the host at a normal exit."""
    global _ABORT, _ATEXIT_REGISTERED
    _ABORT = abort
    threading.Thread(target=_exit_with_parent, name="exit-with-parent", daemon=True).start()
    if not _ATEXIT_REGISTERED:
        atexit.register(_close_host)
        _ATEXIT_REGISTERED = True


def _run_seed(policy_name: str, seed: int, cap_s: float, run_dir: str, verify: bool) -> dict | None:
    """One job. Returns None at once, playing nothing, if the run is being aborted.

    Any exception fails the whole run, so it raises the abort flag itself: this worker takes its next queued
    job before the parent has seen the failure, and must skip it too. The exception (including a
    KeyboardInterrupt in the middle of a host call, which can leave an unread reply behind) also closes this
    worker's host before it propagates, so a later job would start on a fresh host.
    """
    if _ABORT is not None and _ABORT.value:
        return None
    try:
        return _play_seed(policy_name, seed, cap_s, run_dir, verify)
    except BaseException:
        if _ABORT is not None:
            _ABORT.value = 1
        _close_host()
        raise


def _play_seed(policy_name: str, seed: int, cap_s: float, run_dir: str, verify: bool) -> dict:
    """Play one seed on this worker's host; save and (if asked) verify its replay. Returns its summary."""
    host = _worker_host()
    if policy_name == REFERENCE:
        return run_reference(host, seed, cap_s)
    result = play_game(host, seed, POLICIES[policy_name](), cap_s=cap_s, record=True)
    summary = result.summary()
    summary["privileged"] = False
    path = Path(run_dir) / "replays" / f"{seed}.json"
    path.write_text(json.dumps(result.recording), encoding="utf-8")
    # A verifier fault (RuntimeError) propagates and fails the run; only a rejection is a False verdict.
    verified = None
    if verify:
        verified, output = verify_recording(path)
        if not verified:  # keep the verifier's reason (e.g. the command that diverged) next to the replay
            path.with_name(f"{seed}.verify.txt").write_text(output, encoding="utf-8")
    summary["verified"] = verified
    return summary


MP_CONTEXT = multiprocessing.get_context("spawn")  # the Windows default, made explicit


def _new_abort_flag():
    """A shared byte, 0 until the run aborts; anyone may read `.value`, and writers only ever store 1.

    Deliberately lock-free (RawValue, not Event or Value): a worker terminated while holding a lock (the pool
    terminates every worker when one dies) would leave it held forever, and the parent's next set() would
    block for good. A single-byte store and load need no lock.
    """
    return MP_CONTEXT.RawValue("b", 0)


def _make_pool(workers: int, abort):
    """The executor that runs the jobs (a separate function so tests can substitute an in-process one).

    The abort flag reaches the workers through initargs: a spawned worker inherits the shared memory when it
    is created.
    """
    return ProcessPoolExecutor(max_workers=workers, mp_context=MP_CONTEXT, initializer=_init_worker,
                               initargs=(abort,))


# ---------------------------------------------------------------------------------------------------------
# Parent side
# ---------------------------------------------------------------------------------------------------------

def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _config(policy_name: str, seeds: list[int], cap_s: float, workers: int, verify: bool) -> dict:
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return {
        "commit": commit.strip() if commit is not None else None,
        "dirty": bool(status.strip()) if status is not None else None,
        "packages": {name: _package_version(name) for name in PACKAGES},
        "python": sys.version,
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),  # the workers' value: evaluate() sets it first
        "policy": policy_name,
        "seeds": list(seeds),
        "cap_s": cap_s,
        "host_dll": str(default_host_dll()),
        "workers": workers,
        "verify": verify,
    }


def _stats(values: list[float]) -> dict:
    """Mean, median, min, max and sample SD (0.0 for fewer than two values)."""
    return {
        "mean": float(statistics.mean(values)),
        "median": float(statistics.median(values)),
        "min": float(min(values)),
        "max": float(max(values)),
        "sd": float(statistics.stdev(values)) if len(values) >= 2 else 0.0,
    }


def _aggregate(games: list[dict]) -> dict:
    verified = [g["verified"] for g in games if g.get("verified") is not None]
    return {
        "n": len(games),
        "trips": _stats([g["trips"] for g in games]),
        "seconds": _stats([g["seconds"] for g in games]),
        "verified_pass": sum(1 for v in verified if v is True),
        "verified_total": len(verified),
    }


RUN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# Windows device names: never a folder, whatever the case and with or without an extension ("nul.txt").
RESERVED_NAMES = frozenset(["CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                            *(f"LPT{i}" for i in range(1, 10))])


def _check_run_name(run: str) -> None:
    """ValueError unless `run` is a plain folder name that Windows creates as written.

    Allowed: a letter or digit, then letters, digits, '.', '_' and '-'; no trailing '.' (Windows drops it);
    not a device name such as NUL or com1.txt. This excludes separators, drive prefixes ("C:x"), '.', '..',
    spaces and every character Windows forbids.
    """
    if (not isinstance(run, str) or not RUN_NAME.fullmatch(run) or run.endswith(".")
            or run.split(".")[0].upper() in RESERVED_NAMES):
        raise ValueError(f"run must be a plain folder name ([A-Za-z0-9][A-Za-z0-9._-]*, no trailing '.', "
                         f"not a Windows device name), got {run!r}")


def _check_cap(cap_s) -> None:
    """ValueError unless cap_s is a finite number of seconds greater than 0.

    A cap of 0 or less would end every game at reset with no action (a replay the verifier rejects), and NaN
    would never be reached and is not valid JSON in summary.json.
    """
    try:
        ok = math.isfinite(cap_s) and cap_s > 0
    except TypeError:
        ok = False
    if not ok:
        raise ValueError(f"cap must be a finite number of simulated seconds greater than 0, got {cap_s!r}")


def evaluate(policy_name: str, seeds: list[int], workers: int, run: str, verify: bool,
             cap_s: float = DEFAULT_CAP_S) -> dict:
    """Play every seed (one job per seed on a pool of `workers` processes) and write the run folder.

    Raises RunExistsError (a FileExistsError), before any game, if output/evolved_rules/runs/<run> exists. If any game, worker
    or verification fails, error.txt (the traceback) is written to the run folder, no summary.json is
    written, and the error is re-raised. Returns the summary (also written to summary.json). Bad inputs (policy,
    seeds, run name, a cap that is not finite and > 0) raise ValueError before the folder is claimed.
    """
    if policy_name not in POLICY_NAMES:
        raise ValueError(f"unknown policy {policy_name!r}; expected one of {', '.join(POLICY_NAMES)}")
    seeds = list(seeds)
    if not seeds:
        raise ValueError("no seeds to evaluate")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"duplicate seeds: {seeds}")
    _check_run_name(run)
    _check_cap(cap_s)
    workers = max(1, min(int(workers), len(seeds)))
    recorded = policy_name != REFERENCE
    verify = bool(verify)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_dir = RUNS_DIR / run
    try:
        run_dir.mkdir()  # claims the folder
    except FileExistsError as e:
        raise RunExistsError(f"run folder {run_dir} already exists") from e
    try:
        if recorded:
            (run_dir / "replays").mkdir()
        if verify and recorded:
            build_verifier()  # once, before the pool: no first-build race between workers
        os.environ["PYTHONHASHSEED"] = "0"  # inherited by the spawned workers
        config = _config(policy_name, seeds, cap_s, workers, verify)

        by_seed: dict[int, dict] = {}
        abort = _new_abort_flag()
        pool = _make_pool(workers, abort)
        try:
            futures = {pool.submit(_run_seed, policy_name, seed, cap_s, str(run_dir), verify and recorded): seed
                       for seed in seeds}
            for future in as_completed(futures):
                by_seed[futures[future]] = future.result()
        except BaseException:
            # A ProcessPoolExecutor hands up to 2 x workers + 1 jobs to its workers ahead of time. Those count
            # as running, so cancel_futures cannot drop them; the flag makes each one return without playing.
            # Only the games being played right now then delay the re-raise.
            abort.value = 1
            raise
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

        games = [by_seed[seed] for seed in seeds]
        summary = {"config": config, "games": games, "aggregate": _aggregate(games)}
        (run_dir / "games.jsonl").write_text("".join(json.dumps(g) + "\n" for g in games), encoding="utf-8")
        partial = run_dir / "summary.json.tmp"
        partial.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        os.replace(partial, run_dir / "summary.json")  # last: its presence marks a complete run
        return summary
    except BaseException:
        try:
            (run_dir / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        raise


def _format_aggregate(summary: dict) -> str:
    agg = summary["aggregate"]
    t, s = agg["trips"], agg["seconds"]
    return (f"{agg['n']} games: trips mean {t['mean']:.1f} median {t['median']:g} sd {t['sd']:.1f} "
            f"[{t['min']}, {t['max']}]; seconds mean {s['mean']:.1f} [{s['min']:.1f}, {s['max']:.1f}]; "
            f"verified {agg['verified_pass']}/{agg['verified_total']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evolved_rules.evaluate", description=__doc__.splitlines()[0])
    parser.add_argument("--policy", required=True, choices=POLICY_NAMES)
    parser.add_argument("--seeds", required=True, nargs="+", help='seeds and inclusive ranges, e.g. 1000 2000-2019')
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--run", required=True, help="run folder name under output/evolved_rules/runs")
    parser.add_argument("--verify", action="store_true", help="verify every replay with the pinned verifier")
    parser.add_argument("--cap", type=float, default=DEFAULT_CAP_S, help="episode cap in simulated seconds")
    args = parser.parse_args(argv)
    try:
        seeds = parse_seeds(args.seeds)
        _check_run_name(args.run)
        _check_cap(args.cap)
    except ValueError as e:
        parser.error(str(e))
    try:
        summary = evaluate(args.policy, seeds, args.workers, args.run, args.verify, cap_s=args.cap)
    except RunExistsError:
        print(f"run folder {RUNS_DIR / args.run} already exists; choose another --run name", file=sys.stderr)
        return EXISTING_RUN_EXIT_CODE
    print(f"{RUNS_DIR / args.run}: {_format_aggregate(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
