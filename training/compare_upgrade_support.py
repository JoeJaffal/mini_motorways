"""Development-only frozen-policy test of supported upgrade package filtering."""
import argparse
import json
from pathlib import Path

import torch
from sb3_contrib import MaskablePPO

from diagnose_policy_regression import digest, save
from environment import ROOT
from train_goal import model_environment


def supported_mask(mask, offers):
    """Filter unsupported extras only with a supported, no-fewer-roads alternative.

    This is a heuristic, not true dominance: inventory and future offer weights
    can change. Never alter non-upgrade actions or filter both upgrade offers.
    """
    result = mask.copy()
    supported = {0, 1, 3}  # roads, bridges, lights in this restricted signal agent
    for i, offer in enumerate(offers[:2]):
        if offer['type'] in supported or not mask[i+1]:
            continue
        if any(j != i and mask[j+1] and other['type'] in supported
               and other['amount'] > 0 and other['roads'] >= offer['roads']
               for j, other in enumerate(offers[:2])):
            result[i+1] = False
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--run', type=Path, default=ROOT/'output/training/signals-context-02')
    p.add_argument('--smoke', action='store_true', help='Two-second wiring check on one map, not performance')
    a = p.parse_args()
    if a.output.exists():
        p.error('Choose a fresh output folder')
    checkpoint = a.run/'final.zip'
    checksum = digest(checkpoint)
    seeds = [2000] if a.smoke else list(range(2000,2005))
    cap = 2 if a.smoke else 3600
    torch.set_num_threads(2)
    model = MaskablePPO.load(checkpoint, device='cpu')
    if 'signals' not in model.observation_space.spaces:
        p.error('Requires the restricted signal policy')
    weights = [x.detach().clone() for x in model.policy.parameters()]
    a.output.mkdir(parents=True)
    save(a.output/'protocol.json', dict(checkpoint=str(checkpoint.resolve()), checkpoint_sha256=checksum,
        source_sha256=digest(Path(__file__)), seeds=seeds, cap=cap, smoke=a.smoke, no_training=True,
        intervention='Mask unsupported-tool upgrade only if another legal package has a positive supported extra and at least as many roads; all other actions/observations unchanged.',
        limits='Exposed development maps. Engineered selection heuristic, not learned improvement or mathematical dominance. Package counts can affect future offers.'))
    results = {}
    for filtered in [False, True]:
        label = 'supported-filter' if filtered else 'baseline'
        env = model_environment(model, seconds=cap, dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),
                                skip_forced_wait=getattr(model,'skip_forced_wait',False))
        games = []; events = []; best = None; best_score = -1
        try:
            for seed in seeds:
                obs,_ = env.reset(seed=seed, options={'scenario_seed':seed})
                interventions = 0
                while True:
                    mask = env.action_masks()
                    original = int(model.predict(obs,deterministic=True,action_masks=mask)[0])
                    offers = env.base.raw['upgradeChoices']
                    changed = supported_mask(mask, offers) if filtered else mask
                    action = int(model.predict(obs,deterministic=True,action_masks=changed)[0])
                    if offers:
                        events.append(dict(seed=seed, time=env.base.raw['time'], offers=offers,
                            masked_actions=[i for i in [1,2] if mask[i] and not changed[i]],
                            original_action=original, executed_action=action))
                    interventions += int(action != original)
                    obs,_,term,trunc,info = env.step(action)
                    if term or trunc:
                        break
                games.append(dict(seed=seed, trips=info['trips'], seconds=info['seconds'],
                    signals_placed=info.get('signals_placed'), changed_decisions=interventions,
                    terminated=term, truncated=trunc))
                if not filtered and not a.smoke:
                    expected = json.loads((a.run/'summary.json').read_text(encoding='utf-8'))['after'][seed-2000]
                    if (expected['scenario_seed'] != seed or expected['trips'] != info['trips']
                            or abs(expected['seconds']-info['seconds']) > 1e-6):
                        raise RuntimeError(f'Baseline differs from recorded final evaluation on {seed}')
                if info['trips'] > best_score:
                    best=env.export_replay(); best_score=info['trips']
                print(f'{label} | seed {seed} | {info["trips"]} trips | {info["seconds"]:.1f}s | {interventions} changed choices',flush=True)
        finally:
            env.close()
        if digest(checkpoint)!=checksum or not all(torch.equal(x,y) for x,y in zip(weights,model.policy.parameters())):
            raise RuntimeError('Policy/checkpoint changed')
        results[label] = games
        save(a.output/f'{label}-games.json', games)
        save(a.output/f'{label}-upgrades.json', events)
        best['source']='upgrade-support-evaluation'
        save(a.output/f'{label}-best-replay.json', best)
    pairs = [dict(seed=x['seed'],baseline=x['trips'],filtered=y['trips'],difference=y['trips']-x['trips'])
             for x,y in zip(results['baseline'],results['supported-filter'])]
    save(a.output/'comparison.json', dict(paired_scores=pairs, weights_unchanged=True, smoke=a.smoke,
        baseline_mean=sum(x['baseline'] for x in pairs)/len(pairs),
        filtered_mean=sum(x['filtered'] for x in pairs)/len(pairs),
        wins=sum(x['difference']>0 for x in pairs), ties=sum(x['difference']==0 for x in pairs),
        losses=sum(x['difference']<0 for x in pairs)))
    print(f'UPGRADE COMPARISON COMPLETE | {a.output / "comparison.json"}',flush=True)


if __name__ == '__main__':
    main()
