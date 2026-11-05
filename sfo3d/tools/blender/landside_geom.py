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
#                            relief shift vs the outline's east edge, ~17-20 m) [obs NAIP, approx]; r1: the slab face behind the
#                            podium follows R1['hyatt_slab_east'] (continuous with the north part of the face, photo l4)

# ------------------------------------------------------------------------------------------------ round-1 review observations
# tools/blender/landside_r1_measure.py -> landside_r1_obs.json (NAIP 2024 plan positions / colours, numbers read off the
# reference photos; tags in that file's header). Not on the sheets yet: listed per building as 'r1_observations' and raised
# with the drawings group (docs/research/buildings3d.md).
import json as _json  # noqa: E402
R1 = _json.load(open(os.path.join(HERE, 'landside_r1_obs.json')))
_L1 = R1['photos']['l1_station_block']; _I2 = R1['photos']['i2_drums']
WALKWAY_H = 0.9            # AirTrain emergency walkway above the running surface (= the deck top of the model) [obs l1 / l5; inf]
STATION_BLOCK_H = WALKWAY_H + _L1['top_above_platform']        # Garage A station block top above the deck: 12.0 m [obs l1, low]
STATION_BLOCK_SLOT = WALKWAY_H + _L1['slot_centre_above_platform']   # slot centre above the deck: 7.4 m [obs l1, low]
STATION_BLOCK_D = 30.0     # block depth west of the east face: >= 27 m (sky above the block in l1, sightline) [inf]; the garage deck
#                            behind it stays the BL-03 placeholder at the drum ring [unk]
TOWER_W, TOWER_DP = 8.0, 8.0   # drum stair / elevator towers: 8 m along the face x 8 m deep [inf]; at both ends of each drum
#                                [obs i2 + NAIP bright boxes at the outline notches]; top = drum ring + 3.0 [obs i2, low]
SCREEN_COVER = 0.62        # perforated screen panels cover the lower 62 % of each parking level (dark open strip above) [obs l1]
SCREEN_MULL = 4.05         # screen panel width between thin steel mullions (two panels per 8.1-m bay) [obs l1]
BART_BAND_UP, BART_BAND_H = 4.1, 4.3   # BART station north face: glazed band top 4.1 m below the body top, 4.3 m tall [obs a2 with
#                                        the solved camera (r2): band 9.2-13.5 m under a 17.6-m body top at x 1100-1700; r1 read
#                                        1.6 / 3.9 from proportions of an unmatched view, which left a 53 % white spandrel below]
CG_RING_R = 43.5          # central garage: outer radius of the helix ring road round the void [obs NAIP 2024, 87-m ring, +-1.5 m]
CG_DECK_RGB = (229, 232, 227)  # central-garage deck median sRGB [obs NAIP 2024, build_landside naip_colours deck.central_garage]
CG_CAR_ALPHA = 0.5        # car share of a detected car blob's pixels (0.6-m NAIP, blob edges mixed with the deck) [inf]: the blob
#                           colour is un-mixed against the deck before choosing the nearest fleet colour (r1 render: mixed blob
#                           means mapped dark cars to beige / silver)

# ------------------------------------------------------------------------------------------------ round-2 review observations
# tools/blender/landside_r2_measure.py -> landside_r2_obs.json: Garage A / G heights from photo a2 with its SOLVED camera
# (out/buildings3d/itb_a2_camera.json), the i2 drum slots in level pitches, the BART band (a2), the RCC tower rake (l5), the
# central-garage rims / lobes with smooth outlines. Not on the sheets yet (BL-03 draws the garages at the NAIP drum ring 39.6 /
# 37.6 [obs, low] with the deck dotted [unk]): listed as deviations_from_sheets and raised with the drawings group.
R2 = _json.load(open(os.path.join(HERE, 'landside_r2_obs.json')))
_GA2 = R2['garages']
# Garages A / G (review r2, finding 2): a2 with the solved camera puts the near parapet edge at 29.1 m (A, 9 columns 28.85-29.5)
# and 27.5 m (G, 4 columns) - the drawn 39.6 / 37.6 land ~10 m too high (the garages' tops in the trees behind them); the a2 level
# rows (deep dark strips at 25.3 / 22.0 / 18.6 / 15.3 m over 270 px) give a 3.34-m pitch: 9 levels [pub] with L1 at grade put
# the roof deck at 8 x 3.34 = 26.7 m, the penthouse base sits on that deck line, and Level 7 (AirTrain [pub]) at 20.0 m (the
# network level 19.75 [inf]). Camera sensitivity: Grand Hyatt pick 40 / 48 m -> -2.4 / +2.4 m [obs a2, low].
GAR_R2 = {
    'garage_a': dict(parapet=float(_GA2['garage_a']['parapet']), pitch=float(_GA2['garage_a']['level_rows']['pitch']),
                     ring=float(_GA2['garage_a']['drum_ring'])),
    'garage_g': dict(parapet=float(_GA2['garage_g']['parapet']), pitch=None, ring=None),
}
for _k, _g in GAR_R2.items():
    _g['deck'] = 8 * _g['pitch'] if _g['pitch'] else None
GAR_R2['garage_g']['pitch'] = round(GAR_R2['garage_a']['pitch'] * GAR_R2['garage_g']['parapet'] / GAR_R2['garage_a']['parapet'], 3)   # same
#   design (one Tutor Perini contract for both, 9 levels each [pub]): Garage A's section scaled to G's measured parapet [inf]
GAR_R2['garage_g']['deck'] = 8 * GAR_R2['garage_g']['pitch']
GAR_R2['garage_g']['ring'] = round(GAR_R2['garage_g']['parapet'] + GAR_R2['garage_a']['ring'] - GAR_R2['garage_a']['parapet'], 2)    # [inf from A]
TOWER_ABOVE_PARAPET = 1.5  # drum stair / elevator towers: a2 (Garage A NNW tower top 0.7-2 m over the north face) / i2 (top level
#                            with the ring) [obs, low]; r1 read +3.0 above a 39.6 ring from i2 at the drum-width scale
I2_LEV = R2['i2']          # drum slots / top opening in level pitches below the ring top [obs i2]
DRUM_SLOT_H = 0.30         # slot height in level pitches (i2: ~10 px of 32) [obs i2, low]
PH_A = _GA2['garage_a']['penthouse']     # Garage A penthouse: open lower storey to 29.6, top 36.0 [obs a2]
ROT_A = _GA2['garage_a']['rotunda']      # Garage A NE rotunda: D 16.5, top 36.5 [obs a2 / NAIP, low]
NAIP_LEAN_GA = 13.25 / GAR_R2['garage_a']['ring']   # NAIP east lean per metre of height at Garage A: the drum band 13.25 m [obs] /
#                                                     the a2 ring 31.0 = 0.43 m/m (the ITB pole model's 0.334 does not hold here)
PH_BOX_IMG = ((-1462.0, 536.0), (-1440.0, 548.0))  # penthouse imaged in NAIP (draw_landside GAR box_img) [obs]: lean-corrected with
#                                                     the base (west face) at the deck and the top (east face) at the roof
BART_COLONNADE = 5.9       # BART station open ground storey top (a2 solved camera, 4 columns 5.4-6.1) [obs a2]; OSM min_height 4 [osm]


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


def holed_wall(mb, a, b, z0, z1, holes, mat, s0=0.0, tile=(3.0, 3.0), v0=0.0, grp=None, smooth=False):
    """vertical wall a -> b (outward = right) from z0 to z1 minus rectangular holes [(s_a, s_b, h0, h1)] (s along a -> b)."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if not holes:
        mb.quad_wall(a, b, z0, z1, z0, z1, mat, s0, tile, v0=v0, grp=grp, smooth=smooth); return
    ss = sorted({0.0, L} | {min(max(h[0], 0.0), L) for h in holes} | {min(max(h[1], 0.0), L) for h in holes})
    zz = sorted({z0, z1} | {min(max(h[2], z0), z1) for h in holes} | {min(max(h[3], z0), z1) for h in holes})
    d = (np.array(b, float) - np.array(a, float)) / L
    for i in range(len(ss) - 1):
        for j in range(len(zz) - 1):
            sm, zm = 0.5 * (ss[i] + ss[i + 1]), 0.5 * (zz[j] + zz[j + 1])
            if any(h[0] < sm < h[1] and h[2] < zm < h[3] for h in holes): continue
            pa = tuple(np.array(a) + d * ss[i]); pb = tuple(np.array(a) + d * ss[i + 1])
            mb.quad_wall(pa, pb, zz[j], zz[j + 1], zz[j], zz[j + 1], mat, s0 + ss[i], tile, v0=v0, grp=grp, smooth=smooth)


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


def garage_facade(mb, P, bands, style, tiles, recess=RECESS, gdetail=None, gdetail1=None):
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
        eb = clip_bands(st.get('bands', bands), st.get('z0', 0.0), st.get('z1', 1e9))
        if not eb: continue
        sm = bool(st.get('smooth'))
        grp_ = ('curve', st['solid']) if sm else None          # r2: shared vertices + smooth normals along smoothed curves
        if st['kind'] == 'solid':
            holed_wall(mb, a, b, eb[0][0], eb[-1][1], st.get('holes', []), st['solid'], s0, tiles[st['solid']], grp=grp_, smooth=sm)
            if st.get('recess'):
                # recessed openings behind holes (drum slots): back wall, sill, soffit (+ jambs at the run ends) [obs i2]
                dep, ends = st['recess'], st.get('recess_ends', (False, False))
                for (ha, hb, z0r, z1r) in st.get('holes', []):
                    pa_, pb_ = A + (B - A) / L * ha, A + (B - A) / L * hb
                    qa_, qb_ = pa_ - n * dep, pb_ - n * dep
                    mb.quad_wall(tuple(qa_), tuple(qb_), z0r, z1r, z0r, z1r, 'interior', 0.0, (4.0, 4.0))
                    uvq = [(0, 0), (1, 0), (1, 1), (0, 1)]
                    mb.face_dir([(*pa_, z0r), (*pb_, z0r), (*qb_, z0r), (*qa_, z0r)], 'sill', uvq, (0, 0, 1))
                    mb.face_dir([(*pa_, z1r), (*pb_, z1r), (*qb_, z1r), (*qa_, z1r)], 'soffit', uvq, (0, 0, -1))
                    d_ = (B - A) / L
                    if ends[0]:
                        mb.face_dir([(*pa_, z0r), (*qa_, z0r), (*qa_, z1r), (*pa_, z1r)], st['solid'], uvq, (d_[0], d_[1], 0))
                    if ends[1]:
                        mb.face_dir([(*pb_, z0r), (*qb_, z0r), (*qb_, z1r), (*pb_, z1r)], st['solid'], uvq, (-d_[0], -d_[1], 0))
            if st.get('slot_runs') and L > 2.0:
                # long dark window slots at given heights over given runs along the edge [(s_a, s_b, zc, h)] (photo l1)
                d = (B - A) / L
                for sa, sb, zc, hh in st['slot_runs']:
                    sa, sb = max(sa, 0.3), min(sb, L - 0.3)
                    if sb - sa < 0.8: continue
                    pa_, pb_ = A + d * sa + n * 0.02, A + d * sb + n * 0.02
                    gd.quad_wall(tuple(pa_), tuple(pb_), zc - hh / 2, zc + hh / 2, zc - hh / 2, zc + hh / 2, 'slot', 0.0, (3.0, hh))
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
                mb.quad_wall(a, b, z0, z1, z0, z1, st['solid'], s0, tiles[st['solid']], grp=grp_, smooth=sm)
        q = Polygon([A, B, B - n * recess, A - n * recess])
        if q.is_valid and q.area > 1e-3:
            ob = tuple((z0, z1) for z0, z1, k in eb if k == 'open')
            if ob:
                open_quads.append(q); zone_bands.setdefault(ob, []).append(q)
        dx = st['pier_dx']
        pw, pmat = st.get('pier_w', PIER_W), st.get('pier_mat', st['solid'])
        if sm and L <= 4.0:
            # smoothed curve (r2): mullions every pier_dx of arc length (s0 = arc length along the ring), panels run on
            d = (B - A) / L
            ss = np.array([t_ - s0 for t_ in np.arange(math.ceil(s0 / dx) * dx, s0 + L, dx) if 0.05 < t_ - s0 < L - 0.05])
            for s in ss:
                c = A + d * s
                p0, p1 = c - d * pw / 2, c + d * pw / 2
                q0, q1 = p0 + n * (SCREEN_OUT + 0.08), p1 + n * (SCREEN_OUT + 0.08)
                for z0, z1, kind in eb:
                    if kind == 'solid' and z1 >= eb[-1][1] - 1e-6: continue
                    gd.face_dir([(*q0, z0), (*q1, z0), (*q1, z1), (*q0, z1)], pmat, [(0, 0), (1, 0), (1, 1), (0, 1)], (n[0], n[1], 0))
        elif L > 4.0:
            k = max(1, int(round((L - 4.0) / dx)))
            ss = np.linspace(2.0, L - 2.0, k + 1)
            d = (B - A) / L
            for s in ss:
                c = A + d * s
                p0, p1 = c - d * pw / 2, c + d * pw / 2
                q0, q1 = (p0 - n * recess, p1 - n * recess) if not st.get('cover') else (p0 + n * (SCREEN_OUT + 0.08), p1 + n * (SCREEN_OUT + 0.08))
                for z0, z1, kind in eb:
                    if kind != 'open' and not st.get('cover'): continue
                    if st.get('cover'):
                        if kind == 'solid' and z1 >= eb[-1][1] - 1e-6: continue          # not over the top (parapet) band
                        # thin steel mullion in front of the screen line, over every band (photo l1: slim posts between panels)
                        gd.face_dir([(*q0, z0), (*q1, z0), (*q1, z1), (*q0, z1)], pmat, [(0, 0), (1, 0), (1, 1), (0, 1)], (n[0], n[1], 0))
                        gd.face_dir([(*p1, z0), (*q1, z0), (*q1, z1), (*p1, z1)], pmat, [(0, 0), (1, 0), (1, 1), (0, 1)], (d[0], d[1], 0))
                        gd.face_dir([(*p0, z0), (*q0, z0), (*q0, z1), (*p0, z1)], pmat, [(0, 0), (1, 0), (1, 1), (0, 1)], (-d[0], -d[1], 0))
                        continue
                    gd.quad_wall(tuple(p0), tuple(p1), z0, z1, z0, z1, pmat, s0 + s - pw / 2, tiles[pmat])
                    gd.quad_wall(tuple(p1), tuple(q1), z0, z1, z0, z1, pmat, 0.0, tiles[pmat])
                    gd.quad_wall(tuple(q0), tuple(p0), z0, z1, z0, z1, pmat, 0.0, tiles[pmat])
        else:
            ss, d = [], (B - A) / L
        if st['kind'] == 'screen' and (L > 0.8 or sm):
            # (r1 render: edges <= 4 m, e.g. on the curved garage ends, got no panels -> one panel over the whole edge)
            # r2: on smoothed curves the panels run on across the vertices (no inset, no end faces, shared normals)
            cuts = [0.0] + (list(ss) if not (sm and L <= 4.0) else []) + [L]
            gw = pw / 2 if not st.get('cover') else 0.02
            for i in range(len(cuts) - 1):
                end0 = 0.0 if sm else 0.15
                sa = cuts[i] + (gw if i > 0 else end0); sb = cuts[i + 1] - (gw if i < len(cuts) - 2 else end0)
                if sb - sa < (0.2 if sm else 0.5): continue
                pa = A + d * sa + n * SCREEN_OUT; pb = A + d * sb + n * SCREEN_OUT
                fa, fb = A + d * sa, A + d * sb
                for z0, z1, kind in eb:
                    if kind != 'open': continue
                    if st.get('cover'):
                        # full-bay perforated panel over the slab edge and the lower part of the level; dark strip above
                        za = z0 - 0.15; zb = za + st['cover'] * (z1 - z0 + 0.30); za = max(za, eb[0][0])
                    else:
                        za, zb = z0 + SCREEN_GAP, z1 - SCREEN_GAP
                    if zb - za < 0.6: continue
                    if sm:
                        # continuous panel band: u = arc length / the panel width (the texture's panel frame every SCREEN_MULL)
                        gd.quad_wall(tuple(pa), tuple(pb), za, zb, za, zb, 'screen', s0 + sa, (SCREEN_MULL, zb - za), v0=za, grp=('scr', round(za, 3)), smooth=True)
                        if gdetail1 is not None:
                            gdetail1.quad_wall(tuple(pa), tuple(pb), za, zb, za, zb, 'screen', s0 + sa, (SCREEN_MULL, zb - za), v0=za, grp=('scr', round(za, 3)), smooth=True)
                    else:
                        gd.quad_wall(tuple(pa), tuple(pb), za, zb, za, zb, 'screen', 0.0, (sb - sa, zb - za), v0=za)
                        if gdetail1 is not None:
                            gdetail1.quad_wall(tuple(pa), tuple(pb), za, zb, za, zb, 'screen', 0.0, (sb - sa, zb - za), v0=za)
                    uvq = [(0, 0), (1, 0), (1, 0.05), (0, 0.05)]
                    gd.face_dir([(pa[0], pa[1], zb), (pb[0], pb[1], zb), (fb[0], fb[1], zb), (fa[0], fa[1], zb)], 'screen_edge', uvq, (0, 0, 1))
                    gd.face_dir([(fa[0], fa[1], za), (fb[0], fb[1], za), (pb[0], pb[1], za), (pa[0], pa[1], za)], 'screen_edge', uvq, (0, 0, -1))
                    if not sm:
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


def deck_and_parapet(mb, P, deck_z, top_z, deck_mat, deck_uv, thk=PARAPET_T, coping='coping', cut=None):
    """parking roof: deck cap (stall texture through deck_uv) inside a parapet ring; returns the deck polygon. cut: local
    polygon left out of the deck cap (zones capped separately with their own material, e.g. the central-garage lobes)."""
    ring, inner = ring_band(P, thk)
    cap(mb, ring, top_z, coping, 1.0)
    for q in polys(inner):
        for r in rings_of(q):
            n = len(r)
            for i in range(n):
                a, b = r[i], r[(i + 1) % n]
                mb.quad_wall(b, a, deck_z, top_z, deck_z, top_z, coping, 0.0, (3.0, 3.0))
        qq = orient_all(q.difference(cut).buffer(0)) if cut is not None and not cut.is_empty else q
        for q2 in polys(qq):
            cap(mb, q2, deck_z, deck_mat, 6.0, uvf=deck_uv)
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


def stack_coarse(mb, P, top, wall_mat, roof_mat, tile=(6.0, 6.0), deck=None, thk=0.35):
    """LOD2 prism; with `deck` (review r2, finding 9): the roof at the LOD0 deck / roof level inside a parapet ring capped at
    `top` (the LOD2 roof had jumped 1.0-1.2 m to the parapet cap at the LOD switch)."""
    walls(mb, P, 0.0, top, wall_mat, tile)
    if deck is None or top - deck < 0.05:
        cap(mb, P, top, roof_mat, 12.0); return
    ring, inner = ring_band(P, thk)
    cap(mb, ring, top, 'coping', 3.0)
    for q in polys(inner):
        for r in rings_of(q):
            for i in range(len(r)):
                mb.quad_wall(r[(i + 1) % len(r)], r[i], deck, top, deck, top, 'coping', 0.0, (3.0, 3.0))
        cap(mb, q, deck, roof_mat, 12.0)


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
                      src='obs', deck_mat='deck', bands=None, lanes=False, ground_open=True, deck_cut=None):
    """shell (facades, recesses, deck, parapet) + LOD0 details (piers, screens) of an open parking structure."""
    tiles = tiles or TILES
    sh, det, det1 = MB(name), MB(name + '_piers'), MB(name + '_screens1')
    bands = bands or level_bands(slabs, top, ground_open=ground_open, deck=deck)
    garage_facade(sh, P, bands, style, tiles, gdetail=det, gdetail1=det1)
    inner = deck_and_parapet(sh, P, deck, top, 'deck_lanes' if lanes else deck_mat, deck_uvf(B.F, car_axis, deck_origin, lanes), cut=deck_cut)
    B.shells.append(Part(name, sh, 'shell', src, feature, spec, dims))
    if not det.empty():
        B.details[0].append(Part(name + '_piers', det, 'detail', 'inf', 'facade piers / perforated screens (module inf)', spec))
    if not det1.empty():
        B.details[1].append(Part(name + '_screens', det1, 'detail', 'obs', 'perforated screen panels (LOD1: flat panels)', spec))
    return inner, bands


TILES = {'precast': (6.0, 3.0), 'precast_band': (6.0, 1.6), 'concrete': (4.0, 4.0), 'concrete_board': (4.0, 2.4), 'screen': (3.0, 1.6),
         'screen_edge': (1.0, 1.0), 'interior': (6.0, 6.0), 'hangar_wall': (2.0, 2.0), 'moc_wall': (2.0, 2.0), 'glass_hyatt': (6.0, 3 * DL.GH_P),
         'metal_dark': (3.0, 3.0), 'podium': (3.0, 3.0), 'cac_wall': (3.0, 15 * FT), 'glass_band': (3.0, DL.GH_P / 3), 'coping': (3.0, 3.0),
         'ribbon': (3.0, 3.0), 'louvre': (3.0, 1.0), 'slot': (3.0, 1.2), 'drum_metal': (3.0, 1.5), 'precast_white': (4.0, 3.0),
         'bart_panel': (3.0, 3.0), 'glass_bart': (3.0, 2.95), 'roof_membrane': (8.0, 8.0), 'hangar_door': (8.375, 8.0), 'spine_wall': (3.0, 3.6), 'concrete_lt': (4.0, 4.0)}


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
             unknown=['what 81 ft measures', 'level heights (equal fifths)', 'facade module', 'roof rims: curb / planter / ramp edge (drawn 0.15 m)',
                      'rooftop box heights'],
             not_modelled=['the helix ring road round the void as a ramp (drawn flat at the deck)',
                           'other roof light poles (positions not measured)', 'DOF 06-039216 antenna 130 ft (4D: +-250 ft horizontal)',
                           'Level-3 skybridges to the terminals (domestic group)'])
    F = B.F
    P = F.poly(main_w)
    cut_b = cut.boundary

    vc = np.array(F.L(-930.8, 275.5)); pitch5 = top / 5

    def style(a, b):
        mid = Point(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
        wm = Point(*F.W(mid.x, mid.y))
        if cut_b.distance(wm) < 0.6:
            return dict(kind='open', pier_dx=PIER_DX['cg'], solid='concrete', z0=h5 + AT.WALL_H)
        rr = math.hypot(mid.x - vc[0], mid.y - vc[1])
        if rr < 35.0:
            # the void: the helix ramp coils round it [obs NAIP: ramp levels visible inside the void]: the level lines rise one
            # pitch (top / 5) per turn with the angle round the void centre (equal-fifths placeholder [unk])
            f = (math.atan2(mid.y - vc[1], mid.x - vc[0]) % (2 * math.pi)) / (2 * math.pi)
            hl = [pitch5 * (j + f) for j in range(5) if 0.8 < pitch5 * (j + f) < deck - 1.6]
            return dict(kind='open', pier_dx=PIER_DX['cg'] * 1.5, solid='concrete', bands=level_bands(hl, top, deck=deck))
        return dict(kind='open', pier_dx=PIER_DX['cg'], solid='concrete')
    rf = R1['cg_roof']
    rf2 = R2['cg_roof']          # r2 (finding 4): the same NAIP masks contoured smoothly (crisp curved bands, not pixel staircases)
    lobes_l = unary_union([Polygon([F.L(*p) for p in q]).buffer(0) for q in rf2['lobes']])
    # the helix ring road round the void: a stall-free light band to r = CG_RING_R [obs NAIP 2024: lane marks, moving cars,
    # no stalls; drawn flat at the deck]
    lobes_l = unary_union([lobes_l, Point(*vc).buffer(CG_RING_R, 64)])
    rims_l = unary_union([Polygon([F.L(*p) for p in q]).buffer(0) for q in rf2['rims']])
    deck_poly0 = ring_band(P, PARAPET_T)[1]
    lobes_l = orient_all(lobes_l.difference(rims_l).intersection(deck_poly0.buffer(-0.3)).buffer(0))
    rims_l = orient_all(rims_l.intersection(deck_poly0.buffer(-0.3)).buffer(0))
    inner, bands = parking_structure(B, P, top, deck, slabs, style, 117.8, tuple(mr['centre']), name='cg_body', tiles=TILES,
                                     feature='garage body: concrete spandrels, dark open levels, deck + parapet, helix void',
                                     spec=['cg_footprint', 'cg_void_obs', 'cg_height'], dims=B.dims, src='pub',
                                     deck_cut=unary_union([lobes_l, rims_l]))
    sh0 = B.shells[-1].mb
    # roof zones [obs NAIP 2024]: stall-free bright lobes (own material, flush with the deck) and the beige rims / curbs round them
    # (0.15 m raised [inf]: their nature - curb, planter, ramp edge - is not known)
    for q in polys(lobes_l):
        cap(sh0, q, deck, 'deck_plain', 8.0)
    for q in polys(rims_l):
        cap(sh0, q, deck + 0.15, 'deck_rim', 4.0)
        for r in rings_of(q):
            for i in range(len(r)):
                sh0.quad_wall(r[i], r[(i + 1) % len(r)], deck, deck + 0.15, deck, deck + 0.15, 'deck_rim', 0.0, (2.0, 2.0))
    # the void floor at grade: a parking surface with stall marks [obs NAIP 2024: stalls and a few cars inside the void; its
    # level from the south-wall shadow / relief lean ~ grade, low] (was open to the ground below)
    for q in polys(P):
        for hr in q.interiors:
            hp = Polygon(hr)
            if hp.area > 1000.0 and hp.distance(Point(*vc)) < 1.0:
                cap(sh0, orient_all(hp.buffer(0.3)), 0.03, 'void_floor', 6.0)
    # rooftop stair / elevator heads and plant groups [obs NAIP plan, +-2 m; heights inf]
    bxm = MB('cg_roof_boxes'); boxes = []
    for bx in rf['boxes']:
        x0, z0, x1, z1 = bx['rect']
        q = orient_all(Polygon([F.L(x0, z0), F.L(x1, z0), F.L(x1, z1), F.L(x0, z1)]).intersection(deck_poly0.buffer(-0.5)))
        if q.is_empty or q.area < 4.0: continue
        q = largest(q)
        h = deck + bx['above_deck']
        walls(bxm, q, deck, h, 'concrete' if bx['kind'] == 'tower' else 'steel', TILES['concrete'])
        cap(bxm, q, h, 'cg_box_roof', 4.0)           # NAIP 2024 median colour of the box roofs (dark grey) [obs]
        boxes.append(dict(kind=bx['kind'], top=round(h, 2), area=round(q.area, 1), note=bx['note'], poly=q))
    B.shells.append(Part('cg_roof_boxes', bxm, 'shell', 'obs', 'rooftop stair / elevator heads and plant groups (NAIP 2024 plan [obs]; '
                         'heights inf: %s)' % R1['cg_boxes_note'], ['cg_roof_cars']))
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
    excl_cg = [Point(F.L(*p['world'])).buffer(1.5) for p in poles.values()] + [b_['poly'].buffer(1.2) for b_ in boxes] + \
              [lobes_l.buffer(0.5), rims_l.buffer(0.8), Point(*vc).buffer(56.0)]
    pos = []
    for cr in rf['cars']:
        xl, yl = F.L(cr['x'], cr['z'])
        hdg = cr['hdg']
        pos.append((xl, yl, math.atan2(*loc_dir(hdg)[::-1]), tuple(cr['rgb'])))
    B.decks.append(dict(poly=inner, z=deck, axis=117.8, origin=tuple(mr['centre']), key=k, positions=pos, extra_share=0.37 / 0.63, snap=3.0,
                        unmix=(CG_DECK_RGB, CG_CAR_ALPHA),
                        count_src='cg_roof_cars: %d dark / coloured cars at their NAIP 2024 positions [obs] + white / silver cars (not separable '
                                  'from the light deck) by the fleet share 37 %% next to the detected clusters [inf]; spec visual 300 +-100' % len(pos),
                        axis_src='r2: every car snapped to the nearest free stall of the deck layout (axis 117.8 deg [obs NAIP rows], <= 3 m) - the '
                                 'per-blob NAIP headings are noise at 0.5 m/px (deviation from the stall axis: median 18, p90 42 deg = uniform random); '
                                 'NAIP position and colour kept [obs]',
                        exclude=excl_cg))
    B.anchors_r1 = dict(lobes_m2=round(lobes_l.area, 1), rims_m2=round(rims_l.area, 1), boxes=[{k_: v for k_, v in b_.items() if k_ != 'poly'} for b_ in boxes],
                        cars_naip=len(pos))
    cm2 = MB('cg_L2')
    P2 = P.simplify(0.8)
    walls(cm2, P2, 0.0, top, 'concrete', (6.0, 6.0))
    ring2, inner2 = ring_band(P2, PARAPET_T)
    cap(cm2, ring2, top, 'coping', 3.0)
    for q in polys(inner2):
        for r in rings_of(q):
            for i in range(len(r)):
                cm2.quad_wall(r[(i + 1) % len(r)], r[i], deck, top, deck, top, 'coping', 0.0, (3.0, 3.0))
        cap(cm2, q, deck, 'deck_far', 12.0)
    for b_ in boxes:
        walls(cm2, b_['poly'].simplify(0.3), deck, b_['top'], 'concrete', (6.0, 6.0)); cap(cm2, b_['poly'].simplify(0.3), b_['top'], 'coping', 6.0)
    for q in polys(under):
        stack_coarse(cm2, F.poly(q).simplify(0.8), zt, 'concrete', 'concrete')
    # r2 (finding 9): the LOD2 keeps the void floor at grade, the garage edge beside the guideway (to the trough-wall top, the
    # Level-5 parts) and the two DOF roof poles (the LOD2 top was 28.1 m without them)
    for q in polys(P):
        for hr_ in q.interiors:
            hp_ = Polygon(hr_)
            if hp_.area > 1000.0 and hp_.distance(Point(*vc)) < 1.0:
                cap(cm2, orient_all(hp_.buffer(0.3).simplify(0.5)), 0.03, 'void_floor', 12.0)
    for q in slivers_w:
        stack_coarse(cm2, F.poly(q).simplify(0.5), h5 + AT.WALL_H, 'concrete', 'coping')
    for p_ in poles.values():
        c_ = F.L(*p_['world'])
        boxm(cm2, c_, (1, 0), 0.45, 0.45, (deck, p_['top']), 'steel', (1.0, 1.0))
    B.coarse.append(Part('cg_L2', cm2, 'coarse', 'pub', 'central garage (coarse): body, deck, boxes, void floor, Level-5 edges, poles', ['cg_footprint']))
    B.footprint_w = full; B.top = top
    B.anchors = dict(r1=B.anchors_r1, parapet_top=round(top, 3), deck=round(deck, 3), level5=round(h5, 3), levels=[round(z, 3) for z in slabs],
                     void_centre=[-930.8, 275.5], poles=poles, main_area=round(main_w.area, 1), under_area=round(under.area, 1),
                     sliver_area=round(sum(p.area for p in slivers_w), 1))
    return B


# ================================================================================================ Garages A / G
def screen_bands(slabs, top, deck):
    """bands of a screened parking face (photo l1): a thin slab-edge band (0.3 m) at every level line, open between (the
    perforated panels of garage_facade's cover mode hang over the lower SCREEN_COVER of each level), solid from the deck
    slab to the parapet top."""
    out, z = [], 0.0
    for zl in slabs:
        if zl - 0.15 > z + 0.05: out.append((z, zl - 0.15, 'open'))
        out.append((zl - 0.15, zl + 0.15, 'solid')); z = zl + 0.15
    if deck - SPANDREL_DN > z + 0.05: out.append((z, deck - SPANDREL_DN, 'open'))
    out.append((deck - SPANDREL_DN, top, 'solid'))
    return out


def smooth_arcs(P, tol=0.6, chord=1.2, max_turn=24.0, min_total=30.0):
    """replace runs of outline vertices that follow a circle (consecutive turns < max_turn deg of one sign, total >= min_total,
    circle-fit residual < tol m) by the fitted arc sampled every <= chord m (review r2, finding 8: the SFO Museum outline gives
    the curved garage ends as a few long chords -> visibly faceted walls and box-like screen panels). -> (polygon, [arc
    LineStrings])."""
    ring = np.array(P.exterior.coords)[:-1]; n = len(ring)
    if n < 6: return P, []
    d_in = ring - np.roll(ring, 1, 0); d_out = np.roll(ring, -1, 0) - ring
    turn = np.degrees(np.arctan2(d_in[:, 0] * d_out[:, 1] - d_in[:, 1] * d_out[:, 0], (d_in * d_out).sum(1)))
    smooth = (np.abs(turn) < max_turn) & (np.abs(turn) > 0.5)
    if smooth.all() or not smooth.any(): return P, []
    st = int(np.argmin(smooth))                   # start the scan at a corner
    runs, cur = [], []
    for j in range(1, n + 1):
        i = (st + j) % n
        if smooth[i] and (not cur or np.sign(turn[i]) == np.sign(turn[cur[-1]])): cur.append(i)
        else:
            if len(cur) >= 2: runs.append(cur)
            cur = [i] if smooth[i] else []
    if len(cur) >= 2: runs.append(cur)
    new, arcs, done = [], [], {}
    for run in runs:
        if abs(turn[run].sum()) < min_total: continue
        ok = False
        for idx_ in ([(run[0] - 1) % n] + run + [(run[-1] + 1) % n], run):      # with the bounding corners, else between run ends
            Q = ring[idx_]
            if len(Q) < 3: continue
            A_ = np.c_[2 * Q[:, 0], 2 * Q[:, 1], np.ones(len(Q))]
            sol = np.linalg.lstsq(A_, Q[:, 0] ** 2 + Q[:, 1] ** 2, rcond=None)[0]
            cc = sol[:2]; R_ = float(np.sqrt(sol[2] + cc @ cc))
            if np.max(np.abs(np.hypot(*(Q - cc).T) - R_)) <= tol and R_ <= 200:
                ok = True; break
        if not ok: continue
        if len(idx_) == len(run):                     # arc between the run's end vertices: keep them as vertices
            run = run[1:-1]
            if not run: continue
        t0 = math.atan2(*(Q[0] - cc)[::-1]); t1 = math.atan2(*(Q[-1] - cc)[::-1])
        sgn = 1.0 if turn[run[0]] > 0 else -1.0
        dt = (t1 - t0) % (2 * math.pi) if sgn > 0 else -((t0 - t1) % (2 * math.pi))
        m = max(2, int(math.ceil(abs(dt) * R_ / chord)))
        pts = [tuple(cc + R_ * np.array([math.cos(t0 + dt * q / m), math.sin(t0 + dt * q / m)])) for q in range(1, m)]
        done[run[0]] = (run, pts)
        arcs.append(LineString([tuple(Q[0])] + pts + [tuple(Q[-1])]))
    skip = {i for run, _ in done.values() for i in run}
    for i in range(n):
        if i in done: new += done[i][1]
        elif i not in skip: new.append(tuple(ring[i]))
    Pn = Polygon(new).buffer(0)
    if not Pn.is_valid or Pn.is_empty or abs(Pn.area - P.area) > 0.03 * P.area: return P, []
    return orient_all(largest(Pn)), arcs


def drum_arc_ends(ring, circ, tol=0.8):
    """indices (i0, i1) of the first / last vertex of the longest run of ring vertices on the fitted drum circle."""
    c = np.array(circ['c']); R = circ['R']; n = len(ring)
    on = [abs(math.hypot(p[0] - c[0], p[1] - c[1]) - R) < tol for p in ring]
    best, cur = (0, -1, -1), None
    for k in range(2 * n):
        i = k % n
        if on[i]:
            cur = (cur[0], k) if cur else (k, k)
            if cur[1] - cur[0] > best[0]: best = (cur[1] - cur[0], cur[0] % n, cur[1] % n)
        else:
            cur = None
    return best[1], best[2]


def ring_walk(ring, i, step, dist):
    """point at arc length `dist` from ring[i] walking in direction step (+1 / -1)."""
    n = len(ring); p = np.array(ring[i], float); left = dist; j = i
    for _ in range(n):
        q = np.array(ring[(j + step) % n], float); L = float(np.hypot(*(q - p)))
        if L >= left: return p + (q - p) / max(L, 1e-9) * left
        left -= L; p = q; j = (j + step) % n
    return p


def drum_towers(body_w, circ):
    """stair / elevator towers at both ends of the drum (photo i2; NAIP bright boxes at the outline notches): a TOWER_W x
    TOWER_DP square at each arc end along the adjacent outline (away from the drum), inside the body, off the guideway."""
    ring = [tuple(p) for p in list(orient_all(body_w).exterior.coords)[:-1]]
    i0, i1 = drum_arc_ends(ring, circ)
    out = []
    for i, step in ((i0, -1), (i1, +1)):
        E = np.array(ring[i], float); Q = ring_walk(ring, i, step, TOWER_W)
        d = (Q - E) / max(float(np.hypot(*(Q - E))), 1e-9); m = np.array([-d[1], d[0]])
        if not body_w.contains(Point(*(E + d * TOWER_W / 2 + m * 1.0))): m = -m
        sq = Polygon([E, E + d * TOWER_W, E + d * TOWER_W + m * TOWER_DP, E + m * TOWER_DP])
        t = largest(sq.intersection(body_w).difference(RAIL.buffer(1.0, join_style=2)))
        if t.area > 20.0: out.append(orient_all(t.simplify(0.05)))
    return out


def garage_ag(k):
    """International Garage A / G (BL-02 panel B, BL-03 rows 1-2): the garage body (outline up to u = Lb), the helix drum
    (outline arc at the west end), core cylinder and Garage A rooftop box; deck at the drum ring (dotted on BL-03) [unk].
    Round 1 (review): drum in smooth metal panels with five long horizontal slots and an open top band [obs i2], screens as
    full-bay perforated panels between thin mullions [obs l1], white precast stair / elevator towers at both drum ends [obs
    i2 / NAIP], the Garage A station block as a lower block over the tracks with two long slots, open under its soffit over
    the tracks and on columns to the south [obs l1]."""
    g = DL.GAR[k]; G = DL.ggeom(k); r2 = GAR_R2[k]
    # review r2 (finding 2): heights from photo a2 with its solved camera (GAR_R2) instead of the BL-03 drum-ring placeholder
    hd_sheet = float(g['drum'])
    hd = r2['parapet']; hr = r2['ring']; deck = r2['deck']; pitch = r2['pitch']
    c, a, b, L, Lb = G['c'], G['a'], G['b'], G['L'], G['Lb']
    o = c + a * (Lb / 2 - L / 2)
    nm = 'International Garage A (Bldg 95)' if k == 'garage_a' else 'International Garage G (Bldg 495)'
    zt = AT.NET_LEVEL
    h7_sheet = hd_sheet * 6 / 8
    # drum slots / top opening one per level below the ring top (i2, in level pitches) [obs i2, low]
    slots_z = [(hr - (cz + DRUM_SLOT_H / 2) * pitch, hr - (cz - DRUM_SLOT_H / 2) * pitch) for cz in I2_LEV['slot_centres_below_ring']]
    top_open = (hr - (I2_LEV['top_opening_below_ring'][1] + DRUM_SLOT_H / 2) * pitch, hr - (I2_LEV['top_opening_below_ring'][0] - DRUM_SLOT_H / 2) * pitch)
    tower_top = hd + TOWER_ABOVE_PARAPET
    blk_top = hd                                     # r2: the station block reaches the parapet top (a2: nothing above the roof
    #                                                  at the SE corner; NAIP: the roof deck with stalls runs over it)
    B = Bldg(k, nm, o[0], o[1], 'obs', [f'{k}_footprint', f'{k}_height', f'{k}_levels', f'{k}_airtrain_level', 'garage_ag_facade', f'{k}_roof_cars'],
             dict(footprint=dim('SFO Museum outline up to u = %.1f (garage body)' % Lb, 'obs', 'BL-02 B / draw_landside.ggeom'),
                  parapet_top=dim(round(hd, 2), 'obs', 'photo a2, solved camera: near parapet edge %s (%d columns) [obs a2, low; +-2.4 m '
                                  'with the Hyatt pick 40-48 m]; BL-03 draws the NAIP drum ring %.1f m (%s)' %
                                  (_GA2[k]['parapet_spread'], _GA2[k]['parapet_n'], hd_sheet, g['drum_rng'])),
                  deck=dim(round(deck, 2), 'obs' if k == 'garage_a' else 'inf', 'roof deck = Level 9 = 8 x %.2f m (a2 level rows, L1 at grade)%s' %
                           (pitch, '' if k == 'garage_a' else ' - Garage A section scaled to the measured parapet')),
                  levels=dim('9 [pub] at %.2f m (a2 level rows %s)' % (pitch, _GA2['garage_a']['level_rows']['h']), 'obs' if k == 'garage_a' else 'inf', 'photo a2'),
                  drum_ring=dim(round(hr, 2), 'obs' if k == 'garage_a' else 'inf', 'photo a2: the drum ring wall rises ~1.9 m over the parapet (Garage A) [low]'),
                  drum=dim(dict(centre=[round(float(G['drum_c'][0]), 2), round(float(G['drum_c'][1]), 2)], D=round(2 * G['R'], 1)), 'obs',
                           'circle fit to the outline arc (BL-02 B)'),
                  drum_slots=dim(dict(slots=[[round(z0, 2), round(z1, 2)] for z0, z1 in slots_z], top_opening=[round(v, 2) for v in top_open]), 'obs',
                                 'photo i2 (five long horizontal slots + an open top band; heights scaled from the drum width) [obs, low]'),
                  towers=dim(dict(top=round(tower_top, 2), size=[TOWER_W, TOWER_DP]), 'obs/inf',
                             'stair / elevator towers at both drum ends: positions obs NAIP / i2, size inf (i2: 85 px = 8.9 m), top = parapet + %.1f [obs a2 / i2, low]' % TOWER_ABOVE_PARAPET),
                  core=dim(dict(D=DL.GAR_CORE_D, top=round(deck + PARAPET_H, 2)), 'obs', 'D ~13 m [obs NAIP dark disc = the helix eye]; a2 / i2: nothing rises above the '
                           'drum ring -> a guard ring round the eye (r1 drew a 4-m cylinder above the ring)'),
                  airtrain_level=dim(round(zt, 2), 'inf', 'network level (landside_airtrain.NET_LEVEL); BL-03 placeholder %.1f m' % h7_sheet),
                  long_face_m=dim(round(Lb, 1), 'obs', 'garage body to the start of the guideway tail')),
             inferred=['deck = drawn parapet top - 1.07 m guard', 'facade module: perforated screen panels %.2f m wide between thin steel mullions, '
                       'covering the lower %.0f %% of each level (photo l1), thin slab-edge bands' % (SCREEN_MULL, 100 * SCREEN_COVER),
                       'drum: smooth metal panels, slots recessed 0.8 m (dark interior)', 'stair / elevator towers %.0f x %.0f m' % (TOWER_W, TOWER_DP)],
             unknown=['absolute height scale of a2: the camera rests on the Grand Hyatt top 44 m [inf] (40 / 48 m -> -2.4 / +2.4 m)',
                      'level heights other than the a2 rows (L1 at grade, equal pitch)'] + ([] if k == 'garage_a' else ['Garage G deck / ring: Garage A section scaled']),
             conflicts=['NAIP drum band %.2f m east lean / ITB pole k -> drum ring %.1f m (BL-03) vs photo a2 (solved camera) %.1f m: implies a NAIP '
                        'lean of %.2f m/m here (the ITB pole model 0.33 does not transfer: different NAIP frame?)' % (13.25 if k == 'garage_a' else 12.0, hd_sheet, hr,
                                                                                                                       (13.25 if k == 'garage_a' else 12.0) / hr)] +
                       (['photo l1 station block top 11.1 m above the walkway (31.75 m, door-cabin scale +-15 %%) vs a2: no block above the %.1f-m '
                         'parapet at the SE corner -> block top = parapet' % hd] if k == 'garage_a' else []),
             not_modelled=['roof light poles (positions not measured)'],
             deviations=['AirTrain level %.2f m (network level) instead of the BL-03 Level-7 placeholder %.1f m (6/8 of the drum ring, [unk]): '
                         'the Grand Hyatt station is 40 m along the same track; %.2f m is inside the sheet\'s own [inf] range 18.3-21.0 m'
                         % (zt, h7_sheet, zt),
                         'review r2: parapet %.2f / drum ring %.2f / deck %.2f m from photo a2 (solved camera) instead of the BL-03 drum ring %.1f m [obs, low]'
                         % (hd, hr, deck, hd_sheet)])
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
    body_w, arcs_w = smooth_arcs(body_w)            # r2: curved drum / NE end as 1.2-m chords (smooth facades)
    if not g['rail_near']:
        body_w = orient_all(largest(body_w.difference(RAIL.buffer(0.4, join_style=2))))     # the arcs stay off the guideway
    arcs_u = unary_union(arcs_w) if arcs_w else None
    circ = dict(c=[float(G['drum_c'][0]), float(G['drum_c'][1])], R=float(G['R']))
    towers_w = drum_towers(body_w, circ)
    # Garage A station block (photo l1): the part of the body south of the station polygon's north edge (b <= st_b max) within
    # STATION_BLOCK_D of the east face
    blk_w = Polygon()
    if g['rail_near']:
        # north edge: 0.4 m north of the north track at the east face (photo l1: the curved NE garage wall starts there)
        eastx = [np.array(q.coords) for q in getattr(body_w.exterior.intersection(RAIL.buffer(0.2)), 'geoms', [])
                 if q.geom_type == 'LineString' and q.length > 2.0]
        bs = [float((p_ - c) @ b) for q in eastx for p_ in q if float((p_ - c) @ a + L / 2) > Lb - 5]
        bn = (max(bs) + 0.4) if bs else G['st_b'][1]
        zone = Polygon([c + a * (Lb - STATION_BLOCK_D - L / 2) + b * bn, c + a * (Lb - L / 2 + 5) + b * bn,
                        c + a * (Lb - L / 2 + 5) + b * (bn - 80), c + a * (Lb - STATION_BLOCK_D - L / 2) + b * (bn - 80)])
        blk_w = largest(body_w.intersection(zone))
        blk_w = orient_all(blk_w.simplify(0.05))
    main_w = largest(body_w.difference(unary_union(towers_w + ([blk_w] if not blk_w.is_empty else [])).buffer(0.01)))
    main_w = orient_all(main_w.simplify(0.05, preserve_topology=True))
    # r2: the parking body keeps the station block in its plan (one roof deck over both, NAIP stalls over the block); the block
    # draws only its own facades and hall
    roof_w = orient_all(largest(body_w.difference(unary_union(towers_w).buffer(0.01)) if towers_w else body_w).simplify(0.05, preserve_topology=True))
    P = F.poly(roof_w)
    Pfull = F.poly(body_w)
    slabs = [pitch * i for i in range(1, 8)]          # L2..L8 slab lines (L9 = the roof deck) [obs a2 pitch]
    sbands = screen_bands(slabs, hd, deck)
    rail_in = RAIL.intersection(body_w)
    # portals: the guideway crossing the outline across the tracks (west face u ~2.6, east face u = Lb) and the block's west edge
    portal_w = []
    if g['rail_near']:
        cross = body_w.exterior.intersection(RAIL.buffer(0.2))
        for seg in getattr(cross, 'geoms', [cross]):
            if seg.geom_type != 'LineString' or seg.length < 2.0: continue
            q = np.array(seg.coords); dd = q[-1] - q[0]
            if abs(dd @ a) / (np.hypot(*dd) or 1) < 0.3:                  # faces across the tracks only (u ~2.6 and u = Lb)
                portal_w.append((q[0], q[-1], 'east' if float((q[0] - c) @ a + L / 2) > Lb - 5 else 'west'))
        if not blk_w.is_empty:
            ub = Lb - STATION_BLOCK_D
            ln = LineString([c + a * (ub - L / 2) - b * 200, c + a * (ub - L / 2) + b * 200]).intersection(rail_in.buffer(0.01))
            for seg in getattr(ln, 'geoms', [ln]):
                if seg.geom_type == 'LineString' and seg.length > 2.0:
                    q = np.array(seg.coords); portal_w.append((q[0], q[-1], 'block'))
    ad = np.array([a[0], -a[1]])
    on_outline = lambda seg: body_w.exterior.distance(Point(*F.W(*seg.interpolate(0.5, normalized=True).coords[0]))) < 0.3
    tw_u = unary_union(towers_w) if towers_w else None
    tw_b = tw_u.boundary if towers_w else None
    blk_b = blk_w.boundary if not blk_w.is_empty else None

    def face_portals(seg):
        """portal holes on a local edge segment: (s_a, s_b) of every portal crossing lying on it."""
        out = []
        for pa_w, pb_w, kind in portal_w:
            pa_, pb_ = Point(F.L(*pa_w)), Point(F.L(*pb_w))
            if seg.length > 0.5 and seg.distance(pa_) < 0.5 and seg.distance(pb_) < 0.5:
                sa_, sb_ = seg.project(pa_), seg.project(pb_)
                out.append((min(sa_, sb_), max(sa_, sb_), kind))
        return sorted(out)

    def style(pa, pb):
        seg = LineString([pa, pb]); mid_w = Point(*F.W(*seg.interpolate(0.5, normalized=True).coords[0]))
        d = np.array(pb, float) - np.array(pa, float); d /= np.linalg.norm(d)
        if tw_b is not None and tw_b.distance(mid_w) < 0.3 and not on_outline(seg):
            return dict(kind='none')                                   # against a tower (inside the building)
        if blk_b is not None and blk_b.distance(mid_w) < 0.3 and blk_w.buffer(0.3).contains(mid_w):
            return dict(kind='none')                                   # the station block's own faces (r2: one roof over both)
        sm = arcs_u is not None and arcs_u.distance(mid_w) < 0.05     # on a smoothed curve (r2): shared normals, continuous panels
        fp = face_portals(seg)
        if fp:
            return dict(kind='solid', solid='precast', holes=[(s0_ + 0.6, s1_ - 0.6, zt - AT.DECK_T - 0.3, zt + AT.PORTAL_H) for s0_, s1_, _ in fp])
        if on_circle(pa, pb, F, circ):
            # drum: smooth metal panels; slots + top opening recessed 0.8 m, closed by jambs where the run meets a tower [obs i2]
            Ls = seg.length
            ends = tuple(bool(tw_u is not None and tw_u.distance(Point(*F.W(*p_))) < 0.5) for p_ in (pa, pb))
            # r2: the drum wall rises to the ring top hr (a2: ~1.9 m over the parapet); its crown is closed below
            return dict(kind='solid', solid='drum_metal', holes=[(0.0, Ls, z0_, z1_) for z0_, z1_ in slots_z + [top_open]], recess=0.8,
                        recess_ends=ends, bands=[(0.0, hr, 'solid')], smooth=sm)
        # every other face: open levels behind the perforated screens [obs spec garage_ag_facade, photos l1 / a2 / i2]
        return dict(kind='screen', pier_dx=SCREEN_MULL, pier_w=0.12, pier_mat='screen_edge', solid='precast', bands=sbands, cover=SCREEN_COVER,
                    smooth=sm)
    axis = float(LB[k]['roof_cars']['car_row_axis_heading_deg'])
    inner, bands = parking_structure(B, P, hd, deck, slabs, style, axis, (float(c[0]), float(c[1])), name=f'{k}_body',
                                     feature='garage body: perforated screen panels, drum (metal panels, slots), deck + parapet',
                                     spec=['garage_ag_facade', f'{k}_footprint'], dims=B.dims, src='obs')
    # r2: drum crown above the parapet (inner face + coping on the drum edges from the parapet top to the ring top)
    sh_body = B.shells[-1].mb
    for a_, b_, s0 in ring_edges(P):
        if not on_circle(a_, b_, F, circ): continue
        n_, L_ = edge_normal(a_, b_)
        ia, ib = np.array(a_) - n_ * PARAPET_T, np.array(b_) - n_ * PARAPET_T
        sh_body.quad_wall(tuple(ib), tuple(ia), hd, hr, hd, hr, 'drum_metal', 0.0, TILES['drum_metal'], grp='drumcrown', smooth=True)
        sh_body.face_dir([(a_[0], a_[1], hr), (b_[0], b_[1], hr), (ib[0], ib[1], hr), (ia[0], ia[1], hr)], 'coping', [(0, 0), (1, 0), (1, 0.1), (0, 0.1)], (0, 0, 1))
    cl = np.array(F.L(*circ['c']))
    cm = MB(f'{k}_core')
    # the helix eye (NAIP dark disc D ~13 m): a guard ring round a dark opening at the deck (a2 / i2: nothing rises above the ring;
    # r1 drew a 4-m cylinder over the ring) [obs NAIP / a2]
    cyl(cm, cl, DL.GAR_CORE_D / 2, deck, deck + PARAPET_H, 32, 'precast_band', TILES['precast_band'], top=None, smooth=True)
    cyl(cm, cl, DL.GAR_CORE_D / 2 - PARAPET_T, deck + PARAPET_H, deck + 0.02, 32, 'precast_band', TILES['precast_band'], top=None, smooth=True)
    ang_ = np.linspace(0, 2 * math.pi, 33)[:-1]
    rr_ = DL.GAR_CORE_D / 2 - PARAPET_T
    cm.face([(cl[0] + rr_ * math.cos(t), cl[1] + rr_ * math.sin(t), deck + 0.03) for t in ang_], 'interior', [(0.5, 0.5)] * len(ang_))
    for i_ in range(32):
        t0_, t1_ = ang_[i_], ang_[(i_ + 1) % 32]
        cm.face([(cl[0] + rr_ * math.cos(t0_), cl[1] + rr_ * math.sin(t0_), deck + PARAPET_H), (cl[0] + rr_ * math.cos(t1_), cl[1] + rr_ * math.sin(t1_), deck + PARAPET_H),
                 (cl[0] + DL.GAR_CORE_D / 2 * math.cos(t1_), cl[1] + DL.GAR_CORE_D / 2 * math.sin(t1_), deck + PARAPET_H),
                 (cl[0] + DL.GAR_CORE_D / 2 * math.cos(t0_), cl[1] + DL.GAR_CORE_D / 2 * math.sin(t0_), deck + PARAPET_H)][::-1], 'coping', [(0, 0)] * 4)
    B.shells.append(Part(f'{k}_core', cm, 'shell', 'obs', 'helix eye: guard ring round the dark opening (D obs NAIP; nothing above the ring in a2 / i2)',
                         ['garage_ag_facade'], dict(D=dim(DL.GAR_CORE_D, 'obs', 'NAIP dark disc, approx'), top=dim(round(deck + PARAPET_H, 2), 'inf', '42-in guard'))))
    excl = [Point(cl).buffer(DL.GAR_CORE_D / 2 + 1.5)]
    if k == 'garage_a':
        # NE rotunda (review r2, finding 3): a light precast cylinder on the curved NE end, D 16.5, top 36.5 m [obs a2 / NAIP, low]
        rc_ = np.array(F.L(*ROT_A['centre']))
        rt = MB(f'{k}_rotunda')
        cyl(rt, rc_, ROT_A['D'] / 2, deck, ROT_A['top'] - 0.9, 48, 'precast', TILES['precast'], top=None, smooth=True)
        cyl(rt, rc_, ROT_A['D'] / 2 + 0.12, ROT_A['top'] - 0.9, ROT_A['top'], 48, 'precast_band', TILES['precast_band'], top='roof_membrane', smooth=True)
        B.shells.append(Part(f'{k}_rotunda', rt, 'shell', 'obs', 'NE rotunda on the curved east end (photo a2: light cylinder ~16 m across rising ~10 m over the '
                             'deck; NAIP 2024 disc, lean-corrected) [obs a2 / NAIP, low; use unk]', ['garage_ag_facade'],
                             dict(D=dim(ROT_A['D'], 'obs', 'a2 width 94 px at 5.8 px/m; NAIP rim'), top=dim(ROT_A['top'], 'obs', 'a2 solved camera [low]'),
                                  centre=dim(list(ROT_A['centre']), 'obs', ROT_A['note']))))
        excl.append(Point(*rc_).buffer(ROT_A['D'] / 2 + 1.5))
    # stair / elevator towers: white precast with ribs, a column of small square windows on the outward faces [obs i2]
    twm = MB(f'{k}_towers'); twd = MB(f'{k}_tower_windows')
    pitch = hd / 9
    for tw in towers_w:
        T_ = F.poly(tw)
        walls(twm, T_, 0.0, tower_top, 'precast_white', TILES['precast_white'])
        cap(twm, T_, tower_top, 'coping', 4.0)
        for a_, b_, s0 in ring_edges(T_):
            n_, L_ = edge_normal(a_, b_)
            if L_ < 4.0 or not body_w.exterior.buffer(0.4).contains(Point(*F.W(0.5 * (a_[0] + b_[0]), 0.5 * (a_[1] + b_[1])))): continue
            dd_ = (np.array(b_) - np.array(a_)) / L_; mid = 0.5 * (np.array(a_) + np.array(b_))
            for zc in np.arange(pitch * 0.55, tower_top - 1.5, pitch):
                p0_, p1_ = mid - dd_ * 0.6 + n_ * 0.02, mid + dd_ * 0.6 + n_ * 0.02
                twd.quad_wall(tuple(p0_), tuple(p1_), zc - 0.6, zc + 0.6, zc - 0.6, zc + 0.6, 'slot', 0.0, (1.2, 1.2))
        excl.append(F.poly(tw).buffer(1.5))
    if towers_w:
        B.shells.append(Part(f'{k}_towers', twm, 'shell', 'obs', 'white precast stair / elevator towers at both drum ends (photo i2; NAIP '
                             'boxes at the outline notches) [positions obs, size inf, top obs i2 low]', ['garage_ag_facade'],
                             dict(top=dim(round(tower_top, 2), 'obs', 'photo i2: ~3 m above the drum ring [low]'))))
        B.details[0].append(Part(f'{k}_tower_windows', twd, 'detail', 'obs', 'small square windows, one per level (photo i2)', ['garage_ag_facade']))
        B.details[1].append(Part(f'{k}_tower_windows', twd, 'detail', 'obs', 'tower windows', ['garage_ag_facade']))
    ph = None
    if G['box']:
        # r2 (finding 3): the penthouse from a2 - base on the deck, an open braced lower storey to 29.6 m, a solid upper part to
        # 36.0 m [obs a2]; plan = the NAIP box lean-corrected with the measured lean (NAIP_LEAN_GA): west face at the deck height,
        # east face at the top (the r1 plan shifted the whole imaged box by 13.25 m: 24.6 m long, a2 shows ~18 m)
        (ix0, iz0), (ix1, iz1) = PH_BOX_IMG
        ph_w = Polygon([(ix0 - NAIP_LEAN_GA * deck, iz0), (ix1 - NAIP_LEAN_GA * PH_A['top'], iz0), (ix1 - NAIP_LEAN_GA * PH_A['top'], iz1),
                        (ix0 - NAIP_LEAN_GA * deck, iz1)])
        bp = orient_all(F.poly(ph_w))
        bx = MB(f'{k}_rooftop_box')
        zo = PH_A['open_top']
        walls(bx, bp, zo, PH_A['top'], 'precast', TILES['precast'])
        cap(bx, bp, PH_A['top'], 'coping', 6.0)
        cap(bx, bp, zo, 'soffit', 6.0, down=True)
        core_ = bp.buffer(-1.2, join_style=2)
        walls(bx, core_, deck, zo, 'interior', TILES['interior'])           # dark core behind the open storey
        cs_ = np.array(bp.exterior.coords)[:-1]
        for q_ in cs_:                                                     # corner columns + one X-brace per face (a2: braced)
            boxm(bx, q_ - (q_ - np.array(bp.centroid.coords[0])) / np.linalg.norm(q_ - np.array(bp.centroid.coords[0])) * 0.45, (1, 0), 0.6, 0.6, (deck, zo), 'precast', (3.0, 3.0), top=False)
        for i_ in range(len(cs_)):
            p0_, p1_ = cs_[i_], cs_[(i_ + 1) % len(cs_)]
            tube(bx, [(p0_[0], p0_[1], deck + 0.2), (p1_[0], p1_[1], zo - 0.2)], 0.12, 4, 'steel')
            tube(bx, [(p1_[0], p1_[1], deck + 0.2), (p0_[0], p0_[1], zo - 0.2)], 0.12, 4, 'steel')
        B.shells.append(Part(f'{k}_rooftop_box', bx, 'shell', 'obs', 'rooftop penthouse: open braced lower storey, solid upper part (photo a2; NAIP plan '
                             'lean-corrected) [obs a2 / NAIP; use unk]', [f'{k}_height'],
                             dict(plan=dim([[round(x_, 2), round(z_, 2)] for x_, z_ in ph_w.exterior.coords][:4], 'obs', 'NAIP box, lean %.3f m/m' % NAIP_LEAN_GA),
                                  open_top=dim(zo, 'obs', 'photo a2 [low]'), top=dim(PH_A['top'], 'obs', 'photo a2 [low]; r1 drew ring + 3.5'))))
        excl.append(bp.buffer(1.5))
        ph = dict(poly=bp, top=PH_A['top'], open_top=zo)
    # ---------------- Garage A station block (photo l1)
    blk_info = None
    if not blk_w.is_empty:
        Pb = F.poly(blk_w)
        main_b = main_w.boundary
        zh0, zh1 = zt, zt + AT.PORTAL_H                       # station hall at the track level (open over the tracks / to the south)
        zg = zt - AT.DECK_T - 0.3                             # top of the garage levels below the guideway
        gbands = clip_bands(sbands, 0.0, zg)

        def bstyle(pa, pb):
            seg = LineString([pa, pb]); mid_w = Point(*F.W(*seg.interpolate(0.5, normalized=True).coords[0]))
            if main_b.distance(mid_w) < 0.3 and not on_outline(seg):
                return dict(kind='none')
            fp = face_portals(seg)
            d = np.array(pb, float) - np.array(pa, float); Ls = float(np.hypot(*d)); d /= Ls
            if fp:
                # east face across the tracks: openings over both tracks (the south one extended over the overhang to the face end),
                # central pier between them, two long slots at STATION_BLOCK_SLOT (none over the central pier) [obs l1]
                ints = [(s0_, s1_) for s0_, s1_, _ in fp]
                south_first = blk_w.exterior.distance(Point(*F.W(*pa))) < 0.5 and float((np.array(F.W(*pa)) - c) @ b) < float((np.array(F.W(*pb)) - c) @ b)
                if len(ints) >= 2:
                    pier = (ints[0][1] - 0.6, ints[1][0] + 0.6)
                else:
                    pier = (ints[0][1] - 0.6, ints[0][1] + 6.0)
                holes = []
                for j, (s0_, s1_) in enumerate(ints[:2]):
                    h0 = 0.6 if (j == 0) else s0_ + 0.6
                    h1 = (s1_ - 0.6) if j == 0 else Ls - 0.6
                    holes.append((h0, h1, zg, zh1))
                runs = [(0.6, pier[0], zt + STATION_BLOCK_SLOT, 1.2), (pier[1], Ls - 0.6, zt + STATION_BLOCK_SLOT, 1.2)]
                # one precast wall from grade to the block top (review r1 render: with the garage bands the face stopped at
                # the guideway level and the block was open to the east)
                return dict(kind='solid', solid='precast', holes=holes, slot_runs=runs, bands=[(0.0, blk_top, 'solid')], z1=blk_top)
            # long faces: garage levels below the guideway, the deck edge, the open hall on columns (south), solid block above
            return dict(kind='screen', pier_dx=SCREEN_MULL, pier_w=0.12, pier_mat='screen_edge', solid='precast', cover=SCREEN_COVER,
                        bands=gbands + [(zg, zh0, 'solid'), (zh1, blk_top, 'solid')])
        bsh, bdet = MB(f'{k}_station_block'), MB(f'{k}_station_block_det')
        garage_facade(bsh, Pb, gbands, bstyle, TILES, gdetail=bdet)
        # the hall: ceiling, back / side walls, floor around the tracks, columns along the south face (r2: the roof is the
        # garage roof deck over the block - one deck and parapet, drawn with the body)
        cap(bsh, Pb, zh1, 'soffit', 6.0, down=True)
        rail_l = F.poly(RAIL.buffer(0.15, join_style=2))
        floor = orient_all(Pb.buffer(-0.3, join_style=2).difference(rail_l).buffer(0))
        for q in polys(floor):
            if q.area > 2.0: cap(bsh, q, zh0 + 0.02, 'platform', 6.0)
        cap(bsh, Pb, zg, 'concrete', 6.0)                     # top of the garage levels under the deck / platform
        for a_, b_, s0 in ring_edges(Pb):
            seg = LineString([a_, b_]); mid_w = Point(*F.W(*seg.interpolate(0.5, normalized=True).coords[0]))
            n_, L_ = edge_normal(a_, b_)
            if main_b.distance(mid_w) < 0.3 and not on_outline(seg):
                # the hall's back / north walls (the main body behind): dark interior seen through the openings
                bsh.quad_wall(b_, a_, zh0, zh1, zh0, zh1, 'interior', 0.0, (4.0, 4.0))
            elif not face_portals(seg) and L_ > 8.0:
                # south face: the hall open to the south under the block, on round columns just outside the face (the south track
                # runs 0.2 m inside it) [obs l1: two round columns under the south overhang; D 1.0 / spacing ~7.5 m inf]
                dd_ = (np.array(b_) - np.array(a_)) / L_
                for s_ in np.linspace(0.8, L_ - 0.8, max(2, int(round(L_ / 7.5)) + 1)):
                    cc_ = np.array(a_) + dd_ * s_ + n_ * 0.55
                    tube(bsh, [(cc_[0], cc_[1], zg), (cc_[0], cc_[1], zh1)], 0.5, 12, 'concrete_lt', cap_ends=False)
        # the long faces' hall band is open: remove nothing (garage_facade drew no wall in [zh0, zh1] there), add the jamb at the east end
        B.shells.append(Part(f'{k}_station_block', bsh, 'shell', 'obs', 'AirTrain station block over the tracks: top %.1f m above the guideway, '
                             'two long slots, open hall on columns [obs l1, low]' % STATION_BLOCK_H, [f'{k}_airtrain_level', 'garage_ag_facade'],
                             dict(top=dim(round(blk_top, 2), 'obs', 'photo l1: %.1f m above the walkway (%.1f m above the deck) [low]' % (_L1['top_above_platform'], STATION_BLOCK_H)),
                                  depth=dim(STATION_BLOCK_D, 'inf', 'l1 sightline: >= 27 m'), slots=dim(round(zt + STATION_BLOCK_SLOT, 2), 'obs', 'photo l1'))))
        B.details[0].append(Part(f'{k}_station_block_det', bdet, 'detail', 'obs', 'block slots, columns, screens below the guideway', ['garage_ag_facade']))
        blk_info = dict(top=round(blk_top, 3), depth=STATION_BLOCK_D, slot_z=round(zt + STATION_BLOCK_SLOT, 2), hall=[round(zh0, 2), round(zh1, 2)],
                        area=round(blk_w.area, 1))
    rc = LB[k]['roof_cars']
    B.decks.append(dict(poly=inner, z=deck, axis=axis, origin=(float(c[0]), float(c[1])), key=k,
                        density=rc['cars_per_1000m2'], count_src='%s_roof_cars: %d detected (+-30 %%), %.1f per 1,000 m2 [obs, low]' % (k, rc['cars_detected'], rc['cars_per_1000m2']),
                        axis_src='car long axis %.0f deg [obs NAIP, coherence %.2f]' % (axis, rc['row_axis_coherence']), exclude=excl))
    # portal tunnels (dark boxes 10 m into the body) at the west face and at the station block's back wall
    tn = MB(f'{k}_portal')
    portal_local = []
    for pa_w, pb_w, kind in portal_w:
        if kind == 'east' and not blk_w.is_empty: continue            # the east face opens into the station hall
        pa, pb = np.array(F.L(*pa_w)), np.array(F.L(*pb_w))
        n, Le = edge_normal(pa, pb)
        mid = 0.5 * (pa + pb)
        host = P if kind != 'block' else F.poly(main_w)
        if host.contains(Point(*(mid + n * 1.0))): n = -n
        if host.contains(Point(*(mid + n * 1.0))) or not host.buffer(0.01).contains(Point(*(mid - n * 1.0))): continue
        din = -n * 10.0
        if np.cross(np.r_[pb - pa, 0], np.r_[n, 0])[2] > 0: pa, pb = pb, pa
        z0, z1 = zt - AT.DECK_T - 0.3, zt + AT.PORTAL_H
        d = (pb - pa) / Le
        pa2, pb2 = pa + d * 0.6, pb - d * 0.6
        zf = z0 + AT.DECK_T + 0.3
        cen = np.r_[0.5 * (pa2 + pb2) + din * 0.5, 0.5 * (zf + z1)]
        uvq = [(0, 0), (1, 0), (1, 1), (0, 1)]

        def inward(pts, mat):
            P_ = np.asarray(pts, float); c_ = P_.mean(0)
            tn.face_dir(pts, mat, uvq, cen - c_)
        inward([(*(pa2 + din), z0), (*(pb2 + din), z0), (*(pb2 + din), z1), (*(pa2 + din), z1)], 'interior')
        inward([(*pa2, z0), (*(pa2 + din), z0), (*(pa2 + din), z1), (*pa2, z1)], 'interior')
        inward([(*pb2, z0), (*(pb2 + din), z0), (*(pb2 + din), z1), (*pb2, z1)], 'interior')
        q = [pa2, pb2, pb2 + din, pa2 + din]
        inward([(p[0], p[1], z1) for p in q], 'interior')
        tn.face_dir([(p[0], p[1], zf) for p in q], 'guideway_deck', uvq, (0, 0, 1))
        if kind != 'block':
            tn.face_dir([(*pa2, z0), (*pb2, z0), (*pb2, zf), (*pa2, zf)], 'guideway', uvq, (-din[0], -din[1], 0))
        else:
            # the block's back wall around the tunnel mouth (dark interior of the hall faces east)
            pass
        portal_local.append([[round(float(v), 2) for v in pa], [round(float(v), 2) for v in pb], kind])
    if not tn.empty():
        B.shells.append(Part(f'{k}_portal', tn, 'shell', 'obs', 'AirTrain portals into the garage (guideway crossing [obs polygons]; '
                             'opening at the network level [inf])', [f'{k}_airtrain_level', 'at_section']))
    B.anchors = dict(parapet=round(hd, 2), drum_ring=round(hr, 2), deck=round(deck, 2), pitch=pitch, core_top=round(deck + PARAPET_H, 2), levels=[round(z, 2) for z in slabs],
                     penthouse=(dict(top=ph['top'], open_top=ph['open_top'], plan=[[round(float(x_), 2), round(float(y_), 2)] for x_, y_ in ph['poly'].exterior.coords][:-1]) if ph else None),
                     rotunda=(dict(ROT_A) if k == 'garage_a' else None), parapet_sheet=hd_sheet, Lb=Lb, u_axis_world=[float(a[0]), float(a[1])],
                     u0_world=[float((c - a * L / 2)[0]), float((c - a * L / 2)[1])], portal_spans=len(portal_w), airtrain_level=round(zt, 3),
                     drum=dict(c=circ['c'], R=circ['R']), body_area=round(body_w.area, 1), drum_slots=[[round(z0, 2), round(z1, 2)] for z0, z1 in slots_z],
                     drum_top_opening=[round(v, 2) for v in top_open], towers=[[[round(x, 2), round(z, 2)] for x, z in t.exterior.coords] for t in towers_w],
                     tower_top=round(tower_top, 2), station_block=blk_info, portals_local=portal_local)
    # ---------------- LOD2: body prism with the parapet recess, drum slot bands, core, towers, rooftop box, station block, portals
    cm2 = MB(f'{k}_L2')
    P2 = P.simplify(0.8)
    portal2 = []
    for pa_w, pb_w, kind in portal_w:
        if kind == 'block': continue
        portal2.append((Point(F.L(*pa_w)), Point(F.L(*pb_w)), kind))
    for q in polys(P2):
        for ring in rings_of(q):
            n_r = len(ring); s = 0.0
            for i in range(n_r):
                a_, b_ = ring[i], ring[(i + 1) % n_r]
                Ls = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
                if Ls < 1e-3: continue
                seg = LineString([a_, b_]); mid_w = Point(*F.W(*seg.interpolate(0.5, normalized=True).coords[0]))
                if (tw_b is not None and tw_b.distance(mid_w) < 0.6 and not on_outline(seg)):
                    s += Ls; continue
                z0w = blk_top if (blk_b is not None and blk_b.distance(mid_w) < 0.6 and not on_outline(seg)) else 0.0
                holes = []
                for pa_, pb_, kind in portal2:
                    if seg.distance(pa_) < 1.0 and seg.distance(pb_) < 1.0:
                        sa_, sb_ = sorted((seg.project(pa_), seg.project(pb_)))
                        holes.append((sa_ + 0.6, sb_ - 0.6, zt - AT.DECK_T - 0.3, zt + AT.PORTAL_H))
                mat = 'drum_metal' if on_circle(a_, b_, F, circ, tol=2.0) else 'precast'
                holed_wall(cm2, a_, b_, z0w, hr if mat == 'drum_metal' else hd, holes, mat, s, (6.0, 6.0))
                if mat == 'drum_metal':
                    nn_, _ = edge_normal(a_, b_)
                    for z0_, z1_ in slots_z + [top_open]:
                        p0_, p1_ = np.array(a_) + nn_ * 0.05, np.array(b_) + nn_ * 0.05
                        cm2.quad_wall(tuple(p0_), tuple(p1_), z0_, z1_, z0_, z1_, 'interior', 0.0, (4.0, 4.0))
                for (h0, h1, z0h, z1h) in holes:
                    dd_ = (np.array(b_) - np.array(a_)) / Ls; nn_, _ = edge_normal(a_, b_)
                    pa2_, pb2_ = np.array(a_) + dd_ * h0 - nn_ * 6.0, np.array(a_) + dd_ * h1 - nn_ * 6.0
                    cm2.quad_wall(tuple(pa2_), tuple(pb2_), z0h, z1h, z0h, z1h, 'interior', 0.0, (4.0, 4.0))
                s += Ls
    ring2, inner2 = ring_band(P2, PARAPET_T)
    cap(cm2, ring2, hd, 'coping', 3.0)
    for q in polys(inner2):
        for r in rings_of(q):
            for i in range(len(r)):
                cm2.quad_wall(r[(i + 1) % len(r)], r[i], deck, hd, deck, hd, 'coping', 0.0, (3.0, 3.0))
        cap(cm2, q, deck, 'deck_far', 12.0)
    cyl(cm2, cl, DL.GAR_CORE_D / 2, deck, deck + PARAPET_H, 10, 'precast_band', (6.0, 6.0), top='interior', smooth=False)
    if k == 'garage_a':
        cyl(cm2, np.array(F.L(*ROT_A['centre'])), ROT_A['D'] / 2, deck, ROT_A['top'], 16, 'precast', (6.0, 6.0), top='roof_membrane', smooth=True)
    for tw in towers_w:
        T_ = F.poly(tw).simplify(0.3)
        walls(cm2, T_, 0.0, tower_top, 'precast_white', (6.0, 6.0)); cap(cm2, T_, tower_top, 'coping', 6.0)
    if ph:
        walls(cm2, ph['poly'], deck, ph['top'], 'precast', (6.0, 6.0)); cap(cm2, ph['poly'], ph['top'], 'coping', 6.0)
    # r2: the station block is part of the body plan (its east-face portal opens into a dark recess; roof = the garage deck)
    B.coarse.append(Part(f'{k}_L2', cm2, 'coarse', 'obs', 'garage body (coarse): parapet recess, drum slots, core, towers, box, station block, portals', [f'{k}_footprint']))
    B.footprint_w = body_w; B.top = max(hr, tower_top, ph['top'] if ph else 0.0, ROT_A['top'] if k == 'garage_a' else 0.0)
    B.body_w = body_w; B.blk_w = blk_w; B.main_w = main_w
    return B


# ================================================================================================ SFO BART station (r1)
BART_W = [(-1592.0, 25.0), (-1572.0, 25.0), (-1562.0, 42.0), (-1445.0, 42.0), (-1425.0, 14.0), (-1336.0, 14.0)]
#   complex depth south of the NAIP north wall line (x, depth): the west corridor 25 m, the vault / platform section to the Garage G
#   body (42 m, cut by the body), the twin guideway east of x -1425 (14 m; the curved branch to Garage A leaves there) [obs NAIP, approx]


def bart_footprint(gG):
    """SFO BART station complex (Building 497, under the Garage G AirTrain station and guideway) - plan: a band south of the NAIP
    2024 north wall line (R1 bart.north) [obs], BART_W deep (tapering east of x -1430 to the twin guideway) [obs NAIP, approx],
    outside the Garage G body and the ITB outline; holes filled."""
    north = [tuple(p) for p in R1['bart']['north']]
    xs = np.linspace(north[0][0], north[-1][0], 60)
    nz = np.interp(xs, [p[0] for p in north], [p[1] for p in north])
    w = np.interp(xs, [p[0] for p in BART_W], [p[1] for p in BART_W])
    reg = Polygon(list(zip(xs, nz)) + list(zip(xs[::-1], (nz + w)[::-1]))).buffer(0)
    ob = R1.get('osm', {}).get('bart')
    if ob:
        # OpenStreetMap way 221663595 'train_station' (ODbL): the same north edge within ~1.5 m, a straight south edge -> used as
        # the plan [osm, cross-checked with NAIP]; the NAIP band stays the fallback
        reg = Polygon(ob['poly']).buffer(0)
    body = reg.difference(gG.body_w.buffer(0.3, join_style=2)).difference(AT.ITB_OUTLINE.buffer(0.3, join_style=2))
    body = largest(body)
    return orient_all(Polygon(body.exterior).buffer(2.0, join_style=2).buffer(-2.0, join_style=2).simplify(0.3, preserve_topology=True))


def bart(gG, lev, fp_w):
    """SFO BART station body (round 1; spec garage_g_identity [pub]: 'integral Garage G BART and AirTrain Station, Building 497';
    the BART station one level below the AirTrain platform [pub, secondary]). Plan fp_w (bart_footprint) [obs]; the body carries
    the AirTrain deck: its top follows the AirTrain level field 1.6 m below the deck top [inf]; north / east faces from photo
    a2 (proportions): an open ground storey on columns, white panels, a green glazed band below the AirTrain level [obs a2
    ratios; heights inf]; the white station vault is the Garage G AirTrain station roof (landside_airtrain 'vault')."""
    k = 'bart_station'
    LVb = R1['bart']['levels']
    c = fp_w.centroid
    B = Bldg(k, 'SFO BART station (Building 497, with the Garage G AirTrain station)', c.x, c.y, 'obs',
             ['garage_g_identity', 'at_stations'],
             dict(plan=dim('OpenStreetMap way 221663595 train_station (ODbL), its north edge within ~1.5 m of the NAIP 2024 shadow line [obs]; '
                           'minus the Garage G body and the ITB outline', 'osm/obs', 'tools/blender/landside_r1_obs.json osm.bart / bart.north'),
                  osm_tags=dim(R1.get('osm', {}).get('bart', {}).get('tags', {}), 'osm', 'OSM building:levels 4, min_level 1, height 20, min_height 4 '
                               '(volunteer-mapped, unverified)'),
                  top=dim('AirTrain deck top - %.1f m (follows the level field: %.2f m at the Garage G station)' % (AT.DECK_T, AT.NET_LEVEL - AT.DECK_T), 'inf',
                          'the body carries the AirTrain (photo a2: the station face rises to the guideway trough)'),
                  colonnade=dim(BART_COLONNADE, 'obs', 'photo a2, solved camera (r2): 5.4-6.1 m over 4 columns; OSM min_height 4 [osm]'),
                  glazed_band=dim(dict(below_top=BART_BAND_UP, height=BART_BAND_H), 'obs', 'photo a2, solved camera (r2): band 9.2-13.5 m under a 17.6-m top [low]'),
                  bart_track=dim(LVb['track'], 'unk', 'one level below the AirTrain platform [pub secondary]; not modelled (inside the body)')),
             inferred=['top 1.6 m below the AirTrain deck top', 'colonnade 4.3 m, columns every 9 m, 3-m dark recess', 'white metal / precast panels (colour inf)',
                       'glazed band %.1f m tall, %.1f m below the top (follows the level field)' % (BART_BAND_H, BART_BAND_UP), 'flat roof where no AirTrain deck covers it'],
             unknown=['body height and levels (no source)', 'BART track / platform level', 'the station length east of the vault (NAIP shadow line only)'],
             not_modelled=['BART three-track aerial approach: from the station west end it shares the corridor covered by the SFO Museum '
                           'AirTrain polygon (x -1920..-1592: the AirTrain deck stands for both; levels not separable from NAIP); west of '
                           'x -1920 it continues 2+ km over US 101 to the wye and the San Bruno / Millbrae branches (outside the landside scene)',
                           'BART tracks, platforms and the concourse inside', 'station entrances / skybridge to the ITB departures level'])
    F = B.F
    P = F.poly(fp_w)
    top_at = lambda X, Y: float(np.clip(lev.h(*F.W(X, Y)) - AT.DECK_T - 0.02, 10.0, 19.0))
    ob = R1.get('osm', {}).get('bart', {}).get('tags', {})
    zc = BART_COLONNADE      # r2: open ground storey top 5.9 m (a2 solved camera, 5.4-6.1) [obs a2]; OSM min_height 4 [osm, unverified]
    inside_other = unary_union([gG.body_w, AT.ITB_OUTLINE]).buffer(0.6)
    sh, det = MB('bart_body'), MB('bart_columns')
    rz = []                                   # colonnade recess strips
    bands_seen = []
    for a, b, s0 in ring_edges(P):
        mid = Point(*F.W(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])))
        if inside_other.contains(mid): continue                                # against the garage / ITB: internal
        n, L = edge_normal(a, b)
        ta, tb = top_at(*a), top_at(*b)
        # white panels from the colonnade soffit to the band, the glazed band, a white strip to the top - all sloping with the
        # level field (r1 render: a band from a fixed 15.2 m to the top was a sliver where the AirTrain descends west); band
        # BART_BAND_UP below the top, BART_BAND_H tall [obs a2 with the solved camera (r2), low]
        g1a, g1b = ta - BART_BAND_UP, tb - BART_BAND_UP
        g0a, g0b = max(g1a - BART_BAND_H, zc + 2.0), max(g1b - BART_BAND_H, zc + 2.0)
        uvq = lambda z0a, z0b, z1a, z1b, h: [(s0 / 3.0, z0a / h), ((s0 + L) / 3.0, z0b / h), ((s0 + L) / 3.0, z1b / h), (s0 / 3.0, z1a / h)]
        sh.face([(a[0], a[1], zc), (b[0], b[1], zc), (b[0], b[1], g0b), (a[0], a[1], g0a)], 'bart_panel', uvq(zc, zc, g0a, g0b, 3.0))
        sh.face([(a[0], a[1], g0a), (b[0], b[1], g0b), (b[0], b[1], g1b), (a[0], a[1], g1a)], 'glass_bart', uvq(g0a, g0b, g1a, g1b, 2.95))
        sh.face([(a[0], a[1], g1a), (b[0], b[1], g1b), (b[0], b[1], tb), (a[0], a[1], ta)], 'bart_panel', uvq(g1a, g1b, ta, tb, 3.0))
        bands_seen.append((min(g0a, g0b), max(g1a, g1b)))
        # the colonnade: 3-m dark recess behind the facade line, round columns every 9 m on it [obs a2]
        A_, B_ = np.array(a), np.array(b)
        q = Polygon([A_, B_, B_ - n * 3.0, A_ - n * 3.0])
        if q.is_valid and q.area > 0.5: rz.append(q)
        if L > 3.0:
            d = (B_ - A_) / L
            for s_ in np.arange(min(4.5, L / 2), L - 1.0, LVb['pier_dx']):
                cc = A_ + d * s_ - n * 0.5
                tube(det, [(cc[0], cc[1], 0.0), (cc[0], cc[1], zc)], 0.45, 10, 'concrete_lt')
    zone = orient_all(unary_union(rz).intersection(P).buffer(0))
    cap(sh, zone, 0.02, 'sill', 6.0)
    cap(sh, zone, zc, 'soffit', 6.0, down=True)
    pb = P.boundary
    for q in polys(zone):
        for ring in rings_of(q):
            for i in range(len(ring)):
                a, b = ring[i], ring[(i + 1) % len(ring)]
                mid = Point(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
                if pb.distance(mid) < 0.05: continue
                sh.quad_wall(b, a, 0.0, zc, 0.0, zc, 'interior', 0.0, (6.0, 6.0))
    # roof under / beside the AirTrain deck (hidden under the deck; flat membrane where open)
    cap(sh, P, 0.0, 'roof_membrane', 8.0, zf=top_at)
    B.shells.append(Part('bart_body', sh, 'shell', 'obs', 'BART station body: colonnade, white panels, green glazed band, carrying the AirTrain [obs plan, inf heights]',
                         ['garage_g_identity'], B.dims))
    B.details[0].append(Part('bart_columns', det, 'detail', 'inf', 'colonnade columns every %.0f m' % LVb['pier_dx'], ['garage_g_identity']))
    det1 = MB('bart_columns1')
    for t in range(0):
        pass
    cm2 = MB('bart_L2')
    for a, b, s0 in ring_edges(P.simplify(0.8)):
        mid = Point(*F.W(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])))
        if inside_other.contains(mid): continue
        ta, tb = top_at(*a), top_at(*b)
        g1a, g1b = ta - BART_BAND_UP, tb - BART_BAND_UP
        g0a, g0b = max(g1a - BART_BAND_H, zc + 2.0), max(g1b - BART_BAND_H, zc + 2.0)
        cm2.quad_wall(a, b, 0.0, zc, 0.0, zc, 'interior', s0, (6.0, 6.0))
        cm2.face([(a[0], a[1], zc), (b[0], b[1], zc), (b[0], b[1], g0b), (a[0], a[1], g0a)], 'bart_panel', [(0, 0), (1, 0), (1, 1), (0, 1)])
        cm2.face([(a[0], a[1], g0a), (b[0], b[1], g0b), (b[0], b[1], g1b), (a[0], a[1], g1a)], 'glass_bart', [(0, 0), (1, 0), (1, 1), (0, 1)])
        cm2.face([(a[0], a[1], g1a), (b[0], b[1], g1b), (b[0], b[1], tb), (a[0], a[1], ta)], 'bart_panel', [(0, 0), (1, 0), (1, 1), (0, 1)])
    cap(cm2, P.simplify(0.8), 0.0, 'roof_membrane', 12.0, zf=top_at)
    B.coarse.append(Part('bart_L2', cm2, 'coarse', 'obs', 'BART station body (coarse)', ['garage_g_identity']))
    B.footprint_w = fp_w; B.top = max(top_at(*p) for p in list(P.exterior.coords))
    B.anchors = dict(area=round(fp_w.area, 1), x_range=[round(fp_w.bounds[0], 1), round(fp_w.bounds[2], 1)], colonnade=zc, band=[round(min(b_[0] for b_ in bands_seen), 2), round(max(b_[1] for b_ in bands_seen), 2)] if bands_seen else None,
                     top_min=round(min(top_at(*p) for p in list(P.exterior.coords)), 2), top_max=round(B.top, 2))
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
    cm2 = MB('ltp1_L2'); stack_coarse(cm2, P.simplify(0.8), top, 'precast', 'deck_far', deck=deck)
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
    cm2 = MB('ltp2_L2'); stack_coarse(cm2, P.simplify(0.8), top, 'concrete_lt', 'deck_far', deck=deck)
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
    LOUVRE_PITCH = 0.20                      # blade pitch [obs l5: ~40 px apart ~6 m from the camera (f 1442 px) -> ~0.17-0.2 m]
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
             deviations=['west wall / station platform at %.1f m (photo l5, camera solved: landside_r1_obs.json photos.l5_camera) instead of '
                         'the BL-03 L4 placeholder 12.35 m [unk]' % hp])
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
        # louvre blades (LOD0): fine horizontal blades every LOUVRE_PITCH, 0.12 m deep, following the cant (photo l5: many thin
        # blades; r1: were 0.6-m slats that read as 5-6 giant boards near the camera)
        for z in np.arange(zb1 + 0.15, top - 0.05, LOUVRE_PITCH):
            t = (z - zb1) / (top - zb1)
            off = n * (lean * t + 0.02)
            p0 = np.array(a) + off; p1 = np.array(b) + off
            q0 = p0 + n * 0.12; q1 = p1 + n * 0.12
            uvb = [(0, 0), (L / 3, 0), (L / 3, 0.1), (0, 0.1)]
            lv.face_dir([(p0[0], p0[1], z), (p1[0], p1[1], z), (q1[0], q1[1], z - 0.05), (q0[0], q0[1], z - 0.05)], 'louvre_blade', uvb,
                        (n[0] * 0.05, n[1] * 0.05, 0.12))
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
    cm2 = MB('rcc_L2'); stack_coarse(cm2, P.simplify(0.8), top, 'concrete', 'deck_far', deck=deck)
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
    # round 1 (photo l4: one continuous east face): the slab face behind the podium continues the outline's east face from its
    # notch corner along the relief-corrected NAIP slab-roof edge (R1 hyatt_slab_east) instead of a constant 17-m set-back
    hs = R1['hyatt_slab_east']
    pts = [tuple(hs['corner'])] + [(x - hs['shift_x'], z) for x, z in hs['imaged'] if z > hs['corner'][1] + 1.0]
    (x1_, z1_), (x2_, z2_) = pts[-2], pts[-1]
    pts.append((x2_ + (x2_ - x1_) * 30.0 / max(z2_ - z1_, 1e-6), z2_ + 30.0))
    east_reg = Polygon(pts + [(pts[-1][0] + 200.0, pts[-1][1]), (pts[0][0] + 200.0, pts[0][1])]).buffer(0)
    zone_r1 = orient_all(Pfull.intersection(F.poly(east_reg)).intersection(half_s).buffer(0))
    if zone_r1.area > 50.0:
        zone = zone_r1
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
    pent = []; pent_q = []
    for (f0, f1), hh in (((0.518, 0.692), 1.4 * p), ((0.615, 0.742), 0.65 * p)):
        q = largest(core.intersection(band_f(f0, f1)))
        if q.is_empty: continue
        q = orient_all(q)
        walls(ph, q, H - 1.0, H + hh, 'metal_dark', (3.0, 3.0)); cap(ph, q, H + hh, 'coping', 4.0)
        pent.append(dict(f=[f0, f1], top=round(H + hh, 2))); pent_q.append((q, H + hh))
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
    cm2 = MB('gh_L2'); stack_coarse(cm2, P.simplify(0.6), H, 'glass_hyatt', 'roof_membrane', deck=H - 1.0)
    for q in podium: stack_coarse(cm2, q.simplify(0.6), hp, 'metal_dark', 'roof_membrane')
    for q, zt_ in pent_q:                                   # the stepped penthouse in LOD2 too (review r1)
        walls(cm2, q.simplify(0.5), H, zt_, 'metal_dark', (3.0, 3.0)); cap(cm2, q.simplify(0.5), zt_, 'coping', 6.0)
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
    cm2 = MB('cac_L2'); stack_coarse(cm2, P.simplify(0.6), par, 'cac_wall', 'roof_membrane', deck=roof)
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
                  door_head=dim(door_h, 'unk', 'tip - 3 m (BL-03)'), door_bays=dim(67.0, 'inf', 'two per face (four 747 bays [pub])'),
                  l3_identification=dim('photo l3 = the Superbay from the NW: the NNE end face (165 m: plain walls, the darker spine end at its '
                                        'centre under the hipped spine roof) on the left, the WNW door face (138 m, the folded-plate eave '
                                        'sawtooth, grey door leaves over its whole length) on the right', 'obs', 'review r1 (photo l3, ~2008)'),
                  roof_colour=dim('one light roof colour on both cantilevers: NAIP 2024 medians (238, 238, 229) WNW / (242, 242, 234) ESE '
                                  'at noon; the grey-green vs tan of l3 (~2008, afternoon sun from the W / SW) is the lighting of the '
                                  'two 11-deg roof planes (and an older roof finish)', 'obs', 'NAIP 2024 vs photo l3')),
             inferred=['tip height 27 m', 'fold tapers to 0 at the root', 'roof thickness 1.2 m at the eaves', 'door bays 67 m, 8 leaves',
                       'spine-end facets fall to the cantilever-root level (no step at the roof corners)', 'spine end-face office windows (6 bands)',
                       'hangar walls clipped 1 m inside the roof tips (outline 2.4 m beyond the WNW tip, BL-02)'],
             unknown=['fold amplitude', 'door head / leaf division', 'interior height 120 ft position'],
             conflicts=['roof 138 m along the spine vs outline 134.5 m (1.75 m overhang per end [inf] or outline error [unk])',
                        '17.3 m roof bays [obs] vs 50 ft structural bays [pub]', '"140-ft roof" [pub] vs DOF 135 ft'],
             not_modelled=['roof ribs / skylights', 'apron-side annexes', 'the lattice radar tower and low sheds in front (photo l3)'],
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
    boxm(dl, rlp, (1, 0), 0.4, 0.4, (hs, hs + 0.5), 'red_light', (1, 1))      # own material: extras.obstruction_light (DOF lighting R)
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
    boxm(cm2, rlp, (1, 0), 0.4, 0.4, (hs, hs + 0.5), 'red_light', (1, 1))     # the DOF red light in every LOD (review r1)
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
    vaults = []; vault_geo = []
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
        vault_geo.append((o0, ux, uy, Lx, Wy))
    B.shells.append(Part('moc_barrel', br, 'shell', 'obs', 'two barrel-vault hangars (plan obs imaged; heights unk placeholders)', ['moc_barrel_hangars']))
    cm2 = MB('moc_L2')
    for u0, u1, d in parts:
        strip = Polygon([c + ax * (u0 - W_ / 2 - (5 if u0 == 0 else 0)) - bn * 200, c + ax * (u1 - W_ / 2) - bn * 200,
                         c + ax * (u1 - W_ / 2) + bn * 200, c + ax * (u0 - W_ / 2 - (5 if u0 == 0 else 0)) + bn * 200])
        q = orient_all(big.intersection(strip))
        if not q.is_empty: stack_coarse(cm2, F.poly(q), d['agl_m'], 'moc_wall', 'moc_roof', deck=d['agl_m'] - 1.0, thk=0.4)
    for o0, ux, uy, Lx, Wy in vault_geo:                     # coarse barrels (6 facets) to the crown (review r1: LOD2 kept the eave + 0.7 rise)
        prof = [(Wy * i / 6, BARREL_EAVE + BARREL_RISE * math.sin(math.pi * i / 6)) for i in range(7)]
        for i in range(6):
            (y0, z0), (y1, z1) = prof[i], prof[i + 1]
            cm2.face_dir([(*(o0 + uy * y0), z0), (*(o0 + ux * Lx + uy * y0), z0), (*(o0 + ux * Lx + uy * y1), z1), (*(o0 + uy * y1), z1)],
                         'barrel_roof', [(0, 0), (1, 0), (1, 1), (0, 1)], (*(uy * (Wy / 2 - 0.5 * (y0 + y1)) * 0.0 + 0.0 * ux), 1.0))
        for (pa, pb) in ((o0, o0 + ux * Lx), (o0 + ux * Lx + uy * Wy, o0 + uy * Wy)):
            cen = o0 + ux * Lx / 2 + uy * Wy / 2; mid = 0.5 * (pa + pb)
            cm2.face_dir([(*pa, 0.0), (*pb, 0.0), (*pb, BARREL_EAVE), (*pa, BARREL_EAVE)], 'moc_wall', [(0, 0), (1, 0), (1, 1), (0, 1)], (*(mid - cen), 0.0))
        for xg, sg in ((0.0, -1), (Lx, 1)):
            pts = [(*(o0 + ux * xg + uy * y), z) for y, z in prof] + [(*(o0 + ux * xg + uy * Wy), 0.0), (*(o0 + ux * xg), 0.0)]
            cm2.face_dir(pts, 'moc_wall', [(0, 0)] * len(pts), (*(ux * sg), 0.0))
    B.coarse.append(Part('moc_L2', cm2, 'coarse', 'obs', 'MOC (coarse)', ['moc_large_hangar']))
    B.footprint_w = unary_union([big, bb]); B.top = max(d['agl_m'] for d in L['dof'])
    B.anchors = dict(shift_large=[round(float(shift[0]), 2), 0.0], parts=out_parts, barrel_shift=round(-MOC_LEAN * (BARREL_EAVE + 0.6 * BARREL_RISE), 2),
                     vaults=vaults, imaged_corners=L['corners_imaged'])
    return B


# ================================================================================================ assembly
TAIL_WALK_W = 1.6   # emergency walkway beside each single-track trough east of the Garage A station: ~1.5-2 m wide with a galvanised
#                     cable rail on its open edge [obs l1 (the camera's track); the other track by symmetry inf] (review r2, finding 1)


def ga_tail_walk():
    """walkways in the gap between the two single tracks east of Garage A (review r2, finding 1): photo l1 shows a narrow
    emergency walkway (~1.5-2 m, galvanised cable rail) beside the camera's track and open air down to grade beyond it, the other
    guideway a separate structure. The SFO Museum Garage A outline 'tail' between the track polygons (b -13.8..-22.9) is a
    footprint at grade: what it is [unk]; r1 had filled it with a 656-m2 deck at track level. -> the TAIL_WALK_W strips along
    both tracks inside the tail (world polygon)."""
    G = DL.ggeom('garage_a'); c, a, b, L, Lb = G['c'], G['a'], G['b'], G['L'], G['Lb']
    cutter = Polygon([c + a * (Lb - L / 2) + b * 200, c + a * (Lb - L / 2 + 600) + b * 200, c + a * (Lb - L / 2 + 600) - b * 200,
                      c + a * (Lb - L / 2) - b * 200])
    tail = sfom_union(DL.GAR['garage_a']['nm']).intersection(cutter)
    gap = tail.difference(RAIL.buffer(0.05, join_style=2)).buffer(-0.02).buffer(0.02)
    walk = gap.intersection(RAIL.buffer(TAIL_WALK_W + 0.05, join_style=2))
    return orient_all(unary_union([q for q in polys(walk) if q.area > 2.0]).buffer(0))


def ga_tail_gap_area():
    G = DL.ggeom('garage_a'); c, a, b, L, Lb = G['c'], G['a'], G['b'], G['L'], G['Lb']
    cutter = Polygon([c + a * (Lb - L / 2) + b * 200, c + a * (Lb - L / 2 + 600) + b * 200, c + a * (Lb - L / 2 + 600) - b * 200,
                      c + a * (Lb - L / 2) - b * 200])
    tail = sfom_union(DL.GAR['garage_a']['nm']).intersection(cutter)
    return float(tail.difference(RAIL.buffer(0.05, join_style=2)).area)


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
    clip = [AT.ITB_OUTLINE, gA.body_w.difference(gA.blk_w) if not gA.blk_w.is_empty else gA.body_w]   # r1: the guideway runs through the station-block hall
    bart_fp = bart_footprint(gG)
    outlines = [b.footprint_w for b in out if b.footprint_w is not None] + [gA.body_w, gG.body_w, AT.ITB_OUTLINE, bart_fp] + \
               [Polygon(r).buffer(0) for r in D.complex_rings()] + [sfom_union('Central Parking Garage'), sfom_union('Rental Car Center')]
    tiles, info, lev = ([], {}, None)
    if not only or 'airtrain' in only:
        tiles, info, lev = AT.build(clip, outlines, Bldg, Part, dim, station_exclude={'GAR_G': gG.body_w}, walks_world=[ga_tail_walk()])
    if lev is not None and (not only or 'bart_station' in only):
        out.append(bart(gG, lev, bart_fp))
    if only:
        out = [b for b in out if b.key in only]
    return out, tiles, info, lev
