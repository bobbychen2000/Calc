"""Sheets of the SFO landside / support buildings, drawn from tools/buildings/spec_landside.json (verified 2026-11-04,
docs/research/buildings_landside.md section 14) and tools/buildings/landside_naip_measurements.json:
  BL-01  key plan 1:5000 (A1): all landside buildings, FAA DOF points, heights
  BL-02  roof plans 1:2000 (A1): central garage, Garages A / G + Grand Hyatt, LTP garages, United MOC, RCC, CAC, Superbay
         + NAIP overlay with deviation dots
  BL-03  principal elevations 1:1000 (A1): every building's long face as a massing elevation with levels and heights
Footprints are the SFO Museum polygons (data/sfo_airport.json); the United MOC has none (imaged NAIP roof corners, relief
NOT removed, are drawn instead).
"""
import numpy as np

import draw_data as D
from draw_lib import Sheet, FT, hdg_vec, unit
from draw_tower import draw_dev

LV = D.LV
LB = D.LANDM['buildings']
MOC = D.LANDM['moc']
NAMES = {'central_garage': 'Central Parking Garage', 'garage_a': 'Garage A', 'garage_g': 'Garage G', 'ltp_garage_1': 'Long-Term Parking Garage 1',
         'ltp_garage_2': 'Long-Term Parking Garage 2', 'rental_car_center': 'Rental Car Center', 'grand_hyatt': 'Grand Hyatt Hotel',
         'cac': 'Consolidated Administration Campus', 'superbay': 'Super Bay Hangar Building'}
SUMMARY = {
    'central_garage': ('Central Parking Garage (Bldg 195)', '5 levels [pub]; 81 ft = 24.69 m [pub, definition unknown];\nroof light poles 101 / 109 ft [pub DOF]; void 58.9 m [obs] (200 ft [pub])', 'pub'),
    'garage_a': ('International Garage A (Bldg 95)', '9 levels [pub]; AirTrain at L7 [pub]; roof deck NOT measured;\nhelix drum top 39.6 m (38.0-41.5) [obs, low]', 'obs'),
    'garage_g': ('International Garage G (Bldg 495)', '9 levels [pub]; AirTrain at L7 [pub]; roof deck NOT measured;\nhelix drum top 37.6 m (36.0-40.0) [obs, low]', 'obs'),
    'grand_hyatt': ('Grand Hyatt at SFO (Bldg 55)', '12 stories [pub]; lobby + AirTrain at the 4th floor [pub];\nheight ~44 m (40-48) [inf, low] - NOT published', 'inf'),
    'cac': ('Consolidated Administration Campus', '4 stories x 15 ft [pub] -> 60 ft roof, ~64 ft parapet [inf];\nNAIP shadow 17.4-19.2 m [obs]', 'inf'),
    'ltp_garage_1': ('Long-Term Parking Garage 1 (Bldg 795)', 'north-end parapet 16.5 m (15.9-16.8) [obs, shadow];\nDOF 86 / 91 ft = towers [pub]; >= 5 levels [inf]', 'obs'),
    'ltp_garage_2': ('Long-Term Parking Garage 2 (Bldg 794)', '6 levels, 12 ft floor-to-floor [pub] -> deck 60 ft [inf];\nroof PV canopies [pub], height unknown', 'inf'),
    'rental_car_center': ('Rental Car Center (Bldg 780)', '5 levels [pub]; "66-foot-tall" = 20.12 m [pub, disputed as roof];\nroof outline 54 / 59 ft [pub DOF]; station tower 60 ft [pub]', 'pub'),
    'superbay': ('Superbay hangar (Bldg 1060)', 'DOF 135 ft = 41.15 m, red light [pub]; "140-ft roof" [pub];\ninterior 120 ft [pub]; cantilever "over 230 ft from the centre" [pub]', 'pub'),
}


def dofs(k):
    return LB[k]['dof'] if k in LB else []


def draw_bldg(V, k, bg, fs=3.9, label=True, dofs_on=True):
    nm = NAMES[k]
    for poly in D.sfom(nm, 'structures'):
        V.poly(poly[0], 'obs', fc='#e7eef6' if not bg else 'none', lw=0.7, z=2)
        for h in poly[1:]:
            V.poly(h, 'obs', fc='white' if not bg else 'none', lw=0.6, z=2.1)
    if dofs_on:
        for d in dofs(k):
            tg = 'pub'
            V.mark(d['world'], tg, marker='^', ms=4)


def moc_draw(V, bg):
    for key, v in MOC.items():
        V.poly(v['corners_imaged'], 'obs', fc='#eef3f8' if not bg else 'none', lw=0.7, z=2, ls=(0, (6, 2)))
        for d in v.get('dof', []):
            V.mark(d['world'], 'pub', marker='^', ms=4)


def label_dofs(V, k, dx=10, dy=4, fs=3.6, skip=()):
    for i, d in enumerate(dofs(k)):
        if d['oas'] in skip: continue
        acc = d['acc']
        V.leader(d['world'], dx, dy - 6 * i, f"DOF {d['oas']} {d['type']} {d['agl_ft']} ft = {d['agl_ft'] * FT:.1f} m ({acc})", 'pub', fs=fs)


# ------------------------------------------------------------------------------------------------ BL-01
def sheet_key():
    S = Sheet('BL-01', 'Landside and support buildings: key plan with heights and FAA DOF points', 'A1',
              subtitle='Spec: tools/buildings/spec_landside.json + landside_naip_measurements.json; note docs/research/buildings_landside.md (14)')
    V = S.view(0, 0, S.vw, S.vh, 5000, (-1190, -690), kind='plan', title='1  KEY PLAN')
    V.grid(250)
    for r in D.complex_rings(): V.ctx(r, fc='#f2f2f2')
    for poly in D.sfom('AirTrain Rail', 'structures'):
        V.ctx_holes(poly, fc='#d9d9d9', lw=0.2)
    for f in D.AIR['structures']:
        if f['kind'] == 'airtrain':
            for poly in f['polys']: V.ctx(poly[0], fc='#c8c8c8', lw=0.2)
    for k in NAMES:
        draw_bldg(V, k, False)
    moc_draw(V, False)
    pos = {'central_garage': (14, -10), 'garage_a': (-58, -8), 'garage_g': (-60, 12), 'grand_hyatt': (-62, 4), 'cac': (-60, 8),
           'ltp_garage_1': (22, -8), 'ltp_garage_2': (-58, 14), 'rental_car_center': (-60, -10), 'superbay': (16, 10)}
    for k, (dx, dy) in pos.items():
        mr = LB[k]['footprint']['min_rect']['centre']
        t, s, tg = SUMMARY[k]
        V.leader(mr, dx, dy, t + '\n' + s, tg, fs=4.2)
    V.leader((-1603, -1925), 26, -12, 'United Airlines MOC (no SFO Museum outline): large hangar block,\nimaged roof 241 x 85 m (relief not removed) [obs, low];\n'
             'DOF 132 / 117 / 116 ft [pub]; barrel-vault hangars south of it [obs]', 'obs', fs=4.2)
    V.text((-1245, 365), 'ITB', 'unk', fs=5, color='#777777', style='normal', bg=False)
    V.text((-850, 450), 'terminal complex (context)', 'unk', fs=4.6, color='#777777', style='normal', bg=False)
    V.leader((-1700, -1400), -30, 20, 'AirTrain guideway (SFO Museum polygon, context): single 4.8-5.1 m,\ntwin 9.5-11.5 m [obs]; extension "50 ft above a public\nroadway" [pub]; "35 to 40 ft at its highest point" [pub, conflict]', 'obs', fs=4.0)
    V.scalebar()
    S.note('Heights are metres above local grade. FAA DOF points (triangles) are surveyed tops (1A: +-20 ft horizontal, +-3 ft vertical) '
           'of the highest element there - often a stair / elevator tower, pole or helix, not the roof deck.')
    S.note('NAIP 2024 is not one moment: noon-like over the terminals and the North Field, a morning frame over the Superbay; relief lean '
           'differs per frame (0.30-0.33 m/m east in the North Field, north-west at the Superbay).')
    S.note('SFO Museum data issue: the newer AirTrain station polygons "International Terminal (A)" / "(G)" (ids 1763588569 / 1763588567) '
           'have A and G swapped; the older 1729791961 / 1729791965 are right.')
    return S.finish()


# ------------------------------------------------------------------------------------------------ BL-02
def sheet_roofs(variant='vector', dev=None):
    bg = variant != 'vector'
    S = Sheet('BL-02', 'Landside and support buildings: roof plans', 'A1', variant=variant,
              subtitle='Spec: tools/buildings/spec_landside.json (footprints obs = SFO Museum; MOC = NAIP imaged roof)')
    panels = []

    def panel(x, y, w, h, scale, c, title):
        V = S.view(x, y, w, h, scale, c, kind='plan', title=title)
        if bg: V.background()
        V.grid(50)
        panels.append(V)
        return V

    def dims(V, k, off=6):
        mr = LB[k]['footprint']['min_rect']
        c = np.array(mr['centre']); a = hdg_vec(mr['long_side_heading_deg']); b = np.array([a[1], -a[0]])
        L, W = mr['length_m'], mr['width_m']
        p = [c - a * L / 2 - b * W / 2, c + a * L / 2 - b * W / 2, c + a * L / 2 + b * W / 2]
        V.dim(p[0], p[1], off, f'{L:.1f} m [obs, min. rectangle]', 'obs', fs=3.8)
        V.dim(p[1], p[2], off, f'{W:.1f} m', 'obs', fs=3.8)
        V.poly([p[0], p[1], p[2], c - a * L / 2 + b * W / 2], 'obs', lw=0.25, ls=(0, (1, 2)), z=1.8)

    # P1 central garage
    V = panel(0, 368, 178, 202, 2000, (-938, 272), 'A  CENTRAL PARKING GARAGE')
    draw_bldg(V, 'central_garage', bg); dims(V, 'central_garage', 5)
    V.leader((-930.8, 275.5), 14, 24, 'central void: 58.9 m [obs] (200 ft [pub])\nring of up / down ramps [pub]', 'obs', fs=3.8)
    label_dofs(V, 'central_garage', 20, -14)
    V.leader((-1000, 400), -2, 10, '5 levels; 81 ft [pub]; AirTrain T1 / T2 / T3\nstations on Level 5 [pub]; RADP "Central Hub"\nwould replace it (planned) [pub]', 'pub', fs=3.8, ha='left')
    # P2 Garages A / G + Hyatt
    V = panel(184, 300, 236, 270, 2000, (-1462, 470), 'B  INTERNATIONAL GARAGES A / G AND GRAND HYATT')
    for k in ('garage_a', 'garage_g', 'grand_hyatt'):
        draw_bldg(V, k, bg); dims(V, k, 5)
    for f in D.AIR['structures']:
        if f['kind'] == 'airtrain' and f['id'] in (1729791949, 1729791947, 1729791967, 1729791961, 1729791965):
            for poly in f['polys']: V.ctx(poly[0], fc='#d0d0d0' if not bg else 'none')
    V.leader((-1500, 530), -8, 26, 'Garage A: 9 levels [pub]; AirTrain station at L7 [pub];\nhelix drum (west end) top 39.6 m [obs, low]; deck not measured', 'obs', fs=3.8)
    V.leader((-1500, 300), -8, -30, 'Garage G: 9 levels [pub]; BART + AirTrain station;\nhelix drum top 37.6 m [obs, low]; deck not measured', 'obs', fs=3.8)
    V.leader((-1640, 650), 22, -22, 'Grand Hyatt: crescent slab, concave glass face east [obs];\n12 stories [pub], ~44 m [inf]; outline includes the podium -\nnot a ground trace of the slab [obs]', 'inf', fs=3.8)
    V.text((-1395, 432), 'AirTrain stations\n(context, grey)', 'unk', fs=3.6, color='#777777', style='normal')
    # P3 LTP garages
    V = panel(426, 360, 150, 210, 2000, (-2266, -1921), 'C  LONG-TERM PARKING GARAGES 1 AND 2')
    for k in ('ltp_garage_1', 'ltp_garage_2'):
        draw_bldg(V, k, bg); dims(V, k, 5)
    label_dofs(V, 'ltp_garage_1', 14, 10)
    V.leader((-2220, -1981), 16, -24, 'LTP 1: north-end parapet 16.5 m [obs]', 'obs', fs=3.8)
    V.leader((-2322, -1883), -6, 30, 'LTP 2: 6 levels x 12 ft [pub];\nPV canopies on the roof [pub];\nlevel-5 link to LTP 1 [pub]', 'pub', fs=3.8)
    # P4 MOC
    V = panel(582, 300, 157, 270, 2000, (-1610, -1845), 'D  UNITED MAINTENANCE CENTER (MOC)')
    moc_draw(V, bg)
    for d in MOC['moc_large_hangar']['dof']:
        V.leader(d['world'], 10, 6, f"DOF {d['oas']} {d['agl_ft']} ft = {d['agl_m']} m [pub]", 'pub', fs=3.6)
    V.leader((-1603, -1925), -8, 34, 'large hangar block: IMAGED roof 241 x 85 m\n(relief NOT removed) [obs, low]; stepped roof,\nsteps at z ~-1945 / -1885 [obs]', 'obs', fs=3.8, ha='right')
    V.leader((-1590, -1715), 10, -20, 'two barrel-vault hangars, imaged\n156 x 90 m [obs]; no DOF entry [unk]', 'obs', fs=3.8)
    # P5 RCC
    V = panel(0, 120, 150, 170, 2000, (-2184, -1061), 'E  RENTAL CAR CENTER')
    draw_bldg(V, 'rental_car_center', bg); dims(V, 'rental_car_center', 5)
    for i, d in enumerate(dofs('rental_car_center')):
        V.leader(d['world'], -6 if d['world'][0] < -2200 else 8, 8 - 7 * i, f"{d['oas']} {d['type']} {d['agl_ft']} ft [pub]", 'pub', fs=3.4)
    # P6 CAC
    V = panel(0, 8, 150, 100, 2000, (-2014, -458), 'F  CONSOLIDATED ADMINISTRATION CAMPUS')
    draw_bldg(V, 'cac', bg); dims(V, 'cac', 5)
    V.leader((-2017, -466), 16, -24, 'bent bar round a court [pub]; 4 stories x 15 ft [pub];\noutline 4,752 m2 vs 3,135 m2 / floor published [obs]', 'pub', fs=3.8)
    # P7 Superbay
    V = panel(158, 8, 166, 282, 2000, (-94, -862), 'G  SUPERBAY HANGAR')
    draw_bldg(V, 'superbay', bg); dims(V, 'superbay', 5)
    mr = LB['superbay']['footprint']['min_rect']; c = np.array(mr['centre'])
    sv = hdg_vec(117.83); tv = hdg_vec(27.83)
    sp = [c + sv * -14 + tv * -69, c + sv * 18 + tv * -69, c + sv * 18 + tv * 69, c + sv * -14 + tv * 69]
    V.poly(sp, 'obs', fc='#d6e2ee' if not bg else 'none', lw=0.6, z=3)
    for side in (-1, 1):
        a0, a1 = (-14, -80.5) if side < 0 else (18, 84.5)
        for i in range(9):
            t = -69 + 17.25 * i
            V.line([c + sv * a0 + tv * t, c + sv * a1 + tv * t], 'obs', lw=0.35, z=3)
    V.leader(c + tv * -40, -10, 56, 'central spine 32 m (a -14..+18) along the 27.8 deg grid [obs];\nfolded cantilever roofs WNW / ESE, ~66.5 m beyond it, 8 bays\n'
             'of 17.3 m per side [obs] (Deep3DS: "50 ft structural bays" [pub],\nconflict); roof 165 m overall [obs]', 'obs', fs=3.8)
    label_dofs(V, 'superbay', 14, -26)
    V.leader(c + sv * 60, 4, -46, 'NAIP roof imaged (-7.0, -7.5) m NW of the outline\n(frame leans NW here) [obs]', 'obs', fs=3.8)
    for V in panels: V.scalebar()
    rows = [(SUMMARY[k][0], {'central_garage': '24.69 m (81 ft)', 'garage_a': 'drum 39.6 m', 'garage_g': 'drum 37.6 m', 'grand_hyatt': '~44 m (40-48)',
                             'cac': '18.3-19.5 m', 'ltp_garage_1': '16.5 m parapet', 'ltp_garage_2': '18.3 m deck', 'rental_car_center': '16.5-18.0 m roof outline',
                             'superbay': '41.15 m'}[k], {'central_garage': 'pub', 'garage_a': 'obs', 'garage_g': 'obs', 'grand_hyatt': 'inf', 'cac': 'inf',
                                                          'ltp_garage_1': 'obs', 'ltp_garage_2': 'inf', 'rental_car_center': 'pub', 'superbay': 'pub'}[k],
             SUMMARY[k][1].replace('\n', ' ')) for k in SUMMARY]
    rows.append(('United MOC large hangar', '35.4-40.2 m', 'pub', 'DOF 116 / 117 / 132 ft at three parts; section heights between them unknown'))
    S.table(332, 292, 404, 'Landside heights (above grade)', rows, fs=3.8, col=(0.25, 0.17))
    S.note('Dimensions = minimum-area rectangle of the SFO Museum outline (a measure of the outline, not a surveyed building size).')
    S.note('Only the Superbay roof structure is drawn: other roof features (stair / elevator towers, helix drums, canopies, PV) are not '
           'measured as plan geometry.')
    if bg and dev:
        for V in panels:
            draw_dev(V, dev, tuple(NAMES.values()), label_min=99)
        S.note('Overlay: NAIP 2024 under the drawing. Dots: NAIP edge offset from the outline at its predicted imaged position '
               '(roofs with a measured lean and height; facade bases on the faces towards the camera nadir). The Superbay roof offsets use '
               'a shift fitted to this image (circular). deviations.json lists every edge.')
    return S.finish('NAIP 2024' if bg else 'none (vector)', fmt=('jpg',) if bg else ('svg', 'png'))


# ------------------------------------------------------------------------------------------------ BL-03
def massing(V, x0, W, title, items):
    """items: list of (kind, args...) drawn on a ground line from x0 over width W."""
    V.ax.fill_between([x0 - 6, x0 + W + 6], [-2.0, -2.0], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(x0 - 6, 0), (x0 + W + 6, 0)], 'pub', lw=0.7)
    for it in items:
        k = it[0]
        if k == 'box':
            _, h, tag, s = it
            V.poly([(x0, 0), (x0 + W, 0), (x0 + W, h), (x0, h)], tag, fc='#f4f7fb', z=2, lw=0.8)
            V.level(x0 + W + 1, h, s, tag, len_mm=3, fs=3.9, u_line=x0 + W)
        elif k == 'band':
            _, lo, hi, col = it
            V.ax.fill_between([x0, x0 + W], [lo, lo], [hi, hi], color=col, lw=0, zorder=1.4, alpha=0.75)
        elif k == 'levels':
            _, hs, tag = it
            for h in hs:
                V.line([(x0, h), (x0 + W, h)], tag, lw=0.35)
        elif k == 'mark':
            _, u, h, tag, s = it
            V.mark((x0 + u, h), tag, marker='v', ms=3.5)
            V.text((x0 + u, h + 1.8), s, tag, fs=3.6)
        elif k == 'mast':
            _, u, h0, h1, tag = it
            V.line([(x0 + u, h0), (x0 + u, h1)], tag, lw=0.6)
        elif k == 'lvl':
            _, h, tag, s = it
            V.level(x0 + W + 1, h, s, tag, len_mm=3, fs=3.9, u_line=x0 + W)
        elif k == 'lvlL':
            _, h, tag, s = it
            V.level(x0 - 1, h, s, tag, side='left', len_mm=3, fs=3.9, u_line=x0)
        elif k == 'text':
            _, u, h, tag, s = it
            V.text((x0 + u, h), s, tag, fs=3.7)
    V.dim((x0, 0), (x0 + W, 0), -4, f'{W:.0f} m long face [obs, outline min. rectangle]', 'obs', fs=3.8)
    V.text((x0 + W / 2, -9), title, 'pub', fs=4.6, weight='bold', bg=False, color='#000000', style='normal')


def sheet_elev():
    S = Sheet('BL-03', 'Landside and support buildings: principal elevations (long faces) with levels and heights', 'A1',
              subtitle='Spec: tools/buildings/spec_landside.json; massing elevations - facade detail is not measured')
    L = lambda k: LB[k]['footprint']['min_rect']['length_m']

    def proj(k, P):
        """u of a DOF point projected on the long side of the outline's minimum rectangle, from its end opposite the
        long-side heading (e.g. the SSW end for heading 27.8 deg)."""
        mr = LB[k]['footprint']['min_rect']; ax = hdg_vec(mr['long_side_heading_deg'])
        return float(np.dot(np.asarray(P, float) - np.asarray(mr['centre'], float), ax)) + mr['length_m'] / 2

    def dof_items(k, h_from, lbl):
        it = []
        for d in LB[k]['dof']:
            if d['type'] == 'TANK' or d['oas'] not in lbl: continue
            u = proj(k, d['world'])
            it += [('mast', u, h_from, d['agl_m'], 'pub'), ('mark', u, d['agl_m'], 'pub', lbl[d['oas']])]
        return it
    rowh = 136
    V1 = S.view(0, 3 * rowh + 8, S.vw, rowh - 6, 1000, (300, 22), kind='elev', frame=False, title='1  CENTRAL PARKING GARAGE and INTERNATIONAL GARAGE A')
    x = 0; W = L('central_garage')
    lv = [24.69 * i / 5 for i in range(1, 5)]
    massing(V1, x, W, 'CENTRAL PARKING GARAGE (Bldg 195)', [('box', 24.69, 'pub', '+24.69  81 ft "five-level, 81-foot-tall" [pub]; what it measures is not stated'),
                                                         ('levels', lv, 'unk')] +
            dof_items('central_garage', 24.69, {'06-034812': '109 ft pole\n[pub DOF]', '06-034813': '101 ft pole\n[pub DOF]',
                                                '06-039216': '130 ft antenna\n[pub DOF 4D, +-76 m]'}) +
            [('text', W / 2, 12, 'unk', '5 levels [pub]; level lines = equal fifths (placeholder) [unk];\nAirTrain T1/T2/T3 stations on Level 5 [pub];\n'
              'DOF points at their projected positions, u from the SSW end [pub]')])
    x = W + 40; W = L('garage_a')
    massing(V1, x, W, 'INTERNATIONAL GARAGE A (Bldg 95)', [('band', 25, 41.5, '#cfe0f2'), ('box', 25.0, 'unk', '+25-41.5 roof deck: deck NOT measured; 25 = the DISPUTED AirTrain-photo reading,\n41.5 = drum-top upper bound [spec garage_a_height range]'),
                                                          ('mark', 12, 39.6, 'obs', 'helix drum top 39.6\n(38.0-41.5) [obs]'),
                                                          ('text', W / 2, 10, 'pub', '9 levels [pub]; AirTrain station from Level 7 [pub];\nclearance 8 ft 2 in [pub]; precast grid + perforated metal [obs]')])
    V2 = S.view(0, 2 * rowh + 8, S.vw, rowh - 6, 1000, (300, 22), kind='elev', frame=False, title='2  GARAGE G, GRAND HYATT, CONSOLIDATED ADMINISTRATION CAMPUS')
    x = 0; W = L('garage_g')
    massing(V2, x, W, 'INTERNATIONAL GARAGE G (Bldg 495)', [('band', 25, 40.0, '#cfe0f2'), ('box', 25.0, 'unk', '+25-40 roof deck: deck NOT measured; 25 = the DISPUTED AirTrain-photo reading,\n40 = drum-top upper bound [spec garage_g_height range]'),
                                                           ('mark', 12, 37.6, 'obs', 'helix drum top 37.6\n(36.0-40.0) [obs]'),
                                                           ('text', W / 2, 10, 'pub', '9 levels [pub]; BART + AirTrain station from Level 7 [pub]')])
    x = W + 40; W = L('grand_hyatt')
    massing(V2, x, W, 'GRAND HYATT AT SFO (Bldg 55)', [('band', 40, 48, '#f3d9bf'), ('box', 44.0, 'inf', '+44 (40-48) [inf, low]: 13.2 floor pitches x 3.2-3.5 m (photo) - NOT published'),
                                                     ('levels', [44.0 * i / 12 for i in range(1, 12)], 'unk'),
                                                     ('text', W / 2, 20, 'pub', '12 stories [pub];\nlobby + AirTrain\nat the 4th floor [pub]')])
    x += W + 50; W = L('cac')
    massing(V2, x, W, 'CONSOLIDATED ADMINISTRATION CAMPUS', [('band', 17.4, 19.2, '#cfe0f2'), ('box', 60 * FT, 'inf', '+18.29 roof = 4 x 15 ft [inf]'),
                                                           ('lvlL', 64 * FT, 'inf', 'parapet ~64 ft = 19.51 [inf]; shadow 17.4-19.2 [obs] +'),
                                                           ('levels', [15 * FT * i for i in (1, 2, 3)], 'pub'),
                                                           ('text', W / 2, 9, 'pub', '4 stories, 15 ft floor-to-floor [pub]')])
    V3 = S.view(0, rowh + 8, S.vw, rowh - 6, 1000, (300, 22), kind='elev', frame=False, title='3  LONG-TERM PARKING GARAGES 1 AND 2, RENTAL CAR CENTER')
    x = 0; W = L('ltp_garage_1')
    massing(V3, x, W, 'LONG-TERM PARKING GARAGE 1 (Bldg 795)', [('box', 16.5, 'obs', '+16.5 north-end parapet (15.9-16.8) [obs, NAIP shadow]')] +
            dof_items('ltp_garage_1', 16.5, {'06-035206': '91 ft [pub DOF]', '06-035207': '86 ft [pub DOF]'}) +
            [('text', W / 2, 8, 'inf', '>= 5 levels [inf: AirTrain + LTP2 links at Level 5];\nDOF tops = towers / helix ~10 m above the parapet [inf];\n'
              'DOF points at their projected positions, u from the NNW end [pub]')])
    x = W + 55; W = L('ltp_garage_2')
    massing(V3, x, W, 'LONG-TERM PARKING GARAGE 2 (Bldg 794)', [('box', 60 * FT, 'inf', '+18.29 deck = 5 x 12 ft [inf]'),
                                                               ('levels', [12 * FT * i for i in range(1, 5)], 'pub'),
                                                               ('text', W / 2, 9, 'pub', '6 levels, 12 ft floor-to-floor [pub] (level 1 at grade assumed [inf]);\nPV canopies above the deck (dotted), height unknown [unk]')])
    V3.line([(x, 60 * FT + 3.5), (x + W, 60 * FT + 3.5)], 'unk', lw=0.6)
    x += W + 70; W = L('rental_car_center')
    massing(V3, x, W, 'RENTAL CAR CENTER (Bldg 780)', [('band', 54 * FT, 59 * FT, '#d9d9d9'), ('box', 54 * FT, 'pub', '+16.46 / 17.98 roof 54 / 59 ft [pub DOF]'),
                                                     ('lvl', 66 * FT, 'pub', '+20.12 "66-foot-tall" [pub]'),
                                                     ('mark', proj('rental_car_center', next(d['world'] for d in LB['rental_car_center']['dof'] if d['type'] == 'TANK')),
                                                      60 * FT, 'pub', 'DOF 06-034240 TANK 60 ft [pub]\n= station stair / elevator\ntower? [inf]'),
                                                     ('text', W / 2, 8, 'pub', '5 levels [pub]; 2,485 ready-return stalls [pub];\n66 ft is 7-12 ft above the DOF-surveyed roof edge (definition disputed);\nTANK at its projected position, u from the SSW end')])
    V4 = S.view(0, 8, S.vw, rowh - 6, 1000, (300, 22), kind='elev', frame=False, title='4  SUPERBAY HANGAR (section across the spine) and UNITED MOC LARGE HANGAR')
    x = 0; W = 165.0
    massing(V4, x, W, 'SUPERBAY HANGAR (Bldg 1060), across the spine (WNW-ESE)', [
        ('text', W / 2, 18, 'pub', 'four 747-size bays, 6 office levels\n+ central workshop [pub]; roof beams cantilever\n"over 230 ft from the centre" [pub]')])
    sp0, sp1 = 80.5 - 14, 80.5 + 18
    V4.poly([(sp0, 0), (sp1, 0), (sp1, 135 * FT), (sp0, 135 * FT)], 'pub', fc='#f4f7fb', z=2)
    for a, b in ((0, sp0), (sp1, W)):
        V4.poly([(a, 0), (b, 0), (b, 120 * FT), (a, 120 * FT)], 'unk', fc='#f9f9f9', z=1.8)
    V4.level(W + 1, 135 * FT, '+41.15 135 ft [pub DOF 1A, red light] at the spine edge', 'pub', len_mm=3, fs=3.9, u_line=sp1)
    V4.level(W + 1, 140 * FT, '+42.67 "140-foot tall roof" [pub, round number]', 'pub', len_mm=3, fs=3.9, u_line=sp1)
    V4.level(W + 1, 120 * FT, '+36.58 interior ~120 ft [pub]; cantilever tip heights unknown [unk]', 'pub', len_mm=3, fs=3.9, u_line=W)
    V4.dim((sp0, 135 * FT), (sp1, 135 * FT), 3, 'spine 32 m [obs]', 'obs', fs=3.8)
    x = 215; W = MOC['moc_large_hangar']['min_rect']['length_m']
    ax = hdg_vec(160.9); c = np.array(MOC['moc_large_hangar']['min_rect']['centre'])
    u = lambda p: float(np.dot(np.asarray(p) - c, ax)) + W / 2
    zN, zS = -1945, -1885
    uN = u((c[0], zN)) ; uS = u((c[0], zS))
    a, b = sorted([uN, uS])
    hs = {d['oas']: d for d in MOC['moc_large_hangar']['dof']}
    blocks = [(0, a, hs['06-035290']), (a, b, hs['06-035289']), (b, W, hs['06-035288'])]
    V4.ax.fill_between([x - 6, x + W + 6], [-2.0, -2.0], [0, 0], color='#dddddd', lw=0, zorder=1)
    V4.line([(x - 6, 0), (x + W + 6, 0)], 'pub', lw=0.7)
    for b0, b1, d in sorted(blocks, key=lambda t: t[0]):
        V4.poly([(x + b0, 0), (x + b1, 0), (x + b1, d['agl_m']), (x + b0, d['agl_m'])], 'pub', fc='#f4f7fb', z=2, ls=(0, (5, 2)))
        uu = u(d['world'])
        V4.mark((x + uu, d['agl_m']), 'pub', marker='v', ms=3.5)
        V4.text((x + uu, d['agl_m'] + 2.0), f"DOF {d['oas']}\n{d['agl_ft']} ft = {d['agl_m']} m", 'pub', fs=3.6)
    V4.dim((x, 0), (x + W, 0), -4, f'{W:.0f} m imaged roof length (relief not removed) [obs, low]', 'obs', fs=3.8)
    V4.text((x + W / 2, -9), 'UNITED MOC LARGE HANGAR BLOCK, long face from the WSW', 'pub', fs=4.6, weight='bold', bg=False, color='#000000', style='normal')
    V4.text((x + W / 2, 12), 'roof steps at z ~-1945 / -1885 [obs]; each part drawn at the DOF height inside it [pub point, extent inf];\nhangar doors, identities and section heights not verified [unk]', 'inf', fs=3.7)
    for V in (V1, V2, V3, V4): V.scalebar(y_mm=3)
    S.note('Massing elevations: width = the long side of the outline\'s minimum rectangle, height = the spec value with its tag; level lines '
           'only where a floor height is published. Facade modules (precast grid, perforated screens, curtain walls) are not dimensioned.')
    S.note('Garages A / G: the roof deck is still unmeasured; the drawn band is the spec range: its 25 m lower end is what remains of the '
           'disputed "25-30 m" AirTrain-photo reading (spec garage_a/g_height: DISPUTED), the upper end the helix drum top. Grand Hyatt: no '
           'published height.')
    S.note('DOF points are drawn at their positions projected on the long side of each outline\'s minimum rectangle (u from the end '
           'named on the elevation); the RCC "TANK" is identified with the station stair / elevator tower only by inference [inf].')
    return S.finish()
