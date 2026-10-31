"""Frozen final-policy baseline versus a single first-upgrade intervention."""
import argparse
import json
from pathlib import Path

import torch
from sb3_contrib import MaskablePPO

from diagnose_policy_regression import digest, save, state
from environment import ROOT
from train_goal import model_environment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--diagnosis', type=Path, default=ROOT/'output/experiments/regression-2000-01')
    p.add_argument('--smoke', action='store_true', help='Two simulated seconds per condition; wiring only')
    a = p.parse_args()
    if a.output.exists():
        p.error('Choose a fresh output directory')
    protocol = json.loads((a.diagnosis/'protocol.json').read_text(encoding='utf-8'))
    previous = json.loads((a.diagnosis/'diagnosis.json').read_text(encoding='utf-8'))
    reference = json.loads((a.diagnosis/'final-commands.json').read_text(encoding='utf-8'))
    difference = previous['outcomes']['final']['first_disagreement']
    when = difference['state']['time']
    original_action = difference['predictions']['final'][0]['action']
    replacement = difference['predictions']['protected'][0]['action']
    if (protocol['seed'], when, original_action, replacement) != (2000, 140, 1, 2):
        p.error('Expected diagnosed seed2000 first-upgrade difference at140s')
    checkpoint = Path(protocol['checkpoints']['final'])
    checksum = digest(checkpoint)
    if checksum != protocol['checkpoint_sha256']['final']:
        p.error('Final checkpoint differs from original diagnosis')
    cap = 2 if a.smoke else protocol['cap']
    torch.set_num_threads(2)
    a.output.mkdir(parents=True)
    save(a.output/'protocol.json', dict(seed=2000, cap=cap, smoke=a.smoke,
         checkpoint=str(checkpoint), checkpoint_sha256=checksum,
         source_sha256=digest(Path(__file__)),
         diagnosis_protocol_sha256=digest(a.diagnosis/'protocol.json'),
         intervention=dict(time=when, original_action=original_action, replacement=replacement),
         no_training=True, protocol='Same frozen final policy; override exactly one upgrade, then normal deterministic decisions. No later commands held fixed.'))
    results = {}
    for label in ['baseline', 'changed-upgrade']:
        model = MaskablePPO.load(checkpoint, device='cpu')
        weights = [x.detach().clone() for x in model.policy.parameters()]
        env = model_environment(model, seconds=cap, dotnet=str(ROOT/'tmp/dotnet/dotnet.exe'),
                                skip_forced_wait=getattr(model,'skip_forced_wait',False))
        rows = []; commands = []; applied = False
        try:
            obs,_ = env.reset(seed=2000, options={'scenario_seed':2000})
            advance_original = env.base._advance

            def advance(request=None):
                cmd = request or {'command':'wait'}
                index = len(commands)
                # Baseline reproduces every original ordinary command. Both
                # conditions must reproduce the prefix before intervention.
                if not a.smoke and (label == 'baseline' or not applied):
                    if index >= len(reference) or cmd != reference[index]['command']:
                        raise RuntimeError(f'Unexpected command prefix at {index}')
                result = advance_original(request)
                commands.append(dict(command=cmd, after=state(env)))
                return result

            env.base._advance = advance
            while True:
                mask = env.action_masks()
                action = int(model.predict(obs, deterministic=True, action_masks=mask)[0])
                chosen = action; now = env.base.raw['time']
                if label == 'changed-upgrade' and now == when and not applied:
                    if action != original_action or not mask[replacement] or state(env) != difference['state']:
                        raise RuntimeError('Intervention state/action mismatch')
                    applied = True; chosen = replacement
                    print(f'OVERRIDE | {when}s | upgrade choice0 -> choice1; policy continues normally', flush=True)
                rows.append(dict(time=now, policy_action=action, executed_action=chosen))
                obs,_,term,trunc,info = env.step(chosen)
                if len(rows)%50 == 0:
                    print(f'{label} | {len(rows)} decisions | {info["trips"]} trips | {info["seconds"]:.1f}s', flush=True)
                if term or trunc:
                    break
            if not a.smoke:
                if label == 'baseline' and (info['trips'] != 83 or abs(info['seconds']-469.7)>1e-6 or len(commands)!=len(reference)):
                    raise RuntimeError('Baseline did not reproduce original83-trip game')
                if label == 'changed-upgrade' and not applied:
                    raise RuntimeError('Intervention never applied')
            if digest(checkpoint)!=checksum or not all(torch.equal(x,y) for x,y in zip(weights,model.policy.parameters())):
                raise RuntimeError('Policy/checkpoint changed')
            replay = env.export_replay(); replay['source']='fixed-first-upgrade-evaluation'
            save(a.output/f'{label}-replay.json', replay)
            save(a.output/f'{label}-commands.json', commands)
            save(a.output/f'{label}-decisions.json', rows)
            results[label] = dict(trips=info['trips'], seconds=info['seconds'],
                signals_placed=info.get('signals_placed'), intervention_applied=applied,
                terminated=term, truncated=trunc, final_state=state(env))
            print(f'FINISHED {label} | {info["trips"]} trips | {info["seconds"]:.1f}s', flush=True)
        finally:
            env.close()
    save(a.output/'comparison.json', dict(results=results, weights_unchanged=True,
        smoke=a.smoke, trip_difference=results['changed-upgrade']['trips']-results['baseline']['trips'],
        limits='One exposed development seed. Estimates total effect of changing one upgrade under this frozen policy, including later policy feedback; not isolated light physics or generalization evidence. Smoke does not exercise intervention.'))
    print(f'UPGRADE TEST COMPLETE | {a.output / "comparison.json"}', flush=True)


if __name__ == '__main__':
    main()
