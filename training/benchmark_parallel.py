"""Short isolated learner benchmarks; never changes an existing run/checkpoint."""
import argparse
from contextlib import redirect_stdout
from datetime import datetime
import json
from pathlib import Path
import time

import torch
from sb3_contrib import MaskablePPO

from environment import ROOT
from parallel import make_vector
from progress import BudgetCallback,atomic_json
from train import GridEncoder  # Register the same architecture used in production.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet',default='dotnet')
    parser.add_argument('--seconds',type=float,default=15)
    parser.add_argument('--checkpoint',type=Path,default=ROOT/'output/training/first-full-tools/final.zip')
    parser.add_argument('--workers',type=int,nargs='+',default=[1,2,4,4,2,1])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.seconds<=0 or any(x not in [1,2,4] for x in args.workers):parser.error('Use positive seconds and 1/2/4 workers')
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    output=args.output or ROOT/'output/benchmarks'/datetime.now().strftime('%Y%m%d-%H%M%S')
    output.mkdir(parents=True,exist_ok=False)
    results=[]
    for trial,workers in enumerate(args.workers):
        directory=output/f'{trial+1:02d}-{workers}-workers';directory.mkdir()
        env=make_vector(workers,output=directory,dotnet=args.dotnet,seeds=[1000],record_replays=True)
        try:
            model=MaskablePPO.load(args.checkpoint,env=env,device='cpu',n_steps=256//workers,seed=42)
            # Warm up PyTorch kernels, host JIT and rollout allocation consistently.
            model.learn(total_timesteps=256,reset_num_timesteps=True)
            updates=model._n_updates
            callback=BudgetCallback(directory,args.seconds/60,10_000_000,print_seconds=5,
                                    metadata={'schema':'parallel-benchmark','simulator_commit':'benchmark'})
            started=time.perf_counter()
            with (directory/'console.log').open('w',encoding='utf-8') as log,redirect_stdout(log):
                model.learn(total_timesteps=10_000_000,callback=callback,reset_num_timesteps=True)
            elapsed=time.perf_counter()-started
            result=dict(workers=workers,trial=trial+1,seconds=elapsed,selections=model.num_timesteps,
                        selections_per_second=model.num_timesteps/elapsed,commands=callback.commands,
                        commands_per_second=callback.commands/elapsed,games=callback.episodes,
                        games_per_second=callback.episodes/elapsed,optimizer_epochs=model._n_updates-updates,
                        aggregate_rollout_size=256,seed=1000,torch_threads=2)
            results.append(result);atomic_json(output/'results.json',results)
            print(json.dumps(result),flush=True)
        finally:env.close()
    print(f'Benchmark results: {output}',flush=True)


if __name__=='__main__':main()
