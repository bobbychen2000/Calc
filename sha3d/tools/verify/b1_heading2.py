# For each identified SHA movement, the track angle at the fix used for M2 versus the bearing to/from ZSSS.
import csv, json, gzip, sys, os, math, collections
from datetime import datetime, timezone
cache = sys.argv[1]
SHA = (31.19784885, 121.3362899)
def brg(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c); dl = math.radians(d - b)
    x = math.sin(dl) * math.cos(p2); y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360
ad = lambda a, b: abs((a - b + 180) % 360 - 180)
ts = lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
FE = json.load(gzip.open(os.path.join(cache, 'routes_vrs', 'vrs_index.json.gz')))['airports']
days = {'2026-11-10': ('2026.11.09', '2026.11.10'), '2026-11-12': ('2026.11.11', '2026.11.12')}
tot = collections.Counter(); bad_sig = []; spans = []
for day, arch in days.items():
    idx = collections.defaultdict(list)
    for a in arch:
        d = json.load(gzip.open(os.path.join(cache, 'observed_elsewhere', 'scan', f'cs_{a}_prod.json.gz')))
        for f in d['flights']:
            if 'sha_route' not in f['why']: continue
            for seg in f['segs']:
                for p in seg: idx[f['icao']].append(p)
    for r in csv.DictReader(open(os.path.join(cache, 'observed_elsewhere', f'sha_observed_{day}.csv'))):
        if not r['method']: continue
        tot['n'] += 1
        role = r['role_at_ZSSS']
        t = ts(r['last_fix_utc'] if role == 'arr' else r['first_fix_utc'])
        cand = [p for p in idx[r['icao24']] if abs(p[0] - t) < 2]
        if not cand or not isinstance(cand[0][5], (int, float)):
            tot['no track at fix'] += 1; continue
        p = cand[0]
        b = brg(p[1], p[2], *SHA) if role == 'arr' else brg(*SHA, p[1], p[2])
        a = ad(p[5], b)
        if a > 90:
            tot[f'{role}: heading wrong way (>90 deg)'] += 1; import gzip as _g
            fe=FE.get(r['far_end_db']); dfe=None
            if fe:
                import math as _m
                R=6371.0; p1,p2=_m.radians(p[1]),_m.radians(fe[2]); dl=_m.radians(fe[3]-p[2]); dfe=round(2*R*_m.asin(_m.sqrt(_m.sin((p2-p1)/2)**2+_m.cos(p1)*_m.cos(p2)*_m.sin(dl/2)**2)))
            bad_sig.append((day, role, r['far_end_db'], round(a), float(r['sigma_min']), r['db_check'], 'alt', p[3], 'km_to_far_end', dfe, 'span_h', round((ts(r['last_fix_utc'])-ts(r['first_fix_utc']))/3600,1)))
        elif a > 45: tot[f'{role}: 45-90 deg'] += 1
        else: tot[f'{role}: <=45 deg'] += 1
        spans.append((ts(r['last_fix_utc']) - ts(r['first_fix_utc'])) / 3600)
for k, v in sorted(tot.items()): print(k, v)
print('wrong-way cases (day, role, far end, angle, sigma_min, db_check):')
for x in bad_sig: print('  ', x)
print('record span >4 h:', sum(s > 4 for s in spans), ' >3 h:', sum(s > 3 for s in spans))
