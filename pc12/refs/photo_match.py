"""
refs.photo_match -- camera-match real PC-12 photos to out/pc12.glb and show where the model's cockpit
glazing (and the nose around it) differs from the real aircraft.

(work in progress -- full documentation at the end of the build)
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GLB = ROOT / "out" / "pc12.glb"
PHOTO_DIR = HERE / "cache" / "photos"
OUT = ROOT / "out" / "tmp" / "photo_match"


# =============================================================================================
# 1. model geometry (GLB with faces and material names, MODEL coordinates)
# =============================================================================================
_GLB = {}


def read_glb(path=None):
    """-> list of dicts {part, node, material, V (n,3) model coords, F (m,3)} (node transforms applied;
    a mesh belongs to its nearest ancestor node with extras.part)."""
    path = Path(path or GLB)
    key = (str(path), path.stat().st_mtime)
    if key in _GLB:
        return _GLB[key]
    data = path.read_bytes()
    n = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + n])
    binb = data[20 + n + 8:]
    ctype = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    mats = [m.get("name", f"mat{i}") for i, m in enumerate(js.get("materials", []))]

    def acc(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        dt = np.dtype(ctype[a["componentType"]])
        nc = ncomp[a["type"]]
        stride = bv.get("byteStride", dt.itemsize * nc)
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        raw = np.frombuffer(binb, np.uint8, stride * (a["count"] - 1) + dt.itemsize * nc, off)
        arr = np.lib.stride_tricks.as_strided(raw, (a["count"], nc * dt.itemsize), (stride, 1))
        arr = np.ascontiguousarray(arr).view(dt).reshape(a["count"], nc).astype(float)
        if a.get("normalized") and dt.kind in "iu":
            arr = np.maximum(arr / float(np.iinfo(dt).max), -1.0)
        return arr

    def qmat(q):
        x, y, z, w = q
        return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

    def local(nd):
        if "matrix" in nd:
            return np.array(nd["matrix"]).reshape(4, 4).T
        M = np.eye(4)
        M[:3, :3] = qmat(nd.get("rotation", [0, 0, 0, 1])) @ np.diag(nd.get("scale", [1, 1, 1]))
        M[:3, 3] = nd.get("translation", [0, 0, 0])
        return M

    out = []

    def walk(i, M, part):
        nd = js["nodes"][i]
        M = M @ local(nd)
        part = (nd.get("extras") or {}).get("part", part)
        if "mesh" in nd:
            for prim in js["meshes"][nd["mesh"]]["primitives"]:
                V = acc(prim["attributes"]["POSITION"])
                F = acc(prim["indices"]).astype(np.int64).reshape(-1, 3)
                Vw = V @ M[:3, :3].T + M[:3, 3]
                out.append(dict(part=part, node=nd.get("name", ""), material=mats[prim["material"]]
                                if "material" in prim else "", V=np.stack([Vw[:, 2], Vw[:, 0], Vw[:, 1]], -1), F=F))
        for c in nd.get("children", []):
            walk(c, M, part)

    for r in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4), None)
    _GLB[key] = out
    return out


def select(prims, parts=None, materials=None, exclude_parts=()):
    """Merge primitives whose part starts with one of `parts` (and material in `materials`) -> V, F."""
    Vs, Fs, n = [], [], 0
    for p in prims:
        pid = p["part"] or ""
        if parts is not None and not any(pid.startswith(q) for q in parts):
            continue
        if any(pid.startswith(q) for q in exclude_parts):
            continue
        if materials is not None and p["material"] not in materials:
            continue
        Vs.append(p["V"])
        Fs.append(p["F"] + n)
        n += len(p["V"])
    if not Vs:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    return np.concatenate(Vs), np.concatenate(Fs)


SKIN_PARTS = ("fus_fwd", "fus_center", "fus_aft", "cowl_upper", "cowl_lower", "glazing_flightdeck",
              "glazing_cabin", "door_airstair", "door_cargo", "exit_hatch")


class Skin:
    """Fuselage outer skin of the GLB: plane slices and the half-width hw(x, z, side)."""

    def __init__(self, prims=None):
        prims = prims if prims is not None else read_glb()
        self.V, self.F = select(prims, SKIN_PARTS)
        T = self.V[self.F]
        self.T = T
        self.tx0, self.tx1 = T[..., 0].min(1), T[..., 0].max(1)
        self._cache = {}

    def slice_plane(self, n, d, xlim=None):
        """Points of the skin on the plane n.X = d (n need not be unit); xlim prefilters triangles."""
        n = np.asarray(n, float)
        T = self.T
        if xlim is not None:
            m = (self.tx1 >= xlim[0]) & (self.tx0 <= xlim[1])
            T = T[m]
        s = T @ n - d
        out = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            m = (s[:, i] * s[:, j]) < 0
            t = s[m, i] / (s[m, i] - s[m, j])
            out.append(T[m, i] + (T[m, j] - T[m, i]) * t[:, None])
        return np.vstack(out)

    def section(self, x):
        key = round(float(x), 4)
        if key not in self._cache:
            P = np.zeros((0, 3))
            for dx in (0.0, 2e-5, -2e-5):                 # vertices exactly on a part joint
                P = self.slice_plane((1, 0, 0), x + dx, (x + dx - 1e-9, x + dx + 1e-9))
                if len(P):
                    break
            self._cache[key] = P
        return self._cache[key]

    def hw(self, x, z, side=1):
        """|y| of the skin at station x, water line z, on `side` (+1 starboard / -1 port)."""
        P = self.section(x)
        P = P[side * P[:, 1] > 0]
        if len(P) == 0:
            return np.nan
        zb = np.round(P[:, 2] / 0.004).astype(int)
        order = np.lexsort((np.abs(P[:, 1]), zb))
        zb, P = zb[order], P[order]
        last = np.r_[zb[1:] != zb[:-1], True]
        zz, yy = P[last, 2], np.abs(P[last, 1])
        if z < zz.min() - 0.01 or z > zz.max() + 0.01:
            return np.nan
        return float(np.interp(z, zz, yy))

    def top(self, x):
        P = self.section(x)
        return float(P[:, 2].max()), float(P[:, 2].min())

    def point(self, x, z, side):
        return np.array([x, side * self.hw(x, z, side), z])


# =============================================================================================
# 2. reference features of the REAL aircraft (for the camera solve)
# =============================================================================================
# Camera solving must not use model features that are themselves in doubt (the glazing, and -- per
# the registered Pilatus drawing, refs/mbp.py -- the model's door / cabin-window / exhaust positions
# and cabin crown).  Reference points therefore come from
#   * the GLB only where the model is pinned by sourced dimensions (spinner tip, winglet / stab tips,
#     tail bullet, wheel positions = track 4.53 + drawing axle stations), and
#   * the Pilatus drawing 190.10.40.432 as registered by refs/mbp.py, evaluated at RUN TIME from the
#     git-ignored cache (doors, cabin windows, cowling joints, exhaust outlets).  No drawing-derived
#     coordinates are stored in this file.
# Side-view (x, z) drawing features are lifted onto the fuselage side with the model skin half-width
# after mapping the drawing's crown/keel onto the model's (the drawing's cabin sits higher than the
# model's, see PHOTO_MATCH.md).

def _dwg():
    try:
        from refs import mbp
        return mbp.load()
    except Exception as e:                                         # pragma: no cover
        print(f"[photo_match] Pilatus drawing unavailable ({e}); model-only reference points")
        return None


def _items(d, view, box, kinds=("outline",), minlen=2):
    x0, x1, z0, z1 = box
    out = []
    for it in d[view]:
        if it.get("kind") not in kinds:
            continue
        P = np.asarray(it["pts"], float)
        if len(P) >= minlen and P[:, 0].min() >= x0 and P[:, 0].max() <= x1 and P[:, 1].min() >= z0 \
                and P[:, 1].max() <= z1:
            out.append(P)
    return out


def _dense(P, step=0.02):
    """Resample a 2-D polyline to <= step spacing (before lifting it onto the skin)."""
    P = np.asarray(P, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    si = np.linspace(0, s[-1], max(2, int(s[-1] / step) + 1))
    return np.stack([np.interp(si, s, P[:, k]) for k in range(P.shape[1])], 1)


class Reference:
    """Named reference points / curves (MODEL coordinates) with 1-sigma uncertainties [m]."""

    def __init__(self, prims=None, use_drawing=True):
        self.prims = prims if prims is not None else read_glb()
        self.skin = Skin(self.prims)
        self.d = _dwg() if use_drawing else None
        self.pts = {}      # name -> (X (3,), sigma, source)
        self.curves = {}   # name -> (P (N,3), sigma, source)
        self._model_points()
        if self.d is not None:
            self._drawing_features()

    # ---------------------------------------------------------------- helpers
    def add(self, name, X, sigma, src):
        self.pts[name] = (np.asarray(X, float), float(sigma), src)

    def addc(self, name, P, sigma, src, ordered=False, step=0.005):
        """Curve samples; ordered polylines are resampled to `step` so nearest-sample distances are
        accurate to well under a pixel."""
        P = np.asarray(P, float)
        P = P[np.isfinite(P).all(1)]
        if ordered and len(P) > 1:
            seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
            s = np.r_[0, np.cumsum(seg)]
            n = max(2, int(s[-1] / step) + 1)
            si = np.linspace(0, s[-1], n)
            P = np.stack([np.interp(si, s, P[:, k]) for k in range(3)], 1)
        self.curves[name] = (P, float(sigma), src)

    def dz(self, x):
        """Drawing crown WL minus model crown WL at station x (0 without the drawing)."""
        if self.d is None:
            return 0.0
        cr = np.asarray(self.d["profiles"]["side_crown"], float)
        xs = float(np.clip(x, cr[:, 0].min(), cr[:, 0].max()))
        return float(np.interp(xs, cr[:, 0], cr[:, 1])) - self.skin.top(xs)[0]

    def lift(self, xz, side):
        """Drawing side-view points (x, z) -> 3-D points on the model skin (crown offset removed)."""
        out = []
        for x, z in np.asarray(xz, float):
            zm = z - self.dz(x)
            out.append((x, side * self.skin.hw(x, zm, side), z))
        return np.array(out)

    # ---------------------------------------------------------------- model (sourced) points
    def _model_points(self):
        V = lambda parts, mats=None: select(self.prims, parts, mats)[0]
        P = V(["propeller"])
        self.add("spinner_tip", P[np.argmin(P[:, 0])], 0.01, "model (STA 0.39 / WL 1.655, sourced)")
        for s, lab in ((+1, "R"), (-1, "L")):
            W = V([f"winglet_{lab}"])
            top = W[W[:, 2] > W[:, 2].max() - 0.03]
            self.add(f"winglet_top_te_{lab}", top[np.argmax(top[:, 0])], 0.06, "model winglet (span 16.28 sourced; shape estimated)")
            self.add(f"winglet_top_le_{lab}", top[np.argmin(top[:, 0])], 0.06, "model winglet (estimated)")
            S = V(["stabilizer", f"elevator_{lab}"])
            S = S[s * S[:, 1] > 0]
            tip = S[np.abs(S[:, 1]) > np.abs(S[:, 1]).max() - 0.012]
            self.add(f"stab_tip_le_{lab}", tip[np.argmin(tip[:, 0])], 0.03, "model stabiliser (tail span 5.20 sourced)")
            self.add(f"stab_tip_te_{lab}", tip[np.argmax(tip[:, 0])], 0.03, "model stabiliser (tail span 5.20 sourced)")
            G = V([f"gear_main_{lab}"], ["tire"])
            c = 0.5 * (G.min(0) + G.max(0))
            self.add(f"main_axle_{lab}", c, 0.02, "model main wheel centre (track 4.53 sourced)")
        B = V(["tail_bullet"])
        self.add("bullet_aft", B[np.argmax(B[:, 0])], 0.02, "model tail bullet (length 14.40 sourced)")
        self.add("bullet_nose", B[np.argmin(B[:, 0])], 0.04, "model tail bullet nose")
        G = V(["gear_nose"], ["tire"])
        self.add("nose_axle", 0.5 * (G.min(0) + G.max(0)) * [1, 0, 1], 0.02, "model nose wheel centre")
        self._nose_offsets = {"nose_hub_L": -0.07, "nose_hub_R": 0.07, "nose_axle_end_L": -0.115,
                              "nose_axle_end_R": 0.115}
        for k, dy in self._nose_offsets.items():
            self.add(k, self.pts["nose_axle"][0] + [0, dy, 0], 0.02, "nose wheel centre + hub face / fork offset")

    # ---------------------------------------------------------------- drawing features
    def _drawing_features(self):
        d, sk = self.d, self.skin
        chk = {c["name"]: c for c in d["meta"]["checks"]}
        # wheels: axle stations from the drawing
        try:
            xn = float(chk["Nose wheel axle station"]["measured"])
            xm = float(chk["Main wheel axle station"]["measured"])
            X = self.pts["nose_axle"][0].copy(); X[0] = xn
            self.add("nose_axle", X, 0.02, "drawing axle station, model WL")
            for k, dy in self._nose_offsets.items():
                self.add(k, X + [0, dy, 0], 0.02, "drawing axle station + hub face / fork offset")
            for lab in "LR":
                X = self.pts[f"main_axle_{lab}"][0].copy(); X[0] = xm
                self.add(f"main_axle_{lab}", X, 0.02, "drawing axle station, track 4.53, model WL")
        except KeyError:
            pass
        # cowling joints: aft (vertical, near STA 3.0), forward (slanted, near STA 2.07), split line
        aft = [P for P in _items(d, "side", (2.95, 3.06, 0.9, 2.25)) if np.ptp(P[:, 1]) > 1.0]
        fwd = [P for P in _items(d, "side", (1.95, 2.2, 0.9, 2.2)) if np.ptp(P[:, 1]) > 0.9]
        spl = [P for P in _items(d, "side", (2.0, 3.06, 1.4, 1.75)) if np.ptp(P[:, 0]) > 0.8 and np.ptp(P[:, 1]) < 0.01]
        if aft and fwd:
            xa = float(np.mean(aft[0][:, 0]))
            (xa0, za0), (xa1, za1) = fwd[0][np.argsort(fwd[0][:, 1])][[0, -1]]
            # plane through the slanted side-view line, perpendicular to y:  n = (za1-za0, 0, -(xa1-xa0))
            nf = np.array([za1 - za0, 0.0, -(xa1 - xa0)])
            df = nf @ np.array([xa0, 0, za0])
            ring_a = sk.slice_plane((1, 0, 0), xa, (xa - 1e-9, xa + 1e-9))
            ring_f = sk.slice_plane(nf, df, (min(xa0, xa1) - 0.05, max(xa0, xa1) + 0.05))
            for P, nm in ((ring_a, "cowl_joint_aft"), (ring_f, "cowl_joint_fwd")):
                # upper part only: below the max-breadth WL the model's lower cowl departs from the drawing
                # (chin / keel line up to 0.13 m higher), so the lifted ring would be biased there
                zc = 0.5 * (P[:, 2].max() + P[:, 2].min())
                P = P[P[:, 2] > 1.45]
                self.addc(nm + "_port", P[P[:, 1] < -0.02], 0.015, "drawing cowling joint on model skin")
                self.addc(nm + "_stbd", P[P[:, 1] > 0.02], 0.015, "drawing cowling joint on model skin")
                self.addc(nm + "_top", P[P[:, 2] > zc], 0.015, "drawing cowling joint on model skin")
            if spl:
                zs = float(np.mean(spl[0][:, 1]))
                xf_at = xa0 + (zs - za0) * (xa1 - xa0) / (za1 - za0)
                for s, lab in ((-1, "port"), (1, "stbd")):
                    self.add(f"cowl_T_aft_{lab}", sk.point(xa, zs, s), 0.012, "drawing cowl joint x split line")
                    self.add(f"cowl_T_fwd_{lab}", sk.point(xf_at, zs, s), 0.012, "drawing cowl joint x split line")
                    xs = np.linspace(xf_at, xa, 40)
                    self.addc(f"cowl_split_{lab}", [sk.point(x, zs, s) for x in xs], 0.015, "drawing cowl split line",
                              ordered=True)
        # exhaust outlets: aft-most point of the stack outline (side), outlet butt line from the plan
        side_ex = [P for P in _items(d, "side", (1.6, 2.1, 1.55, 1.85)) if np.ptp(P[:, 0]) > 0.2]
        if side_ex:
            P = side_ex[0]
            i = np.argmax(P[:, 0])
            xo, zo = P[i]
            for s, lab in ((-1, "port"), (1, "stbd")):
                pl = [Q for Q in _items(d, "plan", (1.2, 2.3, -1.0, -0.15) if s < 0 else (1.2, 2.3, 0.15, 1.0))
                      if np.ptp(Q[:, 0]) > 0.4]
                if not pl:
                    continue
                Q = np.vstack(pl)
                near = Q[Q[:, 0] > xo - 0.03]
                yo = float(np.mean(near[:, 1])) if len(near) else s * 0.47
                self.add(f"exhaust_out_{lab}", (xo, yo, zo), 0.03, "drawing exhaust-stack aft extreme (side+plan)")
                io = np.argmax(np.abs(Q[:, 1]))
                self.add(f"exhaust_outboard_{lab}", (Q[io, 0], Q[io, 1], zo), 0.03,
                         "drawing exhaust-stack outboard extreme (plan) at the outlet WL")
        # tailplane and winglet tips, stabiliser and wing leading edges (plan + front view).  The model's
        # tailplane tip sits ~0.5 m aft of the drawing's and its winglet top ~0.28 m lower (outside the glazing
        # scope, reported in PHOTO_MATCH.md), so these replace the model-derived points when available.
        plan = np.vstack([np.asarray(it["pts"], float) for it in d["plan"] if it.get("kind") == "outline"])
        front = np.vstack([np.asarray(it["pts"], float) for it in d["front"] if it.get("kind") == "outline"])
        fs = front[(np.abs(front[:, 0]) > 2.45) & (np.abs(front[:, 0]) < 2.7) & (front[:, 1] > 3.8)]
        z_stab = float(np.median(fs[:, 1])) if len(fs) else 4.10
        fw = front[np.abs(front[:, 0]) > 7.9]
        z_wl = float(fw[:, 1].max()) if len(fw) else None
        for s_, lab in ((+1, "R"), (-1, "L")):
            st = plan[(plan[:, 0] > 13.3) & (s_ * plan[:, 1] > 2.2)]
            if len(st):
                te = st[s_ * st[:, 1] > 2.5]
                te = te[np.argmax(te[:, 0])]
                out = st[np.argmax(s_ * st[:, 1])]
                self.add(f"stab_tip_te_{lab}", (te[0], te[1], z_stab), 0.02, "drawing tailplane tip, TE corner")
                self.add(f"stab_tip_out_{lab}", (out[0], out[1], z_stab), 0.02, "drawing tailplane tip, outermost")
            wl = plan[(s_ * plan[:, 1] > 8.0) & (s_ * plan[:, 1] < 8.05)]
            if len(wl) and z_wl:
                t = wl[np.argmax(wl[:, 0])]
                self.add(f"winglet_top_te_{lab}", (t[0], t[1], z_wl), 0.05, "drawing winglet top, TE corner (static)")
            # stabiliser LE: the long swept plan line ending near the tip
            le = [P for P in _items(d, "plan", (12.9, 13.7, 0.0, 2.6) if s_ > 0 else (12.9, 13.7, -2.6, 0.0))
                  if np.ptp(P[:, 1]) > 1.5]
            if le:
                P = le[0]
                P = P[np.argsort(np.abs(P[:, 1]))]
                P = P[np.r_[True, np.diff(np.abs(P[:, 1])) > 0]]
                P = P[np.abs(P[:, 1]) < 2.4]
                self.addc(f"stab_le_{lab}", np.c_[P, np.full(len(P), z_stab)], 0.02, "drawing tailplane LE (plan)",
                          ordered=True)
            wle = [P for P in _items(d, "plan", (5.0, 6.0, 0.8, 7.9) if s_ > 0 else (5.0, 6.0, -7.9, -0.8))
                   if np.ptp(P[:, 1]) > 5]
            if wle:
                P = min(wle, key=lambda Q: Q[:, 0].min())
                P = P[np.argsort(np.abs(P[:, 1]))]
                ys = np.linspace(np.abs(P[:, 1]).min(), min(np.abs(P[:, 1]).max(), 5.5), 60)
                xs = np.interp(ys, np.abs(P[:, 1]), P[:, 0])
                zs = self._wing_le_z(ys, lab)
                self.addc(f"wing_le_{lab}", np.c_[xs, s_ * ys, zs], 0.03, "drawing wing LE (plan) at model LE WL",
                          ordered=True)
        # doors and windows (side view) lifted onto the skin
        op = d["openings"]["side"]
        if "door_airstair" in op:
            self.addc("door_airstair", self.lift(_dense(op["door_airstair"]), -1), 0.02, "drawing airstair door outline",
                      ordered=True)
            P = np.asarray(op["door_airstair"], float)
            self.add("door_airstair_centre", self.lift([P.mean(0)], -1)[0], 0.03, "drawing")
        if "door_cargo" in op:
            self.addc("door_cargo", self.lift(_dense(op["door_cargo"]), -1), 0.02, "drawing cargo door outline",
                      ordered=True)
        wins = sorted([k for k in op if k.startswith("cabin_win")]) + (["door_cargo_win"] if "door_cargo_win" in op else [])
        for k in wins:
            P = np.asarray(op[k], float)
            c = 0.5 * (P.min(0) + P.max(0))
            self.add(f"port_{k}", self.lift([c], -1)[0], 0.015, "drawing port window centre")
            self.addc(f"port_{k}_outline", self.lift(P, -1), 0.015, "drawing port window outline", ordered=True)
        # starboard detail: window-sized loops and the exit hatch
        st = [np.asarray(it["pts"], float) for it in d["detail_stbd"] if it.get("kind") == "outline"]
        ws = sorted([P for P in st if 0.25 < np.ptp(P[:, 0]) < 0.35 and 0.3 < np.ptp(P[:, 1]) < 0.45],
                    key=lambda P: P[:, 0].min())
        for i, P in enumerate(ws, 1):
            c = 0.5 * (P.min(0) + P.max(0))
            self.add(f"stbd_win_{i}", self.lift([c], +1)[0], 0.015, "drawing stbd window centre")
            self.addc(f"stbd_win_{i}_outline", self.lift(P, +1), 0.015, "drawing stbd window outline", ordered=True)
        ex = [P for P in st if 0.4 < np.ptp(P[:, 0]) < 0.6 and 0.5 < np.ptp(P[:, 1]) < 0.8]
        if ex:
            self.addc("exit_hatch", self.lift(_dense(ex[0]), +1), 0.02, "drawing exit hatch outline", ordered=True)
        # cockpit glazing of the drawing (NGX sheet) lifted onto the model skin -- overlay only
        self.glazing = {}
        g = d["glazing"]["side"]
        for k, P in g.items():
            for s, lab in ((-1, "port"), (1, "stbd")):
                if k.startswith("dv") and s > 0:
                    continue
                self.glazing[f"{k.split('_')[0]}_{lab}"] = self.lift(P, s)

    def corrected_skin(self, parts=("fus_fwd", "glazing_flightdeck", "cowl_upper", "cowl_lower", "fus_center"),
                       xmax=6.0):
        """Model skin triangles re-mapped section by section onto the drawing's crown / keel / half-breadth
        profiles (x 1.0 .. 9.0): a better stand-in for the REAL outer surface when back-projecting photo
        pixels (the model's cabin sits ~0.14 m lower than the drawing's).  Without the drawing: the model skin."""
        V, F = select(self.prims, parts)
        c = V[F].mean(1)
        F = F[c[:, 0] < xmax]
        if self.d is None:
            return V[F]
        pr = self.d["profiles"]
        cr, bo, hb = (np.asarray(pr[k], float) for k in ("side_crown", "side_bottom", "plan_hb_stbd"))
        xs = np.arange(1.0, min(9.0, xmax + 0.1), 0.02)
        zt_m, zb_m, hw_m = [], [], []
        for x in xs:
            P = self.skin.section(round(x, 4))
            zt_m.append(P[:, 2].max()); zb_m.append(P[:, 2].min()); hw_m.append(np.abs(P[:, 1]).max())
        zt_m, zb_m, hw_m = map(np.asarray, (zt_m, zb_m, hw_m))
        zt_d = np.interp(xs, cr[:, 0], cr[:, 1])
        zb_d = np.interp(xs, bo[:, 0], bo[:, 1])
        hw_d = np.interp(xs, hb[:, 0], hb[:, 1])
        W = V.copy()
        m = (V[:, 0] >= xs[0]) & (V[:, 0] <= xs[-1])
        x = V[m, 0]
        a_t, a_b = np.interp(x, xs, zt_m), np.interp(x, xs, zb_m)
        b_t, b_b = np.interp(x, xs, zt_d), np.interp(x, xs, zb_d)
        W[m, 2] = b_b + (V[m, 2] - a_b) * (b_t - b_b) / (a_t - a_b)
        W[m, 1] = V[m, 1] * np.interp(x, xs, hw_d) / np.interp(x, xs, hw_m)
        self.skin_map = dict(xs=xs, zt_m=zt_m, zb_m=zb_m, hw_m=hw_m, zt_d=zt_d, zb_d=zb_d, hw_d=hw_d)
        return W[F]

    def _wing_le_z(self, ys, lab):
        """WL of the model wing's leading edge (min-x vertex per span station) at |y| = ys."""
        W = select(self.prims, [f"wing_{lab}"])[0]
        yb = np.round(np.abs(W[:, 1]) / 0.1)
        ks = np.unique(yb)
        le = np.array([W[yb == k][np.argmin(W[yb == k, 0])] for k in ks])
        return np.interp(ys, np.abs(le[:, 1]), le[:, 2])

    def summary(self):
        rows = [(n, X.round(3).tolist(), s, src) for n, (X, s, src) in self.pts.items()]
        rows += [(n, f"curve {len(P)} pts", s, src) for n, (P, s, src) in self.curves.items()]
        return rows


# =============================================================================================
# 3. camera model and solver
# =============================================================================================
def rodrigues(r):
    r = np.asarray(r, float)
    th = np.linalg.norm(r)
    if th < 1e-12:
        return np.eye(3)
    k = r / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def rot_to_vec(R):
    c = np.clip((np.trace(R) - 1) / 2, -1, 1)
    th = np.arccos(c)
    if th < 1e-9:
        return np.zeros(3)
    if th > np.pi - 1e-6:                     # 180 deg: axis from R + I
        A = (R + np.eye(3)) / 2
        k = np.sqrt(np.clip(np.diag(A), 0, None))
        i = np.argmax(k)
        k = A[i] / k[i]
        return th * k / np.linalg.norm(k)
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]) / (2 * np.sin(th))
    return th * w


class Camera:
    """Pinhole camera, OpenCV axes (x right, y down, z forward), pixel origin at the top-left CORNER.
    X_cam = R (X - C);  u = f x/z + cx,  v = f y/z + cy."""

    def __init__(self, R, C, f, cx, cy, W, H):
        self.R, self.C = np.asarray(R, float), np.asarray(C, float)
        self.f, self.cx, self.cy, self.W, self.H = float(f), float(cx), float(cy), int(W), int(H)

    @property
    def K(self):
        return np.array([[self.f, 0, self.cx], [0, self.f, self.cy], [0, 0, 1.0]])

    @property
    def t(self):
        return -self.R @ self.C

    @property
    def P(self):
        return self.K @ np.c_[self.R, self.t]

    def project(self, X, return_depth=False):
        X = np.atleast_2d(np.asarray(X, float))
        Xc = (X - self.C) @ self.R.T
        z = Xc[:, 2]
        uv = np.c_[self.f * Xc[:, 0] / z + self.cx, self.f * Xc[:, 1] / z + self.cy]
        return (uv, z) if return_depth else uv

    def ray(self, uv):
        """Unit ray directions (model frame) through pixels uv (N,2)."""
        uv = np.atleast_2d(np.asarray(uv, float))
        d = np.c_[(uv[:, 0] - self.cx) / self.f, (uv[:, 1] - self.cy) / self.f, np.ones(len(uv))]
        d = d @ self.R          # R^T d
        return d / np.linalg.norm(d, axis=1, keepdims=True)

    def scaled(self, s, W=None, H=None, ox=0.0, oy=0.0):
        """Camera of the image resampled by s and/or cropped at (ox, oy) (original pixels)."""
        return Camera(self.R, self.C, self.f * s, (self.cx - ox) * s, (self.cy - oy) * s,
                      W or round(self.W * s), H or round(self.H * s))

    def to_json(self):
        return dict(K=self.K.tolist(), R=self.R.tolist(), t=self.t.tolist(), C=self.C.tolist(),
                    width=self.W, height=self.H, pixel_origin="corner",
                    fov_x_deg=float(np.degrees(2 * np.arctan(self.W / 2 / self.f))))

    @staticmethod
    def from_json(j):
        K = np.asarray(j["K"], float)
        return Camera(j["R"], j["C"], K[0, 0], K[0, 2], K[1, 2], j["width"], j["height"])

    def describe(self):
        look = self.R[2]
        az = np.degrees(np.arctan2(look[1], look[0]))
        el = np.degrees(np.arcsin(-look[2]))
        fov = np.degrees(2 * np.arctan(self.W / 2 / self.f))
        f35 = 36.0 * self.f / self.W
        return (f"C = ({self.C[0]:.2f}, {self.C[1]:.2f}, {self.C[2]:.2f}) m, look az {az:.1f} deg "
                f"(0 = +x aft), depression {el:.1f} deg, f = {self.f:.0f} px (hfov {fov:.1f} deg, "
                f"~{f35:.0f} mm on 35 mm if uncropped)")


def dlt(X, uv):
    """Direct linear transform: 3x4 P from >= 6 correspondences (Hartley normalisation)."""
    X = np.asarray(X, float)
    uv = np.asarray(uv, float)
    mX, sX = X.mean(0), np.sqrt(3) / np.mean(np.linalg.norm(X - X.mean(0), axis=1))
    mu, su = uv.mean(0), np.sqrt(2) / np.mean(np.linalg.norm(uv - uv.mean(0), axis=1))
    TX = np.diag([sX, sX, sX, 1.0]); TX[:3, 3] = -sX * mX
    Tu = np.diag([su, su, 1.0]); Tu[:2, 2] = -su * mu
    Xn = (np.c_[X, np.ones(len(X))] @ TX.T)
    un = (np.c_[uv, np.ones(len(uv))] @ Tu.T)
    A = []
    for (x, y, z, w), (u, v, _) in zip(Xn, un):
        A.append([x, y, z, w, 0, 0, 0, 0, -u * x, -u * y, -u * z, -u * w])
        A.append([0, 0, 0, 0, x, y, z, w, -v * x, -v * y, -v * z, -v * w])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    Pn = Vt[-1].reshape(3, 4)
    return np.linalg.inv(Tu) @ Pn @ TX


def camera_from_P(P, W, H):
    from render.blender_ortho import rq3
    K, R = rq3(P[:, :3])
    t = np.linalg.solve(K, P[:, 3])
    if np.linalg.det(R) < 0:
        R, t = -R, -t
    K = K / K[2, 2]
    C = -R.T @ t
    return Camera(R, C, 0.5 * (K[0, 0] + K[1, 1]), K[0, 2], K[1, 2], W, H)


class Solver:
    """Least-squares camera fit to point and on-curve keypoints.

    Parameters: rotation vector (3), camera centre (3), log focal (1) [, cx, cy].  Residuals are in
    units of their 1-sigma: image sigma (px) combined with the 3-D reference sigma projected at the
    point's depth.  Curve keypoints use the distance to the nearest projected curve sample."""

    def __init__(self, ref, W, H, pts, on=(), sigma_px=1.5, free_pp=False, weights=None):
        self.ref, self.W, self.H = ref, W, H
        self.pts = {k: np.asarray(v, float) for k, v in pts.items() if k in ref.pts}
        self.missing = [k for k in pts if k not in ref.pts]
        self.on = [(c, np.asarray(uv, float)) for c, uv in on if c in ref.curves]
        self.missing += [c for c, _ in on if c not in ref.curves]
        self.sigma_px = sigma_px
        self.free_pp = free_pp
        self.weights = weights or {}
        self.active = set(self.pts) | {i for i in range(len(self.on))}

    def cam(self, p):
        cx, cy = (p[7], p[8]) if self.free_pp else (self.W / 2, self.H / 2)
        return Camera(rodrigues(p[:3]), p[3:6], np.exp(p[6]), cx, cy, self.W, self.H)

    def residuals(self, p, detail=False, points_only=False):
        cam = self.cam(p)
        res, info = [], []
        names = list(self.pts)
        if names:
            X = np.array([self.ref.pts[k][0] for k in names])
            s3 = np.array([self.ref.pts[k][1] for k in names])
            uv = np.array([self.pts[k] for k in names])
            q, z = cam.project(X, True)
            w = np.array([self.weights.get(k, 1.0) for k in names])
            sig = np.hypot(self.sigma_px * w, s3 * cam.f / np.maximum(np.abs(z), 1e-3))
            r = (q - uv) / sig[:, None]
            r[z <= 0] = 1e3
            on = np.array([k in self.active for k in names])
            r[~on] = 0.0
            res.append(r.ravel())
            if detail:
                for i, k in enumerate(names):
                    info.append((k, "pt", q[i] - uv[i], sig[i], bool(on[i])))
        if not points_only and self.on:
            proj = {}
            for c in {c for c, _ in self.on}:
                Pc, s3, _ = self.ref.curves[c]
                q, z = cam.project(Pc, True)
                ok = z > 0
                proj[c] = (q[ok], z[ok], s3)
            rr = []
            for i, (c, uv) in enumerate(self.on):
                q, z, s3 = proj[c]
                if len(q) == 0:                                  # curve behind the camera
                    rr.append(1e3 if i in self.active else 0.0)
                    if detail:
                        info.append((f"{c}@{i}", "on", np.array([1e3, 0.0]), 1.0, i in self.active))
                    continue
                dd = np.hypot(q[:, 0] - uv[0], q[:, 1] - uv[1])
                j = np.argmin(dd)
                sig = np.hypot(self.sigma_px * self.weights.get(c, 1.0), s3 * cam.f / max(z[j], 1e-3))
                on = i in self.active
                rr.append(dd[j] / sig if on else 0.0)
                if detail:
                    info.append((f"{c}@{i}", "on", np.array([dd[j], 0.0]), sig, on))
            res.append(np.asarray(rr))
        res = np.concatenate(res) if res else np.zeros(0)
        return (res, info) if detail else res

    def fit(self, p0, loss="soft_l1"):
        from scipy.optimize import least_squares
        r = least_squares(self.residuals, p0, loss=loss, f_scale=2.0, x_scale="jac", max_nfev=4000)
        return r.x, r

    def initial(self, f_guess=None):
        """DLT on the point keypoints, else a multi-start over viewing directions."""
        names = list(self.pts)
        X = np.array([self.ref.pts[k][0] for k in names])
        uv = np.array([self.pts[k] for k in names])
        cands = []
        if len(names) >= 6:
            try:
                cam = camera_from_P(dlt(X, uv), self.W, self.H)
                if np.all(cam.project(X, True)[1] > 0) and cam.f > 0:
                    p = np.r_[rot_to_vec(cam.R), cam.C, np.log(cam.f)]
                    if self.free_pp:
                        p = np.r_[p, self.W / 2, self.H / 2]
                    cands.append(p)
            except Exception:
                pass
        centre = X.mean(0)
        ext = np.linalg.norm(X - centre, axis=1).max() + 0.5
        fs = [f_guess] if f_guess else [0.6 * self.W, 1.2 * self.W, 2.5 * self.W, 5 * self.W]
        for f in fs:
            for az in range(0, 360, 30):
                for el in (-15, 5, 25, 45, 65, 85):
                    a, e = np.radians(az), np.radians(el)
                    look = np.array([np.cos(a) * np.cos(e), np.sin(a) * np.cos(e), -np.sin(e)])
                    dist = 1.2 * ext * f / (0.5 * self.W)
                    C = centre - look * dist
                    up = np.array([0, 0, 1.0]) if abs(look[2]) < 0.95 else np.array([1.0, 0, 0])
                    rgt = np.cross(look, up); rgt /= np.linalg.norm(rgt)
                    dwn = np.cross(look, rgt)
                    R = np.stack([rgt, dwn, look])
                    p = np.r_[rot_to_vec(R), C, np.log(f)]
                    if self.free_pp:
                        p = np.r_[p, self.W / 2, self.H / 2]
                    cands.append(p)
        return cands

    def solve(self, reject_sigma=None, max_reject=3, f_guess=None, verbose=False):
        from scipy.optimize import least_squares
        best = None
        cands = self.initial(f_guess)
        fun = lambda q: self.residuals(q, points_only=True)
        for i, p0 in enumerate(cands):
            try:
                r = least_squares(fun, p0, loss="soft_l1", f_scale=2.0, x_scale="jac", max_nfev=200)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
            if i == 0 and r.cost < 2.0 * len(self.pts):      # DLT start already fits: skip multi-start
                break
        p, r = self.fit(best.x)
        rejected = []
        if reject_sigma:
            for _ in range(max_reject):
                res, info = self.residuals(p, detail=True)
                worst = None
                for (k, kind, d, sig, on) in info:
                    e = np.linalg.norm(d) / sig
                    key = k if kind == "pt" else int(k.split("@")[1])
                    if on and e > reject_sigma and (worst is None or e > worst[1]):
                        worst = (key, e, k)
                if worst is None:
                    break
                self.active.discard(worst[0])
                rejected.append((worst[2], round(worst[1], 1)))
                p, r = self.fit(p)
        self.p, self.result, self.rejected = p, r, rejected
        return self.cam(p)

    def report(self, p=None):
        p = self.p if p is None else p
        res, info = self.residuals(p, detail=True)
        rows = []
        for (k, kind, d, sig, on) in info:
            rows.append(dict(name=k, kind=kind, du=float(d[0]), dv=float(d[1]) if kind == "pt" else None,
                             err_px=float(np.linalg.norm(d)), sigma_px=float(sig), used=bool(on)))
        used = [r["err_px"] for r in rows if r["used"]]
        used_pt = [r["err_px"] for r in rows if r["used"] and r["kind"] == "pt"]
        return dict(rows=rows, rms_px=float(np.sqrt(np.mean(np.square(used)))) if used else None,
                    rms_pt_px=float(np.sqrt(np.mean(np.square(used_pt)))) if used_pt else None,
                    n_used=len(used), n_pt=len(used_pt))


# =============================================================================================
# 4. photos: our own pixel measurements (corner-origin pixel coordinates of the cached image)
# =============================================================================================
# pts:  reference-point name -> (u, v)          (measured on 2-6x zoomed crops / intensity profiles)
# on:   (reference-curve name, (u, v))         a pixel lying ON that feature line (1-D constraint)
# trace: glazing features traced in the photo (for the comparison, never used in the solve)
PHOTOS = {}

PHOTOS["pro3010_rfds_port"] = dict(
    file="pro3010_rfds_port_pilatus.webp", variant="PRO (s/n 3010)", side="port",
    view="near-broadside port, camera low and slightly ahead of the wing, gear static",
    pts={
        "spinner_tip": (370.7, 630.0),
        "cowl_T_fwd_port": (819.5, 650.0),
        "cowl_T_aft_port": (1049.0, 655.5),
        "exhaust_out_port": (803.0, 617.0),
        "nose_axle": (960.0, 995.0),
        "main_axle_R": (1425.0, 963.0),          # far-side (starboard) wheel seen under the belly
        "port_cabin_win_1": (1601.4, 535.8),
        "port_cabin_win_2": (1716.2, 542.0),
        "port_cabin_win_3": (1862.1, 550.0),
    },
    on=[("cowl_joint_fwd_port", uv) for uv in [(791, 542), (805, 570), (815, 602), (819, 640), (819, 668)]]
    + [("cowl_joint_aft_port", uv) for uv in [(1041, 574), (1046, 602), (1049, 645), (1048.5, 668)]]
    + [("cowl_split_port", uv) for uv in [(860, 651.5), (940, 653.0), (1000, 654.5)]]
    + [("door_airstair", uv) for uv in [(1391, 455), (1404, 490), (1413, 540), (1416, 580), (1417, 620),
                                         (1416, 680), (1413, 720), (1420, 433), (1440, 435), (1460, 436),
                                         (1480, 437), (1500, 442), (1518, 460), (1527, 480), (1534.5, 500),
                                         (1539, 520), (1544, 560), (1546, 600), (1547, 650), (1544, 700)]],
    glazing_side=-1,
    # port side-window glass: outer edge of the bright seal rim, closed, from the bottom-front corner
    trace={"sw_glass": [(1156, 525), (1175, 504.5), (1200, 484.9), (1225, 465.2), (1250, 445.5), (1254.3, 442.1),
                        (1261.4, 442.9), (1282.9, 445.0), (1304.3, 449.3), (1318.6, 453.6), (1330.0, 462.9),
                        (1337.1, 472.9), (1343.0, 485.0), (1345.7, 498.6), (1345.0, 510.0), (1341.4, 521.4),
                        (1335.7, 530.0), (1325.7, 537.1), (1311.4, 538.6), (1282.9, 537.9), (1254.3, 536.4),
                        (1225.7, 535.7), (1197.1, 535.0), (1175.7, 533.6), (1161.4, 528.6), (1156, 525)]},
    # black surround: dark region (max RGB < 75) around the glazing; outline kept where white skin borders it
    auto_mask=dict(box=(1000, 400, 1400, 580), max_rgb=75, min_lum=150),
)


PHOTOS["pro3066_port34"] = dict(
    file="pro3066_port34_pilatus.webp", variant="PRO (s/n 3066)", side="port",
    view="front-left three-quarter from above (hangar), gear static on chocks",
    pts={
        "spinner_tip": (252.0, 707.0),
        "exhaust_out_port": (897.0, 528.0),
        "cowl_T_fwd_port": (920.0, 570.7),
        "cowl_T_aft_port": (1233.3, 497.3),
        "nose_hub_L": (1225.0, 1006.0),         # axle nut on the port hub face (y ~ -0.07)
        "main_axle_R": (1615.5, 840.0),         # far-side (starboard) wheel, hub centre: weight 3
        "port_cabin_win_1": (1854.0, 170.0),
    },
    weights={"nose_hub_L": 2.0, "main_axle_R": 3.0, "door_airstair": 2.0},
    on=[("cowl_joint_fwd_port", uv) for uv in [(863.3, 463.3), (883.3, 490), (900, 520), (916.7, 560)]]
    + [("cowl_joint_aft_port", uv) for uv in [(1193.3, 400), (1216.7, 446.7), (1248.3, 546.7)]]
    + [("cowl_split_port", uv) for uv in [(1016.7, 548.0), (1116.7, 524.7)]]
    + [("door_airstair", uv) for uv in [(1833, 260), (1846.7, 360), (1856.7, 426.7)]],
    glazing_side=-1,
    trace={
        # side-window glass (inner edge of the dark frame), closed, from the bottom-front corner
        "sw_glass": [(1298, 289), (1317, 254), (1336, 222), (1355, 190), (1374, 156), (1384, 148), (1400, 144),
                     (1430, 142), (1460, 142), (1490, 146), (1510, 154), (1530, 170), (1540, 186), (1544, 200),
                     (1544, 220), (1540, 238), (1530, 250), (1510, 256), (1480, 262), (1440, 272), (1400, 282),
                     (1350, 290), (1298, 289)],
        # outer edge of the black surround around the side window (bottom, aft edge, top), open polyline
        "mask_side": [(1340, 309), (1400, 300), (1460, 290), (1500, 282), (1540, 273), (1560, 262), (1568, 250),
                      (1570, 230), (1570, 210), (1568, 190), (1560, 170), (1546, 150), (1536, 134), (1480, 130),
                      (1440, 133), (1400, 138), (1390, 140)],
    },
)

PHOTOS["pro3001_stbd34_close"] = dict(
    file="pro3001_stbd34_close_aero25.jpg", variant="PRO (s/n 3001, HB-FSG)", side="stbd",
    view="close front-right three-quarter, low, wide angle (AERO 2025), gear static",
    pts={
        "spinner_tip": (3495.0, 955.0),          # chrome spinner, tip seen almost end-on: weight 3
        "exhaust_out_stbd": (1442.0, 1018.0),    # aft end of the stack pipe, mid-height: weight 2
        "cowl_T_aft_stbd": (1147.5, 1172.5),
        "cowl_T_fwd_stbd": (1604.0, 1161.0),     # partly in the stack's shadow: weight 2
        "nose_axle_end_R": (1840.0, 2526.0),     # axle bolt head on the starboard fork arm: weight 2
        "bullet_nose": (705.0, 272.0),           # tail-bullet nose seen head-on (centre of its outline): weight 4
    },
    weights={"spinner_tip": 3.0, "exhaust_out_stbd": 2.0, "cowl_T_fwd_stbd": 2.0, "nose_axle_end_R": 2.0,
             "bullet_nose": 4.0},
    on=[("cowl_joint_aft_stbd", uv) for uv in [(1300, 700), (1245, 775), (1200, 850), (1170, 925), (1152.5, 1000),
                                               (1147.5, 1075), (1146.5, 1150)]]
    + [("cowl_joint_fwd_stbd", uv) for uv in [(1770, 672.5), (1700, 765), (1665, 825), (1640, 897.5)]]
    + [("cowl_split_stbd", uv) for uv in [(1250, 1171), (1400, 1167), (1550, 1163)]],
    glazing_side=+1,
)

PHOTOS["unk_top_front"] = dict(
    file="unk_top_front_pilatus.webp", variant="unknown (NGX or PRO; dark mask, no DV frame visible)", side="top",
    view="air-to-air from above and ahead (camera high, telephoto), gear extended in flight",
    pts={
        "spinner_tip": (2561.0, 2380.0),
        "bullet_aft": (2503.0, 409.5),
        "stab_tip_te_R": (1850.0, 469.0),
        "stab_tip_te_L": (3157.0, 482.0),
        "stab_tip_out_R": (1849.5, 488.5),
        "stab_tip_out_L": (3164.0, 495.0),
        "winglet_top_te_R": (386.0, 1568.0),     # in flight: wing bending raises the tips (sigma 5 cm + weight)
        "winglet_top_te_L": (4683.0, 1597.0),
        "exhaust_outboard_stbd": (2348.0, 2226.0),   # outboard extreme of the stack (plan): weight 2
        "exhaust_outboard_port": (2772.0, 2228.0),
    },
    weights={"exhaust_outboard_stbd": 2.0, "exhaust_outboard_port": 2.0, "winglet_top_te_R": 3.0,
             "winglet_top_te_L": 3.0},
    # leading-edge boots: forward (lower-in-image) edge of the black band, from column intensity profiles
    on=[("stab_le_R", uv) for uv in [(1920, 545), (2000, 550), (2100, 555), (2200, 561), (2300, 567), (2400, 572)]]
    + [("stab_le_L", uv) for uv in [(2600, 575), (2700, 571), (2800, 568), (2900, 565), (3000, 562), (3100, 558)]]
    + [("wing_le_R", uv) for uv in [(1200, 1877), (1400, 1905), (1600, 1932), (1800, 1960), (2000, 1985), (2150, 2005)]]
    + [("wing_le_L", uv) for uv in [(2850, 2021), (3000, 2004), (3200, 1982), (3400, 1960), (3600, 1937), (3800, 1914)]],
    glazing_side=None,
)

# =============================================================================================
# 5. rendering (render/blender_ortho.py perspective mode) and overlays
# =============================================================================================
COCKPIT_BOX = np.array([[x, y, z] for x in (2.9, 4.75) for y in (-0.9, 0.9) for z in (1.75, 2.8)])
MAX_RENDER_PX = 5.2e6


def render_jobs(pid, cam, crop_cam=None, crop_scale=1.0, out_dir=None, samples=16):
    """Blender jobs for one photo: full frame (lines, shaded) and the cockpit close-up (lines, shaded)."""
    out_dir = Path(out_dir or OUT)
    s = min(1.0, float(np.sqrt(MAX_RENDER_PX / (cam.W * cam.H))))
    full = cam.scaled(s) if s < 1.0 else cam
    jobs = []
    for style in ("lines", "shaded"):
        jobs.append(dict(view="persp", camera=full.to_json(), style=style, samples=samples,
                         out=str(out_dir / f"{pid}_render_{style}.png"), line_px=1.2, sil_px=2.0))
    if crop_cam is not None:
        for style in ("lines", "shaded"):
            jobs.append(dict(view="persp", camera=crop_cam.to_json(), style=style, samples=samples,
                             out=str(out_dir / f"{pid}_ck_render_{style}.png"), line_px=1.5, sil_px=2.5))
    return jobs, s


def cockpit_crop(cam, pad=0.12, target_w=1800, extra_pts=()):
    """Pixel box (original photo pixels) around the cockpit + the crop camera at `scale`."""
    pts = np.vstack([COCKPIT_BOX] + [np.atleast_2d(p) for p in extra_pts if len(p)])
    uv, z = cam.project(pts, True)
    uv = uv[z > 0]
    x0, y0 = uv.min(0)
    x1, y1 = uv.max(0)
    w, h = x1 - x0, y1 - y0
    x0, x1 = max(0, x0 - pad * w), min(cam.W, x1 + pad * w)
    y0, y1 = max(0, y0 - pad * h), min(cam.H, y1 + pad * h)
    box = (int(np.floor(x0)), int(np.floor(y0)), int(np.ceil(x1)), int(np.ceil(y1)))
    bw, bh = box[2] - box[0], box[3] - box[1]
    scale = min(4.0, target_w / bw)
    if bw * bh * scale * scale > MAX_RENDER_PX:
        scale = float(np.sqrt(MAX_RENDER_PX / (bw * bh)))
    cc = cam.scaled(scale, W=int(round(bw * scale)), H=int(round(bh * scale)), ox=box[0], oy=box[1])
    return box, scale, cc


def ink_overlay(photo, lines_png, color=(255, 0, 200), dim=0.55, alpha=1.0):
    """Model edges (black-on-white 'lines' render) laid over a dimmed copy of the photo."""
    from PIL import Image
    ph = photo.convert("RGB")
    L = Image.open(lines_png).convert("RGBA")
    if L.size != ph.size:
        L = L.resize(ph.size, Image.LANCZOS)
    a = np.asarray(L, np.float32) / 255.0
    ink = (1.0 - a[..., :3].mean(-1)) * a[..., 3]
    base = np.asarray(ph, np.float32)
    grey = base.mean(-1, keepdims=True)
    base = (0.5 * base + 0.5 * grey) * dim + 255 * (1 - dim) * 0.25
    col = np.array(color, np.float32)
    out = base * (1 - alpha * ink[..., None]) + col * alpha * ink[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def blend(photo, shaded_png, alpha=0.5):
    from PIL import Image
    ph = photo.convert("RGB")
    S = Image.open(shaded_png).convert("RGB")
    if S.size != ph.size:
        S = S.resize(ph.size, Image.LANCZOS)
    return Image.blend(ph, S, alpha)


def _font(size):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_polyline(dr, uv, color, width=2, dash=None, closed=False):
    uv = [tuple(map(float, p)) for p in uv]
    if closed and uv:
        uv = uv + [uv[0]]
    if not dash:
        dr.line(uv, fill=color, width=width, joint="curve")
        return
    on, off = dash
    acc, draw = 0.0, True
    for a, b in zip(uv[:-1], uv[1:]):
        L = float(np.hypot(b[0] - a[0], b[1] - a[1]))
        t = 0.0
        while t < L:
            seg = min((on if draw else off) - acc, L - t)
            if draw:
                p = (a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L)
                q = (a[0] + (b[0] - a[0]) * (t + seg) / L, a[1] + (b[1] - a[1]) * (t + seg) / L)
                dr.line([p, q], fill=color, width=width)
            t += seg
            acc += seg
            if acc >= (on if draw else off) - 1e-9:
                acc, draw = 0.0, not draw


# =============================================================================================
# 6. model glazing outlines (vector, from the GLB) for drawing and measuring
# =============================================================================================
def _boundary_segments(V, F, tol=1e-5):
    key = np.round(V / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    Fw = inv[F]
    E = np.sort(np.concatenate([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]]), axis=1)
    u, c = np.unique(E, axis=0, return_counts=True)
    Vw = V[first]
    B = u[c == 1]
    return Vw[B[:, 0]], Vw[B[:, 1]]


def model_glazing(prims=None):
    """-> dict name -> (A (n,3), B (n,3)) boundary segments of the model's cockpit glazing:
    'ws' windshield panes, 'sw' side windows, 'mask' outer outline of the dark surround (trim_black
    boundary edges that are not on a pane edge)."""
    prims = prims if prims is not None else read_glb()
    out = {}
    V, F = select(prims, ["glazing_flightdeck"], ["glass_windshield"])
    out["ws"] = _boundary_segments(V, F)
    V, F = select(prims, ["glazing_flightdeck"], ["glass"])
    out["sw"] = _boundary_segments(V, F)
    V, F = select(prims, ["fus_fwd", "fus_center"], ["trim_black"])
    A, B = _boundary_segments(V, F)
    G = np.vstack([out["ws"][0], out["sw"][0]])
    from scipy.spatial import cKDTree
    d, _ = cKDTree(G).query(0.5 * (A + B))
    out["mask"] = (A[d > 0.012], B[d > 0.012])
    out["mask_inner"] = (A[d <= 0.012], B[d <= 0.012])
    return out


def visible(cam, P, skin_tri, eps=0.01):
    """True where model points P are not hidden by the skin triangles (ray from the camera)."""
    P = np.atleast_2d(P)
    d = P - cam.C
    L = np.linalg.norm(d, axis=1)
    t = ray_mesh(cam.C, d / L[:, None], skin_tri)
    return ~(t < L - eps)


def ray_mesh(O, D, T, chunk=256):
    """First hit distance of rays O + t D (D unit, (N,3); O (3,) or (N,3)) with triangles T (M,3,3)."""
    D = np.atleast_2d(D)
    O = np.broadcast_to(np.asarray(O, float), D.shape)
    v0 = T[:, 0]
    e1 = T[:, 1] - v0
    e2 = T[:, 2] - v0
    out = np.full(len(D), np.inf)
    for i in range(0, len(D), chunk):
        d = D[i:i + chunk, None, :]
        o = O[i:i + chunk, None, :]
        p = np.cross(d, e2[None])
        det = np.einsum("ijk,jk->ij", p, e1)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = o - v0[None]
        u = np.einsum("ijk,ijk->ij", s, p) * inv
        q = np.cross(s, e1[None])
        v = np.einsum("ijk,ijk->ij", d, q) * inv
        t = np.einsum("ijk,jk->ij", q, e2) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
        t = np.where(hit, t, np.inf)
        out[i:i + chunk] = t.min(1)
    return out


# =============================================================================================
# 7. per-photo pipeline
# =============================================================================================
COL = dict(model=(255, 0, 200), glass=(0, 230, 255), mask=(255, 150, 0), dwg=(255, 235, 0),
           kp=(0, 255, 0), proj=(255, 40, 40), trace=(60, 255, 120))


class Context:
    """Shared, lazily built geometry."""

    def __init__(self, use_drawing=True):
        from scipy.spatial import cKDTree
        self.prims = read_glb()
        self.ref = Reference(self.prims, use_drawing=use_drawing)
        self.mg = model_glazing(self.prims)
        # outward skin normals near the cockpit (outer faces only) for back-face visibility tests
        V, F = select(self.prims, ["fus_fwd", "cowl_upper", "cowl_lower", "fus_center"])
        T = V[F]
        c = T.mean(1)
        keep = c[:, 0] < 5.5
        T, c = T[keep], c[keep]
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        axis = np.c_[c[:, 0], np.zeros(len(c)), np.full(len(c), 1.75)]
        n[np.einsum("ij,ij->i", n, c - axis) < 0] *= -1          # orient outward (convex-ish body)
        self.nrm_tree, self.nrm = cKDTree(c), n
        Vs, Fs = select(self.prims, ["fus_fwd", "glazing_flightdeck", "cowl_upper"])
        self.skin_tri = Vs[Fs]
        self.ref_tri = self.ref.corrected_skin()

    def facing(self, cam, P, tol=0.02):
        """True where the skin at P faces the camera (back-face test with the outward normal)."""
        P = np.atleast_2d(P)
        _, j = self.nrm_tree.query(P)
        v = cam.C - P
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        return np.einsum("ij,ij->i", self.nrm[j], v) > -tol


def solve_photo(ctx, pid, verbose=True):
    from PIL import Image
    ph = PHOTOS[pid]
    W, H = Image.open(PHOTO_DIR / ph["file"]).size
    S = Solver(ctx.ref, W, H, ph["pts"], ph.get("on", ()), sigma_px=ph.get("sigma_px", 1.5),
               free_pp=ph.get("free_pp", False), weights=ph.get("weights"))
    for k in ph.get("exclude", ()):
        S.active.discard(k)
    cam = S.solve(reject_sigma=ph.get("reject_sigma", 4.0), f_guess=ph.get("f_guess"))
    rep = S.report()
    rep["rejected"] = S.rejected
    rep["missing"] = S.missing
    rep["camera"] = cam.describe()
    if verbose:
        print(f"[{pid}] {cam.describe()}")
        print(f"[{pid}] rms {rep['rms_px']:.2f} px over {rep['n_used']} constraints "
              f"(points {rep['rms_pt_px']:.2f} px, n={rep['n_pt']}); rejected {S.rejected}; missing {S.missing}")
    return cam, S, rep


def draw_diagnostics(ctx, pid, cam, S, out):
    """Photo + measured keypoints, reprojected reference points / curves, model glazing and drawing glazing."""
    from PIL import Image, ImageDraw
    ph = PHOTOS[pid]
    im = Image.open(PHOTO_DIR / ph["file"]).convert("RGB")
    k = max(1.0, im.width / 2400)
    lw = max(1, int(round(1.5 * k)))
    dr = ImageDraw.Draw(im)
    fnt = _font(int(13 * k))
    for c, uv in S.on:
        pass
    drawn = set()
    for c, _ in S.on:
        if c in drawn:
            continue
        drawn.add(c)
        P = ctx.ref.curves[c][0]
        q, z = cam.project(P, True)
        for u, v in q[z > 0][::2]:
            dr.point((u, v), fill=COL["dwg"])
    for i, (c, uv) in enumerate(S.on):
        col = COL["kp"] if i in S.active else (128, 128, 128)
        r = 3 * k
        dr.ellipse([uv[0] - r, uv[1] - r, uv[0] + r, uv[1] + r], outline=col, width=lw)
    for name, uv in S.pts.items():
        X = ctx.ref.pts[name][0]
        q = cam.project(X)[0]
        col = COL["kp"] if name in S.active else (128, 128, 128)
        r = 6 * k
        dr.ellipse([uv[0] - r, uv[1] - r, uv[0] + r, uv[1] + r], outline=col, width=lw)
        dr.line([(q[0] - r, q[1]), (q[0] + r, q[1])], fill=COL["proj"], width=lw)
        dr.line([(q[0], q[1] - r), (q[0], q[1] + r)], fill=COL["proj"], width=lw)
        dr.line([tuple(uv), tuple(uv + 10 * (q - uv))], fill=COL["proj"], width=1)
        dr.text((uv[0] + 8 * k, uv[1] + 4 * k), name, fill=col, font=fnt)
    im.save(out, quality=90)


def project_segments(cam, AB, ctx=None):
    A, B = AB
    if ctx is not None and len(A):
        vis = ctx.facing(cam, 0.5 * (A + B))
        A, B = A[vis], B[vis]
    qa, za = cam.project(A, True)
    qb, zb = cam.project(B, True)
    ok = (za > 0) & (zb > 0)
    return qa[ok], qb[ok]


def draw_vectors(ctx, img, cam, trace=None, width=2, dwg=True):
    """Model glazing / mask outlines (vector) + drawing glazing (dashed) + photo traces on img."""
    from PIL import ImageDraw
    dr = ImageDraw.Draw(img)
    for key, col in (("mask", COL["mask"]), ("ws", COL["glass"]), ("sw", COL["glass"])):
        qa, qb = project_segments(cam, ctx.mg[key], ctx)
        for a, b in zip(qa, qb):
            dr.line([tuple(a), tuple(b)], fill=col, width=width)
    if dwg and getattr(ctx.ref, "glazing", None):
        for name, P in ctx.ref.glazing.items():
            P = P[np.isfinite(P).all(1)]
            if len(P) < 2:
                continue
            vis = ctx.facing(cam, P)
            q, z = cam.project(P, True)
            q[~vis | (z <= 0)] = np.nan
            segs, cur = [], []
            for p in q:
                if np.isfinite(p).all():
                    cur.append(p)
                elif cur:
                    segs.append(cur); cur = []
            if cur:
                segs.append(cur)
            for sgm in segs:
                if len(sgm) > 1:
                    draw_polyline(dr, sgm, COL["dwg"], width=max(1, width - 1), dash=(6 * width, 5 * width))
    if trace:
        for name, uv in trace.items():
            draw_polyline(dr, uv, COL["trace"], width=width, dash=(3 * width, 3 * width))
    return img


def _render_current(job, tol=1e-6):
    """True if job['out'] exists and its sidecar was rendered with the same camera and GLB."""
    sc = Path(job["out"]).with_suffix(".json")
    if not Path(job["out"]).exists() or not sc.exists():
        return False
    try:
        j = json.loads(sc.read_text())
        P = np.asarray(j["P"], float)
        cam = Camera.from_json(job["camera"])
        if abs(float(j.get("glb_mtime", 0)) - GLB.stat().st_mtime) > 1:
            return False
        return int(j["width"]) == cam.W and int(j["height"]) == cam.H and \
            np.allclose(P / P[2, 3], cam.P / cam.P[2, 3], rtol=1e-5, atol=1e-3)
    except Exception:
        return False


def process(ctx, pid, do_render=True, out_dir=None, samples=16, verbose=True, reuse=True):
    from PIL import Image
    out_dir = Path(out_dir or OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    ph = PHOTOS[pid]
    photo = Image.open(PHOTO_DIR / ph["file"]).convert("RGB")
    cam, S, rep = solve_photo(ctx, pid, verbose)
    cmp_ = compare(ctx, pid, cam, photo)
    trace = cmp_["trace_uv"]
    extra = [np.array(ctx.ref.pts[k][0]) for k in ph.get("crop_include", ()) if k in ctx.ref.pts]
    box, cs, ccam = cockpit_crop(cam, extra_pts=extra)
    res = dict(pid=pid, file=ph["file"], camera=cam.to_json(), camera_text=cam.describe(), report=rep,
               crop_box=box, crop_scale=cs, crop_camera=ccam.to_json(), compare=cmp_)
    (out_dir / f"{pid}_camera.json").write_text(json.dumps(res, indent=1, default=float))
    draw_diagnostics(ctx, pid, cam, S, out_dir / f"{pid}_keypoints.jpg")
    if not do_render:
        return res, cam, ccam
    from render import blender_ortho as bo
    jobs, s = render_jobs(pid, cam, ccam, cs, out_dir, samples)
    jobs = [j for j in jobs if not (reuse and _render_current(j))]
    t0 = __import__("time").time()
    if jobs:
        bo.render_many(jobs)
    if verbose:
        print(f"[{pid}] rendered {len(jobs)} jobs in {__import__('time').time() - t0:.0f} s")
    # full-frame overlays
    ink_overlay(photo, out_dir / f"{pid}_render_lines.png").save(out_dir / f"{pid}_overlay_lines.jpg", quality=90)
    blend(photo, out_dir / f"{pid}_render_shaded.png").save(out_dir / f"{pid}_blend50.jpg", quality=90)
    # cockpit close-up
    crop = photo.crop(box).resize((ccam.W, ccam.H), Image.LANCZOS)
    crop.save(out_dir / f"{pid}_ck_photo.jpg", quality=92)
    tr = {k: (np.asarray(v, float) - box[:2]) * cs for k, v in trace.items()}
    ov = ink_overlay(crop, out_dir / f"{pid}_ck_render_lines.png", dim=0.7)
    draw_vectors(ctx, ov, ccam, tr, width=2)
    ov.save(out_dir / f"{pid}_ck_overlay.jpg", quality=92)
    bl = blend(crop, out_dir / f"{pid}_ck_render_shaded.png")
    draw_vectors(ctx, bl, ccam, tr, width=2)
    bl.save(out_dir / f"{pid}_ck_blend50.jpg", quality=92)
    return res, cam, ccam


# =============================================================================================
# 8. glazing comparison: traced photo features vs the model (image distance + back-projection)
# =============================================================================================
def dark_region(img, box, max_rgb=75, seed=None, close=2):
    """Largest (or seed-containing) connected dark region inside box -> bool mask (full image)."""
    from scipy import ndimage
    A = np.asarray(img.convert("RGB"), np.int16)
    x0, y0, x1, y1 = box
    c = A[y0:y1, x0:x1]
    dark = c.max(-1) < max_rgb
    if close:
        dark = ndimage.binary_closing(dark, iterations=close)
    lab, n = ndimage.label(dark)
    if n == 0:
        return np.zeros(A.shape[:2], bool)
    if seed is not None:
        k = lab[int(seed[1]) - y0, int(seed[0]) - x0]
    else:
        k = np.argmax(ndimage.sum(dark, lab, range(1, n + 1))) + 1
    M = ndimage.binary_fill_holes(lab == k)
    out = np.zeros(A.shape[:2], bool)
    out[y0:y1, x0:x1] = M
    return out


def region_outline(img, M, min_lum=150, step=2.0, probe=3.0):
    """Outline of mask M (corner-origin pixel coords) where the pixels just outside are bright
    (painted skin) -> list of polylines."""
    import contourpy
    from scipy import ndimage
    L = np.asarray(img.convert("L"), np.float32)
    Ms = ndimage.gaussian_filter(M.astype(np.float32), 1.0)
    gy, gx = np.gradient(Ms)
    cg = contourpy.contour_generator(z=Ms, line_type="Separate")
    out = []
    for P in cg.lines(0.5):                       # P columns: x (col index), y (row index)
        if len(P) < 10:
            continue
        # resample to `step`
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        s = np.r_[0, np.cumsum(seg)]
        si = np.arange(0, s[-1], step)
        Q = np.stack([np.interp(si, s, P[:, 0]), np.interp(si, s, P[:, 1])], 1)
        ix = np.clip(np.round(Q[:, 0]).astype(int), 0, M.shape[1] - 1)
        iy = np.clip(np.round(Q[:, 1]).astype(int), 0, M.shape[0] - 1)
        g = np.stack([gx[iy, ix], gy[iy, ix]], 1)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        pr = Q - probe * g                       # outside (gradient points into the region)
        px = np.clip(np.round(pr[:, 0]).astype(int), 0, M.shape[1] - 1)
        py = np.clip(np.round(pr[:, 1]).astype(int), 0, M.shape[0] - 1)
        ok = L[py, px] > min_lum
        Q = Q + 0.5                              # pixel-centre index -> corner-origin coordinate
        cur = []
        for q, o in zip(Q, ok):
            if o:
                cur.append(q)
            elif len(cur) > 3:
                out.append(np.array(cur)); cur = []
            else:
                cur = []
        if len(cur) > 3:
            out.append(np.array(cur))
    return out


def backproject(cam, uv, tri):
    """Pixels -> first hit on the triangles (model coordinates); NaN where the ray misses."""
    uv = np.atleast_2d(np.asarray(uv, float))
    D = cam.ray(uv)
    t = ray_mesh(cam.C, D, tri, chunk=64)
    X = cam.C + D * t[:, None]
    X[~np.isfinite(t)] = np.nan
    return X


def seg_distance(q, A, B):
    """Distance from 2-D points q (N,2) to the nearest of segments A-B (M,2) -> d (N,), foot (N,2), index."""
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    best = np.full(len(q), np.inf)
    foot = np.zeros_like(q)
    idx = np.zeros(len(q), int)
    for i0 in range(0, len(A), 4096):
        a, ab, l2 = A[i0:i0 + 4096], AB[i0:i0 + 4096], L2[i0:i0 + 4096]
        t = np.clip(((q[:, None, :] - a[None]) * ab[None]).sum(-1) / l2[None], 0, 1)
        P = a[None] + t[..., None] * ab[None]
        d = np.linalg.norm(q[:, None, :] - P, axis=-1)
        j = d.argmin(1)
        dj = d[np.arange(len(q)), j]
        m = dj < best
        best[m] = dj[m]
        foot[m] = P[np.arange(len(q)), j][m]
        idx[m] = j[m] + i0
    return best, foot, idx


def _front_edge(P, lo=0.25, hi=0.75):
    """Front (min-x) edge of a closed side-projection outline between lo..hi of its height ->
    (slope dz/dx, x at z) as a function; points used."""
    z0, z1 = np.percentile(P[:, 2], 2), np.percentile(P[:, 2], 98)
    H = z1 - z0
    bins = np.linspace(z0 + lo * H, z0 + hi * H, 12)
    pts = []
    for a, b in zip(bins[:-1], bins[1:]):
        m = (P[:, 2] >= a) & (P[:, 2] < b)
        if m.any():
            i = np.argmin(np.where(m, P[:, 0], np.inf))
            pts.append(P[i])
    pts = np.array(pts)
    if len(pts) < 3:
        return None, None, pts
    b, a = np.polyfit(pts[:, 2], pts[:, 0], 1)          # x = a + b z
    return (lambda z: a + b * z), float(np.degrees(np.arctan2(1.0, b))), pts


def measure_side_outline(P):
    """Side-projection measures of a closed outline (side window glass or mask) in MODEL coordinates."""
    P = P[np.isfinite(P).all(1)]
    if len(P) < 8:
        return {}
    zmin, zmax = P[:, 2].min(), P[:, 2].max()
    sill = float(np.median(P[P[:, 2] < zmin + 0.015, 2]))
    top = float(np.median(P[P[:, 2] > zmax - 0.015, 2]))
    ia = np.argmax(P[:, 0])
    xf, ang, _ = _front_edge(P)
    out = dict(sill_z=sill, top_z=top, height=top - sill, aft_x=float(P[ia, 0]),
               aft_z=float(np.mean(P[P[:, 0] > P[ia, 0] - 0.006, 2])), fwd_x=float(P[:, 0].min()),
               fwd_z=float(P[np.argmin(P[:, 0]), 2]))
    if xf is not None:
        out.update(front_angle_deg=ang, front_x_at_sill=float(xf(sill)), front_x_at_top=float(xf(top)),
                   front_x_mid=float(xf(0.5 * (sill + top))), sill_len=float(P[ia, 0] - xf(sill)),
                   top_len=float(P[ia, 0] - xf(top)))
    return out


def model_outline_pts(ctx, key, side=None, cam=None):
    A, B = ctx.mg[key]
    P = np.vstack([A, B])
    if side is not None:
        P = P[side * P[:, 1] > 0.02]
    if cam is not None:
        P = P[ctx.facing(cam, P)]
    return P


def _densify2(P, step):
    P = np.asarray(P, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    sc = np.r_[0, np.cumsum(seg)]
    si = np.linspace(0, sc[-1], max(2, int(sc[-1] / step) + 1))
    return np.stack([np.interp(si, sc, P[:, 0]), np.interp(si, sc, P[:, 1])], 1)


def compare(ctx, pid, cam, photo):
    """Traced photo glazing features -> model coordinates on the model skin; image offsets to the model
    outlines (px and mm at the feature depth); side-view measures photo vs model."""
    ph = PHOTOS[pid]
    res = dict(traces={}, measures={})
    tri = ctx.ref_tri
    traces = {k: np.asarray(v, float) for k, v in ph.get("trace", {}).items()}
    am = ph.get("auto_mask")
    if am:
        M = dark_region(photo, am["box"], am.get("max_rgb", 75), am.get("seed"))
        polys = region_outline(photo, M, am.get("min_lum", 150))
        polys = [p for p in polys if len(p) > am.get("min_pts", 15)]
        for i, p in enumerate(polys):
            traces[f"mask_auto{i}"] = p
    res["trace_uv"] = {k: v.tolist() for k, v in traces.items()}
    traces = {k: _densify2(v, 1.5) for k, v in traces.items()}
    side = ph.get("glazing_side")
    for name, uv in traces.items():
        key = "sw" if name.startswith("sw") else "ws" if name.startswith(("ws", "post")) else "mask"
        qa, qb = project_segments(cam, ctx.mg[key], ctx)
        A3, B3 = ctx.mg[key]
        vis = ctx.facing(cam, 0.5 * (A3 + B3))
        A3, B3 = A3[vis], B3[vis]
        za = cam.project(A3, True)[1]
        d, foot, j = seg_distance(uv, qa, qb)
        depth = za[j]
        mm = d * depth / cam.f * 1000.0
        X = backproject(cam, uv, tri)
        res["traces"][name] = dict(n=len(uv), px_mean=float(np.mean(d)), px_max=float(np.max(d)),
                                   mm_mean=float(np.mean(mm)), mm_max=float(np.max(mm)),
                                   hit_frac=float(np.isfinite(X[:, 0]).mean()),
                                   X=np.round(X, 4).tolist(), d_px=np.round(d, 2).tolist(),
                                   d_mm=np.round(mm, 1).tolist())
    # side-view measures of the side window glass and the mask outline
    if side is not None:
        sw = [k for k in traces if k.startswith("sw")]
        if sw:
            Pp = np.vstack([np.asarray(res["traces"][k]["X"], float) for k in sw])
            res["measures"]["side_window"] = dict(photo=measure_side_outline(Pp),
                                                  model=measure_side_outline(model_outline_pts(ctx, "sw", side)))
        mk = [k for k in traces if k.startswith("mask")]
        if mk:
            Pp = np.vstack([np.asarray(res["traces"][k]["X"], float) for k in mk])
            Pm = model_outline_pts(ctx, "mask", side, cam)
            res["measures"]["mask_side"] = dict(photo=_mask_measures(Pp, side), model=_mask_measures(Pm, side))
    return res


def _mask_measures(P, side):
    """Mask outline on one side (side projection): rear boundary (max x per 2 cm WL bin) -> aft edge x at
    its top and bottom; lower / upper boundary (min / max z per 2 cm station bin, between the side
    window's front and the aft edge) -> bottom and top WL; forward-most point on this side."""
    P = P[np.isfinite(P).all(1)]
    P = P[(side * P[:, 1] > 0.25) & (P[:, 0] > 3.3)]
    if len(P) < 5:
        return {}
    zb = np.round(P[:, 2] / 0.02)
    rear = np.array([P[zb == k][np.argmax(P[zb == k, 0])] for k in np.unique(zb)])
    xa = P[:, 0].max()
    rear = rear[rear[:, 0] > xa - 0.12]
    out = dict(aft_x=float(xa))
    if len(rear) >= 3:
        z0, z1 = rear[:, 2].min(), rear[:, 2].max()
        hi = rear[rear[:, 2] > z1 - 0.06]
        lo = rear[rear[:, 2] < z0 + 0.06]
        out.update(aft_x_top=float(np.median(hi[:, 0])), aft_x_bottom=float(np.median(lo[:, 0])),
                   aft_z_top=float(z1), aft_z_bottom=float(z0))
    mid = P[(P[:, 0] > 3.8) & (P[:, 0] < xa - 0.1)]
    if len(mid):
        xb = np.round(mid[:, 0] / 0.02)
        lo = np.array([mid[xb == k, 2].min() for k in np.unique(xb)])
        hi = np.array([mid[xb == k, 2].max() for k in np.unique(xb)])
        out.update(bottom_z=float(np.median(lo)), top_z=float(np.median(hi)))
    return out
