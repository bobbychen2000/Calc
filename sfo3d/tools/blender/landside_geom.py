"""Geometry of the 3-D landside asset (data/buildings3d/landside.glb): Central Parking Garage (with its void), International
Garages A and G (body, helix drum, core cylinder, rooftop box, AirTrain portal), Long-Term Parking Garages 1 / 2, Rental
Car Center (west wall, station tower), Grand Hyatt, Consolidated Administration Campus, Superbay hangar and the United MOC
hangars. The AirTrain guideway and stations are in landside_airtrain.py, the parked cars in landside_cars.py.

Pure numpy / shapely (no bpy): tools/blender/build_landside.py turns the parts into Blender objects; verify_landside.py
measures the exported glb against the same functions.

THE REFERENCE IS THE 2-D DRAWING CODE (sheets BL-01..03, docs/drawings/buildings/README.md), imported here, not copied:
  tools/buildings/draw_landside.py  GAR / ggeom() (Garage A / G body end Lb, drum circle fits, station u / b, rooftop box,
                                    GAR_CORE_D), SB_TIP / SB_FOLD / SB_DOOR_GAP / SB_HIP (Superbay), GH_P / GH_POD / GH_COL
                                    and the l4 fractions of hyatt_elev() (Grand Hyatt east face), RCC_N / RCC_S /
                                    RCC_TOWER_D (RCC west face, station tower), the level placeholders of sheet_elev()
  tools/buildings/draw_data.py      spec_landside.json (LV), landside_naip_measurements.json (LANDM: min rectangles, DOF
                                    points, roof cars, MOC imaged corners), SFO Museum outlines (data/sfo_airport.json)
Every value the sheets do not give is a named constant below with its tag ('inf' derived / chosen from stated evidence,
'unk' placeholder with no source) and is listed in the manifest (data/buildings3d/manifest.json#landside).

Frames: every building node has its own origin (ox, oz) in the app world frame (x east, z south, m from the ARP;
js/geo.js); Blender local X = x - ox, Y = oz - z, Z = height above local grade (build_landside.py puts the node at world
(ox, GROUND_Y, oz)). Faces are wound outwards (single-sided materials; back-face QA render).
"""
import math
import os
import sys

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_landside as DL  # noqa: E402
from draw_lib import FT, hdg_vec  # noqa: E402
import landside_airtrain as AT  # noqa: E402
from landside_mesh import (MB, Frame, boxm, cap, clean, cyl, orient_all, polys, ring_band, rings_of, tube,  # noqa: E402,F401
                           walls)

LV = D.LV
LB = D.LANDM['buildings']
MOC = D.LANDM['moc']
SWITCH_M = {0: 0.0, 1: 450.0, 2: 1500.0}     # LOD switch distance (camera to the building node), m [our choice]

# ------------------------------------------------------------------------------------------------ chosen constants
# (inf = derived from the stated evidence; unk = placeholder, no source). Listed in the manifest.
PARAPET_H = 3.5 * FT       # 1.07 m: parking-deck parapet / guard height above the deck (42 in, typical) [inf]
PARAPET_T = 0.30           # parapet thickness [inf]
RECESS = 3.0               # depth of the dark interior behind the open parking levels (seen through the openings) [inf]
SPANDREL_DN, SPANDREL_UP = 0.30, 0.95   # spandrel / slab edge band around each level line [inf]
PIER_W = 0.6               # facade pier width [inf]
PIER_DX = {'cg': 9.0, 'gar': 8.1, 'gar_end': 9.0, 'ltp1': 9.0, 'ltp2': 9.1, 'rcc': 9.0}   # pier spacing [inf] (LTP2 9.1:
#                            the exposed frame of photo l2 / spec ltp2_facade, bay size inf; Garages A / G: half the 16.2 m
#                            screen module of photo l1 (two screen panels per bay) [inf])
SCREEN_OUT, SCREEN_GAP = 0.15, 0.10   # perforated screen: 0.15 m proud of the facade, 0.10 m gap above / below (photo l1: the
#                                       panels fill the opening between the spandrels) [inf]
STALL_W, STALL_L, AISLE = 2.6, 5.5, 7.6   # parking module (90-degree stalls): 2.6 x 5.5 m stalls, 7.6 m aisle [inf, typical]
MODULE = 2 * STALL_L + AISLE              # 18.6 m
LANE_W, LANE_PITCH = 3.0, 5.6             # RCC ready-return lanes: 3.0 m lanes, cars nose-to-tail every 5.6 m [inf]
TOWER_SIDE = 7.0           # stair / elevator tower at a DOF roof point: 7 x 7 m [inf]
STATION_BLOCK_W = 12.0     # Garage A station block: solid precast faces within 12 m of the guideway strips (photo l1) [inf]
GH_PODIUM_D = 17.0         # Grand Hyatt: podium depth in front of the slab along the south part (NAIP slab roof with the 13.4-m
#                            relief shift vs the outline's east edge, ~17-20 m) [obs NAIP, approx]


def dim(value, tag, source):
    return dict(v=value if not isinstance(value, float) else round(value, 3), tag=tag, source=source)


class Part:
    """one glTF node: mesh + tags. kind 'shell' = gets the baked AO atlas (UV_ao) and is shared by LOD0 / LOD1;
    'detail' = per-LOD members without AO; 'coarse' = LOD2 shell (own small atlas)."""

    def __init__(self, name, mb, kind, src, feature, spec=(), dims=None, note=''):
        self.name, self.mb, self.kind, self.src, self.feature = name, mb, kind, src, feature
        self.spec, self.dims, self.note = list(spec), dims or {}, note

    def extras(self, lod):
        e = dict(src=self.src, feature=self.feature, spec=self.spec, lod=lod)
        if self.dims: e['dims'] = self.dims
        if self.note: e['note'] = self.note
        return e


class Bldg:
    """one landside building: origin, shells (LOD0 + LOD1), details per LOD, LOD2 coarse parts, decks (car areas) and the
    node extras (src, spec keys, per-dimension tags, inferred / unknown lists)."""

    def __init__(self, key, name, ox, oz, src, spec, dims, inferred=(), unknown=(), conflicts=(), not_modelled=(), deviations=()):
        self.key, self.name, self.F = key, name, Frame(round(ox, 1), round(oz, 1))
        self.src, self.spec, self.dims = src, list(spec), dims
        self.inferred, self.unknown, self.conflicts, self.not_modelled = list(inferred), list(unknown), list(conflicts), list(not_modelled)
        self.deviations = list(deviations)
        self.shells, self.details, self.coarse, self.decks = [], {0: [], 1: []}, [], []
        self.anchors = {}
        self.footprint_w = None          # world footprint (shapely) for the plausibility checks
        self.top = None

    def extras(self):
        return dict(src=self.src, feature=self.name, spec=self.spec, dims=self.dims, origin_world_xz=[self.F.ox, self.F.oz],
                    inferred=self.inferred, unknown=self.unknown, conflicts=self.conflicts, not_modelled=self.not_modelled,
                    deviations_from_sheets=self.deviations, anchors=self.anchors)


# ------------------------------------------------------------------------------------------------ geometry helpers
def sfom_union(name):
    return unary_union([Polygon(p[0], p[1:]).buffer(0) for p in D.sfom(name, 'structures')])


RAIL = AT.RAIL


def largest(g):
    ps = polys(g)
    return max(ps, key=lambda p: p.area) if ps else Polygon()


def edge_normal(a, b):
    """outward normal (right of a -> b) in local XY."""
    d = np.array(b, float) - np.array(a, float); L = float(np.hypot(*d))
    return np.array([d[1], -d[0]]) / L, L


def ring_edges(P):
    """[(a, b, s0)] of every ring of a local polygon (exterior CCW, holes CW): outward = right of a -> b."""
    out = []
    for p in polys(P):
        for ring in rings_of(p):
            s = 0.0
            n = len(ring)
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 1e-3: continue
                out.append((tuple(a), tuple(b), s))
                s += L
    return out


def loc_dir(hdg):
    """local XY unit vector of a true heading."""
    v = hdg_vec(hdg)
    return np.array([v[0], -v[1]])


def holed_wall(mb, a, b, z0, z1, holes, mat, s0=0.0, tile=(3.0, 3.0), v0=0.0):
    """vertical wall a -> b (outward = right) from z0 to z1 minus rectangular holes [(s_a, s_b, h0, h1)] (s along a -> b)."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if not holes:
        mb.quad_wall(a, b, z0, z1, z0, z1, mat, s0, tile, v0=v0); return
    ss = sorted({0.0, L} | {min(max(h[0], 0.0), L) for h in holes} | {min(max(h[1], 0.0), L) for h in holes})
    zz = sorted({z0, z1} | {min(max(h[2], z0), z1) for h in holes} | {min(max(h[3], z0), z1) for h in holes})
    d = (np.array(b, float) - np.array(a, float)) / L
    for i in range(len(ss) - 1):
        for j in range(len(zz) - 1):
            sm, zm = 0.5 * (ss[i] + ss[i + 1]), 0.5 * (zz[j] + zz[j + 1])
            if any(h[0] < sm < h[1] and h[2] < zm < h[3] for h in holes): continue
            pa = tuple(np.array(a) + d * ss[i]); pb = tuple(np.array(a) + d * ss[i + 1])
            mb.quad_wall(pa, pb, zz[j], zz[j + 1], zz[j], zz[j + 1], mat, s0 + ss[i], tile, v0=v0)


def level_bands(slabs, top, ground_open=True, dn=SPANDREL_DN, up=SPANDREL_UP, deck=None):
    """facade bands of an open parking structure: a spandrel (solid) band [z - dn, z + up] at every slab line, open bands
    between; the top band from the deck slab to the parapet top is solid. -> [(z0, z1, 'solid' | 'open')]."""
    out = []
    z = 0.0
    lines = list(slabs) + ([deck] if deck is not None else [])
    for i, zl in enumerate(lines):
        a = zl - dn
        if a > z + 0.05:
            out.append((z, a, 'open' if (i > 0 or ground_open) else 'solid'))
        b = top if (deck is not None and i == len(lines) - 1) else zl + up
        out.append((max(a, z), b, 'solid'))
        z = b
    if z < top - 0.01:
        out.append((z, top, 'solid'))
    return out


def clip_bands(bands, z0, z1=1e9):
    out = []
    for a, b, k in bands:
        a2, b2 = max(a, z0), min(b, z1)
        if b2 - a2 > 0.02: out.append((a2, b2, k))
    return out


def garage_facade(mb, P, bands, style, tiles, recess=RECESS, gdetail=None):
    """facades of an open parking structure on the local polygon P (holes = inner courts / voids).
    style(a, b) -> dict(kind='open' | 'screen' | 'solid' | 'none', pier_dx, solid=mat key, holes=[...], z0=, z1=) per ring
    edge. Solid bands are walls at the facade plane; open bands are recessed: a dark interior wall `recess` inside, slab
    soffit / sill caps between, piers every pier_dx; 'screen' edges add perforated panels 0.15 m proud of the facade.
    z0 / z1 clip the bands of an edge (e.g. above a guideway deck that runs along it). gdetail: MB for screens / piers."""
    gd = gdetail if gdetail is not None else mb
    open_quads = []
    zone_bands = {}
    for a, b, s0 in ring_edges(P):
        st = style(a, b)
        if st['kind'] == 'none': continue
        n, L = edge_normal(a, b)
        A, B = np.array(a), np.array(b)
        eb = clip_bands(bands, st.get('z0', 0.0), st.get('z1', 1e9))
        if not eb: continue
        if st['kind'] == 'solid':
            holed_wall(mb, a, b, eb[0][0], eb[-1][1], st.get('holes', []), st['solid'], s0, tiles[st['solid']])
            if st.get('slots') and L > 6.0:
                # dark horizontal window slots, 1.2 m high, one per level band above the AirTrain level (photo l1), 1.5 m in from
                # the edge ends, 2 cm proud of the wall
                d = (B - A) / L
                for z0, z1, kind in eb:
                    if kind != 'open' or z0 < AT.NET_LEVEL + AT.PORTAL_H: continue
                    zc = 0.5 * (z0 + z1)
                    pa_, pb_ = A + d * 1.5 + n * 0.02, B - d * 1.5 + n * 0.02
                    gd.quad_wall(tuple(pa_), tuple(pb_), zc - 0.6, zc + 0.6, zc - 0.6, zc + 0.6, 'slot', 0.0, (3.0, 1.2))
            continue
        for z0, z1, kind in eb:
            if kind == 'solid':
                mb.quad_wall(a, b, z0, z1, z0, z1, st['solid'], s0, tiles[st['solid']])
        q = Polygon([A, B, B - n * recess, A - n * recess])
        if q.is_valid and q.area > 1e-3:
            ob = tuple((z0, z1) for z0, z1, k in eb if k == 'open')
            if ob:
                open_quads.append(q); zone_bands.setdefault(ob, []).append(q)
        dx = st['pier_dx']
        if L > 4.0:
            k = max(1, int(round((L - 4.0) / dx)))
            ss = np.linspace(2.0, L - 2.0, k + 1)
            d = (B - A) / L
            for s in ss:
                c = A + d * s
                p0, p1 = c - d * PIER_W / 2, c + d * PIER_W / 2
                q0, q1 = p0 - n * recess, p1 - n * recess
                for z0, z1, kind in eb:
                    if kind != 'open': continue
                    gd.quad_wall(tuple(p0), tuple(p1), z0, z1, z0, z1, st['solid'], s0 + s - PIER_W / 2, tiles[st['solid']])
                    gd.quad_wall(tuple(p1), tuple(q1), z0, z1, z0, z1, st['solid'], 0.0, tiles[st['solid']])
                    gd.quad_wall(tuple(q0), tuple(p0), z0, z1, z0, z1, st['solid'], 0.0, tiles[st['solid']])
            if st['kind'] == 'screen':
                cuts = [0.0] + list(ss) + [L]
                for i in range(len(cuts) - 1):
                    sa = cuts[i] + (PIER_W / 2 if i > 0 else 0.15); sb = cuts[i + 1] - (PIER_W / 2 if i < len(cuts) - 2 else 0.15)
                    if sb - sa < 0.5: continue
                    pa = A + d * sa + n * SCREEN_OUT; pb = A + d * sb + n * SCREEN_OUT
                    fa, fb = A + d * sa, A + d * sb
                    for z0, z1, kind in eb:
                        if kind != 'open': continue
                        za, zb = z0 + SCREEN_GAP, z1 - SCREEN_GAP
                        if zb - za < 0.6: continue
                        gd.quad_wall(tuple(pa), tuple(pb), za, zb, za, zb, 'screen', 0.0, (sb - sa, zb - za), v0=za)
                        uvq = [(0, 0), (1, 0), (1, 0.05), (0, 0.05)]
                        gd.face_dir([(pa[0], pa[1], zb), (pb[0], pb[1], zb), (fb[0], fb[1], zb), (fa[0], fa[1], zb)], 'screen_edge', uvq, (0, 0, 1))
                        gd.face_dir([(fa[0], fa[1], za), (fb[0], fb[1], za), (pb[0], pb[1], za), (pa[0], pa[1], za)], 'screen_edge', uvq, (0, 0, -1))
                        gd.face_dir([(fa[0], fa[1], za), (pa[0], pa[1], za), (pa[0], pa[1], zb), (fa[0], fa[1], zb)], 'screen_edge', uvq, (-d[0], -d[1], 0))
                        gd.face_dir([(pb[0], pb[1], za), (fb[0], fb[1], za), (fb[0], fb[1], zb), (pb[0], pb[1], zb)], 'screen_edge', uvq, (d[0], d[1], 0))
    if not open_quads:
        return
    bnd = P.boundary
    for ob, qs in zone_bands.items():
        zone = orient_all(unary_union(qs).intersection(P).buffer(0))
        for z0, z1 in ob:
            cap(mb, zone, z0 + (0.02 if z0 < 0.01 else 0.0), 'sill', 6.0)
            cap(mb, zone, z1, 'soffit', 6.0, down=True)
            for q in polys(zone):
                for ring in rings_of(q):
                    m = len(ring)
                    for i in range(m):
                        a, b = ring[i], ring[(i + 1) % m]
                        mid = Point(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
                        if bnd.distance(mid) < 0.05: continue           # on the facade plane: open
                        mb.quad_wall(b, a, z0, z1, z0, z1, 'interior', 0.0, (6.0, 6.0))   # facing into the zone


def deck_and_parapet(mb, P, deck_z, top_z, deck_mat, deck_uv, thk=PARAPET_T, coping='coping'):
    """parking roof: deck cap (stall texture through deck_uv) inside a parapet ring; returns the deck polygon."""
    ring, inner = ring_band(P, thk)
    cap(mb, ring, top_z, coping, 1.0)
    for q in polys(inner):
        for r in rings_of(q):
            n = len(r)
            for i in range(n):
                a, b = r[i], r[(i + 1) % n]
                mb.quad_wall(b, a, deck_z, top_z, deck_z, top_z, coping, 0.0, (3.0, 3.0))
        cap(mb, q, deck_z, deck_mat, 6.0, uvf=deck_uv)
    return inner


def deck_uvf(F, car_axis, origin_world, lanes=False):
    """UV of the parking-deck marking texture in the local frame of building F (landside_tex): 90-degree stalls ('deck':
    u = 4 stalls of 2.6 m across the car axis, v = one 18.6-m module 5.5 stall + 7.6 aisle + 5.5 stall along it) or
    nose-to-tail lanes ('deck_lanes': u = 4 lanes of 3 m, v = 2 car pitches of 5.6 m). car_axis = the cars' long axis
    (true heading, NAIP 'car_row_axis_heading_deg' = the blobs' long axis)."""
    ax = loc_dir(car_axis); row = loc_dir(car_axis + 90.0)
    o = np.array(F.L(*origin_world))
    su, sv = (4 * LANE_W, 2 * LANE_PITCH) if lanes else (4 * STALL_W, MODULE)

    def f(x, y):
        d = np.array([x, y]) - o
        return (float(d @ row) / su, float(d @ ax) / sv)
    return f


def stack_coarse(mb, P, top, wall_mat, roof_mat, tile=(6.0, 6.0)):
    """LOD2 prism."""
    walls(mb, P, 0.0, top, wall_mat, tile)
    cap(mb, P, top, roof_mat, 12.0)


def pole(mb, c, z0, z1, r=0.12, head=None, mat='steel'):
    """light pole / mast: a 6-sided tube, optional luminaire head (w, l)."""
    tube(mb, [(c[0], c[1], z0), (c[0], c[1], z1)], r, 6, mat, cap_ends=True)
    if head:
        boxm(mb, (c[0], c[1]), (1, 0), head[0], head[1], (z1 - 0.25, z1 + 0.05), mat)


def on_circle(a, b, F, circ, tol=1.6):
    """edge a -> b (local) lies on a fitted circle (world centre)."""
    if not circ: return False
    c = np.array(F.L(*circ['c']))
    return all(abs(math.hypot(p[0] - c[0], p[1] - c[1]) - circ['R']) < tol for p in (a, b, (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))))


def dof_tower(mb, F, P_local, world, top, side=TOWER_SIDE, mat='precast'):
    """stair / elevator tower whose top is a DOF point: a side x side box containing the point, moved inside the outline
    if the point is at / outside its edge (DOF 1A horizontal accuracy +-20 ft). Returns the tower centre (local)."""
    p = np.array(F.L(*world))
    inner = P_local.buffer(-side / 2 - 0.5)
    if not inner.contains(Point(*p)):
        q = shapely.ops.nearest_points(inner, Point(*p))[0]; p = np.array([q.x, q.y])
    boxm(mb, p, (1, 0), side, side, (0.0, top), mat, (6.0, 3.0), top_mat='coping')
    return p


def parking_structure(B, P, top, deck, slabs, style, car_axis, deck_origin, tiles=None, name='body', feature='', spec=(), dims=None,
                      src='obs', deck_mat='deck', bands=None, lanes=False, ground_open=True):
    """shell (facades, recesses, deck, parapet) + LOD0 details (piers, screens) of an open parking structure."""
    tiles = tiles or TILES
    sh, det = MB(name), MB(name + '_piers')
    bands = bands or level_bands(slabs, top, ground_open=ground_open, deck=deck)
    garage_facade(sh, P, bands, style, tiles, gdetail=det)
    inner = deck_and_parapet(sh, P, deck, top, 'deck_lanes' if lanes else deck_mat, deck_uvf(B.F, car_axis, deck_origin, lanes))
    B.shells.append(Part(name, sh, 'shell', src, feature, spec, dims))
    if not det.empty():
        B.details[0].append(Part(name + '_piers', det, 'detail', 'inf', 'facade piers / perforated screens (module inf)', spec))
    return inner, bands


TILES = {'precast': (6.0, 3.0), 'precast_band': (6.0, 1.6), 'concrete': (4.0, 4.0), 'concrete_board': (4.0, 2.4), 'screen': (3.0, 1.6),
         'screen_edge': (1.0, 1.0), 'interior': (6.0, 6.0), 'hangar_wall': (2.0, 2.0), 'moc_wall': (2.0, 2.0), 'glass_hyatt': (1.5, DL.GH_P),
         'metal_dark': (3.0, 3.0), 'podium': (3.0, 3.0), 'cac_wall': (3.0, 15 * FT), 'glass_band': (3.0, DL.GH_P / 3), 'coping': (3.0, 3.0),
         'ribbon': (3.0, 3.0), 'louvre': (3.0, 1.0), 'slot': (3.0, 1.2), 'hangar_door': (8.375, 8.0), 'spine_wall': (3.0, 3.6), 'concrete_lt': (4.0, 4.0)}


def car_layout(P_local, car_axis, origin_local, lanes=False):
    """candidate parking slots on a deck polygon (local): [(x, y, yaw_rad)] on the deck_uvf grid; a car fits when its
    4.9 x 2.0 m rectangle is 0.4 m inside the deck."""
    ax = loc_dir(car_axis); row = loc_dir(car_axis + 90.0)
    inner = P_local.buffer(-0.4)
    if inner.is_empty: return []
    o = np.asarray(origin_local, float)
    pts = np.vstack([np.array(q.exterior.coords) for q in polys(P_local)])
    du = (pts - o) @ row; dv = (pts - o) @ ax
    out = []
    if lanes:
        js = range(int(math.floor(du.min() / LANE_W)) - 1, int(math.ceil(du.max() / LANE_W)) + 1)
        ks = range(int(math.floor(dv.min() / LANE_PITCH)) - 1, int(math.ceil(dv.max() / LANE_PITCH)) + 1)
        cand = [(j, k, o + row * (LANE_W * (j + 0.5)) + ax * (LANE_PITCH * (k + 0.5)), 0.0) for j in js for k in ks]
    else:
        js = range(int(math.floor(du.min() / STALL_W)) - 1, int(math.ceil(du.max() / STALL_W)) + 1)
        ks = range(int(math.floor(dv.min() / MODULE)) - 1, int(math.ceil(dv.max() / MODULE)) + 1)
        cand = []
        for j in js:
            for k in ks:
                for side, vv, yaw in ((0, 2.75, 0.0), (1, MODULE - 2.75, math.pi)):
                    cand.append((j, 2 * k + side, o + row * (STALL_W * (j + 0.5)) + ax * (MODULE * k + vv), yaw))
    if not cand: return []
    base_yaw = math.atan2(ax[1], ax[0])
    C = np.array([c[2] for c in cand])
    ok = shapely.contains(inner, shapely.points(C[:, 0], C[:, 1]))
    for (j, k, c, yaw), good in zip(cand, ok):
        if not good: continue
        corners = [c + ax * 2.45 * sx + row * 1.0 * sy for sx in (-1, 1) for sy in (-1, 1)]
        if not all(inner.contains(Point(*q)) for q in corners): continue
        out.append((float(c[0]), float(c[1]), base_yaw + yaw, j, k))
    return out


# ================================================================================================ Central garage
def central_garage():
    """Central Parking Garage (BL-02 A, BL-03 row 1): SFO Museum outline with the 58.9-m void, 81 ft [pub] as the parapet
    top (what the 81 ft measures is not stated [unk]), five levels as equal fifths (BL-03 placeholder [unk]); the AirTrain
    ring and the T1 / T2 / T3 stations on Level 5 (= 4/5, BL-03): their polygons are cut out of the garage body above Level 5
    (the guideway rests on the garage structure below it); the DOF roof light poles 101 / 109 ft [pub]."""
    k = 'central_garage'
    full = clean(sfom_union('Central Parking Garage'), 0.05)
    top = 81 * FT; deck = top - PARAPET_H
    slabs = [top * i / 5 for i in (1, 2, 3, 4)]
    h5 = AT.CG_L5
    mr = LB[k]['footprint']['min_rect']
    st = unary_union([AT.ST_POLY[s] for s in ('T1', 'T2', 'T3')])
    cut = unary_union([RAIL, st]).buffer(0.3, join_style=2)
    rest = full.difference(cut)
    under = orient_all(full.intersection(cut).buffer(0))
    pcs = sorted(polys(rest), key=lambda p: p.area, reverse=True)
    main_w = pcs[0]
    slivers_w = [p for p in pcs[1:] if p.area > 5.0]
    B = Bldg(k, 'Central Parking Garage (Bldg 195)', mr['centre'][0], mr['centre'][1], 'pub',
             ['cg_identity', 'cg_levels', 'cg_height', 'cg_void', 'cg_void_obs', 'cg_footprint', 'cg_airtrain_level', 'cg_dof', 'cg_roof_cars'],
             dict(footprint=dim('SFO Museum outline with the void (58.9 m)', 'obs', 'BL-02 A'),
                  parapet_top=dim(round(top, 3), 'pub', '81 ft [pub]; definition (deck / parapet / towers) not stated [unk]'),
                  deck=dim(round(deck, 3), 'inf', '81 ft - 42-in guard'),
                  levels=dim([round(z, 2) for z in slabs], 'unk', '5 levels [pub] drawn as equal fifths (BL-03 placeholder)'),
                  level5=dim(round(h5, 3), 'unk', 'AirTrain ring / stations on Level 5 [pub], 4/5 of 81 ft (BL-03)'),
                  roof_poles=dim({d['oas']: d['agl_m'] for d in LB[k]['dof'] if d['type'] == 'POLE'}, 'pub', 'FAA DOF 1A')),
             inferred=['deck = 81 ft - 1.07 m guard', 'open parking levels with spandrels %.2f / %.2f m, piers every %.0f m' % (SPANDREL_DN, SPANDREL_UP, PIER_DX['cg']),
                       'garage structure under the AirTrain ring / stations up to the guideway deck'],
             unknown=['what 81 ft measures', 'level heights (equal fifths)', 'facade module'],
             not_modelled=['roof ramp "petals" and the helix ring round the void [obs NAIP, not measured]',
                           'other roof light poles (positions not measured)', 'DOF 06-039216 antenna 130 ft (4D: +-250 ft horizontal)',
                           'Level-3 skybridges to the terminals (domestic group)'])
    F = B.F
    P = F.poly(main_w)
    cut_b = cut.boundary

    def style(a, b):
        mid = Point(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
        wm = Point(*F.W(mid.x, mid.y))
        if cut_b.distance(wm) < 0.6:
            return dict(kind='open', pier_dx=PIER_DX['cg'], solid='concrete', z0=h5 + AT.WALL_H)
        return dict(kind='open', pier_dx=PIER_DX['cg'], solid='concrete')
    inner, bands = parking_structure(B, P, top, deck, slabs, style, 117.8, tuple(mr['centre']), name='cg_body', tiles=TILES,
                                     feature='garage body: concrete spandrels, dark open levels, deck + parapet, void',
                                     spec=['cg_footprint', 'cg_void_obs', 'cg_height'], dims=B.dims, src='pub')
    sh = B.shells[-1].mb
    # under the guideway / stations: garage structure to the deck bottom; walls only on the outline (outer facade)
    outline_b = full.boundary
    pl = MB('cg_plinth')
    zt = h5 - AT.DECK_T
    for q in polys(under):
        Q = F.poly(q)

        def st_u(a, b):
            mid = Point(*F.W(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])))
            if outline_b.distance(mid) < 0.6:
                return dict(kind='open', pier_dx=PIER_DX['cg'], solid='concrete', z1=zt)
            return dict(kind='none')
        garage_facade(pl, Q, level_bands(slabs, top, deck=deck), st_u, TILES)
        cap(pl, Q, zt - 0.02, 'concrete', 6.0)
    # slivers outside the guideway: the garage edge up to the trough wall top
    for q in slivers_w:
        Q = F.poly(q)

        def st_s(a, b):
            mid = Point(*F.W(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])))
            if outline_b.distance(mid) < 0.6:
                return dict(kind='open', pier_dx=PIER_DX['cg'], solid='concrete', z1=h5 + AT.WALL_H)
            return dict(kind='solid', solid='concrete', z0=zt, z1=h5 + AT.WALL_H)
        garage_facade(pl, Q, level_bands(slabs, top, deck=deck), st_s, TILES)
        cap(pl, Q, h5 + AT.WALL_H, 'coping', 3.0)
    B.shells.append(Part('cg_plinth', pl, 'shell', 'inf', 'garage structure under / beside the AirTrain ring (to the guideway deck)',
                         ['cg_airtrain_level']))
    # DOF roof light poles
    pd = MB('cg_poles')
    poles = {}
    for d in LB[k]['dof']:
        if d['type'] != 'POLE': continue
        c = F.L(*d['world'])
        pole(pd, c, deck, d['agl_m'] - 0.05, r=0.22, head=(1.4, 0.7))
        poles[d['oas']] = dict(top=d['agl_m'], world=d['world'])
    B.details[0].append(Part('cg_poles', pd, 'detail', 'pub', 'roof light poles at the FAA DOF points (tops 101 / 109 ft)', ['cg_dof']))
    B.details[1].append(Part('cg_poles', pd, 'detail', 'pub', 'roof light poles at the FAA DOF points', ['cg_dof']))
    B.decks.append(dict(poly=inner, z=deck, axis=117.8, origin=tuple(mr['centre']), key=k, count=300,
                        count_src='cg_roof_cars: about 300 (+-100) cars [obs, low, visual]; the detector (1,000) is inflated by kerbs',
                        axis_src='grid-aligned straight rows in each quadrant [obs]; axis 117.8 deg [inf] (detector coherence 0.04)',
                        exclude=[Point(F.L(*p['world'])).buffer(1.5) for p in poles.values()]))
    cm2 = MB('cg_L2')
    stack_coarse(cm2, P.simplify(0.8), top, 'concrete', 'deck_far')
    for q in polys(under):
        stack_coarse(cm2, F.poly(q).simplify(0.8), zt, 'concrete', 'concrete')
    B.coarse.append(Part('cg_L2', cm2, 'coarse', 'pub', 'central garage (coarse)', ['cg_footprint']))
    B.footprint_w = full; B.top = top
    B.anchors = dict(parapet_top=round(top, 3), deck=round(deck, 3), level5=round(h5, 3), levels=[round(z, 3) for z in slabs],
                     void_centre=[-930.8, 275.5], poles=poles, main_area=round(main_w.area, 1), under_area=round(under.area, 1),
                     sliver_area=round(sum(p.area for p in slivers_w), 1))
    return B


# ================================================================================================ Garages A / G
def garage_ag(k):
    """International Garage A / G (BL-02 panel B, BL-03 rows 1-2): the garage body (outline up to u = Lb), the helix drum
    (outline arc at the west end), core cylinder and Garage A rooftop box; deck at the drum ring (dotted on BL-03) [unk]."""
    g = DL.GAR[k]; G = DL.ggeom(k)
    hd = float(g['drum']); deck = hd - PARAPET_H
    c, a, b, L, Lb = G['c'], G['a'], G['b'], G['L'], G['Lb']
    o = c + a * (Lb / 2 - L / 2)
    nm = 'International Garage A (Bldg 95)' if k == 'garage_a' else 'International Garage G (Bldg 495)'
    zt = AT.NET_LEVEL
    h7_sheet = hd * 6 / 8
    B = Bldg(k, nm, o[0], o[1], 'obs', [f'{k}_footprint', f'{k}_height', f'{k}_levels', f'{k}_airtrain_level', 'garage_ag_facade', f'{k}_roof_cars'],
             dict(footprint=dim('SFO Museum outline up to u = %.1f (garage body)' % Lb, 'obs', 'BL-02 B / draw_landside.ggeom'),
                  parapet_top=dim(hd, 'unk', 'drum-ring value %.1f m [obs, low] (range %s); the roof deck is NOT measured: drawn dotted '
                                  'at the drum ring on BL-03' % (hd, g['drum_rng'])),
                  deck=dim(round(deck, 2), 'unk', 'parapet top - %.2f m (42-in guard) [inf]' % PARAPET_H),
                  levels=dim('9 [pub]; level lines at equal ninths of the drum ring (BL-03 placeholder)', 'unk', 'BL-03'),
                  drum=dim(dict(centre=[round(float(G['drum_c'][0]), 2), round(float(G['drum_c'][1]), 2)], D=round(2 * G['R'], 1)), 'obs',
                           'circle fit to the outline arc (BL-02 B)'),
                  core=dim(dict(D=DL.GAR_CORE_D, top=round(hd + 4.0, 2)), 'obs/unk', 'D ~13 m [obs NAIP]; height above the deck unk (BL-03 draws 4 m)'),
                  airtrain_level=dim(round(zt, 2), 'inf', 'network level (landside_airtrain.NET_LEVEL); BL-03 placeholder %.1f m' % h7_sheet),
                  long_face_m=dim(round(Lb, 1), 'obs', 'garage body to the start of the guideway tail')),
             inferred=['deck = drawn parapet top - 1.07 m guard', 'facade module: precast piers every %.1f m, perforated screens between, '
                       'spandrels %.2f / %.2f m about each level line' % (PIER_DX['gar'], SPANDREL_DN, SPANDREL_UP),
                       'drum: precast bands, open band only under the top deck (arched openings [obs spec] drawn as an open band)'],
             unknown=['roof deck height (candidates 24.4-28.0 / 25-30 [disputed] / %s [NAIP 2-D shift] / %.1f drum ring)' %
                      (LB[k]['shift_scan']['peaks'][0]['h_if_true_footprint_m'], hd),
                      'level heights (equal ninths placeholder)', 'core cylinder height (drawn 4 m)'] +
                     (['rooftop box height (drawn 3.5 m)'] if G['box'] else []),
             not_modelled=['square stair / elevator towers above the parapet [obs spec, positions not measured]', 'roof light poles'],
             deviations=['AirTrain level %.2f m (network level) instead of the BL-03 Level-7 placeholder %.1f m (6/8 of the drum ring, [unk]): '
                         'the Grand Hyatt station is 40 m along the same track; %.2f m is inside the sheet\'s own [inf] range 18.3-21.0 m'
                         % (zt, h7_sheet, zt)])
    F = B.F
    cutter = Polygon([c + a * (-L / 2 - 60) + b * 200, c + a * (Lb - L / 2) + b * 200, c + a * (Lb - L / 2) - b * 200, c + a * (-L / 2 - 60) - b * 200])
    body_w = largest(sfom_union(g['nm']).intersection(cutter))
    if not g['rail_near']:
        # Garage G: the station stands along the NNW face and the guideway runs along it: the guideway polygon is cut out of
        # the body (no shared volume); the station is built on its part outside the body (landside_airtrain station_exclude)
        body_w = largest(body_w.difference(RAIL.buffer(0.4, join_style=2)))
    else:
        # Garage A: the two single tracks run through the body along its SSE half from the west face (u ~2.6) to the east cut
        # (u = Lb), through the station (BL-03 "along the SSE side, behind this face"): the track strips are united with the
        # body so the tracks are inside it end to end (the guideway is clipped there; portals at both faces)
        strip = Polygon([c + a * (2.0 - L / 2) - b * 30, c + a * (Lb - L / 2) - b * 30, c + a * (Lb - L / 2) - b * 7, c + a * (2.0 - L / 2) - b * 7])
        body_w = largest(unary_union([body_w, RAIL.intersection(strip).buffer(0.3, join_style=2)]).buffer(0.05).buffer(-0.05))
    body_w = body_w.simplify(0.05, preserve_topology=True)
    P = F.poly(body_w)
    circ = dict(c=[float(G['drum_c'][0]), float(G['drum_c'][1])], R=float(G['R']))
    slabs = [hd * i / 9 for i in range(1, 9)]
    portal = []
    if g['rail_near']:
        cross = body_w.exterior.intersection(RAIL.buffer(0.2))
        for seg in getattr(cross, 'geoms', [cross]):
            if seg.geom_type != 'LineString' or seg.length < 2.0: continue
            q = np.array(seg.coords); dd = q[-1] - q[0]
            if abs(dd @ a) / (np.hypot(*dd) or 1) < 0.3:                  # faces across the tracks only (u ~2.6 and u = Lb)
                portal.append([F.L(*p) for p in (q[0], q[-1])])
    portal_lines = [LineString(p) for p in portal]
    ad = np.array([a[0], -a[1]])
    rail_edge = RAIL.buffer(0.6, join_style=2)

    # Garage A station block (photo l1): the faces across the tracks are solid precast (panel grid, a dark window slot above the
    # portal) for STATION_BLOCK_W m either side of the guideway strips [obs l1; extent inf]
    rail_strip_l = F.poly(RAIL.intersection(body_w).buffer(0)) if g['rail_near'] else Polygon()

    def style(pa, pb):
        seg = LineString([pa, pb])
        for pl in portal_lines:
            if seg.length > 0.5 and seg.distance(Point(pl.coords[0])) < 0.5 and seg.distance(Point(pl.coords[-1])) < 0.5:
                s_a = seg.project(Point(pl.coords[0])); s_b = seg.project(Point(pl.coords[-1]))
                return dict(kind='solid', solid='precast', slots=True,
                            holes=[(min(s_a, s_b) + 0.6, max(s_a, s_b) - 0.6, zt - AT.DECK_T - 0.3, zt + AT.PORTAL_H)])
        if on_circle(pa, pb, F, circ):
            return dict(kind='solid', solid='precast_band')
        d = np.array(pb, float) - np.array(pa, float); d /= np.linalg.norm(d)
        if g['rail_near'] and abs(d @ ad) < 0.5 and rail_strip_l.distance(seg) < STATION_BLOCK_W:
            return dict(kind='solid', solid='precast', slots=True)
        # every other face: open levels behind the perforated screens [obs spec garage_ag_facade, photos l1 / a2]
        return dict(kind='screen', pier_dx=PIER_DX['gar'] if abs(d @ ad) > 0.85 else PIER_DX['gar_end'], solid='precast')
    axis = float(LB[k]['roof_cars']['car_row_axis_heading_deg'])
    inner, bands = parking_structure(B, P, hd, deck, slabs, style, axis, (float(c[0]), float(c[1])), name=f'{k}_body',
                                     feature='garage body: precast spandrels, perforated screens, dark open levels, deck + parapet',
                                     spec=['garage_ag_facade', f'{k}_footprint'], dims=B.dims, src='obs')
    cl = np.array(F.L(*circ['c']))
    zo0, zo1 = slabs[-1] + SPANDREL_UP + 0.4, deck - SPANDREL_DN - 0.2
    dr = MB('drum_openings')
    for p0, p1, s0 in ring_edges(P):
        if not on_circle(p0, p1, F, circ): continue
        n, Le = edge_normal(p0, p1)
        q0 = np.array(p0) + n * 0.05; q1 = np.array(p1) + n * 0.05
        dr.quad_wall(tuple(q0), tuple(q1), zo0, zo1, zo0, zo1, 'interior', s0, (2.0, 2.0))
    B.details[0].append(Part(f'{k}_drum_openings', dr, 'detail', 'obs', 'drum top openings (arched openings [obs spec]; drawn as a dark band)',
                             ['garage_ag_facade']))
    B.details[1].append(Part(f'{k}_drum_openings', dr, 'detail', 'obs', 'drum top openings', ['garage_ag_facade']))
    cm = MB(f'{k}_core')
    cyl(cm, cl, DL.GAR_CORE_D / 2, deck, hd + 4.0, 24, 'precast_band', TILES['precast_band'], top='coping', smooth=True)
    B.shells.append(Part(f'{k}_core', cm, 'shell', 'obs', 'helix core cylinder above the deck (D obs NAIP; height unk, drawn 4 m)',
                         ['garage_ag_facade'], dict(D=dim(DL.GAR_CORE_D, 'obs', 'NAIP dark disc, approx'), top=dim(hd + 4.0, 'unk', 'BL-03 drawn 4 m'))))
    excl = [Point(cl).buffer(DL.GAR_CORE_D / 2 + 1.5)]
    if G['box']:
        bx = MB(f'{k}_rooftop_box')
        bp = F.poly(Polygon(G['box'][4]))
        walls(bx, bp, deck, hd + 3.5, 'precast', TILES['precast'])
        cap(bx, bp, hd + 3.5, 'coping', 6.0)
        B.shells.append(Part(f'{k}_rooftop_box', bx, 'shell', 'obs', 'rooftop box (NAIP, lean-corrected; stair / elevator tower over the station? [inf])',
                             [f'{k}_height'], dict(plan=dim('u %.0f-%.0f' % (G['box'][0], G['box'][1]), 'obs', 'BL-02 B'),
                                                   top=dim(hd + 3.5, 'unk', 'BL-03 drawn 3.5 m'))))
        excl.append(bp.buffer(1.5))
    rc = LB[k]['roof_cars']
    B.decks.append(dict(poly=inner, z=deck, axis=axis, origin=(float(c[0]), float(c[1])), key=k,
                        density=rc['cars_per_1000m2'], count_src='%s_roof_cars: %d detected (+-30 %%), %.1f per 1,000 m2 [obs, low]' % (k, rc['cars_detected'], rc['cars_per_1000m2']),
                        axis_src='car long axis %.0f deg [obs NAIP, coherence %.2f]' % (axis, rc['row_axis_coherence']), exclude=excl))
    tn = MB(f'{k}_portal')
    for pl in portal:
        pa, pb = np.array(pl[0]), np.array(pl[-1])
        n, Le = edge_normal(pa, pb)
        mid = 0.5 * (pa + pb)
        if P.contains(Point(*(mid + n * 1.0))): n = -n
        if P.contains(Point(*(mid + n * 1.0))) or not P.buffer(0.01).contains(Point(*(mid - n * 1.0))): continue
        din = -n * 10.0
        if np.cross(np.r_[pb - pa, 0], np.r_[n, 0])[2] > 0: pa, pb = pb, pa
        z0, z1 = zt - AT.DECK_T - 0.3, zt + AT.PORTAL_H
        d = (pb - pa) / Le
        pa2, pb2 = pa + d * 0.6, pb - d * 0.6
        zf = z0 + AT.DECK_T + 0.3
        # tunnel faces seen from inside: every normal points into the tunnel box (towards its axis / the opening)
        cen = np.r_[0.5 * (pa2 + pb2) + din * 0.5, 0.5 * (zf + z1)]
        uvq = [(0, 0), (1, 0), (1, 1), (0, 1)]

        def inward(pts, mat, z_c=None):
            P_ = np.asarray(pts, float); c_ = P_.mean(0)
            tn.face_dir(pts, mat, uvq, cen - c_)
        inward([(*(pa2 + din), z0), (*(pb2 + din), z0), (*(pb2 + din), z1), (*(pa2 + din), z1)], 'interior')     # back wall
        inward([(*pa2, z0), (*(pa2 + din), z0), (*(pa2 + din), z1), (*pa2, z1)], 'interior')                        # sides
        inward([(*pb2, z0), (*(pb2 + din), z0), (*(pb2 + din), z1), (*pb2, z1)], 'interior')
        q = [pa2, pb2, pb2 + din, pa2 + din]
        inward([(p[0], p[1], z1) for p in q], 'interior')                                                          # soffit
        tn.face_dir([(p[0], p[1], zf) for p in q], 'guideway_deck', uvq, (0, 0, 1))                                # track deck
        tn.face_dir([(*pa2, z0), (*pb2, z0), (*pb2, zf), (*pa2, zf)], 'guideway', uvq, (-din[0], -din[1], 0))      # deck edge
    if not tn.empty():
        B.shells.append(Part(f'{k}_portal', tn, 'shell', 'obs', 'AirTrain portal into the garage station (guideway crossing [obs polygons]; '
                             'opening at the network level [inf])', [f'{k}_airtrain_level', 'at_section']))
    B.anchors = dict(drum_ring=hd, deck=round(deck, 2), core_top=hd + 4.0, levels=[round(z, 2) for z in slabs], Lb=Lb, u_axis_world=[float(a[0]), float(a[1])],
                     u0_world=[float((c - a * L / 2)[0]), float((c - a * L / 2)[1])], portal_spans=len(portal), airtrain_level=round(zt, 3),
                     drum=dict(c=circ['c'], R=circ['R']), body_area=round(body_w.area, 1))
    cm2 = MB(f'{k}_L2')
    stack_coarse(cm2, P.simplify(0.8), hd, 'precast', 'deck_far')
    B.coarse.append(Part(f'{k}_L2', cm2, 'coarse', 'obs', 'garage body (coarse)', [f'{k}_footprint']))
    B.footprint_w = body_w; B.top = hd + 4.0
    B.body_w = body_w
    return B


# ================================================================================================ LTP garages
def ltp1():
    """Long-Term Parking Garage 1 (BL-02 C, BL-03 row 3): outline (with its corner helix lobes), parapet 16.5 m [obs NAIP
    shadow], >= 5 levels [inf] drawn as L1 at grade and L5 = the roof deck (equal quarters) [unk]; the two DOF tops 86 / 91 ft
    [pub] as stair / elevator towers [inf identity, 7 x 7 m inf]."""
    k = 'ltp_garage_1'
    full = clean(sfom_union('Long-Term Parking Garage 1'), 0.05)
    top = float(LV['ltp1_parapet_obs']['value']); deck = top - PARAPET_H
    slabs = [deck * i / 4 for i in (1, 2, 3)]
    mr = LB[k]['footprint']['min_rect']
    B = Bldg(k, 'Long-Term Parking Garage 1 (Bldg 795)', mr['centre'][0], mr['centre'][1], 'obs',
             ['ltp1_identity', 'ltp1_parapet_obs', 'ltp1_dof', 'ltp1_levels', 'ltp1_footprint', 'ltp1_roof_cars', 'ltp1_team'],
             dict(footprint=dim('SFO Museum outline', 'obs', 'BL-02 C'), parapet_top=dim(top, 'obs', 'north-end parapet, NAIP shadow (15.9-16.8)'),
                  deck=dim(round(deck, 2), 'inf', 'parapet - 1.07 m'),
                  levels=dim([round(z, 2) for z in slabs], 'unk', '>= 5 levels [inf]; L5 = the deck, equal quarters (placeholder)'),
                  towers=dim({d['oas']: d['agl_m'] for d in LB[k]['dof']}, 'pub', 'FAA DOF 1A tops; tower identity / size inf')),
             inferred=['deck = parapet - 1.07 m', 'DOF tops = stair / elevator towers 7 x 7 m', 'precast spandrels (architectural precast by Willis [pub])'],
             unknown=['number of levels', 'level heights'],
             not_modelled=['helix ramp interiors', 'Level-5 links to LTP 2 and the AirTrain bridge (positions not measured)'])
    F = B.F
    P = F.poly(full)
    style = lambda a, b: dict(kind='open', pier_dx=PIER_DX['ltp1'], solid='precast')
    axis = float(LB[k]['roof_cars']['car_row_axis_heading_deg'])
    inner, bands = parking_structure(B, P, top, deck, slabs, style, axis, tuple(mr['centre']), name='ltp1_body',
                                     feature='garage body: precast spandrels, open levels, deck + parapet', spec=['ltp1_footprint'], dims=B.dims)
    tw = MB('ltp1_towers'); excl = []; tws = {}
    for d in LB[k]['dof']:
        p = dof_tower(tw, F, P, d['world'], d['agl_m'])
        excl.append(Point(*p).buffer(TOWER_SIDE / 2 + 1.5).envelope.buffer(1.0))
        tws[d['oas']] = dict(top=d['agl_m'], centre_local=[round(float(p[0]), 2), round(float(p[1]), 2)], world=d['world'])
    B.shells.append(Part('ltp1_towers', tw, 'shell', 'pub', 'stair / elevator towers to the DOF tops 86 / 91 ft (identity / size inf)', ['ltp1_dof']))
    rc = LB[k]['roof_cars']
    B.decks.append(dict(poly=inner, z=deck, axis=axis, origin=tuple(mr['centre']), key=k, density=rc['cars_per_1000m2'],
                        count_src='ltp1_roof_cars: %d detected, %.1f per 1,000 m2 [obs, low]' % (rc['cars_detected'], rc['cars_per_1000m2']),
                        axis_src='car long axis %.0f deg [obs NAIP; "cars at about 70 deg"]' % axis, exclude=excl))
    cm2 = MB('ltp1_L2'); stack_coarse(cm2, P.simplify(0.8), top, 'precast', 'deck_far')
    for d in tws.values():
        boxm(cm2, d['centre_local'], (1, 0), TOWER_SIDE, TOWER_SIDE, (top - 0.1, d['top']), 'precast', top_mat='coping')
    B.coarse.append(Part('ltp1_L2', cm2, 'coarse', 'obs', 'LTP 1 (coarse)', ['ltp1_footprint']))
    B.footprint_w = full; B.top = max(d['agl_m'] for d in LB[k]['dof'])
    B.anchors = dict(parapet_top=top, deck=round(deck, 3), levels=[round(z, 3) for z in slabs], towers=tws)
    return B


def ltp2():
    """Long-Term Parking Garage 2 (BL-02 C, BL-03 row 3): 6 levels x 12 ft [pub], deck 60 ft [inf] (level 1 at grade [inf]),
    exposed concrete frame with deep spandrels and open bays [obs photo l2], PV canopies above the deck [pub; height unk,
    BL-03 dotted at the deck + 3.5 m; layout inf]."""
    k = 'ltp_garage_2'
    full = clean(sfom_union('Long-Term Parking Garage 2'), 0.05)
    deck = 60 * FT; top = deck + PARAPET_H
    slabs = [12 * FT * i for i in (1, 2, 3, 4)]
    mr = LB[k]['footprint']['min_rect']
    pv_h = 3.5
    B = Bldg(k, 'Long-Term Parking Garage 2 (Bldg 794)', mr['centre'][0], mr['centre'][1], 'pub',
             ['ltp2_identity', 'ltp2_levels', 'ltp2_floor_height', 'ltp2_roof_deck_h', 'ltp2_roof_pv', 'ltp2_facade', 'ltp2_footprint', 'ltp2_roof_cars', 'ltp2_structure'],
             dict(footprint=dim('SFO Museum outline', 'obs', 'BL-02 C'), deck=dim(round(deck, 3), 'inf', '5 x 12 ft [pub pitch, L1 at grade inf]'),
                  levels=dim([round(z, 3) for z in slabs], 'pub', '12 ft floor-to-floor [pub]'), parapet_top=dim(round(top, 3), 'inf', 'deck + 1.07 m'),
                  pv_canopy=dim(round(deck + pv_h, 2), 'unk', 'BL-03 dotted at the deck + 3.5 m')),
             inferred=['exposed frame: columns every 9.1 m, spandrels %.2f / 1.10 m' % SPANDREL_DN, 'PV canopy rows over the stall rows (layout inf)'],
             unknown=['PV canopy height and layout'],
             not_modelled=['central lightwell [pub, position not measured]', 'elevator tower with the Morse-code glass, louvred corner towers [pub, positions not measured]',
                           'Level-5 links (positions not measured)'])
    F = B.F
    P = F.poly(full)
    style = lambda a, b: dict(kind='open', pier_dx=PIER_DX['ltp2'], solid='concrete_lt')
    axis = float(LB[k]['roof_cars']['car_row_axis_heading_deg'])
    bands = level_bands(slabs, top, deck=deck, up=1.10)
    inner, _ = parking_structure(B, P, top, deck, slabs, style, axis, tuple(mr['centre']), name='ltp2_body', bands=bands,
                                 feature='exposed concrete frame, deep spandrels, open bays, deck + parapet', spec=['ltp2_facade', 'ltp2_footprint'], dims=B.dims)
    # PV canopies: one per parking module over its two stall rows + aisle, 4 m inside the parapet, columns every 7.8 m [inf]
    ax = loc_dir(axis); row = loc_dir(axis + 90.0)
    o = np.array(F.L(*mr['centre']))
    pv0, pv1 = MB('ltp2_pv0'), MB('ltp2_pv1')
    area = inner.buffer(-4.0)
    pts = np.array(area.exterior.coords) if not area.is_empty else np.zeros((1, 2))
    dv = (pts - o) @ ax
    n_pv = 0
    pv_polys = []
    for kk in range(int(math.floor(dv.min() / MODULE)) - 1, int(math.ceil(dv.max() / MODULE)) + 1):
        v0, v1 = MODULE * kk + 0.6, MODULE * (kk + 1) - 0.6
        strip = Polygon([o + ax * v0 - row * 400, o + ax * v0 + row * 400, o + ax * v1 + row * 400, o + ax * v1 - row * 400])
        for q in polys(area.intersection(strip)):
            if q.area < 40: continue
            q = orient_all(q)
            pv_polys.append(q)
            zf = lambda x, y, v0=v0: deck + pv_h - 0.6 + 0.6 * ((np.array([x, y]) - o) @ ax - v0) / (v1 - v0)    # tilted ~2 deg
            for mbq in (pv0, pv1):
                cap(mbq, q, 0, 'pv', 4.0, zf=zf)
                cap(mbq, q, 0, 'steel', 4.0, down=True, zf=lambda x, y, zf=zf: zf(x, y) - 0.12)
            # columns along the module centre line
            cl = LineString([o + ax * (v0 + v1) / 2 - row * 400, o + ax * (v0 + v1) / 2 + row * 400]).intersection(q.buffer(-1.0))
            for seg in getattr(cl, 'geoms', [cl]):
                if seg.is_empty or seg.length < 1: continue
                for t in np.arange(0.0, seg.length + 0.01, 7.8):
                    pp = seg.interpolate(t)
                    for mbq, sides in ((pv0, 8), (pv1, 4)):
                        tube(mbq, [(pp.x, pp.y, deck), (pp.x, pp.y, float(zf(pp.x, pp.y)) - 0.1)], 0.15, sides, 'steel')
            n_pv += 1
    B.details[0].append(Part('ltp2_pv', pv0, 'detail', 'pub', 'PV canopies on the roof [pub]; height / layout inf-unk', ['ltp2_roof_pv']))
    B.details[1].append(Part('ltp2_pv', pv1, 'detail', 'pub', 'PV canopies (LOD1)', ['ltp2_roof_pv']))
    rc = LB[k]['roof_cars']
    B.decks.append(dict(poly=inner, z=deck, axis=axis, origin=tuple(mr['centre']), key=k, density=rc['cars_per_1000m2'],
                        count_src='ltp2_roof_cars: %d detected, %.1f per 1,000 m2 [obs, low; PV hides cars]' % (rc['cars_detected'], rc['cars_per_1000m2']),
                        axis_src='car long axis %.0f deg [obs NAIP]' % axis, exclude=[]))
    cm2 = MB('ltp2_L2'); stack_coarse(cm2, P.simplify(0.8), top, 'concrete_lt', 'deck_far')
    for q in pv_polys:
        cap(cm2, q.simplify(0.5), deck + pv_h, 'pv', 6.0)
    B.coarse.append(Part('ltp2_L2', cm2, 'coarse', 'pub', 'LTP 2 (coarse) + PV', ['ltp2_footprint']))
    B.footprint_w = full; B.top = deck + pv_h
    B.anchors = dict(deck=round(deck, 3), parapet_top=round(top, 3), levels=[round(z, 3) for z in slabs], pv_top=round(deck + pv_h, 2), pv_rows=n_pv)
    return B


# ================================================================================================ Rental Car Center
def rcc():
    """Rental Car Center (BL-02 E, BL-03 row 3): roof outline 54 ft [pub DOF, three points], 59-ft DOF point on the west face
    (a raised element: stair / elevator tower [inf]), 5 levels as equal quarters of 54 ft (L5 = the deck) [unk]; the west
    (AirTrain) wall from photo l5 / BL-03 wall key: board-formed concrete, ribbon windows at the platform level, a concrete
    band and a canted louvre screen above; nose-to-tail rental lanes on the deck [obs]."""
    k = 'rental_car_center'
    full = clean(sfom_union('Rental Car Center'), 0.05)
    top = 54 * FT; deck = top - PARAPET_H
    slabs = [top * i / 4 for i in (1, 2, 3)]
    mr = LB[k]['footprint']['min_rect']
    hp = AT.RCC_PLATFORM
    zw0, zw1 = hp - 0.4, hp + 2.6             # ribbon windows [obs l5; heights inf]
    zb1 = hp + 4.4                           # concrete band top [inf]
    lean = 1.2                               # louvre screen leans out by 1.2 m at its top [obs l5 "canted"; amount inf]
    B = Bldg(k, 'Rental Car Center (Bldg 780)', mr['centre'][0], mr['centre'][1], 'pub',
             ['rcc_identity', 'rcc_levels', 'rcc_height', 'rcc_dof', 'rcc_facade', 'rcc_footprint', 'rcc_roof_cars', 'rcc_height_check'],
             dict(footprint=dim('SFO Museum outline', 'obs', 'BL-02 E'), parapet_top=dim(round(top, 3), 'pub', 'DOF roof-outline points 54 ft (x3)'),
                  deck=dim(round(deck, 3), 'inf', '54 ft - 1.07 m'), levels=dim([round(z, 2) for z in slabs], 'unk', 'equal quarters (BL-03)'),
                  west_wall=dim(dict(ribbon=[round(zw0, 2), round(zw1, 2)], band_top=round(zb1, 2), louvre_lean=lean), 'inf',
                                'photo l5 order (BL-03 wall key); heights inf'),
                  tower_59ft=dim(59 * FT, 'pub', 'DOF 06-035204 (raised element; tower form inf)')),
             inferred=['west-wall band heights', 'canted louvre screen lean 1.2 m', 'other faces: open parking levels (not photographed)',
                       'rental lanes 3.0 m / cars every 5.6 m'],
             unknown=['what "66 ft" measures', 'level heights', 'facades other than the west wall'],
             conflicts=['DOF 06-035328 BLDG 34 ft (10.4 m) inside the east part of the outline: not modelled as a lower part (outline drawn at 54 ft)',
                        'RCC station platform: BL-03 placeholder 12.35 m vs photo l5 (~5-6 m: see landside_airtrain.RCC_PLATFORM)'],
             not_modelled=['the "66-foot-tall" element (definition disputed)', 'QTA building 782'],
             deviations=['west wall / station platform at %.1f m (photo l5) instead of the BL-03 L4 placeholder 12.35 m [unk]' % hp])
    F = B.F
    P = F.poly(full)
    # the west (AirTrain) wall: the outline between its N-most corner RCC_N and its SW corner RCC_S (BL-03 projects it on that
    # chord; the outline bulges 20 m west of the chord at z -1140)
    ring_w = [tuple(q) for q in np.array(full.exterior.coords)[:-1]]
    iN = int(np.argmin([math.dist(q, DL.RCC_N) for q in ring_w])); iS = int(np.argmin([math.dist(q, DL.RCC_S) for q in ring_w]))
    seq = [ring_w[(iN + i) % len(ring_w)] for i in range(((iS - iN) % len(ring_w)) + 1)]
    seq2 = [ring_w[(iS + i) % len(ring_w)] for i in range(((iN - iS) % len(ring_w)) + 1)]
    wline_w = LineString(seq if min(q[0] for q in seq) < min(q[0] for q in seq2) else seq2)
    west = LineString([F.L(*q) for q in wline_w.coords])

    def is_west(a, b):
        return west.distance(Point(*a)) < 0.3 and west.distance(Point(*b)) < 0.3 and LineString([a, b]).length > 1.0

    def style(a, b):
        if is_west(a, b):
            return dict(kind='none')
        return dict(kind='open', pier_dx=PIER_DX['rcc'], solid='concrete')
    axis = float(LB[k]['roof_cars']['car_row_axis_heading_deg'])
    inner, bands = parking_structure(B, P, top, deck, slabs, style, axis, tuple(mr['centre']), name='rcc_body', lanes=True,
                                     feature='garage body: concrete spandrels, open levels, deck + parapet (rental lanes)', spec=['rcc_footprint'], dims=B.dims)
    sh = B.shells[-1].mb
    lv = MB('rcc_louvres')
    for a, b, s0 in ring_edges(P):
        if not is_west(a, b): continue
        n, L = edge_normal(a, b)
        sh.quad_wall(a, b, 0.0, zw0, 0.0, zw0, 'concrete_board', s0, TILES['concrete_board'])
        sh.quad_wall(a, b, zw0, zw1, zw0, zw1, 'ribbon', s0, TILES['ribbon'], v0=zw0)
        sh.quad_wall(a, b, zw1, zb1, zw1, zb1, 'concrete_board', s0, TILES['concrete_board'])
        # canted louvre screen: from the band top (at the wall plane) leaning out to `lean` at the parapet top
        A2 = np.array(a) + n * lean; B2 = np.array(b) + n * lean
        sh.face([(a[0], a[1], zb1), (b[0], b[1], zb1), (B2[0], B2[1], top), (A2[0], A2[1], top)], 'louvre',
                [(s0 / 3.0, 0), ((s0 + L) / 3.0, 0), ((s0 + L) / 3.0, (top - zb1) / 1.0), (s0 / 3.0, (top - zb1) / 1.0)])
        sh.face([(A2[0], A2[1], top), (B2[0], B2[1], top), (b[0], b[1], top), (a[0], a[1], top)], 'coping', [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
        # louvre blades (LOD0): horizontal blades every 0.6 m, 0.25 m deep, following the cant
        for z in np.arange(zb1 + 0.3, top - 0.1, 0.6):
            t = (z - zb1) / (top - zb1)
            off = n * (lean * t + 0.02)
            p0 = np.array(a) + off; p1 = np.array(b) + off
            q0 = p0 + n * 0.25; q1 = p1 + n * 0.25
            uvb = [(0, 0), (L / 3, 0), (L / 3, 0.1), (0, 0.1)]
            lv.face_dir([(p0[0], p0[1], z), (p1[0], p1[1], z), (q1[0], q1[1], z - 0.12), (q0[0], q0[1], z - 0.12)], 'louvre_blade', uvb,
                        (n[0] * 0.12, n[1] * 0.12, 0.25))
            lv.face_dir([(q0[0], q0[1], z - 0.12), (q1[0], q1[1], z - 0.12), (p1[0], p1[1], z - 0.14), (p0[0], p0[1], z - 0.14)], 'louvre_blade', uvb,
                        (-n[0] * 0.02, -n[1] * 0.02, -0.25))
        # board-formed concrete pilasters between the ribbon windows every 9 m (LOD0)
        for s in np.arange(4.5, L - 1.0, 9.0):
            d = (np.array(b) - np.array(a)) / L; cc = np.array(a) + d * s + n * 0.15
            boxm(lv, cc, d, 0.6, 0.3, (zw0, zw1), 'concrete_board', TILES['concrete_board'], top=False)
    B.details[0].append(Part('rcc_louvres', lv, 'detail', 'obs', 'louvre blades and pilasters of the west wall (photo l5; module inf)', ['rcc_facade']))
    tw = MB('rcc_tower59')
    d59 = next(d for d in LB[k]['dof'] if d['oas'] == '06-035204')
    p59 = dof_tower(tw, F, P, d59['world'], d59['agl_m'], mat='concrete')
    B.shells.append(Part('rcc_tower59', tw, 'shell', 'pub', 'raised element at the 59-ft DOF point (stair / elevator tower, form inf)', ['rcc_dof']))
    rc = LB[k]['roof_cars']
    B.decks.append(dict(poly=inner, z=deck, axis=axis, origin=tuple(mr['centre']), key=k, density=rc['cars_per_1000m2'], lanes=True,
                        count_src='rcc_roof_cars: %d detected, %.1f per 1,000 m2 (densest roof) [obs, low]' % (rc['cars_detected'], rc['cars_per_1000m2']),
                        axis_src='nose-to-tail lanes at %.0f deg [obs NAIP; "115-125 deg"]' % axis,
                        exclude=[Point(*p59).buffer(TOWER_SIDE / 2 + 1.5).envelope]))
    cm2 = MB('rcc_L2'); stack_coarse(cm2, P.simplify(0.8), top, 'concrete', 'deck_far')
    boxm(cm2, p59, (1, 0), TOWER_SIDE, TOWER_SIDE, (top - 0.1, d59['agl_m']), 'concrete')
    B.coarse.append(Part('rcc_L2', cm2, 'coarse', 'pub', 'RCC (coarse)', ['rcc_footprint']))
    B.footprint_w = full; B.top = d59['agl_m']
    B.anchors = dict(parapet_top=round(top, 3), deck=round(deck, 3), levels=[round(z, 3) for z in slabs], platform=hp, ribbon=[zw0, zw1],
                     band_top=zb1, tower59=dict(top=d59['agl_m'], centre_local=[round(float(p59[0]), 2), round(float(p59[1]), 2)]),
                     west_chord=[list(DL.RCC_N), list(DL.RCC_S)])
    return B


# ================================================================================================ Grand Hyatt
def hyatt():
    """Grand Hyatt at SFO (BL-02 B, BL-03 row 2 east face): the crescent outline at the inferred 44 m (13.2 pitches of
    3.33 m, photo l4 [inf]); east-face fractions of hyatt_elev() (l4): dark metal podium under the south 47 %, recessed
    colonnade at 0.02-0.10, curved banded end bay 0-0.049, light concrete end pier with the red sign, framed bay
    0.615-0.842, stepped dark penthouse 0.518-0.692 / 0.615-0.742, four masts; glass curtain wall with one spandrel per floor."""
    k = 'grand_hyatt'
    full = clean(sfom_union('Grand Hyatt Hotel'), 0.05)
    mr = LB[k]['footprint']['min_rect']
    W = mr['length_m']; p = DL.GH_P; H = 13.2 * p; hp = DL.GH_POD * p; hc = (DL.GH_POD + DL.GH_COL) * p
    B = Bldg(k, 'Grand Hyatt at SFO (Bldg 55)', mr['centre'][0], mr['centre'][1], 'inf',
             ['gh_identity', 'gh_stories', 'gh_height', 'gh_plan_shape', 'gh_facade', 'gh_footprint', 'gh_lobby_level'],
             dict(footprint=dim('SFO Museum outline (crescent incl. podium / connector)', 'obs', 'BL-02 B'),
                  parapet_top=dim(round(H, 2), 'inf', '13.2 pitches x 3.33 m (photo l4); 40-48 m; NOT published'),
                  podium=dim(round(hp, 2), 'inf', '3.2 pitches'), colonnade_top=dim(round(hc, 2), 'inf', '4.2 pitches'),
                  face_fractions=dim(dict(podium=0.47, colonnade=[0.02, 0.10], end_bay=0.049, framed=[0.615, 0.842], penthouse=[[0.518, 0.692], [0.615, 0.742]],
                                          masts=[-0.008, 0.027, 0.905, 0.961]), 'obs', 'photo l4 fractions (BL-03 hyatt_elev)')),
             inferred=['height 44 m', 'floor pitch 3.33 m', 'mullion module 1.5 m (BL-03 schematic 3 m with an intermediate)', 'west (convex) face: same curtain wall',
                       'penthouse depth: the slab minus 4 m each side', 'podium / colonnade wrap on the south-facing faces of the podium zone'],
             unknown=['height (40-48)', 'slab vs podium plan (the outline includes both)'],
             conflicts=['spec "taller straight block at the north end" vs photo l4 (one parapet level): drawn at the common parapet (BL-03)'],
             not_modelled=['roof PV (NAIP shows arrays; layout not measured)', 'porte-cochere, enclosed AirTrain bridge'])
    F = B.F
    Pfull = F.poly(full)
    ax = loc_dir(mr['long_side_heading_deg']); east = np.array([ax[1], -ax[0]])      # right of NNE = ESE
    o = np.array(F.L(*mr['centre']))
    f_of = lambda q: float((np.asarray(q, float) - o) @ ax + W / 2) / W
    # podium zone: NAIP 2024 with the 44-m relief shift (ITB k(x) model, 13.4 m east) puts the slab roof's east edge ~17 m west
    # of the outline's east edge along the south part (f < 0.47), where the imaged 10.7-m shift fits the outline's east edge
    # (the podium roof): there the outline is the podium, the slab face stands PODIUM_D behind it [obs NAIP, approx]
    eb = []
    for a_, b_, s0 in ring_edges(Pfull):
        n_, L_ = edge_normal(a_, b_)
        if float(n_ @ east) > 0.3 and f_of(0.5 * (np.array(a_) + np.array(b_))) < 0.47:
            eb.append(LineString([a_, b_]))
    half_s = Polygon([o + ax * (-W) - east * 300, o + ax * (0.47 * W - W / 2) - east * 300, o + ax * (0.47 * W - W / 2) + east * 300, o + ax * (-W) + east * 300])
    from shapely.ops import linemerge
    zone = Polygon()
    if eb:
        ml = linemerge(unary_union(eb))
        strips = [g.buffer(GH_PODIUM_D, single_sided=True, cap_style=2, join_style=2) for g in getattr(ml, 'geoms', [ml])]
        # single-sided buffer to the LEFT of the CCW exterior = the inside; keep the side that overlaps the outline most
        strips = [g if g.intersection(Pfull).area > 0.5 * g.area else g.buffer(0) for g in strips]
        zone = orient_all(Pfull.intersection(unary_union(strips)).intersection(half_s).buffer(0))
    P = largest(Pfull.difference(zone.buffer(0.01)))
    P = orient_all(P.simplify(0.05))
    podium = [orient_all(q) for q in polys(zone) if q.area > 20]
    sh, det = MB('gh_body'), MB('gh_detail')
    cuts_f = [0.02, 0.049, 0.10, 0.47, 0.615, 0.842]

    def zones(f, eastish):
        """vertical bands [(z0, z1, mat, inset, v0)] of a facade piece at face fraction f."""
        if f < 0.049 and eastish:
            base = [(0.0, hp, 'metal_dark', 0.0, 0.0), (hp, hc, 'metal_dark', 2.0, 0.0) if 0.02 <= f else (hp, hc, 'glass_band', 0.0, 0.0),
                    (hc, H, 'glass_band', 0.0, hc)]
            return base
        out = []
        if f < 0.47 and eastish:
            out.append((0.0, hp, 'metal_dark', 0.0, 0.0))
            out.append((hp, hc, 'metal_dark', 2.0, 0.0) if 0.02 <= f < 0.10 else (hp, hc, 'glass_hyatt', 0.0, hc - p))
        else:
            out.append((0.0, hc, 'glass_hyatt', 0.0, hc - p))
        out.append((hc, H, 'glass_hyatt', 0.0, hc))
        return out
    zb = zone.boundary if not zone.is_empty else None
    for a, b, s0 in ring_edges(P):
        n, L = edge_normal(a, b)
        eastish = float(n @ east) > 0.3
        A, Bp = np.array(a), np.array(b)
        d = (Bp - A) / L
        fa, fb = f_of(A), f_of(Bp)
        ss = [0.0, L]
        if eastish and abs(fb - fa) > 1e-6:
            for cf in cuts_f:
                t = (cf - fa) / (fb - fa)
                if 0.01 < t < 0.99: ss.append(t * L)
        ss = sorted(ss)
        for i in range(len(ss) - 1):
            pa, pb = A + d * ss[i], A + d * ss[i + 1]
            fm = f_of(0.5 * (pa + pb))
            on_podium = zb is not None and zb.distance(Point(*(0.5 * (pa + pb)))) < 0.3
            for z0, z1, mat, inset, v0 in zones(fm, eastish):
                if on_podium:                       # slab face behind the podium: from the podium roof up
                    if z1 <= hp + 0.01: continue
                    z0 = max(z0, hp)
                    if mat == 'metal_dark' and inset == 0.0: mat, v0 = 'glass_hyatt', hc - p
                if inset > 0:
                    qa, qb = pa - n * inset, pb - n * inset
                    sh.quad_wall(tuple(qa), tuple(qb), z0, z1, z0, z1, 'glass_hyatt', s0 + ss[i], TILES['glass_hyatt'], v0=z0)
                    uvq = [(0, 0), (1, 0), (1, 1), (0, 1)]
                    sh.face_dir([(pa[0], pa[1], z1), (pb[0], pb[1], z1), (qb[0], qb[1], z1), (qa[0], qa[1], z1)], 'soffit_lt', uvq, (0, 0, -1))
                    sh.face_dir([(pa[0], pa[1], z0), (pb[0], pb[1], z0), (qb[0], qb[1], z0), (qa[0], qa[1], z0)], 'concrete_lt', uvq, (0, 0, 1))
                    sh.face_dir([(qa[0], qa[1], z0), (pa[0], pa[1], z0), (pa[0], pa[1], z1), (qa[0], qa[1], z1)], 'metal_dark', uvq, (d[0], d[1], 0))
                    sh.face_dir([(pb[0], pb[1], z0), (qb[0], qb[1], z0), (qb[0], qb[1], z1), (pb[0], pb[1], z1)], 'metal_dark', uvq, (-d[0], -d[1], 0))
                    for cf in np.linspace(0, 1, 5)[1:-1]:                       # colonnade columns
                        cc = pa + (pb - pa) * cf - n * 0.5
                        boxm(det, cc, d, 0.7, 0.7, (z0, z1), 'concrete_lt', (2, 2), top=False)
                else:
                    sh.quad_wall(tuple(pa), tuple(pb), z0, z1, z0, z1, mat, s0 + ss[i], TILES[mat], v0=v0)
    # roof: parapet 1.0 m, roof at H - 1.0
    ring, innerP = ring_band(P, 0.35)
    cap(sh, ring, H, 'coping', 1.0)
    for q in polys(innerP):
        for r in rings_of(q):
            for i in range(len(r)):
                sh.quad_wall(r[(i + 1) % len(r)], r[i], H - 1.0, H, H - 1.0, H, 'coping', 0, (3, 3))
        cap(sh, q, H - 1.0, 'roof_membrane', 8.0)
    # podium (dark metal panels, large glazed openings [obs l4]) to hp, membrane roof; faces against the slab are internal
    pd_ = MB('gh_podium')
    sb_ = P.boundary
    for q in podium:
        for a_, b_, s0 in ring_edges(q):
            if sb_.distance(Point(*(0.5 * (np.array(a_) + np.array(b_))))) < 0.3: continue
            pd_.quad_wall(a_, b_, 0.0, hp, 0.0, hp, 'metal_dark', s0, TILES['metal_dark'])
        cap(pd_, q, hp, 'roof_membrane', 8.0)
    if not pd_.empty():
        B.shells.append(Part('gh_podium', pd_, 'shell', 'obs', 'podium east of the slab along the south part (outline [obs]; slab set-back '
                             '%.1f m from the relief-corrected NAIP roof [obs, approx]); top 3.2 pitches [inf]' % GH_PODIUM_D, ['gh_plan_shape']))
    # penthouse (two steps), depth = slab minus 4 m each side
    core = P.buffer(-4.0)

    def band_f(f0, f1):
        a0 = o + ax * (f0 * W - W / 2); a1 = o + ax * (f1 * W - W / 2)
        return Polygon([a0 - east * 200, a1 - east * 200, a1 + east * 200, a0 + east * 200])
    ph = MB('gh_penthouse')
    pent = []
    for (f0, f1), hh in (((0.518, 0.692), 1.4 * p), ((0.615, 0.742), 0.65 * p)):
        q = largest(core.intersection(band_f(f0, f1)))
        if q.is_empty: continue
        q = orient_all(q)
        walls(ph, q, H - 1.0, H + hh, 'metal_dark', (3.0, 3.0)); cap(ph, q, H + hh, 'coping', 4.0)
        pent.append(dict(f=[f0, f1], top=round(H + hh, 2)))
    B.shells.append(Part('gh_penthouse', ph, 'shell', 'obs', 'dark stepped mechanical penthouse (photo l4 fractions; depth inf)', ['gh_facade']))
    # east-face points at fraction f (on the outline's east side)
    def east_pt(f):
        a0 = o + ax * (f * W - W / 2)
        ln = LineString([a0 - east * 80, a0 + east * 80]).intersection(P.exterior)
        pts = [np.array(g.coords[0]) for g in getattr(ln, 'geoms', [ln]) if not g.is_empty]
        return max(pts, key=lambda q: float(q @ east)) if pts else a0
    # masts (0.8 pitch, crossbar) [obs l4]
    for f in (-0.008, 0.027, 0.905, 0.961):
        q = east_pt(min(max(f, 0.001), 0.999)) - east * 0.8
        tube(det, [(q[0], q[1], H), (q[0], q[1], H + 0.8 * p)], 0.09, 6, 'steel', cap_ends=True)
        boxm(det, q, ax, 1.8, 0.12, (H + 0.8 * p - 0.1, H + 0.8 * p), 'steel', (1, 1))
    # framed bay 0.615-0.842 up to H - p: a 0.35-m frame 0.25 m proud of the glass
    for f in (0.615, 0.842):
        q = east_pt(f) + east * 0.2
        boxm(det, q, ax, 0.4, 0.4, (0.0, H - p), 'mullion', (1, 1))
    qa, qb = east_pt(0.615) + east * 0.2, east_pt(0.842) + east * 0.2
    ln = np.linspace(0, 1, 9)
    for i in range(len(ln) - 1):
        u0 = qa + (qb - qa) * ln[i]; u1 = qa + (qb - qa) * ln[i + 1]
        # follow the concave face: sample the east outline
        q0 = east_pt(0.615 + 0.227 * ln[i]) + east * 0.2; q1 = east_pt(0.615 + 0.227 * ln[i + 1]) + east * 0.2
        dd = q1 - q0; Ld = float(np.hypot(*dd))
        if Ld < 0.1: continue
        boxm(det, 0.5 * (q0 + q1), dd / Ld, Ld + 0.1, 0.4, (H - p - 0.4, H - p), 'mullion', (1, 1))
    # south end pier with the red sign [obs l4]
    q = east_pt(0.001)
    pc = q - ax * 0.9 - east * 1.5
    boxm(sh, pc, ax, 1.8, 3.0, (0.0, 0.964 * H), 'concrete_lt', (3, 3))
    boxm(det, pc - ax * 0.95, ax, 0.12, 1.2, (0.80 * H, 0.93 * H), 'sign_red', (1, 1))
    B.details[0].append(Part('gh_detail', det, 'detail', 'obs', 'colonnade columns, masts, framed-bay frame, red sign (photo l4)', ['gh_facade']))
    B.details[1].append(Part('gh_detail', det, 'detail', 'obs', 'colonnade columns, masts, framed bay, sign', ['gh_facade']))
    B.shells.insert(0, Part('gh_body', sh, 'shell', 'obs', 'curtain wall slab, podium, colonnade recess, roof, end pier', ['gh_plan_shape', 'gh_facade'],
                            dict(height=dim(round(H, 2), 'inf', 'BL-03'))))
    cm2 = MB('gh_L2'); stack_coarse(cm2, P.simplify(0.6), H, 'glass_hyatt', 'roof_membrane')
    for q in podium: stack_coarse(cm2, q.simplify(0.6), hp, 'metal_dark', 'roof_membrane')
    B.coarse.append(Part('gh_L2', cm2, 'coarse', 'inf', 'Grand Hyatt (coarse)', ['gh_footprint']))
    B.footprint_w = full; B.top = H + 1.4 * p
    B.anchors = dict(parapet_top=round(H, 3), podium=round(hp, 3), colonnade_top=round(hc, 3), pitch=round(p, 4), penthouse=pent, W=W,
                     axis_heading=mr['long_side_heading_deg'], mast_top=round(H + 0.8 * p, 3), end_pier_top=round(0.964 * H, 3))
    return B


# ================================================================================================ CAC
def cac():
    """Consolidated Administration Campus (BL-02 F, BL-03 row 2): bent bar round a court [pub]; 4 stories x 15 ft [pub],
    roof 60 ft / parapet ~64 ft [inf]; reduced window-to-wall ratio [pub] (window bands per floor, proportion inf); exterior
    louvres on the south and west faces [pub] (vertical fins, module inf)."""
    k = 'cac'
    full = clean(sfom_union('Consolidated Administration Campus'), 0.05)
    mr = LB[k]['footprint']['min_rect']
    roof, par = 60 * FT, 64 * FT
    B = Bldg(k, 'Consolidated Administration Campus', mr['centre'][0], mr['centre'][1], 'inf',
             ['cac_identity', 'cac_stories', 'cac_floor_height', 'cac_height', 'cac_form', 'cac_footprint'],
             dict(footprint=dim('SFO Museum outline', 'obs', 'BL-02 F'), roof=dim(round(roof, 3), 'inf', '4 x 15 ft'),
                  parapet_top=dim(round(par, 3), 'inf', '~64 ft (NAIP shadow 17.4-19.2 [obs])'), floors=dim(round(15 * FT, 3), 'pub', '15 ft')),
             inferred=['parapet 64 ft', 'window band 1.8 m per floor (reduced window-to-wall ratio [pub])', 'louvre fins every 1.5 m, 0.6 m deep (S / W faces)',
                       'light panel cladding (colour inf)'],
             unknown=['cladding material / colour', 'window layout'],
             not_modelled=['interior stair tower / light well', 'Phase II buildings (build status unverified)'])
    F = B.F
    P = F.poly(full)
    sh, det, d1 = MB('cac_body'), MB('cac_louvres'), MB('cac_louvres1')
    for a, b, s0 in ring_edges(P):
        n, L = edge_normal(a, b)
        sh.quad_wall(a, b, 0.0, par, 0.0, par, 'cac_wall', s0, TILES['cac_wall'])
        hdg = (math.degrees(math.atan2(n[0], n[1]))) % 360          # local n (x east, y north) -> true heading
        if 155 <= hdg <= 295 and L > 3.0:                             # south / west faces: louvre fins [pub]
            d = (np.array(b) - np.array(a)) / L
            for s in np.arange(0.75, L - 0.5, 1.5):
                c = np.array(a) + d * s + n * 0.32
                boxm(det, c, n, 0.6, 0.08, (3.0, roof), 'louvre_blade', (1, 1))
            for s in np.arange(1.5, L - 1.0, 4.5):
                c = np.array(a) + d * s + n * 0.32
                boxm(d1, c, n, 0.6, 0.15, (3.0, roof), 'louvre_blade', (1, 1))
    ring, innerP = ring_band(P, 0.3)
    cap(sh, ring, par, 'coping', 1.0)
    for q in polys(innerP):
        for r in rings_of(q):
            for i in range(len(r)):
                sh.quad_wall(r[(i + 1) % len(r)], r[i], roof, par, roof, par, 'coping', 0, (3, 3))
        cap(sh, q, roof, 'roof_membrane', 8.0)
    B.shells.append(Part('cac_body', sh, 'shell', 'inf', 'four-storey bar, window bands, parapet, membrane roof', ['cac_form', 'cac_footprint'], B.dims))
    B.details[0].append(Part('cac_louvres', det, 'detail', 'pub', 'exterior louvres S / W (module inf)', ['cac_form']))
    B.details[1].append(Part('cac_louvres', d1, 'detail', 'pub', 'exterior louvres (LOD1, every 3rd fin)', ['cac_form']))
    cm2 = MB('cac_L2'); stack_coarse(cm2, P.simplify(0.6), par, 'cac_wall', 'roof_membrane')
    B.coarse.append(Part('cac_L2', cm2, 'coarse', 'inf', 'CAC (coarse)', ['cac_footprint']))
    B.footprint_w = full; B.top = par
    B.anchors = dict(roof=round(roof, 3), parapet_top=round(par, 3), floors=[round(15 * FT * i, 3) for i in (1, 2, 3)])
    return B


# ================================================================================================ Superbay
def superbay():
    """Superbay hangar (BL-02 G, BL-03 row 4): central spine 32 m (a -14..+18 from the outline centre, along the 27.8-deg grid)
    to the DOF 135 ft [pub]; cantilever roofs WNW / ESE from the spine (root 41.15 - 1.5) to ~27 m tips [inf] at a = -80.5 /
    +84.5 (165 m overall), 8 folded bays of 17.25 m per side (138 m along the spine [obs]), fold 1.5 m at the tip [unk]
    tapering to 0 at the root [inf]; spine-end hip facets (NNE 10.3 / SSW 6.0 m, ridge a -2.5..6.3 [obs NAIP]); hangar walls on
    the SFO Museum outline (clipped 1 m inside the roof tips); two ~67-m door bays per long face [inf], door head 3 m below the
    tip [unk]; office windows in the spine end faces (6 levels [pub], window bands inf); red light at the DOF point."""
    k = 'superbay'
    full = clean(sfom_union('Super Bay Hangar Building'), 0.05)
    mr = LB[k]['footprint']['min_rect']
    c = np.array(mr['centre'], float)
    sv, tv = hdg_vec(117.83), hdg_vec(27.83)
    hs = 135 * FT; root = hs - 1.5; ht = DL.SB_TIP; fold = DL.SB_FOLD
    a0, a1, s0_, s1_ = -80.5, 84.5, -14.0, 18.0
    T = 69.0
    hip = DL.SB_HIP
    door_h = ht - DL.SB_DOOR_GAP
    B = Bldg(k, 'Superbay hangar (Bldg 1060)', c[0], c[1], 'pub',
             ['sb_identity', 'sb_height_dof', 'sb_height_pub', 'sb_interior_h', 'sb_cantilever', 'sb_layout', 'sb_roof_bays_obs', 'sb_footprint', 'sb_bays'],
             dict(spine_top=dim(round(hs, 3), 'pub', 'DOF 06-001451 135 ft, red light'), spine=dim([s0_, s1_], 'obs', 'a from the outline centre (NAIP)'),
                  roof_a=dim([a0, a1], 'obs', 'roof 165 m overall (BL-02 G)'), roof_t=dim([-T, T], 'obs', '8 x 17.25 m (138 m) vs outline 134.5 m'),
                  root=dim(round(root, 3), 'inf', 'spine top - 1.5 m (BL-03)'), tip=dim(ht, 'inf', 'photo l3 ratio, 22-32 [low]'),
                  fold=dim(fold, 'unk', 'BL-03 drawn 1.5 m at the tip'), hips=dim(hip, 'obs', 'NAIP, approx'),
                  door_head=dim(door_h, 'unk', 'tip - 3 m (BL-03)'), door_bays=dim(67.0, 'inf', 'two per face (four 747 bays [pub])')),
             inferred=['tip height 27 m', 'fold tapers to 0 at the root', 'roof thickness 1.2 m at the eaves', 'door bays 67 m, 8 leaves',
                       'spine-end facets fall to the cantilever-root level (no step at the roof corners)', 'spine end-face office windows (6 bands)',
                       'hangar walls clipped 1 m inside the roof tips (outline 2.4 m beyond the WNW tip, BL-02)'],
             unknown=['fold amplitude', 'door head / leaf division', 'interior height 120 ft position'],
             conflicts=['roof 138 m along the spine vs outline 134.5 m (1.75 m overhang per end [inf] or outline error [unk])',
                        '17.3 m roof bays [obs] vs 50 ft structural bays [pub]', '"140-ft roof" [pub] vs DOF 135 ft'],
             not_modelled=['roof ribs / skylights', 'apron-side annexes'],
             deviations=['spine-end facets: BL-03 V4 draws the spine line falling to the tip level (+28.5) at the roof ends [inf]; the model '
                         'falls to the cantilever-root level %.2f so the spine roof meets the cantilever roofs without an 11-m step (plan = BL-02)' % root])
    F = B.F
    P = F.poly(full)
    sl, tl = loc_dir(117.83), loc_dir(27.83)
    W = lambda a, t: tuple(sl * a + tl * t)                  # local XY of (a, t)

    def zroof(a, t):
        """cantilever roof top at (a, t)."""
        if s0_ < a < s1_: return hs
        if a <= s0_: f = (s0_ - a) / (s0_ - a0)
        else: f = (a - s1_) / (a1 - s1_)
        base = root + (ht - root) * f
        ph = ((t + T) / 17.25) % 1.0                         # 0 at bay lines (valleys), 0.5 at bay centres (ridges)
        tri = 1 - abs(ph - 0.5) * 2
        return base + fold * f * tri
    sh = MB('sb_roof')
    # folded cantilever roofs: per side, per half-bay facet, sampled along a every ~8.3 m
    tt = np.linspace(-T, T, 17)
    for side in (-1, 1):
        aa = np.linspace(s0_, a0, 9) if side < 0 else np.linspace(s1_, a1, 9)
        for i in range(16):
            for j in range(8):
                ta, tb = tt[i], tt[i + 1]
                pa, pb = aa[j], aa[j + 1]
                q = [(pa, ta), (pb, ta), (pb, tb), (pa, tb)]
                pts = [(*W(a, t), zroof(a, t)) for a, t in q]
                uv = [(a / 6.0, t / 6.0) for a, t in q]
                # orientation: face up
                n = np.cross(np.array(pts[1]) - np.array(pts[0]), np.array(pts[2]) - np.array(pts[0]))
                if n[2] < 0: pts, uv = pts[::-1], uv[::-1]
                sh.face(pts[:3], 'hangar_roof', uv[:3]); sh.face([pts[0], pts[2], pts[3]], 'hangar_roof', [uv[0], uv[2], uv[3]])
        # eave fascia (1.2 m) along the tip and the roof end edges, soffit beyond the walls
        at = a0 if side < 0 else a1
        for i in range(16):
            ta, tb = tt[i], tt[i + 1]
            p1 = (*W(at, ta), zroof(at, ta)); p2 = (*W(at, tb), zroof(at, tb))
            f = [(p1[0], p1[1], p1[2] - 1.2), (p2[0], p2[1], p2[2] - 1.2), p2, p1]
            n = np.cross(np.array(f[1]) - np.array(f[0]), np.array(f[3]) - np.array(f[0]))
            out = np.array(sl) * side
            if n[:2] @ out < 0: f = f[::-1]
            sh.face(f, 'fascia', [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
        for t_end in (-T, T):
            for j in range(8):
                pa, pb = aa[j], aa[j + 1]
                p1 = (*W(pa, t_end), zroof(pa, t_end)); p2 = (*W(pb, t_end), zroof(pb, t_end))
                f = [(p1[0], p1[1], p1[2] - 1.2), (p2[0], p2[1], p2[2] - 1.2), p2, p1]
                n = np.cross(np.array(f[1]) - np.array(f[0]), np.array(f[3]) - np.array(f[0]))
                if n[:2] @ (np.array(tl) * np.sign(t_end)) < 0: f = f[::-1]
                sh.face(f, 'fascia', [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
        # soffit: the folded roof 1.2 m lower, facing down (visible beyond the walls at the tips and roof ends)
        for i in range(16):
            for j in range(8):
                ta, tb = tt[i], tt[i + 1]; pa, pb = aa[j], aa[j + 1]
                q = [(pa, ta), (pb, ta), (pb, tb), (pa, tb)]
                pts = [(*W(a, t), zroof(a, t) - 1.2) for a, t in q]
                uv = [(a / 6.0, t / 6.0) for a, t in q]
                sh.face_dir(pts[:3], 'soffit', uv[:3], (0, 0, -1)); sh.face_dir([pts[0], pts[2], pts[3]], 'soffit', [uv[0], uv[2], uv[3]], (0, 0, -1))
    # spine roof with hipped ends: ridge a -2.5..6.3 at hs, corners (s0 / s1, +-T) at the root level
    ra, rb = hip['ridge_a']
    tn, ts_ = T - hip['nne'], -(T - hip['ssw'])          # +t = NNE
    spine_top = [((s0_, ts_), (s1_, ts_), (s1_, tn), (s0_, tn))]
    corners = {'n': ((s0_, T), (s1_, T), (rb, tn), (ra, tn)), 's': ((s1_, -T), (s0_, -T), (ra, ts_), (rb, ts_))}

    def zsp(a, t):
        return hs if ts_ <= t <= tn else root
    # flat spine top between the hip ridge lines (between ts_ and tn)
    q = [(s0_, ts_), (s1_, ts_), (s1_, tn), (s0_, tn)]
    pts = [(*W(a, t), hs) for a, t in q]
    if np.cross(np.array(pts[1]) - np.array(pts[0]), np.array(pts[2]) - np.array(pts[0]))[2] < 0: pts = pts[::-1]
    sh.face(pts, 'spine_roof', [(p[0] / 6, p[1] / 6) for p in pts])
    for end, tr in (('n', tn), ('s', ts_)):
        te = T if end == 'n' else -T
        # end facet (trapezoid) + two side facets (triangles) from the ridge segment to the end edge / sides
        facets = [[(s0_, te, root), (s1_, te, root), (rb, tr, hs), (ra, tr, hs)],
                  [(s1_, te, root), (s1_, tr, hs), (rb, tr, hs)],
                  [(s0_, te, root), (ra, tr, hs), (s0_, tr, hs)]]
        for fct in facets:
            pts = [(*W(a, t), z) for a, t, z in fct]
            n = np.cross(np.array(pts[1]) - np.array(pts[0]), np.array(pts[2]) - np.array(pts[0]))
            if n[2] < 0: pts = pts[::-1]
            sh.face(pts, 'spine_roof', [(p[0] / 6, p[1] / 6) for p in pts])
    # spine side walls above the cantilever roots (root -> hs) between the hips, + their triangular ends
    for a_, sg in ((s0_, -1), (s1_, 1)):
        q = [(*W(a_, ts_), root), (*W(a_, tn), root), (*W(a_, tn), hs), (*W(a_, ts_), hs)]
        n = np.cross(np.array(q[1]) - np.array(q[0]), np.array(q[3]) - np.array(q[0]))
        if n[:2] @ (np.array(sl) * sg) < 0: q = q[::-1]
        sh.face(q, 'spine_wall', [(0, 0), (1, 0), (1, 0.5), (0, 0.5)])
    # hangar walls: outline clipped 1 m inside the roof tips and the roof ends; top follows the roof (minus 1.2 m)
    roof_rect = Polygon([W(a0 + 1.0, -T + 1.0), W(a1 - 1.0, -T + 1.0), W(a1 - 1.0, T - 1.0), W(a0 + 1.0, T - 1.0)])
    WP = orient_all(P.intersection(roof_rect).buffer(0))
    WP = largest(WP)
    inv = lambda X, Y: (float(np.array([X, Y]) @ sl), float(np.array([X, Y]) @ tl))
    wl, dl = MB('sb_walls'), MB('sb_doors')
    doors = []
    for a, b, s0 in ring_edges(WP):
        n, L = edge_normal(a, b)
        ua, ta_ = inv(*a); ub, tb_ = inv(*b)
        za = zroof(ua, ta_) - 1.2; zb = zroof(ub, tb_) - 1.2
        longface = abs(float(n @ sl)) > 0.8
        if longface and L > 100:
            # door face: two door bays of 67 m centred on the face, head at door_h [inf / unk]
            d = (np.array(b) - np.array(a)) / L
            tm = 0.5 * (ta_ + tb_)
            s_mid = L / 2 + (0.0 - tm) * (1 if (tb_ - ta_) > 0 else -1)      # face centre at t = 0
            s_mid = L / 2
            holes = []
            for kk in (-1, 0):
                sA = s_mid + kk * 67.0 + 0.5; sB = sA + 66.0
                holes.append((sA, sB, 0.0, door_h))
                doors.append((sA, sB))
                # door leaves recessed 0.4 m, 8 leaves (joints in the texture: tile 8.375 m)
                pA = np.array(a) + d * sA - n * 0.4; pB = np.array(a) + d * sB - n * 0.4
                dl.quad_wall(tuple(pA), tuple(pB), 0.0, door_h, 0.0, door_h, 'hangar_door', 0.0, (66.0 / 8, door_h))
                dl.face([(*(np.array(a) + d * sA), door_h), (*(np.array(a) + d * sB), door_h), (*pB, door_h), (*pA, door_h)][::-1], 'soffit', [(0, 0), (1, 0), (1, 1), (0, 1)])
                dl.quad_wall(tuple(np.array(a) + d * sA), tuple(pA), 0.0, door_h, 0.0, door_h, 'hangar_wall', 0, (2, 2))
                dl.quad_wall(tuple(pB), tuple(np.array(a) + d * sB), 0.0, door_h, 0.0, door_h, 'hangar_wall', 0, (2, 2))
            # wall with the door holes, top following the roof: split into the part below door_h and a sloped top quad
            holed_wall(wl, a, b, 0.0, door_h, holes, 'hangar_wall', s0, TILES['hangar_wall'])
            # wall above the doors up to the folded soffit: one quad per quarter bay (the top follows the folds)
            m_ = max(1, int(math.ceil(L / (17.25 / 4))))
            for i in range(m_):
                p0 = np.array(a) + (np.array(b) - np.array(a)) * i / m_; p1 = np.array(a) + (np.array(b) - np.array(a)) * (i + 1) / m_
                u0, t0 = inv(*p0); u1, t1 = inv(*p1)
                z0, z1 = zroof(u0, t0) - 1.2, zroof(u1, t1) - 1.2
                sa_, sb_ = s0 + L * i / m_, s0 + L * (i + 1) / m_
                wl.face([(p0[0], p0[1], door_h), (p1[0], p1[1], door_h), (p1[0], p1[1], z1), (p0[0], p0[1], z0)], 'hangar_wall',
                        [(sa_ / 2, door_h / 2), (sb_ / 2, door_h / 2), (sb_ / 2, z1 / 2), (sa_ / 2, z0 / 2)])
        else:
            # end walls (NNE / SSW): sample the roof line every ~8 m
            m_ = max(1, int(L / 8.0))
            for i in range(m_):
                p0 = np.array(a) + (np.array(b) - np.array(a)) * i / m_; p1 = np.array(a) + (np.array(b) - np.array(a)) * (i + 1) / m_
                u0, t0 = inv(*p0); u1, t1 = inv(*p1)
                z0, z1 = zroof(u0, t0) - 1.2, zroof(u1, t1) - 1.2
                if s0_ - 0.5 <= u0 <= s1_ + 0.5 and s0_ - 0.5 <= u1 <= s1_ + 0.5:
                    z0 = z1 = root - 1.2
                wl.face([(p0[0], p0[1], 0.0), (p1[0], p1[1], 0.0), (p1[0], p1[1], z1), (p0[0], p0[1], z0)],
                        'spine_wall' if (s0_ <= 0.5 * (u0 + u1) <= s1_) else 'hangar_wall',
                        [(0, 0), (1, 0), (1, z1 / 3.6), (0, z0 / 3.6)] if (s0_ <= 0.5 * (u0 + u1) <= s1_) else
                        [(s0 / 2 + i * L / m_ / 2, 0), (s0 / 2 + (i + 1) * L / m_ / 2, 0), (s0 / 2 + (i + 1) * L / m_ / 2, z1 / 2), (s0 / 2 + i * L / m_ / 2, z0 / 2)])
    # red obstruction light at the DOF point
    d0 = LB[k]['dof'][0]
    rl = np.array(F.L(*d0['world']))
    ua, tb_ = inv(*rl)
    ua = min(max(ua, s0_ + 0.5), s1_ - 0.5)
    rlp = np.array(W(ua, tb_))
    boxm(dl, rlp, (1, 0), 0.4, 0.4, (hs, hs + 0.5), 'sign_red', (1, 1))
    B.shells.append(Part('sb_roof', sh, 'shell', 'pub', 'folded cantilever roofs, spine roof with hipped ends', ['sb_layout', 'sb_roof_bays_obs', 'sb_height_dof']))
    B.shells.append(Part('sb_walls', wl, 'shell', 'obs', 'hangar walls on the outline, door openings', ['sb_footprint', 'sb_bays']))
    B.details[0].append(Part('sb_doors', dl, 'detail', 'inf', 'door leaves (8 per bay), red light', ['sb_bays']))
    B.details[1].append(Part('sb_doors', dl, 'detail', 'inf', 'door leaves, red light', ['sb_bays']))
    cm2 = MB('sb_L2')
    walls(cm2, WP.simplify(0.8), 0.0, ht - 1.2, 'hangar_wall', (2, 2))
    for side in (-1, 1):
        aa = (s0_, a0) if side < 0 else (s1_, a1)
        q = [(*W(aa[0], -T), root), (*W(aa[1], -T), ht), (*W(aa[1], T), ht), (*W(aa[0], T), root)]
        n = np.cross(np.array(q[1]) - np.array(q[0]), np.array(q[2]) - np.array(q[0]))
        if n[2] < 0: q = q[::-1]
        cm2.face(q, 'hangar_roof', [(0, 0), (1, 0), (1, 1), (0, 1)])
    q = [(*W(s0_, -T), hs), (*W(s1_, -T), hs), (*W(s1_, T), hs), (*W(s0_, T), hs)]
    if np.cross(np.array(q[1]) - np.array(q[0]), np.array(q[2]) - np.array(q[0]))[2] < 0: q = q[::-1]
    cm2.face(q, 'spine_roof', [(0, 0), (1, 0), (1, 1), (0, 1)])
    B.coarse.append(Part('sb_L2', cm2, 'coarse', 'pub', 'Superbay (coarse)', ['sb_layout']))
    B.footprint_w = F.wpoly(Polygon([W(a0, -T), W(a1, -T), W(a1, T), W(a0, T)])); B.top = hs + 0.5
    B.anchors = dict(spine_top=round(hs, 3), root=round(root, 3), tip=ht, fold=fold, a=[a0, s0_, s1_, a1], t=[-T, T], hips=hip, door_head=door_h,
                     doors_s=[[round(x, 2) for x in d] for d in doors], red_light_local=[round(float(rlp[0]), 2), round(float(rlp[1]), 2)],
                     walls_area=round(WP.area, 1))
    return B


# ================================================================================================ United MOC
MOC_LEAN = 0.315        # North-Field NAIP relief lean, m east per m of height (0.30-0.33 from shadows at the CAC / LTP 1,
#                         docs/drawings/buildings/README.md 'north' model) [inf]: the imaged roofs are shifted back by it
BARREL_EAVE, BARREL_RISE = 14.0, 10.0    # barrel-vault hangars: no height source (no DOF) -> placeholders [unk]


def moc():
    """United MOC (BL-02 D, BL-03 row 4): the large hangar block from its IMAGED roof corners (relief NOT removed on the
    sheets) shifted back west by the North-Field lean x its height [inf]; three parts along the block (steps at z -1945 /
    -1885 [obs]) at the DOF heights inside them [pub points, extents inf]; the two barrel-vault hangars south of it (imaged
    156 x 90 m [obs]) at placeholder heights [unk]."""
    k = 'united_moc'
    L = MOC['moc_large_hangar']; Bh = MOC['moc_barrel_hangars']
    mr = L['min_rect']; W_ = mr['length_m']
    hs = {d['oas']: d for d in L['dof']}
    hmean = float(np.mean([d['agl_m'] for d in L['dof']]))
    shift = np.array([-MOC_LEAN * hmean, 0.0])
    corners = np.array(L['corners_imaged'], float) + shift
    c = np.array(mr['centre'], float) + shift
    B = Bldg(k, 'United Airlines MOC: large hangar block + barrel-vault hangars', c[0], c[1], 'obs',
             ['moc_identity', 'moc_large_hangar', 'moc_large_hangar_h', 'moc_barrel_hangars', 'moc_other_dof'],
             dict(large_plan=dim('imaged roof corners shifted %.1f m west (lean %.3f x %.1f m)' % (-shift[0], MOC_LEAN, hmean), 'inf', 'BL-02 D (imaged, +-3 m)'),
                  parts=dim({o: d['agl_m'] for o, d in hs.items()}, 'pub', 'DOF 1A points; part extents inf'),
                  barrel=dim(dict(eave=BARREL_EAVE, crown=BARREL_EAVE + BARREL_RISE), 'unk', 'no DOF / no source: placeholders')),
             inferred=['footprint = imaged roof - North-Field lean x mean DOF height (%.1f m)' % hmean, 'part extents between the imaged roof steps',
                       'corrugated metal walls, flat roofs, 1-m parapet', 'barrel hangars: two vaults spanning N-S (shading), axes E-W'],
             unknown=['section heights between the DOF points', 'barrel hangar heights (placeholders %.0f / %.0f m)' % (BARREL_EAVE, BARREL_EAVE + BARREL_RISE),
                      'hangar doors (positions / sizes)'],
             not_modelled=['hangar doors (not verified)', 'other MOC buildings (DOF 107 / 92 / 79 / 75 / 74 / 70 ft, not identified)'])
    F = B.F
    ax = hdg_vec(mr['long_side_heading_deg'])
    u_of = lambda p: float((np.asarray(p, float) - c) @ ax) + W_ / 2
    big = Polygon(corners)
    ua = u_of((c[0], -1945.0)); ub = u_of((c[0], -1885.0))
    parts = [(0.0, ua, hs['06-035290']), (ua, ub, hs['06-035289']), (ub, W_ + 5, hs['06-035288'])]
    sh = MB('moc_large')
    out_parts = []
    bn = np.array([ax[1], -ax[0]])
    for u0, u1, d in parts:
        strip = Polygon([c + ax * (u0 - W_ / 2 - (5 if u0 == 0 else 0)) - bn * 200, c + ax * (u1 - W_ / 2) - bn * 200,
                         c + ax * (u1 - W_ / 2) + bn * 200, c + ax * (u0 - W_ / 2 - (5 if u0 == 0 else 0)) + bn * 200])
        q = orient_all(big.intersection(strip))
        if q.is_empty: continue
        Q = F.poly(q)
        h = d['agl_m']
        walls(sh, Q, 0.0, h, 'moc_wall', TILES['moc_wall'])
        ring, inner = ring_band(Q, 0.4)
        cap(sh, ring, h, 'coping', 1.0)
        for qq in polys(inner):
            for r in rings_of(qq):
                for i in range(len(r)):
                    sh.quad_wall(r[(i + 1) % len(r)], r[i], h - 1.0, h, h - 1.0, h, 'coping', 0, (3, 3))
            cap(sh, qq, h - 1.0, 'moc_roof', 8.0)
        out_parts.append(dict(oas=d['oas'], top=d['agl_m'], u=[round(u0, 1), round(min(u1, W_), 1)], area=round(q.area, 1)))
    B.shells.append(Part('moc_large', sh, 'shell', 'pub', 'large hangar block: three parts at the DOF heights', ['moc_large_hangar', 'moc_large_hangar_h']))
    # barrel-vault hangars: split the imaged rectangle into a north and a south bay (vault axis E-W, arch spanning N-S)
    hb = BARREL_EAVE + BARREL_RISE
    bc = np.array(Bh['corners_imaged'], float) + np.array([-MOC_LEAN * (BARREL_EAVE + 0.6 * BARREL_RISE), 0.0])
    bb = Polygon(bc)
    zc = bb.centroid.y
    br = MB('moc_barrel')
    vaults = []
    for zA, zB in ((bb.bounds[1], zc), (zc, bb.bounds[3])):
        q = orient_all(bb.intersection(shapely.box(bb.bounds[0] - 5, zA, bb.bounds[2] + 5, zB)))
        Q = F.poly(q)
        mrq = np.array(Q.minimum_rotated_rectangle.exterior.coords)[:4]
        e0, e1 = mrq[1] - mrq[0], mrq[2] - mrq[1]
        if abs(e0[0]) < abs(e1[0]): mrq = np.roll(mrq, -1, axis=0); e0, e1 = mrq[1] - mrq[0], mrq[2] - mrq[1]
        Lx, Wy = float(np.hypot(*e0)), float(np.hypot(*e1)); ux, uy = e0 / Lx, e1 / Wy
        o0 = mrq[0]
        nseg = 12
        prof = [(Wy * i / nseg, BARREL_EAVE + BARREL_RISE * math.sin(math.pi * i / nseg)) for i in range(nseg + 1)]
        for i in range(nseg):
            (y0, z0), (y1, z1) = prof[i], prof[i + 1]
            qd = [(*(o0 + uy * y0), z0), (*(o0 + ux * Lx + uy * y0), z0), (*(o0 + ux * Lx + uy * y1), z1), (*(o0 + uy * y1), z1)]
            n = np.cross(np.array(qd[1]) - np.array(qd[0]), np.array(qd[2]) - np.array(qd[0]))
            if n[2] < 0: qd = qd[::-1]
            br.face(qd, 'barrel_roof', [(0, y0 / 4), (Lx / 4, y0 / 4), (Lx / 4, y1 / 4), (0, y1 / 4)], smooth=True, grp='barrel%d' % len(vaults))
        # long walls (N / S) to the eave, gable walls (E / W) up to the arch
        for (pa, pb) in ((o0, o0 + ux * Lx), (o0 + ux * Lx + uy * Wy, o0 + uy * Wy)):
            n_, _ = edge_normal(pa, pb)
            if Q.contains(Point(*(0.5 * (pa + pb) + n_ * 1.0))): pa, pb = pb, pa
            br.quad_wall(tuple(pa), tuple(pb), 0.0, BARREL_EAVE, 0.0, BARREL_EAVE, 'moc_wall', 0, TILES['moc_wall'])
        for xg in (0.0, Lx):
            pts = [(*(o0 + ux * xg + uy * y), z) for y, z in prof] + [(*(o0 + ux * xg + uy * Wy), 0.0), (*(o0 + ux * xg), 0.0)]
            ring2 = [(p[0], p[1]) for p in pts]
            # fan the gable from the bottom centre
            cb = (*(o0 + ux * xg + uy * Wy / 2), 0.0)
            for i in range(nseg):
                tri = [cb, pts[i], pts[i + 1]]
                n = np.cross(np.array(tri[1]) - np.array(tri[0]), np.array(tri[2]) - np.array(tri[0]))
                outd = -ux if xg == 0.0 else ux
                if n[:2] @ outd < 0: tri = tri[::-1]
                br.face(tri, 'moc_wall', [(0, 0), (1, 0), (1, 1)])
            for tri in ([cb, pts[0], (*(o0 + ux * xg), 0.0)], [cb, (*(o0 + ux * xg + uy * Wy), 0.0), pts[nseg]]):
                n = np.cross(np.array(tri[1]) - np.array(tri[0]), np.array(tri[2]) - np.array(tri[0]))
                outd = -ux if xg == 0.0 else ux
                if n[:2] @ outd < 0: tri = tri[::-1]
                br.face(tri, 'moc_wall', [(0, 0), (1, 0), (1, 1)])
        vaults.append(dict(L=round(Lx, 1), span=round(Wy, 1), eave=BARREL_EAVE, crown=hb))
    B.shells.append(Part('moc_barrel', br, 'shell', 'obs', 'two barrel-vault hangars (plan obs imaged; heights unk placeholders)', ['moc_barrel_hangars']))
    cm2 = MB('moc_L2')
    for u0, u1, d in parts:
        strip = Polygon([c + ax * (u0 - W_ / 2 - (5 if u0 == 0 else 0)) - bn * 200, c + ax * (u1 - W_ / 2) - bn * 200,
                         c + ax * (u1 - W_ / 2) + bn * 200, c + ax * (u0 - W_ / 2 - (5 if u0 == 0 else 0)) + bn * 200])
        q = orient_all(big.intersection(strip))
        if not q.is_empty: stack_coarse(cm2, F.poly(q), d['agl_m'], 'moc_wall', 'moc_roof')
    stack_coarse(cm2, F.poly(orient_all(bb)), BARREL_EAVE + BARREL_RISE * 0.7, 'moc_wall', 'barrel_roof')
    B.coarse.append(Part('moc_L2', cm2, 'coarse', 'obs', 'MOC (coarse)', ['moc_large_hangar']))
    B.footprint_w = unary_union([big, bb]); B.top = max(d['agl_m'] for d in L['dof'])
    B.anchors = dict(shift_large=[round(float(shift[0]), 2), 0.0], parts=out_parts, barrel_shift=round(-MOC_LEAN * (BARREL_EAVE + 0.6 * BARREL_RISE), 2),
                     vaults=vaults, imaged_corners=L['corners_imaged'])
    return B


# ================================================================================================ assembly
def build_all(only=None):
    """-> (buildings, airtrain tiles, airtrain info, level field)."""
    fns = [('central_garage', central_garage), ('garage_a', lambda: garage_ag('garage_a')), ('garage_g', lambda: garage_ag('garage_g')),
           ('ltp_garage_1', ltp1), ('ltp_garage_2', ltp2), ('rental_car_center', rcc), ('grand_hyatt', hyatt), ('cac', cac),
           ('superbay', superbay), ('united_moc', moc)]
    out = []
    for k, f in fns:
        if only and k not in only and 'airtrain' not in only: continue
        if only and k not in only and k not in ('garage_a', 'garage_g'): continue
        out.append(f())
    by = {b.key: b for b in out}
    gA = by.get('garage_a') or garage_ag('garage_a')
    gG = by.get('garage_g') or garage_ag('garage_g')
    clip = [AT.ITB_OUTLINE, gA.body_w]
    outlines = [b.footprint_w for b in out if b.footprint_w is not None] + [gA.body_w, gG.body_w, AT.ITB_OUTLINE] + \
               [Polygon(r).buffer(0) for r in D.complex_rings()] + [sfom_union('Central Parking Garage'), sfom_union('Rental Car Center')]
    tiles, info, lev = ([], {}, None)
    if not only or 'airtrain' in only:
        tiles, info, lev = AT.build(clip, outlines, Bldg, Part, dim, station_exclude={'GAR_G': gG.body_w})
    if only:
        out = [b for b in out if b.key in only]
    return out, tiles, info, lev
