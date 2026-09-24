"""Detect a parked aircraft on a stand axis in NAIP 2024 (0.6 m GSD, acquired 2024-05-20) and measure its nose tip
(along the axis) and its fuselage axis (lateral offset and heading) relative to the stand's reference line.

Method (per stand): resample an oriented patch (0.2 m px) with the stand heading up; per row u (m along, + ahead of
the reference stop point) compare the luminance of the central strip |v| < 1.3 m with a per-row background estimated
on side strips 6-9 m off the axis (outside the fuselage, inside most wing roots only near the wing): pixels differing
by > 22 grey levels, or strongly saturated (painted fuselages), are 'object'. The nose is the forward end of the first
>= 10 m long run of rows whose central strip is >= 55 % object, searched from 25 m ahead of the stop point backwards.
The fuselage centre per row = centroid of object pixels within |v| < 3.5 m in rows (nose-14 .. nose-3) and
(nose-34 .. nose-22); a line through both gives the lateral offset at the nose and the heading residual.
The automatic result is only a proposal: every stand is checked by eye on the montage (tools/stands/naip_review.py) and
overridden in tools/stands/naip_obs.py where wrong. Relief displacement of a ~4 m high fuselage in NAIP (off-nadir
view, orthorectified to the ground) shifts it EAST by about 0.54 m per m of height (review round 2, naip_relief.py:
1.2-2.9 m for a fuselage - the earlier "up to ~1 m" was wrong); nose positions are +/- ~1.5 m after that correction.
"""
import math
import numpy as np
import cv2
from common import hdg_vec

RES = 0.2


def measure(N, stop, hdg, ahead=25.0, behind=75.0, half=12.0):
    L = ahead + behind
    f = hdg_vec(hdg)
    cx = stop[0] + f[0] * (ahead - behind) / 2; cz = stop[1] + f[1] * (ahead - behind) / 2
    img, U, V = N.patch(cx, cz, hdg, L, 2 * half, RES)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    Lum = lab[..., 0]; chroma = np.hypot(lab[..., 1] - 128, lab[..., 2] - 128)
    u = U[:, 0]; v = V[0, :]
    side = (np.abs(v) > 6.0) & (np.abs(v) < 9.0)
    bg = np.median(Lum[:, side], axis=1)[:, None]
    bgc = np.median(chroma[:, side], axis=1)[:, None]
    obj = (np.abs(Lum - bg) > 22) | (chroma - bgc > 14)
    obj = cv2.morphologyEx(obj.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    cen = np.abs(v) < 1.3
    fc = obj[:, cen].mean(axis=1)
    on = fc >= 0.55
    # rows are ordered from +ahead (row 0) to -behind; find first run of >= 10 m
    need = int(10.0 / RES); nose = None
    run = 0
    for i in range(len(u)):
        run = run + 1 if on[i] else 0
        if run >= need:
            i0 = i - need + 1
            # extend forward over short gaps (cockpit windows, cab shadow): back up while on within 1 m gaps
            j = i0
            while j > 0 and (on[j - 1] or (j > 5 and on[max(0, j - 5):j].any())):
                j -= 1
            nose = float(u[j]); break
    if nose is None: return {'present': False, 'fc_max': round(float(fc.max()), 2)}
    wide = np.abs(v) < 3.5
    def centre(a0, a1):
        m = (u <= a0) & (u >= a1)
        if m.sum() < 5: return None
        W = obj[m][:, wide]; vv = v[wide]
        cols = W.sum(axis=0)
        if cols.sum() < 20: return None
        return float((cols * vv).sum() / cols.sum())
    c1 = centre(nose - 3, nose - 14); c2 = centre(nose - 22, nose - 34)
    out = {'present': True, 'nose': round(nose, 1), 'fc_mean': round(float(fc[(u <= nose) & (u >= nose - 10)].mean()), 2)}
    if c1 is not None: out['lat_front'] = round(c1, 2)
    if c1 is not None and c2 is not None:
        dh = math.degrees(math.atan2(c1 - c2, 19.5))      # + = aircraft nose points to the right of the stand heading
        out['dhdg'] = round(dh, 1); out['lat_rear'] = round(c2, 2)
    return out
