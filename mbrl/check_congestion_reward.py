"""Delivery-linked congestion shaping, bounds, thresholds and legacy overrides."""
import copy
import unittest

from check_requested_changes import OutcomeHost
from environment import TrafficEnv, ReplayBranch, SnapshotBranch, blocked_fraction


class VehiclesHost(OutcomeHost):
    def __init__(self,vehicles,**kwargs):
        super().__init__(demand=0,**kwargs)
        self.vehicles=vehicles

    def call(self,**request):
        result=super().call(**request)
        self.obs['vehicles']=copy.deepcopy(self.vehicles)
        return result


class CongestionRewardChecks(unittest.TestCase):
    def transition(self,vehicles=(),trips=0,cap=1.,**kwargs):
        host=VehiclesHost(list(vehicles),trips=trips)
        env=TrafficEnv(host,cap_seconds=cap,**kwargs)
        env.reset('LosAngeles',42)
        return env,env.step({'command':'wait'})

    def test_no_idle_bonus_with_no_completed_trips(self):
        for vehicles in ([],[{'stage':'Home','waiting':100}],
                         [{'stage':'Parking','waiting':100}],
                         [{'stage':'Outbound','waiting':0}]):
            _,step=self.transition(vehicles)
            self.assertEqual(step.reward,0)
            self.assertEqual(step.components['clearTripUnits'],0)
            self.assertEqual(step.components['congestionFractionSeconds'],0)

    def test_threshold_and_active_vehicle_filter(self):
        vehicles=[{'stage':'Outbound','waiting':2.}, {'stage':'Returning','waiting':1.999},
                  {'stage':'Home','waiting':100}, {'stage':'Parking','waiting':100},
                  {'waiting':100}]
        self.assertEqual(blocked_fraction({'vehicles':vehicles}),.5)
        self.assertEqual(blocked_fraction({'vehicles':vehicles},3.),0)

    def test_clear_partial_and_full_congestion(self):
        for waits,fraction,expected in (([0,1],0,30.3),([0,2],.5,30.14),([2,5],1,29.98)):
            _,step=self.transition([{'stage':'Outbound','waiting':w} for w in waits],trips=3)
            self.assertAlmostEqual(step.reward,expected)
            self.assertEqual(step.components['blockedFraction'],fraction)
            self.assertEqual(step.components['trips'],3)
            self.assertEqual(step.components['clearTripUnits'],3*(1-fraction))
            self.assertEqual(step.components['congestionFractionSeconds'],fraction)

    def test_penalty_without_deliveries_and_fractional_interval(self):
        vehicles=[{'stage':'Outbound','waiting':2}]
        _,full=self.transition(vehicles)
        _,fractional=self.transition(vehicles,cap=.25)
        self.assertAlmostEqual(full.reward,-.02)
        self.assertAlmostEqual(fractional.reward,-.005)
        self.assertEqual(fractional.components['congestionFractionSeconds'],.25)

    def test_normalized_penalty_does_not_scale_with_car_count(self):
        for count in (2,20,200):
            vehicles=[{'stage':'Outbound','waiting':2 if i%2 else 0} for i in range(count)]
            _,step=self.transition(vehicles)
            self.assertAlmostEqual(step.reward,-.01)

    def test_bonus_and_penalty_bounds_and_legacy_override(self):
        for blocked in range(11):
            vehicles=[{'stage':'Outbound','waiting':5 if i<blocked else 0} for i in range(10)]
            _,step=self.transition(vehicles,trips=5)
            self.assertLessEqual(.1*step.components['clearTripUnits'],.5)
            self.assertLessEqual(.02*step.components['congestionFractionSeconds'],.02)
            _,legacy=self.transition(vehicles,trips=5,trip_reward=1,
                                     clear_trip_bonus=0,congestion_fraction_penalty=0)
            self.assertEqual(legacy.reward,5)

    def test_custom_settings_reach_both_branch_types(self):
        env,_=self.transition(clear_trip_bonus=.08,congestion_fraction_penalty=.015,
                              congestion_wait_threshold=3)
        for kind in (SnapshotBranch,ReplayBranch):
            branch=kind(VehiclesHost([]),env)
            self.assertEqual(branch.env.clear_trip_bonus,.08)
            self.assertEqual(branch.env.congestion_fraction_penalty,.015)
            self.assertEqual(branch.env.congestion_wait_threshold,3)

    def test_invalid_weights_and_thresholds(self):
        for key in ('clear_trip_bonus','congestion_fraction_penalty'):
            for value in (-1,float('nan'),float('inf')):
                with self.assertRaises(ValueError):TrafficEnv(VehiclesHost([]),**{key:value})
        for value in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):TrafficEnv(VehiclesHost([]),congestion_wait_threshold=value)


if __name__=='__main__':
    unittest.main()
