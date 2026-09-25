"""
render.check_mapping -- numerical check of the sidecar pixel mapping of render/blender_ortho.py.

Known model points are taken straight from out/pc12.glb (own reader, independent of Blender's
importer): spinner tip, aft-most point, fin/bullet top, winglet tips, main/nose wheel contact
points, and the windshield centre post (inner edges of the two panes).  Each point is projected
with the sidecar P and compared with the rendered coverage mask (<name>.mask.png) / part-index
map (<name>.ids.png):
  * extreme points (e.g. the spinner tip is the minimum-x vertex): the sub-pixel 0.5 crossing of the
    mask along the image direction of that extreme, searched on the pixel rows/columns within
    +-6 px, must coincide with the projected vertex -> delta [px] (inward = negative);
  * interior points: the part id under the projected pixel;
  * centre post: the post -> glazing_flightdeck id transitions next to the projected inner edges of
    the glazing part (glass + seal mesh) -> delta [px];
  * any projection (incl. perspective): min/max u and v of all projected vertices of the shown parts
    vs. the extreme 0.5 crossings of the mask.

usage (system python3, from pc12/):
    python3 -m render.check_mapping out/tmp/render/side_port_full_shaded.json [...]   # sidecars
    python3 -m render.check_mapping --render        # renders the standard test set first (Blender)
Needs renders made with mask=True and ids=True.  Prints a table and returns non-zero if any
|delta| > --tol px (default 1.5).
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


# ---------------------------------------------------------------------------------------- GLB
def read_glb(path=None):
    """out/pc12.glb -> {part id: (N,3) vertex array in MODEL coordinates} (node transforms applied;
    a mesh belongs to its nearest ancestor node with extras.part)."""
    data = Path(path or ROOT / "out" / "pc12.glb").read_bytes()
    n = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + n])
    binb = data[20 + n + 8:]
    ctype = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

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

    parts = {}

    def walk(i, M, part):
        nd = js["nodes"][i]
        M = M @ local(nd)
        part = (nd.get("extras") or {}).get("part", part)
        if "mesh" in nd:
            for prim in js["meshes"][nd["mesh"]]["primitives"]:
                V = acc(prim["attributes"]["POSITION"])
                Vw = V @ M[:3, :3].T + M[:3, 3]
                parts.setdefault(part, []).append(np.stack([Vw[:, 2], Vw[:, 0], Vw[:, 1]], -1))   # gl -> model
        for c in nd.get("children", []):
            walk(c, M, part)

    for r in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4), None)
    return {k: np.concatenate(v) for k, v in parts.items()}


def reference_points(parts, hide=("structure",)):
    """Named model points with the direction in which each is an extreme vertex."""
    def cat(prefixes, exclude=()):
        arr = [v for k, v in parts.items() if k and any(k.startswith(p) for p in prefixes)
               and not any(k.startswith(h) for h in exclude)]
        return np.concatenate(arr)
    allv = cat([""], hide)
    pts = {}

    def ext(name, V, axis, sign):
        i = np.argmax(sign * V[:, axis])
        e = np.zeros(3)
        e[axis] = sign
        pts[name] = dict(p=V[i], dir=e)
    ext("spinner tip (min x)", cat(["propeller"]), 0, -1)
    ext("aft-most point (max x)", allv, 0, +1)
    ext("fin/bullet top (max z)", allv, 2, +1)
    ext("winglet tip R (max y)", cat(["winglet_R"]), 1, +1)
    ext("winglet tip L (min y)", cat(["winglet_L"]), 1, -1)
    ext("main wheel R contact (min z)", cat(["gear_main_R"]), 2, -1)
    ext("main wheel L contact (min z)", cat(["gear_main_L"]), 2, -1)
    ext("nose wheel contact (min z)", cat(["gear_nose"]), 2, -1)
    G = cat(["glazing_flightdeck"])
    ws = G[(G[:, 0] < 3.9) & (np.abs(G[:, 1]) < 0.7)]
    # glazing outline extremes (checked against the glazing region of the part-index map)
    gl = {}

    def gext(name, V, axis, sign):
        i = np.argmax(sign * V[:, axis])
        e = np.zeros(3)
        e[axis] = sign
        gl[name] = dict(p=V[i], dir=e)
    gext("glazing front-most (min x)", G, 0, -1)
    gext("windshield top (max z)", G[np.abs(G[:, 1]) < 0.7], 2, +1)
    for side, lab in ((-1, "port"), (+1, "stbd")):
        sw = G[side * G[:, 1] > 0.3]
        gext(f"side window rear edge {lab} (max x)", sw, 0, +1)
        gext(f"side window bottom {lab} (min z)", sw, 2, -1)
        gext(f"side window outboard {lab} ({'min' if side < 0 else 'max'} y)", sw, 1, side)
    return pts, ws, gl


# ---------------------------------------------------------------------------------------- checks
def _load(sidecar):
    sp = Path(sidecar)
    sc = json.loads(sp.read_text())
    mask = ids = None
    if sc.get("mask"):
        mask = np.asarray(Image.open(sp.parent / sc["mask"]), float) / 255.0
    if sc.get("ids"):
        ids = np.asarray(Image.open(sp.parent / sc["ids"])).astype(np.int32)
    return sc, mask, ids


def project(sc, X):
    P = np.asarray(sc["P"], float)
    h = np.atleast_2d(X) @ P[:, :3].T + P[:, 3]
    return h[:, :2] / h[:, 2:3]


def edge_delta(mask, uv, d_img, search=12, across=6):
    """Sub-pixel 0.5 crossing of the mask beyond uv along the image direction d_img (unit, axis
    aligned), maximised over the pixel lines within +-across; -> signed distance [px] from uv."""
    H, W = mask.shape
    ax = 0 if abs(d_img[0]) > 0.5 else 1               # 0: along u (rows), 1: along v (columns)
    sgn = np.sign(d_img[ax])
    u, v = uv
    best = None
    c0 = int(np.floor(v if ax == 0 else u))
    s0 = int(np.floor(u if ax == 0 else v))
    for o in range(-across, across + 1):
        line = c0 + o
        if not (0 <= line < (H if ax == 0 else W)):
            continue
        prof = mask[line, :] if ax == 0 else mask[:, line]
        js = np.arange(max(0, s0 - search), min(len(prof), s0 + search + 1))
        if sgn < 0:
            js = js[::-1]
        c = prof[js]
        pos = js + 0.5
        # walk outward along sgn: last index with c >= 0.5 followed by c < 0.5
        inside = np.nonzero(c >= 0.5)[0]
        if not len(inside):
            continue
        i = inside[-1]
        if i + 1 >= len(c):
            continue
        t = (c[i] - 0.5) / (c[i] - c[i + 1]) if c[i] != c[i + 1] else 0.0
        x = pos[i] + sgn * t
        dist = (x - (u if ax == 0 else v)) * sgn
        best = dist if best is None else max(best, dist)
    return best


def _first_crossing(c):
    """Rows of coverage c (n, m): sub-pixel position of the first 0.5 crossing from the left
    (pixel centres at j + 0.5); nan where a row never reaches 0.5."""
    inside = c >= 0.5
    has = inside.any(1)
    j = np.argmax(inside, 1)
    prev = np.where(j > 0, c[np.arange(len(c)), np.maximum(j - 1, 0)], 0.0)
    cur = c[np.arange(len(c)), j]
    t = np.where(cur != prev, (cur - 0.5) / np.maximum(cur - prev, 1e-9), 0.0)
    x = j + 0.5 - np.clip(t, 0, 1)
    return np.where(has, x, np.nan)


def extent_check(sc, mask, parts):
    """Projected-vertex extremes of all shown parts (min/max u, min/max v) vs. the mask's extreme
    0.5 crossings.  Valid for any projection: a projected triangle mesh's extremes are at vertices."""
    shown = sc.get("parts_shown") or []
    V = [v for k, v in parts.items() if k in shown]
    if not V:
        return []
    V = np.concatenate(V)
    P = np.asarray(sc["P"], float)
    h = V @ P[:, :3].T + P[:, 3]
    V = h[h[:, 2] > 1e-6]
    uv = V[:, :2] / V[:, 2:3]
    H, W = mask.shape
    rows = []
    specs = (("min u", uv[:, 0].min(), lambda m: _first_crossing(m), +1),
             ("max u", uv[:, 0].max(), lambda m: W - _first_crossing(m[:, ::-1]), -1),
             ("min v", uv[:, 1].min(), lambda m: _first_crossing(m.T), +1),
             ("max v", uv[:, 1].max(), lambda m: H - _first_crossing(m.T[:, ::-1]), -1))
    for name, val, fn, inward in specs:
        lim = W if name.endswith("u") else H
        if not (2 <= val <= lim - 2):
            continue                                   # extreme outside the image (crop)
        x = fn(mask)
        mx = np.nanmin(x) if inward > 0 else np.nanmax(x)
        rows.append((f"projected mesh extent {name}", "mask extent", None, (mx - val) * inward))
    return rows


def image_dir(sc, e):
    """Model direction -> unit image direction (u, v) for orthographic sidecars."""
    P = np.asarray(sc["P"], float)
    d = P[:2, :3] @ e
    n = np.linalg.norm(d)
    return d / n if n > 1e-9 else None


def check_sidecar(sidecar, pts, ws, gl=None, tol=1.5, parts=None):
    sc, mask, ids = _load(sidecar)
    rows = []
    if mask is None:
        return [(Path(sidecar).name, "no mask (render with mask=True)", None, None)]
    if parts is not None:
        rows += extent_check(sc, mask, parts)
    if sc.get("projection") != "ortho":
        return rows
    pidx = {int(k): v for k, v in (sc.get("part_index") or {}).items()}
    H, W = mask.shape
    for name, rec in pts.items():
        uv = project(sc, rec["p"])[0]
        if not (0 <= uv[0] < W and 0 <= uv[1] < H):
            continue
        d = image_dir(sc, rec["dir"])
        if d is not None and np.max(np.abs(d)) > 0.99:
            delta = edge_delta(mask, uv, d)
            rows.append((name, "silhouette", uv, delta))
        elif ids is not None:
            part = pidx.get(int(ids[int(uv[1]), int(uv[0])]), "background")
            rows.append((name, f"interior: id under point = {part}", uv, None))
    gid = [int(k) for k, v in pidx.items() if v == "glazing_flightdeck"]
    if ids is not None and gl:
        g = np.isin(ids, gid).astype(float)
        for name, rec in gl.items():
            if (" port " in name and sc["view"] == "side_stbd") or (" stbd " in name and sc["view"] == "side_port"):
                continue                               # far-side window seen through / behind the near one
            uv = project(sc, rec["p"])[0]
            if not (2 <= uv[0] < W - 2 and 2 <= uv[1] < H - 2):
                continue
            d = image_dir(sc, rec["dir"])
            if d is None or np.max(np.abs(d)) < 0.99:
                continue
            ins = uv - 1.5 * d                         # just inside the pane: must be visible glazing
            if not g[int(ins[1]), int(ins[0])]:
                rows.append((name, "glazing edge hidden in this view", uv, None))
                continue
            rows.append((name, "glazing_flightdeck part edge (ids)", uv, edge_delta(g, uv, d, search=8, across=3)))
    # windshield centre post (views that see the panes from above / ahead)
    look = np.asarray(sc["image_axes"].get("look", [0, 0, 0]), float)
    if ids is not None and sc.get("projection") == "ortho" and (look[2] < -0.9 or look[0] > 0.9):   # top / front
        if look[2] < -0.9:                             # top: inner pane edges at the station of the pane middle
            xm = 3.40
            sel = ws[np.abs(ws[:, 0] - xm) < 0.02]
            probe = lambda y: np.array([xm, y, 0.0])
        else:                                          # front: at the WL of the pane middle
            zm = float(np.median(ws[:, 2]))
            sel = ws[np.abs(ws[:, 2] - zm) < 0.01]
            probe = lambda y: np.array([0.0, y, zm])
        for side in (+1, -1):
            s = sel[np.sign(sel[:, 1]) == side]
            if not len(s):
                continue
            y_in = side * np.min(np.abs(s[:, 1]))
            uv = project(sc, probe(y_in))[0]
            uc = project(sc, probe(0.0))[0]
            front = pidx.get(int(ids[int(uc[1]), int(uc[0])]), "background")
            if front.startswith(("propeller", "blade")):
                rows.append((f"centre post / glazing edge {'R' if side > 0 else 'L'}", f"post hidden by {front}", uv, None))
                continue
            dy = image_dir(sc, np.array([0.0, side, 0.0]))          # image direction toward the pane
            ax = 0 if abs(dy[0]) > 0.5 else 1
            line = int(np.floor(uv[1] if ax == 0 else uv[0]))
            prof = (ids[line, :] if ax == 0 else ids[:, line])
            g = np.isin(prof, gid)
            s0 = uv[ax]
            # first glazing pixel centre moving from the post toward the pane
            js = np.arange(int(s0) - 15, int(s0) + 16)
            js = js[(js >= 0) & (js < len(prof))]
            sgn = np.sign(dy[ax])
            order = js if sgn > 0 else js[::-1]
            trans = None
            for a, b in zip(order[:-1], order[1:]):
                if not g[a] and g[b]:
                    trans = 0.5 * (a + b) + 0.5                  # boundary between the two pixel centres
            delta = None if trans is None else (trans - s0) * sgn
            rows.append((f"centre post / glazing edge {'R' if side > 0 else 'L'} (y={y_in:+.3f})",
                         "post -> glazing_flightdeck id transition", uv, delta))
    return rows


STANDARD = [
    dict(view="side_port", name="side_port_full"),
    dict(view="top", name="top_full"),
    dict(view="front", name="front_full"),
    dict(view="side_port", name="side_port_cockpit", bounds=[2.6, 4.8, 1.5, 2.8]),
    dict(view="top", name="top_cockpit", bounds=[2.6, 4.8, -1.0, 1.0]),
    dict(view="front", name="front_cockpit", bounds=[-1.1, 1.1, 1.3, 2.8], hide="structure,propeller"),
]


def standard_jobs(styles=("shaded", "lines"), width=2000):
    out = []
    for st in styles:
        for j in STANDARD:
            out.append(dict(j, style=st, width=width, mask=True, ids=True))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m render.check_mapping", description=__doc__.strip().split("\n")[0])
    ap.add_argument("sidecars", nargs="*")
    ap.add_argument("--render", action="store_true", help="render the standard test set first")
    ap.add_argument("--styles", default="shaded,lines")
    ap.add_argument("--width", type=int, default=2000)
    ap.add_argument("--tol", type=float, default=1.5)
    ap.add_argument("--json", help="write the table to this JSON file")
    a = ap.parse_args(argv)
    side = list(a.sidecars)
    if a.render:
        sys.path.insert(0, str(ROOT))
        from render import blender_ortho as bo
        res = bo.render_many(standard_jobs(a.styles.split(","), a.width))
        for r in res:
            print(f"rendered {Path(r['png']).name:34s} {r['width']}x{r['height']}  {r['seconds']:6.1f} s  {r['timings']}")
        side += [r["sidecar"] for r in res]
    parts = read_glb()
    pts, ws, gl = reference_points(parts)
    print("reference points (model, from out/pc12.glb):")
    for k, v in {**pts, **gl}.items():
        print(f"  {k:40s} {np.round(v['p'], 4).tolist()}")
    bad, table = 0, []
    for s in side:
        print(f"\n{Path(s).name}")
        for name, kind, uv, delta in check_sidecar(s, pts, ws, gl, a.tol, parts):
            flag = ""
            if delta is not None and abs(delta) > a.tol:
                flag, bad = "  <-- exceeds tol", bad + 1
            uvs = "" if uv is None else f"u {uv[0]:8.2f} v {uv[1]:8.2f}"
            delta = None if delta is None else float(delta)
            ds = "" if delta is None else f"delta {delta:+.2f} px"
            print(f"  {name:44s} {uvs:22s} {kind:40s} {ds}{flag}")
            table.append(dict(sidecar=Path(s).name, point=name, kind=kind, uv=None if uv is None else list(map(float, uv)),
                              delta_px=None if delta is None else float(delta)))
    if a.json:
        Path(a.json).write_text(json.dumps(table, indent=1))
    print(f"\n{bad} check(s) outside +-{a.tol} px")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
