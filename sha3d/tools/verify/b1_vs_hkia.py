import json, csv, sys, os, re, collections
cache = sys.argv[1]
IATA2ICAO = {'CX': 'CPA', 'MU': 'CES', 'FM': 'CSH', 'HX': 'CRK', 'HO': 'DKH', '9C': 'CQH', 'CA': 'CCA', 'CZ': 'CSN', 'KA': 'HDA', 'UO': 'HKE', 'NX': 'AMU', 'HU': 'CHH', 'MF': 'CXA', 'ZH': 'CSZ'}
hk = {}
for fn, arr in (('hkia_2026-11-13_arrival-false.json', False), ('hkia_2026-11-13_arrival-true.json', True)):
    for day in json.load(open(os.path.join(cache, 'schedules_open', 'hkia', fn))):
        for e in day['list']:
            ports = e.get('origin' if arr else 'destination') or []
            for p in ports:
                if p in ('SHA', 'PVG'):
                    a, n = e['flight'][0]['no'].split()
                    hk[IATA2ICAO.get(a, a) + str(int(n))] = (p, 'arr_HKG' if arr else 'dep_HKG', e['time'], e.get('status'))
print('HKIA SHA callsigns 13 Nov:', sorted(k for k, v in hk.items() if v[0] == 'SHA'))
for day in ('2026-11-10', '2026-11-12'):
    rows = [r for r in csv.DictReader(open(os.path.join(cache, 'observed_elsewhere', f'sha_observed_{day}.csv'))) if r['method'] and r['far_end_db'] == 'VHHH']
    res = collections.Counter()
    for r in rows:
        h = hk.get(r['callsign'])
        res['in HKIA as ' + (h[0] if h else 'absent')] += 1
    hksha = {k for k, v in hk.items() if v[0] == 'SHA'}
    print(day, 'B1 VHHH rows', len(rows), dict(res), 'HKIA-SHA callsigns not identified by B1:', sorted(hksha - {r['callsign'] for r in rows}))
