"""AirTrain guideway and stations of the 3-D landside asset (data/buildings3d/landside.glb). Pure numpy / shapely / scipy.

THE REFERENCE is the 2-D landside sheets (BL-01..03) and their data:
  guideway plan    SFO Museum 'AirTrain Rail' 1779914099 (data/sfo_airport.json) [obs]: one polygon (24 holes), single
                   4.8-5.1 m / twin 9.5-11.5 m (spec at_rail_polygon); built as drawn, clipped only where another asset
                   holds it (inside the ITB outline: data/buildings3d/itb.glb core block; inside the Garage A body)
  stations         the OLDER SFO Museum station polygons (1729791xxx: A / G right way round, BL-01 note), T1 / T2 / T3 on
                   the central garage ring, Garage G, Grand Hyatt, West Field Road in / out, Rental Car Center, LTP
  section          spec at_section / at_station_domestic [obs photos]: concrete deck, trough side walls, single-column T-piers
                   on the extension, glazed platform enclosures with a single-pitch roof (terminal-area stations), curved
                   metal canopies with platform-door cabins (RCC / LTP / West Field), the RCC cylindrical perforated tower
GUIDEWAY LEVEL. Not published anywhere except as station LEVELS (spec at_stations: CG Level 5, garages Level 7, ITB Level 4,
hotel 4th floor, LTP Level 5) and two conflicting general figures ("35 to 40 ft at its highest point" [pub, low] vs the
extension "50 ft above a public roadway" [pub]). The sheets draw placeholders (BL-03: CG L5 = 4/5 of 81 ft = 19.75 m;
garages L7 = 6/8 of the drum ring = 29.7 / 28.2 m; RCC platform = 3/4 of 54 ft = 12.35 m) [unk]. The 3-D needs ONE
continuous profile with physically possible grades, so the deck-top level is interpolated along the guideway (geodesic
distance inside the polygon) between station anchors (ANCHORS, each with its tag and reason; deviations from the sheet
placeholders are listed there and in the manifest).

Frames: world x east, z south, metres from the ARP (js/geo.js); every node has its own origin (landside_mesh.Frame).
"""
import math
import os
import sys

import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_landside as DL  # noqa: E402
from draw_lib import FT  # noqa: E402
from landside_mesh import MB, Frame, boxm, cap, orient_all, polys, rings_of, tube  # noqa: E402

DECK_T = 1.6          # guideway deck depth (the app's 9.0-10.6 m slab, js/live/airport.js) [inf]
WALL_H = 1.1          # trough side wall above the deck top (photos l1 / l5: walkway wall + railing) [inf]
WALL_T = 0.30         # side wall thickness [inf]
PORTAL_H = 6.0        # clear height of the AirTrain portal into Garage A (CX-100 car + guide beam + headroom) [inf]
PIER_DX = 30.0        # pier spacing along the guideway [inf]; "single-column T-piers along the extension" [obs at_section]
PIER_D = 1.8          # pier column diameter (single track) [inf]; twin decks (width > 8 m): 2.4 m [inf]
CAP_D = 1.4           # pier cap depth below the deck [inf]
ENCL_H = 4.5          # platform enclosure height above the platform (BL-03 central garage: drawn 4.5 m) [unk]
TILE = 420.0          # guideway node tiles (m): one glTF node + LODs per tile [our choice]
RES = 1.0             # level raster resolution (m)
SMOOTH_SIG = 6.0      # lateral blending of the level field (m) [our choice]

# Network level placeholders (deck top = platform level), m above grade. CG L5 from BL-03 (4/5 of the published 81 ft,
# equal fifths [unk]); the garages A / G are put on the same network level because the Grand Hyatt station is 40 m along
# the same track from the Garage A station (BL-03's 6/8-of-the-drum placeholder 29.7 m would need a > 20 % grade); 19.75 m
# is inside the sheet's own [inf] range for Level 7 (6 rises x 3.05-3.5 m = 18.3-21.0 m).
CG_L5 = 81 * FT * 4 / 5
NET_LEVEL = CG_L5
ITB_L4 = 16.5        # ITB Level 4 [unk]: ITB L3 = 11.5 m [obs, spec_itb]; 16.5 keeps the guideway (deck + 1.1 m wall) inside
#                      the ITB core block of data/buildings3d/itb.glb (17.9 m placeholder)
RCC_PLATFORM = 5.8   # RCC station platform [inf, photo l5]: the ribbon windows of the west wall are level with the platform,
#                      with a concrete band and the canted louvre screen above them to the 54-ft roof outline, and the station
#                      tower (DOF TANK 60 ft) stands ~2 D above the platform; BL-03 draws a 3/4-of-54-ft placeholder (12.35 m [unk])
LTP_LEVEL = 50 * FT  # Long-Term Parking station: the extension runs "50 feet above a public roadway" [pub]; LTP garage Level 5
#                      (bridge) [pub], height unknown

# key: (sfom id, deck-top level, tag, note, station type)  ('dom' glazed enclosure + single-pitch roof; 'canopy' curved
# canopy + door cabins; None = no station built (inside another asset))
STATIONS = {
    'T1': (1729791955, CG_L5, 'unk', 'central garage Level 5 [pub], 4/5 of 81 ft (BL-03 placeholder)', 'dom'),
    'T2': (1729791959, CG_L5, 'unk', 'central garage Level 5 [pub], 4/5 of 81 ft (BL-03 placeholder)', 'dom'),
    'T3': (1729791957, CG_L5, 'unk', 'central garage Level 5 [pub], 4/5 of 81 ft (BL-03 placeholder)', 'dom'),
    'ITB_A': (1729791961, ITB_L4, 'unk', 'ITB Level 4 [pub]; height placeholder inside the itb.glb core block', None),
    'ITB_G': (1729791965, ITB_L4, 'unk', 'ITB Level 4 [pub]; height placeholder inside the itb.glb core block', None),
    'GAR_A': (1729791949, NET_LEVEL, 'inf', 'Garage A Level 7 [pub]; network level (BL-03 placeholder 29.7 m deviates: grade)', None),
    'GAR_G': (1729791947, NET_LEVEL, 'inf', 'Garage G Level 7 [pub]; network level (BL-03 placeholder 28.2 m deviates: grade)', 'dom'),
    'HYATT': (1729791967, NET_LEVEL, 'inf', 'hotel 4th floor via an enclosed bridge [pub]; network level (40 m from Garage A station)', 'dom'),
    'WFR_IN': (1729791953, None, 'unk', 'West Field Road: no level source (interpolated)', 'canopy'),
    'WFR_OUT': (1729791951, None, 'unk', 'West Field Road: no level source (interpolated)', 'canopy'),
    'RCC': (1729791943, RCC_PLATFORM, 'inf', 'photo l5 (see RCC_PLATFORM); BL-03 placeholder 12.35 m [unk]', 'canopy'),
    'LTP': (1730051431, LTP_LEVEL, 'pub', '"50 feet above a public roadway" (extension) [pub]; LTP Level 5 bridge [pub]', 'canopy'),
}
RCC_TOWER = dict(D=DL.RCC_TOWER_D, top=None)   # top = DOF TANK agl (set below)


def struct_poly(sid):
    f = next(f for f in D.AIR['structures'] if f['id'] == sid)
    return unary_union([Polygon(p[0], p[1:]).buffer(0) for p in f['polys']])


RAIL = struct_poly(1779914099)
ST_POLY = {k: struct_poly(v[0]) for k, v in STATIONS.items()}
ITB_OUTLINE = unary_union([Polygon(p[0], p[1:]).buffer(0) for t in D.AIR['terminals'] if t['name'] == 'International Terminal'
                           for p in t['polys']])
_tk = next(d for d in D.LANDM['buildings']['rental_car_center']['dof'] if d['type'] == 'TANK')
RCC_TOWER['top'] = float(_tk['agl_m']); RCC_TOWER['world'] = [float(v) for v in _tk['world']]; RCC_TOWER['oas'] = _tk['oas']


# ------------------------------------------------------------------------------------------------ level field
class Levels:
    """deck-top level over the guideway (+ station) polygons: geodesic interpolation between station anchors (two nearest
    anchors by distance inside the polygon, weights 1 / d: linear along the path between two stations)."""

    def __init__(self, region):
        import cv2
        from scipy.ndimage import distance_transform_edt
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import dijkstra
        x0, z0, x1, z1 = region.bounds
        self.x0, self.z0 = x0 - 4, z0 - 4
        W = int(math.ceil((x1 - x0 + 8) / RES)); H = int(math.ceil((z1 - z0 + 8) / RES))
        m = np.zeros((H, W), np.uint8)
        f = lambda r: np.array([[(x - self.x0) / RES - 0.5, (z - self.z0) / RES - 0.5] for x, z in r], np.float32)
        for p in polys(region):
            cv2.fillPoly(m, [np.round(f(p.exterior.coords) * 8).astype(np.int32)], 1, shift=3)
            for h in p.interiors:
                cv2.fillPoly(m, [np.round(f(h.coords) * 8).astype(np.int32)], 0, shift=3)
        self.mask = m.astype(bool)
        idx = -np.ones(m.shape, np.int64); n = int(self.mask.sum()); idx[self.mask] = np.arange(n)
        rows, cols, w = [], [], []
        for dr, dc, wt in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2))):
            r0, r1, c0, c1 = max(0, -dr), H - max(0, dr), max(0, -dc), W - max(0, dc)
            a = idx[r0:r1, c0:c1]
            b = idx[r0 + dr:r1 + dr, c0 + dc:c1 + dc]
            ok = (a >= 0) & (b >= 0)
            rows.append(a[ok]); cols.append(b[ok]); w.append(np.full(int(ok.sum()), wt))
        r = np.concatenate(rows); c = np.concatenate(cols); ww = np.concatenate(w)
        self._edges = (r, c, ww)
        G = coo_matrix((np.r_[ww, ww], (np.r_[r, c], np.r_[c, r])), shape=(n, n)).tocsr()
        yy, xx = np.nonzero(self.mask)
        px = self.x0 + (xx + 0.5) * RES; pz = self.z0 + (yy + 0.5) * RES
        anchors = [(k, v[1]) for k, v in STATIONS.items() if v[1] is not None]
        pts = shapely.points(px, pz)
        # harmonic interpolation on the cell graph: the cells of each anchored station polygon are fixed at its level, every
        # other cell is the conductance-weighted mean of its neighbours (Laplace). Along a guideway this is linear between
        # two stations, level across the deck, continuous through junctions and constant beyond the last station.
        from scipy.sparse import diags
        from scipy.sparse.linalg import spsolve
        fixed = np.zeros(n, bool); hfix = np.zeros(n)
        for k, h in anchors:
            # the station's length along its axis, across the whole guideway there (both tracks of a twin section, +-12 m beyond
            # the polygon): a passing track beside the platform is at the platform level too
            mr = np.array(ST_POLY[k].minimum_rotated_rectangle.exterior.coords)[:4]
            e0, e1 = mr[1] - mr[0], mr[2] - mr[1]
            if np.hypot(*e0) < np.hypot(*e1): e0, e1 = e1, e0
            La, Wa = np.hypot(*e0), np.hypot(*e1); ua, ub = e0 / La, e1 / Wa; cc = mr.mean(0)
            d = np.c_[px - cc[0], pz - cc[1]]
            sel = (np.abs(d @ ua) <= La / 2) & (np.abs(d @ ub) <= Wa / 2 + 12.0)
            fixed |= sel; hfix[sel] = h
        Wc = coo_matrix((np.r_[1 / ww, 1 / ww], (np.r_[r, c], np.r_[c, r])), shape=(n, n)).tocsr()
        Lap = (diags(np.asarray(Wc.sum(1)).ravel()) - Wc).tocsr()
        u = ~fixed
        hv = hfix.copy()
        comp_ok = np.ones(n, bool)
        A = Lap[u][:, u].tocsc(); b = -(Lap[u][:, fixed] @ hfix[fixed])
        # cells in components without any anchor would make A singular: give them a weak pull to NET_LEVEL
        A = A + diags(np.full(A.shape[0], 1e-9))
        b = b + 1e-9 * NET_LEVEL
        hv[u] = spsolve(A, b)
        self.anchor_d = {}
        # parallel decks a few metres apart (twin single tracks, separate polygon parts) are not graph neighbours and could take
        # different levels: a normalised Gaussian (sigma SMOOTH_SIG) over all guideway cells blends them; the platforms keep
        # their level (constant over the station length, checked by verify_landside.py)
        from scipy.ndimage import gaussian_filter
        g0 = np.zeros(m.shape, np.float64); g0[self.mask] = hv
        wsum = gaussian_filter(self.mask.astype(np.float64), SMOOTH_SIG / RES)
        gs = gaussian_filter(g0, SMOOTH_SIG / RES) / np.maximum(wsum, 1e-9)
        hv = gs[self.mask]
        grid = np.full(m.shape, np.nan, np.float32); grid[self.mask] = hv
        # fill outside the mask with the nearest inside value (vertices on / just outside the outline)
        _, (iy, ix) = distance_transform_edt(~self.mask, return_indices=True)
        self.grid = grid[iy, ix]
        self.hv = hv
        self.dt = distance_transform_edt(self.mask) * RES
        self.idx = idx

    def h(self, x, z):
        """bilinear deck-top level at world (x, z)."""
        fx = (np.asarray(x, float) - self.x0) / RES - 0.5; fz = (np.asarray(z, float) - self.z0) / RES - 0.5
        H, W = self.grid.shape
        ix = np.clip(np.floor(fx).astype(int), 0, W - 2); iz = np.clip(np.floor(fz).astype(int), 0, H - 2)
        tx = np.clip(fx - ix, 0, 1); tz = np.clip(fz - iz, 0, 1)
        g = self.grid
        return (g[iz, ix] * (1 - tx) * (1 - tz) + g[iz, ix + 1] * tx * (1 - tz) + g[iz + 1, ix] * (1 - tx) * tz + g[iz + 1, ix + 1] * tx * tz)

    def max_grade(self, pct=None):
        """largest level difference per metre along the guideway (graph edges between connected 1-m cells; cells across a
        narrow hole between two decks are not connected); pct: a percentile instead of the max."""
        r, c, ww = self._edges
        g = np.abs(self.hv[r] - self.hv[c]) / (ww * RES)
        return float(np.max(g) if pct is None else np.percentile(g, pct))


def skeleton(mask):
    """Zhang-Suen thinning of a boolean raster (numpy, vectorised)."""
    img = np.pad(mask.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P = img
            p2 = P[:-2, 1:-1]; p3 = P[:-2, 2:]; p4 = P[1:-1, 2:]; p5 = P[2:, 2:]
            p6 = P[2:, 1:-1]; p7 = P[2:, :-2]; p8 = P[1:-1, :-2]; p9 = P[:-2, :-2]
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(n.astype(np.int32) for n in nb)
            seq = nb + [p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int32) for i in range(8))
            c = P[1:-1, 1:-1] == 1
            if step == 0:
                m = c & (B >= 2) & (B <= 6) & (A == 1) & (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                m = c & (B >= 2) & (B <= 6) & (A == 1) & (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            if m.any():
                img[1:-1, 1:-1][m] = 0; changed = True
        if not changed:
            break
    return img[1:-1, 1:-1].astype(bool)


# ------------------------------------------------------------------------------------------------ meshes
def deck_shell(mb, F, poly_w, lev, mat_top='guideway_deck', mat_side='guideway', walls=True, seg=4.0):
    """guideway deck on a world polygon: top at lev.h, bottom DECK_T below, trough side walls WALL_H high on every edge.
    poly_w: world polygon (may have holes). Faces outward; all vertices follow the level field."""
    from landside_mesh import tri_poly
    Pw = orient_all(shapely.segmentize(poly_w, seg))
    Lp = F.poly(Pw)
    H = lambda X, Y: float(lev.h(*F.W(X, Y)))
    inner = orient_all(Lp.buffer(-WALL_T, join_style=2)) if walls else Lp
    # top cap (inside the side walls) and bottom cap (whole outline)
    for p in polys(inner):
        p = orient_all(shapely.segmentize(p, seg))
        for t in tri_poly(p):
            mb.face([(q[0], q[1], H(*q)) for q in t], mat_top, [(q[0] / 6.0, q[1] / 6.0) for q in t])
    for p in polys(Lp):
        for t in tri_poly(p):
            t2 = t[::-1]
            mb.face([(q[0], q[1], H(*q) - DECK_T) for q in t2], mat_side, [(q[0] / 6.0, q[1] / 6.0) for q in t2])
    # outer faces: deck edge + side wall (one face per edge, deck bottom -> wall top)
    top_off = WALL_H if walls else 0.0
    for p in polys(Lp):
        for ring in rings_of(p):
            n = len(ring); s = 0.0
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 1e-3: continue
                ha, hb = H(*a), H(*b)
                mb.face([(a[0], a[1], ha - DECK_T), (b[0], b[1], hb - DECK_T), (b[0], b[1], hb + top_off), (a[0], a[1], ha + top_off)], mat_side,
                        [(s / 4.0, -DECK_T / 4.0), ((s + L) / 4.0, -DECK_T / 4.0), ((s + L) / 4.0, top_off / 4.0), (s / 4.0, top_off / 4.0)])
                s += L
    if not walls:
        return
    # wall coping (ring between outline and inner) and inner faces of the walls
    ring_poly = orient_all(Lp.difference(inner))
    for t in tri_poly(ring_poly):
        mb.face([(q[0], q[1], H(*q) + WALL_H) for q in t], 'coping', [(q[0] / 3.0, q[1] / 3.0) for q in t])
    for p in polys(inner):
        for ring in rings_of(p):
            n = len(ring)
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-3: continue
                ha, hb = H(*a), H(*b)
                mb.face([(b[0], b[1], hb), (a[0], a[1], ha), (a[0], a[1], ha + WALL_H), (b[0], b[1], hb + WALL_H)], mat_side,
                        [(0, 0), (1, 0), (1, 0.3), (0, 0.3)])


def pier(mb, F, site, lev, sides=10, cap_box=True):
    """single-column T-pier: column from grade to the cap, cap beam across the deck under its bottom."""
    x, z, w, d = site['x'], site['z'], site['w'], site['dir']
    h = float(lev.h(x, z)) - DECK_T
    if h < 3.0: return
    c = F.L(x, z)
    D_ = PIER_D if w < 8.0 else 2.4
    zc = h - CAP_D
    tube(mb, [(c[0], c[1], 0.0), (c[0], c[1], zc + 0.05)], D_ / 2, sides, 'guideway', tile=3.0)
    if cap_box:
        dl = np.array([d[0], -d[1]])            # world dir -> local XY (z south -> Y north)
        n = np.array([dl[1], -dl[0]])
        boxm(mb, c, n, max(D_ + 0.6, w - 0.8), 2.0, (zc, h - 0.02), 'guideway', (4.0, 4.0), top=False, bottom=True)


def station(mb, det, F, key, lev, lod=0, exclude=None):
    """station enclosure / canopy on its SFO Museum polygon: platform = polygon minus the guideway polygon (minus the part
    inside a host building body, `exclude`), at the level."""
    sid, _, tag, note, kind = STATIONS[key]
    P = ST_POLY[key]
    if exclude is not None and not exclude.is_empty:
        rest = [q for q in polys(P.difference(exclude.buffer(0.3, join_style=2))) if q.area > 30.0]
        P = max(rest, key=lambda q: q.area) if rest else P
    plat_w = orient_all(P.difference(RAIL.buffer(0.15, join_style=2)).buffer(0))
    plats = [p for p in polys(plat_w) if p.area > 15.0]
    hz = float(lev.h(P.centroid.x, P.centroid.y))
    # platform slab
    for p in plats:
        Lp = F.poly(p)
        for q in polys(Lp):
            cap(mb, q, hz + 0.02, 'platform', 6.0)
            cap(mb, q, hz - DECK_T, 'guideway', 6.0, down=True)
            for ring in rings_of(q):
                n = len(ring)
                for i in range(n):
                    mb.quad_wall(ring[i], ring[(i + 1) % n], hz - DECK_T, hz + 0.02, hz - DECK_T, hz + 0.02, 'guideway', 0.0, (4.0, 4.0))
    # roof over the whole station polygon (minimum rectangle), single pitch (dom) or curved (canopy)
    mr = P.minimum_rotated_rectangle
    cs = np.array(mr.exterior.coords)[:4]
    e0, e1 = cs[1] - cs[0], cs[2] - cs[1]
    if np.linalg.norm(e0) < np.linalg.norm(e1):
        cs = np.roll(cs, -1, axis=0); e0, e1 = cs[1] - cs[0], cs[2] - cs[1]
    Lr, Wr = float(np.linalg.norm(e0)), float(np.linalg.norm(e1))
    ua, ub = e0 / Lr, e1 / Wr
    c0 = cs[0]
    loc = lambda u, v: F.L(*(c0 + ua * u + ub * v))
    zr0 = hz + ENCL_H
    if kind == 'dom':
        # single-pitch roof: ENCL_H at one long side, + 0.8 m at the other [obs photo shape; heights unk]
        zr = lambda v: zr0 + 0.8 * v / Wr
        pts = [(0, -0.6), (Lr, -0.6), (Lr, Wr + 0.6), (0, Wr + 0.6)]
        top = [(*loc(u, v), zr(v) + 0.35) for u, v in pts]; bot = [(*loc(u, v), zr(v)) for u, v in pts]
        mb.face(top, 'station_roof', [(u / 6.0, v / 6.0) for u, v in pts])
        mb.face(bot[::-1], 'station_soffit', [(u / 6.0, v / 6.0) for u, v in pts[::-1]])
        for i in range(4):
            a, b = pts[i], pts[(i + 1) % 4]
            mb.face([bot[i], bot[(i + 1) % 4], top[(i + 1) % 4], top[i]], 'station_roof', [(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
        # glazed walls along the platform outline (enclosure) up to the roof soffit
        for p in plats:
            for q in polys(F.poly(p)):
                for ring in rings_of(q):
                    n = len(ring); s = 0.0
                    for i in range(n):
                        a, b = ring[i], ring[(i + 1) % n]
                        L = math.hypot(b[0] - a[0], b[1] - a[1])
                        if L < 0.5: continue
                        za = zr(_v_of(F, a, c0, ub)) ; zb = zr(_v_of(F, b, c0, ub))
                        mb.face([(a[0], a[1], hz + 0.02), (b[0], b[1], hz + 0.02), (b[0], b[1], zb), (a[0], a[1], za)], 'station_glass',
                                [(s / 3.0, 0), ((s + L) / 3.0, 0), ((s + L) / 3.0, (zb - hz) / 3.0), (s / 3.0, (za - hz) / 3.0)])
                        s += L
        # posts every 6 m along both long sides (outside the platform faces, under the roof edge) + X-bracing (LOD0)
        if det is not None:
            for v in (-0.3, Wr + 0.3):
                for u in np.arange(1.5, Lr - 1.0, 6.0):
                    c = loc(u, v)
                    boxm(det, c, (1, 0), 0.25, 0.25, (hz + 0.02, zr(v) - 0.01), 'steel', (2.0, 2.0))
                if lod == 0:
                    for u in np.arange(1.5, Lr - 7.0, 12.0):
                        a = loc(u, v); b = loc(u + 6.0, v)
                        tube(det, [(a[0], a[1], hz + 0.3), (b[0], b[1], zr(v) - 0.2)], 0.06, 4, 'steel')
                        tube(det, [(b[0], b[1], hz + 0.3), (a[0], a[1], zr(v) - 0.2)], 0.06, 4, 'steel')
    else:
        # curved metal canopy across the station (5 facets), 3.6 m at the eaves, 4.6 m at the crown [obs l5 shape; heights inf]
        nseg = 6
        vv = np.linspace(-0.8, Wr + 0.8, nseg + 1)
        zc = lambda v: hz + 3.6 + 1.0 * math.sin(math.pi * min(max((v + 0.8) / (Wr + 1.6), 0), 1))
        for j in range(nseg):
            v0, v1 = vv[j], vv[j + 1]
            q = [(*loc(0, v0), zc(v0) + 0.25), (*loc(Lr, v0), zc(v0) + 0.25), (*loc(Lr, v1), zc(v1) + 0.25), (*loc(0, v1), zc(v1) + 0.25)]
            mb.face(q, 'station_roof', [(0, v0 / 3), (Lr / 6, v0 / 3), (Lr / 6, v1 / 3), (0, v1 / 3)])
            qd = [(*loc(0, v0), zc(v0)), (*loc(0, v1), zc(v1)), (*loc(Lr, v1), zc(v1)), (*loc(Lr, v0), zc(v0))]
            mb.face(qd, 'station_soffit', [(0, v0 / 3), (0, v1 / 3), (Lr / 6, v1 / 3), (Lr / 6, v0 / 3)])
        for u, sg in ((0.0, -1), (Lr, 1)):
            for j in range(nseg):
                v0, v1 = vv[j], vv[j + 1]
                a0, a1 = loc(u, v0), loc(u, v1)
                f = [(a0[0], a0[1], zc(v0)), (a1[0], a1[1], zc(v1)), (a1[0], a1[1], zc(v1) + 0.25), (a0[0], a0[1], zc(v0) + 0.25)]
                mb.face(f if sg < 0 else f[::-1], 'station_roof', [(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
        for v in (vv[0], vv[-1]):
            a0, a1 = loc(0, v), loc(Lr, v)
            f = [(a0[0], a0[1], zc(v)), (a1[0], a1[1], zc(v)), (a1[0], a1[1], zc(v) + 0.25), (a0[0], a0[1], zc(v) + 0.25)]
            mb.face(f if v > 0 else f[::-1], 'station_roof', [(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
        if det is not None:
            for p in plats:
                cpl = p.centroid
                for u in np.arange(3.0, Lr - 2.0, 8.0):
                    a = c0 + ua * u + ub * (Wr / 2)
                    # posts on the platform under the crown line
                    q = shapely.points(*a)
                    if not p.buffer(0.5).contains(q): continue
                    cl = F.L(*a)
                    boxm(det, cl, (1, 0), 0.3, 0.3, (hz + 0.02, zc(Wr / 2) - 0.02), 'steel', (2, 2))
                # platform-door cabins (glazed boxes 2.4 x 1.6 x 2.6 m) every 12 m along the platform's long axis [obs l5]
                if lod == 0:
                    for u in np.arange(6.0, Lr - 4.0, 12.0):
                        a = c0 + ua * u + ub * (Wr / 2)
                        pp = shapely.points(*a)
                        nearest = shapely.ops.nearest_points(p.exterior, Point(*a))[0] if p.contains(pp) else None
                        if nearest is None: continue
                        cl = F.L(nearest.x, nearest.y)
                        boxm(det, cl, (ua[0], -ua[1]), 2.4, 1.6, (hz + 0.02, hz + 2.6), 'station_glass', (3.0, 3.0), top_mat='station_roof')
    return dict(key=key, sid=sid, level=round(hz, 2), tag=tag, note=note, kind=kind, roof=round(zr0, 2), L=round(Lr, 1), W=round(Wr, 1))


def _v_of(F, p_local, c0, ub):
    w = np.array(F.W(*p_local)) - c0
    return float(np.dot(w, ub))


def rcc_tower(mb, F, lod=0):
    """RCC station stair / elevator tower: free-standing cylinder of perforated metal at the DOF TANK point (D 6.5 [inf],
    top = DOF 60 ft [pub]; identity inf) - BL-02 E / BL-03 row 3."""
    c = F.L(*RCC_TOWER['world'])
    from landside_mesh import cyl
    n = 28 if lod == 0 else 14
    cyl(mb, c, RCC_TOWER['D'] / 2, 0.0, RCC_TOWER['top'] - 0.3, n, 'perf_tower', (3.0, 3.0), top='coping', smooth=True)
    cyl(mb, c, RCC_TOWER['D'] / 2 + 0.08, RCC_TOWER['top'] - 0.3, RCC_TOWER['top'], n, 'steel', (3.0, 3.0), top='coping', smooth=True)


# ------------------------------------------------------------------------------------------------ assembly
def build(clip_world, building_outlines, Bldg, Part, dim, station_exclude=None):
    """-> (list of Bldg tiles, info). clip_world: polygons where the guideway is NOT built (held by another asset / inside a
    building body); building_outlines: polygons where no pier is placed (the guideway is carried by the building)."""
    region = unary_union([RAIL] + [ST_POLY[k] for k in STATIONS])
    lev = Levels(region)
    clip = unary_union(clip_world) if clip_world else Polygon()
    rail_b = orient_all(RAIL.difference(clip).buffer(0))
    # skeleton -> pier sites
    sk = skeleton(lev.mask & ~_raster(lev, clip))
    rail_mask = _raster(lev, RAIL)
    sk &= rail_mask
    yy, xx = np.nonzero(sk)
    px = lev.x0 + (xx + 0.5) * RES; pz = lev.z0 + (yy + 0.5) * RES
    rng = np.random.default_rng(7)
    order = rng.permutation(len(px))
    taken = {}
    sites = []
    blocked = unary_union(building_outlines + [clip]).buffer(1.5)
    pts_all = np.c_[px, pz]
    for i in order:
        gx, gz = int(px[i] // PIER_DX), int(pz[i] // PIER_DX)
        ok = True
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (qx, qz) in taken.get((gx + dx, gz + dz), []):
                    if (qx - px[i]) ** 2 + (qz - pz[i]) ** 2 < (PIER_DX * 0.93) ** 2: ok = False; break
                if not ok: break
            if not ok: break
        if not ok: continue
        taken.setdefault((gx, gz), []).append((px[i], pz[i]))
        if blocked.contains(Point(px[i], pz[i])): continue
        w = 2.0 * float(lev.dt[yy[i], xx[i]])
        near = pts_all[(np.abs(pts_all[:, 0] - px[i]) < 8) & (np.abs(pts_all[:, 1] - pz[i]) < 8)]
        if len(near) < 3: continue
        u, s_, vt = np.linalg.svd(near - near.mean(0)); d = vt[0]
        sites.append(dict(x=float(px[i]), z=float(pz[i]), w=w, dir=(float(d[0]), float(d[1]))))
    # tiles
    x0, z0, x1, z1 = region.bounds
    tiles = []
    info = dict(max_grade=round(lev.max_grade(), 4), piers=0, stations=[], tiles=0, clip_area_m2=round(RAIL.intersection(clip).area, 1),
                anchors={k: dict(level=(round(v[1], 2) if v[1] is not None else None), tag=v[2], note=v[3]) for k, v in STATIONS.items()})
    st_keys = [k for k, v in STATIONS.items() if v[4]]
    st_done = set()
    for ix in range(int(math.floor(x0 / TILE)), int(math.ceil(x1 / TILE))):
        for iz in range(int(math.floor(z0 / TILE)), int(math.ceil(z1 / TILE))):
            box = shapely.box(ix * TILE, iz * TILE, (ix + 1) * TILE, (iz + 1) * TILE)
            part = orient_all(rail_b.intersection(box).buffer(0))
            mine_st = [k for k in st_keys if k not in st_done and box.contains(ST_POLY[k].centroid)]
            if part.is_empty and not mine_st: continue
            c = (part if not part.is_empty else ST_POLY[mine_st[0]]).centroid
            key = f'airtrain_{ix}_{iz}'
            B = Bldg(key, f'AirTrain guideway tile {ix},{iz}', c.x, c.y, 'obs',
                     ['at_rail_polygon', 'at_section', 'at_station_domestic', 'at_stations', 'at_height_ext', 'at_height_general'],
                     dict(plan=dim('SFO Museum AirTrain Rail polygon', 'obs', 'BL-01 / BL-02'),
                          level=dim('station anchors (see airtrain_levels in the manifest), geodesic interpolation', 'inf', 'landside_airtrain.STATIONS'),
                          deck=dim(DECK_T, 'inf', 'app slab depth'), side_wall=dim(WALL_H, 'inf', 'photos l1 / l5')),
                     inferred=['guideway level between stations (interpolated)', 'deck depth %.1f m, side walls %.1f m' % (DECK_T, WALL_H),
                               'pier spacing %.0f m, column D %.1f / 2.4 m, cap %.1f m' % (PIER_DX, PIER_D, CAP_D)],
                     unknown=['station platform levels (see airtrain_levels)', 'enclosure / canopy heights'],
                     not_modelled=['running surfaces / centre guide beams (deck colour only)', 'railings, lamp posts',
                                   'stair / elevator towers of the terminal-area stations (positions not measured)',
                                   'Grand Hyatt enclosed bridge, LTP pedestrian bridge (positions not measured)'])
            F = B.F
            sh = MB(key + '_deck')
            if not part.is_empty:
                deck_shell(sh, F, part, lev)
            det0, det1 = MB(key + '_piers0'), MB(key + '_piers1')
            coarse = MB(key + '_L2')
            if not part.is_empty:
                deck_shell(coarse, F, part.simplify(0.6, preserve_topology=True), lev, walls=False, seg=12.0)
            n_p = 0
            for s in sites:
                if not box.contains(Point(s['x'], s['z'])): continue
                pier(det0, F, s, lev, 10); pier(det1, F, s, lev, 6); pier(coarse, F, s, lev, 4, cap_box=False); n_p += 1
            info['piers'] += n_p
            sdet0, sdet1 = MB(key + '_st0'), MB(key + '_st1')
            for k in mine_st:
                ex = (station_exclude or {}).get(k)
                info['stations'].append(station(sh, sdet0, F, k, lev, 0, ex))
                station(MB('tmp'), sdet1, F, k, lev, 1, ex)
                station(coarse, None, F, k, lev, 2, ex)
                st_done.add(k)
                if k == 'RCC':
                    rcc_tower(sh, F, 0); rcc_tower(coarse, F, 2)
            if sh.empty() and det0.empty(): continue
            B.shells.append(Part(key + '_deck', sh, 'shell', 'obs', 'guideway deck + trough walls on the SFO Museum polygon; stations',
                                 ['at_rail_polygon', 'at_section']))
            if not det0.empty():
                B.details[0].append(Part(key + '_piers', det0, 'detail', 'inf', 'single-column T-piers every %.0f m (inf)' % PIER_DX, ['at_section']))
                B.details[1].append(Part(key + '_piers', det1, 'detail', 'inf', 'piers (6-sided)', ['at_section']))
            if not sdet0.empty():
                B.details[0].append(Part(key + '_stdet', sdet0, 'detail', 'obs', 'station posts, X-bracing, platform-door cabins', ['at_station_domestic', 'at_section']))
                B.details[1].append(Part(key + '_stdet', sdet1, 'detail', 'obs', 'station posts', ['at_station_domestic']))
            B.coarse.append(Part(key + '_L2', coarse, 'coarse', 'obs', 'guideway deck (coarse), piers, station roofs', ['at_rail_polygon']))
            B.anchors = dict(piers=n_p, stations=mine_st)
            tiles.append(B)
    info['tiles'] = len(tiles)
    info['rcc_tower'] = dict(D=RCC_TOWER['D'], top=RCC_TOWER['top'], oas=RCC_TOWER['oas'], world=RCC_TOWER['world'])
    return tiles, info, lev


def _raster(lev, g):
    import cv2
    m = np.zeros(lev.mask.shape, np.uint8)
    f = lambda r: np.array([[(x - lev.x0) / RES - 0.5, (z - lev.z0) / RES - 0.5] for x, z in r], np.float32)
    for p in polys(g):
        cv2.fillPoly(m, [np.round(f(p.exterior.coords) * 8).astype(np.int32)], 1, shift=3)
        for h in p.interiors:
            cv2.fillPoly(m, [np.round(f(h.coords) * 8).astype(np.int32)], 0, shift=3)
    return m.astype(bool)
