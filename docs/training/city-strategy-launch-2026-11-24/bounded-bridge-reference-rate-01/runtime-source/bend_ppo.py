"""Reward-only Maskable-PPO pilot for unfinished road bends."""
import argparse
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
from time import monotonic

import gymnasium as gym
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import SubprocVecEnv

from checkpoint_tools import load_frozen, read_checkpoint
from connection_practice import ARENA_SIZE, SINGLE_BUILD_STAGE, ConnectionPractice
from construction_practice import EDGE_END, ConstructionPractice, tile, verified_original_identity
from edge_policy import LocalEdgeFeatures, SharedEdgePolicy, TILE_CHANNELS, checkpoint_policy
from hierarchy_rollout import policy_fingerprint
from visible_observation import HEIGHT, WIDTH

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = (*TILE_CHANNELS, *range(9, 17), *range(30, 38))


class CompactEdgeFeatures(LocalEdgeFeatures):
    """Adapter to the existing edge scorer. Only its consumed planes are stored."""
    def forward(self, observations):
        compact = observations['grid']
        grid = compact.new_zeros((len(compact), 81, HEIGHT, WIDTH))
        grid[:, CHANNELS, :ARENA_SIZE, :ARENA_SIZE] = compact
        return super().forward({'grid': grid})


def compact_observation(env):
    cells = env.cells
    roads = np.asarray(env.raw['infrastructure'])[cells] == 1
    types = np.asarray(env.raw['buildingKinds'])[cells]
    links = np.asarray(env.raw['connections'])[cells]
    access = np.zeros((9, ARENA_SIZE, ARENA_SIZE), dtype=np.float32)
    for building in env.raw['buildings']:
        x,y = env.local(tile(building['cell'] if building['isHouse'] else building['entrance']))
        access[0,y,x] = access[1+building['drivewayDirection'],y,x] = 1.
    return {'grid': np.stack([np.ones_like(roads), roads, types==1, types==2, access[0],
                              *[(links & (1 << d)) != 0 for d in range(8)], *access[1:]],
                             dtype=np.float32)}


class BendEnvironment(gym.Env):
    """PPO sees only the board, legal builds and the binary terminal outcome."""
    metadata = {'render_modes': []}

    def __init__(self, dll, worker=0, workers=1):
        self.env = ConstructionPractice(dll)
        self.worker, self.workers = worker, workers
        self.episode = 0
        self.observation_space = gym.spaces.Dict({
            'grid': gym.spaces.Box(0, 1, (len(CHANNELS), ARENA_SIZE, ARENA_SIZE), np.float32)
        })
        self.action_space = gym.spaces.Discrete(EDGE_END)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if options is None:
            stage, split = 'bend', 'train'
            layout_seed = 64000+self.worker+self.workers*self.episode
            self.episode += 1
        else:
            stage, split, layout_seed = options['stage'], options['split'], options['layout_seed']
        self.env.reset(stage, split, layout_seed)
        return compact_observation(self.env), {}

    def action_masks(self):
        return self.env.legal[:EDGE_END].copy()

    def step(self, action):
        ended = self.env.step(int(action))
        connected = self.env.connected()
        if not ended:
            ended = not self.env.mask()[:EDGE_END].any()
        return compact_observation(self.env), float(ended and connected), ended, False, {
            'layout_seed': self.env.seed, 'connected': connected,
            'edits': self.env.edits, 'road_units_spent': self.env.inventory-self.env.raw['inventory'][0],
        }

    def close(self):
        self.env.close()


def original_policy(args):
    payload = read_checkpoint(args.checkpoint)
    reference = ConnectionPractice(host_dll=args.original_dll, stage=SINGLE_BUILD_STAGE)
    try:
        policy = checkpoint_policy(reference, lambda _: 0., payload['config'])
        archived_identity = verified_original_identity(payload['config'], args.original_dll, args.source_archive)
        load_frozen(args.checkpoint, policy, archived_identity)
        return policy
    finally:
        reference.close()


def warm_model(args, env, original):
    model = MaskablePPO(
        SharedEdgePolicy, env, learning_rate=1e-4, n_steps=128, batch_size=128,
        n_epochs=4, gamma=1., gae_lambda=1., ent_coef=.01, target_kl=.02,
        device=args.device, seed=42, verbose=0,
        policy_kwargs=dict(features_extractor_class=CompactEdgeFeatures, normalize_images=False,
                           optimizer_kwargs={'eps': 1e-5}),
    )
    model.policy.load_state_dict(original.state_dict(), strict=True)
    if policy_fingerprint(original) != policy_fingerprint(model.policy):
        raise RuntimeError('PPO warm-start weights differ from the reward-trained parent')
    return model


def verify_adapter(original, compact, dll):
    env = BendEnvironment(dll)
    try:
        for stage, seed in [('adjacent', 30000), ('bend', 32000), ('bend', 32001), ('bend', 32002)]:
            small, _ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
            big = env.env.full_observation()
            xmin,ymin = env.env.x0,env.env.y0
            expected = big['grid'][list(CHANNELS), ymin:ymin+ARENA_SIZE, xmin:xmin+ARENA_SIZE]
            np.testing.assert_array_equal(small['grid'], expected)
            mask = env.action_masks()
            with torch.inference_mode():
                a, _ = original.obs_to_tensor(big)
                b, _ = compact.obs_to_tensor(small)
                prior = original.get_distribution(a, action_masks=mask).distribution.logits
                adapter = compact.get_distribution(b, action_masks=mask).distribution.logits
                torch.testing.assert_close(prior, adapter.cpu(), atol=2e-5, rtol=2e-5)
            wrong = int(np.flatnonzero(mask)[0])
            _, reward, ended, truncated, info = env.step(wrong)
            assert not truncated and (reward == 0 or ended and info['connected'])
    finally:
        env.close()


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, payload):
    with path.open('x') as out:
        json.dump(payload, out, indent=2)
        out.write('\n')


class Monitor(BaseCallback):
    def __init__(self, output, seconds):
        super().__init__()
        self.output = output
        self.deadline = monotonic()+seconds
        self.completed_update_decisions = 0
        self.pending = None
        self.games = 0
        self.successes = 0
        self.started = monotonic()
        self.stopped_by_wall = False

    def _save(self):
        temporary = self.output/'checkpoint.tmp.zip'
        self.model.save(temporary)
        temporary.replace(self.output/'latest.zip')

    def _record_update(self):
        if self.pending is None:
            return
        self._save()
        self.completed_update_decisions = self.pending['decisions']
        row = dict(**self.pending, ppo_epochs=self.model._n_updates,
                   elapsed_seconds=monotonic()-self.started, fingerprint=policy_fingerprint(self.model.policy))
        with (self.output/'progress.jsonl').open('a') as out:
            out.write(json.dumps(row)+'\n')
        print(f'PPO | {row["successes"]}/{row["games"]} connected | '
              f'{row["decisions"]} build decisions | {row["ppo_epochs"]} PPO epochs', flush=True)
        self.pending = None

    def _on_rollout_start(self):
        self._record_update()
        self.games = self.successes = 0

    def _on_step(self):
        for done, info in zip(self.locals['dones'], self.locals['infos']):
            if done:
                self.games += 1
                self.successes += int(info['connected'])
                with (self.output/'episodes.jsonl').open('a') as out:
                    out.write(json.dumps(info | {'terminal_observation': None})+'\n')
        self.stopped_by_wall = monotonic() >= self.deadline
        return not self.stopped_by_wall

    def _on_rollout_end(self):
        self.pending = dict(decisions=self.num_timesteps, games=self.games, successes=self.successes)

    def _on_training_end(self):
        self._record_update()


def run_training(args, output):
    parent = original_policy(args)
    if args.dry:
        env = BendEnvironment(args.dll)
        try:
            model = warm_model(args, env, parent)
            verify_adapter(parent, model.policy, args.dll)
            print('Dry run passed: identical warm-start logits and correct terminal-only reward', flush=True)
        finally:
            env.close()
        return
    env = SubprocVecEnv(
        [partial(BendEnvironment, args.dll, worker=i, workers=args.workers) for i in range(args.workers)],
        start_method='forkserver',
    )
    try:
        model = warm_model(args, env, parent)
        verify_adapter(parent, model.policy, args.dll)
        write(output/'config.json', dict(
            parent=str(args.checkpoint), parent_fingerprint=policy_fingerprint(parent),
            native_sha256=digest(args.dll), source_sha256=digest(__file__),
            optimizer='fresh Adam', seed=42, workers=args.workers, rollout_steps_per_worker=128,
            learning_rate=1e-4, batch_size=128, epochs=4, gamma=1., gae_lambda=1., ent_coef=.01,
            target_kl=.02, decision_budget=args.decisions, wall_seconds=args.wall_seconds,
            reward='1 for native visible-road connectivity at termination, otherwise 0',
            teacher_actions=False, device=args.device))
        model.save(output/'initial.zip')
        callback = Monitor(output, args.wall_seconds)
        try:
            model.learn(total_timesteps=args.decisions, callback=callback, progress_bar=False)
        except KeyboardInterrupt:
            result = 'INTERRUPTED'
        else:
            result = 'WALL_BUDGET' if callback.stopped_by_wall else 'DECISION_BUDGET'
        status = dict(result=result, collected_decisions=model.num_timesteps,
                      saved_decisions=callback.completed_update_decisions, elapsed_seconds=monotonic()-callback.started)
        write(output/'status.json', status)
        print(json.dumps(status), flush=True)
    finally:
        env.close()


def evaluate(args, output):
    if args.original_dll:
        policy = original_policy(args)
        use_original = True
    else:
        config = json.loads(Path(args.checkpoint).with_name('config.json').read_text())
        if config['native_sha256'] != digest(args.dll) or config['source_sha256'] != digest(__file__):
            raise ValueError('Checkpoint and curriculum host or runner source differ')
        policy = MaskablePPO.load(args.checkpoint, device='cpu').policy
        use_original = False
    before = policy_fingerprint(policy)
    rows = []
    env = BendEnvironment(args.dll)
    try:
        for stage, base in [('adjacent', 30000), ('bend', 32000)]:
            for seed in range(base,base+100):
                obs,_ = env.reset(options=dict(stage=stage, split='validation', layout_seed=seed))
                rng = torch.Generator().manual_seed(100000+seed)
                actions = []
                done = False
                while not done:
                    mask = env.action_masks()
                    current = env.env.full_observation() if use_original else obs
                    with torch.inference_mode():
                        tensor,_ = policy.obs_to_tensor(current)
                        probs = policy.get_distribution(tensor, action_masks=mask).distribution.probs[0]
                        action = int(probs.argmax()) if not args.sample else int(torch.multinomial(probs,1,generator=rng))
                    actions.append(action)
                    obs,_,done,_,info = env.step(action)
                trips,seconds = env.env.deliveries()
                rows.append(dict(stage=stage,seed=seed,actions=actions,trips=trips,seconds=seconds,**{
                    k:v for k,v in info.items() if k in ('connected','road_units_spent')}))
    finally:
        env.close()
    if policy_fingerprint(policy) != before:
        raise RuntimeError('Frozen evaluation changed weights')
    summary = {stage:dict(three_deliveries=sum(r['trips']>=3 for r in rows if r['stage']==stage),
                          connected=sum(r['connected'] for r in rows if r['stage']==stage))
               for stage in ('adjacent','bend')}
    write(output/'results.json',dict(policy_fingerprint=before,sampled=args.sample,summary=summary,layouts=rows))
    print(json.dumps(summary),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('train','evaluate'))
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--original-dll')
    parser.add_argument('--source-archive')
    parser.add_argument('--dll', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--device', choices=('cpu','cuda'), default='cuda')
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--decisions', type=int, default=131072)
    parser.add_argument('--wall-seconds', type=int, default=1800)
    parser.add_argument('--dry', action='store_true')
    parser.add_argument('--sample', action='store_true')
    args = parser.parse_args()
    if min(args.workers,args.decisions,args.wall_seconds) < 1:
        parser.error('Require positive finite budgets')
    if args.mode=='train' and (not args.original_dll or not args.source_archive
                              or args.decisions % (128*args.workers)):
        parser.error('Training needs the parent host/source and a whole number of rollouts')
    if args.original_dll and not args.source_archive:
        parser.error('The original checkpoint requires its source archive')
    output = Path(args.output)
    output.mkdir(parents=True)
    torch.set_num_threads(2)
    if args.mode == 'train':
        run_training(args, output)
    else:
        evaluate(args, output)


if __name__ == '__main__':
    main()
