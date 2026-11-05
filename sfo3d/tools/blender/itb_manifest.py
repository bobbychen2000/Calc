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
    dict(item='roof eave at the tips', model='34.4 m (fit held non-increasing) [obs, low]', other='spec 34.9 (blend NAIP 34.4 / photo 35.5)',
         note='drawing_note_tips (review r2-27)'),
]

INFERRED = [
    'roof deck + fascia 0.6 m thick (BI-02 top-chord line); cross camber flat (unknown)',
    'glazed truss-line strips 1.5 m wide (NAIP 2024 dark lines, rough)',
    'lens skylights: pointed-lens planform (NAIP shows D shapes: vaulted lens or D plan, not settled), raised as vaults 1.9 m '
    'above the deck (review r1: photos i4 / i2 show the crown capped by dark lens glass, 1.5 m above the white fascia at the '
    'crown in i4 [obs, low]; the deck / fascia of the centre section runs crown_cap(u) = 1.5 (1 - ((u + 1.8) / 24.0)^2) m below the '
    'BI-02 silhouette roof_line(u), and the lens tops form that silhouette as seen from i4; vault form and rise inf)',
    'truss form: three-chord (2 top chords 2.4 m apart, 1 bottom chord), webs on a 20-ft node grid offset 10 ft; depth taper (BI-03); '
    'the west chord is level with the glass head (BI-02) except between the inner column line and the notch, where it follows the '
    'BI-03 taper (up to ~3.4 m above the BI-02 line; photos i3 / i4 show the sweep up to the notch: a deliberate deviation from '
    'BI-02 V1, both lines inf); centre section: a sagging bowstring chord from the deck at the notches to the clear bay head '
    '(photos i3 / i4; BI-03 draws the form as unknown); tube radii '
    '0.50 / 0.32 / 0.20 m',
    'eave outriggers under the soffit at every truss node (photo i3: regular spacing)',
    'column positions +-190 / +-270 ft x 5 truss lines; west line 2.5 m in front of the glass; fan of 5 members (count obs, geometry inf); '
    'radius 0.75 m',
    'west glass wall at the middle of its two canopy readings (v -25.8); level 3 at 11.5 m (9.6-14.8); canopy L3 + 5 m, 5 m deep; '
    'hanger form (inclined pair + post)',
    'upper glazing behind the exposed west truss (photo i3) and a head closure; end walls from level 3 to the roof underside; east '
    'clerestory 1 m inside the east eave',
    'departures curb sidewalk 7 m wide at level 3 with a 1.1 m upstand',
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
    'materials / colours: our reading of the reference photos (no texture from imagery); roof colours sampled from NAIP 2024',
]

UNKNOWN = [
    'ITB core block (east block, north / south bars incl. the AirTrain stations at ITB level 4): height 17.9 m is a PLACEHOLDER '
    '(no source; set equal to the BA-A main roof); facade a metal-panel / window-band placeholder',
    'levels 1-2 under the hall (podium): faces only, concrete / dark band placeholder',
    'end-wall outline and mullions, the central section bottom chord form, fascia depth, mullion module of the end walls',
    'pier floor heights, BA-A gate-room bay positions (placeholders at the bridge heads), parapets, roof equipment (none '
    'modelled); the two isolated 2-lite windows per panel segment on the BA-G NNE face (photo a2) are not modelled',
    'no continuous concourse window band on BA-G: a2 shows none on the pier (the long green band in a2 belongs to the building '
    'beyond the south apron = Garage G / BART station, landside asset)',
    'the 2024-26 roof (new membrane, ~1,400 kW PV): not imaged; the asset shows the NAIP 2024 roof',
    'departures roadway beyond the 7 m curb, the arrivals roadway, the AirTrain guideway through the ITB: not part of this asset',
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
        plausibility_note='airside geometry stays inside the SFO Museum terminal / boarding-area outlines that tools/stands/'
                          'check_stands.py tests every stand and bridge against; rotundas set directly at the pier facade overlap '
                          'that outline by 0.3-1.8 m in the stand data itself (pre-existing, outline accuracy +-5 m: '
                          'data/sfo_buildings.json footprint_accuracy) - listed in verification.plausibility.rotunda_contacts',
        verification=v,
    )


def keep_renders(old, new):
    for k in ('renders', 'render_check', 'renders_updated', 'qa'):
        if old and old.get(k):
            new[k] = old[k]
    return new
