import sys,pathlib,json
sys.path.insert(0,str(pathlib.Path('training').resolve()));from environment import TrafficEnv
r=pathlib.Path('docs/training/event-parity-2026-11-08');old=json.loads(pathlib.Path('docs/training/gameplay-fidelity-repairs-2026-11-08/reward-fixture-v2.json').read_text());env=TrafficEnv(dotnet=str(pathlib.Path('tmp/dotnet/dotnet.exe').resolve()),seeds=[old['seed']],record_replays=True,seconds=300)
try:
 env.reset(seed=42)
 for event in old['actions']:
  if event['command']=='wait':break
  env._advance({k:v for k,v in event.items() if k in ['command','tool','x','y','toX','toY','id','choice']})
 while not env.done:env._advance(None)
 rec=env.export_replay();assert rec['terminated'] and not rec['truncated']
 rec['source']='Ordinary-command reward correctness fixture after movement factor3 and weighted lookahead; same initial commands as historical v2; wait to actual terminal within300s. No learning or policy performance.'
 (r/'reward-fixture-v4.json').write_text(json.dumps(rec,indent=2),encoding='utf-8');print(rec['score'],rec['duration'],len(rec['actions']))
finally:env.close()
