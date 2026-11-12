"""Registration check of the HWD NAIP mosaics against the FAA NASR runway ends and displaced thresholds.

Adapted from sfo3d/tools/imagery/naip_faa_check.py @ a967f9b (same idea: sample NAIP through the exact mapping
world -> lat/lon -> UTM 10N -> pixel and locate painted runway markings in runway-aligned profiles). Changed for HWD:
both runways are parallel (true 119.86 deg), so the lateral checks alone cannot give a 2-D shift; instead every end
gets its own along-track measurement from the marking that the FAA standard ties to the end / threshold, and its own
lateral measurement from the centreline stripes and the edge stripes. HWD has displaced thresholds on 10R and 28L
with yellow demarcation bars at the runway ends (seen in NAIP 2024 crops), so the feature kinds differ per end.

FAA marking geometry used (AC 150/5340-1M Change 1, "Standards for Airport Markings", 12/23/2020,
https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-1M-Chg-1-Airport-Markings.pdf , read 2026-11-12):
  2.9.1.3/2.9.1.5  threshold bar: "located perpendicular to the runway centerline and on the landing portion of the
                   runway. The outboard edge of the marking is aligned with the location labeled 'start of runway
                   displaced threshold' ... or 'start of runway threshold'"; "10 feet (3.1 m) in width".
  2.9.3.3/2.9.3.5  demarcation bar (yellow): "on a blast pad, stopway, or an aligned taxiway ... at the point of
                   intersection with the start of the runway ... no part of the demarcation bar is on the [usable]
                   runway"; "3 feet (0.9 m) wide".
  2.5 Location     threshold stripes: "The runway threshold marking starts 20 feet (6 m) from the actual start point
                   of the runway threshold"; "Previously, when a displaced threshold was painted or a blast pad or
                   stopway added, the 20-foot (6-m) dimension was increased to 30 feet (9 m)"; stripes "150 feet
                   (45.7 m) long".
  2.4              centreline "located along the physical center of the runway width"; stripes 120 ft / gaps 80 ft.
  2.8              edge marking: "outer edge of each stripe approximately on the edge of the paved useable runway".
Which marking exists at which end was read from the NAIP 2024 crops (hwd3d/out/phase1/crop_2024_*.png), not from a
FAA source: 10R and 28L ends = yellow demarcation bar with yellow arrowheads beyond it; 10R and 28L displaced
thresholds = white threshold bar with white arrowheads before it; 10L end = white threshold bar (yellow arrowheads
on the pavement before it); 28R end = no bar, the threshold stripes begin a few metres inside the end.

Conventions: along = metres from the named end toward the opposite end (+ = inward); across = metres to the right of
that direction. Residual = NAIP-measured position - position predicted from NASR + AC geometry. World residual
(dx east, dz south) and (dE, dN) are also given, so that a uniform image shift shows as the same vector at all ends.
Feature edges are half-maximum crossings of runway-aligned profiles (0.1 m steps, bilinear interpolation of the
native 0.6 m pixels; a robust percentile across the runway width removes arrowheads / stripes / aircraft).

Outputs: refs/cache/naip/naip_reg_check.json (committed; own measurement),
         out/phase1/regcheck_<year>_<feature>.png (runway-aligned crops with predicted / measured lines) and
         out/phase1/regcheck_profiles_<year>.png
usage: python3 -I hwd3d/tools/imagery/naip_reg_check.py [--years 2024,2022]
"""
import argparse, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import F, CACHE, OUT, NaipSampler  # noqa: E402

FT = 0.3048
BAR_W = 10 * FT          # threshold bar width (AC 2.9.1.5)
DEM_W = 3 * FT           # demarcation bar width (AC 2.9.3.5)
STRIPE_GAP = 20 * FT     # threshold stripes start (AC 2.5)
STRIPE_GAP_OLD = 30 * FT
STRIPE_LEN = 150 * FT

# feature list: (feature id, runway end, kind, predicted 'along' of the measured quantity relative to the end)
#   kind 'dem'    : yellow demarcation bar, measured = bar centre, predicted = end - DEM_W/2
#   kind 'bar'    : white threshold bar, measured = outboard (approach-side) edge, predicted = threshold (along = disp)
#   kind 'stripes': start of the threshold stripes, predicted = threshold + 20 ft (30 ft for older markings)
FEATURES = [
    ('10R_end', '10R', 'dem'), ('10R_thr', '10R', 'bar'), ('10R_stripes', '10R', 'stripes'),
    ('28L_end', '28L', 'dem'), ('28L_thr', '28L', 'bar'), ('28L_stripes', '28L', 'stripes'),
    ('10L_end', '10L', 'bar'), ('10L_stripes', '10L', 'stripes'),
    ('28R_stripes', '28R', 'stripes'),
]


def width(end):
    rid = '10R/28L' if end in ('10R', '28L') else '10L/28R'
    return F.RWY_DATA[rid]['widthFt'] * FT


class RunwaySampler:
    def __init__(self, S, end):
        self.S, self.end = S, end
        A = F.rwy_axis(end); self.o, self.d, self.r = np.array(A['origin']), np.array(A['dir']), np.array(A['right'])
        self.L = A['length']; self.W = width(end)

    def grid(self, s, t, band):
        SS, TT = np.meshgrid(s, t, indexing='ij')
        X = self.o[0] + SS * self.d[0] + TT * self.r[0]; Z = self.o[1] + SS * self.d[1] + TT * self.r[1]
        if band == 'white':            # min(R, G, B): white paint high, yellow paint / asphalt / grass low
            return np.minimum(np.minimum(self.S.sample_world(X, Z, 0), self.S.sample_world(X, Z, 1)), self.S.sample_world(X, Z, 2))
        if band == 'yellow':           # (R + G) / 2 - B: yellow paint high, white paint / grey asphalt ~ 0
            return (self.S.sample_world(X, Z, 0) + self.S.sample_world(X, Z, 1)) / 2 - self.S.sample_world(X, Z, 2)
        return self.S.sample_world(X, Z)


def half_crossing(s, p, i, level, step):
    """walk from index i in direction step until p drops below level; linear interpolation of the crossing."""
    j = i
    while 0 <= j + step < len(p) and p[j + step] >= level: j += step
    if not (0 <= j + step < len(p)): return None
    a, b = p[j], p[j + step]
    return float(s[j] + (level - a) / (b - a) * (s[j + step] - s[j]))


def measure_bar(RS, s_pred, kind):
    """profile across a full-width bar -> dict(peak, edge_out, edge_in, centre, width, contrast)."""
    band = 'yellow' if kind == 'dem' else 'white'
    W = RS.W
    t = np.r_[np.arange(-(W / 2 - 2.0), -1.5, 0.25), np.arange(1.5, W / 2 - 2.0, 0.25)]
    s = np.arange(s_pred - 20, s_pred + 20, 0.1)
    G = RS.grid(s, t, band)
    p = np.percentile(G, 25, axis=1)                 # bar covers 100 % of the width; arrows/stripes < 50 %
    m = np.abs(s - s_pred) < 8
    i = int(np.flatnonzero(m)[np.argmax(p[m])])
    pk = s[i]
    out_bg = float(np.median(p[(s > pk - 9) & (s < pk - 3.5)]))
    in_bg = float(np.median(p[(s > pk + 3.5) & (s < pk + 9)]))
    top = float(np.percentile(p[np.abs(s - pk) < (0.8 if kind == 'bar' else 0.3)], 50))
    e_out = half_crossing(s, p, i, (out_bg + top) / 2, -1)
    e_in = half_crossing(s, p, i, (in_bg + top) / 2, +1)
    res = dict(peak=float(pk), edge_out=e_out, edge_in=e_in, top=top, bg_out=out_bg, bg_in=in_bg,
               contrast=top - max(out_bg, in_bg))
    if e_out is not None and e_in is not None:
        res['centre'] = (e_out + e_in) / 2; res['width'] = e_in - e_out
    return res, s, p


def measure_stripes(RS, s_pred):
    """start (outboard end) and inboard end of the threshold-stripe block."""
    W = RS.W
    t = np.r_[np.arange(-(W / 2 - 1.0), -1.0, 0.2), np.arange(1.0, W / 2 - 1.0, 0.2)]
    s = np.arange(s_pred - 20, s_pred + STRIPE_LEN + 20, 0.1)
    G = RS.grid(s, t, 'white')
    p = np.percentile(G, 75, axis=1)                 # stripes cover ~50 % of the width
    hi = float(np.median(p[(s > s_pred + 6) & (s < s_pred + STRIPE_LEN - 10)]))
    lo_out = float(np.median(p[(s > s_pred - 12) & (s < s_pred - 4.5)]))   # may contain the threshold bar: see below
    lo_in = float(np.median(p[(s > s_pred + STRIPE_LEN + 6) & (s < s_pred + STRIPE_LEN + 18)]))
    # the threshold bar (if any) lies 3 m before the stripes: use the lower of the two quieter windows as 'low'
    lo_gap = float(np.min(p[(s > s_pred - 4.5) & (s < s_pred + 1.0)]))
    lo = min(lo_out, lo_gap)
    i0 = int(np.argmin(np.abs(s - (s_pred + 8))))
    start = half_crossing(s, p, i0, (lo + hi) / 2, -1)
    i1 = int(np.argmin(np.abs(s - (s_pred + STRIPE_LEN - 8))))
    stop = half_crossing(s, p, i1, (lo_in + hi) / 2, +1)
    return dict(start=start, stop=stop, length=(stop - start) if (start is not None and stop is not None) else None,
                hi=hi, lo=lo, lo_in=lo_in), s, p


def lateral(S, end, seg=61.0):
    """centreline-stripe and edge-stripe positions per segment along the whole runway (from `end`)."""
    RS = RunwaySampler(S, end); W = RS.W
    t = np.arange(-W / 2 - 6, W / 2 + 6, 0.1)
    rows = []
    for s0 in np.arange(5, RS.L - 5 - seg / 2, seg / 2):
        s = np.arange(s0, min(s0 + seg, RS.L - 5), 0.5)
        G = RS.grid(s, t, 'white')
        p = np.percentile(G, 80, axis=0)
        def pk(t0, win):
            m = np.abs(t - t0) < win; tt, pp = t[m], p[m]
            i = int(np.argmax(pp)); base = float(np.percentile(pp, 15)); half = base + 0.5 * (pp[i] - base)
            j0 = i
            while j0 > 0 and pp[j0 - 1] > half: j0 -= 1
            j1 = i
            while j1 < len(pp) - 1 and pp[j1 + 1] > half: j1 += 1
            w = pp[j0:j1 + 1] - half
            return float((tt[j0:j1 + 1] * w).sum() / w.sum()), float(pp[i] - base), float(tt[j1] - tt[j0] + 0.1)
        c, cc, cw = pk(0.0, 2.5)
        l, lc, lw = pk(-W / 2 + 0.5, 2.5)
        r, rc, rw = pk(W / 2 - 0.5, 2.5)
        rows.append(dict(s=float(s.mean()), cl=c, cl_contrast=cc, cl_w=cw, left=l, right=r, edge_mid=(l + r) / 2,
                         edge_sep=r - l, edge_contrast=[lc, rc]))
    return rows


def robust_line(x, y, k=3.0):
    x = np.asarray(x); y = np.asarray(y); keep = np.ones(len(x), bool)
    for _ in range(5):
        a, b = np.polyfit(x[keep], y[keep], 1)
        r = y - (a * x + b); mad = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep]))) + 1e-3
        nk = np.abs(r) < k * mad
        if (nk == keep).all(): break
        keep = nk
    return float(a), float(b), keep, float(np.std(r[keep]))


def to_world(end, d_along, d_across):
    A = F.rwy_axis(end)
    dx = d_along * A['dir'][0] + d_across * A['right'][0]; dz = d_along * A['dir'][1] + d_across * A['right'][1]
    return dict(dx_east=dx, dz_south=dz, dE=dx, dN=-dz)


def crop_png(S, end, s_c, lines, path, title, half_s=14.0, half_t=None, res=0.15):
    """runway-aligned crop (bilinear, `res` m/px, shown 2x; along runs left->right, i.e. toward the opposite end).
    Lines: (along, colour, label); drawn as ticks in a 34 px band above and below the image plus a thin full-height line."""
    from PIL import Image, ImageDraw
    RS = RunwaySampler(S, end); half_t = half_t or RS.W / 2 + 6
    s = np.arange(s_c - half_s, s_c + half_s, res); t = np.arange(-half_t, half_t, res)
    X, Z = _xz(RS, s, t)
    rgb = np.stack([RS.S.sample_world(X, Z, b) for b in range(3)], -1)
    body = Image.fromarray(np.clip(np.transpose(rgb, (1, 0, 2)), 0, 255).astype(np.uint8)).resize((len(s) * 2, len(t) * 2), Image.NEAREST)
    band = 16 + 14 * len(lines)
    im = Image.new('RGB', (body.size[0], body.size[1] + 2 * band), (0, 0, 0)); im.paste(body, (0, band))
    d = ImageDraw.Draw(im)
    for k, (val, col, lab) in enumerate(lines):
        if val is None: continue
        x = (val - s[0]) / res * 2
        d.line([(x, 14 + 14 * k), (x, band)], fill=col, width=2)
        d.line([(x, band + body.size[1]), (x, im.size[1])], fill=col, width=2)
        for y in range(band, band + body.size[1], 8): d.point((x, y), fill=col)
        d.text((x + 4, 12 + 14 * k), f'{lab} {val:+.2f} m', fill=col)
    d.text((4, 0), title, fill=(255, 255, 0))
    sb = 5.0 / res * 2; d.line([(6, im.size[1] - 6), (6 + sb, im.size[1] - 6)], fill=(255, 255, 255), width=3)
    d.text((10 + sb, im.size[1] - 16), '5 m', fill=(255, 255, 255))
    im.save(path)


def _xz(RS, s, t):
    SS, TT = np.meshgrid(s, t, indexing='ij')
    return RS.o[0] + SS * RS.d[0] + TT * RS.r[0], RS.o[1] + SS * RS.d[1] + TT * RS.r[1]


def check_year(year, plots=True):
    S = NaipSampler(year)
    out = dict(year=year, raster=os.path.relpath(S.src, os.path.join(CACHE, '..', '..', '..')), lateral={}, features={})
    # ---- lateral, per runway (from the 10x end) ----
    for end in ('10R', '10L'):
        rows = lateral(S, end)
        s = np.array([r['s'] for r in rows]); cl = np.array([r['cl'] for r in rows]); em = np.array([r['edge_mid'] for r in rows])
        sep = np.array([r['edge_sep'] for r in rows]); msep = float(np.median(sep))
        # a segment is 'clean' when both peaks are the runway's own stripes: edge separation within 0.3 m of the median
        # (threshold stripes / TDZ bars are picked inside the threshold zones otherwise) and the centreline peak
        # within 0.5 m of the edge-stripe midpoint (inner threshold stripes / TDZ bars sit about 2 m off the centre)
        ok_e = np.abs(sep - msep) < 0.3
        ok_c = ok_e & (np.abs(cl - em) < 0.5)
        xs = np.r_[s[ok_c], s[ok_e]]; ys = np.r_[cl[ok_c], em[ok_e]]
        a, b, keep, sd = robust_line(xs, ys)
        L = F.rwy_axis(end)['length']
        local = {}
        for e2, sel in ((end, s < 400), (F._OPP[end], s > L - 400)):
            v = np.r_[cl[ok_c & sel], em[ok_e & sel]]
            local[e2] = dict(median_m=float(np.median(v)) if len(v) else None, n=int(len(v)),
                             frame=f'right of {end}->{F._OPP[end]}')
        out['lateral'][end] = dict(
            method='per 61 m segment (30.5 m step): 80th-percentile cross profile of min(R,G,B); peak centroids of the '
                   'centreline stripe and of both edge stripes; clean segments only (see code); pooled centreline + '
                   'edge-midpoint samples; robust line fit (3 MAD); per-end value = median of the clean samples within '
                   '400 m of that end',
            fit=dict(slope_m_per_km=a * 1000, offset_at_end_m=b, offset_at_opp_m=a * L + b, sd_m=sd,
                     n_used=int(keep.sum()), n_samples=len(xs), n_seg=len(rows)),
            local_400m=local, edge_sep_median_m=msep,
            cl_minus_edgemid_median_m=float(np.median((cl - em)[ok_c])) if ok_c.any() else None,
            cl_width_median_m=float(np.median([r['cl_w'] for r, k in zip(rows, ok_c) if k])) if ok_c.any() else None,
            segments=[dict({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, clean_edges=bool(e1),
                           clean_cl=bool(c1)) for r, e1, c1 in zip(rows, ok_e, ok_c)])
        print(f'{year} {end}-runway lateral (right of {end}->{F._OPP[end]}): {b:+.2f} m at {end}, {a * L + b:+.2f} m at '
              f'{F._OPP[end]} (line sd {sd:.2f} m, {keep.sum()}/{len(xs)} samples from {ok_e.sum()}/{len(rows)} clean '
              f'segments); local medians {local[end]["median_m"]:+.2f} / {local[F._OPP[end]]["median_m"]:+.2f} m; '
              f'edge-stripe separation {msep:.2f} m (runway {width(end):.2f} m)')
    # lateral offset at a given end, expressed relative to that end's direction (local median within 400 m)
    def lat_at(end, along_from_end):
        base = '10R' if end in ('10R', '28L') else '10L'
        v = out['lateral'][base]['local_400m'][end]['median_m']
        return v if end == base else -v                        # right of 28x = left of 10x
    # ---- along-track features ----
    from PIL import Image
    Gj = json.load(open(os.path.join(CACHE, f'naip_{year}_hwd_rgb.json')))
    tidx = np.asarray(Image.open(os.path.join(CACHE, f'naip_{year}_hwd_tileidx.png')))
    def tile_of(end, along):
        x, z = F.rwy_to_world(end, along); E, N = F.world_to_utm10(x, z); c, r = S.en_to_px(E, N)
        k = int(tidx[int(round(r)), int(round(c))]); return Gj['tiles'][k - 1]['id'] if k else None
    profs = {}
    for fid, end, kind in FEATURES:
        RS = RunwaySampler(S, end); disp = F.thr_disp_m(end)
        if kind == 'dem':
            pred = -DEM_W / 2
            r, s, p = measure_bar(RS, pred, kind); meas = r.get('centre', r['peak']); what = 'demarcation bar centre'
        elif kind == 'bar':
            pred = disp
            r, s, p = measure_bar(RS, pred + BAR_W / 2, kind); meas = r['edge_out']; what = 'threshold bar outboard edge'
        else:
            pred = disp + STRIPE_GAP
            r, s, p = measure_stripes(RS, pred); meas = r['start']; what = 'threshold stripes start'
        d_al = None if meas is None else meas - pred
        d_ac = lat_at(end, pred)
        rec = dict(end=end, kind=kind, measured=what, predicted_along_m=pred, measured_along_m=meas,
                   resid_along_m=d_al, resid_across_m=d_ac, naip_tile=tile_of(end, pred), detail={k: v for k, v in r.items()})
        if kind == 'stripes' and meas is not None:
            rec['resid_along_if_30ft_m'] = meas - (disp + STRIPE_GAP_OLD)
        if d_al is not None:
            rec['resid_world'] = to_world(end, d_al, d_ac)
            rec['resid_norm_m'] = math.hypot(d_al, d_ac)
        out['features'][fid] = rec
        profs[fid] = (s, p, pred, meas)
        f = lambda v: 'n/a' if v is None else f'{v:+.2f}'
        extra = ''
        if kind in ('bar', 'dem') and r.get('width') is not None: extra = f", width {r['width']:.2f} m (nominal {(BAR_W if kind == 'bar' else DEM_W):.2f})"
        if kind == 'stripes' and r.get('length') is not None: extra = f", block length {r['length']:.2f} m (nominal {STRIPE_LEN:.2f})"
        print(f'{year} {fid:12s} {what}: predicted {pred:7.2f} m, measured {f(meas)} -> along {f(d_al)}, across {d_ac:+.2f} m{extra}')
        if plots:
            lines = [(pred, (255, 60, 60), 'NASR/AC predicted'), (meas, (60, 255, 60), 'NAIP measured')]
            if kind == 'dem': lines.append((0.0, (255, 160, 0), 'NASR end'))
            crop_png(S, end, pred, lines, os.path.join(OUT, f'regcheck_{year}_{fid}.png'),
                     f'NAIP {year} {fid}: along {end}->{F._OPP[end]} left->right, 0.15 m/px bilinear')
    if plots:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, axs = plt.subplots(3, 3, figsize=(15, 10))
        for ax, (fid, (s, p, pred, meas)) in zip(axs.ravel(), profs.items()):
            ax.plot(s, p, 'k-', lw=0.8); ax.axvline(pred, color='r', ls='--', label='predicted')
            if meas is not None: ax.axvline(meas, color='g', label='measured')
            ax.set_title(fid); ax.set_xlabel(f'along from {out["features"][fid]["end"]} (m)'); ax.legend(fontsize=7)
            if out['features'][fid]['kind'] != 'stripes': ax.set_xlim(pred - 15, pred + 15)
            else: ax.set_xlim(pred - 15, pred + 60)
        fig.suptitle(f'NAIP {year}: runway-aligned profiles (25th pct of width for bars, 75th for stripes)')
        fig.tight_layout(); fig.savefig(os.path.join(OUT, f'regcheck_profiles_{year}.png'), dpi=80); plt.close(fig)
    return out


def _phasecorr(A, B):
    """shift of A relative to B (rows, cols; + = A's content lies further down / right) by phase correlation of the
    gradient magnitudes, Hann window, parabolic sub-pixel peak. Returns (dr, dc, peak)."""
    def grad(I):
        gy, gx = np.gradient(I.astype(np.float32)); return np.hypot(gx, gy)
    n = A.shape[0]; w = np.hanning(n)[:, None] * np.hanning(n)[None]
    A = grad(A); B = grad(B); A = (A - A.mean()) * w; B = (B - B.mean()) * w
    X = np.fft.fft2(A) * np.conj(np.fft.fft2(B)); X /= np.abs(X) + 1e-9
    cc = np.fft.fftshift(np.real(np.fft.ifft2(X)))
    i, j = np.unravel_index(np.argmax(cc), cc.shape)
    if not (0 < i < n - 1 and 0 < j < n - 1): return None
    sub = lambda m1, z, p1: 0.5 * (m1 - p1) / (m1 - 2 * z + p1)
    return i + sub(cc[i - 1, j], cc[i, j], cc[i + 1, j]) - n // 2, j + sub(cc[i, j - 1], cc[i, j], cc[i, j + 1]) - n // 2, float(cc[i, j])


def interyear(a='2022', b='2024', n=128, step=64, max_off=150.0, min_peak=0.15):
    """2-D shift of NAIP `a` relative to `b` (dE, dN in metres; + = features appear further east / north in `a`).
    (1) a grid of n x n px patches (n * 0.6 m) whose centres lie within `max_off` m of either runway axis (flat ground:
    pavement and grass; hangars and other buildings, whose roofs lean differently in each flight, are farther away),
    (2) one patch centred on each runway end / displaced threshold. Patches with a correlation peak < `min_peak` are
    dropped. The two mosaics share the same 0.6 m grid, so pixel (r, c) is the same ground point in both."""
    Sa, Sb = NaipSampler(a), NaipSampler(b)
    seam_E = {}
    for y in (a, b):
        G = json.load(open(os.path.join(CACHE, f'naip_{y}_hwd_rgb.json')))
        c = [t['footprint_centre_utm'] for t in G['tiles']]
        seam_E[y] = (c[0][0] + c[1][0]) / 2 if len(c) == 2 else None
    def meas(r, c):
        r, c = int(round(r)), int(round(c)); h = n // 2
        A = Sa.gray[r - h:r + h, c - h:c + h]; B = Sb.gray[r - h:r + h, c - h:c + h]
        if A.shape != (n, n) or B.shape != (n, n): return None
        q = _phasecorr(A, B)
        if q is None or q[2] < min_peak: return None
        return dict(dE_m=float(q[1] * 0.6), dN_m=float(-q[0] * 0.6), peak=q[2])
    out = dict(method=f'phase correlation of gradient magnitude, {n}x{n} px patches ({n * 0.6:.0f} m), step {step} px, '
                      f'centres within {max_off:.0f} m of a runway axis; peak >= {min_peak}', pair=f'{a} minus {b}',
               seam_E_utm=seam_E, points={}, grid=[])
    for name, (la, lo) in _feature_points().items():
        E, N = F.ll_to_utm10(la, lo); c, r = Sb.en_to_px(E, N)
        m = meas(r, c)
        out['points'][name] = m
        if m: print(f'inter-year {a}-{b} at {name:8s}: dE {m["dE_m"]:+.2f} m, dN {m["dN_m"]:+.2f} m (peak {m["peak"]:.2f})')
        else: print(f'inter-year {a}-{b} at {name:8s}: no reliable peak')
    H, W = Sb.gray.shape
    for r in range(n // 2, H - n // 2, step):
        for c in range(n // 2, W - n // 2, step):
            E, N = Sb.px_to_en(c, r); lat, lon = F.utm10_to_ll(float(E), float(N)); x, z = F.ll_to_world(lat, lon)
            off = min(abs(F.rwy_along_across(e, x, z)[1]) if -50 < F.rwy_along_across(e, x, z)[0] < F.rwy_axis(e)['length'] + 50
                      else 1e9 for e in ('10R', '10L'))
            if off > max_off: continue
            m = meas(r, c)
            if m: out['grid'].append(dict(E=float(E), N=float(N), **m))
    g = out['grid']
    def stats(sel, out_m=2.0):
        """median / spread; patches with |d| > out_m (moving aircraft or vehicles, roofs) are counted, then dropped."""
        if not sel: return None
        dE = np.array([q['dE_m'] for q in sel]); dN = np.array([q['dN_m'] for q in sel]); d = np.hypot(dE, dN)
        k = d <= out_m
        return dict(n=int(k.sum()), n_outliers_gt_2m=int((~k).sum()), median_dE=float(np.median(dE[k])),
                    median_dN=float(np.median(dN[k])), std_dE=float(np.std(dE[k])), std_dN=float(np.std(dN[k])),
                    median_abs=float(np.median(d[k])), p90_abs=float(np.percentile(d[k], 90)), max_abs=float(d[k].max()))
    out['stats_all'] = stats(g)
    for y in (a, b):
        if seam_E[y]:
            out[f'stats_west_of_{y}_seam'] = stats([q for q in g if q['E'] < seam_E[y] - n * 0.3])
            out[f'stats_east_of_{y}_seam'] = stats([q for q in g if q['E'] > seam_E[y] + n * 0.3])
    for k, v in out.items():
        if k.startswith('stats') and v:
            print(f'inter-year {a}-{b} {k}: n {v["n"]} (+{v["n_outliers_gt_2m"]} outliers > 2 m), median ({v["median_dE"]:+.2f} E, {v["median_dN"]:+.2f} N) m, '
                  f'std ({v["std_dE"]:.2f}, {v["std_dN"]:.2f}), |d| median {v["median_abs"]:.2f} p90 {v["p90_abs"]:.2f} max {v["max_abs"]:.2f}')
    return out


def _feature_points():
    pts = {}
    for k, e in F.RWY_ENDS.items():
        pts[k + '_end'] = (e['lat'], e['lon'])
        if e['thrLat'] is not None: pts[k + '_thr'] = (e['thrLat'], e['thrLon'])
    return pts


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--years', default='2024,2022'); ap.add_argument('--no-plots', action='store_true')
    a = ap.parse_args()
    years = a.years.split(',')
    out = dict(about=__doc__.split('\n\n')[0],
               ac_reference=dict(doc='FAA AC 150/5340-1M Change 1 (12/23/2020), paragraphs 2.4, 2.5, 2.8, 2.9.1, 2.9.3',
                                 url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-1M-Chg-1-Airport-Markings.pdf',
                                 sha256='c404f3f363a21d4ba3b5e16922d5df3a0a0272622f94de8deea1106390d7ca15', fetched='2026-11-12',
                                 local_copy='refs/cache/local/faa/150-5340-1M-Chg-1-Airport-Markings.pdf (not committed)'),
               nasr='hwd3d/tools/common/hwd_frame.py RWY_ENDS (FAA NASR cycle 2026-10-29)',
               sign='resid = NAIP measured - predicted; along + = inward from the named end; across + = right of the '
                    'direction from the named end toward the opposite end',
               years={})
    for y in years:
        out['years'][y] = R = check_year(y, plots=not a.no_plots)
        prim = ['10R_end', '10R_thr', '28L_end', '28L_thr', '10L_end', '28R_stripes']
        W = np.array([[R['features'][f]['resid_world']['dE'], R['features'][f]['resid_world']['dN']] for f in prim])
        nrm = np.hypot(W[:, 0], W[:, 1])
        R['summary'] = dict(features=prim, note='one primary marking per runway end / displaced threshold',
                            mean_dE_m=float(W[:, 0].mean()), mean_dN_m=float(W[:, 1].mean()),
                            rms_norm_m=float(np.sqrt((nrm ** 2).mean())), max_norm_m=float(nrm.max()),
                            per_feature_norm_m={f: float(v) for f, v in zip(prim, nrm)})
        print(f'{y} summary NAIP - NASR/AC over {len(prim)} end/threshold markings: mean (dE {W[:, 0].mean():+.2f}, '
              f'dN {W[:, 1].mean():+.2f}) m, rms |r| {np.sqrt((nrm ** 2).mean()):.2f} m, max {nrm.max():.2f} m')
    if len(years) >= 2: out['interyear_phasecorr'] = interyear(years[1], years[0])
    # per-feature year difference
    if len(years) >= 2:
        y0, y1 = years[0], years[1]; dd = {}
        for fid in out['years'][y0]['features']:
            r0 = out['years'][y0]['features'][fid]; r1 = out['years'][y1]['features'][fid]
            if r0['resid_along_m'] is not None and r1['resid_along_m'] is not None:
                dd[fid] = dict(along_m=r1['resid_along_m'] - r0['resid_along_m'], across_m=r1['resid_across_m'] - r0['resid_across_m'])
        out['feature_diff_' + y1 + '_minus_' + y0] = dd
    p = os.path.join(CACHE, 'naip_reg_check.json')
    json.dump(out, open(p, 'w'), indent=1, default=lambda v: float(v))
    print('wrote', p)


if __name__ == '__main__':
    main()
