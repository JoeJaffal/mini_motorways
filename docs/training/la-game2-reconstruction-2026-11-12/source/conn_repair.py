import json, heapq, collections, numpy as np
MAN=json.load(open('manual.json'))
rep=json.load(open('replay-g2-draft1.json'))
N=1198;bad=set(json.load(open('bad_frames.json')))
RD2=np.array([np.load(f'feat/rd2_{i:04d}.npy').astype(np.float32) for i in range(N)])
VS=np.array([np.load(f'feat/{i:04d}.npz')['vis'] for i in range(N)])
for b in bad:VS[b]=False
DIRS={0:(1,0),1:(1,1),2:(0,1),3:(-1,1),4:(-1,0),5:(-1,-1),6:(0,-1),7:(1,-1)}
K={(1,0):0,(0,1):1,(1,1):2,(-1,1):3}
def linkkey(a,b):
    (x,y),(x2,y2)=a,b
    if (x2-x,y2-y) in K:return (x,y,K[(x2-x,y2-y)])
    return (x2,y2,K[(x-x2,y-y2)])
def evidence(a,b,t0,t1):
    x,y,k=linkkey(a,b);v=VS[t0:t1,y,x];vals=RD2[t0:t1,y,x,k][v]
    if len(vals)<4:return 0.0
    return float(np.median(np.sort(vals)[-max(4,len(vals)//3):]))  # typical value of the better third
def build_state(vt):
    links=set();houses={};lots={};blocked=set()
    for e in sorted(rep['events'],key=lambda e:e.get('videoTime',e['at'])):
        if e.get('videoTime',e['at'])>vt:break
        k=e['kind']
        if k=='draw':links.add(frozenset([(e['x'],e['y']),(e['toX'],e['toY'])]))
        elif k=='erase':links.discard(frozenset([(e['x'],e['y']),(e['toX'],e['toY'])]))
        elif k=='house':houses[e['id']]=(e['x'],e['y'],e['color'],e['direction']);blocked.add((e['x'],e['y']))
        elif k=='driveway':h=houses[e['target']];houses[e['target']]=(h[0],h[1],h[2],e['direction'])
        elif k in('shop','shared'):
            x,y,l=e['x'],e['y'],e['layout']
            if k=='shared':w,hh=(4,3) if l<2 else (3,4);acc=[(x-1,y+2),(x+4,y+2)] if l==0 else None
            else:
                w,hh=((2,3) if l<2 else (3,2));ent=[(x,y+2),(x+1,y+2),(x,y),(x,y+1)][l];d=[4,0,6,2][l];acc=[(ent[0]+DIRS[d][0],ent[1]+DIRS[d][1])]
            lots[e['id']]=(acc,e['color'])
            for dx in range(w):
                for dy in range(hh):blocked.add((x+dx,y+dy))
    return links,houses,lots,blocked
def comp_reach(links,start):
    adj=collections.defaultdict(set)
    for l in links:
        a,b=tuple(l);adj[a].add(b);adj[b].add(a)
    seen={start};st=[start]
    while st:
        c=st.pop()
        for n in adj[c]:
            if n not in seen:seen.add(n);st.append(n)
    return seen
def cheapest(links,src,dsts,blocked,t0,t1):
    adj=collections.defaultdict(set)
    for l in links:
        a,b=tuple(l);adj[a].add(b);adj[b].add(a)
    dist={src:0.0};prev={};pq=[(0.0,src)]
    while pq:
        d,c=heapq.heappop(pq)
        if d>dist.get(c,9e9):continue
        if c in dsts:
            path=[];n=c
            while n!=src:path.append((prev[n],n));n=prev[n]
            return d,[p for p in path if frozenset(p) not in links]
        for dx,dy in DIRS.values():
            n=(c[0]+dx,c[1]+dy)
            if not(0<=n[0]<50 and 0<=n[1]<30) or n in blocked:continue
            if frozenset([c,n]) in links:w=0.0
            else:
                ev=evidence(c,n,t0,t1)
                if ev<0.2:continue
                w=0.4+(1-ev)*2
            if d+w<dist.get(n,9e9):dist[n]=d+w;prev[n]=c;heapq.heappush(pq,(d+w,n))
    return None,[]
adds=[]
for vt in range(150,1190,50):
    links,houses,lots,blocked=build_state(vt)
    for a in adds:
        if a[4]<=vt:links.add(frozenset([(a[0],a[1]),(a[2],a[3])]))
    t0,t1=max(0,vt-40),vt
    for hid,(x,y,c,d) in houses.items():
        acc=(x+DIRS[d][0],y+DIRS[d][1]);targets=set()
        for lid,(accs,lc) in lots.items():
            if lc==c:targets|=set(accs)
        if not targets:continue
        if comp_reach(links,acc)&targets:continue
        cost,miss=cheapest(links,acc,targets,blocked,t0,t1)
        if cost is not None and cost<4.0 and miss:
            for a,b in miss:
                adds.append([a[0],a[1],b[0],b[1],vt-20]);links.add(frozenset([a,b]))
            print(vt,hid,'connected with',[(a,b) for a,b in miss],'cost',round(cost,2))
        elif cost is None or cost>=4.0:print(vt,hid,'NOT connectable',cost)
json.dump(adds,open('conn_adds.json','w'))
print(len(adds))
