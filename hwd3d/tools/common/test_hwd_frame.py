#!/usr/bin/env python3
"""Verify the HWD world frame: js/geo.js == tools/common/hwd_frame.py, and both against pyproj and the FAA NASR rows.

Forked from sfo3d/tools/test_geo_frame.py @ a967f9b. Changed: imports hwd_frame; SFO s/t-grid and legacy-frame checks
dropped; added UTM 10N, runway axis / profile, NASR transcription, runway length vs NASR RWY_LEN, displaced threshold
and geodesic bearing checks.

Checks (exit status 1 if any fails):
  1. JS == Python on 60 lat/lon points and 60 world points (llToWorld, worldToLL, wgs84ToWorld, worldToWgs84,
     llToUtm10, utm10ToLL, utm10ToWorld, worldToUtm10, rwyAlongAcross, rwyToWorld, rwySurfaceY), tolerance 1 mm.
  2. Both == the pyproj topocentric pipeline (GRS80 ENU at the ARP) to 1 mm; numpy twins == scalar functions.
  3. UTM 10N (closed-form Krueger series, JS and Python) == pyproj EPSG:4269 <-> EPSG:26910 to 1 mm, both ways.
  4. Constants == FAA NASR rows (refs/cache/faa/nasr_2026-10-29_HWD.json): ARP, field elevation, the 4 runway ends,
     the 2 runways (Python and JS); NASR DMS == NASR decimals to 1 cm.
  5. Runway ends: lat/lon -> world -> lat/lon round trip < 1 cm (JS and Python).
  6. Runway lengths: plane == geodesic (pyproj.Geod GRS80) to 5 cm; geodesic vs NASR RWY_LEN reported in ft (< 1 ft);
     stored geodesic bearings == pyproj to 1e-4 deg and within 0.5 deg of NASR TRUE_ALIGNMENT.
  7. Displaced thresholds: surveyed NASR position lies on the runway axis (< 5 cm across) and at DISPLACED_THR_LEN
     (< 1 ft along).
  8. WGS 84 offset == pyproj NAD83(2011) -> WGS 84 (G2296) (EPSG:6319 -> EPSG:10605) at the frame epoch to < 2 mm at
     the ARP and < 1 cm over the AOI; PROJ's default EPSG:4269 -> EPSG:4326 shown to be a null transformation.
Usage: python3 tools/common/test_hwd_frame.py            (needs node >= 18 on PATH)
"""
import json, math, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import hwd_frame as G

NASR = os.path.join(ROOT, 'refs', 'cache', 'faa', 'nasr_2026-10-29_HWD.json')
random.seed(20261112)
LL = [(G.ARP_LAT + random.uniform(-0.05, 0.05), G.ARP_LON + random.uniform(-0.06, 0.06)) for _ in range(50)]
LL += [(G.ARP_LAT + random.uniform(-0.45, 0.45), G.ARP_LON + random.uniform(-0.55, 0.55)) for _ in range(10)]
WP = [(random.uniform(-3000, 3000), random.uniform(-3000, 3000)) for _ in range(50)]
WP += [(random.uniform(-40000, 40000), random.uniform(-40000, 40000)) for _ in range(10)]
E0, N0 = G.ll_to_utm10(G.ARP_LAT, G.ARP_LON)
UT = [(E0 + random.uniform(-6000, 6000), N0 + random.uniform(-6000, 6000)) for _ in range(50)]
UT += [(E0 + random.uniform(-50000, 50000), N0 + random.uniform(-50000, 50000)) for _ in range(10)]
RA = [(random.choice(list(G.RWY_ENDS)), random.uniform(-300, 2000), random.uniform(-200, 200)) for _ in range(60)]
JS = r"""
const G = await import(process.argv[1]);
const inp = JSON.parse(process.argv[2]);
const xz = w => [w[0], w[2]];
const out = {
  llToWorld: inp.ll.map(([la, lo]) => xz(G.llToWorld(la, lo, 0))),
  wgs84ToWorld: inp.ll.map(([la, lo]) => xz(G.wgs84ToWorld(la, lo, 0))),
  worldToLL: inp.w.map(([x, z]) => G.worldToLL(x, z)),
  worldToWgs84: inp.w.map(([x, z]) => G.worldToWgs84(x, z)),
  llToUtm10: inp.ll.map(([la, lo]) => G.llToUtm10(la, lo)),
  utm10ToLL: inp.ut.map(([e, n]) => G.utm10ToLL(e, n)),
  utm10ToWorld: inp.ut.map(([e, n]) => xz(G.utm10ToWorld(e, n))),
  worldToUtm10: inp.w.map(([x, z]) => G.worldToUtm10(x, z)),
  rwyAlongAcross: inp.ra.map(([k, a, c], i) => G.rwyAlongAcross(k, inp.w[i][0] / 10, inp.w[i][1] / 10)),
  rwyToWorld: inp.ra.map(([k, a, c]) => xz(G.rwyToWorld(k, a, c))),
  rwySurfaceY: inp.ra.map(([k, a, c]) => G.rwySurfaceY(k, a)),
  ends: Object.fromEntries(Object.entries(G.RWY_ENDS).map(([k, E]) => { const w = G.llToWorld(E.lat, E.lon); const ll = G.worldToLL(w[0], w[2]); return [k, { E, w: [w[0], w[2]], back: ll, thr: xz(G.thrWorld(k)), disp: G.thrDispM(k), prof: G.rwyProfile(k) }]; })),
  runways: G.RUNWAYS, rwyData: G.RWY_DATA, byEnd: Object.fromEntries(Object.keys(G.RWY_ENDS).map(k => [k, G.runwayByEnd(k)])),
  datum: G.DATUM, frame: G.FRAME_ID, arp: G.ARP, groundY: G.GROUND_Y, fieldFt: G.FIELD_ELEV_FT,
};
console.log(JSON.stringify(out));
"""


def run_js():
    src = os.path.join(ROOT, 'js', 'geo.js')
    r = subprocess.run(['node', '--input-type=module', '-e', JS, 'file://' + src,
                        json.dumps({'ll': LL, 'w': WP, 'ut': UT, 'ra': RA})], capture_output=True, text=True, cwd=ROOT)
    if r.returncode: print(r.stderr); raise SystemExit('node failed')
    return json.loads(r.stdout)


def main():
    import numpy as np, pyproj
    J = run_js(); fails = []
    def check(name, val, tol, unit='m'):
        ok = val <= tol; print(f'  {"OK " if ok else "FAIL"} {name}: {val:.3g} {unit} (tol {tol:g})')
        if not ok: fails.append(name)
    geod = pyproj.Geod(ellps='GRS80')
    gm = lambda a, b: geod.inv(a[1], a[0], b[1], b[0])[2]          # metres between two (lat, lon)
    print(f'pyproj {pyproj.__version__} / PROJ {pyproj.proj_version_str}; node {subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()}')
    print(f'frame: js {J["frame"]}  py {G.FRAME_ID}; ARP js {J["arp"]} py ({G.ARP_LAT}, {G.ARP_LON})')
    if J['frame'] != G.FRAME_ID or (J['arp']['lat'], J['arp']['lon']) != (G.ARP_LAT, G.ARP_LON): fails.append('frame id / ARP')
    # 1. JS == Python
    print(f'1. js/geo.js vs tools/common/hwd_frame.py ({len(LL)} lat/lon, {len(WP)} world, {len(UT)} UTM, {len(RA)} runway points)')
    d = max(math.dist(J['llToWorld'][i], G.ll_to_world(*LL[i])) for i in range(len(LL))); check('llToWorld', d, 1e-3)
    d = max(math.dist(J['wgs84ToWorld'][i], G.wgs84_to_world(*LL[i])) for i in range(len(LL))); check('wgs84ToWorld', d, 1e-3)
    d = max(gm(J['worldToLL'][i], G.world_to_ll(*WP[i])) for i in range(len(WP))); check('worldToLL (geodesic metres)', d, 1e-3)
    d = max(gm(J['worldToWgs84'][i], G.world_to_wgs84(*WP[i])) for i in range(len(WP))); check('worldToWgs84 (geodesic metres)', d, 1e-3)
    d = max(math.dist(J['llToUtm10'][i], G.ll_to_utm10(*LL[i])) for i in range(len(LL))); check('llToUtm10', d, 1e-3)
    d = max(gm(J['utm10ToLL'][i], G.utm10_to_ll(*UT[i])) for i in range(len(UT))); check('utm10ToLL (geodesic metres)', d, 1e-3)
    d = max(math.dist(J['utm10ToWorld'][i], G.utm10_to_world(*UT[i])) for i in range(len(UT))); check('utm10ToWorld', d, 1e-3)
    d = max(math.dist(J['worldToUtm10'][i], G.world_to_utm10(*WP[i])) for i in range(len(WP))); check('worldToUtm10', d, 1e-3)
    d = max(math.dist(J['rwyAlongAcross'][i], G.rwy_along_across(RA[i][0], WP[i][0] / 10, WP[i][1] / 10)) for i in range(len(RA)))
    check('rwyAlongAcross', d, 1e-3)
    d = max(math.dist(J['rwyToWorld'][i], G.rwy_to_world(*RA[i])) for i in range(len(RA))); check('rwyToWorld', d, 1e-3)
    d = max(abs(J['rwySurfaceY'][i] - G.rwy_surface_y(RA[i][0], RA[i][1])) for i in range(len(RA))); check('rwySurfaceY', d, 1e-3)
    d = 0
    for i, r in enumerate(J['runways']):
        p = G.RUNWAYS[i]
        d = max(d, abs(r['length'] - p['length']), abs(r['dispA'] - p['dispA']), abs(r['dispB'] - p['dispB']),
                math.dist(r['a'], (p['a'][0], -p['a'][1])), math.dist(r['b'], (p['b'][0], -p['b'][1])), abs(r['width'] - p['width']))
        if abs(r['hdgA'] - p['hdgA']) > 1e-9 or r['ends'] != list(p['ends']): d = 1
    check('RUNWAYS records (lengths, displacements, ends)', d, 1e-3)
    d = 0
    for k, b in J['byEnd'].items():
        t = G.rwy_to_world(k, G.thr_disp_m(k))         # runwayByEnd puts thr on the axis at the surveyed displacement
        d = max(d, math.dist(b['thr'], (t[0], -t[1])), abs(b['disp'] - G.thr_disp_m(k)))
    check('runwayByEnd thr / disp vs rwy_to_world(thr_disp_m)', d, 1e-3)
    # 2. vs pyproj topocentric, numpy twins
    print('2. vs pyproj topocentric (GRS80 ENU at the ARP); numpy twins')
    T = pyproj.Transformer.from_pipeline(
        f'+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cart +ellps=GRS80 '
        f'+step +proj=topocentric +ellps=GRS80 +lat_0={G.ARP_LAT} +lon_0={G.ARP_LON} +h_0=0')
    dj = dp = 0
    for i, (la, lo) in enumerate(LL):
        e, n, _ = T.transform(lo, la, 0.0)
        dj = max(dj, math.dist(J['llToWorld'][i], (e, -n))); dp = max(dp, math.dist(G.ll_to_world(la, lo), (e, -n)))
    check('js llToWorld vs pyproj', dj, 1e-3); check('py ll_to_world vs pyproj', dp, 1e-3)
    la = np.array([p[0] for p in LL]); lo = np.array([p[1] for p in LL])
    X, Z = G.ll_to_world_np(la, lo); d = max(math.dist((X[i], Z[i]), G.ll_to_world(*LL[i])) for i in range(len(LL)))
    check('ll_to_world_np vs scalar', d, 1e-6)
    X, Z = G.wgs84_to_world_np(la, lo); d = max(math.dist((X[i], Z[i]), G.wgs84_to_world(*LL[i])) for i in range(len(LL)))
    check('wgs84_to_world_np vs scalar', d, 1e-6)
    wx = np.array([p[0] for p in WP]); wz = np.array([p[1] for p in WP])
    A, B = G.world_to_ll_np(wx, wz); d = max(gm((A[i], B[i]), G.world_to_ll(*WP[i])) for i in range(len(WP)))
    check('world_to_ll_np vs scalar (geodesic metres)', d, 1e-6)
    ue = np.array([p[0] for p in UT]); un = np.array([p[1] for p in UT])
    X, Z = G.utm10_to_world_np(ue, un); d = max(math.dist((X[i], Z[i]), G.utm10_to_world(*UT[i])) for i in range(len(UT)))
    check('utm10_to_world_np vs scalar', d, 1e-6)
    A, B = G.world_to_utm10_np(wx, wz); d = max(math.dist((A[i], B[i]), G.world_to_utm10(*WP[i])) for i in range(len(WP)))
    check('world_to_utm10_np vs scalar', d, 1e-6)
    # 3. UTM vs pyproj EPSG:26910
    print('3. UTM 10N vs pyproj EPSG:4269 <-> EPSG:26910')
    F = pyproj.Transformer.from_crs('EPSG:4269', 'EPSG:26910', always_xy=True)
    I = pyproj.Transformer.from_crs('EPSG:26910', 'EPSG:4269', always_xy=True)
    print(f'     pipeline: {F.to_proj4()}')
    dj = dp = 0
    for i, (la_, lo_) in enumerate(LL):
        e, n = F.transform(lo_, la_)
        dj = max(dj, math.dist(J['llToUtm10'][i], (e, n))); dp = max(dp, math.dist(G.ll_to_utm10(la_, lo_), (e, n)))
    check('llToUtm10 js vs pyproj (60 pts, to +-50 km)', dj, 1e-3); check('ll_to_utm10 py vs pyproj', dp, 1e-3)
    dj = dp = 0
    for i, (e, n) in enumerate(UT):
        lo_, la_ = I.transform(e, n)
        dj = max(dj, gm(J['utm10ToLL'][i], (la_, lo_))); dp = max(dp, gm(G.utm10_to_ll(e, n), (la_, lo_)))
    check('utm10ToLL js vs pyproj (geodesic metres)', dj, 1e-3); check('utm10_to_ll py vs pyproj', dp, 1e-3)
    f = pyproj.Proj('EPSG:26910').get_factors(G.ARP_LON, G.ARP_LAT)
    print(f'     at the ARP: E {E0:.3f} N {N0:.3f}; scale k {f.meridional_scale:.6f}; meridian convergence {f.meridian_convergence:+.4f} deg')
    # 4. constants vs NASR
    print('4. constants vs FAA NASR rows', os.path.relpath(NASR, ROOT))
    tb = json.load(open(NASR))['tables']; base = tb['APT_BASE.csv'][0]
    ends = {r['RWY_END_ID']: r for r in tb['APT_RWY_END.csv']}; rwys = {r['RWY_ID']: r for r in tb['APT_RWY.csv']}
    bad = []
    if (round(float(base['LAT_DECIMAL']), 7), round(float(base['LONG_DECIMAL']), 7)) != (G.ARP_LAT, G.ARP_LON): bad.append('ARP')
    if float(base['ELEV']) != G.FIELD_ELEV_FT or J['fieldFt'] != G.FIELD_ELEV_FT: bad.append('ELEV')
    fnum = lambda r, k: float(r[k]) if k in r else None
    for k, r in ends.items():
        exp = dict(lat=fnum(r, 'LAT_DECIMAL'), lon=fnum(r, 'LONG_DECIMAL'), elev=fnum(r, 'RWY_END_ELEV'),
                   disp=fnum(r, 'DISPLACED_THR_LEN') or 0, thrLat=fnum(r, 'LAT_DISPLACED_THR_DECIMAL'),
                   thrLon=fnum(r, 'LONG_DISPLACED_THR_DECIMAL'), thrElev=fnum(r, 'DISPLACED_THR_ELEV'), tdzElev=fnum(r, 'TDZ_ELEV'),
                   vgsi=r.get('VGSI_CODE'), gpa=fnum(r, 'VISUAL_GLIDE_PATH_ANGLE'), tch=fnum(r, 'THR_CROSSING_HGT'),
                   marking=r.get('RWY_MARKING_TYPE_CODE'), rhTraffic=r.get('RIGHT_HAND_TRAFFIC_PAT_FLAG') == 'Y',
                   trueAln=fnum(r, 'TRUE_ALIGNMENT'), ils=r.get('ILS_TYPE'), reil=r.get('RWY_END_LGTS_FLAG') == 'Y')
        for f_, v in exp.items():
            for side, D in (('py', G.RWY_ENDS[k]), ('js', J['ends'][k]['E'])):
                if D[f_] != v: bad.append(f'{side} {k}.{f_} {D[f_]!r} != NASR {v!r}')
        la_ = float(r['RWY_END_LAT_DEG']) + float(r['RWY_END_LAT_MIN']) / 60 + float(r['RWY_END_LAT_SEC']) / 3600
        lo_ = -(float(r['RWY_END_LONG_DEG']) + float(r['RWY_END_LONG_MIN']) / 60 + float(r['RWY_END_LONG_SEC']) / 3600)
        dd = gm((la_, lo_), (exp['lat'], exp['lon']))
        print(f'     {k}: NASR DMS vs decimal {dd * 1000:.2f} mm; 28L RIGHT_HAND_TRAFFIC_PAT_FLAG present: {"RIGHT_HAND_TRAFFIC_PAT_FLAG" in r}' if k == '28L' else f'     {k}: NASR DMS vs decimal {dd * 1000:.2f} mm')
        if dd > 0.01: bad.append(f'{k} DMS vs decimal')
    for rid, r in rwys.items():
        exp = dict(lenFt=float(r['RWY_LEN']), widthFt=float(r['RWY_WIDTH']), surface=r.get('SURFACE_TYPE_CODE'),
                   treatment=r.get('TREATMENT_CODE'), cond=r.get('COND'), lights=r.get('RWY_LGT_CODE'),
                   gwSW=fnum(r, 'GROSS_WT_SW'), gwDW=fnum(r, 'GROSS_WT_DW'))
        for f_, v in exp.items():
            for side, D in (('py', G.RWY_DATA[rid]), ('js', J['rwyData'][rid])):
                if D[f_] != v: bad.append(f'{side} {rid}.{f_} {D[f_]!r} != NASR {v!r}')
    for b in bad: print('     mismatch:', b)
    check('NASR transcription mismatches (ARP, ELEV, 4 ends x 16 fields, 2 runways x 8 fields, py + js)', len(bad), 0, 'fields')
    # 5. round trip
    print('5. FAA NASR runway ends: lat/lon -> world -> lat/lon')
    worst = 0
    for k, E in J['ends'].items():
        dj = gm((E['E']['lat'], E['E']['lon']), E['back'])
        dp = gm((E['E']['lat'], E['E']['lon']), G.world_to_ll(*G.ll_to_world(E['E']['lat'], E['E']['lon'])))
        worst = max(worst, dj, dp)
        print(f'     {k:>3}: world ({E["w"][0]:9.3f}, {E["w"][1]:9.3f})  y {E["E"]["elev"] * G.FT:6.3f}  round trip js {dj * 1000:.1e} mm  py {dp * 1000:.1e} mm')
    check('runway-end round trip (4 ends)', worst, 0.01)
    # 6. lengths and bearings
    print('6. runway lengths (plane, geodesic GRS80, NASR RWY_LEN) and bearings')
    wl = wf = wb = wa = 0
    for r in J['runways']:
        a, b = r['ends']; A, B = G.RWY_ENDS[a], G.RWY_ENDS[b]
        az, baz, L = geod.inv(A['lon'], A['lat'], B['lon'], B['lat'])
        Lslope = math.hypot(L, (B['elev'] - A['elev']) * G.FT)
        nasr = G.RWY_DATA[r['id']]['lenFt']
        print(f'     {r["id"]}: plane {r["length"]:.4f} m  geodesic {L:.4f} m ({1000 * (r["length"] - L):+.2f} mm)'
              f'  = {L / G.FT:.2f} ft vs NASR {nasr} ft: {L / G.FT - nasr:+.2f} ft  (slope length {Lslope / G.FT:.2f} ft,'
              f' grade {100 * (B["elev"] - A["elev"]) * G.FT / L:.3f} %)')
        azB = geod.inv(B['lon'], B['lat'], A['lon'], A['lat'])[0] % 360
        print(f'        bearing {a} geodesic {az % 360:.5f} (stored {A["brg"]}), {b} {azB:.5f} (stored {B["brg"]});'
              f' plane heading {r["hdgA"]:.5f}; NASR TRUE_ALIGNMENT {A["trueAln"]}/{B["trueAln"]}')
        wl = max(wl, abs(r['length'] - L)); wf = max(wf, abs(L / G.FT - nasr))
        for e1, e2 in ((A, B), (B, A)):
            g = geod.inv(e1['lon'], e1['lat'], e2['lon'], e2['lat'])[0] % 360
            wb = max(wb, abs(g - e1['brg'])); wa = max(wa, abs(g - e1['trueAln']))
    check('plane length vs geodesic', wl, 0.05)
    check('geodesic length vs NASR RWY_LEN', wf, 1.0, 'ft')
    check('stored brg vs pyproj geodesic azimuth', wb, 1e-4, 'deg')
    check('geodesic azimuth vs NASR TRUE_ALIGNMENT (whole deg)', wa, 0.5, 'deg')
    # 7. displaced thresholds
    print('7. displaced thresholds: surveyed NASR position vs DISPLACED_THR_LEN along the axis')
    wa = wc = 0
    for k, E in G.RWY_ENDS.items():
        if E['thrLat'] is None: continue
        al, ac = G.rwy_along_across(k, *G.thr_world(k))
        _, _, gd = geod.inv(E['lon'], E['lat'], E['thrLon'], E['thrLat'])
        print(f'     {k}: along {al:.3f} m = {al / G.FT:.2f} ft (NASR {E["disp"]} ft, {al / G.FT - E["disp"]:+.2f} ft), across {ac * 1000:+.1f} mm,'
              f' geodesic {gd / G.FT:.2f} ft; thr y {E["thrElev"] * G.FT:.3f} m; js disp {J["ends"][k]["disp"]:.3f} m')
        wa = max(wa, abs(al / G.FT - E['disp'])); wc = max(wc, abs(ac))
    check('threshold across offset', wc, 0.05); check('threshold along vs DISPLACED_THR_LEN', wa, 1.0, 'ft')
    for k in G.RWY_ENDS: print(f'     profile {k}: ' + ', '.join(f'{a:.1f} m: y {y:.3f}' for a, y in G.rwy_profile(k)))
    pts = [E['elev'] for E in G.RWY_ENDS.values()] + [E['thrElev'] for E in G.RWY_ENDS.values() if E['thrElev'] is not None]
    print(f'     GROUND_Y {G.GROUND_Y} (js {J["groundY"]}) vs mean of the 6 NASR points {sum(pts) / len(pts) * G.FT:.3f} m;'
          f' FIELD_ELEV_Y {G.FIELD_ELEV_Y:.3f} m')
    if J['groundY'] != G.GROUND_Y or abs(sum(pts) / len(pts) * G.FT - G.GROUND_Y) > 0.05: fails.append('GROUND_Y')
    # 8. datum offset
    print('8. WGS 84 offset vs pyproj NAD83(2011) -> WGS 84 (G2296) @ epoch', G.WGS84_EPOCH)
    H = pyproj.Transformer.from_crs('EPSG:6319', 'EPSG:10605', always_xy=True)
    print('     chain:', H.description)
    lo2, la2, h2, _ = H.transform(G.ARP_LON, G.ARP_LAT, 0.0, G.WGS84_EPOCH)
    e2, n2 = G.ll_to_en(la2, lo2)
    print(f'     ARP displacement in the frame: dE {e2:+.5f} dN {n2:+.5f} dH {h2:+.5f} m (stored {G.WGS84_MINUS_NAD83_E:+.3f}'
          f' {G.WGS84_MINUS_NAD83_N:+.3f} {G.WGS84_MINUS_NAD83_H:+.3f}); |d| {math.hypot(e2, n2):.4f} m az {math.degrees(math.atan2(e2, n2)) % 360:.1f}')
    worst = 0
    for la_, lo_ in [(G.ARP_LAT, G.ARP_LON)] + LL[:50]:
        lo2, la2, _, _ = H.transform(lo_, la_, 0.0, G.WGS84_EPOCH)
        p = G.ll_to_world(la_, lo_); q = G.wgs84_to_world(la2, lo2)
        worst = max(worst, math.dist(p, q))
        if (la_, lo_) == (G.ARP_LAT, G.ARP_LON): check('ARP: wgs84ToWorld(helmert(ARP)) - ARP', math.dist(p, q), 0.002)
    check('AOI (51 pts, +-5 km): wgs84ToWorld(helmert(p)) - p', worst, 0.01)
    lo3, la3, _, _ = H.transform(G.ARP_LON, G.ARP_LAT, 0.0, G.WGS84_EPOCH + 1)
    e3, n3 = G.ll_to_en(la3, lo3)
    print(f'     rate: dE {e3 - e2:+.4f} m/yr dN {n3 - n2:+.4f} m/yr (stored {G.WGS84_RATE_E} {G.WGS84_RATE_N})')
    S = pyproj.Transformer.from_pipeline(
        '+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cart +ellps=GRS80 '
        '+step +proj=topocentric +ellps=GRS80 +lat_0=37.6188056 +lon_0=-122.3754167 +h_0=0')
    lo2, la2, _, _ = H.transform(-122.3754167, 37.6188056, 0.0, 2026.73); es, ns, _ = S.transform(lo2, la2, 0.0)
    print(f'     sanity, SFO ARP @ 2026.73 with this pyproj: dE {es:+.4f} dN {ns:+.4f} (sfo3d: -1.568 +0.159)')
    if abs(es + 1.568) > 0.002 or abs(ns - 0.159) > 0.002: fails.append('SFO sanity')
    Tn = pyproj.Transformer.from_crs('EPSG:4269', 'EPSG:4326', always_xy=True)
    lo4, la4 = Tn.transform(G.ARP_LON, G.ARP_LAT)
    first = pyproj.transformer.TransformerGroup('EPSG:4269', 'EPSG:4326', always_xy=True).transformers[0]
    print(f'     PROJ default EPSG:4269 -> EPSG:4326 moves the ARP by {gm((G.ARP_LAT, G.ARP_LON), (la4, lo4)):.3f} m'
          f' (first candidate: {first.description.split(" (with")[0]}, {first.to_proj4()}) - null, never use')
    jd = J['datum']
    if (jd['epoch'], jd['dE'], jd['dN'], jd['dH']) != (G.WGS84_EPOCH, G.WGS84_MINUS_NAD83_E, G.WGS84_MINUS_NAD83_N, G.WGS84_MINUS_NAD83_H) \
            or (jd['rateE'], jd['rateN']) != (G.WGS84_RATE_E, G.WGS84_RATE_N): fails.append('DATUM js != py')
    print(f'     js DATUM {jd}')
    print('FAILED: ' + ', '.join(fails) if fails else 'ALL CHECKS PASSED')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
