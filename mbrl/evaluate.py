"""Paired policy/MCTS budget evaluation; test data requires an explicit split."""
from __future__ import annotations
import argparse
import json
import math
import hashlib
import shutil
import random
import os
import sys
import time
import atexit
from contextlib import ExitStack
from pathlib import Path
import torch
if "--source-dir" in sys.argv:
    source=Path(sys.argv[sys.argv.index("--source-dir")+1]).resolve()
    os.environ.setdefault("TRAFFIC_HOST_DLL",str(Path(__file__).resolve().parents[1]/"simulation/Headless/bin/Debug/net8.0/TrafficHost.dll"))
    sys.path.insert(0,str(source))
    import environment
    environment.ROOT=Path(__file__).resolve().parents[1]
from alphazero import Network
from environment import HOST_DLL, Host, SnapshotBranch, TrafficEnv
from proposals import Cooldowns
from protocol import validation_cases, test_cases
from train import run_episode
from experiment import rank, atomic_save
from live_view import add_viewer_arguments, viewer_context
from parallel_search import SearchPool, add_search_arguments, configure_search


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint",type=Path,required=True)
    parser.add_argument("--source-dir",type=Path,help="Use a preserved implementation for a frozen control")
    parser.add_argument("--validation-seeds",type=int,help="One for single-city checkpoints; historical city splits default to two")
    parser.add_argument("--split",choices=("validation","test"),default="validation")
    parser.add_argument("--simulations",type=int,default=16,help="Zero evaluates the policy alone")
    parser.add_argument("--budgets",type=int,nargs="+")
    parser.add_argument("--search-depth",type=int,default=4)
    parser.add_argument("--cap-seconds",type=float,default=1800,
                        help="Maximum simulated seconds per game (default: 1800); game failure ends it earlier")
    parser.add_argument("--guarded",action="store_true",help="Apply new guards to a legacy model")
    parser.add_argument("--failure-penalty",type=float,help="Override checkpoint game-failure penalty")
    parser.add_argument("--unanswered-penalty",type=float,help="Override checkpoint penalty per undelivered request-second")
    parser.add_argument("--overcrowding-penalty",type=float,help="Override checkpoint penalty per capacity-pressure second")
    parser.add_argument("--lambda-cost",type=float,help="Override checkpoint modification-cost weight")
    parser.add_argument("--trip-reward",type=float,help="Override completed-trip reward (legacy checkpoints default to 1)")
    parser.add_argument("--clear-trip-bonus",type=float,help="Override bonus per congestion-adjusted completed trip")
    parser.add_argument("--congestion-fraction-penalty",type=float,help="Override penalty per blocked-fraction second")
    parser.add_argument("--congestion-wait-threshold",type=float,help="Seconds blocked before an active car counts as congested")
    parser.add_argument("--compare-heuristic",action="store_true")
    parser.add_argument("--compare-guarded-heuristic",action="store_true")
    parser.add_argument("--heuristic-only",action="store_true")
    parser.add_argument("--save-best",type=Path)
    parser.add_argument("--dotnet",default="dotnet")
    parser.add_argument("--host-dll",type=Path,default=HOST_DLL,
                        help="Simulator host matching the checkpoint; overrides TRAFFIC_HOST_DLL")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--overwrite",action="store_true",help="Repeat a matching completed evaluation")
    parser.add_argument("--runtime-note",default="")
    add_viewer_arguments(parser)
    add_search_arguments(parser)
    args=parser.parse_args()
    if any(v is not None and (not math.isfinite(v) or v < 0)
           for v in (args.failure_penalty,args.unanswered_penalty,args.overcrowding_penalty,args.lambda_cost,
                     args.clear_trip_bonus,args.congestion_fraction_penalty)):
        parser.error("Reward penalties must be finite and nonnegative")
    if args.trip_reward is not None and (not math.isfinite(args.trip_reward) or args.trip_reward<=0):
        parser.error("Trip reward must be finite and positive")
    if args.congestion_wait_threshold is not None and (not math.isfinite(args.congestion_wait_threshold) or args.congestion_wait_threshold<=0):
        parser.error("Congestion wait threshold must be finite and positive")
    if args.source_dir and any(v is not None for v in
                              (args.failure_penalty,args.unanswered_penalty,args.overcrowding_penalty,args.lambda_cost,args.trip_reward,
                               args.clear_trip_bonus,args.congestion_fraction_penalty,args.congestion_wait_threshold)):
        parser.error("Reward overrides require the current implementation, without --source-dir")
    try:
        configure_search(args)
    except ValueError as exc:
        parser.error(str(exc))
    if args.source_dir and args.search_workers != 1:
        parser.error("Frozen source implementations support only --search-workers 1")
    if args.source_dir and args.live:
        parser.error("Live viewing needs the current implementation; replay a frozen control's saved trace with visualize.py --trace")
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        lock=args.output.with_suffix(args.output.suffix+".lock").open("a+b")
        lock.seek(0,2)
        if lock.tell()==0:
            lock.write(b"0");lock.flush()
        atexit.register(lock.close)
        if os.name=="nt":
            import msvcrt
            while True:
                try:
                    lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);break
                except OSError:
                    time.sleep(1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
    budgets=[] if args.heuristic_only else args.budgets or [args.simulations]
    if (budgets and min(budgets)<0) or args.search_depth<1:
        parser.error("Invalid search budget")
    if args.split=="test" and (len(budgets)>1 or args.save_best):
        parser.error("Choose one locked policy before accessing the test split")
    if args.heuristic_only and (args.save_best or not (args.compare_heuristic or args.compare_guarded_heuristic)):
        parser.error("Heuristic-only evaluation needs a heuristic flag and cannot select a model")
    state=torch.load(args.checkpoint,map_location="cpu",weights_only=False)
    config=state["config"]
    import protocol as checkpoint_protocol
    try:
        if hasattr(checkpoint_protocol,"evaluation_cases"):
            cases=checkpoint_protocol.evaluation_cases(config,args.split,args.validation_seeds)
        else:
            count=args.validation_seeds or 2
            cases=validation_cases(count) if args.split=="validation" else test_cases(count)
    except ValueError as exc:
        parser.error(str(exc))
    args.validation_seeds=len(cases)
    reward_options={}
    if not args.source_dir:
        from environment import DEFAULT_FAILURE_PENALTY, DEFAULT_UNANSWERED_PENALTY, OBSERVATION_SCHEMA, GRID_CHANNELS
        from actions import MAX_CANDIDATES, RAW_CANDIDATES
        from alphazero import ROOT_COMPARISON_ACTIONS
        config=dict(config)
        config.update(maxCandidates=MAX_CANDIDATES,rawCandidates=RAW_CANDIDATES)
        config["rootComparisonActions"]=ROOT_COMPARISON_ACTIONS
        config["rootPolicyMode"]="post-comparison-visits-v1"
        config.update(observationSchema=OBSERVATION_SCHEMA,gridChannels=GRID_CHANNELS,
                      searchValueBaseline="state-value-v1")
        config["tripReward"]=args.trip_reward if args.trip_reward is not None else config.get("tripReward",1.0)
        for key,argument,default in (("clearTripBonus",args.clear_trip_bonus,0.),
                                     ("congestionFractionPenalty",args.congestion_fraction_penalty,0.),
                                     ("congestionWaitThreshold",args.congestion_wait_threshold,2.)):
            config[key]=argument if argument is not None else config.get(key,default)
        config["failurePenalty"]=(args.failure_penalty if args.failure_penalty is not None else
                                  config.get("failurePenalty",DEFAULT_FAILURE_PENALTY))
        config["unansweredPenalty"]=(args.unanswered_penalty if args.unanswered_penalty is not None else
                                     config.get("unansweredPenalty",DEFAULT_UNANSWERED_PENALTY))
        # Missing field in a historical checkpoint means no capacity-pressure shaping.
        config["overcrowdingPenalty"]=(args.overcrowding_penalty if args.overcrowding_penalty is not None else
                                       config.get("overcrowdingPenalty",0))
        if args.lambda_cost is not None:
            config["lambdaCost"]=args.lambda_cost
        state["config"]=config
        reward_options={"failure_penalty":config["failurePenalty"],"unanswered_penalty":config["unansweredPenalty"],
                        "overcrowding_penalty":config["overcrowdingPenalty"],"trip_reward":config["tripReward"],
                        "clear_trip_bonus":config["clearTripBonus"],
                        "congestion_fraction_penalty":config["congestionFractionPenalty"],
                        "congestion_wait_threshold":config["congestionWaitThreshold"]}
    model=Network(value_scale=config.get("valueScale",10))
    getattr(model,"load_compatible_state_dict",model.load_state_dict)(state["model"])
    if not args.source_dir:
        state["model"]=model.state_dict()
    # Evaluation exports are inference states. Overrides must not relabel the
    # original optimizer/replay as if it had been trained under new rewards.
    state={"model":state["model"],"config":config,"episode":state.get("episode",0)}
    provenance={"checkpointSha256":hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                "hostSha256":hashlib.sha256(args.host_dll.read_bytes()).hexdigest(),
                "torchVersion":torch.__version__,"sourceHashes":{}}
    if args.output:
        snapshot=args.output.parent/(args.output.stem+"-source")
        snapshot.mkdir(parents=True,exist_ok=True)
        for name in ("actions","alphazero","environment","proposals","protocol","train","experiment","parallel_search"):
            source=Path(sys.modules[name].__file__)
            provenance["sourceHashes"][name]=hashlib.sha256(source.read_bytes()).hexdigest()
            shutil.copy2(source,snapshot/source.name)
    settings={"budgets":budgets,"depth":args.search_depth,"horizon":args.cap_seconds or config["capSeconds"],
              "searchWorkers":args.search_workers,"torchThreads":args.torch_threads,
              "seeds":args.validation_seeds,"split":args.split,"guarded":args.guarded or config.get("safety",False),
              "rawHeuristic":args.compare_heuristic,"guardedHeuristic":args.compare_guarded_heuristic,
              "proposalCache":os.environ.get("TRAFFIC_DISABLE_PROPOSAL_CACHE")!="1"}
    settings.update(experimentProtocol=config.get("experimentProtocol","legacy-city-split"),
                    cases=[[city,seed] for city,seed in cases])
    settings.update(reward_options)
    settings["lambdaCost"]=config["lambdaCost"]
    if not args.source_dir:
        settings["rootComparisonActions"]=config["rootComparisonActions"]
        settings["rootPolicyMode"]=config["rootPolicyMode"]
        settings["observationSchema"]=config["observationSchema"]
        settings["searchValueBaseline"]=config["searchValueBaseline"]
    requested=budgets+([-1] if args.compare_heuristic else [])+([-2] if args.compare_guarded_heuristic else [])
    if args.output and args.output.exists() and not args.overwrite:
        previous=json.loads(args.output.read_text(encoding="utf-8"))
        if previous.get("settings")==settings and previous.get("provenance")==provenance and \
                sorted(r["simulations"] for r in previous["results"])==sorted(requested):
            if args.save_best:
                state["evaluationSelection"]=max([r for r in previous["results"] if r["simulations"]>=0],key=lambda r:tuple(r["rank"]))
                atomic_save(state,args.save_best)
            print(json.dumps({"reusedCompletedEvaluation":str(args.output),"results":previous["results"]}),flush=True)
            return
    guarded=args.guarded or config.get("safety",False)
    cooldowns=Cooldowns(**config.get("cooldowns",{}))
    rows=[]
    results=[]
    print(f"Simulator host: {args.host_dll.resolve()}",flush=True)
    with viewer_context(args) as viewer, Host(dotnet=args.dotnet,dll=args.host_dll) as live, Host(dotnet=args.dotnet,dll=args.host_dll) as other, ExitStack() as workers:
        env=TrafficEnv(live,cap_seconds=args.cap_seconds or config["capSeconds"],
            alpha=config["alpha"],lam=config["lambdaCost"],beta=config.get("betaCongestion",0),**reward_options)
        branch=workers.enter_context(SearchPool(SnapshotBranch(other,env),args.search_workers))
        for budget in budgets+([-1] if args.compare_heuristic else [])+([-2] if args.compare_guarded_heuristic else []):
            subset=[]
            for city,seed in cases:
                _,row,record=run_episode(env,branch,city,seed,model,max(0,budget),random.Random(seed+900000),False,
                    baseline=budget<0,collect_samples=False,depth=args.search_depth,
                    safety=budget==-2 if budget<0 else guarded,cooldowns=cooldowns,
                    discount=config.get("discount",.997),**({"observer":viewer} if viewer is not None else {}))
                row.update(mode="guarded-heuristic" if budget==-2 else "heuristic" if budget==-1 else "policy" if budget==0 else f"mcts{budget}",
                           simulations=budget)
                subset.append(row)
                rows.append(row)
                print(json.dumps(row),flush=True)
                if args.output:
                    trace=args.output.parent/(args.output.stem+f"-{budget}-{seed}-trace.json")
                    trace.parent.mkdir(parents=True,exist_ok=True)
                    trace.write_text(json.dumps(record),encoding="utf-8")
                    if viewer is not None:
                        viewer.save(trace.with_suffix(".html"))
            result={"simulations":budget,"rank":list(rank(subset)),
                    "meanWallSeconds":sum(r["wallSeconds"] for r in subset)/len(subset),
                    "meanDepth":sum(r["meanSearchDepthReached"] for r in subset)/len(subset),
                    "rejected":sum(r["invalidActions"] for r in subset),
                    "reversals":sum(r["reversals"] for r in subset)}
            results.append(result)
            summary={"checkpoint":str(args.checkpoint),"split":args.split,"results":results,"rows":rows,
                     "provenance":provenance,"settings":settings,"runtimeNote":args.runtime_note}
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True)
                args.output.write_text(json.dumps(summary,indent=2),encoding="utf-8")
            print(json.dumps(result),flush=True)
        if args.save_best:
            best=max([r for r in results if r["simulations"]>=0],key=lambda r:tuple(r["rank"]))
            state["evaluationSelection"]=best
            atomic_save(state,args.save_best)


if __name__=="__main__":
    main()
