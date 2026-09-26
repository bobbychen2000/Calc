#!/usr/bin/env python3
"""Derive airfield detail features from the SFO Museum geometry (data/sfo_airport.json) for the live 3D app.

Outputs data/sfo_details.json (+ debug PNGs in out/details/):
  apron          ramp pavement polygons: closing of terminal complex + taxiways + remote stands, limited to the
                 terminal surroundings (SFO Museum data has no apron features; this is an inferred outline)
  centerlines    taxiway centreline polylines: OSM aeroway=taxiway ways (ODbL), cut at runway edges, checked against the
                 painted yellow line on NAIP 2024 and moved onto it where NAIP shows a consistent offset > 0.5 m
                 (centerlineMeta: per line OSM id, ref, src 'osm' / 'osm+naip'; centerlineStats: residuals vs paint);
                 plus painted lines OSM lacks, traced on NAIP from two locator points (PAINT_TRACES, src 'naip')
  holds          runway holding positions: the painted 4-line marking measured on NAIP 2024 on every centreline
                 approach to a runway (position, bar angle, painted length; src 'naip'), else an OSM
                 aeroway=holding_position on the line (src 'osm'); then every OSM holding position (runway / ILS) with
                 no model hold within 15 m is used as a locator and its bar measured on the paint (locator 'osm',
                 kind 'runway' | 'ils'; review round 2); 'dist' = m from the runway centreline
  edges          taxiway edge polylines where the taxiway borders unpaved ground: SFO Museum outline, snapped to the painted
                 edge line on NAIP 2024 (edgeMeta / edgeStats; review round 3)
  masts          floodlight masts mapped in OSM (man_made=mast, tower:type=lighting; review round 3 - were inferred)
  roads          ramp service-road lines offset from the terminal face
World frame (matches js/geo.js): x = east, z = south (m), origin = ARP; projection/datum from tools/geo_frame.py
(exact GRS80 local tangent plane, NAD83(2011)). The ADS-B snapshot (WGS 84) is used only for the debug image (review round 3).
Also writes data/sfo_details.js (the same JSON as an ES module).
"""
import json, math, os, sys
from collections import Counter
import numpy as np, cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import geo_frame
D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
X0, Z0, X1, Z1, RES = -2800.0, -2450.0, 2050.0, 1900.0, 1.0
W, H = int((X1 - X0) / RES), int((Z1 - Z0) / RES)
FT = 0.3048
os.makedirs(os.path.join(ROOT, 'out', 'details'), exist_ok=True)

def px(pts): return np.array([[(x - X0) / RES, (z - Z0) / RES] for x, z in pts], np.float64)
def world(p): return [round(float(X0 + p[0] * RES), 2), round(float(Z0 + p[1] * RES), 2)]
def fillpolys(mask, polys, holes=True):
    for poly in polys:
        cv2.fillPoly(mask, [np.round(px(poly[0]) * 16).astype(np.int32)], 1, lineType=cv2.LINE_8, shift=4)
        if holes:
            for h in poly[1:]: cv2.fillPoly(mask, [np.round(px(h) * 16).astype(np.int32)], 0, lineType=cv2.LINE_8, shift=4)
    return mask
def newmask(): return np.zeros((H, W), np.uint8)

# ---------------------------------------------------------------- base masks
TW = newmask()
for t in D['taxiways']: fillpolys(TW, t['polys'], holes=False)
RW = newmask()
for r in D['runways']: fillpolys(RW, r['polys'], holes=False)
TC = newmask(); fillpolys(TC, [[p[0]] for p in D['terminalComplex']], holes=False)   # building incl. courtyards
BLD = newmask()
for s in D['structures']:
    if s['kind'] in ('garage', 'building', 'hangar', 'hotel', 'atc'): fillpolys(BLD, s['polys'], holes=False)
REM = newmask()
for g in D['gates']:
    if g.get('dup'): continue
    if g['level'] != 2 or g.get('variant'):
        cv2.circle(REM, (int((g['x'] - X0) / RES), int((g['z'] - Z0) / RES)), int(38 / RES), 1, -1)
print('masks', W, H, 'tw', TW.sum(), 'rw', RW.sum(), 'tc', TC.sum())

def dist_to(mask):  # distance (m) from every pixel to the mask
    return ndi.distance_transform_edt(mask == 0) * RES

# ---------------------------------------------------------------- apron (inferred ramp)
A0 = ((TC | TW | RW | REM) > 0).astype(np.uint8)
dA = dist_to(A0); R = 150.0
dil = (dA <= R).astype(np.uint8)
closed = (dist_to(1 - dil) > R).astype(np.uint8)          # morphological closing by a 150 m disc
dT = dist_to(TC)
apron = ((closed == 1) & (A0 == 0) & (dT <= 420)).astype(np.uint8)
apron |= ((dT <= 45) & (TC == 0) & (BLD == 0)).astype(np.uint8)                   # ramp directly around the building
apron &= (1 - BLD)
# keep only pieces touching the terminal ramp or remote stands (drop isolated infield slivers)
lab, n = ndi.label(apron | REM)
keep = set(np.unique(lab[(dT <= 60) | (REM > 0)])) - {0}
apron = np.isin(lab, list(keep)).astype(np.uint8) & (1 - TC)
apron = ndi.binary_opening(apron, iterations=3).astype(np.uint8)
PAVED = ((apron | TW | RW | REM) > 0).astype(np.uint8)
print('apron px', apron.sum())

def contours(mask, tol):
    cs, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    if hier is None: return polys
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1: continue  # outer contours only; holes attached below
        if cv2.contourArea(c) < 400: continue
        rings = [c]
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) > 200: rings.append(cs[j])
            j = hier[j][0]
        out = []
        for r in rings:
            a = cv2.approxPolyDP(r, tol / RES, True)[:, 0, :]
            out.append([world((p[0] + 0.5, p[1] + 0.5)) for p in a])
        polys.append(out)
    return polys
apron_polys = contours(apron, 1.2)

def extent(p, n, maxd=45):  # march across pavement (SFO Museum taxiway / inferred apron masks) from p along +-n
    res = []
    for sg in (1, -1):
        d = 0
        while d < maxd:
            q = p + n * sg * (d + 0.5); ix, iy = int((q[0] - X0) / RES), int((q[1] - Z0) / RES)
            if not (0 <= ix < W and 0 <= iy < H) or not (TW[iy, ix] or apron[iy, ix]): break
            d += 0.5
        res.append(d)
    return res

# ---------------------------------------------------------------- runways (surveyed ends; same as js/geo.js)
ENDS = {k: (v['lat'], v['lon']) for k, v in geo_frame.RWY_ENDS.items()}   # FAA NASR (NAD83) = js/geo.js RWY_ENDS
ll2w = geo_frame.ll_to_world                  # NAD83(2011) lat/lon -> world (x, z)
RWYS = []
for a, b in (('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')):
    pa, pb = np.array(ll2w(*ENDS[a])), np.array(ll2w(*ENDS[b])); L = np.linalg.norm(pb - pa); d = (pb - pa) / L
    RWYS.append({'a': a, 'b': b, 'pa': pa, 'pb': pb, 'dir': d, 'len': L})
def rw_frame(R, p):
    v = np.array(p) - R['pa']; return float(v @ R['dir']), float(-v[0] * R['dir'][1] + v[1] * R['dir'][0])  # along, cross (right of a->b positive)
RWY_HW = 100 * FT          # runway half width (200 ft runways, FAA NASR)

# ---------------------------------------------------------------- taxiway centrelines: OSM ways, checked on NAIP 2024
# Source: OSM aeroway=taxiway/taxilane ways (ODbL 1.0, (c) OpenStreetMap contributors; Overpass download parsed by
# tools/xcheck/parse_osm.py into refs/cache/osm/ksfo_osm_parsed.json), WGS 84 -> world via geo_frame.wgs84_to_world.
# The painted yellow centreline is measured on NAIP 2024 every 4 m (tools/imagery/paintline.py: yellow ridge across
# the line, +-3.5 m, averaged over 4 m along). Where at least 4 of 7 neighbouring samples agree (MAD < 0.4 m) on an
# offset > 0.5 m, the line is moved onto the paint; elsewhere the OSM geometry is kept. Ways tagged construction=yes
# (taxiway W rebuild, started 2026-06-22, not in the 2024 imagery) are skipped. Taxiway centrelines are not painted
# across runways: the parts within the runway pavement (200 ft wide) are cut out.
sys.path.insert(0, os.path.join(HERE, 'imagery'))
from paintline import Yellow, find_ladder, along_profile, refine_bar, BAR_DEPTH
YEL = Yellow()
OSM = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'osm', 'ksfo_osm_parsed.json')))

def densify(pl, step=2.0):
    P = np.asarray(pl, float); out = [P[0]]
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; L = np.linalg.norm(b - a); n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1): out.append(a + (b - a) * k / n)
    return np.array(out)
def arclen(P): return np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
def tangents(P):
    T = np.gradient(P, axis=0); l = np.hypot(T[:, 0], T[:, 1]); l[l == 0] = 1; return T / l[:, None]
def on_runway(p, margin=0.0):
    for R in RWYS:
        al, cr = rw_frame(R, p)
        if -3 < al < R['len'] + 3 and abs(cr) < RWY_HW + margin: return True
    return False

from shapely.geometry import Point as _SPt0, LineString as _SLS0
from shapely.prepared import prep as _prep0
from shapely.ops import unary_union as _suu0


def window_corr(ss, offs, min_shift=0.5, mad_max=0.4, clip=None, strict_big=True):
    """per-sample lateral correction from the measured paint offsets (review round 4). For each sample, the samples
    within +-3 (7-sample window) that found paint: at least 4 needed; a LOCAL LINE offset(s) is fitted (a curve whose
    offset changes along it - the paint curving away from the OSM way - has a large spread about its median but a small
    one about the line; round 4: centreline D 23718492 stayed 1.4-2.3 m off over 46 m, edge runs 1.5-2.8 m off). The
    correction is the line's value at the sample when the residual MAD < mad_max, the slope < 0.15 (8.5 deg) and
    |value| > min_shift. A correction above 1.5 m needs the full window with paint and MAD < 0.25 (review round 2: a
    zig-zag where the paint ends)."""
    masked = np.isinf(offs); offs = np.where(masked, np.nan, offs)
    corr = np.zeros(len(ss))
    for i in range(len(ss)):
        sl = slice(max(0, i - 3), i + 4); v = offs[sl]; sv = ss[sl]; ok = ~np.isnan(v); v, sv = v[ok], sv[ok]
        if len(v) < 4: continue
        m_ = float(np.median(v)); mad0 = float(np.median(np.abs(v - m_)))
        val, mad = m_, mad0
        if len(v) >= 5 and mad0 >= 0.1:
            b_, a_ = np.polyfit(sv - ss[i], v, 1); r_ = v - (a_ + b_ * (sv - ss[i])); mad1 = float(np.median(np.abs(r_)))
            if mad1 < mad0 and abs(b_) < 0.15: val, mad = float(a_), mad1
        if mad < mad_max and abs(val) > min_shift: corr[i] = val if clip is None else float(np.clip(val, -clip, clip))
        if strict_big and abs(corr[i]) > 1.5 and (len(v) < 7 or mad >= 0.25): corr[i] = 0.0
    if len(corr) >= 3:
        # smooth: running median over 3, then a 5-sample moving average (no step between corrected and kept parts)
        cm = np.array([np.median(corr[max(0, i - 1):i + 2]) for i in range(len(corr))])
        corr = np.array([cm[max(0, i - 2):i + 3].mean() for i in range(len(cm))])
        corr[np.abs(corr) < 0.05] = 0.0
    # masked samples (hold-bar zones) take the correction interpolated between their unmasked neighbours
    if masked.any() and (~masked).sum() >= 2:
        corr[masked] = np.interp(ss[masked], ss[~masked], corr[~masked])
    return corr


def measure(P, S, T, ss, half=3.5, avg=4.0, thr=0.6, skip=None):
    """paint offset per sample; `skip` (prepared shapely geometry): samples inside it are not measured (review round 4:
    the taxiway edge runs were pulled 2-3 m onto the runway holding-position ladders and their sign boxes)"""
    offs = np.full(len(ss), np.nan)
    for i, s_ in enumerate(ss):
        p = np.array([np.interp(s_, S, P[:, 0]), np.interp(s_, S, P[:, 1])]); t = np.array([np.interp(s_, S, T[:, 0]), np.interp(s_, S, T[:, 1])])
        t /= max(1e-9, np.hypot(*t))
        if skip is not None and skip.contains(_SPt0(float(p[0]), float(p[1]))): offs[i] = np.inf; continue   # masked (inf)
        r = YEL.cross_peak(p, t, half=half, avg=avg, step=0.1, min_contrast=10.0)
        if r and r[2] < thr * r[1]: offs[i] = r[0]
    return offs


def trace_paint(a, b, step=2.0):
    a, b = np.asarray(a, float), np.asarray(b, float); t = (b - a) / np.linalg.norm(b - a)
    p = a.copy(); pts = [p.copy()]; acc = []; n_ok = 0; n_all = 0; L0 = np.linalg.norm(b - a)
    for _ in range(int(1.4 * L0 / step)):
        q = p + t * step
        if np.linalg.norm(q - b) < step * 1.2: pts.append(b.copy()); break
        if not on_runway(q, 3.0):
            n_all += 1
            r = YEL.cross_peak(q, t, half=2.5, avg=3.0, step=0.1, min_contrast=10.0)
            if r and r[2] < 0.6 * r[1]:
                q = q + np.array([-t[1], t[0]]) * r[0]; acc.append(q.copy()); n_ok += 1
                if len(acc) >= 5:
                    A = np.array(acc[-5:]); d = A[-1] - A[0]
                    if np.linalg.norm(d) > 4: t = d / np.linalg.norm(d)
        # never wander: keep heading within 25 deg of the locator direction (the painted lines here are near straight)
        g = (b - q) / np.linalg.norm(b - q)
        if t @ g < math.cos(math.radians(25)): t = g
        p = q; pts.append(p.copy())
    return np.array(pts), n_ok, n_all

# Review round 4: OSM ways whose END leaves the painted route (centreline T, OSM 23718429: from x ~ -480 it cuts
# diagonally across the taxiway edge marking and the striped non-movement shoulder to the runway edge, while the paint
# runs straight on at z -387..-383 to the runway edge at x ~ -655, measured with Yellow.cross_peak every 15 m: -384.8
# (x -460), -387.8 (-520), -385.7 (-580), -383.7 (-625), -382.2 (-655)). The way is cut at `cut` (the vertex nearest to
# it; the part beyond is dropped) and continued by a trace on the paint (trace_paint, as PAINT_TRACES) to `to`.
PAINT_REROUTES = {
    23718429: {'cut': (-470.0, -384.9), 'to': (-664.0, -381.9), 'why': 'OSM way end cuts across the striped shoulder; the painted centreline runs straight to the runway (review round 4, crop cl16_wide)'},
}

centerlines, cl_meta = [], []
n_samp = n_peak = 0; corr_len = tot_len = 0.0; resid_before, resid_after = [], []
for w in OSM['taxiways']:
    if w['tags'].get('construction') == 'yes' or len(w['pts']) < 2: continue
    Pw = densify([geo_frame.wgs84_to_world(la, lo) for la, lo in w['pts']], 2.0)
    rr_note = None
    if w['id'] in PAINT_REROUTES:
        R_ = PAINT_REROUTES[w['id']]; k_ = int(np.argmin(np.hypot(*(Pw - np.array(R_['cut'])).T)))
        # keep the part on the far side of the cut from `to`
        head, tail = Pw[:k_ + 1], Pw[k_:]
        rev = np.hypot(*(head[0] - np.array(R_['to']))) <= np.hypot(*(tail[-1] - np.array(R_['to'])))
        keep_part, rest = (tail[::-1], head[::-1]) if rev else (head, tail)
        tr_, n_ok_, n_all_ = trace_paint(keep_part[-1], R_['to'])
        # the way beyond the runway it crosses is kept: from its first point on runway pavement on (that part is cut
        # out below; the runway-crossing lead-on is not a taxiway centreline) - it carries the far side's hold
        onr = [i for i, q in enumerate(rest) if on_runway(q)]
        far = rest[onr[0]:] if onr else rest[:0]
        assert on_runway(np.array(R_['to'])), 'reroute target must lie on the runway it joins'
        Pw = np.vstack([densify(np.vstack([keep_part, tr_[1:]]), 2.0)] + ([densify(far, 2.0)] if len(far) >= 2 else []))
        rr_note = 'rerouted: %s; traced part paint %d/%d samples' % (R_['why'], n_ok_, n_all_)
    keep = np.array([not on_runway(p) for p in Pw])
    runs, cur = [], []
    for p, k in zip(Pw, keep):
        if k: cur.append(p)
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    for run in runs:
        P = np.array(run)
        if len(P) < 3 or arclen(P)[-1] < 6: continue
        S = arclen(P); T = tangents(P)
        ss = np.arange(2.0, S[-1] - 1.0, 4.0) if S[-1] > 4 else np.array([S[-1] / 2])
        offs = measure(P, S, T, ss); n_samp += len(ss); n_peak += int((~np.isnan(offs)).sum())
        # (review round 2, centreline 24 / OSM 23718492: a correction above 1.5 m needs the full 7-sample window (24 m)
        # with paint and MAD < 0.25 m - inside window_corr)
        corr = window_corr(ss, offs, 0.5)
        good = ~np.isnan(offs)
        # review round 3 (centrelines OSM 1096199967 / 155702566: the paint lies ~2 m off along a curve, the offset
        # changes along it, so no 7-sample window has MAD < 0.25 m and nothing was corrected although the generator had
        # measured 2.06 / 1.74 m): when the windowed rule left a line with median |offset| > 1.0 m uncorrected, fit a
        # smooth offset (robust quadratic in arc length) and apply it if >= 60 % of the samples have paint and the fit
        # residual is <= 0.35 m rms; otherwise the line is flagged 'naip_unverified' in centerlineMeta.
        fit_note = None
        if good.sum() >= 6 and float(np.median(np.abs(offs[good]))) > 1.0 and float(np.max(np.abs(corr))) < 0.05:
            sg_, og_ = ss[good], offs[good]; keep_ = np.ones(len(sg_), bool)
            for _ in range(4):
                cf = np.polyfit(sg_[keep_], og_[keep_], min(2, int(keep_.sum()) - 1)); rr = og_ - np.polyval(cf, sg_)
                nk = np.abs(rr) < max(0.5, 2.5 * np.median(np.abs(rr[keep_])))
                if (nk == keep_).all(): break
                keep_ = nk
            rms_ = float(np.sqrt(np.mean(rr[keep_] ** 2)))
            if good.mean() >= 0.6 and keep_.sum() >= 0.6 * good.sum() and rms_ <= 0.35:
                corr = np.clip(np.polyval(cf, ss), -3.5, 3.5); fit_note = 'smooth fit (quadratic, %.2f m rms, %d/%d samples)' % (rms_, keep_.sum(), len(ss))
            else:
                fit_note = 'naip_unverified: paint %d/%d samples, fit %.2f m rms' % (good.sum(), len(ss), rms_)
        elif good.any() and float(np.median(np.abs(offs[good]))) > 1.0 and float(np.max(np.abs(corr))) < 0.05:
            fit_note = 'naip_unverified: paint in only %d/%d samples (weak paint), median offset %.2f m' % (good.sum(), len(ss), float(np.median(np.abs(offs[good]))))
        c_pts = np.interp(S, ss, corr) if len(ss) > 1 else np.full(len(S), corr[0])
        N = np.stack([-T[:, 1], T[:, 0]], 1)
        Q = P + N * c_pts[:, None]
        # review round 4: second pass on the corrected line (the +-3.5 m search is now centred on it): residual offsets
        # the first pass could not reach (a curve drifting > 3.5 m, windows split by a gap) are corrected the same way
        if np.any(np.abs(c_pts) > 0.01):
            S2 = arclen(Q); T2 = tangents(Q); o2 = measure(Q, S2, T2, ss); c2 = window_corr(ss, o2, 0.5)
            if np.any(np.abs(c2) > 0.01):
                c2p = np.interp(S2, ss, c2) if len(ss) > 1 else np.full(len(S2), c2[0])
                Q = Q + np.stack([-T2[:, 1], T2[:, 0]], 1) * c2p[:, None]; c_pts = c_pts + c2p; corr = corr + c2
        tot_len += S[-1]; corr_len += float(np.sum((np.abs(c_pts[1:]) > 0.01) * np.diff(S)))
        o3 = measure(Q, arclen(Q), tangents(Q), ss) if np.any(np.abs(c_pts) > 0.01) else offs      # review round 4: residual on the final line
        g3 = ~np.isnan(o3)
        resid_before += list(np.abs(offs[good])); resid_after += list(np.abs(o3[g3]))
        a = cv2.approxPolyDP(Q.astype(np.float32).reshape(-1, 1, 2), 0.12, False)[:, 0, :]
        centerlines.append([[round(float(x), 2), round(float(z), 2)] for x, z in a])
        # review round 4: a line with paint in < 25 % of its samples (or naip_unverified) is kept for routing but not
        # drawn: NAIP shows no (or no consistent) centreline paint there (round 4: ~2 km of yellow on bare pavement)
        drawn = not ((len(ss) and good.sum() < 0.25 * len(ss)) or (fit_note and fit_note.startswith('naip_unverified')))
        cl_meta.append({'osm_id': w['id'], 'ref': w['tags'].get('ref'), 'src': ('osm+naip' if np.any(np.abs(c_pts) > 0.01) else 'osm') + ('+naip_trace' if rr_note else ''),
                        'drawn': bool(drawn), **({'reroute': rr_note} if rr_note else {}),
                        'naip_samples': int(len(ss)), 'naip_peaks': int(good.sum()),
                        'naip_med_abs_off': round(float(np.median(np.abs(offs[good]))), 2) if good.any() else None,
                        'naip_resid_after': round(float(np.median(np.abs(o3[g3]))), 2) if g3.any() else None,
                        'naip_gt1.5_after': int((np.abs(o3[g3]) > 1.5).sum()),
                        'max_corr': round(float(np.max(np.abs(c_pts))), 2), **({'naip_fit': fit_note} if fit_note else {}),
                        **({'naip_unverified': True} if fit_note and fit_note.startswith('naip_unverified') else {})})
# ---- centrelines painted on NAIP 2024 that OSM does not map (review round 2). Each entry: two locator points (world
# x, z) near the ends of the painted line, read on NAIP; the line itself is TRACED on the paint (Yellow.cross_peak every
# 2 m, +-2.5 m search, heading from the last 10 m of accepted peaks) and is not the straight line between the locators.
# Across runway pavement (centrelines are not painted there) the trace coasts straight; the runway parts are cut out
# like the OSM ways. Overpass (database 2026-09-24T09:07Z) has no aeroway=taxiway way along these lines (checked:
# no OSM taxiway within 20 m of the traced middle part); name unknown -> ref None, src 'naip'.
PAINT_TRACES = [
    # east-west crossing of 1L/19R (x ~ -162) and 1R/19L (x ~ 91) north of the terminal: painted centreline with hold
    # ladders on both sides of each runway; west end joins OSM taxiway W (155476504) at about (-291.7, 227.5), east end
    # joins the unnamed OSM ways 155570033/155570035 at about (215.1, 291.9) (review round 2 finding, crop h68w.jpg)
    {'from': (-291.7, 227.5), 'to': (215.1, 291.9), 'why': 'painted E-W taxiway crossing 1L/19R and 1R/19L, no OSM way'},
]

for tr in PAINT_TRACES:
    P0, n_ok, n_all = trace_paint(tr['from'], tr['to'])
    P0 = densify(P0, 2.0)
    keep = np.array([not on_runway(p) for p in P0]); runs, cur = [], []
    for p, k in zip(P0, keep):
        if k: cur.append(p)
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    for run in runs:
        P = np.array(run)
        if len(P) < 3: continue
        # light smoothing of the traced vertices (3-point mean, ends fixed), then simplification
        Ps = P.copy(); Ps[1:-1] = (P[:-2] + P[1:-1] + P[2:]) / 3
        a = cv2.approxPolyDP(Ps.astype(np.float32).reshape(-1, 1, 2), 0.12, False)[:, 0, :]
        centerlines.append([[round(float(x), 2), round(float(z), 2)] for x, z in a])
        # name: the SFO Museum taxiway polygon (CDLA-Permissive-1.0) containing the run's middle, if any
        mid_ = P[len(P) // 2]; sfm = None
        for t in D['taxiways']:
            for poly in t['polys']:
                if cv2.pointPolygonTest(px(poly[0]).astype(np.float32).reshape(-1, 1, 2), ((mid_[0] - X0) / RES, (mid_[1] - Z0) / RES), False) >= 0:
                    sfm = t['name'].replace('Taxiway ', ''); break
            if sfm: break
        cl_meta.append({'osm_id': None, 'ref': sfm, 'ref_src': 'SFO Museum taxiway polygon' if sfm else None, 'src': 'naip', 'drawn': True, 'note': tr['why'] + ' (traced on NAIP 2024; OSM gap)',
                        'naip_samples': n_all, 'naip_peaks': n_ok, 'naip_med_abs_off': None, 'max_corr': None})
    print('traced', tr['why'], 'peaks %d / %d samples' % (n_ok, n_all))
rb, ra = np.array(resid_before), np.array(resid_after)
CL_STATS = {'lines': len(centerlines), 'km': round(tot_len / 1000, 2), 'naip_samples': n_samp, 'naip_peaks': n_peak,
            'osm_vs_paint': {'median': round(float(np.median(rb)), 2), 'gt1.5': round(float((rb > 1.5).mean()), 3), 'gt3': round(float((rb > 3).mean()), 3)},
            'final_vs_paint': {'median': round(float(np.median(ra)), 2), 'gt1.5': round(float((ra > 1.5).mean()), 3), 'gt3': round(float((ra > 3).mean()), 3)},
            'corrected_km': round(corr_len / 1000, 2)}
print('centerlines', CL_STATS)

# ---------------------------------------------------------------- holding positions (painted ladders measured on NAIP)
# Every centreline run that ends at a runway edge is searched on NAIP 2024 for the runway holding-position marking
# (4 yellow lines 12 in wide, 12 in apart = a 7 ft deep band) between 62 and 110 m from the runway centreline. The
# band position is measured at lateral offsets across the taxiway to get the painted bar's angle, and followed
# sideways to get its painted length. Where NAIP shows no clear ladder, an OSM aeroway=holding_position feature
# (runway type) on the line is used ('osm'); otherwise the hold is dropped. The FAA standard 280 ft (85.3 m) is
# NOT assumed: SFO's painted holds lie mostly at ~75.5 m, some at ~85 m (measured, see 'holdStats').
OSM_HOLDS = []
for h in OSM['holding_positions']:
    if h['tags'].get('holding_position:type', 'runway') != 'runway': continue
    OSM_HOLDS.append({'id': h['id'], 'w': np.array([geo_frame.wgs84_to_world(la, lo) for la, lo in h['pts']])})
def osm_hold_near(P, S):
    """(arc length, osm id) of an OSM holding position on the approach polyline (node within 4 m, or a bar way
    crossing it)"""
    best = None
    for h in OSM_HOLDS:
        W_ = h['w']
        if len(W_) == 1:
            d = np.hypot(*(P - W_[0]).T); i = int(np.argmin(d))
            if d[i] < 4 and (best is None or d[i] < best[2]): best = (float(S[i]), h['id'], float(d[i]))
        else:
            from shapely.geometry import LineString as LS
            a, b = LS(W_), LS(P)
            if a.intersects(b):
                x = a.intersection(b); x = x if x.geom_type == 'Point' else x.centroid
                s_ = b.project(x)
                if best is None: best = (float(s_), h['id'], 0.0)
    return best

def paved_mask_at(q):
    ix, iy = int((q[0] - X0) / RES), int((q[1] - Z0) / RES)
    return 0 <= ix < W and 0 <= iy < H and bool(TW[iy, ix] or apron[iy, ix] or RW[iy, ix])

def band_contrast(q, bar, un, depth=BAR_DEPTH):
    """contrast of the yellow hold band (depth across the bar) at point q on the bar: box-filtered yellowness profile
    along the bar normal (+-2.5 m), peak within +-0.6 m minus the profile ends"""
    from paintline import _box
    sgv = np.arange(-2.5, 2.51, 0.1)
    v = along_profile(YEL, q[None] + un[None] * sgv[:, None], np.repeat(bar[None], len(sgv), 0), np.array([-0.25, 0.0, 0.25]))
    f = _box(v, int(round(depth / 0.1))); m_ = len(f) // 2
    return float(f[m_ - 6:m_ + 7].max() - np.median(np.r_[f[:5], f[-5:]]))

def painted_extent(pc, bar, un, depth=BAR_DEPTH):
    """painted length of a hold bar either side of pc (m): follow the band in 0.5 m steps until it stays below 45 % of
    the bar's median contrast (|d| < 8 m) for 3.5 m (review round 2: the old 30 %-of-the-ladder-scan threshold ran
    1.7-9.5 m past the paint onto shoulders / green paint at holds 23, 24, 26, 41)"""
    ref = np.median([band_contrast(pc + bar * d, bar, un, depth) for d in np.r_[np.arange(-8, -1.9, 1.0), np.arange(2, 8.1, 1.0)]])
    thr = 0.45 * max(ref, 8.0); ends = []
    for sg_ in (1, -1):
        d_, miss, last = 0.0, 0, 0.0
        while d_ < 45:
            d_ += 0.5
            if band_contrast(pc + bar * sg_ * d_, bar, un, depth) > thr: last, miss = d_, 0
            else:
                miss += 1
                if miss >= 7: break
        ends.append(last)
    return ends

holds = []; hold_log = []
for ci, cl in enumerate(centerlines):
    Pc = densify(cl, 0.5)
    for end in (0, 1):
        P = Pc if end == 0 else Pc[::-1]
        for R in RWYS:
            al0, cr0 = rw_frame(R, P[0])
            if not (-60 < al0 < R['len'] + 60 and abs(cr0) < RWY_HW + 6): continue
            # the approach: from the runway edge outwards while the distance from the centreline grows to 115 m
            crs = np.array([abs(rw_frame(R, p)[1]) for p in P])
            k = 1
            while k < len(P) and crs[k] < 118 and crs[k] >= crs[k - 1] - 0.3: k += 1
            A = P[:k]; C = crs[:k]
            if len(A) < 20 or C[-1] < 60: continue
            S = arclen(A); T = tangents(A)
            if abs(np.mean(T[:, 0] * R['dir'][0] + T[:, 1] * R['dir'][1])) > 0.87: continue   # running along the runway
            s_lo = float(np.interp(62.0, C, S)); s_hi = float(np.interp(min(110.0, C[-1]), C, S))
            L = find_ladder(YEL, A, T, S, s_lo, s_hi)
            src = None
            if L and L['contrast'] >= 9.0 and L['second'] < 0.75 * L['contrast']:
                s_star = L['s']; src = 'naip'
            else:
                oh = osm_hold_near(A, S)
                if oh and s_lo - 5 < oh[0] < s_hi + 5: s_star = oh[0]; src = 'osm'
            if src is None:
                hold_log.append({'line': ci, 'rwy': R['a'] + '/' + R['b'], 'p': [round(float(v), 1) for v in A[0]], 'status': 'no ladder, no OSM hold',
                                 'contrast': round(L['contrast'], 1) if L else None})
                continue
            pc = np.array([np.interp(s_star, S, A[:, 0]), np.interp(s_star, S, A[:, 1])])
            tc = np.array([np.interp(s_star, S, T[:, 0]), np.interp(s_star, S, T[:, 1])]); tc /= np.linalg.norm(tc)
            nc = np.array([-tc[1], tc[0]])
            # u = unit vector from the hold toward the runway (along the approach towards its start)
            u = -tc
            slope, ext, cen_c = 0.0, None, None
            if src == 'naip':
                # the bar angle is the shear angle of the strongest band (find_ladder scans -60..60 deg, then 1 deg steps);
                # a per-offset line fit was tried and was less robust on worn / partly covered ladders
                slope = math.tan(math.radians(L['skew_deg']))
            bar = nc + tc * slope; bar /= np.linalg.norm(bar)
            if src == 'naip':
                # Bar angle: two hypotheses, refined +-8 deg and compared by band contrast over +-8 m: perpendicular to
                # the taxiway (with the scan's skew) or parallel to the runway. Observed on NAIP: at oblique entries SFO
                # paints the ladder parallel to the runway (e.g. F and C at 10R/28L, M at 1L/19R, G at 1R/19L).
                # A third hypothesis is an OSM aeroway=holding_position way (a traced bar) passing within 8 m: the band
                # is searched around the OSM line (OSM as locator, NAIP decides), weighted 1.3. The band is searched
                # +-2 m across the bar around each hypothesis' anchor.
                cands = [(refine_bar(YEL, pc, bar), 1.0, pc), (refine_bar(YEL, pc, R['dir']), 1.0, pc)]
                from shapely.geometry import LineString as LS, Point as PT
                for oh in OSM_HOLDS:
                    if len(oh['w']) >= 2 and min(np.hypot(*(oh['w'] - pc).T)) < 40:
                        ls_ = LS(oh['w'])
                        if ls_.distance(PT(pc)) < 8:
                            q0 = np.array(ls_.interpolate(ls_.project(PT(pc))).coords[0])
                            dv = oh['w'][-1] - oh['w'][0]; cands.append((refine_bar(YEL, q0, dv), 1.3, q0))
                (q_, b_, c_), _, anchor = max(cands, key=lambda r_: r_[0][2] * r_[1])
                M_ = np.array([[b_[0], -tc[0]], [b_[1], -tc[1]]])
                pc1 = pc
                if abs(np.linalg.det(M_)) > 0.2:
                    ab = np.linalg.solve(M_, pc - q_); pc1 = pc + tc * ab[1]     # onto the centreline
                if os.environ.get('DEBUG_HOLD'):
                    print('refine', [round(float(v), 1) for v in pc], [round(float(c[0][2]), 1) for c in cands], round(abs(rw_frame(R, pc1)[1]), 1))
                # accept only if the refined bar passes within 2.5 m of its anchor, meets the centreline within 8 m and
                # the hold stays in the search window
                if abs(float((anchor - q_) @ np.array([-b_[1], b_[0]]))) < 2.5 and np.linalg.norm(pc1 - pc) < 8 and 60 < abs(rw_frame(R, pc1)[1]) < 112:
                    pc = pc1; bar = b_
                slope = float(np.dot(bar, tc) / max(1e-6, abs(np.dot(bar, nc)))) * (1 if np.dot(bar, nc) >= 0 else -1)
            un = np.array([bar[1], -bar[0]]);  un = un if un @ u > 0 else -un        # bar normal toward the runway
            # painted length: follow the band sideways until it fades (NAIP), else the paved width
            if src == 'naip': ends = painted_extent(pc, bar, un)
            else:
                ends = []
                for sg_ in (1, -1):
                    d_, last = 0.0, 0.0
                    while d_ < 45:
                        d_ += 0.5
                        if paved_mask_at(pc + bar * sg_ * d_): last = d_
                        else: break
                    ends.append(last)
            e1, e2 = ends
            if e1 + e2 < 8: e1, e2 = extent(pc, bar)[0], extent(pc, bar)[1]
            a_pt, b_pt = pc + bar * e1, pc - bar * e2
            mid = (a_pt + b_pt) / 2
            alq, crq = rw_frame(R, mid)
            left = np.array([u[1], -u[0]])
            s_left = R['dir'] @ left; name_left, name_right = (R['b'], R['a']) if s_left > 0 else (R['a'], R['b'])
            tname = cl_meta[ci]['ref']
            if not tname:
                for t in D['taxiways']:
                    for poly in t['polys']:
                        if cv2.pointPolygonTest(px(poly[0]).astype(np.float32).reshape(-1, 1, 2), ((pc[0] - X0) / RES, (pc[1] - Z0) / RES), False) >= 0:
                            tname = t['name'].replace('Taxiway ', ''); break
                    if tname: break
            holds.append({'p': [round(float(pc[0]), 2), round(float(pc[1]), 2)], 'a': [round(float(a_pt[0]), 2), round(float(a_pt[1]), 2)],
                          'b': [round(float(b_pt[0]), 2), round(float(b_pt[1]), 2)], 'dir': [round(float(un[0]), 4), round(float(un[1]), 4)],
                          'rwy': R['a'] + '/' + R['b'], 'text': f'{name_left}-{name_right}', 'twy': tname, 'w': round(float(e1 + e2), 1),
                          'dist': round(abs(crq), 2), 'src': src, 'contrast': round(L['contrast'], 1) if L else None,
                          'skew_deg': round(math.degrees(math.atan(slope)), 1), 'ladder_skew_scan': L['skew_deg'] if L else None})
# de-duplicate (two centreline pieces can reach the same hold): keep the strongest detection
holds.sort(key=lambda h: (h['src'] != 'naip', -(h['contrast'] or 0)))
uniq = []
for h in holds:
    if all(math.dist(h['p'], u_['p']) > 18 for u_ in uniq): uniq.append(h)
holds = sorted(uniq, key=lambda h: (h['rwy'], h['p'][0], h['p'][1]))
for h in holds: h.setdefault('kind', 'runway')

# ---- holds located by OSM (review round 2). The centreline search above only finds ladders 62-110 m out on runs that
# end at a runway; ladders further out (up to ~125 m), on taxiways crossing a runway, and ILS critical-area holds were
# missed although painted. Every OSM aeroway=holding_position (node or traced way; runway, ILS or untyped) with no model
# hold within 15 m is used as a LOCATOR only: the bar is measured on NAIP 2024 (refine_bar, +-4 m around the locator,
# direction hypotheses: across the nearest model centreline, parallel to the runway, along the OSM way) and kept only
# when the band is clearly painted (contrast >= HOLD_MIN_C and at least 8 m of painted length); position, angle and length
# are the paint's. OSM holding_position:type=ILS -> kind 'ils' (FAA AC 150/5340-1M: two 12 in lines 2 ft apart joined by
# 12 in bars every 10 ft = 4 ft deep; sign "ILS"); else 'runway'. Rejected locators are logged in holdsDropped.
HOLD_MIN_C = 20.0
ILS_DEPTH = 4 * FT
from shapely.geometry import LineString as _LS, Point as _PT
cl_lines = [_LS(c) for c in centerlines]
groups = []
for h in OSM['holding_positions']:
    W_ = np.array([geo_frame.wgs84_to_world(la, lo) for la, lo in h['pts']])
    c_ = W_.mean(axis=0); typ = h['tags'].get('holding_position:type') or 'runway'
    if typ not in ('runway', 'ILS'): continue
    g = next((g for g in groups if min(np.linalg.norm(c_ - q) for q in g['c']) < 10), None)
    if g is None: g = {'c': [], 'ways': [], 'ids': [], 'ils': False}; groups.append(g)
    g['c'].append(c_); g['ids'].append(h['id']); g['ils'] |= typ == 'ILS'
    if len(W_) >= 2: g['ways'].append(W_)
def add_hold_from_bar(g, R, q_, bar, c_, un, depth, ci_, multi=False):
    """a hold from a measured bar; with two bars at one locator, the one not crossing the centreline is 'secondary'
    (painted, drawn, but without its own sign pair: signs=False)"""
    loc = np.mean(g['c'], axis=0)
    if c_ < HOLD_MIN_C:
        hold_log.append({'osm': g['ids'], 'p': [round(float(v), 1) for v in loc], 'rwy': R['a'] + '/' + R['b'], 'status': 'OSM hold, no painted bar on NAIP', 'contrast': round(c_, 1)}); return
    e1, e2 = painted_extent(q_, bar, un, depth)
    if e1 + e2 < 8:
        hold_log.append({'osm': g['ids'], 'p': [round(float(v), 1) for v in loc], 'rwy': R['a'] + '/' + R['b'], 'status': 'OSM hold, painted bar shorter than 8 m', 'contrast': round(c_, 1)}); return
    a_pt, b_pt = q_ + bar * e1, q_ - bar * e2; mid = (a_pt + b_pt) / 2
    pc = mid; tname = None; crossed = False
    if ci_ is not None:
        x_ = _LS([a_pt, b_pt]).intersection(cl_lines[ci_])
        if not x_.is_empty:
            x_ = x_ if x_.geom_type == 'Point' else x_.centroid if x_.geom_type != 'MultiPoint' else min(x_.geoms, key=lambda q: q.distance(_PT(mid)))
            pc = np.array(x_.coords[0]); tname = cl_meta[ci_]['ref']; crossed = True
    if not tname:
        for t in D['taxiways']:
            for poly in t['polys']:
                if cv2.pointPolygonTest(px(poly[0]).astype(np.float32).reshape(-1, 1, 2), ((pc[0] - X0) / RES, (pc[1] - Z0) / RES), False) >= 0:
                    tname = t['name'].replace('Taxiway ', ''); break
            if tname: break
    left = np.array([un[1], -un[0]]); s_left = R['dir'] @ left
    name_left, name_right = (R['b'], R['a']) if s_left > 0 else (R['a'], R['b'])
    tn = un @ (R['dir']); skew = math.degrees(math.asin(max(-1, min(1, float(tn)))))
    holds.append({'p': [round(float(pc[0]), 2), round(float(pc[1]), 2)], 'a': [round(float(a_pt[0]), 2), round(float(a_pt[1]), 2)],
                  'b': [round(float(b_pt[0]), 2), round(float(b_pt[1]), 2)], 'dir': [round(float(un[0]), 4), round(float(un[1]), 4)],
                  'rwy': R['a'] + '/' + R['b'], 'text': 'ILS' if g['ils'] else f'{name_left}-{name_right}', 'twy': tname,
                  'w': round(float(e1 + e2), 1), 'dist': round(abs(rw_frame(R, mid)[1]), 2), 'src': 'naip', 'locator': 'osm',
                  'osm_ids': g['ids'], 'kind': 'ils' if g['ils'] else 'runway', 'contrast': round(c_, 1),
                  'bar_vs_runway_deg': round(skew, 1)})
    if multi and not crossed: holds[-1]['secondary'] = True; holds[-1]['signs'] = False
    print('hold from OSM locator', g['ids'][0], R['a'], holds[-1]['p'], holds[-1]['w'], holds[-1]['dist'], holds[-1]['kind'], round(c_, 1))

n_loc = 0
for g in groups:
    loc = np.mean(g['c'], axis=0)
    if any(math.dist(loc, h['p']) < 15 for h in holds): continue
    n_loc += 1
    Rbest = None
    for R in RWYS:
        al, cr = rw_frame(R, loc)
        if -300 < al < R['len'] + 300 and 50 < abs(cr) < 175 and (Rbest is None or abs(cr) < Rbest[1]): Rbest = (R, abs(cr))
    if Rbest is None:
        hold_log.append({'osm': g['ids'], 'p': [round(float(v), 1) for v in loc], 'status': 'OSM hold not 50-175 m from a runway'}); continue
    R = Rbest[0]
    # nearest model centreline and its tangent at the locator
    ci_, dmin = None, 1e9
    for i_, ls_ in enumerate(cl_lines):
        d_ = ls_.distance(_PT(loc))
        if d_ < dmin: ci_, dmin = i_, d_
    # hypotheses: (anchor, bar direction, weight); every segment >= 5 m of a traced OSM hold way is its own hypothesis
    # (some ways trace two ladders, e.g. the straight + angled ladders of T at 10L/28R)
    hyps = [(loc, R['dir'], 1.0)]
    if dmin < 12:
        ls_ = cl_lines[ci_]; s0 = ls_.project(_PT(loc))
        q1 = np.array(ls_.interpolate(max(0, s0 - 3)).coords[0]); q2 = np.array(ls_.interpolate(min(ls_.length, s0 + 3)).coords[0])
        tt = (q2 - q1) / max(1e-6, np.linalg.norm(q2 - q1)); hyps.append((loc, np.array([-tt[1], tt[0]]), 1.0))
    for W_ in g['ways']:
        for k_ in range(len(W_) - 1):
            if np.linalg.norm(W_[k_ + 1] - W_[k_]) >= 5: hyps.append(((W_[k_] + W_[k_ + 1]) / 2, W_[k_ + 1] - W_[k_], 1.15))
    depth = ILS_DEPTH if g['ils'] else BAR_DEPTH
    res_ = []
    for anc, b0, wgt in hyps:
        r_ = refine_bar(YEL, anc, b0, sw=4.0); res_.append((r_, wgt))
    res_.sort(key=lambda r: -r[0][2] * r[1])
    # the primary bar, plus a second painted bar at a clearly different angle (>= 20 deg) from another way segment
    picks = [res_[0][0]]
    for r_, wgt in res_[1:]:
        ang_ = math.degrees(math.acos(min(1.0, abs(float(r_[1] @ picks[0][1])))))
        if wgt > 1.0 and ang_ >= 20 and r_[2] >= HOLD_MIN_C: picks.append(r_); break
    for kk, (q_, bar, c_) in enumerate(picks):
        un = np.array([bar[1], -bar[0]])
        foot = R['pa'] + R['dir'] * rw_frame(R, q_)[0]
        un = un if un @ (foot - q_) > 0 else -un
        add_hold_from_bar(g, R, q_, bar, c_, un, depth, ci_ if dmin < 12 else None, multi=len(picks) > 1)
holds = sorted(holds, key=lambda h: (h['rwy'], h['p'][0], h['p'][1]))
dists = np.array([h['dist'] for h in holds if h['src'] == 'naip'])
HOLD_STATS = {'n': len(holds), 'src': dict(Counter(h['src'] for h in holds)), 'kind': dict(Counter(h['kind'] for h in holds)),
              'osm_located': sum(1 for h in holds if h.get('locator') == 'osm'), 'dropped': len(hold_log),
              'dist_naip_median': round(float(np.median(dists)), 2) if len(dists) else None,
              'dist_hist_m': dict(Counter(int(round(v)) for v in dists))}
print('holds', HOLD_STATS)

# ---------------------------------------------------------------- taxiway edges bordering unpaved ground
edges = []
for t in D['taxiways']:
    for poly in t['polys']:
        for ring in poly:
            run = []
            n = len(ring)
            for i in range(n):
                a, b = np.array(ring[i]), np.array(ring[(i + 1) % n]); L = np.linalg.norm(b - a)
                if L < 0.5: continue
                d = (b - a) / L; nrm = np.array([-d[1], d[0]])
                steps = max(1, int(L / 2.0))
                for k in range(steps + 1):
                    p = a + d * L * k / steps
                    def paved_at(q):
                        ix, iy = int((q[0] - X0) / RES), int((q[1] - Z0) / RES)
                        return 0 <= ix < W and 0 <= iy < H and PAVED[iy, ix] > 0
                    s1, s2 = paved_at(p + nrm * 2.5), paved_at(p - nrm * 2.5)
                    if s1 != s2:
                        inward = nrm if s1 else -nrm
                        run.append([round(float((p + inward * 0.9)[0]), 2), round(float((p + inward * 0.9)[1]), 2)])
                    else:
                        if len(run) > 3: edges.append(run)
                        run = []
            if len(run) > 3: edges.append(run)
# simplify
def simplify(pl, tol):
    c = np.array(pl, np.float32).reshape(-1, 1, 2); a = cv2.approxPolyDP(c, tol, False)[:, 0, :]; return [[round(float(p[0]), 2), round(float(p[1]), 2)] for p in a]
edges = [simplify(e, 0.35) for e in edges if sum(math.dist(e[i], e[i + 1]) for i in range(len(e) - 1)) > 15]
print('edge runs (SFO Museum outline)', len(edges))
# Review round 3: the runs above are the SFO Museum taxiway outline moved 0.9 m inward (inferred) and sat 1-2 m inside
# the painted double yellow edge line (review: median 0.95 m, 20.6 km of 83 km over 1.5 m). Each run is now snapped to
# the paint on NAIP 2024 like the centrelines: the yellow ridge across the line (+-3.5 m, averaged over 3 m along)
# every 2 m; where >= 4 of 7 neighbouring samples agree (MAD < 0.4 m) the run moves onto their median (any size up to
# 3.5 m), smoothed; elsewhere the outline position is kept. edgeMeta per run: 'naip' (snapped), 'outline' (no
# consistent paint: position inferred), with the paint fraction and residuals. Runs over 30 m with paint in < 15 % of
# the samples are dropped (NAIP shows no edge line there; review: lines drawn on grey pavement).
edge_meta, edges_out = [], []
E_before, E_after = [], []
# review round 4: no paint measurement within 7 m of a runway holding-position bar (the 4-line ladder and the sign boxes
# next to it pulled the edge runs 143 / 242 / 302 ... 2-3 m inwards over 10-20 m); the run keeps its neighbours' offset
HOLD_ZONE = _prep0(_suu0([_SLS0([tuple(h['a']), tuple(h['b'])]).buffer(7.0) for h in holds]))
for e in edges:
    P = densify(e, 1.0); S = arclen(P); T = tangents(P)
    if S[-1] < 4: continue
    ss = np.arange(1.0, S[-1] - 0.5, 2.0) if S[-1] > 3 else np.array([S[-1] / 2])
    offs = measure(P, S, T, ss, avg=3.0, thr=0.7, skip=HOLD_ZONE)
    good = np.isfinite(offs); frac = float(good.sum() / max(1, (~np.isinf(offs)).sum()))
    if S[-1] > 30 and frac < 0.15:
        edge_meta.append(None); continue          # marker for the stats below (dropped run)
    corr = window_corr(ss, offs, 0.2, clip=3.5, strict_big=False)
    c_pts = np.interp(S, ss, corr) if len(ss) > 1 else np.full(len(S), corr[0])
    Q = P + np.stack([-T[:, 1], T[:, 0]], 1) * c_pts[:, None]
    # review round 4: further passes on the snapped run (17 edges had 6-40 m stretches 1.5-2.8 m off the paint: the
    # SFO Museum outline underneath is wavy on a ~10 m scale that the smoothed first pass could not follow). Pass 2 as
    # pass 1 on the corrected line; passes 3-4 looser: a sample more than 0.8 m off moves by the median of its 5-sample
    # window when >= 3 of those found paint on the same side (no MAD gate; the +-3.5 m search is centred on the line
    # by now, hold-bar zones stay masked)
    for pass_ in (2, 3, 4):
        S2 = arclen(Q); T2 = tangents(Q); o2 = measure(Q, S2, T2, ss, avg=3.0, thr=0.7, skip=HOLD_ZONE)
        if pass_ == 2: c2 = window_corr(ss, o2, 0.2, clip=3.5, strict_big=False)
        else:
            c2 = np.zeros(len(ss)); of = np.where(np.isinf(o2), np.nan, o2)
            for i in range(len(ss)):
                v = of[max(0, i - 2):i + 3]; v = v[~np.isnan(v)]
                if len(v) >= 3 and not np.isnan(of[i]) and abs(of[i]) > 0.8 and (np.sign(v) == np.sign(of[i])).sum() >= 3: c2[i] = float(np.median(v))
            if len(c2) >= 3: c2 = np.array([c2[max(0, i - 1):i + 2].mean() for i in range(len(c2))])
        if not np.any(np.abs(c2) > 0.01): continue
        c2p = np.interp(S2, ss, c2) if len(ss) > 1 else np.full(len(S2), c2[0])
        Q = Q + np.stack([-T2[:, 1], T2[:, 0]], 1) * c2p[:, None]; c_pts = c_pts + c2p; corr = corr + c2
    # across a masked hold-bar zone the run is drawn straight between the snapped points either side of it (the outline
    # underneath bulges round the hold-sign pads; interpolating only the correction kept that bulge - edge 143)
    msk = np.isinf(offs)
    if msk.any():
        S_ = arclen(Q); i = 0
        while i < len(ss):
            if not msk[i]: i += 1; continue
            j = i
            while j + 1 < len(ss) and msk[j + 1]: j += 1
            if i > 0 and j < len(ss) - 1:
                sa, sb = ss[i - 1], ss[j + 1]
                qa = np.array([np.interp(sa, S_, Q[:, 0]), np.interp(sa, S_, Q[:, 1])]); qb = np.array([np.interp(sb, S_, Q[:, 0]), np.interp(sb, S_, Q[:, 1])])
                sel = (S_ > sa) & (S_ < sb)
                Q[sel] = qa + np.outer((S_[sel] - sa) / (sb - sa), qb - qa)
            i = j + 1
    o3 = measure(Q, arclen(Q), tangents(Q), ss, avg=3.0, thr=0.7, skip=HOLD_ZONE) if np.any(np.abs(c_pts) > 0.01) else offs     # review round 4: residual on the final line
    # review round 4: a run whose paint support is weak (< 30 % of its samples) AND whose final line still sits > 1 m off
    # the paint found (median) is dropped: the paint does not support it (edges 145 / 146 / 246 / 299 / 341 ...)
    f3 = o3[np.isfinite(o3)]
    if len(f3) < 0.3 * max(1, (~np.isinf(o3)).sum()) and (len(f3) == 0 or float(np.median(np.abs(f3))) > 1.0):
        edge_meta.append(None); continue
    E_before += list(np.abs(offs[good])); E_after += list(np.abs(o3[np.isfinite(o3)]))
    edges_out.append(simplify(Q.tolist(), 0.2))
    edge_meta.append({'src': 'naip' if np.any(np.abs(c_pts) > 0.01) else 'outline', 'len': round(float(S[-1]), 1), 'paint_frac': round(frac, 2),
                      'naip_med_abs_off_before': round(float(np.median(np.abs(offs[good]))), 2) if good.any() else None,
                      'naip_med_abs_off_after': round(float(np.median(np.abs(o3[np.isfinite(o3)]))), 2) if np.isfinite(o3).any() else None})
EDGE_STATS = {'runs_outline': len(edges), 'runs_kept': len(edges_out), 'dropped_no_paint': sum(1 for m in edge_meta if m is None),   # (incl. round 4: weak paint and > 1 m off)
              'km_kept': round(sum(m['len'] for m in edge_meta if m) / 1000, 2),
              'snapped_runs': sum(1 for m in edge_meta if m and m['src'] == 'naip'),
              'paint_offset_before': {'median': round(float(np.median(E_before)), 2), 'gt1.5': round(float((np.array(E_before) > 1.5).mean()), 3)} if E_before else None,
              'paint_offset_after': {'median': round(float(np.median(E_after)), 2), 'gt1.5': round(float((np.array(E_after) > 1.5).mean()), 3)} if E_after else None}
edges = edges_out; edge_meta = [m for m in edge_meta if m]
print('edges', EDGE_STATS)

# ---------------------------------------------------------------- floodlight masts: OSM man_made=mast + tower:type=lighting
# Review round 3: the earlier masts were inferred (every ~120 m along the inferred ramp outline) and several stood in
# taxiway pavement or on landside roads. Now only mapped masts: OSM nodes man_made=mast, tower:type=lighting (ODbL;
# parsed by tools/xcheck/parse_osm.py, 'lighting_masts'). Checked on NAIP 2024, all 70 on contact sheets (review round
# 3): on the open airfield and landside each node sits at the base of an imaged mast (shadow line to the NW, the lamp
# head leaning ~15-25 m east by relief displacement); the 45 at the terminal stand on the facade line, with the leaning
# pole visible over the roof. Those at the facade can fall inside the SFO Museum footprint the app renders (outline
# accuracy +-5 m: NAIP roof lean): a mast whose base is inside or within MAST_CLEAR of a rendered building is moved
# out along the outline normal to MAST_CLEAR (inferred; mastMeta.moved lists them), so no pole is drawn inside a wall.
# Masts closer than 25 m to a data taxiway centreline would be listed (mastMeta.near_taxiway; none are: >= 51 m).
from shapely.geometry import Polygon as _SPoly, Point as _SPt, LineString as _SLS
from shapely.ops import unary_union as _suu, nearest_points as _snp
MAST_CLEAR = 1.5   # m, pole centre -> building outline (foundation radius 0.85 m, js/live/items.js)
_BLD = _suu([_SPoly(p[0], p[1:]).buffer(0) for p in D['terminalComplex']] +   # courtyards (holes) are open ground
            [_SPoly(p[0]).buffer(0) for s_ in D['structures'] if s_['kind'] in ('garage', 'building', 'hangar', 'hotel', 'atc') for p in s_['polys']])
_CLS = [_SLS(c) for c in centerlines if len(c) >= 2]
masts, mast_moved, mast_near_tw = [], [], []
for m in OSM.get('lighting_masts', []):
    x, z = m['w']; p = _SPt(x, z); inside = _BLD.contains(p); d = _BLD.boundary.distance(p)
    if inside or d < MAST_CLEAR:
        q = _snp(_BLD.boundary, p)[0]; v = np.array([x - q.x, z - q.y]); L = float(np.hypot(*v))
        if L < 1e-6:   # on the outline: the normal of the nearest outline segment, pointing out of the building
            e = np.array([q.x, q.y]); t = np.array([1.0, 0.0])
            for g in getattr(_BLD, 'geoms', [_BLD]):
                ring = np.array(g.exterior.coords)
                k = int(np.argmin([_SLS(ring[i:i + 2]).distance(q) for i in range(len(ring) - 1)])); t = ring[k + 1] - ring[k]
                if _SLS(ring[k:k + 2]).distance(q) < 1e-3: break
            v = np.array([-t[1], t[0]]) / max(1e-9, float(np.hypot(*t)))
            if _BLD.contains(_SPt(*(e + v * 0.1))): v = -v
        else:
            v = v / L * (-1 if inside else 1)
        n = np.array([q.x, q.y]) + v * MAST_CLEAR
        if _BLD.contains(_SPt(*n)) or _BLD.boundary.distance(_SPt(*n)) < MAST_CLEAR - 0.05:
            # concave corner: the nearest point (0.25 m rings up to 8 m) that is outside and MAST_CLEAR from the outline
            n = None
            for r_ in np.arange(0.25, 8.01, 0.25):
                cand = [np.array([x + r_ * math.cos(a_), z + r_ * math.sin(a_)]) for a_ in np.linspace(0, 2 * math.pi, max(12, int(r_ * 12)), endpoint=False)]
                cand = [c_ for c_ in cand if not _BLD.contains(_SPt(*c_)) and _BLD.boundary.distance(_SPt(*c_)) >= MAST_CLEAR]
                if cand: n = cand[0]; break
            if n is None:
                print('  mast %d: no clear position within 8 m of the building - dropped' % m['id']); mast_moved.append({'osm_id': m['id'], 'dropped': True}); continue
        mast_moved.append({'osm_id': m['id'], 'from': [round(x, 2), round(z, 2)], 'moved_m': round(float(np.hypot(n[0] - x, n[1] - z)), 2), 'was_inside': bool(inside)})
        x, z = float(n[0]), float(n[1])
    dcl = min(c.distance(_SPt(x, z)) for c in _CLS)
    if dcl < 25: mast_near_tw.append({'osm_id': m['id'], 'dist_centreline': round(dcl, 1)})
    masts.append([round(x, 2), round(z, 2)])
print('masts', len(masts), 'moved off buildings', len(mast_moved), 'near taxiway centrelines', len(mast_near_tw))
dTW = dist_to(TW | RW)   # (used by the service-road lines below)

# ---------------------------------------------------------------- service road lines along the terminal face
roads = []
for off in (7.0, 14.5):
    band = ((dT <= off) & (TC == 0)).astype(np.uint8)
    cs, _ = cv2.findContours(band | TC, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs:
        c = c[:, 0, :]; run = []
        for p in c:
            x, y = p
            ok = apron[min(H - 1, y), min(W - 1, x)] and dTW[y, x] > 6
            if ok: run.append(world((x + 0.5, y + 0.5)))
            else:
                if len(run) > 25: roads.append({'off': off, 'pts': simplify(run, 0.5)})
                run = []
        if len(run) > 25: roads.append({'off': off, 'pts': simplify(run, 0.5)})
print('road lines', len(roads))

# Review round 3: the 45 m 'patches' paved wherever an ADS-B aircraft of data/snapshot.js (adsb.fi + adsb.lol, not a
# listed source) stood off the mapped pavement - circular, and two of them paved grass between 1L/19R and 1R/19L. They
# are gone; the real pavement at the other three is classified on NAIP by tools/imagery/paint_pave_naip.py.
out = {'attribution': 'Taxiway centrelines: OpenStreetMap aeroway=taxiway ways ((c) OpenStreetMap contributors, ODbL 1.0), '
                      'checked and locally moved onto the paint measured on USDA NAIP 2024 (public domain). Holding positions: '
                      'painted markings measured on NAIP 2024 (src naip; locator osm = found via an OSM aeroway=holding_position) or OSM '
                      'aeroway=holding_position (src osm). Centrelines with src naip: traced on the NAIP paint where OSM has no way. Taxiway edge lines: '
                      'SFO Museum sfomuseum-data-architecture taxiway outlines (CDLA-Permissive-1.0) snapped to the paint measured on NAIP 2024 '
                      '(edgeMeta). Floodlight masts: OpenStreetMap man_made=mast + tower:type=lighting (ODbL). Apron outline and road lines: '
                      'derived from SFO Museum geometry, inferred. See tools/build_airfield_details.py and docs/ATTRIBUTION.md',
       'frame': geo_frame.FRAME_ID, 'apron': apron_polys, 'centerlines': centerlines, 'centerlineMeta': cl_meta, 'centerlineStats': CL_STATS,
       'holds': holds, 'holdStats': HOLD_STATS, 'holdsDropped': hold_log, 'edges': edges, 'edgeMeta': edge_meta, 'edgeStats': EDGE_STATS,
       'masts': masts, 'mastMeta': {'src': 'osm man_made=mast + tower:type=lighting (base position)', 'n': len(masts),
                                    'check': 'NAIP 2024: all 70 viewed on contact sheets (base of an imaged mast; at the terminal on the facade line), review round 3',
                                    'height': 'not in OSM; js/live/items.js MAST_H is inferred',
                                    'clear_of_buildings_m': MAST_CLEAR, 'moved': mast_moved, 'near_taxiway': mast_near_tw},
       'roads': roads}
json.dump(out, open(os.path.join(ROOT, 'data', 'sfo_details.json'), 'w'), separators=(',', ':'))
open(os.path.join(ROOT, 'data', 'sfo_details.js'), 'w').write('// generated by tools/build_airfield_details.py - ODbL 1.0: taxiway centrelines contain information from OpenStreetMap (c) OpenStreetMap contributors; holds measured on USDA NAIP 2024; apron/edges from SFO Museum (CDLA-Permissive-1.0) - docs/ATTRIBUTION.md\nexport const DETAILS = ' + json.dumps(out, separators=(',', ':')) + ';\n')
print('wrote', os.path.getsize(os.path.join(ROOT, 'data', 'sfo_details.json')) // 1024, 'KB')

# ---------------------------------------------------------------- debug image
img = np.zeros((H, W, 3), np.uint8); img[:] = (40, 70, 40)
img[apron > 0] = (150, 150, 150); img[TW > 0] = (90, 90, 90); img[RW > 0] = (50, 50, 50); img[REM > 0] = (170, 170, 170); img[TC > 0] = (180, 120, 60); img[BLD > 0] = (140, 90, 50)
for l in centerlines: cv2.polylines(img, [np.round(px(l)).astype(np.int32)], False, (0, 220, 255), 1)
for e in edges: cv2.polylines(img, [np.round(px(e)).astype(np.int32)], False, (0, 160, 255), 1)
for h in holds: cv2.line(img, tuple(np.round(px([h['a']])[0]).astype(int)), tuple(np.round(px([h['b']])[0]).astype(int)), (0, 0, 255), 3)
for m in masts: cv2.circle(img, tuple(np.round(px([m])[0]).astype(int)), 5, (255, 255, 255), -1)
for r in roads: cv2.polylines(img, [np.round(px(r['pts'])).astype(np.int32)], False, (255, 255, 255), 1)
snap = json.loads(open(os.path.join(ROOT, 'data', 'snapshot.js')).read().split('SNAPSHOT = ')[1].split(';\nexport')[0])
for a in snap['ac']:
    if a.get('alt_baro') != 'ground': continue
    x, z = ll2w(a['lat'], a['lon'])
    col = (0, 255, 0) if PAVED[int((z - Z0) / RES), int((x - X0) / RES)] else (255, 0, 255)
    cv2.circle(img, (int((x - X0) / RES), int((z - Z0) / RES)), 9, col, 2)
cv2.imwrite(os.path.join(ROOT, 'out', 'details', 'airfield.png'), img)
cv2.imwrite(os.path.join(ROOT, 'out', 'details', 'airfield_small.png'), cv2.resize(img, (W // 3, H // 3), interpolation=cv2.INTER_AREA))
