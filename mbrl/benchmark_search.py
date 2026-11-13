"""Compare search worker counts at one restored city, without full-game search."""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import time

import numpy as np
import torch

from actions import clear_caches
from alphazero import Network, search
from environment import (HOST_DLL, Host, SnapshotBranch, TrafficEnv,
                         DEFAULT_FAILURE_PENALTY, DEFAULT_UNANSWERED_PENALTY)
from parallel_search import SearchPool
from proposals import ActionGuard, Cooldowns, proposals


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint",type=Path,required=True)
    parser.add_argument("--trace",type=Path,help="Restore a saved action prefix instead of the baseline prefix")
    parser.add_argument("--decision",type=int,default=120,help="Number of recorded/baseline decisions to replay once")
    parser.add_argument("--workers",type=int,nargs="+",default=[1,2,4])
    parser.add_argument("--simulations",type=int,default=32,help="Total rollouts, not per worker")
    parser.add_argument("--search-depth",type=int,default=4)
    parser.add_argument("--repeats",type=int,default=3)
    parser.add_argument("--torch-threads",type=int,default=1)
    parser.add_argument("--dotnet",default="dotnet")
    parser.add_argument("--host-dll",type=Path,default=HOST_DLL)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if min(*args.workers,args.simulations,args.search_depth,args.repeats,args.torch_threads)<1 or args.decision<0:
        parser.error("Counts must be positive; decision can be zero")
    if len(set(args.workers)) != len(args.workers):
        parser.error("Worker counts must be distinct")
    output=args.output or Path("output/mbrl")/("parallel-benchmark-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+".json")
    if output.exists():
        parser.error(f"Output already exists: {output}")
    torch.set_num_threads(args.torch_threads)
    checkpoint=torch.load(args.checkpoint,map_location="cpu",weights_only=False)
    config=checkpoint["config"]
    model=Network(value_scale=config.get("valueScale",10))
    model.load_compatible_state_dict(checkpoint["model"])
    model.eval()
    record=json.loads(args.trace.read_text()) if args.trace else None
    city,seed=(record["scenario"],record["seed"]) if record else ("LosAngeles",100090)
    if city=="London":
        parser.error("This development benchmark does not open the held-out London test")
    if record and args.decision>len(record["actions"]):
        parser.error("Decision exceeds recorded prefix")
    with Host(dotnet=args.dotnet,dll=args.host_dll) as host, ExitStack() as stack:
        env=TrafficEnv(host,cap_seconds=config.get("capSeconds",1800),alpha=config.get("alpha",.05),
                       lam=config.get("lambdaCost",.005),beta=config.get("betaCongestion",0),
                       failure_penalty=config.get("failurePenalty",DEFAULT_FAILURE_PENALTY),
                       unanswered_penalty=config.get("unansweredPenalty",DEFAULT_UNANSWERED_PENALTY),
                       overcrowding_penalty=config.get("overcrowdingPenalty",0),
                       trip_reward=config.get("tripReward",1.0),
                       clear_trip_bonus=config.get("clearTripBonus",0.),
                       congestion_fraction_penalty=config.get("congestionFractionPenalty",0.),
                       congestion_wait_threshold=config.get("congestionWaitThreshold",2.))
        env.reset(city,seed)
        guard=ActionGuard(Cooldowns(**config.get("cooldowns",{})))
        history=[]
        for index in range(args.decision):
            if env.done:
                raise RuntimeError(f"Episode ended before requested decision {args.decision}")
            if record:
                stored=record["actions"][index]
                request={key:stored[key] for key in ("command","tool","x","y","toX","toY","id","choice") if key in stored}
            else:
                available=proposals(env.observation,host,guard)
                request=max(available,key=lambda item:item.priority).request
            before=env.observation
            transition=env.step(request)
            guard.record(before,transition.observation,request,transition.accepted)
            history.append(request)
            if record and (transition.accepted != stored["accepted"] or
                           abs(transition.observation["time"]-stored["afterTime"])>1e-6 or
                           transition.observation["tripsCompleted"] != stored["afterTrips"]):
                raise RuntimeError(f"Recorded prefix diverged at decision {index+1}")
        if env.done:
            raise RuntimeError("Choose a prefix before the episode ends")
        root=env.observation
        digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
        root_hash=digest(root)
        # Replay once per host to establish its in-memory root snapshot. Setup is untimed.
        pools={}
        for count in args.workers:
            other=stack.enter_context(Host(dotnet=args.dotnet,dll=args.host_dll))
            branch=SnapshotBranch(other,env)
            branch.env.reset(city,seed)
            for request in history:
                branch.env.step(request)
            if other.call(command="observe")["observation"] != root:
                raise RuntimeError("Benchmark branch prefix diverged")
            other.call(command="saveSnapshot",id=branch.snapshot_id)
            branch.root_observation=root
            pool=stack.enter_context(SearchPool(branch,count))
            for extra in pool.branches[1:]:
                extra.env.reset(city,seed)
                for request in history:
                    extra.env.step(request)
                if extra.env.observation != root:
                    raise RuntimeError("Benchmark worker prefix diverged")
                extra.env.host.call(command="saveSnapshot",id=extra.snapshot_id)
                extra.root_observation=root
            pools[count]=pool
        def measure(count):
            # Fixed cold Python caches for each measurement; no rendering or pacing.
            clear_caches()
            started=time.perf_counter()
            items,visits,stats=search(model,env,pools[count],history,args.simulations,args.search_depth,
                                     random.Random(12345),discount=config.get("discount",.999),guard=guard)
            seconds=time.perf_counter()-started
            assert visits.sum()==args.simulations
            assert digest(host.call(command="observe")["observation"])==root_hash
            return {"workers":count,"wallSeconds":seconds,"stats":stats,
                    "visits":visits.tolist(),"selected":items[int(np.argmax(visits))].request}
        for count in args.workers:
            measure(count)  # Untimed warm-up of model/hosts, with matching cache reset policy.
        rows=[]
        for repeat in range(args.repeats):
            order=args.workers if repeat%2==0 else list(reversed(args.workers))
            for count in order:
                row=measure(count)
                row["repeat"]=repeat
                rows.append(row)
                print(json.dumps({"workers":count,"repeat":repeat,"wallSeconds":row["wallSeconds"]}),flush=True)
        summary=[{"workers":count,"medianSeconds":statistics.median(r["wallSeconds"] for r in rows if r["workers"]==count),
                  "maxSeconds":max(r["wallSeconds"] for r in rows if r["workers"]==count),
                  "medianTransitions":statistics.median(r["stats"]["simulatorTransitions"] for r in rows if r["workers"]==count),
                  "medianTransitionsPerSecond":statistics.median(r["stats"]["simulatorTransitions"]/r["wallSeconds"]
                                                                 for r in rows if r["workers"]==count)} for count in args.workers]
        baseline=next((row["medianSeconds"] for row in summary if row["workers"]==1),None)
        for row in summary:
            row["speedupVsOneWorker"]=baseline/row["medianSeconds"] if baseline else None
        report={"settings":vars(args),"cpuCount":os.cpu_count(),"torchVersion":torch.__version__,
                "hostSha256":hashlib.sha256(args.host_dll.read_bytes()).hexdigest(),
                "checkpointSha256":hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                "sourceHashes":{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                for name in ("parallel_search.py","alphazero.py","actions.py","environment.py","proposals.py")},
                "root":{"scenario":city,"seed":seed,"decision":args.decision,"time":root["time"],
                        "buildings":len(root["buildings"]),"vehicles":len(root["vehicles"]),"sha256":root_hash},
                "notes":"Fixed total rollout budget; deterministic waves change selection versus serial. "
                        "Prefix replay, host startup and warm-up excluded. Python caches reset before each sample. "
                        "Timing/visit differences do not establish gameplay quality.",
                "results":summary,"rows":rows}
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
        print(json.dumps({"output":str(output),"results":summary}),flush=True)


if __name__=="__main__":
    main()
