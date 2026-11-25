"""Explicit experimental reward. Uses visible road links, never engine routes."""
from collections import deque
DIRECTIONS=((1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1))
BETA=.25
ROAD_COST=.01

def specification(mode):
    if mode == 'single-build':
        return dict(name=mode, gamma=1, connected=1, disconnected=0)
    if mode=='score':return dict(name='score',gamma=1)
    if mode!='connection-economy':raise ValueError('Unknown reward mode')
    return dict(name=mode,gamma=1,connection_potential=BETA,positive_road_consumption_cost=ROAD_COST,
                true_terminal_potential=0,refund_reward=0)

def connection_potential(raw,area):
    """Boolean reachability using reciprocal visible edges and correct entrances.

    No generated construction route or gap coordinate is returned to the actor.
    """
    house=next(b for b in raw['buildings'] if b['isHouse'])
    shop=next(b for b in raw['buildings'] if not b['isHouse'])
    if house['color']!=shop['color']:return 0.
    def index(p):return p['y']*50+p['x']
    start=index(house['cell']);target=index(shop['entrance'])
    links=raw['connections']
    def edge(cell,d):
        x,y=cell%50,cell//50;dx,dy=DIRECTIONS[d];xx,yy=x+dx,y+dy
        if not (0<=xx<50 and 0<=yy<30):return None
        nxt=yy*50+xx
        if not (area[cell] and area[nxt] and links[cell]&(1<<d) and links[nxt]&(1<<((d+4)%8))):return None
        return nxt
    if edge(start,house['drivewayDirection']) is None or edge(target,shop['drivewayDirection']) is None:return 0.
    seen={start};queue=deque([start])
    while queue:
        cell=queue.popleft()
        if cell==target:return 1.
        for d in range(8):
            nxt=edge(cell,d)
            if nxt is not None and nxt not in seen:seen.add(nxt);queue.append(nxt)
    return 0.

def reward_parts(mode,*,trips,before,after,spent,terminated):
    specification(mode)
    if spent<0:raise ValueError('Consumption cannot be negative')
    if mode == 'single-build':
        return float(after), 0., 0.
    if mode=='score':return float(trips),0.,0.
    shaping=BETA*((0. if terminated else after)-before)
    cost=ROAD_COST*spent
    return float(trips)+shaping-cost,shaping,cost
