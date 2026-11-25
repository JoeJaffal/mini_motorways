"""Scripted feasibility, frozen evaluations and training for construction practice."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic

import numpy as np
import torch
from torch import nn

from checkpoint_tools import load_frozen, read_checkpoint
from connection_practice import ARENA_SIZE, SINGLE_BUILD_STAGE, ConnectionPractice
from construction_practice import (
    ACTIONS, EDGE_END, EXERCISES, INPUT_CHANNELS, ConstructionPractice, verified_original_identity,
)
from edge_policy import checkpoint_policy
from hierarchy_rollout import policy_fingerprint

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'construction-conv-v1'


class ConstructionPolicy(nn.Module):
    def __init__(self):
        super().__init__()
        width = 48
        self.inputs = nn.Conv2d(INPUT_CHANNELS, width, 3, padding=1)
        self.layers = nn.ModuleList(nn.Conv2d(width, width, 3, padding=dilation, dilation=dilation)
                                    for dilation in (1, 2, 3, 1))
        self.edges = nn.Conv2d(width, 4, 1)
        self.house_actions = nn.Conv2d(width, 9, 1)

    def forward(self, observation):
        features = torch.nn.functional.silu(self.inputs(observation))
        for layer in self.layers:
            features = features + torch.nn.functional.silu(layer(features))
        edges = self.edges(features).permute(0, 2, 3, 1).flatten(1)
        house = (self.house_actions(features) * observation[:, 2:3]).sum(dim=(2, 3))
        return torch.cat((house[:, :1], edges, house[:, 1:]), dim=1)


@dataclass
class Trial:
    env: ConstructionPractice
    stage: str
    seed: int


def file_sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def sources():
    files = ('training/construction_curriculum.py', 'training/construction_practice.py',
             'simulation/Headless/Program.cs', 'simulation/Assets/Simulation/ConstructionCurriculum.cs',
             'simulation/Assets/Simulation/PracticeLegality.cs')
    return {name: file_sha(ROOT/name) for name in files}


def write(path, data):
    with path.open('x') as out:
        json.dump(data, out, indent=2)
        out.write('\n')


class Workers:
    def __init__(self, count, dll):
        self.envs = []
        try:
            for _ in range(count):
                self.envs.append(ConstructionPractice(dll))
        except BaseException:
            self.close()
            raise
        self.pool = ThreadPoolExecutor(max_workers=count)

    def map(self, function, entries):
        work = list(entries)
        futures = [self.pool.submit(function, item) for item in work]
        return [future.result() for future in futures]

    def close(self):
        if hasattr(self, 'pool'):
            self.pool.shutdown(wait=True)
        for env in self.envs:
            env.close()


def generate_trials(workers, stages, count, split):
    for stage in stages:
        stage_id = EXERCISES.index(stage)
        seed_base = (30000 if split == 'validation' else 1000) + 2000*stage_id
        for offset in range(0, count, len(workers.envs)):
            size = min(count-offset, len(workers.envs))
            yield [Trial(env, stage, seed_base+offset+i) for i, env in enumerate(workers.envs[:size])]


def scripted(trial, split, *, examples=False):
    env = trial.env
    env.reset(trial.stage, split, trial.seed)
    actions = env.reference()
    seen = []
    executed = []
    for action in actions:
        if not env.legal[action]:
            raise RuntimeError(f'{trial.stage} seed {trial.seed} has a masked scripted action {action}')
        if examples:
            seen.append((env.observation(), env.aligned_mask(), int(env.to_aligned[action])))
        ended = env.step(action)
        executed.append(action)
        if ended:
            break
        env.mask()
    if not env.connected() or len(executed) > env.edit_limit:
        raise RuntimeError(f'{trial.stage} seed {trial.seed} script did not connect within the budget')
    if examples:
        return seen
    trips, time = env.deliveries()
    if trips < 3:
        raise RuntimeError(f'{trial.stage} seed {trial.seed} script had only {trips} deliveries')
    return dict(stage=trial.stage, seed=trial.seed, actions=executed,
                connected=True, trips=trips, seconds=time, supported=True,
                inventory=env.inventory, edit_limit=env.edit_limit)


def train(args, workers, output):
    device = torch.device(args.device)
    model = ConstructionPolicy().to(device)
    if args.start_from:
        model.load_state_dict(load_model(args.start_from, args.dll, device).state_dict())
    examples = []
    for group in generate_trials(workers, args.stages, args.examples, 'train'):
        samples = workers.map(lambda trial: scripted(trial, 'train', examples=True), group)
        examples.extend(item for trajectory in samples for item in trajectory)
    observations, masks, actions = zip(*examples)
    states = torch.as_tensor(np.stack(observations), device=device)
    legal = torch.as_tensor(np.stack(masks), device=device)
    targets = torch.as_tensor(actions, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    initial = policy_fingerprint(model)
    progress = []
    for epoch in range(args.epochs):
        total_loss = 0.
        correct = 0
        for ids in torch.randperm(len(targets), device=device).split(128):
            logits = model(states[ids]).masked_fill(~legal[ids], -torch.inf)
            loss = nn.functional.cross_entropy(logits, targets[ids])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()*len(ids)
            correct += int((logits.argmax(dim=1)==targets[ids]).sum())
        row = dict(epoch=epoch+1, loss=total_loss/len(targets), accuracy=correct/len(targets))
        progress.append(row)
        if (epoch+1) % 5 == 0 or epoch in (0, args.epochs-1):
            print(f'epoch {epoch+1:3d}: loss {row["loss"]:.4f}, training action accuracy {row["accuracy"]:.1%}', flush=True)
    new = policy_fingerprint(model)
    if new == initial:
        raise RuntimeError('Training produced no weight change')
    metadata = dict(model=MODEL, stages=args.stages, examples_per_stage=args.examples,
                    labeled_actions=len(examples), seed=args.seed, epochs=args.epochs,
                    learning_rate=args.learning_rate, objective='masked behavior cloning of scripted native actions',
                    parent=str(args.start_from) if args.start_from else None,
                    fingerprint=new, native_sha256=file_sha(args.dll), source_hashes=sources())
    torch.save(dict(config=metadata, parameters=model.state_dict()), output/'latest.pt')
    write(output/'config.json', metadata)
    write(output/'progress.json', progress)
    return model.eval()


def load_model(path, dll, device):
    saved = torch.load(path, map_location=device, weights_only=True)
    config = saved['config']
    if config['model'] != MODEL or config['native_sha256'] != file_sha(dll):
        raise ValueError('Curriculum checkpoint format or native binary differs')
    model = ConstructionPolicy().to(device)
    model.load_state_dict(saved['parameters'])
    if policy_fingerprint(model) != config['fingerprint']:
        raise ValueError('Curriculum checkpoint weight hash differs')
    return model.eval()


def load_original(args):
    payload = read_checkpoint(args.checkpoint)
    reference = ConnectionPractice(host_dll=args.original_dll, stage=SINGLE_BUILD_STAGE)
    try:
        policy = checkpoint_policy(reference, lambda _: 0., payload['config'])
        old_identity = verified_original_identity(payload['config'], args.original_dll, args.source_archive)
        load_frozen(args.checkpoint, policy, old_identity)
        return policy
    finally:
        reference.close()


def play_group(workers, trials, policy, mode, device):
    def reset(trial):
        trial.env.reset(trial.stage, 'validation', trial.seed)
    workers.map(reset, trials)
    initially_connected = [t.env.connected() for t in trials]
    # The original actor has no explicit driveway rotation or finish action.
    supported = [mode != 'legacy' or t.stage != 'driveway' for t in trials]
    actions_played = [[] for _ in trials]
    rngs = [torch.Generator().manual_seed(100000+t.seed) for t in trials]
    active = [i for i, support in enumerate(supported) if support]
    while active:
        active = [i for i in active if trials[i].env.legal.any()]
        if not active:
            break
        envs = [trials[i].env for i in active]
        with torch.inference_mode():
            if mode == 'legacy':
                observations = [env.full_observation() for env in envs]
                merged = {k: np.stack([item[k] for item in observations]) for k in observations[0]}
                tensors, _ = policy.obs_to_tensor(merged)
                masks = np.stack([env.legal[:EDGE_END] for env in envs])
                probabilities = policy.get_distribution(tensors, action_masks=masks).distribution.probs
                selected = probabilities.argmax(dim=1).tolist()
            else:
                states = torch.as_tensor(np.stack([env.observation() for env in envs]), device=device)
                masks = torch.as_tensor(np.stack([env.aligned_mask() for env in envs]), device=device)
                logits = policy(states).masked_fill(~masks, -torch.inf).cpu()
                aligned = (logits.argmax(dim=1).tolist() if mode=='greedy' else
                           [int(torch.multinomial(row.softmax(0), 1, generator=rngs[i]).item())
                            for i,row in zip(active, logits)])
                selected = [int(env.from_aligned[a]) for env, a in zip(envs, aligned)]
        for i, action in zip(active, selected):
            actions_played[i].append(action)
        ended = workers.map(lambda pair: pair[0].step(pair[1]), zip(envs, selected))
        active = [i for i, done in zip(active, ended) if not done]
        workers.map(lambda i: trials[i].env.mask(), active)
    results = workers.map(lambda t: (t.env.connected(), *t.env.deliveries()), trials)
    return [dict(stage=t.stage, seed=t.seed, actions=actions_played[i], supported=supported[i],
                 initially_connected=initially_connected[i], connected=connected, trips=trips, seconds=time,
                 inventory=t.env.inventory, edit_limit=t.env.edit_limit)
            for i,(t,(connected,trips,time)) in enumerate(zip(trials,results))]


def evaluate(args, workers, output, policy=None, mode=None):
    mode = mode or args.mode
    before = policy_fingerprint(policy) if policy is not None else None
    results = []
    for group in generate_trials(workers, args.stages, args.layouts, 'validation'):
        if mode == 'scripted':
            rows = workers.map(lambda t: scripted(t, 'validation'), group)
        else:
            rows = play_group(workers, group, policy, mode, torch.device(args.device))
        results.extend(rows)
    if policy is not None and policy_fingerprint(policy) != before:
        raise RuntimeError('Frozen evaluation changed weights')
    stats = {}
    for stage in args.stages:
        subset = [r for r in results if r['stage']==stage]
        successes = sum(r['trips']>=3 for r in subset)
        stats[stage] = dict(games=len(subset), connected=sum(r['connected'] for r in subset),
                            three_deliveries=successes, mean_trips=sum(r['trips'] for r in subset)/len(subset),
                            capital_edits_max=max(len(r['actions']) for r in subset),
                            gate_passed=len(subset)==100 and successes>=90)
    write(output/f'{mode}-games.json', results)
    write(output/f'{mode}-summary.json', stats)
    print(json.dumps(stats, indent=2), flush=True)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['scripted', 'legacy', 'train', 'greedy', 'sampled'])
    parser.add_argument('--dll', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--checkpoint')
    parser.add_argument('--source-archive')
    parser.add_argument('--original-dll')
    parser.add_argument('--start-from')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--stages', nargs='+', choices=EXERCISES, default=list(EXERCISES))
    parser.add_argument('--layouts', type=int, default=100)
    parser.add_argument('--examples', type=int, default=512)
    parser.add_argument('--epochs', type=int, default=32)
    parser.add_argument('--learning-rate', type=float, default=.0015)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--workers', type=int, default=12)
    args = parser.parse_args()
    if min(args.workers,args.layouts,args.examples,args.epochs) < 1 or args.learning_rate <= 0:
        parser.error('Expected positive limits')
    if args.mode in ('legacy','greedy','sampled') and not args.checkpoint:
        parser.error('Frozen evaluation requires a checkpoint')
    if args.mode=='legacy' and (not args.source_archive or not args.original_dll or args.device!='cpu'):
        parser.error('Legacy evaluation requires the archived source, previous binary and CPU')
    output = Path(args.output)
    output.mkdir(parents=True)
    torch.set_num_threads(2)
    torch.manual_seed(args.seed)
    start = monotonic()
    workers = Workers(args.workers, args.dll)
    try:
        if args.mode == 'train':
            train(args, workers, output)
        else:
            model = (load_original(args) if args.mode=='legacy' else
                     load_model(args.checkpoint, args.dll, args.device) if args.mode!='scripted' else None)
            evaluate(args, workers, output, model)
    finally:
        workers.close()
    write(output/'run.json', dict(mode=args.mode, elapsed_seconds=monotonic()-start,
                                  arguments=vars(args), native_sha256=file_sha(args.dll), source_hashes=sources()))


if __name__ == '__main__':
    main()
