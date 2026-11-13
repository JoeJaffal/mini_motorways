"""Native replay compatibility check; never trains or opens held-out seeds."""
import argparse
import random
from pathlib import Path
import torch
from environment import Host, TrafficEnv, ReplayBranch, HOST_DLL, ProtocolError
from alphazero import Network, search
from proposals import ActionGuard


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet',default='dotnet')
    parser.add_argument('--host-dll',type=Path,default=HOST_DLL)
    args=parser.parse_args()
    torch.set_num_threads(1)
    forbidden={'saveSnapshot','loadSnapshot','forkFuture','validateActions'}
    commands=[]
    class CheckedHost(Host):
        def call(self,**request):
            assert request['command'] not in forbidden,request
            commands.append(request['command'])
            return super().call(**request)
    with CheckedHost(args.dotnet,args.host_dll) as live_host, CheckedHost(args.dotnet,args.host_dll) as other:
        env=TrafficEnv(live_host,cap_seconds=5)
        env.reset('LosAngeles',42)
        branch=ReplayBranch(other,env)
        model=Network(value_scale=100)
        tracker=ActionGuard()
        history=[]
        for decision in range(4):
            before=live_host.call(command='observe')['observation']
            items,visits,stats=search(model,env,branch,history,8,3,random.Random(42+decision),guard=tracker)
            assert stats['maxDepthReached']>0
            assert live_host.call(command='observe')['observation']==before,'Search mutated live host'
            action=items[max(range(len(items)),key=lambda i:visits[i])].request
            result=env.step(action)
            tracker.record(before,result.observation,action,result.accepted)
            history.append(action)
            branch.restore(history,result.observation)
        damaged=dict(env.observation);damaged['time']+=1
        try: branch.restore(history,damaged)
        except ProtocolError: pass
        else: raise AssertionError('Replay divergence was not detected')
    assert not forbidden.intersection(commands)
    print('PASS: native multi-decision MCTS, checked replay, live-host isolation, divergence detection; no snapshots, preflight, future fork or training')

if __name__=='__main__': main()
