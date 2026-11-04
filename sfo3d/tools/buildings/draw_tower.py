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


def hf(h, f):
    """spec station h (anchored at 67.36 m with D 14.3) -> height in family f."""
    return f['rim'] - (H_SPEC - h) * f['s']


def shaft_outline(f):
    """half-profile (r, h) of the round airside body of family f from the base-building roof to the flare top deck."""
    pts = [(PROF[0][1] * f['s'], f['ibf'])]                      # Famartin base width at the base-building roof
    pts += [(r * f['s'] / RAT, hf(h, f)) for h, r in PROF[1:]]    # A380 ratios (1.5 % correction)
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


def ibf_u_extent(right):
    ring = np.asarray(D.sfom('Air Traffic Control Tower')[0][0], float)
    u = (ring - AXIS) @ right
    return float(u.min()), float(u.max())


def cab_offset(right):
    """u offset of the cab centre from the shaft axis in a view with right-hand world vector `right` [inf]."""
    return float(np.dot(CAB - AXIS, right))


def draw_body(V, f, fill, uo):
    sh = shaft_outline(f); c = cab_outline(f)
    if fill:
        sil = [(-r, h) for r, h in sh] + [(r, h) for r, h in reversed(sh)]
        V.poly(sil, 'inf', fc='#e8edf2', z=3)
        gb, gt, rim = c['glass_bottom'], c['glass_top'], c['roof_rim']
        V.poly([(uo - gb[0], gb[1]), (uo + gb[0], gb[1]), (uo + gt[0], gt[1]), (uo - gt[0], gt[1])], 'inf', fc='#5f6d7a', z=4)
        V.poly([(uo - gt[0], gt[1]), (uo + gt[0], gt[1]), (uo + rim[0], rim[1]), (uo - rim[0], rim[1])], 'inf', fc='#f4f4f4', z=4)
    else:
        for s in (-1, 1):
            V.line([(s * r, h) for r, h in sh], 'inf', lw=0.75, z=5.5, ls=F2LS)
            V.line([(uo + s * c[k][0], c[k][1]) for k in ('glass_bottom', 'glass_top', 'roof_rim')], 'inf', lw=0.75, z=5.5, ls=F2LS)
        rim = c['roof_rim']; V.line([(uo - rim[0], rim[1]), (uo + rim[0], rim[1])], 'inf', lw=0.75, z=5.5, ls=F2LS)


def draw_blades(V, f, hb, ht, w0, w1):
    """landside glass ribbon in its channel between the NE blade (left, looking ESE) and the SW wing (right), family f.
    Form from photos t3 / t4 (Famartin 2025-08-12, CC BY-SA 4.0, oblique views from bearings 319 / 338) [obs, photo];
    proportions estimated from those oblique views (not dimensioned in any source) [inf]."""
    rim = cab_outline(f)['roof_rim'][1]; deck = hf(60.9, f)
    # ribbon (glass, LED-backlit) with its mullion grid: 2 columns, ~25 rows (photo count) [obs]
    V.poly([(-w0 / 2, hb), (w0 / 2, hb), (w1 / 2, ht), (-w1 / 2, ht)], 'obs', fc='#2b3d55', z=5)
    V.line([(0, hb), (0, ht)], 'obs', lw=0.35, z=5.2, color='#9fb3c8')
    for k in range(1, 25):
        h = hb + (ht - hb) * k / 25; w = w0 + (w1 - w0) * k / 25
        V.line([(-w / 2, h), (w / 2, h)], 'obs', lw=0.25, z=5.2, color='#9fb3c8')
    # NE blade: narrow, sharp-edged, a full-height strip beside the ribbon ending in a pointed tip at about the flare rim
    tip = deck + 1.2
    ne = [(-w0 / 2, hb), (-w0 / 2 - 1.0, hb), (-w1 / 2 - 1.8, ht), (-w1 / 2 - 1.0, tip), (-w1 / 2, ht)]
    V.poly(ne, 'inf', fc='#c9d2dc', z=5.1)
    V.line([(-w0 / 2 - 0.5, hb), (-w1 / 2 - 0.9, ht)], 'inf', lw=0.3, z=5.2)           # crease
    # SW wing: broad, horizontally louvred face, flat top, rounded outer edge, a crease diverging upwards
    wo = w1 / 2 + 5.5
    out = [(w0 / 2 + 1.4, hb)] + [(w0 / 2 + 1.4 + (wo - w0 / 2 - 1.4) * t ** 1.8, hb + (ht - 2.5 - hb) * t) for t in np.linspace(0.1, 1, 12)]
    arc = [(wo - 1.2 + 1.2 * np.cos(a), ht - 1.2 + 1.2 * np.sin(a)) for a in np.linspace(0, np.pi / 2, 6)]
    sw = [(w0 / 2, hb)] + out + arc + [(w1 / 2, ht)]
    V.poly(sw, 'inf', fc='#d6dde5', z=5.1)
    for k in range(1, 30):
        h = hb + (ht - hb) * k / 30
        xo = np.interp(h, [p[1] for p in out], [p[0] for p in out]); xi = w0 / 2 + (w1 - w0) / 2 * (h - hb) / (ht - hb)
        if xo > xi + 0.6: V.line([(xi + 0.2, h), (xo - 0.2, h)], 'inf', lw=0.18, z=5.2, color='#9aa7b4')
    V.line([(w0 / 2 + 0.7, hb), (w1 / 2 + 2.6, ht)], 'inf', lw=0.3, z=5.3)              # crease
    V.leader((-w1 / 2 - 1.0, tip), -30, 9, f'NE blade: narrow, sharp-edged; pointed tip at about the flare rim\n'
             f'(+{tip:.1f}; photos read 0-2.4 m above it) [obs photo t4, low]', 'inf', fs=4.0)
    V.leader((wo - 1.5, ht - 6), 22, 8, 'SW wing: broad blade, horizontally louvred face, flat top,\nrounded outer edge [obs photo t3 / t4];'
             ' width ~5.5 m beyond the\nribbon at the top [inf: oblique photo]; plan depth unknown [unk]', 'inf', fs=4.0)
    V.leader((0, (hb + ht) / 2 + 4), -30, 12, f'glass ribbon (LED-backlit, "waterfall"): 147 ft = {ht - hb:.2f} m tall [pub];\n'
             f'width {w0} -> {w1} m bottom -> top [obs, low; T2 AirTrain photo]; 2 columns x ~25 rows\n'
             '[obs photos]; set in a flat-faced channel between the two blades [obs photo];\n'
             'start / end levels not published: drawn from the base-building roof [inf]', 'obs', fs=4.0)
    V.text((0, ht + 2.2), 'ribbon head drawn level: in t4 the head and the mullion rows slope alike\n'
           '(0.18-0.19 px/px), so the slant seen there is perspective [obs photo]', 'obs', fs=3.6)
    V.dim((-w0 / 2, hb - 1.0), (w0 / 2, hb - 1.0), -2.5, f'{w0} [obs]', 'obs', fs=4.0)
    V.dim((-w1 / 2, ht + 0.4), (w1 / 2, ht + 0.4), 7.0, f'{w1} [obs]', 'obs', fs=4.0)


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
    c1 = cab_outline(F1); rim = c1['roof_rim'][1]
    mast = rim + (T['h_antenna_tips']['value'] - H_SPEC) * F1['s']
    for x in (-5.6, -2.0, 3.4, 6.0):
        V.line([(uo + x, rim), (uo + x, mast)], 'inf', lw=0.5, z=4)
    for h in T['h_seams']['value']:
        r = r_at(h, F1); V.line([(-r, hf(h, F1)), (r, hf(h, F1))], 'inf', lw=0.4, z=4)
    a, bq = (hf(x, F1) for x in T['h_upper_slots']['value'])
    ra, rb = r_at(T['h_upper_slots']['value'][0], F1), r_at(T['h_upper_slots']['value'][1], F1)
    if not ribbon:
        V.poly([(-ra, a), (ra, a), (rb, bq), (-rb, bq)], 'inf', fc='none', hatch='////', z=4)
        a2, b2 = (hf(x, F1) for x in T['h_lower_slot']['value'])
        V.poly([(0.6, a2), (1.6, a2), (3.4, b2), (2.4, b2)], 'inf', fc='#5f6d7a', z=4)
        V.leader((2.9, (a2 + b2) / 2 + 6), 14, 4, f'single inclined slot {a2:.1f}-{b2:.1f} m (F1)\non the airside face [inf, photos]', 'inf', fs=4.0)
    else:
        w0, w1 = T['ribbon_width']['value']; rh = T['ribbon_height']['value_m']
        draw_blades(V, F1, F1['ibf'], F1['ibf'] + rh, w0, w1)
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
        L = [(m, f'+{m:.1f} mast tips' + (' = 221 ft' if f is F2 else ' (232 ft)')), (c['roof_rim'][1], f'+{c["roof_rim"][1]:.2f} roof rim' + (' = 221 ft' if f is F1 else '')),
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
    V.text((sx + 10, 72.0), 'FAMILY 1 (filled, dashed): D 15.2, rim 67.36 = 221 ft', 'inf', fs=fsl + 0.4, ha='left', weight='bold')
    V.text((-sx - 10, 72.0), 'FAMILY 2 (dash-dot outline): D 14.5, rim 64.0, 221 ft at the masts', 'inf', fs=fsl + 0.4, ha='right', weight='bold')
    lv(F1, 'right'); lv(F2, 'left')
    V.text((0, -9.0), f'u = 0: shaft axis [inf] (-740.5, 324.5); cab drawn {uo:+.1f} m off the axis (cab centre (-739, 323.5): '
           'offset 1.5 m towards the airfield [inf, model_proposal])', 'inf', fs=3.8)


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
    sw = [base - sd * w1 / 2, AXIS + e * (R + 2.2) - sd * (w1 / 2 + 1.0), AXIS + e * (R + 2.6) - sd * (w1 / 2 + 3.5),
          AXIS + e * (R + 1.6) - sd * (w1 / 2 + 5.3), AXIS + e * np.sqrt(R ** 2 - (w1 / 2 + 5.8) ** 2) - sd * (w1 / 2 + 5.8)]
    V.poly(sw, 'unk', fc='#e4e4e4', z=5)
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
    V.poly([(-744, 321.5), (-734, 321.5), (-734, 325.5), (-744, 325.5)], 'inf', fc='none', z=4, lw=0.4)
    V.leader(CAB + np.array([5.0, -5.0]), 22, 40, f'cab-roof cap D {F1["D"]} (F1) / {F2["D"]} (F2) [inf];\nmeasured 14.3 +-1.0, EXIF 14.75 +-0.5 [obs]\n'
             'centre (-739, 323.5) [inf]: z 323.5 +-2 from four NAIP epochs [obs];\nx -739 +-5 [inf]; small box = the adopted tolerance', 'inf', fs=4.0)
    # x bounds: from the NAIP 2022 sensor field of view AND an assumed rim height -> one pair per family [inf]
    for x, s, ls, dy in ((-744.1, 'F1 (rim 67.36): x >= -744.1 hard', (0, (2, 2)), 0), (-739.6, 'F1: >= -739.6 likely', (0, (1, 2)), -4.5),
                         (-741.3, 'F2 (rim 63.3-64): x >= -741.3 hard', F2LS, -9.0), (-737.1, 'F2: >= -737.1 likely', (0, (1, 2, 4, 2)), -13.5)):
        V.line([(x, 296), (x, 352)], 'inf', lw=0.45, ls=ls)
        V.text((x - 0.4, 353.5 - dy), s, 'inf', fs=3.4, ha='right')
    V.leader((-741.3, 297.5), -4, -8, 'x bounds: NAIP 2022 sensor field of view (67.1 deg) for an ASSUMED rim height [inf]\n'
             '(spec x_bounds); under F2 the box west of -741.3 is excluded and -739 lies\nbelow the likely bound -737.1', 'inf', fs=3.6, ha='right')
    V.mark(DOF_TOWER, 'pub', marker='^', ms=4)
    V.mark(OEAAA_13, 'pub', marker='^', ms=3.4, fc='none')
    V.mark((-737.0, 324.9), 'pub', marker='^', ms=4, fc='none')
    V.leader(DOF_TOWER, -30, -30, 'FAA DOF 06-323169 = OE/AAA 2008 site 13: 245 ft AGL envelope, accuracy 4D (+-76 m) [pub];\n'
             f'filled = DOF convention WGS 84 ({DOF_TOWER[0]:.1f}, {DOF_TOWER[1]:.1f}), as on BI / BD / BL;\nhollow = the letter\'s NAD83 reading (-742.6, 335.7)', 'pub', fs=3.8)
    V.leader((-737.0, 324.9), 34, -6, 'OE/AAA site 13A (241 ft AGL; NAD83 position) [pub]', 'pub', fs=3.8)
    epochs = {'2016': (-752.75, 323.35), '2018': (-749.70, 323.20), '2022': (-698.75, 325.30), '2024': (-700.85, 322.40)}
    for y, p in epochs.items():
        V.mark(p, 'obs', marker='o', ms=2.6, fc='none')
        V.text(np.array(p) + np.array([0, -2.2 if y in ('2016', '2024') else 2.4]), y, 'obs', fs=3.4, bg=False)
    V.leader((-698.75, 325.3), 8, -22, 'cab roof as IMAGED by NAIP 2016 / 2018 / 2022 / 2024\n(relief displacement - not positions) [obs]:\nthe four epochs agree in z to +-1.2 m', 'obs', fs=3.8)
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
        V.circle(c1['predicted_imaged'], F1['D'] / 2, 'inf', z=7, lw=0.6)
        V.circle(c2['predicted_imaged'], F2['D'] / 2, 'inf', z=7, lw=0.6, ls=F2LS)
        V.leader(np.array(c1['predicted_imaged']) + [0, 7.2], 6, 40, f"predicted imaged cab roof (frame model): F1 {c1['predicted_imaged']}, F2 {c2['predicted_imaged']};\n"
                 f"NAIP 2024 disc centre {c1['observed_imaged']}: delta F1 {c1['delta']} / F2 {c2['delta']} m.\nINCONCLUSIVE: the predictions differ by "
                 f"{cc['_reading']['prediction_difference_m']} m, less than the input uncertainty\n(cab x +-5 m [inf]; flying-height sd -> +-3 m on the 37 m lean)", 'obs', fs=3.8)
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
    S.note('Settle with a surveyed ground photo (rim and grade), the NAIP shadow with the flight time, or an SFO / FAA elevation drawing.')
    S.note('Round airside body: radius = A380-photo width ratios / 1.015 (the verification found them ~1.5 % high) x D, so the flare is '
           '1.58 D = the dimensioned value. The cab is drawn on its inferred centre, 1.5 m from the axis towards the airfield [inf].')
    S.note('Landside (B): the ribbon sits in a flat-faced channel between a narrow, sharp NE blade (pointed tip at about the flare rim) and a '
           'broad, louvred SW wing with a rounded edge; both run full height with creases [obs, photos t3 / t4, Famartin 2025, CC BY-SA 4.0]. '
           'Their proportions are read from oblique photos [inf]; no source dimensions them.')
    S.note('Cab glazing: 24 panes of 6 x 11 ft [pub ENR] do not fit the drawn glass ring; glazed arc 220 / 235 / 270 deg [pub, conflict]. '
           'Cab-glass lean 20 +-4 deg out [obs]. Red obstruction light on the roof rim (SW) [obs, photo]; DOF lighting code R [pub].')
    S.note('Cladding: ~1,500 curved trapezoidal ACM panels (4-mm Alucobond Plus "SFO Silver") with spiralling joints [pub].')
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
    V.poly([(-11.5, fl - 0.4), (11.5, fl - 0.4), (11.5, fl), (-11.5, fl)], 'inf', fc='#999999', z=4)
    for s in (-1, 1):
        V.line([(uo + s * gb[0], gb[1]), (uo + s * gt[0], gt[1])], 'inf', lw=1.2, color='#46576a')
        V.line([(uo + s * gt[0], gt[1]), (uo + s * rim[0], rim[1])], 'inf', lw=0.9)
    V.poly([(uo - rim[0], rim[1] - 0.6), (uo + rim[0], rim[1] - 0.6), (uo + rim[0], rim[1]), (uo - rim[0], rim[1])], 'inf', fc='#999999', z=4)
    c2 = cab_outline(F2)
    for s in (-1, 1):
        V.line([(uo + s * c2[k][0], c2[k][1]) for k in ('glass_bottom', 'glass_top', 'roof_rim')], 'inf', lw=0.6, ls=F2LS)
    V.line([(uo - c2['roof_rim'][0], c2['roof_rim'][1]), (uo + c2['roof_rim'][0], c2['roof_rim'][1])], 'inf', lw=0.6, ls=F2LS)
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
           '(67.36 / 14.3 / 14.2) is inconsistent and not drawn. The cab is drawn 1.6 m NNE of the axis (its inferred centre) [inf].')
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
