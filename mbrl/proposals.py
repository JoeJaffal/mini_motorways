"""Observed-state cooldowns and simulator-checked candidate selection."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json

from actions import DIRS, MAX_CANDIDATES, RAW_CANDIDATES, candidates, _line_cells


@dataclass(frozen=True)
class Cooldowns:
    driveway: float = 20.0
    motorway: float = 30.0
    construction: float = 10.0
    reversal_window: float = 60.0


def key(request: dict) -> str:
    value = dict(request)
    if value["command"] in ("connect", "motorway"):
        a, b = (value["x"], value["y"]), (value["toX"], value["toY"])
        a, b = sorted((a, b))
        value.update(x=a[0], y=a[1], toX=b[0], toY=b[1])
    return json.dumps(value, sort_keys=True)


class ActionGuard:
    def __init__(self, cooldowns: Cooldowns = Cooldowns()):
        self.config = cooldowns
        self.driveways = {}
        self.motorway_ends = {}
        self.tiles = {}
        self.rejected = {}
        self.reversals = 0
        self.driveway_changes = 0
        self.motorway_changes = 0
        self.motorway_reversals = 0
        self.motorway_history = {}

    def clone(self):
        return copy.deepcopy(self)

    def allows(self, request: dict, obs: dict) -> bool:
        now = obs["time"]
        command = request["command"]
        if self.rejected.get(key(request), -1) > now:
            return False
        house = None
        if command == "driveway":
            house = next((b for b in obs["buildings"] if b["id"] == request["id"]), None)
        elif command == "draw":
            house = next((b for b in obs["buildings"] if b["isHouse"] and
                          (b["cell"]["x"], b["cell"]["y"]) == (request["x"], request["y"])), None)
            if house:
                line = _line_cells((request["x"],request["y"]),(request["toX"],request["toY"]))
                delta = (line[1][0]-line[0][0],line[1][1]-line[0][1]) if len(line)>1 else (0,0)
                if delta in DIRS and DIRS.index(delta) == house["drivewayDirection"]:
                    house = None
        if house and house["id"] in self.driveways:
            last = self.driveways[house["id"]]
            dx, dy = DIRS[house["drivewayDirection"]]
            x, y = house["cell"]["x"] + dx, house["cell"]["y"] + dy
            blocked = (not (0 <= x < 50 and 0 <= y < 30) or
                       obs["terrain"][y * 50 + x] != 0 or obs["pendingRemovals"][y * 50 + x])
            if not blocked and now - last["time"] < self.config.driveway:
                return False
            delta=(request["toX"]-request["x"],request["toY"]-request["y"])
            if command=="draw":
                line=_line_cells((request["x"],request["y"]),(request["toX"],request["toY"]))
                delta=(line[1][0]-line[0][0],line[1][1]-line[0][1]) if len(line)>1 else (0,0)
            direction=DIRS.index(delta) if delta in DIRS else -1
            if not blocked and direction==last["from"] and now-last["time"]<self.config.reversal_window:
                return False
        if command in ("motorway", "editMotorway", "removeMotorway"):
            endpoints = []
            old = next((m for m in obs["motorways"] if m["id"] == request.get("id")), None) if command != "motorway" else None
            if old:
                endpoints += [(old[e]["x"], old[e]["y"]) for e in ("start", "end")]
            if command != "removeMotorway":
                endpoints += [(request["x"], request["y"]), (request["toX"], request["toY"])]
            if any(self.motorway_ends.get(cell, -1) > now for cell in endpoints):
                return False
        if command == "build":
            cell = (request["x"], request["y"])
            previous = self.tiles.get(cell)
            if previous and now - previous[0] < self.config.construction:
                # Block only a removal/rebuild reversal; allow upgrades of existing roads.
                if (request["tool"] == "Remove") != previous[1]:
                    return False
        return True

    def record(self, before: dict, after: dict, request: dict, accepted: bool = True) -> None:
        now = before["time"]
        if not accepted:
            self.rejected[key(request)] = now + 30
        old_buildings = {b["id"]: b for b in before["buildings"]}
        for building in after["buildings"]:
            old = old_buildings.get(building["id"])
            if old and building["isHouse"] and old["drivewayDirection"] != building["drivewayDirection"]:
                previous = self.driveways.get(building["id"])
                if previous and previous["from"] == building["drivewayDirection"] and now - previous["time"] <= self.config.reversal_window:
                    self.reversals += 1
                self.driveways[building["id"]] = {"time": now, "from": old["drivewayDirection"], "to": building["drivewayDirection"]}
                self.driveway_changes += 1
        old_motorways = {m["id"]: m for m in before["motorways"]}
        new_motorways = {m["id"]: m for m in after["motorways"]}
        changed = [m for ident, m in old_motorways.items() if new_motorways.get(ident) != m]
        changed += [m for ident, m in new_motorways.items() if old_motorways.get(ident) != m]
        def geometry(m):
            return tuple(sorted((m[e]["x"],m[e]["y"]) for e in ("start","end")))
        old_active={geometry(m) for m in before["motorways"] if not m["pendingRemoval"]}
        new_active={geometry(m) for m in after["motorways"] if not m["pendingRemoval"]}
        for shape, active in [(s,False) for s in old_active-new_active]+[(s,True) for s in new_active-old_active]:
            previous=self.motorway_history.get(shape)
            if previous and previous[1]!=active and now-previous[0]<=self.config.reversal_window:
                self.motorway_reversals+=1
            self.motorway_history[shape]=(now,active)
        if changed:
            self.motorway_changes += 1
            for motorway in changed:
                for end in ("start", "end"):
                    cell = (motorway[end]["x"], motorway[end]["y"])
                    self.motorway_ends[cell] = now + self.config.motorway
        for index, (a, b) in enumerate(zip(before["infrastructure"], after["infrastructure"])):
            if a != b:
                self.tiles[(index % 50, index // 50)] = (now, b == 0)
        if request["command"] == "build" and request.get("tool") == "Remove" and accepted:
            self.tiles[(request["x"], request["y"])] = (now, True)


def proposals(obs: dict, host, guard: ActionGuard, limit: int = MAX_CANDIDATES):
    items = []
    seen = set()
    for candidate in candidates(obs, limit=RAW_CANDIDATES):
        identity = key(candidate.request)
        if identity not in seen and guard.allows(candidate.request, obs):
            items.append(candidate)
            seen.add(identity)
    checks = host.call(command="validateActions", actions=[c.request for c in items],limit=limit)["validation"]
    legal = [candidate for candidate, check in zip(items, checks)
             if check["accepted"] and check["changed"]]
    if not legal or legal[0].request["command"] != "wait":
        raise RuntimeError("The legal candidate set must retain wait")
    return legal[:limit]
