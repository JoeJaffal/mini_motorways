"""Protocol checks; build simulation/Headless in Debug before running."""
import argparse,json,subprocess,pathlib
parser=argparse.ArgumentParser();parser.add_argument('--dotnet',default='dotnet');args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];dotnet=args.dotnet
host=root/'simulation/Headless/bin/Debug/net8.0/TrafficHost.dll'
process=subprocess.Popen([dotnet,str(host)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
def call(**req):
 process.stdin.write(json.dumps(req)+'\n');process.stdin.flush()
 answer=json.loads(process.stdout.readline());assert 'error' not in answer,(req,answer)
 return answer
summaries=[]
for version in ['OriginalReference','Custom']:
 for name in ['LosAngeles','Beijing','Tokyo','DarEsSalaam','London']:
  a=call(command='reset',version=version,scenario=name,seed=42)
  o=a['observation'];assert o['scenario']==name and o['version']==version and o['exactReplicaValidated'] is False
  assert len(o['buildings'])>=2
  if version=='OriginalReference' and name=='London':
   assert len(o['trains'])==1 and len(o['railLines'])==1 and len(o['railLines'][0]['cells'])==53
   assert any(b['isStation'] and len(b['entrances'])==2 and len(b['platform'])==4 for b in o['buildings'])
  else:assert not o['trains'] and not o['railLines']
  call(command='reference');a=call(command='step',ticks=400);o=a['observation']
  assert o['motorways']==[]
  assert a['terminated'] is False
  summaries.append(dict(version=version,map=name,seconds=o['time'],trips=o['tripsCompleted'],buildings=len(o['buildings']),failed=o['failed'],rejected=o['scenarioRejected']))
  if version=='Custom':assert call(command='motorway',x=5,y=5,toX=20,toY=10)['accepted'] is False
call(command='reset',version='OriginalReference',scenario='EmptyLab',seed=42)
call(command='step',ticks=2800)
o=call(command='observe')['observation'];assert o['upgradeChoices']
process.stdin.write(json.dumps(dict(command='reset',requireExact=True))+'\n');process.stdin.flush()
assert 'error' in json.loads(process.stdout.readline())
process.stdin.write('{"command":"quit"}\n');process.stdin.flush();process.wait(timeout=10)
(root/'simulation/Reports/five-map-protocol-checks.json').write_text(json.dumps(dict(result='PASS',checks='Both versions reset all five maps, complete 20-second debug-road smoke runs, expose fidelity=false, reject Custom motorways, expose weekly Original choices, and refuse requireExact resets.',runs=summaries),indent=2))
print('PASS: five-map protocol checks (10 runs).')
