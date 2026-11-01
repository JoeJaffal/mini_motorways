"""A host game wrapped for the agent: every command is followed by a 20-tick step, and logged as an AiReplayAction.

The recording schema is defined by simulation/Assets/Simulation/AiReplay.cs (AiReplayRecording,
AiReplayAction); field names here are the C# field names, because the Unity verifier's JsonUtility
is case-sensitive.
"""
from __future__ import annotations

import functools
import json
import subprocess
from pathlib import Path

from .features import GameMemory
from .host import ROOT, Host, ScenarioRejected, check_scenario
from .state import CityState, parse_observation

TICKS = 20  # AiReplaySession rejects any action whose ticks != 20
DEFAULT_SCENARIO = "LosAngeles"
POLICY_SCHEMA = "evolved-rules-v1"


@functools.lru_cache(maxsize=1)
def _simulator_commit() -> str:
    """Short git hash of the repository the simulator comes from, or "" when git cannot say."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def raise_if_rejected(reply: dict, what: str, seed: int, scenario: str) -> None:
    """ScenarioRejected if a host reply after reset says truncated: the simulator rejected the scenario mid-game.

    The game must not be scored, and the loop must not go on: a rejected world no longer advances time, so a
    game loop waiting for the cap would wait forever.
    """
    if reply.get("truncated"):
        raise ScenarioRejected(f"simulator rejected scenario {scenario!r} seed {seed} during the game "
                               f"(truncated reply to {what!r}): {reply.get('message')}")


def _replayable(request) -> bool:
    """The only requests the agent may send (PLAN decision 6): draw, build with tool exactly "Remove", upgrade.

    The host also runs other commands, and treats tool names case-insensitively with a missing tool as Road;
    AiReplaySession rejects or replays those differently, so such a game would not verify.
    """
    if not isinstance(request, dict):
        return False
    command = request.get("command")
    return command in ("draw", "upgrade") or (command == "build" and request.get("tool") == "Remove")


class Recorder:
    """Collects one AiReplayAction per command + 20-tick pair and builds the AiReplayRecording."""

    def __init__(self, seed: int, scenario: str = DEFAULT_SCENARIO):
        self.seed = seed
        self.scenario = check_scenario(scenario)
        self.actions: list[dict] = []

    def log(self, request: dict | None, accepted: bool, obs: dict) -> None:
        """Append one action. `request` None means a wait (the replay has no `step` command)."""
        req = request or {}
        self.actions.append({
            "command": "wait" if request is None else req["command"],
            "tool": req.get("tool", ""),
            "x": int(req.get("x", 0)),
            "y": int(req.get("y", 0)),
            "toX": int(req.get("toX", 0)),
            "toY": int(req.get("toY", 0)),
            "id": int(req.get("id", 0)),
            "choice": int(req.get("choice", 0)),
            "ticks": TICKS,
            "accepted": bool(accepted),
            "afterTrips": int(obs["tripsCompleted"]),
            "afterTime": float(obs["time"]),
        })

    def recording(self, final_obs: dict, source: str) -> dict:
        # AiReplaySession validates schemaVersion, version, scenario, variation, score, duration and the
        # actions. The remaining C# fields (simulatorCommit, policySteps, episode, ranking) are metadata
        # it never reads; they are filled with plain values so the JSON carries every field of the class.
        return {
            "schemaVersion": 1,
            "version": "OriginalReference",
            "scenario": self.scenario,
            "variation": "SameMap",
            "seed": self.seed,
            "score": int(final_obs["tripsCompleted"]),
            "duration": float(final_obs["time"]),
            "terminated": bool(final_obs["failed"]),
            "truncated": False,
            "actions": [dict(a) for a in self.actions],
            "source": source,
            "policySchema": POLICY_SCHEMA,
            "policySteps": len(self.actions),
            "episode": 0,
            "simulatorCommit": _simulator_commit(),
            "ranking": "",
        }

    def save(self, path, final_obs: dict, source: str) -> None:
        Path(path).write_text(json.dumps(self.recording(final_obs, source)), encoding="utf-8")


def _road_stock(state: CityState) -> int:
    return state.inventory[0] if state.inventory else 0


class GameSession:
    """One game on a host: reset, then command() / wait(), each followed by a 20-tick step.

    Besides the counters, a session owns the game's GameMemory (features.py): a fresh one on every reset, fed
    every observation and the count of accepted offers, so no feature state can leak from one game into the
    next. tiles_built counts road tiles spent by draw commands: the road-stock drop over each draw and its step
    (the agent never removes roads, so no refund lands in that step; offers are separate commands).
    """

    def __init__(self, host: Host, seed: int, cap_s: float = 3600.0, record: bool = True, *,
                 scenario: str = DEFAULT_SCENARIO):
        self.host = host
        self.seed = seed
        self.cap_s = cap_s
        self.scenario = check_scenario(scenario)  # ValueError unless one of the five city maps, exact case
        self._record = record
        self.state: CityState | None = None
        self.raw: dict | None = None
        self._clear()

    def _clear(self) -> None:
        self.commands = 0
        self.rejected = 0
        self.action_counts: dict[str, int] = {}
        self.wait_sum = 0.0
        self.wait_n = 0
        self.max_wait = 0.0
        self.tiles_built = 0
        self.terminated = False
        self.memory = GameMemory()
        self.recorder: Recorder | None = Recorder(self.seed, self.scenario) if self._record else None

    @property
    def done(self) -> bool:
        return self.terminated or (self.state is not None and self.state.time >= self.cap_s)

    def reset(self) -> CityState:
        """Start a fresh game (counters and recording restart). Nothing is logged."""
        reply = self.host.reset(self.seed, self.scenario)
        self._clear()
        self.raw = reply["observation"]
        self.state = parse_observation(self.raw)
        self.terminated = bool(reply["terminated"])
        self.memory.observe(self.state)
        return self.state

    def command(self, request: dict) -> tuple[bool, CityState]:
        """Send one command, then step 20 ticks. Returns (accepted by the command, the state after the step).

        Raises ValueError, sending nothing, unless the request is a draw, a build with tool "Remove" or an upgrade.
        """
        if not _replayable(request):
            raise ValueError(f"not a replayable agent command (draw, build Remove, upgrade): {request!r}")
        return self._act(request)

    def wait(self) -> CityState:
        """Step 20 ticks with no command; logged as `wait`."""
        return self._act(None)[1]

    def _act(self, request: dict | None) -> tuple[bool, CityState]:
        if self.state is None:
            raise RuntimeError("call reset() before sending commands")
        if self.done:
            raise RuntimeError("the game is over (terminated or at the time cap)")
        if request is None:
            accepted = True
        else:
            reply = self.host.call(**request)
            raise_if_rejected(reply, request.get("command"), self.seed, self.scenario)
            accepted = bool(reply["accepted"])
        step = self.host.call(command="step", ticks=TICKS)
        raise_if_rejected(step, "step", self.seed, self.scenario)
        before = self.state
        self.raw = step["observation"]
        self.state = parse_observation(self.raw)
        self.memory.observe(self.state)
        if request is not None and request["command"] == "draw":
            self.tiles_built += max(0, _road_stock(before) - _road_stock(self.state))
        elif request is not None and request["command"] == "upgrade" and accepted:
            self.memory.offers_taken += 1
        self.terminated = bool(step["terminated"])
        self.commands += 1
        if not accepted:
            self.rejected += 1
        key = "wait" if request is None else (request.get("tool") or request["command"])
        self.action_counts[key] = self.action_counts.get(key, 0) + 1
        for w in self.state.vehicles_waiting:
            self.wait_sum += w
            self.wait_n += 1
            self.max_wait = max(self.max_wait, w)
        if self.recorder is not None:
            self.recorder.log(request, accepted, self.raw)
        return accepted, self.state
