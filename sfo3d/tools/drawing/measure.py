"""Automatic deviation measurement: the 2-D features the 3-D app places (out/draw/scene2d.json) against georeferenced
imagery (background.py sources: the owner's Google screenshots - reference only - and NAIP when present).

For every feature edge, sample points every few metres, read a profile along the edge normal (+-10 m, 0.1 m steps,
averaged over 5 parallel lines 0.3 m apart) from ONE source image, and find the imaged edge:
  step         pavement / building / runway-end edges: peaks of the smoothed colour-gradient magnitude (CIE Lab); the
               feature's dominant edge polarity is found first (consensus of its strongest peaks) and only peaks with
               that polarity are kept, which rejects most shadow edges (a cast shadow is dark on the far side, the
               wrong polarity for roofs brighter than their shadow and for pavement darker than grass); among
               peaks >= 50 % of the strongest the one nearest the modelled edge wins; ambiguity is recorded
  line-yellow  painted yellow line (taxiway centreline, lead-in, hold bars): ridge of yellowness (R+G)/2-B against
               its flanks, width-matched; nearest strong ridge
  line-white   white runway edge stripe (0.91 m): ridge of luminance
  bar          fixed jet-bridge walkway: box ridge of either polarity, width 2.8 m
Offsets are signed along the outward normal (+ = the imaged edge lies outside / right of the modelled one).
Per feature: median / p90 / max absolute offset of the measured samples, signed median (bias), n measured / sampled.
Buildings additionally get a best-fit translation (relief displacement of roofs + registration) and the residual
after removing it: aerial imagery shows roof edges displaced away from nadir by height x tan(off-nadir angle), so a
15 m pier can appear 1-4 m from its footprint although the footprint is right.
Registration caveat: the Google screenshots were registered by chamfer matching against the SFO Museum building
outlines (tools/sat/register.py), so building-edge deviations on Google are not independent of that data; runway
ends were checked independently against FAA coordinates (tools/sat/faacheck.py). NAIP is independently georeferenced.
"""
import json, math, os, sys, time
import numpy as np
import cv2
from shapely.geometry import Point, Polygon
from shapely.prepared import prep
from shapely.ops import unary_union
from common import scene, OUT, poly_rings, w2st, st2w, G, hull_poly, buildings
import background

STEP = 0.1; R = 10.0; TAN = (-0.6, -0.3, 0.0, 0.3, 0.6)
D = np.arange(-R, R + 1e-9, STEP)


# ------------------------------------------------------------------------------------------------ helpers
class PaveMask:
    def __init__(self):
        S = scene(); r = S['rasters']['pave_1.00']; A = S['meta']['aptRect']
        im = cv2.imread(os.path.join(OUT, r['file']), cv2.IMREAD_COLOR)
        self.pave = im[:, :, 2] > 127; self.res = r['res']; self.s0 = A['s0']; self.t0 = A['t0']; self.h = A['h']
    def __call__(self, x, z):
        s, t = w2st(x, z); i = np.floor((s - self.s0) / self.res).astype(int); j = np.floor((self.t0 + self.h - t) / self.res).astype(int)
        H, W = self.pave.shape; ok = (i >= 0) & (j >= 0) & (i < W) & (j < H)
        out = np.zeros(np.shape(x), bool); out[ok] = self.pave[j[ok], i[ok]]; return out


def building_union():
    S = scene(); ps = [poly_rings(b['rings']) for b in buildings() if not b.get('notBuilt') and b['kind'] not in ('rail', 'walkway')]
    return unary_union(ps)


def contains(pg, x, z):
    import shapely
    return shapely.contains_xy(pg, x, z)


def sample_ring(ring, step, trim=1.5, closed=True, outward_sign=1):
    """points + unit right-hand normals along a ring/polyline (x,z); trim: stay away from vertices"""
    P = np.asarray(ring, float); n = len(P)
    segs = range(n if closed else n - 1)
    pts, nrm, tan = [], [], []
    for i in segs:
        a, b = P[i], P[(i + 1) % n]; d = b - a; L = math.hypot(*d)
        if L < 2 * trim + 0.5: continue
        u = d / L; nr = np.array([-u[1], u[0]]) * outward_sign
        k = max(1, int((L - 2 * trim) / step))
        for s in np.linspace(trim, L - trim, k + 1 if k > 1 else 1) if k > 1 else [L / 2]:
            pts.append(a + u * s); nrm.append(nr); tan.append(u)
    return np.array(pts).reshape(-1, 2), np.array(nrm).reshape(-1, 2), np.array(tan).reshape(-1, 2)


def ring_orientation_outward(ring):
    """+1 if the right-hand normal (x east, z south frame) of the ring points outward"""
    P = np.asarray(ring, float); a = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    # right-hand normal of travel (x,z) is (-dz, dx); for a positive-area ring (counter-clockwise in x,z) it points inward
    return -1 if a > 0 else 1


def lab(v):
    """(..., 3) BGR float -> Lab float (OpenCV scaling, L 0..100)"""
    sh = v.shape; x = np.nan_to_num(v).reshape(-1, 1, 3).astype(np.float32) / 255.0
    L = cv2.cvtColor(x, cv2.COLOR_BGR2Lab).reshape(sh); return L


def gsmooth(p, sigma_px):
    if sigma_px < 0.3: return p
    k = int(3 * sigma_px) + 1; x = np.arange(-k, k + 1); w = np.exp(-0.5 * (x / sigma_px) ** 2); w /= w.sum()
    pad = np.pad(p, [(0, 0)] * (p.ndim - 1) + [(k, k)], mode='edge') if p.ndim >= 1 else p
    out = np.apply_along_axis(lambda r: np.convolve(r, w, mode='valid'), -1, pad)
    return out


def local_max(y, i0=1):
    return np.where((y[..., 1:-1] >= y[..., :-2]) & (y[..., 1:-1] > y[..., 2:]))


# ------------------------------------------------------------------------------------------------ profile reading
def read_profiles(src, pts, nrm, tan, only=None, Dv=None, exclude=None):
    """(n,2) points, normals, tangents -> vals (n, len(Dv), 3) BGR averaged over the tangential lines, image ids, gsd"""
    Dv = D if Dv is None else Dv
    n = len(pts)
    P = pts[:, None, None, :] + nrm[:, None, None, :] * Dv[None, :, None, None] + tan[:, None, None, :] * np.array(TAN)[None, None, :, None]
    P = P.reshape(n, len(Dv) * len(TAN), 2)
    vals, ids, gsd = src.profiles(P, only=only, need=0.97, exclude=exclude)
    vals = vals.reshape(n, len(Dv), len(TAN), 3)
    with np.errstate(invalid='ignore'):
        v = np.nanmean(vals, axis=2)
    return v, ids, gsd


def find_step(prof, gsd, polarity=None, D=D):
    """prof (k,3) BGR -> candidates [(d, strength, signed L contrast)] along D"""
    if np.isnan(prof).any(): return []
    Lb = lab(prof); sig = max(0.25, 0.6 * gsd) / STEP
    Ls = np.stack([gsmooth(Lb[:, c], sig) for c in range(3)], 1)
    g = np.gradient(Ls, STEP, axis=0); mag = np.sqrt((g ** 2).sum(1))
    (ix,) = local_max(mag); ix = ix + 1
    out = []
    for i in ix:
        a0, a1 = max(0, i - int(2.0 / STEP)), max(1, i - int(0.5 / STEP)); b0, b1 = min(len(D) - 1, i + int(0.5 / STEP)), min(len(D), i + int(2.0 / STEP))
        if a1 <= a0 or b1 <= b0: continue
        dE = np.linalg.norm(Ls[b0:b1].mean(0) - Ls[a0:a1].mean(0)); dL = Ls[b0:b1, 0].mean() - Ls[a0:a1, 0].mean()
        if dE < 6: continue
        out.append((float(D[i]), float(mag[i]), float(dL)))
    return out


def find_ridge(prof, gsd, width, kind, D=D):
    """painted line / bar: ridge response of a width-matched box vs its flanks; kind 'yellow' | 'white' | 'bar'"""
    if np.isnan(prof).any(): return []
    B, Gc, Rr = prof[:, 0], prof[:, 1], prof[:, 2]
    if kind == 'yellow': s = (Rr + Gc) / 2 - B
    else: s = 0.114 * B + 0.587 * Gc + 0.299 * Rr
    w = max(width, 1.2 * gsd); hw = int(round(w / 2 / STEP)); fl0 = hw + int(0.3 / STEP); fl1 = hw + int(max(1.2, w) / STEP)
    c = np.concatenate([[0], np.cumsum(s)])
    def mean(a, b): a = np.clip(a, 0, len(s)); b = np.clip(b, 0, len(s)); return (c[b] - c[a]) / np.maximum(b - a, 1)
    i = np.arange(len(s))
    centre = mean(i - hw, i + hw + 1); left = mean(i - fl1, i - fl0 + 1); right = mean(i + fl0, i + fl1 + 1)
    resp = centre - np.maximum(left, right) if kind != 'bar' else np.minimum(centre - np.maximum(left, right) , 1e9)
    if kind == 'bar':  # either polarity: bright or dark box against both flanks
        resp = np.maximum(centre - np.maximum(left, right), np.minimum(left, right) - centre)
    valid = (i - fl1 >= 0) & (i + fl1 < len(s))
    resp = np.where(valid, resp, 0)
    # pixel noise from the first differences of the signal (independent of wide structures in the window)
    noise = 1.4826 * np.median(np.abs(np.diff(s))) / math.sqrt(2) + 1e-6
    (ix,) = local_max(resp); ix = ix + 1
    thr = {'yellow': 10.0, 'white': 18.0, 'bar': 8.0}[kind]
    return [(float(D[k]), float(resp[k]), float(resp[k] / noise)) for k in ix if resp[k] >= thr and resp[k] >= 4 * noise]


def choose(cands, key_strength=1):
    if not cands: return None, 0
    smax = max(c[key_strength] for c in cands)
    strong = [c for c in cands if c[key_strength] >= 0.5 * smax]
    best = min(strong, key=lambda c: abs(c[0]))
    return best, len(strong)


# ------------------------------------------------------------------------------------------------ features
def build_features(S):
    """list of feature dicts: id, cls, name, mode, width, pts, nrm, tan, draw (for the sheets)"""
    F = []; pave = PaveMask(); B = building_union(); Bp = prep(B.buffer(0.5))
    def keep_edge(pts, nrm, outside_unpaved=True, inside_paved=True, not_building=True, off=5.0):
        if not len(pts): return np.zeros(0, bool)
        o = pts + nrm * off; i = pts - nrm * off
        k = np.ones(len(pts), bool)
        if outside_unpaved: k &= ~pave(o[:, 0], o[:, 1])
        if inside_paved: k &= pave(i[:, 0], i[:, 1])
        if not_building: k &= ~contains(B.buffer(1.0), o[:, 0], o[:, 1]) & ~contains(B.buffer(1.0), i[:, 0], i[:, 1])
        return k
    # --- buildings: outline edges that face open ground (an edge whose outside is another building is internal)
    bl = [b for b in buildings() if b['kind'] not in ('rail', 'walkway')]
    bpoly = [poly_rings(b['rings']) for b in bl]
    parts = [(b, p) for b, p in zip(bl, bpoly) if b['kind'] in ('pier', 'hall')]
    seen = set()
    for bi, b in enumerate(bl):
        oth = unary_union([p for j, p in enumerate(bpoly) if j != bi]).buffer(0.8)
        P, N, T = [], [], []
        for ri, ring in enumerate(b['rings']):
            sg = ring_orientation_outward(ring) * (1 if ri == 0 else -1)
            p, n, t = sample_ring(ring, 2.0, trim=1.5, outward_sign=sg)
            if not len(p): continue
            o = p + n * 3.0
            k = ~contains(oth, o[:, 0], o[:, 1])
            P.append(p[k]); N.append(n[k]); T.append(t[k])
        if not P or not sum(len(x) for x in P): continue
        P, N, T = np.concatenate(P), np.concatenate(N), np.concatenate(T)
        # long outlines (the ramp-level complex) are reported in ~150 m pieces named after the nearest terminal part
        chunks = [np.arange(len(P))] if len(P) <= 110 else np.array_split(np.arange(len(P)), max(1, len(P) // 75))
        for ci, ix in enumerate(chunks):
            name = b['name']
            if len(chunks) > 1:
                c = Point(P[ix].mean(0)); near = min(parts, key=lambda q: q[1].distance(c))[0]['name'] if parts else '?'
                name = f'{b["name"]} near {near} (part {ci + 1}/{len(chunks)})'
            fid = f'bldg:{b["id"]}:{ci}:{name[:48]}'
            F.append(dict(id=fid, cls='building', name=name, kind=b['kind'], height=b['y1'] - G(), mode='step', width=0, pts=P[ix], nrm=N[ix], tan=T[ix], rings=b['rings']))
    # --- taxiway pavement polygons (SFO Museum) and extra pavement (imagery-derived): edges between pavement and unpaved
    def pave_feats(polys, cls, names):
        for pi, (poly, name) in enumerate(zip(polys, names)):
            P, N, T = [], [], []
            for ri, ring in enumerate(poly):
                sg = ring_orientation_outward(ring) * (1 if ri == 0 else -1)
                p, n, t = sample_ring(ring, 4.0, trim=2.0, outward_sign=sg)
                if not len(p): continue
                k = keep_edge(p, n); P.append(p[k]); N.append(n[k]); T.append(t[k])
            if not P or sum(len(x) for x in P) < 3: continue
            F.append(dict(id=f'{cls}:{pi}:{name}', cls=cls, name=name, mode='step', width=0, pts=np.concatenate(P), nrm=np.concatenate(N), tan=np.concatenate(T), rings=poly))
    tw = S['pave']['taxiways']; tpolys, tnames = [], []
    for t in tw:
        for poly in t['polys']: tpolys.append(poly); tnames.append(t['name'])
    pave_feats(tpolys, 'taxiway-edge', tnames)
    pave_feats(S['pave']['extra'], 'extra-pavement', [f'extra pavement #{i}' for i in range(len(S['pave']['extra']))])
    pave_feats(S['pave']['apron'], 'apron-edge', [f'apron outline #{i}' for i in range(len(S['pave']['apron']))])
    # --- runways: edge stripes (both sides), runway-end pavement edge, threshold stripes, displaced threshold bar
    for r in S['runways']:
        c0, c1 = np.array(r['centre'][0]), np.array(r['centre'][1]); d = np.array(r['dir']); nr = np.array([-d[1], d[0]])
        L = np.linalg.norm(c1 - c0); ys = r['paint']['edgeStripe']; yc = (ys[0] + ys[1]) / 2
        for sg, side in ((1, 'right'), (-1, 'left')):
            s = np.arange(30, L - 30, 10.0); p = c0 + np.outer(s, d) + nr * sg * yc
            n = np.tile(nr * sg, (len(s), 1)); t = np.tile(d, (len(s), 1))
            F.append(dict(id=f'rwy-edge:{r["name"][0]}/{r["name"][1]}:{side}', cls='runway-edge-stripe', name=f'RWY {r["name"][0]}/{r["name"][1]} edge stripe ({"south/east" if sg > 0 else "north/west"} side)', mode='line-white', width=ys[1] - ys[0], pts=p, nrm=n, tan=t, line=[(c0 + nr * sg * yc).tolist(), (c1 + nr * sg * yc).tolist()]))
        for e in r['ends']:
            inw = np.array(e['inward']); lat = np.array([-inw[1], inw[0]]); end = np.array(e['end']); thr = np.array(e['thr'])
            # threshold stripes: step into the stripes 6.1 m past the threshold, read at every stripe centre
            tp = r['paint']['thrStripes']; ycs = [(tp['lat0'] + tp['pitch'] * k + tp['width'] / 2) * sg for k in range(tp['n']) for sg in (-1, 1)]
            p = np.array([thr + inw * tp['x0'] + lat * y for y in ycs]); n = np.tile(inw, (len(ycs), 1)); t = np.tile(lat, (len(ycs), 1))
            F.append(dict(range=25.0, pol=-1, maxgsd=0.8, select='nearest', id=f'rwy-thr:{e["name"]}', cls='runway-threshold', name=f'RWY {e["name"]} threshold stripes (start {tp["x0"]} m past threshold)', mode='step', width=0, pts=p, nrm=-n, tan=t, group=True, line=[(thr + lat * 30).tolist(), (thr - lat * 30).tolist()]))
            # pavement end (the runway end line), read across the runway; at EMAS ends the pavement continues into the
            # 35 ft setback, so the visible edge is the EMAS bed entry (measured with the bed below)
            ez = [z for z in S['endZones'] if z['end'] == e['name']]
            if ez and ez[0]['kind'] == 'EMAS': continue
            ys2 = np.arange(-24, 24.1, 4.0); p = np.array([end + lat * y for y in ys2])
            F.append(dict(range=25.0, id=f'rwy-end:{e["name"]}', cls='runway-end', name=f'RWY {e["name"]} pavement end', mode='step', width=0, pts=p, nrm=np.tile(-inw, (len(ys2), 1)), tan=np.tile(lat, (len(ys2), 1)), group=True, line=[(end + lat * 30).tolist(), (end - lat * 30).tolist()]))
            if e['disp'] > 1:
                bar = thr - inw * 1.525; ys3 = np.arange(-26, 26.1, 4.0); p = np.array([bar + lat * y for y in ys3])
                F.append(dict(range=25.0, select='strongest', maxgsd=1.3, id=f'rwy-dthr:{e["name"]}', cls='runway-displaced-threshold', name=f'RWY {e["name"]} displaced threshold bar ({e["disp"]:.1f} m)', mode='line-white', width=3.05, pts=p, nrm=np.tile(inw, (len(ys3), 1)), tan=np.tile(lat, (len(ys3), 1)), group=True, line=[(bar + lat * 30).tolist(), (bar - lat * 30).tolist()]))
    # --- EMAS beds (3-D geometry, world.js buildEMAS): outline against the setback pavement / grass
    for b in S['emasBeds']:
        ring = b['hull']; sg = ring_orientation_outward(ring)
        p, n, t = sample_ring(ring, 3.0, trim=2.0, outward_sign=sg)
        if len(p): F.append(dict(id=f'emas:{b["end"]}', cls='emas-bed', name=f'EMAS bed beyond RWY {b["end"]}', mode='step', width=0, pts=p, nrm=n, tan=t, rings=[ring]))
    # --- painted lines (recorded ribbons): taxiway centrelines, stand lead-ins, hold bars (solid pair)
    tnames_polys = [(t['name'], poly_rings(p)) for t in tw for p in t['polys']]
    def twy_name(pt):
        q = Point(pt)
        for nm, pg in tnames_polys:
            if pg.contains(q): return nm
        return 'apron/ramp'
    ci = 0
    for rb in S['markings']['ribbons']:
        if rb['kind'] not in ('taxiway-centreline', 'leadin'): continue
        pts = np.array(rb['pts'], float)
        if len(pts) < 2: continue
        seglen = np.linalg.norm(np.diff(pts, axis=0), axis=1); L = seglen.sum()
        if L < 8: continue
        cum = np.concatenate([[0], np.cumsum(seglen)])
        if rb['kind'] == 'leadin': ss = np.arange(8.0, min(L, 70.0), 4.0)
        else: ss = np.arange(2.0, L - 2.0, 5.0)
        if not len(ss): continue
        idx = np.clip(np.searchsorted(cum, ss) - 1, 0, len(seglen) - 1)
        tt = (ss - cum[idx]) / np.maximum(seglen[idx], 1e-9)
        p = pts[idx] + (pts[idx + 1] - pts[idx]) * tt[:, None]
        u = (pts[idx + 1] - pts[idx]) / np.maximum(seglen[idx], 1e-9)[:, None]; n = np.c_[-u[:, 1], u[:, 0]]
        p = p + n * rb['offset']
        if rb['kind'] == 'leadin':
            st = min(S['stands'], key=lambda s: math.hypot(s['nose'][0] - pts[0][0], s['nose'][1] - pts[0][1]))
            F.append(dict(id=f'leadin:{st["name"]}', cls='stand-leadin', name=f'stand {st["name"]} lead-in line ({st["src"]})', mode='line-yellow', width=0.15, pts=p, nrm=n, tan=u, line=rb['pts'], stand=st['name']))
        else:
            nm = twy_name(pts[len(pts) // 2]); ci += 1
            F.append(dict(id=f'cl:{ci}:{nm}', cls='taxiway-centreline', name=f'{nm} centreline #{ci}', mode='line-yellow', width=0.15, pts=p, nrm=n, tan=u, line=rb['pts']))
    for hi, h in enumerate(S['markings']['holds']):
        a, b = np.array(h['a']), np.array(h['b']); u = np.array(h['dir']); lat = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        L = np.linalg.norm(b - a); ss = np.arange(2.0, L - 2.0, 3.0)
        if not len(ss): continue
        p = a + np.outer(ss, lat)
        F.append(dict(maxgsd=0.6, id=f'hold:{hi}:{h["text"]}:{h["twy"]}', cls='hold-line', name=f'hold {h["text"]} on {h["twy"]}', mode='line-yellow', width=1.83, pts=p, nrm=np.tile(u, (len(ss), 1)), tan=np.tile(lat, (len(ss), 1)), line=[h['a'], h['b']]))
    # --- jet bridges: fixed walkway (lateral position of the walkway band) and rotunda (disc search, separate)
    for bi, br in enumerate(S['bridges']):
        a = np.array(br['attach']); u = np.array(br['u']); rc = np.array(br['rc']); L = np.linalg.norm(rc - a)
        n = np.array([-u[1], u[0]])
        if L > 9:
            ss = np.arange(3.0, L - 3.5, 2.0); p = a + np.outer(ss, u)
            F.append(dict(id=f'walkway:{br["stand"]}:{br["gate"]}', cls='bridge-walkway', name=f'{br["stand"]} bridge {br["gate"]} fixed walkway', mode='bar', width=2.8, pts=p, nrm=np.tile(n, (len(ss), 1)), tan=np.tile(u, (len(ss), 1)), line=[a.tolist(), rc.tolist()], bridge=bi))
        F.append(dict(id=f'rotunda:{br["stand"]}:{br["gate"]}', cls='bridge-rotunda', name=f'{br["stand"]} bridge {br["gate"]} rotunda', mode='disc', width=4.9, pts=rc[None], nrm=np.array([[1.0, 0]]), tan=np.array([[0, 1.0]]), bridge=bi))
    return F


# ------------------------------------------------------------------------------------------------ measurement
def max_gsd(f):
    """coarsest imagery on which the feature can be seen: thin painted lines need ~2 px across"""
    if f.get('maxgsd'): return f['maxgsd']
    if f['mode'] in ('line-yellow', 'line-white'): return 0.35 if f['width'] < 0.5 else max(0.35, 0.8 * f['width'])
    return 3.5


def measure_feature(f, src, only=None, exclude=None):
    pts, nrm, tan = f['pts'], f['nrm'], f['tan']
    res = dict(id=f['id'], n=len(pts), off=np.full(len(pts), np.nan), strength=np.zeros(len(pts)), amb=np.zeros(len(pts), int), img=[None] * len(pts), gsd=np.full(len(pts), np.nan), why=[''] * len(pts))
    if f['mode'] == 'disc': return measure_disc(f, src, res)
    Rf = f.get('range', R); Dv = np.arange(-Rf, Rf + 1e-9, STEP)
    vals, ids, gsd = read_profiles(src, pts, nrm, tan, only=only, Dv=Dv, exclude=exclude)
    res['gsd'] = gsd; res['img'] = list(ids)
    cands = []
    mg = max_gsd(f)
    for k in range(len(pts)):
        if ids[k] is None: res['why'][k] = 'no imagery'; cands.append(None); continue
        if gsd[k] > mg: res['why'][k] = f'resolution {gsd[k]:.2f} m/px too coarse for a {f["width"]:.2f} m line'; cands.append(None); continue
        if f['mode'] == 'step': c = find_step(vals[k], gsd[k], D=Dv)
        elif f['mode'] == 'line-yellow': c = find_ridge(vals[k], gsd[k], f['width'], 'yellow', D=Dv)
        elif f['mode'] == 'line-white': c = find_ridge(vals[k], gsd[k], f['width'], 'white', D=Dv)
        else: c = find_ridge(vals[k], gsd[k], f['width'], 'bar', D=Dv)
        cands.append(c)
    # step edges: feature-level polarity consensus (sign of the L contrast of each sample's strongest peak)
    pol = f.get('pol', 0)
    if f['mode'] == 'step' and not pol:
        sg = [np.sign(max(c, key=lambda q: q[1])[2]) for c in cands if c]
        if len(sg) >= 3 and abs(np.mean(sg)) > 0.3: pol = float(np.sign(np.mean(sg)))
    for k, c in enumerate(cands):
        if c is None: continue
        if pol: c = [q for q in c if np.sign(q[2]) == pol]
        # candidate rule per feature: self-test (selftest.py) recovery of known shifts is higher with 'strongest' for step
        # edges and bars, and with 'nearest' for thin ridges and runway pavement ends
        sel = f.get('select') or os.environ.get('MEASURE_SELECT') or ('strongest' if f['mode'] in ('step', 'bar') and f['cls'] != 'runway-end' else 'nearest')
        best, amb = choose(c) if sel != 'strongest' else ((max(c, key=lambda q: q[1]), 1) if c else (None, 0))
        if best is None: res['why'][k] = 'no edge found'; continue
        res['off'][k] = best[0]; res['strength'][k] = best[1]; res['amb'][k] = amb
    res['polarity'] = pol
    return res


def measure_disc(f, src, res):
    """jet-bridge rotunda: best disc (bright or dark, r 2-3 m) against its ring within 10 m of the modelled centre"""
    c = f['pts'][0]; half = 14.0; r = 0.2
    img, valid, best = src.raster(c[0] - half, c[1] - half, c[0] + half, c[1] + half, r)
    if valid.mean() < 0.95: res['why'][0] = 'no imagery'; return res
    L = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)[:, :, 0].astype(np.float32)
    top = None
    for rad in (2.0, 2.45, 3.0):
        R1 = int(round(rad / r)); R2 = int(round((rad + 1.5) / r)); k = 2 * R2 + 1
        yy, xx = np.mgrid[-R2:R2 + 1, -R2:R2 + 1]; dd = np.hypot(xx, yy)
        disc = (dd <= R1).astype(np.float32); ring = ((dd > R1 + 1) & (dd <= R2)).astype(np.float32)
        md = cv2.filter2D(L, -1, disc / disc.sum()); mr = cv2.filter2D(L, -1, ring / ring.sum())
        # uniformity inside the disc (a roof), against a contrasting ring
        sd = np.sqrt(np.maximum(cv2.filter2D(L * L, -1, disc / disc.sum()) - md * md, 0))
        score = np.abs(md - mr) - 0.5 * sd
        H, W = score.shape; ii, jj = np.mgrid[0:H, 0:W]
        dist = np.hypot((jj + 0.5) * r - half, (ii + 0.5) * r - half)
        score[dist > 6] = -1e9; score[:R2] = -1e9; score[-R2:] = -1e9; score[:, :R2] = -1e9; score[:, -R2:] = -1e9
        i, j = np.unravel_index(np.argmax(score), score.shape)
        if top is None or score[i, j] > top[0]: top = (float(score[i, j]), (j + 0.5) * r - half, (i + 0.5) * r - half, rad)
    s, dx, dz, rad = top
    res['off'][0] = math.hypot(dx, dz); res['strength'][0] = s; res['gsd'][0] = float(np.median(best[np.isfinite(best)]))
    res['vec'] = [dx, dz]; res['rad'] = rad; res['img'][0] = 'raster'
    if s < 12: res['why'][0] = f'weak disc (score {s:.0f})'; res['off'][0] = np.nan
    return res


def summarize(f, r):
    o = r['off']; m = ~np.isnan(o); a = np.abs(o[m])
    out = dict(id=f['id'], cls=f['cls'], name=f['name'], n=int(r['n']), measured=int(m.sum()))
    if m.sum():
        out.update(median=float(np.median(a)), p90=float(np.percentile(a, 90)), max=float(a.max()), bias=float(np.median(o[m])), over1=int((a > 1.0).sum()),
                   gsd=float(np.nanmedian(r['gsd'][m])), images=sorted({str(x) for x, mm in zip(r['img'], m) if mm and x is not None}))
        if 'vec' in r: out['vec'] = r['vec']
    # buildings: best-fit translation (roof relief displacement + registration) and residual
    if f['cls'] == 'building' and m.sum() >= 8:
        N = f['nrm'][m]; A = N.T @ N
        if np.linalg.cond(A) < 50:
            t = np.linalg.solve(A, N.T @ o[m]); res = o[m] - N @ t; ra = np.abs(res)
            out.update(shift=[float(t[0]), float(t[1])], shiftLen=float(np.hypot(*t)), resid_median=float(np.median(ra)), resid_p90=float(np.percentile(ra, 90)))
    frac = out['measured'] / max(1, out['n'])
    # rotunda positions come from an automatic disc search (low confidence): reported, never flagged
    out['flag'] = bool(out.get('median') is not None and out['median'] > 1.0 and (out['measured'] >= 3 or f.get('group')) and f['cls'] != 'bridge-rotunda')
    out['coverage'] = frac
    return out


def run(which=None):
    S = scene(); srcs = background.sources()
    if which: srcs = {k: v for k, v in srcs.items() if k in which}
    t0 = time.time(); F = build_features(S)
    print(f'  {len(F)} features, {sum(len(f["pts"]) for f in F)} sample points ({time.time() - t0:.0f} s)')
    results = {}
    for name, src in srcs.items():
        t1 = time.time(); per = []; samples = {}
        for i, f in enumerate(F):
            r = measure_feature(f, src); s = summarize(f, r); s['source'] = name
            # second, independent reading from the next-best image covering the same samples (registration check)
            if f['mode'] != 'disc' and s.get('measured'):
                r2 = measure_feature(f, src, exclude=r['img']); s2 = summarize(f, r2)
                if s2.get('measured', 0) >= max(2, 0.3 * s['measured']):
                    s['alt'] = dict(median=s2['median'], bias=s2['bias'], measured=s2['measured'], gsd=s2['gsd'], images=s2['images'])
            per.append(s)
            samples[f['id']] = dict(pts=np.round(f['pts'], 2).tolist(), nrm=np.round(f['nrm'], 4).tolist(), off=[None if np.isnan(x) else round(float(x), 2) for x in r['off']],
                                    img=[str(x) if x is not None else None for x in r['img']], why=r['why'], polarity=r.get('polarity', 0), vec=r.get('vec'))
            if i % 200 == 0: print(f'    [{name}] {i}/{len(F)} features, {time.time() - t1:.0f} s', flush=True)
        results[name] = dict(source=src.name, public=src.public, licence=src.licence, features=per)
        json.dump(dict(source=src.name, samples=samples), open(os.path.join(OUT, f'dev_samples_{name}.json'), 'w'))
        print(f'  [{name}] done in {time.time() - t1:.0f} s')
    # lean model per Google image: roof shift of each building ~ height * lambda(image)
    json.dump(results, open(os.path.join(OUT, 'deviations.json'), 'w'), indent=0)
    return F, results


if __name__ == '__main__':
    run(sys.argv[1:] or None)
