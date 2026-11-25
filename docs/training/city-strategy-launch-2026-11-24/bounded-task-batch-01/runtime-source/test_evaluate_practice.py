"""Gate/cohort/report rules with lightweight test doubles; no learning."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from evaluate_practice import evaluate_gate,select_review


class FixturePolicy:
    def state_dict(self):return {'fixture':torch.tensor(1.)}
    def set_training_mode(self,_):pass
    def predict(self,*args,**kwargs):return 0,None


class FixtureEnv:
    success_count=90;stall=False;error_seed=None
    schema='fixture';protocol_version='fixture';simulator_version='fixture'
    def __init__(self,**kwargs):pass
    def action_masks(self):return np.ones(1501,bool)
    def close(self):pass


class FixtureRecorder:
    def __init__(self,env,*,seed):self.seed=seed;self.initial_observation={}
    def step(self,_):
        if self.seed==FixtureEnv.error_seed:raise RuntimeError('fixture simulator error')
        passed=self.seed<20000+FixtureEnv.success_count
        stall=FixtureEnv.stall and self.seed==20000
        info=dict(trips=3 if passed else 0,seconds=0 if stall else 180,
            pass_candidate=passed and not stall,operational_truncation=stall,
            ending_reason='paused_policy_stall' if stall else 'task_horizon')
        return {},0,not stall,stall,info
    def save(self,path):Path(path).write_text(json.dumps(dict(kind='fixture-only',seed=self.seed)))


class GateChecks(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'cohort'
        FixtureEnv.success_count=90;FixtureEnv.stall=False;FixtureEnv.error_seed=None
        self.p1=patch('evaluate_practice.ConnectionPractice',FixtureEnv)
        self.p2=patch('evaluate_practice.PracticeRecorder',FixtureRecorder)
        self.p1.start();self.p2.start()
    def tearDown(self):self.p2.stop();self.p1.stop();self.directory.cleanup()
    def evaluate(self):return evaluate_gate(FixturePolicy(),replay_directory=self.path,wall_seconds=60)

    def test_ninety_individual_layout_passes_not_average_score(self):
        report=self.evaluate()
        self.assertTrue(report['valid'] and report['passed'])
        self.assertEqual(report['layouts_passed'],90)
        self.assertEqual(len(list(self.path.glob('seed-*.json'))),100)
        self.assertFalse(report['review']['provisional'])
        self.assertEqual(report['review']['examples']['worst']['seed'],20090)

    def test_eighty_nine_passes_fail(self):
        FixtureEnv.success_count=89
        report=self.evaluate();self.assertFalse(report['passed']);self.assertTrue(report['valid'])

    def test_stall_invalidates_otherwise_successful_cohort(self):
        FixtureEnv.success_count=100;FixtureEnv.stall=True
        report=self.evaluate()
        self.assertFalse(report['valid'] or report['passed'])
        self.assertEqual(report['layouts_passed'],99)
        self.assertTrue(report['review']['provisional'])

    def test_simulator_error_keeps_partial_evidence_and_propagates(self):
        FixtureEnv.error_seed=20003
        with self.assertRaisesRegex(RuntimeError,'fixture simulator error'):self.evaluate()
        report=json.loads((self.path/'summary.json').read_text())
        self.assertFalse(report['complete_cohort'] or report['passed'])
        self.assertEqual(len(report['layouts']),3)
        self.assertTrue((self.path/'interrupted-trace.json').exists())
        self.assertTrue(report['review']['provisional'])

    def test_existing_output_is_never_overwritten(self):
        self.path.mkdir();(self.path/'keep.txt').write_text('keep')
        with self.assertRaises(FileExistsError):self.evaluate()
        self.assertEqual((self.path/'keep.txt').read_text(),'keep')

    def test_wall_budget_is_an_interruption_not_a_low_score(self):
        with patch('evaluate_practice.monotonic',side_effect=[0,0,0,100]):
            with self.assertRaisesRegex(TimeoutError,'wall budget'):self.evaluate()
        report=json.loads((self.path/'summary.json').read_text())
        self.assertFalse(report['valid'] or report['passed'])
        self.assertEqual(report['layouts'],[])
        self.assertEqual(report['error_type'],'TimeoutError')
        self.assertTrue((self.path/'interrupted-trace.json').exists())

    def test_nearest_average_is_an_actual_game_with_stable_ties(self):
        rows=[dict(seed=i,trips=score,replay=str(i)+'.json') for i,score in enumerate([0,4,5,11])]
        review=select_review(rows,provisional=False)
        self.assertEqual(review['mean_score'],5)
        self.assertEqual(review['examples']['nearest_average']['seed'],2)


if __name__=='__main__':unittest.main()
