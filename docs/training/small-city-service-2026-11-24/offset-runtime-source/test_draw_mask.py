"""Productive-stroke mask blocks proven no-ops without altering game state."""
import argparse
import json
import unittest
import sys
import numpy as np
from environment import TrafficEnv,ROOT,CELLS

DOTNET='dotnet';DLL=None


class DrawMaskChecks(unittest.TestCase):
    def test_repeated_completed_stroke_is_masked_and_probe_is_read_only(self):
        env=TrafficEnv(dotnet=DOTNET,host_dll=DLL,draw_mask='productive')
        try:
            env.reset(seed=42,options={'scenario_seed':1000})
            r=json.loads((ROOT/'docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/best-game.json').read_text())
            found=None
            for event in r['actions'][:60]:
                req={k:v for k,v in event.items() if k in ['command','tool','x','y','toX','toY','id','choice']}
                env._advance(None if req['command']=='wait' else req)
                if req and req['command']=='draw':
                    before=env.encode()
                    choices=env.host.call(command='drawchoices',x=req['x'],y=req['y'])['possibleChanges']
                    for key in before:np.testing.assert_array_equal(before[key],env.encode()[key])
                    if not choices[req['toY']*50+req['toX']]:found=req;break
            self.assertIsNotNone(found)
            env.step(CELLS+1);env.step(found['y']*50+found['x'])
            target=found['toY']*50+found['toX']
            self.assertFalse(env.action_masks()[target])
            self.assertTrue(env.action_masks().any())
            current=env.host.call(command='observe')['observation']
            self.assertEqual(current['time'],env.raw['time'])
            self.assertEqual(current['connections'],env.raw['connections'])
        finally:env.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dotnet',default='dotnet');p.add_argument('--host-dll')
    a,rest=p.parse_known_args();DOTNET=a.dotnet;DLL=a.host_dll
    unittest.main(argv=[sys.argv[0]]+rest)
