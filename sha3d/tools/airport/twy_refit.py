"""Re-fit OSM taxiway centrelines to the Sentinel-2 pavement where it can be measured (pinned OSM extract).

usage: python3 -I sha3d/tools/airport/twy_refit.py SHA3D_DIR OUT_JSON OUT_PNG

Method (as docs/phase0/geo.md s.4, run on the pinned extract and on both scenes):
* every aeroway=taxiway way is split into straight runs (vertices within 1 m of the chord, run >= 100 m);
* per run and scene, cross profiles of B04 and B08 every 2.5 m along the run, 0.25 m apart, +-(width/2 + 24 m),
  sampled in the S2 registration (OSM position minus the scene's common OSM-S2 offset, geo.md), so what is measured
  is the run's offset relative to the common registration - the OSM frame (OD0) stays as it is;
* median profile, mirror-symmetry centre c (SSD of m(c+t) vs m(c-t), parabolic refinement), bootstrap SD over
  stations (30 draws); a band is usable when the profile is symmetric (q < 0.08), the centre is not at the search
  limit, SD < 2 m and pavement contrast > 150 DN; bands must agree within 3 m;
* pavement width: full width at half depth of the median NDVI profile (grass high, pavement low), reported only
  when both sides cross the half level (blurred by the 10 m pixels: an estimate, +-3 m);
* a scene's centre is used only when its NDVI profile reaches vegetation on both sides (pavement bounded by grass:
  next to an apron or a wide paved junction the symmetry centre is pulled into the paved expanse - seen at D);
* edge centre (QA C1 M1 fix, 2026-11-14): where the symmetry test fails because the two sides have different grass
  levels, the midpoint of the two half-level crossings (each side's own level) is used instead: S2 on the NDVI median
  profile (both sides must reach vegetation), Umbra on the amplitude profile (grass > 3x pavement on each side, width
  15-70 m); bootstrap SD < 2.0 m (S2) / 1.5 m (Umbra) over stations; when both estimators exist for a source and
  differ by more than 4 m, that source is ambiguous and not used;
* Umbra (1.4 m overview): the same symmetry centre on the amplitude profile, usable when q < 0.10, SD < 1.5 m and the
  grass on EACH side is > 2x brighter than the pavement (else the edge centre above). The Umbra registration (Umbra
  minus OSM) is measured on the RUNWAY bands, not on the taxiways (QA C1 M1: a fit on the taxiway runs absorbs the
  taxiway errors): along both OSM runway centrelines every 50 m (300 m from the ends), the dark paved band (runway +
  shoulders, AIP (mirror) widths 45 / 60 m + 2 x 7.5 m) is located from its half-level edges; the median cross-track
  offset is the east shift (north-south shift 0: docs/phase1/stands.md s.2);
* a run is MEASURED when at least 2 of the 3 sources (S2B, S2C, Umbra) agree within 2.0 m, or (runs >= 150 m) when
  Umbra and one S2 scene agree within 2.5 m (QA C1 M1; for this rule the confirming S2 value may be a single band
  centre with relaxed symmetry q < 0.15, SD < 2 m, contrast > 150 DN, grass on both sides); c = their mean;
* a run is RE-FITTED when measured and |c| >= 3.5 m (about 3x the median source spread): its vertices move by c
  along the run normal. A vertex shared by
  several re-fitted runs takes the mean move; vertices on a runway centreline are never moved. Connectivity is kept
  because every way that shares a vertex (same coordinates) gets the same move (applied by build_airport.py).
* Umbra veto (re-verify N2, fix round 2): a run measured by S2 alone is NOT moved when the usable Umbra centre
  dissents (> 2.5 m) and the move would take the line further from it (|UMB - c| > |UMB|): Umbra (1.4 m) is the
  sharper source. A dissenting Umbra that asks for a larger move in the same direction does not block it.
* junction taper (re-verify N2): a moved vertex is moved identically in every way that shares it, and in each
  taxiway / taxilane way that continues from it unmoved, the move is tapered linearly to zero over TAPER_M = 40 m
  of arc length (a 3.5-7.7 m move then bends the way by at most about 5-11 deg and never reverses a segment). The
  taper stops (weight 0) at the next vertex that is shared with another feature (junction, lead-in, holding
  position, apron outline), on a runway centreline or itself moved; tapers from two moved vertices add up, so a
  short link between two moved vertices is translated. Tapered vertices are listed in vertex_moves with
  kind = 'taper'; junction_check in the summary gives the turn angles added and any reversed / short segment.
Output: per run the scene centres, widths, flags, and the vertex moves (keyed by the vertex lon/lat rounded to 1e-7).
"""
import json
import math
from collections import Counter
import os
import sys

import numpy as np
from scipy.ndimage import median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
import imgsample as IS  # noqa: E402
import umbra_reg as UR  # noqa: E402

MIN_RUN = 100.0
TOL = 1.0
AGREE = 2.0
AGREE_UMB_S2 = 2.5       # Umbra + one S2 scene, runs >= LONG_RUN (QA C1 M1)
LONG_RUN = 150.0
Q_RELAXED = 0.15         # rule (b) only: S2 band symmetry residual allowed for the confirming scene
EDGE_CONFLICT = 4.0      # symmetry centre and edge centre of the same source differ by more: the source is ambiguous
REFIT = 3.5
TAPER_M = 40.0           # junction taper length along an unmoved neighbouring way (re-verify N2)
W_DEFAULT = 23.0
RWY_PAVED_W = {'18L/36R': 45.0 + 2 * 7.5, '18R/36L': 60.0 + 2 * 7.5}   # AIP (mirror) width + 2 x shoulder (aip_facts)


def vkey(lon, lat):
    return f'{lon:.7f},{lat:.7f}'


def straight_runs(P, tol=TOL, min_len=MIN_RUN):
    runs, i = [], 0
    while i < len(P) - 1:
        j = i + 1
        while j + 1 < len(P):
            p0, p1 = P[i], P[j + 1]
            L = np.linalg.norm(p1 - p0)
            u = (p1 - p0) / L
            nn = np.array([-u[1], u[0]])
            dev = max(abs((P[k] - p0) @ nn) for k in range(i, j + 2))
            if dev > tol:
                break
            j += 1
        L = float(np.linalg.norm(P[j] - P[i]))
        if L >= min_len:
            runs.append((i, j, L))
        i = j
    return runs


def sym_centre(mp, tt, cmax):
    dt = tt[1] - tt[0]
    taus = np.arange(1.0, tt[-1] - cmax, dt)
    cs = np.arange(-cmax, cmax + 1e-9, 0.25)
    ssd = np.array([np.mean((np.interp(c + taus, tt, mp) - np.interp(c - taus, tt, mp)) ** 2) for c in cs])
    k = int(np.argmin(ssd))
    c = cs[k]
    if 0 < k < len(cs) - 1:
        y0, y1, y2 = ssd[k - 1], ssd[k], ssd[k + 1]
        den = y0 - 2 * y1 + y2
        if den > 0:
            c = cs[k] + 0.5 * (y0 - y2) / den * 0.25
    return float(c), float(ssd[k] / max(np.var(mp), 1e-9)), (k == 0 or k == len(cs) - 1)


def fwhm(tt, prof):
    """width where the profile is below half-way between its centre level and its outer level (pavement = low)."""
    inner = np.median(prof[np.abs(tt) < 4]); outer = np.median(prof[np.abs(tt) > tt[-1] - 6])
    if outer - inner < 0.08:
        return None
    half = 0.5 * (inner + outer)
    below = prof < half
    c = len(tt) // 2
    if not below[c]:
        return None
    l = c
    while l > 0 and below[l]:
        l -= 1
    r = c
    while r < len(tt) - 1 and below[r]:
        r += 1
    if l == 0 or r == len(tt) - 1:
        return None

    def cross(i0, i1):
        y0, y1 = prof[i0] - half, prof[i1] - half
        return tt[i0] + (tt[i1] - tt[i0]) * (y0 / (y0 - y1)) if y0 != y1 else tt[i0]
    return float(cross(r - 1, r) - cross(l, l + 1))


def edge_centre(tt, prof, dark_low=True, side_lo=6.0, ratio=None, wmin=15.0, wmax=70.0):
    """midpoint of the two half-level crossings around t = 0, each side with its OWN outer level (robust to different
    grass levels left and right). dark_low: the pavement is the low part of the profile. Side levels = median over
    T - 16 < |t| < T - side_lo (T = half the profile length). ratio (Umbra): outer / inner > ratio on EACH side; else
    (S2 NDVI) outer - inner > 0.08 on each side. Returns (centre, width) or None."""
    p = prof if dark_low else -prof
    inner = np.median(p[np.abs(tt) < 4])
    T = tt[-1]
    lo_out = np.median(p[(tt < -(T - 16)) & (tt > -(T - side_lo))]); hi_out = np.median(p[(tt > T - 16) & (tt < T - side_lo)])
    if ratio is not None and not (lo_out > ratio * max(inner, 1e-6) and hi_out > ratio * max(inner, 1e-6)):
        return None
    if ratio is None and (lo_out - inner < 0.08 or hi_out - inner < 0.08):
        return None
    c = len(tt) // 2
    ml, mr = 0.5 * (inner + lo_out), 0.5 * (inner + hi_out)
    if not (p[c] < ml and p[c] < mr):
        return None
    l = c
    while l > 0 and p[l - 1] < ml:
        l -= 1
    r = c
    while r < len(tt) - 1 and p[r + 1] < mr:
        r += 1
    if l == 0 or r == len(tt) - 1:
        return None

    def cross(i0, i1, m):
        y0, y1 = p[i0] - m, p[i1] - m
        return tt[i0] + (tt[i1] - tt[i0]) * (y0 / (y0 - y1)) if y0 != y1 else tt[i0]
    tl = cross(l - 1, l, ml); tr = cross(r, r + 1, mr)
    w = tr - tl
    if not (wmin <= w <= wmax):
        return None
    return float(0.5 * (tl + tr)), float(w)


def runway_band_registration(fc, sc0, um):
    """Umbra minus OSM (E, N) from the dark paved band of both runways (QA C1 umb_reg.py method)"""
    per, allt = {}, []
    for f in fc['features']:
        t = f['properties']['tags']
        if t.get('aeroway') != 'runway' or f['geometry']['type'] != 'LineString' or t.get('ref') not in RWY_PAVED_W:
            continue
        cs = f['geometry']['coordinates']
        E, N = sc0.tr.transform(np.array([cs[0][0], cs[-1][0]]), np.array([cs[0][1], cs[-1][1]]))
        p0 = np.array([E[0], N[0]]); p1 = np.array([E[1], N[1]])
        L = float(np.linalg.norm(p1 - p0)); u = (p1 - p0) / L
        e = np.array([u[1], -u[0]])
        if e[0] < 0:
            e = -e
        pav = RWY_PAVED_W[t['ref']]
        tt = np.arange(-90, 90.1, 0.5); aa = np.arange(-20, 20.1, 2.0)
        offs = []
        for s_ in np.arange(300, L - 300, 50):
            c = p0 + s_ * u
            TT, AA = np.meshgrid(tt, aa, indexing='ij')
            lon, lat = sc0.inv.transform(c[0] + TT * e[0] + AA * u[0], c[1] + TT * e[1] + AA * u[1])
            prof = np.nanmedian(um.sample(lon, lat), axis=1)
            grass = np.nanmedian(prof[np.abs(tt) > pav / 2 + 15]); pave = np.nanmedian(prof[np.abs(tt) < pav / 2 - 10])
            if not grass > 2.5 * pave:
                continue
            mid = 0.5 * (grass + pave); ins = prof < mid; i0 = int(np.argmin(np.abs(tt)))
            if not ins[i0]:
                continue
            l = i0
            while l > 0 and ins[l - 1]:
                l -= 1
            r = i0
            while r < len(tt) - 1 and ins[r + 1]:
                r += 1
            tl = tt[l] - 0.5 * (mid - prof[l]) / max(prof[l - 1] - prof[l], 1e-6) if l > 0 else tt[l]
            tr = tt[r] + 0.5 * (mid - prof[r]) / max(prof[r + 1] - prof[r], 1e-6) if r < len(tt) - 1 else tt[r]
            if abs((tr - tl) - pav) > 12:
                continue
            offs.append(0.5 * (tl + tr))
        per[t['ref']] = dict(n=len(offs), median_m=round(float(np.median(offs)), 2) if offs else None,
                             east_normal=[round(float(e[0]), 4), round(float(e[1]), 4)])
        allt += [(o, e) for o in offs]
    med = float(np.median([o for o, _ in allt]))
    eE = float(np.mean([e[0] for _, e in allt]))
    return dict(dE=round(med / eE, 2), dN=0.0, n_stations=len(allt), per_runway=per,
                method='median cross-track centre of the dark paved band (half-level edges) on both runways, Umbra '
                       '1.4 m overview, stations every 50 m from 300 m to L - 300 m, +-20 m along-track median; '
                       'north-south component 0 (docs/phase1/stands.md s.2: Umbra and Sentinel-2 agree N-S at H2)',
                compare='A2 (stands.md s.2) +3.44 m E on 6 full-resolution bands; the former taxiway Huber fit '
                        '(+6.14 E, -0.89 N) is kept only as a diagnostic')


def main(root, out_json, out_png):
    fc = json.load(open(os.path.join(root, 'refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
    scenes = [IS.S2(os.path.join(root, 'refs/cache/s2', n)) for n in IS.S2_OFFSETS]
    um = IS.Umbra(os.path.join(root, 'refs/cache/imagery/umbra_opendata/umbra_gec_ovr4.tif'))
    rng = np.random.default_rng(7)
    nod = {'s2': 0}
    reg = runway_band_registration(fc, scenes[0], um)
    # the measured value is the single Phase-1 Umbra registration (tools/common/umbra_reg.py, re-verify N4): stop if
    # the measurement and the constant the other tools use ever drift apart
    assert abs(reg['dE'] - UR.UMBRA_MINUS_OSM_EN[0]) <= 0.05 and abs(reg['dN'] - UR.UMBRA_MINUS_OSM_EN[1]) <= 0.05, \
        'Umbra registration %s differs from tools/common/umbra_reg.py %s' % ((reg['dE'], reg['dN']), UR.UMBRA_MINUS_OSM_EN)
    reg['single_value_note'] = ('this is the single Phase-1 Umbra registration (tools/common/umbra_reg.py), applied by '
                                'twy_refit, stand_sar, stands_plates and sar_registration')
    runway_keys = set()
    for f in fc['features']:
        if f['properties']['tags'].get('aeroway') == 'runway' and f['geometry']['type'] == 'LineString':
            runway_keys.update(vkey(*c) for c in f['geometry']['coordinates'])
    runs_out = []
    for f in fc['features']:
        t = f['properties']['tags']
        if t.get('aeroway') != 'taxiway' or f['properties']['@type'] != 'way' or f['geometry']['type'] != 'LineString':
            continue
        coords = f['geometry']['coordinates']
        lon = np.array([c[0] for c in coords]); lat = np.array([c[1] for c in coords])
        E0, N0 = scenes[0].tr.transform(lon, lat)          # OSM registration, UTM 51N
        P = np.c_[E0, N0]
        for (i, j, L) in straight_runs(P):
            p0 = P[i]; u = (P[j] - p0) / L
            n = np.array([-u[1], u[0]])
            if n[0] < 0 or (abs(n[0]) < 1e-9 and n[1] < 0):
                n = -n
            cmax = 14.0
            H = W_DEFAULT / 2 + 24.0 + cmax
            tt = np.arange(-H, H + 1e-9, 0.25)
            st = np.arange(12.0, L - 12.0, 2.5)
            per = {}
            for sc in scenes:
                q0 = p0 - np.array(sc.off)                  # into the S2 registration
                pts_E = (q0[0] + st[:, None] * u[0] + tt[None, :] * n[0])
                pts_N = (q0[1] + st[:, None] * u[1] + tt[None, :] * n[1])
                bands = {}
                for band in ('B04', 'B08'):
                    prof = sc.sample_en(band, pts_E, pts_N)
                    mp = np.median(prof, axis=0)
                    c, q, edge = sym_centre(mp, tt, cmax)
                    boots = [sym_centre(np.median(prof[rng.integers(0, len(st), len(st))], axis=0), tt, cmax)[0]
                             for _ in range(30)]
                    contrast = float(mp[np.abs(tt) < 5].mean() - mp[np.abs(tt) > H - cmax - 4].mean())
                    ok = (not edge) and q < 0.08 and np.std(boots) < 2.0 and abs(contrast) > 150
                    bands[band] = dict(c=round(c, 2), q=round(q, 3), sd=round(float(np.std(boots)), 2),
                                       contrast=round(contrast), ok=bool(ok))
                ndp = sc.ndvi_en(pts_E, pts_N)
                nod['s2'] += int((sc.sample_en('B04', pts_E, pts_N) == 0).sum())
                nd = np.median(ndp, axis=0)
                oks = [b for b in bands.values() if b['ok']]
                cval, csrc = None, None
                if oks and not (len(oks) == 2 and abs(oks[0]['c'] - oks[1]['c']) > 3.0):
                    cval, csrc = round(float(np.mean([b['c'] for b in oks])), 2), 'symmetry'
                w = fwhm(tt, nd)
                ec = edge_centre(tt, nd)
                edge = None
                if ec is not None:
                    eb = [edge_centre(tt, np.median(ndp[rng.integers(0, len(st), len(st))], axis=0)) for _ in range(30)]
                    eb = [x[0] for x in eb if x is not None]
                    esd = float(np.std(eb)) if len(eb) >= 20 else 99.0
                    edge = dict(c=round(ec[0], 2), width=round(ec[1], 1), sd=round(esd, 2), ok=bool(esd < 2.0))
                    if cval is None and edge['ok'] and w:
                        cval, csrc = edge['c'], 'ndvi_edges'
                    elif cval is not None and edge['ok'] and abs(edge['c'] - cval) > EDGE_CONFLICT:
                        cval, csrc = None, 'ambiguous (symmetry %.1f vs NDVI edges %.1f m)' % (cval, edge['c'])
                per[sc.name[:3]] = dict(c=cval, c_method=csrc, bands=bands, ndvi_edges=edge,
                                        width_ndvi_fwhm=round(w, 1) if w else None)
            # Umbra SAR (1.4 m overview): amplitude profile, same geometry, in the OSM registration (its own global
            # offset is removed after all runs are measured)
            lonp, latp = scenes[0].inv.transform(p0[0] + st[:, None] * u[0] + tt[None, :] * n[0],
                                                 p0[1] + st[:, None] * u[1] + tt[None, :] * n[1])
            ua = um.sample(lonp, latp)
            ump = median_filter(np.nanmedian(ua, axis=0), size=5, mode='nearest')
            if np.isfinite(ump).all():
                cu, qu, eu = sym_centre(ump, tt, cmax)
                bu = [sym_centre(median_filter(np.nanmedian(ua[rng.integers(0, len(st), len(st))], axis=0), size=5,
                                               mode='nearest'), tt, cmax)[0] for _ in range(30)]
                inner = max(np.median(ump[np.abs(tt) < 5]), 1e-6)
                ctr = float(min(np.median(ump[tt < -(H - cmax - 4)]), np.median(ump[tt > H - cmax - 4])) / inner)
                ok_sym = bool((not eu) and qu < 0.10 and np.std(bu) < 1.5 and ctr > 2.0)
                ec = edge_centre(tt, ump, ratio=3.0)
                edge = None
                if ec is not None:
                    eb = [edge_centre(tt, median_filter(np.nanmedian(ua[rng.integers(0, len(st), len(st))], axis=0),
                                                        size=5, mode='nearest'), ratio=3.0) for _ in range(30)]
                    eb = [x[0] for x in eb if x is not None]
                    esd = float(np.std(eb)) if len(eb) >= 20 else 99.0
                    edge = dict(c=round(ec[0], 2), width=round(ec[1], 1), sd=round(esd, 2), ok=bool(esd < 1.5))
                use_edge = (not ok_sym) and edge is not None and edge['ok']
                if ok_sym and edge is not None and edge['ok'] and abs(edge['c'] - cu) > EDGE_CONFLICT:
                    ok_sym = False          # the two Umbra estimators disagree: ambiguous
                per['UMB_raw'] = dict(c=round(cu, 2) if not use_edge else edge['c'], q=round(qu, 3),
                                      sd=round(float(np.std(bu)), 2), grass_over_pavement=round(ctr, 2),
                                      symmetry=dict(c=round(cu, 2), ok=ok_sym), edges=edge,
                                      c_method='symmetry' if ok_sym else 'edges' if use_edge else None,
                                      ok=bool(ok_sym or use_edge))
            widths = [v['width_ndvi_fwhm'] for k_, v in per.items() if k_ != 'UMB_raw' and v['width_ndvi_fwhm']]
            runs_out.append(dict(way=f['properties']['@id'], version=f['properties']['@version'], ref=t.get('ref'),
                                 v0=i, v1=j, length_m=round(L, 1),
                                 bearing_deg=round(math.degrees(math.atan2(u[0], u[1])) % 360, 1),
                                 normal_EN=[round(float(n[0]), 4), round(float(n[1]), 4)],
                                 scenes=per,
                                 width_s2_m=round(float(np.mean(widths)), 1) if len(widths) == 2 else None,
                                 keys=[vkey(lon[k], lat[k]) for k in range(i, j + 1)]))
    # diagnostic only (QA C1 M1): the former Umbra offset = Huber least squares over the usable taxiway runs. It absorbs
    # the OSM taxiway errors, so it is NOT applied; the runway-band registration (reg) is.
    U = [r for r in runs_out if r['scenes'].get('UMB_raw', {}).get('ok')]
    A = np.array([r['normal_EN'] for r in U]); y = np.array([r['scenes']['UMB_raw']['c'] for r in U])
    wts = np.ones(len(U))
    for _ in range(30):
        g, *_ = np.linalg.lstsq(A * wts[:, None], y * wts, rcond=None)
        res = y - A @ g
        k = 1.5 * (np.median(abs(res)) * 1.4826 + 1e-6)
        wts = np.where(abs(res) <= k, 1.0, np.sqrt(k / abs(res)))
    huber_diag = dict(dE=round(float(g[0]), 2), dN=round(float(g[1]), 2), n_runs=len(U),
                      rms_resid=round(float(np.sqrt(np.mean(res ** 2))), 2), applied=False)
    g = np.array([reg['dE'], reg['dN']])
    for r in runs_out:
        ur = r['scenes'].get('UMB_raw')
        # a scene counts only if its NDVI profile reaches vegetation on BOTH sides (width_ndvi_fwhm defined): next to
        # an apron or a paved junction the symmetry centre is pulled into the paved expanse (seen at taxiway D)
        cands = {k_: v['c'] for k_, v in r['scenes'].items() if k_ in ('S2B', 'S2C') and v['c'] is not None
                 and v['width_ndvi_fwhm'] is not None}
        r['s2_bounded_by_grass'] = {k_: r['scenes'][k_]['width_ndvi_fwhm'] is not None for k_ in ('S2B', 'S2C')}
        if ur and ur['ok']:
            r['scenes']['UMB'] = round(ur['c'] - (g[0] * r['normal_EN'][0] + g[1] * r['normal_EN'][1]), 2)
            cands['UMB'] = r['scenes']['UMB']
        best = []
        names = list(cands)
        rule = None
        for m_ in range(len(names), 1, -1):          # largest agreeing subset (max - min <= AGREE), >= 2 sources
            from itertools import combinations
            for sub in combinations(names, m_):
                v = [cands[x] for x in sub]
                if max(v) - min(v) <= AGREE and (not best or len(sub) > len(best) or
                                                 (len(sub) == len(best) and np.ptp(v) < np.ptp([cands[x] for x in best]))):
                    best = list(sub)
            if best:
                rule = '>= 2 sources within %.1f m' % AGREE
                break
        if not best and 'UMB' in cands and r['length_m'] >= LONG_RUN:
            # S2 confirmation for rule (b): the scene's accepted centre, else (relaxed symmetry, as different grass
            # levels left and right raise q) a single band centre with q < Q_RELAXED, SD < 2 m, |contrast| > 150 DN,
            # in a scene whose NDVI profile reaches grass on both sides
            s2opt = [(abs(v - cands['UMB']), k_, v, 'accepted') for k_, v in cands.items() if k_ != 'UMB']
            for k_ in ('S2B', 'S2C'):
                if k_ in cands or not r['s2_bounded_by_grass'][k_]:
                    continue
                for bn, bv in sorted(r['scenes'][k_]['bands'].items()):
                    if bv['q'] < Q_RELAXED and bv['sd'] < 2.0 and abs(bv['contrast']) > 150:
                        s2opt.append((abs(bv['c'] - cands['UMB']), k_, bv['c'], '%s band, relaxed symmetry q %.3f'
                                      % (bn, bv['q'])))
            s2opt.sort()
            if s2opt and s2opt[0][0] <= AGREE_UMB_S2:
                _, k_, v, how = s2opt[0]
                cands[k_] = v
                best = sorted([k_, 'UMB']); rule = 'Umbra + %s (%s) within %.1f m (run >= %.0f m)' % (
                    k_, how, AGREE_UMB_S2, LONG_RUN)
        r['sources_used'] = best
        r['rule'] = rule
        r['measured'] = len(best) >= 2
        r['offset_m'] = round(float(np.mean([cands[x] for x in best])), 2) if r['measured'] else None
        r['source_spread_m'] = round(float(np.ptp([cands[x] for x in best])), 2) if r['measured'] else None
        r['refit'] = bool(r['measured'] and abs(r['offset_m']) >= REFIT)
        others = {k_: v for k_, v in cands.items() if k_ not in best}
        r['dissent'] = ({k_: v for k_, v in others.items() if abs(v - r['offset_m']) > AGREE_UMB_S2} or None
                        if r['measured'] else None)
        r['umbra_veto'] = None
        if r['refit'] and r['dissent'] and 'UMB' in r['dissent'] and \
                abs(r['dissent']['UMB'] - r['offset_m']) > abs(r['dissent']['UMB']):
            r['refit'] = False
            r['umbra_veto'] = ('not moved: %s give %+.2f m but the usable Umbra centre is %+.2f m; the move would take '
                               'the line away from the sharper Umbra centre (left at the OSM position)'
                               % ('+'.join(best), r['offset_m'], r['dissent']['UMB']))
        big = {k_: v for k_, v in cands.items() if abs(v) >= REFIT}
        r['single_source_flag'] = (None if r['measured'] or not big else
                                   'not measured: only %s give |offset| >= %.1f m (%s); not moved'
                                   % ('+'.join(sorted(big)), REFIT, ', '.join('%s %+.1f m' % (k_, v)
                                                                            for k_, v in sorted(big.items()))))
    # vertex moves
    moves = {}
    for r in runs_out:
        if not r['refit']:
            continue
        for k in r['keys']:
            if k in runway_keys:
                continue
            moves.setdefault(k, []).append((r['offset_m'] * r['normal_EN'][0], r['offset_m'] * r['normal_EN'][1], r['way']))
    vmoves = {}
    for k, lst in moves.items():
        dE = float(np.mean([a[0] for a in lst])); dN = float(np.mean([a[1] for a in lst]))
        lon, lat = map(float, k.split(','))
        E, N = scenes[0].tr.transform(lon, lat)
        lon2, lat2 = scenes[0].inv.transform(E + dE, N + dN)
        vmoves[k] = dict(to=[round(lon2, 7), round(lat2, 7)], dE=round(dE, 2), dN=round(dN, 2),
                         from_runs=sorted(set(a[2] for a in lst)), kind='run')
    junction_check = junction_taper(fc, scenes[0], vmoves, runway_keys)
    meas = [r for r in runs_out if r['measured']]
    off = np.array([r['offset_m'] for r in meas]) if meas else np.array([0.0])
    summary = dict(runs=len(runs_out), measured=len(meas), refit=sum(r['refit'] for r in runs_out),
                   vertices_moved=len(vmoves),
                   vertices_moved_by_kind=dict(Counter(v['kind'] for v in vmoves.values())),
                   not_moved_umbra_veto=[dict(way=r['way'], ref=r['ref'], v0=r['v0'], v1=r['v1']) for r in runs_out
                                         if r.get('umbra_veto')],
                   junction_check=junction_check,
                   abs_offset_median_m=round(float(np.median(abs(off))), 2),
                   abs_offset_p90_m=round(float(np.percentile(abs(off), 90)), 2),
                   abs_offset_max_m=round(float(abs(off).max()), 2),
                   source_spread_median_m=round(float(np.median([r['source_spread_m'] for r in meas])), 2) if meas else None,
                   measured_by=dict(Counter('+'.join(r['sources_used']) for r in meas)),
                   umbra_registration_umbra_minus_osm=reg,
                   umbra_taxiway_huber_fit_diagnostic=huber_diag,
                   measured_by_rule=dict(Counter(r['rule'] for r in meas)),
                   s2_nodata_samples=nod['s2'],
                   width_s2_median_m=round(float(np.median([r['width_s2_m'] for r in runs_out if r['width_s2_m']])), 1),
                   thresholds=dict(min_run_m=MIN_RUN, agree_m=AGREE, agree_umbra_s2_m=AGREE_UMB_S2,
                                   long_run_m=LONG_RUN, refit_m=REFIT, taper_m=TAPER_M),
                   scene_offsets_osm_minus_s2=IS.S2_OFFSETS)
    out = dict(method=__doc__.split('\n\n')[1], summary=summary, runs=[{k: v for k, v in r.items() if k != 'keys'}
                                                                       for r in runs_out], vertex_moves=vmoves)
    out['attribution'] = ('Contains modified Copernicus Sentinel data 2026; Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0 '
                          '(https://creativecommons.org/licenses/by/4.0/), modified; (c) OpenStreetMap contributors '
                          '(ODbL 1.0); the runway paved widths used for the Umbra registration are AIP (mirror) short '
                          'cited facts (aip_facts), not covered by ODbL')
    out['licence'] = ('measurements on OSM ways: ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/); Sentinel-2: '
                      'Copernicus Sentinel data legal notice; Umbra: CC BY 4.0')
    json.dump(out, open(out_json, 'w'), indent=1)
    print(json.dumps(summary, indent=1))
    for r in sorted(meas, key=lambda r: -abs(r['offset_m']))[:25]:
        print(r['way'], r['ref'], r['length_m'], r['offset_m'], r['sources_used'], r['source_spread_m'], r['width_s2_m'], 'REFIT' if r['refit'] else '')
    plot(runs_out, out_png)


def _turn(a, b, c):
    """turn angle (deg) at b of the polyline a-b-c; None for a degenerate segment"""
    v1, v2 = np.subtract(b, a), np.subtract(c, b)
    if np.hypot(*v1) < 1e-9 or np.hypot(*v2) < 1e-9:
        return None
    d = math.degrees(math.atan2(v2[1], v2[0]) - math.atan2(v1[1], v1[0]))
    return abs((d + 180.0) % 360.0 - 180.0)


def junction_taper(fc, sc, vmoves, runway_keys):
    """Add tapered moves (kind 'taper') to vmoves for the taxiway / taxilane vertices next to moved vertices, and
    return a check of every way touched: turn angles added, reversed and short segments (re-verify N2)."""
    owners = {}
    for fi, f in enumerate(fc['features']):
        g = f['geometry']
        if not g:
            continue
        if g['type'] == 'Point':
            seqs = [[g['coordinates']]]
        elif g['type'] == 'LineString':
            seqs = [g['coordinates']]
        elif g['type'] in ('Polygon', 'MultiLineString'):
            seqs = g['coordinates']
        elif g['type'] == 'MultiPolygon':
            seqs = [r for p in g['coordinates'] for r in p]
        else:
            seqs = []
        for seq in seqs:
            for c in seq:
                owners.setdefault(vkey(*c), set()).add(fi)
    ways = [(fi, f['geometry']['coordinates']) for fi, f in enumerate(fc['features'])
            if f['properties']['tags'].get('aeroway') in ('taxiway', 'taxilane') and f['geometry']['type'] == 'LineString']

    def en(c):
        return np.array(sc.tr.transform(c[0], c[1]))
    core = dict(vmoves)
    contrib = {}
    for fi, cs in ways:
        keys = [vkey(*c) for c in cs]
        for j, k in enumerate(keys):
            if k not in core:
                continue
            m = np.array([core[k]['dE'], core[k]['dN']])
            for d in (-1, 1):
                jj = j + d
                if not 0 <= jj < len(cs) or keys[jj] in core:
                    continue
                path, sarc, prev, s_end = [], 0.0, en(cs[j]), TAPER_M
                while 0 <= jj < len(cs):
                    q = en(cs[jj])
                    sarc += float(np.hypot(*(q - prev)))
                    kk = keys[jj]
                    if sarc >= TAPER_M:
                        break
                    if kk in core or kk in runway_keys or len(owners.get(kk, ())) > 1:
                        s_end = sarc
                        break
                    path.append((kk, sarc))
                    prev = q
                    jj += d
                for kk, sa in path:
                    wgt = 1.0 - sa / s_end
                    c_ = contrib.setdefault(kk, [np.zeros(2), set()])
                    c_[0] += wgt * m
                    c_[1].update(core[k]['from_runs'])
    for kk in sorted(contrib):
        dv, runs_ = contrib[kk]
        if np.hypot(*dv) < 0.01:
            continue
        lon, lat = map(float, kk.split(','))
        E, N = sc.tr.transform(lon, lat)
        lon2, lat2 = sc.inv.transform(E + dv[0], N + dv[1])
        vmoves[kk] = dict(to=[round(lon2, 7), round(lat2, 7)], dE=round(float(dv[0]), 2), dN=round(float(dv[1]), 2),
                          from_runs=sorted(runs_), kind='taper')
    # check every taxiway / taxilane way with a moved vertex: turn angles added at its vertices, segments reversed
    # (new direction against the old one) or shorter than 0.5 m
    touched, added, rev, short, big = 0, [], 0, 0, 0
    for fi, cs in ways:
        keys = [vkey(*c) for c in cs]
        if not any(k in vmoves for k in keys):
            continue
        touched += 1
        P0 = [en(c) for c in cs]
        P1 = [p + (np.array([vmoves[k]['dE'], vmoves[k]['dN']]) if k in vmoves else 0) for p, k in zip(P0, keys)]
        for a in range(len(cs) - 1):
            s0, s1 = P0[a + 1] - P0[a], P1[a + 1] - P1[a]
            rev += int(float(s0 @ s1) <= 0)
            short += int(np.hypot(*s1) < 0.5)
        wmax = 0.0
        for a in range(1, len(cs) - 1):
            t0, t1 = _turn(P0[a - 1], P0[a], P0[a + 1]), _turn(P1[a - 1], P1[a], P1[a + 1])
            if t0 is not None and t1 is not None:
                wmax = max(wmax, t1 - t0)
        added.append(wmax)
        big += int(wmax > 15.0)
    return dict(ways_touched=touched, turn_added_max_deg=round(max(added, default=0.0), 1),
                turn_added_median_deg=round(float(np.median(added)) if added else 0.0, 1),
                ways_with_turn_added_over_15deg=big, reversed_segments=rev, segments_under_0_5m=short,
                taper_m=TAPER_M)


def plot(runs, out_png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    meas = [r for r in runs if r['measured']]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    def cv(r, k):
        v = r['scenes'].get(k)
        v = v['c'] if isinstance(v, dict) else v
        return np.nan if v is None else v
    a = np.array([[cv(r, 'S2B'), cv(r, 'S2C') if not np.isnan(cv(r, 'S2C')) else cv(r, 'UMB')] for r in meas])
    col = ['tab:red' if r['refit'] else 'tab:blue' for r in meas]
    ax[0].scatter(a[:, 0], a[:, 1], c=col, s=14)
    lim = max(4, np.nanmax(np.abs(a)) + 1)
    ax[0].plot([-lim, lim], [-lim, lim], 'k:', lw=0.8)
    for v in (-REFIT, REFIT):
        ax[0].axvline(v, color='0.7', lw=0.6); ax[0].axhline(v, color='0.7', lw=0.6)
    for r in meas:
        if r['refit']:
            ax[0].annotate(f"{r['ref'] or 'way ' + str(r['way'])}", (cv(r, 'S2B'), cv(r, 'S2C') if not np.isnan(cv(r, 'S2C')) else cv(r, 'UMB')),
                           fontsize=6, xytext=(3, 3), textcoords='offset points')
    ax[0].set_xlabel('S2B 2026-10-14: imaged pavement centre - OSM (m, along run normal)')
    ax[0].set_ylabel('S2C 2026-02-21 (or Umbra 2024-06-02 where S2C failed): same (m)')
    ax[0].set_title(f'{len(meas)} measured taxiway runs (>= {MIN_RUN:.0f} m), red = re-fitted (|c| >= {REFIT} m)', fontsize=9)
    ax[0].grid(alpha=0.3)
    w = [r['width_s2_m'] for r in runs if r['width_s2_m']]
    ax[1].hist(w, bins=np.arange(10, 70, 2), color='0.4')
    ax[1].set_xlabel('S2 pavement width, NDVI full width at half depth (m)')
    ax[1].set_title('taxiway pavement width on Sentinel-2 (both scenes, mean); blurred by 10 m pixels', fontsize=9)
    fig.suptitle('OSM taxiway centrelines vs Sentinel-2 L2A (Contains modified Copernicus Sentinel data 2026; '
                 'OSM (c) OpenStreetMap contributors)', fontsize=9)
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    plt.savefig(out_png, dpi=90)


if __name__ == '__main__':
    main(*sys.argv[1:4])
