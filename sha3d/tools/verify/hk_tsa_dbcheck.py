# Independent SHA-vs-PVG check of the VRS route DB against official far-end airport data (HKIA 13 Nov, TSA 14 Nov)
import json, gzip, sys, collections, re, os, csv
cache = sys.argv[1]
v = json.load(gzip.open(os.path.join(cache, 'routes_vrs', 'vrs_index.json.gz')))
R = v['routes']
IATA2ICAO = {'CX': 'CPA', 'MU': 'CES', 'FM': 'CSH', 'HX': 'CRK', 'HO': 'DKH', '9C': 'CQH', 'CA': 'CCA', 'CZ': 'CSN',
             'KA': 'HDA', 'UO': 'HKE', 'CI': 'CAL', 'BR': 'EVA', 'NX': 'AMU', 'ZH': 'CSZ', 'MF': 'CXA', 'HU': 'CHH',
             'B7': 'UIA', 'AE': 'MDA', 'JL': 'JAL', 'NH': 'ANA', 'KE': 'KAL', 'OZ': 'AAR', '3U': 'CSC'}
def cs_of(no):
    a, n = no.split()
    return IATA2ICAO.get(a, a) + str(int(re.sub(r'\D', '', n) or 0)) + re.sub(r'\d', '', n)
out = collections.Counter(); rows = []
for fn, arrflag in (('hkia_2026-11-13_arrival-false.json', False), ('hkia_2026-11-13_arrival-true.json', True)):
    D = json.load(open(os.path.join(cache, 'schedules_open', 'hkia', fn)))
    for day in D:
        for e in day['list']:
            ports = e.get('origin' if arrflag else 'destination') or []
            sh = [p for p in ports if p in ('SHA', 'PVG')]
            if not sh: continue
            # operating carrier = first flight number
            no = e['flight'][0]['no']; cs = cs_of(no)
            rt = R.get(cs, [None, None])[1]
            lab = None
            if rt:
                a = rt.split('-')
                lab = 'ZSSS' if 'ZSSS' in a and 'ZSPD' not in a else ('ZSPD' if 'ZSPD' in a and 'ZSSS' not in a else ('both' if 'ZSSS' in a else 'other:' + rt))
            truth = 'ZSSS' if sh[0] == 'SHA' else 'ZSPD'
            hk_in = 'VHHH' in (rt or '')
            res = 'not_in_db' if not rt else ('agree' if lab == truth else 'disagree')
            out[(truth, res)] += 1
            rows.append((day['date'], 'arr' if arrflag else 'dep', no, cs, sh[0], rt, res, e.get('status', '')))
print('HKIA 13 Nov (operating flight number, truth from HKIA origin/destination):')
for k, n in sorted(out.items()): print('  ', k, n)
for r in rows:
    if r[6] != 'agree': print('   non-agree:', r[:7])
# TSA (Taiwan OGDL) 14 Nov
out2 = collections.Counter(); seen=set()
for fn in ('tsa_intl_arr_2026-11-14.json', 'tsa_intl_dep_2026-11-14.json'):
    D = json.load(open(os.path.join(cache, 'schedules_open', 'tsa', fn)))
    L = D if isinstance(D, list) else next(x for x in D.values() if isinstance(x, list))
    if not out2: print('TSA keys', list(L[0].keys()))
    for e in L:
        s = json.dumps(e, ensure_ascii=False)
        if not re.search(r'SHA|PVG|上海|虹橋|浦東', s): continue
        out2['rows'] += 1
        seen.add(s[:400])
print('TSA rows mentioning Shanghai', out2['rows'])
for s in list(seen)[:3]: print('  ', s)
