"""Trusted-local frozen loads and narrowly checked runner migration. No learning."""
import hashlib
from pathlib import Path
import torch
from hierarchy_checkpoint import SCHEMA,load_checkpoint
from hierarchy_rollout import policy_fingerprint

LEGACY_RUNNER='1d7a0cad97ef9c8579de93262c78035e7570c189bab284898c6995769bbd85f6'

# Verified collector-only transition for the initial one-build pilot.
SINGLE_BUILD_ENVIRONMENT = (
    '11663479eb97904b125f3ce217547fe0c8c5ff34d6fe2d35fbd93261c8d1196b',
    '927df9ba9f953c59b4d00e6fc9c27e8288c9f707a2c2353357e00bee25e741ad',
)
SINGLE_BUILD_COLLECTOR = {
    'parallel_stage1.py': (
        '8193f5e3c7e6e40b6147f1750a5f5a379abbe781a0b7c581920e5c7fcb8e4359',
        'b7a1eeef0e5485bfc038116e0449f3ad49b33d1e266d1bf7369d65b1cb9c55f8',
    ),
    'hierarchy_rollout.py': (
        '8e400ce67ec13b1ea8d3e3accaa2954ef4414dad60a94182879ffd698ba7ae74',
        'e98479c49ac509aa4fffddb19f5dce1b9f4b9183f2ffe3bf892a4c1549d79a89',
    ),
    'train_parallel_stage1.py': (
        '0dd4e8834f1087d36aaef0636b6d461d8418bb6a0427676665123f3f376e8641',
        '51cff3c30b13043c51bf1e21d11c4b84c727196efa8bd4b94571d007c1c7d100',
    ),
    'checkpoint_tools.py': (
        '2d22cfe8a6e8161ba53e2f04eecd8091730d8ff977fdc11dc82b4bc5e57199dd',
        None,
    ),
}


def migrate_single_build_config(saved, current):
    """Map the exact prior collector identity while checking every other setting."""
    if saved.get('stage') != 'one-gap-single-build' or saved.get('reward_mode') != 'single-build':
        return saved
    name = 'training/connection_practice.py'
    environment = saved['environment']
    old_env_hash, new_env_hash = SINGLE_BUILD_ENVIRONMENT
    if environment['source_hashes'].get(name) != old_env_hash:
        return saved
    old_hashes = saved['source_hashes']
    new_hashes = current['source_hashes']
    migrated_hashes = dict(old_hashes)
    for file, (old, new) in SINGLE_BUILD_COLLECTOR.items():
        expected = new if new is not None else hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if old_hashes.get(file) != old or new_hashes.get(file) != expected:
            return saved
        migrated_hashes[file] = expected
    migrated_environment = dict(environment, source_hashes={**environment['source_hashes'], name: new_env_hash})
    return dict(saved, source_hashes=migrated_hashes, environment=migrated_environment)


def read_checkpoint(path):
    payload=torch.load(path,map_location='cpu',weights_only=False)
    if payload.get('schema')!=SCHEMA:raise ValueError('Checkpoint schema mismatch')
    class View:
        def state_dict(self):return payload['parameters']
    if policy_fingerprint(View())!=payload['policy_sha256']:raise ValueError('Checkpoint weight hash mismatch')
    return payload

def load_frozen(path,policy,environment):
    payload=read_checkpoint(path);config=payload['config']
    if config['environment'] != environment and config.get('stage') == 'one-gap-single-build':
        current_hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in config['source_hashes']}
        current = dict(config, source_hashes=current_hashes, environment=environment)
        if migrate_single_build_config(config, current) != current:
            raise ValueError('Checkpoint environment/source/build differs')
    elif config['environment'] != environment:
        raise ValueError('Checkpoint environment/source/build differs')
    source=Path(__file__).with_name('hierarchy_policy.py')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=config['source_hashes']['hierarchy_policy.py']:
        raise ValueError('Policy code differs')
    policy.load_state_dict(payload['parameters'],strict=True);policy.set_training_mode(False)
    if policy_fingerprint(policy)!=payload['policy_sha256']:raise ValueError('Loaded policy hash differs')
    return payload

def resume_checkpoint(path,policy,current_config):
    payload=read_checkpoint(path);saved=payload['config']
    candidate=dict(saved);hashes=dict(saved['source_hashes'])
    runner='train_parallel_stage1.py'
    if hashes.get(runner)==LEGACY_RUNNER:
        hashes[runner]=current_config['source_hashes'][runner]
        hashes['checkpoint_tools.py']=current_config['source_hashes']['checkpoint_tools.py']
    candidate['source_hashes']=hashes
    candidate = migrate_single_build_config(candidate, current_config)
    if candidate!=current_config:raise ValueError('Resume configuration/source differs; keep original stage, workers, device, threads, seed, rollout and minibatch settings')
    counters=load_checkpoint(path,policy,expected_config=saved)
    if any(int(counters.get(k,-1))<0 for k in ('tokens','updates','version','episodes')):
        raise ValueError('Invalid checkpoint counters')
    return payload,counters
