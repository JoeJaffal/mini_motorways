from pathlib import Path
import subprocess,sys,json,os
root=Path.cwd();out=root/'output/training'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
for split,warmup in [('train',0),('validation',0),('validation',6)]:
 name=f'city-strategy-reserve-diagnostic-{split}-{warmup}-01'
 cmd=[sys.executable,'-u','training/evaluate_city_curriculum.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints','output/training/city-strategy-balanced-extension-01/segment-001/midpoint.zip','--output',str(out/name),'--lessons','midgame-network-reserve','--count','16','--seed-start','152010000','--workers','4','--controls','--split',split,'--reserve-warmup-seconds',str(warmup)]
 with (out/(name+'.log')).open('x') as f:subprocess.run(cmd,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
