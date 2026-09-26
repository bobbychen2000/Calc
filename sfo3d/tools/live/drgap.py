# Dead-reckoning horizon for moving ground aircraft in coverage gaps: for every gap of 6-45 s between two ground reports
# of an aircraft taxiing at SFO (>= 3 kt), the error at the next report of "constant speed for C s, then a smooth stop
# (tau 3 s)" for several C (traffic.js DRG_CONST_S). Usage: python3 tools/live/drgap.py <stream.jsonl.gz> [...]
import gzip, json, math, sys, collections
ARP=(37.618806,-122.375417); KT=0.514444
def xy(lat,lon): return ((lon-ARP[1])*111320*math.cos(math.radians(ARP[0])), -(lat-ARP[0])*110574)
tracks=collections.defaultdict(dict)
for f in sys.argv[1:]:
    for i,l in enumerate(gzip.open(f,'rt')):
        e=json.loads(l)
        for a in e['p'].get('ac',[]):
            if a.get('lat') is None or '_pt' not in a: continue
            x,z=xy(a['lat'],a['lon'])
            if not (-2700<x<1950 and -2350<z<1800): continue
            tracks[a['hex']][round(a['_pt'],2)]=(x,z,a.get('gs'),a.get('alt_baro')=='ground',a.get('true_heading'))
def dr(v0,t,C): 
    if t<=C: return v0*t
    return v0*C+v0*3*(1-math.exp(-(t-C)/3))
def pct(a,p): a=sorted(a); return a[int(p*(len(a)-1))] if a else float('nan')
pols=[7,15,25,45]
res={c:collections.defaultdict(list) for c in pols}
for hx,R in tracks.items():
    ts=sorted(R)
    for i in range(1,len(ts)-1):
        t0,t1=ts[i],ts[i+1]; G=t1-t0
        x0,z0,gs,g,th=R[t0]; x1,z1,gs1,g1,_=R[t1]; xp,zp,_,_,_=R[ts[i-1]]
        if not (g and g1) or gs is None or gs<3 or not (6<=G<=45): continue
        dx,dz=x0-xp,z0-zp
        if math.hypot(dx,dz)>3: u=(dx/math.hypot(dx,dz),dz/math.hypot(dx,dz))
        elif th is not None: u=(math.sin(math.radians(th)),-math.cos(math.radians(th)))
        else: continue
        v0=gs*KT; b='6-15' if G<15 else '15-30' if G<30 else '30-45'
        for C in pols:
            # mean error over the gap vs straight interpolation and error at the end
            ef=math.hypot(x0+u[0]*dr(v0,G,C)-x1, z0+u[1]*dr(v0,G,C)-z1)
            res[C][b].append(ef); res[C]['all'].append(ef)
            if (gs1 or 0) < 0.5*gs: res[C]['slowing'].append(ef)
for C in pols:
    print('const until %2ds:'%C, '  '.join('%s n=%d p50/p90 %.0f/%.0f'%(b,len(v),pct(v,.5),pct(v,.9)) for b,v in sorted(res[C].items())))
