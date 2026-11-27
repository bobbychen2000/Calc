"""The house: roofs solved from the aerial survey (survey/roof_3d.json, model/roof_solve.py), walls under them.

Blocks (survey/roof.json): two-storey core with a flat deck on top, the balcony gable BG (E), west wing WW, front gable
FG (SW, over the entry), south wing BC; one-storey garage wing (NW) and north wing (N, stone chimney), the patio wing
PB (SE, covered patio on the pool side), the wraparound porch (W / SW / S / E) and the north porch NCP.
Walls: every storey's eave outline in plan (the union of its planes) set in by the overhang; the two-storey walls run
from below the ground up to the two-storey roofs only (the porch roofs lean against them), the one-storey walls
rise to the one-storey roofs and stop where the two-storey footprint begins.  Porches have columns under a beam.
"""
import json
import os

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from model.kit import Geo, Part
from model.massing_kit import RoofPlane, roof_planes, wall

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOF = json.load(open(os.path.join(HERE, 'survey', 'roof_3d.json')))

OVERHANG = {1: 0.50, 2: 0.60}            # eave line -> wall face, plan metres
UNDER = 0.85                             # a roof hidden under an upper eave runs on this far uphill (into the wall)
Z_BASE = -2.5                            # walls start below every ground level; the terrain covers them
OPEN_BLOCKS = {'porch_1st', 'north_porch'}         # roofs on columns, no walls of their own
FLOOR = 0.45                             # main floor above the pool deck (porch / patio floors a step lower)
PORCH_FLOOR = 0.30
WALL = 'siding_shingle'


def _upper_outline():
    """Plan outline of the two-storey roofs (their eave lines), where hidden one-storey roof may run on."""
    polys = [Polygon(np.array(p['poly'])[:, :2]).buffer(0.005, join_style=2) for p in ROOF['planes'] if p['storey'] == 2]
    return unary_union(polys)


def _planes():
    out = []
    upper = _upper_outline()
    for p in ROOF['planes']:
        P = np.array(p['poly'], float)
        a, b, c = p['plane']
        Q = P
        if p['storey'] == 1 and any(k.startswith('under_upper') for k in p['edges']):
            # grow the plane under the upper roof only (hidden there), so it runs into the upper walls
            pp = Polygon(P[:, :2])
            g = pp.union(pp.buffer(UNDER, join_style=2).intersection(upper.buffer(-0.02)))
            if g.geom_type != 'Polygon':
                g = max(g.geoms, key=lambda q: q.area)
            xy = np.array(g.exterior.coords)[:-1]
            Q = np.c_[xy, a * xy[:, 0] + b * xy[:, 1] + c]
        mat = 'roof_flat' if p['flat'] else 'roof_shingle'
        out.append(dict(rp=RoofPlane(p['id'], Q, mat=mat, thickness=0.22, storey=p['storey']), src=p))
    return out


def _aerial_xy(uv, z):
    from model import frame
    from tools import cams as CAMS
    cam = frame.world_cams()['photos/p29_ddf5dc.jpg']
    o, d = CAMS.ray(cam, [uv])
    t = (z - o[2]) / d[0][2]
    return (o + t * d[0])[:2]


def entry_gable(geo, planes):
    """The small front-facing gable over the entry steps (hero photo: pediment on two columns), standing on the
    diagonal porch leg: apex at the leg's outer edge (aerial (725,1249)), ridge running NE into the front gable wall."""
    shed = next(p['rp'] for p in planes if p['src']['id'] == 'swp')
    eave = ROOF['eaves']['porch_1st']
    half, pitch = 1.55, 38.0
    rise = half * np.tan(np.radians(pitch))
    apex = _aerial_xy((725, 1249), eave + rise)
    inner = _aerial_xy((755, 1220), eave + rise)
    ridge = (inner - apex) / np.linalg.norm(inner - apex)           # toward the house (NE)
    side = np.array([ridge[1], -ridge[0]])
    a0 = apex - ridge * 0.25                                          # gable face a little proud of the leg's eave
    a1 = apex + ridge * 3.2                                           # into the front gable's wall
    zt, ze = eave + rise, eave - 0.02
    E = lambda q, z: np.array([q[0], q[1], z])                        # noqa: E731
    for sgn in (1, -1):
        pts = [E(a0, zt), E(a1, zt), E(a1 + side * sgn * half, ze), E(a0 + side * sgn * half, ze)]
        planes.append(dict(rp=RoofPlane('entry_gable_%d' % sgn, pts, mat='roof_shingle', thickness=0.18, storey=1),
                           src={'id': 'entry_gable', 'block': 'porch_1st', 'storey': 1}))
    # pediment (cream trim) and the two columns on stone piers at its corners
    tri = [E(a0 + side * half, ze - 0.25), E(a0 - side * half, ze - 0.25), E(a0, zt - 0.02)]
    geo.poly('trim_white', tri)
    geo.poly('trim_white', tri[::-1])
    for sgn in (1, -1):
        q = a0 + ridge * 0.35 + side * sgn * (half - 0.25)
        geo.box('stone_veneer', (q[0] - 0.24, q[1] - 0.24, PORCH_FLOOR), (q[0] + 0.24, q[1] + 0.24, PORCH_FLOOR + 0.95))
        geo.box('trim_white', (q[0] - 0.15, q[1] - 0.15, PORCH_FLOOR + 0.95), (q[0] + 0.15, q[1] + 0.15, ze - 0.25))
    return shed


def _footprint(planes, blocks, storey):
    """Eave outline of the given blocks (plan union of their visible planes) set in by the overhang."""
    polys = [Polygon(np.array(p['src']['poly'])[:, :2]).buffer(0.02) for p in planes
             if 'poly' in p['src'] and p['src']['block'] in blocks]
    u = unary_union(polys).buffer(0.25, join_style=2).buffer(-0.25, join_style=2)     # close slivers between planes
    return u.buffer(-OVERHANG[storey], join_style=2)


def _rings(geom):
    gs = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    return [g for g in gs if g.area > 1.0]


def _walls(geo, poly, planes, skip_near=None):
    """Walls round a footprint polygon (exterior ring), skipping edges that lie on skip_near's boundary."""
    for g in _rings(poly):
        ring = np.array(g.exterior.coords)[:-1]
        ring = ring if Polygon(ring).exterior.is_ccw is False else ring[::-1]       # clockwise: walls face out
        n = len(ring)
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            if np.linalg.norm(b - a) < 0.05:
                continue
            if skip_near is not None:
                mid = Point((a + b) / 2)
                if skip_near.buffer(0.05).contains(mid):
                    continue
            wall(geo, WALL, a, b, Z_BASE, planes)
        for h in g.interiors:                                      # light-well courts: walls facing the court
            ring = np.array(h.coords)[:-1]
            ring = ring if Polygon(ring).exterior.is_ccw else ring[::-1]
            for i in range(len(ring)):
                a, b = ring[i], ring[(i + 1) % len(ring)]
                if np.linalg.norm(b - a) > 0.05:
                    wall(geo, WALL, a, b, Z_BASE, planes)


def _porch(geo, poly, planes, z_floor, eave_z):
    """Columns along a porch footprint's outer corners (and every ~3 m), a beam on them, the floor slab."""
    for g in _rings(poly):
        ring = np.array(g.exterior.coords)[:-1]
        pts = []
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            L = np.linalg.norm(b - a)
            k = max(1, int(round(L / 3.0)))
            pts += [a + (b - a) * t for t in np.arange(k) / k]
        top = eave_z - 0.30
        for p in pts:
            geo.box('trim_white', (p[0] - 0.14, p[1] - 0.14, z_floor), (p[0] + 0.14, p[1] + 0.14, top))
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
            nrm = np.array([d[1], -d[0]])
            q = [a - nrm * 0.12, b - nrm * 0.12, b + nrm * 0.12, a + nrm * 0.12]
            geo.extrude('trim_white', q, top, eave_z - 0.02)
        geo.extrude('bluestone', ring, z_floor - 0.6, z_floor)


def build():
    planes = _planes()
    geo = Geo()
    entry_gable(geo, planes)
    rps = [p['rp'] for p in planes]
    roof_planes(geo, rps)
    planes_s = [p for p in planes if 'poly' in p['src']]
    st2 = {p['src']['block'] for p in planes if p['src']['storey'] == 2}
    st1_closed = {p['src']['block'] for p in planes if p['src']['storey'] == 1} - OPEN_BLOCKS - {'patio_1st'}
    f2 = _footprint(planes, st2, 2)
    f1 = _footprint(planes, st1_closed, 1).difference(f2)
    p2 = [p['rp'] for p in planes if p['src']['storey'] == 2]
    p1 = [p['rp'] for p in planes if p['src']['storey'] == 1]
    _walls(geo, f2, p2)
    _walls(geo, f1, p1, skip_near=f2)
    eaves = ROOF['eaves']
    for blk in sorted(OPEN_BLOCKS | {'patio_1st'}):
        fp = _footprint(planes, {blk}, 1).difference(f2).difference(f1)
        _porch(geo, fp, p1, PORCH_FLOOR, eaves[blk])
    return [Part('house', geo, group='house')]
