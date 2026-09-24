"""Physical clearance audit of what the 3-D app places on the ground (out/draw/scene2d.json), with shapely.

Objects are plan polygons with a height range (world y): building footprints, elevated walkways / AirTrain deck / ITB
roof overhang, mast bases and heads, signs, VDGS posts, every jet-bridge primitive (walkway, pedestal, rotunda, three
tunnel sections, drive legs/wheels/beam, PCA unit, cab, bellows, stair ...; exact hulls recorded from gates.js
bridgeGeo()), GSE (real vehicle-mesh hulls at their instance transforms) and aircraft (plan of the rendered model or
procedural airframe + per-cell min/max height rasters, so "does the tunnel pass over the wing?" is answered in 3-D).

Scenarios
  LIVE      the snapshot as displayed: live aircraft at their displayed poses, bridges in their current pose, GSE
  REST      every stand empty, every bridge retracted (k = 0)
  DOCK-REF  every stand occupied by its class reference type (gates.js REF_TYPE), bridges docked (k = 1; L2 bridges
            dock only E/F-class types, gates.js docks())
  DOCK-MAX  every stand occupied by its largest non-oversize type (standFits, widest span then longest), bridges docked
  ENVELOPE  every stand's class envelope = union of the planforms (procedural TYPES body AND rendered model) of every
            non-oversize type the stand accepts; neighbours' envelopes, buildings, masts, VDGS, signs, other stands'
            parked bridges and the stand's own parked bridges (the arriving aircraft must clear them)
  OVERSIZE  EL/F stands also take bigger types (traffic.js: 747/A380 on maxSpan >= 64 m stands, neighbours then
            blocked when their noses are closer than 0.5 (spanA + spanB) + 8 m): every overlapped neighbour must be
            blocked, and the oversize aircraft must clear the neighbours' parked bridges and buildings
Severities
  COLLISION   solids intersect (plan overlap AND the vertical extents overlap at the same plan point: aircraft by their
              per-cell height rasters, boxes and jet-bridge tubes as exact parallelepipeds recorded by extract2d.mjs -
              a sloping tunnel is as high as it is at that point, not its whole y range)
  OFF-PAVEMENT two views, reported separately:
              gear-off-pavement          visual: a rendered gear contact point (TYPES nose + main gear) is not on the
                                         rendered paved raster (tyres drawn on grass / sand)
              gear-off-physics-pavement  physics: a GroundPhysics gear point (ground.js samples(): xNose, xMain +-
                                         track/2) is neither on that raster nor on the OSM taxi net (ground.js
                                         pavedUnion: raster OR TaxiNet.paved) - what GroundPhysics itself would accept
  OBSTRUCTION a raised solid (approach-light pier / post, sign) stands on a surface aircraft use: the runway (incl. the
              displaced-threshold area), a blast pad, an EMAS bed or a taxiway polygon; a sign on other physics-legal
              pavement (paved raster, where GroundPhysics may put an aircraft) is a WARNING
  CLEARANCE   aircraft closer than the ICAO Annex 14 stand clearance (3.0 / 4.5 / 7.5 m by code letter) - a design
              check, not a physical conflict (SFO has measured real spacings below the design value)
  WARNING     tight (< 0.5 m between bridges / GSE, < 3 m aircraft to building), bridge tunnel slope > 1:12,
              tunnel sections that stretch instead of telescoping
"""
import json, math, os, time, collections
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, MultiPolygon, box as sbox
from shapely.strtree import STRtree
from shapely.ops import unary_union
from common import (scene, OUT, buildings, poly_rings, hull_poly, circle, AcGeom, ac_instance_geom, plan_world, model_geom, body_geom,
                    stand_W, gear_points_world, m4, G, polys_of, w2st, NetPaved, provenance, phys_gear_points)
from measure import PaveMask

SCEN_SAME_STAND_SKIP = {'DOCK-REF', 'DOCK-MAX', 'ENVELOPE'}   # one aircraft per stand by construction there; never in LIVE
ICAO = {'A': 3.0, 'B': 3.0, 'C': 4.5, 'CL': 4.5, 'D': 7.5, 'E': 7.5, 'EL': 7.5, 'F': 7.5}  # Annex 14 3.13.6
CAB_GROUP = {'cab', 'cab-roof', 'bellows', 'floodlight', 'beacon'}
T_CODE = lambda T: 'F' if T['wing']['span'] >= 65 else 'E' if T['wing']['span'] >= 52 else 'D' if T['wing']['span'] >= 36 else 'C' if T['wing']['span'] >= 24 else 'B'


def pp_heights(pps, X, Z, eps=1e-4):
    """vertical extent (lo, hi) at plan points (X, Z) of a union of parallelepipeds {o, E=[e1, e2, e3]} (points o + a e1
    + b e2 + c e3, a, b, c in [0, 1]); nan where the vertical line misses every one. Exact for boxes and tubes in any
    orientation (a sloping tunnel, a 40 deg stair)."""
    X = np.asarray(X, float); Z = np.asarray(Z, float); n = len(X)
    lo = np.full(n, np.nan); hi = np.full(n, np.nan)
    for pp in pps or []:
        o = np.asarray(pp['o'], float); E = np.asarray(pp['E'], float).T
        if abs(np.linalg.det(E)) < 1e-12: continue
        Ei = np.linalg.inv(E)
        base = Ei @ np.vstack([X - o[0], np.full(n, -o[1]), Z - o[2]]); slope = Ei[:, 1]
        ylo = np.full(n, -np.inf); yhi = np.full(n, np.inf)
        for i in range(3):
            b = base[i]; sl = slope[i]
            if abs(sl) < 1e-12:
                out = (b < -eps) | (b > 1 + eps); ylo[out] = np.inf; yhi[out] = -np.inf
            else:
                y1 = (-eps - b) / sl; y2 = (1 + eps - b) / sl
                ylo = np.maximum(ylo, np.minimum(y1, y2)); yhi = np.minimum(yhi, np.maximum(y1, y2))
        ok = ylo <= yhi
        lo[ok] = np.fmin(lo[ok], ylo[ok]); hi[ok] = np.fmax(hi[ok], yhi[ok])
    return lo, hi


class Obj:
    __slots__ = ('cat', 'id', 'poly', 'y0', 'y1', 'stand', 'part', 'label', 'ac', 'bridge', 'extra', 'pp')

    def __init__(self, cat, oid, poly, y0, y1, stand=None, part=None, label=None, ac=None, bridge=None, extra=None, pp=None):
        self.cat, self.id, self.poly, self.y0, self.y1 = cat, oid, poly, y0, y1
        self.stand, self.part, self.label, self.ac, self.bridge, self.extra = stand, part, label or oid, ac, bridge, extra or {}
        self.pp = pp or None

    def heights(self, X, Z):
        """(lo, hi) of the solid at plan points: aircraft height rasters, exact parallelepipeds, else the y band"""
        if self.ac is not None: return self.ac.heights(X, Z)
        if self.pp: return pp_heights(self.pp, X, Z)
        n = len(X); return np.full(n, self.y0), np.full(n, self.y1)

    def ent(self):
        """(entity key, entity label): conflicts are aggregated per pair of entities (a whole bridge, a stand's
        envelope, an aircraft, a building ...), keeping the worst part pair"""
        if self.cat == 'bridge': return f'bridge:{self.bridge}', self.extra.get('elabel', self.label)
        if self.cat in ('envelope', 'envelope-type'): return f'env:{self.stand}', f'{self.stand} class envelope'
        if self.cat == 'vdgs': return f'vdgs:{self.stand}', f'{self.stand} VDGS / stand sign'
        if self.cat in ('mast', 'pier'): return self.id.split(':')[0], self.extra.get('elabel', self.label)
        return self.id, self.label

    def ref(self):
        e, el = self.ent()
        g = self.poly.simplify(0.15)
        rings = [np.round(np.asarray(p.exterior.coords), 2).tolist() for p in polys_of(g)]
        return dict(cat=self.cat, id=self.id, ent=e, elabel=el, stand=self.stand, part=self.part, label=self.label, type=self.extra.get('type'), y=[round(self.y0, 2), round(self.y1, 2)], geom=rings)


# ------------------------------------------------------------------------------------------------ aircraft objects
class Ac:
    def __init__(self, geom, W, label, stand=None, type_key=None, source=None):
        self.g, self.W = geom, W; self.label, self.stand, self.type = label, stand, type_key
        self.A = W[[0, 2]][:, [0, 2]]; self.t = W[[0, 2], 3]; self.Ai = np.linalg.inv(self.A); self.yoff = W[1, 3]
        self.plan = plan_world(geom, W); self.source = source or geom.source

    def heights(self, X, Z):
        L = self.Ai @ np.vstack([np.asarray(X) - self.t[0], np.asarray(Z) - self.t[1]])
        lo, hi = self.g.heights_at(L[0], L[1]); return lo + self.yoff, hi + self.yoff


def ac_obj(ac, cat='aircraft', oid=None):
    return Obj(cat, oid or ac.label, ac.plan, ac.g.ybot + ac.yoff, ac.g.ytop + ac.yoff, stand=ac.stand, label=ac.label, ac=ac, extra=dict(type=ac.type, source=ac.source))


def type_geom(k, rendered=True):
    """geometry of TYPES key k as the app renders it when parked (model if one is mapped, else procedural)"""
    S = scene(); tr = S['typeRender'].get(k) or {}
    if rendered and tr.get('modelKey') and tr.get('placement'):
        return model_geom(tr['modelKey'], json.dumps(tr['stretch'], sort_keys=True) if tr.get('stretch') else '', json.dumps(tr['placement']))
    return body_geom(k)


def stand_ac(st, k, rendered=True):
    T = scene()['types'][k]; W = stand_W(st['nose'], st['dir'], T)
    return Ac(type_geom(k, rendered), W, f'{st["name"]}:{k}' + ('' if rendered else '(TYPES)'), stand=st['name'], type_key=k)


# ------------------------------------------------------------------------------------------------ static objects
def static_objects():
    S = scene(); g = G(); out = []
    for b in buildings():
        if b.get('notBuilt'): continue
        p = poly_rings(b['rings'])
        if p.is_empty: continue
        out.append(Obj('building', b['id'] + ':' + b['name'], p, b['y0'], b['y1'], label=b['name'] + (' (elevated walkway)' if b['kind'] == 'walkway' else ''), extra=dict(kind=b['kind'])))
    if S.get('itbRoof'):
        itb = [b for b in buildings() if b['kind'] == 'hall' and 'International' in b['name']]
        over = hull_poly(S['itbRoof']['hull']).difference(unary_union([poly_rings(b['rings']) for b in itb]).buffer(0.5))
        for i, p in enumerate(polys_of(over)):
            if p.area > 5: out.append(Obj('building', f'itb-roof-overhang{i}', p, g + 20.7, S['itbRoof']['y'][1], label='ITB wing-roof overhang (underside >= 20.7 m, terminals.js greatHall)', extra=dict(kind='roof')))
    for i, m in enumerate(S['masts']):
        if m['removed']: continue
        el = f'floodlight mast {i}'
        if m.get('prims'):   # the geometry items.js buildMasts() emits: base, pole, platform ring, yawed head bar, luminaires
            for k, p in enumerate(m['prims']):
                if len(p['hull']) >= 3: out.append(Obj('mast', f'mast{i}:{p["part"]}:{k}', hull_poly(p['hull']), p['y'][0], p['y'][1], part=p['part'], label=f'{el} {p["part"]}', pp=p.get('pp'), extra=dict(elabel=el)))
        else:
            out.append(Obj('mast', f'mast{i}:pole', circle((m['x'], m['z']), m['r']), g, g + m['h'], label=el, extra=dict(elabel=el)))
    for i, s in enumerate(S['signs']):
        c = np.array(s['c']); u = np.array(s['u']); n = np.array([-u[1], u[0]]); hw, hd = s['w'] / 2, s['d'] / 2
        P = [c - u * hw - n * hd, c + u * hw - n * hd, c + u * hw + n * hd, c - u * hw + n * hd]
        out.append(Obj('sign', f'sign{i}', Polygon(P), s['y0'], s['y0'] + s['h'], label=f'{s["kind"]} sign {i}'))
    for st in S['stands']:
        for j, p in enumerate(st.get('vdgs') or []):
            if len(p['hull']) >= 3: out.append(Obj('vdgs', f'{st["name"]}:{p["part"]}:{j}', hull_poly(p['hull']), p['y'][0], p['y'][1], stand=st['name'], part=p['part'], label=f'{st["name"]} {p["part"]}', pp=p.get('pp')))
    for pr in S.get('piers') or []:
        el = f'RWY {pr.get("end") or "?"} {pr.get("type") or ""} approach-light {"pier" if pr["water"] else "post"} {pr.get("fromThr") or 0:.0f} m from the threshold'
        for k, p in enumerate(pr['prims']):
            if len(p['hull']) >= 3: out.append(Obj('pier', f'pier{pr["i"]}:{p["part"]}:{k}', hull_poly(p['hull']), p['y'][0], p['y'][1], part=p['part'], label=f'{el} ({p["part"]})', pp=p.get('pp'),
                                                   extra=dict(elabel=el, water=pr['water'], end=pr.get('end'), fromThr=pr.get('fromThr'), fromEnd=pr.get('fromEnd'), base=pr['base'])))
    return out


def bridge_objects(pose):
    S = scene(); out = []
    for bi, b in enumerate(S['bridges']):
        P = b['poses'].get(pose)
        if not P: continue
        for pi, p in enumerate(P['parts']):
            if len(p['hull']) < 3: continue
            el = f'{b["stand"]} bridge {b["gate"]} (L{b["door"]})'
            out.append(Obj('bridge', f'{b["stand"]}/{b["gate"]}/L{b["door"]}:{p["part"]}:{pi}', hull_poly(p['hull']), p['y'][0], p['y'][1], stand=b['stand'], part=p['part'], bridge=bi, label=f'{el} {p["part"]}', extra=dict(elabel=el, door=b['door']), pp=p.get('pp')))
    return out


def gse_objects():
    S = scene(); out = []
    for i, v in enumerate(S['gse']):
        if len(v['hull']) < 3: continue
        # the stand it serves: nearest occupied stand nose
        st = min((s for s in S['stands'] if s['acType']), key=lambda s: math.hypot(s['nose'][0] - v['pos'][0], s['nose'][1] - v['pos'][1]), default=None)
        out.append(Obj('gse', f'gse{i}:{v["kind"]}', hull_poly(v['hull']), v['y'][0], v['y'][1], stand=st['name'] if st else None, part=v['kind'], label=f'{v["kind"]} ({st["name"] if st else "?"})'))
    return out


# ------------------------------------------------------------------------------------------------ pair tests
def sample_region(R, step=0.25):
    if R.is_empty: return np.zeros((0, 2))
    x0, z0, x1, z1 = R.bounds
    xs = np.arange(x0 + step / 2, x1, step); zs = np.arange(z0 + step / 2, z1, step)
    pts = []
    if len(xs) and len(zs):
        X, Z = np.meshgrid(xs, zs); m = shapely.contains_xy(R, X, Z); pts.append(np.c_[X[m], Z[m]])
    for p in polys_of(R): pts.append(np.array(p.exterior.coords)); pts.append(np.array(p.representative_point().coords))
    return np.concatenate(pts) if pts else np.zeros((0, 2))


def vertical(a, b, R):
    """(collide, min vertical gap) of objects a, b over their plan-overlap region R (per-point vertical extents)"""
    P = sample_region(R)
    if not len(P): return False, None
    alo, ahi = a.heights(P[:, 0], P[:, 1]); blo, bhi = b.heights(P[:, 0], P[:, 1])
    ok = ~(np.isnan(alo) | np.isnan(blo))
    if not ok.any(): return False, None
    gap = np.maximum(blo[ok] - ahi[ok], alo[ok] - bhi[ok])
    return bool((gap < 0).any()), float(gap.min())


def depth_of(R):
    if R.is_empty: return 0.0
    try:
        r = R.minimum_rotated_rectangle; c = np.array(r.exterior.coords)
        return float(min(np.linalg.norm(c[1] - c[0]), np.linalg.norm(c[2] - c[1])))
    except Exception: return 0.0


SEV = {'COLLISION': 0, 'OFF-PAVEMENT': 1, 'OBSTRUCTION': 2, 'CLEARANCE': 3, 'WARNING': 4}


class Audit:
    def __init__(self):
        self.best = {}; self.stats = collections.Counter()

    def add(self, scen, kind, sev, a, b, dist=None, area=None, depth=None, vgap=None, loc=None, note=''):
        A = a.ref() if isinstance(a, Obj) else dict(a, ent=a.get('id'), elabel=a.get('label'))
        B = b.ref() if isinstance(b, Obj) else dict(b, ent=b.get('id'), elabel=b.get('label'))
        if A['ent'] > B['ent']: A, B = B, A
        rec = dict(scenario=scen, kind=kind, severity=sev, a=A, b=B, dist=None if dist is None else round(dist, 2), area=None if area is None else round(area, 2),
                   depth=None if depth is None else round(depth, 2), vgap=None if vgap is None else round(vgap, 2), loc=None if loc is None else [round(loc[0], 1), round(loc[1], 1)], note=note)
        key = (scen, kind, A['ent'], B['ent'])
        worse = lambda r: (SEV[r['severity']], -(r['depth'] or 0), -(r['area'] or 0), r['dist'] if r['dist'] is not None else 0)
        old = self.best.get(key)
        parts = f'{A.get("part") or A["cat"]} x {B.get("part") or B["cat"]}'
        types = {t for t in (A.get('type'), B.get('type')) if t}
        if old is None:
            rec['parts'] = {parts}; rec['types'] = types; rec['count'] = 1; self.best[key] = rec
        else:
            old['parts'].add(parts); old['types'] |= types; old['count'] += 1
            if worse(rec) < worse(old):
                rec['parts'], rec['types'], rec['count'] = old['parts'], old['types'], old['count']; self.best[key] = rec

    @property
    def items(self):
        out = []
        for r in self.best.values():
            r = dict(r); r['parts'] = sorted(r['parts']); r['types'] = sorted(r['types']); out.append(r)
        return out

    def pairs(self, scen, kind, A, B, same=False, skip=None, warn=None, clear=None, maxd=30.0, vert=True, note_fn=None):
        """test every a in A against every b in B within maxd; warn: distance below which to record a WARNING
        (callable or number); clear: callable(a, b) -> ICAO clearance for CLEARANCE records"""
        if not A or not B: return
        tree = STRtree([b.poly for b in B])
        for i, a in enumerate(A):
            for j in tree.query(a.poly.buffer(maxd)):
                b = B[j]
                if same and (b is a or (id(b) < id(a))): continue
                if skip and skip(a, b): continue
                self.stats[(scen, kind, 'tested')] += 1
                d = a.poly.distance(b.poly)
                if d <= 1e-6:
                    R = a.poly.intersection(b.poly)
                    if R.area < 1e-4 and not vert: continue
                    col, vg = vertical(a, b, R) if vert else (True, None)
                    loc = R.representative_point().coords[0] if not R.is_empty else a.poly.representative_point().coords[0]
                    dep = depth_of(R)
                    if col and dep < 0.1 and R.area < 0.1: self.add(scen, kind, 'WARNING', a, b, dist=0.0, area=R.area, depth=dep, vgap=vg, loc=loc, note=f'touching ({dep * 100:.0f} cm)')
                    elif col: self.add(scen, kind, 'COLLISION', a, b, dist=0.0, area=R.area, depth=dep, vgap=vg, loc=loc, note=note_fn(a, b, R) if note_fn else '')
                    elif vg is not None and vg < 0.3: self.add(scen, kind, 'WARNING', a, b, dist=0.0, area=R.area, depth=depth_of(R), vgap=vg, loc=loc, note=f'passes {vg:.2f} m above/below (plan overlap {R.area:.1f} m2)')
                    continue
                c = clear(a, b) if clear else None
                w = warn(a, b) if callable(warn) else warn
                if c is not None and d < c:
                    p1, p2 = shapely.ops.nearest_points(a.poly, b.poly); loc = ((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)
                    self.add(scen, kind, 'CLEARANCE', a, b, dist=d, loc=loc, note=f'{d:.1f} m < ICAO {c} m')
                elif w is not None and d < w:
                    p1, p2 = shapely.ops.nearest_points(a.poly, b.poly); loc = ((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)
                    self.add(scen, kind, 'WARNING', a, b, dist=d, loc=loc, note=f'only {d:.2f} m apart')


def bridge_building_skip(a, b):
    return False


def run():
    S = scene(); t0 = time.time(); au = Audit(); g = G()
    stands = {s['name']: s for s in S['stands']}
    pave = PaveMask(); pave16 = PaveMask16(); net = NetPaved(); netcheck = net.check()
    if netcheck: print(f'  taxi-net replica vs the page: {netcheck["agree"] * 100:.2f} % of {netcheck["n"]} points agree')
    statics = static_objects()
    buildings = [o for o in statics if o.cat == 'building']; masts = [o for o in statics if o.cat == 'mast']
    signs = [o for o in statics if o.cat == 'sign']; vdgs = [o for o in statics if o.cat == 'vdgs']; piers = [o for o in statics if o.cat == 'pier']
    attach = {bi: np.array(b['attach']) for bi, b in enumerate(S['bridges'])}

    def bridge_vs_static(scen, BR):
        # the fixed walkway starts inside the building at its attach point: only overlaps further than 3 m from the
        # attach point count
        def note(a, b, R): return ''
        def bb_skip(a, b):
            if a.part == 'walkway' and b.cat == 'building':
                rest = a.poly.intersection(b.poly).difference(Point(attach[a.bridge]).buffer(3.0))
                return rest.area < 0.3
            return False
        au.pairs(scen, 'bridge-building', BR, buildings, skip=bb_skip, maxd=5)
        au.pairs(scen, 'bridge-mast', BR, masts, maxd=5, warn=0.3)
        au.pairs(scen, 'bridge-vdgs', BR, [v for v in vdgs], maxd=5, warn=0.3)
        au.pairs(scen, 'bridge-sign', BR, signs, maxd=5)

    def bridge_vs_bridge(scen, BR):
        au.pairs(scen, 'bridge-bridge', BR, BR, same=True, skip=lambda a, b: a.bridge == b.bridge, warn=lambda a, b: 0.5 if (a.part not in ('column',) and b.part not in ('column',)) else None, maxd=2)

    def bridge_vs_ac(scen, BR, ACS):
        own_cab = []
        def skip(a, b):
            if a.stand == b.stand and a.part in CAB_GROUP:
                own_cab.append((a, b)); return True
            return False
        au.pairs(scen, 'bridge-aircraft', BR, ACS, skip=skip, maxd=3)
        # docked cab against its own aircraft: the bellows touch the fuselage; flag penetration beyond 0.6 m
        for a, b in own_cab:
            R = a.poly.intersection(b.poly)
            if R.is_empty: continue
            P = sample_region(R, 0.1)
            if not len(P): continue
            bd = shapely.distance(shapely.points(P), b.poly.exterior if isinstance(b.poly, Polygon) else b.poly.boundary)
            pen = float(np.max(bd)) if len(bd) else 0.0
            col, vg = vertical(a, b, R)
            if col and pen > 0.6 and a.part != 'bellows':
                au.add(scen, 'bridge-cab-own-aircraft', 'COLLISION', a, b, dist=0, area=R.area, depth=pen, vgap=vg, loc=R.representative_point().coords[0], note=f'{a.part} {pen:.2f} m inside the fuselage outline')
            elif col and pen > 1.0:
                au.add(scen, 'bridge-cab-own-aircraft', 'WARNING', a, b, dist=0, area=R.area, depth=pen, vgap=vg, loc=R.representative_point().coords[0], note=f'bellows {pen:.2f} m inside the fuselage outline')

    def ac_checks(scen, ACS, clearance=True):
        def clear(a, b):
            if not clearance or a.stand is None or b.stand is None: return None
            ca, cb = stands[a.stand]['cls'], stands[b.stand]['cls']; return max(ICAO[ca], ICAO[cb])
        # the same-stand skip only where one aircraft per stand holds by construction; in LIVE two aircraft assigned
        # to one gate must be tested against each other
        same = (lambda a, b: a.stand is not None and a.stand == b.stand) if scen in SCEN_SAME_STAND_SKIP else None
        au.pairs(scen, 'aircraft-aircraft', ACS, ACS, same=True, skip=same, clear=clear, maxd=10)
        au.pairs(scen, 'aircraft-building', ACS, buildings, warn=lambda a, b: 3.0 if (a.stand and b.extra.get('kind') != 'walkway') else None, maxd=4)
        au.pairs(scen, 'aircraft-mast', ACS, masts, maxd=3)
        au.pairs(scen, 'aircraft-vdgs', ACS, vdgs, skip=lambda a, b: False, maxd=2)
        au.pairs(scen, 'aircraft-sign', ACS, signs, maxd=2)
        au.pairs(scen, 'aircraft-pier', ACS, piers, maxd=2)

    def pavement(scen, items):
        """items: list of (Obj, T type dict, W). Visual view: rendered gear on the rendered paved raster; physics view:
        GroundPhysics' own gear points on raster OR OSM taxi net (ground.js pavedUnion)"""
        for o, T, W in items:
            gp = gear_points_world(T, W)
            X = np.array([p[0] for p in gp]); Z = np.array([p[1] for p in gp])
            on = pave(X, Z); on16 = pave16(X, Z)
            au.stats[(scen, 'gear-on-pavement', 'tested')] += 1
            if not on.all():
                bad = [gp[i][2] for i in range(len(gp)) if not on[i]]
                au.add(scen, 'gear-off-pavement', 'OFF-PAVEMENT', o, dict(cat='pavement', id='paved raster 1.0 m', label='rendered paved raster (1.0 m): visual'), loc=(X[~on][0], Z[~on][0]),
                       note='visual: rendered ' + ', '.join(bad) + ' gear on unpaved ground' + (' (physics accepts it: OSM taxi net)' if phys_ok(T, W) else ''))
            elif not on16.all():
                au.add(scen, 'gear-off-pavement', 'WARNING', o, dict(cat='pavement', id='paved raster 1.6 m', label='mobile-quality paved raster (1.6 m)'), loc=(X[~on16][0], Z[~on16][0]), note='on pavement at 1.0 m but not on the 1.6 m (mobile/low quality) raster')
            PX, PZ, names = phys_gear(T, W); ok = pave(PX, PZ) | net(PX, PZ)
            au.stats[(scen, 'gear-on-physics-pavement', 'tested')] += 1
            if not ok.all():
                au.add(scen, 'gear-off-physics-pavement', 'OFF-PAVEMENT', o, dict(cat='pavement', id='physics pavement', label='GroundPhysics pavement (raster OR OSM taxi net): physics'), loc=(PX[~ok][0], PZ[~ok][0]),
                       note='physics: GroundPhysics ' + ', '.join(n for n, k in zip(names, ok) if not k) + ' gear point off raster and taxi net')

    phys_gear = phys_gear_points

    def phys_ok(T, W):
        X, Z, _ = phys_gear(T, W); return bool((pave(X, Z) | net(X, Z)).all())

    # ---------------------------------------------------------------- static: overlapping building footprints (both
    # extruded -> coincident walls / roofs fight in the depth buffer). Terminal parts sit on the ramp-level complex by
    # design and are skipped; everything else that overlaps by more than 5 m2 is reported.
    part_kinds = {'apron-level', 'pier', 'hall', 'walkway'}
    for i, a in enumerate(buildings):
        for b in buildings[i + 1:]:
            ka, kb = a.extra.get('kind'), b.extra.get('kind')
            if (ka in part_kinds and kb in part_kinds) or 'roof' in (ka, kb) or 'rail' in (ka, kb): continue
            if not a.poly.intersects(b.poly): continue
            if 'walkway' in (ka, kb): continue  # sky bridges enter the buildings they connect
            R = a.poly.intersection(b.poly)
            if R.area < 5 or not (a.y0 < b.y1 and b.y0 < a.y1): continue
            small, big = (a, b) if a.poly.area < b.poly.area else (b, a); frac = R.area / small.poly.area
            coplanar = abs(a.y1 - b.y1) < 1.0
            if frac > 0.95 and small.y1 < big.y1 - 1.0: continue  # fully hidden inside a taller building
            note = (f'roofs at the same height ({a.y1 - G():.1f} / {b.y1 - G():.1f} m) over {R.area:.0f} m2: coplanar faces z-fight' if coplanar
                    else f'walls interpenetrate: {frac * 100:.0f} % of {small.label} lies inside {big.label} ({small.y1 - G():.1f} vs {big.y1 - G():.1f} m high)')
            if frac > 0.5 and ka == kb == 'airtrain': note += ' - probably one station listed twice under two names (airport.js only skips exact-name duplicates)'
            au.add('STATIC', 'building-building', 'WARNING', a, b, dist=0, area=R.area, depth=depth_of(R), loc=R.representative_point().coords[0], note=note)
    # ---------------------------------------------------------------- STATIC: raised solids on movement surfaces
    surf = []
    for rw in S['runways']: surf.append(('runway', f'RWY {rw["name"][0]}/{rw["name"][1]}', Polygon(rw['corners'])))
    for z in S['endZones']: surf.append(('emas' if z['kind'] == 'EMAS' else 'blastpad', f'{"EMAS area" if z["kind"] == "EMAS" else "blast pad"} {z["end"]}', Polygon(z['rectW'])))
    for b in S.get('emasBeds') or []: surf.append(('emas-bed', f'EMAS bed {b["end"]} (3-D)', hull_poly(b['hull'])))
    for t in S['pave']['taxiways']:
        for poly in t['polys']: surf.append(('taxiway', f'taxiway {t["name"]}', poly_rings(poly)))
    stree = STRtree([q[2] for q in surf])
    import cv2
    from scipy import ndimage
    pv = pave.pave; dt_in = ndimage.distance_transform_edt(pv) * pave.res   # depth inside the paved raster (m)
    def depth_in_paved(x, z):
        s_, t_ = w2st(x, z); i = int((s_ - pave.s0) / pave.res); j = int((pave.t0 + pave.h - t_) / pave.res)
        return float(dt_in[j, i]) if 0 <= j < dt_in.shape[0] and 0 <= i < dt_in.shape[1] else 0.0
    def obstruction(objs, what):
        by = collections.defaultdict(list)
        for o in objs: by[o.ent()[0]].append(o)
        for ent, os_ in by.items():
            U = unary_union([o.poly for o in os_]); c = U.representative_point(); rep = max(os_, key=lambda o: o.poly.area)
            hits = [surf[j] for j in stree.query(U) if surf[j][2].intersects(U)]
            au.stats[('STATIC', what + '-surface', 'tested')] += 1
            if hits:
                kinds = sorted({h[0] for h in hits}); names = ', '.join(sorted({h[1] for h in hits}))
                # depth: how far inside the surface (centre to its edge), or the overlap's short side when only the
                # footprint's edge reaches onto it
                dep = max(float(h[2].boundary.distance(c)) if h[2].contains(c) else depth_of(h[2].intersection(U)) for h in hits)
                top = max(o.y1 for o in os_) - g
                au.add('STATIC', what + '-on-movement-surface', 'OBSTRUCTION', rep, dict(cat='surface', id='surface:' + '+'.join(kinds), label=names), area=U.area, depth=dep, loc=(c.x, c.y),
                       note=f'{rep.extra.get("elabel", rep.label)} ({top:.1f} m high) stands {dep:.1f} m inside {names}' if any(h[2].contains(c) for h in hits)
                       else f'{rep.extra.get("elabel", rep.label)} ({top:.1f} m high) reaches {dep:.2f} m onto {names}')
            else:
                d = depth_in_paved(c.x, c.y)
                if d > 1.0: au.add('STATIC', what + '-on-physics-pavement', 'WARNING', rep, dict(cat='pavement', id='paved raster', label='paved raster (GroundPhysics-legal ground)'), depth=d, loc=(c.x, c.y),
                                   note=f'{d:.1f} m inside the paved raster GroundPhysics treats as legal aircraft ground (no taxiway/runway polygon there)')
    obstruction(piers, 'pier'); obstruction(signs, 'sign')
    print(f'  STATIC: {len(piers)} pier parts, {len(signs)} signs vs {len(surf)} movement surfaces ({time.time() - t0:.0f} s)')

    # ---------------------------------------------------------------- LIVE
    scen = 'LIVE'; ACS = []; pav = []; markers = []
    for a in S['aircraft']:
        if not a['valid'] or not a['ground']: continue
        geom, W = ac_instance_geom(a)
        if geom is None: markers.append(a); continue
        lbl = f'{a["flight"] or a["hex"]} {a["icao"]}' + (f' at {a["gate"]}' if a['gate'] else '') + f' ({a["phase"]})'
        A = Ac(geom, W, lbl, stand=a['gate'], type_key=a['typeKey']); o = ac_obj(A, oid=a['hex'])
        o.extra.update(hex=a['hex'], phase=a['phase'], gs=a['gs'], phys=a['phys']); ACS.append(o)
        pav.append((o, S['types'][a['typeKey']], W))
    for m in markers:
        au.add(scen, 'marker-no-body', 'WARNING', dict(cat='aircraft', id=m['hex'], label=f'{m["flight"] or m["hex"]} {m["icao"] or "type ?"} ({m["phase"]})', stand=m['gate']), dict(cat='physics', id='-', label='GroundPhysics'), loc=(m['pos'][0], m['pos'][2]), note='drawn as a marker: no model/TYPES entry, so it is not a solid body (ground.js skips it)')
    # aircraft footprints as displayed (plan of the rendered geometry), for other tools
    json.dump([dict(hex=o.id, label=o.label, stand=o.stand, type=o.extra.get('type'), source=o.extra.get('source'), y=[round(o.y0, 2), round(o.y1, 2)],
                    plan=shapely.to_geojson(shapely.set_precision(o.poly, 0.01))) for o in ACS], open(os.path.join(OUT, 'aircraft_footprints.json'), 'w'))
    BRc = bridge_objects('current'); GSE = gse_objects()
    ac_checks(scen, ACS, clearance=False); bridge_vs_ac(scen, BRc, ACS); bridge_vs_bridge(scen, BRc); bridge_vs_static(scen, BRc); pavement(scen, pav)
    au.pairs(scen, 'gse-aircraft', GSE, ACS, maxd=2, warn=0.3)
    au.pairs(scen, 'gse-bridge', GSE, BRc, maxd=2, warn=0.3)
    au.pairs(scen, 'gse-gse', GSE, GSE, same=True, maxd=1, warn=0.2)
    au.pairs(scen, 'gse-building', GSE, buildings + masts + vdgs + signs, maxd=1)
    for o in GSE:
        c = np.array(o.poly.exterior.coords); on = pave(c[:, 0], c[:, 1])
        if not on.all(): au.add(scen, 'gse-off-pavement', 'OFF-PAVEMENT', o, dict(cat='pavement', id='paved raster', label='app paved raster'), loc=tuple(c[~on][0]), note=f'{(~on).sum()} of {len(c)} hull corners unpaved')
    # GSE collision-check rectangles (gates.js placeVehicles ok()) vs the real vehicle meshes
    for i, v in enumerate(S['gse']):
        L, Wd, _ = S['gseCheckDims'][v['kind']]; p = np.array(v['pos']); d = np.array(v['dir']); r = np.array([-d[1], d[0]])
        rect = Polygon([p - d * L / 2 - r * Wd / 2, p + d * L / 2 - r * Wd / 2, p + d * L / 2 + r * Wd / 2, p - d * L / 2 + r * Wd / 2])
        mesh = hull_poly(v['hull']); out = mesh.difference(rect)
        if out.area > 0.5:
            au.add(scen, 'gse-check-mismatch', 'WARNING', dict(cat='gse', id=f'gse{i}:{v["kind"]}', label=f'{v["kind"]} mesh', part=v['kind']), dict(cat='code', id='placeVehicles', label='gates.js placeVehicles() check rectangle'), area=out.area, depth=depth_of(out), loc=tuple(p), note=f'{out.area:.1f} m2 of the {v["kind"]} mesh lies outside the {L} x {Wd} m rectangle the collision check uses')
    print(f'  LIVE: {len(ACS)} solid aircraft, {len(markers)} markers, {len(BRc)} bridge parts, {len(GSE)} GSE ({time.time() - t0:.0f} s)')

    # ---------------------------------------------------------------- REST
    scen = 'REST'; BRr = bridge_objects('rest')
    bridge_vs_bridge(scen, BRr); bridge_vs_static(scen, BRr)
    print(f'  REST ({time.time() - t0:.0f} s)')

    # ---------------------------------------------------------------- DOCK-REF / DOCK-MAX
    for scen, pose, pick in (('DOCK-REF', 'dockRef', lambda st: st['classTypes']['refType']), ('DOCK-MAX', 'dockMax', lambda st: st['classTypes']['maxType'])):
        ACS = []; pav = []
        for st in S['stands']:
            if not st['bridge']: continue
            k = pick(st); A = Ac(type_geom(k), stand_W(st['nose'], st['dir'], S['types'][k]), f'{st["name"]} {k}', stand=st['name'], type_key=k)
            o = ac_obj(A, oid=f'{st["name"]}:{k}'); ACS.append(o); pav.append((o, S['types'][k], A.W))
        BRd = bridge_objects(pose)
        ac_checks(scen, ACS); bridge_vs_ac(scen, BRd, ACS); bridge_vs_bridge(scen, BRd); bridge_vs_static(scen, BRd); pavement(scen, pav)
        print(f'  {scen} ({time.time() - t0:.0f} s)')

    # ---------------------------------------------------------------- ENVELOPE (class-max union of planforms)
    scen = 'ENVELOPE'; env = {}; envAc = {}; pav = []
    for st in S['stands']:
        if not st['bridge']: continue
        ks = st['classTypes']['nonOversize']; acs = []
        for k in ks:
            for rendered in (True, False):
                if not rendered and not (S['typeRender'].get(k) or {}).get('modelKey'): continue
                A = stand_ac(st, k, rendered); acs.append(A)
                if rendered: pav.append((ac_obj(A, oid=f'{st["name"]}:{k}'), S['types'][k], A.W))
        envAc[st['name']] = acs; env[st['name']] = unary_union([a.plan for a in acs])
    envObjs = []
    for n, p in env.items():
        o = Obj('envelope', f'{n}:class-{stands[n]["cls"]}', p, g, g + 20, stand=n, label=f'{n} class {stands[n]["cls"]} envelope'); envObjs.append(o)
    # envelope vs envelope (plan, ICAO clearance)
    def clear(a, b): return max(ICAO[stands[a.stand]['cls']], ICAO[stands[b.stand]['cls']])
    def env_note(a, b, R):
        wa = [x.type for x in envAc[a.stand] if x.plan.intersects(b.poly)]; wb = [x.type for x in envAc[b.stand] if x.plan.intersects(a.poly)]
        return f'{a.stand}: {",".join(sorted(set(wa)))} x {b.stand}: {",".join(sorted(set(wb)))}'
    au.pairs(scen, 'envelope-envelope', envObjs, envObjs, same=True, clear=clear, vert=False, maxd=10, note_fn=env_note)
    # per-type objects for vertical checks against static objects and parked bridges
    typeObjs = [ac_obj(A, oid=A.label) for n in envAc for A in envAc[n]]
    for o in typeObjs: o.cat = 'envelope-type'
    au.pairs(scen, 'envelope-building', typeObjs, buildings, warn=lambda a, b: 3.0 if b.extra.get('kind') not in ('walkway',) else None, maxd=4)
    au.pairs(scen, 'envelope-mast', typeObjs, masts, maxd=2)
    au.pairs(scen, 'envelope-vdgs', typeObjs, vdgs, maxd=1)
    au.pairs(scen, 'envelope-sign', typeObjs, signs, maxd=1)
    # parked (rest) bridges: own stand's (the arriving aircraft) and every other stand's
    au.pairs(scen, 'envelope-rest-bridge', typeObjs, BRr, maxd=1)
    pavement(scen, pav)
    print(f'  ENVELOPE: {len(envObjs)} stands, {len(typeObjs)} type placements ({time.time() - t0:.0f} s)')

    # ---------------------------------------------------------------- OVERSIZE
    scen = 'OVERSIZE'
    for st in S['stands']:
        if not st['bridge']: continue
        for k in st['classTypes']['oversize']:
            A = stand_ac(st, k, True); o = ac_obj(A, oid=f'{st["name"]}:{k}')
            T = S['types'][k]
            for o2 in envObjs:
                if o2.stand == st['name']: continue
                d = o.poly.distance(o2.poly); s2 = stands[o2.stand]
                need = max(ICAO[T_CODE(T)], ICAO[s2['cls']])
                if d >= need: continue
                dn = math.hypot(st['nose'][0] - s2['nose'][0], st['nose'][1] - s2['nose'][1])
                blocked = dn < 0.5 * (st['maxSpan'] + s2['maxSpan']) + 8
                p1, p2 = shapely.ops.nearest_points(o.poly, o2.poly); loc = ((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)
                if not blocked:
                    au.add(scen, 'oversize-not-blocked', 'COLLISION' if d <= 0 else 'CLEARANCE', o, o2, dist=d, loc=loc, note=f'{k} ({T["wing"]["span"]:.1f} m span) at {st["name"]} reaches {o2.stand} (nose distance {dn:.1f} m >= block radius {0.5 * (st["maxSpan"] + s2["maxSpan"]) + 8:.1f} m): {o2.stand} stays available')
                else: au.stats[(scen, 'oversize-blocked-ok', 'tested')] += 1
            # neighbours' parked bridges stay out while blocked
            for b in BRr:
                if b.stand == st['name'] or not o.poly.intersects(b.poly): continue
                R = o.poly.intersection(b.poly); col, vg = vertical(o, b, R)
                if col: au.add(scen, 'oversize-rest-bridge', 'COLLISION', o, b, dist=0, area=R.area, depth=depth_of(R), vgap=vg, loc=R.representative_point().coords[0], note=f'{k} at {st["name"]} hits the parked bridge of {b.stand}')
            for b in buildings:
                if o.poly.distance(b.poly) > 0: continue
                R = o.poly.intersection(b.poly); col, vg = vertical(o, b, R)
                if col: au.add(scen, 'oversize-building', 'COLLISION', o, b, dist=0, area=R.area, depth=depth_of(R), vgap=vg, loc=R.representative_point().coords[0])
    print(f'  OVERSIZE ({time.time() - t0:.0f} s)')

    # ---------------------------------------------------------------- bridge kinematics (rest vs docked geometry)
    for bi, b in enumerate(S['bridges']):
        R, Dk = b['poses']['rest'], b['poses'].get('dockMax')
        if not Dk or not Dk['docks']: continue
        def seclen(P, name):
            p = next((q for q in P['parts'] if q['part'] == name), None)
            if not p: return None
            h = np.array(p['hull']); r = Polygon(h).minimum_rotated_rectangle; c = np.array(r.exterior.coords)
            return float(max(np.linalg.norm(c[1] - c[0]), np.linalg.norm(c[2] - c[1])))
        l0 = [seclen(R, 'tunnel%d' % i) for i in (1, 2, 3)]; l1 = [seclen(Dk, 'tunnel%d' % i) for i in (1, 2, 3)]
        if None in l0 or None in l1: continue
        ch = max(abs(x - y) / max(x, 0.1) for x, y in zip(l0, l1))
        st = stands[b['stand']]
        ref = dict(cat='bridge', id=f'bridge:{bi}', stand=b['stand'], label=f'{b["stand"]} bridge {b["gate"]} (L{b["door"]})')
        if ch > 0.1:
            au.add('KINEMATICS', 'tunnel-stretch', 'WARNING', ref, dict(cat='code', id='gates.js bridgeGeo', label='gates.js bridgeGeo() tunnel sections'), loc=b['rc'],
                   note=f'tunnel sections {"/".join(f"{x:.1f}" for x in l0)} m parked -> {"/".join(f"{x:.1f}" for x in l1)} m docked to {Dk["type"]}: sections scale with the extension instead of telescoping')
        # slope of the docked tunnel floor (rotunda floor -> door sill)
        cab = np.array(Dk['pose']['cab']); rc = np.array(Dk['pose']['rc']); fl = Dk['pose']['floorY']
        run = math.hypot(cab[0] - rc[0], cab[2] - rc[1]); drop = fl - cab[1]
        if run > 1 and abs(drop) / run > 1 / 12:
            au.add('KINEMATICS', 'tunnel-slope', 'WARNING', ref, dict(cat='rule', id='1:12', label='PBB slope limit 1:12 (ADA / ABA 410.1)'), loc=b['rc'],
                   note=f'docked to {Dk["type"]}: floor {fl - g:.1f} m at the rotunda -> {cab[1] - g:.1f} m at the cab over {run:.1f} m = 1:{run / max(abs(drop), 1e-3):.1f}')
    raw = au.items
    per_scen = collections.Counter(f'{x["scenario"]}|{x["severity"]}' for x in raw)
    au.meta = dict(seconds=time.time() - t0, tested={f'{k[0]}|{k[1]}': v for k, v in au.stats.items()}, per_scenario=dict(per_scen),
                   per_scenario_note='counts of the UNMERGED records: one per (scenario, kind, object pair) at that scenario\'s own severity', netcheck=netcheck,
                   provenance=provenance())
    items = merge_scenarios(raw)
    items.sort(key=lambda x: (SEV[x['severity']], -(x['depth'] or 0), -(x['area'] or 0), x['dist'] if x['dist'] is not None else 0))
    for i, x in enumerate(items): x['n'] = i + 1
    envj = {n: shapely.to_geojson(shapely.set_precision(p, 0.01)) for n, p in env.items()}
    json.dump(dict(meta=au.meta, conflicts=items, envelopes=envj), open(os.path.join(OUT, 'audit.json'), 'w'), indent=0)
    for k in sorted(per_scen): print('   ', k, per_scen[k])
    return au


def merge_scenarios(items):
    """one record per (kind, entity pair) - the same parked bridge collides in LIVE and REST alike - keeping the worst
    record, with scenarios = {scenario: that scenario's own severity} (a pair that only warns in LIVE is not listed as
    a LIVE collision)"""
    best = {}
    w = lambda x: (SEV[x['severity']], -(x['depth'] or 0), -(x['area'] or 0))
    for r in items:
        key = (r['kind'], r['a']['ent'], r['b']['ent'])
        o = best.get(key)
        if o is None: r = dict(r); r['scenarios'] = {r['scenario']: r['severity']}; best[key] = r; continue
        sc = dict(o['scenarios']); prev = sc.get(r['scenario'])
        if prev is None or SEV[r['severity']] < SEV[prev]: sc[r['scenario']] = r['severity']
        if w(r) < w(o): r = dict(r); r['scenarios'] = sc; best[key] = r
        else: o['scenarios'] = sc
    return list(best.values())


def scen_label(c):
    """'LIVE, REST (W)' style: scenarios at the record's severity first, others with their own severity initial"""
    sc = c.get('scenarios') or {c['scenario']: c['severity']}
    if isinstance(sc, list): sc = {k: c['severity'] for k in sc}
    same = [k for k, v in sorted(sc.items()) if v == c['severity']]; other = [f'{k} ({v[0]})' for k, v in sorted(sc.items()) if v != c['severity']]
    return ', '.join(same + other)


class PaveMask16(PaveMask):
    def __init__(self):
        import cv2
        S = scene(); r = S['rasters']['pave_1.60']; A = S['meta']['aptRect']
        im = cv2.imread(os.path.join(OUT, r['file']), cv2.IMREAD_COLOR)
        self.pave = im[:, :, 2] > 127; self.res = r['res']; self.s0 = A['s0']; self.t0 = A['t0']; self.h = A['h']


if __name__ == '__main__':
    run()
