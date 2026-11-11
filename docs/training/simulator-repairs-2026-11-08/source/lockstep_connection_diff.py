"""Lockstep replay of reward-fixture-v4 on two variant DLLs; log every change in the set of differing cells."""
import json, pathlib, subprocess, sys

REPO = pathlib.Path(__file__).resolve().parents[4]
S = REPO / "tmp" / "variants"  # built by isolate_reward_v4_drift.py; usage: lockstep_connection_diff.py base spawnonly_off


class Host:
    def __init__(self, dll):
        self.p = subprocess.Popen(["dotnet", str(dll)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def call(self, **r):
        self.p.stdin.write(json.dumps(r) + "\n"); self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())


rec = json.loads((REPO / "docs/training/event-parity-2026-11-08/reward-fixture-v4.json").read_text())
hosts = [Host(S / n / "simulation/Headless/bin/Debug/net8.0/TrafficHost.dll") for n in sys.argv[1:3]]
reset = dict(command="reset", version=rec["version"], scenario=rec["scenario"], seed=rec["seed"], variation=rec["variation"])
for h in hosts: h.call(**reset)
last = None
for i, ev in enumerate(rec["actions"]):
    req = {k: v for k, v in ev.items() if k in ["command", "tool", "x", "y", "toX", "toY", "id", "choice"]}
    if req["command"] != "wait":
        for h in hosts: h.call(**req)
    obs = [h.call(command="step", ticks=20)["observation"] for h in hosts]
    w = obs[0]["width"]
    diff = tuple((j % w, j // w, obs[0]["connections"][j], obs[1]["connections"][j])
                 for j in range(len(obs[0]["connections"])) if obs[0]["connections"][j] != obs[1]["connections"][j])
    if diff != last:
        print("t", obs[0]["time"], "connection differences", diff); last = diff
    if obs[0]["failed"] or obs[1]["failed"] or i == len(rec["actions"]) - 1:
        trips = [o["tripsCompleted"] for o in obs]
        red = [[(b["id"], b["demand"], round(b["overcrowdedFor"], 1)) for b in o["buildings"] if not b["isHouse"]] for o in obs]
        print("t", obs[0]["time"], "trips", trips, "failed", [o["failed"] for o in obs], "destinations (id,demand,overcrowdedFor)", red)
        break
for h in hosts: h.p.kill()
