"""Manifest entry "domestic" of data/buildings3d/manifest.json, written by tools/blender/build_domestic.py (merged under a
file lock; the other asset groups own their keys) and extended by tools/blender/render_domestic.py (renders). Lists, per the
owner's rules: the source tag of every dimension (DIMENSIONS, from the dom_geom constants and the sheets), the polygon counts
and draw calls per LOD, the texture sizes, what is inferred / unknown / not modelled, the open conflicts, the plausibility
findings and the verification summary (tools/blender/verify_domestic.py). No bpy.
"""
import fcntl
import json
import os

import dom_geom as G

D, DD = G.D, G.DD
FT = G.FT
ROOT = G.ROOT
DATA = os.path.join(ROOT, 'data', 'buildings3d')


def _r(v):
    return round(float(v), 3)


def dimensions():
    """per-dimension value, tag and source (the 3-D asset uses exactly these)."""
    H, HR = G.H, G.H_RANGE
    lv = DD.T3_LV
    d = []

    def add(k, v, tag, src, rng=None):
        e = dict(key=k, value=v if isinstance(v, str) else _r(v), tag=tag, source=src)
        if rng is not None: e['range'] = rng
        d.append(e)
    add('BA-B outer roof edge height', H['B'], 'obs', 'spec bab.h_roof (two-epoch NAIP, south half; north half inf)', HR['B'])
    add('BA-B raised centre band height', H['B_band'], 'obs', 'spec bab.h_roof_central (2020 step shadow + parallax; low)', HR['B_band'])
    add('BA-B band ESE edge (airport-grid s)', G.BB_S_E, 'obs', 'dom_bab_band.json (2020 edge, sd 0.13 m)')
    add('BA-B band WNW edge (airport-grid s)', G.BB_S_W, 'obs/inf', 'dom_bab_band.json (2024 wall band t -1150..-960; carried south inf)')
    add('BA-B band extent t', f'{G.BB_T_S:.0f} .. {G.BB_T_N:.0f}', 'obs', 'dom_bab_band.json (step shadow at every 2-m station)')
    add('BA-B outer roof edges (s, south half)', f'{DD.BAB_OUTER_S[0]} / {DD.BAB_OUTER_S[1]}', 'obs', 'spec bab.roof_edges: ESE +2.27 / WNW -1.66 m from the level-2 outline')
    add('BA-B roof wells depth below the deck', G.WELL_D, 'unk', 'placeholder (not measured); positions obs dom_bab_roof.json')
    add('BA-C roof height', H['C'], 'obs', 'spec bac.h_roof (single face, assumed k24; low)', HR['C'])
    add('BA-D head roof height', H['D'], 'obs', 'spec bad.h_roof (low)', HR['D'])
    add('BA-D roof edges from the outline (ESE / WNW)', '+2.40 / -1.36', 'obs', 'spec bad.roof_edges')
    add('BA-D drums: centres, radius 9.6', 'BAD_DRUMS_IMG less the D relief', 'obs (position) / inf (relief)', 'draw_domestic BAD_DRUMS_IMG (NAIP)')
    add('BA-D drum top', DD.BAD_DRUM_TOP, 'inf', 'roof + ~4.7 m (crescent 2.75 m / lean 0.58; obs low)')
    add('BA-E raised centre (tapered fascia) height', H['E'], 'obs', 'spec bae.h_roof', HR['E'])
    add('BA-E lower side roofs', H['E_flank'], 'inf', 'fascia - BAE_STEP 3.0 (photo a1, low)')
    add('BA-E flank / overhang', f'{DD.BAE_FLANK} / {DD.BAE_OVER}', 'inf', 'draw_domestic BAE_FLANK / BAE_OVER (photo a1, low)')
    add('BA-E width', 42.9, 'inf', 'research 5.3 (outline less ~2 m WNW)')
    add('BA-F NE arm roof height (hub, NW arm drawn at it)', H['F'], 'obs', 'spec baf.h_roof_ne_arm (DOF 10.36 m); hub band 10.4-12.1 obs low', HR['F'])
    add('BA-F roof edges from the outline (ESE / WNW)', '+1.83 / -1.15', 'obs', 'draw_data.dom_true_edges (BD-01 / BD-02: 27.0 m arm); see conflicts')
    add('BA-F lantern', 'octagon 19.4 / 13.4 m, centre ~3.3 m E of the hub centre', 'obs (size) / inf (centre)', 'draw_domestic BAF_LANTERN_APO, baf_lantern_centre(), dom_baf_hub.json')
    add('BA-F lantern rise', G.LANTERN_RISE, 'unk', 'review r1: minimal 1.0-m glazed upstand (conservative); the NAIP 2020 cast shadow '
        '(<= 5.2 m) only bounds it', [0.0, G.LANTERN_RISE_BOUND])
    add('BA-F NW-arm monitor rise', 2.5, 'unk', 'placeholder; width ~8 m obs NAIP')
    add('T3 levels above L1 (L2 / L3 / R2 / T3W parapet / R3)', f"{lv['L2']:.2f} / {lv['L3']:.2f} / {lv['R2']:.2f} / {lv['PARAPET_W']:.2f} / {lv['R3']:.2f}",
        'pub (levels) / inf (subtraction)', 'CDR 95 % CD p.28-29 (Oct 2023); T3 L1 at the apron [inf]')
    add('T3W roof deck', H['T3W'], 'inf', 'parapet - 3\'-6" (CDR field wall)')
    add('T3W airside window stack', '10 ft glass + 2 ft band + 10 ft glass from L3', 'pub', 't3w.wall_field')
    add('T3W landside bands (spandrel 1.7 / glazing 5.8 above L2)', 'proportions', 'inf (low)', 'CDR p.23 rendered section (no dimensions)')
    add('T3E roof', H['T3E'], 'inf', 'R2 "top of roof at high point" read as the T3E roof')
    add('T3E penthouse top / extent', f"{H['T3E_pent']:.2f} / bearings {DD.T3E_PENT_BRG}, set back {DD.T3E_PENT_SETBACK} m, 25.5 m deep",
        'inf (top R3) / obs low (extent NAIP)', 'BD-03 view 3')
    add('departures curb above the apron (T1 / T2)', G.CURB, 'inf',
        'close-out r3 (buildings-14): = the published T3 L1 -> L2 rise, 16 ft (CDR 95 % CD p.28-29) [pub at T3]; the domestic departures '
        'loop is ONE connected roadway (the 17 OSM ways named Departures, layer 1, that roadways.glb anchors form one component by shared nodes) '
        'serving the T1 / T2 / T3 curbs -> the same level at T1 / T2 [inf]; not measured there (NAIP relief / shadow of the deck edge '
        'inconclusive at 0.6-m GSD: ~0.5 m of band per metre of height). Soffit over the at-grade roads under the loop = 4.73 - deck depth '
        '(roadways.glb 1.2 m [inf]) = 3.53 m: below the 4.6-m design clearance (see conflicts)')
    add('T1 Center wall head / tier transom / canopy soffit (above the curb)', f'{DD.T1_HEAD} / {DD.T1_SPLIT:.2f} / {DD.T1_CANOPY}', 'inf (photo d1, low)', 'BD-03 view 1')
    add('T1 Center roof height', H['T1'], 'unk', 'curb [unk] + wall head 13.0 [inf]; spec t1c.h_roof: none')
    add('T1 landside facade set-back from the trimmed curb line', G.T1_CANOPY_D, 'inf', 'canopy depth; NAIP 2024 PV roof edge 3-6 m inside the trimmed edge')
    add('T2 hall height', H['T2'], 'unk', 'curb [unk] + 12.0 (BD-03 view 2 placeholder)')
    add('T2 landside face (close-out r3, buildings-2)', 'x = %.3f + %.4f z (z %.0f-%.0f); elsewhere the departures deck edge + %.2f m'
        % (G.T2_EDGE_LINE[0], G.T2_EDGE_LINE[1], G.T2_EDGE_Z[0], G.T2_EDGE_Z[1], G.T2_SIDEWALK), 'obs (NAIP 2024 relief-corrected roof edge) / inf (corners)',
        'lean-free coping line, 59 rows, rms 0.06 m (relief for the 16.88-m placeholder: +1 m of roof -> 0.54 m west); NAIP 2020 within 1.5 m; '
        'the old SFO Museum face was 17-18 m west over the departures roadway; hall area -%.0f m2' % G.T2_CUT_M2)
    add('T2 departures sidewalk (deck edge -> wall)', G.T2_SIDEWALK, 'obs', 'NAIP 2024 roof edge minus OSM deck edge (256787747, 3 x 3.6 m): '
        'median 5.85, p10 5.76, p90 6.63 m; deck at the curb level, 0.6 m thick, overlapping the roadway deck by 0.3 m (%.0f m2)' % G.T2_SIDEWALK_POLY.area)
    add('T2 curb canopy (depth / soffit)', '%.1f / %.2f' % (G.T2_CANOPY_D, G.T1_CANOPY_H), 'obs low / inf',
        'depth: NAIP 2024 / 2022 teal glass band, outer edge lean-corrected at ~9.2 m; soffit as T1 (curb + 4.0, photo d1)')
    add('T2 - garage connector over the departures roadway (soffit / top)', '%.2f / %.2f' % G.T2_LINK_Z, 'inf (level unk)',
        'plan: the T2 outline courtyard connector (SFO Museum) extended along its axis to the moved face, cut at the Central Parking Garage '
        'outline [obs]; floor at the garage Level 3 placeholder (2/5 of 81 ft) so that the soffit clears the departures deck by 4.7 m [inf]')
    add('pier / hall footprints', 'SFO Museum level-2 outlines (+ measured roof edges)', 'obs', 'data/sfo_airport.json (CDLA-Permissive-1.0)')
    add('concourse (departure) floor = the app bridge level per pier (close-out r3 fix 2)',
        ' / '.join('%s %.2f' % (k, G.PIER_LEVEL[k]) for k in 'BCDEF'),
        ' / '.join('%s %s' % (k, G.PIER_LEVEL_TAG[k]) for k in 'BCDEF'),
        'js/live/gates.js DEPARTURE_LEVELS (tools/blender/app_bridges.json, node tools/blender/app_bridges.mjs): B 5.4 inferred, C 3.2 '
        'inferred (the BA-D photo-a1 layout on the 7.2-m roof), D 3.65 photo a1 (low), E / F 4.88 T3 L2 [pub]; door frames, vestibules, '
        'overhang / drum notches and bridge-entered elevated parts follow the walkway floor at each door')
    add('BA-C / BA-D facade bands (close-out r3 fix 2)', 'sill band %.3f-%.3f, glazing %.3f-%.3f of the roof edge: BA-D %.2f-%.2f-%.2f m, '
        'BA-C %.2f-%.2f-%.2f m' % (G.A1_D_RATIO[0], G.A1_D_RATIO[1], G.A1_D_RATIO[1], G.A1_D_RATIO[2],
                                   G.A1_D_RATIO[0] * G.H['D'], G.A1_D_RATIO[1] * G.H['D'], G.A1_D_RATIO[2] * G.H['D'],
                                   G.A1_D_RATIO[0] * G.H['C'], G.A1_D_RATIO[1] * G.H['C'], G.A1_D_RATIO[2] * G.H['C']),
        'obs (low, BA-D) / inf (BA-C)', 'photo a1 at the BA-D near end (rows 763.5 / 773.5 / 790.5 / 795.5 / ~812 px, camera-independent '
        'ratios); BA-C the same layout (too small on a1), as gates.js DEPARTURE_LEVELS.C')
    add('facade bands (service / spandrel / glazing / panel)', 'STYLES in dom_geom.py', 'inf / unk', 'materials pub where described (bab.glazing, bae.facade, t1c, t3w, t3e)')
    add('mullion module / fins', f'{G.MULL} m / {G.FIN[0]} x {G.FIN[1]} m', 'inf', 'no source')
    add('roof slab / parapet', f'{G.ROOF_THK} / {G.PARAPET}', 'inf', 'measured heights are the roof EDGES (coping top)')
    add('PV rack blocks', 'dom_pv.json', 'obs (extent, NAIP 2024 +-1 m) / inf (height 0.35-0.75 m)', 'tools/blender/dom_pv.py')
    add('elevated sky-bridge / connector parts', f'{G.INNER_Y0} - {G.INNER_TOP}', 'unk', 'the app convention (tools/build_terminal_parts.py walkway y0 6.0 / h 10.5)')
    add('elevated parts entered by a bridge walkway (B10 / B11 / B11S / B15 / B16 at %.2f, F22 at the BA-F level): underside' % G.WALK_Y0_BRIDGE,
        'walkway floor inside the part %+.1f m' % G.VEST_DZ[0], 'inf',
        'review r1: the vestibule floor so that the app walkway (floor - 0.3 .. + 3.0) runs inside the part; per bridge from '
        'app_bridges.json since close-out r3 fix 2')
    add('Courtyard 3 Connector office block: footprint', f'T2 outline NW end west of s {G.C3C_S_EAST:.1f} ({G.C3C_POLY.area:.0f} m2)', 'obs',
        'SFO Museum T2 outline; the cut through its two outline jogs; NAIP 2024 imaged east roof edge less the relief on the same line')
    add('Courtyard 3 Connector office block: height', G.C3C_H, 'inf', 'HOK: "Above the connector, a six-story office building" [pub] '
        '-> >= 33.3 m; NAIP 2024 relief 12.9 m / 0.379 = 34.0 m; photo a1 (estimated camera) ~35 m; the conservative end', [32.0, 36.0])
    add('NAIP 2024 lean (east, m/m) at world x', 'k24.n = 0.392 + 0.000432 (x + 800), / sin 117.83', 'inf',
        'linear fit through the four two-epoch pier values (B / D / E / F, within 0.005); used for the C3C only')
    add('PV rack tables (rows / tables with their aisles)', 'tools/blender/dom_roofobs.json pv_tables', 'obs (extent, NAIP 2024 +-0.5 m) / inf (modules)',
        'tools/blender/dom_roofobs.py (review r1: discrete tables instead of one plate per block)')
    add('rooftop mechanical units', 'tools/blender/dom_roofobs.json units', 'obs (extent, NAIP 2024 +-0.7 m) / inf (height 1.5 / 2.2 / 3.0 m by size)',
        'tools/blender/dom_roofobs.py: compact dark objects with a shadow on their NNE side')
    add('bridge doors / vestibules / bulkheads', 'at the walkway attach points (data/sfo_stands.json); frame %+.1f .. %+.1f m, vestibule %+.1f .. '
        '%+.1f m about the app walkway floor at the door' % (G.DOOR_DZ + G.VEST_DZ), 'inf',
        'door 2.6 x 3.0 walkway section (gates.js); floors per door from app_bridges.json (close-out r3 fix 2: 0 bulkheads - the walkway '
        'tops at BA-C 6.20 / BA-D 6.65 m stay under the 6.40 / 7.69 m slab undersides)')
    add('roof colours', 'NAIP 2024 median per building, capped at sRGB 215', 'obs (low) / inf (cap)', 'build_domestic.naip_colours')
    # review round 2
    add('C3C office curtain wall (review r2)', f'{G.C3C_STOREYS} storeys x {G.C3C_STOREY} m from {G.C3C_OFFICE_Z0:.1f} m; storey-height panes, '
        'staggered mullions (widths 1.2-4.5 m, new sequence per storey), light frames, very dark green glass', 'pub (6 storeys, dynamic glazing) / '
        'obs (rhythm, colours: photo a1, low) / inf (storey height, pane widths)', 'HOK; photo a1 8x zoom; dom_tex.c3c_colour')
    add('C3C rooftop penthouse (review r2)', f'u {G.C3C_PENT_U[0]}-{G.C3C_PENT_U[1]} / w {G.C3C_PENT_W[0]}-{G.C3C_PENT_W[1]} m on the NNE-face '
        f'frame ({G.C3C_PENT_U[1] - G.C3C_PENT_U[0]:.1f} x {G.C3C_PENT_W[1] - G.C3C_PENT_W[0]:.1f} m); top {G.C3C_PENT_TOP:.1f} m', 'obs (low)',
        'photo a1 (23-77 % of the NNE face, 4.4-5.3 m visible above the roof edge); NAIP 2024 (its imaged WNW wall band, FWHM 2.5 m / lean '
        '0.438 = 5.7 m above the deck); the 8 C3C PV tables stand on it (NAIP)')
    add('C3C penthouse louvre band (review r2)', f'u {G.C3C_LOUVRE_U[0]}-{G.C3C_LOUVRE_U[1]} m, {G.C3C_LOUVRE_Z[0]:.1f}-{G.C3C_LOUVRE_Z[1]:.1f} m',
        'obs (low)', 'photo a1 (dark band on the penthouse NNE wall)')
    add('BA-E tip end wall glazing (review r2)', 'dark base 0-2.0 m, clear glass 2.0 m to the wall head (83 % of the wall)', 'obs (low)',
        'photo a1 profile at the end wall (glass 746-790 px of a 736-~802 px wall, x 1335-1450)')
    add('BA-E plate PV arrays added (review r2)', 'tools/blender/dom_pv_r2.json (8 arrays, 484 m2)', 'obs (extent, NAIP 2024 +-0.5 m) / inf (modules)',
        'tools/blender/dom_pv_r2.py: the WNW-half arrays dom_pv.py merged with the edge shadow')
    add('walls facing the tower base building (review r2)', 'full height, 0.3 m off the IBF; flashing over the gap at min(top, %.2f m), '
        'a %.2f-m joint at the IBF wall' % (G.TOWER_Z1, G.TOWER_JOINT), 'inf', 'the flashing height: the LOWEST IBF roof over the tower families '
        f'({G.TOWER_IBF_ROOFS} m, manifest.json#tower anchors / anchors_f1 / anchors_f2) less 0.10 m (below the parapet of either family)')
    add('facade notches around the app rotunda drums (review r2)', f'radius max(1.5, min(2.45, rotunda_max_r - 0.25)) + {G.DRUM_CLEAR} m around '
        'data/sfo_stands.json rotunda', 'inf', 'js/live/gates.js drum radius rule (the largest drum the app can draw); 9 facades notched '
        '(B10, D4, D5, D14, D15, D16, E6, E9, E11); door surrounds / vestibules within reach of a drum (36 doors) clipped or left out')
    add('T1 sign sizes (review r2)', 'line 1 1.41 m (incl. descender) x 14.0 m at 14.03 m; line 2 cap 0.79 m, disc 1.10 m at 12.10 m',
        'obs (low)', 'photo d1 with the solved camera (render_domestic.D1_SOLVE); font Liberation Sans Bold x 0.93 [inf]')
    return d


INFERRED = [
    'roof slab 0.8 m below the measured roof edge, parapet / coping 0.6 m (the measured heights are the roof EDGES)',
    'facade bands: apron-level service wall 0-4.6 m, dark spandrel, concourse glazing from 5.4-5.6 m (the bridge floor) to 7.2-11.6 m per '
    'pier, light panel above; glazing materials published where described (BA-B electrochromic, BA-E clear + grey frit, T1 fritted '
    'two-tier, T3W ACM + fritted IGU, T3E grey frit / platinum panels), band heights inferred',
    'mullion fins every 1.5 m on the glazed bands (0.06 x 0.18 m), T1 landside irregular rhythm 1.2-2.4 m (schematic of the published '
    '"Redwood trees" pattern)',
    'BA-B: north-half outer roof edges carried from the south half (offsets from the outline); roof wells 3 m deep (unk) with planting; '
    'well bridges 0.6 m slabs; skylight grids raised 0.3 m',
    'BA-E stepped section (raised plate with a tapered edge 1.5 m over a clerestory, lower flanks 4.4 m, step 3.0 m) from photo a1',
    'BA-F lantern eccentric (~3.3 m E), a minimal 1.0-m glazed upstand (rise unknown, bound 4.6 m); NW-arm monitor 2.5 m rise; hub and '
    'NW arm at the NE-arm height',
    'Courtyard 3 Connector office block (review r1): 33.0 m (six published office storeys above the connector, NAIP relief, photo a1); '
    'review r2: six 3.8-m office storeys of storey-height panes with staggered mullions (pane widths, storey height inf; rhythm / colour obs '
    'photo a1), the connector levels below as the piers; the rooftop penthouse 5.0 m above the roof edge with a louvre band [obs low]',
    'review r2: facades notched (radius + 0.1 m) around the largest rotunda drum the app can draw at a bridge, roof notched where its '
    'underside is below the drum top; door surrounds / vestibules clipped there; the walls facing the tower base building full height '
    '0.3 m off it, a coping flashing over the gap at min(top, 13.03 m) with a 0.15-m joint at the IBF wall',
    'review r2: BA-E tip end wall glazed from 2.0 m (dark base below) [photo a1 profile, low]',
    'rooftop units: boxes on the decks at the NAIP extents, heights 1.5 / 2.2 / 3.0 m by plan size (< 12 / < 50 / >= 50 m2), light '
    'metal casings; PV: rack tables 0.35-0.75 m above the deck at the NAIP table extents, modules in the PV tiles',
    'BA-B electrochromic glass in four per-pane tint states (24 x 6 m tile); T1 clear glass under the canopy mid-grey (the lit hall '
    'seen through, photo d1); the T1 canopy light, uncoated laminated glass',
    'BA-D drums ~4.7 m above the head roof; linear skylights 0.6 m',
    'T1 Center: curb canopy 4.0 m deep at curb + 4.0 m (glass top, aluminium edge, brackets), departures sidewalk deck at the curb; the '
    'landside facade 4.0 m behind the trimmed curb line; three 9 x 11 m skylights; the sign "Harvey Milk Terminal / Terminal 1" on the '
    'west run (photo d1; size / font inf)',
    'T3: L1 at the apron; T3W deck = parapet - 3\'-6"; T3E roof at R2; penthouse at R3; T3W / T3E split along the AirTrain connector gap',
    'airside links at grade between halls and piers: the lower adjoining height',
    'bridge attachment: a door surround (jambs + head around the 2.6 x 3.0 m walkway section) and a dark leaf on the facade at every '
    'bridge; a vestibule box from the facade to the app walkway start where that lies outside the facade (max 2.6 m); a bulkhead above '
    'the roof where the roof edge is below the walkway head (BA-C, BA-D); the BA-D overhang notched at the doors',
    'roof colours from NAIP 2024 (white membranes saturate; base colour capped at sRGB 215); facade colours our reading of the photos',
]

UNKNOWN = [
    'T1 Center and T2 hall heights (nothing published or measured): T1 = curb placeholder + 13.0 m wall head (photo d1), T2 = curb + 12 m',
    'the departures-curb height above the apron (T1 / T2): 4.88 m = the published T3 L1 -> L2 rise carried along the continuous departures '
    'loop [inf] (close-out r3); not measured at T1 / T2',
    'the T2 - garage connector level (close-out r3): modelled 9.43-14.38 m (clearance over the departures deck); NAIP 2024 shows a ~4.5-m '
    'shadow band north of the crossing at x -765 (sun elevation 72.5 deg, azimuth 186.6 deg), which would put its top near 24 m, i.e. at the '
    'AirTrain T2 station level (SFO Museum "Terminal Two AirTrain Station" 1763588561 reaches x -743.8, the T2 wall) - two structures stacked, '
    'or a higher connector landing on a taller part of T2, cannot be told apart from NAIP; a photo of the T2 curb would settle it',
    'the T3 project datum (L1 drawn at the apron); the T3 East landside facade (drawn with the published T3E materials, positions inf)',
    'the BA-B roof-well depth and skylight heights; the BA-F lantern (bound <= 4.6 m, modelled 1.0 m) and monitor rises; the BA-B '
    'north-half outer roof height',
    'the Courtyard 3 Connector height (modelled 33.0 m, range 32-36 m); its rooftop penthouse is modelled since review r2 from photo a1 and '
    'the NAIP 2024 wall band [obs, low] (top 38.0 m, +-1 m); the office storey height and pane widths',
    'the T1 Center roof profile: photo d1 shows PV rows above the landside coping while its solved camera is 2.8 m BELOW the coping, so the '
    'roof rises behind the landside edge (or the edge is lower than the hall roof); modelled flat at the 17.88-m placeholder [unk]',
    'rooftop unit heights and types (extents measured; NAIP 2024 resolves only compact dark units with a shadow; light units on light '
    'membranes and units under 4 m2 are missed); no BA-B reference photo was found with an open licence (Wikimedia Commons searched '
    '2026-11-05), so the BA-B facade materials remain unverified',
    'bay / mullion modules, gate-room glazing extents, the apron-level facades (service band only), parapet heights',
    'the elevated sky-bridge / pod parts (app convention 6.0-10.5 m; 4.9-10.5 m where a bridge walkway enters, review r1)',
    'which T3W state to model (under construction 2024-2029; the May 2026 change adds an airside storey): the asset shows the 95 % CD '
    'parapet 66\'-0" massing without the new storey',
]

NOT_MODELLED = [
    'courtyard links (pedestrian bridges over the curbside roadways to the garage / AirTrain stations) and the links that cross the '
    'AirTrain guideway: no known level (the app keeps its own parts there) - except the T2 - garage connector, modelled since close-out r3 '
    'because the moved T2 face left the app part 19 m short of the building (level inf, see unknown)',
    'the AirTrain guideway / stations and the garages (landside asset), the tower (tower asset), the ITB (itb asset)',
    'T3W penthouses (positions / heights not dimensioned); rooftop equipment that NAIP 2024 does not resolve (see unknown)',
    'interiors (glass is opaque; no interior lighting)',
    'F22: its walkway starts inside BA-F; no pod part (the five BA-B pod bridges B10 / B11 / B11S / B15 / B16 now get door surrounds on '
    'the lowered pod parts, review r1)',
    'signage other than the T1 Center landside sign (gate numbers are drawn by the app on the bridges / stands)',
]

CONFLICTS = [
    dict(item='BA-F ESE roof edge', model='the drawn lean-free line (draw_data.dom_true_edges, BD-01; BD-02 draws the NE arm 27.0 m '
         'between the lines): 1.83 m outside the level-2 outline along the face', other='spec baf.roof_edges note / README round 2: '
         '"ESE on the outline (+0.01 / -0.02)"', note='that note was measured at the line END points, where the line meets the '
         'outline\'s corner jogs; at 25 / 50 / 75 % of the line it is 1.83 m outside (checked 2026-11-05). The 3-D follows the drawn '
         'line; the spec note should be corrected by the drawings group',
         status='resolved (spec note corrected, close-out r3)',
         resolution='tools/buildings/spec_domestic.json baf.roof_edges note corrected 2026-11-07 (and build_spec_domestic.py): the ESE '
                    'line is 1.83 m outside the level-2 outline at 10-90 % of its length, on it only at its end points'),
    dict(item='T1 Center landside face', model='on the measured roof edge: the app\'s trimmed curb line (OSM carriageways) less 4.0 m',
         other='BD-03 view 1 develops the face along the SFO Museum outline (94.1 + 43.6 + 93.8 m)',
         note='NAIP 2024 shows the curb roadway and vehicles INSIDE the SFO Museum outline there, and the PV roof edge 3-6 m inside the '
              'trimmed edge (overlay checked 2026-11-05); heights follow BD-03'),
    dict(item='T2 landside face (close-out r3, buildings-2)', model='on the NAIP 2024 relief-corrected roof edge (x = -811.96 + 0.3063 z, '
         'z 168-254) and 5.85 m off the departures deck edge elsewhere; the departures sidewalk and a 5.4-m glass curb canopy in front, the '
         'T2 - garage connector extended to it', other='BD-03 view 2 / the SFO Museum level-2 outline: the T2 face 17-18 m further west, over '
         'the departures roadway (roadways.glb cut its deck at the T2 body, 1,406 m2, as an interim)',
         note='NAIP 2024 / 2022 show traffic, the sidewalk and the canopy inside the outline; NAIP 2020 images the roof edge within 1.5 m of '
              'the 2024-derived line; the SFO Museum AirTrain T2 station polygon (1763588561) ends at x -743.8, on the new wall line'),
    dict(item='app rotunda drums under the BA-F overhang (close-out r3, buildings-4)', status='resolved (3-D)',
         model='F7 / F8 L1: the drum discs lie ~1.05 m inside the BA-F footprint ring but only under the ESE roof overhang: soffit 9.69 m, '
               'drum top 8.55 m -> 1.14 m clear; facades >= 0.1 m outside the largest drum; F8 L1 tunnel 1 (all poses) >= 1.58 m below '
               'the soffit; D3 L1 facade 0.19 m clear of its drum (verify_domestic_r2.drum_overhead, close-out r3 dump of the gates.js solids)',
         other='integration.json footprint rings are plan-only (the -1.06 / -1.05 / -0.03 m overlaps of the round-3 consolidator)',
         request='integration: carry the height band of the overhang (soffit 9.69 m above the apron) in the footprint tiers (integration-5) '
                 'so plan tests do not read the overhang as a wall',
         update_fix2='close-out r3 fix 2: at the per-pier levels (gates.js DEPARTURE_LEVELS F 4.88) the F7 / F8 L1 rotunda floors are '
                     '4.73 / 4.74 m (tools/blender/app_bridges.json), drum tops 8.03 / 8.04 m: 1.66 / 1.65 m under the 9.69-m soffit '
                     '(verify_domestic_r2.drum_overhead, now per drum from its Hr and counting every face over the disc)'),
    dict(item='departures loop soffit over at-grade roads (close-out r3, buildings-14)', status='open (listed by integration; owner question)',
         model='curb 4.877 m = the published T3 L1 -> L2 16 ft carried along the continuous loop [inf]; roadways.glb deck top 4.73, depth '
               '1.2 m [inf] -> soffit 3.53 m over at-grade roads. integration.json (7 Nov 08:01Z) plausibility.conflicts "vertical clearance '
               'over an at-grade road (< 4.6 m)": 26 roads, 753 m, min 3.53 m at (-940.9, 429.6) - OSM 35157057, 38854912, 38855195, '
               '256787748, 370279555, 370279574, 370279581, 370279585, 701209939, 701476986-701476994 (9), 701476996, 739683506, 1179696687, '
               '1205479970, 1230759557, 1274606309, 1274607795, 1274827440 (the 10 crossings this track listed in close-out r3 are among them)',
         other='4.6 m design clearance (Caltrans HDM 309.2) enforced elsewhere by the roadway solve',
         note='raising the curb to clear 4.6 m (deck top >= 5.8 m) would contradict the published T3 L2 at the T3 curb; with a published '
              '16-ft rise between the stacked arrivals / departures levels the real clearance is 16 ft - curb step - deck depth (~3.8-4.0 m '
              'for a 0.75-0.9 m slab): the stacked arrivals roadway is lower-clearance by design (a posted clearance sign photo would settle '
              'it); integration now lists them (R3.2 done, close-out r3 fix 2 updated this entry to its 26-road list); DECK_DEPTH at the '
              'anchored loop and the posted clearance stay open (owner question)'),
    dict(item='T3W parapet', model='16.76 m = 66\'-0" - T3 L1 11\'-0" (BD-02 / BD-03)', other='spec t3.heights_above_L1 16.99 m '
         '(66\'-0" - T3W L1 10\'-3")', note='datum choice; 0.23 m'),
    dict(item='BA-C / BA-D roofs vs the app concourse floor 5.4 m (review r2 finding 5)',
         status='resolved (close-out r3 fix 2: gates.js DEPARTURE_LEVELS C 3.2 / D 3.65, domestic rebuilt to them)',
         resolution='js/live/gates.js DEPARTURE_LEVELS (bridges close-out r3): BA-C 3.2 m [inf: this BA-D layout on the 7.2-m roof], BA-D '
                    '3.65 m [obs, low: photo a1, the evidence below]. The domestic asset takes every bridge-attachment height per door from '
                    'the app walkway floor (tools/blender/app_bridges.json): the 23 bulkheads and the BA-D overhang notches are gone (walkway '
                    'tops BA-C 6.20 / BA-D 6.65 m under the 6.40 / 7.69 m slab undersides), door frames / vestibules / drum notches follow '
                    'the walkways, and the BA-C / BA-D facade bands follow the photo a1 ratios (glazing 0.443-0.794 of the roof edge); '
                    'verify_domestic_r2 walk / plausibility_bac_bad',
         model='BA-C roof edge 7.20 m (deck 6.60, slab underside 6.40) and BA-D 8.49 m (deck 7.89, underside 7.69) kept as measured '
               '[obs, low]; 9 BA-C bulkheads (top 8.70 m, 1.50 m above the BA-C roof edge) and 14 BA-D bulkheads (top 9.49 m, 1.00 m above '
               'its roof edge) enclose the app walkways where they reach above the roof; the BA-D overhang notched at the doors',
         other='js/live/gates.js DEPARTURE_LEVEL 5.4 m [inf] for every pier: walkways 5.15-8.45 m',
         numbers=dict(BA_C=dict(deck_m=6.6, clear_floor_to_deck_m=1.2, clear_under_0p8m_roof_structure_m=0.4),
                      BA_D=dict(deck_m=7.89, clear_floor_to_deck_m=2.49, clear_under_0p8m_roof_structure_m=1.69),
                      needed_m='>= ~3.0 clear (a concourse) + ~0.8 roof structure + 0.6 parapet above the floor'),
         evidence='photo a1 (ratios, camera-independent): at the BA-D near end the facade reads roof edge (763.5 px) / fascia to 773.5 / '
                  'glazing 773.5-790.5 / light sill band to 795.5 / shadowed apron level to ~812: the concourse glazing spans 0.44-0.79 of '
                  'the roof-edge height, and the walkways enter at that band with about one walkway height (~3 m) of facade above them '
                  '(D14 / D15 and the D head). At the measured 8.49 m that puts the BA-D concourse floor near 3.5-3.8 m and the walkway '
                  'top near 6.7 m; with the app floor kept at 5.4 m the roof edge would have to be 10.7-11.7 m, outside the measured '
                  '8.07-8.93 m. BA-C (photo a1 at ~800 m, 2.4 px/m) shows the same layout, too small to measure. The aircraft-scaled '
                  'vertical scale of photo a1 at D11-D16 gives the near-end roof edge 9.1 +- 1 m [low]: consistent with the NAIP value',
         request='bridges / realtime owners: a per-pier departure level for BA-C and BA-D (about 3.5-4.0 m above the apron, to be '
                 'verified against photos with the walkway at the glazing band); domestic then drops the 23 bulkheads, moves the BA-C / '
                 'BA-D concourse glazing to the photo ratios (0.44-0.79 of the roof edge) and lowers its door surrounds',
         note='(the model / other / numbers above describe the round-2 state that this conflict recorded)'),
    dict(item='photo d1 camera vs the AirTrain guideway level', model='d1 camera solved from the facade lines (render_domestic.D1_SOLVE): '
         '10.2 m above the T1 departures curb (15.06 m in the model frame with the 4.88-m curb placeholder)',
         other='landside asset: T1 AirTrain station deck CG_L5 19.75 m [unk placeholder]', note='a car-borne camera ~2.5 m above the deck '
         'would put the deck ~7.6 m above the curb; both the curb and the station level are placeholders - information for the landside '
         'group, no change here'),
]

DEVIATIONS_FROM_SHEETS = [   # review r2 finding 7: what the 3-D asset has that the 2-D set BD-01..03 (2026-11-05 02:42Z) does not show
    dict(item='Courtyard 3 Connector office block (C3C)', sheets='not drawn (tools/buildings/draw_domestic.py has no C3C)',
         model='T2 outline NW end west of s %.1f (%.0f m2) [obs], 33.0 m [inf, range 32-36], six office storeys (glass from 10.2 m), rooftop '
               'penthouse %.0f m2 to 38.0 m [obs low]' % (G.C3C_S_EAST, G.C3C_POLY.area, 585.0), why='review r1 / r2 (photo a1, HOK [pub])'),
    dict(item='rooftop mechanical units', sheets='not drawn', model='31 boxes on 9 decks at their NAIP 2024 extents (dom_roofobs.json), '
         'heights 1.5 / 2.2 / 3.0 m by size [inf]', why='review r1'),
    dict(item='PV rack tables', sheets='BD-01 shows the roofs without PV tables', model='discrete tables inside the NAIP PV blocks '
         '(dom_roofobs.json) + 8 BA-E plate arrays (dom_pv_r2.json, review r2); the 8 C3C tables on the C3C penthouse', why='review r1 / r2'),
    dict(item='BA-E tip end wall', sheets='BD-02: "end wall: full-height recessed glass [obs photo a1]"', model='glazed from 2.0 m above a '
         'dark base (photo a1 profile, review r2) under the plate; the end bay 8 m [inf]', why='review r2 finding 2'),
    dict(item='BA-F hub lantern rise', sheets='BD-02: rise <= 4.6 m (the 2020 shadow bound)', model='1.0-m glazed upstand [unk]', why='review r1'),
    dict(item='pod parts entered by a bridge walkway', sheets='app convention 6.0-10.5 m', model='underside at the entering walkway floor - 0.5 m '
         '(B10 / B11 / B11S / B15 / B16 4.9 m; F22 at the BA-F level)', why='review r1: the app walkways run inside them'),
    dict(item='jet-bridge attachment', sheets='not drawn', model='door surrounds, vestibules and facade notches around the rotunda drums at '
         'the app bridge level of each pier (gates.js DEPARTURE_LEVELS, close-out r3 fix 2; counts in manifest bridges); no bulkheads',
         why='physical fit with the app bridges (js/live/gates.js)'),
    dict(item='tower base building junction', sheets='T2 drawn up to the IBF outline', model='T2 / BA-D / T1 cut 0.3 m off the IBF outline; '
         'their walls facing it full height and a flashing over the gap at min(top, 13.03 m), 0.15-m joint (review r2)', why='review r2 findings 3 / 6'),
    dict(item='T1 Center landside face', sheets='BD-03 view 1 develops it along the SFO Museum outline', model='on the measured roof edge: '
         'the trimmed curb line less 4.0 m (see conflicts)', why='NAIP 2024'),
    dict(item='T2 landside face, departures sidewalk, curb canopy, T2 - garage connector (close-out r3)', sheets='BD-01 / BD-03 view 2: '
         'the T2 face on the SFO Museum outline (47.7-m face, box 12 m, glass 0-7 m above the curb, no canopy, no connector)',
         model='face on the NAIP-measured roof edge (see conflicts), glass 0-7 m above the curb along the whole curb face, sidewalk 5.85 m, '
               'canopy 5.4 m, connector 9.43-14.38 m', why='buildings-2 (NAIP 2024; the departures roadway open to the sky)'),
    dict(item='T1 sign', sheets='BD-03 view 1: signage zone, extent schematic', model='measured sizes / heights from photo d1 (review r2), '
         'Liberation Sans Bold', why='review r2 finding 4'),
]


def entry(build, ver, parts, mats, roof_rgb, info):
    st = build['glb']
    comps = []
    for bld, ps in parts[0].items():
        for p in ps:
            comps.append(dict(node='L0_' + p.name, building=bld, feature=p.feature, src=p.src, spec=p.spec, dims=p.dims, kind=p.kind,
                              lods=[l for l in (0, 1, 2) if any(q.name == p.name for q in parts[l].get(bld, []))]))
    comps.append(dict(node='L0_T1_lettering', building='T1', feature='T1 Center landside sign "Harvey Milk Terminal / Terminal 1"', src='obs',
                      spec=['t1c.landside_facade'], kind='detail', lods=[0]))
    lods = []
    for lod in (0, 1, 2):
        L = st['lods'].get('LOD%d' % lod, {})
        lods.append(dict(lod=lod, node='LOD%d' % lod, switch_m=G.SWITCH_M[lod], tris=L.get('tris'), verts=L.get('verts'), draw_calls=L.get('draw_calls'),
                         ao_atlas='dom_ao_S / dom_ao_N (shared by the LOD0 / LOD1 shell meshes)' if lod < 2 else 'dom_ao_L2'))
    tex = []
    for im in st['images']:
        n = (im['name'] or '')
        px = {'dom_ao_S': 2048, 'dom_ao_N': 2048, 'dom_ao_L2': 1024}.get(n, 512)
        kind = ('AO (occlusionTexture, TEXCOORD_1)' if n.startswith('dom_ao') else 'normal map, tiling, TEXCOORD_0' if n.startswith('dom_n_')
                else 'base colour, tiling, TEXCOORD_0')
        tex.append(dict(name=n, px=[px, px], mime=im['mime'], bytes=im['bytes'], kind=kind))
    mat = {k: dict(rgb_srgb=list(v['rgb']), metallic=v['m'], roughness=v['r'], ior=v.get('ior', 1.5), src=v['src'],
                   normal_tile=v.get('nrm', [None])[0], base_tile=v.get('tex')) for k, v in mats.items()}
    mat['roof_<building>'] = dict(rgb_srgb=roof_rgb, src='NAIP 2024 per building (capped)', note='per-building copies of roof_membrane')
    v = None
    if ver:
        v = dict(tool='tools/blender/verify_domestic.py', report='out/buildings3d/domestic_verify.json (local)', n_checks=ver['n_checks'],
                 n_fail=ver['n_fail'], failed=[r['check'] for r in ver['checks'] if not r['ok']], tolerance=ver['tolerance'],
                 checks=[{k: r[k] for k in ('group', 'check', 'model', 'drawing', 'dev', 'tol', 'ok', 'src')} for r in ver['checks']],
                 plausibility=ver.get('plausibility'), heights=ver.get('heights'))
    doors = info.get('doors', [])
    return dict(
        asset='data/buildings3d/domestic.glb', bytes=st['bytes'], built=build['built'], git=build['git'],
        generator='tools/blender/build_domestic.py (bpy %s, Cycles CPU AO bake); geometry tools/blender/dom_geom.py + dom_mesh.py; '
                  'textures dom_tex.py' % build['bpy'],
        reference='2-D sheets BD-01..03 (docs/drawings/buildings/README.md), drawn by tools/buildings/draw_domestic.py, imported by dom_geom.py',
        spec='tools/buildings/spec_domestic.json (+ dom_bab_band.json, dom_baf_hub.json, dom_bab_roof.json; tools/blender/dom_pv.json)',
        buildings={k: dict(name=v_[0], tag=v_[1]) for k, v_ in G.BLD_INFO.items()},
        frame=dict(id='ltp-nad83-2011', axes='x east, y up, z south, metres from the ARP (js/geo.js)', root_node='domestic',
                   root_translation=[G.OX, 3.0, G.OZ], ground_y=3.0, note='every building node is recentred on its plan bbox centre (its translation)'),
        lods=lods,
        lod_note='LOD groups are siblings under the root: show one per building. LOD0 / LOD1 hold one node per building and kind '
                 '(L<k>_<bld>_shell / _detail / _fins / _pv, extras.building; _fins carry extras.max_dist_m 160: hide them beyond, the '
                 'curtain caps of the glass tiles keep the rhythm): choose the LOD per building from the camera distance to its node '
                 '(the complex spans ~1.3 km). LOD1 shares the LOD0 shell meshes and atlases; LOD2 is one joined node (L2_domestic, '
                 'extras.parts keeps the per-part tags) with its own atlas; since review r1 it keeps the LOD0 outlines, wells, skylights, '
                 'coping recess, rooftop units >= 15 m2, PV tables (tops) and the bridge vestibules / notches / bulkheads (the phone tier '
                 'sees it up close). Phone / far tier: data/buildings3d/domestic_lod2.glb holds the LOD2 subtree alone (same root transform).',
        files=['data/buildings3d/domestic.glb', 'data/buildings3d/domestic_lod2.glb'], lod2_glb=build.get('lod2_glb'),
        textures=tex, materials=mat,
        material_note='glass: coated (IOR 1.9 -> F0 0.096, KHR_materials_ior + KHR_materials_specular), opaque (no interiors); single-sided, '
                      'every face wound outwards; no imagery is used as a texture (NAIP 2024 only for the roof colour numbers); no TANGENT '
                      'attribute (tiling normal maps; the runtime derives the tangent frame)',
        ao=build.get('ao'), naip_colours=build.get('naip_colours'),
        dimensions=dimensions(), components=comps, inferred=INFERRED, unknown=UNKNOWN, not_modelled=NOT_MODELLED, conflicts=CONFLICTS,
        deviations_from_sheets=DEVIATIONS_FROM_SHEETS,
        deviations_note='the 2-D set BD-01..03 is owned by the drawings group (tools/buildings/draw_domestic.py); these 3-D-only items are '
                        'recorded here instead of redrawing (review r2 finding 7)',
        bridges=dict(doors=len(doors), vestibules=sum(1 for d in doors if (d.get('head') or {}).get('kind') == 'vestibule'),
                     nubs=sum(1 for d in doors if (d.get('head') or {}).get('kind') == 'nub'), bulkheads=sum(1 for d in doors if d['low']),
                     notched=sum(1 for d in doors if d.get('notched')),
                     levels={k: dict(h=G.PIER_LEVEL[k], tag=G.PIER_LEVEL_TAG[k],
                                     doors=sum(1 for d in doors if d['stand'][0] == k),
                                     walkway_floor_at_doors_m=[round(min([d['fl0'] for d in doors if d['stand'][0] == k] or [0]), 2),
                                                               round(max([d['fl1'] for d in doors if d['stand'][0] == k] or [0]), 2)])
                             for k in 'BCDEF'},
                     levels_source='js/live/gates.js DEPARTURE_LEVELS via tools/blender/app_bridges.json (node tools/blender/app_bridges.mjs, '
                                   'generated %s; stale inputs: %s)' % (G.AB.load()['generated'], ', '.join(G.APP_BRIDGES_STALE) or 'none'),
                     note='every bridge of data/sfo_stands.json (B-F) gets a door surround where its walkway meets the 3-D facade; where the '
                          'app\'s walkway (js/live/gates.js) starts outside the facade a vestibule closes the gap over the walkway\'s whole width '
                          '(close-out round 4: tools/blender/bridge_head.py; a nub where the end lies inside the facade but its edge passes a '
                          'corner); the walkway-end gap check (tools/blender/walkend_check.py, verify_domestic.py) holds every end <= 0.1 m',
                     walkway_end_gaps=(ver or {}).get('plausibility', {}).get('walkway_end_gaps_summary')),
        integration=dict(replaces='js/live/terminals.js extrusions of the domestic parts of data/sfo_buildings.json (T1 / T2 / T3 halls, '
                                  'Boarding Areas B-F, their walkways)',
                         keep='the courtyard links and guideway-crossing connectors (not modelled here), the app\'s ramp-level complex outline '
                              'for the bridge clearance tests (gates.js uses the SFO Museum outlines, which this asset follows)',
                         exclusions='the tower base building (tower asset) and the ITB outline are cut out / not overlapped (0 m2)'),
        verification=v,
    )


def keep_renders(old, new):
    for k in ('renders', 'render_check', 'renders_updated', 'renders_args', 'renders_note', 'qa', 'validator', 'neighbours', 'review_r1', 'review_r2',
              'closeout_r3', 'closeout_r3_fix2', 'closeout_r4', 'closeout_r5'):       # (close-out r3 fix 2 / r4 / r5: the close-out records survive a rebuild)
        if old and old.get(k):
            new[k] = old[k]
    return new


def merge(update_fn, key='domestic'):
    path = os.path.join(DATA, 'manifest.json')
    lock = path + '.lock'
    os.makedirs(DATA, exist_ok=True)
    with open(lock, 'a') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            cur = json.load(open(path)) if os.path.exists(path) else {}
        except Exception:  # noqa: BLE001
            cur = {}
        cur.setdefault('_about', 'SFO Live 3D building assets (glTF 2.0, built with Blender from the verified 2-D sheets); one key '
                       'per asset group; frame ltp-nad83-2011 (x east, y up, z south, m from the ARP); see docs/research/buildings3d.md')
        cur[key] = update_fn(cur.get(key))
        tmp = path + '.' + key + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(cur, f, indent=1)
        os.replace(tmp, path)
        fcntl.flock(lf, fcntl.LOCK_UN)
    # (the lock file is never deleted: a process waiting on the old inode would otherwise run beside one that created a new one)
    return path


def add_renders(done, args_dict):
    import datetime

    def upd(old):
        old = old or {}
        old['renders'] = {k: v for k, v in done.items() if k not in ('bab_check', 'args')}
        if 'bab_check' in done: old['render_check'] = done['bab_check']
        old['renders_updated'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
        old['renders_args'] = args_dict
        old['renders_note'] = ('Cycles CPU, AgX, OIDN, <= 960 px / <= 64 spp; photo comparison sheets (domestic_cmp_*.png) hold photo '
                               'pixels and stay local (out/ is not committed)')
        return old
    return merge(upd)


def add_review_r1(after_path, before_path=None):
    """manifest.json#domestic.review_r1: the round-1 findings, their dispositions and the probe summaries
    (tools/blender/verify_domestic_r1.py) before / after."""
    import datetime
    A = json.load(open(after_path)); B = json.load(open(before_path)) if before_path and os.path.exists(before_path) else None

    def summ(R):
        return {k: R[k] for k in ('summary_lod0', 'summary_lod2', 'lod2_vs_lod0')} if R else None

    def upd(old):
        old = old or {}
        old['review_r1'] = dict(
            updated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            probe='tools/blender/verify_domestic_r1.py (out/buildings3d/domestic_verify_r1.json, local)', after=summ(A), before=summ(B),
            dispositions=[
                dict(item=1, finding='roofs empty apart from PV; Courtyard 3 Connector missing', status='fixed',
                     note='C3C block 33.0 m [inf] on the T2 outline NW end [obs]; 31 rooftop units (NAIP 2024, dom_roofobs.json) [obs extents, inf heights]'),
                dict(item=2, finding='PV blobs with one texture', status='fixed', note='303 rack tables with aisles (dom_roofobs.json pv_tables)'),
                dict(item=3, finding='BA-B facade uniform / fins alias', status='fixed (unverified look)',
                     note='EC panes in four tint states; _fins nodes with extras.max_dist_m 160 (js/three/buildings3d.js hides them beyond); no open-licence BA-B photo found'),
                dict(item=4, finding='T1 clear glass black, canopy dark line', status='fixed', note='glass_lobby 112/120/122; light uncoated canopy glass'),
                dict(item=5, finding='LOD2 without vestibules / notches / bulkheads', status='fixed', note='bridge attachment at every LOD'),
                dict(item=6, finding='walkways through the 6.0-m floor of the BA-B pod parts', status='fixed',
                     note='the parts entered by B10 / B11 / B11S / B15 / B16 come down to 4.9 m with their walls; door surrounds added'),
                dict(item=7, finding='BA-F lantern at its 4.6-m bound', status='fixed', note='1.0-m upstand [unk]; bound kept in dimensions'),
                dict(item=8, finding='LOD2 outlines / roofs differ from LOD0', status='fixed', note='LOD0 outlines, wells, coping, clipped PV at LOD2'),
            ])
        return old
    return merge(upd)



def add_review_r2(after_path, before_path=None, extra=None):
    """manifest.json#domestic.review_r2: the round-2 findings, their dispositions and the probe summaries
    (tools/blender/verify_domestic_r2.py) before / after."""
    import datetime
    A = json.load(open(after_path)); B = json.load(open(before_path)) if before_path and os.path.exists(before_path) else None

    def summ(R):
        if not R: return None
        o = {}
        for k in ('tower', 'drums'):
            o[k] = {l: {kk: vv for kk, vv in R[k][l].items() if kk not in ('worst', 'open_examples', 'worst_max_r')} for l in ('lod0', 'lod2')}
        for k in ('c3c', 'bae', 'sign', 'plausibility_bac_bad'):
            if k in R: o[k] = R[k]
        return o

    def upd(old):
        old = old or {}
        old['review_r2'] = dict(
            updated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            probe='tools/blender/verify_domestic_r2.py (out/buildings3d/domestic_verify_r2.json, local)', after=summ(A), before=summ(B),
            integration_status='data/buildings3d/integration.json (b3d_integrate.py, 2026-11-05T16:35Z) lists 2 open conflicts, not 0: the E9 '
                               'rotunda drum vs BA_E (fixed here: 0 contacts at every pose / LOD, needs a re-run of tools/blender/b3d_integrate.py '
                               'by its owner) and the BART-station taxilane OFA (landside asset)',
            dispositions=[
                dict(item=1, severity='major', finding='C3C facade a tiled cube; penthouse missing', status='fixed',
                     note='six 3.8-m storeys of storey-height panes with staggered mullions, very dark green glass, light frames (glass_c3c, '
                          'own 24 x 22.8 m tile, no fins), connector levels below; penthouse 585 m2 to 38.0 m with the louvre band [obs low: '
                          'photo a1 + NAIP wall band]; the 8 C3C PV tables moved onto it'),
                dict(item=2, severity='minor', finding='BA-E end wall glazed only above 5.6 m; plate PV incomplete', status='fixed',
                     note='end wall glazed from 2.0 m (83 % of the wall, photo a1 profile); 8 NAIP arrays added (dom_pv_r2.py, 484 m2): '
                          'plate PV tops 269 -> 753 m2'),
                dict(item=3, severity='minor', finding='TOWER_EXCL z1 14.07 (F1 roof) leaves a slot above the F2 parapet', status='fixed',
                     note='the walls facing the IBF are emitted full height (0.3 m off it) instead of from 14.07 m; the flashing over the '
                          'gap sits at min(top, the lowest family IBF roof - 0.10 = 13.03 m) (manifest.json#tower anchors)'),
                dict(item=4, severity='minor', finding='T1 sign "1" a bar, thin grey letters; d1 camera above the roof edge', status='fixed',
                     note='Liberation Sans Bold (flagged 1), near-black lettering, sizes / heights measured on photo d1; d1 camera solved '
                          'from the photo facade lines: 2.8 m below the coping (render_domestic.D1_SOLVE)'),
                dict(item=5, severity='major', finding='BA-C / BA-D roofs below the 5.4-m concourse / bulkheads above the roofs',
                     status='open (tagged; request to the bridges / realtime owners)',
                     note='the conflict "BA-C / BA-D roofs vs the app concourse floor" (status open) carries the clearance numbers (BA-C 0.4 m, BA-D 1.69 m under a 0.8-m roof structure) and the '
                          'photo a1 evidence that the BA-D concourse sits ~1.5-2 m lower than the app floor; the roofs stay as measured'),
                dict(item=6, severity='minor', finding='0.24-m slit + 0.35-m crack above the IBF parapet', status='fixed',
                     note='walls full height behind the parapet of either family and a coping flashing over the gap (T2 / T1 / BA-D walk) '
                          'with a 0.15-m joint at the IBF wall (clear of its mullions)'),
                dict(item=7, severity='minor', finding='C3C / roof equipment only in 3-D', status='fixed (recorded)',
                     note='manifest deviations_from_sheets (the BD sheets belong to the drawings group)'),
                dict(item=8, severity='minor', finding='rotunda drums E9 (F8 / F7 / E3) inside BA_E / BA_F / T3E surfaces', status='fixed',
                     note='facades notched around the largest drum the app can draw (+0.1 m) at 9 stands; the door parts of the 36 doors near a drum clipped / left out there; '
                          'scene2d drums 20 contacts / 4 conflicts -> 0 / 0 (LOD0), max-radius drums 13 / 10 -> 0 / 0'),
            ])
        if extra: old['review_r2'].update(extra)
        return old
    return merge(upd)
