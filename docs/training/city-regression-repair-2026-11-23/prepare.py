from pathlib import Path
import json,torch
from sb3_contrib import MaskablePPO
from city_learning_policy import CityLearningPolicy
from city_established_policy import CityEstablishedFeatures
from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256

torch.set_num_threads(1)
source=Path('output/training/city-learning-long-01/segment-01/checkpoints/city-000413696-e191fc32.zip')
root=Path('output/training/city-established-start-01');root.mkdir(exist_ok=False)
env=CityRoadEnv('output/city-network-service-build.NdaqGi/bin/TrafficHost/release/TrafficHost.dll')
try:
 old=MaskablePPO.load(source,device='cpu')
 new=MaskablePPO(CityLearningPolicy,env,device='cpu',n_steps=128,batch_size=64,n_epochs=4,learning_rate=1e-6,gamma=1.,gae_lambda=.95,ent_coef=.01,target_kl=.03,
 policy_kwargs=dict(features_extractor_class=CityEstablishedFeatures,features_extractor_kwargs=dict(conservative=True),normalize_images=False))
 missing,extra=new.policy.load_state_dict(old.policy.state_dict(),strict=False)
 assert not extra and all('.opening_reference.' in k for k in missing)
 new.policy.features_extractor.opening_reference.load_state_dict(old.policy.features_extractor.state_dict(),strict=True)
 new.policy.optimizer.load_state_dict(old.policy.optimizer.state_dict())
 new.num_timesteps=old.num_timesteps;new._n_updates=old._n_updates
 new.save(root/'start.zip')
 (root/'config.json').write_text(json.dumps(dict(source=str(source),source_sha256=sha256(source),start_sha256=sha256(root/'start.zip')),indent=2))
finally:env.close()
