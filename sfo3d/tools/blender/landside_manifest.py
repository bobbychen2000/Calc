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
    )


def keep_renders(old, new):
    for k in ('renders', 'render_check', 'renders_updated', 'qa'):
        if old and old.get(k):
            new[k] = old[k]
    return new
