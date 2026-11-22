"""The 16 scene renderers.  Each is f(fig, ctx, t) and draws one frame at time t (s);
ctx.cue(name) is the time the narration reaches {name}.  All numbers drawn come from
data/ (zeta.py) or are recomputed here from first principles."""
import json
import math
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import hsv_to_rgb
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

from render import MONO, PAL, H, W, clamp, ease, overlay, ramp, window

HERE = os.path.dirname(os.path.abspath(__file__))
D = dict(np.load(os.path.join(HERE, "data", "zeta_data.npz")))  # eager: lazy NpzFile handles break across forked workers
with open(os.path.join(HERE, "data", "numbers.json")) as _f:
    NUM = json.load(_f)
with open(os.path.join(HERE, "data", "lean_tree.json")) as _f:
    TREE = json.load(_f)
GAM = D["gammas"]
SCENE_FUNCS = {}


def scene(sid):
    def deco(f):
        SCENE_FUNCS[sid] = f
        return f
    return deco


# ------------------------------------------------------------------------------ helpers
def axes(fig, rect, xlim=None, ylim=None, grid=True, spines=("left", "bottom")):
    ax = fig.add_axes(rect)
    ax.set_facecolor("none")
    for k, sp in ax.spines.items():
        sp.set_visible(k in spines)
        sp.set_color(PAL["faint"])
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    if grid:
        ax.grid(True, color=PAL["grid"], lw=1, alpha=0.6)
        ax.set_axisbelow(True)
    ax.tick_params(length=6, width=1.2)
    return ax


def txt(ov, x, y, s, size=30, color=None, a=1.0, ha="left", va="center", weight="normal", **kw):
    if a <= 0.003:
        return None
    return ov.text(x, y, s, fontsize=size, color=color or PAL["text"], alpha=clamp(a), ha=ha, va=va,
                   fontweight=weight, **kw)


def card(ov, x, y, w, h, a=1.0, fc=None, ec=None, lw=1.5, r=18):
    if a <= 0.003:
        return
    ov.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc or PAL["panel"], ec=ec or PAL["faint"], lw=lw, alpha=clamp(a)))


def code_panel(ov, x, y, w, lines, a=1.0, size=23, label=None, line_h=40):
    """Monospace panel; lines are (text, color) or text.  (x, y) = top-left."""
    if a <= 0.003:
        return
    h = line_h * len(lines) + 34 + (34 if label else 0)
    card(ov, x, y - h, w, h, a=a * 0.96, fc="#0a0e14", ec=PAL["grid"])
    yy = y - 30
    if label:
        txt(ov, x + 24, yy, label, size=17, color=PAL["muted"], a=a)
        yy -= 36
    for ln in lines:
        s, c = (ln, PAL["text"]) if isinstance(ln, str) else ln
        ov.text(x + 24, yy, s, fontsize=size, color=c, alpha=clamp(a), ha="left", va="center",
                family=MONO)
        yy -= line_h


def quote(ov, x, y, w, text, who, a=1.0, size=30, lines=None):
    if a <= 0.003:
        return
    lines = lines or wrap(text, int(w / (size * 0.56)))
    h = 52 * len(lines) + 110
    card(ov, x, y - h, w, h, a=a, fc=PAL["bg2"], ec=PAL["gold"], lw=2)
    txt(ov, x + 30, y - 48, "“", size=70, color=PAL["gold"], a=a, va="center")
    for i, ln in enumerate(lines):
        txt(ov, x + 80, y - 52 - i * 52, ln, size=size, a=a, style="italic")
    txt(ov, x + w - 30, y - h + 36, who, size=20, color=PAL["muted"], a=a, ha="right")


def wrap(s, n):
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n and cur:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out


def arrow(ov, p0, p1, color=None, a=1.0, lw=3, ms=26, style="-|>", rad=0.0):
    if a <= 0.003:
        return
    ov.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=ms, lw=lw,
                                 color=color or PAL["muted"], alpha=clamp(a),
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0))


def tick(ov, x, y, a=1.0, size=34, color=None):
    txt(ov, x, y, "✓", size=size, color=color or PAL["green"], a=a, ha="center", weight="bold")


def label_ax(ax, xl=None, yl=None, size=24):
    if xl:
        ax.set_xlabel(xl, fontsize=size, color=PAL["muted"], labelpad=8)
    if yl:
        ax.set_ylabel(yl, fontsize=size, color=PAL["muted"], labelpad=8)


def fmt_int(n):
    return f"{n:,}"


def cue(ctx, name, default=None):
    return ctx.cue(name, default)


# ------------------------------------------------------------------------------ cached images
_DOM = None


def domain_rgb():
    """Domain colouring of zeta: hue = arg, ring shading = log2 |zeta|, darkened for the theme."""
    global _DOM
    if _DOM is None:
        z = D["dom_z"].astype(complex)
        hue = (np.angle(z) / (2 * np.pi) + 0.58) % 1.0  # zeta ~ 1 (far right) shows as calm blue
        lm = np.log2(np.abs(z) + 1e-300)
        ring = lm - np.floor(lm)
        val = 0.52 + 0.30 * ring ** 0.7
        sat = np.full_like(val, 0.55)
        rgb = hsv_to_rgb(np.dstack([hue, sat, val]))
        # small |zeta| -> darker, near zeros a black pin
        near = np.clip(np.abs(z) / 0.25, 0, 1) ** 0.5
        rgb *= (0.15 + 0.85 * near)[..., None]
        _DOM = rgb
    return _DOM


DOM_EXT = (float(D["dom_sig"][0]), float(D["dom_sig"][-1]), float(D["dom_t"][0]), float(D["dom_t"][-1]))


PLANE_RECT = [0.05, 0.19, 0.32, 0.73]
PLANE_X, PLANE_Y = (-11, 9), (-2, 34)


def plane_ax(fig, rect=PLANE_RECT, a=1.0):
    ax = axes(fig, rect, xlim=PLANE_X, ylim=PLANE_Y, grid=False,
              spines=("left", "bottom", "right", "top"))
    ax.imshow(domain_rgb(), extent=DOM_EXT, origin="lower", aspect="equal", alpha=clamp(a),
              interpolation="bilinear")
    ax.set_xlim(*PLANE_X)
    ax.set_ylim(*PLANE_Y)
    ax.set_xticks([-10, -6, -2, 0, 1, 4, 8])
    ax.set_yticks([0, 10, 20, 30])
    ax.tick_params(labelsize=18)
    label_ax(ax, "real part  σ", "imaginary part  t", size=20)
    return ax


# ==============================================================================
# 0. Cold open
# ==============================================================================
def zero_column(ov, x, y0, y1, a=1.0, n_show=None, tmax=50.0, glow=True):
    ov.plot([x, x], [y0, y1], color=PAL["cyan"], lw=2.5, alpha=0.55 * a)
    gs = GAM[GAM < tmax]
    if n_show is not None:
        gs = gs[:n_show]
    ys = y0 + (gs / tmax) * (y1 - y0)
    if glow:
        ov.scatter([x] * len(ys), ys, s=420, color=PAL["gold"], alpha=0.12 * a, lw=0)
    ov.scatter([x] * len(ys), ys, s=60, color=PAL["gold"], alpha=a, lw=0, zorder=5)


@scene("s01_open")
def s01(fig, ctx, t):
    ov = overlay(fig)
    c_lean, c_joint, c_plan = cue(ctx, "lean"), cue(ctx, "joint"), cue(ctx, "plan")
    # background: zeros climbing the critical line
    n = int(clamp(t / 12) * 12) + 1
    zero_column(ov, 1560, 180, 1000, a=0.9, n_show=n, tmax=50)
    txt(ov, 1590, 205, "Re(s) = ½", size=20, color=PAL["cyan"], a=0.7)
    a_title = ramp(t, 0.3, 0.8) * (1 - ramp(t, c_plan - 0.2, 0.6))
    txt(ov, 120, 820, "The Riemann Hypothesis", size=66, weight="bold", a=a_title)
    txt(ov, 124, 735, "zeta, the primes, and a claimed proof", size=34, color=PAL["muted"], a=a_title)
    a1 = ramp(t, 3.0, 0.6) * (1 - ramp(t, c_plan - 0.2, 0.6))
    card(ov, 120, 420, 1300, 210, a=a1)
    txt(ov, 150, 585, "20 November 2026", size=24, color=PAL["gold"], a=a1, weight="semibold")
    txt(ov, 150, 530, "Levent Alpöge, working with Claude: a 4-page note", size=28, a=a1)
    a2 = ramp(t, c_lean, 0.6) * (1 - ramp(t, c_plan - 0.2, 0.6))
    txt(ov, 150, 470, "and a claimed proof in Lean: 17,374,215 lines, no comments, no written proof", size=28,
        a=a2, color=PAL["cyan"])
    a3 = ramp(t, c_joint, 0.6) * (1 - ramp(t, c_plan - 0.2, 0.6))
    card(ov, 120, 180, 1300, 210, a=a3)
    txt(ov, 150, 345, "21 November 2026", size=24, color=PAL["gold"], a=a3, weight="semibold")
    txt(ov, 150, 290, "Lean and Mathlib communities, endorsed by the Lean FRO and the Mathlib Initiative:", size=26, a=a3)
    txt(ov, 150, 230, "\u201cWe have full confidence that Alpöge\u2019s proof \u2026 is correct\u201d", size=28,
        a=a3, color=PAL["muted"])
    # agenda
    items = ["the zeta function", "the hypothesis", "why primes care", "a world where it is proved",
             "the idea of the claimed proof", "how it was checked, and what is still open"]
    for i, s in enumerate(items):
        a = ramp(t, c_plan + 0.4 + 0.45 * i, 0.5)
        txt(ov, 160, 820 - i * 92, f"{i+1}", size=34, color=PAL["gold"], a=a, weight="bold", ha="center")
        txt(ov, 210, 820 - i * 92, s, size=38, a=a)


# ==============================================================================
# 1. Counting primes
# ==============================================================================
PRIMES = D["primes"]


def pi_of(x):
    return np.searchsorted(PRIMES, x, side="right")


@scene("s02_primes")
def s02(fig, ctx, t):
    ov = overlay(fig)
    c_grid, c_st, c_zoom = cue(ctx, "grid"), cue(ctx, "staircase"), cue(ctx, "zoom")
    c_gauss, c_table, c_q = cue(ctx, "gauss"), cue(ctx, "table"), cue(ctx, "question")
    # number grid 1..100
    a_grid = 1 - ramp(t, c_st - 0.3, 0.6)
    if a_grid > 0:
        named = [2, 3, 5, 7, 11]
        for k in range(1, 101):
            r, c = divmod(k - 1, 10)
            x, y = 560 + c * 82, 880 - r * 66
            isp = k in set(PRIMES[:25].tolist())
            lit = 0.0
            if isp:
                if k in named:
                    lit = ramp(t, 0.6 + 0.55 * named.index(k), 0.3)
                else:
                    lit = ramp(t, c_grid - 0.5 + 0.04 * k, 0.3)
            col = PAL["coral"] if lit > 0.5 else PAL["faint"]
            if lit > 0:
                ov.add_patch(Circle((x, y), 27, color=PAL["coral"], alpha=0.22 * lit * a_grid))
            txt(ov, x, y, str(k), size=24, color=col, a=a_grid * (0.55 + 0.45 * lit), ha="center",
                weight="semibold" if lit > 0.5 else "normal")
    if t < c_st - 0.3:
        return
    a_plot = ramp(t, c_st - 0.3, 0.6)
    # x range: 0..100, then grows to 1e6 at "zoom"
    z = ease((t - c_zoom) / 3.5) if t > c_zoom else 0.0
    xmax = 100 * (1e6 / 100) ** z
    right = 0.62 if t > c_table - 0.3 else 0.86
    ax = axes(fig, [0.10, 0.22, right - 0.02, 0.66], xlim=(0, xmax), ylim=(0, max(30, pi_of(xmax) * 1.12)))
    for sp in ax.spines.values():
        sp.set_alpha(a_plot)
    xs = np.linspace(0, xmax, 3000)
    frac = clamp((t - c_st) / 2.0)
    m = xs <= max(2, xmax * frac if z == 0 else xmax)
    ax.step(xs[m], pi_of(xs[m]), where="post", color=PAL["coral"], lw=3, alpha=a_plot, label="π(x)")
    if t > c_gauss:
        ag = ramp(t, c_gauss, 0.8)
        xx = np.linspace(2.0, xmax, 800)
        from zeta import li
        ax.plot(xx, li(xx), color=PAL["gold"], lw=3, ls=(0, (6, 4)), alpha=ag, label="li(x)")
        txt(ov, 240, 860, r"chance that a number near $x$ is prime  ≈  $1/\ln x$", size=30, a=ag)
        txt(ov, 240, 790, r"$\mathrm{li}(x)=1.045\ldots+\int_2^{x}\frac{du}{\ln u}$", size=34, a=ag,
            color=PAL["gold"])
    ax.ticklabel_format(style="plain", axis="both")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    label_ax(ax, "x", "number of primes ≤ x")
    txt(ov, 1270 if right > 0.7 else 960, 300, "π(x)", size=36, color=PAL["coral"], a=a_plot,
        weight="bold")
    if t > c_table - 0.3:
        at = ramp(t, c_table - 0.3, 0.6)
        x0, y0 = 1335, 860
        card(ov, x0 - 30, 300, 580, 610, a=at)
        txt(ov, x0, y0, "x", size=24, color=PAL["muted"], a=at, weight="semibold")
        txt(ov, x0 + 250, y0, "π(x)", size=24, color=PAL["coral"], a=at, ha="right", weight="semibold")
        txt(ov, x0 + 470, y0, "li(x)", size=24, color=PAL["gold"], a=at, ha="right", weight="semibold")
        for i, (x, p, l, g) in enumerate(NUM["pi_table"]):
            yy = y0 - 70 - i * 66
            a_r = at * ramp(t, c_table + 0.25 * i, 0.4)
            txt(ov, x0, yy, f"10$^{{{int(round(math.log10(x)))}}}$", size=26, a=a_r)
            txt(ov, x0 + 250, yy, fmt_int(p), size=26, a=a_r, ha="right")
            txt(ov, x0 + 470, yy, fmt_int(int(round(l))), size=26, a=a_r, ha="right", color=PAL["muted"])
        aq = ramp(t, c_q, 0.6)
        diff = NUM["pi_table"][-1][2] - NUM["pi_table"][-1][1]
        txt(ov, x0, 345, f"error at 10$^6$: {diff:.0f}  ({100*diff/NUM['pi_table'][-1][1]:.2f} %)", size=24,
            a=aq, color=PAL["cyan"])


# ==============================================================================
# 2. Euler
# ==============================================================================
@scene("s03_euler")
def s03(fig, ctx, t):
    ov = overlay(fig)
    c_basel, c_h, c_prod, c_zeta = cue(ctx, "basel"), cue(ctx, "harmonic"), cue(ctx, "product"), cue(ctx, "zeta")
    c_exp = cue(ctx, "expand")
    a_plot = window(t, c_basel - 0.4, c_prod + 0.2, 0.6)
    if a_plot > 0:
        Nmax = 60
        ax = axes(fig, [0.08, 0.24, 0.84, 0.60], xlim=(0, Nmax + 1), ylim=(0, 5.2))
        n = np.arange(1, Nmax + 1)
        s2 = np.cumsum(1.0 / n ** 2)
        h1 = np.cumsum(1.0 / n)
        k = int(clamp((t - c_basel) / 6.0) * Nmax)
        if k > 0:
            ax.bar(n[:k], s2[:k], color=PAL["cyan"], width=0.7, alpha=0.9 * a_plot)
        ax.axhline(math.pi ** 2 / 6, color=PAL["gold"], ls="--", lw=2.5, alpha=a_plot)
        ax.text(Nmax + 0.5, math.pi ** 2 / 6 + 0.12, r"$\pi^2/6 = 1.6449\ldots$", ha="right", fontsize=28,
                color=PAL["gold"], alpha=a_plot)
        if t > c_h:
            kh = int(clamp((t - c_h) / 3.0) * Nmax)
            ax.plot(n[:max(kh, 1)], h1[:max(kh, 1)], color=PAL["coral"], lw=3.5, alpha=a_plot)
            ax.text(Nmax, h1[-1] + 0.2, r"$1+\frac{1}{2}+\frac{1}{3}+\cdots$ grows forever", ha="right",
                    fontsize=26, color=PAL["coral"], alpha=a_plot * ramp(t, c_h + 1, 0.5))
        label_ax(ax, "number of terms", "partial sum")
        for sp in ax.spines.values():
            sp.set_alpha(a_plot)
        ax.tick_params(colors=PAL["muted"])
        txt(ov, 210, 830, r"$1+\frac{1}{4}+\frac{1}{9}+\frac{1}{16}+\cdots$", size=40, color=PAL["cyan"],
            a=a_plot * ramp(t, c_basel, 0.5))
    a_eq = ramp(t, c_prod, 0.8)
    if a_eq > 0:
        txt(ov, 1000, 700, r"$\sum_{n=1}^{\infty}\ \frac{1}{n^{s}}\ \ =\ \ \prod_{p\ \mathrm{prime}}\ \frac{1}{1-p^{-s}}$",
            size=64, a=a_eq, ha="center")
        txt(ov, 1560, 700, "(for s > 1)", size=28, a=a_eq, ha="left", color=PAL["muted"])
        txt(ov, W / 2, 490, r"$\frac{1}{1-2^{-s}} = 1 + 2^{-s} + 4^{-s} + 8^{-s} + \cdots$,     $\frac{1}{1-3^{-s}} = 1 + 3^{-s} + 9^{-s} + \cdots$",
            size=36, a=a_eq * ramp(t, c_exp, 0.6), ha="center", color=PAL["muted"])
        txt(ov, W / 2, 395, "multiply out: 12 = 2 · 2 · 3 gives 4⁻ˢ · 3⁻ˢ = 12⁻ˢ, exactly once (one factorisation per n)",
            size=28, a=a_eq * ramp(t, c_exp + 2.5, 0.6), ha="center", color=PAL["muted"])
    a_z = ramp(t, c_zeta, 0.6)
    if a_z > 0:
        txt(ov, 560, 700, "ζ(s) =", size=56, color=PAL["gold"], a=a_z, ha="right", weight="bold")
        txt(ov, 790, 300, "all whole numbers", size=30, color=PAL["cyan"], a=a_z, ha="center")
        txt(ov, 1190, 300, "only the primes", size=30, color=PAL["coral"], a=a_z, ha="center")


# ==============================================================================
# 3. Spinning arrows
# ==============================================================================
S_CONV = 2 + 3j
SPIRAL = D["spiral_conv"]


@scene("s04_complex")
def s04(fig, ctx, t):
    ov = overlay(fig)
    c_ph, c_sp, c_cv = cue(ctx, "phasor"), cue(ctx, "spiral"), cue(ctx, "converge")
    a_eq = ramp(t, 1.0, 0.8)
    txt(ov, 120, 880, r"$s=\sigma+it$", size=48, a=a_eq, color=PAL["gold"])
    txt(ov, 120, 790, r"$n^{-s} = n^{-\sigma}\cdot e^{-i\,t\ln n}$", size=44, a=ramp(t, c_ph, 0.8))
    txt(ov, 120, 720, "length  ×  rotation", size=28, a=ramp(t, c_ph + 1.5, 0.6), color=PAL["muted"])
    txt(ov, 120, 610, r"example: $s = 2 + 3i$", size=30, a=ramp(t, c_ph + 2.5, 0.6), color=PAL["cyan"])
    # phasor panel: arrows n^-s from the origin, n = 1..6
    if t < c_sp:
        a = ramp(t, c_ph + 1.0, 0.6)
        ax = axes(fig, [0.52, 0.22, 0.42, 0.70], xlim=(-1.2, 1.2), ylim=(-1.05, 1.15), grid=True,
                  spines=())
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        th = np.linspace(0, 2 * np.pi, 200)
        ax.plot(np.cos(th), np.sin(th), color=PAL["faint"], lw=1.5, alpha=a)
        rot = clamp((t - c_ph - 1.0) / 4.0)
        for nn in range(1, 7):
            v = nn ** (-S_CONV.real) * np.exp(-1j * S_CONV.imag * math.log(nn) * rot)
            col = plt.cm.cool(0.15 * (nn - 1))
            ax.annotate("", xy=(v.real, v.imag), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color=col, lw=3, alpha=a, mutation_scale=22))
            ax.text(v.real * 1.08 + 0.02, v.imag * 1.08 + 0.03, f"n={nn}", fontsize=18, color=col, alpha=a)
        return
    # spiral panel
    a = ramp(t, c_sp, 0.6)
    z_end = SPIRAL[-1]
    zf = ease((t - c_sp - 2.5) / 3.0)
    cx, cy = (1 - zf) * 0.53 + zf * z_end.real, (1 - zf) * (-0.12) + zf * z_end.imag
    hw = (1 - zf) * 0.62 + zf * 0.22
    ax = axes(fig, [0.48, 0.20, 0.48, 0.74], xlim=(cx - hw, cx + hw), ylim=(cy - hw * 0.8, cy + hw * 0.8),
              grid=True, spines=())
    ax.set_xticks([0, 0.5, 1])
    ax.set_yticks([-0.5, 0, 0.25])
    ax.tick_params(labelsize=16)
    ax.axhline(0, color=PAL["faint"], lw=1)
    ax.axvline(0, color=PAL["faint"], lw=1)
    k = int(2 + clamp((t - c_sp) / 5.0) ** 1.6 * (len(SPIRAL) - 3))
    pts = SPIRAL[:k]
    for i in range(min(k - 1, 12)):
        p0, p1 = pts[i], pts[i + 1]
        col = plt.cm.cool(0.08 * i)
        ax.annotate("", xy=(p1.real, p1.imag), xytext=(p0.real, p0.imag),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=3.5, alpha=a, mutation_scale=22))
    if k > 13:
        ax.plot(pts[12:].real, pts[12:].imag, color=PAL["violet"], lw=2.4, alpha=a)
    ax.scatter([pts[-1].real], [pts[-1].imag], s=60, color=PAL["white"], zorder=5, alpha=a)
    ac = ramp(t, c_cv, 0.6)
    if ac > 0:
        ax.scatter([z_end.real], [z_end.imag], s=600, color=PAL["gold"], alpha=0.25 * ac, lw=0)
        ax.scatter([z_end.real], [z_end.imag], s=90, color=PAL["gold"], alpha=ac, zorder=6)
        zr, zi = NUM["zeta_2p3i"]
        ax.text(z_end.real - 0.02, z_end.imag - 0.11, f"ζ(2+3i) = {zr:.3f} {zi:+.3f}i".replace("+-", "−"),
                fontsize=24, color=PAL["gold"], alpha=ac, ha="right")
    txt(ov, 120, 480, r"partial sums  $1 + 2^{-s} + 3^{-s} + \cdots$", size=28, a=a, color=PAL["muted"])
    txt(ov, 120, 420, f"terms shown: {k-1:,}", size=26, a=a, color=PAL["violet"])


# ==============================================================================
# 4. Continuation and the domain-colouring map
# ==============================================================================
@scene("s05_continue")
def s05(fig, ctx, t):
    ov = overlay(fig)
    c_div, c_geom, c_uni, c_map, c_z = (cue(ctx, k) for k in ("diverge", "geom", "unique", "map", "zeros"))
    a1 = window(t, c_div - 0.3, c_geom, 0.5)
    if a1 > 0:
        s = 0.5 + 10j
        n = np.arange(1, 1201)
        ps = np.concatenate([[0], np.cumsum(n ** -s)])
        k = int(2 + clamp((t - c_div) / 4.0) * (len(ps) - 2))
        ax = axes(fig, [0.42, 0.20, 0.50, 0.72], grid=True, spines=())
        ax.plot(ps[:k].real, ps[:k].imag, color=PAL["coral"], lw=1.8, alpha=a1)
        ax.scatter([ps[k - 1].real], [ps[k - 1].imag], s=60, color=PAL["white"], alpha=a1)
        cx = 0.5 * (ps[:k].real.max() + ps[:k].real.min())
        cy = 0.5 * (ps[:k].imag.max() + ps[:k].imag.min())
        lim = 0.62 * max(np.ptp(ps[:k].real), np.ptp(ps[:k].imag), 1.0)
        ax.set_xlim(cx - lim, cx + lim)
        ax.set_ylim(cy - lim * 1.05, cy + lim * 1.05)
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xticks([])
        ax.set_yticks([])
        txt(ov, 120, 860, r"$s=\frac{1}{2}+10i$:  the partial sums wander off", size=32, a=a1, color=PAL["coral"])
        txt(ov, 120, 800, f"terms: {k-1:,}", size=26, a=a1, color=PAL["muted"])
    a2 = window(t, c_geom, c_uni, 0.45)
    if a2 > 0:
        ax = axes(fig, [0.08, 0.25, 0.84, 0.50], xlim=(-3, 3), ylim=(-4, 6))
        x = np.linspace(-3, 3, 1201)
        nn = int(1 + clamp((t - c_geom - 0.5) / 4.0) * 24)
        for j in range(1, nn + 1, 3):
            sn = (1 - x ** (j + 1)) / (1 - x)
            ax.plot(x, sn, color=PAL["cyan"], lw=1.6, alpha=a2 * 0.55)
        with np.errstate(divide="ignore"):
            f = 1 / (1 - x)
        f[np.abs(x - 1) < 0.02] = np.nan
        ax.plot(x, f, color=PAL["gold"], lw=4, alpha=a2 * ramp(t, c_geom + 2, 0.6))
        ax.axvspan(-1, 1, color=PAL["cyan"], alpha=0.07 * a2)
        txt(ov, 200, 890, r"$1+x+x^2+x^3+\cdots\ =\ \dfrac{1}{1-x}$", size=40, a=a2, color=PAL["cyan"])
        txt(ov, 200, 815, "only when −1 < x < 1 (shaded)", size=28, a=a2, color=PAL["muted"])
        txt(ov, 1180, 890, "but 1/(1−x) itself makes sense", size=30, a=a2 * ramp(t, c_geom + 3, 0.6),
            color=PAL["gold"])
        txt(ov, 1180, 845, "for every x ≠ 1", size=30, a=a2 * ramp(t, c_geom + 3, 0.6), color=PAL["gold"])
        label_ax(ax, "x", None)
    a3 = ramp(t, c_uni - 0.2, 0.6)
    if t >= c_uni - 0.3:
        am = ramp(t, c_uni - 0.3, 0.8)
        ax = plane_ax(fig, a=am)
        if t > c_z:
            az = ramp(t, c_z, 0.6)
            ax.scatter([-2, -4, -6, -8, -10], [0] * 5, s=120, facecolor="none", edgecolor="white",
                       lw=2.5, alpha=az)
            gs = GAM[GAM < 34]
            ax.scatter([0.5] * len(gs), gs, s=120, facecolor="none", edgecolor="white", lw=2.5, alpha=az)
        ax.scatter([1], [0], marker="x", s=160, color="white", lw=3, alpha=am)
        ax.text(1.6, 0.6, "pole at s = 1", fontsize=16, color="white", alpha=am)
        txt(ov, 790, 860, "ζ(s), extended to the whole plane", size=36, a=am, weight="semibold")
        txt(ov, 790, 805, "(its analytic continuation; only s = 1 is excluded)", size=26, a=am, color=PAL["muted"])
        am2 = ramp(t, c_map, 0.6)
        txt(ov, 790, 700, "colour = direction (angle) of ζ(s)", size=30, a=am2)
        txt(ov, 790, 645, "rings = size: each ring doubles |ζ(s)|", size=30, a=am2)
        txt(ov, 790, 545, "white circles: zeros (dark meeting points)", size=30, a=ramp(t, c_z, 0.6), color=PAL["white"])
        txt(ov, 790, 495, "(the pole at s = 1 is a bright meeting point)", size=24, a=ramp(t, c_z, 0.6), color=PAL["muted"])


# ==============================================================================
# 5. Zeros
# ==============================================================================
@scene("s06_zeros")
def s06(fig, ctx, t):
    ov = overlay(fig)
    c_tr, c_strip, c_sym, c_line, c_first = (cue(ctx, k) for k in ("trivial", "strip", "symmetry", "line", "first"))
    ax = plane_ax(fig, a=1.0)
    a_tr = ramp(t, c_tr, 0.5)
    ax.scatter([-2, -4, -6, -8, -10], [0] * 5, s=170, facecolor="none", edgecolor="white", lw=3,
               alpha=a_tr)
    for k in (-2, -4, -6):
        ax.text(k, -1.9, str(k), ha="center", fontsize=16, color="white", alpha=a_tr)
    txt(ov, 790, 860, "trivial zeros:  −2, −4, −6, …", size=32, a=a_tr)
    a_st = ramp(t, c_strip, 0.6)
    if a_st > 0:
        ax.axvspan(0, 1, color="white", alpha=0.16 * a_st)
        ax.axvline(0, color="white", lw=1.5, alpha=0.8 * a_st)
        ax.axvline(1, color="white", lw=1.5, alpha=0.8 * a_st)
        txt(ov, 790, 770, "critical strip:  0 < σ < 1", size=32, a=a_st)
        gs = GAM[GAM < 34]
        ax.scatter([0.5] * len(gs), gs, s=110, facecolor="none", edgecolor="white", lw=2.5, alpha=a_st)
    a_sy = ramp(t, c_sym, 0.6)
    if a_sy > 0:
        txt(ov, 790, 690, r"$\zeta(s)\leftrightarrow\zeta(1-s)$  and  $\zeta(\bar{s})=\overline{\zeta(s)}$", size=32, a=a_sy)
        txt(ov, 790, 640, r"together: zeros mirror across $\sigma=\frac{1}{2}$", size=30,
            a=a_sy)
        # schematic: a hypothetical off-line pair and its mirror (inset)
        x0, y0 = 800, 330
        ov.add_patch(Rectangle((x0, y0), 300, 280, color="white", alpha=0.06 * a_sy))
        ov.plot([x0, x0], [y0, y0 + 280], color="white", lw=1.5, alpha=0.6 * a_sy)
        ov.plot([x0 + 300, x0 + 300], [y0, y0 + 280], color="white", lw=1.5, alpha=0.6 * a_sy)
        ov.plot([x0 + 150, x0 + 150], [y0, y0 + 280], color=PAL["cyan"], lw=2, ls="--", alpha=a_sy)
        ov.scatter([x0 + 75, x0 + 225], [y0 + 190, y0 + 190], s=110, color=PAL["coral"], alpha=a_sy)
        arrow(ov, (x0 + 90, y0 + 165), (x0 + 210, y0 + 165), color=PAL["coral"], a=a_sy, rad=0.25)
        txt(ov, x0 + 330, y0 + 225, "if a zero were off the line,", size=24, a=a_sy, color=PAL["muted"])
        txt(ov, x0 + 330, y0 + 190, "its mirror image would be a zero too", size=24, a=a_sy, color=PAL["muted"])
        txt(ov, x0 + 330, y0 + 120, "(hypothetical, not to scale)", size=20, a=a_sy, color=PAL["faint"])
    a_ln = ramp(t, c_line, 0.6)
    if a_ln > 0:
        ax.axvline(0.5, color=PAL["cyan"], lw=3, ls="--", alpha=a_ln)
        gs = GAM[GAM < 34]
        ax.scatter([0.5] * len(gs), gs, s=380, color=PAL["gold"], alpha=0.30 * a_ln, lw=0, zorder=6)
        ax.scatter([0.5] * len(gs), gs, s=70, color=PAL["gold"], alpha=a_ln, lw=0, zorder=7)
        txt(ov, 790, 270, "critical line:  σ = ½", size=32, a=a_ln, color=PAL["cyan"], weight="semibold")
    a_f = ramp(t, c_first, 0.6)
    if a_f > 0:
        ax.scatter([0.5], [GAM[0]], s=600, color=PAL["gold"], alpha=0.35 * a_f, lw=0)
        ax.annotate(f"½ + {GAM[0]:.4f}… i", xy=(0.6, GAM[0]), xytext=(3.3, GAM[0] + 4.5), fontsize=20,
                    color=PAL["gold"], alpha=a_f, arrowprops=dict(arrowstyle="-", color=PAL["gold"], alpha=a_f, lw=2))


# ==============================================================================
# 6. The hypothesis
# ==============================================================================
@scene("s07_rh")
def s07(fig, ctx, t):
    ov = overlay(fig)
    c_state, c_rie, c_z, c_cnt, c_chk, c_pr = (cue(ctx, k) for k in ("state", "riemann", "zplot", "counter", "checked", "prizes"))
    a_s = window(t, c_state - 0.2, c_z, 0.6)
    if a_s > 0:
        txt(ov, W / 2, 720, "Every nontrivial zero of ζ has real part exactly ½.", size=52, a=a_s,
            ha="center", weight="bold")
        txt(ov, W / 2, 620, r"$\zeta(\rho)=0,\ \ 0<\mathrm{Re}\,\rho<1\ \ \Longrightarrow\ \ \mathrm{Re}\,\rho=\frac{1}{2}$",
            size=46, a=a_s * ramp(t, c_state + 1.5, 0.6), ha="center", color=PAL["cyan"])
        ar = ramp(t, c_rie, 0.6)
        quote(ov, 460, 500, 1000, "", "Riemann, 1859 (tr. D. R. Wilkins)", a=ar * a_s, size=30,
              lines=["…it is very probable that all roots are real."])
        txt(ov, W / 2, 295, "(Riemann's roots are values of t, with s = ½ + it: a real t is a zero on the line)", size=24,
            a=ar * a_s, ha="center", color=PAL["muted"])
    if t < c_z - 0.4:
        return
    a = ramp(t, c_z - 0.4, 0.6)
    ax = axes(fig, [0.07, 0.50, 0.86, 0.38], xlim=(0, 60), ylim=(-4.2, 4.2))
    tz, zt = D["tz"], D["zt"]
    tc = 1 + clamp((t - c_z) / 6.0) * 59
    m = tz <= tc
    ax.plot(tz[m], zt[m], color=PAL["cyan"], lw=3, alpha=a)
    ax.axhline(0, color=PAL["muted"], lw=1.2)
    zs = GAM[GAM <= tc]
    ax.scatter(zs, np.zeros_like(zs), s=90, color=PAL["gold"], zorder=5, alpha=a)
    label_ax(ax, "t   (height up the critical line, s = ½ + it)", "Z(t)")
    txt(ov, 150, 905, "Hardy's Z(t):  real on the line,  |Z(t)| = |ζ(½ + it)|", size=28, a=a,
        color=PAL["cyan"])
    a_c = ramp(t, c_cnt, 0.5)
    for i in range(10):
        ai = a_c * ramp(t, c_cnt + 0.9 * min(i, 3) + 0.25 * max(0, i - 3), 0.3)
        txt(ov, 150 + (i % 5) * 330, 405 - (i // 5) * 50, f"{math.floor(GAM[i] * 1e6) / 1e6:.6f}…", size=27, a=ai, color=PAL["gold"],
            family=MONO)
    a_k = ramp(t, c_chk, 0.6)
    card(ov, 130, 190, 780, 115, a=a_k)
    txt(ov, 160, 268, "> 12 trillion zeros checked numerically", size=30, a=a_k, weight="semibold")
    txt(ov, 160, 222, "Platt & Trudgian (2021): every zero up to height 3·10$^{12}$", size=21, a=a_k,
        color=PAL["muted"])
    a_p = ramp(t, c_pr, 0.6)
    card(ov, 960, 190, 830, 115, a=a_p)
    txt(ov, 990, 268, "1900  Hilbert's 8th problem", size=28, a=a_p)
    txt(ov, 990, 222, "2000  Clay Millennium Prize, US$1,000,000", size=28, a=a_p * ramp(t, c_pr + 1.5, 0.5))


# ==============================================================================
# 7. Primes from waves (explicit formula)
# ==============================================================================
@scene("s08_music")
def s08(fig, ctx, t):
    ov = overlay(fig)
    c_f, c_psi, c_w = cue(ctx, "formula"), cue(ctx, "psi"), cue(ctx, "waves")
    adds = [(0, cue(ctx, "add0")), (1, cue(ctx, "add1")), (10, cue(ctx, "add10")),
            (100, cue(ctx, "add100")), (1000, cue(ctx, "add1000"))]
    c_j = cue(ctx, "jumps")
    a_f = ramp(t, c_f, 0.8)
    txt(ov, W / 2, 920,
        r"$\psi(x)\ =\ x\ -\ \sum_{\rho}\ \frac{x^{\rho}}{\rho}\ -\ \ln 2\pi\ -\ \frac{1}{2}\ln\!\left(1-x^{-2}\right)$",
        size=44, a=a_f, ha="center")
    if t < c_psi - 0.3:
        return
    a = ramp(t, c_psi - 0.3, 0.6)
    ax = axes(fig, [0.07, 0.22, 0.86, 0.58], xlim=(2, 100), ylim=(-2, 112))
    xe = D["xe"]
    ax.plot(xe, D["psi_true_e"], color=PAL["coral"], lw=3, alpha=a * (0.35 if t > adds[1][1] else 1.0),
            drawstyle="steps-post")
    label_ax(ax, "x", "ψ(x) = Σ ln p  over prime powers p$^k$ ≤ x")
    if c_w - 0.3 < t < adds[1][1]:
        aw = window(t, c_w - 0.3, adds[1][1], 0.5)
        for j in range(3):
            g = GAM[j]
            rho = 0.5 + 1j * g
            wv = -2 * np.real(np.exp(rho * np.log(xe)) / rho)
            ax.plot(xe, 62 + 14 * j + 45 * wv / np.sqrt(xe), color=plt.cm.cool(0.2 + 0.35 * j), lw=2.2, alpha=aw)
        ax.text(98, 104, "the waves of the first three zero pairs (scaled by 1/√x)", ha="right", fontsize=22,
                color=PAL["muted"], alpha=aw)
        txt(ov, 1060, 380, r"each pair $\frac{1}{2}\pm i\gamma$ subtracts", size=26, a=aw, color=PAL["cyan"])
        txt(ov, 1060, 335, r"$2\sqrt{x}\,\cos(\gamma\ln x-\arg\rho)\,/\,|\rho|$", size=28, a=aw, color=PAL["cyan"])
    # reconstruction: crossfade between successive K
    if t >= adds[0][1] - 0.2:
        cur = 0
        for i, (K, tk) in enumerate(adds):
            if t >= tk:
                cur = i
        K, tk = adds[cur]
        w = ramp(t, tk, 0.6)
        y_new = D[f"recon_{K}"]
        y_old = D[f"recon_{adds[cur - 1][0]}"] if cur > 0 else y_new
        y = (1 - w) * y_old + w * y_new
        ax.plot(xe, y, color=PAL["gold"], lw=2.6, alpha=ramp(t, adds[0][1] - 0.2, 0.5))
        lbl = ("smooth part:  x − ln 2π − ½ ln(1 − x⁻²)" if K == 0 else
               f"smooth part minus waves from {K:,} zero pair{'s' if K > 1 else ''}")
        txt(ov, 1060, 280, lbl, size=26, color=PAL["gold"], a=1, weight="semibold")
    if t > c_j:
        aj = ramp(t, c_j, 0.6)
        pk = D["xpsi"][D["xpsi"] <= 100]
        ax.vlines(pk, -2, 4, color=PAL["white"], lw=1.5, alpha=aj)
        ax.text(3, 6, "prime powers", fontsize=20, color=PAL["white"], alpha=aj)


# ==============================================================================
# 8. Why the line matters: sqrt(x)
# ==============================================================================
_WALK = None


@scene("s09_sqrt")
def s09(fig, ctx, t):
    global _WALK
    ov = overlay(fig)
    c_sz, c_rh, c_wk, c_bd, c_dt = (cue(ctx, k) for k in ("sizes", "rh_eq", "walk", "bound", "data"))
    a1 = window(t, c_sz - 0.3, c_rh + 0.6, 0.6)
    if a1 > 0:
        ax = axes(fig, [0.08, 0.24, 0.84, 0.60], xlim=(0, 10000), ylim=(0, 1100))
        x = np.linspace(0, 10000, 800)
        ax.plot(x, np.sqrt(x), color=PAL["cyan"], lw=4, alpha=a1)
        ax.plot(x, x ** 0.75, color=PAL["coral"], lw=4, alpha=a1 * ramp(t, c_sz + 3, 0.6))
        ax.text(9800, 140, r"$x^{1/2}$: zero on the line", ha="right", fontsize=28, color=PAL["cyan"], alpha=a1)
        ax.text(9800, 1020, r"$x^{3/4}$: a zero at $\sigma = 3/4$ (hypothetical)", ha="right", fontsize=28,
                color=PAL["coral"], alpha=a1 * ramp(t, c_sz + 3, 0.6))
        label_ax(ax, "x", r"growth of one wave ($\propto x^{\mathrm{Re}\,\rho}$)")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    a2 = window(t, c_rh, c_bd, 0.6)
    if a2 > 0 and t > c_rh:
        card(ov, 160, 640, 1600, 230, a=a2)
        txt(ov, W / 2, 800, "Riemann Hypothesis   ⇔   prime-counting error ≈ √x  (up to logs)", size=40,
            a=a2, ha="center", weight="semibold")
        txt(ov, W / 2, 715, r"$\psi(x) = x + O(\sqrt{x}\,\ln^2 x)$        $\pi(x) = \mathrm{li}(x) + O(\sqrt{x}\,\ln x)$",
            size=36, a=a2 * ramp(t, c_rh + 1.5, 0.6), ha="center", color=PAL["cyan"])
        if t > c_wk - 0.3:
            aw = ramp(t, c_wk - 0.3, 0.6)
            if _WALK is None:
                rng = np.random.default_rng(7)
                _WALK = np.concatenate([[0], np.cumsum(rng.choice([-1, 1], 20000))])
            ax = axes(fig, [0.10, 0.20, 0.80, 0.34], xlim=(0, 20000), ylim=(-420, 420))
            k = int(10 + clamp((t - c_wk) / 4.0) * 19990)
            n = np.arange(k)
            ax.plot(n, _WALK[:k], color=PAL["violet"], lw=1.4, alpha=aw)
            nn = np.linspace(0, 20000, 400)
            ax.plot(nn, 2 * np.sqrt(nn), color=PAL["gold"], ls="--", lw=2.5, alpha=aw)
            ax.plot(nn, -2 * np.sqrt(nn), color=PAL["gold"], ls="--", lw=2.5, alpha=aw)
            ax.text(19800, 330, r"$\pm 2\sqrt{n}$", ha="right", fontsize=24, color=PAL["gold"], alpha=aw)
            ax.text(200, 330, "random walk: n fair coin flips", fontsize=24, color=PAL["violet"], alpha=aw)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    if t > c_bd - 0.3:
        ab = ramp(t, c_bd - 0.3, 0.6)
        ax = axes(fig, [0.08, 0.25, 0.84, 0.58], ylim=(-650, 650))
        xg, dev, bd = D["xg"], D["dev"], D["bound"]
        ax.set_xscale("log")
        ax.set_xlim(2000, 1.05e6)
        ax.fill_between(xg, -bd, bd, color=PAL["gold"], alpha=0.10 * ab, lw=0)
        ax.plot(xg, bd, color=PAL["gold"], lw=2.5, ls="--", alpha=ab)
        ax.plot(xg, -bd, color=PAL["gold"], lw=2.5, ls="--", alpha=ab)
        k = int(5 + clamp((t - c_dt) / 3.0) * (len(xg) - 5)) if t > c_dt else 5
        ax.plot(xg[:k], dev[:k], color=PAL["coral"], lw=3.5, alpha=ab)
        ax.axhline(0, color=PAL["muted"], lw=1)
        label_ax(ax, "x", "π(x) − li(x)")
        ax.text(2.2e3, 560, r"RH bound (Schoenfeld 1976):  $|\pi(x)-\mathrm{li}(x)| < \frac{\sqrt{x}\,\ln x}{8\pi}$,  $x \geq 2657$",
                fontsize=24, color=PAL["gold"], alpha=ab)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
        if t > c_dt:
            ax.text(1e6, -590, f"computed here for {len(xg):,} values of x up to 10$^6$: always inside",
                    ha="right", fontsize=22, color=PAL["coral"], alpha=ramp(t, c_dt + 2, 0.6))


# ==============================================================================
# 9. Curves over finite fields
# ==============================================================================
def sols37(p):
    return [(x, y) for x in range(p) for y in range(p) if (y * y + y - (x ** 3 - x)) % p == 0]


SOL13 = sols37(13)
assert len(SOL13) == 15


@scene("s10_curves")
def s10(fig, ctx, t):
    ov = overlay(fig)
    c_cl, c_gr, c_ct, c_hw, c_wl = (cue(ctx, k) for k in ("clock", "grid", "count", "hasse", "weil"))
    a_cl = window(t, c_cl - 0.2, c_hw, 0.6)
    if a_cl > 0:
        cx, cy, r = 420, 650, 240
        ov.add_patch(Circle((cx, cy), r, fc=PAL["panel"], ec=PAL["muted"], lw=3, alpha=a_cl))
        for k in range(13):
            ang = math.pi / 2 - 2 * math.pi * k / 13
            txt(ov, cx + 0.82 * r * math.cos(ang), cy + 0.82 * r * math.sin(ang), str(k), size=26, a=a_cl,
                ha="center")
        txt(ov, cx, cy - 20, "mod 13", size=24, a=a_cl, color=PAL["muted"], ha="center")
        txt(ov, cx, cy - r - 60, "9 + 6 = 2,   5 × 8 = 1", size=28, a=a_cl * ramp(t, c_cl + 1.5, 0.5),
            ha="center", color=PAL["gold"])
        txt(ov, 1000, 900, r"$y^2 + y \;=\; x^3 - x$   (mod p)", size=40, a=ramp(t, c_cl + 2.5, 0.6))
    a_g = window(t, c_gr - 0.3, c_hw, 0.6)
    if a_g > 0:
        x0, y0, s = 1010, 230, 46
        for x in range(13):
            for y in range(13):
                ov.add_patch(Circle((x0 + x * s, y0 + y * s), 4, color=PAL["faint"], alpha=a_g))
        for i, (x, y) in enumerate(SOL13):
            ai = a_g * ramp(t, c_gr + 0.12 * i, 0.3)
            ov.add_patch(Circle((x0 + x * s, y0 + y * s), 13, color=PAL["coral"], alpha=ai))
        txt(ov, x0 + 6 * s, y0 - 50, "x  →", size=22, a=a_g, color=PAL["muted"], ha="center")
        txt(ov, x0 - 45, y0 + 6 * s, "y", size=22, a=a_g, color=PAL["muted"], ha="center")
        ac = ramp(t, c_ct, 0.6)
        txt(ov, 120, 280, "15 solutions + 1 point at infinity = 16", size=28, a=a_g * ac, color=PAL["coral"])
        txt(ov, 120, 235, "expected about p + 1 = 14", size=28, a=a_g * ac, color=PAL["muted"])
    if t > c_hw - 0.3:
        a = ramp(t, c_hw - 0.3, 0.6)
        ax = axes(fig, [0.08, 0.25, 0.84, 0.56], xlim=(0, 5000), ylim=(-150, 150))
        p, ap = D["hw_p"], D["hw_ap"]
        k = int(clamp((t - c_hw) / 3.0) * len(p))
        ax.scatter(p[:k], ap[:k], s=14, color=PAL["coral"], alpha=a, lw=0)
        pp = np.linspace(0, 5000, 500)
        ax.plot(pp, 2 * np.sqrt(pp), color=PAL["gold"], lw=3, alpha=a)
        ax.plot(pp, -2 * np.sqrt(pp), color=PAL["gold"], lw=3, alpha=a)
        label_ax(ax, "prime p", "(p + 1) − number of points")
        ax.text(4950, 128, r"$\pm\,2\sqrt{p}$", ha="right", fontsize=28, color=PAL["gold"], alpha=a)
        ax.text(100, -135, f"{len(p)} odd primes p < 5000 (p ≠ 37)", fontsize=22, color=PAL["coral"], alpha=a)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    if t > c_wl:
        for i, (yr, who) in enumerate([("1930s", "Hasse: elliptic curves"), ("1940s", "Weil: all curves (2g√p)"),
                                        ("1974", "Deligne: all smooth varieties")]):
            ai = ramp(t, c_wl + 1.6 * i, 0.5)
            card(ov, 160 + i * 540, 905, 500, 80, a=ai * 0.95)
            txt(ov, 185 + i * 540, 945, yr, size=28, a=ai, color=PAL["gold"], weight="bold")
            txt(ov, 300 + i * 540, 945, who, size=24, a=ai)


# ==============================================================================
# 10. Stepanov: counting with multiplicity
# ==============================================================================
@scene("s11_stepanov")
def s11(fig, ctx, t):
    ov = overlay(fig)
    c_p, c_aux, c_ct, c_tu, c_mo = (cue(ctx, k) for k in ("poly", "aux", "count", "tune", "moral"))
    a1 = window(t, c_p - 0.3, c_aux, 0.6)
    if a1 > 0:
        ax = axes(fig, [0.08, 0.26, 0.84, 0.56], xlim=(-3, 3.6), ylim=(-6, 6))
        x = np.linspace(-3, 3.6, 1200)
        f = 0.35 * (x + 2) * x ** 2 * (x - 2.6) ** 3
        ax.plot(x, f, color=PAL["cyan"], lw=4, alpha=a1)
        ax.axhline(0, color=PAL["muted"], lw=1.5)
        for xr, m in ((-2, 1), (0, 2), (2.6, 3)):
            ax.scatter([xr], [0], s=120, color=PAL["gold"], zorder=5, alpha=a1)
            ax.text(xr, -1.4, f"multiplicity {m}", ha="center", fontsize=24, color=PAL["gold"], alpha=a1)
        txt(ov, 150, 880, "degree 6 → at most 6 roots, counted with multiplicity:  1 + 2 + 3 = 6", size=30, a=a1)
    if t > c_aux - 0.3 and t < c_tu:
        a = window(t, c_aux - 0.3, c_tu, 0.6)
        ax = axes(fig, [0.08, 0.40, 0.84, 0.40], xlim=(0, 10), ylim=(-0.3, 2.2))
        pts = np.array([1.0, 2.2, 3.1, 4.6, 5.4, 6.9, 8.0, 9.1])
        x = np.linspace(0, 10, 2000)
        g = np.min(((x[:, None] - pts[None, :]) / 0.42) ** 2, axis=1)
        ax.plot(x, 1.8 * np.tanh(g / 2.2), color=PAL["cyan"], lw=3.5, alpha=a)
        ax.axhline(0, color=PAL["muted"], lw=1.5)
        ax.scatter(pts, np.zeros_like(pts), s=140, color=PAL["coral"], zorder=5, alpha=a)
        ax.set_yticks([])
        ax.set_xticks([])
        txt(ov, 150, 880, "auxiliary polynomial: vanishes to order m at each of the N solutions", size=30, a=a)
        txt(ov, 150, 830, "(here m = 2, drawn schematically)", size=22, a=a, color=PAL["muted"])
        ac = ramp(t, c_ct, 0.6)
        txt(ov, W / 2, 300, r"$N \cdot m\ \leq\ D$", size=72, a=ac, ha="center", color=PAL["gold"])
        txt(ov, W / 2, 215, "(solutions) × (multiplicity)  ≤  (degree)", size=28, a=ac, ha="center",
            color=PAL["muted"])
    if t > c_tu - 0.3:
        a = ramp(t, c_tu - 0.3, 0.6)
        ax = axes(fig, [0.10, 0.28, 0.50, 0.56], xlim=(0, 100), ylim=(60, 260))
        p = 2500.0
        m = np.linspace(1, 100, 600)
        e = p / m + m
        ax.plot(m, e, color=PAL["cyan"], lw=4, alpha=a)
        ax.scatter([50], [100], s=200, color=PAL["gold"], zorder=5, alpha=a)
        ax.axvline(50, color=PAL["gold"], ls="--", lw=2, alpha=a)
        ax.text(52, 235, r"best $m \approx \sqrt{p}$", fontsize=26, color=PAL["gold"], alpha=a)
        ax.set_yticks([])
        label_ax(ax, "multiplicity m", "error bound")
        txt(ov, 1240, 800, "schematic: the bound has terms", size=26, a=a, color=PAL["muted"])
        txt(ov, 1240, 740, r"$\sim\ p/m\ \ +\ \ m$", size=44, a=a, color=PAL["cyan"])
        txt(ov, 1240, 672, r"minimised at $m \approx \sqrt{p}$,", size=30, a=a)
        txt(ov, 1240, 625, r"leaving an error of order $\sqrt{p}$", size=30, a=a)
        txt(ov, 1240, 575, r"(here $p = 2500$, $\sqrt{p} = 50$)", size=24, a=a, color=PAL["muted"])
        txt(ov, 1240, 530, "(Stepanov's constant is larger than Hasse's 2;", size=20, a=a, color=PAL["faint"])
        txt(ov, 1240, 503, "Bombieri and W. Schmidt extended it to all curves)", size=20, a=a, color=PAL["faint"])
        am = ramp(t, c_mo, 0.6)
        card(ov, 1200, 300, 620, 150, a=am, ec=PAL["gold"])
        txt(ov, 1510, 400, "multiplicity ≈ √p", size=34, a=am, ha="center", weight="semibold")
        txt(ov, 1510, 345, "⇒  error ≈ √p", size=34, a=am, ha="center", color=PAL["gold"],
            weight="semibold")


# ==============================================================================
# 11. The integer version: divisibility <= size
# ==============================================================================
from math import comb as _comb
assert _comb(20, 10) == 184756 == 4 * 11 * 13 * 17 * 19 and 11 * 13 * 17 * 19 == 46189


@scene("s12_obstacle")
def s12(fig, ctx, t):
    ov = overlay(fig)
    c_q, c_co, c_bi, c_di, c_ch = (cue(ctx, k) for k in ("quote", "cousin", "binom", "dict", "cheb"))
    a1 = 1 - ramp(t, c_q - 0.3, 0.5)
    if a1 > 0:
        ax = axes(fig, [0.07, 0.36, 0.40, 0.48], xlim=(-1.5, 2.5), ylim=(-2.2, 2.6))
        x = np.linspace(-1.5, 2.5, 600)
        f = (x - 1) ** 2 * (x + 1) * 0.8
        fp = 0.8 * (2 * (x - 1) * (x + 1) + (x - 1) ** 2)
        ax.plot(x, f, color=PAL["cyan"], lw=4, alpha=a1)
        ax.plot(x, fp, color=PAL["violet"], lw=3, ls="--", alpha=a1)
        ax.axhline(0, color=PAL["muted"], lw=1.2)
        ax.scatter([1], [0], s=200, color=PAL["gold"], zorder=6, alpha=a1)
        ax.text(1.1, 0.35, "f = 0 and f′ = 0:\na double root", fontsize=22, color=PAL["gold"], alpha=a1)
        ax.text(-1.4, 2.25, "f(x)", fontsize=24, color=PAL["cyan"], alpha=a1)
        ax.text(-1.4, 1.85, "f′(x)", fontsize=24, color=PAL["violet"], alpha=a1)
        txt(ov, 1350, 700, r"$\frac{d}{d\,?}\ 7\ =\ ?$", size=84, a=a1, ha="center", color=PAL["coral"])
        txt(ov, 1350, 470, "a whole number has no variable to vary", size=28, a=a1, ha="center", color=PAL["muted"])
    aq = window(t, c_q - 0.2, c_co, 0.5)
    if aq > 0:
        quote(ov, 260, 720, 1400, "", "Levent Alpöge, remark.pdf, 20 Nov 2026", a=aq, size=34,
              lines=["This argument is a descendant of Stepanov's, but",
                     "multiplicity is hard to find over the integers,",
                     "corresponding to something like differentiating",
                     "whole numbers."])
    a2 = ramp(t, c_co, 0.6) * (1 - ramp(t, c_di - 0.3, 0.5))
    if a2 > 0:
        card(ov, 160, 790, 1600, 120, a=a2, ec=PAL["gold"])
        txt(ov, W / 2, 850, "A nonzero whole number divisible by many primes (or their powers) must be large.", size=27, a=a2,
            ha="center", weight="semibold")
        ab = ramp(t, c_bi, 0.6)
        txt(ov, W / 2, 680, r"$\binom{20}{10}\ =\ 184{,}756\ =\ 2^2\cdot 11\cdot 13\cdot 17\cdot 19$", size=46, a=a2 * ab,
            ha="center")
        txt(ov, W / 2, 545, r"$11\cdot 13\cdot 17\cdot 19\ =\ 46{,}189\ \ \leq\ \ \binom{20}{10}\ \ <\ \ 4^{10}\ =\ 1{,}048{,}576$",
            size=40, a=a2 * ramp(t, c_bi + 2.5, 0.6), ha="center", color=PAL["cyan"])
        txt(ov, W / 2, 440, "every prime between 10 and 20 divides it, so their product is at most its size",
            size=28, a=a2 * ramp(t, c_bi + 4.0, 0.6), ha="center", color=PAL["muted"])
        txt(ov, W / 2, 380, "(true for every n: the primes between n and 2n multiply to less than 4ⁿ)",
            size=24, a=a2 * ramp(t, c_bi + 5.0, 0.6), ha="center", color=PAL["faint"])
    a3 = ramp(t, c_di - 0.3, 0.6)
    if a3 > 0:
        rows = [("polynomials", "whole numbers"),
                ("a root", "a prime factor p"),
                ("its multiplicity m", "its power pᵐ"),
                ("degree", "size, on a log scale  (log |N|)"),
                ("roots × multiplicity  ≤  degree", "Σ m·log p  ≤  log |N|")]
        card(ov, 230, 330, 1460, 560, a=a3)
        for i, (l, r) in enumerate(rows):
            yy = 830 - i * 100
            ai = a3 * ramp(t, c_di + 0.35 * i, 0.4)
            hd = i == 0
            txt(ov, 560, yy, l, size=30 if hd else 30, a=ai, ha="center",
                color=PAL["cyan"] if hd else PAL["text"], weight="semibold" if hd or i == 4 else "normal")
            txt(ov, 960, yy, "↔", size=30, a=ai * (0 if hd else 1), ha="center", color=PAL["muted"])
            txt(ov, 1360, yy, r, size=30, a=ai, ha="center",
                color=PAL["gold"] if hd else PAL["text"], weight="semibold" if hd or i == 4 else "normal")
        ach = ramp(t, c_ch, 0.6)
        txt(ov, W / 2, 270, r"Chebyshev (c. 1850), with ratios of factorials:   $0.92\,\frac{x}{\ln x} < \pi(x) < 1.11\,\frac{x}{\ln x}$  for large x",
            size=28, a=a3 * ach, ha="center", color=PAL["violet"])
        txt(ov, W / 2, 220, "right size, but far from the √x precision of the Riemann Hypothesis", size=24,
            a=a3 * ramp(t, c_ch + 2.5, 0.6), ha="center", color=PAL["muted"])


# ==============================================================================
# 12. The new idea: theta lifts
# ==============================================================================
@scene("s13_theta")
def s13(fig, ctx, t):
    ov = overlay(fig)
    c_th, c_l, c_ch, c_sq, c_tb = (cue(ctx, k) for k in ("theta", "lift", "chain", "sqrt", "table"))
    c_wg = cue(ctx, "weigh")
    a1 = window(t, c_th - 0.3, c_l, 0.6)
    if a1 > 0:
        ax = axes(fig, [0.08, 0.26, 0.52, 0.56], xlim=(0, 4), ylim=(0, 4.6))
        tt = D["tth"]
        th = D["theta_t"]
        m = (tt <= 4)
        inv = np.interp(1 / tt[m], tt, th)
        ax.plot(tt[m], inv, color=PAL["gold"], lw=7, alpha=a1 * 0.7, label=r"$\theta(1/t)$")
        ax.plot(tt[m], np.sqrt(tt[m]) * th[m], color=PAL["cyan"], lw=2.5, ls="--", alpha=a1,
                label=r"$\sqrt{t}\,\theta(t)$")
        ax.plot(tt[m], th[m], color=PAL["muted"], lw=2, alpha=a1 * 0.7, label=r"$\theta(t)$")
        leg = ax.legend(fontsize=26, frameon=False, loc="upper right", labelcolor=PAL["text"])
        for lh in leg.get_lines():
            lh.set_alpha(a1)
        label_ax(ax, "t", None)
        txt(ov, 1220, 820, r"$\theta(t)=\sum_{n\in\mathbb{Z}} e^{-\pi n^2 t}$", size=44, a=a1)
        txt(ov, 1220, 700, r"$\theta(1/t)=\sqrt{t}\;\theta(t)$", size=44, a=a1 * ramp(t, c_th + 3, 0.6), color=PAL["gold"])
        txt(ov, 1220, 610, "the curves coincide (computed)", size=24, a=a1 * ramp(t, c_th + 3, 0.6), color=PAL["muted"])
        txt(ov, 1220, 520, "→ ζ(s) and ζ(1−s) are linked", size=28, a=a1 * ramp(t, c_th + 6, 0.6))
    a2 = ramp(t, c_l, 0.6) * (1 - ramp(t, c_tb - 0.3, 0.5))
    if a2 > 0:
        # chain of groups
        n_box = 5
        xs = [180 + i * 330 for i in range(n_box)]
        y = 700
        labels = [r"$U_0$", r"$U_1$", r"$U_2$", r"$\cdots$", r"$U_m$"]
        txt(ov, 180, 595, "unitary groups (the note writes U(X₀) → U(X₁) → … → U(Xₘ))", size=20,
            a=a2 * ramp(t, c_ch, 0.6) * (1 - ramp(t, c_sq - 0.3, 0.4)), color=PAL["faint"])
        for i in range(n_box):
            ai = a2 * (1.0 if i == 0 else ramp(t, c_ch + 0.7 * (i - 1), 0.4) if i > 1 else ramp(t, c_l + 1.5, 0.5))
            if labels[i] == r"$\cdots$":
                txt(ov, xs[i] + 110, y, labels[i], size=44, a=ai, ha="center")
                continue
            card(ov, xs[i], y - 70, 220, 140, a=ai, ec=PAL["cyan"])
            txt(ov, xs[i] + 110, y + 8, labels[i], size=36, a=ai, ha="center")
            txt(ov, xs[i] + 110, y - 42, "form" if i == 0 else f"lift {i if i < 4 else 'm'}", size=20, a=ai,
                ha="center", color=PAL["muted"])
            if i > 0:
                arrow(ov, (xs[i - 1] + 225, y), (xs[i] - 8, y), color=PAL["gold"], a=ai)
                txt(ov, (xs[i - 1] + xs[i] + 220) / 2, y + 45, "θ", size=30, a=ai, ha="center", color=PAL["gold"])
        txt(ov, 180, 880, r"theta lift:   $F(h)=\int f(g)\,\Theta(g,h)\,dg$", size=36, a=a2 * ramp(t, c_l + 0.5, 0.5))
        txt(ov, 180, 530, "as the note and the guides describe it: a period of the last lift is a nonzero algebraic integer;", size=26,
            a=a2 * ramp(t, c_ch, 0.6) * (1 - ramp(t, c_sq - 0.3, 0.4)), color=PAL["text"])
        txt(ov, 180, 482, "its divisibility by certain primes grows with every lift: one more order of \"multiplicity\"",
            size=26, a=a2 * ramp(t, c_ch + 1.5, 0.6) * (1 - ramp(t, c_sq - 0.3, 0.4)), color=PAL["cyan"])
        awg = ramp(t, c_wg, 0.6) * (1 - ramp(t, c_sq - 0.3, 0.4))
        txt(ov, 180, 420, "its divisibility (weighted by log p) is itself a weighted count of primes,", size=26,
            a=a2 * awg, color=PAL["gold"])
        txt(ov, 180, 375, "so  divisibility ≤ size  caps that count", size=26, a=a2 * awg, color=PAL["gold"])
        aq = ramp(t, c_sq - 0.2, 0.6)
        if aq > 0:
            ax = axes(fig, [0.10, 0.22, 0.38, 0.30], xlim=(0, 100), ylim=(0, 125))
            X = 2500.0
            m = np.linspace(1.5, 100, 400)
            ax.plot(m, X / m, color=PAL["violet"], lw=2.5, ls="--", alpha=a2 * aq)
            ax.plot(m, m, color=PAL["coral"], lw=2.5, ls="--", alpha=a2 * aq)
            ax.plot(m, X / m + m, color=PAL["cyan"], lw=4, alpha=a2 * aq)
            ax.axvline(50, color=PAL["gold"], lw=2, alpha=a2 * aq)
            ax.set_yticks([])
            ax.set_xticks([0, 50, 100])
            ax.set_xticklabels(["0", r"$\sqrt{X}$", ""])
            label_ax(ax, "chain length m", None, size=22)
            ax.text(8, 110, r"$X/m$", fontsize=24, color=PAL["violet"], alpha=a2 * aq)
            ax.text(88, 70, r"$m$", fontsize=24, color=PAL["coral"], alpha=a2 * aq)
            ax.text(52, 112, "balance", fontsize=22, color=PAL["gold"], alpha=a2 * aq)
            txt(ov, 1000, 530, "two errors, as the AI-assisted guides read the code:", size=24,
                a=a2 * aq, color=PAL["muted"])
            txt(ov, 1000, 470, r"$X/m\ +\ m$  is smallest at  $m \approx \sqrt{X}$", size=34, a=a2 * aq,
                color=PAL["gold"])
            txt(ov, 1000, 405, r"error of order $\sqrt{X}$: what RH demands", size=32,
                a=a2 * ramp(t, c_sq + 3.0, 0.6))
            txt(ov, 1000, 330, "X = how far the prime sum runs  (schematic; X = 2500 here)", size=20,
                a=a2 * aq, color=PAL["faint"])
    a3 = ramp(t, c_tb - 0.3, 0.6)
    if a3 > 0:
        x0, x1, x2 = 220, 700, 1240
        rows = [("", "curves over a clock (p)", "the whole numbers"),
                ("count", "points  N", r"prime sum  $\psi(X)$"),
                ("expected", "p + 1", "X"),
                ("tool", r"multiplicity  $m\approx\sqrt{p}$", r"chain of  $\approx\sqrt{X}$  theta lifts"),
                ("error", r"$\leq 2\sqrt{p}$  (proved: Hasse)", r"order $\sqrt{X}$  (= RH, claimed)")]
        card(ov, 180, 420, 1580, 520, a=a3)
        for i, (a, b, c) in enumerate(rows):
            yy = 890 - i * 100
            ai = a3 * ramp(t, c_tb + 0.4 * i, 0.4)
            col = PAL["muted"] if i == 0 else PAL["text"]
            txt(ov, x0, yy, a, size=26, a=ai, color=PAL["muted"])
            txt(ov, x1, yy, b, size=29 if i else 28, a=ai, color=PAL["cyan"] if i == 0 else col,
                weight="semibold" if i == 0 else "normal")
            txt(ov, x2, yy, c, size=29 if i else 28, a=ai, color=PAL["gold"] if i == 0 else col,
                weight="semibold" if i == 0 else "normal")
        txt(ov, 1740, 440, "analogy as described in the note and by readers of the code", size=18, a=a3, ha="right",
            color=PAL["faint"])
        quote(ov, 560, 385, 800, "", "Alpöge, on Claude's suggestion of √X", a=a3 * ramp(t, c_tb + 2.5, 0.6), size=28,
              lines=["And yet, what else could it be?"])


# ==============================================================================
# 13. The construction
# ==============================================================================
TIMELINE = [("Oct 6", "Stepanov determinant"), ("Oct 19", "qN = Mᵏ + R"), ("Oct 20", "switch to Λ (von Mangoldt sum)"),
            ("Nov 15", "iterated theta lifts, m like √X"), ("Nov 16", "GRH")]


def squarify(vals, x, y, w, h):
    """Squarified treemap (Bruls et al.), vals sorted descending; returns rects."""
    vals = list(vals)
    total = sum(vals)
    vals = [v * w * h / total for v in vals]
    rects = []

    def worst(row, side):
        s = sum(row)
        return max(max(side * side * r / (s * s), (s * s) / (side * side * r)) for r in row)

    while vals:
        side = min(w, h)
        row = [vals.pop(0)]
        while vals and worst(row + [vals[0]], side) <= worst(row, side):
            row.append(vals.pop(0))
        s = sum(row)
        if w >= h:
            cw = s / h
            yy = y
            for r in row:
                rects.append((x, yy, cw, r / cw))
                yy += r / cw
            x += cw
            w -= cw
        else:
            ch = s / w
            xx = x
            for r in row:
                rects.append((xx, y, r / ch, ch))
                xx += r / ch
            y += ch
            h -= ch
    return rects


@scene("s14_build")
def s14(fig, ctx, t):
    ov = overlay(fig)
    c_tl, c_ln, c_sk, c1, c2, c3, c_cd = (cue(ctx, k) for k in ("timeline", "lean", "skeleton", "step1", "step2", "step3", "code"))
    c_cv = cue(ctx, "caveat")
    a1 = window(t, c_tl - 0.3, c_ln, 0.6)
    if a1 > 0:
        y = 600
        ov.plot([200, 1720], [y, y], color=PAL["muted"], lw=3, alpha=a1)
        days = [0, 13, 14, 40, 41]  # days after Oct 6
        for i, ((d, s), dd) in enumerate(zip(TIMELINE, days)):
            x = 200 + dd / 41 * 1520
            ai = a1 * ramp(t, c_tl + 0.5 * i, 0.4)
            ov.scatter([x], [y], s=160, color=PAL["gold"], zorder=5, alpha=ai)
            up = i % 2 == 0
            txt(ov, x, y + (70 if up else -60), d, size=26, a=ai, ha="center", color=PAL["gold"], weight="bold")
            txt(ov, x, y + (120 if up else -110), s, size=24, a=ai, ha="center")
        txt(ov, 200, 860, "the note's rough timeline (\"Claude provided\", per the note): 20 items, Oct 6 → Nov 16, 2026", size=28, a=a1)
        txt(ov, 200, 330, "periods · theta lifts · Siegel mass · Iwasawa towers · slope inequalities · relative trace formula …",
            size=24, a=a1 * ramp(t, c_tl + 3, 0.6), color=PAL["muted"])
    a2 = window(t, c_ln - 0.3, c_sk, 0.6)
    if a2 > 0:
        top = TREE["top"]
        items = sorted([(k, v[1]) for k, v in top.items() if v[1] > 50000], key=lambda kv: -kv[1])
        other = TREE["lines"] - sum(v for _, v in items)
        items.append(("other", other))
        rects = squarify([v for _, v in items], 120, 200, 1080, 680)
        cols = [PAL["blue"], PAL["violet"], PAL["cyan"], PAL["green"], PAL["orange"], PAL["coral"], PAL["faint"]]
        for i, ((k, v), (x, y, w, h)) in enumerate(zip(items, rects)):
            ai = a2 * ramp(t, c_ln + 0.2 * i, 0.4)
            ov.add_patch(Rectangle((x + 2, y + 2), w - 4, h - 4, color=cols[i % len(cols)], alpha=0.55 * ai))
            if w > 170 and h > 80:
                txt(ov, x + 16, y + h - 30, k, size=22 if w > 250 else 16, a=ai, weight="semibold")
                txt(ov, x + 16, y + h - 62, f"{v/1e6:.2f} M lines" if v > 1e6 else f"{v/1e3:.0f} k", size=18, a=ai,
                    color=PAL["text"])
        txt(ov, 1260, 820, f"{TREE['files']:,} files", size=44, a=a2, weight="bold", color=PAL["cyan"])
        txt(ov, 1260, 740, f"{TREE['lines']:,} lines", size=44, a=a2, weight="bold", color=PAL["cyan"])
        txt(ov, 1260, 660, "0 comments · 0 new axioms", size=28, a=a2 * ramp(t, c_ln + 2, 0.5))
        txt(ov, 1260, 615, "0 unfinished steps (Lean's \"sorry\")", size=26, a=a2 * ramp(t, c_ln + 2, 0.5))
        txt(ov, 1260, 560, "depends directly only on Mathlib", size=26, a=a2 * ramp(t, c_ln + 2.5, 0.5), color=PAL["muted"])
        txt(ov, 1260, 250, "counted from the published\narchive (sha256 9631b4f0…)", size=20, a=a2,
            color=PAL["faint"], linespacing=1.3)
    a3 = ramp(t, c_sk - 0.3, 0.6)
    if a3 > 0:
        boxes = [
            ("theta lifts on unitary groups, Galois representations,\nSiegel–Weil, … (names as in the code; most of the 17 M lines)", c3, PAL["violet"]),
            ("weighted prime sums stay below  ≈ x$^{1/2}$  on long stretches of x", c2, PAL["coral"]),
            ("no zeros with Re s > ½  for ζ and every Dirichlet L-function", c2, PAL["cyan"]),
            ("mirror symmetry  s ↔ 1 − s", c1, PAL["blue"]),
            ("Riemann Hypothesis", c1, PAL["gold"]),
        ]
        x0, wbox = 140, 1050
        ys = [270, 420, 550, 680, 800]
        for i, (s, ci, col) in enumerate(boxes):
            hi = ramp(t, ci, 0.5)
            ai = a3 * (0.45 + 0.55 * hi)
            hbox = 100 if i == 0 else 78
            card(ov, x0, ys[i] - hbox / 2, wbox, hbox, a=ai, ec=col, lw=2.5 + 1.5 * hi)
            txt(ov, x0 + 26, ys[i], s, size=23 if i == 0 else 25, a=ai, weight="semibold" if i == 4 else "normal",
                linespacing=1.2)
            if i < 4:
                arrow(ov, (x0 + wbox / 2, ys[i] + (hbox / 2) + 2), (x0 + wbox / 2, ys[i + 1] - 37), color=PAL["muted"],
                      a=ai, ms=22)
        txt(ov, 160, 905, "the proof's skeleton, traced from Main.lean", size=28, a=a3, color=PAL["muted"])
        ac = ramp(t, c_cd, 0.6)
        code_panel(ov, 1220, 640, 640, [("x ^ ((1 : ℝ) / 2 - ε) ≤ m ∧", PAL["gold"])], a=ac, size=24,
                   label="Formalism/SizeWindowBrackets/SChain.lean, line 57 (verbatim)")
        txt(ov, 1240, 470, "m = the number of lift steps;", size=24, a=ac, color=PAL["muted"])
        txt(ov, 1240, 432, "at least x$^{1/2-ε}$: just under √x", size=24, a=ac, color=PAL["muted"])
        code_panel(ov, 1220, 380, 640, [("theorem riemannHypothesis :", PAL["cyan"]),
                                        ("  RiemannHypothesis := rhOfAll", PAL["cyan"])],
                   a=a3 * ramp(t, c1, 0.6) * (1 - ramp(t, c_cv - 0.3, 0.4)), size=22,
                   label="Main.lean, line 4 (verbatim; line wrapped)")
        acv = ramp(t, c_cv, 0.6)
        card(ov, 1220, 190, 640, 200, a=acv, ec=PAL["coral"])
        txt(ov, 1245, 345, "caveat from independent readers", size=22, a=acv, color=PAL["coral"], weight="semibold")
        txt(ov, 1245, 300, "some of the note's 20 timeline steps,", size=22, a=acv)
        txt(ov, 1245, 265, "e.g. the \"Stepanov determinant\", have no", size=22, a=acv)
        txt(ov, 1245, 230, "counterpart found in the code (Jaswal, 21 Nov)", size=22, a=acv)


# ==============================================================================
# 14. Checking it
# ==============================================================================
MATHLIB_RH = ["def RiemannHypothesis : Prop :=",
              "  ∀ (s : ℂ) (_ : riemannZeta s = 0)",
              "    (_ : ¬∃ n : ℕ, s = -2 * (n + 1))",
              "    (_ : s ≠ 1), s.re = 1 / 2"]


@scene("s15_check")
def s15(fig, ctx, t):
    ov = overlay(fig)
    c_k, c_4, q1, q2, q3, q4, c_j = (cue(ctx, k) for k in ("kernel", "four", "q1", "q2", "q3", "q4", "joint"))
    a0 = window(t, 0.3, c_4, 0.6)
    if a0 > 0:
        card(ov, 200, 380, 560, 420, a=a0, fc=PAL["bg2"])
        for i in range(14):
            txt(ov, 230, 760 - i * 27, "█" * (8 + (i * 7) % 15), size=12, a=a0 * 0.5, color=PAL["violet"], family=MONO)
        txt(ov, 480, 340, "17.4 M lines (AI-written)", size=26, a=a0, ha="center")
        ak = ramp(t, c_k, 0.6)
        arrow(ov, (790, 590), (1050, 590), color=PAL["gold"], a=ak)
        card(ov, 1080, 500, 300, 180, a=ak, ec=PAL["gold"])
        txt(ov, 1230, 610, "kernel", size=34, a=ak, ha="center", weight="bold")
        txt(ov, 1230, 555, "checks every step", size=22, a=ak, ha="center", color=PAL["muted"])
        arrow(ov, (1410, 590), (1560, 590), color=PAL["green"], a=ak)
        tick(ov, 1620, 590, a=ak, size=70)
    if t < c_4 - 0.3:
        return
    a = ramp(t, c_4 - 0.3, 0.6)
    txt(ov, 120, 920, "four questions for AI-written Lean  (K. Buzzard, Xena blog, 12 Nov 2026)", size=28, a=a,
        color=PAL["muted"])
    qs = [("1", "Is the statement right?", "Mathlib's own definition, vetted by experts", q1),
          ("2", "Does it compile?", "dozens of rebuilds; one sandboxed, byte-identical", q2),
          ("3", "Exactly that statement, standard axioms only?", "comparator, con-leche --compare: yes", q3),
          ("4", "Could it exploit a bug in Lean's kernel?", "several independent checkers accept it", q4)]
    for i, (n, q, ans, ci) in enumerate(qs):
        yy = 820 - i * 118
        ai = a * ramp(t, ci, 0.5)
        txt(ov, 140, yy, n, size=40, a=ai, color=PAL["gold"], weight="bold", ha="center")
        txt(ov, 190, yy + 18, q, size=30, a=ai, weight="semibold")
        txt(ov, 190, yy - 26, ans, size=24, a=ai * ramp(t, ci + 1.5, 0.5), color=PAL["muted"])
        tick(ov, 1000, yy, a=ai * ramp(t, ci + 2.2, 0.4), size=40)
    a_code = ramp(t, q1, 0.6) * (1 - ramp(t, c_j - 0.3, 0.5))
    code_panel(ov, 1110, 840, 760, [(s, PAL["cyan"]) for s in MATHLIB_RH], a=a_code, size=21, line_h=36,
               label="Mathlib's definition (verbatim; long line wrapped)")
    txt(ov, 1130, 605, "in words: every zero s except −2, −4, −6, …", size=19,
        a=a_code * ramp(t, q1 + 2.0, 0.6), color=PAL["muted"])
    txt(ov, 1130, 578, "(and s ≠ 1, the pole) has real part ½", size=19, a=a_code * ramp(t, q1 + 2.0, 0.6), color=PAL["muted"])
    if t > q4 - 0.2:
        a4 = ramp(t, q4 + 1.0, 0.6) * (1 - ramp(t, c_j - 0.3, 0.5))
        txt(ov, 1120, 535, "checks that accepted it (MIT page, 22 Nov):", size=22, a=a4, color=PAL["muted"])
        for i, s in enumerate(["Lean's own kernel: every module replayed", "lean4lean: every compiled module",
                               "nanoda (Rust): the full export", "con-leche (formal soundness proof): full export",
                               "con-ron (its Rust port): full export"]):
            txt(ov, 1140, 497 - i * 34, "• " + s, size=21, a=a4)
        txt(ov, 1140, 322, "Lean's kernel on the full export: still running", size=19, a=a4, color=PAL["faint"])
    aj = ramp(t, c_j, 0.6)
    if aj > 0:
        quote(ov, 1110, 860, 760, "", "Lean + Mathlib communities, 21 Nov 2026", a=aj, size=28,
              lines=["We have full confidence that", "Alpöge's proof of the Riemann", "Hypothesis is correct."])


# ==============================================================================
# 15. Where this leaves us
# ==============================================================================
@scene("s16_close")
def s16(fig, ctx, t):
    ov = overlay(fig)
    c_c, c_d, c_n, c_cl, c_end = (cue(ctx, k) for k in ("certified", "dirichlet", "notyet", "clay", "close"))
    a = 1 - ramp(t, c_end - 0.3, 0.6)
    rows = [
        (c_c, "✓", PAL["green"], "certified", "the Riemann Hypothesis (Mathlib's statement): Lean + Mathlib, 21 Nov"),
        (c_d, "✓", PAL["green"], "also checked", "every Dirichlet L-function (GRH in that sense): A. Sutherland's MIT page"),
        (c_n, "✗", PAL["coral"], "not checked", "other L-functions (Dedekind, Hecke, automorphic); the note only expects ERH"),
        (c_n + 4.0, "✗", PAL["coral"], "not yet", "a human-readable proof (Alpöge: he will \"write it properly\")"),
        (c_cl, "…", PAL["gold"], "Clay prize", "rules: publication, then 2 years, then general acceptance"),
    ]
    for i, (ci, mark, col, head, body) in enumerate(rows):
        ai = a * ramp(t, ci, 0.5)
        yy = 830 - i * 120
        card(ov, 140, yy - 48, 1640, 96, a=ai * 0.95)
        txt(ov, 195, yy, mark, size=40, a=ai, color=col, ha="center", weight="bold")
        txt(ov, 250, yy, head, size=28, a=ai, color=col, weight="semibold")
        txt(ov, 520, yy, body, size=26, a=ai)
    if t > c_end - 0.3:
        ae = ramp(t, c_end - 0.3, 0.8)
        zero_column(ov, W / 2, 260, 1000, a=ae, tmax=60)
        txt(ov, W / 2 - 60, 640, "a claimed proof", size=48, a=ae, ha="right", weight="bold")
        txt(ov, W / 2 - 60, 570, "machine-checked", size=36, a=ae * ramp(t, c_end + 1.5, 0.6), ha="right",
            color=PAL["green"])
        txt(ov, W / 2 + 60, 570, "not yet explained", size=36, a=ae * ramp(t, c_end + 3.0, 0.6), ha="left",
            color=PAL["gold"])
        txt(ov, W / 2, 230, "Sources: alpo.ge/remark.pdf · leanprover-community.github.io/blog · math.mit.edu/~drew/grh",
            size=20, a=ae * ramp(t, c_end + 5, 0.6), ha="center", color=PAL["faint"])
        txt(ov, W / 2, 195, "Synthetic narration (Kokoro-82M) · every plot computed from scratch in Python",
            size=20, a=ae * ramp(t, c_end + 5, 0.6), ha="center", color=PAL["faint"])
