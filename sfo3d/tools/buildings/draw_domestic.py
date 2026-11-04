"""Sheets of the domestic terminals (Harvey Milk Terminal 1 with Boarding Areas B / C, Terminal 2 with BA-D, Terminal 3
with BA-E / BA-F), drawn from tools/buildings/spec_domestic.json (verified 2026-11-04, docs/research/buildings_domestic.md
'Verification') and the two-epoch roof faces of tools/buildings/dom_heights.json:
  BD-01  plan 1:2500 (A1): SFO Museum level-2 outlines, measured lean-free roof edges, heights, DOF points + NAIP overlay
  BD-02  elevations (A1): pier cross-sections on a common datum 1:500, Terminal 3 West airside facade wall sections
         (published CDR, 95 % CD Oct 2023) 1:200
  BD-03  landside (curb) elevations (A1): T1 Center 1:400, Terminal 2 1:200, Terminal 3 1:400
Review backlog round (2026-11-04, docs/drawings/buildings/review_backlog.json groups.domestic): r1-23 BA-B raised centre along
the whole straight pier (dom_bab_band.py -> dom_bab_band.json); r1-22 BA-F hub faces / lantern (dom_baf_hub.py ->
dom_baf_hub.json); r1-34 Terminal 3 landside elevation (BD-03 view 3).
Heights are metres above the local apron (two-epoch NAIP method at the verified |s20| = 1.25; every value carries the
spec's range, -5 % / +5 % for the sun-path uncertainty).
"""
import numpy as np

import draw_data as D
from draw_lib import Sheet, FT, hdg_vec, unit, st2w
from draw_tower import draw_dev

DV = D.DV
PIERS = ['Boarding Area B', 'Boarding Area C', 'Boarding Area D', 'Boarding Area E', 'Boarding Area F']
HALLS = ['Harvey Milk Terminal 1', 'Terminal 2', 'Terminal 3']

# ---- BA-D head roof features (NAIP 2024, imaged; measured 2026-11-04 for the drawings) [obs]
# two drums: imaged roof circles (white rim, dark crescent = the drum's west wall seen obliquely, ~2.5-3 m wide)
BAD_DRUMS_IMG = [((-535.3, 97.8), 9.6), ((-509.5, 187.6), 9.6)]     # centre (x, z), radius; +-1 m
BAD_DRUM_RISE = 4.7          # crescent ~2.75 m / BA-D lean 0.58 m/m -> ~4-5 m above the adjacent roof [obs, low]
BAD_DRUM_TOP = 8.49 + BAD_DRUM_RISE    # [inf]: adjacent roof = bad.h_roof (the head is not one level)
BAD_LINES_IMG = [((-540, 110), (-559, 150)), ((-554, 137), (-527, 128)), ((-540, 110), (-505, 118))]   # roof-plane edges / skylights
# ---- BA-F hub: regular octagon fitted to the SFO Museum level-2 outline (5 edges, residual 0.01 m) [obs]
BAF_HUB_C, BAF_HUB_APO = np.array([-1069.36, -125.93]), 37.10      # edges parallel to the s / t grid and the diagonals
BAF_LANTERN_APO = (9.7, 6.7)          # concentric octagonal rings 19.4 / 13.4 m across (NAIP profiles on 4 axes) [obs]
BAF_LANTERN_IMG = np.array([-1061.3, -125.7])                      # imaged ring centre: 8.1 m E of the hub centre [obs]
BAF_MONITOR_IMG = dict(a=(-1290.0, -243.0), b=(-1100.0, -158.0), s=(12.0, 190.0), d=(-6.5, 1.5))   # NW-arm light strip, imaged


def octagon(c, apo, n0=343.0):
    """regular octagon with edge normals at headings n0 + 45 k (world x, z)."""
    R = apo / np.cos(np.radians(22.5))
    return [np.asarray(c) + hdg_vec(n0 + 22.5 + 45 * k) * R for k in range(8)]


def baf_monitor(shift):
    M = BAF_MONITOR_IMG; a, b = np.array(M['a']), np.array(M['b']); t = unit(b - a); n = np.array([t[1], -t[0]])
    s0, s1 = M['s']; d0, d1 = M['d']
    return [a + t * s + n * d + shift for s, d in ((s0, d0), (s1, d0), (s1, d1), (s0, d1))]


import os  # noqa: E402
# measurement records (numbers only, committed); tolerated missing so that dom_baf_hub.py (which imports the BA-F constants
# above) can regenerate its own record on a fresh checkout
BB = D._j(D.TB, 'dom_bab_band.json') if os.path.exists(os.path.join(D.TB, 'dom_bab_band.json')) else None   # BA-B raised centre (dom_bab_band.py, r1-23) [obs]
BH = D._j(D.TB, 'dom_baf_hub.json') if os.path.exists(os.path.join(D.TB, 'dom_baf_hub.json')) else None     # BA-F hub / lantern (dom_baf_hub.py, r1-22) [obs]
BAB_OUTER_S = (-383.73, -438.04)         # BA-B lean-free outer roof edges, airport-grid s (bab.roof_edges, south half) [obs]


def bab_band():
    """(s ESE edge, s WNW edge, t south end, t north end, (t0, t1) of the measured WNW edge) of the raised centre."""
    w = BB['wnw_edge']['t_range']
    return (BB['ese_edge']['s_lean_free'], BB['wnw_edge']['s_lean_free'], BB['extent']['t_south'], BB['extent']['t_north'],
            (w[0] - 5.0, w[1] + 5.0))


def baf_lantern_centre():
    """lean-free lantern centre [inf]: the imaged ring moved back by the relief of the hub roof (fit, east lean) + half of the
    2020-shadow bound on its rise; the hub-face fit puts the hub edge on the octagon, so the ring is eccentric."""
    f = BH['fits']['east']; rise = 0.5 * BH['ring_2020_shadow']['rise_upper_bound']
    return np.array(BAF_LANTERN_IMG) - np.array(f['lean_per_m']) * (f['h'] + rise)


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
    # BA-B raised central roof band along the WHOLE pier (review r1-23; tools/buildings/dom_bab_band.py): extent = the 2020
    # step shadow on the lower ESE band (t_south..t_north) [obs]; ESE edge lean-free from the 2020 imaged edge [obs]; WNW edge
    # from the 2024 wall band where the roof wells lie below it (north half) [obs], carried south [inf]
    s_e, s_w, t_s, t_n, t_w = bab_band()
    V.poly([st2w(s_e, t_s), st2w(s_e, t_n), st2w(s_w, t_n), st2w(s_w, t_s)], 'inf', fc='#f6e3cf' if not bg else 'none', z=5, lw=0.5)
    V.line([st2w(s_e, t_s), st2w(s_e, t_n)], 'obs', lw=0.9, z=5.6)
    V.line([st2w(s_w, t_w[0]), st2w(s_w, t_w[1])], 'obs', lw=0.9, z=5.6)
    # BA-B roof features along the whole pier (NAIP 2024, by eye, tools/buildings/dom_bab_roof.json) moved back by the relief of
    # the outer roof [obs positions, inf height]
    BR = D._j(D.TB, 'dom_bab_roof.json')['manual']
    lvB, hB, _ = D.dom_lean('B'); shB = -lvB * hB
    from shapely.geometry import Polygon as SP
    roofB = max((SP(r) for r in D.outer_rings('Boarding Area B', 'boardingAreas')), key=lambda g: g.area).buffer(2.5, join_style=2)

    def onroof(r):   # clip a feature to the roof (level-2 outline + 2.5 m: the measured ESE overhang is 2.3 m) [inf]
        g = SP(np.asarray(r) + shB).intersection(roofB)
        gs = [g] if g.geom_type == 'Polygon' else [x for x in getattr(g, 'geoms', []) if x.geom_type == 'Polygon']
        return [np.asarray(x.exterior.coords[:-1]) for x in gs if x.area > 5]
    for r in BR['pv_fields']:
        for q in onroof(r): V.poly(q, 'obs', fc='none', z=5.2, lw=0.4, hatch='||||||', ec='#5a7da0')
    for r in BR['wells']:
        for q in onroof(r): V.poly(q, 'obs', fc='#d7ead0' if not bg else 'none', z=5.3, lw=0.6)
    for r in BR['bridges']:
        for q in onroof(r): V.poly(q, 'obs', fc='white' if not bg else 'none', z=5.35, lw=0.5)
    for r in BR['skylight_grids']:
        for q in onroof(r): V.poly(q, 'obs', fc='#cfe3f3' if not bg else 'none', z=5.3, lw=0.5, hatch='++')
    V.leader(np.mean(BR['wells'][1], 0) + shB, -44, 6, 'BA-B roof (NAIP 2024, by eye +-3 m [obs]; moved back by the 13.1 m outer-roof\n'
             f'relief, {np.hypot(*shB):.1f} m W [inf]): three planted sunken roof wells on the WNW side\n(green; "roof wells" [pub CDR 2016]) '
             'crossed by two bridges (white; they continue W\noff the roof - walkway links?) [obs]; two skylight grids (blue,\ncross-hatched); PV row fields '
             '(hatched; 1.0-1.2 MW, ~3,000 panels [pub];\nrows ~5.5 m at ~9 m pitch [obs]); all clipped to the roof (outline\n+2.5 m) [inf]; '
             'heights of the wells, bridges and skylights\nnot measured [unk]', 'obs', fs=4.0)
    # BA-D head: drums and roof-plane / skylight lines (imaged; moved back by the relief of an assumed height) [obs / inf]
    lvD = D.dom_lean('D')[0]
    for c, r in BAD_DRUMS_IMG:
        V.circle(c, r, 'obs', z=6, lw=0.35, ls=(0, (1, 1.2)))
        V.circle(np.array(c) - lvD * BAD_DRUM_TOP, r, 'inf', z=6, lw=0.7, fc='#f6e3cf' if not bg else 'none')
    for p, q in BAD_LINES_IMG:
        V.line([np.array(p) - lvD * D.DV['bad.h_roof']['value'], np.array(q) - lvD * D.DV['bad.h_roof']['value']], 'inf', lw=0.6, z=6)
    V.leader(np.array(BAD_DRUMS_IMG[0][0]) - lvD * BAD_DRUM_TOP + [0, -9.6], -30, 26, 'BA-D head: two round drums D ~19 m [obs, NAIP roof circles,\n'
             'dotted = as imaged]; drawn moved back by the relief of a ~13 m top\n(lean 0.58 m/m) [inf]; ~4-5 m above the adjacent roof [obs, low];\n'
             'linear skylights / angular roof-plane edges (dashed, as imaged\nless the 8.5 m roof relief) [obs / inf]', 'obs', fs=4.0)
    # BA-F hub: octagon, lantern rings, NW-arm roof monitor
    lvF = D.dom_lean('F')[0]
    V.poly(octagon(BAF_HUB_C, BAF_HUB_APO), 'obs', fc='none', z=5.5, lw=0.8)
    for apo in BAF_LANTERN_APO:
        V.poly(octagon(baf_lantern_centre(), apo), 'inf', fc='#cfe3f3' if not bg else 'none', z=6, lw=0.6)
    V.poly(baf_monitor(-lvF * 11.0), 'inf', fc='#cfe3f3' if not bg else 'none', z=5.6, lw=0.5)
    fE, fF = BH['fits']['east'], BH['fits']['frame_direction']
    V.leader(BAF_HUB_C + hdg_vec(208) * BAF_HUB_APO, -20, -20, 'BA-F hub: octagonal rotunda [pub CDR massing], 74.2 m across\n'
             '(regular octagon fitted to the SFO Museum outline, residual 0.01 m) [obs];\n'
             f'NAIP 2024: the 4 free faces put the roof edge on it ({fE["delta"]:+.1f} / {fF["delta"]:+.1f} m) at\n'
             f'{fF["h"]:.0f}-{fE["h"]:.0f} m (single epoch, lean-direction dependent) [obs, low];\n'
             'octagonal lantern / skylight rings 19.4 / 13.4 m [obs, NAIP]: its 2020\n'
             f'shadow bounds the rise to <= {BH["ring_2020_shadow"]["rise_upper_bound"]:.1f} m, so it is drawn ECCENTRIC,\n'
             f'{np.hypot(*(baf_lantern_centre() - BAF_HUB_C)):.1f} m E of the hub centre [inf]; heights unknown [unk]', 'obs', fs=4.0)
    V.leader(baf_monitor(-lvF * 11.0)[1] * 0.5 + baf_monitor(-lvF * 11.0)[0] * 0.5 + [0, -4], -14, 22, 'BA-F NW arm: central roof monitor / light strip ~8 m wide\n'
             '[obs, NAIP, low contrast]; drawn less the ~11 m roof relief [inf];\nheight unknown [unk]', 'obs', fs=4.0)
    # labels: piers
    sb = BB['summary']; s_e, s_w, t_s, t_n, t_w = bab_band()
    L = [((-905, 905), -40, 24, 'Boarding Area B (south half, t -1238..-1176):\nouter roof edges ' + fmt_h(DV['bab.h_roof']) + ' [obs]\n'
          'raised central roof ' + fmt_h(DV['bab.h_roof_central']) + ' [obs, low]\nlean-free edges (thick blue): ESE 2.3 m outside, WNW 1.7 m\n'
          'inside the level-2 outline; width 54.3 m [obs]', 'obs'),
         ((-905, 600), -48, -2, 'BA-B north half: outer roof edges not measured [unk];\nroof features drawn from NAIP (wells, bridges, skylights, PV)', 'obs'),
         (st2w(s_e, -1060), 34, 4, f'BA-B raised central roof (hatched) along the WHOLE pier, t {t_s:.0f}..{t_n:.0f}\n'
          f'({t_n - t_s:.0f} m: the straight pier, from its bend towards T1 Center to ~20 m short of the\n'
          f'tip; the oblique north wing beyond the bend not tested [unk]) [obs: its 2020 shadow on the lower\n'
          f'ESE band, {sb["whole"]["step_shadow_len"]["median"]:.2f} m long at {sb["whole"]["step_shadow_len"]["n"]} stations, '
          f'= a {sb["whole"]["h_central_step_shadow"]["median"] - BB["constants"]["h_outer"]:.1f} m step everywhere;\n'
          f'2020-24 parallax {sb["south"]["p_central"]["median"]:.2f} / {sb["north"]["p_central"]["median"]:.2f} m (S / N) vs '
          f'{sb["south"]["p_lip"]["median"]:.2f} / {sb["north"]["p_lip"]["median"]:.2f} m at the outer lip];\n'
          f'top ~{sb["whole"]["h_central"]:.1f} m (N half {sb["north"]["h_central_step_shadow"]["p10"]:.1f}-'
          f'{sb["north"]["h_central_parallax"]["p90"]:.1f}) if the outer roof is 13.1 m throughout [inf];\n'
          f'ESE edge s {s_e:.1f} (thick, obs); WNW edge s {s_w:.1f}: 2024 wall band over the wells\n'
          f'(thick, t {t_w[0]:.0f}..{t_w[1]:.0f}) [obs], carried south [inf]; width {s_e - s_w:.1f} m (dom_bab_band.json)', 'obs'),
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
            ('BA-B raised central roof', fmt_h(DV['bab.h_roof_central']), 'obs', 'parallax ratio + 2020 step shadow (low); '
             f'the same step along the whole pier t {BB["extent"]["t_south"]:.0f}..{BB["extent"]["t_north"]:.0f} (dom_bab_band.json)'),
            ('BA-E tapered fascia (north)', fmt_h(DV['bae.h_roof']), 'obs', 'two-epoch'),
            ('BA-F NE arm', fmt_h(DV['baf.h_roof_ne_arm']), 'obs', 'two-epoch; DOF 06-035331 = 10.36 m [pub]'),
            ('BA-F hub roof edge', f'{BH["fits"]["frame_direction"]["h"]:.0f}-{BH["fits"]["east"]["h"]:.0f} m', 'obs',
             'single epoch: 4 free hub faces vs the SFOM octagon, BA-F lean (low; dom_baf_hub.json)'),
            ('BA-D head', fmt_h(DV['bad.h_roof']), 'obs', 'two-epoch, low (faces 118.7 m apart)'),
            ('BA-C east half', fmt_h(DV['bac.h_roof']), 'obs', 'single face, assumed lean 0.40 (low)'),
            ('Control: BA-A (ITB)', f"{DV['control.ba_a']['value']:.2f} m", 'obs', 'ITB research 17.9 m'),
            ('T1 Center / T2 halls', 'no height', 'unk', 'nothing published or measured'),
            ('T3 R2 / R3 roof high points', '14.48 / 21.34 m', 'inf', 'CDR 58\'-6" / 81\'-0" minus L1 11\'-0" [pub]; datum unknown'),
            ('The app (tools/build_terminal_parts.py)', 'piers 14.6 m', 'app', 'halls T1 20 / T2 19 / T3 21 m')]
    S.table(570, 300, 166, 'Domestic roof heights (above the apron)', rows, fs=3.9, col=(0.42, 0.24))
    S.note('SFO Museum boarding-area polygons are departure-level (sfo:level 2) floor outlines, verified on record 1947304261 (BA-B): they '
           'are not roof outlines. The measured lean-free roof edges lie, from the outline (shapely, + = outside): BA-B ESE +2.3 / WNW -1.7 m; '
           'BA-D +2.4 / -1.4 m; BA-F ESE 0.0 (on the outline) / WNW -1.0 to -1.3 m. Spec frame range: 0-5 m outside (ESE), 0-2 m inside (WNW).')
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
def pier_section(V, x0, title, W, h, rng, tag='obs', step=None, note='', h2=None, rng2=None, Wc=None, offc=0.0, step_lbl=None):
    """schematic cross-section of a pier (looking along its axis): roof width W at height h; step = raised centre;
    step_lbl = ((text, tag) of the left band, the raised part, the right band) to replace the default '~ [inf]' labels."""
    V.ax.fill_between([x0 - 4, x0 + W + 4], [-1.5, -1.5], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(x0 - 4, 0), (x0 + W + 4, 0)], 'pub', lw=0.7)
    if rng:
        V.ax.fill_between([x0, x0 + W], [rng[0]] * 2, [rng[1]] * 2, color='#cfe0f2', lw=0, zorder=1.2, alpha=0.8)
    V.poly([(x0, 0), (x0 + W, 0), (x0 + W, h), (x0, h)], tag, fc='#f4f7fb', z=2, lw=0.8)
    if step:
        a, b = x0 + step[0], x0 + step[0] + step[1]
        if rng2: V.ax.fill_between([a, b], [rng2[0]] * 2, [rng2[1]] * 2, color='#f3d9bf', lw=0, zorder=1.3, alpha=0.8)
        V.poly([(a, h), (b, h), (b, h2), (a, h2)], 'obs', fc='#f4f7fb', z=2.2, lw=0.8, ls=(0, (5, 2)))
        lb = step_lbl or ((f'~{step[0]:.1f} [inf]', 'inf'), (f'~{step[1]:.0f} m raised part [inf, approx]', 'inf'),
                          (f'~{W - step[0] - step[1]:.1f} [inf]', 'inf'))
        V.dim((a, h2), (b, h2), 3, lb[1][0], lb[1][1], fs=4.0)
        V.dim((x0, h), (a, h), 3, lb[0][0], lb[0][1], fs=3.8)
        V.dim((b, h), (x0 + W, h), 3, lb[2][0], lb[2][1], fs=3.8)
        V.level(x0 + W + 1, h2, f'+{h2:.2f} ({rng2[0]:.1f}-{rng2[1]:.1f}) [obs, low]', 'obs', len_mm=3, fs=4.0, u_line=b)
        V.text(((a + b) / 2, (h + h2) / 2), 'clerestory\n(Low-E) [pub]', 'pub', fs=3.8)
    V.level(x0 + W + 1, h, f'+{h:.2f}' + (f' ({rng[0]:.1f}-{rng[1]:.1f})' if rng else '') + f' [{tag}]', tag, len_mm=3, fs=4.0, u_line=x0 + W)
    V.dim((x0, 0), (x0 + W, 0), -5, f'{W:.1f} m' + note, 'obs' if not Wc else Wc, fs=4.0)
    V.text((x0 + W / 2, -11), title, 'pub', fs=4.8, weight='bold', bg=False, color='#000000', style='normal')


BAE_FLANK, BAE_STEP, BAE_OVER = 4.4, 3.0, 1.5   # BA-E: lower side roofs ~10 % of the width each, ~3 m below the raised
                                                # roof, tapered edge overhanging the clerestory ~1.5 m (photo a1, Pi.1415926535
                                                # Sept 2025, CC BY-SA 4.0; pier identified by position / airline) [inf, low]


def bae_section(V, x0, W, h, rng):
    """BA-E stepped cross-section: raised centre roof with a thin tapered edge overhanging a recessed clerestory band,
    between lower flat side roofs [pub form bae.roof; obs photo a1; proportions inf]."""
    V.ax.fill_between([x0 - 4, x0 + W + 4], [-1.5, -1.5], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(x0 - 4, 0), (x0 + W + 4, 0)], 'pub', lw=0.7)
    V.ax.fill_between([x0, x0 + W], [rng[0]] * 2, [rng[1]] * 2, color='#cfe0f2', lw=0, zorder=1.2, alpha=0.8)
    hs = h - BAE_STEP; a, b = x0 + BAE_FLANK, x0 + W - BAE_FLANK
    V.poly([(x0, 0), (x0 + W, 0), (x0 + W, hs), (x0, hs)], 'inf', fc='#f4f7fb', z=2, lw=0.7)          # body + side roofs
    V.poly([(a, hs), (b, hs), (b, h - 1.0), (a, h - 1.0)], 'inf', fc='#d7e6f3', z=2.1, lw=0.5)          # clerestory glazing
    for xx in np.linspace(a, b, 9)[1:-1]:
        V.line([(xx, hs), (xx, h - 1.0)], 'inf', lw=0.2, z=2.15, color='#7f97ad')
    o = BAE_OVER
    roof = [(a - o, h - 0.15), (a + 3, h - 1.0), (b - 3, h - 1.0), (b + o, h - 0.15), (b + o, h), (a - o, h)]
    V.poly(roof, 'obs', fc='#c9c9c9', z=2.3, lw=0.7)
    V.level(x0 + W + 1, h, f'+{h:.2f} ({rng[0]:.1f}-{rng[1]:.1f}) tapered fascia [obs]', 'obs', len_mm=3, fs=4.0, u_line=b + o)
    V.level(x0 + W + 1, hs, f'+{hs:.1f} lower side roofs: ~{BAE_STEP:.0f} m step [inf, photo a1, low]', 'inf', len_mm=3, fs=3.8, u_line=x0 + W)
    V.dim((x0, hs), (a, hs), 3, f'~{BAE_FLANK}', 'inf', fs=3.6)
    V.dim((b, hs), (x0 + W, hs), 3, f'~{BAE_FLANK}', 'inf', fs=3.6)
    V.dim((x0, 0), (x0 + W, 0), -5, f'{W:.1f} m [inf: s-profiles + leans]', 'inf', fs=4.0)
    V.leader((b + o - 0.3, h - 0.1), 2, 16, 'raised centre roof, thin tapered edge overhanging\nthe recessed clerestory glazing [pub IDA: "tapered edges\n'
             'overhanging clerestory glazing"; obs photo a1]; overhang\n~1.5 m, step and flank widths [inf, low]; the measured\n'
             '12.85 m fascia taken as the raised roof\'s edge [inf]', 'pub', fs=3.6)
    V.text((x0 + W / 2, (hs + h - 1.0) / 2), 'clerestory [pub]', 'pub', fs=3.4)
    V.text((x0 + W / 2, -11), 'BOARDING AREA E (north part)', 'pub', fs=4.8, weight='bold', bg=False, color='#000000', style='normal')


def sheet_elev():
    S = Sheet('BD-02', 'Domestic terminals: pier cross-sections on a common datum and Terminal 3 West airside wall sections', 'A1',
              subtitle='Spec: tools/buildings/spec_domestic.json (heights obs; T3 levels / wall sections pub, CDR 95 % CD Oct 2023)')
    V = S.view(0, 420, S.vw, 150, 500, (175, 14), title='1  PIER CROSS-SECTIONS (looking along each pier axis), roof heights above the apron', kind='elev', frame=False)
    VD = S.view(0, 228, 330, 170, 500, (64, 14), title='1b  BOARDING AREA D HEAD (same datum)', kind='elev', frame=False)
    GAP = 28
    x = 0
    s_e, s_w, t_s, t_n, t_w = bab_band(); WB = BAB_OUTER_S[0] - BAB_OUTER_S[1]
    stB = (BAB_OUTER_S[0] - s_e, s_e - s_w)
    pier_section(V, x, f'BOARDING AREA B (typical; raised centre t {t_s:.0f}..{t_n:.0f})', WB, DV['bab.h_roof']['value'], DV['bab.h_roof']['range'],
                 step=stB, h2=DV['bab.h_roof_central']['value'], rng2=DV['bab.h_roof_central']['range'], note=' outer roof edges [obs]',
                 step_lbl=((f'{stB[0]:.1f} [obs]', 'obs'), (f'{stB[1]:.1f} m raised part [obs: lean-free edges, dom_bab_band]', 'obs'),
                           (f'{WB - stB[0] - stB[1]:.1f} [obs N / inf S]', 'obs')))
    V.text((x + 27, 4.5), 'apron + concourse + mezzanine\n("two levels and a mezzanine") [pub];\nfloor heights not published [unk]', 'unk', fs=3.7)
    V.text((x + stB[0] + stB[1] + (WB - stB[0] - stB[1]) / 2, 10.0), 'north half: planted\nsunken roof wells\nin this band;\ndepth unknown [unk]', 'unk', fs=3.2)
    V.text((x + stB[0] + stB[1] / 2, DV['bab.h_roof_central']['value'] + 4.4),
           f"same {BB['summary']['whole']['h_central_step_shadow']['median'] - BB['constants']['h_outer']:.1f} m step along the whole pier "
           f"[obs, 2020 step shadow at {BB['summary']['whole']['step_shadow_len']['n']} stations]", 'obs', fs=3.5)
    x += WB + GAP
    bae_section(V, x, 42.9, DV['bae.h_roof']['value'], DV['bae.h_roof']['range'])
    V.text((x + 21, 4.5), 'concourse; end wall: full-height\nrecessed glass [obs photo a1]', 'obs', fs=3.7)
    x += 42.9 + GAP
    pier_section(V, x, 'BOARDING AREA F (NE arm)', 27.0, DV['baf.h_roof_ne_arm']['value'], DV['baf.h_roof_ne_arm']['range'], note=' lean-free edges [obs]')
    V.mark((x + 13.5, 34 * FT), 'pub', marker='v', ms=4)
    V.text((x + 13.5, 34 * FT + 2.2), 'DOF 06-035331\n34 ft = 10.36 [pub]', 'pub', fs=3.7)
    pier_section(VD, 0, 'BOARDING AREA D (head)', 118.7, DV['bad.h_roof']['value'], DV['bad.h_roof']['range'], note=' between the measured faces [obs, low]')
    VD.text((59, 4.0), 'the two faces may belong to different roof levels\n[obs: parallax 0.5-7 m across the head]', 'unk', fs=3.7)
    hD = DV['bad.h_roof']['value']
    for xc, nm in ((39.4, 'S drum'), (104.3, 'N drum')):     # drum centres projected on the cut (from the ESE face) [inf]
        VD.poly([(xc - 9.6, hD), (xc + 9.6, hD), (xc + 9.6, BAD_DRUM_TOP), (xc - 9.6, BAD_DRUM_TOP)], 'inf', fc='#f6e3cf', z=2.4)
        VD.text((xc, BAD_DRUM_TOP + 1.6), f'{nm}: D ~19 m [obs]\ntop ~{BAD_DRUM_TOP:.0f} m [inf]', 'inf', fs=3.6)
    VD.leader((104.3 + 9.6, BAD_DRUM_TOP - 1.5), 10, 12, 'drums: NAIP roof circles; west wall seen over ~2.5-3 m at the\n'
              'D lean 0.58 m/m -> ~4-5 m above the adjacent roof [obs, low];\npositions projected onto the cut [inf]', 'obs', fs=3.7)
    VD.text((0, -6.5), 'ESE face', 'obs', fs=3.6, ha='left'); VD.text((118.7, -6.5), 'WNW face', 'obs', fs=3.6, ha='right')
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
    # ---------- 1c BA-F hub (section through the lantern) and the NW arm with its roof monitor
    VF = S.view(345, 226, 390, 128, 500, (85, 12), title='1c  BOARDING AREA F: HUB (cut WSW-ENE across the flats, through the lantern) and NW ARM (cross-section)',
                kind='elev', frame=False)
    hF = DV['baf.h_roof_ne_arm']['value']; W8 = 2 * BAF_HUB_APO
    fE, fF = BH['fits']['east'], BH['fits']['frame_direction']; rise = BH['ring_2020_shadow']['rise_upper_bound']
    lc = W8 / 2 + float(np.dot(baf_lantern_centre() - BAF_HUB_C, hdg_vec(73.0)))     # lantern centre on the cut (ENE +) [inf]
    VF.ax.fill_between([-4, W8 + 70], [-1.5, -1.5], [0, 0], color='#dddddd', lw=0, zorder=1)
    VF.line([(-4, 0), (W8 + 70, 0)], 'pub', lw=0.7)
    VF.ax.fill_between([0, W8], [fF['h']] * 2, [fE['h']] * 2, color='#cfe0f2', lw=0, zorder=1.2, alpha=0.8)
    VF.poly([(0, 0), (W8, 0), (W8, hF), (0, hF)], 'inf', fc='#f4f7fb', z=2)
    for apo in BAF_LANTERN_APO[:1]:
        VF.poly([(lc - apo, hF), (lc + apo, hF), (lc + apo, hF + rise), (lc - apo, hF + rise)], 'unk', fc='#cfe3f3', z=2.2)
    VF.dim((0, 0), (W8, 0), -5, f'{W8:.1f} m across the flats [obs: SFOM octagon fit; NAIP faces {fE["delta"]:+.1f} / {fF["delta"]:+.1f} m]', 'obs', fs=3.9)
    VF.dim((lc - BAF_LANTERN_APO[0], hF + rise), (lc + BAF_LANTERN_APO[0], hF + rise), 3, '19.4 lantern [obs]', 'obs', fs=3.7)
    VF.dim((W8 / 2, hF + rise + 4.5), (lc, hF + rise + 4.5), 2, f'{lc - W8 / 2:.1f} E [inf]', 'inf', fs=3.4)
    VF.text((W8 / 2, hF / 2), f'hub roof drawn at the NE-arm height 10.49 m [inf];\nband: {fF["h"]:.1f}-{fE["h"]:.1f} m, NAIP 2024 fit of the 4 free\n'
            'faces with the BA-F lean, by its direction [obs, low]', 'inf', fs=3.4)
    VF.level(W8 + 1, fE['h'], f'+{fE["h"]:.1f} / +{fF["h"]:.1f} [obs, low, single epoch]', 'obs', len_mm=3, fs=3.5, u_line=W8)
    VF.leader((lc + BAF_LANTERN_APO[0], hF + rise - 1), 8, 9, f'lantern: rise <= {rise:.1f} m (its 2020 cast shadow,\n<= {BH["ring_2020_shadow"]["length"]:.1f} m '
              f'at 1.25 m/m) [obs, low]; drawn at the bound\n(dotted placeholder, rise unknown) [unk]; so the 8.1 m imaged\n'
              f'offset is eccentricity: centre ~{np.hypot(*(baf_lantern_centre() - BAF_HUB_C)):.1f} m E of the hub\ncentre [inf] (a concentric ring would need ~12 m)', 'unk', fs=3.5)
    x0 = W8 + 22; Wa = 37.5
    VF.poly([(x0, 0), (x0 + Wa, 0), (x0 + Wa, hF), (x0, hF)], 'unk', fc='#f4f7fb', z=2)
    m0 = x0 + Wa / 2 - 4.0
    VF.poly([(m0, hF), (m0 + 8.0, hF), (m0 + 8.0, hF + 2.5), (m0, hF + 2.5)], 'unk', fc='#cfe3f3', z=2.2)
    VF.dim((x0, 0), (x0 + Wa, 0), -5, f'~{Wa} m imaged roof width [obs, low]', 'obs', fs=3.8)
    VF.dim((m0, hF + 2.5), (m0 + 8.0, hF + 2.5), 3, '~8 monitor [obs]', 'obs', fs=3.6)
    VF.text((x0 + Wa / 2, hF / 2), 'NW arm: height not measured\n(drawn at 10.49 [inf])', 'unk', fs=3.6)
    VF.scalebar(y_mm=3)
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
    for y0 in (ft(34), ft(46)):
        V2.poly([(1.0, y0), (11.0, y0), (11.0, y0 + ft(10)), (1.0, y0 + ft(10))], 'pub', fc='#5f6d7a', z=3, lw=0.4)
    V2.text((6, ft(45)), "2'-0\" band", 'pub', fs=3.4, color='#ffffff', bg=False)
    V2.leader((11, ft(40)), 4, -26, "window wall 10'-0\" + 2'-0\" band + 10'-0\" = the 22'-0\" from the international level (34'-0\")\n"
              "to the top of the parapet (56'-0\") [pub chain, spec t3w.wall_field verification]; which 10 ft is on top: as\n"
              "printed order [inf]; the upper window runs in front of the 3'-6\" parapet [inf]", 'pub', fs=3.8)
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
    S.note(f'BA-B step (dom_bab_band.json, review r1-23): the raised centre runs the whole straight pier, t {BB["extent"]["t_south"]:.0f}..'
           f'{BB["extent"]["t_north"]:.0f} ({BB["extent"]["length_m"]:.0f} m): its 2020 shadow on the lower ESE band is '
           f'{BB["summary"]["whole"]["step_shadow_len"]["p10"]:.2f}-{BB["summary"]["whole"]["step_shadow_len"]["p90"]:.2f} m long at '
           f'{BB["summary"]["whole"]["step_shadow_len"]["n"]} stations (same step everywhere); 2020-24 parallax of the centre exceeds '
           'the outer lip at every correlating station. Lean-free edges: ESE s %.1f (2020 edge), WNW s %.1f (2024 wall band over the '
           'wells, north half; carried south [inf]); bands %.1f (ESE) / %.1f (WNW), raised part %.1f m. The outer roof height (13.1 m) is '
           'measured on the south half only [inf elsewhere].' % (BB['ese_edge']['s_lean_free'], BB['wnw_edge']['s_lean_free'],
                                                                BAB_OUTER_S[0] - BB['ese_edge']['s_lean_free'],
                                                                BB['wnw_edge']['s_lean_free'] - BAB_OUTER_S[1],
                                                                BB['ese_edge']['s_lean_free'] - BB['wnw_edge']['s_lean_free']))
    S.note('BA-E is drawn stepped (photo a1, Sept 2025, CC BY-SA 4.0; pier identified by position and airline only): a raised PV-covered '
           'centre roof whose knife-thin tapered edge overhangs a recessed glass clerestory / end wall, between lower flat side roofs. Step '
           '(~3 m), flank width (~4.4 m) and overhang (~1.5 m) are photo proportions [inf, low]; which level the measured 12.85 m fascia '
           'belongs to is not settled (drawn as the raised roof).')
    S.note('BA-E width 42.9 m is derived from the research s-profiles (fascia s -686.2, 2020; WNW roof edge s -726.5, 2024) with the solved '
           'leans [inf]; BA-C width is the level-2 outline.')
    return S.finish()


# ------------------------------------------------------------------------------------------------ BD-03 landside elevations
# Face lengths: SFO Museum level-2 outline edges whose outward normal faces the central garage (within 260 m of its centre):
# T1 two curved runs of 94.1 m ((-805.4, 375.7) -> (-871.2, 440.7)) and 93.8 m ((-912.8, 453.6) -> (-1003.6, 437.3)) with a
# 43.6 m set-back between them; T2 one run of 47.7 m ((-748.3, 296.4) -> (-770.7, 338.5)) [obs SFOM].
# Heights above the departures curb, photo d1 (Famartin 2025-08-12 09:08, CC BY-SA 4.0, from the garage; a person by the wall =
# ~45 px for ~1.7 m): canopy soffit ~3.5-4.5 m, wall head ~12-14 m, tier transom 44 % of the way from the canopy to the head
# [inf, photo d1, low]. The curb's own height above the apron is not published or measured [unk].
T1_RUNS = (94.1, 43.6, 93.8)
T1_CANOPY, T1_HEAD, T1_SPLIT = 4.0, 13.0, 0.44
T2_FACE = 47.7
# Terminal 3 landside face (review r1-34): SFO Museum level-2 outline edges facing the central garage (outward normal within 45 deg
# of the garage centre (-938.2, 256.5)) [obs SFOM]: west run (-1084.6, 170.3) -> (-1008.1, 99.4), 106.4 m of facing edges in
# alternating 10.3 / 4.5 m bays with 0.6-0.9 m jogs; a 16.6 m gap where the AirTrain-station / garage connector joins; east run
# (-992.2, 94.5) -> (-874.6, 116.5), 122.5 m. The face is an arc about the garage (169-172 m), 2.858 m of the east run per
# degree of bearing from the garage centre. West run = T3 West, east run = T3 East (CDR 95 % CD p.24 landside view labels) [inf].
T3_RUNS = (106.4, 16.6, 122.5)
T3_E_BRG0, T3_E_M_PER_DEG = 341.56, 2.858
# Levels, project elevations [pub CDR 95 % CD p.28-29] as metres above T3 L1 arrivals TOC 11'-0" [inf: subtraction]
T3_LV = dict(L2=16 * FT, L3=34 * FT, R2=47.5 * FT, PARAPET_W=55 * FT, R3=70 * FT)
# T3 East mechanical penthouse, NAIP 2024 luminance profiles (2026-11-04): imaged roof top x -944..-884, S edge z 68 / 70.5 / 76
# at x -935 / -915 / -895, N edge z 42.5 / 45.5 / 49.5; W wall seen as a 3.3 m dark band, N-side shadow 1.5-2 m -> ~6-9 m above
# the adjacent roof [obs, low] (R3 - R2 = 6.9 m). Lean-free: imaged minus ~8 m E (top ~21.5 m x 0.33-0.44 m/m, the BA-F / BA-E
# leans) [inf]; radially projected on the east run by bearing from the garage centre: 356.0 .. 13.4 deg.
T3E_PENT_BRG = (356.0, 13.4)
T3E_PENT_SETBACK = (20.0, 24.0)


def t1_mullions(x0, x1, seed=7):
    """irregular vertical mullion positions ('reminiscent of Redwood trees' [pub]): 1.2-2.4 m apart, schematic [inf]."""
    rng = np.random.default_rng(seed); xs = [x0]
    while xs[-1] < x1 - 1.2: xs.append(xs[-1] + float(rng.uniform(1.2, 2.4)))
    return xs[1:-1]


def sheet_landside():
    S = Sheet('BD-03', 'Domestic terminals: landside (curb) elevations of Harvey Milk Terminal 1 Center, Terminal 2 and Terminal 3', 'A1',
              subtitle='Spec: tools/buildings/spec_domestic.json (t1c.landside_facade, t2.landside, t3.levels_datum, t3.penthouses [pub]); '
                       'photo d1, CDR T3W 95 % CD (reference)')
    # ---- T1 Center: developed elevation of the curved face towards the central garage
    L = sum(T1_RUNS)
    V = S.view(0, 330, S.vw, 200, 400, (L / 2 + 28, 6.5), title='1  HARVEY MILK TERMINAL 1 CENTER: landside face towards the central garage, '
               'DEVELOPED (unrolled along the curved outline), looking SE', kind='elev', frame=False)
    V.ax.fill_between([-8, L + 8], [-1.2, -1.2], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(-8, 0), (L + 8, 0)], 'unk', lw=0.8)
    xs = [0.0, T1_RUNS[0], T1_RUNS[0] + T1_RUNS[1], L]
    V.text(((xs[1] + xs[2]) / 2, -2.6), 'departures curb (upper roadway); its height above the apron\nis not published or measured [unk]', 'unk', fs=3.6)
    hs = T1_CANOPY + (T1_HEAD - T1_CANOPY) * T1_SPLIT
    for a, b, setback in ((xs[0], xs[1], False), (xs[1], xs[2], True), (xs[2], xs[3], False)):
        if setback:
            V.poly([(a, 0), (b, 0), (b, T1_HEAD), (a, T1_HEAD)], 'unk', fc='#f2f2f2', z=1.5)
            V.text(((a + b) / 2, T1_HEAD / 2), f'{b - a:.1f} m set-back in the\noutline (station / connector?)\nnot drawn [unk]', 'unk', fs=3.6)
            continue
        V.poly([(a, 0), (b, 0), (b, T1_CANOPY), (a, T1_CANOPY)], 'obs', fc='#cfdce8', z=1.6, lw=0.4)                 # clear glass below
        V.poly([(a, T1_CANOPY), (b, T1_CANOPY), (b, T1_HEAD), (a, T1_HEAD)], 'obs', fc='#c4d8c4', z=1.6, lw=0.6)      # fritted green
        V.line([(a, hs), (b, hs)], 'obs', lw=0.5, z=1.7, color='#5b6b5b')
        for x in t1_mullions(a, b):
            V.line([(x, T1_CANOPY), (x, T1_HEAD)], 'inf', lw=0.25, z=1.7, color='#5b6b5b')
        V.poly([(a - 0.5, T1_CANOPY - 0.35), (b + 0.5, T1_CANOPY - 0.35), (b + 0.5, T1_CANOPY), (a - 0.5, T1_CANOPY)], 'obs', fc='#9fb7c9', z=1.8, lw=0.4)
        for x in np.arange(a + 1, b, 3.0):
            V.line([(x, T1_HEAD + 0.15), (x + 2.2, T1_HEAD + 0.9)], 'obs', lw=0.4, z=1.7, color='#4c6a88')            # PV at the roof edge
        V.dim((a, 0), (b, 0), -5, f'{b - a:.1f} m developed [obs SFOM outline]', 'obs', fs=3.8)
    a, b = xs[2], xs[3]
    V.poly([(a + 35, hs + 0.8), (b - 6, hs + 0.8), (b - 6, T1_HEAD - 1.0), (a + 35, T1_HEAD - 1.0)], 'obs', fc='none', lw=0.4, z=1.9, ls=(0, (1, 1)))
    V.text(((a + 35 + b - 6) / 2, (hs + T1_HEAD) / 2 + 0.2), 'Harvey Milk Terminal\nTerminal (1)', 'obs', fs=5.0, bg=False, color='#26323d', style='normal', weight='bold', z=2)
    V.leader((b - 6, T1_HEAD - 1.0), 10, 8, 'signage zone "Harvey Milk Terminal / Terminal 1" in the\nupper tier [obs photo d1]; extent schematic [inf]', 'obs', fs=3.7)
    V.leader((a + 8, (T1_CANOPY + hs) / 2), -4, 26, 'two-tier fritted-glass curtain wall, vertical mullions "reminiscent of\nRedwood trees" [pub t1c.landside_facade]; '
             'irregular mullion rhythm\n(drawn 1.2-2.4 m, schematic) [inf]; green frit [obs photo d1]', 'pub', fs=3.7)
    V.leader((xs[0] + 20, T1_CANOPY - 0.2), 4, -24, 'continuous glass canopy over the curb; clear glass below it\n[pub CDR 2016 / t1c.landside_facade; '
             'obs photo d1]; warm wood entries [pub]', 'pub', fs=3.7)
    V.leader((xs[0] + 60, T1_HEAD + 0.6), 8, 10, 'PV along the roof edge [obs photo d1, NAIP]', 'obs', fs=3.7)
    for h, s, tg in ((T1_CANOPY, f'+{T1_CANOPY:.1f} canopy (3.5-4.5) above the curb', 'inf'), (hs, f'+{hs:.1f} tier transom (44 % up)', 'inf'),
                     (T1_HEAD, f'+{T1_HEAD:.1f} wall head (12-14) above the curb', 'inf')):
        V.level(L + 2, h, s + f' [{tg}, photo d1, low]', tg, len_mm=4, fs=3.8, u_line=L)
    V.scalebar(y_mm=4)
    # ---- T2
    V2 = S.view(0, 8, 420, 150, 200, (T2_FACE / 2 + 22, 6), title='2  TERMINAL 2: landside entry face towards the central garage, looking E', kind='elev', frame=False)
    V2.ax.fill_between([-8, T2_FACE + 8], [-1.2, -1.2], [0, 0], color='#dddddd', lw=0, zorder=1)
    V2.line([(-8, 0), (T2_FACE + 8, 0)], 'unk', lw=0.8)
    hb = 12.0
    V2.poly([(0, 0), (T2_FACE, 0), (T2_FACE, hb), (0, hb)], 'unk', fc='#eeeeec', z=1.5)
    for y in np.arange(1.5, hb, 1.5):
        V2.line([(0, y), (T2_FACE, y)], 'unk', lw=0.15, z=1.6, color='#bbbbbb')
    g0, g1 = T2_FACE * 0.2, T2_FACE * 0.8
    V2.poly([(g0, 0), (g1, 0), (g1, 7.0), (g0, 7.0)], 'unk', fc='#d7e6f3', z=1.7)
    V2.poly([(g0 + 3, 8.2), (g1 - 3, 8.2), (g1 - 3, 10.6), (g0 + 3, 10.6)], 'unk', fc='none', z=1.8, ls=(0, (1, 1)))
    V2.text(((g0 + g1) / 2, 9.4), 'Terminal 2', 'unk', fs=5.0, bg=False, color='#555555', style='normal', weight='bold')
    V2.dim((0, 0), (T2_FACE, 0), -5, f'{T2_FACE} m [obs SFOM outline face]', 'obs', fs=3.8)
    V2.leader((T2_FACE, hb), 8, 6, 'light metal-panel box with the "Terminal 2" sign and a glass entry\nwall ("neutral exterior, warm interior") [pub CDR '
              't2.landside]; the box\nheight (drawn 12 m), the glass-wall extent and the sign position are\nplaceholders: NOT published or measured [unk]',
              'unk', fs=3.7)
    V2.scalebar(y_mm=4)
    sheet_landside_t3(S)
    S.note('Landside faces are developed along the SFO Museum level-2 outline edges that face the central garage (lengths [obs]); heights are '
           'above the departures curb, whose own height above the apron is unknown. Photo d1 (Famartin 2025-08-12, CC BY-SA 4.0) is reference '
           'only; its ratios are scaled by a person at the wall (~1.7 m) [inf, low].')
    S.note('T2: nothing about the landside face is dimensioned in any source found; the elevation records the published description only.')
    S.note('T3 (view 3, review r1-34): heights are the published project levels (CDR 95 % CD, Oct 2023) above T3 L1 (11\'-0"), not above '
           'the curb; the project datum is not printed (L1 ~1-2 ft above the apron if it is ~AMSL [inf]). The facade bands of T3 West are '
           'proportions of the rendered CDR wall section p.23 (no dimensions printed) [inf, low]; the T3 East landside facade is not '
           'described in any source found [unk]. T3W is under construction 2024-2029 (the May 2026 change adds an airside storey).')
    return S.finish()


def sheet_landside_t3(S):
    """view 3 of BD-03: Terminal 3 landside face, developed along the SFO Museum outline (review r1-34)."""
    Lw, Lg, Le = T3_RUNS; L = Lw + Lg + Le; lv = T3_LV
    V = S.view(0, 165, S.vw, 160, 400, (L / 2 + 26, 9.5), title='3  TERMINAL 3: landside face towards the central garage, DEVELOPED '
               '(unrolled along the curved outline), looking NW; T3 West left, T3 East right; heights above T3 L1', kind='elev', frame=False)
    V.ax.fill_between([-8, L + 8], [-1.2, -1.2], [0, 0], color='#dddddd', lw=0, zorder=1)
    V.line([(-8, 0), (L + 8, 0)], 'inf', lw=0.6)
    x0, x1, x2 = 0.0, Lw, Lw + Lg
    # T3 West: arrivals level behind the lower roadway; ACM spandrel at the departures level; window wall with fritted IGU; ACM to
    # the new parapet 66'-0" [pub materials CDR p.23 / t3w.materials; band proportions inf, low]
    yS, yW = lv['L2'] + 1.7, lv['L2'] + 7.5
    V.poly([(x0, 0), (x1, 0), (x1, lv['L2']), (x0, lv['L2'])], 'unk', fc='#eeeeee', z=1.5)
    V.poly([(x0, lv['L2']), (x1, lv['L2']), (x1, yS), (x0, yS)], 'inf', fc='#c9ccd0', z=1.6, lw=0.4)
    V.poly([(x0, yS), (x1, yS), (x1, yW), (x0, yW)], 'inf', fc='#c6d6e4', z=1.6, lw=0.4)
    V.poly([(x0, yW), (x1, yW), (x1, lv['PARAPET_W']), (x0, lv['PARAPET_W'])], 'pub', fc='#d9dadc', z=1.6, lw=0.6)
    for u in np.arange(x0, x1, 2.0):      # schematic window-wall mullions (module not published) [unk]
        V.line([(u, yS), (u, yW)], 'unk', lw=0.15, z=1.7, color='#7f97ad')
    V.line([(x0, (yS + yW) / 2 + 0.6), (x1, (yS + yW) / 2 + 0.6)], 'unk', lw=0.2, z=1.7, color='#7f97ad')
    for u in np.arange(x0, x1, 4.5):      # ACM panel joints (module not published) [unk]
        V.line([(u, yW), (u, lv['PARAPET_W'])], 'unk', lw=0.12, z=1.7, color='#a0a0a0')
    V.text(((x0 + x1) / 2, lv['L2'] / 2), 'arrivals level, behind the lower roadway [unk]', 'unk', fs=3.4)
    V.leader((x0 + 20, (yS + yW) / 2), 2, 34, 'T3 WEST (under construction 2024-2029): ACM rainscreen panels (Whetstone Gray Metallic, Norfolk\n'
             'Gray Mica, Focus Black) above an aluminium window wall with fritted IGUs over the departures level, ACM\n'
             'spandrel at the slab edge [pub CDR p.23 "East Facade Wall Sections" / t3w.materials]; band heights are\n'
             'proportions of that rendered section, NOT dimensioned (spandrel ~1.7 m, glazing ~5.8 m) [inf, low];\n'
             'mullion / panel modules not published (schematic) [unk]', 'pub', fs=3.5)
    # connector gap
    V.poly([(x1, 0), (x2, 0), (x2, lv['L3']), (x1, lv['L3'])], 'unk', fc='#f4f4f4', z=1.5)
    V.text(((x1 + x2) / 2, lv['L3'] / 2), f'{Lg:.1f} m\nAirTrain /\ngarage\nconnector\n(not drawn)\n[unk]', 'unk', fs=3.2)
    # T3 East: massing to R2 (the roof high point) [inf], facade unknown; penthouse set back
    V.poly([(x2, 0), (L, 0), (L, lv['R2']), (x2, lv['R2'])], 'unk', fc='#eeeeec', z=1.5)
    V.text(((x2 + L) / 2 + 30, lv['R2'] / 2 + 1.0), 'T3 EAST landside facade: not described in the sources found [unk];\n'
           'wall head drawn at R2 "top of roof at high point" [pub level; inf as the wall head]', 'unk', fs=3.4)
    pu = [x2 + (b - T3_E_BRG0 + (360 if b < 180 else 0)) * T3_E_M_PER_DEG for b in T3E_PENT_BRG]
    V.poly([(pu[0], lv['R2']), (pu[1], lv['R2']), (pu[1], lv['R3']), (pu[0], lv['R3'])], 'inf', fc='#e4e6e8', z=1.45)
    for h in np.arange(lv['R2'] + 1.4, lv['R3'] - 0.3, 1.4):     # wide-profile accent stripes (pattern schematic)
        V.line([(pu[0], h), (pu[1], h)], 'unk', lw=0.25, z=1.46, color='#9a9a9a')
    V.dim((pu[0], lv['R3']), (pu[1], lv['R3']), 3, f'{pu[1] - pu[0]:.0f} m [obs NAIP 2024 top edges, lean-corrected inf; radial projection]', 'inf', fs=3.5)
    V.leader((pu[0], lv['R3'] - 1.0), -6, 6, 'T3 EAST mechanical penthouse [pub CDR "Existing Massing", t3.penthouses]: light-grey perforated\n'
             'corrugated metal with wide-profile accent stripes [pub t3e]; set back ~%.0f-%.0f m behind the face [obs NAIP];\n'
             'top drawn at R3 81\'-0" [inf: R3 read as its roof; NAIP W-wall band 3.3 m and N shadow 1.5-2 m give\n'
             '~6-9 m above the roof (obs, low), R3 - R2 = 6.9 m]' % T3E_PENT_SETBACK, 'inf', fs=3.5)
    V.text((x0 + 78, lv['PARAPET_W'] + 1.9), 'T3W: a row of existing smaller penthouses and new mechanical penthouses (CDR p.12-15):\n'
           'positions and heights not dimensioned [unk], not drawn', 'unk', fs=3.4)
    # departures roadway deck in front at ~L2 [inf, CDR p.23 section: the departures level meets the curb]
    V.ax.fill_between([-6, L + 6], [lv['L2'] - 1.3] * 2, [lv['L2'] - 0.2] * 2, color='#b9b9b9', lw=0, zorder=1.9, alpha=0.55)
    V.text((L - 4, lv['L2'] - 2.4), 'departures roadway (upper level) in front, deck at ~L2 [inf, CDR p.23 section]', 'inf', fs=3.4, ha='right')
    for a, b, t in ((x0, x1, 'T3 West'), (x2, L, 'T3 East')):
        V.dim((a, 0), (b, 0), -5, f'{t}: {b - a:.1f} m developed [obs SFOM outline]', 'obs', fs=3.7)
    for k, (h, txt) in enumerate(((0.0, "+0.00 T3 L1 arrivals TOC 11'-0\""), (lv['L2'], f"+{lv['L2']:.2f} L2 departures 27'-0\""),
                                  (lv['L3'], f"+{lv['L3']:.2f} L3 FIS corridor 45'-0\""), (lv['R2'], f"+{lv['R2']:.2f} R2 top of roof, high pt 58'-6\""),
                                  (lv['PARAPET_W'], f"+{lv['PARAPET_W']:.2f} T3W top of parapet 66'-0\""), (lv['R3'], f"+{lv['R3']:.2f} R3 top of roof, high pt 81'-0\""))):
        V.level(L + 2, h, txt + ' [pub; above L1 inf]', 'pub', len_mm=4, fs=3.6, u_line=L if h <= lv['R2'] else None)
    V.scalebar(y_mm=4)
