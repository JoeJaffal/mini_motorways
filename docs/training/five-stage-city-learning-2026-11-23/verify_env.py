"""Reproduce visible-branch, reward-ledger and native host compatibility checks."""
from pathlib import Path
import argparse,json
import torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv,LESSONS
from city_road_pilot import CityRoadEnv,FIXTURE_ROAD,edge_action

p=argparse.ArgumentParser();p.add_argument('--dll',required=True);p.add_argument('--old-dll',required=True);p.add_argument('--checkpoint',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
torch.set_num_threads(1)
model=MaskablePPO.load(args.checkpoint,device='cpu')
env=CityCurriculumEnv(args.dll);rows=[]
try:
 for exercise in LESSONS:
  for split in ('train','validation'):
   env.split=split;obs,info=env.reset(options=dict(scenario_seed=118100001,exercise=exercise))
   tensor,_=model.policy.obs_to_tensor(obs)
   with torch.no_grad():gate=bool(model.policy.features_extractor.service_features(tensor['grid'])[-2])
   assert env.observation_space.contains(obs) and gate
   total=0
   while not env.done:
    obs,reward,_,_,info=env.step(0);total+=reward
   assert total==info['trips']==sum(info['served'].values())
   rows.append(dict(exercise=exercise,split=split,gate=gate,wait=info))
finally:env.close()
old,new=CityRoadEnv(args.old_dll),CityRoadEnv(args.dll);count=0
try:
 for seed in [2004,99161630]:
  old.reset(options={'scenario_seed':seed});new.reset(options={'scenario_seed':seed});assert old.raw==new.raw
  for action in ([edge_action(x,y) for x,y in zip(FIXTURE_ROAD,FIXTURE_ROAD[1:])] if seed==2004 else []):
   old.step(action);new.step(action);assert old.raw==new.raw;count+=1
  while not old.done:
   assert (old.action_masks()==new.action_masks()).all()
   old.step(0);new.step(0);assert old.raw==new.raw;count+=1
  assert new.done
finally:old.close();new.close()
with args.output.open('x') as f:json.dump(dict(fixtures=rows,exact_city_transitions=count),f,indent=2)
