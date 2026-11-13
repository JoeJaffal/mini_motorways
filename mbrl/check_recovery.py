"""Regression checks for exact preflight, partial draws, cooldowns and loss balance."""
import argparse
import copy
import random
import os
import numpy as np
import torch
from actions import candidate_matrix, candidates
from alphazero import Network, Sample, ReplayMixture, train_batch, make_node, predict
from environment import Host, visible_grid, visible_scalar
from proposals import ActionGuard, Cooldowns
from smoke import observation


def checks(dotnet):
    obs=observation()
    for stock in (1,0,2):
        obs["inventory"][1]=stock
        cached=candidates(obs)
        previous=os.environ.get("TRAFFIC_DISABLE_PROPOSAL_CACHE")
        os.environ["TRAFFIC_DISABLE_PROPOSAL_CACHE"]="1"
        uncached=candidates(obs)
        if previous is None:
            os.environ.pop("TRAFFIC_DISABLE_PROPOSAL_CACHE")
        else:
            os.environ["TRAFFIC_DISABLE_PROPOSAL_CACHE"]=previous
        assert cached==uncached
    guard=ActionGuard(Cooldowns(driveway=20,motorway=30))
    after=copy.deepcopy(obs)
    after["buildings"][0]["drivewayDirection"]=2
    after["time"]=1
    action={"command":"driveway","id":0,"x":4,"y":5,"toX":4,"toY":6}
    guard.record(obs,after,action)
    reverse={"command":"driveway","id":0,"x":4,"y":5,"toX":5,"toY":5}
    assert not guard.allows(reverse,after)
    after["time"]=21
    assert not guard.allows(reverse,after)
    after["time"]=61
    assert guard.allows(reverse,after)
    returned=copy.deepcopy(after)
    returned["buildings"][0]["drivewayDirection"]=0
    guard.record(after,returned,reverse)
    assert guard.reversals==0
    # Copies used in hypothetical search must not contaminate actual history.
    branch=guard.clone()
    branch.driveways.clear()
    assert guard.driveways
    with Host(dotnet=dotnet) as host:
        root=host.call(command="reset",version="OriginalReference",scenario="EmptyLab",seed=42)["observation"]
        requests=[{"command":"draw","x":0,"y":10,"toX":49,"toY":10},
            {"command":"build","tool":"Road","x":0,"y":0},
            {"command":"build","tool":"Bridge","x":0,"y":0},
            {"command":"build","tool":"Roundabout","x":5,"y":5},
            {"command":"build","tool":"TrafficLight","x":5,"y":5},
            {"command":"build","tool":"Remove","x":0,"y":0},
            {"command":"connect","x":0,"y":0,"toX":1,"toY":0},
            {"command":"driveway","id":999,"x":0,"y":0,"toX":1,"toY":0},
            {"command":"motorway","x":0,"y":0,"toX":10,"toY":0},
            {"command":"editMotorway","id":999,"x":0,"y":0,"toX":10,"toY":0},
            {"command":"removeMotorway","id":999}, {"command":"upgrade","choice":999}]
        validity=host.call(command="validateActions",actions=requests)["validation"]
        assert host.call(command="observe")["observation"]==root
        assert validity[0]["accepted"] and validity[0]["changed"]
        host.call(command="saveSnapshot",id=5)
        for request, expected in zip(requests,validity):
            host.call(command="loadSnapshot",id=5)
            result=host.call(**request)
            assert result["accepted"]==expected["accepted"],request
        host.call(command="loadSnapshot",id=5)
        partial=host.call(**requests[0])
        built=sum(bool(x) for x in partial["observation"]["infrastructure"])
        assert partial["accepted"] and 0<built<50 and partial["observation"]["inventory"][0]==0
        repeated=host.call(command="validateActions",actions=[requests[0]])["validation"][0]
        assert repeated["accepted"] and not repeated["changed"]
    grid,scalar=visible_grid(obs),visible_scalar(obs)
    options,mask=candidate_matrix(candidates(obs))
    policy=np.zeros(len(mask),dtype=np.float32);policy[0]=1
    sample=Sample(grid,scalar,options,mask,policy,0,1000)
    torch.manual_seed(0)
    initial=Network(value_scale=100)
    results=[]
    for loss in ("mse","huber"):
        model=copy.deepcopy(initial)
        optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
        result=train_batch(model,optimizer,[[sample]],batch_size=2,rng=random.Random(0),
                           value_loss=loss,return_metrics=True)
        assert all(np.isfinite(x) for x in result.values())
        results.append(result)
    assert results[1]["valueLoss"]<results[0]["valueLoss"]
    assert results[1]["valueEncoderGradient"]<results[0]["valueEncoderGradient"]
    initial.eval()
    node=make_node(initial,obs,truncated=True)
    assert node.terminal and not node.edges and abs(node.value-predict(initial,obs,candidates(obs))[0])<1e-6
    replay=ReplayMixture(max_recent_states=2)
    replay.add([sample],{"map":"LosAngeles","trips":1},demonstration=True)
    for i in range(5):
        replay.add([sample],{"map":"LosAngeles","trips":i})
    assert len(replay.demonstrations)==1 and len(replay.recent)==2
    assert len(replay.sample(random.Random(0),32))==32
    print("PASS: native legality for every command, partial draws, isolation, cooldowns, normalized Huber gradients, replay mixture, truncation")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dotnet",default="dotnet")
    checks(p.parse_args().dotnet)
