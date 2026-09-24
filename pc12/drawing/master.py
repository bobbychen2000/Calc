"""
drawing.master -- shared toolkit and registry for the Stage-2 drawing set.

Every sheet of the set is drawn FROM THE PARAMETERS (the control lines / outline tables / planform
parameters the 3-D builder uses -- never from the mesh) and is written twice:

    CLEAN    out/drawings/<id>.svg  <id>.pdf  <id>.png           ours only (tracked in git)
    OVERLAY  refs/cache/overlays/<id>_overlay.pdf  _overlay.png   ours + the registered Pilatus drawing in red
                                                                  + photo-derived marks (git-ignored: the public
                                                                  repo never contains Pilatus geometry)

    python3 -m drawing.master               build every registered sheet
    python3 -m drawing.master L1 G1         only these sheet ids
    python3 -m drawing.master --list        list the registered sheets
    options: --clean-only (skip the overlay variant), --dpi N (PNG preview resolution, default 110)

Writing a sheet module (drawing/<name>.py):

    SHEET = dict(id="L1", title="LINES PLAN", size="A1", scale="1:20 / 1:10", order=10)

    def draw(ds):                       # ds: master.DrawingSheet
        v = ds.add_view(side_view("profile", origin=(40, 140), scale=20))
        ds.frame_and_title()            # A1/A2 frame, zones, title block (id, title, scale, rev, date ...)
        ds.cv.path(v.pts(P), W_OBJ)     # our lines -> clean AND overlay variants
        ds.ov_mbp(v, "side", clip=...)  # Pilatus lines in red -> overlay variant only
        callout(ds, v, (x, z), "Δ +12")  # deviation call-out (our numbers; fine on the clean sheet)

The module is picked up automatically: master scans drawing/*.py for a top-level line starting with
'SHEET = dict(' (no import needed to list it); REGISTRY below can also name modules explicitly.

Views carry an explicit affine model->sheet transform (sheet_mm = A @ (a, b) + t, (a, b) = the view's
natural model coordinates: side (x, z) seen from port, plan (x, y) seen from above with +y (starboard) up,
front (y, z) seen from ahead with +y on the viewer's LEFT, aft (y, z) seen from behind).  The transforms of
every view are written next to the clean outputs (<id>.views.json) so photo/drawing overlays can be mapped
onto the sheet.  Conventions: first-angle projection (plan below the side view, front view to its right),
mm, station grid at the Pilatus frames labelled with STA, WL and BL grids.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from drawing import sheet as S  # noqa: E402
from drawing.canvas import Canvas, text_width  # noqa: E402

OUT_CLEAN = ROOT / "out" / "drawings"
OUT_OVERLAY = ROOT / "refs" / "cache" / "overlays"

INK, PAPER = S.INK, S.PAPER
W_OBJ, W_FINE, W_DIM = S.W_OBJ, S.W_FINE, S.W_DIM          # 0.35 / 0.18 / 0.13 mm
W_THIN, W_GRID = 0.13, 0.09
W_FRAME, W_TABLE, W_TABLE_IN = S.W_FRAME, S.W_TABLE, S.W_TABLE_IN
CHAIN, PHANTOM = S.CHAIN, S.PHANTOM
DASH = (2.4, 1.2)
GRID = "#97A3AB"             # grid lines / grid labels
MUTED = "#5D6B73"            # secondary text
RED = "#E0231C"              # Pilatus reference (overlay only)
BLUE = "#1F6FD1"             # photo-derived marks (overlay only)
ACCENT = "#0E6E62"           # deviation / change call-outs (ours)

SIZES = {"A0": (1189.0, 841.0), "A1": (841.0, 594.0), "A2": (594.0, 420.0), "A3": (420.0, 297.0)}
ZONES = {"A0": (24, 16), "A1": (16, 12), "A2": (12, 8), "A3": (8, 6)}
DATE = "2026-09-24"
DRAWN = "Claude - loftkit parametric model"
WARNING = "RECONSTRUCTION FROM PUBLISHED DATA - NOT FOR CONSTRUCTION"
OVERLAY_BANNER = ("OVERLAY - RED: PILATUS DRAWING 190.10.40.432 (NGX MODEL BUILDING PLAN), REGISTERED TO MODEL "
                  "COORDINATES - PRIVATE REFERENCE, NOT FOR PUBLICATION")

REGISTRY = {}                # sheet id -> module name (explicit entries; discovery adds the rest)


# ================================================================================================ views
@dataclass
class View:
    """Explicit affine map of one view: sheet_mm = A @ (a, b) + t."""
    name: str
    axes: str                              # 'xz' side, 'xy' plan, 'yz' front / section, 'yz_aft'
    A: np.ndarray
    t: np.ndarray
    scale: float                           # drawing scale denominator (1:scale)
    box: tuple | None = None               # model clip box (a0, b0, a1, b1) for overlays / grids
    note: str = ""

    def __call__(self, P):
        P = np.atleast_2d(np.asarray(P, float))
        return P @ self.A.T + self.t

    def pt(self, a, b):
        q = self.A @ np.array([a, b], float) + self.t
        return float(q[0]), float(q[1])

    def pts(self, P):
        return [tuple(q) for q in self(P)]

    def inv(self, XY):
        return (np.atleast_2d(np.asarray(XY, float)) - self.t) @ np.linalg.inv(self.A).T

    @property
    def k(self):
        """sheet mm per model metre."""
        return 1000.0 / self.scale

    def to_dict(self):
        return dict(name=self.name, axes=self.axes, A=self.A.tolist(), t=self.t.tolist(), scale=self.scale,
                    box=list(self.box) if self.box else None, note=self.note,
                    formula="sheet_mm = A @ (a, b) + t; (a, b) = " +
                            {"xz": "(x, z)", "xy": "(x, y)", "yz": "(y, z)", "yz_aft": "(y, z)"}[self.axes])


def _mk(name, axes, sx, sy, origin, model_origin, scale, box, note):
    k = 1000.0 / scale
    A = np.array([[sx * k, 0.0], [0.0, sy * k]])
    t = np.asarray(origin, float) - A @ np.asarray(model_origin, float)
    return View(name, axes, A, t, float(scale), box, note)


def side_view(name, origin, scale, model_origin=(0.0, 0.0), box=None):
    """Side view seen from PORT, nose left: (x, z) -> sheet; origin = sheet mm of model_origin."""
    return _mk(name, "xz", 1, -1, origin, model_origin, scale, box, "seen from port, nose left")


def plan_view(name, origin, scale, model_origin=(0.0, 0.0), box=None):
    """Plan seen from ABOVE, nose left, starboard (+y) up."""
    return _mk(name, "xy", 1, -1, origin, model_origin, scale, box, "seen from above, starboard up")


def front_view(name, origin, scale, model_origin=(0.0, 0.0), box=None):
    """Front view seen from AHEAD: starboard (+y) on the viewer's LEFT."""
    return _mk(name, "yz", -1, -1, origin, model_origin, scale, box, "seen from ahead, starboard left")


def aft_view(name, origin, scale, model_origin=(0.0, 0.0), box=None):
    """View seen from BEHIND: starboard (+y) on the viewer's RIGHT."""
    return _mk(name, "yz_aft", 1, -1, origin, model_origin, scale, box, "seen from aft, starboard right")


# ================================================================================================ sheet
class DrawingSheet:
    """One sheet: the clean canvas (ours), the overlay-only canvas (Pilatus + photo marks), views."""

    def __init__(self, sheet_id, title, size="A1", scale="1:20", rev="A", subtitle=None, sheet_no="1 OF 1",
                 dwg=None):
        W, H = SIZES[size]
        self.id, self.title, self.size, self.scale_txt, self.rev = sheet_id, title, size, scale, rev
        self.subtitle = subtitle or title
        self.sheet_no, self.dwg = sheet_no, dwg or f"PC12-{sheet_id}"
        self.sh = S.Sheet()
        self.sh.cv = Canvas(W, H, PAPER, INK)
        self.ov = Canvas(W, H, PAPER, INK)          # overlay-only items (drawn on top of the clean content)
        self.W, self.H = W, H
        self.frame = (20.0, 10.0, W - 10.0, H - 10.0)   # ISO 5457: 20 mm filing margin left, 10 elsewhere
        self.views = {}
        self.log = []                                  # messages for the build report
        self.title_box = None

    @property
    def cv(self):
        return self.sh.cv

    def text(self, *a, **kw):
        return self.sh.text(*a, **kw)

    def add_view(self, v: View):
        self.views[v.name] = v
        return v

    # ---- frame and title block
    def frame_and_title(self, tb_width=None, fields=None):
        ncol, nrow = ZONES[self.size]
        S.draw_frame(self.sh, self.frame, ncol=ncol, nrow=nrow)
        FX0, FY0, FX1, FY1 = self.frame
        w = tb_width or (250.0 if self.size in ("A0", "A1") else 190.0)
        x0, y1 = FX1 - 6.0 - w, FY1 - 6.0
        y0 = y1 - 71.0
        f = dict(title="PILATUS PC-12 PRO", subtitle=self.subtitle.upper(), dwg=self.dwg, rev=self.rev,
                 scale=self.scale_txt, sheet=f"{self.size} · {self.sheet_no}", units="mm", drawn=DRAWN, date=DATE,
                 warning=WARNING)
        f.update(fields or {})
        S.draw_title_block(self.sh, x0, y0, FX1 - 6.0, y1, fields=f)
        self.title_box = (x0, y0, FX1 - 6.0, y1)
        return self.title_box

    # ---- overlay-only drawing (Pilatus reference in red, photo marks)
    def ov_path(self, pts, w=0.16, color=RED, dash=None, closed=False):
        self.ov.path(pts, w, dash, closed=closed, color=color)

    def ov_polylines(self, view: View, polylines, color=RED, w=0.16, dash=None, clip=None):
        """Model-coordinate polylines (N, 2) in the view's natural axes -> overlay variant, clipped to
        `clip` (a0, b0, a1, b1) or the view's box."""
        box = clip or view.box
        for P in polylines:
            for seg in clip_polyline(np.asarray(P, float), box):
                if len(seg) >= 2:
                    self.ov.path(view.pts(seg), w, dash, color=color)

    def ov_mbp(self, view: View, key, kinds=("outline", "hidden"), clip=None, color=RED, w=0.16, mapfn=None,
               select=None):
        """Draw the registered Pilatus drawing's polylines of d[key] ('side', 'plan', 'front', ...) in red
        (outline solid, hidden dashed) into the overlay variant.  mapfn(P) may transform the points first
        (e.g. mirror a half-section); select(item) filters items."""
        d = mbp_data()
        n = 0
        for it in d[key]:
            if it["kind"] not in kinds or (select and not select(it)):
                continue
            P = it["pts"] if mapfn is None else mapfn(it["pts"])
            self.ov_polylines(view, [P], color, w, (1.6, 0.9) if it["kind"] == "hidden" else None, clip)
            n += 1
        return n

    def ov_marks(self, view: View, pts, labels=None, color=BLUE, r=0.9, size=2.2):
        """Photo-derived marks (overlay variant): small diamonds with optional labels."""
        for i, p in enumerate(np.atleast_2d(pts)):
            X, Y = view.pt(*p)
            self.ov.polygon([(X - r, Y), (X, Y - r), (X + r, Y), (X, Y + r)], fill=color)
            if labels is not None and labels[i]:
                self.ov.text(X + r + 0.8, Y - r - 0.4, labels[i], size, "label", "start", fill=color)

    def ov_text(self, x, y, s, size=2.6, color=RED, anchor="start", weight=500):
        self.ov.text(x, y, s, size, "label", anchor, weight=weight, fill=color)

    # ---- outputs
    def canvases(self):
        clean = self.cv
        over = Canvas(self.W, self.H, PAPER, INK)
        over.items = list(clean.items) + list(self.ov.items)
        # banner along the top frame edge
        FX0, FY0, FX1, FY1 = self.frame
        over.rect(FX0 + 30.0, FY0 + 1.5, FX1 - FX0 - 60.0, 5.2, lw=0.2, fill="#FFF1F0", stroke=True, color=RED)
        over.text(0.5 * (FX0 + FX1), FY0 + 5.2, OVERLAY_BANNER, 3.0, "label", "middle", weight=600, fill=RED)
        return clean, over

    def write(self, clean_only=False, dpi=110, verbose=True):
        OUT_CLEAN.mkdir(parents=True, exist_ok=True)
        clean, over = self.canvases()
        stem = OUT_CLEAN / self.id
        t_title = f"PC-12 {self.title} ({self.dwg} rev {self.rev})"
        svg = clean.to_svg(title=f"PC-12 {self.title}",
                           desc=f"{self.dwg} rev {self.rev}, {self.scale_txt}, {self.size}. {WARNING}.",
                           font_import="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;"
                                       "700&family=IBM+Plex+Mono:wght@400;500&display=swap")
        stem.with_suffix(".svg").write_text(svg)
        clean.to_pdf(str(stem.with_suffix(".pdf")), title=t_title, author="Claude", subject=WARNING)
        render_png(stem.with_suffix(".pdf"), stem.with_suffix(".png"), dpi)
        (OUT_CLEAN / f"{self.id}.views.json").write_text(json.dumps(
            dict(sheet=self.id, size=self.size, sheet_mm=[self.W, self.H], png_dpi=dpi,
                 png_px_per_mm=dpi / 25.4, views={k: v.to_dict() for k, v in self.views.items()}), indent=1))
        files = [stem.with_suffix(e) for e in (".svg", ".pdf", ".png")]
        if not clean_only:
            OUT_OVERLAY.mkdir(parents=True, exist_ok=True)
            ostem = OUT_OVERLAY / f"{self.id}_overlay"
            over.to_pdf(str(ostem.with_suffix(".pdf")), title=t_title + " OVERLAY", author="Claude",
                        subject="private reference overlay - not for publication")
            render_png(ostem.with_suffix(".pdf"), ostem.with_suffix(".png"), dpi)
            files += [ostem.with_suffix(".pdf"), ostem.with_suffix(".png")]
        if verbose:
            for f in files:
                print(f"  {f.relative_to(ROOT) if ROOT in f.parents else f}  {f.stat().st_size / 1e6:.2f} MB")
        return files

    def check_text_overlaps(self, ignore=("zone",)):
        """Pairs of overlapping text boxes (sheet.Sheet.text records a box per text)."""
        B = [b for b in self.sh.boxes if b[4] not in ignore]
        out = []
        for i in range(len(B)):
            for j in range(i + 1, len(B)):
                a, b = B[i], B[j]
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox > 0.3 and oy > 0.3:
                    out.append((a, b))
        return out


def render_png(pdf, png, dpi=110):
    import pymupdf
    doc = pymupdf.open(str(pdf))
    pix = doc[0].get_pixmap(dpi=dpi)
    pix.save(str(png))
    doc.close()


# ================================================================================================ geometry
def clip_polyline(P, box):
    """Split a polyline (N, 2) at the edges of box (a0, b0, a1, b1); returns the inside pieces."""
    if box is None or len(P) < 2:
        return [P]
    a0, b0, a1, b1 = box
    out, cur = [], []

    def inside(p):
        return a0 <= p[0] <= a1 and b0 <= p[1] <= b1

    def cut(p, q):
        # point where segment p->q crosses the box boundary (p inside, q outside or vice versa)
        ts = []
        d = q - p
        for ax, lo, hi in ((0, a0, a1), (1, b0, b1)):
            if abs(d[ax]) > 1e-15:
                for v in (lo, hi):
                    t = (v - p[ax]) / d[ax]
                    if 0 <= t <= 1:
                        r = p + t * d
                        if a0 - 1e-9 <= r[0] <= a1 + 1e-9 and b0 - 1e-9 <= r[1] <= b1 + 1e-9:
                            ts.append(t)
        return ts

    prev = None
    for p in P:
        if prev is None:
            if inside(p):
                cur = [p]
        else:
            ip, iq = inside(prev), inside(p)
            if ip and iq:
                cur.append(p)
            elif ip and not iq:
                ts = cut(prev, p)
                cur.append(prev + min(ts) * (p - prev) if ts else prev)
                out.append(np.array(cur))
                cur = []
            elif not ip and iq:
                ts = cut(prev, p)
                cur = [prev + max(ts) * (p - prev) if ts else p, p]
            else:
                ts = sorted(cut(prev, p))
                if len(ts) >= 2:
                    out.append(np.array([prev + ts[0] * (p - prev), prev + ts[-1] * (p - prev)]))
        prev = p
    if len(cur) >= 2:
        out.append(np.array(cur))
    return out


# ================================================================================================ grids
def grid_lines(ds, view: View, axis, values, lo, hi, labels=None, where=("start",), size=2.3, color=GRID,
               w=W_GRID, dash=None, gap=1.5, weight=400):
    """Grid lines of a view in model coordinates.  axis='a': lines a = const (b from lo to hi);
    axis='b': lines b = const (a from lo to hi).  labels: list of str (or None); where: 'start' / 'end'
    (the label position at lo / hi end)."""
    cv = ds.cv
    for i, v in enumerate(values):
        if axis == "a":
            p, q = view.pt(v, lo), view.pt(v, hi)
        else:
            p, q = view.pt(lo, v), view.pt(hi, v)
        cv.line(p, q, w, dash, color=color)
        if labels is None or not labels[i]:
            continue
        for wh in where:
            e = np.array(p if wh == "start" else q)
            o = np.array(q if wh == "start" else p)
            u = (e - o) / max(np.linalg.norm(e - o), 1e-9)
            tp = e + gap * u
            if abs(u[0]) > abs(u[1]):          # horizontal line: label beyond its end
                ds.text(tp[0], tp[1], labels[i], size, "mono", "start" if u[0] > 0 else "end", vcenter=True,
                        fill=color, tag="grid", weight=weight)
            else:                              # vertical line: label above / below
                yy = tp[1] - 0.6 if u[1] < 0 else tp[1] + 0.72 * size + 0.4
                ds.text(tp[0], yy, labels[i], size, "mono", "middle", fill=color, tag="grid", weight=weight)


def station_grid(ds, views, frames, lo_hi, label_view=None, label_at="hi", size=2.3, extra=None):
    """Vertical station lines at the frames through the side / plan views (views: list of View; lo_hi:
    matching list of (lo, hi) in the view's second coordinate).  The first view (or label_view) carries a
    two-line label: frame name and STA in mm.  extra: {name: station} drawn chain-dotted, labelled too."""
    label_view = label_view or views[0]
    allf = [(n, x, False) for n, x in frames.items()] + [(n, x, True) for n, x in (extra or {}).items()]
    for v, (lo, hi) in zip(views, lo_hi):
        for name, x, ex in allf:
            p, q = v.pt(x, lo), v.pt(x, hi)
            ds.cv.line(p, q, W_GRID, (5.0, 1.0, 0.8, 1.0) if ex else None, color=GRID)
    lo, hi = lo_hi[views.index(label_view)]
    for name, x, ex in allf:
        X, Y = label_view.pt(x, hi if label_at == "hi" else lo)
        if label_at == "hi":
            ds.text(X, Y - 4.4, name, size, "label", "middle", weight=600, fill=GRID if not ex else MUTED,
                    tag="grid")
            ds.text(X, Y - 1.2, f"{x * 1000:.0f}", size - 0.2, "mono", "middle", fill=GRID if not ex else MUTED,
                    tag="grid")
        else:
            ds.text(X, Y + 3.2, name, size, "label", "middle", weight=600, fill=GRID, tag="grid")
            ds.text(X, Y + 6.2, f"{x * 1000:.0f}", size - 0.2, "mono", "middle", fill=GRID, tag="grid")


def mm(v):
    """Model metres -> integer mm string."""
    return f"{v * 1000:.0f}"


# ================================================================================================ annotation
def callout(ds, view: View, pt, text, offset=(12.0, -10.0), color=ACCENT, size=2.5, lines=None, dot=True):
    """Deviation call-out: dot on the model point, leader, text (one or more lines) in a thin box."""
    X, Y = view.pt(*pt)
    tx, ty = X + offset[0], Y + offset[1]
    L = [text] + list(lines or [])
    wmax = max(text_width(s, size, "label") for s in L)
    h = 1.3 * size * len(L) + 1.2
    right = offset[0] >= 0
    bx0 = tx if right else tx - wmax - 2.4
    by0 = ty - h / 2
    # leader to the nearest box side
    ex = bx0 if right else bx0 + wmax + 2.4
    ds.cv.line((X, Y), (ex, ty), W_THIN, color=color)
    if dot:
        r = 0.55
        ds.cv.polygon([(X + r * math.cos(a), Y + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 13)[:-1]],
                      fill=color)
    ds.cv.rect(bx0, by0, wmax + 2.4, h, lw=W_THIN, fill=PAPER, color=color)
    for i, s in enumerate(L):
        ds.text(bx0 + 1.2, by0 + 0.6 + 1.3 * size * (i + 0.5), s, size, "label", "start", vcenter=True,
                fill=color, weight=600 if i == 0 else 400, tag="callout")


def view_title(ds, x, y, title, sub=None, size=4.2):
    ds.text(x, y, title, size, "label", "middle", weight=700, spacing=0.4, tag="title")
    w = text_width(title, size, "label", 700) + 0.4 * len(title)
    ds.cv.line((x - w / 2, y + 1.3), (x + w / 2, y + 1.3), 0.3)
    if sub:
        ds.text(x, y + 5.0, sub, 2.6, "label", "middle", fill=MUTED, tag="title")


def scale_bar(ds, x0, y0, scale, length_m=2.0, step_m=0.5, label=None):
    """Graphic scale bar: alternating blocks of step_m, numbered in metres."""
    k = 1000.0 / scale
    n = int(round(length_m / step_m))
    for i in range(n):
        ds.cv.rect(x0 + i * step_m * k, y0, step_m * k, 1.8, lw=W_FINE, fill=INK if i % 2 == 0 else PAPER)
    for i in range(n + 1):
        v = i * step_m
        ds.text(x0 + i * step_m * k, y0 + 5.2, f"{v:g}", 2.3, "mono", "middle", tag="scalebar")
    ds.text(x0 + n * step_m * k + 2.5, y0 + 5.2, "m", 2.3, "mono", "start", tag="scalebar")
    ds.text(x0, y0 - 1.8, label or f"SCALE 1:{scale:g}", 2.4, "label", "start", weight=600, tag="scalebar")


def table(ds, x0, y0, cols, rows, title=None, size=2.35, row_h=3.7, head_h=5.2, title_h=6.0, zebra=None,
          font="mono"):
    """Simple ruled table.  cols: [(header, width_mm, align)] (align 'l' | 'r' | 'c'); rows: list of
    tuples of str; zebra: callable(row_index) -> bool for a light fill.  Returns the bottom y."""
    cv = ds.cv
    widths = [c[1] for c in cols]
    xs = np.cumsum([x0] + widths)
    x1 = xs[-1]
    y = y0
    if title:
        cv.rect(x0, y, x1 - x0, title_h, lw=W_TABLE, fill=INK)
        ds.text(x0 + 2.0, y + title_h / 2, title, 3.0, "label", "start", weight=600, fill=PAPER, vcenter=True,
                spacing=0.25, tag="table")
        y += title_h
    for i, (h, w, al) in enumerate(cols):
        ds.text(0.5 * (xs[i] + xs[i + 1]), y + head_h / 2, h, 2.3, "label", "middle", weight=600, vcenter=True,
                tag="table")
    cv.line((x0, y + head_h), (x1, y + head_h), W_TABLE)
    y += head_h
    top = y
    for r_i, r in enumerate(rows):
        if zebra and zebra(r_i):
            cv.rect(x0, y, x1 - x0, row_h, lw=0, fill="#EEF1F2", stroke=False)
        for i, s in enumerate(r):
            al = cols[i][2]
            if al == "r":
                tx, anc = xs[i + 1] - 1.3, "end"
            elif al == "c":
                tx, anc = 0.5 * (xs[i] + xs[i + 1]), "middle"
            else:
                tx, anc = xs[i] + 1.3, "start"
            ds.text(tx, y + row_h / 2, s, size, font, anc, vcenter=True, tag="table")
        y += row_h
    for xx in xs[1:-1]:
        cv.line((xx, top - head_h), (xx, y), W_TABLE_IN)
    cv.rect(x0, y0, x1 - x0, y - y0, lw=W_TABLE)
    return y


def notes(ds, x0, y0, x1, items, title="NOTES", size=2.6, line_h=3.6):
    """Numbered notes block; returns the bottom y."""
    ds.text(x0, y0 + 3.4, title, 3.4, "label", "start", weight=600, spacing=0.3, tag="notes")
    y = y0 + 9.0
    for i, n in enumerate(items):
        lines = S.wrap(n, x1 - x0 - 7.0, size)
        ds.text(x0, y, f"{i + 1}.", size, "label", "start", tag="notes")
        for k, ln in enumerate(lines):
            ds.text(x0 + 5.5, y + line_h * k, ln, size, "label", "start", tag="notes")
        y += line_h * len(lines) + 1.2
    return y


# ================================================================================================ reference
@lru_cache(maxsize=1)
def mbp_data():
    """The registered Pilatus drawing (refs/mbp.py; git-ignored cache).  Overlay variants only."""
    from refs import mbp
    return mbp.load()


# ================================================================================================ registry
def discover():
    """{sheet id: (module name, SHEET dict)} from REGISTRY and drawing/*.py files defining 'SHEET = dict('."""
    found = {}
    for f in sorted((ROOT / "drawing").glob("*.py")):
        src = f.read_text()
        m = re.search(r"^SHEET\s*=\s*(dict\(.*?\))\s*$", src, re.M | re.S)
        if not m:
            continue
        try:
            spec = eval(m.group(1), {"dict": dict})           # literal dict(...) only
        except Exception as e:                                 # noqa: BLE001
            print(f"  (skipping {f.name}: SHEET not a literal dict: {e})")
            continue
        found[spec["id"]] = (f"drawing.{f.stem}", spec)
    for sid, mod in REGISTRY.items():
        if sid not in found:
            found[sid] = (mod, dict(id=sid, title=sid))
    return dict(sorted(found.items(), key=lambda kv: (kv[1][1].get("order", 99), kv[0])))


def build_sheet(sid, mod_name, spec, clean_only=False, dpi=110, verbose=True):
    import importlib
    t0 = time.time()
    mod = importlib.import_module(mod_name)
    ds = DrawingSheet(spec["id"], spec.get("title", spec["id"]), spec.get("size", "A1"), spec.get("scale", "1:20"),
                      spec.get("rev", "A"), spec.get("subtitle"), spec.get("sheet_no", "1 OF 1"), spec.get("dwg"))
    mod.draw(ds)
    if verbose:
        print(f"[{sid}] {ds.title}: drawn in {time.time() - t0:.1f}s")
        for m in ds.log:
            print("  " + m)
        ov = ds.check_text_overlaps()
        if ov:
            print(f"  CHECK: {len(ov)} overlapping text pairs, e.g.")
            for a, b in ov[:8]:
                print(f"    {a[4]} @({a[0]:.0f},{a[1]:.0f}) x {b[4]} @({b[0]:.0f},{b[1]:.0f})")
    files = ds.write(clean_only, dpi, verbose)
    return ds, files


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    reg = discover()
    if "--list" in argv:
        for sid, (mod, spec) in reg.items():
            print(f"{sid:6s} {spec.get('title', ''):32s} {spec.get('size', ''):3s} {spec.get('scale', ''):14s} {mod}")
        return
    dpi = 110
    if "--dpi" in argv:
        dpi = int(argv[argv.index("--dpi") + 1])
    ids = [a for a in argv if not a.startswith("--") and not a.isdigit()]
    clean_only = "--clean-only" in argv
    todo = ids or list(reg)
    for sid in todo:
        if sid not in reg:
            print(f"unknown sheet id {sid!r}; registered: {', '.join(reg)}")
            continue
        mod, spec = reg[sid]
        build_sheet(sid, mod, spec, clean_only, dpi)


if __name__ == "__main__":
    main()
