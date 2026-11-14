"""Read the HUD clock dial in every 4 fps crop (dialseq/) and unwrap the hand into game time.
Run in tmp/video after extracting the crops (1920x1200 recording):
  ffmpeg -i "screen-capture (2).webm" -vf "fps=4,crop=150:95:1765:8" dialseq/%05d.png
Then week_dial.py (absolute time, week by week), make_v21d.py (re-timed replay) and cmp_replay.py (comparison).
The unwrapped turns below are only a diagnostic; week_dial.py does not depend on them.
Writes dial_time.csv: video_time, face (L/D/?), angle_deg (clockwise from 12), turns (unwrapped, 10 game s each)."""
import glob, math, csv
import numpy as np
from PIL import Image

CX, CY = 109.0, 43.0
fs = sorted(glob.glob('dialseq/*.png'))
yy, xx = np.mgrid[0:94, 0:150]
dx, dy = xx - CX, yy - CY
r = np.hypot(dx, dy)
face_mask = (r > 3) & (r < 24)
hand_zone = (r >= 3) & (r <= 16)

rows = []
for i, f in enumerate(fs):
    v = i / 4.0
    a = np.asarray(Image.open(f).convert('L'), dtype=float)
    med = np.median(a[face_mask])
    if med > 150: face = 'L'; hand = hand_zone & (a < med - 70)
    elif med < 110: face = 'D'; hand = hand_zone & (a > med + 70)
    else: rows.append((v, '?', float('nan'))); continue
    if hand.sum() < 4: rows.append((v, face, float('nan'))); continue
    w = r[hand]
    sx = (dx[hand] * w).sum(); sy = (dy[hand] * w).sum()
    ang = math.degrees(math.atan2(sx, -sy)) % 360.0
    rows.append((v, face, ang))

# unwrap: turns measured from the 6 o'clock position (where the face switches)
turns = []; prev = None; k = 0
for v, face, ang in rows:
    if math.isnan(ang): turns.append(float('nan')); continue
    u = ((ang - 180.0) % 360.0) / 360.0
    if prev is not None:
        d = u - prev
        if d < -0.5: k += 1
        elif d > 0.5: k -= 1
    prev = u
    turns.append(k + u)
with open('dial_time.csv', 'w', newline='') as fh:
    wr = csv.writer(fh); wr.writerow(['video', 'face', 'angle', 'turns'])
    for (v, face, ang), t in zip(rows, turns): wr.writerow([v, face, '' if math.isnan(ang) else f'{ang:.1f}', '' if math.isnan(t) else f'{t:.4f}'])
ok = [t for t in turns if not math.isnan(t)]
print('frames', len(rows), 'readable', len(ok), 'total turns', ok[-1] - ok[0], '=> game seconds', 10 * (ok[-1] - ok[0]))

# Second pass: face parity. The face flips every turn (light on even turns, dark on odd, counting from the first
# readable frame). After a gap, a parity mismatch away from the switch point means a turn was missed.
fixed=[];k=None;prev_u=None;prev_v=None;mism=0
for (v,face,ang) in rows:
    if math.isnan(ang) or face=='?': fixed.append(float('nan'));continue
    u=((ang-180.0)%360.0)/360.0
    if k is None: k=0 if face=='L' else 1
    else:
        d=u-prev_u
        if d<-0.5:k+=1
        elif d>0.5:k-=1
        if .1<u<.9 and ((k%2==0)!=(face=='L')):
            if v-prev_v>0.3: k+=1
            else: mism+=1
    prev_u=u;prev_v=v;fixed.append(k+u)
with open('dial_time2.csv','w',newline='') as fh:
    wr=csv.writer(fh);wr.writerow(['video','face','turns'])
    for (v,face,ang),t in zip(rows,fixed):
        if not math.isnan(t):wr.writerow([v,face,f'{t:.4f}'])
ok=[t for t in fixed if not math.isnan(t)]
print('pass2 total turns',ok[-1]-ok[0],'parity mismatches without gap',mism)
