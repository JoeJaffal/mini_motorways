"""Frozen inference collection and two-level bookkeeping; no optimization calls.

This module deliberately cannot train. It retains behavior masks/probabilities,
values, exact time, role boundaries and partial options for a future PPO updater.
"""
from dataclasses import dataclass,field
import hashlib

import numpy as np
import torch


def policy_fingerprint(policy):
    digest=hashlib.sha256()
    for name,tensor in sorted(policy.state_dict().items()):
        tensor=tensor.detach().cpu().contiguous()
        digest.update(name.encode());digest.update(str((tuple(tensor.shape),tensor.dtype)).encode())
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def copied_observation(obs):
    return {k:np.array(v,copy=True) for k,v in obs.items()}


@dataclass(frozen=True)
class TokenTransition:
    observation:dict
    mask:np.ndarray
    action:int
    log_probability:float
    value:float
    role:str
    next_role:str
    reward:float
    start_tick:int
    end_tick:int
    terminated:bool
    truncated:bool
    ending_reason:str|None
    policy_version:str
    focus:tuple


@dataclass(frozen=True)
class InferenceBatch:
    transitions:tuple
    final_observation:dict|None
    bootstrap_value:float
    policy_version:str
    policy_sha256:str
    score_delta:float


class FrozenInferenceCollector:
    def __init__(self,env,policy,*,seed):
        self.env,self.policy=env,policy
        self.versions={}
        self.reset(seed=seed)

    def reset(self,*,seed):
        self.observation,_=self.env.reset(seed=seed)
        self._last_version=None

    def collect(self,*,max_tokens,policy_version,deterministic=False):
        if max_tokens<1 or not policy_version:raise ValueError('Explicit positive token bound and policy version required')
        if self.env.done:raise RuntimeError('Episode ended; reset explicitly before another collection')
        fingerprint=policy_fingerprint(self.policy)
        if policy_version in self.versions and self.versions[policy_version]!=fingerprint:
            raise RuntimeError('Behavior weights changed without a new policy version')
        if self._last_version is not None and policy_version!=self._last_version and self.env.role!='primary':
            raise RuntimeError('Cannot change behavior version within a focus')
        self.versions[policy_version]=fingerprint
        self._last_version=policy_version
        self.policy.set_training_mode(False)
        score=self.env.raw['tripsCompleted']
        expected_before=self.env.expected_training_return()
        records=[]
        for _ in range(max_tokens):
            obs=self.observation
            mask=self.env.action_masks()
            role=self.env.role
            start_tick=round(self.env.raw['time']/.05)
            focus=tuple(self.env.focus)
            with torch.inference_mode():
                tensor,_=self.policy.obs_to_tensor(obs)
                action,value,logp=self.policy.forward(tensor,deterministic=deterministic,action_masks=mask)
            action=int(action.cpu().numpy().reshape(-1)[0])
            self.observation,reward,terminated,truncated,info=self.env.step(action)
            records.append(TokenTransition(copied_observation(obs),mask.copy(),action,
                float(logp.cpu().numpy().reshape(-1)[0]),float(value.cpu().numpy().reshape(-1)[0]),
                role,self.env.role,float(reward),start_tick,round(self.env.raw['time']/.05),
                bool(terminated),bool(truncated),info['ending_reason'],policy_version,focus))
            if terminated or truncated:break
        with torch.inference_mode():
            if records[-1].terminated:bootstrap=0.
            else:
                tensor,_=self.policy.obs_to_tensor(self.observation)
                bootstrap=float(self.policy.predict_values(tensor).cpu().numpy().reshape(-1)[0])
        if policy_fingerprint(self.policy)!=fingerprint:
            raise RuntimeError('Policy changed during a supposedly frozen collection')
        score_delta=float(self.env.raw['tripsCompleted']-score)
        if not np.isclose(sum(r.reward for r in records),self.env.expected_training_return()-expected_before,atol=1e-7,rtol=1e-7):
            raise RuntimeError('Environment reward ledger does not telescope')
        return InferenceBatch(tuple(records),copied_observation(self.observation),bootstrap,
                              policy_version,fingerprint,score_delta)


@dataclass
class FocusInterval:
    primary:TokenTransition
    secondary:TokenTransition
    executor:list=field(default_factory=list)
    complete:bool=False

    @property
    def focus(self):
        def coordinate(action):return None if action==1500 else (action%50,action//50)
        return coordinate(self.primary.action),coordinate(self.secondary.action)

    @property
    def reward(self):return sum(t.reward for t in self.executor)
    @property
    def duration_ticks(self):return sum(t.end_tick-t.start_tick for t in self.executor)
    @property
    def behavior_log_probability(self):return self.primary.log_probability+self.secondary.log_probability
    @property
    def terminated(self):return self.executor[-1].terminated if self.executor else self.secondary.terminated
    @property
    def truncated(self):return self.executor[-1].truncated if self.executor else self.secondary.truncated


class FocusAssembler:
    """Carries partial manager selection/options across buffer boundaries."""
    def __init__(self):
        self.pending_primary=None
        self.active=None
        self.completed=[]
        self.version=None
        self.partial_selections=[]
        self.ended=False

    def append(self,transitions):
        for t in transitions:
            if self.ended:raise RuntimeError('New episode requires a new assembler')
            if t.end_tick<t.start_tick or t.start_tick<0:
                raise ValueError('Invalid transition duration')
            if not all(np.isfinite(v) for v in (t.reward,t.value,t.log_probability)):
                raise ValueError('Invalid reward/value/probability record')
            if t.mask.shape!=(1501,) or not 0<=t.action<1501 or not t.mask[t.action]:
                raise ValueError('Recorded action is outside its behavior mask')
            if self.version is None:self.version=t.policy_version
            if t.policy_version!=self.version:
                if self.pending_primary is not None or self.active is not None:
                    raise RuntimeError('Cannot change behavior version in a partial focus')
                self.version=t.policy_version
            if t.role=='primary':
                if self.pending_primary is not None or self.active is not None:
                    raise RuntimeError('Manager selection started before previous focus ended')
                if t.reward!=0:raise RuntimeError('Paused manager selection emitted score')
                if t.end_tick!=t.start_tick:raise RuntimeError('Manager selection advanced game time')
                self.pending_primary=t
                if t.terminated or t.truncated:
                    self.partial_selections.append(t)
                    self.pending_primary=None
            elif t.role=='secondary':
                if self.pending_primary is None or self.active is not None:
                    raise RuntimeError('Secondary selection lacks its primary context')
                if t.reward!=0:raise RuntimeError('Paused manager selection emitted score')
                if t.end_tick!=t.start_tick:raise RuntimeError('Manager selection advanced game time')
                self.active=FocusInterval(self.pending_primary,t)
                self.pending_primary=None
                if t.terminated or t.truncated:
                    self.active.complete=True
                    self.completed.append(self.active)
                    self.active=None
            elif t.role=='executor':
                if self.active is None:raise RuntimeError('Executor transition lacks manager focus')
                self.active.executor.append(t)
                if t.next_role=='primary' or t.terminated or t.truncated:
                    self.active.complete=True
                    self.completed.append(self.active)
                    self.active=None
            else:raise ValueError('Unknown role')
            self.ended=bool(t.terminated or t.truncated)
        return self.completed


def generalized_advantages(*,rewards,values,next_values,terminated,trace_ends,durations,trace_lambda,trace_units):
    """Gamma=1 GAE with explicit trace units. No default lambda or unit is chosen.

    trace_ends includes rollout cuts/operational interruptions; those bootstrap
    using next_values. Only genuine termination suppresses bootstrap. A focus
    handoff is not a terminal flag. Inputs may represent either level.
    """
    if trace_units not in ('policy_tokens','simulation_ticks','simulation_seconds'):
        raise ValueError('Trace units must be recorded explicitly')
    if not 0<=trace_lambda<=1:raise ValueError('Trace lambda must be explicit and bounded')
    arrays=[np.asarray(x) for x in (rewards,values,next_values,terminated,trace_ends,durations)]
    if not arrays or arrays[0].ndim!=1 or any(a.shape!=arrays[0].shape for a in arrays):
        raise ValueError('Inconsistent return arrays')
    r,v,nv,done,cuts,duration=arrays
    if not all(np.isfinite(a).all() for a in (r,v,nv,duration)) or (duration<0).any():
        raise ValueError('Invalid returns or duration')
    if not np.isin(done,[0,1]).all() or not np.isin(cuts,[0,1]).all():
        raise ValueError('Ending flags must be boolean')
    if trace_units!='simulation_seconds' and not np.equal(duration,np.floor(duration)).all():
        raise ValueError('Discrete trace units require integer durations')
    advantage=np.zeros_like(r,dtype=np.float64)
    following=0.
    for i in range(len(r)-1,-1,-1):
        delta=r[i]+(0 if done[i] else nv[i])-v[i]
        decay=trace_lambda**duration[i]
        following=delta+(0 if done[i] or cuts[i] else decay*following)
        advantage[i]=following
    return advantage,advantage+v
