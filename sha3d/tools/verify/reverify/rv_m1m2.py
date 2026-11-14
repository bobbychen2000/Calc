"""Cross-check M1 vs M2 where both exist: is |M1-M2| consistent with the stated sigmas?"""
import json, sys, math, statistics as st, collections
D = sys.argv[1]
SHA = (31.19785, 121.33629)
def brg(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    y = math.sin(lo2-lo1)*math.cos(la2); x = math.cos(la1)*math.sin(la2)-math.sin(la1)*math.cos(la2)*math.cos(lo2-lo1)
    return (math.degrees(math.atan2(y, x))+360) % 360
for day in ('2026-11-10', '2026-11-12'):
    m = json.load(open(f'{D}/sha_observed_{day}.json'))['movements']
    rows = []
    for x in m:
        if x['pick'] and 'M1' in x['est'] and 'M2' in x['est']:
            e1, e2 = x['est']['M1'], x['est']['M2']
            d = (e1['t'] - e2['t']) / 60
            s = math.hypot(e1['sigma_s'], e2['sigma_s']) / 60
            fx = x['segs'][0][0] if x['role'] == 'dep' else x['segs'][-1][-1]
            want = brg(SHA, (fx[1], fx[2])) if x['role'] == 'dep' else brg((fx[1], fx[2]), SHA)
            off = abs((fx[5] - want + 180) % 360 - 180) if fx[5] is not None else None
            rows.append((x['role'], x['far'], d, s, off, x['pick']))
    z = [abs(r[2]) / r[3] for r in rows]
    print(day, 'n', len(rows), 'median |M1-M2| %.1f min' % st.median(abs(r[2]) for r in rows),
          'share |d|<=1 comb sigma %.0f %%' % (100*sum(1 for v in z if v <= 1)/len(z)),
          '<=2: %.0f %%' % (100*sum(1 for v in z if v <= 2)/len(z)))
    by = collections.defaultdict(list)
    for r in rows: by[(r[0], r[1])].append(r[2])
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1]))[:8]:
        print('   ', k, 'n', len(v), 'median M1-M2 %+.1f' % st.median(v), 'range %+.0f..%+.0f' % (min(v), max(v)))
    wr = [r for r in rows if r[4] is not None and r[4] > 90]
    print('  >90 deg cases: M1-M2 (min), comb sigma', [(round(r[2], 1), round(r[3], 1), r[5]) for r in wr])
