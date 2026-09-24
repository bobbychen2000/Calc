#!/usr/bin/env python3
"""Registration -> marketing brand (livery) table for US regional airframes, from official US DOT data.

Why: at SFO the callsign does not tell the livery. SkyWest (SKW) flies United Express, Alaska, Delta Connection and
American Eagle airframes under its own SKW callsign; Republic (RPA), Mesa (ASH), Envoy (ENY), PSA (JIA), Piedmont (PDT),
Endeavor (EDV) and Horizon (QXE) likewise fly for their partners. Each airframe is painted for one partner, so the
livery follows the registration, not the flight.

Source (observed): US DOT / BTS "Marketing Carrier On-Time Performance (Beginning January 2018)", monthly files
  https://transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_<YYYY>_<M>.zip
  (field definitions: https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGK ; US Government work, public domain).
  Columns used: Marketing_Airline_Network, IATA_Code_Operating_Airline, Tail_Number, Origin, Dest.
  Every flight row carries the tail number and the marketing network it was sold under; for regional operators the
  network is the brand painted on the aircraft (e.g. OO + UA = United Express).
Cross-checks: FAA Releasable Aircraft Database (https://registry.faa.gov/database/ReleasableAircraft.zip) for
  manufacturer / model / registered owner; SFO Air Traffic Landings Statistics (DataSF fpux-q53t, PDDL) for the
  operating-vs-published airline pairs that actually occur at SFO.

Types: FAA model CL-600-2C11 = "Regional Jet Series 550" (CRJ550; FAA TCDS A21EA) - a 50-seat CRJ700 conversion.
Output: tools/models/out/regional_brands.json
  { "source": ..., "months": [...], "tails": { "N510SY": {"op": "OO", "brand": "AA", "share": 1.0, "n": 212, "sfo": 31,
     "type": "E175", "owner": "SKYWEST AIRLINES INC"} ... }, "series": [ {operator, type, pattern, brand, n, first, last} ] }
  'series' rules are INFERRED from the observed tails (contiguous registration blocks with a single brand) and are only
  a fallback for airframes not seen in the BTS months (new deliveries, re-assignments).

Usage: python3 tools/models/build_brands.py [YYYY_M ...]   (downloads missing months into refs/cache/bts/)
"""
import csv, collections, io, json, os, re, sys, urllib.request, zipfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CACHE = os.path.join(ROOT, 'refs', 'cache', 'bts')
FAA = os.path.join(ROOT, 'refs', 'cache', 'faa')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'regional_brands.json')
URL = 'https://transtats.bts.gov/PREZIP/On_Time_Marketing_Carrier_On_Time_Performance_Beginning_January_2018_{}.zip'
REGIONALS = {'OO': 'SkyWest', 'QX': 'Horizon', 'YX': 'Republic', 'MQ': 'Envoy', 'OH': 'PSA', '9E': 'Endeavor', 'YV': 'Mesa',
             'G7': 'GoJet', 'C5': 'CommuteAir', 'PT': 'Piedmont', 'ZW': 'Air Wisconsin'}
BRAND = {'UA': 'United Express', 'AA': 'American Eagle', 'DL': 'Delta Connection', 'AS': 'Alaska (regional)'}


def month_rows(ym):
    zp = os.path.join(CACHE, f'mkt_{ym}.zip')
    if not os.path.exists(zp):
        os.makedirs(CACHE, exist_ok=True)
        req = urllib.request.Request(URL.format(ym), headers={'User-Agent': 'sfo-live-3d research'})
        open(zp, 'wb').write(urllib.request.urlopen(req, timeout=300).read())
    with zipfile.ZipFile(zp) as z:
        name = [n for n in z.namelist() if n.endswith('.csv')][0]
        with z.open(name) as fh:
            r = csv.reader(io.TextIOWrapper(fh, encoding='utf-8', newline=''))
            h = [x.strip() for x in next(r)]
            ix = {k: h.index(k) for k in ('Marketing_Airline_Network', 'IATA_Code_Operating_Airline', 'Tail_Number', 'Origin', 'Dest')}
            for row in r:
                yield row[ix['IATA_Code_Operating_Airline']], row[ix['Tail_Number']], row[ix['Marketing_Airline_Network']], row[ix['Origin']], row[ix['Dest']]


def faa_models():
    """N-number -> (short type, FAA model, owner) from the FAA releasable database (MASTER + ACFTREF)."""
    ref = {}
    for r in csv.reader(open(os.path.join(FAA, 'ACFTREF.txt'), encoding='utf-8-sig')):
        ref[r[0].strip()] = (r[1].strip(), r[2].strip())
    out = {}
    for r in csv.reader(open(os.path.join(FAA, 'MASTER.txt'), encoding='utf-8-sig')):
        if r[0] == 'N-NUMBER': continue
        mfr, mdl = ref.get(r[2].strip(), ('', ''))
        t = ('E175' if '170-200' in mdl else 'E170' if '170-100' in mdl else 'E145' if re.search(r'EMB-145|ERJ ?145|135', mdl) else
             'CRJ2' if '2B19' in mdl else 'CRJ7' if '2C10' in mdl else 'CRJ550' if '2C11' in mdl else
             'CRJ9' if '2D24' in mdl else 'CRJX' if '2E25' in mdl else mdl)
        out['N' + r[0].strip()] = (t, f'{mfr} {mdl}'.strip(), r[6].strip())
    return out


def series_rules(tails):
    """Contiguous registration blocks (same prefix digit count and suffix letters) with a single observed brand."""
    groups = collections.defaultdict(list)
    for n, t in tails.items():
        m = re.match(r'N(\d+)([A-Z]*)$', n)
        if not m: continue
        groups[(t['op'], t.get('type', ''), len(m.group(1)), m.group(2))].append((int(m.group(1)), n, t['brand']))
    rules = []
    for (op, typ, nd, suf), items in groups.items():
        items.sort(); run = [items[0]]
        for it in items[1:] + [None]:
            if it and it[2] == run[-1][2]:
                run.append(it); continue
            rules.append(dict(operator=op, type=typ, pattern=f'N{"#" * nd}{suf}', brand=run[0][2], n=len(run), first=run[0][1], last=run[-1][1]))
            if it: run = [it]
    return sorted(rules, key=lambda r: (r['operator'], r['pattern'], r['first']))


def main():
    months = sys.argv[1:] or ['2026_5', '2026_6', '2026_7']
    counts = collections.defaultdict(collections.Counter); sfo = collections.Counter()
    for ym in months:
        for op, tail, mkt, o, d in month_rows(ym):
            if op in REGIONALS and tail:
                counts[(op, tail)][mkt] += 1
                if o == 'SFO' or d == 'SFO': sfo[(op, tail)] += 1
    faa = faa_models() if os.path.exists(os.path.join(FAA, 'MASTER.txt')) else {}
    tails = {}
    for (op, tail), c in counts.items():
        brand, n = c.most_common(1)[0]; tot = sum(c.values())
        t = dict(op=op, brand=brand, share=round(n / tot, 3), n=tot, sfo=sfo.get((op, tail), 0))
        if tail in faa: t.update(type=faa[tail][0], faa_model=faa[tail][1], owner=faa[tail][2])
        if len(c) > 1: t['other'] = dict(c)
        tails[tail] = t
    res = dict(source='US DOT BTS Marketing Carrier On-Time Performance (Beginning January 2018), public domain; '
                      'FAA Releasable Aircraft Database for type/owner', months=months, brands=BRAND, operators=REGIONALS,
               tails=dict(sorted(tails.items())), series=series_rules(tails))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, 'w'), indent=0, separators=(',', ':'))
    mixed = [k for k, v in tails.items() if v['share'] < 1]
    print(f'{len(tails)} regional tails, {len(mixed)} flew for more than one network: {mixed[:10]}')
    for r in res['series']:
        if r['n'] >= 3: print(f"  {r['operator']} {r['type']:6s} {r['pattern']:8s} {r['first']}..{r['last']:8s} -> {r['brand']} ({r['n']})")
    print('->', os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
