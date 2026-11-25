"""Trace two frozen policies on an exposed development map; never train."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from sb3_contrib import MaskablePPO

from environment import ROOT
from train_goal import model_environment


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(env, obs, action):
    if action == 0:
        return dict(kind='wait')
    if action < 3:
        return dict(kind='upgrade', choice=action-1,
                    offers=env.base.raw['upgradeChoices'])
    routes = obs['candidates'].shape[0]
    if action < 3 + routes:
        i = action-3
        return dict(kind='route', cells=[list(p) for p in env.plans[i]],
                    features=obs['candidates'][i].tolist(),
                    bypass=i in env.bypass_baselines)
    i = action-3-routes
    return dict(kind='light', cell=list(env.signal_cells[i]),
                features=obs['signals'][i].tolist())


def state(env):
    raw = env.base.raw
    return dict(time=raw['time'], trips=raw['tripsCompleted'],
                inventory=raw['inventory'],
                shops=[{k:b[k] for k in ['id','cell','color','demand','reserved',
                       'demandCapacity','overcrowdedFor']} for b in raw['buildings']
                       if not b['isHouse']],
                waiting=[{k:v[k] for k in ['id','shopId','stage','x','y','waiting','obstacle']}
                         for v in raw['vehicles'] if v['waiting'] >= 3])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, default=ROOT/'output/training/signals-context-02')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seed', type=int, default=2000)
    p.add_argument('--cap', type=int, default=3600)
    a = p.parse_args()
    if a.output.exists():
        p.error('Choose a fresh output directory')
    if a.cap < 1:
        p.error('Positive cap required')
    paths = {name:a.run/file for name,file in [('protected','validation-best.zip'),('final','final.zip')]}
    hashes = {n:digest(x) for n,x in paths.items()}
    torch.set_num_threads(2)
    models = {n:MaskablePPO.load(x, device='cpu') for n,x in paths.items()}
    if models['protected'].observation_space != models['final'].observation_space:
        p.error('Identical observation schemas required')
    snapshots = {n:[x.detach().clone() for x in m.policy.parameters()] for n,m in models.items()}
    a.output.mkdir(parents=True)
    save(a.output/'protocol.json', dict(seed=a.seed, cap=a.cap, checkpoints={n:str(x.resolve()) for n,x in paths.items()},
         checkpoint_sha256=hashes, no_training=True, source_sha256=digest(Path(__file__)),
         protocol='Two deterministic trajectories; both policies scored on every visited state with identical masks. Development diagnosis, not unseen-map evidence.'))
    outcomes = {}
    for name, model in models.items():
        env = model_environment(model, seconds=a.cap, dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),
                                skip_forced_wait=getattr(model,'skip_forced_wait',False))
        decisions = []; commands = []
        try:
            obs,_ = env.reset(seed=a.seed, options={'scenario_seed':a.seed})
            original = env.base._advance

            def advance(request=None):
                before = state(env)
                result = original(request)
                commands.append(dict(command=request or {'command':'wait'}, before=before,
                                     after=state(env)))
                return result

            env.base._advance = advance
            while True:
                mask = env.action_masks(); predictions = {}
                for label, policy in models.items():
                    with torch.no_grad():
                        probs = policy.policy.get_distribution(policy.policy.obs_to_tensor(obs)[0],
                            action_masks=mask).distribution.probs[0].cpu().numpy()
                    top = sorted(np.flatnonzero(mask), key=lambda i:-float(probs[i]))[:5]
                    predictions[label] = [dict(action=int(i), probability=float(probs[i]),
                         description=describe(env,obs,int(i))) for i in top]
                action = predictions[name][0]['action']
                decisions.append(dict(state=state(env), command_index=len(commands), action=action,
                    legal_routes=len(env.plans), legal_lights=int(mask[515:].sum()),
                    predictions=predictions,
                    disagreement=predictions['protected'][0]['action'] != predictions['final'][0]['action']))
                obs,_,terminated,truncated,info = env.step(action)
                if len(decisions)%50 == 0:
                    print(f'TRACE {name} | {len(decisions)} decisions | {info["trips"]} trips | {info["seconds"]:.1f}s',flush=True)
                if terminated or truncated:
                    break
            save(a.output/f'{name}-decisions.json', decisions)
            save(a.output/f'{name}-commands.json', commands)
            replay=env.export_replay(); replay['source']='hybrid-evaluation'
            save(a.output/f'{name}-replay.json', replay)
            first = next((x for x in decisions if x['disagreement']), None)
            outcomes[name] = dict(trips=info['trips'], seconds=info['seconds'], terminated=terminated,
                truncated=truncated, decisions=len(decisions), disagreements=sum(x['disagreement'] for x in decisions),
                first_disagreement=first, final_state=state(env))
            print(f'FINISHED {name} | {info["trips"]} trips | {info["seconds"]:.1f}s',flush=True)
        finally:
            env.close()
    unchanged = all(digest(paths[n])==hashes[n] and all(torch.equal(x,y) for x,y in
                    zip(snapshots[n],m.policy.parameters())) for n,m in models.items())
    if not unchanged:
        raise RuntimeError('Checkpoint or policy mutated')
    save(a.output/'diagnosis.json', dict(seed=a.seed, weights_unchanged=True, outcomes=outcomes,
         limits='First disagreement is descriptive, not causal proof. Offered routes are planner-restricted; absence of an option does not prove impossibility. No counterfactual intervention performed.'))
    print(f'DIAGNOSIS COMPLETE | {a.output / "diagnosis.json"}',flush=True)


if __name__ == '__main__':
    main()
