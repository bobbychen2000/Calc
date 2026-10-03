"""
Flight deck (Stage 3): the 3-D build of the APPROVED L6 flight-deck tables in model/interior.py -- PC-12 PRO,
Garmin G3000 PRIME.  Everything that the sheets L6 / L6B draw is taken from the tables and their derived functions
(nothing here re-defines a drawn dimension):

  FLOOR       fd_wl (flush with the cabin floor), fd_x0 (footwell front); interior.pedestal_plinth() over
              gear.NOSE_TUNNEL (open shell: the stowed nose wheel rises into it)
  PANEL       PDU plane interior.panel_x() (glass_x, mfd_z, tilt), 3 x 14-in PDUs (pdu_wh, pdu_bl, pdu_cant),
              lower panel to lower_dz, side cheeks to cheek_bl (and the lining), GI 275 standby, ECS eyeballs,
              centre stack (stack_hw, PEDESTAL stack profile) with the 2 portrait 7-in SDUs (interior.sdu_centre())
  GLARESHIELD hood from the windshield inner frame (interior.ws_lower_edge - frame_drop) to the lip arch
              (interior.glareshield_lip), GFC 700 (afcs_wh) on the eyebrow fascia
  YOKE        PC-24-style yokes: hub (interior.yoke_hub, hub_whd, the Y outline interior.yoke_outline_yz), canted grips
              (interior.yoke_grip_axis), horizontal column into the lower panel
  PEDALS      pads at seat CL +/- dy on the face line of interior.pedal_points(), floor hinge PEDALS pivot
  PEDESTAL    interior.pedestal_profile(): control quadrant (PCL, flap lever, trim / interrupt switches, lighting
              knobs, CCD palm grip), emergency T-handles on the aft face
  SIDE_CONSOLE / OVERHEAD / DIVIDER (walls, curtain: interior.curtain_bundle(), extinguisher)
  LINING      the side consoles, CB panels, hood / panel ends and the divider are fitted to interior.lining_section()

Detail sizes that the sheets do not draw (knob radii, switch blocks, bezel borders, screen layouts) are the DETAIL
constants below, tagged [M] (photos in the gitignored refs/cache) or [E].

API
  build_flightdeck(groups=False, floor=True) -> [(Mesh, material)]  one mesh per material (groups=True: {group: [...]})
  build(parts)                                -> adds Part 'flight_deck' (replaces interior.build_flightdeck)
  MATERIALS / EMISSIVE                        this builder's palette entries (views of assemble.MATERIALS / EMISSIVE)
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from cad import sdf2d
from cad.mesh import Mesh, superellipsoid, box, cylinder, revolve, disk, grid_surface, planar_cap, sweep_profile
from model import interior as I

# =====================================================================================================================
# materials: the values live in model/assemble.MATERIALS / EMISSIVE (and render/lookdev.py SPEC); these are the names
# this builder introduced (views of that table, kept for the preview scripts)
# =====================================================================================================================
from model.assemble import MATERIALS as _MAT, EMISSIVE as _EMI     # noqa: E402

OWN_MATERIALS = ("panel_dark", "panel_grey", "leather_glareshield", "carpet_flightdeck", "bezel_black", "display_page",
                 "screen", "screen_sky", "screen_ground", "screen_green", "screen_cyan", "screen_white", "light_amber",
                 "yoke_white", "grip_black", "veneer_walnut", "curtain", "paint_red", "panel_silver",
                 "pedestal_gunmetal", "pcl_pewter", "panel_titanium")
MATERIALS = {k: _MAT[k] for k in OWN_MATERIALS}
EMISSIVE = {k: v for k, v in _EMI.items() if k in OWN_MATERIALS}
# also used, already in assemble.MATERIALS: metal, metal_dark, steel, black, light_red, light_white, chrome_trim
USED_EXISTING = ("metal", "metal_dark", "steel", "black", "light_red", "light_white", "chrome_trim", "placard_red",
                 "lining_flightdeck")

# =====================================================================================================================
# detail constants (not drawn on L6)
# =====================================================================================================================
DETAIL = dict(
    pdu_border=(0.014, 0.014, 0.020, 0.022),   # [M] bezel l, r, top (GARMIN logo), bottom: active 302 x 188 (P1046408)
    sdu_active=(0.094, 0.151),                 # [S] 7-in 16:10 portrait active area
    bezel_depth=0.040,                         # [E] display unit depth visible in the recess
    recess_margin=0.006,                       # [E] recess round the PDU row (the three faces touch, 'edge to edge')
    recess_depth=0.055,                        # [E]
    face_proud=0.003,                          # [E] MFD bezel front this far BEHIND the face (recessed bezels)
    brow_gap=0.018,                            # [M] soffit above the PDU bezel tops (dark shadow band, P1046408); r1 INT-M1 0.012 -> 0.018
    brow_depth=0.030,                          # [M] soffit depth: the fascia foot this far aft of the PDU-face plane (INT-M1)
    fascia_lean=15.0,                          # [M] fascia face leans back (top aft) this much from vertical
    lip_r=0.015,                               # [E] rolled lip radius (sheet: lip 0.03 deep)
    wrap=(0.545, 0.22),                        # [E] panel ends wrap aft outboard of |BL| 0.545 (radius): the cheeks
    ecs_r=0.024,                               # [M] eyeball outlet (cockpit key 47 mm)
    afcs_z=0.180,                              # [M] GFC 700 centre above the MFD centre (sheet: +0.18)
    baro_bl=0.228, warn_bl=0.300,              # [M] BARO knob, master warning / caution pair (face-on photo)
    cb=(4, 10, 0.0055),                        # [M] CB rows, breakers per row, knob radius (P1046409 / 10)
    cup_x=(3.875, 3.985),                      # [M] cup-holder pair in the console pod under the CB panel
    compass_z=2.380,                           # [M] compass on the centre post (P1046408 elevation 23 deg)
)

FL = float(I.FLOOR["fd_wl"])
PN, GS, YK, PD, PE, SC, OV, DV = (I.PANEL, I.GLARESHIELD, I.YOKE, I.PEDALS, I.PEDESTAL, I.SIDE_CONSOLE, I.OVERHEAD,
                                  I.DIVIDER)
ZM = float(PN["mfd_z"])
TILT = math.radians(PN["tilt_deg"])
V_UP = np.array([-math.sin(TILT), 0.0, math.cos(TILT)])        # up the PDU plane (top forward)
N_AFT = np.array([math.cos(TILT), 0.0, math.sin(TILT)])       # PDU plane normal, toward the crew
Z_LO = ZM + float(PN["lower_dz"])                             # lower (yoke / switch) panel bottom
PDU_W, PDU_H = (float(v) for v in PN["pdu_wh"])
Z_BROW = ZM + 0.5 * PDU_H * math.cos(TILT) + DETAIL["brow_gap"]   # fascia bottom / soffit, centre


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# =====================================================================================================================
# lining lookup (interior.lining_section tabulated: half-width at (x, z), headliner at (x, |y|))
# =====================================================================================================================
class _Lining:
    def __init__(self, x0=3.00, x1=4.66, dx=0.01):
        from scipy.interpolate import RegularGridInterpolator as RGI
        self.xs = np.arange(x0, x1 + 1e-9, dx)
        self.zs = np.linspace(1.10, 2.90, 361)
        self.ys = np.linspace(0.0, 0.85, 171)
        HW, CR = [], []
        for x in self.xs:
            L = I.lining_section(float(x), n=1441)
            S = L[:len(L) // 2]                                           # starboard, crown -> keel
            HW.append(np.interp(self.zs, S[::-1, 1], S[::-1, 0]))
            S4 = L[:len(L) // 4]                                          # crown -> max breadth
            CR.append(np.interp(self.ys, S4[:, 0], S4[:, 1]))
        kw = dict(bounds_error=False, fill_value=None)
        self._hw = RGI((self.xs, self.zs), np.array(HW), **kw)
        self._cr = RGI((self.xs, self.ys), np.array(CR), **kw)

    def hw(self, x, z):
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        return self._hw(np.stack([x.ravel(), z.ravel()], 1)).reshape(x.shape)

    def crown(self, x, y):
        x, y = np.broadcast_arrays(np.asarray(x, float), np.abs(np.asarray(y, float)))
        return self._cr(np.stack([x.ravel(), y.ravel()], 1)).reshape(x.shape)


_LIN = None


def lining():
    global _LIN
    if _LIN is None:
        _LIN = _Lining()
    return _LIN


# =====================================================================================================================
# small geometry helpers
# =====================================================================================================================
class Fr:
    """Local frame: p(a, b, c) = o + a u + b v + c w (w = u x v unless given)."""

    def __init__(self, o, u, v, w=None):
        self.o = np.asarray(o, float)
        self.u = _unit(u)
        v = np.asarray(v, float)
        self.v = _unit(v - self.u * np.dot(v, self.u))
        self.w = _unit(np.cross(self.u, self.v)) if w is None else _unit(w)

    def p(self, a, b, c=0.0):
        a, b, c = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(c, float))
        return self.o + a[..., None] * self.u + b[..., None] * self.v + c[..., None] * self.w

    @property
    def R(self):
        return np.stack([self.u, self.v, self.w], 1)

    def moved(self, a=0.0, b=0.0, c=0.0):
        return Fr(self.p(a, b, c), self.u, self.v, self.w)

    def rect(self, u0, v0, u1, v1, c=0.0):
        """Flat rectangle facing +w."""
        P = self.p(np.array([u0, u1, u1, u0]), np.array([v0, v0, v1, v1]), c)
        return _oriented(Mesh(P, np.array([[0, 1, 2], [0, 2, 3]])), self.w)

    def se(self, a, b, c, radii, e=(0.25, 0.25), n=(8, 12)):
        """Superellipsoid (rounded box / pillow) centred at local (a, b, c), radii along u, v, w."""
        return superellipsoid(self.p(a, b, c), radii, e, nu=n[0], nv=n[1], R=self.R)

    def box(self, a, b, c, size):
        return box(self.p(a, b, c), size, R=self.R)

    def knob(self, a, b, r, h, n=14, c0=0.0):
        """Round knob standing on the face along +w, chamfered top."""
        prof = [(0.0, r), (h - 0.25 * r, r), (h, 0.75 * r)]
        return revolve(prof, n=n, axis_origin=self.p(a, b, c0), axis_dir=self.w, ref_dir=self.u, cap_ends=True)

    def disk(self, a, b, r, c=0.0, n=24, r_inner=0.0):
        return disk(self.p(a, b, c), self.w, r, n=n, ref=self.u, r_inner=r_inner)

    def poly(self, P2, c=0.0):
        P2 = np.asarray(P2, float)
        return planar_cap(self.p(P2[:, 0], P2[:, 1], c), self.w)


def _oriented(m, direction):
    """Flip m if its mean face normal points against `direction` (a vector or a function of the face centres)."""
    if not len(m.F):
        return m
    fn = m.face_normals()
    C = m.V[m.F].mean(1)
    d = direction(C) if callable(direction) else np.broadcast_to(np.asarray(direction, float), fn.shape)
    return m.flipped() if np.mean(np.sum(fn * d, 1)) < 0 else m


def _strip(A, B, closed=True):
    """Quad strip between two polylines / loops of equal length."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    n = len(A)
    i = np.arange(n if closed else n - 1)
    j = (i + 1) % n
    F = np.vstack([np.stack([i, j, n + j], 1), np.stack([i, n + j, n + i], 1)])
    return Mesh(np.vstack([A, B]), F)


def _flat(m):
    """Unshare vertices: faceted, crisp normals."""
    V = m.V[m.F].reshape(-1, 3)
    return Mesh(V, np.arange(len(V)).reshape(-1, 3))


def rrect_loop(hw, hh, r, nc=5, cx=0.0, cy=0.0):
    """Rounded rectangle (CCW), nc points per corner (the same topology for every size: loops can be stripped)."""
    r = max(min(r, hw - 1e-4, hh - 1e-4), 1e-4)
    out = []
    for (sx, sy), a0 in (((1, 1), 0.0), ((-1, 1), 90.0), ((-1, -1), 180.0), ((1, -1), 270.0)):
        c = np.array([cx + sx * (hw - r), cy + sy * (hh - r)])
        for a in np.radians(np.linspace(a0, a0 + 90.0, nc)):
            out.append(c + r * np.array([math.cos(a), math.sin(a)]))
    return np.array(out)


def _poly_normals(P):
    """Outward vertex normals (with miter) of a CCW polygon."""
    e = np.roll(P, -1, 0) - P
    n = np.c_[e[:, 1], -e[:, 0]]
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    nv = n + np.roll(n, 1, 0)
    nv /= np.maximum(np.linalg.norm(nv, axis=1, keepdims=True), 1e-12)
    cosh = np.clip(np.sum(nv * n, 1), 0.5, 1.0)
    return nv / cosh[:, None]


def _fillet(P, r, n=4, max_seg=0.02):
    """Round the corners of a polygon (radius r, limited by the edges) and densify its edges."""
    P = np.asarray(P, float)
    m = len(P)
    out = []
    for k in range(m):
        a, b, c = P[k - 1], P[k], P[(k + 1) % m]
        d1, d2 = _unit(a - b), _unit(c - b)
        ang = math.acos(np.clip(np.dot(d1, d2), -1, 1))
        t = min(r / max(math.tan(0.5 * ang), 1e-6), 0.45 * np.linalg.norm(a - b), 0.45 * np.linalg.norm(c - b))
        p0, p1 = b + d1 * t, b + d2 * t
        for s in np.linspace(0, 1, n):                               # quadratic Bezier corner
            out.append((1 - s) ** 2 * p0 + 2 * s * (1 - s) * b + s ** 2 * p1)
    out = np.array(out)
    dense = []
    for k in range(len(out)):
        a, b = out[k], out[(k + 1) % len(out)]
        L = np.linalg.norm(b - a)
        ns = max(1, int(math.ceil(L / max_seg)))
        for s in np.linspace(0, 1, ns, endpoint=False):
            dense.append(a + s * (b - a))
    return np.array(dense)


def _extrusion(fr, outline, depth, bevel=0.004, bulge=0.0, nb=3, back=True):
    """Rounded extrusion of a CCW outline (u, v) along w from -depth/2 to +depth/2: bevelled front edge, domed front
    face (bulge at the centre), flat back."""
    P = np.asarray(outline, float)
    nrm = _poly_normals(P)
    c = P.mean(0)
    h = 0.5 * depth
    rings = [(P, -h), (P, h - bevel)]
    for k in range(1, nb + 1):
        a = 0.5 * math.pi * k / nb
        rings.append((P - bevel * (1 - math.cos(a)) * nrm, h - bevel + bevel * math.sin(a)))
    Pin = P - bevel * nrm
    for s in (0.82, 0.62, 0.42, 0.22, 0.06):
        rings.append((c + (Pin - c) * s, h + bulge * (1.0 - s * s)))
    G = np.array([fr.p(R2[:, 0], R2[:, 1], w) for R2, w in rings])
    m = grid_surface(G, close_v=True)
    tip = fr.p(c[0], c[1], h + bulge)
    last = G[-1]
    n = len(last)
    i = np.arange(n)
    fan = Mesh(np.vstack([last, tip[None]]), np.stack([i, (i + 1) % n, np.full(n, n)], 1))
    back_pt = fr.p(c[0], c[1], -3 * depth)
    parts = [_oriented(m, lambda C: C - back_pt), _oriented(fan, fr.w)]
    if back:
        parts.append(_oriented(planar_cap(G[0], -fr.w), -fr.w))
    return Mesh.merge(parts)


def _bezel(fr, W, H, border, r_out=0.008, r_in=0.003, depth=0.035, glass_in=0.003, nc=5):
    """Display bezel frame in frame fr (front plane w = 0): outer W x H, borders (l, r, top, bottom); returns
    (bezel mesh, glass frame at the active-area centre, (active w, active h))."""
    l, r, t, b = border
    aw, ah = W - l - r, H - t - b
    acx, acy = 0.5 * (l - r), 0.5 * (b - t)
    O = rrect_loop(0.5 * W, 0.5 * H, r_out, nc)
    In = rrect_loop(0.5 * aw, 0.5 * ah, r_in, nc, acx, acy)
    front = _oriented(_strip(fr.p(O[:, 0], O[:, 1]), fr.p(In[:, 0], In[:, 1])), fr.w)
    outer = _oriented(_strip(fr.p(O[:, 0], O[:, 1], -depth), fr.p(O[:, 0], O[:, 1])),
                      lambda C: C - fr.o)
    inner = _oriented(_strip(fr.p(In[:, 0], In[:, 1]), fr.p(In[:, 0], In[:, 1], -glass_in)),
                      lambda C: fr.p(acx, acy, 0.0) - C)
    gfr = Fr(fr.p(acx, acy, -glass_in), fr.u, fr.v, fr.w)
    glass = _oriented(planar_cap(fr.p(In[:, 0], In[:, 1], -glass_in), fr.w), fr.w)
    return Mesh.merge([front, outer, inner]), glass, gfr, (aw, ah)


class _Acc:
    def __init__(self):
        self.d = defaultdict(list)
        self.group = "misc"

    def add(self, m, mat):
        if m is not None and len(m.F):
            self.d[(self.group, mat)].append(m)


# =====================================================================================================================
# panel face geometry (PDU plane + the wrapped cheeks)
# =====================================================================================================================
def lip_z(y):
    t = np.array(GS["lip_dz"], float)
    return ZM + np.interp(np.abs(y), t[:, 0], t[:, 1])


def wrap(ay):
    y0, R = DETAIL["wrap"]
    d = np.clip(np.asarray(ay, float) - y0, 0.0, 0.95 * R)
    return R - np.sqrt(R * R - d * d)


def wrap_slope(ay):
    y0, R = DETAIL["wrap"]
    d = np.clip(np.asarray(ay, float) - y0, 0.0, 0.95 * R)
    return d / np.sqrt(R * R - d * d)


def face_x(y, z):
    return I.panel_x(z) + wrap(np.abs(y))


def face_frame(y, z):
    """Frame on the panel face at (y, z): u = along the face toward starboard, v = up the face, w = aft normal."""
    s = float(np.sign(y)) * float(wrap_slope(abs(y)))
    u = _unit([s, 1.0, 0.0])
    return Fr([float(face_x(y, z)), y, z], u, V_UP)


def z_brow(y):
    """Fascia bottom / soffit / panel-face top at butt line y."""
    return np.minimum(Z_BROW, lip_z(y) - 2.0 * DETAIL["lip_r"])


def fascia_x(y, z):
    """Station of the eyebrow fascia at (y, z): its foot (at z_brow) DETAIL brow_depth aft of the PDU-face plane, the
    face leaning back (top aft) by fascia_lean up to the lip's underside.  Model judging r1 INT-M1: the rev F fascia
    dropped near-vertically from the lip (x 3.615-3.627), 0.15 m aft of the PDUs, and hid the top 50-55 mm of the PDU
    glass from the design eye; with the foot forward the leather lip overhangs the fascia (its underside, the dark
    band above the GFC 700 in P1046408) and the bezel tops show from the design eye (brow_visibility)."""
    zf = z_brow(y)
    return face_x(y, zf) + DETAIL["brow_depth"] + (np.asarray(z, float) - zf) * math.tan(math.radians(
        DETAIL["fascia_lean"]))


def brow_visibility(eyes=None, n=9):
    """Clearance (m) of the sight lines from the design eye(s) to the PDU bezel tops (n points along each top edge,
    glass tops too) under the fascia foot: the smallest (fascia foot WL - sight-line WL at the foot's station) over
    all displays and eyes; > 0 = every bezel top visible under the brow.  Returns (min bezel margin, min glass margin,
    the worst (eye side, display) pair).  Model judging r1 INT-M1 (L6B / fit_check row)."""
    eyes = eyes or {s: I.design_eye(s) for s in (-1, 1)}
    worst = (np.inf, np.inf, None)
    for name, kind, sg, fr, W, H, brd, kw in _display_specs():
        if kind == "sdu":
            continue
        l, r_, t, b = brd
        us = np.linspace(-0.5 * W, 0.5 * W, n)
        for lab, vtop in (("bezel", 0.5 * H), ("glass", 0.5 * H - t)):
            P = np.array([fr.p(u, vtop, 0.0) for u in us])
            for es, E in eyes.items():
                m = np.inf
                for Pk in P:
                    d = E - Pk
                    # march the ray: find s where the ray's x reaches the fascia foot at the ray's y
                    s0, s1 = 0.0, 1.0
                    for _ in range(40):
                        sm = 0.5 * (s0 + s1)
                        q = Pk + sm * d
                        if q[0] < float(fascia_x(q[1], z_brow(q[1]))):
                            s0 = sm
                        else:
                            s1 = sm
                    q = Pk + 0.5 * (s0 + s1) * d
                    m = min(m, float(z_brow(q[1])) - q[2])
                k = 0 if lab == "bezel" else 1
                if m < worst[k]:
                    worst = (m, worst[1], (es, name)) if k == 0 else (worst[0], m, worst[2])
    return worst


def _clamp_lining(P, gap=0.004, cap=None):
    """Pull points inboard to the lining (and |y| <= cap)."""
    L = lining()
    P = np.array(P, float)
    lim = L.hw(P[..., 0], P[..., 2]) - gap
    if cap is not None:
        lim = np.minimum(lim, cap)
    P[..., 1] = np.sign(P[..., 1]) * np.minimum(np.abs(P[..., 1]), lim)
    return P


def _panel_face(acc):
    """Panel face (PDU plane, wrapped outboard to the cheeks, clipped to the lining), the PDU-row recess and the
    lower edge return."""
    acc.group = "panel"
    cheek = float(PN["cheek_bl"])
    mg = DETAIL["recess_margin"]
    ry = float(PN["pdu_bl"][2]) + 0.5 * PDU_W * math.cos(math.radians(PN["pdu_cant"])) + mg + 0.004
    rv = 0.5 * PDU_H + mg
    rz0, rz1 = ZM - rv * math.cos(TILT), ZM + rv * math.cos(TILT)
    ys = np.unique(np.round(np.r_[np.linspace(-cheek, cheek, 97), -ry, ry, -0.146, 0.146], 6))
    zs = np.unique(np.round(np.r_[np.linspace(Z_LO, Z_BROW, 25), rz0, rz1], 6))
    Y, Z = np.meshgrid(ys, zs, indexing="ij")
    Z = np.minimum(Z, z_brow(Y))
    P = np.stack([face_x(Y, Z), Y, Z], -1)
    P = _clamp_lining(P, 0.004, cheek)
    P[..., 0] = face_x(P[..., 1], P[..., 2])
    m = grid_surface(P)
    # drop the cells of the PDU-row recess
    C = m.V[m.F].mean(1)
    inside = (np.abs(C[:, 1]) < ry - 1e-6) & (C[:, 2] > rz0 + 1e-6) & (C[:, 2] < rz1 - 1e-6)
    m.F = m.F[~inside]
    m.compact()
    # the face round the PDUs: the same warm titanium as the sub-panels (P1046408: one metallic surface, black only on
    # the bezels and switch blocks: review r2 F3); final judge r1 LIV-F1-04 / I4: a darker satin titanium
    # ('panel_titanium', metallic) -- the light 'panel_grey' read as beige plastic against the photo's grey metal
    acc.add(_oriented(m, N_AFT), "panel_titanium")
    # lower edge return (the face is a moulding, not a sheet): 40 mm forward under the bottom edge
    bot = P[:, 0]
    acc.add(_oriented(_strip(bot, bot - [0.045, 0.0, 0.004], closed=False), [0, 0, -1.0]), "panel_titanium")
    # recess (black box behind the PDU row)
    fr = Fr([I.panel_x(ZM), 0.0, ZM], [0, 1.0, 0], V_UP)
    d = DETAIL["recess_depth"]
    cn = [(-ry, -rv), (ry, -rv), (ry, rv), (-ry, rv)]
    for k in range(4):
        (a0, b0), (a1, b1) = cn[k], cn[(k + 1) % 4]
        q = _strip(fr.p(np.array([a0, a1]), np.array([b0, b1])), fr.p(np.array([a0, a1]), np.array([b0, b1]), -d),
                   closed=False)
        acc.add(_oriented(q, lambda Cc: fr.o - Cc), "bezel_black")
    acc.add(fr.rect(-ry, -rv, ry, rv, -d), "bezel_black")


# =====================================================================================================================
# displays
# =====================================================================================================================
def _page_glass(glass, g, aw, ah, name):
    """The display glass carrying its G3000 PRIME page (final judge r1 R2 / I1): UVs into the atlas of
    model/g3000_pages.py from each vertex's place on the active area (g: frame at the active-area centre, u right, v up);
    material 'display_page' (emissive texture, cad/glb.py).  The flat coloured page geometry it replaces (_screen, up
    to rev E) read as a placeholder."""
    from model import g3000_pages
    d = glass.V - g.o
    glass.UV = g3000_pages.uv_rect(name, d @ g.u / aw + 0.5, d @ g.v / ah + 0.5)
    return glass


def _display_specs():
    """The five G3000 PRIME displays: [(name, kind, side, bezel frame fr, W, H, border (l, r, t, b), bezel kwargs)] --
    the three PDUs (PFD L, MFD, PFD R) on the panel face, the two SDU touch controllers on the pedestal stack."""
    out = []
    fr0 = Fr([I.panel_x(ZM), 0.0, ZM], [0, 1.0, 0], V_UP)
    cant = math.radians(PN["pdu_cant"])
    for yc in PN["pdu_bl"]:
        sg = int(np.sign(yc))
        o = fr0.p(yc, 0.0, -DETAIL["face_proud"])
        if sg:
            u = math.cos(cant) * fr0.u + sg * math.sin(cant) * fr0.w
            fr = Fr(o, u, fr0.v)
        else:
            fr = Fr(o, fr0.u, fr0.v)
        out.append(({-1: "pfd_L", 0: "mfd", 1: "pfd_R"}[sg], "pfd" if sg else "mfd", sg, fr, PDU_W, PDU_H,
                    tuple(DETAIL["pdu_border"]), dict(depth=DETAIL["bezel_depth"])))
    # SDUs: portrait, side by side on the reclined stack face (interior.sdu_centre)
    sw, sh = (float(v) for v in PN["sdu_wh"])
    a_w, a_h = DETAIL["sdu_active"]
    rec = math.radians(PN["sdu_recline"])
    v_up = np.array([-math.sin(rec), 0.0, math.cos(rec)])
    for sg in (-1, 1):
        c = I.sdu_centre(sg)
        fr = Fr(c + 0.004 * np.array([math.cos(rec), 0.0, math.sin(rec)]), [0, 1.0, 0], v_up)
        brd = (0.5 * (sw - a_w), 0.5 * (sw - a_w), 0.5 * (sh - a_h), 0.5 * (sh - a_h))
        out.append(({-1: "sdu_L", 1: "sdu_R"}[sg], "sdu", sg, fr, sw, sh, brd, dict(r_out=0.006, depth=0.012)))
    return out


def display_frames():
    """Active areas of the five displays (model axes): {name: dict(kind, side, centre (on the glass), u (right), v (up),
    w (out of the screen, toward the crew), size (active w, h), bezel_lip (m from the glass forward to the bezel face),
    page (the page's pixel rectangle x0, y0, x1, y1 in the model/g3000_pages.py atlas, y down))}.  Written into the
    GLB's model meta (the root node's extras) 'displays' by model/build.py; the glass itself carries the page
    (_page_glass)."""
    from model import g3000_pages
    out = {}
    for name, kind, sg, fr, W, H, brd, kw in _display_specs():
        l, r, t, b = brd
        glass_in = kw.get("glass_in", 0.003)
        aw, ah = W - l - r, H - t - b
        c = fr.p(0.5 * (l - r), 0.5 * (b - t), -glass_in)
        out[name] = dict(kind=kind, side=sg, centre=[round(float(v), 5) for v in c],
                         u=[round(float(v), 6) for v in fr.u], v=[round(float(v), 6) for v in fr.v],
                         w=[round(float(v), 6) for v in fr.w], size=[round(float(aw), 5), round(float(ah), 5)],
                         bezel_lip=glass_in, page=list(g3000_pages.ATLAS["rects"][name]))
    return out


def _displays(acc):
    acc.group = "displays"
    for name, kind, sg, fr, W, H, brd, kw in _display_specs():
        bz, glass, g, (aw, ah) = _bezel(fr, W, H, brd, **kw)
        acc.add(bz, "bezel_black")
        acc.add(_page_glass(glass, g, aw, ah, name), "display_page")
        if kind != "sdu":
            acc.add(fr.rect(-0.018, 0.5 * PDU_H - 0.013, 0.018, 0.5 * PDU_H - 0.009, 0.0003), "panel_grey")  # logo
    # GI 275 standby (round face in a square case) and the eyeball ECS outlets, on the wrapped face
    acc.group = "panel"
    sby, sdz, sd = (float(v) for v in PN["standby"])
    f = face_frame(sby, ZM + sdz)
    acc.add(f.se(0, 0, 0.008, (0.5 * sd - 0.002, 0.5 * sd - 0.002, 0.012), (0.3, 0.3), (8, 16)), "bezel_black")
    r = 0.5 * sd - 0.010
    top = np.array([[r * math.cos(a), r * math.sin(a)] for a in np.linspace(0, math.pi, 17)])
    acc.add(f.poly(top, 0.0205), "screen_sky")
    acc.add(f.poly(-top, 0.0205), "screen_ground")
    acc.add(f.rect(-r, -0.0006, r, 0.0006, 0.0208), "screen_white")
    acc.add(f.rect(-0.010, -0.002, 0.010, 0.0, 0.0209), "light_amber")
    for sg in (-1, 1):
        f = face_frame(sg * PN["ecs_bl"], ZM - 0.063)
        rr = DETAIL["ecs_r"]
        ring = revolve([(0.0, rr), (0.006, rr), (0.010, 0.8 * rr)], n=20, axis_origin=f.o, axis_dir=f.w,
                       ref_dir=f.u, cap_ends=False)
        acc.add(ring, "panel_grey")
        acc.add(f.disk(0, 0, 0.8 * rr, 0.004, 20), "black")
        acc.add(f.se(0, 0, 0.004, (0.55 * rr, 0.55 * rr, 0.55 * rr), (0.9, 0.9), (8, 12)), "metal_dark")


# =====================================================================================================================
# glareshield: hood (leather), rolled lip, eyebrow fascia (GFC 700, BARO, master warning / caution), soffit
# =====================================================================================================================
def _glareshield(acc):
    acc.group = "glareshield"
    cheek = float(PN["cheek_bl"])
    yw = np.linspace(0.0, 0.62, 14)
    we = np.array([I.ws_lower_edge(y) for y in yw])
    ys = np.linspace(-cheek, cheek, 81)
    lx = float(GS["lip_x"])
    r = DETAIL["lip_r"]
    hood, lip, und, fas, sof = [], [], [], [], []
    for y in ys:
        ay = min(abs(y), 0.62)
        xa = float(np.interp(ay, yw, we[:, 0])) + 0.010
        za = float(np.interp(ay, yw, we[:, 1])) - float(GS["frame_drop"])
        lz = float(lip_z(y))
        xb, zb = lx - r, lz
        t = np.linspace(0.0, 1.0, 9)
        hx = xa + (xb - xa) * t
        hz = za + (zb - za) * t + 0.010 * np.sin(np.pi * t) * min(1.0, (cheek - abs(y)) / 0.1)
        hood.append(np.c_[hx, np.full_like(hx, y), hz])
        a = np.radians(np.linspace(90.0, -90.0, 9))
        lip.append(np.c_[lx - r + r * np.cos(a), np.full(9, y), lz - r + r * np.sin(a)])
        zf = float(z_brow(y))
        zc = lz - 2 * r
        xd, xt = fascia_x(y, zf), fascia_x(y, zc)            # fascia foot / top (model judging r1 INT-M1)
        fz = np.linspace(zc, zf, 4)
        fas.append(np.c_[fascia_x(y, fz), np.full(4, y), fz])
        und.append(np.c_[np.linspace(lx - r, xt, 3), np.full(3, y), np.full(3, zc)])
        xe = float(face_x(y, zf))
        sof.append(np.c_[np.linspace(xd, xe, 3), np.full(3, y), np.full(3, zf)])
    for G, mat, hint in ((hood, "leather_glareshield", [0.1, 0, 1.0]), (lip, "leather_glareshield", [1.0, 0, 0.3]),
                         (und, "leather_glareshield", [0, 0, -1.0]), (fas, "panel_grey", [1.0, 0, -0.2]),
                         (sof, "panel_titanium", [0, 0, -1.0])):
        # the soffit's clamped end 3.5 mm inboard of the lip's, 1.5 mm inboard of the CB-panel bezel (review r3 K3);
        # final judge r1 LIV-F1-04: the soffit (the brow over the PDUs) dark titanium, not near-black graphite
        P = _clamp_lining(np.array(G), 0.0075 if mat == "panel_titanium" else 0.004,
                          cheek - (0.002 if mat == "panel_titanium" else 0.0))
        # normals from the final faces (the grid's own one-sided differences at the windshield row pointed against the
        # winding on 1.6 % of the hood: review r2 N1 check)
        acc.add(_oriented(grid_surface(P).compute_normals(), hint), mat)
    # contrast stitching along the hood, 8 mm ahead of the lip (brochure p.10)
    H = np.array(hood)
    st = H[:, -1] + (H[:, -2] - H[:, -1]) * (0.008 / np.linalg.norm(H[0, -2] - H[0, -1]))
    band = np.array([st + [0.0006, 0, 0.0008], st + [-0.0006, 0, 0.0008]])
    acc.add(_oriented(grid_surface(_clamp_lining(band.transpose(1, 0, 2), 0.006, cheek - 0.01)), [0, 0, 1.0]),
            "panel_grey")
    # GFC 700 and the eyebrow items on the fascia (centre, BL +/- baro / warn)
    zc = ZM + DETAIL["afcs_z"]

    def fascia_frame(y, z):
        lean = math.radians(DETAIL["fascia_lean"])
        return Fr([float(fascia_x(y, z)), y, z], [0, 1.0, 0], [math.sin(lean), 0.0, math.cos(lean)])
    aw, ah = (float(v) for v in GS["afcs_wh"])
    f = fascia_frame(0.0, zc)
    acc.add(f.se(0, 0, 0.004, (0.5 * aw, 0.5 * ah, 0.009), (0.12, 0.12), (6, 16)), "bezel_black")
    for u in (-0.118, -0.040, 0.050):                                 # FMS / HDG / ALT knobs
        acc.add(f.knob(u, 0.006, 0.0085, 0.014, 14, 0.010), "black")
    for k in range(9):                                                # key row
        acc.add(f.box(-0.125 + k * 0.031, -0.020, 0.0135, (0.014, 0.008, 0.004)), "panel_dark")
    for u in (0.105, 0.125):
        for v in (0.012, -0.004):
            acc.add(f.box(u, v, 0.0135, (0.012, 0.009, 0.004)), "panel_dark")
    for sg in (-1, 1):
        f = fascia_frame(sg * DETAIL["baro_bl"], zc)
        acc.add(f.box(0, 0, 0.004, (0.030, 0.034, 0.008)), "bezel_black")
        acc.add(f.knob(0, 0.003, 0.0085, 0.012, 14, 0.008), "black")
        f = fascia_frame(sg * DETAIL["warn_bl"], zc)
        acc.add(f.box(0, 0, 0.004, (0.078, 0.036, 0.008)), "bezel_black")
        for k in (-1, 1):
            acc.add(f.se(k * 0.019, 0, 0.0085, (0.013, 0.012, 0.003), (0.3, 0.3), (6, 8)), "screen")
        f = fascia_frame(sg * 0.372, zc - 0.012)
        acc.add(f.rect(-0.015, -0.007, 0.015, 0.007, 0.001), "light_white")        # RADIO-CALL placard
        acc.add(f.rect(-0.013, -0.005, 0.013, 0.005, 0.0012), "black")


# =====================================================================================================================
# lower panel: sub-panels (brushed grey), switch blocks, gear handle, parking brake, feather inhibit, oxygen lever
# =====================================================================================================================
def _face_plate(acc, y0, y1, z0, z1, off=0.004, mat="panel_titanium"):
    ny = max(2, int(math.ceil(abs(y1 - y0) / 0.02)) + 1)
    Y, Z = np.meshgrid(np.linspace(y0, y1, ny), np.linspace(z0, z1, 4), indexing="ij")
    P = np.stack([face_x(Y, Z), Y, Z], -1)
    P = _clamp_lining(P, 0.006)
    P[..., 0] = face_x(P[..., 1], P[..., 2])
    Nn = np.zeros_like(P)
    for i in range(ny):
        for j in range(4):
            Nn[i, j] = face_frame(P[i, j, 1], P[i, j, 2]).w
    top = P + off * Nn
    acc.add(_oriented(grid_surface(top), N_AFT), mat)
    for E0, E1 in ((top[:, 0], P[:, 0]), (top[:, -1], P[:, -1]), (top[0], P[0]), (top[-1], P[-1])):
        acc.add(_oriented(_flat(_strip(E0, E1, closed=False)), lambda C: C - top.mean((0, 1))), mat)


# push-button blocks on the inner lower sub-panels [M: P1046408]: rows of dark rectangular buttons with white legends
# under white group placards on the titanium face (final judge r1 I4: the old black square with six toggle dots read as
# an empty block).  Per side: rows (v of the row centre, number of buttons, u of the row centre), button w x h, pitch
# along u, placards (v, half-length); co-pilot: + two white guarded switches (u, v)
BUTTONS = dict(w=0.022, h=0.016, depth=0.005, pitch=0.028, legend=0.0003,
               rows={-1: ((0.044, 3, 0.0), (0.020, 3, 0.0), (-0.026, 3, 0.0), (-0.050, 3, 0.0)),
                     1: ((0.044, 3, 0.0), (0.020, 3, 0.0), (-0.034, 1, -0.030))},
               placards={-1: ((0.061, 0.044), (-0.009, 0.044)), 1: ((0.061, 0.044), (0.003, 0.030))},
               guards={1: ((0.006, -0.034), (0.034, -0.034))})


def _button(acc, f, a, b):
    """One push-button: a dark cap seated on the face with two light legend bars (abstract, no lettering)."""
    q = BUTTONS
    w, h, d = q["w"], q["h"], q["depth"]
    acc.add(f.box(a, b, 0.5 * d, (w, h, d)), "bezel_black")
    c = d + q["legend"]
    acc.add(f.rect(a - 0.34 * w, b + 0.08 * h, a + 0.34 * w, b + 0.26 * h, c), "light_white")
    acc.add(f.rect(a - 0.22 * w, b - 0.26 * h, a + 0.22 * w, b - 0.10 * h, c), "light_white")


def _button_block(acc, f, sg):
    q = BUTTONS
    for v, nb, u0 in q["rows"][sg]:
        for i in range(nb):
            _button(acc, f, u0 + (i - 0.5 * (nb - 1)) * q["pitch"], v)
    for v, hl in q["placards"][sg]:                                    # white group placards (blank)
        acc.add(f.rect(-hl, v - 0.0022, hl, v + 0.0022, 0.0004), "light_white")
    for a, b in q["guards"].get(sg, ()):                              # guarded switches: white guard + bat toggle
        acc.add(f.box(a, b, 0.0055, (0.020, 0.026, 0.011)), "yoke_white")
        acc.add(f.box(a, b, 0.0115, (0.012, 0.018, 0.001)), "bezel_black")
        acc.add(cylinder(f.p(a, b, 0.0115), f.p(a, b + 0.004, 0.024), 0.0022, n=8), "metal")


def _lower_panel(acc):
    acc.group = "panel"
    shw = float(PN["stack_hw"])
    z0, z1 = Z_LO + 0.008, ZM - 0.5 * PDU_H * math.cos(TILT) - DETAIL["recess_margin"] - 0.006
    yc = float(YK["bl"])
    for sg in (-1, 1):
        edges = [shw + 0.008, 0.262, yc + 0.118, float(PN["cheek_bl"])]
        for a, b in zip(edges[:-1], edges[1:]):
            y0, y1 = sorted((sg * (a + 0.003), sg * (b - 0.003)))
            _face_plate(acc, y0, y1, z0, z1)
        zc = 0.5 * (z0 + z1)
        # yoke column boot
        f = face_frame(sg * yc, float(I.yoke_hub(sg)[2])).moved(c=0.004)
        acc.add(revolve([(0.0, 0.050), (0.004, 0.048), (0.010, 0.030), (0.014, 0.026)], n=24, axis_origin=f.o,
                        axis_dir=f.w, ref_dir=f.u, cap_ends=False), "black")
        # inner sub-panel: ICE PROTECTION (pilot) / ELECTRICAL + CABIN PRESSURE (co-pilot) push-button blocks
        _button_block(acc, face_frame(sg * 0.205, zc).moved(c=0.004), sg)
        if sg < 0:
            # landing-gear selector (pilot's lower right panel, next to the stack) and FEATHER INHIBIT
            f = face_frame(-0.160, zc + 0.010).moved(c=0.004)
            acc.add(f.box(0, 0, 0.001, (0.022, 0.090, 0.002)), "bezel_black")
            acc.add(cylinder(f.p(0, 0.02, 0.001), f.p(0, 0.02, 0.045), 0.005, n=10), "steel")   # from inside the
            #                                                                   bezel (r3 K3: coplanar with its back)
            acc.add(revolve([(0.0, 0.004), (0.006, 0.019), (0.014, 0.019), (0.018, 0.004)], n=20,
                            axis_origin=f.p(0.0, 0.02, 0.040), axis_dir=f.u, ref_dir=f.w, cap_ends=True), "grip_black")
            f = face_frame(-0.458, zc - 0.030).moved(c=0.004)
            acc.add(f.box(0, 0, 0.002, (0.024, 0.024, 0.004)), "bezel_black")
            acc.add(f.box(0, 0, 0.0055, (0.014, 0.014, 0.003)), "panel_dark")
            # PARKING BRK T-handle, lower left: a stem out of the bezel and a horizontal grip bar (final judge r1 I4:
            # the upright pillow read as a black slot)
            f = face_frame(-0.635, zc - 0.005).moved(c=0.004)
            acc.add(f.box(0, 0, 0.001, (0.040, 0.075, 0.002)), "bezel_black")
            acc.add(cylinder(f.p(0, -0.012, 0.0015), f.p(0, -0.012, 0.022), 0.0045, n=12), "steel")
            acc.add(f.se(0, -0.012, 0.026, (0.030, 0.0085, 0.0075), (0.35, 0.35), (10, 12)), "black")
        else:
            # OXYGEN lever (vertical slot) next to the stack
            f = face_frame(0.160, zc).moved(c=0.004)
            acc.add(f.box(0, 0, 0.001, (0.018, 0.100, 0.002)), "bezel_black")
            acc.add(f.box(0, -0.030, 0.010, (0.012, 0.016, 0.018)), "panel_dark")
            f = face_frame(0.300, zc + 0.030).moved(c=0.004)
            acc.add(f.rect(-0.022, -0.008, 0.022, 0.008, 0.0015), "light_white")    # cabin pressure placard
        # USB / outboard knob on the outer sub-panel
        f = face_frame(sg * 0.600, zc + 0.020).moved(c=0.004)
        acc.add(f.knob(0, 0, 0.010, 0.012, 14), "black")


# =====================================================================================================================
# centre stack + pedestal (control quadrant) on the nose-wheel tunnel plinth
# =====================================================================================================================
def _pedestal(acc):
    acc.group = "pedestal"
    x0, x1, phw, pz = I.pedestal_plinth()
    shw, hw = float(PN["stack_hw"]), float(PE["hw"])
    st = [(float(p[0]), ZM + float(p[1])) for p in PE["stack"]]
    qx0, qx1 = (float(v) for v in PE["x"])
    zt = FL + float(PE["top_h"])
    xf = float(I.panel_x(Z_LO))
    # side outline (x, z, half-width): stack face with the SDUs, pad, quadrant top, aft face, foot on the plinth
    O = [(st[0][0], st[0][1], shw), (st[1][0], st[1][1], shw), (st[2][0], st[2][1], shw), (st[3][0], st[3][1], hw),
         (qx0, zt, hw), (qx1, zt, hw), (qx1, FL, hw), (x1 + 0.002, FL, hw), (x1 + 0.002, pz, hw), (xf, pz, hw),
         (xf, Z_LO, shw)]
    O = np.array(O)
    # the stack face round the SDUs stays titanium grey; below the SDU pad the quadrant's skins are dark gunmetal
    # with the black slotted quadrant top (throttle photo, P1046408-10: review r3 F3)
    mats = ["panel_dark", "panel_dark", "panel_titanium", "pedestal_gunmetal", "bezel_black", "pedestal_gunmetal", None,
            None, None, "panel_titanium", None]
    # each outline edge faces outward by the polygon's own winding (the centroid test turned the reclined SDU face
    # inward: review r1 C6)
    ccw = 0.5 * float(np.sum(O[:, 0] * np.roll(O[:, 1], -1) - np.roll(O[:, 0], -1) * O[:, 1])) > 0
    for k in range(len(O)):
        a, b = O[k], O[(k + 1) % len(O)]
        if mats[k] is None:
            continue
        q = Mesh(np.array([[a[0], -a[2], a[1]], [b[0], -b[2], b[1]], [b[0], b[2], b[1]], [a[0], a[2], a[1]]]),
                 np.array([[0, 1, 2], [0, 2, 3]]))
        ex_, ez_ = b[0] - a[0], b[1] - a[1]
        nrm = np.array([ez_, 0.0, -ex_]) * (1.0 if ccw else -1.0)
        acc.add(_oriented(q, nrm), mats[k])
    # side cheeks: grey round the stack, gunmetal aft of the SDU pad (the outline clipped at the pad station)
    xs_ = float(st[3][0])

    def clip_x(P, keep_fwd):
        out = []
        for k in range(len(P)):
            a, b = P[k], P[(k + 1) % len(P)]
            ina, inb = (a[0] <= xs_) == keep_fwd, (b[0] <= xs_) == keep_fwd
            if ina:
                out.append(a)
            if ina != inb:
                t = (xs_ - a[0]) / (b[0] - a[0])
                out.append(a + t * (b - a))
        return np.array(out)
    for keep_fwd, mat in ((True, "panel_titanium"), (False, "pedestal_gunmetal")):
        Q = clip_x(O[:, :2], keep_fwd)
        side = planar_cap(np.c_[Q[:, 0], np.zeros(len(Q)), Q[:, 1]], [0, 1.0, 0])
        for sg in (-1, 1):
            s = side.copy()
            s.V[:, 1] = sg * O[np.argmin(np.linalg.norm(s.V[:, None, [0, 2]] - O[None, :, [0, 1]], axis=2), 1), 2]
            acc.add(_oriented(s, [0, sg, 0]), mat)
    # rounded rails along the top edges (brushed, P1046408 / throttle photo) and down the aft edges, their outer faces
    # on the drawn half-widths (PEDESTAL hw; review r3 C2: rev C stood 5 mm proud of them); grey on the stack, gunmetal
    # from the SDU pad aft
    rr_ = 0.009
    path = np.array([(p[0], p[1]) for p in O[:6]])
    hws = O[:6, 2]
    for sg in (-1, 1):
        P3 = np.c_[path[:, 0], sg * (hws - rr_), path[:, 1] + 0.002]
        P3 = np.vstack([P3[:5], [[qx1 - 0.01, sg * (hw - rr_), zt + 0.002]],
                        [[qx1 - rr_, sg * (hw - rr_), zt - 0.01]], [[qx1 - rr_, sg * (hw - rr_), FL + 0.02]]])
        for part_, mat in ((P3[:4], "panel_titanium"), (P3[3:], "pedestal_gunmetal")):
            dense = [part_[0]]
            for a, b in zip(part_[:-1], part_[1:]):
                n = max(1, int(np.linalg.norm(b - a) / 0.02))
                dense += [a + (b - a) * t for t in np.linspace(0, 1, n + 1)[1:]]
            acc.add(sweep_profile(np.array(dense),
                                  np.c_[rr_ * np.cos(np.linspace(0, 2 * np.pi, 10, endpoint=False)),
                                        rr_ * np.sin(np.linspace(0, 2 * np.pi, 10, endpoint=False))]), mat)
    # pad under the SDUs: COM 1/2 VOL knobs and the flat hand-rest pad
    pv = _unit(np.array([st[2][0] - st[3][0], 0.0, st[2][1] - st[3][1]]))
    pc = 0.5 * (np.array([st[2][0], 0.0, st[2][1]]) + np.array([st[3][0], 0.0, st[3][1]]))
    f = Fr(pc, [0, 1.0, 0], pv)
    acc.add(f.se(0, -0.005, 0.002, (0.075, 0.040, 0.003), (0.1, 0.1), (6, 12)), "panel_grey")
    for sg in (-1, 1):
        acc.add(f.knob(sg * 0.105, 0.035, 0.009, 0.014, 14), "black")
    # quadrant top (fwd -> aft): TRIM INTERRUPT, ALTERNATE STAB TRIM, AILERON TRIM, FLAP INTERRUPT (guarded)
    ft = Fr([0.5 * (qx0 + qx1), 0.0, zt], [1.0, 0, 0], [0, 1.0, 0])   # u = aft, v = starboard, w = up
    for a, b, sz, mat in ((-0.160, -0.070, (0.018, 0.018, 0.006), "panel_dark"),
                          (-0.160, -0.030, (0.024, 0.014, 0.010), "black"),
                          (-0.160, 0.015, (0.018, 0.026, 0.010), "black"),
                          (-0.155, 0.070, (0.022, 0.020, 0.012), "light_amber")):
        acc.add(ft.box(a, b, 0.5 * sz[2], sz), mat)
    # PCL (power control lever: slot, stem, big grey knob) and flap lever (slot, black paddle)
    pcx, pcy, pch = (float(v) for v in PE["pcl"])
    fx_, fy_, fh_ = (float(v) for v in PE["flap"])
    for (xa, xb, y) in ((pcx - 0.11, pcx + 0.07, pcy), (fx_ - 0.07, fx_ + 0.09, fy_)):
        acc.add(box([0.5 * (xa + xb), y, zt + 0.0006], (xb - xa, 0.012, 0.0012)), "black")
    acc.add(cylinder([pcx + 0.020, pcy, zt], [pcx + 0.004, pcy, FL + pch - 0.045], 0.008, n=10), "metal")
    # PCL grip: a satin pewter paddle, thin fore / aft, tall, round-topped, tipped forward (throttle photo, P1046408-10;
    # review r3 F3: rev C was a flat 60 x 88 x 48 puck); its top on the drawn PCL height (PEDESTAL pcl)
    Rk = np.array(Fr([0, 0, 0], [math.cos(0.30), 0, math.sin(0.30)], [0, 1.0, 0]).R)     # top tipped forward
    gd, gw, gh = (0.5 * float(v) for v in PE["pcl_grip"])
    g_ = superellipsoid([0.0, 0.0, 0.0], (gd, gw, gh), (0.65, 0.35), nu=12, nv=16)
    zc_ = g_.V[:, 2] / gh                                               # the paddle narrows toward its stem
    g_.V[:, 1] *= 0.62 + 0.38 * np.clip((zc_ + 1.0) / 1.3, 0.0, 1.0) ** 0.8
    g_.V[:, 0] *= 0.80 + 0.20 * np.clip((zc_ + 1.0) / 1.3, 0.0, 1.0)
    g_ = Mesh(g_.V @ Rk.T + [pcx, pcy, FL + pch - gh], g_.F)
    acc.add(g_, "pcl_pewter")
    acc.add(cylinder([fx_ + 0.010, fy_, zt], [fx_, fy_, FL + fh_ - 0.015], 0.005, n=8), "metal")
    acc.add(superellipsoid([fx_, fy_, FL + fh_ - 0.010], (0.012, 0.015, 0.016), (0.3, 0.3), nu=8, nv=12), "black")
    # lighting-knob row and the CCD palm grip at the aft end
    for k in range(6):
        acc.add(ft.knob(0.100, -0.075 + 0.030 * k, 0.0065, 0.012, 12), "black")
    ccx, ccy, cch = (float(v) for v in PE["ccd"])
    acc.add(superellipsoid([ccx, ccy, FL + cch - 0.020], (0.045, 0.034, 0.021), (0.5, 0.5), nu=10, nv=16),
            "grip_black")
    acc.add(cylinder([ccx - 0.028, ccy, FL + cch - 0.004], [ccx - 0.028, ccy, FL + cch + 0.006], 0.007, n=12),
            "panel_grey")
    # aft face: FUEL / ACS emergency shut-off T-handles (red), emergency gear extension (centre), Pilatus band
    fa = Fr([qx1 + 0.0005, 0.0, FL], [0, 1.0, 0], [0, 0, 1.0])       # w = aft
    acc.add(fa.rect(-hw + 0.012, 0.030, hw - 0.012, zt - FL - 0.040, 0.0), "bezel_black")
    acc.add(fa.rect(-hw + 0.006, zt - FL - 0.032, hw - 0.006, zt - FL - 0.010, 0.0004), "panel_grey")
    # final judge r1 I7 (P1046406 / 08): FLAT red pull paddles -- a bottle-shaped plate (wide body, tapered neck) with
    # a T grip on top and white legend bars low on the body, standing 15 mm proud of the black panel (the rounded
    # pillows read as two red cylinders)
    body = _fillet(np.array([(-0.017, 0.072), (0.017, 0.072), (0.017, 0.172), (0.010, 0.198), (0.010, 0.226),
                             (-0.010, 0.226), (-0.010, 0.198), (-0.017, 0.172)]), 0.004, n=3, max_seg=0.01)
    for sg in (-1, 1):
        fp = Fr(fa.p(sg * 0.056, 0.0, 0.0080), fa.u, fa.v)
        acc.add(_extrusion(fp, body, 0.015, bevel=0.003), "paint_red")
        acc.add(_extrusion(fp, rrect_loop(0.024, 0.0095, 0.006, cx=0.0, cy=0.232), 0.017, bevel=0.004), "paint_red")
        for v0, v1, hl in ((0.084, 0.091, 0.010), (0.097, 0.104, 0.007), (0.140, 0.146, 0.011)):
            acc.add(fp.rect(-hl, v0, hl, v1, 0.0080), "light_white")
    acc.add(fa.se(0.0, 0.150, 0.008, (0.018, 0.070, 0.008), (0.3, 0.3), (8, 12)), "black")
    acc.add(fa.rect(-0.012, 0.185, 0.012, 0.197, 0.0170), "light_white")          # 'OPEN' flag


def _plinth_floor(acc, floor=True):
    """Carpeted plinth over the nose-wheel tunnel (open shell: side walls from under the floor + top) and the
    flight-deck floor fitted to the lining, open over the tunnel; threshold strip at the divider; footwell front."""
    from cad.sdf2d import rrect_outline
    acc.group = "floor"
    x0, x1, phw, pz = I.pedestal_plinth()
    ol = rrect_outline(0.5 * (x0 + x1), 0.0, 0.5 * (x1 - x0), phw, 0.05, n_corner=6)
    zb = FL - float(I.FLOOR["t"])
    walls = _strip(np.c_[ol, np.full(len(ol), zb)], np.c_[ol, np.full(len(ol), pz)])
    c = np.array([0.5 * (x0 + x1), 0.0, 0.5 * (zb + pz)])
    acc.add(_oriented(walls, lambda C: C - c), "carpet_flightdeck")
    acc.add(_oriented(planar_cap(np.c_[ol, np.full(len(ol), pz)], [0, 0, 1.0]), [0, 0, 1.0]), "carpet_flightdeck")
    if not floor:
        return
    L = lining()
    xa, xd = float(I.FLOOR["fd_x0"]), float(DV["x_aft"])

    def hwf(x):
        return L.hw(x, FL + 0.002) - 0.001

    for xs_, slot in ((np.linspace(xa, x0, 4), False), (np.linspace(x0, x1, 24), True), (np.linspace(x1, xd, 12),
                                                                                         False)):
        w = hwf(xs_)
        if slot:
            for sg in (-1, 1):
                Y = np.stack([sg * np.full_like(w, phw - 0.002), sg * w], 1)
                P = np.stack([np.repeat(xs_[:, None], 2, 1), Y, np.full_like(Y, FL)], -1)
                acc.add(_oriented(grid_surface(P), [0, 0, 1.0]), "carpet_flightdeck")
        else:
            Y = np.linspace(-1, 1, 9)[None, :] * w[:, None]
            P = np.stack([np.repeat(xs_[:, None], 9, 1), Y, np.full_like(Y, FL)], -1)
            acc.add(_oriented(grid_surface(P), [0, 0, 1.0]), "carpet_flightdeck")
    # threshold strip across the divider opening (metal, flush floor: P1046406)
    ob0, ob1 = (float(v) for v in DV["open_bl"])
    # (final judge r1 I7: a polished strip, 55 mm, as P1046406's bright threshold; was a 40 mm satin bar)
    acc.add(box([xd, 0.5 * (ob0 + ob1), FL + 0.0015], (0.055, ob1 - ob0 + 0.02, 0.003)), "chrome_trim")
    # footwell front closure at the forward end of the lining (dark)
    S = I.lining_section(xa, n=361)
    S = S[S[:, 1] >= zb]
    k = np.argsort(np.arctan2(S[:, 1] - 1.7, S[:, 0]))
    ring = np.c_[np.full(len(S), xa + 0.001), S[k, 0] * 0.995, S[k, 1]]
    acc.add(_oriented(planar_cap(ring, [1.0, 0, 0]), [1.0, 0, 0]), "black")


# =====================================================================================================================
# yokes, pedals
# =====================================================================================================================
def _loft_grip(fr, L, w0, w1, d0, d1, e=0.55, n=18, nr=16):
    """Tapered, round-ended grip along fr.u (0 .. L from the bottom end): half-width across (fr.v) w0 -> w1, half-depth
    (fr.w) d0 -> d1; superellipse sections (exponent e)."""
    s = 0.5 * (1 - np.cos(np.linspace(0.0, np.pi, nr)))
    end = np.sqrt(np.clip(1.0 - (np.clip(np.abs(2 * s - 1) - 0.62, 0, None) / 0.38) ** 2, 0.0, 1.0))
    w = (w0 + (w1 - w0) * s) * end
    d = (d0 + (d1 - d0) * s) * end
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    cu = np.sign(ca) * np.abs(ca) ** e
    su = np.sign(sa) * np.abs(sa) ** e
    G = np.array([fr.p(np.full(n, L * si), wi * cu, di * su) for si, wi, di in zip(s, w, d)])
    axis0 = fr.o
    return _oriented(grid_surface(G, close_v=True),
                     lambda C: C - (axis0 + np.outer((C - axis0) @ fr.u, fr.u)))


def _taper(fr, m, hh, hd, k=(1.0, 0.80, 0.42)):
    """Yoke hub depth taper: full depth at the stem (column side), thin shell at the top edge -- the white shield's
    face leans back toward its top (P1046409, brochure p.12)."""
    L = (m.V - fr.o) @ fr.R
    f = np.interp(L[:, 1], [-0.5 * hh, 0.0, 0.5 * hh], list(k))
    L[:, 2] = -0.5 * hd + (L[:, 2] + 0.5 * hd) * f
    out = Mesh(fr.o + L @ fr.R.T, m.F)
    return out


def _geo_mesh(g, fr, lean=None, mat_of=None):
    """seats.Geo pillow (a, b, c) -> [(Mesh, material)] in the hub frame fr (u = a, v = b, w = c); lean(a, b, c) -> dc:
    an optional change of c (the hub's aft face leaning back toward its top)."""
    V = g.V.copy()
    if lean is not None:
        V[:, 2] += lean(V[:, 0], V[:, 1], V[:, 2])
    g2 = type(g)(fr.p(V[:, 0], V[:, 1], V[:, 2]), g.F, g.pid, g.mats)
    return g2.meshes()


def _top_height(g, a, b):
    """c of a pillow's top face (piece 0, and 3: a re-coloured part of it) at (a, b): barycentric interpolation in the
    plan (None outside it)."""
    T = g.F[(g.pid == 0) | (g.pid == 3) | (g.pid == 4)]
    P = g.V[T]
    for tri in P:
        (x0, y0, _), (x1, y1, _), (x2, y2, _) = tri
        det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(det) < 1e-16:
            continue
        l0 = ((y1 - y2) * (a - x2) + (x2 - x1) * (b - y2)) / det
        l1 = ((y2 - y0) * (a - x2) + (x0 - x2) * (b - y2)) / det
        l2 = 1.0 - l0 - l1
        if min(l0, l1, l2) >= -1e-9:
            return float(l0 * tri[0, 2] + l1 * tri[1, 2] + l2 * tri[2, 2])
    return None


def _grip_loft(o, ax, lat, dep, L, w_prof, d_prof, c_prof, n=16, nr=18, e=0.6):
    """Paddle grip lofted along ax from o (0 .. L): superellipse sections, half-width w_prof(s) across (lat), half-depth
    d_prof(s) along dep, centre offset c_prof(s) along dep, s = 0 .. 1; both ends rounded (the sections shrink on a
    quarter circle over the end radius)."""
    s = 0.5 * (1 - np.cos(np.linspace(0.0, np.pi, nr)))
    w, d, c = w_prof(s), d_prof(s), c_prof(s)
    r0, r1 = w[0] / L, w[-1] / L                                       # end radii as fractions of L
    k0 = np.sqrt(np.clip(1.0 - np.clip((r0 - s) / r0, 0, 1) ** 2, 0.0, 1.0))
    k1 = np.sqrt(np.clip(1.0 - np.clip((s - (1 - r1)) / r1, 0, 1) ** 2, 0.0, 1.0))
    k = np.minimum(k0, k1)
    k = np.maximum(k, 1e-3)
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    cu = np.sign(ca) * np.abs(ca) ** e
    su = np.sign(sa) * np.abs(sa) ** e
    G = np.array([o + L * si * ax + (wi * ki) * np.outer(cu, lat) + (di * ki * su + ci)[:, None] * dep
                  for si, wi, di, ci, ki in zip(s, w, d, c, k)])
    m = grid_surface(G, close_v=True)
    tip0, tip1 = G[0].mean(0), G[-1].mean(0)
    n_ = len(G[0])
    i = np.arange(n_)
    caps = [Mesh(np.vstack([G[0], tip0[None]]), np.stack([i, (i + 1) % n_, np.full(n_, n_)], 1)),
            Mesh(np.vstack([G[-1], tip1[None]]), np.stack([i, (i + 1) % n_, np.full(n_, n_)], 1))]
    centre = lambda C: C - (o + np.outer((C - o) @ ax, ax))                    # noqa: E731
    return Mesh.merge([_oriented(m, centre), _oriented(caps[0], -ax), _oriented(caps[1], ax)])


def _yokes(acc):
    """PC-24-style yokes (YOKE table; P1046408 face-on, P1046409, brochure p.12): a black yoke body (the drawn
    interior.yoke_body_yz: from the grip heads its arms sweep down-inboard round the shield to the stem), the domed
    white goblet shield on it (interior.yoke_shield_yz: top corners at +/- hub width / 2, a shallow V top edge, concave
    sides) with a RECESSED silver centre insert carrying the badge (modelled, not painted), the two canted paddle grips
    swelling to a round head (YOKE grip_head, hat switch on top, trim rocker on the pilot's-side grip), TCS on the white
    outboard shoulder, AFCS DISC on the black arm below it; horizontal column into the lower panel.  Everything stays
    inside the envelope the L6B knee / yoke check sweeps (interior.yoke_roll_clearances): the x-slab hub face .. hub
    face + hub depth times the drawn front-view outline.  The aft faces lean back 10 mm toward the top (P1046409).
    Review r1 F4 / C3 / C5: no coplanar white / black faces, every button seated on its surface; review r3 F2: the
    shield no longer runs out to the grips, the black arms carry them."""
    from model import seats as S
    acc.group = "yokes"
    hw, hh, hd = (float(v) for v in YK["hub_whd"])
    gl, gr, gc = (float(v) for v in YK["grip"])
    hl, rh = (float(v) for v in YK["grip_head"])
    lean_k = 0.010 / 0.11                                         # aft face 10 mm further forward at the top edge

    def lean(a, b, c):
        return -lean_k * np.clip(b + 0.055, 0.0, None) * np.clip(c / hd, 0.0, 1.0)
    # black body: the drawn body outline (c 0.004 .. hd - 0.016, + dome), behind the shield
    body_ol = S.fillet(I.yoke_body_yz(), 0.010, max_len=0.012)
    cb0, cbt = 0.004, hd - 0.016
    body = S.pillow(body_ol, cbt, 0.010, 0.005, h=0.012, crown=S.dome(0.003, 0.012), n_round=2)
    body = body.map(lambda V: V + [0.0, 0.0, cb0])
    # white goblet shield (the drawn shield outline), proud of the body
    shield = I.yoke_shield_yz()
    tc = shield[np.abs(shield[:, 0]) > 0.5 * hw - 1e-9]                # the two top corners
    far = np.min(np.linalg.norm(shield[:, None, :] - tc[None, :, :], axis=2), axis=1)
    shield = shield[(far < 1e-9) | (far > 0.025)]                    # side samples next to the acute top corners
    shield = S.fillet(shield, 0.010, max_len=0.005)                   # dropped (< 1 mm): full-radius corners
    # recessed silver insert: badge panel narrowing to a rounded tongue [M: P1046408 / 09], its top 5 mm under the
    # shield's V
    r_w = 0.006                                                       # the shield's top-edge roll
    ti = 0.5 * hh - float(YK["shield_dip"]) - r_w - 0.003               # inside the top face (its seams kept)
    # final judge r1 I2 (P1046408): the grey insert is a tongue in the LOWER middle of the shield (about 0.3 of its top
    # width, from ~15 mm above the hub centre down toward the stem), white all round and above it up to the badge band
    # along the top edge -- the rev D insert ran up to the top edge and read as a grey V framed by a thin white rim
    ti = min(ti, 0.016)
    insert = np.array([(0.010, -0.036), (0.016, -0.022), (0.020, -0.004), (0.022, ti), (-0.022, ti),
                       (-0.020, -0.004), (-0.016, -0.022), (-0.010, -0.036)])
    insert = S.fillet(insert, 0.007, max_len=0.003)
    rec = 0.0028

    def crown_w(a, b, d):
        sd = sdf2d.polygon(a, b, insert)
        return 0.0045 * S.smoothstep(0.0, 0.016, d) - rec * (sd < 0.0)
    cw0, cwt = hd - 0.034, 0.029
    fb0 = S._STATS["cap_fallback"]
    white = S.pillow(shield, cwt, r_w, 0.004, h=0.0055, crown=crown_w, seams=[insert])
    assert S._STATS["cap_fallback"] == fb0, "yoke shield: the insert seam left the top face"
    white = white.map(lambda V: V + [0.0, 0.0, cw0])
    tops = np.nonzero(white.pid == 0)[0]
    Pc = white.V[white.F[tops]]
    inside = sdf2d.polygon(Pc[..., 0].ravel(), Pc[..., 1].ravel(), insert).reshape(-1, 3) < 0.0
    pid = white.pid.copy()
    pid[tops[inside.all(1)]] = 3                                      # insert floor
    pid[tops[inside.any(1) & ~inside.all(1)]] = 4                     # recess wall: its own normals (crisp edge)
    white = S.Geo(white.V, white.F, pid, {0: "yoke_white", 1: "yoke_white", 2: "yoke_white", 3: "panel_silver",
                                          4: "yoke_white"})
    body.mats = {0: "grip_black", 1: "grip_black", 2: "grip_black"}
    for sg in (-1, 1):
        acc.group = "yoke_" + SIDE[sg]                                  # own part + pivot (review r2 M4)
        hub = I.yoke_hub(sg)
        xf = float(I.panel_x(hub[2]))
        fr = Fr([hub[0], hub[1], hub[2]], [0, 1.0, 0], [0, 0, 1.0])          # w = aft, c = 0 at the hub face
        for g in (body, white):
            for m, mat in _geo_mesh(g, fr, lean):
                acc.add(m, mat)

        def on(g, a, b):
            c = _top_height(g, a, b)
            return c + float(lean(np.array(a), np.array(b), np.array(c)))
        # badge on the insert floor, TCS on the white inboard shoulder, AFCS DISC on the black shoulder
        zb = 0.5 * hh - float(YK["shield_dip"]) - 0.0125                # silver badge band along the top edge
        cbg = on(white, 0.0, zb)                                          # (P1046408: ~0.35 of the top width)
        acc.add(fr.se(0.0, zb, cbg + 0.0004, (0.024, 0.0042, 0.0012), (0.3, 0.3), (6, 12)), "metal")
        ob = sg                                                        # outboard: TCS on the white shoulder, the
        c_t = on(white, ob * 0.052, 0.040)                             # red AFCS DISC below it on the black arm
        acc.add(fr.knob(ob * 0.052, 0.040, 0.0068, 0.0055, 16, c_t - 0.0015), "black")      # (P1046408 pair)
        c_r = on(body, ob * 0.066, 0.012)
        acc.add(fr.knob(ob * 0.066, 0.012, 0.0046, 0.0045, 12, c_r - 0.0015), "light_red")
        # grips on the canted axes (interior.yoke_grip_axis, radius YOKE grip), centred in the hub slab
        for d in (-1, 1):
            p0, p1 = I.yoke_grip_axis(d)
            ax2 = _unit(np.r_[p1 - p0])
            b0 = p0 - gr * ax2                                          # bottom end of the grip (front view)
            ax = ax2[0] * fr.u + ax2[1] * fr.v
            lat = d * (ax2[1] * fr.u - ax2[0] * fr.v)                    # outboard, across the grip
            o = fr.p(b0[0], b0[1], 0.5 * hd)
            s_h0, s_h1 = 1.0 - (hl + 0.010) / gl, 1.0 - rh / gl                # swollen head (YOKE grip_head)
            wp = lambda s_: gr * 0.93 + (rh - gr * 0.93) * S.smoothstep(s_h0, s_h1, s_)    # noqa: E731
            # final judge r1 I2: slimmer paddles (depth 0.62 -> 0.85 of the hub slab from the root to the head; 0.80 ->
            # 0.98 read as fat round handles from behind)
            dp = lambda s_: (0.5 * hd - 0.004) * (0.62 + 0.23 * S.smoothstep(0.45, 0.9, s_))   # noqa: E731
            cp = lambda s_: 0.002 * S.smoothstep(0.5, 0.95, s_)                 # noqa: E731 -- head leans aft
            acc.add(_grip_loft(o, ax, lat, fr.w, gl, wp, dp, cp), "grip_black")
            # grained leather panel on the outboard / aft face [M: P1046408 / brochure p.12]
            pc = o + 0.42 * gl * ax + 0.25 * gr * lat + (0.5 * hd - 0.004) * 0.66 * fr.w
            acc.add(superellipsoid(pc, (0.30 * gl, 0.55 * gr, 0.0020), (0.5, 0.5), nu=8, nv=14,
                                   R=np.stack([ax, lat, fr.w], 1)), "black")
            hdir = _unit(ax + 0.5 * fr.w)                               # hat switch on the head, aft-up
            tip = o + (gl - 0.016) * ax + 0.006 * fr.w
            acc.add(cylinder(tip, tip + 0.010 * hdir, 0.0048, n=12), "black")    # black thumb knob (P1046408)
            acc.add(cylinder(tip + 0.010 * hdir, tip + 0.0145 * hdir, 0.0070, n=12), "black")
            if d == sg:                                                  # trim rocker, aft face of the head
                q = o + (gl - 0.032) * ax + (0.5 * hd - 0.004) * 0.83 * fr.w
                acc.add(superellipsoid(q, (0.007, 0.005, 0.004), (0.4, 0.4), nu=6, nv=10,
                                       R=np.stack([ax, lat, fr.w], 1)), "panel_grey")
        # horizontal column into the lower panel (into the black body's forward face)
        acc.add(cylinder([xf - 0.03, hub[1], hub[2]], [hub[0] + 0.010, hub[1], hub[2]],
                         float(YK["column_r"]), n=16), "steel")


SIDE = {-1: "L", 1: "R"}


def control_pivots():
    """{group / part id: pivot} of the crew controls built as their own parts (review r2 M4), model axes:
    yoke_L / yoke_R: kind 'yoke' -- origin the hub centre, axis along the column pointing FORWARD (a + rotation is a
    right roll, clockwise as the pilot sees it), roll_deg = YOKE roll, travel = the column's pitch travel along +x (aft)
    at full pull / full push (YOKE travel);
    pedal_<seat><foot> (LL, LR, RL, RR): kind 'pedal' -- origin the hanging arm pivot (PEDALS pivot, under the lower
    panel), axis -y, travel_deg = the rotation that moves the pad PEDALS travel, gearing +1 for the right-foot pedals
    (forward with right rudder), -1 for the left: angle = -gearing x yaw x travel_deg (+ yaw = right rudder; a -
    rotation about -y swings the pad, BELOW the pivot, forward)."""
    out = {}
    t0, t1 = (float(v) for v in YK["travel"])
    for sg in (-1, 1):
        hub = I.yoke_hub(sg)
        out["yoke_" + SIDE[sg]] = dict(origin=tuple(float(v) for v in hub), axis=(-1.0, 0.0, 0.0), kind="yoke",
                                       roll_deg=float(YK["roll"]), travel_pull=(t1, 0.0, 0.0),
                                       travel_push=(t0, 0.0, 0.0), note="interior.YOKE roll / travel")
    pp = I.pedal_points(0.0)
    d = np.array([pp["dir"][0], pp["dir"][1]])
    pl = float(PD["pad_wh"][1])
    hx, hz = (float(v) for v in PD["pivot"])
    pad = pp["heel"] + (0.06 + 0.5 * pl) * d
    arm = float(np.hypot(pad[0] - hx, pad[1] - (FL + hz)))
    tdeg = math.degrees(float(PD["travel"]) / arm)
    for sg in (-1, 1):
        for dd in (-1, 1):
            yc = sg * float(I.CREW_SEAT["bl"]) + dd * float(PD["dy"])
            out["pedal_" + SIDE[sg] + SIDE[dd]] = dict(origin=(hx, yc, FL + hz), axis=(0.0, -1.0, 0.0), kind="pedal",
                                                     travel_deg=tdeg, gearing=float(dd),
                                                     note="interior.PEDALS travel at the pad")
    return out


def _pedals(acc):
    """Rudder pedals at neutral crank (interior.pedal_points): pads at seat CL +/- PEDALS dy on the drawn face line,
    HANGING arms from the rudder-bar torque tube under the lower panel (PEDALS pivot; model judging r1 INT-m1: P1046408
    / 09 show dark arms and rods filling the knee hole), toe-brake master cylinders on the arms, the adjustment crank
    between each pair on the floor."""
    acc.group = "pedals"
    pp = I.pedal_points(0.0)
    d = np.array([pp["dir"][0], 0.0, pp["dir"][1]])                 # up the pedal face
    heel = np.array([pp["heel"][0], 0.0, pp["heel"][1]])
    pw, pl = (float(v) for v in PD["pad_wh"])
    hx, hz = (float(v) for v in PD["pivot"])
    for sg in (-1, 1):
        for dd in (-1, 1):
            acc.group = "pedal_" + SIDE[sg] + SIDE[dd]                  # own part + pivot (review r2 M4)
            yc = sg * float(I.CREW_SEAT["bl"]) + dd * float(PD["dy"])
            s_c = 0.06 + 0.5 * pl
            f = Fr(heel + s_c * d + [0.0, yc, 0.0], [0, 1.0, 0], d)
            acc.add(f.se(0, 0, 0.004, (0.5 * pw, 0.5 * pl, 0.008), (0.25, 0.25), (8, 14)), "black")
            # fine tread (final judge r1 I7 / R9: five metal ribs read as ladder slats): eleven narrow dark ribs
            for k in range(-5, 6):
                acc.add(f.box(0, k * 0.0145, 0.0118, (pw - 0.026, 0.0035, 0.0020)), "bezel_black")
            piv = np.array([hx, yc, FL + hz])
            top = f.p(0.0, 0.050, -0.002)                             # into the pad's back (it floated 6 mm)
            mid = f.p(0.0, -0.020, -0.004)
            for sy in (-1, 1):                                         # two dark hanging arms (P1046408 / 09)
                off = np.array([0.0, sy * 0.032, 0.0])
                acc.add(cylinder(piv + off, mid + off, 0.0075, n=10), "metal_dark")
                acc.add(cylinder(mid + off, mid + off * 0.6 + [0.010, 0, -0.030], 0.0065, n=8), "metal_dark")
            acc.add(cylinder(piv + [0.0, -0.040, 0.0], piv + [0.0, 0.040, 0.0], 0.014, n=12), "metal_dark")  # hub
            # toe-brake master cylinder: from the arm hub down to the pad's top (its body steel, the rod chrome)
            cb_ = piv + [0.035, 0.0, -0.030]
            cm_ = cb_ + 0.6 * (top - cb_)
            acc.add(cylinder(cb_, cm_, 0.010, n=10), "steel")
            acc.add(cylinder(cm_, top, 0.004, n=8), "chrome_trim")
            acc.group = "pedals"
        # rudder-bar torque tube across each pair at the arm pivots and its two bearing brackets up under the lower
        # panel (fixed; the pedal arms turn on it)
        y0, y1 = sg * float(I.CREW_SEAT["bl"]) - float(PD["dy"]) - 0.05, sg * float(I.CREW_SEAT["bl"]) + float(PD["dy"]) + 0.05
        acc.add(cylinder([hx, y0, FL + hz], [hx, y1, FL + hz], 0.009, n=10), "metal_dark")
        for yb in (y0, y1):
            acc.add(box([hx, yb, FL + hz + 0.045], (0.045, 0.012, 0.100)), "metal_dark")
        # adjustment crank between each pair (POH 7-3-4), on the floor
        c = np.array([3.110, sg * float(I.CREW_SEAT["bl"]), FL + 0.030])
        acc.add(box(c, (0.040, 0.050, 0.050)), "metal_dark")
        acc.add(cylinder(c + [0.02, 0, 0.0], c + [0.045, 0, 0.0], 0.006, n=8), "steel")
        acc.add(cylinder(c + [0.045, 0, 0.0], c + [0.045, 0, 0.035], 0.005, n=8), "steel")


# =====================================================================================================================
# side consoles (cup-holder pods), CB panels on the sidewalls
# =====================================================================================================================
def _consoles(acc):
    acc.group = "consoles"
    L = lining()
    xa, xb = (float(v) for v in SC["x"])
    zt = FL + float(SC["top_h"])
    yi = float(SC["inner_bl"])
    rr = 0.025                      # rounded top inboard edge (model judging r1 INT-m6: R 15 -> 25, P1046409)
    xs = np.linspace(xa, xb, 17)
    zz = np.linspace(FL, zt, 40)
    na = 7
    for sg in (-1, 1):
        secs = []
        for x in xs:
            h = L.hw(x, zz)
            ok = np.nonzero(h > yi + 0.003)[0]
            zb = zz[ok[0]] if len(ok) else zt - 0.05
            zb = min(zb, zt - 0.06)
            zk = max(zb + 0.010, zt - 0.200)                         # kick-panel / upper-face joint
            yo = float(L.hw(x, zt)) - 0.002
            a = np.radians(np.linspace(180.0, 90.0, na))
            arc = np.c_[yi + rr + rr * np.cos(a), zt - rr + rr * np.sin(a)]
            sec = np.vstack([[yi, zb], [yi, zk], [yi, 0.5 * (zk + zt - rr)], arc, [0.5 * (yi + rr + yo), zt],
                             [yo, zt]])
            secs.append(np.c_[np.full(len(sec), x), sg * sec[:, 0], sec[:, 1]])
        G = np.array(secs)
        hint = lambda C: np.c_[np.zeros(len(C)), -sg * np.ones(len(C)), 0.5 * np.ones(len(C))]   # noqa: E731
        # dark kick panel below, the flight-deck lining grey above and over the top (P1046409 / AOPA: the console is
        # the lining's grey with a darker lower part, not a black box), a satin-titanium trim band on the rounded edge
        acc.add(_oriented(grid_surface(G[:, :2]), hint), "panel_dark")
        acc.add(_oriented(grid_surface(G[:, 1:]), hint), "lining_flightdeck")
        a = np.radians(np.linspace(165.0, 100.0, 6))
        trim_ = np.stack([np.c_[np.full(6, x), sg * (yi + rr + (rr + 0.0012) * np.cos(a)),
                                zt - rr + (rr + 0.0012) * np.sin(a)] for x in xs[1:-1]])
        acc.add(_oriented(grid_surface(trim_), hint), "panel_titanium")
        for k, sgn in ((0, -1.0), (-1, 1.0)):                     # end caps, closed along the lining curve
            x = G[k][0, 0]
            zl = np.linspace(zt, G[k][0, 2], 12)[1:]
            back = np.c_[np.full(len(zl), x), sg * (L.hw(x, zl) - 0.002), zl]
            ring = np.vstack([G[k], back])
            acc.add(_oriented(planar_cap(ring, [sgn, 0, 0]), [sgn, 0, 0]), "lining_flightdeck")
        # cup-holder pod under the CB panel (two holders), USB on the console face
        cx0, cx1 = DETAIL["cup_x"]
        yo = float(L.hw(0.5 * (cx0 + cx1), zt)) - 0.004
        pod_y = 0.5 * (yi - 0.020 + yo)
        acc.add(superellipsoid([0.5 * (cx0 + cx1), sg * pod_y, zt - 0.022],
                               (0.5 * (cx1 - cx0) + 0.045, 0.5 * (yo - yi + 0.020), 0.024), (0.2, 0.25), nu=8, nv=18),
                "panel_dark")
        for cx in (cx0, cx1):
            ctr = np.array([cx, sg * (yi + 0.030), zt + 0.0025])
            acc.add(disk(ctr, [0, 0, 1.0], 0.034, n=24, r_inner=0.029), "chrome_trim")
            acc.add(disk(ctr + [0, 0, 0.0005], [0, 0, 1.0], 0.029, n=24), "black")
        f = Fr([xa + 0.10, sg * (yi - 0.0005), zt - 0.12], [1.0, 0, 0], [0, 0, 1.0], [0, -sg, 0])
        acc.add(f.rect(-0.012, -0.006, 0.012, 0.006), "black")
        acc.add(f.rect(-0.030, 0.020, 0.030, 0.034, 0.0002), "light_white")        # 1-kg pocket placard
        for du in (-0.026, -0.008):                                # USB-A / -C socket pair (P1046409)
            acc.add(f.rect(du - 0.007, -0.034, du + 0.007, -0.024, 0.0003), "black")
            acc.add(f.rect(du - 0.0045, -0.0305, du + 0.0045, -0.0275, 0.0006), "chrome_trim")
    # circuit-breaker panels on the sidewall lining above the consoles (rows 1-4, lit legends): group 'cb_panels', hung
    # on the lining part like the overhead panel (viewer cutaway, review r1 M3)
    acc.group = "cb_panels"
    cx0, cx1, h0, h1 = (float(v) for v in SC["cb_panel"])
    nr, nb, kr = DETAIL["cb"]
    for sg in (-1, 1):
        X, Z = np.meshgrid(np.linspace(cx0, cx1, 8), np.linspace(FL + h0, FL + h1, 8), indexing="ij")
        Yv = sg * (L.hw(X, Z) - 0.006)
        P = np.stack([X, Yv, Z], -1)
        acc.add(_oriented(grid_surface(P), [0, -sg, 0]), "bezel_black")
        pc_ = P.reshape(-1, 3).mean(0)
        for E0 in (P[0], P[-1], P[:, 0], P[:, -1]):
            E1 = E0.copy()
            E1[:, 1] = sg * (L.hw(E0[:, 0], E0[:, 2]) - 0.001)
            acc.add(_oriented(_strip(E0, E1, closed=False), lambda C, c=pc_: (C - c) * [1, 0, 1]), "bezel_black")
        for i in range(nr):
            z = FL + h0 + 0.040 + i * (h1 - h0 - 0.070) / (nr - 1)
            for j in range(nb):
                x = cx0 + 0.030 + j * (cx1 - cx0 - 0.060) / (nb - 1)
                y = sg * (float(L.hw(x, z)) - 0.006)
                acc.add(cylinder([x, y, z], [x, y - sg * 0.011, z], kr, n=8), "metal_dark")
            zl = z - 0.019
            # lit legend strip following the curved panel face 0.5 mm in front of it (a straight box was buried at
            # one end: fit_check 22b)
            xs_ = np.linspace(cx0 + 0.025, cx1 - 0.025, 8)
            G_ = np.stack([np.stack([xs_, sg * (L.hw(xs_, np.full(8, zz)) - 0.0075), np.full(8, zz)], -1)
                           for zz in (zl - 0.0015, zl + 0.0015)], 1)                # 1.5 mm proud (r3 K3)
            acc.add(_oriented(grid_surface(G_), [0, -sg, 0]), "screen_cyan" if sg < 0 else "screen_green")


# =====================================================================================================================
# overhead panel (+ SAFETY AUTOLAND cup, eyeballs), magnetic compass on the centre post
# =====================================================================================================================
def _overhead(acc):
    acc.group = "overhead"
    L = lining()
    xa, xb = (float(v) for v in OV["x"])
    w, dep = float(OV["w"]), float(OV["depth"])
    xs = np.linspace(xa, xb, 6)
    zc = L.crown(xs, 0.0)
    slope = float(np.polyfit(xs, zc, 1)[0])
    xm = 0.5 * (xa + xb)
    zb = float(L.crown(xm, 0.0)) - dep
    u = _unit([1.0, 0.0, slope])
    f = Fr([xm, 0.0, zb], u, [0, -1.0, 0])                             # w = down (toward the crew)
    hl, hwid = 0.5 * (xb - xa) * math.sqrt(1 + slope ** 2), 0.5 * w        # along the slope: the drawn x extent
    O = rrect_loop(hl, hwid, 0.012, 4)
    top_c = np.array([float(L.crown(xm + a * u[0], abs(b))) for a, b in O]) - (zb + slope * O[:, 0] * u[0]) + 0.004
    side = _strip(f.p(O[:, 0], O[:, 1], 0.0), f.p(O[:, 0], O[:, 1], -np.maximum(top_c, 0.004)))
    acc.add(_oriented(side, lambda C: C - f.o), "panel_grey")
    acc.add(_oriented(f.poly(O, 0.0), f.w), "panel_grey")
    # anthracite face inside a grey frame, chrome bat-handle toggles, the white bus-diagram / section lines and the
    # bright red MASTER POWER guard (Pilatus PRO overhead photo, P1046406; model judging r1 INT-m5: review r1 F6's
    # brushed-silver face with black lines came from the over-exposed AOPA studio shot -- the PRO overhead is dark
    # with white printing)
    acc.add(f.rect(-hl + 0.010, -hwid + 0.010, hl - 0.010, hwid - 0.010, 0.0006), "panel_dark")
    # switch layout (look-up photo, [M]; a = aft, s = starboard from the panel centre): SYSTEM TEST / FUEL PUMPS /
    # ENGINE (port), ELECTRICAL POWER MANAGEMENT (aft centre), MASTER POWER guard (aft stbd), EXTERNAL LIGHTS (fwd),
    # PASSENGER WARNING (fwd stbd)
    P = lambda a, s_, c=0.0: f.p(a, -s_, c)                                                  # noqa: E731
    togg = [(-0.012, -0.205), (-0.012, -0.166), (-0.072, -0.150), (0.060, -0.035), (0.066, 0.039), (0.021, -0.082),
            (0.021, -0.034), (0.021, 0.086), (-0.021, -0.080), (-0.021, -0.034), (-0.021, 0.084), (-0.074, -0.100),
            (-0.074, -0.078), (-0.074, -0.056), (-0.074, -0.033), (-0.074, 0.035), (-0.072, 0.154), (-0.072, 0.190)]
    for a_, s_ in togg:                                   # hex nut + chrome bat handle with a ball end
        acc.add(cylinder(P(a_, s_, 0.0006), P(a_, s_, 0.0045), 0.0045, n=6), "metal_dark")
        acc.add(cylinder(P(a_, s_, 0.004), P(a_ - 0.005, s_, 0.018), 0.0019, n=8), "chrome_trim")
        acc.add(superellipsoid(P(a_ - 0.005, s_, 0.018), (0.0030, 0.0030, 0.0030), (1, 1), 6, 8), "chrome_trim")
    for a_, s_ in ((0.057, -0.220), (0.057, -0.162), (-0.070, -0.177)):                     # FIRE WARN, LAMP, START
        acc.add(box(P(a_, s_, 0.004), (0.018, 0.018, 0.008), R=f.R), "panel_dark")
    acc.add(box(P(-0.070, -0.207, 0.008), (0.030, 0.016, 0.016), R=f.R), "panel_grey")      # RUN lever
    for s_ in (0.057, 0.080):                                                                 # LANDING, PULSE paddles
        acc.add(box(P(-0.076, s_, 0.007), (0.012, 0.014, 0.014), R=f.R), "yoke_white")
    acc.add(box(P(0.055, 0.190, 0.006), (0.050, 0.056, 0.012), R=f.R), "placard_red")        # MASTER POWER guard
    acc.add(box(P(0.055, 0.190, 0.0135), (0.010, 0.030, 0.004), R=f.R), "black")            # its guard lever
    for a0, s0, a1, s1 in ((0.021, -0.233, 0.021, -0.133), (-0.039, -0.233, -0.039, 0.233), (0.088, -0.133,
                           -0.039, -0.133), (-0.039, -0.123, -0.095, -0.123), (-0.039, 0.120, -0.095, 0.120),
                           (0.021, -0.082, 0.021, 0.086), (0.060, -0.058, -0.021, -0.058), (0.066, 0.064,
                           -0.021, 0.064), (-0.021, -0.080, -0.021, 0.084)):
        q = np.array([P(a0, s0, 0.0011), P(a1, s1, 0.0011)])
        dv = _unit(q[1] - q[0])
        sd = 0.0010 * _unit(np.cross(dv, f.w))
        quad = Mesh(np.array([q[0] - sd, q[1] - sd, q[1] + sd, q[0] + sd]), np.array([[0, 1, 2], [0, 2, 3]]))
        acc.add(_oriented(quad, f.w), "light_white")
    # SAFETY AUTOLAND cup + two eyeball outlets aft of the panel
    ax_, ay_, asz = (float(v) for v in OV["autoland"])
    zc_ = float(L.crown(ax_, ay_))
    # a proud square bezel on the headliner with the cup inside it (the lining is not cut: the old cup went 8 mm INTO
    # the headliner, so only a 2 mm ring of it showed -- found by fit_check 22b, review r2 C2 check); w = down
    e_ = 0.004
    dzx = float(L.crown(ax_ + e_, ay_) - L.crown(ax_ - e_, ay_)) / (2 * e_)
    dzy = float(L.crown(ax_, ay_ + e_) - L.crown(ax_, ay_ - e_)) / (2 * e_)
    nd = _unit([dzx, dzy, -1.0])                                      # headliner normal into the cabin
    ux = _unit([1.0, 0.0, dzx])
    fa = Fr(np.array([ax_, ay_, zc_]) + 0.002 * nd, ux, np.cross(nd, ux))   # w = nd: on the local tangent plane
    O2 = rrect_loop(0.5 * asz, 0.5 * asz, 0.012, 4)
    In2 = rrect_loop(0.5 * asz - 0.010, 0.5 * asz - 0.010, 0.006, 4)
    acc.add(_oriented(_strip(fa.p(O2[:, 0], O2[:, 1], -0.004), fa.p(O2[:, 0], O2[:, 1], 0.012)),
                      lambda C: C - fa.o), "panel_grey")
    acc.add(_oriented(_strip(fa.p(O2[:, 0], O2[:, 1], 0.012), fa.p(In2[:, 0], In2[:, 1], 0.012), closed=True),
                      fa.w), "panel_grey")
    acc.add(_oriented(_strip(fa.p(In2[:, 0], In2[:, 1], 0.012), fa.p(In2[:, 0], In2[:, 1], 0.004)),
                      lambda C: fa.o - C), "panel_grey")
    acc.add(_oriented(fa.poly(In2, 0.004), fa.w), "panel_dark")
    acc.add(fa.knob(0, 0, 0.016, 0.006, 20, 0.004), "paint_red")
    acc.add(fa.disk(0, 0, 0.019, 0.0045, 24, r_inner=0.016), "light_red")
    for by in (-0.070, 0.070):
        x = xb + 0.065
        fe = Fr([x, by, float(L.crown(x, by)) - 0.002], [1.0, 0, 0], [0, -1.0, 0])
        acc.add(revolve([(0.0, 0.026), (0.006, 0.024), (0.009, 0.017)], n=20, axis_origin=fe.o, axis_dir=fe.w,
                        ref_dir=fe.u), "panel_grey")
        acc.add(fe.se(0, 0, 0.004, (0.014, 0.014, 0.014), (0.9, 0.9), (8, 12)), "metal_dark")
    # magnetic compass on the windshield centre post (P1046408: ~23 deg above the divider camera; P1046409 / 10)
    from model import fuselage as F
    zc = DETAIL["compass_z"]
    xx = np.linspace(3.25, 4.0, 751)
    xp = float(xx[np.argmin(np.abs(F.z_top(xx) - zc))])
    a = math.atan2(float(F.z_top(xp + 0.01) - F.z_top(xp - 0.01)), 0.02)
    inward = np.array([math.sin(a), 0.0, -math.cos(a)])
    p0 = np.array([xp, 0.0, zc])
    # on the centre-post trim (POST_TRIM, model judging r1 INT-m7): the stem from 0.5 mm inside the trim face, the
    # housing clear of it
    fc = Fr(p0 + (POST_TRIM["d"][1] + 0.052) * inward, [0, 1.0, 0], [0, 0, 1.0])          # w = aft
    acc.add(cylinder(p0 + (POST_TRIM["d"][1] - 0.0005) * inward, fc.o, 0.009, n=10), "black")
    acc.add(fc.se(0, 0, 0, (0.034, 0.036, 0.030), (0.3, 0.3), (8, 14)), "panel_grey")
    acc.add(fc.se(0, 0.004, 0.012, (0.026, 0.022, 0.020), (0.3, 0.3), (6, 12)), "black")
    acc.add(fc.rect(-0.017, -0.004, 0.017, 0.012, 0.0325), "light_white")
    acc.add(fc.rect(-0.0008, -0.004, 0.0008, 0.012, 0.0330), "light_red")
    _post_trim(acc)


POST_TRIM = dict(hw=0.033, d=(0.022, 0.058), n=3.0)   # [M] interior windshield centre-post fairing: half-width, depth
#                                                      from / to inside the OML, section exponent (model judging r1
#                                                      INT-m7: P1046408 / AOPA show a moulded grey post ~65-70 wide
#                                                      from the glareshield to the overhead fairing, the compass on it)


def _post_trim(acc):
    """Moulded lining-grey fairing over the windshield centre post, inside the glass: from the glareshield hood (the
    glass lower edge at BL 0, run 25 mm into the hood) up along the OML crown line to the overhead panel's forward end;
    a rounded-rectangle section POST_TRIM hw x d, closed at both ends."""
    from model import fuselage as F
    hw, (d0, d1), ne = POST_TRIM["hw"], POST_TRIM["d"], POST_TRIM["n"]
    xw, zw = I.ws_lower_edge(0.0)
    xs = np.linspace(xw + 0.010, float(OV["x"][0]) + 0.005, 40)
    zt = F.z_top(xs)
    dz = np.gradient(zt, xs)
    nin = np.stack([dz, np.zeros_like(xs), -np.ones_like(xs)], 1)
    nin /= np.linalg.norm(nin, axis=1, keepdims=True)                 # into the cabin (down / aft)
    Q = np.stack([xs, np.zeros_like(xs), zt], 1)
    Q[0] -= 0.025 * _unit([1.0, 0.0, dz[0]])                           # into the hood
    th = np.linspace(0.0, 2 * np.pi, 28, endpoint=False)
    c, s_ = np.cos(th), np.sin(th)
    u = hw * np.sign(c) * np.abs(c) ** (2.0 / ne)
    vv = 0.5 * (d1 - d0) * np.sign(s_) * np.abs(s_) ** (2.0 / ne)
    dm = 0.5 * (d0 + d1)
    G = np.stack([Q[i] + nin[i] * dm + np.outer(u, [0.0, 1.0, 0.0]) + np.outer(vv, nin[i]) for i in range(len(xs))])
    side = grid_surface(G, close_v=True)
    cen = Q + nin * dm
    side = _oriented(side, lambda C: C - cen[np.argmin(np.linalg.norm(C[:, None] - cen[None], axis=2), 1)])
    acc.add(side, "lining_flightdeck")
    for i, sgn in ((0, -1.0), (-1, 1.0)):
        t = _unit([1.0, 0.0, dz[i]]) * sgn
        acc.add(_oriented(planar_cap(G[i], t), t), "lining_flightdeck")


# =====================================================================================================================
# divider (walnut veneer walls, open aisle), curtain track + stowed bundle, fire extinguisher
# =====================================================================================================================
def _divider(acc):
    from model import seats as S_
    acc.group = "divider"
    L = lining()
    xa = float(DV["x_aft"])
    t = float(DV["t"])
    ob0, ob1 = (float(v) for v in DV["open_bl"])
    S = I.lining_section(xa, n=1441)
    tt = np.linspace(0.0, 1.0, len(S), endpoint=False)
    for sg, edge in ((-1, ob0), (1, ob1)):
        m = (tt > 0.5) if sg < 0 else (tt < 0.5)                      # port: keel -> crown; stbd: crown -> keel
        Q = S[m]
        if sg > 0:
            Q = Q[::-1]
        Q = Q[(Q[:, 1] >= FL) & (sg * Q[:, 0] >= sg * edge)]
        zc = float(L.crown(xa, edge))
        ywall = float(L.hw(xa, FL))
        out = np.vstack([[edge, FL], [sg * ywall, FL], Q, [edge, zc]])
        out[:, 0] -= sg * 0.001
        out[:, 1] = np.clip(out[:, 1], FL, None)
        # well-shaped triangles (grid + Delaunay), the opening-edge strip on the same boundary points: no slivers or
        # T-junction cracks (review r1 C4)
        out = S_._subdivide(S_._ccw(S_._dedup(out)), 0.04)
        tri, Gi = S_._cap(out, 0.06)
        P2 = np.vstack([out, Gi])
        for x, nx in ((xa, 1.0), (xa - t, -1.0)):
            acc.add(_oriented(Mesh(np.c_[np.full(len(P2), x), P2], tri), [nx, 0, 0]), "veneer_walnut")
        on = np.abs(out[:, 0] - (edge - sg * 0.001)) < 1e-6
        E = out[on][np.argsort(out[on][:, 1])]
        E0 = np.c_[np.full(len(E), xa - t), E]
        E1 = np.c_[np.full(len(E), xa), E]
        acc.add(_oriented(_strip(E0, E1, closed=False), [0, -sg, 0]), "veneer_walnut")
        # aft-face placard (pax signs, LH) / sign plate (RH), cabin side
        if sg < 0:
            acc.add(box([xa + 0.0015, 0.5 * (edge - 0.60), FL + 1.02], (0.002, 0.11, 0.035)), "paint_red")
        else:
            acc.add(box([xa + 0.0015, edge + 0.10, FL + 1.20], (0.002, 0.07, 0.035)), "bezel_black")
    # curtain track across the opening at the headliner (fwd face) and the stowed bundle at the stow-side edge
    from model import seats as S_
    x0, x1, y0, y1, zt, xt = I.curtain_bundle()
    ys = np.linspace(ob0 - 0.02, ob1 + 0.02, 30)
    path = np.c_[np.full(30, xt), ys, L.crown(xt, ys) - 0.008]
    prof = np.array([[-0.006, -0.012], [0.006, -0.012], [0.006, 0.012], [-0.006, 0.012]])
    acc.add(sweep_profile(path, prof), "metal")
    # the stowed bundle (flared top at zt) against the divider's forward face, part of it behind the walnut edge
    # (DIVIDER curtain tuck), and above it the gathered band up the forward face to the track, all but a sliver of
    # it behind the edge (interior.curtain_band; review r1 F2)
    b0, b1 = I.curtain_band()
    xg = xt - 0.009
    ycm = 0.5 * (y0 + y1)
    zh = float(L.crown(xt, 0.5 * (b0 + b1))) - 0.015
    na = 48
    zs = np.r_[np.linspace(FL + 0.004, zt, 16), np.linspace(zt + 0.02, zt + 0.10, 5), np.linspace(zt + 0.14, zh, 8)]
    phi = np.linspace(0, 2 * np.pi, na, endpoint=False)
    rings = []
    for z in zs:
        if z <= zt:
            fl = 1.0 + 0.10 * max(0.0, (z - (zt - 0.12)) / 0.12)       # flared top of the bundle
            xc_, hx = 0.5 * (x0 + x1), 0.5 * (x1 - x0) * fl
            yc_, hy = ycm, 0.5 * (y1 - y0) * 1.08
            amp = 0.20
        else:
            k = float(np.clip((z - zt) / 0.10, 0.0, 1.0))
            k = k * k * (3 - 2 * k)
            xl = x0 + (xg - x0) * k
            xc_, hx = 0.5 * (xl + x1), 0.5 * (x1 - xl)
            yc_ = ycm + (0.5 * (b0 + b1) - ycm) * k
            hy = 0.5 * (y1 - y0) * 1.08 + (0.5 * (b1 - b0) - 0.5 * (y1 - y0) * 1.08) * k
            amp = 0.20 * (1.0 - k) + 0.06 * k
        cx_, cy_ = np.cos(phi), np.sin(phi)
        e = 0.35
        rx = np.sign(cx_) * np.abs(cx_) ** e
        ry = np.sign(cy_) * np.abs(cy_) ** e
        # vertical folds, fading out on the side against the divider face, which clips the bundle flat there (a fold
        # clipped flat folded the ring over itself: review r2 N1)
        pleat = 1.0 + amp * np.sin(7 * phi + 0.9 * math.sin(9.0 * z)) * (1.0 - S_.smoothstep(0.2, 0.7, cx_))
        X = np.clip(xc_ + hx * rx * pleat, None, x1 - 0.0005)
        Y = yc_ + hy * ry * pleat
        rings.append(np.c_[X, Y, np.full(na, z)])
    G = np.array(rings)
    ctr = G.mean(1)
    acc.add(_oriented(grid_surface(G, close_v=True),
                      lambda C: np.c_[C[:, 0] - np.interp(C[:, 2], zs, ctr[:, 0]),
                                      C[:, 1] - np.interp(C[:, 2], zs, ctr[:, 1]), np.zeros(len(C))]), "curtain")
    acc.add(_oriented(planar_cap(G[0], [0, 0, -1.0]), [0, 0, -1.0]), "curtain")
    acc.add(_oriented(planar_cap(G[-1], [0, 0, 1.0]), [0, 0, 1.0]), "curtain")
    # fire extinguisher on the fwd face of the RH divider (bottle, valve head, handle, hose, bracket)
    ex, ey, ez, ed, eh = (float(v) for v in DV["extinguisher"])
    r = 0.5 * ed
    zb = FL + ez - 0.5 * eh
    prof = [(0.0, 0.0001), (0.0, r * 0.85), (0.012, r), (eh - 0.045, r), (eh - 0.020, 0.55 * r), (eh - 0.005, 0.30 * r),
            (eh, 0.30 * r)]
    acc.add(revolve(prof, n=24, axis_origin=[ex, ey, zb], axis_dir=[0, 0, 1.0], cap_ends=True), "paint_red")
    acc.add(cylinder([ex, ey, zb + eh], [ex, ey, zb + eh + 0.030], 0.013, n=12), "steel")
    acc.add(box([ex - 0.012, ey, zb + eh + 0.034], (0.075, 0.016, 0.008)), "black")            # handle, on the
    acc.add(box([ex - 0.021, ey, zb + eh + 0.018], (0.020, 0.012, 0.018)), "steel")            # valve / nozzle
    for zz_ in (zb + 0.06, zb + eh - 0.07):
        band_path = np.c_[ex + (r + 0.003) * np.cos(np.linspace(-0.5 * np.pi, 1.5 * np.pi, 25)),
                          ey + (r + 0.003) * np.sin(np.linspace(-0.5 * np.pi, 1.5 * np.pi, 25)), np.full(25, zz_)]
        acc.add(sweep_profile(band_path, np.array([[-0.001, -0.009], [0.001, -0.009], [0.001, 0.009],
                                                   [-0.001, 0.009]]), cap=False), "metal_dark")
    xf = xa - float(DV["t"])
    acc.add(box([xf - 0.003, ey, zb + 0.5 * eh], (0.006, 0.050, eh - 0.04)), "metal_dark")      # bracket plate


# =====================================================================================================================
# assembly
# =====================================================================================================================
def build_flightdeck(groups=False, floor=True):
    """All flight-deck meshes (crew seats excluded: built by the seat builder).  groups=False: [(Mesh, material)],
    one merged mesh per material; groups=True: {group: [(Mesh, material)]} (panel, displays, glareshield, pedestal,
    floor, yokes, pedals, consoles, overhead, divider)."""
    acc = _Acc()
    _panel_face(acc)
    _displays(acc)
    _glareshield(acc)
    _lower_panel(acc)
    _pedestal(acc)
    _plinth_floor(acc, floor)
    _yokes(acc)
    _pedals(acc)
    _consoles(acc)
    _overhead(acc)
    _divider(acc)

    def clean(ms):
        m = Mesh.merge(ms)
        return m.remove_degenerate(1e-11)
    if groups:
        out = defaultdict(list)
        for (g, mat), ms in acc.d.items():
            out[g].append((clean(ms), mat))
        return dict(out)
    by_mat = defaultdict(list)
    for (g, mat), ms in acc.d.items():
        by_mat[mat] += ms
    return [(clean(ms), mat) for mat, ms in by_mat.items()]


def build(parts, ceiling=None):
    """Part 'flight_deck' (drop-in for the rev-A interior.build_flightdeck; the crew seats are added by their own
    builder).  ceiling: a list that takes the 'overhead' group [(Mesh, material)] instead of the part (interior.build
    hangs the overhead panel on the interior_lining part: the viewer's cutaway clips it with the headliner)."""
    from model.parts import Part
    e = I.design_eye(-1)
    p = Part("flight_deck", "Flight deck: Garmin G3000 PRIME panel, PC-24-style yokes, pedestal, divider", "interior",
             explode=(0, 0, 0.0), group="Interior",
             material_note="3 x 14-in PDUs, 2 x 7-in SDUs, GI 275, GFC 700; walnut divider with curtain",
             info={"avionics": "Garmin G3000 PRIME (PC-12 PRO)", "displays": "3 x 14 in + 2 x 7 in",
                   "design eye": f"STA {e[0] * 1000:,.0f} / BL +/-{abs(e[1]) * 1000:.0f} / WL {e[2] * 1000:,.0f} "
                                 f"(L6 design_eye)"})
    by_mat = defaultdict(list)
    pivots = control_pivots()
    kids = defaultdict(list)
    fixed_kids = {"consoles": "fd_consoles", "divider": "fd_divider"}   # own parts: the viewer's cutaway clips each
    fixed = defaultdict(lambda: defaultdict(list))                        # WHOLE piece set (review r3 C1)
    for grp, ms in build_flightdeck(groups=True).items():
        for m, mat in ms:
            if ceiling is not None and grp in ("overhead", "cb_panels"):
                ceiling.append((m, mat))
            elif grp in pivots:
                kids[grp].append((m, mat))
            elif grp in fixed_kids:
                fixed[fixed_kids[grp]][mat].append(m)
            else:
                by_mat[mat].append(m)
    for mat, ms in by_mat.items():
        p.add(Mesh.merge(ms), mat)
    parts[p.id] = p
    names = {"fd_consoles": ("Flight-deck side consoles (cup holders, USB, pocket)", "graphite consoles, grey cup "
                                                                                     "rings"),
             "fd_divider": ("Flight-deck divider: walnut walls and header, curtain, extinguisher", "smoked walnut "
                                                                                                 "veneer, orange "
                                                                                                 "curtain")}
    for pid, bm in fixed.items():
        c = Part(pid, names[pid][0], "interior", parent="flight_deck", group="Interior", material_note=names[pid][1],
                 info={"table": "interior.SIDE_CONSOLE" if pid == "fd_consoles" else "interior.DIVIDER"})
        for mat, ms in bm.items():
            c.add(Mesh.merge(ms), mat)
        parts[pid] = c
    # the yokes and rudder pedals: child parts with pivots, so the viewer's roll / pitch / yaw commands move them
    for pid, ms in kids.items():
        pv = pivots[pid]
        yoke = pid.startswith("yoke")
        side = "pilot" if pid[len("yoke_" if yoke else "pedal_")] == "L" else "co-pilot"
        name = (f"Control yoke, {side} (PC-24 style)" if yoke else
                f"Rudder pedal, {side}, {'left' if pid.endswith('L') else 'right'} foot (toe brake)")
        c = Part(pid, name, "interior", parent="flight_deck", pivot=pv, group="Interior",
                 material_note="white hub, leather-grained grips" if yoke else "anti-slip pad on a floor-hinged arm",
                 info={"moves": (f"roll +/-{pv['roll_deg']:.0f} deg about the column, pitch "
                                 f"{pv['travel_push'][0] * 1000:+.0f} / {pv['travel_pull'][0] * 1000:+.0f} mm") if yoke
                       else f"+/-{pv['travel_deg']:.1f} deg about the floor hinge ({I.PEDALS['travel'] * 1000:.0f} mm "
                            f"at the pad)"})
        for m, mat in ms:
            c.add(m, mat)
        parts[pid] = c
    return p
