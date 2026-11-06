"""Elevated landside roadways as a 3-D asset: data/buildings3d/roadways.glb (LOD0-2) + roadways_lod2.glb, the check sheet
out/buildings3d/roadways_plan.png and manifest.json#roadways. numpy + scipy + shapely + Pillow; no bpy (the geometry is
plain extrusion along the OSM centrelines, written to glTF 2.0 directly).

    python3 tools/blender/build_roadways.py            # ~1-2 min (reads the other assets' GLBs for the clash trimming)

Integration review round 1, finding 1 ("none of the elevated roadways exist in 3-D ... nobody owns this"): the
integration step owns them. What is built, and from what (tags as in the other groups' manifests):
  network / levels   tools/blender/roadways_net.py (OSM topology [obs ODbL], widths [osm / inf], levels: the ITB L3 curb
                     [inf], the domestic departures curb [unk placeholder], the rest solved under clearance constraints
                     [inf]); the approach ramps are the at-grade OSM roads the solve lifts above 0.3 m (on fill) [inf]
  deck               ribbon along each centreline, carriageway (OSM lanes x 3.6 m / class default) + SHOULDER each side
                     [inf]; where ribbons of one level overlap (merges, diverges) the higher-priority one keeps the
                     overlap (anchored > wider > ramps), so no two surfaces share a place; DECK_DEPTH 1.2 m [inf]
  trimmed by assets  every ribbon minus what the other assets occupy in its own height band (their exported triangles,
                     tools/blender/b3d_integrate.py occupancy): the ITB L3 curb sidewalk, the domestic curb decks and
                     canopies, garage walls, AirTrain columns - so the deck stops at the curb and never enters a building
  fascia, parapets   on the outer edges (not against another ribbon of the same level, not against an asset): fascia
                     from the deck top to the soffit, a concrete barrier 0.40 x 0.85 m [inf: Caltrans Type 736-like]
  fill               where the deck is lower than FILL_H the structure is solid to grade (retaining walls; approach ramps)
  columns            round piers D_COL at ~COL_SPACING along the centreline where the soffit is >= 2 m; each placed only
                     where it stands clear of at-grade carriageways (data/sfo_landside.json, + 0.3 m), of lower decks and
                     of every asset (tried on the centreline, then across the deck and +-6 m along it, else omitted: a
                     longer span) [inf positions; no structural drawings]
  lane marks         own painted tiles (MUTCD 3A / 3B: 10-ft dashes on 40-ft cycles, 4-in lines, white lane lines, yellow
                     left edge on one-way roads) on the deck top [inf: lane count from OSM]
  colours            asphalt: NAIP 2024 median over the deck tops (the roofs of this asset) x NAIP_ALBEDO (the
                     integration note: NAIP DN-as-albedo is ~1.75x the app's ground) [obs colour, inf scale]; concrete
                     [inf]
LOD: LOD0 everything; LOD1 deck, fascia, parapets, 8-sided columns, no lane tiles beyond 400 m; LOD2 (also roadways_lod2.glb)
deck + fascia + 6-sided columns, plain asphalt. Units (extras.building): one per connected structure group
(itb_departures, domestic_departures, the interchange ramps by area), switched per unit by js/three/buildings3d.js.
Frame ltp-nad83-2011 as the other assets: root at [cx, GROUND_Y, cz], y up, metres."""
import hashlib, io, json, math, os, struct, sys, time
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union, substring

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import roadways_net as RN  # noqa: E402
import b3d_integrate as BI  # noqa: E402
import roadways_itb_plate as RP  # noqa: E402

D3 = os.path.join(ROOT, 'data', 'buildings3d'); OUTD = os.path.join(ROOT, 'out', 'buildings3d')
GROUND_Y = 3.0
SHOULDER = 0.6        # m each side of the carriageway (deck width = carriageway + 2 x shoulder) [inf]
PARAPET_W, PARAPET_H = 0.40, 0.85   # [inf]
FILL_H = 3.2          # deck top below this: solid fill to grade (soffit would be < 2 m) [inf]
COL_SPACING, D_COL = 30.0, 1.4      # [inf]
DASH_CYCLE = 12.192   # 40 ft (MUTCD 3A.06: 10-ft line segments, 30-ft gaps)
NAIP_ALBEDO = 1 / 1.75
SWITCH = {0: 0.0, 1: 400.0, 2: 1400.0}
CONCRETE = (172, 170, 163)  # sRGB [inf]


def srgb2lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ------------------------------------------------------------------------------------------------ pieces
def pieces_of(ways, ramps):
    """road pieces with a level profile: the elevated ways, and the lifted parts (h > 0.15 m) of the approach ramps"""
    P = []
    for w in ways:
        P.append(dict(id=w['id'], src='deck', w=w['w'], lanes=w['lanes'], oneway=w['oneway'], anchor=w['anchor'], layer=w['layer'],
                      pts=w['pts'], s=w['s'], h=w['h'], nodes=w['nodes'], name=w.get('name'), kind=w.get('kind')))
    for g in ramps:
        ls = LineString(g['pts']); hs = g['h']; s = g['s']
        up = hs > 0.15
        # intervals of s where the ramp is lifted (with the crossing to 0.15 interpolated)
        k = 0
        while k < len(up):
            if not up[k]: k += 1; continue
            k0 = k
            while k < len(up) and up[k]: k += 1
            a = s[k0 - 1] + (0.15 - hs[k0 - 1]) / (hs[k0] - hs[k0 - 1]) * (s[k0] - s[k0 - 1]) if k0 > 0 else 0.0
            b = s[k - 1] + (hs[k - 1] - 0.15) / (hs[k - 1] - hs[k]) * (s[k] - s[k - 1]) if k < len(up) else s[-1]
            if b - a < 2.0: continue
            seg = substring(ls, a, b); Q = np.array(seg.coords); sq = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(Q, axis=0).T))])
            hq = np.interp(sq + a, s, hs)
            P.append(dict(id=g['id'], src='ramp', w=g['w'], lanes=g['lanes'], oneway=g['oneway'], anchor=None, layer=0, pts=Q, s=sq, h=hq,
                          nodes=g['nodes'], name=None, kind='ramp'))
    for p in P:
        p['line'] = LineString(p['pts']); p['half'] = p['w'] / 2 + SHOULDER
        p['rib'] = p['line'].buffer(p['half'], cap_style='flat', join_style='round', quad_segs=4)
        p['hmin'], p['hmax'] = float(p['h'].min()), float(p['h'].max())
    return P


def hp(p, xz):
    """deck-top level of piece p at plan points xz (projection onto its centreline)"""
    s = shapely.line_locate_point(p['line'], shapely.points(np.asarray(xz)))
    return np.interp(s, p['s'], p['h'])


def units_of(P):
    """connected structure groups (shared OSM nodes / overlapping ribbons) -> unit names"""
    n = len(P); par = list(range(n))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    nodes = {}
    for i, p in enumerate(P):
        for q in p['nodes']:
            if not isinstance(q, tuple): nodes.setdefault(q, []).append(i)
    for L in nodes.values():
        for j in L[1:]: par[f(j)] = f(L[0])
    comp = {}
    for i in range(n): comp.setdefault(f(i), []).append(i)
    names = {}
    anch = [p for p in P if p['anchor']]
    for i, p in enumerate(P):
        if p['anchor']: names[i] = p['anchor'] + '_departures'; continue
        d = min(((p['line'].distance(q['line']), q['anchor']) for q in anch), default=(1e9, None))
        if d[0] < 120: names[i] = d[1] + '_departures'
        else: c = p['pts'].mean(0); names[i] = 'interchange_%d_%d' % (int((c[0] + 2400) // 300), int((c[1] + 300) // 300))
    for i, p in enumerate(P): p['unit'] = names[i]
    return sorted(set(names.values()))
    for c, L in comp.items():
        an = {P[i]['anchor'] for i in L if P[i]['anchor']}
        cen = np.mean(np.concatenate([P[i]['pts'] for i in L]), 0)
        if 'itb' in an: nm = 'itb_departures'
        elif 'domestic' in an: nm = 'domestic_departures'
        else: nm = 'viaduct_%s%d_%s%d' % ('w' if cen[0] < 0 else 'e', abs(int(cen[0] // 500)), 'n' if cen[1] < 0 else 's', abs(int(cen[1] // 500)))
        for i in L: names[i] = nm
    for i, p in enumerate(P): p['unit'] = names[i]
    return sorted(set(names.values()))


ENC_STEP, ENC_DY = 1.0, 2.0   # enclosure test grid (m) and height of the test points above the deck top (m)


def enclosure_cuts(P, TR, F0, log):
    """review round 2 (finding 3: the domestic departures deck ran 115 m inside the Terminal 2 shell, and 1-3 m inside T1
    / T3; the surface-band test cannot see a deck inside a hollow shell): every deck is sampled on an ENC_STEP grid where
    it overlaps a domestic / ITB / tower unit's footprint, ENC_DY above its top, and each point is tested with
    b3d_integrate.enclosed (a roof above and walls on >= 3 of 4 sides: inside the building). The enclosed cells, grown by
    one cell and clipped to the footprint, are cut from the deck. Overhangs (curb canopies, eaves) are not enclosures,
    so a road under a canopy stays. Returns {(group, unit): plan region} for the trim and the report."""
    out = {}
    for g in ('domestic', 'itb', 'tower'):
        for u, L in F0.get(g, {}).items():
            if u in ('*', 'all'): continue
            T = TR['_lods'].get((g, u, 0))
            if T is None: continue
            fp = unary_union([e['geom'] for l, e in L.items() if l < 2] or [e['geom'] for e in L.values()]); fpb = fp.buffer(1.0); shapely.prepare(fpb)
            cells = []
            for p in P:
                if not p['rib'].intersects(fpb): continue
                X = p['rib'].intersection(fpb)
                if X.area < 1.0: continue
                x0, z0, x1, z1 = X.bounds; xs = np.arange(x0 + ENC_STEP / 2, x1, ENC_STEP); zs = np.arange(z0 + ENC_STEP / 2, z1, ENC_STEP)
                if not len(xs) or not len(zs): continue
                XX, ZZ = np.meshgrid(xs, zs); q = np.c_[XX.ravel(), ZZ.ravel()]; q = q[shapely.contains_xy(X, q[:, 0], q[:, 1])]
                if not len(q): continue
                h = hp(p, q); P3 = np.c_[q[:, 0], GROUND_Y + h + ENC_DY, q[:, 1]]
                e = BI.enclosed(T, P3, TW=BI.group_walls(TR, g, fp.bounds))   # walls of the whole group: a unit's shell is open where it joins the next
                if e.any(): cells += [box(a - ENC_STEP / 2, b - ENC_STEP / 2, a + ENC_STEP / 2, b + ENC_STEP / 2) for a, b in q[e]]
            if cells:
                out[(g, u)] = unary_union(cells).buffer(ENC_STEP, join_style='mitre').intersection(fp)
    log('decks inside buildings (enclosure test, review r2): %s' % (', '.join('%s/%s %.0f m2' % (g, u, v.area) for (g, u), v in sorted(out.items())) or 'none'))
    return out


STACK_GAP = 0.6   # m: the lower of two stacked decks stops this far short of the upper deck's ribbon (review round 2)


def trim(P, TR, log, BODY=None):
    """same-level overlaps go to the higher-priority piece; then every piece minus the assets' occupancy in its band and
    minus the parts that run inside a building (enclosure_cuts, review round 2)"""
    order = sorted(range(len(P)), key=lambda i: (P[i]['anchor'] is None, P[i]['src'] == 'ramp', -P[i]['w'], P[i]['id']))
    kept = []
    for r, i in enumerate(order):
        p = P[i]; g = p['rib']
        for j in kept:
            q = P[j]
            if not g.intersects(q['geom']): continue
            X = g.intersection(q['geom'])
            if X.is_empty or X.area < 0.05: continue
            # same level where they overlap? (their levels at the overlap's points)
            pts = np.array([c for poly in (getattr(X, 'geoms', None) or [X]) if isinstance(poly, Polygon) for c in poly.exterior.coords])
            if not len(pts): continue
            dhs = hp(p, pts) - hp(q, pts); dh = np.abs(dhs)
            if np.median(dh) < 1.0: g = g.difference(q['geom'].buffer(0.02))
            elif np.median(dh) < RN.DECK_DEPTH + RN.CLEAR_MIN:
                # review round 2: two decks overlapping in plan with less than deck + clearance between them (a diverge
                # whose ribbons still overlap where one has begun to climb): the LOWER one gives the overlap up, so the
                # upper deck's edge stands beside it instead of 1-5 m over it (the integration clearance check found
                # 824 m2 of deck under another deck at < 4.6 m)
                # (+ STACK_GAP: the upper deck's parapet and soffit edge overhang its ribbon; with 0.05 m, 1.0-1.3 m slivers stayed)
                if np.median(dhs) < 0: g = g.difference(q['geom'].buffer(STACK_GAP))
                else: q['geom'] = q['geom'].difference(g.intersection(q['geom']).buffer(STACK_GAP)); q.setdefault('stacked_cut_by', []).append(p['id'])
        p['geom'] = g; kept.append(i)
    # assets: occupancy (triangles) in the piece's band, chunk by chunk along it (a ramp spans 0-11 m). Review r2: the
    # other assets' LOD0 / LOD1 triangles only (their LOD2 shells are coarser - the ITB curb's by ~3 m at its ends - and
    # are drawn only beyond 1.2-1.6 km, where this asset shows its own LOD2): a LOD2 box no longer notches the near deck
    TRN = {}
    for g in BI.GROUPS:
        if g not in TR: continue
        Tn = [T for (gg, u), T in TR['_units'].items() if gg == g]
        Tn = np.concatenate(Tn) if Tn else np.zeros((0, 3, 3))
        TRN[g] = dict(solid=TR[g]['solid'], T=TR[g]['T'], all=dict(T=Tn, lo=Tn[:, :, [0, 2]].min(1), hi=Tn[:, :, [0, 2]].max(1), ylo=Tn[:, :, 1].min(1), yhi=Tn[:, :, 1].max(1)))
    nt = 0
    for p in P:
        L = p['line'].length; n = max(1, int(math.ceil(L / 12.0))); cut = []; bygrp = {}; p['cut_by'] = {}
        for k in range(n):
            a, b = L * k / n, L * (k + 1) / n
            seg = substring(p['line'], max(0, a - 1), min(L, b + 1))
            ch = seg.buffer(p['half'] + 0.5, cap_style='flat')
            hh = np.interp([a, b], p['s'], p['h']); y0 = GROUND_Y + min(hh) - (RN.DECK_DEPTH if min(hh) >= FILL_H else min(hh)) - 0.1; y1 = GROUND_Y + max(hh) + PARAPET_H + 0.2
            for g in BI.GROUPS:
                if g not in TR: continue
                o = BI.occupancy(TRN, g, ch.bounds, y0, y1, pad=0.5, tri_only=True)
                if not o.is_empty: cut.append(o.intersection(ch)); bygrp.setdefault(g, []).append(o.intersection(ch))
        # the landside buildings as solids too (garages, RCC, hotel, CAC: a ramp that runs into a garage ends at its
        # facade; their surfaces alone miss a deck that passes between two of a garage's floors)
        if 'landside' in TR and not TR['landside']['solid'].is_empty:
            sol = TR['landside']['solid'].intersection(p['rib'].buffer(0.5))
            if not sol.is_empty: cut.append(sol); bygrp.setdefault('landside', []).append(sol)
        for (g, u), bd in (BODY or {}).items():
            sol = bd.intersection(p['rib'].buffer(0.5))
            if not sol.is_empty and sol.area > 0.05: cut.append(sol); bygrp.setdefault(g + '/' + u + ' inside', []).append(sol)
        if cut:
            C = unary_union(cut).buffer(0.10)
            before = p['geom'].area; p['geom'] = p['geom'].difference(C); p['asset_cut_m2'] = round(before - p['geom'].area, 2)
            if p['asset_cut_m2'] > 0.05: nt += 1
            p['against'] = C
            p['cut_by'] = {g: round(unary_union(v).intersection(p['rib']).area, 2) for g, v in bygrp.items() if unary_union(v).intersection(p['rib']).area > 0.05}
        else: p['asset_cut_m2'] = 0.0; p['against'] = Polygon()
        p['geom'] = unary_union([q for q in (getattr(p['geom'], 'geoms', None) or [p['geom']]) if isinstance(q, Polygon) and q.area > 0.5])
    tot = {}
    for p in P:
        for g, a in p['cut_by'].items(): tot[g] = tot.get(g, 0) + a
    log('trimmed: %d pieces lost area to an asset (%.0f m2 in all; by group %s)' % (nt, sum(p['asset_cut_m2'] for p in P), {g: round(a) for g, a in tot.items()}))


# the terminal-core landside the roadways are built in (the ITB / domestic curbs, the garages and the interchange west of
# the ITB up to US 101); elevated OSM roads beyond it (the US 101 / I-380 ramps 1-2 km away) keep their ground footprint
CORE = box(-2150.0, -50.0, -550.0, 1050.0)


def guideway_tris(path=os.path.join(D3, 'landside.glb')):
    """the AirTrain guideway's LOD0 triangles from the landside asset, split into the deck structure and the T-pier
    caps / columns (nodes '*_piers'): review round 2 - the landside rebuild of 23:26 places its inferred piers every ~30 m
    along the guideway skeleton without regard to the roads under it, and a cap over interchange_2_2 pinned the deck into
    a 70 % dip; the deck is bounded by the guideway deck's soffit, a pier over a road deck is reported (landside_piers)"""
    deck, piers = [], []
    if not os.path.exists(path): return np.zeros((0, 3, 3)), np.zeros((0, 3, 3))
    for r in BI.mesh_nodes(path):
        if BI.lod_of(r) != 0 or len(r['chain']) < 2 or not str(r['chain'][1].get('name', '')).startswith('airtrain'): continue
        (piers if '_piers' in r['name'] else deck).append(r['tris'])
    cat = lambda L: np.concatenate(L) if L else np.zeros((0, 3, 3))
    return cat(deck), cat(piers)


def overhead_of(TR, F=None):
    """the AirTrain guideway deck (landside airtrain units, LOD0, piers excluded) as an overhead structure: plan polygon and
    the soffit level (the lowest non-vertical deck triangle over a point, >= 4 m above grade) for roadways_net.solve_levels"""
    T, _ = guideway_tris()
    if not len(T): return []
    xz = T[:, :, [0, 2]]
    ar = 0.5 * np.abs((xz[:, 1, 0] - xz[:, 0, 0]) * (xz[:, 2, 1] - xz[:, 0, 1]) - (xz[:, 2, 0] - xz[:, 0, 0]) * (xz[:, 1, 1] - xz[:, 0, 1]))
    keep = (ar > 1e-3) & (T[:, :, 1].min(1) > GROUND_Y + 4.0); T = T[keep]; xz = xz[keep]
    lo, hi = xz.min(1), xz.max(1)
    def soff(x, z):
        m = (lo[:, 0] <= x) & (hi[:, 0] >= x) & (lo[:, 1] <= z) & (hi[:, 1] >= z)
        if not m.any(): return None
        t = T[m]; a, b, c = t[:, 0], t[:, 1], t[:, 2]
        v0 = c[:, [0, 2]] - a[:, [0, 2]]; v1 = b[:, [0, 2]] - a[:, [0, 2]]; v2 = np.array([x, z]) - a[:, [0, 2]]
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01; ok = np.abs(den) > 1e-12
        u = np.where(ok, (d11 * d20 - d01 * d21) / np.where(ok, den, 1), -1); v = np.where(ok, (d00 * d21 - d01 * d20) / np.where(ok, den, 1), -1)
        inside = (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
        if not inside.any(): return None
        y = a[:, 1] + u * (c[:, 1] - a[:, 1]) + v * (b[:, 1] - a[:, 1])
        return float(y[inside].min()) - GROUND_Y
    polys = BI.plan_geom(T) if len(T) else Polygon()   # the guideway's own triangles (review r2: not the stored footprints)
    return [(polys, soff)] if not polys.is_empty else []


# ------------------------------------------------------------------------------------------------ mesh building
class MB:
    """mesh buffers per (unit, lod, material): positions (world x, y, z), normals, uv"""
    def __init__(self): self.d = {}
    def get(self, unit, lod, mat):
        return self.d.setdefault((unit, lod, mat), dict(P=[], N=[], T=[], I=[], n=0))
    def tris(self, unit, lod, mat, P, Nm, T, I):
        b = self.get(unit, lod, mat); b['P'].append(P); b['N'].append(Nm); b['T'].append(T); b['I'].append(I + b['n']); b['n'] += len(P)


def tri_polys(geom, seg=3.0):
    """constrained Delaunay of a (multi)polygon densified to `seg` metres: unique vertices (x, z) and triangles"""
    out_v, out_t = [], []; base = 0
    for poly in (getattr(geom, 'geoms', None) or [geom]):
        if not isinstance(poly, Polygon) or poly.area < 0.3: continue
        poly = shapely.segmentize(poly, seg)
        T = shapely.constrained_delaunay_triangles(poly)
        tri = [np.array(t.exterior.coords)[:3] for t in T.geoms]
        if not tri: continue
        tri = np.array(tri)
        key = np.round(tri.reshape(-1, 2) * 1000).astype(np.int64)
        uk, inv = np.unique(key, axis=0, return_inverse=True)
        V = np.zeros((len(uk), 2)); V[inv] = tri.reshape(-1, 2)
        I = inv.reshape(-1, 3)
        # counter-clockwise seen from above (+y) with x east, z south: cross((b-a),(c-a)).y = dz1*dx2 - dx1*dz2 > 0
        a, b, c = V[I[:, 0]], V[I[:, 1]], V[I[:, 2]]
        cr = (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]) - (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
        I[cr < 0] = I[cr < 0][:, [0, 2, 1]]
        out_v.append(V); out_t.append(I + base); base += len(V)
    if not out_v: return np.zeros((0, 2)), np.zeros((0, 3), int)
    return np.concatenate(out_v), np.concatenate(out_t)


def vnormals(P, I):
    n = np.zeros_like(P)
    f = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    for k in range(3): np.add.at(n, I[:, k], f)
    l = np.linalg.norm(n, axis=1, keepdims=True); return n / np.maximum(l, 1e-9)


def lateral(p, V):
    """signed lateral offset (m, + to the right of travel) and arc length of plan points V on piece p's centreline"""
    pts = shapely.points(V); s = shapely.line_locate_point(p['line'], pts)
    q = shapely.get_coordinates(shapely.line_interpolate_point(p['line'], s))
    q2 = shapely.get_coordinates(shapely.line_interpolate_point(p['line'], np.minimum(s + 0.5, p['line'].length)))
    q1 = shapely.get_coordinates(shapely.line_interpolate_point(p['line'], np.maximum(s - 0.5, 0)))
    t = q2 - q1; t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    d = V - q
    # right of travel in x east / z south (seen from above): right = (-t_z, t_x)... with z south, heading vector (tx, tz);
    # the right-hand normal is (-tz, tx)
    lat = d[:, 0] * (-t[:, 1]) + d[:, 1] * t[:, 0]
    return lat, s


def bottom_of(h):
    return np.where(h >= FILL_H, h - RN.DECK_DEPTH, 0.0)


def build_piece(mb, p, P_all, lod, mat_deck, top=True):
    geom = p['geom'].simplify({0: 0.05, 1: 0.35, 2: 1.0}[lod])
    if geom.is_empty: return
    V, I = tri_polys(geom, {0: 6.0, 1: 16.0, 2: 30.0}[lod])
    if not len(I): return
    h = hp(p, V)
    if top:   # the plate's top is built by build_plate_top (bands, islands, crosswalks)
        lat, s = lateral(p, V)
        Pt = np.c_[V[:, 0], GROUND_Y + h, V[:, 1]]
        T = np.c_[0.5 + lat / max(p['lanes'] * RN.LANE_W, 1.0), s / DASH_CYCLE]
        mb.tris(p['unit'], lod, mat_deck, Pt, vnormals(Pt, I), T, I)
    # soffit (where the deck is on columns)
    hb = bottom_of(h); up = hb > 0.01
    if up.any():
        Ib = I[up[I].all(1)]
        if len(Ib):
            Pb = np.c_[V[:, 0], GROUND_Y + hb, V[:, 1]]; Ib2 = Ib[:, [0, 2, 1]]
            mb.tris(p['unit'], lod, 'concrete', Pb, vnormals(Pb, Ib2), np.c_[V[:, 0] / 4, V[:, 1] / 4], Ib2)
    # outer edges: fascia (top -> soffit or grade) and parapets
    # neighbours of the same level (they continue the deck: no fascia / parapet against them)
    nb = []
    for q in P_all:
        if q is p or q['geom'].is_empty or q['geom'].distance(geom) > 0.2: continue
        touch = q['geom'].intersection(geom.buffer(0.3))
        pts = shapely.get_coordinates(touch.boundary if not touch.is_empty else touch)
        if len(pts) and np.median(np.abs(hp(q, pts) - hp(p, pts))) < 1.0: nb.append(q['geom'])
    same = unary_union(nb) if nb else Polygon()
    against = p.get('against', Polygon())
    for poly in (getattr(geom, 'geoms', None) or [geom]):
        if not isinstance(poly, Polygon): continue
        for ring in [poly.exterior] + list(poly.interiors):
            R = np.array(shapely.segmentize(ring, {0: 8.0, 1: 20.0, 2: 40.0}[lod]).coords)
            if len(R) < 3: continue
            A, B = R[:-1], R[1:]; M = 0.5 * (A + B)
            mp = shapely.points(M)
            inner = (shapely.distance(mp, same) < 0.08) if not same.is_empty else np.zeros(len(M), bool)
            ag = (shapely.distance(mp, against) < 0.12) if not against.is_empty else np.zeros(len(M), bool)
            outer = ~inner & ~ag
            if not outer.any(): continue
            ha, hb_ = hp(p, A), hp(p, B)
            ba, bb = bottom_of(ha), bottom_of(hb_)
            # quads facing outward: polygon exterior is ccw in shapely's (x, z) = clockwise seen from above with z south
            # (y up, x east, z south is left-handed in plan): pick the winding from the outward test below
            for k in np.nonzero(outer)[0]:
                a, b = A[k], B[k]
                q = np.array([[a[0], GROUND_Y + ba[k], a[1]], [b[0], GROUND_Y + bb[k], b[1]], [b[0], GROUND_Y + hb_[k], b[1]], [a[0], GROUND_Y + ha[k], a[1]]])
                e = b - a; nrm = np.array([e[1], 0.0, -e[0]]); nrm /= max(np.linalg.norm(nrm), 1e-9)
                c = 0.5 * (a + b) + 0.05 * nrm[[0, 2]]
                if poly.contains(Point(c)): nrm = -nrm
                f = np.cross(q[1] - q[0], q[2] - q[0])
                if f @ nrm < 0 or (abs(f @ nrm) < 1e-9 and np.cross(q[2] - q[0], q[3] - q[0]) @ nrm < 0): q = q[[1, 0, 3, 2]]
                L = float(np.linalg.norm(e)); top = max(ha[k], hb_[k])
                mb.tris(p['unit'], lod, 'concrete', q, np.repeat(nrm[None], 4, 0), np.array([[0, ba[k] / 4], [L / 4, bb[k] / 4], [L / 4, hb_[k] / 4], [0, ha[k] / 4]]), np.array([[0, 1, 2], [0, 2, 3]]))
                if lod == 1 and top > 0.4:
                    # LOD1 parapet: the outer face only (the fascia carried up by PARAPET_H)
                    qq = np.array([[a[0], GROUND_Y + ha[k], a[1]], [b[0], GROUND_Y + hb_[k], b[1]], [b[0], GROUND_Y + hb_[k] + PARAPET_H, b[1]], [a[0], GROUND_Y + ha[k] + PARAPET_H, a[1]]])
                    if np.cross(qq[1] - qq[0], qq[2] - qq[0]) @ nrm < 0: qq = qq[[1, 0, 3, 2]]
                    mb.tris(p['unit'], lod, 'concrete', qq, np.repeat(nrm[None], 4, 0), np.array([[0, 0], [L / 4, 0], [L / 4, 0.2], [0, 0.2]]), np.array([[0, 1, 2], [0, 2, 3]]))
                if lod == 0 and top > 0.4:
                    # parapet: a box on the edge, PARAPET_W inward
                    inn = -nrm[[0, 2]] * PARAPET_W
                    a2, b2 = a + inn, b + inn; H = PARAPET_H
                    box_p = [
                        (np.array([[a[0], GROUND_Y + ha[k], a[1]], [b[0], GROUND_Y + hb_[k], b[1]], [b[0], GROUND_Y + hb_[k] + H, b[1]], [a[0], GROUND_Y + ha[k] + H, a[1]]]), nrm),
                        (np.array([[b2[0], GROUND_Y + hb_[k], b2[1]], [a2[0], GROUND_Y + ha[k], a2[1]], [a2[0], GROUND_Y + ha[k] + H, a2[1]], [b2[0], GROUND_Y + hb_[k] + H, b2[1]]]), -nrm),
                        (np.array([[a[0], GROUND_Y + ha[k] + H, a[1]], [b[0], GROUND_Y + hb_[k] + H, b[1]], [b2[0], GROUND_Y + hb_[k] + H, b2[1]], [a2[0], GROUND_Y + ha[k] + H, a2[1]]]), np.array([0, 1.0, 0]))]
                    for qq, nn in box_p:
                        # winding: make the face normal agree with nn
                        f = np.cross(qq[1] - qq[0], qq[2] - qq[0])
                        if f @ nn < 0: qq = qq[[1, 0, 3, 2]]
                        mb.tris(p['unit'], lod, 'concrete', qq, np.repeat(nn[None], 4, 0), np.array([[0, 0], [L / 4, 0], [L / 4, H / 4], [0, H / 4]]), np.array([[0, 1, 2], [0, 2, 3]]))


# ------------------------------------------------------------------------------------------------ ITB deck plate (review r2)
ISLAND_H = 0.15       # raised islands: 6-in kerb (as the ITB curb's KERB_H) [inf]
RED_KERB_W = 0.45     # red-painted kerb along island B's roadway edge [obs NAIP 2024: R - G peak 0.5-1 m wide incl. blur]
XWALK = dict(width=3.0, bar=0.6, gap=0.6, lift=0.03)   # continental crosswalk bars (MUTCD 3B.18: 12-24 in bars) [inf
                                                       # pattern]; stations: the ITB curb ramps (itb_geom.CROSSWALK_U, obs NAIP)
try:
    import itb_geom as _IG  # noqa: E402  (the ITB group's curb ramp stations; same values as RP.measure's default)
    CROSSWALK_U = tuple(_IG.CROSSWALK_U)
except Exception:  # pragma: no cover - the ITB module needs its own inputs; fall back to the values it holds
    CROSSWALK_U = (-52.8, -15.8, -4.7, 2.5, 14.0, 49.5)


def plate_outline(M, ways, log):
    """the deck plate: the measured outline (kerb to the imaged outer edge) less the lower outer roadway - the elevated
    layer-1 OSM ways running across the outline (their ribbon + 1.5 m) and, on the straight section, everything west of
    island B's west edge - keeping the part connected to the kerb. Returns (the lower ways' ids, the plate polygon)."""
    C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    lower = {}
    for w in ways:
        if w['layer'] >= 2: continue
        ln = LineString(w['pts'])
        if ln.intersection(M['poly']).length > 20.0: lower[w['id']] = ln.buffer(w['w'] / 2 + SHOULDER + 1.5, cap_style='flat')
    s0, s1 = M['straight']; vg = M['gutter_v']
    strip = Polygon(RP.xz_of(np.array([[M['stations'][0] - 5, M['v_cap'] - 5], [M['stations'][-1] + 5, M['v_cap'] - 5], [M['stations'][-1] + 5, vg], [M['stations'][0] - 5, vg]]), C, du, dv))
    st = Polygon(RP.xz_of(np.array([[s0, M['v_cap'] - 5], [s1, M['v_cap'] - 5], [s1, vg], [s0, vg]]), C, du, dv))
    g = M['poly'].difference(unary_union(list(lower.values()) + [st]))
    # the part connected to the kerb strip
    ks = Polygon(RP.xz_of(np.array([[M['stations'][0], M['v_kerb'] - 2], [M['stations'][-1], M['v_kerb'] - 2], [M['stations'][-1], M['v_kerb'] + 2], [M['stations'][0], M['v_kerb'] + 2]]), C, du, dv))
    parts = [q for q in (getattr(g, 'geoms', None) or [g]) if isinstance(q, Polygon) and q.intersects(ks)]
    g = unary_union(parts).buffer(0.5, join_style='mitre').buffer(-0.5, join_style='mitre')
    log('ITB deck plate: measured outline %.0f m2 less the lower outer roadway (OSM layer-1 ways %s) = %.0f m2' % (M['poly'].area, sorted(lower), g.area))
    return set(lower), g


def widen_lower(P, lower, M, log):
    """the lower outer roadway on the straight section spans the imaged band from its outer edge to island B's west edge
    (corrected from the plate's relief height to its own level: an edge at height h is imaged (H_EDGE - h) x the lean
    further out in the plate's frame); its OSM ribbon (2 lanes, 8.4 m) left a gap under the plate's edge"""
    import draw_data as DD
    C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    s0, s1 = M['straight']; kv = float(DD.lean_frame(C[None], 1.0)[0] @ dv)
    for p in P:
        if p['src'] != 'deck' or p['id'] not in lower: continue
        uv = RP.uv_of(p['pts'], C, du, dv); on = (uv[:, 0] > s0) & (uv[:, 0] < s1) & (np.abs(uv[:, 1] - M['outer']['v'][0]) < 15)
        if not on.any(): continue
        h = float(np.median(p['h'][on]))
        v_out = M['v_edge_median'] + (M['h_edge'] - (h + PARAPET_H)) * kv
        band = Polygon(RP.xz_of(np.array([[s0, v_out], [s1, v_out], [s1, M['gutter_v'] + 0.3], [s0, M['gutter_v'] + 0.3]]), C, du, dv))
        before = p['rib'].area; p['rib'] = unary_union([p['rib'], band.intersection(p['line'].buffer(25.0))])
        M.setdefault('lower', []).append(dict(id=p['id'], h_m=round(h, 2), v_out_true=round(v_out, 2), added_m2=round(p['rib'].area - before, 1)))
        log('lower outer roadway (way %s, %.2f m on the straight): widened to the imaged band v %.2f .. %.2f (+%.0f m2), toward the plate edge (the trim keeps STACK_GAP)'
            % (p['id'], h, v_out, M['gutter_v'] + 0.3, p['rib'].area - before))


def plate_piece(M, h):
    """the measured ITB departures deck as one road piece (src 'plate'): level h (the ITB L3 deck top), a centreline
    along the roof axis through the middle of the plate (levels and lateral coordinates are taken on it), anchored"""
    C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    u0, u1 = M['stations'][0] - 2.0, M['stations'][-1] + 2.0; vm = (M['v_kerb'] + M['v_cap']) / 2
    pts = RP.xz_of(np.array([[u0, vm], [u1, vm]]), C, du, dv)
    ln = LineString(pts); s = np.array([0.0, ln.length])
    half = (M['v_kerb'] - M['v_cap']) / 2 + 3.0
    return dict(id='itb_plate', src='plate', w=2 * half, lanes=0, oneway=True, anchor='itb', layer=2, pts=pts, s=s, h=np.array([h, h]), nodes=[],
                name='ITB departures deck (NAIP 2024 plate)', kind='plate', line=ln, half=half, rib=M['plate_poly'], hmin=h, hmax=h, M=M)


def band_lanes(b):
    """lanes painted on a measured band: OSM lanes as a minimum (inner: 2 + the parallel kerb lane, OSM parking:lane:right;
    middle: 2; outer: 2), else the measured width / 3.6 m [inf]"""
    w = abs(b['v'][1] - b['v'][0]); osm = {'inner': 3, 'middle': 2, 'outer': 2}.get(b['name'], 1)
    return max(osm, int(w // RN.LANE_W))


def build_plate_top(mb, p, lod, mats):
    """the plate's top: per band on the straight section (lane tiles, raised islands with the red kerb, crosswalk bars at
    the curb ramps) and plain asphalt on the rest of the plate; travel is towards -u on all three roadways (OSM node
    order of 38853045 / 38853121 / 41015123), so the right of travel is +v (the kerb side)"""
    M = p['M']; C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    geom = p['geom'].simplify({0: 0.05, 1: 0.35, 2: 1.0}[lod])
    if geom.is_empty: return
    s0, s1 = M['straight']; seg = {0: 6.0, 1: 16.0, 2: 30.0}[lod]
    def W(uv): return Polygon(RP.xz_of(np.asarray(uv), C, du, dv))
    def UV(V): return RP.uv_of(V, C, du, dv)
    straight = W([(s0, M['v_cap'] - 5), (s1, M['v_cap'] - 5), (s1, M['v_kerb'] + 5), (s0, M['v_kerb'] + 5)])
    def top(g, mat, lift, Tfn):
        if g.is_empty: return
        V, I = tri_polys(g, seg)
        if not len(I): return
        Pt = np.c_[V[:, 0], np.full(len(V), GROUND_Y + p['hmin'] + lift), V[:, 1]]
        mb.tris(p['unit'], lod, mat, Pt, vnormals(Pt, I), Tfn(V), I)
    plainT = lambda V: np.c_[V[:, 0] / 4, V[:, 1] / 4]
    top(geom.difference(straight), 'deck_plain', 0.0, plainT)
    rest = geom.intersection(straight)
    for b in M['bands']:
        va, vb = sorted(b['v']); g = rest.intersection(W([(s0, va), (s1, va), (s1, vb), (s0, vb)]))
        if g.is_empty: continue
        if b['kind'] == 'island':
            top(g, 'island', ISLAND_H, plainT)
            if lod < 2:   # kerb faces on the long sides (the island's ends stop at the straight section's ends)
                for poly in (getattr(g, 'geoms', None) or [g]):
                    if not isinstance(poly, Polygon): continue
                    R = np.array(poly.exterior.coords); A, B = R[:-1], R[1:]
                    for a, c in zip(A, B):
                        e = c - a; Lm = float(np.linalg.norm(e))
                        if Lm < 0.2: continue
                        nrm = np.array([e[1], -e[0]]) / Lm
                        if poly.contains(Point(*(0.5 * (a + c) + 0.05 * nrm))): nrm = -nrm
                        y0, y1 = GROUND_Y + p['hmin'], GROUND_Y + p['hmin'] + ISLAND_H
                        q = np.array([[a[0], y0, a[1]], [c[0], y0, c[1]], [c[0], y1, c[1]], [a[0], y1, a[1]]]); n3 = np.array([nrm[0], 0.0, nrm[1]])
                        if np.cross(q[1] - q[0], q[2] - q[0]) @ n3 < 0: q = q[[1, 0, 3, 2]]
                        mb.tris(p['unit'], lod, 'island', q, np.repeat(n3[None], 4, 0), np.array([[0, 0], [Lm / 4, 0], [Lm / 4, 0.04], [0, 0.04]]), np.array([[0, 1, 2], [0, 2, 3]]))
            if b['name'] == 'islandB' and lod == 0:   # the red-painted kerb along its roadway (+v) edge [obs NAIP]
                top(g.intersection(W([(s0, vb - RED_KERB_W), (s1, vb - RED_KERB_W), (s1, vb), (s0, vb)])), 'kerb_red', ISLAND_H + 0.005, plainT)
            continue
        n = band_lanes(b); vc = 0.5 * (va + vb); span = n * RN.LANE_W
        mat = ('deck_light_%do' if b['kind'] == 'road_light' else 'deck_%do') % n if lod < 2 else ('deck_plain_light' if b['kind'] == 'road_light' else 'deck_plain')
        mats.setdefault(mat, None)
        top(g, mat, 0.0, lambda V: np.c_[0.5 + (UV(V)[:, 1] - vc) / span, -UV(V)[:, 0] / DASH_CYCLE])
        if b['name'] == 'inner' and lod == 0:   # crosswalk bars at the curb ramps, kerb to island A
            for uc in CROSSWALK_U:
                if not (s0 + 2 < uc < s1 - 2): continue
                v = vb - 0.3
                while v - XWALK['bar'] > va + 0.3:
                    bar = rest.intersection(W([(uc - XWALK['width'] / 2, v - XWALK['bar']), (uc + XWALK['width'] / 2, v - XWALK['bar']), (uc + XWALK['width'] / 2, v), (uc - XWALK['width'] / 2, v)]))
                    top(bar, 'paint_white', XWALK['lift'], plainT); v -= XWALK['bar'] + XWALK['gap']


def plate_columns(p, P, TR, log):
    """columns under the plate on lines under the two islands and 1.5 m inside the outer edge, every COL_SPACING along u,
    each kept only where it stands clear of every asset from grade to the soffit and inside the built deck [inf]"""
    M = p['M']; C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    lines = [0.5 * sum(b['v']) for b in M['bands'] if b['kind'] == 'island'] + [M['v_cap'] + 2.0]
    inner = p['geom'].buffer(-(D_COL / 2 + 0.6)); out = []
    for v in lines:
        for u in np.arange(M['stations'][0] + 6.0, M['stations'][-1] - 3.0, COL_SPACING):
            q = RP.xz_of(np.array([[u, v]]), C, du, dv)[0]; disk = Point(q).buffer(D_COL / 2 + 0.3)
            if not inner.contains(Point(q)): continue
            soff = p['hmin'] - RN.DECK_DEPTH
            if any(not BI.occupancy(TR, g, disk.bounds, GROUND_Y + 0.05, GROUND_Y + soff, pad=0.2, tri_only=True).intersection(disk).is_empty for g in BI.GROUPS if g in TR): continue
            if any(o is not p and o['geom'].intersects(disk) and float(hp(o, q[None])[0]) < soff - 0.1 for o in P): continue
            out.append(dict(unit=p['unit'], xz=q, soffit=soff, way=p['id']))
    log('plate columns: %d (lines at v %s, every %.0f m) [inf]' % (len(out), [round(v, 1) for v in lines], COL_SPACING))
    return out


def curb_gap_check(P, TR, M, curb_h, log):
    """review round 2 check: along the ITB curb (every 0.5 m of u), the void between the curb's top (ITB asset) and the
    departures deck top (this asset, within 0.3 m of the deck level), measured outward from the kerb; must be <= 0.3 m"""
    C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    T = TR['_lods'][('itb', 'hall', 0)]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    cs = T[(n[:, 1] > 0.95) & (np.abs(T[:, :, 1] - (GROUND_Y + curb_h)).max(1) < 0.06)]
    curb = unary_union([Polygon(t[:, [0, 2]]).buffer(0.005) for t in cs if Polygon(t[:, [0, 2]]).area > 1e-4])
    h = M.get('h_deck', 11.35)
    deck = unary_union([q['geom'] for q in P if not q['geom'].is_empty and abs(float(np.median(q['h'])) - h) < 0.3])
    both = unary_union([curb, deck]); gaps = []
    for u in np.arange(M['stations'][0] + 0.5, M['stations'][-1] - 0.5, 0.5):
        ln = LineString(RP.xz_of(np.array([[u, M['v_kerb'] + 0.8], [u, M['v_kerb'] - 12.0]]), C, du, dv))
        cover = ln.intersection(both); segs = [g for g in (getattr(cover, 'geoms', None) or [cover]) if not g.is_empty and g.length > 0]
        ivs = sorted([sorted(float(np.dot(np.array(c) - C, dv)) for c in g.coords) for g in segs], key=lambda x: -x[1])
        # from the kerb outward: the first void after the curb
        gap = None
        if ivs:
            lo = ivs[0][0]
            for a, b in ivs[1:]:
                if b < lo - 1e-3: gap = lo - b; break      # the first void outward from the kerb
                lo = min(lo, a)
            if gap is None: gap = max(0.0, min(a for a, b in ivs) - (M['v_kerb'] - 12.0))   # deck missing to 12 m out
        else: gap = 12.8
        gaps.append((round(float(u), 1), round(gap, 3)))
    g = np.array([x[1] for x in gaps]); worst = max(gaps, key=lambda x: x[1])
    res = dict(stations=len(gaps), max_void_m=round(float(g.max()), 3), at_u=worst[0], over_0_3m=int((g > 0.3).sum()), limit_m=0.3)
    log('ITB curb to departures deck: %d stations, largest void %.3f m (u %.1f), %d over 0.3 m' % (res['stations'], res['max_void_m'], res['at_u'], res['over_0_3m']))
    return res


def clearance_check(mb, TR, log, limit=RN.CLEAR_MIN, piers=False):
    """review round 2 check (finding 5): the deck tops (LOD0 road surfaces) against the AirTrain guideway triangles above
    them: per ~1-m sample of the deck tops, the lowest guideway triangle over it; clearance = that - the deck top. The
    guideway deck (the bound the solve enforces) and, with piers=True, the inferred T-pier caps (the landside group's
    pier sites; reported, not designed around)"""
    Td, Tp = guideway_tris(); T = Tp if piers else Td
    if not len(T): return dict(points=0)
    xz = T[:, :, [0, 2]]; lo, hi = xz.min(1), xz.max(1)
    pts = []
    for (u, l, mat), b in mb.d.items():
        if l != 0 or not (mat.startswith('deck') or mat in ('island', 'paint_white', 'kerb_red')) or not b['P']: continue
        off = 0
        for P, I in zip(b['P'], b['I']):
            if len(I):   # every top triangle sampled on a ~1-m barycentric grid (vertices, edges and interior)
                Tq = P[I - off]
                for t in Tq:
                    k = int(max(1, math.ceil(max(np.linalg.norm(t[1] - t[0]), np.linalg.norm(t[2] - t[1]), np.linalg.norm(t[0] - t[2])) / 1.0)))
                    ij = np.array([(i, j) for i in range(k + 1) for j in range(k + 1 - i)], float) / k
                    pts.append(t[0] + ij[:, :1] * (t[1] - t[0]) + ij[:, 1:] * (t[2] - t[0]))
            off += len(P)
    if not pts: return dict(points=0)
    Q = np.concatenate(pts)
    Q = Q[(Q[:, 0] > lo[:, 0].min() - 1) & (Q[:, 0] < hi[:, 0].max() + 1) & (Q[:, 2] > lo[:, 1].min() - 1) & (Q[:, 2] < hi[:, 1].max() + 1)]
    out = []
    for q in Q:
        m = (lo[:, 0] <= q[0]) & (hi[:, 0] >= q[0]) & (lo[:, 1] <= q[2]) & (hi[:, 1] >= q[2])
        if not m.any(): continue
        t = T[m]; a, b, c = t[:, 0], t[:, 1], t[:, 2]
        v0 = c[:, [0, 2]] - a[:, [0, 2]]; v1 = b[:, [0, 2]] - a[:, [0, 2]]; v2 = q[[0, 2]] - a[:, [0, 2]]
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01; ok = np.abs(den) > 1e-12
        uu = np.where(ok, (d11 * d20 - d01 * d21) / np.where(ok, den, 1), -1); vv = np.where(ok, (d00 * d21 - d01 * d20) / np.where(ok, den, 1), -1)
        ins = (uu >= -1e-6) & (vv >= -1e-6) & (uu + vv <= 1 + 1e-6)
        if not ins.any(): continue
        y = (a[:, 1] + uu * (c[:, 1] - a[:, 1]) + vv * (b[:, 1] - a[:, 1]))[ins]; y = y[y > q[1] + 1.0]
        if len(y): out.append((float(y.min() - q[1]), q[0], q[2], q[1] - GROUND_Y))
    if not out: return dict(points=0)
    out.sort(); cl = np.array([o[0] for o in out])
    bad = [o for o in out if o[0] < limit - 1e-3]
    res = dict(points=len(out), min_m=round(out[0][0], 2), at=[round(out[0][1], 1), round(out[0][2], 1)], deck_m=round(out[0][3], 2), below_limit=int((cl < limit - 1e-3).sum()), limit_m=limit,
               where=sorted({(round(o[1] / 10) * 10, round(o[2] / 10) * 10) for o in bad})[:20])
    log('guideway %s clearance over the deck tops (LOD0 top triangles sampled at ~1 m): %d points under it, min %.2f m at %s (deck %.2f m), %d below %.1f m'
        % ('PIER CAP' if piers else 'deck', res['points'], res['min_m'], res['at'], res['deck_m'], res['below_limit'], limit))
    return res


def cylinder(mb, unit, lod, c, y0, y1, r, nseg):
    a = np.linspace(0, 2 * np.pi, nseg + 1)[:-1]; ca, sa = np.cos(a), np.sin(a)
    P = []; Nn = []; T = []; I = []
    for k in range(nseg):
        k2 = (k + 1) % nseg
        q = np.array([[c[0] + r * ca[k], y0, c[1] + r * sa[k]], [c[0] + r * ca[k2], y0, c[1] + r * sa[k2]], [c[0] + r * ca[k2], y1, c[1] + r * sa[k2]], [c[0] + r * ca[k], y1, c[1] + r * sa[k]]])
        nn = np.array([[ca[k], 0, sa[k]], [ca[k2], 0, sa[k2]], [ca[k2], 0, sa[k2]], [ca[k], 0, sa[k]]])
        f = np.cross(q[1] - q[0], q[2] - q[0])
        if f @ nn[0] < 0: q = q[[1, 0, 3, 2]]; nn = nn[[1, 0, 3, 2]]
        b = len(P) * 4 if False else 4 * k
        P.append(q); Nn.append(nn); T.append(np.array([[k / nseg * 2, y0 / 4], [(k + 1) / nseg * 2, y0 / 4], [(k + 1) / nseg * 2, y1 / 4], [k / nseg * 2, y1 / 4]])); I.append(np.array([[0, 1, 2], [0, 2, 3]]) + 4 * k)
    mb.tris(unit, lod, 'concrete', np.concatenate(P), np.concatenate(Nn), np.concatenate(T), np.concatenate(I))


def columns(P, TR, log):
    L = json.load(open(os.path.join(ROOT, 'data', 'sfo_landside.json')))
    ramp_ids = {p['id'] for p in P if p['src'] == 'ramp'}
    roads = unary_union([LineString(r['pts']).buffer(r['w'] / 2 + 0.3, cap_style='flat') for r in L['roads'] if not r['elevated'] and r['osm_id'] not in ramp_ids and len(r['pts']) >= 2])
    shapely.prepare(roads)
    solid = unary_union([TR[g]['solid'] for g in BI.GROUPS if g in TR and not TR[g]['solid'].is_empty]); shapely.prepare(solid)
    out = []; tried = placed = 0
    for p in P:
        if p['src'] == 'ramp' and p['hmax'] < FILL_H: continue
        Ln = p['line'].length; n = int(Ln // COL_SPACING)
        for k in range(max(1, n)):
            s0 = (k + 0.5) * Ln / max(1, n)
            h0 = float(np.interp(s0, p['s'], p['h']))
            if h0 < FILL_H: continue
            tried += 1; ok = None
            for ds in (0.0, 6.0, -6.0):
                s = min(max(s0 + ds, 1.0), Ln - 1.0); c = np.array(p['line'].interpolate(s).coords[0])
                t = np.array(p['line'].interpolate(min(s + 0.5, Ln)).coords[0]) - np.array(p['line'].interpolate(max(s - 0.5, 0)).coords[0]); t /= max(np.linalg.norm(t), 1e-9)
                nrm = np.array([-t[1], t[0]])
                for off in (0.0, p['half'] - 1.2, -(p['half'] - 1.2), (p['half'] - 1.2) / 2, -(p['half'] - 1.2) / 2):
                    q = c + nrm * off; pt = Point(q); disk = pt.buffer(D_COL / 2 + 0.3)
                    if not p['geom'].buffer(-0.3).contains(pt): continue
                    hs = float(hp(p, q[None])[0]); soff = hs - RN.DECK_DEPTH
                    if soff < 2.0 or roads.intersects(disk) or solid.intersects(disk): continue
                    # lower decks / ramps under this one, and the other assets' triangles from grade to the soffit
                    low = False
                    for o in P:
                        if o is p or not o['geom'].intersects(disk): continue
                        if float(hp(o, q[None])[0]) < soff - 0.1: low = True; break
                    if low: continue
                    if any(not BI.occupancy(TR, g, disk.bounds, GROUND_Y + 0.05, GROUND_Y + soff, pad=0.2, tri_only=True).intersection(disk).is_empty for g in BI.GROUPS if g in TR): continue
                    ok = (q, soff); break
                if ok: break
            if ok: placed += 1; out.append(dict(unit=p['unit'], xz=ok[0], soffit=ok[1], way=p['id']))
    log('columns: %d placed of %d positions (the rest: no clear place within +-6 m, a longer span)' % (placed, tried))
    return out, dict(tried=tried, placed=placed)


# ------------------------------------------------------------------------------------------------ textures / materials
def lane_tile(lanes, oneway, base_srgb, H=256, W=None):
    from PIL import Image
    W = W or (128 if lanes <= 2 else 256)
    rng = np.random.default_rng(7 + lanes * 2 + oneway)
    img = np.ones((H, W, 3)) * np.array(base_srgb, float)[None, None] / 255.0
    # wheel-path wear and patching: low-frequency tone variation (8 x 8 cells, smoothed), quantised so the PNG stays small
    g = rng.standard_normal((H // 32 + 1, W // 32 + 1)); from PIL import ImageFilter
    gi = np.asarray(Image.fromarray(((g * 0.5 + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), float) / 255.0
    img *= (0.96 + 0.08 * np.round(gi * 6) / 6)[:, :, None]
    def line(u, col, dashed, wid_m=0.10):
        span = lanes * RN.LANE_W; px = max(1.0, wid_m / span * W); c0 = u * W
        x = np.arange(W) + 0.5; m = np.clip(px / 2 + 0.5 - np.abs(x - c0), 0, 1)[None, :, None]
        if dashed: v = (np.arange(H) + 0.5) / H; m = m * ((v < 0.25)[:, None, None])
        img[:] = img * (1 - m * 0.85) + np.array(col)[None, None] * m * 0.85
    yellow, white = (0.80, 0.62, 0.18), (0.86, 0.86, 0.84)
    e = 0.30 / (lanes * RN.LANE_W)  # edge lines 0.3 m inside the carriageway edge
    line(e, yellow if oneway else white, False); line(1 - e, white, False)
    for k in range(1, lanes):
        u = k / lanes
        if not oneway and lanes >= 2 and k == lanes // 2: line(u - 0.012, yellow, False); line(u + 0.012, yellow, False)
        else: line(u, white, True)
    im = Image.fromarray((img.clip(0, 1) ** (1 / 1.0) * 255).astype(np.uint8)); b = io.BytesIO(); im.save(b, 'PNG', optimize=True)
    return b.getvalue()


def naip_asphalt(P):
    m = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
    im = np.load(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r')
    vals = []
    for p in P:
        if p['src'] != 'deck' or p['geom'].is_empty: continue
        g = p['geom'].buffer(-1.0)
        if g.is_empty: continue
        x0, z0, x1, z1 = g.bounds; xs = np.arange(x0, x1, 2.0); zs = np.arange(z0, z1, 2.0)
        X, Z = np.meshgrid(xs, zs); pts = shapely.points(X.ravel(), Z.ravel()); inside = shapely.contains(g, pts)
        c = ((X.ravel()[inside] - m['x0']) / m['res'] - 0.5).astype(int); r = ((Z.ravel()[inside] - m['z0']) / m['res'] - 0.5).astype(int)
        ok = (r >= 0) & (c >= 0) & (r < im.shape[0]) & (c < im.shape[1])
        if ok.any(): vals.append(np.asarray(im[r[ok], c[ok]])[:, ::-1])
    v = np.concatenate(vals); med = np.median(v, 0)
    lin = srgb2lin(med) * NAIP_ALBEDO; srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055) * 255
    return [int(round(x)) for x in med], [int(round(x)) for x in srgb], int(len(v))


KERB_RED = (168, 52, 44)   # red curb paint, sRGB [inf: NAIP shows red there (R - G 70-80), not its albedo]


def naip_band(plate, name):
    """NAIP 2024 median colour over one band of the plate's straight section, and the base colour (x NAIP_ALBEDO linear)"""
    M = plate['M']; b = name if isinstance(name, dict) else [x for x in M['bands'] if x['name'] == name][0]
    C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    s0, s1 = M['straight']; va, vb = sorted(b['v'])
    us = np.arange(s0, s1, 1.0); vs = np.arange(va + 0.8, vb - 0.8, 0.5); V, U = np.meshgrid(vs, us)
    px = RP.sample(U, V, M['h_edge'], C, du, dv).reshape(-1, 3)[:, ::-1]
    med = np.median(px, 0); lin = srgb2lin(med) * NAIP_ALBEDO; srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055) * 255
    return [int(round(x)) for x in med], [int(round(x)) for x in srgb]


# ------------------------------------------------------------------------------------------------ glTF writer
class GLB:
    def __init__(self):
        self.js = dict(asset=dict(version='2.0', generator='tools/blender/build_roadways.py (numpy)'), scene=0, scenes=[dict(nodes=[0])], nodes=[], meshes=[],
                       materials=[], accessors=[], bufferViews=[], buffers=[], textures=[], images=[], samplers=[])
        self.bin = bytearray(); self.mat = {}
    def view(self, data, target=None):
        while len(self.bin) % 4: self.bin.append(0)
        o = len(self.bin); self.bin += data; v = dict(buffer=0, byteOffset=o, byteLength=len(data))
        if target: v['target'] = target
        self.js['bufferViews'].append(v); return len(self.js['bufferViews']) - 1
    def acc(self, arr, typ, ctype, target, mm=False):
        a = np.ascontiguousarray(arr); bv = self.view(a.tobytes(), target)
        d = dict(bufferView=bv, componentType=ctype, count=int(a.shape[0]), type=typ)
        if mm: d['min'] = [float(x) for x in a.min(0)]; d['max'] = [float(x) for x in a.max(0)]
        self.js['accessors'].append(d); return len(self.js['accessors']) - 1
    def image(self, png, name):
        bv = self.view(png); self.js['images'].append(dict(bufferView=bv, mimeType='image/png', name=name)); return len(self.js['images']) - 1
    def material(self, name, rgb_srgb, rough, tex=None, extras=None):
        if name in self.mat: return self.mat[name]
        lin = list(srgb2lin(rgb_srgb)) + [1.0]
        pbr = dict(baseColorFactor=[float(x) for x in lin], metallicFactor=0.0, roughnessFactor=rough)
        if tex is not None:
            if not self.js['samplers']: self.js['samplers'].append(dict(magFilter=9729, minFilter=9987, wrapS=33071, wrapT=10497))
            self.js['textures'].append(dict(sampler=0, source=tex)); pbr['baseColorTexture'] = dict(index=len(self.js['textures']) - 1); pbr['baseColorFactor'] = [1, 1, 1, 1]
        self.js['materials'].append(dict(name=name, pbrMetallicRoughness=pbr, extras=extras or {})); self.mat[name] = len(self.js['materials']) - 1
        return self.mat[name]
    def mesh(self, name, prims):
        out = []
        for mat, P, Nn, T, I in prims:
            pa = self.acc(P.astype(np.float32), 'VEC3', 5126, 34962, True); na = self.acc(Nn.astype(np.float32), 'VEC3', 5126, 34962)
            ta = self.acc(T.astype(np.float32), 'VEC2', 5126, 34962)
            idx = I.astype(np.uint32 if P.shape[0] > 65535 else np.uint16).ravel()
            ia = self.acc(idx, 'SCALAR', 5125 if idx.dtype == np.uint32 else 5123, 34963)
            out.append(dict(attributes=dict(POSITION=pa, NORMAL=na, TEXCOORD_0=ta), indices=ia, material=mat))
        self.js['meshes'].append(dict(name=name, primitives=out)); return len(self.js['meshes']) - 1
    def node(self, **kw):
        self.js['nodes'].append(kw); return len(self.js['nodes']) - 1
    def write(self, path):
        while len(self.bin) % 4: self.bin.append(0)
        self.js['buffers'] = [dict(byteLength=len(self.bin))]
        for k in ('textures', 'images', 'samplers'):
            if not self.js[k]: del self.js[k]
        j = json.dumps(self.js, separators=(',', ':')).encode()
        while len(j) % 4: j += b' '
        with open(path + '.tmp', 'wb') as f:  # written aside and renamed: a page loading the file never reads half of it
            f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(self.bin)))
            f.write(struct.pack('<II', len(j), 0x4E4F534A)); f.write(j)
            f.write(struct.pack('<II', len(self.bin), 0x004E4942)); f.write(bytes(self.bin))
        os.replace(path + '.tmp', path)


def export(path, mb, units, lods, mats_def, root_c, extras, unit_extras):
    G = GLB(); tex_ids = {}
    mid = {}
    for name, d in mats_def.items():
        t = None
        if d.get('png') is not None: t = tex_ids.setdefault(name, G.image(d['png'], name))
        mid[name] = G.material(name, d['rgb'], d['rough'], t, d.get('extras'))
    root = G.node(name='roadways', translation=[float(root_c[0]), GROUND_Y, float(root_c[1])], extras=extras, children=[])
    for l in lods:
        ln = G.node(name='LOD%d' % l, extras=dict(lod=l, switch_m=SWITCH[l]), children=[])
        G.js['nodes'][root]['children'].append(ln)
        for u in units:
            prims = []
            for (uu, ll, mat), b in sorted(mb.d.items(), key=lambda kv: kv[0][2]):
                if uu != u or ll != l or not b['P']: continue
                P = np.concatenate(b['P']); P = P - np.array([root_c[0], GROUND_Y, root_c[1]])
                prims.append((mid[mat], P, np.concatenate(b['N']), np.concatenate(b['T']), np.concatenate(b['I'])))
            if not prims: continue
            m = G.mesh('L%d_%s' % (l, u), prims)
            un = G.node(name='L%d_%s' % (l, u), mesh=m, extras=dict(building=u, **unit_extras.get(u, {})))
            G.js['nodes'][ln]['children'].append(un)
    G.write(path)
    return os.path.getsize(path)


# ------------------------------------------------------------------------------------------------ check sheet
def sheet(P, cols, path, LV, stats):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    m = json.load(open(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m.json')))
    im = np.load(os.path.join(ROOT, 'refs', 'cache', 'naip', 'naip_2024_world_0.5m_bgr.npy'), mmap_mode='r')
    X0, Z0, X1, Z1 = -1760, 20, -680, 640
    r0, r1 = int((Z0 - m['z0']) / m['res']), int((Z1 - m['z0']) / m['res']); c0, c1 = int((X0 - m['x0']) / m['res']), int((X1 - m['x0']) / m['res'])
    bg = np.asarray(im[r0:r1:2, c0:c1:2])[:, :, ::-1].astype(float) / 255 * 0.55 + 0.25
    fig = plt.figure(figsize=(16.5, 13.0), dpi=110)
    ax = fig.add_axes([0.03, 0.30, 0.94, 0.66]); ax.imshow(bg, extent=[X0, X1, Z1, Z0]); ax.set_xlim(X0, X1); ax.set_ylim(Z1, Z0); ax.set_aspect('equal')
    cm = plt.get_cmap('viridis'); hmax = 20.0
    polys, cs = [], []
    for p in P:
        for poly in (getattr(p['geom'], 'geoms', None) or [p['geom']]):
            if isinstance(poly, Polygon) and poly.area > 0.5:
                polys.append(np.array(poly.exterior.coords)); cs.append(cm(min(1, float(np.mean(p['h'])) / hmax)))
    ax.add_collection(PolyCollection(polys, facecolors=cs, edgecolors='k', linewidths=0.2, alpha=0.85))
    for c in cols: ax.plot(c['xz'][0], c['xz'][1], 'o', ms=2.2, mfc='w', mec='k', mew=0.3)
    for p in P:
        if p['src'] != 'deck' or p['line'].length < 40: continue
        q = p['line'].interpolate(0.5, normalized=True)
        if X0 < q.x < X1 and Z0 < q.y < Z1: ax.text(q.x, q.y, '%.1f' % float(np.interp(p['line'].project(q), p['s'], p['h'])), fontsize=6, color='w', ha='center', va='center', bbox=dict(boxstyle='round,pad=0.1', fc=(0, 0, 0, 0.45), lw=0))
    sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(0, hmax)); cb = fig.colorbar(sm, ax=ax, fraction=0.018, pad=0.005); cb.set_label('deck top above grade (m)')
    ax.set_title('BR-01  Elevated landside roadways: plan (NAIP 2024, public domain, dimmed), deck levels and columns.  '
                 'Levels: ITB L3 %.2f m [%s], domestic departures curb %.2f m [%s] (less a %.2f m kerb); the rest solved under clearance '
                 'constraints [inf].  OSM (c) OpenStreetMap contributors, ODbL.' % (LV['itb']['curb'], LV['itb']['tag'], LV['domestic']['curb'], LV['domestic']['tag'], RN.KERB_M), fontsize=8.5, loc='left')
    # profiles of the two anchored structures and the main ITB approach
    for k, (nm, sel) in enumerate([('ITB departures (unit itb_departures)', 'itb_departures'), ('domestic departures loop (unit domestic_departures)', 'domestic_departures')]):
        a2 = fig.add_axes([0.05 + 0.48 * k, 0.05, 0.43, 0.20])
        for p in P:
            if p['unit'] != sel: continue
            c = np.array(p['line'].coords); d = np.hypot(c[:, 0] - c[0, 0], c[:, 1] - c[0, 1])
            a2.plot(p['pts'][:, 0], p['h'], '-', lw=1.0 if p['src'] == 'deck' else 0.6, color='C0' if p['src'] == 'deck' else 'C1')
            a2.plot(p['pts'][:, 0], bottom_of(p['h']), ':', lw=0.5, color='0.4')
        a2.axhline(0, color='k', lw=0.5); a2.set_xlabel('x east (m, world)'); a2.set_ylabel('m above grade'); a2.set_title(nm + ': deck top (blue decks, orange ramps), soffit dotted', fontsize=8)
        a2.grid(alpha=0.3)
    fig.text(0.03, 0.005, json.dumps(stats)[:400], fontsize=6)
    fig.savefig(path); plt.close(fig)


# ------------------------------------------------------------------------------------------------ main
def main(argv):
    t0 = time.time(); lines = []
    def log(s): print('[roadways %5.1f s] %s' % (time.time() - t0, s)); lines.append(s)
    os.makedirs(OUTD, exist_ok=True)
    LV = RN.asset_levels()
    # the other assets' triangles (every LOD and file), as b3d_integrate measures them
    groups0 = list(BI.GROUPS); BI.GROUPS[:] = [g for g in groups0 if g != 'roadways']
    F0, TR, files = BI.footprints(lambda s: None)
    log('asset triangles read (%s)' % ', '.join(sorted(files)))
    Fd = {(g, u): unary_union([e['geom'] for l, e in L.items() if l < 2] or [e['geom'] for e in L.values()]) for g in F0 for u, L in F0[g].items() if u != '*'}
    ways, grade, F, st = RN.network(log, F=Fd)
    # the ITB departures deck plate (review round 2, finding 1): measured on NAIP 2024 from the ITB asset's kerb outward
    h_itb = LV['itb']['curb'] - RN.KERB_M
    kerb = RP.kerb_from_asset(TR['_lods'][('itb', 'hall', 0)], LV['itb']['curb'], *RP.frame())
    M, mimg = RP.measure(h_itb, kerb, log, CROSSWALK_U); M['h_deck'] = h_itb
    lower, M['plate_poly'] = plate_outline(M, ways, log)
    sol = RN.solve_levels(ways, grade, F, LV, log, overhead=overhead_of(TR), plates=[dict(poly=M['plate_poly'], h=h_itb, why='ITB L3 deck plate (NAIP 2024)')])
    for u in sol['unresolved']: log('  UNRESOLVED ' + json.dumps(u))
    chk = RN.checks(ways, sol['ramps'], log)
    P = pieces_of(ways, sol['ramps'])
    out = [p for p in P if not CORE.contains(Point(p['pts'].mean(0)))]
    P = [p for p in P if CORE.contains(Point(p['pts'].mean(0)))]
    log('outside the core box %s: %d pieces (%.0f m) not built (ground footprint only, as before)' % (CORE.bounds, len(out), sum(p['line'].length for p in out)))
    plate = plate_piece(M, h_itb); P.insert(0, plate)
    widen_lower(P, lower, M, log)
    units = units_of(P)
    log('pieces %d (decks %d, ramp parts %d, plate 1), units %s' % (len(P), sum(1 for p in P if p['src'] == 'deck'), sum(1 for p in P if p['src'] == 'ramp'), units))
    BODY = enclosure_cuts(P, TR, F0, log)
    trim(P, TR, log, BODY)
    body_cut = {}
    for p in P:
        for k, a in p['cut_by'].items():
            if k.endswith(' inside'): body_cut[k[:-7]] = round(body_cut.get(k[:-7], 0) + a, 1)
    for _ in range(2):   # the grid edge: cut again what a second pass on the trimmed decks still finds enclosed
        left = enclosure_cuts([dict(q, rib=q['geom']) for q in P if not q['geom'].is_empty], TR, F0, lambda m: None)
        if not left: break
        LU = unary_union(list(left.values())).buffer(0.5)
        for q in P:
            if q['geom'].intersects(LU):
                q['geom'] = unary_union([g for g in (getattr(q['geom'].difference(LU), 'geoms', None) or [q['geom'].difference(LU)]) if isinstance(g, Polygon) and g.area > 0.5])
                q['against'] = unary_union([q.get('against', Polygon()), LU])
    body_left = round(sum(v.area for v in left.values()), 2)
    log('decks cut where they ran inside a building: %s m2; deck area still enclosed after the cut: %.2f m2' % (body_cut, body_left))
    cols, cst = columns([p for p in P if p['src'] != 'plate'], TR, log)
    pcols = plate_columns(plate, P, TR, log); cols += pcols; cst['plate'] = len(pcols)
    BI.GROUPS[:] = groups0
    asph_naip, asph, nsamp = naip_asphalt([p for p in P if p['src'] != 'plate'])
    log('asphalt: NAIP 2024 median sRGB %s over %d samples -> base colour %s (x %.2f linear)' % (asph_naip, nsamp, asph, NAIP_ALBEDO))
    lite_naip, lite = naip_band(plate, M['outer'])
    log('outer light-concrete roadway: NAIP 2024 median sRGB %s -> base colour %s' % (lite_naip, lite))
    mats = {'concrete': dict(rgb=CONCRETE, rough=0.85, extras=dict(src='inf', note='cast-in-place concrete, light grey'))}
    for p in P:
        if p['src'] == 'plate': p['mat'] = None; continue
        light = p['src'] == 'deck' and p['id'] in lower
        nm = ('deck_light_%d%s' if light else 'deck_%d%s') % (p['lanes'], 'o' if p['oneway'] else 't'); p['mat'] = nm
        if nm not in mats: mats[nm] = dict(rgb=(255, 255, 255), rough=0.9, png=lane_tile(p['lanes'], p['oneway'], lite if light else asph), extras=dict(src='obs colour (NAIP 2024) / inf markings' + (' (the outer light-concrete roadway along the ITB)' if light else ''), lanes=p['lanes'], oneway=p['oneway']))
    for b in M['bands']:
        if b['kind'] == 'island': continue
        n = band_lanes(b); light = b['kind'] == 'road_light'; nm = ('deck_light_%do' if light else 'deck_%do') % n
        if nm not in mats: mats[nm] = dict(rgb=(255, 255, 255), rough=0.9, png=lane_tile(n, True, lite if light else asph), extras=dict(src='obs colour (NAIP 2024) / inf markings (ITB deck plate band %s)' % b['name'], lanes=n, oneway=True))
    mats['deck_plain'] = dict(rgb=asph, rough=0.9, extras=dict(src='obs colour (NAIP 2024)', note='no markings (LOD2; the plate beyond its straight section)'))
    mats['deck_plain_light'] = dict(rgb=lite, rough=0.88, extras=dict(src='obs colour (NAIP 2024, the outer light-concrete roadway)', note='LOD2'))
    mats['island'] = dict(rgb=CONCRETE, rough=0.85, extras=dict(src='obs extent (NAIP 2024) / inf height %.2f m' % ISLAND_H, note='raised islands of the ITB deck plate'))
    mats['kerb_red'] = dict(rgb=KERB_RED, rough=0.7, extras=dict(src='obs (NAIP 2024 R - G peak) / inf colour', note='red-painted kerb (no stopping)'))
    mats['paint_white'] = dict(rgb=(226, 226, 220), rough=0.6, extras=dict(src='inf', note='crosswalk bars at the ITB curb ramps'))
    mb = MB()
    for l in (0, 1, 2):
        for p in P:
            if p['src'] == 'plate': build_piece(mb, p, P, l, None, top=False); build_plate_top(mb, p, l, mats)
            else: build_piece(mb, p, P, l, p['mat'] if l < 2 else 'deck_plain')
        for c in cols: cylinder(mb, c['unit'], l, c['xz'], GROUND_Y - 0.05, GROUND_Y + c['soffit'] + 0.05, D_COL / 2, {0: 12, 1: 6, 2: 4}[l])
    gapchk = curb_gap_check(P, TR, M, LV['itb']['curb'], log)
    clr = clearance_check(mb, TR, log); clr_p = clearance_check(mb, TR, log, piers=True)
    allxz = np.concatenate([p['pts'] for p in P]); rc = [round(float(v), 1) for v in allxz.mean(0)]
    ntri = {l: sum(int(sum(len(i) for i in b['I'])) for (u, ll, m), b in mb.d.items() if ll == l) for l in (0, 1, 2)}
    log('triangles per LOD: %s' % ntri)
    tags = dict(network='obs (OSM ODbL topology, centrelines)', widths='osm lanes x 3.6 / class default [inf]', itb_level='%s %s' % (LV['itb']['tag'], LV['itb']['source']),
                domestic_level='%s %s' % (LV['domestic']['tag'], LV['domestic']['source']), other_levels='inf (roadways_net.py solve)', structure='inf (deck depth, parapets, columns, fill)')
    ux = {u: dict(src='inf', levels=sorted({p['anchor'] or 'solved' for p in P if p['unit'] == u}), osm_ways=sorted({p['id'] for p in P if p['unit'] == u and isinstance(p['id'], int)})[:60], plate=any(p['src'] == 'plate' for p in P if p['unit'] == u)) for u in units}
    extras = dict(asset='roadways', frame='ltp-nad83-2011', ground_y=GROUND_Y, generator='tools/blender/build_roadways.py', tags=tags)
    full = os.path.join(D3, 'roadways.glb'); l2 = os.path.join(D3, 'roadways_lod2.glb')
    nb = export(full, mb, units, (0, 1, 2), mats, rc, extras, ux)
    used2 = {m for (u, l, m), b in mb.d.items() if l == 2 and b['P']}
    nb2 = export(l2, mb, units, (2,), {k: v for k, v in mats.items() if k in used2}, rc, extras, ux)
    log('wrote %s (%.2f MB), %s (%.2f MB)' % (full, nb / 1e6, l2, nb2 / 1e6))
    gr = sorted(chk['grade'], key=lambda g: -g['max_pct'])
    stats = dict(ways=st, levels=dict(anchored=sol['anchored'], constraints=sol['constraints'], crossings=sol['crossings'], unresolved=len(sol['unresolved'])),
                 ramps=len(sol['ramps']), pieces=len(P), outside_core=dict(pieces=len(out), length_m=round(sum(p['line'].length for p in out))), unresolved=sol['unresolved'], overhead_nodes=sol['overhead'],
                 cut_by_group={g: round(sum(p['cut_by'].get(g, 0) for p in P), 1) for g in BI.GROUPS}, columns=cst, tris=ntri, grade_max=gr[0] if gr else None,
                 grades_over_8pct=[g for g in gr if g['max_pct'] > 8][:20], low_crossings=chk['low'], crossings=len(chk['crossings']),
                 asset_cut_m2=round(sum(p['asset_cut_m2'] for p in P), 1), bytes=dict(full=nb, lod2=nb2),
                 itb_plate=dict(area_m2=round(plate['geom'].area, 1), measured_m2=round(M['poly'].area, 1), straight_u=M['straight'], v_kerb=round(M['v_kerb'], 2), v_edge_median=M['v_edge_median'],
                                v_cap=M['v_cap'], bands=[dict(name=b['name'], v=[round(x, 2) for x in b['v']], kind=b['kind'], lanes=band_lanes(b) if b['kind'] != 'island' else None) for b in M['bands']],
                                gaps=M['gaps'], plate_nodes=sol.get('plate_nodes'), columns=len(pcols), outer_roadway_colour=dict(naip_srgb=lite_naip, base_srgb=lite),
                                lower_outer_roadway=dict(osm_ways=sorted(lower), imaged_band_v=[round(x, 2) for x in M['outer']['v']], widened=M.get('lower', []),
                                                         note='OSM layer 1, passes under the anchored departures leg 20-30 m past the straight: kept as the lower deck (solved level)')),
                 curb_gap=gapchk, guideway_clearance=clr, guideway_pier_caps_over_decks=clr_p, deck_cut_inside_buildings_m2=body_cut, deck_left_inside_buildings_m2=body_left)
    sheet(P, cols, os.path.join(OUTD, 'roadways_plan.png'), LV, dict(pieces=len(P), columns=cst, low=len(chk['low'])))
    log('check sheet out/buildings3d/roadways_plan.png')
    Cf, duf, dvf = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    def to_uv(g):
        if g.is_empty: return g
        return unary_union([Polygon(RP.uv_of(np.array(q.exterior.coords), Cf, duf, dvf)) for q in (getattr(g, 'geoms', None) or [g]) if isinstance(q, Polygon)])
    box_uv = box(M['img']['us'][0], M['img']['vs'][0], M['img']['us'][1], M['img']['vs'][1])
    RP.sheet(M, mimg, [to_uv(p['geom']).intersection(box_uv) for p in P if p['unit'] == 'itb_departures' and not p['geom'].is_empty],
             [RP.uv_of(np.array([c['xz']]), Cf, duf, dvf)[0] for c in cols if c['unit'] == 'itb_departures'], os.path.join(OUTD, 'roadways_itb_plate.png'),
             'BR-02  ITB departures deck (review r2, finding 1): NAIP 2024 (public domain) in the ITB roof frame, relief-corrected for %.2f m (deck + parapet); '
             'measured outline (yellow), built deck after trimming at the ITB curb (magenta), bands on the straight section (cyan), columns. '
             'Curb-to-deck void max %.3f m (limit 0.3).' % (M['h_edge'], gapchk['max_void_m']))
    log('check sheet out/buildings3d/roadways_itb_plate.png')
    entry = dict(asset='roadways (elevated landside roadways: departures decks, viaducts, approach ramps)', owner='integration (review round 1, finding 1)',
                 generator='tools/blender/build_roadways.py + roadways_net.py', built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 files=dict(full='data/buildings3d/roadways.glb', lod2='data/buildings3d/roadways_lod2.glb'), frame='ltp-nad83-2011', root_translation=[rc[0], GROUND_Y, rc[1]],
                 lod_rule='root children LOD0 / LOD1 / LOD2 (extras.switch_m %s); units by extras.building' % SWITCH,
                 levels=dict(itb=dict(deck_top=round(sol['h_itb'], 3), **LV['itb']), domestic=dict(deck_top=round(sol['h_dom'], 3), **LV['domestic']),
                             solve=dict(layer_prior_m=RN.LAYER_H, ell_m=RN.ELL, ell_grade_m=RN.ELL_G, clearance_m=RN.CLEAR_MIN, deck_depth_m=RN.DECK_DEPTH, tag='inf')),
                 materials=dict(asphalt=dict(naip_median_srgb=asph_naip, base_srgb=asph, naip_albedo=NAIP_ALBEDO, src='obs colour / inf scale'), concrete=dict(srgb=CONCRETE, src='inf'),
                                markings='own painted tiles (MUTCD 3A.06 dash cycle 40 ft, 10-ft dashes) [inf]'),
                 observed=['ITB departures deck plate: outline (kerb to the outer edge, the structural gap at the south end), island extents, the red kerb - NAIP 2024 relief-corrected (roadways_itb_plate.py, sheet BR-02)',
                           'network topology / centrelines: OSM (ODbL)', 'asphalt and light-concrete colours: NAIP 2024 medians'],
                 inferred=['deck depth 1.2 m, shoulders 0.6 m, parapets 0.40 x 0.85 m, fill below a 3.2 m deck top, round columns 1.4 m at ~30 m (positions where clear)',
                           'ITB deck plate level: the ITB L3 deck top %.2f m (spec_itb level3.floor 11.5 [inf] - 0.15 kerb); the outer light-concrete roadway is NOT on the plate: '
                           'it is built as the lower deck (OSM ways 41015123 / 739695588, layer 1, solved %s m on the straight) widened to the imaged band toward the plate edge (it stops STACK_GAP short of it: under the plate it would have < 4.6 m) '
                           '(open item, see unknown); island height 0.15 m; lane counts (OSM minimum / width / 3.6 m); plate columns under the islands and the outer edge'
                           % (h_itb, ' / '.join('%.2f' % L['h_m'] for L in M.get('lower', []))),
                           'levels other than the two curbs: screened solve with layer priors %s m and clearance %.1f m (roadways_net.py); at skewed and stacked crossings '
                           'the separation is held over the ribbons\' overlap (the per-crossing deficit, XS_*), stacked pairs on an anchored way or beyond %.1f m by the trim\'s stacked cut'
                           % (RN.LAYER_H, RN.CLEAR_MIN, RN.XS_CAP),
                           'approach ramps: at-grade OSM roads lifted by the solve (ELL_G %.0f m)' % RN.ELL_G, 'lane counts / widths where OSM has none (class defaults)',
                           'lane markings (pattern, colours)'],
                 unknown=['the domestic departures-curb height (%.3f m is the domestic asset placeholder [unk])' % LV['domestic']['curb'],
                          'every viaduct level: no structural drawings or survey; OSM gives only the layer order',
                          'the ITB arrivals roadway level (OSM layer 1 west of the ITB is solved, not anchored)',
                          'whether the outer light-concrete roadway along the ITB is a lower deck (modelled: OSM ways 41015123 / 739695588, layer 1, widened to the imaged band) or on the departures deck (as the reviewer read it); NAIP 2020 / 2024 parallax of its edge is inconclusive (the 2020 lean at this spot is not calibrated)'],
                 deviations=['decks over at-grade roads with less than %.1f m clearance: the anchored domestic loop (soffit %.2f m) - the curb placeholder, kept as the domestic asset has it'
                             % (RN.CLEAR_MIN, sol['h_dom'] - RN.DECK_DEPTH),
                             'decks trimmed at the buildings\' bodies (review r2, finding 3): %s m2; Terminal 2: NAIP 2024 shows the departures roadway open to the sky with traffic between the '
                             'modelled T2 west wall and the glass curb canopy (T2 roof edge 14-20 m east of that wall), i.e. the T2 shell follows the SFO Museum outline over the curb roadway as T1 Center did '
                             'before the domestic group moved its face (manifest.json#domestic.conflicts); the roadway is therefore cut at the T2 body until the domestic group moves the T2 landside face - '
                             'the cut lifts by itself on the next build (request in manifest.json#integration.requests)' % body_cut],
                 verification=stats)
    BI.merge_manifest(entry, key='roadways')
    open(os.path.join(OUTD, 'roadways_build.log'), 'w').write('\n'.join(lines) + '\n')
    json.dump(dict(stats=stats, columns=[dict(unit=c['unit'], xz=[round(float(v), 2) for v in c['xz']], soffit=round(c['soffit'], 2), way=c['way']) for c in cols],
                   pieces=[dict(id=p['id'], src=p['src'], unit=p['unit'], anchor=p['anchor'], w=p['w'], lanes=p['lanes'], h=[round(p['hmin'], 2), round(p['hmax'], 2)], asset_cut_m2=p['asset_cut_m2'], cut_by=p['cut_by'], area_m2=round(p['geom'].area, 1)) for p in P]),
              open(os.path.join(OUTD, 'roadways_build.json'), 'w'), indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
