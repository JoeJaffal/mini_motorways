"""Exact native parity for the opt-in terminal-only small-city acceleration."""
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import time
import numpy as np
import torch
from sb3_contrib import MaskablePPO
from city_curriculum import CityCurriculumEnv, SMALL_LESSONS, SMALL_TIGHT, SMALL_OFFSET
from mini_recorded_starts import MiniRecordedStartEnv
from prepare_city_policy import masked_probs, sha256

ROOT=Path('docs/training/mini-task-repair-2026-11-25')
DLL=Path('output/road-cost-reward-build-02/bin/TrafficHost/release/TrafficHost.dll')
PARENT=Path('output/training/city-whole-initial-01/start.zip')
BANK=ROOT/'start-bank/starts.json'


def worker(jobs):
    torch.set_num_threads(1);model=MaskablePPO.load(PARENT,device='cpu');rows=[]
    for exercise,seed,horizon,prefix in jobs:
        kwargs=dict(collapse_forced_wait=True,small_city_horizon=horizon)
        cls=CityCurriculumEnv
        if prefix is not None:
            cls=MiniRecordedStartEnv
            kwargs.update(mini_starts=str(BANK),stage='expansion-balanced',workers=16,worker=14 if exercise==SMALL_TIGHT else 10)
        slow=cls(str(DLL),**kwargs);fast=cls(str(DLL),fast_small_city_tail=True,**kwargs)
        try:
            if prefix is None:
                options=dict(exercise=exercise,scenario_seed=seed)
                x,ix=slow.reset(options=options);y,iy=fast.reset(options=options)
            else:
                slow.prefix_cursor=fast.prefix_cursor=prefix
                x,ix=slow.reset();y,iy=fast.reset()
            assert ix==iy and slow.raw==fast.raw
            rng=np.random.default_rng(seed+207);times=[0.,0.];decisions=0;compressed=0
            while not slow.done:
                for key in x:np.testing.assert_array_equal(x[key],y[key])
                mask=slow.action_masks();np.testing.assert_array_equal(mask,fast.action_masks())
                p=mask.astype(float) if mask.sum()==1 else masked_probs(model,x,mask).astype(float)
                action=int(rng.choice(len(p),p=p/p.sum()))
                start=time.perf_counter();x,ra,ta,ua,ia=slow.step(action);times[0]+=time.perf_counter()-start
                start=time.perf_counter();y,rb,tb,ub,ib=fast.step(action);times[1]+=time.perf_counter()-start
                assert (ra,ta,ua,ia)==(rb,tb,ub,ib),(exercise,seed,horizon,ia,ib)
                assert slow.raw==fast.raw
                np.testing.assert_array_equal(slow.action_masks(),fast.action_masks())
                decisions+=1;compressed+=ia['forced_waits']
            assert fast.done and ta and not ua
            # Terminal motion history may differ, but this finite episode has
            # terminated=True and is never bootstrapped. Next reset must match.
            options=dict(exercise=exercise,scenario_seed=seed+100)
            x,ix=slow.reset(options=options);y,iy=fast.reset(options=options)
            assert ix==iy and slow.raw==fast.raw
            for key in x:np.testing.assert_array_equal(x[key],y[key])
            row=dict(exercise=exercise,seed=seed,horizon=horizon,prefix=prefix,decisions=decisions,
                     forced_waits=compressed,slow_step_seconds=times[0],fast_step_seconds=times[1])
            rows.append(row);print('TAIL',exercise,seed,horizon,prefix,decisions,times,flush=True)
        finally:slow.close();fast.close()
    return rows


def main():
    output=ROOT/'small-tail-check';output.mkdir(exist_ok=False)
    jobs=[(ex,235200000+i,h,None) for ex in SMALL_LESSONS for h in (60,300) for i in range(4)]
    jobs += [(ex,235201000+i,h,i) for ex in (SMALL_TIGHT,SMALL_OFFSET) for h in (60,300) for i in range(12)]
    before=sha256(PARENT)
    with ProcessPoolExecutor(max_workers=2,mp_context=mp.get_context('spawn')) as pool:
        rows=[row for f in [pool.submit(worker,jobs[k::2]) for k in range(2)] for row in f.result()]
    assert sha256(PARENT)==before
    (output/'games.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    summary=dict(games=len(rows),exact_native_state_reward_flags_info_masks=True,
                 nonterminal_and_next_reset_observations_exact=True,
                 terminal_motion_history_not_compared_or_bootstrapped=True,
                 decisions=sum(r['decisions'] for r in rows),host_sha256=sha256(DLL),parent_sha256=before,
                 step_time_speedup=sum(r['slow_step_seconds'] for r in rows)/sum(r['fast_step_seconds'] for r in rows),
                 limits='Native environment-step timing under concurrent training, excludes policy inference/optimizer. Optional flag remains off in both production studies.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)


if __name__=='__main__':main()
