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
    add('departures curb above the apron (T1 / T2)', G.CURB, 'unk', 'placeholder: T3 L1 -> L2 rise by analogy')
    add('T1 Center wall head / tier transom / canopy soffit (above the curb)', f'{DD.T1_HEAD} / {DD.T1_SPLIT:.2f} / {DD.T1_CANOPY}', 'inf (photo d1, low)', 'BD-03 view 1')
    add('T1 Center roof height', H['T1'], 'unk', 'curb [unk] + wall head 13.0 [inf]; spec t1c.h_roof: none')
    add('T1 landside facade set-back from the trimmed curb line', G.T1_CANOPY_D, 'inf', 'canopy depth; NAIP 2024 PV roof edge 3-6 m inside the trimmed edge')
    add('T2 hall height', H['T2'], 'unk', 'curb [unk] + 12.0 (BD-03 view 2 placeholder)')
    add('pier / hall footprints', 'SFO Museum level-2 outlines (+ measured roof edges)', 'obs', 'data/sfo_airport.json (CDLA-Permissive-1.0)')
    add('concourse (departure) floor', G.FLOOR2, 'inf', 'js/live/gates.js DEPARTURE_LEVEL (bridge floor)')
    add('facade bands (service / spandrel / glazing / panel)', 'STYLES in dom_geom.py', 'inf / unk', 'materials pub where described (bab.glazing, bae.facade, t1c, t3w, t3e)')
    add('mullion module / fins', f'{G.MULL} m / {G.FIN[0]} x {G.FIN[1]} m', 'inf', 'no source')
    add('roof slab / parapet', f'{G.ROOF_THK} / {G.PARAPET}', 'inf', 'measured heights are the roof EDGES (coping top)')
    add('PV rack blocks', 'dom_pv.json', 'obs (extent, NAIP 2024 +-1 m) / inf (height 0.35-0.75 m)', 'tools/blender/dom_pv.py')
    add('elevated sky-bridge / connector parts', f'{G.INNER_Y0} - {G.INNER_TOP}', 'unk', 'the app convention (tools/build_terminal_parts.py walkway y0 6.0 / h 10.5)')
    add('elevated BA-B parts entered by a bridge walkway (B10 / B11 / B11S / B15 / B16): underside', G.WALK_Y0_BRIDGE, 'inf',
        'review r1: the vestibule floor (bridge floor 5.4 - 0.5) so that the app walkway (5.15-8.45 m) runs inside the part')
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
    add('bridge doors / vestibules / bulkheads', 'at the walkway attach points (data/sfo_stands.json)', 'inf', 'door 2.6 x 3.0 walkway section (gates.js)')
    add('roof colours', 'NAIP 2024 median per building, capped at sRGB 215', 'obs (low) / inf (cap)', 'build_domestic.naip_colours')
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
    'Courtyard 3 Connector office block (review r1): 33.0 m (six published office storeys above the connector, NAIP relief, photo a1), '
    'electrochromic ("dynamic") curtain glass on a 3-m module, the connector levels below as the piers',
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
    'the departures-curb height above the apron (T1 / T2): 4.88 m placeholder (T3 L1 -> L2 by analogy)',
    'the T3 project datum (L1 drawn at the apron); the T3 East landside facade (drawn with the published T3E materials, positions inf)',
    'the BA-B roof-well depth and skylight heights; the BA-F lantern (bound <= 4.6 m, modelled 1.0 m) and monitor rises; the BA-B '
    'north-half outer roof height',
    'the Courtyard 3 Connector height (modelled 33.0 m, range 32-36 m) and its roof penthouse (photo a1 shows a light box on the roof: '
    'not resolved in NAIP 2024, not modelled)',
    'rooftop unit heights and types (extents measured; NAIP 2024 resolves only compact dark units with a shadow; light units on light '
    'membranes and units under 4 m2 are missed); no BA-B reference photo was found with an open licence (Wikimedia Commons searched '
    '2026-11-05), so the BA-B facade materials remain unverified'
    'bay / mullion modules, gate-room glazing extents, the apron-level facades (service band only), parapet heights',
    'the elevated sky-bridge / pod parts (app convention 6.0-10.5 m; 4.9-10.5 m where a bridge walkway enters, review r1)',
    'which T3W state to model (under construction 2024-2029; the May 2026 change adds an airside storey): the asset shows the 95 % CD '
    'parapet 66\'-0" massing without the new storey',
]

NOT_MODELLED = [
    'courtyard links (pedestrian bridges over the curbside roadways to the garage / AirTrain stations) and the links that cross the '
    'AirTrain guideway: no known level (the app keeps its own parts there)',
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
         'line; the spec note should be corrected by the drawings group'),
    dict(item='T1 Center landside face', model='on the measured roof edge: the app\'s trimmed curb line (OSM carriageways) less 4.0 m',
         other='BD-03 view 1 develops the face along the SFO Museum outline (94.1 + 43.6 + 93.8 m)',
         note='NAIP 2024 shows the curb roadway and vehicles INSIDE the SFO Museum outline there, and the PV roof edge 3-6 m inside the '
              'trimmed edge (overlay checked 2026-11-05); heights follow BD-03'),
    dict(item='T3W parapet', model='16.76 m = 66\'-0" - T3 L1 11\'-0" (BD-02 / BD-03)', other='spec t3.heights_above_L1 16.99 m '
         '(66\'-0" - T3W L1 10\'-3")', note='datum choice; 0.23 m'),
    dict(item='BA-D overhang vs bridges', model='overhang +2.40 m notched at the doors (roof underside 7.69 m < walkway head 8.4 m)',
         other='bad.h_roof 8.49 m [obs, low] with a bridge floor 5.4 m (gates.js)', note='a real bridge cannot pass under a 7.7 m soffit: '
         'either the head roof is higher there or the edge is local; the notch keeps both values'),
    dict(item='BA-C roof vs bridges', model='bulkheads above the 7.2 m roof at the doors', other='bac.h_roof 7.2 m [obs, low] below the '
         'walkway head 8.4 m', note='as BA-D'),
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
        bridges=dict(doors=len(doors), vestibules=sum(1 for d in doors if d['gap'] > 0.12), bulkheads=sum(1 for d in doors if d['low']),
                     notched=sum(1 for d in doors if d.get('notched')),
                     note='every bridge of data/sfo_stands.json (B-F) gets a door surround where its walkway meets the 3-D facade; where the '
                          'app\'s walkway (js/live/gates.js) starts outside the facade a vestibule closes the gap'),
        integration=dict(replaces='js/live/terminals.js extrusions of the domestic parts of data/sfo_buildings.json (T1 / T2 / T3 halls, '
                                  'Boarding Areas B-F, their walkways)',
                         keep='the courtyard links and guideway-crossing connectors (not modelled here), the app\'s ramp-level complex outline '
                              'for the bridge clearance tests (gates.js uses the SFO Museum outlines, which this asset follows)',
                         exclusions='the tower base building (tower asset) and the ITB outline are cut out / not overlapped (0 m2)'),
        verification=v,
    )


def keep_renders(old, new):
    for k in ('renders', 'render_check', 'renders_updated', 'renders_args', 'renders_note', 'qa', 'validator', 'neighbours', 'review_r1'):
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
    try:
        os.remove(lock)
    except OSError:
        pass
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

