"""Second pass: hours covered, ground-track continuity, NACp on field, runway direction, landings/touch-and-goes."""
import lzma, json, glob, math, sys, collections as C, statistics as S
ARP=(37.65893166,-122.12173888); FE=52
def xy(lat,lon): return ((lon-ARP[1])*111195*math.cos(math.radians(ARP[0])),(lat-ARP[0])*111195)
files=sorted(glob.glob(sys.argv[1]+'/adsblol_*.jsonl.xz'))
# ODbL notice as the first output line (round-1 re-check, 2026-11-12: the committed summary is this script's stdout)
print('# Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/); aggregate output of hwd3d/tools/phase0/hwd_cov.py; offered under the ODbL 1.0')
okh=set(); trk=C.defaultdict(list); nacp=C.Counter(); per_day=C.defaultdict(set); polls_per_h=C.Counter()
for f in files:
    for line in lzma.open(f,'rt'):
        r=json.loads(line)
        if r.get('code')!=200: continue
        t=r['t']; okh.add(int(t//3600)); polls_per_h[int(t//3600)]+=1
        for a in r['d'].get('ac',[]):
            if 'lat' not in a: continue
            x,y=xy(a['lat'],a['lon']); d=math.hypot(x,y)
            alt=a.get('alt_baro'); g= alt=='ground'
            av= FE if g else alt if isinstance(alt,(int,float)) else None
            if av is None or d>1500 or av>FE+150: continue
            tp=t-a.get('seen_pos',0)
            trk[a['hex']].append((round(tp,1),x,y,av,a.get('gs'),a.get('track'),g,a.get('nac_p'),a.get('type')))
            nacp[a.get('nac_p')]+=1
            per_day[int((t-8*3600)//86400)].add(a['hex'])
print('hours with ok polls:',len(okh),'of span',(max(okh)-min(okh)+1))
print('polls/hour median:',S.median(polls_per_h.values()))
print('NACp on field:',sorted(nacp.items(),key=lambda k:str(k[0])))
print('distinct on-field aircraft per local day:',{k:len(v) for k,v in sorted(per_day.items())})
# continuity of moving ground tracks
gaps=[]; still=0; moving=0; runway_ops=C.Counter(); tg=0
for h,p in trk.items():
    p=sorted(set(p),key=lambda q:q[0])
    for a,b in zip(p,p[1:]):
        dt=b[0]-a[0]
        if dt<=0: continue
        if a[6] and b[6] and (a[4] or 0)>3: gaps.append(dt)
    # runway direction: low airborne fixes (<400 ft AGL) with track
    for q in p:
        if not q[6] and q[3]<FE+400 and q[5] is not None and (q[4] or 0)>40:
            tr=q[5]
            runway_ops['28 (W-bound)' if 255<tr<345 else '10 (E-bound)' if 75<tr<165 else 'other']+=1
gaps.sort()
def pct(v,q): return v[min(len(v)-1,int(q*len(v)))]
print('moving ground fix gaps s: n',len(gaps),'p50',pct(gaps,.5),'p90',pct(gaps,.9),'p99',pct(gaps,.99),'>10s share',round(sum(g>10 for g in gaps)/len(gaps),3))
print('low airborne fixes by direction:',runway_ops)
# parked aircraft broadcasting: aircraft with >=20 ground fixes at gs<1 spanning >10 min
parked=[h for h,p in trk.items() if sum(1 for q in p if q[6] and (q[4] or 0)<1)>=20 and (max(q[0] for q in p)-min(q[0] for q in p))>600]
print('aircraft seen standing still on the ground >=20 fixes:',len(parked))
# touch-and-go / pattern: count ground->air transitions per aircraft per visit
cyc=C.Counter()
for h,p in trk.items():
    p=sorted(set(p),key=lambda q:q[0]); n=0
    for a,b in zip(p,p[1:]):
        if a[6] and not b[6] and b[0]-a[0]<60: n+=1
    cyc[min(n,6)]+=1
print('ground->air transitions per aircraft (whole week, 6=6+):',sorted(cyc.items()))
