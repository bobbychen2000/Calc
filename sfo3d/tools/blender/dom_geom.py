"""Geometry of the 3-D domestic terminals asset: Harvey Milk Terminal 1 (T1 Center hall, Boarding Areas B and C),
Terminal 2 (hall, Boarding Area D) and Terminal 3 (T3 West / T3 East halls, Boarding Areas E and F).

Pure numpy / shapely (no bpy): tools/blender/build_domestic.py turns the parts into Blender objects;
tools/blender/verify_domestic.py measures the exported glb against the same functions.

THE REFERENCE IS THE 2-D DRAWING CODE (sheets BD-01..03, docs/drawings/buildings/README.md), imported here, not copied:
  tools/buildings/draw_domestic.py  BA-B raised band bab_band() (dom_bab_band.json) and outer roof edges BAB_OUTER_S;
                                    BA-D drums BAD_DRUMS_IMG / BAD_DRUM_TOP and roof lines BAD_LINES_IMG; BA-E section
                                    BAE_FLANK / BAE_STEP / BAE_OVER; BA-F hub BAF_HUB_C / BAF_HUB_APO, lantern
                                    BAF_LANTERN_APO / baf_lantern_centre(), NW-arm monitor baf_monitor(); octagon();
                                    T1 landside T1_CANOPY / T1_HEAD / T1_SPLIT / t1_mullions(); T2_FACE; T3 levels T3_LV,
                                    T3 East penthouse T3E_PENT_SETBACK; dom_baf_hub.json (BH)
  tools/buildings/draw_data.py      the verified spec (DV: spec_domestic.json items), SFO Museum outlines
                                    (data/sfo_airport.json), the per-pier two-epoch leans dom_lean(), the lean-free roof
                                    edge lines dom_true_edges(), dom_bab_roof.json (BA-B wells / bridges / skylights / PV)
  data/sfo_buildings.json           the app's parts: only (a) the curbside-roadway trim of the complex at the T1 north face
                                    and the T3 landside face (tools/build_terminal_parts.py TRIM_WINDOWS: OSM carriageways,
                                    NAIP 2024 shows vehicles inside the SFO Museum outline there) and (b) the hall / walkway
                                    labels used to tell the hall from its connectors
  data/sfo_stands.json              bridge attach points (walk[0]) -> bridge doors, vestibules and overhang notches

Model frame: Blender local X = x - OX (east), Y = OZ - z (north), Z = height above the local apron (m); build_domestic.py
puts the root node at world (OX, GROUND_Y, OZ). Footprint polygons are kept in world (x, z) and converted per vertex.

Tags: 'pub' published, 'obs' measured (NAIP / SFO Museum / photo), 'inf' derived or chosen from stated evidence, 'unk'
placeholder with no source value. Every choice where the sheets are silent is a named constant below with its tag and
reason, and is listed in the manifest (data/buildings3d/manifest.json#domestic) - nothing here changes a drawn [obs] /
[pub] value.
"""
import json
import math
import os
import sys

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box as sbox
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_domestic as DD  # noqa: E402
from draw_lib import FT, hdg_vec, st2w, unit, w2st  # noqa: E402

DV = D.DV
BB, BH = DD.BB, DD.BH
OX, OZ = -896.5, 336.5           # asset origin: centre of the domestic complex bbox (world x, z), rounded

S_HDG = 117.83                   # airport grid s axis heading (js/geo.js), deg
GARAGE_C = np.array([-938.2, 256.5])   # central garage centre (draw_domestic BD-03 notes) - landside faces look at it

# ------------------------------------------------------------------------------------------------ heights (the sheets)
H = {
    'B': float(DV['bab.h_roof']['value']),            # 13.14 outer roof edges [obs, south half; inf north]
    'B_band': float(DV['bab.h_roof_central']['value']),   # 19.04 raised centre [obs, low]
    'C': float(DV['bac.h_roof']['value']),            # 7.20 [obs, low]
    'D': float(DV['bad.h_roof']['value']),            # 8.49 head [obs, low]
    'E': float(DV['bae.h_roof']['value']),            # 12.85 tapered fascia of the raised centre [obs]
    'F': float(DV['baf.h_roof_ne_arm']['value']),     # 10.49 NE arm [obs]; hub / NW arm drawn at it [inf]
}
H_RANGE = {'B': DV['bab.h_roof']['range'], 'B_band': DV['bab.h_roof_central']['range'], 'C': DV['bac.h_roof']['range'],
           'D': DV['bad.h_roof']['range'], 'E': DV['bae.h_roof']['range'], 'F': DV['baf.h_roof_ne_arm']['range']}
H['E_flank'] = H['E'] - DD.BAE_STEP                 # 9.85 lower side roofs [inf, photo a1, low]
# Terminal 3 [pub CDR 95 % CD levels, metres above T3 L1 (subtraction inf); the sheets draw L1 at the apron, the true
# offset (~1-2 ft) is not verified -> 0 here, as drawn]
T3_LV = {k: float(v) for k, v in DD.T3_LV.items()}
T3_L1 = 0.0
H['T3E'] = T3_L1 + T3_LV['R2']                      # 14.48 R2 "top of roof at high point" read as the T3E roof [inf]
H['T3E_pent'] = T3_L1 + T3_LV['R3']                 # 21.34 penthouse top at R3 [inf] (NAIP 6-9 m above the roof, obs low)
H['T3W_parapet'] = T3_L1 + T3_LV['PARAPET_W']       # 16.76 new T3W parapet [pub] (BD-03 view 3)
H['T3W'] = H['T3W_parapet'] - 3.5 * FT              # 15.69 roof deck = parapet - 3'-6" (CDR field wall) [inf]
# T1 / T2: NOTHING published or measured (spec t1c.h_roof unverified, t2: none) -> placeholders [unk]. BD-03 draws their
# landside faces above the departures curb; the curb height above the apron is unknown: T3's published L1 -> L2 rise
# (16'-0" = 4.88 m) is used by analogy [unk placeholder].
CURB = T3_LV['L2']                                  # 4.88 departures curb above the apron [unk placeholder]
H['T1'] = CURB + DD.T1_HEAD                          # 17.88 wall head 13.0 above the curb [inf photo d1] -> roof [unk]
H['T2'] = CURB + 12.0                                # 16.88 BD-03 draws the T2 box 12 m above the curb [unk]
# connectors: SFO Museum terminal area outside the piers and the halls (airside links at grade: the lower of the
# adjoining parts [inf]); landside (courtyard) fingers to the garage / AirTrain stations: elevated, the app's values
# (tools/build_terminal_parts.py walkway y0 6.0 / h 10.5) [unk]
INNER_Y0, INNER_TOP = 6.0, 10.5

# ------------------------------------------------------------------------------------------------ construction choices
ROOF_THK = 0.8          # roof slab + fascia depth below the parapet deck [inf]; the measured heights are the roof EDGES
PARAPET = 0.6           # parapet / coping above the roof deck [inf] -> deck = h - PARAPET, edge top = h (measured)
PARAPET_T = 0.35        # parapet thickness [inf]
FLOOR2 = 5.4            # concourse (departure) floor: js/live/gates.js DEPARTURE_LEVEL (the bridge floor) [inf]
WALK_TOP = FLOOR2 + 3.0 # app walkway top at the facade (gates.js WALK_H 3.0) - roof overhangs are notched below it
CORE_OPEN = 3.0         # morphological opening radius: outline features < 6 m wide = bridge-head fingers [inf]
FINGER_Z = (FLOOR2 - 0.6, WALK_TOP + 0.3)   # fingers / vestibules: an elevated box round the walkway end [inf]
DOOR_W = 3.2            # bridge door opening on the facade at every attach point [inf]
MULL = 1.5              # curtain-wall mullion module (no source) [inf]
# per-pier facade zones (z0, z1, material) [inf: concourse level from the app's bridge floor; glass "floor-to-ceiling at
# the gates" BA-B [pub]; BA-E "clear glass, light- and dark-grey metal bands above / below" [pub]; others unknown]
ZONES = {
    'B': [(0.0, 4.6, 'service'), (4.6, 5.6, 'panel_dark'), (5.6, 11.6, 'glass_ec'), (11.6, None, 'panel_light')],
    'C': [(0.0, 4.0, 'service'), (4.0, 4.6, 'panel_dark'), (4.6, 6.0, 'glass_tint'), (6.0, None, 'panel_light')],
    'D': [(0.0, 4.6, 'service'), (4.6, 5.4, 'panel_dark'), (5.4, 7.3, 'glass_tint'), (7.3, None, 'panel_light')],
    'E': [(0.0, 4.6, 'service'), (4.6, 5.6, 'panel_dark'), (5.6, 8.4, 'glass_frit'), (8.4, None, 'panel_light')],
    'F': [(0.0, 4.6, 'service'), (4.6, 5.6, 'panel_dark'), (5.6, 8.8, 'glass_tint'), (8.8, None, 'panel_light')],
    'conn': [(0.0, 4.6, 'service'), (4.6, 5.6, 'panel_dark'), (5.6, None, 'panel_light')],
    'hall': [(0.0, 4.6, 'service'), (4.6, 5.6, 'panel_dark'), (5.6, 11.0, 'glass_tint'), (11.0, None, 'panel_light')],
}
SWITCH_M = {0: 0.0, 1: 380.0, 2: 1300.0}   # LOD switch distances (camera to the building group node), m [our choice]

# lean-free roof-edge offsets from the level-2 outline (face normals within +-20 deg of ESE / WNW) [obs per pier]:
# + = roof edge outside (overhang), - = inside (the facade is put on the roof edge there)
EDGE_OFF = {'B': (2.27, -1.66), 'D': (2.40, -1.36), 'E': (0.0, -2.0), 'F': (0.0, -1.15), 'C': (0.0, 0.0)}
# BA-B: spec bab.roof_edges (+2.27 / outline -439.70 -> -438.04); BA-D: bad.roof_edges (+2.40 / -1.36); BA-E: fascia on the
# outline (2020 edge -686.2 less k20 h = -688.6, outline -688.5), WNW ~2 m inside (research 5.3, width 43.0 vs drawn 42.9);
# BA-F: ESE on the outline, WNW -0.96 / -1.31 (README round 2) -> mean


# ------------------------------------------------------------------------------------------------ footprints
TRIM_WINDOWS = {   # tools/build_terminal_parts.py (OSM carriageway trim, review round 4 of the app): world boxes
    'T1 north face (curbside roadways)': (-1050.0, 380.0, -790.0, 470.0),
    'T3 landside face (curbside roadways)': (-975.0, 75.0, -865.0, 125.0)}


def _poly(rings):
    return Polygon(rings[0], rings[1:]).buffer(0)


def _clean(g, a_min=1.0):
    g = g.buffer(0)
    gs = [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon' and p.area >= a_min]
    return unary_union(gs) if gs else Polygon()


def polys_of(g, a_min=0.0):
    if g.is_empty: return []
    return [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon' and p.area >= a_min]


def simplify_window(g, wins, tol=0.45):
    """simplify the (rasterised) trimmed boundary inside the trim windows only."""
    out = g
    for (x0, z0, x1, z1) in wins:
        w = sbox(x0, z0, x1, z1)
        inside = out.intersection(w).simplify(tol, preserve_topology=True)
        out = out.difference(w).union(inside)
    return _clean(out)


def complex_eff():
    cx = unary_union([_poly(p) for p in D.AIR['terminalComplex']])
    app = unary_union([_poly(p['rings']) for p in D.BLD['parts']])
    cut = Polygon()
    for (x0, z0, x1, z1) in TRIM_WINDOWS.values():
        cut = cut.union(cx.intersection(sbox(x0, z0, x1, z1)).difference(app.buffer(0.3)))
    cut = _clean(cut, 5.0)
    return _clean(cx.difference(cut)), cut


CX, TRIM_CUT = complex_eff()
ITB = unary_union([_poly(p) for p in D.sfom('International Terminal', 'terminals')] +
                  [_poly(p) for L in 'AG' for p in D.sfom('Boarding Area ' + L, 'boardingAreas')])
# piers: the full SFO Museum boarding-area outlines (they carry the bridge-head fingers the complex outline lacks), less the ITB
PIER_POLY = {L: _clean(unary_union([_poly(p) for p in D.sfom('Boarding Area ' + L, 'boardingAreas')]).difference(ITB), 20)
             for L in 'BCDEF'}
HALL_NAMES = {'T1': 'Harvey Milk Terminal 1', 'T2': 'Terminal 2', 'T3': 'Terminal 3'}
PIER_OF = {'B': 'T1', 'C': 'T1', 'D': 'T2', 'E': 'T3', 'F': 'T3'}


def _hall_split():
    """per terminal: the hall (main body) and its connectors. rest = terminal outline (trimmed) minus the piers and the ITB;
    the hall is the part covered by the app's 'hall' part of that terminal (an opening of 8 m keeps its body); every
    other piece is a connector: 'inner' when it lies in the central courtyard (closer to the garage centre than 160 m:
    pedestrian links over the roadways to the garage / AirTrain stations), else an airside link at grade."""
    allp = unary_union(list(PIER_POLY.values()))
    out = {}
    for key, nm in HALL_NAMES.items():
        T = unary_union([_poly(p) for p in D.sfom(nm, 'terminals')])
        rest = _clean(T.intersection(CX).difference(allp.buffer(0.02)).difference(ITB.buffer(0.02)), 2.0)
        apph = unary_union([_poly(p['rings']) for p in D.BLD['parts'] if p['kind'] == 'hall' and p['name'] == nm])
        hall = rest.intersection(apph.buffer(2.0))
        hall = _clean(hall.buffer(-8.0, join_style=2).buffer(8.0, join_style=2).intersection(rest), 400.0)
        hall = max(polys_of(hall), key=lambda p: p.area)
        conn = []
        for p in polys_of(rest.difference(hall.buffer(0.01)), 40.0):
            c = np.array(p.representative_point().coords[0])
            inner = float(np.hypot(*(c - GARAGE_C))) < 160.0
            conn.append(dict(poly=p, inner=inner))
        out[key] = dict(hall=hall, conn=conn, terminal=T)
    return out


HALLS = _hall_split()
# exclusions: the 2016 ATCT base building (tower asset, data/buildings3d/manifest.json#tower.integration
# exclusion_footprint_world) stands inside the T2 outline; the AirTrain guideway polygon (SFO Museum 'AirTrain Rail')
# grazes the T1 hall outline (151 m2) - both are cut out so that no two assets / structures share a volume [inf]
TOWER_EXCL = Polygon([[-742.5, 305.5], [-763.4, 345.3], [-739.3, 357.9], [-718.5, 318.1]])
RAIL = unary_union([_poly(p) for s_ in D.AIR['structures'] if s_['name'] == 'AirTrain Rail' for p in s_['polys']])
for _k, _v in HALLS.items():
    _h = _clean(_v['hall'].difference(TOWER_EXCL.buffer(0.3, join_style=2)).difference(RAIL.buffer(1.0)), 50.0)
    _h = _clean(_h.buffer(-1.5, join_style=2).buffer(1.5, join_style=2).intersection(_h), 50.0)   # drop slivers
    _v['hall'] = max(polys_of(_h), key=lambda p: p.area)
for _L in ('D',):
    PIER_POLY[_L] = _clean(PIER_POLY[_L].difference(TOWER_EXCL.buffer(0.3, join_style=2)), 20.0)
# T1 Center landside face: the app's trimmed edge is the carriageway (curb) line; the facade stands behind the sidewalk
# that the curb canopy covers (photo d1; NAIP 2024: the PV roof edge lies 3-6 m inside the trimmed edge) -> the hall is
# set back by the canopy depth along the trimmed face [inf]
T1_CANOPY_D = 4.0
_t1 = HALLS['T1']['hall']
_strip = _t1.difference(_t1.buffer(-T1_CANOPY_D, join_style=2)).intersection(TRIM_CUT.buffer(T1_CANOPY_D + 0.8))
HALLS['T1']['hall'] = max(polys_of(_clean(_t1.difference(_strip), 50.0)), key=lambda p: p.area)
# connectors: modelled only when they are airside links at grade that touch no AirTrain guideway; the courtyard links
# (pedestrian bridges over the curbside roadways to the garage / AirTrain stations) and the links that cross the guideway
# have no known level -> NOT modelled here (listed in the manifest; the app keeps its own parts there) [unk]
for _k, _v in HALLS.items():
    for _c in _v['conn']:
        _c['modelled'] = (not _c['inner']) and _c['poly'].intersection(RAIL.buffer(3.0)).area < 1.0
# T3 West / East: split along the bearing (from the garage centre) of the AirTrain / garage connector gap of the landside
# face (BD-03 view 3: west run ends (-1008.1, 99.4), east run starts (-992.2, 94.5)) [inf: CDR p.24 labels]
T3_SPLIT_BRG = 0.5 * (math.degrees(math.atan2(-1008.1 - GARAGE_C[0], -(99.4 - GARAGE_C[1]))) +
                      math.degrees(math.atan2(-992.2 - GARAGE_C[0], -(94.5 - GARAGE_C[1])))) % 360


def _split_t3():
    h = HALLS['T3']['hall']
    R = 2000.0
    a = math.radians(T3_SPLIT_BRG)
    far = GARAGE_C + R * np.array([math.sin(a), -math.cos(a)])
    # east side: the half-plane to the right of the garage->gap ray, bounded generously
    d = unit(far - GARAGE_C); n = np.array([-d[1], d[0]])     # n points east-ish for a north-pointing ray
    if n[0] < 0: n = -n
    east = Polygon([GARAGE_C - d * 50, far, far + n * R, GARAGE_C - d * 50 + n * R])
    e = _clean(h.intersection(east), 100.0); w = _clean(h.difference(east), 100.0)
    return max(polys_of(w), key=lambda p: p.area), max(polys_of(e), key=lambda p: p.area)


T3W_POLY, T3E_POLY = _split_t3()


FINGER_MAX = (160.0, 26.0)   # a finger: area <= 160 m2 and longest side <= 26 m (BA-B ESE stubs ~12 x 2-5 m) [inf]


def core_and_fingers(poly, r=CORE_OPEN):
    """the body (opening with radius r, mitred) and the short narrow protrusions of the outline (bridge-head fingers);
    long narrow strips (connector arms) go back into the body."""
    core = _clean(poly.buffer(-r, join_style=2).buffer(r, join_style=2).intersection(poly), 50.0)
    fingers, back = [], []
    for f in polys_of(_clean(poly.difference(core.buffer(0.02, join_style=2)), 0.5), 0.5):
        mr = f.minimum_rotated_rectangle
        L = max(math.dist(*list(mr.exterior.coords)[i:i + 2]) for i in range(2)) if mr.geom_type == 'Polygon' else 0
        (fingers if (f.area <= FINGER_MAX[0] and L <= FINGER_MAX[1] and f.area >= 3.0) else back).append(f)
    core = _clean(unary_union([core] + back).buffer(0.03, join_style=2).buffer(-0.03, join_style=2).intersection(poly), 50.0)
    core = max(polys_of(core), key=lambda p: p.area)
    fingers = [f.difference(core) for f in fingers]
    return core, [f for f in fingers if f.area >= 3.0 and f.geom_type == 'Polygon']


