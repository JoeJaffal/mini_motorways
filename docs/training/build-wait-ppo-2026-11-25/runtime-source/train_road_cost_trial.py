"""Bounded reward comparison; raw native scores remain separate from PPO return."""
from pathlib import Path
from functools import partial
import argparse,json,math,time,shutil
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.logger import configure
from city_road_cost_env import CityRoadCostEnv
from prepare_city_policy import sha256
from train_city_curriculum import optimizer_steps
from city_gradient_audit import GradientAudit

FIELDS=('seed','exercise','trips','road_stock','stock_initial','paid_units','road_cost','native_return','shaped_return','road_actions','wait_actions')
def worker(dll,rank,cost,seed):
 return Monitor(CityRoadCostEnv(dll,road_cost=cost,worker=rank,workers=16,seed_start=seed,collapse_forced_wait=True),info_keywords=FIELDS)
class Episodes(BaseCallback):
 def __init__(self,path):super().__init__();self.path=path;self.rows=[]
 def _on_step(self):
  for info in self.locals['infos']:
   if 'episode' not in info:continue
   e=info['episode'];expected=e['native_return']-e['road_cost']*e['paid_units']
   if e['native_return']!=e['trips'] or not math.isclose(e['r'],expected,abs_tol=2e-5):raise RuntimeError('Cost/native episode ledger mismatch')
   row=dict(decisions=self.num_timesteps,**e);self.rows.append(row)
   with self.path.open('a') as f:f.write(json.dumps(row)+'\n')
  return True

def main():
 p=argparse.ArgumentParser()
 for name in ['dll','parent','output']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--road-cost',type=float,required=True);p.add_argument('--seed-start',type=int,default=198000000)
 a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True);torch.set_num_threads(1)
 config=dict(parent=str(a.parent),parent_sha256=sha256(a.parent),dll=str(a.dll),host_sha256=sha256(a.dll),road_cost=a.road_cost,seed_start=a.seed_start,workers=16,rollout_steps=512,rollouts=2,decision_budget=16384,learning_rate=.0003,vf_coef=.00001,gamma=1,gae_lambda=1,n_epochs=4,batch_size=128)
 (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
 env=SubprocVecEnv([partial(worker,a.dll,i,a.road_cost,a.seed_start) for i in range(16)],start_method='forkserver')
 try:
  model=MaskablePPO.load(a.parent,env=env,device='cuda',learning_rate=.0003,n_steps=512,batch_size=128,gamma=1.,gae_lambda=1.,vf_coef=.00001)
  if model.ep_info_buffer is not None:model.ep_info_buffer.clear()
  if model.ep_success_buffer is not None:model.ep_success_buffer.clear()
  model.set_logger(configure(str(a.output),['csv']));start=model.num_timesteps;initial_updates=optimizer_steps(model);t=time.monotonic();saves=[];callback=Episodes(a.output/'episodes.jsonl')
  audit=GradientAudit(model.policy.optimizer,a.output/'gradient_audit.jsonl',64)
  for rollout in range(2):
   model.learn(total_timesteps=8192,reset_num_timesteps=False,callback=callback)
   audit.close()
   if not all(math.isfinite(float(model.logger.name_to_value[k])) for k in ['train/loss','train/value_loss','train/approx_kl']):raise RuntimeError('Nonfinite PPO metrics')
   model.logger.dump(step=model.num_timesteps)
   name='midpoint' if rollout==0 else 'final';path=a.output/f'{name}.zip';pending=a.output/f'{name}.pending.zip';model.save(pending);pending.replace(path)
   row=dict(checkpoint=str(path),sha256=sha256(path),added_decisions=model.num_timesteps-start,optimizer_steps=optimizer_steps(model)-initial_updates,episodes=len(callback.rows),seconds=time.monotonic()-t);saves.append(row)
   (a.output/'checkpoints.json').write_text(json.dumps(saves,indent=2)+'\n')
   recent=callback.rows[-100:];mean=lambda k:sum(x[k] for x in recent)/len(recent)
   print(f"PPO | cost={a.road_cost} | {row['added_decisions']} decisions | {row['optimizer_steps']} updates | native deliveries={mean('trips'):.3f} | shaped return={mean('r'):.3f} | paid roads={mean('paid_units'):.3f}",flush=True)
  assert model.num_timesteps-start==16384
  assert sha256(a.parent)==config['parent_sha256'] and sha256(a.dll)==config['host_sha256']
  (a.output/'complete.json').write_text(json.dumps(dict(checkpoints=saves,seconds=time.monotonic()-t),indent=2)+'\n')
 finally:env.close()
if __name__=='__main__':main()
