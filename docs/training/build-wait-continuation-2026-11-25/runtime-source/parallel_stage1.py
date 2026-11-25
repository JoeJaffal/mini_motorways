"""Shared frozen policy, batched decisions, independent parallel native hosts.

Streams stop at their own focus/episode boundary before a shared policy update.
Never concatenate workers' rewards into one temporal trajectory.
"""
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
import numpy as np
import torch
from hierarchy_rollout import TokenTransition,InferenceBatch,copied_observation,policy_fingerprint
from hierarchy_batches import prepare_batches


class ParallelCollector:
    def __init__(self,environments,policy,*,seeds,on_transition=None):
        if not environments or len(environments)!=len(seeds):raise ValueError('One seed per host required')
        self.envs,self.policy=environments,policy
        self.direct = getattr(environments[0], 'direct', False)
        self.boundary_role = 'executor' if self.direct else 'primary'
        self.single_build = all(getattr(env, 'single_build', False) for env in environments)
        self.pool=ThreadPoolExecutor(max_workers=len(environments))
        self.observations=[None]*len(environments)
        self.on_transition=on_transition
        self.versions={}
        try:
            if self.single_build:
                self.reset_many(enumerate(seeds))
            else:
                for i, seed in enumerate(seeds):
                    self.reset(i, seed)
        except BaseException:
            self.pool.shutdown(wait=True)
            raise

    def reset(self,worker,seed):
        self.observations[worker],_=self.envs[worker].reset(seed=seed)

    def reset_many(self, worker_seeds):
        for _ in self.pool.map(lambda pair: self.reset(*pair), worker_seeds):
            pass

    def _sample(self, active, masks, *, deterministic):
        obs = {key: np.stack([self.observations[i][key] for i in active])
               for key in self.observations[active[0]]}
        with torch.inference_mode():
            tensor, _ = self.policy.obs_to_tensor(obs)
            actions, values, logps = self.policy.forward(tensor, deterministic=deterministic,
                                                       action_masks=np.stack(masks))
        return (actions.cpu().numpy().reshape(-1), values.cpu().numpy().reshape(-1),
                logps.cpu().numpy().reshape(-1))

    def _freeze(self, version):
        fingerprint = policy_fingerprint(self.policy)
        if version in self.versions and self.versions[version] != fingerprint:
            raise RuntimeError('Behavior weights changed without a new version')
        self.versions[version] = fingerprint
        self.policy.set_training_mode(False)
        return fingerprint

    def collect_single_builds(self, *, target_tokens, deadline, policy_version, reset_completed, deterministic=False):
        """Collect independent terminal attempts under one frozen policy version."""
        if not self.single_build or target_tokens < 1:
            raise ValueError('Single-build environments and a positive attempt bound are required')
        before = self._freeze(policy_version)
        collections = []
        while len(collections) < target_tokens:
            if monotonic() >= deadline:
                raise TimeoutError('Collection wall budget exhausted; incomplete rollout discarded')
            active = [i for i, env in enumerate(self.envs) if not env.done][:target_tokens-len(collections)]
            if not active:
                raise RuntimeError('Reset required before single-build collection')
            masks = list(self.pool.map(lambda i: self.envs[i].action_masks(), active))
            actions, values, logps = self._sample(active, masks, deterministic=deterministic)
            results = self.pool.map(lambda pair: self.envs[pair[0]].step_single_build(int(pair[1])),
                                    zip(active, actions))
            for row, (i, result) in enumerate(zip(active, results)):
                _, reward, terminated, truncated, info = result
                env = self.envs[i]
                if not terminated or truncated or info['seconds'] != 0 or info['trips'] != 0:
                    raise RuntimeError('Single-build attempt must terminate immediately')
                if reward not in (0., 1.) or reward != env.expected_training_return():
                    raise RuntimeError('Single-build reward ledger mismatch')
                record = TokenTransition(copied_observation(self.observations[i]), masks[row].copy(),
                                         int(actions[row]), float(logps[row]), float(values[row]),
                                         'executor', 'executor', float(reward), 0, 0, True, False,
                                         info['ending_reason'], policy_version, (None, None))
                self.observations[i] = None
                collections.append((i, InferenceBatch((record,), None, 0., policy_version, before, 0.)))
                if self.on_transition is not None:
                    self.on_transition(i, record, info)
            if len(collections) < target_tokens:
                reset_completed()
        if policy_fingerprint(self.policy) != before:
            raise RuntimeError('Frozen parallel collection changed policy')
        return collections

    def close(self):self.pool.shutdown(wait=True)

    def collect(self,*,target_tokens,hard_limit,deadline,policy_version,deterministic=False):
        if target_tokens<1 or hard_limit<1:raise ValueError('Positive collection limits required')
        if any(not e.done and e.role!=self.boundary_role for e in self.envs):
            raise RuntimeError('Collection must begin at a policy boundary')
        before = self._freeze(policy_version)
        streams=[[] for _ in self.envs];count=0
        scores=[e.raw['tripsCompleted'] for e in self.envs]
        expected_before=[e.expected_training_return() for e in self.envs]
        while True:
            active=[i for i,e in enumerate(self.envs) if not e.done and
                    (count<target_tokens or e.role!=self.boundary_role)]
            if not active:break
            if monotonic()>=deadline:raise TimeoutError('Collection wall budget exhausted; incomplete rollout discarded')
            if count>=hard_limit:raise TimeoutError('Global token budget cuts active focuses; incomplete rollout discarded')
            limit = min(target_tokens, hard_limit) if self.direct else hard_limit
            active = active[:limit-count]
            masks=list(self.pool.map(lambda i:self.envs[i].action_masks(),active))
            actions, values, logps = self._sample(active, masks, deterministic=deterministic)
            before_context=[(self.envs[i].role,round(self.envs[i].raw['time']/.05),tuple(self.envs[i].focus)) for i in active]
            results=list(self.pool.map(lambda pair:self.envs[pair[0]].step(int(pair[1])),zip(active,actions)))
            for row,(i,result) in enumerate(zip(active,results)):
                after,reward,terminated,truncated,info=result
                role,start,focus=before_context[row]
                record=TokenTransition(copied_observation(self.observations[i]),masks[row].copy(),int(actions[row]),
                    float(logps[row]),float(values[row]),role,self.envs[i].role,float(reward),start,
                    round(info['seconds']/.05),bool(terminated),bool(truncated),info['ending_reason'],policy_version,focus)
                streams[i].append(record);self.observations[i]=after;count+=1
                if self.on_transition:self.on_transition(i,record,info)
        if policy_fingerprint(self.policy)!=before:raise RuntimeError('Frozen parallel collection changed policy')
        collections=[]
        for i,records in enumerate(streams):
            if not records:continue
            env=self.envs[i]
            if not env.done and env.role!=self.boundary_role:raise RuntimeError('Worker focus unfinished')
            with torch.inference_mode():
                tensor,_=self.policy.obs_to_tensor(self.observations[i])
                bootstrap=0. if records[-1].terminated else float(self.policy.predict_values(tensor).item())
            delta=float(env.raw['tripsCompleted']-scores[i])
            if not np.isclose(sum(t.reward for t in records),env.expected_training_return()-expected_before[i],atol=1e-7,rtol=1e-7):raise RuntimeError('Per-worker reward ledger mismatch')
            collections.append((i,InferenceBatch(tuple(records),copied_observation(self.observations[i]),bootstrap,
                                                 policy_version,before,delta)))
        return collections


def parallel_batches(collections,*,device,minibatch_size,direct=False,single_build=False):
    """Compute returns per worker, then pool/normalize by role on CPU.

    Only minibatches are transferred to the selected device by the update engine.
    """
    if minibatch_size<1:raise ValueError('Positive minibatch size required')
    versions={(c.policy_version,c.policy_sha256) for _,c in collections}
    if len(versions)!=1:raise ValueError('Cannot mix behavior versions')
    worker_ids=[i for i,_ in collections]
    if single_build:
        if not direct or any(len(c.transitions) != 1 or not c.transitions[0].terminated
                             or c.transitions[0].truncated for _, c in collections):
            raise ValueError('Expected independent one-build episodes')
    elif len(worker_ids)!=len(set(worker_ids)):
        raise ValueError('Duplicate worker streams')
    parts=[b for _,c in collections for b in prepare_batches(c,device='cpu',minibatch_size=minibatch_size,normalize_advantage=False,direct=direct)]
    roles={b['role'] for b in parts};output=[]
    for role in sorted(roles):
        rows=[b for b in parts if b['role']==role]
        tensors={};nested={}
        for key,value in rows[0].items():
            if isinstance(value,torch.Tensor):tensors[key]=torch.cat([b[key] for b in rows])
            elif isinstance(value,dict):nested[key]={name:torch.cat([b[key][name] for b in rows]) for name in value}
        advantage=tensors['advantages']
        if len(advantage)>1:tensors['advantages']=(advantage-advantage.mean())/(advantage.std()+1e-8)
        n=len(advantage)
        for start in range(0,n,minibatch_size):
            end=min(start+minibatch_size,n)
            batch={key:value[start:end] for key,value in tensors.items()}
            batch.update({key:{k:v[start:end] for k,v in value.items()} for key,value in nested.items()})
            batch.update(role=role,level_weight=(end-start)/n/len(roles),normalize_advantage=False)
            if role=='manager':batch['joint_entropy_estimator']=rows[0]['joint_entropy_estimator']
            output.append(batch)
    return output


def batch_to_device(batch,device):
    return {key:({name:value.to(device) for name,value in item.items()} if isinstance(item,dict)
                 else item.to(device) if isinstance(item,torch.Tensor) else item) for key,item in batch.items()}
