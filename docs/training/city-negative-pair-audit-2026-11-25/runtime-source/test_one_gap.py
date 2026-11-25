"""Scripted introductory-stage feasibility; never creates or updates a model."""
import json,os,tempfile,unittest
from pathlib import Path
from connection_practice import ConnectionPractice,WAIT
from environment import DIRS
from test_connection_practice import edit,enter_executor
from practice_replay import PracticeRecorder,verify

DOTNET=os.environ.get('STAGE1_DOTNET','dotnet')
DLL='simulation/Headless/bin/Release/net8.0/TrafficHost.dll'
RESULTS=[]

def gap(env):
    home=next(b for b in env.raw['buildings'] if b['isHouse'])
    shop=next(b for b in env.raw['buildings'] if not b['isHouse'])
    dx,dy=DIRS[shop['drivewayDirection']]
    target=(shop['entrance']['x']+dx,shop['entrance']['y']+dy)
    at=(home['cell']['x'],home['cell']['y']);missing=[]
    while at!=target:
        nxt=(at[0]+(target[0]>at[0])-(target[0]<at[0]),at[1]+(target[1]>at[1])-(target[1]<at[1]))
        d=DIRS.index((nxt[0]-at[0],nxt[1]-at[1]))
        if not env.raw['connections'][at[1]*50+at[0]]&(1<<d):missing.append((at,nxt))
        at=nxt
    if len(missing)!=1:raise AssertionError(('Expected exactly one absent edge',missing))
    return missing[0]

class OneGapChecks(unittest.TestCase):
    def make(self,split='train',stage='one-gap'):
        return ConnectionPractice(dotnet=DOTNET,host_dll=DLL,split=split,stage=stage)
    def test_100_layouts_each_split_complete_after_one_draw(self):
        for split,seeds in [('train',range(42,142)),('validation',range(20000,20100))]:
            env=self.make(split)
            try:
                for seed in seeds:
                    env.reset(seed=seed);a,b=gap(env)
                    self.assertEqual(env.raw['inventory'],[20,0,0,0,0,0])
                    edit(env,a,b)
                    env._call(command='step',ticks=3600)
                    self.assertGreaterEqual(env.info()['trips'],3)
                    self.assertFalse(env.raw['failed'])
                    RESULTS.append(dict(split=split,seed=seed,trips=env.info()['trips']))
            finally:env.close()
    def test_unsolved_gives_no_trips(self):
        env=self.make()
        try:
            for seed in range(42,52):
                env.reset(seed=seed);gap(env)
                env._call(command='step',ticks=3600)
                self.assertEqual(env.info()['trips'],0)
        finally:env.close()
    def test_pipeline_rewards_and_replay(self):
        env=self.make()
        try:
            # Use recorder for every hierarchy token, including successful connection.
            recorder=PracticeRecorder(env,seed=42);a,b=gap(env)
            for action in [0,1500,1,a[1]*50+a[0],DIRS.index((b[0]-a[0],b[1]-a[1]))]:
                result=recorder.step(action);self.assertEqual(result[1],0)
            reward=0
            while not env.done:
                action=0 if env.role in ('primary','executor') else 1500
                result=recorder.step(action);reward+=result[1]
            self.assertGreaterEqual(reward,3)
            self.assertEqual(reward,env.raw['tripsCompleted'])
            with tempfile.TemporaryDirectory() as directory:
                p=Path(directory)/'one-gap.json';recorder.save(p)
                self.assertEqual(verify(p,DOTNET,DLL)['result'],'PASS')
        finally:env.close()
    def test_clear_stage_still_empty_and_invalid_stage_rejected(self):
        env=self.make(stage='clear')
        try:
            env.reset(seed=42);self.assertFalse(any(env.raw['connections']))
        finally:env.close()
        with self.assertRaises(ValueError):self.make(stage='bad')

if __name__=='__main__':
    suite=unittest.main(exit=False,verbosity=2)
    path=os.environ.get('ONE_GAP_RESULTS')
    if path:Path(path).write_text(json.dumps(dict(passed=suite.result.wasSuccessful(),layouts=RESULTS),indent=2)+'\n')
    print(json.dumps(dict(passed=suite.result.wasSuccessful(),layouts_checked=len(RESULTS),minimum_trips=min((r['trips'] for r in RESULTS),default=None))))
    raise SystemExit(not suite.result.wasSuccessful())
