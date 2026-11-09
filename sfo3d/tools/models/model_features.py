#!/usr/bin/env python3
"""Measure the converted aircraft models (data/models/*.sfom) and record the geometry the runtime needs to fit a model
to its real type: where the artist put the passenger doors, the fuselage cross-section along the body, and the wing tip.

Output: data/models/features.json, and the `MODEL_FEATURES` export in data/models/manifest.js (tools/convert_models.py
keeps it when it rewrites the manifest).

Model frame (as tools/convert_models.py writes it and js/live/models.js reads it): x forward with the nose tip at 0 (aft is
negative), y up with the fuselage centre line at 0, z to starboard. Model units are metres of the source model (the
runtime scales every model uniformly to the type's published length). Below, stations are given as a POSITIVE distance
aft of the nose (x_station = -x).

Per model:
  sec    fuselage section every `dx` metres from the nose: top / bottom of the skin on the centre plane and the half
         width at mid height (planar cut of the triangle mesh; body and fin zones only, i.e. no gear, engines, glass);
         over the forward 45 % also `hwf`, the half widths at the fractions `f` of the section height (bridge cab vs skin);
         at every station `hwl`, the STARBOARD half widths (z > 0: the side of the 737 / A320 cargo doors; the source
         models are not symmetric to a few cm: FG 737-800 lower lobe 2.5 cm narrower to starboard) at the heights `lo`
         (model units) above the section bottom (lower lobe: belt loaders, js/aircraft/fit.js skinHalfWidth; up to 1.5,
         close-out round 5)
  doors  passenger-door objects of the SOURCE model (FlightAirMap .glb node names, e.g. A320 `DoorL1`, CRJ `LeftDoor`,
         E-Jet `door.l1`, A220 `doorFL`): station of the centre and of both edges, sill (lowest y) and top, side (L/R).
         Only some source models have door objects; for the others the doors exist only in the texture.
  gearDoors  landing-gear door objects of the source model (station of the centre), for cross-checking gear positions
  cargo  lower-deck cargo-door objects of the source model (FG 737-800 cargodoorF / cargodoorR): station of the centre and
         edges, sill (lowest y), top, side; js/aircraft/fit.js fits the stance to the ACAP cargo-door rows with them
  wing   semi-span (outermost wing vertex), outer edge of the engines/pylons (|z|), for the wing-tip span fit
  under  lowest skin height over a (station, |z|) grid: where the procedural struts of gear-less models meet the skin
  nose   id of another model whose nose section (x < 8 m) is vertex-identical (median distance < 2 cm), so a door
         measured on that model also holds for this one (E175 = E170 nose, CRJ900 = CRJ700 nose)
  contact  models with their own gear (FG 737-800, 777): station and height of the nose-tyre and main-tyre bottoms
         (main: median station of the tyre bottoms within 1 cm of the lowest point, i.e. the bogie centre). The FG models
         stand level with the nose tyre 0.165-0.182 m above the ground; js/aircraft/fit.js pitches them nose-down about
         the main contact so both units touch (review: nose wheel floating).
  finTop station and height of the highest vertex (the fin tip), for the fin-height fit of a pitched model
Source objects (doors, gearDoors) need the source models; without them the values of the existing features.json are kept.

Usage: python3 tools/models/model_features.py [--fam DIR]
  --fam: FlightAirMap-3dmodels checkout (default $FAM_DIR or refs/cache/src/fam3d); without it only `sec`/`wing` are written
"""
import argparse, gzip, json, os, re, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
MD = os.path.join(ROOT, 'data', 'models')
sys.path.insert(0, os.path.join(ROOT, 'tools'))

DOOR_PAX = re.compile(r'^(Door[LR]\d|door\.[lr]\d$|door[FR][LR]$|LeftDoor$|RightDoor$|door[LR][FR]$)', re.I)   # (last: FlightGear 737-800 doorLF / doorLR; the 777's LFdoor objects are nose-gear doors)
# lower-deck cargo doors (FlightGear 737-800 cargodoorF / cargodoorR, right side): js/aircraft/fit.js fits the 737 stance to the
# ACAP cargo-door rows and publishes the drawn doors to the belt loaders (T.fit.cargo; close-out round 3, aircraft-1)
DOOR_CARGO = re.compile(r'^cargodoor[FR]$', re.I)
DOOR_GEAR_NOSE = re.compile(r'GearN|nlg|NoseGearDoor|nosegrdoor|lhnosedoor|rhnosedoor|lhfnosedoor|rhfnosedoor|^nosedoor|geardoor\.f|lgdoor\.(left|right)\.front|NLG_', re.I)
DOOR_GEAR_MAIN = re.compile(r'GearLDoor|GearRDoor|LeftGearDoor|RightGearDoor|wlg_|lhgearibdoor|rhgearibdoor|lhibdoor|rhibdoor|lhfdoor|rhfdoor|gear[LR]door|lgeardoor|rgeardoor|'
                            r'geardoor\.b|(left|right)\.main\.door|^door\dB', re.I)


def load(path):
    raw = gzip.decompress(open(path, 'rb').read())
    _v, hl = struct.unpack('<II', raw[4:12]); head = json.loads(raw[12:12 + hl]); B = 12 + hl
    q, o, nv = head['quant'], head['offsets'], head['nv']
    pq = np.frombuffer(raw, dtype=np.uint16, count=nv * 3, offset=B + o['pos']).reshape(-1, 3)
    pos = np.array(q['pmin']) + pq * np.array(q['pscale'])
    zone = np.frombuffer(raw, dtype=np.uint8, count=nv, offset=B + o['zone'])
    idx = np.frombuffer(raw, dtype=np.uint16 if head['idxType'] == 'u16' else np.uint32, count=head['ni'], offset=B + o['idx']).reshape(-1, 3)
    return head, pos, zone, idx


def plane_segments(pos, tri, xs):
    X = pos[tri][:, :, 0] - xs
    s = np.sign(X)
    T = pos[tri[(s.min(1) < 0) & (s.max(1) > 0)]]
    out = []
    for t in T:
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            xa, xb = t[a, 0] - xs, t[b, 0] - xs
            if (xa < 0) != (xb < 0):
                u = xa / (xa - xb); pts.append((t[a] + u * (t[b] - t[a]))[1:])
        if len(pts) == 2: out.append(pts)
    return np.array(out)


def crossings(segs, axis, v):
    """values of the other coordinate where the segments cross coordinate[axis] == v (segments are (y, z) pairs)"""
    o = 1 - axis; r = []
    for p, q in segs:
        if (p[axis] - v) * (q[axis] - v) <= 0 and p[axis] != q[axis]:
            u = (v - p[axis]) / (q[axis] - p[axis]); r.append(p[o] + u * (q[o] - p[o]))
    return r


# heights (fractions of the section height above its bottom) of the half-width table `hwf` over the forward fuselage
# (stations <= HWF_TO x L): where the jet-bridge cab meets the skin (js/aircraft/fit.js hwAt: door 1, door 2, A380 U1L).
# Review 4 Nov 2026: the ellipse through the best section within +-2 m of the door put widebody cabs 0.20-0.29 m off the skin.
HWF = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
HWF_TO = 0.45
# heights (model units above the section's bottom) of the lower-lobe half-width table `hwl`, every station: where belt
# loaders and other ground equipment meet the lower fuselage (js/aircraft/fit.js skinHalfWidth / T.fit.cargo; close-out
# round 3, aircraft-1: the consumers had only an unpitched ellipse through T.Hc and the crown)
# Close-out round 5 (aircraft verifier c4-2 finding 5): 1.25 and 1.5 added. Aft of HWF_TO the only other answer above the
# table was the ellipse through the tallest section within +-2 m (fit.js hwAt -> secAt), which at a tail cone is a section
# carrying the fin: at keel + 1.4 m it read 0.76-1.01 m against the mesh's 1.81-2.48 m (A330 / 747 / A380 / MD-11 tails).
# js/aircraft/fit.js hwLow reads the rows above 1.0 only at stations without `hwf` (forward of HWF_TO the hwf table is
# the better answer there: nose taper, wing-body fairing)
HWL = (0.05, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0, 1.25, 1.5)
# Close-out round 6 (aircraft verifier c5-1 finding 1): continuity guard on the rows above 1.0. At the wing-root junction
# of the A350 / 787 (aft of HWF_TO, over the main-gear bays) the fuselage skin ends under the wing's lower surface: the cut
# at bottom + 1.5 has no outer crossing within zmax (the wing lies beyond it) and found an inner wall instead - a359 X 33
# 0.86 (gear-bay wall) under a row of 3.08 at 1.25, X 32 2.80 under 3.09, b788 X 26 2.38 under 3.10; fit.js hwLow then
# read keel + 1.4 m as 1.85 against the mesh's 3.09 m. Below its maximum breadth a lower lobe does not narrow with height,
# so a row above 1.0 that falls by more than HWL_DROP while the three rows beneath it rise smoothly (each step -0.02 ..
# HWL_RISE: a lower lobe, not a fairing / tailplane spike or a tail cone above its maximum breadth) reads the row beneath.
# Over the 23 models it changes exactly those three rows (thresholds 0.2-0.3 / 0.1-0.3 give the same set; scratch
# c6/aircraft/scripts/guardsim2.py); a smaller drop (0.15) would also catch fairing spikes at 1.25 (A319 / A320 X 17-18).
HWL_DROP, HWL_RISE = 0.2, 0.15


def hwl_guard(row):
    r = list(row)
    for k in range(3, len(HWL)):
        if HWL[k] <= 1.0: continue
        w = r[k - 3:k + 1]
        if any(v is None for v in w): continue
        if w[3] < w[2] - HWL_DROP and all(-0.02 <= w[i + 1] - w[i] <= HWL_RISE for i in range(2)): r[k] = w[2]
    return r


def sections(pos, zone, idx, L, dx, hwf=False, zmax=None):
    tri = idx[np.isin(zone[idx], (0, 1)).all(1)]
    top, bot, hw, hf, hl = [], [], [], [], []
    n = int(L / dx) + 1
    for i in range(n):
        xs = -min(max(i * dx, 0.02), L - 0.02)
        segs = plane_segments(pos, tri, xs)
        ys = crossings(segs, 1, 0.0) if len(segs) else []
        if not ys:
            top.append(None); bot.append(None); hw.append(None)
            if hwf and i * dx <= HWF_TO * L: hf.append(None)
            if hwf: hl.append(None)
            continue
        t, b = max(ys), min(ys)
        zs = crossings(segs, 0, (t + b) / 2)
        top.append(round(float(t), 2)); bot.append(round(float(b), 2)); hw.append(round(float(max(abs(z) for z in zs)), 2) if zs else None)
        if hwf and i * dx <= HWF_TO * L:
            row = []
            for f in HWF:
                zz = crossings(segs, 0, b + f * (t - b)); row.append(round(float(max(abs(z) for z in zz)), 2) if zz else None)
            hf.append(row)
        if hwf:
            row = []
            for h in HWL:                       # starboard (z > 0: the cargo doors' side); zmax keeps a low wing / fairing out
                zz = [z for z in crossings(segs, 0, b + h) if z > 0 and (zmax is None or z <= zmax)]
                row.append(round(float(max(zz)), 2) if zz and b + h < t else None)
            hl.append(hwl_guard(row))
    out = dict(dx=dx, top=top, bot=bot, hw=hw)
    if hwf: out.update(f=list(HWF), hwf=hf, lo=list(HWL), hwl=hl)
    return out


def wing(pos, zone, L, hw=2.0):
    az = np.abs(pos[:, 2])
    w = (zone == 0) & (pos[:, 0] > -0.8 * L)
    eng = (zone == 2) | (zone == 7)
    # lowest point of the engines: the nacelle zone when the converter found one, else (nacelles merged into the wing mesh:
    # A220-300, E175, MD-11) the lowest skin point outboard of the fuselage (1.4 fuselage half widths) ahead of 0.75 L
    ow = np.isin(zone, (0, 2, 7)) & (az > 1.4 * hw) & (pos[:, 0] > -0.75 * L)
    engLow = float(pos[eng, 1].min()) if eng.sum() > 20 else (float(pos[ow, 1].min()) if ow.any() else None)
    semi = float(az[w].max())
    # wing-tip and tailplane-tip heights (mean y of the outermost 2 %), tailplane semi-span (js/aircraft/fit.js dihedral fit)
    tipY = float(pos[w & (az > 0.98 * semi), 1].mean())
    ht = (pos[:, 0] < -0.8 * L) & (zone != 1); htSemi = float(az[ht].max()) if ht.any() else None
    htY = float(pos[ht & (az > 0.97 * htSemi), 1].mean()) if htSemi else None
    htSt = float(-pos[ht & (az > 0.97 * htSemi), 0].mean()) if htSemi else None     # (its station: the stance fit's stabiliser row)
    out = dict(tipY=round(tipY, 3), htY=round(htY, 3) if htY is not None else None, htSt=round(htSt, 3) if htSt is not None else None, htSemi=round(htSemi, 3) if htSemi else None,
               semi=round(semi, 3), engOut=round(float(az[eng].max()), 3) if eng.sum() > 20 else None,
               engLow=round(engLow, 3) if engLow is not None else None)
    # wing-tip device top and bottom (close-out round 3, fix round 2: the 737NG ACAP rows E 'wingtip' (winglet top) and K
    # 'bottom of winglet'): the highest wing vertex within 1.0 of the semi-span (its station) and the lowest within 0.3
    tw = w & (az > semi - 1.0)
    if tw.any():
        it = int(np.argmax(np.where(tw, pos[:, 1], -np.inf))); lw = w & (az > semi - 0.3)
        out_tip = dict(top=round(float(pos[it, 1]), 3), topSt=round(float(-pos[it, 0]), 3), low=round(float(pos[lw, 1].min()), 3) if lw.any() else None)
    else: out_tip = None
    # nacelle zone alone (close-out round 3, fix round 2, v2: the 737 MAX nacelle offset is fitted to the ACAP engine row):
    # top / bottom of the zone-2 vertices and the station of the lowest one
    nz = zone == 2
    if nz.sum() > 20:
        i = int(np.argmin(np.where(nz, pos[:, 1], np.inf)))
        out['nac'] = dict(top=round(float(pos[nz, 1].max()), 3), low=round(float(pos[i, 1]), 3), lowSt=round(float(-pos[i, 0]), 3))
    if out_tip: out['tip'] = out_tip
    return out


def underside(pos, zone, idx, L, cell=0.5):
    """height of the lowest skin surface (body / wing, zone 0-1) over a grid of stations s (0.25-0.75 L) and |z| (0 to
    the model's half width + 6 m): the first skin a vertical ray from the ground hits. js/aircraft/fit.js reads it at the
    type's main-gear position so the procedural struts of gear-less models reach into the wing / fairing (review round 1:
    struts ended 0.1-0.4 m below the skin). Triangles are sampled every <= 0.2 m."""
    tri = idx[np.isin(zone[idx], (0, 1)).all(1)]
    A, B, C = pos[tri[:, 0]], pos[tri[:, 1]], pos[tri[:, 2]]
    e = np.maximum(np.linalg.norm(B - A, axis=1), np.maximum(np.linalg.norm(C - B, axis=1), np.linalg.norm(A - C, axis=1)))
    n = np.clip(np.ceil(e / 0.2).astype(int), 1, 60)
    s0, s1 = 0.25 * L, 0.75 * L; zmax = 12.0
    ns, nz = int((s1 - s0) / cell) + 1, int(zmax / cell) + 1
    grid = np.full((ns, nz), np.inf)
    for k in np.unique(n):
        q = np.flatnonzero(n == k)
        u, v = np.meshgrid(np.arange(k + 1), np.arange(k + 1)); m = (u + v) <= k
        u = u[m] / k; v = v[m] / k
        P = A[q, None, :] * (1 - u - v)[None, :, None] + B[q, None, :] * u[None, :, None] + C[q, None, :] * v[None, :, None]
        P = P.reshape(-1, 3); st = -P[:, 0]; az = np.abs(P[:, 2])
        ok = (st >= s0) & (st < s1) & (az < zmax)
        i = ((st[ok] - s0) / cell).astype(int); j = (az[ok] / cell).astype(int)
        np.minimum.at(grid, (i, j), P[ok, 1])
    y = [[None if not np.isfinite(v) else round(float(v), 2) for v in row] for row in grid]
    return dict(s0=round(s0, 2), ds=cell, dz=cell, y=y)


def contact(pos, zone, idx, L):
    """nose / main tyre bottoms of a model with its own gear (zone 3), stations positive aft"""
    used = np.zeros(len(pos), bool); used[np.unique(idx)] = True
    g = pos[(zone == 3) & used]
    if len(g) < 50: return None
    nose, main = g[g[:, 0] > -0.3 * L], g[g[:, 0] <= -0.3 * L]
    if not len(nose) or not len(main): return None
    n = nose[np.argmin(nose[:, 1])]; ym = float(main[:, 1].min()); mb = main[main[:, 1] < ym + 0.01]
    return dict(nose=dict(st=round(float(-n[0]), 3), y=round(float(n[1]), 3)),
                main=dict(st=round(float(-np.median(mb[:, 0])), 3), y=round(ym, 3), st0=round(float(-mb[:, 0].max()), 3), st1=round(float(-mb[:, 0].min()), 3)))


def source_objects(key, fam):
    """door / gear-door objects of the source .glb, in the normalised frame of convert() (same transform as check_dims)"""
    import convert_models as cm
    if key in cm.AC_MODELS:                     # FlightGear AC3D sources (737-800, 777): object names from the .ac files
        src, cfg = cm.AC_MODELS[key]
        if not all(os.path.exists(f if isinstance(f, str) else f[0]) for f in src): return None
        prims, _m, _i, _t = cm.ac_model(src, skip=cfg.get('skip'))
        for p in prims: p['node'] = p.get('node') or p.get('name', '')
    elif key in cm.MODELS:
        src, cfg = cm.MODELS[key]
        src = os.path.join(fam, os.path.relpath(src, cm.FAM))
        if not os.path.exists(src): return None
        prims, _m, _i, _t = cm.glb_primitives(src)
    else: return None
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0)
    top = allp[np.argmax(allp[:, 1])]
    fx = (top[0] - lo[0]) / max(hi[0] - lo[0], 1e-6); fz = (top[2] - lo[2]) / max(hi[2] - lo[2], 1e-6)
    axis, tail_pos = cfg['axis'] if cfg.get('axis') else ((0 if abs(fx - 0.5) > abs(fz - 0.5) else 2), None)
    if tail_pos is None: tail_pos = (fx if axis == 0 else fz) > 0.5
    fwd = np.zeros(3); fwd[axis] = -1.0 if tail_pos else 1.0
    R = np.stack([fwd, [0, 1.0, 0], np.cross(fwd, [0, 1.0, 0])])
    for p in prims: p['pos'] = p['pos'] @ R.T
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0); L0 = hi[0] - lo[0]
    sc = cfg['length'] / L0 if cfg.get('length') else 1.0
    if abs(sc - 1) <= 0.03: sc = 1.0
    for p in prims: p['pos'] = p['pos'] * sc
    allp = np.concatenate([p['pos'] for p in prims]); lo, hi = allp.min(0), allp.max(0)
    ft = allp[allp[:, 1] > hi[1] - 0.03 * (hi[1] - lo[1])]; zc = float(np.median(ft[:, 2])); Lm = hi[0] - lo[0]
    fw = (allp[:, 0] < hi[0] - 0.17 * Lm) & (allp[:, 0] > hi[0] - 0.33 * Lm)
    col = allp[fw & (np.abs(allp[:, 2] - zc) < 0.35)]
    if len(col) < 40 or (np.percentile(col[:, 1], 99.5) - np.percentile(col[:, 1], 0.5)) < 1.0:
        col = allp[fw & (np.abs(allp[:, 2] - zc) < 1.0)]
    cy = (np.percentile(col[:, 1], 99.5) + np.percentile(col[:, 1], 0.5)) / 2; Rf = (np.percentile(col[:, 1], 99.5) - np.percentile(col[:, 1], 0.5)) / 2
    near = allp[(np.abs(allp[:, 2] - zc) < 0.6) & (np.abs(allp[:, 1] - cy) < Rf)]
    shift = np.array([float(near[:, 0].max()), cy, zc])
    for p in prims: p['pos'] = p['pos'] - shift
    for f in cfg.get('doorFit', []): cm.door_fit(prims, f)     # the converter's door re-fit (FG 737-800 door 1L)
    objs = {}
    for p in prims:
        name = p['node'].split('|')[0]
        kind = 'pax' if DOOR_PAX.search(name) else 'cargo' if DOOR_CARGO.search(name) else 'nose' if DOOR_GEAR_NOSE.search(name) else 'main' if DOOR_GEAR_MAIN.search(name) else None
        if kind: objs.setdefault((kind, name), []).append(p['pos'])
    doors, gear, cargo = [], [], []
    for (kind, name), qs in objs.items():
        q = np.concatenate(qs)
        x0, x1 = float(-q[:, 0].max()), float(-q[:, 0].min())
        r = dict(name=name, x=round((x0 + x1) / 2, 3), x0=round(x0, 3), x1=round(x1, 3))
        if kind in ('pax', 'cargo'):
            r.update(side='L' if q[:, 2].mean() < 0 else 'R', ySill=round(float(q[:, 1].min()), 3), yTop=round(float(q[:, 1].max()), 3))
            (doors if kind == 'pax' else cargo).append(r)
        else:
            r['kind'] = kind; gear.append(r)
    out = dict(doors=sorted(doors, key=lambda d: (d['side'], d['x'])), gearDoors=sorted(gear, key=lambda d: d['x']))
    if cargo: out['cargo'] = sorted(cargo, key=lambda d: d['x'])
    return out


def same_nose(models, xmax=8.0, tol=0.02):
    from scipy.spatial import cKDTree
    pts = {k: m['pos'][(m['pos'][:, 0] > -xmax) & np.isin(m['zone'], (0, 1, 5))] for k, m in models.items()}
    out = {}
    for a in pts:
        for b in pts:
            if a >= b or len(pts[a]) < 200 or len(pts[b]) < 200: continue
            d1, _ = cKDTree(pts[a]).query(pts[b]); d2, _ = cKDTree(pts[b]).query(pts[a])
            if np.median(d1) < tol and np.median(d2) < tol: out.setdefault(a, []).append(b); out.setdefault(b, []).append(a)
    return out


def write_manifest_js(features):
    mp = os.path.join(MD, 'manifest.json'); man = json.load(open(mp))
    with open(os.path.join(MD, 'manifest.js'), 'w') as f:
        f.write('// generated by tools/convert_models.py (MODEL_DIMS) and tools/models/model_features.py (MODEL_FEATURES)\n')
        f.write('export const MODEL_DIMS = ' + json.dumps({k: v['dims'] for k, v in man.items()}, separators=(',', ':')) + ';\n')
        f.write('export const MODEL_FEATURES = ' + json.dumps(features, separators=(',', ':')) + ';\n')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--fam', default=os.environ.get('FAM_DIR', os.path.join(ROOT, 'refs', 'cache', 'src', 'fam3d')))
    ap.add_argument('--dx', type=float, default=1.0)
    a = ap.parse_args()
    models = {}
    for fn in sorted(os.listdir(MD)):
        if not fn.endswith('.sfom'): continue
        k = fn[:-5]; head, pos, zone, idx = load(os.path.join(MD, fn))
        models[k] = dict(head=head, pos=pos, zone=zone, idx=idx)
    noses = same_nose(models)
    old = {}
    try: old = json.load(open(os.path.join(MD, 'features.json')))
    except Exception: pass
    feats = {}
    for k, m in models.items():
        L = m['head']['dims']['L']
        sec = sections(m['pos'], m['zone'], m['idx'], L, a.dx, hwf=True, zmax=1.1 * float(m['head']['dims'].get('Rz') or m['head']['dims']['R']))
        hwm = float(np.median([h for h in sec['hw'][int(0.3 * L / a.dx):int(0.5 * L / a.dx)] if h is not None] or [2.0]))
        f = dict(sec=sec, wing=wing(m['pos'], m['zone'], L, hwm), under=underside(m['pos'], m['zone'], m['idx'], L))
        if m['head']['dims'].get('hasGear'):
            c = contact(m['pos'], m['zone'], m['idx'], L)
            if c: f['contact'] = c
        used = np.unique(m['idx']); it = used[np.argmax(m['pos'][used, 1])]
        f['finTop'] = dict(st=round(float(-m['pos'][it, 0]), 3), y=round(float(m['pos'][it, 1]), 3))
        # (close-out round 3, fix round 2: the station range of the fin tip - vertices within 3 cm of the top - whose aft end
        # is the highest point once a gear model is pitched nose-down)
        tt = m['pos'][:, 1] > m['pos'][it, 1] - 0.03
        f['finTop'].update(st0=round(float(-m['pos'][tt, 0].max()), 3), st1=round(float(-m['pos'][tt, 0].min()), 3))
        so = source_objects(k, a.fam)            # (None when the model's source is absent: FAM checkout or FG export)
        if so: f.update(so)
        else:                                   # source models not present: keep the measured source objects
            for kk in ('doors', 'gearDoors', 'cargo'):
                if kk in old.get(k, {}): f[kk] = old[k][kk]
        if k in noses: f['sameNose'] = sorted(noses[k])
        feats[k] = f
        print(f"{k:5s} L={L:6.2f} semi={f['wing']['semi']:.2f} engOut={f['wing']['engOut']} doors={[d['name'] + '@' + str(d['x']) for d in f.get('doors', [])]} sameNose={f.get('sameNose')}")
    json.dump(feats, open(os.path.join(MD, 'features.json'), 'w'), separators=(',', ':'))
    write_manifest_js(feats)
    print('wrote data/models/features.json and data/models/manifest.js')


if __name__ == '__main__':
    main()
