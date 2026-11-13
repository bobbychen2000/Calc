"""Tie-down rows from painted tee marks on the committed NAIP mosaics (USDA NAIP 2024 / 2022, public domain).

New for hwd3d (no sfo3d counterpart: SFO has no tie-downs). Used by tools/build_airport.py.

What is detected
  FAA AC 150/5300-13B Chg 1 (refs/cache/faa/ac150_5300_13b_chg1_p136_181_284-288.pdf), Appendix E, para E.2.3.2: a tiedown "Commonly includes a 6-inch (152 mm) yellow striped
  marking in the shape of a tee to demonstrate the location for wing axis and tail location"; Figure E-1: the two wing
  anchors sit at the ends of the cross-bar, the tail anchor at the end of the stem. On the HWD NAIP mosaics the tees are
  light lines on dark asphalt (G2 visual notes: crisp on the Green Ramp, faint on the West Hangars apron). The cross-bar
  and stem lengths below were read by eye on a row-aligned 0.08 m resampling of NAIP 2024 on the Green Ramp
  (out/phase1/g5/green_rot.png): cross-bar about 6.0 m, stem about 4.8 m [obs, by eye, +-0.5 m].
  Parked aircraft there sit with the wing over the cross-bar and the tail over the stem end (nose away from the stem):
  heading of a spot = stem direction + 180 deg [obs on the Green Ramp rows: horizontal tail over the stem end].

Method
  1. Paint index D = gray - median(gray, 4 m) on a world grid of RES m inside each OSM apron (minus OSM hangar /
     building footprints + 1 m); bright objects (D > BRIGHT: aircraft, vehicles) and dark ones (D < -25: shadows,
     tyres) are set to 0 before matching.
  2. Normalised cross-correlation (over the template's 11 m square box) with a tee template (Gaussian line profile,
     sigma 0.3 m) for stem headings every ANG_STEP deg (FFT); best NCC and its heading per cell.
  3. Seeds = local maxima (3 m) with NCC >= SEED_NCC whose arms are confirmed on the image: mean paint contrast along the
     cross-bar and along the stem >= SEED_ARM DN against +-1 m beside them, and the paint does NOT continue beyond the
     bar ends, beyond the stem end or behind the bar (each < 0.5 x the arm contrast: rejects long lines, crosses and
     aircraft), not on a bright object.
  4. Rows: seeds of one apron with the same stem heading (+-12 deg) and the same across-row position (+-1.2 m) form a
     row (>= MIN_ROW_SEEDS seeds). One pitch per apron is fitted to all within-row gaps (gap = k x pitch, k = 1..6, pitch 9-16 m).
  5. Every pitch position of a row (between its first and last seed, and outward while a tee or a parked aircraft is
     found) is scored in both years (and, since the Phase 1 review, the aircraft mask inside a GA-single outline on the
     tee is measured: Grid.planform, PLAN_OCC_M2): 'tee' (NCC >= ROW_NCC and arms >= ROW_ARM within +-1.2 m along / +-0.8 m
     across) -> the spot is observed; 'aircraft' (the aircraft mask - D > AC_D closed by a 0.75 m disk - covers
     >= OCC_M2 within OCC_R m) or 'none' -> the spot is inferred from the row (evidence lists
     what was seen).
All thresholds are constants below; the result lists them.
"""
import math, os, sys
import numpy as np
from scipy import ndimage as nd
from scipy.signal import fftconvolve
from shapely.geometry import Point, Polygon
from shapely.prepared import prep

# Basis (Phase 1 review): BAR / STEM / SIG / BRIGHT / AC_* are read or measured as stated on each line; the matching and
# row thresholds (ANG_STEP, SEED_*, ROW_*, MIN_ROW_SEEDS) were chosen by looking at the Green Ramp and FBO-ramp seeds (G5);
# their sensitivity was not tested.
RES = 0.25          # m, matching grid
BAR, STEM = 6.0, 4.8
SIG = 0.3           # m, line profile of the template (NAIP 0.6 m pixels blur the 0.15 m paint)
ANG_STEP = 7.5      # deg
BRIGHT = 45.0       # DN above the 4 m median: aircraft / vehicles (tee paint is 10-30 DN)
SEED_NCC, SEED_ARM = 0.45, 6.0
ROW_NCC, ROW_ARM = 0.35, 4.0
ROW_ANG, ROW_ACROSS = 12.0, 1.2
MIN_ROW_SEEDS = 4   # a row needs >= 4 seeds (2- and 3-seed 'rows' on the FBO ramps were not tees when looked at)
PITCH_RANGE = (9.0, 16.0)   # m, pitches tried by fit_pitch [chosen: below a C150 span plus a small gap (10.2 m, FAA ACD)
                            # up to an ADG I span plus 10 ft is 14.9 + 3.0 m; HWD's fit is 12.15 m, inside; sensitivity not tested]
AC_R = 3.0          # m, aircraft blob centroid -> spot (ramp-spot evidence)
OCC_R, OCC_M2 = 2.5, 3.0   # m, m2: a row position is 'occupied' when the aircraft mask covers >= OCC_M2 within OCC_R
AC_D = 30.0         # DN above the 4 m median: aircraft mask (closed by a 0.75 m disk; thin wings fragment at 45 DN)
AC_AREA = (8.0, 150.0)   # m2, mask area of one parked aircraft (GA singles about 10-30 m2 at this blur)
AC_EXT = (7.0, 24.0)     # m, its largest extent (GA singles 9-12 m span; rows wing to wing merge and are rejected)
# planform occupancy of a tie-down (Phase 1 review, 2026-11-12): the aircraft mask inside the outline of a GA single
# parked on the tee (wing over the cross-bar, tail over the stem: wing box +-PLAN_WING[0] m along the bar x +-PLAN_WING[1]
# m, fuselage box +-PLAN_FUS[0] m from PLAN_FUS[2] m ahead of the bar to PLAN_FUS[1] m behind it; C172 span 11.0 m and
# length 8.3 m, FAA ACD, with room for the 1-4 m offsets seen on the Green Ramp). Calibrated on the Green Ramp: empty tees
# seen in both years carry 0-0.9 m2 of mask, the 14 positions a reviewer saw occupied on NAIP 2024 2.8-7.6 m2 ->
# threshold PLAN_OCC_M2 (checked by eye on out/phase1/review_fix/green_td_2024.png).
PLAN_WING = (5.5, 1.5)
PLAN_FUS = (0.8, 6.5, 2.5)
PLAN_OCC_M2 = 2.5
# position / heading tolerance of the planform (round-1 re-check, 2026-11-12: TW054N324 had a high wing about 2.3 m off the
# junction and read 0.9 m2): the outline is also tried shifted along the aircraft axis by PLAN_SHIFT (m) and turned by
# PLAN_TURN (deg); the largest mask area counts. Calibration on the Green Ramp (80 positions x 2 years): with the tolerance
# the values split into <= 2.1 m2 and >= 5.6 m2; the 18 positions it adds (TW054N324 in 2024, 17 in 2022, all shifted
# 2-3 m toward the stem) each show an aircraft over the tee by eye (out/phase1/r1/green_td_2022.png / _2024.png)
PLAN_SHIFT = tuple(np.round(np.arange(-3.0, 3.01, 0.5), 2))
PLAN_TURN = (-10.0, 0.0, 10.0)
PARAMS = dict(PLAN_WING=list(PLAN_WING), PLAN_FUS=list(PLAN_FUS), PLAN_OCC_M2=PLAN_OCC_M2, PLAN_SHIFT=[float(v) for v in PLAN_SHIFT], PLAN_TURN=list(PLAN_TURN),
              RES=RES, BAR=BAR, STEM=STEM, SIG=SIG, ANG_STEP=ANG_STEP, BRIGHT=BRIGHT, SEED_NCC=SEED_NCC,
              SEED_ARM=SEED_ARM, ROW_NCC=ROW_NCC, ROW_ARM=ROW_ARM, ROW_ANG=ROW_ANG, ROW_ACROSS=ROW_ACROSS, MIN_ROW_SEEDS=MIN_ROW_SEEDS,
              PITCH_RANGE=list(PITCH_RANGE), AC_R=AC_R, OCC_R=OCC_R, OCC_M2=OCC_M2, AC_D=AC_D, AC_AREA=list(AC_AREA), AC_EXT=list(AC_EXT))


def _unit(h):
    return np.array([math.sin(math.radians(h)), -math.cos(math.radians(h))])


def template(theta):
    """tee with the stem toward heading theta (world x east, z south); origin = junction; window W"""
    s = _unit(theta); b = np.array([-s[1], s[0]])
    g = np.arange(-5.5, 5.5 + 1e-9, RES)
    X, Z = np.meshgrid(g, g)
    pu = X * b[0] + Z * b[1]; pv = X * s[0] + Z * s[1]

    def seg(a0, a1, along, across):
        d = np.maximum(0, np.maximum(a0 - along, along - a1)); return np.exp(-0.5 * (across ** 2 + d ** 2) / SIG ** 2)
    T = np.maximum(seg(-BAR / 2, BAR / 2, pu, pv), seg(0, STEM, pv, pu))
    W = (np.abs(pu) <= BAR / 2 + 1.2) & (pv >= -1.2) & (pv <= STEM + 1.2)
    return T, W


class Grid:
    """paint-index grid of one apron in one NAIP year"""
    def __init__(self, N, poly, holes):
        x0, z0, x1, z1 = poly.bounds
        self.xs = np.arange(x0 - 6, x1 + 6, RES); self.zs = np.arange(z0 - 6, z1 + 6, RES)
        X, Z = np.meshgrid(self.xs, self.zs)
        I = N.sample(X, Z, 'gray')
        D = I - nd.median_filter(I, size=int(round(4.0 / RES)))
        self.bright = D > BRIGHT
        disk = np.hypot(*np.mgrid[-3:4, -3:4]) <= 3.0          # 0.75 m radius at RES 0.25
        self.acmask = nd.binary_closing(D > AC_D, structure=disk)
        D = np.where((D > BRIGHT) | (D < -25), 0.0, D)
        self.D = D; self.N = N; self.poly = poly; self.holes = holes
        self.best = np.full(D.shape, -1.0); self.ang = np.zeros(D.shape)
        # NCC over the template's square box (same box for every heading): local sums by a box filter, the correlation
        # by one real FFT of D and one per heading
        T0, _ = template(0.0); k = T0.shape[0]; n = float(k * k)
        s1 = nd.uniform_filter(D, size=k, mode='constant') * n
        s2 = nd.uniform_filter(D * D, size=k, mode='constant') * n
        den = np.sqrt(np.maximum(s2 - s1 * s1 / n, 1e-6))
        sh = (D.shape[0] + k - 1, D.shape[1] + k - 1)
        Dp = np.fft.rfft2(D, sh); h = k // 2
        for th in np.arange(0, 360, ANG_STEP):
            T, _ = template(th); Tm = T - T.mean()
            num = np.fft.irfft2(Dp * np.fft.rfft2(Tm[::-1, ::-1], sh), sh)[h:h + D.shape[0], h:h + D.shape[1]]
            ncc = num / (den * math.sqrt((Tm ** 2).sum()))
            u = ncc > self.best
            self.best = np.where(u, ncc, self.best); self.ang = np.where(u, th, self.ang)
        self.bright_d = nd.binary_dilation(self.bright, iterations=int(round(1.0 / RES)))

    def rc(self, x, z):
        return int(round((z - self.zs[0]) / RES)), int(round((x - self.xs[0]) / RES))

    def arms(self, x, z, th):
        s = _unit(th); b = np.array([-s[1], s[0]]); p = np.array([x, z])

        def line(d, a0, a1):
            a = np.arange(a0, a1 + 1e-9, 0.2); n = np.array([-d[1], d[0]])
            P = p[None] + a[:, None] * d[None]
            on = self.N.sample(P[:, 0], P[:, 1], 'gray').mean()
            off = 0.5 * (self.N.sample(P[:, 0] + n[0], P[:, 1] + n[1], 'gray').mean() +
                         self.N.sample(P[:, 0] - n[0], P[:, 1] - n[1], 'gray').mean())
            return float(on - off)
        return dict(bar=line(b, -BAR / 2 + 0.6, BAR / 2 - 0.6), stem=line(s, 0.8, STEM - 0.4),
                    bar_out=max(line(b, BAR / 2 + 0.6, BAR / 2 + 2.6), line(b, -BAR / 2 - 2.6, -BAR / 2 - 0.6)),
                    stem_out=line(s, STEM + 0.6, STEM + 2.6), back=line(-s, 0.8, 3.0))

    def seeds(self):
        mx = nd.maximum_filter(self.best, size=int(round(3.0 / RES)))
        ys, xs = np.nonzero((self.best == mx) & (self.best >= SEED_NCC))
        inner = prep(self.poly.buffer(-1.0)); out = []
        for r, c in zip(ys, xs):
            x, z = float(self.xs[c]), float(self.zs[r])
            if not inner.contains(Point(x, z)) or any(h.contains(Point(x, z)) for h in self.holes): continue
            if self.bright_d[r, c]: continue
            th = float(self.ang[r, c]); a = self.arms(x, z, th)
            if (a['bar'] >= SEED_ARM and a['stem'] >= SEED_ARM and a['bar_out'] < 0.5 * a['bar'] and
                    a['stem_out'] < 0.5 * a['stem'] and a['back'] < 0.5 * a['stem']):
                out.append(dict(x=x, z=z, th=th, ncc=float(self.best[r, c]), **{k: round(v, 1) for k, v in a.items()}))
        return out

    def score(self, x, z, th):
        """best tee near (x, z) with stem heading within ROW_ANG of th: +-1.2 m along the bar, +-0.8 m along the stem"""
        s = _unit(th); b = np.array([-s[1], s[0]]); best = None
        for du in np.arange(-1.2, 1.21, RES):
            for dv in np.arange(-0.8, 0.81, RES):
                q = np.array([x, z]) + du * b + dv * s; r, c = self.rc(*q)
                if not (0 <= r < self.best.shape[0] and 0 <= c < self.best.shape[1]): continue
                if abs((self.ang[r, c] - th + 180) % 360 - 180) > ROW_ANG: continue
                if best is None or self.best[r, c] > best[0]: best = (float(self.best[r, c]), float(q[0]), float(q[1]), float(self.ang[r, c]))
        if best is None or best[0] < ROW_NCC: return None
        a = self.arms(best[1], best[2], best[3])
        if a['bar'] < ROW_ARM or a['stem'] < ROW_ARM: return None
        r, c = self.rc(best[1], best[2])
        if self.bright_d[r, c]: return None
        return dict(ncc=round(best[0], 3), x=best[1], z=best[2], th=best[3], bar=round(a['bar'], 1), stem=round(a['stem'], 1))

    def occupied(self, x, z):
        """a parked aircraft over (x, z): >= OCC_M2 of the aircraft mask within OCC_R m"""
        r, c = self.rc(x, z); k = int(round(OCC_R / RES))
        sub = self.acmask[max(0, r - k):r + k + 1, max(0, c - k):c + k + 1]
        yy, xx = np.mgrid[max(0, r - k) - r:max(0, r - k) - r + sub.shape[0], max(0, c - k) - c:max(0, c - k) - c + sub.shape[1]]
        return bool((sub & (np.hypot(yy, xx) <= k)).sum() * RES * RES >= OCC_M2)

    def planform(self, x, z, stem_hdg):
        """m2 of the aircraft mask inside the outline of a GA single parked on a tee at (x, z) (nose away from the stem),
        the largest over shifts along the aircraft axis (PLAN_SHIFT) and turns (PLAN_TURN)"""
        h0 = math.radians((stem_hdg + 180) % 360); a0 = np.array([math.sin(h0), -math.cos(h0)])
        r, c = self.rc(x, z); k = int(round(12.5 / RES))
        r0, r1, c0, c1 = max(0, r - k), min(self.acmask.shape[0], r + k + 1), max(0, c - k), min(self.acmask.shape[1], c + k + 1)
        sub = self.acmask[r0:r1, c0:c1]
        yy, xx = np.mgrid[r0 - r:r1 - r, c0 - c:c1 - c] * RES
        best = 0.0
        for dv in PLAN_SHIFT:
            for dt in PLAN_TURN:
                h = h0 + math.radians(dt); u = np.array([math.sin(h), -math.cos(h)]); b = np.array([math.cos(h), math.sin(h)])
                ox, oz = xx - a0[0] * dv, yy - a0[1] * dv
                pu = ox * u[0] + oz * u[1]; pb = ox * b[0] + oz * b[1]
                wing = (np.abs(pb) <= PLAN_WING[0]) & (np.abs(pu) <= PLAN_WING[1])
                fus = (np.abs(pb) <= PLAN_FUS[0]) & (pu <= PLAN_FUS[2]) & (pu >= -PLAN_FUS[1])
                best = max(best, float((sub & (wing | fus)).sum() * RES * RES))
        return best

    def aircraft(self):
        """parked aircraft on the image: the aircraft mask fragments (a high wing, the fuselage and the tail break apart
        at 0.6 m) are grouped by a 1 m dilation; a group whose mask area is AC_AREA m2 and whose largest extent is AC_EXT m
        is one aircraft (centroid of its mask pixels), if it lies inside the apron and not on a mapped building"""
        disk = np.hypot(*np.mgrid[-4:5, -4:5]) <= 4.0          # 1 m at RES 0.25
        lab, n = nd.label(nd.binary_dilation(self.acmask, structure=disk))
        if n == 0: return []
        lab = np.where(self.acmask, lab, 0)
        out = []
        for i, sl in enumerate(nd.find_objects(lab)):
            if sl is None: continue
            m = lab[sl] == i + 1; area = m.sum() * RES * RES
            if not (AC_AREA[0] <= area <= AC_AREA[1]): continue
            rr, cc = np.nonzero(m)
            pts = np.c_[cc, rr] * RES; ev = np.linalg.eigh(np.cov(pts.T))[1] if len(pts) > 2 else np.eye(2)
            proj = pts @ ev; ptp = np.ptp(proj, axis=0); ext = float(ptp.max())
            if not (AC_EXT[0] <= ext <= AC_EXT[1]): continue
            x = float(self.xs[0] + (sl[1].start + cc.mean()) * RES); z = float(self.zs[0] + (sl[0].start + rr.mean()) * RES)
            P = Point(x, z)
            if not self.poly.contains(P) or any(h.contains(P) for h in self.holes): continue
            # shape (Phase 1 review): minor extent and fill of the blob's principal-axis box (a vehicle is a compact
            # rectangle, an aircraft a cross); and the two halves of a 1-D 2-means split along the major axis (two
            # aircraft parked wing to wing merge into one blob)
            u = proj[:, int(np.argmax(ptp))]; c0, c1 = np.percentile(u, [25, 75])
            for _ in range(20):
                g = np.abs(u - c0) <= np.abs(u - c1); c0, c1 = u[g].mean(), u[~g].mean() if (~g).any() else c1
            halves = [[round(float(self.xs[0] + (sl[1].start + cc[k].mean()) * RES), 2), round(float(self.zs[0] + (sl[0].start + rr[k].mean()) * RES), 2)]
                      for k in (g, ~g) if k.any()]
            out.append(dict(x=x, z=z, area=round(float(area), 1), extent=round(ext, 1), minor=round(float(ptp.min()), 1),
                            fill=round(float(area / max(ptp[0] * ptp[1], 1e-6)), 2), halves=halves))
        return out


def _ang_close(a, b, tol):
    return abs((a - b + 180) % 360 - 180) <= tol


def merge_seeds(lists):
    """union of the seeds of several years: same place (1.0 m) and heading (ROW_ANG) -> one seed with its years"""
    out = []
    for year, L in lists:
        for s in L:
            for o in out:
                if math.hypot(o['x'] - s['x'], o['z'] - s['z']) < 1.0 and _ang_close(o['th'], s['th'], ROW_ANG):
                    o['years'].append(year); break
            else:
                out.append(dict(s, years=[year]))
    return out


def rows_of(seeds):
    """group seeds into rows (same stem heading, same across-row coordinate)"""
    groups = []
    for s in sorted(seeds, key=lambda s: (s['th'], s['x'], s['z'])):
        for g in groups:
            if _ang_close(g['th'], s['th'], ROW_ANG):
                st = _unit(g['th'])
                v = s['x'] * st[0] + s['z'] * st[1]
                if abs(v - g['v']) <= ROW_ACROSS:
                    g['m'].append(s); vs = [m['x'] * st[0] + m['z'] * st[1] for m in g['m']]; g['v'] = float(np.median(vs)); break
        else:
            st = _unit(s['th']); groups.append(dict(th=s['th'], v=s['x'] * st[0] + s['z'] * st[1], m=[s]))
    rows = []
    for g in groups:
        if len(g['m']) < MIN_ROW_SEEDS: continue
        th = float(np.degrees(np.arctan2(np.mean([math.sin(math.radians(m['th'])) for m in g['m']]),
                                         np.mean([math.cos(math.radians(m['th'])) for m in g['m']]))) % 360)
        st = _unit(th); b = np.array([-st[1], st[0]])
        us = sorted(m['x'] * b[0] + m['z'] * b[1] for m in g['m'])
        v = float(np.median([m['x'] * st[0] + m['z'] * st[1] for m in g['m']]))
        rows.append(dict(th=th, v=v, u=us, seeds=g['m']))
    return rows


def fit_pitch(rows):
    gaps = [b - a for r in rows for a, b in zip(r['u'], r['u'][1:]) if b - a > 2.0]
    if not gaps: return None, None
    best = None
    for p in np.arange(PITCH_RANGE[0], PITCH_RANGE[1] + 1e-9, 0.01):
        k = np.clip(np.round(np.array(gaps) / p), 1, 6); res = np.abs(np.array(gaps) - k * p)
        cost = float(np.sum(np.minimum(res, 2.0)))
        if best is None or cost < best[0] - 1e-9: best = (cost, float(p), float(np.median(res)))
    return round(best[1], 2), round(best[2], 2)


def walk_rows(rows, pitch, grids, acs, inner, holes):
    """spots of every row: grids = {year: Grid}, acs = {year: [aircraft blobs]}; inner = prepared apron polygon
    shrunk by 1 m; holes = building footprints. Returns a list of spot dicts (row-wise, along-row order)."""
    out = []
    for ri, r in enumerate(rows):
        st = _unit(r['th']); b = np.array([-st[1], st[0]]); p = pitch
        ang = np.array([2 * math.pi * (u % p) / p for u in r['u']])
        u0 = float((math.atan2(np.sin(ang).mean(), np.cos(ang).mean()) % (2 * math.pi)) * p / (2 * math.pi))
        ks = [int(round((u - u0) / p)) for u in r['u']]
        resid = [round(u - (u0 + k * p), 2) for u, k in zip(r['u'], ks)]

        def probe(k):
            u = u0 + k * p; q = u * b + r['v'] * st; x, z = float(q[0]), float(q[1]); P = Point(x, z)
            if not inner.contains(P) or any(h.contains(P) for h in holes): return None
            tee = {}
            for y, g in grids.items():
                t = g.score(x, z, r['th'])
                if t: tee[y] = t
            ac = sorted(y for y, g in grids.items() if g.occupied(x, z))
            pl = {y: round(g.planform(x, z, r['th']), 1) for y, g in sorted(grids.items())}
            return dict(k=k, x=x, z=z, tee=tee, ac=ac, pl=pl)
        got = {}
        for k in range(min(ks), max(ks) + 1):
            pr = probe(k)
            if pr: got[k] = pr
        for step in (-1, 1):
            k = (min(ks) if step < 0 else max(ks)) + step
            while True:
                pr = probe(k)
                if not pr or not (pr['tee'] or pr['ac']): break
                got[k] = pr; k += step
        for k in sorted(got):
            g_ = got[k]
            if g_['tee']:
                ys = sorted(g_['tee']); t = g_['tee'][ys[-1]]
                x, z = float(np.mean([g_['tee'][y]['x'] for y in ys])), float(np.mean([g_['tee'][y]['z'] for y in ys]))
            else:
                x, z = g_['x'], g_['z']
            out.append(dict(row=ri, k=k, x=x, z=z, stem_hdg=r['th'], tee_years=sorted(g_['tee']),
                            tee=({y: {kk: g_['tee'][y][kk] for kk in ('ncc', 'bar', 'stem')} for y in g_['tee']}),
                            aircraft_years=g_['ac'], aircraft_planform_m2=g_['pl'],
                            aircraft_planform_years=sorted(y for y, v in g_['pl'].items() if v >= PLAN_OCC_M2),
                            pred=[round(g_['x'], 2), round(g_['z'], 2)]))
        r['u0'] = round(u0, 2); r['k_seed'] = ks; r['seed_resid_m'] = resid
    return out
