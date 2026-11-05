"""Geometry of the 3-D landside asset (data/buildings3d/landside.glb): Central Parking Garage (with its void), International
Garages A and G (body, helix drum, core cylinder, rooftop box), Long-Term Parking Garages 1 / 2, Rental Car Center, Grand
Hyatt, Consolidated Administration Campus, Superbay hangar and the United MOC large hangar. The AirTrain guideway and
stations are in landside_airtrain.py, the parking-deck stall grids and parked cars in landside_cars.py.

Pure numpy / shapely (no bpy): tools/blender/build_landside.py turns the parts into Blender objects; verify_landside.py
measures the exported glb against the same functions.

THE REFERENCE IS THE 2-D DRAWING CODE (sheets BL-01..03, docs/drawings/buildings/README.md), imported here, not copied:
  tools/buildings/draw_landside.py  GAR / ggeom() (Garage A / G body end Lb, drum circle fits, station u / b, rooftop box,
                                    GAR_CORE_D), SB_TIP / SB_FOLD / SB_DOOR_GAP / SB_HIP (Superbay), GH_P / GH_POD / GH_COL
                                    and the l4 fractions of hyatt_elev() (Grand Hyatt east face), RCC_N / RCC_S /
                                    RCC_TOWER_D (RCC west face, station tower), the level placeholders of sheet_elev()
  tools/buildings/draw_data.py      spec_landside.json (LV), landside_naip_measurements.json (LANDM: min rectangles, DOF
                                    points, MOC imaged corners), SFO Museum outlines (data/sfo_airport.json)
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
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_landside as DL  # noqa: E402
from draw_lib import FT, hdg_vec  # noqa: E402
from landside_mesh import (MB, Frame, boxm, cap, clean, cyl, orient_all, polys, rings_of, tube,  # noqa: E402,F401
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
PIER_W = 0.8               # facade pier width [inf]
PIER_DX = {'cg': 9.0, 'gar': 16.2, 'drum': 6.0, 'ltp1': 9.0, 'ltp2': 9.1, 'rcc': 9.0}   # pier spacing [inf] (LTP2 9.1:
#                            the exposed frame of photo l2 / spec ltp2_facade, bay size inf)
SCREEN_OUT, SCREEN_GAP = 0.15, 0.35   # perforated screen: 0.15 m proud of the facade, 0.35 m dark gap above / below [inf]
FT12 = 12 * FT


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

    def __init__(self, key, name, ox, oz, src, spec, dims, inferred=(), unknown=(), conflicts=(), not_modelled=()):
        self.key, self.name, self.F = key, name, Frame(round(ox, 1), round(oz, 1))
        self.src, self.spec, self.dims = src, list(spec), dims
        self.inferred, self.unknown, self.conflicts, self.not_modelled = list(inferred), list(unknown), list(conflicts), list(not_modelled)
        self.shells, self.details, self.coarse, self.decks = [], {0: [], 1: []}, [], []
        self.anchors = {}

    def extras(self):
        return dict(src=self.src, feature=self.name, spec=self.spec, dims=self.dims, origin_world_xz=[self.F.ox, self.F.oz],
                    inferred=self.inferred, unknown=self.unknown, conflicts=self.conflicts, not_modelled=self.not_modelled,
                    anchors=self.anchors)


# ------------------------------------------------------------------------------------------------ geometry helpers
def sfom_union(name):
    return unary_union([Polygon(p[0], p[1:]).buffer(0) for p in D.sfom(name, 'structures')])


def struct_poly(sid):
    f = next(f for f in D.AIR['structures'] if f['id'] == sid)
    return unary_union([Polygon(p[0], p[1:]).buffer(0) for p in f['polys']])


RAIL = struct_poly(1779914099)                 # SFO Museum 'AirTrain Rail' (src sfo) [obs]


def largest(g):
    ps = polys(g)
    return max(ps, key=lambda p: p.area) if ps else Polygon()


def mr_frame(k):
    """minimum rectangle of the outline (landside_naip_measurements.json): centre, long axis a (world xz), across b
    (left of a), length, width."""
    mr = LB[k]['footprint']['min_rect']
    c = np.array(mr['centre'], float); a = hdg_vec(mr['long_side_heading_deg']); b = np.array([a[1], -a[0]])
    return c, a, b, mr['length_m'], mr['width_m']


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


def holed_wall(mb, a, b, z0, z1, holes, mat, s0=0.0, tile=(3.0, 3.0)):
    """vertical wall a -> b (outward = right) from z0 to z1 minus rectangular holes [(s_a, s_b, h0, h1)] (s along a -> b)."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if not holes:
        mb.quad_wall(a, b, z0, z1, z0, z1, mat, s0, tile); return
    ss = sorted({0.0, L} | {min(max(h[0], 0.0), L) for h in holes} | {min(max(h[1], 0.0), L) for h in holes})
    zz = sorted({z0, z1} | {min(max(h[2], z0), z1) for h in holes} | {min(max(h[3], z0), z1) for h in holes})
    d = (np.array(b, float) - np.array(a, float)) / L
    for i in range(len(ss) - 1):
        for j in range(len(zz) - 1):
            sm, zm = 0.5 * (ss[i] + ss[i + 1]), 0.5 * (zz[j] + zz[j + 1])
            if any(h[0] < sm < h[1] and h[2] < zm < h[3] for h in holes): continue
            pa = tuple(np.array(a) + d * ss[i]); pb = tuple(np.array(a) + d * ss[i + 1])
            mb.quad_wall(pa, pb, zz[j], zz[j + 1], zz[j], zz[j + 1], mat, s0 + ss[i], tile)


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


def garage_facade(mb, P, bands, style, tiles, mats, recess=RECESS, gdetail=None):
    """facades of an open parking structure on the local polygon P (holes = inner courts / voids).
    style(a, b) -> dict(kind='open' | 'screen' | 'solid', pier_dx, solid=mat key, holes=[(s_a, s_b, h0, h1)]) per ring edge.
    Solid bands are walls at the facade plane; open bands are recessed: a dark interior wall `recess` inside, slab soffit /
    sill caps between, piers every pier_dx; 'screen' edges add perforated panels 0.15 m proud of the facade (garage_ag_facade).
    gdetail: MB for the screens / piers (else mb)."""
    gd = gdetail if gdetail is not None else mb
    top = bands[-1][1]
    open_quads = []
    edges = ring_edges(P)
    for a, b, s0 in edges:
        st = style(a, b)
        n, L = edge_normal(a, b)
        A, B = np.array(a), np.array(b)
        if st['kind'] == 'solid':
            holed_wall(mb, a, b, 0.0, top, st.get('holes', []), st['solid'], s0, tiles[st['solid']])
            continue
        for z0, z1, kind in bands:
            if kind == 'solid':
                holed_wall(mb, a, b, z0, z1, [], st['solid'], s0, tiles[st['solid']])
        q = Polygon([A, B, B - n * recess, A - n * recess])
        if q.is_valid and q.area > 1e-3:
            open_quads.append(q)
        # piers (front + two sides), every pier_dx, 2 m clear of the edge ends
        dx = st['pier_dx']
        if L > 4.0:
            k = max(1, int(round((L - 4.0) / dx)))
            ss = np.linspace(2.0, L - 2.0, k + 1) if k >= 1 else []
            d = (B - A) / L
            for s in ss:
                c = A + d * s
                p0, p1 = c - d * PIER_W / 2, c + d * PIER_W / 2
                q0, q1 = p0 - n * recess, p1 - n * recess
                for z0, z1, kind in bands:
                    if kind != 'open': continue
                    gd.quad_wall(tuple(p0), tuple(p1), z0, z1, z0, z1, st['solid'], s0 + s - PIER_W / 2, tiles[st['solid']])
                    gd.quad_wall(tuple(p1), tuple(q1), z0, z1, z0, z1, st['solid'], 0.0, tiles[st['solid']])
                    gd.quad_wall(tuple(q0), tuple(p0), z0, z1, z0, z1, st['solid'], 0.0, tiles[st['solid']])
            if st['kind'] == 'screen':
                cuts = [0.0] + [s for s in ss] + [L]
                for i in range(len(cuts) - 1):
                    sa = cuts[i] + (PIER_W / 2 if i > 0 else 0.15); sb = cuts[i + 1] - (PIER_W / 2 if i < len(cuts) - 2 else 0.15)
                    if sb - sa < 0.5: continue
                    pa = A + d * sa + n * SCREEN_OUT; pb = A + d * sb + n * SCREEN_OUT
                    fa, fb = A + d * sa, A + d * sb
                    for z0, z1, kind in bands:
                        if kind != 'open': continue
                        za, zb = z0 + SCREEN_GAP, z1 - SCREEN_GAP
                        if zb - za < 0.6: continue
                        gd.quad_wall(tuple(pa), tuple(pb), za, zb, za, zb, 'screen', s0 + sa, tiles['screen'], v0=za)
                        gd.face([(pa[0], pa[1], zb), (pb[0], pb[1], zb), (fb[0], fb[1], zb), (fa[0], fa[1], zb)], 'screen_edge',
                                [(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
                        gd.face([(fa[0], fa[1], za), (fb[0], fb[1], za), (pb[0], pb[1], za), (pa[0], pa[1], za)], 'screen_edge',
                                [(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
                        gd.quad_wall(tuple(fa), tuple(pa), za, zb, za, zb, 'screen_edge', 0.0, (1.0, 1.0))
                        gd.quad_wall(tuple(pb), tuple(fb), za, zb, za, zb, 'screen_edge', 0.0, (1.0, 1.0))
    if not open_quads:
        return
    zone = orient_all(unary_union(open_quads).intersection(P).buffer(0))
    bnd = P.boundary
    for z0, z1, kind in bands:
        if kind != 'open': continue
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
    from landside_mesh import ring_band
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


def deck_uvf(F, heading, origin_world):
    """UV of the parking-deck stall texture (landside_tex.deck_stalls: u = 4 stalls of 2.6 m along the car rows, v = one
    18.6-m module: 5.5 stall + 7.6 aisle + 5.5 stall), in the local frame of building F; rows along `heading` (world, deg)."""
    r = np.array([math.sin(math.radians(heading)), math.cos(math.radians(heading))])      # local XY row direction
    p = np.array([r[1], -r[0]])
    o = np.array(F.L(*origin_world))

    def f(x, y):
        d = np.array([x, y]) - o
        return (float(d @ r) / 10.4, float(d @ p) / 18.6)
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


def anchors_dof(B, k):
    return [dict(oas=d['oas'], type=d['type'], agl_m=d['agl_m'], agl_ft=d['agl_ft'], acc=d['acc'], world=d['world'])
            for d in LB[k]['dof']]


def fit_circle_seed(ring, seed, rmax=24.0, tol=1.5, min_pts=5):
    """circle fitted to the outline vertices around a seed (iteratively dropping residuals > tol); None if < min_pts."""
    s = np.array(seed, float); R = None
    for it in range(8):
        d = np.hypot(*(ring - s).T); sel = ring[d < rmax]
        if R is not None:
            sel = sel[np.abs(np.hypot(*(sel - s).T) - R) < tol]
        if len(sel) < 3: return None
        A = np.c_[2 * sel[:, 0], 2 * sel[:, 1], np.ones(len(sel))]
        q = np.linalg.lstsq(A, sel[:, 0] ** 2 + sel[:, 1] ** 2, rcond=None)[0]
        s = q[:2]; R = math.sqrt(q[2] + s[0] ** 2 + s[1] ** 2)
    res = np.abs(np.hypot(*(sel - s).T) - R)
    if len(sel) < min_pts or res.max() > tol: return None
    return dict(c=[round(float(s[0]), 2), round(float(s[1]), 2)], R=round(R, 2), n=int(len(sel)), res_max=round(float(res.max()), 2))


def on_circle(a, b, F, circ, tol=1.6):
    """edge a -> b (local) lies on a fitted circle (world centre)."""
    if not circ: return False
    c = np.array(F.L(*circ['c']))
    return all(abs(math.hypot(p[0] - c[0], p[1] - c[1]) - circ['R']) < tol for p in (a, b, (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))))


def parking_structure(B, P, top, deck, slabs, style, deck_heading, deck_origin, mats_solid='concrete', ground_open=True,
                      tiles=None, name='body', feature='', spec=(), dims=None, src='obs', deck_mat='deck', bands=None):
    """shell (facades, recesses, deck, parapet) + LOD0 details (piers, screens) of an open parking structure."""
    tiles = tiles or TILES
    sh, det = MB(name), MB(name + '_piers')
    bands = bands or level_bands(slabs, top, ground_open=ground_open, deck=deck)
    garage_facade(sh, P, bands, style, tiles, None, gdetail=det)
    inner = deck_and_parapet(sh, P, deck, top, deck_mat, deck_uvf(B.F, deck_heading, deck_origin))
    B.shells.append(Part(name, sh, 'shell', src, feature, spec, dims))
    if not det.empty():
        B.details[0].append(Part(name + '_piers', det, 'detail', 'inf', 'facade piers / perforated screens (module inf)', spec))
    return inner, bands


TILES = {'precast': (6.0, 3.0), 'precast_band': (6.0, 1.6), 'concrete': (4.0, 4.0), 'concrete_board': (4.0, 2.4), 'screen': (3.0, 1.6),
         'screen_edge': (1.0, 1.0), 'interior': (6.0, 6.0), 'hangar_wall': (2.0, 2.0), 'moc_wall': (2.0, 2.0), 'glass_hyatt': (3.0, 3.3333),
         'metal_dark': (3.0, 3.0), 'podium': (6.0, 3.5555), 'cac_wall': (3.0, 4.572), 'glass_band': (3.0, 3.0), 'coping': (3.0, 3.0)}


# ================================================================================================ Garages A / G
def garage_ag(k):
    """International Garage A / G (BL-02 panel B, BL-03 rows 1-2): the garage body (outline up to u = Lb), the helix drum
    (outline arc at the west end), core cylinder and Garage A rooftop box; deck at the drum ring (dotted on BL-03) [unk]."""
    g = DL.GAR[k]; G = DL.ggeom(k)
    hd = float(g['drum']); deck = hd - PARAPET_H
    c, a, b, L, Lb = G['c'], G['a'], G['b'], G['L'], G['Lb']
    o = c + a * (Lb / 2 - L / 2)
    nm = 'International Garage A (Bldg 95)' if k == 'garage_a' else 'International Garage G (Bldg 495)'
    B = Bldg(k, nm, o[0], o[1], 'obs', [f'{k}_footprint', f'{k}_height', f'{k}_levels', f'{k}_airtrain_level', 'garage_ag_facade', f'{k}_roof_cars'],
             dict(footprint=dim('SFO Museum outline up to u = %.1f (garage body)' % Lb, 'obs', 'BL-02 B / draw_landside.ggeom'),
                  parapet_top=dim(hd, 'unk', 'drum-ring value %.1f m [obs, low] (range %s); the roof deck is NOT measured: drawn dotted '
                                  'at the drum ring on BL-03' % (hd, g['drum_rng'])),
                  deck=dim(round(deck, 2), 'unk', 'parapet top - %.2f m (42-in guard) [inf]' % PARAPET_H),
                  levels=dim('9 [pub]; level lines at equal ninths of the drum ring (BL-03 placeholder)', 'unk', 'BL-03'),
                  drum=dim(dict(centre=[round(float(G['drum_c'][0]), 2), round(float(G['drum_c'][1]), 2)], D=round(2 * G['R'], 1)), 'obs',
                           'circle fit to the outline arc (BL-02 B)'),
                  core=dim(dict(D=DL.GAR_CORE_D, top=round(hd + 4.0, 2)), 'obs/unk', 'D ~13 m [obs NAIP]; height above the deck unk (BL-03 draws 4 m)'),
                  long_face_m=dim(round(Lb, 1), 'obs', 'garage body to the start of the guideway tail')),
             inferred=['deck = drawn parapet top - 1.07 m guard', 'facade module: precast piers every %.1f m, perforated screens between, '
                       'spandrels %.2f / %.2f m about each level line' % (PIER_DX['gar'], SPANDREL_DN, SPANDREL_UP),
                       'drum: precast bands, open band only under the top deck (arched openings [obs spec] drawn as an open band)'],
             unknown=['roof deck height (candidates 24.4-28.0 / 25-30 [disputed] / %s [NAIP 2-D shift] / %.1f drum ring)' %
                      (LB[k]['shift_scan']['peaks'][0]['h_if_true_footprint_m'], hd),
                      'level heights (equal ninths placeholder)', 'core cylinder height (drawn 4 m)'] +
                     (['rooftop box height (drawn 3.5 m)'] if G['box'] else []),
             not_modelled=['square stair / elevator towers above the parapet [obs spec, positions not measured]', 'roof light poles'])
    F = B.F
    U = lambda p: float(np.dot(np.asarray(p, float) - c, a) + L / 2)
    cutter = Polygon([c + a * (-L / 2 - 60) + b * 200, c + a * (Lb - L / 2) + b * 200, c + a * (Lb - L / 2) - b * 200, c + a * (-L / 2 - 60) - b * 200])
    body_w = largest(sfom_union(g['nm']).intersection(cutter))
    if not g['rail_near']:
        # Garage G: the station stands outside the body along the NNW face (BL-02: station u 37-167, b -1..46) and the
        # guideway runs along that face: the guideway polygon is cut out of the body (no shared volume)
        body_w = largest(body_w.difference(RAIL.buffer(0.4, join_style=2)))
    else:
        # Garage A: the two single tracks run through the body along its SSE half from the west face (u ~2.6) to the east
        # cut (u = Lb), through the station (BL-03 "along the SSE side, behind this face"); the outline is notched round the
        # tracks near the east end: the track strips are united with the body so the tracks are inside it end to end
        strip = Polygon([c + a * (2.0 - L / 2) - b * 30, c + a * (Lb - L / 2) - b * 30, c + a * (Lb - L / 2) - b * 7, c + a * (2.0 - L / 2) - b * 7])
        body_w = largest(unary_union([body_w, RAIL.intersection(strip).buffer(0.3, join_style=2)]).buffer(0.05).buffer(-0.05))
    body_w = body_w.simplify(0.05, preserve_topology=True)
    P = F.poly(body_w)
    circ = dict(c=[float(G['drum_c'][0]), float(G['drum_c'][1])], R=float(G['R']))
    slabs = [hd * i / 9 for i in range(1, 9)]
    # AirTrain portals (Garage A: the guideway runs through the body along the SSE half, BL-03): where the guideway polygon
    # crosses the body outline, a solid precast station-block face with the portal opening at the loop level
    import landside_airtrain as AT
    zt = AT.LOOP_DECK
    portal = []
    if g['rail_near']:
        cross = body_w.exterior.intersection(RAIL.buffer(0.2))
        for seg in getattr(cross, 'geoms', [cross]):
            if seg.geom_type != 'LineString' or seg.length < 2.0: continue
            q = np.array(seg.coords); dd = q[-1] - q[0]
            if abs(dd @ a) / (np.hypot(*dd) or 1) < 0.3:                  # faces across the tracks only (u ~2.6 and u = Lb)
                portal.append([F.L(*p) for p in (q[0], q[-1])])
    portal_lines = [LineString(p) for p in portal]

    def style(pa, pb):
        mid = Point(0.5 * (pa[0] + pb[0]), 0.5 * (pa[1] + pb[1]))
        for pl in portal_lines:
            if pl.distance(mid) < 0.5 and LineString([pa, pb]).length > 0.5:
                s_a = LineString([pa, pb]).project(Point(pl.coords[0])); s_b = LineString([pa, pb]).project(Point(pl.coords[-1]))
                return dict(kind='solid', solid='precast', holes=[(min(s_a, s_b) + 0.6, max(s_a, s_b) - 0.6, zt - AT.DECK_T - 0.3, zt + AT.PORTAL_H)])
        if on_circle(pa, pb, F, circ):
            return dict(kind='solid', solid='precast_band')
        d = np.array(pb, float) - np.array(pa, float); d /= np.linalg.norm(d)
        al = abs(d @ np.array([a[0], -a[1]]))           # local XY of the long axis
        if al > 0.85:
            return dict(kind='screen', pier_dx=PIER_DX['gar'], solid='precast')
        return dict(kind='open', pier_dx=PIER_DX['cg'], solid='precast')
    inner, bands = parking_structure(B, P, hd, deck, slabs, style, 66.0, (float(c[0]), float(c[1])), name=f'{k}_body',
                                     feature='garage body: precast spandrels, perforated screens, dark open levels, deck + parapet',
                                     spec=['garage_ag_facade', f'{k}_footprint'], dims=B.dims, src='obs')
    # drum: open band under the top deck (arched openings at the top [obs spec garage_ag_facade]), as a recess in the band
    sh = B.shells[-1].mb
    cl = np.array(F.L(*circ['c']))
    zo0, zo1 = slabs[-1] + SPANDREL_UP + 0.4, deck - SPANDREL_DN - 0.2
    # (the drum's solid wall already covers that band: add the arched-opening band as dark inset panels on its face)
    dr = MB('drum_openings')
    for p0, p1, s0 in ring_edges(P):
        if not on_circle(p0, p1, F, circ): continue
        n, Le = edge_normal(p0, p1)
        q0 = np.array(p0) + n * 0.05; q1 = np.array(p1) + n * 0.05
        dr.quad_wall(tuple(q0), tuple(q1), zo0, zo1, zo0, zo1, 'interior', s0, (2.0, 2.0))
    B.details[0].append(Part(f'{k}_drum_openings', dr, 'detail', 'obs', 'drum top openings (arched openings [obs spec]; drawn as a dark band)',
                             ['garage_ag_facade']))
    # core cylinder D 13 at the drum centre, deck .. drum ring + 4 m (BL-03: height unk, drawn 4 m)
    cm = MB(f'{k}_core')
    cyl(cm, cl, deck, hd + 4.0, 24, 'precast_band', TILES['precast_band'], top='coping', smooth=True)
    B.shells.append(Part(f'{k}_core', cm, 'shell', 'obs', 'helix core cylinder above the deck (D obs NAIP; height unk, drawn 4 m)',
                         ['garage_ag_facade'], dict(D=dim(DL.GAR_CORE_D, 'obs', 'NAIP dark disc, approx'), top=dim(hd + 4.0, 'unk', 'BL-03 drawn 4 m'))))
    if G['box']:
        bx = MB(f'{k}_rooftop_box')
        bp = F.poly(Polygon(G['box'][4]))
        walls(bx, bp, deck, hd + 3.5, 'precast', TILES['precast'])
        cap(bx, bp, hd + 3.5, 'coping', 6.0)
        B.shells.append(Part(f'{k}_rooftop_box', bx, 'shell', 'obs', 'rooftop box (NAIP, lean-corrected; stair / elevator tower over the station? [inf])',
                             [f'{k}_height'], dict(plan=dim('u %.0f-%.0f' % (G['box'][0], G['box'][1]), 'obs', 'BL-02 B'),
                                                   top=dim(hd + 3.5, 'unk', 'BL-03 drawn 3.5 m'))))
    B.decks.append(dict(poly=inner, z=deck, heading=66.0, origin=(float(c[0]), float(c[1])), key=k,
                        density=LB[k]['roof_cars']['cars_per_1000m2'], count_src=LB[k]['roof_cars'],
                        exclude=[Point(cl).buffer(DL.GAR_CORE_D / 2 + 1.5)] + ([bp.buffer(1.5)] if G['box'] else [])))
    # portals: dark tunnel boxes 10 m deep behind each opening
    tn = MB(f'{k}_portal')
    for pl in portal:
        pa, pb = np.array(pl[0]), np.array(pl[-1])
        n, Le = edge_normal(pa, pb)
        mid = 0.5 * (pa + pb)
        if P.contains(Point(*(mid + n * 1.0))): n = -n          # n outward
        if P.contains(Point(*(mid + n * 1.0))) or not P.buffer(0.01).contains(Point(*(mid - n * 1.0))): continue
        din = -n * 10.0
        if np.cross(np.r_[pb - pa, 0], np.r_[n, 0])[2] > 0: pa, pb = pb, pa      # walk so that n is on the right
        z0, z1 = zt - AT.DECK_T - 0.3, zt + AT.PORTAL_H
        d = (pb - pa) / Le
        pa2, pb2 = pa + d * 0.6, pb - d * 0.6
        tn.quad_wall(tuple(pa2 + din), tuple(pb2 + din), z0, z1, z0, z1, 'interior', 0, (6, 6))     # back, facing the opening
        tn.quad_wall(tuple(pa2), tuple(pa2 + din), z0, z1, z0, z1, 'interior', 0, (6, 6))     # sides, facing the tunnel
        tn.quad_wall(tuple(pb2 + din), tuple(pb2), z0, z1, z0, z1, 'interior', 0, (6, 6))
        q = [pa2, pb2, pb2 + din, pa2 + din]                                                    # CCW from above
        tn.face([(p[0], p[1], z1) for p in q[::-1]], 'interior', [(0, 0), (1, 0), (1, 1), (0, 1)])   # soffit (down)
        tn.face([(p[0], p[1], z0) for p in q], 'interior', [(0, 0), (1, 0), (1, 1), (0, 1)])         # floor (up)
    if not tn.empty():
        B.shells.append(Part(f'{k}_portal', tn, 'shell', 'obs', 'AirTrain portal into the garage station (guideway crossing [obs polygons]; '
                             'opening height = loop level placeholder)', [f'{k}_airtrain_level', 'at_section']))
    B.anchors = dict(drum_ring=hd, deck=round(deck, 2), core_top=hd + 4.0, levels=[round(z, 2) for z in slabs], Lb=Lb, u_axis_world=[float(a[0]), float(a[1])],
                     u0_world=[float((c - a * L / 2)[0]), float((c - a * L / 2)[1])], portal_spans=len(portal))
    # LOD2
    cm2 = MB(f'{k}_L2')
    stack_coarse(cm2, P.simplify(0.8), hd, 'precast', 'deck_far')
    B.coarse.append(Part(f'{k}_L2', cm2, 'coarse', 'obs', 'garage body (coarse)', [f'{k}_footprint']))
    return B
