import json
from pathlib import Path
import torch,numpy as np
from sb3_contrib import MaskablePPO
from prepare_city_policy import sha256
r=Path('docs/training/mini-task-repair-2026-11-25');torch.set_num_threads(1)
paths={'original':'output/training/city-whole-initial-01/start.zip','previous-final':'output/training/expansion-comparison-01/expansion/final.zip','reset-65536':'output/training/mini-reset-comparison-01/reset-curriculum/checkpoint-000065536.zip'}
rows=[]
for label,path in paths.items():
 m=MaskablePPO.load(path,device='cpu');opt=m.policy.optimizer
 for i,g in enumerate(opt.param_groups):
  vals=[];updates=[];steps=[]
  for p in g['params']:
   s=opt.state.get(p,{})
   if 'exp_avg_sq' not in s:continue
   n=int(s['step']);steps.append(n);b1,b2=g['betas'];v=(s['exp_avg_sq']/(1-b2**n)).sqrt();mu=s['exp_avg']/(1-b1**n)
   vals.append(v.flatten());updates.append((g['lr']*g.get('lr_scale',1)*mu/(v+g['eps'])).abs().flatten())
  row=dict(model=label,group=i,base_lr=g['lr'],lr_scale=g.get('lr_scale',1),eps=g['eps'],parameters=sum(p.numel() for p in g['params']),steps=sorted(set(steps)),weight_decay=g.get('weight_decay',0))
  if vals:
   v=torch.cat(vals);u=torch.cat(updates);row.update(median_gradient_rms=float(v.median()),fraction_rms_below_epsilon=float((v<g['eps']).float().mean()),median_last_update_magnitude=float(u.median()),last_update_norm=float(u.norm()))
  rows.append(row)
(r/'optimizer-inspection.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
