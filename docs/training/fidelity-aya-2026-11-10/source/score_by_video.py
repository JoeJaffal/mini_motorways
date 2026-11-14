# index i -> video second 10*i ; None = unreadable
S=[None,None,1,2,3,5, 6,8,None,13,16,20, 24,30,36,42,45,51, 55,61,67,75,83,88, 102,112,122,130,137,149,
 159,166,176,186,196,208, 222,223,223,223,225,237, 244,253,270,285,294,308, 322,322,322,322,322,325,
 332,332,332,341,356,372, 377,379,397,397,397,411, 430,439,439,439,439,448, 459,481,498,516,537,537,
 540,562,None,604,625,651, 674,705,732,764,782,809, 809,809,809,809,809,809, 809,826,826,826,829]
import json,bisect,sys
ev=json.load(open('docs/training/simulator-repairs-2026-11-08/replay-candidate-v21.json'))['events']
pairs=sorted({(e['videoTime'],e['at']) for e in ev if 'videoTime' in e})
vt=[p[0] for p in pairs];gt=[p[1] for p in pairs]
def game(v):
    i=bisect.bisect_right(vt,v)
    if i==0:return gt[0]-(vt[0]-v)
    if i>=len(vt):return gt[-1]+(v-vt[-1])
    a,b=pairs[i-1],pairs[i]
    return a[1]+(b[1]-a[1])*(v-a[0])/(b[0]-a[0]) if b[0]>a[0] else a[1]
rows=[(10*i,round(game(10*i),1),s) for i,s in enumerate(S) if s is not None]
open('tmp/video/score_timeline.csv','w').write('video_s,game_s,score\n'+''.join(f'{a},{b},{c}\n' for a,b,c in rows))
print(len(pairs),'pairs; last pair',pairs[-1]); print(rows[::6])
