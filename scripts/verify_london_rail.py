"""Compare numeric London rail ordering with a read-only installed-assembly oracle.

Run after building the headless host and producing ReferenceProbe --rail output.
The fixture is numeric terrain only; no game code or assemblies are copied.
"""
import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser()
p.add_argument('--dotnet',default='dotnet')
p.add_argument('--oracle',required=True)
a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
oracle=json.loads(pathlib.Path(a.oracle).read_text(encoding='utf-8-sig'))
request=json.dumps(dict(command='reset',version='OriginalReference',scenario='London',seed=42))+'\n'+json.dumps(dict(command='quit'))+'\n'
run=subprocess.run([a.dotnet,str(root/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll')],input=request,text=True,capture_output=True,check=True)
observation=json.loads(run.stdout.splitlines()[0])['observation']
assert len(oracle['lines'])==len(observation['railLines'])==1
for original,replica in zip(oracle['lines'],observation['railLines']):
 expected=[dict(x=c['x']+25,y=14-c['y']) for c in original['cells']]
 actual=[dict(x=c['x'],y=c['y']) for c in replica['cells']]
 assert original['valid'] and original['loop']==replica['loop'] and expected==actual
 spawn=next(i for i,c in enumerate(original['cells']) if c['origin'])
 assert spawn==14
report=dict(result='PASS',scope='53 ordered London rail tiles, loop flag and origin index 14 match installed topology component. Does not validate train motion, station placement or whole-game parity.',assemblySha256=oracle['assemblySha256'],lines=oracle['lines'])
(root/'simulation/Reports/reference-london-rail.json').write_text(json.dumps(report,indent=2))
print('PASS: London rail topology matches installed component (53 tiles, loop, origin).')
