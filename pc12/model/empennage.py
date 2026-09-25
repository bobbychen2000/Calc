"""
PC-12 T-tail: swept fin with dorsal fin, rudder with trim tab, trimmable (variable-incidence) tailplane
with paired elevators and horn-balanced tips, fin/tailplane bullet fairing, and twin ventral strakes.

Stage 2 (rev B): positions and planforms from the Pilatus NGX model drawing 190.10.40.432 (side view,
plan, front view and the fin / tailplane sections VF1 WL 2609, VF2 WL 3919, HF1 BL 0, HF2 BL 2270):
  fin        straight LE 40.3 deg (through the VF1 / VF2 leading edges, meeting the crown at FR40),
             rudder TE 22.2 deg from the tail-cone closure (STA 13,568 WL 1,912) to the bullet; NACA 0018
             (VF1 17.8 %, VF2 17.9 %); rudder nose at 63.7 % chord, hinge (nose-circle centre) 69.7 %;
             sloped rudder edges: bottom along the ventral edge, top 3,854 -> 3,772 (RUD_TOP_EDGE)
  dorsal     straight top edge from the crown at FR33 (STA 9,000 WL 2,770) rising 0.134 m/m, blended
             into the fin LE at WL ~3,400; max half-width 114 mm (FR38 / FR40 sections)
  tailplane  chord plane WL 4,099 (zero dihedral, zero incidence as drawn), LE x = 13.0696 + 0.1267 y,
             TE x = 14.3996 - 0.0542 y, elevator hinge at a constant STA 14,000 (= 70 % chord), fixed
             tip rib BL 2,270, horn balance BL 2,270 - 2,600; NACA 0012 root -> 0009 tip (HF1 / HF2)
  bullet     STA 12,606 - 14,790 (drawn end 14,811, 21 mm aft: the official 14.40 m length wins),
             elliptic sections, WL 3,917 - 4,261, 289 mm wide
  strakes    root line STA 9,750 WL 1,365 -> STA 12,190 WL 1,955 on the tail-cone side, tip line
             STA 9,790 WL 1,335 -> STA 11,870 WL 1,530, canted 11 deg (tip outboard; FR38 / FR40)
Anchors: tailplane span 5.20 m (Pilatus), overall height 4.26 m (top of bullet), overall length 14.40 m
(spinner tip STA 0.39 -> aft-most point STA 14.79).
"""
from __future__ import annotations
import numpy as np

from cad.mesh import Mesh, grid_surface, planar_cap, revolve, cap_ring, trim
from model.airfoil import Airfoil, naca00, naca4_thickness
from model.lifting import Section, skin, strip, curve_patch, closed_body, cos_pts
from model.wing import plain_cove, plain_surface_loop, x_end_of_plain, span_stations
from model.parts import Part
from model import fuselage as F

# ---------------------------------------------------------------- fin
FIN_Z0, FIN_Z1 = 1.76, 4.05            # root (buried in the tail cone, ventral below it) / tip (in the bullet)
FIN_LE = ((11.868, 2.609), (12.978, 3.919))     # straight LE through the VF1 / VF2 leading edges
FIN_TE = ((13.568, 1.912), (14.386, 3.919))     # rudder trailing edge
# lower edge of the exposed ventral part of the fin and of the rudder below the tail cone (side view, from the
# strake's aft end to the lower rudder TE corner); the fin root sections run down to FIN_Z0 and Stage 3 trims
# them (and models the ventral fairing, FR40) to this line
VENTRAL_EDGE = ((11.950, 1.645), (13.568, 1.912))
RUD_XH = 0.697                          # hinge at 69.7 % local chord (rudder nose-circle centre)
RUD_NOSE_XC = RUD_XH - 0.05             # visible rudder nose / gap line drawn on the sheets (chord fraction)
RUD_TAB = (2.55, 3.60, 0.940)           # rudder trim tab: WL range and hinge chord fraction
# Rudder top and bottom edges (side view of the drawing), both SLOPED: the bottom edge runs along VENTRAL_EDGE from
# the rudder nose (drawn STA 12,654 WL 1,759) to the lower TE corner (13,568 / 1,912); the top edge falls from the
# rudder nose (13,837 / 3,854) to WL 3,802 at STA 13,935 and on to the TE line at (14,326 / 3,772).  The fixed fin
# tip between the top edge and the bullet runs aft to the TE line.  (Rev B.0 used horizontal edges at WL 1,800 /
# 3,820: the lower aft rudder corner hung 104 mm below the tail-cone / ventral edge.)
RUD_TOP_EDGE = ((13.837, 3.854), (13.935, 3.802), (14.326, 3.772))
FIN_AF_ROOT, FIN_AF_TIP = naca00(0.18), naca00(0.18)


def _lin(p, q, z):
    return p[0] + (q[0] - p[0]) * (z - p[1]) / (q[1] - p[1])


def fin_le(z):
    return _lin(*FIN_LE, z)


def fin_te(z):
    return _lin(*FIN_TE, z)


def rudder_bottom_z(x):
    """WL of the rudder's (sloped) bottom edge at station x = the ventral edge line."""
    (x0, z0), (x1, z1) = VENTRAL_EDGE
    return z0 + (z1 - z0) * (np.asarray(x, float) - x0) / (x1 - x0)


def rudder_top_z(x):
    """WL of the rudder's (sloped) top edge at station x (RUD_TOP_EDGE, extended linearly at both ends)."""
    T = np.array(RUD_TOP_EDGE)
    x = np.asarray(x, float)
    z = np.interp(x, T[:, 0], T[:, 1])
    z = np.where(x < T[0, 0], T[0, 1] + (T[1, 1] - T[0, 1]) / (T[1, 0] - T[0, 0]) * (x - T[0, 0]), z)
    return np.where(x > T[-1, 0], T[-1, 1] + (T[-1, 1] - T[-2, 1]) / (T[-1, 0] - T[-2, 0]) * (x - T[-1, 0]), z)


def fin_chord_x(xc, z):
    """Station of chord fraction xc of the fin section at WL z."""
    return fin_le(z) + xc * (fin_te(z) - fin_le(z))


def rudder_edge_point(xc, edge):
    """(x, z) where the chord-fraction line xc (e.g. RUD_XH = hinge, RUD_NOSE_XC = nose, 1.0 = TE) meets the rudder's
    'bottom' or 'top' edge."""
    f = rudder_bottom_z if edge == "bottom" else rudder_top_z
    z = 1.8 if edge == "bottom" else 3.8
    for _ in range(30):                     # fixed point: the edges are shallow, the chord lines steep
        z = float(f(fin_chord_x(xc, z)))
    return float(fin_chord_x(xc, z)), z


def rudder_outline(n=24):
    """Closed side-view outline (x, z) of the rudder: nose line (bottom -> top), sloped top edge, trailing edge,
    sloped bottom edge (parameters above)."""
    nb, nt = rudder_edge_point(RUD_NOSE_XC, "bottom"), rudder_edge_point(RUD_NOSE_XC, "top")
    tb, tt = rudder_edge_point(1.0, "bottom"), rudder_edge_point(1.0, "top")
    xt = np.linspace(nt[0], tt[0], n)
    xb = np.linspace(tb[0], nb[0], n)
    return np.vstack([[nb], np.c_[xt, rudder_top_z(xt)], np.c_[xb, rudder_bottom_z(xb)]])


# derived (rev B.0 names kept for the 3-D build): the edge WLs where the hinge line meets the sloped edges.  Stage 3
# trims the rudder / fin skins to rudder_bottom_z / rudder_top_z instead of these horizontal cuts.
RUD_Z = (round(rudder_edge_point(RUD_XH, "bottom")[1], 4), round(rudder_edge_point(RUD_XH, "top")[1], 4))


def fin_section(z):
    xl = fin_le(z)
    xt = fin_te(z)
    w = np.clip((z - FIN_Z0) / (FIN_Z1 - FIN_Z0), 0, 1)
    af = FIN_AF_ROOT.blend(FIN_AF_TIP, w)
    return Section(le=np.array([xl, 0.0, z]), chord=xt - xl, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=af)


# ---------------------------------------------------------------- tailplane
STAB_Z = 4.099                         # chord plane WL (front view / HF1 / HF2)
STAB_ROOT_LE = 13.0696                 # leading edge at BL 0
STAB_ROOT_C = 1.330                    # chord at BL 0
STAB_SWEEP = np.arctan(0.1267)         # leading edge 7.2 deg
STAB_TE_SLOPE = -0.0542                # trailing edge dx/dy (slightly forward-swept)
STAB_TIP_Y = 2.60                      # 5.20 m span
STAB_TIP_RIB = 2.27                    # fixed-stabiliser tip rib (HF2); horn balance outboard
STAB_TAPER_C = STAB_ROOT_C + (STAB_TE_SLOPE - np.tan(STAB_SWEEP)) * STAB_TIP_RIB   # chord at the tip rib
ELEV_Y = (0.120, 2.270)
ELEV_HORN = (2.270, 2.600, 13.650)     # horn balance: BL range, its leading-edge (front-face) station
# Tip planform (plan view of the drawing): two parallel raked edges, dx/dy = STAB_TIP_RAKE -- the fixed tip's LE from
# the kink on the straight LE (BL ~2350) to the horn gap, and the horn balance's LE to the tip at (STA 14000,
# BL 2600); the horn's front face (ELEV_HORN[2]) sits behind the fixed tip's aft edge (STAB_HORN_GAP) with a
# rounded corner; the tip edge is raked from (14000, 2600) to the trailing-edge corner at BL 2575.
STAB_TIP_RAKE = 2.078                  # dx/dy of both raked edges
STAB_FIXED_TIP_LE = (13.470, 2.400)    # a point on the fixed tip's raked LE (STA, BL)
STAB_HORN_LE = (13.740, 2.480)         # a point on the horn's raked LE (STA, BL)
STAB_HORN_GAP = ((13.608, 2.270), (13.623, 2.474))   # fixed tip's aft edge (ahead of the horn), BL 2270 -> corner
STAB_HORN_CORNER = (2.430, 0.020)      # horn front face runs to BL 2430, then a radius into the raked LE
STAB_TIP_TE = (14.260, 2.575)          # trailing-edge corner of the raked tip edge
ELEV_XH = 0.70                         # hinge (= constant STA 14,000 with these LE / TE lines)
STAB_INC = np.radians(0.0)
STAB_AF_ROOT, STAB_AF_TIP = naca00(0.12), naca00(0.09)
STAB_AF = STAB_AF_ROOT


def _stab_le_lin(y):
    return STAB_ROOT_LE + abs(y) * np.tan(STAB_SWEEP)


def _fixed_tip_le(y):
    return STAB_FIXED_TIP_LE[0] + STAB_TIP_RAKE * (y - STAB_FIXED_TIP_LE[1])


def _horn_le(y):
    return STAB_HORN_LE[0] + STAB_TIP_RAKE * (y - STAB_HORN_LE[1])


STAB_TIP_KINK_Y = float((STAB_FIXED_TIP_LE[0] - STAB_TIP_RAKE * STAB_FIXED_TIP_LE[1] - STAB_ROOT_LE)
                        / (np.tan(STAB_SWEEP) - STAB_TIP_RAKE))         # straight LE meets the fixed-tip rake
STAB_NOTCH_Y = STAB_HORN_GAP[1][1]                                    # fixed tip ends; the horn LE takes over


def stab_le(y):
    """Leading edge = outer envelope in plan (parameters above): straight LE to the kink at BL STAB_TIP_KINK_Y,
    the fixed tip's raked edge to the horn gap at BL STAB_NOTCH_Y, then the horn balance's raked LE to the tip
    (STA ~14000 at BL 2600).  The notch at the horn gap is a 4 mm ramp (the loft samples it; stab_tip_outline()
    gives the exact plan outline for the drawings)."""
    y = abs(float(y)) if np.ndim(y) == 0 else np.abs(np.asarray(y, float))
    lin = _stab_le_lin(y)
    fixed = np.maximum(lin, _fixed_tip_le(y))
    horn = np.maximum(lin, _horn_le(y))
    w = np.clip((y - STAB_NOTCH_Y) / 0.004, 0, 1)
    out = np.where(y <= STAB_TIP_KINK_Y, lin, fixed * (1 - w) + horn * w)
    return float(out) if np.ndim(out) == 0 else out


def stab_te(y):
    """Trailing edge (plan): straight, slightly forward-swept line; outboard of the TE corner (BL 2575) the raked
    tip edge to (STA 14000, BL 2600)."""
    y = abs(float(y)) if np.ndim(y) == 0 else np.abs(np.asarray(y, float))
    te = STAB_ROOT_LE + STAB_ROOT_C + y * STAB_TE_SLOPE
    x_tip_le = float(_horn_le(STAB_TIP_Y))
    tip = STAB_TIP_TE[0] + (x_tip_le - STAB_TIP_TE[0]) * (y - STAB_TIP_TE[1]) / (STAB_TIP_Y - STAB_TIP_TE[1])
    out = np.where(y <= STAB_TIP_TE[1], te, np.minimum(te, tip))
    return float(out) if np.ndim(out) == 0 else out


def stab_tip_outline():
    """Plan-view outline pieces of the starboard tailplane tip (x, y) from the parameters above, for the drawings:
    'outer' = the outer envelope from the LE kink round the tip to the TE corner (with the notch at the horn gap),
    'gap_fixed' = the fixed tip's aft edge, 'horn_front' = the horn's front face with its rounded corner,
    'horn_root' = the horn's inboard edge at BL ELEV_HORN[0] (front face -> elevator gap line)."""
    yk, yn = STAB_TIP_KINK_Y, STAB_NOTCH_Y
    xg1 = STAB_HORN_GAP[1][0]
    yc, rc = STAB_HORN_CORNER
    xh = ELEV_HORN[2]
    # horn front face -> rounded corner -> raked LE
    a = np.linspace(np.pi, np.pi / 2 + np.arctan(1 / STAB_TIP_RAKE), 8)
    yhc = yc                                                # corner centre BL
    xhc = xh + rc
    corner = np.c_[xhc + rc * np.cos(a), yhc + rc * np.sin(a)]
    y_join = float(corner[-1, 1])
    horn_le = np.array([[float(_horn_le(y_join)), y_join], [float(_horn_le(STAB_TIP_Y)), STAB_TIP_Y]])
    outer = np.vstack([[[float(_stab_le_lin(yk)), yk]], [[float(_fixed_tip_le(yn)), yn]], [[xg1, yn]]])
    horn = np.vstack([[[xh, ELEV_HORN[0] + 0.006]], corner, horn_le[1:]])
    tip = np.array([[float(_horn_le(STAB_TIP_Y)), STAB_TIP_Y], list(STAB_TIP_TE)])
    return dict(outer=outer, horn_front=horn, tip=tip,
                gap_fixed=np.array(STAB_HORN_GAP),
                horn_root=np.array([[xh, ELEV_HORN[0] + 0.006], [float(stab_te(ELEV_HORN[0])), ELEV_HORN[0] + 0.006]]))


def stab_plan_polygon(n_root=40):
    """Closed plan outline (x, y) of the starboard tailplane incl. the horn balance, from BL 0 along the LE, round
    the tip (fixed-tip rake, horn-gap notch, horn LE, raked tip edge) and back along the TE (parameters only)."""
    t = stab_tip_outline()
    yk = STAB_TIP_KINK_Y
    ys = np.linspace(0.0, yk, n_root)
    le = np.c_[_stab_le_lin(ys), ys]
    o = t["outer"]                                  # kink -> fixed-tip corner -> gap corner
    gap = np.asarray(STAB_HORN_GAP)
    y_r = ELEV_HORN[0] + 0.006                      # the horn's inboard edge
    g_lo = gap[1] + (gap[0] - gap[1]) * (gap[1][1] - y_r) / (gap[1][1] - gap[0][1])
    horn = t["horn_front"]
    notch = np.vstack([g_lo[None], horn])           # the horn gap slot: down the fixed tip's aft edge, across,
    #                                                 up the horn's front face, round its corner, out along its LE
    tip = t["tip"][1:]
    yt = np.linspace(STAB_TIP_TE[1], 0.0, n_root)
    te = np.c_[STAB_ROOT_LE + STAB_ROOT_C + yt * STAB_TE_SLOPE, yt]
    return np.vstack([le, o[1:], notch, tip, te])


def stab_section(y):
    xl, xt = stab_le(y), stab_te(y)
    c = max(xt - xl, 0.02)
    af = STAB_AF_ROOT.blend(STAB_AF_TIP, float(np.clip(abs(y) / STAB_TIP_RIB, 0, 1)))
    return Section(le=np.array([xl, y, STAB_Z]), chord=c, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 0, 1.0]), twist=STAB_INC, airfoil=af)


def horn_gap_x(y):
    """STA of the fixed tip's aft edge (the drawn horn-gap line STAB_HORN_GAP, extended linearly) at BL |y|."""
    (x0, y0), (x1, y1) = STAB_HORN_GAP
    return x0 + (x1 - x0) * (np.abs(np.asarray(y, float)) - y0) / (y1 - y0)


def horn_front_x(y):
    """STA of the horn balance's front face at BL |y|: flat at ELEV_HORN[2], the rounded corner STAB_HORN_CORNER,
    then the horn's raked leading edge."""
    y = np.abs(np.asarray(y, float))
    yc, rc = STAB_HORN_CORNER
    xh = ELEV_HORN[2]
    corner = xh + rc - np.sqrt(np.clip(rc * rc - (y - yc) ** 2, 0.0, None))
    return np.where(y <= yc, xh, np.maximum(np.where(y <= yc + rc, corner, xh + rc), _horn_le(y)))


def _cut_face_loop(sec, xc0, xc1=None, n=16):
    """Chord-unit loop of the section between chord fractions xc0 and xc1 (default the TE): upper surface aft,
    lower surface forward, closed by flat faces."""
    af = sec.airfoil
    xc1 = 1.0 if xc1 is None else xc1
    xu = cos_pts(n, 0, 1) * (xc1 - xc0) + xc0
    up = np.stack([xu, af.upper(xu)], 1)
    lo = np.stack([xu[::-1], af.lower(xu[::-1])], 1)
    return np.vstack([up, lo[1:-1]]) if xc1 >= 1.0 - 1e-9 else np.vstack([up, lo])


def horn_loop(sec):
    """Horn-balance section loop: the section aft of its front face (horn_front_x) with a flat front."""
    y = abs(float(sec.le[1]))
    xc0 = float(np.clip((float(horn_front_x(y)) - sec.le[0]) / sec.chord, 0.0, 0.98))
    return _cut_face_loop(sec, xc0)


# ---------------------------------------------------------------- dorsal fin
DORSAL_X0, DORSAL_Z0 = 9.000, 2.770    # starts on the crown at FR33
DORSAL_SLOPE = 0.1338                  # straight top edge dz/dx
DORSAL_KNEE_X = 12.20                  # end of the straight edge; quadratic blend into the fin LE
DORSAL_HW = 0.114                      # max half-width (FR38 / FR40)
DORSAL_RAMP = 3.2                      # m behind the edge to full width (FR36: 74 mm at 0.75 m)
DORSAL_ZTOP = 3.40                     # the blend meets the fin LE here (approx.)


def _dorsal_curve(n=24):
    """Side-view top edge of the dorsal fin as (x, z) points: straight edge, then a quadratic Bezier tangent
    to the edge and to the fin LE line."""
    k = np.array([DORSAL_KNEE_X, DORSAL_Z0 + DORSAL_SLOPE * (DORSAL_KNEE_X - DORSAL_X0)])
    # corner C = intersection of the edge line with the fin LE line
    (x1, z1), (x2, z2) = FIN_LE
    g = (x2 - x1) / (z2 - z1)                          # fin LE dx/dz
    # z = z0 + s (x - x0)  and  x = x1 + g (z - z1)
    zc = (DORSAL_Z0 + DORSAL_SLOPE * (x1 - g * z1 - DORSAL_X0)) / (1 - DORSAL_SLOPE * g)
    c = np.array([x1 + g * (zc - z1), zc])
    d = np.linalg.norm(c - k)
    u = np.array([g, 1.0]) / np.hypot(g, 1.0)
    f = c + d * u
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * k + 2 * t * (1 - t) * c + t ** 2 * f


def dorsal_edge_x(z):
    """Station of the dorsal fin's top edge at water line z."""
    cur = _dorsal_curve(64)
    zk = cur[0, 1]
    if z <= zk:
        return DORSAL_X0 + (z - DORSAL_Z0) / DORSAL_SLOPE
    if z >= cur[-1, 1]:
        return fin_le(z)
    return float(np.interp(z, cur[:, 1], cur[:, 0]))


# Dorsal / fin ROOT FILLET (Stage 2 rev C, review round 3, G3-2).  The Pilatus drawing's plan view draws the dorsal's
# root as a closed outline on the tail cone, about twice as wide as the dorsal slab (half-width 72 mm at STA 9250,
# 170 at 10000, 222 at 11000, 252 at 12200), and its side view draws the matching line exactly at z_at(x, that
# half-width) -- an edge on the skin: the foot of a broad fillet that fairs the dorsal (and, aft of the dorsal / fin
# seam, the fin root) into the tail cone.  The top-view photos (unk_top_front_pilatus, unk_top_corsica_pilatus) show
# the same V-shaped, widening root.  The drawing's frame sections FR36-FR40 draw the slab only (114 mm half-width,
# no fillet); the slab (DORSAL_HW) is kept and the fillet is the low concave flank from the slab side down to this
# foot line.  Table: (STA, half-width of the foot on the OML); round nose at STA 9.023; from the seam (DORSAL_SEAM)
# aft the foot follows the drawn side-view line (skin half-width side_y(x, z_drawn)) to the rudder nose at STA ~13.0.
DORSAL_FILLET = ((9.023, 0.000), (9.030, 0.025), (9.050, 0.038), (9.100, 0.047), (9.200, 0.064), (9.400, 0.095),
                 (9.600, 0.123), (9.800, 0.148), (10.000, 0.170), (10.200, 0.187), (10.500, 0.206), (10.800, 0.218),
                 (11.200, 0.225), (11.600, 0.231), (12.000, 0.246), (12.200, 0.252), (12.373, 0.249), (12.500, 0.238),
                 (12.600, 0.222), (12.700, 0.202), (12.800, 0.180), (12.900, 0.157), (13.000, 0.134))
# the fillet flank meets the slab / fin side this far above the crown: aft of the seam the drawing shows that upper
# edge of the fin-root fairing as a line from the seam (STA 12410 WL 2615) to the rudder nose (13080 / 2505), i.e.
# 55-65 mm above our crown
DORSAL_FILLET_RISE = 0.060
DORSAL_SEAM_X0 = 12.373         # dorsal / fin panel seam: from the fillet foot here up to the dorsal-curve end


def dorsal_fillet_hw(x):
    """Half-width of the dorsal / fin root-fillet foot on the OML at station(s) x (0 outside the table)."""
    from cad.mesh import pchip
    T = np.array(DORSAL_FILLET)
    x = np.asarray(x, float)
    w = pchip(T[:, 0], T[:, 1])(np.clip(x, T[0, 0], T[-1, 0]))
    return np.where((x >= T[0, 0]) & (x <= T[-1, 0]), np.maximum(w, 0.0), 0.0)


def dorsal_root_line(n=200):
    """Side-view line (x, z) of the fillet foot: z_at(x, dorsal_fillet_hw(x)) from the nose to the rudder nose."""
    T = np.array(DORSAL_FILLET)
    xs = np.linspace(T[0, 0], T[-1, 0], n)
    return np.c_[xs, F.z_at(xs, dorsal_fillet_hw(xs))]


def dorsal_seam():
    """Dorsal / fin seam (2, 2) (x, z): from the fillet foot at DORSAL_SEAM_X0 to the end of the dorsal top curve."""
    x0 = DORSAL_SEAM_X0
    return np.array([[x0, float(F.z_at(x0, dorsal_fillet_hw(x0)))], list(_dorsal_curve()[-1])])


def fin_fairing_edge(n=60):
    """Side-view upper edge (x, z) of the fin-root fairing aft of the dorsal / fin seam: WL z_top(x) + RISE from the
    seam to the rudder nose line (chord fraction RUD_NOSE_XC)."""
    sm = dorsal_seam()
    z_of = lambda x: F.z_top(x) + DORSAL_FILLET_RISE                                   # noqa: E731
    x0 = sm[0, 0]
    for _ in range(40):                                  # where the seam line reaches the edge WL
        x0 = sm[0, 0] + (float(z_of(x0)) - sm[0, 1]) * (sm[1, 0] - sm[0, 0]) / (sm[1, 1] - sm[0, 1])
    x1 = 13.0
    for _ in range(40):                                  # where the rudder nose line reaches it
        x1 = float(fin_chord_x(RUD_NOSE_XC, float(z_of(x1))))
    xs = np.linspace(x0, x1, n)
    return np.c_[xs, z_of(xs)]


def dorsal_body_hw(x, z):
    """Half-width of the dorsal slab or the fin (whichever is wider) at station x, WL z (0 outside both)."""
    w = 0.0
    if z <= _dorsal_curve()[-1, 1] + 0.05:
        s = dorsal_section(z)
        xc = (x - s.le[0]) / s.chord
        if 0.0 <= xc <= 1.0:
            w = max(w, float(s.chord * s.airfoil.upper(np.array(xc))))
    s = fin_section(z)
    xc = (x - s.le[0]) / s.chord
    if 0.0 <= xc <= 1.0:
        w = max(w, float(0.5 * s.chord * s.airfoil.thickness(np.array(xc))))
    return w


def dorsal_fillet_section(x, n=16):
    """Starboard fillet flank (n, 2) (y, z) at station x, from the foot on the OML (tangent to the skin) up to the slab /
    fin side at WL z_top(x) + DORSAL_FILLET_RISE (tangent to vertical): quadratic Bezier (Stage 3 lofts it)."""
    yf = float(dorsal_fillet_hw(x))
    if yf <= 0.0:
        return np.zeros((0, 2))
    zf = float(F.z_at(x, yf))
    zt = float(F.z_top(x)) + DORSAL_FILLET_RISE
    ys = min(dorsal_body_hw(x, zt), 0.95 * yf)
    e = 1e-3
    slope = (float(F.z_at(x, yf + e)) - float(F.z_at(x, yf - e))) / (2 * e)          # dz/dy of the skin at the foot
    c = np.array([ys, zf + slope * (ys - yf)])                                         # skin tangent meets y = ys
    c[1] = min(max(c[1], zf), zt)
    t = np.linspace(0.0, 1.0, n)[:, None]
    return (1 - t) ** 2 * np.array([yf, zf]) + 2 * t * (1 - t) * c + t ** 2 * np.array([ys, zt])


def dorsal_section(z):
    x_start = dorsal_edge_x(z)
    x_end = fin_le(z) + 0.45
    c = max(x_end - x_start, 0.05)

    def half(xc, c=c):
        u = np.clip(np.asarray(xc, float) * c / DORSAL_RAMP, 0, 1)
        return DORSAL_HW / c * np.sqrt(np.clip(1 - (1 - u) ** 2, 0, 1)) * np.clip((1 - np.asarray(xc, float)) / 0.05, 0, 1) ** 0.5

    af = Airfoil("dorsal", half, lambda x: 0.0 * np.asarray(x, float))
    return Section(le=np.array([x_start, 0.0, z]), chord=c, e_c=np.array([1.0, 0, 0]),
                   e_t=np.array([0, 1.0, 0]), twist=0.0, airfoil=af)


# ---------------------------------------------------------------- bullet fairing (side view + plan of the drawing)
# station, top WL, bottom WL, half-width (aft of STA 13.5 compressed so the end is STA 14.790, drawn 14.811)
BULLET = ((12.606, 4.099, 4.099, 0.000), (12.650, 4.150, 4.048, 0.040), (12.700, 4.174, 4.022, 0.056),
          (12.800, 4.207, 3.984, 0.083), (12.900, 4.229, 3.958, 0.104), (13.000, 4.244, 3.939, 0.119),
          (13.100, 4.254, 3.926, 0.130), (13.200, 4.259, 3.919, 0.139), (13.300, 4.260, 3.917, 0.142),
          (13.400, 4.257, 3.920, 0.144), (13.500, 4.246, 3.927, 0.138), (13.600, 4.244, 3.929, 0.132),
          (13.800, 4.240, 3.938, 0.121), (14.000, 4.236, 3.951, 0.110), (14.200, 4.232, 3.970, 0.107),
          (14.400, 4.228, 4.000, 0.092), (14.500, 4.222, 4.019, 0.080), (14.600, 4.213, 4.039, 0.064),
          (14.700, 4.201, 4.062, 0.046), (14.790, 4.186, 4.090, 0.020))
BULLET_X = (BULLET[0][0], BULLET[-1][0])
BULLET_EXP = 2.3                       # section super-ellipse exponent


def bullet_section(x, n=48):
    """Bullet cross-section at station x (closed ring, n points)."""
    T = np.array(BULLET)
    zt, zb, w = (np.interp(x, T[:, 0], T[:, k]) for k in (1, 2, 3))
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    zc, hz = 0.5 * (zt + zb), 0.5 * (zt - zb)
    y = w * np.sign(np.sin(a)) * np.abs(np.sin(a)) ** (2 / BULLET_EXP)
    z = zc + hz * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** (2 / BULLET_EXP)
    return np.stack([np.full(n, x), y, z], 1)


# ---------------------------------------------------------------- ventral strakes (side view, FR38 / FR40)
STRAKE_ROOT = ((9.750, 1.365), (12.190, 1.955))   # attachment line on the tail-cone side (x, z)
STRAKE_TIP = ((9.790, 1.335), (11.870, 1.530))    # lower (tip) edge; aft edge from its end to the root end
STRAKE_CANT = np.radians(11.0)                      # from vertical, tip outboard
STRAKE_T = 0.022                                    # plate thickness


def strake_frame(x):
    """(root point, tip point) of the starboard strake in the cross-section at station x (None outside)."""
    (r0x, r0z), (r1x, r1z) = STRAKE_ROOT
    (t0x, t0z), (t1x, t1z) = STRAKE_TIP
    if x < r0x or x > r1x:
        return None
    zr = r0z + (r1z - r0z) * (x - r0x) / (r1x - r0x)
    if x <= t1x:
        zt = t0z + (t1z - t0z) * np.clip((x - t0x) / (t1x - t0x), 0, 1)
        zt = min(zt, zr)
    else:                                            # aft edge: straight from the tip end to the root end
        zt = t1z + (r1z - t1z) * (x - t1x) / (r1x - t1x)
    yr = float(F.side_y(x, zr))
    depth = (zr - zt) / np.cos(STRAKE_CANT)
    return np.array([x, yr, zr]), np.array([x, yr + depth * np.sin(STRAKE_CANT), zt])


# ---------------------------------------------------------------- tail-cone closure, fin / rudder trims (Stage 3)
# The tail cone (fuselage OML, drawn to STA 13.57) lies inside the rudder / fin aft of the rudder leading edge (sheet
# L1 note): it is cut along a plane through the fin chord line TAIL_CUT_XC (normal to the plane of symmetry, parallel
# to the hinge line) just ahead of the fixed cove, and closed there by a flat bulkhead fairing.  The single-piece rudder
# runs from its sloped top edge down to the ventral edge behind that cut, so it clears the fixed structure at any
# deflection.  Below the tail cone the fixed part is a thin ventral fairing (FR40) from the strake end to the cut.
RUD_COVE_GAP = 0.010                     # fixed cove radius over the rudder nose (chord units, wing.plain_cove)
TAIL_CUT_XC = round(RUD_XH - 0.5 * float(FIN_AF_ROOT.thickness(RUD_XH)) - RUD_COVE_GAP - 0.010, 4)   # 0.6216
RUD_EDGE_GAP = 0.010                     # m: rudder top edge / fin tip gap, each side of the drawn line
VENTRAL_T = 0.020                        # ventral fairing half-thickness (m)
VENTRAL_X0 = 11.80                       # ventral fairing leading edge meets the keel (hidden behind the strake)


def _cut_line():
    """(a, b): the tail cut line x = a + b z (side view) = fin chord-fraction line TAIL_CUT_XC."""
    z0, z1 = 1.5, 3.0
    x0, x1 = fin_chord_x(TAIL_CUT_XC, z0), fin_chord_x(TAIL_CUT_XC, z1)
    b = (x1 - x0) / (z1 - z0)
    return x0 - b * z0, b


def tail_cut_x(z):
    a, b = _cut_line()
    return a + b * np.asarray(z, float)


def tail_cut_field(x, z):
    """Signed distance (m) to the tail-cut plane: > 0 aft of it (the tail cone is removed there)."""
    a, b = _cut_line()
    return (np.asarray(x, float) - a - b * np.asarray(z, float)) / np.hypot(1.0, b)


def tail_cut_normal():
    a, b = _cut_line()
    n = np.array([1.0, 0.0, -b])
    return n / np.linalg.norm(n)


def _cut_z_range():
    """WLs where the cut plane meets the keel and the crown of the tail cone."""
    zs = np.linspace(1.6, 2.8, 2401)
    xs = np.clip(tail_cut_x(zs), F.STA["cowl_front"], F.STA["tail_end"])
    zb = zs[np.argmin(np.abs(F.z_bot(xs) - zs))]
    zt = zs[np.argmin(np.abs(F.z_top(xs) - zs))]
    return float(zb), float(zt)


def oml_field(V):
    """Approximate signed distance (m, + outside) of points V to the fuselage OML; + beyond the loft range."""
    x = V[:, 0]
    xc = np.clip(x, F.STA["cowl_front"], F.STA["tail_end"])
    d = F._OML.section_distance(xc, V[:, 1], V[:, 2])
    return np.where((x < F.STA["cowl_front"]) | (x > F.STA["tail_end"]), 1.0, d)


def tail_closure(step=0.004):
    """Flat bulkhead fairing closing the tail cone in the cut plane (both halves, normal aft)."""
    from cad.mesh import grid_surface as _gs, trim as _trim
    zb, zt = _cut_z_range()
    zs = np.linspace(zb - 0.01, zt + 0.01, int((zt - zb + 0.02) / step) + 2)
    ys = np.linspace(0.0, 0.30, int(0.30 / step) + 2)
    Z, Y = np.meshgrid(zs, ys, indexing="ij")
    X = tail_cut_x(Z)
    P = np.stack([X, Y, Z], -1)
    out = []
    for sgn in (1, -1):
        m = _gs(P * [1, sgn, 1])
        f = np.abs(m.V[:, 1]) - F.side_y(np.clip(m.V[:, 0], F.STA["cowl_front"], F.STA["tail_end"]), m.V[:, 2])
        m = _trim(m, f, "negative")
        if np.dot(m.face_normals().mean(0), tail_cut_normal()) < 0:
            m = m.flipped()
        m.N = np.tile(tail_cut_normal(), (len(m.V), 1))
        out.append(m)
    return Mesh.merge(out)


def fin_halfwidth(x, z):
    """Half-thickness of the fin section (NACA 0018) at station x, WL z (0 outside the chord)."""
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    le, te = fin_le(z), fin_te(z)
    xc = (x - le) / (te - le)
    t = FIN_AF_ROOT.thickness(np.clip(xc, 0.0, 1.0))
    return np.where((xc >= 0) & (xc <= 1), 0.5 * t * (te - le), 0.0)


def rudder_split_z(x):
    """Fixed-tip / rudder boundary (the drawn top edge), flat forward of the rudder nose."""
    xn = rudder_edge_point(RUD_NOSE_XC, "top")[0]
    return rudder_top_z(np.maximum(np.asarray(x, float), xn))


def _fin_tip_cap():
    """Lower face of the fixed fin tip over the rudder: along the sloped top edge (+gap) from the cove to the TE, closed
    at the front by the cove arc at the flat part of the edge."""
    from model.wing import plain_cove
    z0 = float(rudder_split_z(0.0)) + RUD_EDGE_GAP
    sec = fin_section(z0)
    cove, _ = plain_cove(sec, RUD_XH, RUD_COVE_GAP)
    arc = sec.point(cove[:, 0], cove[:, 1])                    # upper (+y) -> round the front -> lower (-y)
    xs = np.linspace(float(arc[0, 0]), float(fin_te(3.77)), 40)
    zz = np.array([float(rudder_split_z(x)) + RUD_EDGE_GAP for x in xs])
    for _ in range(3):                                          # the TE moves with z: re-evaluate the chord end
        xs = np.linspace(float(arc[0, 0]), float(fin_te(zz[-1])) - 0.002, 40)
        zz = np.array([float(rudder_split_z(x)) + RUD_EDGE_GAP for x in xs])
    hw = fin_halfwidth(xs, zz)
    side_s = np.c_[xs, hw, zz]
    side_p = np.c_[xs, -hw, zz][::-1]
    loop = np.vstack([arc[::-1], side_s[1:], side_p[1:-1]])
    return planar_cap(loop, (0, 0, -1))


def _fin_keel_cap():
    """Cap closing the fixed fin strip behind the tail-cone closure (cut plane -> cove) at the keel line."""
    from model.wing import plain_cove
    zb = _cut_z_range()[0]
    sec = fin_section(zb)
    cove, _ = plain_cove(sec, RUD_XH, RUD_COVE_GAP)
    arc = sec.point(cove[:, 0], cove[:, 1])
    xs = np.linspace(float(tail_cut_x(zb)), float(arc[0, 0]), 10)
    hw = fin_halfwidth(xs, np.full_like(xs, zb))
    side_s = np.c_[xs, hw, np.zeros_like(xs)]
    side_p = np.c_[xs, -hw, np.zeros_like(xs)][::-1]
    loop = np.vstack([side_s, arc[1:-1] * [1, 1, 0], side_p])
    loop[:, 2] = F.z_bot(np.clip(loop[:, 0], F.STA["cowl_front"], F.STA["tail_end"])) + 0.003
    return planar_cap(loop, (0, 0, -1))


def ventral_fairing(n_ring=24):
    """Thin ventral fairing under the tail cone (FR40): between the keel line and VENTRAL_EDGE, from its leading edge
    (hidden behind the strakes) to the tail cut; rounded lower edge, capped in the cut plane."""
    from cad.mesh import trim as _trim, boundary_loops as _bl
    (vx0, vz0), _ = VENTRAL_EDGE
    x_end = float(tail_cut_x(rudder_bottom_z(12.7))) + 0.05
    xs = np.linspace(VENTRAL_X0 + 0.003, x_end, 48)
    rows = []
    for x in xs:
        zk = float(F.z_bot(min(x, F.STA["tail_end"])))
        zlow = float(rudder_bottom_z(x)) if x >= vx0 else zk + (vz0 - zk) * (x - VENTRAL_X0) / (vx0 - VENTRAL_X0)
        ztop = zk + 0.035
        h = max(ztop - zlow, 0.004)
        t = min(VENTRAL_T, 0.45 * h)
        a = np.linspace(-np.pi / 2, np.pi / 2, n_ring // 2)
        low = np.c_[t * np.sin(a), zlow + t - t * np.cos(a)]          # rounded bottom, -y -> +y
        ring = np.vstack([low, [[t, ztop]], [[-t, ztop]]])
        rows.append(np.c_[np.full(len(ring), x), ring])
    P = np.array(rows)
    m = grid_surface(P, close_v=True)
    cen = P.mean(1)
    if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
        m = m.flipped()
    m = _trim(m, tail_cut_field(m.V[:, 0], m.V[:, 2]), "negative")
    caps = [cap_ring(P[0], (-1, 0, 0))]
    for lp in _bl(m):
        caps.append(planar_cap(m.V[lp], tail_cut_normal()))
    return Mesh.merge([m] + caps)


def rudder_body():
    """Rudder (with its trim-tab cut-out) between the sloped bottom edge (VENTRAL_EDGE) and top edge (- gap), capped on
    both sloped faces.  Returns (body, tab, (tab hinge points))."""
    from model.wing import segmented_surface
    from cad.mesh import trim as _trim, boundary_loops as _bl
    zb0 = float(rudder_edge_point(RUD_NOSE_XC, "bottom")[1]) - 0.03
    zt1 = float(rudder_edge_point(RUD_NOSE_XC, "top")[1]) + 0.03
    body, tab, hinge = segmented_surface(fin_section, zb0, zt1, RUD_XH, RUD_TAB, step=0.06)
    body = _trim(body, body.V[:, 2] - rudder_bottom_z(body.V[:, 0]), "positive")
    body = _trim(body, body.V[:, 2] - (rudder_split_z(body.V[:, 0]) - RUD_EDGE_GAP), "negative")
    caps = []
    for lp in _bl(body):
        P = body.V[lp]
        up = P[:, 2].mean() > 3.0
        caps.append(planar_cap(P, (0, 0, 1) if up else (0, 0, -1)))
    return Mesh.merge([body] + caps), tab, hinge


def fin_mesh():
    """Fixed fin: skins with the rudder cove, trimmed to the tail-cone OML (the root stands on the cone, nothing below
    its maximum-breadth line: the ventral part is ventral_fairing()) and to the sloped rudder top edge."""
    from model.wing import plain_cove, x_end_of_plain, cut_rib
    from cad.mesh import trim as _trim
    zT0 = float(rudder_split_z(0.0)) + RUD_EDGE_GAP
    zB = span_stations(RUD_Z[0], zT0, 0.06)
    xl_e, xu_e = x_end_of_plain(fin_section(float(np.mean(RUD_Z))), RUD_XH, RUD_COVE_GAP)
    lower = [skin(fin_section, zB, x_lo_end=xl_e, x_up_end=xu_e, n=56),
             curve_patch(fin_section, zB, lambda s: plain_cove(s, RUD_XH, RUD_COVE_GAP)[0], n=16,
                         outward_hint=lambda s: s.e_c)]
    zC = np.unique(np.r_[span_stations(float(np.min(rudder_top_z(np.array([14.4])))) - 0.02, 4.0, 0.03),
                         span_stations(4.0, FIN_Z1, 0.05)])
    upper = [skin(fin_section, zC, n=56), strip(fin_section, zC, 1.0, 1.0)]
    out = []
    X0, X1 = F.STA["cowl_front"], F.STA["tail_end"]

    def keep(V):
        """> 0 where the fixed fin is kept: above the tail cone (outside the OML, over its max-breadth line) or,
        behind the tail-cone closure, the strip + cove round the rudder nose down to the keel line."""
        xc = np.clip(V[:, 0], X0, X1)
        above = np.minimum(oml_field(V), V[:, 2] - F.z_mw(xc))
        behind = np.minimum(tail_cut_field(V[:, 0], V[:, 2]), V[:, 2] - F.z_bot(xc) - 0.003)
        return np.maximum(above, behind)

    for m in lower:
        out.append(_trim(m, keep(m.V), "positive"))
    for m in upper:
        out.append(_trim(m, m.V[:, 2] - (rudder_split_z(m.V[:, 0]) + RUD_EDGE_GAP), "positive"))
    out.append(_fin_tip_cap())
    out.append(_fin_keel_cap())
    return Mesh.merge(out)


def dorsal_mesh():
    """Dorsal slab (above the tail-cone crown only) and its root fillet into the tail cone (both flanks)."""
    from cad.mesh import trim as _trim
    zd = span_stations(2.40, float(_dorsal_curve()[-1, 1]) - 0.01, 0.03)
    slab = skin(dorsal_section, zd, n=48)
    slab = _trim(slab, oml_field(slab.V), "positive")
    T = np.array(DORSAL_FILLET)
    xs = np.unique(np.r_[np.linspace(T[0, 0] + 0.002, 9.25, 24), np.linspace(9.25, T[-1, 0], 90)])
    rows = [dorsal_fillet_section(x, n=18) for x in xs]
    P = np.array([np.c_[np.full(len(r), x), r] for x, r in zip(xs, rows)])
    fil = []
    for sgn in (1, -1):
        m = grid_surface(P * [1, sgn, 1])
        k = len(m.V) // 2
        if m.N[k, 1] * sgn + m.N[k, 2] < 0:
            m = m.flipped()
        m = _trim(m, tail_cut_field(m.V[:, 0], m.V[:, 2]), "negative")
        fil.append(m)
    return Mesh.merge([slab] + fil)


def build(parts: dict):
    # ---------------- fin (fixed part, trimmed to the tail cone) + ventral fairing + rudder
    fin = Part("fin", "Vertical stabiliser (fin) + ventral fairing", "empennage_v", explode=(0.9, 0, 0.9),
               group="Empennage", material_note="Aluminium two-spar fin; glass-fibre ventral fairing",
               info={"LE sweep": "%.0f deg" % np.degrees(np.arctan2(FIN_LE[1][0] - FIN_LE[0][0], FIN_LE[1][1] - FIN_LE[0][1])),
                     "section": "NACA 0018 (drawing VF1 / VF2)"})
    fin.add(fin_mesh(), "paint_white").add(ventral_fairing(), "paint_white")
    parts[fin.id] = fin

    # rudder (single piece, two hinges) with an electric trim tab low on the trailing edge
    rud, rtab, (rta, rtb) = rudder_body()
    a, b = fin_section(RUD_Z[0]), fin_section(RUD_Z[1])
    ha, hb = a.point(np.array(RUD_XH), np.array(0.0)), b.point(np.array(RUD_XH), np.array(0.0))
    ax = (hb - ha) / np.linalg.norm(hb - ha)
    rp = Part("rudder", "Rudder", "empennage_v", pivot=dict(origin=ha.tolist(), axis=ax.tolist(), kind="rudder",
                                                            range=[-25.0, 25.0]),
              explode=(1.5, 0, 0.9), group="Flight controls", material_note="Mass-balanced rudder")
    rp.add(rud, "paint_white")
    parts[rp.id] = rp
    tax = (rtb - rta) / np.linalg.norm(rtb - rta)
    tp = Part("rudder_tab", "Rudder trim tab (electric)", "empennage_v", parent="rudder",
              pivot=dict(origin=rta.tolist(), axis=tax.tolist(), kind="tab", gearing=0.0, range=[-12, 12]),
              explode=(0.3, 0, 0), group="Flight controls", material_note="Electric trim (tab location per drawing)")
    tp.add(rtab, "paint_white")
    parts[tp.id] = tp

    # dorsal fin + root fillet
    dp = Part("dorsal_fin", "Dorsal fin + root fillet", "empennage_v", explode=(0.6, 0, 0.7), group="Empennage",
              material_note="Glass-fibre fairing")
    dp.add(dorsal_mesh(), "paint_white")
    parts[dp.id] = dp

    # ventral strakes
    parts["strakes"] = build_strakes()

    # ---------------- tailplane (one piece, trimmable) + elevators
    stab_meshes = []
    for sgn in (1, -1):
        def sec_fn(y, sgn=sgn):
            s = stab_section(abs(y))
            if sgn < 0:
                s = Section(le=s.le * [1, -1, 1], chord=s.chord, e_c=s.e_c, e_t=s.e_t, twist=s.twist,
                            airfoil=s.airfoil)
            return s
        ys0 = span_stations(0.0, ELEV_Y[0], 0.05)
        ys1 = span_stations(ELEV_Y[0], ELEV_Y[1], 0.15)
        ys2 = np.concatenate([span_stations(ELEV_Y[1], 2.30, 0.05), span_stations(2.30, STAB_TIP_Y - 0.004, 0.02)[1:]])
        ms = []
        ms.append(skin(sec_fn, ys0, n=48))
        ms.append(strip(sec_fn, ys0, 1.0, 1.0))
        xl_e, xu_e = x_end_of_plain(stab_section(1.2), ELEV_XH)
        ms.append(skin(sec_fn, ys1, x_lo_end=xl_e, x_up_end=xu_e, n=48))
        ms.append(curve_patch(sec_fn, ys1, lambda s: plain_cove(s, ELEV_XH)[0], outward_hint=lambda s: s.e_c))
        # fixed tip outboard of the elevator (BL 2270): only ahead of the drawn horn gap (STAB_HORN_GAP); the horn
        # balance aft of it (ELEV_HORN, stab_tip_outline) moves with the elevator (horn_body())
        tipskin = skin(sec_fn, ys2, n=48)
        ms.append(trim(tipskin, tipskin.V[:, 0] - horn_gap_x(tipskin.V[:, 1]), "negative"))
        from model.wing import cut_rib
        sec = sec_fn(ELEV_Y[0])
        cove, _ = plain_cove(sec, ELEV_XH)
        xl, xu = x_end_of_plain(sec, ELEV_XH)
        ms.append(planar_cap(cut_rib(sec, cove[::-1], xl, xu), (0, sgn, 0)))
        # outboard face of the fixed part at BL 2270 between the horn gap and the elevator cove
        sec = sec_fn(ELEV_Y[1])
        cove, _ = plain_cove(sec, ELEV_XH)
        xl, xu = x_end_of_plain(sec, ELEV_XH)
        xg = float((horn_gap_x(ELEV_Y[1]) - sec.le[0]) / sec.chord)
        af = sec.airfoil
        xs_u = cos_pts(10, 0, 1) * (xu - xg) + xg
        xs_l = (cos_pts(10, 0, 1) * (xl - xg) + xg)[::-1]
        poly = np.vstack([np.stack([xs_u, af.upper(xs_u)], 1)[:-1], cove[:-1], np.stack([xs_l, af.lower(xs_l)], 1)])
        ms.append(planar_cap(sec.point(poly[:, 0], poly[:, 1]), (0, sgn, 0)))
        # aft face of the fixed tip along the horn gap (BL 2270 -> the point where the gap line leaves the LE)
        yy = np.linspace(ELEV_Y[1], STAB_NOTCH_Y, 24)
        up, lo = [], []
        for y in yy:
            sc = sec_fn(y)
            xc = float(np.clip((float(horn_gap_x(y)) - sc.le[0]) / sc.chord, 0.0, 1.0))
            up.append(sc.upper(np.array(xc)))
            lo.append(sc.lower(np.array(xc)))
        ms.append(planar_cap(np.vstack([np.array(up), np.array(lo)[::-1][:-1]]), (1, 0, 0)))
        m = Mesh.merge(ms)
        if sgn < 0:
            # skins built with mirrored sections have inverted orientation -> fix by normal test
            pass
        stab_meshes.append(m)
    # stabiliser pivots (variable incidence) about a spanwise axis at its rear spar
    piv = np.array([STAB_ROOT_LE + 0.62 * STAB_ROOT_C, 0.0, STAB_Z])
    sp = Part("stabilizer", "Horizontal stabiliser (variable incidence)", "empennage_h",
              pivot=dict(origin=piv.tolist(), axis=[0, 1.0, 0], kind="trim", range=[-4.0, 2.0]),
              explode=(0.9, 0, 1.5), group="Empennage", material_note="Electrically trimmed, dual actuators",
              info={"span": "5,200 mm", "root chord": f"{STAB_ROOT_C*1000:.0f} mm",
                    "LE sweep": f"{np.degrees(STAB_SWEEP):.1f} deg, horn-balanced tips (drawing)"})
    sp.add(Mesh.merge(stab_meshes), "paint_white")
    parts[sp.id] = sp

    horn = horn_body()
    for side, sgn in (("R", 1), ("L", -1)):
        ys = span_stations(ELEV_Y[0] + 0.012, ELEV_HORN[0] + 0.006, 0.15)
        em = Mesh.merge([closed_body(stab_section, ys, lambda s: plain_surface_loop(s, ELEV_XH)), horn])
        a, b = stab_section(ELEV_Y[0]), stab_section(ELEV_Y[1])
        ha, hb = a.point(np.array(ELEV_XH), np.array(0.0)), b.point(np.array(ELEV_XH), np.array(0.0))
        if sgn < 0:
            em = em.mirrored_y()
            ha, hb = ha * [1, -1, 1], hb * [1, -1, 1]
        ax = (hb - ha) / np.linalg.norm(hb - ha) * sgn
        ep = Part(f"elevator_{side}", f"{'Right' if sgn > 0 else 'Left'} elevator", "empennage_h",
                  parent="stabilizer",
                  pivot=dict(origin=ha.tolist(), axis=ax.tolist(), kind="elevator", range=[-20.0, 15.0]),
                  explode=(0.5, sgn * 0.35, 0.0), group="Flight controls",
                  material_note="Paired elevators with horn-balanced tips")
        ep.add(em, "paint_white")
        parts[ep.id] = ep

    # bullet fairing
    parts["tail_bullet"] = build_bullet()
    return parts


def horn_body():
    """Starboard horn balance (moves with the elevator): the tailplane tip aft of its front face (horn_front_x) from
    the elevator's outboard end (ELEV_HORN[0] + 6 mm) to the tip, with a rounded tip cap."""
    ys = np.unique(np.r_[span_stations(ELEV_HORN[0] + 0.006, STAB_NOTCH_Y + 0.006, 0.012),
                         span_stations(STAB_NOTCH_Y + 0.006, STAB_TIP_Y - 0.004, 0.02)])
    body = closed_body(stab_section, ys, horn_loop)
    tip = stab_section(STAB_TIP_Y - 0.004)
    xx = cos_pts(40)
    loop = np.vstack([tip.lower(xx[::-1]), tip.upper(xx[1:-1])])
    return Mesh.merge([body, cap_ring(loop, (0, 1, 0))])


def fix_orient(m: Mesh, zc):
    """Stabiliser skins: normals must point away from the chord plane."""
    up = m.V[:, 2] - zc
    # only correct patches where most normals point inward: approximate per-face test
    fn = m.face_normals()
    ctr = m.V[m.F].mean(1)
    s = np.sign(ctr[:, 2] - zc) * fn[:, 2]
    # flip faces whose normal points toward the chord plane on thick regions
    bad = s < -0.3
    if bad.mean() > 0.3:
        m = m.flipped()
    return m


def build_bullet():
    """Bullet fairing lofted through the elliptic sections of BULLET (drawing side view + plan)."""
    T = np.array(BULLET)
    xs = np.unique(np.concatenate([np.linspace(T[0, 0], T[-1, 0], 60), T[:, 0]]))
    rows = [bullet_section(x) for x in xs[1:]]
    P = np.array(rows)
    m = grid_surface(P, close_v=True)
    cen = P.mean(1)
    if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
        m = m.flipped()
    nose = np.array([T[0, 0], 0.0, T[0, 1]])
    # nose fan and aft end cap
    n = P.shape[1]
    V = np.vstack([P[0], nose[None]])
    k = np.arange(n)
    fan = Mesh(V, np.stack([np.full(n, n), (k + 1) % n, k], 1))
    if np.dot(fan.face_normals().mean(0), [-1, 0, 0]) < 0:
        fan = fan.flipped()
    m = Mesh.merge([m, fan, cap_ring(P[-1], (1, 0, 0))])
    p = Part("tail_bullet", "Fin / tailplane bullet fairing", "empennage_h", explode=(1.2, 0, 1.9),
             group="Empennage", material_note="Composite fairing, tail nav/strobe light")
    p.add(m, "paint_white")
    return p


def build_strakes():
    """Two canted ventral strakes: thin plates between the root line (on the tail-cone side) and the tip line."""
    ms = []
    (r0x, _), (r1x, _) = STRAKE_ROOT
    xs = np.linspace(r0x + 0.01, r1x - 0.005, 40)
    for sgn in (1, -1):
        rows = []
        for x in xs:
            fr = strake_frame(x)
            if fr is None:
                continue
            r, t = fr
            d = t - r
            L = max(np.linalg.norm(d), 1e-4)
            u = d / L
            nrm = np.array([0.0, u[2], -u[1]])          # plate normal (in the cross-section plane)
            ss = np.linspace(0, 1, 8)
            h = 0.5 * STRAKE_T * np.minimum(1.0, 6 * np.minimum(ss, 1 - ss) + 0.15) * min(1.0, L / 0.05)
            a = r[None] + ss[:, None] * d[None] + h[:, None] * nrm[None]
            b = (r[None] + ss[:, None] * d[None] - h[:, None] * nrm[None])[::-1]
            ring = np.vstack([a, b[1:-1]]) if len(a) > 2 else np.vstack([a, b])
            if sgn < 0:
                ring = ring * [1, -1, 1]
            rows.append(ring)
        P = np.array(rows)
        m = grid_surface(P, close_v=True)
        cen = P.mean(1)
        if np.mean(np.sum((P - cen[:, None]).reshape(-1, 3) * m.N, 1)) < 0:
            m = m.flipped()
        ms.append(Mesh.merge([m, cap_ring(P[0], (-1, 0, 0)), cap_ring(P[-1], (1, 0, 0))]))
    p = Part("strakes", "Ventral strakes (2)", "empennage_v", explode=(0.6, 0, -0.8), group="Empennage",
             qty=2, material_note="Kevlar / honeycomb sandwich")
    p.add(Mesh.merge(ms), "paint_white")
    return p
