"""
Cirrus SF50 Vision Jet -- parameters, control lines and section laws (hwd3d Phase 3, M1).

Every number below is tagged:
  [obs: <source>]  stated by a primary / manufacturer source (see SF50_FACTS.md for the URL and quoted words)
  [inf: <method>]  inferred -- read off a drawing, derived from other numbers, or a modelling choice
The reference drawings are the Cirrus AFM P/N 31452-001 figures (Figure 1-1 "Airplane Three View", Figure 1-2
"Airplane Interior Dimensions", Figure 8-1); they are reference only and are never committed.  Only the FITTED model
parameters are kept here, each with a one-line basis; the readings of those figures (outlines, stations, scales) are local
reference data in the gitignored refs/cache/local/models/afm_sf50_meas.json (fix round 3: orchestrator decision (b)
2026-11-13 under the owner's delegation; the owner may overrule).  The printed dimension labels of the AFM (e.g. "11.1 ft")
are published values and are quoted.

Model axes (same convention as pc12/):
  x = fuselage station FS, metres aft of the type-certificate datum ("89 inches in front of the flat surface of the
      forward cabin bulkhead", FAA TCDS A00018CH)                                            [obs]
  y = butt line, + starboard
  z = height above the ground, aircraft static on its gear (ground = 0)
glTF (pc12/cad/glb.py to_gl): X = y (starboard), Y = z (up), Z = x (aft).
"""
from __future__ import annotations
import numpy as np
from scipy.interpolate import PchipInterpolator

IN = 0.0254
FT = 0.3048


def pchip(pts):
    a = np.asarray(pts, float)
    return PchipInterpolator(a[:, 0], a[:, 1], extrapolate=True)


# ------------------------------------------------------------------------------------------------ overall (obs)
LENGTH = 9.357           # [obs: FAA ACD 30.7 ft; AFM Fig 1-1 30.7 ft; EASA TCDS 9.36 m]
SPAN = 11.796            # [obs: FAA ACD / Cirrus / AFM Fig 1-1 38.7 ft]  (EASA TCDS says 11.67 m (38.3 ft): see facts)
HEIGHT = 3.322           # [obs: FAA ACD 10.9 ft; AFM Fig 1-1 10.9 ft; Cirrus 3.32 m]
WING_AREA = 18.18        # [obs: EASA TCDS 18.18 m2; AFM Fig 1-1 195.7 sq ft]
TRACK = 11.2 * FT        # 3.414 m [obs: AFM Fig 1-1 front view "11.2 ft (3.4 m)"]
VTAIL_SPAN = 14.7 * FT   # 4.481 m [obs: AFM Fig 1-1 top view "14.7 ft (4.5 m)", tip to tip]
X_WING_LE_ROOT_FROM_NOSE = 11.1 * FT   # 3.383 m [obs: AFM Fig 1-1 "11.1 ft (3.4 m)" nose -> wing root LE]
X_WING_TE_ROOT_FROM_NOSE = 18.3 * FT   # 5.578 m [obs: AFM Fig 1-1 "18.3 ft (5.6 m)" nose -> wing root TE (fillet)]

# ------------------------------------------------------------------------------------------------ datum / stations
X_NOSE = 0.900           # [inf: fitted, AFM Fig 1-2 window stations (FS) registered on the same windows in Fig 1-1]
X_TAIL = X_NOSE + LENGTH  # 10.257
X_FWD_BULKHEAD = 89.0 * IN   # 2.261 [obs: TCDS datum definition]
CABIN_LENGTH = 137.8 * IN    # [obs: AFM Fig 1-2 table]
CABIN_WIDTH = 61.0 * IN      # [obs: AFM Fig 1-2 table; Cirrus 5.1 ft]
CABIN_HEIGHT = 48.8 * IN     # [obs: AFM Fig 1-2 table; Cirrus 4.1 ft]
FLOOR_Z = 0.99               # [inf: fitted, AFM Fig 1-2 window heights above the floor vs Fig 1-1 window heights]

# ------------------------------------------------------------------------------------------------ fuselage control lines
# (FS m, value m): fitted control lines [inf: nose / tail fitted to AFM Fig 1-1 side + plan, cabin to the AFM Fig 1-2 OML]
_CROWN = [(0.900, 1.170), (0.905, 1.205), (0.915, 1.240), (0.94, 1.277), (0.97, 1.310), (1.00, 1.338), (1.06, 1.378),
          (1.125, 1.410), (1.28, 1.474), (1.435, 1.530), (1.59, 1.576), (1.746, 1.620), (1.90, 1.666), (2.056, 1.706),
          (2.21, 1.748), (2.30, 1.790), (2.40, 1.856), (2.46, 1.880), (2.595, 1.953), (2.728, 2.026), (2.86, 2.096),
          (2.993, 2.159), (3.126, 2.218), (3.259, 2.265), (3.392, 2.302), (3.524, 2.328), (3.657, 2.348), (3.79, 2.361),
          (3.923, 2.371), (4.056, 2.378), (4.25, 2.381), (4.45, 2.381), (4.587, 2.375), (4.72, 2.368), (4.853, 2.358),
          (4.985, 2.348), (5.118, 2.331), (5.251, 2.311), (5.384, 2.292), (5.517, 2.268), (5.649, 2.245), (5.782, 2.215),
          (5.915, 2.185), (6.10, 2.140), (6.35, 2.075), (6.65, 2.020), (6.98, 1.969), (7.24, 1.930), (7.51, 1.893),
          (7.80, 1.868), (8.10, 1.852), (8.40, 1.838), (8.70, 1.822), (9.00, 1.802), (9.30, 1.780), (9.60, 1.752),
          (9.90, 1.718), (10.08, 1.690), (10.18, 1.662), (10.23, 1.635), (10.25, 1.612), (10.257, 1.590)]
_KEEL = [(0.900, 1.170), (0.905, 1.130), (0.915, 1.095), (0.94, 1.057), (0.97, 1.026), (1.00, 1.000), (1.06, 0.966),
         (1.125, 0.940), (1.28, 0.885), (1.435, 0.837), (1.59, 0.800), (1.90, 0.760), (2.21, 0.727), (2.46, 0.712),
         (2.73, 0.695), (3.00, 0.688), (3.40, 0.690), (3.66, 0.695), (3.90, 0.690),
         # belly / wing-root fairing [inf: fitted to the AFM Fig 1-1 side view]
         (4.15, 0.665), (4.45, 0.628), (4.80, 0.605), (5.30, 0.598), (5.70, 0.608), (6.00, 0.640), (6.30, 0.700),
         (6.60, 0.775), (6.90, 0.842), (7.33, 0.930), (7.64, 0.995), (7.95, 1.060), (8.42, 1.140), (8.88, 1.230),
         (9.30, 1.320), (9.70, 1.400), (10.00, 1.455), (10.15, 1.500), (10.23, 1.545), (10.25, 1.568), (10.257, 1.590)]
_HALF = [(0.900, 0.0), (0.905, 0.050), (0.915, 0.080), (0.93, 0.105), (0.96, 0.140), (1.00, 0.170), (1.06, 0.205),
         (1.18, 0.262), (1.34, 0.326), (1.49, 0.385), (1.65, 0.437), (1.80, 0.483), (1.96, 0.528), (2.11, 0.570),
         (2.27, 0.603), (2.35, 0.617), (2.51, 0.648), (2.68, 0.680), (2.84, 0.711), (3.01, 0.737), (3.17, 0.762),
         (3.34, 0.784), (3.51, 0.801), (3.67, 0.818), (3.84, 0.832), (4.01, 0.840), (4.17, 0.845), (4.40, 0.848),
         (4.60, 0.847), (4.75, 0.842), (4.92, 0.836), (5.08, 0.826), (5.25, 0.810), (5.42, 0.792), (5.58, 0.773),
         (6.00, 0.714), (6.50, 0.632), (6.83, 0.577), (7.16, 0.519), (7.57, 0.453), (8.00, 0.385), (8.40, 0.318),
         (8.80, 0.235), (9.15, 0.170), (9.50, 0.140), (9.80, 0.122), (10.00, 0.108), (10.12, 0.094), (10.20, 0.074),
         (10.235, 0.052), (10.25, 0.032), (10.257, 0.0)]
_ZMW = [(0.900, 1.170), (1.00, 1.160), (1.30, 1.160), (1.60, 1.185), (2.00, 1.250), (2.40, 1.330), (2.80, 1.410),
        (3.20, 1.480), (3.60, 1.530), (4.00, 1.550), (5.00, 1.560), (5.60, 1.565), (6.20, 1.575), (6.80, 1.585),
        (7.40, 1.585), (8.00, 1.575), (8.60, 1.565), (9.20, 1.565), (9.80, 1.575), (10.257, 1.590)]
# super-ellipse exponents (2 = ellipse): slightly square cabin, flat-bottomed belly fairing over the wing box
_NTOP = [(0.90, 2.0), (2.0, 2.05), (2.6, 2.25), (3.4, 2.35), (5.6, 2.35), (7.0, 2.2), (8.5, 2.1), (10.257, 2.0)]
_NBOT = [(0.90, 2.0), (2.0, 2.15), (3.2, 2.35), (3.95, 2.45), (4.40, 3.05), (5.80, 3.10), (6.40, 2.75), (7.20, 2.35),
         (8.50, 2.15), (10.257, 2.0)]

z_top = pchip(_CROWN)
z_bot = pchip(_KEEL)
half_w = pchip(_HALF)
z_mw = pchip(_ZMW)
n_top = pchip(_NTOP)
n_bot = pchip(_NBOT)
CONTROL_LINES = dict(crown=_CROWN, keel=_KEEL, half_breadth=_HALF, max_breadth_wl=_ZMW, n_top=_NTOP, n_bot=_NBOT)


def section(x, t):
    """OML point(s).  t in [0, 1): 0 = crown, 0.25 = starboard max breadth, 0.5 = keel, 0.75 = port."""
    x = np.asarray(x, float)
    t = np.asarray(t, float)
    a = 2 * np.pi * t
    s, c = np.sin(a), np.cos(a)
    up = c >= 0
    n = np.where(up, n_top(x), n_bot(x))
    hw = np.maximum(half_w(x), 0.0)
    zm = z_mw(x)
    hz = np.where(up, z_top(x) - zm, zm - z_bot(x))
    hz = np.maximum(hz, 0.0)
    y = hw * np.sign(s) * np.abs(s) ** (2.0 / n)
    z = zm + hz * np.sign(c) * np.abs(c) ** (2.0 / n)
    return np.stack(np.broadcast_arrays(x, y, z), -1)


def side_y(x, z):
    """|y| of the OML at (x, z); 0 outside the section's z range."""
    x = np.asarray(x, float)
    z = np.asarray(z, float)
    zm = z_mw(x)
    up = z >= zm
    n = np.where(up, n_top(x), n_bot(x))
    hz = np.maximum(np.where(up, z_top(x) - zm, zm - z_bot(x)), 1e-6)
    r = np.clip(np.abs(z - zm) / hz, 0, 1)
    return np.maximum(half_w(x), 0) * (1 - r ** n) ** (1.0 / n)


def inside_fuselage(P):
    """Signed distance-like field: > 0 outside the fuselage OML, < 0 inside (lateral metres)."""
    P = np.asarray(P, float)
    x = np.clip(P[..., 0], X_NOSE, X_TAIL)
    z = P[..., 2]
    zin = (z <= z_top(x)) & (z >= z_bot(x)) & (P[..., 0] >= X_NOSE) & (P[..., 0] <= X_TAIL)
    sy = side_y(x, z)
    d = np.abs(P[..., 1]) - sy
    return np.where(zin, d, np.maximum(d, 0.0) + 0.05 + np.minimum(np.abs(z - z_top(x)), np.abs(z - z_bot(x))))


def t_of(x, z, side=1):
    """Circumferential parameter of the OML point at (x, z) on the given side."""
    x = np.asarray(x, float)
    z = np.asarray(z, float)
    zm = z_mw(x)
    up = z >= zm
    n = np.where(up, n_top(x), n_bot(x))
    hz = np.where(up, z_top(x) - zm, zm - z_bot(x))
    r = np.clip((z - zm) / hz, -1, 1)
    c = np.sign(r) * np.abs(r) ** (n / 2.0)
    t = np.arccos(np.clip(c, -1, 1)) / (2 * np.pi)
    return t if side > 0 else 1.0 - t


def station_grid():
    tip = np.r_[np.linspace(0.900, 0.915, 5), np.linspace(0.92, 1.00, 12)]
    body = np.arange(1.01, 10.20, 0.022)
    tail = np.linspace(10.20, X_TAIL, 9)
    return np.unique(np.r_[tip, body, tail, [2.30, 2.40, 4.25, 4.45]])


# ------------------------------------------------------------------------------------------------ glazing & openings
# Windshield: two wrap-around panes with a centre post (Cirrus: "two panoramic pilot and copilot windows").
# Plan outline (FS, BL) and sill line (FS, WL) [inf: fitted to AFM Fig 1-1 plan + side].
WS_PLAN = [(2.355, -0.20), (2.355, 0.0), (2.372, 0.15), (2.415, 0.30), (2.495, 0.44), (2.615, 0.56), (2.775, 0.66),
           (2.950, 0.74), (3.100, 0.80), (3.180, 0.98), (3.560, 0.98), (3.495, 0.77), (3.445, 0.65), (3.370, 0.51),
           (3.265, 0.35), (3.150, 0.19), (3.075, 0.06), (3.058, 0.0), (3.058, -0.20)]
WS_SILL = [(2.25, 1.880), (2.40, 1.818), (2.55, 1.786), (2.75, 1.757), (3.00, 1.740), (3.25, 1.739), (3.45, 1.760),
           (3.60, 1.800)]
WS_POST = 0.040          # half-width of the centre post [inf: fitted to AFM Fig 1-1 plan]
z_sill = pchip(WS_SILL)

# cabin windows: squircles in side projection (cx, cz, half-length, half-height, exponent) [inf: fitted to AFM Fig 1-1
# side view; same stations on the right side per the plan view]
WINDOWS = {
    "w1": (3.935, 1.950, 0.240, 0.205, 3.2),    # port: in the cabin door; starboard: emergency egress window
    "w2": (4.617, 1.930, 0.220, 0.200, 3.0),
    "w3": (5.232, 1.905, 0.168, 0.160, 2.7),
}
# cabin door (port only, clam-shell: "pull the bottom half of the door up and the top half down", AOPA) -- parallelogram
# leaning forward at the bottom.  AFM Fig 1-2: opening 24.6 in wide x 49.4 in high.  [obs: size; inf: placement]
DOOR = dict(bf=(3.385, 0.975), ba=(4.010, 0.975), ta=(4.300, 2.270), tf=(3.675, 2.270), r=0.07)
DOOR_SPLIT_Z = 1.625     # [inf: below the door window; AFM Fig 2-21/2-22 "Door Operation, Upper / Lower"]
# baggage door (port, aft fuselage: AFM walk-around "Left Fuselage ... Baggage Door"); AFM Fig 1-2 opening 23.0 / 24.9 in
# wide x 19.3 / 17.6 in high.  [obs: size; inf: position from AFM Fig 8-1]
BAG_DOOR = dict(cx=6.43, cz=1.62, hx=0.316, hz=0.245, r=0.05)
# registration panel: blank area on each side of the aft fuselage, filled by the runtime only for aircraft not flagged
# LADD/PIA (D1).  [inf: position; FAA 14 CFR 45.29 marks >= 12 in high -> panel 0.32 m]
REG_PANEL = dict(x0=7.05, x1=8.30, zc=1.635, h=0.30)
# nose-gear bay in the keel [inf: fitted to the open nose-gear doors of AFM Fig 1-1]
NOSE_BAY = dict(x0=1.33, x1=2.30, hw=0.165, r=0.05)

# ------------------------------------------------------------------------------------------------ wing
# NACA 23015 root -> NACA 23012 tip.  The SF50 section is not published (the Incomplete Guide to Airfoil Usage lists
# the Cirrus SR20/SR22 as "Roncz airfoil" and has no SF50 entry); the NACA 230xx family is the documented choice of a
# contemporary light jet (Cessna 501 Citation I: NACA 23014 / 23012) and has an exact analytic definition. [inf]
WING_SEMI_REF = SPAN / 2          # 5.898: reference trapezoid to the overall span [inf: convention]
Y_TIPCAP = 5.500                  # start of the wing-tip fairing [inf: fitted to AFM Fig 1-1 plan]
Y_FUS = 0.848                     # fuselage half-breadth at the wing root [inf]
LE_SWEEP = np.radians(5.65)       # [inf: fitted to AFM Fig 1-1 plan]
TAPER_FIT = 0.6428571428571428   # model chord ratio, tip fairing / fuselage side [inf: fitted to AFM Fig 1-1 plan]


def _solve_planform():
    # chord law c(y) = c0 * (1 - k y), linear, with c(Y_TIPCAP) / c(Y_FUS) = TAPER_FIT; scale so the reference trapezoid
    # (0..SPAN/2) has the TCDS area.
    k = (1 - TAPER_FIT) / (Y_TIPCAP - TAPER_FIT * Y_FUS)
    area_unit = 2 * (WING_SEMI_REF - 0.5 * k * WING_SEMI_REF ** 2)
    c0 = WING_AREA / area_unit
    return c0, k


C0, K_CHORD = _solve_planform()
X_LE_FUS = X_NOSE + X_WING_LE_ROOT_FROM_NOSE            # LE at the fuselage side, FS 4.283 [obs 11.1 ft]
X_LE0 = X_LE_FUS - Y_FUS * np.tan(LE_SWEEP)            # LE at BL 0
DIHEDRAL = np.radians(4.8)        # [inf: fitted to AFM Fig 1-1 front view (mean of the upper and lower outline slopes)]
# chord-line LE height at BL 0 [inf: fitted to the AFM Fig 1-1 front view registered on the main wheels (fix round 2; fix
# round 1 had 0.735 from 'belly = root lower surface', not drawn)]. The gear trunnion, wells and leg door move with it (WING_DZ).
Z_LE0_FR1 = 0.735
Z_LE0 = 0.835
WING_DZ = Z_LE0 - Z_LE0_FR1       # 0.100: everything placed against the fix-round-1 wing moves up by this
INC_ROOT, INC_TIP = np.radians(1.5), np.radians(-1.5)   # [inf: typical 3 deg washout]


def wing_chord(y):
    return C0 * (1 - K_CHORD * np.clip(np.abs(y), 0, WING_SEMI_REF))


def wing_x_le(y):
    return X_LE0 + np.abs(y) * np.tan(LE_SWEEP)


def wing_z_le(y):
    return Z_LE0 + np.abs(y) * np.tan(DIHEDRAL)


# root trailing-edge fillet: the TE curves aft into the fuselage to the AFM Fig 1-1 "18.3 ft" station [obs: dimension; inf: shape]
def te_fillet(y):
    y = np.abs(y)
    u = np.clip((1.15 - y) / 0.30, 0, 1.25)
    return 0.36 * u ** 1.8


# control surfaces [inf: AFM Fig 8-1 isometric: single-slotted flap over the inner ~60 % of the semi-span, aileron outboard]
Y_FLAP = (1.17, 3.48)
Y_AIL = (3.56, 5.30)
FLAP_X_LO, FLAP_X_LIP = 0.705, 0.765   # cove start on the lower surface / shroud lip on the upper surface (chord units)
AIL_XH = 0.755
BOOT_Y = (0.90, 5.35)             # wing de-ice boots [obs: AFM "Wing Deicer and Leading Edge"; inf: extent]
GEAR_BL = TRACK / 2               # 1.707

# ------------------------------------------------------------------------------------------------ V-tail
VT_DIHEDRAL = np.radians(38.0)    # [inf: fitted to AFM Fig 1-1 front, plan and side views]
VT_ROOT_Y, VT_ROOT_Z = 0.11, 1.650  # root reference point (chord line), inside the tail cone [inf: tip top = 3.322 m]
VT_TIP_Y = VTAIL_SPAN / 2 - 0.03    # tip chord station (tip cap adds ~0.03) [obs span]
VT_S_TIP = (VT_TIP_Y - VT_ROOT_Y) / np.cos(VT_DIHEDRAL)   # span along the surface
VT_LE_ROOT, VT_TE_ROOT = 8.64, 9.93   # root chord 1.29 m [inf: fitted to AFM Fig 1-1 side + plan]
VT_LE_TIP, VT_TE_TIP = 9.545, 10.248  # [inf: tip chord 0.70 m; TE tip = aft-most point (overall length)]
RV_XH = 0.66                      # ruddervator hinge (chord fraction) [inf: AFM Fig 8-1]
RV_S = (0.18, 2.40)               # ruddervator span along the surface [inf]

# ------------------------------------------------------------------------------------------------ nacelle (FJ33-5A)
# engine: length 42.7 in (108.5 cm), height 25.1 in, forward flange OD 18.4 in [obs: FAA TCDS E3GL]
ENGINE_LEN = 42.7 * IN
ENGINE_FLANGE_D = 18.4 * IN
# nacelle stations / heights [inf: fitted to AFM Fig 1-1 side view (top line, inlet face) and plan (width)]
NAC_X0, NAC_X1 = 5.865, 8.010     # inlet highlight, exhaust exit
_NAC = [  # (FS, centre z, half-width, half-height); the lower part merges into the fuselage crown (pylon)
    (5.865, 2.445, 0.338, 0.182),
    (5.95, 2.433, 0.350, 0.202),
    (6.10, 2.370, 0.356, 0.246),
    (6.30, 2.322, 0.356, 0.268),
    (6.60, 2.265, 0.354, 0.285),
    (7.00, 2.200, 0.345, 0.280),
    (7.40, 2.130, 0.312, 0.260),
    (7.70, 2.105, 0.262, 0.215),
    (7.90, 2.093, 0.215, 0.172),
    (8.010, 2.075, 0.180, 0.135),
]
nac_zc = pchip([(a, b) for a, b, c, d in _NAC])
nac_hw = pchip([(a, c) for a, b, c, d in _NAC])
nac_hh = pchip([(a, d) for a, b, c, d in _NAC])
NAC_N = 2.4                       # super-ellipse exponent of the nacelle section

# ------------------------------------------------------------------------------------------------ landing gear
MAIN_TIRE_D, MAIN_TIRE_W = 18.0 * IN, 5.6 * IN      # [obs: AFM 8-26 "18 x 5.5, 8-ply rating tubeless"]
NOSE_TIRE_D, NOSE_TIRE_W = 14.0 * IN, 5.0 * IN      # [obs: AFM 8-26 "5.00 x 5" -> 5.00-5 tyre, ~14 in OD]
X_MAIN_AXLE = 5.353               # [inf: fitted to the AFM Fig 1-1 side-view wheel centre]
X_NOSE_AXLE = 2.048               # [inf: fitted to the AFM Fig 1-1 side-view wheel centre]
WHEELBASE = X_MAIN_AXLE - X_NOSE_AXLE   # 3.305 [inf]; FAA ACD Wheelbase_ft 10.9 = 3.322 m [obs] (build_sf50.py check)

# light anchors (model coords) are defined in sf50_parts.py next to their lens geometry.
