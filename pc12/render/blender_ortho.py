"""
render.blender_ortho -- calibrated Blender/Cycles renders of out/pc12.glb.

Every PNG comes with a sidecar JSON holding the exact MODEL -> pixel mapping, so renders can be
overlaid with the Pilatus drawing, camera-matched photos or our own 2-D geometry (refs/overlay.py).

Runs in the separate Blender venv (Blender 5 as a Python module, Cycles on CPU; EEVEE does not work
headless here).  The module has no top-level bpy import: from the system python3 it can still be
imported (view maths, projection helpers) and render() transparently re-runs itself in the venv.

Model coordinates: x = station [m] aft of the W&B datum, y = butt line (+ starboard), z = water line
(ground = 0).  glTF -> Blender import gives Blender (X, Y, Z) = (y, -x, z); the importer's root
empties are rotated +90 deg about Z so that Blender world coordinates == MODEL coordinates.

Orthographic views (image u to the right, v down):
    side_port   seen from port  (camera at -y looking +y): nose LEFT,  u = +x, up = +z
    side_stbd   seen from starboard:                       nose RIGHT, u = -x, up = +z
    top         seen from above, u = +x, DOWN = +y (starboard at the bottom).  NOTE: with the nose on
                the left a real top view has starboard at the TOP, so 'top' is the mirror image of
                what an observer above sees (same mapping as 'bottom'; drafting-style plan).  It is
                rendered from above and flipped; the sidecar P describes the written image exactly.
    top_true    physical view from above: u = +x, UP = +y (starboard at the top)
    bottom      seen from below: u = +x, down = +y (physically correct, starboard at the bottom)
    front       seen from ahead: up = +z, starboard (+y) on the LEFT  (u = -y)
    rear        seen from behind: up = +z, starboard on the RIGHT     (u = +y)
  Aliases: side -> side_port, plan -> top, port -> side_port, stbd -> side_stbd.
  Region: bounds in the view's natural axes (side: x0,x1,z0,z1; top/bottom: x0,x1,y0,y1;
  front/rear: y0,y1,z0,z1); default = bounding box of the visible parts + margin.  Size: px_per_m
  or width (or height).  Bounds are adjusted (about their centre) to a whole number of pixels; the
  sidecar gives the adjusted values.

Perspective ('persp'): camera = dict with either
    position, target, up (default 0,0,1), fov (vertical deg) | hfov (horizontal deg)
    P: 3x4 projection matrix                               (decomposed with RQ into K [R | t])
    K (3x3) or fx, fy, cx, cy  plus  R (3x3) and t (3) or C (camera centre)   OpenCV camera axes
        (x right, y down, z forward; X_cam = R X_model + t)
    pixel_origin: 'corner' (default: u = 0 at the left edge of the image) | 'center' (OpenCV:
        u = 0 at the centre of the first pixel; converted by +0.5)
  plus width/height (or a 'size' WxH).  Blender cameras have square pixels and no skew: fy is set
  to fx (warning if they differ by > 0.1 %), skew dropped; the sidecar P is the one realised.

Styles: shaded (GLB materials, even studio light = uniform white world + camera-relative key/fill
suns, 8 spp + OIDN; glass tinted blue-grey and opaque so the panes read against the black surround
trim; glass='original'|'clear'|'dark' to change), clay (matte grey, glass dark), lines (black
silhouette / occlusion / crease / material-boundary edges on white, derived with numpy from Cycles
object-index, material-index, normal and depth passes rendered at 1 spp with a 0.01 px box filter,
i.e. sampled at the (supersampled) pixel centres; supersample 0 = auto: 3x up to 1.5 Mpx, 2x up to
6 Mpx, else 1x; isolated specks from sliver triangles are dropped), shaded+lines, clay+lines (edges
over the shading), freestyle (Blender Freestyle; works headless but is ~3-10x slower than 'lines' and
also draws the mesh split lines between skin parts; kept for comparison).
Line options: line_px (inner lines) / sil_px (silhouettes) in output pixels, crease_deg (normal
break), line_detail = outline (silhouette + occlusion) | normal (+ creases + material boundaries,
livery paints merged) | full (+ livery), fill='glass' (light blue tint on the glazing), line_color.
Background: bg = white | transparent (RGBA) | '#rrggbb'.

Part filters (prefixes of the node extras 'part' ids; a mesh matches if its own part id or that of
any ancestor part starts with the prefix, so 'propeller' includes the blades): only=..., hide=...
Default hide = 'structure'.  With only given and no hide, nothing is hidden.

Sidecar JSON (same basename, .json):  P (3x4) with [u*w, v*w, w] = P @ [x, y, z, 1] (u right,
v down, origin at the top-left pixel CORNER: the first pixel's centre is (0.5, 0.5); w == 1 for
ortho), width, height, view, projection, bounds / bounds_list / px_per_m / centre (ortho),
fov / warnings (perspective), camera (Blender camera + OpenCV K/R/t/C for perspective), image_axes
(model directions of image right / down / look), style, settings, parts_shown / parts_hidden,
timings, and 'blender_check_px' (bbox corners projected by P vs. Blender's own camera frame; ~1e-3
px, the residue of Blender storing ortho_scale in float32).  Optional outputs: <name>.mask.png
(8-bit coverage: Cycles alpha for shaded/clay, supersampled geometry coverage for lines) and
<name>.ids.png (16-bit part index of the first surface hit at the pixel centre -- with an even
supersampling factor the sample sits 0.25 px off-centre; sidecar 'part_index' maps index -> part
id; 0 = background).  Verified with render/check_mapping.py: projected extreme vertices (spinner
tip, tail, fin top, winglet tips, wheel contacts, glazing edges, centre post) land within 0.7 px
of the rendered silhouettes / part edges in all six test views, perspective renders within 0.6 px.

CLI (from pc12/):
    /opt/venv-blender/bin/python render/blender_ortho.py --view side_port,top,front --style shaded
    python3 render/blender_ortho.py --view side --style lines --bounds 2.6,4.8,1.5,2.8 --px-per-m 900
    python3 -m render.blender_ortho --view front --style shaded+lines --hide cabin_interior,structure \\
        --bounds -1.1,1.1,1.3,2.8 --width 2000 --mask --ids --out out/tmp/render/front_ck.png
    python3 -m render.blender_ortho --view persp --cam-pos -6,-9,4 --target 4,0,1.6 --fov 35 --size 1600x1000
    python3 -m render.blender_ortho --view persp --camera-json cam.json --size 4000x3000
    python3 -m render.blender_ortho --jobs jobs.json          # list of job dicts, one Blender session
  (system python3 re-executes in /opt/venv-blender automatically; override with $BLENDER_PYTHON)

Python API:
    from render import blender_ortho as bo
    res = bo.render(view='side_port', style='lines', bounds=(2.6, 4.8, 1.5, 2.8), px_per_m=900,
                    out='out/tmp/render/side_ck_lines.png')          # -> dict (paths, sidecar, seconds)
    res = bo.render_many([job1, job2, ...])                          # one Blender session
    P, W, H, info = bo.ortho_setup('top', bounds=(2.6, 4.8, -1, 1), px_per_m=900)   # no rendering
    uv = bo.project(P, pts)                                          # (N,3) -> (N,2) pixels

Timings (4 CPUs, measured while other jobs kept the load average at 5-15, so an idle machine is
faster): GLB import ~1 s; 2000 px wide, 8 spp + OIDN (fast): side full shaded 14 s / lines 4-19 s,
front full 7 s / 4-10 s, top full (2000x2253) 31 s / 5-23 s, cockpit crops (2.4-3.6 Mpx, fully
covered) 31-43 s / 15-25 s.  Shaded time scales with pixels x samples (denoise='high' roughly
doubles it); 'lines' is bound by the 1-spp ID render and the EXR hand-over (~40 bytes per
supersampled pixel, temporary files in out/tmp/render/_work_*, deleted afterwards).
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings("ignore", message=".*use_nodes.*", category=DeprecationWarning)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GLB = ROOT / "out" / "pc12.glb"
OUT_DIR = ROOT / "out" / "tmp" / "render"
BLENDER_PY = os.environ.get("BLENDER_PYTHON", "/opt/venv-blender/bin/python")
RESULT_TAG = "BLENDER_ORTHO_RESULT "

# =============================================================================================
# 1. views and projection maths (pure numpy, usable from any interpreter)
# =============================================================================================

VIEWS = {
    "side_port": dict(right=(1, 0, 0), down=(0, 0, -1), look=(0, 1, 0), axes="xz"),
    "side_stbd": dict(right=(-1, 0, 0), down=(0, 0, -1), look=(0, -1, 0), axes="xz"),
    "top": dict(right=(1, 0, 0), down=(0, 1, 0), look=(0, 0, -1), axes="xy"),
    "top_true": dict(right=(1, 0, 0), down=(0, -1, 0), look=(0, 0, -1), axes="xy"),
    "bottom": dict(right=(1, 0, 0), down=(0, 1, 0), look=(0, 0, 1), axes="xy"),
    "front": dict(right=(0, -1, 0), down=(0, 0, -1), look=(1, 0, 0), axes="yz"),
    "rear": dict(right=(0, 1, 0), down=(0, 0, -1), look=(-1, 0, 0), axes="yz"),
}
ALIASES = {"side": "side_port", "port": "side_port", "stbd": "side_stbd", "starboard": "side_stbd",
           "plan": "top", "perspective": "persp"}
AX = {"x": 0, "y": 1, "z": 2}
STYLES = ("shaded", "clay", "lines", "shaded+lines", "clay+lines", "freestyle")
DEFAULT_HIDE = ("structure",)


def view_name(v):
    v = str(v).strip().lower()
    return ALIASES.get(v, v)


def view_basis(view):
    """-> right, down, look (unit model vectors) and 'mirrored' (image frame is left-handed)."""
    d = VIEWS[view_name(view)]
    r, dn, lk = (np.array(d[k], float) for k in ("right", "down", "look"))
    mirrored = float(np.dot(np.cross(r, -dn), -lk)) < 0.0      # right x up must point at the viewer
    return r, dn, lk, mirrored


def project(P, pts):
    """Model points (N,3) -> pixel (N,2) with the sidecar matrix P (3x4)."""
    P = np.asarray(P, float)
    X = np.atleast_2d(np.asarray(pts, float))
    h = X @ P[:, :3].T + P[:, 3]
    return h[:, :2] / h[:, 2:3]


def ortho_setup(view, bounds=None, px_per_m=None, width=None, height=None, bbox=None, margin=0.25):
    """Orthographic view -> (P, W, H, info).

    bounds: (a0, a1, b0, b1) in the view's natural axes (side: x, z; top/bottom: x, y; front/rear:
    y, z); None -> bbox (x0, x1, y0, y1, z0, z1) of the model + margin.  Size from px_per_m, width
    or height (default width 2000).  The bounds are grown/shrunk about their centre to a whole number
    of pixels; info['bounds'] has the final values."""
    vn = view_name(view)
    r, dn, lk, mirrored = view_basis(vn)
    ax = VIEWS[vn]["axes"]
    ia, ib = AX[ax[0]], AX[ax[1]]
    if bounds is None:
        if bbox is None:
            raise ValueError("ortho_setup: need bounds or bbox")
        bb = np.asarray(bbox, float).reshape(3, 2)
        bounds = (bb[ia, 0] - margin, bb[ia, 1] + margin, bb[ib, 0] - margin, bb[ib, 1] + margin)
    a0, a1, b0, b1 = (float(v) for v in bounds)
    if a1 <= a0 or b1 <= b0:
        raise ValueError(f"bad bounds {bounds}")
    ac, bc = 0.5 * (a0 + a1), 0.5 * (b0 + b1)
    if px_per_m:
        s = float(px_per_m)
        W = max(1, int(round((a1 - a0) * s)))
        H = max(1, int(round((b1 - b0) * s)))
    elif height and not width:
        H = int(height)
        s = H / (b1 - b0)
        W = max(1, int(round((a1 - a0) * s)))
    else:
        W = int(width or 2000)
        s = W / (a1 - a0)
        H = max(1, int(round((b1 - b0) * s)))
        if height:
            H = int(height)
    a0, a1 = ac - 0.5 * W / s, ac + 0.5 * W / s
    b0, b1 = bc - 0.5 * H / s, bc + 0.5 * H / s
    c = np.zeros(3)
    c[ia], c[ib] = ac, bc
    P = np.zeros((3, 4))
    P[0, :3], P[0, 3] = s * r, 0.5 * W - s * float(c @ r)
    P[1, :3], P[1, 3] = s * dn, 0.5 * H - s * float(c @ dn)
    P[2, 3] = 1.0
    info = dict(view=vn, axes=ax, bounds={ax[0]: [a0, a1], ax[1]: [b0, b1]}, bounds_list=[a0, a1, b0, b1],
                px_per_m=s, centre=c.tolist(), mirrored=mirrored,
                image_axes=dict(right=r.tolist(), down=dn.tolist(), look=lk.tolist(), toward_viewer=(-lk).tolist()),
                ortho_width_m=W / s, ortho_height_m=H / s)
    return P, W, H, info


def rq3(M):
    """RQ decomposition of a 3x3 matrix: M = K @ R, K upper triangular with positive diagonal."""
    F = np.flipud(np.eye(3))
    Q, U = np.linalg.qr((F @ M).T)
    K = F @ U.T @ F
    R = F @ Q.T
    D = np.diag(np.sign(np.diag(K)))
    return K @ D, D @ R


def _vec(v, n=3):
    if isinstance(v, str):
        v = [float(t) for t in v.replace(" ", "").split(",")]
    a = np.asarray(v, float).ravel()
    if a.size != n:
        raise ValueError(f"expected {n} numbers, got {v}")
    return a


def persp_setup(camera, width=None, height=None):
    """Perspective camera dict (see module doc) -> (P, W, H, info) with P = K [R | t] realised by a
    Blender camera (square pixels, no skew), pixel origin at the top-left corner."""
    cam = dict(camera or {})
    W = int(cam.get("width") or width or 1600)
    H = int(cam.get("height") or height or 1000)
    warn = []
    corner = str(cam.get("pixel_origin", "corner")).lower() != "center"
    if "P" in cam:
        Pin = np.asarray(cam["P"], float).reshape(3, 4)
        K, R = rq3(Pin[:, :3])
        t = np.linalg.solve(K, Pin[:, 3])
        if np.linalg.det(R) < 0:
            R, t = -R, -t
        K = K / K[2, 2]
    elif "position" in cam or "pos" in cam:
        C = _vec(cam.get("position", cam.get("pos")))
        T = _vec(cam["target"])
        up = _vec(cam.get("up", (0, 0, 1)))
        f = T - C
        f /= np.linalg.norm(f)
        rgt = np.cross(f, up)
        if np.linalg.norm(rgt) < 1e-9:
            raise ValueError("camera up is parallel to the viewing direction")
        rgt /= np.linalg.norm(rgt)
        dwn = np.cross(f, rgt)
        R = np.stack([rgt, dwn, f])
        t = -R @ C
        if cam.get("hfov") is not None:
            fx = 0.5 * W / math.tan(math.radians(float(cam["hfov"])) / 2)
        else:
            fx = 0.5 * H / math.tan(math.radians(float(cam.get("fov", 40.0))) / 2)
        K = np.array([[fx, 0, 0.5 * W], [0, fx, 0.5 * H], [0, 0, 1.0]])
        corner = True
    else:
        if "K" in cam:
            K = np.asarray(cam["K"], float).reshape(3, 3)
            K = K / K[2, 2]
        else:
            fx = float(cam["fx"])
            fy = float(cam.get("fy", fx))
            K = np.array([[fx, float(cam.get("skew", 0.0)), float(cam.get("cx", 0.5 * W))],
                          [0, fy, float(cam.get("cy", 0.5 * H))], [0, 0, 1.0]])
        R = np.asarray(cam["R"], float).reshape(3, 3)
        if "t" in cam:
            t = _vec(cam["t"])
        else:
            t = -R @ _vec(cam["C"])
        if np.linalg.det(R) < 0:
            raise ValueError("R is not a rotation (det < 0)")
    if not corner:                              # OpenCV pixel centres at integers -> corner origin
        K = K.copy()
        K[0, 2] += 0.5
        K[1, 2] += 0.5
    fx, fy, sk, cx, cy = K[0, 0], K[1, 1], K[0, 1], K[0, 2], K[1, 2]
    if abs(fy - fx) > 1e-3 * fx:
        warn.append(f"fx {fx:.2f} != fy {fy:.2f}: Blender uses square pixels, fy set to fx")
    if abs(sk) > 1e-6 * fx:
        warn.append(f"skew {sk:.4g} dropped")
    Kr = np.array([[fx, 0, cx], [0, fx, cy], [0, 0, 1.0]])
    # re-orthonormalise R (numerical noise from an input P)
    U, _, Vt = np.linalg.svd(R)
    R = U @ Vt
    P = Kr @ np.c_[R, t]
    C = -R.T @ t
    info = dict(view="persp", K=Kr.tolist(), R=R.tolist(), t=t.tolist(), C=C.tolist(),
                fov_x_deg=math.degrees(2 * math.atan(0.5 * W / fx)), fov_y_deg=math.degrees(2 * math.atan(0.5 * H / fx)),
                warnings=warn, mirrored=False,
                image_axes=dict(right=R[0].tolist(), down=R[1].tolist(), look=R[2].tolist()))
    return P, W, H, info


# =============================================================================================
# 2. OpenEXR reader (scanline, single- or multi-part, NONE / ZIPS / ZIP) -- numpy only
# =============================================================================================

_LINES_PER_BLOCK = {0: 1, 2: 1, 3: 16}


def read_exr(path):
    """-> {channel name: (H, W) float32 array}.  Enough of OpenEXR for Blender's multilayer output."""
    b = Path(path).read_bytes()
    magic, ver = struct.unpack("<ii", b[:8])
    if magic != 20000630:
        raise ValueError(f"{path}: not an OpenEXR file")
    if ver & 0x200:
        raise ValueError("tiled EXR not supported")
    multipart = bool(ver & 0x1000)
    i = 8

    def cstr(i):
        j = b.index(b"\0", i)
        return b[i:j].decode("latin-1"), j + 1

    headers = []
    while True:
        h = {}
        while True:
            name, i = cstr(i)
            if not name:
                break
            typ, i = cstr(i)
            (size,) = struct.unpack("<i", b[i:i + 4])
            i += 4
            h[name] = (typ, b[i:i + size])
            i += size
        headers.append(h)
        if not multipart or b[i] == 0:
            if multipart:
                i += 1
            break
    parts = []
    for h in headers:
        chl = h["channels"][1]
        chans, p = [], 0
        while chl[p] != 0:
            q = chl.index(b"\0", p)
            nm = chl[p:q].decode("latin-1")
            (pt,) = struct.unpack("<i", chl[q + 1:q + 5])
            chans.append((nm, pt))
            p = q + 1 + 16
        x0, y0, x1, y1 = struct.unpack("<iiii", h["dataWindow"][1])
        comp = h["compression"][1][0]
        if comp not in _LINES_PER_BLOCK:
            raise ValueError(f"EXR compression {comp} not supported (use NONE/ZIP/ZIPS)")
        W, H = x1 - x0 + 1, y1 - y0 + 1
        lpb = _LINES_PER_BLOCK[comp]
        n_chunks = struct.unpack("<i", h["chunkCount"][1])[0] if "chunkCount" in h else -(-H // lpb)
        parts.append(dict(chans=chans, W=W, H=H, y0=y0, comp=comp, lpb=lpb, n=n_chunks))
    offsets = []
    for pp in parts:
        offsets.append(np.frombuffer(b, "<u8", pp["n"], i))
        i += 8 * pp["n"]
    out = {}
    sizes = {0: 4, 1: 2, 2: 4}
    dts = {0: "<u4", 1: "<f2", 2: "<f4"}
    b8 = np.frombuffer(b, np.uint8)
    pre = 4 if multipart else 0
    for pi, pp in enumerate(parts):
        W, H = pp["W"], pp["H"]
        arrs = {nm: np.empty((H, W), np.float32) for nm, _ in pp["chans"]}
        line_bytes = sum(sizes[pt] for _, pt in pp["chans"]) * W
        offs = offsets[pi].astype(np.int64)
        step = line_bytes + 8 + pre
        if pp["comp"] == 0 and len(offs) == H and np.all(np.diff(offs) == step):
            # uncompressed, one line per chunk, chunks back to back: one strided view for the part
            ys = np.lib.stride_tricks.as_strided(b8[offs[0] + pre:], shape=(H, 4), strides=(step, 1))
            ys = np.ascontiguousarray(ys).view("<i4").ravel() - pp["y0"]
            blk = np.lib.stride_tricks.as_strided(b8[offs[0] + pre + 8:], shape=(H, line_bytes), strides=(step, 1))
            p = 0
            for nm, pt in pp["chans"]:
                n = sizes[pt] * W
                arrs[nm][ys] = np.ascontiguousarray(blk[:, p:p + n]).view(dts[pt])
                p += n
            out.update(arrs)
            continue
        for off in offs:
            o = int(off) + pre
            y, size = struct.unpack("<ii", b[o:o + 8])
            data = b[o + 8:o + 8 + size]
            nl = min(pp["lpb"], pp["y0"] + H - y)
            if pp["comp"] in (2, 3) and size < line_bytes * nl:
                raw = np.frombuffer(zlib.decompress(data), np.uint8)
                t = ((np.cumsum(raw.astype(np.int64) - 128) + 128) & 0xFF).astype(np.uint8)   # undo predictor
                hlf = (t.size + 1) // 2
                d = np.empty_like(t)
                d[0::2], d[1::2] = t[:hlf], t[hlf:]  # ... and the byte de-interleave
                data = d.tobytes()
            p = 0
            for ln in range(nl):
                r = y - pp["y0"] + ln
                for nm, pt in pp["chans"]:
                    n = sizes[pt] * W
                    arrs[nm][r] = np.frombuffer(data, dts[pt], W, p)
                    p += n
        out.update(arrs)
    return out


def _passes(exr):
    """Blender multilayer EXR channels -> dict of named arrays."""
    def find(*suffixes):
        for s in suffixes:
            for k in exr:
                if k.endswith(s):
                    return exr[k]
        return None
    out = {}
    rgba = [find(".Combined." + c) for c in "RGBA"]
    if rgba[0] is not None:
        out["combined"] = np.stack(rgba, -1)
    z = find(".Depth.Z", ".Z")
    if z is not None:
        out["depth"] = z
    n = [find(".Normal." + c) for c in "XYZ"]
    if n[0] is not None:
        out["normal"] = np.stack(n, -1)
    oi = find(".Object Index.X", ".IndexOB.X")
    if oi is not None:
        out["oid"] = np.rint(oi).astype(np.int32)
    mi = find(".Material Index.X", ".IndexMA.X")
    if mi is not None:
        out["mid"] = np.rint(mi).astype(np.int32)
    return out


# =============================================================================================
# 3. image post-processing (numpy)
# =============================================================================================

def srgb_encode(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _parse_color(c, default=(1.0, 1.0, 1.0)):
    if c is None:
        return default
    if isinstance(c, str):
        c = c.strip()
        if c.startswith("#"):
            return tuple(int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
        named = {"white": (1, 1, 1), "black": (0, 0, 0), "grey": (0.5, 0.5, 0.5), "gray": (0.5, 0.5, 0.5)}
        if c in named:
            return named[c]
        return tuple(float(t) for t in c.split(","))
    return tuple(float(t) for t in c)


def _downsample(a, k):
    if k == 1:
        return a.astype(np.float32)
    H, W = a.shape[0] // k, a.shape[1] // k
    return a.reshape(H, k, W, k, *a.shape[2:]).mean(axis=(1, 3), dtype=np.float32)


def _dilate(m, r):
    """Binary dilation with a disc of radius r pixels (numpy shifts)."""
    if r <= 0.01:
        return m
    ri = int(math.floor(r + 1e-6))
    out = m.copy()
    H, W = m.shape
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if (dy == 0 and dx == 0) or dx * dx + dy * dy > r * r + 1e-6:
                continue
            ys0, ys1 = max(0, -dy), H - max(0, dy)
            xs0, xs1 = max(0, -dx), W - max(0, dx)
            out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] |= m[ys0:ys1, xs0:xs1]
    return out


def _edges_axis(bg, cls, depth, nrm, pxw, cos_crease, dz_k):
    """Edge flags for neighbour pairs along axis 1 -> (silhouette, inner) boolean (H, W-1)."""
    bp, bq = bg[:, :-1], bg[:, 1:]
    sil = bp != bq
    both = ~(bp | bq)
    inner = both & (cls[:, :-1] != cls[:, 1:])
    if nrm is not None and cos_crease is not None:
        dot = np.einsum("ijk,ijk->ij", nrm[:, :-1], nrm[:, 1:])
        inner |= both & (dot < cos_crease)
    if depth is not None:
        z = np.where(bg, np.float32(np.nan), depth.astype(np.float32))
        d = z[:, 1:] - z[:, :-1]
        e = np.full_like(d, np.inf)
        np.fmin(np.abs(d[:, 1:] - d[:, :-1]), np.inf, out=e[:, 1:])          # vs. the left neighbour pair
        e[:, :-1] = np.fmin(e[:, :-1], np.abs(d[:, :-1] - d[:, 1:]))         # vs. the right neighbour pair
        with np.errstate(invalid="ignore"):
            ad = np.abs(d)
            e = np.where(np.isfinite(e), e, ad)
            thr = dz_k * (pxw if np.isscalar(pxw) else np.fmin(pxw[:, :-1], pxw[:, 1:]))
            inner |= both & (e > thr) & (ad > thr)
    return sil, inner


def auto_supersample(W, H):
    """Supersampling factor for the line passes: 3 up to 1.5 Mpx, 2 up to 6 Mpx, else 1."""
    n = W * H
    return 3 if n <= 1.5e6 else 2 if n <= 6.0e6 else 1


def _box_count(M, r):
    """Number of set pixels in the (2r+1)^2 window around each pixel (integral image)."""
    S = np.zeros((M.shape[0] + 2 * r + 1, M.shape[1] + 2 * r + 1), np.int32)
    S[1:, 1:] = np.pad(M, r).astype(np.int32).cumsum(0).cumsum(1)
    n = 2 * r + 1
    return S[n:, n:] - S[:-n, n:] - S[n:, :-n] + S[:-n, :-n]


def despeckle(M, k, min_len_px=2.5):
    """Drop isolated specks (e.g. crease flags from sliver triangles with bad normals) from a
    supersampled edge-mark mask: keep a pixel only if its 2k-radius window holds at least as many
    marks as a 2-pixel-wide segment of min_len_px output pixels."""
    r = max(2, 2 * k)
    return M & (_box_count(M, r) >= int(round(2 * min_len_px * k)))


def edge_ink(oid, cls, depth, nrm, k, pxw, line_px=1.0, sil_px=1.8, crease_deg=35.0, dz_k=4.0, min_len_px=2.5):
    """Supersampled pass arrays -> anti-aliased ink coverage (H/k, W/k) in [0, 1].
    oid: object/part index (0 = background); cls: material class; depth: view depth [m];
    nrm: world normals; pxw: world size of one supersampled pixel (scalar or per pixel)."""
    bg = oid <= 0
    cc = math.cos(math.radians(crease_deg)) if crease_deg else None
    s_h, i_h = _edges_axis(bg, cls, depth, nrm, pxw, cc, dz_k)
    T = (lambda a: None if a is None else (a.transpose(1, 0, 2) if a.ndim == 3 else a.T))
    s_v, i_v = _edges_axis(bg.T, cls.T, T(depth), T(nrm), pxw if np.isscalar(pxw) else pxw.T, cc, dz_k)
    S = np.zeros(bg.shape, bool)
    I = np.zeros(bg.shape, bool)
    for M, h, v in ((S, s_h, s_v), (I, i_h, i_v)):
        M[:, :-1] |= h
        M[:, 1:] |= h
        M[:-1, :] |= v.T
        M[1:, :] |= v.T
    if min_len_px:
        I = despeckle(I & ~S, k, min_len_px) | (I & S)
    ink_s = _downsample(_dilate(S, (sil_px * k - 1) / 2), k)
    ink_i = _downsample(_dilate(I, (line_px * k - 1) / 2), k)
    return np.maximum(ink_s, ink_i)


def save_png(path, arr):
    from PIL import Image
    a = np.asarray(arr)
    Image.fromarray(a).save(str(path), optimize=False, compress_level=4)


# =============================================================================================
# 4. Blender session (runs only inside /opt/venv-blender)
# =============================================================================================

@contextlib.contextmanager
def _quiet(enabled=True):
    """Silence C-level stdout/stderr (glTF importer / Cycles chatter)."""
    if not enabled:
        yield
        return
    sys.stdout.flush()
    sys.stderr.flush()
    saved = os.dup(1), os.dup(2)
    null = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(null, 1)
        os.dup2(null, 2)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved[0], 1)
        os.dup2(saved[1], 2)
        os.close(null)
        os.close(saved[0])
        os.close(saved[1])


GLASS_NAMES = ("glass", "glass_windshield")
PAINT_NAMES = ("paint_white", "paint_belly", "paint_accent", "paint_stripe")
GLASS_TINT = (0.075, 0.12, 0.17)          # linear; reads as a blue-grey against trim_black (0.018)
GLASS_FILL = np.array([0.80, 0.87, 0.93], np.float32)   # sRGB tint for glazing in line drawings (--fill glass)


def _match(chain, prefixes):
    return any(p and c.startswith(p) for c in chain for p in prefixes)


class Session:
    """One Blender scene with the GLB imported (world == model coordinates)."""

    def __init__(self, glb=None, quiet=True):
        import bpy
        from mathutils import Matrix
        self.bpy = bpy
        self.quiet = quiet
        self.glb = str(Path(glb or GLB).resolve())
        t = time.time()
        with _quiet(quiet):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=self.glb)
        self.t_import = time.time() - t
        Rz = Matrix.Rotation(math.pi / 2, 4, "Z")        # Blender (y, -x, z) -> model (x, y, z)
        for o in [o for o in bpy.data.objects if o.parent is None]:
            o.matrix_world = Rz @ o.matrix_world
        bpy.context.view_layer.update()
        sc = self.sc = bpy.context.scene

        def chain(o):
            c = []
            while o is not None:
                if "part" in o.keys():
                    c.append(str(o["part"]))
                o = o.parent
            return c
        self.meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        self.chain = {o.name: chain(o) for o in self.meshes}
        parts = sorted({c[0] for c in self.chain.values() if c})
        self.part_index = {p: i + 1 for i, p in enumerate(parts)}
        for o in self.meshes:
            c = self.chain[o.name]
            o.pass_index = self.part_index[c[0]] if c else len(parts) + 1
        mats = sorted(m.name for m in bpy.data.materials)
        self.mat_index = {m: i + 1 for i, m in enumerate(mats)}
        for m in bpy.data.materials:
            m.pass_index = self.mat_index[m.name]
        self.orig = {}
        for o in self.meshes:
            me = o.data
            if me.name not in self.orig:
                self.orig[me.name] = [m.name if m else None for m in me.materials]
        # world-space vertex boxes per mesh
        self.box = {}
        for o in self.meshes:
            n = len(o.data.vertices)
            co = np.empty(n * 3)
            o.data.vertices.foreach_get("co", co)
            M = np.array(o.matrix_world)
            w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
            self.box[o.name] = (w.min(0), w.max(0))
        self._variants = {}
        # render defaults
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.render.film_transparent = True
        sc.render.use_persistent_data = True
        sc.render.resolution_percentage = 100
        sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1.0
        sc.view_settings.view_transform = "Standard"
        vl = sc.view_layers[0]
        vl.use_pass_z = vl.use_pass_normal = True
        vl.use_pass_object_index = vl.use_pass_material_index = True
        vl.pass_alpha_threshold = 0.5
        ims = sc.render.image_settings
        try:
            ims.media_type = "MULTI_LAYER_IMAGE"
        except Exception:
            pass
        ims.file_format = "OPEN_EXR_MULTILAYER"
        ims.exr_codec = "NONE"
        ims.color_depth = "32"
        self.world = bpy.data.worlds.new("studio")
        sc.world = self.world
        self._lights = []
        cd = bpy.data.cameras.new("cam")
        self.cam = bpy.data.objects.new("cam", cd)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam

    # ------------------------------------------------------------------ materials
    def _principled(self, name, color, rough=0.6, metallic=0.0, alpha=1.0, pass_index=0, emission=None):
        bpy = self.bpy
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        nt = m.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        if bsdf is None:
            bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
            out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
            nt.links.new(bsdf.outputs[0], out.inputs[0])
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Alpha"].default_value = alpha
        if emission is not None:
            bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
            bsdf.inputs["Emission Strength"].default_value = 1.0
            bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
            bsdf.inputs["Roughness"].default_value = 1.0
            try:
                bsdf.inputs["Specular IOR Level"].default_value = 0.0
            except Exception:
                pass
        m.pass_index = pass_index
        m.diffuse_color = (*color, alpha)
        return m

    def _variant(self, kind, glass="tint"):
        """Material name -> Material for a style ('orig', 'clay', 'ids', 'white')."""
        key = (kind, glass)
        if key in self._variants:
            return self._variants[key]
        bpy = self.bpy
        vmap = {}
        for name, idx in self.mat_index.items():
            m = bpy.data.materials.get(name)
            is_glass = name in GLASS_NAMES
            if kind == "orig":
                if is_glass and glass == "tint":
                    vmap[name] = self._principled(name + ".tint", GLASS_TINT, rough=0.3, pass_index=idx)
                elif is_glass and glass == "dark":
                    vmap[name] = self._principled(name + ".dark", (0.02, 0.025, 0.03), rough=0.1, pass_index=idx)
                elif is_glass and glass == "clear":
                    vmap[name] = self._principled(name + ".clear", (0.2, 0.25, 0.3), rough=0.05, alpha=0.25,
                                                  pass_index=idx)
                else:
                    vmap[name] = m
            elif kind == "clay":
                if is_glass:
                    vmap[name] = self._principled(name + ".clay", (0.03, 0.035, 0.04), rough=0.15, pass_index=idx)
                else:
                    vmap[name] = self._principled(name + ".clay", (0.55, 0.55, 0.55), rough=0.9, pass_index=idx)
            elif kind == "ids":
                vmap[name] = self._principled(name + ".ids", (0.5, 0.5, 0.5), rough=1.0, pass_index=idx)
            elif kind == "white":
                vmap[name] = self._principled(name + ".white", (1, 1, 1), emission=(1, 1, 1), pass_index=idx)
        self._variants[key] = vmap
        return vmap

    def _apply_materials(self, kind, glass="tint"):
        vmap = self._variant(kind, glass)
        for me_name, names in self.orig.items():
            me = self.bpy.data.meshes[me_name]
            for i, n in enumerate(names):
                if n is not None:
                    me.materials[i] = vmap[n]

    # ------------------------------------------------------------------ scene state
    def set_visibility(self, only=None, hide=None):
        only = [p for p in (only or []) if p]
        hide = [p for p in (hide or []) if p]
        shown, hidden = set(), set()
        for o in self.meshes:
            c = self.chain[o.name]
            vis = (not only or _match(c, only)) and not _match(c, hide)
            o.hide_render = not vis
            (shown if vis else hidden).add(c[0] if c else o.name)
        return sorted(shown), sorted(hidden - shown)

    def visible_bbox(self):
        lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
        for o in self.meshes:
            if not o.hide_render:
                a, b = self.box[o.name]
                lo, hi = np.minimum(lo, a), np.maximum(hi, b)
        return np.stack([lo, hi], 1).ravel()           # x0, x1, y0, y1, z0, z1

    def _lighting(self, style, right, up, toward):
        bpy = self.bpy
        for lo in self._lights:
            bpy.data.objects.remove(lo, do_unlink=True)
        self._lights = []
        w = self.world
        try:
            w.use_nodes = True
        except Exception:
            pass
        bg = w.node_tree.nodes.get("Background")
        if bg is None:
            bg = w.node_tree.nodes.new("ShaderNodeBackground")
            wo = w.node_tree.nodes.get("World Output") or w.node_tree.nodes.new("ShaderNodeOutputWorld")
            w.node_tree.links.new(bg.outputs[0], wo.inputs[0])
        bg.inputs[0].default_value = (1, 1, 1, 1)
        if style == "white":
            bg.inputs[1].default_value = 0.0
            return
        amb, key, fill = {"clay": (0.55, 1.9, 0.45)}.get(style, (0.52, 1.7, 0.4))
        bg.inputs[1].default_value = amb
        from mathutils import Matrix, Vector
        r, u, tw = (np.asarray(v, float) for v in (right, up, toward))
        for nm, d, e in (("key", -0.45 * r + 0.6 * u + 0.66 * tw, key), ("fill", 0.55 * r - 0.25 * u + 0.8 * tw, fill)):
            d = d / np.linalg.norm(d)
            ld = bpy.data.lights.new(nm, "SUN")
            ld.energy = e
            ld.angle = math.radians(12)
            lo = bpy.data.objects.new(nm, ld)
            z = Vector(d.tolist())
            x = z.orthogonal().normalized()
            y = z.cross(x)
            M = Matrix((x, y, z)).transposed().to_4x4()
            lo.matrix_world = M
            self.sc.collection.objects.link(lo)
            self._lights.append(lo)

    def _camera(self, P, W, H, info, proj):
        from mathutils import Matrix
        cam, cd = self.cam, self.cam.data
        cd.sensor_fit = "HORIZONTAL"
        cd.sensor_width = 36.0
        if proj == "ortho":
            r, dn, lk = (np.asarray(info["image_axes"][k], float) for k in ("right", "down", "look"))
            up = -dn
            if info["mirrored"]:
                up = -up                                    # render the physical view, flip afterwards
            back = -lk
            dist = 60.0
            pos = np.asarray(info["centre"], float) + back * dist
            cd.type = "ORTHO"
            cd.ortho_scale = info["ortho_width_m"]
            cd.shift_x = cd.shift_y = 0.0
            cd.clip_start, cd.clip_end = 0.5, 2 * dist
            rot = np.stack([r, up, back], 1)
        else:
            K, R = np.asarray(info["K"]), np.asarray(info["R"])
            pos = np.asarray(info["C"])
            fx, cx, cy = K[0, 0], K[0, 2], K[1, 2]
            cd.type = "PERSP"
            cd.lens_unit = "MILLIMETERS"
            cd.lens = fx * cd.sensor_width / W
            cd.shift_x = (0.5 * W - cx) / W
            cd.shift_y = (cy - 0.5 * H) / W
            cd.clip_start, cd.clip_end = 0.05, 2000.0
            rot = np.stack([R[0], -R[1], -R[2]], 1)
            r, up, back = R[0], -R[1], -R[2]
        M = np.eye(4)
        M[:3, :3], M[:3, 3] = rot, pos
        cam.matrix_world = Matrix(M.tolist())
        self.bpy.context.view_layer.update()
        return r, up, back

    def _blender_check(self, P, W, H, mirrored, pts):
        """Project points with Blender's camera frame and compare with P (px)."""
        from bpy_extras.object_utils import world_to_camera_view
        from mathutils import Vector
        sc = self.sc
        sc.render.resolution_x, sc.render.resolution_y = W, H
        err = 0.0
        uvP = project(P, pts)
        for p, q in zip(pts, uvP):
            c = world_to_camera_view(sc, self.cam, Vector([float(v) for v in p]))
            u, v = c.x * W, (1.0 - c.y) * H
            if mirrored:
                v = H - v
            err = max(err, math.hypot(u - q[0], v - q[1]))
        return err

    def _render_exr(self, W, H, work):
        sc = self.sc
        sc.render.resolution_x, sc.render.resolution_y = W, H
        path = str(Path(work) / f"r_{time.time_ns()}.exr")
        sc.render.filepath = path
        t = time.time()
        with _quiet(self.quiet):
            self.bpy.ops.render.render(write_still=True)
        t_r = time.time() - t
        t = time.time()
        p = _passes(read_exr(path))
        os.remove(path)
        return p, t_r, time.time() - t

    # ------------------------------------------------------------------ one job
    def run(self, job):
        t0 = time.time()
        job = normalize_job(job)
        sc = self.sc
        style, vn = job["style"], job["view"]
        shown, hidden = self.set_visibility(job["only"], job["hide"])
        if vn == "persp":
            P, W, H, info = persp_setup(job["camera"], job.get("width"), job.get("height"))
            proj = "perspective"
        else:
            P, W, H, info = ortho_setup(vn, job.get("bounds"), job.get("px_per_m"), job.get("width"),
                                        job.get("height"), bbox=self.visible_bbox(), margin=job["margin"])
            proj = "ortho"
        mirrored = info["mirrored"]
        r, up, back = self._camera(P, W, H, info, "ortho" if proj == "ortho" else "persp")
        bb = self.visible_bbox().reshape(3, 2)
        corners = np.array([[bb[0, i], bb[1, j], bb[2, k]] for i in (0, 1) for j in (0, 1) for k in (0, 1)])
        chk = self._blender_check(P, W, H, mirrored, corners)
        out = Path(job["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="_work_", dir=str(OUT_DIR)))
        timings = {}
        bgc = job["bg"]
        transparent = bgc == "transparent"
        bgrgb = np.array(_parse_color(None if transparent else bgc), np.float32)
        np_lines = "lines" in style
        rgba = None            # final straight-alpha sRGB float image
        cover = None
        ids = None
        k_used = None
        try:
            if style in ("shaded", "clay", "shaded+lines", "clay+lines"):
                kind = "clay" if style.startswith("clay") else "orig"
                self._apply_materials(kind, job["glass"])
                self._lighting("clay" if kind == "clay" else "shaded", r, up, back)
                c = sc.cycles
                c.samples = int(job["samples"])
                c.use_adaptive_sampling = True
                c.adaptive_threshold = 0.02
                dn = job["denoise"]
                c.use_denoising = bool(dn) and str(dn).lower() not in ("0", "false", "off", "none")
                if c.use_denoising:                         # OIDN: 'high' = HIGH quality + ACCURATE prefilter
                    high = str(dn).lower() == "high"      # (~2x the render time here), default BALANCED + FAST
                    c.denoising_quality = "HIGH" if high else "BALANCED"
                    c.denoising_prefilter = "ACCURATE" if high else "FAST"
                c.pixel_filter_type = "BLACKMAN_HARRIS"
                c.filter_width = 1.5
                c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 3, 1, 1
                c.transmission_bounces, c.transparent_max_bounces = 1, 8
                c.caustics_reflective = c.caustics_refractive = False
                p, tr, tx = self._render_exr(W, H, work)
                timings["beauty_render"], timings["beauty_exr_read"] = round(tr, 2), round(tx, 2)
                C = p["combined"]
                if mirrored:
                    C = C[::-1]
                a = np.clip(C[..., 3], 0, 1)
                cover = a
                if transparent:
                    rgb = np.where(a[..., None] > 1e-4, C[..., :3] / np.maximum(a[..., None], 1e-4), 0)
                    rgba = np.dstack([srgb_encode(rgb), a])
                else:
                    lin = C[..., :3] + (1 - a[..., None]) * bgrgb
                    rgba = np.dstack([srgb_encode(lin), np.ones_like(a)])
            if style == "freestyle":
                self._freestyle_render(job, r, up, back)
                p, tr, tx = self._render_exr(W, H, work)
                sc.render.use_freestyle = False
                timings["freestyle_render"], timings["exr_read"] = round(tr, 2), round(tx, 2)
                C = p["combined"]
                if mirrored:
                    C = C[::-1]
                a = np.clip(C[..., 3], 0, 1)
                lum = np.clip(C[..., :3].mean(-1) + (1 - a), 0, 1)       # white objects, black lines
                ink = 1 - lum
                cover = a
                rgba = self._ink_image(ink, None, bgrgb, transparent, job)
            if np_lines or job["ids"]:
                k = (int(job["supersample"]) or auto_supersample(W, H)) if np_lines else 1
                k_used = k
                self._apply_materials("ids")
                self._lighting("white", r, up, back)
                c = sc.cycles
                c.samples = 1
                c.use_adaptive_sampling = False
                c.use_denoising = False
                c.pixel_filter_type = "BOX"
                c.filter_width = 0.01                       # sample exactly at the pixel centres
                c.max_bounces = c.diffuse_bounces = c.glossy_bounces = c.transmission_bounces = 0
                c.transparent_max_bounces = 0
                p, tr, tx = self._render_exr(W * k, H * k, work)
                timings["id_render"], timings["id_exr_read"] = round(tr, 2), round(tx, 2)
                t = time.time()
                oid, mid, dep, nrm = p["oid"], p["mid"], p["depth"], p["normal"]
                if mirrored:
                    oid, mid, dep, nrm = oid[::-1], mid[::-1], dep[::-1], nrm[::-1]
                if job["ids"]:
                    ids = oid[k // 2::k, k // 2::k].astype(np.uint16)
                if np_lines:
                    cls = self._material_classes(job["line_detail"])[np.clip(mid, 0, None)]
                    if proj == "ortho":
                        pxw = 1.0 / (info["px_per_m"] * k)
                    else:
                        pxw = np.where(oid > 0, dep, 0) / (np.asarray(info["K"])[0, 0] * k)
                    if job["line_detail"] == "outline":
                        cls = np.where(oid > 0, 1, 0)
                        nrm_use, cdeg = None, None
                    else:
                        nrm_use, cdeg = nrm, job["crease_deg"]
                    ink = edge_ink(oid, cls, dep, nrm_use, k, pxw, job["line_px"], job["sil_px"], cdeg or 0, job["depth_k"])
                    cov_l = _downsample((oid > 0), k)
                    if cover is None:
                        cover = cov_l
                    rgba = self._ink_image(ink, rgba, bgrgb, transparent, job,
                                           glass=(np.isin(mid, [self.mat_index[g] for g in GLASS_NAMES if g in self.mat_index]), k))
                timings["edges"] = round(time.time() - t, 2)
            # ------------------------------------------------------------ write
            img = np.clip(np.rint(rgba * 255), 0, 255).astype(np.uint8)
            if not transparent:
                img = img[..., :3]
            save_png(out, img)
            extra = {}
            if job["mask"] and cover is not None:
                mp = out.with_suffix(".mask.png")
                save_png(mp, np.clip(np.rint(cover * 255), 0, 255).astype(np.uint8))
                extra["mask"] = mp.name
            if ids is not None:
                ip = out.with_suffix(".ids.png")
                from PIL import Image
                Image.fromarray(ids.astype(np.uint16)).save(str(ip))
                extra["ids"] = ip.name
        finally:
            shutil.rmtree(work, ignore_errors=True)
        timings["total"] = round(time.time() - t0, 2)
        cd = self.cam.data
        camrec = dict(type=cd.type, location=list(self.cam.matrix_world.translation),
                      rotation_matrix=[list(rw)[:3] for rw in self.cam.matrix_world.to_3x3()],
                      sensor_fit=cd.sensor_fit, sensor_width=cd.sensor_width, shift_x=cd.shift_x, shift_y=cd.shift_y,
                      clip=[cd.clip_start, cd.clip_end])
        if cd.type == "ORTHO":
            camrec["ortho_scale"] = cd.ortho_scale
            camrec["note"] = "Blender camera frame; the image rows are flipped afterwards" if mirrored else ""
        else:
            camrec.update(lens_mm=cd.lens, K=info["K"], R=info["R"], t=info["t"], C=info["C"],
                          convention="OpenCV: X_cam = R X + t, x right, y down, z forward; K for corner-origin pixels")
        side = dict(
            image=out.name, width=W, height=H, view=vn, projection=proj, style=style,
            P=np.asarray(P).tolist(),
            mapping="[u*w, v*w, w] = P @ [x, y, z, 1] in MODEL coords (x aft of datum, y starboard, z up, m); "
                    "u right, v down, origin at the top-left pixel corner (pixel centres at +0.5)",
            image_axes=info["image_axes"], mirrored=mirrored,
            **({k: info[k] for k in ("bounds", "bounds_list", "px_per_m", "axes", "centre")} if proj == "ortho" else
               {k: info[k] for k in ("fov_x_deg", "fov_y_deg", "warnings")}),
            camera=camrec, blender_check_px=round(chk, 6),
            glb=os.path.relpath(self.glb, ROOT), glb_mtime=os.path.getmtime(self.glb),
            parts_shown=shown, parts_hidden=hidden, only=job["only"], hide=job["hide"],
            settings={k: job[k] for k in ("samples", "denoise", "glass", "bg", "supersample", "line_px", "sil_px",
                                          "crease_deg", "depth_k", "line_detail", "fill")},
            supersample_used=k_used,
            blender=self.bpy.app.version_string, timings=timings, **extra)
        if ids is not None:
            side["part_index"] = {str(v): k for k, v in self.part_index.items()}
        sp = out.with_suffix(".json")
        sp.write_text(json.dumps(side, indent=1))
        return dict(png=str(out), sidecar=str(sp), seconds=timings["total"], width=W, height=H,
                    blender_check_px=chk, timings=timings, **{k: str(out.parent / v) for k, v in extra.items()})

    def _material_classes(self, detail):
        n = max(self.mat_index.values()) + 2
        cls = np.arange(n)
        if detail != "full":
            paint = [self.mat_index[m] for m in PAINT_NAMES if m in self.mat_index]
            if paint:
                cls[paint] = paint[0]
        return cls

    def _ink_image(self, ink, rgba, bgrgb, transparent, job, glass=None):
        """Lay the ink (line coverage) over rgba (straight-alpha sRGB) or over the background."""
        lc = np.array(_parse_color(job["line_color"], (0, 0, 0)), np.float32)
        H, W = ink.shape
        if rgba is None:
            # premultiplied layers: background, optional glass tint, lines
            a = np.full((H, W), 0.0 if transparent else 1.0, np.float32)
            prem = np.zeros((H, W, 3), np.float32) + (0.0 if transparent else srgb_encode(bgrgb).astype(np.float32))
            if job["fill"] == "glass" and glass is not None:
                g = _downsample(glass[0], glass[1])[..., None]
                prem = GLASS_FILL * g + prem * (1 - g)
                a = g[..., 0] + a * (1 - g[..., 0])
        else:
            a = rgba[..., 3].astype(np.float32)
            prem = rgba[..., :3] * a[..., None]
        i = ink[..., None]
        prem = lc * i + prem * (1 - i)
        a = ink + a * (1 - ink)
        rgb = np.where(a[..., None] > 1e-6, prem / np.maximum(a[..., None], 1e-6), 0)
        return np.dstack([rgb, a])

    def _freestyle_render(self, job, r, up, back):
        bpy, sc = self.bpy, self.sc
        self._apply_materials("white")
        self._lighting("white", r, up, back)
        c = sc.cycles
        c.samples = 4
        c.use_denoising = False
        c.use_adaptive_sampling = False
        c.pixel_filter_type = "BLACKMAN_HARRIS"
        c.filter_width = 1.5
        c.max_bounces = 0
        sc.render.use_freestyle = True
        sc.render.line_thickness_mode = "ABSOLUTE"
        sc.render.line_thickness = float(job["line_px"])
        fs = sc.view_layers[0].freestyle_settings
        fs.crease_angle = math.radians(180 - float(job["crease_deg"]))
        if not fs.linesets:
            fs.linesets.new("lines")
        ls = fs.linesets[0]
        if ls.linestyle is None:
            ls.linestyle = bpy.data.linestyles.new("lines")
        ls.linestyle.color = _parse_color(job["line_color"], (0, 0, 0))
        ls.linestyle.thickness = float(job["line_px"])
        ls.select_by_visibility = True
        ls.visibility = "VISIBLE"
        ls.select_silhouette = ls.select_border = ls.select_crease = True
        ls.select_material_boundary = job["line_detail"] != "outline"


# =============================================================================================
# 5. jobs, API and CLI
# =============================================================================================

JOB_DEFAULTS = dict(view="side_port", style="shaded", bounds=None, px_per_m=None, width=None, height=None,
                    margin=0.25, camera=None, only=None, hide=None, bg="white", samples=8, denoise="fast",
                    glass="tint", supersample=0, line_px=1.0, sil_px=1.8, crease_deg=35.0, depth_k=4.0,
                    line_detail="normal", line_color="black", fill="none", mask=False, ids=False, out=None,
                    name=None)


def _split(v):
    if v is None:
        return None
    if isinstance(v, str):
        return [t.strip() for t in v.split(",") if t.strip()]
    return [str(t) for t in v]


def normalize_job(job):
    j = dict(JOB_DEFAULTS)
    j.update({k: v for k, v in dict(job).items() if v is not None or k in ("bounds",)})
    j["view"] = view_name(j["view"])
    if j["view"] != "persp" and j["view"] not in VIEWS:
        raise ValueError(f"unknown view {j['view']!r}; use one of {sorted(VIEWS)} or 'persp'")
    if j["style"] not in STYLES:
        raise ValueError(f"unknown style {j['style']!r}; use one of {STYLES}")
    if j["view"] == "persp" and not j.get("camera"):
        raise ValueError("view 'persp' needs a camera dict")
    if isinstance(j.get("bounds"), str):
        j["bounds"] = [float(t) for t in j["bounds"].split(",")]
    if j.get("bounds") is not None and len(j["bounds"]) != 4:
        raise ValueError("bounds must be 4 numbers (a0, a1, b0, b1) in the view's natural axes")
    j["only"] = _split(j["only"]) or []
    hide = _split(job.get("hide")) if "hide" in job and job.get("hide") is not None else None
    j["hide"] = hide if hide is not None else ([] if j["only"] else list(DEFAULT_HIDE))
    if j.get("camera") and ("width" in j["camera"] or "height" in j["camera"]):
        j["width"] = j["width"] or j["camera"].get("width")
        j["height"] = j["height"] or j["camera"].get("height")
    if not j.get("out"):
        nm = j.get("name") or j["view"]
        j["out"] = str(OUT_DIR / f"{nm}_{j['style'].replace('+', '_')}.png")
    j["out"] = str(Path(j["out"]) if Path(j["out"]).is_absolute() else (Path.cwd() / j["out"]))
    return j


def _have_bpy():
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def render_many(jobs, glb=None, quiet=True, timeout=3600):
    """Render a list of job dicts in one Blender session -> list of result dicts.
    From a python without bpy, re-runs this file in the Blender venv."""
    jobs = [normalize_job(j) for j in jobs]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if _have_bpy():
        s = Session(glb, quiet=quiet)
        res = []
        for j in jobs:
            r = s.run(j)
            r["import_seconds"] = round(s.t_import, 2)
            res.append(r)
        return res
    with tempfile.NamedTemporaryFile("w", suffix=".json", dir=str(OUT_DIR), delete=False) as f:
        json.dump(jobs, f)
        jf = f.name
    try:
        cmd = [BLENDER_PY, str(Path(__file__).resolve()), "--jobs", jf, "--result-line"]
        if glb:
            cmd += ["--glb", str(glb)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(Path.cwd()))
    finally:
        os.remove(jf)
    line = [ln for ln in p.stdout.splitlines() if ln.startswith(RESULT_TAG)]
    if p.returncode != 0 or not line:
        raise RuntimeError(f"blender render failed (rc {p.returncode}):\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    return json.loads(line[-1][len(RESULT_TAG):])


def render(glb=None, **job):
    """Render one view (keyword arguments = job keys, see JOB_DEFAULTS / module doc)."""
    return render_many([job], glb=glb)[0]


def _size(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="render/blender_ortho.py", description=__doc__.strip().split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--view", default="side_port", help="comma list: " + ", ".join(VIEWS) + ", persp")
    ap.add_argument("--style", default="shaded", help="comma list: " + ", ".join(STYLES))
    ap.add_argument("--bounds", help="a0,a1,b0,b1 in the view's natural axes (side x,z; top x,y; front y,z)")
    ap.add_argument("--px-per-m", type=float)
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--size", help="WxH (perspective)")
    ap.add_argument("--margin", type=float, default=0.25, help="margin around the default full-aircraft bounds [m]")
    ap.add_argument("--cam-pos")
    ap.add_argument("--target")
    ap.add_argument("--up", default="0,0,1")
    ap.add_argument("--fov", type=float, help="vertical field of view [deg]")
    ap.add_argument("--hfov", type=float, help="horizontal field of view [deg]")
    ap.add_argument("--camera-json", help="JSON file: P | K,R,t | fx,fy,cx,cy,R,t | position,target,up,fov")
    ap.add_argument("--only", help="part-id prefixes to show")
    ap.add_argument("--hide", help="part-id prefixes to hide (default 'structure'; '' shows everything)")
    ap.add_argument("--bg", default="white", help="white | transparent | #rrggbb")
    ap.add_argument("--samples", type=int, default=8, help="Cycles samples for shaded/clay (OIDN denoised)")
    ap.add_argument("--denoise", default="fast", choices=("fast", "high", "off"),
                    help="OIDN denoiser: fast (BALANCED quality, FAST prefilter; default), high, off")
    ap.add_argument("--glass", default="tint", choices=("tint", "original", "clear", "dark"))
    ap.add_argument("--supersample", type=int, default=0,
                    help="line styles: supersampling factor (0 = auto: 3 up to 1.5 Mpx, 2 up to 6 Mpx, else 1)")
    ap.add_argument("--line-px", type=float, default=1.0)
    ap.add_argument("--sil-px", type=float, default=1.8)
    ap.add_argument("--crease-deg", type=float, default=35.0)
    ap.add_argument("--line-detail", default="normal", choices=("outline", "normal", "full"))
    ap.add_argument("--line-color", default="black")
    ap.add_argument("--fill", default="none", choices=("none", "glass"), help="lines: light tint on glazing")
    ap.add_argument("--mask", action="store_true", help="also write <name>.mask.png (coverage)")
    ap.add_argument("--ids", action="store_true", help="also write <name>.ids.png (16-bit part index)")
    ap.add_argument("--out", help="output PNG (single job)")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    ap.add_argument("--name", help="output basename prefix (default <view>_<style>)")
    ap.add_argument("--glb", default=str(GLB))
    ap.add_argument("--jobs", help="JSON file with a list of job dicts")
    ap.add_argument("--verbose", action="store_true", help="show Blender/Cycles output")
    ap.add_argument("--result-line", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.jobs:
        jobs = json.loads(Path(a.jobs).read_text())
    else:
        camera = None
        if a.camera_json:
            camera = json.loads(Path(a.camera_json).read_text())
        elif a.cam_pos:
            camera = dict(position=a.cam_pos, target=a.target or "7,0,1.5", up=a.up, fov=a.fov, hfov=a.hfov)
        if camera is not None and a.fov is not None and "fov" not in camera:
            camera["fov"] = a.fov
        w, h = (a.width, a.height)
        if a.size:
            w, h = _size(a.size)
        jobs = []
        views, styles = _split(a.view), _split(a.style)
        for v in views:
            for st in styles:
                nm = (f"{a.name}_{view_name(v)}" if len(views) > 1 else a.name) if a.name else view_name(v)
                out = a.out if (a.out and len(views) * len(styles) == 1) else \
                    str(Path(a.out_dir) / f"{nm}_{st.replace('+', '_')}.png")
                jobs.append(dict(view=v, style=st, bounds=a.bounds, px_per_m=a.px_per_m, width=w, height=h,
                                 margin=a.margin, camera=camera, only=a.only, hide=a.hide, bg=a.bg,
                                 samples=a.samples, denoise=a.denoise, glass=a.glass,
                                 supersample=a.supersample, line_px=a.line_px, sil_px=a.sil_px,
                                 crease_deg=a.crease_deg, line_detail=a.line_detail, line_color=a.line_color,
                                 fill=a.fill, mask=a.mask, ids=a.ids, out=out))
    res = render_many(jobs, glb=a.glb, quiet=not a.verbose)
    if a.result_line:
        print(RESULT_TAG + json.dumps(res))
    else:
        for r in res:
            print(f"{r['png']}  {r['width']}x{r['height']}  {r['seconds']:.1f} s  "
                  f"(P vs blender camera {r['blender_check_px']:.2e} px)  sidecar {Path(r['sidecar']).name}")
    return res


if __name__ == "__main__":
    main()
