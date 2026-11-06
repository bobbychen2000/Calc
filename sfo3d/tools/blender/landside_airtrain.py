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
import shapely.prepared
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
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
WALL_H = 0.9          # trough side wall above the running surface (= deck top): level with the walkway (photos l1 / l5) [obs, low];
#                       r1: was 1.1 m ("tall thick white trough walls")
WALL_T = 0.25         # side wall thickness [inf]
WALKWAY_H = 0.9       # emergency walkway between the two tracks of twin sections, above the running surface [obs l1]; handrails
#                       1.07 m above it (posts every 3 m, top + mid rail, galvanised) [obs l1 / l5; spacing inf]
PAD_W, PAD_H, PAD_OFF = 0.60, 0.12, 0.95   # concrete running pads under the rubber tyres: 0.6 m wide, 0.12 m high, +-0.95 m from the
#                                            track centre [obs l1 / l5 two pads + a centre guide rail; sizes inf]
PORTAL_H = 4.2        # clear height of the AirTrain portal into Garage A above the deck: CX-100 car ~3.4 m + headroom; photo l1
#                       shows a low opening at the track level [obs shape; height inf]
PIER_DX = 30.0        # pier spacing along the guideway [inf]; "single-column T-piers along the extension" [obs at_section]
PIER_D = 1.8          # pier column diameter (single track) [inf]; twin decks (width > 8 m): 2.4 m [inf]
CAP_D = 1.4           # pier cap depth below the deck [inf]
# close-out r3 (buildings-3): pier sites stay off the roads. b3d_integrate (2026-11-06 03:59Z) found 3 columns standing in road decks
# ((-1726.8, 427.2), (-1727.8, 530.2), (-1728.8, 456.2)) and caps 3.25 m over interchange_2_2 (8.6 m2 below 4.6 m): the pier sites
# were picked on the guideway skeleton only [inf]. Now a site is accepted only if its column (+ PIER_ROAD_CLEAR) touches no
# carriageway (data/sfo_landside.json roads, OSM centrelines buffered by their widths - at grade and elevated) and no road deck of
# data/buildings3d/roadways.glb (LOD0 deck tops), and its cap underside is >= CAP_ROAD_CLEAR above every deck under the cap; a
# rejected site no longer reserves its 30-m slot, so the next skeleton point is tried (spans may grow; reported in info).
PIER_ROAD_CLEAR = 0.5  # column face to a carriageway / deck edge [the finding: +0.5 m]
CAP_ROAD_CLEAR = 4.6   # cap underside over a road deck (Caltrans HDM 309.2, 15 ft; as tools/blender/roadways_net.CLEAR_MIN) [inf]
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
RCC_PLATFORM = 8.84  # review r2: the l5 tower-top silhouette fit (landside_r2_obs.json l5_rake, rms 2.3 px) puts the high point of the
#                      raked top on the near (north) side, 17.05 m from the camera instead of 19.4: with the top at the DOF value
#                      the eye / platform is 0.84 m higher than the r1 solve [obs l5 + DOF, low]
#                    RCC station platform [obs l5 + DOF, low] (round 1: the l5 camera solved from the tower and the guideway
#                      vanishing point, landside_r1_obs.json photos.l5_camera: tower top (DOF TANK 18.3) 8.6 m above the eye, eye
#                      1.7 m above the platform); was 5.8 [inf] with the BL-02 tower D 6.5 (which puts the l5 camera inside the
#                      RCC); BL-03 draws a 3/4-of-54-ft placeholder (12.35 m [unk])
LTP_LEVEL = 50 * FT  # Long-Term Parking station: the extension runs "50 feet above a public roadway" [pub]; LTP garage Level 5
#                      (bridge) [pub], height unknown

# key: (sfom id, deck-top level, tag, note, station type)  ('dom' glazed enclosure + single-pitch roof; 'barrel' / 'vault' white
# barrel roof over the platform (vault: and the tracks) [obs NAIP]; 'canopy' curved
# canopy + door cabins; None = no station built (inside another asset))
STATIONS = {
    'T1': (1729791955, CG_L5, 'unk', 'central garage Level 5 [pub], 4/5 of 81 ft (BL-03 placeholder)', 'barrel'),
    'T2': (1729791959, CG_L5, 'unk', 'central garage Level 5 [pub], 4/5 of 81 ft (BL-03 placeholder)', 'barrel'),
    'T3': (1729791957, CG_L5, 'unk', 'central garage Level 5 [pub], 4/5 of 81 ft (BL-03 placeholder)', 'barrel'),
    'ITB_A': (1729791961, ITB_L4, 'unk', 'ITB Level 4 [pub]; height placeholder inside the itb.glb core block', None),
    'ITB_G': (1729791965, ITB_L4, 'unk', 'ITB Level 4 [pub]; height placeholder inside the itb.glb core block', None),
    'GAR_A': (1729791949, NET_LEVEL, 'inf', 'Garage A Level 7 [pub]; network level (BL-03 placeholder 29.7 m deviates: grade)', None),
    'GAR_G': (1729791947, NET_LEVEL, 'inf', 'Garage G Level 7 [pub]; network level (BL-03 placeholder 28.2 m deviates: grade)', 'vault'),
    'HYATT': (1729791967, NET_LEVEL, 'inf', 'hotel 4th floor via an enclosed bridge [pub]; network level (40 m from Garage A station)', 'dom'),
    'WFR_IN': (1729791953, None, 'unk', 'West Field Road: no level source (interpolated)', 'canopy'),
    'WFR_OUT': (1729791951, None, 'unk', 'West Field Road: no level source (interpolated)', 'canopy'),
    'RCC': (1729791943, RCC_PLATFORM, 'inf', 'photo l5 (see RCC_PLATFORM); BL-03 placeholder 12.35 m [unk]', 'canopy'),
    'LTP': (1730051431, LTP_LEVEL, 'pub', '"50 feet above a public roadway" (extension) [pub]; LTP Level 5 bridge [pub]', 'canopy'),
}
import json as _json  # noqa: E402
_L5R = _json.load(open(os.path.join(HERE, 'landside_r2_obs.json')))['l5_rake']
RCC_TOWER = dict(D=4.7, top=None, centre=(-2280.5, -1073.7), rake=float(_L5R['rake']), high_bearing=float(_L5R['high_bearing']))
#   review r2 (finding 5): rake 2.55 m, highest toward bearing 353 (toward the l5 camera, north) - fitted to the photo-l5 top
#   silhouette (an arch highest mid-left, rms 2.3 px; r1's 2.5 m toward 236 deg gave a straight rising edge, rms 74 px)
#   D 4.7 at (-2280.5, -1073.7): the round lobe of the SFO Museum RCC station polygon (x -2282.8..-2278.1) [obs] - BL-02 E draws
#   D 6.5 [inf] at the DOF point (1.8 m east, inside the 1A +-6 m accuracy); the top cut by a raked plane, 2.5 m lower at the
#   front, highest toward bearing 236 deg (photo l5: the curved perforated hood rises to the right-back) [obs l5, low]; top = the DOF
#   TANK 60 ft [pub] (set below)


def struct_poly(sid):
    f = next(f for f in D.AIR['structures'] if f['id'] == sid)
    return unary_union([Polygon(p[0], p[1:]).buffer(0) for p in f['polys']])


RAIL = struct_poly(1779914099)
ST_POLY = {k: struct_poly(v[0]) for k, v in STATIONS.items()}
ITB_OUTLINE = unary_union([Polygon(p[0], p[1:]).buffer(0) for t in D.AIR['terminals'] if t['name'] == 'International Terminal'
                           for p in t['polys']])
_tk = next(d for d in D.LANDM['buildings']['rental_car_center']['dof'] if d['type'] == 'TANK')
RCC_TOWER['top'] = float(_tk['agl_m']); RCC_TOWER['world'] = list(RCC_TOWER['centre']); RCC_TOWER['dof_world'] = [float(v) for v in _tk['world']]
RCC_TOWER['oas'] = _tk['oas']


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
def deck_shell(mb, F, poly_w, lev, mat_top='guideway_deck', mat_side='guideway', walls=True, seg=4.0, open_line=None):
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
                if open_line is not None and open_line.distance(Point(*F.W(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])))) < 0.05:
                    s += L; continue          # cut by another asset (the deck continues inside it): no end face
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
                if open_line is not None and open_line.distance(Point(*F.W(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])))) < WALL_T + 0.05:
                    continue
                ha, hb = H(*a), H(*b)
                mb.face([(b[0], b[1], hb), (a[0], a[1], ha), (a[0], a[1], ha + WALL_H), (b[0], b[1], hb + WALL_H)], mat_side,
                        [(0, 0), (1, 0), (1, 0.3), (0, 0.3)])


BEAM_IN, BEAM_W, BEAM_H = 2.4, 0.22, 0.30   # centre guide rail: on the track centre line 2.4 m in from the deck edge (a 4.8-m single
#                                           track), 0.22 m wide, 0.30 m above the running surface (photos l1 / l5: a low steel guide /
#                                           power rail between the running pads; r1: was a 0.8-m beam that read as a wall) [obs, sizes inf]


def _strip(mb, F, lev, strip_w, z_off, h, mat, top_mat=None, seg=4.0, sides=True):
    """raised strip on the deck (world polygon) from the deck top + z_off to + z_off + h, following the level field."""
    from landside_mesh import tri_poly
    strip_w = orient_all(shapely.segmentize(strip_w, seg))
    Lp = F.poly(strip_w)
    H = lambda X, Y: float(lev.h(*F.W(X, Y)))
    for p in polys(Lp):
        if p.area < 0.2: continue
        for t in tri_poly(p):
            mb.face([(q[0], q[1], H(*q) + z_off + h) for q in t], top_mat or mat, [(q[0] / 4.0, q[1] / 4.0) for q in t])
        if not sides: continue
        for ring in rings_of(p):
            n = len(ring)
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-3: continue
                ha, hb = H(*a), H(*b)
                mb.face([(a[0], a[1], ha + z_off), (b[0], b[1], hb + z_off), (b[0], b[1], hb + z_off + h), (a[0], a[1], ha + z_off + h)], mat,
                        [(0, 0), (1, 0), (1, 0.2), (0, 0.2)])


def guide_beams(mb, F, poly_w, lev, seg=4.0, lod=0, rails=None):
    """track furniture (LOD0 / LOD1): centre guide rail (LOD0) + two running pads per track on the track centre lines (the deck
    boundary offset BEAM_IN inwards: single and twin sections alike); on twin sections the walkway between the tracks (the deck
    offset 3.7 m inwards, raised WALKWAY_H) with handrails on both edges (LOD0, into `rails`)."""
    inner = poly_w.buffer(-BEAM_IN, join_style=2)
    if inner.is_empty: return
    lines = inner.boundary
    clipz = poly_w.buffer(-1.2)
    if lod == 0:
        strip = orient_all(lines.buffer(BEAM_W / 2, cap_style=2, join_style=2).intersection(clipz).buffer(0))
        _strip(mb, F, lev, strip, 0.0, BEAM_H, 'guide_rail', seg=max(seg, 6.0))
    outer = lines.buffer(PAD_OFF + PAD_W / 2, cap_style=2, join_style=2).difference(lines.buffer(PAD_OFF - PAD_W / 2, cap_style=2, join_style=2))
    pads = orient_all(outer.intersection(poly_w.buffer(-0.35)).buffer(0))
    _strip(mb, F, lev, pads, 0.0, PAD_H, 'running_pad', seg=max(seg, 8.0), sides=False)     # 0.12-m pads: top faces only
    walk = poly_w.buffer(-3.7, join_style=2)
    walk = orient_all(walk.buffer(0.4, join_style=2).intersection(poly_w.buffer(-3.3, join_style=2)).buffer(0)) if not walk.is_empty else walk
    if walk.is_empty: return
    _strip(mb, F, lev, walk, 0.0, WALKWAY_H, 'walkway', top_mat='walkway', seg=seg)
    if lod != 0 or rails is None: return
    H = lambda X, Y: float(lev.h(*F.W(X, Y)))
    for p in polys(walk):
        if p.area < 4.0: continue
        for ring in [p.exterior] + list(p.interiors):
            ln = LineString(ring.coords).buffer(0).exterior if False else LineString(ring.coords)
            L = ln.length
            if L < 3.0: continue
            ts = np.arange(0.0, L, 3.0)
            pts = [ln.interpolate(t) for t in ts]
            # posts (two crossed quads) and two rails as thin vertical strips (doubleSided 'handrail')
            for q in pts:
                X, Y = F.L(q.x, q.y); h0 = H(X, Y) + WALKWAY_H
                for dx, dy in ((0.03, 0.0), (0.0, 0.03)):
                    rails.face([(X - dx, Y - dy, h0), (X + dx, Y + dy, h0), (X + dx, Y + dy, h0 + 1.07), (X - dx, Y - dy, h0 + 1.07)], 'handrail',
                               [(0, 0), (1, 0), (1, 1), (0, 1)])
            for i in range(len(pts)):
                q0, q1 = pts[i], pts[(i + 1) % len(pts)] if i + 1 < len(pts) else ln.interpolate(L)
                A = F.L(q0.x, q0.y); Bq = F.L(q1.x, q1.y)
                ha, hb = H(*A) + WALKWAY_H, H(*Bq) + WALKWAY_H
                for zr in (1.07, 0.55):
                    rails.face([(A[0], A[1], ha + zr - 0.05), (Bq[0], Bq[1], hb + zr - 0.05), (Bq[0], Bq[1], hb + zr), (A[0], A[1], ha + zr)], 'handrail',
                               [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])


def inter_walk(mb, rails, F, lev, walk_w, lod=0):
    """emergency walkways beside the single-track troughs east of the Garage A station (review r2, finding 1; photo l1: a narrow
    walkway ~1.5-2 m wide beside the camera's track with a galvanised cable rail on its open edge, open air below and beyond it):
    a 0.25-m slab cantilevered from the trough at the walkway level (+WALKWAY_H, level with the trough-wall tops), its open edge
    with posts every 1.5 m, a top rail and four cables [obs l1; post spacing / cable count from l1, low]. The strip between the
    walkways stays open (r1 had a 656-m2 deck at track level there)."""
    from landside_mesh import tri_poly
    walk_w = orient_all(walk_w.buffer(0))
    if walk_w.is_empty: return 0.0
    SL = 0.25
    _strip(mb, F, lev, walk_w, WALKWAY_H - SL, SL, 'walkway', top_mat='walkway', seg=4.0)
    H = lambda X, Y: float(lev.h(*F.W(X, Y)))
    Lp = F.poly(orient_all(shapely.segmentize(walk_w, 4.0)))
    for p in polys(Lp):
        if p.area < 0.2: continue
        for t in tri_poly(p):
            mb.face([(q[0], q[1], H(*q) + WALKWAY_H - SL) for q in t][::-1], 'guideway', [(q[0] / 4.0, q[1] / 4.0) for q in t][::-1])
    if lod != 0 or rails is None: return float(walk_w.area)
    rail_near = RAIL.buffer(0.3, join_style=2)
    for p in polys(walk_w):
        if p.area < 4.0: continue
        ring = np.array(p.exterior.coords)
        for i in range(len(ring) - 1):
            a, b = ring[i], ring[i + 1]
            Ls = float(np.hypot(*(b - a)))
            if Ls < 3.0: continue
            if rail_near.contains(Point(*(0.5 * (a + b)))): continue          # the edge against the trough: no rail
            ts = np.arange(0.2, Ls - 0.19, 1.5)
            d = (b - a) / Ls; nrm = np.array([d[1], -d[0]])
            if p.contains(Point(*(0.5 * (a + b) + nrm * 0.3))): nrm = -nrm
            pts = [a + d * t - nrm * 0.08 for t in ts] + [b - d * 0.2 - nrm * 0.08]
            for q in pts:
                X, Y = F.L(*q); h0 = H(X, Y) + WALKWAY_H
                for dx, dy in ((0.04, 0.0), (0.0, 0.04)):
                    rails.face([(X - dx, Y - dy, h0), (X + dx, Y + dy, h0), (X + dx, Y + dy, h0 + 1.07), (X - dx, Y - dy, h0 + 1.07)], 'handrail',
                               [(0, 0), (1, 0), (1, 1), (0, 1)])
            for j in range(len(pts) - 1):
                A_ = F.L(*pts[j]); B_ = F.L(*pts[j + 1])
                ha, hb = H(*A_) + WALKWAY_H, H(*B_) + WALKWAY_H
                for zr, th in ((1.07, 0.05), (0.85, 0.012), (0.65, 0.012), (0.45, 0.012), (0.25, 0.012)):
                    rails.face([(A_[0], A_[1], ha + zr - th), (B_[0], B_[1], hb + zr - th), (B_[0], B_[1], hb + zr), (A_[0], A_[1], ha + zr)],
                               'handrail', [(0, 0), (1, 0), (1, 0.1), (0, 0.1)])
    return float(walk_w.area)


def road_obstacles():
    """(carriageway + road-deck plan union, LOD0 deck-top triangles in world metres (N, 3, 3), source note) for the pier test."""
    import json, struct
    roads = json.load(open(os.path.join(ROOT, 'data', 'sfo_landside.json')))['roads']
    foot = [LineString(r['pts']).buffer(0.5 * float(r['w']), cap_style=2) for r in roads if len(r['pts']) >= 2 and r.get('w')]
    tris = np.zeros((0, 3, 3))
    path = os.path.join(ROOT, 'data', 'buildings3d', 'roadways.glb')
    if os.path.exists(path):
        data = open(path, 'rb').read(); clen = struct.unpack_from('<I', data, 12)[0]
        j = json.loads(data[20:20 + clen]); off = 20 + clen; blen = struct.unpack_from('<I', data, off)[0]; b = data[off + 8: off + 8 + blen]
        CT = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}; NC = {'SCALAR': 1, 'VEC3': 3}

        def acc(i):
            a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]; n = NC[a['type']]; dt = CT[a['componentType']]
            st = bv.get('byteOffset', 0) + a.get('byteOffset', 0); stride = bv.get('byteStride', 0)
            if stride and stride != n * np.dtype(dt).itemsize:
                raw = np.frombuffer(b, np.uint8, count=stride * a['count'], offset=st).reshape(a['count'], stride)
                return raw[:, :n * np.dtype(dt).itemsize].copy().view(dt).reshape(a['count'], n)
            return np.frombuffer(b, dt, count=a['count'] * n, offset=st).reshape(a['count'], n)

        def nmat(n):
            M = np.eye(4)
            if 'matrix' in n: return np.array(n['matrix']).reshape(4, 4).T
            x, y, z, w = n.get('rotation', [0, 0, 0, 1])
            R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                          [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
            M[:3, :3] = R @ np.diag(n.get('scale', [1, 1, 1])); M[:3, 3] = n.get('translation', [0, 0, 0]); return M
        mats = [m.get('name', '') for m in j.get('materials', [])]
        out = []

        def walk(i, M, lod):
            n = j['nodes'][i]; Mi = M @ nmat(n); nm = n.get('name', '')
            if nm.startswith('LOD') and nm[3:4].isdigit(): lod = int(nm[3])
            if 'mesh' in n and lod == 0:
                for pr in j['meshes'][n['mesh']]['primitives']:
                    if not mats[pr.get('material', 0)].startswith('deck'): continue
                    P = acc(pr['attributes']['POSITION']).astype(np.float64); P = (Mi[:3, :3] @ P.T).T + Mi[:3, 3]
                    T = P[acc(pr['indices']).ravel().astype(np.int64).reshape(-1, 3)]
                    nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); up = nn[:, 1] / (np.linalg.norm(nn, axis=1) + 1e-12) > 0.9
                    out.append(T[up])
            for c in n.get('children', []): walk(c, Mi, lod)
        for r in j['scenes'][j.get('scene', 0)]['nodes']: walk(r, np.eye(4), None)
        if out:
            tris = np.concatenate(out)
            foot.append(unary_union([Polygon(t[:, [0, 2]]).buffer(0.01) for t in tris]))
    return unary_union(foot), tris, 'data/sfo_landside.json roads + data/buildings3d/roadways.glb LOD0 deck tops (%d)' % len(tris)


def pier_conflict(x, z, w, d, h, obs, cols=None):
    """None if a pier at (x, z) (deck bottom h above grade, deck width w, guideway direction d) is clear of the roads, else the
    reason: 'column' (a column + PIER_ROAD_CLEAR on a carriageway / deck) or 'cap' (cap underside < CAP_ROAD_CLEAR over a deck).
    cols: column offsets across the guideway (None: one column on the centre line, the T-pier; else a straddle bent whose cap
    beam spans the columns)."""
    foot_p, tris, lo, hi = obs
    D_ = PIER_D if w < 8.0 else 2.4
    dl = np.array(d, float) / (np.linalg.norm(d) + 1e-12); n = np.array([-dl[1], dl[0]]); p = np.array([x, z], float)
    for o in (cols or [0.0]):
        if foot_p.intersects(Point(*(p + n * o)).buffer(D_ / 2 + PIER_ROAD_CLEAR, 16)): return 'column'
    if len(tris):
        a0, a1 = (-max(D_ + 0.6, w - 0.8) / 2, max(D_ + 0.6, w - 0.8) / 2) if not cols else (min(cols) - D_ / 2 - 0.3, max(cols) + D_ / 2 + 0.3)
        cap = Polygon([tuple(p + n * a + dl * c * 1.0) for a, c in ((a0, -1), (a1, -1), (a1, 1), (a0, 1))])
        x0, z0, x1, z1 = cap.bounds
        m = (hi[:, 0] > x0) & (lo[:, 0] < x1) & (hi[:, 1] > z0) & (lo[:, 1] < z1)
        zc = h - CAP_D
        for t in tris[m]:
            top = float(t[:, 1].max()) - 3.0                        # GROUND_Y 3.0
            if zc - top < CAP_ROAD_CLEAR and Polygon(t[:, [0, 2]]).buffer(0).intersects(cap): return 'cap'
    return None


STRADDLE_MAX = 18.0   # straddle-bent column offset limit from the guideway centre line [inf: ~36-m cap beams over a carriageway]


def straddle_cols(x, z, w, d, h, obs):
    """a straddle bent where a T-pier column would stand on a road: the nearest clear column position on each side of the
    guideway (0.5-m steps, between the deck edge and STRADDLE_MAX), whose cap beam clears every deck under it; None if none."""
    D_ = PIER_D if w < 8.0 else 2.4
    out = []
    for side in (-1.0, 1.0):
        hit = None
        for o in np.arange(w / 2 + D_ / 2 + 0.3, STRADDLE_MAX + 1e-6, 0.5):
            if pier_conflict(x, z, w, d, h, obs, cols=[side * o]) is None: hit = side * o; break
        if hit is None: return None
        out.append(float(hit))
    return out if pier_conflict(x, z, w, d, h, obs, cols=out) is None else None


def pier(mb, F, site, lev, sides=10, cap_box=True):
    """single-column T-pier: column from grade to the cap, cap beam across the deck under its bottom; or (close-out r3) a
    straddle bent: site['cols'] columns off the centre line and a cap beam spanning them under the deck."""
    x, z, w, d = site['x'], site['z'], site['w'], site['dir']
    h = float(lev.h(x, z)) - DECK_T
    if h < 3.0: return
    c = F.L(x, z)
    D_ = PIER_D if w < 8.0 else 2.4
    zc = h - CAP_D
    dl = np.array([d[0], -d[1]])            # world dir -> local XY (z south -> Y north)
    n = np.array([dl[1], -dl[0]])
    cols = site.get('cols')
    if cols:
        # local n = world (-d1, d0)? world n = (-d[1], d[0]) -> local (wx, -wz) = (-d[1], -d[0])
        nl = np.array([-d[1], -d[0]])
        for o in cols:
            q = (c[0] + nl[0] * o, c[1] + nl[1] * o)
            tube(mb, [(q[0], q[1], 0.0), (q[0], q[1], zc + 0.05)], D_ / 2, sides, 'guideway', tile=3.0)
        mid = np.array(c) + nl * 0.5 * (cols[0] + cols[1])
        L = abs(cols[1] - cols[0]) + D_ + 0.6
        boxm(mb, mid, nl, L, 2.0, (zc, h - 0.02), 'guideway', (4.0, 4.0), top=True, bottom=True)
        return
    tube(mb, [(c[0], c[1], 0.0), (c[0], c[1], zc + 0.05)], D_ / 2, sides, 'guideway', tile=3.0)
    if cap_box:
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
    # roof over the whole station polygon (minimum rectangle), single pitch (dom) or curved (canopy); 'vault' (Garage G / BART
    # station, round 1): one white barrel over the platform AND the tracks (NAIP 2024 white roof over both, photo a2) [obs]
    mr = P.minimum_rotated_rectangle
    if kind == 'vault':
        cs_ = np.array(mr.exterior.coords)[:4]; e0_, e1_ = cs_[1] - cs_[0], cs_[2] - cs_[1]
        if np.linalg.norm(e0_) < np.linalg.norm(e1_): cs_ = np.roll(cs_, -1, axis=0); e0_, e1_ = cs_[1] - cs_[0], cs_[2] - cs_[1]
        w_ = e1_ / np.linalg.norm(e1_) * 14.0
        band = Polygon([cs_[0] - w_, cs_[1] - w_, cs_[2] + w_, cs_[3] + w_])        # widened across only (not along the platform)
        mr = unary_union([P, RAIL.intersection(band)]).minimum_rotated_rectangle
        if exclude is not None and not exclude.is_empty:
            # keep the vault off the host garage: pull the long side nearest to it in until there is no overlap
            for _ in range(40):
                if mr.intersection(exclude).area < 0.5: break
                cs_ = np.array(mr.exterior.coords)[:4]; e0_, e1_ = cs_[1] - cs_[0], cs_[2] - cs_[1]
                if np.linalg.norm(e0_) < np.linalg.norm(e1_): cs_ = np.roll(cs_, -1, axis=0); e1_ = cs_[2] - cs_[1]
                u_ = e1_ / np.linalg.norm(e1_)
                side0 = Polygon([cs_[0], cs_[1], cs_[1] + u_ * 2, cs_[0] + u_ * 2]).intersection(exclude).area
                side1 = Polygon([cs_[3], cs_[2], cs_[2] - u_ * 2, cs_[3] - u_ * 2]).intersection(exclude).area
                if side0 >= side1: cs_[0] = cs_[0] + u_ * 0.25; cs_[1] = cs_[1] + u_ * 0.25
                else: cs_[2] = cs_[2] - u_ * 0.25; cs_[3] = cs_[3] - u_ * 0.25
                mr = Polygon(cs_)
    cs = np.array(mr.exterior.coords)[:4]
    e0, e1 = cs[1] - cs[0], cs[2] - cs[1]
    if np.linalg.norm(e0) < np.linalg.norm(e1):
        cs = np.roll(cs, -1, axis=0); e0, e1 = cs[1] - cs[0], cs[2] - cs[1]
    Lr, Wr = float(np.linalg.norm(e0)), float(np.linalg.norm(e1))
    ua, ub = e0 / Lr, e1 / Wr
    c0 = cs[0]
    if key == 'RCC':
        # the station polygon includes the stair-tower lobe; the canopy starts behind the tower (photo l5: open sky and the exit
        # cabin beside the tower, the curved roof beyond it) [obs l5, low]: trim the roof rectangle at the tower's far side + 0.6 m
        tu = float((np.array(RCC_TOWER['world']) - c0) @ ua); rt = RCC_TOWER['D'] / 2 + 0.6
        if tu < Lr / 2:
            cut_ = min(tu + rt, Lr - 6.0); c0 = c0 + ua * cut_; Lr -= cut_
        else:
            Lr = max(tu - rt, 6.0)
        # ... and across: nothing west of the tower at canopy height (l5: sky right of the tower; the canopy's west part is hidden
        # behind it) -> the canopy ends at the tower's centre line on the tower side
        tv = float((np.array(RCC_TOWER['world']) - c0) @ ub)
        if 0.0 < tv < Wr / 2:
            c0 = c0 + ub * tv; Wr -= tv
        elif Wr / 2 <= tv < Wr:
            Wr = tv
    loc = lambda u, v: F.L(*(c0 + ua * u + ub * v))
    zr0 = hz + ENCL_H
    if kind in ('vault', 'barrel'):
        # 'barrel' (review r2, finding 4): the T1 / T2 / T3 stations on the central garage carry white barrel roofs in NAIP 2024
        # (long rounded white roofs with a bright crown line) [obs NAIP], not flat boxes - same section as the Garage G vault
        # barrel vault across the station: eaves at the enclosure top, rise W / 8 [inf], 8 facets, 0.35-m roof, soffit; glazed
        # enclosure walls on the platform outline up to the vault soffit [obs a2: glazing under the white roof]
        nseg = 8; rise = Wr / 8.0
        vv = np.linspace(-0.6, Wr + 0.6, nseg + 1)
        zc = lambda v: zr0 + rise * math.sin(math.pi * min(max((v + 0.6) / (Wr + 1.2), 0), 1))
        for j in range(nseg):
            v0, v1 = vv[j], vv[j + 1]
            q = [(*loc(-0.6, v0), zc(v0) + 0.35), (*loc(Lr + 0.6, v0), zc(v0) + 0.35), (*loc(Lr + 0.6, v1), zc(v1) + 0.35), (*loc(-0.6, v1), zc(v1) + 0.35)]
            mb.face_dir(q, 'vault_roof', [(0, v0 / 3), (Lr / 6, v0 / 3), (Lr / 6, v1 / 3), (0, v1 / 3)], (0, 0, 1), smooth=True, grp=('vault', key))
            qd = [(*loc(-0.6, v0), zc(v0)), (*loc(-0.6, v1), zc(v1)), (*loc(Lr + 0.6, v1), zc(v1)), (*loc(Lr + 0.6, v0), zc(v0))]
            mb.face_dir(qd, 'station_soffit', [(0, v0 / 3), (0, v1 / 3), (Lr / 6, v1 / 3), (Lr / 6, v0 / 3)], (0, 0, -1))
        cu = np.array(loc(Lr / 2, Wr / 2))
        for u in (-0.6, Lr + 0.6):
            for j in range(nseg):
                v0, v1 = vv[j], vv[j + 1]
                a0, a1 = loc(u, v0), loc(u, v1)
                f = [(a0[0], a0[1], zc(v0)), (a1[0], a1[1], zc(v1)), (a1[0], a1[1], zc(v1) + 0.35), (a0[0], a0[1], zc(v0) + 0.35)]
                out = np.array(a0) - cu
                mb.face_dir(f, 'vault_roof', [(0, 0), (1, 0), (1, 0.05), (0, 0.05)], (out[0], out[1], 0))
                # gable glazing under the vault ends (above the enclosure / track clearance)
                g = [(a0[0], a0[1], zr0), (a1[0], a1[1], zr0), (a1[0], a1[1], zc(v1)), (a0[0], a0[1], zc(v0))]
                mb.face_dir(g, 'station_glass', [(0, 0), (1, 0), (1, 0.3), (0, 0.3)], (out[0], out[1], 0))
        for v in (vv[0], vv[-1]):
            a0, a1 = loc(-0.6, v), loc(Lr + 0.6, v)
            f = [(a0[0], a0[1], zc(v)), (a1[0], a1[1], zc(v)), (a1[0], a1[1], zc(v) + 0.35), (a0[0], a0[1], zc(v) + 0.35)]
            out = np.array(loc(Lr / 2, v)) - cu
            mb.face_dir(f, 'vault_roof', [(0, 0), (1, 0), (1, 0.05), (0, 0.05)], (out[0], out[1], 0))
        for p in plats:
            for q in polys(F.poly(p)):
                for ring in rings_of(q):
                    n = len(ring); s = 0.0
                    for i in range(n):
                        a, b = ring[i], ring[(i + 1) % n]
                        L = math.hypot(b[0] - a[0], b[1] - a[1])
                        if L < 0.5: continue
                        mb.face([(a[0], a[1], hz + 0.02), (b[0], b[1], hz + 0.02), (b[0], b[1], zr0), (a[0], a[1], zr0)], 'station_glass',
                                [(s / 3.0, 0), ((s + L) / 3.0, 0), ((s + L) / 3.0, (zr0 - hz) / 3.0), (s / 3.0, 0)])
                        s += L
        if det is not None:
            # vault ribs / posts along both long eaves every 6 m (LOD0 / LOD1)
            for v in (-0.3, Wr + 0.3):
                for u in np.arange(1.5, Lr - 1.0, 6.0):
                    c = loc(u, v)
                    boxm(det, c, (1, 0), 0.3, 0.3, (hz + 0.02, zr0), 'steel', (2.0, 2.0))
        return dict(key=key, sid=sid, level=round(hz, 2), tag=tag, note=note, kind=kind, roof=round(zr0, 2), crown=round(zr0 + rise + 0.35, 2),
                    L=round(Lr, 1), W=round(Wr, 1), rect=[[round(float(x), 2) for x in c0 + ua * u + ub * v] for u, v in ((0, 0), (Lr, 0), (Lr, Wr), (0, Wr))])
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
    """RCC station stair / elevator tower: free-standing cylinder of perforated metal (D 4.7 [obs SFO Museum polygon lobe]) to the
    DOF TANK 60 ft [pub; identity inf], its top cut by a raked plane (RCC_TOWER rake / high_bearing, fitted to photo l5), a
    see-through doubleSided expanded-mesh skin (alpha-blended 'perf_tower', review r2), frame rings and posts, and inside a dark
    stair core with switch-back flights and landings every 3 m [obs l5: the stair seen through the mesh; layout inf] -
    BL-02 E / BL-03 row 3."""
    c = F.L(*RCC_TOWER['world'])
    n = 28 if lod == 0 else (14 if lod == 1 else 10)
    r, top, rake = RCC_TOWER['D'] / 2, RCC_TOWER['top'], RCC_TOWER['rake']
    th_hi = math.radians(90.0 - RCC_TOWER['high_bearing'])          # bearing -> local XY angle (X east, Y north)
    ztop = lambda t: top - rake * (1 - math.cos(t - th_hi)) / 2
    ang = np.linspace(0, 2 * math.pi, n + 1)
    g = ('rcc_tower', lod)
    for i in range(n):
        t0, t1 = ang[i], ang[i + 1]
        a = (c[0] + r * math.cos(t0), c[1] + r * math.sin(t0)); b = (c[0] + r * math.cos(t1), c[1] + r * math.sin(t1))
        u0, u1 = r * t0 / 3.0, r * t1 / 3.0
        mb.face([(a[0], a[1], 0.0), (b[0], b[1], 0.0), (b[0], b[1], ztop(t1)), (a[0], a[1], ztop(t0))], 'perf_tower',
                [(u0, 0), (u1, 0), (u1, ztop(t1) / 3.0), (u0, ztop(t0) / 3.0)], True, g)
        if lod < 2:
            # frame rings every 3 m + the raked top ring (slightly proud, steel)
            for zr in list(np.arange(3.0, top - rake - 0.5, 3.0)):
                a2 = (c[0] + (r + 0.06) * math.cos(t0), c[1] + (r + 0.06) * math.sin(t0)); b2 = (c[0] + (r + 0.06) * math.cos(t1), c[1] + (r + 0.06) * math.sin(t1))
                mb.face([(a2[0], a2[1], zr), (b2[0], b2[1], zr), (b2[0], b2[1], zr + 0.15), (a2[0], a2[1], zr + 0.15)], 'steel', [(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
            a2 = (c[0] + (r + 0.06) * math.cos(t0), c[1] + (r + 0.06) * math.sin(t0)); b2 = (c[0] + (r + 0.06) * math.cos(t1), c[1] + (r + 0.06) * math.sin(t1))
            mb.face([(a2[0], a2[1], ztop(t0) - 0.2), (b2[0], b2[1], ztop(t1) - 0.2), (b2[0], b2[1], ztop(t1)), (a2[0], a2[1], ztop(t0))], 'steel',
                    [(0, 0), (1, 0), (1, 0.05), (0, 0.05)])
    # landing roof inside, below the lowest point of the rake (dark, seen through the open top)
    zl = top - rake - 0.6
    mb.face([(c[0] + (r - 0.05) * math.cos(t), c[1] + (r - 0.05) * math.sin(t), zl) for t in ang[:-1]], 'soffit', [(0.5, 0.5)] * n)
    if lod < 2:
        # r2: what the mesh shows inside (l5): a dark core (lift / stair well, 1.6 m square) and switch-back flights with landings
        # every 3 m, galvanised [obs l5; sizes inf]; posts between the frame rings every 1/8 turn
        boxm(mb, c, (1, 0), 1.6, 1.6, (0.0, zl), 'metal_dark', (2.0, 2.0), top=False)
        for zf in np.arange(0.0, zl - 0.1, 3.0):
            for side in (0, 1):
                ya, yb = (-1.6, 1.6) if side == 0 else (1.6, -1.6)
                xo = 1.2 if side == 0 else -1.2
                z0f, z1f = zf + 1.5 * side, zf + 1.5 * (side + 1)
                if z1f > zl: continue
                q = [(c[0] + xo - 0.4, c[1] + ya, z0f), (c[0] + xo + 0.4, c[1] + ya, z0f), (c[0] + xo + 0.4, c[1] + yb, z1f), (c[0] + xo - 0.4, c[1] + yb, z1f)]
                mb.face(q, 'handrail', [(0, 0), (1, 0), (1, 1), (0, 1)])
            mb.face([(c[0] - 1.1, c[1] + 0.8, zf + 1.5), (c[0] + 1.1, c[1] + 0.8, zf + 1.5), (c[0] + 1.1, c[1] + 2.0, zf + 1.5), (c[0] - 1.1, c[1] + 2.0, zf + 1.5)],
                    'handrail', [(0, 0), (1, 0), (1, 1), (0, 1)])
        for t in np.linspace(0, 2 * math.pi, 9)[:-1]:
            p_ = (c[0] + (r + 0.05) * math.cos(t), c[1] + (r + 0.05) * math.sin(t))
            boxm(mb, p_, (math.cos(t), math.sin(t)), 0.10, 0.18, (0.0, ztop(t) - 0.1), 'steel', (1.0, 1.0))


# ------------------------------------------------------------------------------------------------ assembly
def build(clip_world, building_outlines, Bldg, Part, dim, station_exclude=None, walks_world=None):
    """-> (list of Bldg tiles, info). clip_world: polygons where the guideway is NOT built (held by another asset / inside a
    building body); building_outlines: polygons where no pier is placed (the guideway is carried by the building);
    walks_world: walkway decks between the tracks (inter_walk, round 1)."""
    region = unary_union([RAIL] + [ST_POLY[k] for k in STATIONS])
    lev = Levels(region)
    clip = unary_union(clip_world) if clip_world else Polygon()
    rail_b = orient_all(RAIL.difference(clip).buffer(0))
    walks = orient_all(unary_union(walks_world).difference(RAIL.buffer(0.05, join_style=2)).difference(clip).buffer(0)) if walks_world else None
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
    # close-out r3 (buildings-3): the road test (road_obstacles / pier_conflict); rejected sites do not reserve their slot
    rfoot, rtris, rsrc = road_obstacles()
    obs = (shapely.prepared.prep(rfoot), rtris, rtris[:, :, [0, 2]].min(1) if len(rtris) else None, rtris[:, :, [0, 2]].max(1) if len(rtris) else None)
    rejected = dict(column=0, cap=0, straddle=0)
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
        if blocked.contains(Point(px[i], pz[i])):
            taken.setdefault((gx, gz), []).append((px[i], pz[i])); continue      # (as before r3: a building-held stretch keeps its slot)
        w = 2.0 * float(lev.dt[yy[i], xx[i]])
        near = pts_all[(np.abs(pts_all[:, 0] - px[i]) < 8) & (np.abs(pts_all[:, 1] - pz[i]) < 8)]
        if len(near) < 3:
            taken.setdefault((gx, gz), []).append((px[i], pz[i])); continue
        u, s_, vt = np.linalg.svd(near - near.mean(0)); d = vt[0]
        h_ = float(lev.h(px[i], pz[i])) - DECK_T
        if h_ >= 3.0:
            why = pier_conflict(float(px[i]), float(pz[i]), w, (float(d[0]), float(d[1])), h_, obs)
            if why == 'column':
                cols = straddle_cols(float(px[i]), float(pz[i]), w, (float(d[0]), float(d[1])), h_, obs)
                if cols:
                    taken.setdefault((gx, gz), []).append((px[i], pz[i]))
                    sites.append(dict(x=float(px[i]), z=float(pz[i]), w=w, dir=(float(d[0]), float(d[1])), cols=cols)); rejected['straddle'] += 1
                    continue
            if why: rejected[why] += 1; continue
        taken.setdefault((gx, gz), []).append((px[i], pz[i]))
        sites.append(dict(x=float(px[i]), z=float(pz[i]), w=w, dir=(float(d[0]), float(d[1]))))
    # tiles
    x0, z0, x1, z1 = region.bounds
    tiles = []
    info = dict(max_grade=round(lev.max_grade(), 4), piers=0, stations=[], tiles=0, clip_area_m2=round(RAIL.intersection(clip).area, 1),
                pier_road_test=dict(source=rsrc, rejected_candidates=rejected, column_clear_m=PIER_ROAD_CLEAR, cap_clear_m=CAP_ROAD_CLEAR,
                                    sites=[[round(s_['x'], 2), round(s_['z'], 2)] + ([round(v, 2) for v in s_['cols']] if s_.get('cols') else []) for s_ in sites]),
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
                          deck=dim(DECK_T, 'inf', 'app slab depth'), side_wall=dim(WALL_H, 'obs', 'photos l1 / l5 (level with the walkway) [low]')),
                     inferred=['guideway level between stations (interpolated)', 'deck depth %.1f m, side walls %.1f m' % (DECK_T, WALL_H),
                               'running pads %.2f x %.2f m at +-%.2f m, guide rail %.2f x %.2f m, twin walkway +%.1f m' % (PAD_W, PAD_H, PAD_OFF, BEAM_W, BEAM_H, WALKWAY_H),
                               'pier spacing %.0f m, column D %.1f / 2.4 m, cap %.1f m' % (PIER_DX, PIER_D, CAP_D)],
                     unknown=['station platform levels (see airtrain_levels)', 'enclosure / canopy heights'],
                     not_modelled=['walkways / railings of single-track sections', 'lamp posts, cable trays, power-rail details',
                                   'stair / elevator towers of the terminal-area stations (positions not measured)',
                                   'Grand Hyatt enclosed bridge, LTP pedestrian bridge (positions not measured)'])
            F = B.F
            sh = MB(key + '_deck')
            if not part.is_empty:
                deck_shell(sh, F, part, lev, open_line=clip.boundary if not clip.is_empty else None)
            det0, det1 = MB(key + '_piers0'), MB(key + '_piers1')
            trk0, trk1, rails0 = MB(key + '_track0'), MB(key + '_track1'), MB(key + '_rails0')
            coarse = MB(key + '_L2')
            if not part.is_empty:
                # LOD2 keeps the trough walls (review r1: the LOD2 tiles were 1.1 m low without them)
                deck_shell(coarse, F, part.simplify(0.6, preserve_topology=True), lev, walls=True, seg=12.0,
                           open_line=clip.boundary if not clip.is_empty else None)
            if not part.is_empty:
                guide_beams(trk0, F, part, lev, lod=0, rails=rails0)
                guide_beams(trk1, F, part, lev, seg=8.0, lod=1)
            if walks:
                wk = orient_all(walks.intersection(box).buffer(0))
                if not wk.is_empty and wk.area > 1.0:
                    info['walkway_m2'] = round(info.get('walkway_m2', 0.0) + inter_walk(sh, rails0, F, lev, wk, 0), 1)
                    inter_walk(coarse, None, F, lev, wk.simplify(0.6, preserve_topology=True), 2)
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
            if not trk0.empty():
                B.details[0].append(Part(key + '_track', trk0, 'detail', 'obs', 'running pads, low centre guide rail, twin-section walkway (photos l1 / l5)', ['at_section']))
                B.details[1].append(Part(key + '_track', trk1, 'detail', 'obs', 'running pads, walkway (LOD1)', ['at_section']))
            if not rails0.empty():
                B.details[0].append(Part(key + '_handrails', rails0, 'detail', 'obs', 'walkway handrails: galvanised posts every 3 m, top + mid rail [obs l1; spacing inf]', ['at_section']))
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
