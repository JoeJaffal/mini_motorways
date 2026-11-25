"""Published visible-state schema, independent of legacy debug-rich encoding.

No policy input is derived from routes, reservations, internal vehicle speed/wait,
score, future events or continuous overcrowding timers. Four traffic frames use
only visible positions/headings at distinct observation timestamps.
"""
from collections import deque
import math

import gymnasium as gym
import numpy as np

WIDTH, HEIGHT, CELLS = 50, 30, 1500
SCHEMA = 'maskable-visible-v1'


def observation_space():
    return gym.spaces.Dict({
        'grid': gym.spaces.Box(-1, 1, (81, HEIGHT, WIDTH), np.float32),
        'global': gym.spaces.Box(0, 1, (54,), np.float32),
        'motorways': gym.spaces.Box(0, 1, (CELLS, 6), np.float32),
    })


def bounded(value, scale):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('Expected finite nonnegative displayed quantity')
    return value/(value+scale)


def point(value):
    return int(value['x']), int(value['y'])


class VisibleObservation:
    def __init__(self):
        self.reset()

    def reset(self):
        self.frames = deque(maxlen=4)
        self.last_time = None
        self.previous_cars = {}

    @staticmethod
    def visibility(raw):
        if (raw['width'], raw['height']) != (WIDTH, HEIGHT):
            raise ValueError('Canvas schema changed')
        yy, xx = np.mgrid[:HEIGHT, :WIDTH]
        bounds = [raw[k] for k in ('playableXMin','playableXMax','playableYMin','playableYMax')]
        if not all(math.isfinite(v) for v in bounds):
            raise ValueError('Nonfinite revealed bounds')
        return (xx >= bounds[0]) & (xx < bounds[1]) & (yy >= bounds[2]) & (yy < bounds[3])

    def _traffic(self, raw, visible):
        now = float(raw['time'])
        if not math.isfinite(now) or now < 0:
            raise ValueError('Invalid observation time')
        if self.last_time is not None and now < self.last_time:
            raise ValueError('Time moved backwards without encoder reset')
        if self.last_time == now:
            return
        cars = {}
        count = np.zeros((HEIGHT, WIDTH), np.float64)
        sums = np.zeros((6, HEIGHT, WIDTH), np.float64)
        tracked = np.zeros_like(count)
        for car in raw['vehicles']:
            # Host flag mirrors ordinary rendering; no internal stage/speed is an input.
            if not car['visible']:
                continue
            x, y, hx, hy = (float(car[k]) for k in ('x','y','headingX','headingY'))
            if not all(math.isfinite(v) for v in (x,y,hx,hy)) or abs(hx)>1.000001 or abs(hy)>1.000001:
                raise ValueError('Invalid displayed vehicle geometry')
            if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
                continue
            ix, iy = min(WIDTH-1, math.floor(x+.5)), min(HEIGHT-1, math.floor(y+.5))
            if not visible[iy,ix]:
                continue
            identity = int(car['id'])
            if identity in cars:
                raise ValueError('Duplicate visible vehicle ID')
            cars[identity] = (x,y)
            count[iy,ix] += 1
            sums[1,iy,ix] += hx
            sums[2,iy,ix] += hy
            if identity in self.previous_cars and self.last_time is not None:
                px, py = self.previous_cars[identity]
                vx, vy = (x-px)/(now-self.last_time), (y-py)/(now-self.last_time)
                sums[3,iy,ix] += vx
                sums[4,iy,ix] += vy
                tracked[iy,ix] += 1
                sums[5,iy,ix] += math.hypot(vx,vy) < .02
        frame = np.zeros((6,HEIGHT,WIDTH), np.float32)
        frame[0] = count/(count+1)
        for channel in (1,2):
            np.divide(sums[channel], count, out=frame[channel], where=count>0)
        for channel in (3,4,5):
            np.divide(sums[channel], tracked, out=frame[channel], where=tracked>0)
        frame[3:5] /= np.abs(frame[3:5])+4
        # Valid means a previous distinct-time observation was available for motion.
        self.frames.appendleft((now, frame, self.last_time is not None))
        self.previous_cars, self.last_time = cars, now

    def encode(self, raw, *, horizon, stage=0, control=None, paused_tokens=0,
               operands=(None,None,None,None)):
        visible = self.visibility(raw)
        grid = np.zeros((81,HEIGHT,WIDTH), np.float32)
        grid[0] = visible
        def array(name, low, high):
            a = np.asarray(raw[name])
            if a.shape != (CELLS,):
                raise ValueError('Unexpected '+name+' shape')
            a = a.reshape(HEIGHT,WIDTH)
            if not np.isfinite(a[visible]).all() or ((a[visible]<low)|(a[visible]>high)).any():
                raise ValueError('Unknown visible '+name+' value')
            if not np.equal(a[visible], np.floor(a[visible])).all():
                raise ValueError('Noninteger visible '+name+' value')
            return np.where(visible,a,0)
        terrain = array('terrain',0,2)
        infra = array('infrastructure',0,4)
        connections = array('connections',0,255).astype(np.int64)
        pending = array('pendingRemovals',0,1)
        kinds = array('buildingKinds',0,2)
        colors = array('buildingColors',-1,7)
        demand = array('demand',0,np.inf)
        for i in range(3): grid[1+i] = terrain == i
        for i in range(5): grid[4+i] = infra == i
        for i in range(8): grid[9+i] = (connections & (1<<i)) != 0
        grid[17] = pending
        for i in range(3): grid[18+i] = kinds == i
        for i in range(8): grid[21+i] = (colors == i) & (kinds != 0)
        for b in raw['buildings']:
            x,y = point(b['cell'])
            w,h = int(b['width']),int(b['height'])
            if w < 1 or h < 1: raise ValueError('Invalid displayed building footprint')
            if x+w<=0 or y+h<=0 or x>=WIDTH or y>=HEIGHT: continue
            footprint = np.zeros_like(visible)
            footprint[max(0,y):min(HEIGHT,y+h),max(0,x):min(WIDTH,x+w)] = True
            footprint &= visible
            if not footprint.any(): continue
            if not 0 <= b['color'] < 8: raise ValueError('Unknown visible building color')
            for ch,key in ((38,'upgraded'),(39,'sharedLot'),(40,'isStation')):
                grid[ch,footprint] = bool(b[key])
            if not b['isHouse']:
                # The host provides only a displayed warning bit to this encoder.
                grid[42,footprint] = bool(b['warningVisible'])
            accesses = [b['cell']] if b['isHouse'] else (b['entrances'] or [b['entrance']])
            directions = [b['drivewayDirection']] if b['isHouse'] else (b['entranceDirections'] or [b['drivewayDirection']])
            if len(accesses) != len(directions): raise ValueError('Entrance schema mismatch')
            for access,direction in zip(accesses,directions):
                px,py = point(access)
                if 0<=px<WIDTH and 0<=py<HEIGHT and visible[py,px]:
                    if not 0<=direction<8: raise ValueError('Unknown entrance direction')
                    grid[29,py,px] = 1
                    grid[30+direction,py,px] = 1
        grid[41] = np.where(kinds==2,demand/(demand+10),0)
        def shown(p):
            return 0<=p[0]<WIDTH and 0<=p[1]<HEIGHT and visible[p[1],p[0]]
        records = []
        for m in raw['motorways']:
            a,b = point(m['start']),point(m['end'])
            retiring = bool(m['pendingRemoval'])
            for p,q in ((a,b),(b,a)):
                if shown(p):
                    grid[44 if retiring else 43,p[1],p[0]] = 1
                    if not retiring and shown(q):
                        grid[45,p[1],p[0]] = (q[0]-p[0])/49
                        grid[46,p[1],p[0]] = (q[1]-p[1])/29
            if shown(a) and shown(b):
                records.append((retiring,a[1],a[0],b[1],b[0],int(m['id'])))
        if len(records)>=CELLS: raise ValueError('Visible motorway table capacity reached')
        table = np.zeros((CELLS,6), np.float32)
        for i,(pending,ay,ax,by,bx,_) in enumerate(sorted(records)):
            table[i] = ax/49,ay/29,bx/49,by/29,pending,1
        for r in raw['roundabouts']:
            x,y = point(r['center'])
            if shown((x,y)): grid[47,y,x] = 1
        if len(operands)!=4: raise ValueError('Expected four operand markers')
        for ch,p in enumerate(operands,48):
            if p is not None and shown(p): grid[ch,p[1],p[0]] = 1
        yy,xx = np.mgrid[:HEIGHT,:WIDTH]
        grid[52],grid[53] = xx/49,yy/29
        for line in raw['railLines']:
            for cell in line['cells']:
                x,y=point(cell)
                if shown((x,y)): grid[54,y,x]=1
        for cell in raw['closedRailCrossings']:
            x,y=point(cell)
            if shown((x,y)): grid[55,y,x]=1
        for train in raw['trains']:
            x,y=float(train['x']),float(train['y'])
            if not math.isfinite(x) or not math.isfinite(y): raise ValueError('Invalid visible train geometry')
            if 0<=x<WIDTH and 0<=y<HEIGHT:
                ix,iy=min(WIDTH-1,math.floor(x+.5)),min(HEIGHT-1,math.floor(y+.5))
                if shown((ix,iy)): grid[56,iy,ix]=1
        self._traffic(raw,visible)
        global_values=np.zeros(54,np.float32)
        if len(raw['inventory'])!=6: raise ValueError('Inventory schema changed')
        global_values[:6]=[bounded(n,100) for n in raw['inventory']]
        offers=raw['upgradeChoices']
        if len(offers)>2: raise ValueError('Offer schema overflow')
        for i,offer in enumerate(offers):
            if not 0<=offer['type']<6: raise ValueError('Unknown offer type')
            offset=6+i*9
            global_values[offset]=1
            global_values[offset+1+offer['type']]=1
            global_values[offset+7:offset+9]=bounded(offer['amount'],100),bounded(offer['roads'],100)
        now=float(raw['time'])
        if not 0<horizon<=3600: raise ValueError('Unsupported task horizon')
        global_values[24:28]=bounded(raw['day'],100),bounded(raw['week'],100),(now%20)/20,max(0,horizon-now)/3600
        if not 0<=stage<6: raise ValueError('Unknown interface stage')
        global_values[28+stage]=1
        if control is not None:
            if not 0<=control<10: raise ValueError('Unknown root control')
            global_values[34+control]=1
        global_values[44]=min(max(0,paused_tokens)/4096,1)
        for i,(time,frame,valid) in enumerate(self.frames):
            grid[57+i*6:63+i*6]=frame
            global_values[45+i]=valid
            global_values[49+i]=bounded(now-time,1)
        global_values[53]=bool(offers)
        grid[:,~visible]=0
        output={'grid':grid,'global':global_values,'motorways':table}
        if not all(np.isfinite(a).all() for a in output.values()):
            raise ValueError('Nonfinite visible observation')
        return output
