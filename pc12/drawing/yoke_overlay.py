"""
Photo overlays of the yoke design (sheets L6Y / L6Y2, interior.YOKE_DESIGN rev K) -- PRIVATE REFERENCE, git-ignored
output.

The drawn yoke is the set of solids of model/yoke_geom.py; it is RAY-CAST (sphere tracing of the signed-distance
solids, the switches included) through the fitted cameras of the photos, so the overlays show what the camera would see
of the drawn yoke -- silhouettes of the white cover and of the black moulding -- plus the table's feature curves on the
solids' faces (inserts, badge, pads, trim face, shield, switches):

    P1046408   cams_beauty.json 'panel_408' (the one calibrated face-on view), both yokes
    Mexico     the Pilatus press photo pil_Mexico_PC12PRO_8 (bundle-adjustment camera), both yokes
    AOPA       fd_aopa_pro_cockpit.jpg (= the Pilatus press photo): pilot yoke from aft-OUTBOARD, co-pilot yoke from
               aft-INBOARD (~54 deg; rev K, judges FID2-01, with its step / lower-insert picks EXTRA_PICKS)
    P1046410   bundle-adjustment camera, pilot yoke

Only the yoke's photo POSE is fitted (fore-aft dx, lateral dy, vertical dz, roll -- the photos show the gust-locked /
hand-held column, never the drawn neutral), to the COVER landmarks only (TCS, AFCS cap, badge, step ends, lower-insert
corners, foot; the heads are checked, not fitted).  Criteria per photo (deviations.json, sheet L6Y2):
  landmarks   pick vs drawn landmark, mm (trim / hbtn: the heads, not fitted)
  grip rows   rev K: the CURATED photo silhouettes (refs/cache/.../measure/r3/sil2.pkl -- the near-face-on views' auto
              rows with the background features masked (the round panel recesses), the inboard slot sides hand-traced
              and snapped (the J band / panel seam behind them), the AOPA co-pilot view hand-traced; the AOPA pilot
              view's auto rows are dropped: they lock onto the leather texture against the dark panel) vs the ray-cast
              silhouette per image row, mm (+ = drawn wider / lower), with per-band (h) mean and max
  pads        the pad outlines traced at 2-7x (r2 traces + r3 AOPA co-pilot / Mexico R) vs the drawn pads, mm (mean /
              max nearest distance)
  neck        P1046408: the inboard neck's top edge per pixel column, mm (+ = drawn high)
  shell       the shell outline snapped to the photo edges (+-4 mm), signed mean by region, mm (+ = photo outside)

    python3 -m drawing.yoke_overlay [p408 mex press p410]   -> refs/cache/overlays/yoke/*.png (+ deviations.json)

Inputs (all git-ignored, refs/cache): photos, fd_research/yoke/measure/{depth_scripts, r2, r3}.  No photo and no overlay
that embeds one is ever written outside refs/cache.
"""
from __future__ import annotations

import importlib.util
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model import interior as I  # noqa: E402
from model import yoke_geom as G  # noqa: E402

CACHE = ROOT / "refs" / "cache"
MEAS = CACHE / "fd_research" / "yoke" / "measure"
OUT = CACHE / "overlays" / "yoke"
IMG = {"p408": CACHE / "photos/interior/fd_commons_pro3001_P1046408.jpg",
       "p410": CACHE / "photos/interior/fd_commons_pro3001_P1046410.jpg",
       "mex": CACHE / "fd_research/pc12pro_layout/pilnews/pil_Mexico_PC12PRO_8.jpg",
       "press": CACHE / "photos/interior/fd_aopa_pro_cockpit.jpg"}
COVER_FEATS = ("tcs", "red", "badge", "stp_o", "stp_i", "inb_o", "inb_i", "foot")
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    FONT_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
except OSError:                                                  # pragma: no cover
    FONT = FONT_B = None


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).parent))
    spec.loader.exec_module(mod)
    return mod


def rodrigues(r):
    r = np.asarray(r, float)
    th = np.linalg.norm(r)
    if th < 1e-12:
        return np.eye(3)
    k = r / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


class Cam:
    """Pinhole (+ k1 and principal-point offset for the bundle-adjustment cameras): q = rvec(3), t(3), f, k1, cx, cy."""

    def __init__(self, q, W, H):
        q = np.r_[np.asarray(q, float), np.zeros(max(0, 10 - len(q)))]
        self.q, self.W, self.H = q, W, H
        self.R = rodrigues(q[:3])
        self.C = -self.R.T @ q[3:6]

    def __call__(self, X):
        q = self.q
        Xc = np.atleast_2d(X) @ self.R.T + q[3:6]
        xn, yn = Xc[:, 0] / Xc[:, 2], Xc[:, 1] / Xc[:, 2]
        k = 1 + q[7] * (xn * xn + yn * yn)
        return np.c_[self.W / 2 + q[8] + q[6] * xn * k, self.H / 2 + q[9] + q[6] * yn * k]

    def rays(self, px):
        """Unit world directions of pixels (k1 undone iteratively)."""
        px = np.atleast_2d(np.asarray(px, float))
        q = self.q
        xd = (px[:, 0] - self.W / 2 - q[8]) / q[6]
        yd = (px[:, 1] - self.H / 2 - q[9]) / q[6]
        xn, yn = xd.copy(), yd.copy()
        for _ in range(20):
            k = 1 + q[7] * (xn * xn + yn * yn)
            xn, yn = xd / k, yd / k
        d = np.c_[xn, yn, np.ones(len(xn))] @ self.R
        return d / np.linalg.norm(d, axis=1)[:, None]


def cameras():
    cb = json.loads((CACHE / "overlays/vqa/cams_beauty.json").read_text())
    B = pickle.load(open(MEAS / "depth_scripts" / "ba5_cl.pkl", "rb"))
    WH = {"p408": (1920, 1440), "p410": (1920, 2560), "mex": (7657, 5170), "press": (5000, 3335)}
    cams = {"p408": Cam(cb["panel_408"]["p"], 1920, 1440)}
    for k in ("p410", "mex", "press"):
        cams[k] = Cam(B["Q"][k], *WH[k])
    return cams


# ------------------------------------------------------------------------------------------------ the design
def features():
    """Landmarks (u, h, a) of the drawn yoke (co-pilot sense: u outboard; the inboard head at u < 0)."""
    D = I.YOKE_DESIGN
    tu, th = D["tcs"][:2]
    au, ah = D["afcs"][:2]
    c, _ = G.head_out_face()
    ci, ni = G.head_in_face()
    b = D["button"]
    nci, cci = ni * [-1, 1, 1], ci * [-1, 1, 1]
    pb = np.array([-float(b[0]), float(b[1])])
    a_b = cci[2] - ((pb[0] - cci[0]) * nci[0] + (pb[1] - cci[1]) * nci[1]) / nci[2]
    hb = np.array([pb[0], pb[1], a_b]) + (float(b[4]) + float(b[5])) * nci       # the cap top
    ca, na = G.afcs_axis()
    red = ca + 0.8 * float(D["afcs"][3]) * na                       # 0.8 up the red cap on its boss (rev K)
    f = dict(tcs=(tu, th, float(G.face_a(th))),
             red=tuple(red),
             badge=(0.0, 49.65, float(G.face_a(49.65))), stp_o=(12.9, 4.1, 0.0), stp_i=(-12.9, 4.1, 0.0),
             inb_o=(8.8, -17.6, float(G.face_a(-17.6))), inb_i=(-8.8, -17.6, float(G.face_a(-17.6))),
             foot=(0.0, -56.0, float(G.face_a(-56.0))), trim=tuple(c), hbtn=tuple(hb))
    return {k: np.array(v, float) for k, v in f.items()}


def to_model(P, side, pose):
    """(u, h, a) mm -> model (x, y, z) m for the yoke on `side` in the photo pose (dx, dy, dz m, roll deg)."""
    dx, dy, dz, rho = pose
    P = np.atleast_2d(P)
    hub = I.yoke_hub(side)
    x_ref = float(hub[0] + I.YOKE["hub_whd"][2])
    yl, zl = side * P[:, 0] * 1e-3, P[:, 1] * 1e-3
    c, s = math.cos(math.radians(rho)), math.sin(math.radians(rho))
    return np.c_[x_ref + dx + P[:, 2] * 1e-3, hub[1] + dy + yl * c - zl * s, hub[2] + dz + yl * s + zl * c]


def from_model(X, side, pose):
    dx, dy, dz, rho = pose
    X = np.atleast_2d(X)
    hub = I.yoke_hub(side)
    x_ref = float(hub[0] + I.YOKE["hub_whd"][2])
    a = (X[:, 0] - x_ref - dx) * 1e3
    y, z = X[:, 1] - hub[1] - dy, X[:, 2] - hub[2] - dz
    c, s = math.cos(math.radians(rho)), math.sin(math.radians(rho))
    yl, zl = y * c + z * s, -y * s + z * c
    return np.c_[side * yl * 1e3, zl * 1e3, a]


def fit_pose(cam, picks, feat, side, sig_px=2.0):
    names = [k for k in COVER_FEATS if k in picks and k in feat]
    U = np.array([picks[k] for k in names], float)
    X0 = np.array([feat[k] for k in names])

    def res(p):
        return ((cam(to_model(X0, side, p)) - U) / sig_px).ravel()
    return least_squares(res, np.zeros(4), loss="soft_l1", x_scale=[0.02, 0.01, 0.01, 2.0]).x


def px_per_mm(cam, side, pose, at=(0.0, 0.0, 0.0)):
    P = np.array([at, np.add(at, (10.0, 0, 0)), np.add(at, (0, 10.0, 0))], float)
    q = cam(to_model(P, side, pose))
    return 0.5 * (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[0])) / 10.0


# ------------------------------------------------------------------------------------------------ ray casting
PARTS = ("body", "cover", "switches", "grip_out", "grip_in")    # rev K: grips labelled apart (no lateral-mask heuristics)
BLACK = (0, 3, 4)                                                 # the black moulding = body + both grips
GRIP_ID = {"out": 3, "in": 4}


def raycast(cam, side, pose, box, step_px):
    """Sphere-trace the solids for the pixels of box every step_px: ids index PARTS (0 body, 1 white cover, 2 switches,
    3 outboard grip, 4 inboard grip; -1 miss) -- the part whose field is smallest at the hit."""
    xs = np.arange(box[0], box[2], step_px) + 0.5 * step_px
    ys = np.arange(box[1], box[3], step_px) + 0.5 * step_px
    X, Y = np.meshgrid(xs, ys)
    d = cam.rays(np.c_[X.ravel(), Y.ravel()])
    Cl = from_model(cam.C[None, :], side, pose)[0]
    Dl = from_model(cam.C[None, :] + d * 0.1, side, pose) - Cl
    Dl /= np.linalg.norm(Dl, axis=1)[:, None]
    lo, hi = np.array([-160.0, -70.0, -90.0]), np.array([160.0, 110.0, 40.0])
    with np.errstate(divide="ignore", invalid="ignore"):
        t0, t1 = (lo - Cl) / Dl, (hi - Cl) / Dl
    tn = np.nanmax(np.minimum(t0, t1), axis=1)
    tf = np.nanmin(np.maximum(t0, t1), axis=1)
    t = np.maximum(tn, 0.0)
    alive = tf > tn
    hit = np.full(len(t), -1)
    for _ in range(110):
        idx = np.where(alive)[0]
        if not len(idx):
            break
        P = Cl + t[idx, None] * Dl[idx]
        vals = np.stack([G.part_sdf(p, P[:, 0], P[:, 1], P[:, 2]) for p in PARTS])
        s = vals.min(0)
        done = s < 0.08
        hit[idx[done]] = np.argmin(vals[:, done], axis=0)
        alive[idx[done]] = False
        t[idx[~done]] += np.maximum(0.85 * s[~done], 0.15)
        alive[idx[~done]] &= t[idx[~done]] < tf[idx[~done]]
    return xs, ys, hit.reshape(X.shape)


def id_contours(xs, ys, ids, keep):
    import contourpy
    m = ndi.gaussian_filter(np.isin(ids, keep).astype(float), 0.7)
    return [np.asarray(L) for L in contourpy.contour_generator(xs, ys, m).lines(0.5) if len(L) > 6]


# ------------------------------------------------------------------------------------------------ photo edges
def edge_along(g, p0, d, half, step=0.25, polarity=0, sigma=0.8):
    """Strongest intensity step along p0 + t d (|t| <= half px): (t, strength); polarity +1 bright -> dark."""
    t = np.arange(-half, half + step, step)
    d = np.asarray(d, float) / np.linalg.norm(d)
    P = np.asarray(p0, float)[None, :] + t[:, None] * d[None, :]
    v = ndi.map_coordinates(g, [P[:, 1] - 0.5, P[:, 0] - 0.5], order=1, mode="nearest")
    v = ndi.gaussian_filter1d(v, sigma / step)
    dv = np.gradient(v, step)
    s = -dv if polarity > 0 else (dv if polarity < 0 else np.abs(dv))
    i = int(np.argmax(s))
    off = 0.0
    if 0 < i < len(s) - 1:
        a, b, c = s[i - 1], s[i], s[i + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if den != 0 else 0.0
    return t[i] + off * step, float(s[i])


def _clean(y, x, thr):
    from scipy.interpolate import UnivariateSpline
    ok = ~np.isnan(x)
    for _ in range(6):
        if ok.sum() < 6:
            return np.zeros(len(x), bool)
        sp = UnivariateSpline(y[ok], x[ok], k=3, s=ok.sum() * 0.8)
        new = ~np.isnan(x) & (np.abs(x - sp(y)) < thr)
        if (new == ok).all():
            break
        ok = new
    return ok


def grip_rows(g_img, xs, ys, mask, ppm, axis_h, outer_left):
    """Per image row of a grip's ray-cast silhouette (mask): the photo's edges near the drawn ones -> residuals (+ =
    drawn wider) for the outer side and the slot side, with the axis height of each row."""
    rows = []
    for i in range(0, len(ys), 2):
        j = np.where(mask[i])[0]
        if len(j) < 3:
            continue
        y = ys[i]
        hw = 0.5 * (xs[1] - xs[0])
        xl, xr = xs[j[0]] - hw, xs[j[-1]] + hw
        sl, vl = edge_along(g_img, (xl, y), (1.0, 0.0), 8.0 * ppm, polarity=1)
        sr, vr = edge_along(g_img, (xr, y), (1.0, 0.0), 8.0 * ppm, polarity=-1)
        rows.append((y, xl, xl + sl if vl > 6 else np.nan, xr, xr + sr if vr > 6 else np.nan))
    R = np.array(rows)
    out = {}
    if not len(R):
        return out
    for col_m, col_p, sgn, left in ((1, 2, -1.0, True), (3, 4, 1.0, False)):
        ok = _clean(R[:, 0], R[:, col_p], 1.6 * ppm)
        hh = axis_h(R[:, 0])
        outer = left == outer_left
        lo, hi = (-38.0, 68.0) if outer else (-38.0, 14.0)
        sel = ok & (hh >= lo) & (hh <= hi)
        d = sgn * (R[sel, col_m] - R[sel, col_p]) / ppm
        out["outer" if outer else "slot"] = dict(h=hh[sel].tolist(), d=d.tolist(),
                                                pts=np.c_[R[sel, col_p], R[sel, 0]].tolist())
    return out


def curated_rows(ph, side, xs, ys, ids, cam, pose, ppm):
    """Residuals of the ray-cast grip silhouettes against the CURATED photo silhouette data (rev K, judges FID2-03 /
    04: refs/cache/.../measure/r3/sil2.pkl -- masked auto rows of the near-face-on views, hand-traced and snapped
    inboard slot sides, hand traces of the AOPA co-pilot view; the AOPA pilot view's auto rows are dropped: they lock
    onto the leather texture on the dark panel): {g: {kind: dict(h, d, pts)}} (+ = drawn wider / lower)."""
    f = MEAS / "r3" / "sil2.pkl"
    if not f.exists():
        return None
    data = pickle.load(open(f, "rb"))
    X = np.broadcast_to(xs[None, :], ids.shape)
    xm = cam(to_model(np.array([[0.0, 0.0, -10.0]]), side, pose))[0, 0]
    out = {}
    for g, sg in (("out", 1.0), ("in", -1.0)):
        xc = cam(to_model(np.array([[sg * 100.0, 0.0, -10.0]]), side, pose))[0, 0]
        mask = ids == GRIP_ID[g]                                     # the grip's own hits (rev K)
        outer_left = xc < xm
        hw = 0.5 * (xs[1] - xs[0])
        res = {}
        for kind in ("outer", "slot", "bottom"):
            D = data.get((ph, side, g, kind))
            if D is None or not len(D):
                continue
            hh, dd, pts = [], [], []
            for row in D:
                if kind == "bottom":
                    x, y = row[0], row[1]
                    j = int(np.argmin(np.abs(xs - x)))
                    i = np.where(mask[:, j])[0]
                    if not len(i):
                        continue
                    ym = ys[i[-1]] + hw
                    dd.append((ym - y) / ppm)
                    hh.append(float(x))
                else:
                    y, x, h = row[0], row[1], row[2]
                    i = int(np.argmin(np.abs(ys - y)))
                    j = np.where(mask[i])[0]
                    if not len(j):
                        continue
                    left = (kind == "outer") == outer_left
                    xm_ = xs[j[0]] - hw if left else xs[j[-1]] + hw
                    dd.append(((x - xm_) if left else (xm_ - x)) / ppm)
                    hh.append(float(h))
                pts.append((x, y))
            res[kind] = dict(h=hh, d=dd, pts=pts)
        out[g] = res
    return out


def band_stats(h, d, edges=(-50, -30, -10, 10, 30, 50, 70)):
    """Per-band (h) mean and max residual: [(lo, hi, n, mean, max)]."""
    h, d = np.asarray(h, float), np.asarray(d, float)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (h >= lo) & (h < hi)
        if m.any():
            out.append((lo, hi, int(m.sum()), float(d[m].mean()), float(d[m][np.argmax(np.abs(d[m]))])))
    return out


# ------------------------------------------------------------------------------------------------ feature curves
def pad_curve3(g, sg):
    """The drawn pad outline on grip g's aft plane, co-pilot sense (u, h, a), closed."""
    P = G.pad_outline(g)
    Q = np.c_[P, G.grip_plane_a(P[:, 0], P[:, 1], g)]
    return np.vstack([Q, Q[:1]]) * [sg, 1, 1]


def curves3():
    """{name: (N, 3)} feature polylines on the solids (co-pilot sense)."""
    from drawing import yoke_sheet as YS
    F = I.yoke_front_mm()
    D = I.YOKE_DESIGN
    out = {}
    for k in ("insert_upper", "insert_lower", "badge"):
        P = np.vstack([F[k], F[k][:1]])
        out[k] = np.c_[P, G.face_a(P[:, 1])]
    out["pad_out"] = pad_curve3("out", 1.0)
    out["pad_in"] = pad_curve3("in", -1.0)
    tp = YS.trim_pieces()
    out["trim_face"] = np.vstack([tp["face"], tp["face"][:1]])
    out["trim_ring"] = np.vstack([tp["ring"], tp["ring"][:1]])
    bp = YS.button_pieces()
    out["shield"] = np.vstack([bp["shield"], bp["shield"][:1]])
    out["hex"] = np.vstack([bp["hex"], bp["hex"][:1]])
    t = np.linspace(0, 2 * np.pi, 61)
    for nm, c, r, aoff in (("tcs", D["tcs"], 0.5 * float(D["tcs"][2]), 0.0),
                           ("afcs", D["afcs"], 0.5 * float(D["afcs"][2]), -float(D["cover_t"]) + float(D["afcs"][3])),
                           ("afcs_boss", D["afcs"], 0.5 * float(D["afcs"][4]), -float(D["cover_t"]) + 1.5)):
        P = np.c_[float(c[0]) + r * np.cos(t), float(c[1]) + r * np.sin(t)]
        out[nm] = np.c_[P, G.face_a(P[:, 1]) + aoff]
    return out


STYLE = {"cover": (0, 230, 255), "black": (80, 160, 255), "insert": (255, 220, 0), "badge": (255, 220, 0),
         "pad": (255, 120, 255), "trim": (255, 255, 255), "shield": (255, 255, 255), "hex": (255, 80, 80),
         "tcs": (255, 80, 80), "afcs": (255, 80, 80), "trace": (255, 0, 200)}


def _style(nm):
    for k, v in STYLE.items():
        if nm.startswith(k):
            return v
    return (255, 80, 80)


def _seg_dist(q, P):
    a, b = P[:-1], P[1:]
    ab = b - a
    L2 = np.maximum((ab * ab).sum(1), 1e-12)
    t = np.clip(((q[:, None, :] - a[None]) * ab[None]).sum(2) / L2[None], 0, 1)
    d = q[:, None, :] - (a[None] + t[..., None] * ab[None])
    return np.sqrt((d * d).sum(2)).min(1)


def shell_snap(g_img, cam, side, pose, ppm):
    """Shell outline (on the face) snapped to the photo (+-4 mm): signed mean offset by region (+ = photo outside)."""
    sh = np.asarray(I.YOKE_DESIGN["shell_half"], float)
    Q = G.shell_outline()
    regions = dict(crown=range(0, 5), chamfer=range(5, 11), arm_top=range(11, 22), tip=range(22, 24),
                   arm_lower=range(24, 36), stem=range(36, 45), foot=range(45, 49))
    out = {}
    for nm, idx in regions.items():
        vals = {1: [], -1: []}
        for sg in (1, -1):
            for i in idx:
                u, h = sg * sh[i, 0], sh[i, 1]
                j = int(np.argmin(np.hypot(Q[:, 0] - u, Q[:, 1] - h)))
                t = Q[(j + 3) % len(Q)] - Q[j - 3]
                n2 = np.array([t[1], -t[0]]) / np.linalg.norm(t)
                if np.dot(n2, Q[j] - np.array([0.0, 20.0])) < 0:
                    n2 = -n2
                p3 = np.array([Q[j, 0], Q[j, 1], float(G.face_a(Q[j, 1]))])
                q0, q1 = cam(to_model(np.vstack([p3, p3 + np.r_[n2, 0.0]]), side, pose))
                d = q1 - q0
                s, _ = edge_along(g_img, q0, d, 4.0 * ppm)
                vals[sg].append(s / np.linalg.norm(d))
        out[nm] = dict(outboard=float(np.mean(vals[1])), inboard=float(np.mean(vals[-1])))
    return out


def neck_check(g_img, xs, ys, ids, cam, side, pose, ppm):
    """P1046408: the inboard neck's top edge between the white arm tip and the inboard head: per pixel column the
    drawn black moulding's top edge vs the photo's strongest vertical edge within +-8 mm (+ = drawn high), mm."""
    a_tip = cam(to_model(np.array([[-74.0, 54.0, float(G.face_a(54.0))]]), side, pose))[0]
    c_in = G.head_in_face()[0] * [-1, 1, 1]
    a_head = cam(to_model(np.array([[c_in[0] + 15.0, 68.0, c_in[2]]]), side, pose))[0]
    x0, x1 = sorted([a_tip[0], a_head[0]])
    res, pts = [], []
    for x in np.arange(x0 + 1.0, x1 - 1.0, 1.0):
        j = int(np.argmin(np.abs(xs - x)))
        col = np.isin(ids[:, j], BLACK)
        if not col.any():
            continue
        y_top = ys[np.where(col)[0][0]] - 0.5 * (ys[1] - ys[0])
        s, _ = edge_along(g_img, (x, y_top), (0.0, 1.0), 8.0 * ppm)
        res.append(s / ppm)
        pts.append((x, y_top + s))
    r = np.array(res)
    return dict(mean=float(np.mean(r)), mean_abs=float(np.mean(np.abs(r))), max=float(r[np.argmax(np.abs(r))]),
                n=len(r), pts=pts)


# ------------------------------------------------------------------------------------------------ one photo
def render(ph, side, cams, picks, box, step_px, title, traces):
    cam = cams[ph]
    feat = features()
    pose = fit_pose(cam, picks, feat, side)
    ppm = px_per_mm(cam, side, pose)
    im = Image.open(IMG[ph]).convert("RGB")
    if im.size != (cam.W, cam.H):                                     # the AOPA copy of the press photo
        im = im.resize((cam.W, cam.H), Image.LANCZOS)
    g_img = np.asarray(im, float).mean(2)
    xs, ys, ids = raycast(cam, side, pose, box, step_px)
    k = max(1, int(round(1300 / (box[2] - box[0]))))
    crop = im.crop(box).resize(((box[2] - box[0]) * k, (box[3] - box[1]) * k), Image.LANCZOS)
    a = np.asarray(crop, float) / 255.0
    crop = Image.fromarray((np.clip(0.15 + 0.85 * a ** 0.85, 0, 1) * 255).astype(np.uint8))
    dr = ImageDraw.Draw(crop)

    def to(uv):
        return [((u - box[0]) * k, (v - box[1]) * k) for u, v in uv]
    for keep, col in (([1], STYLE["cover"]), ([0, 1, 2, 3, 4], STYLE["black"])):
        for L in id_contours(xs, ys, ids, keep):
            dr.line(to(L), fill=col, width=2)
    for nm, P in curves3().items():
        dr.line(to(cam(to_model(P, side, pose))), fill=_style(nm), width=1)
    rep = dict(pose=[float(x) for x in pose], px_per_mm=ppm)
    lm = {}
    for f, uv in picks.items():
        if f not in feat:
            continue
        q = cam(to_model(feat[f][None, :], side, pose))[0]
        e = float(np.hypot(*(q - np.asarray(uv)))) / ppm
        lm[f] = e
        p = to([uv])[0]
        dr.line([(p[0] - 6, p[1] - 6), (p[0] + 6, p[1] + 6)], fill=(255, 40, 40), width=2)
        dr.line([(p[0] - 6, p[1] + 6), (p[0] + 6, p[1] - 6)], fill=(255, 40, 40), width=2)
        qq = to([q])[0]
        dr.ellipse([qq[0] - 5, qq[1] - 5, qq[0] + 5, qq[1] + 5], outline=(255, 255, 255), width=2)
        dr.text((p[0] + 8, p[1] + 4), f"{f} {e:.1f}", fill=(255, 255, 0) if e > 3.0 else (180, 255, 180), font=FONT)
    rep["landmarks_mm"] = lm
    gr = {}
    X = np.broadcast_to(xs[None, :], ids.shape)
    xm = cam(to_model(np.array([[0.0, 0.0, -10.0]]), side, pose))[0, 0]
    for g, sg in (("out", 1.0), ("in", -1.0)):
        hs = np.linspace(-45, 100, 146)
        qa = cam(to_model(np.c_[sg * G.grip_axis_u(hs), hs, np.full_like(hs, -10.0)], side, pose))
        o = np.argsort(qa[:, 1])

        def axis_h(y, qa=qa, o=o, hs=hs):
            return np.interp(y, qa[o, 1], hs[o])
        xc = cam(to_model(np.array([[sg * 100.0, 0.0, -10.0]]), side, pose))[0, 0]
        mask = ids == GRIP_ID[g]
        gr[g] = grip_rows(g_img, xs, ys, mask, ppm, axis_h, xc < xm)
        for v in gr[g].values():
            for x_, y_ in v["pts"]:
                p = to([(x_, y_)])[0]
                dr.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], outline=STYLE["trace"], width=1)
    cur = curated_rows(ph, side, xs, ys, ids, cam, pose, ppm)
    if cur is not None:
        gr = cur
        for v in [v for d_ in cur.values() for v in d_.values()]:
            for x_, y_ in v["pts"]:
                p = to([(x_, y_)])[0]
                dr.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], outline=(255, 255, 0), width=1)
    rep["grip_rows_mm"] = {
        g: {s_: dict(n=len(v["d"]), mean=float(np.mean(v["d"])) if v["d"] else None,
                     rms=float(np.sqrt(np.mean(np.square(v["d"])))) if v["d"] else None,
                     max=float(np.asarray(v["d"])[np.argmax(np.abs(v["d"]))]) if v["d"] else None,
                     bands=band_stats(v["h"], v["d"]) if s_ != "bottom" else None,
                     rows=[[round(h, 1), round(d, 2)] for h, d in zip(v["h"], v["d"])])
            for s_, v in d_.items()} for g, d_ in gr.items()}
    pads = {}
    for g, sg in (("out", 1.0), ("in", -1.0)):
        tr = traces.get((ph, side, g))
        if tr is None:
            continue
        closed = True
        if isinstance(tr, tuple):
            tr, closed = tr
        q = cam(to_model(pad_curve3(g, sg), side, pose))
        tq = np.asarray(tr, float)
        dr.line(to(np.vstack([tq, tq[:1]]) if closed else tq), fill=STYLE["trace"], width=1)
        dd = _seg_dist(tq, q) / ppm
        pads[g] = dict(mean=float(np.mean(dd)), max=float(np.max(dd)))
    rep["pads_mm"] = pads
    rep["shell_mm"] = shell_snap(g_img, cam, side, pose, ppm)
    if ph == "p408":
        nk = neck_check(g_img, xs, ys, ids, cam, side, pose, ppm)
        for x_, y_ in nk.pop("pts"):
            p = to([(x_, y_)])[0]
            dr.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], outline=(255, 255, 0), width=1)
        rep["neck_mm"] = nk
    W = crop.width
    lines = [title, f"fitted pose (cover landmarks only): dx {pose[0] * 1000:+.0f} mm, dy {pose[1] * 1000:+.1f}, dz "
                    f"{pose[2] * 1000:+.1f}, roll {pose[3]:+.1f} deg; {ppm:.2f} px/mm at the hub",
             "landmarks mm: " + ", ".join(f"{f} {v:.1f}" for f, v in lm.items())]
    for g, d_ in rep["grip_rows_mm"].items():
        lines.append(f"grip {g}: " + "; ".join(f"{s_} n {v['n']} mean {v['mean']:+.1f} max {v['max']:+.1f}"
                                               for s_, v in d_.items() if v["n"]) + " mm (+ = drawn wider / lower)")
    if pads:
        lines.append("pads vs traces: " + "; ".join(f"{g} {v['mean']:.1f} / {v['max']:.1f}" for g, v in pads.items())
                     + " mm (mean / max)")
    if "neck_mm" in rep:
        nk = rep["neck_mm"]
        lines.append(f"inboard neck top edge: mean {nk['mean']:+.1f}, |mean| {nk['mean_abs']:.1f}, max {nk['max']:+.1f} "
                     f"mm over {nk['n']} columns (+ = drawn high)")
    hh = 22 * len(lines) + 8
    canvas = Image.new("RGB", (W, crop.height + hh + 26), (0, 0, 0))
    canvas.paste(crop, (0, hh))
    d2 = ImageDraw.Draw(canvas)
    for i, ln in enumerate(lines):
        d2.text((8, 4 + 22 * i), ln, fill=(255, 255, 255) if i else (255, 230, 120), font=FONT_B if i == 0 else FONT)
    d2.text((8, hh + crop.height + 4), "ray-cast: cyan white cover / blue black moulding; yellow inserts + badge, "
            "pink pads, white trim face + shield, red switches; magenta: photo edges / pad traces; yellow o: neck "
            "edge; red x picks, white o drawn landmarks", fill=(200, 200, 200), font=FONT)
    return canvas, rep


JOBS = [("p408", -1, "L", (240, 690, 680, 960), 1.0, "P1046408 pilot yoke through panel_408"),
        ("press", 1, "R", (2680, 1780, 3220, 2260), 1.5, "AOPA / Pilatus press photo, co-pilot yoke from aft-INBOARD "
                                                         "(~54 deg)"),
        ("p408", 1, "R", (1260, 690, 1720, 960), 1.0, "P1046408 co-pilot yoke through panel_408"),
        ("mex", -1, "L", (1800, 1750, 3000, 2650), 3.0, "Mexico press photo, pilot yoke (bundle-adj. camera)"),
        ("mex", 1, "R", (4600, 1700, 5950, 2650), 3.0, "Mexico press photo, co-pilot yoke (bundle-adj. camera)"),
        ("press", -1, "L", (1050, 1950, 2350, 2950), 3.0, "AOPA / Pilatus press photo, pilot yoke from aft-outboard"),
        ("p410", -1, "L", (480, 1150, 1200, 1650), 1.5, "P1046410 pilot yoke (bundle-adj. camera)")]
TRACES = ((("p408", -1, "out"), "P408L_PAD_OUT"), (("p408", -1, "in"), "P408L_PAD_IN"),
          (("p408", 1, "out"), "P408R_PAD_OUT"), (("p408", 1, "in"), "P408R_PAD_IN"),
          (("mex", -1, "in"), "MEXL_PAD_IN"), (("press", -1, "out"), "PRESSL_PAD_OUT"),
          (("press", -1, "in"), "PRESSL_PAD_IN"))
TRACES3 = ((("press", 1, "in"), "PRESSR_PAD_IN", True), (("mex", 1, "out"), "MEXR_PAD_OUT", False))
# extra cover picks of the AOPA co-pilot view (r2: the step ends and the lower insert's bottom corners; the r2 judges'
# run had tcs / red / foot only)
EXTRA_PICKS = {("press", "R"): dict(stp_i=(2931.0, 2016.0), stp_o=(2952.0, 2010.0), inb_i=(2939.0, 2046.0),
                                    inb_o=(2954.0, 2041.0))}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    OUT.mkdir(parents=True, exist_ok=True)
    cams = cameras()
    PK = _load("picks2", MEAS / "depth_scripts" / "picks2.py").YOKE
    traces = {}
    tf = MEAS / "r2" / "traces.py"
    if tf.exists():
        tr_mod = _load("traces_r2", tf)
        traces = {key: getattr(tr_mod, nm) for key, nm in TRACES if hasattr(tr_mod, nm)}
    tf3 = MEAS / "r3" / "traces3.py"
    if tf3.exists():
        t3 = _load("traces_r3", tf3)
        traces.update({key: (getattr(t3, nm), closed) for key, nm, closed in TRACES3 if hasattr(t3, nm)})
    report = {}
    for ph, side, sd, box, step, title in JOBS:
        if argv and ph not in argv:
            continue
        picks = {f: v for f, v in dict(PK.get((ph, sd), {}), **EXTRA_PICKS.get((ph, sd), {})).items()
                 if not f.startswith("j")}
        img, rep = render(ph, side, cams, picks, box, step, title, traces)
        name = f"yoke_{ph}_{'pilot' if side < 0 else 'copilot'}.png"
        img.save(OUT / name)
        report[name] = rep
        print(f"{name}: pose {np.round(rep['pose'], 4)}  landmarks " +
              ", ".join(f"{f} {v:.1f}" for f, v in rep["landmarks_mm"].items()))
        for g, d_ in rep["grip_rows_mm"].items():
            for s_, v in d_.items():
                if v["n"]:
                    b = " ".join(f"{lo}..{hi}:{mn:+.1f}/{mx:+.1f}" for lo, hi, n, mn, mx in (v["bands"] or []))
                    print(f"    grip {g} {s_:6s} n {v['n']:3d} mean {v['mean']:+5.1f} max {v['max']:+5.1f}  {b}")
        for g, v in rep["pads_mm"].items():
            print(f"    pad {g} mean {v['mean']:.1f} max {v['max']:.1f}")
        print("    shell " + ", ".join(f"{k} {v['outboard']:+.1f}/{v['inboard']:+.1f}" for k, v in rep["shell_mm"].items()))
        if "neck_mm" in rep:
            print(f"    neck {rep['neck_mm']}")
    old = {}
    if argv and (OUT / "deviations.json").exists():
        old = json.loads((OUT / "deviations.json").read_text())
    old.update(report)
    (OUT / "deviations.json").write_text(json.dumps(old, indent=1))


if __name__ == "__main__":
    main()
