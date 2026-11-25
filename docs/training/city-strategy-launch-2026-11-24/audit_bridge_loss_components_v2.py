"""Collect a diagnostic rollout, measure PPO loss gradients, perform no updates."""
from pathlib import Path
from functools import partial
import json,torch,numpy as np
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv
from train_city_curriculum import worker,optimizer_steps
class Finished(Exception):pass
class Audit(BaseCallback):
 def _on_step(self):return True
 def _on_rollout_end(self):
  m=self.model;groups=m.policy.optimizer.param_groups;params=[p for g in groups for p in g['params']];rows=[]
  reference=MaskablePPO.load('output/training/city-strategy-wide-initial-01/start.zip',device='cuda')
  probability_rows=[]
  for data in m.rollout_buffer.get(128):
   values,logp,entropy=m.policy.evaluate_actions(data.observations,data.actions.long().flatten(),action_masks=data.action_masks)
   p=m.policy.action_dist.distribution.probs.detach()
   with torch.no_grad():q=reference.policy.get_distribution(data.observations,action_masks=data.action_masks).distribution.probs
   a=p[:,1:]/p[:,1:].sum(1,keepdim=True).clamp_min(1e-20);b=q[:,1:]/q[:,1:].sum(1,keepdim=True).clamp_min(1e-20)
   valid=data.action_masks[:,1:].sum(1)>=2
   for j in torch.where(valid)[0].tolist():
    probability_rows.append(dict(wait_change=float(p[j,0]-q[j,0]),road_total_variation=float((a[j]-b[j]).abs().sum()/2),reference_top_road=float(b[j].max()),candidate_top_road=float(a[j].max()),legal_roads=int(data.action_masks[j,1:].sum())))
   adv=data.advantages;adv=(adv-adv.mean())/(adv.std()+1e-8)
   ratio=torch.exp(logp-data.old_log_prob)
   policy=-torch.min(adv*ratio,adv*torch.clamp(ratio,.8,1.2)).mean()
   ent=-entropy.mean()*m.ent_coef;value=torch.nn.functional.mse_loss(values.flatten(),data.returns)*m.vf_coef
   grads=[]
   for loss in (policy,ent,value):
    g=torch.autograd.grad(loss,params,retain_graph=True,allow_unused=True)
    grads.append([torch.zeros_like(p) if v is None else v for p,v in zip(params,g)])
   row=dict(losses=[float(x.detach()) for x in (policy,ent,value)],groups=[]);offset=0
   for i,group in enumerate(groups):
    n=len(group['params']);vec=[torch.cat([v.flatten() for v in gs[offset:offset+n]]) for gs in grads];norm=[float(v.norm()) for v in vec];cos=float(torch.dot(vec[0],vec[1])/(vec[0].norm()*vec[1].norm()).clamp_min(1e-20))
    row['groups'].append(dict(index=i,policy_norm=norm[0],weighted_entropy_norm=norm[1],weighted_value_norm=norm[2],policy_entropy_cosine=cos,policy_value_cosine=float(torch.dot(vec[0],vec[2])/(vec[0].norm()*vec[2].norm()).clamp_min(1e-20))));offset+=n
   rows.append(row)
  self.rows=rows;self.probability_rows=probability_rows;raise Finished()
if __name__=='__main__':
 torch.set_num_threads(1);torch.manual_seed(16924);np.random.seed(16924)
 root=Path.cwd();out=root/'docs/training/city-strategy-launch-2026-11-24/bridge-loss-components-v2.json';assert not out.exists()
 dll='output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll';path='output/training/city-strategy-bridge-reference-city-01/segment-001/final.zip'
 env=SubprocVecEnv([partial(worker,dll,'city',i,4,169000000,True,1200,False,0,None,True) for i in range(4)],start_method='forkserver')
 try:
  m=MaskablePPO.load(path,env=env,device='cuda',n_steps=512,batch_size=128)
  before={k:v.clone() for k,v in m.policy.state_dict().items()};steps=optimizer_steps(m);a=Audit()
  try:m.learn(total_timesteps=2048,callback=a,reset_num_timesteps=False)
  except Finished:pass
  assert optimizer_steps(m)==steps and all(torch.equal(v,m.policy.state_dict()[k]) for k,v in before.items())
  summary=[dict(index=i,**{k:float(np.mean([r['groups'][i][k] for r in a.rows])) for k in ['policy_norm','weighted_entropy_norm','weighted_value_norm','policy_entropy_cosine','policy_value_cosine']}) for i in range(4)]
  out.write_text(json.dumps(dict(checkpoint=path,training_seed_start=169000000,decisions=2048,optimizer_updates=0,weights_exact=True,groups=summary,batches=a.rows,probability_samples=a.probability_rows,probability_summary={k:dict(mean=float(np.mean([r[k] for r in a.probability_rows])),median=float(np.median([r[k] for r in a.probability_rows]))) for k in a.probability_rows[0]},limit='One rollout and16 minibatches; gradient norms are diagnostic, not causal proof of score effects.'),indent=2)+'\n');print(json.dumps(summary,indent=2))
 finally:env.close()
