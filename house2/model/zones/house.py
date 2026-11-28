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
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from model.kit import Geo, Part
from model.massing_kit import RoofPlane, roof_planes, wall, wall_top
from model import plan

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOF = json.load(open(os.path.join(HERE, 'survey', 'roof_3d.json')))

OVERHANG = {1: 0.50, 2: 0.60}            # eave line -> wall face, plan metres
UNDER = 0.85                             # a roof hidden under an upper eave runs on this far uphill (into the wall)
Z_GROW_MAX = 5.9                         # a one-storey roof grown on under the upper eaves stops below them
Z_BASE = -2.5                            # walls start below every ground level; the terrain covers them
Z2 = 3.45                                # upper floor level: the upper walls start here, the ground walls stop under it
SLAB_T = 0.25
FLOOR = plan.FLOOR                       # main floor above the pool deck
# wraparound porch floor: round 3 measured it 0.14 m under plan.FRONT_PORCH_FLOOR (0.42) through the level p01 camera --
# the four step nosings (v 1222 / 1237 / 1252 / 1265, walk 1280) fit a floor at 0.21-0.25 over the walk at -0.25..-0.31,
# the front run's bottom rail ends at z 0.31 (a 4 cm gap above the floor), and hero's 4 risers read ~0.14 m each:
# 0.28 (4 risers of ~0.14 over the walk at -0.27); the front door's sill 0.35 (p01 ray on the door wall)
PORCH_FLOOR = 0.28
PATIO_FLOOR = plan.REAR_PATIO_FLOOR      # covered rear patios (BG, the NC recess, PB)
WALL = 'siding_shingle'
TRIM = 'trim_cream'
FRAME = 'frame_bronze'
MATERIALS = {
    'trim_cream': dict(color=(0.84, 0.80, 0.70), roughness=0.6),            # cream casings, fascia, columns, railings
    'frame_bronze': dict(color=(0.030, 0.026, 0.022), roughness=0.5, metallic=0.3),
    'door_espresso': dict(color=(0.035, 0.022, 0.016), roughness=0.5),
    'vent_louvre': dict(color=(0.22, 0.20, 0.19), roughness=0.8),          # dark brown louvres (hero FG vent ~55/53/56)
    'trim_taupe': dict(color=(0.50, 0.44, 0.33), roughness=0.6),            # porch column capitals (p01: ~0.6 x the shaft)
}
TAUPE = 'trim_taupe'
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
# round 3: p01 is keystone-corrected (a LEVEL camera with a shifted principal point fits its 14 roof pairs at 5.9 px, the
# tilted pinhole at 12.8 px).  Through it the four west-run shafts fall on one line x -23.05 at EVEN 3.0 m bays
# (y -15.4 / -12.4 / -9.4 / -6.4; the old 2.6 m bays needed a slanted line), the corner on the front line y -15.42, the
# capital tops at z 3.06-3.09 (hero, at the entry: the beam top level with the entry gable's rake ends)
COL_X_W, COL_Y_S, COL_Y_N = -23.05, -15.42, -6.42
COL_BAY_W = 3.0                          # west-run bays
COL_X_MIRROR = -23.0                     # the south leg's column line is the mirror of the old west line (no photograph)
COL_TOP = 3.06                           # underside of the porch box beam = top of the column capitals
BEAM_H = 0.34                            # beam face 0.35 m deep (hero: 75 px at 213 px/m)
PIER_H = 0.83                            # stone pier over the porch floor (p01 front run: stone top z 1.11, floor 0.28)
PIER_BAND = 0.08                         # a cream band flush with the stone on top of it (p01: 1.11-1.19; hero 20 px)
PIER_CAP = 0.055                         # then the cream cap slab 0.72 wide; the shaft stands on it (no plinth: hero)
PORCH_INSET = 1.0                        # eave -> porch floor edge / column line of the wraparound porch


def _upper_outline():
    """Plan outline of the two-storey roofs (their eave lines), where hidden one-storey roof may run on."""
    polys = [Polygon(np.array(p['poly'])[:, :2]).buffer(0.005, join_style=2) for p in ROOF['planes'] if p['storey'] == 2]
    return unary_union(polys)


def _grow_under(P, edges, plane, upper, walls):
    """A one-storey roof's 'under_upper_eave' edges are where the aerial loses it under a two-storey eave -- displaced
    by up to ~2 m from the true eave by the aerial's parallax (the upper roof is 3-4 m higher).  Sweep those edges
    up-slope to the upper walls (0.25 m into them) and grow the plane under the upper roof, so no strip is left open
    between the visible roof and the walls (round 3: holes beside the west gable and under the north wing's eave)."""
    a, b, c = plane
    pp = Polygon(P[:, :2])
    up = np.array([a, b], float)
    nu = np.hypot(*up)
    parts = [pp.buffer(UNDER, join_style=2).intersection(upper.buffer(-0.02))]
    if nu > 1e-6:
        up = up / nu
        n = len(P)
        for k, kind in enumerate(edges):
            if not kind.startswith('under_upper'):
                continue
            e0, e1 = P[k, :2], P[(k + 1) % n, :2]
            parts.append(Polygon([e0, e1, e1 + up * 4.5, e0 + up * 4.5]).buffer(0))
            d = e1 - e0                                  # and straight out of the edge (edges along the slope)
            if np.hypot(*d) > 0.05:
                nn = np.array([d[1], -d[0]]) / np.hypot(*d)
                if pp.contains(Point(*((e0 + e1) / 2 + nn * 0.05))):
                    nn = -nn
                if nn @ up > -0.2:
                    parts.append(Polygon([e0, e1, e1 + nn * 4.5, e0 + nn * 4.5]).buffer(0))
    grow = unary_union(parts).intersection(upper.buffer(2.2, join_style=2)).difference(walls.buffer(-0.25, join_style=2))
    # stay on this plane's side of its hips / valleys (their lines run on up to the walls): no spill over a neighbour
    ctr = np.array(pp.representative_point().coords[0])
    n = len(P)
    for k, kind in enumerate(edges):
        if kind not in ('hip', 'valley', 'ridge'):
            continue
        e0, e1 = P[k, :2], P[(k + 1) % n, :2]
        d = e1 - e0
        if np.hypot(*d) < 0.05:
            continue
        d = d / np.hypot(*d)
        nn = np.array([-d[1], d[0]])
        if (ctr - e0) @ nn < 0:
            nn = -nn
        hp = Polygon([e0 - d * 30, e1 + d * 30, e1 + d * 30 + nn * 30, e0 - d * 30 + nn * 30])
        grow = grow.intersection(hp.buffer(0.02))
    if nu > 1e-6:                                    # and below the two-storey eaves (6.4): never through them
        zc = Z_GROW_MAX - c
        o = up * zc / nu
        side = np.array([-up[1], up[0]])
        grow = grow.intersection(Polygon([o - side * 60, o + side * 60, o + side * 60 - up * 60, o - side * 60 - up * 60]))
    g = pp.union(grow).buffer(0.01, join_style=2).buffer(-0.01, join_style=2)
    if g.geom_type != 'Polygon':
        g = max(g.geoms, key=lambda q: q.area if q.intersects(pp) else 0.0)
    return g.simplify(0.01)


def _planes():
    out = []
    upper = _upper_outline()
    walls2 = upper.buffer(-OVERHANG[2], join_style=2)
    for p in ROOF['planes']:
        P = np.array(p['poly'], float)
        a, b, c = p['plane']
        Q = P
        if p['storey'] == 1 and any(k.startswith('under_upper') for k in p['edges']):
            # grow the plane under the upper roof (hidden there), so it runs into the upper walls
            g = _grow_under(P, p['edges'], p['plane'], upper, walls2)
            xy = np.array(g.exterior.coords)[:-1]
            Q = np.c_[xy, a * xy[:, 0] + b * xy[:, 1] + c]
        if p['id'] in ('ncp_n', 'ncp_e'):
            # roof_3d.json runs them to the upper wall's face; here 0.12 m on into the wall
            xy = P[:, :2].copy()
            k, w = (1, NC_Y_N) if p['id'] == 'ncp_n' else (0, BG_X_WALL)
            xy[np.abs(xy[:, k] - w) < 0.08, k] = w - 0.12
            Q = np.c_[xy, a * xy[:, 0] + b * xy[:, 1] + c]
        elif p['id'] in ('gb_w', 'gb_e'):
            Q = garage_gable()[p['id']]
        elif p['id'] == 'g_s':
            Q = P[:3]                    # no notch: the (lower) gable runs into this plane and is buried where it is lower
        mat = 'roof_flat' if p['flat'] else 'roof_shingle'
        out.append(dict(rp=RoofPlane(p['id'], Q, mat=mat, thickness=0.22, storey=p['storey'], fascia=TRIM), src=p))
    return out


def garage_gable():
    """The garage's south gable (roof_3d.json: symmetric, its valleys on g_s).  Both planes are run on north at full
    width to the valley apex's y, buried under g_s (no open valley seam); + apex / rake feet for the trim."""
    P = {p['id']: np.array(p['poly']) for p in ROOF['planes'] if p['id'] in ('gb_w', 'gb_e')}
    apex, fw, fe = P['gb_w'][1], P['gb_w'][2], P['gb_e'][2]          # ridge front, rake feet
    yb = P['gb_w'][0][1]
    gw, ge = P['gb_w'].copy(), P['gb_e'].copy()
    gw[3, 1] = yb
    ge[1, 1] = yb
    return {'gb_w': gw, 'gb_e': ge, 'apex': apex, 'foot_w': fw, 'foot_e': fe}


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


def swp_pieces(planes):
    """The diagonal porch roof SWP round the entry gable: its plane (grown under the front gable's eave to the walls)
    minus the plan triangle where the gable stands above it -- the gable's valleys run from its eave corners up to the
    ridge, dep = (half - |u|) tan(pitch) / swp's slope along n.  (Round 3: SWP had been left out whole, which opened a
    hole beside the gable down to the ground-floor wall tops, seen from the drone.)"""
    sp = next(p for p in planes if p['src']['id'] == 'swp')['rp']
    M, t, n, half, eave = entry_frame()
    a, b, c = sp.abc
    slope = a * n[0] + b * n[1]
    k = np.tan(np.radians(ENTRY_PITCH)) / max(slope, 0.05)
    w = half + 0.03
    tri = Polygon([M + t * u + n * d for u, d in ((-w, -1.5), (w, -1.5), (w, 0.0), (0.0, k * w), (-w, 0.0))])
    rest = Polygon(sp.xy).buffer(0).difference(tri)
    rest = rest.buffer(-0.06, join_style=2).buffer(0.06, join_style=2)   # no slivers along the gable's side eaves
    out = []
    for i, g in enumerate(_rings(rest, 0.05)):
        xy = np.array(g.exterior.coords)[:-1]
        out.append(RoofPlane('swp_%d' % i, np.c_[xy, a * xy[:, 0] + b * xy[:, 1] + c], mat=sp.mat, thickness=sp.t,
                             storey=1, fascia=TRIM))
    return out


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
    # pediment over the two entry columns (hero, seen frontally): a shingled field from the beam top up to the rakes'
    # underside, a king-post corbel from the apex down to the beam, a corbel on each end of the beam (over the column,
    # from the rake down past the beam onto the capital) and a bracket under each rake end
    tn = np.tan(np.radians(ENTRY_PITCH))
    t3, n3 = np.array([t[0], t[1], 0.0]), np.array([n[0], n[1], 0.0])
    c = M + n * 0.55
    us = lambda u: eave - 0.18 + (half - abs(u)) * tn                 # noqa: E731  rake underside at lateral u
    zbt = COL_TOP + BEAM_H
    x1 = half - (zbt - us(half)) / tn
    za = us(0.0) + 0.01
    tri = [E(c - t * x1, zbt), E(c + t * x1, zbt), E(c, za)]
    geo.poly(WALL, tri[::-1])
    geo.poly(WALL, tri)
    corbel(geo, E(c, za - 0.01), -n3, t3, L=za - 0.01 - zbt, D=0.20, w=0.18)
    for sgn in (-1, 1):
        q = M + t * sgn * 1.25 + n * (0.6 - 0.19)                     # hero: 0.16 wide, down past the capital by 0.17
        corbel(geo, E(q, us(1.25) + 0.01), -n3, t3, L=us(1.25) + 0.01 - (COL_TOP - 0.37), D=0.24, w=0.17)
        f = M + t * sgn * (1.25 + 0.10) + n * 0.6
        knee_brace(geo, E(f, COL_TOP - 0.25), t3 * sgn, n3, size=0.40, t=0.09)


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


def column_craft(geo, x, y, z0, z1, ang=0.0, pier=0.62, pier_h=PIER_H, s0=0.45, s1=0.36, ground=None):
    """Tapered square Craftsman column (cream) on a ledgestone pier (the wraparound porch; hero / p01, round 3): the stone
    pier with a flush cream band and a cream cap slab 0.72 wide on top, the shaft standing straight on the slab (no base
    plinth) and tapering s0 -> s1 (hero, entry column: 90 -> 72 px over a 125 px pier, a 144 px slab), a taupe capital
    (neck, block, cap plate: ~1.3 x the shaft top, 0.20 m tall) under the beam."""
    ex, ey = np.array([np.cos(ang), np.sin(ang), 0.0]), np.array([-np.sin(ang), np.cos(ang), 0.0])
    o = np.array([x, y, 0.0])
    zb = z0 - 1.0 if ground is None else min(ground, z0) - 0.3
    sq = lambda half, za, zz, mat, faces='xXyY': geo.obox(mat, o, ex, ey, (0, 0, 1), (-half, -half, za),  # noqa: E731
                                                         (half, half, zz), faces)
    h = pier / 2
    zp = z0 + pier_h
    sq(h, zb, zp, 'stone_veneer')
    sq(h + 0.005, zp, zp + PIER_BAND, TRIM, 'xXyYz')                     # flush cream band
    sq(h + 0.05, zp + PIER_BAND, zp + PIER_BAND + PIER_CAP, TRIM, 'xXyYzZ')   # cap slab, 5 cm proud
    za, zt = zp + PIER_BAND + PIER_CAP, z1 - 0.20
    c0 = [o + ex * sx * s0 / 2 + ey * sy * s0 / 2 + (0, 0, za) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    c1 = [o + ex * sx * s1 / 2 + ey * sy * s1 / 2 + (0, 0, zt) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4):
        j = (i + 1) % 4
        geo.poly(TRIM, [c0[i], c0[j], c1[j], c1[i]])
    sq(s1 / 2 + 0.012, zt, zt + 0.04, TAUPE, 'xXyYz')                     # capital: neck, block, cap plate
    sq(s1 / 2 + 0.035, zt + 0.04, zt + 0.15, TAUPE, 'xXyYz')
    sq(s1 / 2 + 0.06, zt + 0.15, z1, TAUPE, 'xXyYz')


def corbel(geo, top, out, along, L=0.86, D=0.22, w=0.18, mat=TRIM):
    """Craftsman corbel / bracket block: `top` = the middle of its top edge on the face it hangs on, `out` = unit
    horizontal out of that face, `along` = across its width.  Side profile: D proud at the top, stepping in to 0.5 D
    over its lower part, L long."""
    top, out, along = (np.asarray(v, float) for v in (top, out, along))
    side = np.cross(along, (0, 0, 1.0))
    sg = 1.0 if side @ out > 0 else -1.0
    prof = [(0, 0), (D, 0), (D, -0.10), (0.78 * D, -0.16), (0.78 * D, -0.45 * L), (0.5 * D, -0.62 * L), (0.5 * D, -L),
            (0, -L)]
    geo.prism(mat, [(sg * a, b) for a, b in prof], top - along * w / 2, top + along * w / 2, up=(0, 0, 1.0))


def railing(geo, a, b, z0, h=0.80, gap=0.122, mat=TRIM, inset=0.0, bw=0.048, bot=(0.06, 0.14)):
    """Porch railing between plan points a and b (floor at z0): a flat cap board on the top rail, a bottom rail held off
    the floor (bot = its underside / top over the floor), plain square balusters bw wide at `gap` centres."""
    r, n, L = _frame(a, b)
    L -= 2 * inset
    if L < 0.25:
        return
    o = np.array([a[0], a[1], 0.0]) + r * inset
    _lbox(geo, mat, o, r, n, (0, -0.06, z0 + h - 0.035), (L, 0.06, z0 + h), 'yYzZ')            # cap board
    _lbox(geo, mat, o, r, n, (0, -0.04, z0 + h - 0.11), (L, 0.04, z0 + h - 0.035), 'yYz')      # top rail
    _lbox(geo, mat, o, r, n, (0, -0.04, z0 + bot[0]), (L, 0.04, z0 + bot[1]), 'yYzZ')          # bottom rail
    k = max(1, int(round(L / gap)))
    hb = bw / 2
    for i in range(k):
        s = (i + 0.5) * L / k
        _lbox(geo, mat, o, r, n, (s - hb, -hb, z0 + bot[1]), (s + hb, hb, z0 + h - 0.11), 'xXyY')


# the wraparound porch's railing (p01 through the level camera on the front run's plane, round 3): cap board top level
# with the piers' cream band (z 1.20 = 0.92 over the floor), square balusters ~0.07 at 0.165-0.175 m centres (12 in the
# front run's 2.1 m between piers), the bottom rail 0.04-0.17 over the floor
FRONT_RAIL = dict(h=0.92, gap=0.168, bw=0.068, bot=(0.04, 0.17))


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
    if kind == 'unit':
        return door_unit(geo, o, r, n, w, h, casing)
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


def door_unit(geo, o, r, n, w, h, c, leaf=1.02, side=0.22, side_at=0.70):
    """The front door unit in a hole w x h (p01 / hero): an espresso frame filling the hole, the leaf recessed in its
    middle with three tall top lights (0.29-0.85 m under the head), a sidelight glass at +-side_at (0.25 m over the sill
    to 0.29 m under the head), a flat espresso casing c wide round the hole (no cream casing: hero)."""
    E = 'door_espresso'
    _bx(geo, E, o, r, n, -c, 0, 0, h + c, -0.02, 0.025)
    _bx(geo, E, o, r, n, w, w + c, 0, h + c, -0.02, 0.025)
    _bx(geo, E, o, r, n, -c, w + c, h, h + c, -0.02, 0.025)
    m = w / 2
    x0, x1 = m - leaf / 2, m + leaf / 2
    za, zb = 0.25, h - 0.29                                           # sidelight glass
    for sg in (-1, 1):
        g0, g1 = sorted((m + sg * (side_at - side / 2), m + sg * (side_at + side / 2)))
        geo.poly('glass', [o + r * g0 - n * 0.05, o + r * g1 - n * 0.05, o + r * g1 - n * 0.05 + (0, 0, h),
                           o + r * g0 - n * 0.05 + (0, 0, h)])
        f0, f1 = (0.0, g0) if sg < 0 else (g1, w)                      # jamb outside the sidelight
        m0, m1 = (g1, x0) if sg < 0 else (x1, g0)                      # mullion between it and the leaf
        for a_, b_ in ((f0, f1), (m0, m1)):
            _bx(geo, E, o, r, n, a_, b_, 0, h, -0.06, -0.01, 'xXY')
        _bx(geo, E, o, r, n, g0, g1, 0, za, -0.06, -0.01, 'Y')
        _bx(geo, E, o, r, n, g0, g1, zb, h, -0.06, -0.01, 'Y')
    _bx(geo, E, o, r, n, x0, x1, h - 0.10, h, -0.06, -0.01, 'Y')         # head over the leaf
    lz0, lz1 = h - 0.85, h - 0.29                                    # the leaf: a slab with three tall lights
    _bx(geo, E, o, r, n, x0 + 0.005, x1 - 0.005, 0, lz0, -0.10, -0.04, 'xXY')
    _bx(geo, E, o, r, n, x0 + 0.005, x1 - 0.005, lz1, h - 0.10, -0.10, -0.04, 'xXY')
    _bx(geo, E, o, r, n, x0 + 0.005, x0 + 0.17, lz0, lz1, -0.10, -0.04, 'xXY')
    _bx(geo, E, o, r, n, x1 - 0.17, x1 - 0.005, lz0, lz1, -0.10, -0.04, 'xXY')
    geo.poly('glass', [o + r * x0 - n * 0.09 + (0, 0, lz0), o + r * x1 - n * 0.09 + (0, 0, lz0),
                       o + r * x1 - n * 0.09 + (0, 0, lz1), o + r * x0 - n * 0.09 + (0, 0, lz1)])
    lw = (leaf - 0.34) / 3
    for k in (1, 2):                                                 # two muntins between the three lights
        xm = x0 + 0.17 + lw * k
        _bx(geo, E, o, r, n, xm - 0.025, xm + 0.025, lz0, lz1, -0.10, -0.06, 'xXY')
    _bx(geo, E, o, r, n, x0 + 0.17, x1 - 0.17, lz0 - 0.05, lz0, -0.10, -0.03, 'YzZ')   # a shelf under the lights


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


def curved_bracket(geo, top, out, along, L=0.60, H=0.95, t=0.10, w=0.13, d=0.16, mat=TRIM):
    """Heavy Craftsman gable bracket (p01, the west gable): a horizontal outrigger d deep from the wall out L under the
    rake (top = the middle of its top edge on the wall face) and a curved strut t thick, a quarter ellipse from the wall
    H under the outrigger's top up into the outrigger's outer part, bowed toward the corner."""
    top, out, along = (np.asarray(v, float) for v in (top, out, along))
    side = np.cross(along, (0, 0, 1.0))
    sg = 1.0 if side @ out > 0 else -1.0
    geo.prism(mat, [(sg * a, b) for a, b in [(0, 0), (L, 0), (L, -d), (0, -d)]],
              top - along * w / 2, top + along * w / 2, up=(0, 0, 1.0))
    a0, b0 = 0.82 * L, H - d * 0.5                                    # ellipse centred at (0.82 L, -H)
    th = np.linspace(0, np.pi / 2, 13)
    inner = [(0.82 * L - a0 * np.cos(q), -H + b0 * np.sin(q)) for q in th]
    outer = [(0.82 * L - (a0 + t) * np.cos(q), -H + (b0 + t) * np.sin(q)) for q in th][::-1]
    prof = [(max(x, -0.02), z) for x, z in inner + outer]
    geo.prism(mat, [(sg * a, b) for a, b in prof], top - along * w * 0.4, top + along * w * 0.4, up=(0, 0, 1.0))


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


def garage_sill():
    """One slab level for the three garage doors: just above the motor court's highest point in front of them."""
    pts = [op[2] for op in OPENINGS if op[0] == 'garage']
    return max(float(plan.ground_z(x - 0.6, y)) for x, y in pts) + 0.03


def garage_wainscot(geo, fp):
    """Stone wainscot with a cream water table round the garage's south gable bay, up to the window sill (p01)."""
    g = min(_rings(fp['G']), key=lambda q: q.bounds[0])              # the garage / north-wing ring
    x0, y0, x1, y1 = -28.6, g.bounds[1] - 0.1, -24.4, -2.6
    bay = g.intersection(box(x0, y0, x1, y1))
    if bay.is_empty:
        return
    sill = next(op[3] for op in OPENINGS if op[0] == 'win' and op[2] == GARAGE_WIN)
    ztop = sill - 0.07 - 0.07                                        # under the window's sill board
    cut = box(x0 - 1, y1 - 0.02, x1 + 1, y1 + 2)                     # open toward the house side: no back face proud
    for mat, d, za, zb in (('stone_veneer', 0.07, None, ztop), (TRIM, 0.10, ztop, ztop + 0.07)):
        b = bay.buffer(d, join_style=2).difference(cut)
        ring = np.array(b.exterior.coords)[:-1]
        zg = float(np.min(plan.ground_z(ring[:, 0], ring[:, 1]))) - 0.3
        geo.extrude(mat, ring, zg if za is None else za, zb, cap_bottom=za is not None)


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
                zs = garage_sill()
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
    bend left of the entry, the two entry columns, and their mirror images about the entry's axis; then the south and
    east legs (aerial: the porch roof runs on round the south wing to the patio wing's south wall; column line 1 m
    inside the eave like the front, even bays -- no photograph shows these two legs)."""
    M, t, n, half, eave = entry_frame()
    c = M[0] - M[1]
    mir = lambda q: (q[1] + c, q[0] - c)                              # noqa: E731  (reflection in the entry's axis)
    xw, ys = COL_X_W, COL_Y_S
    west = [(xw, ys + COL_BAY_W * k) for k in (3, 2, 1)]            # p01: 3 + the corner, 3.0 m bays
    sw, bl = (xw, ys), (-18.67, ys)                                  # bl: p01 / hero bearings onto the south line
    el, er = tuple(M - t * 1.25 + n * 0.6), tuple(M + t * 1.25 + n * 0.6)
    se0 = mir((COL_X_MIRROR, ys))
    south = [(x, se0[1]) for x in np.linspace(se0[0], COL_X_E, 4)[1:]]
    east = [(COL_X_E, (se0[1] + PB_ROOM[1]) / 2)]
    return west + [sw, bl, el, er, mir(bl), se0] + south + east


COL_X_E = -6.60                          # east leg's column line (eave -5.6)
PORCH_END_N = (-19.2, COL_Y_N)           # the west leg's north end: the beam returns to the west wall (x -19.16) here
PORCH_END_E = (COL_X_E, PB_ROOM[1])      # the east leg ends on the patio wing's south wall
FLOOR_OUT = 0.10                         # porch floor edge outside the column line
SLAB_EDGE = 0.08                         # the bluestone floor slab's edge over the stone skirt
ENTRY_EDGE = 0.60 - FLOOR_OUT            # floor edge at the entry, metres inside the gable's outer eave line M


def porch_floor_plan(fp=None):
    """Plan of the wraparound porch floor: everything between the column line (+ FLOOR_OUT) and the ground-storey
    walls, from the west leg's north end round the entry, the south wing and the east leg to the patio wing."""
    cols = front_columns()
    line = [PORCH_END_N] + cols + [PORCH_END_E]
    # close through the house (anchors inside the ground outline G): only the part outside the walls is floor
    inner = [(COL_X_E, -17.0), (-11.0, -17.0), (-14.5, -15.5), (-18.5, -12.0), (-18.5, COL_Y_N)]
    P = Polygon(line + inner).buffer(0)
    if P.geom_type != 'Polygon':
        P = max(P.geoms, key=lambda g: g.area)
    G = (fp or footprints(_planes()))['G']
    # the west leg's north end and the east end stay square: buffer, then cut back at both ends
    f = P.buffer(FLOOR_OUT, join_style=2).difference(G.buffer(-0.12, join_style=2))
    f = f.intersection(box(-30.0, -30.0, COL_X_E + FLOOR_OUT, COL_Y_N + FLOOR_OUT))
    parts = [g for g in _rings(f, 0.5)]
    return parts


def porch_floor(geo, fp):
    """The floor slab (bluestone, its dark edge ~8 cm, 4 cm proud) straight on the stone skirt, which runs down into the
    ground (plan.ground_z along its edge).  Hero / p01 (round 3): no cream fascia under the slab -- the railing's wide
    bottom rail, a dark bluestone edge, then the ledgestone."""
    zf = PORCH_FLOOR
    for g in porch_floor_plan(fp):
        ring = np.array(g.exterior.coords)[:-1]
        holes = [np.array(h.coords)[:-1] for h in g.interiors]
        zg = float(np.min(plan.ground_z(ring[:, 0], ring[:, 1])))
        geo.extrude('stone_veneer', ring, zg - 0.35, zf - SLAB_EDGE, holes=holes, cap_top=False, cap_bottom=False)
        gn = g.buffer(0.04, join_style=2)
        geo.extrude('bluestone', np.array(gn.exterior.coords)[:-1], zf - SLAB_EDGE, zf,
                    holes=[np.array(h.coords)[:-1] for h in gn.interiors])


def front_porch(geo, eaves):
    M, t, n, half, eave = entry_frame()
    cols = front_columns()
    zf = PORCH_FLOOR
    top = COL_TOP + BEAM_H
    corners = (3, 4, 7, 8, 11)
    for i, q in enumerate(cols):
        a, b = cols[max(i - 1, 0)], cols[min(i + 1, len(cols) - 1)]
        ang = float(np.arctan2(b[1] - a[1], b[0] - a[0])) if i not in corners else 0.0
        column_craft(geo, q[0], q[1], zf, COL_TOP, ang, ground=plan.ground_z(q[0], q[1]))
    line = [PORCH_END_N] + cols + [PORCH_END_E]                     # both ends return to a wall
    for i in range(len(line) - 1):
        a, b = line[i], line[i + 1]
        beam(geo, a, b, COL_TOP, top, t=0.30)
        if i != 6 and 0 < i < len(line) - 2:                        # no railing across the steps / at the wall returns
            railing(geo, a, b, zf, inset=0.31, **FRONT_RAIL)
    railing(geo, cols[-1], PORCH_END_E, zf, inset=0.31, **FRONT_RAIL)   # east leg: railed up to the patio wing
    # entry: box beam under the pediment, 4 risers down to the front walk, a short cream post at each side of the foot
    el, er = np.array(cols[5]), np.array(cols[6])
    beam(geo, el, er, COL_TOP, top, t=0.34)
    t3, n3 = np.array([t[0], t[1], 0.0]), np.array([n[0], n[1], 0.0])
    edge = M + n * (ENTRY_EDGE - 0.04)                               # the porch floor's nosing under the gable
    zfoot = float(plan.ground_z(*(edge - n * 1.30)))                 # the walk at the bottom step (ground zone)
    rise = (zf - zfoot) / 4                                          # 4 equal risers from the walk as built
    hw = 1.25 - 0.30
    zw = min(plan.FRONT_WALK, zfoot) - 0.3
    for k in range(1, 4):
        o = np.array([edge[0], edge[1], 0.0]) - n3 * (0.32 * k)
        geo.obox('bluestone', o, t3, n3, (0, 0, 1), (-hw - 0.15, 0.0, zw), (hw + 0.15, 0.34, zf - rise * k))
    # the step posts (hero): a square cream post, a flared cap ~0.5 m over the porch floor and a sloped wedge on it
    # rising toward the porch (the foot of a stair-cheek cap)
    for sgn in (-1, 1):
        q = edge + t * sgn * (hw + 0.45) - n * 1.05
        o = np.array([q[0], q[1], 0.0])
        zc = zf + 0.59                                                 # p01 ray: cap 0.87-0.95, wedge top 1.15
        geo.obox(TRIM, o, t3, n3, (0, 0, 1), (-0.17, -0.17, zw + 0.1), (0.17, 0.17, zc), 'xXyY')
        geo.obox(TRIM, o, t3, n3, (0, 0, 1), (-0.21, -0.21, zc), (0.21, 0.21, zc + 0.08))
        geo.prism(TRIM, [(-0.10, 0.0), (0.12, 0.0), (0.12, 0.08), (0.02, 0.19), (-0.10, 0.12)],
                  o - t3 * 0.09 + (0, 0, zc + 0.08), o + t3 * 0.09 + (0, 0, zc + 0.08), up=(0, 0, 1.0))


def porch_soffit(geo, fp, planes):
    """Under the wraparound porch roof (p01 / hero): a flat cream ceiling at the beam top inside the column line, the
    beam's face carried up to the sloped soffit outside it (the frieze), and exposed rafter tails under the soffit
    between the beam and the eave (curved ends under the gutter, ~0.5 m apart)."""
    top = COL_TOP + BEAM_H
    for g in porch_floor_plan(fp):
        gc = g.buffer(0.05, join_style=2)
        geo.extrude('soffit_white', np.array(gc.exterior.coords)[:-1], top - 0.03, top,
                    holes=[np.array(h.coords)[:-1] for h in gc.interiors], cap_top=False)
    p1 = [p['rp'] for p in planes if p['src']['storey'] == 1]
    cols = front_columns()
    line = [PORCH_END_N] + cols + [PORCH_END_E]
    for i in range(len(line) - 1):
        if i == 6:                                                    # the entry: under the pediment
            continue
        a, b = np.asarray(line[i], float), np.asarray(line[i + 1], float)
        r, n, L = _frame(a, b)
        o = n[:2] * 0.151
        a2, b2 = a + o - r[:2] * 0.15, b + o + r[:2] * 0.15
        prof = wall_top(p1, a2, b2, top - 0.01, default=top - 0.01)     # no roof over it: no frieze
        L2 = float(np.linalg.norm(b2 - a2))
        P3 = lambda s_, z_: np.array([a2[0], a2[1], 0.0]) + r * s_ + np.array([0, 0, z_])     # noqa: E731
        ring = [P3(0, top - 0.01), P3(L2, top - 0.01)] + [P3(s_, min(z_, top + 0.55)) for s_, z_ in reversed(prof)]
        geo.poly(TRIM, ring)
    # rafter tails along the porch eaves (not the diagonal entry leg: the pediment's beam is there)
    line_ls = LineString([tuple(q) for q in line])
    for p in planes:
        src = p['src']
        if src.get('block') != 'porch_1st' or src.get('id') in ('swp', 'entry_gable') or 'edges' not in src:
            continue
        rp = p['rp']
        P = np.array(src['poly'], float)
        dn = rp.downhill
        tn = np.tan(np.radians(rp.pitch))
        inside = Polygon(P[:, :2]).buffer(0.01)
        for k, kind in enumerate(src['edges']):
            if kind != 'eave':
                continue
            A, B = P[k, :2], P[(k + 1) % len(P), :2]
            L = float(np.linalg.norm(B - A))
            e = (B - A) / L
            m = max(1, int(L / 0.50))
            for j in range(m):
                s0 = 0.55 + (L - 1.10) * (j + 0.5) / m if L > 1.2 else L / 2
                if s0 < 0.55 or s0 > L - 0.55:
                    continue
                q = A + e * s0
                # inward run: to the beam's outer face (+0.25 into it), at most 1.6 m
                dist = line_ls.distance(Point(q))
                run = min(1.6, max(0.3, dist - 0.15 + 0.25))
                seg = LineString([tuple(q - dn * 0.02), tuple(q - dn * run)]).intersection(inside.buffer(-0.04))
                if seg.is_empty or seg.length < 0.25:
                    continue
                if seg.geom_type != 'LineString':
                    seg = min(seg.geoms, key=lambda g: g.distance(Point(q)))
                run = min(run, float(np.max(np.linalg.norm(np.array(seg.coords) - q, axis=1))))
                rafter_tail(geo, q, -dn, e, rp.z(*q) - rp.t, tn, run)


def rafter_tail(geo, q, inward, along, z_us, tn, run, w=0.055, d=0.13):
    """One exposed rafter tail under a sloped soffit: q = plan point on the eave line, inward = unit plan vector up the
    slope, z_us = soffit height at q, tn = slope; a shaped (rounded-off) lower end 3 cm inside the fascia."""
    q, inward, along = np.asarray(q, float), np.asarray(inward, float), np.asarray(along, float)
    inv3 = np.array([inward[0], inward[1], 0.0])
    side = np.cross(np.array([along[0], along[1], 0.0]), (0, 0, 1.0))
    sg = 1.0 if side @ inv3 > 0 else -1.0
    r0 = 0.03
    zt = lambda r: z_us + r * tn + 0.01                               # noqa: E731  top: just into the soffit
    prof = [(r0, zt(r0)), (r0, zt(r0) - 0.06), (r0 + 0.03, zt(r0 + 0.03) - d + 0.025), (r0 + 0.08, zt(r0 + 0.08) - d),
            (run, zt(run) - d), (run, zt(run))]
    a = np.array([q[0], q[1], 0.0]) - np.array([along[0], along[1], 0.0]) * w / 2
    b = a + np.array([along[0], along[1], 0.0]) * w
    geo.prism(TRIM, [(sg * r, z) for r, z in prof], a, b, up=(0, 0, 1.0))


def gable_trim(geo, planes):
    """Louvred vents, king posts and brackets on the street gables: the front gable FG (hero: a king-post corbel through
    the vent, a tall corbel on the wall under each rake end, a curved bracket under each eave end), the west gable WG
    (p01: two heavy curved brackets) and the garage gable (p01: a king-post block and a tall corbel under each rake end)."""
    P = {p['id']: np.array(p['poly']) for p in ROOF['planes']}
    up = np.array([0, 0, 1.0])

    def face(apex, foot_l, foot_r, inset, vent_w, vent_h, drop, brace=0.7, corbels=False, thick=0.22):
        """apex / feet = the rake's roof points; the wall face lies `inset` behind the rake."""
        a, l, r = (np.asarray(v, float) for v in (apex, foot_l, foot_r))
        rr = (r - l) * [1, 1, 0]
        rr = rr / np.linalg.norm(rr)
        n = np.array([rr[1], -rr[0], 0.0])                           # out of the wall
        mid = np.array([(l[0] + r[0]) / 2, (l[1] + r[1]) / 2, 0.0]) - n * (inset - 0.02)
        ze = (l[2] + r[2]) / 2
        hr = np.linalg.norm((r - l)[:2]) / 2
        tn = (a[2] - ze) / hr
        us = lambda u: ze + (hr - abs(u)) * tn - thick               # noqa: E731  rake underside at lateral u
        gable_vent(geo, mid + up * (ze + drop), rr, n, vent_w, vent_h)
        half = hr - inset - 0.02                                     # wall half-width
        if corbels == 'garage':
            # p01 (rays on the wall, round 3): a king-post block 0.20 wide from the apex down through the vent to its
            # base, and a tall corbel under each rake end 0.29 m inside the wall's end, its foot ~0.59 under the eave
            corbel(geo, mid + up * us(0.0), n, rr, L=us(0.0) - (ze + drop), D=0.14, w=0.20)
            for sgn in (-1, 1):
                u = half - 0.29
                corbel(geo, mid + rr * sgn * u + up * (us(u) + 0.01), n, rr, L=us(u) + 0.01 - (ze - 0.59), D=0.26,
                       w=0.21)
            return
        if corbels == 'curved':
            # p01 (round 3): two heavy curved brackets under the rakes near the wall's ends, an outrigger from the wall
            # out to the fascia right under the rake soffit and a curved strut ~0.9 m down the wall; no apex brace
            for sgn in (-1, 1):
                u = half - 0.18
                curved_bracket(geo, mid + rr * sgn * u + up * (us(u) + 0.01), n, rr, L=inset - 0.06, H=0.95)
            return
        if not corbels:
            for sgn in (-1, 1):
                knee_brace(geo, mid + rr * sgn * (hr - 0.62) + up * (ze - brace - 0.30), n, rr * sgn, size=brace)
            knee_brace(geo, mid + up * (a[2] - brace - 0.42), n, rr, size=brace)
            return
        corbel(geo, mid + up * us(0.0), n, rr, L=us(0.0) - (ze + drop), D=0.17, w=0.14)
        for sgn in (-1, 1):
            u = half - 0.28
            corbel(geo, mid + rr * sgn * u + up * (us(u) + 0.01), n, rr, L=0.94, D=0.22, w=0.19)
            knee_brace(geo, mid + rr * sgn * (half - 0.05) + up * (ze - 0.55), rr * sgn, n, size=0.45, t=0.10)

    fg = P['fg_nw'], P['fg_se']
    face(fg[0][4], fg[0][0], fg[1][3], OVERHANG[2], 2.3, 0.75, 0.18, corbels=True)
    wg = P['wg_n'], P['wg_s']
    face(wg[0][3], wg[0][0], wg[1][3], OVERHANG[2], 1.3, 0.5, 0.30, corbels='curved')   # feet N -> S: faces west
    gg = garage_gable()
    # garage gable vent (p01): frame base z ~3.57, 2.15 wide, its top under the king-post block at ~4.19
    face(gg['apex'], gg['foot_w'], gg['foot_e'], OVERHANG[1], 2.15, 0.62, 0.16, corbels='garage')


# openings: (kind, storey, plan point on the wall, sill z, width, height, options).  Front: p01 through the fitted
# camera onto the wall planes; rear: p21 / p28.  Sills hidden by railings are assumed 0.55 m above the floor.
F0 = FLOOR
GARAGE_WIN = (-26.53, -3.45)
FRONT_DOOR = (-16.29, -16.40)
OPENINGS = [
    # ---- street side -------------------------------------------------------------------------------------------
    ('win', 'g', (-18.90, -13.71), F0 + 0.55, 2.40, 1.80, dict(units=3)),              # W2 behind the left front run
    ('win', 'g', (-21.26, -13.22), F0 + 0.55, 0.70, 1.80, {}),                          # W1 on the bay's return
    # the front door unit (p01 rays on the entry wall + hero, round 3): one dark frame 1.86 x 2.34 (sill 0.33, head 2.67)
    # set straight into the shingles (dark casing) -- the leaf 1.02 with three tall top lights, a narrow sidelight (0.22 glass) at +-0.70
    ('door', 'g', FRONT_DOOR, PORCH_FLOOR + 0.05, 1.86, 2.34, dict(kind='unit', casing=0.06)),
    ('win', 'g', (-13.23, -19.00), F0 + 0.55, 2.30, 1.80, dict(units=3)),               # W3 right of the entry
    ('door', 'g', (-13.23, -20.85), PORCH_FLOOR + 0.05, 0.85, 2.20, dict(kind='glass', lights=0)),   # W4 (porch door)
    ('win', 'u', (-19.26, -13.71), 4.45, 2.50, 1.60, dict(units=3)),                    # triple window, upper left
    ('win', 'u', (-16.21, -16.48), 4.50, 1.85, 1.55, dict(units=2)),                    # twin window in the front gable
    ('win', 'u', (-21.57, -11.25), 4.65, 0.80, 1.50, {}),                               # west gable
    # garage gable (p01, level camera, rays on the wall y -3.40, +0.08 for the camera's 6 px there): frame x -27.35..-25.73,
    # z 1.41..2.96; flat casings ~0.17 wide, the stone wainscot's water table right under the sill
    ('win', 'g', GARAGE_WIN, 1.41, 1.62, 1.55, dict(units=2, casing=0.16)),
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
    roof_planes(geo, [p['rp'] for p in planes if p['src']['id'] != 'swp'] + swp_pieces(planes))
    fp = footprints(planes)
    walls(geo, fp, planes)
    eaves = ROOF['eaves']
    rear(geo, fp, planes, eaves)
    gable_trim(geo, planes)
    front_porch(geo, eaves)
    porch_floor(geo, fp)
    porch_soffit(geo, fp, planes)
    garage_wainscot(geo, fp)
    return [Part('house', geo, group='house')]
