from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time,sys,subprocess,json
from run_city_strategy_long import run_child
root=Path.cwd();r=root/'docs/training/city-road-choice-2026-11-24';checkpoint=root/'output/training/city-road-choice-fit-02/roads/final.zip';status=root/'output/training/city-road-choice-fit-02/status.json'
start=time.monotonic()
while not (checkpoint.parent/'complete.json').exists():
 if time.monotonic()-start>1800:raise TimeoutError('Training completion not observed')
 if status.exists() and json.loads(status.read_text()).get('status')=='error':raise RuntimeError('Training launcher failed')
 time.sleep(5)
def run(job):
 name,args=job
 wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
 run_child([sys.executable,'-c',wrapper,str(r/f'{name}.log'),sys.executable,'-u',*map(str,args)],cwd=root,timeout=1200)
jobs=[('audit',[r/'audit.py'])]
for name,seed,action_seed in [('watched-failed-opening',184000000,193251),('watched-scoring-opening',184000003,193254)]:
 jobs.append((name,[r/'watch.py','--checkpoint',checkpoint,'--seed',seed,'--action-seed',action_seed,'--output',r/name]))
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,jobs))
(r/'postcheck-complete.json').write_text(json.dumps(dict(complete=True,seconds=time.monotonic()-start))+'\n')
