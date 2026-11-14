import ctypes, math, os, sys
dll=ctypes.CDLL(os.path.join(os.path.dirname(__file__),'lib','dpcPlatform.dll'))
f=dll.CalculateAcceleration;f.restype=ctypes.c_int64;f.argtypes=[ctypes.c_int64]*9
S=2**32
def raw(x):return int(round(x*S))
def native(gap,v,vl,al,vd,amax,aexp,bmax,bexp):return f(*(raw(x) for x in (gap,v,vl,al,vd,amax,aexp,bmax,bexp)))/S
VL=2791728742/S;MG=429496729/S;T=1.0;COOL=858993459/S
def ref(gap,v,vl,al,vd,a,ae,b,be):
    s=max(gap-VL,MG);dv=v-vl
    free=a*(1-(v/vd)**ae) if v<=vd else -b*(1-(vd/v)**(a*be/b))
    z=(MG+max(0,v*T+0.5*v*dv/math.sqrt(a*b)))/s
    f5=a*(1-z*z)
    if v<=vd:f6=f5 if z>=1 else free*(1-z**(2*a/max(free,1e-3)))
    else:f6=free+f5 if z>=1 else free
    f7=1 if v-vl>=0 else 0;f8=2*s*al or 1e-5
    first=(v*v*al/(vl*vl-f8)) if vl*dv<-f8 else (al-dv*dv*f7/(2*s))
    first=min(first,a)
    sec=f6 if f6>=first else (1-COOL)*f6+COOL*(first+b*math.tanh((f6-first)/b))
    return max(-b,sec) if vd>=1e-5 else 0
a,ae,b,be=0.54,4.0,12.0,6.0
print(' v(world)  d(world)   native   reference')
for v in (2.3,2.0,1.5,1.0,0.5):
    for d in (2.0,1.5,1.0,0.6,0.3,0.1):
        g=d+VL+MG
        print(f'{v:6.2f} {d:7.2f}  {native(g,v,0,0,2.4,a,ae,b,be):9.3f} {ref(g,v,0,0,2.4,a,ae,b,be):9.3f}')
