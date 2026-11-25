from pathlib import Path
import json
import argparse
import torch
from sb3_contrib import MaskablePPO
from prepare_city_policy import sha256

torch.set_num_threads(1)
parser=argparse.ArgumentParser()
parser.add_argument('--run',type=Path,required=True)
root=parser.parse_args().run
state=json.loads((root/'state.json').read_text())
old=MaskablePPO.load('output/training/city-learning-start-01/start.zip',device='cpu')
old_state=old.policy.state_dict()
results=[]
for row in state['checkpoints']:
 path=root/row['path']
 assert sha256(path)==row['sha256']
 new=MaskablePPO.load(path,device='cpu')
 changes={key:float((value-old_state[key]).abs().max()) for key,value in new.policy.state_dict().items()}
 protected={k:v for k,v in changes.items() if not any(s in k for s in ('.growth_','value_net.'))}
 assert all(v==0 for v in protected.values())
 assert any(v>0 for k,v in changes.items() if '.growth_roads.' in k)
 assert any(v>0 for k,v in changes.items() if '.growth_grid.' in k)
 results.append(dict(path=str(path),changes=changes,optimizer_entries=len(new.policy.optimizer.state),decisions=new.num_timesteps))
(root/'update-audit.json').write_text(json.dumps(results,indent=2)+'\n')
print('Verified learned spatial weights changed and protected actor weights stayed exact')
