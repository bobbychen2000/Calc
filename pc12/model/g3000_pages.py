"""
model.g3000_pages -- generic G3000-PRIME-style display pages, carried in out/pc12.glb as one texture atlas
(final judge r1 R2 / I1: the flat coloured page geometry read as a placeholder).

    python3 model/g3000_pages.py [--out out/tmp/displays]      # writes the pages + the atlas, prints the paths

model/flightdeck.py maps the atlas onto the five displays' glass (material 'display_page': emissive texture + UVs,
written by cad/glb.py), so the viewer, the GLB and every importer show the same pages.  Pages:
  pfd_L / pfd_R  split PDU: the PFD on the outboard 62 % -- synthetic-vision sky and layered terrain ridges, pitch ladder,
                 roll scale, flight-director cue, airspeed / altitude tapes with numerals and speed bands, VSI, an HSI
                 compass rose (ticks every 5 deg, numerals every 30) with a magenta course needle, a heading bug, data
                 boxes and a softkey row -- and an inboard flight-plan pane (rows of numeric legs, the active leg magenta)
  mfd            engine strip (TRQ / ITT / NG dials with green arcs, bar gauges) and a moving map: shaded relief in the
                 terrain palette, lakes, rivers, roads, towns, airspace rings, a magenta flight plan with waypoints, the
                 own-ship symbol, range ring and compass arc; a vertical-profile strip below
  sdu_L / sdu_R  touch controllers: status bar and dense grids of rounded buttons with simple glyphs and legend marks
Unbranded: no logos, and no lettering beyond instrument numerals (legends are short bars).  Everything is numpy + PIL,
deterministic (fixed seeds); the atlas is cached by the hash of this file (out/tmp/displays, git-ignored).
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out" / "tmp" / "displays"
SIZES = {"pdu": (2048, 1275), "sdu": (640, 1028)}      # active areas 302 x 188 mm and 94 x 151 mm (flightdeck)
SS = 2                                                 # supersampling of the drawing

# palette (sRGB)
BG = (10, 12, 17)
PANE = (22, 26, 34)
BAR = (30, 34, 42)
LINE = (70, 78, 92)
WHITE = (236, 238, 240)
GREY = (150, 156, 166)
CYAN = (40, 210, 240)
GREEN = (60, 220, 90)
MAGENTA = (230, 60, 220)
AMBER = (250, 190, 40)
YELLOW = (250, 230, 40)
RED = (230, 40, 40)
TAPE = (40, 44, 52, 170)


def _font(px, bold=False):
    from PIL import ImageFont
    names = (("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf") if bold else ("DejaVuSans.ttf", "LiberationSans-Regular.ttf"))
    for d in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/dejavu"):
        for n in names:
            f = os.path.join(d, n)
            if os.path.exists(f):
                return ImageFont.truetype(f, int(px))
    return ImageFont.load_default()


def _noise2(h, w, scales, seed, amps=None):
    """Fractal value noise (h, w) in [0, 1]: random grids of the given cell sizes (px), bicubic-upsampled, summed."""
    from PIL import Image
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amps = amps or [0.5 ** i for i in range(len(scales))]
    for s, a in zip(scales, amps):
        gh, gw = max(2, int(h / s) + 2), max(2, int(w / s) + 2)
        g = rng.random((gh, gw)).astype(np.float32)
        im = Image.fromarray(g, "F").resize((w, h), Image.BICUBIC)
        acc += a * np.asarray(im)
    acc -= acc.min()
    return acc / max(float(acc.max()), 1e-6)


def _noise1(n, scales, seed, amps=None):
    rng = np.random.default_rng(seed)
    x = np.arange(n)
    acc = np.zeros(n)
    amps = amps or [0.5 ** i for i in range(len(scales))]
    for s, a in zip(scales, amps):
        k = int(n / s) + 3
        g = rng.random(k)
        xs = x / s
        i = np.floor(xs).astype(int)
        t = xs - i
        t = t * t * (3 - 2 * t)
        acc += a * (g[i] * (1 - t) + g[i + 1] * t)
    acc -= acc.min()
    return acc / max(acc.max(), 1e-9)


class Canvas:
    """RGB canvas drawn at SS x the final size (coordinates in FINAL pixels, scaled here)."""

    def __init__(self, w, h, bg=BG):
        from PIL import Image, ImageDraw
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1, r=0):
        box = [min(x0, x1) * SS, min(y0, y1) * SS, max(x0, x1) * SS, max(y0, y1) * SS]
        if r:
            self.d.rounded_rectangle(box, r * SS, fill=fill, outline=outline, width=int(width * SS))
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=int(width * SS))

    def line(self, pts, fill, width=1):
        self.d.line(self._p(pts), fill=fill, width=max(1, int(round(width * SS))), joint="curve")

    def poly(self, pts, fill=None, outline=None, width=1):
        self.d.polygon(self._p(pts), fill=fill, outline=outline, width=int(width * SS) if outline else 1)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1):
        self.d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=fill, outline=outline,
                       width=int(width * SS))

    def arc(self, cx, cy, r, a0, a1, fill, width=1):
        self.d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], a0, a1, fill=fill,
                   width=max(1, int(width * SS)))

    def text(self, x, y, s, px, fill=WHITE, anchor="mm", bold=False):
        self.d.text((x * SS, y * SS), s, font=_font(px * SS, bold), fill=fill, anchor=anchor)

    def marks(self, x, y, n, px, fill=GREY, seed=0, gap=0.35):
        """A legend as short bars (no lettering): n 'words' of 2-6 letter widths at height px."""
        rng = np.random.default_rng(seed)
        for _ in range(n):
            L = px * rng.uniform(1.2, 3.2)
            self.rect(x, y - 0.32 * px, x + L, y + 0.32 * px, fill=fill, r=0.15 * px)
            x += L + gap * px * 2
        return x

    def paste(self, img, x, y):
        self.im.paste(img, (int(x * SS), int(y * SS)))

    def final(self):
        from PIL import Image
        return self.im.resize((self.w, self.h), Image.LANCZOS)


# ------------------------------------------------------------------------------------------------------------ PFD
def _svt(w, h, y_h, seed, roll_deg=0.0):
    """Synthetic-vision background (w x h, final px): sky gradient over layered terrain ridges below the horizon row
    y_h, drawn at SS; returns a PIL image (SS scale)."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H, yh = w * SS, h * SS, y_h * SS
    yy = np.arange(H)[:, None].astype(np.float32)
    t = np.clip((yh - yy) / max(yh, 1), 0, 1)                       # 0 at the horizon, 1 at the top
    sky_top, sky_hor = np.array([28, 78, 176], np.float32), np.array([128, 176, 228], np.float32)
    sky = sky_hor + (sky_top - sky_hor) * (t ** 0.7)[..., None]
    img = np.broadcast_to(sky, (H, W, 3)).copy()
    # ground base below the horizon: hazy green far -> richer green / brown near
    g = np.clip((yy - yh) / max(H - yh, 1), 0, 1)
    far, near = np.array([112, 140, 110], np.float32), np.array([66, 104, 46], np.float32)
    ground = far + (near - far) * (g ** 0.6)[..., None]
    img = np.where((yy > yh)[..., None], np.broadcast_to(ground, (H, W, 3)), img)
    im = Image.fromarray(img.astype(np.uint8))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    n_layers = 16
    xs = np.linspace(0, W, 160)
    for i in range(n_layers):
        k = i / (n_layers - 1)                                      # 0 far .. 1 near
        base = yh + (H - yh) * (0.02 + 0.9 * k ** 1.8)
        amp = (0.04 + 0.35 * k ** 1.3) * (H - yh) * (1.4 if i < 4 else 1.0)
        prof = _noise1(len(xs), (40 - 30 * k, 14 - 9 * k, 5), seed + 17 * i)
        prof = prof ** (1.6 - 0.5 * k)
        ys = base - amp * prof
        # colour: far layers hazy blue-green, near ones green / olive / brown with the crest lit
        haze = (1 - k) ** 1.5
        c_near = np.array([[70, 110, 48], [92, 116, 58], [110, 100, 64], [80, 120, 60]])[i % 4]
        c = c_near * (1 - haze) + np.array([126, 154, 150]) * haze
        c = c * rng.uniform(0.9, 1.08)
        pts = list(zip(xs, ys)) + [(W, H), (0, H)]
        d.polygon(pts, fill=tuple(int(v) for v in np.clip(c, 0, 255)))
        # sunlit crest band on the slopes facing the light (left): lighter strip under the ridge line
        dy = np.gradient(ys)
        for j in range(len(xs) - 1):
            if dy[j] > 0.2:
                continue
            a = min(1.0, -dy[j] / (amp * 0.03 + 1e-3))
            cc = tuple(int(v) for v in np.clip(c * (1.0 + 0.22 * a), 0, 255))
            d.polygon([(xs[j], ys[j]), (xs[j + 1], ys[j + 1]), (xs[j + 1], ys[j + 1] + 0.10 * amp),
                       (xs[j], ys[j] + 0.10 * amp)], fill=cc)
    # fine texture on the ground (fields / forest mottling)
    arr = np.asarray(im).astype(np.float32)
    n = _noise2(H, W, (6 * SS, 18 * SS, 50 * SS), seed + 99)
    mask = (yy > yh + 2 * SS)[..., 0] if False else (np.arange(H)[:, None] > yh + 2 * SS)
    arr = np.where(mask[..., None], arr * (0.88 + 0.22 * n[..., None]), arr)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6 * SS))
    if roll_deg:
        im = im.rotate(roll_deg, resample=Image.BICUBIC, center=(W / 2, yh), fillcolor=tuple(int(v) for v in sky_top))
    return im


def pfd_pane(c: Canvas, x0, y0, w, h, seed=3, hdg=287.0, ias=172, alt=11500, sel_alt=12000):
    """PFD in the rectangle (x0, y0, w, h) of canvas c (final px)."""
    top = 0.075 * h                                                  # nav status bar
    ax0, ay0, aw, ah = x0, y0 + top, w, h - top - 0.07 * h           # attitude area (SVT), softkeys below
    cx = ax0 + 0.47 * aw
    y_h = ay0 + 0.36 * ah                                            # horizon (pitch ~ +3 deg nose up)
    svt = _svt(int(aw), int(ah), y_h - ay0, seed)
    c.paste(svt, ax0, ay0)
    ppd = 0.018 * ah                                                 # px per degree of pitch
    # horizon line + pitch ladder
    c.line([(ax0, y_h), (ax0 + aw, y_h)], WHITE, 2.2)
    for p in (-10, -5, 5, 10, 15, 20):
        y = y_h - p * ppd
        if y < ay0 + 0.06 * ah:
            continue
        L = 0.075 * aw if p % 10 == 0 else 0.035 * aw
        c.line([(cx - L, y), (cx + L, y)], WHITE, 1.8)
        if p % 10 == 0:
            for s in (-1, 1):
                c.text(cx + s * (L + 0.022 * aw), y, f"{abs(p)}", 0.028 * ah, WHITE)
    for p in (-2.5, 2.5, 7.5):
        y = y_h - p * ppd
        c.line([(cx - 0.018 * aw, y), (cx + 0.018 * aw, y)], WHITE, 1.4)
    # roll scale arc + pointer
    R = 0.30 * ah
    rc = (cx, y_h + 0.12 * ah)
    c.arc(rc[0], rc[1], R, 210, 330, WHITE, 1.8)
    for a in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
        th = math.radians(-90 + a)
        L = 0.045 * ah if a % 30 == 0 else 0.025 * ah
        c.line([(rc[0] + R * math.cos(th), rc[1] + R * math.sin(th)),
                (rc[0] + (R + L) * math.cos(th), rc[1] + (R + L) * math.sin(th))], WHITE, 1.8)
    c.poly([(cx, rc[1] - R - 0.002 * ah), (cx - 0.02 * ah, rc[1] - R - 0.045 * ah), (cx + 0.02 * ah, rc[1] - R - 0.045 * ah)],
           fill=WHITE)
    c.poly([(cx, rc[1] - R + 0.004 * ah), (cx - 0.018 * ah, rc[1] - R + 0.040 * ah),
            (cx + 0.018 * ah, rc[1] - R + 0.040 * ah)], fill=YELLOW)
    # flight director (magenta chevrons) and the aircraft symbol (yellow wedges)
    fy = y_h - 1.0 * ppd
    for s in (-1, 1):
        c.poly([(cx, fy), (cx + s * 0.12 * aw, fy + 0.07 * ah), (cx + s * 0.10 * aw, fy + 0.085 * ah)], fill=MAGENTA)
        c.poly([(cx, y_h + 0.012 * ah), (cx + s * 0.11 * aw, y_h + 0.085 * ah), (cx + s * 0.06 * aw, y_h + 0.085 * ah)],
               fill=YELLOW, outline=(40, 30, 0), width=1)
    # airspeed tape
    tx0, tx1 = ax0 + 0.035 * aw, ax0 + 0.135 * aw
    ty0, ty1 = ay0 + 0.10 * ah, ay0 + 0.66 * ah
    tm = 0.5 * (ty0 + ty1)
    c.rect(tx0, ty0, tx1, ty1, fill=TAPE)
    kpx = (ty1 - ty0) / 60.0                                          # 60 kt over the tape
    for v in range(ias - 40, ias + 41):
        y = tm - (v - ias) * kpx
        if y < ty0 + 4 or y > ty1 - 4:
            continue
        if v % 10 == 0:
            c.line([(tx1 - 0.022 * aw, y), (tx1, y)], WHITE, 1.6)
            if v % 20 == 0:
                c.text(tx1 - 0.030 * aw, y, f"{v}", 0.034 * ah, WHITE, anchor="rm")
        elif v % 5 == 0:
            c.line([(tx1 - 0.012 * aw, y), (tx1, y)], WHITE, 1.2)
    for (v0, v1, col) in ((ias - 40, 160, GREEN), (160, 200, YELLOW), (200, ias + 40, RED)):
        a, b = tm - (v0 - ias) * kpx, tm - (v1 - ias) * kpx
        c.rect(tx1 - 0.006 * aw, max(min(a, b), ty0), tx1, min(max(a, b), ty1), fill=col)
    c.rect(tx0 - 0.004 * aw, tm - 0.035 * ah, tx1 - 0.006 * aw, tm + 0.035 * ah, fill=(0, 0, 0), outline=WHITE, width=1.5)
    c.text(tx1 - 0.014 * aw, tm, f"{ias}", 0.050 * ah, WHITE, anchor="rm", bold=True)
    c.rect(tx0, ty0 - 0.050 * ah, tx1, ty0, fill=(0, 0, 0))
    c.text(0.5 * (tx0 + tx1), ty0 - 0.025 * ah, "180", 0.032 * ah, CYAN)
    c.rect(tx0, ty1, tx1, ty1 + 0.045 * ah, fill=(0, 0, 0))
    c.text(0.5 * (tx0 + tx1), ty1 + 0.0225 * ah, ".412", 0.030 * ah, WHITE)
    # altitude tape + VSI
    ax_0, ax_1 = ax0 + 0.80 * aw, ax0 + 0.915 * aw
    c.rect(ax_0, ty0, ax_1, ty1, fill=TAPE)
    fpx = (ty1 - ty0) / 600.0
    for v in range(alt - 300, alt + 301, 20):
        y = tm - (v - alt) * fpx
        if y < ty0 + 4 or y > ty1 - 4:
            continue
        if v % 100 == 0:
            c.line([(ax_0, y), (ax_0 + 0.020 * aw, y)], WHITE, 1.6)
            c.text(ax_0 + 0.026 * aw, y, f"{v}", 0.030 * ah, WHITE, anchor="lm")
        else:
            c.line([(ax_0, y), (ax_0 + 0.010 * aw, y)], WHITE, 1.1)
    yb = tm - (sel_alt - alt) * fpx
    c.poly([(ax_0, yb - 0.02 * ah), (ax_0 + 0.012 * aw, yb - 0.02 * ah), (ax_0 + 0.012 * aw, yb + 0.02 * ah),
            (ax_0, yb + 0.02 * ah), (ax_0 + 0.006 * aw, yb)], fill=CYAN)
    c.rect(ax_0 + 0.004 * aw, tm - 0.035 * ah, ax_1 + 0.022 * aw, tm + 0.035 * ah, fill=(0, 0, 0), outline=WHITE,
           width=1.5)
    c.text(ax_1 + 0.016 * aw, tm, f"{alt}", 0.040 * ah, WHITE, anchor="rm", bold=True)
    c.rect(ax_0, ty0 - 0.050 * ah, ax_1, ty0, fill=(0, 0, 0))
    c.text(0.5 * (ax_0 + ax_1), ty0 - 0.025 * ah, f"{sel_alt}", 0.032 * ah, CYAN)
    c.rect(ax_0, ty1, ax_1, ty1 + 0.045 * ah, fill=(0, 0, 0))
    c.text(0.5 * (ax_0 + ax_1), ty1 + 0.0225 * ah, "29.92", 0.030 * ah, CYAN)
    vx0, vx1 = ax_1 + 0.008 * aw, ax_1 + 0.045 * aw
    c.rect(vx0, ty0 + 0.04 * ah, vx1, ty1 - 0.04 * ah, fill=(40, 44, 52, 140))
    for k in (-2, -1, 0, 1, 2):
        y = tm - k * 0.10 * ah
        c.line([(vx0, y), (vx0 + 0.012 * aw, y)], WHITE, 1.3)
        if k:
            c.text(vx0 + 0.022 * aw, y, f"{abs(k)}", 0.026 * ah, WHITE)
    c.poly([(vx0, tm - 0.05 * ah), (vx0 + 0.02 * aw, tm - 0.065 * ah), (vx0 + 0.02 * aw, tm - 0.035 * ah)], fill=GREEN)
    # HSI (compass rose) at the bottom centre
    hr = 0.235 * ah
    hc = (cx, ay0 + ah - 0.06 * ah + 0.02 * ah)
    hcy = ay0 + 0.745 * ah + 0.5 * hr
    hc = (cx, min(hcy, ay0 + ah + 0.10 * ah))
    c.circle(hc[0], hc[1], hr * 1.02, fill=(12, 14, 20, 200))
    for a in range(0, 360, 5):
        th = math.radians(a - hdg - 90)
        L = 0.07 * hr if a % 10 == 0 else 0.04 * hr
        c.line([(hc[0] + hr * math.cos(th), hc[1] + hr * math.sin(th)),
                (hc[0] + (hr - L) * math.cos(th), hc[1] + (hr - L) * math.sin(th))], WHITE, 1.4)
        if a % 30 == 0:
            rr = hr - 0.17 * hr
            c.text(hc[0] + rr * math.cos(th), hc[1] + rr * math.sin(th), f"{a // 10 if a else 36}", 0.11 * hr, WHITE)
    # heading box + lubber
    c.rect(hc[0] - 0.13 * hr, hc[1] - hr - 0.17 * hr, hc[0] + 0.13 * hr, hc[1] - hr - 0.02 * hr, fill=(0, 0, 0),
           outline=WHITE, width=1.4)
    c.text(hc[0], hc[1] - hr - 0.095 * hr, f"{int(hdg):03d}", 0.11 * hr, WHITE, bold=True)
    # course needle (magenta), CDI, heading bug (cyan), aircraft
    crs = math.radians(292 - hdg - 90)
    u = np.array([math.cos(crs), math.sin(crs)])
    n = np.array([-u[1], u[0]])
    P = np.array(hc)
    for a_, b_ in ((0.78, 0.30), (-0.30, -0.78)):
        c.line([tuple(P + a_ * hr * u), tuple(P + b_ * hr * u)], MAGENTA, 3.2)
    c.poly([tuple(P + 0.80 * hr * u), tuple(P + 0.66 * hr * u + 0.07 * hr * n), tuple(P + 0.66 * hr * u - 0.07 * hr * n)],
           fill=MAGENTA)
    c.line([tuple(P - 0.26 * hr * u + 0.06 * hr * n), tuple(P + 0.26 * hr * u + 0.06 * hr * n)], MAGENTA, 3.2)
    for k in (-2, -1, 1, 2):
        c.circle(*(P + k * 0.13 * hr * n), 0.018 * hr, outline=WHITE, width=1.2)
    bug = math.radians(300 - hdg - 90)
    bu = np.array([math.cos(bug), math.sin(bug)])
    bn = np.array([-bu[1], bu[0]])
    c.poly([tuple(P + hr * bu + 0.05 * hr * bn), tuple(P + hr * bu - 0.05 * hr * bn), tuple(P + 0.93 * hr * bu)],
           fill=CYAN)
    c.poly([(P[0], P[1] - 0.12 * hr), (P[0] - 0.09 * hr, P[1] + 0.06 * hr), (P[0], P[1] + 0.02 * hr),
            (P[0] + 0.09 * hr, P[1] + 0.06 * hr)], fill=WHITE)
    # data boxes (wind, OAT, TAS, GS) bottom corners
    for (bx, by, vals, col) in ((ax0 + 0.02 * aw, ay0 + 0.74 * ah, ("270", "12", "-18"), WHITE),
                                (ax0 + 0.79 * aw, ay0 + 0.74 * ah, ("268", "251", "35"), GREEN)):
        c.rect(bx, by, bx + 0.17 * aw, by + 0.16 * ah, fill=(0, 0, 0, 200), outline=LINE, width=1)
        for k, v in enumerate(vals):
            yy = by + (0.035 + 0.045 * k) * ah
            c.marks(bx + 0.012 * aw, yy, 1, 0.022 * ah, GREY, seed=k + int(bx))
            c.text(bx + 0.155 * aw, yy, v, 0.030 * ah, col, anchor="rm")
    # nav status bar (top) and softkeys (bottom)
    c.rect(x0, y0, x0 + w, y0 + top, fill=(8, 9, 12))
    fields = ((0.02, "117.95", GREEN), (0.18, "112.30", WHITE), (0.36, "12.4", MAGENTA), (0.50, "292", MAGENTA),
              (0.63, "0:07", WHITE), (0.80, "251", GREEN))
    for fx, v, col in fields:
        c.rect(x0 + fx * w, y0 + 0.40 * top, x0 + (fx + 0.030) * w, y0 + 0.60 * top, fill=GREY, r=3)
        c.text(x0 + (fx + 0.038) * w, y0 + 0.5 * top, v, 0.40 * top, col, anchor="lm")
    sk0 = y0 + h - 0.07 * h
    c.rect(x0, sk0, x0 + w, y0 + h, fill=(8, 9, 12))
    for k in range(8):
        bx = x0 + (k + 0.08) * w / 8
        c.rect(bx, sk0 + 0.012 * h, bx + 0.84 * w / 8, y0 + h - 0.012 * h, fill=(34, 38, 46), outline=LINE, r=4)
        c.marks(bx + 0.18 * w / 8, sk0 + 0.035 * h, 1, 0.020 * h, (190, 196, 204), seed=50 + k)


def fplan_pane(c: Canvas, x0, y0, w, h, seed=5, active=2):
    """Inboard flight-plan pane: header tabs, a column header, legs (numerals only), the active leg magenta."""
    c.rect(x0, y0, x0 + w, y0 + h, fill=PANE)
    hb = 0.075 * h
    c.rect(x0, y0, x0 + w, y0 + hb, fill=(8, 9, 12))
    for k in range(3):
        bx = x0 + (0.03 + 0.32 * k) * w
        c.rect(bx, y0 + 0.012 * h, bx + 0.29 * w, y0 + hb - 0.010 * h, fill=(46, 52, 64) if k == 0 else (30, 34, 42),
               r=5)
        c.marks(bx + 0.04 * w, y0 + 0.5 * hb, 1, 0.022 * h, CYAN if k == 0 else GREY, seed=k + 7)
    ych = y0 + hb + 0.045 * h
    for fx in (0.05, 0.42, 0.62, 0.82):
        c.marks(x0 + fx * w, ych, 1, 0.018 * h, GREY, seed=int(fx * 97))
    c.line([(x0 + 0.02 * w, ych + 0.03 * h), (x0 + 0.98 * w, ych + 0.03 * h)], LINE, 1.2)
    rng = np.random.default_rng(seed)
    rows = 11
    rh = (h - (ych + 0.05 * h - y0) - 0.10 * h) / rows
    for i in range(rows):
        yy = ych + 0.06 * h + (i + 0.5) * rh
        col = MAGENTA if i == active else (WHITE if i > active else (130, 136, 146))
        if i == active:
            c.rect(x0 + 0.01 * w, yy - 0.45 * rh, x0 + 0.99 * w, yy + 0.45 * rh, fill=(60, 20, 60, 120))
            c.poly([(x0 + 0.015 * w, yy - 0.2 * rh), (x0 + 0.035 * w, yy), (x0 + 0.015 * w, yy + 0.2 * rh)], fill=MAGENTA)
        c.marks(x0 + 0.05 * w, yy, 1, 0.30 * rh, col, seed=100 + i)
        dtk = int(rng.uniform(0, 360))
        dis = rng.uniform(3, 60)
        c.text(x0 + 0.52 * w, yy, f"{dtk:03d}", 0.40 * rh, col, anchor="rm")
        c.text(x0 + 0.74 * w, yy, f"{dis:.1f}", 0.40 * rh, col, anchor="rm")
        c.text(x0 + 0.96 * w, yy, f"{int(dis * 7 + 3000) // 100 * 100}", 0.40 * rh, CYAN if i > active else col,
               anchor="rm")
        c.line([(x0 + 0.02 * w, yy + 0.5 * rh), (x0 + 0.98 * w, yy + 0.5 * rh)], (40, 44, 54), 1.0)
    # bottom summary strip
    by = y0 + h - 0.09 * h
    c.rect(x0, by, x0 + w, y0 + h, fill=(8, 9, 12))
    for k, v in enumerate(("1:42", "412", "8.4")):
        c.marks(x0 + (0.04 + 0.33 * k) * w, by + 0.045 * h, 1, 0.018 * h, GREY, seed=200 + k)
        c.text(x0 + (0.30 + 0.33 * k) * w, by + 0.045 * h, v, 0.032 * h, WHITE, anchor="rm")


def pfd_page(side):
    W, H = SIZES["pdu"]
    c = Canvas(W, H)
    wp = int(0.60 * W)
    gap = 6
    if side <= 0:
        pfd_pane(c, 0, 0, wp, H, seed=3)
        fplan_pane(c, wp + gap, 0, W - wp - gap, H, seed=5)
    else:
        fplan_pane(c, 0, 0, W - wp - gap, H, seed=9, active=3)
        pfd_pane(c, W - wp, 0, wp, H, seed=4, ias=172, alt=11500)
    return c.final()


# ------------------------------------------------------------------------------------------------------------ MFD
def _relief(w, h, seed):
    """Moving-map relief (w x h final px) at SS: terrain-palette shaded relief, lakes, rivers, roads, towns."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H = w * SS, h * SS
    z = _noise2(H, W, (260 * SS, 110 * SS, 44 * SS, 16 * SS), seed, amps=[1.0, 0.5, 0.22, 0.06])
    ridge = 1.0 - np.abs(2 * _noise2(H, W, (160 * SS, 60 * SS), seed + 1) - 1)
    z = 0.65 * z + 0.35 * ridge * z
    # hillshade (light from the NW)
    gy, gx = np.gradient(z * 60.0)
    shade = np.clip(0.85 + 1.2 * (-gx * 0.7 - gy * 0.7) / np.sqrt(1 + gx ** 2 + gy ** 2), 0.6, 1.2)
    # terrain palette (sectional-like): green lowland -> yellow-green -> tan -> brown -> light rock
    stops = np.array([0.0, 0.30, 0.48, 0.62, 0.78, 1.0])
    cols = np.array([[122, 160, 96], [158, 178, 110], [206, 196, 140], [196, 160, 104], [160, 120, 84],
                     [214, 206, 196]], np.float32)
    rgb = np.stack([np.interp(z, stops, cols[:, k]) for k in range(3)], -1) * shade[..., None]
    water = z < 0.16
    rgb[water] = (86, 140, 204)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA")
    rng = np.random.default_rng(seed + 2)
    # rivers: descend along the negative gradient from a few springs
    for _ in range(5):
        y, x = rng.integers(0, H), rng.integers(0, W)
        pts = []
        for _ in range(900):
            pts.append((x, y))
            yi, xi = int(np.clip(y, 0, H - 1)), int(np.clip(x, 0, W - 1))
            dx, dy = -gx[yi, xi], -gy[yi, xi]
            nrm = math.hypot(dx, dy) + 1e-6
            x += 4 * SS * dx / nrm + rng.normal(0, 1.2 * SS)
            y += 4 * SS * dy / nrm + rng.normal(0, 1.2 * SS)
            if not (0 <= x < W and 0 <= y < H) or water[int(y), int(x)]:
                break
        if len(pts) > 20:
            d.line(pts, fill=(70, 130, 200, 255), width=int(1.6 * SS), joint="curve")
    # roads: gently curving polylines, a few highways (thicker, yellow-orange)
    for k in range(9):
        a = rng.uniform(0, math.pi)
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        pts = []
        for _ in range(60):
            pts.append((x, y))
            a += rng.normal(0, 0.12)
            x += 30 * SS * math.cos(a)
            y += 30 * SS * math.sin(a)
        wd, col = ((2.4, (230, 150, 60, 255)) if k < 3 else (1.3, (120, 110, 100, 230)))
        d.line(pts, fill=col, width=int(wd * SS), joint="curve")
    # towns: small yellow blobs
    for _ in range(26):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(3, 11) * SS
        d.ellipse([x - r, y - 0.7 * r, x + r, y + 0.7 * r], fill=(238, 214, 90, 230))
    return im.filter(ImageFilter.GaussianBlur(0.5 * SS)), z


def mfd_page():
    W, H = SIZES["pdu"]
    c = Canvas(W, H)
    ew = int(0.20 * W)
    # --- engine strip
    c.rect(0, 0, ew, H, fill=(12, 14, 19))
    gauges = (("TRQ", 72, (0.0, 0.9), GREEN), ("ITT", 690, (0.0, 0.85), GREEN), ("NG", 96.4, (0.0, 0.95), GREEN))
    for k, (_, val, (g0, g1), col) in enumerate(gauges):
        gx, gy, r = 0.5 * ew, 0.12 * H + k * 0.20 * H, 0.075 * H
        c.arc(gx, gy, r, 150, 390, (70, 76, 88), 0.012 * H)
        c.arc(gx, gy, r, 150 + 240 * g0, 150 + 240 * g1, col, 0.012 * H)
        c.arc(gx, gy, r, 150 + 240 * 0.95, 390, RED, 0.012 * H)
        frac = 0.62 + 0.08 * k
        th = math.radians(150 + 240 * frac)
        c.line([(gx, gy), (gx + 0.92 * r * math.cos(th), gy + 0.92 * r * math.sin(th))], WHITE, 3)
        c.circle(gx, gy, 0.012 * H, fill=WHITE)
        c.rect(gx - 0.33 * ew, gy + 0.035 * H, gx + 0.33 * ew, gy + 0.085 * H, fill=(0, 0, 0), outline=LINE, width=1)
        c.text(gx + 0.28 * ew, gy + 0.060 * H, f"{val}", 0.040 * H, GREEN, anchor="rm")
        c.marks(gx - 0.30 * ew, gy + 0.060 * H, 1, 0.018 * H, GREY, seed=300 + k)
    # bar gauges (prop, oil press / temp, fuel)
    for k in range(4):
        by = 0.66 * H + k * 0.052 * H
        c.marks(0.05 * ew, by, 1, 0.016 * H, GREY, seed=400 + k)
        c.rect(0.26 * ew, by - 0.008 * H, 0.66 * ew, by + 0.008 * H, fill=(50, 56, 66))
        c.rect(0.35 * ew, by - 0.008 * H, 0.59 * ew, by + 0.008 * H, fill=(40, 170, 70))
        px = 0.26 * ew + (0.52 + 0.06 * k) * 0.40 * ew
        c.poly([(px, by - 0.004 * H), (px - 0.012 * H, by - 0.022 * H), (px + 0.012 * H, by - 0.022 * H)], fill=WHITE)
        c.text(0.97 * ew, by, f"{[2000, 112, 74, 1480][k]}", 0.028 * H, WHITE, anchor="rm")
    for s, v in ((0, "1180"), (1, "1175")):
        bx = (0.22 + 0.36 * s) * ew
        c.rect(bx, 0.87 * H, bx + 0.20 * ew, 0.975 * H, fill=(50, 56, 66))
        c.rect(bx, 0.90 * H, bx + 0.20 * ew, 0.975 * H, fill=(40, 170, 70))
        c.text(bx + 0.10 * ew, 0.855 * H, v, 0.026 * H, WHITE)
    c.line([(ew, 0), (ew, H)], LINE, 2)
    # --- map pane
    mx0, mw = ew + 3, W - ew - 3
    top = int(0.075 * H)
    vp = int(0.22 * H)                                                # vertical profile strip
    mh = H - top - vp
    relief, z = _relief(mw, mh, seed=21)
    c.paste(relief, mx0, top)
    # airspace rings, range ring, compass arc
    ox, oy = mx0 + 0.52 * mw, top + 0.80 * mh                        # own ship
    for (cxr, cyr, r, col) in ((0.30, 0.35, 0.22, (70, 110, 230, 255)), (0.78, 0.28, 0.16, (190, 60, 190, 255))):
        cxp, cyp, rp = mx0 + cxr * mw, top + cyr * mh, r * mw
        for a in range(0, 360, 8):
            c.arc(cxp, cyp, rp, a, a + 5, col, 2.2)
    c.arc(ox, oy, 0.50 * mh, 200, 340, WHITE, 1.6)
    for a in range(200, 341, 10):
        th = math.radians(a)
        L = 0.03 * mh if a % 30 == 0 else 0.015 * mh
        c.line([(ox + 0.50 * mh * math.cos(th), oy + 0.50 * mh * math.sin(th)),
                (ox + (0.50 * mh - L) * math.cos(th), oy + (0.50 * mh - L) * math.sin(th))], WHITE, 1.6)
    c.text(ox - 0.32 * mh, oy - 0.36 * mh, "10", 0.030 * H, WHITE)
    # flight plan (magenta active leg, white legs) with waypoint symbols
    wps = [(0.52, 0.80), (0.47, 0.52), (0.60, 0.30), (0.72, 0.12), (0.88, 0.02)]
    P = [(mx0 + a * mw, top + b * mh) for a, b in wps]
    c.line(P[:2], MAGENTA, 4.0)
    c.line(P[1:], WHITE, 3.0)
    for k, (x, y) in enumerate(P[1:]):
        c.poly([(x, y - 9), (x + 9, y), (x, y + 9), (x - 9, y)], fill=None, outline=WHITE if k else MAGENTA, width=2.5)
        c.marks(x + 16, y - 4, 1, 0.022 * H, WHITE, seed=500 + k)
    # airports (cyan circles with runway ticks), a few numeric labels
    rng = np.random.default_rng(31)
    for _ in range(6):
        x, y = mx0 + rng.uniform(0.05, 0.95) * mw, top + rng.uniform(0.05, 0.9) * mh
        c.circle(x, y, 8, outline=CYAN, width=2.4)
        c.line([(x - 6, y + 5), (x + 6, y - 5)], CYAN, 2.4)
        c.marks(x + 12, y + 12, 1, 0.018 * H, CYAN, seed=int(x))
    for _ in range(8):
        x, y = mx0 + rng.uniform(0.05, 0.9) * mw, top + rng.uniform(0.05, 0.9) * mh
        c.text(x, y, f"{int(rng.uniform(20, 99)) * 100}", 0.020 * H, (60, 50, 40), anchor="lm")
    c.poly([(ox, oy - 18), (ox - 13, oy + 12), (ox, oy + 5), (ox + 13, oy + 12)], fill=WHITE, outline=(0, 0, 0),
           width=1.5)
    # map top bar
    c.rect(mx0, 0, W, top, fill=(8, 9, 12))
    for k, (v, col) in enumerate((("12.4", MAGENTA), ("292", MAGENTA), ("251", GREEN), ("0:42", WHITE),
                                  ("412", WHITE))):
        fx = mx0 + (0.02 + 0.19 * k) * mw
        c.marks(fx, 0.5 * top, 1, 0.24 * top, GREY, seed=600 + k)
        c.text(fx + 0.15 * mw, 0.5 * top, v, 0.44 * top, col, anchor="rm")
    # vertical profile
    vy0 = top + mh
    c.rect(mx0, vy0, W, H, fill=(14, 16, 22))
    xs = np.linspace(mx0 + 0.07 * mw, W, 200)
    prof = _noise1(200, (40, 15, 6), 44)
    ys = vy0 + vp * (0.95 - 0.55 * prof)
    c.poly(list(zip(xs, ys)) + [(W, H), (mx0 + 0.07 * mw, H)], fill=(124, 92, 58))
    c.line(list(zip(xs, ys)), (170, 130, 86), 1.5)
    c.line([(mx0 + 0.07 * mw, vy0 + 0.30 * vp), (mx0 + 0.45 * mw, vy0 + 0.30 * vp), (mx0 + 0.60 * mw, vy0 + 0.22 * vp),
            (W, vy0 + 0.22 * vp)], CYAN, 2.5)
    c.poly([(mx0 + 0.09 * mw, vy0 + 0.30 * vp), (mx0 + 0.075 * mw, vy0 + 0.26 * vp),
            (mx0 + 0.075 * mw, vy0 + 0.34 * vp)], fill=WHITE)
    for k, v in enumerate(("14000", "10000", "6000")):
        yy = vy0 + (0.18 + 0.30 * k) * vp
        c.text(mx0 + 0.06 * mw, yy, v, 0.024 * H, WHITE, anchor="rm")
        c.line([(mx0 + 0.07 * mw, yy), (W, yy)], (50, 56, 66), 1.0)
    c.line([(mx0, vy0), (W, vy0)], LINE, 2)
    return c.final()


# ------------------------------------------------------------------------------------------------------------ SDU
def _glyph(c: Canvas, x, y, s, kind, col):
    if kind == 0:                                                   # aircraft
        c.poly([(x, y - s), (x + 0.2 * s, y - 0.2 * s), (x + s, y + 0.1 * s), (x + s, y + 0.3 * s), (x + 0.2 * s, y + 0.1 * s),
                (x + 0.15 * s, y + 0.7 * s), (x + 0.4 * s, y + s), (x - 0.4 * s, y + s), (x - 0.15 * s, y + 0.7 * s),
                (x - 0.2 * s, y + 0.1 * s), (x - s, y + 0.3 * s), (x - s, y + 0.1 * s), (x - 0.2 * s, y - 0.2 * s)],
               fill=col)
    elif kind == 1:                                                 # map / waypoint
        c.poly([(x, y - s), (x + s, y), (x, y + s), (x - s, y)], outline=col, width=3)
        c.circle(x, y, 0.2 * s, fill=col)
    elif kind == 2:                                                 # radio waves
        for r in (0.35, 0.7, 1.0):
            c.arc(x - 0.5 * s, y, r * s, -45, 45, col, 3)
        c.circle(x - 0.5 * s, y, 0.15 * s, fill=col)
    elif kind == 3:                                                 # list
        for k in range(3):
            c.rect(x - s, y - 0.7 * s + k * 0.6 * s, x + s, y - 0.45 * s + k * 0.6 * s, fill=col)
    elif kind == 4:                                                 # gauge
        c.arc(x, y + 0.3 * s, s, 200, 340, col, 3)
        c.line([(x, y + 0.3 * s), (x + 0.6 * s, y - 0.4 * s)], col, 3)
    elif kind == 5:                                                 # sun / brightness
        c.circle(x, y, 0.45 * s, outline=col, width=3)
        for a in range(0, 360, 45):
            th = math.radians(a)
            c.line([(x + 0.65 * s * math.cos(th), y + 0.65 * s * math.sin(th)),
                    (x + s * math.cos(th), y + s * math.sin(th))], col, 3)
    elif kind == 6:                                                 # weather / cloud
        for dx, r in ((-0.4, 0.45), (0.1, 0.6), (0.55, 0.4)):
            c.circle(x + dx * s, y, r * s, fill=col)
    else:                                                           # gear / settings
        c.circle(x, y, 0.55 * s, outline=col, width=4)
        for a in range(0, 360, 60):
            th = math.radians(a)
            c.line([(x + 0.55 * s * math.cos(th), y + 0.55 * s * math.sin(th)),
                    (x + 0.95 * s * math.cos(th), y + 0.95 * s * math.sin(th))], col, 5)


def gtc_page(variant=0):
    W, H = SIZES["sdu"]
    c = Canvas(W, H, bg=(6, 8, 12))
    # status bar: COM / NAV frequencies (numerals), transponder
    sb = 0.10 * H
    c.rect(0, 0, W, sb, fill=(18, 22, 30))
    for k, (v, col) in enumerate((("118.975", GREEN), ("121.500", WHITE))):
        c.text(0.04 * W, (0.28 + 0.44 * k) * sb, v, 0.30 * sb, col, anchor="lm")
    c.text(0.96 * W, 0.28 * sb, "7000", 0.30 * sb, WHITE, anchor="rm")
    c.marks(0.60 * W, 0.72 * sb, 1, 0.20 * sb, GREEN, seed=700 + variant)
    # page title bar
    tb = 0.055 * H
    c.rect(0, sb, W, sb + tb, fill=(34, 40, 52))
    c.marks(0.36 * W, sb + 0.5 * tb, 1, 0.34 * tb, WHITE, seed=710 + variant)
    # button grid
    cols, rows = 3, 5
    gx0, gy0, gx1, gy1 = 0.03 * W, sb + tb + 0.015 * H, 0.97 * W, 0.86 * H
    bw, bh = (gx1 - gx0) / cols, (gy1 - gy0) / rows
    rng = np.random.default_rng(800 + variant)
    for i in range(rows):
        for j in range(cols):
            x, y = gx0 + j * bw, gy0 + i * bh
            hi = rng.random() < 0.18
            fill = (44, 70, 104) if hi else (36, 42, 54)
            c.rect(x + 5, y + 5, x + bw - 5, y + bh - 5, fill=fill, outline=(84, 96, 116), width=1.5, r=10)
            c.rect(x + 7, y + 7, x + bw - 7, y + 0.45 * bh, fill=(255, 255, 255, 14), r=8)
            gc = CYAN if rng.random() < 0.55 else WHITE
            _glyph(c, x + 0.5 * bw, y + 0.40 * bh, 0.20 * min(bw, bh), int(rng.integers(0, 8)), gc)
            L = bw * rng.uniform(0.35, 0.62)
            c.rect(x + 0.5 * (bw - L), y + 0.76 * bh, x + 0.5 * (bw + L), y + 0.83 * bh, fill=(206, 212, 222), r=3)
            if rng.random() < 0.3:
                c.text(x + bw - 14, y + 16, f"{int(rng.integers(1, 99))}", 0.09 * bh, GREEN, anchor="rt")
    # bottom row: home / back / knob hints
    by = 0.88 * H
    for k in range(4):
        x = 0.03 * W + k * 0.235 * W
        c.rect(x + 4, by, x + 0.235 * W - 4, 0.985 * H, fill=(28, 32, 40), outline=(70, 80, 96), width=1.2, r=8)
        _glyph(c, x + 0.1175 * W, by + 0.045 * H, 0.030 * H, [3, 1, 5, 7][k], WHITE)
    return c.final()


# ------------------------------------------------------------------------------------------------------------ API
PAGES = {"pfd_L": lambda: pfd_page(-1), "mfd": mfd_page, "pfd_R": lambda: pfd_page(1),
         "sdu_L": lambda: gtc_page(0), "sdu_R": lambda: gtc_page(1)}

# GLB texture atlas: one JPEG (4:4:4, quality 90) holding the five pages, PDUs 1016 px wide (3.4 px / mm on the
# 302 mm active area), SDUs 400 px (4.3 px / mm); 16 px gutters filled by edge-extending each page so the mip levels do
# not bleed one page into its neighbour.  ATLAS['rects']: page -> (x0, y0, x1, y1) pixels, y down (glTF UV convention).
ATLAS = dict(size=(2048, 1296), quality=90,
             rects={"pfd_L": (0, 0, 1016, 633), "mfd": (1032, 0, 2048, 633), "pfd_R": (0, 649, 1016, 1282),
                    "sdu_L": (1032, 649, 1432, 1291), "sdu_R": (1448, 649, 1848, 1291)})


def _key():
    return hashlib.sha1(Path(__file__).read_bytes()).hexdigest()[:10]


def pages(out_dir=None, names=None):
    """{name: png path} of the display pages, drawn once per version of this file (cached in out_dir)."""
    out_dir = Path(out_dir or OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _key()
    out = {}
    for n in names or PAGES:
        p = out_dir / f"{n}_{key}.png"
        if not p.exists():
            PAGES[n]().save(p)
        out[n] = p
    return out


def atlas(out_dir=None):
    """(JPEG bytes, ATLAS) of the five pages packed into one texture, cached in out_dir per version of this file."""
    from PIL import Image
    out_dir = Path(out_dir or OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"atlas_{_key()}.jpg"
    if not path.exists():
        W, H = ATLAS["size"]
        im = Image.new("RGB", (W, H), BG)
        src = pages(out_dir)
        for n, (x0, y0, x1, y1) in ATLAS["rects"].items():
            pg = Image.open(src[n]).convert("RGB")
            g = 8                                                # edge-extend into the gutter, then the page itself
            ex = pg.resize((x1 - x0 + 2 * g, y1 - y0 + 2 * g), Image.LANCZOS)
            im.paste(ex.crop((max(0, g - x0), max(0, g - y0), ex.width - max(0, x1 + g - W),
                              ex.height - max(0, y1 + g - H))), (max(0, x0 - g), max(0, y0 - g)))
            im.paste(pg.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))
        tmp = path.with_suffix(".tmp")
        im.save(tmp, "JPEG", quality=int(ATLAS["quality"]), subsampling=0, optimize=True)
        tmp.replace(path)
    return path.read_bytes(), ATLAS


def uv_rect(name, s, t):
    """Atlas UVs (glTF: origin top left, v down) of page `name` at the fractions s (right) / t (up) of its active area,
    half a texel inside the page's rectangle."""
    W, H = ATLAS["size"]
    x0, y0, x1, y1 = ATLAS["rects"][name]
    s, t = np.clip(np.asarray(s, float), 0.0, 1.0), np.clip(np.asarray(t, float), 0.0, 1.0)
    u = (x0 + 0.5 + s * (x1 - x0 - 1.0)) / W
    v = (y0 + 0.5 + (1.0 - t) * (y1 - y0 - 1.0)) / H
    return np.stack([u, v], -1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    for n, p in pages(a.out).items():
        print(n, p)
    data, _ = atlas(a.out)
    print(f"atlas {ATLAS['size'][0]} x {ATLAS['size'][1]}: {len(data) / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
