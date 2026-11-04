"""International Terminal (ITB) - adversarial fact-check of the ITB research (docs/research/buildings_itb.md
'## Verification', tools/buildings/spec_itb.json).

Independent re-checks, where possible with methods that differ from itb_naip_measure.py:

 A. FAA DOF re-read from the CURRENT daily file (refs/cache/lighting/DAILY_DOF_CSV.ZIP, re-fetched 2026-11-04,
    DOF.CSV dated 2026-11-02): the roof tops 06-035315/-316, the A-pier object 06-035352, the calibration poles.
 B. Relief model: the measurement uses k(x) = a + b x (east shift only). Here the same five pole picks are also fitted
    with a central (frame-camera) projection, shift = h (P - N) / (H - h), which has a north-south component. Both are
    carried through the planform (length, corners, centre) and the pier heights.
 C. Sun: NOAA solar-position formulas for 2024-05-20 (NAIP QQDATE) at the pole-shadow azimuth -> elevation (instead
    of the shadow length).
 D. NAIP pixels (refs/cache/naip/naip_2024_world_0.5m_bgr.npy, public domain): truss-line spacing by autocorrelation
    of the cross profiles; axis heading from a straight-line fit to the west facade base (bright ground -> dark band
    gradient); west-eave vs east-eave wander (height signal or plan curvature?); north-tip profile in / outside the
    roof width; Boarding Area A west band (facade + shadow, overhang-free); Boarding Area G north shadow band;
    A-pier pod rim bands.
 E. Source quotes: each key quote is searched in the re-fetched pages (refs/cache/buildings/itb/verify/src/*.html,
    fetched 2026-11-04; reference only, not redistributed) -> found / not found.
 F. --apply: writes the verdicts into tools/buildings/spec_itb.json (verification records; corrected values keep the
    old value and the reason). Re-run after tools/buildings/build_spec_itb.py, which regenerates the spec.

Outputs: tools/buildings/itb_verify.json (numbers only), QA crops out/buildings/itb/verify/qa_*.jpg (NAIP pixels, local).
usage : python3 tools/buildings/itb_verify.py [--apply]        (~5 s; no network: uses the caches)
"""
import csv, datetime, html, io, json, math, os, re, sys, zipfile
import numpy as np
import cv2
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

NAIP_NPY = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy')
NAIP_META = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')
DOF_ZIP = os.path.join(ROOT, 'refs', 'cache', 'lighting', 'DAILY_DOF_CSV.ZIP')
SRC = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'itb', 'verify', 'src')
MEAS = os.path.join(HERE, 'itb_naip_measurements.json')
SPEC = os.path.join(HERE, 'spec_itb.json')
OUT = os.path.join(HERE, 'itb_verify.json')
QA = os.path.join(ROOT, 'out', 'buildings', 'itb', 'verify')
FT = 0.3048
TODAY = '2026-11-04'
M = json.load(open(MEAS))

# ------------------------------------------------------------------------------------------------------- helpers
class Naip:
    def __init__(self):
        m = json.load(open(NAIP_META)); self.x0, self.z0, self.res = m['x0'], m['z0'], m['res']
        self.A = np.load(NAIP_NPY, mmap_mode='r')

    def frame(self, c, a, U, V):
        """rows = u (along a), cols = v (along n = (a_z, -a_x)); bilinear"""
        n = np.array([a[1], -a[0]]); uu, vv = np.meshgrid(U, V, indexing='ij')
        X, Z = c[0] + uu * a[0] + vv * n[0], c[1] + uu * a[1] + vv * n[1]
        col = ((X - self.x0) / self.res - 0.5).astype(np.float32); row = ((Z - self.z0) / self.res - 0.5).astype(np.float32)
        r0, c0 = int(row.min()) - 3, int(col.min()) - 3; r1, c1 = int(row.max()) + 4, int(col.max()) + 4
        sub = np.ascontiguousarray(self.A[r0:r1, c0:c1])
        return cv2.remap(sub, col - c0, row - r0, cv2.INTER_LINEAR)


def lum(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)


def hvec(h):                                    # heading (deg, clockwise from north) -> world (x east, z south)
    return np.array([math.sin(math.radians(h)), -math.cos(math.radians(h))])


def fwhm_band(p, j, lo, hi, dv):
    """edges of the dark band around the minimum j of profile p: the band level is the median of the contiguous run of
    samples darker than halfway between the minimum and the lighter surroundings (robust to mullions / single dark
    pixels); each edge is the sub-pixel crossing of the half level between that band level and the outer (lo) or
    inner (hi) level"""
    thr = 0.5 * (p[j] + min(lo, hi)); a = j
    while a > 0 and p[a - 1] < thr: a -= 1
    b = j
    while b < len(p) - 1 and p[b + 1] < thr: b += 1
    core = float(np.median(p[a:b + 1])); hl, hh = 0.5 * (lo + core), 0.5 * (hi + core)
    while a > 0 and p[a] < hl: a -= 1
    while b < len(p) - 1 and p[b] < hh: b += 1
    fa = (hl - p[a]) / (p[a + 1] - p[a] + 1e-6); fb = (hh - p[b - 1]) / (p[b] - p[b - 1] + 1e-6)
    return (a + fa) * dv, (b - 1 + fb) * dv


# ------------------------------------------------------------------------------------------------- A. DOF re-read
def dof_check():
    want = ['06-035315', '06-035316', '06-035352', '06-035353', '06-035354', '06-035355', '06-035356', '06-035357',
            '06-034823', '06-034825', '06-034826']
    out = {}
    with zipfile.ZipFile(DOF_ZIP) as zf:
        name = [n for n in zf.namelist() if n.upper().endswith('.CSV')][0]; dt = zf.getinfo(name).date_time
        for d in csv.DictReader(io.TextIOWrapper(zf.open(name), encoding='latin-1')):
            if d['OAS'] in want:
                x, z = GF.wgs84_to_world(float(d['LATDEC']), float(d['LONDEC']))
                out[d['OAS']] = dict(type=d['TYPE'].strip(), agl_ft=int(d['AGL']), amsl_ft=int(d['AMSL']), acc=d['ACCURACY'].strip(),
                                     verified=d['VERIFIED STATUS'], action=d['ACTION'].strip(), jdate=d['JDATE'].strip(),
                                     x=round(x, 2), z=round(z, 2), ground_amsl_ft=int(d['AMSL']) - int(d['AGL']))
    cmp = {}
    for o, d in out.items():
        old = M['dof_objects'].get(o)
        if old:
            cmp[o] = dict(same_agl=old['agl_ft'] == d['agl_ft'], same_amsl=old['amsl_ft'] == d['amsl_ft'], same_acc=old['acc'] == d['acc'],
                          moved_m=round(math.hypot(old['x'] - d['x'], old['z'] - d['z']), 2))
    return dict(file='DOF.CSV %04d-%02d-%02d (DAILY_DOF_CSV.ZIP re-fetched %s)' % (dt[0], dt[1], dt[2], TODAY), objects=out, vs_measurement=cmp,
                note='JDATE yyyyddd = date of the action; ACTION A = added (DOF_README). 2013289 = 2013-10-16.')


# ----------------------------------------------------------------------------------------------- B. relief models
def relief_models():
    P = M['relief']['poles']
    B = np.array([p['base'] for p in P]); S = np.array([p['shift'] for p in P]); H = np.array([p['agl_ft'] * FT for p in P])
    rf = least_squares(lambda q: ((B - q[:2]) * H[:, None] / q[2] - S).ravel(), [-2700, 440, 3600])
    J = rf.jac; cov = np.linalg.inv(J.T @ J) * (rf.fun ** 2).sum() / (rf.fun.size - 3); sd = np.sqrt(np.diag(cov))
    rx = least_squares(lambda q: np.r_[(B[:, 0] - q[0]) * H / q[1] - S[:, 0], -S[:, 1]], [-2700, 3600])
    d = np.degrees(np.arctan2(S[:, 0], -S[:, 1]))
    return dict(frame=dict(nadir_xz=[round(rf.x[0], 1), round(rf.x[1], 1)], nadir_sd=[round(sd[0], 1), round(sd[1], 1)],
                           H_minus_h=round(rf.x[2], 1), H_minus_h_sd=round(sd[2], 1), rms_m=round(float(np.sqrt((rf.fun ** 2).mean())), 3),
                           residuals_xz=np.round(rf.fun.reshape(-1, 2), 2).tolist()),
                x_only=dict(nadir_x=round(rx.x[0], 1), H_minus_h=round(rx.x[1], 1), rms_m=round(float(np.sqrt((rx.fun ** 2).mean())), 3)),
                pole_dir_vs_z=[[round(z, 1), round(a, 1), P[i]['pick']] for i, (z, a) in enumerate(zip(B[:, 1], d))],
                corr_dir_z=round(float(np.corrcoef(B[:, 1], d)[0, 1]), 3),
                note='frame model: one central projection fitted to the 2-D ring shifts of the five DOF poles; x_only: the '
                     'measurement\'s k(x) (no north-south component). Two of the five picks are manual (+-1 m), so the '
                     'north-south signal (dz up to 1.25 m) is near the pick noise.'), rf.x


# ------------------------------------------------------------------------------------------------------- C. sun
def sunpos(y, mo, d, hh, mm, lat, lon):
    """NOAA 'general solar position' (fractional-year series), UTC; ~0.1 deg"""
    doy = datetime.date(y, mo, d).timetuple().tm_yday; g = 2 * math.pi / 365 * (doy - 1 + (hh - 12) / 24 + mm / 1440)
    eot = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
           - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    ha = math.radians((hh * 60 + mm + eot + 4 * lon) / 4 - 180); la = math.radians(lat)
    z = math.acos(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha))
    az = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(dec) * math.cos(la))) + 180) % 360
    return 90 - math.degrees(z), az, math.degrees(dec)


def sun_check():
    lat, lon = GF.world_to_wgs84(-1245.0, 365.0)
    az_obs = M['sun']['picks'][0]['sun_az_deg']; best = None
    for t in range(18 * 60, 22 * 60):
        e, az, dec = sunpos(2024, 5, 20, t // 60, t % 60, lat, lon)
        if best is None or abs(az - az_obs) < abs(best[2] - az_obs): best = (t, e, az, dec)
    t, e, az, dec = best
    band = [sunpos(2024, 5, 20, (t + dt) // 60, (t + dt) % 60, lat, lon)[0] for dt in (-12, 12)]   # az +-4 deg ~ +-12 min
    return dict(date='2024-05-20', az_from_shadow=az_obs, utc='%02d:%02d' % (t // 60, t % 60), pdt='%02d:%02d' % (t // 60 - 7, t % 60),
                elev_deg=round(e, 2), elev_range_deg=[round(min(band), 2), round(e, 2)], declination_deg=round(dec, 2),
                cot_elev=round(1 / math.tan(math.radians(e)), 4), elev_from_shadow_length=M['sun']['picks'][0]['sun_elev_deg'])


# ------------------------------------------------------------------------------------------------- D. planform
def planform(fr):
    """relief-corrected outline from the measurement's imaged picks, under both relief models"""
    N = np.array(fr[:2]); D = fr[2]; Hfly = D + 47.0          # D = H - h_pole (poles ~47 m)
    a = np.array(M['roof_frame']['axis_xz']); c = np.array(M['roof_frame']['centre_imaged_xz']); n = np.array([a[1], -a[0]])
    F = M['roof_length']['tips']['fascia']; vw = M['true_planform']['west_eave_v_img']; W = M['roof_width']['img_median_m']
    t = M['roof_length']['tips']; h_pk = round(np.mean([M['dof_objects'][o]['agl_ft'] for o in ('06-035315', '06-035316')]) * FT, 2); h_tip = 34.9
    I = lambda u, v: c + u * a + v * n
    kx = lambda x: M['relief']['model']['a'] + M['relief']['model']['b'] * x
    models = {'frame': lambda P, h: N + (np.asarray(P) - N) * (Hfly - h) / Hfly,
              'x_only': lambda P, h: np.asarray(P) - np.array([kx(np.asarray(P)[0] - 16.0) * h, 0.0])}   # no magnification
    res = {}
    for nm, T in models.items():
        w1, w2 = T(I(-67, vw), h_pk), T(I(67, vw), h_pk)
        ax = (w2 - w1) / np.linalg.norm(w2 - w1); nx = np.array([ax[1], -ax[0]])
        uN = (T(I(F['N'], vw + W / 2), h_tip) - w1) @ ax; uS = (T(I(F['S'], vw + W / 2), h_tip) - w1) @ ax
        Wt = (T(I(67, vw + W), h_pk) - w1) @ nx
        cen = w1 + 0.5 * (uN + uS) * ax + 0.5 * Wt * nx
        cor = {'NW': w1 + uN * ax, 'NE': w1 + uN * ax + Wt * nx, 'SE': w1 + uS * ax + Wt * nx, 'SW': w1 + uS * ax}
        rel = lambda P: round(float((np.asarray(P) - cen) @ ax), 2)
        dof = {o: dict(u=rel((M['dof_objects'][o]['x'], M['dof_objects'][o]['z'])),
                       v_inside_west_eave=round(float((np.array([M['dof_objects'][o]['x'], M['dof_objects'][o]['z']]) - w1) @ nx), 2))
               for o in ('06-035315', '06-035316')}
        res[nm] = dict(heading_deg=round(math.degrees(math.atan2(ax[0], -ax[1])) % 360, 2), length_m=round(float(uS - uN), 2),
                       width_m=round(float(Wt), 2), centre_xz=[round(float(q), 2) for q in cen],
                       corners={k: [round(float(q), 2) for q in v] for k, v in cor.items()}, dof_roof_tops=dof,
                       lens_row_u=rel(T(I(np.median([q['u_c'] for q in M['lenses']]), -6), 40.0)),
                       glass_edges_u={k: rel(T(I(t[k], -6), h_tip)) for k in ('N_outer', 'N_inner', 'S_inner', 'S_outer')},
                       fascia_u={k: rel(T(I(F[k], -6), h_tip)) for k in ('N', 'S')})
    old = M['true_planform']['corners']
    res['measurement_corners_outline_length_m'] = round(math.dist(old['NW'], old['SW']), 2)
    res['measurement_length_m'] = M['true_planform']['length_m']
    d15, d16 = (np.array([M['dof_objects'][o]['x'], M['dof_objects'][o]['z']]) for o in ('06-035315', '06-035316'))
    res['dof_pair_along_axis_m'] = round(float(abs((d15 - d16) @ np.array(M['roof_frame']['axis_xz']))), 2)
    res['inner_column_span_published_m'] = round(380 * FT, 2)
    return res


# ------------------------------------------------------------------------------------------------- E. NAIP pixels
def naip_checks(Nm, fr, cot):
    a = np.array(M['roof_frame']['axis_xz']); c = np.array(M['roof_frame']['centre_imaged_xz']); out = {}
    # E1 truss-line spacing: autocorrelation peak (10-14.5 m) of each high-passed cross profile, |u| 30..104
    r = 0.1; U = np.arange(-104, 104, 0.5); V = np.arange(-36, 28, r); L = lum(Nm.frame(c, a, U, V)); sp = []
    for i, u in enumerate(U):
        if abs(u) < 30: continue
        p = L[i] - cv2.GaussianBlur(L[i].reshape(1, -1), (0, 0), 40).ravel(); p -= p.mean()
        ac = np.correlate(p, p, 'full')[len(p) - 1:]; ac /= ac[0]; j = int(10 / r) + int(np.argmax(ac[int(10 / r):int(14.5 / r)]))
        if ac[j] < 0.25: continue
        y0, y1, y2 = ac[j - 1:j + 2]; sp.append((j + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)) * r)
    s = float(np.median(sp)); Hfly = fr[2] + 47.0
    out['truss_spacing'] = dict(rows=len(sp), imaged_m=round(s, 3), iqr=[round(float(np.percentile(sp, 25)), 3), round(float(np.percentile(sp, 75)), 3)],
                                true_m=round(s * (1 - 38.0 / Hfly), 3), true_ft=round(s * (1 - 38.0 / Hfly) / FT, 2))
    # E2 axis: straight-line fit to the west facade base (ground level: no relief), strongest bright->dark step
    U = np.arange(-118, 118, 0.5); V = np.arange(-52, -34, r)
    G = np.diff(cv2.GaussianBlur(lum(Nm.frame(c, a, U, V)), (0, 0), 1.5), axis=1)
    pts = np.array([(u, V[int(np.argmin(G[i]))] + r / 2) for i, u in enumerate(U) if abs(u) >= 25 and G[i].min() < -8])
    uu, vv = pts[:, 0], pts[:, 1]
    for _ in range(3):
        cf = np.polyfit(uu, vv, 1); res = vv - np.polyval(cf, uu); m = np.abs(res) < max(0.5, 2.5 * res.std()); uu, vv = uu[m], vv[m]
    cf = np.polyfit(uu, vv, 1); sd = float((vv - np.polyval(cf, uu)).std())
    hd0 = math.degrees(math.atan2(a[0], -a[1])) % 360
    out['axis'] = dict(points=int(len(uu)), of=int(len(pts)), facade_base_v=round(float(cf[1]), 2), slope=round(float(cf[0]), 5), sd_m=round(sd, 2),
                       heading_deg=round(hd0 - math.degrees(math.atan(cf[0])), 2), grid_t_plus_135=round(27.83 + 135, 2))
    # E3 east eave vs west eave wander (binned 10 m)
    V = np.arange(16, 34, r); U = np.arange(-120, 120, 0.5)
    G = np.diff(cv2.GaussianBlur(lum(Nm.frame(c, a, U, V)), (0, 0), 1.2), axis=1)
    E = np.array([(u, V[int(np.argmin(G[i]))] + r / 2, G[i].min()) for i, u in enumerate(U)]); E = E[E[:, 2] < -3]
    Wp = np.array([(p['u'], p['v_eave']) for p in M['eave_profile']['points']])
    def binned(P):
        return {b: float(np.median(P[(P[:, 0] >= b - 5) & (P[:, 0] < b + 5), 1])) for b in range(-115, 116, 10)
                if ((P[:, 0] >= b - 5) & (P[:, 0] < b + 5)).sum() >= 4}
    we, ee = binned(Wp), binned(E)
    rows = [dict(u=b, west=round(we[b], 2), east=round(ee[b], 2), width=round(ee[b] - we[b], 2)) for b in sorted(set(we) & set(ee))]
    good = [q for q in rows if 64 < q['width'] < 68]
    nrow = {q['u']: q for q in good}
    out['eaves'] = dict(rows=rows, width_median=round(float(np.median([q['width'] for q in good])), 2),
                        north_tip_to_hump=dict(west=round(nrow[-55]['west'] - nrow[-115]['west'], 2), east=round(nrow[-55]['east'] - nrow[-115]['east'], 2)) if -55 in nrow and -115 in nrow else None,
                        note='rows with an implausible width (other roof features picked) are excluded from the median')
    # E4 north tip: along-axis profile inside / outside the roof width
    U = np.arange(-134, -120, 0.25); V = np.arange(-40, 50, 0.25); L = lum(Nm.frame(c, a, U, V))
    def tipband(v0, v1):
        p = np.median(L[:, np.searchsorted(V, v0):np.searchsorted(V, v1)], axis=1)[::-1]   # from the roof outward
        j = int(np.argmin(p)); a_, b_ = fwhm_band(p, j, float(np.median(p[:8])), float(np.median(p[-8:])), 0.25)
        return dict(min_L=round(float(p[j]), 1), band_from_roof_end_m=round(b_ - a_, 2))
    out['north_tip'] = dict(inside_roof=tipband(-28, 20), outside_roof=tipband(28, 48),
                            note='inside the imaged roof width the dark band beyond the fascia is wider: the hall casts its shadow there; the band continues outside the roof (a joint of the lower structure), so it is not roof')
    # E5 Boarding Area A: west band (oblique WNW facade + its shadow) - overhang-free
    out['pier_A'] = pier_A(Nm, fr, cot)
    out['pier_G'] = pier_G(Nm, fr, cot)
    out['pier_widths'] = pier_widths(Nm)
    return out


def relief_per_m(P, normal, fr, kx):
    """relief shift per metre of height along a unit normal, for both models"""
    N = np.array(fr[:2]); Pn = np.asarray(P)
    return dict(frame=float((Pn - N) @ normal / fr[2]), x_only=float(kx(Pn[0]) * normal[0]))


def pier_A(Nm, fr, cot):
    h = 208.0; a = hvec(h); c = np.array([-1232.5, 661.8]); n = np.array([a[1], -a[0]]); r = 0.05
    U = np.arange(-160, 160, 0.25); V = np.arange(-26, -6, r); L = lum(Nm.frame(c, a, U, V))
    kx = lambda x: M['relief']['model']['a'] + M['relief']['model']['b'] * x
    nW = -n; s = hvec((M['sun']['picks'][0]['sun_az_deg'] + 180) % 360); sh = float(s @ nW) * cot
    W = []
    for u0 in np.arange(-150, 150, 4.0):
        p = np.median(L[np.searchsorted(U, u0):np.searchsorted(U, u0 + 4)], axis=0)
        if (p < 120).sum() * r < 4: continue
        ap = float(np.median(p[:np.searchsorted(V, -23.5)])); rf = float(np.median(p[np.searchsorted(V, -10.5):np.searchsorted(V, -8)]))
        if ap < 150: continue                                    # a gate room / bridge stands west of the band
        j = int(np.argmin(np.where((V > -21) & (V < -12), p, 1e9))); a_, b_ = fwhm_band(p, j, ap, rf, r); W.append((u0, b_ - a_))
    W = np.array(W); w = float(np.median(W[:, 1]))
    rp = relief_per_m(c + (-12) * n, nW * -1, fr, kx)          # roof leans east = away from the west wall
    hx, hf = w / (rp['x_only'] + sh), w / (rp['frame'] + sh)
    # pod rim bands (curved WNW edges of the raised D-shaped pods): width along -v at each pod's apex region
    V2 = np.arange(-10, 4, r); L2 = cv2.GaussianBlur(lum(Nm.frame(c, a, U, V2)), (0, 0), 2); pods = []
    for lo_, hi_ in ((-101, -89), (-13, 1), (71, 85)):
        ws = []
        for u0 in np.arange(lo_, hi_ + 0.1, 2.0):
            i = np.searchsorted(U, u0); p = np.median(L2[i - 4:i + 4], axis=0); j = int(np.argmin(p))
            if p[j] > 150 or j < 40 or j > len(p) - 60: continue
            a_, b_ = fwhm_band(p, j, float(np.median(p[j - 40:j - 20])), float(np.median(p[j + 30:j + 60])), r); ws.append(b_ - a_)
        pods.append(round(float(np.median(ws)), 2) if ws else None)
    rpp = relief_per_m(c + (-4) * n, n, fr, kx)
    dpod = [[round(wp / (rpp[m] + sh), 1) for m in ('frame', 'x_only')] + [round(wp / rpp['x_only'], 1)] for wp in pods if wp]
    return dict(axis_heading_deg=h, stations=int(len(W)), band_m=round(w, 2), band_iqr=[round(float(np.percentile(W[:, 1], 25)), 2), round(float(np.percentile(W[:, 1], 75)), 2)],
                shadow_per_m=round(sh, 3), relief_per_m={k: round(v, 3) for k, v in rp.items()},
                h_roof_m=dict(x_only=round(hx, 1), frame=round(hf, 1)),
                pod_rim_band_m=pods, pod_dh_m_frame_xonly_noshadow=dpod,
                note='band = imaged eave -> outer edge of the shadow on the apron = (relief + shadow) * h; a roof overhang moves both edges equally and cancels')


def pier_widths(Nm):
    """imaged main-roof widths: A = west eave (dark band -> roof rise) to the east edge (roof -> outside fall);
    G = between the two bright parapet lines (L > 238). Eaves at one height -> the width is relief-free (x 0.995)."""
    out = {}
    a = hvec(208.0); c = np.array([-1232.5, 661.8]); U = np.arange(-150, 150, 0.25); V = np.arange(-16, 34, 0.1)
    G = np.diff(cv2.GaussianBlur(lum(Nm.frame(c, a, U, V)), (0, 0), 1.0), axis=1); w = []
    for u0 in np.arange(-145, 145, 5.0):
        g = np.median(G[np.searchsorted(U, u0):np.searchsorted(U, u0 + 5)], axis=0)
        jw = np.searchsorted(V, -14) + int(np.argmax(g[np.searchsorted(V, -14):np.searchsorted(V, -9)]))
        je = np.searchsorted(V, 22) + int(np.argmin(g[np.searchsorted(V, 22):np.searchsorted(V, 32)])); w.append(V[je] - V[jw])
    out['A'] = dict(stations=len(w), width_img_m=round(float(np.median(w)), 2), iqr=[round(float(np.percentile(w, 25)), 2), round(float(np.percentile(w, 75)), 2)],
                    note='upper quartile = gate rooms / bridge heads on the east side')
    a = hvec(297.75); c = np.array([-1408.5, 105.1]); V = np.arange(-26, 24, 0.1); L = lum(Nm.frame(c, a, U, V)); w = []
    for u0 in np.arange(-145, 145, 5.0):
        pk = np.where(np.median(L[np.searchsorted(U, u0):np.searchsorted(U, u0 + 5)], axis=0) > 238)[0]
        if len(pk) >= 2 and V[pk[-1]] - V[pk[0]] > 30: w.append(V[pk[-1]] - V[pk[0]])
    out['G'] = dict(stations=len(w), width_img_m=round(float(np.median(w)), 2), iqr=[round(float(np.percentile(w, 25)), 2), round(float(np.percentile(w, 75)), 2)],
                    note='parapet-line centres; outer edges ~0.5-1 m more')
    return out


def pier_G(Nm, fr, cot):
    h = 297.75; a = hvec(h); c = np.array([-1408.5, 105.1]); n = np.array([a[1], -a[0]]); r = 0.05
    U = np.arange(-170, 170, 0.25); V = np.arange(-30, -15, r); L = lum(Nm.frame(c, a, U, V))
    kx = lambda x: M['relief']['model']['a'] + M['relief']['model']['b'] * x
    nN = -n; s = hvec((M['sun']['picks'][0]['sun_az_deg'] + 180) % 360); sh = float(s @ nN) * cot; rows = []
    for u0 in np.arange(-150, 150, 5.0):
        p = np.median(L[np.searchsorted(U, u0):np.searchsorted(U, u0 + 5)], axis=0)
        j = int(np.argmin(np.where((V > -25) & (V < -19), p, 1e9)))
        ap = float(np.median(p[(V > -29) & (V < -25.5)])); rf = float(p[(V > -21.5) & (V < -18.5)].max())
        if p[j] > 115 or ap < 170: continue                     # bridges / gate rooms
        a_, b_ = fwhm_band(p, j, ap, rf, r)
        P = c + u0 * a + (-21) * n; rp = relief_per_m(P, nN, fr, kx)
        rows.append((u0, b_ - a_, rp['x_only'], rp['frame']))
    R = np.array(rows); w = R[:, 1]; hx = w / (sh - R[:, 2]); den_f = sh - R[:, 3]
    return dict(axis_heading_deg=h, stations=int(len(R)), shadow_band_m=round(float(np.median(w)), 2),
                band_iqr=[round(float(np.percentile(w, 25)), 2), round(float(np.percentile(w, 75)), 2)], shadow_per_m=round(sh, 3),
                relief_per_m_x_only=[round(float(R[:, 2].min()), 3), round(float(R[:, 2].max()), 3)],
                relief_per_m_frame=[round(float(R[:, 3].min()), 3), round(float(R[:, 3].max()), 3)],
                h_roof_m_x_only=dict(median=round(float(np.median(hx)), 1), iqr=[round(float(np.percentile(hx, 25)), 1), round(float(np.percentile(hx, 75)), 1)]),
                frame_visible_shadow_per_m=round(float(np.median(den_f)), 3),
                note='visible shadow = (shadow - relief) * h along the north normal (the roof leans over its own shadow); under the single-frame model the '
                     'roof would cover almost all of it (h ~ 45 m implied, impossible for a three-story pier) -> G is not in the poles\' frame, or the relief there has no strong '
                     'northward component. The sunlit SSW facade could not be separated from the apron, so the k-free sum method of the research note was not reproduced.')


# --------------------------------------------------------------------------------------------- E. source quotes
QUOTES = [
    ('seaonc', 'five sets of steel balanced double cantilever trusses with a central trussed span'),
    ('seaonc', 'supported on 20 cantilevered columns rising from the third floor departures level'),
    ('seaonc', 'up to 29 ft deep, spans 380 ft at its center and 160 ft at each end cantilever with an overall length of 860 ft'),
    ('seaonc', '705 ft long, 210 ft wide, and up to 83 ft high'),
    ('seaonc', '26 new gates'),
    ('seaonc', '172,000 sq. ft. of exposed trussed steel roof'),
    ('seaonc', 'disassembled into some 35 major pieces'),
    ('seaonc', 'The Herrick Corporation'),
    ('seaonc', '267 single concave friction pendulum'),
    ('seaonc', 'Designed and constructed from 1994 to 2000'),
    ('som', 'Building Height: 144 feet'), ('som', 'Number of Stories: 5'), ('som', 'Building Gross Area: 1,800,000 square feet'),
    ('som', 'Site Area: 1,000,000 square feet'), ('som', 'Design Finish Year 1995'),
    ('som', 'A series of double-cantilevered trusses linked by bowstring trusses support the roof'),
    ('smith_emery', '860’ long “winglike” roof'), ('smith_emery', 'soaring 60 to 90’ above the floor'),
    ('smith_emery', 'three-chord “football” shaped trusses'),
    ('sfgate2000', '100-foot-high terminal roof'), ('sfgate2000', 'The roof has a 380-foot span'), ('sfgate2000', 'The ticket lobby is 700 feet long'),
    ('sfgate2000', 'Level 1 is devoted to services and baggage; level 2 to arrivals; level 3 to departures'), ('sfgate2000', '55 feet high'),
    ('enclos', 'Height: 144 ft'), ('enclos', 'San Francisco Department of Public Health'), ('enclos', 'some 267 of them'),
    ('tutor_itb', '382,000 square feet of metal and glass'), ('tutor_itb', 'COMPLETION 2001'), ('tutor_itb', '24 international gates'),
    ('tutor_itb', 'five-level steel structure'),
    ('tutor_bag', '380,000-square-foot, three-story'), ('tutor_bag', 'ARCHITECT Robin Chiang & Company'), ('tutor_bag', 'COMPLETION 1999'),
    ('tutor_bag', 'twelve 747-400'), ('tutor_bag', 'metallic finished composite aluminum panels'),
    ('ags_baa', '23 passenger boarding bridges (PBBs) at Gates A1 through A15'), ('ags_baa', 'Gate A6 was retrofitted to allow for a three PBB'),
    ('airportworld25', 'On Sunday, December 10, 2000, SFO held a ribbon-cutting ceremony'), ('airportworld25', 'Breaking ground in October 1995'),
    ('airportworld25', 'On January 16, 2024, the San Francisco Airport Commission approved a resolution to rename'),
    ('airportworld25', 'expected to be completed in mid-2026'),
    ('webcor_roof', '1,400 kW'), ('webcor_ceremony', 'June 27, 2024'), ('webcor_ceremony', '$75'),
    ('ftf_roof', 'Scaffolds reached 90 feet high'),
    ('wiki_sfo', 'Gate A11 has three [[Jet bridge|jetways]]'), ('wiki_sfo', 'Gerson/Overstreet Architects and built by [[Hensel Phelps Construction]]'),
    ('wiki_sfo', 'Robin Chiang & Company, Robert B. Wong Architects'),
]
SOURCE_STATUS = {'msc2000': 'curl 403 (Cloudflare), WebFetch 403, web.archive.org connection reset (snapshot 2024-09-04 exists)',
                 'ai_roof': 'curl 403'}


def page_text(sid):
    fn = os.path.join(SRC, sid + '.html')
    if not os.path.exists(fn): return None
    s = open(fn, encoding='utf-8', errors='replace').read()
    if sid != 'wiki_sfo':
        s = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', s); s = re.sub(r'(?s)<[^>]+>', ' ', s); s = html.unescape(s)
    return re.sub(r'\s+', ' ', s)


def quote_check():
    T = {}; out = []
    for sid, q in QUOTES:
        if sid not in T: T[sid] = page_text(sid)
        out.append(dict(src=sid, quote=q, found=bool(T[sid]) and q in T[sid]))
    return dict(fetched=TODAY, cache='refs/cache/buildings/itb/verify/src/', quotes=out, unreachable=SOURCE_STATUS)


def qa_crops(Nm):
    """local QA crops (NAIP pixels, public domain; out/ is not committed): the piers in their grid-aligned frames, the
    roof tips and the centre-section lenses in the roof frame. Ticks: metres in the frame (u along, v across)."""
    def ticks(img, U, V, step_u, step_v, transpose):
        for uu in np.arange(np.ceil(U[0] / step_u) * step_u, U[-1], step_u):
            k = int(round((uu - U[0]) / (U[1] - U[0])))
            if transpose: cv2.line(img, (k, 0), (k, 10), (0, 0, 255), 2); cv2.putText(img, '%d' % uu, (k + 2, 22), 0, 0.5, (0, 0, 255), 1)
            else: cv2.line(img, (0, k), (10, k), (0, 0, 255), 2); cv2.putText(img, '%d' % uu, (12, k + 5), 0, 0.5, (0, 0, 255), 1)
        for vv in np.arange(np.ceil(V[0] / step_v) * step_v, V[-1], step_v):
            k = int(round((vv - V[0]) / (V[1] - V[0])))
            if transpose: cv2.line(img, (0, k), (12, k), (0, 0, 255), 2); cv2.putText(img, '%d' % vv, (14, k + 5), 0, 0.5, (0, 0, 255), 1)
            else: cv2.line(img, (k, 0), (k, 10), (255, 255, 255), 1); cv2.putText(img, '%d' % vv, (k + 2, 22), 0, 0.45, (255, 255, 255), 1)
        return img
    for nm, h, c in (('pierA', 208.0, (-1232.5, 661.8)), ('pierG', 297.75, (-1408.5, 105.1))):
        U = np.arange(-170, 170, 0.4); V = np.arange(-45, 45, 0.2)
        img = np.ascontiguousarray(Nm.frame(np.array(c), hvec(h), U, V).transpose(1, 0, 2))
        cv2.imwrite(os.path.join(QA, 'qa_%s_frame.jpg' % nm), ticks(img, U, V, 20, 10, True), [cv2.IMWRITE_JPEG_QUALITY, 85])
    a = np.array(M['roof_frame']['axis_xz']); c = np.array(M['roof_frame']['centre_imaged_xz'])
    for nm, (u0, u1) in (('N', (-150, -95)), ('S', (95, 150))):
        U = np.arange(u0, u1, 0.1); V = np.arange(-75, 45, 0.1); img = Nm.frame(c, a, U, V)
        cv2.imwrite(os.path.join(QA, 'qa_tip_%s.jpg' % nm), ticks(img, U, V, 5, 10, False), [cv2.IMWRITE_JPEG_QUALITY, 85])
    U = np.arange(-32, 32, 0.1); V = np.arange(-45, 30, 0.1)
    cv2.imwrite(os.path.join(QA, 'qa_lenses.jpg'), ticks(Nm.frame(c, a, U, V), U, V, 5, 10, False), [cv2.IMWRITE_JPEG_QUALITY, 85])


# ------------------------------------------------------------------------------------------------------- main
def main():
    os.makedirs(QA, exist_ok=True)
    rel, fr = relief_models(); sun = sun_check(); Nm = Naip()
    res = dict(generated_by='tools/buildings/itb_verify.py', date=TODAY, dof=dof_check(), relief=rel, sun=sun, planform=planform(fr),
               naip=naip_checks(Nm, fr, sun['cot_elev']), sources=quote_check())
    qa_crops(Nm)
    photos = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'itb', 'verify', 'commons_photos.json')
    if os.path.exists(photos):
        q = json.load(open(photos))['query']['pages']; spec = {p['title']: p for p in json.load(open(SPEC))['photos']}
        chk = []
        for pg in q.values():
            m = (pg.get('imageinfo') or [{}])[0].get('extmetadata', {}); lic = m.get('LicenseShortName', {}).get('value', '')
            art = re.sub('<[^>]+>', '', m.get('Artist', {}).get('value', '')).strip(); sp = spec.get(pg['title'], {})
            chk.append(dict(title=pg['title'], licence=lic, author=art[:60], spec_licence=sp.get('licence'), licence_match=lic == sp.get('licence'),
                            author_match=(not art and not sp.get('author')) or (bool(sp.get('author')) and sp['author'][:20] in art)))
        res['photos'] = dict(api='Wikimedia Commons API imageinfo/extmetadata, %s' % TODAY, n=len(chk),
                             all_licences_match=all(c['licence_match'] for c in chk), all_authors_match=all(c['author_match'] for c in chk), rows=chk)
    res = json.loads(json.dumps(res, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))   # numpy scalars
    json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({k: res[k] for k in ('relief', 'sun')}, indent=1))
    print(json.dumps(res['planform'], indent=1)); print(json.dumps(res['naip'], indent=1))
    print('quotes not found:', [q for q in res['sources']['quotes'] if not q['found']])
    if 'photos' in res: print('photos', res['photos']['n'], res['photos']['all_licences_match'], res['photos']['all_authors_match'])
    return res


# ------------------------------------------------------------------------------------- F. write into the spec
def apply(V):
    S = json.load(open(SPEC)); items = {it['id']: it for it in S['items']}
    P, NA, PL = V['planform'], V['naip'], V['planform']['frame']

    def ver(iid, verdict, evidence, status=None, conf=None, correct=None, add_src=(), **extra):
        it = items[iid]
        if correct is not None and 'corrected' not in it:
            it['corrected'] = dict(old_value=it['value'], date=TODAY, reason=correct[1]); it['value'] = correct[0]
        elif correct is not None:
            it['value'] = correct[0]
        if status: it['status'] = status
        if conf: it['confidence'] = conf
        for s in add_src:
            if s not in it['sources']: it['sources'].append(s)
        it.update(extra); it['verification'] = dict(date=TODAY, verdict=verdict, evidence=evidence)

    sea = 'SEAONC page read first-hand on %s (refs/cache/buildings/itb/verify/src/seaonc.html)' % TODAY
    ver('itb.name', 'CONFIRMED', 'Airport World: "On January 16, 2024, the San Francisco Airport Commission approved a resolution to rename the International Terminal ... for the late Senator ... Dianne Feinstein"')
    ver('itb.opened', 'CONFIRMED', 'Airport World: "On Sunday, December 10, 2000, SFO held a ribbon-cutting ceremony"; ground broken October 1995; SEAONC "Designed and constructed from 1994 to 2000"; Tutor Perini lists COMPLETION 2001 (contract close-out, not the opening)')
    ver('itb.architect', 'CONFIRMED', 'SOM page; SEAONC lists Craig W. Hartman, Keith Boswell, Michael Duncan (SOM), Del Campo & Maru, Michael Willis & Associates (JV)')
    ver('itb.structure_engineer', 'CONFIRMED', 'SEAONC: structural engineering firms SOM, OLMM, Faye Bernstein & Associates; engineers Navinchandra R. Amin, Raj Desai', add_src=['seaonc'])
    ver('itb.contractor', 'CONFIRMED', 'SOM collaborators; SEAONC main contractor "Tutor Saliba, Perini Corporation, Buckley & Co. (JV)"', add_src=['seaonc'])
    ver('itb.steel', 'CONFIRMED (now first-hand)', sea + ': The Herrick Corporation listed; "Roof trusses were fully assembled at the Mare Island fabrication shop and then disassembled into some 35 major pieces ... shipped directly to the site on barges. Once completed, trusses were jacked into position and pinned in place."',
        status='verified', conf='high', add_src=['seaonc'])
    ver('itb.gross_area', 'CONFIRMED', 'SOM "Building Gross Area: 1,800,000 square feet"; Tutor Perini "1,800,000-square-foot"; SEAONC "1.8 million sq. ft. of framed steel area"')
    ver('itb.site_area', 'CONFIRMED', 'SOM "Site Area: 1,000,000 square feet"')
    ver('itb.stories', 'CONFIRMED', 'SOM "Number of Stories: 5"; SFGate "Five stories high"; Tutor Perini "five-level"; SEAONC "five-story structure"')
    ver('itb.levels', 'CONFIRMED', 'SFGate: "Level 1 is devoted to services and baggage; level 2 to arrivals; level 3 to departures, ticketing and security checks; levels 4 and 5 to airline offices and lounges." SEAONC: columns "rising from the third floor departures level"')
    ver('itb.height_som', 'CONFIRMED as published; datum still unknown (conflict kept)', 'SOM "Building Height: 144 feet". Enclos repeats 144 ft but its spec block also lists the owner as "San Francisco Department of Public Health" (a data-entry error): Enclos is not an independent source for the height. DOF 131/132 ft AGL = 139/140 ft AMSL - 144 ft matches neither.')
    ver('itb.isolators', 'CONFIRMED', 'Enclos "some 267"; SEAONC "267 single concave friction pendulum \'cast steel\' isolation bearings ... allowing up to 20 inches of lateral displacement"', add_src=['seaonc'])
    ver('itb.gates_2000', 'CONFLICT (now first-hand)', sea + ': "26 new gates"; Tutor Perini ITB page: "24 international gates". Today: A1-A15 + G1-G14 (Wikipedia).',
        status='conflict', conf='medium', conflicting_values=[dict(value=24, unit='count', src='tutor_itb', note='"Some of the features include 24 international gates"')])
    ver('itb.cladding', 'CONFIRMED', 'Tutor Perini: "382,000 square feet of metal and glass"')
    ver('roof.form', 'CONFIRMED (first-hand)', sea + ': "five sets of steel balanced double cantilever trusses with a central trussed span linked together creating a continuous wing-like form"; Smith-Emery "three-chord \'football\' shaped trusses"; "The middle sections were erected first, followed by the outside cantilever and the inside cantilever trusses."')
    ver('roof.length_pub', 'CONFIRMED as published; CONFLICT with NAIP kept', sea + ': "overall length of 860 ft"; Smith-Emery "860\' long". NAIP gives %.1f-%.1f m (frame / x-only relief model) = %.0f-%.0f ft, i.e. 7-9 m short. SEAONC also gives "172,000 sq. ft. of exposed trussed steel roof" (15,980 m2; NAIP outline %.0f m2).'
        % (PL['length_m'], P['x_only']['length_m'], PL['length_m'] / FT, P['x_only']['length_m'] / FT, PL['length_m'] * PL['width_m']))
    ver('roof.span_centre', 'CONFIRMED + independent support', sea + ' ("spans 380 ft at its center"); SFGate "380-foot span". NEW: the two DOF roof tops lie %.1f m apart along the axis (%.0f ft) at u = %+.1f / %+.1f m from the relief-corrected roof centre - i.e. over the inferred inner column lines (+-190 ft = +-57.9 m).'
        % (P['dof_pair_along_axis_m'], P['dof_pair_along_axis_m'] / FT, PL['dof_roof_tops']['06-035315']['u'], PL['dof_roof_tops']['06-035316']['u']))
    ver('roof.cantilever_end', 'CONFIRMED (now first-hand); geometry conflict with NAIP', sea + ': "160 ft at each end cantilever". With the inner columns at the DOF tops and the 80-ft N/S column bay, NAIP puts the fascia %.1f m (%.0f ft) beyond the outer column line, not 160 ft.'
        % (0.5 * PL['length_m'] - 82.3, (0.5 * PL['length_m'] - 82.3) / FT), status='verified', conf='high')
    ver('roof.truss_len', 'STILL SNIPPET-ONLY', 'AISC PDF: ' + SOURCE_STATUS['msc2000'])
    ver('roof.centre_section', 'STILL SNIPPET-ONLY', 'AISC PDF: ' + SOURCE_STATUS['msc2000'])
    ver('roof.truss_depth', 'CONFIRMED (now first-hand)', sea + ': "up to 29 ft deep"', status='verified')
    ver('roof.columns', 'CONFIRMED (now first-hand)', sea + ': "supported on 20 cantilevered columns rising from the third floor departures level"; trusses "sitting on spherical ball-joints atop the cantilevered concrete filled steel box columns"', status='verified', conf='high')
    ver('roof.height_above_floor', 'CONFIRMED', 'Smith-Emery: "soaring 60 to 90\' above the floor of a cavernous ticketing hall" (top or underside not stated)')
    ver('hall.size_snippet', 'CONFIRMED (now first-hand)', sea + ': "The main Terminal\'s glass-enclosed \'great hall\' - 705 ft long, 210 ft wide, and up to 83 ft high". 83 ft is the interior hall height, not the roof height above ground.', status='verified', conf='high')
    ver('hall.lobby_len', 'CONFIRMED', 'SFGate: "The ticket lobby is 700 feet long."')
    ver('hall.bamboo', 'CONFIRMED', 'SFGate: "A stand of living giant bamboo stretches 55 feet high between Levels 2 and 3."')
    ver('roof.rhythm_inf', 'PLAUSIBLE (inner span supported; end segment conflicts with NAIP)', 'the DOF roof-top pair marks +-%.1f m (= 190 ft) from the centre, as the inferred inner column lines; but the NAIP fascia lies %.1f m beyond the inferred outer column line (+-82.3 m) instead of 160 ft (48.8 m): either the 860-ft total or the 80-ft bay does not apply to the visible roof.'
        % (0.5 * P['dof_pair_along_axis_m'], 0.5 * PL['length_m'] - 82.3))
    ver('roof.col_positions_inf', 'PLAUSIBLE (inner lines supported by the DOF pair)', 'DOF 06-035315/-316 at u = %+.1f / %+.1f m from the relief-corrected centre' % (PL['dof_roof_tops']['06-035315']['u'], PL['dof_roof_tops']['06-035316']['u']))
    ver('roof.axis_obs', 'CONFIRMED', 'independent straight-line fit to the west facade base (ground level, no relief): %d of %d rows, sd %.2f m, heading %.2f deg. 162.83 = the airport grid t-axis (27.83) + 135 deg; the piers lie on the grid axes too (A 208.0, G 297.75 by NAIP edge alignment).'
        % (NA['axis']['points'], NA['axis']['of'], NA['axis']['sd_m'], NA['axis']['heading_deg']))
    ver('roof.centre_obs', 'PLAUSIBLE', 'frame-camera relief model: %s (%.2f m from the stated centre); within the +-1.5 m stated' % (PL['centre_xz'], math.dist(PL['centre_xz'], items['roof.centre_obs']['value'])),
        alt_frame_model=PL['centre_xz'])
    ver('roof.corners_obs', 'CORRECTED (internal inconsistency)', 'the stated corners span %.2f m along the axis (no magnification removed: the east-only k(x) shift), while roof.length_obs (%.2f m) removes it. New corners from one central-projection relief model fitted to the same five pole picks (nadir %s, H-h %.0f m): outline %.2f x %.2f m, consistent with the length.'
        % (P['measurement_corners_outline_length_m'], P['measurement_length_m'], V['relief']['frame']['nadir_xz'], V['relief']['frame']['H_minus_h'], PL['length_m'], PL['width_m']),
        correct=(PL['corners'], 'stated corners were relief-corrected east-only (outline %.2f m long) and contradict roof.length_obs; replaced by frame-model corners (outline %.2f m)' % (P['measurement_corners_outline_length_m'], PL['length_m'])),
        alt_x_only_model=P['x_only']['corners'])
    ver('roof.length_obs', 'PLAUSIBLE; range widened', 're-derived: %.2f m (central projection, the pole ring shifts rotate with z: corr %.2f, rms 0.21 vs 0.54 m) or %.2f m (east-only relief, no magnification). The north-south relief component is not pinned (two of five picks manual; Boarding Area G contradicts a single frame). Still 7-9 m short of 860 ft.'
        % (PL['length_m'], V['relief']['corr_dir_z'], P['x_only']['length_m']), range_m=[round(min(PL['length_m'], P['measurement_length_m']) - 0.1, 1), round(P['x_only']['length_m'] + 0.1, 1)])
    ver('roof.width_obs', 'CONFIRMED', 'east eave re-measured: imaged width %.2f m (median of the 10-m bins), constant along the length; true %.2f m (frame model)' % (NA['eaves']['width_median'], PL['width_m']))
    ver('roof.truss_lines_obs', 'CONFIRMED', 'five straight glazed lines visible on the NAIP crops; five lens skylights on them')
    ver('roof.truss_spacing_obs', 'CONFIRMED', 'autocorrelation of %d cross profiles: imaged %.3f m (IQR %s) -> %.3f m = %.2f ft (published 40 ft = 12.192 m)'
        % (NA['truss_spacing']['rows'], NA['truss_spacing']['imaged_m'], NA['truss_spacing']['iqr'], NA['truss_spacing']['true_m'], NA['truss_spacing']['true_ft']))
    ver('roof.lenses_obs', 'PLAUSIBLE (minor)', '48.4 m is the IMAGED detection-box length (mean of the four detected boxes 47.75-48.75 m; magnification not removed -> ~47.9 m); the pointed ends fade, so tip-to-tip may be 1-2 m more. The westmost lens is full length too (detected 34 m because it is darker). Each skylight reads as a D in NAIP (straight east edge, convex west edge): a vaulted lens leaning east, or a D in plan - not settled.')
    ver('roof.glazed_tips_obs', 'CONFIRMED + NEW asymmetry', 'glass bands visible on 0.1 m crops at the stated rows. NEW: relative to the fascia midpoint the centre-section lens row sits %.1f m north; beyond the glass the south tip carries a %.1f m white segmented strip, the north tip %.1f m (frame model)'
        % (-PL['lens_row_u'], PL['fascia_u']['S'] - PL['glass_edges_u']['S_outer'], PL['glass_edges_u']['N_outer'] - PL['fascia_u']['N']))
    for o in ('06-035315', '06-035316'):
        d = V['dof']['objects'][o]
        ver('roof.dof_' + o, 'CONFIRMED', 'current DOF (%s): %d ft AGL / %d ft AMSL, accuracy %s, verified status %s, ACTION %s, JDATE %s (added 2013-10-16, before NAIP 2024 and the 2024-26 re-roofing); position unchanged. On the roof: u = %+.1f m from the relief-corrected centre, %.1f m inside the west eave (frame model) - the u values +54.7 / -60.9 in the note were relative to the IMAGED centre.'
            % (V['dof']['file'], d['agl_ft'], d['amsl_ft'], d['acc'], d['verified'], d['action'], d['jdate'], PL['dof_roof_tops'][o]['u'], PL['dof_roof_tops'][o]['v_inside_west_eave']))
    ver('roof.ground_amsl', 'CONFIRMED', 'AMSL - AGL = 8 / 8 ft (roof tops), 9 ft (06-035352)')
    ver('roof.profile', 'PLAUSIBLE (reproduced; one new independent check)', 'itb_naip_measure.py re-run: byte-identical output. NEW: the east eave wanders WITH the west eave (north tip -> hump: west %+.2f m, east %+.2f m, width constant) - the wander is a height signal, not a curved plan. The photo silhouette was not re-run (Commons API rate-limited, file not cached). The two relief models differ by 1-4 %% along the hall (<= 0.5 m on the drops).'
        % (NA['eaves']['north_tip_to_hump']['west'], NA['eaves']['north_tip_to_hump']['east']) if NA['eaves']['north_tip_to_hump'] else 'reproduced')
    ver('level3.floor', 'PLAUSIBLE / STILL UNVERIFIED', 'published heights bracket it: 40.1 m minus 90 ft (12.7), minus 100 ft (9.6), minus the 83-ft hall height now read first-hand (14.8, less the roof build-up at the crown). No section drawing found.')
    ver('facade.west', 'CONFIRMED', 'SFGate (frit, glass) re-read')
    ver('facade.end_walls', 'CONFIRMED', 'Enclos: "custom-designed unitized curtainwalls spanning over 60\'"')
    ver('facade.back_wall', 'CONFIRMED', 'SFGate re-read')
    ver('roof.upgrade_2024', 'CONFIRMED except the cost', 'Webcor: ceremony "June 27, 2024", "installing 1,400 kW solar"; FTF (first-hand): "Scaffolds reached 90 feet high over active roadways and AirTran tracks"; Airport World: "expected to be completed in mid-2026". The "$75 M" was not found in the re-fetched Webcor pages (Airports International still 403): unverified.')
    ver('naip.k_model', 'PLAUSIBLE (reproduced); north-south component unresolved', 'the five ring shifts also fit one central projection (nadir %s, H-h %.0f m) with rms %.2f m against %.2f m for k(x); the shift direction rotates with z (corr %.2f), as in a frame camera (NAIP 2022 here was a Leica ContentMapper frame sensor; the 2024 sensor is not documented in an open source found). At Boarding Area G (z ~100) the single-frame model fails (see ba_g.height_roof).'
        % (V['relief']['frame']['nadir_xz'], V['relief']['frame']['H_minus_h'], V['relief']['frame']['rms_m'], V['relief']['x_only']['rms_m'], V['relief']['corr_dir_z']),
        alt_frame_model=V['relief']['frame'])
    ver('naip.sun', 'CONFIRMED', 'NOAA solar position for 2024-05-20 at the shadow azimuth %.1f deg: %s PDT, elevation %.2f deg (cot %.4f), declination %.2f deg; the shadow-length elevation %.1f agrees'
        % (V['sun']['az_from_shadow'], V['sun']['pdt'], V['sun']['elev_deg'], V['sun']['cot_elev'], V['sun']['declination_deg'], V['sun']['elev_from_shadow_length']))
    A_ = NA['pier_A']
    ver('ba_a.height_roof', 'CORRECTED (refined; derivation partly flawed)', 'west band re-measured %.2f m (IQR %s, %d clean stations) = (relief + shadow) x h; a roof overhang moves both band edges equally and cancels, so the note\'s "minus any roof overhang" does not apply; method (b) depends on the SFO Museum footprint (offset 3-6 m at G). h = %.1f m (k(x)) / %.1f m (frame model).'
        % (A_['band_m'], A_['band_iqr'], A_['stations'], A_['h_roof_m']['x_only'], A_['h_roof_m']['frame']),
        correct=(round(0.5 * (A_['h_roof_m']['x_only'] + A_['h_roof_m']['frame']), 1), 'the overhang cancels in the band method; the footprint-offset method is unreliable; re-measured band gives %.1f-%.1f m' % (A_['h_roof_m']['frame'], A_['h_roof_m']['x_only'])),
        range_m=[round(A_['h_roof_m']['frame'] - 0.5, 1), round(A_['h_roof_m']['x_only'] + 0.5, 1)], conf='medium')
    ver('ba_a.pods', 'PLAUSIBLE (weaker than stated)', 'rim bands at the three pod apexes %s m (note: 2.5-3); the dark band includes the pod\'s own shadow (0.116 per m), so the rise is %s m (frame / k(x) / band without shadow) -> pod top %.1f-%.1f m, not 7.5 m above the main roof; the DOF 85 ft (25.9 m) point lies at pod 1\'s NNE end near the west eave (+-6.1 m). Pod 1 reads ~55-60 m long by eye on qa_pierA_frame.jpg (note: 70); pods 2 and 3 ~52-55 m.'
        % (A_['pod_rim_band_m'], A_['pod_dh_m_frame_xonly_noshadow'], A_['h_roof_m']['frame'] + min(min(q) for q in A_['pod_dh_m_frame_xonly_noshadow']), A_['h_roof_m']['x_only'] + max(max(q) for q in A_['pod_dh_m_frame_xonly_noshadow'])))
    ver('ba_a.dof_pod', 'CONFIRMED', 'current DOF: 06-035352 85 ft AGL / 94 ft AMSL, 1A, added 2013-10-16')
    ver('ba_a.gates', 'CONFIRMED (A6 vs A11 not a contradiction in time)', 'AGS: "Gate A6 was retrofitted to allow for a three PBB operation" (completed 2020); Wikipedia: "Gate A11 has three jetways" citing an older SFGate A380 article')
    ver('ba_a.architect', 'UNCHANGED (secondary-only)', 'Wikipedia re-read: "Gerson/Overstreet Architects and built by Hensel Phelps Construction (Boarding Area A)"')
    G_ = NA['pier_G']
    ver('ba_g.height_roof', 'PLAUSIBLE (re-measured, k(x) relief)', 'north shadow band re-measured %.2f m (IQR %s, %d stations); with k(x) h = %.1f m (IQR %s). The sunlit SSW facade could not be separated from the apron, so the k-free sum (0.297 h) was not reproduced. Under the single-frame relief model the roof would hide its own shadow -> G is in another frame of the mosaic or has little north-south relief.'
        % (G_['shadow_band_m'], G_['band_iqr'], G_['stations'], G_['h_roof_m_x_only']['median'], G_['h_roof_m_x_only']['iqr']), range_m=[13.0, 20.0])
    ver('ba_g.architect', 'CONFIRMED', 'Tutor Perini: "ARCHITECT Robin Chiang & Company"; Wikipedia: HOK in association with Robin Chiang & Company, Robert B. Wong Architects')
    ver('ba_g.area', 'CONFIRMED', 'Tutor Perini: "380,000-square-foot, three-story"')
    ver('ba_g.stories', 'CONFIRMED', 'Tutor Perini re-read')
    ver('ba_g.gaterooms', 'CONFIRMED', 'Tutor Perini: "six double-gated, two-level common use passenger gate rooms- capable of handling passenger traffic of twelve 747-400 wide-body aircraft"')
    ver('ba_g.facade', 'CONFIRMED', 'Tutor Perini: "metallic finished composite aluminum panels and a tinted energy-efficient glazed curtainwall"')
    ver('ba_g.pods', 'PLAUSIBLE', 'by eye on the G-frame crop (heading 297.75): ~62 / 58 / 66 m (note 60 / 55 / 62), +-4 m')
    PW = NA['pier_widths']
    ver('roof.col_grid', 'NOT RE-CHECKED (image not re-fetched); E/W grid consistent', 'the 40-ft E/W grid matches the NAIP truss spacing %.2f ft; the 80-ft N/S bay is not observable in NAIP' % NA['truss_spacing']['true_ft'])
    ver('ba_a.footprint', 'PLAUSIBLE', 'imaged main-roof width re-measured %.2f m (IQR %s, %d stations; note: 36.5 m by eye); axis 208.0 deg by NAIP edge alignment = airport grid t-axis + 180 (SFO Museum rectangle 207.7)'
        % (PW['A']['width_img_m'], PW['A']['iqr'], PW['A']['stations']), naip_roof_width_m=PW['A']['width_img_m'])
    ver('ba_g.footprint', 'NAIP WIDTH REFUTED (value unchanged)', 'the roof between its two parapet lines measures %.2f m (IQR %s, %d stations), not ~33.5 m - it matches the SFO Museum body width 38.3-38.4 m; axis 297.75 deg by NAIP edge alignment = airport grid s-axis + 180. The 3-6 m NNE offset was not re-checked.'
        % (PW['G']['width_img_m'], PW['G']['iqr'], PW['G']['stations']), naip_roof_width_m=PW['G']['width_img_m'])
    ver('ba_g.gates', 'UNCHANGED (secondary-only)', 'Wikipedia re-read: "Boarding Area G with 14 gates (G1-G14)"')
    ver('radp.itb', 'NOT RE-CHECKED', 'the RADP NOP was not re-fetched in this round')
    # sources, photos, lists
    s = S['sources']['seaonc']; s.update(read='full', accessed=TODAY, cache='refs/cache/buildings/itb/verify/src/seaonc.html',
                                         note='read first-hand on %s (the bot challenge of Sep 2026 no longer blocked curl)' % TODAY)
    tried = '; re-tried %s: %s' % (TODAY, SOURCE_STATUS['msc2000'])
    if tried not in S['sources']['msc2000']['note']: S['sources']['msc2000']['note'] += tried
    if 'photos' in V:
        S['photos_verification'] = dict(date=TODAY, method=V['photos']['api'], n=V['photos']['n'], all_licences_match=V['photos']['all_licences_match'],
                                        all_authors_match=V['photos']['all_authors_match'])
    S['unverified'] = [u for u in S['unverified'] if 'SEAONC' not in u and '705' not in u]
    S['unverified'] += [u for u in [
        'AISC Modern Steel Construction Feb 2000: still unreadable (%s) - truss length 320 ft and centre section 180 ft remain snippet-only' % SOURCE_STATUS['msc2000'],
        'NAIP 2024 sensor / mosaic seamlines: no open FGDC metadata found; the north-south relief component (roof length 252.7-255.1 m, pier G height) depends on it',
        'ITB roof upgrade cost ($75 M): not found in the re-fetched Webcor pages'] if u not in S['unverified']]
    oq = 'Verification %s: the roof length (252.7-255.1 m by NAIP) is 7-9 m short of the published 860 ft even though the DOF roof-top pair confirms the 380-ft centre span; an SFO record drawing (roof plan) or a ground survey of the tips would settle it' % TODAY
    if oq not in S['open_questions']: S['open_questions'].append(oq)
    S['verification'] = dict(date=TODAY, tool='tools/buildings/itb_verify.py', results='tools/buildings/itb_verify.json',
                             doc='docs/research/buildings_itb.md ## Verification',
                             note='verdicts per item in items[].verification; corrected items keep the previous value in items[].corrected')
    json.dump(S, open(SPEC, 'w'), indent=1, ensure_ascii=False)
    print('spec updated:', sum('verification' in it for it in S['items']), 'items carry a verification record;',
          [it['id'] for it in S['items'] if 'corrected' in it], 'corrected')


if __name__ == '__main__':
    V = main()
    if '--apply' in sys.argv:
        apply(V)
