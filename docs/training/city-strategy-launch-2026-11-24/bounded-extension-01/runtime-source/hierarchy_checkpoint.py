"""Atomic trusted-local checkpoints. Never deserialize arbitrary remote weights."""
import os
from pathlib import Path
import random
import numpy as np
import torch
from hierarchy_rollout import policy_fingerprint

SCHEMA='maskable-hierarchy-checkpoint-v1'

def save_checkpoint(path,policy,*,config,counters):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload=dict(schema=SCHEMA,parameters=policy.state_dict(),optimizer=policy.optimizer.state_dict(),
        config=config,counters=counters,policy_sha256=policy_fingerprint(policy),
        python_rng=random.getstate(),numpy_rng=np.random.get_state(),torch_rng=torch.get_rng_state(),
        cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None)
    temporary=path.with_name(path.name+'.tmp')
    try:
        with temporary.open('wb') as stream:
            torch.save(payload,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()

def load_checkpoint(path,policy,*,expected_config):
    payload=torch.load(path,map_location=policy.device,weights_only=False)
    if payload.get('schema')!=SCHEMA or payload.get('config')!=expected_config:
        raise ValueError('Checkpoint schema/configuration mismatch')
    class StateView:
        def state_dict(self):return payload['parameters']
    if policy_fingerprint(StateView())!=payload['policy_sha256']:raise ValueError('Checkpoint weight hash mismatch')
    if payload['cuda_rng'] is not None and not torch.cuda.is_available():raise ValueError('Exact CUDA RNG restoration requires CUDA')
    policy.load_state_dict(payload['parameters'],strict=True)
    if policy_fingerprint(policy)!=payload['policy_sha256']:raise ValueError('Checkpoint weight hash mismatch')
    policy.optimizer.load_state_dict(payload['optimizer'])
    random.setstate(payload['python_rng']);np.random.set_state(payload['numpy_rng'])
    torch.set_rng_state(payload['torch_rng'].cpu())
    if payload['cuda_rng'] is not None:
        if not torch.cuda.is_available():raise ValueError('Exact CUDA RNG restoration requires CUDA')
        torch.cuda.set_rng_state_all([x.cpu() for x in payload['cuda_rng']])
    return payload['counters']
