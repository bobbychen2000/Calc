import csv, sys, collections, statistics, math, json
from datetime import datetime, timezone
def P(xs,q):
    xs=sorted(xs); 
    if not xs: return None
    k=(len(xs)-1)*q; f=math.floor(k); c=min(f+1,len(xs)-1); return xs[f]+(xs[c]-xs[f])*(k-f)
def hav(a,b,c,d):
    R=6371.0088; p1,p2=math.radians(a),math.radians(c); dl=math.radians(d-b); dp=p2-p1
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2; return 2*R*math.asin(math.sqrt(h))
SHA=(31.19784885,121.3362899)
allrows=[]
for f in sys.argv[1:]:
    rows=[r for r in csv.DictReader(open(f)) if r["method"]]
    allrows+=rows
    day=rows[0]['day']
    roles=collections.Counter(r['role_at_ZSSS'] for r in rows)
    regs=set(r['registration'] for r in rows); icao=set(r['icao24'] for r in rows)
    print(f'== {day}: n={len(rows)} roles={dict(roles)} distinct icao24={len(icao)} regs={len(regs)} share783.4={len(rows)/783.4:.3f} share802={len(rows)/802:.3f}')
    print(' reg empty', sum(1 for r in rows if not r['registration']), 'type empty', sum(1 for r in rows if not r['type']))
    print(' reg_src', collections.Counter(r['reg_src'] for r in rows), 'type_src', collections.Counter(r['type_src'] for r in rows))
    print(' db_check', collections.Counter(r['db_check'] for r in rows))
    print(' wiki_pair', collections.Counter(r['wiki_pair'] for r in rows))
    print(' method', collections.Counter(r['method'] for r in rows))
    s=[float(r['sigma_min']) for r in rows]
    print(f' sigma median {statistics.median(s):.1f} P10 {P(s,.1):.1f} P90 {P(s,.9):.1f} max {max(s):.1f} <=5 {sum(x<=5 for x in s)/len(s):.3f} <=10 {sum(x<=10 for x in s)/len(s):.3f} <=20 {sum(x<=20 for x in s)/len(s):.3f}')
    # nearest fix distance
    dists=[]
    for r in rows:
        if r['role_at_ZSSS']=='arr': lat,lon=float(r['last_lat']),float(r['last_lon'])
        else: lat,lon=float(r['first_lat']),float(r['first_lon'])
        dists.append(hav(SHA[0],SHA[1],lat,lon))
    print(f' nearest-fix km P10 {P(dists,.1):.0f} med {statistics.median(dists):.0f} P90 {P(dists,.9):.0f} max {max(dists):.0f}  >1300km {sum(d>1300 for d in dists)} >900 {sum(d>900 for d in dists)}')
    big=[(d,float(r['sigma_min']),r['method'],r['role_at_ZSSS']) for d,r in zip(dists,rows) if d>1300]
    if big: print('  >1300 km: sigma', sorted(set(round(b[1],1) for b in big)), collections.Counter((b[2],b[3]) for b in big))
    # duplicates
    key=collections.Counter((r['callsign'],r['role_at_ZSSS']) for r in rows)
    print(' duplicate callsign+role', [k for k,v in key.items() if v>1][:10])
    key2=collections.Counter((r['icao24'],r['first_fix_utc']) for r in rows)
    print(' duplicate icao+firstfix', sum(1 for v in key2.values() if v>1))
    print(' regions', collections.Counter(r['nearest_fix_region'] for r in rows))
    print(' far_end_event nonempty', sum(1 for r in rows if r['far_end_event']))
# type mix
fam=collections.Counter()
def family(t):
    if t in ('A318','A319','A320','A321','A19N','A20N','A21N'): return 'A320fam'
    if t.startswith('B73') or t in ('B37M','B38M','B39M','B3XM'): return '737'
    if t in ('C919',): return 'C919'
    if t in ('AJ27','AJ30'): return 'C909'
    if t[:3] in ('A33','A34','A35','A38','B74','B76','B77','B78') : return 'wide'
    return 'other:'+t
for r in allrows: fam[family(r['type'])]+=1
n=sum(fam.values()); print('type mix n=',n, {k:f'{100*v/n:.1f}' for k,v in fam.most_common()})
tc=collections.Counter(r['type'] for r in allrows); print({k:f'{100*v/n:.1f}' for k,v in tc.most_common(15)})
