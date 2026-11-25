"""Compare rewards for a fixed ordinary-command replay; no policy or training."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from environment import TrafficEnv,ROOT
from rewards import GAMMA,WEIGHT,HOUSE_CAP,REWARD_SCHEMAS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet',default='dotnet')
    parser.add_argument('--replay',type=Path,default=ROOT/'docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/best-game.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output file')
    recording=json.loads(args.replay.read_text())
    plain=TrafficEnv(dotnet=args.dotnet,seeds=[recording['seed']])
    shaped=TrafficEnv(dotnet=args.dotnet,seeds=[recording['seed']],reward_mode='connectivity')
    try:
        plain.reset(seed=42);shaped.reset(seed=42)
        discounted=0;first=None;peak=0;positive=negative=0
        for i,event in enumerate(recording['actions']):
            request={k:v for k,v in event.items() if k in ['command','tool','x','y','toX','toY','id','choice']}
            if request['command']=='wait':request=None
            a,r,terminated,truncated,ia=plain._advance(request)
            b,s,term,trunc,info=shaped._advance(request)
            if (terminated,truncated,ia['trips'],ia['accepted'])!=(term,trunc,info['trips'],info['accepted']):
                raise RuntimeError('Simulation outcomes diverged')
            for key in a:np.testing.assert_array_equal(a[key],b[key])
            f=info['shaping_reward'];discounted+=GAMMA**i*f
            positive+=int(f>0);negative+=int(f<0);peak=max(peak,info['connected_houses'])
            if first is None and f>0:first=dict(command=i+1,seconds=info['seconds'],trips=info['trips'],shaping=f)
        if not terminated or info['trips']!=recording['score'] or abs(discounted)>1e-9:
            raise RuntimeError('Replay/terminal shaping check failed')
        result=dict(protocol='Fixed ordinary commands, one transition per command; intermediate selections tested separately. No optimizer/policy calls.',
                    source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    source_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                    reward_schema=REWARD_SCHEMAS['connectivity'],gamma=GAMMA,weight=WEIGHT,house_cap=HOUSE_CAP,
                    source_hash_normalization='UTF-8 source bytes with CRLF normalized to LF',
                    source_hashes={name:hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in
                                   ['training/environment.py','training/rewards.py','training/audit_rewards.py',
                                    'simulation/Assets/Simulation/UsefulConnectivity.cs','simulation/Headless/Program.cs']},
                    replay_sha256=hashlib.sha256(args.replay.read_bytes()).hexdigest(),
                    score=info['trips'],seconds=info['seconds'],commands=len(recording['actions']),
                    observations_and_outcomes_identical=True,first_positive_shaping=first,
                    max_connected_houses=peak,positive_shaping_transitions=positive,negative_shaping_transitions=negative,
                    discounted_shaping_sum=discounted,shaping_reward_total=info['shaping_reward_total'],
                    trip_reward_total=info['trip_reward_total'],training_reward_total=info['training_reward_total'])
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:plain.close();shaped.close()


if __name__=='__main__':main()
