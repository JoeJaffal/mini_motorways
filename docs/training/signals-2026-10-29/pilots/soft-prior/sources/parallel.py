"""Parallel C# hosts with shared-memory Python observations and batched policy calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from functools import partial
from pathlib import Path

import numpy as np
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

from environment import TrafficEnv


def make_worker(worker, output=None, **kwargs):
    monitor = None if output is None else str(Path(output)/f'worker-{worker:02d}.monitor.csv')
    return Monitor(TrafficEnv(**kwargs),monitor,
                   info_keywords=('trips','seconds','rejected_actions'))


class ParallelHostVecEnv(DummyVecEnv):
    """Independent .NET processes execute concurrently; arrays stay in Python.

    Avoids sending 300 KB grid observations through an additional Python-process
    pipe on every selection. JSON encoding/decoding still shares Python's GIL;
    this is measured, not assumed to scale. Simulation itself runs in .NET.
    """
    def __init__(self, factories):
        super().__init__(factories)
        self.executor=ThreadPoolExecutor(max_workers=self.num_envs,thread_name_prefix='traffic-host')
        self.pending=None
        self.closed=False

    def _step_worker(self, i, action):
        obs,reward,terminated,truncated,info=self.envs[i].step(action)
        done=terminated or truncated
        info['worker']=i
        info['TimeLimit.truncated']=truncated and not terminated
        reset_info=None
        if done:
            info['terminal_observation']=obs
            obs,reset_info=self.envs[i].reset()
        return obs,reward,done,info,reset_info

    def step_async(self,actions):
        if self.pending is not None:
            raise RuntimeError('A parallel step is already pending')
        self.actions=actions
        self.pending=[self.executor.submit(self._step_worker,i,action) for i,action in enumerate(actions)]

    def wait_pending(self):
        if self.pending is not None:
            # Keep pending references if Ctrl+C interrupts the wait, so shutdown
            # can finish host requests before reading partial recordings.
            results=[];errors=[]
            for future in self.pending:
                try:results.append(future.result())
                except Exception as error:results.append(None);errors.append(error)
            self.pending=None
            for i,result in enumerate(results):
                if result is None:continue
                obs,reward,done,info,reset_info=result
                self.buf_rews[i]=reward;self.buf_dones[i]=done;self.buf_infos[i]=info
                if reset_info is not None:self.reset_infos[i]=reset_info
                self._save_obs(i,obs)
            if errors:raise RuntimeError(f'{len(errors)} parallel worker(s) failed: {errors[0]}') from errors[0]

    def step_wait(self):
        self.wait_pending()
        return self._obs_from_buf(),self.buf_rews.copy(),self.buf_dones.copy(),deepcopy(self.buf_infos)

    def close(self):
        if self.closed:return
        self.executor.shutdown(wait=True,cancel_futures=False)
        try:
            for env in self.envs:
                try:env.close()
                except (OSError,ValueError):pass
        finally:self.closed=True


def make_vector(workers,output=None,**kwargs):
    factories=[partial(make_worker,i,output,**kwargs) for i in range(workers)]
    return ParallelHostVecEnv(factories) if workers>1 else DummyVecEnv(factories)
