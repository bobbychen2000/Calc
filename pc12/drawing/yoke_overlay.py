"""
Photo overlays of the yoke design drawing (sheet L6Y, interior.YOKE_DESIGN) -- PRIVATE REFERENCE, git-ignored output.

The drawn yoke is placed in 3-D from its parameters (front outlines on the aft face: the 17.5 deg upper face, the convex
lower face, the raked / toed-out grips and the trim head's facet; interior.yoke_* helpers) and projected through the
fitted cameras of the photos:

    P1046408   cams_beauty.json 'panel_408' (the one calibrated face-on view), both yokes
    Mexico     the Pilatus press photo pil_Mexico_PC12PRO_8 (bundle-adjustment camera of the 2026-10-05 depth
               measurement), both yokes
    AOPA       fd_aopa_pro_cockpit.jpg (= the Pilatus press photo pil_PC-12-PRO-Cockpit), pilot yoke (same camera)
    P1046410   bundle-adjustment camera, pilot yoke

Only the yoke's photo POSE is fitted (fore-aft dx, lateral dy, vertical dz, roll -- the photos show the gust-locked /
hand-held column, never the drawn neutral) to the landmark picks of the depth measurement (TCS, AFCS cap, trim ring,
inboard button, badge, step ends, lower-insert corners, foot); the shape is the drawing's.  Deviations: on P1046408 the
traced edges of the front measurement (front_data.py, rectified through panel_408) are mapped back to pixels and their
distance to the drawn outlines is reported in mm per region; on the other photos the landmark residuals.

    python3 -m drawing.yoke_overlay            -> refs/cache/overlays/yoke/*.png (+ deviations.json)

Inputs (all git-ignored, refs/cache): photos/interior, fd_research/yoke/measure/{work,depth_scripts}.  No photo and no
overlay that embeds one is ever written outside refs/cache.
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
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model import interior as I  # noqa: E402

CACHE = ROOT / "refs" / "cache"
MEAS = CACHE / "fd_research" / "yoke" / "measure"
OUT = CACHE / "overlays" / "yoke"
IMG = {"p408": CACHE / "photos/interior/fd_commons_pro3001_P1046408.jpg",
       "p410": CACHE / "photos/interior/fd_commons_pro3001_P1046410.jpg",
       "mex": CACHE / "fd_research/pc12pro_layout/pilnews/pil_Mexico_PC12PRO_8.jpg",
       "press": CACHE / "photos/interior/fd_aopa_pro_cockpit.jpg"}
FEATS = ("tcs", "red", "trim", "hbtn", "badge", "stp_o", "stp_i", "inb_o", "inb_i", "foot")
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


def cameras():
    cb = json.loads((CACHE / "overlays/vqa/cams_beauty.json").read_text())
    B = pickle.load(open(MEAS / "depth_scripts" / "ba5_cl.pkl", "rb"))
    WH = {"p408": (1920, 1440), "p410": (1920, 2560), "mex": (7657, 5170), "press": (5000, 3335)}
    cams = {"p408": Cam(cb["panel_408"]["p"], 1920, 1440)}
    for k in ("p410", "mex", "press"):
        cams[k] = Cam(B["Q"][k], *WH[k])
    cams["p408_ba"] = Cam(B["Q"]["p408"], 1920, 1440)
    return cams


# ------------------------------------------------------------------------------------------------ the 3-D design
def _face_pt(u, h, back=0.0):
    return np.c_[np.asarray(u, float), np.asarray(h, float), I.yoke_face_a(h) - back]


def _circle3(c, n, r, k=48):
    n = np.asarray(n, float) / np.linalg.norm(n)
    e1 = np.cross(n, [0.0, 0.0, 1.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    t = np.linspace(0, 2 * np.pi, k)
    return c[None, :] + r * (np.cos(t)[:, None] * e1 + np.sin(t)[:, None] * e2)


def design3d():
    """{name: (N, 3) (u, h, a) mm} polylines of the drawn yoke (copilot sense: u outboard; the inboard grip at u < 0),
    plus 'feat': {pick name: (u, h, a)}."""
    D = I.YOKE_DESIGN
    F = I.yoke_front_mm()
    out = {}
    for k in ("shell", "insert_upper", "insert_lower", "badge"):
        P = np.vstack([F[k], F[k][:1]])
        out[k] = _face_pt(P[:, 0], P[:, 1])
    out["step"] = _face_pt(F["step"][:, 0], F["step"][:, 1])
    bh = np.asarray(D["body_half"], float)
    cover = float(D["cover_t"])
    for sg in (1, -1):
        rim = bh[20:] * [sg, 1]
        out[f"rim{sg:+d}"] = _face_pt(rim[:, 0], rim[:, 1], cover)
        slot = bh[12:21] * [sg, 1]
        out[f"slot{sg:+d}"] = _face_pt(slot[:, 0], slot[:, 1], cover)
        neck = bh[3:10]
        a0 = float(I.yoke_face_a(neck[0, 1])) - cover
        a1 = float(I.yoke_grip_aft_a(neck[-1, 0], neck[-1, 1], "out" if sg > 0 else "in"))
        t = np.linspace(0, 1, len(neck))
        out[f"neck{sg:+d}"] = np.c_[neck[:, 0] * sg, neck[:, 1], a0 + t * (a1 - a0)]
    from cad import sdf2d
    hf = I.yoke_head_facet()
    for sg, nm in ((1, "out"), (-1, "in")):
        gf = I.yoke_grip_faces(nm)
        S, G = gf["S"], gf["G"]
        v, da = I.yoke_grip_shift(nm)
        fwd = sdf2d.polygon(S[:, 0] - v[0], S[:, 1] - v[1], S) < -1.0
        a_S = np.where(fwd, I.yoke_grip_aft_a(S[:, 0] - v[0], S[:, 1], nm) + da, I.yoke_grip_aft_a(S[:, 0], S[:, 1], nm))
        P = np.c_[S[:, 0], S[:, 1], a_S]
        out[f"grip_{nm}"] = np.vstack([P, P[:1]]) * [sg, 1, 1]
        Pg = np.c_[G[:, 0], G[:, 1], I.yoke_grip_aft_a(G[:, 0], G[:, 1], nm)]
        out[f"aft_{nm}"] = np.vstack([Pg, Pg[:1]]) * [sg, 1, 1]
        pad = gf["pad"]
        Pp = np.c_[pad[:, 0], pad[:, 1], I.yoke_grip_aft_a(pad[:, 0], pad[:, 1], nm) + 1.0]
        out[f"pad_{nm}"] = np.vstack([Pp, Pp[:1]]) * [sg, 1, 1]
    # the trim head's facet + ring (outboard), the inboard button collar
    s = 0.5 * hf["size"]
    sq = sdf2d.rrect_outline(0.0, 0.0, s, s, 4.0, n_corner=6)
    Q = hf["c"][None, :] + sq[:, :1] * hf["eu"][None, :] + sq[:, 1:2] * hf["ev"][None, :]   # (a, u, h)
    fac = np.c_[Q[:, 1], Q[:, 2], Q[:, 0]]
    out["facet"] = np.vstack([fac, fac[:1]])
    ring = _circle3(hf["c"], hf["n"], 0.5 * float(D["trim"][2]))
    out["trim_ring"] = np.c_[ring[:, 1], ring[:, 2], ring[:, 0]]
    tu, th = D["tcs"][:2]
    tn = np.array([math.cos(math.radians(D["face_tilt"])), 0.0, math.sin(math.radians(D["face_tilt"]))])
    c_t = np.array([float(I.yoke_face_a(th)), tu, th])
    ring = _circle3(c_t, tn, 0.5 * float(D["tcs"][2]))
    out["tcs"] = np.c_[ring[:, 1], ring[:, 2], ring[:, 0]]
    au, ah = D["afcs"][:2]
    c_a = np.array([float(I.yoke_face_a(ah)) - cover + 0.5 * float(D["afcs"][3]), au, ah])
    ring = _circle3(c_a, tn, 0.5 * float(D["afcs"][2]))
    out["afcs"] = np.c_[ring[:, 1], ring[:, 2], ring[:, 0]]
    bu, bhh = D["button"][:2]
    n_g = I.yoke_grip_normal("in") * [1, -1, 1]                      # (a, u, h) of the inboard grip (u < 0)
    c_b = np.array([float(I.yoke_grip_aft_a(bu, bhh, "in")), -bu, bhh])
    ring = _circle3(c_b, n_g, 0.5 * float(D["button"][2]))
    out["button"] = np.c_[ring[:, 1], ring[:, 2], ring[:, 0]]
    feat = dict(tcs=(tu, th, float(I.yoke_face_a(th))), red=(au, ah, float(I.yoke_face_a(ah)) - cover + 0.8 * float(D["afcs"][3])),
                trim=(hf["c"][1], hf["c"][2], hf["c"][0]), hbtn=tuple(np.array([-bu, bhh, c_b[0]])
                                                             + float(D["button"][4]) * n_g[[1, 2, 0]]),
                badge=(0.0, 49.65, float(I.yoke_face_a(49.65))),
                stp_o=(12.9, 4.1, 0.0), stp_i=(-12.9, 4.1, 0.0),
                inb_o=(8.8, -17.6, float(I.yoke_face_a(-17.6))), inb_i=(-8.8, -17.6, float(I.yoke_face_a(-17.6))),
                foot=(0.0, -56.0, float(I.yoke_face_a(-56.0))))
    out["feat"] = {k: np.array(v, float) for k, v in feat.items()}
    return out


def to_model(P, side, pose):
    """(u, h, a) mm -> model (x, y, z) m for the yoke on `side` in the photo pose (dx, dy, dz m, roll deg)."""
    dx, dy, dz, rho = pose
    P = np.atleast_2d(P)
    hub = I.yoke_hub(side)
    x_ref = float(hub[0] + I.YOKE["hub_whd"][2])
    yl, zl = side * P[:, 0] * 1e-3, P[:, 1] * 1e-3
    c, s = math.cos(math.radians(rho)), math.sin(math.radians(rho))
    return np.c_[x_ref + dx + P[:, 2] * 1e-3, hub[1] + dy + yl * c - zl * s, hub[2] + dz + yl * s + zl * c]


def fit_pose(cam, picks, feat, side, sig_px=2.0):
    """Least-squares yoke pose (dx, dy, dz, roll) putting the design's features on the picks; returns (pose,
    residuals {feature: px})."""
    names = [k for k in FEATS if k in picks and k in feat]
    U = np.array([picks[k] for k in names], float)
    X0 = np.array([feat[k] for k in names])

    def res(p):
        return ((cam(to_model(X0, side, p)) - U) / sig_px).ravel()
    sol = least_squares(res, np.zeros(4), loss="soft_l1", x_scale=[0.02, 0.01, 0.01, 2.0])
    r = (cam(to_model(X0, side, sol.x)) - U)
    return sol.x, {k: tuple(v) for k, v in zip(names, r)}


def px_per_mm(cam, side, pose, at=(0.0, 0.0, 0.0)):
    P = np.array([at, np.add(at, (10.0, 0, 0)), np.add(at, (0, 10.0, 0))], float)
    q = cam(to_model(P, side, pose))
    return 0.5 * (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[0])) / 10.0


# ------------------------------------------------------------------------------------------------ measured traces
def traces_p408(side):
    """The front measurement's traced edges (front_data.py, local mm on its rectification plane) mapped back to
    P1046408 pixels through panel_408 for the yoke on `side` (pilot -1 / co-pilot +1)."""
    fd = _load("front_data", MEAS / "work" / "front_data.py")
    rect = _load("rect", MEAS / "work" / "rect.py")
    cam = rect.Cam("panel_408")
    T = {"shell out": fd.SHELL_OBS_OUTBOARD, "shell in": fd.SHELL_OBS_INBOARD, "insert": fd.INS_UP,
         "lower insert": fd.INS_LO, "badge": fd.BADGE, "rim": fd.RIM_HALF, "slot out": fd.SLOT_OUT,
         "slot in (seen)": fd.SLOT_IN_OBS, "neck out": fd.NECK_OUT, "neck in": fd.NECK_IN,
         "grip out": fd.GRIP_OUT, "grip in": fd.GRIP_IN, "pad in": fd.PAD_IN}
    return {k: cam.proj(rect.local2model_t(np.asarray(v, float), side)) for k, v in T.items()}


# region of the drawing each trace is compared with
TRACE_VS = {"shell out": ("shell",), "shell in": ("shell",), "insert": ("insert_upper",),
            "lower insert": ("insert_lower",), "badge": ("badge",), "rim": ("rim+1", "rim-1"),
            "slot out": ("slot+1", "rim+1", "grip_out"), "slot in (seen)": ("slot-1", "rim-1", "grip_in"),
            "neck out": ("neck+1",), "neck in": ("neck-1",), "grip out": ("grip_out",), "grip in": ("grip_in",),
            "pad in": ("pad_in",)}


def _seg_dist(q, P):
    """Distance from each point q (M, 2) to the polyline P (N, 2)."""
    a, b = P[:-1], P[1:]
    ab = b - a
    L2 = np.maximum((ab * ab).sum(1), 1e-12)
    t = np.clip(((q[:, None, :] - a[None]) * ab[None]).sum(2) / L2[None], 0, 1)
    d = q[:, None, :] - (a[None] + t[..., None] * ab[None])
    return np.sqrt((d * d).sum(2)).min(1)


# ------------------------------------------------------------------------------------------------ drawing
STYLE = {"shell": ((0, 230, 255), 3), "insert_upper": ((255, 220, 0), 2), "insert_lower": ((255, 170, 0), 2),
         "step": ((255, 170, 0), 2), "badge": ((255, 220, 0), 2), "grip": ((0, 255, 120), 3),
         "aft": ((0, 200, 90), 1), "pad": ((255, 120, 255), 2), "facet": ((255, 255, 255), 2),
         "body": ((80, 160, 255), 3), "sw": ((255, 80, 80), 2), "trace": ((255, 0, 200), 2)}


def _style(name):
    for k, v in STYLE.items():
        if name.startswith(k):
            return v
    if name.startswith(("rim", "slot", "neck")):
        return STYLE["body"]
    return STYLE["sw"]


def render(ph, side, cams, picks, box, k, title, traces=None, cam_key=None):
    cam = cams[cam_key or ph]
    d3 = design3d()
    pose, res = fit_pose(cam, picks, d3["feat"], side)
    ppm = px_per_mm(cam, side, pose)
    im = Image.open(IMG[ph]).convert("RGB")
    if ph == "press" and im.size != (cam.W, cam.H):              # the AOPA copy of the press photo
        im = im.resize((cam.W, cam.H), Image.LANCZOS)
    crop = im.crop(box)
    crop = crop.resize(((box[2] - box[0]) * k, (box[3] - box[1]) * k), Image.LANCZOS)
    a = np.asarray(crop, float) / 255.0
    crop = Image.fromarray((np.clip(0.15 + 0.85 * a ** 0.85, 0, 1) * 255).astype(np.uint8))
    dr = ImageDraw.Draw(crop)

    def to(uv):
        return [((u - box[0]) * k, (v - box[1]) * k) for u, v in uv]
    proj = {}
    for nm, P in d3.items():
        if nm == "feat":
            continue
        q = cam(to_model(P, side, pose))
        proj[nm] = q
        col, w = _style(nm)
        dr.line(to(q), fill=col, width=w)
    dev = {}
    if traces:
        for tn, q in traces.items():
            dr.line(to(q), fill=STYLE["trace"][0], width=1)
            P = np.vstack([proj[n] for n in TRACE_VS[tn]])
            # distance to the union of the compared outlines (pieces kept apart)
            dd = np.min(np.stack([_seg_dist(q, proj[n]) for n in TRACE_VS[tn]]), axis=0) / ppm
            dev[tn] = (float(np.mean(dd)), float(np.max(dd)), q[int(np.argmax(dd))].tolist())
            del P
    for f, uv in picks.items():
        if f not in d3["feat"]:
            continue
        p = to([uv])[0]
        dr.line([(p[0] - 6, p[1] - 6), (p[0] + 6, p[1] + 6)], fill=(255, 40, 40), width=2)
        dr.line([(p[0] - 6, p[1] + 6), (p[0] + 6, p[1] - 6)], fill=(255, 40, 40), width=2)
        q = to(cam(to_model(d3["feat"][f][None, :], side, pose)))[0]
        dr.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], outline=(255, 255, 255), width=2)
        if f in res:
            e = math.hypot(*res[f]) / ppm
            dr.text((p[0] + 8, p[1] + 4), f"{e:.1f}", fill=(255, 255, 0) if e > 3.0 else (180, 255, 180), font=FONT)
    # call-outs
    W = crop.width
    lines = [title,
             f"fitted pose: dx {pose[0] * 1000:+.0f} mm (fwd -), dy {pose[1] * 1000:+.1f}, dz {pose[2] * 1000:+.1f}, "
             f"roll {pose[3]:+.1f} deg; {ppm:.2f} px/mm at the hub",
             "landmarks (pick x vs drawn o): " + ", ".join(f"{f} {math.hypot(*r) / ppm:.1f}" for f, r in res.items())
             + " mm"]
    if dev:
        lines.append("traced edges vs drawing, mean / max mm: " + "; ".join(f"{t} {m:.1f}/{x:.1f}"
                                                                           for t, (m, x, _) in dev.items()))
    wrapped = []
    for ln in lines:
        while len(ln) > 150:
            cut = ln.rfind(" ", 0, 150)
            wrapped.append(ln[:cut])
            ln = "    " + ln[cut + 1:]
        wrapped.append(ln)
    hh = 22 * len(wrapped) + 8
    canvas = Image.new("RGB", (W, crop.height + hh + 26), (0, 0, 0))
    canvas.paste(crop, (0, hh))
    d2 = ImageDraw.Draw(canvas)
    for i, ln in enumerate(wrapped):
        d2.text((8, 4 + 22 * i), ln, fill=(255, 255, 255) if i else (255, 230, 120), font=FONT_B if i == 0 else FONT)
    d2.text((8, hh + crop.height + 4), "cyan shell / yellow insert + badge / blue body rim, slot, necks / green grip "
            "silhouette (thin: aft face) / pink pad / white trim facet / red switches / magenta thin: traced edges "
            "(P1046408) / red x picks, white o drawn landmarks", fill=(200, 200, 200), font=FONT)
    if dev:
        for t, (m, x, at) in dev.items():
            if x > 3.0:
                p = to([at])[0]
                d2.text((p[0] + 8, p[1] + hh - 8), f"{t} {x:.1f}", fill=(255, 0, 200), font=FONT)
    return canvas, dict(pose=[float(v) for v in pose], px_per_mm=ppm,
                        landmarks_mm={f: math.hypot(*r) / ppm for f, r in res.items()},
                        traces_mm={t: dict(mean=m, max=x) for t, (m, x, _) in dev.items()})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cams = cameras()
    PK = _load("picks2", MEAS / "depth_scripts" / "picks2.py")
    Y = PK.YOKE
    jobs = [("p408", -1, "L", (250, 640, 690, 980), 3, "P1046408 pilot yoke through panel_408", True, None),
            ("p408", 1, "R", (1260, 630, 1720, 980), 3, "P1046408 co-pilot yoke through panel_408", True, None),
            ("mex", -1, "L", (1800, 1750, 3000, 2600), 1, "Mexico press photo, pilot yoke (bundle-adj. camera)",
             False, None),
            ("mex", 1, "R", (4600, 1700, 5900, 2600), 1, "Mexico press photo, co-pilot yoke (bundle-adj. camera)",
             False, None),
            ("press", -1, "L", (1050, 1950, 2350, 2900), 1, "AOPA / Pilatus press photo, pilot yoke from aft-outboard",
             False, None),
            ("p410", -1, "L", (480, 1100, 1180, 1620), 2, "P1046410 pilot yoke (bundle-adj. camera)", False, None)]
    report = {}
    for ph, side, sd, box, k, title, tr, ck in jobs:
        picks = {f: v for f, v in Y.get((ph, sd), {}).items() if not f.startswith("j")}
        traces = traces_p408(side) if tr else None
        img, rep = render(ph, side, cams, picks, box, k, title, traces, ck)
        name = f"yoke_{ph}_{'pilot' if side < 0 else 'copilot'}.png"
        img.save(OUT / name)
        report[name] = rep
        print(f"{name}: pose {np.round(rep['pose'], 4)}  landmarks " +
              ", ".join(f"{f} {v:.1f}" for f, v in rep["landmarks_mm"].items()))
        for t, v in rep["traces_mm"].items():
            print(f"    {t:16s} mean {v['mean']:4.1f}  max {v['max']:4.1f} mm")
    (OUT / "deviations.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
