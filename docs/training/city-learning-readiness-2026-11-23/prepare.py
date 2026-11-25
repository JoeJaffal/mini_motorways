from pathlib import Path
import json
import torch
from sb3_contrib import MaskablePPO
from city_learning_policy import CityLearningPolicy
from city_network_service_policy import CityNetworkServiceFeatures
from city_road_pilot import CityRoadEnv
from prepare_city_policy import sha256,masked_probs
import numpy as np

torch.set_num_threads(1)
source=Path('output/training/city-network-service-pilot-01/final.zip')
root=Path('output/training/city-learning-start-01')
root.mkdir(exist_ok=False)
env=CityRoadEnv('output/city-network-service-build.NdaqGi/bin/TrafficHost/release/TrafficHost.dll')
try:
 old=MaskablePPO.load(source,device='cpu')
 new=MaskablePPO(CityLearningPolicy,env,device='cpu',n_steps=128,batch_size=64,n_epochs=4,
    learning_rate=5e-5,gamma=1.,gae_lambda=.95,ent_coef=.01,target_kl=.03,
    policy_kwargs=dict(features_extractor_class=CityNetworkServiceFeatures,features_extractor_kwargs=dict(conservative=True),normalize_images=False))
 new.policy.load_state_dict(old.policy.state_dict(),strict=True)
 new.num_timesteps=old.num_timesteps
 new._n_updates=old._n_updates
 obs,_=env.reset(options={'scenario_seed':108400001})
 mask=env.action_masks()
 np.testing.assert_array_equal(masked_probs(old,obs,mask),masked_probs(new,obs,mask))
 inputs,_=new.policy.obs_to_tensor(obs)
 masks=np.stack([mask,mask])
 inputs={k:v.expand(2,*v.shape[1:]) for k,v in inputs.items()}
 actions,values,logp=new.policy(inputs,action_masks=masks)
 estimated,relogp,entropy=new.policy.evaluate_actions(inputs,actions,action_masks=masks)
 torch.testing.assert_close(logp,relogp)
 loss=estimated.mean()-relogp.mean()-.01*entropy.mean()
 trainable=[p for p in new.policy.parameters() if p.requires_grad]
 grads=torch.autograd.grad(loss,trainable,allow_unused=True)
 assert all(g is None or torch.isfinite(g).all() for g in grads)
 new.save(root/'start.zip')
 (root/'checks.json').write_text(json.dumps(dict(source=str(source),source_sha256=sha256(source),start_sha256=sha256(root/'start.zip'),
   parity=True,finite_gradients=True,trainable=[n for n,p in new.policy.named_parameters() if p.requires_grad]),indent=2))
finally: env.close()
