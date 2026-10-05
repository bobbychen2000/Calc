"""
Shared drawing helpers for the yoke sheets L6Y / L6Y2 (drawing/yoke_sheet.py, drawing/yoke_sheet2.py): primitives in
yoke-local millimetres and the geometry they draw, all derived from model/interior.py YOKE_DESIGN through the rev J
solids of model/yoke_geom.py (exact sections = contours of the solids on the cutting plane, silhouettes = contours of
the solids' minimum along the view direction, feature curves = the table's curves placed on the solids' faces).
Nothing comes from a mesh or a photo.
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, MUTED, PAPER, ACCENT, W_OBJ, W_FINE, W_THIN, CHAIN, PHANTOM,  # noqa: E402,F401
                            table, view_title, notes)
from drawing.canvas import text_width  # noqa: E402
from drawing.wheel_sheet import hatch  # noqa: E402
from model import interior as I  # noqa: E402
from model import yoke_geom as G  # noqa: E402

D = I.YOKE_DESIGN
TXT = 2.2
TXT_S = 2.1
WHITE = "#F4F5F6"            # white cover
SILVER = "#C9CDD2"           # upper insert / badge
SMOKE = "#9AA1A9"            # lower insert
BLACK = "#3A4045"            # body / grips (satin black, drawn dark grey so the lines read)
BODY = "#4A5257"             # body in the side / plan views
LEATHER = "#565D63"          # pads
RED = "#C8423B"
GLOSS = "#1E2326"            # gloss black bezels
SWITCH = "#3E464B"
COLLAR = "#6F777D"           # column surround (satin dark grey)
HID = (1.6, 0.9)
W_CREASE = 0.22              # crease / parting lines (visible edges inside an outline)
W_TAN = 0.10                 # tangent edges (the start of a radius)
PART_STYLE = dict(cover=(WHITE, -45.0, 0.8), body=("#E3E6E8", 45.0, 1.4), grip_out=("#D7DBDE", 45.0, 1.0),
                  grip_in=("#D7DBDE", -45.0, 1.0), black=("#E3E6E8", 45.0, 1.2))


# ============================================================================================ primitives (local mm)
def mkview(name, axes, sx, sy, origin, s, note):
    """View over yoke-local MILLIMETRES: sheet = diag(sx, sy) * s * (p, q) + origin (s = sheet mm per mm)."""
    A = np.array([[sx * s, 0.0], [0.0, sy * s]])
    return M.View(name, axes, A, np.asarray(origin, float), 1.0 / s, None, note + " -- yoke-local mm")


def P_(v, P):
    return [tuple(q) for q in v(np.asarray(P, float))]


def poly(ds, v, P, w=W_OBJ, fill=None, dash=None, color=None, closed=True):
    ds.cv.path(P_(v, P), w, dash, closed=closed, fill=fill, stroke=w > 0, color=color)


def line(ds, v, P, w=W_FINE, dash=None, color=None):
    ds.cv.path(P_(v, P), w, dash, color=color)


def circle(c, r, n=72, a0=0.0, a1=360.0):
    a = np.radians(np.linspace(a0, a1, n))
    return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]


def circ(ds, v, c, d, w=W_FINE, fill=None, color=None, dash=None, n=72):
    P = circle(c, 0.5 * d, n + 1)[:-1]
    ds.cv.path(P_(v, P), w, dash, closed=True, fill=fill, stroke=w > 0, color=color)


def lbl(ds, X, Y, s, size=TXT, anchor="start", color=INK, weight=400, font="label"):
    ds.text(X, Y, s, size, font, anchor, fill=color, weight=weight, tag="lbl", vcenter=True)


def arrow_head(ds, tip, d, L=1.8, W=0.65, color=None):
    d = np.asarray(d, float) / np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    tip = np.asarray(tip, float)
    b = tip - L * d
    ds.cv.polygon([tuple(tip), tuple(b + 0.5 * W * n), tuple(b - 0.5 * W * n)], fill=color or INK)


def dim(ds, p1, p2, pos, text, orient="h", size=TXT, color=INK, text_at=None, gap=0.8, outside=None):
    """Linear dimension between sheet points p1, p2 (dimension line at y = pos for 'h', x = pos for 'v')."""
    p1, p2 = np.asarray(p1, float), np.asarray(p2, float)
    a, b = (np.array([p1[0], pos]), np.array([p2[0], pos])) if orient == "h" else \
        (np.array([pos, p1[1]]), np.array([pos, p2[1]]))
    for f, e in ((p1, a), (p2, b)):
        vv = e - f
        L = np.linalg.norm(vv)
        if L > gap + 0.2:
            u = vv / L
            ds.cv.line(tuple(f + gap * u), tuple(e + 1.2 * u), W_THIN, color=color)
    L = np.linalg.norm(b - a)
    u = (b - a) / max(L, 1e-9)
    tw = text_width(text, size, "mono")
    out = outside if outside is not None else L < 6.0
    if not out:
        ds.cv.line(tuple(a), tuple(b), W_THIN, color=color)
        arrow_head(ds, a, -u, color=color)
        arrow_head(ds, b, u, color=color)
    else:
        ds.cv.line(tuple(a - 3.5 * u), tuple(b + 3.5 * u), W_THIN, color=color)
        arrow_head(ds, a, u, color=color)
        arrow_head(ds, b, -u, color=color)
    if text_at is not None:
        tx, ty = text_at
    elif not out and L > tw + 4.0:
        tx, ty = 0.5 * (a + b)
    else:
        tx, ty = b + (4.8 + 0.5 * tw) * u
    if orient == "h":
        ds.text(tx, ty - 0.7, text, size, "mono", "middle", fill=color, tag="dim")
    else:
        ds.text(tx - 0.7, ty, text, size, "mono", "middle", rot=-90, fill=color, tag="dim")


def leader(ds, P, T, text, lines=None, size=TXT, color=INK, weight=600, dot=True):
    """Leader from sheet point P to the text anchor T (sheet), a 2 mm shoulder, the text on the far side."""
    X, Y = P
    right = T[0] >= X
    ds.cv.line((X, Y), tuple(T), W_THIN, color=color)
    sh = 2.0 if right else -2.0
    ds.cv.line(tuple(T), (T[0] + sh, T[1]), W_THIN, color=color)
    if dot:
        ds.cv.circle(X, Y, 0.4, w=0.0, fill=color, stroke=False)
    for i, t in enumerate([text] + list(lines or [])):
        ds.text(T[0] + sh + (0.6 if right else -0.6), T[1] + i * 1.3 * size, t, size if i == 0 else min(size, TXT_S),
                "label", "start" if right else "end", vcenter=True, fill=color, weight=weight if i == 0 else 400,
                tag="lbl")


def balloon(ds, P, B, n, r=2.7):
    """Item balloon: leader from the sheet point P (dot) to a circle of radius r at B carrying the item number."""
    P, B = np.asarray(P, float), np.asarray(B, float)
    d = P - B
    L = np.linalg.norm(d)
    if L > r + 0.5:
        ds.cv.line(tuple(B + r * d / L), tuple(P), W_THIN)
    ds.cv.circle(P[0], P[1], 0.45, w=0.0, fill=INK, stroke=False)
    ds.cv.circle(B[0], B[1], r, w=W_FINE, fill=PAPER)
    ds.text(B[0], B[1], str(n), 2.5, "label", "middle", weight=700, vcenter=True, tag="balloon")


def centre_mark(ds, v, c, r, ext=2.0):
    X, Y = v.pt(*c)
    k = abs(v.A[0, 0]) * r + ext
    ds.cv.line((X - k, Y), (X + k, Y), W_THIN, CHAIN, color=MUTED)
    ds.cv.line((X, Y - k), (X, Y + k), W_THIN, CHAIN, color=MUTED)


def hatch_poly(ds, v, P, ang=45.0, step=1.0, fill=PAPER, w=W_OBJ):
    S_ = v(np.asarray(P, float))
    ds.cv.path([tuple(q) for q in S_], 0.0, closed=True, fill=fill, stroke=False)
    hatch(ds, S_, ang, step)
    ds.cv.path([tuple(q) for q in S_], w, closed=True)


def break_line(ds, v, p0, p1, amp=1.6, n=4):
    """Short zig-zag break line between local points p0, p1 of view v."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    t = np.linspace(0, 1, 2 * n + 1)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
    off = amp * np.array([0 if i in (0, 2 * n) else (1 if i % 2 else -1) for i in range(2 * n + 1)])
    line(ds, v, p0 + t[:, None] * d + off[:, None] * nrm, W_THIN)


def ticks(c, r0, r1, a0, a1, n):
    """Tick strokes (list of 2-point arrays) radially between r0 and r1 at n angles from a0 to a1 deg (0 = +x)."""
    out = []
    for a in np.radians(np.linspace(a0, a1, n)):
        e = np.array([math.cos(a), math.sin(a)])
        out.append(np.array([np.asarray(c) + r0 * e, np.asarray(c) + r1 * e]))
    return out


def wrap_rows(rows, widths, size):
    from drawing import sheet as S_
    out = []
    for r in rows:
        cells = [S_.wrap(str(c), w - 2.4, size) for c, w in zip(r, widths)]
        n = max(len(c) for c in cells)
        for k in range(n):
            out.append(tuple(c[k] if k < len(c) else "" for c in cells))
    return out


# ============================================================================================ switch geometry (2-D)
def rocker_halves(n=10):
    """Split bow-tie rocker in its own plane (x across the head, y along the face): two MIRROR-IMAGE lobes, each
    from the split (|x| = gap / 2, waist ww) to an end of width we with a round end (R we / 2); D7: one lobe is
    built and mirrored, so neither crosses itself."""
    tr = D["trim"]
    L, we, ww, gap = float(tr[3]), float(tr[4]), float(tr[5]), float(tr[6])
    r = 0.5 * we
    xc = 0.5 * L - r
    arc = [(xc + r * math.cos(t), r * math.sin(t)) for t in np.linspace(-0.5 * math.pi, 0.5 * math.pi, n)]
    half = np.array([(0.5 * gap, -0.5 * ww)] + arc + [(0.5 * gap, 0.5 * ww)], float)
    return [half, half * [-1.0, 1.0]]


def hexagon(across_corners, rot=0.0):
    r = 0.5 * float(across_corners)
    a = np.radians(np.arange(6) * 60.0 + 30.0 + rot)
    return np.c_[r * np.cos(a), r * np.sin(a)]


# ============================================================================================ geometry on the solids
def trim_frame():
    """(c, n, eu, ev) of the outboard head's round face, co-pilot sense (u, h, a)."""
    c, n = G.head_out_face()
    eu, ev = G._facet_frame(c, n)
    return c, n, eu, ev


def shield_frame():
    """(c, n, eu, ev) of the inboard head's shield facet in the CO-PILOT sense (the inboard head at u < 0); eu points
    away from the yoke centreline (-u), ev up the facet."""
    c, n = G.head_in_face()
    eu, ev = G._facet_frame(c, n)
    m = np.array([-1.0, 1.0, 1.0])
    return c * m, n * m, eu * m, ev * m


def on_frame(fr, P2):
    """2-D points (x, y) of a facet frame -> 3-D (u, h, a)."""
    c, n, eu, ev = fr
    P2 = np.atleast_2d(np.asarray(P2, float))
    return c + P2[:, :1] * eu + P2[:, 1:2] * ev


def front_to_plane(fr, P2):
    """Front-view points (u, h) lifted along a onto the facet plane of frame fr -> 3-D (u, h, a)."""
    c, n, _, _ = fr
    P2 = np.atleast_2d(np.asarray(P2, float))
    a = c[2] - ((P2[:, 0] - c[0]) * n[0] + (P2[:, 1] - c[1]) * n[1]) / n[2]
    return np.c_[P2, a]


def VIEWPROJ(P3, view):
    """3-D (u, h, a) -> 2-D of a view: 'front' (u, h), 'side' (a, h), 'plan' (u, a)."""
    P3 = np.atleast_2d(P3)
    return {"front": P3[:, [0, 1]], "side": P3[:, [2, 1]], "plan": P3[:, [0, 2]]}[view]


def tcs_centre3():
    tu, th = (float(x) for x in D["tcs"][:2])
    return np.array([tu, th, float(G.face_a(th))])


def face_normal3():
    t = math.radians(float(D["face_tilt"]))
    return np.array([0.0, math.sin(t), math.cos(t)])


def afcs_centre3():
    au, ah = (float(x) for x in D["afcs"][:2])
    return np.array([au, ah, float(G.face_a(ah)) - float(D["cover_t"])])


def top_land_line():
    """Front-view polylines of the top land's lower edge: the shell outline offset inward by the land height where
    its outward normal points up (crown, chamfers, arm tops)."""
    Q = G.shell_outline()
    land_h = float(D["crown"][3])
    t = np.roll(Q, -2, 0) - np.roll(Q, 2, 0)
    nrm = np.c_[t[:, 1], -t[:, 0]]
    nrm /= np.linalg.norm(nrm, axis=1)[:, None]
    cen = np.array([0.0, 20.0])
    flip = np.einsum("ij,ij->i", nrm, Q - cen) < 0
    nrm[flip] *= -1
    up = nrm[:, 1] > 0.45
    P = Q - land_h * nrm
    runs, cur = [], []
    for i in range(len(Q)):
        if up[i]:
            cur.append(P[i])
        elif cur:
            runs.append(np.array(cur))
            cur = []
    if cur:
        runs.append(np.array(cur))
    return [r for r in runs if len(r) > 4]


def crown_crease():
    """Front-view polyline of the crown crease across the upper insert (h = crown[0], between the insert's sides)."""
    hc = float(D["crown"][0])
    P = G.insert_upper_outline()
    xs = []
    Q = np.vstack([P, P[:1]])
    for a, b in zip(Q[:-1], Q[1:]):
        if (a[1] - hc) * (b[1] - hc) < 0:
            xs.append(a[0] + (hc - a[1]) / (b[1] - a[1]) * (b[0] - a[0]))
    xs = sorted(xs)
    return np.array([(xs[0], hc), (xs[-1], hc)]) if len(xs) >= 2 else None


def heel_line(g):
    """Front-view line of the heel lip's top edge (the pad's bottom offset by the frame), own sense."""
    P = G.pad_outline(g)
    b = float(P[:, 1].min())
    sel = P[:, 1] < b + 3.0
    return np.array([(P[sel, 0].min(), b - 0.6 * float(D["grip_frame"])), (P[sel, 0].max(), b - 0.6 * float(D["grip_frame"]))])


@lru_cache(maxsize=None)
def views(axis):
    """Silhouettes of every part along axis (G.view_silhouettes), largest contour per part plus the rest."""
    return G.view_silhouettes(axis, step=0.4, depth_step=0.5)


def draw_parts(ds, v, sil, order, fills=None, w=W_OBJ):
    """Draw silhouette contours {part: [contours]} filled in `order` (far to near)."""
    fills = fills or {}
    for p in order:
        for C in sorted(sil.get(p, []), key=len, reverse=True):
            if len(C) < 8:
                continue
            poly(ds, v, C, w, fill=fills.get(p, BLACK))


def section_contours(S, parts):
    """Closed contours of a G.section result, part by part, biggest first."""
    out = []
    for p in parts:
        for C in sorted(S.get(p, []), key=len, reverse=True):
            if len(C) > 8 and np.allclose(C[0], C[-1], atol=0.6):
                out.append((p, C))
    return out


def draw_section(ds, v, S, parts=("body", "cover", "grip_out", "grip_in"), style=None):
    """Hatch the section contours (each part its own angle / step: adjacent parts read apart)."""
    style = style or PART_STYLE
    for p, C in section_contours(S, parts):
        fill, ang, step = style.get(p, (PAPER, 45.0, 1.0))
        hatch_poly(ds, v, C, ang=ang, step=step, fill=fill)
