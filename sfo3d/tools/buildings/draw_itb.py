"""Sheets of the International Terminal (Senator Dianne Feinstein ITB): main hall wing roof, Boarding Areas A and G,
drawn from tools/buildings/spec_itb.json (verified 2026-11-04, docs/research/buildings_itb.md 'Verification') and its
measurement record tools/buildings/itb_naip_measurements.json:
  BI-01  roof plans: group key plan 1:2500, hall roof 1:750, BA-A 1:2000, BA-G 1:2500 (A1) + NAIP overlay
  BI-02  west (landside) elevation 1:400 and north end elevation 1:250 (A1)
  BI-03  long section along the roof axis 1:400 and cross section at the inner column line 1:250 (A1)
  BI-04  Boarding Areas A and G: apron-face elevations 1:750 and sections 1:400 with the roof pods and the BA-G pod-3 end
         box (tools/buildings/itb_pods.json, NAIP 2024 trace) (A1)
Roof frame: corners of spec roof.corners_obs (frame-model relief correction); u along the axis (+ towards BA-A, SSE),
v across (+ towards ENE). Heights AGL (grade ~8 ft AMSL at the ITB, DOF AMSL - AGL).

Facade (photos i3 Elizabeth K. Joseph 2017 CC BY 2.0, i4 DimiCalifornia 2005 public domain; reference only, kept in
refs/cache/buildings/review_likeness): the west glass wall stands on the elevated departures curb (level 3) and is flat-
topped ~9.3 m below the wing crest; the triangulated "football" trusses are exposed above it along the whole facade;
single white columns stand clear in front of the glass (each casts a shadow on it) at the column lines and branch into
struts into the trusses; the hall (705 ft) stops ~19-21 m short of each roof tip, so the tips are open cantilevers.
"""
import json
import math
import os

import numpy as np

import draw_data as D
from draw_lib import Sheet, FT, ROOT
from draw_tower import draw_dev

I = D.IV
F = D.itb_frame()
HL = F['L'] / 2
HW = F['W'] / 2
SP = I['roof.truss_spacing_obs']['value']
LINES_V = [k * SP for k in (-2, -1, 0, 1, 2)]
COL_U = [57.9, 82.3]                                   # roof.col_positions_inf (+-190 / +-270 ft)
H_PEAK = 40.08
CROWN = I['roof.profile']['value']['centre crown (u ~ 0, glazed centre section top)']['h']
H_NOTCH = I['roof.profile']['value']['notch (|u| 25-31 m, where the wings meet the centre section)']['h']
H_TIP_SPEC = I['roof.profile']['value']['tip (|u| ~ 126 m)']['h']     # 34.9 = blend of NAIP 34.4 (at |u| 119) and photo 35.5
# Beyond the humps the eave fit is made NON-INCREASING towards the tips (review r2-27): the even polynomial's rise from
# 34.40 (|u| 115-119) to 34.83 at |u| 123 is an end artefact - the raw NAIP eave stations fall monotonically to the tips
# (itb_naip_measurements eave_profile.points, median per bin N / S: |u| 100-105 34.8 / 36.3, 110-114 33.5 / 35.6,
# 114-121 32.1 / 34.4-33.8, read over the glazed tip bands, weak) and so does the photo silhouette (itb_photo_skyline:
# north side monotone from x 60 to the hump; south side monotone to the last ~2 m, a 0.5-0.9 m upturn at the fascia
# corner only). Isotonic version of the fit: its minimum 34.40 is held from |u| 117 to the tip [obs, low; 32-35.5].
_EU = np.arange(67.0, 123.01, 0.5)
_EH = np.minimum.accumulate(D.itb_eave_h(_EU))
H_TIP = round(float(_EH[-1]), 2)                       # drawn tip (34.40) [obs, low]
TIP_RNG = (32.0, 35.5)                                 # raw NAIP stations over the glazed band .. photo pair mean (+-2)
L3 = I['level3.floor']['value']
L3R = D.L3_RANGE
LENS = D.ITBM['lenses']
MAG = 0.99                                             # imaged -> true size at the roof (H-h)/H, h ~ 38 m
DOF_ROOF = {'06-035315': ((-1258.1, 429.4), 131), '06-035316': ((-1292.4, 319.1), 132)}
DOF_POD = ((-1195.3, 555.0), 85)
UN = 27.0                    # |u| of the V notches (spec 25-31 m; photo i4 27-29 m) [obs]
WALL = D.itb_west_wall()     # west glass wall: band of the two canopy readings, v = its middle [inf] (NAIP line [obs])
WH = 30.8                    # glass-wall head: 70 px = 9.3 m below the wing crest in photo i4 (0.1335 m/px) [obs, photo, +-1.5]
CANOPY = WALL['h_canopy']    # curb canopy: ~4.5-6 m above the departures curb (photos i3 / i4) [inf]; exists [pub SEAONC]
CANOPY_D = D.CANOPY_D        # its depth, ~5 m (photos) [inf]
HALL_W = 210 * FT            # great hall width 210 ft [pub SEAONC]
BAY_HW = 40.0                # clear central glazing bay: +-39 m (i4: x 730-1320 about 1025 at 0.1331 m/px) / +-42 m (i1) [obs photos]
LETTER_HW = 33.0             # 'SAN FRANCISCO INTERNATIONAL': +-32.5 m (i4) / +-37 m (i1) [obs photos]
BAY_HEAD = 2.0               # the central glazing's head follows the centre section's bottom chord, 1-3.5 m above the side
                             # bays' head (i4 crop: 25-40 px at 0.1331 m/px x 0.67) [obs photo i4, tentative]
HALL_HL = 705 * FT / 2       # great hall 705 ft [pub SEAONC]; centred on the roof [inf]
# curb-canopy hangers (review r1-31 / r2-26) [obs photo i4]: inclined pairs from the glass wall down to the canopy, the
# long leg falling towards +u, with a post under the canopy at each. i4 (frontal, long lens): in the wings their spacing
# is 0.493 / 0.489 of the 80-ft column bay (N / S wing: 266 / 281 px against 540 / 575 px on 3x crops) = 40 ft, set
# 20 ft either side of every column line; over the 180-ft centre section they stand at +-30 / +-90 ft (spacing 60 ft).
# Read u (i4, columns as scale): N -87.9 -76.1 -64.2 -52.2, centre -27.9 -9.2 9.2 27.9, S 28.2 40.1 51.9 63.8 75.9 87.8
# -> the 40-ft grid 90 + 40 k ft within +-0.5 m. Apex ~3.6 m above the canopy, long leg ~2.9 m along u [obs, rough].
HANGER_U = sorted(sg * f * FT for sg in (-1, 1) for f in (30, 90, 130, 170, 210, 250, 290, 330))
HANGER_H, HANGER_L = 3.6, 2.9
TIP_GAP = (1.6, 3.6)         # glass band ends inside the fascia: N 1.6 / S 3.6 m (white strip, spec verification) [obs]
TN, TS = I['roof.glazed_tips_obs']['value']['north'], I['roof.glazed_tips_obs']['value']['south']
# Boarding Areas A / G pods and the BA-G pod-3 end box: NAIP 2024 trace + band heights (tools/buildings/itb_pods.py, review
# r1-26 / r2-29 / r2-30); outlines relief-corrected [obs], heights [obs, low], the box's function [inf]
PODS = json.load(open(os.path.join(D.TB, 'itb_pods.json')))
POD = {p['id']: p for p in PODS['pods']}
FASCIA_MID_IMG = (D.ITBM['roof_length']['tips']['fascia']['N'] + D.ITBM['roof_length']['tips']['fascia']['S']) / 2   # +1.0 m imaged


def UV(u, v):
    return D.itb_uv(F, u, v)


def wing(u):
    """west-eave height of the wings [obs]: spec roof.profile full_curve (NAIP eave relief, DOF-anchored) for |u| >= UN,
    eased over 6 m into the notch value 35.7 [obs] (the NAIP curve reads 36.25 at |u| 27); beyond the hump (|u| 67) made
    non-increasing towards the tip (isotonic fit, see H_TIP): 34.40 from |u| 117 to the tip."""
    a = max(abs(u), UN)
    if a >= 67: return float(np.interp(min(a, 123.0), _EU, _EH))
    d = float(D.itb_eave_h(UN)) - H_NOTCH
    return float(D.itb_eave_h(a)) - d * max(0.0, 1.0 - (a - UN) / 6.0)


def roof_line(u):
    """primary roof silhouette seen from the west: the wings, and between the V notches (|u| < 27) the convex glazed
    centre arch rising to the crown 40.1 m (+-2) [obs, photo i4 / i1; NAIP cannot see it through the lens glass]."""
    a = abs(u)
    if a >= UN: return wing(u)
    return H_NOTCH + (CROWN - H_NOTCH) * (1 - (a / UN) ** 2)


eave = wing          # the west eave of the wings (measure / plan labels)
crown = roof_line    # BX-01 and older callers


def depth(u):
    """truss depth [inf]: 29 ft over the supports (pub), tapering linearly to ~1.5 m at the tip and at the centre
    section's ends (|u| 27.4 = 90 ft: the 180-ft central section, snippet)."""
    a = abs(u); d = 29 * FT
    if 57.9 <= a <= 82.3: return d
    if a < 57.9: return float(np.interp(a, [27.4, 57.9], [1.5, d]))
    return float(np.interp(a, [82.3, HL], [d, 1.5]))


def chord(u):
    """bottom chord of the exposed trusses seen from the west [inf]: level with the glass-wall head over the hall,
    rising over the open cantilevers to ~1.5 m below the tip."""
    a = abs(u)
    if a <= HALL_HL: return WH
    return float(np.interp(a, [HALL_HL, HL], [WH, H_TIP - 1.5]))


def lens_poly(k, d_shape=False):
    """lens k (west -> east) in the roof frame: centred on its truss line; u from the detected boxes relative to the
    FASCIA midpoint (imaged +1.0) and the area centroid, i.e. 1.5-2.2 m north of the roof centre [obs]; the westmost lens
    is full length (detected 34 m only because it is darker - spec verification): drawn with the mean of the others."""
    L = LENS[k]
    if k == 0:
        o = LENS[1:]
        uc = np.mean([x['u_c'] for x in o]); half = np.mean([(x['u1'] - x['u0']) / 2 for x in o]); w = np.mean([x['w_max'] for x in o])
    else:
        uc, half, w = L['u_c'], (L['u1'] - L['u0']) / 2, L['w_max']
    uc = (uc - FASCIA_MID_IMG) * MAG; a = half * MAG; b = w / 2 * MAG
    t = np.linspace(-1, 1, 25)
    if d_shape:   # alternative planform: a D with a straight east edge and a convex west edge, same length / width [inf]
        top = [(uc + a * x, LINES_V[k] + b) for x in t]
        bot = [(uc + a * x, LINES_V[k] + b - 2 * b * (1 - x * x)) for x in t[::-1]]
        return [UV(u, v) for u, v in top + bot], 2 * a, 2 * b, uc
    top = [(uc + a * x, LINES_V[k] + b * (1 - x * x)) for x in t]
    bot = [(uc + a * x, LINES_V[k] - b * (1 - x * x)) for x in t[::-1]]
    return [UV(u, v) for u, v in top + bot], 2 * a, 2 * b, uc


def tip_bands():
    return ((-HL + TIP_GAP[0], -HL + TIP_GAP[0] + TN), (HL - TIP_GAP[1] - TS, HL - TIP_GAP[1]))


# ------------------------------------------------------------------------------------------------ plan
def draw_hall_roof(V, variant, detail=True):
    C = F['corners']; ring = [C['NW'], C['NE'], C['SE'], C['SW']]
    V.poly(ring, 'obs', fc='#e7eef6' if variant == 'vector' else 'none', lw=0.9, z=3)
    (n0, n1), (s0, s1) = tip_bands()
    for u0, u1 in ((n0, n1), (s0, s1)):
        V.poly([UV(u0, -HW), UV(u1, -HW), UV(u1, HW), UV(u0, HW)], 'obs', fc='#cfe3f3' if variant == 'vector' else 'none', hatch='||||' if detail else None, z=3.2, lw=0.4)
    for v in LINES_V:
        V.line([UV(n1, v), UV(s0, v)], 'obs', lw=0.5 if detail else 0.3, z=3.4)
    for k in range(5):
        P = lens_poly(k)[0]
        V.poly(P, 'inf', fc='#cfe3f3' if variant == 'vector' else 'none', z=3.6, lw=0.5)
        if detail: V.poly(lens_poly(k, d_shape=True)[0], 'unk', fc='none', z=3.62, lw=0.4)
    if detail:
        for cu in COL_U:
            for s in (-1, 1):
                V.line([UV(s * cu, -HW - 4), UV(s * cu, HW + 4)], 'inf', lw=0.4, z=3.5)
                for v in LINES_V[1:]:
                    V.mark(UV(s * cu, v), 'inf', marker='s', ms=2.4)
                V.mark(UV(s * cu, WALL['v'] - 2.5), 'inf', marker='o', ms=2.6)
        # west glass wall over the hall extent: the band of the two canopy readings [inf] and the L3-foot reading (dotted)
        b0, b1 = WALL['band']
        V.poly([UV(-HALL_HL, b0), UV(HALL_HL, b0), UV(HALL_HL, b1), UV(-HALL_HL, b1)], 'inf', fc='#f6e3cf' if variant == 'vector' else 'none',
               lw=0.3, z=3.65, alpha=0.8)
        V.line([UV(-HALL_HL, WALL['v']), UV(HALL_HL, WALL['v'])], 'inf', lw=1.0, z=3.7)
        V.line([UV(-HALL_HL, WALL['v_l3']), UV(HALL_HL, WALL['v_l3'])], 'inf', lw=0.4, z=3.7, ls=(0, (1, 1.5)))
    return ring


def _ring_c(p):
    return np.mean(np.asarray(p['ring_true_xz'], float), axis=0)


def draw_pods(V, pier, variant):
    """pods / end box of one pier (itb_pods.json): relief-corrected outline [obs]; on the overlay also the imaged trace (dotted)."""
    for p in PODS['pods']:
        if p['pier'] != pier: continue
        box = p['id'].endswith('box')
        V.poly(p['ring_true_xz'], 'obs', fc=('#f3dcc0' if box else '#d6e6f5') if variant == 'vector' else 'none', lw=0.6, z=3)
        if variant != 'vector': V.poly(p['ring_imaged_xz'], 'obs', fc='none', lw=0.4, z=3.1, ls=(0, (1, 1.2)))
        if not box: V.text(_ring_c(p), p['id'], 'obs', fs=3.4, bg=False, z=3.2)


def sheet_plan(variant='vector', dev=None):
    S = Sheet('BI-01', 'International Terminal: roof plans (main hall wing roof, Boarding Areas A and G)', 'A1', variant=variant,
              subtitle='Spec: tools/buildings/spec_itb.json + itb_naip_measurements.json; note docs/research/buildings_itb.md (Verification)')
    bg = variant != 'vector'
    # ---------------- V1 key plan
    V1 = S.view(0, 160, 225, 410, 2500, (-1330, 400), title='1  KEY PLAN: ITB, Boarding Areas A and G', kind='plan')
    if bg: V1.background()
    V1.grid(100)
    for r in D.outer_rings('International Terminal', 'terminals'):
        V1.poly(r, 'obs', fc='#f1f1f1' if not bg else 'none', lw=0.4, z=1)
    for nm in ('Garage A', 'Garage G', 'Grand Hyatt Hotel'):
        for r in D.outer_rings(nm, 'structures'): V1.ctx(r, fc='#f7f7f7' if not bg else 'none')
    for nm in ('Boarding Area A', 'Boarding Area G'):
        for r in D.outer_rings(nm, 'boardingAreas'):
            V1.poly(r, 'obs', fc='#e7eef6' if not bg else 'none', lw=0.6, z=2)
    draw_hall_roof(V1, variant, detail=False)
    V1.leader(UV(0, -HW), -20, 18, 'main hall roof (relief-corrected) [obs]\n252.9 x 65.4 m; top 34.9-40.1 m', 'obs', fs=4.2)
    V1.leader((-1260, 760), 14, 10, 'Boarding Area A\nroof 17.9 m (16.9-18.8) [obs]\npod 1 top: DOF 25.9 m [pub]\n(NAIP 22.3-25.2 m: conflict)', 'obs', fs=4.2)
    V1.leader((-1450, 90), -6, -26, 'Boarding Area G\nroof 17.0 m (13-20) [obs, low]', 'obs', fs=4.2)
    V1.leader((-1500, 560), -4, 14, 'Garage A (context)', 'unk', fs=3.8)
    V1.leader((-1480, 320), -2, -14, 'Garage G (context)', 'unk', fs=3.8)
    V1.text((-1180, 150), 'ITB outline =\nSFO Museum\n"International\nTerminal" [obs]', 'obs', fs=3.8)
    V1.scalebar()
    # ---------------- V2 hall roof plan
    V2 = S.view(232, 0, 270, 570, 750, (-1245, 365), title='2  MAIN HALL WING ROOF: roof plan', kind='plan')
    if bg: V2.background()
    V2.grid(20)
    draw_hall_roof(V2, variant)
    C = F['corners']
    V2.dim(C['NW'], C['SW'], -9, f'{F["L"]:.2f} m eave tip to tip (252.6-255.1) [obs, NAIP relief-corrected]', 'obs', fs=4.6)
    V2.dim(C['NW'] + F['ax'] * (HL - 131.06), C['SW'] + F['ax'] * (131.06 - HL), -19, '860 ft = 262.13 m overall [pub SEAONC, Smith-Emery] - CONFLICT with the obs length', 'pub', fs=4.6)
    V2.dim(C['NE'], C['NW'], -8, f'{F["W"]:.2f} m [obs] (214 ft); hall 210 ft [pub] does NOT fit east of the west wall (BI-03)', 'obs', fs=4.6)
    V2.dim(UV(-60, LINES_V[3]), UV(-60, LINES_V[4]), 0, f'{SP:.2f} [obs] = 40 ft grid [pub]', 'obs', fs=3.8, ext=False)
    (n0, n1), (s0, s1) = tip_bands()
    V2.dim(UV(s0, HW + 1), UV(s1, HW + 1), 5, f'{TS} glazed [obs]', 'obs', fs=3.6)
    V2.dim(UV(s1, HW + 1), UV(HL, HW + 1), 5, f'{TIP_GAP[1]}', 'obs', fs=3.4)
    V2.dim(UV(n0, HW + 1), UV(n1, HW + 1), 5, f'{TN} glazed [obs]', 'obs', fs=3.6)
    V2.dim(UV(-HL, HW + 1), UV(n0, HW + 1), 5, f'{TIP_GAP[0]}', 'obs', fs=3.4)
    V2.leader(UV(HL - 1.8, -HW + 6), 18, -8, 'white segmented strip beyond the glass:\nS 3.6 m, N 1.6 m [obs, spec verification]', 'obs', fs=3.6)
    edges_ft = [-430, -410, -270, -190, -90, 90, 190, 270, 410, 430]
    for a, b in zip(edges_ft[:-1], edges_ft[1:]):
        V2.dim(UV(a * FT, HW + 2), UV(b * FT, HW + 2), 13, f'{b - a} ft', 'inf', fs=3.8)
    V2.leader(UV(126, HW + 14), -10, -24, 'published / inferred rhythm (ft) [inf]: 20 overhang | 140 truss cantilever |\nouter column | 80 | inner column | 100 | 180 centre section | ... ;\n'
              'centre span 380 ft [pub], end cantilever 160 ft [pub], 860 ft [pub]', 'inf', fs=3.8)
    for cu in COL_U:
        for s in (-1, 1):
            V2.text(UV(s * cu, -HW - 7), f'{"inner" if cu < 60 else "outer"} col. line\nu {s * cu:+.1f} [inf]', 'inf', fs=3.4)
    V2.leader(UV(70, LINES_V[2]), 30, 30, '20 columns = 5 truss lines x 4 (inner / outer column lines at +-190 / +-270 ft) [inf];\n'
              '"20 cantilevered columns rising from the third floor departures level" [pub SEAONC];\n'
              'west line: the columns stand clear in front of the glass (circles) [obs photos], v not measured -\ndrawn 2.5 m in front of '
              'the wall band\'s middle [inf]', 'inf', fs=3.8)
    P, Lk, Wk, uc = lens_poly(2)
    V2.leader(UV(uc, LINES_V[2] + 4), 34, 6, f'5 skylights on the truss lines, {Lk:.1f} m x {Wk:.1f} m [obs], row centred {-uc:.1f} m N of\n'
              'the fascia midpoint [obs]; the westmost is full length too (spec verification);\ncentre section 180 ft [pub, snippet]. PLANFORM [inf]: '
              'NAIP shows each as a D\n(straight east edge, convex west edge) - a vaulted lens leaning east (drawn,\npointed lens) or a D in plan '
              '(dotted) - not settled (spec roof.lenses_obs)', 'inf', fs=3.8)
    b0, b1 = WALL['band']
    V2.leader(UV(-80, WALL['v']), -26, 12, f'west glass wall [inf]: band v {b0:.1f} to {b1:.1f} ({b0 + HW:.1f}-{b1 + HW:.1f} m inside the eave),\n'
              f'drawn at its middle {WALL["v"]:.1f}. The NAIP straight facade-base line [obs] is NOT the wall\'s foot:\n'
              f'the curb canopy ("entrance canopy" [pub SEAONC], ~5 m deep [inf]) hides the foot\nfrom the camera whenever it is deeper than '
              f'{WALL["foot_hidden_depth"]:.1f} m ({CANOPY - L3:.0f} m x {WALL["k"]:.2f} m/m), so the line is\nthe canopy edge (-> {b1:.1f}) or the '
              f'wall just above the canopy (-> {b0:.1f}).\nDotted: {WALL["v_l3"]:.1f}, valid only if the canopy were <= 2 m deep (foot on L3 '
              f'visible).\nOver the 705-ft hall only [pub length, centred inf]', 'inf', fs=3.8)
    for oas, (p, ft) in DOF_ROOF.items():
        V2.mark(p, 'pub', marker='^', ms=4.5)
        V2.leader(p, -24, 6 if ft == 132 else -6, f'FAA DOF {oas}: {ft} ft AGL = {ft * FT:.2f} m\n(1A, +-3 ft) roof top [pub]', 'pub', fs=3.8)
    for uu, s in ((0, f'crown {CROWN} (photo, +-2) [obs]'), (-UN, f'notch {H_NOTCH} [obs]'), (UN, f'notch {H_NOTCH} [obs]'), (-67, 'hump 40.08 [inf: DOF-anchored fit]'), (67, 'hump 40.08 [inf: DOF-anchored fit]'),
                  (-100, '36.4 [obs]'), (100, '36.4 [obs]'), (-124, f'tip {H_TIP:.1f} ({TIP_RNG[0]:.0f}-{TIP_RNG[1]}) [obs, low]'), (124, f'tip {H_TIP:.1f} [obs, low]')):
        V2.mark(UV(uu, -HW), 'obs', marker='o', ms=2.0)
        V2.text(UV(uu, -HW - 2.5), s, 'inf' if 'fit' in s else 'obs', fs=3.6, ha='right', rot=0)
    V2.text(UV(-112, -HW - 46), 'west eave heights AGL\n(roof.profile: NAIP eave relief,\nanchored on the DOF mean at the\nfitted peak |u| 67 [inf]; at the DOF\n'
            'stations u +57.2 / -58.4 the curve\nreads 39.70 / 39.78, 0.23 / 0.45 m\nbelow 39.93 / 40.23 [pub]: anchored\nthere, all heights '
            'rise ~0.34 m)', 'obs', fs=3.8)
    A = D.app_great_hall(); av = np.array([A['ax'][1], -A['ax'][0]])
    R = [A['c'] + A['ax'] * su * A['L'] / 2 + av * sv * A['W'] / 2 for su, sv in ((-1, -1), (-1, 1), (1, 1), (1, -1))]
    V2.poly(R, 'app', fc='none', lw=0.8, z=6)
    V2.leader(R[1], -6, 22, f'app today (terminals.js greatHall): {A["L"]:.1f} x {A["W"]:.1f} m roof on the SFO Museum hall-part\naxis, centre ({A["c"][0]:.1f}, {A["c"][1]:.1f}) = 35 m E of the spec centre, axis 2.9 deg off', 'app', fs=3.8)
    V2.mark(F['c'], 'obs', marker='+', ms=7)
    V2.leader(F['c'], -30, -40, f'roof centre ({F["c"][0]:.1f}, {F["c"][1]:.1f}) [obs]\naxis heading 162.85 deg [obs]', 'obs', fs=3.8)
    V2.scalebar()
    # ---------------- V3 / V4 piers
    V3 = S.view(510, 300, 229, 270, 2000, (-1232, 664), title='3  BOARDING AREA A', kind='plan')
    V4 = S.view(510, 6, 229, 280, 2500, (-1362, 104), title='4  BOARDING AREA G', kind='plan')
    for V, nm in ((V3, 'Boarding Area A'), (V4, 'Boarding Area G')):
        if bg: V.background()
        V.grid(50)
        for r in D.outer_rings(nm, 'boardingAreas'):
            V.poly(r, 'obs', fc='#e7eef6' if not bg else 'none', lw=0.7, z=2)
        V.scalebar()
    draw_pods(V3, 'A', variant); draw_pods(V4, 'G', variant)
    V3.mark(DOF_POD[0], 'pub', marker='^', ms=4.5)
    V3.leader(DOF_POD[0], 14, 12, 'FAA DOF 06-035352: 85 ft = 25.91 m AGL\n(1A) top of pod 1 [pub]', 'pub', fs=3.8)
    V3.leader((-1240, 700), 16, -4, 'main roof 17.9 m (16.9-18.8) [obs]\nNAIP oblique-band method, k 0.42;\n'
              'two-epoch control 17.8 m [obs]\nroof width 37.85 m [obs]; outline\n38.7-38.8 m (incl. facade band) [obs]', 'obs', fs=3.8)
    A_ = [POD[k] for k in ('A1', 'A2', 'A3')]; G_ = [POD[k] for k in ('G1', 'G2', 'G3')]; BX = POD['G3-box']
    V3.leader(_ring_c(A_[2]), -8, -16, '3 raised D-shaped pods A1-A3 (from the ITB), traced on NAIP 2024 and\nrelief-corrected (frame model) [obs]: L ' +
              ' / '.join(f"{p['length_m']:.0f}" for p in A_) + f" m, W ~{A_[0]['width_m']:.0f} m; curved WNW edge, straight\nends [obs], straight ESE side [obs, weak]. "
              f"Rise {min(p['rise_m'] for p in A_)}-{max(p['rise_m'] for p in A_)} m (WNW band\n= face + shadow) -> tops {A_[2]['top_m']}-{A_[0]['top_m']} m "
              f"({A_[2]['top_range_m'][0]}-{A_[0]['top_range_m'][1]}) [obs, low];\npod 1 DOF 25.9 m [pub]: consistent only at the upper ends\n"
              '(dotted on the overlay = imaged trace)', 'obs', fs=3.8, ha='right')
    V3.leader((-1240, 700), 16, -4, 'main roof 17.9 m (16.9-18.8) [obs]\nNAIP oblique-band method, k 0.42;\n'
              'two-epoch control 17.8 m [obs]\nroof width 37.85 m [obs]; outline\n38.7-38.8 m (incl. facade band) [obs]', 'obs', fs=3.8)
    V4.leader((-1400, 100), -4, -22, 'main roof 17.0 m (13-20) [obs, low; k(x) relief]\nroof width 38.4 m between parapets [obs]\n(the earlier ~33.5 m is refuted)', 'obs', fs=3.8)
    V4.leader(_ring_c(G_[1]), 10, 34, '3 raised lens pods G1-G3 (from the ITB), truncated by straight end walls;\ntraced on NAIP 2024, relief-corrected (k(x)) [obs]: L ' +
              ' / '.join(f"{p['length_m']:.0f}" for p in G_) + f" m, W ~{G_[1]['width_m']:.0f} m (edges between the read\npoints parabolic [inf]); "
              f"rise {min(p['rise_m'] for p in G_)}-{max(p['rise_m'] for p in G_)} m (WNW end band) -> tops "
              f"{min(p['top_m'] for p in G_)}-{max(p['top_m'] for p in G_)} m\n[obs, low; main roof 13-20]; no DOF entry. SFOM outline 3-6 m NNE of\nthe NAIP roof [obs, unresolved]", 'obs', fs=3.8, ha='left')
    V4.leader(_ring_c(BX), 3, -62, f"raised box ~{BX['length_m']:.0f} x {BX['width_m']:.0f} m at the WNW end of pod G3 [obs, NAIP 2024]:\n"
              f"WNW band = box face {BX['band_box_face_m']} m + pod end {BX['band_pod_end_m']} m -> {BX['rise_above_pod_m'][0]}-{BX['rise_above_pod_m'][1]} m above\n"
              f"the pod, top {BX['top_main_value_m'][0]}-{BX['top_main_value_m'][1]} m ({BX['top_range_m'][0]}-{BX['top_range_m'][1]}) [obs, low]. The box-shaped cab\n"
              'with a dark window band and antennas on a raised roof volume of\nphoto d2 (wbaiv 2018, CC BY 4.0) [inf]; ramp-control cab [inf, unconfirmed]', 'inf', fs=3.8, ha='left')
    rows = [('DOF roof tops (u +57.2 / -58.4, west eave)', '39.93 / 40.23 m (131/132 ft)', 'pub', 'FAA DOF 06-035315/16, 1A (+-3 ft)'),
            ('Hump (fitted peak, |u| 67)', '40.08 m', 'inf', 'eave fit anchored on the DOF mean at its peak; 0.23 / 0.45 m low at the DOF stations'),
            ('Notches (wings meet centre section)', f'{H_NOTCH} m at |u| ~27', 'obs', 'NAIP eave relief 36.25 + photo 35.2'),
            ('Centre crown (glazed arch top)', '40.1 m +-2', 'obs', 'public-domain photo only'),
            ('Tips', f'{H_TIP:.1f} m ({TIP_RNG[0]:.0f}-{TIP_RNG[1]})', 'obs', f'eave fit made non-increasing to the tips (minimum held); spec {H_TIP_SPEC} = NAIP / photo blend'),
            ('Roof length / width', '252.9 x 65.4 m', 'obs', 'NAIP, relief-corrected; 860 ft pub conflicts'),
            ('Truss lines / spacing', '5 / 12.12 m', 'obs', 'NAIP comb fit; 40 ft grid [pub]'),
            ('Truss depth max / centre span / end cantilever', '29 / 380 / 160 ft', 'pub', 'SEAONC (read in full)'),
            ('West glass wall behind the eave', f'{WALL["v"] + HW:.1f} m ({WALL["band"][0] + HW:.1f}-{WALL["band"][1] + HW:.1f})', 'inf', 'NAIP line [obs] = canopy edge or wall above the canopy [inf]'),
            ('Hall width 210 ft vs room under the roof', f'64.0 vs <= {HW - WALL["band"][0]:.1f} m', 'pub', 'CONFLICT: see BI-03'),
            ('Level 3 (departures) floor', f'{L3} m ({L3R[0]}-{L3R[1]})', 'inf', 'DOF top minus 100 ft / 90 ft / 83 ft'),
            ('"Building height 144 ft"', 'datum unknown', 'pub', 'SOM, Enclos - do not use'),
            ('BA-A / BA-G main roof', '17.9 / 17.0 m', 'obs', 'NAIP relief / shadow'),
            ('BA-A pods A1-A3 (D)', f"top {POD['A3']['top_m']}-{POD['A1']['top_m']} m", 'obs', 'NAIP trace + WNW band (low); pod 1 DOF 25.9 [pub]'),
            ('BA-G pods G1-G3 (lens)', f"top {POD['G2']['top_m']}-{POD['G3']['top_m']} m", 'obs', 'NAIP trace + end band (low); main roof 13-20'),
            ('BA-G pod-3 end box', f"top {POD['G3-box']['top_main_value_m'][0]}-{POD['G3-box']['top_main_value_m'][1]} m", 'obs', 'NAIP band (low); cab of photo d2 [inf]'),
            ('Roof 2024-26 upgrade (membrane, ~1,400 kW PV)', 'layout unknown', 'pub', 'NAIP 2024-05-20 predates it')]
    S.table(0, 150, 222, 'ITB key values', rows, fs=4.0, col=(0.46, 0.24))
    S.note('Hall roof outline, truss lines, lenses and tip bands: NAIP 2024 measured and relief-corrected with the frame model fitted to five '
           'FAA DOF high-mast poles (rms 0.21 m); +-1.5 m. Length 252.6-255.1 m depending on the relief model; the published 860 ft (262.1 m) '
           'is NOT reproduced (conflict open: 145 ft visible end cantilever vs 160 ft published).')
    S.note('Column lines are inferred from the only rhythm that satisfies all published spans; the DOF pair 115.5 m (379 ft) apart over the inner '
           'column lines supports it, and photo i4 puts the west columns at u -83.4 / -59.4 m (+-1.5). The SFO Museum pier outlines include '
           'the oblique facade band (lean).')
    S.note('The roof seen by NAIP (2024-05-20) predates the 2024-26 envelope upgrade (new membrane, rooftop PV ~1,400 kW): PV layout unknown.')
    if bg and dev:
        draw_dev(V2, dev, ('ITB main hall roof', 'ITB west facade (glass-wall base on L3)'))
        draw_dev(V3, dev, ('Boarding Area A',), label_min=99)
        draw_dev(V4, dev, ('Boarding Area G',), label_min=99)
        S.note('Overlay: NAIP 2024 under the drawing. Dots = measured offset of the NAIP edge from the drawn edge at its PREDICTED imaged '
               'position (frame model; roof heights from the eave profile / pier heights; BA-G with the k(x) model as its spec height; the '
               'west wall base at L3); green <= 1 m, amber <= 2.5, red > 2.5, hollow = weak. deviations.json lists every edge.')
    return S.finish('NAIP 2024' if bg else 'none (vector)', fmt=('jpg',) if bg else ('svg', 'png'))


# ------------------------------------------------------------------------------------------------ elevations
def draw_roof_profile(V, us):
    """primary roof silhouette: wings (solid obs) and the centre arch (obs, with its +-2 m photo band)."""
    V.line([(u, roof_line(u)) for u in us if u <= -UN], 'obs', lw=1.1, z=6)
    V.line([(u, roof_line(u)) for u in us if u >= UN], 'obs', lw=1.1, z=6)
    ua = np.linspace(-UN, UN, 80)
    band = [2.0 * (1 - (u / UN) ** 2) for u in ua]
    V.ax.fill_between(ua, [roof_line(u) - b for u, b in zip(ua, band)], [roof_line(u) + b for u, b in zip(ua, band)],
                      color='#cfe0f2', lw=0, zorder=1.8, alpha=0.9)
    V.line([(u, roof_line(u)) for u in ua], 'obs', lw=1.1, z=6)


def draw_trusses(V, us):
    """exposed truss band between the roof line and the bottom chord, with a schematic web (panels ~6 m) [inf]."""
    V.ax.fill_between(us, [chord(u) for u in us], [roof_line(u) - 0.6 for u in us], color='#f6efe6', lw=0, zorder=1.6)
    V.line([(u, chord(u)) for u in us], 'inf', lw=0.6, z=4)
    V.line([(u, roof_line(u) - 0.6) for u in us], 'inf', lw=0.35, z=4)
    nodes = np.arange(-HL + 2.0, HL - 1.9, 6.0)
    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        if i % 2 == 0: V.line([(a, chord(a)), (b, roof_line(b) - 0.6)], 'inf', lw=0.25, z=4)
        else: V.line([(a, roof_line(a) - 0.6), (b, chord(b))], 'inf', lw=0.25, z=4)


def draw_columns(V, struts=True):
    """the 20 columns' west line: white columns in front of the glass up to the glass head, where each branches into a
    fan of 4-6 members into the trusses (photos i3 / i4: a vertical post continuing to the top chord + about 2 members
    each side) [obs count, review r2-26]; drawn as post + 2 per side at +-5 / +-10 m [inf geometry, schematic]."""
    for cu in COL_U:
        for s in (-1, 1):
            u = s * cu
            V.poly([(u - 0.75, L3), (u + 0.75, L3), (u + 0.75, WH), (u - 0.75, WH)], 'inf', fc='#ffffff', z=6.5, lw=0.7)
            if struts:
                for du in (-10.0, -5.0, 0.0, 5.0, 10.0):
                    V.line([(u, WH), (u + du, roof_line(u + du) - (0.6 if abs(du) > 7 else 1.2))], 'inf', lw=0.8 if du else 1.0, z=6.4, color='#8c8c8c')


def draw_hangers(V):
    """curb-canopy hangers and the posts under the canopy (HANGER_U) [obs photo i4; form schematic]."""
    for uh in HANGER_U:
        if abs(uh) > HALL_HL: continue
        V.line([(uh - 0.4, CANOPY), (uh, CANOPY + HANGER_H), (uh + HANGER_L, CANOPY)], 'obs', lw=0.45, z=5.2, color='#3f4f5c')
        V.line([(uh, L3), (uh, CANOPY)], 'obs', lw=0.35, z=5.1, color='#6d7c88')


def west_elev(V):
    us = np.linspace(-HL, HL, 500)
    V.ax.fill_between([-HL - 25, HL + 25], [-3, -3], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(-HL - 25, 0), (HL + 25, 0)], 'pub', lw=0.8)
    # lower levels (services, arrivals) and the elevated departures roadway / curb at L3
    V.poly([(-HALL_HL, 0), (HALL_HL, 0), (HALL_HL, L3), (-HALL_HL, L3)], 'unk', fc='#f2f2f2', z=1.5)
    V.ax.fill_between([-HL - 20, HL + 20], [L3 - 1.2] * 2, [L3] * 2, color='#c9c9c9', lw=0, zorder=2)
    V.line([(-HL - 20, L3), (HL + 20, L3)], 'inf', lw=0.6)
    V.text((-HL - 8, L3 + 1.6), 'departures roadway / curb (L3)', 'inf', fs=3.6, ha='left')
    V.text((0, 4.0), 'levels 1-2 (services, arrivals) behind the lower roadway: not dimensioned in any source [unk]', 'unk', fs=3.9)
    # west glass wall over the hall extent [obs photos i1 / i4]: clear entrance glazing under the curb canopy; above it fritted
    # side bays (white, horizontal frit bands, a dark clear strip just above the canopy) and the wide clear central bay on a
    # mullion grid carrying the 'SAN FRANCISCO INTERNATIONAL' lettering; the central glazing's head rises into the centre section
    V.poly([(-HALL_HL, L3), (HALL_HL, L3), (HALL_HL, CANOPY), (-HALL_HL, CANOPY)], 'obs', fc='#c9d6e2', z=1.7, lw=0.3)
    for sg in (-1, 1):
        a, b = sorted((sg * BAY_HW, sg * HALL_HL))
        V.poly([(a, CANOPY), (b, CANOPY), (b, WH), (a, WH)], 'obs', fc='#f4f4f1', z=1.7, lw=0.4)
        V.poly([(a, CANOPY), (b, CANOPY), (b, CANOPY + 1.5), (a, CANOPY + 1.5)], 'obs', fc='#5f6d7a', z=1.75, lw=0.2)
        for hh in np.arange(CANOPY + 2.4, WH - 0.3, 0.9):
            V.line([(a, hh), (b, hh)], 'obs', lw=0.15, z=1.76, color='#b8bec4')
    head = [(-BAY_HW, WH), (-UN, WH + BAY_HEAD), (UN, WH + BAY_HEAD), (BAY_HW, WH)]
    V.poly([(BAY_HW, CANOPY), (-BAY_HW, CANOPY)] + head, 'obs', fc='#d7e6f3', z=1.72, lw=0.5)
    for uu in np.arange(-BAY_HW, BAY_HW + 0.01, 20 * FT):
        V.line([(uu, CANOPY), (uu, float(np.interp(uu, [p[0] for p in head], [p[1] for p in head])))], 'obs', lw=0.2, z=1.77, color='#7f97ad')
    for hh in np.arange(CANOPY + 2.2, WH + BAY_HEAD, 2.2):
        ua = float(np.interp(hh, [WH, WH + BAY_HEAD], [BAY_HW, UN])) if hh > WH else BAY_HW
        V.line([(-ua, hh), (ua, hh)], 'obs', lw=0.2, z=1.77, color='#7f97ad')
    V.poly([(-LETTER_HW, 25.8), (LETTER_HW, 25.8), (LETTER_HW, 28.6), (-LETTER_HW, 28.6)], 'obs', fc='none', z=1.8, lw=0.3, ls=(0, (1, 1)))
    V.text((0, 27.2), 'SAN FRANCISCO INTERNATIONAL', 'obs', fs=6.2, bg=False, color='#26323d', style='normal', weight='bold', z=1.9)
    V.line([(-HALL_HL, CANOPY), (HALL_HL, CANOPY)], 'inf', lw=0.7, z=5)
    draw_hangers(V)
    for s in (-1, 1):
        V.line([(s * HALL_HL, L3), (s * HALL_HL, chord(s * HALL_HL))], 'obs', lw=0.8, z=5)
    draw_trusses(V, us)
    draw_columns(V)
    draw_roof_profile(V, us)
    (n0, n1), (s0, s1) = tip_bands()
    for a, b in ((n0, n1), (s0, s1)):
        uu = np.linspace(a, b, 20)
        V.ax.fill_between(uu, [roof_line(u) - 1.0 for u in uu], [roof_line(u) for u in uu], color='#cfe3f3', lw=0, zorder=6.2, hatch='||||', edgecolor='#0b57a4')
    # levels
    V.level(HL + 2, L3, f'+{L3} departures curb / level 3 ({L3R[0]}-{L3R[1]}) [inf]', 'inf', len_mm=6, fs=4.2, u_line=HALL_HL)
    V.level(HL + 2, CANOPY, f'+{CANOPY:.1f} curb canopy (photos) [inf]', 'inf', len_mm=6, fs=4.0, u_line=HALL_HL)
    V.level(HL + 2, WH, f'+{WH} glass-wall head (photo i4) [obs, +-1.5]', 'obs', len_mm=6, fs=4.0, u_line=HALL_HL)
    for oas, (p, ft) in DOF_ROOF.items():
        u = float(np.dot(np.asarray(p) - F['c'], F['ax']))
        V.mark((u, ft * FT), 'pub', marker='v', ms=4)
        V.text((u, ft * FT + 3.0), f'DOF {oas}\n{ft} ft = {ft * FT:.2f} m [pub]', 'pub', fs=3.9)
    V.level(HL + 2, 144 * FT, '+43.89 "144 ft" [pub SOM]: datum unknown', 'pub', len_mm=6, fs=4.0, u_line=HL - 10)
    V.level(HL + 2, H_TIP, f'+{H_TIP:.1f} tip ({TIP_RNG[0]:.0f}-{TIP_RNG[1]}) [obs, low]', 'obs', len_mm=6, fs=4.0, u_line=HL)
    V.level(HL + 2, H_PEAK, '+40.08 humps |u| 67 [inf: DOF-anchored fit]', 'inf', len_mm=6, fs=4.2, u_line=67)
    V.level(-HL - 2, H_NOTCH, f'+{H_NOTCH} notches [obs]', 'obs', side='left', len_mm=4, fs=4.2, u_line=-UN)
    V.level(-HL - 2, CROWN + 0.0001, f'+{CROWN} crown (photo +-2) [obs]', 'obs', side='left', len_mm=4, fs=4.2, u_line=0)
    V.dim((-HL, -1), (HL, -1), -8, f'{F["L"]:.2f} m eave tip to tip (252.6-255.1) [obs]', 'obs', fs=4.6)
    V.dim((-131.06, -1), (131.06, -1), -16, '860 ft = 262.13 m [pub] - conflict', 'pub', fs=4.6)
    V.dim((-HALL_HL, L3 - 1.4), (HALL_HL, L3 - 1.4), -3, '705 ft = 214.9 m great hall [pub SEAONC]; centred [inf]', 'pub', fs=4.2)
    V.dim((-HL, chord(-HL) - 1.0), (-HALL_HL, chord(-HL) - 1.0), -4, f'{HL - HALL_HL:.1f} open cantilever [inf; photo i4 ~21]', 'inf', fs=3.8)
    V.dim((HALL_HL, chord(HL) - 1.0), (HL, chord(HL) - 1.0), -4, f'{HL - HALL_HL:.1f} [inf]', 'inf', fs=3.8)
    for a, b in zip([-430, -410, -270, -190, -90, 90, 190, 270, 410], [-410, -270, -190, -90, 90, 190, 270, 410, 430]):
        V.dim((a * FT, 46), (b * FT, 46), 4, f'{b - a}', 'inf', fs=3.8)
    V.text((0, 52.5), 'published / inferred structural rhythm, ft [inf]: 20 | 140 | 80 | 100 | 180 | 100 | 80 | 140 | 20', 'inf', fs=4.2)
    V.text((0, 8.6), 'WEST GLASS WALL on the departures curb: three layers of ceramic frit [pub]; drawn over the 705-ft hall only - the roof tips beyond are open cantilevers [obs photos]',
           'pub', fs=4.0)
    V.leader((BAY_HW - 6, 22.0), 26, -14, f'clear central bay ~{2 * BAY_HW:.0f} m wide (+-39 m i4, +-42 m i1) on a mullion grid (~6.1 m x ~2.2 m, i4,\n'
             f'low), carrying the lettering (~{2 * LETTER_HW:.0f} m: +-32.5 i4, +-37 i1; ~2.8 m tall, centre ~27 m) [obs photos i1 / i4];\n'
             f'its head follows the centre section\'s bottom chord, ~{BAY_HEAD:.0f} m (1-3.5) above the side bays\' head [obs photo i4,\n'
             'tentative]. Side bays: white horizontally banded frit, a dark clear strip just above the canopy;\nclear entrance glazing under the '
             'canopy [obs photos i1-i4]; module not published [unk]', 'obs', fs=3.8)
    V.leader((-COL_U[1], L3 + 2.0), -4, -21, 'white columns stand clear in front of the glass (shadow on it) and branch at the\nglass head into a fan of 4-6 members '
             'into the trusses (post + ~2 per side) [obs photos i3 / i4];\nu at the column lines [inf] (photo i4: -83.4 / -59.4 m); member geometry schematic [inf]', 'inf', fs=3.8, ha='right')
    uh = HANGER_U[len(HANGER_U) // 2 + 4]
    V.leader((uh + 1.0, CANOPY + 1.8), 12, -31, 'curb-canopy hangers: inclined pairs from the glass wall to the canopy (long leg falling to +u), a post under\n'
             'the canopy at each [obs photo i4]: |u| = 30 / 90 ft over the 180-ft centre section, then every 40 ft from 130 to 330 ft\n'
             '= 20 ft either side of each column line (i4: spacing / 80-ft bay 0.493 N, 0.489 S; read u within +-0.5 m of the grid);\n'
             f'apex ~{HANGER_H} m above the canopy, leg ~{HANGER_L} m [obs photo, rough]; canopy height / depth [inf]', 'obs', fs=3.7)
    V.leader((-112, (chord(-112) + roof_line(-112)) / 2), -6, -12, 'exposed "football" trusses above the wall head, tapering to the tips\n'
             '(bottom chord = soffit over the open cantilevers) [obs photos]; web schematic [inf]', 'inf', fs=3.8, ha='right')


def hall_conflict(V, sign, y):
    """dimension the published hall width from the west wall (plot coordinate = sign x v) against the room under the roof."""
    vw = WALL['v']; ve = vw + HALL_W
    V.line([(sign * ve, L3), (sign * ve, WH)], 'inf', lw=0.7, ls=(0, (4, 2)))
    V.dim((sign * vw, y), (sign * ve, y), 3 if sign < 0 else -3, f'hall 210 ft = {HALL_W:.1f} m [pub SEAONC], measured from the west wall [inf]', 'pub', fs=3.8)
    V.dim((sign * WALL['band'][0], y - 3.2), (sign * HW, y - 3.2), 3 if sign < 0 else -3,
          f'<= {HW - WALL["band"][0]:.1f} m under the roof east of the wall (wall band: {HW - WALL["band"][1]:.1f}-{HW - WALL["band"][0]:.1f})', 'inf', fs=3.8)
    V.leader((sign * ve, (L3 + WH) / 2), -sign * 6 if sign > 0 else 6, 4, f'CONFLICT: the published hall ends {ve - HW:.1f} m beyond the measured east eave.\n'
             'Resolutions: wall nearer the eave / hall continuing east under a lower roof\n(east edge = "fascia -> lower roof fall" [obs]) / wider roof (SOM sketch 260 ft)', 'pub', fs=3.7,
             ha='left' if sign < 0 else 'right')


def north_elev(V):
    V.ax.fill_between([-HW - 18, HW + 18], [-2, -2], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(-HW - 18, 0), (HW + 18, 0)], 'pub', lw=0.8)
    # plot coordinate = -v (viewer looks SSE: right hand = WSW)
    V.poly([(-HW, H_TIP - 1.5), (HW, H_TIP - 1.5), (HW, H_TIP), (-HW, H_TIP)], 'obs', fc='#cfe3f3', z=3, hatch='||||')
    V.line([(-HW, H_PEAK), (HW, H_PEAK)], 'inf', lw=0.5, ls=(0, (6, 3)))
    V.text((0, H_PEAK + 1.6), 'silhouette of the humps behind (40.08 m, DOF-anchored fit [inf]; DOF 39.93 / 40.23 [pub]); cross camber unknown [unk]', 'inf', fs=4.0)
    V.line([(-HW, CROWN), (HW, CROWN)], 'obs', lw=0.4, ls=(0, (2, 3)))
    xw = -WALL['v']; top = chord(HALL_HL)
    V.poly([(-HW, L3), (xw, L3), (xw, top), (-HW, top)], 'unk', fc='#f4f8fb', z=2)
    V.text((xw - 30, (L3 + top) / 2), 'END CURTAIN WALL: custom unitized, spanning over 60 ft [pub Enclos]\nunder the roof, set back ~19 m behind the tip '
           '[inf: 705-ft hall\ncentred in the 252.9-m roof; photo i4 ~21 m]; outline and mullions not\npublished [unk]; open cantilever in front of it', 'unk', fs=4.0)
    V.ax.fill_between([-WALL['band'][1], -WALL['band'][0]], [L3] * 2, [WH] * 2, color='#f6e3cf', lw=0, zorder=2.1, alpha=0.8)
    V.line([(xw, L3), (xw, WH)], 'inf', lw=1.0)
    hall_conflict(V, sign=-1, y=L3 - 4.5)
    V.line([(-HW - 4, L3), (HW + 12, L3)], 'inf', lw=0.5)
    V.level(HW + 2, L3, f'+{L3} level 3 / curb ({L3R[0]}-{L3R[1]}) [inf]', 'inf', len_mm=5, fs=4.2, u_line=HW)
    V.level(HW + 2, H_TIP, f'+{H_TIP:.1f} roof tip fascia ({TIP_RNG[0]:.0f}-{TIP_RNG[1]}) [obs, low]', 'obs', len_mm=5, fs=4.2, u_line=HW)
    V.level(HW + 2, H_TIP - 1.5, 'tip depth ~1.5 m (truss taper) [inf]', 'inf', len_mm=5, fs=4.0, u_line=HW)
    V.level(HW + 2, WH, f'+{WH} west glass-wall head [obs photo]', 'obs', len_mm=5, fs=4.0, u_line=xw)
    V.level(-HW - 2, H_PEAK, '+40.08 humps [inf: DOF-anchored fit]', 'inf', side='left', len_mm=5, fs=4.2, u_line=-HW)
    V.dim((-HW, 0), (HW, 0), -7, f'{F["W"]:.2f} m eave to eave [obs]', 'obs', fs=4.6)
    V.dim((xw, L3 + 1), (HW, L3 + 1), 3, f'{HW - xw:.1f} ({HW + WALL["band"][1]:.1f}-{HW + WALL["band"][0]:.1f}) eave overhang [inf]', 'inf', fs=3.9)
    V.text((-HW + 2, 4), 'E (airside)', 'unk', fs=4.0, color='#555555', style='normal')
    V.text((HW - 2, 4), 'W (landside)', 'unk', fs=4.0, color='#555555', style='normal')
    V.text((0, 6.5), 'levels 1-2 (services, arrivals) and the airside building east of the hall: not dimensioned in any source [unk]', 'unk', fs=3.8)


def sheet_elev():
    S = Sheet('BI-02', 'International Terminal main hall: west (landside) elevation and north end elevation', 'A1',
              subtitle='Spec: tools/buildings/spec_itb.json (roof.profile, level3.floor, facade.*); photos i1 / i3 / i4 (reference)')
    V1 = S.view(0, 330, S.vw, 240, 400, (0, 23), title='1  WEST (LANDSIDE) ELEVATION, looking ENE (u: + towards Boarding Area A)', kind='elev', frame=False)
    west_elev(V1); r3_hall(V1); V1.scalebar(y_mm=6)
    V2 = S.view(0, 6, 420, 280, 250, (0, 22), title='2  NORTH END ELEVATION, looking SSE', kind='elev', frame=False)
    north_elev(V2); V2.scalebar(y_mm=6)
    rows = [('Eave profile |u| 27-126 m', f'35.7 -> 40.08 -> {H_TIP:.1f} m', 'obs', 'NAIP: west eave vs the straight facade-base line, 0.955 k h; even-polynomial fit, rms 0.20 m; '
             'beyond the humps held non-increasing (the fit\'s upturn at |u| 123 is an end artefact; raw stations and photo fall to the tips)'),
            ('Second method (photo)', 'drops 4.91 / 4.62 m', 'obs', 'public-domain frontal photo; NAIP drops 3.83 / 5.68 m'),
            ('DOF roof tops', '39.93 / 40.23 m', 'pub', 'DOF 131/132 ft at u +57.2 / -58.4, 0.8-1.1 m inside the west eave'),
            ('Humps (fitted peak |u| 67)', '40.08 m', 'inf', 'fit anchored on the DOF mean at its peak: 0.23 / 0.45 m below the DOF at their stations'),
            ('Centre arch crown', '40.1 m +-2', 'obs', 'photo only (i4 reads it level with the humps, ~41)'),
            ('Glass-wall head', f'{WH} m +-1.5', 'obs', 'photo i4: 9.3 m below the wing crest'),
            ('Roof "90 ft" / "100 ft" above the floor', f'-> L3 = 40.1 - 90 ft / - 100 ft = 12.7 / 9.6 m', 'inf', 'Smith-Emery (60 to 90 ft) / sfgate2000 (100 ft); surface not stated'),
            ('Great hall interior', '705 x 210 x up to 83 ft', 'pub', 'SEAONC; interior, not the roof (the app uses it as the roof)'),
            ('Stories', '5', 'pub', 'L1 services, L2 arrivals, L3 departures, L4-5 offices / lounges'),
            ('Ground at the ITB', '8 ft AMSL', 'inf', 'DOF AMSL - AGL')]
    S.table(430, 290, 305, 'Heights and their sources', rows, fs=4.1, col=(0.36, 0.22))
    S.note('Roof: spec roof.profile full_curve eased into the 35.7 m notches; beyond the humps held non-increasing to the '
           f'{H_TIP:.1f} m tip (the fit\'s upturn at |u| 123 is an end artefact). Centre arch: one photo, +-2 m (blue band). Symmetric by fit.')
    S.note('Facade from photos (reference only): glass wall on the departures curb (L3), level-topped ~9.3 m below the crest; trusses '
           'exposed above; columns in front of the glass, each branching into 4-6 members; canopy ~4.5-6 m above the curb, its hangers on the '
           '40-ft grid and at +-30 / +-90 ft; the hall ends ~19-21 m short of each tip.')
    S.note('Not published: mullion module, fascia depth, canopy depth, the end-wall outline, the lower building masses. They need SFO record drawings.')
    r3_notes(S, ('BI-02',))
    S.note('Hall width CONFLICT: 210 ft = 64.0 m [pub SEAONC] does not fit under the measured 65.4-m roof east of the west wall (at most '
           f'{HW - WALL["band"][0]:.1f} m with the wall at its westmost reading). Resolutions: the wall nearer the eave; the hall running east under a '
           'lower roof (the measured east edge is a "fascia -> lower roof fall"); or a wider roof (SOM concept sketch "866\' x 260\'"). Drawn: '
           'the published width measured from the west wall, ending beyond the east eave.')
    return S.finish()


def sheet_section():
    S = Sheet('BI-03', 'International Terminal main hall: long section on the centre truss line and cross section at the inner column line', 'A1',
              subtitle='Spec: tools/buildings/spec_itb.json (roof.*, level3.floor, hall.*); structure in part inferred')
    V1 = S.view(0, 330, S.vw, 240, 400, (0, 21), title='1  LONG SECTION along the roof axis (v = 0, centre truss line), looking ENE', kind='elev', frame=False)
    us = np.linspace(-HL, HL, 500)
    V1.ax.fill_between([-HL - 25, HL + 25], [-4, -4], [0, 0], color='#dddddd', lw=0, zorder=1)
    V1.line([(-HL - 25, 0), (HL + 25, 0)], 'pub', lw=0.8)
    draw_roof_profile(V1, us)
    V1.line([(u, roof_line(u) - depth(u)) for u in us if abs(u) >= 27.4], 'inf', lw=0.8, z=4)
    for s in (-1, 1):
        uu = np.linspace(s * 27.4, s * HL, 60)
        V1.ax.fill_between(uu, [roof_line(u) - depth(u) for u in uu], [roof_line(u) for u in uu], color='#f6e3cf', lw=0, zorder=2)
        for cu in COL_U:
            V1.poly([(s * cu - 0.6, L3), (s * cu + 0.6, L3), (s * cu + 0.6, roof_line(s * cu) - depth(s * cu)), (s * cu - 0.6, roof_line(s * cu) - depth(s * cu))], 'inf', fc='#b35900', z=4)
    V1.line([(u, WH + 1.0 + 1.2 * math.cos(math.pi * u / 54.8)) for u in np.linspace(-27.4, 27.4, 40)], 'unk', lw=0.6)
    V1.text((0, 27.0), 'central section 180 ft [pub, snippet only]: glazed lens skylights on\nbowstring trusses, arch to the crown (photo); bottom chord form unknown [unk]', 'unk', fs=3.9)
    hl = HALL_HL
    V1.poly([(-hl, L3 - 0.8), (hl, L3 - 0.8), (hl, L3), (-hl, L3)], 'inf', fc='#999999', z=3)
    V1.level(HL + 2, L3, f'+{L3} level 3 departures floor ({L3R[0]}-{L3R[1]}) [inf]', 'inf', len_mm=6, fs=4.2, u_line=hl)
    V1.level(HL + 2, L3 + 83 * FT, f'+{L3 + 83 * FT:.1f} great hall "up to 83 ft" above L3 [pub height, inf datum]', 'inf', len_mm=6, fs=4.2, u_line=hl)
    V1.dim((-hl, L3 - 1), (hl, L3 - 1), -10, '705 ft = 214.9 m great hall [pub SEAONC]; ticket lobby 700 ft [pub]', 'pub', fs=4.4)
    V1.dim((-57.9, 4), (57.9, 4), 0, '380 ft centre span between the inner column lines [pub]; DOF pair 115.5 m apart [obs]', 'pub', fs=4.2, ext=False)
    V1.dim((82.3, 4), (82.3 + 160 * FT, 4), 0, '160 ft end cantilever [pub]', 'pub', fs=4.0, ext=False)
    V1.dim((82.3, 7), (HL, 7), 0, f'{HL - 82.3:.1f} m visible [obs/inf]', 'obs', fs=4.0, ext=False)
    for cu in COL_U:
        V1.dim((cu, roof_line(cu) - depth(cu)), (cu, roof_line(cu)), 3, '29 ft max [pub]' if cu < 60 else '', 'pub', fs=3.8)
    V1.leader((70, roof_line(70) - 4.4), 30, -14, 'double-cantilever "football" trusses (three chords), 5 sets [pub]; depth up to 29 ft over the\n'
              'supports [pub]; taper to the tips and the centre section drawn linearly [inf]; trusses "up to 320 ft long" [snippet]', 'inf', fs=3.9)
    V1.leader((57.9, L3 + 8), -20, -8, 'columns rising from the level-3 floor\n(4 per truss line, 20 in all) [pub count; positions inf]', 'inf', fs=3.9, ha='right')
    V1.text((0, -2.5), 'base isolation: 267 friction-pendulum isolators [pub]; foundations not dimensioned [unk]', 'pub', fs=3.9)
    V1.level(HL + 2, H_PEAK, '+40.08 humps [inf: DOF-anchored fit]', 'inf', len_mm=6, fs=4.2, u_line=67)
    for oas, (p, ft) in DOF_ROOF.items():
        u = float(np.dot(np.asarray(p) - F['c'], F['ax']))
        V1.mark((u, ft * FT), 'pub', marker='v', ms=4)
        V1.text((u, ft * FT + 2.6), f'DOF {ft} ft = {ft * FT:.2f} [pub]', 'pub', fs=3.7)
    V1.level(-HL - 2, CROWN + 0.0001, f'+{CROWN} centre crown (photo, +-2) [obs]', 'obs', side='left', len_mm=6, fs=4.2, u_line=0)
    V1.level(-HL - 2, H_TIP, f'+{H_TIP:.1f} tip ({TIP_RNG[0]:.0f}-{TIP_RNG[1]}) [obs, low]', 'obs', side='left', len_mm=6, fs=4.2, u_line=-HL)
    r3_hall(V1); r3_notes(S, ('BI-03',))
    V1.scalebar(y_mm=6)
    # cross section at u = +57.9 (looking NNW: right hand = ENE = +v)
    V2 = S.view(0, 6, 420, 280, 250, (-2, 22), title='2  CROSS SECTION at the inner column line u = +57.9 m, looking NNW', kind='elev', frame=False)
    h0 = wing(57.9); d0 = depth(57.9); vw = WALL['v']; vc = vw - 2.5
    V2.ax.fill_between([-HW - 22, HW + 18], [-3, -3], [0, 0], color='#dddddd', lw=0, zorder=1)
    V2.line([(-HW - 22, 0), (HW + 18, 0)], 'pub', lw=0.8)
    V2.poly([(-HW, h0 - 1.0), (HW, h0 - 1.0), (HW, h0), (-HW, h0)], 'obs', fc='#999999', z=3)
    V2.text((0, h0 + 4.2), f'roof top {h0:.1f} m at u 57.9 (eave profile: NAIP shape [obs], DOF-anchored at its peak [inf]); cross camber unknown - drawn flat [unk]',
            'inf', fs=4.0)
    for oas, (p, ft) in DOF_ROOF.items():
        uu = float(np.dot(np.asarray(p) - F['c'], F['ax'])); vv = float(np.dot(np.asarray(p) - F['c'], F['v']))
        V2.mark((vv, ft * FT), 'pub', marker='v', ms=4.5)
        V2.leader((vv, ft * FT), -10 if ft == 131 else 6, 7 if ft == 131 else 12, f'DOF {oas} {ft} ft = {ft * FT:.2f} [pub]\nat u {uu:+.1f}, v {vv:.1f}'
                  + (' (mirror station)' if uu < 0 else ''), 'pub', fs=3.6)
    for v in LINES_V:
        V2.poly([(v - 1.2, h0 - d0), (v + 1.2, h0 - d0), (v + 1.2, h0 - 1), (v - 1.2, h0 - 1)], 'inf', fc='#f6e3cf', z=3)
    for v in LINES_V[1:]:
        V2.poly([(v - 0.6, L3), (v + 0.6, L3), (v + 0.6, h0 - d0), (v - 0.6, h0 - d0)], 'inf', fc='#b35900', z=4)
    # west line: column in front of the glass, branching into the outer truss; the wall behind it
    V2.poly([(vc - 0.75, L3), (vc + 0.75, L3), (vc + 0.75, WH), (vc - 0.75, WH)], 'inf', fc='#ffffff', z=4.5, lw=0.8)
    for tv, th in ((LINES_V[0], h0 - d0 / 2), (-HW + 1.5, h0 - 1.5), ((LINES_V[0] + LINES_V[1]) / 2, h0 - d0 + 0.5)):
        V2.line([(vc, WH), (tv, th)], 'inf', lw=0.9, z=4.4, color='#8c8c8c')
    V2.ax.fill_between(list(WALL['band']), [L3] * 2, [WH] * 2, color='#f6e3cf', lw=0, zorder=2.2, alpha=0.8)
    V2.line([(vw, L3), (vw, WH)], 'inf', lw=1.2, z=4.6)
    V2.line([(WALL['v_l3'], L3), (WALL['v_l3'], WH)], 'inf', lw=0.4, ls=(0, (1, 1.5)), z=4.6)
    # sight line from the wall's foot to the NAIP camera (frame model): hidden by any canopy deeper than ~2 m
    V2.line([(WALL['v_l3'], L3), (WALL['v_l3'] - WALL['k'] * (CANOPY + 3 - L3), CANOPY + 3)], 'inf', lw=0.4, ls=(0, (3, 1, 1, 1)), z=4.7)
    hall_conflict(V2, sign=1, y=L3 + 3.0)
    V2.line([(vw, WH), (LINES_V[0] + 1.2, WH)], 'unk', lw=0.5)
    V2.poly([(-HW - 16, L3 - 1.0), (vw, L3 - 1.0), (vw, L3), (-HW - 16, L3)], 'inf', fc='#c9c9c9', z=3)
    V2.line([(vw, CANOPY), (vw - CANOPY_D, CANOPY)], 'inf', lw=1.0)
    V2.poly([(vw + 0.5, L3 - 0.8), (HW - 0.5, L3 - 0.8), (HW - 0.5, L3), (vw + 0.5, L3)], 'inf', fc='#999999', z=3)
    b0, b1 = WALL['band']
    V2.leader((vw, WH - 3), -16, -2, f'west glass wall (3 layers of frit) [pub] on the departures curb [inf]: band v {b0:.1f} to {b1:.1f}\n'
              f'(orange), drawn at its middle {vw:.1f}. The NAIP facade-base line [obs] reads {WALL["v_grade"]:.1f} at grade;\n'
              f'the canopy ({CANOPY_D:.0f} m deep [inf]) hides the wall foot from the camera (sight line dash-dot:\n{WALL["k"]:.2f} m/m -> '
              f'{WALL["foot_hidden_depth"]:.1f} m at canopy height), so the line is the canopy edge (-> {b1:.1f})\nor the wall above the canopy '
              f'(-> {b0:.1f}); dotted {WALL["v_l3"]:.1f} = foot on L3, only with a canopy\n<= 2 m deep; head +{WH} [obs photo]', 'inf', fs=3.8, ha='right')
    V2.leader((vc, (L3 + WH) / 2), -12, 8, 'column stands clear in front of the glass and branches into the\nouter truss [obs photos i3 / i4]; '
              'its v is not measured [unk] -\ndrawn 2.5 m in front of the wall [inf]', 'inf', fs=3.8, ha='right')
    V2.text((-HW - 10, L3 + 1.5), 'departures roadway / curb', 'inf', fs=3.6)
    V2.text((vw - 2.5, CANOPY + 1.2), 'entrance canopy [pub SEAONC];\ndepth ~5 m [inf]', 'inf', fs=3.4)
    V2.text((HW + 1.5, 24), 'east: cherry-wood high wall\n(interior) [pub]; position\nunknown [unk]; dashed = 210 ft\nfrom the west wall [inf]', 'unk', fs=3.9, ha='left')
    for a, b in zip(LINES_V[:-1], LINES_V[1:]):
        V2.dim((a, L3 - 1), (b, L3 - 1), -4, f'{SP:.2f}', 'obs', fs=4.0)
    V2.dim((-HW, 0), (HW, 0), -8, f'{F["W"]:.2f} m eave to eave [obs]; outer truss line to eave ~8.4 m [obs]', 'obs', fs=4.4)
    V2.dim((-HW, h0 - 1.0), (vw, h0 - 1.0), 2.5, f'{vw + HW:.1f} ({b0 + HW:.1f}-{b1 + HW:.1f}) eave overhang [inf]', 'inf', fs=3.9)
    V2.dim((LINES_V[4] + 1.2, h0 - d0), (LINES_V[4] + 1.2, h0), 4, '29 ft [pub]', 'pub', fs=4.0)
    V2.level(HW + 2, L3, f'+{L3} level 3 ({L3R[0]}-{L3R[1]}) [inf]', 'inf', len_mm=5, fs=4.2, u_line=HW)
    V2.level(HW + 2, WH, f'+{WH} glass-wall head [obs photo]', 'obs', len_mm=5, fs=4.2, u_line=vw)
    V2.level(HW + 2, h0, f'+{h0:.1f} roof [obs]', 'obs', len_mm=5, fs=4.2, u_line=HW)
    V2.scalebar(y_mm=6)
    rows = [('Five balanced double-cantilever truss sets, linked by bowstring trusses', 'roof form', 'pub', 'SEAONC, MSC 2000, SOM, Smith-Emery'),
            ('Truss depth (max, over supports)', '29 ft = 8.84 m', 'pub', 'SEAONC'),
            ('Centre span / end cantilever / overall', '380 / 160 / 860 ft', 'pub', 'SEAONC; 860 ft conflicts with NAIP 830 ft'),
            ('Truss length / centre section', '320 / 180 ft', 'pub', 'MSC 2000 snippet only (AISC PDF unreadable)'),
            ('Columns', '20 from level 3', 'pub', 'SEAONC; positions inferred (5 lines x 4); west line in front of the glass [obs photo]'),
            ('Steel', 'Herrick; ~35 pieces by barge', 'pub', 'MSC 2000, SEAONC'),
            ('Isolators', '267 friction pendulum', 'pub', 'Enclos, SEAONC')]
    S.table(430, 290, 305, 'Structure (published) and what is inferred', rows, fs=4.1, col=(0.40, 0.22))
    S.note('The section is a measured roof top (NAIP eave profile anchored on the FAA DOF roof tops) over an INFERRED structure: '
           'column positions from the published spans, truss depth published as a maximum only.')
    S.note('Level 3 = DOF roof top minus "100 ft" (sfgate2000) / "90 ft" (Smith-Emery) / the 83-ft hall height: 9.6-14.8 m, 11.5 adopted - no drawing or survey found.')
    S.note('West wall [inf]: the NAIP straight line fixes the wall only together with what it images. The curb canopy (SEAONC: "760 tons of '
           'exposed steel at the ITB departures level window walls and entrance canopy"; ~5 m above L3 and ~5 m deep in photos) hides the wall\'s '
           'foot from the camera if deeper than ~2 m, so the line is the canopy edge or the wall just above it: band v -28.3 to -23.3. The '
           'earlier -26.3 (foot on L3) holds only for a canopy <= 2 m deep.')
    S.note('Hall width CONFLICT: 210 ft = 64.0 m [pub] against at most 61.0 m under the roof east of the wall (55.9-61.0 over the band). '
           'Resolutions: the wall nearer the eave; the hall continuing east under a lower roof (east edge = "fascia -> lower roof fall"); a '
           'wider roof (SOM concept sketch 260 ft). Drawn: the published width from the west wall (dashed), 5.5 m beyond the east eave.')
    return S.finish()


# ------------------------------------------------------------------------------------------------ piers (BI-04)
# Boarding Areas A and G: long (apron) faces and cross sections with the pods and the BA-G pod-3 end box (review r2-29,
# r2-30). Pier frames as tools/buildings/itb_pods.py (s along the pier away from the ITB, t across).
BODY_S = {'A': (-130.0, 169.4), 'G': (-140.0, 235.1)}   # pier body along s: SFO Museum outline; beyond it, the junction /
                                                         # connector to the ITB (s profile of the outline, width ~38-39 m)


def _pf(key):
    P = PODS['piers'][key]
    return np.array(P['centre_xz'], float), np.array(P['s_axis'], float), np.array(P['t_axis'], float)


def _st(key, ring):
    c, ax, n = _pf(key); r = np.asarray(ring, float) - c
    return np.c_[r @ ax, r @ n]


def _cut(key, ring, s0):
    """t interval of a ring (world) on the cross line s = s0 (pier frame)."""
    from shapely.geometry import Polygon, LineString
    g = LineString([(s0, -200), (s0, 200)]).intersection(Polygon(_st(key, ring)).buffer(0))
    return (g.bounds[1], g.bounds[3]) if not g.is_empty else None


def _pier_elev(V, key, sign):
    """long-face elevation of one pier: plot x = sign * s."""
    P = PODS['piers'][key]; hm = P['h_main_roof']; r0, r1 = P['h_main_range']; s0, s1 = BODY_S[key]
    X = lambda s: sign * s  # noqa: E731
    xa, xb = sorted((X(s0 - 25), X(s1 + 15)))
    V.ax.fill_between([xa, xb], [-3, -3], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(xa, 0), (xb, 0)], 'pub', lw=0.8)
    V.poly([(X(s0), 0), (X(s1), 0), (X(s1), hm), (X(s0), hm)], 'obs', fc='#eef3f8', z=2, lw=0.8)
    V.ax.fill_between(sorted([X(s0), X(s1)]), [r0, r0], [r1, r1], color='#9cc3e0', alpha=0.25, lw=0, zorder=2.1)
    V.poly([(X(s0 - 22), 0), (X(s0), 0), (X(s0), hm), (X(s0 - 22), hm)], 'unk', fc='none', z=2, lw=0.5)
    V.text((X(s0 - 11), hm / 2), 'junction /\nconnector\nto the ITB\n[unk]', 'unk', fs=3.4)
    pods = [p for p in PODS['pods'] if p['pier'] == key]
    for p in pods:
        st = _st(key, p['ring_true_xz']); a, b = st[:, 0].min(), st[:, 0].max()
        if p['id'].endswith('box'):
            base = POD['G3']['top_m']; t0, t1 = p['top_main_value_m']; top = p['top_m']
            V.poly([(X(a), base), (X(b), base), (X(b), top), (X(a), top)], 'obs', fc='#f3dcc0', z=3.2, lw=0.7)
            V.ax.fill_between(sorted([X(a), X(b)]), [t0, t0], [t1, t1], color='#e0a060', alpha=0.35, lw=0, zorder=3.3)
            V.ax.fill_between(sorted([X(a) + sign * 0.6, X(b) - sign * 0.6]), [top - 2.6] * 2, [top - 1.2] * 2, color='#55606a', lw=0, zorder=3.4)
            for xx in np.linspace(X(a) + sign * 1.5, X(b) - sign * 1.5, 3):
                V.line([(xx, top), (xx, top + 5.0)], 'obs', lw=0.35, z=3.4, color='#55606a')
            continue
        top = p['top_m']
        V.poly([(X(a), hm), (X(b), hm), (X(b), top), (X(a), top)], 'obs', fc='#d6e6f5', z=3, lw=0.7)
        V.text(((X(a) + X(b)) / 2, (hm + top) / 2), p['id'], 'obs', fs=3.6, bg=False, z=3.5)
        V.dim((X(a), top), (X(b), top), 3 if sign > 0 else -3, f"{p['length_m']:.1f} [obs]", 'obs', fs=3.5)
    return pods


def sheet_piers():
    S = Sheet('BI-04', 'International Terminal: Boarding Areas A and G - long-face elevations and cross sections with the roof pods', 'A1',
              subtitle='Spec: spec_itb.json (ba_a.*, ba_g.*); pods / end box: itb_pods.json (NAIP 2024 trace, tools/buildings/itb_pods.py)')
    A_ = [POD[k] for k in ('A1', 'A2', 'A3')]; G_ = [POD[k] for k in ('G1', 'G2', 'G3')]; BX = POD['G3-box']
    PA, PG = PODS['piers']['A'], PODS['piers']['G']
    # ---------------- V1 BA-G apron (NNE) face, looking SSW: x = +s (right = WNW, away from the ITB)
    V1 = S.view(0, 395, S.vw, 172, 750, (50, 22), title='1  BOARDING AREA G: north-north-east (apron) face, looking SSW (left: the ITB)', kind='elev', frame=False)
    _pier_elev(V1, 'G', +1)
    s0, s1 = BODY_S['G']
    V1.dim((s0, -2), (s1, -2), -5, f'{s1 - s0:.0f} m pier body (SFO Museum outline) [obs]', 'obs', fs=4.2)
    V1.level(s1 + 3, PG['h_main_roof'], f"+{PG['h_main_roof']} main roof ({PG['h_main_range'][0]:.0f}-{PG['h_main_range'][1]:.0f}, blue band) [obs, low]", 'obs', len_mm=5, fs=4.0, u_line=s1)
    V1.level(s1 + 3, G_[2]['top_m'], f"+{min(p['top_m'] for p in G_)}-{max(p['top_m'] for p in G_)} pod tops: rise {min(p['rise_m'] for p in G_)}-"
             f"{max(p['rise_m'] for p in G_)} m [obs, low]", 'obs', len_mm=5, fs=4.0, u_line=s1)
    V1.level(s1 + 3, BX['top_m'], f"+{BX['top_main_value_m'][0]}-{BX['top_main_value_m'][1]} end box (orange band) [obs, low]", 'obs', len_mm=5, fs=4.0, u_line=s1)
    sb = _st('G', BX['ring_true_xz'])[:, 0].mean()
    V1.leader((sb, BX['top_m'] + 2.0), -30, 9, 'END BOX on pod G3 (~8 x 9 m, set back ~1 m from the pod end) [obs, NAIP 2024]: NAIP band of its WNW face\n'
              f"{BX['band_box_face_m']} m above the pod-end band {BX['band_pod_end_m']} m -> {BX['rise_above_pod_m'][0]}-{BX['rise_above_pod_m'][1]} m above the pod roof "
              f"(face + shadow .. face only).\nPhoto d2 (wbaiv, 2018-09-08, CC BY 4.0): a box-shaped cab with a dark window band and antennas on a raised roof volume,\n"
              'about as high again above it as the volume above the main roof [obs photo]. Window band / antennas drawn schematic [inf];\n'
              'function: ramp-control cab (LiveATC lists "Ramp G (West)") [inf, NOT confirmed by any SFO source]', 'inf', fs=3.8, ha='right')
    V1.text((40, 6.0), 'apron level + level 2 (arrivals, sterile corridor) + level 3 (departures concourse) [pub tutor_bag]; floor heights not dimensioned [unk].\n'
            'Facade: metallic-finish composite aluminium panels and a tinted glazed curtain wall [pub]; bay layout not measured [unk]', 'unk', fs=3.8)
    V1.scalebar(y_mm=4)
    # ---------------- V2 BA-A apron (ESE) face, looking WNW: x = -s (right = NNE, the ITB)
    V2 = S.view(0, 213, S.vw, 172, 750, (-60, 22), title='2  BOARDING AREA A: east-south-east (apron) face, looking WNW (right: the ITB)', kind='elev', frame=False)
    _pier_elev(V2, 'A', -1)
    s0, s1 = BODY_S['A']
    V2.dim((-s1, -2), (-s0, -2), -5, f'{s1 - s0:.0f} m pier body (SFO Museum outline) [obs]', 'obs', fs=4.2)
    sd = float(_st('A', [DOF_POD[0]])[0, 0])
    V2.mark((-sd, DOF_POD[1] * FT), 'pub', marker='v', ms=4)
    V2.leader((-sd, DOF_POD[1] * FT), 8, 10, 'FAA DOF 06-035352: 85 ft = 25.91 m [pub]\n(1A: +-20 ft H, +-3 ft V) at pod A1\'s NNE end', 'pub', fs=3.7)
    V2.level(-s1 - 3, PA['h_main_roof'], f"+{PA['h_main_roof']} main roof ({PA['h_main_range'][0]}-{PA['h_main_range'][1]}) [obs]", 'obs', side='left', len_mm=5, fs=4.0, u_line=-s1)
    V2.level(-s1 - 3, A_[0]['top_m'], f"+{A_[2]['top_m']}-{A_[0]['top_m']} pod tops ({A_[2]['top_range_m'][0]}-{A_[0]['top_range_m'][1]}) [obs, low]", 'obs', side='left', len_mm=5, fs=4.0, u_line=-s1)
    V2.line([(-s1 - 6.75, 17.2), (-s1, 17.2)], 'obs', lw=0.35)
    V2.line([(-s1 - 6.75, 5.2), (-s1 - 6.75, 17.2)], 'obs', lw=0.35)
    V2.level(-s1 - 3, 5.2, 'glazed gate-room bays ~5.2-17.2 m (photo a2, +-1.5) [obs photo]', 'obs', side='left', len_mm=5, fs=3.6, u_line=-s1)
    V2.text((-20, 3.0), 'glazed gate-room bays (two passenger levels) alternate with metal panels; bay positions along the face not measured [unk] (photo a2,\n'
            'Pi.1415926535, Sept 2025, CC BY-SA 4.0: BA-A from the east). Apron level below; floor heights not dimensioned [unk]', 'unk', fs=3.6)
    V2.scalebar(y_mm=4)
    # ---------------- table
    rows = [('BA-A pods A1 / A2 / A3: length', ' / '.join(f"{p['length_m']}" for p in A_) + ' m', 'obs', 'NAIP 2024 trace (imaged roof edges; ends by eye, WNW arc scanned)'),
            ('BA-A pods: width (arc apex - ESE side)', f"~{A_[0]['width_m']} m", 'obs', 'ESE side a weak line only (all three pods)'),
            ('BA-A pods: rise / top', f"{A_[2]['rise_m']}-{A_[0]['rise_m']} / {A_[2]['top_m']}-{A_[0]['top_m']} m", 'obs', f"WNW band {A_[0]['band_wnw_m']} m / {A_[0]['band_coef_per_m']} per m (frame face + shadow); low"),
            ('BA-A pod 1 DOF top', '25.91 m', 'pub', 'FAA DOF 06-035352 (1A); NAIP range reaches 25.0'),
            ('BA-G pods G1 / G2 / G3: length', ' / '.join(f"{p['length_m']}" for p in G_) + ' m', 'obs', 'NAIP 2024 trace; G3 runs under the end box image'),
            ('BA-G pods: width', f"~{G_[1]['width_m']} m", 'obs', 'apexes by eye; edges parabolic between [inf]'),
            ('BA-G pods: rise / top', f"{G_[1]['rise_m']}-{G_[2]['rise_m']} / {G_[1]['top_m']}-{G_[2]['top_m']} m", 'obs', 'WNW end band 2.25-2.5 m, k(x) face + shadow; main roof 13-20 (low)'),
            ('BA-G end box on G3', f"{BX['top_main_value_m'][0]}-{BX['top_main_value_m'][1]} m", 'obs', f"{BX['rise_above_pod_m'][0]}-{BX['rise_above_pod_m'][1]} m above the pod; range {BX['top_range_m'][0]}-{BX['top_range_m'][1]} with the main roof"),
            ('End box function', 'ramp-control cab?', 'inf', 'photo d2 (2018) form + "Ramp G (West)" frequency; unconfirmed'),
            ('Pier glazing (BA-A)', '~5.2-17.2 m', 'obs', 'photo a2, rough; bay positions unknown')]
    S.table(500, 200, 239, 'Boarding-area pods and heights', rows, fs=3.8, col=(0.40, 0.20))
    # ---------------- V3 / V4 cross sections
    for k, (key, pid, x0, w, title, sign) in enumerate((('A', 'A1', 0, 235, '3  BA-A SECTION through pod A1 near its NNE end, looking NNE', 1),
                                                         ('G', 'G3', 245, 245, '4  BA-G SECTION through pod G3 and the end box, looking WNW', -1))):
        P = PODS['piers'][key]; hm = P['h_main_roof']; r0, r1 = P['h_main_range']
        if key == 'A': sc = float(_st('A', POD['A1']['ring_true_xz'])[:, 0].min()) + 8.0   # near the NNE end (DOF station)
        else: sc = float(_st('G', BX['ring_true_xz'])[:, 0].mean())
        body = _cut(key, D.outer_rings(P['name'], 'boardingAreas')[0], sc); pod = _cut(key, POD[pid]['ring_true_xz'], sc)
        tc = 0.5 * (body[0] + body[1])
        V = S.view(x0, 8, w, 190, 400, (sign * tc, 18), title=title, kind='elev', frame=False)
        X = lambda t: sign * t  # noqa: E731
        V.ax.fill_between(sorted([X(body[0] - 14), X(body[1] + 14)]), [-2, -2], [0, 0], color='#dddddd', lw=0, zorder=1)
        V.line([(X(body[0] - 14), 0), (X(body[1] + 14), 0)], 'pub', lw=0.8)
        V.poly([(X(body[0]), 0), (X(body[1]), 0), (X(body[1]), hm), (X(body[0]), hm)], 'obs', fc='#eef3f8', z=2, lw=0.8)
        V.ax.fill_between(sorted([X(body[0]), X(body[1])]), [r0, r0], [r1, r1], color='#9cc3e0', alpha=0.25, lw=0, zorder=2.1)
        top = POD[pid]['top_m']
        V.poly([(X(pod[0]), hm), (X(pod[1]), hm), (X(pod[1]), top), (X(pod[0]), top)], 'obs', fc='#d6e6f5', z=3, lw=0.8)
        V.dim((X(body[0]), -1), (X(body[1]), -1), -5 if sign > 0 else 5, f'{body[1] - body[0]:.1f} m (SFO Museum outline at this station) [obs]', 'obs', fs=4.0)
        V.dim((X(pod[0]), top), (X(pod[1]), top), 3 if sign > 0 else -3, f'{pod[1] - pod[0]:.1f} pod [obs]', 'obs', fs=3.8)
        V.dim((X(body[1]) + sign * 3, 0), (X(body[1]) + sign * 3, hm), -3 if sign > 0 else 3, f'{hm}', 'obs', fs=3.8)
        V.dim((X(pod[1]) + sign * 2, hm), (X(pod[1]) + sign * 2, top), -3 if sign > 0 else 3, f"+{POD[pid]['rise_m']}", 'obs', fs=3.8)
        V.text((X(tc), hm / 2), 'apron level + 2 passenger levels:\nfloors not dimensioned [unk]', 'unk', fs=3.8)
        if key == 'A':
            td = float(_st('A', [DOF_POD[0]])[0, 1])
            V.mark((X(td), DOF_POD[1] * FT), 'pub', marker='v', ms=4)
            V.leader((X(td), DOF_POD[1] * FT), -6, 8, 'DOF 06-035352 25.91 m [pub]\n(+-6.1 m horizontally: at the\npod\'s WNW rim or the eave)', 'pub', fs=3.6, ha='right')
            V.leader((X(pod[0]), top), -8, -18, f"curved WNW rim [obs]; top {top} ({POD[pid]['top_range_m'][0]}-{POD[pid]['top_range_m'][1]}) [obs, low]", 'obs', fs=3.6, ha='right')
            V.leader((X(pod[1]), (hm + top) / 2), 10, 8, 'straight ESE side [obs, weak]', 'obs', fs=3.6)
            V.text((X(body[1]) + 8, -1.0), 'right: ESE (apron) face', 'unk', fs=3.4, color='#555555', style='normal')
        else:
            bx = _cut('G', BX['ring_true_xz'], sc); t0, t1 = BX['top_main_value_m']; bt = BX['top_m']
            V.poly([(X(bx[0]), top), (X(bx[1]), top), (X(bx[1]), bt), (X(bx[0]), bt)], 'obs', fc='#f3dcc0', z=3.2, lw=0.8)
            V.ax.fill_between(sorted([X(bx[0]), X(bx[1])]), [t0, t0], [t1, t1], color='#e0a060', alpha=0.35, lw=0, zorder=3.3)
            V.ax.fill_between(sorted([X(bx[0]) + sign * 0.3, X(bx[1]) - sign * 0.3]), [bt - 2.6] * 2, [bt - 1.2] * 2, color='#55606a', lw=0, zorder=3.4)
            V.dim((X(bx[0]), bt), (X(bx[1]), bt), -3, f'{bx[1] - bx[0]:.1f} box [obs]', 'obs', fs=3.8)
            ur = max(X(body[0]), X(body[1])) + 2.0
            V.level(ur, bt, f'+{t0}-{t1} box top (orange band) [obs, low]', 'obs', len_mm=4, fs=3.8, u_line=max(X(bx[0]), X(bx[1])))
            V.level(ur, top, f'+{top} pod top [obs, low]', 'obs', len_mm=4, fs=3.8, u_line=max(X(pod[0]), X(pod[1])))
            V.text((ur + 6, -1.0), 'right: NNE (apron) face', 'unk', fs=3.4, color='#555555', style='normal')
            V.leader((X(0.5 * (bx[0] + bx[1])), bt - 1.9), 14, 10, 'dark window band + antennas: as photo d2,\nschematic [inf]', 'inf', fs=3.6)
        V.scalebar(y_mm=4)
    S.note('Pods and the end box are traced on NAIP 2024 in pier frames (BA-A 208.0 deg, BA-G 297.75 deg) and relief-corrected with their own '
           'top heights (BA-A frame model, BA-G k(x), as the main-roof heights). Outlines +-1 m; tools/buildings/itb_pods.py writes itb_pods.json.')
    S.note('Heights: a raised volume\'s dark band on its WNW side = (visible face + shadow) x rise. Low confidence: one image, half-level band '
           'widths, the relief model, and the main-roof ranges (BA-G 13-20 m) all carry into the tops.')
    S.note('BA-A pod 1: NAIP 21.8-25.0 m against the FAA DOF 25.91 m (+-0.9 m): consistent only at the upper ends. The NNE-end DOF point lies '
           'within its 6.1 m horizontal accuracy of the pod\'s WNW rim.')
    S.note('BA-G end box: the only structure on BA-G whose band exceeds the pods\' (checked on all three pods and the pier head; BA-F and the '
           'ITB north end show nothing like it). It stands on NAIP 2024-05-20, so the 2018 photo d2 shows it in place. Its function is '
           'inferred; model it as a closed box with a window band, heights per the band.')
    S.note('Not measured: floor heights, gate-room bay positions, parapets and roof equipment. Photos a2 / d2 are reference only.')
    r3_notes(S, ('BI-04', 'BI-01'))
    return S.finish()

# ------------------------------------------------------------------------------------------------ close-out r3 (buildings-10)
def _itb_geom():
    """the 3-D geometry module (imports this one: imported lazily, at draw time)."""
    import os, sys
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'blender'))
    import itb_geom
    return itb_geom


def r3_hall(V):
    """the 3-D state of the centre section and the curb canopy drawn over BI-02 V1 / BI-03 V1 (u frame): the deck / fascia
    roof_line(u) - crown_cap(u) under the lens vaults (their tops = deck + crown_cap + LOS_DROP), and the canopy slab
    (CANOPY - CANOPY_THK .. CANOPY) - so the sheet is again the reference for tools/blender/itb_geom.py."""
    G = _itb_geom()
    us = np.linspace(-30.0, 30.0, 241)
    deck = [(u, G.roof_top(u)) for u in us]
    vault = [(u, G.roof_top(u) + G.crown_cap(u) + G.LOS_DROP) for u in us if G.crown_cap(u) > 0.01]
    V.line(deck, 'obs', lw=1.0, z=6.2, color='#1f4e79')
    if vault: V.line(vault, 'inf', lw=0.6, z=6.2, ls=(0, (2, 1)))
    V.leader((0.0, G.roof_top(0.0)), 30, -10, f'3-D STATE (review r1 / r2): centre deck / fascia {G.roof_top(0.0):.2f} m at the crown = roof_line - crown cap '
             f'{G.CROWN_CAP:.1f} m\n(1.6 (1 - |x|^3)^0.7 over the lens row) [obs photo i4, low]; lens vaults {G.LOS_DROP:.1f} m above the cap line form '
             'the 40.1-m silhouette [inf]', 'obs', fs=3.6)
    HH = G.HALL_HL
    V.poly([(-HH, G.CANOPY - G.CANOPY_THK), (HH, G.CANOPY - G.CANOPY_THK), (HH, G.CANOPY), (-HH, G.CANOPY)], 'inf', fc='none', lw=0.5, z=6.1)
    V.leader((HH * 0.6, G.CANOPY - G.CANOPY_THK), 20, -12, f'3-D: curb canopy slab {G.CANOPY_THK:.2f} m (close-out r3: soffit {G.CANOPY - G.CANOPY_THK:.2f} m, '
             f'4.67 m over the departures plate); kerb line v {G.KERB_V} [obs NAIP],\nsidewalk {G.CURB_W:.2f} m, no upstand, 0.15-m kerb, 44 bollards '
             '[obs photo i3] (review r2)', 'inf', fs=3.6)


def r3_notes(S, sheets):
    """the manifest's itb.deviations_from_sheets for these sheets as sheet notes (close-out r3, buildings-10): every 3-D change
    not drawn in a view is stated on the sheet with its size and tag (the 3-D builder records them, tools/blender/itb_manifest.py)."""
    import json, os
    try:
        dv = json.load(open(os.path.join(ROOT, 'data', 'buildings3d', 'manifest.json')))['itb'].get('deviations_from_sheets', [])
    except (OSError, ValueError, KeyError):
        return
    for d_ in dv:
        if not any(t in str(d_.get('sheet', '')) for t in sheets): continue
        S.note(f"3-D STATE (manifest itb.deviations_from_sheets, close-out r3) - {d_.get('item', '')}: {d_.get('model', '')} "
               f"[{d_.get('tag', 'inf')}]; the views draw: {d_.get('drawn', '')}")
