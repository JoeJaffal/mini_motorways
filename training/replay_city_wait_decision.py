"""Replay lowest-seed native Wait-review case per family with exact counters."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_wait_decision import CityWaitDecisionEnv
from export_city_replays import frame, action_endpoints
from prepare_city_policy import masked_probs, sha256


def main():
    parser = argparse.ArgumentParser()
    for name in ('dll', 'checkpoint', 'evaluation', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    a = parser.parse_args()
    torch.set_num_threads(1)
    a.output.mkdir(parents=True, exist_ok=False)
    rows = [json.loads(line) for line in (a.evaluation/'games.jsonl').read_text().splitlines()]
    assert all(row['mode'] == 'native' for row in rows)
    selected = [min((r for r in rows if r['case'] == case), key=lambda r: r['seed'])
                for case in sorted({r['case'] for r in rows})]
    config = json.loads((a.evaluation/'config.json').read_text())
    assert sha256(a.checkpoint) == config['checkpoint_sha256']
    assert sha256(a.dll) == config['host_sha256']
    (a.output/'selection.json').write_text(json.dumps(dict(
        criterion='Lowest seed in each family, independent of outcome. Illustrations, not averages.',
        checkpoint_sha256=sha256(a.checkpoint), host_sha256=sha256(a.dll), selected=selected), indent=2)+'\n')
    model = MaskablePPO.load(a.checkpoint, device='cpu')
    env = CityWaitDecisionEnv(str(a.dll), validation=True, bandit=False)
    template = (Path(__file__).parent/'stage1_replay.html').read_text()
    try:
        for expected in selected:
            obs, info = env.reset(options=dict(case=expected['case'], scenario_seed=expected['seed']))
            rng = np.random.default_rng(expected['action_seed'])
            frames = [frame(env.raw, 'Start')]
            steps = []
            total = 0
            while not env.done:
                mask = env.action_masks()
                p = mask.astype(float) if mask.sum() == 1 else masked_probs(model, obs, mask).astype(float)
                action = int(rng.choice(len(p), p=p/p.sum()))
                obs, reward, terminal, truncated, info = env.step(action)
                total += reward
                steps.append(dict(action=action, time=info['seconds'], native_reward=reward))
                frames.append(frame(env.raw, 'Build' if action else 'Wait', action_endpoints(action) if action else None))
            assert total == info['native_trips_since_reset'] == expected['native_deliveries']
            assert info['road_actions'] == expected['builds']
            assert info['road_stock'] == expected['remaining_stock']
            assert info['seconds'] == expected['final_time']
            assert len(steps) == expected['decisions'] and steps[0]['action'] == expected['first_action']
            assert terminal == expected['native_game_over']
            data = dict(title=f"{expected['case']}: {total} native deliveries, {info['road_actions']} builds",
                        intro='Frozen policy; native60-second review from a varied waiting prefix.',
                        speed='8', ending='Native game-over' if terminal else 'Evaluation horizon',
                        frames=frames, terrain=[[i, t] for i, t in enumerate(env.raw['terrain']) if t])
            dest = a.output/expected['case']
            dest.mkdir()
            (dest/'trace.json').write_text(json.dumps(data))
            (dest/'steps.jsonl').write_text(''.join(json.dumps(step)+'\n' for step in steps))
            (dest/'replay.html').write_text(template.replace('/*REPLAY_DATA*/', json.dumps(data).replace('<', '\\u003c')))
            (dest/'verification.json').write_text(json.dumps(dict(exact=True, expected=expected), indent=2)+'\n')
            print('EXACT WAIT REPLAY', expected['case'], expected['seed'], flush=True)
        assert sha256(a.checkpoint) == config['checkpoint_sha256']
        assert sha256(a.dll) == config['host_sha256']
    finally:
        env.close()


if __name__ == '__main__':
    main()
