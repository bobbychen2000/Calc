#!/usr/bin/env python3
"""Livery atlas for the converted aircraft models (data/models/<key>.sfom).

Why: the artist models carry the UV layouts of their FlightGear sources. Those layouts differ per model, share texels
between the left and right side on several models (so a title would read mirrored on one side), leave parts untextured
(E175 aft body, 737 nose), and give the fuselage very different resolutions (747: 1024 x 256 for 70 m). A livery painted
into those layouts cannot be made consistent. So every paintable surface of the skin gets a second, uniform layout of
our own, and the livery is baked into that:

  1. Parts. Each paint triangle (material kind 'paint', zones base / fin / engine / gear door / pylon) is assigned a part:
     fuselage (inside the model's fuselage section envelope, data/models/features.json `sec`, incl. nose, tail cone,
     belly fairing, dorsal fillet), fin (+ rudder), horizontal tail, engine nacelle skin (per engine; fan faces, inlet
     insides and exhausts keep their own texture), pylon, wing-tip device, gear door. The wing keeps its original
     texture and UVs (its panel detail is finer there than an atlas could hold).
  2. Charts. Per part, triangles are grouped by the dominant axis of their face normal (box projection: sides x-y,
     top/bottom x-z, front/back z-y) and projected orthographically; charts longer than the atlas are cut along the
     body; triangles hidden behind another surface of the same chart go to a further layer (no shared texels).
  3. Packing. Charts are shelf-packed into one square atlas with a per-part texel density (fuselage and fin highest).
     The UV of every atlas triangle is replaced (vertices are duplicated per chart); the atlas becomes texture 0 of the
     model, so a livery is a single texture swap (js/live/aircraft.js, js/three/aircraft.js).
  4. Neutral bake. The default atlas texture is the white skin with the source model's surface detail: the neutralised
     source texture (tools/convert_models.py) sampled through the original UVs, high-pass filtered (panel lines, door
     outlines, small markings; large grey areas of the source livery flatten to white), dark areas (anti-glare panel,
     walkways, exhaust stains) kept as they are. Alpha channel = class: 1 paint, 0.75 keep-original (dark), < 0.5
     window glass (night cabin glow).
  5. Cabin windows (tools/liveries/windows.py; owner feedback Sep 2026: two rows of windows on the livery renders).
     Exactly one row per deck: models whose artist windows differ from the manufacturer's drawing, or are openings in
     the skin / painted in the source texture / missing, get their artist windows removed before the atlas is built
     (glass objects deleted, openings closed with skin triangles, texture windows dropped from the kept dark areas)
     and the reference row painted (neutral atlas: the model's own type; every other type: tools/liveries/paint.py).
     Models whose glass matches the drawing (or have no usable drawing) keep it; only the windows it lacks are painted.
  6. Fuselage plugs (js/aircraft/fit.js PLUG_AT): every triangle crossing a plug station is split so that a 2 cm band
     of triangles straddles the station; the band gets its own charts, laid out as long as the longest plug of any type
     rendered with the model (dmax), so a stretched type (737-900 on the 737-800, 787-10 on the 787-8, ...) has texels
     for the plug and its windows instead of one smeared texel column.
  7. head.atlas records the charts, parts, plug bands and window mode so tools/liveries/paint.py paints into the same
     layout.

The first run backs the converted model up to refs/cache/models_orig/<key>.sfom (gitignored) and always rebuilds from
that backup, so the tool is idempotent. tools/convert_models.py output must be re-atlased after a re-conversion.

Usage: python3 tools/liveries/atlas.py [keys...] [--size 2048] [--preview DIR]
"""
import argparse, collections, gzip, io, json, math, os, re, shutil, struct, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, sfom, windows
from raster import raster, dilate_fill, sample_bilinear, occlusion

PARTS = ['keep', 'fus', 'fin', 'hstab', 'eng', 'pylon', 'tip', 'gdoor']
PID = {p: i for i, p in enumerate(PARTS)}
DENSITY = dict(fus=1.0, fin=1.0, hstab=0.55, eng=0.8, pylon=0.5, tip=0.9, gdoor=0.45)
DIRS = ['+x', '-x', '+y', '-y', '+z', '-z']
# textures that are never livery skin (cockpit / cabin interiors, gear, glazing, fan faces, chrome)
NONSKIN_TEX = re.compile(r'interior|carpet|seat|landing|gear|windshield|inside|chrome|^lights?\.', re.I)
FAN_TEX = re.compile(r'fan', re.I)
BAND_EPS = 0.02          # width of the plug band in the unstretched model (model units)
WHITE = 0.925            # sRGB level of the neutral skin in the default atlas
PAD = 6                  # chart padding at 2048 px (1.5 px at 512)


# ---------------------------------------------------------------- source
def source_path(key):
    os.makedirs(common.ORIG, exist_ok=True)
    cur = os.path.join(common.MD, key + '.sfom'); bak = os.path.join(common.ORIG, key + '.sfom')
    h = sfom.load(cur, textures=False)['head']
    if 'atlas' not in h:
        shutil.copy2(cur, bak)          # a fresh conversion (tools/convert_models.py): it becomes the source
    elif not os.path.exists(bak):
        raise RuntimeError(f'{key}: model already atlased and no source in {common.ORIG}; re-run tools/convert_models.py {key}')
    return bak


# ---------------------------------------------------------------- mesh edits before the atlas
def _append_vertices(m, P, N, UV, Z):
    """append vertices to model m (arrays pos, nrm, uv, zone); returns the index of the first new vertex"""
    i0 = len(m['pos'])
    m['pos'] = np.concatenate([m['pos'], P]); m['nrm'] = np.concatenate([m['nrm'], N])
    m['uv'] = np.concatenate([m['uv'], UV]); m['zone'] = np.concatenate([m['zone'], Z.astype(m['zone'].dtype)])
    return i0


def edit_windows(m, key, A):
    """remove the artist windows windows.removals() lists: delete their glass triangles (and a glass strip behind
    openings), close their openings in the skin with a fan of skin triangles (material of the surrounding skin)"""
    rem = windows.removals(key, A)
    idx, tm = m['idx'], m['tri_mat']
    drop = np.zeros(len(idx), bool)
    for w in rem['glass']: drop[w['tris']] = True
    if len(rem['strip']): drop[rem['strip']] = True
    # window reveals / frames modelled inside the openings (A350: 1,861 small textured triangles around the old row):
    # every triangle whose three vertices lie within a removed window's outline (+2 cm)
    Pv = m['pos'][idx]                                            # (n, 3, 3)
    sv, yv, zv = -Pv[..., 0], Pv[..., 1], Pv[..., 2]
    # only near the window itself (|z| within 0.3 m of the window's): the rectangle alone also caught wing-tip and winglet
    # triangles at the same station and height (A320, 737-800, A350, 767 wing tips were opened)
    # Body-skin triangles (zone 0) are never dropped: the reveals of an opening lie behind the fan that closes it, and
    # dropping skin triangles next to a window left small holes beside the A350's windows.
    tz_all = m['zone'][idx[:, 0]]
    for w in list(rem['glass']) + list(rem['holes']):
        inside = ((np.abs(sv - w['s']) <= w['w'] / 2 + 0.02) & (np.abs(yv - w['y']) <= w['h'] / 2 + 0.02) & (np.sign(zv) == w['side'])
                  & (np.abs(np.abs(zv) - w['z']) < 0.3)).all(1)
        drop |= inside & (tz_all != 0)
    before = _skin_boundary(m['pos'], idx[tz_all == 0])
    newT, newM = [], []
    P, N, UV = m['pos'], m['nrm'], m['uv']
    if rem['holes']:
        # skin material around each opening: the most common material of the triangles using the loop's vertices
        q = np.round(P / 0.001).astype(np.int64); _, inv = np.unique(q, axis=0, return_inverse=True); inv = inv.reshape(-1)
        tri_of = {}
        tz = m['zone'][idx[:, 0]]
        for t in np.where(tz == 0)[0]:
            for v in inv[idx[t]]: tri_of.setdefault(int(v), []).append(t)
        for h in rem['holes']:
            loop = np.array(h['loop'])
            mats = [tm[t] for v in inv[loop] for t in tri_of.get(int(v), [])]
            mat = max(set(mats), key=mats.count) if mats else tm[np.where(tz == 0)[0][0]]
            T_ = _fan(m, loop); newT += T_; newM += [mat] * len(T_)
            P, N, UV = m['pos'], m['nrm'], m['uv']
    keep = ~drop
    m['idx'] = np.concatenate([idx[keep], np.array(newT, np.int64).reshape(-1, 3)])
    m['tri_mat'] = np.concatenate([tm[keep], np.array(newM, np.int32)])
    # the skin must stay closed: skin edges that the removal left open (triangles of the skin inside a window's outline,
    # e.g. the corners around the E175's stray window) are closed with a fan per loop; open chains are reported
    tz_all = m['zone'][m['idx'][:, 0]]
    after = _skin_boundary(m['pos'], m['idx'][tz_all == 0])
    new_edges = [e for e in after if e not in before]
    closed, open_chains = _close_loops(m, new_edges, after)
    return dict(mode=rem['mode'], glass=len(rem['glass']), holes=len(rem['holes']), strip=int(len(rem['strip'])), texture=rem['texture'],
                dropped=int(drop.sum()), reclosed=closed, open=open_chains)


def _fan(m, loop):
    """triangles closing the opening bounded by `loop` (source vertex ids, in order): a fan to a centre vertex. The fan gets
    its own vertices (loop positions and UVs) with the skin's outward normal: loop vertices of the source can carry the
    normal of a reveal wall (A350: +-x normals at the window edges shaded the fan dark grey)"""
    P, N, UV = m['pos'], m['nrm'], m['uv']
    loop = np.asarray(loop)
    n0 = N[loop].sum(0); n0 /= max(np.linalg.norm(n0), 1e-9)
    good = (N[loop] @ n0) > 0.7
    n = N[loop][good].mean(0) if good.any() else n0; n /= max(np.linalg.norm(n), 1e-9)
    Nl = np.where(((N[loop] @ n) > 0.8)[:, None], N[loop], n[None])
    c = P[loop].mean(0)
    i0 = _append_vertices(m, np.concatenate([P[loop], c[None]]), np.concatenate([Nl, n[None]]),
                          np.concatenate([UV[loop], UV[loop].mean(0)[None]]), np.zeros(len(loop) + 1, int))
    k = len(loop); P = m['pos']; out = []
    for j in range(k):
        tri = [i0 + j, i0 + (j + 1) % k, i0 + k]
        fn = np.cross(P[tri[1]] - P[tri[0]], P[tri[2]] - P[tri[0]])
        if np.dot(fn, n) < 0: tri = [tri[1], tri[0], tri[2]]
        out.append(tri)
    return out


def _skin_boundary(P, T):
    """boundary edges of the triangle list T (edges used once), keyed by quantised vertex positions (1 mm): {key: (a, b)}
    with a, b source vertex indices"""
    q = np.round(P / 0.001).astype(np.int64)
    K = [tuple(r) for r in q]
    cnt, rep = {}, {}
    for a, b, c in T:
        for u, v in ((a, b), (b, c), (c, a)):
            ku, kv = K[u], K[v]; k = (ku, kv) if ku < kv else (kv, ku)
            cnt[k] = cnt.get(k, 0) + 1; rep.setdefault(k, (int(u), int(v)))
    return {k: rep[k] for k, n in cnt.items() if n == 1}


def _close_loops(m, keys, edges, max_extent=1.2):
    """close the closed loops formed by the boundary edges `keys` (of `edges`: key -> (a, b)) with triangle fans (the
    material and normal of the adjoining skin); loops longer than max_extent (m) and open chains are left alone.
    Returns (loops closed, open chains)"""
    if not keys: return 0, 0
    P = m['pos']; q = np.round(P / 0.001).astype(np.int64)
    adj = collections.defaultdict(list); vid = {}
    for k in keys:
        a, b = edges[k]; ka, kb = k
        adj[ka].append(kb); adj[kb].append(ka); vid.setdefault(ka, a); vid.setdefault(kb, b)
    # material per vertex key: the skin triangles around it
    tz = m['zone'][m['idx'][:, 0]]; mat_of = collections.defaultdict(list)
    for t in np.where(tz == 0)[0]:
        for v in m['idx'][t]:
            kv = tuple(q[v])
            if kv in adj: mat_of[kv].append(int(m['tri_mat'][t]))
    seen = set(); nT, nM = [], []; closed = opened = 0
    for k0 in list(adj):
        if k0 in seen: continue
        loop = [k0]; seen.add(k0); prev, cur, ok = None, k0, True
        while True:
            if len(adj[cur]) != 2: ok = False
            nb = [x for x in adj[cur] if x != prev]
            if not nb: ok = False; break
            nxt = nb[0]
            if nxt == k0: break
            if nxt in seen: ok = False; break
            loop.append(nxt); seen.add(nxt); prev, cur = cur, nxt
        V = np.array([vid[k] for k in loop]); ext = np.ptp(P[V], 0).max() if len(V) else 0
        if not ok or len(V) < 3 or ext > max_extent: opened += 1; continue
        mats = [x for k in loop for x in mat_of.get(k, [])]
        mat = max(set(mats), key=mats.count) if mats else int(m['tri_mat'][0])
        T_ = _fan(m, V); nT += T_; nM += [mat] * len(T_)
        P = m['pos']
        closed += 1
    if nT:
        m['idx'] = np.concatenate([m['idx'], np.array(nT, np.int64)]); m['tri_mat'] = np.concatenate([m['tri_mat'], np.array(nM, np.int32)])
    return closed, opened


def plug_bands(key, A):
    """plug stations of model `key` (model units, positive aft of the nose) with the longest positive plug any type
    rendered with the model inserts there (model units)"""
    base = A['base'][key]; Tb = A['types'][base]; s0 = Tb['fit']['s0'] if Tb['fit'] else 1.0
    bands = {}
    for t, T in A['types'].items():
        f = T.get('fit')
        if not f or f['model'] != key or not f['plugs']: continue
        for at, d in ((f['plugs']['at1'], f['plugs']['d1']), (f['plugs']['at2'], f['plugs']['d2'])):
            k = round(at / s0, 4)
            bands[k] = max(bands.get(k, 0.0), d / s0)
    return [dict(s=k, dmax=round(v, 4)) for k, v in sorted(bands.items()) if v > 0.01]


def split_plane(m, x0, tris_mask=None):
    """split every triangle crossing the plane x = x0 (model frame) into triangles on either side; new vertices on the
    crossed edges interpolate position, normal, UV and take the zone of the edge's first vertex"""
    P, idx = m['pos'], m['idx']
    X = P[idx][:, :, 0] - x0
    cross = (X.min(1) < -1e-7) & (X.max(1) > 1e-7)
    if tris_mask is not None: cross &= tris_mask
    ci = np.where(cross)[0]
    if not len(ci): return 0
    cache = {}
    newP, newN, newUV, newZ = [], [], [], []
    base = len(P)
    def mid(a, b):
        k = (min(a, b), max(a, b))
        if k in cache: return cache[k]
        xa, xb = P[a, 0] - x0, P[b, 0] - x0; t = xa / (xa - xb)
        newP.append(P[a] + t * (P[b] - P[a])); nn = m['nrm'][a] + t * (m['nrm'][b] - m['nrm'][a]); newN.append(nn / max(np.linalg.norm(nn), 1e-9))
        newUV.append(m['uv'][a] + t * (m['uv'][b] - m['uv'][a])); newZ.append(m['zone'][a])
        cache[k] = base + len(newP) - 1
        return cache[k]
    outT, outM = [], []
    for t in ci:
        a, b, c = idx[t]; xs = [P[a, 0] - x0, P[b, 0] - x0, P[c, 0] - x0]; vs = [a, b, c]
        # rotate so that vertex 0 is alone on its side
        sg = [1 if x > 0 else -1 for x in xs]
        for r in range(3):
            if sg[r] != sg[(r + 1) % 3] and sg[r] != sg[(r + 2) % 3]: break
        v0, v1, v2 = vs[r], vs[(r + 1) % 3], vs[(r + 2) % 3]
        if abs(P[v1, 0] - x0) < 1e-7 or abs(P[v2, 0] - x0) < 1e-7:
            # one vertex on the plane: split into two
            if abs(P[v1, 0] - x0) < 1e-7: e = mid(v0, v2); outT += [[v0, v1, e], [e, v1, v2]]
            else: e = mid(v0, v1); outT += [[v0, e, v2], [e, v1, v2]]
            outM += [m['tri_mat'][t]] * 2; continue
        e1 = mid(v0, v1); e2 = mid(v0, v2)
        outT += [[v0, e1, e2], [e1, v1, v2], [e1, v2, e2]]; outM += [m['tri_mat'][t]] * 3
    keep = ~cross
    if newP:
        m['pos'] = np.concatenate([P, np.array(newP)]); m['nrm'] = np.concatenate([m['nrm'], np.array(newN)])
        m['uv'] = np.concatenate([m['uv'], np.array(newUV)]); m['zone'] = np.concatenate([m['zone'], np.array(newZ, m['zone'].dtype)])
    m['idx'] = np.concatenate([idx[keep], np.array(outT, np.int64)]); m['tri_mat'] = np.concatenate([m['tri_mat'][keep], np.array(outM, np.int32)])
    return len(ci)


def make_bands(m, bands):
    """split the mesh at x = -(s -+ eps/2) for every plug station; returns per triangle the band index (-1 = none)"""
    for b in bands:
        split_plane(m, -b['s'] + BAND_EPS / 2)
        split_plane(m, -b['s'] - BAND_EPS / 2)
    C = m['pos'][m['idx']].mean(1)[:, 0]
    band_of = np.full(len(m['idx']), -1, np.int16)
    for i, b in enumerate(bands):
        band_of[np.abs(C + b['s']) < BAND_EPS / 2] = i
    return band_of


def band_positions(P, idx, band_of, bands):
    """positions for charting the band triangles: the aft side of each band is moved aft by the band's dmax, so its
    charts are as long as the longest plug"""
    Pb = P.copy()
    for i, b in enumerate(bands):
        vs = np.unique(idx[band_of == i])
        aft = vs[P[vs, 0] < -b['s']]
        Pb[aft, 0] -= b['dmax']
    return Pb


# ---------------------------------------------------------------- engines
def engine_clusters(C):
    """cluster engine-zone triangle centroids C (n, 3) by position in the y-z plane (0.4 m grid, 8-connected)"""
    if not len(C): return np.zeros(0, int), []
    g = 0.4
    iy = np.floor(C[:, 1] / g).astype(int); iz = np.floor(C[:, 2] / g).astype(int)
    oy, oz = iy.min(), iz.min(); grid = np.zeros((iy.max() - oy + 3, iz.max() - oz + 3), bool)
    grid[iy - oy + 1, iz - oz + 1] = True
    lab, n = ndimage.label(grid, structure=np.ones((3, 3), bool))
    cl = lab[iy - oy + 1, iz - oz + 1] - 1
    info = []
    for k in range(n):
        P = C[cl == k]
        yc = (P[:, 1].min() + P[:, 1].max()) / 2; zc = (P[:, 2].min() + P[:, 2].max()) / 2
        r = max(P[:, 1].max() - P[:, 1].min(), P[:, 2].max() - P[:, 2].min()) / 2
        info.append(dict(yc=float(yc), zc=float(zc), r=float(r), x0=float(P[:, 0].min()), x1=float(P[:, 0].max()), n=int(len(P))))
    # merge tiny clusters (detached bits) into the nearest big one
    big = [k for k in range(n) if info[k]['n'] >= 12] or list(range(n))
    remap = {}
    for k in range(n):
        if k in big: remap[k] = big.index(k)
        else:
            d = [math.hypot(info[k]['yc'] - info[b]['yc'], info[k]['zc'] - info[b]['zc']) for b in big]
            remap[k] = int(np.argmin(d))
    cl = np.array([remap[c] for c in cl]) if len(cl) else cl
    out = []
    for j, b in enumerate(big):
        P = C[cl == j]
        yc = (P[:, 1].min() + P[:, 1].max()) / 2; zc = (P[:, 2].min() + P[:, 2].max()) / 2
        out.append(dict(yc=round(float(yc), 3), zc=round(float(zc), 3), r=round(float(max(P[:, 1].ptp(), P[:, 2].ptp()) / 2), 3),
                        x0=round(float(P[:, 0].min()), 3), x1=round(float(P[:, 0].max()), 3)))
    return cl, out


# ---------------------------------------------------------------- classification
def classify(m, env, feat, seeds=None):
    h = m['head']; mats = h['mats']; texs = h['textures']
    P, N, idx, Z = m['pos'], m['nrm'], m['idx'], m['zone']
    L = h['dims']['L']; semi = feat['wing']['semi']
    C = P[idx].mean(1)
    fn = np.cross(P[idx[:, 1]] - P[idx[:, 0]], P[idx[:, 2]] - P[idx[:, 0]])
    area = np.linalg.norm(fn, axis=1) / 2
    Nf = fn / np.maximum(area[:, None] * 2, 1e-12)
    # orient face normals like the vertex normals (winding may be inconsistent in the sources)
    vn = N[idx].sum(1); flip = (Nf * vn).sum(1) < 0; Nf[flip] *= -1
    tz = Z[idx[:, 0]]
    kind = np.array([mats[i]['kind'] for i in m['tri_mat']])
    texn = np.array([(texs[mats[i]['tex']]['name'] if mats[i]['tex'] >= 0 else '') for i in m['tri_mat']])
    paint = (kind == 'paint') & np.isin(tz, (0, 1, 2, 4, 7)) & np.array([not NONSKIN_TEX.search(t) for t in texn])
    s = -C[:, 0]
    top, bot, hw = env.at(s)
    part = np.zeros(len(idx), np.int8)
    az = np.abs(C[:, 2])
    tipL = max(1.0, 0.07 * semi)
    # fuselage envelope (generous: belly fairing and wing-root fillets are body)
    inbody = (az <= hw * 1.15 + 0.1) & (C[:, 1] >= bot - 0.35) & (C[:, 1] <= top + 0.25)
    z0 = paint & (tz == 0)
    part[z0 & inbody] = PID['fus']
    rest = z0 & ~inbody
    # nose: the measured envelope under-reads the first metres of some noses (767: a 4.5 m^2 ring 1.1-1.8 m aft of the
    # tip fell outside and kept the source livery); nothing but fuselage is there
    part[rest & (s < 0.1 * L)] = PID['fus']; rest &= ~(s < 0.1 * L)
    finlike = rest & (C[:, 1] > top + 0.1) & (az < 1.2) & (s > 0.55 * L)
    part[finlike] = PID['fin']
    rest &= ~finlike
    part[rest & (s > 0.72 * L) & (az > hw * 1.1)] = PID['hstab']
    rest &= ~((s > 0.72 * L) & (az > hw * 1.1))
    part[rest & (az > semi - tipL)] = PID['tip']
    # fin zone: fin, or the tailplane of a T-tail
    z1 = paint & (tz == 1)
    part[z1 & (az <= 1.3)] = PID['fin']; part[z1 & (az > 1.3)] = PID['hstab']
    part[paint & (tz == 7)] = PID['pylon']
    part[paint & (tz == 4)] = PID['gdoor']
    # engines: nacelle skin only (outward-facing, not the fan face / inlet inside / exhaust faces)
    ENG_TEX = re.compile(r'engine|turbofan|nacelle|cowl', re.I)
    etex = np.array([bool(ENG_TEX.search(t)) for t in texn])
    z2 = np.where(paint & ((tz == 2) | ((tz == 0) & etex & (part == 0))) & np.array([not FAN_TEX.search(t) for t in texn]))[0]
    ecl, eng = engine_clusters(C[z2])
    # real nacelles only: not the radome ('nose cone' names), not long thin strips, not APU / light bits
    # (a small cluster on the centre line is the APU exhaust of the tail cone, e.g. E170 / E190: not an engine)
    good = [j for j, e in enumerate(eng) if e['r'] >= 0.35 and e['x1'] < -0.06 * L and (e['x1'] - e['x0']) < 8 * e['r']
            and not (abs(e['zc']) < 0.5 and e['r'] < 0.6)]
    remap = {j: i for i, j in enumerate(good)}
    keepz2 = np.array([c in remap for c in ecl], bool) if len(ecl) else np.zeros(0, bool)
    z2 = z2[keepz2]; ecl = np.array([remap[c] for c in ecl[keepz2]], int); eng = [eng[j] for j in good]
    eng_of = np.full(len(idx), -1, np.int16)
    z0p = np.where(paint & (tz == 0) & (part == 0))[0]
    # models whose nacelles are not in the engine zone (E175, MD-11: merged into the wing mesh): find them from the type's
    # engine stations (js/aircraft/types.js eng z, r; seeds only) by fitting a circle to the body-zone triangles there
    if seeds and len(z0p):
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        q_ = np.round(P / 0.002).astype(np.int64); _, inv = np.unique(q_, axis=0, return_inverse=True); inv = inv.reshape(-1)
        Tq = inv[idx[z0p]]; nvq = inv.max() + 1
        g = coo_matrix((np.ones(2 * len(Tq)), (np.concatenate([Tq[:, 0], Tq[:, 1]]), np.concatenate([Tq[:, 1], Tq[:, 2]]))), shape=(nvq, nvq))
        _, lab = connected_components(g, directed=False)
        tl = lab[Tq[:, 0]]
        comps = []
        for cc in np.unique(tl):
            sel_ = z0p[tl == cc]
            if len(sel_) < 40: continue
            V = P[idx[sel_]].reshape(-1, 3); lo, hi = V.min(0), V.max(0)
            comps.append(dict(tris=sel_, lo=lo, hi=hi, area=float(area[sel_].sum())))
        for (zs, rs) in seeds:
            if any(abs(e['zc'] - zs) < 1.5 * rs for e in eng): continue
            best = None
            for cp in comps:
                dy, dz = cp['hi'][1] - cp['lo'][1], cp['hi'][2] - cp['lo'][2]; zc = (cp['lo'][2] + cp['hi'][2]) / 2
                if np.sign(zc) != np.sign(zs) or abs(zc - zs) > 2.5 * rs: continue
                if not (1.2 * rs < dy < 3.4 * rs and 1.2 * rs < dz < 3.4 * rs and 0.65 < dy / dz < 1.5): continue
                if best is None or cp['area'] > best['area']: best = cp
            if best is None: continue
            lo, hi = best['lo'], best['hi']
            eng.append(dict(yc=round(float((lo[1] + hi[1]) / 2), 3), zc=round(float((lo[2] + hi[2]) / 2), 3), r=round(float(((hi[1] - lo[1]) + (hi[2] - lo[2])) / 4), 3),
                            x0=round(float(lo[0]), 3), x1=round(float(hi[0]), 3), seed=True))
            z2 = np.concatenate([z2, best['tris']]); ecl = np.concatenate([ecl, np.full(len(best['tris']), len(eng) - 1)])
    for j, e in enumerate(eng):
        sel = z2[ecl == j]
        # inlet cowls modelled in the body zone (e.g. FG 737-800): body-zone triangles ahead of the engine-zone part,
        # inside the nacelle cylinder
        rr = np.hypot(C[z0p, 1] - e['yc'], C[z0p, 2] - e['zc'])
        cand = z0p[(rr < 1.4 * e["r"]) & (C[z0p, 1] - e['yc'] < 1.05 * e['r']) & (C[z0p, 0] > e["x0"] - 3.0 * e['r']) & (C[z0p, 0] < e['x1'] + 3.2 * e['r'])]
        cand = np.setdiff1d(cand, sel)
        if len(cand):
            sel = np.concatenate([sel, cand]); e['x1'] = round(float(max(e['x1'], P[idx[cand]][:, :, 0].max())), 3)
            e['x0'] = round(float(min(e['x0'], P[idx[cand]][:, :, 0].min())), 3)
        rad = C[sel][:, 1:] - np.array([e['yc'], e['zc']]); rl = np.linalg.norm(rad, axis=1)
        # outer skin = the outermost surface at its station and angle around the nacelle axis (the source normals are
        # not reliable: single-sided cowls, mirrored engines); fan faces and exhaust faces (|nx| > 0.8) excluded
        ang = np.arctan2(rad[:, 1], rad[:, 0])
        bx = np.floor((C[sel, 0] - e['x0']) / 0.25).astype(int); ba = np.floor((ang + np.pi) / (np.pi / 9)).astype(int)
        key = bx * 100 + ba
        rmax = np.zeros(len(sel))
        for k_ in np.unique(key):
            q = key == k_; rmax[q] = rl[q].max()
        ok = (np.abs(Nf[sel][:, 0]) < 0.8) & (rl > 0.9 * rmax) & (rl > 0.45 * e['r'])
        part[sel[ok]] = PID['eng']; eng_of[sel[ok]] = j
    # degenerate triangles stay where they are
    part[area < 1e-10] = 0
    return part, eng_of, eng, Nf, area


# ---------------------------------------------------------------- charts
def proj(P, d):
    """box projection per dominant normal axis d (0..5): model metres -> chart plane (a, b); b grows downward"""
    if d in (4, 5): return np.stack([-P[..., 0], -P[..., 1]], -1)       # sides: station, height
    if d in (2, 3): return np.stack([-P[..., 0], P[..., 2]], -1)        # top / bottom: station, butt line
    return np.stack([P[..., 2], -P[..., 1]], -1)                        # front / back: butt line, height


def depth_of(P, d):
    return (-P[..., 0], P[..., 0], -P[..., 1], P[..., 1], -P[..., 2], P[..., 2])[d]


def cpos(c, P, Pb):
    return Pb if (Pb is not None and c.get('band', -1) >= 0) else P


def build_charts(m, part, eng_of, Nf, area, band_of=None, Pb=None):
    P, idx = m['pos'], m['idx']
    if band_of is None: band_of = np.full(len(idx), -1, np.int16)
    tris = np.where(part > 0)[0]
    dom = np.argmax(np.abs(Nf[tris]), 1) * 2 + (np.take_along_axis(Nf[tris], np.argmax(np.abs(Nf[tris]), 1)[:, None], 1)[:, 0] < 0)
    # the fuselage sides take triangles up to 55 deg from the side (fewer, larger side charts; better for titles)
    fus = part[tris] == PID['fus']
    n = Nf[tris]
    side = fus & (np.abs(n[:, 2]) > 0.55 * np.hypot(n[:, 1], n[:, 2])) & (np.abs(n[:, 0]) < 0.75)
    dom = np.where(side, np.where(n[:, 2] > 0, 4, 5), dom)
    groups = {}
    for t, d in zip(tris, dom):
        p = PARTS[part[t]]; sub = int(eng_of[t]) if p == 'eng' else (int(np.sign(P[idx[t]].mean(0)[2]) >= 0) if p in ('tip', 'hstab', 'gdoor', 'pylon') else 0)
        groups.setdefault((p, sub, int(d), int(band_of[t])), []).append(t)
    charts = []
    for (p, sub, d, bnd), tl in groups.items():
        tl = np.array(tl)
        layer = 0
        Pc = Pb if (bnd >= 0 and Pb is not None) else P
        while len(tl):
            # hidden-surface split: triangles mostly more than 12 cm behind another surface of the same chart (in its
            # projection direction) go to the next layer, so no two surfaces share texels
            Q = proj(Pc[idx[tl]], d); D = depth_of(Pc[idx[tl]], d)
            lo = Q.reshape(-1, 2).min(0); g = 0.05
            ext = Q.reshape(-1, 2).max(0) - lo
            if ext[0] * ext[1] / (g * g) > 4e6: g = math.sqrt(ext[0] * ext[1] / 4e6)
            px = (Q - lo) / g
            W = int(np.ceil(px[..., 0].max())) + 2; H = int(np.ceil(px[..., 1].max())) + 2
            frac, tot = occlusion(px, D.astype(np.float32), W, H, 0.12)
            hid = (tot >= 2) & (frac > 0.4)
            charts.append(dict(part=p, sub=sub, dir=d, layer=layer, tris=tl[~hid], band=bnd))
            tl = tl[hid]; layer += 1
            if layer > 4:
                if len(tl): charts.append(dict(part=p, sub=sub, dir=d, layer=layer, tris=tl, band=bnd))
                break
    return [c for c in charts if len(c['tris'])]


def split_long(charts, P, idx, kpm, maxw, Pb=None):
    """cut charts wider than maxw pixels (at kpm px per metre x part density) into pieces along a"""
    out = []
    for c in charts:
        Q = proj(cpos(c, P, Pb)[idx[c['tris']]], c['dir'])
        k = kpm * DENSITY[c['part']]
        w = (Q[..., 0].max() - Q[..., 0].min()) * k
        if w <= maxw: out.append(c); continue
        n = int(math.ceil(w / (maxw * 0.92)))
        a = Q[..., 0].mean(1); a0, a1 = Q[..., 0].min(), Q[..., 0].max()
        cut = np.minimum((( a - a0) / (a1 - a0 + 1e-9) * n).astype(int), n - 1)
        for j in range(n):
            sel = c['tris'][cut == j]
            if len(sel): out.append(dict(c, tris=sel, piece=j))
    return out


def chart_rects(charts, P, idx, kpm, Pb=None):
    for c in charts:
        Q = proj(cpos(c, P, Pb)[idx[c['tris']]], c['dir']); k = kpm * DENSITY[c['part']]
        lo = Q.reshape(-1, 2).min(0); hi = Q.reshape(-1, 2).max(0)
        c['lo'] = lo; c['k'] = k
        c['w'] = int(math.ceil((hi[0] - lo[0]) * k)) + 2 * PAD; c['h'] = int(math.ceil((hi[1] - lo[1]) * k)) + 2 * PAD


def shelf_pack(charts, S):
    order = sorted(range(len(charts)), key=lambda i: -charts[i]['h'])
    x = y = rowh = 0
    for i in order:
        c = charts[i]
        if c['w'] > S: return False
        if x + c['w'] > S: x = 0; y += rowh; rowh = 0
        if y + c['h'] > S: return False
        c['x'] = x; c['y'] = y; x += c['w']; rowh = max(rowh, c['h'])
    return True


def pack(charts, P, idx, S, Pb=None):
    area = 0
    for c in charts:
        Q = proj(cpos(c, P, Pb)[idx[c['tris']]], c['dir']); ext = Q.reshape(-1, 2).ptp(0); area += ext[0] * ext[1] * DENSITY[c['part']] ** 2
    kpm = math.sqrt(S * S * 0.8 / max(area, 1e-6))
    for _ in range(40):
        cs = split_long(charts, P, idx, kpm, S - 2 * PAD - 2, Pb)
        chart_rects(cs, P, idx, kpm, Pb)
        if shelf_pack(cs, S): return cs, kpm
        kpm *= 0.96
    raise RuntimeError('atlas packing failed')


# ---------------------------------------------------------------- detail (high-pass of the neutralised source texture)
def detail_maps(m, orig=None):
    """per source texture, in that texture's pixel space:
      D  thin dark lines (panel lines, door and hatch outlines): black top-hat of the luminance (3 cm structuring
         element) restricted to features longer than 0.8 m horizontally or vertically, as a multiplier 0..1. Lettering,
         logos and windows of the source livery are not kept, so no ghost titles show through a new livery.
      K  dark areas of the skin that stay as they are (anti-glare panel, radome, walkways): low-pass luminance below 55 %
         of the white level, only regions up to 1.5 m^2 (a whole dark crown or belly of the source livery is repainted)
      rgb the neutralised source colour (for K)"""
    out = {}
    h = m['head']; P, idx, UV = m['pos'], m['idx'], m['uv']
    for ti, im in enumerate(m['textures']):
        a = np.asarray(im).astype(np.float32) / 255
        lum = a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
        mats = [i for i, mm in enumerate(h['mats']) if mm['tex'] == ti]
        sel = np.isin(m['tri_mat'], mats)
        dens = 200.0
        if sel.any():
            T = idx[sel]
            A3 = np.linalg.norm(np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]]), axis=1) / 2
            U = UV[T] * np.array([im.size[0], im.size[1]])
            A2 = np.abs(np.cross(U[:, 1] - U[:, 0], U[:, 2] - U[:, 0])) / 2
            ok = (A3 > 1e-4) & (A2 > 1e-3)
            if ok.any(): dens = float(np.median(np.sqrt(A2[ok] / A3[ok])))
        r = max(1, int(round(0.03 * dens)))
        closed = ndimage.grey_closing(lum, size=(2 * r + 1, 2 * r + 1), mode='wrap')
        th = np.maximum(closed - lum, 0)
        # only line-like features: longer than 0.8 m horizontally or vertically (panel lines, door outlines), so the
        # lettering, logos and windows of the source livery are dropped
        Lp = max(5, int(round(0.8 * dens)))
        tb = th > 0.06
        lines = ndimage.binary_opening(tb, structure=np.ones((1, Lp), bool)) | ndimage.binary_opening(tb, structure=np.ones((Lp, 1), bool))
        lines = ndimage.binary_dilation(lines, iterations=1) & tb
        D = np.clip(1 - np.where(lines, th, 0) / np.maximum(closed, 0.05), 0, 1)
        base = ndimage.gaussian_filter(lum, max(2.0, 0.35 * dens), mode='wrap')
        wl = h['textures'][ti]['white']
        K0 = base < 0.55 * wl
        lab, n = ndimage.label(K0)
        if n:
            sizes = ndimage.sum(K0, lab, index=np.arange(1, n + 1))
            K0 = np.isin(lab, np.where(sizes <= 1.5 * dens * dens)[0] + 1)
        # where the source livery was painted (the original texture differs from the neutralised one), the old titles
        # and logos leave outlines: no detail and no kept-dark area there
        src = (orig or {}).get(h['textures'][ti]['name'])
        if src is not None:
            o = np.asarray(src.convert('RGB').resize(im.size, Image.BILINEAR)).astype(np.float32) / 255
            diff = np.abs(o - a[..., :3]).sum(-1) > 0.12
            diff = ndimage.binary_dilation(diff, iterations=max(2, int(round(0.05 * dens))))
            D[diff] = 1.0; K0[diff] = False
        out[ti] = (D, K0.astype(np.float32), a[..., :3])
    return out


def source_images(key):
    """the original (not neutralised) textures of the model's source, by image name (FlightAirMap .glb or FlightGear
    files, as tools/convert_models.py reads them); {} when the source checkout is not available"""
    os.environ.setdefault('FAM_DIR', os.path.join(common.ROOT, 'refs', 'cache', 'src', 'fam3d'))
    sys.path.insert(0, os.path.join(common.ROOT, 'tools'))
    try:
        import convert_models as cm
    except Exception:
        return {}
    out = {}
    if key in cm.MODELS and os.path.exists(cm.MODELS[key][0]):
        _, _, images, _ = cm.glb_primitives(cm.MODELS[key][0])
        for im in images:
            try: out[im['name']] = Image.open(io.BytesIO(im['data']))
            except Exception: pass
    elif key in ('b772', 'b77w') and key in cm.AC_MODELS:     # FlightGear 777: textures exported next to the .ac files
        for f in cm.AC_MODELS[key][0]:
            d = os.path.dirname(f)
            for line in open(f, 'r', errors='replace'):
                if line.startswith('texture '):
                    n = line.split('"')[1]; tp = os.path.join(d, n)
                    if os.path.basename(n) not in out and os.path.exists(tp): out[os.path.basename(n)] = Image.open(tp)
    elif key == 'b738':
        import subprocess
        repo = os.path.join(common.ROOT, 'refs', 'cache', 'src', 'fg', '737-800')
        try:
            data = subprocess.run(['git', 'show', 'HEAD:Models/737-800.png'], cwd=repo, capture_output=True, check=True).stdout
            out['737-800.png'] = Image.open(io.BytesIO(data))
        except Exception: pass
    return out


# ---------------------------------------------------------------- main
def process(key, S=2048, preview=None, outdir=None):
    src = source_path(key)
    m = sfom.load(src)
    # exact duplicate triangles of the source (double-sided copies: 1,897 on the FAM 747-8, 19,374 on the A380): the copy
    # that is occluded by its twin went to another chart layer and stayed unpainted, so the renderer showed a grey band
    # where it drew that copy first (review round 1, DLH 747-8); one copy is kept (the renderer draws both faces)
    kq = np.round(m['pos'][m['idx']] * 1000).astype(np.int64); kq.sort(axis=1)
    # of each duplicate set keep a 'paint' copy (the other copy can carry a glass / dark / untextured material: keeping it
    # left grey unpainted panels on the 747-8 body)
    paint = np.array([m['head']['mats'][i]['kind'] == 'paint' and m['head']['mats'][i]['tex'] >= 0 for i in m['tri_mat']])
    order = np.lexsort((np.arange(len(paint)), ~paint))
    _, fo = np.unique(kq.reshape(len(m['idx']), -1)[order], axis=0, return_index=True); first = order[fo]
    if len(first) < len(m['idx']):
        keep = np.zeros(len(m['idx']), bool); keep[first] = True
        print(f'  {key}: {len(m["idx"]) - len(first)} duplicate triangles dropped')
        m['idx'] = m['idx'][keep]; m['tri_mat'] = m['tri_mat'][keep]
    h = m['head']; A = common.app(); F = common.features()[key]
    # cabin windows: remove the artist windows the painted reference row replaces (tools/liveries/windows.py)
    wedit = edit_windows(m, key, A)
    dec = windows.decision(key, A)
    # fuselage plug bands (js/aircraft/fit.js PLUG_AT)
    bands = plug_bands(key, A)
    band_of = make_bands(m, bands) if bands else None
    env = common.Envelope(m['pos'], m['idx'], m['zone'], h['dims']['L'])
    T = A['types'][A['base'][key]]; s0 = T['fit']['s0'] if T['fit'] else 1.0
    seeds = [(sg * e['z'] / s0, e['r'] / s0) for e in (T['eng'] or []) for sg in (-1, 1)]
    part, eng_of, eng, Nf, area = classify(m, env, F, seeds)
    P, idx, UV, Nv, Z = m['pos'], m['idx'], m['uv'], m['nrm'], m['zone']
    Pb = band_positions(P, idx, band_of, bands) if bands else None
    charts = build_charts(m, part, eng_of, Nf, area, band_of, Pb)
    charts, kpm = pack(charts, P, idx, S, Pb)
    print(f'  {key}: {sum(len(c["tris"]) for c in charts)} atlas tris in {len(charts)} charts, {kpm:.1f} px/m at {S} '
          f'({100 / kpm:.2f} cm/px fuselage); engines {len(eng)}; kept {int((part == 0).sum())} tris; windows {dec["mode"]} '
          f'(removed glass {wedit["glass"]}, closed openings {wedit["holes"]}, strip tris {wedit["strip"]}); plug bands {bands}')
    # ---- new vertex arrays: kept triangles reuse their vertices; atlas triangles get one vertex per (chart, vertex)
    nv0 = len(P)
    newP = [P]; newN = [Nv]; newUV = [UV]; newZ = [Z]; srcUV = [UV]
    tri_new = idx.copy(); tri_atlas = np.zeros(len(idx), bool); tri_chart = np.full(len(idx), -1, np.int32)
    base = nv0
    for ci, c in enumerate(charts):
        T = c['tris']; vs = np.unique(idx[T]); remap = {v: base + i for i, v in enumerate(vs)}
        Q = proj(cpos(c, P, Pb)[vs], c['dir'])
        u = (c['x'] + PAD + (Q[:, 0] - c['lo'][0]) * c['k']) / S
        v = (c['y'] + PAD + (Q[:, 1] - c['lo'][1]) * c['k']) / S
        newP.append(P[vs]); newN.append(Nv[vs]); newZ.append(Z[vs]); newUV.append(np.stack([u, v], -1)); srcUV.append(UV[vs])
        tri_new[T] = np.vectorize(remap.get)(idx[T]); tri_atlas[T] = True; tri_chart[T] = ci
        base += len(vs)
    P2 = np.concatenate(newP); N2 = np.concatenate(newN); UV2 = np.concatenate(newUV); Z2 = np.concatenate(newZ); SUV = np.concatenate(srcUV)
    # ---- neutral bake
    tex, alpha, info = bake_neutral(m, key, S, charts, tri_new, tri_atlas, P2, SUV, UV2, env, A)
    # ---- materials: atlas materials (one per zone) are tex 0; source textures still used by kept triangles follow
    mats = h['mats']
    used_src = sorted({mats[i]['tex'] for i in np.unique(m['tri_mat'][~tri_atlas]) if mats[i]['tex'] >= 0})
    tex_remap = {t: i + 1 for i, t in enumerate(used_src)}
    new_mats = []; mat_remap = {}
    for i, mm in enumerate(mats):
        q = dict(mm); q['tex'] = tex_remap.get(mm['tex'], -1) if mm['tex'] >= 0 else -1
        mat_remap[i] = len(new_mats); new_mats.append(q)
    atlas_mat = {}
    for z in sorted({int(Z[idx[t, 0]]) for t in np.where(tri_atlas)[0]}):
        atlas_mat[z] = len(new_mats)
        new_mats.append(dict(kind='paint', zone=z, tex=0, white=WHITE, color=[1.0, 1.0, 1.0], rough=0.35, metal=0.0, alphaTest=False, atlas=True))
    tri_mat2 = np.array([atlas_mat[int(Z[idx[t, 0]])] if tri_atlas[t] else mat_remap[m['tri_mat'][t]] for t in range(len(idx))])
    # ---- draws: group triangles by (material)
    order = np.argsort(tri_mat2, kind='stable'); tri_sorted = tri_new[order]; mat_sorted = tri_mat2[order]
    draws = []
    for mi in np.unique(mat_sorted):
        sel = np.where(mat_sorted == mi)[0]
        draws.append(dict(mat=int(mi), first=int(sel[0] * 3), count=int(len(sel) * 3), zone=int(new_mats[mi]['zone'])))
    # drop vertices no triangle uses any more
    used = np.unique(tri_sorted); rm = -np.ones(len(P2), np.int64); rm[used] = np.arange(len(used))
    P2, N2, UV2, Z2 = P2[used], N2[used], UV2[used], Z2[used]; tri_sorted = rm[tri_sorted]
    # ---- textures: atlas (webp, RGBA) + the source textures still referenced
    rgba = np.concatenate([tex, alpha[..., None]], -1)
    atlas_img = Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')
    buf = io.BytesIO(); atlas_img.save(buf, 'WEBP', quality=88, method=6, alpha_quality=90)
    tex_out = [dict(name='livery-atlas', fmt='webp', w=S, h=S, data=buf.getvalue(), alpha=False, white=WHITE)]
    raw, B = m['raw'], m['B']
    for t in used_src:
        tt = dict(h['textures'][t]); tt['data'] = raw[B + tt['offset']:B + tt['offset'] + tt['length']]; tex_out.append(tt)
    atlas_meta = dict(v=2, size=S, pad=PAD, kpm=round(kpm, 3), white=WHITE, parts=PARTS, dirs=DIRS, eng=eng, winPainted=info['win'],
                      windows=dict(mode=dec['mode'], why=dec['why'], ref=dec.get('ref'), removed=wedit, painted=info['nwin']),
                      bands=[dict(b, eps=BAND_EPS) for b in bands],
                      charts=[dict(p=c['part'], s=int(c['sub']), d=int(c['dir']), l=int(c['layer']), x=int(c['x']), y=int(c['y']), w=int(c['w']), h=int(c['h']),
                                   k=round(float(c['k']), 4), a0=round(float(c['lo'][0]), 4), b0=round(float(c['lo'][1]), 4), band=int(c.get('band', -1))) for c in charts],
                      source=os.path.relpath(src, common.ROOT))
    if key in common.NORMAL_SMOOTH: N2, _ = common.smooth_normals(P2, N2, Z2, common.NORMAL_SMOOTH[key])   # lumpy nose skin
    head = write_sfom(key, h, P2, N2, UV2, Z2, tri_sorted, new_mats, draws, tex_out, atlas_meta, outdir)
    if preview:
        os.makedirs(preview, exist_ok=True)
        atlas_img.convert('RGB').resize((1024, 1024)).save(os.path.join(preview, f'{key}_atlas.png'))
        dbg = np.zeros((S, S, 3), np.float32)
        rng = np.random.default_rng(1)
        for c in charts:
            dbg[c['y']:c['y'] + c['h'], c['x']:c['x'] + c['w']] = rng.uniform(0.2, 0.9, 3)
        Image.fromarray((dbg * 255).astype(np.uint8)).resize((512, 512)).save(os.path.join(preview, f'{key}_charts.png'))
    return head


def bake_neutral(m, key, S, charts, tri_new, tri_atlas, P2, SUV, UV2, env, A):
    h = m['head']; mats = h['mats']
    T = np.where(tri_atlas)[0]
    tri_px = UV2[tri_new[T]] * S
    tid, bary = raster(tri_px, S, S)
    ok = tid >= 0; tt = T[np.maximum(tid, 0)]
    Vi = tri_new[tt]                                   # (S, S, 3) new vertex ids
    pos = (P2[Vi] * bary[..., None]).sum(-2)
    suv = (SUV[Vi] * bary[..., None]).sum(-2)
    dm = detail_maps(m, source_images(key))
    D = np.ones((S, S), np.float32); K = np.zeros((S, S), np.float32); orig = np.full((S, S, 3), WHITE, np.float32)
    texi = np.array([mats[i]['tex'] for i in m['tri_mat']])[tt]
    for ti, (Dm, Km, rgb) in dm.items():
        sel = ok & (texi == ti)
        if not sel.any(): continue
        u = suv[sel][:, 0] % 1.0; v = suv[sel][:, 1] % 1.0
        D[sel] = sample_bilinear(Dm[..., None], u, v)[:, 0]
        K[sel] = sample_bilinear(Km[..., None], u, v)[:, 0]
        orig[sel] = sample_bilinear(rgb, u, v)
    # cabin windows of the model's own type (tools/liveries/windows.py plan): painted as glass (alpha < 0.5); where the
    # artist windows were removed, dark areas of the source skin in the window band (painted source windows) are dropped
    base_t = A['base'][key]
    pl = windows.plan(key, base_t, env, A)
    side = part_is_fus_side(tid, T, charts, tri_atlas, S)
    kfus = np.median([c['k'] for c in charts if c['part'] == 'fus'])
    sp, yp = -pos[..., 0], pos[..., 1]
    wm = np.zeros((S, S), np.float32)
    # not in the plug bands: they are 2 cm wide on this type, and a stretched type gets its own bake (paint.py)
    nb = side & ~band_texels(charts, tid, S)
    if pl['win']:
        wm[nb] = windows.window_mask(sp[nb], yp[nb], pl['win'], 1.0 / kfus)
    # no dark source-skin areas in the window band of the fuselage sides: painted source windows (747-400, CRJ200) and
    # the texture under removed or kept glass must not show as a second row
    ref_rows = [(w['y'], w['h']) for w in pl['win']]
    if pl['mode'] == 'keep':
        ref_rows += [(g['y'], g['h']) for g in windows.artist(key)['glass']]
    for yrow in sorted({round(y, 2) for y, _ in ref_rows}):
        hmax = max(hh for y, hh in ref_rows if abs(y - yrow) < 0.01)
        K[side & (np.abs(yp - yrow) < hmax / 2 + 0.3)] = 0
        # where the artist windows were replaced: no skin detail in the row either (window frames drawn in the
        # source texture, e.g. the A350's grey windows, would otherwise show as a second row)
        if pl['mode'] == 'paint': D[side & (np.abs(yp - yrow) < hmax / 2 + 0.12)] = 1.0
    keep = K > 0.5
    col = np.repeat((WHITE * D)[..., None], 3, -1)
    col[keep] = orig[keep]
    alpha = np.where(keep, 0.75, 1.0).astype(np.float32)
    col = col * (1 - wm[..., None]) + np.array([0.075, 0.085, 0.10], np.float32) * wm[..., None]
    alpha = np.minimum(alpha, 1 - 0.9 * wm)          # glass: alpha 0.1 (not 0, so no encoder or viewer drops its colour)
    win = bool(pl['win'])
    col[~ok] = WHITE; alpha[~ok] = 1
    colA = np.concatenate([col, alpha[..., None]], -1)
    colA, _ = dilate_fill(colA, ok, radius=24)
    return colA[..., :3], colA[..., 3], dict(win=win, nwin=len(pl['win']))


def band_texels(charts, tid, S):
    """(S, S) bool: texel belongs to a plug-band chart"""
    out = np.zeros((S, S), bool)
    for c in charts:
        if c.get('band', -1) >= 0: out[c['y']:c['y'] + c['h'], c['x']:c['x'] + c['w']] = True
    return out & (tid >= 0)


def part_is_fus_side(tid, T, charts, tri_atlas, S):
    """(S, S) bool: texel belongs to a fuselage side chart (windows are only painted there)"""
    out = np.zeros((S, S), bool)
    for c in charts:
        if c['part'] == 'fus' and c['dir'] in (4, 5):
            out[c['y']:c['y'] + c['h'], c['x']:c['x'] + c['w']] = True
    return out & (tid >= 0)


def write_sfom(key, h, P, N, UV, Z, tri, mats, draws, tex_out, atlas_meta, outdir=None):
    plo, phi = P.min(0), P.max(0)
    # keep the source quantisation grid where possible (positions identical to the unatlased model)
    q0 = h['quant']
    pmin = np.array(q0['pmin']); pscale = np.array(q0['pscale'])
    if (plo < pmin - 1e-6).any() or (phi > pmin + pscale * 65535 + 1e-6).any():
        pmin = plo; pscale = (phi - plo) / 65535.0
    pq = np.round((P - pmin) / np.maximum(pscale, 1e-12)).astype(np.uint16)
    nq = np.round(np.clip(N, -1, 1) * 127).astype(np.int8)
    ulo, uhi = UV.min(0), UV.max(0); uscale = np.maximum(uhi - ulo, 1e-6) / 65535.0
    uq = np.round((UV - ulo) / uscale).astype(np.uint16)
    ib = tri.reshape(-1); idx_type = 'u16' if len(P) < 65536 else 'u32'
    ib = ib.astype(np.uint16 if idx_type == 'u16' else np.uint32)
    blob = io.BytesIO()
    def put(arr):
        off = blob.tell(); blob.write(arr.tobytes())
        while blob.tell() % 4: blob.write(b'\0')
        return off
    offs = dict(pos=put(pq), nrm=put(np.concatenate([nq, np.zeros((len(nq), 1), np.int8)], 1)), uv=put(uq), zone=put(Z.astype(np.uint8)), idx=put(ib))
    texs = []
    for t in tex_out:
        t = dict(t); data = t.pop('data'); t.pop('offset', None); t.pop('length', None)
        t['offset'] = blob.tell(); blob.write(data); t['length'] = len(data)
        while blob.tell() % 4: blob.write(b'\0')
        texs.append(t)
    head = dict(h); head.update(nv=int(len(P)), ni=int(len(ib)), idxType=idx_type, offsets=offs,
                                quant=dict(pmin=pmin.tolist(), pscale=pscale.tolist(), umin=ulo.tolist(), uscale=uscale.tolist()),
                                mats=mats, draws=draws, textures=texs, atlas=atlas_meta)
    hj = json.dumps(head, separators=(',', ':')).encode()
    while len(hj) % 4: hj += b' '
    raw = b'SFOM' + struct.pack('<II', 1, len(hj)) + hj + blob.getvalue()
    gz = gzip.compress(raw, 9)
    outdir = outdir or common.MD
    out = os.path.join(outdir, key + '.sfom')
    open(out, 'wb').write(gz)
    print(f'  -> {os.path.relpath(out, common.ROOT)}: verts {len(P)} tris {len(ib) // 3} textures {len(texs)} gz {len(gz) / 1e6:.2f} MB')
    # manifest.json bookkeeping (vertex / index counts, file size); MODEL_DIMS in manifest.js is unchanged (same geometry)
    mp = os.path.join(common.MD, 'manifest.json')
    if os.path.exists(mp) and os.path.abspath(outdir) == os.path.abspath(common.MD):
        man = json.load(open(mp))
        if key in man: man[key].update(nv=int(len(P)), ni=int(len(ib)), size=len(gz), atlas=True); json.dump(man, open(mp, 'w'), indent=1)
    return head


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('keys', nargs='*')
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--preview', default=None)
    ap.add_argument('--out', default=None, help='output directory (default data/models)')
    a = ap.parse_args()
    keys = a.keys or sorted(k[:-5] for k in os.listdir(common.MD) if k.endswith('.sfom'))
    for k in keys:
        print('==', k)
        process(k, a.size, a.preview, a.out)
