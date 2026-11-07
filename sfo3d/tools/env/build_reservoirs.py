#!/usr/bin/env python3
"""Peninsula reservoirs and the SFPUC watershed for the terrain (close-out round 3, env-14; engine_closeout.md §2).

The world had no water in the San Andreas valley west of the airport and drew city blocks there (live3: a diagonal strip
of urban bake), while San Andreas Lake and the Crystal Springs reservoirs lie in that valley inside the undeveloped San
Francisco Peninsula Watershed. Sources (cached in refs/cache/env_src/osm/, SOURCES.json beside them):
  - OpenStreetMap (ODbL 1.0, (c) OpenStreetMap contributors) via the OSM API v0.6 `/way/<id>/full` and
    `/relation/<id>/full` (ids found with Nominatim, 2026-11-07):
      way 33449157 San Andreas Lake (natural=water, water=reservoir, v7 2024-08-25),
      way 815759758 Lower Crystal Springs Reservoir (ele=85, v7 2024-08-25),
      way 23782143 Upper Crystal Springs Reservoir (ele=87, v66 2023-11-09),
      relation 3944756 San Francisco Peninsula Watershed (boundary=protected_area, leisure=nature_reserve, operator
      SFPUC, v18 2023-11-20; OSM fixme: "newer CPAD data (2019b) show this needs updating" - kept as tagged);
  - water-surface elevations: San Andreas Lake 134.35 m NAVD88 from the USGS 3DEP 1 m DEM (Elevation Point Query
    Service, epqs.nationalmap.gov, acquisition 2023, public domain; hydro-flattened water surface), Crystal Springs
    from the OSM `ele` tags (85 / 87 m; source of the tag not stated: 2nd; EPQS timed out for them on 2026-11-07).
World y = elevation (m NAVD88) - 4.0 + GROUND_Y 3 (the airfield level GROUND_Y = SFO field elevation 13.1 ft = 4.0 m,
js/live/app.js alsPlane). Levels vary with storage (NV: the 3DEP value is one day of 2023).
Output: js/env/reservoirs_data.js (generated, do not edit): {lakes: [{name, osm, level_y, src, ring [[x, z]...],
tris [i...] (up-facing: clockwise in x-z)}], watershed: {name, osm, rings [[[x, z]...]...]}} in world metres (x east, z south; tools/geo_frame.py).
"""
import json, os, sys, xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF   # noqa: E402

SRC = os.path.join(ROOT, 'refs', 'cache', 'env_src', 'osm')
OUT = os.path.join(ROOT, 'js', 'env', 'reservoirs_data.js')
FIELD_ELEV_M, GROUND_Y = 13.1 * 0.3048, 3.0
LAKES = [  # (way id, name, elevation m NAVD88, source tag)
    (33449157, 'San Andreas Lake', 134.35, 'V: USGS 3DEP 1 m (EPQS, 2023)'),
    (815759758, 'Lower Crystal Springs Reservoir', 85.0, '2nd: OSM ele tag'),
    (23782143, 'Upper Crystal Springs Reservoir', 87.0, '2nd: OSM ele tag'),
]
WATERSHED_REL = 3944756


def parse(fn):
    t = ET.parse(fn).getroot()
    nodes = {n.get('id'): (float(n.get('lat')), float(n.get('lon'))) for n in t.findall('node')}
    ways = {w.get('id'): [nd.get('ref') for nd in w.findall('nd')] for w in t.findall('way')}
    return t, nodes, ways


def world(nodes, refs):
    return [tuple(round(v, 1) for v in GF.wgs84_to_world(*nodes[r])) for r in refs]


def simplify(ring, tol=4.0):
    """Douglas-Peucker on a closed ring (world m), keeps the shape within tol (the terrain grid is 15 m near the airport,
    the lakes are 4-10 km from it where the grid is ~60-200 m)."""
    def dp(pts):
        if len(pts) < 3: return pts
        (x0, z0), (x1, z1) = pts[0], pts[-1]; L = max(((x1 - x0) ** 2 + (z1 - z0) ** 2) ** 0.5, 1e-9)
        dmax, k = 0, 0
        for i in range(1, len(pts) - 1):
            x, z = pts[i]; d = abs((x1 - x0) * (z0 - z) - (x0 - x) * (z1 - z0)) / L
            if d > dmax: dmax, k = d, i
        if dmax <= tol: return [pts[0], pts[-1]]
        a = dp(pts[:k + 1]); b = dp(pts[k:]); return a[:-1] + b
    r = ring[:-1] if ring[0] == ring[-1] else ring
    i0 = 0; i1 = max(range(len(r)), key=lambda i: (r[i][0] - r[0][0]) ** 2 + (r[i][1] - r[0][1]) ** 2)
    a = dp(r[i0:i1 + 1]); b = dp(r[i1:] + [r[0]])
    return a[:-1] + b[:-1]


def area(r):
    return 0.5 * sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))


def earcut(r):
    """ear clipping of a simple polygon (CCW in x-z after orientation fix); returns index triples"""
    idx = list(range(len(r))); tris = []
    if area(r) < 0: idx.reverse()
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    def inside(p, a, b, c): return cross(a, b, p) >= 0 and cross(b, c, p) >= 0 and cross(c, a, p) >= 0
    guard = 0
    while len(idx) > 3 and guard < 100000:
        guard += 1; n = len(idx); found = False
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]; a, b, c = r[i0], r[i1], r[i2]
            if cross(a, b, c) <= 0: continue
            if any(inside(r[j], a, b, c) for j in idx if j not in (i0, i1, i2)): continue
            tris += [i0, i1, i2]; idx.pop(k); found = True; break
        if not found: break
    if len(idx) == 3: tris += idx
    return tris


def rings_of(t, nodes, ways, rel_id):
    rel = [r for r in t.findall('relation') if r.get('id') == str(rel_id)][0]
    segs = [ways[m.get('ref')][:] for m in rel.findall('member') if m.get('type') == 'way' and m.get('role') == 'outer']
    rings = []
    while segs:
        cur = segs.pop(0)
        while cur[0] != cur[-1]:
            for i, s in enumerate(segs):
                if s[0] == cur[-1]: cur += s[1:]; segs.pop(i); break
                if s[-1] == cur[-1]: cur += s[::-1][1:]; segs.pop(i); break
            else: break
        rings.append(cur)
    return [world(nodes, r) for r in rings if len(r) > 3]


def main():
    out = {'note': __doc__.split('\n')[0], 'licence': 'ODbL 1.0 - contains information from OpenStreetMap (c) OpenStreetMap contributors; USGS 3DEP public domain',
           'level_y_rule': 'elevation m NAVD88 - 4.0 + GROUND_Y 3', 'lakes': [], 'watershed': None}
    for wid, name, elev, src in LAKES:
        t, nodes, ways = parse(os.path.join(SRC, f'way_{wid}.xml'))
        ring = simplify(world(nodes, ways[str(wid)]))
        if area(ring) < 0: ring.reverse()
        tris = earcut(ring)
        # earcut works counter-clockwise in (x, z); with z pointing south that is a DOWN-facing triangle (y-component of
        # (b - a) x (c - a) < 0), culled from above. The world's water / ground meshes face up (clockwise in (x, z)):
        # flip each triangle (close-out round 3: the first live3 reservoir render showed no lakes)
        tris = [v for k in range(0, len(tris), 3) for v in (tris[k], tris[k + 2], tris[k + 1])]
        out['lakes'].append({'name': name, 'osm': f'way {wid}', 'elev_m': elev, 'level_y': round(elev - FIELD_ELEV_M + GROUND_Y, 2), 'src': src,
                             'area_km2': round(abs(area(ring)) / 1e6, 3), 'ring': [list(p) for p in ring], 'tris': tris})
        print(name, len(ring), 'vertices', len(tris) // 3, 'triangles', round(abs(area(ring)) / 1e6, 2), 'km2, level y', out['lakes'][-1]['level_y'])
    t, nodes, ways = parse(os.path.join(SRC, f'rel_{WATERSHED_REL}_full.xml'))
    rings = [simplify(r, 15.0) for r in rings_of(t, nodes, ways, WATERSHED_REL)]
    out['watershed'] = {'name': 'San Francisco Peninsula Watershed', 'osm': f'relation {WATERSHED_REL}', 'rings': [[list(p) for p in r] for r in rings],
                        'area_km2': round(sum(abs(area(r)) for r in rings) / 1e6, 1)}
    print('watershed rings', len(rings), [len(r) for r in rings], out['watershed']['area_km2'], 'km2')
    with open(OUT, 'w') as f:
        f.write('// generated by tools/env/build_reservoirs.py - ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap contributors; USGS 3DEP (public domain). Do not edit.\n')
        f.write('export const RESERVOIRS = ' + json.dumps(out, separators=(',', ':')) + ';\n')
    print('wrote', OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
