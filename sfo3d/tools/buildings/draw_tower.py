"""Sheets of the SFO air traffic control tower (2016) and its base building, drawn from tools/buildings/spec_tower.json
(verified 2026-09-26, docs/research/buildings_tower.md section 12):
  BT-01  site / roof plan 1:500 (A3)              + overlay on NAIP 2024 (out/buildings/drawings/BT-01_naip.jpg)
  BT-02  elevations from the ESE (airside) and from the WNW (landside, glass ribbon) 1:400 (A2)
  BT-03  section through the shaft axis 1:400 (A3)
Heights: the spec's adopted set (rim 67.36 m = 221 ft, cab-roof D 14.3 m) is drawn solid; the verification (12.3) found it
inconsistent by ~3 m and named two self-consistent families; family 2 (D 14.5 m, rim 64.0 m, 221 ft to the mast tips)
is drawn dashed so both stay visible until a surveyed photo / drawing settles it.
"""
import numpy as np

import draw_data as D
from draw_lib import Sheet, hdg_vec, unit, FT

T = D.TV
H1, D1 = 67.36, 14.3                    # spec / family-1 anchor (rim, cab-roof diameter)
H2, D2 = 64.0, 14.5                     # family 2 (buildings_tower.md 12.3: D 14.3-14.75, rim 63-65)
S2 = D2 / D1
AXIS = np.array(T['position_shaft_axis']['value'], float)
CAB = np.array(T['position_cab_roof_centre']['value'], float)
MP = D.SPEC_T['model_proposal_provisional']
PROF = [(h, r) for h, r in MP['profile_r_of_h_m']]   # (h, r): round airside body; 60.9 / 61.0 = flare top deck


def fam2(h):
    return H2 - (H1 - h) * S2


def body_outline(fam=1):
    """closed half-profile list (r, h) of the round body from the base-building roof to the roof rim."""
    cab = MP['cab']
    pts = [(r, h) for h, r in PROF] + [(cab['glass_bottom'][1], cab['glass_bottom'][0]), (cab['glass_top'][1], cab['glass_top'][0]),
                                       (cab['roof_rim'][1], cab['roof_rim'][0])]
    if fam == 2:
        pts = [(r * S2, fam2(h)) for r, h in pts]
    return pts


def ibf_u_extent(right):
    ring = np.asarray(D.sfom('Air Traffic Control Tower')[0][0], float)
    u = (ring - AXIS) @ right
    return float(u.min()), float(u.max())


def draw_tower_elev(V, right, ribbon=False, label_side='right'):
    """elevation of the tower in view V: u = metres along `right` (world unit vector) from the shaft axis."""
    h_ibf = T['h_ibf_roof']['value']; lo, hi = T['h_ibf_roof']['range']
    u0, u1 = ibf_u_extent(right)
    # grade
    V.ax.fill_between([u0 - 14, u1 + 14], [-2.5, -2.5], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(u0 - 14, 0), (u1 + 14, 0)], 'pub', lw=0.8)
    # base building (3 storeys, roof 14.2 [inf], range band)
    V.ax.fill_between([u0, u1], [lo, lo], [hi, hi], color='#f3d9bf', lw=0, zorder=1.2, alpha=0.7)
    V.poly([(u0, 0), (u1, 0), (u1, h_ibf), (u0, h_ibf)], 'inf', fc='#f7f7f7', z=1.5)
    V.text(((u0 + u1) / 2 + 12 * np.sign(u0 + u1 + 1e-9), 6.0), 'base building (IBF)\n3 storeys [pub], ~44,000 sq ft [pub]\nfloor levels not published', 'pub', fs=4.0)
    V.dim((u0, 0), (u1, 0), -6, f'{u1 - u0:.2f} m  long face [obs SFOM footprint]', 'obs')
    # family 2 (dashed, behind)
    f2 = body_outline(2); f2 = [(r, h) for r, h in f2 if h >= 13.0]
    V.line([(-r, h) for r, h in f2], 'unk', lw=0.6, z=2)
    V.line([(r, h) for r, h in f2], 'unk', lw=0.6, z=2)
    rr, hh = f2[-1]; V.line([(-rr, hh), (rr, hh)], 'unk', lw=0.6, z=2)
    # spec body (solid) as a filled silhouette
    b = body_outline(1)
    sil = [(-r, h) for r, h in b] + [(r, h) for r, h in reversed(b)]
    V.poly(sil, 'inf', fc='#e8edf2', z=3)
    # cab glass band + fascia
    cab = MP['cab']
    gb, gt, rim = cab['glass_bottom'], cab['glass_top'], cab['roof_rim']
    V.poly([(-gb[1], gb[0]), (gb[1], gb[0]), (gt[1], gt[0]), (-gt[1], gt[0])], 'inf', fc='#5f6d7a', z=4)
    V.poly([(-gt[1], gt[0]), (gt[1], gt[0]), (rim[1], rim[0]), (-rim[1], rim[0])], 'inf', fc='#f4f4f4', z=4)
    # masts (count changes over time; 2-3 shown)
    for x in (-5.6, -2.0, 3.4, 6.0):
        V.line([(x, rim[0]), (x, T['h_antenna_tips']['value'])], 'inf', lw=0.5, z=4)
    # seams, slots
    for h in T['h_seams']['value']:
        r = np.interp(h, [p[0] for p in PROF], [p[1] for p in PROF])
        V.line([(-r, h), (r, h)], 'inf', lw=0.4, z=4)
    a, bq = T['h_upper_slots']['value']
    ra = np.interp(a, [p[0] for p in PROF], [p[1] for p in PROF]); rb = np.interp(bq, [p[0] for p in PROF], [p[1] for p in PROF])
    V.poly([(-ra, a), (ra, a), (rb, bq), (-rb, bq)], 'inf', fc='none', hatch='////', z=4)
    if not ribbon:
        a, bq = T['h_lower_slot']['value']
        V.poly([(0.6, a), (1.6, a), (3.4, bq), (2.4, bq)], 'inf', fc='#5f6d7a', z=4)
        V.leader((2.9, (a + bq) / 2 + 6), 14, 4, f'single inclined slot {a:.1f}-{bq:.1f} m\non the airside face [inf, photos]', 'inf', fs=4.0)
    # ribbon + fins on the landside face
    if ribbon:
        w0, w1 = T['ribbon_width']['value']; rh = T['ribbon_height']['value_m']
        hb, ht = h_ibf, h_ibf + rh
        V.poly([(-w0 / 2, hb), (w0 / 2, hb), (w1 / 2, ht), (-w1 / 2, ht)], 'obs', fc='#2b3d55', z=5)
        for s in (-1, 1):
            V.line([(s * (w0 / 2 + 1.2), hb), (s * (w1 / 2 + 1.6), ht), (s * (w1 / 2 + 2.6), 60.9)], 'unk', lw=0.6, z=5)
        V.line([(w1 / 2 + 2.6, 60.9), (w1 / 2 + 6.5, 62.4)], 'unk', lw=0.6, z=5)
        V.leader((w1 / 2 + 5.5, 62.0), 24, 9, 'prow of one fin above the flare [obs, photos];\nfin / blade plan geometry NOT known [unk]', 'unk', fs=4.0)
        V.leader((0, 30), -26, 10, f'glass ribbon (LED-backlit, "waterfall"): 147 ft = {rh:.2f} m tall [pub];\n'
                 f'width {w0} -> {w1} m bottom -> top [obs, low; T2 AirTrain photo];\nstart / end levels not published: drawn from the IBF roof [inf]',
                 'obs', fs=4.0)
        V.dim((-w0 / 2, hb - 1.0), (w0 / 2, hb - 1.0), -2.5, f'{w0} [obs]', 'obs', fs=4.0)
        V.dim((-w1 / 2, ht + 1.0), (w1 / 2, ht + 1.0), 3.0, f'{w1} [obs]', 'obs', fs=4.0)
    # diameters (obs) at their stations
    st = [('d_cab_roof', H1 + 0.2, 4.0), ('d_cab_glass_top', 64.7, None), ('d_cab_glass_bottom', 61.8, None),
          ('d_flare_max', 59.4, None), ('d_shaft_waist', T['h_narrowest']['value'], None), ('d_shaft_at_ibf_roof', h_ibf + 0.4, None)]
    fsd = 3.8 if V.scale >= 400 else 4.4
    for key, h, off in st:
        d = T[key]['value']; tol = T[key].get('tolerance_m')
        s = f'D {d:g}' + (f' +-{tol:g}' if tol else '') + ' m [obs]'
        if key in ('d_cab_glass_top', 'd_cab_glass_bottom'):
            V.dim((-d / 2, h), (d / 2, h), 0, s, 'obs', fs=fsd, ext=False, text_off=0.4 if key == 'd_cab_glass_top' else -0.4)
        else:
            V.dim((-d / 2, h), (d / 2, h), off if off else 0, s, 'obs', fs=fsd, ext=bool(off))
    # levels (right) and family-2 levels (left)
    sx = 13.5; fsl = 3.7 if V.scale >= 400 else 4.5
    lv = [(T['h_dof_envelope']['value_m'], '+74.68  245 ft AGL = FAA DOF / 2008 envelope [pub] - upper bound, not as-built', 'pub'),
          (T['h_antenna_tips']['value'], '+70.7 mast tips (70.3-71.2) [inf, photos]', 'inf'),
          (H1, '+67.36 roof rim = 221 ft [pub number; definition unverified] (63.0-67.6) [inf]', 'inf'),
          (64.7, '+64.7 cab glass head [inf]', 'inf'), (61.8, '+61.8 cab glass sill [inf]', 'inf'),
          (61.0, '+61.0 cab floor (sill band) [inf]', 'inf'), (59.4, '+59.4 flare, widest [inf]', 'inf'),
          (56.8, '+49.2-56.8 band of inclined slots (flare) [inf]', 'inf'),
          (44.3, '+44.3 seam [inf]', 'inf'), (29.5, '+29.5 seam [inf]', 'inf'), (T['h_narrowest']['value'], '+26.3 waist (24.5-28.0) [inf]', 'inf'),
          (h_ibf, f'+{h_ibf} base-building roof (12.7-16.5) [inf, NAIP ratio 0.20-0.21 x rim]', 'inf'),
          (T['h_roof_garden']['value'], '+12.5 roof garden (2,000 sq ft [pub]) [inf]', 'inf')]
    yprev = 1e9
    for h, s, tg in lv:
        y = min(h, yprev - V.mm(fsl * 0.55))
        V.level(sx, y, s, tg, len_mm=3, fs=fsl, u_line=max(u1, 12.0) if h < 20 else 12.0)
        yprev = y
    for h, s in ((fam2(H1), f'{fam2(H1):.1f} rim'), (fam2(H1) + 3.3, f'{fam2(H1) + 3.3:.1f} masts = 221 ft'), (fam2(59.4), f'{fam2(59.4):.1f} flare'),
                 (13.0, '13.0 IBF roof')):
        V.level(-12.0, h, 'family 2: ' + s, 'unk', side='left', len_mm=3, fs=fsl - 0.1)
    V.text((0, -9.0), 'u = 0: shaft axis [inf] (-740.5, 324.5); cab centred 1-3 m towards the airfield [inf] - not drawn', 'inf', fs=3.8)


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
        L = float(np.hypot(*(q - p)))
        V.dim(p, q, 5, f'{L:.2f} [obs]', 'obs', fs=4.2)
    V.leader((-752, 340), -40, 4, 'base building (IBF): footprint = SFO Museum atc ring [obs]\n44.95 x 27.20 m, long axis 27.7 deg [obs]\n'
             'roof +14.2 (12.7-16.5) [inf]; 3 storeys [pub]', 'obs', fs=4.0)
    # shaft circles at the inferred axis
    for key in ('d_flare_max', 'd_shaft_at_ibf_roof', 'd_shaft_waist'):
        V.circle(AXIS, T[key]['value'] / 2, 'inf', z=4, lw=0.5)
    V.leader(AXIS + np.array([-11.3, 0]), -32, 26, 'flared shaft top D 22.6 +-1.5 m at +59.4 [obs];\nshaft D 10.3 at the IBF roof, waist D 9.8 [obs];\n'
             'circles centred on the inferred axis (-740.5, 324.5) [inf]', 'inf', fs=4.0)
    V.circle(CAB, D1 / 2, 'inf', z=5, lw=0.9)
    V.mark(CAB, 'inf', marker='+', ms=6)
    V.mark(AXIS, 'inf', marker='x', ms=4)
    V.poly([(-744, 321.5), (-734, 321.5), (-734, 325.5), (-744, 325.5)], 'inf', fc='none', z=4, lw=0.4)
    V.leader(CAB + np.array([5.0, -5.0]), 22, 40, 'cab-roof cap D 14.3 +-1.0 m [obs] (family 2: 14.5)\ncentre (-739, 323.5) [inf]:\n'
             'z 323.5 +-2 from four NAIP epochs [obs]; x -739 +-5 [inf]\n(hard bound x >= -744.1: NAIP 2022 sensor field of view);\n'
             'small box = the adopted tolerance', 'inf', fs=4.0)
    V.line([(-744.1, 296), (-744.1, 352)], 'obs', lw=0.4, ls=(0, (2, 2)))
    V.text((-744.6, 294.5), 'x = -744.1 hard minimum [obs]', 'obs', fs=3.6, ha='right')
    for b in (300, 320):
        V.line([AXIS, AXIS + hdg_vec(b) * 30], 'obs', lw=0.4, ls=(0, (3, 2)))
    V.text(AXIS + hdg_vec(310) * 34, 'glass ribbon faces\n~300-320 deg [obs, photos];\nfin plan unknown [unk]', 'obs', fs=3.8)
    V.mark((-742.6, 335.7), 'pub', marker='^', ms=4)
    V.mark((-737.0, 324.9), 'pub', marker='^', ms=4)
    V.leader((-742.6, 335.7), -30, -30, 'OE/AAA 2008 site 13 = FAA DOF 06-323169:\n245 ft AGL envelope, accuracy 4D (+-76 m) [pub]', 'pub', fs=3.8)
    V.leader((-737.0, 324.9), 34, -6, 'OE/AAA site 13A (241 ft AGL) [pub]', 'pub', fs=3.8)
    epochs = {'2016': (-752.75, 323.35), '2018': (-749.70, 323.20), '2022': (-698.75, 325.30), '2024': (-700.85, 322.40)}
    for y, p in epochs.items():
        V.mark(p, 'obs', marker='o', ms=2.6, fc='none')
        V.text(np.array(p) + np.array([0, -2.2 if y in ('2016', '2024') else 2.4]), y, 'obs', fs=3.4, bg=False)
    V.leader((-698.75, 325.3), 8, -22, 'cab roof as IMAGED by NAIP 2016 / 2018 / 2022 / 2024\n(relief displacement - not positions) [obs]:\nthe four epochs agree in z to +-1.2 m', 'obs', fs=3.8)
    A = D.app_tower()
    V.mark(A['centre'], 'app', marker='x', ms=4)
    V.circle(A['cab_centre'], A['cab']['roof'][1][0], 'app', z=6, lw=0.6)
    V.leader(A['centre'] + np.array([0, 10.16]), 26, -30, 'app today (js/live/terminals.js buildTower): shaft at the\nfootprint centroid (-740.9, 331.7), 7.2 m S of the spec\naxis; cab-roof D 20.3 m (spec 14.3)', 'app', fs=3.8)
    V.leader(ring[1] + np.array([3, -3]), -22, -16, 'roof garden 2,000 sq ft [pub], "SW side",\n+12.5 [inf]; outline not measured', 'inf', fs=3.8)
    V.scalebar()
    S.note('Positions: world frame ltp-nad83-2011. The tower axis and cab x are NOT surveyed; NAIP roofs lean 38-40 m east at the cab '
           '(relief displacement), so x rests on bounds (spec position_cab_roof_centre, x_bounds).')
    S.note('Footprint = SFO Museum atc ring (data/sfo_airport.json); its accuracy against a lean-free survey is unknown (+-1.5-5 m).')
    S.note('The T1-T2 connectors (one with a 35-ft glass ceiling [pub]) are part of the base building; their plan is not in any source found.')
    if variant != 'vector' and dev:
        draw_dev(V, dev, ('Tower base building (IBF)',))
        cc = dev['tower_cab_check']
        for fam, c in cc.items():
            V.circle(c['predicted_imaged'], D1 / 2 if '1' in fam else D2 / 2, 'inf' if '1' in fam else 'unk', z=7, lw=0.6)
        c1 = cc['spec / family 1 (rim 67.36 m)']; c2 = cc['family 2 (rim 64.0 m)']
        V.leader(np.array(c1['predicted_imaged']) + [0, 7.2], 6, 40, f"predicted imaged cab roof (frame model, rim 67.36): {c1['predicted_imaged']};\n"
                 f"NAIP 2024 disc centre {c1['observed_imaged']}: delta {c1['delta']} m;\nfamily 2 (rim 64.0): delta {c2['delta']} m - "
                 "the cab x is itself +-5 m [inf]", 'obs', fs=3.8)
        S.note('Overlay: NAIP 2024 (2024-05-20) under the drawing. Dots = measured offset of the NAIP edge from the drawn edge at its PREDICTED '
               'imaged position (roof edges displaced by h x (P - N)/(H - h), frame model on FAA DOF poles); green <= 1 m, amber <= 2.5 m, '
               'red > 2.5 m, hollow grey = weak edge. Numbers: docs/drawings/buildings/deviations.json.')
    return S.finish('NAIP 2024' if variant != 'vector' else 'none (vector)', fmt=('svg', 'png') if variant == 'vector' else ('jpg',))


def sheet_elev():
    S = Sheet('BT-02', 'Air traffic control tower: elevations from the ESE (airside) and the WNW (landside)', 'A1',
              subtitle='Spec: tools/buildings/spec_tower.json (heights inherit h_roof_top: the two families of 12.3)')
    w, h = (S.vw - 14) / 2, S.vh - 16
    right_ese = hdg_vec(27.7)        # looking WNW (297.7): right hand = NNE
    right_wnw = hdg_vec(207.7)       # looking ESE (117.7): right hand = SSW
    c1 = sum(ibf_u_extent(right_ese)) / 2 + 12.5; c2 = sum(ibf_u_extent(right_wnw)) / 2 + 12.5
    V1 = S.view(0, 12, w, h, 200, (c1, 37), title='A  ELEVATION FROM THE ESE (airside), looking WNW', kind='elev', frame=False)
    draw_tower_elev(V1, right_ese, ribbon=False)
    V2 = S.view(w + 14, 12, w, h, 200, (c2, 37), title='B  ELEVATION FROM THE WNW (landside), looking ESE - glass ribbon', kind='elev', frame=False)
    draw_tower_elev(V2, right_wnw, ribbon=True)
    for V in (V1, V2): V.scalebar(y_mm=6)
    S.note('Solid silhouette = the spec values: stations from photos scaled by the cab-roof diameter D 14.3 m and anchored at the roof rim '
           '67.36 m (221 ft). The verification (buildings_tower.md 12.3) shows this set is ~3 m inconsistent: either D ~15.2 m with the rim at '
           '221 ft (family 1), or D ~14.3-14.75 m with the rim at 63-65 m and 221 ft at the mast tips (family 2).')
    S.note('Grey dotted = family 2 drawn with D 14.5 m, rim 64.0 m (every station = 64.0 - (67.36 - h) x 14.5/14.3). Settle with a surveyed '
           'ground photo (rim and grade), the NAIP shadow with the flight time, or an SFO / FAA elevation drawing.')
    S.note('Round airside body only: radius profile = A380-photo width ratios x D (shaft_profile_ratio_A380, ~1.5 % high per the verification). '
           'The landside fins / prow and the cab offset (1-3 m towards the airfield) are not dimensioned in any source.')
    S.note('Cab glazing: 24 panes of 6 x 11 ft [pub ENR] do not fit the drawn glass ring; glazed arc 220 / 235 / 270 deg [pub, conflict]. '
           'Cab-glass lean 20 +-4 deg out [obs]. Red obstruction light on the roof rim (SW) [obs, photo]; DOF lighting code R [pub].')
    S.note('Cladding: ~1,500 curved trapezoidal ACM panels (4-mm Alucobond Plus "SFO Silver") with spiralling joints [pub].')
    return S.finish()


def sheet_section():
    S = Sheet('BT-03', 'Air traffic control tower: section through the shaft axis (NNE-SSW), looking WNW', 'A3',
              subtitle='Spec: tools/buildings/spec_tower.json (structure items are published text; most dimensions are not)')
    V = S.view(0, 12, S.vw, S.vh - 14, 400, (4, 34.0), kind='elev', frame=False)
    right = hdg_vec(27.7)
    u0, u1 = ibf_u_extent(right)
    h_ibf = T['h_ibf_roof']['value']
    V.ax.fill_between([u0 - 10, u1 + 10], [-6, -6], [0, 0], color='#e6e6e6', lw=0, zorder=1)
    V.line([(u0 - 10, 0), (u1 + 10, 0)], 'pub', lw=0.8)
    mat = 7 * FT
    V.poly([(-14, 0), (14, 0), (14, -mat), (-14, -mat)], 'unk', fc='#d0d0d0', hatch='xxxx', z=2)
    V.leader((10, -mat / 2), 14, -3, f'mat 7 ft = {mat:.2f} m thick [pub ENR]; plan extent unknown [unk];\n213 piles 140 ft (ENR) / 125 ft to bedrock (STRUCTURE) [pub, conflict]', 'pub', fs=3.8)
    # IBF cut: walls + roof slab; three storeys (levels unknown)
    for x in (u0, u1):
        V.poly([(x - 0.15, 0), (x + 0.15, 0), (x + 0.15, h_ibf), (x - 0.15, h_ibf)], 'inf', fc='#999999', z=3)
    V.poly([(u0, h_ibf - 0.5), (u1, h_ibf - 0.5), (u1, h_ibf), (u0, h_ibf)], 'inf', fc='#999999', z=3)
    for k in (1, 2):
        V.line([(u0, h_ibf * k / 3), (u1, h_ibf * k / 3)], 'unk', lw=0.5)
    V.text(((u0 + u1) / 2 - 9, h_ibf * 0.5), 'base building: 3 storeys [pub]\nfloor levels unknown (dotted = equal\nthirds, placeholder only) [unk]', 'unk', fs=3.8)
    # shaft: outer profile (cut) and the core inside
    prof = body_outline(1)
    left = [(-r, h) for r, h in prof]; rt = [(r, h) for r, h in prof]
    V.line(left, 'inf', lw=1.0); V.line(rt, 'inf', lw=1.0)
    V.line([(-r * S2, fam2(h)) for r, h in prof if fam2(h) > 13], 'unk', lw=0.5)
    V.line([(r * S2, fam2(h)) for r, h in prof if fam2(h) > 13], 'unk', lw=0.5)
    cr = 3.6
    for s in (-1, 1):
        V.line([(s * cr, -mat), (s * cr, 61.0)], 'unk', lw=0.6)
    V.leader((cr, 36), 16, 6, 'concrete core: slip-formed cylinder, unbonded vertical PT\n(26 tendon bundles) [pub]; wall 30 in -> 18 in [snippet,\nunverified]; DIAMETER NOT PUBLISHED - dotted placeholder [unk]', 'unk', fs=3.8)
    V.leader((-9.0, 54), -14, 4, 'steel-framed flare and cab cantilever\nfrom the core [pub]; cladding outline [inf]', 'inf', fs=3.8)
    # cab: floor, glass, roof, centre column (snippet)
    cab = MP['cab']; gb, gt, rim = cab['glass_bottom'], cab['glass_top'], cab['roof_rim']
    V.poly([(-11.0, 60.6), (11.0, 60.6), (11.0, 61.0), (-11.0, 61.0)], 'inf', fc='#999999', z=4)
    for s in (-1, 1):
        V.line([(s * gb[1], gb[0]), (s * gt[1], gt[0])], 'inf', lw=1.2, color='#46576a')
        V.line([(s * gt[1], gt[0]), (s * rim[1], rim[0])], 'inf', lw=0.9)
    V.poly([(-rim[1], rim[0] - 0.6), (rim[1], rim[0] - 0.6), (rim[1], rim[0]), (-rim[1], rim[0])], 'inf', fc='#999999', z=4)
    V.line([(0, 61.0), (0, rim[0] - 0.6)], 'unk', lw=0.8)
    V.leader((0, 65.6), -20, 6, 'cab roof cantilevered from a 2\'-2" x 3\'-4" centre column\n[snippet, unverified]; 13 positions [snippet]; 650 sq ft [pub]', 'unk', fs=3.8)
    V.leader((gt[1] - 0.4, 63.2), 16, 2, 'frameless laminated glass, leaning out\n20 +-4 deg [obs]; 2 tuned mass dampers\nnear the cab [pub], position unknown', 'inf', fs=3.8)
    for h, s, tg in ((rim[0], '+67.36 rim (63.0-67.6) [inf]', 'inf'), (gt[0], '+64.7 glass head [inf]', 'inf'), (gb[0], '+61.8 glass sill [inf]', 'inf'),
                     (61.0, '+61.0 cab floor [inf]; "200-ft concrete core" = 60.96 [snippet]', 'inf'), (59.4, '+59.4 flare widest [inf]', 'inf'),
                     (h_ibf, '+14.2 IBF roof (12.7-16.5) [inf]', 'inf'), (0.0, '+0.0 grade (site 13 ft AMSL [pub OE/AAA])', 'pub')):
        V.level(13.0 if h > 20 else u1, h, s, tg, len_mm=4, fs=3.6)
    V.dim((-24, 0), (-24, rim[0]), 0, f'{rim[0]:.2f} m = 221 ft [pub; definition unverified]', 'inf', fs=3.8)
    V.dim((-30, 0), (-30, fam2(H1)), 0, f'family 2: {fam2(H1):.1f} m rim, 221 ft at the masts', 'unk', fs=3.8)
    V.scalebar(y_mm=4)
    S.note('Cut through the shaft axis along the base building\'s long axis (27.7 deg). The section shows what is published as text '
           '(core type, mat, steel flare and cab, TMDs); no structural drawing was found, so wall thicknesses, core diameter, floor levels '
           'and the elevator / stair core are placeholders.')
    S.note('Outer profile as BT-02 (spec values solid, family 2 dotted).')
    return S.finish()


# ------------------------------------------------------------------------------------------------ deviation dots
DEVC = {'g': '#1a9850', 'a': '#f4a300', 'r': '#d73027', 'w': '#9e9e9e'}


def draw_dev(V, dev, buildings, label_min=2.5):
    for e in dev['edges']:
        if e['building'] not in buildings: continue
        a = np.array(e['p0']) + e['shift']; b = np.array(e['p1']) + e['shift']; n = np.array(e['n'])
        mid = (a + b) / 2
        col = DEVC['w'] if not e['ok'] else DEVC['g'] if abs(e['o']) <= 1 else DEVC['a'] if abs(e['o']) <= 2.5 else DEVC['r']
        if e['kind'] != 'base':
            V.line([a, b], 'inf', lw=0.5, color='#ffe082' if e['kind'] == 'roof' else '#80deea', ls=(0, (3, 2)))
        f0, f1 = a + n * e['o'], b + n * e['o']
        V.line([f0, f1], 'obs', lw=0.9, color=col)
        q = V.P(mid + n * e['o'])
        V.ax.plot([q[0]], [q[1]], 'o', ms=2.2, mfc=col if e['ok'] else 'none', mec=col, mew=0.5, zorder=12)
        if e['ok'] and abs(e['o']) > label_min:
            V.text(mid + n * (e['o'] + 2.0 * V.m * 3), f"{e['o']:+.1f}", 'obs', fs=3.4, color=col, z=13)
