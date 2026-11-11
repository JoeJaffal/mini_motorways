import re,sys,statistics as st
for name in sys.argv[1:]:
    rows=[re.match(r'(\w+) seed (\d) t=(\d+) houses (\d+) destinations (\d+) lots (\d+) upgraded (\d+) meanHouseToOwnDest ([\d.]+) housesTouchingLots (\d+)',l) for l in open(name)]
    rows=[r.groups() for r in rows if r]
    print(name,open(name).readline().strip())
    for m in ['LosAngeles','London']:
        for t in ['600','1200']:
            g=[r for r in rows if r[0]==m and r[2]==t]
            f=lambda i:st.mean(float(r[i]) for r in g)
            print(f'  {m} t={t}: houses {f(3):.1f} ({min(int(r[3]) for r in g)}-{max(int(r[3]) for r in g)}) destinations {f(4):.1f} ({min(int(r[4]) for r in g)}-{max(int(r[4]) for r in g)}) lots {f(5):.1f} upgraded {f(6):.1f} meanDist {f(7):.2f} ({min(float(r[7]) for r in g):.2f}-{max(float(r[7]) for r in g):.2f}) touching {f(8):.1f}')
