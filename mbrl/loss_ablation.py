"""Compare normalized MSE and Huber on identical replay and an unseen training seed."""
import argparse
import copy
import json
import random
from pathlib import Path
import numpy as np
import torch
from alphazero import Network, ReplayMixture, train_batch
from environment import Host, SnapshotBranch, TrafficEnv
from experiment import atomic_save
from train import run_episode


@torch.no_grad()
def calibration(model,samples):
    model.eval()
    predicted=[]
    for start in range(0,len(samples),32):
        chunk=samples[start:start+32]
        arrays=[np.stack([getattr(s,name) for s in chunk]) for name in ("grid","scalar","options","mask")]
        inputs=[torch.as_tensor(a,dtype=torch.bool if index==3 else torch.float32) for index,a in enumerate(arrays)]
        value,_=model(*inputs)
        predicted.extend(value.tolist())
    target=np.asarray([s.value_target for s in samples])
    error=np.asarray(predicted)-target
    return {"rmse":float(np.sqrt(np.mean(error**2))),"bias":float(error.mean()),
            "explainedVariance":float(1-np.var(error)/max(1e-9,np.var(target)))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demonstrations",type=Path,required=True)
    parser.add_argument("--legacy-checkpoint",type=Path,required=True)
    parser.add_argument("--updates",type=int,default=384)
    parser.add_argument("--dotnet",default="dotnet")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--holdout-only",action="store_true")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    demonstrations=torch.load(args.demonstrations,map_location="cpu",weights_only=False)
    replay=ReplayMixture()
    replay.demonstrations=demonstrations
    old=torch.load(args.legacy_checkpoint,map_location="cpu",weights_only=False)
    legacy=Network(value_scale=old["config"].get("valueScale",10))
    legacy.load_compatible_state_dict(old["model"])
    with Host(dotnet=args.dotnet) as host,Host(dotnet=args.dotnet) as other:
        env=TrafficEnv(host,cap_seconds=1800,lam=old["config"].get("lambdaCost",.005),
                       failure_penalty=old["config"].get("failurePenalty",0),
                       unanswered_penalty=old["config"].get("unansweredPenalty",0),
                       overcrowding_penalty=old["config"].get("overcrowdingPenalty",0),
                       trip_reward=old["config"].get("tripReward",1.0),
                       clear_trip_bonus=old["config"].get("clearTripBonus",0.),
                       congestion_fraction_penalty=old["config"].get("congestionFractionPenalty",0.),
                       congestion_wait_threshold=old["config"].get("congestionWaitThreshold",2.))
        branch=SnapshotBranch(other,env)
        heldout,row,_=run_episode(env,branch,"LosAngeles",100090,legacy,0,random.Random(900090),False,
            baseline=True,collect_samples=True,discount=.999)
    results={"heldoutScenario":row,"legacyLongReturnCalibration":calibration(legacy,heldout)}
    atomic_save(heldout,args.output/"heldout.pt")
    if args.holdout_only:
        (args.output/"results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
        print(json.dumps(results),flush=True)
        return
    torch.manual_seed(1000)
    initial=Network(value_scale=100)
    for loss in ("mse","huber"):
        model=copy.deepcopy(initial)
        optimizer=torch.optim.Adam(model.parameters(),lr=3e-4,weight_decay=1e-5)
        rng=random.Random(1000)
        metrics=[]
        for _ in range(args.updates):
            metrics.append(train_batch(model,optimizer,replay,rng=rng,value_loss=loss,return_metrics=True))
        result={"calibration":calibration(model,heldout),
                "early":{key:float(np.mean([r[key] for r in metrics[:32]])) for key in metrics[0]},
                "late":{key:float(np.mean([r[key] for r in metrics[-32:]])) for key in metrics[0]}}
        results[loss]=result
        config={"valueScale":100,"capSeconds":1800,"alpha":.05,"lambdaCost":env.lam,
                "discount":.999,"safety":True,"valueLoss":loss,
                "failurePenalty":env.failure_penalty,"unansweredPenalty":env.unanswered_penalty,
                "overcrowdingPenalty":env.overcrowding_penalty,"tripReward":env.trip_reward,
                "clearTripBonus":env.clear_trip_bonus,"congestionFractionPenalty":env.congestion_fraction_penalty,
                "congestionWaitThreshold":env.congestion_wait_threshold,
                "observationSchema":"traffic-risk-v3","gridChannels":42}
        atomic_save({"model":model.state_dict(),"config":config,"episode":0},args.output/f"checkpoint-{loss}.pt")
        (args.output/"results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
        print(json.dumps({"valueLoss":loss,**result}),flush=True)


if __name__=="__main__":
    main()
