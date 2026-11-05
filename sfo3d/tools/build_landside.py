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
Static close-out (2026-11-04): access=no service paths on the airfield -> `airside_paths` (concrete, width / offset measured
on NAIP 2024; were drawn as 4 m landside asphalt); `level` > 0 / 'Level N' names / aisles inside multi-storey garages are
elevated (only their footprint is paved ground). The OSM extract is pinned (tools/xcheck/fetch_osm.py, database
2026-09-26T03:03:01Z).
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


AIRFIELD_M, AIRFIELD_TW_M = 250, 120     # airfield zone for access=no service paths (runway centreline / taxiway pavement)
_NAIP = {}


def _naip():
    if not _NAIP:
        m = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
        _NAIP.update(m=m, im=np.load(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r'))
    return _NAIP


def measure_band(p, t, half=6.0, step=0.25, info=False):
    """bright, unsaturated band across the line through p (direction t) on NAIP 2024: grey level profile over +-half m,
    averaged over 3 m along; the band = the contiguous run round the brightest sample above (grass median + 60 % of the
    contrast). -> (centre offset m (+ = right of t), width m) or None (no band: contrast < 25 grey levels or saturated).
    info=True adds a third value: True when a flank (0.5-2.5 m beyond either band edge) is itself unsaturated ground
    (>= 60 % of its samples with max-min channel spread < FLANK_SAT) - the band is then a light line INSIDE wider
    pavement (road edge / lane paint, a kerb), not a path across the field (round 2: 2.7 km of 1-1.5 m 'paths' were
    such lines on the asphalt perimeter road)"""
    from scipy.ndimage import map_coordinates
    N = _naip(); m = N['m']; res, x0, z0 = m['res'], m['x0'], m['z0']
    t = np.asarray(t, float) / np.linalg.norm(t); n = np.array([-t[1], t[0]])
    o = np.arange(-half, half + 1e-9, step); a = np.linspace(-1.5, 1.5, 7)
    O, Aa = np.meshgrid(o, a); X = p[0] + O * n[0] + Aa * t[0]; Z = p[1] + O * n[1] + Aa * t[1]
    r = (Z - z0) / res - 0.5; c = (X - x0) / res - 0.5
    r0, c0 = int(np.floor(r.min())) - 1, int(np.floor(c.min())) - 1
    if r0 < 0 or c0 < 0: return None
    sub = np.asarray(N['im'][r0:int(np.ceil(r.max())) + 2, c0:int(np.ceil(c.max())) + 2], np.float32)
    ch = [map_coordinates(sub[..., k], [r - r0, c - c0], order=1, mode='nearest').mean(0) for k in range(3)]
    g = (ch[0] + ch[1] + ch[2]) / 3; sat = np.max(ch, 0) - np.min(ch, 0)
    bg = np.median(g); k = int(np.argmax(g)); con = g[k] - bg
    if con < 25 or sat[k] > 35: return None
    thr = bg + 0.6 * con; i0 = k; i1 = k
    while i0 > 0 and g[i0 - 1] >= thr: i0 -= 1
    while i1 < len(g) - 1 and g[i1 + 1] >= thr: i1 += 1
    if i0 == 0 or i1 == len(g) - 1: return None               # band wider than the window: not a path
    if not info: return float((o[i0] + o[i1]) / 2), float(o[i1] - o[i0] + step)
    fl = int(round(0.5 / step)), int(round(2.5 / step))
    paved = any(len(f) and np.mean(f < FLANK_SAT) >= 0.6 for f in (sat[max(0, i0 - fl[1]):max(0, i0 - fl[0])], sat[i1 + fl[0]:i1 + fl[1]]))
    return float((o[i0] + o[i1]) / 2), float(o[i1] - o[i0] + step), bool(paved)


PATH_STEP = 2.5          # m between NAIP profiles along an airside path
PATH_OUTLIER = 1.0       # m: a profile whose band centre is this far from the local median (+-20 m) is another feature
PATH_SMOOTH = 12.5       # m: half window of the running median of the band centre (piecewise offset, not one per way)
PATH_GAP = 15.0          # m: shorter runs without an imaged band inside an imaged stretch are bridged (crossings, shadows)
PATH_MIN = 10.0          # m: shortest imaged stretch drawn
PATH_W_MIN = 1.75        # m: a narrower imaged band is a paint line / kerb, not a vehicle path (inferred: a 0.5 m NAIP pixel
                         # blurs a 4-12 in line to 0.75-1.5 m; the narrowest airside vehicles are ~2 m wide)
FLANK_SAT = 22.0         # NAIP max-min channel spread below which a flank counts as pavement (asphalt / concrete 3-17,
                         # dry grass / soil 30-50 on the profiles of round 2; measured, tools/build_landside.py notes)


def measure_path(e, ls, t):
    """airside service path -> list of stretches (dicts). NAIP 2024 profiles every PATH_STEP m (measure_band); outliers
    off the local median dropped; the drawn centre = OSM station + running-median band offset along the SAME normal
    measure_band uses (n = [-t_z, t_x], + = right of travel in the x-east / z-south world frame); drawn only where NAIP
    images the band (stretches; gaps < PATH_GAP m bridged), width = median band width of the stretch.
    Round 2 (2026-11-05, review static-v1): the round-1 code moved the whole way by ONE median offset with shapely
    parallel_offset, whose 'right' is right in a y-UP frame = LEFT in this z-south frame - the drawn bands ended ~2x the
    offset from the imaged path. Shapely's side convention is no longer used."""
    from shapely.ops import substring
    L = ls.length
    S = np.arange(PATH_STEP / 2, L, PATH_STEP) if L > PATH_STEP else np.array([L / 2])
    Q = np.zeros((len(S), 2)); N = np.zeros((len(S), 2)); O = np.full(len(S), np.nan); Wd = np.full(len(S), np.nan)
    LINE = np.zeros(len(S), bool)
    for i, s_ in enumerate(S):
        q0 = ls.interpolate(max(0, s_ - 2)); q1 = ls.interpolate(min(L, s_ + 2)); q = ls.interpolate(s_)
        tt = np.array([q1.x - q0.x, q1.y - q0.y]); Q[i] = (q.x, q.y)
        nt = np.linalg.norm(tt)
        if nt < 1e-6: continue
        tt /= nt; N[i] = (-tt[1], tt[0])                       # measure_band's normal
        r = measure_band((q.x, q.y), tt, info=True)
        if r and (r[2] or r[1] < PATH_W_MIN): LINE[i] = True   # a light line inside wider pavement / a paint line: not a path band
        elif r: O[i], Wd[i] = r[0], r[1]
    ok = ~np.isnan(O)
    for _ in range(2):                                         # drop profiles that caught another bright feature
        idx = np.where(ok)[0]
        if not len(idx): break
        med = np.array([np.median(O[idx[np.abs(S[idx] - S[i]) <= 20.0]]) for i in idx])
        ok[idx[np.abs(O[idx] - med) > PATH_OUTLIER]] = False
    idx = np.where(ok)[0]
    n_ok = len(idx); frac = n_ok / len(S)
    # stretches: stations within 2 profiles of an accepted one; runs merged across gaps < PATH_GAP
    cov = np.zeros(len(S), bool)
    for i in idx: cov[max(0, i - 2):i + 3] = True
    runs, i = [], 0
    while i < len(S):
        if cov[i]:
            j = i
            while j + 1 < len(S) and cov[j + 1]: j += 1
            runs.append([i, j]); i = j + 1
        else: i += 1
    merged = []
    for r in runs:
        if merged and (S[r[0]] - S[merged[-1][1]]) < PATH_GAP: merged[-1][1] = r[1]
        else: merged.append(r)
    good = [r for r in merged if S[r[1]] - S[r[0]] + PATH_STEP >= PATH_MIN and ok[r[0]:r[1] + 1].sum() >= 3]
    base = {'osm_id': e['id'], 'kind': 'airside_path', 'material': 'concrete', 'surface_osm': t.get('surface'), 'access': t.get('access'),
            'naip_frac': round(frac, 2)}
    out, cur = [], 0.0
    def undrawn(a, b):
        if b - a < 1.0: return
        g = substring(ls, a, b)
        if g.geom_type != 'LineString' or g.length < 1.0: return
        k = (S >= a) & (S <= b); fl = float(LINE[k].mean()) if k.any() else 0.0
        out.append({**base, 'part': len(out), 'w': None, 'offset_m': 0.0, 'drawn': False,
                    'w_src': ('NAIP: a light line inside wider pavement (%.0f %% of the profiles) - a wider road / apron edge, not a path '
                              'band; not drawn, the road itself is not measured here' % (100 * fl)) if fl >= 0.3 else 'NAIP shows no band here: not drawn',
                    **({'paved_line_frac': round(fl, 2)} if fl > 0 else {}),
                    'pts': [[round(x, 1), round(z, 1)] for x, z in g.simplify(0.3).coords]})
    for a, b in good:
        sa = 0.0 if a == 0 else S[a] - PATH_STEP / 2; sb = L if b == len(S) - 1 else S[b] + PATH_STEP / 2
        undrawn(cur, sa); cur = sb
        ii = np.arange(a, b + 1); acc = idx[(idx >= a) & (idx <= b)]
        sm = np.array([np.median(O[acc[np.abs(S[acc] - S[k]) <= PATH_SMOOTH]]) if np.any(np.abs(S[acc] - S[k]) <= PATH_SMOOTH) else np.nan for k in acc])
        off = np.interp(S[ii], S[acc], sm)                     # piecewise offset, flat beyond the first / last profile
        P = Q[ii] + off[:, None] * N[ii]
        w = float(np.median(Wd[acc]))
        g = LineString(P).simplify(0.3)
        out.append({**base, 'part': len(out), 'w': round(w, 2), 'offset_m': round(float(np.median(off)), 2),
                    'offset_range': [round(float(off.min()), 2), round(float(off.max()), 2)], 'drawn': True,
                    'naip_frac_part': round(len(acc) / len(ii), 2),
                    'w_src': 'NAIP 2024 median band width (%d of %d profiles of this stretch)' % (len(acc), len(ii)),
                    'pts': [[round(x, 1), round(z, 1)] for x, z in g.coords]})
    undrawn(cur, L)
    if not out:
        out.append({**base, 'part': 0, 'w': None, 'offset_m': 0.0, 'drawn': False, 'w_src': 'NAIP shows no band: not drawn',
                    'pts': [[round(x, 1), round(z, 1)] for x, z in ls.simplify(0.3).coords]})
    return out


def main():
    meta = json.load(open(os.path.join(CACHE, 'overpass_landside_latest.meta.json')))
    d = json.load(open(os.path.join(CACHE, meta['file'])))
    osm_air = json.load(open(os.path.join(CACHE, 'ksfo_osm_parsed.json')))
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    air = [Polygon([GF.wgs84_to_world(la, lo) for la, lo in a['pts']]).buffer(0) for a in osm_air['aprons'] if len(a['pts']) >= 4]
    for group in (A['taxiways'], A['runways']):
        for t in group:
            for poly in t['polys']: air.append(Polygon(poly[0], poly[1:]).buffer(0))
    for poly in A['terminalComplex']: air.append(Polygon(poly[0], poly[1:]).buffer(0))      # with its holes: the central landside (garage, loop roads) is a hole
    # the ramp outline of data/sfo_details.json (apron between the terminals; airside service lanes there are paint on
    # concrete, not roads)
    for poly in json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))['apron']: air.append(Polygon(poly[0], poly[1:]).buffer(0))
    airside = unary_union(air).buffer(2.0)
    # the app bakes the ground only inside APT_RECT (js/world/airfield.js: s0 -2800, t0 -1760, w 4700, h 3220 m in the
    # airport grid); everything is clipped to that rectangle (+50 m)
    s0, t0, w_, h_ = -2800.0, -1760.0, 4700.0, 3220.0
    rect = Polygon([GF.st_to_world(s0 - 50, t0 - 50), GF.st_to_world(s0 + w_ + 50, t0 - 50), GF.st_to_world(s0 + w_ + 50, t0 + h_ + 50), GF.st_to_world(s0 - 50, t0 + h_ + 50)])
    airside = airside.union(rect.exterior.buffer(0.01)).union(Polygon([(-1e5, -1e5), (1e5, -1e5), (1e5, 1e5), (-1e5, 1e5)]).difference(rect))
    roads, parks, paths = [], [], []
    n_elev = n_air = 0
    # static close-out (2026-11-04): (1) AIRSIDE service paths. OSM highway=service + access=no ways on the airfield (within
    # AIRFIELD_M of a runway centreline or of SFO Museum taxiway pavement) are the infield / perimeter vehicle paths, not
    # landside roads (review: 16.2 km painted as 4 m asphalt across the grass; NAIP shows ~2.5 m neutral concrete bands, their
    # centre a median 1.25 m off the OSM line). They go to `airside_paths`, each with its width and lateral offset MEASURED
    # on NAIP 2024 (bright band across the line, measure_band) and material concrete; a path NAIP does not show is kept
    # with drawn false. (2) Upper-level aisles: `level` > 0, a name 'Level N' (N >= 2) or a way inside a multi-storey
    # garage footprint (OSM parking=multi-storey / SFO Museum garage) is elevated (review: 677 m of 'Garage Level 4/5
    # Parking Aisle' drawn at grade, 400 m inside the Central Parking Garage).
    rw_lines = [LineString([GF.end_world(a), GF.end_world(b)]) for a, b in GF.RWY_PAIRS]
    tw_union = unary_union([Polygon(poly[0], poly[1:]).buffer(0) for t in A['taxiways'] for poly in t['polys']])
    garages = [Polygon(world(e['geometry'])).buffer(0) for e in d['elements'] if e['type'] == 'way' and 'geometry' in e
               and e.get('tags', {}).get('amenity') == 'parking' and e['tags'].get('parking') == 'multi-storey' and len(e['geometry']) >= 4]
    garages += [Polygon(poly[0]).buffer(0) for s_ in A['structures'] if s_['kind'] == 'garage' for poly in s_['polys']]
    garage_u = unary_union(garages)
    import re as _re
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
            lvl = num(t.get('level')); mN = _re.search(r'\bLevel\s*(\d+)', t.get('name', '') or '')
            elev_why = None
            if not elev and lvl is not None and lvl > 0: elev, elev_why = True, 'level %s' % t['level']
            elif not elev and mN and int(mN.group(1)) >= 2: elev, elev_why = True, 'name %s' % t['name']
            elif not elev and t.get('service') == 'parking_aisle' and garage_u.contains(ls.interpolate(0.5, normalized=True)) \
                    and ls.intersection(garage_u).length > 0.8 * ls.length:
                elev, elev_why = True, 'parking aisle inside a multi-storey garage footprint'
            if t.get('highway') == 'service' and t.get('access') == 'no' and \
                    (min(r.distance(ls) for r in rw_lines) < AIRFIELD_M or tw_union.distance(ls) < AIRFIELD_TW_M):
                paths.extend(measure_path(e, ls, t)); continue
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
                              **({'elevated_why': elev_why} if elev_why else {}),
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
           'source': 'OSM %s, database %s (%s; pinned, tools/xcheck/fetch_osm.py)' % (', '.join(meta['endpoint']) if isinstance(meta['endpoint'], list) else meta['endpoint'], meta['osm_base'], meta['file']),
           'note': 'landside roads (OSM centrelines with widths: osm width / lanes x 3.6 m / class default - see w_src; '
                   'elevated = bridge / layer >= 1: only their footprint counts as paved ground, not an at-grade road) and car '
                   'parks (kind parking = surface, garage = multi-storey footprint), clipped out of the airside (OSM aprons, '
                   'SFO Museum taxiways / runways / terminal complex, the ramp outline of sfo_details.json, + 2 m); tunnels '
                   'and layer < 0 are not included. Generated by '
                   'tools/build_landside.py; replaces the hand-drawn landside() of js/world/airfield.js in the live app.',
           'roads': roads, 'parking': parks, 'airside_paths': paths,
           'airside_paths_note': ('OSM highway=service + access=no on the airfield (within %d m of a runway centreline or %d m of SFO Museum '
                                  'taxiway pavement): infield / perimeter vehicle paths, concrete; one entry per stretch (`part`): drawn where '
                                  'NAIP 2024 images the band (measure_band every %.1f m across the OSM line; gaps < %.0f m bridged), its centre '
                                  'moved by the running-median band offset (+-%.1f m; offset_m = stretch median, offset_range) along '
                                  'measure_band\'s own normal, w = median band width; drawn false where NAIP shows no band (static close-out '
                                  '2026-11-04; piecewise offset with the corrected side, round 2 2026-11-05)' % (AIRFIELD_M, AIRFIELD_TW_M, PATH_STEP, PATH_GAP, PATH_SMOOTH))}
    json.dump(res, open(os.path.join(ROOT, 'data', 'sfo_landside.json'), 'w'), separators=(',', ':'))
    open(os.path.join(ROOT, 'data', 'sfo_landside.js'), 'w').write(
        '// generated by tools/build_landside.py - ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap '
        'contributors (docs/ATTRIBUTION.md)\nexport const LANDSIDE = ' + json.dumps(res, separators=(',', ':')) + ';\n')
    from collections import Counter
    print('roads %d (%s), parking %d, elevated / tunnel skipped %d, airside-only skipped %d' % (
        len(roads), dict(Counter(r['w_src'].split(' (')[0] for r in roads)), len(parks), n_elev, n_air))
    print('airside paths: %d ways, %d stretches (%.1f km; drawn %d, %.1f km; median measured width %.2f m, median |offset| %.2f m); elevated by level / name / garage: %d (%.0f m)' % (
        len({p_['osm_id'] for p_ in paths}), len(paths), sum(LineString(p_['pts']).length for p_ in paths) / 1000, sum(p_['drawn'] for p_ in paths),
        sum(LineString(p_['pts']).length for p_ in paths if p_['drawn']) / 1000,
        float(np.median([p_['w'] for p_ in paths if p_['drawn']] or [0])), float(np.median([abs(p_['offset_m']) for p_ in paths if p_['drawn']] or [0])),
        sum(1 for r in roads if r.get('elevated_why')), sum(LineString(r['pts']).length for r in roads if r.get('elevated_why'))))
    print('wrote data/sfo_landside.json / .js (%d KB)' % (os.path.getsize(os.path.join(ROOT, 'data', 'sfo_landside.js')) // 1024))


if __name__ == '__main__':
    main()
