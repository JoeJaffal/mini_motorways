"""Exact token/focus replay for Stage 1, without training or stored policy weights."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from connection_practice import ConnectionPractice,DRAW,ERASE,REMOVE,WAIT,HANDOFF,CANCEL,NONE
from environment import DIRS

SCHEMA='maskable-hierarchy-replay-v1'
ROOT=Path(__file__).resolve().parents[1]
SOURCE_FILES=('training/connection_practice.py','training/visible_observation.py',
    'training/environment.py','training/practice_replay.py','training/practice_reward.py',
    'simulation/Headless/Program.cs','simulation/Assets/Simulation/PracticeScenario.cs',
    'simulation/Assets/Simulation/PracticeLegality.cs')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observation_hash(obs):
    digest=hashlib.sha256()
    for key,array in sorted(obs.items()):
        array=np.ascontiguousarray(array)
        digest.update(json.dumps([key,array.shape,array.dtype.str],separators=(',',':')).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def identity(env):
    return dict(environment_schema=env.schema,protocol=env.protocol_version,
        simulator=env.simulator_version,dll_sha256=file_hash(env.host.process.args[1]),
        source_hashes={name:file_hash(ROOT/name) for name in SOURCE_FILES})


def describe(env,action):
    if env.direct:
        if action == WAIT:
            return 'Wait up to one simulated second'
        start, end = env.direct_endpoints(action)
        return f'Draw connection {start} to {end}'
    if env.role=='primary':return 'Manager focus: '+str((action%50,action//50))
    if env.role=='secondary':return 'No second focus' if action==NONE else 'Manager second focus: '+str((action%50,action//50))
    if env.phase and action==CANCEL:return 'Cancel selection and keep current focus'
    if env.phase==0:
        return {WAIT:'Wait up to one simulated second',DRAW:'Choose connection tool',ERASE:'Choose connection eraser',
                REMOVE:'Choose tile removal',HANDOFF:'Return control to manager'}.get(action,'Unsupported Stage 1 control')
    if env.phase==1:return ('Remove tile ' if env.tool==REMOVE else 'Choose starting tile ')+str((action%50,action//50))
    dx,dy=DIRS[action]
    target=(env.first[0]+dx,env.first[1]+dy)
    return ('Draw connection ' if env.tool==DRAW else 'Erase connection ')+str(env.first)+' -> '+str(target)


class PracticeRecorder:
    def __init__(self,env,*,seed):
        self.env=env
        obs,_=env.reset(seed=seed)
        self.trace=dict(schema=SCHEMA,identity=identity(env),seed=int(seed),split=env.split,stage=env.stage,reward_mode=env.reward_mode,
            max_paused_tokens=env.max_paused_tokens,initial_observation=observation_hash(obs),
            tokens=[],complete=False,ending_reason='partial',score=0,seconds=0.)
        self.initial_observation=obs

    def step(self,action):
        before=dict(role=self.env.role,phase=self.env.phase)
        description=describe(self.env,int(action))
        obs,reward,terminated,truncated,info=self.env.step(action)
        self.trace['tokens'].append(dict(action=int(action),before=before,
            description=description,
            after=dict(role=self.env.role,phase=self.env.phase),
            focus=[list(p) if p is not None else None for p in self.env.focus],
            observation=observation_hash(obs),reward=reward,
            score=info['trips'],seconds=info['seconds'],terminated=terminated,truncated=truncated,
            ending_reason=info['ending_reason']))
        self.trace.update(complete=terminated or truncated,ending_reason=info['ending_reason'] or 'partial',
                          score=info['trips'],seconds=info['seconds'])
        return obs,reward,terminated,truncated,info

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.tmp')
        temporary.write_text(json.dumps(self.trace,indent=2,allow_nan=False)+'\n')
        temporary.replace(path)


def verify(path,dotnet='dotnet',host_dll=None):
    trace=json.loads(Path(path).read_text())
    if trace.get('schema')!=SCHEMA:raise ValueError('Unsupported replay schema')
    env=ConnectionPractice(dotnet=dotnet,host_dll=host_dll,split=trace['split'],stage=trace.get('stage','clear'),reward_mode=trace.get('reward_mode','score'),
                           max_paused_tokens=trace['max_paused_tokens'])
    try:
        if identity(env)!=trace['identity']:
            raise ValueError('Replay source/build/protocol differs from current environment')
        recorder=PracticeRecorder(env,seed=trace['seed'])
        if recorder.trace['initial_observation']!=trace['initial_observation']:
            raise ValueError('Replay initial observation differs')
        for index,event in enumerate(trace['tokens']):
            recorder.step(event['action'])
            if recorder.trace['tokens'][-1]!=event:
                raise ValueError('Replay diverged at token '+str(index))
        for key in ('complete','ending_reason','score','seconds'):
            if recorder.trace[key]!=trace[key]:raise ValueError('Replay summary differs: '+key)
        return dict(result='PASS',tokens=len(trace['tokens']),complete=trace['complete'],
                    ending_reason=trace['ending_reason'],score=trace['score'],seconds=trace['seconds'])
    finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('replay');p.add_argument('--dotnet',default='dotnet')
    p.add_argument('--dll',default='simulation/Headless/bin/Release/net8.0/TrafficHost.dll')
    args=p.parse_args()
    print(json.dumps(verify(args.replay,args.dotnet,args.dll),indent=2))
