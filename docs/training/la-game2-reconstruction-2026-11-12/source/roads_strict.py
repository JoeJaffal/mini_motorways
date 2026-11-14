import numpy as np, glob, json, os
fs=sorted(glob.glob('feat/[0-9]*.npz'));N=max(int(os.path.basename(f)[:4]) for f in fs)+1
RD=np.zeros((N,30,50,4),np.float32);LD=np.zeros((N,30,50,4),np.float32);VS=np.zeros((N,30,50),bool);CF=np.zeros((N,30,50,5),np.float32)
for f in fs:
    i=int(os.path.basename(f)[:4]);z=np.load(f);RD[i]=np.load(f'feat/rd3_{i:04d}.npy');LD[i]=np.load(f'feat/ld3_{i:04d}.npy');VS[i]=z['vis'];CF[i]=z['cf']
for _b in json.load(open('bad_frames.json')):
    VS[_b]=False
houses=json.load(open('houses_raw.json'))
LOTS={(10,9):(3,2),(11,12):(3,2),(15,12):(3,2),(12,15):(3,2),(16,17):(3,2),(28,9):(4,3),(27,15):(3,2),(27,18):(3,2),(38,15):(2,3)}
blocked=np.zeros((30,50),bool)
for (x,y),(w,h) in LOTS.items():blocked[y:y+h,x:x+w]=True
for h in houses:blocked[h['y'],h['x']]=True
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
def game(v):
    for end,c in W:
        if v<=end+2:return v+c
D=[(1,0),(0,1),(1,1),(-1,1)]
RD2=np.zeros_like(RD)
for i in range(N):RD2[i]=np.load(f'feat/rd2_{i:04d}.npy')
def sh(a,dx,dy):
    # value at (x+dx,y+dy) placed at (x,y); zero outside
    out=np.zeros_like(a);H,W=a.shape[-2:]
    ys=slice(max(0,-dy),H-max(0,dy));xs=slice(max(0,-dx),W-max(0,dx))
    yd=slice(max(0,dy),H-max(0,-dy)+0 if dy<=0 else H);xd=slice(max(0,dx),W if dx>=0 else W+dx)
    out[...,ys,xs]=a[...,max(0,dy):H+min(0,dy),max(0,dx):W+min(0,dx)]
    return out
S3=RD[...,2];W3=RD[...,3];strongd=0.6
# diagonals touching an E link at (x,y): SE(x,y), SW(x+1,y), SW(x+1,y-1), SE(x,y-1)
diagE=np.maximum.reduce([S3,sh(W3,1,0),sh(W3,1,-1),sh(S3,0,-1)])
# diagonals touching an S link at (x,y): SE(x,y), SW(x,y), SW(x+1,y), SE(x-1,y)
diagS=np.maximum.reduce([S3,W3,sh(W3,1,0),sh(S3,-1,0)])
C=np.zeros_like(RD)
for k,dg in ((0,diagE),(1,diagS)):
    C[...,k]=np.where(RD[...,k]>=0.6,RD[...,k],np.where((RD2[...,k]>=0.6)&(dg<strongd),RD2[...,k]*0.99,0))
# crossing diagonals at the same corner: SE(x,y) vs SW(x+1,y)
se=np.maximum(RD[...,2],0.99*RD2[...,2]*(RD2[...,2]>=0.6));sw=np.maximum(RD[...,3],0.99*RD2[...,3]*(RD2[...,3]>=0.6))
swn=sh(sw,1,0);sen=sh(se,-1,0)
C[...,2]=np.where(se>=swn,se,0)
C[...,3]=np.where(sw>sen,sw,0)
RD=C
# frames where the whole picture changes (upgrade screen, drawing overlay): road coverage collapses together
ref=(np.nanmean(np.where(VS[-60:,...,None],RD[-60:],np.nan),axis=0)>0.6)
cov=np.array([RD[t][ref&VS[t][...,None]].mean() if (ref&VS[t][...,None]).sum()>20 else np.nan for t in range(N)])
med=np.array([np.nanmedian(cov[max(0,t-15):t+16]) for t in range(N)])
bad=~(cov>=0.8*med)
bad|=np.isnan(cov)&False
VS=VS&~bad[:,None,None]
print('bad frames',int(bad.sum()),[t for t in range(N) if bad[t]][:80])
ON,OFF,HOLD=0.6,0.3,6
events=[];final={}
for y in range(30):
    for x in range(50):
        for k,(dx,dy) in enumerate(D):
            x2,y2=x+dx,y+dy
            if not(0<=x2<50 and 0<=y2<30) or blocked[y,x] or blocked[y2,x2]:continue
            p0=RD[:,y,x,k];l0=LD[:,y,x,k];v=VS[:,y,x]&VS[:,y2,x2]
            idx=np.where(v)[0];p=np.zeros(N,np.float32);l=np.zeros(N,np.float32)
            if len(idx):
                vals=p0[idx];sm=np.array([np.median(vals[max(0,j-4):j+5]) for j in range(len(idx))]);p[idx]=sm
                lv=l0[idx];l[idx]=np.array([np.median(lv[max(0,j-4):j+5]) for j in range(len(idx))])
            state=False;run=0;cand=None
            for t in range(N):
                if not v[t]:continue
                on=ON if k<2 else 0.8
                want=p[t]>on if not state else not(l[t]>0.6)
                if want!=state:
                    if cand is None:cand=t
                    run+=1
                    need=HOLD if want else (15 if cand<1130 else 10**9)
                    if run>=need:
                        state=want;events.append(dict(kind='draw' if state else 'erase',x=x,y=y,toX=x2,toY=y2,t=cand,video=cand+0.5,game=round(game(cand+0.5),2)))
                        run=0;cand=None
                else:run=0;cand=None
            final[(x,y,k)]=state
events.sort(key=lambda e:(e['t'],e['kind']!='erase'))
json.dump(events,open('roads_raw.json','w'),indent=0)
import collections
print(len(events),collections.Counter(e['kind'] for e in events))
print('diagonal draws',sum(1 for e in events if e['kind']=='draw' and e['x']!=e['toX'] and e['y']!=e['toY']))
print('final links',sum(final.values()))
