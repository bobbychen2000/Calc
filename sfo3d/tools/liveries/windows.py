#!/usr/bin/env python3
"""Cabin windows: where the artist models have them, where the real aircraft have them, and what the livery atlas and
the painter do so that every model, type and brand shows exactly ONE row of windows (plus the upper deck of the 747
and A380), at the manufacturer's stations, count, pitch and height.

Owner feedback (Sep 2026): the livery renders showed TWO rows of cabin windows (a painted row plus a second, slightly
offset row). Cause: tools/liveries/atlas.py painted a window row from the procedural type table (js/aircraft/types.js
`win`, estimates) on five models it believed had no windows, while three of them have the artist's own windows: the
737-800 as openings in the skin with a dark strip behind them, the 747-400 and CRJ200 painted in their source textures
(the atlas kept them as "small dark areas"). The A330-300 and A380 sources really have none.

The rows of the real aircraft come from the manufacturers' drawings (tools/liveries/windows_ref.py ->
tools/liveries/windows_ref.json: Boeing CAD 3-views, Airbus AC, Bombardier APM). The artist rows were compared with
them (`python3 tools/liveries/windows.py`); several artist rows are wrong (787-8: 41 windows at 0.75 m pitch, the real
aircraft has 47 at 0.613 m (24 in); 737-800: the row starts 1.4 m late and ends 1.5 m early; 767-300, A350-900,
A319/A320: pitch / count / layout off). So:

  mode 'paint'  the model's artist windows are removed (glass objects deleted, openings in the skin closed, windows
                painted in the source texture dropped from the kept skin detail) and the painter paints the reference row
                of every rendered type (tools/liveries/paint.py; the neutral atlas gets the model's own type);
  mode 'keep'   the artist's glass windows match the reference (count within 2, 90 % of the reference windows within
                0.35 pitch of an artist window: MD-11, 757-200, A321) or there is no usable reference (E-Jets, CRJ700 /
                900, A220, 747-8: kept as modelled, unverified); artist windows that the reference does not have are
                removed; reference windows the artist lacks and the windows of fuselage plugs are painted, at the artist
                row's height.

Every type's row: its own drawing (REF_OK), or the row of a type with the same fuselage (REF_FROM, inferred), or the
row of the model's own type transformed by the type's fuselage plugs (js/aircraft/fit.js: a positive plug inserts
windows at the local pitch, a negative plug removes the windows of the removed section; inferred).

Usage: python3 tools/liveries/windows.py [keys...]   -> artist rows vs references, and the decision per model
"""
import collections, json, math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, sfom
from raster import raster

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'windows_ref.json')
# reference rows checked on their plots (windows_ref.py --plot): window count, pitch, first / last window, height; the
# scale is the drawing's own unit (Boeing CAD) or the published door stations (Airbus AC) or the overall length (CRJ200,
# checked against door 1)
REF_OK = {'b738', 'b37m', 'b38m', 'b39m', 'b3xm', 'b744', 'b752', 'b753', 'b762', 'b763', 'b764', 'b772', 'b77l', 'b773',
          'b77w', 'b779', 'b788', 'b789', 'b78x', 'md11', 'a319', 'a19n', 'a320', 'a20n', 'a321', 'a21n', 'a332', 'a333',
          'a338', 'a339', 'a359', 'a35k', 'a388', 'crj2'}
# types whose drawing shows no cabin windows, with a type of the same fuselage length and exit layout
REF_FROM = {'b739': ('b39m', '737-900 CAD 3-view (2001) draws no cabin windows; 737-9 fuselage: same length (42.11 m) '
                             'and plug stations')}
# window height (eta) taken from a type with the same fuselage cross-section where the drawing's outline scan measured
# too few windows (the A319 sheets are drawn at a smaller scale: 4 / 3 usable windows, eta 0.09 / 0.27 vs 0.33 on the
# A320 sheets; the A320 family shares the fuselage section and window line)
ETA_FROM = {'a319': 'a320', 'a19n': 'a20n'}
# door stations per window deck where the type table lists only the bridge doors: A380 (Airbus AC A380, FIGURE-2-7-0-
# 991-002-A01 Door Location: main deck M1-M5, upper deck U1-U3; the reference's row 0 is the upper deck)
DECK_DOORS = {'a388': {0: [20.94, 40.30, 49.19], 1: [6.32, 16.50, 32.68, 44.74, 53.63]}}
KEEP_COUNT, KEEP_DEV, KEEP_FRAC = 2, 0.35, 0.9
DOOR_CLEAR = 0.45          # m: no window centre within this + half a window width of a door centre (door windows)
_cache = {}


# ---------------------------------------------------------------- artist windows (source model before the atlas)
def _merge_ids(P, tol=0.001):
    q = np.round(P / tol).astype(np.int64); _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    return inv.reshape(-1), first


def _components(P, idx, sel, tol=0.002):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    inv, _ = _merge_ids(P, tol)
    T = inv[idx[sel]]; n = inv.max() + 1
    g = coo_matrix((np.ones(2 * len(T)), (np.r_[T[:, 0], T[:, 1]], np.r_[T[:, 1], T[:, 2]])), shape=(n, n))
    _, lab = connected_components(g, directed=False)
    return lab[T[:, 0]]


def _rows(W):
    """number the rows per side by height clusters: 0 = the row with most windows (main deck), 1 = next (upper deck)"""
    out = []
    for side in (-1, 1):
        w = [x for x in W if x['side'] == side]
        if len(w) < 6: continue
        ys = np.array([x['y'] for x in w]); order = np.argsort(ys); groups = [[order[0]]]
        for i in order[1:]:
            if ys[i] - ys[groups[-1][-1]] < 0.15: groups[-1].append(i)
            else: groups.append([i])
        groups = sorted([g for g in groups if len(g) >= 6], key=len, reverse=True)
        for gi, g in enumerate(groups):
            for i in g: w[i]['row'] = gi
            out += [w[i] for i in g]
    return sorted(out, key=lambda x: (x['side'], x['row'], x['s']))


def _glass(P, idx, tz, L):
    C = P[idx].mean(1); s = -C[:, 0]
    g = np.where((tz == 5) & (s > 0.1 * L) & (s < 0.9 * L) & (np.abs(C[:, 2]) > 0.4))[0]
    if not len(g): return [], np.zeros(0, int)
    lab = _components(P, idx, g)
    W = []; other = []
    for c in np.unique(lab):
        tr = g[lab == c]; V = P[idx[tr]].reshape(-1, 3)
        lo, hi = V.min(0), V.max(0); w, hh = hi[0] - lo[0], hi[1] - lo[1]
        if 0.12 < w < 0.6 and 0.15 < hh < 0.8:
            W.append(dict(s=float(-(lo[0] + hi[0]) / 2), y=float((lo[1] + hi[1]) / 2), w=float(w), h=float(hh), side=int(np.sign(V[:, 2].mean())), tris=tr))
        elif w > 3 and hh < 1.5: other.append(tr)          # a dark strip behind openings in the skin (737-800)
    return _rows(W), (np.concatenate(other) if other else np.zeros(0, int))


def _holes(P, idx, tz, L):
    """window-size openings in the body skin: ordered boundary loops (merged vertex ids + one source vertex per id)"""
    inv, first = _merge_ids(P)
    sel = np.where(tz == 0)[0]; T = inv[idx[sel]]
    # representative source vertex per merged position: a body-skin vertex (glass shares the openings' positions)
    first = first.copy(); first[T.reshape(-1)] = idx[sel].reshape(-1)
    E = collections.Counter()
    for a, b, c in T:
        for u, v in ((a, b), (b, c), (c, a)): E[(min(u, v), max(u, v))] += 1
    adj = collections.defaultdict(list)
    for (a, b), n in E.items():
        if n == 1: adj[a].append(b); adj[b].append(a)
    Pu = P[first]
    seen = set(); W = []
    for v0 in list(adj):
        if v0 in seen: continue
        # walk the loop
        loop = [v0]; seen.add(v0); prev = None; cur = v0; ok = True
        while True:
            nb = [q for q in adj[cur] if q != prev]
            if len(adj[cur]) != 2: ok = False
            if not nb: ok = False; break
            nxt = nb[0]
            if nxt == v0: break
            if nxt in seen: ok = False; break
            loop.append(nxt); seen.add(nxt); prev, cur = cur, nxt
        V = Pu[loop]; lo, hi = V.min(0), V.max(0)
        w, hh = hi[0] - lo[0], hi[1] - lo[1]; st = -(lo[0] + hi[0]) / 2
        if ok and 0.12 < w < 0.5 and 0.15 < hh < 0.7 and 0.1 * L < st < 0.9 * L and abs(V[:, 2].mean()) > 0.4 and (hi[2] - lo[2]) < 0.25:
            W.append(dict(s=float(st), y=float((lo[1] + hi[1]) / 2), w=float(w), h=float(hh), side=int(np.sign(V[:, 2].mean())), loop=[int(first[i]) for i in loop]))
    return _rows(W)


def _texture_windows(m, L):
    """dark window-sized blobs of the source textures on the fuselage sides, located on the model through the UVs"""
    from scipy import ndimage
    h = m['head']; P, idx, UV = m['pos'], m['idx'], m['uv']; Z = m['zone']; tz = Z[idx[:, 0]]
    mats = h['mats']; texi = np.array([mats[i]['tex'] for i in m['tri_mat']])
    C = P[idx].mean(1); s = -C[:, 0]
    W = []
    for ti, im in enumerate(m['textures']):
        sel0 = np.where((texi == ti) & (tz == 0) & (s > 0.08 * L) & (s < 0.92 * L))[0]
        if len(sel0) < 20: continue
        a = np.asarray(im.convert('RGB')).astype(np.float32) / 255; Ht, Wt = a.shape[:2]
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        dark = lum < 0.45 * h['textures'][ti].get('white', 0.9)
        lab, n = ndimage.label(dark)
        if n == 0: continue
        objs = ndimage.find_objects(lab)
        for side in (-1, 1):
            sel = sel0[np.sign(C[sel0, 2]) == side]
            if len(sel) < 10: continue
            U = UV[idx[sel]] % 1.0
            ok = (U.max(1) - U.min(1)).max(1) < 0.5
            sel = sel[ok]; U = U[ok]
            tid, bary = raster(U * np.array([Wt, Ht]), Wt, Ht)
            hit = tid >= 0
            pos = np.zeros((Ht, Wt, 3)); pos[hit] = (P[idx[sel[tid[hit]]]] * bary[hit][..., None]).sum(1)
            for k, sl in enumerate(objs):
                if sl is None: continue
                mk = (lab[sl] == k + 1) & hit[sl]
                if mk.sum() < 3: continue
                Q = pos[sl][mk]; lo, hi = Q.min(0), Q.max(0); w, hh = hi[0] - lo[0], hi[1] - lo[1]; st = -(lo[0] + hi[0]) / 2
                if 0.08 < w < 0.5 and 0.1 < hh < 0.7 and abs(Q[:, 2].mean()) > 0.4 and 0.1 * L < st < 0.9 * L and hh > 0.8 * w:
                    W.append(dict(s=float(st), y=float((lo[1] + hi[1]) / 2), w=float(w), h=float(hh), side=side, tex=ti))
    W.sort(key=lambda x: (x['side'], x['s']))
    out = []
    for x in W:
        if out and out[-1]['side'] == x['side'] and abs(out[-1]['s'] - x['s']) < 0.05 and abs(out[-1]['y'] - x['y']) < 0.05: continue
        out.append(x)
    return _rows(out)


def artist(key):
    """the artist's cabin windows of model `key` (model units: s = station aft of the nose tip, y up, z starboard):
    kind 'geometry' | 'holes' | 'texture' | 'none'; win (the windows of that kind), glass / holes (both lists, a model
    can have glass objects over openings in the skin), strip (other cabin glass triangles, e.g. a dark strip)"""
    if key in _cache: return _cache[key]
    m = sfom.load(os.path.join(common.ORIG, key + '.sfom'), textures=True)
    h = m['head']; P, idx, Z = m['pos'], m['idx'], m['zone']
    L = h['dims']['L']; tz = Z[idx[:, 0]]
    glass, strip = _glass(P, idx, tz, L)
    holes = _holes(P, idx, tz, L)
    tex = _texture_windows(m, L) if len(glass) < 12 and len(holes) < 12 else []
    if len(glass) >= 12: kind, win = 'geometry', glass
    elif len(holes) >= 12: kind, win = 'holes', holes
    elif len(tex) >= 12: kind, win = 'texture', tex
    else: kind, win = 'none', []
    res = dict(kind=kind, win=win, glass=glass, holes=holes, texture=tex, strip=strip, L=float(L))
    _cache[key] = res
    return res


# ---------------------------------------------------------------- reference rows
_ref = None
def reference(t):
    global _ref
    if _ref is None: _ref = json.load(open(REF)) if os.path.exists(REF) else {}
    r = _ref.get(t)
    return r if r and 'error' not in r else None


def _door_filter(s, w, doors):
    if not doors: return np.ones(len(s), bool)
    d = np.abs(np.asarray(s)[:, None] - np.asarray(doors)[None, :]).min(1)
    return d > DOOR_CLEAR + w / 2


def _plug_transform(s, pitch, plugs):
    """window stations (m, base type) -> stations of a type with fuselage plugs {at1, at2, d1, d2} (m): a positive plug
    shifts everything aft of its station and inserts windows at the local pitch in the gap; a negative plug removes
    the windows of the removed section [at, at + |d|] and shifts the rest forward"""
    s = np.sort(np.asarray(s, float)); ins = []
    out = s.copy()
    for at, d in ((plugs['at1'], plugs['d1']), (plugs['at2'], plugs['d2'])):
        if abs(d) < 1e-6: continue
        if d > 0:
            aft = s > at; out = np.where(aft, out + d, out)
            # windows around the plug (base stations) and the gap they leave
            fwd = s[s <= at]; aftw = s[s > at]
            if len(fwd) and len(aftw):
                a = fwd.max(); b = aftw.min()
                a2 = out[s == a][0]; b2 = out[s == b][0]
                p = pitch
                n = int(round((b2 - a2) / p)) - 1
                if n > 0: ins += list(a2 + (b2 - a2) * np.arange(1, n + 1) / (n + 1))
        else:
            keep = ~((s > at) & (s < at - d))
            out = np.where(s >= at - d, out + d, out)
            out[~keep] = np.nan
    res = np.sort(np.concatenate([out[~np.isnan(out)], ins])) if ins else np.sort(out[~np.isnan(out)])
    return res, np.array(sorted(ins))


def type_rows(t, A=None):
    """reference rows of type t in metres of that type: [dict(s, eta, w, h, pitch, dy, deck, src, inf, inserted)]"""
    A = A or common.app()
    T = A['types'][t]
    doors = list(T['doors'] or []) + list(T.get('doorsOpt') or [])
    src, inf, base_t, plugs = None, False, t, None
    if t in REF_OK and reference(t): r = reference(t); src = r['src']
    elif t in REF_FROM and reference(REF_FROM[t][0]): r = reference(REF_FROM[t][0]); src = r['src'] + ' (inferred: ' + REF_FROM[t][1] + ')'; inf = True
    else:
        f = T['fit']
        if not f: return []
        base_t = A['base'][f['model']]
        r = reference(base_t) if base_t in REF_OK else None
        if r is None: return []
        plugs = f['plugs']; inf = True
        src = r['src'] + f' (inferred: the {base_t} row with the {t} fuselage plugs of js/aircraft/fit.js)'
    rows = []
    eta = r['eta']
    if base_t in ETA_FROM and reference(ETA_FROM[base_t]): eta = reference(ETA_FROM[base_t])['eta']; src += f' (height: {ETA_FROM[base_t]} drawing)'
    decks = [dict(s=r['s'], eta=eta, w=r['w'], h=r['h'], pitch=r['pitch'], dy=0.0, deck=0)]
    for k, x in enumerate(r.get('rows', [])):
        decks.append(dict(s=x['s'], eta=x.get('eta'), w=x['w'], h=x['h'], pitch=x['pitch'], dy=x['dy'], deck=k + 1))
    for d in decks:
        s = np.array(d['s'], float); ins = np.zeros(0)
        if plugs: s, ins = _plug_transform(s, d['pitch'], plugs)
        # door windows are not cabin windows: the main deck against the type's doors, other decks against their own
        dd = DECK_DOORS.get(base_t, {}).get(d['deck'], doors if d['deck'] == 0 and base_t not in DECK_DOORS else [])
        s = s[_door_filter(s, d['w'], dd)]
        rows.append(dict(d, s=s, inserted=ins, src=src, inf=inf, type=t))
    return rows


# ---------------------------------------------------------------- per model: keep or paint
def decision(key, A=None):
    A = A or common.app()
    t = A['base'][key]; T = A['types'][t]; s0 = T['fit']['s0'] if T['fit'] else 1.0
    a = artist(key)
    r = reference(t) if t in REF_OK else None
    geo = [x for x in a['glass'] if x['side'] == -1 and x['row'] == 0]
    if a['kind'] != 'geometry':
        return dict(mode='paint', why=f"artist windows are {a['kind']}", ref=t if r else None)
    if r is None:
        return dict(mode='keep', why='no usable manufacturer drawing: artist glass windows kept (unverified)', ref=None)
    S = np.array([x['s'] * s0 for x in geo]); R = np.array(r['s']); p = r['pitch']
    dev = np.abs(R[:, None] - S[None, :]).min(1)
    frac = float(np.mean(dev < KEEP_DEV * p)); dn = len(S) - len(R)
    st = dict(n_artist=len(S), n_ref=len(R), matched=frac, pitch_artist=float(np.median(np.diff(S))), pitch_ref=p)
    if abs(dn) <= KEEP_COUNT and frac >= KEEP_FRAC:
        return dict(mode='keep', why=f'artist glass matches the drawing ({len(S)} vs {len(R)} windows, {frac:.0%} within {KEEP_DEV} pitch)', ref=t, stats=st)
    return dict(mode='paint', why=f'artist glass differs from the drawing ({len(S)} vs {len(R)} windows, {frac:.0%} within {KEEP_DEV} pitch, pitch {st["pitch_artist"]:.3f} vs {p:.3f} m)', ref=t, stats=st)


def removals(key, A=None):
    """what atlas.py removes from the source model: glass triangles to delete, hole loops to close, and whether painted
    texture windows must be dropped from the kept skin"""
    A = A or common.app()
    dec = decision(key, A); a = artist(key)
    t = A['base'][key]; s0 = A['types'][t]['fit']['s0'] if A['types'][t]['fit'] else 1.0
    if dec['mode'] == 'paint':
        glass = [x for x in a['glass']]; holes = [x for x in a['holes']]
        return dict(glass=glass, holes=holes, strip=a['strip'], texture=bool(a['texture']), mode='paint')
    # keep: remove the artist windows the reference does not have (and their openings)
    r = reference(dec['ref']) if dec['ref'] else None
    if r is None:
        # no reference: only an isolated artist window ahead of door 1 on a single-deck regional / narrow-body type is
        # removed (E175 model: a glass object at 3.14 m, 3.7 m ahead of the row, in front of the door at 5.14 m; the E170
        # model with the same nose has none)
        T = A['types'][t]; extra = []
        if T['cls'] in ('B', 'C', 'CL') and T['doors']:
            for side in (-1, 1):
                w = sorted([x for x in a['glass'] if x['side'] == side and x['row'] == 0], key=lambda x: x['s'])
                if len(w) > 3:
                    p = float(np.median(np.diff([x['s'] for x in w])))
                    if w[0]['s'] * s0 < T['doors'][0] and w[1]['s'] - w[0]['s'] > 2.5 * p: extra.append(w[0])
        hs = [x for x in a['holes'] if any(abs(x['s'] - g['s']) < 0.05 and x['side'] == g['side'] and abs(x['y'] - g['y']) < 0.1 for g in extra)]
        return dict(glass=extra, holes=hs, strip=np.zeros(0, int), texture=False, mode='keep')
    R = np.array(r['s']) / s0; p = r['pitch'] / s0
    extra = [x for x in a['glass'] if np.abs(R - x['s']).min() > KEEP_DEV * p]
    hs = [x for x in a['holes'] if any(abs(x['s'] - g['s']) < 0.05 and x['side'] == g['side'] and abs(x['y'] - g['y']) < 0.1 for g in extra)]
    return dict(glass=extra, holes=hs, strip=np.zeros(0, int), texture=False, mode='keep')


def barrel(env, L):
    """centre and half height of the model's constant fuselage section: median top / bottom between 20 and 32 % of the
    length (ahead of the wing-body fairing)"""
    m = (env.s > 0.2 * L) & (env.s < 0.32 * L)
    top, bot = float(np.median(env.top[m])), float(np.median(env.bot[m]))
    return (top + bot) / 2, (top - bot) / 2


def plan(key, t, env, A=None):
    """windows to paint for type t on model key, in the rendered (stretched) model frame (model units: s aft of the nose
    tip, y up): list of dict(s, y, w, h, deck); `env` = fuselage envelope of the stretched model (common.Envelope)"""
    A = A or common.app()
    T = A['types'][t]; f = T['fit']; sc = f['s'] if f else 1.0
    dec = decision(key, A)
    rows = type_rows(t, A)
    L = env.L; yc, hh = barrel(env, L)
    out = []
    if dec['mode'] == 'paint':
        y0 = yc + rows[0]['eta'] * hh if rows and rows[0]['eta'] is not None else yc
        for r in rows:
            # further decks: their own measured height, else the main row + the drawing's vertical offset
            y = yc + r['eta'] * hh if r['eta'] is not None else y0 + r['dy'] / sc
            for s in r['s']: out.append(dict(s=float(s / sc), y=float(y), w=r['w'] / sc, h=r['h'] / sc, deck=r['deck']))
        return dict(mode='paint', win=out, rows=rows, why=dec['why'])
    # keep: the artist glass (minus removals), stretched; paint the reference windows it does not cover
    a = artist(key); rem = removals(key, A)
    gone = {id(x) for x in rem['glass']}
    geo = [x for x in a['glass'] if id(x) not in gone and x['side'] == -1]
    st = (f or {}).get('stretch') or {}
    # stretch applies to the ORIGINAL x for both cuts (js/live/models.js applyStretch)
    def rx2(s):
        x = -s; dx = 0.0
        for c, d in ((st.get('cut1'), st.get('d1')), (st.get('cut2'), st.get('d2'))):
            if c is None: continue
            if d >= 0: dx += -d if x < c else 0.0
            else: dx += (-d if x < c + d else (c - x if x < c else 0.0))
        return -(x + dx)
    G = np.array([rx2(x['s']) for x in geo]) if geo else np.zeros(0)
    gy = float(np.median([x['y'] for x in geo if x['row'] == 0])) if geo else yc
    gw = float(np.median([x['w'] for x in geo])) if geo else 0.25 / sc
    gh = float(np.median([x['h'] for x in geo])) if geo else 0.35 / sc
    if not rows:
        # no reference: fill the plug gaps from the artist row itself (stretched), at its pitch
        if not geo or not f or not f['plugs']: return dict(mode='keep', win=[], rows=[], why=dec['why'])
        S = np.array(sorted(x['s'] for x in geo if x['row'] == 0)); p = float(np.median(np.diff(S)))
        pl = dict(f['plugs']); pl.update(d1=pl['d1'] / f['s0'], d2=pl['d2'] / f['s0'], at1=pl['at1'] / f['s0'], at2=pl['at2'] / f['s0'])
        _, ins = _plug_transform(S, p, pl)
        out = [dict(s=float(s), y=gy, w=gw, h=gh, deck=0) for s in ins]
        return dict(mode='keep', win=out, rows=[], why=dec['why'] + '; plug windows from the artist pitch (inferred)')
    for r in rows:
        if r['deck'] != 0: continue
        p = r['pitch'] / sc
        for s in r['s']:
            s_m = s / sc
            if len(G) and np.abs(G - s_m).min() < 0.6 * p: continue
            out.append(dict(s=float(s_m), y=gy, w=gw, h=gh, deck=0))
    return dict(mode='keep', win=out, rows=rows, why=dec['why'])


def window_mask(s, y, win, tex):
    """soft mask (0..1) of rounded-rectangle windows at texel positions (s, y) (model units), texel size tex (m)"""
    M = np.zeros(len(s), np.float32)
    if not win: return M
    W = np.array([[w['s'], w['y'], w['w'], w['h']] for w in win])
    order = np.argsort(W[:, 0]); W = W[order]
    for k in range(len(W)):
        cs, cy, ww, hh = W[k]
        q = np.where((np.abs(s - cs) < ww) & (np.abs(y - cy) < hh))[0]
        if not len(q): continue
        rr = 0.38 * ww
        dx = np.abs(s[q] - cs) - (ww / 2 - rr); dy = np.abs(y[q] - cy) - (hh / 2 - rr)
        sd = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0) - rr
        t = tex[q] if np.ndim(tex) else tex
        M[q] = np.maximum(M[q], np.clip(0.5 - sd / np.maximum(t, 1e-4), 0, 1))
    return M


if __name__ == '__main__':
    A = common.app()
    keys = sys.argv[1:] or sorted(A['base'])
    for k in keys:
        a = artist(k); t = A['base'][k]; T = A['types'][t]; s0 = T['fit']['s0'] if T['fit'] else 1.0
        dec = decision(k, A)
        print(f"{k:5s} artist {a['kind']:8s} glass {len([x for x in a['glass'] if x['side'] < 0])} holes {len([x for x in a['holes'] if x['side'] < 0])} "
              f"texture {len([x for x in a['texture'] if x['side'] < 0])} (port)  ->  {dec['mode']}: {dec['why']}")
        for tt in sorted(x for x in A['typeModel'] if A['typeModel'][x] == k):
            rows = type_rows(tt, A)
            if rows:
                r = rows[0]
                print(f"      {tt:5s} {len(r['s']):3d} windows {r['s'][0]:6.2f}..{r['s'][-1]:6.2f} m pitch {r['pitch']:.3f} eta {r['eta']}"
                      + (f" +{len(r['inserted'])} in plugs" if len(r['inserted']) else '') + (' [inf]' if r['inf'] else '')
                      + ''.join(f" | deck{x['deck']} {len(x['s'])}" for x in rows[1:]))
            else: print(f'      {tt:5s} no reference row')
