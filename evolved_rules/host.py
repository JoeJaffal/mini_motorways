"""Client for the C# headless simulator (TrafficHost): one JSON line in, one JSON line out."""
from __future__ import annotations

import collections
import json
import os
import queue
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STDERR_LINES = 20

# The five city maps, spelled exactly as CityCatalog.Maps names them (simulation/Assets/Simulation/CityCatalog.cs).
# The host would also take lab scenarios (ReferenceLab, EmptyLab), any letter case and numbers, but the agent may
# not play labs, and AiReplaySession only replays these exact names.
CITY_SCENARIOS = ("LosAngeles", "Beijing", "Tokyo", "DarEsSalaam", "London")


def check_scenario(scenario) -> str:
    """Return scenario if it is one of CITY_SCENARIOS (exact match); ValueError otherwise."""
    if not isinstance(scenario, str) or scenario not in CITY_SCENARIOS:
        raise ValueError(f"scenario must be one of {', '.join(CITY_SCENARIOS)} (exact case), got {scenario!r}")
    return scenario


class HostError(RuntimeError):
    """The host failed, timed out, exited, or replied with an error."""


class ScenarioRejected(HostError):
    """The simulator refused to generate the requested scenario (a `truncated` reset)."""


def default_host_dll() -> Path:
    """Release TrafficHost.dll, or the path in EVOLVED_RULES_HOST_DLL when that is set and non-empty."""
    override = os.environ.get("EVOLVED_RULES_HOST_DLL")
    if override:
        return Path(override)
    return ROOT /"simulation" / "Headless" / "bin" / "Release" / "net8.0" / "TrafficHost.dll"


class Host:
    def __init__(self, dll: Path | None = None, timeout: float = 30.0):
        self._start(["dotnet", str(dll or default_host_dll())], timeout)

    def _start(self, argv: list[str], timeout: float) -> None:
        self._timeout = timeout
        self._dead = False
        self._stderr_tail: collections.deque[str] = collections.deque(maxlen=STDERR_LINES)
        self._replies: queue.Queue[str | None] = queue.Queue()
        self._proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
        self._stdout_thread = threading.Thread(target=self._pump_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._pump_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _pump_stdout(self) -> None:
        for line in self._proc.stdout:
            self._replies.put(line)
        self._replies.put(None)  # EOF: the host exited

    def _pump_stderr(self) -> None:
        # Always drained, so a chatty host can never fill the pipe and block.
        for line in self._proc.stderr:
            self._stderr_tail.append(line.rstrip())

    def _stderr_text(self) -> str:
        self._stderr_thread.join(timeout=0.2 if self._proc.poll() is not None else 0)
        return "\n".join(self._stderr_tail)

    def _fail(self, what: str) -> HostError:
        """Kill the host (its reply stream can no longer be trusted) and build the error."""
        self._dead = True
        if self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait()
        stderr = self._stderr_text()
        return HostError(what + (f"\nhost stderr (last lines):\n{stderr}" if stderr else ""))

    def call(self, **request) -> dict:
        if self._dead or self._proc.poll() is not None:
            raise self._fail("host is not running")
        try:
            self._proc.stdin.write(json.dumps(request) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as e:
            raise self._fail(f"could not send {request.get('command')!r} to the host: {e}") from e
        try:
            line = self._replies.get(timeout=self._timeout)
        except queue.Empty:
            raise self._fail(f"no reply to {request.get('command')!r} within {self._timeout}s") from None
        if line is None:
            raise self._fail(f"host exited while handling {request.get('command')!r}")
        try:
            reply = json.loads(line)
        except json.JSONDecodeError as e:
            raise self._fail(f"unparseable host reply {line[:200]!r}: {e}") from e
        if "error" in reply:
            stderr = self._stderr_text()
            raise HostError(f"host error for {request.get('command')!r}: {reply['error']}"
                            + (f"\nhost stderr (last lines):\n{stderr}" if stderr else ""))
        return reply

    def reset(self, seed: int, scenario: str = "LosAngeles") -> dict:
        check_scenario(scenario)  # ValueError before anything is sent
        reply = self.call(command="reset", version="OriginalReference", scenario=scenario, seed=seed)
        if reply.get("truncated"):
            raise ScenarioRejected(f"simulator rejected scenario {scenario!r} seed {seed}: {reply.get('message')}")
        obs = reply["observation"]
        if obs["version"] != "OriginalReference" or obs["unlimitedConstruction"]:
            raise HostError(f"unexpected rules after reset: version={obs['version']!r}, "
                            f"unlimitedConstruction={obs['unlimitedConstruction']!r}")
        return reply

    def close(self) -> None:
        proc = getattr(self, "_proc", None)
        if proc is None:
            return
        if proc.poll() is None:
            try:
                proc.stdin.write('{"command":"quit"}\n')
                proc.stdin.flush()
                proc.wait(timeout=5)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                proc.kill()
                proc.wait()
        self._dead = True
        try:
            proc.stdin.close()
        except (OSError, ValueError):
            pass  # Windows may already have invalidated the pipe once the host exited.
        # stdout/stderr are left to their reader threads, which end at EOF; closing them here
        # could block on a thread still inside a read.

    def __enter__(self) -> "Host":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
