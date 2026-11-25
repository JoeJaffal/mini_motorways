"""Adjust the trained route policy's alignment and no-progress Wait preferences."""

import argparse
import json
from pathlib import Path

from sb3_contrib import MaskablePPO
import torch

from city_route_repair_policy import RouteProgressPolicy, RouteRepairFeatures
from prepare_city_policy import sha256
from train_limited_route_ppo import LimitedRouteEnv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dll','checkpoint','output'):
        parser.add_argument(f'--{name}',type=Path,required=True)
    parser.add_argument('--alignment',type=float,default=8.)
    parser.add_argument('--hold',type=float,default=3.25)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a fresh output path')
    torch.set_num_threads(1)
    source = MaskablePPO.load(args.checkpoint,device='cpu')
    env = LimitedRouteEnv(args.dll)
    try:
        model = MaskablePPO(
            RouteProgressPolicy,env,device='cpu',n_steps=source.n_steps,batch_size=source.batch_size,
            policy_kwargs=dict(features_extractor_class=RouteRepairFeatures,normalize_images=False,
                               features_extractor_kwargs=dict(frontier=True,progress=True,calibrated=True)),
        )
        missing,extra = model.policy.load_state_dict(source.policy.state_dict(),strict=False)
        if extra or {name.split('.')[-1] for name in missing}!={'route_alignment','route_hold'}:
            raise RuntimeError('Use the trained progress-conditioned policy as the source')
        features = model.policy.features_extractor
        with torch.no_grad():
            features.route_alignment.fill_(args.alignment)
            features.route_hold.fill_(args.hold)
        model.num_timesteps = source.num_timesteps
        model._n_updates = source._n_updates
        model.save(args.output,exclude=['_last_obs','_last_episode_starts','ep_info_buffer','ep_success_buffer'])
        print(json.dumps(dict(source_sha256=sha256(args.checkpoint),checkpoint_sha256=sha256(args.output),
                              decisions=model.num_timesteps,alignment=args.alignment,hold=args.hold),indent=2))
    finally:
        env.close()


if __name__=='__main__':
    main()
