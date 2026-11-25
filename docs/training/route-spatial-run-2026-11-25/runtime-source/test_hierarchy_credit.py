"""Synthetic timing/credit cases. No episodes or optimizer updates."""
import math
import unittest
from dataclasses import replace

import numpy as np
from hierarchy_rollout import TokenTransition,FocusAssembler,generalized_advantages


def token(role,next_role,*,reward=0,start=0,end=0,terminated=False,truncated=False,version='v1'):
    return TokenTransition({},np.ones(1501,bool),0,-math.log(2),1.,role,next_role,reward,
        start,end,terminated,truncated,None,version,(None,None))


class CreditChecks(unittest.TestCase):
    def test_manager_joint_probability_and_score_is_not_duplicated(self):
        assembler=FocusAssembler()
        records=[token('primary','secondary'),token('secondary','executor'),
            token('executor','executor'),token('executor','primary',reward=3,end=20)]
        intervals=assembler.append(records)
        self.assertEqual(len(intervals),1)
        self.assertAlmostEqual(math.exp(intervals[0].behavior_log_probability),.25)
        self.assertEqual(intervals[0].reward,3)
        self.assertEqual(sum(t.reward for t in records),3)
        self.assertEqual(intervals[0].duration_ticks,20)
        self.assertFalse(intervals[0].terminated)

    def test_focus_selection_and_interval_survive_rollout_cuts(self):
        assembler=FocusAssembler()
        first=token('primary','secondary')
        assembler.append([first])
        self.assertIs(assembler.pending_primary,first)
        self.assertEqual(assembler.completed,[])
        assembler.append([token('secondary','executor'),token('executor','executor')])
        self.assertIsNotNone(assembler.active)
        assembler.append([token('executor','primary',reward=2,end=10)])
        self.assertEqual(assembler.completed[0].reward,2)
        self.assertEqual(assembler.completed[0].duration_ticks,10)

    def test_version_change_inside_focus_is_rejected(self):
        assembler=FocusAssembler();assembler.append([token('primary','secondary')])
        with self.assertRaisesRegex(RuntimeError,'partial focus'):
            assembler.append([token('secondary','executor',version='v2')])

    def test_interruption_during_manager_selection_is_preserved(self):
        assembler=FocusAssembler()
        t=token('primary','secondary',truncated=True)
        assembler.append([t])
        self.assertEqual(assembler.partial_selections,[t])
        self.assertEqual(assembler.completed,[])
        with self.assertRaises(RuntimeError):assembler.append([token('primary','secondary')])

    def test_gamma_one_lambda_one_carries_delayed_reward_through_paused_tokens(self):
        adv,returns=generalized_advantages(rewards=[0,0,3],values=[1,2,1],next_values=[2,1,9],
            terminated=[False,False,True],trace_ends=[False,False,True],durations=[1,1,1],
            trace_lambda=1.,trace_units='policy_tokens')
        np.testing.assert_array_equal(returns,[3,3,3])
        np.testing.assert_array_equal(adv,[2,1,2])

    def test_operational_and_rollout_cuts_bootstrap_but_task_end_does_not(self):
        common=dict(rewards=[0],values=[1],next_values=[7],trace_ends=[True],durations=[0],
                    trace_lambda=.95,trace_units='simulation_seconds')
        _,operational=generalized_advantages(terminated=[False],**common)
        _,terminal=generalized_advantages(terminated=[True],**common)
        self.assertEqual(operational[0],7)
        self.assertEqual(terminal[0],0)

    def test_zero_duration_focus_does_not_impose_time_decay(self):
        _,returns=generalized_advantages(rewards=[0,4],values=[0,0],next_values=[0,0],
            terminated=[False,True],trace_ends=[False,True],durations=[0,20],
            trace_lambda=.5,trace_units='simulation_ticks')
        np.testing.assert_array_equal(returns,[4,4])
        _,token_returns=generalized_advantages(rewards=[0,4],values=[0,0],next_values=[0,0],
            terminated=[False,True],trace_ends=[False,True],durations=[1,1],
            trace_lambda=.5,trace_units='policy_tokens')
        np.testing.assert_array_equal(token_returns,[2,4])

    def test_trace_units_and_lambda_cannot_be_implicit(self):
        common=dict(rewards=[0],values=[0],next_values=[0],terminated=[False],trace_ends=[True],durations=[1])
        with self.assertRaises(TypeError):generalized_advantages(**common)
        with self.assertRaises(ValueError):generalized_advantages(**common,trace_lambda=.95,trace_units='unspecified')


if __name__=='__main__':unittest.main()
