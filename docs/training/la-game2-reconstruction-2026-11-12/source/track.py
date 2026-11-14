import json, numpy as np, sys
from scipy.optimize import linear_sum_assignment
D=json.load(open(sys.argv[1]));D={int(k):v for k,v in D.items()};ts=sorted(D)
# remove static blobs
def near(p,lst,r):return any(abs(p[0]-q[0])<r and abs(p[1]-q[1])<r for q in lst)
clean={}
for t in ts:
    win=[u for u in ts if abs(u-t)<=10 and u!=t]
    clean[t]=[p for p in D[t] if sum(near(p,D[u],0.2) for u in win)<0.7*len(win)]
print('mean moving dets',round(np.mean([len(v) for v in clean.values()]),1))
# link
tracks=[];active=[]
for t in ts:
    dets=clean[t];
    if active and dets:
        C=np.array([[np.hypot(tr['pts'][-1][1]-d[0],tr['pts'][-1][2]-d[1]) for d in dets] for tr in active])
        r,c=linear_sum_assignment(C);used=set();keep=[]
        for i,j in zip(r,c):
            gap=t-active[i]['pts'][-1][0]
            if gap<=2 and C[i,j]<=2.5*gap:active[i]['pts'].append((t,dets[j][0],dets[j][1]));used.add(j)
        for j,d in enumerate(dets):
            if j not in used:active.append({'pts':[(t,d[0],d[1])]})
    else:
        for d in dets:active.append({'pts':[(t,d[0],d[1])]})
    still=[]
    for tr in active:
        (still if t-tr['pts'][-1][0]<=2 else tracks).append(tr)
    active=still
tracks+=active
long=[tr for tr in tracks if len(tr['pts'])>=5]
json.dump(long,open(sys.argv[2],'w'))
print('tracks',len(tracks),'long',len(long))
