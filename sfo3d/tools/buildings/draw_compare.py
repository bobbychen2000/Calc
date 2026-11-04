"""BX-01: what the 3-D app builds today against the verified specs (comparison sheet, A2).

The app values are read from the code / data that build the buildings (no js/ or data/ file is changed):
  js/live/terminals.js   buildTerminals (part heights from data/sfo_buildings.json), greatHall (ITB roof), buildTower
  js/live/airport.js     STRUCT_H_BY_NAME (garages, hotel, hangar, CAC, RCC), STRUCT_H (AirTrain stations)
  data/sfo_buildings.json part heights (piers 14.6 m, halls 19-25.3 m) - made by tools/build_terminal_parts.py
The spec values: tools/buildings/spec_{tower,itb,domestic,landside}.json (tags as on the other sheets).
"""
import numpy as np

import draw_data as D
from draw_lib import Sheet, BORDER, TAGS, FT
from draw_tower import body_outline, H1, H2, S2, fam2

TV, IV, DV, LV = D.TV, D.IV, D.DV, D.LV


def rows():
    A = D.app_tower(); cab = A['cab']
    rim_app = cab['roof'][2][1]; glass = cab['glass']
    G = D.app_great_hall()
    sp = lambda nm: D.app_part(nm)['h']
    hall_top = [G['top'](s) for s in np.linspace(-G['L'] / 2, G['L'] / 2, 200)]
    R = [
        # (building / item, app, spec, tag, delta, note)
        ('Tower: shaft position', '(-740.9, 331.7) footprint centroid', 'axis (-740.5, 324.5); cab (-739, 323.5)', 'inf', '7.2 m S', 'cab z 323.5 +-2 [obs]'),
        ('Tower: roof rim', f'{rim_app:.1f} m', f'{H1} m (63.0-67.6)', 'inf', f'{rim_app - H1:+.1f} m', '221 ft [pub], definition open'),
        ('Tower: cab glass sill / head', f'{glass[0][1]:.1f} / {glass[1][1]:.1f} m', '61.8 / 64.7 m', 'inf', f'{glass[0][1] - 61.8:+.1f} m', 'photo stations'),
        ('Tower: cab-roof diameter', f'{2 * cab["roof"][1][0]:.1f} m', '14.3 +-1.0 (14.75 +-0.5) m', 'obs', f'{2 * cab["roof"][1][0] - 14.3:+.1f} m', 'EXIF / panel scale'),
        ('Tower: flare, widest', f'D {2 * 7.2:.1f} at 57.2 m', 'D 22.6 +-1.5 at 59.4 m', 'obs', f'{14.4 - 22.6:+.1f} m', ''),
        ('Tower: waist', 'D 8.4 at 36-44 m', 'D 9.8 at 26.3 m', 'obs', '-1.4 m', ''),
        ('Tower: mast tips / base-building roof', f'{cab["mast_top"]:.1f} / {A["ibf_roof"]:.1f} m', '70.7 / 14.2 (12.7-16.5) m', 'inf', f'{cab["mast_top"] - 70.7:+.1f} / {A["ibf_roof"] - 14.2:+.1f}', ''),
        ('ITB hall: roof top', f'{min(hall_top):.1f}-{max(hall_top):.1f} m ("83 ft")', '34.9-40.1 m (DOF 131/132 ft)', 'pub', f'{max(hall_top) - 40.08:+.1f} m', '83 ft is the interior height'),
        ('ITB hall: roof size', f'{G["L"]:.1f} x {G["W"]:.1f} m', '252.9 x 65.4 m (860 ft pub)', 'obs', f'{G["L"] - 252.9:+.1f} / {G["W"] - 65.4:+.1f}', ''),
        ('ITB hall: roof centre / axis', f'({G["c"][0]:.1f}, {G["c"][1]:.1f}), SFOM hall-part axis', '(-1244.6, 365.4), 162.85 deg', 'obs', '35 m E, 2.9 deg', ''),
        ('ITB hall: columns', '2 x 10 along the long edges', '5 truss lines x 4 at +-190 / +-270 ft', 'inf', 'layout', '20 from level 3 [pub]'),
        ('Boarding Area A', f'{sp("Boarding Area A")} m', '17.9 m (16.9-18.8); pod 1 25.9 m', 'obs', f'{sp("Boarding Area A") - 17.9:+.1f} m', 'pods not built'),
        ('Boarding Area G', f'{sp("Boarding Area G")} m', '17.0 m (13-20)', 'obs', f'{sp("Boarding Area G") - 17.0:+.1f} m', 'low'),
        ('Boarding Area B', f'{sp("Boarding Area B")} m flat', '13.1 outer / 19.0 raised centre', 'obs', f'{sp("Boarding Area B") - 13.14:+.1f} / {sp("Boarding Area B") - 19.04:+.1f}', 'stepped section'),
        ('Boarding Area C', f'{sp("Boarding Area C")} m', '7.2 m (7.0-7.5)', 'obs', f'{sp("Boarding Area C") - 7.2:+.1f} m', 'low'),
        ('Boarding Area D', f'{sp("Boarding Area D")} m', '8.5 m (8.1-8.9)', 'obs', f'{sp("Boarding Area D") - 8.49:+.1f} m', 'low'),
        ('Boarding Area E', f'{sp("Boarding Area E")} m', '12.85 m (12.2-13.5)', 'obs', f'{sp("Boarding Area E") - 12.85:+.1f} m', ''),
        ('Boarding Area F (NE arm)', f'{sp("Boarding Area F")} m', '10.49 m; DOF 10.36 m', 'obs', f'{sp("Boarding Area F") - 10.49:+.1f} m', ''),
        ('Pier outlines', 'SFOM level-2 outline = roof', 'roof 1.8-2.3 m outside (ESE), 1.3-1.7 inside (WNW)', 'obs', '1-3 m', 'BA-B, BA-F'),
        ('T1 / T2 / T3 halls', f'{D.app_part("Harvey Milk Terminal 1")["h"]} / {D.app_part("Terminal 2")["h"]} / {D.app_part("Terminal 3")["h"]} m', 'T1, T2 unknown; T3 R2 14.5 / R3 21.3', 'inf', '-', 'T3 datum unknown'),
        ('Central Parking Garage', f'{D.APP_STRUCT_H["Central Parking Garage"]} m', '24.69 m (81 ft)', 'pub', f'{22 - 24.69:+.1f} m', 'definition open'),
        ('Garages A / G', '21 / 21 m', 'deck unmeasured; drums 39.6 / 37.6', 'obs', '?', '9 levels [pub]'),
        ('LTP Garage 1 / 2', '16 / 16 m', '16.5 (parapet) / 18.3 (deck)', 'obs', '-0.5 / -2.3', 'LTP2 inf'),
        ('Rental Car Center', '26 m', '16.5-18.0 roof (DOF) / 20.1 (66 ft)', 'pub', '+8.0 / +5.9', ''),
        ('Consolidated Admin. Campus', '20 m', '18.3-19.5 m', 'inf', '+0.5..+1.7', 'shadow 17.4-19.2'),
        ('Grand Hyatt', '38 m', '~44 m (40-48)', 'inf', '-6 m', 'not published'),
        ('Superbay hangar', '34 m flat box', '41.15 m (DOF 135 ft)', 'pub', '-7.2 m', 'spine + cantilevers'),
        ('United MOC hangars', 'not built', 'DOF 35.4-40.2 m; imaged roofs', 'pub', '-', 'no SFOM outline'),
    ]
    return R


def sheet():
    S = Sheet('BX-01', 'Current 3-D app vs the verified building specs', 'A2',
              subtitle='App: js/live/terminals.js, js/live/airport.js, data/sfo_buildings.json (read only). Spec: tools/buildings/spec_*.json')
    S.used_tags.add('app')
    fig, pw, ph = S.fig, S.pw, S.ph
    # ---------------- table
    ax = fig.add_axes([BORDER / pw, (BORDER + 168) / ph, 300 / pw, 228 / ph]); ax.set_xlim(0, 300); ax.set_ylim(0, 228); ax.axis('off')
    cols = [0, 64, 130, 228, 262]
    hdr = ['Building / item', 'App today', 'Verified spec', 'Delta (app - spec)', 'Note']
    y = 226
    ax.text(0, y, 'Comparison table (heights above grade)', fontsize=7.0, fontweight='bold', va='top'); y -= 6
    for c, h in zip(cols, hdr):
        ax.text(c, y, h, fontsize=4.9, fontweight='bold', va='top')
    y -= 3.6; ax.plot([0, 300], [y + 0.6, y + 0.6], color='k', lw=0.5)
    for it, app, spec, tag, dl, note in rows():
        T = TAGS[tag]
        ax.text(cols[0], y, it, fontsize=4.5, va='top')
        ax.text(cols[1], y, app, fontsize=4.5, va='top', color=TAGS['app']['c'])
        ax.text(cols[2], y, f'{spec} [{tag}]', fontsize=4.5, va='top', color=T['c'], fontstyle=T['st'])
        ax.text(cols[3], y, dl, fontsize=4.5, va='top', fontweight='bold')
        ax.text(cols[4], y, note, fontsize=4.1, va='top', color='#555555')
        y -= 7.1
        ax.plot([0, 300], [y + 2.2, y + 2.2], color='#e0e0e0', lw=0.3)
    # ---------------- heights dot plot
    ax2 = fig.add_axes([(BORDER + 58) / pw, (BORDER + 10) / ph, 236 / pw, 150 / ph])
    items = [('Tower roof rim', 61.9, H1, (63.0, 67.6), 'inf'), ('Tower base bldg', 14.0, 14.2, (12.7, 16.5), 'inf'),
             ('ITB hall roof (max)', 26.5, 40.08, (34.9, 40.1), 'pub'), ('BA-A', 14.6, 17.9, (16.9, 18.8), 'obs'), ('BA-G', 14.6, 17.0, (13, 20), 'obs'),
             ('BA-B outer', 14.6, 13.14, (12.49, 13.81), 'obs'), ('BA-B centre', 14.6, 19.04, (18.1, 20.0), 'obs'), ('BA-C', 14.6, 7.2, (6.99, 7.53), 'obs'),
             ('BA-D', 14.6, 8.49, (8.07, 8.93), 'obs'), ('BA-E', 14.6, 12.85, (12.21, 13.51), 'obs'), ('BA-F', 14.6, 10.49, (9.97, 11.03), 'obs'),
             ('Central garage', 22, 24.69, None, 'pub'), ('Garage A (drum)', 21, 39.6, (25, 41.5), 'obs'), ('Garage G (drum)', 21, 37.6, (25, 40), 'obs'),
             ('LTP 1', 16, 16.5, (15.9, 16.8), 'obs'), ('LTP 2', 16, 18.29, None, 'inf'), ('RCC roof', 26, 17.98, (16.46, 20.12), 'pub'),
             ('CAC', 20, 19.51, (17.4, 19.5), 'inf'), ('Grand Hyatt', 38, 44, (40, 48), 'inf'), ('Superbay', 34, 41.15, None, 'pub')]
    yy = np.arange(len(items))[::-1]
    for y_, (nm, a, s, rg, tg) in zip(yy, items):
        T = TAGS[tg]
        if rg: ax2.plot(rg, [y_, y_], color=T['c'], lw=2.2, alpha=0.35, solid_capstyle='butt')
        ax2.plot([s], [y_], 'o', ms=3.4, color=T['c'])
        ax2.plot([a], [y_], 'x', ms=4.2, mew=1.0, color=TAGS['app']['c'])
        ax2.plot([a, s], [y_, y_], color='#bbbbbb', lw=0.4, zorder=0)
    ax2.set_yticks(yy); ax2.set_yticklabels([i[0] for i in items], fontsize=4.6)
    ax2.set_xlabel('height above grade (m)', fontsize=5); ax2.tick_params(axis='x', labelsize=4.6)
    ax2.grid(axis='x', color='#e5e5e5', lw=0.4); ax2.set_xlim(0, 72)
    ax2.set_title('Heights: app (x, magenta) vs spec (dot, tag colour; bar = range)', fontsize=5.6, loc='left')
    for s_ in ax2.spines.values(): s_.set_linewidth(0.4)
    # ---------------- tower profile (true scale 1:500)
    V = S.view(318, 205, 170, 190, 500, (0, 36), kind='elev', frame=False, title='TOWER PROFILE (concentric; app axis is 7.2 m S)')
    b1 = body_outline(1)
    V.line([(-r, h) for r, h in b1], 'inf', lw=0.9); V.line([(r, h) for r, h in b1], 'inf', lw=0.9)
    b2 = [(r * S2, fam2(h)) for r, h in b1 if fam2(h) > 13]
    V.line([(-r, h) for r, h in b2], 'unk', lw=0.6); V.line([(r, h) for r, h in b2], 'unk', lw=0.6)
    A = D.app_tower()
    pa = [(r, h) for r, h in A['profile']] + A['cab']['floor'] + A['cab']['glass'] + A['cab']['roof']
    V.line([(-r, h) for r, h in pa], 'app', lw=0.9); V.line([(r, h) for r, h in pa], 'app', lw=0.9)
    V.line([(-30, 0), (30, 0)], 'pub', lw=0.6)
    V.text((14, 66), 'spec (rim 67.36, D 14.3) [inf]', 'inf', fs=4.2, ha='left')
    V.text((14, 61), 'family 2 (rim 64.0, D 14.5)', 'unk', fs=4.2, ha='left')
    V.text((14, 56), 'app today (buildTower)', 'app', fs=4.2, ha='left')
    V.scalebar(y_mm=3, nice=20)
    # ---------------- ITB roof profile (diagram)
    ax3 = fig.add_axes([(BORDER + 326) / pw, (BORDER + 22) / ph, 160 / pw, 150 / ph])
    I = __import__('draw_itb')
    us = np.linspace(-I.HL, I.HL, 400)
    ax3.plot(us, [I.crown(u) for u in us], color=TAGS['obs']['c'], lw=1.0, label='spec: eave profile + crown [obs / pub DOF]')
    G = D.app_great_hall(); ss = np.linspace(-G['L'] / 2, G['L'] / 2, 200)
    ax3.plot(ss, [G['top'](s) for s in ss], color=TAGS['app']['c'], lw=1.0, ls=TAGS['app']['ls'], label='app: greatHall top(s)')
    ax3.plot([-131.06, 131.06], [1, 1], color='k', lw=2, alpha=0.4, label='published 860 ft length')
    ax3.plot([-I.HL, I.HL], [3, 3], color=TAGS['obs']['c'], lw=2, alpha=0.5, label='NAIP 252.9 m length')
    ax3.plot([-G['L'] / 2, G['L'] / 2], [5, 5], color=TAGS['app']['c'], lw=2, alpha=0.5, label='app 237.4 m length')
    ax3.set_xlim(-140, 140); ax3.set_ylim(0, 46)
    ax3.set_xlabel('u along the roof axis (m, + towards BA-A)', fontsize=4.8); ax3.set_ylabel('height above grade (m)', fontsize=4.8)
    ax3.tick_params(labelsize=4.4); ax3.grid(color='#e5e5e5', lw=0.4); ax3.legend(fontsize=4.0, loc='lower center', frameon=False)
    ax3.set_title('ITB hall roof along its axis (diagram; vertical exaggeration)', fontsize=5.4, loc='left')
    for s_ in ax3.spines.values(): s_.set_linewidth(0.4)
    S.note('App values read from js/live/terminals.js (buildTerminals, greatHall, buildTower), js/live/airport.js (STRUCT_H_BY_NAME) and '
           'data/sfo_buildings.json part heights (tools/build_terminal_parts.py PIER_H 14.6 m, HALL_H). Nothing in js/ or data/ was changed.')
    S.note('Deltas are app minus spec at the spec value; where the spec is a range, see the dot plot. The tower spec is itself uncertain by '
           'the two height families (BT-02): the app is lower than both.')
    S.note('Biggest gaps: ITB roof 13.6 m too low and 35 m too far east; tower cab 20.3 m wide (spec 14.3-14.75) and 5 m too low; every '
           'domestic pier at 14.6 m (measured 7.2-19.0); Superbay 7 m and RCC 6-8 m off; the MOC hangars are missing.')
    return S.finish()
