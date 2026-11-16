"""Check specification arithmetic, architecture and review provenance. No training."""
import json, math
from pathlib import Path
import torch
from torch import nn

folder=Path(__file__).resolve().parent
cfg=json.loads((folder/'CONFIG.json').read_text())
rows=json.loads((folder/'decisions.json').read_text())
assert all(r['decision']=='Done' for r in rows)
assert sum(r['review']=='Not reviewed' for r in rows)==33
assert cfg['training_authorized'] is False
static=[1,3,5,8,1,3,8,9,3,2,2,2,1,4,2,3]
assert sum(static)==57 and sum(static)+4*6==81
assert sum([6,18,4,6,10,1,8,1])==54
ppo=cfg['ppo']; rollout=ppo['n_steps']*cfg['workers']
assert rollout==2048 and rollout%ppo['batch_size']==0
assert ppo['gamma']==1 and cfg['tick_seconds']*cfg['wait_ticks']==1
assert cfg['pilot']['tokens']%rollout==0
torch.manual_seed(42)
torch.set_num_threads(2)
grid=nn.Sequential(nn.Conv2d(81,32,3,1,1),nn.ReLU(),nn.Conv2d(32,64,3,2,1),nn.ReLU(),nn.Conv2d(64,64,3,2,1),nn.ReLU(),nn.AdaptiveAvgPool2d((4,7)),nn.Flatten(),nn.Linear(1792,256),nn.ReLU())
global_net=nn.Sequential(nn.Linear(54,64),nn.ReLU())
pairs=nn.Sequential(nn.Linear(6,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU())
shared=nn.Sequential(nn.Linear(384,256),nn.ReLU())
actor=nn.Sequential(nn.Linear(256,128),nn.ReLU(),nn.Linear(128,1501))
critic=nn.Sequential(nn.Linear(256,128),nn.ReLU(),nn.Linear(128,1))
modules=[grid,global_net,pairs,shared,actor,critic]
with torch.no_grad():
    g=grid(torch.zeros(2,81,30,50));v=global_net(torch.zeros(2,54))
    p=pairs(torch.zeros(2,1500,6));valid=torch.zeros(2,1500,dtype=torch.bool)
    # Empty records must contribute zero after masking, including MLP biases.
    means=(p*valid.unsqueeze(-1)).sum(1)/valid.sum(1,keepdim=True).clamp_min(1)
    maxima=p.masked_fill(~valid.unsqueeze(-1),float('-inf')).amax(1)
    maxima=torch.where(valid.any(1,keepdim=True),maxima,torch.zeros_like(maxima))
    pair_features=torch.cat([means,maxima],1)
    features=shared(torch.cat([g,v,pair_features],1))
    logits=actor(features);values=critic(features)
    assert logits.shape==(2,1501) and values.shape==(2,1)
    assert torch.isfinite(logits).all() and torch.isfinite(values).all()
    assert torch.count_nonzero(pair_features)==0
    mask=torch.zeros_like(logits,dtype=torch.bool);mask[:,0]=True
    probs=torch.softmax(logits.masked_fill(~mask,float('-inf')),1)
    assert torch.all(probs[:,0]==1) and torch.all(probs[:,1:]==0)
counts={name:sum(p.numel() for p in mod.parameters()) for name,mod in zip(['grid','global','pairs','shared','actor','critic'],modules)}
result={'date':'2026-11-16','checks':['all51design records selected','33new decisions remain Not reviewed;18prior approvals preserved by selection script','schema channel arithmetic','disjoint city/seed splits checked by selection script','batch/rollout/pilot divisibility','one-second tick arithmetic','architecture forward shapes','empty pair masking','one-valid-action normalization','finite logits/values'], 'parameter_counts':counts,'total_parameters':sum(counts.values()),'rollout_tokens':rollout,'minibatches_per_epoch':rollout//ppo['batch_size'],'optimizer_steps_per_full_rollout':rollout//ppo['batch_size']*ppo['n_epochs'],'pilot_max_full_rollouts':cfg['pilot']['tokens']//rollout,'estimated_float32_rollout_bytes':{'grid':rollout*81*30*50*4,'motorway_table':rollout*1500*6*4,'global':rollout*54*4},'limits':['Random synthetic forward only; no optimizer step, training or saved weights','No simulator episodes, new masks or adapter implemented','Memory figures are source arithmetic, not peak measurement','User review remains outstanding']}
(folder/'SPEC_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
