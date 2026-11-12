"""Measure KHWD traffic in the sfo3d adsb.lol rec_pack: type mix, sources, ground/low coverage."""
import lzma, json, glob, math, sys, collections as C
ARP=(37.65893166,-122.12173888)  # NASR APT_BASE 2026-10-29
FE=52  # field elev ft
def dist(lat,lon):
    dy=(lat-ARP[0])*111195; dx=(lon-ARP[1])*111195*math.cos(math.radians(ARP[0])); return math.hypot(dx,dy)
files=sorted(glob.glob(sys.argv[1]+'/adsblol_*.jsonl.xz'))
polls=0; okp=0; ts=[]
ac={}   # hex -> info
src_fix=C.Counter(); ground_src=C.Counter(); air_src=C.Counter()
low_fix=0; ground_fix=0; fix_by_ring=C.Counter()
hours=C.Counter(); ground_by_hour=C.Counter()
for f in files:
    for line in lzma.open(f,'rt'):
        r=json.loads(line); polls+=1
        if r.get('code')!=200: continue
        okp+=1; t=r['t']; ts.append(t)
        for a in r['d'].get('ac',[]):
            if 'lat' not in a: continue
            d=dist(a['lat'],a['lon'])
            alt=a.get('alt_baro'); g = alt=='ground'
            altv = FE if g else (alt if isinstance(alt,(int,float)) else None)
            if d>5556 or altv is None or altv>3000+FE: continue   # 3 nm, < 3000 ft AGL
            h=a['hex']; s=a.get('type','?')
            x=ac.setdefault(h,{'r':set(),'t':set(),'cs':set(),'cat':set(),'src':C.Counter(),'n':0,'g':0,'airport':0,'tisb':0,'first':t,'last':t,'minalt':99999,'dbFlags':0})
            x['n']+=1; x['last']=t; x['src'][s]+=1
            if a.get('r'): x['r'].add(a['r'])
            if a.get('t'): x['t'].add(a['t'])
            cs=(a.get('flight') or '').strip()
            if cs: x['cs'].add(cs)
            if a.get('category'): x['cat'].add(a['category'])
            x['dbFlags']|=a.get('dbFlags',0)
            x['minalt']=min(x['minalt'],altv)
            src_fix[s]+=1
            if d<1500 and altv<FE+150:   # on/at the airfield
                x['airport']+=1; ground_src[s]+=1; ground_fix+=1
                ground_by_hour[int((t-8*3600)//3600%24)]+=1   # PST hour (UTC-8 after 1 Nov 2026)
            if g: x['g']+=1
            fix_by_ring[(int(d//1852), 'gnd' if g else 'air')]+=1
ts.sort()
gaps=[b-a for a,b in zip(ts,ts[1:])]
print('files',len(files),'polls',polls,'ok',okp,'span_h',round((ts[-1]-ts[0])/3600,1),'median_poll_s',sorted(gaps)[len(gaps)//2])
print('first',ts[0],'last',ts[-1])
print('aircraft within 3nm <3000ft AGL:',len(ac))
print('source of fixes (3nm box):',src_fix.most_common())
print('source of fixes on airfield (<1.5km, <150ft AGL):',ground_src.most_common(), 'total',ground_fix)
onfield=[h for h,x in ac.items() if x['airport']>0]
print('aircraft seen on/at airfield:',len(onfield), ' with alt_baro=ground:',sum(1 for h in onfield if ac[h]['g']>0))
def bucket(xs):
    c=C.Counter()
    for h in xs:
        x=ac[h]; c['/'.join(sorted(x['t'])) or '(none)']+=1
    return c
print('TYPE MIX (all low aircraft):',bucket(ac).most_common(60))
print('TYPE MIX (on airfield):',bucket(onfield).most_common(60))
cat=C.Counter('/'.join(sorted(ac[h]['cat'])) or '(none)' for h in onfield); print('categories on field:',cat.most_common())
print('no registration:',sum(1 for h in onfield if not ac[h]['r']),' no type:',sum(1 for h in onfield if not ac[h]['t']),' no callsign:',sum(1 for h in onfield if not ac[h]['cs']))
print('non-ICAO/anon hex (~ prefix):',sum(1 for h in onfield if h.startswith('~')))
cs_is_reg=sum(1 for h in onfield if ac[h]['cs'] and ac[h]['r'] and any(c==r for c in ac[h]['cs'] for r in ac[h]['r']))
print('callsign == registration:',cs_is_reg)
srcmix=C.Counter(max(ac[h]['src'],key=ac[h]['src'].get) for h in onfield); print('dominant source per on-field aircraft:',srcmix.most_common())
print('dbFlags (1=mil,2=interesting,4=PIA,8=LADD):',C.Counter(ac[h]['dbFlags'] for h in onfield).most_common())
print('on-field fixes by local PST hour:',sorted(ground_by_hour.items()))
print('fixes by nm ring:',sorted(fix_by_ring.items()))
# operators: callsign prefixes that are ICAO 3-letter + digits
ops=C.Counter()
for h in onfield:
    for cs in ac[h]['cs']:
        if len(cs)>3 and cs[:3].isalpha() and cs[3:].isdigit(): ops[cs[:3]]+=1
print('ICAO-callsign operators on field:',ops.most_common(30))
json.dump({h:{k:(sorted(v) if isinstance(v,set) else v) for k,v in x.items()} for h,x in ac.items()},open(sys.argv[2],'w'),default=dict)
