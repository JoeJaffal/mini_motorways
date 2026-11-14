import numpy as np, json, glob, os
ev=json.load(open('roads_raw.json'));houses=json.load(open('houses_dom.json'))
N=1198;bad=set(json.load(open('bad_frames.json')))
D=[(1,0),(0,1),(1,1),(-1,1)]
LOTS={(10,9):(3,2),(11,12):(3,2),(15,12):(3,2),(12,15):(3,2),(16,17):(3,2),(28,9):(4,3),(27,15):(3,2),(27,18):(3,2),(38,15):(2,3)}
blocked=set()
for (x,y),(w,h) in LOTS.items():
    for dx in range(w):
        for dy in range(h):blocked.add((x+dx,y+dy))
hcells={(h['x'],h['y']) for h in houses};blocked|=hcells
# terminal cells: tiles next to a house or lot (driveways / entrances end there)
import collections
DIRS={0:(1,0),1:(1,1),2:(0,1),3:(-1,1),4:(-1,0),5:(-1,-1),6:(0,-1),7:(1,-1)}
term=set()
for h in houses:
    cs=[d for t,d in h['conn'] if d is not None]
    for d in set(cs):term.add((h['x']+DIRS[d][0],h['y']+DIRS[d][1]))
for c in [(12,17),(16,16),(15,14),(11,14),(27,17),(27,20),(27,11),(32,11),(10,11),(40,17)]:term.add(c)
RD2=np.array([np.load(f'feat/rd2_{i:04d}.npy').astype(np.float32) for i in range(N)])
VS=np.array([np.load(f'feat/{i:04d}.npz')['vis'] for i in range(N)])
for b in bad:VS[b]=False
strong={}
for e in ev:strong.setdefault((e['x'],e['y'],e['toX'],e['toY']),[]).append((e['t'],e['kind']=='draw'))
def on_at(link,t):
    st=False
    for tt,s in strong.get(link,[]):
        if tt<=t:st=s
    return st
def degree(c,t,extra):
    d=0
    for (x,y,x2,y2) in list(strong)+extra:
        if (x,y)==c or (x2,y2)==c:
            if on_at((x,y,x2,y2),t) or (x,y,x2,y2) in extra:d+=1
    return d
added=[];extra=[]
for y in range(30):
    for x in range(50):
        for k,(dx,dy) in enumerate(D):
            x2,y2=x+dx,y+dy
            if not(0<=x2<50 and 0<=y2<30) or (x,y) in blocked or (x2,y2) in blocked or (x,y,x2,y2) in strong:continue
            v=VS[:,y,x]&VS[:,y2,x2];idx=np.where(v)[0]
            if len(idx)<10:continue
            vals=RD2[idx,y,x,k];sm=np.array([np.median(vals[max(0,j-4):j+5]) for j in range(len(idx))])
            run=0
            for j,t in enumerate(idx):
                run=run+1 if sm[j]>=0.3 else 0
                if run>=8:
                    t0=int(idx[j-7]);break
            else:continue
            # check against the network at the end of the weak run and 60 s later
            for t in (t0,min(N-1,t0+60)):
                d1=degree((x,y),t,extra);d2=degree((x2,y2),t,extra)
                dead1=d1==1 and (x,y) not in term;dead2=d2==1 and (x2,y2) not in term
                if d1>=1 and d2>=1 and (dead1 or dead2):
                    added.append(dict(kind='draw',x=x,y=y,toX=x2,toY=y2,t=t,video=t+0.5,weak=True));extra.append((x,y,x2,y2));break
print(len(added),[(a['x'],a['y'],a['toX'],a['toY'],a['t']) for a in added])
W=[(139.25,0.9),(285.5,-3.35),(425.75,-5.79),(570.0,-8.51),(713.0,-12.86),(863.25,-18.66),(1003.25,-23.35),(1145.5,-25.35),(1e9,-28.11)]
def game(v):
    for end,c in W:
        if v<=end+2:return round(v+c,2)
for a in added:a['game']=game(a['video'])
allev=sorted(ev+added,key=lambda e:(e['t'],e['kind']!='erase'))
json.dump(allev,open('roads_fixed.json','w'),indent=0)
