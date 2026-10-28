"""Summarize archived measurements for the investigation PDF; never runs a model."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    if (a.archive/'assessment.json').exists():p.error('Assessment already exists')
    runs={f.parent.name:json.loads(f.read_text()) for f in (a.archive/'runs').glob('*/summary.json')}
    selection=json.loads((a.archive/'experiments/selection.json').read_text())
    goal_names=[n for n in runs if n.startswith('goal-')]
    order=['goal-hybrid-20261028','goal-scaled-20261028','goal-choice-20261028','goal-rate-20261028']
    goal_names=[n for n in order if n in goal_names]
    labels=dict(zip(order,['Scale 1','Scale .01','Choice only','Choice + rate .001']))
    test_order=['old-baseline','informed-initial','primitive-selected','goal-initial','goal-trained']
    test_labels=dict(zip(test_order,['Old primitive PPO','Frozen informed primitive','Selected trained primitive','Frozen initial goal policy','Selected trained goal policy']))
    tests={key:json.loads((a.archive/'experiments/final-tests'/f'{key}.json').read_text()) for key in test_order}
    sampled={key:json.loads((a.archive/'experiments/final-tests'/f'{key}-sampled.json').read_text()) for key in ['goal-initial','goal-trained']}
    before=tests['goal-initial'];after=tests['goal-trained'];delta=after['mean_trips']-before['mean_trips']
    pairs=[y['trips']-x['trips'] for x,y in zip(before['results'],after['results'])]
    wins=sum(d>0 for d in pairs);losses=sum(d<0 for d in pairs);ties=sum(d==0 for d in pairs)
    best_run=max(goal_names,key=lambda n:runs[n]['best_training_score'])
    best_replay=json.loads((a.archive/'runs'/best_run/'best-game.json').read_text())
    primitive_best=max(s['best_training_score'] for n,s in runs.items() if not n.startswith('goal-'))
    goal_best=max(runs[n]['best_training_score'] for n in goal_names)
    max_score=max(primitive_best,goal_best,max(r['best_trips'] for r in tests.values()))
    headline='Stronger construction; learning gains remain unproven.'
    if delta>0:headline='Stronger construction, with a limited fresh-map learning gain.'
    conclusion=(f"The old primitive policy averaged {tests['old-baseline']['mean_trips']:.1f} trips on ten fresh maps. "
                f"The planner-aided frozen initial policy averaged {before['mean_trips']:.1f}; the selected trained goal policy averaged {after['mean_trips']:.1f}. "
                "Most of the change from the old agent comes from the new route-planning/action abstraction and informed starting policy. "
                "The initial-versus-trained comparison is the relevant check for learning; one small experiment cannot establish robust convergence.")
    goal_interpretation=(f"All four arms began with the same informed weights and a deterministic development mean of 162.6 trips. "
        f"The best trained development candidate averaged {selection['goal_trained']['mean_trips']:.1f}. "
        f"Operational selection chose {selection['goal']['checkpoint']}. "
        "The frozen initial policy was eligible for selection and wins exact ties. Actor and critic weights were verified to change; this alone is not evidence of better play. "
        "Reward scaling addressed numerical loss balance; choice-only timing removed policy calls with no alternative action; the last arm increased learning rate tenfold. "
        "These are adaptive engineering pilots, not replicated causal estimates.")
    test_interpretation=(f"Compared with its timing-matched frozen initial policy, the trained goal candidate changed the paired mean by {delta:+.1f} trips: "
        f"{wins} maps improved, {losses} worsened and {ties} tied. "
        "Checkpoints were chosen using development maps before these results were opened. No subsequent training or selection used this test set. "
        "The old-versus-goal comparison includes engineered route planning and a different action space; it is not a measure of learning alone.")
    recommendation=("Preserve both the frozen initial baseline and the development-selected checkpoint. "
        "Use the separate goal trainer for further planner-aided experiments and keep the original all-tools trainer as a baseline. "
        "Do not assume that more hours on the same seed, more parameters or a higher training best will solve transfer. "
        "A next investigation should test capacity-aware route alternatives and meaningful decision credit, using new validation/test partitions and multiple training seeds. "
        "No further run is automatically scheduled.")
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),authorization_start_utc='2026-10-28T10:40:22Z',
                authorization_deadline_utc='2026-10-28T13:40:22Z',headline=headline,conclusion=conclusion,
                primitive_best=primitive_best,goal_best=goal_best,target_status='not reached' if max_score<1000 else 'reached by at least one recorded variant; see method labels',
                goal_runs=goal_names,goal_run_labels=labels,goal_interpretation=goal_interpretation,
                test_order=test_order,test_labels=test_labels,test_interpretation=test_interpretation,recommendation=recommendation,
                best_run=best_run,best_replay=best_replay,replay_verification='Exact headless/native replay; see final-best-native.log and final-best-headless.txt',
                paired_goal_test_differences=pairs,paired_goal_mean_change=delta,paired_goal_wins=wins,paired_goal_losses=losses,paired_goal_ties=ties)
    sample_delta=sampled['goal-trained']['mean_trips']-sampled['goal-initial']['mean_trips']
    result['sampled_interpretation']=(f"The frozen initial goal policy averaged {sampled['goal-initial']['mean_trips']:.1f} trips and the selected trained policy {sampled['goal-trained']['mean_trips']:.1f}, a change of {sample_delta:+.1f}. "
        "This secondary test samples one trajectory per scenario with Torch seed 43 plus scenario offset, reset after checkpoint loading and before each game. "
        "Scenario seeds are paired, but action histories can consume random numbers differently. One sampled trajectory per map is noisy and does not estimate expected performance precisely. "
        "It was predeclared before final testing and was not used to select a checkpoint or restart training.")
    result['sampled_goal_mean_change']=sample_delta
    (a.archive/'assessment.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['headline','primitive_best','goal_best','target_status','paired_goal_mean_change','best_run']},indent=2))


if __name__=='__main__':main()
