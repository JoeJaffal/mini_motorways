"""Batch evaluation engine with a persistent result cache (Phase 2 Task 4).

    engine = Engine(workers=10, cap_s=3600.0, cache_path=RUNS / "cache.jsonl")
    results = engine.play([(text, seed), ...])   # one game summary per job, in job order
    engine.record(text, seed, path, verify=True)  # one recorded (and verified) game, for final evaluation

A job is (individual text, seed); its result is the game summary (GameResult.summary(), no recording) of
TreePolicy(text) with coverage targets (the evolved policies' setting) played to cap_s. A game is
deterministic, so a result is cached for good under the key (CODE_VERSION, canonical text, seed, cap_s) in an
append-only JSONL file: a cached job never plays again, in this process or the next one (resume). Duplicate
jobs in one batch play once. Results are returned as fresh JSON-decoded copies, so a cached result and a
freshly played one are equal and independent.

Workers. Each worker slot is a spawn-context ProcessPoolExecutor with exactly one process, set up by
evaluate.py's worker initializer (the parent watchdog: a worker exits when the parent dies) and keeping one
long-lived Host (evaluate._worker_host) across games. The engine hands a slot one game at a time, so every
game starts as soon as it is submitted and its wall-clock deadline (timeout_s, default 900 s) is exact. One
process per executor is what makes a fault local: a timed-out worker is killed with its host (taskkill /T on
Windows) and a crashed one (BrokenProcessPool) is attributed to the one game it was playing; either way only
that slot is replaced. A shared pool can do neither: it cannot kill one worker, and a crash breaks every
pending future. Nothing is ever queued ahead of a worker, so evaluate.py's abort flag has nothing to skip
and is not used.

Sleep. Deadlines count awake time only. On Windows time.monotonic() includes time the machine spent suspended
(S3 or Modern Standby), so on waking every deadline would have passed and every running game would be killed
as hung. The parent therefore never blocks longer than POLL_S (5 s); each pass measures the time since the
previous one, and a gap more than SUSPEND_MARGIN_S (30 s) beyond the wait it asked for is taken as a
suspend: every running deadline moves back by the excess (one "suspend detected" line on stderr). A real hang
still times out after timeout_s of awake time. A parent busy for over 30 s in one pass (killing a worker) is
counted the same way, which only lengthens the running deadlines by that time. Results are unaffected.

Faults. A game that raises (the worker then closes its host, so the retry starts on a fresh one), times out
or crashes its worker is retried once; a second failure of the same game raises EngineError. Any error or
interrupt first caches every game that has already finished (including one that finished in the same instant
as the fatal failure, or while the parent was busy killing another worker), then kills the workers still
playing and propagates. So a rerun replays nothing that completed.

The cache is append-only and written by the parent only, one fsynced line per finished game. A torn last
line (a kill in the middle of a write) is skipped when the cache is loaded, and the next append starts on a
new line. One cache file must not be shared by two live engines.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, BrokenExecutor, ProcessPoolExecutor, wait
from pathlib import Path

from . import evaluate as ev
from .agent import play_game
from .gp import TreePolicy, individual_from_text, individual_text
from .power import SUSPEND_MARGIN_S, suspend_excess  # noqa: F401  (SUSPEND_MARGIN_S re-exported)
from .verify import build_verifier, verify_recording

# Bump whenever agent behaviour changes (agent, candidates, executor, features, gp, session, state, the
# simulator): it is part of every cache key, so results from older code are never reused.
CODE_VERSION = "gp4-v1"  # gp-4: placement, 5-tree texts, driving-only near cars (older texts play as before)
DEFAULT_TIMEOUT_S = 900.0  # seconds of awake wall clock per game (a suspend does not count)
KILL_TIMEOUT_S = 30.0
POLL_S = 5.0  # the parent's longest single wait, so a suspend is seen within one poll of waking
MP_CONTEXT = ev.MP_CONTEXT  # spawn, as evaluate.py


class EngineError(RuntimeError):
    """A game failed twice (raised, timed out or crashed its worker); the run cannot go on without it."""


def canonical_text(text: str) -> str:
    """The individual's canonical text (gp.individual_text): equal individuals share one cache key.

    ValueError for anything that is not an individual text.
    """
    if not isinstance(text, str):
        raise ValueError(f"an individual text is a str, got {type(text).__name__}")
    return individual_text(individual_from_text(text))


def cache_key(text: str, seed: int, cap_s: float) -> tuple[str, str, int, float]:
    """(CODE_VERSION, text, seed, cap_s) with text already canonical."""
    return (CODE_VERSION, text, int(seed), float(cap_s))


# ---------------------------------------------------------------------------------------------------------
# Worker side (module level: pickled by reference into spawned workers)
# ---------------------------------------------------------------------------------------------------------

def _play_job(text: str, seed: int, cap_s: float) -> dict:
    """Play one unrecorded game on this worker's long-lived host; returns its summary.

    An exception closes the host before it propagates (its reply stream may be out of step), so the next game
    on this worker, the retry included, starts on a fresh host.
    """
    try:
        result = play_game(ev._worker_host(), seed, TreePolicy(text), cap_s=cap_s, record=False)
        return result.summary()
    except BaseException:
        ev._close_host()
        raise


def _record_job(text: str, seed: int, cap_s: float, path: str, verify: bool) -> dict:
    """Play one recorded game, write the recording to path and, if asked, verify it.

    Returns the summary plus "verified" (None when not verifying). A rejected replay also gets
    <path stem>.verify.txt with the verifier's output, as evaluate.py; a verifier fault raises.
    """
    try:
        result = play_game(ev._worker_host(), seed, TreePolicy(text), cap_s=cap_s, record=True)
        out = Path(path)
        out.write_text(json.dumps(result.recording), encoding="utf-8")
        summary = result.summary()
        verified = None
        if verify:
            verified, output = verify_recording(out)
            if not verified:
                out.with_name(f"{out.stem}.verify.txt").write_text(output, encoding="utf-8")
        summary["verified"] = verified
        return summary
    except BaseException:
        ev._close_host()
        raise


# ---------------------------------------------------------------------------------------------------------
# Parent side
# ---------------------------------------------------------------------------------------------------------

def _make_worker():
    """One worker slot: a one-process spawn executor with evaluate.py's initializer (tests substitute this)."""
    return ProcessPoolExecutor(max_workers=1, mp_context=MP_CONTEXT, initializer=ev._init_worker,
                               initargs=(None,))


def _kill_worker(executor) -> None:
    """Stop a slot now: kill its process with its whole tree (the host), then drop the executor.

    On Windows a killed worker would leave a hung host running (only a host that reads its stdin sees the EOF),
    so taskkill /T takes the tree. An in-process substitute (no processes) is only shut down: its thread
    finishes its job and the result is ignored.
    """
    processes = list((getattr(executor, "_processes", None) or {}).values())
    for p in processes:
        if p.is_alive():
            if sys.platform == "win32":
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True,
                                   timeout=KILL_TIMEOUT_S)
                except (OSError, subprocess.SubprocessError):
                    pass
            try:
                p.kill()
            except (OSError, ValueError, AttributeError):
                pass
    executor.shutdown(wait=False, cancel_futures=True)
    for p in processes:
        p.join(KILL_TIMEOUT_S)


class Engine:
    """Plays (individual text, seed) jobs on `workers` long-lived worker processes, caching every result.

    Counters (cumulative over the engine's life): games_played (games finished on a worker, every recorded
    game included, so it measures compute), cache_hits (jobs answered from the cache, duplicates in a batch
    counted once), retries (failed attempts retried).
    """

    def __init__(self, workers: int = 10, cap_s: float = ev.DEFAULT_CAP_S, cache_path: str | Path | None = None,
                 *, timeout_s: float = DEFAULT_TIMEOUT_S, clock=None) -> None:
        ev._check_cap(cap_s)
        if not (isinstance(timeout_s, (int, float)) and math.isfinite(timeout_s) and timeout_s > 0):
            raise ValueError(f"timeout_s must be a finite number of seconds > 0, got {timeout_s!r}")
        self.workers = max(1, int(workers))
        self.cap_s = float(cap_s)
        self.timeout_s = float(timeout_s)
        self._clock = time.monotonic if clock is None else clock  # injectable for the suspend tests
        self.cache_path = Path(cache_path) if cache_path is not None else None
        self.games_played = self.cache_hits = self.retries = 0
        self._slots: list = []
        self._cache: dict[tuple, dict] = {}
        self._torn_tail = False
        os.environ["PYTHONHASHSEED"] = "0"  # inherited by the spawned workers
        if self.cache_path is not None:
            self._load_cache()

    # --- cache ---------------------------------------------------------------------------------------------

    def _load_cache(self) -> None:
        """Read every well-formed line; keep those of this CODE_VERSION. A torn line is skipped."""
        if not self.cache_path.exists():
            return
        data = self.cache_path.read_bytes()
        self._torn_tail = bool(data) and not data.endswith(b"\n")
        for raw in data.decode("utf-8", errors="replace").splitlines():
            try:
                line = json.loads(raw)
                key = (line["version"], line["text"], int(line["seed"]), float(line["cap_s"]))
                result = line["result"]
            except (ValueError, KeyError, TypeError):
                continue
            if key[0] == CODE_VERSION and isinstance(result, dict):
                self._cache[key] = result

    def _store(self, key: tuple, result: dict) -> dict:
        """Cache a finished game (in memory and, with a cache file, one fsynced JSONL line); returns a copy."""
        encoded = json.dumps(result)
        self._cache[key] = json.loads(encoded)
        if self.cache_path is not None:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps({"version": key[0], "text": key[1], "seed": key[2], "cap_s": key[3],
                               "result": result})
            with open(self.cache_path, "a", encoding="utf-8", newline="\n") as f:
                if self._torn_tail:  # never glue a new line onto a torn one
                    f.write("\n")
                    self._torn_tail = False
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
        return json.loads(encoded)

    def cached(self, text: str, seed: int) -> dict | None:
        """The cached result of (text, seed) at this engine's cap, or None; never plays."""
        result = self._cache.get(cache_key(canonical_text(text), seed, self.cap_s))
        return None if result is None else json.loads(json.dumps(result))

    # --- playing -------------------------------------------------------------------------------------------

    def play(self, jobs) -> list[dict]:
        """Results of (text, seed) jobs in job order: cached ones at once, the rest played once each.

        Every text is parsed before any game is played (ValueError for a bad one or a non-integer seed).
        """
        keys = []
        for job in jobs:
            text, seed = job
            if isinstance(seed, bool) or not isinstance(seed, int):
                raise ValueError(f"a seed is an int, got {seed!r}")
            keys.append(cache_key(canonical_text(text), seed, self.cap_s))
        todo: list[tuple] = []
        seen: set[tuple] = set()  # membership only; the order comes from `keys`
        for key in keys:
            if key in seen:
                continue
            seen.add(key)
            if key in self._cache:
                self.cache_hits += 1
            else:
                todo.append(key)
        if todo:
            def store(i: int, result: dict) -> None:
                self.games_played += 1
                self._store(todo[i], result)

            tasks = [(f"seed {k[2]}", _play_job, (k[1], k[2], k[3]), self.timeout_s) for k in todo]
            self._run(tasks, store)
        return [json.loads(json.dumps(self._cache[key])) for key in keys]

    def record(self, text: str, seed: int, path: str | Path, verify: bool = True) -> dict:
        """Play (text, seed) recorded, save the recording at path and verify it if asked; returns the summary.

        The summary carries "verified" (True/False, None without verify). The game is also cached; if the
        cache already held it with a different summary the game is not deterministic and EngineError is raised.
        The deadline is 2 x timeout_s when verifying (the verifier replays the whole game).
        """
        key = cache_key(canonical_text(text), seed, self.cap_s)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        verify = bool(verify)
        if verify:
            build_verifier()  # once, in the parent: no first-build race between workers
        out: list[dict] = []
        timeout = self.timeout_s * (2 if verify else 1)
        self._run([(f"recorded seed {seed}", _record_job, (key[1], key[2], key[3], str(path), verify), timeout)],
                  lambda i, result: out.append(result))
        summary = out[0]
        self.games_played += 1  # a recorded game is always played, cached or not
        game = {k: v for k, v in summary.items() if k != "verified"}
        if key in self._cache:
            if json.loads(json.dumps(game)) != self._cache[key]:
                raise EngineError(f"recorded game seed {seed} differs from its cached result: not deterministic "
                                  f"(or CODE_VERSION was not bumped after a behaviour change)")
        else:
            self._store(key, game)
        return summary

    def _slot(self, i: int):
        while len(self._slots) <= i:
            self._slots.append(None)
        if self._slots[i] is None:
            self._slots[i] = _make_worker()
        return self._slots[i]

    def _drop(self, i: int) -> None:
        executor, self._slots[i] = self._slots[i], None
        if executor is not None:
            _kill_worker(executor)

    def _run(self, tasks: list[tuple], on_result) -> None:
        """Run (label, fn, args, timeout_s) tasks on the slots, one at a time per slot; on_result(i, value).

        A failure (exception, timeout, crashed worker) puts the task back at the front of the queue once; the
        second failure raises EngineError. Any exception leaving this method first hands every game that has
        already finished successfully to on_result (fail() can raise while finished games are still waiting
        in `running`: later in the same done set, or done since wait() returned), then kills the workers still
        playing. Deadlines are suspend-aware (see the module docstring).
        """
        clock = self._clock
        pending = deque(range(len(tasks)))
        failures: dict[int, list[str]] = {}
        running: dict = {}  # future -> (slot, task index, deadline)
        free = deque(range(min(self.workers, len(tasks))))

        def fail(slot: int, i: int, why: str, replace: bool) -> None:
            if replace:
                self._drop(slot)
            free.append(slot)
            failures.setdefault(i, []).append(why)
            label = tasks[i][0]
            if len(failures[i]) >= 2:
                raise EngineError(f"game {label} failed twice:\n  1) {failures[i][0]}\n  2) {failures[i][1]}\n"
                                  f"individual:\n{tasks[i][2][0]}")
            self.retries += 1
            pending.appendleft(i)

        last, waited = clock(), 0.0  # the previous pass's end and the wait it asked for
        try:
            while pending or running:
                while pending and free:
                    slot, i = free.popleft(), pending.popleft()
                    _, fn, args, timeout = tasks[i]
                    try:
                        future = self._slot(slot).submit(fn, *args)
                    except BrokenExecutor:  # the idle worker died: replace it (no game was lost)
                        self._drop(slot)
                        future = self._slot(slot).submit(fn, *args)
                    running[future] = (slot, i, clock() + timeout)
                nearest = min(deadline for _, _, deadline in running.values())
                waited = min(POLL_S, max(0.0, nearest - clock()))
                done, _ = wait(list(running), timeout=waited, return_when=FIRST_COMPLETED)
                for future in sorted(done, key=lambda f: running[f][1]):  # task order: deterministic retries
                    slot, i, _ = running.pop(future)
                    try:
                        value = future.result()
                    except BrokenExecutor as e:
                        fail(slot, i, f"worker crashed: {type(e).__name__}: {e}", replace=True)
                    except Exception as e:  # the worker closed its host; the slot stays
                        fail(slot, i, f"{type(e).__name__}: {e}", replace=False)
                    else:
                        free.append(slot)
                        on_result(i, value)
                now = clock()
                excess = suspend_excess(now - last, waited)
                last = now
                if excess and running:
                    for future, (slot, i, deadline) in list(running.items()):
                        running[future] = (slot, i, deadline + excess)
                    print(f"suspend detected: {excess:.0f} s; deadlines extended", file=sys.stderr, flush=True)
                for future, (slot, i, deadline) in sorted(running.items(), key=lambda kv: kv[1][1]):
                    if deadline <= now and not future.done():
                        del running[future]
                        fail(slot, i, f"timed out after {tasks[i][3]:g} s wall clock", replace=True)
        except BaseException:
            try:
                for future, (slot, i, _) in sorted(running.items(), key=lambda kv: kv[1][1]):
                    if future.done() and not future.cancelled() and future.exception() is None:
                        del running[future]  # finished: its worker is idle and healthy, the slot stays
                        on_result(i, future.result())
            finally:
                for slot, _, _ in running.values():
                    self._drop(slot)
            raise

    # --- lifetime ------------------------------------------------------------------------------------------

    def close(self) -> None:
        """Shut the workers down (each closes its host at exit). The engine can be used again afterwards."""
        slots, self._slots = self._slots, []
        for executor in slots:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=True)

    def __enter__(self) -> "Engine":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


__all__ = ["CODE_VERSION", "DEFAULT_TIMEOUT_S", "POLL_S", "SUSPEND_MARGIN_S", "Engine", "EngineError", "cache_key",
           "canonical_text", "suspend_excess"]
