"""The house: roofs as a union of simple blocks, walls as facades with their openings, the front porch.

World metres (model/kit.py).  Sources: eave lines from the registered aerial photo (tools/p30w.py), eave heights
and pitches from the drone point cloud (tools/fitbox.py: shingle roofs 5:12 from eaves at 7.2, standing-seam
roofs ~21 deg from eaves at 4.0, the membrane roof behind the porch at 4.82), openings from the zone surveys cast
through the registered photos (tools/elem_world.py).  Roof blocks overlap; what is inside another block never shows.
"""
import numpy as np

from model import fixtures as FX
from model import openings as OP
from model.kit import Geo, Part
from model.massing_kit import hip_roof, roof_planes

SL_UP, SL_LO = 5 / 12, 0.385
Z_SLAB, FLOOR = 0.36, 1.0            # garage slab / main floor and porch floor
Z_E1, Z_E2 = 4.0, 7.2                # top of the roofing at the lower / upper eave lines
ROOF_T = 0.24
PLATE1, PLATE2 = Z_E1 - ROOF_T, Z_E2 - ROOF_T
OVER = 0.40                          # eave line -> wall face

# ---- roof blocks: eave rectangle (x0, y0, x1, y1), gable ends, ridge direction -----------------------------------
UPPER = {
    'UA_left': dict(rect=(1.96, 2.40, 11.40, 10.40)),
    'UA_bay': dict(rect=(2.54, 1.95, 6.26, 6.5), gable=('y0',), ridge='y'),
    'UB_rear_left_gable': dict(rect=(1.96, 6.0, 6.40, 11.60), gable=('y1',), ridge='y'),
    'UC_rear_mid': dict(rect=(10.38, 5.0, 15.18, 13.20), ridge='y'),
    'UD_mid': dict(rect=(8.5, 2.90, 18.0, 8.80), ridge='x', gable=('x0', 'x1')),
    'UE_right_gable': dict(rect=(14.38, 0.38, 19.82, 6.5), gable=('y0',), ridge='y'),
    'UE_bay': dict(rect=(15.35, -0.45, 19.25, 3.0), gable=('y0',), ridge='y'),
    'UF_right': dict(rect=(16.8, 0.95, 23.10, 10.05), ridge='y', gable=('y1',)),
}
# lower roofs overlap deeply, so that their inner ends are buried in the neighbour (two blocks that merely touch
# would show a V between their hips)
LOWER = {
    'LB1_garage_left': dict(rect=(0.10, 0.15, 10.4, 13.20)),
    'LP_base': dict(rect=(6.60, -2.47, 19.80, 4.0), z_cap=4.82),
    'LP_left': dict(rect=(6.60, -3.30, 14.85, 4.0), z_cap=4.82),
    'LP_entry': dict(rect=(10.40, -3.55, 14.85, 4.0), z_cap=4.82),
    'LB3_wing': dict(rect=(19.40, -1.67, 25.95, 13.06)),
    'LB3b_wing_bay': dict(rect=(14.85, -2.22, 25.03, 3.0), z_cap=4.6),
    'LB3c_wing_gable': dict(rect=(20.45, -1.97, 24.05, 1.0), gable=('y0',), ridge='y', z=4.3),
    'LB4_rear_family': dict(rect=(12.0, 8.0, 20.80, 14.35)),
    'LB5_rear_bay': dict(rect=(10.38, 9.0, 15.10, 16.47), z_cap=4.75),
    'LB6_rear_left': dict(rect=(6.68, 8.0, 15.10, 13.88)),
}


def blocks():
    out = {}
    for name, b in UPPER.items():
        out[name] = hip_roof(name, *b['rect'], Z_E2, SL_UP, 'roof_shingle', gable=b.get('gable', ()), ridge=b.get('ridge'), storey=2)
    for name, b in LOWER.items():
        out[name] = hip_roof(name, *b['rect'], b.get('z', Z_E1), SL_LO, 'roof_seam', gable=b.get('gable', ()),
                             ridge=b.get('ridge'), z_cap=b.get('z_cap'), storey=1)
    return out


def planes():
    return [p for ps in blocks().values() for p in ps]


def _up(n):
    return n if n[2] > 0 else -n


def roof_details(geo, bl):
    """Standing seams, ridge / hip caps, and fascia + gutter along the eaves that are not buried in another block."""
    for name, ps in bl.items():
        others = [p for n, q in bl.items() if n != name for p in q]
        z_e = min(p.pts[:, 2].min() for p in ps)
        edges = {}
        for p in ps:
            if p.pitch < 2:
                continue
            dn = p.downhill
            if p.mat == 'roof_seam':
                FX.seam_ribs(geo, p.pts, np.array([-dn[1], dn[0], 0.0]))
            n = len(p.pts)
            for i in range(n):
                a, b = p.pts[i], p.pts[(i + 1) % n]
                key = tuple(sorted((tuple(np.round(a, 3)), tuple(np.round(b, 3)))))
                edges.setdefault(key, []).append(p)
        for (a, b), pp in edges.items():
            a, b = np.array(a), np.array(b)
            if len(pp) == 2:                               # hip or ridge
                if a[2] > b[2]:
                    a, b = b, a
                FX.ridge_cap(geo, a, b, kind='seam' if pp[0].mat == 'roof_seam' else 'shingle',
                             n1=_up(FX.poly_normal(pp[0].pts)), n2=_up(FX.poly_normal(pp[1].pts)))
            elif abs(a[2] - z_e) < 0.01 and abs(b[2] - z_e) < 0.01:      # an eave: gutter where it is exposed
                dn = pp[0].downhill
                out = np.array([dn[0], dn[1], 0.0])
                L = float(np.linalg.norm(b - a))
                m = max(2, int(L / 0.25))
                ok = []
                for k in range(m):
                    q = a + (b - a) * (k + 0.5) / m
                    qo = q + out * 0.12
                    ok.append(not any(o.contains(qo[0], qo[1]) and o.z(qo[0], qo[1]) > z_e - 0.3 for o in others))
                k = 0
                while k < m:
                    if ok[k]:
                        j = k
                        while j < m and ok[j]:
                            j += 1
                        if (j - k) * L / m > 0.4:
                            FX.gutter(geo, a + (b - a) * k / m, a + (b - a) * j / m, out)
                        k = j
                    else:
                        k += 1


# ---- facades -----------------------------------------------------------------------------------------------------
# a, b: the wall's ends in plan, LEFT then RIGHT as seen from outside; z0: its base; openings: (builder, x, z, args, kw)
# with x along the wall from a and z above z0.
def _lantern(x, z=1.55):
    return ('lantern', x, z)


GROUND = [
    dict(name='garage_front', a=(0.5, 0.55), b=(7.75, 0.55), z0=Z_SLAB, ops=[
        (OP.garage_pair, 1.49, 0.0, (), dict(door_w=2.37, h=2.25, pier=0.23, seed=3))],
        lanterns=[(1.0, 1.915), (6.75, 1.915)], awning=dict(x=3.725, z=2.66, w=5.5, rods=4)),
    dict(name='office_west', a=(7.75, 0.55), b=(7.75, -0.65), z0=FLOOR, ops=[
        (OP.window, 0.38, 0.35, (0.45, 1.95), dict(n=1, lights=1, floor=0.35, seed=11))]),
    dict(name='office_front', a=(7.75, -0.65), b=(11.85, -0.65), z0=FLOOR, ops=[
        (OP.french_doors, 0.96, 0.0, (), dict(w=2.05, h=2.3, leaves=2, lights=3, seed=12))]),
    dict(name='entry_west', a=(11.85, -0.65), b=(11.85, 0.85), z0=FLOOR, ops=[]),
    dict(name='entry_living', a=(11.85, 0.85), b=(19.3, 0.85), z0=FLOOR, ops=[
        (OP.entry_door, 0.21, 0.0, (), dict(w=1.86, h=2.47, seed=13)),
        (OP.french_doors, 3.78, 0.0, (), dict(w=2.65, h=2.31, leaves=2, lights=3, side_l=0.38, side_r=0.38, seed=14))],
        lanterns=[(2.75, 1.87)]),
    dict(name='wing_west', a=(19.3, 0.85), b=(19.3, -1.1), z0=FLOOR, ops=[
        (OP.french_doors, 0.95, 0.0, (), dict(w=0.9, h=2.45, leaves=1, lights=2, seed=15))]),
    dict(name='wing_front_l', a=(19.3, -1.1), b=(20.1, -1.1), z0=FLOOR, ops=[]),
    dict(name='wing_bay_w', a=(20.1, -1.1), b=(20.1, -1.8), z0=FLOOR, ops=[], mat='siding_bb'),
    dict(name='wing_bay_front', a=(20.1, -1.8), b=(24.5, -1.8), z0=FLOOR, mat='siding_bb', ops=[
        (OP.bay_window, 0.72, 0.35, (), dict(w=2.85, h=1.85))],
        lanterns=[(0.34, 1.73), (3.95, 1.73)], awning=dict(x=2.3, z=2.3, w=3.6, rods=3, proj=0.8, slats=0)),
    dict(name='wing_bay_e', a=(24.5, -1.8), b=(24.5, -1.26), z0=FLOOR, ops=[], mat='siding_bb'),
    dict(name='wing_front_r', a=(24.5, -1.26), b=(25.55, -1.26), z0=FLOOR, ops=[]),
    dict(name='east', a=(25.55, -1.26), b=(25.55, 12.66), z0=FLOOR, ops=[]),
    dict(name='wing_rear', a=(25.55, 12.66), b=(20.4, 12.66), z0=FLOOR, ops=[]),
    dict(name='family_east', a=(20.4, 12.66), b=(20.4, 13.95), z0=FLOOR, ops=[]),
    dict(name='family_rear', a=(20.4, 13.95), b=(14.7, 13.95), z0=FLOOR, ops=[]),
    dict(name='rear_bay_east', a=(14.7, 13.95), b=(14.7, 16.07), z0=FLOOR, ops=[]),
    dict(name='rear_bay', a=(14.7, 16.07), b=(10.78, 16.07), z0=FLOOR, ops=[]),
    dict(name='rear_bay_west', a=(10.78, 16.07), b=(10.78, 13.48), z0=FLOOR, ops=[]),
    dict(name='rear_left_mid', a=(10.78, 13.48), b=(7.08, 13.48), z0=FLOOR, ops=[]),
    dict(name='rear_left_step', a=(7.08, 13.48), b=(7.08, 12.8), z0=FLOOR, ops=[]),
    dict(name='rear_left', a=(7.08, 12.8), b=(0.5, 12.8), z0=FLOOR, ops=[]),
    dict(name='west', a=(0.5, 12.8), b=(0.5, 0.55), z0=Z_SLAB, ops=[]),
]
ZU = Z_E1                              # base of the upper facades (the upper floor is ~0.4 above it)
UPPER_WALLS = [
    dict(name='ua_front_stub', a=(2.36, 2.8), b=(2.84, 2.8), ops=[]),
    dict(name='ua_bay_w', a=(2.84, 2.8), b=(2.84, 2.3), ops=[], mat='siding_bb'),
    dict(name='ua_bay', a=(2.84, 2.3), b=(5.96, 2.3), mat='siding_bb', gable=(0.3, 0.3), ops=[
        (OP.window, 0.71, 0.88, (1.9, 1.71), dict(n=2, lights=2, seed=21))]),
    dict(name='ua_bay_e', a=(5.96, 2.3), b=(5.96, 2.8), ops=[], mat='siding_bb'),
    dict(name='ua_front', a=(5.96, 2.8), b=(11.0, 2.8), ops=[
        (OP.window, 1.75, 1.95, (1.03, 0.58), dict(n=1, lights=0, seed=22)),
        (OP.window, 3.64, 1.0, (0.87, 1.53), dict(n=1, lights=2, seed=23))]),
    dict(name='ud_step', a=(11.0, 2.8), b=(11.0, 3.3), ops=[]),
    dict(name='ud_front', a=(11.0, 3.3), b=(14.78, 3.3), ops=[
        (OP.window, 1.22, 0.72, (1.72, 1.99), dict(n=2, lights=2, seed=24))]),
    dict(name='ue_west', a=(14.78, 3.3), b=(14.78, 0.78), ops=[
        (OP.window, 1.13, 1.84, (0.81, 0.71), dict(n=1, lights=0, seed=25))]),
    dict(name='ue_front_l', a=(14.78, 0.78), b=(15.75, 0.78), ops=[]),
    dict(name='ue_bay_w', a=(15.75, 0.78), b=(15.75, 0.08), ops=[], mat='siding_bb'),
    dict(name='ue_bay', a=(15.75, 0.08), b=(18.85, 0.08), mat='siding_bb', gable=(0.4, 0.4), ops=[
        (OP.window, 0.7, 1.04, (1.7, 1.49), dict(n=2, lights=2, seed=26))]),
    dict(name='ue_bay_e', a=(18.85, 0.08), b=(18.85, 0.78), ops=[], mat='siding_bb'),
    dict(name='ue_front_r', a=(18.85, 0.78), b=(19.42, 0.78), ops=[]),
    dict(name='ue_east', a=(19.42, 0.78), b=(19.42, 1.35), ops=[]),
    dict(name='uf_front', a=(19.42, 1.35), b=(22.7, 1.35), ops=[
        (OP.window, 1.75, 1.59, (0.8, 0.73), dict(n=1, lights=0, seed=27))]),
    dict(name='uf_east', a=(22.7, 1.35), b=(22.7, 9.65), ops=[]),
    dict(name='uf_rear', a=(22.7, 9.65), b=(17.2, 9.65), gable=(0.4, 0.4), mat='siding_bb', ops=[]),
    dict(name='uc_east', a=(14.78, 9.65), b=(14.78, 12.8), ops=[]),
    dict(name='uc_rear', a=(14.78, 12.8), b=(10.78, 12.8), ops=[]),
    dict(name='uc_west', a=(10.78, 12.8), b=(10.78, 10.0), ops=[]),
    dict(name='ua_rear', a=(10.78, 10.0), b=(6.0, 10.0), ops=[]),
    dict(name='ub_east', a=(6.0, 10.0), b=(6.0, 11.2), ops=[]),
    dict(name='ub_rear', a=(6.0, 11.2), b=(2.36, 11.2), gable=(0.4, 0.4), mat='siding_bb', ops=[]),
    dict(name='ua_west', a=(2.36, 11.2), b=(2.36, 2.8), ops=[]),
]
COLUMNS = [(7.85, -3.05), (11.35, -3.30), (14.4, -3.30), (14.4, -2.22), (18.95, -2.22)]      # centres, porch floor to beam
COL_LANTERN = [0, 1, 2, 4]
CHIMNEYS = [dict(x=(19.25, 20.45), y=(0.7, 2.2), z0=4.0, top=9.5, cap=True),
            dict(x=(17.47, 18.04), y=(6.96, 7.52), z0=7.0, top=9.3, cap=True),
            dict(x=(24.05, 24.95), y=(9.7, 10.45), z0=4.0, top=6.3, cap=True)]


def _frame(w):
    a, b = np.array(w['a'], float), np.array(w['b'], float)
    L = float(np.linalg.norm(b - a))
    right = np.array([(b - a)[0] / L, (b - a)[1] / L, 0.0])
    out = np.array([right[1], -right[0], 0.0])
    return a, right, out, L


def _facade(walls, extras, w, z0, h, gable_slope=None):
    a, right, out, L = _frame(w)
    f = OP.Facade(walls, (a[0], a[1], z0), right, L, h, mat=w.get('mat', 'siding_lap'))
    for builder, x, z, args, kw in w.get('ops', []):
        f.add(builder, x, z, *args, **kw)
    f.finish()
    if gable_slope:                                    # the gable above the plate, up to the roof's underside
        top, (ol, orr) = z0 + h, w['gable']
        e, m = a + right[:2] * L, a + right[:2] * (L + orr - ol) / 2
        walls.poly(w.get('mat', 'siding_lap'), [(a[0], a[1], top), (e[0], e[1], top), (e[0], e[1], top + orr * gable_slope),
                                                 (m[0], m[1], top + (L + ol + orr) / 2 * gable_slope),
                                                 (a[0], a[1], top + ol * gable_slope)])
    o = np.array([a[0], a[1], z0])
    for x, z in w.get('lanterns', []):
        FX.lantern(extras, o + right * x + np.array([0, 0, z]), right, out)
    if w.get('awning'):
        aw = w['awning']
        FX.awning(extras, o + right * aw['x'] + np.array([0, 0, aw['z']]), right, out, aw['w'], rods=aw.get('rods', 4),
                  proj=aw.get('proj', 0.95), slats=aw.get('slats', 4))


def build():
    roofs, walls, extras, porch = Geo(), Geo(), Geo(), Geo()
    bl = blocks()
    ps = [p for q in bl.values() for p in q]
    roof_planes(roofs, ps)
    roof_details(roofs, bl)
    for w in GROUND:
        _facade(walls, extras, w, w['z0'], PLATE1 - w['z0'])
        a, right, out, L = _frame(w)                   # foundation band down into the ground
        walls.poly('concrete', [(a[0], a[1], -0.6), tuple(np.r_[a + right[:2] * L, -0.6]), tuple(np.r_[a + right[:2] * L, w['z0']]),
                                (a[0], a[1], w['z0'])])
    for w in UPPER_WALLS:
        _facade(walls, extras, w, ZU, PLATE2 - ZU, gable_slope=SL_UP if w.get('gable') else None)
    # chimneys
    for c in CHIMNEYS:
        walls.box('chimney_white', (c['x'][0], c['y'][0], c['z0']), (c['x'][1], c['y'][1], c['top']), faces='xXyYZ')
        if c['cap']:
            FX.chimney_cap(extras, ((c['x'][0] + c['x'][1]) / 2, (c['y'][0] + c['y'][1]) / 2, c['top']),
                           c['x'][1] - c['x'][0], c['y'][1] - c['y'][0])
    # the right wing's front gable: a white pediment over the bay's skirt roof
    gx0, gy, gx1, gz = 20.55, -1.87, 23.95, 4.3 + 0.1 * SL_LO
    walls.poly('trim_white', [(gx0, gy, gz), (gx1, gy, gz), ((gx0 + gx1) / 2, gy, gz + (gx1 - gx0) / 2 * SL_LO)])
    # front porch: bluestone floor on a stone base, columns under the beams at the eave, steps
    slabs = ((7.6, -3.25, 11.15, -0.65), (11.15, -3.5, 14.6, 0.85), (14.6, -2.42, 19.3, 0.85))
    for x0, y0, x1, y1 in slabs:
        porch.box('bluestone', (x0, y0, FLOOR - 0.05), (x1, y1, FLOOR), faces='xXyZ')
        porch.box('stone_veneer', (x0 + 0.03, y0 + 0.03, 0.0), (x1 - 0.03, y1, FLOOR - 0.05), faces='xXy')
    zb = FLOOR + 2.62
    for i, (cx, cy) in enumerate(COLUMNS):
        FX.column(porch, (cx, cy, FLOOR), 2.62, size=0.3)
        if i in COL_LANTERN:
            FX.lantern(extras, (cx, cy - 0.15, FLOOR + 1.73), np.array([1.0, 0, 0]), np.array([0, -1.0, 0]))
    c = COLUMNS
    for a, b in (((c[0][0] - 0.15, c[0][1]), (c[1][0], c[0][1])), ((c[1][0], c[1][1]), (c[2][0] + 0.15, c[2][1])),
                 ((c[3][0], c[3][1]), (19.3, c[4][1])), ((c[0][0], c[0][1]), (c[0][0], -0.65)),
                 ((c[1][0], c[1][1]), (c[1][0], -0.65)), ((c[2][0], c[2][1]), (c[2][0], 0.85))):
        FX.beam(porch, (a[0], a[1], zb), (b[0], b[1], zb))
    for x0, y0, x1, y1 in ((7.75, -3.2, 11.3, -0.65), (11.3, -3.45, 14.55, 0.85), (14.55, -2.37, 19.3, 0.85)):
        porch.box('soffit_white', (x0, y0, zb + 0.26), (x1, y1, zb + 0.28), faces='z')
    for k in range(4):                                 # entry steps: 4 risers from the walk (0.46) to the porch floor
        z1 = FLOOR - (k + 1) * 0.135
        porch.box('bluestone', (11.7, -3.5 - (k + 1) * 0.32, 0.0), (13.95, -3.5 - k * 0.32, z1), faces='xXyZ')
    return [Part('roofs', roofs), Part('walls', walls), Part('porch', porch), Part('fixtures', extras)]
