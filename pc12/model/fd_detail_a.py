"""
Flight-deck detail, track A (flight deck r1 GEOM A, owner 2026-10-04 "the details are drastically missing"): the panel
area -- yokes, rudder pedals and footwells, glareshield hood, GFC 700 / eyebrow fascia, lower panel, panel zoning,
centre stack and pedestal.  The helpers and builders the owned model/flightdeck.py functions call (_yokes, _pedals,
_glareshield, _lower_panel, _pedestal, _panel_face) and the hook _detail_a(acc) that model/flightdeck.build_flightdeck
calls after _pedals.

Every dimension the sheets L6 / L6B draw comes from the interior tables (PANEL, GLARESHIELD, YOKE, PEDALS, PEDESTAL);
the sizes here are builder-level detail (knobs, keys, bezels, screws, stitching), tagged [M] (measured on the
gitignored reference photos: P1046406 / 08 / 09 / 10 of PRO s/n 3001, the JTF p.18 cockpit key, the brochure pp.10 /
12, the Pilatus throttle photo) or [E].  No markings: legends are abstract strokes and pictograms in light_white /
the annunciator colours (no text, no logos; the legend atlas is the seed's).  Segment counts are explicit (the flight
deck is rebuilt at RES 2 in the light tier too once build.LOW_FINE takes it: the seed's job).
"""
from __future__ import annotations

import math

import numpy as np

from cad import sdf2d
from cad.mesh import Mesh, grid_surface, planar_cap

# The flight-deck shared materials are the seed's ('flight deck shared (seed)' block of model/assemble.py); until that
# block lands these stand-ins register the names this track uses so the branch builds on its own.  setdefault only:
# the seed's values (or any existing entry) win, no existing material changes.
SHARED_FALLBACK = {
    "leather_black": ((0.030, 0.030, 0.032), 0.0, 0.60, dict(specular=0.5)),
    "stitch_thread": ((0.30, 0.29, 0.27), 0.0, 0.70),
    "rubber_black": ((0.020, 0.020, 0.022), 0.0, 0.85),
    "annun_amber": ((0.60, 0.33, 0.04), 0.0, 0.30),
    "annun_red": ((0.55, 0.04, 0.03), 0.0, 0.30),
    "annun_green": ((0.05, 0.40, 0.12), 0.0, 0.30),
}


def _register_fallback():
    from model import assemble
    for k, v in SHARED_FALLBACK.items():
        assemble.MATERIALS.setdefault(k, v)


_register_fallback()


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


def clip_below(P, z):
    """The part of the closed polygon P (a, b) with b <= z (Sutherland-Hodgman against one half-plane)."""
    P = np.asarray(P, float)
    out = []
    for k in range(len(P)):
        a, b = P[k], P[(k + 1) % len(P)]
        ina, inb = a[1] <= z, b[1] <= z
        if ina:
            out.append(a)
        if ina != inb:
            t = (z - a[1]) / (b[1] - a[1])
            out.append(a + t * (b - a))
    return np.array(out)


def superellipse(hw, hh, e=0.5, n=24, cx=0.0, cy=0.0):
    """Closed superellipse outline (CCW): |x / hw|^(2/e) + |y / hh|^(2/e) = 1 (e 1 = ellipse, -> 0 = rectangle)."""
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(a), np.sin(a)
    return np.c_[cx + hw * np.sign(c) * np.abs(c) ** e, cy + hh * np.sign(s) * np.abs(s) ** e]


# =====================================================================================================================
# yoke pieces (model/flightdeck._yokes)
# =====================================================================================================================
YOKE_DETAIL = dict(
    # paddle grip [M: P1046408 at 0.70 mm/px, P1046409 at 0.52, brochure p.12]: D section, flat aft face carrying the
    # leather inset; width from the YOKE grip / grip_head table (28-32 mm near the bottom, 42 under the head)
    grip_d=0.014,                  # half-depth (fore-aft) [M: P1046409 side view ~28 mm]
    grip_ra=0.0040,                # aft-face corner radius
    grip_rf=0.0120,                # forward (finger) side radius
    inset=(0.09, 0.80, 0.0018),    # leather inset on the aft face: s0, s1 along the grip, rim width [M: P1046409]
    trigger=(0.66, 0.014, 0.020, 0.006),   # PTT trigger on the outboard grip's forward face: s, width, height, proud
)


def paddle_grip(o, ax, lat, dep, L, w_of, d, ra, rf, n_s=30, nc=4, ne=3, end_p=(2.0, 3.0)):
    """Paddle grip lofted along ax from o (0 .. L): D sections (d_section) of half-width w_of(s) (s = 0 .. 1) across
    lat, half-depth d along dep, flat aft face (+dep); both ends rounded over their half-width (the sections shrink on a
    superellipse of exponent end_p: 2 = a quarter circle, 3 = the squarer head).  Returns (Mesh, aft-face function
    (s) -> (centre point, flat half-width))."""
    s = 0.5 * (1 - np.cos(np.linspace(0.0, np.pi, n_s)))
    w = np.array([w_of(si) for si in s])
    r0, r1 = w[0] / L, w[-1] / L
    p0, p1 = end_p
    k0 = np.clip(1.0 - np.clip((r0 - s) / r0, 0, 1) ** p0, 0.0, 1.0) ** (1.0 / p0)
    k1 = np.clip(1.0 - np.clip((s - (1 - r1)) / r1, 0, 1) ** p1, 0.0, 1.0) ** (1.0 / p1)
    k = np.maximum(np.minimum(k0, k1), 2e-3)
    G = []
    for si, wi, ki in zip(s, w, k):
        S2 = d_section(wi, d, ra, rf, nc, ne) * ki
        G.append(o + L * si * ax + np.outer(S2[:, 0], lat) + np.outer(S2[:, 1], dep))
    G = np.array(G)
    body = _orient_out(grid_surface(G, close_v=True), lambda C: o + np.outer((C - o) @ ax, ax))
    caps = [_orient_out(_fan(G[0], G[0].mean(0)), lambda C: C + ax), _orient_out(_fan(G[-1], G[-1].mean(0)),
                                                                                    lambda C: C - ax)]

    def aft(si):
        wi = float(w_of(si))
        return o + L * si * ax + d * dep, wi - ra
    return Mesh.merge([body] + caps), aft


def taper_outline(L, s0, s1, hw_of, n=18, e=0.45):
    """Closed outline (u along the grip, v across) of an inset from s0 to s1 (fractions of L), half-width hw_of(s),
    the ends rounded (superellipse exponent e of the end caps).  CCW."""
    t = np.linspace(0.0, np.pi, n)
    uu = 0.5 * (1 - np.cos(t))                                      # 0 .. 1, dense at the ends
    s = s0 + (s1 - s0) * uu
    env = np.sin(t) ** e
    hw = np.array([hw_of(si) for si in s]) * env
    right = np.c_[s * L, -hw]
    left = np.c_[s * L, hw][::-1]
    P = np.vstack([right, left[1:-1]])
    return P


def inset(o, u, v, n, outline, rim, h_rim=0.0010, h_in=0.0005, nb=2):
    """A grained leather inset on a flat face: the leather pad (outline (u, v) about o in the face, raised h_in along n,
    its edge rolled) and its moulded rim, a band rim wide round it standing h_rim (rounded).  Returns
    [(Mesh, material)]."""
    P = np.asarray(outline, float)
    c = P.mean(0)
    nrm = _poly_normals(P)
    # rim: outer foot -> top (outer) -> top (inner) -> inner foot (into the leather)
    rings = []
    for off, hgt in ((rim, 0.0), (rim, 0.6 * h_rim), (0.6 * rim, h_rim), (0.15 * rim, h_rim), (0.0, 0.4 * h_rim)):
        Q = P + off * nrm
        rings.append(o + np.outer(Q[:, 0], u) + np.outer(Q[:, 1], v) + hgt * n)
    rim_m = grid_surface(np.array(rings), close_v=True)
    rim_m = rim_m if np.mean(np.sum(rim_m.face_normals(), 0) @ n) >= 0 else rim_m.flipped()
    # leather pad: the outline shrinking to the centre in a gentle crown
    pr = []
    for s, hgt in ((1.0, 0.4 * h_rim), (0.92, h_in + 0.2 * h_rim), (0.7, h_in + 0.25 * h_rim), (0.4, h_in + 0.3 * h_rim),
                   (0.12, h_in + 0.32 * h_rim)):
        Q = c + (P - c) * s
        pr.append(o + np.outer(Q[:, 0], u) + np.outer(Q[:, 1], v) + hgt * n)
    pg = grid_surface(np.array(pr), close_v=True)
    pf = _fan(pr[-1], o + c[0] * u + c[1] * v + (h_in + 0.33 * h_rim) * n)
    pad = Mesh.merge([m_ if np.mean(m_.face_normals() @ n) >= 0 else m_.flipped() for m_ in (pg, pf)])
    return [(rim_m, "grip_black"), (pad, "leather_black")]


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


def bellows(o, axis, ref, r_out, r_in, length, pleats=6, n=28):
    """Rubber bellows boot along axis from o: pleats folds between r_out and r_in over length, open ends."""
    axis = _unit(axis)
    ref = _unit(np.asarray(ref, float) - axis * np.dot(ref, axis))
    side = np.cross(axis, ref)
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    k = 4 * pleats + 1
    t = np.linspace(0.0, 1.0, k)
    rad = r_in + (r_out - r_in) * 0.5 * (1 + np.cos(2 * np.pi * pleats * t))      # r_out at the ends
    rad = np.r_[rad[:1], rad[1:]]
    G = np.array([o + ti * length * axis + np.outer(ri * np.cos(a), ref) + np.outer(ri * np.sin(a), side)
                  for ti, ri in zip(t, rad)])
    return _orient_out(grid_surface(G, close_v=True), lambda C: o + np.outer((C - o) @ axis, axis))


# =====================================================================================================================
# footwells (A2): dark walls round each pair of rudder pedals, the panel's underside, the cubby under the panel's
# outboard lower edge with the USB pair
# =====================================================================================================================
FOOTWELL = dict(
    inner_bl=0.1775,               # inboard walls: the nose-tunnel plinth's sides carried up to the lower panel (2 mm
    #                                outboard of the plinth wall) [M: P1046408, the dark walls beside the stack]
    outer_gap=0.020,               # outboard walls this far inside the side-wall lining [E]
    # the outboard cubby under the cheek leg (lower_panel z_bot) [M: P1046408 / 10: a dark moulding under the
    # panel's swept outboard edge, USB pair + placard]
    cubby_bl=0.580,                # its inboard edge: >= 17 mm outboard of the 95th-pct legs (max |BL| 0.556 + r)
    usb=(0.598, 1.672, 0.030, 0.024),   # USB pair module: |BL|, WL, w, h [M: P1046408 / 10]
    ceiling_gap=0.004,             # the panel's underside this far below the lower-panel edge ...
    ceiling_rise=0.050,            # ... rising this much forward of the face's return (over the rudder-bar pivots)
)


def footwell_walls():
    """[(Mesh, material)] of the footwell walls (A2): per side an inboard wall (the tunnel side, BL +/- inner_bl), an
    outboard wall following the lining, the dark underside of the panel between them, and the aft-facing cubby face
    outboard of the knees, under the cheek leg (z_bot), with its USB pair; carpet / dark moulding (carpet_flightdeck / panel_dark).  The
    rudder pedals and the 95th-pct shoes clear them by >= 10 mm (test/fit_fd_a.py check 28)."""
    FD = _FD()
    from model import interior as I
    L = FD.lining()
    FL, ZLO = FD.FL, FD.Z_LO
    q = FOOTWELL
    x0 = float(I.FLOOR["fd_x0"]) + 0.002
    xf = float(I.panel_x(ZLO))                                   # lower-panel face at its bottom edge
    xr = xf - 0.045                                              # the face's return (flightdeck._panel_face)
    zt = ZLO - q["ceiling_gap"]
    from model import seats as S

    def ztop(x):
        return zt + q["ceiling_rise"] * S.smoothstep(xr, xr - 0.15, x)
    out = []
    for sg in (-1, 1):
        # inboard wall: x0 .. the lower-panel face, floor .. the panel underside
        xs = np.linspace(x0, xf - 0.002, 10)
        zs = np.linspace(0.0, 1.0, 6)
        X, Z = np.meshgrid(xs, zs, indexing="ij")
        Z = FL + 0.0005 + Z * (ztop(X) - FL - 0.0005)
        P = np.stack([X, np.full_like(X, sg * q["inner_bl"]), Z], -1)
        out.append((FD._oriented(grid_surface(P), [0, sg, 0]), "carpet_flightdeck"))
        # outboard wall: x0 .. the cubby face, following the lining
        yo0 = float(L.hw(3.60, 0.5 * (FL + zt))) - q["outer_gap"]
        xc = float(FD.face_x(yo0, float(z_bot(yo0)) - 0.002)) - 0.004
        xs = np.linspace(x0, xc, 12)
        zs = np.linspace(0.0, 1.0, 8)
        X, Z = np.meshgrid(xs, zs, indexing="ij")
        Z = FL + 0.0005 + Z * (ztop(X) - FL - 0.0005)
        Y = sg * (L.hw(X, Z) - q["outer_gap"])
        P = np.stack([X, Y, Z], -1)
        out.append((FD._oriented(grid_surface(P), [0, -sg, 0]), "carpet_flightdeck"))
        yo = float(L.hw(xc, 0.5 * (FL + zt))) - q["outer_gap"]
        # underside of the panel between the walls: from the face's return forward to the footwell front, rising
        # forward over the rudder-bar pivots (their hubs >= 50 mm clear; fit_fd_a 28)
        ys = np.linspace(q["inner_bl"], yo + 0.002, 10)
        xs = np.linspace(x0, xr, 10)
        X, Yg = np.meshgrid(xs, ys, indexing="ij")
        Zc = zt + q["ceiling_rise"] * S.smoothstep(xr, xr - 0.15, X)
        yo_x = L.hw(X, Zc) - q["outer_gap"] + 0.002
        Yg = np.minimum(Yg, yo_x)
        P = np.stack([X, sg * Yg, Zc], -1)
        out.append((FD._oriented(grid_surface(P), [0, 0, -1.0]), "panel_dark"))
        # the cubby face (aft-facing, outboard of the knees, under the cheek leg): from the floor up to the leg's swept
        # foot (lower_panel), 4 mm behind its face; cubby_bl .. the wall
        ys = np.linspace(q["cubby_bl"], yo + 0.002, 8)
        zs = np.linspace(0.0, 1.0, 8)
        Yg, Tz = np.meshgrid(ys, zs, indexing="ij")
        Zt = z_bot(Yg) - 0.002
        Z = FL + 0.0005 + Tz * (Zt - FL - 0.0005)
        Xc = FD.face_x(Yg, Zt) - 0.004
        P = np.stack([Xc, sg * Yg, Z], -1)
        out.append((FD._oriented(grid_surface(P), [1.0, 0, 0]), "panel_dark"))
        # USB pair: a satin bezel with two dark slots, on the cubby face [M: P1046408 / 10]
        ub, uz, uw, uh = q["usb"]
        xu = float(FD.face_x(ub, float(z_bot(ub)) - 0.002)) - 0.004
        fu = FD.Fr([xu, sg * ub, uz], [0, -sg, 0], [0, 0, 1.0], [1.0, 0, 0])
        out.append((FD._extrusion(fu, FD.rrect_loop(0.5 * uw, 0.5 * uh, 0.003), 0.006, bevel=0.0012, nb=2),
                    "panel_silver"))
        for v in (-0.0045, 0.0045):
            out.append((fu.box(0.0, v, 0.0031, (0.0115, 0.0042, 0.0006)), "black"))
        out.append((fu.rect(-0.006, -0.0215, 0.006, -0.0200, 0.0004), "light_white"))        # '5V DC' stroke
        # the 1-kg weight-limit placard beside it: two abstract legend rows (P1046408 / 10)
        for v, hl in ((-0.040, 0.020), (-0.047, 0.024)):                    # centred on the cubby face
            out.append((fu.rect(-0.012 - hl, v - 0.0009, -0.012 + hl, v + 0.0009, 0.0004), "light_white"))
    return out


# =====================================================================================================================
# glareshield (A3): stitching, the lip / hood end section for the sidewall sill (track B), ECS vent pods
# =====================================================================================================================
GLARE = dict(
    stitch_pitch=0.006,            # dash pitch [M: brochure p.10 contrast stitching; owner brief 6 mm]
    stitch_dash=(0.0030, 0.0010),  # dash length, width
    stitch_rows=(0.008, 0.0115),   # double row: distances from the lip's start along the hood
    stitch_raise=0.0008,           # (above the refined hood surface: >= 0.3 mm everywhere, fit_check 26)
    crown_seam=0.100,              # a seam across the hood this far forward of the lip, double-stitched either side
    seam_w=0.0016,                 # the seam's dark welt
    end_trim=0.012,                # stitching stops this far from the hood's ends
)


def _polyline_resample(P, step):
    """Points every `step` of arc length along the polyline P (n, 3), with unit tangents."""
    P = np.asarray(P, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    sc = np.r_[0.0, np.cumsum(seg)]
    ss = np.arange(0.5 * step, sc[-1] - 0.25 * step, step)
    Q = np.c_[[np.interp(ss, sc, P[:, k]) for k in range(3)]].T
    T = np.c_[[np.interp(ss + 1e-4, sc, P[:, k]) - np.interp(ss - 1e-4, sc, P[:, k]) for k in range(3)]].T
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    return Q, T


def dashes(P, N, pitch, length, width, raise_=0.0004):
    """Stitch dashes along the polyline P (n, 3) with surface normals N (n, 3): a raised quad every `pitch`, `length`
    long along the line, `width` across.  One Mesh (2 triangles a dash)."""
    Q, T = _polyline_resample(P, pitch)
    Nq = np.c_[[np.interp(np.linspace(0, 1, len(Q)), np.linspace(0, 1, len(N)), N[:, k]) for k in range(3)]].T
    Nq /= np.maximum(np.linalg.norm(Nq, axis=1, keepdims=True), 1e-12)
    B = np.cross(Nq, T)
    B /= np.maximum(np.linalg.norm(B, axis=1, keepdims=True), 1e-12)
    c = Q + raise_ * Nq
    hl, hw = 0.5 * length, 0.5 * width
    V = np.stack([c - hl * T - hw * B, c + hl * T - hw * B, c + hl * T + hw * B, c - hl * T + hw * B], 1).reshape(-1, 3)
    k = 4 * np.arange(len(Q))[:, None]
    F = np.vstack([np.c_[k[:, 0], k[:, 0] + 1, k[:, 0] + 2], np.c_[k[:, 0], k[:, 0] + 2, k[:, 0] + 3]])
    m = Mesh(V, F)
    return m if np.mean(np.sum(m.face_normals() * np.repeat(Nq, 2, 0)[np.r_[np.arange(len(Q)), np.arange(len(Q))]],
                               1)) >= 0 else m.flipped()


def hood_lines(H, Hn, dists):
    """Lines across the hood at the given distances (m) forward of the lip's start, measured along each hood row:
    H (ny, nt, 3) the hood grid (t = 0 at the windshield, t = -1 at the lip), Hn its vertex normals.  Returns
    [(P (ny, 3), N (ny, 3))]."""
    out = []
    seg = np.linalg.norm(np.diff(H, axis=1), axis=2)                  # (ny, nt-1)
    sfromlip = np.concatenate([np.cumsum(seg[:, ::-1], axis=1)[:, ::-1], np.zeros((len(H), 1))], axis=1)
    for dist in dists:
        P, N = [], []
        for i in range(len(H)):
            sl = sfromlip[i][::-1]                                    # increasing from the lip
            P.append([np.interp(dist, sl, H[i, ::-1, k]) for k in range(3)])
            N.append([np.interp(dist, sl, Hn[i, ::-1, k]) for k in range(3)])
        out.append((np.array(P), np.array(N)))
    return out


def ecs_vent(f, rr):
    """Eyeball ECS outlet in its dark moulded pod on the panel face (frame f: w out of the face) [M: P1046408 / 10,
    brochure p.10]: a raised pod (panel_dark) round a satin bezel ring, the dark throat and the turned eyeball with its
    nozzle.  Returns [(Mesh, material)]."""
    out = []
    pod = [(0.0, rr + 0.022), (0.003, rr + 0.020), (0.0075, rr + 0.012), (0.0085, rr + 0.007), (0.0085, rr + 0.004)]
    out.append((_FD().revolve(pod, n=40, axis_origin=f.o, axis_dir=f.w, ref_dir=f.u, cap_ends=False), "panel_dark"))
    ring = [(0.0080, rr + 0.0045), (0.0105, rr + 0.0035), (0.0110, rr + 0.0005), (0.0060, rr - 0.0005)]
    out.append((_FD().revolve(ring, n=40, axis_origin=f.o, axis_dir=f.w, ref_dir=f.u, cap_ends=False), "panel_silver"))
    out.append((f.disk(0, 0, rr, 0.0040, 32), "black"))
    ball_c = f.p(0, 0, 0.0055)
    out.append((_FD().superellipsoid(ball_c, (0.62 * rr, 0.62 * rr, 0.62 * rr), (1.0, 1.0), nu=12, nv=20,
                                     R=f.R), "metal_dark"))
    out.append((_FD().cylinder(f.p(0, 0, 0.0055 + 0.50 * rr), f.p(0, 0, 0.0055 + 0.66 * rr), 0.30 * rr, n=16),
                "black"))
    return out


# =====================================================================================================================
# GFC 700 autopilot controller and the eyebrow items (A4)
# =====================================================================================================================
# GFC 700 face layout [M: P1046408 at 0.769 mm/px over the drawn GLARESHIELD afcs_wh 0.286 x 0.062]: (u, v) from its
# centre, m.  Three dividers split it into four sections (the photo shows four, not five).
GFC = dict(
    frame=0.003,                                       # raised frame width, its corner screws
    # flight deck r1 research (M4, the PRO's Pilatus-custom face, fractions of the width from the left / of the height
    # from the top -> m from the centre): dividers x 0.176 / 0.468 / 0.785
    dividers=(-0.0927, -0.0092, 0.0815),
    knobs=((-0.1115, 0.0090), (-0.0309, 0.0090), (0.0641, 0.0090)),      # FMS / MAN, HDG / TRK, ALT (x .110/.392/.724)
    knob_d=(0.017, 0.012, 0.023),                      # dual concentric: outer cap / inner cap / ring diameters
    wheel=(0.0143, 0.0074, 0.016, 0.007),              # VS thumbwheel (u, v, diameter, width) in its 7 x 28 slot
    keys=((-0.1115, -0.0192), (-0.0809, -0.0192), (-0.0561, -0.0192), (-0.0309, -0.0192), (0.0140, -0.0192),
          (0.0395, -0.0192), (0.0646, -0.0192), (0.1075, -0.0192),                     # AT APR NAV HDG VS FLC ALT L/R
          (-0.0561, 0.0167), (0.0395, 0.0167), (0.0952, 0.0167), (0.1198, 0.0167), (0.1075, -0.0012)),  # BANK VNAV AP YD FD
    key_wh=(0.012, 0.009),
    sensor=(-0.1304, 0.0205),                          # light sensor dot
)


def fluted_knob(o, axis, ref, r, h, flutes=24, depth=0.0005, per_flute=3, chamfer=0.22):
    """Knurled / fluted knob: flutes x per_flute segments (explicit count), a chamfered flat top."""
    return knob(o, axis, ref, r, h, n=flutes * per_flute, flutes=flutes, depth=depth, chamfer=chamfer)


def gfc700(f, aw, ah):
    """GFC 700 on the eyebrow fascia (frame f at the fascia centre, w out of the fascia): a black body with a raised
    satin frame and four corner screws, three light dividers, dual concentric knurled knobs (speed, HDG, ALT), the
    ribbed pitch wheel in its slot, 13 keys with legend bars.  Returns [(Mesh, material)]."""
    FD = _FD()
    q = GFC
    out = []
    body = FD._extrusion(f.moved(c=0.0045), FD.rrect_loop(0.5 * aw, 0.5 * ah, 0.004, nc=5), 0.009, bevel=0.0015, nb=2)
    out.append((body, "bezel_black"))
    fw = q["frame"]
    ring_o = FD.rrect_loop(0.5 * aw, 0.5 * ah, 0.004, nc=5)
    ring_i = FD.rrect_loop(0.5 * aw - fw, 0.5 * ah - fw, 0.002, nc=5)
    zf = 0.0092
    top_o, top_i = f.p(ring_o[:, 0], ring_o[:, 1], zf + 0.0012), f.p(ring_i[:, 0], ring_i[:, 1], zf + 0.0012)
    out.append((FD._oriented(FD._strip(top_o, top_i), f.w), "panel_dark"))
    out.append((FD._oriented(FD._strip(f.p(ring_i[:, 0], ring_i[:, 1], zf), top_i), lambda C: f.o - C), "panel_dark"))
    for su in (-1, 1):                                                 # corner screws on the frame
        for sv in (-1, 1):
            c = f.p(su * (0.5 * aw - 0.5 * fw), sv * (0.5 * ah - 0.5 * fw), zf + 0.0012)
            out.append((knob(c - 0.0004 * f.w, f.w, f.u, 0.0011, 0.0009, n=10, chamfer=0.5), "steel_dark"))
    for u in q["dividers"]:                                            # light section dividers
        out.append((f.box(u, 0.001, zf + 0.0003, (0.0010, ah - 2 * fw - 0.010, 0.0006)), "panel_silver"))
    od, idm, rd = q["knob_d"]
    for u, v in q["knobs"]:                                            # dual concentric knurled knobs on a ring
        c = f.p(u, v, zf)
        out.append((knob(c, f.w, f.u, 0.5 * rd, 0.0016, n=40, chamfer=0.15), "bezel_black"))      # ring, 23
        out.append((knob(c + 0.0016 * f.w, f.w, f.u, 0.5 * rd - 0.0004, 0.0005, n=40, chamfer=0.0, cap=False),
                    "panel_silver"))                                                           # thin silver trim
        out.append((knob(c + 0.0010 * f.w, f.w, f.u, 0.5 * rd - 0.0016, 0.0012, n=40, chamfer=0.0), "bezel_black"))
        out.append((fluted_knob(c + 0.0022 * f.w, f.w, f.u, 0.5 * od, 0.0072, flutes=24), "black"))
        out.append((fluted_knob(c + 0.0094 * f.w, f.w, f.u, 0.5 * idm, 0.0062, flutes=18, depth=0.0004), "black"))
    su_, sv_ = q["sensor"]
    out.append((knob(f.p(su_, sv_, zf - 0.0002), f.w, f.u, 0.0016, 0.0005, n=12, chamfer=0.4), "screen"))
    wu, wv, wd, ww = q["wheel"]                                        # VS thumbwheel: slot + ribbed wheel across u
    out.append((f.box(wu, wv, zf - 0.0005, (ww + 0.002, 0.028, 0.0012)), "black"))
    wc = f.p(wu, wv, zf - 0.004)
    a = np.linspace(0.0, 2 * np.pi, 60, endpoint=False)
    rw = 0.5 * wd - 0.0004 * (0.5 * (1 - np.cos(20 * a)))
    rings = [wc + np.outer(np.full(60, x), f.u) + np.outer(rw * np.cos(a), f.v) + np.outer(rw * np.sin(a), f.w)
             for x in (-0.5 * ww, 0.5 * ww)]
    wm = Mesh.merge([_orient_out(grid_surface(np.array(rings), close_v=True), lambda C: wc + np.outer((C - wc) @ f.u,
                                                                                                        f.u)),
                     _orient_out(_fan(rings[0], wc - 0.5 * ww * f.u), lambda C: C + f.u),
                     _orient_out(_fan(rings[1], wc + 0.5 * ww * f.u), lambda C: C - f.u)])
    out.append((wm, "grip_black"))
    kw, kh = q["key_wh"]
    for u, v in q["keys"]:                                             # keys: rounded caps, a light legend bar each
        fk = f.moved(u, v, zf)
        out.append((FD._extrusion(fk.moved(c=0.0012), FD.rrect_loop(0.5 * kw, 0.5 * kh, 0.0015, nc=3), 0.0024,
                                  bevel=0.0007, nb=1), "grip_black"))
        out.append((fk.rect(-0.30 * kw, -0.10 * kh, 0.30 * kw, 0.10 * kh, 0.0028), "light_white"))
    return out


def eyebrow_items(fascia_frame, zc, sg):
    """The eyebrow fascia's side items for one side (sg): BARO knob on its black plate, the master WARNING / CAUTION
    lenses in a raised frame, the RADIO-CALL placard, the photocell (pilot's side) and the screws at the fascia end
    [M: P1046408, brochure p.10].  Returns [(Mesh, material)]."""
    FD = _FD()
    D = FD.DETAIL
    out = []
    f = fascia_frame(sg * D["baro_bl"], zc)
    out.append((FD._extrusion(f.moved(c=0.0025), FD.rrect_loop(0.0155, 0.0175, 0.004, nc=4), 0.005, bevel=0.001, nb=1),
                "bezel_black"))
    out.append((fluted_knob(f.p(0, 0.002, 0.005), f.w, f.u, 0.0085, 0.0110, flutes=20), "black"))
    out.append((f.rect(-0.0012, 0.0045, 0.0012, 0.0065, 0.0165), "light_white"))                    # index
    f = fascia_frame(sg * D["warn_bl"], zc)
    out.append((FD._extrusion(f.moved(c=0.002), FD.rrect_loop(0.0375, 0.016, 0.003, nc=4), 0.004, bevel=0.0008, nb=1),
                "bezel_black"))
    for k, mat in ((-1, "annun_red"), (1, "annun_amber")):
        fk = f.moved(k * 0.019, 0.0, 0.004)
        out.append((FD._extrusion(fk.moved(c=0.0015), FD.rrect_loop(0.0155, 0.0135, 0.002, nc=3), 0.003, bevel=0.0006,
                                  nb=1), "bezel_black"))
        out.append((FD._extrusion(fk.moved(c=0.0032), FD.rrect_loop(0.0130, 0.0110, 0.0015, nc=3), 0.0016,
                                  bevel=0.0005, nb=1), mat))
    f = fascia_frame(sg * 0.372, zc - 0.012)
    out.append((FD._extrusion(f.moved(c=0.0008), FD.rrect_loop(0.0145, 0.0080, 0.0012, nc=3), 0.0016, bevel=0.0004,
                              nb=1), "bezel_black"))
    out.append((f.rect(-0.011, -0.0020, 0.011, 0.0005, 0.0020), "light_white"))                # RADIO-CALL strokes
    out.append((f.rect(-0.008, 0.0022, 0.008, 0.0042, 0.0020), "light_white"))
    if True:                                                           # round recess / photocell beside the BARO
        f = fascia_frame(sg * 0.170, zc + 0.001)                       # plate [M: P1046408, research M18]
        out.append((knob(f.o, f.w, f.u, 0.0075, 0.0020, n=28, chamfer=0.3), "bezel_black"))
        out.append((knob(f.p(0, 0, 0.0019), f.w, f.u, 0.0028, 0.0012, n=16, chamfer=0.4), "metal_dark"))
    zt_ = float(FD.lip_z(0.420)) - 2.0 * D["lip_r"]                    # the fascia's top there (rev H lip arch)
    zb_ = float(FD.z_brow(0.420))
    for zz in (zb_ + 0.30 * (zt_ - zb_), zb_ + 0.70 * (zt_ - zb_)):    # fascia end screws, within the fascia
        f = fascia_frame(sg * 0.420, zz)
        out.append((knob(f.o - 0.0003 * f.w, f.w, f.u, 0.0015, 0.0009, n=10, chamfer=0.5), "steel_dark"))
    return out


# =====================================================================================================================
# lower panel (A5): titanium sub-panels on the charcoal face, yoke wells, switch blocks, handles, sockets
# =====================================================================================================================
# [M] P1046408 (0.78 mm/px across, 0.72 up the lower panel), P1046409 / 10, JTF p.18, brochure p.10.  BL = |y|, z = WL.
LOWER = dict(
    edges=(0.290, 0.575),          # sub-panel joints: ICE PROTECTION / ACS-CPCS | yoke | outer (PARKING BRK)
    band=0.034,                    # the titanium band under the PDU row (its height), over the sub-panels
    gap=0.002,                     # dark seams between the plates
    plate_off=0.004, band_off=0.003, plate_r=0.005,
    screw=(0.008, 0.002),          # pan-head screws: inset from the plate corners, radius
    well=(0.056, 1.782, 0.050, 0.020),   # yoke well: half-width, bottom WL, depth, corner radius (open into the band)
    bellows=(0.045, 0.036, 8),     # the column's rubber bellows (on the yoke part): r_out, r_in, pleats
    # the side cheeks' legs [M: research M17 (JTF PRO / NGX), P1046408 / 10]: outboard of the yoke sub-panel the lower
    # panel's bottom edge sweeps down to 0.111 below the lower-panel edge, over |BL| 0.575 -> 0.660
    leg=(0.575, 0.660, 0.111),
    sockets=(0.665, 1.655),        # O2 mask / mic sockets on the legs: |BL|, WL
)


def z_bot(ay):
    """Bottom edge (WL) of the panel face at |BL| ay: the lower-panel edge, sweeping down over the cheek legs."""
    from model import seats as S
    y0, y1, dz = LOWER["leg"]
    return _FD().Z_LO - dz * S.smoothstep(y0, y1, np.abs(np.asarray(ay, float)))


def _face_pt(y, z, off=0.0):
    FD = _FD()
    f = FD.face_frame(float(y), float(z))
    return f.o + off * f.w


def panel_plate(outline_yz, off, mat, h=0.012, wall=True):
    """A raised plate on the (wrapped, tilted) panel face: outline (y, z) CCW, the top `off` proud along the face
    normal, side walls back to the face.  [(Mesh, material)]."""
    from model import seats as S
    FD = _FD()
    B = S._ccw(np.asarray(outline_yz, float))
    tri, G = S._cap(B, h)
    P2 = np.vstack([B, G])
    top = np.array([_face_pt(y, z, off) for y, z in P2])
    base = np.array([_face_pt(y, z, 0.0) for y, z in B])
    m = Mesh(top, tri)
    out = [(FD._oriented(m, FD.N_AFT), mat)]
    if wall:
        cen = top.mean(0) - 0.05 * FD.N_AFT
        out.append((FD._oriented(FD._flat(FD._strip(top[:len(B)], base)), lambda C: C - cen), mat))
    return out


def screw(y, z, off, r=0.002):
    """Pan-head screw on a plate (with its cross slot)."""
    FD = _FD()
    f = FD.face_frame(y, z).moved(c=off)
    return [(knob(f.o - 0.0002 * f.w, f.w, f.u, r, 0.0009, n=12, chamfer=0.6), "steel_dark"),
            (f.box(0.0, 0.0, 0.0009, (1.4 * r, 0.0005, 0.0003)), "black")]


def rocker_block(f, n, cap=(0.018, 0.028), pitch=0.023, pad=0.004, legend=True):
    """A black block of n rocker switches (caps cap w x h, a split rocking face) in frame f on the panel."""
    FD = _FD()
    out = []
    cw, ch = cap
    bw, bh = n * pitch + 2 * pad - (pitch - cw), ch + 2 * pad
    out.append((FD._extrusion(f.moved(c=0.0015), FD.rrect_loop(0.5 * bw, 0.5 * bh, 0.002, nc=3), 0.003, bevel=0.0006,
                              nb=1), "bezel_black"))
    for i in range(n):
        u = (i - 0.5 * (n - 1)) * pitch
        fk = f.moved(u, 0.0, 0.003)
        out.append((FD._extrusion(fk.moved(c=0.0015), FD.rrect_loop(0.5 * cw, 0.5 * ch, 0.0015, nc=3), 0.003,
                                  bevel=0.0008, nb=1), "grip_black"))
        # the rocking face: the upper half pressed in, the lower proud (a shallow V across the cap)
        P = np.array([fk.p(-0.45 * cw, 0.45 * ch, 0.0040), fk.p(0.45 * cw, 0.45 * ch, 0.0040),
                      fk.p(0.45 * cw, -0.02 * ch, 0.0058), fk.p(-0.45 * cw, -0.02 * ch, 0.0058),
                      fk.p(-0.45 * cw, -0.45 * ch, 0.0046), fk.p(0.45 * cw, -0.45 * ch, 0.0046)])
        m = Mesh(P, np.array([[0, 1, 2], [0, 2, 3], [3, 2, 5], [3, 5, 4]]))
        out.append((FD._oriented(FD._flat(m), f.w), "grip_black"))
        if legend:
            out.append((fk.rect(-0.28 * cw, 0.22 * ch, 0.28 * cw, 0.30 * ch, 0.0052), "light_white"))
            out.append((fk.rect(-0.20 * cw, -0.33 * ch, 0.20 * cw, -0.25 * ch, 0.0056), "light_white"))
    return out


def push_cap(f, w=0.012, h=0.012, proud=0.003, annun="annun_green"):
    """Square push-button cap (R 1, `proud` mm proud, black satin) with a legend bar and a dim annunciator split."""
    FD = _FD()
    out = [(FD._extrusion(f.moved(c=0.5 * proud), FD.rrect_loop(0.5 * w, 0.5 * h, 0.001, nc=3), proud, bevel=0.0006,
                          nb=1), "grip_black")]
    out.append((f.rect(-0.32 * w, 0.12 * h, 0.32 * w, 0.30 * h, proud + 0.0004), "light_white"))
    out.append((f.rect(-0.36 * w, -0.36 * h, 0.36 * w, -0.10 * h, proud + 0.0004), annun))
    return out


def guarded_toggle(f, guard_mat="yoke_white"):
    """Guarded toggle: a hinged U guard over a bat-handle toggle on a small base."""
    FD = _FD()
    out = [(FD._extrusion(f.moved(c=0.0015), FD.rrect_loop(0.011, 0.015, 0.002, nc=3), 0.003, bevel=0.0006, nb=1),
            "bezel_black")]
    for s_ in (-1, 1):                                                   # the guard's cheeks and its cross bar
        out.append((f.box(s_ * 0.0095, 0.0, 0.0075, (0.0022, 0.026, 0.009)), guard_mat))
    out.append((f.box(0.0, 0.0115, 0.0110, (0.021, 0.003, 0.0022)), guard_mat))
    out.append((_FD().cylinder(f.p(0, -0.002, 0.003), f.p(0, 0.003, 0.0105), 0.0018, n=10), "metal_dark"))
    out.append((_FD().superellipsoid(f.p(0, 0.0035, 0.0112), (0.0026, 0.0026, 0.0032), (0.6, 0.6), nu=8, nv=10,
                                     R=f.R), "metal_dark"))
    return out


def lower_panel(sg):
    """The lower (yoke / switch) panel of one side (sg): [(Mesh, material)] -- see flightdeck._lower_panel."""
    FD = _FD()
    from model import interior as I, seats as S
    q = LOWER
    PN, YK = I.PANEL, I.YOKE
    out = []
    shw = float(PN["stack_hw"])
    z0 = FD.Z_LO + 0.008
    z1 = FD.ZM - 0.5 * FD.PDU_H * math.cos(FD.TILT) - FD.DETAIL["recess_margin"] - 0.006
    zb = z1 - q["band"]                                                # band bottom = sub-panels' top
    yc = float(YK["bl"])
    cheek = float(PN["cheek_bl"])
    L = FD.lining()
    g = 0.5 * q["gap"]
    ww, wz0, wd, wr = q["well"]

    def yend(z):
        return min(cheek, float(L.hw(float(FD.face_x(cheek, z)), z)) - 0.008)
    # the band under the PDU row (two pieces either side of the yoke well)
    for a, b in ((shw + 0.008, yc - ww - 0.006), (yc + ww + 0.006, yend(zb))):
        ol = S.fillet(np.array([(a + g, zb + g), (b - g, zb + g), (b - g, z1 - g), (a + g, z1 - g)]), 0.004,
                      max_len=0.02)
        out += panel_plate(ol * [sg, 1] if sg > 0 else (ol * [sg, 1])[::-1], q["band_off"], "panel_titanium")
    # sub-panels: inner, yoke (notched round the well), outer
    e1, e2 = q["edges"]
    plates = [(shw + 0.008, e1), (e1, e2), (e2, yend(0.5 * (z0 + zb)))]
    r = q["plate_r"]
    # the cheek leg below the lower-panel edge: charcoal face (+ its return under the edge) behind the outer plate
    ysl = np.linspace(q["leg"][0], cheek, 14)
    zsl = np.linspace(0.0, 1.0, 6)
    Yl, Tl = np.meshgrid(ysl, zsl, indexing="ij")
    Zl = z_bot(Yl) + Tl * (FD.Z_LO + 0.002 - z_bot(Yl))
    Pl = np.stack([FD.face_x(Yl, Zl), Yl, Zl], -1)
    Pl = FD._clamp_lining(Pl, 0.004, cheek)
    Pl[..., 0] = FD.face_x(Pl[..., 1], Pl[..., 2])
    Pl[..., 1] *= sg
    out.append((FD._oriented(grid_surface(Pl), FD.N_AFT), "panel_dark"))
    bot = Pl[:, 0]
    out.append((FD._oriented(FD._strip(bot, bot - [0.045, 0.0, 0.004], closed=False), [0, 0, -1.0]), "panel_dark"))
    for k, (a, b) in enumerate(plates):
        if k == 2:                                                     # outer plate: its foot follows the leg
            yy = np.linspace(a + g, b - g, 12)
            pts = [(y_, float(z_bot(y_)) + 0.008 + g) for y_ in yy] + [(b - g, zb - g), (a + g, zb - g)]
            rad = [0.0] * len(yy) + [r, r]
            rad[0] = rad[-3] = r
            ol = S.fillet(np.array(pts), rad, max_len=0.02) * [sg, 1]
            out += panel_plate(ol if sg > 0 else ol[::-1], q["plate_off"], "panel_titanium")
            si, sr = q["screw"]
            for y_, z_ in ((a + g + si, float(z_bot(a + g + si)) + 0.008 + g + si),
                           (b - g - si, float(z_bot(b - g - si)) + 0.008 + g + si), (b - g - si, zb - g - si),
                           (a + g + si, zb - g - si)):
                out += screw(sg * y_, z_, q["plate_off"], sr)
            continue
        if k == 1:                                                     # notch for the yoke well (open at the top)
            pts = [(a + g, z0 + g), (b - g, z0 + g), (b - g, zb - g), (yc + ww + 0.006, zb - g),
                   (yc + ww + 0.006, wz0 - 0.006), (yc - ww - 0.006, wz0 - 0.006), (yc - ww - 0.006, zb - g),
                   (a + g, zb - g)]
            rad = [r, r, r, 0.003, wr + 0.006, wr + 0.006, 0.003, r]
        else:
            pts = [(a + g, z0 + g), (b - g, z0 + g), (b - g, zb - g), (a + g, zb - g)]
            rad = [r, r, r, r]
        ol = S.fillet(np.array(pts), rad, max_len=0.02)
        ol = ol * [sg, 1]
        out += panel_plate(ol if sg > 0 else ol[::-1], q["plate_off"], "panel_titanium")
        si, sr = q["screw"]
        for y_, z_ in ((a + g + si, z0 + g + si), (b - g - si, z0 + g + si), (b - g - si, zb - g - si),
                       (a + g + si, zb - g - si)):
            out += screw(sg * y_, z_, q["plate_off"], sr)
    # yoke well: walls + floor round the column (panel_dark), a satin lip round its sides and bottom, the bellows
    zt = z1 + 0.004
    W = S.fillet(np.array([(yc - ww, wz0), (yc + ww, wz0), (yc + ww, zt), (yc - ww, zt)]), [wr, wr, 0.0, 0.0],
                 max_len=0.008)
    ring_f = np.array([_face_pt(sg * y, z, 0.0) for y, z in W])
    ring_b = np.array([_face_pt(sg * y, z, -wd) for y, z in W])
    cw = ring_f.mean(0)
    out.append((FD._oriented(FD._strip(ring_f, ring_b), lambda C: cw - wd * FD.N_AFT - C), "panel_dark"))
    from cad.mesh import planar_cap
    out.append((FD._oriented(planar_cap(ring_b, FD.N_AFT), FD.N_AFT), "panel_dark"))
    lip = np.array([_face_pt(sg * y, z, q["plate_off"] - 0.001) for y, z in W[W[:, 1] < zb - 0.004]])
    if len(lip) > 3:
        from cad.mesh import sweep_profile
        prof = np.c_[0.0030 * np.cos(np.linspace(0, 2 * np.pi, 10, endpoint=False)),
                     0.0030 * np.sin(np.linspace(0, 2 * np.pi, 10, endpoint=False))]
        out.append((sweep_profile(lip, prof), "panel_silver"))
    # (the column's rubber bellows rides on the yoke: flightdeck._yokes, yoke_bellows)
    # inner sub-panel items
    if sg < 0:
        # ICE PROTECTION: two blocks of three rocker switches under their legend strokes [M: P1046408 / 10]
        for zz in (1.808, 1.752):
            f = FD.face_frame(-0.250, zz).moved(c=q["plate_off"])
            out += rocker_block(f, 3)
            out.append((f.rect(-0.034, 0.0215, 0.034, 0.0235, 0.0004), "light_white"))
        # V-LE / V-LO placard and the landing-gear handle (wheel knob on a lever in its slot, UP at the top)
        f = FD.face_frame(-0.180, 1.808).moved(c=q["plate_off"])
        out.append((FD._extrusion(f.moved(c=0.0005), FD.rrect_loop(0.0135, 0.0085, 0.001, nc=2), 0.001, bevel=0.0003,
                                  nb=1), "bezel_black"))
        for v in (-0.003, 0.003):
            out.append((f.rect(-0.010, v - 0.0008, 0.010, v + 0.0008, 0.0014), "light_white"))
        f = FD.face_frame(-0.160, 1.792).moved(c=q["plate_off"])
        out.append((FD._extrusion(f.moved(c=0.001), FD.rrect_loop(0.012, 0.047, 0.004, nc=3), 0.002, bevel=0.0005,
                                  nb=1), "bezel_black"))
        out.append((f.box(0.0, 0.0, 0.0021, (0.006, 0.084, 0.0004)), "black"))                    # the slot
        out.append((_FD().cylinder(f.p(0, 0.032, 0.001), f.p(0, 0.032, 0.040), 0.0042, n=12), "metal_dark"))
        wc = f.p(0.0, 0.032, 0.040)
        out.append((_FD().revolve([(0.0, 0.004), (0.002, 0.016), (0.005, 0.019), (0.009, 0.019), (0.012, 0.016),
                                   (0.014, 0.004)], n=40, axis_origin=wc - 0.007 * f.u, axis_dir=f.u, ref_dir=f.w,
                                  cap_ends=True), "grip_black"))
        out.append((f.rect(-0.004, 0.0405, 0.004, 0.0430, 0.0024), "light_white"))                # UP mark
        # FEATHER INHIBIT: a guarded square push button on the yoke sub-panel
        f = FD.face_frame(-0.442, 1.758).moved(c=q["plate_off"])
        out.append((FD._extrusion(f.moved(c=0.0015), FD.rrect_loop(0.0175, 0.0200, 0.003, nc=3), 0.003, bevel=0.0006,
                                  nb=1), "bezel_black"))
        out.append((FD._extrusion(f.moved(c=0.0035), FD.rrect_loop(0.0125, 0.0125, 0.002, nc=3), 0.002, bevel=0.0005,
                                  nb=1), "panel_silver"))
        out.append((FD._extrusion(f.moved(c=0.0040), FD.rrect_loop(0.0095, 0.0095, 0.0015, nc=3), 0.004, bevel=0.0007,
                                  nb=1), "grip_black"))
        out.append((f.rect(-0.012, 0.0145, 0.012, 0.0165, 0.0034), "light_white"))
        # PARKING BRK: a vertical black lozenge handle on its round boss, lower left [M: P1046410]
        f = FD.face_frame(-0.637, 1.787).moved(c=q["plate_off"])
        out.append((knob(f.o, f.w, f.u, 0.0140, 0.0050, n=32, chamfer=0.3), "panel_dark"))
        out.append((_FD().cylinder(f.p(0, 0, 0.004), f.p(0, 0, 0.020), 0.0045, n=14), "metal_dark"))
        loz = FD._fillet(np.array([(0.0, -0.034), (0.0105, -0.012), (0.0105, 0.012), (0.0, 0.034), (-0.0105, 0.012),
                                   (-0.0105, -0.012)]), 0.007, n=4, max_seg=0.01)
        out.append((FD._extrusion(f.moved(c=0.026), loz, 0.012, bevel=0.003, nb=2), "grip_black"))
        out.append((f.rect(-0.0012, -0.022, 0.0012, 0.022, 0.0324), "light_white"))                # legend stroke
    else:
        # ACS / CPCS: two placards in the band, a row of four lit push buttons, the rockers and the guarded DUMP
        # [M: P1046409, P1046408]
        for yy in (0.200, 0.244):
            f = FD.face_frame(yy, 1.851).moved(c=q["band_off"])
            out.append((FD._extrusion(f.moved(c=0.0005), FD.rrect_loop(0.0195, 0.0062, 0.001, nc=2), 0.001,
                                      bevel=0.0003, nb=1), "bezel_black"))
            for v in (-0.0022, 0.0022):
                out.append((f.rect(-0.015, v - 0.0006, 0.015, v + 0.0006, 0.0014), "light_white"))
        for yy, an in ((0.186, "annun_green"), (0.208, "annun_green"), (0.231, "annun_amber"), (0.254, "annun_green")):
            f = FD.face_frame(yy, 1.816).moved(c=q["plate_off"])
            out.append((FD._extrusion(f.moved(c=0.001), FD.rrect_loop(0.0105, 0.0105, 0.0015, nc=3), 0.002,
                                      bevel=0.0004, nb=1), "bezel_black"))
            out += push_cap(f.moved(c=0.002), 0.017, 0.017, 0.003, an)
            out.append((f.rect(-0.009, 0.0125, 0.009, 0.0140, 0.0004), "light_white"))
        f = FD.face_frame(0.188, 1.769).moved(c=q["plate_off"])
        out += rocker_block(f, 1, cap=(0.016, 0.026), legend=True)
        f = FD.face_frame(0.223, 1.769).moved(c=q["plate_off"])
        out += rocker_block(f, 1, cap=(0.016, 0.026), legend=True)
        out += guarded_toggle(FD.face_frame(0.279, 1.769).moved(c=q["plate_off"]))
        out.append((FD.face_frame(0.234, 1.792).moved(c=q["plate_off"]).rect(-0.050, -0.0008, 0.050, 0.0008, 0.0004),
                    "light_white"))
        # OXYGEN lever in its vertical slot next to the stack
        f = FD.face_frame(0.162, 1.787).moved(c=q["plate_off"])
        out.append((FD._extrusion(f.moved(c=0.001), FD.rrect_loop(0.0095, 0.050, 0.004, nc=3), 0.002, bevel=0.0005,
                                  nb=1), "bezel_black"))
        out.append((f.box(0.0, 0.0, 0.0021, (0.004, 0.088, 0.0004)), "black"))
        out.append((FD._extrusion(f.moved(0.0, -0.022, 0.012), FD.rrect_loop(0.0065, 0.010, 0.003, nc=3), 0.020,
                                  bevel=0.003, nb=2), "panel_silver"))
    # panel-end rotary knob below the eyeball vent (skirted, white index) and the O2 mask / mic socket
    yk = min(0.700, float(L.hw(3.62, 1.90)) - 0.020)
    f = FD.face_frame(sg * yk, FD.ZM + (-0.099 if sg < 0 else -0.114)).moved(c=0.002)
    out.append((knob(f.o, f.w, f.u, 0.011, 0.012, n=40, skirt=(0.0135, 0.003), chamfer=0.2), "grip_black"))
    out.append((f.rect(-0.0009, 0.004, 0.0009, 0.0085, 0.0154), "light_white"))
    ys_, zs_ = q["sockets"]
    f = FD.face_frame(sg * ys_, zs_).moved(c=q["plate_off"])
    out.append((knob(f.o, f.w, f.u, 0.020, 0.004, n=40, chamfer=0.3), "panel_dark"))
    out.append((knob(f.p(0, 0, 0.004), f.w, f.u, 0.012, 0.002, n=32, chamfer=0.2), "black"))
    out.append((knob(f.p(0, 0, 0.003), f.w, f.u, 0.0045, 0.0045, n=20, chamfer=0.3), "chrome_trim"))
    return out


# =====================================================================================================================
# centre stack + pedestal (A7)
# =====================================================================================================================
# [M] P1046408 (the waisted stack, the pad, the COM knobs on the horns), the Pilatus throttle photo (the quadrant: one
# satin-black plate in a raised gunmetal frame, brush-sealed slots, the PCL's cylinder handle on its arm, the framed
# trim panel), the JTF p.18 pedestal plan (the order fore -> aft, scaled to PEDESTAL x 3.73-4.15), P1046406 (the CCD).
STACK = dict(
    edge_r=0.012,                   # moulded radius along the stack's front edges (was 9 mm tube rails)
    horn_s=0.215,                   # the stack keeps its SDU width (PANEL stack_hw) down to here (arc length, m)
    waist=(0.335, 0.098),           # ... then narrows to the waist at the pad's foot [M: P1046408 x 830 / 1110]
    flare_s=0.385,                  # ... and flares to the quadrant's half-width (PEDESTAL hw) at its front
    pad=(0.2815, 0.0535, 0.0775, 0.012, 0.003),   # touch pad: centre s, half-length, half-width, r, recess
    bezel=0.006,                    # titanium bezel round the pad
    com=(0.222, 0.100, 0.0095),     # COM 1/2 VOL knobs on the horns: s, |y|, radius (research M6: dia 19, BL +/-0.10)
)
QUAD = dict(
    frame=(0.014, 0.006, 0.020),    # raised gunmetal frame: width, height above the plate, outer corner radius
    trim_x=(3.738, 3.800),          # framed trim panel fore / aft
    trim_items=(-0.062, -0.020, 0.024, 0.070),    # TRIM INTERRUPT, ALT STAB TRIM, AILERON TRIM, FLAP INTERRUPT (y)
    slot_w=0.012,                   # brush-sealed slots
    pcl_slot=(3.832, 3.985), flap_slot=(3.850, 3.985),
    placard_x=3.995,
    knobs=(4.020, (-0.080, -0.040, 0.0, 0.040, 0.080)),    # PILOT PFD, SDU 1, MFD, SDU 2, CO-PILOT PFD
    knobs2=(4.054, (-0.078, 0.078)),                        # PANEL / CKPT FLOOD, CAB FLOOD / CKPT DOME
    pcl_handle=0.020,               # PCL handle radius (a cylinder across the slot: its length = PEDESTAL pcl_grip w)
)


def _profile_stack():
    """Front profile (x, z) of the stack from the MFD bezel foot down the SDU face and the pad to the quadrant's front
    edge (PEDESTAL stack, x[0], top_h): dense points, arc length s, outward unit normals (aft-up)."""
    FD = _FD()
    from model import interior as I
    PE = I.PEDESTAL
    st = [(float(p[0]), FD.ZM + float(p[1])) for p in PE["stack"]]
    qx0 = float(PE["x"][0])
    zt = FD.FL + float(PE["top_h"])
    P = np.array(st + [(qx0, zt)])
    dense = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(2, int(math.ceil(np.linalg.norm(b - a) / 0.008)))
        dense += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)[1:]]
    D = np.array(dense)
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(D, axis=0), axis=1))]
    T = np.gradient(D, s, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.c_[-T[:, 1], T[:, 0]]                                        # (x, z): rotate the tangent (down-aft)
    N = np.where((N[:, :1] > 0) | ((N[:, :1] == 0) & (N[:, 1:] > 0)), N, -N)
    return D, s, N


def stack_hw(s):
    from model import interior as I
    q = STACK
    hw0, hwq = float(I.PANEL["stack_hw"]), float(I.PEDESTAL["hw"])
    sw, ww = q["waist"]
    from model import seats as S
    s = np.asarray(s, float)
    a = hw0 + (ww - hw0) * S.smoothstep(q["horn_s"], sw, s)
    return np.where(s <= sw, a, ww + (hwq - ww) * S.smoothstep(sw, q["flare_s"], s))


def stack_frame(s_, y=0.0, d=0.0):
    """Frame on the stack face at arc length s_ and BL y: u = +y, v = up the face (toward s = 0), w = out of it."""
    FD = _FD()
    D, s, N = _profile_stack()
    x = float(np.interp(s_, s, D[:, 0]))
    z = float(np.interp(s_, s, D[:, 1]))
    nx, nz = float(np.interp(s_, s, N[:, 0])), float(np.interp(s_, s, N[:, 1]))
    n = np.array([nx, 0.0, nz])
    n /= np.linalg.norm(n)
    v = np.array([-nz, 0.0, nx])                                        # up the face
    if v[2] < 0:
        v = -v
    return FD.Fr(np.array([x, y, z]) + d * n, [0, 1.0, 0], v, n)


def stack_shell():
    """The stack moulding: the front face from the MFD foot to the quadrant (SDU surround charcoal, the waist and the
    pad bezel titanium) with a moulded radius along both edges, its waisted side walls down to the plinth and back to
    the lower panel, the recessed touch pad with its bezel and lighter hand-rest lip, the COM 1/2 VOL knobs on the
    horns.  [(Mesh, material)]."""
    FD = _FD()
    from model import interior as I, seats as S
    from cad.mesh import trim
    q = STACK
    D, s, N = _profile_stack()
    hw = stack_hw(s)
    R = q["edge_r"]
    out = []
    # section across: left side end (-hw, -R) -> arc -> flat front -> arc -> (hw, -R)
    na, nf = 6, 14
    sec = []
    for k in range(na + 1):                                              # left arc: 180 -> 90 deg
        a = math.radians(180.0 - 90.0 * k / na)
        sec.append(("L", math.cos(a), math.sin(a)))
    for k in range(1, nf):
        sec.append(("F", -1.0 + 2.0 * k / nf, 0.0))
    for k in range(na + 1):
        a = math.radians(90.0 - 90.0 * k / na)
        sec.append(("R", math.cos(a), math.sin(a)))
    G, UVp = [], []
    for i in range(len(D)):
        row, uvr = [], []
        c = np.array([D[i, 0], 0.0, D[i, 1]])
        n = np.array([N[i, 0], 0.0, N[i, 1]])
        for kind, cu, su in sec:
            if kind == "F":
                y, d = cu * (hw[i] - R), 0.0
            else:
                sg = -1.0 if kind == "L" else 1.0
                y, d = sg * (hw[i] - R) + R * cu, -R + R * su
            row.append(c + y * np.array([0, 1.0, 0]) + d * n)
            uvr.append((len(uvr) / (len(sec) - 1.0), s[i]))
        G.append(row)
        UVp.append(uvr)
    G, UVp = np.array(G), np.array(UVp)
    m = grid_surface(G, UV=UVp)
    m = FD._oriented(m, lambda C: C - np.array([3.30, 0.0, 1.45]))
    sc, hl, hwp, rp, rec = q["pad"]
    bz = q["bezel"]
    fpad = sdf2d.rrect(m.V[:, 1], m.UV[:, 1], 0.0, sc, hwp, hl, rp)
    face = trim(m, fpad, keep="positive")
    # material zones along s: SDU surround (charcoal) above the pad's top bezel; titanium below
    s_sdu = float(sc - hl - bz - 0.004)
    uvF = face.UV[face.F].mean(1)
    upper = uvF[:, 1] < s_sdu
    k0, k1 = na / (len(sec) - 1.0), (len(sec) - 1.0 - na) / (len(sec) - 1.0)   # whole quads (no sawtooth)
    edge = (uvF[:, 0] < k0) | (uvF[:, 0] > k1)                         # the moulded radius edges (by section index)
    up = Mesh(face.V, face.F[upper & ~edge], face.N).compact() if np.any(upper & ~edge) else None
    lo = Mesh(face.V, face.F[~(upper & ~edge)], face.N).compact()
    if up is not None:
        out.append((up, "panel_dark"))
    out.append((lo, "panel_titanium"))
    # the recessed pad: walls + floor, a lighter lip along its foot, the bezel's raised edge
    ring = FD.rrect_loop(hwp, hl, rp, nc=6)
    ring = np.c_[ring[:, 0], ring[:, 1] + sc]

    def at(y, s_, d):
        f = stack_frame(s_, y)
        return f.o + d * f.w
    top = np.array([at(y, s_, 0.0) for y, s_ in ring])
    bot = np.array([at(y, s_, -rec) for y, s_ in ring])
    cc = at(0.0, sc, -rec - 0.05)
    out.append((FD._oriented(FD._strip(top, bot), lambda C_: cc - C_), "panel_titanium"))
    flc = planar_cap(bot, stack_frame(sc).w)
    out.append((FD._oriented(flc, stack_frame(sc).w), "panel_grey"))
    ringb = FD.rrect_loop(hwp + bz, hl + bz, rp + bz, nc=6)
    ringb = np.c_[ringb[:, 0], ringb[:, 1] + sc]
    b0 = np.array([at(y, s_, 0.0) for y, s_ in ringb])
    b1 = np.array([at(y, s_, 0.0008) for y, s_ in ring])
    out.append((FD._oriented(FD._strip(b0, b1), lambda C_: C_ - cc), "panel_titanium"))
    fl_ = stack_frame(sc + hl + 0.004)
    from cad.mesh import cylinder as _cyl
    out.append((_cyl(fl_.p(-hwp + 0.004, 0.0, 0.002), fl_.p(hwp - 0.004, 0.0, 0.002), 0.0035, n=16), "panel_silver"))
    # COM 1/2 VOL knobs on the horns + their legend strokes
    cs, cy, cr = q["com"]
    for sg in (-1, 1):
        f = stack_frame(cs, sg * cy)
        out.append((knob(f.o, f.w, f.u, cr, 0.012, n=36, skirt=(cr + 0.003, 0.0025), chamfer=0.2), "grip_black"))
        out.append((f.rect(-0.0008, 0.35 * cr, 0.0008, 0.75 * cr, 0.0149), "light_white"))
        out.append((f.rect(-0.010, cr + 0.004, 0.010, cr + 0.0055, 0.0003), "light_white"))
        out.append((f.rect(-0.012, -cr - 0.0055, 0.012, -cr - 0.004, 0.0003), "light_white"))
    # waisted side walls: the region under the front edge, down to the plinth and back to the lower panel
    x0p, x1p, phw, pz = I.pedestal_plinth()
    E = np.c_[D[:, 0] - R * N[:, 0], D[:, 1] - R * N[:, 1]]               # the edge's inner end in the side view
    xf = float(I.panel_x(FD.Z_LO)) - 0.020                             # 20 mm behind the panel face: the outline
    zz = np.linspace(E[0, 1], FD.Z_LO, 4)[1:]                          # must not fold where the stack meets it
    back = [(float(I.panel_x(z)) - 0.020, z) for z in zz]
    poly = np.vstack([E, [(E[-1, 0], pz + 0.001), (xf, pz + 0.001)], np.array(back)[::-1]])
    poly = S._ccw(S._dedup(poly, 1e-5))
    tri, Gi = S._cap(poly, 0.02)
    P2 = np.vstack([poly, Gi])
    # y of each point: the edge's half-width at the nearest profile station
    d2 = np.linalg.norm(P2[:, None, :] - E[None, :, :], axis=2)
    yv = hw[np.argmin(d2, axis=1)]
    for sg in (-1, 1):
        V = np.c_[P2[:, 0], sg * yv, P2[:, 1]]
        out.append((FD._oriented(Mesh(V, tri), [0, sg, 0]), "panel_titanium"))
    return out


def arc_scale(f, r, w, c, a0=-135.0, a1=135.0, n=28, ticks=5):
    """A white dimmer arc scale round a knob (frame f, w up): an arc band of width w at radius r from a0 to a1 deg
    (0 = toward -u, i.e. forward on the pedestal), with tick marks; c above the face."""
    a = np.radians(np.linspace(a0, a1, n))
    ca, sa = -np.cos(a), np.sin(a)
    P0 = f.p((r - 0.5 * w) * ca, (r - 0.5 * w) * sa, c)
    P1 = f.p((r + 0.5 * w) * ca, (r + 0.5 * w) * sa, c)
    parts = [_FD()._oriented(_FD()._strip(P0, P1, closed=False), f.w)]
    for t in np.radians(np.linspace(a0, a1, ticks)):
        u_, v_ = -math.cos(t), math.sin(t)
        q0, q1 = f.p((r + 0.5 * w) * u_, (r + 0.5 * w) * v_, c), f.p((r + 0.5 * w + 0.002) * u_, (r + 0.5 * w + 0.002) * v_,
                                                                        c)
        side = 0.0005 * np.array([-v_, u_])
        Q = np.array([q0 + side[0] * f.u + side[1] * f.v, q1 + side[0] * f.u + side[1] * f.v,
                      q1 - side[0] * f.u - side[1] * f.v, q0 - side[0] * f.u - side[1] * f.v])
        parts.append(_FD()._oriented(Mesh(Q, np.array([[0, 1, 2], [0, 2, 3]])), f.w))
    return Mesh.merge(parts)


def _bristles(x0, x1, y, zt, w):
    """Brush seal along a slot: two rows of black bristle fins meeting over its centre line."""
    FD = _FD()
    out = []
    for sg in (-1, 1):
        a = np.array([[x0, y + sg * 0.5 * w, zt + 0.0004], [x1, y + sg * 0.5 * w, zt + 0.0004]])
        b = np.array([[x0, y + sg * 0.0006, zt - 0.003], [x1, y + sg * 0.0006, zt - 0.003]])
        out.append((FD._oriented(FD._strip(a, b, closed=False), [0, 0, 1.0]), "rubber_black"))
    return out


def quadrant():
    """The control quadrant on the pedestal: the satin-black top plate in its raised rounded gunmetal frame, the framed
    trim panel (TRIM INTERRUPT in a raised frame, the ALT STAB TRIM and AILERON TRIM rockers, the guarded FLAP
    INTERRUPT), the brush-sealed PCL and flap slots with detent ticks and the striped reverse gate, the PCL (arm,
    pewter cylinder handle, flag), the flap paddle, the placard band, the 5 + 2 skirted lighting knobs with pointer
    lines, the CCD palm grip (PEDESTAL ccd).  [(Mesh, material)]."""
    FD = _FD()
    from model import interior as I
    from cad.mesh import cylinder as _cyl, superellipsoid as _se, box as _box
    PE = I.PEDESTAL
    q = QUAD
    FL = FD.FL
    qx0, qx1 = (float(v) for v in PE["x"])
    hw = float(PE["hw"])
    zt = FL + float(PE["top_h"])
    out = []
    fw, fh, fr = q["frame"]
    cx = 0.5 * (qx0 + qx1)
    hx = 0.5 * (qx1 - qx0)
    fp = FD.Fr([cx, 0.0, zt], [1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0])      # u = aft, v = starboard, w = up
    # plate + frame: the frame a rounded ring (outer foot -> raised round top -> inner foot)
    O = FD.rrect_loop(hx, hw, fr, nc=8)
    Iin = FD.rrect_loop(hx - fw, hw - fw, max(fr - fw, 0.004), nc=8)
    rings = []
    for t, hgt in ((0.0, 0.0), (0.0, 0.6 * fh), (0.15, fh), (0.5, fh + 0.001), (0.85, fh), (1.0, 0.6 * fh),
                   (1.0, 0.0)):
        P = O + t * (Iin - O)
        rings.append(fp.p(P[:, 0], P[:, 1], hgt))
    frame = grid_surface(np.array(rings), close_v=True)
    out.append((FD._oriented(frame, lambda C: C - fp.p(0, 0, -0.05)), "pedestal_gunmetal"))
    out.append((FD._oriented(planar_cap(fp.p(Iin[:, 0], Iin[:, 1], 0.0), [0, 0, 1.0]), [0, 0, 1.0]), "black"))
    # framed trim panel at the forward end
    tx0, tx1 = q["trim_x"]
    ft = FD.Fr([0.5 * (tx0 + tx1), 0.0, zt], [1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0])
    th = 0.5 * (tx1 - tx0)
    out.append((FD._extrusion(ft.moved(c=0.0012), FD.rrect_loop(th, hw - fw - 0.006, 0.004, nc=4), 0.0024,
                              bevel=0.0006, nb=1), "bezel_black"))
    y1, y2, y3, y4 = q["trim_items"]
    fk = ft.moved(0.004, y1, 0.0024)
    out.append((FD._extrusion(fk.moved(c=0.002), FD.rrect_loop(0.012, 0.012, 0.002, nc=3), 0.004, bevel=0.0007, nb=1),
                "pedestal_gunmetal"))
    out.append((FD._extrusion(fk.moved(c=0.004), FD.rrect_loop(0.008, 0.008, 0.0015, nc=3), 0.004, bevel=0.0007,
                              nb=1), "grip_black"))
    out.append((fk.rect(-0.004, -0.004, 0.004, 0.004, 0.0064), "annun_red"))
    for yy, horiz in ((y2, False), (y3, True)):                          # rockers in their raised bezels
        fk = ft.moved(0.006, yy, 0.0024)
        bw, bh = (0.016, 0.026) if not horiz else (0.026, 0.016)
        out.append((FD._extrusion(fk.moved(c=0.0015), FD.rrect_loop(0.5 * bh, 0.5 * bw, 0.002, nc=3), 0.003,
                                  bevel=0.0006, nb=1), "bezel_black"))
        if horiz:
            for s_ in (-1, 1):
                out.append((_se(fk.p(0.0, s_ * 0.0055, 0.0055), (0.0055, 0.0045, 0.0028), (0.4, 0.4), nu=6, nv=10),
                            "grip_black"))
            out.append((fk.box(0.0, 0.0, 0.0085, (0.004, 0.002, 0.003)), "grip_black"))
        else:
            for s_ in (-1, 1):
                out.append((_se(fk.p(s_ * 0.0058, 0.0, 0.0055), (0.0050, 0.0055, 0.0028), (0.4, 0.4), nu=6, nv=10),
                            "grip_black"))
    fk = ft.moved(0.004, y4, 0.0024)                                     # guarded FLAP INTERRUPT
    gt = FD.Fr(fk.o, fk.u, fk.v, fk.w)
    out += guarded_toggle(FD.Fr(gt.o, gt.v, -gt.u, gt.w), guard_mat="pedestal_gunmetal")
    for yy, hl in ((y1, 0.010), (y2, 0.009), (y3, 0.012), (y4, 0.011)):   # legend strokes on the trim panel
        out.append((ft.rect(-th + 0.003, yy - hl, -th + 0.0045, yy + hl, 0.0028), "light_white"))
    # slots with brush seals, detent ticks, the striped reverse gate
    sw = q["slot_w"]
    pcx, pcy, pch = (float(v) for v in PE["pcl"])
    fx, fy, fh_ = (float(v) for v in PE["flap"])
    for (a, b), yy in ((q["pcl_slot"], pcy), (q["flap_slot"], fy)):
        out.append((_box([0.5 * (a + b), yy, zt - 0.004], (b - a, sw, 0.008)), "black"))
        out += _bristles(a, b, yy, zt, sw)
    for xx in (pcx - 0.090, pcx - 0.072):                                # TO / MCP detent marks
        out.append((fp.rect(xx - cx - 0.003, pcy - sw - 0.008, xx - cx + 0.003, pcy - sw - 0.002, 0.0003),
                    "light_white"))
    out.append((fp.rect(pcx + 0.020 - cx, pcy - sw - 0.007, pcx + 0.024 - cx, pcy - sw - 0.002, 0.0003),
                "light_white"))                                          # IDLE
    for k in range(6):                                                   # striped reverse gate (abstract)
        x_ = pcx + 0.030 + 0.0055 * k
        out.append((fp.rect(x_ - cx, pcy - sw - 0.008, x_ + 0.005 - cx, pcy - sw - 0.002, 0.0003),
                    "paint_red" if k % 2 == 0 else "light_white"))
    for k in range(4):                                                   # flap detents 0 / 15 / 30 / 40
        x_ = fx - 0.050 + 0.040 * k
        out.append((fp.rect(x_ - cx - 0.0015, fy + sw, x_ - cx + 0.0015, fy + sw + 0.007, 0.0003), "light_white"))
    # PCL: dark arm from the slot to the handle, a pewter cylinder handle across, the red flag at its root
    rh = q["pcl_handle"]
    gw = float(PE["pcl_grip"][1])
    hc = np.array([pcx, pcy, FL + pch - rh])
    root = np.array([pcx + 0.022, pcy, zt - 0.006])
    tip = hc + [0.004, 0.0, -0.006]
    fa_ = FD.Fr(0.5 * (root + tip), _unit(tip - root), [0, 1.0, 0])
    out.append((FD._extrusion(FD.Fr(fa_.o, fa_.u, fa_.w, fa_.v), FD.rrect_loop(0.5 * np.linalg.norm(tip - root) + 0.004,
                                                                             0.011, 0.005, nc=4), 0.008,
                              bevel=0.002, nb=2), "metal_dark"))
    out.append((_FD().revolve([(0.0, 0.0), (0.0, 0.70 * rh), (0.003, 0.93 * rh), (0.008, rh), (gw - 0.008, rh),
                               (gw - 0.003, 0.93 * rh), (gw, 0.70 * rh), (gw, 0.0)], n=36,
                              axis_origin=hc - [0.0, 0.5 * gw, 0.0], axis_dir=[0, 1.0, 0], ref_dir=[1.0, 0, 0],
                              cap_ends=False), "pcl_pewter"))
    for k in range(3):
        out.append((_box(root + [0.0, 0.0, 0.020 + 0.006 * k], (0.010, 0.0035, 0.0055)),
                    "paint_red" if k % 2 == 0 else "light_white"))
    # flap lever: stem + black square paddle
    out.append((_cyl([fx + 0.010, fy, zt - 0.006], [fx, fy, FL + fh_ - 0.015], 0.0045, n=10), "metal_dark"))
    out.append((_se([fx, fy, FL + fh_ - 0.010], (0.012, 0.015, 0.016), (0.3, 0.3), nu=8, nv=12), "grip_black"))
    # placard band across the quadrant (abstract strokes)
    px_ = q["placard_x"]
    out.append((fp.rect(px_ - cx - 0.0035, -hw + fw + 0.008, px_ - cx + 0.0035, hw - fw - 0.008, 0.0003),
                "panel_dark"))
    out.append((fp.rect(px_ - cx - 0.0006, -hw + fw + 0.012, px_ - cx + 0.0006, hw - fw - 0.012, 0.0005),
                "light_white"))
    # lighting knobs: 5 + 2, skirted, with pointer lines and legend strokes (JTF p.18)
    kx, ky = q["knobs"]
    kx2, ky2 = q["knobs2"]
    for x_, ys_, r_ in ((kx, ky, 0.0068), (kx2, ky2, 0.0075)):
        for yy in ys_:
            f = FD.Fr([x_, yy, zt], [1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0])
            out.append((knob(f.o, f.w, f.u, r_, 0.011, n=32, skirt=(r_ + 0.0035, 0.0022), chamfer=0.2), "grip_black"))
            out.append((f.rect(-0.85 * r_, -0.0007, -0.40 * r_, 0.0007, 0.0136), "light_white"))
            out.append((f.rect(-r_ - 0.0125, -0.007, -r_ - 0.0112, 0.007, 0.0003), "light_white"))
            out.append((arc_scale(f, r_ + 0.0062, 0.0011, 0.0003), "light_white"))   # white arc scale (research M20)
    out.append((FD.Fr([kx2, 0.0, zt], [1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]).rect(-0.006, -0.032, 0.006, 0.032,
                                                                                    0.0003), "panel_dark"))
    # CCD palm grip at the aft end (PEDESTAL ccd): a black dome, its front with the scroll wheel and two keys
    ccx, ccy, cch = (float(v) for v in PE["ccd"])
    cw_, cl_ = float(PE["ccd_wl"][0]), float(PE["ccd_wl"][1])
    hgt = FL + cch - zt
    g = _se([ccx, ccy, zt], (0.5 * cl_, 0.5 * cw_, hgt), (0.45, 0.55), nu=24, nv=32)
    V = g.V.copy()
    below = V[:, 2] < zt
    V[below, 2] = zt + 0.0005 * (V[below, 2] - zt)                       # flat bottom on the plate
    tilt = (V[:, 0] - ccx) / (0.5 * cl_)                                # the dome rises toward its aft end
    V[:, 2] = zt + (V[:, 2] - zt) * (0.82 + 0.18 * np.clip(tilt, -1, 1))
    out.append((Mesh(V, g.F).compute_normals(), "grip_black"))
    fcc = FD.Fr([ccx - 0.5 * cl_ + 0.006, ccy, zt + 0.55 * hgt], [0, 1.0, 0], [0.45, 0, 0.9], [-0.9, 0, 0.45])
    a_ = np.linspace(0.0, 2 * np.pi, 40, endpoint=False)
    rw = 0.0085 - 0.0004 * (0.5 * (1 - np.cos(14 * a_)))
    wc = fcc.p(0.0, 0.0, -0.004)
    rings = [wc + np.outer(np.full(40, xx), fcc.u) + np.outer(rw * np.cos(a_), fcc.v) + np.outer(rw * np.sin(a_), fcc.w)
             for xx in (-0.005, 0.005)]
    out.append((_orient_out(grid_surface(np.array(rings), close_v=True),
                            lambda C: wc + np.outer((C - wc) @ fcc.u, fcc.u)), "panel_dark"))
    for s_ in (-1, 1):
        out.append((_se(fcc.p(s_ * 0.022, -0.004, -0.004), (0.010, 0.008, 0.005), (0.4, 0.4), nu=6, nv=10,
                        R=fcc.R), "black"))
    # trackball in its CURSOR ring on the dome's forward slope, the HOME / SCROLL rocker ahead of it, two LEDs
    # [S / M: research M19, Honeywell-Apex style]
    TD = V[g.F]

    def dome_z(x, y):                       # the built dome's top surface over (x, y) (a vertical ray), not a fit
        a, b, c = TD[:, 0], TD[:, 1], TD[:, 2]
        den = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
        ok = np.abs(den) > 1e-14
        a, b, c, den = a[ok], b[ok], c[ok], den[ok]
        l1 = ((b[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (y - c[:, 1])) / den
        l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / den
        l3 = 1.0 - l1 - l2
        hit = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        return float((l1 * a[:, 2] + l2 * b[:, 2] + l3 * c[:, 2])[hit].max())
    bx = ccx - 0.010
    bz = float(dome_z(bx, ccy))
    nrm = _unit([-0.45, 0.0, 1.0])
    out.append((_FD().revolve([(-0.004, 0.0150), (0.0006, 0.0150), (0.0016, 0.0138), (0.0016, 0.0122),
                               (-0.004, 0.0122)], n=40, axis_origin=[bx, ccy, bz], axis_dir=nrm, ref_dir=[0, 1.0, 0],
                              cap_ends=False), "panel_silver"))
    out.append((_se([bx, ccy, bz - 0.001], (0.0115, 0.0115, 0.0115), (1.0, 1.0), nu=16, nv=24), "metal_dark"))
    rx = ccx - 0.5 * cl_ + 0.016
    rz = float(dome_z(rx, ccy))
    out.append((_se([rx, ccy, rz + 0.001], (0.006, 0.014, 0.004), (0.35, 0.35), nu=8, nv=12), "black"))
    for s_ in (-1, 1):
        lz = float(dome_z(rx + 0.010, ccy + s_ * 0.020))
        out.append((_se([rx + 0.010, ccy + s_ * 0.020, lz + 0.0006], (0.0018, 0.0018, 0.0012), (1.0, 1.0), nu=6,
                        nv=10), "annun_green"))
    return out


# =====================================================================================================================
# displays and placards (A5 / A8): bezel screws, light sensor, SDU gripping lips, GI 275 ring + knob, V-speed placards
# =====================================================================================================================
def _corner_pads(fr, W, H, wo, wi, h, inset=0.0):
    """Four trapezoid corner pads on a display face (frame fr, w out): `wo` wide at the face's top / bottom edge, `wi`
    at the glass edge, `h` tall, each with a countersunk screw [M: research M2 / M3, JTF p.18]."""
    out = []
    for su in (-1, 1):
        for sv in (-1, 1):
            cu = su * (0.5 * W - inset - 0.5 * wo - 0.002)
            v0, v1 = sv * (0.5 * H), sv * (0.5 * H - h)
            from model import seats as S
            P = S._ccw(np.array([(cu - 0.5 * wo, v0), (cu + 0.5 * wo, v0), (cu + 0.5 * wi, v1), (cu - 0.5 * wi, v1)]))
            P = _FD()._fillet(P, 0.0012, n=2, max_seg=0.02)
            out.append((_FD()._flat(_FD()._extrusion(fr.moved(c=0.0003), P, 0.0006, bevel=0.0002, nb=1)), "metal_dark"))
            c = fr.p(cu, 0.5 * (v0 + v1), 0.0006)
            out.append((knob(c - 0.0002 * fr.w, fr.w, fr.u, 0.0024, 0.0005, n=12, chamfer=0.6), "steel_dark"))
    return out


def display_details():
    """Display details [M: flight deck r1 research M1-M3, JTF p.18, P1046408]: four anthracite trapezoid corner pads
    with a screw on every PDU (33 / 23 x 10) and SDU (26 / 18 x 9), a thin metal rim round each PDU's glass, the MFD's
    light sensor.  [(Mesh, material)]."""
    FD = _FD()
    out = []
    for name, kind, sg, fr, W, H, brd, kw in FD._display_specs():
        l, r, t, b = brd
        if kind != "sdu":
            out += _corner_pads(fr, W, H, 0.033, 0.023, 0.010)
            aw, ah = W - l - r, H - t - b
            cx, cy = 0.5 * (l - r), 0.5 * (b - t)
            ro = FD.rrect_loop(0.5 * aw + 0.0013, 0.5 * ah + 0.0013, 0.004, nc=4, cx=cx, cy=cy)
            ri = FD.rrect_loop(0.5 * aw, 0.5 * ah, 0.003, nc=4, cx=cx, cy=cy)
            rim = FD._strip(fr.p(ro[:, 0], ro[:, 1], 0.0003), fr.p(ri[:, 0], ri[:, 1], 0.0003))
            out.append((FD._oriented(rim, fr.w), "metal_dark"))
            if kind == "mfd":
                c = fr.p(0.5 * W - 0.030, 0.5 * H - 0.008, 0.0)
                out.append((knob(c - 0.0002 * fr.w, fr.w, fr.u, 0.0016, 0.0006, n=12, chamfer=0.4), "screen"))
        else:
            out += _corner_pads(fr, W, H, 0.026, 0.018, 0.009)
    return out


def standby_details(f, ub, ud):
    """GI 275 standby: a dark ring round the round display, its dual concentric knob in the bezel's lower-left corner
    (as P1046410 shows it on the PRO), the light sensor."""
    FD = _FD()
    r = 0.5 * ud
    out = [(FD.revolve([(0.0118, r + 0.0045), (0.0128, r + 0.0030), (0.0128, r + 0.0006), (0.0122, r)], n=48,
                       axis_origin=f.o, axis_dir=f.w, ref_dir=f.u, cap_ends=False), "metal_dark")]
    c = f.p(-0.5 * ub + 0.0085, -0.5 * ub + 0.0085, 0.0118)
    out.append((knob(c, f.w, f.u, 0.0072, 0.0030, n=36, chamfer=0.2), "black"))
    out.append((fluted_knob(c + 0.0030 * f.w, f.w, f.u, 0.0058, 0.0065, flutes=18), "black"))
    out.append((knob(f.p(0.5 * ub - 0.008, 0.5 * ub - 0.008, 0.0118), f.w, f.u, 0.0015, 0.0006, n=10, chamfer=0.4),
                "screen"))
    return out


def vspeed_placard(sg):
    """V-speed placard above the GI 275 / beside the PFD's outer edge [M: P1046408 / 10: ~45 x 50 mm above-inboard of
    the standby]: a black plate with abstract legend rows."""
    FD = _FD()
    f = FD.face_frame(sg * 0.547, 2.013).moved(c=0.0006)
    out = [(FD._extrusion(f.moved(c=0.0006), FD.rrect_loop(0.0225, 0.025, 0.0015, nc=3), 0.0012, bevel=0.0003, nb=1),
            "bezel_black")]
    for k, v in enumerate((0.016, 0.0095, 0.003, -0.0035, -0.013, -0.0195)):
        hl = 0.016 if k not in (4, 5) else 0.013
        out.append((f.rect(-hl, v - 0.0008, hl - 0.010, v + 0.0008, 0.0016), "light_white"))
        out.append((f.rect(hl - 0.008, v - 0.0008, hl, v + 0.0008, 0.0016), "light_white"))
    return out


def yoke_bellows(sg):
    """The column's rubber bellows, carried by the yoke (it moves with it): from the hub's forward face forward to the
    yoke well's floor at neutral (at full push it slides deeper behind the panel face, at full pull its end stands in
    the well), 8 pleats, OD 90 (owner brief; the bare column read as a chrome pole between the hub and the panel)."""
    FD = _FD()
    from model import interior as I
    hub = I.yoke_hub(sg)
    ww, wz0, wd, wr = LOWER["well"]
    r_o, r_i, n_p = LOWER["bellows"]
    x_floor = float(FD.face_x(sg * float(I.YOKE["bl"]), float(hub[2]))) - wd + 0.004
    L = float(hub[0]) + 0.004 - x_floor
    o = np.array([x_floor, float(hub[1]), float(hub[2])])
    return [(bellows(o, [1.0, 0, 0], [0, 1.0, 0], r_o, r_i, L, pleats=n_p, n=32), "rubber_black")]


# =====================================================================================================================
# the hook called by model/flightdeck.build_flightdeck after _pedals
# =====================================================================================================================
def _detail_a(acc):
    """Track A's extra flight-deck pieces (none yet: the owned builders call the helpers above)."""
    return acc
