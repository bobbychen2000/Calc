"""Verification of the exported domestic terminals asset against the 2-D sheets (BD-01..03) and the plausibility rules.

    python3 tools/blender/verify_domestic.py [data/buildings3d/domestic.glb]   -> out/buildings3d/domestic_verify.json (+ table)

Reads the glb back with its own minimal glTF reader (numpy; no bpy), applies the node transforms (world = app frame: x east,
y up, z south, metres from the ARP; ground at GROUND_Y = 3.0) and measures every check FROM THE MESH (a top-surface height
probe: the highest LOD0 triangle over a plan point), against the values the sheet code draws (tools/buildings/
draw_domestic.py, draw_data.py, through tools/blender/dom_geom.py):
  placement      root translation
  heights        the roof edge (coping / fascia top) of every pier, band, drum, lantern, monitor, hall and penthouse
  BA-B           the raised band's lean-free edges (s -391.0 / -423.4) and the outer roof edges (s -383.73 / -438.04) at
                 every 10 m along the straight pier; the widths 7.3 / 32.4 / 14.7 / 54.3 m (BD-02 view 1)
  roof edges     BA-B / BA-D / BA-F measured lean-free roof edge lines (dom_true_edges) vs the mesh's roof edge
  BA-E           stepped section: fascia 12.85, lower side roofs 9.85, flank 4.4, overhang 1.5 (BD-02)
  BA-F / BA-D    lantern (19.4 m octagon at baf_lantern_centre, top 10.49 + 1.0 minimal rise), drums (D 19.2 m, top 13.19)
  T3             T3W parapet 16.76, T3W airside window stack (L3 10.36, +10 ft glass, +2 ft band), T3E 14.48, penthouse 21.34
  T1             curb canopy soffit 8.88 (curb 4.88 + 4.0), depth 4.0; wall head 17.88; landside run lengths vs BD-03
  footprints     the walls lie on the SFO Museum level-2 outlines (except the documented trims / set-backs)
  plausibility   clearance of every B-F stand envelope (app planforms, all accepted types, tools/stands/geom.py) to the
                 3-D footprint, with the height of what is near; bridge walkways (the app's drawn part, from its start E)
                 vs 3-D geometry in the walkway height band; SFO Museum taxiways; the tower base-building exclusion;
                 the ITB asset footprint
  budget         triangles / draw calls per LOD, textures
Tolerance of the task: 0.5 m or 2 % (whichever is larger) against the drawn value.
"""
import json
import math
import os
import struct
import sys

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dom_geom as G  # noqa: E402

ROOT = G.ROOT
D, DD = G.D, G.DD
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
    return j, data[off + 8: off + 8 + blen], len(data)


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
    M[:3, :3] = quat_mat(n.get('rotation', [0, 0, 0, 1])) @ S; M[:3, 3] = n.get('translation', [0, 0, 0])
    return M


def scene_meshes(j, b):
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


def to_local(P):
    """glTF world (x, y, z) -> dom local (X east from OX, Y north from OZ, Z above grade)."""
    return np.c_[P[:, 0] - G.OX, G.OZ - P[:, 2], P[:, 1] - GROUND_Y]


# ------------------------------------------------------------------------------------------------ height probe
class TopProbe:
    """highest triangle over a plan point (local X, Y) among a set of triangles (non-vertical only), grid-hashed."""

    def __init__(self, tris, cell=6.0):
        T = np.asarray(tris, float)
        e1 = T[:, 1, :2] - T[:, 0, :2]; e2 = T[:, 2, :2] - T[:, 0, :2]
        a = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
        keep = np.abs(a) > 1e-6
        self.T = T[keep]; self.A = a[keep]; self.cell = cell
        lo = self.T[:, :, :2].min(1); hi = self.T[:, :, :2].max(1)
        self.h = {}
        for k, (l, h_) in enumerate(zip(lo, hi)):
            for cx in range(int(math.floor(l[0] / cell)), int(math.floor(h_[0] / cell)) + 1):
                for cy in range(int(math.floor(l[1] / cell)), int(math.floor(h_[1] / cell)) + 1):
                    self.h.setdefault((cx, cy), []).append(k)

    def z(self, X, Y):
        ks = self.h.get((int(math.floor(X / self.cell)), int(math.floor(Y / self.cell))))
        if not ks: return None
        T = self.T[ks]; A = self.A[ks]
        p = np.array([X, Y])
        w1 = ((T[:, 1, 0] - p[0]) * (T[:, 2, 1] - p[1]) - (T[:, 1, 1] - p[1]) * (T[:, 2, 0] - p[0])) / A
        w2 = ((T[:, 2, 0] - p[0]) * (T[:, 0, 1] - p[1]) - (T[:, 2, 1] - p[1]) * (T[:, 0, 0] - p[0])) / A
        w3 = 1 - w1 - w2
        m = (w1 >= -1e-9) & (w2 >= -1e-9) & (w3 >= -1e-9)
        if not m.any(): return None
        zz = w1[m] * T[m, 0, 2] + w2[m] * T[m, 1, 2] + w3[m] * T[m, 2, 2]
        return float(zz.max())


def tris_of(S, names, mats=None, lod=0):
    out = []
    for n, m in S.items():
        if m['lod'] != lod or (names is not None and not any(n.startswith(x) for x in names)): continue
        for p in m['prims']:
            if mats is not None and p['mat'].split('@')[0] not in mats: continue
            L = to_local(p['P'])
            out.append(L[p['T']])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def footprint(S, lod, zband=None, names=None):
    """union of the plan projections (world x, z) of a LOD's triangles (optionally only triangles reaching into a height band;
    vertical faces as 5-cm strips)."""
    polys = []
    for n, m in S.items():
        if m['lod'] != lod or (names is not None and not any(n.startswith(x) for x in names)): continue
        for p in m['prims']:
            P = p['P']
            for t in p['T']:
                q = P[t]
                if zband is not None:
                    h = q[:, 1] - GROUND_Y
                    if h.max() < zband[0] or h.min() > zband[1]: continue
                pg = Polygon(q[:, [0, 2]])
                if pg.area > 1e-4:
                    polys.append(pg)
                else:
                    ln = LineString(q[:, [0, 2]])
                    if ln.length > 1e-3: polys.append(ln.buffer(0.025, cap_style=2))
    return unary_union(polys) if polys else Polygon()


def tol(v):
    return max(0.5, 0.02 * abs(v))


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, name, model, drawing, tolerance=None, src='', unit='m', ok=None, group=''):
        if ok is None:
            dev = abs(model - drawing)
            tol_ = tolerance if tolerance is not None else tol(drawing)
            ok = dev <= tol_
        else:
            dev = None if not isinstance(model, (int, float, np.floating)) or not isinstance(drawing, (int, float, np.floating)) else abs(model - drawing)
            tol_ = tolerance
        self.rows.append(dict(group=group, check=name,
                              model=round(float(model), 3) if isinstance(model, (int, float, np.floating)) else model,
                              drawing=round(float(drawing), 3) if isinstance(drawing, (int, float, np.floating)) else drawing,
                              dev=None if dev is None else round(float(dev), 3), tol=tol_, ok=bool(ok), src=src, unit=unit))
        return ok


def st_local(s, t):
    x, z = G.st2w(s, t)
    return G.Lp(x, z)


# ------------------------------------------------------------------------------------------------ checks
def run(path):
    j, b, size = load_glb(path)
    S = scene_meshes(j, b)
    C = Checks()
    W, feats, info = G.build_world(0)
    sol = {s.key: s for s in W.S}
    root = next(n for n in j['nodes'] if n.get('name') == 'domestic')
    t = root.get('translation', [0, 0, 0])
    for k, (v, d) in enumerate(zip(t, (G.OX, GROUND_Y, G.OZ))):
        C.add('root translation ' + 'xyz'[k], v, d, 0.001, 'dom_geom OX / GROUND_Y / OZ (js/geo.js GROUND_Y 3.0)', group='placement')

    shell = tris_of(S, None, lod=0)
    TP = TopProbe(shell)
    log_rows = {}

    # ---------------- heights: roof edge of every solid = max of the top surface on a ring 0.12 m inside its roof outline
    def edge_top(s, inset=0.12, step=4.0, excl=()):
        zs = []
        for p in G.polys_of(s.roof):
            ring = p.exterior
            for d_ in np.arange(0, ring.length, step):
                q = ring.interpolate(d_)
                # inward point
                q2 = ring.interpolate(d_ + 0.05)
                tx, ty = q2.x - q.x, q2.y - q.y; L = math.hypot(tx, ty) or 1
                nx, ny = -ty / L, tx / L             # left of the CCW ring = inside
                X, Y = q.x + nx * inset, q.y + ny * inset
                if any(e.buffer(0.3).contains(Point(X, Y)) for e in excl): continue
                z = TP.z(X, Y)
                if z is not None: zs.append(z)
        return np.array(zs)
    drawn_h = [
        ('BA_B_body', 'bab.h_roof', 'obs (S half; N inf)'), ('BA_B_band', 'bab.h_roof_central', 'obs, low'), ('BA_C_body', 'bac.h_roof', 'obs, low'),
        ('BA_D_body', 'bad.h_roof', 'obs, low'), ('BA_E_centre', 'bae.h_roof', 'obs'), ('BA_E_body', 'BA-E lower side roofs = fascia - BAE_STEP', 'inf'),
        ('BA_F_body', 'baf.h_roof_ne_arm', 'obs'), ('BA_F_lantern', 'hub lantern: roof + 1.0 minimal upstand (bound 4.6)', 'unk'),
        ('BA_F_monitor', 'NW-arm monitor: roof + 2.5', 'unk'), ('BA_D_drum0', 'BAD_DRUM_TOP', 'inf'), ('BA_D_drum1', 'BAD_DRUM_TOP', 'inf'),
        ('T1_hall', 'curb 4.88 + wall head 13.0 (BD-03 v1)', 'unk / inf'), ('T2_hall', 'curb 4.88 + 12.0 (BD-03 v2)', 'unk'),
        ('T3W_hall', 'T3W parapet 66\'-0" - L1 (BD-02 / BD-03 v3)', 'pub / inf'), ('T3E_hall', 'R2 58\'-6" - L1', 'inf'),
        ('T3E_penthouse', 'R3 81\'-0" - L1', 'inf'), ('C3C_block', 'C3C: six office storeys above the connector (HOK) / NAIP relief / photo a1', 'inf')]
    heights = {}
    for key, src, tag in drawn_h:
        s = sol.get(key)
        if s is None: continue
        # exclude where a taller solid stands on / against the edge (its own top would be probed)
        excl = [o.poly for o in W.S if o is not s and o.h > s.h + 0.05 and o.poly.distance(s.roof) < 0.5]
        zs = edge_top(s, excl=excl)
        if not len(zs): continue
        med = float(np.median(zs)); p10, p90 = np.percentile(zs, [10, 90])
        heights[key] = dict(median=round(med, 3), p10=round(float(p10), 3), p90=round(float(p90), 3), n=len(zs))
        C.add(f'{key}: roof edge top (median of {len(zs)} probes, p10 {p10:.2f} / p90 {p90:.2f})', med, s.h, src=f'{src} [{tag}]', group='heights')

    # ---------------- BA-B section at every 10 m along the straight pier (BD-02 view 1, dom_bab_band.json)
    bS_E, bS_W, tS, tN = G.BB_S_E, G.BB_S_W, G.BB_T_S, G.BB_T_N
    oE, oW = DD.BAB_OUTER_S
    hmid = 0.5 * (G.H['B'] + G.H['B_band'])
    rows = []
    for tt in np.arange(tS + 10, tN - 5, 10.0):
        prof = []
        for ss in np.arange(oW - 6, oE + 6, 0.1):
            X, Y = st_local(ss, tt)
            z = TP.z(X, Y)
            prof.append((ss, -1.0 if z is None else z))
        P = np.array(prof)
        hi = P[P[:, 1] > hmid]; lo = P[P[:, 1] > G.H["B"] - 1.5]          # above the elevated walkways (10.5 m)
        if not len(hi) or not len(lo): continue
        rows.append((tt, hi[:, 0].min(), hi[:, 0].max(), lo[:, 0].min(), lo[:, 0].max()))
    R = np.array(rows)
    if len(R):
        south = R[:, 0] < -1150          # the typical section applies south of t -1150 (BD-02 / README: 7.3 / 32.4 / 14.7 m), where
                                         # the outer edges were measured (BAB_OUTER_S, the bab.roof_edges lines t -1238..-1176)
        for k, (nm, drawn, tag) in enumerate((('band WNW edge s', bS_W, 'obs N half / inf S'), ('band ESE edge s', bS_E, 'obs'),
                                              ('outer WNW roof edge s (t < -1150)', oW, 'obs'), ('outer ESE roof edge s (t < -1150)', oE, 'obs'))):
            v = R[:, k + 1] if k < 2 else R[south, k + 1]
            dev = np.abs(v - drawn)
            C.add(f'BA-B {nm}: max |dev| over {len(v)} stations (every 10 m, t {R[0, 0]:.0f}..{R[-1, 0]:.0f})', float(drawn + dev.max() * np.sign((v - drawn)[dev.argmax()])),
                  drawn, 0.5, f'dom_bab_band.json / BAB_OUTER_S [{tag}]', group='BA-B section')
        widths = dict(ese_strip=(R[south, 4] - R[south, 2]).mean(), band=(R[:, 2] - R[:, 1]).mean(), wnw_strip=(R[south, 1] - R[south, 3]).mean(),
                      total=(R[south, 4] - R[south, 3]).mean())
        for nm, drawn in (('ese_strip', 7.3), ('band', 32.4), ('wnw_strip', 14.7), ('total', 54.3)):
            C.add(f'BA-B width {nm} (mean over the stations)', widths[nm], drawn, src='BD-02 view 1 widths [obs / inf]', group='BA-B section')

    # ---------------- measured lean-free roof-edge lines (BA-B south half, BA-D, BA-F): mesh roof edge vs the line
    for L_, key, cfg in (('B', 'BA_B_body', ('bab.roof_edges', 'ba_b_south')), ('D', 'BA_D_body', ('bad.roof_edges', 'ba_d_head')),
                         ('F', 'BA_F_body', ('baf.roof_edges', 'ba_f_ne_arm'))):
        lines = D.dom_true_edges(*cfg)
        s = sol[key]
        notches = unary_union([d['notch'] for d in info['doors'] if d.get('notched')] or [Polygon()])
        for side, (p0, p1) in lines.items():
            a = np.array(G.Lp(*p0)); bq = np.array(G.Lp(*p1))
            hd = math.radians(117.83 if side == 'n' else 297.83)          # outward: ESE for the 'n' line, WNW for 'm'
            dl = (bq - a) / np.hypot(*(bq - a)); nrm = np.array([-dl[1], dl[0]])
            if np.dot(nrm, [math.sin(hd), math.cos(hd)]) < 0: nrm = -nrm
            devs = []
            for f in np.linspace(0.05, 0.95, 19):
                q = a + (bq - a) * f
                if notches.distance(Point(*q)) < 1.0: continue      # door notches of the overhang (bridges below a low roof)
                last = None
                for o in np.arange(-6, 6, 0.05):
                    z = TP.z(*(q + nrm * o))
                    if z is not None and abs(z - s.h) < 0.05: last = o
                if last is not None: devs.append(last)
            if devs:
                dv = np.array(devs)
                C.add(f'{key}: roof edge vs the measured lean-free {"ESE" if side == "n" else "WNW"} line (max |offset|, {len(dv)} stations)',
                      float(dv[np.abs(dv).argmax()]), 0.0, 0.5, f'spec {cfg[0]} / draw_data.dom_true_edges [obs]', group='roof edges')

    # BA-F NE arm section width (BD-02 view 1: 27.0 m between the lean-free edges): mesh roof edges across the arm at the middle
    # 60 % of the measured lines
    Lf = D.dom_true_edges('baf.roof_edges', 'ba_f_ne_arm')
    a = np.array(G.Lp(*Lf['n'][0])); bq = np.array(G.Lp(*Lf['n'][1])); dl = (bq - a) / np.hypot(*(bq - a))
    nrm = np.array([-dl[1], dl[0]])
    if np.dot(nrm, [math.sin(math.radians(117.83)), math.cos(math.radians(117.83))]) < 0: nrm = -nrm
    wsF = []
    for f in np.linspace(0.2, 0.8, 7):
        q = a + (bq - a) * f
        hit = [o for o in np.arange(-34, 6, 0.05) if (lambda z: z is not None and abs(z - G.H['F']) < 0.05)(TP.z(*(q + nrm * o)))]
        if hit: wsF.append(max(hit) - min(hit))
    if wsF:
        C.add(f'BA-F NE arm roof width (median of {len(wsF)} sections)', float(np.median(wsF)), 27.0, src='BD-02 view 1: 27.0 m between the lean-free edges [obs]',
              group='roof edges')

    # ---------------- BA-E stepped section (BD-02 bae_section)
    # sections across the straight north part (heading 27.83): every 5 m over the middle 60 % of the raised plate's length
    sE, sC_ = sol['BA_E_body'], sol['BA_E_centre']
    ax = np.array([math.sin(math.radians(27.83)), math.cos(math.radians(27.83))])     # local direction of t
    nE = np.array([ax[1], -ax[0]])
    Pc = np.array(sC_.poly.exterior.coords); kk = Pc @ ax
    c0 = np.array(sC_.poly.centroid.coords[0]); k0 = float(c0 @ ax)
    WT, WL, TOP, SIDE = [], [], [], []
    for kq in np.linspace(kk.min() + 0.2 * np.ptp(kk), kk.max() - 0.2 * np.ptp(kk), 13):
        base = c0 + ax * (kq - k0)
        prof = []
        for o in np.arange(-45, 45, 0.1):
            z = TP.z(*(base + nE * o)); prof.append((o, -1 if z is None else z))
        P = np.array(prof)
        top = P[np.abs(P[:, 1] - G.H['E']) < 0.3]; low = P[np.abs(P[:, 1] - G.H['E_flank']) < 0.3]
        allr = P[P[:, 1] > G.H['E_flank'] - 0.6]
        if not len(top) or not len(low): continue
        # contiguous run around the plate centre
        WT.append(top[:, 0].max() - top[:, 0].min()); WL.append(allr[:, 0].max() - allr[:, 0].min())
        TOP.append(np.median(top[:, 1])); SIDE.append(np.median(low[:, 1]))
    if WT:
        C.add(f'BA-E raised plate top (median of {len(TOP)} sections)', float(np.median(TOP)), G.H['E'], src='bae.h_roof 12.85 (tapered fascia) [obs]', group='BA-E')
        C.add(f'BA-E lower side roof top (median of {len(SIDE)} sections)', float(np.median(SIDE)), G.H['E_flank'], src='fascia - BAE_STEP 3.0 [inf, photo a1]', group='BA-E')
        C.add('BA-E total roof width (median of the sections)', float(np.median(WL)), 42.9, src='BD-02 (research 5.3, 42.9 m) [inf]', group='BA-E')
        C.add('BA-E raised plate width (median of the sections)', float(np.median(WT)), 42.9 - 2 * DD.BAE_FLANK + 2 * DD.BAE_OVER,
              src='width - 2 x flank 4.4 + 2 x overhang 1.5 [inf]', group='BA-E')

    # ---------------- BA-F lantern / BA-D drums (plan, from the mesh: top-surface extent)
    lan = sol['BA_F_lantern']; lc = np.array(G.Lp(*DD.baf_lantern_centre()))
    ext = []
    for k in range(8):
        a = math.radians(343.0 + 45 * k + 22.5)       # across the flats: the flat normals are n0 + 45 k (octagon(), n0 343)
        d_ = np.array([math.sin(a), math.cos(a)])
        last = None
        for o in np.arange(0, 16, 0.05):
            z = TP.z(*(lc + d_ * o))
            if z is not None and z > G.H['F'] + 0.5: last = o
        ext.append(last or 0.0)
    across = [ext[k] + ext[(k + 4) % 8] for k in range(4)]
    C.add('BA-F lantern width across (mean of 4 axes, vertex directions)', float(np.mean(across)), 2 * DD.BAF_LANTERN_APO[0] / math.cos(math.radians(22.5)),
          src='octagon 19.4 m across the flats [obs NAIP] -> across the corners', group='BA-F / BA-D')
    for k, (c, r) in enumerate(DD.BAD_DRUMS_IMG):
        dr = sol[f'BA_D_drum{k}']
        cl = np.array(dr.poly.centroid.coords[0])
        exp = np.array(G.Lp(c[0] - float(D.dom_lean('D')[0][0]) * DD.BAD_DRUM_TOP, c[1]))
        # radius from the mesh: top surface above the BA-D roof along 8 rays
        rs = []
        for a in np.linspace(0, 2 * math.pi, 8, endpoint=False):
            d_ = np.array([math.cos(a), math.sin(a)]); last = None
            for o in np.arange(0, 14, 0.05):
                z = TP.z(*(exp + d_ * o))
                if z is not None and z > G.H['D'] + 1.0: last = o
            if last is not None: rs.append(last)
        C.add(f'BA-D drum {k} radius (8 rays from the drawn centre)', float(np.mean(rs)) if rs else 0.0, r, src='BAD_DRUMS_IMG D 19.2 [obs, low]', group='BA-F / BA-D')

    # ---------------- T3 / T1 facades: material bands on the walls
    def band_z(names, mats, lod=0):
        T = tris_of(S, names, mats, lod)
        if not len(T): return None
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        vert = np.abs(n[:, 2]) < 1e-6 * np.linalg.norm(n, axis=1) + 1e-9
        Z = T[vert][:, :, 2]
        return Z.min(), Z.max(), Z
    z = band_z(['L0_T3W_shell'], ['panel_acm_dark'])
    if z:
        Zs = np.unique(np.round(z[2], 2))
        lv = DD.T3_LV
        exp = [lv['L3'] + 10 * G.FT, lv['L3'] + 12 * G.FT]
        got = [Zs[np.abs(Zs - e).argmin()] for e in exp]
        for e, g_, nm in zip(exp, got, ('L3 + 10 ft (glass head)', 'L3 + 12 ft (band top)')):
            C.add(f'T3W airside window stack: {nm}', float(g_), e, src='t3w.wall_field 10 + 2 + 10 ft above L3 [pub]', group='T3 / T1')
    z = band_z(['L0_T3W_shell'], ['glass_ec'])
    if z:
        C.add('T3W airside glazing bottom = L3 (34 ft above L1)', float(np.unique(np.round(z[2], 2))[np.abs(np.unique(np.round(z[2], 2)) - DD.T3_LV['L3']).argmin()]),
              DD.T3_LV['L3'], src='CDR L3 45\'-0" - L1 11\'-0" [pub / inf]', group='T3 / T1')
    z = band_z(['L0_T1_shell'], ['glass_frit_green'])
    if z:
        C.add('T1 landside fritted tiers: bottom (canopy line)', float(z[0]), G.T1_CANOPY_H, src='curb 4.88 [unk] + canopy 4.0 [inf photo d1]', group='T3 / T1')
        C.add('T1 landside fritted tiers: top (slab underside below the 17.88 edge)', float(z[1]), G.H['T1'] - G.ROOF_THK, src='wall head 13.0 above the curb [inf photo d1] - 0.8 slab', group='T3 / T1')
    T = tris_of(S, ['L0_T1_shell'], ['soffit'])
    if len(T):
        Zs = T[:, :, 2]
        nz = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])[:, 2]
        can = Zs[(nz < 0) & (np.abs(Zs.mean(1) - G.T1_CANOPY_H) < 0.3)]
        if len(can):
            C.add('T1 curb canopy soffit height', float(np.median(can)), G.T1_CANOPY_H, src='curb 4.88 [unk] + 4.0 [inf photo d1]', group='T3 / T1')
    CP = TopProbe(tris_of(S, ['L0_T1_shell'], ['glass_canopy']))
    deps = []
    s1 = sol['T1_hall']
    for ring in G.M.rings_of(s1.poly):
        for i in range(len(ring)):
            a, b2 = np.array(ring[i]), np.array(ring[(i + 1) % len(ring)])
            Ln = float(np.hypot(*(b2 - a)))
            if Ln < 8 or not G.is_landside(tuple(a), tuple(b2)): continue
            dl = (b2 - a) / Ln; nrm = np.array([dl[1], -dl[0]])
            q = (a + b2) / 2
            if CP.z(*(q + nrm * 0.5)) is None: continue
            last = 0.0
            for o in np.arange(0.05, 8, 0.05):
                if CP.z(*(q + nrm * o)) is not None: last = o
            deps.append(last)
    if deps:
        C.add(f'T1 curb canopy depth from the facade (median of {len(deps)} faces)', float(np.median(deps)), G.T1_CANOPY_D,
              src='T1_CANOPY_D 4.0 (NAIP roof edge 3-6 m inside the trimmed curb) [inf]', group='T3 / T1')
    # landside run lengths of the T1 face (BD-03 view 1 developed along the SFO Museum outline - the 3-D facade stands on the
    # measured roof edge, behind the curb roadway that the SFO Museum outline includes there: reported, not a pass / fail)
    s = sol['T1_hall']
    runs = {'east': 0.0, 'west': 0.0}
    for ring in G.M.rings_of(s.poly):
        for i in range(len(ring)):
            a, b2 = ring[i], ring[(i + 1) % len(ring)]
            Ln = math.hypot(b2[0] - a[0], b2[1] - a[1])
            if Ln < 0.5 or not G.is_landside(a, b2): continue
            mx, mz = G.Wp((a[0] + b2[0]) / 2, (a[1] + b2[1]) / 2)
            if 380 < mz < 470 and -1010 < mx < -795:
                runs['west' if mx < -890 else 'east'] += Ln
    for k_, drawn in (('east', DD.T1_RUNS[0]), ('west', DD.T1_RUNS[2])):
        C.add(f'T1 landside face, {k_} run length (INFO: BD-03 develops along the SFO Museum outline on the curb roadway)', runs[k_], drawn,
              None, 'SFO Museum outline [obs]; the 3-D face = trimmed curb line - 4.0 m (NAIP 2024 roof edge) [inf]', ok=True, group='T3 / T1')

    # ---------------- footprints vs SFO Museum outlines
    fp0 = footprint(S, 0)
    fp_walls = footprint(S, 0, zband=(0.5, 5.0))          # what stands at grade (walls of the apron level)
    outl = unary_union([G.CX] + [G.PIER_POLY[L_] for L_ in 'BCDEF'])
    out_area = fp_walls.difference(outl.buffer(0.05)).area
    C.add('apron-level walls (0.5-5 m) outside the SFO Museum outlines (bridge vestibules excluded)', out_area, 0.0, None, 'm2: the vestibules '
          'reach from the facade to the app walkway start (bridges)', ok=True, unit='m2', group='footprints')
    over = fp0.difference(outl.buffer(0.05))
    C.add('LOD0 plan area outside the SFO Museum outlines (roof overhangs, canopy, vestibules)', over.area, 0.0, None,
          'BA-B / BA-D ESE overhangs +2.3 / +2.4 m [obs], T1 canopy 4 m [inf], vestibules [inf]', ok=True, unit='m2', group='footprints')

    # ---------------- plausibility
    plaus = {}
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'stands'))
    import geom as GM
    st = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))['stands']
    worst = []
    fp_low = footprint(S, 0, zband=(0.0, 20.0))
    for s_ in st:
        if s_['letter'] not in 'BCDEF': continue
        env = GM.stand_env(s_)
        dd = env.distance(fp0)
        worst.append((dd, s_['name'], env))
    worst.sort()
    dmin, name_min, env_min = worst[0]
    # 3-D: where an envelope comes within 2 m in plan, what is there (lowest underside of the geometry within 2 m)
    close = []
    for dd, nm, env in worst:
        if dd >= 2.0: break
        near = fp0.intersection(env.buffer(2.0))
        close.append(dict(stand=nm, plan_m=round(dd, 2), near_m2=round(near.area, 2)))
    plaus['stand_min_plan_m'] = round(dmin, 2); plaus['stand_min'] = name_min; plaus['stands_within_2m'] = close
    C.add(f'B-F stand envelopes: min plan distance to the 3-D footprint ({name_min}; app planforms, all accepted types)', dmin, 2.0,
          None, 'check_stands.py criterion >= 2.0 m vs the SFO Museum outline; listed below if < 2 m', ok=dmin >= 0.0, group='plausibility')
    for c in close:
        C.add(f'  stand {c["stand"]} within 2 m of the 3-D footprint', c['plan_m'], 2.0, None,
              'pre-existing (stand data vs SFO Museum outline) unless the near part is a 3-D addition', ok=c['plan_m'] > 0.0, group='plausibility')
    # bridges: the app's fixed walkway solids (js/live/gates.js solidsQ rest, tools/blender/app_bridges.json: per-pier
    # DEPARTURE_LEVELS and the 1:12 slope to the rotunda) vs the 3-D triangles inside EACH SOLID'S OWN height band (close-out r3
    # fix 2: was one plan footprint of the 4.8-8.7 m band, i.e. the one 5.4-m level for every pier)
    import app_bridges as AB
    from shapely.ops import substring
    TW = np.concatenate([p['P'][p['T']] for n_, m_ in S.items() if m_['lod'] == 0 for p in m_['prims']])
    TW = TW.copy(); TW[:, :, 1] -= GROUND_Y
    tlo = TW[:, :, [0, 2]].min(1); thi = TW[:, :, [0, 2]].max(1); tylo = TW[:, :, 1].min(1); tyhi = TW[:, :, 1].max(1)

    def band_area(g, y0, y1):
        """plan area of the triangles' parts between y0 and y1 (above the apron) inside g (vertical faces as 5-cm strips)."""
        if g.is_empty: return 0.0
        x0, z0, x1, z1 = g.bounds
        m = (thi[:, 0] > x0) & (tlo[:, 0] < x1) & (thi[:, 1] > z0) & (tlo[:, 1] < z1) & (tyhi > y0) & (tylo < y1)
        out = []
        for t in TW[m]:
            poly = [tuple(v) for v in t]
            for lim, keep in ((y0, lambda v: v[1] >= y0), (y1, lambda v: v[1] <= y1)):
                res = []
                for k in range(len(poly)):
                    a, b_ = poly[k], poly[(k + 1) % len(poly)]
                    if keep(a): res.append(a)
                    if keep(a) != keep(b_):
                        f = (lim - a[1]) / (b_[1] - a[1]); res.append(tuple(a[q] + f * (b_[q] - a[q]) for q in range(3)))
                poly = res
                if not poly: break
            if len(poly) < 3: continue
            xz = [(v[0], v[2]) for v in poly]; P_ = Polygon(xz)
            if P_.is_valid and P_.area > 1e-4: out.append(P_)
            else:
                xs = np.array(xz); dm = np.linalg.norm(xs[:, None] - xs[None], axis=2); a, b_ = np.unravel_index(dm.argmax(), dm.shape)
                if dm[a, b_] > 0.02: out.append(LineString([xz[a], xz[b_]]).buffer(0.025, cap_style=2))
        return unary_union(out).intersection(g).area if out else 0.0

    def solids_of(stand, door):
        b_ = AB.bridge(stand, door, False)
        if b_ is None: return []
        return [(Polygon(P_), lo_ + 0.03, hi_ - 0.03) for P_, lo_, hi_ in AB.walkway_slices(b_, 1.0)]   # 1-m slices, local band
    ab_stale = AB.stale()
    C.add('app bridge dump (tools/blender/app_bridges.json) matches the current js/live/gates.js / stands inputs',
          ', '.join(ab_stale) or 'current', 'current', None, 're-run node tools/blender/app_bridges.mjs when it lists a file',
          ok=not ab_stale, group='plausibility')
    hits, nb, contacts = [], 0, []
    doors = {(d['stand'], d['gate'], d['door']): d for d in info['doors']}
    for s_ in st:
        if s_['letter'] not in 'BCDEF': continue
        for br in s_['bridges']:
            w = br.get('walk') or []
            if len(w) < 2: continue
            nb += 1
            d = doors.get((s_['name'], br.get('gate'), br.get('door')))
            ln = LineString(w)
            # the walkway as drawn by the app starts at E; where E lies inside the 3-D facade it emerges at the facade X; bridges
            # that attach INTO an elevated sky-bridge / pod part (walk[0] inside it) emerge where they leave that part; the first
            # 1.5 m beyond are the attachment (door frame / vestibule end / the stand data's own contact with the outline, as in
            # verify_itb.py) and are listed separately
            s0 = 0.0
            if d:
                s0 = max(ln.project(Point(G.Wp(*d['E']))), ln.project(Point(G.Wp(*d['X']))))
            host = [o for o in W.S if o.poly.contains(Point(G.Lp(*w[0])))]
            if host:
                hp = unary_union([o.poly for o in host])
                for sd in np.arange(0, ln.length, 0.1):
                    q = ln.interpolate(sd)
                    if not hp.contains(Point(G.Lp(q.x, q.y))): s0 = max(s0, sd); break
            SB = solids_of(s_['name'], br.get('door'))
            near = substring(ln, s0, min(ln.length, s0 + 1.5)).buffer(GM.WALK_W / 2 + 0.05, cap_style=2) if ln.length - s0 > 0.05 else Polygon()
            an = sum(band_area(g.intersection(near), y0, y1) for g, y0, y1 in SB) if not near.is_empty else 0.0
            if an > 0.05: contacts.append((s_['name'], br.get('gate'), br.get('door'), round(an, 2)))
            s0 += 1.5
            if ln.length - s0 < 0.5: continue
            seg = substring(ln, s0, ln.length).buffer(GM.WALK_W / 2 + 0.05, cap_style=2)
            a = sum(band_area(g.intersection(seg), y0, y1) for g, y0, y1 in SB)
            if a > 0.05: hits.append((s_['name'], br.get('gate'), br.get('door'), round(a, 2)))
    plaus['bridge_walkway_hits'] = hits
    plaus['bridge_attach_contacts'] = contacts
    C.add(f'bridge attachments: walkway first 1.5 m beyond the facade touching 3-D geometry ({len(contacts)} bridges; INFO)',
          float(sum(c[3] for c in contacts)), 0.0, None, 'door frames / vestibule ends / walkways meeting the facade at an angle '
          '(stand data vs SFO Museum outline, as the ITB rotunda contacts)', unit='m2', ok=True, group='plausibility')
    C.add(f'bridge walkways (app solids beyond facade + 1.5 m) overlapping 3-D geometry in their own height band ({nb} bridges)', float(sum(h[3] for h in hits)), 0.0, 0.5,
          'gates.js fixed-walkway solids (WALK_W 2.6, floor - 0.3 .. + WALK_H 3.0) at the pier DEPARTURE_LEVELS (B 5.4, C 3.2, D 3.65, '
          'E / F 4.88), tools/blender/app_bridges.json', unit='m2', group='plausibility')
    tw = unary_union([Polygon(p[0], p[1:]).buffer(0) for t_ in D.AIR['taxiways'] for p in t_['polys']])
    C.add('SFO Museum taxiway polygons inside the 3-D footprint', tw.intersection(fp0).area, 0.0, 0.5, 'data/sfo_airport.json taxiways', 'm2', group='plausibility')
    C.add('tower base-building exclusion inside the 3-D footprint', G.TOWER_EXCL.intersection(fp0).area, 0.0, 0.5,
          'manifest.json#tower.integration.exclusion_footprint_world', 'm2', group='plausibility')
    itb = G.ITB
    C.add('ITB outline (the ITB asset) inside the 3-D footprint', itb.intersection(fp0).area, 0.0, 0.5, 'SFO Museum ITB + BA-A / BA-G', 'm2', group='plausibility')
    rail = G.RAIL
    C.add('AirTrain guideway (SFO Museum "AirTrain Rail") inside the 3-D footprint', rail.intersection(fp0).area, 0.0, 1.0,
          'cut out of the T1 hall / canopy (+1 m)', 'm2', group='plausibility')
    # vestibules abut the app walkway start
    gaps = [d['head']['gap_max'] for d in info['doors'] if (d.get('head') or {}).get('kind') == 'vestibule']
    plaus['doors'] = dict(n=len(info['doors']), vestibules=len(gaps), max_gap_bridged_m=round(max(gaps), 2) if gaps else 0.0,
                          nubs=sum(1 for d in info['doors'] if (d.get('head') or {}).get('kind') == 'nub'),
                          bulkheads=sum(1 for d in info['doors'] if d['low']))
    # close-out round 4: walkway-end gap check (tools/blender/walkend_check.py) - every app walkway that starts at a domestic
    # facade is closed by the asset (facade / vestibule / nub, or its own drum) over its full width at floor + 0.3 / 1.5 / 2.7 m,
    # at every LOD of this file and of the phone-tier domestic_lod2.glb; F22 L2 starts 17.6 m from any building (fed from F22
    # L1's rotunda: a bridges-data matter, listed as exempt)
    import walkend_check as WK
    exempt = {('F22', 2, False): 'walkway starts 17.6 m from BA-F, 1.5 m from F22 L1\'s drum (bridge data: L2 fed from L1\'s rotunda), not at a building'}
    Tl = {l: WK.tris_from_scene(S, l) for l in sorted({m['lod'] for m in S.values() if m['lod'] is not None})}
    l2p = os.path.join(os.path.dirname(path), os.path.basename(path).replace('.glb', '_lod2.glb'))
    if os.path.exists(l2p) and l2p != path:
        j2_, b2_, _ = load_glb(l2p); S2_ = scene_meshes(j2_, b2_)
        Tl['lod2_glb'] = WK.tris_from_scene(S2_, 2)
    we = WK.run(Tl, 'BCDEF', exempt)
    plaus['walkway_end_gaps'] = {str(k): v for k, v in we.items()}
    plaus['walkway_end_gaps_summary'] = {str(k): dict(n=v['n'], n_fail=v['n_fail'], max_gap=v['max_gap'], exempt=[e['stand'] + ' L%d' % e['door'] for e in v['exempt']])
                                         for k, v in we.items()}
    for k, v in we.items():
        C.add('walkway ends closed by the asset (gap <= %.2f m over the full width at floor + 0.3 / 1.5 / 2.7) - %s: %d of %d open%s' %
              (WK.GAP_MAX, 'LOD%d' % k if isinstance(k, int) else 'domestic_lod2.glb', v['n_fail'], v['n'],
               (': ' + ', '.join('%s L%d' % (f['stand'], f['door']) for f in v['fails'][:8])) if v['fails'] else ''),
              v['n_fail'], 0, ok=v['n_fail'] == 0, src='app_bridges.json walk[0] (gates.js); max gap %s m; exempt: %s' %
              (v['max_gap'], ', '.join(e['stand'] + ' L%d' % e['door'] for e in v['exempt']) or 'none'), unit='', group='plausibility')

    # close-out round 5 (verifier: the round-4 drum notches put the facade fins back where short walkways leave the building -
    # 21 -> 27 contact sets; and new same-facing coplanar faces at the BA-C door heads / BA-B door jambs): (1) LOD0 mullion fins
    # inside an app fixed walkway solid (app_bridges.json rest segments, separating-axis test shrunk 0.02 m) - 0 allowed;
    # (2) same-facing coplanar overlapping faces (plane within 5 mm, normals within 2 deg) between each pier's detail node and
    # the other nodes of that building at LOD0 - 0 allowed
    try:
        import app_bridges as AB

        def _sat(T, c, u, hl, hw, lo, hi, shrink=0.02):
            v = np.array([-u[1], u[0]])
            ax = [np.array([u[0], 0, u[1]]), np.array([0, 1.0, 0]), np.array([v[0], 0, v[1]])]
            h = np.array([hl - shrink, (hi - lo) / 2 - shrink, hw - shrink])
            Pl = np.stack([(T - np.array([c[0], (lo + hi) / 2, c[1]])) @ a for a in ax], -1)
            ok = np.ones(len(T), bool)
            for k in range(3): ok &= ~((Pl[:, :, k].min(1) > h[k]) | (Pl[:, :, k].max(1) < -h[k]))
            e = [Pl[:, 1] - Pl[:, 0], Pl[:, 2] - Pl[:, 1], Pl[:, 0] - Pl[:, 2]]
            nn = np.cross(e[0], e[1]); ok &= np.abs((nn * Pl[:, 0]).sum(-1)) <= (np.abs(nn) * h).sum(-1)
            for ei in e:
                for k in range(3):
                    a = np.cross(np.eye(3)[k][None], ei); pr = np.einsum('nj,nij->ni', a, Pl); r = (np.abs(a) * h).sum(-1)
                    ok &= ~((pr.min(1) > r) | (pr.max(1) < -r))
            return ok
        fin_hits = {}
        for n, m in S.items():
            if m['lod'] != 0 or not n.endswith('_fins'): continue
            T = np.concatenate([p['P'][p['T']] for p in m['prims']]); cen = T[:, :, [0, 2]].mean(1)
            for b_ in AB.bridges('ABCDEFG'):
                for so in b_['rest']:
                    if so['part'] != 'walkway': continue
                    R_ = so['hl'] + so['hw'] + 3
                    mm = (np.abs(cen[:, 0] - so['c'][0]) < R_) & (np.abs(cen[:, 1] - so['c'][1]) < R_)
                    if not mm.any(): continue
                    hh = _sat(T[mm], so['c'], np.array(so['u'], float), so['hl'], so['hw'], so['lo'] + GROUND_Y, so['hi'] + GROUND_Y)
                    if hh.any(): fin_hits['%s L%d seg %s' % (b_['stand'], b_['door'], so.get('seg'))] = int(hh.sum())
        plaus['fins_in_app_walkways'] = fin_hits
        C.add('LOD0 mullion fins inside the app fixed walkway solids (%d bridges)' % len(fin_hits), sum(fin_hits.values()), 0, ok=not fin_hits,
              unit='tris', src='app_bridges.json rest walkway segments (gates.js); dom_geom.fin_spans cuts the fins round them: %s' % (fin_hits or 'none'),
              group='plausibility')

        def _nrm(T):
            nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); L_ = np.linalg.norm(nn, axis=1); return nn / np.where(L_ > 0, L_, 1)[:, None], L_

        def _inside(p_, t):
            v0, v1, v2 = t[2] - t[0], t[1] - t[0], p_ - t[0]
            d00, d01, d02, d11, d12 = v0 @ v0, v0 @ v1, v0 @ v2, v1 @ v1, v1 @ v2
            den = d00 * d11 - d01 * d01
            if abs(den) < 1e-12: return False
            uu = (d11 * d02 - d01 * d12) / den; vv = (d00 * d12 - d01 * d02) / den
            return uu > 0.01 and vv > 0.01 and uu + vv < 0.99
        cop = {}
        for bld in ('BA_B', 'BA_C', 'BA_D', 'BA_E', 'BA_F'):
            dn = 'L0_%s_detail' % bld
            if dn not in S: continue
            A_ = np.concatenate([p['P'][p['T']] for p in S[dn]['prims']])
            Bl = [(n, np.concatenate([p['P'][p['T']] for p in m['prims']])) for n, m in S.items() if m['lod'] == 0 and n != dn and n.startswith('L0_%s_' % bld)]
            if not Bl: continue
            B_ = np.concatenate([t for _, t in Bl]); BN = np.concatenate([[n] * len(t) for n, t in Bl])
            nA, LA = _nrm(A_); nB, LB = _nrm(B_); cA = A_.mean(1); cB = B_.mean(1)
            hits_ = []
            for i in range(len(A_)):
                if LA[i] < 1e-8: continue
                near = np.nonzero((np.abs(cB - cA[i]) < 15).all(1) & (LB > 1e-8))[0]
                if not len(near): continue
                near = near[(nB[near] * nA[i]).sum(1) > np.cos(np.radians(2))]
                if not len(near): continue
                near = near[np.abs(((cA[i] - B_[near][:, 0]) * nB[near]).sum(1)) < 0.005]
                for k in near:
                    if _inside(cA[i], B_[k]) or _inside(cB[k], A_[i]): hits_.append((BN[k], tuple(np.round(cA[i], 1))))
            if hits_: cop[dn] = dict(n=len(hits_), with_=sorted({h[0] for h in hits_}), at=[h[1] for h in hits_[:6]])
        plaus['coplanar_same_facing_detail'] = cop
        C.add('LOD0 same-facing coplanar overlapping faces, pier detail nodes vs their building (z-fight)', sum(v['n'] for v in cop.values()), 0, ok=not cop,
              unit='pairs', src='plane within 5 mm, normals within 2 deg, centroid inside the other face: %s' % (cop or 'none'), group='plausibility')
    except Exception as e:  # noqa: BLE001
        C.add('fins vs walkways / coplanar detail faces', str(e), 'error', ok=False, group='plausibility')

    # close-out round 4 (verifier r3 v9): back-face first hits (tools/blender/bf_rays.py) at LOD0 and LOD2 in NEAR mode (context
    # occludes only within 10 m in front of the asset). Round 4 found pre-existing see-through on T3W / T1 / T3E that the far
    # context of round 3 hid (identical in the r3 fix-2 file and this one: not from the bridge heads) - recorded as residuals at
    # their measured counts (a regression above them fails), to be traced in the next round; other nodes: <= 60 (landside gate)
    # close-out round 5: traced - every T1 / T3W / T3E hit was a ray through the ITB core into a hall left open at its junction
    # with the ITB (dom_geom: the ITB occupancy hid those walls); the junction is now closed by the domestic asset itself
    # (emit_walls closure walls) - the round-4 residuals are dropped, per node <= 60 as the landside gate; the LOD2 file is ONE
    # node (L2_domestic: all buildings), so it gets the sum of the per-building remainders measured on the geometry module
    # (BA-B 31 / BA-E 24 / T1 22 / T3E 4 / BA-C 1 / BA-F 1 = 83) + 5 %
    DOM_BF_RESIDUAL = {'L2_domestic': 88}
    try:
        import bf_rays as BF
        D3_ = os.path.join(ROOT, 'data', 'buildings3d')
        l2p_ = os.path.join(os.path.dirname(path), os.path.basename(path).replace('.glb', '_lod2.glb'))
        bfr = {}
        for lod_, own_, ctx_ in ((0, path, ('itb.glb', 'tower.glb', 'roadways.glb')), (2, l2p_ if os.path.exists(l2p_) else path, ('itb_lod2.glb', 'tower_lod2.glb', 'roadways_lod2.glb'))):
            r_ = BF.near_summary(own_, [os.path.join(D3_, c) for c in ctx_], lod=lod_)
            bfr['lod%d' % lod_] = r_
            over = {k: v for k, v in r_['per_node'].items() if v > max(BF.NODE_MAX, int(DOM_BF_RESIDUAL.get(k, 0) * 1.05))}
            C.add('LOD%d back-face first hits, near context %.0f m (worst %s; residuals %s)' % (lod_, r_['near_m'], r_['worst'],
                  {k: r_['per_node'].get(k, 0) for k in DOM_BF_RESIDUAL if k.startswith('L%d' % lod_)}), r_['total'], 0, ok=not over, unit='hits',
                  src='bf_rays.py near mode; per node <= 60 (merged LOD2 node: <= 1.05 x the recorded close-out r5 sum); over: %s' % (over or 'none'), group='plausibility')
        plaus['backface_near'] = bfr
    except Exception as e:  # noqa: BLE001
        C.add('back-face near-context rays', str(e), 'error', ok=False, group='plausibility')

    # ---------------- budget
    tris, calls = {}, {}
    for n, m in S.items():
        tris[m['lod']] = tris.get(m['lod'], 0) + sum(len(p['T']) for p in m['prims'])
        calls[m['lod']] = calls.get(m['lod'], 0) + len(m['prims'])
    imgs = [dict(name=im.get('name'), mime=im.get('mimeType'), bytes=j['bufferViews'][im['bufferView']]['byteLength']) for im in j.get('images', [])]
    res = dict(glb=os.path.relpath(path, ROOT), bytes=size, tris=tris, draw_calls=calls, images=imgs, checks=C.rows, heights=heights,
               n_checks=len(C.rows), n_fail=sum(1 for r in C.rows if not r['ok']), plausibility=plaus,
               tolerance='0.5 m or 2 % of the drawn value (whichever is larger) unless stated')
    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, 'domestic_verify.json'), 'w'), indent=1)
    for r in C.rows:
        print('%-4s %-96s model %-9s drawing %-9s dev %-7s tol %s' % ('ok' if r['ok'] else 'FAIL', r['check'][:96], r['model'], r['drawing'], r['dev'], r['tol']))
    print('checks %d, failed %d; tris %s; draw calls %s; %.2f MB' % (res['n_checks'], res['n_fail'], tris, calls, size / 1e6))
    return res


def neighbours(path):
    """3-D contact with the neighbouring assets (LOD0 of each): plan overlap of triangles whose height ranges overlap (a
    conservative triangle-bbox test) -> out/buildings3d/domestic_neighbours.json. Slow (~3 min): run with --neighbours."""
    from shapely.strtree import STRtree

    def tri_polys(S, pref):
        out = []
        for n, m in S.items():
            if not (n.startswith(pref) or m.get('lod') == 0): continue
            for p in m['prims']:
                P = p['P']
                for t in p['T']:
                    q = P[t]; pg = Polygon(q[:, [0, 2]])
                    g = pg if pg.area > 1e-4 else LineString(q[:, [0, 2]]).buffer(0.025, cap_style=2)
                    out.append((n, g, q[:, 1].min(), q[:, 1].max()))
        return out
    jd, bd, _ = load_glb(path); D_ = tri_polys(scene_meshes(jd, bd), 'L0_')
    res = {}
    for f in ('landside.glb', 'itb.glb', 'tower.glb'):
        fp = os.path.join(ROOT, 'data', 'buildings3d', f)
        if not os.path.exists(fp): continue
        j, b, _ = load_glb(fp); L = tri_polys(scene_meshes(j, b), 'L0_')
        tree = STRtree([g for _, g, _, _ in L]); hits = {}
        for n, g, z0, z1 in D_:
            for i in tree.query(g):
                ln, lg, lz0, lz1 = L[i]
                if lz1 < z0 + 0.05 or lz0 > z1 - 0.05: continue
                a = g.intersection(lg).area
                if a > 1e-3: hits[n + ' / ' + ln] = hits.get(n + ' / ' + ln, 0) + a
        res[f] = dict(n_tris=len(L), overlap_m2=round(sum(hits.values()), 3), pairs={k: round(v, 3) for k, v in sorted(hits.items(), key=lambda x: -x[1])[:20]})
        print(f, res[f]['overlap_m2'], list(res[f]['pairs'].items())[:5])
    json.dump(res, open(os.path.join(OUT, 'domestic_neighbours.json'), 'w'), indent=1)
    return res


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    glb = args[0] if args else os.path.join(ROOT, 'data', 'buildings3d', 'domestic.glb')
    if '--neighbours' in sys.argv: neighbours(glb)
    else: run(glb)
