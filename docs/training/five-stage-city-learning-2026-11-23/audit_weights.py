"""Verify optimizer activity, frozen actor retention, and archive exact changes."""
import argparse,json
from pathlib import Path
import torch
from sb3_contrib import MaskablePPO
from prepare_city_policy import sha256
p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--checkpoints',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
torch.set_num_threads(1)
old=MaskablePPO.load(args.parent,device='cpu');before=old.policy.state_dict();rows=[]
for path in args.checkpoints:
 new=MaskablePPO.load(path,device='cpu');changes={k:float((v-before[k]).abs().max()) for k,v in new.policy.state_dict().items()}
 allowed=lambda k:'opening_reference' not in k and ('.growth_' in k or k.startswith('value_net.'))
 assert all(v==0 for k,v in changes.items() if not allowed(k))
 assert any(v>0 for k,v in changes.items() if '.growth_roads.' in k and allowed(k))
 assert all(not p.requires_grad for p in new.policy.features_extractor.opening_reference.parameters())
 rows.append(dict(path=str(path),sha256=sha256(path),num_timesteps=new.num_timesteps,optimizer_entries=len(new.policy.optimizer.state),changes=changes))
with args.output.open('x') as f:json.dump(dict(parent=str(args.parent),parent_hash=sha256(args.parent),saves=rows),f,indent=2)
print('Verified frozen reference and actual spatial updates for',len(rows),'saves')
