"""Verify held-out isolation and every-third-example validation, including resume."""
from contextlib import nullcontext, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

import experiment
from protocol import SingleCitySeeds, SINGLE_CITY_PROTOCOL, evaluation_cases, MAX_GAME_SEED

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'output/mbrl/recovery-20261101/host/TrafficHost.dll'


class SingleCityChecks(unittest.TestCase):
    def test_seed_collisions_and_held_out_seeds_are_skipped(self):
        split=SingleCitySeeds()
        with patch.object(split.rng,'randint',side_effect=[200000,300000,123,123,456]):
            self.assertEqual(split.training_case(),('LosAngeles',123))
            self.assertEqual(split.training_case(),('LosAngeles',456))
        self.assertEqual(split.used,{123,456})

    def test_sampler_restores_the_exact_sequence(self):
        split=SingleCitySeeds(sequence_seed=7)
        first=[split.training_case() for _ in range(1000)]
        state=split.state_dict()
        expected=[split.training_case() for _ in range(100)]
        resumed=SingleCitySeeds(sequence_seed=99)
        resumed.load_state_dict(state)
        actual=[resumed.training_case() for _ in range(100)]
        self.assertEqual(actual,expected)
        self.assertEqual(len({seed for _,seed in first+actual}),1100)
        self.assertTrue(all(city=='LosAngeles' and seed not in (200000,300000) for city,seed in first+actual))

    def test_invalid_splits_are_rejected(self):
        for seed in (-1,0,MAX_GAME_SEED+1):
            with self.assertRaises(ValueError):SingleCitySeeds(validation_seed=seed)
        with self.assertRaises(ValueError):SingleCitySeeds(validation_seed=3,test_seed=3)
        state=SingleCitySeeds().state_dict()
        state['usedSeeds']=[200000]
        with self.assertRaises(ValueError):SingleCitySeeds().load_state_dict(state)

    def test_evaluator_uses_the_saved_city_and_single_seed(self):
        config={'experimentProtocol':SINGLE_CITY_PROTOCOL,'city':'LosAngeles',
                'validationSeed':200000,'testSeed':300000}
        self.assertEqual(evaluation_cases(config,'validation'),[('LosAngeles',200000)])
        self.assertEqual(evaluation_cases(config,'test'),[('LosAngeles',300000)])
        with self.assertRaises(ValueError):evaluation_cases(config,'validation',2)
        self.assertEqual(evaluation_cases({},'validation'),[('DarEsSalaam',200000),('DarEsSalaam',200001)])

    def run_cli(self,out,episodes,resume=None):
        calls=[]
        def episode(env,branch,city,seed,model,simulations,rng,explore,**kwargs):
            self.assertEqual(city,'LosAngeles')
            self.assertNotEqual(seed,300000,'Reserved test game was opened')
            calls.append((city,seed,explore,kwargs.get('baseline',False)))
            row={'map':city,'seed':seed,'trips':100,'waitingSeconds':0.,'modificationCost':0.}
            return [],row,{'scenario':city,'seed':seed,'actions':[]}
        args=['experiment.py','--episodes',str(episodes),'--updates-per-episode','1',
              '--batch-size','1','--seed-sequence-seed','17','--host-dll',str(HOST),
              '--output',str(out)]
        if resume:args+=['--resume',str(resume)]
        with patch.object(sys,'argv',args), \
             patch.object(experiment,'Host',side_effect=lambda **kwargs:nullcontext(object())), \
             patch.object(experiment,'TrafficEnv',side_effect=lambda *args,**kwargs:SimpleNamespace()), \
             patch.object(experiment,'SnapshotBranch',side_effect=lambda *args:object()), \
             patch.object(experiment,'SearchPool',side_effect=lambda *args:nullcontext(object())), \
             patch.object(experiment,'viewer_context',side_effect=lambda *args:nullcontext(None)), \
             patch.object(experiment,'run_episode',side_effect=episode), \
             patch.object(experiment,'train_batch',return_value={'loss':.1}), redirect_stdout(io.StringIO()):
            experiment.main()
        return calls

    def test_validation_only_after_three_and_six_examples(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp',prefix='single-city-check-') as folder:
            out=Path(folder)/'six'
            calls=self.run_cli(out,6)
            self.assertEqual([call[2] for call in calls],[True,True,True,False,True,True,True,False])
            self.assertTrue(all(not call[3] for call in calls),'Automatic baseline opened validation early')
            validation=[json.loads(line) for line in (out/'validation.jsonl').read_text().splitlines()]
            self.assertEqual([row['checkpointEpisode'] for row in validation],[3,6])
            self.assertTrue(all(row['seed']==200000 for row in validation))
            self.assertFalse((out/'test.jsonl').exists())
            state=torch.load(out/'checkpoint-last.pt',weights_only=False)
            self.assertEqual(state['trainingExamplesCompleted'],6)
            self.assertEqual(len(state['trainingSeedSampler']['usedSeeds']),6)

    def test_partial_batch_and_resume_keep_validation_cadence(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp',prefix='single-city-resume-check-') as folder:
            folder=Path(folder)
            first=self.run_cli(folder/'first',2)
            self.assertEqual(len(first),2)
            self.assertFalse((folder/'first/validation.jsonl').exists())
            resumed=self.run_cli(folder/'resumed',4,folder/'first/checkpoint-last.pt')
            self.assertEqual([call[2] for call in resumed],[True,False,True,True,True,False])
            whole=self.run_cli(folder/'whole',6)
            self.assertEqual(first+resumed,whole)
            partial=folder/'partial'
            self.run_cli(partial,4)
            selection=json.loads((partial/'selection.json').read_text())
            self.assertEqual(selection['selected']['episode'],4)
            self.assertIsNone(selection['selected']['validation'])
            self.assertEqual(selection['latestValidation']['episode'],3)


if __name__=='__main__':
    unittest.main()
