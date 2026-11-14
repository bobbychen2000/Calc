"""Own leave-one-route-out check of the M1 China air-time sigma (no code from tools/adsb).
Usage: python3 -I rv_m1loro.py <refs/cache>"""
import gzip, json, math, sys, statistics as st, collections
C = sys.argv[1]
A = json.load(gzip.open(f'{C}/routes_vrs/vrs_index.json.gz', 'rt'))['airports']
def gc(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371.0088*math.asin(min(1, math.sqrt(h)))
def theil_sen(x, y):
    # median of pairwise slopes (subsampled deterministically if large)
    n = len(x); sl = []
    step = max(1, n*(n-1)//2 // 200000)
    k = 0
    for i in range(n):
        for j in range(i+1, n):
            k += 1
            if k % step: continue
            if x[j] != x[i]: sl.append((y[j]-y[i])/(x[j]-x[i]))
    b = st.median(sl); a = st.median([yi - b*xi for xi, yi in zip(x, y)])
    return a, b
def ols(x, y):
    mx, my = st.fmean(x), st.fmean(y)
    b = sum((a-mx)*(c-my) for a, c in zip(x, y)) / sum((a-mx)**2 for a in x); return my - b*mx, b
for day, files in (('2026-11-10', ('2026.11.09', '2026.11.10')), ('2026-11-12', ('2026.11.11', '2026.11.12'))):
    cal = []
    seen = set()
    for fd in files:
        x = json.load(gzip.open(f'{C}/observed_elsewhere/scan/cs_{fd}_prod.json.gz', 'rt'))
        for f in x['flights']:
            if not (f.get('dep') and f.get('arr')): continue
            da, aa = f['dep']['ap'], f['arr']['ap']
            if da == aa or da not in A or aa not in A: continue
            a, b = A[da], A[aa]
            d = gc(a[2], a[3], b[2], b[3]); T = f['arr']['t'] - f['dep']['t']
            if d < 200 or T <= 0 or not (250 <= d/(T/3600) <= 1000): continue
            key = (f['icao'], round(f['dep']['t']))
            if key in seen: continue
            seen.add(key)
            if a[5] == 'CN' and b[5] == 'CN':
                cal.append((tuple(sorted((da, aa))), d, T))
    routes = collections.Counter(c[0] for c in cal)
    print(day, 'China calibration flights', len(cal), 'routes', len(routes), 'top', routes.most_common(4))
    for name, fit in (('Theil-Sen', theil_sen), ('OLS', ols)):
        a, b = fit([c[1] for c in cal], [c[2] for c in cal])
        ins = [c[2] - (a + b*c[1]) for c in cal]
        e = []
        for rt in routes:
            tr = [c for c in cal if c[0] != rt]
            if len(tr) < 10: continue
            a2, b2 = fit([c[1] for c in tr], [c[2] for c in tr])
            e += [c[2] - (a2 + b2*c[1]) for c in cal if c[0] == rt]
        print('  %-9s a %.0f s b %.2f s/km | in-sample sigma %.1f min | LORO n %d sigma %.1f min, median |e| %.1f, bias %+.1f min'
              % (name, a, b, 1.4826*st.median(abs(v) for v in ins)/60, len(e), 1.4826*st.median(abs(v) for v in e)/60,
                 st.median(abs(v) for v in e)/60, st.median(e)/60))
