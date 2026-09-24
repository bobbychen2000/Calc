"""Absolute check of NAIP against the FAA runway-end coordinates (task (c), 'vs FAA runway ends').

FAA ends: js/geo.js RWY_ENDS (AirNav / FAA NASR, NAD83), copied in tools/imagery/common.py.
Everything is compared in the world frame (geo.js llToWorld); NAIP is sampled through the exact mapping
world -> lat/lon -> UTM 10N (NAD83), so a perfect NAIP would put every feature exactly where FAA says.

Lateral (cross-track) check: a runway-aligned strip (0.1 m across, 0.5 m along) is sampled over each runway
(150 m in from each end); per 300 m segment the 75th-percentile cross profile shows the two continuous white
runway side stripes (3 ft wide, outer edge at the 200 ft runway edge -> stripe centre +-30.02 m, AC 150/5340-1M
section 2.4 'runway side stripes') and the centreline stripes.  Side-stripe midpoint = measured centreline.
A linear fit along the runway gives the offset (m) and the azimuth difference.  Runways 10/28 and 1/19 are
perpendicular, so their lateral offsets together give the full 2-D NAIP-minus-FAA shift (least squares).

Along-track check (non-displaced ends 10L, 10R, 19L, 19R): longitudinal profile of the threshold-stripe band;
reports the outer edge of the white threshold bar (imaged runway end), the stripe block and, at 19L/19R, the EMAS
edge, all relative to the FAA end (s > 0 = inward).

Writes refs/cache/naip/naip_faa_check_<year>.json and a profile plot.
usage: python3 tools/imagery/naip_faa_check.py [--year 2024]
"""
import argparse, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

STRIPE_T = 30.48 - 0.4572      # side-stripe centre from the centreline (m), 200 ft runway, 3 ft stripe


def peak(t, p, t0, win=3.0):
    """sub-sample peak position: centroid of the part of the peak above half height, within t0 +- win."""
    m = (t > t0 - win) & (t < t0 + win)
    tt, pp = t[m], p[m]
    i = int(np.argmax(pp)); base = np.percentile(pp, 20); half = base + 0.5 * (pp[i] - base)
    j0 = i
    while j0 > 0 and pp[j0 - 1] > half: j0 -= 1
    j1 = i
    while j1 < len(pp) - 1 and pp[j1 + 1] > half: j1 += 1
    w = pp[j0:j1 + 1] - half
    return float((tt[j0:j1 + 1] * w).sum() / w.sum()), float(pp[i] - base), float(tt[j1] - tt[j0])


def runway_frame(a, b):
    A = np.array(world_geojs(*RWY_ENDS[a]), float); B = np.array(world_geojs(*RWY_ENDS[b]), float)
    L = float(np.linalg.norm(B - A)); v = (B - A) / L; n = np.array([-v[1], v[0]])   # n = right of a->b
    return A, B, L, v, n


def lateral(S, a, b, seg=300.0):
    A, B, L, v, n = runway_frame(a, b)
    t = np.arange(-40, 40, 0.1); rows = []
    for s0 in np.arange(150, L - 150 - seg / 2, seg):
        s = np.arange(s0, min(s0 + seg, L - 150), 0.5)
        SS, TT = np.meshgrid(s, t, indexing='ij')
        G = S(A[0] + SS * v[0] + TT * n[0], A[1] + SS * v[1] + TT * n[1])
        p = np.percentile(G, 75, axis=0)
        (tl, hl, wl), (tr, hr, wr), (tc, hc, wc) = peak(t, p, -STRIPE_T), peak(t, p, STRIPE_T), peak(t, p, 0.0)
        rows.append(dict(s=float(s.mean()), left=tl, right=tr, mid=(tl + tr) / 2, cl=tc, width=tr - tl,
                         contrast=[hl, hr, hc], stripe_w=[wl, wr, wc]))
    s = np.array([r['s'] for r in rows]); m = np.array([r['mid'] for r in rows])
    k, c = np.polyfit(s - L / 2, m, 1)
    return dict(runway=f'{a}-{b}', length_geojs=L, normal=n.tolist(), segments=rows, offset_mid_m=float(c),
                slope_m_per_km=float(k * 1000), az_diff_deg=float(math.degrees(math.atan(k))),
                seg_std_m=float(np.std(m - (k * (s - L / 2) + c))), mean_width_m=float(np.mean([r['width'] for r in rows])),
                cl_minus_mid_m=float(np.mean([r['cl'] - r['mid'] for r in rows])))


def along(S, end, other):
    """longitudinal profile of the threshold band.  At all four non-displaced ends NAIP shows (inward from the end):
    a ~3 m white threshold bar starting at s ~ 0, a ~2 m gap, then the 150 ft threshold stripes.  The bar's outer
    (runway-end side) edge is taken as the imaged runway end; reported = its position relative to the FAA end."""
    A, B, L, v, n = runway_frame(end, other)
    s = np.arange(-60, 150, 0.1)
    t = np.r_[np.arange(-26, -3, 0.25), np.arange(3, 26, 0.25)]
    SS, TT = np.meshgrid(s, t, indexing='ij')
    G = S(A[0] + SS * v[0] + TT * n[0], A[1] + SS * v[1] + TT * n[1])
    p = np.percentile(G, 60, axis=1)
    def cross(i0, i1, thr, rising):
        for i in range(i0, i1):
            a, b = p[i], p[i + 1]
            if (rising and a < thr <= b) or (not rising and a >= thr > b):
                return float(s[i] + (thr - a) / (b - a) * 0.1)
        return None
    k = lambda v_: int(np.argmin(np.abs(s - v_)))
    bar_hi = float(p[k(-3):k(6)].max())
    lo_in = float(np.median(p[k(-8):k(-1.5)]))                   # pavement just outside the bar
    thr = 0.5 * (lo_in + bar_hi)
    i_peak = k(-3) + int(np.argmax(p[k(-3):k(6)]))
    r0 = None
    for i in range(i_peak, k(-8), -1):                             # walk outward from the bar peak
        if p[i] < thr <= p[i + 1]: r0 = float(s[i] + (thr - p[i]) / (p[i + 1] - p[i]) * 0.1); break
    f0 = cross(i_peak, k(8), 0.5 * (float(np.min(p[i_peak:k(8)])) + bar_hi), False)
    st = cross(k(3), k(12), 0.5 * (float(np.min(p[i_peak:k(8)])) + float(np.median(p[k(10):k(45)]))), True)
    se = cross(k(40), k(60), 0.5 * (float(np.median(p[k(10):k(45)])) + float(np.median(p[k(60):k(140)]))), False)
    # EMAS / pavement change beyond the end (EMAS beds at 1L/1R/19L/19R, AC 150/5220-22; published setback 35 ft)
    o = None
    if end in ('19L', '19R'):
        far = float(np.median(p[k(-50):k(-20)])); near = float(np.min(p[k(-15):k(-3)]))
        for i in range(k(-3), k(-30), -1):
            if p[i] <= 0.5 * (far + near) < p[i - 1]: o = float(s[i]); break
    return dict(end=end, bar_outer_edge_m=r0, bar_inner_edge_m=f0, bar_width_m=(f0 - r0) if (f0 and r0) else None,
                stripes_start_m=st, stripes_end_m=se, stripes_len_m=(se - st) if (se and st) else None,
                emas_edge_m=o, profile_s=s[::5].tolist(), profile=p[::5].tolist())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--year', default='2024'); a = ap.parse_args()
    S = NaipSampler(a.year)
    out = dict(year=a.year, lateral={}, along={})
    Nmat, obs = [], []
    for p, q in RWY_PAIRS:
        r = lateral(S, p, q); out['lateral'][r['runway']] = r
        Nmat.append(r['normal']); obs.append(r['offset_mid_m'])
        print(f"{r['runway']}: NAIP c/l is {r['offset_mid_m']:+.2f} m (right of {p}->{q} = +), az diff {r['az_diff_deg']:+.4f} deg, "
              f"segment scatter {r['seg_std_m']:.2f} m, stripe spacing {r['mean_width_m']:.2f} m (nominal {2 * STRIPE_T:.2f}), "
              f"c/l stripe - midpoint {r['cl_minus_mid_m']:+.2f} m")
    d, res, *_ = np.linalg.lstsq(np.array(Nmat), np.array(obs), rcond=None)
    resid = np.array(obs) - np.array(Nmat) @ d
    out['shift_naip_minus_faa_world'] = dict(dx_east_m=float(d[0]), dz_south_m=float(d[1]), norm_m=float(np.hypot(*d)),
                                             residuals_m=resid.tolist())
    print(f'2-D shift NAIP - FAA (world): dx {d[0]:+.2f} m (east), dz {d[1]:+.2f} m (south) = {np.hypot(*d):.2f} m; residuals {np.round(resid, 2)}')
    for e, o in [('10L', '28R'), ('10R', '28L'), ('19L', '1R'), ('19R', '1L')]:
        r = along(S, e, o); out['along'][e] = r
        A, B, L, v, n = runway_frame(e, o)
        r['along_component_of_lateral_shift_m'] = pred = float(np.dot(d, v))
        f = lambda x: 'n/a' if x is None else f'{x:+.2f}'
        print(f"{e}: threshold bar outer edge {f(r['bar_outer_edge_m'])} m inward of FAA end (bar {f(r['bar_width_m'])} m wide); "
              f"stripes {f(r['stripes_start_m'])}..{f(r['stripes_end_m'])} m (len {f(r['stripes_len_m'])}); EMAS edge {f(r['emas_edge_m'])} m; "
              f"along-track part of the lateral 2-D shift {pred:+.2f} m")
    json.dump(out, open(os.path.join(CACHE, f'naip_faa_check_{a.year}.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
