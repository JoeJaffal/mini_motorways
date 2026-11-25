"""Read-only probability/decision audit on a frozen development trajectory."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from environment import ROOT
from goal_agent import GoalEnv


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=int,default=900)
    p.add_argument('--comparison-checkpoint',type=Path,help='Optional paired initial-policy comparison instead of final.zip')
    a=p.parse_args()
    if a.output.exists():p.error('Fresh audit output required')
    torch.set_num_threads(2)
    paths={'initial':a.run/'initial.zip','final':a.comparison_checkpoint or a.run/'final.zip'}
    models={n:MaskablePPO.load(path,device='cpu') for n,path in paths.items()}
    if models['initial'].observation_space!=models['final'].observation_space:p.error('Comparison requires identical observation schemas')
    snapshots={n:[x.detach().clone() for x in m.policy.parameters()] for n,m in models.items()}
    from train_goal import model_environment
    env=model_environment(models['initial'],seconds=a.seconds,dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'))
    rows=[];forced=0
    try:
        obs,_=env.reset(seed=42,options={'scenario_seed':2000})
        while True:
            mask=env.action_masks();probs={}
            for name,m in models.items():
                with torch.no_grad():
                    probs[name]=m.policy.get_distribution(m.policy.obs_to_tensor(obs)[0],action_masks=mask).distribution.probs[0].cpu().numpy()
            if mask.sum()>1:
                x,y=probs['initial'],probs['final'];valid=mask & (x>0)
                rows.append(dict(time=env.base.raw['time'],legal_actions=int(mask.sum()),
                    initial_entropy=float(-np.sum(x[valid]*np.log(x[valid]))),
                    final_entropy=float(-np.sum(y[mask & (y>0)]*np.log(y[mask & (y>0)]))),
                    initial_max_probability=float(x.max()),final_max_probability=float(y.max()),
                    kl_initial_final=float(np.sum(x[valid]*np.log(x[valid]/np.maximum(y[valid],1e-30)))),
                    decision_changed=bool(x.argmax()!=y.argmax())))
            else:forced+=1
            obs,_,term,trunc,_=env.step(int(probs['initial'].argmax()))
            if term or trunc:break
        unchanged=all(all(torch.equal(x,y) for x,y in zip(snapshots[n],m.policy.parameters())) for n,m in models.items())
        if not unchanged:raise RuntimeError('Audit mutated weights')
        report=dict(run=str(a.run),protocol='Same states from frozen initial deterministic policy, development seed 2000 only; no training',
            weights_unchanged=True,forced_states=forced,choice_states=len(rows),
            decision_changes=sum(x['decision_changed'] for x in rows),
            mean_initial_entropy=float(np.mean([x['initial_entropy'] for x in rows])),
            mean_final_entropy=float(np.mean([x['final_entropy'] for x in rows])),
            mean_initial_max_probability=float(np.mean([x['initial_max_probability'] for x in rows])),
            mean_final_max_probability=float(np.mean([x['final_max_probability'] for x in rows])),
            mean_kl_initial_final=float(np.mean([x['kl_initial_final'] for x in rows])),
            comparison_checkpoint=str(paths['final']),
            checkpoint_sha256={n:hashlib.sha256(path.read_bytes()).hexdigest() for n,path in paths.items()},states=rows)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='states'},indent=2),flush=True)
    finally:env.close()


if __name__=='__main__':main()
