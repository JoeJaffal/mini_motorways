"""Controlled training with mixed replay, component losses and paired evaluation."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import shutil
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch

from alphazero import ROOT_COMPARISON_ACTIONS, Network, ReplayMixture, train_batch
from actions import MAX_CANDIDATES, RAW_CANDIDATES
from environment import (ROOT, HOST_DLL, Host, TrafficEnv, SnapshotBranch, ReplayBranch,
                         DEFAULT_FAILURE_PENALTY, DEFAULT_UNANSWERED_PENALTY,
                         DEFAULT_MODIFICATION_PENALTY, DEFAULT_OVERCROWDING_PENALTY,
                         DEFAULT_TRIP_REWARD, OBSERVATION_SCHEMA, GRID_CHANNELS,
                         DEFAULT_CLEAR_TRIP_BONUS, DEFAULT_CONGESTION_FRACTION_PENALTY,
                         DEFAULT_CONGESTION_WAIT_THRESHOLD)
from proposals import Cooldowns
from protocol import (aggregate_rank, SingleCitySeeds, SINGLE_CITY_PROTOCOL,
                      DEFAULT_CITY, DEFAULT_VALIDATION_SEED, DEFAULT_TEST_SEED)
from train import run_episode
from live_view import add_viewer_arguments, viewer_context
from parallel_search import SearchPool, add_search_arguments, configure_search


def atomic_save(value, path):
    temp = path.with_suffix(path.suffix + ".tmp")
    torch.save(value, temp)
    temp.replace(path)


def rank(rows):
    return aggregate_rank(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes",type=int,default=6)
    parser.add_argument("--city",choices=("LosAngeles","Beijing","Tokyo","DarEsSalaam","London"),default=DEFAULT_CITY)
    parser.add_argument("--validation-seed",type=int,default=DEFAULT_VALIDATION_SEED)
    parser.add_argument("--test-seed",type=int,default=DEFAULT_TEST_SEED)
    parser.add_argument("--seed-sequence-seed",type=int,help="Reproduce training-seed draws; otherwise generate and record a fresh sampler seed")
    parser.add_argument("--validation-seeds",type=int,default=1,help="Must be 1 for the single-city protocol")
    parser.add_argument("--test-seeds",type=int,default=1,help="Must be 1 for the single-city protocol")
    parser.add_argument("--validate-every",type=int,default=3)
    parser.add_argument("--evaluation-budgets",type=int,nargs="+",default=[0],
                        help="Validation search budgets; policy-only is zero. Budget sweeps are separate.")
    parser.add_argument("--simulations",type=int,default=16)
    parser.add_argument("--search-depth",type=int,default=4)
    parser.add_argument("--branch",choices=("snapshot","replay"),default="snapshot")
    parser.add_argument("--bootstrap-episodes",type=int,default=0)
    parser.add_argument("--bootstrap-updates",type=int,default=128)
    parser.add_argument("--updates-per-episode",type=int,default=64)
    parser.add_argument("--batch-size",type=int,default=32)
    parser.add_argument("--replay-states",type=int,default=6000)
    parser.add_argument("--value-loss",choices=("huber","mse"),default="huber")
    parser.add_argument("--value-scale",type=float,default=100)
    parser.add_argument("--value-weight",type=float,default=1)
    parser.add_argument("--policy-weight",type=float,default=1)
    parser.add_argument("--discount",type=float,default=.999)
    parser.add_argument("--cap-seconds",type=float,default=1800)
    parser.add_argument("--alpha",type=float,default=.05)
    parser.add_argument("--trip-reward",type=float,default=DEFAULT_TRIP_REWARD)
    parser.add_argument("--clear-trip-bonus",type=float,default=DEFAULT_CLEAR_TRIP_BONUS)
    parser.add_argument("--congestion-fraction-penalty",type=float,default=DEFAULT_CONGESTION_FRACTION_PENALTY)
    parser.add_argument("--congestion-wait-threshold",type=float,default=DEFAULT_CONGESTION_WAIT_THRESHOLD)
    parser.add_argument("--lambda-cost",type=float,default=DEFAULT_MODIFICATION_PENALTY)
    parser.add_argument("--beta-congestion",type=float,default=0)
    parser.add_argument("--failure-penalty",type=float,default=DEFAULT_FAILURE_PENALTY,
                        help="Penalty on natural game failure, excluding time cutoffs (default: 10)")
    parser.add_argument("--unanswered-penalty",type=float,default=DEFAULT_UNANSWERED_PENALTY,
                        help="Penalty per undelivered request per simulated second (default: .01)")
    parser.add_argument("--overcrowding-penalty",type=float,default=DEFAULT_OVERCROWDING_PENALTY,
                        help="Per second: weight * max(0, demand - capacity + 1) per destination (default: .05)")
    parser.add_argument("--driveway-cooldown",type=float,default=20)
    parser.add_argument("--motorway-cooldown",type=float,default=30)
    parser.add_argument("--construction-cooldown",type=float,default=10)
    parser.add_argument("--reversal-window",type=float,default=60)
    parser.add_argument("--patience",type=int,default=0,help="Validation rounds without improvement; zero disables")
    parser.add_argument("--min-episodes",type=int,default=3)
    parser.add_argument("--final-test",action="store_true")
    parser.add_argument("--dotnet",default="dotnet")
    parser.add_argument("--host-dll",type=Path,default=HOST_DLL,
                        help="Simulator host matching the checkpoint; overrides TRAFFIC_HOST_DLL")
    parser.add_argument("--device",default="cpu")
    parser.add_argument("--init-checkpoint",type=Path)
    parser.add_argument("--resume",type=Path,help="Continue the latest full checkpoint, including replay, optimizer and RNG")
    parser.add_argument("--resume-demonstration",type=Path,
                        help="Continue an episode-zero checkpoint with optimizer and RNG state")
    parser.add_argument("--demonstrations",type=Path,help="Permanent replay archive for a demonstration-state continuation")
    parser.add_argument("--episode-offset",type=int,default=0)
    parser.add_argument("--output",type=Path)
    add_viewer_arguments(parser)
    add_search_arguments(parser)
    args = parser.parse_args()
    if args.validation_seeds!=1 or args.test_seeds!=1:
        parser.error("Single-city training reserves exactly one validation seed and one test seed")
    try:
        seed_cases=SingleCitySeeds(args.city,args.validation_seed,args.test_seed)
    except ValueError as exc:
        parser.error(str(exc))
    if any(not np.isfinite(v) or v < 0 for v in
           (args.lambda_cost,args.failure_penalty,args.unanswered_penalty,args.overcrowding_penalty,
            args.clear_trip_bonus,args.congestion_fraction_penalty)):
        parser.error("Reward penalties must be finite and nonnegative")
    try:
        configure_search(args)
    except ValueError as exc:
        parser.error(str(exc))
    if min(args.episodes,args.validation_seeds,args.test_seeds,args.validate_every,args.batch_size,
           args.bootstrap_updates,args.updates_per_episode,args.search_depth,args.value_scale,args.cap_seconds)<=0:
        parser.error("Counts, scales and horizon must be positive")
    if args.simulations<0 or not 0<args.discount<=1 or args.bootstrap_episodes<0:
        parser.error("Invalid search, discount or demonstration setting")
    if min(args.alpha,args.lambda_cost,args.beta_congestion,args.driveway_cooldown,args.motorway_cooldown,
           args.construction_cooldown,args.reversal_window,args.patience,args.min_episodes,args.episode_offset,
           args.policy_weight,args.value_weight)<0 or args.replay_states<1:
        parser.error("Penalties, cooldowns, stopping settings and loss weights must be nonnegative; replay must be positive")
    if args.policy_weight+args.value_weight==0:
        parser.error("At least one loss weight must be positive")
    if not np.isfinite(args.trip_reward) or args.trip_reward <= 0:
        parser.error("Trip reward must be finite and positive")
    if not np.isfinite(args.congestion_wait_threshold) or args.congestion_wait_threshold<=0:
        parser.error("Congestion wait threshold must be finite and positive")
    resumed=None
    if args.resume:
        if args.init_checkpoint or args.resume_demonstration or args.demonstrations or args.bootstrap_episodes:
            parser.error("--resume needs --bootstrap-episodes 0 and cannot combine with other initialization modes")
        resumed=torch.load(args.resume,map_location="cpu",weights_only=False)
        if "replay" not in resumed or resumed["config"].get("observationSchema") != OBSERVATION_SCHEMA:
            parser.error("Exact resume requires a full checkpoint with the current input schema and replay; "
                         "use --init-checkpoint for a legacy weights-only warm start")
        required=("optimizer","pythonRandom","numpyRandom","torchRandom","episode")
        if any(key not in resumed for key in required):
            parser.error("Resume checkpoint is missing optimizer, RNG or episode state")
        previous=resumed["config"]
        if (previous.get("experimentProtocol")!=SINGLE_CITY_PROTOCOL
                or "trainingSeedSampler" not in resumed or "trainingExamplesCompleted" not in resumed):
            parser.error("This checkpoint uses the previous city split; use --init-checkpoint with the latest weights to start the Los Angeles seed protocol")
        if args.seed_sequence_seed is not None and args.seed_sequence_seed!=previous["seed_sequence_seed"]:
            parser.error("Seed-sequence seed must match the resumed checkpoint")
        args.seed_sequence_seed=previous["seed_sequence_seed"]
        matching={"tripReward":args.trip_reward,"alpha":args.alpha,"lambdaCost":args.lambda_cost,
                  "betaCongestion":args.beta_congestion,"failurePenalty":args.failure_penalty,
                  "unansweredPenalty":args.unanswered_penalty,"overcrowdingPenalty":args.overcrowding_penalty,
                  "discount":args.discount,"valueScale":args.value_scale,"capSeconds":args.cap_seconds,
                  "maxCandidates":MAX_CANDIDATES,"rawCandidates":RAW_CANDIDATES,
                  "simulations":args.simulations,"search_depth":args.search_depth,
                  "search_workers":args.search_workers,"torch_threads":args.torch_threads,
                  "searchValueBaseline":"state-value-v1","rootPolicyMode":"post-comparison-visits-v1",
                  "updates_per_episode":args.updates_per_episode,
                  "batch_size":args.batch_size,"replay_states":args.replay_states,
                  "policy_weight":args.policy_weight,"value_weight":args.value_weight,"value_loss":args.value_loss,
                  "branch":args.branch,"driveway_cooldown":args.driveway_cooldown,
                  "motorway_cooldown":args.motorway_cooldown,"construction_cooldown":args.construction_cooldown,
                  "reversal_window":args.reversal_window,"city":args.city,
                  "validationSeed":args.validation_seed,"testSeed":args.test_seed,
                  "validate_every":args.validate_every,"clearTripBonus":args.clear_trip_bonus,
                  "congestionFractionPenalty":args.congestion_fraction_penalty,
                  "congestionWaitThreshold":args.congestion_wait_threshold}
        differences=[key for key,value in matching.items() if previous.get(key)!=value]
        if differences:
            parser.error("Resume settings differ: "+", ".join(differences)+"; use matching settings or --init-checkpoint")
        if previous.get("hostSha256") != hashlib.sha256(args.host_dll.read_bytes()).hexdigest():
            parser.error("Exact resume requires the same simulator host")
        if args.episode_offset not in (0,resumed["episode"]):
            parser.error("Episode offset must match the resumed checkpoint")
        args.episode_offset=resumed["episode"]
    if args.episode_offset+args.episodes>50000 or args.bootstrap_episodes>50000:
        parser.error("Reserved training seed range exceeded")
    if min(args.evaluation_budgets)<0:
        parser.error("Evaluation budgets must be nonnegative")
    if args.resume_demonstration and (args.init_checkpoint or not args.demonstrations or args.bootstrap_episodes):
        parser.error("A demonstration continuation needs --demonstrations and --bootstrap-episodes 0")
    demonstration_state=None
    if args.resume_demonstration:
        demonstration_state=torch.load(args.resume_demonstration,map_location="cpu",weights_only=False)
        previous=demonstration_state["config"]
        if previous.get("experimentProtocol")!=SINGLE_CITY_PROTOCOL:
            parser.error("Previous city-split demonstrations require a weights-only --init-checkpoint transition")
        if args.seed_sequence_seed is not None and args.seed_sequence_seed!=previous["seed_sequence_seed"]:
            parser.error("Seed-sequence seed must match the demonstration checkpoint")
        args.seed_sequence_seed=previous["seed_sequence_seed"]
    if args.seed_sequence_seed is None:
        args.seed_sequence_seed=random.SystemRandom().randrange(2**63)
    seed_cases=SingleCitySeeds(args.city,args.validation_seed,args.test_seed,args.seed_sequence_seed)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out=args.output or ROOT/"output/mbrl"/f"controlled-{stamp}"
    if out.exists():
        parser.error(f"Output already exists: {out}")
    out.mkdir(parents=True)
    (out/"traces").mkdir()
    (out/"source").mkdir()
    for source in (ROOT/"mbrl").glob("*.py"):
        shutil.copy2(source,out/"source"/source.name)
    shutil.copy2(ROOT/"mbrl/viewer.html",out/"source/viewer.html")
    config=vars(args).copy()
    config.update(algorithm="simulator-alphazero-v2",valueScale=args.value_scale,
        capSeconds=args.cap_seconds,alpha=args.alpha,lambdaCost=args.lambda_cost,
        betaCongestion=args.beta_congestion,discount=args.discount,
        failurePenalty=args.failure_penalty,unansweredPenalty=args.unanswered_penalty,
        overcrowdingPenalty=args.overcrowding_penalty,tripReward=args.trip_reward,
        clearTripBonus=args.clear_trip_bonus,congestionFractionPenalty=args.congestion_fraction_penalty,
        congestionWaitThreshold=args.congestion_wait_threshold,
        observationSchema=OBSERVATION_SCHEMA,gridChannels=GRID_CHANNELS,
        searchValueBaseline="state-value-v1",checkpointSelection="latest",
        maxCandidates=MAX_CANDIDATES,rawCandidates=RAW_CANDIDATES,
        rootComparisonActions=ROOT_COMPARISON_ACTIONS,
        rootPolicyMode="post-comparison-visits-v1",
        safety=True, cooldowns={"driveway":args.driveway_cooldown,"motorway":args.motorway_cooldown,
                                "construction":args.construction_cooldown,"reversal_window":args.reversal_window},
        replayMixture={"demonstration":.35,"recent":.4,"successful":.25},
        experimentProtocol=SINGLE_CITY_PROTOCOL,city=args.city,
        trainingMaps=[args.city],validationMap=args.city,testMap=args.city,
        validationSeed=args.validation_seed,testSeed=args.test_seed,
        trainingSeedPolicy="random-without-replacement-excluding-held-out",
        hostSha256=hashlib.sha256(args.host_dll.read_bytes()).hexdigest(),
        sourceHashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (ROOT/"mbrl").glob("*.py")})
    (out/"config.json").write_text(json.dumps(config,indent=2,default=str),encoding="utf-8")
    rng=random.Random(1000)
    np.random.seed(1000)
    torch.manual_seed(1000)
    model=Network(value_scale=args.value_scale).to(args.device)
    optimizer=torch.optim.Adam(model.parameters(),lr=3e-4,weight_decay=1e-5)
    if args.init_checkpoint:
        state=torch.load(args.init_checkpoint,map_location=args.device,weights_only=False)
        model.load_compatible_state_dict(state["model"])
        # Rescale the value head when importing a legacy checkpoint.
        old_scale=state["config"].get("valueScale",10)
        with torch.no_grad():
            model.value[-1].weight.mul_(old_scale/args.value_scale)
            model.value[-1].bias.mul_(old_scale/args.value_scale)
    replay=ReplayMixture(args.replay_states)
    if args.resume_demonstration:
        resumed=demonstration_state
        if (resumed["episode"]!=0 or resumed["config"].get("valueScale",10)!=args.value_scale
                or resumed["config"].get("observationSchema")!=OBSERVATION_SCHEMA
                or resumed["config"].get("experimentProtocol")!=SINGLE_CITY_PROTOCOL
                or resumed["config"].get("city")!=args.city
                or resumed["config"].get("validationSeed")!=args.validation_seed
                or resumed["config"].get("testSeed")!=args.test_seed):
            parser.error("Continuation requires an episode-zero checkpoint with the same value scale")
        if (resumed["config"].get("failurePenalty",0)!=args.failure_penalty or
                resumed["config"].get("unansweredPenalty",0)!=args.unanswered_penalty or
                resumed["config"].get("overcrowdingPenalty",0)!=args.overcrowding_penalty or
                resumed["config"].get("lambdaCost",.005)!=args.lambda_cost or
                resumed["config"].get("tripReward",1)!=args.trip_reward or
                resumed["config"].get("clearTripBonus",0)!=args.clear_trip_bonus or
                resumed["config"].get("congestionFractionPenalty",0)!=args.congestion_fraction_penalty or
                resumed["config"].get("congestionWaitThreshold",2)!=args.congestion_wait_threshold):
            parser.error("Demonstration continuation requires matching reward penalties; use --init-checkpoint "
                         "and collect fresh demonstrations when changing rewards")
        model.load_state_dict(resumed["model"])
        optimizer.load_state_dict(resumed["optimizer"])
        rng.setstate(resumed["pythonRandom"])
        np.random.set_state(resumed["numpyRandom"])
        torch.set_rng_state(resumed["torchRandom"].cpu())
        replay.demonstrations=torch.load(args.demonstrations,map_location="cpu",weights_only=False)
        seed_cases.load_state_dict(resumed["trainingSeedSampler"])
    if args.resume:
        model.load_state_dict(resumed["model"])
        optimizer.load_state_dict(resumed["optimizer"])
        replay.load_state_dict(resumed["replay"])
        seed_cases.load_state_dict(resumed["trainingSeedSampler"])
        rng.setstate(resumed["pythonRandom"])
        np.random.set_state(resumed["numpyRandom"])
        torch.set_rng_state(resumed["torchRandom"].cpu())
    cooldowns=Cooldowns(args.driveway_cooldown,args.motorway_cooldown,args.construction_cooldown,args.reversal_window)
    best_metadata=resumed.get("bestObserved") if args.resume else None
    best_rank=tuple(best_metadata["rank"]) if best_metadata else None
    latest_metadata=resumed.get("latest") if args.resume else None
    no_improvement=resumed.get("noImprovement",0) if args.resume else 0
    examples_completed=resumed.get("trainingExamplesCompleted",0) if args.resume else 0
    started=time.perf_counter()
    def write_row(name,row):
        with (out/name).open("a",encoding="utf-8") as stream:
            stream.write(json.dumps(row)+"\n")
        print(json.dumps(row),flush=True)
    def trace(record,phase,episode):
        path=out/"traces"/f"{phase}-{episode}-{record['scenario']}-{record['seed']}.json"
        path.write_text(json.dumps(record),encoding="utf-8")
        if viewer is not None:
            viewer.save(path.with_suffix(".html"))
    def update(count,episode,phase):
        begun=time.perf_counter()
        metrics=[]
        for index in range(count):
            row=train_batch(model,optimizer,replay,batch_size=args.batch_size,rng=rng,
                policy_weight=args.policy_weight,value_weight=args.value_weight,value_loss=args.value_loss,
                return_metrics=True)
            row.update(episode=episode,phase=phase,update=index)
            with (out/"optimizer.jsonl").open("a",encoding="utf-8") as stream:
                stream.write(json.dumps(row)+"\n")
            metrics.append(row)
        return {key:float(np.mean([m[key] for m in metrics])) for key in metrics[0]
                if key not in ("episode","phase","update")}, time.perf_counter()-begun
    def state(episode):
        return {"model":model.state_dict(),"optimizer":optimizer.state_dict(),"config":config,
                "episode":episode,"pythonRandom":rng.getstate(),"numpyRandom":np.random.get_state(),
                "torchRandom":torch.get_rng_state(),"replay":replay.state_dict(),
                "trainingSeedSampler":seed_cases.state_dict(),"trainingExamplesCompleted":examples_completed,
                "bestObserved":best_metadata,"latest":latest_metadata,"noImprovement":no_improvement}
    print(f"Run directory: {out}",flush=True)
    print(f"Simulator host: {args.host_dll.resolve()}",flush=True)
    with viewer_context(args) as viewer, Host(dotnet=args.dotnet,dll=args.host_dll) as host, Host(dotnet=args.dotnet,dll=args.host_dll) as other, ExitStack() as workers:
        env=TrafficEnv(host,args.cap_seconds,alpha=args.alpha,lam=args.lambda_cost,beta=args.beta_congestion,
                       failure_penalty=args.failure_penalty,unanswered_penalty=args.unanswered_penalty,
                       overcrowding_penalty=args.overcrowding_penalty,trip_reward=args.trip_reward,
                       clear_trip_bonus=args.clear_trip_bonus,congestion_fraction_penalty=args.congestion_fraction_penalty,
                       congestion_wait_threshold=args.congestion_wait_threshold)
        branch=SnapshotBranch(other,env) if args.branch=="snapshot" else ReplayBranch(other,env)
        branch=workers.enter_context(SearchPool(branch,args.search_workers))
        def evaluate(episode):
            nonlocal best_rank,best_metadata,latest_metadata
            improved=False
            for budget in args.evaluation_budgets:
                mode="policy" if not budget else f"mcts{budget}"
                rows=[]
                for city,seed in [seed_cases.validation_case()]:
                    _,row,record=run_episode(env,branch,city,seed,model,budget,random.Random(seed+900000),False,
                        collect_samples=False,depth=args.search_depth,cooldowns=cooldowns,discount=args.discount,observer=viewer)
                    row.update(phase="validation",checkpointEpisode=episode,mode=mode)
                    write_row("validation.jsonl",row)
                    trace(record,f"validation-{mode}",episode)
                    rows.append(row)
                score=rank(rows)
                if budget==args.evaluation_budgets[0]:
                    latest_metadata={"episode":episode,"mode":mode,"simulations":budget,
                                     "rank":list(score),"rows":rows}
                if best_rank is None or score>best_rank:
                    improved=True
                    best_rank=score
                    best_metadata={"episode":episode,"mode":mode,"simulations":budget,
                                   "rank":list(score),"rows":rows}
            return improved
        for index in range(args.bootstrap_episodes):
            city,seed=seed_cases.training_case()
            samples,row,record=run_episode(env,branch,city,seed,model,0,rng,False,baseline=True,
                cooldowns=cooldowns,discount=args.discount,observer=viewer)
            replay.add(samples,row,demonstration=True)
            metrics,seconds=update(args.bootstrap_updates,index+1,"demonstration")
            row.update(phase="demonstration",episode=index+1,optimizer=metrics,updateWallSeconds=seconds)
            write_row("bootstrap.jsonl",row)
            trace(record,"demonstration",index+1)
        initial_episode=args.episode_offset
        atomic_save(state(initial_episode),out/"checkpoint-demonstration.pt")
        atomic_save(replay.demonstrations,out/"demonstrations.pt")
        atomic_save(state(initial_episode),out/"checkpoint-last.pt")
        for index in range(args.episodes):
            number=args.episode_offset+index+1
            city,seed=seed_cases.training_case()
            samples,row,record=run_episode(env,branch,city,seed,model,args.simulations,rng,True,
                depth=args.search_depth,cooldowns=cooldowns,discount=args.discount,observer=viewer)
            replay.add(samples,row)
            metrics,seconds=update(args.updates_per_episode,number,"train")
            row.update(phase="train",episode=number,optimizer=metrics,updateWallSeconds=seconds)
            write_row("training.jsonl",row)
            trace(record,"train",number)
            examples_completed+=1
            if examples_completed%args.validate_every==0:
                improved=evaluate(number)
                no_improvement=0 if improved else no_improvement+1
                atomic_save(state(number),out/f"checkpoint-episode-{number}.pt")
                atomic_save(state(number),out/"checkpoint-last.pt")
                if args.patience and no_improvement>=args.patience and index+1>=args.min_episodes:
                    print("Stopping: validation patience exhausted",flush=True)
                    break
            else:
                atomic_save(state(number),out/f"checkpoint-episode-{number}.pt")
                atomic_save(state(number),out/"checkpoint-last.pt")
        selection={"selected":{"episode":number,"checkpoint":str(out/"checkpoint-last.pt"),
                                "validation":latest_metadata if latest_metadata and latest_metadata["episode"]==number else None},
                   "latestValidation":latest_metadata,"checkpointSelection":"latest","bestObserved":best_metadata,
                   "trainingExamplesCompleted":examples_completed,"testDeferred":not args.final_test,
                   "wallSeconds":time.perf_counter()-started,"stopReason":"patience" if
                   args.patience and no_improvement>=args.patience else "episode-budget"}
        (out/"selection.json").write_text(json.dumps(selection,indent=2),encoding="utf-8")
        print(json.dumps(selection),flush=True)
        if args.final_test:
            for city,seed in [seed_cases.test_case()]:
                for heuristic in (True,False):
                    _,row,record=run_episode(env,branch,city,seed,model,args.evaluation_budgets[0],
                        random.Random(seed+900000),False,baseline=heuristic,collect_samples=False,
                        safety=not heuristic,depth=args.search_depth,cooldowns=cooldowns,discount=args.discount,observer=viewer)
                    row.update(policy="heuristic" if heuristic else "selected")
                    write_row("test.jsonl",row)
                    trace(record,"test-heuristic" if heuristic else "test-selected",number)


if __name__=="__main__":
    main()
