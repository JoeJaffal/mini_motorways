from pathlib import Path
import subprocess,sys,os,json
root=Path.cwd();out=root/'output/training';rec=root/'docs/training/city-strategy-launch-2026-11-24'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONPATH=str(root/'training'))
def run(name,cmd):
 with (out/(name+'.log')).open('x') as f:subprocess.run([sys.executable,'-u',*cmd],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for label in ('midpoint','final'):
 if label=='final':subprocess.run([sys.executable,'-u',str(rec/'review_original_delay_final.py')],cwd=root,env=env,check=True)
 name='city-strategy-original-delay-'+label+'-broader-development-01'
 run(name,['training/evaluate_city_service.py','--dll','output/city-road-reserve-build-01/bin/TrafficHost/release/TrafficHost.dll','--checkpoints',str(out/f'city-strategy-original-delay-01/segment-001/{label}.zip'),'--output',str(out/name),'--games','64','--seed','950242','--workers','8'])
 run(name+'-comparison',[str(rec/'compare.py'),'--parent',str(out/'city-strategy-confirmation-02'),'--candidate',str(out/name),'--output',str(rec/f'original-delay-{label}-broader-comparison-01.json')])
(rec/'original-delay-broader-reviews-complete.json').write_text(json.dumps(dict(status='complete',note='Reused950242 cohort; not independent confirmation'))+'\n')
