"""Native replay parity, reward exclusion, cold-reset and forced-Wait checks."""
import argparse
import json
from pathlib import Path
import numpy as np
from city_curriculum import CityCurriculumEnv, SMALL_TIGHT, SMALL_OFFSET
from mini_recorded_starts import MiniRecordedStartEnv
from city_recorded_starts import raw_digest, observation_digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',required=True);p.add_argument('--bank',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    bank=json.loads(Path(a.bank).read_text());checked=[];transitions=0
    env=MiniRecordedStartEnv(a.dll,mini_starts=a.bank,stage='expansion-balanced',workers=16,worker=14)
    plain=CityCurriculumEnv(a.dll)
    try:
        for ex,rank in ((SMALL_TIGHT,14),(SMALL_OFFSET,10)):
            env.worker=rank;env.prefix_cursor=0
            for prefix in env.start_groups[ex]:
                obs,info=env.reset();assert info['prefix_id']==prefix['id']
                assert info['trips']==0 and sum(info['served'].values())==0 and info['road_actions']==0
                assert info['stock_initial']==prefix['stock'] and env.horizon==60
                assert raw_digest(env.raw)==prefix['raw_sha256'] and observation_digest(obs)==prefix['observation_sha256']
                obs2,_=plain.reset(options=dict(exercise=ex,scenario_seed=prefix['seed']))
                for action in prefix['actions']:obs2,_,_,_,_=plain.step(action)
                total=0;start=env.raw['tripsCompleted'];rng=np.random.default_rng(prefix['seed'])
                while not env.done:
                    np.testing.assert_array_equal(env.action_masks(),plain.action_masks())
                    # Wait-biased legal continuation still exercises occasional builds.
                    mask=env.action_masks();action=int(rng.choice(np.flatnonzero(mask))) if rng.random()<.2 else 0
                    obs,r,t,u,info=env.step(action);obs2,r2,t2,u2,info2=plain.step(action)
                    assert (r,t,u)==(r2,t2,u2) and env.raw==plain.raw
                    for key in obs:np.testing.assert_array_equal(obs[key],obs2[key])
                    total+=r;transitions+=1
                assert total==info['trips']==env.raw['tripsCompleted']-start==sum(info['served'].values())
                checked.append(prefix['id'])
        # Explicit evaluation requests must stay on empty boards, even on warm workers.
        for ex in (SMALL_TIGHT,SMALL_OFFSET):
            options=dict(exercise=ex,scenario_seed=235000000)
            obs,info=env.reset(options=options);obs2,info2=plain.reset(options=options)
            assert env.raw==plain.raw and info['prefix_id'] is None and info['trips']==0
            for key in obs:np.testing.assert_array_equal(obs[key],obs2[key])
    finally:env.close();plain.close()
    # Compare compression against primitive Wait, including the second arrival.
    compressed=MiniRecordedStartEnv(a.dll,mini_starts=a.bank,stage='expansion-balanced',workers=16,worker=10,collapse_forced_wait=True)
    primitive=MiniRecordedStartEnv(a.dll,mini_starts=a.bank,stage='expansion-balanced',workers=16,worker=10)
    try:
        compressed.reset();primitive.reset();totals=[0,0]
        while not compressed.done:
            mask=compressed.action_masks();action=int(np.flatnonzero(mask)[-1])
            _,r,_,_,_=compressed.step(action);totals[0]+=r
            _,r,_,_,_=primitive.step(action);totals[1]+=r
            while primitive.raw['time']<compressed.raw['time']-1e-6 and not primitive.done:
                _,r,_,_,_=primitive.step(0);totals[1]+=r
            assert compressed.raw==primitive.raw
        assert totals[0]==totals[1]
    finally:compressed.close();primitive.close()
    a.output.write_text(json.dumps(dict(starts=len(checked),unique_starts=len(set(checked)),exact_transitions=transitions,reward_prefix_excluded=True,empty_evaluation_resets=True,forced_wait_parity=True),indent=2));print(a.output.read_text())

if __name__=='__main__':main()
