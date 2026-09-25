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
     walkways, exhaust stains) kept as they are. Models whose source has no cabin-window geometry (737-800, 747-400,
     A330-300, A380, CRJ200) get painted cabin windows at the type's window row (js/aircraft/types.js `win`, doors
     skipped). Alpha channel = class: 1 paint, 0.75 keep-original (dark), 0 window glass (night cabin glow).
  5. head.atlas records the charts and the parts so tools/liveries/paint.py can paint liveries into the same layout.

The first run backs the converted model up to refs/cache/models_orig/<key>.sfom (gitignored) and always rebuilds from
that backup, so the tool is idempotent. tools/convert_models.py output must be re-atlased after a re-conversion.

Usage: python3 tools/liveries/atlas.py [keys...] [--size 2048] [--preview DIR]
"""
import argparse, gzip, io, json, math, os, re, shutil, struct, sys
import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, sfom
from raster import raster, dilate_fill, sample_bilinear, occlusion

PARTS = ['keep', 'fus', 'fin', 'hstab', 'eng', 'pylon', 'tip', 'gdoor']
PID = {p: i for i, p in enumerate(PARTS)}
DENSITY = dict(fus=1.0, fin=1.0, hstab=0.55, eng=0.8, pylon=0.5, tip=0.9, gdoor=0.45)
DIRS = ['+x', '-x', '+y', '-y', '+z', '-z']
# textures that are never livery skin (cockpit / cabin interiors, gear, glazing, fan faces, chrome)
NONSKIN_TEX = re.compile(r'interior|carpet|seat|landing|gear|windshield|inside|chrome|^lights?\.', re.I)
FAN_TEX = re.compile(r'fan', re.I)
# models whose source has no cabin-window geometry: windows are painted into the atlas (js/aircraft/types.js win rows)
PAINT_WINDOWS = {'b738', 'b744', 'a333', 'a388', 'crj2'}
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


def build_charts(m, part, eng_of, Nf, area):
    P, idx = m['pos'], m['idx']
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
        groups.setdefault((p, sub, int(d)), []).append(t)
    charts = []
    for (p, sub, d), tl in groups.items():
        tl = np.array(tl)
        layer = 0
        while len(tl):
            # hidden-surface split: triangles mostly more than 12 cm behind another surface of the same chart (in its
            # projection direction) go to the next layer, so no two surfaces share texels
            Q = proj(P[idx[tl]], d); D = depth_of(P[idx[tl]], d)
            lo = Q.reshape(-1, 2).min(0); g = 0.05
            ext = Q.reshape(-1, 2).max(0) - lo
            if ext[0] * ext[1] / (g * g) > 4e6: g = math.sqrt(ext[0] * ext[1] / 4e6)
            px = (Q - lo) / g
            W = int(np.ceil(px[..., 0].max())) + 2; H = int(np.ceil(px[..., 1].max())) + 2
            frac, tot = occlusion(px, D.astype(np.float32), W, H, 0.12)
            hid = (tot >= 2) & (frac > 0.4)
            charts.append(dict(part=p, sub=sub, dir=d, layer=layer, tris=tl[~hid]))
            tl = tl[hid]; layer += 1
            if layer > 4:
                if len(tl): charts.append(dict(part=p, sub=sub, dir=d, layer=layer, tris=tl))
                break
    return [c for c in charts if len(c['tris'])]


def split_long(charts, P, idx, kpm, maxw):
    """cut charts wider than maxw pixels (at kpm px per metre x part density) into pieces along a"""
    out = []
    for c in charts:
        Q = proj(P[idx[c['tris']]], c['dir'])
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


def chart_rects(charts, P, idx, kpm):
    for c in charts:
        Q = proj(P[idx[c['tris']]], c['dir']); k = kpm * DENSITY[c['part']]
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


def pack(charts, P, idx, S):
    area = 0
    for c in charts:
        Q = proj(P[idx[c['tris']]], c['dir']); ext = Q.reshape(-1, 2).ptp(0); area += ext[0] * ext[1] * DENSITY[c['part']] ** 2
    kpm = math.sqrt(S * S * 0.8 / max(area, 1e-6))
    for _ in range(40):
        cs = split_long(charts, P, idx, kpm, S - 2 * PAD - 2)
        chart_rects(cs, P, idx, kpm)
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
    h = m['head']; A = common.app(); F = common.features()[key]
    env = common.Envelope(m['pos'], m['idx'], m['zone'], h['dims']['L'])
    T = A['types'][A['base'][key]]; s0 = T['fit']['s0'] if T['fit'] else 1.0
    seeds = [(sg * e['z'] / s0, e['r'] / s0) for e in (T['eng'] or []) for sg in (-1, 1)]
    part, eng_of, eng, Nf, area = classify(m, env, F, seeds)
    P, idx, UV, Nv, Z = m['pos'], m['idx'], m['uv'], m['nrm'], m['zone']
    charts = build_charts(m, part, eng_of, Nf, area)
    charts, kpm = pack(charts, P, idx, S)
    print(f'  {key}: {sum(len(c["tris"]) for c in charts)} atlas tris in {len(charts)} charts, {kpm:.1f} px/m at {S} '
          f'({100 / kpm:.2f} cm/px fuselage); engines {len(eng)}; kept {int((part == 0).sum())} tris')
    # ---- new vertex arrays: kept triangles reuse their vertices; atlas triangles get one vertex per (chart, vertex)
    nv0 = len(P)
    newP = [P]; newN = [Nv]; newUV = [UV]; newZ = [Z]; srcUV = [UV]
    tri_new = idx.copy(); tri_atlas = np.zeros(len(idx), bool); tri_chart = np.full(len(idx), -1, np.int32)
    base = nv0
    for ci, c in enumerate(charts):
        T = c['tris']; vs = np.unique(idx[T]); remap = {v: base + i for i, v in enumerate(vs)}
        Q = proj(P[vs], c['dir'])
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
    atlas_meta = dict(v=1, size=S, pad=PAD, kpm=round(kpm, 3), white=WHITE, parts=PARTS, dirs=DIRS, eng=eng, winPainted=info['win'],
                      charts=[dict(p=c['part'], s=int(c['sub']), d=int(c['dir']), l=int(c['layer']), x=int(c['x']), y=int(c['y']), w=int(c['w']), h=int(c['h']),
                                   k=round(float(c['k']), 4), a0=round(float(c['lo'][0]), 4), b0=round(float(c['lo'][1]), 4)) for c in charts],
                      source=os.path.relpath(src, common.ROOT))
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


def window_rows(key, A, env):
    """painted cabin windows in model units: list of (s0, s1, pitch, w, h, y, skip-list) from the base type's TYPES entry"""
    base = A['base'][key]; T = A['types'][base]; s0 = T['fit']['s0'] if T['fit'] else 1.0
    R = T['R']; topf = T['top']
    rows = []
    dw = 0.86 if T['cls'] in ('B', 'C', 'CL') else 1.07
    doors = [d / s0 for d in (T['doors'] or [])]
    for w in T['win']:
        hf = (w['y'] + R) / (R * (1 + topf))        # height of the window centre as a fraction of the procedural section
        y = env.mainBot + hf * (env.mainTop - env.mainBot)
        rows.append(dict(s0=w['x0'] / s0, s1=w['x1'] / s0, sp=w['sp'] / s0, w=w['w'] / s0, h=w['h'] / s0, y=y, doors=doors, dw=dw / s0))
    return rows


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
    col = np.repeat((WHITE * D)[..., None], 3, -1)
    keep = K > 0.5
    col[keep] = orig[keep]
    alpha = np.where(keep, 0.75, 1.0).astype(np.float32)
    # painted cabin windows
    win = key in PAINT_WINDOWS
    if win:
        rows = window_rows(key, A, env)
        wm = window_mask(pos, rows, part_is_fus_side(tid, T, charts, tri_atlas, S))
        col = col * (1 - wm[..., None]) + np.array([0.075, 0.085, 0.10], np.float32) * wm[..., None]
        alpha = np.minimum(alpha, 1 - wm)
    col[~ok] = WHITE; alpha[~ok] = 1
    colA = np.concatenate([col, alpha[..., None]], -1)
    colA, _ = dilate_fill(colA, ok, radius=24)
    return colA[..., :3], colA[..., 3], dict(win=win)


def part_is_fus_side(tid, T, charts, tri_atlas, S):
    """(S, S) bool: texel belongs to a fuselage side chart (windows are only painted there)"""
    out = np.zeros((S, S), bool)
    for c in charts:
        if c['part'] == 'fus' and c['dir'] in (4, 5):
            out[c['y']:c['y'] + c['h'], c['x']:c['x'] + c['w']] = True
    return out & (tid >= 0)


def window_mask(pos, rows, side):
    """soft mask (0..1) of rounded-rectangle cabin windows at the model positions pos (S, S, 3)"""
    s = -pos[..., 0]; y = pos[..., 1]
    M = np.zeros(s.shape, np.float32)
    px = 0.012
    for r in rows:
        k = np.round((s - r['s0']) / r['sp']); c = r['s0'] + k * r['sp']
        inrow = (k >= 0) & (c <= r['s1'] + 1e-6)
        for d in r['doors']:
            inrow &= np.abs(c - d) > (r['dw'] / 2 + r['w'] / 2 + 0.1)
        dx = np.abs(s - c) - (r['w'] / 2 - 0.35 * r['w']); dy = np.abs(y - r['y']) - (r['h'] / 2 - 0.35 * r['w'])
        rr = 0.35 * r['w']
        sd = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0) - rr
        M = np.maximum(M, np.where(inrow & side, np.clip(0.5 - sd / px, 0, 1), 0))
    return M


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
