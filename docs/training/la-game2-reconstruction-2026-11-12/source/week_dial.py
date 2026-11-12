"""Absolute game time from the HUD dial, week by week.
The weekly upgrade screen appears when the clock reaches Monday 00:00, i.e. at game time 140k (weeks of 7 x 20 s,
the game starting Monday 00:00). Time of day comes from the face (light 6am-6pm, dark 6pm-6am) and the hand: on a 12 h
dial one turn = one face = 10 game s, midnight = 12 o'clock on the dark face. Inside a week the time of day is unwrapped
(20 s period) over frames whose face reading is reliable (hand away from the 6 o'clock switch), backwards from the week's
end anchor. Writes week_time.csv: video, game. Prints, per week, the forward/backward consistency."""
import csv, math
rows = [r for r in csv.DictReader(open('dial_time.csv'))]
frames = []
for r in rows:
    if r['angle'] == '' or r['face'] == '?': continue
    u = ((float(r['angle']) - 180) % 360) / 360          # 0 at 6 o'clock
    if not (.08 < u < .92): continue
    tod = (5 + 10*u) if r['face'] == 'L' else ((u - .5)*10 if u >= .5 else 15 + 10*u)  # seconds since midnight
    frames.append((float(r['video']), tod % 20))
screens = [139.25, 285.5, 425.75, 570.0, 713.0, 863.25, 1003.25, 1145.5]
bounds = [0.0] + screens + [1e9]
out = []
for k in range(len(bounds) - 1):
    seg = [f for f in frames if bounds[k] < f[0] <= bounds[k+1] + 1e-6]
    if not seg: continue
    # backward from the end anchor (week k+1 ends at 140(k+1)) or forward from game start for the first week
    def unwrap(seq, start):
        res = [start]; prev_tod = seq[0][1]
        for v, tod in seq[1:]:
            d = tod - prev_tod
            while d > 10: d -= 20
            while d < -10: d += 20
            res.append(res[-1] + d); prev_tod = tod
        return res
    if k < len(screens):
        end_tod = seg[-1][1]; end_T = 140*(k+1) - (20 - end_tod if end_tod > 10 else -end_tod)
        back = unwrap(seg[::-1], end_T)[::-1]
    else:
        back = None
    if k > 0:
        st_tod = seg[0][1]; st_T = 140*k + (st_tod if st_tod < 10 else st_tod - 20)
        fwd = unwrap(seg, st_T)
    else:
        fwd = unwrap(seg, seg[0][1])   # week 1 starts at Monday 00:00 = 0
    use = back if back is not None else fwd
    if back is not None:
        diffs = [b - f for b, f in zip(back, fwd)]
        print(f'week {k+1}: video {seg[0][0]:7.2f}-{seg[-1][0]:7.2f}  start {use[0]:8.2f} end {use[-1]:8.2f}  backward-forward at start {diffs[0]:+6.2f}')
    else:
        print(f'week {k+1}: video {seg[0][0]:7.2f}-{seg[-1][0]:7.2f}  start {use[0]:8.2f} end {use[-1]:8.2f}  (forward only)')
    out += list(zip([s[0] for s in seg], use))
with open('week_time.csv', 'w', newline='') as fh:
    w = csv.writer(fh); w.writerow(['video', 'game'])
    for v, g in out: w.writerow([v, f'{g:.3f}'])
