"""Small development-only frozen-initial-policy comparison; never learns."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import torch
from sb3_contrib import MaskablePPO
from goal_agent import GoalEnv,GoalPolicy
from environment import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--count',type=int,default=3)
    p.add_argument('--seconds',type=int,default=1200)
    a=p.parse_args()
    if not 1<=a.count<=5 or a.seconds<=0:p.error('Use 1-5 development seeds and a positive time cap')
    if a.output.exists():p.error('Fresh output folder required')
    a.output.mkdir(parents=True);torch.set_num_threads(2)
    report=dict(protocol='Frozen informed initial policies, deterministic; development seeds 2000 onward; no learning. v2 paired ablation uses identical weights.',
                cap=a.seconds,seed_start=2000,arms={})
    for name,aware,alternatives in [('v1-live',False,False),('v2-no-bypass',True,False),('v2-bypass',True,True)]:
        env=GoalEnv(congestion_aware=aware,allow_alternatives=alternatives,
                    dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),seconds=a.seconds)
        try:
            model=MaskablePPO(GoalPolicy,env,device='cpu',seed=42,n_steps=8,batch_size=8)
            before=[v.detach().clone() for v in model.policy.parameters()]
            digest=hashlib.sha256(b''.join(v.cpu().numpy().tobytes() for v in before)).hexdigest()
            rows=[];best=-1;start=time.perf_counter()
            for seed in range(2000,2000+a.count):
                obs,_=env.reset(seed=seed,options={'scenario_seed':seed});offered=selected=0
                while True:
                    offered+=len(env.bypass_baselines)
                    action,_=model.predict(obs,deterministic=True,action_masks=env.action_masks())
                    selected+=int(int(action)-3 in env.bypass_baselines)
                    obs,_,term,trunc,info=env.step(action)
                    if term or trunc:break
                row={k:v for k,v in info.items() if k!='episode_replay'}
                row.update(seed=seed,bypass_offers=offered,bypass_selections=selected,terminated=term,truncated=trunc)
                rows.append(row)
                if info['trips']>best:
                    best=info['trips'];(a.output/f'{name}-best.json').write_text(json.dumps(env.export_replay(),indent=2)+'\n')
                print(f'{name} | seed {seed} | {info["trips"]} trips | bypass choices {selected} | offers {offered}',flush=True)
            unchanged=all(torch.equal(x,y) for x,y in zip(before,model.policy.parameters()))
            if not unchanged:raise RuntimeError('Frozen comparison mutated weights')
            report['arms'][name]=dict(initial_weights_sha256=digest,weights_unchanged=unchanged,
                mean_trips=sum(r['trips'] for r in rows)/len(rows),wall_seconds=time.perf_counter()-start,results=rows)
            (a.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:env.close()


if __name__=='__main__':main()
