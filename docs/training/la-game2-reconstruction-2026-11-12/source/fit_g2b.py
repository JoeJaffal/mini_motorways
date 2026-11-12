import numpy as np,csv,sys
BASE=[0.9,1.3,0.85,0.85,0.7];BURST=[1.3,0.5,1.9,1.75,1.3];ECC=[2,3,6,9,1];PER=[7,13,12,9,23]
dests=[(0,1.4,658.1),(1,68.9,1e9),(0,288.2,1029.65),(3,298.2,905.65),(2,328.2,1e9),(1,385.2,658.1),(2,483.5,821.3),(1,528.5,1e9),(4,788.3,1e9)]
real=[(float(r['game_s']),int(r['score'])) for r in csv.DictReader(open('tmp/video/g2/score_timeline_g2.csv'))]
TMAX=float(sys.argv[1]) if len(sys.argv)>1 else 1160
rt=np.array([g for g,s in real if g<=TMAX]);rs=np.array([s for g,s in real if g<=TMAX])
T=np.arange(0,1320,1.0)
ramp=1+np.maximum(0,np.floor(T/20)-35)*0.013
def osc(c,ph):
    d=T/20+ph;w=np.abs(np.sin((d%PER[c])*np.pi/PER[c]))**(2+ECC[c]);return BASE[c]+w*(BURST[c]-BASE[c])
# Late scheduled destinations (colour, scheduledAt, appears): original BalanceDemandFromFailedSpawns
import os,json
DELAYED=json.loads(os.environ.get('DELAYED','[[0,160,288.2],[3,230,298.2],[2,407,483.5]]'))
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
    ph=[rng.random()*P for P in PER];lag=rng.random()*45
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
samp=[pins([rng.random()*P for P in PER])[1160] for _ in range(300)]
print('expected pins @1160: mean',np.mean(samp).round(1),'p10',np.percentile(samp,10),'p90',np.percentile(samp,90),'fitted',pins(ph)[1160])
for t in (300,500,700,900,1100,1160): print(t,'fit pins',pins(ph)[t])
