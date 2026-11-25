"""Replay correctness only; no model/learner is instantiated."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

from connection_practice import ConnectionPractice,DRAW,WAIT,HANDOFF,NONE,CANCEL
from practice_replay import PracticeRecorder,verify

DOTNET='dotnet'
DLL=None


class ReplayChecks(unittest.TestCase):
    def setUp(self):
        self.env=ConnectionPractice(dotnet=DOTNET,host_dll=DLL)
        self.directory=tempfile.TemporaryDirectory()
        self.path=Path(self.directory.name)/'trace.json'

    def tearDown(self):
        self.env.close();self.directory.cleanup()

    def test_paused_cancellation_focus_changes_and_wait_replay(self):
        recorder=PracticeRecorder(self.env,seed=42)
        for action in (0,NONE,DRAW,CANCEL,DRAW,0,0,HANDOFF,1,2,WAIT):
            recorder.step(action)
        recorder.save(self.path)
        self.assertEqual(self.env.raw['time'],1)
        self.assertEqual(self.env.role,'primary')
        report=verify(self.path,DOTNET,DLL)
        self.assertEqual(report['result'],'PASS')
        self.assertFalse(report['complete'])
        self.assertEqual(report['ending_reason'],'partial')

    def test_operational_interruption_replays_as_incomplete_game(self):
        self.env.max_paused_tokens=3
        recorder=PracticeRecorder(self.env,seed=43)
        for action in (0,NONE,HANDOFF):recorder.step(action)
        recorder.save(self.path)
        report=verify(self.path,DOTNET,DLL)
        self.assertTrue(report['complete'])
        self.assertEqual(report['ending_reason'],'paused_policy_stall')
        self.assertEqual(report['seconds'],0)

    def test_tampered_token_result_and_source_are_rejected(self):
        recorder=PracticeRecorder(self.env,seed=44)
        recorder.step(0);recorder.save(self.path)
        trace=json.loads(self.path.read_text());trace['tokens'][0]['score']=999
        self.path.write_text(json.dumps(trace))
        with self.assertRaisesRegex(ValueError,'diverged'):verify(self.path,DOTNET,DLL)
        recorder.save(self.path)
        trace=json.loads(self.path.read_text());trace['identity']['dll_sha256']='wrong'
        self.path.write_text(json.dumps(trace))
        with self.assertRaisesRegex(ValueError,'source/build/protocol'):verify(self.path,DOTNET,DLL)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dotnet',default='dotnet');p.add_argument('--dll')
    args,rest=p.parse_known_args();DOTNET,DLL=args.dotnet,args.dll
    unittest.main(argv=[sys.argv[0]]+rest)
