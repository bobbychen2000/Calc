"""Runway edge marking measured on the committed NAIP mosaics, against the FAA NASR runway rectangle.

New for hwd3d (the idea follows sfo3d/tools/imagery/naip_faa_check.py @ a967f9b; the lateral profile method follows
hwd3d/tools/imagery/naip_reg_check.py). Used by tools/build_airport.py (evidence of the runway pavement outline) and
tools/check_airport.py (the check).

FAA AC 150/5340-1M Chg 1, para 2.8 "Runway Edge Marking" (refs/cache/faa/ac150_5340_1m_chg1_p52-54_63.pdf, PDF pages 52-53 = printed 2-16 / 2-17):
"The runway edge marking consists of two parallel stripes, one placed along each edge of the usable runway with the
outer edge of each stripe approximately on the edge of the paved useable runway." ... "minimum width of 36 inches
(90 cm) for runways of 100 feet (30.5 m) or wider in width and at least 18 inches (45 cm) on smaller width runways".
So the NASR width (RWY_WIDTH, ft) should equal the distance between the OUTER edges of the two white edge stripes;
the stripe centres sit width/2 - stripe/2 from the centreline. The stripe width actually painted is not known (the
values above are minimums): the outer edge is computed with the minimum width [inferred], which biases the edge
inward by half of any extra paint width.

Method: stations every STEP m along the NASR axis (skipping 30 m at each end); at each station and side the white
index (gray minus the median of the profile) is averaged over AVG m along the runway and profiled across it in
[W/2 - 5, W/2 + 3] m at 0.05 m; the strongest ridge with contrast >= MIN_C DN whose second-best ridge (>= 1.5 m away) is
< 0.7 x the best is the stripe centre. Per side: median and MAD of (centre + stripe/2 - W/2) over the clean stations
(residual > 0 = the painted edge lies OUTSIDE the NASR rectangle).
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'common')); sys.path.insert(0, os.path.join(HERE, '..', 'imagery'))
import hwd_frame as F                                                     # noqa: E402

FT = 0.3048
STEP, AVG, MIN_C = 15.0, 6.0, 8.0   # m between stations, m averaged along the edge, DN minimum stripe contrast [chosen; G5]
STRIPE_MIN = {150: 36 * 0.0254, 75: 18 * 0.0254}    # AC 150/5340-1M Chg 1 para 2.8 minimum stripe width (m)


def measure(N, rwy):
    """rwy = '10L/28R' | '10R/28L' -> dict per side ('left' / 'right' of the direction from the first end)"""
    a, b = rwy.split('/'); D = F.RWY_DATA[rwy]; W = D['widthFt'] * FT; sw = STRIPE_MIN[D['widthFt']]
    A = F.rwy_axis(a); L = A['length']; d = np.array(A['dir']); rt = np.array(A['right']); o0 = np.array(A['origin'])
    res = {'right': [], 'left': []}; n_st = 0
    for s in np.arange(30.0, L - 30.0 + 1e-9, STEP):
        n_st += 1; c = o0 + s * d
        for side, sg in (('right', 1.0), ('left', -1.0)):
            off = np.arange(W / 2 - 5.0, W / 2 + 3.0 + 1e-9, 0.05); al = np.linspace(-AVG / 2, AVG / 2, 13)
            O, Al = np.meshgrid(off, al)
            X = c[0] + sg * O * rt[0] + Al * d[0]; Z = c[1] + sg * O * rt[1] + Al * d[1]
            y = N.sample(X, Z, 'gray').mean(axis=0); y = y - np.median(y)
            k = int(np.argmax(y)); cst = float(y[k])
            if cst < MIN_C or k in (0, len(y) - 1): continue
            sec = y[np.abs(off - off[k]) > 1.5]
            if sec.size and sec.max() >= 0.7 * cst: continue
            dd = y[k - 1] - 2 * y[k] + y[k + 1]
            pk = off[k] + (0.5 * 0.05 * (y[k - 1] - y[k + 1]) / dd if dd < 0 else 0.0)
            res[side].append((float(s), float(pk + sw / 2 - W / 2), cst))
    out = {'runway': rwy, 'naip': N.jpeg, 'naip_flight_dates': N.flight, 'nasr_width_m': round(W, 3), 'stripe_min_m': round(sw, 3),
           'stations': n_st}
    for side, v in res.items():
        r = np.array([q[1] for q in v])
        if len(r) == 0:
            out[side] = None; continue
        med = float(np.median(r)); mad = float(np.median(np.abs(r - med)))
        clean = np.abs(r - med) <= max(3 * 1.4826 * mad, 0.15)
        out[side] = {'n': int(len(r)), 'n_clean': int(clean.sum()), 'median_m': round(float(np.median(r[clean])), 3),
                     'mad_m': round(mad, 3), 'p10_m': round(float(np.percentile(r[clean], 10)), 3),
                     'p90_m': round(float(np.percentile(r[clean], 90)), 3)}
    if out['right'] and out['left']:
        out['width_naip_m'] = round(W + out['right']['median_m'] + out['left']['median_m'], 3)
        out['centre_offset_right_m'] = round((out['right']['median_m'] - out['left']['median_m']) / 2, 3)
    return out
