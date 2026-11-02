"""Keep the machine awake while a long run plays (sleep-safe runs, Phase 2 Task 4 addendum).

    with keep_awake():
        ...  # Windows will not idle-sleep (S3 or Modern Standby) until the block exits

On Windows this asks kernel32.SetThreadExecutionState for ES_CONTINUOUS | ES_SYSTEM_REQUIRED |
ES_AWAYMODE_REQUIRED (falling back to ES_CONTINUOUS | ES_SYSTEM_REQUIRED if away mode is refused) and
restores ES_CONTINUOUS on exit, exceptions included. The request belongs to the calling thread, so enter it
on the thread that runs the loop. Nesting is allowed: only the outermost block sets and restores. Anywhere
else it is a no-op. A refused or failing call prints one line to stderr and never raises: keeping awake is
a convenience, and the engine's suspend-aware deadlines are what make a sleep harmless.

It does not stop a sleep the user asks for (lid, power button, Start > Sleep) or a critical-battery one.
"""
from __future__ import annotations

import ctypes
import sys
import threading
from contextlib import contextmanager

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040
KEEP_AWAKE = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
FALLBACK = ES_CONTINUOUS | ES_SYSTEM_REQUIRED

SUSPEND_MARGIN_S = 30.0  # a wait this much longer than it asked for is a suspend

_depth = threading.local()


def suspend_excess(gap: float, expected: float, margin: float | None = None) -> float:
    """Seconds of a wait to treat as a suspend: gap - expected when that exceeds margin, else 0.

    gap is the clock time since the previous check, expected the longest the wait in between could block.
    On Windows time.monotonic() keeps counting while the machine sleeps, so deadlines built on it must be
    pushed back by this excess (engine.py game deadlines, host.py reply timeouts).
    """
    margin = SUSPEND_MARGIN_S if margin is None else margin
    excess = gap - expected
    return float(excess) if excess > margin else 0.0


def _api():
    """kernel32.SetThreadExecutionState (flags -> previous state, 0 on failure), or None off Windows."""
    if sys.platform != "win32":
        return None
    try:
        fn = ctypes.WinDLL("kernel32").SetThreadExecutionState
        fn.argtypes = [ctypes.c_uint32]
        fn.restype = ctypes.c_uint32
        return fn
    except (OSError, AttributeError):
        return None


def _call(fn, flags: int) -> bool:
    try:
        return bool(fn(flags))
    except Exception:  # a broken ctypes binding must never stop a run
        return False


@contextmanager
def keep_awake():
    """Hold a keep-awake request for the block; yields True if Windows accepted it, else False."""
    depth = getattr(_depth, "n", 0)
    _depth.n = depth + 1
    try:
        if depth:  # an outer block already holds the request (it is not a counter in Windows)
            yield getattr(_depth, "held", False)
            return
        fn = _api()
        held = False
        if fn is not None:
            held = _call(fn, KEEP_AWAKE) or _call(fn, FALLBACK)
            if not held:
                print("keep-awake: SetThreadExecutionState refused; the machine may sleep (runs survive it)",
                      file=sys.stderr, flush=True)
        _depth.held = held
        try:
            yield held
        finally:
            if fn is not None:
                _call(fn, ES_CONTINUOUS)
            _depth.held = False
    finally:
        _depth.n = depth


__all__ = ["keep_awake", "suspend_excess", "SUSPEND_MARGIN_S", "KEEP_AWAKE", "ES_CONTINUOUS", "ES_SYSTEM_REQUIRED", "ES_AWAYMODE_REQUIRED"]
