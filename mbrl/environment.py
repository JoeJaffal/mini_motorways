"""OriginalReference protocol adapter and filtered current-state encoding."""

from __future__ import annotations

import json
import math
import os
import queue
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
HOST_DLL = Path(os.environ.get("TRAFFIC_HOST_DLL", ROOT / "simulation/Headless/bin/Debug/net8.0/TrafficHost.dll"))
MAPS = ("LosAngeles", "Beijing", "Tokyo", "DarEsSalaam", "London")
GRID_FIELDS = (
    "terrain", "infrastructure", "connections", "buildingColors", "buildingKinds",
    "demand", "reservations", "pendingRemovals",
)
LEGACY_GRID_CHANNELS = 39
GRID_CHANNELS = 42
OBSERVATION_SCHEMA = "traffic-risk-v3"
OVERCROWDING_TIMER_SCALE = 50.0
SCALAR_FEATURES = 19
DEFAULT_TRIP_REWARD = 10.0
DEFAULT_FAILURE_PENALTY = 10.0
DEFAULT_UNANSWERED_PENALTY = 0.01
DEFAULT_MODIFICATION_PENALTY = 0.01
DEFAULT_OVERCROWDING_PENALTY = 0.05
DEFAULT_CLEAR_TRIP_BONUS = 0.1
DEFAULT_CONGESTION_FRACTION_PENALTY = 0.02
DEFAULT_CONGESTION_WAIT_THRESHOLD = 2.0


class ProtocolError(RuntimeError):
    pass


class Host:
    def __init__(self, dotnet: str = "dotnet", dll: Path = HOST_DLL, timeout: float = 30):
        self.dotnet, self.dll = dotnet, Path(dll)
        if not dll.is_file():
            raise FileNotFoundError(f"Build the host first: dotnet build simulation/Headless ({dll})")
        self.process = subprocess.Popen(
            [dotnet, str(dll)], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self.timeout = timeout
        self.lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        for line in self.process.stdout:
            self.lines.put(line)

    def call(self, **request: Any) -> dict:
        if self.process.poll() is not None:
            raise ProtocolError(f"Host exited with code {self.process.returncode}")
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        try:
            line = self.lines.get(timeout=self.timeout)
        except queue.Empty as exc:
            raise ProtocolError(f"Host response timed out for {request.get('command')}") from exc
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"Non-JSON host response: {line[:200]!r}") from exc
        if "error" in response:
            raise ProtocolError(str(response["error"]))
        return response

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                self.process.stdin.write('{"command":"quit"}\n')
                self.process.stdin.flush()
                self.process.wait(timeout=3)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait(timeout=3)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream:
                stream.close()

    def __enter__(self) -> "Host":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def visible_grid(observation: dict) -> np.ndarray:
    """Current-state terrain, links, access directions, motorways and traffic."""
    width, height = observation["width"], observation["height"]
    if (width, height) != (50, 30):
        raise ValueError(f"Unexpected canvas: {width}x{height}")
    channels = []
    scales = (2, 4, 255, 7, 2, 9, 9, 1)
    for field, scale in zip(GRID_FIELDS, scales):
        values = observation[field]
        if len(values) != width * height:
            raise ValueError(f"Invalid grid field {field}")
        channels.append(np.asarray(values, dtype=np.float32).reshape(height, width) / scale)
    grid = np.stack(channels)
    xmin = max(0, int(observation["playableXMin"]))
    xmax = min(width, int(observation["playableXMax"]))
    ymin = max(0, int(observation["playableYMin"]))
    ymax = min(height, int(observation["playableYMax"]))
    mask = np.zeros((height, width), dtype=np.float32)
    mask[ymin:ymax, xmin:xmax] = 1
    grid *= mask[None]
    # Empty color is -1; map it to zero after masking.
    grid[3] = np.maximum(grid[3], 0)
    rails = np.zeros((height, width), dtype=np.float32)
    for line in observation.get("railLines", []):
        for cell in line["cells"]:
            x, y = cell["x"], cell["y"]
            if 0 <= x < width and 0 <= y < height:
                rails[y, x] = 1
    vehicles = np.zeros((height, width), dtype=np.float32)
    waiting = np.zeros((height, width), dtype=np.float32)
    for vehicle in observation["vehicles"]:
        x, y = int(vehicle["x"]), int(vehicle["y"])
        if 0 <= x < width and 0 <= y < height:
            vehicles[y, x] += 1
            waiting[y, x] += float(vehicle["waiting"])
    vehicles = np.minimum(vehicles / 5, 1)
    waiting = np.minimum(waiting / 10, 1)
    link_bits = np.asarray(observation["connections"], dtype=np.uint16).reshape(height, width)
    explicit_links = np.stack([((link_bits >> direction) & 1).astype(np.float32) * mask
                               for direction in range(8)])
    house_access = np.zeros((8, height, width), dtype=np.float32)
    shop_access = np.zeros((8, height, width), dtype=np.float32)
    for building in observation["buildings"]:
        if building["isHouse"]:
            x, y = building["cell"]["x"], building["cell"]["y"]
            if 0 <= x < width and 0 <= y < height:
                house_access[building["drivewayDirection"], y, x] = 1
        else:
            entries = building["entrances"] or [building["entrance"]]
            directions = building["entranceDirections"] or [building["drivewayDirection"]]
            for entry, direction in zip(entries, directions):
                x, y = entry["x"], entry["y"]
                if 0 <= x < width and 0 <= y < height:
                    shop_access[direction, y, x] = 1
    motorway = np.zeros((3, height, width), dtype=np.float32)
    for edge in observation["motorways"]:
        if edge["pendingRemoval"]:
            continue
        a, b = edge["start"], edge["end"]
        for here, other in ((a, b), (b, a)):
            x, y = here["x"], here["y"]
            if 0 <= x < width and 0 <= y < height:
                motorway[0, y, x] = 1
                motorway[1, y, x] = other["x"] / width
                motorway[2, y, x] = other["y"] / height
    risk = np.zeros((3, height, width), dtype=np.float32)
    for building in observation["buildings"]:
        if building["isHouse"]:
            continue
        capacity = building.get("demandCapacity")
        timer = building.get("overcrowdedFor")
        if (capacity is None or not math.isfinite(capacity) or capacity <= 0
                or timer is None or not math.isfinite(timer) or timer < 0):
            raise ProtocolError("Risk inputs require positive demandCapacity and nonnegative overcrowdedFor")
        x, y = building["cell"]["x"], building["cell"]["y"]
        xmin_b, xmax_b = max(0, x), min(width, x + building["width"])
        ymin_b, ymax_b = max(0, y), min(height, y + building["height"])
        if xmax_b <= xmin_b or ymax_b <= ymin_b:
            continue
        risk[:, ymin_b:ymax_b, xmin_b:xmax_b] = np.asarray([
            capacity / 10.0, max(0, building["demand"]) / capacity,
            timer / OVERCROWDING_TIMER_SCALE], dtype=np.float32)[:, None, None]
    result = np.concatenate((grid, (rails * mask)[None], (vehicles * mask)[None], mask[None],
                             explicit_links, house_access * mask, shop_access * mask,
                             motorway * mask, (waiting * mask)[None], risk * mask), axis=0)
    assert result.shape[0] == GRID_CHANNELS
    return result


def visible_scalar(observation: dict) -> np.ndarray:
    """Current-state features only; excludes future spawn and RNG diagnostics."""
    inventory = list(observation["inventory"])
    if len(inventory) != 6:
        raise ValueError("Expected six inventory counts")
    demand = sum(b["demand"] for b in observation["buildings"] if not b["isHouse"])
    offer_features = []
    for offer in observation["upgradeChoices"][:2]:
        offer_features.extend(((offer["type"] + 1) / 6, offer["amount"] / 30,
                               offer["roads"] / 30))
    offer_features.extend([0.0] * (6 - len(offer_features)))
    return np.asarray([
        observation["time"] / 1800,
        observation["tripsCompleted"] / 100,
        len(observation["motorways"]) / 10,
        demand / 100,
        len(observation["buildings"]) / 100,
        len(observation["vehicles"]) / 200,
        *(min(100, max(0, v)) / 100 for v in inventory),
        len(observation["upgradeChoices"]) / 2,
        *offer_features,
    ], dtype=np.float32)


def material_use(observation: dict) -> int:
    """Provisional OriginalReference tie breaker: occupied infrastructure cells/items."""
    return sum(1 for item in observation["infrastructure"] if item) + len(observation["motorways"])


@dataclass(frozen=True)
class Transition:
    observation: dict
    accepted: bool
    terminated: bool
    truncated: bool
    reward: float
    components: dict[str, float]
    action_request: dict


def modification_cost(before: dict, after_action: dict) -> float:
    """Count actual infrastructure changes, with no credit for delayed refunds."""
    tiles = sum(a != b for a, b in zip(before["infrastructure"], after_action["infrastructure"]))
    links = sum((a ^ b).bit_count() for a, b in zip(before["connections"], after_action["connections"])) / 2
    motorways_before = {(m["id"], m["pendingRemoval"]) for m in before["motorways"]}
    motorways_after = {(m["id"], m["pendingRemoval"]) for m in after_action["motorways"]}
    driveway = sum(a["drivewayDirection"] != b["drivewayDirection"] for a, b in
                   zip(before["buildings"], after_action["buildings"]) if a["isHouse"])
    return float(tiles + links + len(motorways_before ^ motorways_after) + driveway)


def capacity_pressure(observation: dict, required: bool = True) -> float:
    """One unit at capacity, plus one for each request above capacity."""
    pressure = 0.0
    for building in observation["buildings"]:
        if building["isHouse"]:
            continue
        capacity = building.get("demandCapacity")
        if capacity is None or not math.isfinite(capacity) or capacity <= 0:
            if not required:
                continue
            raise ProtocolError("Overcrowding reward requires positive destination demandCapacity; "
                                "use a matching simulator host or --overcrowding-penalty 0")
        pressure += max(0.0, building["demand"] - capacity + 1)
    return pressure


def blocked_fraction(observation: dict, wait_threshold: float = DEFAULT_CONGESTION_WAIT_THRESHOLD) -> float:
    """Share of active cars blocked for at least the configured number of seconds."""
    active=[v for v in observation["vehicles"] if v.get("stage") not in (None,"Home","Parking")]
    return sum(v.get("waiting",0.0)>=wait_threshold for v in active)/len(active) if active else 0.0


class TrafficEnv:
    def __init__(self, host: Host, cap_seconds: float = 300, ticks_per_decision: int = 20,
                 alpha: float = 0.05, lam: float = DEFAULT_MODIFICATION_PENALTY, beta: float = 0.0,
                 failure_penalty: float = DEFAULT_FAILURE_PENALTY,
                 unanswered_penalty: float = DEFAULT_UNANSWERED_PENALTY,
                 overcrowding_penalty: float = DEFAULT_OVERCROWDING_PENALTY,
                 trip_reward: float = DEFAULT_TRIP_REWARD,
                 clear_trip_bonus: float = DEFAULT_CLEAR_TRIP_BONUS,
                 congestion_fraction_penalty: float = DEFAULT_CONGESTION_FRACTION_PENALTY,
                 congestion_wait_threshold: float = DEFAULT_CONGESTION_WAIT_THRESHOLD):
        if any(not math.isfinite(v) or v < 0 for v in (failure_penalty, unanswered_penalty, overcrowding_penalty,
                                                     clear_trip_bonus,congestion_fraction_penalty)):
            raise ValueError("Reward bonus and penalty coefficients must be finite and nonnegative")
        if not math.isfinite(congestion_wait_threshold) or congestion_wait_threshold<=0:
            raise ValueError("Congestion wait threshold must be finite and positive")
        self.host = host
        self.cap_seconds = cap_seconds
        self.ticks_per_decision = ticks_per_decision
        self.alpha, self.lam, self.beta = alpha, lam, beta
        self.failure_penalty, self.unanswered_penalty = failure_penalty, unanswered_penalty
        self.overcrowding_penalty = overcrowding_penalty
        if not math.isfinite(trip_reward) or trip_reward <= 0:
            raise ValueError("Trip reward must be finite and positive")
        self.trip_reward = trip_reward
        self.clear_trip_bonus=clear_trip_bonus
        self.congestion_fraction_penalty=congestion_fraction_penalty
        self.congestion_wait_threshold=congestion_wait_threshold
        self.observation: dict | None = None
        self.done = True
        self.scenario = ""
        self.seed = 0

    def reset(self, scenario: str, seed: int) -> dict:
        if scenario not in MAPS:
            raise ValueError(f"Unsupported map: {scenario}")
        response = self.host.call(command="reset", version="OriginalReference", scenario=scenario,
                                  seed=seed, variation="SameMap")
        obs = response["observation"]
        if obs["version"] != "OriginalReference" or obs["unlimitedConstruction"]:
            raise ProtocolError("Unexpected game rules")
        required = ("tripsDispatched", "waitingSeconds", "congestionSeconds")
        missing = [field for field in required if field not in obs]
        if missing:
            raise ProtocolError(
                f"Incompatible simulator host: missing observation fields {', '.join(missing)}. "
                "Rebuild simulation/Headless with the workspace .NET SDK for new runs, "
                "or pass --host-dll with the archived host for a historical evaluation. "
                "The host selection also honors TRAFFIC_HOST_DLL.")
        if self.overcrowding_penalty:
            capacity_pressure(obs)  # Check host support before collecting an episode.
        self.observation = obs
        self.done = False
        self.scenario, self.seed = scenario, seed
        return obs

    def step(self, request: dict) -> Transition:
        if self.done or self.observation is None:
            raise RuntimeError("Reset before stepping")
        command = request.get("command")
        if command not in {"wait", "draw", "build", "connect", "driveway", "motorway", "editMotorway", "removeMotorway", "upgrade"}:
            raise ValueError(f"Action unavailable to policy: {command}")
        before = self.observation
        accepted = True
        after_action = before
        spending_delta = 0
        if command != "wait":
            result = self.host.call(**request)
            accepted = bool(result["accepted"])
            after_action = result["observation"]
            spending_delta = result["spendingDelta"]
        remaining = max(0, round((self.cap_seconds - before["time"]) / 0.05))
        result = self.host.call(command="step", ticks=min(self.ticks_per_decision, remaining))
        after = result["observation"]
        terminated = bool(result["terminated"])
        truncated = bool(result["truncated"]) or (after["time"] >= self.cap_seconds - 1e-8 and not terminated)
        self.done = terminated or truncated
        trips = after["tripsCompleted"] - before["tripsCompleted"]
        waiting = after.get("waitingSeconds", after.get("meanWaiting", 0.0)) - before.get("waitingSeconds", before.get("meanWaiting", 0.0))
        congestion = after.get("congestionSeconds", 0.0) - before.get("congestionSeconds", 0.0)
        cost = modification_cost(before, after_action)
        # Demand already includes reserved requests: assignment is not delivery.
        # Use actual elapsed time, including shortened final decision intervals.
        elapsed = max(0.0, after["time"] - before["time"])
        unanswered = sum(max(0, b["demand"]) for b in after["buildings"] if not b["isHouse"]) * elapsed
        failure = float(bool(after.get("failed", False)) and not before.get("failed", False))
        pressure_seconds = capacity_pressure(after, required=bool(self.overcrowding_penalty)) * elapsed
        fraction=blocked_fraction(after,self.congestion_wait_threshold)
        clear_trips=trips*(1-fraction)
        fraction_seconds=fraction*elapsed
        reward = (self.trip_reward * trips - self.alpha * waiting - self.lam * cost - self.beta * congestion
                  - self.failure_penalty * failure - self.unanswered_penalty * unanswered
                  - self.overcrowding_penalty * pressure_seconds
                  + self.clear_trip_bonus * clear_trips - self.congestion_fraction_penalty * fraction_seconds)
        components = {"trips": float(trips), "waitingSeconds": float(waiting),
                      "modificationCost": cost, "congestionSeconds": float(congestion),
                      "spendingDelta": float(spending_delta), "failure": failure,
                      "unansweredRequestSeconds": float(unanswered),
                      "capacityPressureSeconds": float(pressure_seconds),
                      "blockedFraction":float(fraction),"clearTripUnits":float(clear_trips),
                      "congestionFractionSeconds":float(fraction_seconds)}
        self.observation = after
        return Transition(after, accepted, terminated, truncated, reward, components, request)


class ReplayBranch:
    """Independent host with checked reset-and-replay, then counterfactual futures."""

    def __init__(self, host: Host, live: TrafficEnv):
        self.env = TrafficEnv(host, live.cap_seconds, live.ticks_per_decision, live.alpha, live.lam, live.beta,
                              live.failure_penalty, live.unanswered_penalty, live.overcrowding_penalty, live.trip_reward,
                              live.clear_trip_bonus,live.congestion_fraction_penalty,live.congestion_wait_threshold)
        self.live = live

    def start(self, expected: dict) -> None:
        pass

    def restore(self, history: list[dict], expected: dict) -> None:
        observed = self.env.reset(self.live.scenario, self.live.seed)
        for action in history:
            observed = self.env.step(action).observation
        if observed != expected:
            raise ProtocolError("Reset-and-replay diverged from the live episode")

    def transition(self, action: dict, future_seed: int) -> Transition:
        self.env.host.call(command="forkFuture", seed=future_seed)
        return self.env.step(action)

    def commit(self, action: dict, expected: dict) -> None:
        pass


class SnapshotBranch:
    """Keep an exact live-state snapshot; each MCTS simulation restores it in O(state size)."""

    def __init__(self, host: Host, live: TrafficEnv):
        self.env = TrafficEnv(host, live.cap_seconds, live.ticks_per_decision, live.alpha, live.lam, live.beta,
                              live.failure_penalty, live.unanswered_penalty, live.overcrowding_penalty, live.trip_reward,
                              live.clear_trip_bonus,live.congestion_fraction_penalty,live.congestion_wait_threshold)
        self.live = live
        self.snapshot_id = 1
        self.root_observation: dict | None = None

    def start(self, expected: dict) -> None:
        observed = self.env.reset(self.live.scenario, self.live.seed)
        if observed != expected:
            raise ProtocolError("Snapshot host reset differs from live episode")
        self.env.host.call(command="saveSnapshot", id=self.snapshot_id)
        self.root_observation = observed

    def restore(self, history: list[dict], expected: dict) -> None:
        observed = self.env.host.call(command="loadSnapshot", id=self.snapshot_id)["observation"]
        self.env.observation = observed
        self.env.done = bool(observed["failed"] or observed["scenarioRejected"])
        if observed != expected:
            raise ProtocolError("Snapshot differs from live episode")

    def transition(self, action: dict, future_seed: int) -> Transition:
        self.env.host.call(command="forkFuture", seed=future_seed)
        return self.env.step(action)

    def commit(self, action: dict, expected: dict) -> None:
        self.restore([], self.root_observation)
        observed = self.env.step(action).observation
        if observed != expected:
            raise ProtocolError("Snapshot host diverged after live action")
        self.env.host.call(command="saveSnapshot", id=self.snapshot_id)
        self.root_observation = observed
