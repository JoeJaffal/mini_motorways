"""Human-readable progress, per-seed metrics and exact best-game recordings."""
from collections import defaultdict, deque
import json
from pathlib import Path
import time

from stable_baselines3.common.callbacks import BaseCallback


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for attempt in range(10):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(.02)  # A Windows viewer may briefly have the old file open.


def clock(seconds):
    seconds = max(0, round(seconds))
    return f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}'


class BudgetCallback(BaseCallback):
    def __init__(self, output, minutes, step_budget, episodes_per_seed=100,
                 print_seconds=5, metadata=None):
        super().__init__()
        self.output, self.seconds, self.step_budget = Path(output), minutes*60, step_budget
        self.episodes_per_seed, self.print_seconds = episodes_per_seed, print_seconds
        self.metadata = metadata or {}
        self.started = self.last_print = self.last_save = None
        self.commands = self.episodes = self.best = self.rejects = 0
        self.episode_results, self.per_seed = [], defaultdict(list)
        self.recent = defaultdict(lambda: deque(maxlen=20))
        self.best_rank, self.seed_best_rank = (-1, -1, 0), {}
        self.current_seed = None
        self.worker_seeds, self.worker_status = {}, {}

    def _on_training_start(self):
        self.started = self.last_print = self.last_save = time.perf_counter()
        print(f'TRAINING | learner budget {clock(self.seconds)} or {self.step_budget:,} selections | '
              f'progress every {self.print_seconds:g}s | Ctrl+C saves and stops', flush=True)

    def _save_game(self, info, result):
        recording = info.get('episode_replay')
        if recording is None:
            return
        rank = (result['trips'], result['seconds'], -result['rejected_actions'])
        seed = result['scenario_seed']
        recording = dict(recording, source='training', simulatorCommit=self.metadata.get('simulator_commit', ''),
                         policySchema=self.metadata.get('schema', ''), policySteps=self.num_timesteps,
                         worker=info.get('worker',0),
                         episode=self.episodes+int(bool(recording.get('partial'))),
                         ranking='highest trips, then longest survival, then fewest rejected actions')
        if rank > self.seed_best_rank.get(seed, (-1, -1, 0)):
            self.seed_best_rank[seed] = rank
            atomic_json(self.output/'seeds'/f'seed-{seed}'/'best-game.json', recording)
        if rank > self.best_rank:
            self.best_rank = rank
            atomic_json(self.output/'best-game.json', recording)
            # This policy is the one present at episode end; an episode can span
            # PPO updates. The action recording, not this checkpoint, is exact.
            self.model.save(self.output/'best-policy')
            print(f'NEW BEST | seed {seed} | score {result["trips"]} | survived {result["seconds"]:.1f}s | '
                  f'replay: {self.output / "best-game.json"}', flush=True)

    def _status(self, info, now, finished=False):
        elapsed = max(now-self.started, .001)
        rate = self.num_timesteps/elapsed
        time_left = max(0, self.seconds-elapsed)
        step_eta = max(0, self.step_budget-self.num_timesteps)/max(rate, .001)
        seed = info.get('scenario_seed', self.current_seed)
        stats = self.per_seed[seed]
        status = dict(wall_seconds=round(elapsed, 1), policy_steps=self.num_timesteps,
                      completed_commands=self.commands, episodes=self.episodes, best_training_score=self.best,
                      policy_steps_per_second=round(rate, 1), commands_per_second=round(self.commands/elapsed, 1),
                      estimated_seconds_remaining=round(min(time_left, step_eta), 1),
                      current_seed=seed, seed_attempt=info.get('seed_attempt'), seed_cycle=info.get('seed_cycle'),
                      seed_games=len(stats), seed_mean_score=sum(stats)/max(1,len(stats)),
                      seed_best_score=max(stats, default=0), current_score=info.get('trips',0),
                      current_game_seconds=info.get('seconds',0), mean_car_wait=info.get('mean_car_wait',0),
                      max_car_wait=info.get('max_car_wait',0), finished=finished)
        status['workers']=list(self.worker_status.values())
        atomic_json(self.output/'status.json', status)
        return status

    def _on_step(self):
        now = time.perf_counter()
        current = {}
        for worker,(info, done) in enumerate(zip(self.locals['infos'], self.locals['dones'])):
            info=dict(info,worker=worker)
            current = info
            seed = info['scenario_seed']
            self.worker_status[worker]=dict(worker=worker,seed=seed,attempt=info['seed_attempt'],
                                           score=info['trips'],game_seconds=info['seconds'])
            if self.worker_seeds.get(worker) != seed:
                print(f'WORKER {worker} | SEED {seed} | block attempt {info["seed_attempt"]}/{self.episodes_per_seed} | '
                      f'cycle {info["seed_cycle"]} | model weights continue', flush=True)
                self.worker_seeds[worker]=seed
            self.current_seed = seed
            self.commands += int(info.get('command_completed', False))
            if done:
                self.episodes += 1
                self.best = max(self.best, info['trips'])
                self.rejects += info['rejected_actions']
                keys = ['trips','seconds','rejected_actions','commands','scenario_seed',
                        'seed_attempt','seed_cycle','mean_car_wait','max_car_wait','action_counts']
                result = {k: info[k] for k in keys}
                result['worker']=worker
                result['terminated'] = not info.get('TimeLimit.truncated', False)
                result['truncated'] = bool(info.get('TimeLimit.truncated', False))
                result['policy_steps'] = self.num_timesteps
                result['wall_seconds'] = now-self.started
                self.episode_results.append(result)
                self.per_seed[seed].append(info['trips'])
                self.recent[seed].append(info['trips'])
                with (self.output/'episodes.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps(result)+'\n')
                self._save_game(info,result)
                stats, recent = self.per_seed[seed], self.recent[seed]
                waits = info['action_counts'].get('wait',0)
                print(f'GAME {self.episodes} | worker {worker} | seed {seed} try {info["seed_attempt"]}/{self.episodes_per_seed} | '
                      f'score {info["trips"]} | seed mean {sum(stats)/len(stats):.2f} '
                      f'recent20 {sum(recent)/len(recent):.2f} best {max(stats)} | '
                      f'survival {info["seconds"]:.1f}s | car wait mean/max '
                      f'{info["mean_car_wait"]:.2f}/{info["max_car_wait"]:.2f}s | '
                      f'wait actions {waits}/{info["commands"]} | rejected {info["rejected_actions"]}', flush=True)
        if now-self.last_print >= self.print_seconds:
            status = self._status(current,now)
            print(f'PROGRESS | elapsed {clock(status["wall_seconds"])} | ETA ~{clock(status["estimated_seconds_remaining"])} | '
                  f'{self.num_timesteps:,}/{self.step_budget:,} selections | '
                  f'{status["commands_per_second"]:.1f} commands/s | '
                  f'seed {status["current_seed"]} try {status["seed_attempt"]}/{self.episodes_per_seed} | '
                  f'current score {status["current_score"]} at {status["current_game_seconds"]:.1f}s | '
                  f'best {self.best} | {len(self.worker_status)} workers', flush=True)
            self.last_print = now
        if now-self.last_save >= 120:
            self.model.save(self.output/'latest')
            print('CHECKPOINT | latest.zip saved',flush=True)
            self.last_save = now
        return now-self.started < self.seconds

    def _on_training_end(self):
        # Avoid reporting a stale countdown after a time/step limit or Ctrl+C.
        vector = self.model.get_env()
        if vector is not None and getattr(vector,'envs',None):
            for worker,wrapped in enumerate(vector.envs):
                env = wrapped.unwrapped
                recording = env.export_replay()
                if recording is not None and recording.get('partial'):
                    partial = dict(env.info(),worker=worker)
                    partial['episode_replay'] = recording
                    self.best = max(self.best,partial['trips'])
                    self._save_game(partial,partial)
            # A Ctrl+C can arrive while a vector step finishes and autoresets.
            # Retain terminal recordings from those in-flight games as well.
            for worker,info in enumerate(getattr(vector,'buf_infos',[])):
                if info.get('episode_replay'):
                    self.best=max(self.best,info['trips'])
                    self._save_game(dict(info,worker=worker),info)
        info = (self.locals.get('infos') or [{}])[0]
        self._status(info,time.perf_counter(),finished=True)
        per_seed = {str(seed): dict(games=len(scores),mean_score=sum(scores)/len(scores),
                                   best_score=max(scores),recent20_mean=sum(scores[-20:])/len(scores[-20:]))
                    for seed,scores in self.per_seed.items() if scores}
        atomic_json(self.output/'seed-summary.json',per_seed)
