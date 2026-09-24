"""Compare the runway ends the app uses (js/geo.js RWY_ENDS) with the FAA's own data and with OSM / X-Plane.

Sources (downloaded to refs/cache/xcheck/faa/, refs/cache/osm/, refs/cache/xplane/):
  FAA NASR 28-day subscription, cycle effective 2026-09-03, APT CSV:
    https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip -> APT_RWY_END.csv, APT_RWY.csv (ARPT_ID SFO)
    (fields per APT_CSV_DATA_STRUCTURE.csv in the same zip: LAT_DECIMAL/LONG_DECIMAL = runway end,
     LAT_DISPLACED_THR_DECIMAL/LONG_DISPLACED_THR_DECIMAL, DISPLACED_THR_LEN (ft), RWY_END_ELEV (ft), TRUE_ALIGNMENT,
     RWY_END_PSN_SOURCE/_DATE, TKOF_RUN_AVBL/TKOF_DIST_AVBL/ACLT_STOP_DIST_AVBL/LNDG_DIST_AVBL (ft))
  AirNav https://www.airnav.com/airport/KSFO ("FAA INFORMATION EFFECTIVE 03 SEPTEMBER 2026") - the page geo.js cites
  X-Plane Gateway apt.dat row 100 (runway end lat/lon, displaced threshold m, blast pad m)
  OSM aeroway=runway ways (extreme nodes along the FAA axis), aeroway=stopway ways
Distances: WGS-84 geodesic (pyproj), decomposed along / across the FAA runway axis (+along = toward the opposite end,
i.e. into the runway; +cross = right of the centreline looking from this end down the runway).
Writes refs/cache/xcheck/runways_result.json and refs/cache/xcheck/tables_runways.md.
Usage: python3 tools/xcheck/compare_runways.py
"""
import csv, io, json, math, os, re, zipfile
import xcommon as X

FAA = os.path.join(X.ROOT, 'refs', 'cache', 'xcheck', 'faa')
OUT = os.path.join(X.ROOT, 'refs', 'cache', 'xcheck')
PAIRS = {'10L': '28R', '28R': '10L', '10R': '28L', '28L': '10R', '1L': '19R', '19R': '1L', '1R': '19L', '19L': '1R'}


def nasr():
    z = zipfile.ZipFile(os.path.join(FAA, '03_Sep_2026_APT_CSV.zip'))
    ends = {}
    for r in csv.DictReader(io.TextIOWrapper(z.open('APT_RWY_END.csv'), encoding='latin-1')):
        if r['ARPT_ID'] != 'SFO': continue
        k = r['RWY_END_ID'].lstrip('0')
        f = lambda n: float(r[n]) if r[n] not in ('', None) else None
        ends[k] = {'lat': f('LAT_DECIMAL'), 'lon': f('LONG_DECIMAL'), 'elev_ft': f('RWY_END_ELEV'),
                   'dt_lat': f('LAT_DISPLACED_THR_DECIMAL'), 'dt_lon': f('LONG_DISPLACED_THR_DECIMAL'),
                   'dt_len_ft': f('DISPLACED_THR_LEN'), 'dt_elev_ft': f('DISPLACED_THR_ELEV'), 'tdze_ft': f('TDZ_ELEV'),
                   'true_align': f('TRUE_ALIGNMENT'), 'psn_src': r['RWY_END_PSN_SOURCE'], 'psn_date': r['RWY_END_PSN_DATE'],
                   'tora': f('TKOF_RUN_AVBL'), 'toda': f('TKOF_DIST_AVBL'), 'asda': f('ACLT_STOP_DIST_AVBL'),
                   'lda': f('LNDG_DIST_AVBL'), 'appr_lgt': r['APCH_LGT_SYSTEM_CODE'], 'eff': r['EFF_DATE'],
                   'dms': f"{r['RWY_END_LAT_DEG']}-{r['RWY_END_LAT_MIN']}-{r['RWY_END_LAT_SEC']}{r['RWY_END_LAT_HEMIS']} "
                          f"{r['RWY_END_LONG_DEG']}-{r['RWY_END_LONG_MIN']}-{r['RWY_END_LONG_SEC']}{r['RWY_END_LONG_HEMIS']}"}
    rwys = {}
    for r in csv.DictReader(io.TextIOWrapper(z.open('APT_RWY.csv'), encoding='latin-1')):
        if r['ARPT_ID'] != 'SFO': continue
        rwys[r['RWY_ID']] = {'len_ft': float(r['RWY_LEN']), 'wid_ft': float(r['RWY_WIDTH']), 'src': r['RWY_LEN_SOURCE'],
                             'date': r['LENGTH_SOURCE_DATE']}
    return ends, rwys


def airnav():
    fn = os.path.join(FAA, 'airnav_KSFO.txt')
    if not os.path.exists(fn): return {}, None
    t = open(fn).read().replace('\xa0', ' ')
    eff = re.search(r'FAA INFORMATION EFFECTIVE ([0-9A-Z ]+)', t)
    out = {}
    for m in re.finditer(r'RUNWAY (\w+)\s+RUNWAY (\w+)\s*\nLatitude:\s*(\d+)-([\d.]+)N(\d+)-([\d.]+)N\s*\nLongitude:\s*(\d+)-([\d.]+)W(\d+)-([\d.]+)W'
                         r'\s*\nElevation:\s*([\d.]+) ft\.([\d.]+) ft\.', t):
        a, b = m.group(1), m.group(2)
        out[a] = {'lat': int(m.group(3)) + float(m.group(4)) / 60, 'lon': -(int(m.group(7)) + float(m.group(8)) / 60), 'elev_ft': float(m.group(11))}
        out[b] = {'lat': int(m.group(5)) + float(m.group(6)) / 60, 'lon': -(int(m.group(9)) + float(m.group(10)) / 60), 'elev_ft': float(m.group(12))}
    for m in re.finditer(r'RUNWAY (\w+)\s+RUNWAY (\w+)[\s\S]*?Displaced threshold:\s*(no|[\d,]+ ft\.)(no|[\d,]+ ft\.)', t):
        for k, v in ((m.group(1), m.group(3)), (m.group(2), m.group(4))):
            if k in out and 'disp_ft' not in out[k]:
                out[k]['disp_ft'] = 0.0 if v == 'no' else float(v.replace(',', '').replace(' ft.', ''))
    return out, eff.group(1) if eff else None


def axis(ends, k):
    a, b = ends[k], ends[PAIRS[k]]
    az, _, L = X.GEOD.inv(a['lon'], a['lat'], b['lon'], b['lat'])
    return az, L


def off(ref, az, lat, lon):
    """along/cross (m) of (lat,lon) from ref (lat,lon) w.r.t. azimuth az"""
    a2, _, d = X.GEOD.inv(ref[1], ref[0], lon, lat)
    t = math.radians(a2 - az)
    return d * math.cos(t), d * math.sin(t)


def main():
    N, NR = nasr(); AN, an_eff = airnav(); G = X.rwy_ends_geojs()
    xp = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'xplane', 'ksfo_apt_parsed.json')))
    osm = json.load(open(os.path.join(X.ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')))
    XPE = {}
    for rw in xp['runways']:
        for e in rw['ends']: XPE[e['id'].lstrip('0')] = e
    rows = []
    for k in ['10L', '28R', '10R', '28L', '1L', '19R', '1R', '19L']:
        n = N[k]; az, L = axis(N, k); ref = (n['lat'], n['lon'])
        r = {'end': k, 'nasr': n, 'az_true': round(az % 360, 2), 'len_geod_m': round(L, 1)}
        # geo.js (the app)
        g = G[k]; r['geojs'] = {**g, 'along_cross': [round(v, 2) for v in off(ref, az, g['lat'], g['lon'])],
                                'elev_diff_ft': round(g['elev_ft'] - n['elev_ft'], 2), 'disp_diff_ft': g['disp_ft'] - (n['dt_len_ft'] or 0)}
        # app's threshold: end + disp along the app's (planar) axis -> compare with NASR displaced threshold point
        if n['dt_lat'] is not None:
            gp = X.ll_to_world(g['lat'], g['lon']); go = X.ll_to_world(G[PAIRS[k]]['lat'], G[PAIRS[k]]['lon'])
            Lp = math.dist(gp, go); u = ((go[0] - gp[0]) / Lp, (go[1] - gp[1]) / Lp); d = g['disp_ft'] * X.FT
            tlat, tlon = X.world_to_ll(gp[0] + u[0] * d, gp[1] + u[1] * d)
            r['geojs_thr_vs_nasr_dt'] = [round(v, 2) for v in off((n['dt_lat'], n['dt_lon']), az, tlat, tlon)]
            r['nasr_dt_from_end'] = [round(v, 2) for v in off(ref, az, n['dt_lat'], n['dt_lon'])]
        if k in AN:
            a = AN[k]; r['airnav'] = {**a, 'along_cross': [round(v, 2) for v in off(ref, az, a['lat'], a['lon'])]}
        if k in XPE:
            e = XPE[k]; r['xplane'] = {**e, 'along_cross': [round(v, 2) for v in off(ref, az, e['lat'], e['lon'])],
                                       'disp_ft_equiv': round(e['disp_m'] / X.FT, 0)}
        rows.append(r)
    # OSM runway ways: extreme nodes along each FAA axis
    by = {}
    for w in osm['runways']:
        ref = (w['ref'] or '').replace('01', '1').replace('/0', '/')
        closed = len(w['pts']) > 3 and w['pts'][0] == w['pts'][-1]
        by.setdefault(ref, []).append({**w, 'closed': closed})
    osm_rows = {}
    for ref, ws in by.items():
        a, b = ref.split('/')
        if a not in N: continue
        az, L = axis(N, a); r0 = (N[a]['lat'], N[a]['lon'])
        pts = [(p, off(r0, az, *p)) for w in ws if not w['closed'] for p in w['pts']]
        if not pts: continue
        pa = min(pts, key=lambda t: t[1][0]); pb = max(pts, key=lambda t: t[1][0])
        osm_rows[a] = {'along_cross': [round(v, 2) for v in off(r0, az, *pa[0])], 'ways': [w['id'] for w in ws], 'tag_length': [w['tags'].get('length') for w in ws]}
        azb, _ = axis(N, b); rb = (N[b]['lat'], N[b]['lon'])
        osm_rows[b] = {'along_cross': [round(v, 2) for v in off(rb, azb, *pb[0])], 'ways': [w['id'] for w in ws], 'tag_length': [w['tags'].get('length') for w in ws]}
    for r in rows:
        if r['end'] in osm_rows: r['osm'] = osm_rows[r['end']]
    # OSM stopways: which end, length, offset of the outer node
    stop = []
    for w in osm['stopways']:
        p0, p1 = w['pts'][0], w['pts'][-1]
        best = None
        for k, n in N.items():
            d0 = X.geod_dist(n['lat'], n['lon'], *p0); d1 = X.geod_dist(n['lat'], n['lon'], *p1)
            d = min(d0, d1)
            if best is None or d < best[0]: best = (d, k, p0 if d0 < d1 else p1, p1 if d0 < d1 else p0)
        az, _ = axis(N, best[1])
        inner = off((N[best[1]]['lat'], N[best[1]]['lon']), az, *best[2]); outer = off((N[best[1]]['lat'], N[best[1]]['lon']), az, *best[3])
        stop.append({'end': best[1], 'id': w['id'], 'len_m': round(X.geod_dist(*p0, *p1), 1), 'inner_along_cross': [round(v, 1) for v in inner],
                     'outer_along': round(outer[0], 1), 'tags': w['tags']})
    # app runway lengths (planar geo.js frame) vs geodesic vs NASR published
    lens = []
    for a, b in X.pairs_of_runways():
        ga, gb = G[a], G[b]
        planar = math.dist(X.ll_to_world(ga['lat'], ga['lon']), X.ll_to_world(gb['lat'], gb['lon']))
        geod = X.geod_dist(N[a]['lat'], N[a]['lon'], N[b]['lat'], N[b]['lon'])
        rid = ('0' + a if len(a) == 2 and a[0] == '1' and a[1] in 'LR' else a) + '/' + b
        pub = NR.get(rid, {}).get('len_ft')
        lens.append({'rwy': f'{a}/{b}', 'nasr_len_ft': pub, 'nasr_len_m': round(pub * X.FT, 1) if pub else None,
                     'geod_nasr_ends_m': round(geod, 1), 'app_planar_m': round(planar, 1),
                     'app_minus_geod_m': round(planar - geod, 2)})
    res = {'nasr_eff': N['10L']['eff'], 'airnav_eff': an_eff, 'rows': rows, 'stopways': stop, 'lengths': lens,
           'xp_header_elev_ft': xp['header']['elev_ft']}
    json.dump(res, open(os.path.join(OUT, 'runways_result.json'), 'w'), indent=1)
    write_tables(res)
    print(open(os.path.join(OUT, 'tables_runways.md')).read())


def ac(v):
    return '—' if v is None else f'{v[0]:+.1f} / {v[1]:+.1f}'


def write_tables(res):
    L = ['<!--BEGIN:runway_table-->',
         '| End | FAA NASR end (DMS) | elev ft | disp ft | geo.js − NASR (along / cross m) | AirNav − NASR | geo.js elev − NASR ft | '
         'X-Plane end − NASR | X-Plane disp m (ft) / blast pad m | OSM runway way end − NASR |',
         '|---|---|---|---|---|---|---|---|---|---|']
    for r in res['rows']:
        n = r['nasr']; xp = r.get('xplane')
        L.append('| ' + ' | '.join([r['end'], n['dms'], f"{n['elev_ft']}", f"{int(n['dt_len_ft'] or 0)}", ac(r['geojs']['along_cross']),
                                    ac(r.get('airnav', {}).get('along_cross')), f"{r['geojs']['elev_diff_ft']:+.1f}",
                                    ac(xp['along_cross']) if xp else '—',
                                    f"{xp['disp_m']:.0f} ({xp['disp_ft_equiv']:.0f}) / {xp['blastpad_m']:.0f}" if xp else '—',
                                    ac(r.get('osm', {}).get('along_cross'))]) + ' |')
    L.append('<!--END:runway_table-->')
    L.append('<!--BEGIN:threshold_table-->')
    L.append('| End | NASR displaced threshold: along / cross from runway end (m) | app threshold (end + disp along geo.js axis) − NASR DT (along / cross m) | NASR TORA / TODA / ASDA / LDA ft | position source, date |')
    L.append('|---|---|---|---|---|')
    for r in res['rows']:
        n = r['nasr']
        if n['dt_lat'] is None: continue
        L.append(f"| {r['end']} | {ac(r['nasr_dt_from_end'])} | {ac(r['geojs_thr_vs_nasr_dt'])} | {n['tora']:.0f} / {n['toda']:.0f} / {n['asda']:.0f} / {n['lda']:.0f} | {n['psn_src']}, {n['psn_date']} |")
    L.append('<!--END:threshold_table-->')
    L.append('<!--BEGIN:length_table-->')
    L.append('| Runway | NASR published length | geodesic between NASR ends | app (geo.js planar frame) | app − geodesic |')
    L.append('|---|---|---|---|---|')
    for l in res['lengths']:
        L.append(f"| {l['rwy']} | {l['nasr_len_ft']:.0f} ft = {l['nasr_len_m']} m | {l['geod_nasr_ends_m']} m | {l['app_planar_m']} m | {l['app_minus_geod_m']:+.2f} m |")
    L.append('<!--END:length_table-->')
    L.append('<!--BEGIN:stopway_table-->')
    L.append('| OSM way | nearest FAA end | length m | inner node along / cross from the end (m) | outer node along (m) | tags |')
    L.append('|---|---|---|---|---|---|')
    for s in sorted(res['stopways'], key=lambda s: s['end']):
        t = ', '.join(f'{k}={v}' for k, v in s['tags'].items() if k != 'aeroway')
        L.append(f"| way {s['id']} | {s['end']} | {s['len_m']} | {s['inner_along_cross'][0]:+.1f} / {s['inner_along_cross'][1]:+.1f} | {s['outer_along']:+.1f} | {t} |")
    L.append('<!--END:stopway_table-->')
    open(os.path.join(OUT, 'tables_runways.md'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
