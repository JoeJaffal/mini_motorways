# Monte Carlo of the gp-7/cma-7 stop rule: per-map paired slope over the last W snapshots on a fixed tracking block.
import numpy as np, sys
rng=np.random.default_rng(7)
NM=150; EVERY=5; W=5; GMIN=25; GMAX=45; TAU=2.0; Z=0.8416  # one-sided 80%
def curve(name,g):
    g=np.asarray(g,float)
    return {'flat':0*g,'rise15':4*np.minimum(g,15),'rise25':4*np.minimum(g,25),'lin2':2*g,'lin3':3*g,'lin4':4*g,
            'rise35':4*np.minimum(g,35)}[name]
def run(name,sd,rho,reps=4000):
    snaps=np.arange(0,GMAX+1,EVERY); S=len(snaps)
    conv=0; gens=[]
    x=np.arange(W)*EVERY; xc=x-x.mean(); w=xc/(xc**2).sum()
    for _ in range(reps):
        e=np.empty((S,NM)); e[0]=rng.normal(0,sd,NM)
        for i in range(1,S): e[i]=rho*e[i-1]+np.sqrt(1-rho**2)*rng.normal(0,sd,NM)
        y=e+curve(name,snaps)[:,None]+rng.normal(0,110,NM)[None,:]
        fired=None
        for i in range(S):
            g=snaps[i]
            if g<GMIN or i+1<W: continue
            sl=w@y[i+1-W:i+1]   # per-map slope
            ub=sl.mean()+Z*sl.std(ddof=1)/np.sqrt(NM)
            if ub<TAU: fired=g; break
        if fired is not None: conv+=1; gens.append(fired)
    return conv/reps, (np.median(gens) if gens else None)
if __name__=="__main__":
     for sd in (250,330):
      for rho in (0.2,0.5):
        out=[]
        for c in ('flat','rise15','rise25','rise35','lin2','lin3','lin4'):
            p,m=run(c,sd,rho,2000); out.append(f"{c}:{p:.3f}/{m}")
        print(f"sd={sd} rho={rho} ", "  ".join(out)); sys.stdout.flush()
