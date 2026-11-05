"""Manifest entry "landside" of data/buildings3d/manifest.json, written by tools/blender/build_landside.py (merged under a
file lock; the other asset groups own their keys). Per the owner's rules: the source tag of every dimension (per building
node, landside_geom Bldg.dims), polygon counts per LOD and building, texture sizes, what is inferred / unknown, the open
conflicts and the deliberate deviations from the sheet placeholders, the verification summary (verify_landside.py) and the
renders (render_landside.py).
"""
import landside_airtrain as AT
import landside_geom as G

GLOBAL_INFERRED = [
    'parking structures: open levels as a 3-m dark recess behind the facade plane, spandrels %.2f / %.2f m about each level line, '
    'facade piers %.1f m wide (spacing per building, landside_geom.PIER_DX), 42-in (1.07 m) deck guard' % (G.SPANDREL_DN, G.SPANDREL_UP, G.PIER_W),
    'parking modules: 2.6 x 5.5 m stalls, 7.6 m aisles (18.6-m module); RCC lanes 3.0 m with cars every 5.6 m',
    'parked cars: counts / densities and car axes from NAIP 2024 (landside_naip_measurements roof_cars; central garage: the visual '
    'estimate 300); which stalls are taken is random (seeded); fleet colours / shapes inf (landside_cars)',
    'stair / elevator towers at DOF roof points: 7 x 7 m boxes to the DOF top (LTP 1 x2, RCC 59-ft point), moved inside the outline '
    'within the 1A horizontal accuracy',
    'materials / colours: our reading of the reference photos (no imagery as texture); deck and roof colours sampled from NAIP 2024',
]
GLOBAL_UNKNOWN = [
    'Garage A / G roof decks (drawn at the drum ring), the central garage / RCC "81 ft" / "66 ft" definitions, the Hyatt height, '
    'the LTP 1 level count, the CAC parapet, the Superbay tips / folds / doors, the MOC section heights and barrel hangar heights',
    'AirTrain level along the guideway (see airtrain.levels: placeholders, interpolated between stations)',
    'facade modules of every building (schematic)',
]


REVIEW_R1 = [
    dict(n=1, item='Garage A station block', disposition='fixed (block); conflict raised (garage deck)',
         change='separate low block over the tracks: top 12.0 m above the guideway deck (l1: 11.1 m above the walkway), two long slots at +7.4 m '
                '(none over the central pier), open hall under its soffit over both tracks and to the south on round columns; >= 27 m deep '
                '(l1 sightline; 30 m drawn); the curved NE garage end next to it stays at the drum ring [unk, BL-03]',
         open='photo l1 puts the curved NE garage parapet ~12.9 m above the deck (~32.7 m), not the 39.6-m ring [obs, low]: the garage '
              'deck / ring conflict goes to the drawings group (BL-03 is the reference; not changed here)'),
    dict(n=2, item='Garages A / G drums, screens, towers', disposition='fixed',
         change='drums in smooth light metal panels with five long horizontal slots and an open top band, recessed 0.8 m (i2 heights); '
                'screens as full-bay perforated panels between thin mullions covering the lower 62 % of each level (l1); white precast '
                'stair / elevator towers with small square windows at both ends of each drum (NAIP boxes at the outline notches, top '
                'ring + 3.0 m [obs i2, low])'),
    dict(n=3, item='SFO BART station / Garage G station roof', disposition='fixed (station); approach not modelled (reason given)',
         change='new node bart_station: plan = OSM way 221663595 (ODbL) checked against the NAIP 2024 north wall line; open ground '
                'storey (OSM min_height 4) on columns, white panels, green glazed band (a2 ratios), top carrying the AirTrain deck; the '
                'Garage G AirTrain station roof is now a white barrel vault over platform and tracks (NAIP white roof, a2)',
         open='the three-track approach shares the corridor the SFO Museum AirTrain polygon covers (x -1920..-1592) and continues 2+ km '
              'west to the wye: not separated / not modelled; the spec / sheet item is requested from the drawings group'),
    dict(n=4, item='Central garage roof', disposition='fixed',
         change='NAIP-traced beige rims (0.15 m, nature unk) and stall-free lobes (own material), 11 rooftop stair / elevator / plant '
                'boxes (NAIP plan, heights inf), the void ring as a helix (level lines rising one pitch per turn), 216 cars at their '
                'NAIP 2024 positions + 127 white / silver ones next to them by fleet share'),
    dict(n=5, item='l5 comparison', disposition='fixed (camera solved, comparison redone)',
         change='camera solved from the tower width, the guideway vanishing point and the horizon: with the BL-02 tower D 6.5 the camera '
                'falls inside the RCC; the SFO Museum station polygon has the tower as a 4.7-m lobe 1.8 m west of the DOF point -> camera '
                'on the east walkway 19.4 m from the tower; platform 8.0 m (DOF top 8.6 m above the eye); louvres every 0.2 m; raked '
                'perforated hood (2.5 m rake, open top); twin tracks with running pads, guide rail and the walkway'),
    dict(n=6, item='AirTrain guideway section', disposition='fixed',
         change='trough walls 0.9 m (was 1.1), low guide rail 0.3 m (was a 0.8-m beam), concrete running pads, the twin-section walkway '
                '+0.9 m with galvanised handrails (LOD0), weathered darker concrete (streak texture)'),
    dict(n=7, item='Grand Hyatt face / glass', disposition='fixed',
         change='slab face behind the podium continues the outline east face along the relief-corrected NAIP roof edge (no re-entrant '
                'notch); glass retinted to saturated blue (texture glass (30, 92, 140))'),
    dict(n=8, item='Superbay roof / doors', disposition='partly rejected (with evidence); doors re-tagged inf',
         change='l3 identified: the Superbay from the NW (NNE end face 165 m on the left with the darker spine end under the hipped spine '
                'roof; the WNW door face 138 m on the right with the sawtooth fold eave and door leaves over its whole length) - the '
                'model already has plain end walls and doors on the door faces only; the two-tone roof is lighting: NAIP 2024 medians '
                '(238, 238, 229) / (242, 242, 234) on the two cantilevers at noon'),
    dict(n=9, item='other hangars / cargo buildings', disposition='listed as not modelled (scene_not_modelled, OSM ODbL)'),
    dict(n=10, item='Superbay red light', disposition='fixed', change="own material 'red_light' with extras.obstruction_light (glowKind -> beacon), in LOD0 / 1 / 2"),
    dict(n=11, item='LOD2', disposition='fixed',
         change='garage LOD2: parapet recess (deck at parapet - 1.07), core, rooftop box, towers, drum slot bands, station block, guideway '
                'portals with dark tunnel backs; Hyatt penthouse; MOC barrels to the crown; AirTrain LOD2 trough walls; 9 LOD2 checks '
                'in verify_landside.py. LOD2 keeps no parked cars by design (>= 1500 m: sub-pixel; deck_far carries the NAIP deck+car mean)'),
]


def entry(build, ver, bldgs, tiles, mats):
    st = build['glb']
    comps = {}
    for B in bldgs:
        comps[B.key] = dict(name=B.name, node=B.key, origin_world_xz=[B.F.ox, B.F.oz], src=B.src, spec=B.spec, dims=B.dims,
                            inferred=B.inferred, unknown=B.unknown, conflicts=B.conflicts, not_modelled=B.not_modelled,
                            deviations_from_sheets=B.deviations, anchors=B.anchors,
                            parts=[dict(node='L0_' + p.name, feature=p.feature, src=p.src, spec=p.spec, kind=p.kind, dims=p.dims)
                                   for p in B.shells + B.details[0]],
                            tris=st['per_building'].get(B.key), cars=build['cars'].get(B.key))
    at = build['airtrain']
    tiles_tris = {t.key: st['per_building'].get(t.key) for t in tiles}
    lods = {}
    for lod in (0, 1, 2):
        L = st['lods'].get(str(lod)) or st['lods'].get(lod) or {}
        lods[str(lod)] = dict(switch_m=G.SWITCH_M[lod], tris=L.get('tris'), instanced_car_tris=L.get('instanced_tris'), verts=L.get('verts'),
                              draw_calls=L.get('draws'))
    tex = []
    for im in st['images']:
        n = im['name'] or ''
        if n.startswith('landside_ao'):
            kind = 'AO (occlusionTexture, TEXCOORD_1)'; px = {'landside_ao_A': 2048, 'landside_ao_B': 2048, 'landside_ao_C': 1024}.get(n)
        elif n.startswith('ls_n_'):
            kind, px = 'normal map, tiling, TEXCOORD_0', None
        else:
            kind, px = 'base colour, tiling, TEXCOORD_0', None
        tex.append(dict(name=n, px=px, mime=im['mime'], bytes=im['bytes'], kind=kind))
    mat = {k: dict(rgb_srgb=list(v['rgb']), metallic=v['m'], roughness=v['r'], ior=v.get('ior', 1.5), src=v['src'],
                   normal_tile=(v.get('nrm') or [None])[0], base_tile=v.get('tex'), naip=v.get('naip')) for k, v in mats.items()}
    vv = None
    if ver:
        vv = dict(tool='tools/blender/verify_landside.py', report='out/buildings3d/landside_verify.json (local)', n_checks=ver['n_checks'],
                  n_fail=ver['n_fail'], failed=[r['check'] for r in ver['checks'] if not r['ok']], tolerance='0.5 m or 2 % unless stated',
                  checks=ver['checks'], plans=ver.get('plans'), plausibility=ver.get('plausibility'))
    return dict(
        asset='data/buildings3d/landside.glb', bytes=st['bytes'], built=build['built'], git=build['git'],
        generator='tools/blender/build_landside.py (bpy %s, Cycles CPU AO bake); geometry landside_geom.py / landside_airtrain.py / '
                  'landside_cars.py; textures landside_tex.py' % build['bpy'],
        reference='2-D sheets BL-01..03 (docs/drawings/buildings/README.md), drawn by tools/buildings/draw_landside.py, imported by landside_geom.py',
        spec='tools/buildings/spec_landside.json (+ landside_naip_measurements.json)',
        frame=dict(id='ltp-nad83-2011', axes='x east, y up, z south, metres from the ARP (js/geo.js)', root_node='landside',
                   root_translation=[0.0, 3.0, 0.0], ground_y=3.0,
                   building_nodes='one child per building / AirTrain tile, translated to its origin (origin_world_xz); heights above local grade'),
        lod_rule='per building node: LOD0 / LOD1 / LOD2 children; show exactly one: camera distance to the building node >= switch_m of '
                 'that LOD and < switch_m of the next. LOD0 / LOD1 share the shell meshes and their AO atlas (A: parking structures, '
                 'B: the other buildings + AirTrain); LOD2 is one joined node per building with atlas C. Parked cars '
                 '(EXT_mesh_gpu_instancing, one node per deck x shape x colour) under LOD0 and LOD1. Phone / far tier: '
                 'data/buildings3d/landside_lod2.glb = every LOD2 subtree with the same node transforms.',
        lods=lods, files=['data/buildings3d/landside.glb', 'data/buildings3d/landside_lod2.glb'], lod2_glb=build.get('lod2_glb'),
        textures=tex, materials=mat,
        material_note='glass coated (IOR 1.9 -> F0 0.096: KHR_materials_ior + _specular), opaque; deck / roof colours are NAIP 2024 '
                      'medians at the imaged (relief-shifted) roof positions (naip_colours); single-sided (faces wound outwards); cars: '
                      'one material, paint / glass / skirt in COLOR_0. No TANGENT attribute (tiling normal maps).',
        ao=build.get('ao'), naip_colours=build.get('naip_colours'),
        buildings=comps,
        airtrain=dict(tiles=tiles_tris, levels=at.get('anchors'), max_grade=at.get('max_grade'), piers=at.get('piers'), stations=at.get('stations'),
                      clipped_m2=at.get('clip_area_m2'), rcc_tower=at.get('rcc_tower'),
                      level_method='deck top = harmonic (Laplace) interpolation on the 1-m cells of the guideway polygon between the station '
                                   'platforms fixed at their levels: linear between stations, continuous through junctions',
                      clip='not built inside the ITB outline (itb.glb core block holds it, ITB L4 placeholder 16.5 m keeps it inside) and '
                           'inside the Garage A body (portals at both faces)',
                      deviations=['Garage A / G stations at the network level %.2f m, not the BL-03 Level-7 placeholders 29.7 / 28.2 m (grade to '
                                  'the Grand Hyatt station 40 m away)' % AT.NET_LEVEL,
                                  'RCC platform %.1f m from photo l5, not the BL-03 placeholder 12.35 m [unk]' % AT.RCC_PLATFORM]),
        cars=dict(total=build.get('cars_total'), per_deck=build.get('cars')),
        inferred=GLOBAL_INFERRED, unknown=GLOBAL_UNKNOWN,
        integration=dict(
            replaces='js/live/airport.js STRUCT_H_BY_NAME boxes for these buildings and its AirTrain guideway slab / columns',
            overlaps_with_other_assets=['AirTrain guideway crosses the SFO Museum terminal outlines of T1 / T2 / T3 (skybridge parts, '
                                        '~300-640 m2 each, at Level 3 below the guideway): check against the domestic asset',
                                        'ITB core block (itb.glb) holds the guideway / ITB stations inside the ITB outline'],
            note='the guideway is part of this asset; the app\'s guideway (G + 9.0..10.6 slab) must be removed with it'),
        verification=vv,
        review_r1=dict(findings=REVIEW_R1, observations='tools/blender/landside_r1_obs.json (tools/blender/landside_r1_measure.py): NAIP 2024 '
                       'plan positions / colours, OSM (ODbL) BART station way, numbers read off photos l1 / i2 / l5 / a2 (tags per item)',
                       requests_to_drawings=['Garage A / G roof deck vs drum ring (photo l1: NE parapet ~32.7 m)', 'Garage A station block '
                                             '(top, slots, depth) on BL-03', 'SFO BART station (plan, levels) as a spec item + sheet',
                                             'RCC station tower D 4.7 at the polygon lobe and the RCC platform 8.0 m (l5 camera solve)',
                                             'drum stair / elevator towers (positions / heights)', 'central-garage roof rims / lobes / boxes']),
        scene_not_modelled=dict(note='large airport buildings outside every asset (OpenStreetMap, ODbL 1.0, (c) OpenStreetMap contributors; '
                                     'refs/cache/osm): no spec / sheet yet - for a later spec round', buildings=G.R1.get('osm', {}).get('not_modelled', [])),
    )


def keep_renders(old, new):
    for k in ('renders', 'render_check', 'renders_updated', 'qa'):
        if old and old.get(k):
            new[k] = old[k]
    return new


def add_renders(render_json_path, verify_json_path=None):
    """merge the render list (out/buildings3d/landside_render.json, written by render_landside.py) into
    manifest.json#landside.renders under the manifest lock (no bpy)."""
    import fcntl
    import json
    import os
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    path = os.path.join(root, 'data', 'buildings3d', 'manifest.json')
    R = json.load(open(render_json_path))
    rel = lambda p: os.path.relpath(p, root) if isinstance(p, str) and p.startswith('/') else p
    out = {}
    for v, d in R.items():
        if not isinstance(d, dict): continue
        e = {k: rel(x) for k, x in d.items() if k in ('render', 'compare')}
        if d.get('silhouette_vs_sheet'):
            e['silhouette_vs_sheet'] = {k: d['silhouette_vs_sheet'][k] for k in ('n', 'px_m', 'max_abs_dev_m', 'p95_abs_dev_m', 'mean_dev_m')}
        if d.get('red_px') is not None:
            e['backface_red_px'] = d['red_px']
        out[v] = e
    lock = path + '.lock'
    with open(lock, 'a') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        cur = json.load(open(path))
        cur.setdefault('landside', {})['renders'] = dict(
            tool='tools/blender/render_landside.py (Cycles CPU, <= 960 px, 48 spp + OIDN, AgX; back-face QA 8 spp)',
            note='out/buildings3d/landside_*.png (local); landside_cmp_*.png overlay the BL-03 lines (orthographic) or sit beside '
                 'the reference photo (perspective; photo pixels, local only)', views=out)
        tmp = path + '.landside.tmp'
        json.dump(cur, open(tmp, 'w'), indent=1)
        os.replace(tmp, path)
        fcntl.flock(lf, fcntl.LOCK_UN)
    try:
        os.remove(lock)
    except OSError:
        pass
    return path


if __name__ == '__main__':
    import sys
    print(add_renders(sys.argv[1] if len(sys.argv) > 1 else 'out/buildings3d/landside_render.json'))
