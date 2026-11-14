import stop7 as s, sys
for tau,z in ((1.5,0.8416),(2.0,1.2816),(1.5,1.2816)):
    s.TAU=tau; s.Z=z
    for sd,rho in ((250,0.3),(330,0.3)):
        out=[]
        for c in ('flat','rise15','rise25','lin2','lin3','lin4'):
            p,m=s.run(c,sd,rho,1500); out.append(f"{c}:{p:.3f}/{m}")
        print(f"tau={tau} z={z} sd={sd} ", "  ".join(out)); sys.stdout.flush()
