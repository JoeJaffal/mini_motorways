"""Root comparison selection, strong-prior coverage and parallel opening waves."""
import argparse
import random
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from actions import Candidate, _features
from alphazero import Edge, Network, Node, root_comparison_indices, root_policy, search
from environment import HOST_DLL, Host, SnapshotBranch, TrafficEnv
from parallel_search import SearchPool
from proposals import ActionGuard, key
from train import choose, run_episode


def selection_checks():
    requests = [
        {"command":"wait"},
        {"command":"connect","x":2,"y":2,"toX":3,"toY":3},
        {"command":"connect","x":2,"y":2,"toX":3,"toY":2},
        {"command":"draw","x":5,"y":5,"toX":8,"toY":5},
        {"command":"build","tool":"Road","x":9,"y":9}]
    items = [Candidate(r,str(i),_features(0)) for i,r in enumerate(requests)]
    root = Node({},items,0,[Edge(p) for p in (.001,.65,.25,.07,.029)])
    assert root_comparison_indices(root,16)==[0,1,3,4]
    for budget in (0,1,2,3,4,16):
        selected = root_comparison_indices(root,budget)
        assert len(selected)==min(4,budget)
    root.items[2] = Candidate({"command":"connect","x":3,"y":3,"toX":2,"toY":2},'reverse',_features(0))
    selected = root_comparison_indices(root,16)
    assert len({key(root.items[i].request) for i in selected})==len(selected)
    lone = Node({},items[:1],0,[Edge(1)])
    assert root_comparison_indices(lone,16)==[0]


def policy_checks():
    # Reproduce the regression pattern: a probe-only construction had 1/16 mass.
    policy,support,mode=root_policy([13,1,1,1],[0,1,2,3],[.9,.04,.03,.03])
    assert support.tolist()==[12,0,0,0] and policy.tolist()==[1,0,0,0]
    assert mode=='postComparisonVisits'
    rng=random.Random(9)
    assert all(choose(policy,np.ones(4,dtype=bool),rng,True)==0 for _ in range(100))
    # A promising comparison can still earn further visits and teach a new choice.
    policy,support,_=root_policy([4,10,1,1],[0,1,2,3],[.9,.04,.03,.03])
    assert support.tolist()==[3,9,0,0] and np.allclose(policy,[.25,.75,0,0])
    draws=[choose(policy,np.ones(4,dtype=bool),rng,True) for _ in range(1000)]
    assert set(draws)=={0,1} and .15<draws.count(0)/1000<.35
    # Without opening comparisons, preserve ordinary visit-proportional training.
    policy,_,_=root_policy([7,1,0],[],[.8,.1,.1])
    assert np.allclose(policy,[.875,.125,0])
    # An opening-only budget falls back to priors among visited actions, not uniform probes.
    policy,support,mode=root_policy([1,1,0],[0,1],[.1,.3,.6])
    assert np.allclose(policy,[.25,.75,0]) and not support.any() and mode=='priorFallback'
    policy,_,_=root_policy([1,0],[0],[0,1])
    assert policy.tolist()==[1,0]
    policy,_,_=root_policy([0,0],[],[.5,.5])
    assert not policy.any() and np.isfinite(policy).all()


def checks(dotnet,host_dll):
    selection_checks()
    policy_checks()
    torch.set_num_threads(1)
    model = Network(value_scale=100)

    def confident_wait(model,observation,items):
        priors = np.full(len(items),1e-9,dtype=np.float64)
        priors[0]=1
        return 0.0,priors/priors.sum()

    with Host(dotnet=dotnet,dll=host_dll) as host, Host(dotnet=dotnet,dll=host_dll) as other:
        env=TrafficEnv(host,cap_seconds=4)
        for workers in (1,2,3,6):
            root=env.reset('LosAngeles',100000)
            with SearchPool(SnapshotBranch(other,env),workers) as pool:
                pool.start(root)
                for budget in (1,2,3,4,16):
                    events=[]
                    guard=ActionGuard()
                    def observe(kind,observation,**event):
                        if event.get('depth')==1:
                            events.append(event['action'])
                    with patch('alphazero.predict',side_effect=confident_wait):
                        items,visits,stats=search(model,env,pool,[],budget,4,random.Random(21),
                            guard=guard,observer=observe)
                    target=min(4,budget,len(items))
                    assert stats['rootComparisonActions']==target
                    assert stats['rootComparisonActionsVisited']==target
                    assert stats['rootActionsVisited']>=target
                    assert len({key(a) for a in events[:target]})==target
                    assert events[0]['command']=='wait'
                    assert visits.sum()==budget
                    assert sum(r['visits'] for r in stats['rootActionStats'])==budget
                    assert sum(r['initialComparison'] for r in stats['rootActionStats'])==target
                    assert all(np.isfinite(r['meanReturn']) for r in stats['rootActionStats'])
                    assert np.isclose(sum(stats['rootPolicy']),1)
                    if stats['rootPolicySource']=='postComparisonVisits':
                        assert all(r['policyWeight']==0 for r in stats['rootActionStats']
                                   if r['initialComparison'] and r['visits']==1)
                    assert host.call(command='observe')['observation']==root
                    assert not guard.driveways and not guard.rejected
                    # Repeating with the same worker count has stable reservation/backup order.
                    with patch('alphazero.predict',side_effect=confident_wait):
                        _,again,repeated=search(model,env,pool,[],budget,4,random.Random(21),guard=guard)
                    assert np.array_equal(visits,again) and stats==repeated
                if workers==2:
                    with patch('alphazero.predict',side_effect=confident_wait):
                        samples,_,record=run_episode(env,pool,'LosAngeles',100000,model,16,
                            random.Random(17),True,collect_samples=True,progress_every=0)
                    for sample,action in zip(samples,record['actions']):
                        assert np.allclose(sample.policy[:len(action['search']['rootPolicy'])],
                                           action['search']['rootPolicy'])
                        for row in action['search']['rootActionStats']:
                            if row['initialComparison'] and row['visits']==1:
                                assert sample.policy[row['index']]==0
    print('PASS: diverse alternatives, duplicate filtering, 1/2/3/4/16 budgets, serial and 2/3/6 workers, '
          'strong-prior coverage, opening reservation uniqueness, corrected policy targets, stochastic selection, visit/Q logs and isolation')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dotnet',default='dotnet')
    parser.add_argument('--host-dll',type=Path,default=HOST_DLL)
    args=parser.parse_args()
    checks(args.dotnet,args.host_dll)
