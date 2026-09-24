"""
refs.overlay -- draw MODEL-coordinate geometry onto calibrated renders, blend and tile images.

Works with the sidecar JSON that render/blender_ortho.py writes next to every PNG:
    [u*w, v*w, w] = P @ [x, y, z, 1]   (u right, v down, origin at the top-left pixel corner,
                                         pixel centres at +0.5; w == 1 for orthographic views)
Model coordinates: x = station aft of the datum, y = butt line (+ starboard), z = water line [m].
Plain numpy + Pillow (system python3); no Blender needed.

Polylines are (N, 3) model points, or (N, 2) points in the view's natural 2-D coordinates:
    side_port / side_stbd -> (x, z)      top / top_true / bottom -> (x, y)      front / rear -> (y, z)
The missing coordinate is filled with `fill` (default 0; irrelevant for orthographic views).  For a
perspective render pass view='side' | 'top' | 'front' (or any view name) to say which plane 2-D
points live in, and `fill` for the constant coordinate (e.g. the butt line of a side-window outline).

API:
    from refs import overlay as ov
    ov.draw_polylines('out/tmp/render/side_port_lines.png', None, [pts_xz, ...], 'out/tmp/x.png',
                      color='red', width=2, closed=True)           # sidecar=None -> <render>.json
    ov.draw_points(render, sidecar, pts, out, color, radius=4, labels=None)
    ov.draw_grid(render, sidecar, out, step=0.5)                     # labelled model grid (ortho)
    ov.blend(render, other, alpha=0.5, out=None)                     # -> PIL image
    ov.mosaic([a, b, c], out, cols=2, labels=['render', 'photo', 'overlay'])
    ov.project(sidecar, pts) / ov.unproject(sidecar, uv)             # model <-> pixel (ortho inverse)
    Images may be paths or PIL images; draw_* accept out=None and return the PIL image.

CLI (from pc12/):
    python3 -m refs.overlay draw  RENDER.png POLY.json [--color red --width 2 --closed --view side] -o OUT.png
    python3 -m refs.overlay points RENDER.png "0.39,0,1.655" "3.215,0,2.2" -o OUT.png
    python3 -m refs.overlay grid  RENDER.png --step 0.25 -o OUT.png
    python3 -m refs.overlay blend A.png B.png --alpha 0.5 -o OUT.png
    python3 -m refs.overlay mosaic A.png B.png C.png --cols 3 --labels a,b,c -o OUT.png
    python3 -m refs.overlay project SIDECAR.json "0.39,0,1.655" ...
  POLY files: .json (list of point lists, or {name: point list}), .npy ((N,2|3) or list), .csv/.txt
  (one point per line, commas or spaces, blank line = new polyline).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

NATURAL = {"side_port": "xz", "side_stbd": "xz", "side": "xz", "top": "xy", "top_true": "xy", "bottom": "xy",
           "plan": "xy", "front": "yz", "rear": "yz"}
AX = {"x": 0, "y": 1, "z": 2}
SUPERSAMPLE = 3


# ---------------------------------------------------------------------------------------- sidecars
def load_sidecar(sidecar, render_png=None):
    """dict | path to the .json | None (-> <render_png>.json)."""
    if isinstance(sidecar, dict):
        return sidecar
    if sidecar is None:
        if render_png is None or not isinstance(render_png, (str, Path)):
            raise ValueError("need a sidecar (or a render path next to its .json)")
        sidecar = Path(render_png).with_suffix(".json")
    p = Path(sidecar)
    if p.suffix.lower() == ".png":
        p = p.with_suffix(".json")
    return json.loads(p.read_text())


def _img(im, mode="RGBA"):
    if isinstance(im, Image.Image):
        return im.convert(mode)
    return Image.open(im).convert(mode)


def to_3d(pts, sidecar=None, view=None, fill=0.0):
    """(N,2) natural view coordinates or (N,3) model points -> (N,3) model points."""
    a = np.asarray(pts, float)
    if a.ndim != 2:
        raise ValueError(f"polyline must be (N,2) or (N,3), got {a.shape}")
    if a.shape[1] == 3:
        return a
    if a.shape[1] != 2:
        raise ValueError(f"polyline must be (N,2) or (N,3), got {a.shape}")
    v = view or (sidecar or {}).get("view")
    if v not in NATURAL:
        raise ValueError(f"2-D points need an orthographic view or view=side|top|front (got {v!r})")
    ax = NATURAL[v]
    X = np.full((len(a), 3), float(fill))
    X[:, AX[ax[0]]] = a[:, 0]
    X[:, AX[ax[1]]] = a[:, 1]
    return X


def project(sidecar, pts, view=None, fill=0.0, return_w=False):
    """Model points ((N,3), or (N,2) natural) -> pixels (N,2) (u right, v down, corner origin)."""
    sc = load_sidecar(sidecar)
    P = np.asarray(sc["P"], float)
    X = to_3d(pts, sc, view, fill)
    h = X @ P[:, :3].T + P[:, 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        uv = h[:, :2] / h[:, 2:3]
    return (uv, h[:, 2]) if return_w else uv


def unproject(sidecar, uv):
    """Orthographic only: pixels (N,2) -> natural 2-D model coordinates (N,2) of the view."""
    sc = load_sidecar(sidecar)
    if sc.get("projection") != "ortho":
        raise ValueError("unproject needs an orthographic sidecar")
    P = np.asarray(sc["P"], float)
    ax = sc["axes"]
    cols = [AX[ax[0]], AX[ax[1]]]
    A = P[:2, cols]
    uv = np.atleast_2d(np.asarray(uv, float))
    return np.linalg.solve(A, (uv - P[:2, 3]).T).T


# ---------------------------------------------------------------------------------------- drawing
def _color(c, alpha=255):
    if isinstance(c, str):
        from PIL import ImageColor
        rgb = ImageColor.getrgb(c)
        return rgb if len(rgb) == 4 else (*rgb, alpha)
    c = tuple(int(round(v * 255)) if isinstance(v, float) and v <= 1.0 else int(v) for v in c)
    return c if len(c) == 4 else (*c, alpha)


def _as_list(polylines):
    if isinstance(polylines, dict):
        return list(polylines.values())
    if isinstance(polylines, np.ndarray) and polylines.ndim == 2:
        return [polylines]
    if isinstance(polylines, (list, tuple)) and len(polylines) and np.ndim(polylines[0]) == 1:
        return [np.asarray(polylines, float)]
    return list(polylines)


class _Canvas:
    """Anti-aliased drawing: an RGBA layer at SUPERSAMPLE x, downsampled and composited."""

    def __init__(self, base):
        self.base = base
        self.S = SUPERSAMPLE
        self.layer = Image.new("RGBA", (base.width * self.S, base.height * self.S), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.layer)

    def xy(self, uv):
        return [(float(u) * self.S - 0.5, float(v) * self.S - 0.5) for u, v in uv]

    def result(self):
        small = self.layer.resize(self.base.size, Image.Resampling.BOX)
        return Image.alpha_composite(self.base, small)


def _segments(uv, w, closed):
    """Split a projected polyline where points are behind the camera or not finite."""
    ok = np.isfinite(uv).all(1) & (w > 1e-9)
    idx = list(range(len(uv))) + ([0] if closed and len(uv) > 2 else [])
    runs, cur = [], []
    for i in idx:
        if ok[i]:
            cur.append(uv[i])
        else:
            if len(cur) > 1:
                runs.append(np.array(cur))
            cur = []
    if len(cur) > 1:
        runs.append(np.array(cur))
    return runs


def _save(im, out):
    if out is not None:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        im.save(str(out))
    return im


def draw_polylines(render_png, sidecar_json, polylines, out_png, color="red", width=2.0, closed=False,
                   view=None, fill=0.0, dash=None):
    """Draw model-coordinate polylines onto a calibrated render.
    polylines: one (N,2|3) array, a list of them, or {name: array}.  width in output pixels.
    dash: (on, off) in pixels for dashed lines.  Returns the PIL image (and writes out_png if given)."""
    sc = load_sidecar(sidecar_json, render_png)
    base = _img(render_png)
    cv = _Canvas(base)
    col = _color(color)
    lw = max(1, int(round(width * cv.S)))
    for pl in _as_list(polylines):
        pl = np.asarray(pl, float)
        if len(pl) < 2:
            continue
        uv, w = project(sc, pl, view, fill, return_w=True)
        for run in _segments(uv, w, closed):
            pts = cv.xy(run)
            if dash:
                _dashed(cv.draw, pts, col, lw, dash[0] * cv.S, dash[1] * cv.S)
            else:
                cv.draw.line(pts, fill=col, width=lw, joint="curve")
    return _save(cv.result().convert(base.mode), out_png)


def _dashed(draw, pts, col, lw, on, off):
    pos, state_on, left = 0.0, True, on
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while t < L - 1e-9:
            step = min(left, L - t)
            if state_on:
                a, b = t / L, (t + step) / L
                draw.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)],
                          fill=col, width=lw)
            t += step
            left -= step
            if left <= 1e-9:
                state_on = not state_on
                left = on if state_on else off
        pos += L


def _font(size):
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_points(render_png, sidecar_json, pts, out_png, color="red", radius=4.0, labels=None, view=None,
                fill=0.0, cross=True, font_px=13):
    """Mark model points (crosshair + circle) with optional text labels."""
    sc = load_sidecar(sidecar_json, render_png)
    base = _img(render_png)
    cv = _Canvas(base)
    col = _color(color)
    uv, w = project(sc, np.atleast_2d(np.asarray(pts, float)), view, fill, return_w=True)
    S, r = cv.S, radius * cv.S
    font = _font(int(font_px * S))
    for i, ((u, v), wi) in enumerate(zip(uv, w)):
        if not (np.isfinite(u) and np.isfinite(v)) or wi <= 0:
            continue
        x, y = u * S - 0.5, v * S - 0.5
        cv.draw.ellipse([x - r, y - r, x + r, y + r], outline=col, width=max(1, S))
        if cross:
            cv.draw.line([(x - 2 * r, y), (x + 2 * r, y)], fill=col, width=max(1, S))
            cv.draw.line([(x, y - 2 * r), (x, y + 2 * r)], fill=col, width=max(1, S))
        if labels is not None and i < len(labels) and labels[i]:
            cv.draw.text((x + 2 * r, y - 2 * r - font_px * S), str(labels[i]), fill=col, font=font)
    return _save(cv.result().convert(base.mode), out_png)


def draw_grid(render_png, sidecar_json, out_png, step=0.5, color=(0, 120, 255, 110), width=1.0, labels=True,
              font_px=12, major=None):
    """Model-coordinate grid (orthographic sidecars): lines every `step` m in the view's natural axes."""
    sc = load_sidecar(sidecar_json, render_png)
    if sc.get("projection") != "ortho":
        raise ValueError("draw_grid needs an orthographic sidecar")
    base = _img(render_png)
    cv = _Canvas(base)
    col = _color(color)
    ax = sc["axes"]
    (a0, a1), (b0, b1) = sc["bounds"][ax[0]], sc["bounds"][ax[1]]
    font = _font(int(font_px * cv.S))
    lw = max(1, int(round(width * cv.S)))
    for axis, (lo, hi), (olo, ohi) in ((0, (a0, a1), (b0, b1)), (1, (b0, b1), (a0, a1))):
        for val in np.arange(math.ceil(lo / step) * step, hi + 1e-9, step):
            q = np.array([[val, olo], [val, ohi]]) if axis == 0 else np.array([[olo, val], [ohi, val]])
            uv = project(sc, q)
            is_major = major and abs(val / major - round(val / major)) < 1e-6
            cv.draw.line(cv.xy(uv), fill=col, width=lw * (2 if is_major else 1))
            if labels:
                u, v = uv[0] if axis == 0 else uv[np.argmin(uv[:, 0])]
                u = min(max(u, 0), base.width - 40)
                v = min(max(v, 0), base.height - 16) if axis == 1 else 2
                cv.draw.text((u * cv.S + 3 * cv.S, v * cv.S + 2 * cv.S), f"{ax[axis]} {val:.2f}".rstrip("0").rstrip("."),
                             fill=col[:3] + (255,), font=font)
    return _save(cv.result().convert(base.mode), out_png)


# ---------------------------------------------------------------------------------------- blending
def blend(render_png, other_png, alpha=0.5, out_png=None, resize=True):
    """Alpha blend: result = (1 - alpha) * render + alpha * other (other resized to the render if needed)."""
    a = _img(render_png, "RGB")
    b = _img(other_png, "RGB")
    if b.size != a.size:
        if not resize:
            raise ValueError(f"size mismatch {a.size} vs {b.size}")
        b = b.resize(a.size, Image.Resampling.LANCZOS)
    return _save(Image.blend(a, b, float(alpha)), out_png)


def difference(render_png, other_png, out_png=None):
    """Colour-coded comparison of two line images: render dark lines in red, other in blue, both black."""
    a = np.asarray(_img(render_png, "L"), float) / 255
    b = _img(other_png, "L")
    if b.size[::-1] != a.shape:
        b = b.resize((a.shape[1], a.shape[0]), Image.Resampling.LANCZOS)
    b = np.asarray(b, float) / 255
    ia, ib = 1 - a, 1 - b                      # ink of each image
    rgb = np.clip(np.stack([1 - ib, 1 - np.maximum(ia, ib), 1 - ia], -1), 0, 1)
    return _save(Image.fromarray((rgb * 255).astype(np.uint8)), out_png)


def mosaic(images, out_png=None, cols=None, labels=None, pad=8, bg="white", height=None, font_px=16):
    """Tile images in a grid (cols=None -> one row).  Each row is scaled to a common height
    (height=None -> the smallest image height in that row).  Returns the PIL image."""
    ims = [_img(im, "RGB") for im in images]
    n = len(ims)
    cols = cols or n
    rows = [ims[i:i + cols] for i in range(0, n, cols)]
    labs = list(labels or [])
    font = _font(font_px)
    lab_h = font_px + 6 if labels else 0
    row_imgs, k = [], 0
    for r in rows:
        h = height or min(im.height for im in r)
        scaled = [im.resize((max(1, round(im.width * h / im.height)), h), Image.Resampling.LANCZOS) for im in r]
        wtot = sum(im.width for im in scaled) + pad * (len(scaled) + 1)
        row = Image.new("RGB", (wtot, h + lab_h + pad), bg)
        x = pad
        d = ImageDraw.Draw(row)
        for im in scaled:
            row.paste(im, (x, lab_h + pad))
            if k < len(labs) and labs[k]:
                d.text((x, 2), str(labs[k]), fill="black", font=font)
            x += im.width + pad
            k += 1
        row_imgs.append(row)
    W = max(r.width for r in row_imgs)
    H = sum(r.height for r in row_imgs) + pad
    out = Image.new("RGB", (W, H), bg)
    y = 0
    for r in row_imgs:
        out.paste(r, (0, y))
        y += r.height
    return _save(out, out_png)


# ---------------------------------------------------------------------------------------- CLI
def load_polylines(path):
    p = Path(path)
    if p.suffix == ".json":
        d = json.loads(p.read_text())
        if isinstance(d, dict):
            return {k: np.asarray(v, float) for k, v in d.items()}
        if d and np.ndim(d[0]) == 1:
            return [np.asarray(d, float)]
        return [np.asarray(v, float) for v in d]
    if p.suffix == ".npy":
        a = np.load(p, allow_pickle=True)
        return [a] if a.dtype != object and a.ndim == 2 else list(a)
    out, cur = [], []
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            if cur:
                out.append(np.array(cur))
                cur = []
            continue
        cur.append([float(t) for t in ln.replace(",", " ").split()])
    if cur:
        out.append(np.array(cur))
    return out


def _pt(s):
    return [float(t) for t in s.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m refs.overlay", description=__doc__.strip().split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw", help="draw polylines from a file")
    d.add_argument("render")
    d.add_argument("poly", nargs="+")
    d.add_argument("--sidecar")
    d.add_argument("--color", default="red")
    d.add_argument("--width", type=float, default=2.0)
    d.add_argument("--closed", action="store_true")
    d.add_argument("--view")
    d.add_argument("--fill", type=float, default=0.0)
    d.add_argument("-o", "--out", required=True)
    q = sub.add_parser("points", help="mark model points x,y,z")
    q.add_argument("render")
    q.add_argument("pts", nargs="+")
    q.add_argument("--sidecar")
    q.add_argument("--color", default="red")
    q.add_argument("--radius", type=float, default=4)
    q.add_argument("-o", "--out", required=True)
    g = sub.add_parser("grid", help="labelled model grid")
    g.add_argument("render")
    g.add_argument("--sidecar")
    g.add_argument("--step", type=float, default=0.5)
    g.add_argument("-o", "--out", required=True)
    b = sub.add_parser("blend")
    b.add_argument("a")
    b.add_argument("b")
    b.add_argument("--alpha", type=float, default=0.5)
    b.add_argument("-o", "--out", required=True)
    m = sub.add_parser("mosaic")
    m.add_argument("images", nargs="+")
    m.add_argument("--cols", type=int)
    m.add_argument("--labels")
    m.add_argument("--height", type=int)
    m.add_argument("-o", "--out", required=True)
    pr = sub.add_parser("project", help="print pixel coordinates of model points")
    pr.add_argument("sidecar")
    pr.add_argument("pts", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "draw":
        im = a.render
        cols = ["red", "blue", "green", "magenta", "orange", "cyan"]
        for i, f in enumerate(a.poly):
            im = draw_polylines(im, a.sidecar or load_sidecar(None, a.render), load_polylines(f), None,
                                a.color if len(a.poly) == 1 else cols[i % len(cols)], a.width, a.closed, a.view, a.fill)
        _save(im, a.out)
    elif a.cmd == "points":
        draw_points(a.render, a.sidecar, [_pt(s) for s in a.pts], a.out, a.color, a.radius, labels=a.pts)
    elif a.cmd == "grid":
        draw_grid(a.render, a.sidecar, a.out, a.step)
    elif a.cmd == "blend":
        blend(a.a, a.b, a.alpha, a.out)
    elif a.cmd == "mosaic":
        mosaic(a.images, a.out, a.cols, a.labels.split(",") if a.labels else None, height=a.height)
    elif a.cmd == "project":
        uv = project(a.sidecar, [_pt(s) for s in a.pts])
        for s, (u, v) in zip(a.pts, uv):
            print(f"{s:>28s} -> u {u:9.2f}  v {v:9.2f}")
    if getattr(a, "out", None):
        print(a.out)


if __name__ == "__main__":
    main()
