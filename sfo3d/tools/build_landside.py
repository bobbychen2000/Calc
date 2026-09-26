#!/usr/bin/env python3
"""Landside roads and surface car parks from OpenStreetMap -> data/sfo_landside.json / .js (static fix-up, 26 Sep 2026).

Why: review round 4 found js/live/airport.js painting a hand-drawn, unsourced landside into the ground bake (a 236 m
disc round the terminal centre, freeway bands and rectangles as "parking"). This replaces it with mapped geometry.

Source: OSM ways highway=* and amenity=parking, Overpass download 26 Sep 2026 03:04 UTC (database 2026-09-26T03:03Z),
cached in refs/cache/osm/overpass_landside_*.json (query and endpoint in overpass_landside_latest.meta.json).
Licence: ODbL 1.0 - contains information from OpenStreetMap (c) OpenStreetMap contributors (docs/ATTRIBUTION.md).

What is kept (landside only):
  * roads: highway in ROAD_CLASSES, NOT tunnel / building_passage / layer < 0; bridge=yes / layer >= 1 are kept with
    `elevated` true (their footprint is paved ground; the app does not draw them as at-grade roads); clipped OUT of the
    airside (OSM aeroway=apron polygons, SFO Museum taxiway / runway polygons, the terminal complex, the ramp outline of
    sfo_details.json, each + 2 m), so apron service lanes (paint on concrete) are not drawn as roads;
  * parking: amenity=parking areas, kind 'parking' (surface / street_side / unset) or 'garage' (multi-storey: its
    footprint is paved / built ground), clipped the same way.
Widths (roads are OSM centrelines): OSM `width` where tagged (1 way); else `lanes` x 3.6 m (inferred: the FHWA 12 ft
lane); else a per-class default (DEFAULT_W, inferred - OSM has no width) - `w_src` says which.
Frame: tools/geo_frame.py (= js/geo.js) world x east / z south.
Usage: python3 tools/build_landside.py
"""
import json, os, sys
import numpy as np
from shapely.geometry import LineString, Polygon, MultiLineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import geo_frame as GF  # noqa: E402

CACHE = os.path.join(ROOT, 'refs', 'cache', 'osm')
ROAD_CLASSES = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link',
                'tertiary', 'tertiary_link', 'unclassified', 'residential', 'service'}
# inferred carriageway widths (m) where OSM has neither width nor lanes: 2 lanes of 3.6 m for through roads, one lane
# plus margin for links / service roads / parking aisles
DEFAULT_W = {'motorway': 7.2, 'trunk': 7.2, 'primary': 7.2, 'secondary': 7.2, 'tertiary': 7.2, 'unclassified': 6.0,
             'residential': 6.0, 'motorway_link': 4.5, 'trunk_link': 4.5, 'primary_link': 4.5, 'secondary_link': 4.5,
             'tertiary_link': 4.5, 'service': 4.0}


def world(geom):
    return [GF.wgs84_to_world(g['lat'], g['lon']) for g in geom]


def num(v):
    try: return float(str(v).split(';')[0].replace('m', '').strip())
    except (TypeError, ValueError): return None


def main():
    meta = json.load(open(os.path.join(CACHE, 'overpass_landside_latest.meta.json')))
    d = json.load(open(os.path.join(CACHE, meta['file'])))
    osm_air = json.load(open(os.path.join(CACHE, 'ksfo_osm_parsed.json')))
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    air = [Polygon([GF.wgs84_to_world(la, lo) for la, lo in a['pts']]).buffer(0) for a in osm_air['aprons'] if len(a['pts']) >= 4]
    for group in (A['taxiways'], A['runways']):
        for t in group:
            for poly in t['polys']: air.append(Polygon(poly[0], poly[1:]).buffer(0))
    for poly in A['terminalComplex']: air.append(Polygon(poly[0]).buffer(0))
    # the ramp outline of data/sfo_details.json (apron between the terminals; airside service lanes there are paint on
    # concrete, not roads)
    for poly in json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))['apron']: air.append(Polygon(poly[0], poly[1:]).buffer(0))
    airside = unary_union(air).buffer(2.0)
    # the app bakes the ground only inside APT_RECT (js/world/airfield.js: s0 -2800, t0 -1760, w 4700, h 3220 m in the
    # airport grid); everything is clipped to that rectangle (+50 m)
    s0, t0, w_, h_ = -2800.0, -1760.0, 4700.0, 3220.0
    rect = Polygon([GF.st_to_world(s0 - 50, t0 - 50), GF.st_to_world(s0 + w_ + 50, t0 - 50), GF.st_to_world(s0 + w_ + 50, t0 + h_ + 50), GF.st_to_world(s0 - 50, t0 + h_ + 50)])
    airside = airside.union(rect.exterior.buffer(0.01)).union(Polygon([(-1e5, -1e5), (1e5, -1e5), (1e5, 1e5), (-1e5, 1e5)]).difference(rect))
    roads, parks = [], []
    n_elev = n_air = 0
    for e in d['elements']:
        t = e.get('tags', {})
        if e['type'] != 'way' or 'geometry' not in e: continue
        if t.get('highway') in ROAD_CLASSES and t.get('area') != 'yes':
            lay = num(t.get('layer')) or 0.0
            if t.get('tunnel', 'no') != 'no' or lay < 0 or t.get('covered') == 'yes':
                n_elev += 1; continue
            # elevated roads (terminal departures level, flyovers): kept as kind 'elevated' - their FOOTPRINT is paved
            # ground in the bake (the viaducts stand on roads / pavement), but they are not drawn as an at-grade road
            elev = t.get('bridge', 'no') != 'no' or lay >= 1
            ls = LineString(world(e['geometry']))
            if ls.length < 1.0: continue
            keep = ls.difference(airside)
            if keep.is_empty: n_air += 1; continue
            parts = list(keep.geoms) if isinstance(keep, MultiLineString) else [keep] if keep.geom_type == 'LineString' else []
            w = num(t.get('width')); src = 'osm width'
            if w is None and num(t.get('lanes')):
                w = num(t['lanes']) * 3.6; src = 'osm lanes x 3.6 m (inferred lane width)'
            if w is None:
                w = DEFAULT_W[t['highway']] + (2.0 if t.get('service') == 'parking_aisle' else 0.0); src = 'class default (inferred)'
            for p in parts:
                if p.length < 2.0: continue
                roads.append({'osm_id': e['id'], 'kind': t['highway'], 'w': round(w, 1), 'w_src': src, 'elevated': elev,
                              'pts': [[round(x, 1), round(z, 1)] for x, z in p.simplify(0.5).coords]})
        elif t.get('amenity') == 'parking' and t.get('parking') in (None, 'surface', 'street_side', 'lane', 'multi-storey'):
            pts = world(e['geometry'])
            if len(pts) < 4 or pts[0] != pts[-1] and np.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) > 0.5: continue
            pg = Polygon(pts).buffer(0).difference(airside)
            for g in (getattr(pg, 'geoms', None) or [pg]):
                if g.is_empty or g.area < 50: continue
                parks.append({'osm_id': e['id'], 'kind': 'garage' if t.get('parking') == 'multi-storey' else 'parking', 'access': t.get('access'),
                              'pts': [[round(x, 1), round(z, 1)] for x, z in list(g.simplify(0.5).exterior.coords)[:-1]]})
    res = {'frame': GF.FRAME_ID,
           'licence': 'ODbL 1.0 - contains information from OpenStreetMap (c) OpenStreetMap contributors, '
                      'https://www.openstreetmap.org/copyright; see docs/ATTRIBUTION.md',
           'source': 'OSM Overpass %s, database %s (%s)' % (meta['endpoint'], meta['osm_base'], meta['file']),
           'note': 'landside roads (OSM centrelines with widths: osm width / lanes x 3.6 m / class default - see w_src; '
                   'elevated = bridge / layer >= 1: only their footprint counts as paved ground, not an at-grade road) and car '
                   'parks (kind parking = surface, garage = multi-storey footprint), clipped out of the airside (OSM aprons, '
                   'SFO Museum taxiways / runways / terminal complex, the ramp outline of sfo_details.json, + 2 m); tunnels '
                   'and layer < 0 are not included. Generated by '
                   'tools/build_landside.py; replaces the hand-drawn landside() of js/world/airfield.js in the live app.',
           'roads': roads, 'parking': parks}
    json.dump(res, open(os.path.join(ROOT, 'data', 'sfo_landside.json'), 'w'), separators=(',', ':'))
    open(os.path.join(ROOT, 'data', 'sfo_landside.js'), 'w').write(
        '// generated by tools/build_landside.py - ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap '
        'contributors (docs/ATTRIBUTION.md)\nexport const LANDSIDE = ' + json.dumps(res, separators=(',', ':')) + ';\n')
    from collections import Counter
    print('roads %d (%s), parking %d, elevated / tunnel skipped %d, airside-only skipped %d' % (
        len(roads), dict(Counter(r['w_src'].split(' (')[0] for r in roads)), len(parks), n_elev, n_air))
    print('wrote data/sfo_landside.json / .js (%d KB)' % (os.path.getsize(os.path.join(ROOT, 'data', 'sfo_landside.js')) // 1024))


if __name__ == '__main__':
    main()
