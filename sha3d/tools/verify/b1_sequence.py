# Physical plausibility of inferred SHA times along each aircraft's day (no new data; local per-flight tables only)
import csv, sys, os, json, gzip, math, collections, statistics
from datetime import datetime
cache = sys.argv[1]
A = json.load(gzip.open(os.path.join(cache, 'routes_vrs', 'vrs_index.json.gz')))['airports']
def gc(a, b, c, d):
    R = 6371.0; p1, p2 = math.radians(a), math.radians(c); dl = math.radians(d - b)
    return 2 * R * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
SHA = (31.19784885, 121.3362899)
air = lambda km: (673 + 5.684 * km) / 60     # B1's own China air-time fit (min)
ts = lambda s: datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').timestamp() / 60
tot = collections.Counter(); turn = []; ex = []
for day in ('2026-11-10', '2026-11-12'):
    rows = [r for r in csv.DictReader(open(os.path.join(cache, 'observed_elsewhere', f'sha_observed_{day}.csv'))) if r['method']]
    by = collections.defaultdict(list)
    for r in rows: by[r['icao24']].append(r)
    for h, ms in by.items():
        ms.sort(key=lambda r: ts(r['sha_time_utc_inf']))
        for a, b in zip(ms, ms[1:]):
            g = ts(b['sha_time_utc_inf']) - ts(a['sha_time_utc_inf'])
            s = math.hypot(float(a['sigma_min']), float(b['sigma_min']))
            k = a['role_at_ZSSS'] + '>' + b['role_at_ZSSS']
            tot[k] += 1
            if k == 'arr>dep':
                turn.append(g)
                if g < 25: tot['arr>dep gap<25min'] += 1
                if g < 25 - 2 * s: tot['arr>dep gap<25min-2sigma'] += 1
            if k == 'dep>arr':
                fa, fb = A.get(a['far_end_db']), A.get(b['far_end_db'])
                if not fa or not fb: continue
                need = air(gc(*SHA, fa[2], fa[3])) + 30 + air(gc(fa[2], fa[3], fb[2], fb[3])) + (air(gc(fb[2], fb[3], *SHA)) if a['far_end_db'] != b['far_end_db'] else 0)
                if a['far_end_db'] != b['far_end_db']:
                    need = air(gc(*SHA, fa[2], fa[3])) + 30 + air(gc(fa[2], fa[3], fb[2], fb[3])) + 30 + air(gc(fb[2], fb[3], *SHA))
                else:
                    need = 2 * air(gc(*SHA, fa[2], fa[3])) + 30
                tot['dep>arr checked'] += 1
                if g < need - 2 * s:
                    tot['dep>arr impossible (beyond 2 sigma)'] += 1
                    ex.append((day, round(g), round(need), a['far_end_db'], b['far_end_db'], round(s)))
                elif g < need:
                    tot['dep>arr tight (within 2 sigma)'] += 1
for k, v in sorted(tot.items()): print(k, v)
print('arr>dep turn min: n', len(turn), 'P5', sorted(turn)[len(turn)//20] if turn else None, 'min', min(turn) if turn else None, 'median', statistics.median(turn) if turn else None)
print('impossible examples (gap, needed, far ends, combined sigma):', ex[:12])
