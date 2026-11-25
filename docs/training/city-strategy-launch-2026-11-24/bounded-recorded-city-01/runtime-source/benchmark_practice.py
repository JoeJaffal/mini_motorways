"""Bounded infrastructure/inference benchmark. No rollout learning or optimizer steps.

Synthetic repeated observations measure inference overhead, not playing skill.
Scripted waits measure environment throughput, not a trained policy's workload.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import platform
from time import perf_counter

import numpy as np
import torch
from connection_practice import ConnectionPractice, WAIT, NONE
from hierarchy_policy import HierarchyPolicy
from hierarchy_rollout import policy_fingerprint


def rollout_waits(dotnet, dll, seed, steps):
    env = ConnectionPractice(dotnet=dotnet, host_dll=dll)
    try:
        env.reset(seed=seed)
        count = 0
        for _ in range(steps):
            env.step(0)
            env.step(NONE)
            _, _, terminated, truncated, _ = env.step(WAIT)
            count += 1
            if terminated or truncated:
                env.reset(seed=seed)
        return count
    finally:
        env.close()


def coupled_inference(policy,dotnet,dll,workers,rounds):
    """One frozen policy, batched inference, parallel native steps; no learning."""
    environments=[]
    before=policy_fingerprint(policy)
    try:
        observations=[]
        for worker in range(workers):
            env=ConnectionPractice(dotnet=dotnet,host_dll=dll)
            environments.append(env)
            obs,_=env.reset(seed=1000+worker);observations.append(obs)
        def batch():return {key:np.stack([o[key] for o in observations]) for key in observations[0]}
        first_masks=np.stack([env.action_masks() for env in environments])
        for _ in range(3):policy.predict(batch(),deterministic=True,action_masks=first_masks)
        if policy.device.type=='cuda':torch.cuda.synchronize()
        completed=0;seconds=0.;resets=0;episodes=[0]*workers
        start=perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for _ in range(rounds):
                masks=np.stack([env.action_masks() for env in environments])
                actions,_=policy.predict(batch(),deterministic=True,action_masks=masks)
                before_times=[env.raw['time'] for env in environments]
                results=list(pool.map(lambda pair:pair[0].step(int(pair[1])),zip(environments,actions)))
                for i,(obs,_,terminated,truncated,info) in enumerate(results):
                    seconds+=info['seconds']-before_times[i]
                    completed+=info['command_completed']
                    if terminated or truncated:
                        episodes[i]+=1;resets+=1
                        obs,_=environments[i].reset(seed=1000+i+workers*episodes[i])
                    observations[i]=obs
        if policy.device.type=='cuda':torch.cuda.synchronize()
        elapsed=perf_counter()-start
        if policy_fingerprint(policy)!=before:raise RuntimeError('Benchmark changed policy weights')
        return dict(workers=workers,rounds=rounds,tokens=workers*rounds,
            wall_seconds=elapsed,tokens_per_second=workers*rounds/elapsed,
            completed_commands=completed,simulated_seconds=seconds,resets=resets,
            includes_process_startup=False,untrained_policy=True,policy_sha256=before)
    finally:
        for env in environments:env.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dotnet', default='dotnet')
    p.add_argument('--dll', default='simulation/Headless/bin/Release/net8.0/TrafficHost.dll')
    p.add_argument('--workers', type=int, nargs='+', default=[1, 2, 4, 8])
    p.add_argument('--batch-sizes', type=int, nargs='+', default=[1, 8, 32])
    p.add_argument('--steps', type=int, default=20)
    p.add_argument('--iterations', type=int, default=20)
    p.add_argument('--threads', type=int, default=1)
    p.add_argument('--coupled-rounds',type=int,default=0,
                   help='Bounded end-to-end inference rounds; zero skips this extra measurement')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    if min(args.workers+args.batch_sizes+[args.steps,args.iterations,args.threads]) < 1:
        p.error('All counts must be positive')
    if args.coupled_rounds<0:p.error('Coupled rounds must be nonnegative')
    if Path(args.output).exists():p.error('Output exists; choose a new measurement file')
    torch.set_num_threads(args.threads)
    torch.manual_seed(42)
    result = dict(kind='no-training-infrastructure-benchmark', platform=platform.platform(),
                  torch=torch.__version__, threads=args.threads, workers=[], inference=[],coupled=[])
    for workers in args.workers:
        start = perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            counts = list(pool.map(lambda seed: rollout_waits(args.dotnet, args.dll, seed, args.steps), range(workers)))
        elapsed = perf_counter()-start
        result['workers'].append(dict(workers=workers, waits=sum(counts), wall_seconds=elapsed,
            waits_per_second=sum(counts)/elapsed, includes_process_startup=True))
    env = ConnectionPractice(dotnet=args.dotnet, host_dll=args.dll)
    try:
        obs, _ = env.reset(seed=42)
        mask = env.action_masks()
        for device in ['cpu']+(['cuda'] if torch.cuda.is_available() else []):
            if device == 'cuda':
                result['gpu'] = torch.cuda.get_device_name(0)
            torch.manual_seed(42)  # Same initial weights for the compared devices.
            policy = HierarchyPolicy(env.observation_space, env.action_space,
                                     lr_schedule=lambda _: 0.0).to(device)
            policy.set_training_mode(False)
            for size in args.batch_sizes:
                batch = {k: np.repeat(v[None], size, axis=0) for k,v in obs.items()}
                masks = np.repeat(mask[None], size, axis=0)
                for _ in range(3):
                    policy.predict(batch, deterministic=True, action_masks=masks)
                if device == 'cuda':
                    torch.cuda.synchronize()
                start = perf_counter()
                for _ in range(args.iterations):
                    policy.predict(batch, deterministic=True, action_masks=masks)
                if device == 'cuda':
                    torch.cuda.synchronize()
                elapsed = perf_counter()-start
                result['inference'].append(dict(device=device, batch_size=size,
                    decisions_per_second=size*args.iterations/elapsed,
                    seconds_per_batch=elapsed/args.iterations,
                    includes_numpy_transfers=True))
            if args.coupled_rounds:
                for workers in args.workers:
                    measurement=coupled_inference(policy,args.dotnet,args.dll,workers,args.coupled_rounds)
                    measurement['device']=device
                    result['coupled'].append(measurement)
    finally:
        env.close()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
