"""Frozen diagnostic adapter: current city observations/actions on native pairs."""
import gymnasium as gym
from city_road_pilot import CityRoadEnv
from city_curriculum import CityCurriculumEnv

CASES=('match','mismatch','homes','destinations')
class CityPairAuditEnv(CityCurriculumEnv):
    def __init__(self,*args,**kwargs):
        CityRoadEnv.__init__(self,*args,**kwargs)
    info=CityRoadEnv.info
    # Use the existing native practice connection/Wait semantics, without the
    # curriculum's destination-dependent bookkeeping or any automatic Finish.
    step=CityCurriculumEnv._step_once
    def reset(self,*,seed=None,options=None):
        gym.Env.reset(self,seed=seed)
        self.scenario_seed=options['scenario_seed'];case=options['case']
        self.exercise='pair-'+case;self.cached_mask=None;self.first_action=None
        assert case in CASES
        result=self.host.call(command='reset',version='OriginalReference',practice=True,
            practiceStage='curriculum-pair-'+case,practiceSplit='validation',seed=self.scenario_seed)
        assert result['accepted'] and not result['terminated'] and not result['truncated']
        self.raw=result['observation'];assert self.raw['time']==0
        homes=[b for b in self.raw['buildings'] if b['isHouse']]
        shops=[b for b in self.raw['buildings'] if not b['isHouse']]
        assert (len(homes),len(shops))=={'match':(1,1),'mismatch':(1,1),'homes':(2,0),'destinations':(0,2)}[case]
        if case=='match':assert homes[0]['color']==shops[0]['color']==1
        if case=='mismatch':assert homes[0]['color']==1 and shops[0]['color']==0
        if case=='homes':assert all(b['color']==1 for b in homes)
        if case=='destinations':assert all(b['color']==0 for b in shops)
        self.encoder.reset();self.done=False
        self.weekly_awards=self.road_actions=self.wait_actions=0
        return self.observation(),self.info()
