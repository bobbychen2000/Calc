"""
The yoke's printed legends as letter BLOCKS (YOKE_DESIGN legends / legend_style; no lettering: NO MARKINGS), for the
sheets (drawing/yoke_draw.legend_quads) and the 3-D build (yoke3d.legend_pieces) alike.

Rev P (3-D judges r3 CR3-05: twelve equal bars 0.35 of the pitch read as a chunky tick dial at close range): each
letter's block width varies along its word by +/- legend_style[2] of the mean (legend_style[0] of the letter pitch) on a
fixed golden-angle sequence -- letters differ in weight, so a word reads as print, not as a scale.  These supersede
yoke_geom.legend_blocks / legend_quads (rev N / O: uniform widths), which are left in place unused: yoke_geom's source
is part of the solids' design key (yoke_geom.design_key), and a printed finish must not re-key every cached view,
section and mesh stage of the solids.

Rev Q (3-D judges r4 CR4-06: CR3-05's uneven widths did not break the EVEN PITCH -- the rings still read as scales at
close range): the letters of a word are SET, not spaced on a grid -- each letter's advance follows its own width plus an
uneven letter gap (legend_style[4] of the mean gap, a second fixed sequence), the word kept on its drawn arc, so the
blocks cluster into words with clear word gaps; and each block's radial extent varies (legend_style[3]): some letters
stand the full cap height, others shorter and sitting on the baseline or hanging from the cap line (the ink of an L,
a T, an E's arms read as a short block at the bottom / top of the row).
"""
from __future__ import annotations

import math

import numpy as np

from model import yoke_geom as G


def legend_blocks(k):
    """The legend of switch k (YOKE_DESIGN legends rows: 0 TCS, 1 AFCS, 2 / 3 the trim face's fore / aft lune, 4 the push
    button) as plain letter BLOCKS: [(P0, P1, width)] -- each block the radial segment P0 -> P1 (its radial extent within
    the row's r0 -> r1, at the letter's centre angle, in the switch's front-view frame about its centre: x outboard, y
    up, co-pilot sense) and its width across: legend_style[0] of the mean letter pitch x (1 + legend_style[2] x the
    letter's weight in [-1, 1]).  Rev Q: letters set by their widths with uneven gaps (legend_style[4]) and varied radial
    extents (legend_style[3]) -- see the module note."""
    r0, r1, words = G.T()["legends"][k]
    r0, r1 = float(r0), float(r1)
    sty = G.T()["legend_style"]
    frac = float(sty[0])
    var = float(sty[2]) if len(sty) > 2 else 0.0
    var_r = float(sty[3]) if len(sty) > 3 else 0.0
    var_g = float(sty[4]) if len(sty) > 4 else 0.0
    rm = 0.5 * (r0 + r1)
    out = []
    j = 0
    for a0, a1, n in words:
        n = int(n)
        span = math.radians(float(a1) - float(a0))
        idx = np.arange(j, j + n)
        wv = np.sin(2.39996 * (idx + 3 * k + 1))                      # golden-angle sequence in [-1, 1]: letter weight
        gv = np.sin(1.61803 * (idx + 5 * k + 2) + 0.7)                 # a second sequence: the gap after each letter
        hv = np.sin(3.14159 * 0.618 * (idx + 7 * k) + 1.3)             # a third: the letter's radial extent / anchor
        w = frac * (1.0 + var * wv)                                    # widths in mean pitches
        g = (1.0 - frac) * (1.0 + var_g * gv)                          # gaps in mean pitches
        # set the word: letter i's centre at the sum of the advances before it + half its width; a full mean gap kept
        # free at both ends of the word's drawn arc (n pitches) -- the letters close up and the words stand apart
        adv = np.r_[0.0, np.cumsum(w[:-1] + 0.5 * (g[:-1] + g[1:]))]
        cen = (1.0 - frac) + 0.5 * w + adv
        tot = cen[-1] + 0.5 * w[-1] + (1.0 - frac)
        dp = span / n
        sc = n / tot
        for i in range(n):
            a = math.radians(float(a0)) + cen[i] * sc * dp
            e = np.array([math.cos(a), math.sin(a)])
            # radial extent: full cap height, or up to var_r shorter -- on the baseline (r0 side), or from the cap line
            short = var_r * max(0.0, float(hv[i]))
            if hv[i] > 0.55:
                q0, q1 = r1 - (1.0 - short) * (r1 - r0), r1             # hanging from the cap line (a T's bar)
            else:
                q0, q1 = r0, r0 + (1.0 - short) * (r1 - r0)             # standing on the baseline
            out.append((q0 * e, q1 * e, w[i] * rm * dp))
        j += n
    return out


def legend_quads(k):
    """legend_blocks(k) as closed quads (5, 2) (front-view frame of the switch, co-pilot sense)."""
    out = []
    for P0, P1, w in legend_blocks(k):
        d = (P1 - P0) / np.linalg.norm(P1 - P0)
        t = 0.5 * w * np.array([-d[1], d[0]])
        out.append(np.array([P0 - t, P1 - t, P1 + t, P0 + t, P0 - t]))
    return out
