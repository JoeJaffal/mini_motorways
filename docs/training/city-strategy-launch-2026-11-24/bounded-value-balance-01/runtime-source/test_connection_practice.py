"""Scripted correctness/feasibility fixtures only. Never constructs a learner."""
import argparse
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from connection_practice import ConnectionPractice, WAIT, DRAW, ERASE, REMOVE, HANDOFF, NONE, CANCEL

DOTNET = 'dotnet'
DLL = None
RESULTS = []


def enter_executor(env, primary=0):
    if env.role == 'primary':
        env.step(primary)
    if env.role == 'secondary':
        env.step(NONE)


def advance_score_fixture(env, ticks):
    """Place a test near the horizon while accounting for the setup deliveries."""
    assert env.reward_mode == 'score'
    outcome = env._call(command='step', ticks=ticks)
    env.training_reward_total += outcome['tripsDelta']


def edit(env, a, b):
    enter_executor(env)
    env.step(DRAW)
    env.step(a[1]*50+a[0])
    result = env.step(__import__('environment').DIRS.index((b[0]-a[0], b[1]-a[1])))
    assert result[4]['accepted'], (a, b, env.raw['time'])
    assert result[1] == 0 and env.raw['time'] == 0
    return result


def scripted_connection(env):
    # A test-only witness, never imported by policy/environment or exposed in observations.
    shop = next(b for b in env.raw['buildings'] if not b['isHouse'])
    home = next(b for b in env.raw['buildings'] if b['isHouse'])
    from environment import DIRS
    a = (home['cell']['x'], home['cell']['y'])
    entrance = shop['entrance']['x'], shop['entrance']['y']
    dx, dy = DIRS[shop['drivewayDirection']]
    target = entrance[0]+dx, entrance[1]+dy
    while a != target:
        b = (a[0]+int(np.sign(target[0]-a[0])), a[1]+int(np.sign(target[1]-a[1])))
        edit(env, a, b)
        a = b
    # Native driveway attaches when the tile outside the destination is built.


class PracticeChecks(unittest.TestCase):
    def setUp(self):
        self.env = ConnectionPractice(dotnet=DOTNET, host_dll=DLL)

    def tearDown(self):
        self.env.close()

    def test_paused_hierarchy_and_focus_not_pruning(self):
        env = self.env
        obs, _ = env.reset(seed=11)
        self.assertTrue(env.observation_space.contains(obs))
        enter_executor(env, 1)
        env.step(DRAW)
        before = env.action_masks()
        env.focus = [(49,29), (48,29)]
        np.testing.assert_array_equal(before, env.action_masks())
        a = int(np.flatnonzero(before[:1500])[0])
        env.step(a)
        direction = int(np.flatnonzero(env.action_masks()[:8])[0])
        _, reward, _, _, info = env.step(direction)
        self.assertEqual(reward, 0)
        self.assertEqual(info['seconds'], 0)
        self.assertEqual(env.edit_count, 1)
        env.step(HANDOFF)
        self.assertEqual(env.role, 'primary')
        enter_executor(env)
        env.step(WAIT)
        self.assertAlmostEqual(env.raw['time'], 1)
        self.assertEqual(env.role, 'primary')

    def test_eight_completed_edits_trigger_review(self):
        env = self.env
        env.reset(seed=23)
        enter_executor(env)
        for i in range(8):
            edit(env, (0,0), (1,0))
            self.assertEqual(env.role, 'primary' if i == 7 else 'executor')
        self.assertEqual(env.raw['time'], 0)

    def test_operational_cap_is_not_a_gate_pass(self):
        self.env.max_paused_tokens = 1
        self.env.reset(seed=0)
        _, _, terminated, truncated, info = self.env.step(0)
        self.assertFalse(terminated)
        self.assertTrue(truncated and info['operational_truncation'])
        self.assertFalse(info['pass_candidate'])

    def test_pause_guard_resets_only_on_positive_game_time(self):
        env = self.env
        env.max_paused_tokens = 6
        env.reset(seed=42)
        for _ in range(4):
            enter_executor(env)
            self.assertEqual(env.paused_tokens, 2)
            _, _, terminated, truncated, _ = env.step(WAIT)
            self.assertFalse(terminated or truncated)
            self.assertEqual(env.paused_tokens, 0)
        self.assertGreater(env.decisions, env.max_paused_tokens)
        self.assertEqual(env.encode()['context'][7], 0)
        for _ in range(2):
            enter_executor(env)
            _, _, _, truncated, info = env.step(HANDOFF)
        self.assertTrue(truncated)
        self.assertEqual(info['ending_reason'], 'paused_policy_stall')
        self.assertEqual(env.encode()['context'][7], 1)

    def test_wait_stops_at_fractional_task_horizon(self):
        env = self.env
        env.reset(seed=42)
        scripted_connection(env)
        advance_score_fixture(env, 3595)
        self.assertAlmostEqual(env.raw['time'], 179.75)
        enter_executor(env)
        _, _, terminated, truncated, info = env.step(WAIT)
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertAlmostEqual(info['seconds'], 180)
        self.assertEqual(info['ending_reason'], 'task_horizon')

    def test_native_ending_uses_the_approved_score_floor(self):
        self.env.reset(seed=4)
        self.env.raw['failed']=True
        self.env.raw['tripsCompleted']=3
        self.assertTrue(self.env.info()['pass_candidate'])
        self.env.raw['tripsCompleted']=2
        self.assertFalse(self.env.info()['pass_candidate'])
        self.env.raw['failed']=False
        self.env.raw['tripsCompleted']=10
        self.assertFalse(self.env.info()['pass_candidate'])

    def test_cancel_stays_with_executor_and_direction_masks_are_cached(self):
        env=self.env
        env.reset(seed=5)
        enter_executor(env)
        env.step(DRAW)
        env.step(0)
        before=env.timings['host_calls']
        env.action_masks();env.action_masks()
        after=env.timings['host_calls']
        self.assertLessEqual(after-before,1)
        env.action_masks()
        self.assertEqual(env.timings['host_calls'],after)
        env.step(CANCEL)
        self.assertEqual(env.role,'executor')
        self.assertEqual(env.phase,0)
        self.assertEqual(env.raw['time'],0)
        self.assertEqual(env.edit_count,0)

    def test_native_rejection_is_fatal_not_a_scored_loss_or_forced_wait(self):
        env=self.env
        env.reset(seed=8)
        enter_executor(env)
        env.step(DRAW)
        env.step(49)
        # Fault injection: pretend an off-canvas direction is legal.
        env._direction_cache[(DRAW,(49,0))]=np.ones(8,bool)
        with self.assertRaisesRegex(RuntimeError,'masked-valid'):
            env.step(0)
        self.assertTrue(env.done)
        self.assertEqual(env.raw['time'],0)
        self.assertEqual(env.raw['tripsCompleted'],0)
        with self.assertRaises(RuntimeError):env.step(0)
        env.reset(seed=8)
        self.assertFalse(env.done)

    def test_reset_rejects_rule_or_distribution_drift(self):
        from unittest.mock import patch
        env=self.env
        original=env._call
        for field,value in [('unlimitedConstruction',True),('tripsCompleted',1),('version','Custom')]:
            def changed(**request):
                result=original(**request)
                if request['command']=='reset':env.raw[field]=value
                return result
            with self.subTest(field=field),patch.object(env,'_call',side_effect=changed):
                with self.assertRaisesRegex(RuntimeError,'Unexpected Stage 1 reset'):
                    env.reset(seed=12)
                self.assertTrue(env.done)

    def test_reset_determinism_and_no_hidden_channels(self):
        env = self.env
        a, _ = env.reset(seed=77)
        raw = env.raw
        env.raw = dict(raw, scheduledSpawns=[{'time': 0}], randomDraws=999999)
        b = env.encode()
        for k in a:
            np.testing.assert_array_equal(a[k], b[k])
        c, _ = env.reset(seed=77)
        for k in a:
            np.testing.assert_array_equal(a[k], c[k])
        env.reset()
        next_seed = env.scenario_seed
        env.reset()
        self.assertNotEqual(next_seed, env.scenario_seed)
        env.reset(seed=77)
        env.reset()
        self.assertEqual(next_seed, env.scenario_seed)

    def test_time_limit_and_reward_are_native_trip_delta(self):
        env = self.env
        env.reset(seed=42)
        scripted_connection(env)
        advance_score_fixture(env, 3580)
        before = env.raw['tripsCompleted']
        enter_executor(env)
        _, reward, terminated, truncated, info = env.step(WAIT)
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertEqual(info['seconds'], 180)
        self.assertEqual(reward, info['trips']-before)
        self.assertTrue(info['pass_candidate'])
        with self.assertRaises(RuntimeError):
            env.step(WAIT)

    def test_policy_batch_forward_without_weight_updates(self):
        import torch
        from hierarchy_policy import HierarchyPolicy
        torch.set_num_threads(1)
        env = self.env
        obs, _ = env.reset(seed=9)
        policy = HierarchyPolicy(env.observation_space, env.action_space, lambda _: 0.0)
        policy.set_training_mode(False)
        before = {k: v.clone() for k,v in policy.state_dict().items()}
        batch = {k: np.repeat(v[None], 3, axis=0) for k,v in obs.items()}
        masks = np.repeat(env.action_masks()[None], 3, axis=0)
        actions, _ = policy.predict(batch, deterministic=True, action_masks=masks)
        self.assertEqual(actions.shape, (3,))
        self.assertTrue(all(masks[i,a] for i,a in enumerate(actions)))
        self.assertFalse(policy.optimizer.state)
        for k,v in policy.state_dict().items():
            self.assertTrue(torch.equal(before[k], v))

    def test_native_timing_feasibility_100_layouts(self):
        env = self.env
        env.split = 'validation'
        identities = set()
        for seed in range(20000, 20100):
            env.reset(seed=seed)
            identity = tuple((b['cell']['x'], b['cell']['y'], b['layout'],
                              b['color'], b['drivewayDirection']) for b in env.raw['buildings'])
            self.assertNotIn(identity, identities)
            identities.add(identity)
            scripted_connection(env)
            # Bulk ticking tests native trip timing without 18,000 redundant
            # observation serializations. This is not a model gate evaluation.
            result = env._call(command='step', ticks=3600)
            info = env.info()
            self.assertEqual(info['seconds'], 180)
            self.assertFalse(result['terminated'] or result['truncated'])
            self.assertGreaterEqual(info['trips'], 3)
            self.assertEqual(len(env.raw['buildings']), 2)
            self.assertEqual(env.raw['upgradeChoices'], [])
            RESULTS.append(dict(seed=seed, trips=info['trips'], seconds=info['seconds']))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dotnet', default='dotnet')
    p.add_argument('--dll')
    p.add_argument('--results')
    args, rest = p.parse_known_args()
    DOTNET, DLL = args.dotnet, args.dll
    result = unittest.main(argv=[sys.argv[0]]+rest, exit=False)
    if args.results:
        Path(args.results).write_text(json.dumps(dict(kind='scripted-feasibility-not-model-evaluation',
            passed=result.result.wasSuccessful(), layouts=RESULTS), indent=2)+'\n')
    sys.exit(not result.result.wasSuccessful())
