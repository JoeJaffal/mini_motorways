"""Disposable PPO integration check through the trainer's actual worker factory."""
import argparse
from functools import partial
import json
from pathlib import Path
import time
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from train_city_curriculum import worker, optimizer_steps
from prepare_city_policy import sha256


class Audit(BaseCallback):
    def __init__(self):
        super().__init__(); self.rows=[]

    def _on_step(self):
        for info in self.locals['infos']:
            if 'episode' in info:
                assert info['episode']['r']==info['trips']
                assert not info['TimeLimit.truncated']
                self.rows.append(dict(info['episode']))
        return True


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    output=parser.parse_args().output;output.mkdir(exist_ok=False)
    root=Path.cwd();archive=root/'docs/training/mini-fixed-route-2026-11-25'
    parent=root/'output/training/mini-road-detached-initial-01/start.zip';before=sha256(parent)
    torch.set_num_threads(1)
    args=dict(dll=str(root/'output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll'),
        stage='single-connection',count=16,seed=232000001,collapse=True,horizon=600,
        fast_priority_tail=False,reserve_warmup_seconds=0,reserve_delay_seconds=None,allow_bridges=True,
        mini_starts=None,small_city_horizon=300,fast_small_city_tail=True,repeat_mini_seed=232000001)
    (output/'config.json').write_text(json.dumps(args,indent=2)+'\n')
    env=DummyVecEnv([partial(worker,rank=i,**args) for i in (0,1)])
    try:
        model=MaskablePPO.load(parent,env=env,device='cuda',n_steps=64,batch_size=32,n_epochs=1,
                              learning_rate=.0003,gae_lambda=1,vf_coef=1e-5)
        model.policy.features_extractor.growth_cache_enabled=True
        if model.ep_info_buffer is not None:model.ep_info_buffer.clear()
        frozen={n:p.detach().cpu().clone() for n,p in model.policy.features_extractor.named_parameters() if not p.requires_grad}
        initial=model.num_timesteps;steps=optimizer_steps(model);assert steps==8192;callback=Audit();start=time.monotonic()
        model.learn(total_timesteps=128,reset_num_timesteps=False,callback=callback)
        assert model.num_timesteps-initial==128 and callback.rows
        assert all(torch.equal(frozen[n],p.detach().cpu()) for n,p in model.policy.features_extractor.named_parameters() if n in frozen)
        assert all(torch.isfinite(x).all() for x in model.policy.state_dict().values())
        model.save(output/'final.zip');restored=MaskablePPO.load(output/'final.zip',device='cpu')
        assert restored.num_timesteps==model.num_timesteps and sha256(parent)==before
        assert optimizer_steps(restored)==8196
        report=dict(decisions=128,adam_updates=optimizer_steps(model)-steps,episodes=len(callback.rows),
            native_reward_ledger=True,no_terminal_bootstrap=True,frozen_prior_and_wait_unchanged=True,reload=True,finite=True,
            seconds=time.monotonic()-start,checkpoint_sha256=sha256(output/'final.zip'),parent_sha256=before,
            limits='Disposable2-worker synchronous integration smoke through actual trainer worker factory. No performance claim or production promotion.')
        (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
        (archive/'resume-smoke-verification.json').write_text(json.dumps(report,indent=2)+'\n')
        (archive/'resume-smoke-config.json').write_text(json.dumps(args,indent=2)+'\n')
        (archive/'resume-smoke-episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in callback.rows))
        print(report,flush=True)
    finally:
        env.close()


if __name__=='__main__':main()
