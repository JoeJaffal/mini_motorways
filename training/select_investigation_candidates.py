"""Freeze development-only selection before fresh-map final evaluation."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def candidate(path,score,origin,steps):
    return dict(checkpoint=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                mean_trips=score,development_evidence=origin,policy_steps=steps)


def trained(name,goal):
    folder=ROOT/'output/training'/name;s=json.loads((folder/'summary.json').read_text())
    options=[]
    v=folder/'validation.jsonl'
    if v.exists():
        records=[json.loads(l) for l in v.read_text().splitlines()]
        best=max(records,key=lambda r:r['mean_trips'])
        options.append(candidate(folder/'validation-best.zip',best['mean_trips'],f'{name}/validation.jsonl',best['policy_steps']))
    results=s['after'] if goal else s['deterministic_after']
    options.append(candidate(folder/'final.zip',sum(x['trips'] for x in results)/len(results),f'{name}/summary.json final deterministic',s['policy_steps']))
    return max(options,key=lambda r:r['mean_trips'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--goal-run',action='append',required=True);a=p.parse_args()
    if a.output.exists():p.error('Selection record already exists; never overwrite after testing')
    primitive=trained('informed-credit-20261028',False)
    first=ROOT/'output/training'/a.goal_run[0]
    before=json.loads((first/'before.json').read_text());score=sum(x['trips'] for x in before)/len(before)
    initial=candidate(first/'initial.zip',score,f'{a.goal_run[0]}/before.json deterministic',0)
    arms=[trained(n,True) for n in a.goal_run];best_trained=max(arms,key=lambda r:r['mean_trips'])
    # Every arm starts from the same policy weights. Match its action-duration
    # mode too, so the frozen final-test baseline is not a timing ablation.
    matched=ROOT/Path(best_trained['checkpoint']).parent
    matched_before=json.loads((matched/'before.json').read_text())
    initial=candidate(matched/'initial.zip',sum(x['trips'] for x in matched_before)/len(matched_before),
                      f'{matched.name}/before.json deterministic; timing matched to trained candidate',0)
    operational=max([initial]+arms,key=lambda r:r['mean_trips'])
    record=dict(created_utc=datetime.now(timezone.utc).isoformat(),protocol='Development seeds 2000-2004 only; first listed candidate wins exact ties. Include frozen initial for operational selection. No later updates or selection use final seeds 3000-3009.',
                primitive=primitive,goal_initial=initial,goal_trained=best_trained,goal=operational,goal_candidates=arms,
                test_seeds=list(range(3000,3010)),final_test_cap=3600,
                note='Frozen goal initial uses the same decision timing as the selected trained candidate. Primitive candidate development mean 13.0 exceeds frozen informed mean 12.6 by only 0.4; this difference is not robust evidence.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
