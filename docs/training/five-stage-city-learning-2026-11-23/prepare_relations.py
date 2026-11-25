from pathlib import Path
import argparse,json,torch
from sb3_contrib import MaskablePPO
from city_relational_policy import CityRelationalPolicy,CityRelationalFeatures,CityDemandRelationsFeatures,RelativeRateAdam
from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256

p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=Path("output/training/city-five-stage-relations-initial-01"));p.add_argument("--demand",action="store_true");args=p.parse_args()
torch.set_num_threads(1)
parent=Path('output/training/city-established-pilot-01/checkpoints/city-000425984-7ec13846.zip')
out=args.output;out.mkdir(exist_ok=False)
e=CityRoadEnv('output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll')
try:
 old=MaskablePPO.load(parent,device='cpu')
 m=MaskablePPO(CityRelationalPolicy,e,device='cpu',n_steps=128,batch_size=64,n_epochs=4,learning_rate=.01,gamma=1.,gae_lambda=.95,ent_coef=.01,target_kl=.03,
  policy_kwargs=dict(features_extractor_class=CityDemandRelationsFeatures if args.demand else CityRelationalFeatures,features_extractor_kwargs=dict(conservative=True,temperature=20.),optimizer_class=RelativeRateAdam,normalize_images=False))
 missing,extra=m.policy.load_state_dict(old.policy.state_dict(),strict=False)
 assert not extra and len(missing)==6 and all(k.endswith(('.growth_relations.weight','.growth_road_temperature')) for k in missing)
 assert m.policy.features_extractor.growth_relations.weight.count_nonzero()==0
 m.num_timesteps=old.num_timesteps;m._n_updates=old._n_updates
 m.save(out/'start.zip')
 (out/'config.json').write_text(json.dumps(dict(parent=str(parent),parent_sha256=sha256(parent),initial_sha256=sha256(out/'start.zip'),optimizer='fresh: changed trainable parameters',actor_rate=.01,critic_rate=.0001,temperature=20),indent=2)+'\n')
finally:e.close()
