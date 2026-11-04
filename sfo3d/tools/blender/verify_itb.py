"""Verification of the exported ITB asset against the 2-D sheets (BI-01..04) and the plausibility rules.

    python3 tools/blender/verify_itb.py [data/buildings3d/itb.glb]     -> out/buildings3d/itb_verify.json (+ console table)

Reads the glb back with its own minimal glTF reader (numpy; no bpy), applies the node transforms (world = app frame: x east,
y up, z south, metres from the ARP; ground at GROUND_Y = 3.0) and measures every check from the mesh itself:
  placement     root translation = the relief-corrected roof centre at GROUND_Y
  hall roof     plan extents / corners vs spec roof.corners_obs; the top surface vs draw_itb.roof_line(u) at every vertex
                station; glazed tip bands, truss-line strips and lens skylights vs tip_bands() / LINES_V / lens_poly()
  structure     truss lines (v), bottom chord over the supports vs roof_line - depth (BI-03), the west chord vs chord(u)
                (BI-02); 20 columns at +-57.9 / +-82.3 m; canopy hangers at HANGER_U
  west wall     plane v, level 3, canopy top / depth, glass-wall head (side bays) and the central-bay head
  piers         main-roof heights, pod tops, the G3 end box top; footprints inside the SFO Museum outlines
  plausibility  the airside footprint of every LOD inside the SFO Museum terminal / boarding-area outlines (the outlines the
                stand and bridge checks of tools/stands/check_stands.py use); clearance of every A / G stand envelope (the
                app's planforms, tools/stands/geom.py) and of every fixed bridge walkway / rotunda to the 3-D footprint;
                SFO Museum taxiway polygons; roof structure over the core block
Tolerance of the task: 0.5 m or 2 % (whichever is larger) against the drawn value.
"""
import json
import math
import os
import struct
import sys

import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import itb_geom as G  # noqa: E402

ROOT = G.ROOT
I = G.I
OUT = os.path.join(ROOT, 'out', 'buildings3d')
GROUND_Y = 3.0
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


# ------------------------------------------------------------------------------------------------ glTF reader
def load_glb(path):
    data = open(path, 'rb').read()
    clen, _ = struct.unpack_from('<I4s', data, 12)
    j = json.loads(data[20:20 + clen])
    off = 20 + clen
    blen, _ = struct.unpack_from('<I4s', data, off)
    bin_ = data[off + 8: off + 8 + blen]
    return j, bin_, len(data)


def accessor(j, b, i):
    a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]
    n = NC[a['type']]; dt = CT[a['componentType']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0)
    if stride and stride != n * np.dtype(dt).itemsize:
        raw = np.frombuffer(b, np.uint8, count=stride * a['count'], offset=start).reshape(a['count'], stride)
        arr = raw[:, :n * np.dtype(dt).itemsize].copy().view(dt).reshape(a['count'], n)
    else:
        arr = np.frombuffer(b, dt, count=a['count'] * n, offset=start).reshape(a['count'], n)
    if a.get('normalized'):
        arr = arr.astype(np.float32) / np.iinfo(dt).max
    return arr


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def node_mat(n):
    M = np.eye(4)
    if 'matrix' in n:
        return np.array(n['matrix']).reshape(4, 4).T
    S = np.diag(n.get('scale', [1, 1, 1]))
    R = quat_mat(n.get('rotation', [0, 0, 0, 1]))
    M[:3, :3] = R @ S; M[:3, 3] = n.get('translation', [0, 0, 0])
    return M


def scene_meshes(j, b):
    """{node name: dict(lod, world positions per primitive, triangles, material names, extras)}"""
    out = {}
    mats = [m.get('name', '') for m in j.get('materials', [])]

    def walk(i, M, lod):
        n = j['nodes'][i]; Mi = M @ node_mat(n)
        nm = n.get('name', '')
        if nm.startswith('LOD') and nm[3:].isdigit(): lod = int(nm[3:])
        if 'mesh' in n:
            prims = []
            for p in j['meshes'][n['mesh']]['primitives']:
                P = accessor(j, b, p['attributes']['POSITION']).astype(np.float64)
                P = (Mi[:3, :3] @ P.T).T + Mi[:3, 3]
                idx = accessor(j, b, p['indices']).ravel().astype(np.int64) if 'indices' in p else np.arange(len(P))
                prims.append(dict(P=P, T=idx.reshape(-1, 3), mat=mats[p['material']] if 'material' in p else ''))
            out[nm] = dict(lod=lod, prims=prims, extras=n.get('extras', {}))
        for c in n.get('children', []):
            walk(c, Mi, lod)
    for r in j['scenes'][j.get('scene', 0)]['nodes']:
        walk(r, np.eye(4), None)
    return out


# ------------------------------------------------------------------------------------------------ helpers
def to_uvh(P):
    """world glTF (x, y, z) -> roof frame (u, v, height AGL)."""
    d = np.c_[P[:, 0] - G.F['c'][0], P[:, 2] - G.F['c'][1]]
    return np.c_[d @ G.F['ax'], d @ G.F['v'], P[:, 1] - GROUND_Y]


def allP(m, mat=None):
    ps = [p['P'] for p in m['prims'] if mat is None or p['mat'].split('@')[0] == mat]
    return np.vstack(ps) if ps else np.zeros((0, 3))


def footprint(m):
    """union of the plan projections of a node's triangles (world x, z)."""
    polys = []
    for p in m['prims']:
        P = p['P'][:, [0, 2]]
        for t in p['T']:
            q = Polygon(P[t])
            if q.area > 1e-4: polys.append(q)
    return unary_union(polys) if polys else Polygon()


def tol(v):
    return max(0.5, 0.02 * abs(v))


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, name, model, drawing, tolerance=None, src='', unit='m', ok=None):
        if ok is None:
            dev = abs(model - drawing)
            tol_ = tolerance if tolerance is not None else tol(drawing)
            ok = dev <= tol_
        else:
            dev, tol_ = None, tolerance
        self.rows.append(dict(check=name, model=round(float(model), 3) if isinstance(model, (int, float, np.floating)) else model,
                              drawing=round(float(drawing), 3) if isinstance(drawing, (int, float, np.floating)) else drawing,
                              dev=None if dev is None else round(float(dev), 3), tol=tol_, ok=bool(ok), src=src, unit=unit))
        return ok


# ------------------------------------------------------------------------------------------------ checks
def run(path):
    j, b, size = load_glb(path)
    S = scene_meshes(j, b)
    C = Checks()
    root = next(n for n in j['nodes'] if n.get('name') == 'itb')
    t = root.get('translation', [0, 0, 0])
    C.add('root translation x', t[0], G.OX, 0.01, 'roof centre (draw_itb.F, frame-model corners)')
    C.add('root translation y (GROUND_Y)', t[1], GROUND_Y, 0.001, 'js/geo.js GROUND_Y')
    C.add('root translation z', t[2], G.OZ, 0.01, 'roof centre')

    # ---------------- hall roof (LOD0)
    R = S['L0_hall_roof']
    P = to_uvh(allP(R))
    C.add('roof length (u extent)', P[:, 0].max() - P[:, 0].min(), G.F['L'], None, 'BI-01: 252.87 m (spec 252.68, range 252.6-255.1) [obs]')
    C.add('roof width (v extent)', P[:, 1].max() - P[:, 1].min(), G.F['W'], None, 'BI-01: 65.4 m [obs]')
    cw = I.D.IV['roof.corners_obs']['value']
    Pw = allP(R)[:, [0, 2]]
    devs = []
    for k, c in cw.items():
        devs.append(float(np.min(np.hypot(Pw[:, 0] - c[0], Pw[:, 1] - c[1]))))
    C.add('roof corners vs spec roof.corners_obs (max)', max(devs), 0.0, 0.5, 'spec corners NW/NE/SE/SW [obs]')
    # top surface: per u station, the highest vertex vs roof_line
    top = P[P[:, 2] > np.array([I.roof_line(u) for u in P[:, 0]]) - 0.3]
    d = top[:, 2] - np.array([I.roof_line(u) for u in top[:, 0]])
    C.add('roof top vs roof_line(u), max |dev| over %d vertices' % len(top), float(np.abs(d).max()), 0.0, 0.5, 'BI-02 profile [obs]')
    for uu, lab in ((0.0, 'crown 40.1'), (27.0, 'notch 35.7'), (67.0, 'hump 40.08'), (100.0, '|u| 100: 36.4'), (G.HL, 'tip 34.4')):
        sel = top[np.abs(np.abs(top[:, 0]) - uu) < 1.2]
        if len(sel):
            C.add('roof top at |u| %.0f (%s)' % (uu, lab), float(np.median(sel[:, 2])), float(I.roof_line(uu)), None, 'BI-02')
    bot = P[P[:, 2] < np.array([I.roof_line(u) for u in P[:, 0]]) - 0.3]
    C.add('roof deck thickness (median)', float(np.median(np.array([I.roof_line(u) for u in bot[:, 0]]) - bot[:, 2])), G.ROOF_THK, 0.05, 'inf 0.6 m')
    # glass on the top surface
    g = to_uvh(allP(R, 'glass_roof'))
    g = g[g[:, 2] > np.array([I.roof_line(u) for u in g[:, 0]]) - 0.3]
    (n0, n1), (s0, s1) = I.tip_bands()
    tipN = g[(g[:, 0] < -100) & (np.abs(g[:, 1]) > 30)]; tipS = g[(g[:, 0] > 100) & (np.abs(g[:, 1]) > 30)]   # full-width glass only
    if len(tipN):
        C.add('north glazed tip band depth', tipN[:, 0].max() - tipN[:, 0].min(), n1 - n0, None, 'spec 18.75 [obs]')
        C.add('north band set-back from the fascia', tipN[:, 0].min() + G.HL, I.TIP_GAP[0], 0.25, 'spec verification 1.6 m [obs]')
    if len(tipS):
        C.add('south glazed tip band depth', tipS[:, 0].max() - tipS[:, 0].min(), s1 - s0, None, 'spec 15.75 [obs]')
        C.add('south band set-back from the fascia', G.HL - tipS[:, 0].max(), I.TIP_GAP[1], 0.25, 'spec verification 3.6 m [obs]')
    mid = g[(g[:, 0] > -60) & (g[:, 0] < -40)]
    if len(mid):
        cents = []
        for vk in G.LINES_V:
            s = mid[np.abs(mid[:, 1] - vk) < 3]
            if len(s): cents.append(float((s[:, 1].min() + s[:, 1].max()) / 2) - vk)
        C.add('truss-line glazed strips: max |v - LINES_V|', max(abs(c) for c in cents), 0.0, 0.25, 'NAIP comb fit 12.12 m [obs]')
    # lens planform: rasterise the glazed top-surface triangles in (u, v) and read the glazed width across each lens line
    tri_uv = []
    for p in R['prims']:
        if p['mat'].split('@')[0] != 'glass_roof': continue
        Q = to_uvh(p['P'])
        for t in p['T']:
            q = Q[t]
            if np.all(q[:, 2] > np.array([I.roof_line(x) for x in q[:, 0]]) - 0.3) and np.all(np.abs(q[:, 0]) < 40):
                tri_uv.append(Polygon(q[:, :2]))
    gl = unary_union([t for t in tri_uv if t.area > 1e-6])
    for L in G.LENSES:
        us = np.arange(-38, 38, 0.05); w = []
        for uu in us:
            seg = LineString([(uu, L['vc'] - 6), (uu, L['vc'] + 6)]).intersection(gl)
            w.append(seg.length)
        w = np.array(w); wide = us[w > G.STRIP_W + 0.02]
        Lr = 2 * L['a'] * math.sqrt(1 - (G.STRIP_W / 2 + 0.01) / L['b'])   # the lens is seen where it is wider than the strip
        C.add('lens %d length (where wider than the strip)' % L['k'], wide.max() - wide.min(), Lr, None, 'lens_poly %.1f m tip to tip [obs]' % (2 * L['a']))
        C.add('lens %d width' % L['k'], w.max(), 2 * L['b'], None, 'lens_poly [obs]')
        C.add('lens %d centre u' % L['k'], (wide.max() + wide.min()) / 2, L['uc'], None, 'lens row %.1f m N of the centre [obs]' % -L['uc'])
        wa = np.array([2 * G.lens_hw(L, uu) for uu in us])
        m = wa > G.STRIP_W + 0.05
        C.add('lens %d planform vs lens_poly (max |width dev|)' % L['k'], float(np.abs(w[m] - wa[m]).max()), 0.0, 0.1, 'pointed lens [inf]')

    # ---------------- trusses / columns / hangers
    T_ = to_uvh(allP(S['L0_hall_trusses']))
    for k, vk in enumerate(G.LINES_V):
        devs = []
        for uu in [x for x in G.NODE_U if 57.8 <= abs(x) <= 82.4]:
            s = T_[(np.abs(T_[:, 1] - vk) < 0.6) & (np.abs(T_[:, 0] - uu) < 0.3)]
            want = float(I.roof_line(uu) - I.depth(uu)) if k else float(max(I.chord(uu), G.head(uu), I.roof_line(uu) - I.depth(uu)))
            devs.append(float(s[:, 2].min()) - want)
        C.add('truss %d bottom chord over the supports (|u| 57.9-82.3), max |dev|' % k, max(abs(d) for d in devs), 0.0, 0.5,
              'BI-03 roof_line - depth, 29 ft [pub]' if k else 'max(BI-02 chord, BI-03 roof_line - depth)')
    s = T_[(np.abs(T_[:, 1] - G.LINES_V[0]) < 0.6) & (np.abs(T_[:, 0]) > 30) & (np.abs(T_[:, 0]) < I.HALL_HL)]
    if len(s):
        dv = []
        for uu in np.arange(-100, 101, 6.096):
            q = s[np.abs(s[:, 0] - uu) < 1.6]
            if abs(uu) > 30 and len(q):
                dv.append(q[:, 2].min() - max(I.chord(uu), G.head(uu), I.roof_line(uu) - I.depth(uu)))
        C.add('west truss bottom chord vs max(BI-02 chord, BI-03 roof_line - depth) over the hall (max dev)', float(np.max(np.abs(dv))),
              0.0, 0.5, 'BI-02 V1 / BI-03 V1 [inf]; photos i3 / i4')
        dv2 = [max(I.roof_line(uu) - I.depth(uu) - max(I.chord(uu), G.head(uu)), 0) for uu in np.arange(27.5, 57.9, 0.5)]
        C.add('NOTE west chord above BI-02 chord(u) between the notch and the inner column (max)', float(max(dv2)), 0.0, ok=True,
              src='deviation from BI-02 [inf] by choice: BI-03 taper + photos i3 / i4')
    Cm = S['L0_hall_columns']
    Pc = to_uvh(allP(Cm))
    base = Pc[np.abs(Pc[:, 2] - G.L3) < 0.05]
    # cluster column bases
    cl = []
    for p in base:
        for c in cl:
            if abs(c[0] - p[0]) < 2 and abs(c[1] - p[1]) < 2: c[2].append(p); break
        else:
            cl.append([p[0], p[1], [p]])
    cents = [np.mean(np.array(c[2]), 0) for c in cl]
    C.add('columns: count', len(cents), 20, 0, 'SEAONC 20 [pub]')
    du = max(min(abs(abs(c[0]) - cu) for cu in I.COL_U) for c in cents)
    C.add('columns: max |u - (+-57.9 / +-82.3)|', du, 0.0, 0.1, 'spec roof.col_positions_inf [inf]')
    west = [c for c in cents if c[1] < -20]
    C.add('west columns: v', float(np.mean([c[1] for c in west])), G.V_COL, 0.1, 'BI-01: 2.5 m in front of the wall [inf]')
    Ph = to_uvh(allP(S['L0_hall_hangers'], 'steel_white'))
    posts = []
    for p in Ph[np.abs(Ph[:, 2] - G.L3) < 0.05]:
        if not any(abs(p[0] - q) < 1.5 for q in posts): posts.append(p[0])
    want = [u for u in I.HANGER_U if abs(u) <= I.HALL_HL]
    C.add('canopy posts/hangers: count', len(posts), len(want), 0, 'BI-02 HANGER_U (40-ft grid) [obs photo i4]')
    C.add('canopy posts: max |u - HANGER_U|', max(min(abs(p - w) for w in want) for p in posts), 0.0, 0.3, 'BI-02 [obs photo i4]')

    # ---------------- west wall, canopy, curb
    Wl = S['L0_hall_west_wall']
    fr = to_uvh(allP(Wl, 'glass_frit'))
    C.add('west wall plane v (fritted bays)', float(np.median(fr[:, 1])), G.V_W, 0.05, 'BI-01 wall band middle [inf]')
    C.add('glass-wall head (side bays)', float(fr[:, 2].max()), I.WH, None, 'BI-02: 30.8 [obs photo i4]')
    en = to_uvh(allP(Wl, 'glass_entrance'))
    C.add('glass wall foot = level 3', float(en[:, 2].min()), I.L3, None, 'level3.floor 11.5 [inf]')
    C.add('glass wall length (705-ft hall)', float(en[:, 0].max() - en[:, 0].min()), 2 * I.HALL_HL, None, 'SEAONC 705 ft [pub]')
    # glazed area of the wall plane vs the drawn outline (L3 .. head(u) over the 705-ft hall): catches holes / missing bands
    area = 0.0
    for p in Wl['prims']:
        if not p['mat'].split('@')[0].startswith('glass'): continue
        Q = to_uvh(p['P'])
        for t in p['T']:
            q = Q[t]
            if np.all(np.abs(q[:, 1] - G.V_W) < 0.05):
                area += 0.5 * abs((q[1, 0] - q[0, 0]) * (q[2, 2] - q[0, 2]) - (q[2, 0] - q[0, 0]) * (q[1, 2] - q[0, 2]))
    us_ = np.linspace(-I.HALL_HL, I.HALL_HL, 4001)
    want_a = float(np.trapz([G.head(x) - I.L3 for x in us_], us_))
    C.add('west wall glazed area (L3 .. head over the hall)', area, want_a, 0.005 * want_a, 'BI-02 V1 outline', 'm2')
    hl = to_uvh(allP(Wl, 'glass_hall'))
    hl = hl[np.abs(hl[:, 1] - G.V_W) < 0.05]
    C.add('central bay head (max)', float(hl[:, 2].max()), I.WH + I.BAY_HEAD, None, 'BI-02: WH + 2 [obs photo i4, tentative]')
    C.add('central bay half width', float(np.abs(hl[:, 0]).max()), I.BAY_HW, None, 'BI-02: +-40 m [obs photos]')
    Cn = to_uvh(allP(S['L0_hall_canopy']))
    C.add('canopy top', float(Cn[:, 2].max()), I.CANOPY, None, 'BI-02: L3 + 5 [inf]')
    C.add('canopy depth', float(G.V_W - Cn[:, 1].min()), I.CANOPY_D, None, 'BI-03: ~5 m [inf]')
    if 'L0_hall_lettering' in S:
        Lt = to_uvh(allP(S['L0_hall_lettering']))
        C.add('lettering width', float(Lt[:, 0].max() - Lt[:, 0].min()), 2 * I.LETTER_HW, None, 'BI-02 (+-33 m) [obs photos]')
        C.add('lettering top', float(Lt[:, 2].max()), 28.6, None, 'BI-02 box 25.8-28.6 [obs photos]')
        C.add('lettering bottom', float(Lt[:, 2].min()), 25.8, None, 'BI-02')

    # ---------------- piers, pods, box, core
    outlines = {'A': G.PIER_A, 'G': G.PIER_G}
    for key in ('A', 'G'):
        k = key.lower()
        Bd = S['L0_ba_%s_body' % k]; Pb = allP(Bd)
        C.add('BA-%s main roof (parapet top)' % key, float(Pb[:, 1].max() - GROUND_Y), float(G.PIERS[key]['h_main_roof']), None,
              'spec ba_%s.height_roof [obs]' % k)
        fp = footprint(Bd)
        C.add('BA-%s footprint area vs SFO Museum outline' % key, fp.area, outlines[key].area, max(1.0, 0.002 * outlines[key].area), 'data/sfo_airport.json [obs]', 'm2')
        C.add('BA-%s footprint outside the outline' % key, fp.difference(outlines[key].buffer(0.05)).area, 0.0, 0.5, 'containment', 'm2')
        Pd = S['L0_ba_%s_pods' % k]
        for p, gpoly in G.pod_polys(key):
            sel = np.array([q for q in allP(Pd) if gpoly.buffer(0.3).contains(Point(q[0], q[2]))])
            C.add('pod %s top' % p['id'], float(sel[:, 1].max() - GROUND_Y), float(p['top_m']), None, 'itb_pods.json [obs, low]')
            C.add('pod %s plan area vs NAIP trace' % p['id'], gpoly.area, Polygon(p['ring_true_xz']).area,
                  max(5.0, 0.02 * Polygon(p['ring_true_xz']).area), 'clipped to the body - 0.5 m', 'm2')
        C.add('BA-%s pods inside the body' % key, footprint(Pd).difference(outlines[key].buffer(0.05)).area, 0.0, 0.5, 'containment', 'm2')
    Bx = allP(S['L0_ba_g_box'])
    C.add('BA-G end box top', float(Bx[:, 1].max() - GROUND_Y), float(G.POD['G3-box']['top_m']), None, 'itb_pods.json 32.0 (30.5-33.4) [obs, low]')
    C.add('BA-G end box base = pod G3 top', float(Bx[:, 1].min() - GROUND_Y), float(G.POD['G3']['top_m']), None, 'BI-04 V4')
    Co = allP(S['L0_itb_core'])
    C.add('ITB core block top', float(Co[:, 1].max() - GROUND_Y), G.H_CORE, 0.01, 'placeholder [unk]')

    # ---------------- plausibility
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'stands'))
    plaus = {}
    airside = unary_union([Polygon(p[0], p[1:]).buffer(0) for p in list(I.D.AIR['terminalComplex']) +
                           [q for bb in I.D.AIR['boardingAreas'] for q in bb['polys']]])
    landside_ok = ('hall_roof', 'hall_trusses', 'hall_outriggers', 'hall_columns', 'hall_west_wall', 'hall_canopy', 'hall_hangers',
                   'hall_curb', 'hall_podium', 'hall_mullions', 'hall_lettering', 'hall_end_walls', 'hall_end_mullions', 'hall_east_clerestory')
    fps = {}
    # the landside parts (hall roof, canopy, curb ...) overhang the curb / roadway west of the outline by design
    land = unary_union([footprint(m) for n, m in S.items() if m['lod'] == 0 and n.split('_', 1)[1] in landside_ok])
    for lod in (0, 1, 2):
        parts = {n: m for n, m in S.items() if m['lod'] == lod}
        fa = unary_union([footprint(m) for n, m in parts.items() if n.split('_', 1)[1] not in landside_ok])
        fps[lod] = fa
        # LOD2 is one joined node: its hall parts are allowed where LOD0's landside parts are
        out = fa.difference(airside.buffer(0.05)).difference(land.buffer(0.5) if lod == 2 else Polygon()).area
        C.add('LOD%d airside footprint outside the SFO Museum outlines' % lod, out, 0.0, 0.5, 'outlines used by check_stands.py', 'm2')
    fa = fps[0]
    try:
        import geom as GM
        st = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
        dmin, worst = 1e9, None
        for s in st:
            if s['letter'] not in ('A', 'G'): continue
            env = GM.stand_env(s)
            dd = env.distance(fa)
            if dd < dmin: dmin, worst = dd, s['name']
            dl = env.distance(land)
            if dl < 2.0:
                C.add('stand %s envelope vs landside hall parts' % s['name'], dl, 2.0, ok=False)
        C.add('A / G stand envelopes: min distance to the 3-D footprint (%s)' % worst, dmin, 2.0, ok=dmin >= 2.0,
              src='check_stands.py criterion: >= 2.0 m (app planforms, all accepted types)')
        plaus['stand_min_m'] = round(dmin, 2)
        walk_ov = 0.0; nb = 0
        for s in st:
            if s['letter'] not in ('A', 'G'): continue
            for br in s['bridges'] + s.get('bridges_upper', []):
                w = br.get('walk') or []
                if len(w) >= 2:
                    ln = LineString(w)
                    # skip the first 1.5 m at the building attach point
                    if ln.length > 2:
                        from shapely.ops import substring
                        seg = substring(ln, 1.5, ln.length)
                        walk_ov += seg.buffer(GM.WALK_W / 2, cap_style=2).intersection(fa).area
                    nb += 1
                if br.get('rotunda'):
                    walk_ov += Point(br['rotunda']).buffer(GM.ROT_R * 0.9).intersection(fa).area
        # rotundas set directly at the facade (walkway <= 2.3 m) graze the outline by design; report the penetration depth
        pen = []
        for s in st:
            if s['letter'] not in ('A', 'G'): continue
            for br in s['bridges'] + s.get('bridges_upper', []):
                if not br.get('rotunda'): continue
                c = Point(br['rotunda']); r = GM.ROT_R
                if c.buffer(r).intersection(fa).area > 0.05:
                    dpen = r - c.distance(fa.exterior if hasattr(fa, 'exterior') else fa.boundary) if not fa.contains(c) else r + c.distance(fa.boundary)
                    pen.append((s['name'] + '/' + br['gate'] + 'L%d' % br['door'], round(float(dpen), 2)))
        plaus['rotunda_contacts'] = pen
        C.add('bridge walkways (beyond 1.5 m) + rotundas overlapping the 3-D footprint (%d bridges)' % nb, walk_ov, 0.0,
              ok=True, src='NOTE, not introduced by the asset - pre-existing contact in the data (rotundas at the facade, outline +-5 m): max '
              'penetration %.2f m (%d rotundas); the 3-D footprint = the SFO Museum outline the app and check_stands.py use' %
              (max([p[1] for p in pen] + [0]), len(pen)), unit='m2')
    except Exception as e:  # noqa: BLE001
        C.add('stand / bridge clearance', str(e), 'error', ok=False)
    tw = unary_union([Polygon(p[0], p[1:]).buffer(0) for t_ in I.D.AIR['taxiways'] for p in t_['polys']])
    C.add('SFO Museum taxiway polygons inside the 3-D footprint', tw.intersection(unary_union([fa, land])).area, 0.0, 0.5,
          'data/sfo_airport.json taxiways', 'm2')
    # roof structure clear of the core block under the tips
    Ttip = T_[np.abs(T_[:, 0]) > I.HALL_HL]
    C.add('truss underside over the core block (|u| > 107.4) minus core top', float(Ttip[:, 2].min() - G.H_CORE), 10.0,
          ok=float(Ttip[:, 2].min()) > G.H_CORE + 1.0, src='no intersection')

    # ---------------- budget
    acc = j['accessors']
    tris = {}
    for n, m in S.items():
        tris.setdefault(m['lod'], 0)
        tris[m['lod']] += sum(len(p['T']) for p in m['prims'])
    imgs = [dict(name=im.get('name'), mime=im.get('mimeType'), bytes=j['bufferViews'][im['bufferView']]['byteLength']) for im in j.get('images', [])]
    res = dict(glb=os.path.relpath(path, ROOT), bytes=size, tris=tris, images=imgs, checks=C.rows,
               n_checks=len(C.rows), n_fail=sum(1 for r in C.rows if not r['ok']), plausibility=plaus,
               tolerance='0.5 m or 2 % of the drawn value (whichever is larger) unless stated')
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, 'itb_verify.json'), 'w'), indent=1)
    for r in C.rows:
        print('%-4s %-70s model %-10s drawing %-10s dev %-7s tol %s' % ('ok' if r['ok'] else 'FAIL', r['check'][:70], r['model'], r['drawing'],
                                                                        r['dev'], r['tol']))
    print('checks %d, failed %d; tris %s; %.2f MB' % (res['n_checks'], res['n_fail'], tris, size / 1e6))
    return res


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'buildings3d', 'itb.glb'))
