"""Sheets of the SFO landside / support buildings, drawn from tools/buildings/spec_landside.json (verified 2026-11-04,
docs/research/buildings_landside.md section 14) and tools/buildings/landside_naip_measurements.json:
  BL-01  key plan 1:5000 (A1): all landside buildings, FAA DOF points, heights
  BL-02  roof plans 1:2000 (A1): central garage, Garages A / G + Grand Hyatt, LTP garages, United MOC, RCC, CAC, Superbay
         + NAIP overlay with deviation dots
  BL-03  principal elevations 1:1000 (A1): every building's long face as a massing elevation with levels and heights
Footprints are the SFO Museum polygons (data/sfo_airport.json); the United MOC has none (imaged NAIP roof corners, relief
NOT removed, are drawn instead).
"""
import os
import sys

import numpy as np

import draw_data as D
from draw_lib import Sheet, FT, ROOT, hdg_vec, unit
from draw_tower import draw_dev

LV = D.LV
SB_TIP, SB_TIP_RNG = 27.0, (22.0, 32.0)    # Superbay cantilever tip height [inf, photo l3 ratio, low; identification unverified]
SB_FOLD, SB_DOOR_GAP = 1.5, 3.0            # fold amplitude at the tip face [unk], door head below the tip [unk] (schematic)
# spine-end hip facets on NAIP 2024 (roof rectified to the building frame, review backlog r1-24; 0.25 m px): the roof spans
# b -75..+63 in that crop (138 m, centre -6 -> shifted to the drawing frame); the bright spine ends ~10 m (NNE) and ~6 m (SSW)
# before the roof edges, where facets fall to the edge; the NNE ridge end is ~9 m wide (a -2.5..+6.3) [obs, approx]
SB_HIP = {'nne': 10.3, 'ssw': 6.0, 'ridge_a': (-2.5, 6.3)}
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
    'ltp_garage_1': ('Long-Term Parking Garage 1 (Bldg 795)', 'north-end parapet 16.5 m (15.9-16.8) [obs, shadow];\nDOF 86 / 91 ft [pub] = stair towers / helix? [inf]; >= 5 levels [inf]', 'obs'),
    'ltp_garage_2': ('Long-Term Parking Garage 2 (Bldg 794)', '6 levels, 12 ft floor-to-floor [pub] -> deck 60 ft [inf];\nroof PV canopies [pub], height unknown', 'inf'),
    'rental_car_center': ('Rental Car Center (Bldg 780)', '5 levels [pub]; "66-foot-tall" = 20.12 m [pub, disputed as roof];\nroof outline 54 / 59 ft [pub DOF]; DOF TANK 60 ft [pub]\n= station stair / elevator tower? [inf]', 'pub'),
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


# ------------------------------------------------------------------------------------------------ Garages A / G geometry
# Read for these sheets on 2026-11-04 (review backlog r1-32 / r2-23) from the SFO Museum outlines (flysfo ground traces),
# the SFO Museum AirTrain polygons and NAIP 2024; frame: u along the outline's minimum-rectangle long side from its WSW
# end, b = to the left of +u (+b = NNW, -b = SSE = the face drawn on BL-03).
#  - The outline is NOT one garage block: the garage body ends at u ~150 m; the remaining ~130 m is a 9.1-m-wide tail
#    that coincides with the SFO Museum 'AirTrain Rail' polygon (Garage A: 642 of its 1,336 m2) = the AirTrain guideway
#    to the ITB station, not a parking structure.
#  - The helix drum is the rounded WEST end: circle fit to the outline vertices of the arc (residuals < 0.6 m).
#  - NAIP: the drum's ribbed west facade is imaged up to a top ring that is continuous with the roof deck, and the deck
#    edges carry the same ~13 m east lean (2-D roof scan 13.0 m vs drum band 13.25 m, Garage A): the drum top ring is
#    level with the deck within the method's error, NOT a tower above a lower deck. Photo a2 (Pi.1415926535, Sept 2025,
#    CC BY-SA 4.0) shows the same: the banded parapet runs over the rounded end at the long-face level; above the deck
#    stand only a smaller core cylinder (NAIP: dark disc ~13 m) and square stair / elevator boxes.
#  - Garage A rooftop box: imaged x -1462..-1440, z 536..548 (shadow on its N side), lean-corrected by the 13 m east shift.
GAR = {
    'garage_a': dict(nm='Garage A', drum=39.6, drum_rng=(38.0, 41.5), zwin=(535.0, 560.0), lean=13.25, station=1729791949,
                     rail_near=True, box_img=((-1462.0, 536.0), (-1440.0, 548.0))),
    'garage_g': dict(nm='Garage G', drum=37.6, drum_rng=(36.0, 40.0), zwin=(358.0, 385.0), lean=12.0, station=1729791947,
                     rail_near=False, box_img=None),
}
GAR_CORE_D = 13.0           # helix core cylinder diameter [obs NAIP dark disc, approx]; its height above the deck [unk]
GAR_PITCH = (3.05, 3.5)     # typical parking floor-to-floor, an ASSUMPTION used only to show the level-count range [inf]
_GG = {}


def ggeom(k):
    """Garage A / G plan geometry in the (u, b) frame of the outline's minimum rectangle (see GAR)."""
    if k in _GG: return _GG[k]
    from shapely.geometry import Polygon, LineString
    g = GAR[k]; mr = LB[k]['footprint']['min_rect']
    c = np.array(mr['centre'], float); a = hdg_vec(mr['long_side_heading_deg']); b = np.array([a[1], -a[0]]); L = mr['length_m']
    ub = lambda p: (float(np.dot(np.asarray(p, float) - c, a) + L / 2), float(np.dot(np.asarray(p, float) - c, b)))
    ring = np.array(D.sfom(g['nm'], 'structures')[0][0], float)
    P = Polygon(ring)
    sec = []
    for u in np.arange(0.25, L, 0.5):
        p = c + a * (u - L / 2)
        sec.append((u, LineString([p - b * 90, p + b * 90]).intersection(P).length))
    Lb = max(u for u, w in sec if w >= 20.0)                                  # garage body: cross-section >= 20 m
    tail_w = float(np.median([w for u, w in sec if u > Lb + 30]))
    sel = ring[(ring[:, 1] >= g['zwin'][0]) & (ring[:, 1] <= g['zwin'][1]) & (ring[:, 0] < ring[:, 0].min() + 15)]
    A = np.c_[2 * sel[:, 0], 2 * sel[:, 1], np.ones(len(sel))]
    s = np.linalg.lstsq(A, sel[:, 0] ** 2 + sel[:, 1] ** 2, rcond=None)[0]
    dc = np.array([s[0], s[1]]); R = float(np.sqrt(s[2] + s[0] ** 2 + s[1] ** 2))
    uc, bc = ub(dc)
    st = next(f for f in D.AIR['structures'] if f['id'] == g['station'])
    sp = [ub(p) for p in st['polys'][0][0]]
    box = None
    if g['box_img']:
        (x0, z0), (x1, z1) = g['box_img']; lx = g['lean']
        cs = [ub((x - lx, z)) for x in (x0, x1) for z in (z0, z1)]
        box = (min(q[0] for q in cs), max(q[0] for q in cs), min(q[1] for q in cs), max(q[1] for q in cs),
               [(x - lx, z) for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))])
    half = float(np.median([w for u, w in sec if 20 < u < Lb - 20])) / 2
    _GG[k] = dict(c=c, a=a, b=b, L=L, Lb=round(Lb, 1), tail_w=round(tail_w, 1), drum_c=dc, R=round(R, 1), uc=uc, bc=bc,
                  st_u=(min(q[0] for q in sp), max(q[0] for q in sp)), st_b=(min(q[1] for q in sp), max(q[1] for q in sp)),
                  box=box, half=half, ring=ring)
    return _GG[k]


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
    for k in ('garage_a', 'garage_g'):
        G = ggeom(k)
        V.circle(G['drum_c'], G['R'], 'obs', lw=0.7, z=3.2)
        V.circle(G['drum_c'], GAR_CORE_D / 2, 'unk', z=3.2)
        p0 = G['c'] + G['a'] * (G['Lb'] - G['L'] / 2)
        V.line([p0 - G['b'] * 36, p0 + G['b'] * 36], 'obs', lw=0.5, z=3.2, ls=(0, (4, 2)))
        if G['box']:
            V.poly(G['box'][4], 'unk', z=3.2)
    Ga, Gg = ggeom('garage_a'), ggeom('garage_g')
    V.leader(Ga['drum_c'] + np.array([0, Ga['R']]), -4, -14, f'helix drums (west ends): circle fits to the outline arcs, A D {2 * Ga["R"]:.0f} m,\n'
             f'G D {2 * Gg["R"]:.0f} m [obs]; core cylinder ~13 m (dotted) [obs NAIP]; Garage A\nrooftop box (dotted, lean-corrected) [obs NAIP]', 'obs', fs=3.5, ha='right')
    pA = Ga['c'] + Ga['a'] * (Ga['L'] / 2 - 40) - Ga['b'] * 18
    V.leader(pA, -2, -34, f'dashed: end of the garage body (u {Ga["Lb"]:.0f} / {Gg["Lb"]:.0f} m); beyond it the outlines are a\n'
             f'{Ga["tail_w"]:.1f}-m tail along the AirTrain guideway to the ITB station [obs]', 'obs', fs=3.5, ha='right')
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
    tk = next(d for d in LB['rental_car_center']['dof'] if d['type'] == 'TANK')
    V.circle(tk['world'], RCC_TOWER_D / 2, 'inf', z=3.2)
    V.line([RCC_N, RCC_S], 'obs', lw=0.4, z=3.1, ls=(0, (1, 1.5)))
    V.leader(np.array(tk['world']) + np.array([RCC_TOWER_D / 2, 0]), 14, -22, f'station tower D ~{RCC_TOWER_D} m at the TANK point\n[inf, photo l5]; '
             'dotted: west-face chord\ndrawn on BL-03 [obs]', 'inf', fs=3.4)
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
    for sg, L_ in ((1, SB_HIP['nne']), (-1, SB_HIP['ssw'])):
        e_, r_ = sg * 69.0, sg * (69.0 - L_)
        for a_e, a_r in ((-14, SB_HIP['ridge_a'][0]), (18, SB_HIP['ridge_a'][1])):
            V.line([c + sv * a_e + tv * e_, c + sv * a_r + tv * r_], 'obs', lw=0.5, z=3.3)
        V.line([c + sv * SB_HIP['ridge_a'][0] + tv * r_, c + sv * SB_HIP['ridge_a'][1] + tv * r_], 'obs', lw=0.5, z=3.3)
    V.leader(c + sv * 2 + tv * 64, 12, 18, f"spine-end hip facets: NNE ~{SB_HIP['nne']:.0f} m, SSW ~{SB_HIP['ssw']:.0f} m [obs NAIP, approx];\n"
             'the faceted roof ends of photo l3 [obs, identification unverified]', 'obs', fs=3.6)
    V.leader(c + tv * -40, -10, 56, 'central spine 32 m (a -14..+18) along the 27.8 deg grid [obs];\nfolded cantilever roofs WNW / ESE, ~66.5 m beyond it, 8 bays\n'
             'of 17.3 m per side [obs] (Deep3DS: "50 ft structural bays" [pub],\nconflict); roof 165 m overall [obs]', 'obs', fs=3.8)
    sbL = LB['superbay']['footprint']['min_rect']
    Wsp = min(sbL['length_m'], sbL['width_m'])
    V.dim(c + sv * 18 + tv * -69, c + sv * 18 + tv * 69, -14, f'roof 138.0 m along the spine (8 x 17.25) [obs] vs outline {Wsp:.1f} m [obs]: '
          f'{(138.0 - Wsp) / 2:.2f} m per end = roof overhang [inf] or outline error [unk]', 'inf', fs=3.6)
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
    S.note('Roof features drawn: the Superbay spine and roof bays, the Garage A / G helix drums (outline arcs), their core cylinders and the '
           'Garage A rooftop box (NAIP), the RCC station tower (inferred size). Other stair / elevator towers, canopies and PV are not measured '
           'as plan geometry.')
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


def ground(V, xa, xb):
    V.ax.fill_between([xa, xb], [-2.0, -2.0], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(xa, 0), (xb, 0)], 'pub', lw=0.7)


def garage_elev(V, x0, k, title):
    """International Garage A / G: the SSE long face, looking NNW, u from the WSW end (geometry: GAR / ggeom). The roof deck
    is not measured: the body is drawn dotted at the drum-ring value (NAIP: the ring is level with the deck) with the
    range of every candidate beside it; the drum stands behind the face (hidden lines)."""
    g = GAR[k]; G = ggeom(k); L, Lb, uc, R = G['L'], G['Lb'], G['uc'], G['R']
    hd = g['drum']; h7 = hd * 6 / 8
    scan = LB[k]['shift_scan']['peaks']
    ground(V, x0 - 6, x0 + L + 6)
    V.poly([(x0, 0), (x0 + Lb, 0), (x0 + Lb, hd), (x0, hd)], 'unk', fc='#f4f7fb', z=2)
    for h in np.arange(1, 9) * hd / 9:                                         # 9 levels as equal ninths: placeholder
        V.line([(x0, h), (x0 + Lb, h)], 'unk', lw=0.18, z=2.05)
    # the helix drum behind the near face (hidden), its top ring at the deck line
    V.poly([(x0 + uc - R, 0), (x0 + uc + R, 0), (x0 + uc + R, hd), (x0 + uc - R, hd)], 'obs', lw=0.45, ls=(0, (3, 1.5)), z=2.3)
    r = GAR_CORE_D / 2
    V.poly([(x0 + uc - r, hd), (x0 + uc + r, hd), (x0 + uc + r, hd + 4.0), (x0 + uc - r, hd + 4.0)], 'unk', fc='#eef2f6', z=2.3)
    if G['box']:
        u0, u1 = G['box'][0], G['box'][1]
        V.poly([(x0 + u0, hd), (x0 + u1, hd), (x0 + u1, hd + 3.5), (x0 + u0, hd + 3.5)], 'unk', fc='#eef2f6', z=2.3)
        V.leader((x0 + (u0 + u1) / 2, hd + 3.5), x0 + 60 - (x0 + (u0 + u1) / 2), 56 - (hd + 3.5), f'rooftop box u {u0:.0f}-{u1:.0f} (imaged 22 x 12 m, lean-corrected) [obs NAIP];\n'
                 'stair / elevator tower over the station? [inf]; height unk (drawn 3.5 m)', 'obs', fs=3.4)
    # AirTrain at Level 7: placeholder height = 6/8 of the deck line (equal levels, L1 at grade, L9 = the roof)
    s0, s1 = G['st_u']
    hid = (0, (2, 1.5))
    for a_, b_, ls in ((-6, 0, None), (0, Lb, hid), (Lb, L + 6, None)):
        if not g['rail_near'] and a_ == 0: ls = hid
        for h in (h7 - 1.0, h7 + 1.0):
            V.line([(x0 + a_, h), (x0 + b_, h)], 'unk', lw=0.5, z=2.4, ls=ls)
    V.poly([(x0 + s0, h7 + 1.0), (x0 + s1, h7 + 1.0), (x0 + s1, h7 + 6.0), (x0 + s0, h7 + 6.0)], 'unk', z=2.35, ls=hid)
    side = 'along the SSE side, behind this face' if g['rail_near'] else 'along the NNW side (far side)'
    V.leader((x0 + (s0 + s1) / 2, h7 + 6.0), x0 + 2 - (x0 + (s0 + s1) / 2), 68 - (h7 + 6.0),
             f'AirTrain station inside the garage, u {s0:.0f}-{s1:.0f} [obs SFO Museum polygon], {side},\nreached from Level 7 [pub]; '
             f'guideway drawn at 6/8 of the deck line = {h7:.1f} m (equal levels) [unk];\n'
             f'with typical 3.05-3.5 m levels L7 = {6 * GAR_PITCH[0]:.0f}-{6 * GAR_PITCH[1]:.0f} m [inf]', 'unk', fs=3.4, ha='left')
    V.leader((x0 + (Lb + L) / 2, h7 - 1.0), 2, -9, f'AirTrain guideway to the ITB station on the {G["tail_w"]:.1f}-m-wide outline tail\n'
             f'(u {Lb:.0f}-{L:.0f}; overlaps the SFO Museum guideway polygon) [obs]', 'obs', fs=3.4)
    V.leader((x0 + uc, hd - 3.0), 2 - uc, 80 - (hd - 3.0),
             f'helix drum D {2 * R:.0f} m at the west end (outline arc, centre u {uc:.0f}) [obs], behind this face (dashed);\n'
             f'its ribbed west facade rises to a top ring at {hd} m ({g["drum_rng"][0]}-{g["drum_rng"][1]}) [obs NAIP, low] that is level\n'
             'with the deck (same east lean), not a tower above it; core cylinder D ~13 m above the deck [obs], height unk (drawn 4 m)',
             'obs', fs=3.4, ha='left')
    # range of the unmeasured deck
    ux = x0 + Lb + 3
    lo, hi = 8 * GAR_PITCH[0], g['drum_rng'][1]
    V.line([(ux, lo), (ux, hi)], 'unk', lw=0.6, z=3, ls='-')
    for h in (lo, 8 * GAR_PITCH[1], 25.0, 30.0, hd):
        V.line([(ux - 1.2, h), (ux + 1.2, h)], 'unk', lw=0.6, z=3, ls='-')
    pk = scan[0]
    sc = (f'{pk["h_if_true_footprint_m"]} m = NAIP 2-D roof shift {pk["dx_m"]} m [obs, low]' if pk['score'] > 1.2 * scan[1]['score'] else
          f'{pk["h_if_true_footprint_m"]} m = NAIP 2-D roof shift {pk["dx_m"]} m - NOT a clear maximum [obs, very low]')
    V.leader((ux, hi), 3, 7, f'roof deck NOT measured [unk]; dotted at the drum ring {hd} m; candidates:\n{hd} ({g["drum_rng"][0]}-{hi}) drum ring band [obs, low]; '
             f'{sc};\n25-30 m AirTrain-photo reading [DISPUTED]; {lo:.1f}-{8 * GAR_PITCH[1]:.1f} m = 8 rises x 3.05-3.5 m\n'
             '(typical parking pitch, NOT published) [inf]. 9 levels [pub]; clearance 8 ft 2 in [pub]', 'unk', fs=3.4)
    V.text((x0 + Lb * 0.62, 12.0), 'light precast panels in a square grid; perforated metal screens\nwith horizontal slots over the parking levels [obs spec garage_ag_facade];\n'
           'level lines = equal ninths (placeholder) [unk]', 'obs', fs=3.4)
    V.dim((x0, 0), (x0 + Lb, 0), -4, f'{Lb:.0f} m garage body [obs outline]', 'obs', fs=3.8)
    V.dim((x0 + Lb, 0), (x0 + L, 0), -4, f'{L - Lb:.0f} m guideway tail (outline min. rectangle {L:.0f} m) [obs]', 'obs', fs=3.6)
    V.text((x0 + L / 2, -9), title, 'pub', fs=4.6, weight='bold', bg=False, color='#000000', style='normal')


def _gar_r2(k):
    """the 3-D (review r2) garage heights: photo a2 with its solved camera (tools/blender/landside_geom.GAR_R2; the absolute scale
    rests on the Grand Hyatt top 44 m [inf]) - imported lazily (landside_geom imports this module)."""
    try:
        sys.path.insert(0, os.path.join(ROOT, 'tools', 'blender'))
        import landside_geom as LG
        return dict(LG.GAR_R2.get(k, {}))
    except Exception:  # noqa: BLE001
        return None


def garage_r3(V, x0, k):
    """close-out r3 (buildings-10): draw the 3-D state of the garage over the round-1 sheet: the a2 parapet / deck / level pitch /
    drum ring (solid, [obs a2]) and the NAIP lean-model alternative, with the reading adopted (the sheet is the reference again)."""
    r2 = _gar_r2(k)
    if not r2: return
    g = GAR[k]; G = ggeom(k); Lb, uc, R = G['Lb'], G['uc'], G['R']
    par, deck, ring, pitch = r2['parapet'], r2['deck'], r2['ring'], r2['pitch']
    V.poly([(x0, 0), (x0 + Lb, 0), (x0 + Lb, par), (x0, par)], 'obs', fc='none', lw=1.1, z=3.6)
    for i in range(1, 9):
        V.line([(x0, i * pitch), (x0 + Lb, i * pitch)], 'obs' if k == 'garage_a' else 'inf', lw=0.25, z=3.55, color='#3c6e8f')
    V.line([(x0 + uc - R, ring), (x0 + uc + R, ring)], 'obs', lw=1.0, z=3.6)
    lean = float(D.lean_frame(np.asarray(LB[k]['footprint']['min_rect']['centre'], float), ring)[0]) / ring
    band = 13.25 if k == 'garage_a' else 12.00
    ncol = 9 if k == 'garage_a' else 4
    V.leader((x0 + Lb * 0.30, par), -2, 30 if k == 'garage_a' else 26,
             f'3-D STATE (review r2, close-out r3): parapet {par:.2f} m, roof deck (L9 = 8 x {pitch:.2f} m) {deck:.2f} m, drum ring {ring:.2f} m '
             f'[obs photo a2, solved camera, {ncol} parapet columns;\nabsolute scale: Grand Hyatt top 44 m [inf, 40-48 -> -/+2.4 m]] - '
             f'SUPERSEDES the {g["drum"]} m NAIP drum-ring reading (dotted body).\nLean-model conflict, resolved [inf]: the NAIP drum band lies {band:.2f} m E of the outline '
             f'arc; the NAIP frame model (spec naip.k_model,\nITB poles) gives {lean:.3f} m/m here -> {band / lean:.1f} m if the band were pure relief; that needs a Hyatt '
             f'of ~{44 * band / lean / ring:.0f} m (outside 40-48).\nAdopted: the a2 height, the band = relief {lean * ring:.1f} m + {band - lean * ring:.1f} m '
             "between the SFO Museum outline arc and the ring's outer edge [inf]; the Hyatt height (owner item OD-6) decides",
             'obs', fs=3.2, ha='left')


def garage_west_end(V, xe, k):
    """Garage A west end (helix drum face), looking ENE: x = xe + (half - b), i.e. NNW on the left, SSE on the right."""
    g = GAR[k]; G = ggeom(k); hd = g['drum']; h7 = hd * 6 / 8; half, R, bc = G['half'], G['R'], G['bc']
    X = lambda b: xe + (half - b)
    ground(V, X(half) - 4, X(-half) + 4)
    V.poly([(X(half), 0), (X(-half), 0), (X(-half), hd), (X(half), hd)], 'unk', fc='#f4f7fb', z=2)
    V.poly([(X(bc + R), 0), (X(bc - R), 0), (X(bc - R), hd), (X(bc + R), hd)], 'obs', fc='#e3ebf3', z=2.2)
    for h in np.arange(1, 9) * hd / 9:
        V.line([(X(bc + R), h), (X(bc - R), h)], 'obs', lw=0.25, z=2.3, color='#6f8796')
    r = GAR_CORE_D / 2
    V.poly([(X(bc + r), hd), (X(bc - r), hd), (X(bc - r), hd + 4.0), (X(bc + r), hd + 4.0)], 'unk', fc='#eef2f6', z=2.3)
    rb = (-27.0, -9.0)                                     # guideway polygon across the west end, b -27..-9 (SFO Museum) [obs]
    V.poly([(X(rb[1]), h7 - 1.0), (X(rb[0]), h7 - 1.0), (X(rb[0]), h7 + 5.0), (X(rb[1]), h7 + 5.0)], 'unk', fc='#ffffff', z=2.4)
    V.line([(X(rb[1]), h7 - 1.0), (X(rb[0]), h7 - 1.0)], 'unk', lw=0.8, z=2.5, ls='-')
    V.leader((X(bc), hd * 0.5), -3, 40, f'helix drum D {2 * R:.0f} m [obs outline arc]: continuous horizontal bands\n'
             '[obs spec / photo a2], band count schematic; top ring = deck level', 'obs', fs=3.3, ha='right')
    V.leader((X((rb[0] + rb[1]) / 2), h7 + 5.0), -1, 20, 'AirTrain portal, guideway b -27..-9\n[obs polygon] at L7 [pub],\nheight placeholder [unk]', 'unk', fs=3.3, ha='right')
    V.dim((X(half), 0), (X(-half), 0), -4, f'{2 * half:.1f} m', 'obs', fs=3.6)
    V.text((X(0), -9), 'GARAGE A, WEST END, looking ENE', 'pub', fs=4.2, weight='bold', bg=False, color='#000000', style='normal')


def cg_stations(V, x0, k='central_garage'):
    """Central garage: the AirTrain ring at Level 5 and the T1 / T2 station enclosures on the near (ESE) face, u from the SSW
    end along the minimum rectangle; positions from the SFO Museum station polygons [obs], level 5 [pub], heights [unk]."""
    mr = LB[k]['footprint']['min_rect']; c = np.array(mr['centre']); a = hdg_vec(mr['long_side_heading_deg']); L = mr['length_m']
    b = np.array([a[1], -a[0]])
    h5 = 24.69 * 4 / 5                                        # level 5 on the equal-fifths placeholder [unk]
    ground_ = []
    for sid, nm in ((1729791955, 'T1'), (1729791959, 'T2'), (1729791957, 'T3')):
        P = np.array(next(f for f in D.AIR['structures'] if f['id'] == sid)['polys'][0][0], float)
        u = (P - c) @ a + L / 2; bb = (P - c) @ b
        near = bb.mean() < 0
        V.poly([(x0 + u.min(), h5), (x0 + u.max(), h5), (x0 + u.max(), h5 + 4.5), (x0 + u.min(), h5 + 4.5)], 'unk',
               fc='#ffffff' if near else 'none', z=2.6 if near else 2.05, ls=None if near else (0, (2, 1.5)))
        if near: V.text((x0 + (u.min() + u.max()) / 2, h5 + 2.3), nm + (' (T3 behind)' if nm == 'T2' else ''), 'unk', fs=3.2, bg=False)
        ground_.append((nm, u.min(), u.max(), near))
    for h in (h5 - 1.2, h5):
        V.line([(x0 - 6, h), (x0 + L + 6, h)], 'unk', lw=0.5, z=2.55)
    t1 = ground_[0]
    V.leader((x0 + (t1[1] + t1[2]) / 2, h5 + 4.5), -2, 17,
             'AirTrain T1 / T2 / T3 stations on Level 5 [pub] at u ' + ' / '.join(f'{u0:.0f}-{u1:.0f}' for _, u0, u1, _ in ground_) +
             ' [obs SFO Museum polygons]:\nglazed platform enclosures, single-pitch roof on X-braced struts, dark stair / elevator tower '
             '[obs photo, Famartin 2025];\nring guideway round the garage at Level 5 [pub]; drawn on the level-5 placeholder [unk], '
             'enclosure height unk (drawn 4.5 m)', 'unk', fs=3.4)


RCC_N, RCC_S = (-2260.7, -1187.1), (-2258.3, -966.3)   # west-face ends of the SFO Museum outline (its N-most / SW corner) [obs]
RCC_TOWER_D = 6.5   # station stair / elevator cylinder diameter: photo l5, ~2.7 x the width of a platform-door cabin (~2.4 m assumed) [inf]


def rcc_west_elev(V, x0):
    """Rental Car Center, WEST (AirTrain) face looking east, x from the N end: the face where every roof-outline DOF point,
    the station and the TANK are (spec rcc_dof, rcc_facade). Projected on the chord of the outline's west face (heading 179.4)."""
    pn, ps = np.array(RCC_N), np.array(RCC_S); e = unit(ps - pn); Lw = float(np.dot(ps - pn, e))
    X = lambda p: x0 + float(np.dot(np.asarray(p, float) - pn, e))
    H = 54 * FT
    ring = np.array(D.sfom('Rental Car Center', 'structures')[0][0], float)
    Xm = max(X(p) for p in ring) - x0                      # the south face recedes to the SE: silhouette beyond the SW corner
    ground(V, x0 - 6, x0 + Xm + 6)
    V.poly([(x0 + Lw, 0), (x0 + Xm, 0), (x0 + Xm, H), (x0 + Lw, H)], 'pub', fc='#eef1f5', z=1.9, lw=0.4)
    V.text((x0 + (Lw + Xm) / 2, H / 2), 'S face\nreceding\nSE (set\nback to\n70 m)', 'obs', fs=2.9, bg=False)
    V.poly([(x0, 0), (x0 + Lw, 0), (x0 + Lw, H), (x0, H)], 'pub', fc='#f4f7fb', z=2)
    for h in np.arange(1, 4) * H / 4:
        V.line([(x0, h), (x0 + Lw, h)], 'unk', lw=0.25, z=2.05)
    V.line([(x0, 66 * FT), (x0 + Lw, 66 * FT)], 'pub', lw=0.35, z=2.1, ls=(0, (6, 3)))
    V.text((x0 + 4, 66 * FT + 1.2), '+20.12 "66-foot-tall" [pub] (tallest element? definition not stated)', 'pub', fs=3.4, ha='left')
    V.text((x0 + 4, H - 1.6), '+16.46 roof outline 54 ft [pub DOF, 3 points]', 'pub', fs=3.4, ha='left')
    for d in LB['rental_car_center']['dof']:
        if d['type'] != 'BLDG' or d['agl_ft'] < 50: continue
        xx = X(d['world'])
        if d['agl_ft'] > 55:
            V.line([(xx, H), (xx, d['agl_m'])], 'pub', lw=0.6, z=2.6)
        V.mark((xx, d['agl_m']), 'pub', marker='v', ms=3.2)
        V.text((xx, d['agl_m'] + 1.6), f"{d['agl_ft']}", 'pub', fs=3.2, bg=False)
    # station: SFO Museum polygon (west of the face); platform level unknown -> drawn on the L4 placeholder (customer service
    # on floors 1 and 4 [pub, Conrac]; the station at the L4 service floor [inf])
    sp = np.array(next(f for f in D.AIR['structures'] if f['id'] == 1729791943)['polys'][0][0], float)
    s0, s1 = min(X(p) for p in sp), max(X(p) for p in sp)
    hp = 3 * H / 4
    V.line([(s0, hp), (s1, hp)], 'unk', lw=0.9, z=2.7, ls='-')
    tt = np.linspace(0, 1, 30)
    V.line(np.c_[s0 + (s1 - s0) * tt, hp + 3.0 + 1.0 * np.sin(np.pi * tt)], 'unk', lw=0.6, z=2.7)
    for xx in (s0 + 1, s1 - 1):
        V.line([(xx, hp), (xx, hp + 3.0)], 'unk', lw=0.4, z=2.7)
    tk = next(d for d in LB['rental_car_center']['dof'] if d['type'] == 'TANK'); xt = X(tk['world']); r = RCC_TOWER_D / 2
    V.poly([(xt - r, 0), (xt + r, 0), (xt + r, tk['agl_m']), (xt - r, tk['agl_m'])], 'inf', fc='#e9e4d6', z=2.8, hatch='////')
    V.mark((xt, tk['agl_m']), 'pub', marker='v', ms=3.2)
    V.leader((xt, tk['agl_m']), 6, 14, f"DOF 06-034240 TANK 60 ft = {tk['agl_m']} m [pub] = the free-standing cylindrical perforated-metal\n"
             f"stair / elevator tower of the AirTrain station [inf, photo l5]; D ~{RCC_TOWER_D} m [inf, scaled from the platform-door cabins];\n"
             "l5 shows it ~2 D above the platform: platform level or TANK identity unresolved [conflict]", 'inf', fs=3.4)
    V.leader(((s0 + s1) / 2, hp + 4.0), -10, 27, f'AirTrain station x {s0 - x0:.0f}-{s1 - x0:.0f} [obs SFO Museum polygon]: curved metal canopy,\n'
             'glazed platform-door cabins [obs photo l5]; platform drawn at the L4 placeholder\n(customer service on floors 1 and 4 [pub]; station at L4 [inf]); level unk', 'unk', fs=3.4, ha='right')
    V.leader((x0 + 0.3 * Lw, H * 0.7), -8, 30, 'west wall [obs photo l5, Pi.1415926535 2021, CC BY-SA 4.0; spec rcc_facade]: board-formed\n'
             'concrete with horizontal ribbon windows at the platform / service level, a concrete band,\nand above it a CANTED (outward-leaning) '
             'screen of horizontal green-grey metal blades (louvres,\ngaps visible); see the wall key above. Band heights not measured [unk]', 'obs', fs=3.4, ha='right')
    # wall key (section through the west wall, west = left; order only, NOT to scale): the canted louvre screen leaning out
    # over the board-formed concrete band and the ribbon windows of the platform / service level (photo l5)
    kx, ky = x0 + Xm - 22, 30.0                            # drawn above the roof, in free space; its own base line
    V.line([(kx - 3, ky), (kx + 3, ky)], 'unk', lw=0.4, z=3, ls='-')
    V.line([(kx, ky), (kx, ky + 4.0)], 'unk', lw=0.8, z=3, ls='-')                                      # wall below (unk)
    V.poly([(kx - 0.4, ky + 4.0), (kx + 0.4, ky + 4.0), (kx + 0.4, ky + 8.0), (kx - 0.4, ky + 8.0)], 'obs', fc='#bcd3df', z=3)
    V.poly([(kx - 0.9, ky + 8.0), (kx + 0.9, ky + 8.0), (kx + 0.9, ky + 11.0), (kx - 0.9, ky + 11.0)], 'obs', fc='#d9d9d9', z=3)
    for h in np.linspace(11.6, 21.0, 9):                                                                 # louvre blades
        xx = kx + 0.6 - 4.5 * (h - 11.0) / 10.0
        V.line([(xx - 1.6, ky + h - 0.5), (xx + 0.4, ky + h)], 'obs', lw=0.6, z=3.1, ls='-')
    V.line([(kx + 0.9, ky + 11.0), (kx - 3.9, ky + 21.6)], 'obs', lw=0.3, z=3.05, ls=(0, (2, 1)))
    V.text((kx + 2.0, ky + 17.0), 'canted louvre screen', 'obs', fs=3.0, ha='left')
    V.text((kx + 2.0, ky + 9.5), 'concrete band', 'obs', fs=3.0, ha='left')
    V.text((kx + 2.0, ky + 6.0), 'ribbon windows', 'obs', fs=3.0, ha='left')
    V.text((kx - 6.0, ky + 27.0), 'WEST WALL KEY (section, west\nto the left; order only, NOT\nto scale) [obs photo l5]', 'obs', fs=3.0, ha='left')
    V.dim((x0, 0), (x0 + Lw, 0), -4, f'{Lw:.0f} m west face (outline chord N corner - SW corner) [obs]', 'obs', fs=3.8)
    V.dim((x0 + Lw, 0), (x0 + Xm, 0), -4, f'{Xm - Lw:.0f}', 'obs', fs=3.4)
    V.text((x0 + Lw / 2, -9), 'RENTAL CAR CENTER (Bldg 780), WEST (AirTrain) face, looking east', 'pub', fs=4.6, weight='bold', bg=False,
           color='#000000', style='normal')
    V.text((x0 + Lw * 0.74, 5.5), '5 levels [pub] (level lines = equal quarters, placeholder [unk]);\n2,485 ready-return stalls [pub]; DOF roof points 54 / 59 ft '
           '(06-035329 / -35205 / -35204 / -35203)\nat their projected positions [pub]; 66 ft is 7-12 ft above them (definition disputed)', 'pub', fs=3.4)


GH_P = 44.0 / 13.2          # Hyatt floor pitch: the inferred 44 m over the 13.2 pitches of photo 7391 [inf]
GH_POD, GH_COL = 3.2, 1.0   # podium / recessed colonnade level in pitches (spec gh_height note, photo 7391) [obs ratio]


def hyatt_elev(V, x0, W):
    """Grand Hyatt east face (photo l4 = 'Harvey Milk Terminal 1 Community Day - July 2019 (7391)', Gregory Varnum, CC BY-SA 4.0,
    seen from the airfield; left = SSW): spec gh_plan_shape / gh_facade [obs] and the pitch decomposition of gh_height."""
    # fractions of the face are read on l4 (1920 px: slab x 56-1860, grade y 1065, parapet y 372-378, pitch 52.5 px)
    p = GH_P; H = 13.2 * p; hp, hc = GH_POD * p, (GH_POD + GH_COL) * p
    pod = 0.47 * W                                   # dark podium under the south half (l4: x 75-895) [obs photo]
    V.poly([(x0, 0), (x0 + W, 0), (x0 + W, H), (x0, H)], 'inf', fc='#dbe7ee', z=2, lw=0.8)        # glass curtain wall
    V.poly([(x0, 0), (x0 + pod, 0), (x0 + pod, hp), (x0, hp)], 'obs', fc='#4b4f55', z=2.2, lw=0.5)  # podium, dark metal panels
    col0, col1 = x0 + 0.02 * W, x0 + 0.10 * W        # recessed colonnade level only at the south end (l4: x 95-235) [obs photo]
    V.poly([(col0, hp), (col1, hp), (col1, hc), (col0, hc)], 'obs', fc='#7d858d', z=2.2, lw=0.4)
    for xx in np.linspace(col0, col1, 5)[1:-1]:
        V.line([(xx, hp), (xx, hc)], 'obs', lw=0.35, z=2.25, color='#d0d4d8')
    for i in range(1, 10):
        V.line([(x0, hc + i * p - p), (x0 + W, hc + i * p - p)], 'inf', lw=0.25, z=2.3, color='#6f8796')     # spandrel band per floor
    for xx in np.arange(x0 + 3.0, x0 + W, 3.0):
        V.line([(xx, hp if xx < x0 + pod else 0.0), (xx, H)], 'inf', lw=0.12, z=2.25, color='#8fa6b4')
    e1 = x0 + 0.049 * W                              # curved south end bay, horizontally banded glass (l4: x 56-145) [obs photo]
    V.poly([(x0, hp), (e1, hp), (e1, H), (x0, H)], 'obs', fc='#cfdde6', z=2.32, lw=0.35)
    for h in np.arange(hc, H, p / 3):
        V.line([(x0, h), (e1, h)], 'obs', lw=0.2, z=2.33, color='#6f8796')
    V.poly([(x0 - 1.8, 0), (x0, 0), (x0, 0.964 * H), (x0 - 1.8, 0.964 * H)], 'obs', fc='#cfcfcf', z=2.34, lw=0.4)   # end pier
    V.poly([(x0 - 1.5, 0.80 * H), (x0 - 0.3, 0.80 * H), (x0 - 0.3, 0.93 * H), (x0 - 1.5, 0.93 * H)], 'obs', fc='#c62828', z=2.35, lw=0.2)
    f0, f1 = x0 + 0.615 * W, x0 + 0.842 * W          # framed bay, up to one floor below the parapet (l4: x 1165-1575) [obs photo]
    V.poly([(f0, 0), (f1, 0), (f1, H - p), (f0, H - p)], 'obs', lw=0.6, z=2.36)
    a, b, c2 = x0 + 0.518 * W, x0 + 0.692 * W, x0 + 0.615 * W
    V.poly([(a, H), (b, H), (b, H + 1.4 * p), (a, H + 1.4 * p)], 'obs', fc='#4b4f55', z=2.4, lw=0.4)                 # penthouse, upper step
    V.poly([(c2, H), (x0 + 0.742 * W, H), (x0 + 0.742 * W, H + 0.65 * p), (c2, H + 0.65 * p)], 'obs', fc='#4b4f55', z=2.35, lw=0.4)
    for u in (-0.9, 0.027 * W, 0.905 * W, 0.961 * W):                                           # masts (l4: x ~45, 105, 1688, 1790)
        V.line([(x0 + u, H), (x0 + u, H + 0.8 * p)], 'obs', lw=0.5, z=2.4)
        V.line([(x0 + u - 0.9, H + 0.8 * p), (x0 + u + 0.9, H + 0.8 * p)], 'obs', lw=0.5, z=2.4)
    V.level(x0 + W + 1, H, f'+{H:.0f} parapet (40-48) [inf, low]: 13.2 floor pitches x 3.2-3.5 m (photo 7391) - NOT published', 'inf', len_mm=3, fs=3.9, u_line=x0 + W)
    V.level(x0 - 2.5, hc, f'top of the colonnade level ({GH_POD + GH_COL:.1f} pitches) +{hc:.1f} [inf]', 'inf', side='left', len_mm=3, fs=3.6, u_line=col0)
    V.level(x0 - 2.5, hp, f'podium roof ({GH_POD} pitches) +{hp:.1f} [inf]', 'inf', side='left', len_mm=3, fs=3.6, u_line=x0)
    V.leader((x0 + pod / 2, hp / 2), -32, -2, 'podium: dark metal panels, large glazed openings,\nporte-cochere (2-3 storeys) [obs photo l4 / spec gh_plan_shape];\n'
             'recessed colonnade level only at the south end (0.02-0.10) [obs photo l4]', 'obs', fs=3.4, ha='right')
    V.leader((x0 - 1.0, 0.86 * H), -12, 8, 'south end: light concrete pier with the vertical red sign, top ~1 m\nbelow the parapet, and the curved end bay '
             'of horizontally banded\nglass (0.00-0.05) [obs photo l4]; corner masts at 0.00 / 0.03 / 0.91 / 0.96,\n~0.8 pitch [obs photo l4]', 'obs', fs=3.4, ha='right')
    V.leader(((a + b) / 2, H + 1.4 * p), -4, 10, 'dark stepped mechanical penthouse (0.52-0.69 / 0.62-0.74 of the face,\n~1.4 / 0.65 pitches) [obs photo l4]', 'obs', fs=3.4, ha='right')
    V.leader((x0 + 0.75 * W, H - 2.5 * p), 4, 20, 'framed bay 0.62-0.84 up to one floor below the parapet [obs photo l4];\n'
             'unitised glass curtain wall, vertical mullion grid, one spandrel band\nper floor [obs gh_facade]; concave all-glass east face [obs gh_plan_shape];\n'
             'mullion module schematic (3 m) [inf]; 12 stories [pub], lobby + AirTrain\nat the 4th floor [pub]', 'obs', fs=3.4)
    V.text((x0 + W / 2, -14.5), 'spec "taller straight block at the north end" [obs, not re-checked]: photo l4 shows one parapet level along the whole east face; '
           'the north part is set apart only by the framed bay - drawn at the common parapet [conflict]', 'inf', fs=3.3)


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
    massing(V1, x, W, 'CENTRAL PARKING GARAGE (Bldg 195)', [('box', 24.69, 'pub', '+24.69 = 81 ft [pub]'),
                                                         ('levels', lv, 'unk')] +
            dof_items('central_garage', 24.69, {'06-034812': '109 ft pole\n[pub DOF]', '06-034813': '101 ft pole\n[pub DOF]',
                                                '06-039216': '130 ft antenna\n[pub DOF 4D, +-76 m]'}) +
            [('text', W / 2, 9, 'unk', '5 levels [pub]; level lines = equal fifths (placeholder) [unk];\n'
              'DOF points at their projected positions, u from the SSW end [pub]; ESE face, looking WNW;\n'
              '"five-level, 81-foot-tall" [pub]: what the 81 ft measures is not stated')])
    cg_stations(V1, x)
    x = W + 40
    garage_elev(V1, x, 'garage_a', 'INTERNATIONAL GARAGE A (Bldg 95), SSE face, looking NNW')
    garage_r3(V1, x, 'garage_a')
    garage_west_end(V1, x + L('garage_a') + 13, 'garage_a')
    V2 = S.view(0, 2 * rowh + 8, S.vw, rowh - 6, 1000, (300, 22), kind='elev', frame=False, title='2  GARAGE G, GRAND HYATT, CONSOLIDATED ADMINISTRATION CAMPUS')
    x = 0; W = L('garage_g')
    garage_elev(V2, x, 'garage_g', 'INTERNATIONAL GARAGE G (Bldg 495), SSE face, looking NNW')
    garage_r3(V2, x, 'garage_g')
    x = W + 40; W = L('grand_hyatt')
    massing(V2, x, W, 'GRAND HYATT AT SFO (Bldg 55), east (airfield) face', [('band', 40, 48, '#f3d9bf')])
    hyatt_elev(V2, x, W)
    x += W + 50; W = L('cac')
    massing(V2, x, W, 'CONSOLIDATED ADMINISTRATION CAMPUS', [('band', 17.4, 19.2, '#cfe0f2'), ('box', 60 * FT, 'inf', '+18.29 roof = 4 x 15 ft [inf]'),
                                                           ('lvlL', 64 * FT, 'inf', '~64 ft = 19.51 parapet [inf]'),
                                                           ('levels', [15 * FT * i for i in (1, 2, 3)], 'pub'),
                                                           ('text', W / 2, 9, 'pub', '4 stories, 15 ft floor-to-floor [pub]; NAIP shadow 17.4-19.2 m [obs] (band)')])
    V3 = S.view(0, rowh + 8, S.vw, rowh - 6, 1000, (335, 22), kind='elev', frame=False, title='3  LONG-TERM PARKING GARAGES 1 AND 2, RENTAL CAR CENTER')
    x = 0; W = L('ltp_garage_1')
    massing(V3, x, W, 'LONG-TERM PARKING GARAGE 1 (Bldg 795)', [('box', 16.5, 'obs', '+16.5 north-end parapet (15.9-16.8) [obs, NAIP shadow]')] +
            dof_items('ltp_garage_1', 16.5, {'06-035206': '91 ft [pub DOF]', '06-035207': '86 ft [pub DOF]'}) +
            [('text', W / 2, 8, 'inf', '>= 5 levels [inf: AirTrain + LTP2 links at Level 5];\nDOF tops = towers / helix ~10 m above the parapet [inf];\n'
              'DOF points at their projected positions, u from the NNW end [pub]')])
    x = W + 45; W = L('ltp_garage_2')
    massing(V3, x, W, 'LONG-TERM PARKING GARAGE 2 (Bldg 794)', [('box', 60 * FT, 'inf', '+18.29 deck = 5 x 12 ft [inf]'),
                                                               ('levels', [12 * FT * i for i in range(1, 5)], 'pub'),
                                                               ('text', W / 2, 9, 'pub', '6 levels, 12 ft floor-to-floor [pub] (level 1 at grade assumed [inf]);\nPV canopies above the deck (dotted), height unknown [unk]')])
    V3.line([(x, 60 * FT + 3.5), (x + W, 60 * FT + 3.5)], 'unk', lw=0.6)
    x += W + 40
    rcc_west_elev(V3, x)
    V4 = S.view(0, 8, S.vw, rowh - 6, 1000, (322, 22), kind='elev', frame=False, title='4  SUPERBAY HANGAR (section across the spine, WNW door face) and UNITED MOC LARGE HANGAR')
    x = 0; W = 165.0
    massing(V4, x, W, 'SUPERBAY HANGAR (Bldg 1060), section across the spine (WNW-ESE), looking NNE', [
        ('text', W / 2, 7, 'pub', 'four 747-size bays, 6 office levels\n+ central workshop [pub]; roof beams cantilever\n"over 230 ft from the centre" [pub]')])
    sp0, sp1 = 80.5 - 14, 80.5 + 18
    hs, ht = 135 * FT, SB_TIP
    V4.ax.fill_between([0, W], [SB_TIP_RNG[0]] * 2, [SB_TIP_RNG[1]] * 2, color='#e6e6e6', lw=0, zorder=1.3)
    V4.poly([(sp0, 0), (sp1, 0), (sp1, hs), (sp0, hs)], 'pub', fc='#f4f7fb', z=2.2)
    for a, b in ((0, sp0), (sp1, W)):
        tip = a if a == 0 else b; root = b if a == 0 else a
        V4.poly([(tip, 0), (root, 0), (root, hs - 1.5), (tip, ht)], 'inf', fc='#f9f9f9', z=1.8)          # cantilever roof falling to the tip
        V4.line([(root, hs - 1.5), (tip, ht)], 'inf', lw=1.0, z=2.3)
        V4.line([(tip, 0), (tip, ht - SB_DOOR_GAP)], 'unk', lw=0.5, z=2.3)
    V4.level(W + 1, hs, '+41.15 135 ft [pub DOF 1A, red light] at the spine edge', 'pub', len_mm=3, fs=3.9, u_line=sp1)
    V4.level(W + 1, 140 * FT, '+42.67 "140-foot tall roof" [pub, round number]', 'pub', len_mm=3, fs=3.9, u_line=sp1)
    V4.level(W + 1, 120 * FT, '+36.58 interior ~120 ft [pub] (where it is measured: not stated)', 'pub', len_mm=3, fs=3.9, u_line=sp1)
    V4.level(W + 1, ht, f'+{ht:.0f} ({SB_TIP_RNG[0]}-{SB_TIP_RNG[1]}) cantilever tips [inf, photo l3, low]; not published [unk]', 'inf', len_mm=3, fs=3.9, u_line=W)
    V4.dim((sp0, hs), (sp1, hs), 3, 'spine 32 m [obs]', 'obs', fs=3.8)
    V4.leader((sp0 - 25, (hs + ht) / 2 + 3), -10, 14, 'roofs fall from the spine to both tips [obs photo l3, BrokenSphere 2009,\nCC BY-SA 3.0, '
              'identification unverified; spec sb_layout]: tip / ridge\n~87 / 133 px -> ~27 m if the ridge is the 41.15 m DOF top [inf, low]', 'inf', fs=3.6, ha='right')
    # WNW face (door face) looking ESE: 8 folded roof bays of 17.25 m along the spine, two door openings per side
    xw0 = 252 + MOC['moc_large_hangar']['min_rect']['length_m'] + 38; Lr = 138.0; Lo = 134.5
    V4.ax.fill_between([xw0 - 6, xw0 + Lr + 6], [-2.0, -2.0], [0, 0], color='#dddddd', lw=0, zorder=1)
    V4.line([(xw0 - 6, 0), (xw0 + Lr + 6, 0)], 'pub', lw=0.7)
    edge = [(xw0 + 17.25 * i / 2, ht + (SB_FOLD if i % 2 else 0.0)) for i in range(17)]
    V4.poly([(xw0, 0), (xw0 + Lr, 0)] + edge[::-1], 'inf', fc='#f9f9f9', z=1.8)
    V4.line(edge, 'inf', lw=0.9, z=2.3)
    for i in range(1, 16, 2):
        V4.line([(xw0 + 17.25 * i / 2, ht + SB_FOLD), (xw0 + 17.25 * i / 2, hs - 1.5)], 'unk', lw=0.3, z=2.2)
    # spine roof behind, falling at its hipped ends (NNE = left in this view) to the tip level [plan obs NAIP, heights inf]
    V4.line([(xw0, ht + SB_FOLD), (xw0 + SB_HIP['nne'], hs - 1.5), (xw0 + Lr - SB_HIP['ssw'], hs - 1.5), (xw0 + Lr, ht + SB_FOLD)],
            'inf', lw=0.6, z=2.1)
    V4.leader((xw0 + SB_HIP['nne'] / 2, (ht + hs) / 2), -3, 38, 'spine roof behind; hipped ends\n(NNE ~10 m, SSW ~6 m) [obs NAIP plan,\nheights inf]', 'inf', fs=3.4, ha='right')
    dw = 67.0
    for k in range(2):
        a = xw0 + (Lr - 2 * dw) / 2 + k * dw
        V4.poly([(a + 0.5, 0), (a + dw - 0.5, 0), (a + dw - 0.5, ht - SB_DOOR_GAP), (a + 0.5, ht - SB_DOOR_GAP)], 'unk', fc='#ececec', z=2.0)
        for xx in np.linspace(a + 0.5, a + dw - 0.5, 9)[1:-1]:
            V4.line([(xx, 0), (xx, ht - SB_DOOR_GAP)], 'unk', lw=0.2, z=2.05)
    V4.dim((xw0, 0), (xw0 + Lr, 0), -4, f'{Lr:.0f} m roof (8 x 17.25) [obs] / outline {Lo} m [obs]', 'obs', fs=3.8)
    V4.text((xw0 + Lr / 2, -9), 'SUPERBAY, WNW (door) face, looking ESE', 'pub', fs=4.6, weight='bold', bg=False, color='#000000', style='normal')
    V4.leader((xw0 + 17.25 * 1.5, ht + SB_FOLD), -4, 24, 'folded roof: 8 bays of 17.25 m per side, each a light / shaded pair\n'
              '[obs NAIP, spec sb_roof_bays_obs]; fold amplitude drawn 1.5 m [unk];\nspine roof behind at +41.15 [pub DOF]', 'inf', fs=3.6)
    V4.leader((xw0 + Lr / 2, (ht - SB_DOOR_GAP) / 2), 22, 18, 'hangar doors on the WNW and ESE faces [obs NAIP: sunlit\n10-m ESE door band]; '
              'two door bays of ~67 m per side (four 747-size\nbays [pub]) [inf]; door head and leaf division [unk]', 'unk', fs=3.6)
    x = 252; W = MOC['moc_large_hangar']['min_rect']['length_m']
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
    S.note('Massing elevations: width = the long side of the outline\'s minimum rectangle (except: Garages A / G split into the garage '
           'body and the AirTrain guideway tail of their outlines; the RCC drawn on its west-face chord), height = the spec value with its '
           'tag; level lines only where a floor height is published, else dotted placeholders. Facade modules are not dimensioned.')
    S.note('Garages A / G: the roof deck is still unmeasured: drawn dotted at the NAIP drum-ring value (the ring is imaged with the same '
           'east lean as the deck edges, i.e. level with the deck), with every candidate on the range bar; the helix drum (outline arc) '
           'stands behind the SSE face; the 25-30 m AirTrain-photo reading stays DISPUTED. Grand Hyatt: no published height.')
    S.note('DOF points are drawn at their positions projected on the face drawn (u from the end named on the elevation); the RCC '
           '"TANK" is identified with the station stair / elevator tower only by inference [inf].')
    S.note('Photos (reference only, refs/cache/buildings/review_likeness): l4 Grand Hyatt east face (Gregory Varnum 2019), l5 RCC '
           'station (Pi.1415926535 2021), a2 aerial (Pi.1415926535 2025), l3 hangar (BrokenSphere 2009), all CC BY-SA.')
    return S.finish()
