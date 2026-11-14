"""Registration of the full-resolution Umbra GEC (2024-06-02, CC BY 4.0) against OSM, for task A2 (jet bridges).

usage: python3 -I sha3d/tools/airport/sar_registration.py SHA3D_DIR OUT_JSON
East-west: the dark (smooth) paved band of each runway in 6 full-resolution bands (refs/cache/imagery/umbra_fullres_reg,
tools/airport/umbra_stand_windows.py ... reg): along-track median cross profile, steepest falling / rising edges, band
centre minus the OSM centreline. North-south: the paved band across TWY H2 between grass islands (x -585..-475 and
-370..-285), in Umbra and in the two pinned Sentinel-2 scenes (raw registration), relative to the OSM H2 line.
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import uniform_filter1d
from shapely.geometry import LineString

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
from sarwin import SarWindows  # noqa: E402
from imgsample import S2  # noqa: E402


def edges(tt, prof):
    p = uniform_filter1d(prof, 9); dp = np.gradient(p); h = len(tt) // 2
    return tt[np.argmin(dp[:h])], tt[h + np.argmax(dp[h:])]


def main(root, out):
    S = SarWindows(root, (0, 0), 'umbra_fullres_reg')
    A = json.load(open(os.path.join(root, 'data/sha_airport.json')))
    res = {'runway_bands': [], 'h2': []}
    for r in A['runways']:
        p0, p1 = np.array(r['centreline']['pts'], float)
        d = (p1 - p0) / np.linalg.norm(p1 - p0); n = np.array([-d[1], d[0]])     # n points west (right of southward)
        for za, zb in [(-1330, -970), (-180, 180), (970, 1330)]:
            sa, sb = (za - p0[1]) / d[1], (zb - p0[1]) / d[1]
            ss = np.arange(sa, sb, 1.0); tt = np.arange(-60, 60, 0.25)
            SS, TT = np.meshgrid(ss, tt, indexing='ij')
            g = np.log1p(S.sample_xz(p0[0] + SS * d[0] + TT * n[0], p0[1] + SS * d[1] + TT * n[1]))
            prof = np.nanmedian(g, axis=0)
            e0, e1 = edges(tt, prof)
            east = float((e0 + e1) / 2 * n[0])
            res['runway_bands'].append({'runway': r['id'], 'z_range': [za, zb], 'edges_m': [float(e0), float(e1)],
                                        'width_m': float(e1 - e0), 'umbra_minus_osm_east_m': round(east, 2)})
    h2 = LineString([t for t in A['taxiways'] if t['id'] == 'osm:way/128706558'][0]['pts'])
    s2s = [S2(os.path.join(root, 'refs/cache/s2', sc)) for sc in ('S2B_51RUQ_20261014_0_L2A', 'S2C_51RUQ_20260221_0_L2A')]
    for xa, xb in [(-585, -475), (-370, -285)]:
        xs = np.arange(xa, xb, 1.0)
        zc = np.array([h2.intersection(LineString([(x, -1700), (x, -1300)])).coords[0][1] for x in xs])
        tt = np.arange(-50, 50, 0.25)
        X = xs[None, :] + 0 * tt[:, None]; Z = zc[None, :] + tt[:, None]
        g = np.log1p(S.sample_xz(X, Z)); prof = np.nanmedian(g, axis=1)
        p = uniform_filter1d(prof, 9); dp = np.gradient(p); h = len(tt) // 2
        e0, e1 = tt[np.argmin(dp[:h])], tt[h + np.argmax(dp[h:])]
        row = {'x_range': [xa, xb], 'umbra_band_centre_south_of_osm_m': float((e0 + e1) / 2), 'umbra_width_m': float(e1 - e0)}
        for s in s2s:
            tt2 = np.arange(-50, 50, 1.0); pr = []
            for t in tt2:
                vals = []
                for x in np.arange(xa, xb, 5.0):
                    z = h2.intersection(LineString([(x, -1700), (x, -1300)])).coords[0][1] + t
                    lat, lon = F.world_to_ll(x, z)
                    E, N = s.en(np.array([lon]), np.array([lat]), osm_frame=False)
                    vals.append(float(s.ndvi_en(E, N)[0]))
                pr.append(np.median(vals))
            pr = uniform_filter1d(np.array(pr), 3); dp = np.gradient(pr); h = len(tt2) // 2
            a, b = tt2[np.argmin(dp[:h])], tt2[h + np.argmax(dp[h:])]
            row[s.name[:3] + '_band_centre_south_of_osm_m'] = float((a + b) / 2)
        res['h2'].append(row)
    ew = [b['umbra_minus_osm_east_m'] for b in res['runway_bands']]
    res['summary'] = {'umbra_minus_osm_east_m_mean': round(float(np.mean(ew)), 2), 'range': [min(ew), max(ew)],
                      'applied_shift_en_m': [3.4, 0.0],
                      'north_note': 'H2 band centre: Umbra and Sentinel-2 (registration within ~1 m of OSM north-south, '
                                    'phase 0) agree within their spread, so the OSM H2 line itself is off; 0 m applied N-S'}
    res['attribution'] = 'Umbra SAR Open Data (CC BY 4.0); Contains modified Copernicus Sentinel data 2026; OSM (ODbL)'
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(res['summary']), [r for r in res['h2']])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
