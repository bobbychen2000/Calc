"""The house: roofs solved from the aerial survey (survey/roof_3d.json, model/roof_solve.py), walls and facades under them.

Blocks (survey/roof.json): two-storey core with a flat deck on top, the balcony gable BG (E), west wing WW with its
west gable WG, front gable FG (SW, over the entry), south wing BC; one-storey garage wing (NW) and north wing, the
patio wing PB (SE), the wraparound porch (W / SW / S / E) and the north porch NCP.
Plan: U = the upper storey's wall outline (its eave outline set in by the overhang, the balcony cut out), G = the
ground storey's closed outline (U + the one-storey blocks + PB's room, minus the roofed open floors: the BG patio,
the dining recess under NC, the set-back wall under the core's diagonal NE face).  Ground walls rise to the upper
floor (Z2) or the one-storey roof above them, upper walls from Z2 to the two-storey roofs.  OPENINGS are given as plan
points on those walls (read through the registered / fitted cameras); the wall they lie on cuts and mounts them.
Front (street side, faces SW): the diagonal porch leg is the entry gable; columns from p01 through its fitted camera
(survey/pairs_world.json -> cams_world.json), mirrored about the entry's axis.  Rear: measured on p28 / p21.
Outward normals: massing_kit.wall() faces to the RIGHT of a -> b, so rings are walked counter-clockwise.
"""
import json
import os

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from model.kit import Geo, Part
from model.massing_kit import RoofPlane, roof_planes, wall
from model import plan

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOF = json.load(open(os.path.join(HERE, 'survey', 'roof_3d.json')))

OVERHANG = {1: 0.50, 2: 0.60}            # eave line -> wall face, plan metres
UNDER = 0.85                             # a roof hidden under an upper eave runs on this far uphill (into the wall)
Z_BASE = -2.5                            # walls start below every ground level; the terrain covers them
Z2 = 3.45                                # upper floor level: the upper walls start here, the ground walls stop under it
SLAB_T = 0.25
FLOOR = plan.FLOOR                       # main floor above the pool deck
PORCH_FLOOR = plan.FRONT_PORCH_FLOOR     # wraparound porch (4 risers above the front walk)
PATIO_FLOOR = plan.REAR_PATIO_FLOOR      # covered rear patios (BG, the NC recess, PB)
WALL = 'siding_shingle'
TRIM = 'trim_cream'
FRAME = 'frame_bronze'
MATERIALS = {
    'trim_cream': dict(color=(0.84, 0.80, 0.70), roughness=0.6),            # cream casings, fascia, columns, railings
    'frame_bronze': dict(color=(0.030, 0.026, 0.022), roughness=0.5, metallic=0.3),
    'door_espresso': dict(color=(0.035, 0.022, 0.016), roughness=0.5),
    'vent_louvre': dict(color=(0.42, 0.42, 0.40), roughness=0.8),
}
# ---- measured plan (p28 / p21 rays onto the floors, metres) ----------------------------------------------------------
BG_X_WALL = -11.0                        # BG upper wall (balcony doors): flush with the NC east wall
BG_X_POST = -9.15                        # BG corner posts (p28: (-9.2, -4.7) and (-9.15, 0.3))
BG_Y = (-4.40, 0.35)
REAR_X_GROUND = -12.4                    # ground-floor wall under BG and NC (the patio / dining recess is 3.2 / 1.4 m deep)
NC_Y_N = 5.6                             # NC north wall
DIAG = ((-10.8, -7.7), (-7.7, -10.7))    # the core's NE-facing 45 deg upper wall; the ground wall below is set back
DIAG_BACK = 1.5
PB_ROOM = (-9.0, -17.9, -0.6, -14.3)     # the enclosed part of the patio wing (x0, y0, x1, y1)
PB_COL_Y = -11.5                         # column line of its covered patio
# front colonnade (p01: the 4 west-run columns as pairs of the camera fit, rms 7 px): the column line stands ~1.15 m
# inside the eave (deep overhang with exposed rafter tails), the box beam's underside at 3.12
COL_X_W, COL_Y_S, COL_Y_N = -23.0, -15.42, -7.6
COL_TOP = 3.12                           # underside of the porch box beam = top of the column capitals
BEAM_H = 0.34                            # the south leg's flat roof (14 deg) leaves no more over the column line
PORCH_INSET = 1.0                        # eave -> porch floor edge / column line of the wraparound porch


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
        if p['block'] in LOW_PITCH_K:    # heights above the block's eave scaled (affine: the plane stays a plane)
            ze = ROOF['eaves'][p['block']]
            P = P.copy()
            P[:, 2] = ze + (P[:, 2] - ze) * LOW_PITCH_K[p['block']]
            c = ze + (c - ze) * LOW_PITCH_K[p['block']]
            a, b = a * LOW_PITCH_K[p['block']], b * LOW_PITCH_K[p['block']]
        Q = P
        if p['storey'] == 1 and any(k.startswith('under_upper') for k in p['edges']):
            # grow the plane under the upper roof only (hidden there), so it runs into the upper walls
            pp = Polygon(P[:, :2])
            g = pp.union(pp.buffer(UNDER, join_style=2).intersection(upper.buffer(-0.02)))
            if g.geom_type != 'Polygon':
                g = max(g.geoms, key=lambda q: q.area)
            xy = np.array(g.exterior.coords)[:-1]
            Q = np.c_[xy, a * xy[:, 0] + b * xy[:, 1] + c]
        if p['id'] == 'ncp_n':
            # the aerial sees only the strip outside the upper eave: the porch roof runs on up-slope to the NC north wall
            xy = [P[0, :2], P[1, :2], P[2, :2], (P[2, 0], NC_Y_N - 0.12), (P[3, 0], NC_Y_N - 0.12)]
            xy = np.array(xy, float)
            Q = np.c_[xy, a * xy[:, 0] + b * xy[:, 1] + c]
        elif p['id'] == 'ncp_e':
            xy = np.array([P[0, :2], P[1, :2], (BG_X_WALL - 0.12, P[2, 1]), (BG_X_WALL - 0.12, P[3, 1])], float)
            Q = np.c_[xy, a * xy[:, 0] + b * xy[:, 1] + c]
        elif p['id'] in ('gb_w', 'gb_e'):
            Q = garage_gable()[p['id']]
        elif p['id'] == 'g_s':
            Q = P[:3]                    # no notch: the (lower) gable runs into this plane and is buried where it is lower
        elif p['id'] in BG_RIDGE_K:
            Q = P.copy()
            ze = P[:, 2].min()
            Q[:, 2] = ze + (P[:, 2] - ze) * BG_RIDGE_K[p['id']]
        mat = 'roof_flat' if p['flat'] else 'roof_shingle'
        out.append(dict(rp=RoofPlane(p['id'], Q, mat=mat, thickness=0.22, storey=p['storey'], fascia=TRIM), src=p))
    return out


GARAGE_GABLE_PITCH = 26.0                # the aerial's symmetric gable (ridge displaced 17 px by its height) + p01's apex
# garage + north wing roofs: the solve's 23-27 deg (its pitch prior) stood 0.5-0.65 m above the roof's silhouette in
# p01; at ~19 deg the garage gable's ridge (26 deg, apex 4.44) meets g_s exactly at the surveyed valley apex
LOW_PITCH_K = {'garage_wing': 0.70, 'north_wing': 0.70}
BG_RIDGE_K = {'bg_n': 0.886, 'bg_s': 0.886}   # balcony gable ridge 8.17 -> 7.97 (p21: apex 0.2 m lower; epi: 7.5-8.0)


def garage_gable():
    """The garage's south gable rebuilt symmetric about the middle of its two rake feet (the solve put its ridge
    0.3 m off centre and 0.45 m high: 30 / 37 deg planes).  Returns both planes + apex / feet for the trim."""
    P = {p['id']: np.array(p['poly']) for p in ROOF['planes'] if p['id'] in ('gb_w', 'gb_e')}
    fw, fe = P['gb_w'][2], P['gb_e'][2]                              # rake feet (fascia line)
    yb = P['gb_w'][0][1]                                             # the old valley apex: far enough to be buried
    xr, ze = (fw[0] + fe[0]) / 2, (fw[2] + fe[2]) / 2
    za = ze + (fe[0] - fw[0]) / 2 * np.tan(np.radians(GARAGE_GABLE_PITCH))
    yf = (fw[1] + fe[1]) / 2
    return {'gb_w': np.array([(xr, yb, za), (xr, yf, za), (fw[0], yf, ze), (fw[0], yb, ze)]),
            'gb_e': np.array([(xr, yb, za), (fe[0], yb, ze), (fe[0], yf, ze), (xr, yf, za)]),
            'apex': np.array([xr, yf, za]), 'foot_w': np.array([fw[0], yf, ze]), 'foot_e': np.array([fe[0], yf, ze])}


def _aerial_xy(uv, z):
    from model import frame
    from tools import cams as CAMS
    cam = frame.world_cams()['photos/p29_ddf5dc.jpg']
    o, d = CAMS.ray(cam, [uv])
    t = (z - o[2]) / d[0][2]
    return (o + t * d[0])[:2]


ENTRY_PITCH = 26.0                       # p01 / hero: rise 100 px over a half-width of 212 px, seen frontally


def entry_frame():
    """The diagonal entry leg: M = middle of its outer eave, t along the eave (to the right seen from the street),
    n into the house, half = half the gable's width (the leg's whole length), eave height."""
    swp = next(np.array(p['poly']) for p in ROOF['planes'] if p['id'] == 'swp')
    L, R = swp[4, :2], swp[3, :2]                                    # outer eave: left / right rake feet
    M = (L + R) / 2
    t = (R - L) / np.linalg.norm(R - L)
    n = np.array([-t[1], t[0]])
    return M, t, n, float(np.linalg.norm(R - L)) / 2, float(swp[3:5, 2].mean())


def entry_gable(geo, planes):
    """The entry gable over the front steps: the whole diagonal porch leg is one gable facing SW (aerial: its outer eave
    is the gable foot, 4.2 m wide), ridge running NE under the front gable FG's eave into its wall."""
    M, t, n, half, eave = entry_frame()
    rise = half * np.tan(np.radians(ENTRY_PITCH))
    E = lambda q, z: np.array([q[0], q[1], z])                        # noqa: E731
    a0, a1 = M, M + n * 3.1
    zt, ze = eave + rise, eave
    for sgn in (1, -1):
        pts = [E(a0, zt), E(a1, zt), E(a1 + t * sgn * half, ze), E(a0 + t * sgn * half, ze)]
        planes.append(dict(rp=RoofPlane('entry_gable_%d' % sgn, pts, mat='roof_shingle', thickness=0.18, storey=1,
                                        fascia=TRIM),
                           src={'id': 'entry_gable', 'block': 'porch_1st', 'storey': 1}))
    # pediment over the two entry columns: shingled field, king post, box beam, knee braces under the rake feet
    c = M + n * 0.55
    hb = half - 0.55
    zb = eave - 0.30
    tri = [E(c - t * hb, zb + 0.30), E(c + t * hb, zb + 0.30), E(c, zb + 0.30 + hb * np.tan(np.radians(ENTRY_PITCH)))]
    geo.poly(WALL, tri[::-1])
    geo.poly(WALL, tri)
    t3, n3 = np.array([t[0], t[1], 0.0]), np.array([n[0], n[1], 0.0])
    geo.prism(TRIM, [(-0.07, -0.05), (0.07, -0.05), (0.07, 0.05), (-0.07, 0.05)], E(c, zb + 0.3) - n3 * 0.05,
              tri[2] - n3 * 0.05, up=-n3, cap=False)
    for sgn in (-1, 1):
        knee_brace(geo, E(c + t * sgn * (hb + 0.05), zb - 0.55) - n3 * 0.0, -n3, t3 * sgn, size=0.55, t=0.10)


# =====================================================================================================================
# small builders: columns, beams, railings, windows, doors
# =====================================================================================================================
def _frame(a, b):
    a, b = np.asarray(a, float)[:2], np.asarray(b, float)[:2]
    L = float(np.linalg.norm(b - a))
    r = np.array([(b - a)[0] / L, (b - a)[1] / L, 0.0])
    return r, np.array([r[1], -r[0], 0.0]), L                  # right, out (to the right of a -> b), length


def _lbox(geo, mat, o, r, n, lo, hi, faces='xXyYzZ'):
    """Box in a wall frame (r right, n out, z up).  That frame is LEFT-handed (r x n = -z), which would turn every face
    inside out in Geo.obox: build it in the right-handed frame (r, -n, z) instead; face letters y / Y keep their meaning
    (y = the side toward the house, Y = the side facing out)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    nn = -np.asarray(n, float)
    geo.obox(mat, o, r, nn, (0, 0, 1), (x0, -y1, z0), (x1, -y0, z1), faces.translate(str.maketrans('yY', 'Yy')))


def beam(geo, a, b, z0, z1, t=0.20, mat=TRIM, e0=None, e1=None):
    """Box beam from a to b; e0 / e1 = how far it runs past its ends (default half its thickness)."""
    r, n, L = _frame(a, b)
    e0 = t / 2 if e0 is None else e0
    e1 = t / 2 if e1 is None else e1
    _lbox(geo, mat, (a[0], a[1], 0.0), r, n, (-e0, -t / 2, z0), (L + e1, t / 2, z1))


def column_sq(geo, x, y, z0, z1, s=0.28, ang=0.0, mat=TRIM):
    """Plain square post with a base block and a stepped capital (rear porches, the balcony)."""
    ex, ey = (np.cos(ang), np.sin(ang), 0.0), (-np.sin(ang), np.cos(ang), 0.0)
    h = s / 2
    geo.obox(mat, (x, y, 0), ex, ey, (0, 0, 1), (-h - 0.04, -h - 0.04, z0), (h + 0.04, h + 0.04, z0 + 0.22), 'xXyYZ')
    geo.obox(mat, (x, y, 0), ex, ey, (0, 0, 1), (-h, -h, z0 + 0.22), (h, h, z1 - 0.14), 'xXyY')
    geo.obox(mat, (x, y, 0), ex, ey, (0, 0, 1), (-h - 0.05, -h - 0.05, z1 - 0.14), (h + 0.05, h + 0.05, z1), 'xXyYz')


def column_craft(geo, x, y, z0, z1, ang=0.0, pier=0.60, pier_h=0.92, s0=0.47, s1=0.37, ground=None):
    """Tapered square cream column on a stone pier with a bluestone cap (the wraparound porch)."""
    ex, ey = np.array([np.cos(ang), np.sin(ang), 0.0]), np.array([-np.sin(ang), np.cos(ang), 0.0])
    o = np.array([x, y, 0.0])
    zb = z0 - 1.0 if ground is None else ground - 0.3
    h = pier / 2
    geo.obox('stone_veneer', o, ex, ey, (0, 0, 1), (-h, -h, zb), (h, h, z0 + pier_h), 'xXyY')
    geo.obox('bluestone', o, ex, ey, (0, 0, 1), (-h - 0.04, -h - 0.04, z0 + pier_h), (h + 0.04, h + 0.04, z0 + pier_h + 0.06))
    za, zt = z0 + pier_h + 0.06, z1 - 0.16
    geo.obox(TRIM, o, ex, ey, (0, 0, 1), (-s0 / 2 - 0.03, -s0 / 2 - 0.03, za), (s0 / 2 + 0.03, s0 / 2 + 0.03, za + 0.10), 'xXyYZ')
    c0 = [o + ex * sx * s0 / 2 + ey * sy * s0 / 2 + (0, 0, za + 0.10) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    c1 = [o + ex * sx * s1 / 2 + ey * sy * s1 / 2 + (0, 0, zt) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4):
        j = (i + 1) % 4
        geo.poly(TRIM, [c0[i], c0[j], c1[j], c1[i]])
    geo.obox(TRIM, o, ex, ey, (0, 0, 1), (-s1 / 2 - 0.06, -s1 / 2 - 0.06, zt), (s1 / 2 + 0.06, s1 / 2 + 0.06, z1), 'xXyYz')


def railing(geo, a, b, z0, h=0.92, gap=0.14, mat=TRIM, inset=0.0):
    """Top + bottom rail with square balusters between plan points a and b (floor at z0)."""
    r, n, L = _frame(a, b)
    L -= 2 * inset
    if L < 0.25:
        return
    o = np.array([a[0], a[1], 0.0]) + r * inset
    _lbox(geo, mat, o, r, n, (0, -0.045, z0 + h - 0.07), (L, 0.045, z0 + h), 'yYzZ')
    _lbox(geo, mat, o, r, n, (0, -0.035, z0 + 0.10), (L, 0.035, z0 + 0.17), 'yYzZ')
    k = max(1, int(round(L / gap)))
    for i in range(k):
        s = (i + 0.5) * L / k
        _lbox(geo, mat, o, r, n, (s - 0.022, -0.022, z0 + 0.17), (s + 0.022, 0.022, z0 + h - 0.07), 'xXyY')


def _bx(geo, mat, o, r, n, x0, x1, z0, z1, y0, y1, faces='xXyYzZ'):
    _lbox(geo, mat, o, r, n, (x0, y0, z0), (x1, y1, z1), faces)


def window(geo, o, r, n, w, h, units=1, divided=True, casing=0.11, sill=True, glass='glass'):
    """This house's window in a hole w x h (o = its lower-left corner on the wall face, r right, n out): cream casing,
    `units` dark-bronze units side by side, each a 2 x 2 divided upper part over one large lower lite."""
    c = casing
    _bx(geo, TRIM, o, r, n, -c, 0, -0.02, h + c, -0.02, 0.035)
    _bx(geo, TRIM, o, r, n, w, w + c, -0.02, h + c, -0.02, 0.035)
    _bx(geo, TRIM, o, r, n, -c - 0.03, w + c + 0.03, h, h + c + 0.02, -0.02, 0.05)
    if sill:
        _bx(geo, TRIM, o, r, n, -c - 0.03, w + c + 0.03, -0.07, 0.0, -0.02, 0.07)
    geo.poly(glass, [o + r * 0 - n * 0.06, o + r * w - n * 0.06, o + r * w - n * 0.06 + (0, 0, h), o - n * 0.06 + (0, 0, h)])
    uw = w / units
    f = 0.05
    for i in range(units):
        x0, x1 = i * uw, (i + 1) * uw
        for (xa, xb, za, zb) in ((x0, x0 + f, 0, h), (x1 - f, x1, 0, h), (x0 + f, x1 - f, 0, f), (x0 + f, x1 - f, h - f, h)):
            _bx(geo, FRAME, o, r, n, xa, xb, za, zb, -0.06, -0.015, 'xXyYzZ'.replace('y', ''))
        if divided:
            zm = h * 0.58
            _bx(geo, FRAME, o, r, n, x0 + f, x1 - f, zm - 0.022, zm + 0.022, -0.06, -0.03, 'YzZ')
            _bx(geo, FRAME, o, r, n, (x0 + x1) / 2 - 0.012, (x0 + x1) / 2 + 0.012, zm + 0.022, h - f, -0.06, -0.04, 'xXY')
            zq = (zm + h - f) / 2
            _bx(geo, FRAME, o, r, n, x0 + f, x1 - f, zq - 0.012, zq + 0.012, -0.06, -0.04, 'YzZ')


def door(geo, o, r, n, w, h, leaves=1, kind='glass', casing=0.11, mat=None, lights=0):
    """Doors in a hole w x h: 'glass' = full-lite dark-framed leaves (French doors), 'wood' = the espresso entry door
    (three small top lights), 'solid' = a plain painted slab."""
    c = casing
    cm = 'door_espresso' if kind == 'wood' else TRIM
    _bx(geo, cm, o, r, n, -c, 0, 0, h + c, -0.02, 0.035)
    _bx(geo, cm, o, r, n, w, w + c, 0, h + c, -0.02, 0.035)
    _bx(geo, cm, o, r, n, -c - 0.03, w + c + 0.03, h, h + c + 0.02, -0.02, 0.05)
    lw = w / leaves
    if kind == 'glass':
        geo.poly('glass', [o - n * 0.07, o + r * w - n * 0.07, o + r * w - n * 0.07 + (0, 0, h), o - n * 0.07 + (0, 0, h)])
        f = 0.10
        for i in range(leaves):
            x0, x1 = i * lw, (i + 1) * lw
            for (xa, xb, za, zb) in ((x0, x0 + f, 0, h), (x1 - f, x1, 0, h), (x0 + f, x1 - f, 0, 0.22), (x0 + f, x1 - f, h - f, h)):
                _bx(geo, FRAME, o, r, n, xa, xb, za, zb, -0.07, -0.02, 'xXYzZ')
            for k in range(lights):
                zz = 0.22 + (h - f - 0.22) * (k + 1) / (lights + 1)
                _bx(geo, FRAME, o, r, n, x0 + f, x1 - f, zz - 0.012, zz + 0.012, -0.07, -0.045, 'YzZ')
    else:
        m = mat or ('door_espresso' if kind == 'wood' else 'frame_bronze')
        for i in range(leaves):
            x0, x1 = i * lw, (i + 1) * lw
            _bx(geo, m, o, r, n, x0 + 0.005, x1 - 0.005, 0, h, -0.09, -0.03, 'xXY')
            if kind == 'wood':                                 # three small lights under the top rail
                for k in range(3):
                    xa = x0 + 0.14 + k * (lw - 0.28) / 3 + 0.02
                    xb = xa + (lw - 0.28) / 3 - 0.04
                    geo.poly('glass', [o + r * xa - n * 0.028 + (0, 0, h - 0.50), o + r * xb - n * 0.028 + (0, 0, h - 0.50),
                                       o + r * xb - n * 0.028 + (0, 0, h - 0.16), o + r * xa - n * 0.028 + (0, 0, h - 0.16)])


def garage_door(geo, o, r, n, w, h):
    """Carriage-style sectional door: cream panels with a row of small top lights, cream casing."""
    c = 0.12
    _bx(geo, TRIM, o, r, n, -c, 0, 0, h + c, -0.02, 0.04)
    _bx(geo, TRIM, o, r, n, w, w + c, 0, h + c, -0.02, 0.04)
    _bx(geo, TRIM, o, r, n, -c - 0.03, w + c + 0.03, h, h + c + 0.03, -0.02, 0.055)
    _bx(geo, 'door_garage', o, r, n, 0, w, 0, h, -0.14, -0.08, 'Y')
    for i in range(1, 4):                                      # section joints
        _bx(geo, 'door_garage', o, r, n, 0.04, w - 0.04, h * i / 4 - 0.25, h * i / 4 - 0.02, -0.08, -0.065, 'xXYzZ')
    k = max(2, int(round(w / 0.62)))
    for i in range(k):
        xa, xb = 0.12 + i * (w - 0.24) / k + 0.05, 0.12 + (i + 1) * (w - 0.24) / k - 0.05
        geo.poly('glass', [o + r * xa - n * 0.062 + (0, 0, h - 0.48), o + r * xb - n * 0.062 + (0, 0, h - 0.48),
                           o + r * xb - n * 0.062 + (0, 0, h - 0.12), o + r * xa - n * 0.062 + (0, 0, h - 0.12)])
        _bx(geo, TRIM, o, r, n, xa - 0.05, xa, h - 0.50, h - 0.10, -0.08, -0.055, 'xXY')
    _bx(geo, TRIM, o, r, n, 0.04, w - 0.04, h - 0.10, h - 0.02, -0.08, -0.055, 'YzZ')


def gable_vent(geo, o, r, n, w, h):
    """Triangular louvred gable vent (base w, height h; o = the middle of its base) with a king post and cream trim."""
    A, B, C = o - r * w / 2, o + r * w / 2, o + np.array([0, 0, h])
    geo.poly('vent_louvre', [A + n * 0.03, B + n * 0.03, C + n * 0.03])
    k = max(3, int(h / 0.11))
    for i in range(1, k):
        t = i / k
        geo.prism(TRIM, [(-0.012, -0.012), (0.012, -0.012), (0.012, 0.012), (-0.012, 0.012)],
                  A + (C - A) * t * 0 + r * (w / 2 * t) + (0, 0, h * t) + n * 0.045, B - r * (w / 2 * t) + (0, 0, h * t) + n * 0.045, cap=False)
    for P, Q in ((A, B), (A, C), (B, C)):
        geo.prism(TRIM, [(-0.05, -0.02), (0.05, -0.02), (0.05, 0.03), (-0.05, 0.03)], P + n * 0.05, Q + n * 0.05, up=n, cap=False)
    geo.prism(TRIM, [(-0.05, -0.03), (0.05, -0.03), (0.05, 0.03), (-0.05, 0.03)], o + n * 0.06, C + n * 0.06, up=n, cap=False)


def knee_brace(geo, p, n, side, size=0.75, t=0.11):
    """Craftsman knee brace under a rake: p = the foot on the wall face, n = out of the wall, side = unit vector along the
    wall; an upright on the wall, an outrigger under the rake and the diagonal between."""
    p, n = np.asarray(p, float), np.asarray(n, float)
    sec = [(-t / 2, -t / 2), (t / 2, -t / 2), (t / 2, t / 2), (-t / 2, t / 2)]
    geo.prism(TRIM, sec, p + n * t / 2, p + n * t / 2 + (0, 0, size), up=side)
    geo.prism(TRIM, sec, p + (0, 0, size - t / 2), p + n * size + (0, 0, size - t / 2), up=(0, 0, 1))
    geo.prism(TRIM, sec, p + n * t / 2 + (0, 0, 0.06), p + n * (size - 0.08) + (0, 0, size - t), up=side, cap=False)


# =====================================================================================================================
# footprints and walls
# =====================================================================================================================
def _footprint(planes, blocks, storey, inset=None):
    """Eave outline of the given blocks (plan union of their visible planes) set in by the overhang."""
    polys = [Polygon(np.array(p['src']['poly'])[:, :2]).buffer(0.02) for p in planes
             if 'poly' in p['src'] and p['src']['block'] in blocks]
    u = unary_union(polys).buffer(0.25, join_style=2).buffer(-0.25, join_style=2)     # close slivers between planes
    return u.buffer(-(OVERHANG[storey] if inset is None else inset), join_style=2)


def _rings(geom, amin=1.0):
    gs = [geom] if geom.geom_type == 'Polygon' else [g for g in getattr(geom, 'geoms', []) if g.geom_type == 'Polygon']
    return [g for g in gs if g.area > amin]


def _simplify(g):
    return g.buffer(0.08, join_style=2).buffer(-0.16, join_style=2).buffer(0.08, join_style=2).simplify(0.12)


def footprints(planes):
    """U = upper-storey wall outline, G = ground-storey closed outline, plus the open (roofed) floors."""
    st2 = {p['src']['block'] for p in planes if p['src']['storey'] == 2}
    f2 = _footprint(planes, st2, 2)
    U = f2.difference(box(BG_X_WALL, BG_Y[0] - 1.5, BG_X_WALL + 6, BG_Y[1] + 1.5))            # the balcony is open
    f1 = _footprint(planes, {'garage_wing', 'north_wing'}, 1)
    (ax, ay), (bx, by) = DIAG
    d = DIAG_BACK * 0.7071
    diag = Polygon([(ax + 0.3, ay + 0.3), (bx + 0.3, by + 0.3), (bx - d, by - d), (ax - d, ay - d)])
    rear_open = box(REAR_X_GROUND, BG_Y[0], BG_X_WALL + 6, NC_Y_N)
    both = unary_union([f2, f1])
    bridge = both.buffer(0.8, join_style=2).buffer(-0.8, join_style=2).intersection(box(-23.5, -3.2, -16.0, 9.0))
    G = unary_union([both, bridge, box(*PB_ROOM)]).difference(unary_union([rear_open, diag]))
    patio_pb = box(PB_ROOM[0], PB_ROOM[3], PB_ROOM[2] + 0.15, PB_COL_Y + 0.2).union(diag).difference(G)
    patio_bg = unary_union([box(REAR_X_GROUND, BG_Y[0] - 0.2, BG_X_POST + 0.2, BG_Y[1] + 0.2),
                            box(REAR_X_GROUND, BG_Y[1], BG_X_WALL + 0.15, NC_Y_N)]).difference(G)   # N of BG: the recess only
    return dict(f2=f2, U=_simplify(U), G=_simplify(G), patio_pb=patio_pb, patio_bg=patio_bg, diag=diag)


def _wall_ring(geo, ring, z0, planes, storey, outer=True, log=None):
    ring = np.asarray(ring, float)
    cw = not Polygon(ring).exterior.is_ccw
    if cw == outer:
        ring = ring[::-1]                # counter-clockwise outer rings: wall() normals (right of a -> b) face out
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        r, n, L = _frame(a, b)
        if L < 0.05:
            continue
        holes, items = [], []
        for op in OPENINGS:
            kind, st, pt, zs, w, h = op[:6]
            if st != storey:
                continue
            if zs is None:
                zs = float(plan.ground_z(pt[0] - 1.0, pt[1])) + 0.05
            v = np.asarray(pt, float) - a
            s, dist = float(v @ r[:2]), float(v @ n[:2])
            if abs(dist) < 0.45 and w / 2 + 0.05 < s < L - w / 2 - 0.05:
                holes.append((s - w / 2, zs, s + w / 2, zs + h))
                items.append((op, s - w / 2, zs))
        wall(geo, WALL, a, b, z0, planes, holes=holes, reveal_mat=TRIM, reveal=0.07)
        for op, s0, zs in items:
            kind, st, pt, _, w, h = op[:6]
            kw = op[6] if len(op) > 6 else {}
            o = np.array([a[0], a[1], zs]) + r * s0
            if kind == 'win':
                window(geo, o, r, n, w, h, **kw)
            elif kind == 'door':
                door(geo, o, r, n, w, h, **kw)
            elif kind == 'garage':
                garage_door(geo, o, r, n, w, h)
            if log is not None:
                log.append(op)


def walls(geo, fp, planes):
    p1 = [p['rp'] for p in planes if p['src']['storey'] == 1]
    p2 = [p['rp'] for p in planes if p['src']['storey'] == 2]
    slabs = []
    done = []
    for g in _rings(fp['U'].union(box(BG_X_WALL - 0.1, BG_Y[0] - 0.1, BG_X_POST + 0.1, BG_Y[1] + 0.1))):
        ring = np.array(g.exterior.coords)[:-1]
        slabs.append(RoofPlane('slab', np.c_[ring, np.full(len(ring), Z2)], thickness=SLAB_T))
    for g in _rings(fp['U']):
        ring = np.array(g.buffer(-0.015, join_style=2).exterior.coords)[:-1]
        geo.extrude(WALL, ring, Z2 - SLAB_T, Z2, cap_top=False)
        _wall_ring(geo, np.array(g.exterior.coords)[:-1], Z2, p2, 'u', log=done)
        for hh in g.interiors:
            _wall_ring(geo, np.array(hh.coords)[:-1], Z2, p2, 'u', outer=False, log=done)
    for g in _rings(fp['G']):
        _wall_ring(geo, np.array(g.exterior.coords)[:-1], Z_BASE, p1 + slabs, 'g', log=done)
        for hh in g.interiors:
            _wall_ring(geo, np.array(hh.coords)[:-1], Z_BASE, p1 + slabs, 'g', outer=False, log=done)
    missing = [op for op in OPENINGS if op not in done]
    for op in missing:
        print('house: opening not placed', op[:3])
    return p1, p2


# =====================================================================================================================
# rear: balcony gable BG, the recess under NC, the north porch NCP, the court, the patio wing PB
# =====================================================================================================================
def rear(geo, fp, planes, eaves):
    p2 = [p['rp'] for p in planes if p['src']['storey'] == 2]
    y0, y1 = BG_Y
    xp, xw = BG_X_POST, BG_X_WALL
    zf = Z2 + 0.12                                              # balcony floor
    # balcony floor + its cream fascia band, posts below and above, header beam, the gable face with its vent
    geo.box('bluestone', (xw - 0.05, y0 - 0.14, zf - 0.06), (xp + 0.14, y1 + 0.14, zf))
    geo.box(TRIM, (xw - 0.05, y0 - 0.20, zf - 0.60), (xp + 0.20, y1 + 0.20, zf - 0.06), 'xXyYz')      # p21: ~0.55 deep
    zh = eaves['balcony_gable_2st'] - 0.22
    for y in (y0, y1):
        column_sq(geo, xp, y, PATIO_FLOOR, zf - 0.60, s=0.42)             # p21 / frame 134000: 0.40-0.45
        column_sq(geo, xp, y, zf, zh - 0.30, s=0.38)
        beam(geo, (xw, y), (xp, y), zh - 0.30, zh, t=0.22)
        railing(geo, (xw, y), (xp, y), zf, h=1.0, inset=0.13)
    beam(geo, (xp, y0), (xp, y1), zh - 0.30, zh, t=0.24)
    railing(geo, (xp, y0), (xp, y1), zf, h=1.0, inset=0.13)
    wall(geo, WALL, (xp, y0), (xp, y1), zh, p2)
    ym = (y0 + y1) / 2
    gable_vent(geo, np.array([xp, ym, zh + 0.25]), np.array([0, 1.0, 0]), np.array([1.0, 0, 0]), 3.0, 1.05)
    for y, sd in ((y0, -1), (y1, 1)):
        knee_brace(geo, (xp + 0.12, y, zh - 0.75), (1, 0, 0), (0, sd, 0), size=0.62)
    # the recess under NC: beam under the upper wall, the porch floor; the court beam and column
    zb = Z2 - SLAB_T
    beam(geo, (xw, y1), (xw, NC_Y_N), zb - 0.10, Z2, t=0.24)
    (ax, ay), (bx, by) = DIAG
    cc = (ax + 0.25, ay - 0.25)
    column_sq(geo, cc[0], cc[1], PATIO_FLOOR, zb, s=0.30, ang=np.pi / 4)
    beam(geo, DIAG[0], DIAG[1], zb - 0.10, Z2, t=0.24, e1=-0.45)      # stops short of the PB roof at the far end
    beam(geo, cc, (xp, y0), zb - 0.05, Z2, t=0.20)
    # patio wing PB: columns + beam along its pool side, floor
    ze = eaves['patio_1st'] - 0.24
    cols = [(PB_ROOM[2] - 0.15, PB_COL_Y), (bx + 0.1, PB_COL_Y + 0.15)]
    for c in cols:
        column_sq(geo, c[0], c[1], PATIO_FLOOR, ze - 0.28, s=0.32)
    beam(geo, cols[0], cols[1], ze - 0.28, ze, t=0.22)
    beam(geo, cols[0], (cols[0][0], PB_ROOM[3]), ze - 0.28, ze, t=0.22)
    for key in ('patio_pb', 'patio_bg'):
        for g in _rings(fp[key], 0.3):
            geo.extrude('bluestone', np.array(g.exterior.coords)[:-1], PATIO_FLOOR - 0.9, PATIO_FLOOR)
    # north porch NCP: plain columns at its NE corner and along the north side, beam, floor (2 risers above the deck)
    zn = eaves['north_porch'] - 0.24
    ncp = [(xw + 0.1, NC_Y_N + 1.5), (-14.0, NC_Y_N + 1.5), (-16.9, NC_Y_N + 1.5)]
    for c in ncp:
        column_sq(geo, c[0], c[1], plan.NCP_FLOOR, zn - 0.26, s=0.30)
    beam(geo, ncp[0], ncp[2], zn - 0.26, zn, t=0.22)
    beam(geo, ncp[0], (ncp[0][0], NC_Y_N), zn - 0.26, zn, t=0.22)
    geo.extrude('bluestone', [(-17.1, NC_Y_N), (xw + 0.3, NC_Y_N), (xw + 0.3, NC_Y_N + 1.7), (-17.1, NC_Y_N + 1.7)],
                plan.NCP_FLOOR - 0.9, plan.NCP_FLOOR)
    # stone-clad section at the north end of PB's east face (p28)
    x1 = PB_ROOM[2]
    geo.box('stone_veneer', (x1 - 0.2, PB_ROOM[3] - 1.5, PATIO_FLOOR - 0.5), (x1 + 0.06, PB_ROOM[3] + 0.06, ze - 0.3), 'XyY')


# =====================================================================================================================
# porches
# =====================================================================================================================
def _outer_edges(poly, closed, tol=0.35):
    """Edges of a porch footprint that do not run along the closed house (the open sides)."""
    out = []
    ring = np.array(poly.exterior.coords)[:-1]
    if Polygon(ring).exterior.is_ccw:
        ring = ring[::-1]
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        if np.linalg.norm(b - a) < 0.4:
            continue
        if closed.distance(Point((a + b) / 2)) > tol:
            out.append((a, b))
    return out


def porch_auto(geo, poly, closed, z_floor, eave_z, craft=True, rail=False, span=3.2, skip=None):
    """A roof on columns: columns at the ends of every open edge and every ~span metres, a box beam, the floor
    (stone skirt, bluestone top).  skip: a plan region whose columns / beams are built elsewhere."""
    top = (COL_TOP + BEAM_H) if craft else eave_z - 0.24
    seen = []
    for a, b in _outer_edges(poly, closed):
        r, n, L = _frame(a, b)
        if skip is not None and skip.contains(Point((a + b) / 2)):
            continue
        k = max(1, int(round(L / span)))
        pts = [a + (b - a) * t for t in np.arange(k + 1) / k]
        ang = float(np.arctan2(r[1], r[0]))
        for p in pts:
            if closed.distance(Point(p)) < 0.5 or any(np.linalg.norm(p - q) < 0.6 for q in seen):
                continue
            seen.append(p)
            if skip is not None and skip.contains(Point(p)):
                continue
            if craft:
                column_craft(geo, p[0], p[1], z_floor, COL_TOP, ang, ground=plan.ground_z(p[0], p[1]))
            else:
                column_sq(geo, p[0], p[1], z_floor, top - 0.30, ang=ang)
        beam(geo, a, b, COL_TOP if craft else top - 0.30, top, t=0.30 if craft else 0.26)
        if rail:
            for i in range(k):
                railing(geo, pts[i], pts[i + 1], z_floor, inset=0.32)
    g = np.array(poly.exterior.coords)[:-1]
    zg = float(np.min(plan.ground_z(g[:, 0], g[:, 1])))
    geo.extrude('stone_veneer', g, min(zg, z_floor - 0.5) - 0.3, z_floor, mat_top='bluestone', cap_bottom=False)
    return seen


def front_columns():
    """The wraparound porch's columns on its street sides (p01 through the fitted camera): west run, SW corner, the
    bend left of the entry, the two entry columns, and their mirror images about the entry's axis."""
    M, t, n, half, eave = entry_frame()
    c = M[0] - M[1]
    mir = lambda q: (q[1] + c, q[0] - c)                              # noqa: E731  (reflection in the entry's axis)
    xw, ys = COL_X_W, COL_Y_S
    west = [(xw, y) for y in np.linspace(COL_Y_N, ys, 4)[:3]]       # p01: 3 + the corner, evenly spaced
    sw, bl = (xw, ys), (-18.67, ys)                                  # bl: p01 / hero bearings onto the south line
    el, er = tuple(M - t * 1.25 + n * 0.6), tuple(M + t * 1.25 + n * 0.6)
    return west + [sw, bl, el, er, mir(bl), mir(sw)]


def front_porch(geo, eaves):
    M, t, n, half, eave = entry_frame()
    cols = front_columns()
    zf = PORCH_FLOOR
    top = COL_TOP + BEAM_H
    for i, q in enumerate(cols):
        a, b = cols[max(i - 1, 0)], cols[min(i + 1, len(cols) - 1)]
        ang = float(np.arctan2(b[1] - a[1], b[0] - a[0])) if i not in (3, 4, 7, 8) else 0.0
        column_craft(geo, q[0], q[1], zf, COL_TOP, ang, ground=plan.ground_z(q[0], q[1]))
    beam(geo, cols[0], (cols[0][0] + 1.9, cols[0][1]), COL_TOP, top, t=0.30)       # return to the wall at the north end
    for i in range(len(cols) - 1):
        a, b = cols[i], cols[i + 1]
        beam(geo, a, b, COL_TOP, top, t=0.30)
        if i != 5:                                                  # no railing across the steps
            railing(geo, a, b, zf, inset=0.32)
    # entry: box beam under the pediment, 4 risers down to the front walk, a short cream post at each side of the foot
    el, er = np.array(cols[5]), np.array(cols[6])
    beam(geo, el, er, COL_TOP, top + 0.06, t=0.34)
    t3, n3 = np.array([t[0], t[1], 0.0]), np.array([n[0], n[1], 0.0])
    rise = (zf - plan.FRONT_WALK) / 4
    edge = M + n * 0.42                                              # the porch floor's edge under the gable
    hw = 1.25 - 0.30
    for k in range(1, 4):
        o = np.array([edge[0], edge[1], 0.0]) - n3 * (0.32 * k)
        geo.obox('bluestone', o, t3, n3, (0, 0, 1), (-hw - 0.15, 0.0, plan.FRONT_WALK - 0.3), (hw + 0.15, 0.34, zf - rise * k))
    for sgn in (-1, 1):
        q = edge + t * sgn * (hw + 0.45) - n * 1.05
        geo.obox(TRIM, (q[0], q[1], 0.0), t3, n3, (0, 0, 1), (-0.17, -0.17, plan.FRONT_WALK - 0.2), (0.17, 0.17, zf + 0.30))
        geo.obox(TRIM, (q[0], q[1], 0.0), t3, n3, (0, 0, 1), (-0.21, -0.21, zf + 0.30), (0.21, 0.21, zf + 0.38))


def gable_trim(geo, planes):
    """Louvred vents, king posts and knee braces on the street gables (front gable FG, west gable WG, the garage's)."""
    P = {p['id']: np.array(p['poly']) for p in ROOF['planes']}
    up = np.array([0, 0, 1.0])

    def face(apex, foot_l, foot_r, inset, vent_w, vent_h, drop, brace=0.7):
        """apex / feet = the rake's roof points; the wall face lies `inset` behind the rake."""
        a, l, r = (np.asarray(v, float) for v in (apex, foot_l, foot_r))
        rr = (r - l) * [1, 1, 0]
        rr = rr / np.linalg.norm(rr)
        n = np.array([rr[1], -rr[0], 0.0])                           # out of the wall
        mid = np.array([(l[0] + r[0]) / 2, (l[1] + r[1]) / 2, 0.0]) - n * (inset - 0.02)
        ze = (l[2] + r[2]) / 2
        gable_vent(geo, mid + up * (ze + drop), rr, n, vent_w, vent_h)
        half = np.linalg.norm((r - l)[:2]) / 2 - 0.62
        for sgn in (-1, 1):
            knee_brace(geo, mid + rr * sgn * half + up * (ze - brace - 0.30), n, rr * sgn, size=brace)
        knee_brace(geo, mid + up * (a[2] - brace - 0.42), n, rr, size=brace)

    fg = P['fg_nw'], P['fg_se']
    face(fg[0][4], fg[0][0], fg[1][3], OVERHANG[2], 2.3, 0.75, 0.18)
    wg = P['wg_n'], P['wg_s']
    face(wg[0][3], wg[1][3], wg[0][0], OVERHANG[2], 1.3, 0.5, 0.30, brace=0.6)
    gg = garage_gable()
    face(gg['apex'], gg['foot_w'], gg['foot_e'], OVERHANG[1], 2.2, 0.6, 0.10, brace=0.5)


# openings: (kind, storey, plan point on the wall, sill z, width, height, options).  Front: p01 through the fitted
# camera onto the wall planes; rear: p21 / p28.  Sills hidden by railings are assumed 0.55 m above the floor.
F0 = FLOOR
OPENINGS = [
    # ---- street side -------------------------------------------------------------------------------------------
    ('win', 'g', (-18.90, -13.71), F0 + 0.55, 2.40, 1.80, dict(units=3)),              # W2 behind the left front run
    ('win', 'g', (-21.26, -13.22), F0 + 0.55, 0.70, 1.80, {}),                          # W1 on the bay's return
    ('door', 'g', (-16.29, -16.40), F0 - 0.02, 1.02, 2.10, dict(kind='wood')),          # the espresso front door
    ('win', 'g', (-16.87, -15.84), F0 + 0.10, 0.30, 1.90, dict(divided=False, sill=False, casing=0.07)),
    ('win', 'g', (-15.71, -16.96), F0 + 0.10, 0.30, 1.90, dict(divided=False, sill=False, casing=0.07)),
    ('win', 'g', (-13.23, -19.00), F0 + 0.55, 2.30, 1.80, dict(units=3)),               # W3 right of the entry
    ('door', 'g', (-13.23, -20.85), F0 - 0.02, 0.85, 2.10, dict(kind='glass', lights=0)),   # W4
    ('win', 'u', (-19.26, -13.71), 4.45, 2.50, 1.60, dict(units=3)),                    # triple window, upper left
    ('win', 'u', (-16.21, -16.48), 4.50, 1.85, 1.55, dict(units=2)),                    # twin window in the front gable
    ('win', 'u', (-21.57, -11.25), 4.65, 0.80, 1.50, {}),                               # west gable
    ('win', 'g', (-26.53, -3.45), 1.50, 1.95, 1.50, dict(units=2)),                     # garage south gable
    ('garage', 'g', (-30.45, 5.60), None, 2.60, 2.30, {}),                              # 3 garage doors on the motor
    ('garage', 'g', (-30.45, 2.40), None, 2.60, 2.30, {}),                              # court (assumed sizes: no
    ('garage', 'g', (-30.45, -0.80), None, 2.60, 2.30, {}),                             # photograph shows them)
    # ---- pool side ---------------------------------------------------------------------------------------------
    ('door', 'u', (BG_X_WALL, -1.85), Z2 + 0.12, 4.30, 2.50, dict(kind='glass', leaves=4)),   # balcony doors
    ('door', 'g', (REAR_X_GROUND, -3.06), PATIO_FLOOR + 0.05, 1.00, 2.40, dict(kind='glass')),      # BG patio door
    ('win', 'g', (REAR_X_GROUND, -0.87), 0.90, 2.50, 1.75, dict(units=3)),              # BG patio window
    ('door', 'g', (REAR_X_GROUND, 2.75), PATIO_FLOOR + 0.05, 3.20, 2.40, dict(kind='glass', leaves=4)),   # NC doors
    ('win', 'u', (BG_X_WALL, 4.80), 4.45, 1.00, 1.65, {}),                              # NC east, upper
    ('win', 'u', (-13.60, NC_Y_N), 4.40, 2.40, 1.45, dict(units=3)),                    # NC north, upper
    ('win', 'u', (-9.39, -9.03), 4.90, 2.40, 1.45, dict(units=3)),                      # court, the diagonal wall
    ('win', 'u', (-10.79, -6.55), 4.70, 0.90, 1.35, {}),                                # court, CC east wall
    ('door', 'g', (-9.61, -10.94), PATIO_FLOOR + 0.05, 1.70, 2.40, dict(kind='glass', leaves=2)),   # French doors
    ('win', 'g', (-6.40, PB_ROOM[3]), 0.80, 1.80, 2.00, dict(units=2)),                 # PB patio back wall
    ('win', 'g', (-8.55, PB_ROOM[3]), 0.80, 0.70, 2.00, {}),
    ('door', 'g', (-1.45, PB_ROOM[3]), PATIO_FLOOR + 0.05, 0.92, 2.40, dict(kind='glass')),
    ('door', 'g', (PB_ROOM[2], -17.15), 0.25, 0.92, 2.25, dict(kind='solid')),          # PB east wall
]


def build():
    planes = _planes()
    geo = Geo()
    entry_gable(geo, planes)
    roof_planes(geo, [p['rp'] for p in planes if p['src']['id'] != 'swp'])
    fp = footprints(planes)
    walls(geo, fp, planes)
    eaves = ROOF['eaves']
    rear(geo, fp, planes, eaves)
    gable_trim(geo, planes)
    closed = fp['G']
    front_porch(geo, eaves)
    explicit = box(-25.0, -24.6, -14.9, -6.3)
    for blk, zf, craft in (('porch_1st', PORCH_FLOOR, True),):
        f = _footprint(planes, {blk}, 1, inset=PORCH_INSET).difference(closed.buffer(0.02))
        for g in _rings(f):
            porch_auto(geo, g, closed, zf, eaves[blk], craft=craft, rail=craft, skip=explicit if craft else None)
    return [Part('house', geo, group='house')]
