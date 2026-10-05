"""
Sheet L6Y -- PC-24-STYLE CONTROL YOKE, DETAIL (PC12-L6Y), drawn from model/interior.py YOKE_DESIGN (rev I) and the
yoke_* helpers that the L6 / L6B knee checks and (in Stage 3) the 3-D builder use.  Nothing comes from the mesh or a
photo: the photo overlays are separate, git-ignored (python3 -m drawing.yoke_overlay -> refs/cache/overlays/yoke).

    python3 -m drawing.master L6Y

A1, first-angle, yoke-local millimetres (u outboard, h up from the hub centre = the column axis, a aft of the aft face
at the insert step).  The PILOT yoke is drawn; the co-pilot yoke is its mirror image (switches outboard on both).
  FRONT ELEVATION (1:1, looking forward, as the pilot sees it), SIDE ELEVATION (1:1, from outboard, with the column and
  its surround on the lower panel), VIEW FROM ABOVE (1:1), SECTIONS A-A (mid-grip, 2:1), B-B (horizontal through the
  badge and the TCS, 1:1), C-C (the trim head, 2:1), DETAILS D (TCS), E (AFCS disconnect), F (pitch-trim switch), G
  (inboard push button), H (badge) at 4:1 / 3:1, tables: finishes, main dimensions, the knee / roll check (L6B) rev H ->
  rev I, notes, open points, revisions.  NO MARKINGS: the badge is an abstract winged plate, legends are tick strokes.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from drawing import master as M  # noqa: E402
from drawing.master import (INK, GRID, MUTED, PAPER, ACCENT, W_OBJ, W_FINE, W_THIN, CHAIN, PHANTOM, table,  # noqa
                            view_title, notes)
from drawing.canvas import text_width  # noqa: E402
from drawing.wheel_sheet import hatch  # noqa: E402
from model import interior as I  # noqa: E402

SHEET = dict(id="L6Y", title="CONTROL YOKE - DETAIL", subtitle="PC-24-STYLE CONTROL YOKE - DETAIL", size="A1",
             scale="AS SHOWN", rev="A", order=62, sheet_no="1 OF 1", dwg="PC12-L6Y")
REVISIONS = (
    ("A", "2026-10-05", "first issue (owner 2026-10-05: 'the yoke isn't quite right especially if you look at the "
                        "details'): yoke re-measured on 8 PRO photos (P1046408 through the fitted camera panel_408, "
                        "P1046409 / 10, Mexico and AOPA press photos, JTF p.18) incl. a bundle adjustment for depth; "
                        "YOKE_DESIGN rev I replaces the rev H outline (L6 / L6B rev I)"),
)
D = I.YOKE_DESIGN
TXT = 2.2
TXT_S = 2.1
WHITE = "#F4F5F6"            # white cover
SILVER = "#C9CDD2"           # upper insert / badge
SMOKE = "#9AA1A9"            # lower insert
BLACK = "#3A4045"            # body / grips (satin black, drawn dark grey so the lines read)
LEATHER = "#565D63"          # pads
RED = "#C8423B"
COLLAR = "#6F777D"           # column surround (satin dark grey)
HID = (1.6, 0.9)
W_CREASE = 0.22              # crease / parting lines (visible edges inside an outline)


# ============================================================================================ views (local mm)
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


def circ(ds, v, c, d, w=W_FINE, fill=None, color=None, dash=None, n=72):
    t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    P = np.c_[c[0] + 0.5 * d * np.cos(t), c[1] + 0.5 * d * np.sin(t)]
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


def radius_note(ds, P, T, text, size=TXT_S, color=INK):
    leader(ds, P, T, text, size=size, color=color, weight=500)


def centre_mark(ds, v, c, r, ext=2.0):
    X, Y = v.pt(*c)
    k = abs(v.A[0, 0]) * r + ext
    ds.cv.line((X - k, Y), (X + k, Y), W_THIN, CHAIN, color=MUTED)
    ds.cv.line((X, Y - k), (X, Y + k), W_THIN, CHAIN, color=MUTED)


# ============================================================================================ 3-D derived outlines
# Each solid is a set of samples (u, h) of its front outline with an a-interval [a_lo, a_hi] through it (the slab
# between its forward and aft faces); its side / plan silhouettes are the per-row / per-column extremes.
def _band_outline(x, lo, hi, step=0.5, smooth=3):
    """Closed outline from samples at x with intervals [lo, hi]: per bin of x the min lo and max hi."""
    from scipy.ndimage import median_filter
    k = np.floor((x - x.min()) / step).astype(int)
    n = k.max() + 1
    mn = np.full(n, np.inf)
    mx = np.full(n, -np.inf)
    np.minimum.at(mn, k, lo)
    np.maximum.at(mx, k, hi)
    ok = np.isfinite(mn)
    xs = x.min() + (np.arange(n) + 0.5) * step
    xs, mn, mx = xs[ok], mn[ok], mx[ok]
    if smooth > 1 and len(xs) > smooth:
        from scipy.ndimage import uniform_filter1d
        mn = uniform_filter1d(median_filter(mn, smooth, mode="nearest"), 5, mode="nearest")
        mx = uniform_filter1d(median_filter(mx, smooth, mode="nearest"), 5, mode="nearest")
    xs = np.r_[xs[0] - 0.5 * step, xs, xs[-1] + 0.5 * step]
    mn, mx = np.r_[mn[0], mn, mn[-1]], np.r_[mx[0], mx, mx[-1]]
    return np.vstack([np.c_[xs, mn], np.c_[xs[::-1], mx[::-1]]])


def grip_samples(g):
    """(u, h, a_lo, a_hi) samples of a grip (own sense: u > 0 away from the yoke centreline) along the slab from its
    aft face (the trim head's facet where it stands proud) to its forward face, 12 steps (the toe-out shifts u)."""
    from cad import sdf2d
    gf = I.yoke_grip_faces(g)
    G = gf["G"]
    v, da = I.yoke_grip_shift(g)
    uu, hh = np.meshgrid(np.arange(G[:, 0].min(), G[:, 0].max() + 0.5, 0.5),
                         np.arange(G[:, 1].min(), G[:, 1].max() + 0.5, 0.5))
    m = sdf2d.polygon(uu, hh, G) <= 0
    Q = np.vstack([G, np.c_[uu[m], hh[m]]])
    a_aft = I.yoke_grip_aft_a(Q[:, 0], Q[:, 1], g)
    a_top = a_aft.copy()
    if g == "out":
        hf = I.yoke_head_facet()
        rel = np.c_[a_aft - hf["c"][0], Q[:, 0] - hf["c"][1], Q[:, 1] - hf["c"][2]]
        on_f = (np.abs(rel @ hf["eu"]) <= 0.5 * hf["size"]) & (np.abs(rel @ hf["ev"]) <= 0.5 * hf["size"])
        a_fac = hf["c"][0] - (rel[:, 1] * hf["n"][1] + rel[:, 2] * hf["n"][2]) / hf["n"][0]
        a_top = np.where(on_f, a_fac, a_aft)          # the facet: proud below its centre, a chamfer above
    a_fwd = a_aft + da
    out = []
    for t in np.linspace(0.0, 1.0, 13):
        a_t = a_top + t * (a_fwd - a_top)
        out.append(np.c_[Q[:, 0] + t * v[0], Q[:, 1], a_t, a_t])
    S = np.vstack(out)
    S[:, 2] = np.minimum(S[:, 2], S[:, 3])
    return S


BODY_TOP = ((-20.5, 67.0), (-34.0, 64.5), (-50.0, 61.0), (-60.0, 56.0))   # [E] the body's top behind the crown (a, h)
FOOT_R = 14.0                                                          # [E] forward-lower corner of the body
NECK_DEPTH = 25.0                                                      # [E] the necks' fore-aft depth


def body_front_a(h):
    """[E] a of the black body's forward face at height h: -body_depth, its top sloping aft to the crown (BODY_TOP), its
    lower forward corner rounded FOOT_R (hidden in every photo)."""
    h = np.asarray(h, float)
    bt = np.asarray(BODY_TOP, float)
    a = np.full(h.shape, -float(D["body_depth"]))
    a = np.where(h > bt[-1, 1], np.interp(h, bt[::-1, 1], bt[::-1, 0]), a)
    hb = -61.8 + FOOT_R
    c = -float(D["body_depth"]) + FOOT_R
    return np.where(h < hb, c - np.sqrt(np.clip(FOOT_R ** 2 - (h - hb) ** 2, 0, None)), a)


def body_samples():
    """(u, h, a_lo, a_hi) samples of the shell + body: inside the front outlines, from the forward face (body_front_a)
    to the aft face (the cover on the face profile; the necks blending to the grip heads' aft faces)."""
    from cad import sdf2d
    F = I.yoke_front_mm()
    sh, bo = F["shell"], F["body"]
    uu, hh = np.meshgrid(np.arange(-101.0, 101.0, 0.5), np.arange(-62.0, 90.0, 0.5))
    m = (sdf2d.polygon(uu, hh, sh) <= 0) | (sdf2d.polygon(uu, hh, bo) <= 0)
    u, h = uu[m], hh[m]
    in_sh = sdf2d.polygon(u, h, sh) <= 0
    a_aft = I.yoke_face_a(h) - np.where(in_sh, 0.0, float(D["cover_t"]))
    neck = (np.abs(u) > 58.0) & (h > 50.0) & ~in_sh
    t = np.clip((np.abs(u) - 58.0) / 34.0, 0, 1)
    a_head = np.where(u > 0, I.yoke_grip_aft_a(np.abs(u), h, "out"), I.yoke_grip_aft_a(np.abs(u), h, "in"))
    a_aft = np.where(neck, (1 - t) * a_aft + t * a_head, a_aft)
    a_front = np.where(neck, a_aft - NECK_DEPTH, body_front_a(h))
    return np.c_[u, h, a_front, a_aft]


def cover_samples():
    from cad import sdf2d
    sh = I.yoke_front_mm()["shell"]
    uu, hh = np.meshgrid(np.arange(-73.0, 73.5, 0.5), np.arange(-56.5, 67.5, 0.5))
    m = sdf2d.polygon(uu, hh, sh) <= 0
    u, h = uu[m], hh[m]
    a1 = I.yoke_face_a(h)
    return np.c_[u, h, a1 - float(D["cover_t"]), a1]


def side_outline(S):
    """(a, h) silhouette of samples (u, h, a_lo, a_hi)."""
    P = _band_outline(S[:, 1], S[:, 2], S[:, 3])
    return P[:, ::-1]


def plan_outline(S, sg=1.0):
    """(u, a) silhouette (from above) of samples; sg mirrors u."""
    return _band_outline(sg * S[:, 0], S[:, 2], S[:, 3])


# ============================================================================================ switch geometry (2-D)
def ticks(c, r0, r1, a0, a1, n):
    """Tick strokes (list of 2-point arrays) radially between r0 and r1 at n angles from a0 to a1 deg (u, h axes:
    0 = outboard (+u), 90 = up)."""
    out = []
    for a in np.radians(np.linspace(a0, a1, n)):
        e = np.array([math.cos(a), math.sin(a)])
        out.append(np.array([c + r0 * e, c + r1 * e]))
    return out


def circle(c, r, n=72, a0=0.0, a1=360.0):
    a = np.radians(np.linspace(a0, a1, n))
    return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]


def rocker_plan(L=None, we=None, ww=None, gap=None, n=10):
    """Split bow-tie rocker in its own plan (x along the rocker, y across): two halves widening from the waist to the
    ends, R 3 ends in plan; returns [half_a, half_b] closed outlines."""
    tr = D["trim"]
    L = float(tr[3]) if L is None else L
    we = float(tr[4]) if we is None else we
    ww = float(tr[5]) if ww is None else ww
    gap = float(tr[6]) if gap is None else gap
    out = []
    for sg in (-1, 1):
        x0, x1 = sg * 0.5 * gap, sg * 0.5 * L
        r = 0.5 * we
        xc = x1 - sg * r
        arc = [(xc + sg * r * math.cos(t), r * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, n)]
        if sg < 0:
            arc = [(xc - r * math.cos(t), -r * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, n)]
        P = [(x0, -0.5 * ww)] + arc[:1] + arc + [(x0, 0.5 * ww)]
        out.append(np.array(P, float))
    return out


def facet_map(P2):
    """Points (x across, y up the face) on the trim head's facet -> front view (u, h)."""
    hf = I.yoke_head_facet()
    P2 = np.asarray(P2, float)
    Q = hf["c"][None, :] + P2[:, :1] * hf["eu"][None, :] + P2[:, 1:2] * hf["ev"][None, :]
    return Q[:, 1:3]


def btn_map(P2):
    """Points (x across, y up) on the inboard grip's aft face about the button centre -> front view (u, h)
    (outboard-grip sense u > 0 of the inboard grip, mirror for the drawing)."""
    n = I.yoke_grip_normal("in")                                     # (a, u, h)
    eu = np.array([-n[1], n[0], 0.0])
    eu /= np.linalg.norm(eu)
    ev = np.cross(n, eu)
    bu, bh = (float(x) for x in D["button"][:2])
    c = np.array([float(I.yoke_grip_aft_a(bu, bh, "in")), bu, bh])
    P2 = np.asarray(P2, float)
    Q = c[None, :] + P2[:, :1] * eu[None, :] + P2[:, 1:2] * ev[None, :]
    return Q[:, 1:3]


# ============================================================================================ layout (sheet mm)
FR_O = (232.0, 122.0)        # front elevation: sheet position of the hub centre (1:1)
SD_O = (530.0, 122.0)        # side elevation: sheet position of (a 0, h 0) (1:1); the column is broken
TP_O = (232.0, 330.0)        # view from above: sheet position of (u 0, a 0) (1:1), forward up
COL_X = (606.0, 826.0)       # right-hand column (tables)


def make_views(ds):
    v = {}
    v["front"] = ds.add_view(mkview("front", "yz_aft", -1, -1, FR_O, 1.0,
                                    "front elevation of the PILOT yoke looking forward: (u, h), u outboard = sheet left"))
    v["side"] = ds.add_view(mkview("side", "xz", 1, -1, SD_O, 1.0, "side elevation from outboard (port for the pilot "
                                                                    "yoke), nose left: (a, h)"))
    v["top"] = ds.add_view(mkview("top", "xy", -1, 1, TP_O, 1.0, "from above, forward up: (u, a), u outboard = left"))
    return v


def draw(ds):
    v = make_views(ds)
    ds.frame_and_title(fields=dict(date="2026-10-05"))
    ctx = context()
    draw_front(ds, v["front"])
    front_annotations(ds, v["front"])
    draw_side(ds, v["side"])
    draw_top(ds, v["top"])
    draw_sections(ds)
    draw_details(ds)
    draw_column_detail(ds)
    draw_tables(ds, ctx)
    ds.log.append(f"knee / roll (rev I): {ctx['summary']}")


# python3 -m drawing.yoke_overlay (refs/cache/overlays/yoke/deviations.json, 2026-10-05): photo, landmark residual
# (mean, max) mm, traced-edge deviations (P1046408 only: the front measurement's traces)
PHOTO_CHECK = (
    ("P1046408 pilot (panel_408)", (2.0, 4.0), "shell 1.8, insert 1.0, badge 1.1, rim 1.8, grips 4.1, slot 4.2; "
                                               "neck out 2.4 / in 14 *, inboard pad 6.6 *"),
    ("P1046408 co-pilot (panel_408)", (2.1, 4.2), "shell 2.4, insert 1.6, badge 2.0, rim 1.7, grips 3.2, slot 4.1; "
                                                  "neck out 2.5 / in 14 *, inboard pad 6.2 *"),
    ("Mexico press photo, pilot", (2.1, 4.7), "landmarks only (roll 10° in this photo)"),
    ("Mexico press photo, co-pilot", (2.1, 4.3), "landmarks only (roll 7°)"),
    ("AOPA / Pilatus press, pilot", (2.1, 3.5), "landmarks only (seen from aft-outboard)"),
    ("P1046410 pilot", (1.6, 2.7), "landmarks only"),
)
PHOTO_NOTE = ("* traced 'as seen' from inboard: features off the trace's 4.3° plane shift toward the camera (the inboard "
              "neck and the 28° toed inboard pad); the drawing follows the 3-D fit")

REV_H_KNEES = dict(p95m=(37.6, -18.9, 17.5, 5.0, -10.6, -1.0), p50m=(50.4, -13.1, 25.0, 10.0, 5.2, 0.0),
                   p5m=(50.6, -21.0, 22.5, 10.0, 20.5, 7.5), p5f=(76.1, 4.9, 87.5, 27.5, 55.0, 25.0))
# L6B rev H (2026-10-05, the rev H outline): legs to the yoke wings level / full roll sweep (mm), roll to contact /
# keeping 25 (deg), full rudder wings level (mm), full rudder roll to contact (deg)


def context():
    r = I.crew_checks(-1)
    occ = r["occ"]
    rows = {}
    for k in ("p95m", "p50m", "p5m", "p5f"):
        o = occ[k]
        rows[k] = (1000 * float(o["yoke_pitch"]), 1000 * float(o["yoke_sweep"]), float(o["roll_contact"]),
                   float(o["roll_clear"]), 1000 * float(o["rud_pitch"]), float(o["rud_roll_contact"]))
    o = rows["p95m"]
    return dict(knees=rows, summary=f"95th wings level {o[0]:.1f} mm, contact from {o[2]:.1f} deg, keeping 25 mm to "
                                    f"{o[3]:.1f} deg; full rudder {o[4]:.1f} mm")


# ============================================================================================ front elevation
def draw_front(ds, v):
    F = I.yoke_front_mm()
    mir = np.array([-1.0, 1.0])
    # black body (with its hidden parts: covered by the shell / grips drawn after it)
    poly(ds, v, F["body"], W_OBJ, fill=BLACK)
    for g, S_, G_, pad in (("out", F["grip_out"], F["aft_out"], F["pad_out"]),
                           ("in", F["grip_in"], F["aft_in"], F["pad_in"])):
        poly(ds, v, S_, W_OBJ, fill=BLACK)
        poly(ds, v, G_, W_THIN, color="#8D969C")                         # aft-face edge (R 5, tangent edge)
        poly(ds, v, pad, W_FINE, fill=LEATHER, color="#1E2326")
    # the grip heads: the trim facet (crease) and the switches
    poly(ds, v, F["facet"], W_CREASE, color="#B9C0C5")
    draw_trim_front(ds, v)
    draw_button_front(ds, v)
    # white cover, inserts, badge
    poly(ds, v, F["shell"], W_OBJ, fill=WHITE)
    poly(ds, v, F["insert_upper"], W_CREASE, fill=SILVER)
    poly(ds, v, F["insert_lower"], W_CREASE, fill=SMOKE)
    line(ds, v, F["step"], W_FINE)
    poly(ds, v, F["badge"], W_THIN)
    poly(ds, v, F["badge_border"], W_THIN)
    for L in F["badge_lines"]:
        line(ds, v, L, W_THIN)
    # TCS, AFCS
    draw_tcs(ds, v)
    draw_afcs(ds, v)


def draw_tcs(ds, v, k=1.0):
    u, h, od, bd = (float(x) for x in D["tcs"][:4])
    c = np.array([u, h])
    circ(ds, v, c, od, W_FINE, fill="#1E2326")                          # gloss black bezel
    circ(ds, v, c, 2 * 8.7, W_THIN, color="#7E878D")                     # rim / dish edge
    circ(ds, v, c, 2 * 4.8, W_THIN, color="#7E878D")                     # clearance ring
    circ(ds, v, c, bd, W_THIN, fill="#2B3135", color="#9AA3A9")         # recessed domed button
    for T in ticks(c, 6.1, 8.3, 70, 110, 3):
        line(ds, v, T, 0.25 * k, color="#E8EAEC")


def draw_afcs(ds, v, k=1.0):
    u, h, cd, ch, bd = (float(x) for x in D["afcs"][:5])
    c = np.array([u, h])
    ring = np.vstack([circle(c, 0.5 * bd, 40, 25, 205), circle(c, 5.0, 40, 205, 25)])
    poly(ds, v, ring, W_THIN, fill="#1E2326")                            # legend half-ring boss (upper-inboard)
    for T in ticks(c, 6.0, 8.0, 32, 198, 9):
        line(ds, v, T, 0.22 * k, color="#E8EAEC")
    circ(ds, v, c, cd, W_FINE, fill=RED)


def draw_trim_front(ds, v):
    tr = D["trim"]
    od = float(tr[2])
    ring = facet_map(circle((0.0, 0.0), 0.5 * od, 72))
    poly(ds, v, ring, W_FINE, fill="#23292D", color="#AEB6BB")
    for c0, a0, a1 in (((0, 0), 48, 132), ((0, 0), 228, 312)):         # legend ticks on the fore / aft lunes
        for T in ticks(np.array(c0, float), 10.0, 13.0, a0, a1, 7):
            line(ds, v, facet_map(T), 0.2, color="#E8EAEC")
    for half in rocker_plan():                                           # rocker across the head (along the facet's u)
        poly(ds, v, facet_map(half), W_THIN, fill="#3E464B", color="#C9CFD3")


def draw_button_front(ds, v):
    b = D["button"]
    col = btn_map(circle((0.0, 0.0), 0.5 * float(b[2]), 60)) * [-1, 1]
    cap = btn_map(circle((0.0, 0.0), 0.5 * float(b[3]), 48)) * [-1, 1]
    poly(ds, v, col, W_THIN, fill="#23292D", color="#AEB6BB")
    poly(ds, v, cap, W_THIN, fill="#3A4247", color="#C9CFD3")
    for T in ticks(np.zeros(2), 6.3, 8.3, 70, 210, 6):
        line(ds, v, btn_map(T * [-1, 1]) * [-1, 1], 0.2, color="#E8EAEC")


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


ITEMS = (  # item, part, material (render/lookdev name), finish [source]
    (1, "WHITE COVER (Y SHELL)", "yoke_white", "gloss clear-coat white, neutral-cool (0.77 / 0.78 / 0.80), fine "
                                               "pearl; R 1 edges [M]"),
    (2, "UPPER INSERT = CROWN, BADGE", "yoke_silver (new)", "satin aluminium 0.62, metallic 0.85, rough 0.30; badge "
                                                            "grooves 0.5 [M]"),
    (3, "LOWER INSERT", "yoke_silver_dark (new)", "smoke silver 0.30, metallic 0.85, rough 0.34; 0.47 x item 2 [M]"),
    (4, "BLACK BODY (RIM, NECKS)", "grip_black", "satin black, rough 0.42 (was 0.62): crisp edge highlights [M]"),
    (5, "GRIP (2), HEADS", "grip_black", "satin black, R 5 aft / R 11 forward edges [M / E]"),
    (6, "LEATHER PAD (2)", "leather_black", "charcoal 0.05, rough 0.58, 1.1 pebble grain, ~1 creases, bead [M]"),
    (7, "TCS BUTTON", "gloss_black / black", "gloss black bezel <= 1 proud, satin button recessed [M]"),
    (8, "AFCS DISCONNECT", "button_red (new) / black", "red 0.70 / 0.035 / 0.04, clear coat 0.3, NOT emissive [M]"),
    (9, "PITCH TRIM SWITCH", "black / legend_white", "satin black ring + rocker, tick legends white 0.80 [M]"),
    (10, "PUSH BUTTON (INBOARD HEAD)", "black", "satin black dished collar, smooth cap, centre dimple [M]"),
    (11, "COLUMN", "metal_dark", "satin dark metal, dia 44 [E] (never seen)"),
    (12, "COLUMN SURROUND (PANEL)", "pedestal_gunmetal", "satin dark grey moulding, J band 23 wide [M]"),
)


def front_annotations(ds, v):
    """Centre lines, section planes, detail circles, dimensions and item balloons of the front elevation."""
    X0, Y0 = v.pt(0.0, 0.0)
    ds.cv.line((X0, Y0 - 106.0), (X0, Y0 + 72.0), W_THIN, CHAIN)
    ds.cv.line((X0 - 150.0, Y0), (X0 + 150.0, Y0), W_THIN, CHAIN)
    for d in (1, -1):                                                    # grip axes
        (ub, hb), (ut, ht) = D["grip_axis"]
        t0, t1 = -0.07, 1.07
        line(ds, v, [(d * (ub + t0 * (ut - ub)), hb + t0 * (ht - hb)), (d * (ub + t1 * (ut - ub)), hb + t1 * (ht - hb))],
             W_THIN, CHAIN, color=MUTED)
    lbl(ds, X0 + 1.2, Y0 - 104.5, "CL YOKE  BL -375 (CO-PILOT +375)", TXT_S, color=MUTED)
    lbl(ds, X0 - 151.0, Y0 - 1.8, "COLUMN AXIS h 0", TXT_S, "end", color=MUTED)
    lbl(ds, X0 - 151.0, Y0 + 1.8, "(ROLL PIVOT) WL 1845", TXT_S, "end", color=MUTED)
    # ---- dimensions
    dim(ds, v.pt(72.3, 51.5), v.pt(-72.3, 51.5), Y0 - 74.0, "144.6 ARM TIPS")
    dim(ds, v.pt(141.6, -25.0), v.pt(-141.6, -25.0), Y0 + 77.0, "283 GRIPS OVERALL (BOTTOMS)")
    dim(ds, v.pt(21.1, -50.0), v.pt(-21.1, -50.0), Y0 + 68.0, "42.2 STEM @ h -50")
    dim(ds, v.pt(127.5, 95.4), v.pt(91.0, 95.4), Y0 - 101.0, "36.6 HEAD")
    hx = X0 + 150.0                                                      # height ladder right of the inboard grip
    for h, t, u in ((95.4, "95.4", -127.5), (67.0, "67.0", 0.0), (-42.3, "-42.3", -122.5), (-56.0, "-56.0", 0.0),
                    (-61.8, "-61.8", 0.0)):
        X, Y = v.pt(u, h)
        ds.cv.line((X + (25.0 if u == 0 else 1.0), Y), (hx + 1.0, Y), W_THIN, color=MUTED)
        lbl(ds, hx + 2.0, Y + (1.3 if h == -61.8 else (-1.0 if h == -56.0 else 0.0)), t, TXT_S, font="mono")
    ds.cv.line((hx, v.pt(0, 95.4)[1]), (hx, v.pt(0, -61.8)[1]), W_THIN)
    for h in (95.4, 67.0, -42.3, -56.0, -61.8):
        ds.cv.circle(hx, v.pt(0, h)[1], 0.45, w=0.0, fill=INK, stroke=False)
    lbl(ds, hx + 2.0, Y0, "0", TXT_S, font="mono")
    # ---- item balloons
    B = [((-30.0, 25.0), (X0 + 70.0, Y0 + 52.0), 1), ((10.0, 40.0), (X0 + 26.0, Y0 - 86.0), 2),
         ((-4.0, -10.0), (X0 + 18.0, Y0 + 56.0), 3), ((-28.0, -40.0), (X0 + 48.0, Y0 + 60.0), 4),
         ((-75.0, 72.0), (X0 + 62.0, Y0 - 98.0), 4), ((-138.0, 30.0), (X0 + 158.0, Y0 - 40.0), 5),
         ((-115.0, 0.0), (X0 + 158.0, Y0 - 20.0), 6), ((58.5, 51.4), (X0 - 66.0, Y0 - 86.0), 7),
         ((60.6, 23.4), (X0 - 150.0, Y0 + 20.0), 8), ((109.5, 81.5), (X0 - 150.0, Y0 - 98.0), 9),
         ((-106.5, 79.5), (X0 + 158.0, Y0 - 86.0), 10), ((0.0, 0.0), (X0 + 108.0, Y0 + 56.0), 11),
         ((125.0, -20.0), (X0 - 150.0, Y0 + 40.0), 6), ((90.0, -10.0), (X0 - 150.0, Y0 + 60.0), 5)]
    for P, T, n in B:
        balloon(ds, v.pt(*P), T, n)
    poly(ds, v, circle((0.0, 0.0), 22.0, 60), W_THIN, dash=HID, color=MUTED)    # the column behind (hidden)
    # ---- detail circles and section planes
    for c, r, let, at in (((58.5, 51.4), 12.5, "D", (-1, -1)), ((60.6, 23.4), 11.5, "E", (-1, 1)),
                          ((-106.5, 79.5), 11.5, "G", (1, -1)), ((0.0, 49.7), 25.0, "H", (1, -1))):
        X, Y = v.pt(*c)
        ds.cv.path(P_(v, circle(c, r, 60)), W_THIN, (3.0, 1.0), closed=True)
        u_ = np.array(at, float) / math.hypot(*at)
        lbl(ds, X + (r * abs(v.A[0, 0]) + 2.6) * u_[0], Y + (r + 2.6) * u_[1], let, 4.0, "middle", weight=700)
    (ub, hb), (ut, ht) = D["grip_axis"]
    ax = np.array([ut - ub, ht - hb]) / math.hypot(ut - ub, ht - hb)
    nrm = np.array([ax[1], -ax[0]])
    cA = np.array([float(I.yoke_grip_axis_u(14.0)), 14.0])
    M.cutting_plane(ds, v, tuple(cA - 31.0 * nrm), tuple(cA + 31.0 * nrm), "A", look=(ax[0], ax[1]), ext=1.5,
                    length=6.0)
    M.cutting_plane(ds, v, (146.0, 48.0), (-146.0, 48.0), "B", look=(0.0, 1.0), ext=1.5, length=6.0)
    M.cutting_plane(ds, v, (109.5, 108.0), (109.5, 55.0), "C", look=(1.0, 0.0), ext=1.0, length=5.5)
    view_title(ds, X0, Y0 + 91.0, "FRONT ELEVATION - PILOT YOKE",
               "LOOKING FORWARD, AS THE PILOT SEES IT (CO-PILOT YOKE = MIRROR IMAGE) - SCALE 1:1")


# ============================================================================================ side elevation
def x_ref():
    hub = I.yoke_hub(-1)
    return float(hub[0] + I.YOKE["hub_whd"][2])


def a_panel(h):
    """a (mm) of the lower-panel face at the yoke (BL 375) at height h."""
    from model import flightdeck as FD
    hub = I.yoke_hub(-1)
    return np.array([(FD.face_x(float(hub[1]), float(hub[2]) + hh * 1e-3) - x_ref()) * 1000.0
                     for hh in np.atleast_1d(h)])


def break_line(ds, v, p0, p1, amp=1.6, n=4):
    """Short zig-zag break line between model points p0, p1 of view v."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    t = np.linspace(0, 1, 2 * n + 1)
    d = p1 - p0
    nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
    off = amp * np.array([0 if i in (0, 2 * n) else (1 if i % 2 else -1) for i in range(2 * n + 1)])
    line(ds, v, p0 + t[:, None] * d + off[:, None] * nrm, W_THIN)


def draw_side(ds, v):
    X0, Y0 = v.pt(0.0, 0.0)
    r = 1000.0 * float(I.YOKE["column_r"])
    a_brk = -float(D["body_depth"]) - 16.0
    poly(ds, v, [(a_brk, r), (-float(D["body_depth"]), r), (-float(D["body_depth"]), -r), (a_brk, -r)], W_FINE,
         fill="#D9DCDF")
    break_line(ds, v, (a_brk, r + 3), (a_brk, -r - 3))
    lbl(ds, *v.pt(a_brk - 2.0, r + 8.0), "11 TO THE PANEL: DETAIL J", TXT_S, "end", color=MUTED)
    body = side_outline(body_samples())
    poly(ds, v, body, W_OBJ, fill="#555C61")
    cov = side_outline(cover_samples())
    poly(ds, v, cov, W_FINE, fill=WHITE)
    hh = np.linspace(-56.0, 67.0, 80)
    line(ds, v, np.c_[I.yoke_face_a(hh), hh], W_OBJ)
    gs = grip_samples("out")
    gpoly = side_outline(gs)
    poly(ds, v, gpoly, W_OBJ, fill=BLACK)
    # the pad side of the outboard grip (aft face, 4 in from its outer edge) and the trim facet + rocker
    G = I.yoke_grip_faces("out")["G"]
    hs2 = np.linspace(-31.0, 60.0, 30)
    uo = np.array([G[np.abs(G[:, 1] - h) < 1.2, 0].max() for h in hs2])
    line(ds, v, np.c_[I.yoke_grip_aft_a(uo - 4.0, hs2, "out"), hs2], W_FINE, color="#9AA3A9")
    hf = I.yoke_head_facet()
    s_ = 0.5 * hf["size"]
    f = np.array([hf["c"] - s_ * hf["ev"], hf["c"] + s_ * hf["ev"]])
    line(ds, v, f[:, [0, 2]], W_OBJ, color="#9AA3A9")
    rk = [hf["c"] + p_ * hf["ev"] + q_ * hf["n"] for p_, q_ in ((-4.0, 0.0), (-4.0, 6.5), (4.0, 6.5), (4.0, 0.0))]
    poly(ds, v, np.array(rk)[:, [0, 2]], W_FINE, fill="#5B6368")
    # construction: the aft-face plane above the step and the grip rake
    T = math.tan(math.radians(D["face_tilt"]))
    line(ds, v, [(0.0, 2.1), (-(104.0 - 2.1) * T, 104.0)], W_THIN, CHAIN, color=ACCENT)
    line(ds, v, [(0.0, -72.0), (0.0, 104.0)], W_THIN, CHAIN, color=MUTED)
    ds.cv.line(v.pt(a_brk - 4.0, 0.0), v.pt(30.0, 0.0), W_THIN, CHAIN)
    h0, a0 = D["grip_a0"]
    R = math.tan(math.radians(D["grip_rake"]))
    line(ds, v, [(a0 + (h0 + 64.0) * R, -64.0), (a0 - (104.0 - h0) * R, 104.0)], W_THIN, CHAIN, color=ACCENT)
    X, Y = v.pt(-(104.0 - 2.1) * T, 104.0)
    lbl(ds, X + 1.0, Y - 1.6, f"AFT FACE {D['face_tilt']:.1f}° TOP FWD", TXT_S, color=ACCENT, weight=600)
    X, Y = v.pt(a0 + (h0 + 64.0) * R, -64.0)
    lbl(ds, X + 1.2, Y + 1.6, f"GRIP RAKE {D['grip_rake']:.0f}°", TXT_S, color=ACCENT, weight=600)
    lbl(ds, X0 + 1.0, Y0 + 70.0, "a 0", TXT_S, color=MUTED)
    # dimensions (a)
    yb = Y0 + 80.0
    dim(ds, v.pt(-float(D["body_depth"]), -45.0), v.pt(0.0, -45.0), yb, f"{D['body_depth']:.0f} [E]")
    a_max = float(gpoly[:, 0].max())
    h_amax = float(gpoly[np.argmax(gpoly[:, 0]), 1])
    dim(ds, v.pt(0.0, -30.0), v.pt(a_max, h_amax), yb, f"{a_max:.0f}", outside=True)
    a_cr = float(I.yoke_face_a(67.0))
    dim(ds, v.pt(a_cr, 67.0), v.pt(0.0, 2.1), Y0 - 101.0, f"{-a_cr:.1f}", outside=True)
    a_hf = float(gpoly[:, 0].min())
    dim(ds, v.pt(a_hf, 80.0), v.pt(0.0, 2.1), Y0 - 108.0, f"{-a_hf:.0f}", outside=True)
    leader(ds, v.pt(float(hf["c"][0]) + 2.0, float(hf["c"][2]) + 4.0), (X0 + 22.0, Y0 - 92.0),
           "TRIM FACET 38° ABOVE AFT", ["ring flush, rocker 6.5 proud"], size=TXT_S)
    leader(ds, v.pt(3.5, -22.0), (X0 + 22.0, Y0 + 40.0), "CONVEX LOWER FACE", ["+4.6 at h -30"], size=TXT_S)
    leader(ds, v.pt(-55.0, 20.0), (X0 - 70.0, Y0 - 64.0), "BODY FWD FACE, TOP", ["R 14 FOOT [E]: hidden"],
           size=TXT_S)
    view_title(ds, X0 - 22.0, Y0 + 91.0, "SIDE ELEVATION", "FROM OUTBOARD, NOSE LEFT, NEUTRAL PITCH; a 0 = X 3700 "
                                                           "- 1:1")


# ============================================================================================ view from above
def draw_top(ds, v):
    X0, Y0 = v.pt(0.0, 0.0)
    r = 1000.0 * float(I.YOKE["column_r"])
    a_brk = -float(D["body_depth"]) - 20.0
    poly(ds, v, [(r, -float(D["body_depth"])), (r, a_brk), (-r, a_brk), (-r, -float(D["body_depth"]))], W_FINE,
         fill="#D9DCDF")
    break_line(ds, v, (-r - 3, a_brk), (r + 3, a_brk))
    poly(ds, v, plan_outline(body_samples()), W_OBJ, fill="#555C61")
    poly(ds, v, plan_outline(cover_samples()), W_FINE, fill=WHITE)
    for g, sg in (("out", 1.0), ("in", -1.0)):
        S_ = grip_samples(g)
        poly(ds, v, plan_outline(S_, sg), W_OBJ, fill=BLACK)
        G = I.yoke_grip_faces(g)["G"]
        sel = np.abs(G[:, 1] - 14.0) < 1.0
        uu = np.array([G[sel, 0].min(), G[sel, 0].max()])
        aa = I.yoke_grip_aft_a(uu, 14.0, g)
        line(ds, v, np.c_[sg * uu, aa], W_FINE, color="#C9CFD3")
        ang = float(D["grip_toe"][0 if g == "out" else 1])
        X, Y = v.pt(sg * uu.mean(), float(aa.mean()))
        lbl(ds, X, Y + 9.0, f"PAD @ h 14, TOE-OUT {ang:.0f}°", TXT_S, "middle", color=ACCENT, weight=600)
    hf = I.yoke_head_facet()
    s_ = 0.5 * hf["size"]
    from cad import sdf2d
    sq = sdf2d.rrect_outline(0.0, 0.0, s_, s_, 4.0, n_corner=6)
    Q = hf["c"][None, :] + sq[:, :1] * hf["eu"][None, :] + sq[:, 1:2] * hf["ev"][None, :]
    poly(ds, v, np.c_[Q[:, 1], Q[:, 0]], W_FINE, fill="#4A5257", color="#B9C0C5")
    ds.cv.line((X0, Y0 - 92.0), (X0, Y0 + 30.0), W_THIN, CHAIN)
    ds.cv.line((X0 - 150.0, Y0), (X0 + 150.0, Y0), W_THIN, CHAIN, color=MUTED)
    lbl(ds, X0 + 151.0, Y0 - 1.6, "a 0", TXT_S, color=MUTED)
    lbl(ds, X0 + 2.0, Y0 - 90.0, "FWD", TXT_S, color=MUTED, weight=600)
    lbl(ds, X0 - 150.0, Y0 - 56.0, "OUTBOARD", TXT_S, color=MUTED, weight=600)
    lbl(ds, X0 + 150.0, Y0 - 56.0, "INBOARD", TXT_S, "end", color=MUTED, weight=600)
    view_title(ds, X0, Y0 + 40.0, "VIEW FROM ABOVE", "FORWARD UP, PILOT YOKE - SCALE 1:1")


# ============================================================================================ sections
def hatch_poly(ds, v, P, ang=45.0, step=1.0, fill=PAPER, w=W_OBJ):
    S_ = v(np.asarray(P, float))
    ds.cv.path([tuple(q) for q in S_], 0.0, closed=True, fill=fill, stroke=False)
    hatch(ds, S_, ang, step)
    ds.cv.path([tuple(q) for q in S_], w, closed=True)


def rrect2(x0, x1, y0, y1, r0, r1, n=8):
    """Rectangle x0..x1, y0..y1 with corner radii r0 at y1 (top) and r1 at y0 (bottom)."""
    pts = []
    for (cx, cy, rr, a0) in ((x1 - r0, y1 - r0, r0, 0), (x0 + r0, y1 - r0, r0, 90), (x0 + r1, y0 + r1, r1, 180),
                             (x1 - r1, y0 + r1, r1, 270)):
        for t in np.linspace(0, 90, n):
            a = math.radians(a0 + t)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return np.array(pts)


def draw_sections(ds):
    # ---- A-A: mid-grip section normal to the axis (2:1): x across (outboard to the sheet LEFT), d aft (+, down)
    w, dep, ra, rf = (float(x) for x in D["grip_section"])
    vA = ds.add_view(mkview("sec_A", "yz", -1, 1, (447.0, 300.0), 2.0, "section A-A, (across, d) mm: aft face at "
                                                                         "d 0, forward up"))
    sec = rrect2(-0.5 * w, 0.5 * w, -dep, 0.0, ra, rf)                   # aft face at d 0 (bottom), forward = -d (up)
    hatch_poly(ds, vA, sec)
    pad_w = w - 2 * float(D["pad"][2])
    xs = np.linspace(-0.5 * pad_w, 0.5 * pad_w, 21)
    crown = float(D["pad"][5])
    pad = np.vstack([np.c_[xs, crown * (1 - (xs / (0.5 * pad_w)) ** 2) + 0.4], [(0.5 * pad_w, 0.0), (-0.5 * pad_w,
                                                                                                    0.0)]])
    poly(ds, vA, pad, W_FINE, fill=LEATHER)
    X0, Y0 = vA.pt(0, 0)
    dim(ds, vA.pt(0.5 * w, -dep), vA.pt(-0.5 * w, -dep), Y0 - 2 * dep - 6.0, f"{w:.0f}")
    dim(ds, vA.pt(-0.5 * w, 0.0), vA.pt(-0.5 * w, -dep), X0 + w + 6.0, f"{dep:.0f}", orient="v")
    dim(ds, vA.pt(0.5 * pad_w, 2.0), vA.pt(-0.5 * pad_w, 2.0), Y0 + 9.0, f"PAD {pad_w:.0f}")
    lbl(ds, X0 + w + 1.5, Y0 + 1.5, f"R {ra:.0f}", TXT_S)
    lbl(ds, X0 + w + 1.5, Y0 - 2 * dep - 1.0, f"R {rf:.0f} [E]", TXT_S)
    lbl(ds, X0 - w - 2.0, Y0 - 2 * dep + 3.0, "FWD", TXT_S, "end", color=MUTED, weight=600)
    lbl(ds, X0 - w - 2.0, Y0 - 2.0, "AFT (PAD)", TXT_S, "end", color=MUTED, weight=600)
    lbl(ds, X0, Y0 + 14.5, f"crown {crown:.1f}, rim 1 [E]; outboard <- -> inboard", TXT_S, "middle")
    view_title(ds, X0, Y0 + 23.0, "SECTION A-A", "MID-PAD, NORMAL TO THE GRIP AXIS - 2:1", size=3.4)
    # ---- C-C: the trim head at u 109.5, (a, h) (2:1)
    vC = ds.add_view(mkview("sec_C", "xz", 1, -1, (566.0, 292.0), 2.0, "section C-C, (a, h) mm about the trim centre"))
    hf = I.yoke_head_facet()
    c = hf["c"]
    S_ = grip_samples("out")
    sel = np.abs(S_[:, 0] - c[1]) < 0.6
    cut = side_outline(S_[sel])
    cut = cut[cut[:, 1] > 58.0]
    cut = np.vstack([cut, [(cut[-1, 0], 58.0), (cut[0, 0], 58.0)]]) if len(cut) else cut
    rel = cut - [c[0], c[2]]
    hatch_poly(ds, vC, rel)
    ev2 = np.array([hf["ev"][0], hf["ev"][2]])
    n2 = np.array([hf["n"][0], hf["n"][2]])
    ring = np.array([-0.5 * float(D["trim"][2]) * ev2, 0.5 * float(D["trim"][2]) * ev2])
    line(ds, vC, ring, 0.6, color=INK)
    rk = np.array([p_ * ev2 + q_ * n2 for p_, q_ in ((-2.0, 0.0), (-2.0, 3.5), (2.0, 3.5), (2.0, 0.0))])
    poly(ds, vC, rk, W_FINE, fill="#5B6368")
    X0, Y0 = vC.pt(0, 0)
    for t, sgn, T in (("DN LUNE (FWD)", 1.0, (X0 - 30.0, Y0 - 44.0)), ("UP LUNE (AFT)", -1.0, (X0 + 30.0, Y0 + 14.0))):
        p = sgn * 9.0 * ev2
        leader(ds, vC.pt(*p), T, t, size=TXT_S, weight=500)
    nn = n2 / np.linalg.norm(n2)
    ds.cv.line((X0, Y0), (X0 + 24.0 * nn[0], Y0 - 24.0 * nn[1]), W_THIN, CHAIN, color=ACCENT)
    lbl(ds, X0 + 25.0 * nn[0] - 8.0, Y0 - 25.0 * nn[1] - 3.0, "NORMAL 38° ABOVE AFT", TXT_S, color=ACCENT, weight=600)
    lbl(ds, X0 + 25.0 * nn[0] - 8.0, Y0 - 25.0 * nn[1] + 0.5, "10° TOWARD THE CL", TXT_S, color=ACCENT)
    view_title(ds, X0 - 10.0, Y0 + 54.0, "SECTION C-C", "TRIM HEAD AT u 109.5 - 2:1", size=3.4)
    # ---- B-B: horizontal at h 48 through the badge and the TCS, outboard half + the grip (1:1), from above
    vB = ds.add_view(mkview("sec_B", "xy", -1, 1, (176.0, 448.0), 1.0, "section B-B, (u, a) mm from above"))
    hB = 48.0
    aF = float(I.yoke_face_a(hB))
    cov = float(D["cover_t"])
    F = I.yoke_front_mm()
    sh = F["shell"]
    u_tip = 72.3
    u_ins = float(np.interp(hB, *np.array(D["insert_side"])[::-1, ::-1].T))
    Gb = I.yoke_grip_faces("out")["G"]
    body_u1 = float(Gb[np.abs(Gb[:, 1] - hB) < 0.8, 0].min()) + float(I.yoke_grip_shift("out")[0][0]) + 2.0
    a_fr = float(body_front_a(np.array([hB]))[0])
    hatch_poly(ds, vB, [(-8.0, aF - cov), (body_u1, aF - cov), (body_u1, a_fr + 6.0), (body_u1 - 6.0, a_fr),
                        (-8.0, a_fr)], ang=45.0, step=1.4, fill="#E3E6E8")
    hatch_poly(ds, vB, [(-8.0, aF), (u_tip, aF), (u_tip, aF - cov), (-8.0, aF - cov)], ang=-45.0, step=0.8)
    line(ds, vB, [(u_ins, aF + 1.5), (u_ins, aF - 4.5)], W_THIN, color=ACCENT)
    lbl(ds, *vB.pt(u_ins, aF + 6.0), "INSERT JOINT", TXT_S, "middle", color=ACCENT)
    tcs = D["tcs"]
    tb = np.array([(tcs[0] - 9.6, aF), (tcs[0] - 9.0, aF + 0.9), (tcs[0] + 9.0, aF + 0.9), (tcs[0] + 9.6, aF)])
    poly(ds, vB, tb, W_FINE, fill="#1E2326", closed=False)
    poly(ds, vB, [(tcs[0] - 4.3, aF + 0.2), (tcs[0] + 4.3, aF + 0.2), (tcs[0] + 4.3, aF - 2.0),
                  (tcs[0] - 4.3, aF - 2.0)], W_FINE, fill="#3A4247")
    G = I.yoke_grip_faces("out")["G"]
    sel = np.abs(G[:, 1] - hB) < 0.8
    u0, u1 = G[sel, 0].min(), G[sel, 0].max()
    v_, da = I.yoke_grip_shift("out")
    a0_, a1_ = I.yoke_grip_aft_a(np.array([u0, u1]), hB, "out")
    gsec = [(u0, a0_), (u1, a1_), (u1 + v_[0], a1_ + da), (u0 + v_[0], a0_ + da)]
    hatch_poly(ds, vB, gsec, ang=45.0, step=1.0)
    X0, Y0 = vB.pt(0, 0)
    ds.cv.line((X0, Y0 - 70.0), (X0, Y0 + 12.0), W_THIN, CHAIN)
    dim(ds, vB.pt(0.0, aF), vB.pt(u_tip, aF), Y0 + 12.0, f"{u_tip:.1f}")
    lbl(ds, *vB.pt(tcs[0], aF + 8.0), "TCS <= 1 PROUD", TXT_S, "middle")
    lbl(ds, *vB.pt(40.0, a_fr - 4.0), "BODY [E]", TXT_S, "middle", color=MUTED)
    lbl(ds, *vB.pt(110.0, a1_ + 9.0), "GRIP 27 DEEP, TOE 13°", TXT_S, "middle")
    lbl(ds, *vB.pt(-9.0, aF), f"FACE a {aF:.1f}", TXT_S, "start")
    leader(ds, vB.pt(20.0, aF - 1.5), (vB.pt(20.0, aF)[0] - 14.0, vB.pt(0, aF)[1] + 12.0), f"COVER {cov:.0f} [E]",
           size=TXT_S, weight=500)
    view_title(ds, X0 - 55.0, Y0 + 26.0, "SECTION B-B", f"h {hB:.0f} (BADGE / TCS), OUTBOARD HALF (THE INBOARD "
               "HALF MIRRORS IT WITHOUT THE TCS) - 1:1", size=3.4)


# ============================================================================================ details
def detail_title(ds, X, Y, t, sub):
    view_title(ds, X, Y, t, sub, size=3.2)


def draw_details(ds):
    # ---- D: TCS (3:1), front + profile
    u, h, od, bd, proud = (float(x) for x in D["tcs"][:5])
    vD = ds.add_view(mkview("det_D", "yz_aft", -1, -1, (58.0, 527.0), 3.0, "detail D (TCS), mm about its centre"))
    c = np.zeros(2)
    circ(ds, vD, c, od, W_OBJ, fill="#1E2326")
    circ(ds, vD, c, 2 * 8.7, W_THIN, color="#9AA3A9")
    circ(ds, vD, c, 2 * 4.8, W_THIN, color="#9AA3A9")
    circ(ds, vD, c, bd, W_FINE, fill="#3A4247", color="#C9CFD3")
    for T in ticks(c, 6.1, 8.3, 70, 110, 3):
        line(ds, vD, T, 0.35, color="#E8EAEC")
    centre_mark(ds, vD, c, 0.5 * od)
    X0, Y0 = vD.pt(0, 0)
    dim(ds, vD.pt(-0.5 * od, 0), vD.pt(0.5 * od, 0), Y0 + 0.5 * od * 3 + 5.0, f"{od:.1f} BEZEL")
    leader(ds, vD.pt(1.5, -2.0), (X0 + 34.0, Y0 + 26.0), f"BUTTON {bd:.1f}", ["recessed, domed"], size=TXT_S)
    leader(ds, vD.pt(-6.6, 0.0), (X0 + 34.0, Y0 + 8.0), "DISH r 4.8-8.7", ["0.5 gap ring"], size=TXT_S)
    leader(ds, vD.pt(0.0, 7.2), (X0 + 34.0, Y0 - 22.0), "3 TICKS 70-110°", ["r 7.2 (no lettering)"], size=TXT_S)
    detail_title(ds, X0, Y0 + 45.0, "DETAIL D - TCS", f"ON THE WHITE ARM, u {u:.1f} h {h:.1f}, <= {proud:.0f} PROUD - 3:1")
    # ---- E: AFCS disconnect (3:1)
    u, h, cd, ch, bdo = (float(x) for x in D["afcs"][:5])
    vE = ds.add_view(mkview("det_E", "yz_aft", -1, -1, (150.0, 527.0), 3.0, "detail E (AFCS DISC), mm"))
    ring = np.vstack([circle(c, 0.5 * bdo, 40, 25, 205), circle(c, 5.0, 40, 205, 25)])
    line(ds, vE, [(-14.0, -6.0), (-6.0, -2.5), (0.0, -1.0), (8.0, -2.0), (14.0, -5.0)], W_FINE, HID, color=MUTED)
    poly(ds, vE, ring, W_FINE, fill="#1E2326")
    for T in ticks(c, 6.0, 8.0, 32, 198, 9):
        line(ds, vE, T, 0.35, color="#E8EAEC")
    circ(ds, vE, c, cd, W_OBJ, fill=RED)
    centre_mark(ds, vE, c, 0.5 * bdo)
    X0, Y0 = vE.pt(0, 0)
    dim(ds, vE.pt(-0.5 * cd, 0), vE.pt(0.5 * cd, 0), Y0 + 25.0, f"{cd:.1f} CAP")
    leader(ds, vE.pt(-7.0, 4.5), (X0 + 32.0, Y0 - 22.0), f"HALF-RING OD {bdo:.1f}", ["25-205°, 9 ticks, +1"],
           size=TXT_S)
    leader(ds, vE.pt(10.0, -3.4), (X0 + 32.0, Y0 + 12.0), "BODY LOWER EDGE", ["cap overhangs the slot"], size=TXT_S)
    detail_title(ds, X0, Y0 + 45.0, "DETAIL E - AFCS DISC", f"u {u:.1f} h {h:.1f}; CAP {cd:.1f} x {ch:.1f} HIGH - 3:1")
    # ---- G: inboard push button (3:1) + profile
    b = D["button"]
    vG = ds.add_view(mkview("det_G", "yz_aft", -1, -1, (240.0, 527.0), 3.0, "detail G (push button), mm"))
    circ(ds, vG, c, float(b[2]), W_OBJ, fill="#23292D")
    circ(ds, vG, c, float(b[2]) - 2.6, W_THIN, color="#9AA3A9")
    circ(ds, vG, c, float(b[3]), W_FINE, fill="#3A4247", color="#C9CFD3")
    circ(ds, vG, c, float(b[5]), W_THIN, color="#C9CFD3")
    for T in ticks(c, 6.3, 8.3, 70 + 180, 210 + 180, 6):
        line(ds, vG, T * [1, 1], 0.35, color="#E8EAEC")
    centre_mark(ds, vG, c, 0.5 * float(b[2]))
    X0, Y0 = vG.pt(0, 0)
    dim(ds, vG.pt(-0.5 * float(b[2]), 0), vG.pt(0.5 * float(b[2]), 0), Y0 + 0.5 * float(b[2]) * 3 + 5.0,
        f"{float(b[2]):.1f} COLLAR")
    leader(ds, vG.pt(2.5, 3.0), (X0 + 30.0, Y0 - 22.0), f"CAP {float(b[3]):.1f}, {float(b[4]):.0f} PROUD",
           ["smooth, R 1, dimple 2"], size=TXT_S)
    leader(ds, vG.pt(-7.0, -2.0), (X0 + 30.0, Y0 + 14.0), "6 TICKS 70-210°", ["on the inboard arc"], size=TXT_S)
    detail_title(ds, X0, Y0 + 45.0, "DETAIL G - PUSH BUTTON", "INBOARD HEAD (NOT A 4-WAY HAT) - 3:1")
    # ---- F: pitch-trim switch on the head facet (2:1), plan on the facet + rocker profile
    tr = D["trim"]
    vF = ds.add_view(mkview("det_F", "yz_aft", -1, -1, (462.0, 410.0), 2.0, "detail F (trim), facet plane mm"))
    hf = I.yoke_head_facet()
    s_ = 0.5 * hf["size"]
    from cad import sdf2d
    poly(ds, vF, sdf2d.rrect_outline(0.0, 0.0, s_, s_, 4.0, n_corner=6), W_OBJ, fill="#5B6368")
    od = float(tr[2])
    circ(ds, vF, c, od, W_FINE, fill="#23292D", color="#C9CFD3")
    lune = 7.3
    for sg in (-1, 1):                                                   # the slot between the lunes (+-7.4)
        line(ds, vF, [(-0.5 * od + 2.0, sg * (0.5 * od - lune)), (0.5 * od - 2.0, sg * (0.5 * od - lune))], W_THIN,
             color="#9AA3A9")
    for a0, a1 in ((48, 132), (228, 312)):
        for T in ticks(c, 10.0, 13.0, a0, a1, 7):
            line(ds, vF, T, 0.3, color="#E8EAEC")
    for half in rocker_plan():
        poly(ds, vF, half, W_FINE, fill="#3E464B", color="#C9CFD3")
    centre_mark(ds, vF, c, s_)
    X0, Y0 = vF.pt(0, 0)
    dim(ds, vF.pt(-0.5 * od, -s_), vF.pt(0.5 * od, -s_), Y0 + s_ * 2 + 6.0, f"{od:.1f} RING")
    dim(ds, vF.pt(-s_, s_), vF.pt(s_, s_), Y0 - s_ * 2 - 5.0, f"{2 * s_:.0f} FACET")
    leader(ds, vF.pt(0.0, 10.5), (X0 - 46.0, Y0 - 30.0), "DN LUNE (FWD)", ["7 ticks / 84°"], size=TXT_S)
    leader(ds, vF.pt(0.0, -10.5), (X0 - 46.0, Y0 + 22.0), "UP LUNE (AFT)", ["7 ticks / 84°"], size=TXT_S)
    leader(ds, vF.pt(-11.0, 3.0), (X0 + 44.0, Y0 - 30.0), f"ROCKER {float(tr[3]):.0f} x {float(tr[4]):.0f}",
           [f"waist {float(tr[5]):.0f}, split {float(tr[6]):.1f}"], size=TXT_S)
    lbl(ds, X0, Y0 - s_ * 2 - 11.0, "OUTBOARD <-   ACROSS THE HEAD   -> INBOARD", TXT_S, "middle", color=MUTED)
    # rocker profile (saddle), along its length
    vR = ds.add_view(mkview("det_F2", "xz", 1, -1, (462.0, 470.0), 2.0, "detail F rocker profile, mm"))
    L = float(tr[3])
    xs = np.linspace(-0.5 * L, 0.5 * L, 41)
    he, hm = float(tr[7]), float(tr[8])
    prof = hm + (he - hm) * (np.abs(xs) / (0.5 * L)) ** 1.6
    split = float(tr[6])
    for sg in (-1, 1):
        sel = sg * xs >= 0.5 * split
        P = np.vstack([[(sg * 0.5 * split, 0.0)], np.c_[xs[sel], prof[sel]][::sg], [(sg * 0.5 * L, 0.0)]])
        poly(ds, vR, P, W_FINE, fill="#3E464B")
    line(ds, vR, [(-0.5 * od, 0.0), (0.5 * od, 0.0)], W_OBJ)
    X1, Y1 = vR.pt(0, 0)
    dim(ds, vR.pt(0.5 * L, he), vR.pt(0.5 * L, 0.0), X1 + L + 7.0, f"{he:.1f}", orient="v")
    dim(ds, vR.pt(0.0, hm), vR.pt(0.0, 0.0), X1 - L - 9.0, f"{hm:.1f}", orient="v", outside=True)
    lbl(ds, X1, Y1 + 4.5, "ROCKER SADDLE [E +/-2], RING FLUSH", TXT_S, "middle")
    detail_title(ds, X0, Y1 + 13.0, "DETAIL F - PITCH TRIM", "ON THE OUTBOARD HEAD'S FACET (38° UP) - 2:1")
    # ---- H: badge (3:1): abstract winged plate, NO letters
    vH = ds.add_view(mkview("det_H", "yz_aft", -1, -1, (360.0, 527.0), 3.0, "detail H (badge), mm about h 49.65"))
    F = I.yoke_front_mm()
    hc = 49.65
    sub = np.array([0.0, hc])
    poly(ds, vH, F["badge"] - sub, W_OBJ, fill=SILVER)
    poly(ds, vH, F["badge_border"] - sub, W_FINE)
    for Ln in F["badge_lines"]:
        line(ds, vH, Ln - sub, W_FINE)
    poly(ds, vH, F["badge_field"] - sub, W_THIN, dash=(1.0, 0.8), color=MUTED)
    X0, Y0 = vH.pt(0, 0)
    (bu0, bh0), (bu1, bh1) = D["badge"]
    dim(ds, vH.pt(bu0, bh0 - hc), vH.pt(-bu0, bh0 - hc), Y0 - 16.0, f"{2 * bu0:.1f}")
    dim(ds, vH.pt(bu1, bh1 - hc), vH.pt(-bu1, bh1 - hc), Y0 + 16.0, f"{2 * bu1:.1f}")
    dim(ds, vH.pt(-bu0, bh0 - hc), vH.pt(-bu1, bh1 - hc), X0 + 76.0, f"{bh0 - bh1:.1f}", orient="v", outside=True)
    lbl(ds, X0, Y0 + 24.0, "PLAIN FIELD (NO LETTERING); 3 SPEED-LINE GROOVES EACH WING, PITCH 1.3", TXT_S, "middle")
    detail_title(ds, X0, Y0 + 34.0, "DETAIL H - BADGE", f"ABSTRACT WINGED PLATE, TOP AT h {bh0:.1f} - 3:1")


# ============================================================================================ column detail
def draw_column_detail(ds):
    """DETAIL J (1:2): the column and the lower panel, side view from outboard: panel face, the measured surround
    points, the column [E], the yoke at neutral and (phantom) at full push / pull."""
    vJ = ds.add_view(mkview("det_J", "xz", 1, -1, (706.0, 306.0), 0.5, "detail J, (a, h) mm"))
    hs = np.linspace(-95.0, 80.0, 30)
    ap = a_panel(hs)
    poly(ds, vJ, np.vstack([np.c_[ap, hs], [(ap[-1] - 30.0, hs[-1]), (ap[0] - 30.0, hs[0])]]), W_FINE, fill="#E7E9EB")
    a_p0 = float(a_panel(0.0)[0])
    r = 1000.0 * float(I.YOKE["column_r"])
    poly(ds, vJ, [(a_p0 - 25.0, r), (-float(D["body_depth"]), r), (-float(D["body_depth"]), -r), (a_p0 - 25.0, -r)],
         W_FINE, fill="#D9DCDF")
    t0, t1 = (1000.0 * float(x) for x in I.YOKE["travel"])
    body = side_outline(body_samples())
    grip = side_outline(grip_samples("out"))
    for dx, dash in ((t0, PHANTOM), (0.0, None)):
        poly(ds, vJ, body + [dx, 0.0], W_FINE if dash is None else W_THIN, dash=dash,
             fill="#555C61" if dash is None else None, color=None if dash is None else MUTED)
        poly(ds, vJ, grip + [dx, 0.0], W_FINE if dash is None else W_THIN, dash=dash,
             fill=BLACK if dash is None else None, color=None if dash is None else MUTED)
    for h_ in (12.0, -24.0, -44.0):
        X, Y = vJ.pt(float(a_panel(h_)[0]), h_)
        ds.cv.line((X - 1.8, Y), (X + 1.8, Y), 0.35, color=ACCENT)
    X0, Y0 = vJ.pt(0, 0)
    gap = -float(D["body_depth"]) + t0 - a_p0
    Xp, _ = vJ.pt(a_p0, 0)
    leader(ds, vJ.pt(a_p0, 12.0), (X0 + 16.0, Y0 - 52.0), "SURROUND (12) [M]: J BAND 23 WIDE",
           ["inboard of CL: top h +12, joint -24, screw -44;", "NO BELLOWS; depth / fixed or moving: OPEN"],
           size=TXT_S, color=ACCENT)
    leader(ds, vJ.pt(-120.0, -r), (X0 + 16.0, Y0 + 12.0), "COLUMN (11) DIA 44 [E], HIDDEN",
           ["axis h 0 = WL 1845 (kept)"], size=TXT_S)
    dim(ds, vJ.pt(a_p0, -r), vJ.pt(-float(D["body_depth"]), -r), Y0 + 20.0, f"{-float(D['body_depth']) - a_p0:.0f}")
    lbl(ds, X0 + 16.0, Y0 + 28.0, f"PHANTOM: FULL PUSH {t0:+.0f} [E] (pull +{t1:.0f})", TXT_S)
    lbl(ds, X0 + 16.0, Y0 + 31.2, f"leaves {gap:.0f} to the panel face", TXT_S)
    detail_title(ds, X0 - 40.0, Y0 + 58.0, "DETAIL J - COLUMN", "AT THE LOWER PANEL, FROM OUTBOARD - 1:2")


# ============================================================================================ tables, notes
def wrap_rows(rows, widths, size):
    from drawing import sheet as S_
    out = []
    for r in rows:
        cells = [S_.wrap(str(c), w - 2.4, size) for c, w in zip(r, widths)]
        n = max(len(c) for c in cells)
        for k in range(n):
            out.append(tuple(c[k] if k < len(c) else "" for c in cells))
    return out


def draw_tables(ds, ctx):
    x0, x1 = COL_X
    W = x1 - x0
    size = 2.1
    cols = [("#", 7.0, "c"), ("PART", 46.0, "l"), ("MATERIAL", 40.0, "l"), ("FINISH / COLOUR [SOURCE]", W - 93.0, "l")]
    rows = wrap_rows([(str(n), p, m, f) for n, p, m, f in ITEMS], [c[1] for c in cols], size)
    y = table(ds, x0, 15.0, cols, rows, title="ITEMS & FINISHES (render/lookdev names; 'new' = to add)", size=size,
              row_h=3.3, font="label")
    dims_ = [
        ("shell (white cover) height / about h 0", "123 / -56..+67", "[M] P1046408 panel_408, both yokes"),
        ("arm tips / stem at h 0 / at h -50", "144.6 / 65.6 / 42.2", "[M] sigma 1.5"),
        ("insert crown above the arm junctions", "13.3 (67.0 / 53.7)", "[M] parting grooves"),
        ("step line / lower insert bottom", "h 2.1 (2 V) / -18.9", "[M]"),
        ("black rim at h 10 / 0 / -50 / foot", "13.0 / 10.1 / 4.5 / 5.8", "[M] outboard true edge"),
        ("hand-slot top", "h 24 +/-3", "[M] both sides averaged"),
        ("aft face above the step", f"{D['face_tilt']:.1f}° top fwd", "[M] bundle adj., +/-4"),
        ("body depth / cover", f"{D['body_depth']:.0f} / {D['cover_t']:.0f}", "[E] hidden in every photo"),
        ("grips overall / bottoms / head tops", "283 / -42.3 / 95.4", "[M] (rev H 285 / -40 / 118)"),
        ("grip length / cant (tops inboard)", "137.7 / 15-17°", "[M] (rev H 160 / 10°)"),
        ("section A-A / rake / toe-out out, in", "42 x 27 / 20° / 13°, 28°", "[M] +/-4 / +/-5 / +/-8"),
        ("pad: top / bottom / frame", "h 61 / -32.5 / 4", "[M] P1046408, AOPA"),
        ("TCS centre / bezel / button", f"({D['tcs'][0]:.1f}, {D['tcs'][1]:.1f}) / 19.2 / 8.6", "[M]"),
        ("AFCS cap centre / dia x high", f"({D['afcs'][0]:.1f}, {D['afcs'][1]:.1f}) / 9.8 x 5.5", "[M]"),
        ("trim centre / ring / rocker", f"({D['trim'][0]:.1f}, {D['trim'][1]:.1f}) / 29.5 / 27 x 8", "[M]"),
        ("push button centre / collar / cap", f"({D['button'][0]:.1f}, {D['button'][1]:.1f}) / 17.3 / 10.2",
         "[M] (inboard head: -u)"),
        ("column dia / axis", "44 [E] / h 0 = WL 1845", "kept; surround reads 1821"),
        ("pitch travel / roll", "+/-90 [E] / +/-70 [E]", "unchanged (YOKE)"),
    ]
    cols2 = [("DIMENSION (mm, YOKE-LOCAL)", 74.0, "l"), ("VALUE", 50.0, "l"), ("SOURCE", W - 124.0, "l")]
    rows2 = wrap_rows(dims_, [c[1] for c in cols2], size)
    y = table(ds, x0, y + 3.0, cols2, rows2, title="MAIN DIMENSIONS", size=size, row_h=3.3, font="label")
    K = ctx["knees"]
    nm = dict(p95m="95th male", p50m="50th male", p5m="5th male", p5f="5th female")
    rows3 = []
    for k in ("p95m", "p50m", "p5m", "p5f"):
        h_, i_ = REV_H_KNEES[k], K[k]
        rows3.append((nm[k], f"{h_[0]:.0f} > {i_[0]:.0f}", f"{h_[1]:.0f} > {i_[1]:.0f}",
                      f"{h_[2]:.1f} > {i_[2]:.1f}", f"{h_[3]:.1f} > {i_[3]:.1f}", f"{h_[4]:.0f} > {i_[4]:.0f}"))
    cols3 = [("OCCUPANT", 26.0, "l"), ("LEVEL mm", 34.0, "c"), ("ROLL+/-70 mm", 36.0, "c"),
             ("CONTACT deg", 40.0, "c"), ("KEEP 25 deg", 40.0, "c"), ("RUDDER mm", W - 176.0, "c")]
    y = table(ds, x0, y + 3.0, cols3, rows3, title="KNEES vs YOKE (L6B), REV H > REV I - CRITERIA UNCHANGED",
              size=size, row_h=3.3, font="label")
    o95 = K["p95m"]
    nts = [
        "Yoke-local mm: u outboard (pilot: -y), h up from the hub centre = the column axis / roll pivot (WL 1845, "
        "BL -/+375), a aft of the aft face at the insert step (X 3700 at neutral pitch).  Drawn from "
        "model/interior.py YOKE_DESIGN rev I; L6 / L6B take the same outline (yoke_outline_yz, yoke_sweep_pieces).",
        "Symmetric moulding except the switches: TCS, AFCS DISC and the trim on the OUTBOARD side, the push button "
        "on the inboard head; the co-pilot yoke is the mirror image.",
        "Sources: P1046408 through the fitted camera panel_408; P1046409 / 10, the Mexico and AOPA press photos, "
        "the JTF p.18 elevation; a bundle adjustment of 4 photos for depth.  All photos look from inboard: the "
        "outboard and the mirrored inboard traces are averaged; the drawn yoke, projected through the cameras, sits "
        "on the photos within 0.3-4.7 mm at the landmarks (overlays, refs/cache).",
        "NO MARKINGS: the badge is an abstract winged plate, every legend a row of ticks.",
        "Not modelled / unsupported: the rev H column bellows (none in 8 photos), a PTT trigger (none seen), the "
        "PC-24's extra button and grip tab.",
        f"Knee checks on the rev I outline: the 95th clears the yoke by {o95[0]:.0f} mm wings level (criterion 25: "
        f"passes); roll to contact {o95[2]:.1f}°, keeping 25 mm to {o95[3]:.1f}° (rev H 5.0°) -- owner decision "
        "(open point 1 of L6B; criteria not loosened).",
    ]
    y = notes(ds, x0, y + 2.0, x1, nts, title="NOTES", size=size, line_h=2.9)
    opn = [
        "Absolute fore-aft station: the locked photos put the aft face 60 +/-30 forward of the drawn neutral "
        "(hub_dx kept: the gust-lock pose?).",
        "Column: the surround's joint line reads WL 1821 +/-10 (25 under the pivot, kept); fixed J surround on the "
        "panel vs a curved arm moving with the yoke; push travel 90 [E] leaves 17 to the panel.",
        "Toe-out 13 / 28 measured per grip (+/-8): symmetric 20 / 20 would suit a symmetric moulding but left the "
        "outboard pad too narrow in P1046410.",
        "Hidden: body depth 60, top and foot radius, grip forward corners R 11, rocker / cap heights (+/-2).",
        "PTT: none on the PRO in any photo; the PC-24 has a grip tab.",
    ]
    y = notes(ds, x0, y + 1.0, x1, opn, title="OPEN POINTS FOR THE OWNER", size=size, line_h=2.9)
    ds.log.append(f"right column (tables) ends at y {y:.1f}")
    rows4 = [(ph, f"{lm[0]:.1f} / {lm[1]:.1f}", tr) for ph, lm, tr in PHOTO_CHECK]
    cols4 = [("PHOTO (CAMERA)", 70.0, "l"), ("LANDMARKS mean / max", 44.0, "c"),
             ("TRACED EDGES mean (mm)", W - 114.0, "l")]
    y4 = table(ds, x0, 383.0, cols4, wrap_rows(rows4, [c[1] for c in cols4], size),
               title="PHOTO CHECK: THE DRAWN YOKE THROUGH THE PHOTO CAMERAS (mm)", size=size, row_h=3.3, font="label")
    from drawing import sheet as S_
    for k, t in enumerate(S_.wrap("Only the yoke's photo pose (pitch, roll, a few mm of shift) is fitted per photo, to "
                                  "the landmark picks (TCS, AFCS cap, trim ring, button, badge, step ends, lower insert, "
                                  "foot); overlays in refs/cache/overlays/yoke (private). " + PHOTO_NOTE, W, TXT_S)):
        lbl(ds, x0, y4 + 3.0 + 2.8 * k, t, TXT_S, color=MUTED)
    from drawing.interior_sheet import revisions_block
    import drawing.interior_sheet as IS
    saved = IS.SHEET
    IS.SHEET = SHEET
    try:
        revisions_block(ds, x0, 470.0, x1, size=2.1, title_size=2.4, rows=REVISIONS)
    finally:
        IS.SHEET = saved
