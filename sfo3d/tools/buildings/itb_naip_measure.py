"""International Terminal (ITB) - NAIP 2024 measurements for the building research spec (tools/buildings/spec_itb.json,
docs/research/buildings_itb.md). Research tool: it writes numbers only (tools/buildings/itb_naip_measurements.json) plus
QA overlays with NAIP pixels to out/buildings/itb/ (local; NAIP is US public domain, but out/ is not committed).

Why NAIP needs care here (docs/research/imagery.md s.6): NAIP 2024 is orthorectified to a terrain DEM, so everything
above the ground is displaced away from the nadir of its frame ("relief displacement", roofs lean east). Around the
ITB this is 0.3-0.45 m per metre of height, i.e. 12-17 m for the 40 m hall roof. The tool therefore
  1. calibrates the displacement factor k (m of image shift per m of height) on FAA Digital Obstacle File (DOF) poles
     of known height (their luminaire rings are imaged 15-19 m east of the pole bases) -> linear model k(x);
  2. measures in-plane quantities that relief does not change (lengths/spacings between features at the same height:
     roof length tip to tip, truss-line spacing, lens skylights, pier widths) - with the central-projection
     magnification H/(H-h) (about +1 % at 40 m) removed;
  3. measures the relief itself where it carries information: the lateral wander of the five straight roof skylight
     lines = the wing-roof height profile (relative), anchored to the DOF roof top (131/132 ft AGL);
  4. reads the sun position from DOF pole shadows (for later shadow checks).
Every constant below carries its source. Frames: world x east, z south, metres from the ARP (tools/geo_frame.py).

Usage: python3 tools/buildings/itb_naip_measure.py [--qa-world]   (about 25 s; --qa-world only redraws the world overlay)
Inputs:  refs/cache/naip/naip_2024_world_0.5m_bgr.npy + .json (tools/imagery/naip_world.py),
         refs/cache/lighting/DAILY_DOF_CSV.ZIP (FAA DOF, DOF.CSV of 2026-09-18),
         data/sfo_airport.json (SFO Museum footprints, CDLA-Permissive-1.0) - read only.
Outputs: tools/buildings/itb_naip_measurements.json, out/buildings/itb/qa_*.png
"""
import csv, io, json, math, os, sys, zipfile
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

NAIP_NPY = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy')
NAIP_META = os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')
DOF_ZIP = os.path.join(ROOT, 'refs', 'cache', 'lighting', 'DAILY_DOF_CSV.ZIP')
OUT_JSON = os.path.join(HERE, 'itb_naip_measurements.json')
QA = os.path.join(ROOT, 'out', 'buildings', 'itb')
FT = 0.3048

# ---------------------------------------------------------------------------------------------- DOF objects used here
# FAA DOF (DAILY_DOF_CSV.ZIP, DOF.CSV 2026-09-18), accuracy code 1A = +-20 ft horizontal, +-3 ft vertical (DOF_README).
DOF_POLES_TALL = ['06-035353', '06-035354', '06-035355', '06-035356', '06-035357']   # 153-157 ft AGL, west of the ITB
DOF_ROOF = ['06-035315', '06-035316', '06-035352']                                   # BLDG 131 / 132 / 85 ft AGL
DOF_SHADOW = ['06-034826']                                                           # 108 ft apron pole, clear shadow
# Luminaire-ring picks (world x, z) for the tall poles: automatic difference-of-Gaussians peak inside a corridor
# 9..23 m east of the DOF base; where that peak sat on bright ground instead of the ring (06-035355, 06-035357) the
# ring was picked by eye on 0.05 m/px CLAHE crops (out/buildings/itb/pole_pick.png) - stated here, uncertainty +-1 m.
RING_MANUAL = {'06-035355': (-1410.2, 420.5), '06-035357': (-1606.2, 521.3)}
# Shadow picks for 06-034826 on a 0.05 m/px crop (out/buildings/itb/pole_shadow_a.png): shadow foot at the pole foot,
# tip = centre of the luminaire's shadow blob. By eye, +-0.7 m each.
SHADOW_PICK = {'06-034826': {'foot': (-1135.7, 247.3), 'tip': (-1134.5, 237.0)}}
TOWER = {'oas': '06-323169', 'imaged_cab_shift_m': (38.0, 40.0), 'src': 'docs/research/imagery.md s.6 (tower_lean.py)'}


def load_dof(oas_list):
    out = {}
    with zipfile.ZipFile(DOF_ZIP) as zf:
        name = [n for n in zf.namelist() if n.upper().endswith('.CSV')][0]
        with zf.open(name) as f:
            for d in csv.DictReader(io.TextIOWrapper(f, encoding='latin-1')):
                if d['OAS'] in oas_list:
                    lat, lon = float(d['LATDEC']), float(d['LONDEC'])
                    x, z = GF.wgs84_to_world(lat, lon)   # DOF horizontal datum is WGS 84 (DOF_README)
                    out[d['OAS']] = dict(oas=d['OAS'], type=d['TYPE'].strip(), agl_ft=int(d['AGL']), amsl_ft=int(d['AMSL']),
                                         acc=d['ACCURACY'].strip(), verified=d['VERIFIED STATUS'], jdate=d['JDATE'].strip(),
                                         study=d['FAA STUDY'].strip(), lat=lat, lon=lon, dmslat=d['DMSLAT'], dmslon=d['DMSLON'],
                                         x=round(x, 2), z=round(z, 2))
    return out


class Naip:
    def __init__(self):
        m = json.load(open(NAIP_META)); self.x0, self.z0, self.res = m['x0'], m['z0'], m['res']
        self.A = np.load(NAIP_NPY, mmap_mode='r')

    def sample(self, X, Z, interp=cv2.INTER_LINEAR):
        col = ((X - self.x0) / self.res - 0.5).astype(np.float32); row = ((Z - self.z0) / self.res - 0.5).astype(np.float32)
        r0, c0 = int(row.min()) - 2, int(col.min()) - 2; r1, c1 = int(row.max()) + 3, int(col.max()) + 3
        sub = np.ascontiguousarray(self.A[r0:r1, c0:c1])
        return cv2.remap(sub, col - c0, row - r0, interp)

    def box(self, xa, za, w, h, r):
        xs = np.arange(xa, xa + w, r); zs = np.arange(za, za + h, r); X, Z = np.meshgrid(xs, zs)
        return self.sample(X, Z, cv2.INTER_CUBIC), xs, zs

    def frame_patch(self, c, a, U, V):
        """rows = u (along a), cols = v (along n = a rotated -90 deg, i.e. east-ish for a pointing south-south-east)"""
        n = np.array([a[1], -a[0]]); uu, vv = np.meshgrid(U, V, indexing='ij')
        return self.sample(c[0] + uu * a[0] + vv * n[0], c[1] + uu * a[1] + vv * n[1])


def lab(img):
    q = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32); return q[..., 0], q[..., 2] - 128.0


# ------------------------------------------------------------------------------------------- 1. relief calibration
def calibrate_k(N, dof):
    rows = []
    for o in DOF_POLES_TALL:
        d = dof[o]; x, z, h = d['x'], d['z'], d['agl_ft'] * FT
        if o in RING_MANUAL:
            rx, rz = RING_MANUAL[o]; how = 'manual'
        else:
            img, xs, zs = N.box(x + 5, z - 7, 22, 14, 0.1); L, _ = lab(img)
            dog = cv2.GaussianBlur(L, (0, 0), 7) - cv2.GaussianBlur(L, (0, 0), 25)
            X, Z = np.meshgrid(xs, zs); m = (X > x + 9) & (X < x + 23) & (np.abs(Z - z) < 3.5)
            iy, ix = np.unravel_index(np.argmax(np.where(m, dog, -1e9)), dog.shape); rx, rz = xs[ix], zs[iy]; how = 'auto-DoG'
        dx, dz = rx - x, rz - z; dist = math.hypot(dx, dz)
        rows.append(dict(oas=o, agl_ft=d['agl_ft'], base=[x, z], ring=[round(rx, 2), round(rz, 2)], shift=[round(dx, 2), round(dz, 2)],
                         shift_m=round(dist, 2), k=round(dist / h, 4), pick=how, dir_deg=round(math.degrees(math.atan2(dx, -dz)) % 360, 1)))
    X = np.array([r['base'][0] for r in rows]); K = np.array([r['k'] for r in rows])
    Afit = np.c_[np.ones_like(X), X]; coef, res, *_ = np.linalg.lstsq(Afit, K, rcond=None)
    pred = Afit @ coef; sig = float(np.sqrt(((K - pred) ** 2).sum() / (len(K) - 2)))
    # uncertainty of the model at x (ordinary least squares), plus the DOF 1A horizontal tolerance (+-6.1 m on a
    # ~17 m shift -> +-0.13 in k per pole worst case; the scatter of the 5 poles is the honest empirical error)
    cov = sig ** 2 * np.linalg.inv(Afit.T @ Afit)
    kfun = lambda x: float(coef[0] + coef[1] * x)
    ksig = lambda x: float(math.sqrt(cov[0, 0] + 2 * x * cov[0, 1] + x * x * cov[1, 1]))
    tw = load_dof([TOWER['oas']])[TOWER['oas']]
    k_tower = kfun(tw['x'])
    return rows, dict(model='k(x) = a + b*x (x = world east of the object foot, m)', a=round(float(coef[0]), 5), b=round(float(coef[1]), 7),
                      scatter_sigma=round(sig, 4), H_minus_h_est_m=round(1 / coef[1]) if coef[1] > 0 else None,
                      nadir_x_est=round(-coef[0] / coef[1]) if coef[1] > 0 else None,
                      check_tower=dict(x=tw['x'], k_pred=round(k_tower, 3), imaged_cab_shift_m=TOWER['imaged_cab_shift_m'],
                                       implied_height_m=[round(s / k_tower, 1) for s in TOWER['imaged_cab_shift_m']],
                                       dof_top_agl_m=round(tw['agl_ft'] * FT, 1), src=TOWER['src'])), kfun, ksig


def sun_from_shadow(dof):
    out = []
    for o, p in SHADOW_PICK.items():
        d = dof[o]; h = d['agl_ft'] * FT; dx, dz = p['tip'][0] - p['foot'][0], p['tip'][1] - p['foot'][1]
        Ls = math.hypot(dx, dz); az_shadow = math.degrees(math.atan2(dx, -dz)) % 360
        out.append(dict(oas=o, agl_ft=d['agl_ft'], shadow_len_m=round(Ls, 2), shadow_az_deg=round(az_shadow, 1),
                        sun_az_deg=round((az_shadow + 180) % 360, 1), sun_elev_deg=round(math.degrees(math.atan2(h, Ls)), 1)))
    # physical bound: noon elevation on 2024-05-20 at 37.62 N, declination +20.0 deg (approx.) -> 72.4 deg max
    return dict(picks=out, noon_elev_max_deg=round(90 - 37.62 + 20.0, 1), date='2024-05-20 (NAIP QQDATE)')


# ------------------------------------------------------------------------------------------------- 2. ITB hall roof
AX0 = np.array([0.2466, 0.9691])      # principal axis of the SFO Museum 'International Terminal' hall part (tools/build_terminal_parts.py)
C0 = np.array([-1222.0, 365.0])       # first guess of the imaged roof centre (by eye, NAIP)
RU, RV = 0.25, 0.25                    # patch sampling (m); NAIP world raster is 0.5 m (native 0.6 m)


def roof_patch(N, c, a, U=np.arange(-160, 160, RU), V=np.arange(-80, 80, RV)):
    return N.frame_patch(c, a, U, V), U, V


def glazed_tips(img, U, V):
    """inner/outer u of the bluish glazed bands at both roof tips, per v column -> rotation of the tip edges"""
    L, b = lab(img); bb = cv2.blur(b, (5, 5)); res = {}
    for end, (ua, ub) in (('N', (-140, -100)), ('S', (98, 135))):
        i0, i1 = np.searchsorted(U, ua), np.searchsorted(U, ub); rows = []
        for v in np.arange(-32, 14.1, 2.0):
            j = int(round((v - V[0]) / RV)); g = np.where(bb[i0:i1, j] < -1.0)[0]
            if len(g) == 0: continue
            runs = np.split(g, np.where(np.diff(g) > 2)[0] + 1); r = max(runs, key=len)
            if len(r) * RU < 12: continue
            rows.append((v, U[i0 + r[0]], U[i0 + r[-1]]))
        rows = np.array(rows); res[end] = rows
    return res


def fit_line(x, y):
    A = np.c_[np.ones_like(x), x]; c, *_ = np.linalg.lstsq(A, y, rcond=None); r = y - A @ c
    return c, float(np.sqrt((r ** 2).sum() / max(1, len(x) - 2)))


def west_edges(img, U, V, u_list):
    """imaged west roof edge: east end of the dark west-facade band (glass seen obliquely, L < 150) where the white
    fascia starts (first v with L > 200 east of the band), searched in v in [-55, -25]"""
    L, _ = lab(img); Ls = cv2.blur(L, (1, 5)); out = []
    for u in u_list:
        i = int(round((u - U[0]) / RU)); j0, j1 = int((-55 - V[0]) / RV), int((-25 - V[0]) / RV)
        row = Ls[i, j0:j1]; dark = np.where(row < 150)[0]
        if len(dark) == 0: out.append((u, np.nan)); continue
        jd = dark.max(); br = np.where(row[jd:] > 200)[0]
        if len(br) == 0: out.append((u, np.nan)); continue
        jb = jd + br[0]
        # sub-pixel: where the profile crosses the midpoint between band and fascia
        lo, hi = row[jd], row[jb]; mid = 0.5 * (lo + hi); seg = row[jd:jb + 1]
        k = np.where(seg >= mid)[0][0]; f = (mid - seg[k - 1]) / (seg[k] - seg[k - 1] + 1e-6) if k > 0 else 0
        out.append((u, V[j0 + jd + k - 1] + f * RV if k > 0 else V[j0 + jd]))
    return np.array(out)


def track_skylights(img, U, V, u_list, vwest, backwards=False):
    """comb fit of 5 equally spaced dark skylight lines (offset o, spacing s) per u row, the first line constrained
    to lie 3-15 m east of the imaged west roof edge (the dark facade band must not be taken for a skylight)"""
    L, _ = lab(img); Lm = cv2.blur(L, (1, 9)); bg = cv2.dilate(Lm, np.ones((1, 25), np.uint8))
    D = cv2.GaussianBlur(np.clip(bg - Lm, 0, 80), (0, 0), sigmaX=1.2, sigmaY=0.1)
    out = []; o, s = None, 12.3; jj = np.arange(D.shape[1]); W = dict(zip(vwest[:, 0], vwest[:, 1]))
    for u in (u_list[::-1] if backwards else u_list):
        i = int(round((u - U[0]) / RU)); vw = W.get(u, np.nan)
        if not np.isfinite(vw): continue
        lo, hi = vw + 3.0, vw + 15.0
        orange = np.arange(lo, hi, 0.1) if o is None else np.arange(max(lo, o - 1.5), min(hi, o + 1.5) + 0.01, 0.05)
        srange = np.arange(11.5, 13.21, 0.05) if o is None else np.arange(max(11.0, s - 0.4), min(13.6, s + 0.4) + 0.01, 0.05)
        best = (-1, o, s)
        for oo in orange:
            for ss in srange:
                val = np.interp((oo + ss * np.arange(5) - V[0]) / RV, jj, D[i]).sum()
                if val > best[0]: best = (val, oo, ss)
        val, o, s = best; out.append((u, o, s, val, vw))
    out.sort(); return np.array(out)


def lenses(img, U, V, v_lo=-40.0, v_hi=30.0):
    """lens-shaped glazed skylights of the roof centre section: teal glass (Lab a* < -4.5), u in [-45, 40]"""
    L, b = lab(img); a = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)[..., 1] - 128.0
    m = (cv2.blur(a, (3, 3)) < -4.5).astype(np.uint8)
    i0, i1 = np.searchsorted(U, -45), np.searchsorted(U, 40); m[:i0] = 0; m[i1:] = 0
    m[:, :int((v_lo - V[0]) / RV)] = 0; m[:, int((v_hi - V[0]) / RV):] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 3), np.uint8))
    n, labl, st, cen = cv2.connectedComponentsWithStats(m)
    comps = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] * RU * RV < 60: continue
        ys, xs = np.where(labl == i)
        comps.append(dict(u0=float(U[ys.min()]), u1=float(U[ys.max()]), v_c=float(V[int(round(xs.mean()))]),
                          u_c=float(U[int(round(ys.mean()))]), w_max=float((np.bincount(ys).max()) * RV), area_m2=float(len(ys) * RU * RV)))
    comps.sort(key=lambda c: c['v_c']); return comps


def east_edges(img, U, V, track):
    """imaged east roof edge: strongest bright -> dark step 2-14 m east of the 5th skylight line"""
    L, _ = lab(img); Ls = cv2.GaussianBlur(L, (0, 0), 1.0); G = np.gradient(Ls, axis=1); out = []
    for u, o, s, val, vw in track:
        i = int(round((u - U[0]) / RU)); v5 = o + 4 * s
        je = np.arange(int((v5 + 2 - V[0]) / RV), int((v5 + 14 - V[0]) / RV)); e = je[np.argmin(G[i, je])]
        out.append((u, vw, V[e], 0.0, G[i, e]))
    return np.array(out)


def measure_roof(N, kfun, dof):
    # pass 1: SFO Museum axis -> tip-edge and lens-row rotation
    a = AX0 / np.linalg.norm(AX0); img, U, V = roof_patch(N, C0, a)
    tips = glazed_tips(img, U, V)
    slopes = []
    for end in ('N', 'S'):
        r = tips[end]
        for col in (1, 2):                                   # inner and outer glass boundary u(v)
            (c0, c1), sd = fit_line(r[:, 0], r[:, col]); slopes.append(c1)
    lz = lenses(img, U, V)
    if len(lz) >= 3:
        (c0, c1), _ = fit_line(np.array([q['v_c'] for q in lz]), np.array([q['u_c'] for q in lz])); slopes.append(c1)
    dudv = float(np.median(slopes)); delta = -dudv                                # tip edges perpendicular to the axis
    n = np.array([a[1], -a[0]]); a2 = a + delta * n; a2 /= np.linalg.norm(a2)
    # pass 2: rotated frame, re-centred on the tips (u) and the middle skylight line (v, at the lens row)
    img2, U, V = roof_patch(N, C0, a2); tips2 = glazed_tips(img2, U, V)
    uN_out = float(np.median(tips2['N'][:, 1])); uS_out = float(np.median(tips2['S'][:, 2]))
    uN_in = float(np.median(tips2['N'][:, 2])); uS_in = float(np.median(tips2['S'][:, 1]))
    ucen = 0.5 * (uN_out + uS_out)
    n2 = np.array([a2[1], -a2[0]]); c2 = C0 + ucen * a2
    img3, U, V = roof_patch(N, c2, a2); tips3 = glazed_tips(img3, U, V)
    # roof tip edges: outermost roof pixels beyond the glass (dark gap / lower roofs follow); take the glass outer edge
    # plus the fascia seen on the crops (~0.5-1 m) - reported separately
    tN_out = float(np.median(tips3['N'][:, 1])); tS_out = float(np.median(tips3['S'][:, 2]))
    tN_in = float(np.median(tips3['N'][:, 2])); tS_in = float(np.median(tips3['S'][:, 1]))
    fasc = fascia_ends(img3, U, V, tN_out, tS_out)
    uu = np.arange(-104, 104.1, 1.0); usel = np.r_[uu[uu <= -46], uu[uu >= 28]]
    vw = west_edges(img3, U, V, usel)
    tr_n = track_skylights(img3, U, V, uu[uu <= -46], vw, backwards=True)
    tr_s = track_skylights(img3, U, V, uu[uu >= 28], vw)
    tr = np.r_[tr_n, tr_s]
    edges = east_edges(img3, U, V, tr)
    lz3 = lenses(img3, U, V, v_lo=float(np.nanmedian(tr[:, 1])) - 7, v_hi=float(np.nanmedian(tr[:, 1] + 4 * tr[:, 2])) + 7)
    return dict(a=a2, c=c2, n=n2, pass1=dict(dudv_slopes=[round(s, 4) for s in slopes], delta=round(delta, 4)),
                tips=dict(N_outer=tN_out, N_inner=tN_in, S_outer=tS_out, S_inner=tS_in, fascia=fasc,
                          N_rows=tips3['N'].tolist(), S_rows=tips3['S'].tolist()),
                lenses=lz3, track=tr, edges=edges, img=img3, U=U, V=V)


def fascia_ends(img, U, V, uN, uS):
    """the roof tip line = last bright/roof pixel outside the glazed band (median over v), searched 0-4 m beyond"""
    L, _ = lab(img); Ls = cv2.GaussianBlur(L, (0, 0), 0.8); res = {}
    js = np.arange(int((-30 - V[0]) / RV), int((10 - V[0]) / RV), 8)
    for end, u0, sgn in (('N', uN, -1), ('S', uS, +1)):
        pos = []
        for j in js:
            us = u0 + sgn * np.arange(0, 4.01, RU); ii = np.clip(((us - U[0]) / RU).round().astype(int), 0, len(U) - 1)
            prof = Ls[ii, j]; g = np.diff(prof)
            k = int(np.argmin(g)) if len(g) else 0              # strongest bright -> dark step going outward
            pos.append(us[k] + sgn * RU / 2)
        res[end] = float(np.median(pos))
    return res


# ------------------------------------------------------------------------------------------------------------ main
def eave_profile(N, c, a, kfun, u_list=np.arange(-124, 124.1, 1.0), exclude=23.0):
    """Primary wing-profile signal. Along the west side of the hall the oblique west glass wall shows as a dark band
    between a STRAIGHT line at constant height (its west boundary, v ~ -43.3 m in this frame: the facade base /
    canopy line) and the imaged west roof eave (its east boundary). The eave line wanders east where the roof is
    higher: v_eave(u) = v_true + 0.969*k(x)*h_eave(u) (0.969 = east . n). The straightness of the base line checks the
    frame; the lens centre section (|u| < 23 m) has a different west wall and is excluded."""
    U = np.arange(-160, 160, RU); V = np.arange(-80, 80, RV); n = np.array([a[1], -a[0]])
    img = N.frame_patch(c, a, U, V); L, _ = lab(img); Ls = cv2.blur(L, (1, 5)); out = []
    for u in u_list:
        if abs(u) < exclude: continue
        i = int(round((u - U[0]) / RU)); j0, j1 = int((-60 - V[0]) / RV), int((-25 - V[0]) / RV)
        row = Ls[i, j0:j1]; dark = np.where(row < 150)[0]
        if len(dark) == 0: continue
        runs = np.split(dark, np.where(np.diff(dark) > 2)[0] + 1); r = runs[-1]
        if len(r) * RV < 1.5 or len(r) * RV > 8: continue      # glazed tips / bridges: no clean band
        vb, ve = V[j0 + r[0]], V[j0 + r[-1]] + RV
        x = (c + u * a + ve * n)[0]
        out.append((u, vb, ve, kfun(x - 16.0)))                 # k at the (approx.) true eave x
    return np.array(out)


def main():
    os.makedirs(QA, exist_ok=True)
    N = Naip(); dof = load_dof(DOF_POLES_TALL + DOF_ROOF + DOF_SHADOW)
    poles, kmodel, kfun, ksig = calibrate_k(N, dof)
    sun = sun_from_shadow(dof)
    R = measure_roof(N, kfun, dof)
    a, c, n = R['a'], R['c'], R['n']
    to_world = lambda u, v: c + u * a + v * n
    EP = eave_profile(N, c, a, kfun)
    base_med = float(np.median(EP[:, 1])); base_sd = float(np.std(EP[:, 1]))
    proj_e = float(n[0])                                   # relief direction ~ due east -> component along v
    # symmetric even fit of the eave line: ve = c0 + s*u + proj*k*(p2 u^2 + p4 u^4 + p6 u^6)
    ue, ve, ke = EP[:, 0], EP[:, 2], EP[:, 3]; x_ = np.abs(ue) / 100
    Me = np.c_[np.ones_like(ue), ue, proj_e * ke[:, None] * np.c_[x_ ** 2, x_ ** 4, x_ ** 6]]
    pe, *_ = np.linalg.lstsq(Me, ve, rcond=None); re_ = ve - Me @ pe
    he_rel = lambda u: float(pe[2] * (abs(u) / 100) ** 2 + pe[3] * (abs(u) / 100) ** 4 + pe[4] * (abs(u) / 100) ** 6)
    ug = np.arange(23, 125, 1.0); hg = np.array([he_rel(u) for u in ug]); upk = float(ug[np.argmax(hg)])
    H_top_e = np.mean([dof[o]['agl_ft'] for o in ('06-035315', '06-035316')]) * FT
    eave = dict(method='west eave line vs the straight facade-base line (dark oblique west wall band); even-polynomial fit (u^2,u^4,u^6) with axis-tilt term; anchored to the DOF roof tops (131/132 ft AGL = %.2f m) at the fitted peak' % H_top_e,
                base_line_v_median=round(base_med, 2), base_line_v_sd=round(base_sd, 3), fit_coef=[round(float(q), 4) for q in pe],
                fit_rms_m=round(float(np.sqrt((re_ ** 2).mean())), 3), tilt=round(float(pe[1]), 5), peak_abs_u_m=upk,
                profile=[dict(abs_u=float(u), drop_below_peak_m=round(float(hg.max() - h), 2), h_agl_m=round(H_top_e - float(hg.max() - h), 2)) for u, h in zip(ug, hg)],
                points=[dict(u=float(u), v_base=round(float(b), 2), v_eave=round(float(e), 2), k=round(float(k), 3),
                             drop_below_peak_m=round(float((ve.max() - e) / (proj_e * k)), 2)) for u, b, e, k in EP],
                n_points=int(len(EP)))
    # --- relief-corrected (true) roof planform: imaged roof-level features moved back by k*h along the relief
    #     direction (due east within the pole scatter), and demagnified by (H-h)/H about the frame nadir (1st order)
    E_ = R['edges']; width_img_med = float(np.median(E_[:, 2] - E_[:, 1]))
    h_of = lambda u: H_top_e - float(hg.max() - he_rel(min(max(abs(u), 23.0), 124.0)))
    e_n, e_a = float(n[0]), float(a[0])                      # east . n, east . a
    fN, fS = R['tips']['fascia']['N'], R['tips']['fascia']['S']
    v_w_img = float(np.median([q[2] - 0.0 for q in EP if 55 <= abs(q[0]) <= 80]))    # west eave at the humps (imaged)
    k0 = kfun(-1240.0); h_pk = H_top_e
    v_w_true = v_w_img - e_n * k0 * h_pk
    v_e_true = v_w_true + width_img_med * (1 - h_pk / (kmodel['H_minus_h_est_m'] or 3600.0))
    uN_true = fN - e_a * kfun(-1255.0) * h_of(fN); uS_true = fS - e_a * kfun(-1190.0) * h_of(fS)
    corners = {nm: [round(float(q), 2) for q in (c + uu_ * a + vv_ * n)] for nm, (uu_, vv_) in dict(
        NW=(uN_true, v_w_true), NE=(uN_true, v_e_true), SE=(uS_true, v_e_true), SW=(uS_true, v_w_true)).items()}
    ctr_true = c + 0.5 * (uN_true + uS_true) * a + 0.5 * (v_w_true + v_e_true) * n
    dof_uv_true = {o: [round(float((np.array([dof[o]['x'], dof[o]['z']]) - c) @ a), 2), round(float((np.array([dof[o]['x'], dof[o]['z']]) - c) @ n), 2)] for o in ('06-035315', '06-035316', '06-035352')}
    planform = dict(note='relief-corrected estimate of the MAIN ROOF outline (eaves), world x/z; +-1.5 m (k +-0.02, anchor +-1 m, edge picks +-0.5 m)',
                    axis_xz=[round(float(a[0]), 5), round(float(a[1]), 5)], centre_xz=[round(float(q), 2) for q in ctr_true],
                    corners=corners, length_m=round(float(uS_true - uN_true) * (1 - 34.0 / (kmodel['H_minus_h_est_m'] or 3600.0)), 2),
                    width_m=round(float(v_e_true - v_w_true), 2), west_eave_v_img=round(v_w_img, 2), west_eave_v_true=round(float(v_w_true), 2),
                    dof_roof_points_uv=dof_uv_true,
                    check='DOF 06-035315/06-035316 (roof tops, +-6.1 m horizontal) project to v = %s / %s, i.e. %.1f / %.1f m inside the relief-corrected west eave line' % (
                        dof_uv_true['06-035315'][1], dof_uv_true['06-035316'][1], dof_uv_true['06-035315'][1] - v_w_true, dof_uv_true['06-035316'][1] - v_w_true))
    # --- relief-free lengths (central-projection magnification removed, H - h from the k(x) slope)
    Hh = kmodel['H_minus_h_est_m'] or 3500.0
    tips = R['tips']
    L_glass_img = tips['S_outer'] - tips['N_outer']
    L_fascia_img = tips['fascia']['S'] - tips['fascia']['N']
    # --- skylight lines -> centre-line wander c(u) -> relative height profile
    T = R['track']; good = T[:, 3] > 0.55 * np.median(T[:, 3])
    uu, cc, ss = T[good, 0], T[good, 1] + 2 * T[good, 2], T[good, 2]
    xw = np.array([to_world(u, v)[0] for u, v in zip(uu, cc)])          # imaged x of the line; true x ~ imaged - k h
    k_u = np.array([kfun(x - 15.0) for x in xw])                        # evaluate k at the (approx.) true foot x
    proj = float(np.dot([1.0, 0.0], n))                                  # relief is ~due east (pole rings 88-103 deg)
    # symmetric fit: cc = c0 + s*u + proj*k(u)*h(|u|), h(|u|) even polynomial in u (deg 4); solve linear LSQ
    Au = np.abs(uu); Mh = np.c_[np.ones_like(Au), (Au / 100) ** 2, (Au / 100) ** 4]
    M = np.c_[np.ones_like(uu), uu, proj * k_u[:, None] * Mh[:, 1:]]    # h0 absorbed in c0 (k ~ const locally)
    p, *_ = np.linalg.lstsq(M, cc, rcond=None); resid = cc - M @ p
    s_tilt = float(p[1])
    # relative profile h(u) - h(0): from the fitted even part, and point-wise from the de-trended data
    h_rel_fit = lambda u: float(p[2] * (abs(u) / 100) ** 2 + p[3] * (abs(u) / 100) ** 4)
    h_rel_pts = (cc - p[0] - s_tilt * uu) / (proj * k_u)
    # anchor: DOF roof tops 06-035315/06-035316 = 131/132 ft AGL at |u| ~ where the fitted profile peaks
    dofr = [dof[o] for o in ('06-035315', '06-035316')]
    dof_uv = [((np.array([d['x'], d['z']]) - c) @ a, (np.array([d['x'], d['z']]) - c) @ n) for d in dofr]
    ugrid = np.arange(0, 131, 1.0); hgrid = np.array([h_rel_fit(u) for u in ugrid])
    # the imaged profile is only sampled over |u| in [28,104]; report max inside that range
    samp = (ugrid >= 28) & (ugrid <= 104)
    u_pk = float(ugrid[samp][np.argmax(hgrid[samp])]); h_pk_rel = float(hgrid[samp].max())
    H_top = np.mean([d['agl_ft'] for d in dofr]) * FT
    prof = [dict(u=float(u), h_agl_m=round(H_top - (h_pk_rel - h_rel_fit(u)), 2)) for u in ugrid if 28 <= u <= 104]
    pts = [dict(u=float(u), dv_m=round(float(v), 3), h_rel_m=round(float(h), 2)) for u, v, h in zip(uu, cc - p[0] - s_tilt * uu, h_rel_pts)]
    # asymmetry check: north (u<0) vs south (u>0) point-wise heights at mirrored |u|
    north = {int(abs(q['u'])): q['h_rel_m'] for q in pts if q['u'] < 0}; south = {int(q['u']): q['h_rel_m'] for q in pts if q['u'] > 0}
    common = sorted(set(north) & set(south)); asym = [south[u] - north[u] for u in common]
    # --- truss spacing and roof width
    # spacing: (1) north half only (u < 0; the south half of the roof shows doubled dark lines ~2.5 m apart in the
    # May 2024 image - origin unknown; the 2024-26 re-roofing only started on 27 Jun 2024), strong comb rows;
    # (2) the five lens skylights, which sit on the truss lines (centre-to-centre)
    Tn = T[(T[:, 0] < 0) & (T[:, 3] >= np.percentile(T[:, 3], 50))]
    spacing = float(np.median(Tn[:, 2])); spacing_sd = float(np.std(Tn[:, 2]))
    lzc = sorted(q['v_c'] for q in R['lenses'] if q['u1'] - q['u0'] > 40)
    lens_sp = float(np.median(np.diff(lzc))) if len(lzc) >= 3 else float('nan')
    E = R['edges']; width_img = E[:, 2] - E[:, 1]
    # --- lenses
    lz = R['lenses']
    # --- world positions (imaged, i.e. roof level) and relief-corrected (true) estimates of key points
    res = dict(
        generated_by='tools/buildings/itb_naip_measure.py', imagery='USDA NAIP 2024 (flown 2024-05-20), world raster refs/cache/naip/naip_2024_world_0.5m (0.5 m, native 0.6 m); public domain',
        dof_file='FAA DOF DAILY_DOF_CSV.ZIP, DOF.CSV dated 2026-09-18 (https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP)',
        dof_objects={o: dof[o] for o in DOF_ROOF + DOF_POLES_TALL + DOF_SHADOW},
        relief=dict(poles=poles, model=kmodel, k_at_itb_roof=dict(x=-1225.0, k=round(kfun(-1225.0), 3), sigma=round(ksig(-1225.0), 3)),
                    k_at_pierA=dict(x=-1235.0, k=round(kfun(-1235.0), 3)), k_at_pierG=dict(x=-1420.0, k=round(kfun(-1420.0), 3)),
                    direction='due east within +-8 deg (ring shifts 88-103 deg)'),
        sun=sun,
        roof_frame=dict(axis_xz=[round(float(a[0]), 5), round(float(a[1]), 5)],
                        axis_heading_deg=round(math.degrees(math.atan2(a[0], -a[1])) % 360, 2),
                        rotation_vs_sfom_axis_deg=round(math.degrees(math.atan2(R['pass1']['delta'], 1)), 2), pass1=R['pass1'],
                        centre_imaged_xz=[round(float(q), 2) for q in c],
                        note='u along the axis (towards SSE / Boarding Area A), v across (towards ENE); imaged = roof level in NAIP, shifted east by k*h'),
        roof_length=dict(glass_outer_to_outer_img_m=round(L_glass_img, 2), fascia_to_fascia_img_m=round(L_fascia_img, 2),
                         magnification_note='imaged plane at height h is magnified by (H-h+h)/(H-h) ~ 1 + h/(H-h); H-h from k slope = %s m' % Hh,
                         fascia_to_fascia_true_m=[round(L_fascia_img * Hh / (Hh + h), 2) for h in (30.0, 40.0)],
                         tips=dict(N_outer=tips['N_outer'], N_inner=tips['N_inner'], S_outer=tips['S_outer'], S_inner=tips['S_inner'], fascia=tips['fascia'])),
        glazed_tip_bands=dict(N_depth_m=round(tips['N_inner'] - tips['N_outer'], 2), S_depth_m=round(tips['S_outer'] - tips['S_inner'], 2)),
        skylight_lines=dict(count=5, spacing_img_m_north_rows=round(spacing, 3), spacing_sd=round(spacing_sd, 3), rows=int(len(Tn)),
                            spacing_img_m_lens_centres=round(lens_sp, 3), lens_centres_v=[round(q, 2) for q in lzc],
                            spacing_true_m=round(0.5 * (spacing + lens_sp) * Hh / (Hh + 38.0), 3),
                            outer_line_to_line_true_m=round(2 * (spacing + lens_sp) * Hh / (Hh + 38.0), 2),
                            note='true = imaged * (H-h)/H with h ~ 38 m; published column grid 40 ft (12.19 m) E/W (SOM concept sketch)'),
        roof_width=dict(img_median_m=round(float(np.median(width_img)), 2), img_p10_p90=[round(float(np.percentile(width_img, 10)), 2), round(float(np.percentile(width_img, 90)), 2)],
                        true_m=round(float(np.median(width_img)) * Hh / (Hh + 36.0), 2), note='west edge = facade band -> white fascia rise; east edge = fascia -> lower roof fall'),
        lenses=[{k: round(v, 2) for k, v in q.items()} for q in lz],
        eave_profile=eave,
        true_planform=planform,
        wing_profile=dict(method='five straight skylight lines; their common lateral wander in NAIP = relief = 0.97*k(x)*h(u); even-polynomial fit h(|u|) + axis tilt; anchored to DOF 131/132 ft AGL at the fitted peak',
                          fit_coef=[round(float(q), 4) for q in p], fit_rms_m=round(float(np.sqrt((resid ** 2).mean())), 3), tilt_residual=round(s_tilt, 5),
                          peak_u_m=u_pk, peak_minus_u0_m=round(h_pk_rel, 2), anchored_profile=prof, points=pts,
                          asymmetry_south_minus_north_m=dict(u=common, d=[round(q, 2) for q in asym]),
                          dof_roof_points_uv=[[round(float(q), 1) for q in t] for t in dof_uv]))
    json.dump(res, open(OUT_JSON, 'w'), indent=1)
    qa(R, res, N, dof, poles)
    print(json.dumps({k: res[k] for k in ('roof_frame', 'roof_length', 'glazed_tip_bands', 'skylight_lines', 'roof_width')}, indent=1))
    print('k model', kmodel); print('k at ITB', res['relief']['k_at_itb_roof']); print('sun', sun)
    print('lenses', res['lenses']); print('profile peak', u_pk, h_pk_rel, 'rms', res['wing_profile']['fit_rms_m'])
    for q in prof[::8]: print('  u=%5.1f h=%.2f' % (q['u'], q['h_agl_m']))
    print('asym', list(zip(common[::6], [round(q, 2) for q in asym[::6]])))
    print('eave: base sd', eave['base_line_v_sd'], 'rms', eave['fit_rms_m'], 'tilt', eave['tilt'], 'peak |u|', eave['peak_abs_u_m'])
    for q in eave['profile'][::8]: print('  |u|=%5.1f drop=%.2f h=%.2f' % (q['abs_u'], q['drop_below_peak_m'], q['h_agl_m']))


def qa(R, res, N, dof, poles):
    img = R['img'].copy(); U, V = R['U'], R['V']
    P = lambda u, v: (int(round((v - V[0]) / RV)), int(round((u - U[0]) / RU)))
    for u, o, s, val, vw in R['track']:
        for i in range(5): cv2.circle(img, P(u, o + i * s), 1, (0, 0, 255), -1)
    for u, vw, ve, gw, ge in R['edges']:
        cv2.circle(img, P(u, vw), 1, (0, 255, 0), -1); cv2.circle(img, P(u, ve), 1, (255, 0, 0), -1)
    t = R['tips']
    for key, col in (('N_outer', (0, 255, 255)), ('N_inner', (0, 160, 255)), ('S_outer', (0, 255, 255)), ('S_inner', (0, 160, 255))):
        y = P(t[key], 0)[1]; cv2.line(img, (0, y), (img.shape[1] - 1, y), col, 1)
    for end in ('N', 'S'):
        y = P(t['fascia'][end], 0)[1]; cv2.line(img, (0, y), (img.shape[1] - 1, y), (255, 0, 255), 1)
    for q in R['lenses']:
        cv2.rectangle(img, P(q['u0'], q['v_c'] - q['w_max'] / 2), P(q['u1'], q['v_c'] + q['w_max'] / 2), (255, 255, 0), 1)
    cv2.imwrite(os.path.join(QA, 'qa_roof_frame.png'), img)




def qa_world():
    """NAIP (0.25 m) with: SFO Museum hall outline (magenta), imaged roof outline (yellow), relief-corrected roof
    outline (cyan), DOF roof points with their +-6.1 m circles (red). Reads the JSON written by main()."""
    R = json.load(open(OUT_JSON)); N = Naip(); T = R['true_planform']
    xa, za, w, h, r = -1360.0, 200.0, 260.0, 330.0, 0.25
    img, xs, zs = N.box(xa, za, w, h, r); s = 1 / r
    P = lambda p: (int(round((p[0] - xa) * s)), int(round((p[1] - za) * s)))
    B = json.load(open(os.path.join(ROOT, 'data', 'sfo_buildings.json')))
    hall = [q for q in B['parts'] if q['kind'] == 'hall' and 'International' in q['name']][0]
    cv2.polylines(img, [np.array([P(p) for p in hall['rings'][0]], np.int32)], True, (255, 0, 255), 1)
    cor = [T['corners'][k] for k in ('NW', 'NE', 'SE', 'SW')]
    cv2.polylines(img, [np.array([P(p) for p in cor], np.int32)], True, (255, 255, 0), 2)
    a = np.array(R['roof_frame']['axis_xz']); c = np.array(R['roof_frame']['centre_imaged_xz']); n = np.array([a[1], -a[0]])
    f = R['roof_length']['tips']['fascia']; vw = T['west_eave_v_img']; ve = vw + R['roof_width']['img_median_m']
    img_c = [c + f['N'] * a + vw * n, c + f['N'] * a + ve * n, c + f['S'] * a + ve * n, c + f['S'] * a + vw * n]
    cv2.polylines(img, [np.array([P(p) for p in img_c], np.int32)], True, (0, 255, 255), 1)
    for o in ('06-035315', '06-035316', '06-035352'):
        d = R['dof_objects'][o]; cv2.circle(img, P((d['x'], d['z'])), int(6.1 * s), (0, 0, 255), 2)
        cv2.putText(img, '%s %d ft' % (o, d['agl_ft']), (P((d['x'], d['z']))[0] + 26, P((d['x'], d['z']))[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(img, 'magenta SFO Museum hall part | yellow NAIP imaged roof | cyan relief-corrected roof | red DOF +-6.1 m', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(QA, 'qa_planform_world.png'), img)
    cv2.imwrite(os.path.join(QA, 'qa_planform_world_small.png'), cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA))


if __name__ == '__main__':
    if '--qa-world' not in sys.argv:
        main()
    qa_world()
