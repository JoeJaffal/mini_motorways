"""Summarize the exposed seed5009 diagnosis and archive measured timelines."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Fresh archive folder required')
    a.output.mkdir(parents=True)
    d=json.loads((a.input/'diagnosis.json').read_text())
    on=json.loads((a.input/'on-trace.json').read_text());off=json.loads((a.input/'off-trace.json').read_text())
    first_only=json.loads((a.input/'omit-697-trace.json').read_text())
    timeline={}
    for name,rows in [('ON policy',[x['after'] for x in on]),('OFF policy',[x['after'] for x in off]),
                      ('First light only; fixed ON commands',first_only)]:
        timeline[name]=[dict(time=s['time'],trips=s['trips'],green=next((x for x in s['shops'] if x['id']==28),None)) for s in rows]
    horizon=len(on);fixed=[]
    for c in d['counterfactuals']:
        label='omit-'+'-'.join(map(str,c['omitted_commands']))
        replay=json.loads((a.input/f'{label}-replay.json').read_text())
        entry=replay['actions'][min(horizon,len(replay['actions']))-1]
        fixed.append(dict(omitted=c['omitted_commands'],final_score=c['score'],final_seconds=c['seconds'],rejected=c['rejected'],
            original_command_horizon_score=entry['afterTrips'],original_command_horizon_seconds=entry['afterTime'],
            failed_destination=max(c['final']['shops'],key=lambda x:x['overcrowded'])))
    queue=[v for v in d['lights'][1]['before']['waiting_cars'] if abs(v['x']-24)<2 and abs(v['y']-14)<2]
    report=dict(first_difference_index=d['first_difference_index'],first_difference_time=d['first_difference_on']['before']['time'],
        first_on_command=d['first_difference_on']['command'],first_off_command=d['first_difference_off']['command'],
        full_policy_scores=dict(on=279,off=475),fixed_ON_command_counterfactuals=fixed,
        lights=[dict(command_index=x['command_index'],time=x['before']['time'],request=x['command']) for x in d['lights']],
        on_failed_destination=max(d['on_final']['shops'],key=lambda x:x['overcrowded']),
        second_light_nearby_waiting_cars=queue,
        limits='Single exposed diagnostic. Fixed ON commands, omitted builds replaced by equal-duration waits; after recorded horizon only waits. Not a new trained policy or clean per-junction throughput experiment.')
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'timeline.json').write_text(json.dumps(timeline,indent=2)+'\n')
    verification=[];manifest=[]
    for f in sorted(a.input.glob('*-replay.json')):
        r=subprocess.run([str(ROOT/'tmp/dotnet/dotnet.exe'),str(ROOT/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'),
            '--verify-replay',str(f.resolve())],capture_output=True,text=True,timeout=120)
        if r.returncode:raise RuntimeError(r.stderr)
        verification.append(dict(file=f.name,result=json.loads(r.stdout)))
    (a.output/'replay-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    for f in [a.input/'protocol.json',a.input/'diagnosis.json',a.input/'on-light-snapshots.json',*a.input.glob('*-replay.json')]:
        shutil.copyfile(f,a.output/f.name);manifest.append(dict(source=str(f),archived=f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    for name in ['diagnose_light_failure.py','report_light_failure.py']:
        f=ROOT/'training'/name;shutil.copyfile(f,a.output/name);manifest.append(dict(source=str(f),archived=name,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(first_difference_time=report['first_difference_time'],lights=report['lights'],
        counterfactuals=fixed,verified_replays=len(verification)),indent=2))


if __name__=='__main__':main()
