#!/usr/bin/env python3
"""Split the SFO terminal complex (SFO Museum geometry) into building parts with heights, and precompute for every
wall edge the height of whatever lies directly outside it, so the renderer can draw each wall only where it is
actually exposed (no coincident walls, no z-fighting).

Parts: boarding areas (piers) A-G, terminal halls (terminal polygon minus its boarding areas), and connectors
(rest of the complex). Heights are approximate except the International Terminal hall (up to 83 ft, published).
Output: data/sfo_buildings.json and data/sfo_buildings.js (same JSON as an ES module). World frame = that of
data/sfo_airport.json (tools/geo_frame.py; no projection is done here).
"""
import json, math, os
import numpy as np, cv2
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
D = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
RES = 0.5
xs = [p[0] for p in D['terminalComplex'][0][0]]; zs = [p[1] for p in D['terminalComplex'][0][0]]
X0, Z0 = min(xs) - 20, min(zs) - 20; X1, Z1 = max(xs) + 20, max(zs) + 20
W, H = int((X1 - X0) / RES), int((Z1 - Z0) / RES)
def px(pts): return np.array([[(x - X0) / RES, (z - Z0) / RES] for x, z in pts], np.float64)
def fill(mask, rings, holes=True, val=1):
    cv2.fillPoly(mask, [np.round(px(rings[0]) * 16).astype(np.int32)], val, shift=4)
    if holes:
        for h in rings[1:]: cv2.fillPoly(mask, [np.round(px(h) * 16).astype(np.int32)], 0, shift=4)
    return mask
def m(): return np.zeros((H, W), np.uint8)

CX = m(); fill(CX, D['terminalComplex'][0])
# Static fix-up (26 Sep 2026; review round 4: "T1, T3 ... footprints > 3 m off where roof lean cannot explain it (T1 / T3
# over the curbside roadways)"). Evidence: the OpenStreetMap carriageways "Departures" (elevated, layer 1) and
# "Arrivals" (ODbL; refs/cache/osm/overpass_landside_*.json, 26 Sep 2026) run INSIDE the SFO Museum complex along the
# T1 north face and the T3 landside face, and NAIP 2024 shows vehicles on those lanes inside the modelled footprint
# (refs/cache/stands/view/t3l.png, t1e.png). Within the two windows below, the complex is cut back by those carriageways
# (centreline +- lanes x 3.6 m / 2; 2 lanes where OSM has no lanes tag - inferred). The sidewalk / canopy strip between
# the carriageway and the facade stays building (the canopy overhangs it). N / S-facing faces: the east roof lean does
# not move them, so the imaged vehicles are a valid check. Elsewhere (BA D SSE corner, BA A east face) no such ground
# evidence exists and the misfits stay listed.
TRIM_WINDOWS = {'Harvey Milk Terminal 1 north face (curbside roadways)': (-1050.0, 380.0, -790.0, 470.0),
                'Terminal 3 landside face (curbside roadways)': (-975.0, 75.0, -865.0, 125.0)}
TRIMMED = {}
try:
    import glob as _glob, sys as _sys
    _sys.path.insert(0, HERE); import geo_frame as _GF
    _meta = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_landside_latest.meta.json')))
    _osm = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'osm', _meta['file'])))
    from shapely.geometry import LineString as _LS, box as _box
    from shapely.ops import unary_union as _uu
    _roads = []
    for _e in _osm['elements']:
        _t = _e.get('tags', {})
        if _e['type'] != 'way' or 'geometry' not in _e or _t.get('highway') not in ('primary', 'secondary', 'tertiary', 'primary_link', 'secondary_link', 'tertiary_link'): continue
        if _t.get('tunnel', 'no') != 'no' or _t.get('covered') == 'yes': continue
        _w = float(_t['lanes']) * 3.6 if _t.get('lanes', '').replace('.', '').isdigit() else 7.2
        _roads.append((_e['id'], _t.get('name'), _LS([_GF.wgs84_to_world(g['lat'], g['lon']) for g in _e['geometry']]).buffer(_w / 2, cap_style=2)))
    for _name, (_x0, _z0, _x1, _z1) in TRIM_WINDOWS.items():
        _win = _box(_x0, _z0, _x1, _z1); _cut = _uu([g.intersection(_win) for i_, n_, g in _roads if g.intersects(_win)])
        if _cut.is_empty: continue
        _mk = m()
        for _g in getattr(_cut, 'geoms', [_cut]):
            if _g.geom_type == 'Polygon' and not _g.is_empty: fill(_mk, [list(_g.exterior.coords)], holes=False)
        _rm = (CX > 0) & (_mk > 0)
        TRIMMED[_name] = {'removed_m2': round(float(_rm.sum()) * RES * RES), 'window': [_x0, _z0, _x1, _z1],
                          'osm_ways': sorted({'%d %s' % (i_, n_) for i_, n_, g in _roads if g.intersects(_win)})}
        CX[_rm] = 0
    print('trimmed by OSM carriageways:', TRIMMED)
except FileNotFoundError as _e:
    print('OSM landside cache missing - footprints NOT trimmed:', _e)
BA = {b['letter'] if b.get('letter') else b['name'][-1]: fill(m(), b['polys'][0]) & CX for b in D['boardingAreas']}
TM = {t['name']: fill(m(), t['polys'][0]) & CX for t in D['terminals']}
HALL_H = {'Harvey Milk Terminal 1': 20.0, 'Terminal 2': 19.0, 'Terminal 3': 21.0, 'International Terminal': 25.3}
PIER_H, CONN_H = 14.6, 12.0
baU = np.zeros_like(CX)
for k, v in BA.items(): baU |= v
parts = []  # (label mask, meta)
for k, v in BA.items(): parts.append((v, {'kind': 'pier', 'name': 'Boarding Area ' + k, 'h': PIER_H}))
tU = np.zeros_like(CX)
for name, v in TM.items():
    hall = v & (1 - ndi.binary_dilation(baU, iterations=2).astype(np.uint8))
    hall = ndi.binary_opening(hall, iterations=3).astype(np.uint8)
    parts.append((hall, {'kind': 'hall', 'name': name, 'h': HALL_H.get(name, 20.0)}))
    tU |= v
conn = CX & (1 - ndi.binary_dilation(baU | tU, iterations=1).astype(np.uint8))
conn = ndi.binary_opening(conn, iterations=2).astype(np.uint8)
parts.append((conn, {'kind': 'connector', 'name': 'Connector', 'h': CONN_H}))
# thin structures (sky bridges / corridors < ~14 m wide) become elevated walkways instead of full-height buildings
def split_thin(mk, r_px=int(7 / RES)):
    se = np.ones((3, 3), bool)
    core = ndi.binary_opening(mk > 0, structure=se, iterations=r_px)
    core = ndi.binary_dilation(core, structure=se, iterations=2) & (mk > 0)
    thin = (mk > 0) & ~core
    thin = ndi.binary_opening(thin, iterations=1)
    return core.astype(np.uint8), thin.astype(np.uint8)
split = []; THIN = np.zeros_like(CX)
for mk, meta in parts:
    core, thin = split_thin(mk)
    split.append((core, meta))
    if thin.sum() * RES * RES > 150: split.append((thin, {'kind': 'walkway', 'name': meta['name'] + ' walkway', 'h': 10.5, 'y0': 6.0})); THIN |= thin
parts = split
# label raster: part index + height raster
LAB = np.full((H, W), -1, np.int32)
for i, (mk, meta) in enumerate(parts):
    LAB[(mk > 0) & (LAB < 0)] = i
HGT = np.zeros((H, W), np.float32)
for i, (mk, meta) in enumerate(parts): HGT[LAB == i] = meta['h'] if meta['kind'] != 'walkway' else 0.0  # walkways do not hide neighbouring walls
# fill tiny gaps inside the complex with the nearest (non-walkway) part so there are no holes between parts
gap = (CX > 0) & (LAB < 0) & (ndi.distance_transform_edt(LAB < 0) < 4 / RES)
if gap.any():
    idx = ndi.distance_transform_edt(LAB < 0, return_distances=False, return_indices=True)
    LAB[gap] = LAB[idx[0][gap], idx[1][gap]]; HGT[gap] = HGT[idx[0][gap], idx[1][gap]]

def world(p): return [round(float(X0 + p[0] * RES), 2), round(float(Z0 + p[1] * RES), 2)]
out = []
for i, (mk, meta) in enumerate(parts):
    lm = (LAB == i).astype(np.uint8)
    cs, hier = cv2.findContours(lm, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None: continue
    hier = hier[0]
    for j, c in enumerate(cs):
        if hier[j][3] != -1 or cv2.contourArea(c) * RES * RES < 250: continue
        rings = [c]; k = hier[j][2]
        while k != -1:
            if cv2.contourArea(cs[k]) * RES * RES > 60: rings.append(cs[k])
            k = hier[k][0]
        R = []; B = []
        for r in rings:
            a = cv2.approxPolyDP(r, 0.9 / RES, True)[:, 0, :].astype(np.float64)
            pts = [world((p[0] + 0.5, p[1] + 0.5)) for p in a]
            # for every edge: what is outside? sample 1.2 m outward at 3 points along the edge
            n = len(pts); base = []
            area = sum(pts[q][0] * pts[(q + 1) % n][1] - pts[(q + 1) % n][0] * pts[q][1] for q in range(n)) / 2
            for q in range(n):
                p0, p1 = np.array(pts[q]), np.array(pts[(q + 1) % n]); L = np.linalg.norm(p1 - p0)
                if L < 1e-6: base.append(0); continue
                d = (p1 - p0) / L; nrm = np.array([-d[1], d[0]])
                # outward normal: for a ring with positive raw area (x,z) the left normal points inward
                if (area > 0) == (len(R) == 0): nrm = -nrm
                hs = []
                for t in (0.25, 0.5, 0.75):
                    s = p0 + (p1 - p0) * t + nrm * 1.2
                    ix, iy = int((s[0] - X0) / RES), int((s[1] - Z0) / RES)
                    if 0 <= ix < W and 0 <= iy < H and LAB[iy, ix] >= 0 and LAB[iy, ix] != i: hs.append(float(HGT[iy, ix]))
                    else: hs.append(0.0)
                base.append(round(min(hs), 2))
            R.append(pts); B.append(base)
        # principal axis (for skylights / roof features)
        P = np.array(R[0]); c0 = P.mean(0); cov = np.cov((P - c0).T); ev, evec = np.linalg.eigh(cov); ax = evec[:, 1]
        ext = (P - c0) @ ax; wid = (P - c0) @ np.array([-ax[1], ax[0]])
        out.append({**meta, 'rings': R, 'base': B, 'axis': [round(float(ax[0]), 4), round(float(ax[1]), 4)], 'center': [round(float(c0[0]), 1), round(float(c0[1]), 1)],
                    'len': round(float(ext.max() - ext.min()), 1), 'wid': round(float(wid.max() - wid.min()), 1), 'area': round(float(cv2.contourArea(c)) * RES * RES)})
print(len(out), 'parts:', [(o['kind'], o['name'], len(o['rings'][0])) for o in out])
# complex outline rings (apron-level base walls 0-5 m)
cxr = []
BASE = (CX & (1 - THIN)).astype(np.uint8); BASE = ndi.binary_opening(BASE, iterations=2).astype(np.uint8)
cs, hier = cv2.findContours(BASE, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
for c in cs:
    if cv2.contourArea(c) * RES * RES < 60: continue
    a = cv2.approxPolyDP(c, 0.9 / RES, True)[:, 0, :].astype(np.float64)
    cxr.append([world((p[0] + 0.5, p[1] + 0.5)) for p in a])
# Review round 3: footprint accuracy. NAIP 2024 cannot verify the SFO Museum outlines to better than ~5 m: roofs lean
# east by ~0.54 m per m of height (tools/stands/naip_relief.py) and NAIP 2022 has the same lean (docs/research/imagery.md
# s.6), so a second epoch gives no lean-free view. Measured misfits beyond the predicted lean (review round 3): Boarding
# Area D's SSE face imaged 7.7 m outside (2.5 m predicted), BA A east +10.3 (7.2); the Harvey Milk T1 hall includes a
# ~20 m bulge over the departures roadway / AirTrain guideway at x -1047..-980, z 412..443 (SFO Museum footprint; NAIP
# shows roadway and guideway there - kept, not verifiable without a true ortho). All footprints: inferred, +-5 m.
_doc = {'frame': D.get('frameId', 'equirect-v1'), 'complex': cxr, 'parts': out, 'note': 'derived from SFO Museum footprints; heights approximate except ITB hall (83 ft)',
        'footprint_accuracy': {'src': 'inferred', 'tol_m': 5.0, 'why': 'SFO Museum outlines; NAIP 2022/2024 roofs lean east ~0.54 m/m (same lean in both epochs): no lean-free check',
                               'known_misfits': ['Boarding Area D SSE face: imaged roof 7.7 m outside vs 2.5 m predicted lean',
                                                 'Boarding Area A east face: +10.3 m vs 7.2 m predicted',
                                                 'Harvey Milk Terminal 1 hall: bulge over the departures roadway / AirTrain guideway (x -1047..-980, z 412..443)',
                                                 # review round 4 (lean-invariant N/S faces; the review measured the imaged glass facade / roof edge):
                                                 'Harvey Milk Terminal 1 north face x -1000..-840: model 1.8 m (x -998) growing to ~12 m (x -866..-842) north of the imaged facade, over the curbside lanes - TRIMMED by the OSM carriageways (see trimmed); the sidewalk / canopy strip stays',
                                                 'Terminal 3 landside (S/SE-facing curve) x -960..-880: model 4.4-10 m beyond the imaged roof / canopy edge, over the curb lane - TRIMMED by the OSM carriageways (see trimmed)',
                                                 'Boarding Area D SSE corner near (-616, 208): model cuts ~10-15 m off the imaged roof corner',
                                                 'unconfirmed N/S-facing medians (review round 4 drawing audit): International Terminal N -3.0 / S +3.2 m, T3 S +6.2 m, BA E N +7.0 m'],
                               'trimmed': {k: dict(v, how='complex cut back by the OSM carriageways (lanes x 3.6 m) inside the window; NAIP 2024 shows vehicles on them inside the SFO Museum footprint (static fix-up 26 Sep 2026)') for k, v in TRIMMED.items()},
                               'not_trimmed_why': 'BA D SSE corner, BA A east face and the unconfirmed medians: no ground-contact evidence (the imaged roof corner of BA D is not separable from the concrete apron at NAIP contrast; the D3 bridge attaches there) and no OSM outline; the review\'s by-eye offsets are not a source - listed misfits (footprints are SFO Museum, CDLA; tolerance stated above)'}}
json.dump(_doc, open(os.path.join(ROOT, 'data', 'sfo_buildings.json'), 'w'), separators=(',', ':'))
open(os.path.join(ROOT, 'data', 'sfo_buildings.js'), 'w').write('// Terminal building parts derived from SFO Museum footprints (CDLA-Permissive-1.0), trimmed at T1 / T3 by OpenStreetMap carriageways (ODbL 1.0, (c) OpenStreetMap contributors) - tools/build_terminal_parts.py\nexport const BUILDINGS = ' + json.dumps(_doc, separators=(',', ':')) + ';\n')
print('bytes', os.path.getsize(os.path.join(ROOT, 'data', 'sfo_buildings.json')))
# debug image
img = np.zeros((H, W, 3), np.uint8)
cols = [(200, 120, 60), (60, 160, 220), (90, 200, 90), (220, 90, 160), (160, 160, 60), (80, 80, 220), (200, 200, 200), (120, 60, 200), (60, 220, 200), (220, 160, 90), (150, 90, 90), (90, 150, 150)]
for i in range(len(parts)): img[LAB == i] = cols[i % len(cols)]
cv2.imwrite(os.path.join(ROOT, 'out', 'details', 'parts.png'), cv2.resize(img, (W // 3, H // 3)))
