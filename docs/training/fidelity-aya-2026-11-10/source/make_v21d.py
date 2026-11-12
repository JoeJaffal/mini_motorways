"""Replay v21d: v21c with event times re-read from the game's clock dial (week_time.csv from week_dial.py).
Each event's 'at' becomes the dial's game time at its videoTime (linear between readable frames up to 1.5 s apart,
or the nearest readable frame within 0.5 s). Offer/choose events stay on their week boundary. Events where the
dial cannot be read take the correction of the nearest dial-timed event in the same week. Times stay non-decreasing
in file order. Prints the corrections."""
import csv, json, bisect, sys
src = sys.argv[1]; dst = sys.argv[2]
rows = list(csv.DictReader(open('week_time.csv')))
V = [float(r['video']) for r in rows]; G = [float(r['game']) for r in rows]
def g_at(v):
    if v < 20: return None                     # the HUD is still sliding in
    i = bisect.bisect_left(V, v)
    if 0 < i < len(V) and V[i] - V[i-1] <= 1.5:
        f = (v - V[i-1]) / (V[i] - V[i-1]); return G[i-1] + f*(G[i] - G[i-1])
    if i < len(V) and abs(V[i] - v) <= .5: return G[i]
    if i > 0 and abs(V[i-1] - v) <= .5: return G[i-1]
    return None
d = json.load(open(src)); ev = d['events']
corr = [None]*len(ev)
for i, e in enumerate(ev):
    if e['kind'] in ('offer', 'choose'): corr[i] = 0.0; continue
    g = g_at(e['videoTime'])
    if g is None and e['videoTime'] >= 20:
        j = bisect.bisect_left(V, e['videoTime'])
        if 0 < j < len(V) and G[j] - G[j-1] < 1.0: g = G[j-1]     # inside a pause: the clock stood still
    if g is not None: corr[i] = g - e['at']
week = lambda t: int(t // 140)
for i, e in enumerate(ev):
    if corr[i] is None:
        cands = [(abs(j - i), corr[j]) for j in range(len(ev)) if corr[j] is not None and ev[j]['kind'] not in ('offer', 'choose') and week(ev[j]['at']) == week(e['at'])]
        corr[i] = min(cands)[1] if cands else 0.0
prev = 0.0; changed = 0
for i, e in enumerate(ev):
    new = round(max(prev, e['at'] + corr[i]), 2)
    if abs(new - e['at']) > 0.25: changed += 1
    if abs(new - e['at']) > 1.0: print(f"#{i:3d} video {e['videoTime']:6.1f} {e['kind']:9s} {e['at']:8.2f} -> {new:8.2f} ({new - e['at']:+.2f})")
    e['at'] = new; prev = new
d.setdefault('notes', [])
if isinstance(d['notes'], list): d['notes'].append('v21d: event times re-read from the HUD clock dial (tmp/video/week_dial.py); offers stay on week boundaries.')
json.dump(d, open(dst, 'w'), indent=1)
print('events moved by more than 0.25 s:', changed, 'of', len(ev))
