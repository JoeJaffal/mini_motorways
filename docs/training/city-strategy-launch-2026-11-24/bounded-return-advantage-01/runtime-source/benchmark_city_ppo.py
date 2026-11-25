"""Time a bounded city PPO worker trial starting from frozen weights."""

import argparse
import csv
from datetime import datetime
from functools import partial
import json
from pathlib import Path
import subprocess
from threading import Event, Thread
from time import perf_counter

from sb3_contrib import MaskablePPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

from prepare_city_policy import sha256
from train_city_score_pilot import RecordEpisodes, make_env


class TimedPPO(MaskablePPO):
    def collect_rollouts(self, *args, **kwargs):
        start = perf_counter()
        result = super().collect_rollouts(*args, **kwargs)
        torch.cuda.synchronize()
        self.collection_seconds.append(perf_counter() - start)
        return result

    def train(self):
        start = perf_counter()
        super().train()
        torch.cuda.synchronize()
        self.update_seconds.append(perf_counter() - start)
        print(f'ROLLOUT | {self.n_envs} workers | {self.num_timesteps} decisions | '
              f'collect {self.collection_seconds[-1]:.2f}s | update {self.update_seconds[-1]:.2f}s',
              flush=True)


def sample_hardware(destination, stop):
    labels = Path('/sys/class/hwmon').glob('hwmon*/temp*_label')
    label = next((path for path in labels if path.read_text().strip() == 'Tctl'), None)
    cpu = label.with_name(label.name.replace('_label', '_input')) if label else None
    with destination.open('x') as file:
        output = csv.writer(file)
        output.writerow(('local_time', 'cpu_tctl_c', 'available_ram_mib', 'gpu_c', 'gpu_util_pct',
                         'gpu_used_mib', 'gpu_power_w'))
        while not stop.is_set():
            ram = next(int(line.split()[1]) / 1024
                       for line in Path('/proc/meminfo').read_text().splitlines()
                       if line.startswith('MemAvailable:'))
            gpu = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=temperature.gpu,utilization.gpu,memory.used,power.draw',
                 '--format=csv,noheader,nounits'], text=True, timeout=5,
            ).strip().splitlines()[0].split(',')
            output.writerow((datetime.now().astimezone().isoformat(timespec='seconds'),
                             float(cpu.read_text()) / 1000 if cpu else '', round(ram, 1),
                             *(field.strip() for field in gpu)))
            file.flush()
            stop.wait(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--pilot-config', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=(16, 24, 32), required=True)
    parser.add_argument('--decisions', type=int, default=12288)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.pilot_config.read_text())
    n_steps = config['rollout_steps']
    if args.decisions <= 0 or args.decisions % (args.workers * n_steps):
        parser.error('The decision budget must cover a whole number of worker rollouts')
    parent_hash, host_hash = sha256(args.checkpoint), sha256(args.dll)
    if config['parent_sha256'] != parent_hash or config['host_sha256'] != host_hash:
        parser.error('Benchmark host and starting checkpoint must match the pilot')
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    startup = perf_counter()
    env = SubprocVecEnv([partial(make_env, args.dll, i, args.workers) for i in range(args.workers)],
                        start_method='forkserver')
    try:
        model = TimedPPO.load(
            args.checkpoint, env=env, device='cuda',
            seed=config['seed'], n_steps=n_steps, batch_size=config['batch_size'],
            n_epochs=config['epochs'], learning_rate=config['learning_rate'], gamma=config['gamma'],
            gae_lambda=config['gae_lambda'], ent_coef=config['entropy_coefficient'],
            target_kl=config['target_kl'],
        )
        if model.num_timesteps or model.policy.optimizer.state:
            raise RuntimeError('The benchmark must start with a fresh optimizer and zero city decisions')
        model.collection_seconds = []
        model.update_seconds = []
        model.set_logger(configure(str(args.output), ['csv']))
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        startup_seconds = perf_counter() - startup
        stop = Event()
        hardware_path = args.output / 'hardware.csv'
        sampler = Thread(target=sample_hardware, args=(hardware_path, stop))
        sampler.start()
        try:
            with (args.output / 'episodes.jsonl').open('x') as output:
                callback = RecordEpisodes(output)
                start = perf_counter()
                model.learn(total_timesteps=args.decisions, reset_num_timesteps=False, callback=callback)
                model.logger.dump(step=model.num_timesteps)
                elapsed = perf_counter() - start
        finally:
            stop.set()
            sampler.join()
        if model.num_timesteps != args.decisions or sha256(args.checkpoint) != parent_hash:
            raise RuntimeError('Unexpected start checkpoint change or benchmark decision count')
        with hardware_path.open() as file:
            samples = list(csv.DictReader(file))
        if not samples:
            raise RuntimeError('No hardware samples were collected')
        summary = dict(
            workers=args.workers, decisions=model.num_timesteps, host_sha256=host_hash,
            parent_sha256=parent_hash, pilot_config_sha256=sha256(args.pilot_config),
            startup_seconds=startup_seconds, elapsed_seconds=elapsed,
            decisions_per_second=model.num_timesteps / elapsed,
            collection_seconds=model.collection_seconds, update_seconds=model.update_seconds,
            ppo_epochs=model._n_updates, completed_games=callback.completed,
            peak_cuda_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
            peak_cuda_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
            hardware_samples=len(samples),
            min_available_ram_mib=min(float(sample['available_ram_mib']) for sample in samples),
            sampled_peak_gpu_mib=max(float(sample['gpu_used_mib']) for sample in samples),
            sampled_peak_gpu_c=max(float(sample['gpu_c']) for sample in samples),
            sampled_mean_gpu_util_pct=sum(float(sample['gpu_util_pct']) for sample in samples) / len(samples),
            sampled_peak_cpu_tctl_c=max((float(s['cpu_tctl_c']) for s in samples if s['cpu_tctl_c']),
                                       default=None),
        )
        (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(f'COMPLETE | {args.workers} workers | {summary["decisions_per_second"]:.1f} decisions/s',
              flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()
