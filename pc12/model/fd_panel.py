"""Flight-deck instrument panel: glareshield detail, GFC 700, eyebrow, lower panel, U recess / J band, displays and placards (split from model/fd_detail_a.py)."""
from __future__ import annotations

import math

import numpy as np

from cad import sdf2d
from cad.mesh import Mesh, grid_surface, planar_cap
from model import fd_print as PR
from model.fd_kit import (_FD, _fan, _orient_out, _unit, knob)  # noqa: F401

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


_GFC_KEYS = {(-0.1115, -0.0192): "AT", (-0.0809, -0.0192): "APR", (-0.0561, -0.0192): "NAV",
             (-0.0309, -0.0192): "HDG", (0.014, -0.0192): "VS", (0.0395, -0.0192): "FLC", (0.0646, -0.0192): "ALT",
             (0.1075, -0.0192): "L/R", (-0.0561, 0.0167): "BANK", (0.0395, 0.0167): "VNV", (0.0952, 0.0167): "AP",
             (0.1198, 0.0167): "YD", (0.1075, -0.0012): "FD"}


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
        # (flight deck + yoke fix r4 FIDY4-04: the knobs in the panel knobs' cool satin `grip_black`, not the shared
        # `black` the quadrant plate's warm viewer tint carried onto them -- P1046408's knob tops read B - R +30..+37)
        out.append((fluted_knob(c + 0.0022 * f.w, f.w, f.u, 0.5 * od, 0.0086, flutes=24), "grip_black"))
        out.append((knob(c + 0.0108 * f.w, f.w, f.u, 0.5 * od - 0.0012, 0.0008, n=40, chamfer=0.0), "panel_silver"))
        out.append((fluted_knob(c + 0.0116 * f.w, f.w, f.u, 0.5 * idm, 0.0074, flutes=18, depth=0.0004), "grip_black"))
        # (first-principles A3) the knob's printed title on the face above it (FMS / HDG / ALT, pseudo-text)
        out.append(PR.decal(f, u - 0.0105, v + 0.0125, u + 0.0105, v + 0.0175, zf + PR.LIFT, "words", rows=1, cap=1.6,
                            seed=("gfc_knob", round(u, 4)),
                            text={-0.1115: "FMS", -0.0309: "HDG", 0.0641: "ALT"}.get(round(u, 4), "CRS")))
    for k_, (u, v) in enumerate(((q["wheel"][0], 0.0247),)):           # the VS wheel's UP / DN title
        out.append(PR.decal(f, u - 0.008, v - 0.0021, u + 0.008, v + 0.0021, zf + PR.LIFT, "words", rows=1, cap=1.4,
                            seed=("gfc_vs", k_), text="UP VS DN"))
    su_, sv_ = q["sensor"]
    out.append((knob(f.p(su_, sv_, zf - 0.0002), f.w, f.u, 0.0016, 0.0005, n=12, chamfer=0.4), "screen"))
    wu, wv, wd, ww = q["wheel"]                                        # VS thumbwheel: slot + ribbed wheel across u
    out.append((f.box(wu, wv, zf - 0.0005, (ww + 0.002, 0.028, 0.0012)), "rubber_black"))          # (fix r4: matte slot)
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
        out.append(PR.decal(fk, -0.40 * kw, -0.22 * kh, 0.40 * kw, 0.22 * kh, 0.0040 + PR.LIFT, "words", rows=1,
                            cap=1.5, fill=0.8, seed=("gfc_key", round(u, 4), round(v, 4)),
                            text=_GFC_KEYS.get((round(u, 4), round(v, 4)), "AP")))   # printed key legend (A3)
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
    out.append((fluted_knob(f.p(0, 0.002, 0.005), f.w, f.u, 0.0085, 0.0110, flutes=20), "grip_black"))   # (fix r4)
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
    out.append(PR.decal(f, -0.0135, -0.0068, 0.0135, 0.0068, 0.0016 + PR.LIFT, "words", rows=2, cap=1.5,
                        seed=("radio_call", sg), text=("RADIO", "CALL")))                                     # RADIO-CALL plate, printed (A3)
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
    """A countersunk cross-recess screw flush in a plate (first-principles A2: fd_kit.flush_screw; was a pan head
    standing 0.9 mm proud with a raised slot bar)."""
    from model.fd_kit import flush_screw
    FD = _FD()
    f = FD.face_frame(y, z)
    f = FD.Fr(_face_pt(y, z, off), f.u, f.v)                      # seated on the plate's own top (its offset normal)
    return flush_screw(f, 0.0, 0.0, 0.0, 0.8 * r, "csk", "steel_dark")


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
            # printed on the rocking face (A3; P1046408: white words on both halves of the black caps, HEAVY / LIGHT /
            # OFF, OPEN / CLOSED), each laid on its facet's slope
            for k_, (vt, ct, vb, cb) in enumerate(((0.45, 0.0040, -0.02, 0.0058), (-0.02, 0.0058, -0.45, 0.0046))):
                top_, bot_ = fk.p(0.0, vt * ch, ct), fk.p(0.0, vb * ch, cb)
                fv = FD.Fr(0.5 * (top_ + bot_), fk.u, top_ - bot_)          # u right, v up the facet, w out
                hl = 0.5 * float(np.linalg.norm(top_ - bot_))
                out.append(PR.decal(fv, -0.40 * cw, -0.42 * hl, 0.40 * cw, 0.42 * hl, PR.LIFT, "words", rows=1,
                                    cap=1.5, fill=0.9, seed=("rk", tuple(np.round(fk.o, 4)), k_)))
    return out


def push_cap(f, w=0.012, h=0.012, proud=0.003, annun="annun_off_green"):
    """Square push-button cap (R 1, `proud` mm proud, black satin) with a legend bar and a dim annunciator split."""
    FD = _FD()
    out = [(FD._extrusion(f.moved(c=0.5 * proud), FD.rrect_loop(0.5 * w, 0.5 * h, 0.001, nc=3), proud, bevel=0.0006,
                          nb=1), "grip_black")]
    out.append(PR.decal(f, -0.38 * w, 0.06 * h, 0.38 * w, 0.36 * h, proud + PR.LIFT, "words", rows=1, cap=1.3,
                        fill=0.85, seed=("cap", round(w, 4), round(h, 4), annun, tuple(np.round(f.o, 4)))))
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
    out.append(PR.decal(f, -0.012, -0.0170, 0.012, -0.0105, PR.LIFT, "words", rows=1, cap=1.6, seed=("usb", sg), text="USB"))
    out += column_surround(sg)
    # inner sub-panel items
    if sg < 0:
        # ICE PROTECTION: two blocks of three rocker switches under their legend strokes [M: P1046408 / 10]
        for zz in (1.808, 1.752):
            f = FD.face_frame(-0.250, zz).moved(c=q["plate_off"])
            out += rocker_block(f, 3)
            # printed (A3): the group's frame with its title, a caption under each switch
            out.append(PR.decal(f, -0.038, -0.0255 if zz > 1.78 else -0.0165, 0.038, 0.0275, PR.LIFT, "frame", gap=0.62, cap=1.5, lw=0.3,
                                rc=1.5, seed=("ice", zz), text="ICE PROTECTION"))
            for i in range(3 if zz > 1.78 else 0):          # (the lower block's foot lies on the plate's edge)
                out.append(PR.decal(f, (i - 1) * 0.023 - 0.0105, -0.0245, (i - 1) * 0.023 + 0.0105, -0.0185,
                                    PR.LIFT, "words", rows=1, cap=1.2, fill=0.9, seed=("ice_sw", zz, i),
                                    text=("LH WSHLD", "RH WSHLD", "PROBES")[i]))
        # V-LE / V-LO placard and the landing-gear handle (wheel knob on a lever in its slot, UP at the top)
        f = FD.face_frame(-0.180, 1.808).moved(c=q["plate_off"])
        out.append((FD._extrusion(f.moved(c=0.0005), FD.rrect_loop(0.0135, 0.0085, 0.001, nc=2), 0.001, bevel=0.0003,
                                  nb=1), "bezel_black"))
        out.append(PR.decal(f, -0.0125, -0.0075, 0.0125, 0.0075, 0.0010 + PR.LIFT, "words", rows=2, cap=1.4,
                            seed="vle_vlo", text=("VLE 180 KIAS", "VLO 180 KIAS")))                                         # V-LE / V-LO placard (A3)
        f = FD.face_frame(-0.160, 1.792).moved(c=q["plate_off"])
        out.append((FD._extrusion(f.moved(c=0.001), FD.rrect_loop(0.012, 0.047, 0.004, nc=3), 0.002, bevel=0.0005,
                                  nb=1), "bezel_black"))
        out.append((f.box(0.0, 0.0, 0.0021, (0.006, 0.084, 0.0004)), "black"))                    # the slot
        out.append((_FD().cylinder(f.p(0, 0.032, 0.001), f.p(0, 0.032, 0.040), 0.0042, n=12), "metal_dark"))
        wc = f.p(0.0, 0.032, 0.040)
        out.append((_FD().revolve([(0.0, 0.004), (0.002, 0.016), (0.005, 0.019), (0.009, 0.019), (0.012, 0.016),
                                   (0.014, 0.004)], n=40, axis_origin=wc - 0.007 * f.u, axis_dir=f.u, ref_dir=f.w,
                                  cap_ends=True), "grip_black"))
        out.append(PR.decal(f, -0.0085, 0.0395, 0.0085, 0.0445, 0.0020 + PR.LIFT, "words", rows=1, cap=1.8,
                            seed="gear_up", text="UP"))                                         # UP / DN on the bezel (A3)
        out.append(PR.decal(f, -0.0085, -0.0445, 0.0085, -0.0395, 0.0020 + PR.LIFT, "words", rows=1, cap=1.8,
                            seed="gear_dn", text="DN"))
        # FEATHER INHIBIT: a guarded square push button on the yoke sub-panel
        f = FD.face_frame(-0.442, 1.758).moved(c=q["plate_off"])
        out.append((FD._extrusion(f.moved(c=0.0015), FD.rrect_loop(0.0175, 0.0200, 0.003, nc=3), 0.003, bevel=0.0006,
                                  nb=1), "bezel_black"))
        out.append((FD._extrusion(f.moved(c=0.0035), FD.rrect_loop(0.0125, 0.0125, 0.002, nc=3), 0.002, bevel=0.0005,
                                  nb=1), "panel_silver"))
        out.append((FD._extrusion(f.moved(c=0.0040), FD.rrect_loop(0.0095, 0.0095, 0.0015, nc=3), 0.004, bevel=0.0007,
                                  nb=1), "grip_black"))
        out.append(PR.decal(f, -0.0160, 0.0125, 0.0160, 0.0190, 0.0030 + PR.LIFT, "words", rows=1, cap=1.4,
                            seed="feather_inh", text="FEATHER INHIBIT"))                                     # FEATHER INHIBIT (A3)
        # PARKING BRK: a vertical black lozenge handle on its round boss, lower left [M: P1046410]
        f = FD.face_frame(-0.637, 1.787).moved(c=q["plate_off"])
        out.append((knob(f.o, f.w, f.u, 0.0140, 0.0050, n=32, chamfer=0.3), "panel_dark"))
        out.append((_FD().cylinder(f.p(0, 0, 0.004), f.p(0, 0, 0.020), 0.0045, n=14), "metal_dark"))
        loz = FD._fillet(np.array([(0.0, -0.034), (0.0105, -0.012), (0.0105, 0.012), (0.0, 0.034), (-0.0105, 0.012),
                                   (-0.0105, -0.012)]), 0.007, n=4, max_seg=0.01)
        out.append((FD._extrusion(f.moved(c=0.026), loz, 0.012, bevel=0.003, nb=2), "grip_black"))
        out.append(PR.decal(FD.Fr(f.o, f.v, -f.u, f.w), -0.019, -0.0035, 0.019, 0.0035, 0.032 + PR.LIFT, "words",
                            rows=1, cap=2.0, seed="park_brk", text="PARK BRK"))                        # PARKING BRK on the handle (A3)
    else:
        # ACS / CPCS: two placards in the band, a row of four lit push buttons, the rockers and the guarded DUMP
        # [M: P1046409, P1046408]
        for yy in (0.200, 0.244):
            f = FD.face_frame(yy, 1.851).moved(c=q["band_off"])
            out.append((FD._extrusion(f.moved(c=0.0005), FD.rrect_loop(0.0195, 0.0062, 0.001, nc=2), 0.001,
                                      bevel=0.0003, nb=1), "bezel_black"))
            out.append(PR.decal(f, -0.0180, -0.0052, 0.0180, 0.0052, 0.0010 + PR.LIFT, "words", rows=2, cap=1.2,
                                seed=("acs_placard", yy),
                                text=(("MAX DIFF", "5.75 PSI"), ("CABIN ALT", "10000 FT"))[int(yy > 0.22)]))                           # printed (A3)
        for yy, an in ((0.186, "annun_off_green"), (0.208, "annun_off_green"), (0.231, "annun_off_amber"),
                       (0.254, "annun_off_green")):                 # unlit on a parked aircraft (FID-FD1-03)
            f = FD.face_frame(yy, 1.816).moved(c=q["plate_off"])
            out.append((FD._extrusion(f.moved(c=0.001), FD.rrect_loop(0.0105, 0.0105, 0.0015, nc=3), 0.002,
                                      bevel=0.0004, nb=1), "bezel_black"))
            out += push_cap(f.moved(c=0.002), 0.017, 0.017, 0.003, an)
            out.append(PR.decal(f, -0.0110, 0.0115, 0.0110, 0.0160, PR.LIFT, "words", rows=1, cap=1.3,
                                seed=("acs_title", yy),
                                text=dict(((0.186, "BLEED"), (0.208, "PACK"), (0.231, "AUTO"), (0.254, "VENT")))
                                .get(round(yy, 3), "ACS")))
        f = FD.face_frame(0.188, 1.769).moved(c=q["plate_off"])
        out += rocker_block(f, 1, cap=(0.016, 0.026), legend=True)
        f = FD.face_frame(0.223, 1.769).moved(c=q["plate_off"])
        out += rocker_block(f, 1, cap=(0.016, 0.026), legend=True)
        out += guarded_toggle(FD.face_frame(0.279, 1.769).moved(c=q["plate_off"]))
        fg = FD.face_frame(0.226, 1.769).moved(c=q["plate_off"])                    # the ACS group's frame + title
        out.append(PR.decal(fg, -0.056, -0.0215, 0.068, 0.0255, PR.LIFT, "frame", gap=0.45, cap=1.5, lw=0.3, rc=1.5,
                            seed="acs_frame", text="ENVIRONMENTAL"))
        for k_, yy in enumerate((0.188, 0.223)):
            out.append(PR.decal(FD.face_frame(yy, 1.769).moved(c=q["plate_off"]), -0.010, -0.0200, 0.010, -0.0160,
                                PR.LIFT, "words", rows=1, cap=1.2, seed=("acs_sw", k_), text=("CPCS", "TEMP")[k_]))
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
    out.append((knob(c, f.w, f.u, 0.0072, 0.0030, n=36, chamfer=0.2), "grip_black"))                  # (fix r4)
    out.append((fluted_knob(c + 0.0030 * f.w, f.w, f.u, 0.0058, 0.0065, flutes=18), "grip_black"))
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
    # (first-principles A3: printed -- label column left aligned, value column on the right)
    top = 0.0012
    out.append(PR.decal(f, -0.0205, -0.0030 + 0.0020, 0.0040, 0.0215, top + PR.LIFT, "words", rows=4, cap=1.1,
                        align="l", fill=0.95, fill2=0.9, seed=("vs_l", sg), text=("VMO", "VA", "VFE 15", "VFE 40")))
    out.append(PR.decal(f, 0.0060, -0.0010, 0.0205, 0.0215, top + PR.LIFT, "words", rows=4, cap=1.1, align="l",
                        fill=0.8, fill2=1.0, seed=("vs_r", sg), text=("240", "165", "165", "130")))
    out.append(PR.decal(f, -0.0205, -0.0205, 0.0205, -0.0070, top + PR.LIFT, "words", rows=2, cap=1.1, align="l",
                        fill=0.9, fill2=1.0, seed=("vs_b", sg), text=("MAX DEMO X-WIND 30 KT", "MANEUVERING SPEED 165 KIAS")))
    return out
