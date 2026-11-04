"""Sheets of the SFO air traffic control tower (2016) and its base building, drawn from tools/buildings/spec_tower.json
(verified 2026-09-26, docs/research/buildings_tower.md section 12):
  BT-01  site / roof plan 1:400 (A3)              + overlay on NAIP 2024 (out/buildings/drawings/BT-01_naip.jpg)
  BT-02  elevations from the ESE (airside) and from the WNW (landside, glass ribbon between two blades) 1:200 (A1)
  BT-03  section through the shaft axis 1:400 (A3)

Heights: every vertical photo station is h_rim - k x D (k from the photos, D = cab-roof diameter). The spec's adopted trio
{rim 67.36 m, D 14.3 m, base-building roof 14.2 m} fails the photo-span / NAIP-ratio test of buildings_tower.md 12.3 by
~3 m: it is NOT a family and is not drawn. The two self-consistent families of 12.3 are drawn, neither preferred:
  family 1  D 15.2 m (15.1-15.3), rim 67.36 m = 221 ft;       base-building roof = rim - (3.46 D + 0.7) = 14.1 m
  family 2  D 14.5 m (14.3-14.75), rim 64.0 m (63-65), 221 ft at the mast tips;  base-building roof 13.1 m
Station h of the spec (anchored 67.36, D 14.3) -> family f: rim_f - (67.36 - h) x D_f / 14.3. Radii: A380 width ratios
x D_f, divided by 1.015 (shaft_profile_ratio_A380 verification: the ratios are ~1.5 % high); cab glass / roof radii
(Famartin pixel ratios) x D_f / 14.3.
"""
import numpy as np

import draw_data as D
from draw_lib import Sheet, hdg_vec, unit, FT
import geo_frame as GF

T = D.TV
H_SPEC, D_SPEC = 67.36, 14.3            # the spec's anchor (rim, cab-roof D) of every photo station
RAT = 1.015                             # A380 ratios ~1.5 % high (verification of shaft_profile_ratio_A380)
SPAN_K, PARAPET = 3.46, 0.7             # photo span rim -> base-building airside parapet = 3.46 D; roof ~0.7 m below it
FAM = {1: dict(D=15.2, rim=67.36, short='F1', label='family 1: D 15.2, rim 67.36 = 221 ft'),
       2: dict(D=14.5, rim=64.0, short='F2', label='family 2: D 14.5, rim 64.0, 221 ft at the masts')}
for _f in FAM.values():
    _f['s'] = _f['D'] / D_SPEC
    _f['ibf'] = _f['rim'] - (SPAN_K * _f['D'] + PARAPET)
F1, F2 = FAM[1], FAM[2]
F2LS = (0, (7, 2, 1.5, 2))              # family-2 outline: inf colour, dash-dot (family 1 = inf dashed, filled)
AXIS = np.array(T['position_shaft_axis']['value'], float)
CAB = np.array(T['position_cab_roof_centre']['value'], float)
MP = D.SPEC_T['model_proposal_provisional']
PROF = [(h, r) for h, r in MP['profile_r_of_h_m']]   # spec (h, r): round airside body; 60.9 / 61.0 = flare top deck
CABP = MP['cab']
DOF_TOWER = GF.wgs84_to_world(37.61578056, -122.38382778)   # DOF 06-323169 under the DOF convention (WGS 84, as BI/BD/BL)
OEAAA_13 = (-742.6, 335.7)                                     # the same numbers read as NAD83 (the 2008 OE/AAA letter)
# x bounds of the cab-roof centre (spec position_cab_roof_centre x_bounds): -744.1 / -739.6 for a 67.36 m rim, -741.3 / -737.1
# for 63.3 m, i.e. -0.69 / -0.62 m per m of rim; interpolated to the F2 rim 64.0 m [inf]
XB_F2 = tuple(round(b63 + (b67 - b63) * (64.0 - 63.3) / (67.36 - 63.3), 1) for b67, b63 in ((-744.1, -741.3), (-739.6, -737.1)))


def hf(h, f):
    """spec station h (anchored at 67.36 m with D 14.3) -> height in family f."""
    return f['rim'] - (H_SPEC - h) * f['s']


def shaft_outline(f):
    """half-profile (r, h) of the round airside body of family f from the base-building roof to the flare top deck."""
    pts = [(PROF[0][1] * f['s'], f['ibf'])]                      # Famartin base width at the base-building roof
    pts += [(r * f['s'] / RAT, hf(h, f)) for h, r in PROF[1:] if h <= 59.4]    # A380 ratios (1.5 % correction)
    # flare top: rounded shoulder from the widest corner (59.4) rising inwards to the deck at the plinth foot (60.9), shape
    # SHOULDER [obs photo t1]; replaces the spec's vertical lip (59.4 -> 60.9 at r 11.48 -> 11.0) and flat deck
    r0, h0 = pts[-1]; r1, h1 = PLINTH_D / 2 * f['D'] / PLINTH_REF, hf(60.9, f)
    for a, b in SHOULDER[1:]:
        pts.append((r0 - (r0 - r1) * a, h0 + (h1 - h0) * b))
    pts.append((PROF[-1][1] * f['s'] / RAT, hf(PROF[-1][0], f)))  # 61.0: the deck meets the cab (inside the plinth)
    return pts


def cab_outline(f):
    """cab glass bottom, glass top / fascia bottom, roof rim as (r, h) of family f (Famartin pixel ratios x D)."""
    return {k: (CABP[k][1] * f['s'], hf(CABP[k][0], f)) for k in ('glass_bottom', 'glass_top', 'roof_rim')}


def r_at(h_spec, f):
    """A380 radius of family f at the spec station h_spec."""
    return np.interp(h_spec, [p[0] for p in PROF[1:]], [p[1] for p in PROF[1:]]) * f['s'] / RAT


def body_outline(fam=1):
    """closed half-profile list (r, h) of the round body + cab (concentric) of family fam - for BX-01."""
    f = FAM[fam]; c = cab_outline(f)
    return shaft_outline(f) + [c['glass_bottom'], c['glass_top'], c['roof_rim']]


# Photo-derived surface features (reference photos t1 Basil D Soufi 2015 CC BY-SA 4.0, bearing 142; t2 / t3 / t4 Famartin
# 2025-08-12 CC BY-SA 4.0, bearings 126 / 319 / 338; refs/cache/buildings/review_likeness, reference only), read 2026-11-04:
# bearings are from the shaft axis, clockwise from north; every slot runs with its top towards smaller bearings (NNE on the
# airside face).
SLOT_PITCH = 27.7            # upper slots: azimuth spacing at mid-band, t1 row profiles 24-34 deg (mean 27.7) [obs photo t1]
SLOT_PHASE = 124.0           # one slot centred at bearing ~124 at mid-band (t1: 212 / 178 / 154 / 124 / 99 / 72) [obs photo t1]
SLOT_SWEEP = 20.0            # each upper slot sweeps ~20 deg of azimuth over the band [obs photo t1, rows 240-320: 13 deg / 6 m]
SLOT_W = 1.4                 # upper-slot width, m (t1: 15-25 px at 0.074 m/px) [obs photo t1]
SLOT_SKIP = (230.0, 335.0)   # no slots drawn in the landside ribbon / SW-wing sector (t4: only the 3 NE-flank slots show; the
                             # position at ~235 deg is hidden by the wing in t3 / t4 and outside t1 / t2: not confirmed) [obs photo t3 / t4]
LONG_SLOT = (137.0, 93.0)    # long slot: bearing at its foot / head (t1: u/R +0.13 -> +0.78 from 142; t2: -0.22 -> +0.52 from
                             # 126: both give foot ~135-139, head ~91-95 -> a ~44 deg helix) [obs photos t1 / t2]
LONG_W = 1.0                 # long-slot width, m [obs photo t1]
PLINTH_D, PLINTH_REF = 10.8, 15.2   # dark ring under the cab glass: 590 px of the 830-px (15.2 m) roof in t1, ~0.73 m high,
                                    # standing on the flare shoulder [obs photo t1; t3 shows it with a railing]
WING_TIP = (254.0, 14.0)     # SW wing outer tip in plan (bearing, m from the axis, F1 scale): the single point that reproduces
                             # BOTH oblique photos - t3: 14.5 m right of the cab centre and 7.0 m beyond the ribbon edge;
                             # t4: 15.7 m and 6.6 m (model: 14.5 / 7.6 and 15.7 / 5.8) [inf from obs photos t3 / t4]
RIB_BRG = 310.0              # ribbon facing, middle of the 300-320 deg photo range [obs photos]

# Review backlog (round 3, 2026-11-04), read on the same photos (t1-t5, refs/cache/buildings/review_likeness, reference only):
# Flare shoulder [obs photo t1, near-orthographic from 1.75 km; 0.073 m/px; 1.6 deg roll removed]: no vertical lip - the top
# rises inwards from the widest corner in a rounded shoulder: 0.15 / 0.35 / 0.48 / 0.86 / 1.15 m above the corner at 0.2 / 0.5 /
# 1.1 / 3.4 / 6.6 m in from the limb (6.6 m = the plinth foot). Drawn as these fractions of the spec rise 59.4 -> 60.9
# (the photo's 1.15 m in F1 metres is inside the spec's +-0.8 m) [shape obs, stations inf].
SHOULDER = ((0.0, 0.0), (0.03, 0.13), (0.076, 0.30), (0.167, 0.42), (0.515, 0.75), (1.0, 1.0))   # (run, rise) fractions
# Cladding grid [obs photo t2, 0.0315 m/px at the shaft]: circumferential panel rows 82-84 px apart = 6 rows between the seams
# 29.5 / 44.3 -> pitch 14.8 / 6 = 2.467 spec m; the same pitch lands on 49.2 / 56.6 (upper slot band), 24.6 / 41.8 (long slot)
# and 59.1 (flare corner): the slots start and end on row joints. Vertical joints ~0.46 m apart at the waist (t2 rows
# y 1600-1700) -> ~68 around [obs; count inf]; they lean 12-15 deg there, top towards smaller bearings, as the slots.
# Slots and joints share one twist rate: upper slots 20 deg / 7.6 m = 2.63, long slot 44 / 17.1 = 2.57 deg per spec metre
# (a constant-twist, ruled cladding; 2.6 deg/m x r 4.9 m -> 12.5 deg at the waist = the joint lean) [inf from obs].
# Published: ~1,500 curved trapezoidal panels with spiralling joints (MCN 2017); 68 x ~18 rows ~ 1,200 + flare / landside.
ROW0, ROW_PITCH = 29.5, 14.8 / 6        # spec metres
N_JOINTS, TWIST = 68, 2.6               # joints around; deg of azimuth per spec metre (bearing decreases upwards)
# Roof masts, 2025 set [obs photos t2 (11:57, bearing 126) / t3 (09:12, bearing 319), Famartin 2025-08-12]: each photo only
# gives true heights on its near half (the camera is ~12 deg below the rim, so far-side bases hide ~1.5-3 m behind the near rim).
# Near-side whips: bearing = right + acos(a / 0.92) (a = u / rim half-width, /1.027 for the nearer distance), masts on a ring
# at 0.92 x the rim radius; heights above the rim in F1 metres (rim = D 15.2 m: t2 474 px, t3 371 px). The short whips each
# photo shows on its far half fall on the other photo's near set (far branch): t2 1.7 / 1.3 / 1.8 m -> 279 / 300 / 340 deg
# (t3 P 283, O 291 - M 312, G 334 - D 346); t3 2.1 m and the thin whips -> 96 / 118 / 139 deg (t2 100, 111, 142); t3's thin
# whip at 188 deg matches t2's short item at the SW limb (a ~1.3 m pole). Whips seen: t3 14, t2 ~10; drawn 15 [count obs;
# bearings / heights inf, +-5 deg / +-0.3 m]. The landside whips reach ~4.5 m above the rim, the airside ones 2.3-3.5 m
# (2015 t1: 8 masts, ~3.3-3.6 m; the spec's mast-tip station 70.7 = rim + 3.0-3.35 spec m comes from those).
MAST_K = 0.92
MASTS = ((168, 3.4), (142, 3.5), (111, 2.3), (100, 3.2), (82, 3.0), (78, 2.5),                      # t2 near half (airside)
         (6, 4.0), (351, 3.2), (346, 4.5), (334, 3.6), (325, 4.7), (312, 2.8), (291, 2.5), (283, 4.5), (272, 4.2))   # t3
POLES = ((188, 1.3), (139, 1.6), (67, 0.8),                                                         # t2: pole, dome camera, lamp
         (16, 1.8), (342, 1.1), (322, 1.5), (297, 1.6), (276, 1.6), (257, 0.8))                     # t3: cameras, lamps, brackets
WING_POST = 1.9              # post with a diagonal stay on the SW wing top [obs photos t3 / t4 2025, t5 2018; position inf]
SLOT_GLAZED = (330.0, 30.0)  # NE-flank slots (bearings 345.5 / 13.2) carry a glazed pane in their lowest panel row, ~70 % of the
                             # slot width [obs photos t3 / t4]; none on the airside slots (t1 / t2); the slot at ~41 is at the limb
                             # in t3 / t4 (not resolved)
# Base building (IBF) faces [obs photos]:
# airside (SE) face, t2 (frontal, 8 deg off view A; 0.0299 m/px at the face, 244 m): parapet top y 2005, a metal panel band to
# y 2055 (1.50 m), a continuous dark glazing band to y 2183 (3.83 m), panels below (lower face hidden by the gates). Seen from
# u -12.9 (view A) to the NE end; SW of that it is hidden by a foreground building.
IBF_AIR_BAND = (1.50, 3.83, -12.9)      # panel band below the parapet, glazing band, observed SW end (u in view A)
# landside (NW) face, t4 (81 m, bearing 338; 0.0184 deg/px from the shaft limb and the ribbon base): a full-height curtain-wall
# bay (5 bays between 6 mullions, transoms ~1.2 m) in the same plane as the metal panels, under the parapet; its edges' rays
# (x 1152 / 1733) meet the NW face 8.1 and 29.2 m from its N corner (-742.5, 305.5) -> view B u -7.8 .. +13.3 (+-5 m: phone GPS,
# 40 deg oblique). In t4 its NE edge looks aligned with the ribbon only by perspective (the face is 6.3 m in front of the ribbon).
# Seen >= 9.6 m down from its head; its foot is below the frame [unk].
IBF_CW = (8.1, 29.2, 9.6, 5)
# NOT the base building: the tall dark louvred block beside the shaft (t1 left, t2 right, t3 right of the shaft) triangulates
# from the three photos to (-804, 259) (residual 1.3 m), 91 m NW of the axis at the SE end of the SFO Museum "Terminal 2
# AirTrain Station" polygon; the thin "canopy plates" in t1 lie on the same rays as that station's platform canopy (the V-strut
# roof in the t3 foreground). The 2015 jib davit on the SW flare deck (t1: post ~4.3 m, jib ~5 m) is not in the 2025 photos.
AIRTRAIN_BLOCK = (-804.3, 259.4)


def h2spec(h, f):
    """height in family f -> the spec station (anchored at 67.36 m, D 14.3)."""
    return H_SPEC - (f['rim'] - h) / f['s']


def r_h(h, f):
    """radius of the round body of family f at height h (family metres)."""
    return float(r_at(h2spec(h, f), f))


def surf_u(brg, r, right):
    """u of a point on the body surface at plan bearing brg (deg) and radius r, in a view with right-hand vector `right`."""
    return float(r * np.dot(hdg_vec(brg), right))


def visible(brg, right):
    """True if bearing brg faces the viewer (camera bearing = right-hand heading + 90)."""
    rh = np.degrees(np.arctan2(right[0], -right[1]))
    return np.cos(np.radians(brg - (rh + 90.0))) > 0.08


def slot_poly(right, f, b0, b1, h0, h1, w, n=14):
    """outline (u, h) of a helical slot from bearing b0 at h0 to b1 at h1, width w (m of arc), projected in the view."""
    hs = np.linspace(h0, h1, n)
    L, R = [], []
    for h in hs:
        t = (h - h0) / (h1 - h0); b = b0 + (b1 - b0) * t; r = r_h(h, f); dw = np.degrees(w / 2 / r)
        L.append((surf_u(b - dw, r, right), h)); R.append((surf_u(b + dw, r, right), h))
    return L + R[::-1]


def rib_shift(h, f, right):
    """u of the ribbon centre at height h: the ribbon faces RIB_BRG at ~1 m inside the round-body radius (as BT-01)."""
    return surf_u(RIB_BRG, r_h(h, f) - 1.0, right)


def ibf_u_extent(right):
    ring = np.asarray(D.sfom('Air Traffic Control Tower')[0][0], float)
    u = (ring - AXIS) @ right
    return float(u.min()), float(u.max())


def cab_offset(right):
    """u offset of the cab centre from the shaft axis in a view with right-hand world vector `right` [inf]."""
    return float(np.dot(CAB - AXIS, right))


def plinth(f):
    """dark ring under the cab glass: (half-width, bottom = flare top deck, top = glass sill) in family f [obs photo t1]."""
    return PLINTH_D / 2 * f['D'] / PLINTH_REF, hf(60.9, f), cab_outline(f)['glass_bottom'][1]


def draw_body(V, f, fill, uo, clip_right=None):
    """round body + cab of family f; clip_right: hide the body outline right of this u above the wing's foot (view B)."""
    sh = shaft_outline(f); c = cab_outline(f)
    pr, p0, p1 = plinth(f)
    if fill:
        sil = [(-r, h) for r, h in sh] + [(r, h) for r, h in reversed(sh)]
        V.poly(sil, 'inf', fc='#e8edf2', z=3)
        V.poly([(uo - pr, p0), (uo + pr, p0), (uo + pr, p1), (uo - pr, p1)], 'obs', fc='#3c4650', z=4.1, lw=0.5)
        gb, gt, rim = c['glass_bottom'], c['glass_top'], c['roof_rim']
        V.poly([(uo - gb[0], gb[1]), (uo + gb[0], gb[1]), (uo + gt[0], gt[1]), (uo - gt[0], gt[1])], 'inf', fc='#5f6d7a', z=4)
        V.poly([(uo - gt[0], gt[1]), (uo + gt[0], gt[1]), (uo + rim[0], rim[1]), (uo - rim[0], rim[1])], 'inf', fc='#f4f4f4', z=4)
    else:
        V.poly([(uo - pr, p0), (uo + pr, p0), (uo + pr, p1), (uo - pr, p1)], 'inf', fc='none', lw=0.5, z=5.5, ls=F2LS)
        for s in (-1, 1):
            V.line([(s * r, h) for r, h in sh], 'inf', lw=0.75, z=5.5, ls=F2LS)
            V.line([(uo + s * c[k][0], c[k][1]) for k in ('glass_bottom', 'glass_top', 'roof_rim')], 'inf', lw=0.75, z=5.5, ls=F2LS)
        rim = c['roof_rim']; V.line([(uo - rim[0], rim[1]), (uo + rim[0], rim[1])], 'inf', lw=0.75, z=5.5, ls=F2LS)


def draw_blades(V, f, hb, ht, w0, w1, right):
    """landside glass ribbon in its channel between the NE blade (left, looking ESE) and the SW wing (right), family f.
    Form from photos t3 / t4 (Famartin 2025-08-12, CC BY-SA 4.0, oblique views from bearings 319 / 338) [obs, photo];
    proportions from those oblique views (not dimensioned in any source) [inf]. Every u is shifted by the ribbon's plan
    position (bearing 310, as BT-01): u(h) = rib_shift(h)."""
    rim = cab_outline(f)['roof_rim'][1]; deck = hf(60.9, f)
    sh = lambda u, h: (u + rib_shift(h, f, right), h)
    S = lambda pts: [sh(u, h) for u, h in pts]
    # ribbon (glass, LED-backlit) with its mullion grid: 2 columns, ~25 rows (photo count) [obs]
    V.poly(S([(-w0 / 2, hb), (w0 / 2, hb), (w1 / 2, ht), (-w1 / 2, ht)]), 'obs', fc='#2b3d55', z=5)
    V.line(S([(0, hb), (0, ht)]), 'obs', lw=0.35, z=5.2, color='#9fb3c8')
    for k in range(1, 25):
        h = hb + (ht - hb) * k / 25; w = w0 + (w1 - w0) * k / 25
        V.line(S([(-w / 2, h), (w / 2, h)]), 'obs', lw=0.25, z=5.2, color='#9fb3c8')
    # NE blade: narrow, sharp-edged, a full-height strip beside the ribbon ending in a pointed tip at about the flare rim
    tip = deck + 1.2
    ne = [(-w0 / 2, hb), (-w0 / 2 - 1.0, hb), (-w1 / 2 - 1.8, ht), (-w1 / 2 - 1.0, tip), (-w1 / 2, ht)]
    V.poly(S(ne), 'inf', fc='#c9d2dc', z=5.1)
    V.line(S([(-w0 / 2 - 0.5, hb), (-w1 / 2 - 0.9, ht)]), 'inf', lw=0.3, z=5.2)           # crease
    # SW wing: broad, horizontally louvred face, flat top, rounded outer corner, a crease diverging upwards; its outer tip in
    # this view is the projection of the plan tip WING_TIP (scaled to family f)
    wt = surf_u(WING_TIP[0], WING_TIP[1] * f['s'] * D_SPEC / 15.2, right)
    x0 = w0 / 2 + 1.4 + rib_shift(hb, f, right)
    out = [(x0 + (wt - x0) * t ** 1.8, hb + (ht - 2.5 - hb) * t) for t in np.linspace(0.0, 1, 13)]
    arc = [(wt - 1.2 + 1.2 * np.cos(a), ht - 1.2 + 1.2 * np.sin(a)) for a in np.linspace(0, np.pi / 2, 6)]
    inner = lambda h: w0 / 2 + (w1 - w0) / 2 * (h - hb) / (ht - hb) + rib_shift(h, f, right)
    sw = [(inner(hb), hb)] + out + arc + [(inner(ht), ht)]
    V.poly(sw, 'inf', fc='#d6dde5', z=5.6)
    for k in range(1, 30):
        h = hb + (ht - hb) * k / 30
        xo = np.interp(h, [p[1] for p in out], [p[0] for p in out]); xi = inner(h)
        if xo > xi + 0.6: V.line([(xi + 0.2, h), (xo - 0.2, h)], 'inf', lw=0.18, z=5.7, color='#9aa7b4')
    V.line(S([(w0 / 2 + 0.7, hb), (w1 / 2 + 2.6, ht)]), 'inf', lw=0.3, z=5.7)              # crease
    # post with a diagonal stay on the wing top, about 3/5 of the way out [obs photos t3 / t4 2025, t5 2018; position inf]
    up = inner(ht) + 0.6 * (wt - inner(ht)); pt = ht + WING_POST * f['D'] / 15.2
    V.line([(up, ht), (up, pt)], 'obs', lw=0.7, z=5.8, ls='-')
    V.line([(up, pt - 0.2), (up - 1.6, ht)], 'obs', lw=0.25, z=5.8, ls='-')
    V.leader((up, pt), 14, 10, f'post with a stay on the SW wing top, ~{WING_POST} m [obs photos t3 / t4 2025, t5 2018;\n'
             'position inf]', 'obs', fs=3.9)
    V.leader(sh(-w1 / 2 - 1.0, tip), -20, 60, f'NE blade: narrow, sharp-edged; pointed tip at about the flare rim\n'
             f'(+{tip:.1f}; photos read 0-2.4 m above it) [obs photo t4, low]', 'inf', fs=4.0)
    V.leader((wt - 1.5, ht - 6), 22, 8, f'SW wing: broad blade, horizontally louvred face, flat top, rounded outer\ncorner [obs photo t3 / t4]. '
             f'Outer tip drawn at u {wt:+.1f}: the projection of the plan tip\n{WING_TIP[0]:.0f} deg / {WING_TIP[1]:.1f} m from the axis, the point '
             'that reproduces both\noblique photos (t3: 14.5 m right of the cab centre, 7.0 m beyond the\nribbon; t4: 15.7 / 6.6 m) [inf]. From this '
             'bearing (297.7) the round\nflare (R 12.0) stays outside it; if the wing wrapped south to ~208 deg\n(not excluded by t3 / t4) its '
             'silhouette could reach u +13.6 [inf].\nPlan depth unknown [unk]', 'inf', fs=3.9)
    V.line([(wt + 0.4, ht - 1.2), (13.6, ht - 1.2)], 'inf', lw=0.5, ls=(0, (1, 1.5)), z=5.8)
    V.leader(sh(w0 / 2 + 0.6, hb + 19), 44, 0, f'glass ribbon (LED-backlit, "waterfall"): 147 ft = {ht - hb:.2f} m tall [pub];\n'
             f'width {w0} -> {w1} m bottom -> top [obs, low; T2 AirTrain photo];\n2 columns x ~25 rows [obs photos]; set in a flat-faced '
             'channel between\nthe two blades [obs photo]; start / end levels not published:\ndrawn from the base-building roof [inf]; head '
             'drawn level: in t4 the\nhead and the mullion rows slope alike (0.18-0.19 px/px), so the\nslant seen there is perspective [obs photo];\n'
             f'faces bearing {RIB_BRG:.0f} (BT-01), so it sits {rib_shift(ht, f, right):+.1f} m off the axis at the top [inf]', 'obs', fs=4.0)
    V.dim(sh(-w0 / 2, hb - 1.0), sh(w0 / 2, hb - 1.0), -2.5, f'{w0} [obs]', 'obs', fs=4.0)
    V.dim(sh(-w1 / 2, ht - 2.0), sh(w1 / 2, ht - 2.0), 0, f'{w1} [obs]', 'obs', fs=4.0, ext=False)


def draw_slots(V, f, right):
    """upper band of discrete inclined slots and the long helical slot (family f), wherever they face the viewer."""
    a, b = (hf(x, f) for x in T['h_upper_slots']['value'])
    n = int(round(360 / SLOT_PITCH))
    shown = 0
    for k in range(n):
        bm = (SLOT_PHASE + k * 360.0 / n) % 360
        if SLOT_SKIP[0] <= bm <= SLOT_SKIP[1] or not visible(bm, right): continue
        V.poly(slot_poly(right, f, bm + SLOT_SWEEP / 2, bm - SLOT_SWEEP / 2, a, b, SLOT_W), 'inf', fc='#4a5663', z=4.2, lw=0.3)
        if bm >= SLOT_GLAZED[0] or bm <= SLOT_GLAZED[1]:
            # glazed pane in the slot's lowest panel row (one row pitch), inset 0.25 m [obs photos t3 / t4]
            g0, g1 = a + 0.25 * f['s'], hf(h2spec(a, f) + ROW_PITCH, f) - 0.25 * f['s']
            t0, t1 = (g0 - a) / (b - a), (g1 - a) / (b - a)
            b0 = bm + SLOT_SWEEP / 2 - SLOT_SWEEP * t0; b1 = bm + SLOT_SWEEP / 2 - SLOT_SWEEP * t1
            V.poly(slot_poly(right, f, b0, b1, g0, g1, 0.7 * SLOT_W, n=6), 'obs', fc='#a9c3d6', z=4.25, lw=0.3)
        shown += 1
    a2, b2 = (hf(x, f) for x in T['h_lower_slot']['value'])
    if visible(sum(LONG_SLOT) / 2, right):
        V.poly(slot_poly(right, f, LONG_SLOT[0], LONG_SLOT[1], a2, b2, LONG_W, n=24), 'inf', fc='#4a5663', z=4.2, lw=0.3)
    return shown, (a, b), (a2, b2)


def draw_cladding_grid(V, f, right):
    """panel rows (ROW_PITCH) and helical vertical joints (N_JOINTS, TWIST) on the round body of family f, thin and light
    [rows / spacing obs photo t2; twist inf from the slots; joint phase unknown: one joint drawn along the long-slot foot]."""
    lo, hi = h2spec(f['ibf'], f) + 0.3, 59.4 - 0.3
    for k in range(-12, 13):
        h = ROW0 + k * ROW_PITCH
        if lo < h < hi and min(abs(h - s) for s in T['h_seams']['value']) > 0.3:
            r = r_at(h, f); V.line([(-r, hf(h, f)), (r, hf(h, f))], 'inf', lw=0.15, z=3.6, color='#aeb9c4', ls='-')
    hs = np.linspace(lo - 0.3, 59.4, 60)
    for j in range(N_JOINTS):
        seg = []
        for h in list(hs) + [None]:
            b = None if h is None else LONG_SLOT[0] + j * 360.0 / N_JOINTS - TWIST * (h - T['h_lower_slot']['value'][0])
            if b is not None and visible(b, right):
                seg.append((surf_u(b, r_at(h, f), right), hf(h, f)))
            elif seg:
                if len(seg) > 1: V.line(seg, 'inf', lw=0.12, z=3.6, color='#aeb9c4', ls='-')
                seg = []


def mast_u(b, f, right, uo):
    """u of a roof mast at bearing b (from the cab centre) on the ring MAST_K x the rim radius of family f."""
    return uo + MAST_K * cab_outline(f)['roof_rim'][0] * float(np.dot(hdg_vec(b), right))


def draw_masts(V, f, right, uo):
    """2025 roof masts (whips) and short camera / lamp / bracket poles of family f [count obs photos t2 / t3; positions inf]."""
    rim = cab_outline(f)['roof_rim'][1]; k = f['D'] / 15.2
    for b, hm in MASTS:
        V.line([(mast_u(b, f, right, uo), rim), (mast_u(b, f, right, uo), rim + hm * k)], 'inf', lw=0.45, z=4, ls='-')
    for b, hm in POLES:
        u = mast_u(b, f, right, uo)
        V.line([(u, rim), (u, rim + hm * k)], 'inf', lw=0.8, z=4, ls='-')
        V.mark((u, rim + hm * k), 'inf', marker='o', ms=1.3, fc='none', z=4.1)


def ibf_face_u(s, right):
    """u in a view of the point s metres along the base building's NW face from its N corner (towards the W corner)."""
    ring = np.asarray(D.sfom('Air Traffic Control Tower')[0][0], float)
    e = unit(ring[1] - ring[0])
    return float((ring[0] + e * s - AXIS) @ right)


def draw_ibf_faces(V, right, ribbon, u0, u1):
    """photo features of the base-building faces (F1 heights): airside parapet + dark glazing band (view A), landside
    curtain-wall bay (view B) [obs photos t2 / t4; extents / heights relative to the parapet / roof]."""
    par = F1['ibf'] + PARAPET
    if not ribbon:
        V.poly([(u0, F1['ibf']), (u1, F1['ibf']), (u1, par), (u0, par)], 'inf', fc='#f7f7f7', z=3.5, lw=0.4)
        gt = par - IBF_AIR_BAND[0]; gb = gt - IBF_AIR_BAND[1]; us = IBF_AIR_BAND[2]
        V.poly([(us, gb), (u1, gb), (u1, gt), (us, gt)], 'obs', fc='#3d4a57', z=1.7, lw=0.4)
        V.poly([(u0, gb), (us, gb), (us, gt), (u0, gt)], 'unk', fc='none', z=1.7, lw=0.4)
        V.leader((us + 14, gb + 0.6), 6, -14, f'airside face: parapet +{par:.1f} = rim - 3.46 D [obs photo span], metal panel band '
                 f'{IBF_AIR_BAND[0]:.1f} m,\ncontinuous dark glazing band {IBF_AIR_BAND[1]:.1f} m (+{gb:.1f} to +{gt:.1f}) [obs photo t2, '
                 f'heights below the parapet;\nabsolute inherits F1]; seen from u {us:+.1f} to the NE end, hidden further SW '
                 '(dotted) [unk];\nlower face hidden by the gates in t2 [unk]', 'obs', fs=3.9)
    else:
        s0, s1, hv_, nb = IBF_CW
        ua, ub = sorted((ibf_face_u(s0, right), ibf_face_u(s1, right)))
        top = F1['ibf']; bot = top - hv_
        V.poly([(ua, bot), (ub, bot), (ub, top), (ua, top)], 'obs', fc='#8fa79e', z=1.7, lw=0.4)
        V.poly([(ua, 0), (ub, 0), (ub, bot), (ua, bot)], 'unk', fc='none', z=1.7, lw=0.4)
        for i in range(1, nb):
            u = ua + (ub - ua) * i / nb; V.line([(u, bot), (u, top)], 'obs', lw=0.3, z=1.8, color='#4b5d57')
        for h in np.arange(top - 1.2, bot, -1.2):
            V.line([(ua, h), (ub, h)], 'obs', lw=0.18, z=1.8, color='#4b5d57')
        V.leader(((ua + ub) / 2 + 3, bot + 2), 10, -24, f'landside face: curtain-wall bay, 5 bays, transoms ~1.2 m, under the parapet '
                 f'[obs photo t4];\nplan {s0}-{s1} m from the N corner of the NW face = u {ua:+.1f} .. {ub:+.1f} (+-5 m) [inf: t4 rays, '
                 'phone GPS,\n40 deg oblique]; seen >= 9.6 m down, foot below the frame (dotted) [unk]. Not centred\non the ribbon: '
                 'in t4 its NE edge lines up with the ribbon only by perspective', 'obs', fs=3.9)


def draw_tower_elev(V, right, ribbon=False):
    """elevation of the tower in view V: u = metres along `right` (world unit vector) from the shaft axis.
    Family 1 filled (detail drawn on it), family 2 as a dash-dot outline; levels: family 1 right, family 2 left."""
    u0, u1 = ibf_u_extent(right); uo = cab_offset(right)
    V.ax.fill_between([u0 - 14, u1 + 14], [-2.5, -2.5], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(u0 - 14, 0), (u1 + 14, 0)], 'pub', lw=0.8)
    lo, hi = T['h_ibf_roof']['range']
    V.ax.fill_between([u0, u1], [lo, lo], [hi, hi], color='#f3d9bf', lw=0, zorder=1.2, alpha=0.7)
    V.poly([(u0, 0), (u1, 0), (u1, F1['ibf']), (u0, F1['ibf'])], 'inf', fc='#f7f7f7', z=1.5)
    V.line([(u0, F2['ibf']), (u1, F2['ibf'])], 'inf', lw=0.6, ls=F2LS, z=1.6)
    V.text(((u0 + u1) / 2 + 12 * np.sign(u0 + u1 + 1e-9), 6.0), 'base building (IBF)\n3 storeys [pub], ~44,000 sq ft [pub]\nfloor levels not published', 'pub', fs=4.0)
    V.dim((u0, 0), (u1, 0), -6, f'{u1 - u0:.2f} m  long face [obs SFOM footprint]', 'obs')
    draw_body(V, F1, True, uo)
    draw_body(V, F2, False, cab_offset(right))
    draw_ibf_faces(V, right, ribbon, u0, u1)
    draw_cladding_grid(V, F1, right)
    c1 = cab_outline(F1); rim = c1['roof_rim'][1]
    draw_masts(V, F1, right, uo)
    um = max(MASTS, key=lambda m: m[1] if visible(m[0], right) else 0)
    if not ribbon:
        V.leader((mast_u(um[0], F1, right, uo), rim + um[1] * F1['D'] / 15.2 - 0.3), -24, 8,
             f'roof masts (both views), 2025 set: {len(MASTS)} whips + {len(POLES)} camera / lamp / bracket poles (dots), on a ring at '
             f'{MAST_K} x the rim radius\n[count obs photos t2 / t3, Famartin 2025; bearings / heights inf, each from the photo '
             'that sees it on its near half].\nLandside whips up to ~4.7 m above the rim, airside 2.3-3.5 m; the levels\' '
             '"mast tips" = the spec station (2015 masts,\n~3.3-3.6 m in t1). The 2015 jib davit on the SW deck (t1) is not in '
             'the 2025 photos: not drawn', 'inf', fs=3.9)
    for h in T['h_seams']['value']:
        r = r_at(h, F1); V.line([(-r, hf(h, F1)), (r, hf(h, F1))], 'inf', lw=0.4, z=4)
    nsl, (a, bq), (a2, b2) = draw_slots(V, F1, right)
    if not ribbon:
        um = surf_u(sum(LONG_SLOT) / 2, r_h((a2 + b2) / 2, F1), right)
        V.leader((um, (a2 + b2) / 2), 16, 4, f'single long helical slot {a2:.1f}-{b2:.1f} m (F1): sweeps ~44 deg of azimuth,\nbearing '
                 f'{LONG_SLOT[0]:.0f} at its foot -> {LONG_SLOT[1]:.0f} at its head, ~{LONG_W} m wide [inf from obs photos\nt1 / t2: u/R '
                 '+0.13 -> +0.78 seen from 142, -0.22 -> +0.52 from 126]', 'inf', fs=4.0)
        ur = surf_u(SLOT_PHASE, r_h((a + bq) / 2, F1), right)
        V.leader((ur, (a + bq) / 2), 30, 10, f'upper band: {int(round(360 / SLOT_PITCH))} positions every {SLOT_PITCH} deg, none in the landside\n'
                 f'ribbon / wing sector -> {nsl} visible here; each ~{SLOT_W} m wide, sweeping ~{SLOT_SWEEP:.0f} deg\nbetween the band seams, '
                 'tops towards the NNE [obs photo t1: 6 slots\nacross the visible half; t2: 5] [inf: count / phase]; no glazed panes on '
                 'the airside slots (t1 / t2)', 'inf', fs=4.0)
        rr = ROW0 + 4 * ROW_PITCH; ug = surf_u(LONG_SLOT[0] - 40, r_h(hf(rr, F1), F1), right)
        V.leader((ug, hf(rr, F1)), -54, 6, f'cladding grid (thin): panel rows every {ROW_PITCH:.2f} spec m = {ROW_PITCH * F1["s"]:.2f} m (F1) - 6 '
                 'between the seams; the slot ends\nlie on rows [obs photo t2]; ~1,500 trapezoidal ACM panels with spiralling joints '
                 f'[pub MCN]: ~{N_JOINTS} joints\naround (~0.46 m apart at the waist) [obs photo t2; count inf], each turning '
                 f'{TWIST} deg of azimuth per spec metre,\nthe twist of both slot kinds (12-15 deg lean at the waist) [inf]; joint '
                 'phase unknown', 'inf', fs=3.9)
    else:
        w0, w1 = T['ribbon_width']['value']; rh = T['ribbon_height']['value_m']
        draw_blades(V, F1, F1['ibf'], F1['ibf'] + rh, w0, w1, right)
        V.leader((surf_u((SLOT_PHASE + 8 * 360 / 13) % 360, r_h(52.5, F1), right), 52.5), -34, 14,
                 f'{nsl} upper slots visible on the NE flank, left of the ribbon\n[obs photos t3 / t4: 2-3 slots]; none in the ribbon / wing sector;\n'
                 'each has a glazed pane in its lowest panel row (light) [obs photos t3 / t4]', 'inf', fs=4.0)
    # diameters of both families at their stations (dimension line on family 1)
    fsd = 3.8 if V.scale >= 400 else 4.3
    d1, d2 = F1['D'], F2['D']
    V.dim((uo - d1 / 2, rim + 0.2), (uo + d1 / 2, rim + 0.2), 4.0, f'cab roof D {d1} (F1) / {d2} (F2) [inf]; measured 14.3 +-1.0, EXIF 14.75 +-0.5 [obs]', 'inf', fs=fsd)
    for key, hs, A380, txt_off in (('d_cab_glass_top', CABP['glass_top'][0], False, 0.4), ('d_cab_glass_bottom', CABP['glass_bottom'][0], False, -0.4),
                                   ('flare', 59.4, True, 0), ('waist', T['h_narrowest']['value'], True, 0)):
        if A380:
            r1, r2 = r_at(hs, F1), r_at(hs, F2)
        else:
            r1, r2 = T[key]['value'] / 2 * F1['s'], T[key]['value'] / 2 * F2['s']
        o = uo if not A380 else 0.0
        nm = {'d_cab_glass_top': 'glass head', 'd_cab_glass_bottom': 'glass sill'}.get(key, key)
        V.dim((o - r1, hf(hs, F1)), (o + r1, hf(hs, F1)), 0, f'{nm} D {2 * r1:.1f} / {2 * r2:.1f} [inf]', 'inf', fs=fsd, ext=False,
              text_off=txt_off if txt_off else 1.0)
    rb1 = PROF[0][1] * F1['s']
    V.dim((-rb1, F1['ibf'] + 0.4), (rb1, F1['ibf'] + 0.4), 0, f'D {2 * rb1:.1f} / {2 * PROF[0][1] * F2["s"]:.1f} [inf]', 'inf', fs=fsd, ext=False)
    # levels: family 1 (right), family 2 (left)
    fsl = 3.7 if V.scale >= 400 else 4.4
    sx = 16.0
    V.level(sx, T['h_dof_envelope']['value_m'], '+74.68  245 ft AGL = FAA DOF / 2008 envelope [pub] - upper bound, not as-built', 'pub', len_mm=3, fs=fsl, u_line=12.0)

    def lv(f, side):
        c = cab_outline(f); m = c['roof_rim'][1] + (T['h_antenna_tips']['value'] - H_SPEC) * f['s']
        L = [(m, f'+{m:.1f} mast tips' + (' = 221 ft' if f is F2 else ' (233 ft)')), (c['roof_rim'][1], f'+{c["roof_rim"][1]:.2f} roof rim' + (' = 221 ft' if f is F1 else '')),
             (c['glass_top'][1], f'+{c["glass_top"][1]:.1f} cab glass head'), (c['glass_bottom'][1], f'+{c["glass_bottom"][1]:.1f} cab glass sill'),
             (hf(61.0, f), f'+{hf(61.0, f):.1f} cab floor (sill band)'), (hf(59.4, f), f'+{hf(59.4, f):.1f} flare, widest'),
             (hf(56.8, f), f'+{hf(49.2, f):.1f}-{hf(56.8, f):.1f} band of inclined slots'), (hf(44.3, f), f'+{hf(44.3, f):.1f} seam'),
             (hf(29.5, f), f'+{hf(29.5, f):.1f} seam'), (hf(T['h_narrowest']['value'], f), f'+{hf(T["h_narrowest"]["value"], f):.1f} waist'),
             (f['ibf'], f'+{f["ibf"]:.1f} base-building roof = rim - (3.46 D + 0.7)')]
        yprev = 1e9 if side == 'right' else 1e9
        for h, s in L:
            y = min(h, yprev - V.mm(fsl * 0.55))
            if side == 'right':
                V.level(sx, y, s + ' [inf]', 'inf', len_mm=3, fs=fsl, u_line=max(u1, 12.6) if h < 20 else 12.6)
            else:
                V.level(-sx + 1.5, y, f['short'] + ': ' + s, 'inf', side='left', len_mm=3, fs=fsl - 0.1, u_line=min(u0, -12.6) if h < 20 else -12.6)
            yprev = y
    V.text((sx, 78.0), 'F1 (filled): D 15.2, rim 67.36 = 221 ft', 'inf', fs=fsl + 0.4, ha='left', weight='bold')
    V.text((-sx + 1.5, 78.0), 'F2 (dash-dot): D 14.5, rim 64.0', 'inf', fs=fsl + 0.4, ha='right', weight='bold')
    lv(F1, 'right'); lv(F2, 'left')
    V.text((0, -9.0), f'u = 0: shaft axis [inf] (-740.5, 324.5); cab centre (-739.0, 323.5) [inf]: offset 1.8 m (1.5 E, 1.0 N) from '
           f'the axis [inf], {uo:+.1f} m in this view', 'inf', fs=3.8)


def sheet_plan(variant='vector', dev=None):
    S = Sheet('BT-01', 'Air traffic control tower: site and roof plan', 'A3', variant=variant,
              subtitle='Spec: tools/buildings/spec_tower.json; note docs/research/buildings_tower.md (12: verification)')
    V = S.view(0, 0, S.vw, S.vh, 400, (-734, 331), kind='plan', frame=True)
    if variant != 'vector': V.background()
    V.grid(10)
    for r in D.complex_rings():
        V.ctx(r, fc='#f4f4f4' if variant == 'vector' else 'none', z=0.3)
    V.text((-783, 300), 'terminal complex\n(SFO Museum, context)', 'unk', fs=3.6, color='#888888', style='normal')
    ring = np.asarray(D.sfom('Air Traffic Control Tower')[0][0], float)
    V.poly(ring, 'obs', fc='#dfe8f1' if variant == 'vector' else 'none', z=2, lw=0.8)
    for i in range(4):
        p, q = ring[i], ring[(i + 1) % 4]
        V.dim(p, q, 5, f'{float(np.hypot(*(q - p))):.2f} [obs]', 'obs', fs=4.2)
    V.leader((-752, 340), -40, 4, 'base building (IBF): footprint = SFO Museum atc ring [obs]\n44.95 x 27.20 m, long axis 27.7 deg [obs]\n'
             f'roof +{F1["ibf"]:.1f} (F1) / +{F2["ibf"]:.1f} (F2) [inf]; 3 storeys [pub]', 'obs', fs=4.0)
    # flare and shaft circles of both families on the inferred axis
    for f, ls in ((F1, None), (F2, F2LS)):
        V.circle(AXIS, r_at(59.4, f), 'inf', z=4, lw=0.5, ls=ls)
        V.circle(AXIS, PROF[0][1] * f['s'], 'inf', z=4, lw=0.4, ls=ls)
    V.leader(AXIS + np.array([-12.0, 0]), -32, 26, f'flare, widest: D {2 * r_at(59.4, F1):.1f} (F1, dashed) / {2 * r_at(59.4, F2):.1f} (F2, dash-dot) [inf];\n'
             f'shaft at the base-building roof D {2 * PROF[0][1] * F1["s"]:.1f} / {2 * PROF[0][1] * F2["s"]:.1f} [inf]\n'
             '(photo ratio x D; spec 22.6 +-1.5 / 10.3 at D 14.3);\ncircles centred on the inferred axis (-740.5, 324.5) [inf]', 'inf', fs=3.9)
    # landside ribbon channel and blades (form from photos; plan geometry not measured)
    e = hdg_vec(310); sd = hdg_vec(40); R = r_at(59.4, F1); w1 = T['ribbon_width']['value'][1]
    base = AXIS + e * (R - 1.0)
    V.line([base + sd * w1 / 2, base - sd * w1 / 2], 'unk', lw=1.4, z=5)
    ne = [AXIS + e * np.sqrt(R ** 2 - (w1 / 2 + 1.2) ** 2) + sd * (w1 / 2 + 1.2), base + sd * w1 / 2, AXIS + e * (R + 1.6) + sd * (w1 / 2 + 0.5)]
    V.poly(ne, 'unk', fc='#e4e4e4', z=5)
    tip = AXIS + hdg_vec(WING_TIP[0]) * WING_TIP[1]
    sw = [base - sd * w1 / 2, AXIS + hdg_vec(285) * (R + 0.9), AXIS + hdg_vec(266) * (R + 1.7), tip,
          AXIS + hdg_vec(246) * (R + 0.9), AXIS + hdg_vec(240) * R]
    V.poly(sw, 'unk', fc='#e4e4e4', z=5)
    V.mark(tip, 'inf', marker='o', ms=2.4)
    V.leader(tip, -18, -14, f'SW wing tip {WING_TIP[0]:.0f} deg, {WING_TIP[1]:.1f} m from the axis (2 m outside the flare)\n'
             '[inf: the one point that reproduces photos t3 (319 deg) and t4 (338 deg):\n14.5 / 15.7 m right of the cab centre, 7.0 / 6.6 m beyond the ribbon]', 'inf', fs=3.6)
    for b in (300, 320):
        V.line([AXIS, AXIS + hdg_vec(b) * 30], 'obs', lw=0.4, ls=(0, (3, 2)))
    V.leader(AXIS + e * (R + 1.0), -6, 30, 'landside: glass ribbon (faces ~300-320 deg [obs, photos]) in a flat channel\n'
             'between a narrow NE blade and a broad, louvred SW wing [obs photos t3 / t4];\n'
             'plan shape SCHEMATIC at the flare level - depth / width not measured [unk]', 'unk', fs=3.8)
    # cab roof caps of both families
    V.circle(CAB, F1['D'] / 2, 'inf', z=5, lw=0.9)
    V.circle(CAB, F2['D'] / 2, 'inf', z=5, lw=0.7, ls=F2LS)
    V.mark(CAB, 'inf', marker='+', ms=6)
    V.mark(AXIS, 'inf', marker='x', ms=4)
    # roof masts (2025 set, F1 cab) [count obs photos t2 / t3; bearings inf]
    rr = MAST_K * cab_outline(F1)['roof_rim'][0]
    for b, _ in MASTS:
        V.mark(CAB + hdg_vec(b) * rr, 'inf', marker='o', ms=1.1, fc='#b35806')
    for b, _ in POLES:
        V.mark(CAB + hdg_vec(b) * rr, 'inf', marker='o', ms=1.1, fc='none')
    V.leader(CAB + hdg_vec(100) * rr, 46, 14, f'roof masts, 2025: {len(MASTS)} whips (filled) + {len(POLES)} camera / lamp poles (hollow)\n'
             f'on a ring {MAST_K} x the F1 rim radius [count obs photos t2 / t3; bearings inf] (BT-02)', 'inf', fs=3.5)
    # base-building faces seen in photos (BT-02): airside glazing band (SE face), landside curtain-wall bay (NW face) [approximate]
    ring_ = np.asarray(D.sfom('Air Traffic Control Tower')[0][0], float); cen = ring_.mean(0)
    def face_seg(i, s0, s1, off=0.9):
        p, q = ring_[i], ring_[(i + 1) % 4]; e = unit(q - p); n = np.array([e[1], -e[0]])
        if np.dot(n, p - cen) < 0: n = -n
        return [p + e * s0 + n * off, p + e * s1 + n * off]
    se = 2; rA = hdg_vec(27.7)
    p, q = ring_[se], ring_[(se + 1) % 4]; L = float(np.hypot(*(q - p)))
    up_, uq_ = float((p - AXIS) @ rA), float((q - AXIS) @ rA)
    s_obs = (IBF_AIR_BAND[2] - up_) / (uq_ - up_) * L
    V.line(face_seg(se, s_obs, L), 'obs', lw=1.8, color='#3d4a57', ls='-', z=4)
    V.line(face_seg(se, 0, s_obs), 'unk', lw=1.0, z=4)
    V.leader(face_seg(se, s_obs, L)[0] * 0.5 + face_seg(se, s_obs, L)[1] * 0.5, 16, -10,
             'airside face: continuous dark glazing band under a 1.5 m panel band\n[obs photo t2]; dotted = hidden in t2 [unk] (BT-02 A)', 'obs', fs=3.5)
    cw = face_seg(0, IBF_CW[0], IBF_CW[1], off=1.8)
    V.line(cw, 'obs', lw=1.8, color='#6f8f84', ls='-', z=4)
    V.leader(cw[0] * 0.45 + cw[1] * 0.55, -36, 6, f'landside face: curtain-wall bay {IBF_CW[0]}-{IBF_CW[1]} m from the\n'
             'N corner (+-5 m) [obs photo t4; extent inf] (BT-02 B)', 'obs', fs=3.5)
    V.poly([(-744, 321.5), (-734, 321.5), (-734, 325.5), (-744, 325.5)], 'inf', fc='none', z=4, lw=0.4)
    V.leader(CAB + np.array([5.0, -5.0]), 22, 40, f'cab-roof cap D {F1["D"]} (F1) / {F2["D"]} (F2) [inf];\nmeasured 14.3 +-1.0, EXIF 14.75 +-0.5 [obs]\n'
             'centre (-739, 323.5) [inf]: z 323.5 +-2 from four NAIP epochs [obs];\nx -739 +-5 [inf]; small box = the adopted tolerance', 'inf', fs=4.0)
    # x bounds: from the NAIP 2022 sensor field of view AND an assumed rim height -> one pair per family [inf]
    for x, s, ls, dy in ((-744.1, 'F1 (rim 67.36): x >= -744.1 hard', (0, (2, 2)), 0), (-739.6, 'F1: >= -739.6 likely', (0, (1, 2)), -4.5),
                         (XB_F2[0], f'F2 (rim 64.0): x >= {XB_F2[0]:.1f} hard (rim 63.3: -741.3)', F2LS, -9.0),
                         (XB_F2[1], f'F2: >= {XB_F2[1]:.1f} likely (rim 63.3: -737.1)', (0, (1, 2, 4, 2)), -13.5)):
        V.line([(x, 296), (x, 352)], 'inf', lw=0.45, ls=ls)
        V.text((x - 0.4, 353.5 - dy), s, 'inf', fs=3.4, ha='right')
    V.leader((XB_F2[0], 297.5), -4, -8, 'x bounds: NAIP 2022 sensor field of view (67.1 deg) for an ASSUMED rim height [inf]\n'
             f'(spec x_bounds at 67.36 / 63.3 m, interpolated to 64.0: -0.69 / -0.62 m per m of rim); under F2 the box\nwest of '
             f'{XB_F2[0]:.1f} is excluded and -739 lies below the likely bound {XB_F2[1]:.1f}', 'inf', fs=3.6, ha='right')
    V.mark(DOF_TOWER, 'pub', marker='^', ms=4)
    V.mark(OEAAA_13, 'pub', marker='^', ms=3.4, fc='none')
    V.mark((-737.0, 324.9), 'pub', marker='^', ms=4, fc='none')
    V.leader(DOF_TOWER, -36, -50, 'FAA DOF 06-323169 = OE/AAA 2008 site 13: 245 ft AGL envelope, accuracy 4D (+-76 m) [pub];\n'
             f'filled = DOF convention WGS 84 ({DOF_TOWER[0]:.1f}, {DOF_TOWER[1]:.1f}), as on BI / BD / BL;\nhollow = the letter\'s NAD83 reading (-742.6, 335.7)', 'pub', fs=3.8)
    V.leader((-737.0, 324.9), 34, -6, 'OE/AAA site 13A (241 ft AGL; NAD83 position) [pub]', 'pub', fs=3.8)
    epochs = {'2016': (-752.75, 323.35), '2018': (-749.70, 323.20), '2022': (-698.75, 325.30), '2024': (-700.85, 322.40)}
    for y, p in epochs.items():
        V.mark(p, 'obs', marker='o', ms=2.6, fc='none')
        V.text(np.array(p) + np.array([0, -2.2 if y in ('2016', '2024') else 2.4]), y, 'obs', fs=3.4, bg=False)
    V.leader((-698.75, 325.3), 8, -22, 'cab roof as IMAGED by NAIP 2016 / 2018 / 2022 / 2024\n(relief displacement - not positions) [obs]:\nz spread 322.4-325.3, i.e. +-1.45 m about 323.85', 'obs', fs=3.8)
    A = D.app_tower()
    V.mark(A['centre'], 'app', marker='x', ms=4)
    V.circle(A['cab_centre'], A['cab']['roof'][1][0], 'app', z=6, lw=0.6)
    V.leader(A['centre'] + np.array([0, 10.16]), 26, -30, 'app today (js/live/terminals.js buildTower): shaft at the\nfootprint centroid (-740.9, 331.7), 7.2 m S of the spec\naxis; cab-roof D 20.3 m (F1 15.2 / F2 14.5)', 'app', fs=3.8)
    V.leader(ring[1] + np.array([3, -3]), -22, -16, 'roof garden 2,000 sq ft [pub], "SW side",\n~1.7 m below the IBF roof [inf]; outline not measured', 'inf', fs=3.8)
    V.scalebar()
    S.note('Positions: world frame ltp-nad83-2011. The tower axis and cab x are NOT surveyed; NAIP roofs lean 38-40 m east at the cab '
           '(relief displacement), so x rests on bounds that themselves depend on the disputed rim height (one pair per family).')
    S.note('Two height families (buildings_tower.md 12.3), neither preferred: F1 D 15.2 / rim 67.36 (dashed), F2 D 14.5 / rim 64.0 '
           '(dash-dot). The spec trio {67.36, 14.3, 14.2} is inconsistent by ~3 m and is not drawn.')
    S.note('Footprint = SFO Museum atc ring (data/sfo_airport.json); its accuracy against a lean-free survey is unknown (+-1.5-5 m).')
    S.note('The T1-T2 connectors (one with a 35-ft glass ceiling [pub]) are part of the base building; their plan is not in any source found.')
    if variant != 'vector' and dev:
        draw_dev(V, dev, ('Tower base building (IBF)',))
        cc = dev['tower_cab_check']
        c1 = cc['family 1 (rim 67.36 m)']; c2 = cc['family 2 (rim 64.0 m)']
        c2b = cc[next(k for k in cc if k.startswith('family 2 at'))]
        V.circle(c1['predicted_imaged'], F1['D'] / 2, 'inf', z=7, lw=0.6)
        V.circle(c2['predicted_imaged'], F2['D'] / 2, 'inf', z=7, lw=0.6, ls=F2LS)
        V.circle(c2b['predicted_imaged'], F2['D'] / 2, 'inf', z=7, lw=0.4, ls=(0, (1, 1.5)))
        V.leader(np.array(c1['predicted_imaged']) + [0, 7.2], 6, 40, f"predicted imaged cab roof (frame model): F1 {c1['predicted_imaged']}, F2 {c2['predicted_imaged']} "
                 f"(both at cab x -739);\nNAIP 2024 disc centre {c1['observed_imaged']}: delta F1 {c1['delta']} / F2 {c2['delta']} m. At x -739 F2 lies "
                 f"below its own likely\nbound; at that bound (x {c2b['cab_x']}, dotted) F2 predicts {c2b['predicted_imaged']}, delta {c2b['delta']}: "
                 f"F2 then fits about as well as F1\n(|delta| 1.7 vs 1.5 m). INCONCLUSIVE: the predictions differ by {cc['_reading']['prediction_difference_m']} m, less than "
                 f"the input uncertainty\n(cab x +-5 m [inf]; flying-height sd -> +-{cc['_reading']['input_uncertainty']['frame_lean_sd_m']} m on the lean)", 'obs', fs=3.8)
        S.note('Overlay: NAIP 2024 (2024-05-20) under the drawing. Dots = measured offset of the NAIP edge from the drawn edge at its PREDICTED '
               'imaged position (roof edges displaced by h x (P - N)/(H - h), frame model on FAA DOF poles); green <= 1 m, amber <= 2.5 m, '
               'red > 2.5 m, hollow grey = weak edge. Numbers: docs/drawings/buildings/deviations.json.')
    return S.finish('NAIP 2024' if variant != 'vector' else 'none (vector)', fmt=('svg', 'png') if variant == 'vector' else ('jpg',))


def sheet_elev():
    S = Sheet('BT-02', 'Air traffic control tower: elevations from the ESE (airside) and the WNW (landside)', 'A1',
              subtitle='Spec: tools/buildings/spec_tower.json; both height families of buildings_tower.md 12.3')
    w, h = (S.vw - 14) / 2, S.vh - 16
    right_ese = hdg_vec(27.7)        # looking WNW (297.7): right hand = NNE
    right_wnw = hdg_vec(207.7)       # looking ESE (117.7): right hand = SSW
    c1 = sum(ibf_u_extent(right_ese)) / 2 + 12.5; c2 = sum(ibf_u_extent(right_wnw)) / 2 + 12.5
    V1 = S.view(0, 12, w, h, 200, (c1, 37), title='A  ELEVATION FROM THE ESE (airside), looking WNW', kind='elev', frame=False)
    draw_tower_elev(V1, right_ese, ribbon=False)
    V2 = S.view(w + 14, 12, w, h, 200, (c2, 37), title='B  ELEVATION FROM THE WNW (landside), looking ESE - ribbon between the blades', kind='elev', frame=False)
    draw_tower_elev(V2, right_wnw, ribbon=True)
    for V in (V1, V2): V.scalebar(y_mm=6)
    S.note('Every vertical station is rim - k x D (k from the photos). The spec trio {rim 67.36, D 14.3, base-building roof 14.2} fails the '
           'photo-span / NAIP-ratio test by ~3 m (buildings_tower.md 12.3) and is not a family: it is not drawn. Both self-consistent families are '
           'drawn and neither is preferred: F1 D 15.2 m with the rim at 221 ft (filled, levels right); F2 D 14.5 m, rim 64.0 m, 221 ft at the '
           'mast tips (dash-dot outline, levels left). Station details (cab, slots, seams, ribbon, blades) are drawn on F1 only.')
    S.note('CTBUH (Skyscraper Center, re-fetched 2026-11-04: "Structure Height 67.4 m / 221 ft, Floors 12") lists 221 ft as a height '
           'excluding antennae [pub, database classification]: it favours F1\'s definition but is not a survey.')
    S.note('Settle with a surveyed ground photo (rim and grade), the NAIP shadow with the flight time, or an SFO / FAA elevation drawing.')
    S.note('Round airside body: radius = A380-photo width ratios / 1.015 (the verification found them ~1.5 % high) x D, so the flare is '
           '1.58 D = the dimensioned value. The cab is drawn on its inferred centre, offset 1.8 m (1.5 E, 1.0 N) from the axis [inf]; 1.6 m in '
           'these views. Dark plinth ring under the cab glass, D 10.8 m (F1), from the flare deck to the sill [obs photo t1].')
    S.note('Slots (inf from photos t1 / t2, CC BY-SA 4.0): the upper band is discrete slots, ~1.4 m wide, each sweeping ~20 deg of azimuth '
           'between the band seams with its top towards the NNE (13 positions, none in the landside ribbon / wing sector); the long slot is a '
           'helix sweeping ~44 deg (bearing 137 at its foot, 93 at its head). Drawn by projecting these plan bearings on the round body.')
    S.note('Landside (B): the ribbon sits in a flat-faced channel between a narrow, sharp NE blade (pointed tip at about the flare rim) and a '
           'broad, louvred SW wing with a rounded edge; both run full height with creases [obs, photos t3 / t4, Famartin 2025, CC BY-SA 4.0]. '
           'Their proportions are read from oblique photos [inf]; no source dimensions them. The ribbon faces bearing 310 (BT-01), so in B it '
           'sits up to 2.3 m left of the axis; the SW wing tip (254 deg, 14.0 m in plan) reproduces both oblique photos and projects inside '
           'the flare silhouette from 297.7 deg.')
    S.note('Cab glazing: 24 panes of 6 x 11 ft [pub ENR] do not fit the drawn glass ring; glazed arc 220 / 235 / 270 deg [pub, conflict]. '
           'Cab-glass lean 20 +-4 deg out [obs]. Red obstruction light on the roof rim (SW) [obs, photo]; DOF lighting code R [pub].')
    S.note('Cladding: ~1,500 curved trapezoidal ACM panels (4-mm Alucobond Plus "SFO Silver") with spiralling joints [pub]. Drawn '
           'thin on F1: panel rows every 2.47 spec m (6 between the seams; the slot ends lie on rows) and ~68 helical joints turning '
           '2.6 deg of azimuth per spec metre, the twist of both slot kinds [rows / spacing obs photo t2; twist / count inf].')
    S.note('Flare top: a rounded shoulder rising inwards from the widest corner to the plinth foot (t1: 0.35 m in the first 0.5 m, '
           '0.86 m at 3.4 m, ~1.15 m at the plinth) [obs photo t1]; the spec\'s vertical lip + flat deck is not drawn.')
    S.note('Not the base building: the tall dark louvred block seen beside the shaft (t1 left, t2 / t3 right) triangulates from the '
           f'three photos to ({AIRTRAIN_BLOCK[0]:.0f}, {AIRTRAIN_BLOCK[1]:.0f}), 91 m NW of the axis, the SE end of the Terminal 2 AirTrain '
           'station (SFO Museum polygon); the thin canopy plates in t1 are that station\'s platform roof. Neither is drawn.')
    return S.finish()


def sheet_section():
    S = Sheet('BT-03', 'Air traffic control tower: section through the shaft axis (NNE-SSW), looking WNW', 'A3',
              subtitle='Spec: tools/buildings/spec_tower.json (structure items are published text; most dimensions are not)')
    V = S.view(0, 12, S.vw, S.vh - 14, 400, (4, 34.0), kind='elev', frame=False)
    right = hdg_vec(27.7)
    u0, u1 = ibf_u_extent(right); uo = cab_offset(right)
    h_ibf = F1['ibf']
    V.ax.fill_between([u0 - 10, u1 + 10], [-6, -6], [0, 0], color='#e6e6e6', lw=0, zorder=1)
    V.line([(u0 - 10, 0), (u1 + 10, 0)], 'pub', lw=0.8)
    mat = 7 * FT
    V.poly([(-14, 0), (14, 0), (14, -mat), (-14, -mat)], 'unk', fc='#d0d0d0', hatch='xxxx', z=2)
    V.leader((10, -mat / 2), 14, -3, f'mat 7 ft = {mat:.2f} m thick [pub ENR]; plan extent unknown [unk];\n213 piles 140 ft (ENR) / 125 ft to bedrock (STRUCTURE) [pub, conflict]', 'pub', fs=3.8)
    for x in (u0, u1):
        V.poly([(x - 0.15, 0), (x + 0.15, 0), (x + 0.15, h_ibf), (x - 0.15, h_ibf)], 'inf', fc='#999999', z=3)
    V.poly([(u0, h_ibf - 0.5), (u1, h_ibf - 0.5), (u1, h_ibf), (u0, h_ibf)], 'inf', fc='#999999', z=3)
    V.line([(u0, F2['ibf']), (u1, F2['ibf'])], 'inf', lw=0.6, ls=F2LS)
    for k in (1, 2):
        V.line([(u0, h_ibf * k / 3), (u1, h_ibf * k / 3)], 'unk', lw=0.5)
    V.text(((u0 + u1) / 2 - 9, h_ibf * 0.5), 'base building: 3 storeys [pub]\nfloor levels unknown (dotted = equal\nthirds, placeholder only) [unk]', 'unk', fs=3.8)
    for f, ls, lw in ((F1, None, 1.0), (F2, F2LS, 0.6)):
        sh = shaft_outline(f)
        for s in (-1, 1):
            V.line([(s * r, h) for r, h in sh], 'inf', lw=lw, ls=ls)
    cr = 3.6
    for s in (-1, 1):
        V.line([(s * cr, -mat), (s * cr, hf(61.0, F1))], 'unk', lw=0.6)
    V.leader((cr, 36), 16, 6, 'concrete core: slip-formed cylinder, unbonded vertical PT\n(26 tendon bundles) [pub]; wall 30 in -> 18 in [snippet,\nunverified]; DIAMETER NOT PUBLISHED - dotted placeholder [unk]', 'unk', fs=3.8)
    V.leader((-9.5, 54), -14, 4, 'steel-framed flare and cab cantilever\nfrom the core [pub]; cladding outline [inf]', 'inf', fs=3.8)
    c = cab_outline(F1); gb, gt, rim = c['glass_bottom'], c['glass_top'], c['roof_rim']
    fl = hf(61.0, F1)
    pr_ = plinth(F1)[0]          # cab floor inside the plinth ring (the flare top is the sloping shoulder outside it)
    V.poly([(uo - pr_, fl - 0.4), (uo + pr_, fl - 0.4), (uo + pr_, fl), (uo - pr_, fl)], 'inf', fc='#999999', z=4)
    for s in (-1, 1):
        V.line([(uo + s * gb[0], gb[1]), (uo + s * gt[0], gt[1])], 'inf', lw=1.2, color='#46576a')
        V.line([(uo + s * gt[0], gt[1]), (uo + s * rim[0], rim[1])], 'inf', lw=0.9)
    V.poly([(uo - rim[0], rim[1] - 0.6), (uo + rim[0], rim[1] - 0.6), (uo + rim[0], rim[1]), (uo - rim[0], rim[1])], 'inf', fc='#999999', z=4)
    c2 = cab_outline(F2)
    for s in (-1, 1):
        V.line([(uo + s * c2[k][0], c2[k][1]) for k in ('glass_bottom', 'glass_top', 'roof_rim')], 'inf', lw=0.6, ls=F2LS)
    V.line([(uo - c2['roof_rim'][0], c2['roof_rim'][1]), (uo + c2['roof_rim'][0], c2['roof_rim'][1])], 'inf', lw=0.6, ls=F2LS)
    pr, p0, p1 = plinth(F1)
    V.poly([(uo - pr, p0), (uo - pr + 0.4, p0), (uo - pr + 0.4, p1), (uo - pr, p1)], 'obs', fc='#3c4650', z=4.2, lw=0.4)
    V.poly([(uo + pr - 0.4, p0), (uo + pr, p0), (uo + pr, p1), (uo + pr - 0.4, p1)], 'obs', fc='#3c4650', z=4.2, lw=0.4)
    V.leader((uo - pr, (p0 + p1) / 2), -26, -10, f'plinth ring under the glass: D {2 * pr:.1f} m, {p1 - p0:.2f} m high (flare deck -> sill)\n'
             '[obs photo t1: 590 of the 830-px roof, ~0.73 m; t3 shows a railing on it]; wall thickness [unk]', 'obs', fs=3.6)
    V.line([(uo, fl), (uo, rim[1] - 0.6)], 'unk', lw=0.8)
    V.leader((uo, rim[1] - 1.8), -20, 6, 'cab roof cantilevered from a 2\'-2" x 3\'-4" centre column\n[snippet, unverified]; 13 positions [snippet]; 650 sq ft [pub]', 'unk', fs=3.8)
    V.leader((uo + gt[0] - 0.4, (gb[1] + gt[1]) / 2 + 0.6), 16, 2, 'frameless laminated glass, leaning out\n20 +-4 deg [obs]; 2 tuned mass dampers\nnear the cab [pub], position unknown', 'inf', fs=3.8)
    for h, s, tg in ((rim[1], f'+{rim[1]:.2f} rim (F1) / {c2["roof_rim"][1]:.1f} (F2) [inf]', 'inf'), (gt[1], f'+{gt[1]:.1f} glass head (F1) [inf]', 'inf'),
                     (gb[1], f'+{gb[1]:.1f} glass sill (F1) [inf]', 'inf'),
                     (fl, f'+{fl:.1f} cab floor (F1) [inf]; "200-ft concrete core" = 60.96 [snippet]', 'inf'), (hf(59.4, F1), f'+{hf(59.4, F1):.1f} flare widest (F1) [inf]', 'inf'),
                     (h_ibf, f'+{h_ibf:.1f} IBF roof (F1) / {F2["ibf"]:.1f} (F2) [inf]', 'inf'), (0.0, '+0.0 grade (site 13 ft AMSL [pub OE/AAA])', 'pub')):
        V.level(13.5 if h > 20 else u1, h, s, tg, len_mm=4, fs=3.6)
    V.dim((-24, 0), (-24, rim[1]), 0, f'F1: {rim[1]:.2f} m rim = 221 ft [pub number; definition unverified]', 'inf', fs=3.8)
    V.dim((-30, 0), (-30, c2['roof_rim'][1]), 0, f'F2: {c2["roof_rim"][1]:.1f} m rim, 221 ft at the masts', 'inf', fs=3.8)
    V.scalebar(y_mm=4)
    S.note('Cut through the shaft axis along the base building\'s long axis (27.7 deg). The section shows what is published as text '
           '(core type, mat, steel flare and cab, TMDs); no structural drawing was found, so wall thicknesses, core diameter, floor levels '
           'and the elevator / stair core are placeholders.')
    S.note('Outer profile as BT-02: family 1 (D 15.2, rim 67.36) dashed and detailed, family 2 (D 14.5, rim 64.0) dash-dot; the spec trio '
           '(67.36 / 14.3 / 14.2) is inconsistent and not drawn. The cab is drawn on its inferred centre, offset 1.8 m (1.5 E, 1.0 N) from the axis [inf], 1.6 m NNE in this '
           'cut. Dark plinth ring D 10.8 m (F1) under the cab glass, from the flare deck to the sill [obs photo t1].')
    return S.finish()


# ------------------------------------------------------------------------------------------------ deviation dots
DEVC = {'g': '#1a9850', 'a': '#f4a300', 'r': '#d73027', 'w': '#9e9e9e'}


def draw_dev(V, dev, buildings, label_min=2.5):
    for e in dev['edges']:
        if e['building'] not in buildings: continue
        a = np.array(e['p0']) + e['shift']; b = np.array(e['p1']) + e['shift']; n = np.array(e['n'])
        mid = (a + b) / 2
        col = DEVC['w'] if not e['ok'] else DEVC['g'] if abs(e['o']) <= 1 else DEVC['a'] if abs(e['o']) <= 2.5 else DEVC['r']
        if e['kind'] not in ('base',):
            V.line([a, b], 'inf', lw=0.5, color='#ffe082' if e['kind'] == 'roof' else '#80deea', ls=(0, (3, 2)))
        f0, f1 = a + n * e['o'], b + n * e['o']
        V.line([f0, f1], 'obs', lw=0.9, color=col)
        q = V.P(mid + n * e['o'])
        V.ax.plot([q[0]], [q[1]], 'o', ms=2.2, mfc=col if e['ok'] else 'none', mec=col, mew=0.5, zorder=12)
        if e['ok'] and abs(e['o']) > label_min:
            V.text(mid + n * (e['o'] + 2.0 * V.m * 3), f"{e['o']:+.1f}", 'obs', fs=3.4, color=col, z=13)
