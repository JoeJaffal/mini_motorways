import argparse,json
from pathlib import Path
import torch
from sb3_contrib import MaskablePPO
from city_learning_policy import CityLearningPolicy
from city_exploration_policy import CityResidualExplorationFeatures
from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256
p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--dll',required=True);p.add_argument('--temperature',type=float,default=8.);args=p.parse_args()
torch.set_num_threads(1);args.output.mkdir(parents=True,exist_ok=False)
env=CityRoadEnv(args.dll)
try:
 old=MaskablePPO.load(args.parent,device='cpu')
 new=MaskablePPO(CityLearningPolicy,env,device='cpu',n_steps=128,batch_size=64,n_epochs=4,learning_rate=1e-4,gamma=1.,gae_lambda=.95,ent_coef=.01,target_kl=.03,
  policy_kwargs=dict(features_extractor_class=CityResidualExplorationFeatures,features_extractor_kwargs=dict(conservative=True,temperature=args.temperature),normalize_images=False))
 missing,extra=new.policy.load_state_dict(old.policy.state_dict(),strict=False)
 assert not extra and len(missing)==3 and all(k.endswith('.growth_road_temperature') for k in missing)
 new.policy.optimizer.load_state_dict(old.policy.optimizer.state_dict())
 new.num_timesteps=old.num_timesteps;new._n_updates=old._n_updates
 new.save(args.output/'start.zip')
 (args.output/'config.json').write_text(json.dumps(dict(source=str(args.parent),source_sha256=sha256(args.parent),initial_sha256=sha256(args.output/'start.zip'),temperature=args.temperature,optimizer_entries=len(new.policy.optimizer.state)),indent=2)+'\n')
finally:env.close()
