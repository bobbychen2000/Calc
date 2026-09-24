"""NAIP 2024 relief displacement of parked aircraft, and relief-corrected NAIP readings (review round 2, 24 Sep 2026).

Why: NAIP is orthorectified to a terrain DEM, so anything above the ground is shifted away from the nadir of its frame
(docs/research/imagery.md §6: the ATC tower cab sits ~38-40 m east of its base, ~0.57 m per m of height, nadir ~2.5 km
west of the terminals). A parked aircraft's imaged fuselage is therefore shifted EAST by k * h (h = height of the
imaged feature). Review round 2 showed the by-eye lateral readings (stand_table.NAIP_OBS, 'lateral 0.0') were in fact
1.5-2.6 m off the model axis at many stands, with the sign of cos(heading) (= east of the axis).

What this does (no NAIP pixels in any output):
  1. fuselage centre, measured: for every NAIP_OBS stand not flagged 'u', on an oriented patch (0.2 m px, stand heading
     up) rows 4-22 m behind the read nose: the bright fuselage band crossing the axis region (luminance above the
     row's side background by > 18, the connected run through the brightest pixel within +-4 m of the by-eye axis;
     dark fuselages / shadows are not measured); the band
     midpoint per row, median over rows -> lateral offset of the imaged fuselage centre from the OSM lead-in line
     ('lat_img', m, + = right of the heading). Rows whose band is narrower than 70 % or wider than 130 % of the
     fuselage width of the group (narrow 3.95 m, wide 6.2 m) are rejected (wings, bridge, shadow).
  2. relief model: lat_img = lat_true + k * h * (east . right), with right = (cos hdg, sin hdg) in x-east / z-south,
     h = imaged fuselage-band height (widest point: narrow bodies ~3.4 m, wide bodies ~5.3 m above ground; A320 / 777
     airport-planning sections, inferred mid-fuselage heights). k is fitted by least squares over all measured stands
     ASSUMING the OSM/paint lead-ins are unbiased on average (lat_true ~ 0 in the mean); the residual spread is the
     honest accuracy of a NAIP position check.
  3. corrected readings: lat_corr = lat_img - k * h * cos(hdg); nose along (by-eye NAIP_OBS reading at the nose tip,
     h_nose ~2.5 m narrow / 4.5 m wide) along_corr = along - k * h_nose * sin(hdg).
Output: refs/cache/stands/naip_relief.json {k, k_sigma, per stand {lat_img, lat_corr, along_corr, n_rows}} - read by
build_stands.py. Usage: python3 tools/stands/naip_relief.py [--plot]
"""
import json, math, os, sys
import numpy as np
import cv2
from common import Naip, WORK, hdg_vec, load_osm, Buildings
from osm_src import lead_ins
import stand_table as TB

H_FUS = {'narrow': 3.4, 'wide': 5.3}        # m, imaged fuselage band (widest section) height above ground (inferred)
H_NOSE = {'narrow': 2.5, 'wide': 4.5}       # m, nose tip height (inferred)
FUS_W = {'narrow': 3.95, 'wide': 6.2}       # m, A320 / 777 fuselage width (ACAP)
OUT = os.path.join(WORK, 'naip_relief.json')


def fuselage_centre(N, stop, hdg, nose_along, grp, lat0=0.0, res=0.2):
    f = hdg_vec(hdg); a0 = nose_along - 4.0; a1 = nose_along - 22.0
    cx = stop[0] + f[0] * (a0 + a1) / 2; cz = stop[1] + f[1] * (a0 + a1) / 2
    r_ = (math.cos(math.radians(hdg)), math.sin(math.radians(hdg))); cx += r_[0] * lat0; cz += r_[1] * lat0
    img, U, V = N.patch(cx, cz, hdg, a0 - a1, 20.0, res)
    lum = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    v = V[0]; W = FUS_W[grp]; mids = []
    for row in lum:
        side = row[(np.abs(v) > 7.5)]
        bg = np.median(side); on = row > bg + 18
        c = np.abs(v) <= 4.0
        if not on[c].any(): continue
        k = int(np.argmax(np.where(c, row, -1e9)))
        if not on[k]: continue
        i0 = k
        while i0 > 0 and on[i0 - 1]: i0 -= 1
        i1 = k
        while i1 < len(on) - 1 and on[i1 + 1]: i1 += 1
        wdt = v[i1] - v[i0] + res
        if 0.7 * W <= wdt <= 1.3 * W: mids.append((v[i0] + v[i1]) / 2)
    if len(mids) < 20: return None, len(mids)
    return float(np.median(mids)) + lat0, len(mids)


def main(plot=False):
    N = Naip(); osm = load_osm(); B = Buildings()
    LB = {r['osm_id']: r for r in lead_ins(osm, B)}
    rows = []
    for wid, (along, lat_eye, grp, fl) in TB.NAIP_OBS.items():
        if 'u' in fl or wid not in LB: continue
        w = LB[wid]; h = w['hdg']
        lat_img, n = fuselage_centre(N, w['stop'], h, along, grp, lat0=lat_eye)
        if lat_img is None: continue
        rows.append({'osm_id': wid, 'hdg': h, 'grp': grp, 'along_eye': along, 'lat_eye': lat_eye, 'lat_img': round(lat_img, 2), 'n_rows': n,
                     'east_right': math.cos(math.radians(h)), 'east_fwd': math.sin(math.radians(h))})
    # fit k: lat_img = k * h * cos(hdg) + e ; robust (drop |resid| > 2.5 m once: aircraft really off the line, e.g. F15)
    X = np.array([H_FUS[r['grp']] * r['east_right'] for r in rows]); Yv = np.array([r['lat_img'] for r in rows])
    keep = np.ones(len(rows), bool)
    for _ in range(3):
        k = float((X[keep] @ Yv[keep]) / (X[keep] @ X[keep])); res = Yv - k * X
        new = np.abs(res) < 2.5
        if (new == keep).all(): break
        keep = new
    sig = float(np.std(res[keep])); k_sig = sig / math.sqrt(float(X[keep] @ X[keep]))
    for r, e in zip(rows, res):
        r['relief_lat'] = round(k * H_FUS[r['grp']] * r['east_right'], 2)
        r['lat_corr'] = round(float(e), 2)
        r['along_corr'] = round(r['along_eye'] - k * H_NOSE[r['grp']] * r['east_fwd'], 2)
        r['fit_used'] = bool(keep[rows.index(r)])
    out = {'k': round(k, 3), 'k_sigma': round(k_sig, 3), 'resid_sigma_m': round(sig, 2), 'n': len(rows), 'n_fit': int(keep.sum()),
           'h_fus': H_FUS, 'h_nose': H_NOSE, 'model': 'lat_img = lat_true + k*h*cos(hdg); along_img = along_true + k*h*sin(hdg) (east lean)',
           'stands': {str(r['osm_id']): r for r in rows}}
    json.dump(out, open(OUT, 'w'), indent=1)
    print('k = %.3f +- %.3f m/m, residual sigma %.2f m, %d stands (%d in fit)' % (k, k_sig, sig, len(rows), keep.sum()))
    for r in sorted(rows, key=lambda r: -abs(r['lat_corr'])):
        print('  %10d %-6s hdg %5.1f lat_eye %+5.1f lat_img %+5.2f relief %+5.2f -> corr %+5.2f  along %+5.1f -> %+5.1f %s' % (
            r['osm_id'], r['grp'], r['hdg'], r['lat_eye'], r['lat_img'], r['relief_lat'], r['lat_corr'], r['along_eye'], r['along_corr'], '' if r['fit_used'] else '(not in fit)'))


if __name__ == '__main__':
    main('--plot' in sys.argv)
