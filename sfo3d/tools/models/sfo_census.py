#!/usr/bin/env python3
"""Who flies what at SFO: operator / brand / ICAO type census, for choosing liveries and models.

Sources
  1. SFO Air Traffic Landings Statistics (DataSF dataset fpux-q53t, https://data.sf.gov/d/fpux-q53t, licence ODC-PDDL 1.0):
     monthly landings by operating airline, published (marketing) airline and aircraft model, self-reported by airlines
     to SFO. Official and complete; the published-vs-operating split is exactly the brand-vs-callsign distinction.
  2. Our own ADS-B recorder (tools/live/record.py -> refs/cache/rec/*.jsonl.gz; adsb.fi + adsb.lol, 1 Hz, 40 nm) and the
     app snapshot (data/snapshot.js): observed airframes (registration, ICAO type, callsign) on the ground at SFO or below
     2500 ft within 8 km of the ARP.
  3. tools/models/out/regional_brands.json (tools/models/build_brands.py, US DOT BTS) to turn SKW/QXE/... airframes into
     their painted brand.

Usage: python3 tools/models/sfo_census.py [--months 12]   -> prints tables, writes tools/models/out/sfo_census.json
"""
import argparse, collections, json, math, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'sfo_census.json')
CACHE = os.path.join(ROOT, 'refs', 'cache', 'sfo')
ARP = (37.6188, -122.3754)   # FAA 5010 ARP (same constant as tools/live/record.py)
REG_OPS = {'SKW': 'OO', 'QXE': 'QX', 'RPA': 'YX', 'ENY': 'MQ', 'JIA': 'OH', 'EDV': '9E', 'ASH': 'YV', 'GJS': 'G7', 'UCA': 'C5', 'PDT': 'PT'}
BRAND_OF = {'UA': 'United Express', 'AA': 'American Eagle', 'DL': 'Delta Connection', 'AS': 'Alaska (regional)'}


def datasf(months):
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, 'landings_12m.json')
    if not os.path.exists(fn):
        q = urllib.parse.urlencode({'$limit': 50000, '$order': 'activity_period DESC'})
        open(fn, 'wb').write(urllib.request.urlopen(urllib.request.Request('https://data.sf.gov/resource/fpux-q53t.json?' + q,
                                                                          headers={'User-Agent': 'sfo-live-3d research'}), timeout=120).read())
    rows = json.load(open(fn))
    periods = sorted({r['activity_period'] for r in rows})[-months:]
    return [r for r in rows if r['activity_period'] in periods], periods


def dist_km(lat, lon):
    return 6371 * math.hypot(math.radians(lat - ARP[0]), math.radians(lon - ARP[1]) * math.cos(math.radians(ARP[0])))


def observed():
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
    seen = {}
    def take(a, src):
        lat, lon = a.get('lat'), a.get('lon')
        if lat is None or not a.get('r'): return
        alt = a.get('alt_baro'); d = dist_km(lat, lon)
        at_sfo = (alt == 'ground' and d < 3.5) or (isinstance(alt, (int, float)) and alt < 2500 and d < 8)
        if not at_sfo: return
        k = a['r']; e = seen.setdefault(k, dict(reg=k, type=a.get('t'), callsigns=set(), src=set()))
        if a.get('flight'): e['callsigns'].add(a['flight'].strip())
        e['src'].add(src)
    try:
        from recio import records
        for rec in records():
            d = rec.get('d') or {}
            for a in d.get('aircraft') or d.get('ac') or []: take(a, 'recorder')
    except Exception as e:
        print('recorder not read:', e)
    s = open(os.path.join(ROOT, 'data', 'snapshot.js')).read()
    snap = json.JSONDecoder().raw_decode(s[s.index('{'):])[0]
    for a in snap['ac']: take(a, 'snapshot')
    for e in seen.values(): e['callsigns'] = sorted(e['callsigns']); e['src'] = sorted(e['src'])
    return seen


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--months', type=int, default=12); a = ap.parse_args()
    rows, periods = datasf(a.months)
    pax = [r for r in rows if r.get('landing_aircraft_type') == 'Passenger']
    n = lambda r: int(float(r['landing_count']))
    pub = collections.Counter(); pair = collections.Counter(); model = collections.Counter(); pub_model = collections.defaultdict(collections.Counter)
    for r in pax:
        pub[r['published_airline']] += n(r); pair[(r['published_airline'], r['operating_airline'])] += n(r)
        model[r['aircraft_model']] += n(r); pub_model[(r['published_airline'], r['operating_airline'])][r['aircraft_model']] += n(r)
    tot = sum(pub.values())
    print(f'DataSF fpux-q53t, {periods[0]}..{periods[-1]}: {tot} passenger landings')
    print('\nPublished (brand) airline            landings  share   operating airline -> models')
    for (p, o), v in sorted(pair.items(), key=lambda kv: -kv[1])[:45]:
        print(f'  {p[:34]:34s} {v:7d} {100 * v / tot:5.1f}%   {o[:26]:26s} {dict(pub_model[(p, o)].most_common(6))}')
    print('\nAircraft model (SFO coding)        landings')
    for m, v in model.most_common(40): print(f'  {m:10s} {v:7d} {100 * v / tot:5.1f}%')
    brands = {}
    bp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'regional_brands.json')
    if os.path.exists(bp): brands = json.load(open(bp))['tails']
    obs = observed()
    print(f'\nObserved at SFO in recorder + snapshot: {len(obs)} airframes')
    by = collections.Counter()
    for e in obs.values():
        cs = e['callsigns'][0] if e['callsigns'] else ''
        op = cs[:3] if re.match(r'^[A-Z]{3}\d', cs) else '?'
        b = brands.get(e['reg'])
        brand = BRAND_OF.get(b['brand'], b['brand']) if b and op in REG_OPS else op
        e['operator'] = op; e['brand'] = brand
        by[(brand, e['type'])] += 1
    for k, v in by.most_common(): print(f'  {str(k[0]):18s} {str(k[1]):6s} {v}')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(dict(datasf=dict(dataset='https://data.sf.gov/d/fpux-q53t', licence='ODC-PDDL-1.0', periods=periods, passenger_landings=tot,
                               by_pair=[dict(published=p, operating=o, landings=v, models=dict(pub_model[(p, o)])) for (p, o), v in pair.most_common()],
                               by_model=dict(model.most_common())),
                   observed=sorted(obs.values(), key=lambda e: e['reg'])), open(OUT, 'w'), indent=1)
    print('->', os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
