"""Regression checks: viewer isolation, branch events, replay checks and controls."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import random
import tempfile
import threading
import time
from unittest.mock import patch
from urllib.request import Request, urlopen

import torch
from alphazero import Network
from environment import HOST_DLL, Host, ProtocolError, SnapshotBranch, TrafficEnv
from live_view import LiveViewer, UnityLiveViewer
from train import run_episode
from visualize import replay


def checks(dotnet, host_dll):
    torch.set_num_threads(1)
    torch.manual_seed(123)
    model = Network(value_scale=100)
    with Host(dotnet=dotnet,dll=host_dll) as host, Host(dotnet=dotnet,dll=host_dll) as other:
        env = TrafficEnv(host,cap_seconds=3.25)
        branch = SnapshotBranch(other,env)
        viewer = LiveViewer(delay=0,search_delay=0,show_search=True)
        def run(observer=None):
            return run_episode(env,branch,"DarEsSalaam",200000,model,8,random.Random(901),False,
                               collect_samples=False,observer=observer,progress_every=0)
        _, plain, plain_record = run()
        final_state = copy.deepcopy(env.observation)
        _, observed, record = run(viewer)
        assert record == plain_record, "Observation changed real actions or search diagnostics"
        assert env.observation == final_state, "Observation changed the simulator state"
        for key in plain:
            if key != "wallSeconds":
                assert plain[key] == observed[key], key
        assert len(viewer.session["main"]) == len(record["actions"])+1
        assert any(f["depth"] > 0 for f in viewer.search_frames), "No branch transitions streamed"
        roots = [f for f in viewer.search_frames if f["depth"] == 0]
        assert roots and all(f["state"] == viewer.session["main"][f["decisionIndex"]]["state"] for f in roots)
        assert all(len(f["decision"]["candidates"]) > 0 for f in viewer.session["main"][1:])
        replayed = LiveViewer(delay=0,search_delay=0)
        replay(host,record,replayed)
        assert replayed.session["result"]["replayVerified"]
        assert replayed.session["main"][-1]["state"] == viewer.session["main"][-1]["state"]
        with tempfile.TemporaryDirectory() as directory:
            native=UnityLiveViewer(directory=directory,delay=0,search_delay=0,show_search=True)
            native("reset",final_state,scenario="DarEsSalaam",seed=200000,weights=record["rewardWeights"])
            native("search",final_state,simulation=1,depth=0)
            native("main",final_state,decision=record["actions"][-1])
            main_packet=json.loads((Path(directory)/"main.json").read_text())
            search_packet=json.loads((Path(directory)/"search.json").read_text())
            assert main_packet["state"]==search_packet["state"]
            assert main_packet["meta"]["runId"]==search_packet["meta"]["runId"]
            assert search_packet["simulation"]==1 and main_packet["decision"]==record["actions"][-1]
            replace = Path.replace
            attempts = []
            def transient_lock(path,target):
                attempts.append(target)
                if len(attempts)<=2:
                    raise PermissionError("Simulated Windows reader lock")
                return replace(path,target)
            with patch.object(Path,"replace",transient_lock):
                native("search",final_state,simulation=2,depth=0)
            assert len(attempts)==3 and native.skipped_frames==0
            with patch.object(Path,"replace",side_effect=PermissionError("Persistent reader lock")):
                native("search",final_state,simulation=3,depth=0)
            assert native.skipped_frames==1 and native.search_frames[-1]["simulation"]==3
            native.save(Path(directory)/"archive.html")
            assert json.loads((Path(directory)/"archive.session.json").read_text())["main"][-1]["state"]==main_packet["state"]
        broken = copy.deepcopy(record)
        broken["actions"][0]["afterTrips"] += 1
        try:
            replay(host,broken,replayed)
        except ProtocolError:
            pass
        else:
            raise AssertionError("Replay accepted divergent trips")
        with LiveViewer(port=0,delay=0,search_delay=0,show_search=True) as server:
            url = f"http://127.0.0.1:{server.port}"
            server("reset",final_state,scenario="DarEsSalaam",seed=200000,mode="test",weights=record["rewardWeights"])
            def get(path):
                with urlopen(url+path,timeout=3) as response:
                    return json.load(response)
            def control(value):
                request = Request(url+"/api/control",data=json.dumps(value).encode(),
                                  headers={"Content-Type":"application/json"})
                with urlopen(request,timeout=3) as response:
                    return json.load(response)
            payload = get("/api/events")
            assert payload["session"]["main"][0]["state"] == viewer.session["main"][-1]["state"]
            cursor = payload["seq"]
            server("search",final_state,simulation=1,depth=0)
            assert [e["kind"] for e in get(f"/api/events?after={cursor}")["events"]] == ["search"]
            control({"paused":True})
            worker = threading.Thread(target=lambda:server("search",final_state,simulation=2,depth=0))
            worker.start()
            time.sleep(.08)
            assert worker.is_alive(), "Pause did not block the observation callback"
            control({"paused":False})
            worker.join(timeout=2)
            assert not worker.is_alive(), "Resume failed"
            server.session["meta"]["source"] = "</script><script>unsafe()</script>"
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/"replay.html"
                server.save(path)
                html = path.read_text(encoding="utf-8")
                assert "__SESSION_DATA__" not in html and "<script>unsafe()" not in html
                embedded = html.split('<script id="sessionData" type="application/json">')[1].split("</script>")[0]
                assert json.loads(embedded)["meta"]["source"].startswith("</script>")
    print("PASS: viewing preserves actions/RNG/outcomes; MCTS roots restore correctly; fractional replay; "
          "divergence detection; incremental HTTP; pause/resume; portable HTML escaping")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotnet",default="dotnet")
    parser.add_argument("--host-dll",type=Path,default=HOST_DLL)
    args = parser.parse_args()
    checks(args.dotnet,args.host_dll)
