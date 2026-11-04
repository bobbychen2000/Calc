"""Sheets of the International Terminal (Senator Dianne Feinstein ITB): main hall wing roof, Boarding Areas A and G,
drawn from tools/buildings/spec_itb.json (verified 2026-11-04, docs/research/buildings_itb.md 'Verification') and its
measurement record tools/buildings/itb_naip_measurements.json:
  BI-01  roof plans: group key plan 1:2500, hall roof 1:750, BA-A 1:2000, BA-G 1:2500 (A1) + NAIP overlay
  BI-02  west (landside) elevation 1:400 and north end elevation 1:250 (A1)
  BI-03  long section along the roof axis 1:400 and cross section at the inner column line 1:250 (A1)
Roof frame: corners of spec roof.corners_obs (frame-model relief correction); u along the axis (+ towards BA-A, SSE),
v across (+ towards ENE). Heights AGL (grade ~8 ft AMSL at the ITB, DOF AMSL - AGL).
"""
import math

import numpy as np

import draw_data as D
from draw_lib import Sheet, FT
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
H_TIP = I['roof.profile']['value']['tip (|u| ~ 126 m)']['h']
L3 = I['level3.floor']['value']
LENS = D.ITBM['lenses']
MAG = 0.99                                             # imaged -> true size at the roof (H-h)/H, h ~ 38 m
DOF_ROOF = {'06-035315': ((-1258.1, 429.4), 131), '06-035316': ((-1292.4, 319.1), 132)}
DOF_POD = ((-1195.3, 555.0), 85)


def UV(u, v):
    return D.itb_uv(F, u, v)


def eave(u):
    a = abs(u)
    if a <= 123: return float(D.itb_eave_h(max(a, 23.0)))
    return float(np.interp(a, [123, HL], [34.83, H_TIP]))


def crown(u):
    """centre-section silhouette (photo, +-2 m): from the notch (|u| 27, 35.7) up to the crown 40.1 at u = 0 [obs]."""
    a = abs(u)
    if a >= 27: return eave(u)
    return 35.7 + (CROWN - 35.7) * math.cos(math.pi * a / 54) ** 2


def depth(u):
    """truss depth [inf]: 29 ft over the supports (pub), tapering linearly to ~1.5 m at the tip and at the centre
    section's ends (|u| 27.4 = 90 ft: the 180-ft central section, snippet)."""
    a = abs(u); d = 29 * FT
    if 57.9 <= a <= 82.3: return d
    if a < 57.9: return float(np.interp(a, [27.4, 57.9], [1.5, d]))
    return float(np.interp(a, [82.3, HL], [d, 1.5]))


def lens_poly(k):
    L = LENS[k]
    uc = (L['u0'] + L['u1']) / 2 * MAG; a = (L['u1'] - L['u0']) / 2 * MAG; b = L['w_max'] / 2 * MAG
    t = np.linspace(-1, 1, 25)
    top = [(uc + a * x, LINES_V[k] + b * (1 - x * x)) for x in t]
    bot = [(uc + a * x, LINES_V[k] - b * (1 - x * x)) for x in t[::-1]]
    return [UV(u, v) for u, v in top + bot], 2 * a, 2 * b


# ------------------------------------------------------------------------------------------------ plan
def draw_hall_roof(V, variant, detail=True):
    C = F['corners']; ring = [C['NW'], C['NE'], C['SE'], C['SW']]
    V.poly(ring, 'obs', fc='#e7eef6' if variant == 'vector' else 'none', lw=0.9, z=3)
    # glazed tip bands
    tn, ts = I['roof.glazed_tips_obs']['value']['north'], I['roof.glazed_tips_obs']['value']['south']
    for u0, u1 in ((-HL, -HL + tn), (HL - ts, HL)):
        V.poly([UV(u0, -HW), UV(u1, -HW), UV(u1, HW), UV(u0, HW)], 'obs', fc='#cfe3f3' if variant == 'vector' else 'none', hatch='||||' if detail else None, z=3.2, lw=0.4)
    for v in LINES_V:
        V.line([UV(-HL + tn, v), UV(HL - ts, v)], 'obs', lw=0.5 if detail else 0.3, z=3.4)
    for k in range(5):
        P, Lk, Wk = lens_poly(k)
        V.poly(P, 'obs', fc='#cfe3f3' if variant == 'vector' else 'none', z=3.6, lw=0.5)
    if detail:
        for cu in COL_U:
            for s in (-1, 1):
                V.line([UV(s * cu, -HW - 4), UV(s * cu, HW + 4)], 'inf', lw=0.4, z=3.5)
                for v in LINES_V:
                    V.mark(UV(s * cu, v), 'inf', marker='s', ms=2.4)
    return ring


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
    V1.leader((-1260, 760), 14, 10, 'Boarding Area A\nroof 17.9 m (16.9-18.8) [obs]\npod 1: 25.9 m (DOF) [pub]', 'obs', fs=4.2)
    V1.leader((-1450, 90), -6, -26, 'Boarding Area G\nroof 17.0 m (13-20) [obs, low]', 'obs', fs=4.2)
    V1.leader((-1500, 560), -4, 14, 'Garage A (context)', 'unk', fs=3.8)
    V1.leader((-1480, 320), -2, -14, 'Garage G (context)', 'unk', fs=3.8)
    V1.text((-1180, 150), 'ITB outline =\nSFO Museum\n"International\nTerminal" [obs]', 'obs', fs=3.8)
    V1.scalebar()
    # ---------------- V2 hall roof plan
    V2 = S.view(232, 0, 270, 570, 750, (-1245, 365), title='2  MAIN HALL WING ROOF: roof plan', kind='plan')
    if bg: V2.background()
    V2.grid(20)
    ring = draw_hall_roof(V2, variant)
    C = F['corners']
    V2.dim(C['NW'], C['SW'], -9, f'{F["L"]:.2f} m eave tip to tip (252.6-255.1) [obs, NAIP relief-corrected]', 'obs', fs=4.6)
    V2.dim(C['NW'] + F['ax'] * (HL - 131.06), C['SW'] + F['ax'] * (131.06 - HL), -19, '860 ft = 262.13 m overall [pub SEAONC, Smith-Emery] - CONFLICT with the obs length', 'pub', fs=4.6)
    V2.dim(C['NE'], C['NW'], -8, f'{F["W"]:.2f} m [obs] (214 ft; hall 210 ft [pub])', 'obs', fs=4.6)
    # truss line spacing
    V2.dim(UV(-60, LINES_V[3]), UV(-60, LINES_V[4]), 0, f'{SP:.2f} [obs] = 40 ft grid [pub]', 'obs', fs=3.8, ext=False)
    V2.dim(UV(HL - 15.75, HW + 1), UV(HL, HW + 1), 5, '15.75 glazed tip [obs]', 'obs', fs=3.8)
    V2.dim(UV(-HL, HW + 1), UV(-HL + 18.75, HW + 1), 5, '18.75 glazed tip [obs]', 'obs', fs=3.8)
    # rhythm chain (published / inferred, ft) along the east side, centred on the roof centre
    edges_ft = [-430, -410, -270, -190, -90, 90, 190, 270, 410, 430]
    for a, b in zip(edges_ft[:-1], edges_ft[1:]):
        V2.dim(UV(a * FT, HW + 2), UV(b * FT, HW + 2), 13, f'{b - a} ft', 'inf', fs=3.8)
    V2.leader(UV(126, HW + 14), -10, -24, 'published / inferred rhythm (ft) [inf]: 20 overhang | 140 truss cantilever |\nouter column | 80 | inner column | 100 | 180 centre section | ... ;\n'
              'centre span 380 ft [pub], end cantilever 160 ft [pub], 860 ft [pub]', 'inf', fs=3.8)
    for cu in COL_U:
        for s in (-1, 1):
            V2.text(UV(s * cu, -HW - 7), f'{"inner" if cu < 60 else "outer"} col. line\nu {s * cu:+.1f} [inf]', 'inf', fs=3.4)
    V2.leader(UV(70, LINES_V[2]), 30, 30, '20 columns = 5 truss lines x 4 (inner / outer column lines at +-190 / +-270 ft) [inf];\n'
              '"20 cantilevered columns rising from the third floor departures level" [pub SEAONC]', 'inf', fs=3.8)
    P, Lk, Wk = lens_poly(2)
    V2.leader(UV(0, LINES_V[2] + 4), 34, 6, f'5 lens skylights on the truss lines, {Lk:.1f} m x {Wk:.1f} m [obs]\n(the westmost {(LENS[0]["u1"] - LENS[0]["u0"]) * MAG:.0f} m); centre section 180 ft [pub, snippet]', 'obs', fs=3.8)
    for oas, (p, ft) in DOF_ROOF.items():
        V2.mark(p, 'pub', marker='^', ms=4.5)
        V2.leader(p, -24, 6 if ft == 132 else -6, f'FAA DOF {oas}: {ft} ft AGL = {ft * FT:.2f} m\n(1A, +-3 ft) roof top [pub]', 'pub', fs=3.8)
    for uu, s in ((0, f'crown {CROWN} (photo, +-2) [obs]'), (-27, 'notch 35.7 [obs]'), (27, 'notch 35.7 [obs]'), (-67, 'hump 40.08 [pub DOF]'), (67, 'hump 40.08 [pub DOF]'),
                  (-100, '36.4 [obs]'), (100, '36.4 [obs]'), (-124, f'tip {H_TIP} [obs]'), (124, f'tip {H_TIP} [obs]')):
        V2.mark(UV(uu, -HW), 'obs', marker='o', ms=2.0)
        V2.text(UV(uu, -HW - 2.5), s, 'pub' if 'DOF' in s else 'obs', fs=3.6, ha='right', rot=0)
    V2.text(UV(-112, -HW - 46), 'west eave heights AGL\n(roof.profile: NAIP eave relief,\nanchored on the DOF tops)', 'obs', fs=3.8)
    # the app's roof
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
    for V, nm, hid in ((V3, 'Boarding Area A', 'ba_a.height_roof'), (V4, 'Boarding Area G', 'ba_g.height_roof')):
        if bg: V.background()
        V.grid(50)
        for r in D.outer_rings(nm, 'boardingAreas'):
            V.poly(r, 'obs', fc='#e7eef6' if not bg else 'none', lw=0.7, z=2)
        V.scalebar()
    V3.mark(DOF_POD[0], 'pub', marker='^', ms=4.5)
    V3.leader(DOF_POD[0], 14, 12, 'FAA DOF 06-035352: 85 ft = 25.91 m AGL\n(1A) top of pod 1 [pub]', 'pub', fs=3.8)
    V3.leader((-1240, 700), 16, -4, 'main roof 17.9 m (16.9-18.8) [obs]\nNAIP oblique-band method, k 0.42;\n'
              'two-epoch control 17.8 m [obs]\nroof width 37.85 m [obs]; outline\n38.7-38.8 m (incl. facade band) [obs]', 'obs', fs=3.8)
    V3.leader((-1300, 780), -2, 16, '3 raised D-shaped pods 70 / 55 / 55 m long\n[obs, by eye]; pod 1 +4.9-5.2 m above\nthe main roof [obs]; pod positions not recorded', 'obs', fs=3.8, ha='right')
    V4.leader((-1400, 100), -4, -22, 'main roof 17.0 m (13-20) [obs, low]\nroof width 38.4 m between parapets [obs]\n(the earlier ~33.5 m is refuted)', 'obs', fs=3.8)
    V4.leader((-1520, 30), -6, 22, '3 raised lens pods 60 / 55 / 62 m [obs, by eye]\nno DOF entry: pod heights unknown [unk]\nSFOM outline 3-6 m NNE of the NAIP roof [obs, unresolved]', 'obs', fs=3.8, ha='right')
    # ---------------- key table
    rows = [('Roof top over the column pairs (humps)', '40.08 m (131/132 ft)', 'pub', 'FAA DOF 06-035315/16, 1A'),
            ('Notches (wings meet centre section)', '35.7 m', 'obs', 'NAIP eave relief + photo'),
            ('Centre crown (glazed section top)', '40.1 m +-2', 'obs', 'public-domain photo only'),
            ('Tips', '34.9 m', 'obs', 'NAIP + photo'),
            ('Roof length / width', '252.9 x 65.4 m', 'obs', 'NAIP, relief-corrected; 860 ft pub conflicts'),
            ('Truss lines / spacing', '5 / 12.12 m', 'obs', 'NAIP comb fit; 40 ft grid [pub]'),
            ('Truss depth max / centre span / end cantilever', '29 / 380 / 160 ft', 'pub', 'SEAONC (read in full)'),
            ('Level 3 (departures) floor', f'{L3} m (9.6-14.8)', 'inf', 'DOF top minus 90 / 100 ft'),
            ('"Building height 144 ft"', 'datum unknown', 'pub', 'SOM, Enclos - do not use'),
            ('BA-A / BA-G main roof', '17.9 / 17.0 m', 'obs', 'NAIP relief / shadow'),
            ('Roof 2024-26 upgrade (membrane, ~1,400 kW PV)', 'layout unknown', 'pub', 'NAIP 2024-05-20 predates it')]
    S.table(0, 150, 222, 'ITB key values', rows, fs=4.0, col=(0.46, 0.24))
    S.note('Hall roof outline, truss lines, lenses and tip bands: NAIP 2024 measured and relief-corrected with the frame model fitted to five '
           'FAA DOF high-mast poles (rms 0.21 m); +-1.5 m. Length 252.6-255.1 m depending on the relief model; the published 860 ft (262.1 m) '
           'is NOT reproduced (conflict open: 145 ft visible end cantilever vs 160 ft published).')
    S.note('Column lines are inferred from the only rhythm that satisfies all published spans; the DOF pair 115.5 m (379 ft) apart over the inner '
           'column lines supports it. The SFO Museum pier outlines include the oblique facade band (lean).')
    S.note('The roof seen by NAIP (2024-05-20) predates the 2024-26 envelope upgrade (new membrane, rooftop PV ~1,400 kW): PV layout unknown.')
    if bg and dev:
        draw_dev(V2, dev, ('ITB main hall roof',))
        draw_dev(V3, dev, ('Boarding Area A',), label_min=99)
        draw_dev(V4, dev, ('Boarding Area G',), label_min=99)
        S.note('Overlay: NAIP 2024 under the drawing. Dots = measured offset of the NAIP edge from the drawn edge at its PREDICTED imaged '
               'position (frame model; roof heights from the eave profile / pier heights); green <= 1 m, amber <= 2.5, red > 2.5, hollow = weak. '
               'deviations.json lists every edge.')
    return S.finish('NAIP 2024' if bg else 'none (vector)', fmt=('jpg',) if bg else ('svg', 'png'))


# ------------------------------------------------------------------------------------------------ elevations
def west_elev(V):
    us = np.linspace(-HL, HL, 400)
    V.ax.fill_between([-HL - 25, HL + 25], [-3, -3], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(-HL - 25, 0), (HL + 25, 0)], 'pub', lw=0.8)
    top = [(u, eave(u)) for u in us]
    V.ax.fill_between(us, 0, [eave(u) for u in us], color='#eef3f8', lw=0, zorder=1.5)
    V.line([(u, h) for u, h in top if abs(u) >= 23], 'obs', lw=1.0, z=4)
    V.line([(u, eave(u)) for u in us if abs(u) <= 23], 'unk', lw=0.6, z=4)
    V.line([(u, crown(u)) for u in us if abs(u) <= 27], 'obs', lw=0.9, ls=(0, (5, 2)), z=4)
    for s in (-1, 1):
        tn = 18.75 if s < 0 else 15.75
        uu = np.linspace(s * HL, s * (HL - tn), 20)
        V.ax.fill_between(uu, [eave(u) - 2.5 for u in uu], [eave(u) for u in uu], color='#cfe3f3', lw=0, zorder=3, hatch='||||', edgecolor='#0b57a4')
    V.line([(-HL + 18.75, 0.5), (HL - 15.75, 0.5)], 'unk', lw=0.3)
    V.line([(-HL, L3), (HL, L3)], 'inf', lw=0.5)
    V.level(HL + 2, L3, f'+{L3} level 3 departures floor (9.6-14.8) [inf]', 'inf', len_mm=6, fs=4.2, u_line=HL)
    for cu in COL_U:
        for s in (-1, 1):
            V.line([(s * cu, L3), (s * cu, eave(s * cu) - depth(s * cu))], 'inf', lw=0.4)
    for oas, (p, ft) in DOF_ROOF.items():
        u = float(np.dot(np.asarray(p) - F['c'], F['ax']))
        V.mark((u, ft * FT), 'pub', marker='v', ms=4)
        V.text((u, ft * FT + 3.0), f'DOF {oas}\n{ft} ft = {ft * FT:.2f} m [pub]', 'pub', fs=3.9)
    V.level(HL + 2, 144 * FT, '+43.89 "building height 144 ft" [pub SOM / Enclos] - datum not stated, conflict', 'pub', len_mm=6, fs=4.0, u_line=HL - 10)
    V.level(HL + 2, H_TIP, f'+{H_TIP} tip [obs]', 'obs', len_mm=6, fs=4.2, u_line=HL)
    V.level(-HL - 2, H_PEAK, '+40.08 humps over the column pairs [pub DOF]', 'pub', side='left', len_mm=6, fs=4.2, u_line=-67)
    V.level(-HL - 2, 35.7, '+35.7 notches [obs]', 'obs', side='left', len_mm=6, fs=4.2, u_line=-27)
    V.level(-HL - 2, CROWN + 1.6, f'+{CROWN} centre crown (photo, +-2) [obs]', 'obs', side='left', len_mm=6, fs=4.2, u_line=0)
    V.dim((-HL, 0), (HL, 0), -8, f'{F["L"]:.2f} m eave tip to tip (252.6-255.1) [obs]', 'obs', fs=4.6)
    V.dim((-131.06, 0), (131.06, 0), -16, '860 ft = 262.13 m [pub] - conflict', 'pub', fs=4.6)
    for a, b in zip([-430, -410, -270, -190, -90, 90, 190, 270, 410], [-410, -270, -190, -90, 90, 190, 270, 410, 430]):
        V.dim((a * FT, 46), (b * FT, 46), 4, f'{b - a}', 'inf', fs=3.8)
    V.text((0, 52.5), 'published / inferred structural rhythm, ft [inf]: 20 | 140 | 80 | 100 | 180 | 100 | 80 | 140 | 20', 'inf', fs=4.2)
    V.text((0, 18), 'WEST (landside) GLASS WALL: full-height, three layers of ceramic frit [pub]; mullion grid not dimensioned in any source [unk]', 'pub', fs=4.2)
    V.text((-HL + 9, 25), 'glazed\ntip band\n18.75 [obs]', 'obs', fs=3.6)
    V.text((HL - 8, 25), 'glazed\ntip band\n15.75 [obs]', 'obs', fs=3.6)


def north_elev(V):
    vs = np.linspace(-HW, HW, 50)
    V.ax.fill_between([-HW - 18, HW + 18], [-2, -2], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(-HW - 18, 0), (HW + 18, 0)], 'pub', lw=0.8)
    # plot coordinate = -v (viewer looks SSE: right hand = WSW)
    V.poly([(-HW, H_TIP - 2.5), (HW, H_TIP - 2.5), (HW, H_TIP), (-HW, H_TIP)], 'obs', fc='#cfe3f3', z=3, hatch='||||')
    V.line([(-HW, H_PEAK), (HW, H_PEAK)], 'pub', lw=0.5, ls=(0, (6, 3)))
    V.text((0, H_PEAK + 1.6), 'silhouette of the humps behind (40.08 m [pub DOF]); cross camber unknown [unk]', 'pub', fs=4.0)
    V.line([(-HW, CROWN), (HW, CROWN)], 'obs', lw=0.4, ls=(0, (2, 3)))
    hw = 210 * FT / 2
    V.poly([(-hw, L3), (hw, L3), (hw, H_TIP - 2.5), (-hw, H_TIP - 2.5)], 'unk', fc='#f4f8fb', z=2)
    V.text((0, (L3 + H_TIP) / 2), 'END CURTAIN WALL: custom unitized, spanning over 60 ft [pub Enclos]\nunder the roof, set back ~24 m behind the tip [inf: 705-ft hall vs 860-ft roof];\nits outline and mullions are not published [unk]', 'unk', fs=4.0)
    V.line([(-HW, L3), (HW, L3)], 'inf', lw=0.5)
    V.level(HW + 2, L3, f'+{L3} level 3 floor (9.6-14.8) [inf]', 'inf', len_mm=5, fs=4.2, u_line=HW)
    V.level(HW + 2, H_TIP, f'+{H_TIP} roof tip fascia [obs]', 'obs', len_mm=5, fs=4.2, u_line=HW)
    V.level(HW + 2, H_TIP - 2.5, 'glazed tip band (depth of fascia unknown) [unk]', 'unk', len_mm=5, fs=4.0, u_line=HW)
    V.level(-HW - 2, H_PEAK, '+40.08 humps [pub DOF]', 'pub', side='left', len_mm=5, fs=4.2, u_line=-HW)
    V.dim((-HW, 0), (HW, 0), -7, f'{F["W"]:.2f} m eave to eave [obs]', 'obs', fs=4.6)
    V.dim((-hw, L3), (hw, L3), -5, '210 ft = 64.0 m hall width [pub SEAONC]', 'pub', fs=4.2)
    V.text((-HW + 2, 4), 'E (airside)', 'unk', fs=4.0, color='#555555', style='normal')
    V.text((HW - 2, 4), 'W (landside)', 'unk', fs=4.0, color='#555555', style='normal')
    V.text((0, 4), 'levels 1-2 (services, arrivals) and the airside building east of the hall: not dimensioned in any source [unk]', 'unk', fs=3.8)


def sheet_elev():
    S = Sheet('BI-02', 'International Terminal main hall: west (landside) elevation and north end elevation', 'A1',
              subtitle='Spec: tools/buildings/spec_itb.json (roof.profile, level3.floor, facade.*)')
    V1 = S.view(0, 330, S.vw, 240, 400, (0, 23), title='1  WEST (LANDSIDE) ELEVATION, looking ENE (u: + towards Boarding Area A)', kind='elev', frame=False)
    west_elev(V1); V1.scalebar(y_mm=6)
    V2 = S.view(0, 6, 420, 280, 250, (0, 22), title='2  NORTH END ELEVATION, looking SSE', kind='elev', frame=False)
    north_elev(V2); V2.scalebar(y_mm=6)
    rows = [('Eave profile |u| 23-123 m', '35.8 -> 40.08 -> 34.8 m', 'obs', 'NAIP: west eave vs the straight facade-base line, 0.955 k h; even-polynomial fit, rms 0.20 m'),
            ('Second method (photo)', 'drops 4.91 / 4.62 m', 'obs', 'public-domain frontal photo; NAIP drops 3.83 / 5.68 m'),
            ('Humps', '40.08 m', 'pub', 'DOF 131/132 ft; may be the skylight ridges, then the eave is 1-2 m lower [unverified]'),
            ('Roof "60 to 90 ft above the floor"', '-> L3 9.6-12.7 m', 'pub', 'Smith-Emery / MSC; surface not stated'),
            ('Great hall interior', '705 x 210 x up to 83 ft', 'pub', 'SEAONC; interior, not the roof (the app uses it as the roof)'),
            ('Stories', '5', 'pub', 'L1 services, L2 arrivals, L3 departures, L4-5 offices / lounges'),
            ('Ground at the ITB', '8 ft AMSL', 'inf', 'DOF AMSL - AGL')]
    S.table(430, 290, 305, 'Heights and their sources', rows, fs=4.1, col=(0.36, 0.22))
    S.note('Eave heights: spec roof.profile full_curve (|u| 23-123 m), extended linearly to the 34.9 m tip; the profile is symmetric by fit '
           '(north and south halves pooled). The centre-section silhouette (dashed) rests on one photo.')
    S.note('Below the eave the west wall is drawn as one glass field: no mullion module, fascia depth or canopy line is published.')
    S.note('The north end elevation shows what is known; the lower building masses and the end wall outline need SFO record drawings.')
    return S.finish()


def sheet_section():
    S = Sheet('BI-03', 'International Terminal main hall: long section on the centre truss line and cross section at the inner column line', 'A1',
              subtitle='Spec: tools/buildings/spec_itb.json (roof.*, level3.floor, hall.*); structure in part inferred')
    V1 = S.view(0, 330, S.vw, 240, 400, (0, 21), title='1  LONG SECTION along the roof axis (v = 0, centre truss line), looking ENE', kind='elev', frame=False)
    us = np.linspace(-HL, HL, 500)
    V1.ax.fill_between([-HL - 25, HL + 25], [-4, -4], [0, 0], color='#dddddd', lw=0, zorder=1)
    V1.line([(-HL - 25, 0), (HL + 25, 0)], 'pub', lw=0.8)
    V1.line([(u, crown(u)) for u in us], 'obs', lw=1.1, z=4)
    V1.line([(u, crown(u) - depth(u)) for u in us if abs(u) >= 27.4], 'inf', lw=0.8, z=4)
    for s in (-1, 1):
        uu = np.linspace(s * 27.4, s * HL, 60)
        V1.ax.fill_between(uu, [crown(u) - depth(u) for u in uu], [crown(u) for u in uu], color='#f6e3cf', lw=0, zorder=2)
        for cu in COL_U:
            V1.poly([(s * cu - 0.6, L3), (s * cu + 0.6, L3), (s * cu + 0.6, crown(s * cu) - depth(s * cu)), (s * cu - 0.6, crown(s * cu) - depth(s * cu))], 'inf', fc='#b35900', z=4)
    V1.line([(u, 34.0 + 1.2 * math.cos(math.pi * u / 54.8)) for u in np.linspace(-27.4, 27.4, 40)], 'unk', lw=0.6)
    V1.text((0, 30.5), 'central section 180 ft [pub, snippet only]:\nglazed lens skylight / bowstring - form unknown [unk]', 'unk', fs=3.9)
    hl = 705 * FT / 2
    V1.poly([(-hl, L3 - 0.8), (hl, L3 - 0.8), (hl, L3), (-hl, L3)], 'inf', fc='#999999', z=3)
    V1.level(HL + 2, L3, f'+{L3} level 3 departures floor (9.6-14.8) [inf]', 'inf', len_mm=6, fs=4.2, u_line=hl)
    V1.level(HL + 2, L3 + 83 * FT, f'+{L3 + 83 * FT:.1f} great hall "up to 83 ft" above L3 [pub height, inf datum]', 'inf', len_mm=6, fs=4.2, u_line=hl)
    V1.dim((-hl, L3 - 1), (hl, L3 - 1), -10, '705 ft = 214.9 m great hall [pub SEAONC]; ticket lobby 700 ft [pub]', 'pub', fs=4.4)
    V1.dim((-57.9, 4), (57.9, 4), 0, '380 ft centre span between the inner column lines [pub]; DOF pair 115.5 m apart [obs]', 'pub', fs=4.2, ext=False)
    V1.dim((82.3, 4), (82.3 + 160 * FT, 4), 0, '160 ft end cantilever [pub]', 'pub', fs=4.0, ext=False)
    V1.dim((82.3, 7), (HL, 7), 0, f'{HL - 82.3:.1f} m visible [obs/inf]', 'obs', fs=4.0, ext=False)
    for cu in COL_U:
        V1.dim((cu, crown(cu) - depth(cu)), (cu, crown(cu)), 3, '29 ft max [pub]' if cu < 60 else '', 'pub', fs=3.8)
    V1.leader((70, crown(70) - 4.4), 30, -14, 'double-cantilever "football" trusses (three chords), 5 sets [pub]; depth up to 29 ft over the\n'
              'supports [pub]; taper to the tips and the centre section drawn linearly [inf]; trusses "up to 320 ft long" [snippet]', 'inf', fs=3.9)
    V1.leader((57.9, L3 + 8), -20, -8, 'columns rising from the level-3 floor\n(4 per truss line, 20 in all) [pub count; positions inf]', 'inf', fs=3.9, ha='right')
    V1.text((0, -2.5), 'base isolation: 267 friction-pendulum isolators [pub]; foundations not dimensioned [unk]', 'pub', fs=3.9)
    V1.level(-HL - 2, H_PEAK, '+40.08 [pub DOF]', 'pub', side='left', len_mm=6, fs=4.2, u_line=-67)
    V1.level(-HL - 2, H_TIP, f'+{H_TIP} tip [obs]', 'obs', side='left', len_mm=6, fs=4.2, u_line=-HL)
    V1.scalebar(y_mm=6)
    # cross section at u = +57.9 (looking NNW: right hand = ENE = +v)
    V2 = S.view(0, 6, 420, 280, 250, (0, 22), title='2  CROSS SECTION at the inner column line u = +57.9 m, looking NNW', kind='elev', frame=False)
    h0 = eave(57.9); d0 = depth(57.9)
    V2.ax.fill_between([-HW - 18, HW + 18], [-3, -3], [0, 0], color='#dddddd', lw=0, zorder=1)
    V2.line([(-HW - 18, 0), (HW + 18, 0)], 'pub', lw=0.8)
    V2.poly([(-HW, h0 - 1.0), (HW, h0 - 1.0), (HW, h0), (-HW, h0)], 'obs', fc='#999999', z=3)
    V2.text((0, h0 + 1.8), f'roof top {h0:.1f} m at u 57.9 (eave profile [obs]); cross camber unknown - drawn flat [unk]', 'obs', fs=4.0)
    for v in LINES_V:
        V2.poly([(v - 1.2, h0 - d0), (v + 1.2, h0 - d0), (v + 1.2, h0 - 1), (v - 1.2, h0 - 1)], 'inf', fc='#f6e3cf', z=3)
        V2.poly([(v - 0.6, L3), (v + 0.6, L3), (v + 0.6, h0 - d0), (v - 0.6, h0 - d0)], 'inf', fc='#b35900', z=4)
    V2.poly([(-HW + 0.5, L3 - 0.8), (HW - 0.5, L3 - 0.8), (HW - 0.5, L3), (-HW + 0.5, L3)], 'inf', fc='#999999', z=3)
    V2.line([(-HW, 0), (-HW, h0 - 1.0)], 'pub', lw=1.0, color='#46576a')
    V2.text((-HW - 1.5, 20), 'west glass wall\n(3 layers of frit) [pub]\nposition = eave line [inf]', 'pub', fs=3.9, ha='right')
    V2.line([(HW - 4, L3), (HW - 4, h0 - d0)], 'unk', lw=0.6)
    V2.text((HW + 1.5, 24), 'east: cherry-wood high wall\n(interior) [pub]; position\nunknown [unk]', 'unk', fs=3.9, ha='left')
    for a, b in zip(LINES_V[:-1], LINES_V[1:]):
        V2.dim((a, L3 - 1), (b, L3 - 1), -4, f'{SP:.2f}', 'obs', fs=4.0)
    V2.dim((-HW, 0), (HW, 0), -8, f'{F["W"]:.2f} m eave to eave [obs]; outer truss line to eave ~8.4 m [obs]', 'obs', fs=4.4)
    V2.dim((LINES_V[4] + 1.2, h0 - d0), (LINES_V[4] + 1.2, h0), 4, '29 ft [pub]', 'pub', fs=4.0)
    V2.level(HW + 2, L3, f'+{L3} level 3 (9.6-14.8) [inf]', 'inf', len_mm=5, fs=4.2, u_line=HW)
    V2.level(HW + 2, h0, f'+{h0:.1f} roof [obs]', 'obs', len_mm=5, fs=4.2, u_line=HW)
    V2.scalebar(y_mm=6)
    rows = [('Five balanced double-cantilever truss sets, linked by bowstring trusses', 'roof form', 'pub', 'SEAONC, MSC 2000, SOM, Smith-Emery'),
            ('Truss depth (max, over supports)', '29 ft = 8.84 m', 'pub', 'SEAONC'),
            ('Centre span / end cantilever / overall', '380 / 160 / 860 ft', 'pub', 'SEAONC; 860 ft conflicts with NAIP 829 ft'),
            ('Truss length / centre section', '320 / 180 ft', 'pub', 'MSC 2000 snippet only (AISC PDF unreadable)'),
            ('Columns', '20 from level 3', 'pub', 'SEAONC; positions inferred (5 lines x 4)'),
            ('Steel', 'Herrick; ~35 pieces by barge', 'pub', 'MSC 2000, SEAONC'),
            ('Isolators', '267 friction pendulum', 'pub', 'Enclos, SEAONC')]
    S.table(430, 290, 305, 'Structure (published) and what is inferred', rows, fs=4.1, col=(0.40, 0.22))
    S.note('The section is a measured roof top (NAIP eave profile anchored on the FAA DOF roof tops) over an INFERRED structure: '
           'column positions from the published spans, truss depth published as a maximum only.')
    S.note('Level 3 = DOF roof top minus "90 ft" / "100 ft" above the floor (two press figures), midpoint 11.5 m - no drawing or survey found.')
    return S.finish()
