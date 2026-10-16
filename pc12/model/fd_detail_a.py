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
    # flight deck fix r1 (FID-FD1-08): the pod 76 mm across (rr + 0.014; P1046408 at the GI 275's scale: ~77 against its
    # 82.6, the first build's rr + 0.022 = 92 mm read as a speaker), a slim moulded lip in the face's graphite
    pod = [(0.0, rr + 0.014), (0.003, rr + 0.0125), (0.0065, rr + 0.009), (0.0085, rr + 0.0065), (0.0085, rr + 0.004)]
    out.append((_FD().revolve(pod, n=40, axis_origin=f.o, axis_dir=f.w, ref_dir=f.u, cap_ends=False), "panel_graphite"))
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
        # flight deck fix r1 (FID-FD1-07): the knobs stand ~19 mm proud as the knurled cylinders of AOPA / P1046408
        # (the first build's 15.6 mm stack read as shallow discs), a satin ring between the outer and inner knob
        out.append((fluted_knob(c + 0.0022 * f.w, f.w, f.u, 0.5 * od, 0.0086, flutes=24), "black"))
        out.append((knob(c + 0.0108 * f.w, f.w, f.u, 0.5 * od - 0.0012, 0.0008, n=40, chamfer=0.0), "panel_silver"))
        out.append((fluted_knob(c + 0.0116 * f.w, f.w, f.u, 0.5 * idm, 0.0074, flutes=18, depth=0.0004), "black"))
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
        # raised charcoal caps 4 mm proud (FID-FD1-07: the 2.4 mm black caps vanished into the black face)
        out.append((FD._extrusion(fk.moved(c=0.0020), FD.rrect_loop(0.5 * kw, 0.5 * kh, 0.0015, nc=3), 0.0040,
                                  bevel=0.0008, nb=1), "panel_dark"))
        out.append((fk.rect(-0.30 * kw, -0.10 * kh, 0.30 * kw, 0.10 * kh, 0.0044), "light_white"))
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
    for k, mat in ((-1, "annun_off_red"), (1, "annun_off_amber")):     # unlit smoked lenses (FID-FD1-03)
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
    # the yoke's column surround: the U recess and the J band are YOKE_DESIGN column_recess / column_band / column
    # (sheet L6Y2 detail J; rev M); the column's opening in the recess floor clears it by this (m)
    col_clear=0.0010,
    # the side cheeks' legs [M: research M17 (JTF PRO / NGX), P1046408 / 10]: outboard of the yoke sub-panel the lower
    # panel's bottom edge sweeps down to 0.111 below the lower-panel edge, over |BL| 0.575 -> 0.660
    leg=(0.575, 0.660, 0.111),
    sockets=(0.665, 1.655),        # O2 mask / mic sockets on the legs: |BL|, WL
    edge_strip=0.020,              # satin trim strip down the outer plate's outboard edge (fix r2) [M: P1046409]
    # flight deck fix r3 (FID-FD3-01 / FDO3-01) [M: P1046408 / 10 at their fitted cameras]: the outer (PARKING BRK)
    # plate ends on the sub-panel row's bottom line, sweeping down `outer_drop` toward its outboard end over |BL|
    # outer_sweep; the cheek leg below it is the dark sculpted cove (fd_cove) with the USB charger and a placard, not
    # titanium; the plates' walls dark (the 2 mm seams read as dark lines), a rolled lip `lip_r` along the row's bottom
    outer_drop=0.026, outer_sweep=(0.615, 0.700),
    usb=(0.625, 1.700), lip_r=0.0045,
)


def z_bot(ay):
    """Bottom edge (WL) of the panel face at |BL| ay: the lower-panel edge, sweeping down over the cheek legs."""
    from model import seats as S
    y0, y1, dz = LOWER["leg"]
    return _FD().Z_LO - dz * S.smoothstep(y0, y1, np.abs(np.asarray(ay, float)))


def z_foot(ay):
    """Bottom edge (WL) of the sub-panel row at |BL| ay (flight deck fix r3): the row's line, sweeping down
    LOWER outer_drop over outer_sweep toward the outer plate's outboard end (never below the face's own edge)."""
    from model import seats as S
    q = LOWER
    ay = np.abs(np.asarray(ay, float))
    z = _FD().Z_LO + 0.008 - q["outer_drop"] * S.smoothstep(*q["outer_sweep"], ay)
    return np.maximum(z, z_bot(ay) + 0.008)


def _face_pt(y, z, off=0.0):
    FD = _FD()
    f = FD.face_frame(float(y), float(z))
    return f.o + off * f.w


def panel_plate(outline_yz, off, mat, h=0.012, wall=True, wall_mat=None):
    """A raised plate on the (wrapped, tilted) panel face: outline (y, z) CCW, the top `off` proud along the face
    normal, side walls back to the face (in `wall_mat`, default the plate's).  [(Mesh, material)]."""
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
        out.append((FD._oriented(FD._flat(FD._strip(top[:len(B)], base)), lambda C: C - cen), wall_mat or mat))
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


def push_cap(f, w=0.012, h=0.012, proud=0.003, annun="annun_off_green"):
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


RECESS_MARGIN = 0.0030       # the titanium plates' notch stands this far outside the recess outline (the rim flange covers it)
RECESS_MAT = "panel_dark"    # the U recess's walls, rim flange and floor (rev N, judges FID1-08: pedestal_gunmetal read pale)
BAND_MAT = "yoke_band"       # the J band: satin dark-grey metal, the slimmer dark-grey / metallic arc of P1046408 / 09
#                              (rev R, yoke judge r5 FID5-05: its own material -- the PCL grip's pcl_pewter read light)


def recess_dims():
    """(half-width, floor WL, corner R, depth, top WL) of the column recess (m): YOKE_DESIGN column_recess about the
    column axis (the hub centre)."""
    from model import interior as I
    hw, hb, rc, dep, ht = (1e-3 * float(x) for x in I.YOKE_DESIGN["column_recess"])
    zc = float(I.yoke_hub(-1)[2])
    return hw, zc + hb, rc, dep, zc + ht


def recess_outline(grow=0.0, n=10):
    """The column recess's front outline (|BL|, WL) m, closed CCW (L6Y2 detail J recess_u: a U of half-width hw about
    the column axis, floor at hb, bottom corners R rc, straight sides up to ht), its top corners R 4; grown by `grow`."""
    from model import interior as I, seats as S
    hw, zb_, rc, _, zt = recess_dims()
    yc = float(I.YOKE["bl"])
    P = np.array([(yc - hw - grow, zb_ - grow), (yc + hw + grow, zb_ - grow), (yc + hw + grow, zt + grow),
                  (yc - hw - grow, zt + grow)])
    return S.fillet(P, [rc + grow, rc + grow, 0.004 + grow, 0.004 + grow], max_len=0.004)


def recess_sdf(ay, z, grow=0.0):
    """Signed distance (m, negative inside) of the front-view points (|BL|, WL) to the recess outline grown by grow."""
    from cad import sdf2d
    return sdf2d.polygon(ay, z, recess_outline(grow))


def sleeve_depth():
    """Depth (m) of the dark sleeve behind the recess floor's column opening: the column's forward end lies 30 mm + the
    pull travel behind the floor at neutral (flightdeck._yokes) and moves the push travel further forward, so the sleeve's
    closed end stands 10 mm beyond it at full push (it was 30 mm deep: the column ran through its cap)."""
    from model import interior as I
    t0, t1 = (float(v) for v in I.YOKE["travel"])
    return 0.030 + t1 - t0 + 0.010


BAND_HOOK_END = 330.0      # deg (front view about the column axis, 0 = outboard, co-pilot sense): where the J band's
#                            hook ends under the stem -- its round end's tip (rev P; L6Y2 detail J)


def column_surround(sg):
    """The lower panel's column surround of one side (rev M, sheet L6Y2 detail J; YOKE_DESIGN column / column_band /
    column_recess): the U recess cut column_recess[3] deep from the titanium plate's top (walls + floor, a 3 mm rim
    flange over the plates' notch), the column's opening in its floor (+ a dark sleeve behind it) and the J BAND on the
    floor -- column_band[0] wide, [1] proud, R [2] rolled edges, a flat top [3] wide: its vertical leg on the inboard side
    (|BL| of its inboard side column[0]) from a round top end at WL column[1] down to the joint line (WL column[2]), then
    hooking under the stem on an arc about the column axis at h column_band[4]; a panel-fixed pan-head screw on the arc at
    WL column[3].  The band is the panel's (no bellows: none in any PRO photo).  Rev N (judges FID1-08: the band and the
    floor read as a large pale hook beside the cover): the recess walls / flange / floor charcoal (RECESS_MAT), the band
    satin pewter (BAND_MAT; rev R its own satin dark grey, yoke_band), the screw steel_dark; owner 2026-10-11 (judges
    CR1-01, fit_check 30c): the band and the recess re-centred on the column axis (the hub: joint line on it, the hook
    concentric with the column, 1 mm off it).
    [(Mesh, material)]."""
    FD = _FD()
    from model import interior as I
    from model import yoke_tri as YT
    D = I.YOKE_DESIGN
    q = LOWER
    out = []
    hw, zb_, rc, dep, zt = recess_dims()
    yc = float(I.YOKE["bl"])
    hub = I.yoke_hub(sg)
    zc = float(hub[2])
    off_top = q["plate_off"] + 0.0002
    off_floor = q["plate_off"] - dep
    W = recess_outline()                                   # CCW in (|BL|, WL)

    def pt(ay, z, off):
        return _face_pt(sg * ay, z, off)
    ring_t = np.array([pt(y, z, off_top) for y, z in W])
    ring_b = np.array([pt(y, z, off_floor) for y, z in W])
    cw = np.array([FD.face_x(sg * yc, zc), sg * yc, zc])
    out.append((FD._oriented(FD._strip(ring_t, ring_b), lambda C: cw - C), RECESS_MAT))
    # rim flange on the plates (covers their notch)
    Wo = recess_outline(RECESS_MARGIN + 0.0005)
    ring_o = np.array([pt(y, z, off_top + 0.0001) for y, z in Wo])
    out.append((FD._oriented(FD._strip(ring_o, ring_t), FD.N_AFT), RECESS_MAT))
    edge_o = np.array([pt(y, z, q["plate_off"] - 0.0005) for y, z in Wo])
    out.append((FD._oriented(FD._strip(edge_o, ring_o), lambda C: C - cw), RECESS_MAT))
    # floor with the column's opening (CDT of the U with the round hole)
    rh = float(I.YOKE["column_r"]) + q["col_clear"]
    a = np.linspace(0.0, 2 * math.pi, 48, endpoint=False)
    Hc = np.c_[yc + rh * np.cos(a), zc + rh * np.sin(a)]
    # the opening concentric with the column in the model's (y, z): the face points move along the tilted face normal
    # by off_floor, which shifted the drawn circle 0.9 mm off the axis (0.1 mm left on one side) -- pre-compensated
    for _ in range(3):
        Pq = np.array([pt(y, z, off_floor) for y, z in Hc])
        Hc = Hc + np.c_[yc + rh * np.cos(a) - sg * Pq[:, 1], zc + rh * np.sin(a) - Pq[:, 2]]
    X = np.vstack([W, Hc])
    nW = len(W)
    cons = [(i, (i + 1) % nW) for i in range(nW)] + [(nW + i, nW + (i + 1) % len(Hc)) for i in range(len(Hc))]
    T = YT.cdt(X, cons)
    T = YT.inside(T, X, [np.arange(nW), nW + np.arange(len(Hc))])
    Pf = np.array([pt(y, z, off_floor) for y, z in X])
    out.append((FD._oriented(Mesh(Pf, T), FD.N_AFT), RECESS_MAT))
    # the sleeve behind the opening (dark), closed beyond the column's forward end at full push (sleeve_depth)
    ring_h = Pf[nW:]
    ring_s = ring_h - [sleeve_depth(), 0.0, 0.0]
    out.append((FD._oriented(FD._strip(ring_h, ring_s), lambda C: np.c_[C[:, 0], np.full(len(C), sg * yc),
                                                                     np.full(len(C), zc)] - C), "panel_dark"))
    from cad.mesh import planar_cap
    out.append((FD._oriented(planar_cap(ring_s, [1.0, 0, 0]), [1.0, 0, 0]), "panel_dark"))
    # ---- the J band
    col = D["column"]
    bw, bh, br, bf, hcb = (1e-3 * float(x) for x in D["column_band"][:5])
    u_in = -(float(col[0]) - yc)                                        # its inboard side, u (< 0), m
    rcb = abs(u_in) - 0.5 * bw                                          # band centreline radius about (0, hcb)
    h_top = float(col[1]) - zc
    h_joint = float(col[2]) - zc
    h_scr = float(col[3]) - zc
    gap = 0.0005                                                         # the joint line: a 0.5 mm split
    leg = np.c_[np.full(8, -rcb), np.linspace(h_top - 0.5 * bw, h_joint + 0.5 * gap, 8)]
    a0 = math.pi + gap / rcb
    # rev P (3-D judges r3 CR3-04): the hook ends ROUND -- its centreline stops half a band width short of the drawn
    # end (BAND_HOOK_END) and the round cap reaches it, so the band's extent is the drawn one
    th = np.linspace(a0, math.radians(BAND_HOOK_END) - 0.5 * bw / rcb, 40)
    arc = np.c_[rcb * np.cos(th), hcb + rcb * np.sin(th)]
    prof = _band_profile(bw, bh, br)
    for path, cap0, cap1 in ((leg, "round", "flat"), (arc, "flat", "round")):
        for m_ in _band_sweep(path, prof, sg, yc, zc, off_floor, cap0, cap1):
            out.append((m_, BAND_MAT))
    # the screw on the arc (pan head, cross slot), on the band's top
    us = -math.sqrt(max(rcb * rcb - (h_scr - hcb) ** 2, 0.0))
    f = FD.face_frame(sg * (yc + us), zc + h_scr)
    f = f.moved(c=off_floor + bh)
    out.append((knob(f.o - 0.0002 * f.w, f.w, f.u, 0.0025, 0.0011, n=20, chamfer=0.45), "steel_dark"))
    out.append((f.box(0.0, 0.0, 0.0011, (0.0036, 0.0006, 0.0004)), "black"))
    # one consistent winding per material over the pieces that share positions (walls / floor, the band's body and
    # caps: each was oriented by its own reference direction; fit_check 23 wants every shared edge once each way)
    for mat in {m for _, m in out}:
        idx = [i for i, (_, m) in enumerate(out) if m == mat]
        newF = YT.orient_group([(out[i][0].V, out[i][0].F) for i in idx], 2e-5)
        for i, Fi in zip(idx, newF):
            out[i][0].F = Fi
    return out


def _band_profile(bw, bh, br, n_arc=5):
    """The J band's section: points (w across, z up from the floor) with outward normals, from the floor on the -w side
    over the top to the floor on the +w side; the rolled edges R br, the flat top between them."""
    P, N = [(-0.5 * bw, 0.0)], [(-1.0, 0.0)]
    P.append((-0.5 * bw, bh - br))
    N.append((-1.0, 0.0))
    for t in np.linspace(math.pi, 0.5 * math.pi, n_arc + 1)[1:]:
        P.append((-0.5 * bw + br + br * math.cos(t), bh - br + br * math.sin(t)))
        N.append((math.cos(t), math.sin(t)))
    for t in np.linspace(0.5 * math.pi, 0.0, n_arc + 1)[1:]:
        P.append((0.5 * bw - br + br * math.cos(t), bh - br + br * math.sin(t)))
        N.append((math.cos(t), math.sin(t)))
    P.append((0.5 * bw, 0.0))
    N.append((1.0, 0.0))
    return np.array(P), np.array(N)


def _band_sweep(path, prof, sg, yc, zc, off_floor, cap0, cap1="flat"):
    """The band swept along `path` ((u, h) m about the column axis, yoke-local sense: u outboard) on the recess floor:
    [Mesh]: the swept surface (exact section normals), each end closed flat or by a half revolution of the section
    (cap0 / cap1 'round': the band's round top end; rev P, 3-D judges r3 CR3-04: the hook's end too -- cut flat it read
    as a light-grey wedge beside the column)."""
    FD = _FD()
    P2, N2 = prof
    path = np.asarray(path, float)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    Nl = np.c_[-T[:, 1], T[:, 0]]                                  # left normal in (u, h)

    def to3(u, h, w_dir, w, z):
        y = sg * (yc + u + w * w_dir[0])
        zz = zc + h + w * w_dir[1]
        return _face_pt(y, zz, off_floor + z)
    fr = FD.face_frame(sg * yc, zc)

    def dir3(d2):                                                   # front-view (u, h) direction -> 3-D on the face
        v = sg * d2[0] * fr.u + d2[1] / max(float(fr.v[2]), 1e-6) * fr.v
        return v / np.linalg.norm(v)
    G, NG = [], []
    for (u, h), nl in zip(path, Nl):
        G.append([to3(u, h, nl, w, z) for w, z in P2])
        nl3 = dir3(nl)
        NG.append([_unit(nw * nl3 + nz * fr.w) for nw, nz in N2])
    G, NG = np.array(G), np.array(NG)
    k, m = G.shape[:2]
    V = G.reshape(-1, 3)
    Nn = NG.reshape(-1, 3)
    F = []
    for i in range(k - 1):
        for j in range(m - 1):
            a, b, c, d = i * m + j, (i + 1) * m + j, (i + 1) * m + j + 1, i * m + j + 1
            F += [(a, b, c), (a, c, d)]
    body = Mesh(V, np.array(F), Nn)
    # wound by its own (exact, outward) section normals -- rev N: FD._oriented's mean-normal test flipped the mirrored
    # pilot band together with its normals, so the pilot's band came out inside-out (its caps wound the other way)
    out = [_orient_by_normals(body)]

    def round_cap(c0, nl, tout):
        # a half revolution of the section's half (w <= 0) about the end's centre, from -nl over tout to +nl
        half = P2[:, 0] <= 1e-9
        ring, nring = [], []
        for ph in np.linspace(0.0, math.pi, 13):
            d2 = math.cos(ph) * (-nl) + math.sin(ph) * tout
            d3 = dir3(d2)
            ring.append([to3(c0[0], c0[1], d2, -w, z) for w, z in P2[half]])
            nring.append([_unit(-nw * d3 + nz * fr.w) for nw, nz in N2[half]])
        R_, NR = np.array(ring), np.array(nring)
        kk, mm = R_.shape[:2]
        V2, N2_ = R_.reshape(-1, 3), NR.reshape(-1, 3)
        F2 = []
        for i in range(kk - 1):
            for j in range(mm - 1):
                a, b, c, d = i * mm + j, (i + 1) * mm + j, (i + 1) * mm + j + 1, i * mm + j + 1
                F2 += [(a, b, c), (a, c, d)]
        # the flat top inside the rolled edges' revolution (rev P: rev M-O left it open -- a half-disc 'D' hole in the
        # leg's round top end): a fan from the first ring's top point, whose diameter edge is the body's flat top edge
        top = R_[:, -1]
        k0 = len(V2)
        V2 = np.vstack([V2, top])
        N2_ = np.vstack([N2_, np.tile(fr.w, (kk, 1))])
        F2 += [(k0, k0 + i, k0 + i + 1) for i in range(1, kk - 1)]
        return _orient_by_normals(Mesh(V2, np.array(F2), N2_))
    if cap1 == "round":
        out.append(round_cap(path[-1], Nl[-1], T[-1]))
    else:
        endr = G[-1]
        out.append(FD._oriented(_fan(endr, endr.mean(0)), dir3(T[-1])))
    if cap0 == "round":
        out.append(round_cap(path[0], Nl[0], -T[0]))
    else:
        st = G[0]
        out.append(FD._oriented(_fan(st, st.mean(0)), -dir3(T[0])))
    return out


def _orient_by_normals(m):
    """Wind every face of m so its geometric normal agrees with its corner normals."""
    fn = np.cross(m.V[m.F[:, 1]] - m.V[m.F[:, 0]], m.V[m.F[:, 2]] - m.V[m.F[:, 0]])
    flip = np.sum(fn * m.N[m.F].sum(1), 1) < 0
    F = m.F.copy()
    F[flip] = F[flip][:, ::-1]
    return Mesh(m.V, F, m.N)


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
    ww, wz0, wr, wd, zt_r = recess_dims()
    mrg = RECESS_MARGIN

    def yend(z):
        return min(cheek, float(L.hw(float(FD.face_x(cheek, z)), z)) - 0.008)
    # the band under the PDU row: two pieces either side of the column recess and a bridge over its top (rev M)
    # rev N (judges CR1-01; owner 2026-10-11: band + recess re-centred on the column axis): the U runs up through the
    # band (column_recess top h 27: the column, r 22 about the hub, stands 5 mm clear), its rim flange's top edge on the
    # band's top edge -- the bridge over the U is gone
    if zt_r + mrg + 0.0005 > z1 + 1e-4:
        raise ValueError("column recess: its rim flange would stand above the titanium band under the PDU row")
    pieces = [(shw + 0.008, yc - ww - mrg, zb), (yc + ww + mrg, yend(zb), zb)]
    if z1 - (zt_r + mrg) > 0.008:                                        # a bridge over the U (rev M) where it fits
        pieces.append((yc - ww - mrg, yc + ww + mrg, zt_r + mrg))
    for a, b, za in pieces:
        ol = S.fillet(np.array([(a + g, za + g), (b - g, za + g), (b - g, z1 - g), (a + g, z1 - g)]), 0.004,
                      max_len=0.02)
        out += panel_plate(ol * [sg, 1] if sg > 0 else (ol * [sg, 1])[::-1], q["band_off"], "panel_titanium",
                           wall_mat="panel_dark")
    # sub-panels: inner, yoke (notched round the well), outer
    e1, e2 = q["edges"]
    plates = [(shw + 0.008, e1), (e1, e2), (e2, yend(0.5 * (z0 + zb)))]
    r = q["plate_r"]
    # the cheek leg below the lower-panel edge: the graphite face (+ its charcoal return under the edge) behind the
    # outer plate
    ysl = np.linspace(q["leg"][0], cheek, 14)
    zsl = np.linspace(0.0, 1.0, 6)
    Yl, Tl = np.meshgrid(ysl, zsl, indexing="ij")
    # (its top just under the face's bottom edge: since flight deck fix r3 the leg is the cove's own material, and the
    # 2 mm the graphite leg ran up behind the face overlapped it coplanar -- fit_check 26)
    Zl = z_bot(Yl) + Tl * (FD.Z_LO - 0.0002 - z_bot(Yl))
    Pl = np.stack([FD.face_x(Yl, Zl), Yl, Zl], -1)
    Pl = FD._clamp_lining(Pl, 0.004, cheek)
    Pl[..., 0] = FD.face_x(Pl[..., 1], Pl[..., 2])
    Pl[..., 1] *= sg
    out.append((FD._oriented(grid_surface(Pl), FD.N_AFT), "fd_cove"))         # (fix r3: the dark cove, was graphite)
    bot = Pl[:, 0]
    out.append((FD._oriented(FD._strip(bot, bot - [0.045, 0.0, 0.004], closed=False), [0, 0, -1.0]), "panel_dark"))
    for k, (a, b) in enumerate(plates):
        if k == 2:                                                     # outer plate: its foot sweeps down outboard
            yy = np.linspace(a + g, b - g, 12)
            pts = [(y_, float(z_foot(y_)) + g) for y_ in yy] + [(b - g, zb - g), (a + g, zb - g)]
            rad = [0.0] * len(yy) + [r, r]
            rad[0] = rad[-3] = r
            ol = S.fillet(np.array(pts), rad, max_len=0.02) * [sg, 1]
            out += panel_plate(ol if sg > 0 else ol[::-1], q["plate_off"], "panel_titanium", wall_mat="panel_dark")
            si, sr = q["screw"]
            for y_, z_ in ((a + g + si, float(z_foot(a + g + si)) + g + si),
                           (b - g - si, float(z_foot(b - g - si)) + g + si), (b - g - si, zb - g - si),
                           (a + g + si, zb - g - si)):
                out += screw(sg * y_, z_, q["plate_off"], sr)
            # (flight deck fix r2 FID-FD2-03) the satin trim strip down the panel's outboard edge -- from the band to the
            # leg's foot, where the panel meets the side wall above the CB panels (P1046409: the bright vertical
            # titanium swoop between the outer sub-panel and the breakers)
            # (1 mm inside the plates' edges all round: its walls must not lie on theirs -- fit_check 26)
            tw_, e_ = q["edge_strip"], 0.001
            zs_ = np.linspace(float(z_foot(b - g)) + g + e_, z1 - g - e_, 10)
            pts = [(b - g - e_ - tw_, z_) for z_ in zs_] + [(b - g - e_, z_) for z_ in zs_[::-1]]
            ol = S.fillet(np.array(pts), [0.003] + [0.0] * 8 + [0.003, 0.003] + [0.0] * 8 + [0.003], max_len=0.02)
            ol = ol * [sg, 1]
            out += panel_plate(ol if sg > 0 else ol[::-1], q["plate_off"] + 0.0025, "panel_silver")
            continue
        if k == 1:                                                     # notch for the column recess (open at the top)
            pts = [(a + g, z0 + g), (b - g, z0 + g), (b - g, zb - g), (yc + ww + mrg, zb - g),
                   (yc + ww + mrg, wz0 - mrg), (yc - ww - mrg, wz0 - mrg), (yc - ww - mrg, zb - g),
                   (a + g, zb - g)]
            rad = [r, r, r, 0.002, wr + mrg, wr + mrg, 0.002, r]
        else:
            pts = [(a + g, z0 + g), (b - g, z0 + g), (b - g, zb - g), (a + g, zb - g)]
            rad = [r, r, r, r]
        ol = S.fillet(np.array(pts), rad, max_len=0.02)
        ol = ol * [sg, 1]
        out += panel_plate(ol if sg > 0 else ol[::-1], q["plate_off"], "panel_titanium", wall_mat="panel_dark")
        si, sr = q["screw"]
        for y_, z_ in ((a + g + si, z0 + g + si), (b - g - si, z0 + g + si), (b - g - si, zb - g - si),
                       (a + g + si, zb - g - si)):
            out += screw(sg * y_, z_, q["plate_off"], sr)
    # (flight deck fix r3 FID-FD3-01) the rolled lip along the sub-panel row's bottom edge: a satin half-round under the
    # plates' foot from the stack to the outer plate's outboard end (P1046408: the light-catching rolled edge over the
    # dark knee well), and the cove's dual USB charger with its legend stroke [M: P1046408 / 10]
    from cad.mesh import sweep_profile
    lr = q["lip_r"]
    yl = np.linspace(shw + 0.008 + g, plates[2][1] - g - 0.004, 60)
    lip = np.array([_face_pt(sg * y_, float(z_foot(y_)) + g - 0.25 * lr, q["plate_off"] - 0.9 * lr) for y_ in yl])
    ang = np.linspace(0, 2 * np.pi, 14, endpoint=False)
    out.append((sweep_profile(lip, np.c_[lr * np.cos(ang), lr * np.sin(ang)]), "trim_satin"))
    uy, uz = q["usb"]
    f = FD.face_frame(sg * uy, uz).moved(c=0.0005)
    out.append((FD._extrusion(f, FD.rrect_loop(0.0125, 0.0085, 0.002, nc=3), 0.003, bevel=0.0007, nb=1),
                "bezel_black"))
    for du in (-0.0045, 0.0045):
        out.append((FD._extrusion(f.moved(du, 0.0, 0.003), FD.rrect_loop(0.0016, 0.0042, 0.0012, nc=2), 0.0006,
                                  bevel=0.0002, nb=1), "black"))
    out.append((f.rect(-0.008, -0.0145, 0.008, -0.0125, 0.0001), "light_white"))
    out += column_surround(sg)
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
        for yy, an in ((0.186, "annun_off_green"), (0.208, "annun_off_green"), (0.231, "annun_off_amber"),
                       (0.254, "annun_off_green")):                 # unlit on a parked aircraft (FID-FD1-03)
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
    pad=(0.2815, 0.0535, 0.0775, 0.012, 0.005),   # touch pad: centre s, half-length, half-width, r, recess (fix r2: 5)
    bezel=0.0045,                   # the rolled bead round the pad (its width; fix r2 FDO2-04; fix r5 FDO4-03: 6 -> 4.5 mm,
    #                                 dark bronze -- P1046409 / 10: a dark bronze rim, the light tube read as a frame)
    dish=0.0025,                    # the pad floor's sag at its middle (fix r3 FDO3-01)
    com=(0.222, 0.100, 0.0095),     # COM 1/2 VOL knobs on the horns: s, |y|, radius (research M6: dia 19, BL +/-0.10)
)
QUAD = dict(
    frame=(0.014, 0.006, 0.020),    # raised gunmetal frame: width, height above the plate, outer corner radius
    trim_x=(3.738, 3.800),          # framed trim panel fore / aft
    trim_items=(-0.062, -0.020, 0.024, 0.070),    # TRIM INTERRUPT, ALT STAB TRIM, AILERON TRIM, FLAP INTERRUPT (y)
    trim_k=1.3,                     # the trim items' bezels / caps x this (fix r5 FID-FD4-03) [M: throttle photo]
    slot_w=0.012,                   # brush-sealed slots
    pcl_slot=(3.832, 3.985), flap_slot=(3.850, 3.985),
    placard_x=3.995,
    knobs=(4.020, (-0.080, -0.040, 0.0, 0.040, 0.080)),    # PILOT PFD, SDU 1, MFD, SDU 2, CO-PILOT PFD
    knobs2=(4.054, (-0.078, 0.078)),                        # PANEL / CKPT FLOOD, CAB FLOOD / CKPT DOME
    pcl_tines=(0.015, 0.0025, 0.0045),   # forked arm: tine width, thickness, the gap between them (fix r2) [M]
)
# the PCL grip (flight deck fix r5 FDO4-05 / FID-FD4-03; the turned cylinder of fix r2 / r3 read as a can / glass jar
# from the seats) [M: P1046408 / 09 through their fitted cameras, the Pilatus throttle photo]: a satin pewter PADDLE of
# PEDESTAL pcl_grip's 36 x 80 x 72 (fore-aft, width, height incl. the neck) -- a superellipsoid across the slot (ends
# `e_end`: flat with rounded edges, section `e_sec`: a rounded oval), its width narrowing to `w_bot` of the top's at the
# body's foot and its section to `d_bot` (from behind the photos' trapezoid, ~80 wide at the rounded top, ~56 at the
# foot), its top tipped forward by `lean` deg; on a `neck` tall dark stem of radius `neck_r` into the forked arm
PCL_PADDLE = dict(e_end=0.38, e_sec=0.80, w_bot=0.70, d_bot=0.72, lean=12.0, neck=0.012, neck_r=0.0095, nu=16, nv=32)


def pcl_paddle(c, hx, hy, hz):
    """The PCL paddle grip's body (PCL_PADDLE) centred at c: half-depth hx (fore-aft), half-width hy, half-height hz."""
    from cad.mesh import superellipsoid
    q = PCL_PADDLE
    m = superellipsoid([0.0, 0.0, 0.0], (hx, hz, hy), e=(q["e_end"], q["e_sec"]), nu=q["nu"], nv=q["nv"])
    X, Zl, Yl = m.V[:, 0].copy(), m.V[:, 1].copy(), m.V[:, 2].copy()     # local: x fore-aft, y up, z lateral (poles)
    t = np.clip((Zl + hz) / (2.0 * hz), 0.0, 1.0)                       # 0 at the body's foot .. 1 at its top
    ky = q["w_bot"] + (1.0 - q["w_bot"]) * t * (2.0 - t)                 # the trapezoid, rounding into the top
    kx = q["d_bot"] + (1.0 - q["d_bot"]) * np.sqrt(t)
    V = np.c_[kx * X - math.tan(math.radians(q["lean"])) * Zl, ky * Yl, Zl] + np.asarray(c, float)
    out = Mesh(V, m.F).compute_normals()
    if np.mean(np.sum((out.V - np.asarray(c, float)) * out.N, 1)) < 0:
        out = out.flipped()
    return out


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
    if up is not None:
        out.append((up, "panel_dark"))
    # (flight deck fix r2 FID-FD2-03: the stack's lower face in the graphite -- the titanium read as pale grey plastic
    # round the pad, 150-170 at panel_408b against P1046408's ~100-120 -- so the pad's bead and lid read against it)
    # (flight deck fix r5 FDO4-03 / FID-FD4-03: the shroud round the tray still read as light-grey plastic, 130-150 from
    # above; the photos' a dark gunmetal with a thin bright edge: the face and its moulded radius edges the stack's
    # satin gunmetal -- the rolled edges catch the thin highlight; as broad titanium bands they read as light strips
    # down both sides of the stack at panel_408b and from the seats)
    out.append((Mesh(face.V, face.F[~(upper & ~edge)], face.N).compact(), "stack_gunmetal"))
    # the recessed pad: walls + floor, a lighter lip along its foot, the bezel's raised edge
    ring = FD.rrect_loop(hwp, hl, rp, nc=6)
    ring = np.c_[ring[:, 0], ring[:, 1] + sc]

    def at(y, s_, d):
        f = stack_frame(s_, y)
        return f.o + d * f.w
    top = np.array([at(y, s_, 0.0) for y, s_ in ring])
    bot = np.array([at(y, s_, -rec) for y, s_ in ring])
    cc = at(0.0, sc, -rec - 0.05)
    # flight deck fix r2 (FDO2-04: the palm tray read as a blank light slab): a recessed tray -- graphite walls, a satin
    # titanium floor 5 mm down (P1046408 / 09: the lid a mid grey a shade under its bezel) -- under a rolled light
    # satin bead round its edge (the photos' lighter bevelled lip)
    out.append((FD._oriented(FD._strip(top, bot), lambda C_: cc - C_), "panel_graphite"))
    # (flight deck fix r3 FDO3-01 / FDO3-05: the flat floor read as a uniform light square, luminance sd 1) the floor
    # dished `dish` m at its middle, falling smoothly from its edge over the first 35 mm, so it shades like a palm tray
    B2 = S._ccw(np.asarray(ring, float))
    tri, Gi = S._cap(B2, 0.008)
    P2 = np.vstack([B2, Gi])
    d_in = np.maximum(-sdf2d.rrect(P2[:, 0], P2[:, 1], 0.0, sc, hwp, hl, rp), 0.0)
    dz = -rec - q["dish"] * S.smoothstep(0.0, 0.035, d_in)
    flc = Mesh(np.array([at(y_, s_, d_) for (y_, s_), d_ in zip(P2, dz)]), tri)
    out.append((FD._oriented(flc, stack_frame(sc).w), "tray_titanium"))     # (fix r5 FDO4-03: matte warm titanium)
    rb = 0.5 * bz                                                       # the bead: a half round on the face, its inner
    rings = []                                                          # side rolling into the tray wall
    for phi in np.radians(np.linspace(0.0, 180.0, 9)):
        off, dd = rb * (1.0 + math.cos(phi)), rb * math.sin(phi)
        rl = FD.rrect_loop(hwp + off, hl + off, rp + off, nc=6)
        rings.append(np.array([at(y, s_ + sc, dd) for y, s_ in rl]))
    bead = grid_surface(np.array(rings), close_v=True)
    out.append((FD._oriented(bead, lambda C_: C_ - cc), "trim_bronze"))
    fl_ = stack_frame(sc + hl + 0.004)
    from cad.mesh import cylinder as _cyl
    out.append((_cyl(fl_.p(-hwp + 0.004, 0.0, 0.002), fl_.p(hwp - 0.004, 0.0, 0.002), 0.0035, n=16), "trim_bronze"))
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
    # (flight deck fix r2 FID-FD2-03: the flanks a gunmetal like the quadrant's cheeks -- P1046408 reads them ~46, the
    # titanium rendered 73: pale grey plastic; its own name, `stack_gunmetal`: consistency_2d3d finds the quadrant's top
    # by the pedestal_gunmetal / panel faces at its height)
    for sg in (-1, 1):
        V = np.c_[P2[:, 0], sg * yv, P2[:, 1]]
        out.append((FD._oriented(Mesh(V, tri), [0, sg, 0]), "stack_gunmetal"))
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


def _bristles(x0, x1, y, zt, w, pitch=0.0016):
    """Brush seal along a slot: two rows of black bristle fins meeting over its centre line, and over them the tufts --
    thin fins across the slot every `pitch`, alternately long and short (flight deck fix r3 FID-FD3-07: the two flat
    strips read as a plain dark slot; the throttle photo's seals are a ragged fringe)."""
    FD = _FD()
    out = []
    for sg in (-1, 1):
        a = np.array([[x0, y + sg * 0.5 * w, zt + 0.0004], [x1, y + sg * 0.5 * w, zt + 0.0004]])
        b = np.array([[x0, y + sg * 0.0006, zt - 0.003], [x1, y + sg * 0.0006, zt - 0.003]])
        # dark grey fibres against the black slot (FDO1-07: the throttle photo's brush seals read; rubber_black did not)
        out.append((FD._oriented(FD._strip(a, b, closed=False), [0, 0, 1.0]), "brush_seal"))
    rng = np.random.default_rng(int(1e4 * abs(y)) + 7)
    V, F = [], []
    for sg in (-1, 1):
        for x_ in np.arange(x0 + 0.001, x1 - 0.001, pitch):
            reach = (0.5 * w - 0.0004) * (0.80 + 0.2 * rng.random())       # tuft length from the slot's edge
            xa = x_ + 0.0003 * (rng.random() - 0.5)
            k = len(V)
            ye, yt = y + sg * 0.5 * w, y + sg * (0.5 * w - reach)
            V += [(xa - 0.00035, ye, zt + 0.0006), (xa + 0.00035, ye, zt + 0.0006),
                  (xa + 0.00025, yt, zt - 0.0012), (xa - 0.00025, yt, zt - 0.0012)]
            F += [(k, k + 1, k + 2), (k, k + 2, k + 3)]
    if V:
        out.append((FD._oriented(Mesh(np.array(V, float), np.array(F)), [0, 0, 1.0]), "brush_seal"))
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
    # (flight deck fix r5 FID-FD4-03: from the seats the trim panel read as three tiny switches; the Pilatus throttle
    # photo and P1046409 / 10 show each item in its own black bezel, the bezels ~1.3 x the first build's: TRIM
    # INTERRUPT a 30 mm framed square, the rockers in 22 x 34 mm bezels with the caps to match)
    k5 = q["trim_k"]
    fk = ft.moved(0.004, y1, 0.0024)
    out.append((FD._extrusion(fk.moved(c=0.002), FD.rrect_loop(0.012 * k5, 0.012 * k5, 0.002, nc=3), 0.004,
                              bevel=0.0007, nb=1), "pedestal_gunmetal"))
    # TRIM INTERRUPT: a proud gloss-black square cap with a rolled rim, unlit (FID-FD1-03: the Pilatus throttle photo; the
    # red cap read as an alarm on the parked aircraft)
    # (flight deck fix FDY r2 FDY-O2-04: the white frame stroke on its top read as a bare outline square -- a placeholder
    # -- from the pedestal close-up; the throttle photo shows a black cap standing ~3 mm proud of its bezel, its rolled
    # rim catching the light, no stroke on it)
    out.append((FD._extrusion(fk.moved(c=0.0045), FD.rrect_loop(0.0082 * k5, 0.0082 * k5, 0.0018, nc=3), 0.005,
                              bevel=0.0012, nb=2), "gloss_black"))
    # the trim rockers: solid gloss-black caps in their raised bezels, split across the middle (the two halves of the
    # rocker, one pressed: 1.5 mm lower), each half with one short legend stroke on it (DOWN / UP, LWD / RWD: abstract)
    # (fix FDY r2 FDY-O2-04: the r5 superellipsoid bumps with the AILERON TRIM bezel's white outline read as bare white
    # outlines; the throttle photo: framed black rocker caps standing in black bezels)
    for yy, horiz in ((y2, False), (y3, True)):
        fk = ft.moved(0.006, yy, 0.0024)
        bw, bh = (0.016 * k5, 0.026 * k5) if not horiz else (0.026 * k5, 0.016 * k5)
        out.append((FD._extrusion(fk.moved(c=0.0015), FD.rrect_loop(0.5 * bh, 0.5 * bw, 0.002, nc=3), 0.003,
                                  bevel=0.0006, nb=1), "bezel_black"))
        cu, cv = 0.40 * bh, 0.37 * bw                     # the cap's half extent (u fore-aft, v across)
        gap = 0.0006
        for s_, top in ((-1, 0.0072), (1, 0.0058)):
            if horiz:      # split across v
                hu, hv, cu_, cv_ = cu, 0.5 * (cv - gap), 0.0, s_ * 0.5 * (cv + gap)
            else:          # split across u
                hu, hv, cu_, cv_ = 0.5 * (cu - gap), cv, s_ * 0.5 * (cu + gap), 0.0
            dep = top - 0.0020
            out.append((FD._extrusion(fk.moved(cu_, cv_, top - 0.5 * dep), FD.rrect_loop(hu, hv, 0.0012, nc=3), dep,
                                      bevel=0.0009, nb=2), "gloss_black"))
            lv = 0.45 * hv
            if horiz:
                out.append((fk.rect(cu_ - 0.45 * hu, cv_ - 0.0006, cu_ + 0.45 * hu, cv_ + 0.0006, top + 0.0002),
                            "light_white"))
            else:
                out.append((fk.rect(cu_ - 0.0006, cv_ - lv, cu_ + 0.0006, cv_ + lv, top + 0.0002), "light_white"))
    fk = ft.moved(0.004, y4, 0.0024)                                     # guarded FLAP INTERRUPT
    gt = FD.Fr(fk.o, fk.u, fk.v, fk.w)
    out += guarded_toggle(FD.Fr(gt.o, gt.v, -gt.u, gt.w), guard_mat="pedestal_gunmetal")
    # legend strokes on the trim panel: each item's title in two rows of word-length strokes ahead of it (fix r5
    # FID-FD4-03: one bar per item read as a bare panel; P1046408 / 09: TRIM / INTERRUPT, ALTERNATE / STAB TRIM,
    # AILERON TRIM, FLAP / INTERRUPT), the AILERON TRIM bezel's white outline with its LWD / RWD marks
    for yy, rows in ((y1, ((0.008,), (0.017,))), (y2, ((0.017,), (0.007, 0.008))), (y3, ((0.013, 0.009),)),
                     (y4, ((0.007,), (0.017,)))):
        for r_, words in enumerate(rows):
            u0 = -th + 0.0030 + 0.0042 * r_
            tot = sum(words) + 0.0025 * (len(words) - 1)
            v = yy - 0.5 * tot
            for w_ in words:
                out.append((ft.rect(u0, v, u0 + 0.0016, v + w_, 0.0028), "light_white"))
                v += w_ + 0.0025
    bw, bh = 0.026 * k5, 0.016 * k5
    oa, ob = 0.5 * bh + 0.0012, 0.5 * bw + 0.0012
    for s_ in (-1, 1):                                                   # LWD / RWD marks (the outline went, FDY r2)
        out.append((ft.rect(0.006 + oa + 0.0020, y3 + s_ * 0.6 * ob - 0.0030, 0.006 + oa + 0.0034,
                            y3 + s_ * 0.6 * ob + 0.0030, 0.0028), "light_white"))
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
    for k in range(4):                                                   # flap detents 0 / 15 / 30 / 40 (fix r3:
        x_ = fx - 0.050 + 0.040 * k                                      # bolder, FID-FD3-07)
        out.append((fp.rect(x_ - cx - 0.0022, fy + sw, x_ - cx + 0.0022, fy + sw + 0.009, 0.0003), "light_white"))
    # PCL: dark arm from the slot to the handle, the satin pewter paddle grip on its neck, the red flag at its root
    # (flight deck fix r5 FDO4-05 / FID-FD4-03: the turned cylinder of r2 / r3 -- 40 mm across, PEDESTAL pcl_grip's
    # height not used -- read as a can / glass jar from the seats; P1046408 / 09 through their cameras show a PADDLE:
    # from behind a trapezoid ~80 wide at its rounded top narrowing to ~56 over the body, on a short neck into the dark
    # arm; from the side (the Pilatus throttle photo) a rounded oval section.  Built now to the table's 36 x 80 x 72:
    # PCL_PADDLE)
    gd, gw, gh = (float(v) for v in PE["pcl_grip"])
    pp = PCL_PADDLE
    top = FL + pch
    bh = 0.5 * (gh - pp["neck"])                                         # the body's half height
    zc = top - bh
    neck_bot = top - gh
    lean = math.radians(pp["lean"])
    root = np.array([pcx + 0.022, pcy, zt - 0.006])
    tip = np.array([pcx + math.tan(lean) * bh, pcy, neck_bot])
    fa_ = FD.Fr(0.5 * (root + tip), _unit(tip - root), [0, 1.0, 0])
    tw, tt, tg = q["pcl_tines"]
    for s_ in (-1, 1):
        ft = FD.Fr(fa_.o + s_ * (0.5 * tg + 0.5 * tt) * np.array([0, 1.0, 0]), fa_.u, fa_.w, fa_.v)
        out.append((FD._extrusion(ft, FD.rrect_loop(0.5 * np.linalg.norm(tip - root) + 0.004, 0.5 * tw, 0.004, nc=4),
                                  tt, bevel=0.0008, nb=1), "metal_dark"))
    out.append((_box(root + [0.0, 0.0, 0.004], (0.016, tg + 2 * tt, 0.010)), "metal_dark"))   # the clevis in the slot
    out.append((pcl_paddle(np.array([pcx, pcy, zc]), 0.5 * gd, 0.5 * gw, bh), "pcl_pewter"))
    # the neck: a satin-dark stem from the arm's tip into the body's underside, a chrome collar at its foot (the
    # Pilatus throttle photo's root ring)
    nr = pp["neck_r"]
    nk_top = np.array([pcx + math.tan(lean) * 0.45 * bh, pcy, zc - 0.45 * bh])   # inside the body, on its lean
    ln = float(np.linalg.norm(nk_top - tip))                            # flaring into the body (P1046408 / 09)
    out.append((_FD().revolve([(0.0, 0.0), (0.0, nr), (0.35 * ln, 1.04 * nr), (0.6 * ln, 1.18 * nr),
                               (0.8 * ln, 1.32 * nr), (ln, 1.5 * nr), (ln, 0.0)], n=24, axis_origin=tip,
                              axis_dir=_unit(nk_top - tip), ref_dir=[0, 1.0, 0], cap_ends=False), "metal_dark"))
    out.append((_FD().revolve([(0.0, 0.0), (0.0, nr + 0.0015), (0.0008, nr + 0.0025), (0.0042, nr + 0.0025),
                               (0.0050, nr + 0.0015), (0.0050, 0.0)], n=28,
                              axis_origin=tip + 0.002 * _unit(nk_top - tip), axis_dir=_unit(nk_top - tip),
                              ref_dir=[0, 1.0, 0], cap_ends=False), "chrome_trim"))
    for k in range(3):
        out.append((_box(root + [0.0, 0.0, 0.020 + 0.006 * k], (0.010, 0.0035, 0.0055)),
                    "paint_red" if k % 2 == 0 else "light_white"))
    # abstract legend strokes on the plate (no lettering): the POWER title by the PCL slot, the flap angle marks' labels,
    # the stabilised-propeller caution line along the plate's port edge (FDO1-07: the face read empty)
    a0, b0 = q["pcl_slot"]
    out.append((fp.rect(a0 - cx + 0.004, pcy + sw + 0.004, a0 - cx + 0.026, pcy + sw + 0.0065, 0.0003), "light_white"))
    for k in range(4):
        x_ = fx - 0.050 + 0.040 * k
        out.append((fp.rect(x_ - cx - 0.003, fy + sw + 0.010, x_ - cx + 0.003, fy + sw + 0.0125, 0.0003),
                    "light_white"))
    out.append((fp.rect(a0 - cx, -hw + fw + 0.005, b0 - cx + 0.020, -hw + fw + 0.0062, 0.0003), "light_white"))
    for k, (u0_, u1_) in enumerate(((0.0, 0.030), (0.034, 0.052), (0.056, 0.090), (0.094, 0.120))):
        out.append((fp.rect(a0 - cx + 0.010 + u0_, -hw + fw + 0.0085, a0 - cx + 0.010 + u1_, -hw + fw + 0.0095, 0.0003),
                    "light_white"))
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
            # (fix r2 FDO2-04: knurled bodies -- 16 flutes -- over the skirts, the throttle photo's lighting knobs)
            out.append((knob(f.o, f.w, f.u, r_, 0.011, n=32, flutes=16, depth=0.0004, skirt=(r_ + 0.0035, 0.0022),
                             chamfer=0.2), "grip_black"))
            out.append((f.rect(-0.85 * r_, -0.0007, -0.40 * r_, 0.0007, 0.0136), "light_white"))
            out.append((f.rect(-r_ - 0.0125, -0.007, -r_ - 0.0112, 0.007, 0.0003), "light_white"))
            out.append((f.rect(-r_ - 0.0102, -0.0045, -r_ - 0.0092, 0.0045, 0.0003), "light_white"))  # (fix r3: 2-line)
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
            # dark charcoal, a shade off the bezel black (AOPA Garmin close-up: the PDU / MFD corners carry a dark
            # chamfered insert with a small screw; the first build's grey metal read as tabs -- FDO1-06)
            out.append((_FD()._flat(_FD()._extrusion(fr.moved(c=0.0003), P, 0.0006, bevel=0.0002, nb=1)), "panel_dark"))
            c = fr.p(cu, 0.5 * (v0 + v1), 0.0006)
            out.append((knob(c - 0.0002 * fr.w, fr.w, fr.u, 0.0017, 0.0005, n=12, chamfer=0.6), "steel_dark"))
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
    # text-like rows (FID-FD1-07: the first build's full-width bars read as a louvred grille): two blocks as the AOPA
    # close-up shows them -- four rows, a gap, two rows --, each row a label of word-length strokes on the left and a
    # value on the right, 1 mm high (abstract: no lettering)
    rng = np.random.default_rng(275 + sg)
    for k, v in enumerate((0.0175, 0.0120, 0.0065, 0.0010, -0.0110, -0.0165)):
        u = -0.0195
        while True:
            wl = float(rng.uniform(0.0025, 0.0065))
            if u + wl > 0.0010:
                break
            out.append((f.rect(u, v - 0.0005, u + wl, v + 0.0005, 0.0016), "light_white"))
            u += wl + 0.0014
        out.append((f.rect(0.0080, v - 0.0005, 0.0080 + float(rng.uniform(0.006, 0.010)), v + 0.0005, 0.0016),
                    "light_white"))
    return out


# =====================================================================================================================
# the hook called by model/flightdeck.build_flightdeck after _pedals
# =====================================================================================================================
def _detail_a(acc):
    """Track A's extra flight-deck pieces (none yet: the owned builders call the helpers above)."""
    return acc
