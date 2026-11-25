"""Compare the original edit cap with room for both free parcel attachments."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Lock

import torch
from sb3_contrib import MaskablePPO

import spare_road_ppo
from bend_ppo import digest
from hierarchy_rollout import policy_fingerprint
from spare_road_ppo import SpareRoadEnvironment


def run_layout(env, policy, policy_lock, seed, extra_edits, greedy):
    obs, _ = env.reset(options=dict(stage='clear', split='validation', layout_seed=seed))
    original_limit = env.env.edit_limit
    stock = env.env.inventory
    env.env.edit_limit += extra_edits
    steps = []
    done = False
    rng = torch.Generator().manual_seed(100000+seed)
    while not done:
        with policy_lock, torch.inference_mode():
            tensor,_ = policy.obs_to_tensor(obs)
            probs = policy.get_distribution(tensor,action_masks=env.action_masks()).distribution.probs[0]
            action = int(probs.argmax()) if greedy else int(torch.multinomial(probs, 1, generator=rng))
        before = env.env.raw['inventory'][0]
        obs, _, done, truncated, info = env.step(action)
        if truncated:
            raise RuntimeError('Unexpected diagnostic truncation')
        steps.append(dict(action=action, paid=before-env.env.raw['inventory'][0]))
    trips, seconds = env.env.deliveries()
    return dict(seed=seed,distance=env.distance,offset=env.offset,stock=stock,
                original_limit=original_limit,extra_edits=extra_edits,steps=steps,
                connected=info['connected'],trips=trips,seconds=seconds)


def main(args):
    config=json.loads(Path(args.checkpoint).with_name('config.json').read_text())
    if config['native_sha256']!=digest(args.dll) or config['source_sha256']!=digest(spare_road_ppo.__file__):
        raise ValueError('Native host or runner changed')
    torch.set_num_threads(2)
    model=MaskablePPO.load(args.checkpoint,device='cpu')
    policy=model.policy
    policy.set_training_mode(False)
    fingerprint=policy_fingerprint(policy)
    envs=[]
    arms={}
    policy_lock = Lock()
    try:
        for _ in range(8):
            envs.append(SpareRoadEnvironment(args.dll))
        with ThreadPoolExecutor(max_workers=len(envs)) as pool:
            for extra_edits in (0,1):
                rows=[]
                for seed in range(36000,36100,len(envs)):
                    group=zip(envs,range(seed,min(seed+len(envs),36100)))
                    rows.extend(pool.map(lambda job: run_layout(job[0],policy,policy_lock,job[1],extra_edits,args.greedy),group))
                arms[str(extra_edits)]=rows
    finally:
        for env in envs:env.close()
    if policy_fingerprint(policy)!=fingerprint:
        raise RuntimeError('Evaluation changed weights')
    for original, relaxed in zip(arms['0'],arms['1']):
        if original['seed']!=relaxed['seed'] or original['stock']!=relaxed['stock']:
            raise RuntimeError('Paired test changed native stock or layouts')
    return dict(native_sha256=digest(args.dll),source_sha256=digest(__file__),
                policy_fingerprint=fingerprint,changed_weights=False,greedy=args.greedy,arms=arms)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',required=True)
    p.add_argument('--dll',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--greedy',action='store_true')
    args=p.parse_args()
    output=Path(args.output)
    if output.exists():
        p.error('Use a new output path')
    with output.open('x') as f:
        json.dump(main(args),f,indent=2)
        f.write('\n')
