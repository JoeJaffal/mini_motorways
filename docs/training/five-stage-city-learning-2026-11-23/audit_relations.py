from pathlib import Path
import json,torch
from sb3_contrib import MaskablePPO
from prepare_city_policy import sha256

torch.set_num_threads(1)
a=Path('docs/training/five-stage-city-learning-2026-11-23')
rows=[]
for name in ['relations-01','relations-mixed-01']:
 run=Path('output/training/city-five-stage-'+name);cfg=json.loads((run/'config.json').read_text())
 old=MaskablePPO.load(cfg['parent'],device='cpu');before=old.policy.state_dict()
 for checkpoint in json.loads((run/'checkpoints.json').read_text()):
  path=Path(checkpoint['path']);assert sha256(path)==checkpoint['sha256']
  new=MaskablePPO.load(path,device='cpu')
  changes={k:float((v-before[k]).abs().max()) for k,v in new.policy.state_dict().items()}
  assert all(v==0 for k,v in changes.items() if not ('.growth_relations.' in k or k.startswith('value_net.')))
  assert any(v>0 for k,v in changes.items() if '.growth_relations.' in k)
  assert [n for n,p in new.policy.features_extractor.named_parameters() if p.requires_grad]==['growth_relations.weight']
  rows.append(dict(path=str(path),sha256=sha256(path),coefficients=new.policy.features_extractor.growth_relations.weight.detach().tolist(),changes=changes,optimizer_entries=len(new.policy.optimizer.state),group_scales=[g['lr_scale'] for g in new.policy.optimizer.param_groups]))
with (a/'relation-weight-audit.json').open('x') as f:json.dump(rows,f,indent=2)
print('All four relation saves update only the declared relation actor and critic; references preserved.')
