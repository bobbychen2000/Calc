"""Build sha3d/data/sha_buildings3d.json and sha_buildings3d.js (window.SHA_BUILDINGS3D): the parametric building parts of
SHA Live 3D (Phase 2, package P2d: terminals, tower, hangars, surroundings). Deterministic; run it to rebuild:

    python3 -I sha3d/tools/buildings/build_buildings3d.py [SHA3D_DIR]

Role (sfo3d@e3218d6 tools/build_terminal_parts.py -> data/sfo_buildings.js, same idea, NO SFO geometry or data): the OSM
building outlines of data/sha_airport.json (one outline per terminal; T1 is `source=estimation`) are split into the
volumes the renderer draws (js/world/buildings3d.js), each with a height, a style (facade / roof form) and its sources.
Every split line, height, depth and style below is a modelling parameter [inf] chosen from the open-licence photos
(docs/phase1/photos_credits.md, contact sheet; proportions only, nothing traced or textured) and the B3 height
measurements (data/meas/b3_building_heights.json, all inf). The OSM outline itself (the airside facade the jet bridges
attach to) is never moved: parts are intersections of the OSM polygon with zones.

Inputs (committed): data/sha_airport.json (OSM, ODbL), data/sha_stands.json (bridge attach points, for a check only),
data/meas/b3_building_heights.json (B3 heights).

Decisions (all [inf] unless a source is named):
  T2 (osm:relation/21913345, one outline incl. piers; photos 09-17, aerials 21/22/24):
    hall      x <= -1238                        main hall (landside processor)  22 m  B3 "T2 main hall" 22 +- 4
    central   -1238 < x <= -1098, -150 <= z <= 492   central concourse + core    21 m  B3 Umbra layover on its west wall
                                                                                       at x -1140, z 307-490: 21.4 +- 3.3
    finger_n  x > -1098, z < 100                north finger pier (gates 226-237)  15 m  rule: two glazed levels + roof
    finger_s  x > -1098, z > 300                south finger pier (256-266)       15 m  (photos 09, 14, 15)
    arm_n     x <= -1098, z < -150              north linear arm (221-225)        15 m
    arm_s     x <= -1098, z > 492               south linear arm (272-276)        15 m
  T1 (osm:way/93184730, `source=estimation`; photos 01-05, 02 = airside from RWY 18L/36R):
    the airside concourse is a band along the west and north facades: front tier 0-12 m deep at 9 m (B3 photo ratio,
    8.9 m), rear tier 12-32 m deep at 13 m (photo 02, same scale: upper set-back tier, 40 px -> 13 m);
    the rest of the outline: x > 553 and z < 140 = landside block with louvre bands (photos 01/03) 24 m; x <= 553 = airside core
    15 m; a 30 m square yard around the east tower node (the tower rises from the ground behind the concourse, photo 02);
    (slivers narrower than 8 m are dropped from these two);
    T1 central hall = osm:way/590426959 (its west face is where B3 placed the hall front, x ~ 560, z ~ 240): 26 m
    (B3 photo ratio 26.4, 23.0-30.1), glazed clerestory + louvre bands (photos 01-03).
  East control tower (osm:node/3342630333): height 44.5 m (AIP (mirror) obstacle elevation 47 m - ground 2.5 m); form
    from photo 02 (1920 px, 0.356 m/px at the tower, B3 scale): square shaft 7.7 m with a dark vertical slot, inverted
    frustum head from 29.5 m to 39.8 m (7.7 -> 15.8 m) with two rows of small windows, cab glazing 39.8-43.0 m leaning
    outward (10.5 -> 12.1 m), flat roof slab 43.0-44.5 m (12.6 m; nothing above the AIP obstacle top); +-1 px = +-0.36 m; plan orientation unknown
    (aligned with the runway grid 177.3 deg) [inf].
  SW towers (osm:way/1576039982, 1576039987: untyped man_made=tower, added 2026-11-06, role unknown): OSM footprint
    extruded to the 35 m rule, plain, with a rooftop mast [inf].
  Hangars: heights B3 (China Eastern 33.5 SAR, big east 28.5 SAR, NE 16 SAR, small east 22 rule); door wall = the side
    of the minimum rectangle with the most airside pavement in front (computed below); roof forms from the aerials:
    China Eastern a shallow barrel (photo 22), big east hangar 4 parallel bays (photo 21), others flat [inf].
  Other airport buildings and the Hongqiao hub (rail station, platform canopies, bus terminal, T2 metro / suburban rail
    station, parking P6 / P7): styles by kind, heights = the data's rule heights (inf).
"""
import datetime
import hashlib
import json
import math
import os
import re
import sys

from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union
import shapely

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..'))
AIRPORT = os.path.join(ROOT, 'data/sha_airport.json')
STANDS = os.path.join(ROOT, 'data/sha_stands.json')
HEIGHTS = os.path.join(ROOT, 'data/meas/b3_building_heights.json')
S2HINT = os.path.join(ROOT, 'data/sha_ground_s2.js')
CAAC_JS = os.path.join(ROOT, 'js/live/caac_markings.js')   # the ONE CAAC parameter table (stand envelope values, read below)
OUT_JSON = os.path.join(ROOT, 'data/sha_buildings3d.json')
OUT_JS = os.path.join(ROOT, 'data/sha_buildings3d.js')
R2 = lambda v: round(float(v), 2)  # noqa: E731

T1_ID, T2_ID, T1_HALL_ID = 'osm:way/93184730', 'osm:relation/21913345', 'osm:way/590426959'
TOWER_SW = ['osm:way/1576039982', 'osm:way/1576039987']
HANGARS = {   # id: (name, B3 key / rule, roof form, bays)
    'osm:way/327613444': ('China Eastern hangar', 'barrel', 1),
    'osm:way/327473856': ('big east hangar', 'multi', 4),
    'osm:way/327473860': ('small east hangar', 'flat', 1),
    'osm:way/328013621': ('north-east hangar', 'flat', 1),
}
# style by building id (airport buildings) and by kind (fallback); heights stay the data's unless set here
STYLE_BY_ID = {
    'osm:way/469610770': ('glass_pavilion', None, 'business-aviation terminal (FBO): glazed 2-3 storey box [inf]'),
    'osm:way/1443258835': ('t1_annex', None, 'east-area VVIP terminal at the south end of the T1 concourse: white, dark apron level, window '
                           'row (photo 02, right edge) [inf]'),
    'osm:relation/21913196': ('office', None, 'China Eastern office block [inf]'),
    'osm:way/71898265': ('parking', None, 'T2 multi-storey car park (OSM ref 6)'),
    'osm:way/101936681': ('parking', None, 'T2 multi-storey car park (OSM ref 7)'),
    'osm:way/449054625': ('station', None, 'T2 suburban-rail / metro station building (Hongqiao hub, east part)'),
    'osm:way/1576050065': ('hotel', None, 'hotel (Traders) by T2'),
}
HUB_CONTEXT = {   # context buildings of the Hongqiao transport hub, drawn here (low detail)
    'osm:way/70364443': ('station', 'Shanghai Hongqiao railway station main building'),
    'osm:way/558909171': ('canopy', 'Hongqiao railway station platform canopies (south)'),
    'osm:way/558909169': ('canopy', 'Hongqiao railway station platform canopies (north)'),
    'osm:way/392964430': ('station', 'Shanghai Hongqiao long-distance bus terminal'),
}
STYLE_BY_KIND = {'hangar': 'hangar', 'office': 'office', 'hotel': 'hotel', 'parking': 'parking', 'train_station': 'station',
                 'business_terminal': 'glass_pavilion', 'vvip': 'glass_pavilion', 'tower': 'tower_sw', 'roof': 'canopy'}


def load(p):
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def poly_of(b):
    rings = [b['ring']] + [r[0] if isinstance(r[0][0], list) else r for r in (b.get('more_rings') or [])]
    ps = [Polygon(r).buffer(0) for r in rings if len(r) >= 3]
    return unary_union(ps)


def ring_area(r):
    a = 0.0
    for i in range(len(r)):
        p, q = r[i], r[(i + 1) % len(r)]
        a += p[0] * q[1] - q[0] * p[1]
    return a / 2


def rings_of(geom, min_area=30.0):
    """[[outer, hole, ...], ...] with outer positive (shoelace x,z) and holes negative; slivers dropped"""
    out = []
    geoms = list(geom.geoms) if hasattr(geom, 'geoms') else [geom]
    for g in geoms:
        if g.is_empty or g.geom_type != 'Polygon' or g.area < min_area:
            continue
        g = shapely.geometry.polygon.orient(g.simplify(0.05), 1.0)
        outer = [[R2(x), R2(z)] for x, z in list(g.exterior.coords)[:-1]]
        holes = [[[R2(x), R2(z)] for x, z in list(h.coords)[:-1]] for h in g.interiors if Polygon(h).area > 5]
        if ring_area(outer) < 0:
            outer.reverse()
        holes = [h if ring_area(h) < 0 else h[::-1] for h in holes]
        out.append([outer] + holes)
    return out


def frame_of(geom):
    """principal axis (unit x,z), centre, length, width of the minimum rotated rectangle"""
    mrr = geom.minimum_rotated_rectangle
    c = list(mrr.exterior.coords)[:4]
    e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
    l1, l2 = math.hypot(*e1), math.hypot(*e2)
    ax, L, W = (e1, l1, l2) if l1 >= l2 else (e2, l2, l1)
    n = math.hypot(*ax) or 1
    ctr = mrr.centroid
    return {'axis': [R2(ax[0] / n * 100) / 100, R2(ax[1] / n * 100) / 100], 'center': [R2(ctr.x), R2(ctr.y)], 'len': R2(L), 'wid': R2(W), 'area': R2(geom.area)}


def part(pid, of, name, geom, h, style, h_src, h_note, extra=None):
    p = {'id': pid, 'of': of, 'name': name, 'style': style, 'h': h, 'h_src': h_src, 'h_note': h_note, 'polys': rings_of(geom), 'src': 'inf',
         'geom_src': 'OSM outline (obs) split into volumes by modelling zones (inf)' if pid != of else 'OSM outline (obs)'}
    p.update(frame_of(geom))
    if extra:
        p.update(extra)
    return p


def b3(H, bid):
    for r in H['buildings']:
        if r['id'] == bid:
            return r
    return None


# ---------------------------------------------------------------------------------------------- airside fill (fix round 1, H2)
# The OSM apron ways stop 15-40 m short of the T1 / T2 airside facades, so the ground shader drew grass ("dirt moat") under
# every fixed link, rotunda and VDGS post. Photo 09 shows a dark asphalt service road there (white edge lines, parking,
# vehicles); the Sentinel-2 hint (data/sha_ground_s2.js, 10 m) shows the band as paved. The fill below is drawn by
# js/live/terminals.js through the core pavement hook as 'paved' (asphalt) [inf]:
#   1. every airside facade segment (<= FILL_SEG m) whose outward normal meets airside pavement (aprons, taxiway / runway
#      surfaces) within FILL_REACH m gets a quad from the facade to that pavement + FILL_OVERLAP m; convex corners between
#      two such segments get a disc of the shorter reach (pier tips);
#   2. cut to the aerodrome polygon (never landside) and to outside the buildings;
#   3. minus the 10 m Sentinel-2 pixels that read as grass (GRASS_TEST, clusters of >= 3 pixels: isolated dark pixels are
#      shadows or bridge roofs, not grass) so real grass stays grass;
#   4. plus a WALK_W m corridor along every fixed link (attach -> rotunda), a ROT_R m disc at every rotunda and a
#      STAND_CL_W m strip along every contact stand's centreline from the nose to the facade (VDGS posts)
#      (data/sha_stands.json), never grass under a bridge.
AIRSIDE_FILL_OF = [T1_ID, T2_ID, 'osm:way/1443258835']   # T1, T2, the VVIP annex at the south end of the T1 concourse
FILL_REACH, FILL_OVERLAP, FILL_SEG = 60.0, 3.0, 8.0     # m [inf]
WALK_W, ROT_R = 24.0, 14.0                              # m [inf] (review_visual.md H2)
STAND_CL_W = 10.0                                       # m [inf] contact-stand centreline strip (VDGS posts)
# Sentinel-2 grass test on rho (linear reflectance): L = mean(R, G, B), g = (G - (R + B) / 2) / L. Medians on this scene:
# apron L 0.177, g 0.035 (12,516 px inside the aprons); airside grass L 0.092, g 0.053 (11,589 px) -> grass when
# L < 0.115 and g > 0.02, or g > 0.12 [inf]
GRASS_L, GRASS_G, GRASS_G_ANY = 0.115, 0.02, 0.12


_S2 = {}


def s2_hint():
    if 'h' in _S2:
        return _S2['h']
    import base64
    import io
    import numpy as np
    from PIL import Image
    s = open(S2HINT, encoding='utf-8').read()
    meta = json.loads(s[s.index('{'):s.rindex('}') + 1])
    im = np.asarray(Image.open(io.BytesIO(base64.b64decode(meta['png']))).convert('RGBA'), dtype=float)
    v = im[..., :3] / 255.0
    rho = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4) / 2.0   # decode as the file says
    _S2['h'] = (meta, rho, im[..., 3] > 0)
    return _S2['h']


def s2_grass_geom(bounds):
    """the 10 m Sentinel-2 pixels inside bounds that read as grass (GRASS_L / GRASS_G / GRASS_G_ANY, clusters of >= 3 px:
    isolated dark pixels are shadows or bridge roofs), as one geometry buffered by 1 m"""
    import numpy as np
    meta, rho, valid = s2_hint()
    L = rho.mean(axis=2); gidx = (rho[..., 1] - 0.5 * (rho[..., 0] + rho[..., 2])) / np.maximum(L, 1e-3)
    grass = valid & (((L < GRASS_L) & (gidx > GRASS_G)) | (gidx > GRASS_G_ANY))
    gp = np.pad(grass, 1); nb = sum(np.roll(np.roll(gp, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)[1:-1, 1:-1]
    grass &= nb >= 2   # itself + >= 2 neighbours
    x0, z0 = meta['rect'][0], meta['rect'][1]; res = meta['res_m']
    bx0, bz0, bx1, bz1 = bounds
    i0, i1 = max(0, int((bx0 - x0) / res) - 1), min(grass.shape[1], int((bx1 - x0) / res) + 2)
    j0, j1 = max(0, int((bz0 - z0) / res) - 1), min(grass.shape[0], int((bz1 - z0) / res) + 2)
    gboxes = [box(x0 + i * res, z0 + j * res, x0 + (i + 1) * res, z0 + (j + 1) * res) for j in range(j0, j1) for i in range(i0, i1) if grass[j, i]]
    return unary_union(gboxes).buffer(1.0, join_style=2) if gboxes else Polygon()


def airside_fill(A, S, terminals):
    import numpy as np
    T = unary_union(terminals)
    allb = unary_union([poly_of(b) for b in A['buildings']])
    pav = unary_union([Polygon(a['ring'], a.get('holes') or []).buffer(0) for a in A['aprons']] +
                      [Polygon(p['ring']).buffer(0) for k in ('taxiway', 'runway', 'taxiway_shoulders', 'runway_shoulders_blast_pads')
                       for p in A['surfaces'].get(k, [])])
    aer = unary_union([Polygon(r).buffer(0) for r in A['aerodrome']['rings']])
    quads, discs, nseg, nhit = [], [], 0, 0
    for g in (list(T.geoms) if hasattr(T, 'geoms') else [T]):
        ring = list(shapely.geometry.polygon.orient(g, 1.0).exterior.coords)[:-1]
        reach_at = []   # per original edge: list of (p, q, reach or None)
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 0.5:
                reach_at.append([]); continue
            d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L); n = (d[1], -d[0])
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if g.contains(Point(mid[0] + n[0] * 0.5, mid[1] + n[1] * 0.5)):
                n = (-n[0], -n[1])
            k = max(1, int(math.ceil(L / FILL_SEG))); segs = []
            for j in range(k):
                p = (a[0] + d[0] * L * j / k, a[1] + d[1] * L * j / k); q = (a[0] + d[0] * L * (j + 1) / k, a[1] + d[1] * L * (j + 1) / k)
                m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2); ts = np.arange(1.0, FILL_REACH + 0.5, 1.0)
                hit = shapely.contains_xy(pav, m[0] + n[0] * ts, m[1] + n[1] * ts)
                bl = shapely.contains_xy(allb, m[0] + n[0] * ts, m[1] + n[1] * ts)   # another building in the way: no fill
                nseg += 1; r = None
                if hit.any():
                    t0 = float(ts[int(np.argmax(hit))])
                    if not bl[ts < t0].any():
                        r = t0 + FILL_OVERLAP; nhit += 1
                        quads.append(Polygon([p, q, (q[0] + n[0] * r, q[1] + n[1] * r), (p[0] + n[0] * r, p[1] + n[1] * r)]))
                segs.append((p, q, r))
            reach_at.append(segs)
        for i in range(len(ring)):   # corners between two filled facade segments (convex corners leave a wedge: pier tips)
            s0, s1 = reach_at[i - 1], reach_at[i]
            if s0 and s1 and s0[-1][2] and s1[0][2]:
                discs.append(Point(ring[i]).buffer(min(s0[-1][2], s1[0][2]), 24))
    band = unary_union(quads + discs).buffer(1.0, join_style=2).buffer(-1.0, join_style=2)
    band = band.intersection(aer).difference(allb).difference(pav.buffer(-2.0))
    # Sentinel-2 grass pixels (clusters of >= 3)
    grass_geom = s2_grass_geom(band.bounds)
    before = band.area
    band = band.difference(grass_geom)
    grass_cut = before - band.area
    # fixed links and rotundas (never grass under a bridge); contact stands: the centreline from the nose to the facade
    # (<= FILL_REACH m, STAND_CL_W wide), where the gates package stands the VDGS post (e.g. 221, beyond the end of the
    # T2 north arm, where no facade segment faces the apron)
    br = []
    for s in S['stands']:
        for b in s.get('bridges') or []:
            br.append(shapely.geometry.LineString(b['walk']).buffer(WALK_W / 2, cap_style=2, join_style=2))
            br.append(Point(*b['rotunda']).buffer(ROT_R, 24))
        if s.get('bridges'):
            h = math.radians(s['hdg']); f = (math.sin(h), -math.cos(h)); n0 = s['nose']; ts = np.arange(1.0, FILL_REACH + 0.5, 1.0)
            inb = shapely.contains_xy(allb, n0[0] + f[0] * ts, n0[1] + f[1] * ts); t1 = float(ts[int(np.argmax(inb))]) if inb.any() else FILL_REACH
            br.append(shapely.geometry.LineString([n0, (n0[0] + f[0] * t1, n0[1] + f[1] * t1)]).buffer(STAND_CL_W / 2, cap_style=2))
    brg = unary_union(br).intersection(aer).difference(allb).difference(pav.buffer(-2.0))
    # close slivers < 6 m between the pieces (e.g. stand 221's centreline strip and the band), stay out of buildings
    fill = unary_union([band, brg]).buffer(3.0, join_style=2).buffer(-3.0, join_style=2).intersection(aer).difference(allb).simplify(0.4)
    polys = rings_of(fill, min_area=40.0)
    stats = {'facade_segments': nseg, 'segments_facing_pavement': nhit, 'area_m2': R2(fill.area), 'grass_cut_m2': R2(grass_cut),
             'bridge_corridors_m2': R2(brg.area), 'rings': len(polys)}
    out = {'kind': 'paved', 'src': 'inf', 'polys': polys,
           'evidence': 'OSM apron ways stop 15-40 m short of the T1 / T2 airside facades (no apron polygon under the fixed links, '
                       'rotundas and VDGS posts); the band is paved in the Sentinel-2 hint (S2B_51RUQ_20261014, 10 m) and is a dark '
                       'asphalt service road in photo 09 (Commons, T2)',
           'rule': 'facade-to-pavement quads (reach <= %g m, + %g m overlap) and pier-tip corner discs, inside the aerodrome, outside '
                   'buildings, minus Sentinel-2 grass pixels (L < %g and g > %g, or g > %g; clusters >= 3 px); plus %g m fixed-link '
                   'corridors, %g m rotunda discs and %g m contact-stand centreline strips nose -> facade [inf]' % (FILL_REACH, FILL_OVERLAP, GRASS_L, GRASS_G, GRASS_G_ANY, WALK_W, ROT_R, STAND_CL_W),
           'drawn_as': "asphalt ('paved' kind of the core pavement hook, js/live/terminals.js)"}
    return out, stats



# ---------------------------------------------------------------------------------------------- stand-head fill (fix round 2, R1)
# Since gates fix round 1 the OSM stop node (aeroway=parking_position) is the NOSE-WHEEL stop (MH 5001-2021 6.2.16-7): the
# class reference's nose tip lies nose_gear_m ahead of it (data/sha_stands.json class_ref, obs per type), the painted
# envelope front a further 3.75 m (table 4.13.5 note a, caac_markings.js stand.noseE) and the equipment areas (6.2.20) lie
# beside the nose up to about that front (js/live/caac_decals.js). At the edge stands the OSM apron polygons end at or just
# ahead of the stop nodes (T2 apron 2: 212-219, 278-290; east apron: 318-322, 339-342; business apron 306; west remote apron
# 4: 401-413; apron 6: 601-608; east remote: 501-525), so noses, envelope fronts, equipment areas, stairs and signs stood on
# grass (docs/phase2/review_visual_fix1.md R1). The Sentinel-2 hint reads neutral grey there, not grass (e.g. 286-290: L
# 0.14-0.20 from the apron edge to the aerodrome boundary; 401-413: L 0.13-0.18 in the first 10 m pixel beyond the edge,
# grass beyond it), so the apron is taken to continue [inf: OSM apron gap ahead of the stand heads]. Rule [inf]:
#   1. per stand, the head rectangle in the decals' stand frame (shifted by nose_gear_m): u from -HEAD_BACK x length (contact
#      stands; remote stands: from the envelope's back, -length - 3 m, as caac_decals.js) to the envelope front + HEAD_FRONT_PAD, v = +-(span / 2 + B + HEAD_SIDE_PAD) (B = table 4.13.5 by code letter); the part of
#      it outside the pavement (aprons, taxiway / runway surfaces and shoulders, the H2 facade fill) is the stand's need;
#      stands needing < HEAD_MIN_M2 are skipped;
#   2. the needs are joined (HEAD_CLOSE m closing: one band along a row, no teeth), cut to the aerodrome polygon, outside
#      every building and OSM water area, minus the Sentinel-2 grass pixels (the H2 test above, clusters >= 3 px);
#   3. drawn as apron concrete (airfield map G 255: same surface and night flood as the apron it continues), overlapping the
#      apron by APRON_OVERLAP m and never drawn over taxiway / runway pavement or the H2 asphalt band.
HEAD_BACK, HEAD_FRONT_PAD, HEAD_SIDE_PAD = 0.5, 3.0, 2.0   # [inf] (front pad: pavedAt samples a 2 m grid of a blurred map)
HEAD_MIN_M2, HEAD_CLOSE, APRON_OVERLAP = 5.0, 6.0, 2.0     # m², m, m [inf]


def caac_stand():
    """clearB (table 4.13.5), noseE and classLetter from js/live/caac_markings.js (the ONE CAAC table; not duplicated here)"""
    t = open(CAAC_JS, encoding='utf-8').read()

    def obj(key):
        m = re.search(r'\b' + key + r':\s*P\((\{[^}]*\})', t)
        if not m:
            raise SystemExit('caac_markings.js: ' + key + ' not found')
        return json.loads(re.sub(r'(\w+)\s*:', r'"\1":', m.group(1)).replace("'", '"'))
    m = re.search(r'\bnoseE:\s*P\(([\d.]+)', t)
    if not m:
        raise SystemExit('caac_markings.js: noseE not found')
    return {'clearB': obj('clearB'), 'classLetter': obj('classLetter'), 'noseE': float(m.group(1))}


def stand_frame(s, refs, C):
    """the decals' stand frame: world(u, v) with u along the heading from the class nose tip, v to the right; + dims"""
    ref = refs.get(s['cls']) or refs.get('C') or {'length_m': 44.5, 'span_m': 35.8, 'nose_gear_m': 0.0}
    L = s.get('len_max') or ref['length_m']; Sp = s.get('span_max') or ref['span_m']; ng = ref.get('nose_gear_m') or 0.0
    B = C['clearB'].get(C['classLetter'].get(s['cls'], 'C'), 4.5)
    h = math.radians(s['hdg']); f = (math.sin(h), -math.cos(h)); r = (-f[1], f[0]); n = s['nose']

    def W(u, v):
        return (n[0] + f[0] * (u + ng) + r[0] * v, n[1] + f[1] * (u + ng) + r[1] * v)
    return W, {'L': L, 'Sp': Sp, 'ng': ng, 'B': B, 'E': C['noseE']}


def stand_head_fill(A, S, h2):
    C = caac_stand(); refs = S.get('class_ref') or {}
    aprons = unary_union([Polygon(a['ring'], a.get('holes') or []).buffer(0) for a in A['aprons']])
    other = unary_union([Polygon(p['ring']).buffer(0) for k in ('taxiway', 'runway', 'taxiway_shoulders', 'runway_shoulders_blast_pads')
                         for p in A['surfaces'].get(k, [])])
    pav = unary_union([aprons, other, h2])
    aer = unary_union([Polygon(r).buffer(0) for r in A['aerodrome']['rings']])
    allb = unary_union([poly_of(b) for b in A['buildings']])
    water = unary_union([Polygon(w['ring']).buffer(0) for w in (A.get('context') or {}).get('water_areas', []) if len(w['ring']) >= 3])
    needs, names = [], []
    for s in S['stands']:
        W, d = stand_frame(s, refs, C)
        # contact stands: the front half (the rear meets the terminal and the H2 band); remote stands: the whole envelope length
        u0 = -HEAD_BACK * d['L'] if s.get('bridges') else -d['L'] - 3.0
        u1, hw = d['E'] + HEAD_FRONT_PAD, d['Sp'] / 2 + d['B'] + HEAD_SIDE_PAD
        miss = Polygon([W(u0, -hw), W(u1, -hw), W(u1, hw), W(u0, hw)]).difference(pav)
        if miss.area >= HEAD_MIN_M2:
            needs.append(miss); names.append(s['name'])
    need = unary_union(needs).buffer(HEAD_CLOSE, join_style=2).buffer(-HEAD_CLOSE, join_style=2)
    need = need.intersection(aer).difference(allb).difference(water)
    grass = s2_grass_geom(need.bounds)
    before = need.area
    need = need.difference(grass)
    grass_cut = before - need.area
    fill = need.difference(aprons.buffer(-APRON_OVERLAP, join_style=2)).difference(other).difference(h2).simplify(0.4)
    polys = rings_of(fill, min_area=20.0)
    stats = {'stands_needing': len(names), 'area_m2': R2(fill.area), 'grass_cut_m2': R2(max(0.0, grass_cut)), 'rings': len(polys)}
    out = {'kind': 'apron', 'src': 'inf', 'polys': polys, 'stands': names,
           'evidence': 'OSM apron polygons end at or just ahead of the stop nodes of the edge stands, while the nose-wheel stop '
                       'convention (MH 5001-2021 6.2.16-7; class_ref nose_gear_m) puts the nose, the envelope front (table 4.13.5 '
                       'note a) and the equipment areas (6.2.20) 5-12 m beyond; the Sentinel-2 hint (S2B_51RUQ_20261014, 10 m) '
                       'reads neutral grey, not grass, there',
           'rule': 'per stand, the head rectangle (u from -%g x length (remote stands: -length - 3 m) to the envelope front + %g m, v = +-(span / 2 + B + %g m), '
                   'decals stand frame) outside the pavement and the H2 fill; stands needing >= %g m2; %g m closing; inside the '
                   'aerodrome, outside buildings and water, minus Sentinel-2 grass pixels (the H2 test); drawn as apron, %g m '
                   'overlap with the apron, never over taxiway / runway pavement [inf]' % (HEAD_BACK, HEAD_FRONT_PAD, HEAD_SIDE_PAD, HEAD_MIN_M2, HEAD_CLOSE, APRON_OVERLAP),
           'drawn_as': "apron concrete ('apron' kind of the core pavement hook, js/live/terminals.js)"}
    return out, stats, fill


def stand_head_check(A, S, geoms):
    """stop nodes and class nose tips (and the envelope front centre) outside the pavement + fills, polygon test"""
    C = caac_stand(); refs = S.get('class_ref') or {}
    pav = unary_union([Polygon(a['ring'], a.get('holes') or []).buffer(0) for a in A['aprons']] +
                      [Polygon(p['ring']).buffer(0) for k in ('taxiway', 'runway', 'taxiway_shoulders', 'runway_shoulders_blast_pads')
                       for p in A['surfaces'].get(k, [])] + list(geoms))
    node, tip, front = [], [], []
    for s in S['stands']:
        W, d = stand_frame(s, refs, C)
        if not pav.contains(Point(*s['nose'])):
            node.append(s['name'])
        if not pav.contains(Point(*W(0, 0))):
            tip.append(s['name'])
        if not pav.contains(Point(*W(d['E'], 0))):
            front.append(s['name'])
    return {'stop_nodes_off': node, 'nose_tips_off': tip, 'envelope_fronts_off': front}


def main():
    A = load(AIRPORT); S = load(STANDS); H = load(HEIGHTS)
    B = {b['id']: b for b in A['buildings']}
    CB = {b['id']: b for b in A['context']['buildings']}
    parts, towers, hangars, claims, checks = [], [], [], [], {}

    # ------------------------------------------------------------------------------------------------ T2
    t2 = poly_of(B[T2_ID]); claims.append(T2_ID)
    hb = b3(H, T2_ID)
    Z = {
        'hall': box(-1700, 0, -1238, 900),
        'central': box(-1238, -150, -1098, 492),
        'finger_n': box(-1098, -600, -600, 100),
        'finger_s': box(-1098, 300, -600, 900),
        'arm_n': box(-1300, -600, -1098, -150).union(box(-1300, -600, -1238, 0)),
        'arm_s': box(-1300, 492, -1098, 900),
    }
    T2P = {
        'hall': ('T2 main hall', 22.0, 't2_hall', 'B3 "T2 main hall" 22 +- 4 (Umbra 21.4 + DSM p90 22.2)'),
        'central': ('T2 central concourse and core', 21.0, 't2_concourse', 'B3 Umbra layover on its west wall (x -1140, z 307-490): 21.4 +- 3.3'),
        'finger_n': ('T2 north finger pier', 15.0, 't2_pier', 'rule: apron level + two glazed levels + roof (photos 09, 14, 15) [inf]'),
        'finger_s': ('T2 south finger pier', 15.0, 't2_pier', 'rule (as the north finger) [inf]'),
        'arm_n': ('T2 north linear arm', 15.0, 't2_pier', 'rule (as the finger piers) [inf]'),
        'arm_s': ('T2 south linear arm', 15.0, 't2_pier', 'rule (as the finger piers) [inf]'),
    }
    acc = 0
    for k, z in Z.items():
        g = t2.intersection(z)
        if g.is_empty:
            continue
        nm, h, st, note = T2P[k]
        parts.append(part('t2_' + k, T2_ID, nm, g, h, st, 'inf', note))
        acc += g.area
    checks['t2_area_split_vs_outline'] = [R2(acc), R2(t2.area)]

    # ------------------------------------------------------------------------------------------------ T1
    t1 = poly_of(B[T1_ID]); claims.append(T1_ID)
    tw = A['control_tower']
    # west facade line x_f(z) (points 0-19 / 98-106 of the OSM ring) and north facade line z_f(x) (points 86-98)
    xf = lambda z: 457.0 + (z - 20.0) * 0.047           # noqa: E731
    zf = lambda x: 19.45 - 0.0513 * (x - 467.5)          # noqa: E731

    def west_band(d):
        return Polygon([(300, -100), (xf(-100) + d, -100), (xf(600) + d, 600), (300, 600)])

    def north_band(d):
        return Polygon([(300, -100), (900, -100), (900, zf(900) + d), (300, zf(300) + d)])
    front = t1.intersection(unary_union([west_band(12), north_band(14)]))
    rear = t1.intersection(unary_union([west_band(32), north_band(34)])).difference(front)
    yard = Point(tw['x'], tw['z']).buffer(15, cap_style=3)   # 30 m square yard (a round cut showed as a curved wall)
    rest = t1.difference(unary_union([west_band(32), north_band(34)])).difference(yard)
    north = box(553, -100, 900, 140)
    opening = lambda g: g.buffer(-4, join_style=2).buffer(4, join_style=2).intersection(g)   # noqa: E731  drops slivers < 8 m
    land = opening(rest.intersection(north))
    core = opening(rest.difference(north))
    parts.append(part('t1_conc_front', T1_ID, 'T1 airside concourse (front tier)', front, 9.0, 't1_concourse', 'inf',
                      'B3 photo ratio (photo 02): airside concourse roof 8.9 m (7.3-10.8)'))
    parts.append(part('t1_conc_rear', T1_ID, 'T1 airside concourse (rear tier)', rear, 13.0, 't1_concourse_rear', 'inf',
                      'photo 02 at the B3 scale: set-back upper tier 40 px -> 13 m [inf]'))
    parts.append(part('t1_core', T1_ID, 'T1 airside core', core, 15.0, 't1_core', 'inf', 'rule [inf] (not measured)'))
    parts.append(part('t1_land', T1_ID, 'T1 landside block', land, 24.0, 't1_louvre', 'inf',
                      'rule [inf]; louvre-band facade and glazed clerestory from photos 01 / 03 / 05'))
    claims.append(T1_HALL_ID)
    parts.append(part('t1_hall', T1_HALL_ID, 'T1 central hall', poly_of(B[T1_HALL_ID]), 26.0, 't1_hall', 'inf',
                      'B3 photo ratio (photo 02): central hall roof 26.4 m (23.0-30.1); identification of this OSM way as the hall: '
                      'its west face is where B3 placed the hall front (x ~ 560, z ~ 240) [inf]',
                      # fix round 1 (review L2): photo 02 shows a raised white roof volume over the hall (it carries the red
                      # "上海 SHANGHAI" letters): flat crest, ends sloping down to north and south. Drawn as an arch across the
                      # N-S length (dir = world z): y(s) = rise * (1 - |s|^exp), s = -1..1; the crest stays at the B3 height
                      # (h + roof slab), the eaves are rise lower [inf: rise, exponent and orientation read from photo 02]
                      {'roof_form': {'kind': 'arch', 'rise': 7.0, 'exp': 4.0, 'dir': [0.0, 1.0], 'src': 'inf',
                                     'note': 'photo 02: raised white roof volume, flat crest, sloping N / S ends; crest = B3 height'}}))
    checks['t1_area_split_vs_outline'] = [R2(front.area + rear.area + core.area + land.area + yard.intersection(t1).area), R2(t1.area)]
    checks['t1_tower_in_yard'] = bool(yard.contains(Point(tw['x'], tw['z'])))

    # ------------------------------------------------------------------------------------------------ towers
    claims.append('tower')
    towers.append({
        'id': 'tower_east', 'of': tw['id'], 'name': 'East control tower', 'x': tw['x'], 'z': tw['z'], 'h': tw.get('height_m', 44.5),
        'h_src': 'AIP (mirror)', 'h_note': tw.get('height_evidence', ''), 'src': 'inf', 'form': 'control',
        'form_src': 'photo 02 (MNXANL, CC BY-SA 4.0, 2023): proportions measured at 0.356 m/px (B3 scale), +-0.36 m [inf]',
        'dims': {'shaft_w': 7.7, 'flare_y0': 29.5, 'head_y1': 39.8, 'head_w': 15.8, 'cab_y1': 43.0, 'cab_w0': 10.5, 'cab_w1': 12.1,
                 'roof_w': 12.6, 'slot_w': 0.8, 'window_rows': [32.6, 37.9]},
        'yaw_deg': 177.33, 'yaw_src': 'unknown; aligned with the runway grid [inf]', 'slot_face': 'west (towards the runways, as seen in photo 02)'})
    for i, tid in enumerate(TOWER_SW):
        b = B.get(tid)
        if not b:
            continue
        claims.append(tid)
        g = poly_of(b)
        towers.append({'id': 'tower_sw_%d' % (i + 1), 'of': tid, 'name': 'untyped tower (south-west) %d' % (i + 1), 'form': 'block',
                       'polys': rings_of(g), 'h': b['height_m'], 'h_src': b['height_src'], 'h_note': b['height_evidence'], 'src': 'inf',
                       'form_src': 'OSM man_made=tower (role unknown, added 2026-11-06): footprint extruded to the rule height, '
                                   'plain, rooftop mast [inf]', **frame_of(g)})

    # ------------------------------------------------------------------------------------------------ hangars
    pav = unary_union([Polygon(a['ring']).buffer(0) for a in A['aprons']] +
                      [Polygon(p['ring']).buffer(0) for k in ('taxiway', 'runway') for p in A['surfaces'].get(k, [])])
    for hid, (nm, roof, bays) in HANGARS.items():
        b = B.get(hid)
        if not b:
            continue
        claims.append(hid)
        g = poly_of(b); fr = frame_of(g)
        m = b3(H, hid)
        h = float(m['proposed_m']) if m else b['height_m']
        hnote = (m['method'] + ' (B3, +-%s m)' % m['unc_m']) if m else b['height_evidence']
        # door side: which side of the minimum rectangle has the most airside pavement within 15-70 m in front
        mrr = g.minimum_rotated_rectangle; c = list(mrr.exterior.coords)[:4]
        ctr = mrr.centroid; best, scores = None, []
        for i in range(4):
            p, q = c[i], c[(i + 1) % 4]
            mx, mz = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            nx, nz = mx - ctr.x, mz - ctr.y; nl = math.hypot(nx, nz); nx, nz = nx / nl, nz / nl
            L = math.hypot(q[0] - p[0], q[1] - p[1]); tx, tz = (q[0] - p[0]) / L, (q[1] - p[1]) / L
            band = Polygon([(p[0] + nx * 15, p[1] + nz * 15), (q[0] + nx * 15, q[1] + nz * 15), (q[0] + nx * 70, q[1] + nz * 70), (p[0] + nx * 70, p[1] + nz * 70)])
            s = band.intersection(pav).area / band.area
            scores.append(R2(s))
            if best is None or s > best[0]:
                best = (s, [[R2(p[0]), R2(p[1])], [R2(q[0]), R2(q[1])]], [R2(nx), R2(nz)])
        if best[0] < 0.05:   # no pavement polygon in front of any side: the side whose midpoint is nearest to pavement
            dd = []
            for i in range(4):
                p, q = c[i], c[(i + 1) % 4]; mx, mz = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                nx, nz = mx - ctr.x, mz - ctr.y; nl = math.hypot(nx, nz)
                dd.append((pav.distance(Point(mx + nx / nl * 5, mz + nz / nl * 5)), i, nx / nl, nz / nl))
            d0, i, nx, nz = min(dd); p, q = c[i], c[(i + 1) % 4]
            best = (0.0, [[R2(p[0]), R2(p[1])], [R2(q[0]), R2(q[1])]], [R2(nx), R2(nz)]); scores.append('nearest-pavement side %d (%.0f m)' % (i, d0))
        hangars.append({'id': hid, 'of': hid, 'name': nm, 'polys': rings_of(g), 'h': h, 'h_src': 'inf', 'h_note': hnote, 'roof': roof, 'bays': bays,
                        'door': {'edge': best[1], 'normal': best[2], 'pavement_share': R2(best[0]), 'side_scores': scores,
                                 'rule': 'side of the minimum rectangle with the most airside pavement 15-70 m in front [inf]'},
                        'roof_src': 'aerial photos 21 / 22 (form only) [inf]', 'src': 'inf', **fr})

    # ------------------------------------------------------------------------------------------------ other airport buildings
    for b in A['buildings']:
        if b['id'] in claims:
            continue
        st, h, note = STYLE_BY_ID.get(b['id'], (STYLE_BY_KIND.get(b['kind'], 'generic'), None, ''))
        claims.append(b['id'])
        g = poly_of(b)
        parts.append(part(b['id'], b['id'], b.get('name_en') or b.get('name') or b['kind'], g, h or b['height_m'], st, b['height_src'],
                          b['height_evidence'], {'kind': b['kind'], 'note': note}))
    for cid, (st, nm) in HUB_CONTEXT.items():
        b = CB.get(cid)
        if not b:
            continue
        claims.append(cid)
        parts.append(part(cid, cid, nm, poly_of(b), b['height_m'], st, b['height_src'], b['height_evidence'], {'kind': b['kind'], 'context': True}))

    # ------------------------------------------------------------------------------------------------ roof overhangs [inf]
    # roof slab beyond the walls: T2 main hall (deep flat roof edge, photos 07 / 08 / 11), T1 halls (photos 01 / 03 / 05),
    # the railway station; mitred buffer of the part outline
    OVER = {'t2_hall': 6.0, 't1_hall': 3.0, 't1_louvre': 3.0, 'station': 6.0}
    for p in parts:
        d = OVER.get(p['style'])
        if not d:
            continue
        g = unary_union([Polygon(pl[0], pl[1:]) for pl in p['polys']])
        p['roof_polys'] = rings_of(g.buffer(d, join_style=2, mitre_limit=2.0).simplify(0.2))
        p['roof_overhang_m'] = d

    # ------------------------------------------------------------------------------------------------ airside fill (fix 1, H2)
    fill, fill_stats = airside_fill(A, S, [poly_of(B[i]) for i in AIRSIDE_FILL_OF if i in B])
    checks['airside_fill'] = fill_stats
    # ------------------------------------------------------------------------------------------------ stand-head fill (fix 2, R1)
    h2 = unary_union([Polygon(pl[0], pl[1:]).buffer(0) for pl in fill['polys']])
    head, head_stats, head_geom = stand_head_fill(A, S, h2)
    checks['stand_head_fill'] = head_stats
    checks['stand_heads_unpaved_before'] = stand_head_check(A, S, [h2])
    checks['stand_heads_unpaved'] = stand_head_check(A, S, [h2, head_geom])

    # ------------------------------------------------------------------------------------------------ checks
    # every bridge attach point (OSM gate node on the facade) must lie on a T1 / T2 part boundary (within 1.5 m)
    tparts = [p for p in parts if p['of'] in (T1_ID, T2_ID)]
    bnd = unary_union([Polygon(pl[0], pl[1:]).boundary for p in tparts for pl in p['polys']])
    dmax, nb = 0.0, 0
    for s in S['stands']:
        for br in s.get('bridges') or []:
            dmax = max(dmax, bnd.distance(Point(*br['attach']))); nb += 1
    checks['bridge_attach_on_facade'] = {'n': nb, 'max_dist_m': R2(dmax)}

    src_files = [AIRPORT, STANDS, HEIGHTS, S2HINT, CAAC_JS, os.path.abspath(__file__)]
    out = {
        'what': 'Parametric building volumes of SHA Live 3D (terminals T1 / T2 split into piers and halls, control towers, hangars, '
                'hub, other airport buildings), for js/world/buildings3d.js',
        'licence': 'ODbL 1.0 (derived from OpenStreetMap outlines); heights and styles are our modelling parameters',
        'attribution': '(c) OpenStreetMap contributors (ODbL); B3 heights (Copernicus WorldDEM-30, Umbra Open Data CC BY 4.0, Commons photo '
                       'CC BY-SA 4.0 by MNXANL: see data/meas/b3_building_heights.json); proportions from Commons photos (docs/phase1/photos_credits.md)',
        'generator': 'tools/buildings/build_buildings3d.py',
        'inputs_sha256_16': {os.path.relpath(f, ROOT): hashlib.sha256(open(f, 'rb').read()).hexdigest()[:16] for f in src_files},
        'frame': A['frame']['id'],
        'src_legend': {'obs': 'observed (OSM outline, AIP fact, measurement)', 'inf': 'inferred (rule, modelling parameter, photo reading)'},
        'note': 'all heights inf (B3: measurements or rules); every split zone, depth, roof form and facade style is a modelling '
                'parameter [inf]; the OSM outline (the airside facade) is not moved',
        'parts': parts, 'towers': towers, 'hangars': hangars, 'claims': claims, 'checks': checks,
        'airside_fill': fill, 'stand_head_fill': head,
        'counts': {'parts': len(parts), 'towers': len(towers), 'hangars': len(hangars), 'claims': len(claims), 'airside_fill_rings': len(fill['polys']),
                   'stand_head_fill_rings': len(head['polys'])},
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    with open(OUT_JS, 'w', encoding='utf-8') as fh:
        fh.write('// generated by tools/buildings/build_buildings3d.py - do not edit. (c) OpenStreetMap contributors (ODbL); heights / '
                 'styles: modelling parameters (inf), see data/sha_buildings3d.json\n')
        fh.write('window.SHA_BUILDINGS3D = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(json.dumps(out['counts']), json.dumps(checks))
    for p in parts[:14]:
        print(p['id'], p['style'], p['h'], len(p['polys']), p['area'])
    for h in hangars:
        print(h['id'], h['name'], h['h'], h['roof'], h['door']['side_scores'], h['door']['normal'])


if __name__ == '__main__':
    main()
