from pathlib import Path
import time,sys,json
from concurrent.futures import ThreadPoolExecutor
from run_city_strategy_long import run_child
root=Path.cwd();r=root/'docs/training/small-city-service-2026-11-24';out=root/'output/training/small-city-offset-fit-01';start=time.monotonic()
def run(name,args):
 wrapper='import subprocess,sys; f=open(sys.argv[1],"x"); raise SystemExit(subprocess.call(sys.argv[2:],stdout=f,stderr=subprocess.STDOUT))'
 run_child([sys.executable,'-c',wrapper,str(r/f'{name}.log'),sys.executable,'-u',*map(str,args)],cwd=root,timeout=1200)
run('watch-parent',[r/'watch.py','--label','parent','--checkpoint',root/'output/training/city-whole-initial-01/start.zip'])
while not (out/'ppo/complete.json').exists():
 if time.monotonic()-start>1800:raise TimeoutError('Training completion not observed')
 if json.loads((out/'status.json').read_text()).get('status')=='error':raise RuntimeError('Trainer failed')
 time.sleep(5)
with ThreadPoolExecutor(max_workers=2) as pool:
 jobs=[pool.submit(run,'watch-final',[r/'watch.py','--label','final','--checkpoint',out/'ppo/final.zip']),pool.submit(run,'policy-audit',[r/'audit.py'])]
 for f in jobs:f.result()
(r/'postcheck-complete.json').write_text(json.dumps(dict(complete=True,seconds=time.monotonic()-start))+'\n')
