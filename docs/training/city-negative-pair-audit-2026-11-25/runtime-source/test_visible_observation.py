"""Semantic visibility/history tests; synthetic observations, no learner."""
import copy
import unittest

import numpy as np
from visible_observation import VisibleObservation, observation_space


def scene():
    z = [0]*1500
    return dict(width=50,height=30,time=0.,day=0,week=1,
        playableXMin=0,playableXMax=50,playableYMin=0,playableYMax=30,
        terrain=z.copy(),infrastructure=z.copy(),connections=z.copy(),
        pendingRemovals=z.copy(),buildingKinds=z.copy(),buildingColors=[-1]*1500,
        demand=z.copy(),buildings=[],vehicles=[],motorways=[],roundabouts=[],
        railLines=[],closedRailCrossings=[],trains=[],inventory=[20,0,0,0,0,0],upgradeChoices=[])


def car(identity=1,x=10.,y=10.,**extra):
    result=dict(id=identity,x=x,y=y,headingX=1.,headingY=0.,visible=True)
    result.update(extra)
    return result


def compare(test,a,b):
    for key in a:
        np.testing.assert_array_equal(a[key],b[key],err_msg=key)


class VisibleChecks(unittest.TestCase):
    def test_published_shapes_bounds_and_empty_table(self):
        output=VisibleObservation().encode(scene(),horizon=180)
        self.assertTrue(observation_space().contains(output))
        self.assertEqual(output['grid'].shape,(81,30,50))
        self.assertEqual(output['global'].shape,(54,))
        self.assertFalse(output['motorways'].any())
        self.assertAlmostEqual(output['global'][27],.05)
        self.assertFalse(output['grid'][57:].any())

    def test_hidden_diagnostics_have_no_effect(self):
        raw=scene(); raw['vehicles']=[car()]
        changed=copy.deepcopy(raw)
        changed.update(tripsCompleted=999,meanWaiting=123,reservations=[999]*1500,
            scheduledSpawns=[{'time':-1}],randomDraws=999,randomAlgorithm='secret',scenario='London')
        changed['vehicles'][0].update(speed=999,waiting=888,route=[{'x':49,'y':29}],
            returnRoute=[{'x':0,'y':0}],obstacle='secret',acceleration=100,progress=.999)
        compare(self,VisibleObservation().encode(raw,horizon=180),VisibleObservation().encode(changed,horizon=180))

    def test_distinct_time_history_measures_positions_not_internal_speed(self):
        encoder=VisibleObservation(); raw=scene();raw['vehicles']=[car()]
        first=encoder.encode(raw,horizon=180)
        self.assertEqual(first['grid'][57,10,10],.5)
        self.assertFalse(first['global'][45:49].any())
        raw['time']=1;raw['vehicles']=[car(x=11.,speed=999,waiting=999)]
        moved=encoder.encode(raw,horizon=180)
        self.assertAlmostEqual(moved['grid'][60,10,11],.2)
        self.assertEqual(moved['grid'][62,10,11],0)
        self.assertEqual(moved['global'][45],1)
        self.assertAlmostEqual(moved['global'][50],.5)
        self.assertEqual(moved['grid'][63,10,10],.5)
        raw['time']=2
        stopped=encoder.encode(raw,horizon=180)
        self.assertEqual(stopped['grid'][62,10,11],1)
        self.assertEqual(stopped['grid'][60,10,11],0)
        raw['time']=3;encoder.encode(raw,horizon=180)
        raw['time']=4;encoder.encode(raw,horizon=180)
        self.assertEqual(len(encoder.frames),4)
        self.assertEqual(encoder.frames[-1][0],1)

    def test_paused_changes_do_not_duplicate_or_advance_history(self):
        encoder=VisibleObservation();raw=scene();raw['vehicles']=[car()]
        first=encoder.encode(raw,horizon=180)
        raw['infrastructure'][0]=1
        for _ in range(10):
            next_obs=encoder.encode(raw,horizon=180,paused_tokens=4)
        np.testing.assert_array_equal(first['grid'][57:],next_obs['grid'][57:])
        self.assertEqual(len(encoder.frames),1)
        self.assertNotEqual(first['grid'][5,0,0],next_obs['grid'][5,0,0])
        self.assertAlmostEqual(next_obs['global'][44],4/4096)

    def test_invisible_geometry_cannot_leak_through_aggregation(self):
        raw=scene();raw.update(playableXMin=5,playableXMax=15,playableYMin=5,playableYMax=15)
        raw['vehicles']=[car()]
        changed=copy.deepcopy(raw)
        changed['vehicles'].extend([car(2,x=30),car(3,x=10,visible=False)])
        changed['terrain'][0]=999
        changed['infrastructure'][0]=999
        changed['connections'][0]=999
        changed['buildingColors'][0]=999
        changed['motorways']=[dict(id=1,start={'x':30,'y':20},end={'x':40,'y':25},pendingRemoval=False)]
        a=VisibleObservation().encode(raw,horizon=180)
        b=VisibleObservation().encode(changed,horizon=180)
        compare(self,a,b)
        self.assertFalse(a['grid'][:,:,0].any())

    def test_warning_is_boolean_and_internal_building_fields_are_excluded(self):
        raw=scene()
        building=dict(id=0,cell={'x':10,'y':10},width=2,height=3,color=0,isHouse=False,
            upgraded=False,sharedLot=False,isStation=False,warningVisible=True,
            entrance={'x':10,'y':12},entrances=[],entranceDirections=[],drivewayDirection=4)
        raw['buildings']=[building]
        for y in range(10,13):
            for x in range(10,12):
                raw['buildingKinds'][x+50*y]=2;raw['buildingColors'][x+50*y]=0;raw['demand'][x+50*y]=5
        changed=copy.deepcopy(raw)
        changed['buildings'][0].update(overcrowdedFor=999,reserved=999,feasibilityVerified=True,
            feasibleDemandInterval=.001,originalDemandInterval=.001,upgradeAt=1,plannedDemandMultiplier=999)
        a=VisibleObservation().encode(raw,horizon=180)
        compare(self,a,VisibleObservation().encode(changed,horizon=180))
        self.assertEqual(a['grid'][42,10,10],1)
        self.assertAlmostEqual(a['grid'][41,10,10],1/3)
        changed['buildings'][0]['warningVisible']=False
        self.assertEqual(VisibleObservation().encode(changed,horizon=180)['grid'][42,10,10],0)

    def test_visible_retiring_motorway_pair_and_hidden_end(self):
        raw=scene(); raw['motorways']=[dict(id=77,start={'x':5,'y':6},end={'x':10,'y':9},pendingRemoval=True)]
        obs=VisibleObservation().encode(raw,horizon=180)
        np.testing.assert_allclose(obs['motorways'][0],[5/49,6/29,10/49,9/29,1,1])
        self.assertEqual(obs['grid'][44,6,5],1)
        raw['playableXMax']=8
        obs=VisibleObservation().encode(raw,horizon=180)
        self.assertFalse(obs['motorways'].any())
        self.assertEqual(obs['grid'][44,6,5],1)
        self.assertEqual(obs['grid'][45,6,5],0)

    def test_unknown_visible_values_and_overflow_fail(self):
        for name,value in [('terrain',3),('infrastructure',5),('buildingColors',8),('connections',256),('buildingKinds',.5)]:
            raw=scene();raw[name][0]=value
            with self.assertRaises(ValueError,msg=name):
                VisibleObservation().encode(raw,horizon=180)
        raw=scene();raw['motorways']=[dict(id=i,start={'x':1,'y':1},end={'x':2,'y':2},pendingRemoval=False) for i in range(1500)]
        with self.assertRaises(ValueError): VisibleObservation().encode(raw,horizon=180)

    def test_history_reset_and_time_reversal(self):
        encoder=VisibleObservation();raw=scene();raw['time']=1
        encoder.encode(raw,horizon=180)
        raw['time']=0
        with self.assertRaises(ValueError): encoder.encode(raw,horizon=180)
        encoder.reset();encoder.encode(raw,horizon=180)
        self.assertEqual(len(encoder.frames),1)


if __name__=='__main__': unittest.main()
