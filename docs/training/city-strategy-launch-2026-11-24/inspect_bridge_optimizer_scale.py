from pathlib import Path
import json,torch
from sb3_contrib import MaskablePPO
torch.set_num_threads(1)
p=Path('output/training/city-strategy-bridge-reference-city-01/segment-001/midpoint.zip')
m=MaskablePPO.load(p,device='cpu');groups=[]
for i,g in enumerate(m.policy.optimizer.param_groups):
 vals=[]
 for param in g['params']:
  s=m.policy.optimizer.state.get(param,{})
  if 'exp_avg_sq' in s:
   t=float(s['step']);vals.append((s['exp_avg_sq']/(1-g['betas'][1]**t)).sqrt().flatten())
 v=torch.cat(vals);rat=v/g['eps'];groups.append(dict(index=i,lr=g['lr'],lr_scale=g.get('lr_scale'),epsilon=g['eps'],parameters=len(v),sqrt_second_moment_over_epsilon_quantiles=torch.quantile(rat,torch.tensor([.1,.5,.9,.99])).tolist(),fraction_below_epsilon=float((rat<1).float().mean())))
out=Path('docs/training/city-strategy-launch-2026-11-24/bridge-reference-midpoint-optimizer-scale.json');assert not out.exists();out.write_text(json.dumps(dict(checkpoint=str(p),groups=groups,limit='Moment-to-epsilon ratio is a numerical diagnostic, not proof that a parameter should learn faster.'),indent=2)+'\n');print(out.read_text())
