"""
The yoke's printed legends as letter BLOCKS (YOKE_DESIGN legends / legend_style; no lettering: NO MARKINGS), for the
sheets (drawing/yoke_draw.legend_quads) and the 3-D build (yoke3d.legend_pieces) alike.

Rev P (3-D judges r3 CR3-05: twelve equal bars 0.35 of the pitch read as a chunky tick dial at close range): each
letter's block width varies along its word by +/- legend_style[2] of the mean (legend_style[0] of the letter pitch) on a
fixed golden-angle sequence -- letters differ in weight, so a word reads as print, not as a scale.  These supersede
yoke_geom.legend_blocks / legend_quads (rev N / O: uniform widths), which are left in place unused: yoke_geom's source
is part of the solids' design key (yoke_geom.design_key), and a printed finish must not re-key every cached view,
section and mesh stage of the solids.
"""
from __future__ import annotations

import math

import numpy as np

from model import yoke_geom as G


def legend_blocks(k):
    """The legend of switch k (YOKE_DESIGN legends rows: 0 TCS, 1 AFCS, 2 / 3 the trim face's fore / aft lune, 4 the push
    button) as plain letter BLOCKS: [(P0, P1, width)] -- each block the radial segment P0 -> P1 (r0 -> r1 at the
    letter's centre angle, in the switch's front-view frame about its centre: x outboard, y up, co-pilot sense) and its
    width across: legend_style[0] of the letter pitch x (1 + legend_style[2] x the letter's weight in [-1, 1])."""
    r0, r1, words = G.T()["legends"][k]
    r0, r1 = float(r0), float(r1)
    sty = G.T()["legend_style"]
    frac = float(sty[0])
    var = float(sty[2]) if len(sty) > 2 else 0.0
    rm = 0.5 * (r0 + r1)
    out = []
    j = 0
    for a0, a1, n in words:
        dp = math.radians(float(a1) - float(a0)) / int(n)
        for i in range(int(n)):
            a = math.radians(float(a0)) + (i + 0.5) * dp
            e = np.array([math.cos(a), math.sin(a)])
            wv = math.sin(2.39996 * (j + 3 * k + 1))                      # golden-angle sequence in [-1, 1]
            out.append((r0 * e, r1 * e, frac * (1.0 + var * wv) * rm * dp))
            j += 1
    return out


def legend_quads(k):
    """legend_blocks(k) as closed quads (5, 2) (front-view frame of the switch, co-pilot sense)."""
    out = []
    for P0, P1, w in legend_blocks(k):
        d = (P1 - P0) / np.linalg.norm(P1 - P0)
        t = 0.5 * w * np.array([-d[1], d[0]])
        out.append(np.array([P0 - t, P1 - t, P1 + t, P0 + t, P0 - t]))
    return out
