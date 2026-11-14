import numpy as np,csv,sys,os
# usage: [DELAYED='[[colour,scheduledAt,appears],...]'] [DESTS=<DUMP_DESTS output>] [SCORE=<score timeline csv>] py -3 fit_phases.py <fit-until-s> <seed>
# DELAYED lists late scheduled destinations; their colour gets the original's failed-spawn extra demand while they wait.
BASE=[0.9,1.3,0.85,0.85,0.7];BURST=[1.3,0.5,1.9,1.75,1.3];ECC=[2,3,6,9,1];PER=[7,13,12,9,23]
dests=[]
for l in open(os.environ.get('DESTS','tmp/runs/dests.txt')):
    if l.startswith('D '):
        p=l.split();dests.append((int(p[2]),float(p[3]),{14:1030.7,34:1105.8,22:1252.0}.get(int(p[1]),1e9)))
real=[(float(r['game_s']),int(r['score'])) for r in csv.DictReader(open(os.environ.get('SCORE','tmp/video/score_timeline.csv')))]
TMAX=float(sys.argv[1]) if len(sys.argv)>1 else 1200
rt=np.array([g for g,s in real if g<=TMAX]);rs=np.array([s for g,s in real if g<=TMAX])
T=np.arange(0,1320,1.0)
ramp=1+np.maximum(0,np.floor(T/20)-35)*0.013
def osc(c,ph):
    d=T/20+ph;w=np.abs(np.sin((d%PER[c])*np.pi/PER[c]))**(2+ECC[c]);return BASE[c]+w*(BURST[c]-BASE[c])
# Late scheduled destinations (colour, scheduledAt, appears): original BalanceDemandFromFailedSpawns
import json
DELAYED=json.loads(os.environ.get('DELAYED','[]'))
extra=np.zeros((5,len(T)))
for ti,t in enumerate(T):
    act={}
    for c,s0,m in dests:
        if s0<=t: act[c]=act.get(c,0)+0.8*(2 if t>=m else 1)
    tot=sum(act.values())
    for c,a,b in DELAYED:
        if not(a<=t<b): continue
        v=1.0
        if c in act:
            x=min(act[c],v);extra[c,ti]+=x/act[c];v-=x
        if v>0 and tot>0:
            for k in act:
                if k!=c: extra[k,ti]+=v/tot
def pins(phases):
    tot=np.zeros_like(T)
    for c,s,m in dests:
        rate=ramp*1.55*0.8*np.where(T>=m,2.0,1.0)*osc(c,phases[c])*(1+extra[c])/20
        cum=np.cumsum(rate)  # pins/s integrated at 1 s
        first=s+4;i0=int(np.ceil(first))
        arr=np.where(T>=first,1+cum-cum[min(i0,len(T)-1)],0)
        tot+=np.floor(arr)
    return tot
def loss(phases,lag):
    p=pins(phases);model=np.interp(rt-lag,T,p);return np.mean((model-rs)**2)
rng=np.random.default_rng(int(sys.argv[2]) if len(sys.argv)>2 else 0);best=(1e18,None,None)
for it in range(4000):
    ph=[rng.random()*P for P in PER];lag=rng.random()*25
    l=loss(ph,lag)
    if l<best[0]:best=(l,ph,lag)
l,ph,lag=best;step=[P/8 for P in PER]+[3]
for rnd in range(60):
    improved=False
    for k in range(6):
        for sgn in (1,-1):
            ph2=list(ph);lag2=lag
            if k<5: ph2[k]=(ph2[k]+sgn*step[k])%PER[k]
            else: lag2=max(0,lag+sgn*step[5])
            l2=loss(ph2,lag2)
            if l2<l:l,ph,lag,improved=l2,ph2,lag2,True
    if not improved: step=[s/2 for s in step]
print('rmse',round(l**.5,2),'lag',round(lag,2),'phases',' '.join(f'{x:.3f}' for x in ph))
# phase-averaged expected and spread
samp=[pins([rng.random()*P for P in PER])[1314] for _ in range(300)]
print('expected pins @1314: mean',np.mean(samp).round(1),'p10',np.percentile(samp,10),'p90',np.percentile(samp,90),'fitted',pins(ph)[1314])
for t in (300,500,700,900,1100,1200,1300): print(t,'fit pins',pins(ph)[t])
