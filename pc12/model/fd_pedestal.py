"""Flight-deck centre stack and pedestal / quadrant (split from model/fd_detail_a.py)."""
from __future__ import annotations

import math

import numpy as np

from cad import sdf2d
from cad.mesh import Mesh, grid_surface, planar_cap
from model.fd_kit import (_FD, _orient_out, _unit, knob)  # noqa: F401
from model.fd_panel import (guarded_toggle)  # noqa: F401
from model import fd_print as PR

# =====================================================================================================================
# centre stack + pedestal (A7)
# =====================================================================================================================
# [M] P1046408 (the waisted stack, the pad, the COM knobs on the horns), the Pilatus throttle photo (the quadrant: one
# satin-black plate in a raised gunmetal frame, brush-sealed slots, the PCL's cylinder handle on its arm, the framed
# trim panel), the JTF p.18 pedestal plan (the order fore -> aft, scaled to PEDESTAL x 3.73-4.15), P1046406 (the CCD).
STACK = dict(
    # (the moulded radius along the stack's front edges is interior.PEDESTAL blend[0] since the first-principles A6)
    horn_s=0.215,                   # the stack keeps its SDU width (PANEL stack_hw) down to here (arc length, m)
    waist=(0.312, 0.098),           # ... then narrows to the waist at the pad's foot [M: P1046408 x 830 / 1110]
    flare_s=0.330,                  # ... and flares to the quadrant's half-width (PEDESTAL hw) over the trim panel's top
    # touch pad: centre s, half-length, half-width, r, recess (fix r2: 5).  All-lens review r1 FD8-02 (P1046408 through
    # the fitted panel_408b camera: the tray ~20 px longer / lower than the photo's, the stack stretched below the
    # SDUs): half-length 0.0535 -> 0.046 with its top edge kept (s 0.228), the waist / flare 15 / 13 mm higher with it.
    # All-lens review r2 FD9-01 (the same camera: the tray still 7-10 px low, the trim panel hidden behind the PCL head on
    # the plate, the stack a long plain slab under the tray): the stack face runs straight down to the plate
    # (PEDESTAL stack), the pad 8 mm higher (s 0.274 -> 0.266: y 678-767 of 900, P1046408 675-769), the waist / flare
    # with it, and the trim panel on the face under it (QUAD trim_s: y ~778-840, P1046408 775-830)
    pad=(0.266, 0.046, 0.0775, 0.012, 0.005),
    bezel=0.0040,                   # the chamfer round the pad (its width; fix r2 FDO2-04; fix r5 FDO4-03: 6 -> 4.5 mm,
    #                                 dark bronze -- P1046409 / 10: a dark bronze rim, the light tube read as a frame)
    dish=0.0025,                    # the pad floor's sag at its middle (fix r3 FDO3-01)
    com=(0.222, 0.100, 0.0095),     # COM 1/2 VOL knobs on the horns: s, |y|, radius (research M6: dia 19, BL +/-0.10)
)
QUAD = dict(
    # (the raised gunmetal frame -- width, height, outer corner radius, rolled top -- is interior.PEDESTAL rim since the
    # first-principles flight deck A6, sheet L6C)
    trim_s=(0.322, 0.383),          # framed trim panel on the stack face: arc length from / to (FD9-01; rev N: the plate
    #                                 x 3.738-3.800, behind the PCL head from the crew / cabin eyes)
    trim_hw=0.088,                  # its half-width (the stack face's flat 0.093-0.098 there)
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


TRAY_EDGE_MAT = "panel_titanium"   # the tray's chamfer and foot lip (all-lens r1 FD8-04; fix r5: trim_bronze)


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
    # (first-principles A6, sheet L6C: the moulding's sections meet in R blend[1] fillets -- the drawn polyline's kinks
    # at the SDU foot and the pad, rounded as a moulded part is; tangent arcs, each limited to 0.45 of its edges)
    rf = float(PE["blend"][1])
    pts = [P[0]]
    for k in range(1, len(P) - 1):
        a, b, c = P[k - 1], P[k], P[k + 1]
        d1, d2 = (a - b) / np.linalg.norm(a - b), (c - b) / np.linalg.norm(c - b)
        ang = math.acos(float(np.clip(d1 @ d2, -1, 1)))
        if ang > math.radians(178.0):
            pts.append(b)
            continue
        t = min(rf / math.tan(0.5 * ang), 0.45 * np.linalg.norm(a - b), 0.45 * np.linalg.norm(c - b))
        r_ = t * math.tan(0.5 * ang)
        p0, p1 = b + d1 * t, b + d2 * t
        bis = (d1 + d2) / np.linalg.norm(d1 + d2)
        cen = b + bis * (r_ / math.sin(0.5 * ang))
        a0, a1 = math.atan2(*(p0 - cen)[::-1]), math.atan2(*(p1 - cen)[::-1])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for u in np.linspace(0, 1, 7):
            pts.append(cen + r_ * np.array([math.cos(a0 + u * da), math.sin(a0 + u * da)]))
    pts.append(P[-1])
    P = np.array(pts)
    dense = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        if np.linalg.norm(b - a) < 1e-9:
            continue
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / 0.008)))
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
    R = float(I.PEDESTAL["blend"][0])                               # the moulding's front-edge radius (L6C)
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
    # all-lens review r1 FD8-04 (P1046408: a crisp light titanium tray with a sharp chamfer and lip; the fix r5 dark
    # bronze half-round bead read as a brown frame round a soft cushion): a flat 45-deg CHAMFER `bz` wide from the face
    # down into the tray wall, in the brushed titanium (TRAY_EDGE_MAT), a small rounded nose at its top edge; the hand-rest
    # lip at the pad's foot the same titanium, thinner
    rings = []
    for off, dd in ((bz + 0.0006, 0.0), (bz, -0.0002), (bz - 0.0005, -0.0006), (0.0, -bz), (0.0, -bz - 0.0004)):
        rl = FD.rrect_loop(hwp + off, hl + off, rp + off, nc=6)
        rings.append(np.array([at(y, s_ + sc, dd) for y, s_ in rl]))
    bead = grid_surface(np.array(rings), close_v=True)
    out.append((FD._oriented(bead, lambda C_: C_ - cc), TRAY_EDGE_MAT))
    fl_ = stack_frame(sc + hl + 0.004)
    from cad.mesh import cylinder as _cyl
    out.append((_cyl(fl_.p(-hwp + 0.004, 0.0, 0.0018), fl_.p(hwp - 0.004, 0.0, 0.0018), 0.0028, n=16), TRAY_EDGE_MAT))
    # COM 1/2 VOL knobs on the horns + their legend strokes
    cs, cy, cr = q["com"]
    for sg in (-1, 1):
        f = stack_frame(cs, sg * cy)
        out.append((knob(f.o, f.w, f.u, cr, 0.012, n=36, skirt=(cr + 0.003, 0.0025), chamfer=0.2), "grip_black"))
        out.append((f.rect(-0.0008, 0.35 * cr, 0.0008, 0.75 * cr, 0.0149), "light_white"))
        out.append(PR.decal(f, -0.012, cr + 0.0032, 0.012, cr + 0.0068, PR.LIFT, "words", rows=1, cap=1.6,
                            seed=("com", sg)))                         # (first-principles A3: printed) COM 1 / 2
        out.append(PR.decal(f, -0.013, -cr - 0.0072, 0.013, -cr - 0.0032, PR.LIFT, "words", rows=1, cap=1.4,
                            seed=("vol", sg)))                         # PUSH / VOL
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
    fw, fh, fr, rr = (float(v) for v in PE["rim"])        # the cast rim (PEDESTAL rim, sheet L6C R-R)
    cx = 0.5 * (qx0 + qx1)
    hx = 0.5 * (qx1 - qx0)
    fp = FD.Fr([cx, 0.0, zt], [1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0])      # u = aft, v = starboard, w = up
    # plate + frame: the frame a rounded ring (outer foot -> raised round top -> inner foot)
    O = FD.rrect_loop(hx, hw, fr, nc=8)
    Iin = FD.rrect_loop(hx - fw, hw - fw, max(fr - fw, 0.004), nc=8)
    rings = []
    # (first-principles A6) the rim's section as cast: straight walls, the top edges rolled R rr, a flat top
    prof = [(0.0, 0.0), (0.0, fh - rr)]
    prof += [((rr - rr * math.cos(a)) / fw, fh - rr + rr * math.sin(a)) for a in np.linspace(0.0, 0.5 * math.pi, 5)[1:]]
    prof += [((fw - rr + rr * math.sin(a)) / fw, fh - rr + rr * math.cos(a)) for a in np.linspace(0.0, 0.5 * math.pi, 5)]
    prof += [(1.0, 0.0)]
    for t, hgt in prof:
        P = O + t * (Iin - O)
        rings.append(fp.p(P[:, 0], P[:, 1], hgt))
    frame = grid_surface(np.array(rings), close_v=True)
    out.append((FD._oriented(frame, lambda C: C - fp.p(0, 0, -0.05)), "pedestal_gunmetal"))
    out.append((FD._oriented(planar_cap(fp.p(Iin[:, 0], Iin[:, 1], 0.0), [0, 0, 1.0]), [0, 0, 1.0]), "black"))
    # framed trim panel on the stack face under the tray (all-lens review r2 FD9-01: P1046408 through the fitted
    # panel_408b camera -- on the plate it lay behind the PCL head): u down the face (toward the plate), v starboard,
    # w out of the face; the items keep their layout (titles above them, toward the tray)
    ts0, ts1 = q["trim_s"]
    fs_ = stack_frame(0.5 * (ts0 + ts1))
    ft = FD.Fr(fs_.o, -fs_.v, fs_.u, fs_.w)
    th = 0.5 * (ts1 - ts0)
    out.append((FD._extrusion(ft.moved(c=0.0012), FD.rrect_loop(th, q["trim_hw"], 0.004, nc=4), 0.0024,
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
            # printed on the cap (first-principles A3: was a raised stroke; the Pilatus throttle photo / P1046408: a
            # white word on each half)
            out.append(PR.decal_r(fk, cu_ - 0.55 * hu, cv_ - 0.85 * hv, cu_ + 0.55 * hu, cv_ + 0.85 * hv,
                                  top + PR.LIFT, "words", rows=1, cap=1.5, fill=0.95,
                                  seed=("trimcap", round(yy, 3), s_)))   # DOWN / NOSE, LWD / RWD on the cap
    fk = ft.moved(0.004, y4, 0.0024)                                     # guarded FLAP INTERRUPT
    gt = FD.Fr(fk.o, fk.u, fk.v, fk.w)
    out += guarded_toggle(FD.Fr(gt.o, gt.v, -gt.u, gt.w), guard_mat="pedestal_gunmetal")
    # legend strokes on the trim panel: each item's title in two rows of word-length strokes ahead of it (fix r5
    # FID-FD4-03: one bar per item read as a bare panel; P1046408 / 09: TRIM / INTERRUPT, ALTERNATE / STAB TRIM,
    # AILERON TRIM, FLAP / INTERRUPT), the AILERON TRIM bezel's white outline with its LWD / RWD marks
    # (first-principles A3: printed on the bezel plate -- pseudo-text titles, one or two lines over each item -- instead of
    # raised word strokes)
    for k_, (yy, rows) in enumerate(((y1, 2), (y2, 2), (y3, 1), (y4, 2))):
        hw_ = min(0.019, q["trim_hw"] - 0.007 - abs(yy))                  # inside the bezel's rounded corners
        out.append(PR.decal_r(ft, -th + 0.0018, yy - hw_, -th + 0.0018 + 0.0036 * rows + 0.0012, yy + hw_,
                              0.0024 + PR.LIFT, "words", rows=rows, cap=1.3, seed=("trim", k_)))
    bw, bh = 0.026 * k5, 0.016 * k5
    oa, ob = 0.5 * bh + 0.0012, 0.5 * bw + 0.0012
    for s_ in (-1, 1):                                                   # LWD / RWD marks (the outline went, FDY r2)
        out.append(PR.decal_r(ft, 0.006 + oa + 0.0012, y3 + s_ * 0.6 * ob - 0.0045, 0.006 + oa + 0.0042,
                              y3 + s_ * 0.6 * ob + 0.0045, 0.0024 + PR.LIFT, "words", rows=1, cap=1.3,
                              seed=("lwd", s_)))
    # slots with brush seals, detent ticks, the striped reverse gate
    sw = q["slot_w"]
    pcx, pcy, pch = (float(v) for v in PE["pcl"])
    fx, fy, fh_ = (float(v) for v in PE["flap"])
    for (a, b), yy in ((q["pcl_slot"], pcy), (q["flap_slot"], fy)):
        out.append((_box([0.5 * (a + b), yy, zt - 0.004], (b - a, sw, 0.008)), "black"))
        out += _bristles(a, b, yy, zt, sw)
    # (first-principles A3: the PCL / flap scales printed on the plate -- a tick scale along each slot, the detent
    # titles, the striped reverse gate -- instead of raised strokes)
    a0, b0 = q["pcl_slot"]
    out.append(PR.decal(fp, a0 - cx + 0.004, pcy - sw - 0.0085, b0 - cx - 0.004, pcy - sw - 0.0015, PR.LIFT, "ticks",
                        n=19, major=6, side="t"))
    for xx, k_ in ((pcx - 0.090, 0), (pcx - 0.072, 1), (pcx + 0.020, 2)):   # TO / MCP / IDLE titles
        out.append(PR.decal_r(fp, xx - cx - 0.0040, pcy - sw - 0.0185, xx - cx + 0.0040, pcy - sw - 0.0095, PR.LIFT,
                              "words", rows=1, cap=1.4, fill=0.9, seed=("pcl", k_)))
    out.append(PR.decal(fp, pcx + 0.030 - cx, pcy - sw - 0.008, pcx + 0.063 - cx, pcy - sw - 0.002, PR.LIFT,
                        "stripes", colour="red", period=3.0))                     # striped reverse gate
    fa0, fb0 = q["flap_slot"]
    out.append(PR.decal(fp, fa0 - cx + 0.002, fy + sw + 0.0015, fb0 - cx - 0.002, fy + sw + 0.0090, PR.LIFT, "ticks",
                        n=4, major=1, side="b", lw=0.6, base=False))              # flap detents 0 / 15 / 30 / 40
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
    out.append(PR.decal(fp, a0 - cx + 0.004, pcy + sw + 0.003, a0 - cx + 0.030, pcy + sw + 0.0075, PR.LIFT, "words",
                        rows=1, cap=1.8, seed="power"))                          # POWER (along the slot)
    for k in range(4):
        x_ = fx - 0.050 + 0.040 * k
        out.append(PR.decal_r(fp, x_ - cx - 0.004, fy + sw + 0.0095, x_ - cx + 0.004, fy + sw + 0.0135, PR.LIFT, "words",
                              rows=1, cap=1.6, fill=0.6, seed=("flap", k)))       # 0 / 15 / 30 / 40
    # the stabilised-propeller caution placard along the plate's port edge: a framed two-line printed block
    out.append(PR.decal(fp, a0 - cx, -hw + fw + 0.0035, b0 - cx + 0.024, -hw + fw + 0.0110, PR.LIFT, "frame", rc=0.8,
                        lw=0.3, gap=0.0, title=False))
    out.append(PR.decal(fp, a0 - cx + 0.002, -hw + fw + 0.0045, b0 - cx + 0.022, -hw + fw + 0.0100, PR.LIFT, "words",
                        rows=2, cap=1.25, align="l", seed="caution"))
    # flap lever: stem + black square paddle
    out.append((_cyl([fx + 0.010, fy, zt - 0.006], [fx, fy, FL + fh_ - 0.015], 0.0045, n=10), "metal_dark"))
    # (FIDY5-02: a satin BLACK paddle -- the panel knobs' grip_black reflection floor read it grey from the seats)
    # (first-principles judge r1 FP1-03: a flat square paddle ~30 x 30 x 12 as P1046409, its FLAP title printed on the
    # aft face -- the 24 x 30 x 32 block read as a cube knob)
    zp_ = FL + fh_ - 0.012
    out.append((_se([fx, fy, zp_], (0.006, 0.015, 0.014), (0.25, 0.25), nu=10, nv=16), "bezel_black"))
    out.append(PR.decal(FD.Fr([fx + 0.0061, fy, zp_], [0, 1.0, 0], [0, 0, 1.0]), -0.009, -0.0035, 0.009, 0.0035,
                        PR.LIFT, "words", rows=1, cap=2.2, seed="flap_paddle"))
    # placard band across the quadrant (abstract strokes)
    px_ = q["placard_x"]
    out.append(PR.decal_r(fp, px_ - cx - 0.0045, -hw + fw + 0.008, px_ - cx + 0.0045, hw - fw - 0.008, PR.LIFT, "words",
                          rows=2, cap=1.3, seed="placard_band"))
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
            # (first-principles A3) printed: the two-line title ahead of the knob, the white dimmer arc (OFF -> BRT
            # wedge) with its ticks round it (research M20)
            out.append(PR.decal_r(f, -r_ - 0.0135, -0.0095, -r_ - 0.0080, 0.0095, PR.LIFT, "words", rows=2, cap=1.2,
                                  seed=("knob", round(x_, 3), round(yy, 3))))
            Ra = r_ + 0.0075
            out.append(PR.decal_r(f, -Ra, -Ra, Ra, Ra, PR.LIFT, "arc", R=1000 * (r_ + 0.0058), a0=-45.0, a1=225.0,
                                  lw=0.9, ticks=5))
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
