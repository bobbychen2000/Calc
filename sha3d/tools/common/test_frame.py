"""Checks for tools/common/frame.py (run: python3 -I sha3d/tools/common/test_frame.py [PIN_SUMMARY_JSON]).

1. ll_to_en == PROJ +proj=topocentric (east, north) at the origin, 400 points within 6 km, < 1e-6 m.
2. en_to_ll round trip < 1e-8 m (float64 floor at ECEF scale).
3. Plane distance from the origin vs the WGS 84 geodesic distance (pyproj Geod) at 1, 2, 5, 10, 50 km.
4. Curvature drop (ENU up of a ground point) at 5 km.
5. The equirectangular shortcut (111320 m/deg) vs the exact plane at the runway ends.
6. The geodesic vs arithmetic midpoint of the two OSM end nodes (OD0).
7. Plate motion of a fixed point at the origin, 2000.0 -> 2026.87 (PROJ ITRF2014:EURA), i.e. CGCS2000 vs WGS 84 now.
8. Optional (argument: refs/cache/osm_pinned/pin_summary.json): the origin nodes in the pinned OSM extract still
   have the OD0 coordinates.
Prints a JSON summary (used in docs/phase1/airport.md).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frame as F  # noqa: E402
from pyproj import Geod, Transformer  # noqa: E402

out = {}
G = Geod(ellps='WGS84')
topo = Transformer.from_pipeline(
    f'+proj=pipeline +step +proj=cart +ellps=WGS84 +step +proj=topocentric +ellps=WGS84 '
    f'+lat_0={F.ORIGIN_LAT} +lon_0={F.ORIGIN_LON} +h_0=0')

# 1 + 2
worst_topo = worst_rt = 0.0
for i in range(20):
    for j in range(20):
        e0, n0 = -6000 + 600 * i + 17.3, -6000 + 600 * j - 11.1
        lat, lon = F.en_to_ll(e0, n0)
        e1, n1 = F.ll_to_en(lat, lon)
        worst_rt = max(worst_rt, math.hypot(e1 - e0, n1 - n0))
        te, tn, tu = topo.transform(lon, lat, 0.0)
        worst_topo = max(worst_topo, math.hypot(te - e1, tn - n1))
assert worst_topo < 1e-6, worst_topo
assert worst_rt < 1e-8, worst_rt
out['max_diff_vs_proj_topocentric_m'] = worst_topo
out['max_roundtrip_m'] = worst_rt

# 3 + 4
dist = {}
for d in (1000, 2000, 5000, 10000, 50000):
    worst = 0.0; drop = 0.0
    for az in range(0, 360, 15):
        lon, lat, _ = G.fwd(F.ORIGIN_LON, F.ORIGIN_LAT, az, d)
        e, n = F.ll_to_en(lat, lon)
        worst = max(worst, abs(math.hypot(e, n) - d))
        drop = min(drop, F.ll_to_enu(lat, lon, 0.0)[2])
    dist[f'{d // 1000}km'] = {'plane_minus_geodesic_max_m': round(worst, 6), 'curvature_drop_m': round(drop, 3)}
out['distance_error'] = dist
assert dist['5km']['plane_minus_geodesic_max_m'] < 0.001

# 5
eq = {}
for nm, (lat, lon) in {'18L_osm_end': (31.2131135, 121.3354641), '36R_osm_end': (31.1825842, 121.3371157),
                       '18R_osm_end': (31.2129628, 121.3316265), '36L_osm_end': (31.1833933, 121.3332449)}.items():
    e, n = F.ll_to_en(lat, lon)
    eqe = (lon - F.ORIGIN_LON) * 111320 * math.cos(math.radians(F.ORIGIN_LAT)); eqn = (lat - F.ORIGIN_LAT) * 111320
    eq[nm] = {'exact_en_m': [round(e, 3), round(n, 3)], 'equirect_minus_exact_m': [round(eqe - e, 3), round(eqn - n, 3)]}
out['equirect_check'] = eq
out['scale_equirect_vs_exact'] = {'east': round(111320 * math.cos(math.radians(F.ORIGIN_LAT)) / F.MLON - 1, 5),
                                  'north': round(111320 / F.MLAT - 1, 5)}

# 6
(_, _, la1, lo1), (_, _, la2, lo2) = F.ORIGIN_NODES['n'], F.ORIGIN_NODES['s']
az12, az21, L = G.inv(lo1, la1, lo2, la2)
lo_m, la_m, _ = G.fwd(lo1, la1, az12, L / 2)
e, n = F.ll_to_en(la_m, lo_m)
out['origin'] = {'lat': F.ORIGIN_LAT, 'lon': F.ORIGIN_LON,
                 'arith_mean_of_nodes': [(la1 + la2) / 2, (lo1 + lo2) / 2],
                 'geodesic_midpoint_offset_m': round(math.hypot(e, n), 5),
                 'rwy_18L36R_osm_length_m': round(L, 2), 'rwy_18L36R_osm_az_deg': round(az12 % 360, 4)}
assert abs((la1 + la2) / 2 - F.ORIGIN_LAT) < 1e-12 and abs((lo1 + lo2) / 2 - F.ORIGIN_LON) < 1e-12

# 7: plate motion (Eurasia, ITRF2014 PMM) of a fixed ground point from epoch 2000.0 to 2026.87
pm = Transformer.from_pipeline('+proj=pipeline +step +proj=cart +ellps=GRS80 +step +init=ITRF2014:EURA '
                               '+step +inv +proj=cart +ellps=GRS80')
p00 = pm.transform(F.ORIGIN_LON, F.ORIGIN_LAT, 0.0, 2000.0)
p26 = pm.transform(F.ORIGIN_LON, F.ORIGIN_LAT, 0.0, 2026.87)
dE = (p26[0] - p00[0]) * F.MLON; dN = (p26[1] - p00[1]) * F.MLAT
out['plate_motion_2000_to_2026.87_m'] = {'dE': round(dE, 3), 'dN': round(dN, 3), 'total': round(math.hypot(dE, dN), 3),
                                          'model': 'PROJ ITRF2014:EURA (Altamimi et al. 2017 PMM), stable Eurasia'}

# 8
if len(sys.argv) > 1:                      # refs/cache/osm_pinned/pin_summary.json
    idx = json.load(open(sys.argv[1]))['origin_nodes_check']
    for k, (_, i, la, lo) in F.ORIGIN_NODES.items():
        assert idx[str(i)][0] == la and idx[str(i)][1] == lo, (i, idx[str(i)])
    out['pinned_origin_nodes'] = {'match': True, **idx}

print(json.dumps(out, indent=1))
print('OK')
