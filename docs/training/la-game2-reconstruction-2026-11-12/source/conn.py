import json
hs=json.load(open('houses_dom.json'));ev=json.load(open('roads_fixed.json'))
DIRS={0:(1,0),1:(1,1),2:(0,1),3:(-1,1),4:(-1,0),5:(-1,-1),6:(0,-1),7:(1,-1)}
def roadcells(t):
    st={}
    for e in ev:
        if e['t']<=t:st[(e['x'],e['y'],e['toX'],e['toY'])]=e['kind']=='draw'
    c=set()
    for (x,y,x2,y2),on in st.items():
        if on:c.add((x,y));c.add((x2,y2))
    return c
cache={}
for h in hs:
    seq=[]
    for (t,sc) in h['series'][::5]:
        if t not in cache:cache[t]=roadcells(t)
        rc=cache[t];cand=[d for d in DIRS if (h['x']+DIRS[d][0],h['y']+DIRS[d][1]) in rc]
        # prefer straight directions on ties
        d=max(cand,key=lambda d:(sc[d],d%2==0)) if cand else None
        seq.append((t,d))
    h['conn']=seq
json.dump(hs,open('houses_dom.json','w'))
import collections
for h in hs:
    cs=[d for t,d in h['conn'] if d is not None];print(h['x'],h['y'],collections.Counter(cs).most_common(3))
