import numpy as np, json
from PIL import Image
T=32
hs=json.load(open('houses_raw.json'))
DIRS={0:(1,0),1:(1,1),2:(0,1),3:(-1,1),4:(-1,0),5:(-1,-1),6:(0,-1),7:(1,-1)}
def roadmask(a):
    R,G,B=a[...,0],a[...,1],a[...,2]
    return (np.minimum(np.minimum(R,G),B)>238)&(np.abs(B-R)<10)&(np.abs(G-R)<10)
# sample point offsets per direction (in tile units, relative to house centre)
OFF={}
for d,(dx,dy) in DIRS.items():
    n=(dx*dx+dy*dy)**.5;ux,uy=dx/n,dy/n;lo,hi=(0.45,0.95) if n==1 else (0.6,1.3)
    OFF[d]=[(ux*r-uy*o/T,uy*r+ux*o/T) for r in np.linspace(lo,hi,8) for o in (-2,0,2)]
frames=list(range(0,1198,2))
cache={}
def mask(i):
    if i not in cache:cache[i]=roadmask(np.asarray(Image.open(f'boards/{i:04d}.png').convert('RGB'),float))
    return cache[i]
series={}
for i in frames:
    m=mask(i)
    for h in hs:
        if i<h['t']:continue
        sc=[]
        for d in range(8):
            v=[m[int((h['y']+0.5+oy)*T),int((h['x']+0.5+ox)*T)] for ox,oy in OFF[d]]
            sc.append(np.mean(v))
        series.setdefault((h['x'],h['y']),[]).append((i,sc))
    cache.clear()
out=[]
for h in hs:
    s=series[(h['x'],h['y'])];t=np.array([a for a,_ in s]);S=np.array([b for _,b in s])
    # windows of 10 frames (20 s)
    dom=[]
    for k in range(0,len(t),5):
        w=S[k:k+10].mean(0);d=int(w.argmax());dom.append((int(t[k]),d,round(float(w[d]),2),round(float(np.sort(w)[-2]),2)))
    h['dominant']=dom;h['series']=[(int(a),[round(float(x),2) for x in b]) for a,b in zip(t,S)];out.append(h)
    print(h['x'],h['y'],h['name'],h['video'],' '.join(f'{a}:{d}({sc})' for a,d,sc,_ in dom[:6]),'...',' '.join(f'{a}:{d}({sc})' for a,d,sc,_ in dom[-2:]))
json.dump(out,open('houses_dom.json','w'))
