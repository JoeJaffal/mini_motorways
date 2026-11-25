"""Opt-in mini-task reset curriculum from the policy's own saved games."""
import json
from pathlib import Path
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT, SMALL_OFFSET
from city_recorded_starts import raw_digest, observation_digest
from prepare_city_policy import sha256

class MiniRecordedStartEnv(CityCurriculumEnv):
    def __init__(self,dll,*,mini_starts,**kwargs):
        data=json.loads(Path(mini_starts).read_text())
        if data.get('schema')!='native-mini-starts-v1' or data['host_sha256']!=sha256(Path(dll)):
            raise ValueError('Mini starts require their exact native host')
        if kwargs.get('stage')!='expansion-balanced' or kwargs.get('workers',0)%16:
            raise ValueError('Mini starts require expansion-balanced with a multiple of16 workers')
        self.start_groups={ex:[s for s in data['starts'] if s['exercise']==ex] for ex in (SMALL_TIGHT,SMALL_OFFSET)}
        if any(len(group)<8 for group in self.start_groups.values()):
            raise ValueError('At least8 recorded starts per task are required')
        self.prefix_cursor=kwargs.get('worker',0);self.prefix_id=None
        super().__init__(dll,**kwargs)

    def reset(self,*,seed=None,options=None):
        self.prefix_id=None
        rank=self.worker%16
        if options is not None or rank not in (10,11,14,15):
            return super().reset(seed=seed,options=options)
        ex=SMALL_OFFSET if rank<12 else SMALL_TIGHT
        group=self.start_groups[ex];prefix=group[self.prefix_cursor%len(group)];self.prefix_cursor+=1
        obs,info=super().reset(seed=seed,options=dict(exercise=ex,scenario_seed=prefix['seed']))
        for action in prefix['actions']:
            if self.done or not self.action_masks()[action]:raise RuntimeError('Unavailable recorded mini action')
            obs,_,_,_,info=self._step_once(action)
        if self.done or raw_digest(self.raw)!=prefix['raw_sha256'] or observation_digest(obs)!=prefix['observation_sha256']:
            raise RuntimeError('Mini reset prefix mismatch')
        self.prefix_id=prefix['id']
        # Reset rewards/counters only; native roads, stock, time, future arrival
        # and the configured absolute lesson deadline stay unchanged. Prefix
        # time is not added back to extend the learner's remaining time budget.
        self.start_time=self.raw['time'];self.start_score=self.raw['tripsCompleted']
        self.initial_served={b['id']:b['served'] for b in self.raw['buildings'] if not b['isHouse']}
        self.initial_pending=[k for k,v in self.initial_served.items() if v==0]
        self.stock_initial=self.raw['inventory'][0];self.future_stock=None
        self.road_actions=self.wait_actions=self.weekly_awards=0;self.first_action=None
        return obs,self.info()

    def info(self):
        return dict(super().info(),prefix_id=self.prefix_id)
