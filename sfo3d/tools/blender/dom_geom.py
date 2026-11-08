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
  tools/blender/app_bridges.json    the app's bridge levels per pier (js/live/gates.js DEPARTURE_LEVELS), rotunda floors
                                    Hr and fixed-walkway floors (node tools/blender/app_bridges.mjs; close-out r3 fix 2):
                                    door frames, vestibules, bulkheads, drum notches and the bridge-entered elevated parts
                                    follow the walkway that docks into them

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
import shapely.prepared
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box as sbox
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_domestic as DD  # noqa: E402
sys.path.insert(0, HERE)
import app_bridges as AB  # noqa: E402
import bridge_head as BHD  # noqa: E402
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
# Bridge level (the floor of the app's fixed walkway where it leaves the building): PER PIER since close-out r3 -
# js/live/gates.js DEPARTURE_LEVELS (tools/blender/app_bridges.json): B 5.4 [inf], C 3.2 [inf], D 3.65 [obs, low, photo a1],
# E / F 4.88 [pub T3 L2]. Every bridge-attachment element (door frame, vestibule, bulkhead, overhang notch, drum notch, the
# underside of a bridge-entered elevated part) is sized per door from the walkway floor at the facade (bridge_doors).
# FLOOR2 / WALK_TOP: the BA-B value, kept only as the default for a door the dump does not list.
PIER_LEVEL = {k: float(AB.level(k)['h']) for k in 'BCDEF'}
PIER_LEVEL_TAG = {k: AB.level(k)['tag'] for k in 'BCDEF'}
APP_BRIDGES_STALE = AB.stale()   # inputs changed since app_bridges.json was written: re-run node tools/blender/app_bridges.mjs
FLOOR2 = PIER_LEVEL['B']  # BA-B concourse (departure) floor = gates.js DEPARTURE_LEVELS.B 5.4 [inf] (default for unlisted doors)
WALK_TOP = FLOOR2 + 3.0 # app walkway top at that floor (gates.js WALK_H 3.0)
CORE_OPEN = 3.0         # morphological opening radius: outline features < 6 m wide = bridge-head fingers [inf]
E_END_D = 8.0           # BA-E tip end bay depth behind the glazed end wall (photo a1: the tall glass spans ~1 structural bay) [inf]
DOOR_W = 3.2            # bridge door opening on the facade at every attach point [inf]
MULL = 1.5              # curtain-wall mullion module (no source) [inf]
SWITCH_M = {0: 0.0, 1: 380.0, 2: 1300.0}   # LOD switch distances (camera to the building group node), m [our choice]

# lean-free roof-edge offsets from the level-2 outline (face normals within +-20 deg of ESE / WNW) [obs per pier]:
# + = roof edge outside (overhang), - = inside (the facade is put on the roof edge there)
EDGE_OFF = {'B': (2.27, -1.66), 'D': (2.40, -1.36), 'E': (0.0, -2.0), 'F': (1.83, -1.15), 'C': (0.0, 0.0)}
# BA-B: spec bab.roof_edges (+2.27 / outline -439.70 -> -438.04); BA-D: bad.roof_edges (+2.40 / -1.36); BA-E: fascia on the
# outline (2020 edge -686.2 less k20 h = -688.6, outline -688.5), WNW ~2 m inside (research 5.3, width 43.0 vs drawn 42.9);
# BA-F: ESE +1.83 = the DRAWN lean-free line (draw_data.dom_true_edges, BD-01; BD-02 view 1 draws the NE arm 27.0 m between
# the lines = 27.06 measured): along the face the line lies 1.83 m outside the level-2 outline. The spec / README note "ESE on
# the outline (+0.01 / -0.02)" was measured at the line's END points only, where the line meets the outline's corner jogs
# (checked 2026-11-05: 1.83 m at 25 / 50 / 75 % of the line) -> the 3-D follows the drawn line (manifest conflict);
# WNW -0.96 / -1.31 (README round 2) -> mean -1.15


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


def _tower_ibf_roof():
    """review r2 (findings 3 / 6): the height up to which the walls facing the tower base building (IBF) are interior = the
    LOWEST IBF roof deck over the tower families the app may load (manifest.json#tower anchors_f1 / anchors_f2 / anchors
    ibf_roof_h: F2 13.13, F1 14.068 on 2026-11-05), less a 0.10-m tuck: the T2 wall then always reaches down behind the
    IBF parapet (F2 parapet top 13.83) - the old fixed 14.07 (the F1 roof) left a 0.24-m open slot above the default F2
    parapet. Fallback 13.13 (F2) when the tower entry is missing."""
    try:
        t = json.load(open(os.path.join(ROOT, 'data', 'buildings3d', 'manifest.json'))).get('tower', {})
        hs = [float(t[k]['ibf_roof_h']) for k in ('anchors', 'anchors_f1', 'anchors_f2') if isinstance(t.get(k), dict) and 'ibf_roof_h' in t[k]]
        return (min(hs) if hs else 13.13), sorted(set(hs))
    except Exception:  # noqa: BLE001
        return 13.13, []


TOWER_IBF_ROOF, TOWER_IBF_ROOFS = _tower_ibf_roof()
TOWER_TUCK = 0.10
TOWER_Z1 = TOWER_IBF_ROOF - TOWER_TUCK      # occupancy top of the IBF for the wall clipping (13.03 m with F2)
TOWER_GAP = 0.3                             # the halls / piers are cut 0.3 m off the IBF outline (below) [our choice]
TOWER_JOINT = 0.15                          # review r2: the flashing over that gap stops 0.15 m off the IBF wall (clear of its 0.12-m
                                            # curtain mullions, tower_geom): an expansion joint; the domestic walls facing the IBF are
                                            # emitted full height behind it (no view into an open interior) [our choice]
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

# Courtyard 3 Connector (C3C) office block (review r1): the glazed block between the tower and BA-E in photo a1, at the NW
# end of the T2 outline. [pub] HOK project page: "The project links Terminals 2 and 3 with a pre- and post-security
# connector"; "Above the connector, a six-story office building"; 124,000 sq ft; "Dynamic glazing". Hensel Phelps: 100,000 SF
# of office space. Footprint [obs]: the T2 outline (SFO Museum) west of the cut line through its two outline jogs at the
# block's east wall (north face (-783.5, 101.05), south face notch (-804.8, 141.6)); NAIP 2024 check: the imaged roof's east
# edge (x ~ -777 at z 115) less the relief (0.447 m/m x 33 m) falls on the same line (s -646.7). 1,932 m2 x 6 storeys =
# 125,000 sq ft (the published 124,000 sq ft). Height [inf]: 33.0 m above the apron = the conservative end of three
# estimates: six office storeys above the connector head (>= 6 x 3.8 + ~10.5 = 33.3); NAIP 2024 relief: the imaged WNW roof
# edge lies 12.9 m (median of 9 stations) inside the outline face, / lean 0.379 m/m (k24.n = 0.392 + 0.000432 (x + 800):
# linear in x through the four measured piers B / D / E / F to within 0.005) = 34.0 m; photo a1 with its estimated camera
# ~35 m. Listed in the manifest (heights unk-to-inf, range 32-36 m).
C3C_H = 33.0
C3C_CUT = ((-783.5, 101.05), (-804.8, 141.6))       # east-wall line through the outline jogs [obs SFO Museum outline]
# review r2 (finding 1): the office curtain wall. Six office storeys [pub HOK "six-story office building"] of 3.8 m [inf: the
# storey height already used for C3C_H] ending at the roof edge -> the office glass starts at 33.0 - 6 x 3.8 = 10.2 m (below:
# the connector levels as the piers). Photo a1 (reference only, 8x zoom of the NNE face): storey-height panes, the vertical
# mullions STAGGERED from floor to floor (pane widths ~1.2-4.5 m, no common grid), light frames (thin horizontals at the
# floor lines), very dark green glass (photo median sRGB 22 / 32 / 31; frames ~125 / 132 / 132 under overcast) [obs, low]
C3C_STOREY, C3C_STOREYS = 3.8, 6
C3C_OFFICE_Z0 = C3C_H - C3C_STOREYS * C3C_STOREY    # 10.2 m [inf]
# review r2: the rooftop penthouse (photo a1: a light box set back from the NNE face with a dark louvre band; NAIP 2024: its
# imaged WNW wall is a 2.5-m (FWHM) grey band on the C3C roof, i.e. ~5.7 m above the deck at the 0.437 m/m lean) [obs, low].
# Frame: u along the NNE face from its ESE end (-783.1, 100.3) towards (-815.1, 83.4) [SFO Museum outline], w inwards (SSW).
# Extent u 9.9 .. 32.4 m (photo a1: 23 % .. 77 % of the face; NAIP: the WNW wall at u 32.4, 3 rows z 100 / 105 / 110),
# w 4.4 .. 30.4 m (NAIP: the imaged NW / SW wall ends moved back by the relief); top 38.0 m = roof edge + 5.0 (photo a1:
# 4.4-5.3 m visible above the roof edge; NAIP 5.7 above the deck) [obs, low]. Louvre band on its NNE wall u 11.2 .. 20.6,
# the lower ~80 % of the visible face (photo a1) [obs, low].
C3C_FACE_E = (-783.1, 100.3); C3C_FACE_W = (-815.1, 83.4)
C3C_PENT_U, C3C_PENT_W = (9.9, 32.4), (4.4, 30.4)
C3C_PENT_TOP = C3C_H + 5.0
C3C_LOUVRE_U, C3C_LOUVRE_Z = (11.2, 20.6), (C3C_H + 0.2, C3C_H + 4.0)


def c3c_uw(u, w):
    """world (x, z) of the C3C face frame point (u along the NNE face from its ESE end, w inwards)."""
    e, f = np.array(C3C_FACE_E), np.array(C3C_FACE_W)
    uh = (f - e) / np.hypot(*(f - e)); wh = np.array([uh[1], -uh[0]])
    if wh[1] < 0: wh = -wh                         # inwards = south-ish (+z)
    return tuple(e + uh * u + wh * w)


def _c3c():
    h = HALLS['T2']['hall']
    (ax, az), (bx, bz) = C3C_CUT
    sE = 0.5 * (float(w2st(ax, az)[0]) + float(w2st(bx, bz)[0]))
    s0, t0 = w2st(-815.0, 110.0)
    cut = Polygon([tuple(st2w(sE - 120, t0 - 60)), tuple(st2w(sE, t0 - 60)), tuple(st2w(sE, t0 + 60)), tuple(st2w(sE - 120, t0 + 60))])
    c = max(polys_of(_clean(h.intersection(cut), 100.0)), key=lambda p: p.area)
    rest = max(polys_of(_clean(h.difference(c.buffer(0.01, join_style=2)), 100.0)), key=lambda p: p.area)
    return c, rest, sE


C3C_POLY, _t2rest, C3C_S_EAST = _c3c()
HALLS['T2']['hall'] = _t2rest

# Close-out round 3 (buildings-2): the T2 LANDSIDE FACE moved off the departures curb roadway. The SFO Museum level-2 outline
# runs over the elevated departures roadway along T2 (NAIP 2024 / 2022 show traffic, a curb sidewalk and a teal glass curb
# canopy between the outline face and the T2 roof edge, ~17 m inside it), as at T1 Center before round 1.
#  * lean-free T2 roof edge [obs NAIP 2024]: the coping (first dark->bright rise after the shaded facade / canopy band, 0.1-m
#    profiles every 1 m in z) minus draw_data.lean_frame(P, H['T2']) -> the straight line x = -811.961 + 0.3063 z over
#    z 176-202 and 216-248 (59 rows, rms 0.06 m; the AirTrain-station connector crosses at z 204-215). It matches the integration
#    review's -750.5 / -745 / -739 at z 200 / 220 / 240 (+-1 m). The height is the T2 placeholder (16.88 [unk]): +1 m of roof
#    moves the line 0.54 m west. NAIP 2020 (a different camera, lean ~0.1 m/m) images the same edge at -752.5 / -751.5
#    (z 180 / 190), i.e. within ~1.5 m.
#  * the curb: the departures roadway is OSM way 256787747 ('Departures', layer 1, 3 lanes -> 10.8 m [inf lane width]) and
#    682008752 (2 lanes) - the decks roadways.glb builds; the lean-free roof edge lies T2_SIDEWALK = 5.85 m (median; p10 5.76,
#    p90 6.63 m) beyond the deck edge along the measured stretch [obs NAIP minus OSM]: the departures sidewalk. The teal
#    canopy's lean-corrected outer edge (NAIP 2024 / 2022 colour mask, h ~9.2 m) lies ~5.4 m off the wall [obs, low].
#  * the face = the measured line within z T2_EDGE_Z, elsewhere (the north corner towards C3C and the south end) the deck edge
#    + T2_SIDEWALK, which reproduces the line within 0.2 m where both exist [inf]; the old outline strip outside the face is
#    the deck (integration's roadways.glb), the sidewalk (below, this asset) and the lower roadways (not modelled).
T2_EDGE_LINE = (-811.961, 0.3063)          # lean-free T2 roof edge x(z) [obs NAIP 2024, relief-corrected for H['T2']]
T2_EDGE_Z = (168.0, 254.0)                 # z range where the line is used [obs: measured 176-248, extended 8 / 6 m]
T2_SIDEWALK = 5.85                         # deck edge -> T2 wall [obs NAIP - OSM, median]
T2_CANOPY_D = 5.4                          # curb canopy depth off the wall [obs NAIP teal mask, low]
# OSM 'Departures' ways along T2 (refs/cache/osm/overpass_landside_at_20260926T030301Z.json, (c) OpenStreetMap contributors,
# ODbL; world frame ltp-nad83-2011 via tools/geo_frame.py) and their carriageway half-widths (lanes x 3.6 m / 2 [inf]):
T2_DEP_WAYS = {
    256787747: (5.4, [(-761.7, 286.7), (-757.9, 279.1), (-752.7, 268.8), (-751.5, 266.2), (-748.9, 258.4), (-748.9, 249.0),
                      (-750.3, 239.7), (-755.0, 224.0), (-762.2, 200.9), (-767.8, 182.8), (-773.5, 173.5), (-781.0, 166.9),
                      (-785.6, 163.8), (-798.9, 156.6), (-817.1, 147.0), (-830.0, 140.4), (-832.8, 139.0), (-843.3, 133.1),
                      (-872.2, 117.8), (-887.7, 109.7)]),
    682008752: (3.6, [(-782.6, 329.1), (-761.7, 286.7)]),
}


def _t2_curb():
    """the T2 hall cut back to the curb face; the departures sidewalk strip (deck edge - 0.3 m .. wall; overlapping the deck
    by 0.3 m so the roadway is trimmed against it without a slot) and the T2 - AirTrain-station / garage connector over the
    roadway: the T2 outline's courtyard connector (SFO Museum, the app's 'Terminal 2 walkway') extended along its own axis
    to the new face, cut at the Central Parking Garage outline."""
    old = HALLS['T2']['hall']
    a, k = T2_EDGE_LINE; z0, z1 = T2_EDGE_Z
    half = Polygon([(a + k * z0 - 300, z0), (a + k * z0, z0), (a + k * z1, z1), (a + k * z1 - 300, z1)])
    deck = [(LineString(p), w) for w, p in T2_DEP_WAYS.values()]
    cut = unary_union([half] + [l.buffer(w + T2_SIDEWALK, cap_style=2, join_style=1) for l, w in deck])
    new = max(polys_of(_clean(old.difference(cut), 50.0)), key=lambda p: p.area)
    new = max(polys_of(_clean(new.buffer(-1.5, join_style=2).buffer(1.5, join_style=2).intersection(new), 50.0)), key=lambda p: p.area)
    dk = unary_union([l.buffer(w - 0.3, cap_style=2) for l, w in deck])
    reach = unary_union([l.buffer(w + T2_SIDEWALK + 0.8, cap_style=2) for l, w in deck])
    side = old.difference(new.buffer(0.01, join_style=2)).intersection(reach).difference(dk)
    side = unary_union([p for p in polys_of(_clean(side, 5.0)) if p.distance(new) < 0.1] or [Polygon()])
    conn = [c['poly'] for c in HALLS['T2']['conn'] if c['inner']]
    link = Polygon()
    if conn:
        cn = max(conn, key=lambda p: p.area)
        mr = np.array(cn.minimum_rotated_rectangle.exterior.coords)[:4]
        e0, e1 = mr[1] - mr[0], mr[2] - mr[1]
        if np.linalg.norm(e0) < np.linalg.norm(e1): mr = np.roll(mr, -1, axis=0); e0 = mr[1] - mr[0]
        u = e0 / np.linalg.norm(e0)
        if u[0] < 0: u = -u                                   # towards T2 (east)
        cm = mr.mean(0)
        band = Polygon([tuple(p + u * 40.0 * (1 if (p - cm) @ u > 0 else -1)) for p in mr])
        ext = band.intersection(old).difference(new)
        cg = unary_union([_poly(p) for p in D.sfom('Central Parking Garage', 'structures')])
        g = unary_union([cn.buffer(0.05, join_style=2), ext.buffer(0.05, join_style=2)]).buffer(-0.05, join_style=2)
        g = g.difference(cg.buffer(0.05, join_style=2)).difference(new.buffer(0.01, join_style=2))
        link = max(polys_of(_clean(g, 5.0)), key=lambda p: p.area) if polys_of(_clean(g, 5.0)) else Polygon()
    return new, side, link, old.area - new.area


HALLS['T2']['hall'], T2_SIDEWALK_POLY, T2_LINK_POLY, T2_CUT_M2 = _t2_curb()
# the T2 - garage connector's level [inf, unk]: the app draws it 6.0-10.5 m (sky-bridge convention), which leaves 1.3 m over the
# departures deck (4.73 m) - vehicles could not pass. Floor at the Central Parking Garage Level 3 (2/5 of 81 ft = 9.88 m, the
# landside BL-03 equal-fifths placeholder) so that the soffit (floor - 0.45) clears the departures deck by 4.7 m (Caltrans HDM
# 309.2 15 ft = 4.6 m, as the roadways solve); a 4.5-m glazed tube as the app's. NOTE: NAIP 2024's shadow of the crossing
# (dark band north of it, ~4.5 m at x -765, sun az 186.6 / elev 72.5) would put its TOP near 24 m, i.e. at the AirTrain T2
# station level (SFO Museum 'Terminal Two AirTrain Station' 1763588561 reaches x -743.8, the T2 wall) - unresolved, listed.
T2_LINK_FLOOR = 0.4 * 81 * FT               # 9.876 m [inf]
T2_LINK_Z = (T2_LINK_FLOOR - 0.45, T2_LINK_FLOOR + 4.5)


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




# =====================================================================================================================
# 3-D PART BUILDERS (Blender local frame; build_domestic.py turns each Part into one glTF node)
# =====================================================================================================================
import dom_mesh as M  # noqa: E402
from dom_mesh import MB  # noqa: E402

BB_S_E, BB_S_W, BB_T_S, BB_T_N, BB_T_WOBS = DD.bab_band()      # BA-B raised centre [obs edges / extent; WNW south inf]
T1_CANOPY_H = CURB + DD.T1_CANOPY                                # 8.88: canopy soffit 4.0 above the curb [inf photo d1]
T1_SPLIT_H = CURB + DD.T1_CANOPY + (DD.T1_HEAD - DD.T1_CANOPY) * DD.T1_SPLIT   # 12.84 tier transom [inf photo d1]
T1_WALL_HEAD = CURB + DD.T1_HEAD                                 # 17.88 [inf photo d1 above an unk curb]
WELL_D = 3.0            # BA-B roof wells: depth below the outer deck - NOT measured [unk placeholder]
PV_Z = (0.35, 0.75)     # PV racks: underside / top above the deck (low-tilt ballasted racks) [inf]
FIN = (0.06, 0.18)      # mullion fin width / projection (aluminium vertical fins [pub BA-E / T3E]; size inf)
# bridge door frame around the walkway (gates.js WALK_W 2.6 x WALK_H 3.0) and the vestibule from the facade to the app's
# walkway start [inf]: offsets from the walkway floor at the door (per door since close-out r3 fix 2: bridge_doors() 'fl0' /
# 'fl1' = the app walkway floor at the facade / at the walkway start, gates.js DEPARTURE_LEVELS + its 1:12 slope); the dicts
# below are the BA-B (5.4 m) values, kept as defaults / for the manifest
DOOR_DZ = (-0.2, 3.2)        # frame foot / head above the walkway floor (walkway solid: floor - 0.3 .. floor + 3.0)
VEST_DZ = (-0.5, 3.3)        # vestibule underside / top above the walkway floor (0.2 m outside the walkway solid)
DOOR = dict(w=3.2, z0=FLOOR2 + DOOR_DZ[0], z1=FLOOR2 + DOOR_DZ[1])
VEST = dict(w=3.2, z0=FLOOR2 + VEST_DZ[0], z1=FLOOR2 + VEST_DZ[1])
WALK_W_APP = 2.6        # js/live/gates.js WALK_W
MULL_T1 = (1.2, 2.4)    # T1 landside irregular mullions (draw_domestic.t1_mullions) [inf schematic of the pub pattern]
LANTERN_RISE = 1.0      # BA-F hub lantern rise above the arm roof: minimal skylight upstand [unk] (review r1; was the bound)
LANTERN_RISE_BOUND = float(BH['ring_2020_shadow']['rise_upper_bound'])   # <= 4.6 m (NAIP 2020 shadow, buildings_domestic.md r1-22)
# elevated sky-bridge / pod parts that a jet bridge's fixed walkway enters (B10, B11, B11S, B15, B16, F22): the part's floor
# comes down to the vestibule floor of the walkway that enters it (review r1: the 6.0-m underside cut the walkways' lower
# 0.85 m) - per bridge since close-out r3 fix 2 (walk_y0: lowest walkway floor inside the part + VEST_DZ[0]; BA-B 4.9, F22
# at the BA-F level 4.88 -> 4.38) [inf]; WALK_Y0_BRIDGE = the BA-B value (manifest)
WALK_Y0_BRIDGE = FLOOR2 + VEST_DZ[0]
FIN_MAX_M = 160.0       # LOD0 mullion fins: own node per building, extras.max_dist_m (the loader hides them beyond; review r1:
                        # 6-cm fins every 1.5 m alias beyond ~150 m at phone / desktop resolutions) [our choice]

# materials: key -> tile (metres per texture repeat of UV_detail, (u, v)) - must match tools/blender/dom_tex.py
TILE = {'roof_membrane': (12.0, 12.0), 'roof_membrane_b': (12.0, 12.0), 'roof_membrane_t': (12.0, 12.0),
        'panel_light': (6.0, 6.0), 'panel_dark': (6.0, 6.0), 'panel_acm': (6.0, 6.0), 'panel_acm_dark': (6.0, 6.0),
        'panel_platinum': (6.0, 6.0), 'service': (6.0, 6.0), 'fascia': (6.0, 6.0), 'coping': (3.0, 3.0), 'soffit': (6.0, 6.0),
        'concrete': (6.0, 6.0), 'penthouse_corr': (3.0, 3.0), 'pv': (4.0, 4.0), 'planting': (8.0, 8.0), 'door_dark': (3.2, 3.2),
        'mullion': (3.0, 3.0), 'mullion_dark': (3.0, 3.0), 'glass_canopy': (6.0, 6.0), 'glass_sky': (6.0, 6.0), 'lettering': (3.0, 3.0),
        'unit': (6.0, 6.0), 'unit_top': (6.0, 6.0)}
for _g in ('glass_ec', 'glass_lowe', 'glass_tint', 'glass_frit_grey', 'glass_clear', 'glass_lobby'):
    TILE[_g] = (6.0, 6.0)        # curtain grid 1.5 m verticals x 3.0 m transoms from the band bottom [inf]
TILE['glass_ec'] = (24.0, 6.0)   # electrochromic panes in mixed tint states: 16 x 2 panes per tile (review r1: no 6-m repeat)
TILE['glass_frit_green'] = (12.0, 9.0)   # T1 landside tiers: one tile = canopy line -> wall head (9.0 m), transom 3.96 m up
TILE['glass_t3w'] = (6.0, 5.8)           # T3W window wall: 2.0-m verticals, band 5.8 m (BD-03 view 3 schematic)
TILE['penthouse_corr'] = (3.0, 2.8)      # corrugation 0.2 m, accent bands every 1.4 m (BD-03 schematic)
TILE['glass_c3c'] = (24.0, C3C_STOREYS * C3C_STOREY)   # review r2: 6 storeys x 24 m, staggered panes (dom_tex.c3c_colour)
TILE['louvre'] = (3.0, 3.0)              # review r2: C3C penthouse louvre blades 0.15 m (dom_tex)
# (tile sizes: tools/blender/dom_tex.py TILES)
GLASS = {k for k in TILE if k.startswith('glass')}


def tl(m):
    return TILE.get(m, (6.0, 6.0))


# ------------------------------------------------------------------------------------------------ frames
def loc(g):
    """world (x, z) shapely geometry -> Blender local XY (CCW exteriors)."""
    return M.orient_all(affinity.affine_transform(g, [1, 0, 0, -1, -OX, OZ]))


def wld(g):
    return affinity.affine_transform(g, [1, 0, 0, -1, OX, OZ])


def Lp(x, z):
    return (x - OX, OZ - z)


def Wp(X, Y):
    return (X + OX, OZ - Y)


def hdg_local(vx, vy):
    return math.degrees(math.atan2(vx, vy)) % 360.0


def angd(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def largest(g):
    ps = polys_of(g)
    return max(ps, key=lambda p: p.area) if ps else Polygon()


def tagdim(value, tag, source):
    return dict(v=round(value, 3) if isinstance(value, float) else value, tag=tag, source=source)


class Part:
    """one glTF node: mesh + tags. kind 'shell' = baked AO atlas (UV_ao); 'detail' = thin members / racks, no AO."""

    def __init__(self, name, mb, kind, src, feature, spec=(), dims=None, note='', extra=None):
        self.name, self.mb, self.kind, self.src, self.feature = name, mb, kind, src, feature
        self.spec, self.dims, self.note, self.extra = list(spec), dims or {}, note, dict(extra or {})

    def extras(self, lod):
        e = dict(src=self.src, feature=self.feature, spec=self.spec, lod=lod)
        if self.dims: e['dims'] = self.dims
        if self.note: e['note'] = self.note
        e.update(self.extra)
        return e


# ------------------------------------------------------------------------------------------------ facade styles
# bands (z0, z1, material, mullion module or 0); z absolute above the apron; None = up to the wall head (slab underside).
# Sources: concourse floor = the app's bridge floor 5.4 (gates.js DEPARTURE_LEVEL) [inf]; BA-B "floor-to-ceiling
# electrochromic glass at the gates" [pub bab.glazing], head [inf]; BA-E "clear glass with grey frit, light- / dark-grey
# metal-panel bands above / below, aluminium vertical fins" [pub bae.facade], band heights [inf]; BA-C / BA-D / BA-F and the
# halls' airside faces: not described [unk -> generic bands]; T1 landside [pub t1c.landside_facade, heights inf photo d1];
# T2 landside [pub t2.landside, heights unk]; T3W landside / airside [pub CDR p.18 / p.23 materials and the 10 + 2 + 10 ft
# window stack; band proportions inf]; T3E [pub t3e.facade materials; positions inf].
# photo a1 (Wikimedia Commons "Aerial view of SFO from departing flight, September 2025"), BA-D near end, image rows (camera-
# independent ratios over the roof-edge height, apron ~812 px, roof edge 763.5 px): light sill band 795.5-790.5 px, concourse
# glazing 790.5-773.5 px, fascia 773.5-763.5 px -> sill 0.340-0.443, glazing 0.443-0.794 [obs, low]
A1_D_RATIO = ((812.0 - 795.5) / 48.5, (812.0 - 790.5) / 48.5, (812.0 - 773.5) / 48.5)
STYLES = {
    'B': [(0.0, 4.6, 'service', 0), (4.6, 5.6, 'panel_dark', 0), (5.6, 11.6, 'glass_ec', 1.5), (11.6, None, 'panel_light', 0)],
    # BA-C / BA-D (close-out r3 fix 2): the photo a1 ratios of the BA-D near end (manifest domestic.conflicts, resolved): light
    # sill band A1_D_RATIO[0]-[1], concourse glazing [1]-[2] of the roof-edge height, fascia above [obs, low]; BA-C the same layout
    # on its 7.20 m edge [inf] (= how gates.js DEPARTURE_LEVELS.C 3.2 was derived; the walkways enter at the glazing band)
    'C': [(0.0, A1_D_RATIO[0] * H['C'], 'service', 0), (A1_D_RATIO[0] * H['C'], A1_D_RATIO[1] * H['C'], 'panel_light', 0),
          (A1_D_RATIO[1] * H['C'], A1_D_RATIO[2] * H['C'], 'glass_tint', 1.5), (A1_D_RATIO[2] * H['C'], None, 'panel_light', 0)],
    'D': [(0.0, A1_D_RATIO[0] * H['D'], 'service', 0), (A1_D_RATIO[0] * H['D'], A1_D_RATIO[1] * H['D'], 'panel_light', 0),
          (A1_D_RATIO[1] * H['D'], A1_D_RATIO[2] * H['D'], 'glass_tint', 1.5), (A1_D_RATIO[2] * H['D'], None, 'panel_light', 0)],
    'E': [(0.0, 4.6, 'service', 0), (4.6, 5.6, 'panel_dark', 0), (5.6, 8.4, 'glass_frit_grey', 1.5), (8.4, None, 'panel_light', 0)],
    'E_end': [(0.0, 4.6, 'service', 0), (4.6, 5.6, 'panel_dark', 0), (5.6, None, 'glass_clear', 1.5)],
    'F': [(0.0, 4.6, 'service', 0), (4.6, 5.6, 'panel_dark', 0), (5.6, 8.8, 'glass_tint', 1.5), (8.8, None, 'panel_light', 0)],
    'hall': [(0.0, 4.6, 'service', 0), (4.6, 5.6, 'panel_dark', 0), (5.6, 11.0, 'glass_tint', 1.5), (11.0, None, 'panel_light', 0)],
    'conn': [(0.0, 4.6, 'service', 0), (4.6, 5.6, 'panel_dark', 0), (5.6, None, 'panel_light', 0)],
    # (the first band from 0: clamped to the part's underside - 6.0, or 4.9 where a bridge enters, review r1)
    'walk': [(0.0, INNER_Y0 + 0.8, 'panel_light', 0), (INNER_Y0 + 0.8, INNER_TOP - 0.7, 'glass_tint', 1.5),
             (INNER_Y0 + 0.8 + 3.0, None, 'panel_light', 0)],
    'T1_land': [(0.0, CURB, 'service', 0), (CURB, T1_CANOPY_H, 'glass_lobby', 1.5), (T1_CANOPY_H, None, 'glass_frit_green', -1)],
    # T2 landside (close-out r3, buildings-2: the face on the measured roof edge, behind the departures sidewalk): "a light metal-
    # panel box ... and a glass entry wall" [pub t2.landside], "transparent (west-facing) facade" [pub t2.daylight]; BD-03 view 2
    # draws the glass 0-7.0 m above the curb [unk] -> glass along the whole curb face, panel above [inf]
    'T2_land': [(0.0, CURB, 'service', 0), (CURB, CURB + 7.0, 'glass_lobby', 1.5), (CURB + 7.0, None, 'panel_light', 0)],
    # the T2 - garage connector over the departures roadway (close-out r3): a glazed tube as the app's sky bridges [inf]
    # (no mullion fins: its end walls abut the Central Garage, close-out r3 neighbour check 0.64 m2 with fins)
    'link': [(0.0, T2_LINK_Z[0] + 0.8, 'panel_light', 0), (T2_LINK_Z[0] + 0.8, T2_LINK_Z[1] - 0.7, 'glass_tint', 0),
             (T2_LINK_Z[1] - 0.7, None, 'panel_light', 0)],
    'T3W_land': [(0.0, CURB, 'service', 0), (CURB, CURB + 1.7, 'panel_acm_dark', 0), (CURB + 1.7, CURB + 7.5, 'glass_t3w', 2.0),
                 (CURB + 7.5, None, 'panel_acm', 0)],
    'T3W_air': [(0.0, CURB, 'service', 0), (CURB, T3_LV['L3'], 'panel_acm', 0), (T3_LV['L3'], T3_LV['L3'] + 10 * FT, 'glass_ec', 1.5),
                (T3_LV['L3'] + 10 * FT, T3_LV['L3'] + 12 * FT, 'panel_acm_dark', 0), (T3_LV['L3'] + 12 * FT, None, 'glass_ec', 1.5)],
    'T3E': [(0.0, 4.6, 'service', 0), (4.6, CURB + 0.7, 'panel_dark', 0), (CURB + 0.7, T3_LV['L3'], 'glass_frit_grey', 1.5),
            (T3_LV['L3'], None, 'panel_platinum', 0)],
    # C3C (review r2): the six office storeys from C3C_OFFICE_Z0 in the storey-height, staggered-mullion dark-green curtain
    # glass (glass_c3c: "Dynamic glazing" [pub HOK], look obs photo a1; frames in the tile, no fins); the connector levels
    # below as the piers (service base, dark spandrel, tinted concourse glass, dark band at the office floor) [inf]
    'C3C': [(0.0, 4.6, 'service', 0), (4.6, 5.6, 'panel_dark', 0), (5.6, C3C_OFFICE_Z0 - 0.6, 'glass_tint', 1.5),
            (C3C_OFFICE_Z0 - 0.6, C3C_OFFICE_Z0, 'panel_dark', 0), (C3C_OFFICE_Z0, None, 'glass_c3c', 0)],
    'pent_c3c': [(0.0, None, 'panel_light', 0)],
    # BA-E tip end wall (review r2: photo a1 shows the apron-facing end wall glazed over ~80-90 % of its height: a dark base
    # 0-2.0 m, then clear glass to the wall head, profile ratios of photo a1 at the end wall [obs, low])
    'E_endwall': [(0.0, 2.0, 'panel_dark', 0), (2.0, None, 'glass_clear', 1.5)],
    'clere_B': [(0.0, None, 'glass_lowe', 1.5)],
    'clere_E': [(0.0, H['E'] - 1.0, 'glass_lowe', 1.5), (H['E'] - 1.0, None, 'panel_dark', 0)],
    'drum': [(0.0, None, 'panel_light', 0)],
    'lantern': [(0.0, None, 'glass_lowe', 1.2)],
    'monitor': [(0.0, None, 'glass_lowe', 1.5)],
    'penthouse': [(0.0, None, 'penthouse_corr', 0)],
    'vest': [(0.0, None, 'panel_light', 0)],
}
FASCIA = {'T3W_land': 'panel_acm', 'T3W_air': 'panel_acm', 'T3E': 'panel_platinum', 'penthouse': 'penthouse_corr',
          'T1_land': 'fascia', 'drum': 'panel_light'}


# ------------------------------------------------------------------------------------------------ solids
class Solid:
    """a 2.5-D extruded body (Blender local XY): walls of `poly` from z0 to the slab underside, the roof slab `roof`
    (outline >= poly; overhang = roof - poly with a soffit) from h - thk to the measured roof edge h, a coping ring and the
    deck at h - parapet (holes: footprints of solids standing on it). Walls are clipped where a neighbouring solid occupies
    the same height (interior walls are not emitted); style(solid, edge) -> facade bands."""

    def __init__(self, key, bld, poly, h, z0=0.0, roof=None, style='hall', thk=ROOF_THK, parapet=PARAPET, roof_mat='roof_membrane',
                 tag='inf', feature='', spec=(), dims=None, underside=False, top=True, deck_mat=None):
        self.key, self.bld = key, bld
        self.poly = M.orient_all(poly)
        self.roof = M.orient_all(roof) if roof is not None else self.poly
        self.h, self.z0, self.thk, self.parapet = float(h), float(z0), float(thk), float(parapet)
        self.style, self.roof_mat, self.deck_mat = style, roof_mat, deck_mat or roof_mat
        self.tag, self.feature, self.spec, self.dims = tag, feature, list(spec), dims or {}
        self.underside, self.top = underside, top
        self.holes = []          # local polygons cut out of the deck (solids standing on it, wells, skylights)
        self.deck_extra = []     # (poly, z, mat) caps inside the holes (skylight glass, planting)

    @property
    def deck(self):
        return self.h - self.parapet if self.parapet > 0 else self.h

    def bands(self, a, b):
        st = self.style(self, a, b) if callable(self.style) else self.style
        return STYLES[st], st


class World:
    """all solids + an occupancy index for the wall clipping."""

    def __init__(self):
        self.S = []

    def add(self, s):
        self.S.append(s); return s

    def finish(self):
        from shapely.strtree import STRtree
        self.occ = []     # (geom, z0, z1, solid)
        # neighbouring assets: the ITB (data/buildings3d/itb.glb: piers 17.0-17.9 m, core 17.9 m placeholder) and the tower
        # base building (tower.glb) - walls facing them are interior and not emitted (they would be hidden / z-fight)
        # (review r2: the walls facing the tower base building are no longer clipped - the IBF occupancy (up to the LOWEST
        # family's IBF roof less a tuck, TOWER_Z1) reaches only TOWER_JOINT - 0.02 m out, so the T2 / BA-D / T1 walls 0.3 m off
        # the IBF are emitted full height (before: clipped up to 14.07 m, the F1 roof, leaving a 0.24-m slot above the default F2
        # parapet and an open view into T2); the gap between them is covered by a flashing, tower_flashing())
        for g, z1 in ((ITB.buffer(0.05, join_style=2), 17.0), (TOWER_EXCL.buffer(TOWER_JOINT - 0.02, join_style=2), TOWER_Z1)):
            self.occ.append((loc(g), 0.0, z1, None))
        for s in self.S:
            # a solid with a parapet occupies up to its DECK: along a taller neighbour its coping ring is cut away (emit_roof), so
            # the neighbour's wall must come down to the deck there (review r1: a 0.6-m slot showed between the T2 deck and the C3C)
            self.occ.append((s.poly, s.z0, s.deck if s.parapet > 0 else s.h, s))
            ov = s.roof.difference(s.poly.buffer(0.01, join_style=2))
            if ov.area > 0.5: self.occ.append((ov, s.h - s.thk, s.h, s))
        self.tree = STRtree([o[0] for o in self.occ])
        self.prep = [shapely.prepared.prep(o[0]) for o in self.occ]

    def occupied(self, p, me):
        out = []
        pt = Point(p)
        for i in self.tree.query(pt):
            g, z0, z1, s = self.occ[i]
            if s is me: continue
            if self.prep[i].contains(pt): out.append((z0, z1))
        return out

    def splits(self, a, b, me):
        """parameters (0..1) along a->b where it crosses a neighbouring occupancy boundary."""
        ln = LineString([a, b]); L = ln.length
        ts = {0.0, 1.0}
        for i in self.tree.query(ln.buffer(0.2)):
            g, z0, z1, s = self.occ[i]
            if s is me: continue
            x = ln.intersection(g.boundary)
            for q in getattr(x, 'geoms', [x]):
                if q.is_empty: continue
                for c in (q.coords if q.geom_type != 'Point' else [q.coords[0]]):
                    ts.add(min(1.0, max(0.0, ln.project(Point(c)) / L)))
            # close-out r3 (back-face QA t2curb): a neighbour whose edge runs ALONG this one a few cm off never crosses it,
            # so its corners split nothing and the midpoint sample clipped the whole edge (the T2 face 199.2-220.7 opened
            # 9.43-14.38 m for the 16.9-m-wide connector end: a 5-m hole into the hall). Its vertices within 0.15 m split too.
            for rg in [g.exterior] + list(g.interiors) if g.geom_type == 'Polygon' else [r for p_ in getattr(g, 'geoms', []) for r in [p_.exterior] + list(p_.interiors)]:
                for c in rg.coords:
                    pc = Point(c)
                    if ln.distance(pc) < 0.15:
                        t_ = ln.project(pc) / L
                        if 1e-4 < t_ < 1.0 - 1e-4: ts.add(t_)
        return sorted(ts)


def _sub(iv, cut):
    """interval list minus one interval."""
    out = []
    for a, b in iv:
        c0, c1 = cut
        if c1 <= a or c0 >= b: out.append((a, b)); continue
        if c0 > a: out.append((a, c0))
        if c1 < b: out.append((c1, b))
    return [(a, b) for a, b in out if b - a > 0.02]


def exposed_pieces(W, s, a, b, lo, hi):
    """[(t0, t1, [(z0, z1) visible])] along a->b for a wall from lo to hi; the outside is sampled 0.12 m out."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = ((b[1] - a[1]) / L, -(b[0] - a[0]) / L)
    ts = W.splits(a, b, s)
    out = []
    for t0, t1 in zip(ts[:-1], ts[1:]):
        if (t1 - t0) * L < 0.02: continue
        tm = 0.5 * (t0 + t1)
        p = (a[0] + (b[0] - a[0]) * tm + n[0] * 0.12, a[1] + (b[1] - a[1]) * tm + n[1] * 0.12)
        iv = [(lo, hi)]
        for c in W.occupied(p, s): iv = _sub(iv, c)
        if iv: out.append((t0, t1, iv))
    # merge consecutive pieces with the same visibility
    m = []
    for p in out:
        if m and abs(m[-1][1] - p[0]) < 1e-9 and m[-1][2] == p[2]: m[-1] = (m[-1][0], p[1], p[2])
        else: m.append(p)
    return m


IBF_L = loc(TOWER_EXCL)   # the tower base building outline (local)


def emit_walls(mb, det, W, s, lod, mull_geom=True):
    """facade walls of solid s (poly rings) from z0 to the slab underside, banded by its style, clipped by neighbours;
    LOD0 mullion fins on glazed bands into the detail mesh det."""
    head = s.h - s.thk
    for p in M.polys(s.poly):
        for ring in M.rings_of(p):
            n_ = len(ring); s_acc = 0.0
            for i in range(n_):
                a, b = ring[i], ring[(i + 1) % n_]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 0.05: continue
                bands, st = s.bands(a, b)
                # review r2: a wall 0.3 m off the tower base building (emitted full height behind the flashing joint) is a blank
                # panel wall - no glazing, no fins (they would reach the IBF mullions)
                if IBF_L.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < TOWER_GAP + 0.1:
                    bands, st = [(0.0, None, 'panel_light', 0)], 'ibf_side'
                for t0, t1, iv in exposed_pieces(W, s, a, b, s.z0, head):
                    pa = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
                    pb = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
                    sa = s_acc + t0 * L
                    for z0, z1, mat, mod in bands:
                        z1 = head if z1 is None else min(z1, head)
                        z0 = max(z0, s.z0)
                        if s.style in ('clere_B', 'clere_E', 'drum', 'lantern', 'monitor', 'penthouse', 'vest') or st in ('clere_B', 'clere_E', 'drum', 'lantern', 'monitor', 'penthouse', 'vest'):
                            z0b, z1b = (s.z0 if z0 <= 0.0 else z0), z1   # relative styles start at the solid's base
                        else:
                            z0b, z1b = z0, z1
                        for v0, v1 in iv:
                            za, zb = max(z0b, v0), min(z1b, v1)
                            if zb - za < 0.02: continue
                            mb.quad_wall(pa, pb, za, zb, za, zb, mat, sa, tl(mat), v0=z0b)
                            if lod == 0 and mull_geom and mat in GLASS and det is not None:
                                fins(det, pa, pb, sa, za, zb, mod, s, st)
                s_acc += L


def fins(det, a, b, s0, z0, z1, mod, s, st):
    """vertical aluminium fins on a glazed band: every `mod` m of the ring's running length (aligned with the curtain
    texture), or the irregular T1 rhythm (mod -1)."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L < 0.6 or mod == 0: return
    d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L); n = (d[1], -d[0])
    if mod < 0:
        xs = [x for x in DD.t1_mullions(0.0, L, seed=int(abs(a[0] * 7 + a[1] * 13)) % 997)]
    else:
        k0 = math.ceil((s0 + 0.3) / mod); k1 = math.floor((s0 + L - 0.3) / mod)
        xs = [k * mod - s0 for k in range(k0, k1 + 1)]
    w, pr = FIN
    fm = 'mullion_dark' if st in ('T1_land', 'T3W_land', 'T3W_air') else 'mullion'   # T3W dark grey fins [pub]; T1 dark [obs photo d1]
    for x in xs:
        c = (a[0] + d[0] * x, a[1] + d[1] * x)
        p0 = (c[0] - d[0] * w / 2, c[1] - d[1] * w / 2); p1 = (c[0] + d[0] * w / 2, c[1] + d[1] * w / 2)
        q0 = (p0[0] + n[0] * pr, p0[1] + n[1] * pr); q1 = (p1[0] + n[0] * pr, p1[1] + n[1] * pr)
        det.quad_wall(p0, q0, z0, z1, z0, z1, fm, 0, (3.0, 3.0))
        det.quad_wall(q0, q1, z0, z1, z0, z1, fm, 0, (3.0, 3.0))
        det.quad_wall(q1, p1, z0, z1, z0, z1, fm, 0, (3.0, 3.0))
        # (no top cap: 6 x 18 cm, seen only from above; the band head / slab closes it in most views) [budget]


def emit_roof(mb, W, s, lod):
    """roof slab edge (fascia, clipped by neighbours), soffit under the overhang, coping ring, inner parapet faces, deck."""
    zt, zb = s.h, s.h - s.thk
    fm = FASCIA.get(s.style if isinstance(s.style, str) else 'x', 'fascia')
    for p in M.polys(s.roof):
        for ring in M.rings_of(p):
            n_ = len(ring); s_acc = 0.0
            for i in range(n_):
                a, b = ring[i], ring[(i + 1) % n_]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 0.05: continue
                for t0, t1, iv in exposed_pieces(W, s, a, b, zb, zt):
                    pa = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
                    pb = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
                    for v0, v1 in iv:
                        mb.quad_wall(pa, pb, v0, v1, v0, v1, fm, s_acc + t0 * L, tl(fm))
                s_acc += L
    ov = s.roof.difference(s.poly.buffer(0.005, join_style=2))
    if ov.area > 0.2:
        M.cap(mb, ov, zb, 'soffit', tl('soffit'), down=True)
    if s.underside and s.z0 > 0.1:
        M.cap(mb, s.poly, s.z0, 'soffit', tl('soffit'), down=True)
    if not s.top: return
    holes = unary_union(s.holes) if s.holes else Polygon()
    if s.parapet <= 0:
        M.cap(mb, s.roof.difference(holes), zt, s.roof_mat, tl(s.roof_mat))
    else:
        inner = s.roof.buffer(-PARAPET_T, join_style=2)
        # no coping where a taller neighbour stands against the roof edge: the deck runs to the edge there
        taller = unary_union([o.poly for o in W.S if o is not s and o.h > s.deck + 0.05 and o.z0 < s.deck and o.poly.distance(s.roof) < 0.2])
        ring = s.roof.difference(inner)
        if not taller.is_empty: ring = ring.difference(taller.buffer(PARAPET_T + 0.15, join_style=2))
        ring = M.orient_all(_clean(ring, 0.05))
        deck = M.orient_all(s.roof.difference(ring.buffer(0.001, join_style=2)).difference(holes))
        M.cap(mb, ring, zt, 'coping', tl('coping'))
        # inner parapet faces: deck boundary pieces that touch the coping ring
        rp = shapely.prepared.prep(ring.buffer(0.02))
        for q in M.polys(deck):
            for rr in M.rings_of(q):
                for i in range(len(rr)):
                    a, b = rr[i], rr[(i + 1) % len(rr)]
                    L = math.hypot(b[0] - a[0], b[1] - a[1])
                    if L < 0.02: continue
                    mid = ((a[0] + b[0]) / 2 + (b[1] - a[1]) / L * 0.05, (a[1] + b[1]) / 2 - (b[0] - a[0]) / L * 0.05)
                    if rp.contains(Point(mid)):
                        # the inner face of the parapet faces the deck (left of a->b): wound b->a (back-face QA)
                        mb.quad_wall(b, a, s.deck, zt, s.deck, zt, 'coping', 0.0, (3.0, 3.0))
            M.cap(mb, q, s.deck, s.deck_mat, tl(s.deck_mat))
    for g, z, mat in s.deck_extra:
        M.cap(mb, g, z, mat, tl(mat))


# ------------------------------------------------------------------------------------------------ edge offsets
EDGE_CLOSE = 8.0   # closing radius of the roof-edge strips (bridges gaps <= 16 m along a side) [inf]
EDGE_LINES = {   # pier -> (drawn lean-free ESE line, WNW line) in world (x, z); offsets from the level-2 outline (EDGE_OFF)
    'B': D.dom_true_edges('bab.roof_edges', 'ba_b_south'), 'D': D.dom_true_edges('bad.roof_edges', 'ba_d_head'),
    'F': D.dom_true_edges('baf.roof_edges', 'ba_f_ne_arm')}


def face_offsets(L_, poly_l, others_l):
    """(wall footprint, roof outline) of a pier (local): roof edges on the ESE faces EDGE_OFF[0] outside the level-2 outline
    (overhang; the wall stays on the outline) and the WNW faces' roof edge EDGE_OFF[1] inside (the wall moves onto the roof
    edge) - applied to exterior faces parallel (+-20 deg) to the measured line and within 6 m of its extension (B / D / F);
    BA-E: WNW -2.0 m on every WNW face (research 5.3), ESE on the outline [obs / inf, see EDGE_OFF]."""
    off_n, off_m = EDGE_OFF[L_]
    lines = EDGE_LINES.get(L_)
    S_ESE = 117.83; S_WNW = 297.83
    add, sub = [], []
    oth = shapely.prepared.prep(unary_union(others_l).buffer(0.3)) if others_l else None
    for p in M.polys(poly_l):
        for ring in M.rings_of(p):
            for i in range(len(ring)):
                a, b = np.array(ring[i]), np.array(ring[(i + 1) % len(ring)])
                Ln = float(np.hypot(*(b - a)))
                if Ln < 3.0: continue
                n = np.array([(b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln])
                hd = hdg_local(*n)
                mid = (a + b) / 2
                if oth is not None and oth.contains(Point(mid + n * 0.4)): continue      # shared with a neighbour
                for which, H0, off in (('n', S_ESE, off_n), ('m', S_WNW, off_m)):
                    if abs(off) < 1e-6 or angd(hd, H0) > 20: continue
                    if lines is not None:
                        (x0, z0), (x1, z1) = lines[which]
                        la, lb = np.array(Lp(x0, z0)), np.array(Lp(x1, z1))
                        dl = (lb - la) / np.hypot(*(lb - la))
                        perp = abs(float(np.cross(dl, mid - la)))
                        if perp > 6.0: continue
                    q = Polygon([tuple(a), tuple(b), tuple(b + n * off), tuple(a + n * off)])
                    (add if off > 0 else sub).append(q.buffer(0.0))
    # the strips are per outline face: close the gaps between collinear strips (short jogs < 3 m and the roots of the
    # bridge-head fingers cut off by core_and_fingers) so that the roof edge runs straight along the measured line, as drawn
    # (BD-01 draws one continuous lean-free edge per side) [inf]
    # (limited to the offset band of the outline: the closing must not cut / add deeper than |offset| at concave jogs)
    if add:
        band = poly_l.buffer(off_n + 0.02, join_style=2).difference(poly_l)
        add = [M.orient_all(_clean(unary_union(add).buffer(EDGE_CLOSE, join_style=2).buffer(-EDGE_CLOSE, join_style=2).intersection(band), 0.5))]
    if sub:
        band = poly_l.difference(poly_l.buffer(-abs(off_m) - 0.02, join_style=2))
        sub = [M.orient_all(_clean(unary_union(sub).buffer(EDGE_CLOSE, join_style=2).buffer(-EDGE_CLOSE, join_style=2).intersection(band), 0.5))]
    wall = poly_l.difference(unary_union(sub).buffer(0.001)) if sub else poly_l
    wall = largest(_clean(wall, 5.0))
    roof = unary_union([wall] + add) if add else wall
    if others_l: roof = roof.difference(unary_union(others_l).buffer(0.05))
    roof = largest(_clean(roof.buffer(0.01, join_style=2).buffer(-0.01, join_style=2), 5.0))
    return M.orient_all(wall), M.orient_all(roof)


# ------------------------------------------------------------------------------------------------ footprints (local)
APP_WALK = unary_union([Polygon(r).buffer(0) for p in D.BLD['parts'] if p['kind'] == 'walkway' for r in p['rings']])
APP_BLD = unary_union([Polygon(r).buffer(0) for r in D.BLD['complex']] +
                      [Polygon(r).buffer(0) for p in D.BLD['parts'] if p['kind'] != 'walkway' for r in p['rings']])


BRIDGE_WALKS = unary_union([LineString(b['walk']).buffer(1.6, cap_style=2) for s_ in json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
                             if s_['letter'] in 'BCDEF' for b in s_['bridges'] + s_.get('bridges_upper', []) if len(b.get('walk') or []) >= 2])


BRIDGE_LINES = unary_union([LineString(b['walk']) for s_ in json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
                            if s_['letter'] in 'BCDEF' for b in s_['bridges'] if len(b.get('walk') or []) >= 2])


def _app_walks():
    """[(walk line (world x, z), app bridge record)] of the B-F main-deck bridges (tools/blender/app_bridges.json)."""
    out = []
    for b in AB.bridges('BCDEF', upper=False):
        if len(b['walk']) >= 2: out.append((LineString([(p[0], p[2]) for p in b['walk']]), b))
    return out


APP_WALKS = _app_walks()


def walk_y0(w_local):
    """underside of an elevated sky-bridge / pod part: the app convention 6.0 m, or - where a jet bridge's walkway (data/
    sfo_stands.json walk polyline, +1.5 m: the walkway half width + 0.2) enters it (review r1) - the vestibule floor of that
    walkway: its lowest floor inside the part (gates.js DEPARTURE_LEVELS + 1:12 slope, app_bridges.json) + VEST_DZ[0]
    (close-out r3 fix 2: per bridge, was the one 5.4-m level)."""
    w = wld(w_local)
    if not w.intersects(BRIDGE_LINES.buffer(1.5)): return INNER_Y0
    fl = []
    for ln, b in APP_WALKS:
        seg = ln.intersection(w.buffer(1.5))
        if seg.is_empty: continue
        fl += [AB.floor_at(b, x, z) for x, z in shapely.get_coordinates(seg)]
    return min(fl) + VEST_DZ[0] if fl else WALK_Y0_BRIDGE


def split_walk(poly):
    """(body, [elevated walkway pieces]): the parts of an outline the app models as elevated walkways (thin sky bridges /
    corridors < ~14 m, tools/build_terminal_parts.py: 6.0 -> 10.5 m) [unk app convention]."""
    w = _clean(poly.intersection(APP_WALK.buffer(0.3, join_style=2)), 1.0)
    w = _clean(w.buffer(-1.0, join_style=2).buffer(1.0, join_style=2).intersection(poly), 40.0)
    body = _clean(poly.difference(w.buffer(0.02, join_style=2)), 20.0)
    return body, polys_of(w, 40.0)


def footprints():
    """world footprints of every body: piers (core, walkways split off), halls, connectors."""
    F = {}
    for L_ in 'BCDEF':
        pp = largest(PIER_POLY[L_])
        body, walks = split_walk(pp)
        core, fingers = core_and_fingers(largest(body))
        # narrow outline strips that carry a bridge's fixed walkway (e.g. the long diagonal walkways at the BA-B tip, B24 /
        # B26 / B27) are the walkways themselves (drawn by the app's bridge system): not part of the building body [inf]
        narrow = _clean(core.difference(core.buffer(-4.0, join_style=2).buffer(4.0, join_style=2)), 1.0)
        cut = [q for q in polys_of(narrow, 5.0) if q.intersection(BRIDGE_WALKS).area > 0.4 * q.area]
        if cut:
            core = largest(_clean(core.difference(unary_union(cut).buffer(0.05, join_style=2)), 50.0))
            fingers = fingers + cut
        F['BA_' + L_] = dict(core=core, walks=walks, fingers=fingers)
    for k in ('T1', 'T2'):
        F[k] = dict(core=HALLS[k]['hall'], walks=[], links=[])
    F['T3W'] = dict(core=T3W_POLY, walks=[], links=[]); F['T3E'] = dict(core=T3E_POLY, walks=[], links=[])
    F['C3C'] = dict(core=C3C_POLY, walks=[], links=[])
    for k in ('T1', 'T2', 'T3'):
        for c in HALLS[k]['conn']:
            if not c['modelled']: continue
            wf = c['poly'].intersection(APP_WALK).area / c['poly'].area
            tgt = k if k != 'T3' else 'T3E'
            (F[tgt]['walks'] if wf > 0.5 else F[tgt]['links']).append(c['poly'])
    return F


FP = footprints()


BROOF = D._j(D.TB, 'dom_bab_roof.json')['manual']     # BA-B roof features as imaged (wells, bridges, skylights, PV) [obs]


def pv_regions(lB, lE, lF):
    """roof regions searched for PV in dom_pv.py: (name, true polygon world, roof height, east lean m/m, position tag)."""
    band = Polygon([tuple(st2w(BB_S_E, BB_T_S)), tuple(st2w(BB_S_E, BB_T_N)), tuple(st2w(BB_S_W, BB_T_N)), tuple(st2w(BB_S_W, BB_T_S))])
    lT = 0.5 * (lB + float(D.dom_lean('C')[0][0]))
    l3 = 0.5 * (lE + lF)
    wells = unary_union([Polygon(np.asarray(r) - [lB * H['B'], 0.0]) for r in BROOF['wells']]).buffer(2.0)
    return [('B_outer', FP['BA_B']['core'].difference(band.buffer(1.0)).difference(wells), H['B'], lB, 'obs (B lean, outer roof 13.14 obs S / inf N)'),
            ('B_band', band, H['B_band'], lB, 'obs (B lean, band 19.04 obs low)'),
            ('E_centre', FP['BA_E']['core'].buffer(-DD.BAE_FLANK, join_style=2), H['E'], lE, 'obs (E lean, fascia 12.85 obs)'),
            ('T1', FP['T1']['core'], H['T1'], lT, 'inf (T1 height unk 17.88, lean = mean of B / C)'),
            ('T3W', FP['T3W']['core'].buffer(-2.5, join_style=2), H['T3W_parapet'], l3, 'inf (T3W 16.76 pub/inf, lean = mean of E / F)'),
            ('T3E', FP['T3E']['core'].buffer(-2.5, join_style=2), H['T3E'], l3, 'inf (T3E 14.48 inf, lean = mean of E / F)'),
            ('C3C', FP['C3C']['core'].buffer(-1.5, join_style=2), C3C_H, lean_x(FP['C3C']['core'].centroid.x),
             'inf (C3C 33.0 inf; lean linear in x through the B / D / E / F piers)')]


def lean_x(x):
    """NAIP 2024 east lean (m per m of height) at world x: the pier values (draw_data.dom_lean, two-epoch) follow
    k24.n = 0.392 + 0.000432 (x + 800) along the ESE normal (B -905: 0.343 vs 0.347; D -520: 0.513; E -800: 0.392; F -1030:
    0.294 vs 0.293) -> east = k24.n / sin(117.83 deg) [inf: a linear fit through four obs values]."""
    return (0.392 + 0.000432 * (x + 800.0)) / math.sin(math.radians(117.83))


PV = json.load(open(os.path.join(HERE, 'dom_pv.json'))) if os.path.exists(os.path.join(HERE, 'dom_pv.json')) else None
ROOFOBS = json.load(open(os.path.join(HERE, 'dom_roofobs.json'))) if os.path.exists(os.path.join(HERE, 'dom_roofobs.json')) else None
PV_R2 = json.load(open(os.path.join(HERE, 'dom_pv_r2.json'))) if os.path.exists(os.path.join(HERE, 'dom_pv_r2.json')) else None


# ------------------------------------------------------------------------------------------------ helpers
def strip_faces(poly_l, pred, off):
    """union of strips of width |off| on the edges of poly_l selected by pred(hdg) (off > 0 outward, < 0 inward)."""
    out = []
    for p in M.polys(poly_l):
        for ring in M.rings_of(p):
            for i in range(len(ring)):
                a, b = np.array(ring[i]), np.array(ring[(i + 1) % len(ring)])
                Ln = float(np.hypot(*(b - a)))
                if Ln < 2.0: continue
                n = np.array([(b[1] - a[1]) / Ln, -(b[0] - a[0]) / Ln])
                if pred(hdg_local(*n)):
                    out.append(Polygon([tuple(a), tuple(b), tuple(b + n * off), tuple(a + n * off)]).buffer(0))
    return unary_union(out) if out else Polygon()


def is_landside(a, b, max_d=260.0, tol=45.0):
    """an edge (local) faces the central garage: outward normal within tol of the bearing to the garage centre and the
    midpoint within max_d of it (draw_domestic BD-03 notes)."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    n = ((b[1] - a[1]) / L, -(b[0] - a[0]) / L)
    m = Wp((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    g = GARAGE_C - np.array(m)
    if np.hypot(*g) > max_d: return False
    gl = (g[0], -g[1])                         # world (x, z) -> local direction
    return angd(hdg_local(*n), hdg_local(*gl)) < tol


def circle(c, r, n=48):
    return Polygon([(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)])


def oct_local(c_world, apo, n0=343.0):
    return M.orient_all(Polygon([Lp(*p) for p in DD.octagon(c_world, apo, n0)]))


def pv_blocks(region, world=False):
    """the PV of a roof region as discrete rack tables (tools/blender/dom_roofobs.py: the rows / tables with their aisles inside
    each NAIP block, review r1) - or the block outlines when the tables are not measured; plus the arrays that dom_pv.py
    missed (tools/blender/dom_pv_r2.py, review r2: the BA-E plate). world=True: world (x, z) polygons (lean-free)."""
    rings = []
    if ROOFOBS is not None and region in ROOFOBS.get('pv_tables', {}) and ROOFOBS['pv_tables'][region]['tables']:
        rings = [t['ring'] for t in ROOFOBS['pv_tables'][region]['tables']]
    elif PV is not None and region in PV['regions']:
        rings = [b['ring'] for b in PV['regions'][region]['blocks']]
    if PV_R2 is not None and region in PV_R2.get('regions', {}):
        rings += [t['ring'] for t in PV_R2['regions'][region]['tables']]
    if world:
        return [Polygon(r).buffer(0) for r in rings]
    return [M.orient_all(Polygon([Lp(x, z) for x, z in r]).buffer(0)) for r in rings]


def pv_block_outlines(region):
    if PV is None or region not in PV['regions']: return []
    return [M.orient_all(Polygon([Lp(x, z) for x, z in b['ring']]).buffer(0)) for b in PV['regions'][region]['blocks']]


UNIT_LOD2_MIN = 15.0    # LOD2 keeps the rooftop units >= 15 m2 [our choice]


def roof_units(W, lod):
    """rooftop mechanical units measured on NAIP 2024 (tools/blender/dom_roofobs.py) on their host decks: [(local poly, host,
    height)] [obs extents, inf heights]."""
    if ROOFOBS is None: return []
    sol = {s.key: s for s in W.S}
    out = []
    for key, rec in ROOFOBS.get('units', {}).items():
        host = sol.get(key)
        if host is None: continue
        free = host.roof.buffer(-(PARAPET_T + 0.3), join_style=2)
        if host.holes: free = free.difference(unary_union(host.holes).buffer(0.3, join_style=2))
        for u in rec['units']:
            q = loc(Polygon(u['ring']).buffer(0)).intersection(free)
            for qq in M.polys(q, 2.0):
                if lod == 2 and qq.area < UNIT_LOD2_MIN: continue
                out.append((M.orient_all(qq), host, float(u['h'])))
    return out


def unit_boxes(mb, units):
    for q, host, hu in units:
        M.ring_walls(mb, q, host.deck, host.deck + hu, 'unit', tl('unit'))
        M.cap(mb, q, host.deck + hu, 'unit_top', tl('unit_top'))


# ------------------------------------------------------------------------------------------------ the world of solids
class Feat:
    """extra (non-extruded) geometry of a building: fn(mb_shell, mb_detail, lod)."""

    def __init__(self, bld, fn, kind='shell'):
        self.bld, self.fn, self.kind = bld, fn, kind


def build_world(lod):
    """all solids and features of the domestic complex for one LOD (0 / 1 share it). LOD2 (review r1: the phone tier sees it
    up close) keeps the LOD0 outlines, roof wells, skylights, coping recess and the bridge vestibules / notches / bulkheads; it
    drops only the thin members (fins, door frames, rack sides, brackets) and uses a reduced palette."""
    simp = 0.0
    W = World(); feats = []; info = {}

    def S_(g):
        g = M.orient_all(g)
        return M.orient_all(largest(_clean(g.simplify(simp, preserve_topology=True), 5.0))) if simp else g
    core = {k: S_(loc(v['core'])) for k, v in FP.items()}
    walks = [(k, S_(loc(w))) for k, v in FP.items() for w in v['walks']]
    links = [(k, S_(loc(w))) for k, v in FP.items() for w in v.get('links', [])]
    allfp = list(core.values()) + [w for _, w in walks] + [w for _, w in links]

    def others(k):
        return [g for kk, g in core.items() if kk != k] + [w for _, w in walks] + [w for _, w in links]

    # ---------------- BA-B
    wB, rB = face_offsets('B', core['BA_B'], others('BA_B'))
    sB = W.add(Solid('BA_B_body', 'BA_B', wB, H['B'], roof=rB, style='B', tag='obs', feature='Boarding Area B pier body',
                     spec=['bab.h_roof', 'bab.roof_edges', 'bab.glazing', 'outline.level']))
    band = loc(Polygon([tuple(st2w(BB_S_E, BB_T_S)), tuple(st2w(BB_S_E, BB_T_N)), tuple(st2w(BB_S_W, BB_T_N)), tuple(st2w(BB_S_W, BB_T_S))]))
    band = M.orient_all(band.intersection(wB.buffer(-0.5, join_style=2)))
    sBb = W.add(Solid('BA_B_band', 'BA_B', band, H['B_band'], z0=sB.deck, style='clere_B', tag='obs',
                      feature='Boarding Area B raised centre (clerestory band)', spec=['bab.h_roof_central', 'bab.clerestory']))
    sB.holes.append(band)
    info['B_band'] = band
    lB = float(D.dom_lean('B')[0][0])
    shB = np.array([-lB * H['B'], 0.0])
    if True:
        free = wB.difference(band.buffer(1.5, join_style=2)).buffer(-1.0, join_style=2)
        wells = []
        for r in BROOF['wells']:
            g = loc(Polygon(np.asarray(r) + shB)).intersection(free)
            for q in M.polys(g, 20.0): wells.append(M.orient_all(q))
        info['B_wells'] = wells
        for q in wells:
            sB.holes.append(q)
            sB.deck_extra.append((q, sB.deck - WELL_D, 'planting'))

        def well_walls(mb, det, lod_, wells=wells, z1=sB.deck):
            for q in wells:
                M.ring_walls(mb, q, z1 - WELL_D, z1, 'panel_light', tl('panel_light'), inward=True)
        feats.append(Feat('BA_B', well_walls))
        brs = []
        for r in BROOF['bridges']:
            g = loc(Polygon(np.asarray(r) + shB)).intersection(unary_union(wells).buffer(0.6, join_style=2)) if wells else Polygon()
            brs += [M.orient_all(q) for q in M.polys(g, 2.0)]

        def well_bridges(mb, det, lod_, brs=brs, z1=sB.deck):
            for q in brs:
                M.prism(mb, q, z1 - 0.6, z1 + 0.02, 'panel_light', top_mat='concrete', bottom_mat='soffit', tile=tl('panel_light'))
        feats.append(Feat('BA_B', well_bridges))
        info['B_bridges'] = brs
        # skylight grids: on the band or the outer roof (host = the larger overlap), raised 0.3 m glazed panels [obs pos, inf h]
        sky = []
        for r in BROOF['skylight_grids']:
            g = loc(Polygon(np.asarray(r) + shB))
            for host in (sBb, sB):
                q = g.intersection(host.poly.buffer(-1.2, join_style=2))
                if host is sB: q = q.difference(band.buffer(1.2, join_style=2))
                for qq in M.polys(q, 20.0):
                    qq = M.orient_all(qq); host.holes.append(qq); sky.append((qq, host.deck))
        info['B_skylights'] = sky
        feats.append(Feat('BA_B', lambda mb, det, lod_, sky=sky: skylights(mb, det, lod_, sky)))
    # PV (NAIP 2024 blocks), on the band and the outer roof
    pv = []
    for reg, host in (('B_band', sBb), ('B_outer', sB)):
        for q in pv_blocks(reg):
            pv.append((q, host))
    feats.append(Feat('BA_B', lambda mb, det, lod_, pv=pv: pv_racks(det, pv, lod_), kind='pv'))
    for k, w in walks:
        if k == 'BA_B':
            W.add(Solid('BA_B_walk%d' % len(W.S), 'BA_B', w, INNER_TOP, z0=walk_y0(w), style='walk', parapet=0.0, thk=0.7, underside=True,
                        tag='unk', feature='elevated walkway (the app\'s sky-bridge convention 6.0-10.5 m)', spec=['outline.level']))

    # ---------------- BA-C
    sC = W.add(Solid('BA_C_body', 'BA_C', core['BA_C'], H['C'], style='C', tag='obs', feature='Boarding Area C pier body',
                     spec=['bac.h_roof', 'bac.roof', 'outline.level']))
    if True:
        lC = float(D.dom_lean('C')[0][0])
        q = loc(Polygon([(-678 - lC * H['C'], 412), (-672 - lC * H['C'], 412), (-672 - lC * H['C'], 418), (-678 - lC * H['C'], 418)]))
        q = M.orient_all(q.intersection(sC.poly.buffer(-1.0)))
        if q.area > 4: sC.holes.append(q); feats.append(Feat('BA_C', lambda mb, det, lod_, q=q, z=sC.deck: skylights(mb, det, lod_, [(q, z)])))

    # ---------------- BA-D
    wD, rD = face_offsets('D', core['BA_D'], others('BA_D'))
    sD = W.add(Solid('BA_D_body', 'BA_D', wD, H['D'], roof=rD, style='D', tag='obs', feature='Boarding Area D pier and head',
                     spec=['bad.h_roof', 'bad.roof_edges', 'bad.roof', 'outline.level']))
    lD = float(D.dom_lean('D')[0][0])
    drums = []
    for k, (c, r) in enumerate(DD.BAD_DRUMS_IMG):
        cl = Lp(c[0] - lD * DD.BAD_DRUM_TOP, c[1])
        g = M.orient_all(circle(cl, r, 48).intersection(wD.buffer(-0.3)))
        sd = W.add(Solid('BA_D_drum%d' % k, 'BA_D', g, DD.BAD_DRUM_TOP, z0=sD.deck, style='drum', thk=0.6, parapet=0.5, tag='inf',
                         feature='Boarding Area D head drum (NAIP roof circle, D ~19 m; top inf)', spec=['bad.roof']))
        sD.holes.append(g); drums.append(sd)
    info['D_drums'] = [(d.poly.centroid.coords[0], d.h) for d in drums]
    if True:
        lines = []
        for p, q in DD.BAD_LINES_IMG:
            a = Lp(p[0] - lD * H['D'], p[1]); b = Lp(q[0] - lD * H['D'], q[1])
            g = LineString([a, b]).buffer(0.6, cap_style=2).intersection(wD.buffer(-1.0)).difference(unary_union([d.poly for d in drums]).buffer(1.0))
            lines += [M.orient_all(x) for x in M.polys(g, 2.0)]
        info['D_lines'] = lines
        feats.append(Feat('BA_D', lambda mb, det, lod_, lines=lines, z=sD.deck: ridge_lights(mb, lines, z)))
    for k, w in walks:
        if k == 'BA_D':
            W.add(Solid('BA_D_walk%d' % len(W.S), 'BA_D', w, INNER_TOP, z0=walk_y0(w), style='walk', parapet=0.0, thk=0.7, underside=True,
                        tag='unk', feature='elevated connector T2 - BA-D (app sky-bridge convention)', spec=['outline.level']))

    # ---------------- BA-E (stepped section, BD-02 bae_section)
    wE, rE = face_offsets('E', core['BA_E'], others('BA_E'))
    longf = lambda h: angd(h, 117.83) < 20 or angd(h, 297.83) < 20

    def styleE(s, a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return 'E' if longf(hdg_local((b[1] - a[1]) / L, -(b[0] - a[0]) / L)) else 'E_end'
    sEf = W.add(Solid('BA_E_body', 'BA_E', wE, H['E_flank'], style=styleE, tag='inf',
                      feature='Boarding Area E body and lower side roofs (~3 m below the raised centre)', spec=['bae.roof', 'bae.facade', 'outline.level']))
    centre = M.orient_all(largest(_clean(wE.difference(strip_faces(wE, longf, -DD.BAE_FLANK).buffer(0.001)), 50.0)))
    plate = M.orient_all(largest(_clean(unary_union([centre, strip_faces(centre, longf, DD.BAE_OVER)]).intersection(wE.buffer(-0.05)), 50.0)))
    # end bay at the NNE tip (photo a1, BD-02: "a recessed full-height glass end wall" under the tapered plate): the last
    # E_END_D m of the raised centre stand on the apron (no flank roof across the end), the glass wall recessed BAE_OVER
    # inside the outline under the plate (the plate edge stays on the outline: nothing outside the level-2 footprint) [inf]
    endf = lambda h: angd(h, 27.83) < 35
    bay = largest(_clean(centre.intersection(strip_faces(centre, endf, -E_END_D).buffer(0.001)), 20.0))
    roof_c = plate
    if bay.area > 50:
        bay = M.orient_all(bay)
        bay_wall = M.orient_all(largest(_clean(bay.difference(strip_faces(bay, endf, -DD.BAE_OVER).buffer(0.001)), 20.0)))
        bay_ext = unary_union([bay, strip_faces(bay, longf, DD.BAE_OVER + 0.05)])
        roof_b = M.orient_all(largest(_clean(plate.intersection(bay_ext), 20.0)))
        roof_c = M.orient_all(largest(_clean(plate.difference(roof_b.buffer(0.001, join_style=2)), 50.0)))
        sEf.poly = M.orient_all(largest(_clean(wE.difference(bay.buffer(0.001, join_style=2)), 50.0)))
        sEf.roof = sEf.poly
        sEb = W.add(Solid('BA_E_endbay', 'BA_E', bay_wall, H['E'], roof=roof_b, style='E_endwall', thk=0.8, parapet=0.0, tag='inf',
                          feature='Boarding Area E tip: full-height glazed end wall recessed under the tapered plate (photo a1)',
                          spec=['bae.roof', 'bae.facade']))
        info['E_endbay'] = bay_wall
    cen2 = M.orient_all(largest(_clean(centre.difference(bay.buffer(0.001, join_style=2)), 50.0))) if bay.area > 50 else centre
    sEc = W.add(Solid('BA_E_centre', 'BA_E', cen2, H['E'], z0=sEf.deck, roof=roof_c, style='clere_E', thk=0.8, parapet=0.0, tag='obs',
                      feature='Boarding Area E raised PV roof, tapered edge overhanging the clerestory', spec=['bae.h_roof', 'bae.roof']))
    sEf.holes.append(cen2)
    info['E_centre'] = centre; info['E_plate'] = plate
    feats.append(Feat('BA_E', lambda mb, det, lod_, pv=[(q, sEc) for q in pv_blocks('E_centre')]: pv_racks(det, pv, lod_), kind='pv'))

    # ---------------- BA-F
    wF, rF = face_offsets('F', core['BA_F'], others('BA_F'))
    sF = W.add(Solid('BA_F_body', 'BA_F', wF, H['F'], roof=rF, style='F', tag='obs', feature='Boarding Area F arms and octagonal hub',
                     spec=['baf.h_roof_ne_arm', 'baf.roof_edges', 'baf.hub', 'outline.level']))
    lF = float(D.dom_lean('F')[0][0])
    lan = oct_local(DD.baf_lantern_centre(), DD.BAF_LANTERN_APO[0])
    # review r1: the rise is unknown (the NAIP 2020 shadow only bounds it, <= 4.6 m): modelled conservatively as a 1.0-m
    # glazed upstand [unk], the 4.6-m bound kept in the manifest (LANTERN_RISE_BOUND)
    rise = LANTERN_RISE
    sL = W.add(Solid('BA_F_lantern', 'BA_F', lan, H['F'] + rise, z0=sF.deck, style='lantern', thk=0.6, parapet=0.0, tag='unk',
                     feature='BA-F hub lantern (eccentric octagon 19.4 m [obs]; rise 1.0 m minimal upstand [unk], bound <= 4.6 m)', spec=['baf.hub']))
    sF.holes.append(lan)
    inner = oct_local(DD.baf_lantern_centre(), DD.BAF_LANTERN_APO[1])
    sL.holes.append(inner); sL.deck_extra.append((inner, sL.h + 0.25, 'glass_sky'))
    feats.append(Feat('BA_F', lambda mb, det, lod_, g=inner, z=sL.h: M.ring_walls(mb, g, z, z + 0.25, 'coping', (3.0, 3.0))))
    mon = M.orient_all(Polygon([Lp(*p) for p in DD.baf_monitor(-np.array([lF, 0.0]) * 11.0)]).intersection(wF.buffer(-1.0)))
    sM = W.add(Solid('BA_F_monitor', 'BA_F', largest(mon), H['F'] + 2.5, z0=sF.deck, style='monitor', thk=0.5, parapet=0.0, tag='unk',
                     feature='BA-F NW-arm roof monitor ~8 m wide [obs NAIP]; rise 2.5 m placeholder [unk]', spec=['baf.hub']))
    sF.holes.append(sM.poly)
    info['F_lantern'] = lan; info['F_monitor'] = sM.poly
    for k, w in walks:
        if k == 'BA_F':
            W.add(Solid('BA_F_walk%d' % len(W.S), 'BA_F', w, INNER_TOP, z0=walk_y0(w), style='walk', parapet=0.0, thk=0.7, underside=True,
                        tag='unk', feature='elevated F connector (app sky-bridge convention)', spec=['outline.level']))

    # ---------------- halls
    def styleT1(s, a, b): return 'T1_land' if is_landside(a, b) else 'hall'
    side2 = loc(T2_SIDEWALK_POLY) if not T2_SIDEWALK_POLY.is_empty else Polygon()

    def on_curb(a, b, side=side2):
        # the edge faces the departures sidewalk (close-out r3): its midpoint 1 m outward lies on the sidewalk strip
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 0.5 or side.is_empty: return False
        n = ((b[1] - a[1]) / L, -(b[0] - a[0]) / L)
        return side.contains(Point((a[0] + b[0]) / 2 + n[0], (a[1] + b[1]) / 2 + n[1]))

    def styleT2(s, a, b): return 'T2_land' if (on_curb(a, b) or is_landside(a, b)) else 'hall'
    def styleT3W(s, a, b): return 'T3W_land' if is_landside(a, b) else 'T3W_air'
    sT1 = W.add(Solid('T1_hall', 'T1', core['T1'], H['T1'], style=styleT1, tag='unk', feature='Harvey Milk Terminal 1 Center hall',
                      spec=['t1c.h_roof', 't1c.landside_facade', 't1c.roof_pv', 't1c.skylights_count']))
    sT2 = W.add(Solid('T2_hall', 'T2', core['T2'], H['T2'], style=styleT2, tag='unk', feature='Terminal 2 hall', spec=['t2.landside', 't2.daylight']))
    # close-out r3 (buildings-2): the T2 - garage connector over the departures roadway (see T2_LINK_POLY / T2_LINK_Z)
    if not T2_LINK_POLY.is_empty:
        sTL = W.add(Solid('T2_garage_link', 'T2', S_(loc(T2_LINK_POLY)), T2_LINK_Z[1], z0=T2_LINK_Z[0], style='link', parapet=0.0, thk=0.7,
                          underside=True, tag='inf', spec=['outline.level'],
                          feature='T2 - Central Parking Garage connector over the departures roadway (SFO Museum T2 courtyard connector '
                                  'extended to the moved T2 face [obs plan]; floor at the garage Level 3 placeholder 9.88 m, soffit 4.7 m '
                                  'over the departures deck [inf]; level unk)'))
        info['T2_link'] = sTL.poly
    # Courtyard 3 Connector office block (review r1; see C3C_H): node building 'C3C'
    sC3 = W.add(Solid('C3C_block', 'C3C', core['C3C'], C3C_H, style='C3C', tag='inf',
                      feature='Courtyard 3 Connector: six-storey office block above the T2-T3 connector (HOK [pub]); footprint T2 '
                              'outline NW end [obs]; height 33.0 m [inf, range 32-36]', spec=[]))
    # its rooftop penthouse (review r2, see C3C_PENT_*) with the louvre band on the NNE wall
    pent_c = loc(Polygon([c3c_uw(u, w) for u, w in ((C3C_PENT_U[0], C3C_PENT_W[0]), (C3C_PENT_U[1], C3C_PENT_W[0]),
                                                    (C3C_PENT_U[1], C3C_PENT_W[1]), (C3C_PENT_U[0], C3C_PENT_W[1]))]))
    pent_c = M.orient_all(largest(_clean(pent_c.intersection(sC3.poly.buffer(-(PARAPET_T + 0.5), join_style=2)), 20.0)))
    sC3p = W.add(Solid('C3C_penthouse', 'C3C', pent_c, C3C_PENT_TOP, z0=sC3.deck, style='pent_c3c', thk=0.6, parapet=0.4, tag='obs',
                       feature='Courtyard 3 Connector rooftop penthouse (photo a1 light box with a dark louvre band; NAIP 2024 WNW wall '
                               'band) [obs, low]; top 38.0 m [obs, low]', spec=[]))
    sC3.holes.append(sC3p.poly); info['C3C_penthouse'] = sC3p.poly
    feats.append(Feat('C3C', lambda mb, det, lod_: c3c_louvre(mb, det, lod_)))
    sT3W = W.add(Solid('T3W_hall', 'T3W', core['T3W'], H['T3W_parapet'], style=styleT3W, parapet=3.5 * FT, tag='pub',
                       feature='Terminal 3 West (95 % CD state: parapet 66\'-0")', spec=['t3.levels_datum', 't3w.wall_field', 't3w.materials']))
    sT3E = W.add(Solid('T3E_hall', 'T3E', core['T3E'], H['T3E'], style='T3E', tag='inf', feature='Terminal 3 East', spec=['t3.levels_datum', 't3e.facade']))
    # T3E penthouse: radial band about the garage centre, bearings 356.0..13.4 deg, set back 20-24 m behind the landside face,
    # ~25.5 m deep (NAIP 2024 top edges, BD-03 view 3) [obs low]; top R3 21.34 [inf]
    pent = t3e_penthouse(core['T3E'])
    sP = W.add(Solid('T3E_penthouse', 'T3E', pent, H['T3E_pent'], z0=sT3E.deck, style='penthouse', thk=0.6, parapet=0.4, tag='inf',
                     feature='T3E mechanical penthouse (perforated corrugated metal [pub]; extent obs NAIP; top R3 inf)', spec=['t3.penthouses', 't3e.facade']))
    sT3E.holes.append(pent); info['T3E_penthouse'] = pent
    for k, w in walks:
        if k in ('T1', 'T2', 'T3E'):
            W.add(Solid('%s_walk%d' % (k, len(W.S)), k, w, INNER_TOP, z0=walk_y0(w), style='walk', parapet=0.0, thk=0.7, underside=True,
                        tag='unk', feature='elevated connector (app sky-bridge convention)', spec=['outline.level']))
    for k, w in links:
        hs = [s.h for s in W.S if s.z0 < 0.1 and s.poly.distance(w) < 0.6]
        W.add(Solid('%s_link%d' % (k, len(W.S)), k, w, min(hs) if hs else H['D'], style='conn', tag='inf',
                    feature='airside link at grade (height: the lower adjoining part)', spec=['outline.level']))
    if True:
        lT = 0.5 * (lB + float(D.dom_lean('C')[0][0]))
        sky = []
        for p in ((-826, 460), (-815, 508), (-884, 530)):
            q = np.array(p) - [lT * H['T1'], 0.0]
            g = loc(Polygon([q + [-4.5, -5.5], q + [4.5, -5.5], q + [4.5, 5.5], q + [-4.5, 5.5]])).intersection(sT1.poly.buffer(-1.5))
            for qq in M.polys(g, 20.0):
                qq = M.orient_all(qq); sT1.holes.append(qq); sky.append((qq, sT1.deck))
        info['T1_skylights'] = sky
        feats.append(Feat('T1', lambda mb, det, lod_, sky=sky: skylights(mb, det, lod_, sky)))
    for reg, host, bld in (('T1', sT1, 'T1'), ('T3W', sT3W, 'T3W'), ('T3E', sT3E, 'T3E'), ('C3C', sC3, 'C3C')):
        pv = [(q, host) for q in pv_blocks(reg)] if reg != 'C3C' else c3c_pv(sC3, sC3p)
        feats.append(Feat(bld, lambda mb, det, lod_, pv=pv: pv_racks(det, pv, lod_), kind='pv'))
    # T1 curb canopy + departures sidewalk deck along the trimmed landside face [pub canopy; inf / unk heights]
    can = t1_canopy(sT1)
    info['T1_canopy'] = can
    feats.append(Feat('T1', lambda mb, det, lod_, can=can: canopy(mb, det, lod_, can)))
    # close-out r3 (buildings-2): T2 curb canopy + departures sidewalk deck along the moved landside face
    can2 = t2_canopy(sT2, side2, loc(T2_LINK_POLY) if not T2_LINK_POLY.is_empty else Polygon())
    info['T2_canopy'] = can2
    feats.append(Feat('T2', lambda mb, det, lod_, can=can2: canopy(mb, det, lod_, can)))

    # ---------------- review r2: facades notched around the app's rotunda drums (finding 8)
    info['drum_notches'] = drum_notches(W)
    # ---------------- bridge doors / vestibules (jet-bridge attachment facades), overhang notches
    doors = bridge_doors(W)
    info['doors'] = doors
    for d in doors:
        if d['notch'] is not None:
            for s in W.S:
                if s.z0 < 0.1 and s.h - s.thk < d['vz1'] + 0.3 and s.roof.distance(d['notch']) < 0.1:
                    ov = s.roof.difference(s.poly.buffer(0.01, join_style=2))
                    cut = ov.intersection(d['notch'])
                    if cut.area > 0.05:
                        s.roof = M.orient_all(largest(_clean(s.roof.difference(cut.buffer(0.01, join_style=2)), 5.0)))
                        d['notched'] = d.get('notched', 0.0) + cut.area
        if d['low']:
            host = next(o for o in W.S if o.key == d['host'])
            hole = bulkhead_hole(d).intersection(host.roof.buffer(-0.05, join_style=2))
            if hole.area > 0.5: host.holes.append(M.orient_all(hole))
        bld = d['bld']
        feats.append(Feat(bld, lambda mb, det, lod_, d=d: door_geom(mb, det, lod_, d)))
    # rooftop mechanical units (NAIP 2024, review r1)
    units = roof_units(W, lod)
    info['units'] = units
    for bld in sorted({h.bld for _, h, _ in units}):
        feats.append(Feat(bld, lambda mb, det, lod_, us=[u for u in units if u[1].bld == bld]: unit_boxes(mb, us)))
    # review r2 (findings 3 / 6): flashing over the 0.3-m gap to the tower base building
    fl = tower_flashing(W)
    info['tower_flashing'] = fl
    for bld, g, z in fl:
        feats.append(Feat(bld, lambda mb, det, lod_, g=g, z=z: M.cap(mb, g, z, 'coping', tl('coping'))))
    W.finish()
    return W, feats, info


# ------------------------------------------------------------------------------------------------ feature geometry
def skylights(mb, det, lod, sky):
    """raised glazed panels (0.3 m curb, coping sides, glass top) in a deck hole; the floor under them stays open (hidden)."""
    for q, z in sky:
        M.ring_walls(mb, q, z, z + 0.3, 'coping', (3.0, 3.0))
        M.cap(mb, q, z + 0.3, 'glass_sky', tl('glass_sky'))


def ridge_lights(mb, lines, z):
    for q in lines:
        M.ring_walls(mb, q, z, z + 0.6, 'coping', (3.0, 3.0))
        M.cap(mb, q, z + 0.6, 'glass_sky', tl('glass_sky'))


def pv_racks(det, pv, lod):
    """PV rack blocks (NAIP 2024 extents [obs]) on their host deck, clear of the deck holes and 0.6 m from the parapets:
    LOD0 boxes (aluminium sides, module top) PV_Z above the deck; LOD1 / LOD2 the top only."""
    for q, host in pv:
        free = host.roof.buffer(-(PARAPET_T + 0.6), join_style=2)
        if host.holes: free = free.difference(unary_union(host.holes).buffer(0.6, join_style=2))
        g = q.intersection(free)
        for qq in M.polys(g, 6.0):
            qq = M.orient_all(qq.simplify(0.1))
            rr = qq.minimum_rotated_rectangle
            e = list(rr.exterior.coords)
            v1 = np.subtract(e[1], e[0]); v2 = np.subtract(e[2], e[1])
            ax = v1 if np.hypot(*v1) >= np.hypot(*v2) else v2
            ax = ax / np.hypot(*ax); ay = np.array([-ax[1], ax[0]])
            uvf = lambda x, y, ax=ax, ay=ay: ((x * ax[0] + y * ax[1]) / tl('pv')[0], (x * ay[0] + y * ay[1]) / tl('pv')[1])
            z0, z1 = host.deck + PV_Z[0], host.deck + PV_Z[1]
            if lod == 2:
                # (review r1: the minimum rectangle overhung the curved T3 roof edges - the clipped table is used)
                M.cap(det, qq, z1, 'pv', uvf=uvf)
                continue
            M.cap(det, qq, z1, 'pv', uvf=uvf)
            if lod == 0:
                M.ring_walls(det, qq, z0, z1, 'mullion', (3.0, 3.0))


def canopy(mb, det, lod, can):
    """T1 curb canopy (glass top, aluminium edge, light soffit) at T1_CANOPY_H and the departures sidewalk deck at CURB."""
    if can is None or can['poly'].is_empty: return
    g = can['poly']
    M.ring_walls(mb, g, T1_CANOPY_H, T1_CANOPY_H + 0.35, 'mullion', (3.0, 3.0))
    M.cap(mb, g, T1_CANOPY_H + 0.35, 'glass_canopy', tl('glass_canopy'))
    M.cap(mb, g, T1_CANOPY_H, 'soffit', tl('soffit'), down=True)
    sw = can['walk']
    M.ring_walls(mb, sw, CURB - 0.6, CURB, 'concrete', tl('concrete'))
    M.cap(mb, sw, CURB, 'concrete', tl('concrete'))
    M.cap(mb, sw, CURB - 0.6, 'soffit', tl('soffit'), down=True)
    if lod == 0:
        for a, n in can['brackets']:
            dd = can.get('depth', T1_CANOPY_D)
            P0 = (a[0], a[1], T1_CANOPY_H + 2.2); P1 = (a[0] + n[0] * (dd - 0.3), a[1] + n[1] * (dd - 0.3), T1_CANOPY_H + 0.35)
            M.tube(det, [P0, P1], 0.06, 6, 'mullion', cap_ends=True)


def t1_canopy(sT1):
    """canopy strip: T1_CANOPY_D out from the landside wall pieces inside the T1 curbside trim window (where the hall was
    set back by the canopy depth, so the canopy ends on the trimmed curb line); minus the AirTrain guideway (+1 m)."""
    x0, z0, x1, z1 = TRIM_WINDOWS['T1 north face (curbside roadways)']
    win = loc(sbox(x0, z0, x1, z1))
    strips, br = [], []
    for ring in M.rings_of(sT1.poly):
        for i in range(len(ring)):
            a, b = np.array(ring[i]), np.array(ring[(i + 1) % len(ring)])
            L = float(np.hypot(*(b - a)))
            if L < 0.5 or not is_landside(tuple(a), tuple(b)): continue
            if not win.contains(Point((a + b) / 2)): continue
            n = np.array([(b[1] - a[1]) / L, -(b[0] - a[0]) / L])
            strips.append(Polygon([tuple(a), tuple(b), tuple(b + n * T1_CANOPY_D), tuple(a + n * T1_CANOPY_D)]).buffer(0.02))
            for t in np.arange(3.0, L - 1.0, 6.0):
                br.append((tuple(a + (b - a) * t / L), tuple(n)))
    if not strips: return None
    g = unary_union(strips).difference(sT1.poly.buffer(0.01)).difference(loc(RAIL).buffer(1.0))
    g = M.orient_all(_clean(g, 5.0))
    walk = g
    # brackets only where the canopy exists (it is cut back 1 m from the AirTrain guideway): bracket midpoint over the canopy
    gp = shapely.prepared.prep(g.buffer(0.05))
    br = [b for b in br if gp.contains(Point(b[0][0] + b[1][0] * T1_CANOPY_D / 2, b[0][1] + b[1][1] * T1_CANOPY_D / 2))]
    return dict(poly=g, walk=walk, brackets=br)


def t2_canopy(sT2, side, link):
    """close-out r3 (buildings-2): T2 curb canopy, T2_CANOPY_D out from the T2 wall pieces that face the departures sidewalk
    (strip of the moved face), over the sidewalk only and stopped 0.5 m short of the garage connector (its soffit is 0.2 m
    above the canopy top); the sidewalk deck at CURB under it (the whole strip from the wall to the deck edge)."""
    if side.is_empty: return None
    strips, br = [], []
    for ring in M.rings_of(sT2.poly):
        for i in range(len(ring)):
            a, b = np.array(ring[i]), np.array(ring[(i + 1) % len(ring)])
            L = float(np.hypot(*(b - a)))
            if L < 0.5: continue
            n = np.array([(b[1] - a[1]) / L, -(b[0] - a[0]) / L])
            if not side.contains(Point(*((a + b) / 2 + n))): continue
            strips.append(Polygon([tuple(a), tuple(b), tuple(b + n * T2_CANOPY_D), tuple(a + n * T2_CANOPY_D)]).buffer(0.02))
            for t in np.arange(3.0, L - 1.0, 6.0):
                br.append((tuple(a + (b - a) * t / L), tuple(n)))
    if not strips: return None
    g = unary_union(strips).intersection(side.buffer(0.05, join_style=2)).difference(sT2.poly.buffer(0.01))
    if not link.is_empty: g = g.difference(link.buffer(0.5, join_style=2))
    g = M.orient_all(_clean(g, 5.0))
    gp = shapely.prepared.prep(g.buffer(0.05))
    br = [b for b in br if gp.contains(Point(b[0][0] + b[1][0] * T2_CANOPY_D / 2, b[0][1] + b[1][1] * T2_CANOPY_D / 2))]
    return dict(poly=g, walk=M.orient_all(_clean(side, 5.0)), brackets=br, depth=T2_CANOPY_D)


def t3e_penthouse(t3e):
    """radial band about the garage centre: inner radius = landside face + set-back (mid of 20-24 m), 25.5 m deep [obs low]."""
    b0, b1 = DD.T3E_PENT_BRG
    sb = 0.5 * sum(DD.T3E_PENT_SETBACK); depth = 25.5
    inner, outer = [], []
    gl = Lp(*GARAGE_C)
    face = t3e.exterior
    for b in np.linspace(b0, b1 + 360.0 if b1 < b0 else b1, 24):
        v = (math.sin(math.radians(b)), math.cos(math.radians(b)))      # local direction of the bearing
        ray = LineString([gl, (gl[0] + v[0] * 400, gl[1] + v[1] * 400)])
        x = ray.intersection(face)
        pts = [x] if x.geom_type == 'Point' else [p for p in getattr(x, 'geoms', []) if p.geom_type == 'Point']
        if not pts: continue
        r0 = min(math.dist(gl, p.coords[0]) for p in pts)
        inner.append((gl[0] + v[0] * (r0 + sb), gl[1] + v[1] * (r0 + sb)))
        outer.append((gl[0] + v[0] * (r0 + sb + depth), gl[1] + v[1] * (r0 + sb + depth)))
    g = Polygon(inner + outer[::-1]).buffer(0).intersection(t3e.buffer(-2.0, join_style=2))
    return M.orient_all(largest(g))


# ------------------------------------------------------------------------------------------------ review r2 features
def c3c_louvre(mb, det, lod):
    """the dark louvre band on the C3C penthouse NNE wall (photo a1) [obs, low]: a 0.08-m deep box 0.02 m off the wall."""
    u0, u1 = C3C_LOUVRE_U
    a = np.array(Lp(*c3c_uw(u0, C3C_PENT_W[0]))); b = np.array(Lp(*c3c_uw(u1, C3C_PENT_W[0])))
    d = (b - a) / np.hypot(*(b - a)); n = np.array([d[1], -d[0]])
    inw = np.array(Lp(*c3c_uw(0.5 * (u0 + u1), C3C_PENT_W[0] + 1.0))) - (a + b) / 2
    if np.dot(n, inw) > 0: n = -n                       # n: outwards from the penthouse wall (NNE)
    c = (a + b) / 2 + n * 0.06
    M.boxm(det, tuple(c), tuple(d), float(np.hypot(*(b - a))), 0.08, C3C_LOUVRE_Z, 'louvre', tl('louvre'), top=True, bottom=True)


def c3c_pv(block, pent):
    """the C3C PV tables (dom_roofobs.json, measured with the relief of the 33.0-m roof): a table whose position moved back by
    the penthouse's extra relief (lean x 5.0 m, ~2.2 m west) lies on the penthouse roof is hosted there (NAIP shows the
    tables on the raised box), the others stay on the block deck (review r2)."""
    k = lean_x(C3C_POLY.centroid.x)
    out = []
    pw = wld(pent.poly)
    for q in pv_blocks('C3C', world=True):
        q2 = affinity.translate(q, -k * (C3C_PENT_TOP - C3C_H), 0.0)
        if pw.buffer(0.5).contains(q2.centroid):
            out.append((M.orient_all(loc(q2)), pent))
        else:
            out.append((M.orient_all(loc(q)), block))
    return out


DRUM_R_APP, DRUM_MIN_APP = 2.45, 1.5        # js/live/gates.js: drum radius clampN(min(2.45, rotundaMaxR - 0.25), DRUM_MIN 1.5, 2.45)
DRUM_CLEAR = 0.10                           # facade clearance to the largest drum the app can draw [review r2: 0.1 m]
# the app's drum: gates.js solidsQ rotunda Hr - 0.3 .. Hr + 3.3 (drawn cyl Hr - 0.45 .. Hr + 3.15); notch band with 0.3 m margin
# below. Close-out r3 fix 2: PER DRUM from its rotunda floor Hr (app_bridges.json; Hr follows the pier's DEPARTURE_LEVELS and
# the walkway's 1:12 band, B 5.1-5.6, C ~2.8-3.2, D ~3.4, E / F 3.5-4.9 m); DRUM_BAND = the old BA-B band (the default)
DRUM_DZ = (-0.6, 3.3)
DRUM_BAND = (FLOOR2 + DRUM_DZ[0], FLOOR2 + DRUM_DZ[1])


def rotunda_drums():
    """the app's rotunda drums of the B-F bridges: centre = data/sfo_stands.json rotunda (gates.js b.rot; rotShift 0 today),
    radius = the app's drawn rotR (tools/blender/app_bridges.json; close-out round 4) - without a record, the LARGEST the app
    can draw for that bridge, max(DRUM_MIN, min(2.45, rotunda_max_r - 0.25)) (the other gates.js limits only shrink it;
    checked against all 332 drum solids of out/buildings3d/integ/draw/scene2d.json: none larger)."""
    st = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
    out = []
    for s_ in st:
        if s_['letter'] not in 'BCDEF': continue
        for b in s_['bridges'] + s_.get('bridges_upper', []):
            r = b.get('rotunda')
            if not r: continue
            rm = b.get('rotunda_max_r')
            rr = max(DRUM_MIN_APP, min(DRUM_R_APP, (rm if rm is not None else 2.7) - 0.25))
            # the drum's height band (close-out r3 fix 2): the app's rotunda floor Hr of this bridge (app_bridges.json, matched
            # by stand and rotunda centre: upper-deck bridges have no door number in the data)
            cand = [a for a in AB.load()['bridges'] if a['stand'] == s_['name'] and math.dist(a['rot'], r) < 0.6]
            ab = min(cand, key=lambda a: math.dist(a['rot'], r)) if cand else None
            Hr = ab['Hr'] if ab else PIER_LEVEL.get(s_['letter'], FLOOR2)
            # close-out round 4: the radius the app DRAWS (app_bridges.json rotR: gates.js prepBridge, fixed at load from the
            # static data - the drum limits are the outlines and the neighbours' fixed solids) where the dump has the bridge;
            # the upper bound above only without a record. The upper bound left 0.4-0.6 m of open slot between the notch /
            # vestibule and the drawn drum at E3 / E9 / F7 / F8 (drums 1.7-2.1 m drawn, 2.2-2.45 m assumed)
            r_app = float(ab['rotR']) if ab else None
            r_use = r_app if r_app is not None else rr
            out.append(dict(stand=s_['name'], door=b.get('door'), c=Lp(*r), r=r_use, r_max=rr, r_app=r_app, rc=r_use + DRUM_CLEAR, Hr=Hr,
                            band=(Hr + DRUM_DZ[0], Hr + DRUM_DZ[1]), app=bool(cand)))
    return out


DRUMS = rotunda_drums()


def drum_notches(W):
    """review r2 (finding 8): every solid whose height range meets the drum band is notched around each drum (radius + 0.1 m)
    that reaches into it; the roof is notched too where its underside is below the drum top (else it overhangs the notch,
    with a soffit). -> [dict(stand, door, solid, r_app_max, notched_m2, depth_m)]."""
    out = []
    for s in W.S:
        # (close-out r3 fix 2: each drum's own band, from its rotunda floor Hr)
        hit = [d for d in DRUMS if not (s.z0 > d['band'][1] or s.h < d['band'][0]) and s.poly.distance(Point(d['c'])) < d['rc'] - 0.005]
        if not hit: continue
        cut = unary_union([circle(d['c'], d['rc'], 64) for d in hit]).buffer(0.001)
        orig = s.poly
        # roof underside below a drum's top: the roof is notched too (around those drums only)
        low = [d for d in hit if (s.h - s.thk) < d['band'][1] + 0.1]
        low_roof = bool(low)
        if low_roof:
            cut_r = unary_union([circle(d['c'], d['rc'], 64) for d in low]).buffer(0.001)
        if low_roof:
            s.roof = M.orient_all(largest(_clean(s.roof.difference(cut_r), 5.0)))
        s.poly = M.orient_all(largest(_clean(orig.difference(cut), 5.0)))
        if low_roof and s.roof.area > s.poly.area - 0.01 and s.roof.difference(s.poly).area < 0.01: s.roof = s.poly
        for d in hit:
            pc = Point(d['c'])
            depth = d['rc'] - pc.distance(orig.exterior) if not orig.contains(pc) else d['rc'] + pc.distance(orig.exterior)
            out.append(dict(stand=d['stand'], door=d['door'], solid=s.key, r_app_max=round(d['r_max'], 2), r_drawn=d['r_app'] and round(d['r_app'], 3),
                            notched_m2=round(orig.intersection(circle(d['c'], d['rc'], 64)).area, 2), depth_m=round(depth, 2),
                            roof_notched=d in low, Hr=round(d['Hr'], 3), drum_top=round(d['band'][1], 3)))
    return out


def tower_flashing(W):
    """review r2 (finding 6): caps over the TOWER_GAP gap between the solids cut off the tower base building (IBF) and the IBF
    walls (looking down into it showed the open inside of T2): per solid standing next to it, the gap band along its stretch
    at min(solid top, TOWER_Z1), stopping TOWER_JOINT off the IBF wall (clear of its mullions; no shared volume); the domestic
    walls behind it run full height, so the joint shows wall faces, not an open interior."""
    ex = loc(TOWER_EXCL)
    band = ex.buffer(TOWER_GAP + 0.02, join_style=2).difference(ex.buffer(TOWER_JOINT, join_style=2))   # a joint at the IBF wall
    out = []
    for s in W.S:
        if s.z0 > TOWER_Z1 or s.roof.distance(ex) > TOWER_GAP + 0.1: continue
        g = band.intersection(s.roof.buffer(TOWER_GAP + 0.15, join_style=2)).difference(s.roof)
        g = _clean(g, 0.05)
        if g.is_empty: continue
        out.append((s.bld, M.orient_all(g), round(min(s.h, TOWER_Z1), 3)))
    return out


# ------------------------------------------------------------------------------------------------ bridge doors
def bridge_doors(W):
    """jet-bridge attachment facades: for every bridge of the domestic stands (data/sfo_stands.json walk), the point X where
    the walkway meets the 3-D facade, the app's walkway start E (js/live/gates.js: where the polyline last leaves the app's
    building rings), a door frame on the facade at X and - where E lies outside the facade - a vestibule box X -> E with the
    walkway's section (+0.3 m) so that the app's walkway abuts it [inf]. Where a roof edge (or C's low roof) is below the
    walkway top, the overhang is notched / a bulkhead rises above the roof [inf]."""
    st = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
    # hosts: the buildings standing on the apron, and the elevated parts whose floor comes down to the vestibule floor where a
    # bridge enters them (review r1: B10 / B11 / B11S / B15 / B16)
    isHost = lambda o: (o.z0 < 0.1 and o.h > 6.0 and o.style not in ('drum', 'lantern', 'monitor', 'penthouse')) or \
        (o.style == 'walk' and o.z0 < INNER_Y0 - 0.01)          # (a part lowered for the walkway that enters it, walk_y0)
    body = unary_union([s.poly for s in W.S if isHost(s)])
    bp = shapely.prepared.prep(body)
    body_w = wld(body)                                  # world (x, z): the closing-box depth samples (bridge_head.py)
    app = shapely.prepared.prep(APP_BLD)
    allb = AB.bridges('ABCDEFG')
    out = []
    for s in st:
        if s['letter'] not in 'BCDEF': continue
        for br in s['bridges'] + s.get('bridges_upper', []):
            wpts = br.get('walk') or []
            if len(wpts) < 2: continue
            if br.get('upper') or any(x is br for x in s.get('bridges_upper', [])): continue
            ab = AB.bridge(s['name'], br.get('door'), False)
            if ab is not None and ab.get('walkFrom'): continue          # drawn from its twin's walkway, not from the building
            if ab is not None and len(ab['walk']) >= 2:
                # close-out round 4: the app's walkway start E and direction d straight from the dump (gates.js walk[0] ->
                # walk[1]). Round 3 re-derived E from the stands polyline and took d towards the first polyline point > 0.5 m
                # from E - for E8 / B2 that is the attach point BEHIND E (inside the building), so d pointed into the
                # building, no facade was found within 8 m and the door was dropped (E8 0.5-0.76 m, B2 up to 1.37 m open)
                Ew, uw, vw = BHD.frame(ab)
                El = np.array(Lp(*Ew)); d = np.array([uw[0], -uw[1]])   # world (x, z) -> local (X, Y) = (x, -z) direction
            else:
                # app walkway start (gates.js prepGeom trim)
                Wl = [np.array(p, float) for p in wpts]
                E = Wl[0]
                for i in range(len(Wl) - 2, -1, -1):
                    if not app.contains(Point(Wl[i])): continue
                    A, Bq = Wl[i], Wl[i + 1]
                    if app.contains(Point(Bq)): break
                    lo, hi = 0.0, 1.0
                    for _ in range(24):
                        mid = 0.5 * (lo + hi)
                        if app.contains(Point(A + (Bq - A) * mid)): lo = mid
                        else: hi = mid
                    E = A + (Bq - A) * hi; break
                El = np.array(Lp(*E))
                # direction of the walkway leaving the building at E
                nxt = next((np.array(Lp(*p)) for p in wpts[1:] if math.dist(Lp(*p), El) > 0.5), None)
                if nxt is None: continue
                d = (nxt - El) / np.hypot(*(nxt - El))
                Ew = np.array(Wp(*El)); uw = np.array([d[0], -d[1]]); vw = np.array([-uw[1], uw[0]])
            inside = bp.contains(Point(El))
            if inside:
                # app walkway starts inside our facade: march out along d to the facade
                t = 0.0
                while t < 30 and bp.contains(Point(El + d * t)): t += 0.05
                X = El + d * t; pen = t
            else:
                t = 0.0
                while t < 8.0 and not bp.contains(Point(El - d * t)): t += 0.05
                if t >= 8.0: continue
                X = El - d * t; pen = -t
            host = next((o for o in W.S if isHost(o) and o.poly.buffer(0.1).contains(Point(X))), None)
            if host is None: continue
            # close-out round 4: the closing box over the walkway's whole width (bridge_head.py): oblique facades (B2 -0.72 ..
            # +1.37 m across the end), ends past a corner, drums behind the end
            head = BHD.head_box(BHD.depths(body_w, Ew, uw, vw))
            # close-out r3 fix 2: the app walkway floor at the facade X and at the walkway start E (gates.js DEPARTURE_LEVELS
            # per pier + the walkway's slope to its rotunda, tools/blender/app_bridges.json); every height of the door parts
            # is taken from these (it was the one 5.4-m level for all piers)
            ab = AB.bridge(s['name'], br.get('door'), False)
            if ab is not None:
                f_x, f_e = AB.floor_at(ab, *Wp(*X)), AB.floor_at(ab, *Wp(*El))
                lvl, lvl_tag = ab['Hb'], ab['HbTag']
            else:
                f_x = f_e = lvl = PIER_LEVEL.get(s['letter'], FLOOR2); lvl_tag = 'inf (no app_bridges record: pier level)'
            fl0, fl1 = min(f_x, f_e), max(f_x, f_e)
            vz0, vz1 = fl0 + VEST_DZ[0], fl1 + VEST_DZ[1]
            low = host.h < vz1 + 0.4                            # roof below the walkway head: bulkhead above the roof
            gap = max(0.0, -pen)
            notch = LineString([tuple(X - d * 0.1), tuple(X + d * (gap + 6.0))]).buffer(VEST['w'] / 2 + 0.4, cap_style=2)
            # review r2: the app's rotunda drums within reach (any bridge's: twin heads) - door parts are clipped / culled there.
            # Close-out round 4: at the drawn radius + VEST_CLEAR (0.05; the drum is a fixed cylinder, gates.js cyl 24 sides
            # inscribed) - with rc (+0.1, and the radius upper bound) a 0.1-0.6 m slot stayed between the vestibule and the drum
            # that closes a short walkway's end (E3 / E9 / F7 / F8); + the OTHER bridges' fixed walkway solids in the band
            z1v = vz1 if not low else max(vz1, host.h + 1.0)
            dc = [circle(dr['c'], (dr['r'] if dr['r_app'] is not None else dr['rc']) + BHD.VEST_CLEAR, 64) for dr in DRUMS
                  if math.dist(dr['c'], tuple(X)) < dr['rc'] + 8.0 and not (dr['band'][0] > z1v or dr['band'][1] < vz0)]
            oc = BHD.other_solids_cut(allb, {(s['name'], br.get('door'), False)}, Ew, vz0, z1v, drums=False)
            if oc is not None: dc.append(loc(oc))
            out.append(dict(stand=s['name'], gate=br.get('gate'), door=br.get('door'), X=tuple(X), E=tuple(El), d=tuple(d), gap=round(gap, 3),
                            penetration=round(max(0.0, pen), 3), host=host.key, bld=host.bld, low=low, h_host=host.h, notch=notch,
                            drum_cut=unary_union(dc) if dc else None, head=head,
                            level=lvl, level_tag=lvl_tag, fl0=round(fl0, 3), fl1=round(fl1, 3), vz0=round(vz0, 3), vz1=round(vz1, 3),
                            dz0=round(fl0 + DOOR_DZ[0], 3), wtop=round(fl1 + 3.0, 3)))
    return out


def bulkhead_back(d):
    """how far a bulkhead reaches behind the facade: 2.5 m, or past the app walkway's start where that lies further inside
    (review r1: the walkway top 8.45 m must not reach above a 7.9-m deck anywhere)"""
    return max(2.5, float(d['penetration']) + 0.5)


def bulkhead_hole(d):
    """plan footprint (local) of a bulkhead: the host deck is cut there and the bulkhead's top closes it (review r2: less the
    app's rotunda drums, as the bulkhead itself)."""
    X, El, dd = np.array(d['X']), np.array(d['E']), np.array(d['d'])
    A = X - dd * bulkhead_back(d); Bp = El if d['gap'] > 0.12 else X
    c = (A + Bp) / 2; L = float(np.hypot(*(Bp - A)))
    n = np.array([dd[1], -dd[0]]); w = VEST['w'] / 2 - 0.02
    g = Polygon([tuple(c - dd * L / 2 - n * w), tuple(c + dd * L / 2 - n * w), tuple(c + dd * L / 2 + n * w), tuple(c - dd * L / 2 + n * w)])
    if d.get('drum_cut') is not None: g = largest(_clean(g.difference(d['drum_cut']), 0.05))
    return g


def vest_poly(d):
    """plan footprint (local) of the vestibule / bulkhead box of a door, less the app's rotunda drums (review r2) and the other
    bridges' fixed walkway solids (close-out round 4). Close-out round 4: the box spans the closing extent of
    bridge_head.head_box over the walkway's whole width (from the deepest facade point + 0.15 m to the walkway end face E; a
    nub where the end lies inside the facade but its edge passes a corner) - it was the centreline facade point X - 0.15 -> E,
    which left oblique facades open on one side. The bulkhead (low roof) keeps its round-1 extent."""
    X, El, dd = np.array(d['X']), np.array(d['E']), np.array(d['d'])
    n = np.array([dd[1], -dd[0]]); w = VEST['w'] / 2
    hb = d.get('head') or {}
    if d['low']:
        A = X - dd * bulkhead_back(d); Bp = El if d['gap'] > 0.12 else X
        if hb.get('kind'): A = El + dd * min(float((A - El) @ dd), hb['a0']); Bp = El + dd * max(float((Bp - El) @ dd), hb['a1'])
    elif hb.get('kind'):
        A = El + dd * hb['a0']; Bp = El + dd * hb['a1']
    else:
        return Polygon()
    c = (A + Bp) / 2; L = float(np.hypot(*(Bp - A)))
    g = Polygon([tuple(c - dd * L / 2 - n * w), tuple(c + dd * L / 2 - n * w), tuple(c + dd * L / 2 + n * w), tuple(c - dd * L / 2 + n * w)])
    if d.get('drum_cut') is not None: g = largest(_clean(g.difference(d['drum_cut']), 0.05))
    return M.orient_all(g) if not g.is_empty else g


def door_geom(mb, det, lod, d):
    X, El, dd = np.array(d['X']), np.array(d['E']), np.array(d['d'])
    n = np.array([dd[1], -dd[0]])
    dcut = d.get('drum_cut')
    hb = d.get('head') or {}
    if hb.get('kind') or d['low']:
        z1 = d['vz1'] if not d['low'] else max(d['vz1'], d['h_host'] + 1.0)
        vp = vest_poly(d)
        if not vp.is_empty and vp.area > 0.05:
            # (review r2: clipped around the app's rotunda drum, the drum closes the walkway end there; close-out round 4:
            # the closing extent over the walkway's whole width, clipped clear of the other bridges' walkway solids too)
            M.prism(mb, vp, d['vz0'], z1, 'panel_light', top_mat='coping', bottom_mat='panel_light', tile=tl('panel_light'))
    if lod == 0:
        # door surround on the facade (or on the vestibule end) AROUND the walkway section (gates.js WALK_W 2.6 x WALK_H 3.0
        # at the pier's DEPARTURE_LEVELS floor, d['fl0'] / d['wtop']): two jambs and a head 0.12 m proud, clear of the
        # walkway, and a dark leaf 0.02 m proud inside it (the closed door behind the docked bridge's end) [inf]
        P = np.array(d['E']) if hb.get('kind') == 'vestibule' else X
        wj = 0.25; off = WALK_W_APP / 2 + 0.05 + wj / 2

        def clear(c, w, h):
            """review r2: a surround member is left out where it would stand inside an app rotunda drum (+0.1 m)."""
            if dcut is None: return True
            q = Polygon([tuple(c + n * w / 2 + dd * h / 2), tuple(c - n * w / 2 + dd * h / 2), tuple(c - n * w / 2 - dd * h / 2), tuple(c + n * w / 2 - dd * h / 2)])
            return not q.intersects(dcut)
        for sg in (-1, 1):
            cj = P + dd * 0.06 + n * sg * off
            if clear(cj, wj, 0.12):
                M.boxm(det, tuple(cj), tuple(n), wj, 0.12, (d['dz0'], d['wtop'] + 0.4), 'mullion', (3.0, 3.0), top=True)
        if clear(P + dd * 0.06, WALK_W_APP + 0.1 + 2 * wj, 0.12):
            M.boxm(det, tuple(P + dd * 0.06), tuple(n), WALK_W_APP + 0.1 + 2 * wj, 0.12, (d['wtop'] + 0.08, d['wtop'] + 0.4), 'mullion', (3.0, 3.0), top=True,
                   bottom=True)
        if clear(P + dd * 0.01, WALK_W_APP + 0.1, 0.02):
            M.boxm(det, tuple(P + dd * 0.01), tuple(n), WALK_W_APP + 0.1, 0.02, (d['fl0'], d['wtop'] + 0.08), 'door_dark', (3.0, 3.0), top=False)


# ------------------------------------------------------------------------------------------------ parts per building
BLD_INFO = {
    'T1': ('Harvey Milk Terminal 1 Center', 'unk'), 'BA_B': ('Boarding Area B', 'obs'), 'BA_C': ('Boarding Area C', 'obs'),
    'T2': ('Terminal 2', 'unk'), 'BA_D': ('Boarding Area D', 'obs'), 'T3W': ('Terminal 3 West', 'pub'), 'T3E': ('Terminal 3 East', 'inf'),
    'BA_E': ('Boarding Area E', 'obs'), 'BA_F': ('Boarding Area F', 'obs'),
    'C3C': ('Courtyard 3 Connector office block', 'inf')}


def build(lod):
    """{building: [Part]} for one LOD; shells (AO) and details."""
    W, feats, info = build_world(lod)
    out = {}
    for bld in BLD_INFO:
        sh = MB(f'{bld}_shell'); det = MB(f'{bld}_detail'); pvm = MB(f'{bld}_pv'); fin = MB(f'{bld}_fins')
        sol = [s for s in W.S if s.bld == bld]
        for s in sol:
            emit_walls(sh, fin, W, s, lod, mull_geom=(lod == 0))
            emit_roof(sh, W, s, lod)
        for f in feats:
            if f.bld != bld: continue
            if f.kind == 'pv': f.fn(sh, pvm, lod)
            else: f.fn(sh, det, lod)
        nm, tag = BLD_INFO[bld]
        dims = {s.key: dict(h=tagdim(s.h, s.tag, 'see spec keys'), z0=tagdim(s.z0, 'inf' if s.z0 else 'obs', 'apron / host deck')) for s in sol}
        P = [Part(f'{bld}_shell', sh, 'shell', tag, nm + ': walls, roofs, roof features', spec=sorted({k for s in sol for k in s.spec}), dims=dims)]
        if not det.empty():
            P.append(Part(f'{bld}_detail', det, 'detail', 'inf', nm + ': bridge door frames, skylight frames, canopy brackets'))
        if not fin.empty():
            P.append(Part(f'{bld}_fins', fin, 'detail', 'inf', nm + ': curtain-wall mullion fins (LOD0 only)',
                          extra=dict(max_dist_m=FIN_MAX_M, max_dist_note='hide beyond this camera distance to the node bounding box '
                                     '(sub-pixel fins alias; the curtain caps of the glass tiles carry the rhythm)')))
        if not pvm.empty():
            P.append(Part(f'{bld}_pv', pvm, 'detail', 'obs', nm + ': PV rack blocks (NAIP 2024 extents [obs]; rack height inf)',
                          spec=['bab.pv', 'bab.pv_layout', 't1c.roof_pv']))
        out[bld] = P
    return out, W, info
