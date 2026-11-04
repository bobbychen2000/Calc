"""Sheets of the domestic terminals (Harvey Milk Terminal 1 with Boarding Areas B / C, Terminal 2 with BA-D, Terminal 3
with BA-E / BA-F), drawn from tools/buildings/spec_domestic.json (verified 2026-11-04, docs/research/buildings_domestic.md
'Verification') and the two-epoch roof faces of tools/buildings/dom_heights.json:
  BD-01  plan 1:2500 (A1): SFO Museum level-2 outlines, measured lean-free roof edges, heights, DOF points + NAIP overlay
  BD-02  elevations (A1): pier cross-sections on a common datum 1:500, Terminal 3 West airside facade wall sections
         (published CDR, 95 % CD Oct 2023) 1:200
Heights are metres above the local apron (two-epoch NAIP method at the verified |s20| = 1.25; every value carries the
spec's range, -5 % / +5 % for the sun-path uncertainty).
"""
import numpy as np

import draw_data as D
from draw_lib import Sheet, FT, hdg_vec, unit
from draw_tower import draw_dev

DV = D.DV
PIERS = ['Boarding Area B', 'Boarding Area C', 'Boarding Area D', 'Boarding Area E', 'Boarding Area F']
HALLS = ['Harvey Milk Terminal 1', 'Terminal 2', 'Terminal 3']


def fmt_h(rec):
    r = rec.get('range')
    return f"{rec['value']:.2f} m" + (f" ({r[0]:.1f}-{r[1]:.1f})" if r else '')


def sheet_plan(variant='vector', dev=None):
    bg = variant != 'vector'
    S = Sheet('BD-01', 'Domestic terminals T1 / T2 / T3: plan with roof heights and measured roof edges', 'A1', variant=variant,
              subtitle='Spec: tools/buildings/spec_domestic.json + dom_heights.json; note docs/research/buildings_domestic.md (Verification)')
    V = S.view(0, 0, 560, S.vh, 2500, (-930, 335), kind='plan', title='1  PLAN (SFO Museum outlines = departure-level floor outlines, not roofs)')
    if bg: V.background()
    V.grid(100)
    for nm in ('International Terminal',):
        for r in D.outer_rings(nm, 'terminals'): V.ctx(r, fc='#f7f7f7' if not bg else 'none')
    for nm in ('Central Parking Garage', 'Air Traffic Control Tower'):
        for r in D.outer_rings(nm, 'structures'): V.ctx(r, fc='#f7f7f7' if not bg else 'none')
    for nm in HALLS:
        for poly in D.sfom(nm, 'terminals'):
            V.poly(poly[0], 'obs', fc='#efefef' if not bg else 'none', lw=0.5, z=1.5)
            for h in poly[1:]:
                V.poly(h, 'obs', fc='white' if not bg else 'none', lw=0.4, z=1.55)   # courtyards (holes)
    for nm in PIERS:
        for r in D.outer_rings(nm, 'boardingAreas'):
            V.poly(r, 'obs', fc='#e7eef6' if not bg else 'none', lw=0.6, z=2)
    # lean-free roof edges (obs)
    for sid, rid in (('bab.roof_edges', 'ba_b_south'), ('bad.roof_edges', 'ba_d_head'), ('baf.roof_edges', 'ba_f_ne_arm')):
        te = D.dom_true_edges(sid, rid)
        for k in ('n', 'm'):
            V.line(te[k], 'obs', lw=1.6, z=6)
    # BA-B raised central roof band (south half, approx) [inf]
    te = D.dom_true_edges('bab.roof_edges', 'ba_b_south')
    n_a, n_b = np.array(te['n']); m_a, m_b = np.array(te['m'])
    ti = unit(n_b - n_a); nn = np.array([-ti[1], ti[0]]); inward = unit((m_a + m_b) / 2 - (n_a + n_b) / 2)
    nn = nn if np.dot(nn, inward) > 0 else -nn
    band = [n_a + nn * 7.5, n_b + nn * 7.5]
    m2 = [m_b - nn * 14.0, m_a - nn * 14.0]
    V.poly([band[0], band[1], *sorted(m2, key=lambda p: np.dot(p - band[0], ti), reverse=True)], 'inf', fc='#f6e3cf' if not bg else 'none', z=5, lw=0.6)
    # labels: piers
    L = [((-905, 905), -40, 24, 'Boarding Area B (south half, t -1238..-1176):\nouter roof edges ' + fmt_h(DV['bab.h_roof']) + ' [obs]\n'
          'raised central roof ' + fmt_h(DV['bab.h_roof_central']) + ' [obs, low]\nlean-free edges (thick blue): ESE 2.3 m outside, WNW 1.7 m\n'
          'inside the level-2 outline; width 54.3 m [obs]; raised part\n~33 m wide (hatched, approx.) [inf]', 'obs'),
         ((-905, 600), -48, -2, 'BA-B north half: not measured; PV rows on the roof\n(1.0-1.2 MW, ~3,000 panels [pub]); landside roof wells [pub/obs]', 'obs'),
         ((-650, 410), 18, 22, 'Boarding Area C: roof edge ' + fmt_h(DV['bac.h_roof']) + '\n[obs, low: single face, assumed lean]', 'obs'),
         ((-520, 200), 14, 18, 'Boarding Area D head: ' + fmt_h(DV['bad.h_roof']) + ' [obs, low]\n(faces 118.7 m apart may be two roof levels)', 'obs'),
         ((-800, -40), 24, -10, 'Boarding Area E (north part, t -350..-310):\ntapered fascia ' + fmt_h(DV['bae.h_roof']) + ' [obs]', 'obs'),
         ((-1030, -185), -26, -24, 'Boarding Area F NE arm: ' + fmt_h(DV['baf.h_roof_ne_arm']) + ' [obs]\nFAA DOF 06-035331: 34 ft = 10.36 m [pub] (control)', 'obs')]
    for p, dx, dy, s, tg in L:
        V.leader(p, dx, dy, s, tg, fs=4.2)
    for nm, p, dx, dy in (('Harvey Milk Terminal 1 Center', (-860, 470), -52, 30), ('Terminal 2', (-820, 170), -40, 14), ('Terminal 3', (-950, 60), -44, 20)):
        txt = {'Harvey Milk Terminal 1 Center': 'T1 Center main hall: NO published or measured height [unk];\n3 skylights [pub] (blue squares: imaged positions, lean-affected) [obs];\n'
                                                'roof covered by radial PV rows [obs]',
               'Terminal 2': 'Terminal 2 hall: no published or measured height [unk];\nclerestories + skylights over the lobby [pub]',
               'Terminal 3': 'Terminal 3: CDR levels above L1 (datum unknown):\nR2 roof high point 14.48 m, R3 21.34 m [pub / inf];\nT3W under construction 2024-2029 [pub]'}[nm]
        V.leader(p, dx, dy, txt, 'unk' if nm != 'Terminal 3' else 'pub', fs=4.2)
    for p in ((-826, 460), (-815, 508), (-884, 530)):
        q = np.array(p); V.poly([q + [-4.5, -5.5], q + [4.5, -5.5], q + [4.5, 5.5], q + [-4.5, 5.5]], 'obs', fc='#cfe3f3', z=6, lw=0.4)
    V.poly([(-678, 412), (-672, 412), (-672, 418), (-678, 418)], 'obs', fc='#cfe3f3', z=6, lw=0.4)
    # DOF points
    dof = [((-1027.2, -211.2), '06-035331 34 ft: on the BA-F NE arm roof [pub]', 'pub', (-34, -6)),
           ((-1022.1, -243.8), '06-035332 16 ft: 9.2 m outside BA-F on the apron\n(bridge / apron object) - not BA-F [refuted]', 'unk', (-30, -14)),
           ((-486.9, 71.9), '06-035330 25 ft: 23.7 m outside BA-D [refuted as BA-D]', 'unk', (14, -10)),
           ((-482.1, 257.8), '06-035321 24 ft: 37.2 m outside BA-D [refuted]', 'unk', (16, 6)),
           ((-444.3, 194.0), '06-035320 25 ft: 31.8 m outside BA-D [refuted]', 'unk', (12, -2)),
           ((-881.4, 518.1), '06-035351 50 ft: OLD T1 center (demolished\n2019-23), 2013 survey - superseded', 'unk', (-30, 6))]
    for p, s, tg, (dx, dy) in dof:
        V.mark(p, tg, marker='^', ms=4.5)
        V.leader(p, dx, dy, 'FAA DOF ' + s, tg, fs=3.9)
    V.scalebar()
    rows = [('BA-B outer roof edges (south half)', fmt_h(DV['bab.h_roof']), 'obs', 'two-epoch NAIP 2020 / 2024, |s20| 1.25'),
            ('BA-B raised central roof', fmt_h(DV['bab.h_roof_central']), 'obs', 'parallax ratio + 2020 step shadow (low)'),
            ('BA-E tapered fascia (north)', fmt_h(DV['bae.h_roof']), 'obs', 'two-epoch'),
            ('BA-F NE arm', fmt_h(DV['baf.h_roof_ne_arm']), 'obs', 'two-epoch; DOF 06-035331 = 10.36 m [pub]'),
            ('BA-D head', fmt_h(DV['bad.h_roof']), 'obs', 'two-epoch, low (faces 118.7 m apart)'),
            ('BA-C east half', fmt_h(DV['bac.h_roof']), 'obs', 'single face, assumed lean 0.40 (low)'),
            ('Control: BA-A (ITB)', f"{DV['control.ba_a']['value']:.2f} m", 'obs', 'ITB research 17.9 m'),
            ('T1 Center / T2 halls', 'no height', 'unk', 'nothing published or measured'),
            ('T3 R2 / R3 roof high points', '14.48 / 21.34 m', 'inf', 'CDR 58\'-6" / 81\'-0" minus L1 11\'-0" [pub]; datum unknown'),
            ('The app (tools/build_terminal_parts.py)', 'piers 14.6 m', 'app', 'halls T1 20 / T2 19 / T3 21 m')]
    S.table(570, 300, 166, 'Domestic roof heights (above the apron)', rows, fs=3.9, col=(0.42, 0.24))
    S.note('SFO Museum boarding-area polygons are departure-level (sfo:level 2) floor outlines, verified on record 1947304261 (BA-B): they '
           'are not roof outlines. Measured lean-free roof edges overhang them by ~1.8-2.3 m on the airfield (ESE) faces and lie 1.3-1.7 m '
           'inside them on the WNW faces.')
    S.note('Heights scale with the 2020 sun (|s20| 1.25, range 1.19-1.31): x0.95-1.05. Measured stretches only (labels name them); other parts '
           'of the piers are unmeasured.')
    S.note('The T1 "70 ft skylight trusses / four 180 x 30 ft reflectors" belong to the ITB main hall (refuted for T1 in the verification).')
    S.note('BA-D DOF points 06-035320/21/30 lie 24-37 m outside the pier (DOF 1A = +-6 m): they are not BA-D; 06-035332 is an apron object.')
    if bg and dev:
        draw_dev(V, dev, tuple(PIERS + HALLS + [f'Boarding Area {x} (lean-free roof edge, {f})' for x in 'BDF' for f in ('ESE', 'WNW')]), label_min=99)
        S.note('Overlay: NAIP 2024 under the drawing. Dots: NAIP edge offset from the drawn outline at its predicted imaged position '
               '(roof edges at the pier height x the pier\'s two-epoch lean; facade bases on the west faces at grade); green <= 1 m, amber '
               '<= 2.5 m, red > 2.5 m. Roof offsets on the ESE faces are mostly the roof overhang beyond the level-2 outline.')
    return S.finish('NAIP 2024' if bg else 'none (vector)', fmt=('jpg',) if bg else ('svg', 'png'))


# ------------------------------------------------------------------------------------------------ elevations
def pier_section(V, x0, title, W, h, rng, tag='obs', step=None, note='', h2=None, rng2=None, Wc=None, offc=0.0):
    """schematic cross-section of a pier (looking along its axis): roof width W at height h; step = raised centre."""
    V.ax.fill_between([x0 - 4, x0 + W + 4], [-1.5, -1.5], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(x0 - 4, 0), (x0 + W + 4, 0)], 'pub', lw=0.7)
    if rng:
        V.ax.fill_between([x0, x0 + W], [rng[0]] * 2, [rng[1]] * 2, color='#cfe0f2', lw=0, zorder=1.2, alpha=0.8)
    V.poly([(x0, 0), (x0 + W, 0), (x0 + W, h), (x0, h)], tag, fc='#f4f7fb', z=2, lw=0.8)
    if step:
        a, b = x0 + step[0], x0 + step[0] + step[1]
        if rng2: V.ax.fill_between([a, b], [rng2[0]] * 2, [rng2[1]] * 2, color='#f3d9bf', lw=0, zorder=1.3, alpha=0.8)
        V.poly([(a, h), (b, h), (b, h2), (a, h2)], 'obs', fc='#f4f7fb', z=2.2, lw=0.8, ls=(0, (5, 2)))
        V.dim((a, h2), (b, h2), 3, f'~{step[1]:.0f} m raised part [inf, approx]', 'inf', fs=4.0)
        V.dim((x0, h), (a, h), 3, f'~{step[0]:.1f} [inf]', 'inf', fs=3.8)
        V.dim((b, h), (x0 + W, h), 3, f'~{W - step[0] - step[1]:.1f} [inf]', 'inf', fs=3.8)
        V.level(x0 + W + 1, h2, f'+{h2:.2f} ({rng2[0]:.1f}-{rng2[1]:.1f}) [obs, low]', 'obs', len_mm=3, fs=4.0, u_line=b)
        V.text(((a + b) / 2, (h + h2) / 2), 'clerestory\n(Low-E) [pub]', 'pub', fs=3.8)
    V.level(x0 + W + 1, h, f'+{h:.2f}' + (f' ({rng[0]:.1f}-{rng[1]:.1f})' if rng else '') + f' [{tag}]', tag, len_mm=3, fs=4.0, u_line=x0 + W)
    V.dim((x0, 0), (x0 + W, 0), -5, f'{W:.1f} m' + note, 'obs' if not Wc else Wc, fs=4.0)
    V.text((x0 + W / 2, -11), title, 'pub', fs=4.8, weight='bold', bg=False, color='#000000', style='normal')


def sheet_elev():
    S = Sheet('BD-02', 'Domestic terminals: pier cross-sections on a common datum and Terminal 3 West airside wall sections', 'A1',
              subtitle='Spec: tools/buildings/spec_domestic.json (heights obs; T3 levels / wall sections pub, CDR 95 % CD Oct 2023)')
    V = S.view(0, 420, S.vw, 150, 500, (175, 14), title='1  PIER CROSS-SECTIONS (looking along each pier axis), roof heights above the apron', kind='elev', frame=False)
    VD = S.view(0, 228, 330, 170, 500, (64, 14), title='1b  BOARDING AREA D HEAD (same datum)', kind='elev', frame=False)
    GAP = 28
    x = 0
    pier_section(V, x, 'BOARDING AREA B (south half)', 54.3, DV['bab.h_roof']['value'], DV['bab.h_roof']['range'], step=(7.5, 33.0),
                 h2=DV['bab.h_roof_central']['value'], rng2=DV['bab.h_roof_central']['range'], note=' outer roof edges [obs]')
    V.text((x + 27, 4.5), 'apron + concourse + mezzanine\n("two levels and a mezzanine") [pub];\nfloor heights not published [unk]', 'unk', fs=3.7)
    x += 54.3 + GAP
    pier_section(V, x, 'BOARDING AREA E (north part)', 42.9, DV['bae.h_roof']['value'], DV['bae.h_roof']['range'], note=' [inf: s-profiles + leans]', Wc='inf')
    V.text((x + 21, 4.5), 'tapered roof edge over\nclerestory glazing [pub IDA]', 'pub', fs=3.7)
    x += 42.9 + GAP
    pier_section(V, x, 'BOARDING AREA F (NE arm)', 27.0, DV['baf.h_roof_ne_arm']['value'], DV['baf.h_roof_ne_arm']['range'], note=' lean-free edges [obs]')
    V.mark((x + 13.5, 34 * FT), 'pub', marker='v', ms=4)
    V.text((x + 13.5, 34 * FT + 2.2), 'DOF 06-035331\n34 ft = 10.36 [pub]', 'pub', fs=3.7)
    pier_section(VD, 0, 'BOARDING AREA D (head)', 118.7, DV['bad.h_roof']['value'], DV['bad.h_roof']['range'], note=' between the measured faces [obs, low]')
    VD.text((59, 4.0), 'the two faces may belong to different roof levels\n[obs: parallax 0.5-7 m across the head]', 'unk', fs=3.7)
    VD.line([(-4, 14.6), (124, 14.6)], 'app', lw=0.6)
    VD.text((-3, 15.4), 'app today: 14.6 m', 'app', fs=4.0, ha='left')
    VD.scalebar(y_mm=4)
    x += 27.0 + GAP
    pier_section(V, x, 'BOARDING AREA C (east half)', 43.4, DV['bac.h_roof']['value'], DV['bac.h_roof']['range'], note=' level-2 outline [obs SFOM]')
    x += 43.4 + GAP
    pier_section(V, x, 'CONTROL: BOARDING AREA A (ITB)', 37.85, 17.9, [16.9, 18.8], note=' roof [obs ITB]')
    V.mark((x + 19, DV['control.ba_a']['value']), 'obs', marker='o', ms=3)
    V.text((x + 19, DV['control.ba_a']['value'] + 2.0), f"two-epoch control {DV['control.ba_a']['value']:.2f} [obs]", 'obs', fs=3.7)
    V.line([(-10, 14.6), (x + 50, 14.6)], 'app', lw=0.6)
    V.text((-9, 16.6), 'app today: every pier 14.6 m (tools/build_terminal_parts.py PIER_H)', 'app', fs=4.0, ha='left')
    V.scalebar(y_mm=4)
    # ---------- T3W wall sections
    V2 = S.view(0, 8, S.vw, 200, 200, (68, 9), title='2  TERMINAL 3 WEST: airside wall sections (CDR 95 % CD, Oct 2023) and T3 level datum', kind='elev', frame=False)
    ft = lambda f, i=0: (f + i / 12.0) * FT
    def wall(x0, w, lv, roof, top, label, top_lbl):
        V2.ax.fill_between([x0 - 2, x0 + w + 2], [-0.8, -0.8], [0, 0], color='#dddddd', lw=0, zorder=1)
        V2.poly([(x0, 0), (x0 + w, 0), (x0 + w, top), (x0, top)], 'pub', fc='#f6f6f6', z=2)
        for h, s in lv:
            V2.line([(x0 - 1.5, h), (x0 + w + 1.5, h)], 'pub', lw=0.5)
            V2.level(x0 + w + 1.5, h, s, 'pub', len_mm=3, fs=4.0)
        V2.line([(x0, roof), (x0 + w, roof)], 'inf', lw=0.6)
        V2.level(x0 + w + 1.5, roof, f'+{roof:.2f} roof (parapet minus screen) [inf]', 'inf', len_mm=3, fs=4.0)
        V2.level(x0 + w + 1.5, top, top_lbl, 'pub', len_mm=3, fs=4.0)
        V2.dim((x0, 0), (x0 + w, 0), -5, 'bay width not published (schematic) [unk]', 'unk', fs=3.8)
        V2.text((x0 + w / 2, -4.2), label, 'pub', fs=4.6, weight='bold', bg=False, color='#000000', style='normal')
    lvF = [(0.0, '+0.00 L1 arrivals'), (ft(16), "+4.88  16'-0\" L2 departures"), (ft(34), "+10.36  +18'-0\" international")]
    wall(0, 12, lvF, ft(56) - ft(3, 6), ft(56), 'FIELD WALL (CDR p.18)', "+17.07  56'-0\" top of parapet (3'-6\")")
    for y0 in (ft(16) + ft(2), ft(16) + ft(14)):
        V2.poly([(1.0, y0), (11.0, y0), (11.0, y0 + ft(10)), (1.0, y0 + ft(10))], 'inf', fc='#5f6d7a', z=3, lw=0.4)
    V2.text((6, ft(16) + ft(13)), "2'-0\" band", 'inf', fs=3.4, color='#ffffff', bg=False)
    V2.leader((11, ft(16) + ft(7)), 4, -26, "windows 10'-0\" x 2 with a 2'-0\" horizontal mullion band [pub];\nvertical position on the wall not dimensioned - placed at L2 [inf]", 'inf', fs=3.8)
    lvG = [(0.0, '+0.00 L1'), (ft(16, 9), "+5.11  16'-9\" L2"), (ft(16, 9) + ft(18), "+10.59  +18'-0\" L3")]
    wall(46, 12, lvG, ft(59, 7) - ft(8), ft(59, 7), 'GATEHOUSE WALL (CDR p.20)', "+18.16  59'-7\" top of the 8'-0\" penthouse screen")
    # T3 level datum column
    xd = 95
    V2.line([(xd, -0.5), (xd, ft(81) - ft(11) + 0.5)], 'pub', lw=0.8)
    for f, s in ((0, "L1 arrivals TOC 11'-0\" (T3W 10'-3\")"), (16, "L2 departures 27'-0\""), (31.5, "L2M mezzanine 42'-6\""), (34, "L3 FIS corridor 45'-0\""),
                 (47.5, "R2 top of roof, high pt 58'-6\""), (55.75, "T3W parapet 66'-0\" (from 10'-3\")"), (70, "R3 top of roof, high pt 81'-0\"")):
        V2.level(xd, f * FT, f'+{f * FT:.2f}  {s} [pub]', 'pub', len_mm=4, fs=4.0)
    V2.text((xd + 14, -4.2), 'T3 LEVEL DATUM (project elevations, 95 % CD)', 'pub', fs=4.6, weight='bold', bg=False, color='#000000', style='normal')
    V2.text((xd + 14, -7.0), 'heights above L1 [inf: subtraction]; datum of the project elevations not printed [unk]', 'inf', fs=3.8, bg=False)
    V2.scalebar(y_mm=4)
    rows = [('L1 -> L2 (field / gatehouse)', "16'-0\" / 16'-9\"", 'pub', 'CDR wall sections'),
            ('L2 -> L3 international', "18'-0\"", 'pub', 'CDR'),
            ('L1 -> parapet (field / gatehouse)', "56'-0\" / 59'-7\"", 'pub', "CDR; 22'-0\" = 10 + 10 + 2 is a sum, not printed"),
            ('Parapet / penthouse screen', "3'-6\" / 8'-0\"", 'pub', 'CDR'),
            ('Materials', 'ACM Whetstone Gray / Norfolk Gray, Focus Black', 'pub', 'CDR legend MP-50 / 51 / 52'),
            ('Glazing', 'electrochromic GL-50 + IGU', 'pub', 'CDR'),
            ('May 2026 change', '+1 airside storey (club L4, L5 MEP)', 'pub', 'CDR update 2026: owner to choose the state'),
            ('Apron vs L1', '~1-2 ft', 'inf', 'DOF ground 9-10 ft AMSL if the datum ~ AMSL [unverified]')]
    S.table(345, 398, 390, 'Terminal 3 West (under construction 2024-2029)', rows, fs=3.9, col=(0.34, 0.30))
    S.note('Pier sections are schematic boxes at the measured roof height and width; shaded bands = the spec range. Roof forms beyond what is '
           'listed (fascia depths, clerestory glazing heights, PV racks) are not measured.')
    S.note('BA-B step: lower band ~7.5 m (ESE) / ~14 m (WNW), raised part ~33 m (lean-corrected, approximate, south half only).')
    S.note('BA-E width 42.9 m is derived from the research s-profiles (fascia s -686.2, 2020; WNW roof edge s -726.5, 2024) with the solved '
           'leans [inf]; BA-C width is the level-2 outline.')
    return S.finish()
