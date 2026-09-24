#!/usr/bin/env python3
"""Verify the world frame: js/geo.js == tools/geo_frame.py, and both against pyproj / the FAA source.

Checks (exit status 1 if any fails):
  1. JS == Python on 50 lat/lon points and 50 world points (llToWorld, worldToLL, wgs84ToWorld, worldToWgs84,
     stToWorld, worldToST), tolerance 1 mm (in practice ~1e-9 m).
  2. Both == the pyproj topocentric pipeline (GRS80 ENU at the ARP) to 1 mm.
  3. FAA NASR runway ends: lat/lon -> world -> lat/lon round trip < 1 cm (JS and Python).
  4. RUNWAYS lengths (js) == geodesic lengths on GRS80 (pyproj.Geod) to < 5 cm.
  5. WGS 84 offset == pyproj NAD83(2011) -> WGS 84 (G2296) at the frame epoch to < 2 mm at the ARP and < 1 cm
     over the AOI.
  6. Legacy migration: legacy_to_world(world_to_legacy(p)) == p to < 1 mm.
Usage: python3 tools/test_geo_frame.py            (needs node >= 18 on PATH)
"""
import json, math, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import geo_frame as G

random.seed(20260924)
LL = [(G.ARP_LAT + random.uniform(-0.05, 0.05), G.ARP_LON + random.uniform(-0.06, 0.06)) for _ in range(40)]
LL += [(G.ARP_LAT + random.uniform(-0.45, 0.45), G.ARP_LON + random.uniform(-0.55, 0.55)) for _ in range(10)]
WP = [(random.uniform(-3000, 3000), random.uniform(-3000, 3000)) for _ in range(40)]
WP += [(random.uniform(-40000, 40000), random.uniform(-40000, 40000)) for _ in range(10)]
JS = r"""
const G = await import(process.argv[1]);
const inp = JSON.parse(process.argv[2]);
const out = {
  llToWorld: inp.ll.map(([la, lo]) => { const w = G.llToWorld(la, lo, 0); return [w[0], w[2]]; }),
  wgs84ToWorld: inp.ll.map(([la, lo]) => { const w = G.wgs84ToWorld(la, lo, 0); return [w[0], w[2]]; }),
  worldToLL: inp.w.map(([x, z]) => G.worldToLL(x, z)),
  worldToWgs84: inp.w.map(([x, z]) => G.worldToWgs84(x, z)),
  worldToST: inp.w.map(([x, z]) => G.worldToST(x, z)),
  stToWorld: inp.w.map(([s, t]) => { const w = G.stToWorld(s, t, 0); return [w[0], w[2]]; }),
  ends: Object.fromEntries(Object.entries(G.RWY_ENDS).map(([k, E]) => { const w = G.llToWorld(E.lat, E.lon); const ll = G.worldToLL(w[0], w[2]); return [k, { lat: E.lat, lon: E.lon, w: [w[0], w[2]], back: ll }]; })),
  runways: G.RUNWAYS.map(r => ({ ends: r.ends, length: r.length, hdgA: r.hdgA })),
  V: G.V, U: G.U, HDG_28: G.HDG_28, datum: G.DATUM, frame: G.FRAME_ID,
};
console.log(JSON.stringify(out));
"""


def run_js():
    src = os.path.join(ROOT, 'js', 'geo.js')
    r = subprocess.run(['node', '--input-type=module', '-e', JS, 'file://' + src, json.dumps({'ll': LL, 'w': WP})],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode: print(r.stderr); raise SystemExit('node failed')
    return json.loads(r.stdout)


def main():
    J = run_js(); fails = []
    def check(name, val, tol, unit='m'):
        ok = val <= tol; print(f'  {"OK " if ok else "FAIL"} {name}: {val:.3g} {unit} (tol {tol:g})')
        if not ok: fails.append(name)
    print(f'frame: js {J["frame"]}  py {G.FRAME_ID}')
    # 1. JS == Python
    print('1. js/geo.js vs tools/geo_frame.py')
    d = max(math.dist(J['llToWorld'][i], G.ll_to_world(*LL[i])) for i in range(len(LL)))
    check('llToWorld (50 pts)', d, 1e-3)
    d = max(math.dist(J['wgs84ToWorld'][i], G.wgs84_to_world(*LL[i])) for i in range(len(LL)))
    check('wgs84ToWorld (50 pts)', d, 1e-3)
    d = max(math.dist(G.ll_to_world(*J['worldToLL'][i]), G.ll_to_world(*G.world_to_ll(*WP[i]))) for i in range(len(WP)))
    check('worldToLL (50 pts, compared in metres)', d, 1e-3)
    d = max(math.dist(G.ll_to_world(*J['worldToWgs84'][i]), G.ll_to_world(*G.world_to_wgs84(*WP[i]))) for i in range(len(WP)))
    check('worldToWgs84 (50 pts, in metres)', d, 1e-3)
    d = max(math.dist(J['worldToST'][i], G.world_to_st(*WP[i])) for i in range(len(WP)))
    check('worldToST (50 pts)', d, 1e-3)
    d = max(math.dist(J['stToWorld'][i], G.st_to_world(*WP[i])) for i in range(len(WP)))
    check('stToWorld (50 pts)', d, 1e-3)
    check('grid heading HDG_28 js - py', abs(J['HDG_28'] - (G.HDG_S + 180) % 360), 1e-9, 'deg')
    # 2. vs pyproj topocentric
    print('2. vs pyproj topocentric (GRS80 ENU at the ARP)')
    import pyproj
    T = pyproj.Transformer.from_pipeline(
        f'+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=cart +ellps=GRS80 '
        f'+step +proj=topocentric +ellps=GRS80 +lat_0={G.ARP_LAT} +lon_0={G.ARP_LON} +h_0=0')
    d = 0
    for i, (la, lo) in enumerate(LL):
        e, n, _ = T.transform(lo, la, 0.0); d = max(d, math.dist(J['llToWorld'][i], (e, -n)))
    check('js llToWorld vs pyproj (50 pts)', d, 1e-3)
    # 3. FAA runway ends round trip
    print('3. FAA NASR runway ends: lat/lon -> world -> lat/lon')
    geod = pyproj.Geod(ellps='GRS80'); worst = 0
    for k, E in J['ends'].items():
        _, _, dj = geod.inv(E['lon'], E['lat'], E['back'][1], E['back'][0])
        la, lo = G.world_to_ll(*G.ll_to_world(E['lat'], E['lon'])); _, _, dp = geod.inv(E['lon'], E['lat'], lo, la)
        worst = max(worst, dj, dp)
        print(f'     {k:>3}: world ({E["w"][0]:9.3f}, {E["w"][1]:9.3f})  round trip js {dj * 1000:.2e} mm  py {dp * 1000:.2e} mm')
    check('runway-end round trip (8 ends)', worst, 0.01)
    # 4. runway lengths vs geodesic
    print('4. RUNWAYS lengths vs geodesic (pyproj.Geod GRS80)')
    worst = 0
    for r in J['runways']:
        a, b = r['ends']; A, B = G.RWY_ENDS[a], G.RWY_ENDS[b]
        az, _, L = geod.inv(A['lon'], A['lat'], B['lon'], B['lat'])
        worst = max(worst, abs(r['length'] - L))
        print(f'     {a}/{b}: app {r["length"]:.4f} m  geodesic {L:.4f} m  diff {1000 * (r["length"] - L):+.2f} mm'
              f'  (plane heading {r["hdgA"]:.4f}, geodesic azimuth at {a} {az % 360:.4f})')
    check('runway length vs geodesic', worst, 0.05)
    # 5. datum offset
    print('5. WGS 84 offset vs pyproj NAD83(2011) -> WGS 84 (G2296) @ epoch', G.WGS84_EPOCH)
    H = pyproj.Transformer.from_crs('EPSG:6319', 'EPSG:10605', always_xy=True)
    worst = 0
    for la, lo in [(G.ARP_LAT, G.ARP_LON)] + LL[:40]:
        lo2, la2, _, _ = H.transform(lo, la, 0.0, G.WGS84_EPOCH)
        # the NAD83 point la/lo is at world p; its WGS 84 coordinates la2/lo2 must map back onto p
        p = G.ll_to_world(la, lo); q = G.wgs84_to_world(la2, lo2)
        worst = max(worst, math.dist(p, q))
        if (la, lo) == (G.ARP_LAT, G.ARP_LON): check('ARP: wgs84ToWorld(helmert(ARP)) - ARP', math.dist(p, q), 0.002)
    check('AOI (41 pts): wgs84ToWorld(helmert(p)) - p', worst, 0.01)
    print(f'     js DATUM {J["datum"]}')
    # 6. legacy migration round trip
    print('6. legacy frame migration')
    d = max(math.dist(G.legacy_to_world(*G.world_to_legacy(*p)), p) for p in WP[:40])
    check('legacy_to_world(world_to_legacy(p)) (40 pts)', d, 1e-3)
    print('FAILED: ' + ', '.join(fails) if fails else 'ALL CHECKS PASSED')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
