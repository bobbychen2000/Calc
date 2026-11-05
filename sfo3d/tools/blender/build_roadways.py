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


def trim(P, TR, log):
    """same-level overlaps go to the higher-priority piece; then every piece minus the assets' occupancy in its band"""
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
            dh = np.abs(hp(p, pts) - hp(q, pts))
            if np.median(dh) < 1.0: g = g.difference(q['geom'].buffer(0.02))
        p['geom'] = g; kept.append(i)
    # assets: occupancy (triangles) in the piece's band, chunk by chunk along it (a ramp spans 0-11 m)
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
                o = BI.occupancy(TR, g, ch.bounds, y0, y1, pad=0.5, tri_only=True)
                if not o.is_empty: cut.append(o.intersection(ch)); bygrp.setdefault(g, []).append(o.intersection(ch))
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


def overhead_of(TR, F):
    """the AirTrain guideway (landside airtrain units, elevated) as overhead structures: plan polygons and the soffit level
    (the lowest non-vertical guideway triangle over a point, >= 4 m above grade) for roadways_net.solve_levels"""
    T = TR['landside']['T'] if 'landside' in TR else np.zeros((0, 3, 3))
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
    polys = unary_union([g for (grp, u), g in F.items() if grp == 'landside' and u.startswith('airtrain')])
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


def build_piece(mb, p, P_all, lod, mat_deck):
    geom = p['geom'].simplify({0: 0.05, 1: 0.35, 2: 1.0}[lod])
    if geom.is_empty: return
    V, I = tri_polys(geom, {0: 6.0, 1: 16.0, 2: 30.0}[lod])
    if not len(I): return
    h = hp(p, V); lat, s = lateral(p, V)
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
        with open(path, 'wb') as f:
            f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(self.bin)))
            f.write(struct.pack('<II', len(j), 0x4E4F534A)); f.write(j)
            f.write(struct.pack('<II', len(self.bin), 0x004E4942)); f.write(bytes(self.bin))


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
    _, TR, files = BI.footprints(lambda s: None)
    log('asset triangles read (%s)' % ', '.join(sorted(files)))
    ways, grade, F, st = RN.network(log)
    sol = RN.solve_levels(ways, grade, F, LV, log, overhead=overhead_of(TR, F))
    for u in sol['unresolved']: log('  UNRESOLVED ' + json.dumps(u))
    chk = RN.checks(ways, sol['ramps'], log)
    P = pieces_of(ways, sol['ramps'])
    out = [p for p in P if not CORE.contains(Point(p['pts'].mean(0)))]
    P = [p for p in P if CORE.contains(Point(p['pts'].mean(0)))]
    log('outside the core box %s: %d pieces (%.0f m) not built (ground footprint only, as before)' % (CORE.bounds, len(out), sum(p['line'].length for p in out)))
    units = units_of(P)
    log('pieces %d (decks %d, ramp parts %d), units %s' % (len(P), sum(1 for p in P if p['src'] == 'deck'), sum(1 for p in P if p['src'] == 'ramp'), units))
    trim(P, TR, log)
    cols, cst = columns(P, TR, log)
    BI.GROUPS[:] = groups0
    asph_naip, asph, nsamp = naip_asphalt(P)
    log('asphalt: NAIP 2024 median sRGB %s over %d samples -> base colour %s (x %.2f linear)' % (asph_naip, nsamp, asph, NAIP_ALBEDO))
    mats = {'concrete': dict(rgb=CONCRETE, rough=0.85, extras=dict(src='inf', note='cast-in-place concrete, light grey'))}
    for p in P:
        nm = 'deck_%d%s' % (p['lanes'], 'o' if p['oneway'] else 't'); p['mat'] = nm
        if nm not in mats: mats[nm] = dict(rgb=(255, 255, 255), rough=0.9, png=lane_tile(p['lanes'], p['oneway'], asph), extras=dict(src='obs colour (NAIP 2024) / inf markings', lanes=p['lanes'], oneway=p['oneway']))
    mats['deck_plain'] = dict(rgb=asph, rough=0.9, extras=dict(src='obs colour (NAIP 2024)', note='LOD2: no markings'))
    mb = MB()
    for l in (0, 1, 2):
        for p in P: build_piece(mb, p, P, l, p['mat'] if l < 2 else 'deck_plain')
        for c in cols: cylinder(mb, c['unit'], l, c['xz'], GROUND_Y - 0.05, GROUND_Y + c['soffit'] + 0.05, D_COL / 2, {0: 12, 1: 6, 2: 4}[l])
    allxz = np.concatenate([p['pts'] for p in P]); rc = [round(float(v), 1) for v in allxz.mean(0)]
    ntri = {l: sum(int(sum(len(i) for i in b['I'])) for (u, ll, m), b in mb.d.items() if ll == l) for l in (0, 1, 2)}
    log('triangles per LOD: %s' % ntri)
    tags = dict(network='obs (OSM ODbL topology, centrelines)', widths='osm lanes x 3.6 / class default [inf]', itb_level='%s %s' % (LV['itb']['tag'], LV['itb']['source']),
                domestic_level='%s %s' % (LV['domestic']['tag'], LV['domestic']['source']), other_levels='inf (roadways_net.py solve)', structure='inf (deck depth, parapets, columns, fill)')
    ux = {u: dict(src='inf', levels=sorted({p['anchor'] or 'solved' for p in P if p['unit'] == u}), osm_ways=sorted({p['id'] for p in P if p['unit'] == u})[:60]) for u in units}
    extras = dict(asset='roadways', frame='ltp-nad83-2011', ground_y=GROUND_Y, generator='tools/blender/build_roadways.py', tags=tags)
    full = os.path.join(D3, 'roadways.glb'); l2 = os.path.join(D3, 'roadways_lod2.glb')
    nb = export(full, mb, units, (0, 1, 2), mats, rc, extras, ux)
    nb2 = export(l2, mb, units, (2,), {k: v for k, v in mats.items() if k in ('concrete', 'deck_plain')}, rc, extras, ux)
    log('wrote %s (%.2f MB), %s (%.2f MB)' % (full, nb / 1e6, l2, nb2 / 1e6))
    gr = sorted(chk['grade'], key=lambda g: -g['max_pct'])
    stats = dict(ways=st, levels=dict(anchored=sol['anchored'], constraints=sol['constraints'], crossings=sol['crossings'], unresolved=len(sol['unresolved'])),
                 ramps=len(sol['ramps']), pieces=len(P), outside_core=dict(pieces=len(out), length_m=round(sum(p['line'].length for p in out))), unresolved=sol['unresolved'], overhead_nodes=sol['overhead'],
                 cut_by_group={g: round(sum(p['cut_by'].get(g, 0) for p in P), 1) for g in BI.GROUPS}, columns=cst, tris=ntri, grade_max=gr[0] if gr else None,
                 grades_over_8pct=[g for g in gr if g['max_pct'] > 8][:20], low_crossings=chk['low'], crossings=len(chk['crossings']),
                 asset_cut_m2=round(sum(p['asset_cut_m2'] for p in P), 1), bytes=dict(full=nb, lod2=nb2))
    sheet(P, cols, os.path.join(OUTD, 'roadways_plan.png'), LV, dict(pieces=len(P), columns=cst, low=len(chk['low'])))
    log('check sheet out/buildings3d/roadways_plan.png')
    entry = dict(asset='roadways (elevated landside roadways: departures decks, viaducts, approach ramps)', owner='integration (review round 1, finding 1)',
                 generator='tools/blender/build_roadways.py + roadways_net.py', built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 files=dict(full='data/buildings3d/roadways.glb', lod2='data/buildings3d/roadways_lod2.glb'), frame='ltp-nad83-2011', root_translation=[rc[0], GROUND_Y, rc[1]],
                 lod_rule='root children LOD0 / LOD1 / LOD2 (extras.switch_m %s); units by extras.building' % SWITCH,
                 levels=dict(itb=dict(deck_top=round(sol['h_itb'], 3), **LV['itb']), domestic=dict(deck_top=round(sol['h_dom'], 3), **LV['domestic']),
                             solve=dict(layer_prior_m=RN.LAYER_H, ell_m=RN.ELL, ell_grade_m=RN.ELL_G, clearance_m=RN.CLEAR_MIN, deck_depth_m=RN.DECK_DEPTH, tag='inf')),
                 materials=dict(asphalt=dict(naip_median_srgb=asph_naip, base_srgb=asph, naip_albedo=NAIP_ALBEDO, src='obs colour / inf scale'), concrete=dict(srgb=CONCRETE, src='inf'),
                                markings='own painted tiles (MUTCD 3A.06 dash cycle 40 ft, 10-ft dashes) [inf]'),
                 inferred=['deck depth 1.2 m, shoulders 0.6 m, parapets 0.40 x 0.85 m, fill below a 3.2 m deck top, round columns 1.4 m at ~30 m (positions where clear)',
                           'levels other than the two curbs: screened solve with layer priors %s m and clearance %.1f m (roadways_net.py)' % (RN.LAYER_H, RN.CLEAR_MIN),
                           'approach ramps: at-grade OSM roads lifted by the solve (ELL_G %.0f m)' % RN.ELL_G, 'lane counts / widths where OSM has none (class defaults)',
                           'lane markings (pattern, colours)'],
                 unknown=['the domestic departures-curb height (%.3f m is the domestic asset placeholder [unk])' % LV['domestic']['curb'],
                          'every viaduct level: no structural drawings or survey; OSM gives only the layer order',
                          'the ITB arrivals roadway level (OSM layer 1 west of the ITB is solved, not anchored)'],
                 deviations=['decks over at-grade roads with less than %.1f m clearance: the anchored domestic loop (soffit %.2f m) - the curb placeholder, kept as the domestic asset has it'
                             % (RN.CLEAR_MIN, sol['h_dom'] - RN.DECK_DEPTH)],
                 verification=stats)
    BI.merge_manifest(entry, key='roadways')
    open(os.path.join(OUTD, 'roadways_build.log'), 'w').write('\n'.join(lines) + '\n')
    json.dump(dict(stats=stats, columns=[dict(unit=c['unit'], xz=[round(float(v), 2) for v in c['xz']], soffit=round(c['soffit'], 2), way=c['way']) for c in cols],
                   pieces=[dict(id=p['id'], src=p['src'], unit=p['unit'], anchor=p['anchor'], w=p['w'], lanes=p['lanes'], h=[round(p['hmin'], 2), round(p['hmax'], 2)], asset_cut_m2=p['asset_cut_m2'], cut_by=p['cut_by'], area_m2=round(p['geom'].area, 1)) for p in P]),
              open(os.path.join(OUTD, 'roadways_build.json'), 'w'), indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
