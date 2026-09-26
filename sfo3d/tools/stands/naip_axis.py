"""Fuselage-axis fit of a parked aircraft on NAIP 2024, relief-corrected (review round 4, 26 Sep 2026).

Why: round 4 found stands whose model axis is laterally offset AND rotated against the imaged aircraft (G1: the 787
crosses the model axis ~26 m behind the nose; G12). naip_relief.py measures only one lateral number (median fuselage
centre 4-22 m behind the nose), so a heading error is invisible to it.

Method (no NAIP pixels in any output):
  * oriented patch along the stand's model axis (0.2 m px), rows from `a0` to `a1` m behind the model nose;
  * per row: luminance band of the bright fuselage crossing the axis region (the connected run through the brightest
    pixel within +-`search` m of the axis whose luminance exceeds the row's side background by > 18; the same test as
    naip_relief.fuselage_centre), accepted when its width is 0.7-1.3 x the fuselage width of the group (narrow 3.95 m,
    wide 6.2 m; rejects wing roots, engines, bridges, shadows);
  * robust line fit mid(a) = c0 + c1 * a over the accepted rows (3 passes, rows > 0.6 m off dropped);
  * relief: NAIP leans every raised feature EAST by k * h (naip_relief.json k, h = 3.4 m narrow / 5.3 m wide fuselage
    band height); the lateral component k * h * cos(hdg) is subtracted from c0 (it is the same for every row, so the
    heading is unaffected).
Output per stand: lat_nose (m, + = right of the model heading, at the model nose), lat_30 (30 m behind it), dh (deg,
imaged heading - model heading), n rows used / tried, rms (m). Written to refs/cache/stands/naip_axis.json.
Accuracy: rms of the row midpoints ~0.1-0.3 m; the relief model leaves ~0.7 m rms (naip_relief.py) - an axis fit is a
check to ~1 m laterally and ~1 deg, not better.
Usage: python3 tools/stands/naip_axis.py [STAND ...]   (default: every contact stand in data/sfo_stands.json)
"""
import json, math, os, sys
import numpy as np
import cv2
from common import Naip, WORK, ROOT
from naip_relief import H_FUS, FUS_W

OUT = os.path.join(WORK, 'naip_axis.json')


def axis_fit(N, nose, hdg, grp, a0=4.0, a1=45.0, search=4.5, res=0.2, k=None):
    f = (math.sin(math.radians(hdg)), -math.cos(math.radians(hdg)))
    L = a1 - a0; cx = nose[0] - f[0] * (a0 + a1) / 2; cz = nose[1] - f[1] * (a0 + a1) / 2
    img, U, V = N.patch(cx, cz, hdg, L, 24.0, res)
    lum = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    v = V[0]; W = FUS_W[grp]; rows = []
    for i, row in enumerate(lum):
        along = -((a0 + a1) / 2) + U[i, 0]           # m, relative to the model nose (- = behind)
        side = row[np.abs(v) > 8.5]; bg = np.median(side); on = row > bg + 18
        c = np.abs(v) <= search
        if not on[c].any(): continue
        kk = int(np.argmax(np.where(c, row, -1e9)))
        if not on[kk]: continue
        i0 = kk
        while i0 > 0 and on[i0 - 1]: i0 -= 1
        i1 = kk
        while i1 < len(on) - 1 and on[i1 + 1]: i1 += 1
        wdt = v[i1] - v[i0] + res
        if 0.7 * W <= wdt <= 1.3 * W: rows.append((along, (v[i0] + v[i1]) / 2))
    n_try = len(lum)
    if len(rows) < 25: return None
    A = np.array(rows); keep = np.ones(len(A), bool)
    for _ in range(3):
        c1, c0 = np.polyfit(A[keep, 0], A[keep, 1], 1)
        r = A[:, 1] - (c0 + c1 * A[:, 0]); new = np.abs(r) < 0.6
        if new.sum() < 20 or (new == keep).all(): break
        keep = new
    rms = float(np.sqrt(np.mean(r[keep] ** 2)))
    relief = (k or 0.0) * H_FUS[grp] * math.cos(math.radians(hdg))
    c0c = c0 - relief
    # the fitted line in the model frame: lateral(a) = c0c + c1 * a (a <= 0 behind the nose)
    return {'lat_nose': round(float(c0c), 2), 'lat_30': round(float(c0c - 30 * c1), 2), 'dh': round(float(math.degrees(math.atan(c1))), 2),
            'n': int(keep.sum()), 'n_try': n_try, 'rms': round(rms, 2), 'relief_lat': round(relief, 2),
            'span_used': [round(float(A[keep, 0].min()), 1), round(float(A[keep, 0].max()), 1)]}


def main(names):
    N = Naip(); k = json.load(open(os.path.join(WORK, 'naip_relief.json')))['k']
    D = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    out = old.get('stands', {}) if names else {}
    for s in D['stands']:
        if names and s['name'] not in names: continue
        grp = 'wide' if s['cls'] in ('D', 'E', 'EL', 'F') else 'narrow'
        r = axis_fit(N, s['nose'], s['hdg'], grp, a1=45.0 if grp == 'wide' else 30.0, k=k)
        out[s['name']] = r
        if r: print('%-5s %-6s lat_nose %+5.2f lat_30 %+5.2f dh %+5.1f  n %3d/%3d rms %.2f (relief %+.2f)' % (
            s['name'], grp, r['lat_nose'], r['lat_30'], r['dh'], r['n'], r['n_try'], r['rms'], r['relief_lat']))
    json.dump({'k': k, 'note': __doc__.split('\n')[0], 'stands': out}, open(OUT, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
