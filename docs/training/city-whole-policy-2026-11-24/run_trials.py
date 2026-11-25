from pathlib import Path
import json,os,sys,shutil,subprocess,datetime
from concurrent.futures import ThreadPoolExecutor
from run_city_strategy_long import run_child
root=Path.cwd();rec=root/'docs/training/city-whole-policy-2026-11-24';out=root/'output/training/city-whole-fit-01';out.mkdir(exist_ok=False)
runtime=out/'runtime';source=runtime/'training';source.mkdir(parents=True)
for p in (root/'training').glob('*.py'):shutil.copy2(p,source/p.name)
shutil.copytree(source,rec/'runtime-source')
host=runtime/'host';shutil.copytree(root/'output/city-bridge-connection-build-01/bin/TrafficHost/release',host)
status=dict(status='running',pid=os.getpid(),phase='preparing',started=datetime.datetime.now().astimezone().isoformat())
def publish():
 for p in (out/'status.json',rec/'status.json'):p.write_text(json.dumps(status,indent=2)+'\n')
try:
 for arm,parent in [('gated','city-strategy-wide-initial-01'),('whole','city-whole-initial-01')]:
  status.update(phase='training',arm=arm);publish()
  cmd=[sys.executable,'-u',str(source/'train_city_curriculum.py'),'--dll',str(host/'TrafficHost.dll'),'--parent',str(root/f'output/training/{parent}/start.zip'),'--output',str(out/arm),'--record-dir',str(rec/'runs'/arm),'--stage','city','--repeat-city-count','8','--workers','16','--seed-start','184000000','--rollouts','4','--rollout-steps','512','--batch-size','128','--gae-lambda','1','--horizon','600','--learning-rate','.0001','--value-coefficient','.00001','--gradient-audit-steps','64','--allow-bridges','--collapse-forced-wait','--save-every-rollouts','1']
  (rec/f'{arm}-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
  # Own child group cleanup, with log redirection through a short Python wrapper.
  wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
  run_child([sys.executable,'-c',wrapper,str(out/f'{arm}.log'),*cmd],cwd=root,timeout=3600)
 status.update(phase='evaluation',arm='both');publish()
 def evaluate(arm):
  cmd=[sys.executable,'-u',str(rec/'evaluate.py'),'--checkpoint',str(out/arm/'final.zip'),'--output',str(root/f'output/training/city-whole-{arm}-eval-01'),'--baseline',str(root/'output/training/city-whole-baseline-01')]
  wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
  run_child([sys.executable,'-c',wrapper,str(out/f'{arm}-evaluation.log'),*cmd],cwd=root,timeout=3600)
 with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(evaluate,('gated','whole')))
 status.update(status='complete',phase='finished');publish()
except BaseException as e:
 status.update(status='error',error=repr(e));publish();raise
