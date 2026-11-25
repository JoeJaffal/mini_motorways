from pathlib import Path
import argparse,json,torch,numpy as np
from sb3_contrib import MaskablePPO
from city_relational_policy import CityRelationalPolicy,CitySharpRelationsFeatures,RelativeRateAdam
from city_curriculum import CityCurriculumEnv,LOW
from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256,masked_probs
p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
torch.set_num_threads(1);args.output.mkdir(exist_ok=False)
dll='output/city-five-stage-build-01/bin/TrafficHost/release/TrafficHost.dll';e=CityRoadEnv(dll)
try:
 old=MaskablePPO.load(args.parent,device='cpu')
 m=MaskablePPO(CityRelationalPolicy,e,device='cpu',n_steps=128,batch_size=64,n_epochs=4,learning_rate=.003,gamma=1.,gae_lambda=.95,ent_coef=.01,target_kl=.03,
  policy_kwargs=dict(features_extractor_class=CitySharpRelationsFeatures,features_extractor_kwargs=dict(conservative=True,temperature=20.,road_scale=20.),optimizer_class=RelativeRateAdam,normalize_images=False))
 missing,extra=m.policy.load_state_dict(old.policy.state_dict(),strict=False)
 assert not extra and len(missing)==3 and all(k.endswith('.growth_sampling_scale') for k in missing)
 m.policy.optimizer.load_state_dict(old.policy.optimizer.state_dict())
 m.num_timesteps=old.num_timesteps;m._n_updates=old._n_updates
 obs,_=e.reset(options=dict(scenario_seed=2004));mask=e.action_masks()
 np.testing.assert_array_equal(masked_probs(m,obs,mask),masked_probs(old,obs,mask))
finally:e.close()
e=CityCurriculumEnv(dll,validation=True)
try:
 obs,_=e.reset(options=dict(scenario_seed=118200000,exercise=LOW));mask=e.action_masks()
 a,b=masked_probs(old,obs,mask),masked_probs(m,obs,mask)
 np.testing.assert_allclose(a[0],b[0],atol=1e-6,rtol=0);assert (b[~mask]==0).all()
 assert a[1:].argmax()==b[1:].argmax()
finally:e.close()
m.save(args.output/'candidate.zip')
(args.output/'config.json').write_text(json.dumps(dict(source=str(args.parent),source_sha256=sha256(args.parent),candidate_sha256=sha256(args.output/'candidate.zip'),road_scale=20,opening_parity=True,wait_mass_parity=True,road_argmax_preserved=True),indent=2)+'\n')
