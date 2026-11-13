#!/usr/bin/env python3
"""Measures runway paint positions on NAIP 2024 along the runway axes (P2, Phase 2 dev tool).

The committed NAIP 2024 mosaic (refs/cache/naip/naip_2024_hwd_rgb.jpg, USDA, public domain; 0.6 m pixels) is sampled
bilinearly (tools/imagery/common.py NaipSampler: world -> NAD83 lat/lon -> UTM 10N -> pixel) on lines parallel to each
runway axis from the FAA NASR ends (same frame as js/geo.js). Bright runs (white paint) are found where the brightness
exceeds the local pavement median by `k` DN; their along-runway ends are interpolated to sub-pixel at half height.
Positions are in feet from the end's threshold (displaced threshold where NASR has one), the AC 150/5340-1M reference.

Prints, per runway end:
  - threshold stripes: start / end of the white run at the across offset of a stripe centre;
  - aiming point (10R / 28L): start / end of the run at the across offset of the bar centre (30 ft wide, 72 ft apart);
  - displaced-area centreline arrows (10R / 28L): tip positions (the far end of each white run on the axis);
  - designation glyph extents on the axis (L / R stacked letter and the numeral box).
Expected accuracy: +-0.5 px = +-1 ft for a crisp edge; NAIP edges are blurred over ~1.5 px.

usage (from hwd3d/): python3 dev/measure_paint.py
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'imagery'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
from common import NaipSampler  # noqa: E402
import hwd_frame as F  # noqa: E402

FT = 0.3048


def end_xz(e):
    E = F.RWY_ENDS[e]; w = F.ll_to_world(E["lat"], E["lon"]); return np.array([w[0], w[1]])


def thr_xz(e):
    E = F.RWY_ENDS[e]
    if E.get('thrLat') is None: return end_xz(e)
    w = F.ll_to_world(E["thrLat"], E["thrLon"]); return np.array([w[0], w[1]])


def axis(e, o):
    a, b = end_xz(e), end_xz(o); d = (b - a) / np.linalg.norm(b - a); r = np.array([-d[1], d[0]])   # right of travel
    return a, d, r


def runs(prof, s, k, min_len_ft=2.0):
    """bright runs of prof (DN) above (median + k); returns [(start_ft, end_ft)] at half height"""
    base = np.median(prof); thr = base + k
    on = prof > thr; out = []; i = 0; n = len(prof)
    while i < n:
        if not on[i]: i += 1; continue
        j = i
        while j + 1 < n and on[j + 1]: j += 1
        def cross(a, b):   # sub-sample crossing of thr between samples a (below) and b (above)
            if a < 0 or a >= n: return s[b]
            pa, pb = prof[a], prof[b]; t = (thr - pa) / (pb - pa) if pb != pa else 0.5
            return s[a] + (s[b] - s[a]) * t
        st = cross(i - 1, i); en = cross(j + 1, j)
        if en - st >= min_len_ft: out.append((round(st, 1), round(en, 1)))
        i = j + 1
    return out


def main():
    N = NaipSampler('2024', prefer='jpg')
    res = {}
    step = 0.25 * FT
    for e, o in (('10R', '28L'), ('28L', '10R'), ('10L', '28R'), ('28R', '10L')):
        a, d, r = axis(e, o); t = thr_xz(e); disp = float(np.dot(t - a, d))   # m from the end
        Wft = 150 if e in ('10R', '28L') else 75
        # along positions in ft from the threshold, -900 .. +1400
        s = np.arange(-disp / FT - 40, 1400, step / FT)
        def prof(across_ft, width_ft=1.0):
            vals = []
            for q in np.linspace(-width_ft / 2, width_ft / 2, 3):
                pts = a[None, :] + d[None, :] * (disp + s[:, None] * FT) + r[None, :] * (across_ft + q) * FT
                vals.append(N.sample_world(pts[:, 0], pts[:, 1]))
            return np.mean(vals, 0)
        R = {'displacement_ft': round(disp / FT, 1)}
        # threshold stripes: centre of the first stripe off the axis (5.75 + 5.75/2 ft) and of the third
        st = prof(5.75 + 2.875, 2.0); rr = [x for x in runs(st, s, 40) if -15 < x[0] < 60]
        R['threshold_stripe_run_ft'] = rr[:2]
        if Wft == 150:
            ap = prof(36 + 15, 8.0); R['aiming_point_run_ft'] = [x for x in runs(ap, s, 40) if 900 < x[0] < 1200]
            cl = prof(0, 1.0); R['axis_runs_before_threshold_ft'] = [x for x in runs(cl, s, 40) if x[1] < 0]
        cl = prof(0, 1.0)
        R['axis_runs_0_400_ft'] = [x for x in runs(cl, s, 40) if 0 < x[0] < 420]
        res[e] = R
        print(e, json.dumps(R))
    out = os.path.join(ROOT, 'out', 'phase2', 'naip_paint_measure.json')
    json.dump(res, open(out, 'w'), indent=1); print('->', out)


if __name__ == '__main__':
    main()
