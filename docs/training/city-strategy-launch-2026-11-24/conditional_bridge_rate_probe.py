"""Predeclared bounded rate comparison; never starts an overnight run."""
from pathlib import Path
import subprocess,sys,os,json,time,datetime
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
def wait(p):
 for _ in range(720):
  if p.exists():return
  time.sleep(10)
 raise TimeoutError(str(p))
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
comparison=rec/'bridge-reference-final-longer-comparison.json';wait(comparison)
if json.loads(comparison.read_text())['strong_gain_pass']:
 (rec/'bridge-reference-rate-skip.json').write_text(json.dumps(dict(reason='Low-rate final passes development gain gate; do not launch rate probe'))+'\n');sys.exit(0)
for _ in range(720):
 s=json.loads((out/'city-strategy-bridge-reference-city-01/status.json').read_text())
 if s['status'] in ('complete','regression_stop'):break
 if s['status'] in ('interrupted','failed'):raise RuntimeError(s)
 time.sleep(10)
else:raise TimeoutError('Original trainer still active')
name='city-strategy-bridge-reference-rate-01';target=out/name
cmd=['training/run_city_strategy_long.py','--start','output/training/city-strategy-wide-initial-01/start.zip','--dll','output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll','--output',str(target),'--record-dir',str(rec/'bounded-bridge-reference-rate-01'),'--hours','.0001','--stage','city','--seed-start','168000000','--workers','16','--segment-rollouts','4','--review-every','1','--review-games','2','--horizon','1200','--learning-rate','.001','--value-coefficient','.00001','--gradient-audit-steps','64','--allow-bridges']
with (out/(name+'.log')).open('x') as f:p=subprocess.Popen([sys.executable,'-u',*cmd],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(rec/'bridge-reference-rate-launch.json').write_text(json.dumps(dict(pid=p.pid,command=[sys.executable,'-u',*cmd],time=datetime.datetime.now().astimezone().isoformat(),decision_budget=32768,condition=str(comparison)),indent=2)+'\n')
with (root/'training/EXPERIMENT_HISTORY.md').open('a') as f:f.write('\nConditional bridge-reference-rate-01 launched after low-rate final failed the predeclared development gain gate.32,768 city-only decisions,LR.001,otherwise same starting policy/168M seeds/1200s bridge environment and optimizer coefficient. Bounded comparison only; launch record and matched reviews in strategy archive.\n')
for label in ('midpoint','final'):
 candidate=target/f'segment-001/{label}.zip';wait(candidate)
 review=f'city-strategy-bridge-rate-{label}-longer-01'
 run(review,['training/evaluate_city_service.py','--dll','output/city-bridge-connection-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',str(candidate),'--output',str(out/review),'--games','32','--seed','950241','--workers','8','--horizon','1200','--allow-bridges'])
 run(review+'-comparison',[str(rec/'compare.py'),'--parent',str(out/'city-strategy-bridge-longer-baseline-01'),'--candidate',str(out/review),'--output',str(rec/f'bridge-rate-{label}-longer-comparison.json')])
 run(review+'-audit',[str(rec/'audit.py'),'--parent','output/training/city-strategy-wide-initial-01/start.zip','--candidate',str(candidate),'--output',str(rec/f'bridge-rate-{label}-audit.json')])
(rec/'bridge-reference-rate-reviews-complete.json').write_text(json.dumps(dict(status='complete'))+'\n')
