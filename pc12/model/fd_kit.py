"""Flight-deck parts kit: frames, sections, knobs, shared helpers (split from model/fd_detail_a.py)."""
from __future__ import annotations

import math

import numpy as np

from cad import sdf2d
from cad.mesh import Mesh, grid_surface, planar_cap


# The flight-deck shared materials (leather_black, stitch_thread, rubber_black, legend_*, annun_*) are
# model/assemble.MATERIALS' 'flight deck shared' block (render/lookdev.py SPEC the same).


def _FD():
    from model import flightdeck
    return flightdeck


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _orient_out(m, centre_fn):
    """Flip m if its faces point (on average) toward centre_fn(C) rather than away from it."""
    if not len(m.F):
        return m
    fn = m.face_normals()
    C = m.V[m.F].mean(1)
    return m.flipped() if np.mean(np.sum(fn * (C - centre_fn(C)), 1)) < 0 else m


def _fan(ring, tip):
    n = len(ring)
    i = np.arange(n)
    return Mesh(np.vstack([ring, np.asarray(tip, float)[None]]), np.stack([i, (i + 1) % n, np.full(n, n)], 1))


# =====================================================================================================================
# section outlines
# =====================================================================================================================
def d_section(w, d, ra, rf, nc=4, ne=3):
    """D-shaped grip section in (lat, dep) about its centre: half-width w, half-depth d, the AFT face (dep = +d) flat
    between corners of radius ra, the forward side rounded by rf (rf ~ d: a full round front).  A fixed point count
    (4 corners x nc + 4 edges x ne) so sections loft; CCW in (lat, dep)."""
    ra = min(ra, w - 1e-5, d - 1e-5)
    rf = min(rf, w - 1e-5, 2 * d - ra - 1e-5)
    out = []
    # corners: (centre, start angle) CCW from the aft-right corner; edges between them
    C = [((w - ra, d - ra), 0.0, ra), ((-(w - ra), d - ra), 90.0, ra), ((-(w - rf), -d + rf), 180.0, rf),
         ((w - rf, -d + rf), 270.0, rf)]
    for k, ((cx, cy), a0, r) in enumerate(C):
        for a in np.radians(np.linspace(a0, a0 + 90.0, nc)):
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        (nx, ny), b0, rn = C[(k + 1) % 4][0], C[(k + 1) % 4][1], C[(k + 1) % 4][2]
        p = np.array(out[-1])
        q = np.array([nx + rn * math.cos(math.radians(b0)), ny + rn * math.sin(math.radians(b0))])
        for t in np.linspace(0.0, 1.0, ne + 2)[1:-1]:
            out.append(tuple(p + t * (q - p)))
    return np.array(out)


def superellipse(hw, hh, e=0.5, n=24, cx=0.0, cy=0.0):
    """Closed superellipse outline (CCW): |x / hw|^(2/e) + |y / hh|^(2/e) = 1 (e 1 = ellipse, -> 0 = rectangle)."""
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(a), np.sin(a)
    return np.c_[cx + hw * np.sign(c) * np.abs(c) ** e, cy + hh * np.sign(s) * np.abs(s) ** e]


def _poly_normals(P):
    return _FD()._poly_normals(np.asarray(P, float))


def knob(o, axis, ref, r, h, n=24, flutes=0, depth=0.0005, skirt=None, chamfer=0.25, cap=True):
    """Turned knob standing on o along axis (explicit segment count n, no res.seg): an optional skirt (r_s, h_s) at its
    foot, a fluted / knurled side (flutes > 0: the radius dips `depth` between flutes, n raised to 4 x flutes), a top
    chamfer of chamfer x r, a flat top."""
    axis = _unit(axis)
    ref = _unit(np.asarray(ref, float) - axis * np.dot(ref, axis))
    side = np.cross(axis, ref)
    m = max(n, 4 * flutes) if flutes else n
    a = np.linspace(0.0, 2 * np.pi, m, endpoint=False)
    rf = r - (depth * 0.5 * (1 - np.cos(flutes * a)) if flutes else 0.0)
    prof = []                                                   # (height, radius array)
    z0 = 0.0
    if skirt:
        rs, hs = skirt
        prof += [(0.0, np.full(m, rs)), (0.65 * hs, np.full(m, rs)), (hs, np.full(m, 0.94 * rs)),
                 (hs, np.full(m, min(r, 0.94 * rs)))]
        z0 = hs
    ch = min(chamfer * r, 0.45 * h)
    prof += [(z0, rf), (z0 + h - ch, rf), (z0 + h, rf - ch)]
    G = np.array([o + z * axis + np.outer(R * np.cos(a), ref) + np.outer(R * np.sin(a), side) for z, R in prof])
    parts = [_orient_out(grid_surface(G, close_v=True), lambda C: o + np.outer((C - o) @ axis, axis))]
    if cap:
        parts.append(_orient_out(_fan(G[-1], o + (z0 + h) * axis), lambda C: C - axis))
    return Mesh.merge(parts)
