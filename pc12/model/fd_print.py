"""
Printed legends of the flight deck (first-principles flight deck, part A3; owner 2026-10-19 "Show me some printed
legends!"): the silk-screened / pad-printed markings of the real panels -- switch titles, captions, frames round
switch groups, trim / flap tick scales, dimmer arcs, row dots, chevrons, stitched edge strips -- drawn into ONE RGBA
texture atlas and carried by thin decals that lie ON the panel surface (a copy of the surface patch lifted
`LIFT` 0.1 mm), material 'legend_print' (alpha-blended, base colour = the atlas).  They replace the floating
light_white strips (raised 0.3-0.4 mm boxes with hard edges that shimmered and floated at the crew stops).

Lettering (owner 2026-10-24, "Real English words"; it relaxes the no-lettering rule for the cockpit placards only --
still no logos, brands, registrations or serials): the text is real generic placard English (switch titles, breaker
names, scales, limitation placards; a print's `text`, else words from VOCAB / CB_VOCAB) set in a sans-serif stroke font
of Latin capitals, digits and a little punctuation (_L).  The first build's invented glyph set read as Cyrillic.

Mechanics.  `decal(fr, u0, v0, u1, v1, c, kind, **kw)` returns (Mesh, 'legend_print'): a quad (or a grid laid onto a
curved surface by `surf`) in the frame `fr` at height c (the surface + LIFT), its UVs into a cell of the atlas that
is packed online (a deterministic shelf packer: the build order fixes the layout, the light tier builds the same
atlas) at PX_PER_MM.  `atlas()` draws every registered cell (4x supersampled, box-filtered down) and returns PNG
bytes; model/assemble.TEXTURES maps 'legend_print' -> 'fd_print_atlas'.  Each cell is ONE colour (RGB constant over
the whole cell, the shape in alpha), so mip-mapping never darkens the edges.
"""
from __future__ import annotations

import io
import math
import zlib

import numpy as np

from cad.mesh import Mesh

MAT = "legend_print"
LIFT = 0.00015               # m above the surface the decal sits on (0.15 mm: no z-fight at the 1 cm near plane, above
                              # fit_check 26's 0.1 mm coplanar band)
PX_PER_MM = 8.0               # atlas resolution: 0.125 mm a texel (a 2 mm cap height = 16 texels)
LIFT_MAP = 0.00025            # on a curved map (decal_map): its <= 6 mm cells' chords against the surface's own chords
SIZE = 4096                   # atlas width (px)
SIZE_H = 4096                 # atlas height (px; UVs are normalised: the light tier ships it at half size, atlas(0.5))
PPM = {"frame": 4.0, "vector": 5.0, "cells": 6.0, "stripes": 5.0}   # px / mm of the large, sparse kinds
PAD = 3                       # px between cells (and the cell's transparent border: mips stay inside the cell)
SS = 4                        # supersampling of the drawing
CAP_K = 1.6                   # every pseudo-text's cap height x this (clamped to its box)
WEIGHT = 0.13                 # stroke width / cap height

COLOURS = {                   # sRGB 0-255 of the inks
    "white": (236, 236, 232), "grey": (170, 172, 174), "red": (214, 40, 36), "amber": (232, 156, 30),
    "green": (60, 200, 90), "black": (22, 22, 24), "yellow": (238, 206, 40), "blue": (70, 130, 220),
    "red_dim": (150, 42, 38), "plate_black": (18, 18, 20), "silver": (196, 198, 200),
}

_CELLS = []                   # registered cells: dict(x, y, w, h (px), kind, kw)
_SHELF = {"x": 0, "y": 0, "h": 0}
_KEYS = {}
_SHELVES = []


def reset():
    _CELLS.clear()
    _KEYS.clear()
    _SHELVES.clear()
    _SHELF.update(x=0, y=0, h=0)


def _alloc(w, h):
    """Shelf packing (deterministic, online): the lowest-waste open shelf that takes the cell, else a new shelf."""
    best = None
    for sh in _SHELVES:
        if sh["h"] >= h + PAD and sh["x"] + w + PAD <= SIZE and (best is None or sh["h"] < best["h"]):
            if sh["h"] <= 2 * (h + PAD) or sh["x"] + w + PAD <= SIZE:
                best = sh
    if best is None:
        y = _SHELF["y"]
        if y + h + PAD > SIZE_H:
            raise RuntimeError("fd_print atlas full")
        best = dict(y=y, h=h + PAD, x=0)
        _SHELVES.append(best)
        _SHELF["y"] = y + h + PAD
    x, y = best["x"] + PAD, best["y"] + PAD
    best["x"] += w + PAD
    return x, y


def register(w_m, h_m, kind, **kw):
    """Reserve a cell for a w_m x h_m (m) print; returns its pixel rectangle (x, y, w, h)."""
    ppm = float(kw.pop("ppm", PPM.get(kind, PX_PER_MM)))
    w = max(4, int(math.ceil(w_m * 1000 * ppm)))
    h = max(4, int(math.ceil(h_m * 1000 * ppm)))
    key = (w, h, kind, repr(sorted(kw.items())))
    if key in _KEYS:                 # the same print again (or a second build in one process): one cell
        return _KEYS[key]
    x, y = _alloc(w, h)
    _CELLS.append(dict(x=x, y=y, w=w, h=h, kind=kind, kw=kw, wm=w_m, hm=h_m, ppm=ppm))
    _KEYS[key] = (x, y, w, h)
    return x, y, w, h


def _uv(rect, s, t):
    """Atlas UVs (glTF: origin top left) at fractions s (right) / t (up) of a cell, half a texel inside."""
    x, y, w, h = rect
    return np.stack([(x + 0.5 + s * (w - 1.0)) / SIZE, (y + 0.5 + (1.0 - t) * (h - 1.0)) / SIZE_H], -1)


def decal(fr, u0, v0, u1, v1, c, kind, nu=1, nv=1, surf=None, **kw):
    """A print on the face of frame fr (u right, v up, w out) over [u0, u1] x [v0, v1] at height c.  surf(P) -> (P, n)
    projects grid points onto a curved surface (then lifted LIFT along n); nu x nv grid cells."""
    rect = register(abs(u1 - u0), abs(v1 - v0), kind, **kw)
    s, t = np.meshgrid(np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1), indexing="ij")
    P = fr.p(u0 + s * (u1 - u0), v0 + t * (v1 - v0), np.full(s.shape, c))
    N = np.broadcast_to(fr.w, P.shape).copy()
    if surf is not None:
        P, N = surf(P.reshape(-1, 3))
        P = P + LIFT * N
        P, N = P.reshape(s.shape + (3,)), N.reshape(s.shape + (3,))
    # a left-handed frame (w given against u x v) would show the print mirrored: read it the other way along u
    UV = _uv(rect, 1 - s, t) if float(np.cross(fr.u, fr.v) @ fr.w) < 0 else _uv(rect, s, t)
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, cc, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    F = np.concatenate([np.stack([a, b, cc], -1).reshape(-1, 3), np.stack([a, cc, d], -1).reshape(-1, 3)])
    m = Mesh(P.reshape(-1, 3), F, N.reshape(-1, 3), UV.reshape(-1, 2))
    fn = m.face_normals()
    if np.mean(fn @ fr.w) < 0:
        m = Mesh(m.V, m.F[:, ::-1], m.N, m.UV)
    return m, MAT


def decal_map(M, u0, v0, u1, v1, off, kind, seg=0.006, flip=False, **kw):
    """A print laid on a SurfMap M (model/fd_detail_b.py: arc-length u / v over a curved surface) over u0..u1 x v0..v1,
    `off` + LIFT off it: a grid of <= seg cells following the surface.  The image's right is +u, its up +v (flip:
    the image turned 180 deg, for maps whose u / v run against the reading direction)."""
    rect = register(abs(u1 - u0), abs(v1 - v0), kind, **kw)
    nu = max(1, int(math.ceil(abs(u1 - u0) / seg)))
    nv = max(1, int(math.ceil(abs(v1 - v0) / seg)))
    s, t = np.meshgrid(np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1), indexing="ij")
    P, N = M.frame(u0 + s * (u1 - u0), v0 + t * (v1 - v0))
    P = P + (off + LIFT_MAP) * N
    # the map's (u, v) left-handed about its normal (e.g. a port wall: u aft, v up, n inboard): mirror u so the print
    # reads (its right forward there)
    du = M.frame(min(u0, u1) + 1e-3, 0.5 * (v0 + v1))[0] - M.frame(min(u0, u1), 0.5 * (v0 + v1))[0]
    dv = M.frame(min(u0, u1), 0.5 * (v0 + v1) + 1e-3)[0] - M.frame(min(u0, u1), 0.5 * (v0 + v1))[0]
    lh = float(np.cross(du, dv) @ N.reshape(-1, 3).mean(0)) < 0
    if lh:
        s = 1 - s
    UV = _uv(rect, 1 - s, 1 - t) if flip else _uv(rect, s, t)
    idx = np.arange((nu + 1) * (nv + 1)).reshape(nu + 1, nv + 1)
    a, b, cc, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    F = np.concatenate([np.stack([a, b, cc], -1).reshape(-1, 3), np.stack([a, cc, d], -1).reshape(-1, 3)])
    m = Mesh(P.reshape(-1, 3), F, N.reshape(-1, 3), UV.reshape(-1, 2))
    if np.mean(np.sum(m.face_normals() * N.reshape(-1, 3).mean(0), 1)) < 0:
        m = Mesh(m.V, m.F[:, ::-1], m.N, m.UV)
    return m, MAT


def decal_r(fr, u0, v0, u1, v1, c, kind, **kw):
    """decal() over fr's [u0, u1] x [v0, v1] read with the text's top toward fr's -u (see reading())."""
    return decal(reading(fr), v0, -u1, v1, -u0, c, kind, **kw)


def reading(fr):
    """The frame turned so a print reads with its top toward fr's -u (on a horizontal plate whose u runs aft: the top
    of the text forward, read from the seats) and its right along fr's +v."""
    from model.flightdeck import Fr
    return Fr(fr.o, fr.v, -fr.u, fr.w)


# =====================================================================================================================
# drawing (numpy rasteriser of capsules / arcs / dots into an alpha field)
# =====================================================================================================================
class _Canvas:
    def __init__(self, w, h, ppm=PX_PER_MM):
        self.w, self.h = w * SS, h * SS
        self.a = np.zeros((self.h, self.w), np.float32)
        self.ppm = ppm
        self.k = SS * ppm                             # px per mm on the supersampled canvas

    def _box(self, x0, y0, x1, y1):
        return (max(0, int(x0) - 1), max(0, int(y0) - 1), min(self.w, int(x1) + 2), min(self.h, int(y1) + 2))

    def seg(self, p, q, r):
        """Capsule from p to q (mm, origin bottom left, y up) of radius r mm."""
        k = self.k
        p = np.array([p[0] * k, self.h - p[1] * k])
        q = np.array([q[0] * k, self.h - q[1] * k])
        rr = r * k
        X0, Y0, X1, Y1 = self._box(min(p[0], q[0]) - rr, min(p[1], q[1]) - rr, max(p[0], q[0]) + rr, max(p[1], q[1]) + rr)
        if X1 <= X0 or Y1 <= Y0:
            return
        yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32) + 0.5
        d = q - p
        L2 = max(float(d @ d), 1e-9)
        t = np.clip(((xx - p[0]) * d[0] + (yy - p[1]) * d[1]) / L2, 0, 1)
        dist = np.hypot(xx - p[0] - t * d[0], yy - p[1] - t * d[1])
        self.a[Y0:Y1, X0:X1] = np.maximum(self.a[Y0:Y1, X0:X1], np.clip(rr - dist + 0.5, 0, 1))

    def rect(self, x0, y0, x1, y1):
        k = self.k
        X0, X1 = x0 * k, x1 * k
        Y0, Y1 = self.h - y1 * k, self.h - y0 * k
        a, b, c, d = self._box(X0, Y0, X1, Y1)
        if c <= a or d <= b:
            return
        yy, xx = np.mgrid[b:d, a:c].astype(np.float32) + 0.5
        cov = np.clip(np.minimum(xx - X0, X1 - xx) + 0.5, 0, 1) * np.clip(np.minimum(yy - Y0, Y1 - yy) + 0.5, 0, 1)
        self.a[b:d, a:c] = np.maximum(self.a[b:d, a:c], cov)

    def arc(self, c, R, a0, a1, r, n=None):
        n = n or max(6, int(abs(a1 - a0) / 6))
        A = np.radians(np.linspace(a0, a1, n + 1))
        P = np.c_[c[0] + R * np.cos(A), c[1] + R * np.sin(A)]
        for i in range(n):
            self.seg(P[i], P[i + 1], r)

    def dot(self, c, r):
        self.seg(c, c, r)

    def result(self):
        A = self.a.reshape(self.h // SS, SS, self.w // SS, SS).mean((1, 3))
        return A


# The letter set: plain sans-serif Latin CAPITALS drawn as stroke polylines on a unit cell (x 0..1 = the letter width,
# y 0..1 = the cap height).  (Owner 2026-10-24: the first pseudo-glyphs -- bars, bowls and diagonals of no script --
# "read Russian"; placards on the PRO are English.)  The words are random letter groups (consonant / vowel runs, never a
# dictionary word on purpose), so the printing reads as English placards at a glance and says nothing: the no-lettering
# rule (no logos, registrations, serials or readable text outside the live displays) holds.
def _arc_pts(cx, cy, rx, ry, a0, a1, n=7):
    return [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]


_L = {
    "A": [[(0, 0), (0.5, 1), (1, 0)], [(0.2, 0.36), (0.8, 0.36)]],
    "B": [[(0, 0), (0, 1), (0.62, 1)] + _arc_pts(0.62, 0.76, 0.3, 0.24, 90, -90) + [(0, 0.52)],
          [(0.66, 0.52)] + _arc_pts(0.66, 0.26, 0.32, 0.26, 90, -90) + [(0, 0)]],
    "C": [_arc_pts(0.55, 0.5, 0.48, 0.5, 40, 320, 11)],
    "D": [[(0, 0), (0, 1), (0.45, 1)] + _arc_pts(0.45, 0.5, 0.5, 0.5, 90, -90, 9) + [(0, 0)]],
    "E": [[(0.9, 1), (0, 1), (0, 0), (0.9, 0)], [(0, 0.52), (0.75, 0.52)]],
    "F": [[(0.9, 1), (0, 1), (0, 0)], [(0, 0.52), (0.75, 0.52)]],
    "G": [_arc_pts(0.55, 0.5, 0.48, 0.5, 40, 340, 11) + [(1.0, 0.45), (0.6, 0.45)]],
    "H": [[(0, 0), (0, 1)], [(1, 0), (1, 1)], [(0, 0.52), (1, 0.52)]],
    "I": [[(0.5, 0), (0.5, 1)]],
    "J": [[(0.8, 1), (0.8, 0.3)] + _arc_pts(0.42, 0.3, 0.38, 0.3, 0, -180, 7)],
    "K": [[(0, 0), (0, 1)], [(0.95, 1), (0, 0.38)], [(0.3, 0.6), (1, 0)]],
    "L": [[(0, 1), (0, 0), (0.85, 0)]],
    "M": [[(0, 0), (0, 1), (0.5, 0.35), (1, 1), (1, 0)]],
    "N": [[(0, 0), (0, 1), (1, 0), (1, 1)]],
    "O": [_arc_pts(0.5, 0.5, 0.5, 0.5, 0, 360, 15)],
    "P": [[(0, 0), (0, 1), (0.6, 1)] + _arc_pts(0.6, 0.73, 0.35, 0.27, 90, -90) + [(0, 0.46)]],
    "R": [[(0, 0), (0, 1), (0.6, 1)] + _arc_pts(0.6, 0.73, 0.35, 0.27, 90, -90) + [(0, 0.46)], [(0.45, 0.46), (1, 0)]],
    "S": [_arc_pts(0.5, 0.75, 0.45, 0.25, 15, 270, 8) + _arc_pts(0.5, 0.25, 0.45, 0.25, 90, -165, 8)],
    "T": [[(0, 1), (1, 1)], [(0.5, 1), (0.5, 0)]],
    "U": [[(0, 1), (0, 0.32)] + _arc_pts(0.5, 0.32, 0.5, 0.32, 180, 360, 9) + [(1, 1)]],
    "V": [[(0, 1), (0.5, 0), (1, 1)]],
    "W": [[(0, 1), (0.25, 0), (0.5, 0.65), (0.75, 0), (1, 1)]],
    "X": [[(0, 1), (1, 0)], [(0, 0), (1, 1)]],
    "Y": [[(0, 1), (0.5, 0.48), (1, 1)], [(0.5, 0.48), (0.5, 0)]],
    "Z": [[(0, 1), (1, 1), (0, 0), (1, 0)]],
    "Q": [_arc_pts(0.5, 0.5, 0.5, 0.5, 0, 360, 15), [(0.6, 0.25), (1.0, -0.05)]],
    "0": [_arc_pts(0.5, 0.5, 0.45, 0.5, 0, 360, 15)],
    "1": [[(0.2, 0.8), (0.55, 1), (0.55, 0)]],
    "2": [_arc_pts(0.5, 0.72, 0.42, 0.28, 160, -30, 7) + [(0.05, 0), (0.95, 0)]],
    "3": [_arc_pts(0.5, 0.75, 0.4, 0.25, 160, -90, 7) + _arc_pts(0.5, 0.26, 0.45, 0.26, 90, -160, 7)],
    "4": [[(0.75, 0), (0.75, 1), (0, 0.3), (1, 0.3)]],
    "5": [[(0.9, 1), (0.15, 1), (0.1, 0.55)] + _arc_pts(0.5, 0.32, 0.45, 0.32, 125, -160, 9)],
    "6": [_arc_pts(0.5, 0.3, 0.45, 0.3, 0, 360, 11), [(0.06, 0.32), (0.25, 0.8), (0.75, 1.0)]],
    "7": [[(0, 1), (1, 1), (0.35, 0)]],
    "8": [_arc_pts(0.5, 0.76, 0.38, 0.24, 0, 360, 11), _arc_pts(0.5, 0.27, 0.45, 0.27, 0, 360, 11)],
    "9": [_arc_pts(0.5, 0.7, 0.45, 0.3, 0, 360, 11), [(0.94, 0.68), (0.75, 0.2), (0.25, 0.0)]],
    "/": [[(0.1, 0), (0.9, 1)]],
    "-": [[(0.15, 0.5), (0.85, 0.5)]],
    ".": [[(0.5, 0.0), (0.5, 0.02)]],
    ":": [[(0.5, 0.15), (0.5, 0.17)], [(0.5, 0.75), (0.5, 0.77)]],
    "%": [[(0.1, 0), (0.9, 1)], _arc_pts(0.2, 0.8, 0.15, 0.17, 0, 360, 7), _arc_pts(0.8, 0.2, 0.15, 0.17, 0, 360, 7)],
}
# real cockpit placard vocabulary (owner 2026-10-24: "Real English words" -- generic system labels, no logos, brands,
# registrations or serials) for the prints that carry no explicit `text`
VOCAB = ("ON OFF AUTO TEST NORM ARM MAN STBY BATT GEN EXT PWR BUS TIE FUEL PUMP BOOST IGN START NAV STROBE BEACON "
         "TAXI LDG RECOG LOGO WING DOME CABIN PANEL FLOOD DIM BRT PRESS DUMP HEAT VENT FAN PITOT STATIC PROBE "
         "WSHLD BOOTS INERT SEP PROP DEICE AP YD TRIM NOSE UP DN LWD RWD FLAP GEAR HORN TEST MASTER CAUT WARN "
         "RESET OPEN CLOSE PULL PUSH SEL VOL SQ COM NAV XPDR AUDIO OXY MASK CREW PAX TEMP COLD HOT EMER LIGHTS "
         "INST AVIONICS ESS NON HYD FIRE DET ECS BLEED FLOW HI LO").split()
CB_VOCAB = ("PFD 1|PFD 2|MFD|GTC 1|GTC 2|AHRS 1|AHRS 2|ADC 1|ADC 2|COM 1|COM 2|NAV 1|NAV 2|XPDR 1|XPDR 2|AUDIO|AP SERVO|"
            "TRIM|FLAP|GEAR|FUEL QTY|FUEL PUMP|BOOST|IGN|START|STBY BATT|GEN 1|GEN 2|BATT|EXT PWR|PITOT 1|PITOT 2|"
            "PROBES|WSHLD|BOOTS|INERT SEP|PROP DEICE|STALL|NAV LT|STROBE|BEACON|TAXI LT|LDG LT|RECOG|CABIN LT|DOME|"
            "PANEL LT|FLOOD|ECS|BLEED|PRESS|DUMP|OXY|WX RADAR|TAWS|DATALINK|ENG IND|OIL PRESS|ITT|TORQUE|NG|NP|"
            "FIRE DET|HORN|CAUT|WARN|STBY ATT|CLOCK|USB|12V|LAV|GALLEY").split("|")


def cb_names(key, n):
    """n breaker names for one CB panel, each used once (first-principles judge FPF-05: drawn per cell, names repeated
    within a row); a fixed shuffle of CB_VOCAB keyed by the panel."""
    rng = np.random.default_rng(zlib.crc32(repr(key).encode()))
    idx = rng.permutation(len(CB_VOCAB))
    return [CB_VOCAB[idx[i % len(idx)]] for i in range(n)]


def text_for(kw, rows, rng):
    """The rows of a print: kw['text'] (a str or a tuple of rows) when given, else generic placard words."""
    t = kw.get("text")
    if t is not None:
        t = (t,) if isinstance(t, str) else tuple(t)
        return list(t[:rows]) + [""] * max(0, rows - len(t))
    if kw.get("cb"):
        return [str(rng.choice(CB_VOCAB))] + [""] * (rows - 1)
    out = []
    for i in range(rows):
        n = int(rng.integers(1, 3)) if i == 0 else int(rng.integers(1, 4))
        out.append(" ".join(str(rng.choice(VOCAB)) for _ in range(n)))
    return out
_WIDTH = {"I": 0.25, "M": 0.85, "W": 0.95, "J": 0.6, "L": 0.62, "E": 0.62, "F": 0.62, "1": 0.6, ".": 0.3, ":": 0.3,
          "/": 0.6, "-": 0.6}
_CONS, _VOW = "BCDFGHKLMNPRSTVWZ", "AEIOU"


def _word(rng, n):
    """A random letter group of n capitals in consonant / vowel runs (reads as a word, means nothing)."""
    out, v = [], rng.random() < 0.3
    for _ in range(n):
        out.append(str(rng.choice(list(_VOW if v else _CONS))))
        v = (not v) if rng.random() < (0.9 if v else 0.6) else v
    return "".join(out)


def _letter(cv, x, y, h, ch, r):
    """Draw capital ch with its foot at (x, y) mm, cap height h, stroke radius r; returns its advance (mm)."""
    w = 0.62 * h * _WIDTH.get(ch, 1.0) / (1.0 if ch not in _WIDTH else 1.0)
    for pl in _L[ch]:
        P = [(x + px * w, y + py * h) for px, py in pl]
        for a, b in zip(P[:-1], P[1:]):
            cv.seg(a, b, r)
    return w


def _rng(kw, salt=0):
    key = repr(sorted((k, v) for k, v in kw.items() if k != "colour")) + str(salt)
    return np.random.default_rng(zlib.crc32(key.encode()))


def _words(cv, W, H, kw):
    """Rows of pseudo-text: rows (n), cap (mm, cap height), align ('c' / 'l' / 'r'), fill (share of the width used),
    weight (stroke / cap), seed."""
    rows = int(kw.get("rows", 1))
    cap = float(kw.get("cap", min(2.0, 0.75 * H / max(rows, 1) / 1.45)))
    # (dev round 1: at the crew stops the first prints vanished -- a silk-screened switch title is ~2.5-3 mm tall,
    # P1046408 at its camera shows every one as a white mark): CAP_K x the nominal cap, as large as the box allows
    cap = min(CAP_K * cap, 0.80 * H / rows)
    r = 0.5 * float(kw.get("weight", WEIGHT)) * cap
    hl = cap - 2 * r                                             # the letters' drawn height
    gap, wgap = 0.24 * cap, 0.55 * cap

    def wwidth(w_):
        return (sum(0.62 * hl * _WIDTH.get(c, 1.0) + gap for c in w_ if c != " ") + wgap * w_.count(" ") - gap
                + 2 * r)
    lead = (H - rows * cap) / (rows + 1)
    rng = _rng(kw)
    fill = float(kw.get("fill", 0.85))
    align = kw.get("align", "c")
    for i, line in enumerate(text_for(kw, rows, rng)):
        if not line:
            continue
        avail = W * (fill if i == 0 else fill * float(kw.get("fill2", 0.7)))
        k = min(1.0, max(0.35, avail / max(wwidth(line), 1e-6)))       # a long label is set smaller to fit
        hk, gk, rk = hl * k, gap * k, r * max(k, 0.7)
        total = wwidth(line) * k
        x = {"c": 0.5 * (W - total), "l": r + 0.2 * cap, "r": W - total - r - 0.2 * cap}[align]
        y = H - lead * (i + 1) - cap * (i + 1) + 0.5 * (1 - k) * hl
        for ch in line:
            if ch == " ":
                x += wgap * k
                continue
            x += _letter(cv, x + r, y + r, hk, ch, rk) + gk


def _stamp_words(cv, x0, y0, x1, y1, kw):
    """_words() into the box x0..x1 x y0..y1 (mm) of canvas cv."""
    W, H = x1 - x0, y1 - y0
    sub = _Canvas(max(1, int(round(W * cv.ppm))), max(1, int(round(H * cv.ppm))), cv.ppm)
    _words(sub, W, H, kw)
    X0 = int(round(x0 * cv.k))
    Y0 = cv.h - int(round(y1 * cv.k))
    hh, ww = sub.a.shape
    ya, xa = max(Y0, 0), max(X0, 0)
    yb, xb = min(Y0 + hh, cv.h), min(X0 + ww, cv.w)
    if yb > ya and xb > xa:
        cv.a[ya:yb, xa:xb] = np.maximum(cv.a[ya:yb, xa:xb], sub.a[ya - Y0:yb - Y0, xa - X0:xb - X0])


def _draw(cell):
    k, kw = cell["kind"], cell["kw"]
    ppm = cell["ppm"]
    cv = _Canvas(cell["w"], cell["h"], ppm)
    W, H = cell["w"] / ppm, cell["h"] / ppm
    lw = float(kw.get("lw", 0.35))                    # line width (mm)
    if k == "words":
        _words(cv, W, H, kw)
    elif k == "frame":
        # a frame round a switch group: line lw, corner radius rc, an optional title gap at the top (gap = share)
        rc = float(kw.get("rc", 1.5))
        g = float(kw.get("gap", 0.0))
        m = 0.5 * lw + 0.1
        x0, y0, x1, y1 = m, m, W - m, H - m
        xa, xb = 0.5 * W - 0.5 * g * W, 0.5 * W + 0.5 * g * W
        top = [((x0 + rc, y1), (x1 - rc, y1))] if g <= 0 else [((x0 + rc, y1), (xa, y1)), ((xb, y1), (x1 - rc, y1))]
        for p, q in top + [((x0 + rc, y0), (x1 - rc, y0)), ((x0, y0 + rc), (x0, y1 - rc)), ((x1, y0 + rc), (x1, y1 - rc))]:
            cv.seg(p, q, 0.5 * lw)
        for cx, cy, a in ((x1 - rc, y1 - rc, 0), (x0 + rc, y1 - rc, 90), (x0 + rc, y0 + rc, 180), (x1 - rc, y0 + rc, 270)):
            cv.arc((cx, cy), rc, a, a + 90, 0.5 * lw, n=8)
        if g > 0 and kw.get("title", True):
            sub = dict(kw, rows=1, cap=float(kw.get("cap", 1.6)), fill=0.95)
            cap = sub["cap"]
            cv2 = _Canvas(int(round(g * W * ppm)), int(round(2.2 * cap * ppm)), ppm)
            _words(cv2, g * W, 2.2 * cap, sub)
            a = cv2.a
            X0 = int(round(xa * cv.k))
            Y0 = int(round((H - (y1 + 1.1 * cap)) * cv.k))
            hh, ww = a.shape
            hh, ww = min(hh, cv.h - max(Y0, 0)), min(ww, cv.w - X0)
            cv.a[max(Y0, 0):max(Y0, 0) + hh, X0:X0 + ww] = np.maximum(cv.a[max(Y0, 0):max(Y0, 0) + hh, X0:X0 + ww],
                                                                        a[:hh, :ww])
    elif k == "ticks":
        # a straight tick scale along u: n ticks, every `major` one long, base line optional, side 'b' / 't'
        n = int(kw.get("n", 11))
        major = int(kw.get("major", 5))
        side = kw.get("side", "b")
        for i in range(n):
            x = lw + (W - 2 * lw) * i / max(n - 1, 1)
            L = (0.9 if i % major == 0 else 0.5) * H
            y0 = 0.0 if side == "b" else H - L
            cv.seg((x, y0 + 0.5 * lw), (x, y0 + L - 0.5 * lw), 0.5 * lw)
        if kw.get("base", True):
            yb = 0.5 * lw if side == "b" else H - 0.5 * lw
            cv.seg((lw, yb), (W - lw, yb), 0.5 * lw)
    elif k == "vticks":
        # a vertical scale (flap / trim): n ticks along v, majors longer, from the left edge
        n = int(kw.get("n", 5))
        major = int(kw.get("major", 1))
        for i in range(n):
            y = lw + (H - 2 * lw) * i / max(n - 1, 1)
            L = (0.95 if i % major == 0 else 0.55) * W
            cv.seg((0.5 * lw, y), (L - 0.5 * lw, y), 0.5 * lw)
    elif k == "arc":
        # a dimmer arc round a knob at the cell centre: radius R (mm), a0..a1 (deg, 0 = right, CCW), ticks, a
        # tapering wedge when `wedge` (OFF -> BRT)
        R = float(kw.get("R", 0.5 * min(W, H) - lw))
        a0, a1 = float(kw.get("a0", -135.0)), float(kw.get("a1", 135.0))
        c = (0.5 * W, 0.5 * H)
        if kw.get("wedge", True):
            n = 40
            for i in range(n):
                t0, t1 = i / n, (i + 1) / n
                A0, A1 = a1 - (a1 - a0) * t0, a1 - (a1 - a0) * t1
                rr = 0.5 * lw * (0.35 + 1.4 * t0)
                cv.arc(c, R - rr, A1, A0, rr, n=2)
        else:
            cv.arc(c, R, a0, a1, 0.5 * lw)
        for i in range(int(kw.get("ticks", 5))):
            A = math.radians(a0 + (a1 - a0) * i / max(int(kw.get("ticks", 5)) - 1, 1))
            cv.seg((c[0] + (R + 0.3) * math.cos(A), c[1] + (R + 0.3) * math.sin(A)),
                   (c[0] + (R + 1.2) * math.cos(A), c[1] + (R + 1.2) * math.sin(A)), 0.5 * lw)
    elif k == "dots":
        n = int(kw.get("n", 1))
        r = float(kw.get("r", 0.5 * min(H, W / max(n, 1)) * 0.5))
        for i in range(n):
            cv.dot(((i + 0.5) * W / n, 0.5 * H), r)
    elif k == "chevron":
        # n chevrons pointing up (dir 'u') / down ('d') / right ('r') / left ('l')
        n = int(kw.get("n", 1))
        d = kw.get("dir", "u")
        for i in range(n):
            if d in ("u", "d"):
                cx, w2 = (i + 0.5) * W / n, 0.4 * W / n
                ya, yb = (0.25 * H, 0.75 * H) if d == "u" else (0.75 * H, 0.25 * H)
                cv.seg((cx - w2, ya), (cx, yb), 0.5 * lw)
                cv.seg((cx + w2, ya), (cx, yb), 0.5 * lw)
            else:
                cy, h2 = (i + 0.5) * H / n, 0.4 * H / n
                xa, xb = (0.25 * W, 0.75 * W) if d == "r" else (0.75 * W, 0.25 * W)
                cv.seg((xa, cy - h2), (xb, cy), 0.5 * lw)
                cv.seg((xa, cy + h2), (xb, cy), 0.5 * lw)
    elif k == "stitch":
        # a stitched edge strip: rows of dashes (pitch, dash) along u
        rows = kw.get("rows", (0.5,))
        pitch, dash = float(kw.get("pitch", 4.0)), float(kw.get("dash", 2.6))
        for fy in rows:
            x = 0.5 * (pitch - dash)
            while x + dash < W:
                cv.seg((x + 0.5 * lw, fy * H), (x + dash - 0.5 * lw, fy * H), 0.5 * lw)
                x += pitch
    elif k == "bar":
        cv.rect(0, 0, W, H)
    elif k == "stripes":
        # diagonal hazard stripes (reverse gate): period (mm)
        P = float(kw.get("period", 4.0))
        for x in np.arange(-H, W + H, P):
            cv.seg((x, 0), (x + H, H), 0.25 * P)
    elif k == "plate":
        # a placard: a filled plate (colour) with text rows in `ink` (two inks: RGB per pixel), rounded corners rc mm
        rc = float(kw.get("rc", 0.6))
        cv.rect(0, rc, W, H - rc)
        cv.rect(rc, 0, W - rc, H)
        for cx, cy in ((rc, rc), (W - rc, rc), (rc, H - rc), (W - rc, H - rc)):
            cv.dot((cx, cy), rc)
        inner = _Canvas(cell["w"], cell["h"], ppm)
        m = float(kw.get("margin", 0.08))
        _words(inner, W * (1 - 2 * m), H, dict(kw, rows=kw.get("rows", 2), fill=float(kw.get("fill", 0.92))))
        sh = int(round(m * W * inner.k))
        ta = np.zeros_like(inner.a)
        ta[:, sh:] = inner.a[:, :inner.a.shape[1] - sh]
        return cv.result(), ta.reshape(ta.shape[0] // SS, SS, ta.shape[1] // SS, SS).mean((1, 3))
    elif k == "vector":
        # a free drawing in cell mm (origin bottom left): prims ('seg', x0, y0, x1, y1, lw), ('words', x0, y0, x1, y1,
        # rows, cap, seed), ('dot', x, y, r), ('arc', cx, cy, R, a0, a1, lw)
        for pr in kw["prims"]:
            if pr[0] == "seg":
                cv.seg(pr[1:3], pr[3:5], 0.5 * pr[5])
            elif pr[0] == "dot":
                cv.dot(pr[1:3], pr[3])
            elif pr[0] == "arc":
                cv.arc(pr[1:3], pr[3], pr[4], pr[5], 0.5 * pr[6])
            elif pr[0] == "words":
                _stamp_words(cv, *pr[1:5], dict(rows=pr[5], cap=pr[6], seed=pr[7], fill=0.95,
                                                **({"text": pr[8]} if len(pr) > 8 else {})))
    elif k == "cells":
        # a CB label strip: ncol cells (vertical rules between them, rules top and bottom), each with 1-2 rows of
        # short pseudo-words centred
        ncol = int(kw.get("ncol", 4))
        rows = int(kw.get("rows", 2))
        lw_ = float(kw.get("lw", 0.25))
        cw = W / ncol
        if kw.get("rules", True):
            cv.seg((0, 0.5 * lw_), (W, 0.5 * lw_), 0.5 * lw_)
            cv.seg((0, H - 0.5 * lw_), (W, H - 0.5 * lw_), 0.5 * lw_)
            for c in range(1, ncol):
                cv.seg((c * cw, 0), (c * cw, H), 0.5 * lw_)
        for c in range(ncol):
            sub = _Canvas(int(round(cw * ppm)), cell["h"], ppm)
            nm = kw.get("names")          # the breakers' own names (unique on a panel), else drawn from CB_VOCAB
            _words(sub, cw, H, dict(kw, rows=1, cb=True, fill=0.86, seed=(kw.get("seed"), c),
                                    **({"text": nm[c]} if nm else {})))
            X0 = int(round(c * cw * cv.k))
            hh, ww = sub.a.shape
            ww = min(ww, cv.w - X0)
            cv.a[:hh, X0:X0 + ww] = np.maximum(cv.a[:hh, X0:X0 + ww], sub.a[:, :ww])
    else:
        raise KeyError(k)
    return cv.result()


def atlas(scale=1.0):
    """The atlas as PNG bytes (RGBA; RGB the cell's ink everywhere in the cell, alpha its shape); scale < 1 box-filters
    it down (the light tier), cropped to the rows in use (UVs scaled to match: see uv_scale())."""
    from PIL import Image
    img = np.zeros((SIZE_H, SIZE, 4), np.uint8)
    img[..., :3] = 255
    for c in _CELLS:
        a = _draw(c)
        col = COLOURS[c["kw"].get("colour", "white")]
        x, y, w, h = c["x"], c["y"], c["w"], c["h"]
        x0, y0 = max(0, x - PAD + 1), max(0, y - PAD + 1)                 # the ink bleeds into the padding (mips)
        img[y0:y + h + PAD - 1, x0:x + w + PAD - 1, :3] = col
        if isinstance(a, tuple):                                           # two inks: the plate + its text
            a, ta = a
            ink = np.array(COLOURS[c["kw"].get("ink", "white")], float)
            rgb = np.array(col, float) * (1 - ta[..., None]) + ink * ta[..., None]
            img[y:y + h, x:x + w, :3] = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
        img[y:y + h, x:x + w, 3] = np.clip(np.round(255 * a), 0, 255).astype(np.uint8)
    im = Image.fromarray(img, "RGBA")
    if scale != 1.0:
        im = im.resize((int(SIZE * scale), int(SIZE_H * scale)), Image.BOX)
    bio = io.BytesIO()
    im.save(bio, "PNG", optimize=True)
    return bio.getvalue()


def used():
    return len(_CELLS), _SHELF["y"]
