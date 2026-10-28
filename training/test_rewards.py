"""Shaping accounting and anti-cycle checks; no learning/optimizer updates."""
import argparse
import unittest
import sys
import json
from rewards import ConnectionPotential,GAMMA
from environment import TrafficEnv,CELLS,ROOT

DOTNET='dotnet'


class PotentialChecks(unittest.TestCase):
    def test_connection_break_cycle_and_terminal_cancel(self):
        reward=ConnectionPotential();reward.reset(0)
        self.assertAlmostEqual(reward.step(1),.24975)
        self.assertAlmostEqual(reward.step(0),-.25)
        # Discounted create/delete loop has zero additional return, not a bonus.
        reward.reset(0)
        changes=[reward.step(n) for n in [1,0]*30]
        self.assertAlmostEqual(sum(GAMMA**i*r for i,r in enumerate(changes)),0,places=12)
        reward.reset(0)
        changes=[reward.step(1),reward.step(1),reward.step(1,terminated=True)]
        self.assertAlmostEqual(sum(GAMMA**i*r for i,r in enumerate(changes)),0,places=12)

    def test_cap_reset_and_external_limit_bootstrap(self):
        reward=ConnectionPotential();reward.reset(100)
        self.assertEqual(reward.previous,2)
        self.assertAlmostEqual(reward.step(100),-.002)
        self.assertEqual(reward.previous,2)  # Time-limit transitions retain live potential.
        reward.reset(0);self.assertEqual(reward.previous,0)
        with self.assertRaises(ValueError):reward.potential(None)

    def test_real_hosts_identical_observations_and_nonconnection_zero(self):
        plain=TrafficEnv(dotnet=DOTNET,seeds=[1000],seconds=2)
        shaped=TrafficEnv(dotnet=DOTNET,seeds=[1000],seconds=2,reward_mode='connectivity')
        try:
            import numpy as np
            a,_=plain.reset(seed=42);b,info=shaped.reset(seed=42)
            self.assertEqual(info['connected_houses'],0)
            for k in a:np.testing.assert_array_equal(a[k],b[k])
            for _ in range(2):
                a,r,term,trunc,ia=plain.step(CELLS)
                b,s,tm,tc,ib=shaped.step(CELLS)
                self.assertEqual((r,term,trunc),(s,tm,tc))
                self.assertEqual(s,0)
                for k in a:np.testing.assert_array_equal(a[k],b[k])
            self.assertTrue(tc)
            self.assertEqual(ib['trip_reward_total'],0)
            self.assertEqual(ib['shaping_reward_total'],0)
        finally:plain.close();shaped.close()

    def test_intermediate_selection_is_shaped_without_simulation_time(self):
        env=TrafficEnv(dotnet=DOTNET,reward_mode='connectivity')
        try:
            env.reset(seed=42,options={'scenario_seed':1000})
            # Inject only the diagnostic to isolate selection accounting; this
            # fixture does not change a city or become training experience.
            env.connected_houses=1;env.connection_potential.reset(1)
            _,r,_,_,info=env.step(CELLS+1)
            self.assertFalse(info['command_completed'])
            self.assertEqual(env.raw['time'],0)
            self.assertAlmostEqual(r,-.00025)
            self.assertAlmostEqual(info['shaping_reward_total'],r)
            self.assertEqual(info['trip_reward'],0)
        finally:env.close()

    def test_recorded_normal_game_connects_before_trip_and_keeps_simulation_identical(self):
        import numpy as np
        path=ROOT/'docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/best-game.json'
        recording=json.loads(path.read_text())
        plain=TrafficEnv(dotnet=DOTNET,seeds=[recording['seed']])
        shaped=TrafficEnv(dotnet=DOTNET,seeds=[recording['seed']],reward_mode='connectivity')
        try:
            plain.reset(seed=42);shaped.reset(seed=42)
            discounted_shaping=0;positive_before_trip=False;connected_seen=False
            for i,event in enumerate(recording['actions']):
                request={k:v for k,v in event.items() if k in ['command','tool','x','y','toX','toY','id','choice']}
                if request['command']=='wait':request=None
                a,r,term,trunc,ia=plain._advance(request)
                b,s,tm,tc,ib=shaped._advance(request)
                self.assertEqual((term,trunc,ia['trips'],ia['accepted']),(tm,tc,ib['trips'],ib['accepted']))
                for k in a:np.testing.assert_array_equal(a[k],b[k])
                self.assertAlmostEqual(s,r+ib['shaping_reward'])
                discounted_shaping+=GAMMA**i*ib['shaping_reward']
                connected_seen |= ib['connected_houses']>0
                positive_before_trip |= ib['shaping_reward']>0 and ib['trips']==0
                self.assertLessEqual(ib['connection_potential'],2)
            self.assertTrue(term);self.assertFalse(trunc)
            self.assertEqual(ia['trips'],recording['score'])
            self.assertTrue(connected_seen);self.assertTrue(positive_before_trip)
            self.assertEqual(ib['connection_potential'],0)
            self.assertAlmostEqual(discounted_shaping,0,places=10)
            self.assertEqual(ib['trip_reward_total'],recording['score'])
            self.assertAlmostEqual(ib['training_reward_total'],ib['trip_reward_total']+ib['shaping_reward_total'])
        finally:plain.close();shaped.close()

    def test_connected_external_cap_retains_live_potential(self):
        recording=json.loads((ROOT/'docs/training/evidence-2026-10-28/runs/seed-1000-parallel-02/best-game.json').read_text())
        env=TrafficEnv(dotnet=DOTNET,seeds=[recording['seed']],reward_mode='connectivity')
        try:
            env.reset(seed=42)
            for event in recording['actions']:
                request={k:v for k,v in event.items() if k in ['command','tool','x','y','toX','toY','id','choice']}
                env._advance(None if request['command']=='wait' else request)
                if env.connected_houses:break
            self.assertGreater(env.connected_houses,0)
            previous=env.connection_potential.previous
            env.seconds=env.raw['time']+1
            _,reward,terminated,truncated,info=env.step(CELLS)
            self.assertFalse(terminated);self.assertTrue(truncated)
            self.assertGreater(info['connection_potential'],0)
            self.assertAlmostEqual(info['shaping_reward'],GAMMA*info['connection_potential']-previous)
            self.assertAlmostEqual(reward,info['trip_reward']+info['shaping_reward'])
        finally:env.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dotnet',default='dotnet')
    args,rest=parser.parse_known_args();DOTNET=args.dotnet
    unittest.main(argv=[sys.argv[0]]+rest)
