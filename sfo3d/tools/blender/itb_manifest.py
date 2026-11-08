"""Manifest entry "itb" of data/buildings3d/manifest.json, written by tools/blender/build_itb.py (merged under a file lock;
the other asset groups own their keys). Lists, per the owner's rules: the source tag of every dimension (per node, from
itb_geom Part.dims), the polygon counts per LOD, the texture sizes, what is inferred / unknown, the open conflicts, and the
verification summary (tools/blender/verify_itb.py) and renders (tools/blender/render_itb.py).
"""
import os

import itb_geom as G

I = G.I
FT = 0.3048

CONFLICTS = [
    dict(item='roof length', model='252.87 m (NAIP 2024, frame-model relief correction) [obs]', other='860 ft = 262.13 m [pub SEAONC, '
         'Smith-Emery, MSC 2000]', note='BI-01 / BI-02 draw both; the asset follows the measured roof (range 252.6-255.1 m)'),
    dict(item='hall width', model='west wall at v -25.8 (band -28.3..-23.3) [inf]; east side closed by a clerestory 1 m inside the east eave',
         other='210 ft = 64.0 m [pub SEAONC] does not fit east of the wall under the 65.4-m roof', note='BI-02 / BI-03'),
    dict(item='BA-A pod 1 top', model='23.6 m (NAIP band, 22.1-25.0) [obs, low]', other='FAA DOF 06-035352 85 ft = 25.91 m [pub]',
         note='consistent only at the upper ends; the drawings draw the NAIP value'),
    dict(item='"building height 144 ft"', model='not used', other='SOM / Enclos, datum unknown [pub]', note='BI-02'),
    dict(item='BA-G bridge-head bump-outs vs the app walkways (review r2)', model='6.5 m [obs photo a2, low; r2 re-reading 6.5-7.1 m]',
         status='resolved (close-out r3: bridges lowered BA-G to DEPARTURE_LEVELS.G 2.7 [obs a2, low]; fix 2 re-check)',
         resolution='js/live/gates.js DEPARTURE_LEVELS.G 2.7 m: the 20 BA-G walkways that dock into a bump-out top at 5.71-5.87 m at the '
                    'attach points, under the 6.5-m bump-out roofs; the 4 at G12 / G13 (no bump-out) top at 6.16-7.29 m under the '
                    '16.0-m pier roof (verify_itb.py walkway_vs_host_roof from tools/blender/app_bridges.json, generated from the current '
                    'gates.js: 0 of 24 BA-G and 0 of 21 BA-A walkways above their host roof, 7 Nov 2026)',
         other='(round-2 state) gates.js walkway 5.2-8.46 m (DEPARTURE_LEVEL 5.4 [inf] + WALK_H 3.0)',
         note='NOT raised to ~9 m: on a2 the 6.5-m outline (solved camera) lies on the observed bump-out roof with its rooftop unit '
              'while a 9-m outline falls on the gate-room glazing behind; an upper-storey 2-lite window sits above bump-out B2 at '
              '~9.8-12.1 m; the walkway roofs meet the bump-outs ~1-1.4 m BELOW their roof edge. So the walkway head is the inferred '
              'value that is off: request to bridges (lower the BA-G walkway: top <= 6.0 m). verify_itb.py reports the cross-asset '
              'table (walkway top vs host roof per attach point)'),
    dict(item='roof eave at the tips', model='34.4 m (fit held non-increasing) [obs, low]', other='spec 34.9 (blend NAIP 34.4 / photo 35.5)',
         note='drawing_note_tips (review r2-27)'),
]

INFERRED = [
    'roof deck + fascia 0.6 m thick (BI-02 top-chord line); cross camber flat (unknown)',
    'glazed truss-line strips 1.5 m wide (NAIP 2024 dark lines, rough)',
    'lens skylights: pointed-lens planform (NAIP shows D shapes: vaulted lens or D plan, not settled), raised as vaults (review '
    'r1 / r2: photo i4 shows the crown capped by dark lens glass above the white fascia; r2 re-measure: 11-12 px = 1.6 m at the '
    'crown, >= 3 px over 83 % of the notch-to-notch span [obs, low]); the deck / fascia of the centre section runs '
    'crown_cap(u) = 1.6 (1 - (u / 27)^2)^0.7 m below the BI-02 silhouette roof_line(u) (between the notches), each lens vault rises '
    'crown_cap(u) + 0.4 m (the i4 line-of-sight drop) along its centre line, closed at the tips by (1 - x^8); vault form inf',
    'truss form: three-chord (2 top chords 2.4 m apart, 1 bottom chord), webs on a 20-ft node grid offset 10 ft; depth taper (BI-03); '
    'the west chord is level with the glass head (BI-02) except between the inner column line and the notch, where it follows the '
    'BI-03 taper (up to ~3.4 m above the BI-02 line; photos i3 / i4 show the sweep up to the notch: a deliberate deviation from '
    'BI-02 V1, both lines inf); centre section: a sagging bowstring chord from the deck at the notches to the clear bay head '
    '(photos i3 / i4; BI-03 draws the form as unknown); tube radii '
    '0.50 / 0.32 / 0.20 m',
    'eave outriggers under the soffit at every truss node (photo i3: regular spacing); review r2: white, 0.35 x 0.9 m (i3 / i4 show '
    'white brackets against the dark soffit)',
    'truss webs (review r2): the two side planes carry opposite diagonals, an X per 20-ft panel seen from the west (photo i4), with '
    'the V posts at every node as the verticals; wall-head brackets: dark inverted V 1.7 x 1.4 m at mid-panel (u = k 20 ft) hanging '
    'off the glass-wall head (photo i4 rhythm / size [obs, low], form inf)',
    'column positions +-190 / +-270 ft x 5 truss lines; west line 2.5 m in front of the glass; fan of 5 members (count obs, geometry inf: '
    'review r2 - the post continues to the roof (r 0.30), slender struts to the bottom-chord nodes +-6.1 m (r 0.18) and to the eave '
    'soffit +-2 m (r 0.16); round 1 had +-10-m arms that read as thick Y branches i4 does not show); radius 0.75 m',
    'west glass wall at the middle of its two canopy readings (v -25.8); level 3 at 11.5 m (9.6-14.8); canopy L3 + 5 m, 5 m deep; '
    'hanger form (inclined pair + post)',
    'upper glazing behind the exposed west truss (photo i3) and a head closure; end walls from level 3 to the roof underside; east '
    'clerestory 1 m inside the east eave',
    'departures curb sidewalk at level 3 from the wall [inf] to the kerb line v -30.1 [obs NAIP 2024: crosswalk warning strips, lane-1 '
    'cars] = 4.33 m, a 0.15-m kerb (the roadway deck at L3 - 0.15, roadways_net.KERB_M) and NO upstand (review r2, photo i3); bollards '
    '0.3 x 0.9 m (photo i3 form) 0.6 m behind the kerb on the 10-ft pitch with gaps at the five NAIP crosswalks [inf]; a 1.07-m guard '
    'only at the two curb end returns (open edge) [inf]; canopy posts 0.45 m behind the kerb (round 1 had them 0.2 m out on the roadway)',
    'pier parapet 1.0 m (roof deck below the measured roof edge)',
    'BA-G facade (review r1; photo a2 = the BA-G NNE face, camera solved): gate-room curtain walls 4.6-14.7 m filling the main-face '
    'segments between the bridge-head bump-outs that a roof pod overlaps by >= 35 m (6 rooms = the six double-gated gate rooms '
    '[pub]); obs on the NNE face (s 9.6..73.2 m and -133.1..-69.6 m imaged), inf on the SSW face and at G3 (outside a2); dark '
    'apron level 0-3.0 m and a light band 3.0-4.6 m [obs a2]; bridge-head bump-outs 6.5 m high [obs a2 B1, low; the others by '
    'eye / analogy]; curtain-wall rhythm (15.9-m bays, light mullion at mid-bay, ~1.7-m transoms, floor band) [obs a2, low]',
    'BA-A facade: NO reference photo (round 0 read a2 as BA-A; a2 shows BA-G): the round-0 glazed bays (24 m centred on the '
    'bridge attach points) are kept as placeholders [unk] with the BA-G band heights [inf, analogy]; bump-outs at the full '
    'outline height [unk]; the BA-G gate-room rule does not transfer (BA-A pods sit over its bump-outs)',
    'BA-G end box: window band top-2.6..top-1.2, three antennas (schematic, photo d2); function ramp-control cab (unconfirmed)',
    'BA-G walls (review r2): composite panels 7.32 x 3.048 m with faint halving lines (photo a2: strong joints every 7.3 m along '
    'the face and every 2.9 m up it - four rows below the roof edge - faint ones halfway) as a base-colour tile with dark reveals '
    'and +-3 % panel tone + normal tile; the same module on BA-A and the core [inf]; four imaged '
    '2-lite windows on the NNE face (a2, s +-2 m, heights +-1.5 m) [obs, low]; gate-room glass teal (base 16 / 92 / 96) [obs a2 hue]',
    'rooftop units: extents from NAIP 2024 (tools/blender/itb_roofobs.py: dark-object / shadow detection on the BA-A, BA-G and bump-out '
    'roofs, +-0.7 m) [obs]; heights 1.2 / 1.8 / 2.4 m by plan size, colour and louvre band [inf]',
    'ITB core north bar (review r2): an elevated connector over the domestic departures viaduct and the at-grade roads - underside '
    'L3 - 1.0 = 10.5 m (4.6 m [pub 15-ft minimum clearance] over the highest deck under it, 5.88 m in roadways.glb), top the 17.9-m '
    'placeholder, 0.6-m round columns where clear of every OSM road footprint (+1.5 m) [inf]; the core block cut back where OSM '
    'road footprints graze its outline (<= 5 m; the outline is +-5 m)',
    'materials / colours: our reading of the reference photos (no texture from imagery); roof colours sampled from NAIP 2024',
]

UNKNOWN = [
    'ITB core block (east block, north / south bars incl. the AirTrain stations at ITB level 4): height 17.9 m is a PLACEHOLDER '
    '(no source; set equal to the BA-A main roof); facade a metal-panel / window-band placeholder',
    'levels 1-2 under the hall (podium): faces only, concrete / dark band placeholder',
    'end-wall outline and mullions, the central section bottom chord form, fascia depth, mullion module of the end walls',
    'pier floor heights, BA-A gate-room bay positions (placeholders at the bridge heads), parapets; windows on the BA-G SSW face and '
    'on BA-A (not imaged); rooftop units below the NAIP limit (~1.5 m; photo a2 shows a row of small units behind the BA-G NNE parapet)',
    'no continuous concourse window band on BA-G: a2 shows none on the pier (the long green band in a2 belongs to the building '
    'beyond the south apron = Garage G / BART station, landside asset)',
    'the 2024-26 roof (new membrane, ~1,400 kW PV): not imaged; the asset shows the NAIP 2024 roof',
    'departures roadway beyond the kerb, the arrivals roadway, the AirTrain guideway through the ITB: not part of this asset (the '
    'roadways are the integration group\'s roadways.glb; see requests)',
    'the function and floor of the ITB core north bar (elevated connector; height of its floor = the departures level [inf])',
]


DEVIATIONS_FROM_SHEETS = [   # 3-D vs the 2-D sheets BI-01..04 (dated 2026-11-05 02:42Z): what the 3-D model changed after the sheets,
    # with sizes and tags (review r2 #9: the sheets were not redrawn; this list is the record)
    dict(sheet='BI-02 V1 / BI-03 V1', item='centre-section deck / fascia', drawn='on roof_line(u) (crown 40.1)',
         model='roof_line(u) - crown_cap(u): 1.60 m below at the crown (deck 38.50), 0 at the notches (u +-27); profile '
               '1.6 (1 - (u / 27)^2)^0.7', tag='obs photo i4 (r1 / r2 re-measure), low'),
    dict(sheet='BI-02 V1 / BI-01 V2', item='lens skylights', drawn='flat glazing in the deck plane (lens_poly planform)',
         model='vaults rising crown_cap(u) + 0.4 m above the deck along each lens centre line (2.0 m at the crown); tops <= 0.4 m above '
               'roof_line', tag='inf (form), obs i4 (dark cap)'),
    dict(sheet='BI-02 V1', item='west truss bottom chord', drawn='level with the glass head (30.8) notch to tip',
         model='max(BI-02 chord, BI-03 taper): up to ~3.4 m above BI-02 between the notch and the inner column line', tag='inf (photos i3 / i4)'),
    dict(sheet='BI-03 V1', item='centre-section bottom chord', drawn='form unknown [unk]', model='sagging bowstring: deck at the notches to '
         'WH + 2 at u = 0', tag='inf (photos i3 / i4)'),
    dict(sheet='BI-02 V1', item='column fans', drawn='post + 2 members per side at +-5 / +-10 m',
         model='post to the roof (r 0.30) + struts to the bottom-chord nodes at +-6.1 m (r 0.18) + eave struts at +-2 m (r 0.16)',
         tag='inf (review r2, photos i3 / i4)'),
    dict(sheet='BI-02 V1', item='truss webs / wall-head brackets / outriggers', drawn='schematic webs (~6 m), no brackets',
         model='X per 20-ft panel (opposite side-plane diagonals) + V posts; 35 dark 1.7 x 1.4-m brackets at u = k 20 ft; white 0.35 x '
               '0.9-m outriggers', tag='obs rhythm photo i4 (low), form inf'),
    dict(sheet='BI-02 V1 / V2', item='departures curb', drawn='curb band at L3 (width not dimensioned)',
         model='sidewalk wall -> kerb v -30.1 (4.33 m), 0.15-m kerb, no upstand, bollards + end guards, canopy posts 0.45 m behind '
               'the kerb', tag='obs NAIP (kerb line), inf (furniture)'),
    dict(sheet='BI-04 V1 / V2', item='BA-G bridge-head bump-outs', drawn='outline at the pier roof height (17.0)',
         model='6.5-m boxes (10) with roof units', tag='obs photo a2, low'),
    dict(sheet='BI-04 V2', item='pier glazing', drawn='~5.2-17.2 m gate-room bays (photo a2, then read as BA-A), positions unk',
         model='BA-G: 6 gate-room curtain walls 4.6-14.7 m filling the main-face segments between the bump-outs under a pod (63.5 m '
               'wide); BA-A: 24-m placeholder bays 4.6-14.7 m at the bridge attach points', tag='obs a2 (BA-G NNE), inf (SSW, BA-A)'),
    dict(sheet='BI-04', item='BA-G wall detail', drawn='panels / curtain wall named, layout unk',
         model='7.32 x 3.048-m panel module with faint halving lines (tile), four 2-lite windows (NNE face), NAIP roof units', tag='obs a2 / NAIP (low)'),
    dict(sheet='BI-01 V1', item='ITB core north bar', drawn='outline only (no height)', model='elevated connector 10.5-17.9 m with 7 '
         'columns; the core block cut back from OSM road footprints (-144 m2)', tag='inf (review r2)'),
]

REQUESTS = [
    dict(to='integration (roadways.glb, unit itb_departures)', what='extend the ITB departures deck to the kerb line', why='the deck '
         'starts at v -36.3 (roof frame) with a concrete parapet on its inner edge; NAIP 2024 puts the kerb at v -30.1 (lane-1 cars at '
         'v -31..-33, crosswalk ramps at the kerb): a 6.2-m gap with a drop to grade between the curb and the deck over |u| < 55 m. '
         'Kerb line in world coordinates: itb_geom.UVw(u, KERB_V) for u in [-107.4, 107.4] (e.g. %s .. %s); the curb sidewalk top is '
         'L3 = 11.5, the deck L3 - 0.15. Then re-run the roadway trim (b3d_integrate occupancy) against the new itb.glb (curb 4.33 m '
         'wide, north bar now elevated from 10.5 m)' % (str([round(c, 2) for c in G.UVw(-107.4, G.KERB_V)]), str([round(c, 2) for c in G.UVw(107.4, G.KERB_V)]))),
    dict(to='bridges (js/live/gates.js)', what='lower the Boarding Area G fixed walkways (top <= 6.0 m at the attach point)',
         status='done (close-out r3: DEPARTURE_LEVELS.G 2.7, walkway tops 5.71-5.87 m at the bump-outs, 6.16-7.29 m at G12 / G13 under the 16.0-m roof; checked fix 2)',
         why='DEPARTURE_LEVEL 5.4 [inf] + WALK_H 3.0 = 8.46-m walkway tops dock into 6.5-m bump-outs (photo a2: bump-out roofs 6.5-7.1 m '
             'with rooftop units, the walkway roofs ~1-1.4 m below the bump-out roof edge, the dark apron level to ~3.0 m, a light band to '
             '~4.6 m): at G3, G4, G7, G8, G9-1 the walkway pierces the bump-out roof, elsewhere its upper 2 m stands open above it. '
             'verify_itb.py lists walkway top vs host roof per attach point (manifest itb.verification.plausibility.walkway_vs_host_roof)'),
]


def entry(build, ver, parts, mats):
    st = build['glb']
    comps = []
    for name, p in parts[0].items():
        comps.append(dict(node='L0_' + name, feature=p.feature, src=p.src, spec=p.spec, dims=p.dims,
                          lods=[l for l in (0, 1, 2) if name in parts[l]], kind=p.kind))
    comps.append(dict(node='L0_hall_lettering', feature='west-wall lettering "SAN FRANCISCO INTERNATIONAL"', src='obs', spec=['facade.west'],
                      dims=dict(width=G.dim(66.0, 'obs', 'photos i1 / i4'), height=G.dim(2.8, 'obs', 'BI-02 V1'), font=G.dim('Blender built-in', 'inf', '')),
                      lods=[0, 1], kind='detail', note='LOD1 (L1_hall_lettering): flat front faces, coarse curves (review r1)'))
    lods = []
    for lod in (0, 1, 2):
        L = st['lods'].get('LOD%d' % lod, {})
        lods.append(dict(lod=lod, node='LOD%d' % lod, switch_m=G.SWITCH_M[lod], tris=L.get('tris'), verts=L.get('verts'),
                         ao_atlas='itb_ao_A (shared by LOD0 / LOD1 shell meshes)' if lod < 2 else 'itb_ao_B'))
    tex = []
    for im in st['images']:
        n = (im['name'] or '')
        kind = 'AO (occlusionTexture, TEXCOORD_1)' if n.startswith('itb_ao') else ('normal map, tiling, TEXCOORD_0' if n.startswith('itb_n_')
                                                                                   else 'base colour, tiling, TEXCOORD_0')
        px = {'itb_ao_A': 2048, 'itb_ao_B': 512, 'itb_c_frit': 256}.get(n, 512)
        if n.startswith('itb_c_curtain'): kind = 'base colour (glass + mullion caps), tiling, TEXCOORD_0'
        tex.append(dict(name=n, px=[px, px], mime=im['mime'], bytes=im['bytes'], kind=kind))
    mat = {k: dict(rgb_srgb=list(v['rgb']), metallic=v['m'], roughness=v['r'], ior=v.get('ior', 1.5), src=v['src'],
                   normal_tile=v.get('nrm', [None])[0], base_tile=v.get('tex')) for k, v in mats.items()}
    v = None
    if ver:
        key = [r for r in ver['checks'] if not r['ok']]
        v = dict(tool='tools/blender/verify_itb.py', report='out/buildings3d/itb_verify.json (local)', n_checks=ver['n_checks'],
                 n_fail=ver['n_fail'], failed=[r['check'] for r in key], tolerance=ver['tolerance'],
                 checks=[{k: r[k] for k in ('check', 'model', 'drawing', 'dev', 'tol', 'ok', 'src')} for r in ver['checks']],
                 plausibility=ver.get('plausibility'))
    return dict(
        asset='data/buildings3d/itb.glb', bytes=st['bytes'], built=build['built'], git=build['git'],
        generator='tools/blender/build_itb.py (bpy %s, Cycles CPU AO bake); geometry tools/blender/itb_geom.py' % build['bpy'],
        reference='2-D sheets BI-01..04 (docs/drawings/buildings/README.md), drawn by tools/buildings/draw_itb.py, imported by itb_geom.py',
        spec='tools/buildings/spec_itb.json (+ itb_naip_measurements.json, itb_pods.json)',
        frame=dict(id='ltp-nad83-2011', axes='x east, y up, z south, metres from the ARP (js/geo.js)', root_node='itb',
                   root_translation=[G.OX, 3.0, G.OZ], ground_y=3.0,
                   roof_frame=dict(centre_xz=[G.OX, G.OZ], u_axis_xz=[round(float(G.F['ax'][0]), 5), round(float(G.F['ax'][1]), 5)],
                                   heading_deg=162.85, note='u along the roof axis (+ towards BA-A, SSE), v across (+ ENE)')),
        lods=lods,
        lod_note='LOD nodes are siblings under the root: show exactly one (camera distance to the root >= switch_m of that LOD and '
                 '< switch_m of the next). LOD1 / LOD0 share the shell meshes and atlas A; LOD2 is one joined node (L2_itb, '
                 'extras.parts keeps the per-part tags) with its own atlas B. Phone / far tier: data/buildings3d/itb_lod2.glb holds '
                 'the LOD2 subtree alone (same root transform).',
        files=['data/buildings3d/itb.glb', 'data/buildings3d/itb_lod2.glb'], lod2_glb=build.get('lod2_glb'),
        textures=tex, materials=mat,
        material_note='glass: coated (IOR 1.9 -> F0 0.096, KHR_materials_ior), opaque (interior not modelled; glass_hall carries the '
                      'brightness of the lit hall seen through the clear bay); no imagery is used as a texture. No TANGENT attribute '
                      '(tiling normal maps of joints / seams; the runtime derives the tangent frame: 1.3 MB saved, validator '
                      'warning MESH_PRIMITIVE_GENERATED_TANGENT_SPACE accepted)',
        ao=build.get('ao'), naip_colours=build.get('naip_colours'),
        components=comps, inferred=INFERRED, unknown=UNKNOWN, conflicts=CONFLICTS,
        deviations_from_sheets=DEVIATIONS_FROM_SHEETS, requests=REQUESTS,
        plausibility_note='airside geometry stays inside the SFO Museum terminal / boarding-area outlines that tools/stands/'
                          'check_stands.py tests every stand and bridge against; rotundas set directly at the pier facade overlap '
                          'that outline by 0.3-1.8 m in the stand data itself (pre-existing, outline accuracy +-5 m: '
                          'data/sfo_buildings.json footprint_accuracy) - listed in verification.plausibility.rotunda_contacts',
        verification=v,
    )


def keep_renders(old, new):
    for k in ('renders', 'render_check', 'renders_updated', 'qa', 'closeout_r3', 'closeout_r3_fix2', 'closeout_r4'):   # (fix 2 / r4: close-out records survive)
        if old and old.get(k):
            new[k] = old[k]
    return new
