"""Archive small signal-pilot evidence and compare tensors; never trains."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import torch
from sb3_contrib import MaskablePPO
from environment import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Fresh archive folder required')
    a.output.mkdir(parents=True);torch.set_num_threads(2)
    manifest=[]
    def preserve(source,target):
        source=ROOT/source;target=a.output/target;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Archive copy mismatch')
        manifest.append(dict(source=str(source.relative_to(ROOT)),archived=str(target.relative_to(a.output)),sha256=digest))
    report=dict(date='2026-10-29',protocol='Two 512-decision pilots; same initial tensors/seed, only prior temperature differs; development maps only; no tuning after results',arms={})
    initial_states={}
    for label,run in [('control','signals-control-20261029'),('soft-prior','signals-soft-prior-20261029')]:
        root=ROOT/'output/training'/run
        models={n:MaskablePPO.load(root/f'{n}.zip',device='cpu') for n in ['initial','final','validation-best']}
        states={n:dict(m.policy.named_parameters()) for n,m in models.items()}
        initial_states[label]={n:v.detach().clone() for n,v in states['initial'].items()}
        delta={prefix:float(torch.sqrt(sum(((states['final'][n].detach()-v.detach())**2).sum() for n,v in states['initial'].items() if n.startswith(prefix))))
               for prefix in ['features_extractor.prior','features_extractor.route_context','features_extractor.signal_row','features_extractor.signal_prior','features_extractor.traffic_encoder']}
        summary=json.loads((root/'summary.json').read_text())
        report['arms'][label]=dict(run=run,prior_temperature=models['initial'].policy.features_extractor.prior_temperature,
            before=[x['trips'] for x in summary['before']],after=[x['trips'] for x in summary['after']],
            before_mean=summary['initial_validation_mean'],after_mean=sum(x['trips'] for x in summary['after'])/len(summary['after']),
            policy_steps=summary['policy_steps'],wall_seconds=summary['training_wall_seconds'],parameter_l2_changes=delta,
            selected_initial=all(torch.equal(v,states['validation-best'][n]) for n,v in states['initial'].items()),
            checkpoint_sha256={n:hashlib.sha256((root/f'{n}.zip').read_bytes()).hexdigest() for n in models})
        for name in ['config.json','summary.json','validation-best.json','progress.csv','episodes.jsonl']:
            preserve(root/name,Path('pilots')/label/name)
        for name in ['goal_agent.py','signal_agent.py','train_goal.py','environment.py','planner_diagnostic.py','progress.py','rewards.py','parallel.py','shutdown.py']:
            preserve(root/name,Path('pilots')/label/'sources'/name)
    report['initial_tensors_equal']=all(torch.equal(v,initial_states['soft-prior'][n]) for n,v in initial_states['control'].items())
    if not report['initial_tensors_equal']:raise RuntimeError('Pilot initial tensors differed')
    if not all(x['policy_steps']==512 and x['selected_initial'] for x in report['arms'].values()):raise RuntimeError('Unexpected pilot selection/budget')
    for source,target in [
        ('output/experiments/signal-audit-v2-20261029.json','old-policy-audit.json'),
        ('output/experiments/signals-temperature-audit-20261029.json','temperature-audit.json'),
        ('output/experiments/signals-evaluator-smoke-20261029.json','evaluator-smoke.json'),
        ('output/training/signals-four-worker-smoke-20261029/summary.json','four-worker-smoke.json'),
        ('output/training/signals-resume-smoke-20261029/summary.json','resume-smoke.json'),
        ('output/training/signals-resume-smoke-20261029/config.json','resume-config.json')]:preserve(source,target)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
