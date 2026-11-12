import json, numpy as np
rep=json.load(open('replay-g2-draft1.json'));N=1198
bad=set(json.load(open('bad_frames.json')))
VS=np.array([np.load(f'feat/{i:04d}.npz')['vis'] for i in range(N)])
for b in bad:VS[b]=False
LD=np.array([np.load(f'feat/ld3_{i:04d}.npy').astype(np.float32) for i in range(N)])
RD=np.array([np.maximum(np.load(f'feat/rd3_{i:04d}.npy'),np.load(f'feat/rd2_{i:04d}.npy')).astype(np.float32) for i in range(N)])
K={(1,0):0,(0,1):1,(1,1):2,(-1,1):3}
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
def game(v):
    for end,c in W:
        if v<=end+2:return round(v+c,2)
def key(e):
    a,b=(e['x'],e['y']),(e['toX'],e['toY'])
    if (b[0]-a[0],b[1]-a[1]) in K:return (a[0],a[1],K[(b[0]-a[0],b[1]-a[1])])
    return (b[0],b[1],K[(a[0]-b[0],a[1]-b[1])])
# on-intervals per link from the replay
ivs={}
for e in sorted(rep['events'],key=lambda e:e.get('videoTime',e['at'])):
    if e['kind'] not in('draw','erase') or e.get('manual'):continue
    k=key(e);v=e.get('videoTime')
    if e['kind']=='draw' and k not in ivs:ivs[k]=[[v,None,e]]
    elif e['kind']=='draw' and ivs[k][-1][1] is not None:ivs[k].append([v,None,e])
    elif e['kind']=='erase' and k in ivs and ivs[k][-1][1] is None:ivs[k][-1][1]=v
added=[]
for (x,y,k),lst in ivs.items():
    for iv in lst:
        s=int(iv[0])+5;end=int(iv[1]) if iv[1] is not None else N
        idx=[t for t in range(s,min(end,N)) if VS[t,y,x]]
        run=0;start=None
        for t in idx:
            gone=LD[t,y,x,k]>0.5 and RD[t,y,x,k]<0.2
            if gone:
                run+=1;start=start if start is not None else t
                if run>=15:
                    e=iv[2];added.append(dict(at=game(start+0.5),videoTime=start+0.5,kind='erase',x=e['x'],y=e['y'],toX=e['toX'],toY=e['toY'],allowRejection=True,post=True));break
            else:run=0;start=None
rep['events']+=added
order={'offer':0,'choose':1,'shop':2,'shared':2,'join':2,'house':3,'circle':4,'erase':5,'driveway':6,'draw':7}
rep['events']=[e for e in rep['events'] if 0<e['at']<1162]
rep['events'].sort(key=lambda e:(e['at'],order[e['kind']]))
json.dump(rep,open('replay-g2-draft1.json','w'),indent=1)
print('added erases',len(added))
