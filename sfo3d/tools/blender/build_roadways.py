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
from shapely.geometry import LineString, Polygon, MultiPolygon, MultiPoint, Point, box
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


BLEND = 8.0               # m: the width over which two touching decks meet halfway (close-out r4) [inf]
BLEND_DH = 0.6            # m: their step where they touch is taken out in full up to this; beyond it the correction falls off at
                          # the rate the step grows (fix round 2: phi(r) = 2 x BLEND_DH - r, none from 2 x BLEND_DH = 1.2 m) [inf]


def hp_ext(p, xz, ext=BLEND, run=4.0):
    """hp, but beyond either end of the centreline extrapolated with the profile's end slope (over its last `run` m; up
    to `ext` m out) instead of clamped at the end level: the level a neighbour's deck would have there if it went on
    (fix round 2: the blend compared decks with a clamped neighbour beyond its end - a ramp starting beside a deck's end
    pulled that deck towards the ramp's start level, a grade spike of 14.4 % at (-1546.5, 471.5) in dev build e0)"""
    xz = np.asarray(xz, float); pts = shapely.points(xz); Ln = p['line'].length
    s = shapely.line_locate_point(p['line'], pts); h = np.interp(s, p['s'], p['h'])
    if Ln < 1.0: return h
    r = min(run, Ln)
    for (E, t), at_end in zip(_ends(p), (False, True)):
        m = (s >= Ln - 1e-6) if at_end else (s <= 1e-6)
        if not m.any(): continue
        d = np.clip((xz[m] - E) @ t, 0.0, ext)
        g = (np.interp(Ln, p['s'], p['h']) - np.interp(Ln - r, p['s'], p['h'])) / r if at_end else (np.interp(0.0, p['s'], p['h']) - np.interp(r, p['s'], p['h'])) / r
        h[m] = h[m] + g * d
    return h


def _ends(p):
    """the two centreline ends of piece p: (end point, outward unit direction)"""
    e = p.get('_ends')
    if e is None:
        c = np.array(p['line'].coords); e = []
        for a, b in ((c[1], c[0]), (c[-2], c[-1])):
            t = b - a; e.append((b, t / max(np.linalg.norm(t), 1e-9)))
        p['_ends'] = e
    return e


def continuation(p, q):
    """the joint where p and q continue each other end to end (centreline ends within JOINT_TOL, outward directions opposed:
    a bend < 60 deg, as joint_wedges), or None"""
    if p['src'] not in ('deck', 'ramp') or q['src'] not in ('deck', 'ramp'): return None
    for Np, tp in _ends(p):
        for Nq, tq in _ends(q):
            if np.linalg.norm(Np - Nq) <= JOINT_TOL and float(np.dot(tp, tq)) <= -0.5: return Np
    return None


def blend_neighbours(P, log):
    """close-out round 4 (the verifier's unguarded 0.44-0.63 m step between two decks of interchange_2_2, and the steps at
    junctions in general): each piece's level is its own centreline's profile projected sideways (hp), so two ways that
    meet at a shared OSM node and run side by side (merges, diverges, junction pieces) disagree along their common edge by
    their grades x the distance from the node (r22: ~2,000 m of shared edge with 0.02-1 m between the two tops, ~880 m of
    it over 0.3 m). Such pairs now meet halfway: hb() moves each towards the other over BLEND metres, so their tops agree
    on the common edge (the verifier's 'equalise the two profiles where the ribbons touch').
    Fix round 2 (verifier ver1, major: the round-4 blend made a grade wave at every joint, mesh max 13.4 -> 14.8 %, ITB
    area > 10 % 0 -> 115 m2):
    - NOT two ways that continue each other end to end (continuation(); 90 of the 140 pairs of round 4). They meet at the
      shared node's level already (both caps are square to their centrelines there), and beyond the neighbour's end hp()
      clamps to the node level, so the blend pulled every deck within 8 m of every joint towards the node level by up to
      (1 - d/8) x grade x d / 2. A continuation pair is kept only if it also touches farther than its half width + 3 m
      from the joint (none);
    - the neighbour's level beyond its own ends is extrapolated with its end slope (hp_ext), not clamped;
    - the correction falls off beyond BLEND_DH at the rate the step grows (phi, slope -1), not by a linear weight on the
      step (round 4: (1.0 - r) / 0.4 x r, whose slope reaches -2.5: a deck beside one at a different grade dipped or rose
      by up to 1.25 x the grade difference where the step grew through 0.6-1.0 m - 13.7 % at (-1577.4, 492.2) and 10.0 %
      on the ITB loop in dev build e1);
    - decks that share no OSM node are not blended (tried in dev build e1 for the 0.02-0.30 m step faces: it moved no
      step out of 0.05-0.30 m and raised the mesh maximum to 13.7 %).
    Offline on the e1 pieces (f2/blendlab.py): mesh max 13.37 %, area > 10 % 784 m2 = no blend at all, ITB > 10 % 0 m2;
    contact edge with a 0.05-0.30 m step 648 m without a blend -> 172 m"""
    n = nc = 0; kept_c = []
    for p in P:
        p['blend_nbrs'] = []
    for i, p in enumerate(P):
        if p['geom'].is_empty: continue
        for q in P[i + 1:]:
            if q['geom'].is_empty or q['geom'].distance(p['geom']) > 0.2 or not connected(p, q): continue
            J = continuation(p, q)
            if J is not None:
                C = p['geom'].buffer(0.25).intersection(q['geom'].buffer(0.25))
                if C.is_empty or C.hausdorff_distance(Point(*J)) <= max(p['half'], q['half']) + 3.0:
                    nc += 1; continue
                kept_c.append((p['id'], q['id']))
            p['blend_nbrs'].append(q); q['blend_nbrs'].append(p); n += 1
    log('connected decks blended side by side (close-out r4 fix round 2; BLEND %.0f m, steps taken out in full up to %.1f m, none from %.1f m): %d pairs; '
        'end-to-end continuations not blended: %d; kept (also side by side): %s' % (BLEND, BLEND_DH, 2 * BLEND_DH, n, nc, kept_c or 'none'))
    return dict(pairs=n, continuations_not_blended=nc, continuations_kept=kept_c, rule='connected (shared OSM node), touching, not end to end; '
                'each moves w x phi(step) / 2, w = 1 - d / %.0f m, phi(r) = r up to %.1f m, 2 x %.1f - r beyond, 0 from %.1f m; neighbour extrapolated beyond its ends' % (BLEND, BLEND_DH, BLEND_DH, 2 * BLEND_DH))


def hb(p, xz):
    """deck-top level of piece p at plan points xz as built: hp, met halfway by each blended neighbour q within BLEND m:
    + w x phi(raw) / 2 with raw = hp_ext(q) - hp(p), w = 1 - distance to q's deck / BLEND, phi(r) = r for |r| <= BLEND_DH,
    sign(r) (2 BLEND_DH - |r|) up to 2 BLEND_DH, 0 beyond.
    Close-out round 5 note (integration verifier, wedge creases): a joint wedge keeps this level, the clamped node level
    beyond its owner's centreline end. Both caps it fills between are at the node level along their whole width (hp depends
    on the station only), so the flat wedge is the exact C0 fill; the 6.4-deg fold where it meets an 11.2 % ramp is the
    ramp's own grade. Dev build c5/g1 tried the two decks' end-slope extrapolations, weighted by distance (no step at
    either cap): folds > 6 deg 6 -> 17 and 0.002-m2 slivers at 79 % - reverted; removing the fold needs a warped junction
    surface (open item)"""
    xz = np.asarray(xz, float); h = hp(p, xz)
    if not p.get('blend_nbrs') or not len(xz): return h
    pts = shapely.points(xz); dh = np.zeros(len(xz))
    for q in p['blend_nbrs']:
        w = np.clip(1.0 - shapely.distance(q['geom'], pts) / BLEND, 0.0, 1.0)
        if not (w > 0).any(): continue
        raw = hp_ext(q, xz) - h; r = np.abs(raw)
        phi = np.where(r <= BLEND_DH, r, np.clip(2 * BLEND_DH - r, 0.0, None)) * np.sign(raw)
        dh += w * phi / 2
    return h + dh


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
ASSET_BUF = 0.10      # m: a deck stops this far short of an asset's occupancy (trim)
ASSET_BUF_DOM = 0.02  # m: ... of the domestic group's (the T2 curb sidewalk's kerb face; buildings R3.12) [inf]
# close-out round 3 (integration-2): the outer light-concrete band along the ITB (OSM 41015123 / 739695588) is a LOWER level
# than the departures plate [obs: photo i1 (Kulikovsky 2007, CC BY 3.0, refs/cache/buildings/review_likeness/i1.jpg), the
# ITB frontage seen from the west: the departures deck ends in a planter of pink-flowering shrubs on its fascia, and in front
# of it and below it runs a lower level with trees in planters on its outer edge, shelters and pedestrians, which continues
# under the departures deck; NAIP 2024: the pink line (R - G peak) between the bus roadway and the band is that planter, not
# a painted kerb]. Its level along the straight is LEVEL in i1 (the lower coping is horizontal within ~1 px over 0.9 km of
# image width), so it is held at one level there (a plate), not solved: LOWER_H = the lowest level that clears the at-grade
# roads beneath it (OSM 256787738 / 370279550 / 370279603 / 370279607, tunnel=building_passage, pass under it) by
# CLEAR_MIN + DECK_DEPTH [inf]. i1 (scale 9.0 px/m at the deck edge from the planter's NAIP length 104 m = 935 px) gives a
# coping-to-coping step of ~6.7 m (6.1-7.3), more than the 5.6 m modelled: with this lower level the L3 deck would be ~1 m
# higher than spec_itb level3.floor 11.5 [inf, +-1.5] - left to the ITB group (manifest.json#roadways.unknown)
LOWER_H = RN.DECK_DEPTH + RN.CLEAR_MIN
WALK_UNDER = 3.0      # m: the lower level's sidewalk continues this far under the plate's edge (i1: pedestrians and shelters
                      # under the deck) [inf width] - closes the slit. Fix 2 (verifier v4): OSM footway 1164416297 (layer 1, bridge)
                      # runs at v ~ -48 over u -86..86, i.e. under island A, ~16 m inside the plate edge (v -64.3), not along the edge:
                      # it argues for a lower level that runs much further under the deck than modelled (manifest#roadways.unknown)
WALK_KERB = 0.15      # sidewalk above the lower roadway [inf, as KERB_M]
PLANTER_H = 0.95      # the deck-edge planter (island B) above the deck: its planting shows over the 0.85-m parapet, as in
                      # i1 [inf height; obs extent: NAIP 2024 R - G band, i1]


MIN_LANE_W = 3.0      # m: a stacked cut may not leave less than lanes x MIN_LANE_W of carriageway (+ a SHOULDER each side for the
                      # parapets), nor split the lower deck (close-out r3 fix 2, verifier v1: "refuse a cut that leaves less than lanes x
                      # 3.0 m of carriageway, and report it as a conflict instead") [inf]
KEEP_CLEAR = 3.5      # m: such a cut is refused (the lower deck kept whole under the upper one, a low-clearance conflict reported)
                      # only while the clearance kept is at least this; below it the two decks would clash, so the cut stands and the
                      # narrowed deck is reported instead [inf: posted low clearances of ~3.5 m (11.5 ft) carry general traffic]


def polys_of(g):
    return [y for y in (getattr(g, 'geoms', None) or [g]) if isinstance(y, Polygon) and y.area > 0.5]


def deck_widths(p, geom, s0, s1, step=1.0):
    """the built width across piece p's centreline at stations s0..s1: the part of the cross-section through `geom` that
    contains, or is nearest to, the centreline point"""
    L = p['line'].length; out = []
    for s in np.arange(max(0.0, s0), min(L, s1) + 1e-6, step):
        q = p['line'].interpolate(s); q2 = p['line'].interpolate(min(L, s + 0.5)); q1 = p['line'].interpolate(max(0.0, s - 0.5))
        t = np.array([q2.x - q1.x, q2.y - q1.y]); t /= max(np.linalg.norm(t), 1e-9); n = np.array([-t[1], t[0]]) * (p['half'] + 3.0)
        cs = LineString([(q.x - n[0], q.y - n[1]), (q.x + n[0], q.y + n[1])]).intersection(geom)
        segs = [y for y in (getattr(cs, 'geoms', None) or [cs]) if not y.is_empty and y.geom_type == 'LineString']
        out.append((float(s), min(segs, key=lambda y: y.distance(q)).length if segs else 0.0))
    return out


def stacked_cut(lo, up, geo, up_geo, X, bad, sep_min, rule):
    """the stacked cut (review round 2; close-out round 3 fix 2, verifier v1 - the round-3 partial cut removed 1-m cells + a
    round buffer: a scalloped deck edge with a wavy parapet, the carriageway of OSM 739695588 down to 3.5 m). The lower deck
    `lo` (geometry `geo`; the upper's `up_geo`) gives up the components of the ribbons' overlap X that hold a sample with less
    than deck + clearance (`bad`; rule 'median': the whole overlap, as in review round 2), grown by STACK_GAP: its new edge
    runs along the upper deck's edge at STACK_GAP, a smooth line, and the parapet is built on it. If that splits the lower
    deck or leaves less than lanes x MIN_LANE_W of carriageway (+ shoulders) where it was wider, the cut is refused while the
    clearance kept (sep_min - DECK_DEPTH) is >= KEEP_CLEAR (a low-clearance conflict, reported), else made and the narrowed
    deck reported. Returns (new geometry, or None when refused / nothing to cut; record or None)."""
    if rule == 'median': U = X
    else:
        comps = [c for c in polys_of(X) if shapely.contains_xy(c.buffer(0.3), bad[:, 0], bad[:, 1]).any()]
        if not comps: return None, None
        U = unary_union(comps)
    R = unary_union([U, up_geo.intersection(U.buffer(STACK_GAP + 0.5))]).buffer(STACK_GAP, join_style='mitre', mitre_limit=2.0).simplify(0.05)
    new = geo.difference(R)
    sR = shapely.line_locate_point(lo['line'], shapely.points(shapely.get_coordinates(R)))
    W0 = dict(deck_widths(lo, geo, sR.min() - 1.0, sR.max() + 1.0)); W1 = deck_widths(lo, new, sR.min() - 1.0, sR.max() + 1.0)
    need = lo['lanes'] * MIN_LANE_W + 2 * SHOULDER
    narrow = [(s, w) for s, w in W1 if w < need - 1e-3 and w < W0.get(s, 0.0) - 0.05]
    split = len(polys_of(new)) > len(polys_of(geo)) or sum(len(y.interiors) for y in polys_of(new)) > sum(len(y.interiors) for y in polys_of(geo))
    keep = round(sep_min - RN.DECK_DEPTH, 2)
    rec = dict(lower=lo['id'], upper=up['id'], rule=rule, cut_m2=round(geo.area - new.area, 1), min_width_m=round(min((w for s, w in W1), default=0.0), 2), need_m=round(need, 2),
               clearance_if_kept_m=keep, at=[round(c, 1) for c in U.representative_point().coords[0]])
    if split or narrow:
        why = 'split' if split else 'carriageway %.2f m < %d x %.1f m (+ shoulders) over %d m' % (min(w for s, w in narrow), lo['lanes'], MIN_LANE_W, len(narrow))
        if keep >= KEEP_CLEAR:
            rec['refused'] = why; return None, rec
        rec['narrowed'] = why + ' (kept: the decks would clash, %.2f m)' % keep
    lo.setdefault('stack_cut_R', []).append(R)   # close-out r4: the joint wedges never re-fill a stacked cut
    return new, rec


def prio_key(p):
    """which of two pieces keeps a shared place: anchored > deck (not ramp) > wider > OSM id order"""
    return (p['anchor'] is None, p['src'] == 'ramp', -p['w'], isinstance(p['id'], str), p['id'] if not isinstance(p['id'], str) else 0, str(p['id']))


def _polys(g):
    """the polygons of any geometry (collections and multi-parts flattened)"""
    if g is None or g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    return [x for y in getattr(g, 'geoms', []) for x in _polys(y)]


def merge_into(p, g):
    """add region g to piece p's deck, closing hairline seams (< 4 cm) between them: a wedge / fill / taper computed as the
    difference of the decks can touch its owner along a numerically split edge and stay a separate polygon, whose side
    against the owner then read as an outer edge (a parapet across the lane, close-out r4 dev build d1). The close uses
    round joins and is checked: GEOS's mitre negative buffer returned invalid or EMPTY results on near-degenerate unions
    (dev build d9 lost two whole decks, 41015044 and 905752945), so a result that is invalid or smaller than the plain
    union falls back to the (validated) union"""
    u = unary_union([p['geom'], g])
    c = u.buffer(0.02, join_style='round', quad_segs=2).buffer(-0.02, join_style='round', quad_segs=2)
    if c.is_empty or not c.is_valid or c.area < u.area - max(0.05, 0.002 * u.area):
        c = shapely.make_valid(u)
    new = unary_union([x for x in _polys(c) if x.area > 0.05])
    if new.area < p['geom'].area - 0.05:   # never lose deck (self-check)
        raise RuntimeError('merge_into lost deck area on %s: %.2f -> %.2f m2' % (p['id'], p['geom'].area, new.area))
    p['geom'] = new


JOINT_TOL = 0.5       # m: two pieces' centreline ends this close (and level within 0.1 m) are an end-to-end joint (a shared OSM node)
TAPER_K, TAPER_MAX = 8.0, 15.0   # a width step at a joint tapers over TAPER_K x the step (max TAPER_MAX m) [inf: of the order of the
                                 # MUTCD lane-reduction taper for low speeds (L = W S^2 / 60 ft, S <= 40 mph; ~10:1 at 25 mph),
                                 # recalled, not re-checked; no drawings of these decks]


def joint_wedges(P, occ, log):
    """close-out round 4 (verifier's major on fix 2: parapet 'fingers' 0.4 m wide, 0.85 m tall, 1-2.7 m long standing in
    the driving lane). Root cause: every ribbon ends in a flat cap square to its own centreline, so where two ways continue
    each other at a shared OSM node with a bend, the two caps leave a wedge open to grade on the outside of the bend (r22:
    100 of 105 joints, up to 4.9 m2, mouths of ~0.05-1.4 m; the inside of the bend overlaps and goes to one piece). The
    wedge's sides run along the caps, ACROSS the lanes; since fix 2's 0.5-m edge sampling they were outer edges and got
    parapets (r18 broke the parapet there instead: an opening). The wedge is deck: the convex hull of the two caps, less
    both decks, less any other piece within the stacking band (same level: itself + 0.02 m; less than deck + clearance
    apart: + STACK_GAP, as a stacked cut), less what the trim took from either (stacked cuts) and less the assets'
    occupancy in its band (occ: as trim(), ASSET_BUF / ASSET_BUF_DOM). It joins the piece of higher priority; its level is
    the joint's (both caps are square to their centrelines at the shared node, so hp() clamps to the node's level there).
    Its outer side is the chord between the two decks' outer corners, which carries the parapet across the joint."""
    SEP = RN.DECK_DEPTH + RN.CLEAR_MIN
    ends = []
    for p in P:
        if p['src'] not in ('deck', 'ramp') or p['geom'].is_empty: continue
        c = np.array(p['line'].coords)
        for a, b in ((c[1], c[0]), (c[-2], c[-1])):
            t = b - a; t = t / max(np.linalg.norm(t), 1e-9); nrm = np.array([-t[1], t[0]]) * p['half']
            ends.append((p, b, t, [tuple(b - nrm), tuple(b + nrm)]))
    tree = shapely.STRtree([q['geom'] for q in P])
    n_j = 0; added = []
    for i in range(len(ends)):
        p, Np, tp, Cp = ends[i]
        for j in range(i + 1, len(ends)):
            q, Nq, tq, Cq = ends[j]
            # a continuation: the two outward directions at the node roughly opposite (a bend < 60 deg; not a diverge)
            if q is p or np.linalg.norm(Np - Nq) > JOINT_TOL or float(np.dot(tp, tq)) > -0.5: continue
            h0 = float(hp(p, Np[None])[0])
            if abs(float(hp(q, Nq[None])[0]) - h0) > 0.1: continue
            n_j += 1
            H = MultiPoint(Cp + Cq).convex_hull
            if H.area < 1e-3: continue
            Wd = H.difference(p['geom']).difference(q['geom'])
            if Wd.is_empty or Wd.area < 1e-3: continue
            cut = [g for g in p.get('stack_cut_R', []) + q.get('stack_cut_R', [])]
            pts = np.concatenate([shapely.get_coordinates(Wd), np.array([[Np[0], Np[1]]])])
            for k in tree.query(H.buffer(STACK_GAP)):
                r = P[k]
                if r is p or r is q or r['geom'].is_empty: continue
                dh = float(np.abs(hp(r, pts) - h0).min())
                if dh < 1.0: cut.append(r['geom'].buffer(0.02))
                elif dh < SEP: cut.append(r['geom'].buffer(STACK_GAP))
            y0 = GROUND_Y + h0 - (RN.DECK_DEPTH if h0 >= FILL_H else h0) - 0.1; y1 = GROUND_Y + h0 + PARAPET_H + 0.2
            o = occ(H, y0, y1)
            if not o.is_empty: cut.append(o)
            if cut: Wd = Wd.difference(unary_union(cut))
            keep = [c for c in (getattr(Wd, 'geoms', None) or [Wd]) if isinstance(c, Polygon) and c.area > 2e-3
                    and c.distance(p['geom']) < 0.03 and c.distance(q['geom']) < 0.03]
            if not keep: continue
            Wd = unary_union(keep); own, oth = (p, q) if prio_key(p) <= prio_key(q) else (q, p)
            merge_into(own, Wd)
            own.setdefault('joint_wedge_m2', 0.0); own['joint_wedge_m2'] += Wd.area
            added.append(dict(owner=own['id'], other=oth['id'], at=[round(float(Np[0]), 1), round(float(Np[1]), 1)], area_m2=round(Wd.area, 2),
                              bend_deg=round(float(np.degrees(np.arccos(np.clip(-np.dot(tp, tq), -1, 1)))), 1), level_m=round(h0, 2)))
    log('joint wedges (close-out r4: the flat caps of two ways that continue each other at a shared node leave a wedge on the outside of a bend; '
        'filled as deck so no parapet runs across the lanes): %d joints, %d wedges filled (%.1f m2; largest %s)'
        % (n_j, len(added), sum(a['area_m2'] for a in added), max(added, key=lambda a: a['area_m2']) if added else None))
    # width steps: where a wider way continues into a narrower one, the wider deck's flat cap stood square across the
    # narrower deck's outer lanes beyond its edge, a parapet across a lane that ends (the verifier's T2
    # curb site at (-780.4, 329.9)). A taper on each side, alongside the narrower deck, from the wider deck's corner to the
    # narrower deck's edge TAPER_K x the width step further on, joins the narrower piece (its own level there)
    nt = 0; ta = 0.0
    for i in range(len(ends)):
        p, Np, tp, Cp = ends[i]
        for j in range(len(ends)):
            q, Nq, tq, Cq = ends[j]
            if q is p or np.linalg.norm(Np - Nq) > JOINT_TOL or float(np.dot(tp, tq)) > -0.5 or p['half'] - q['half'] < 0.25: continue
            if abs(float(hp(q, Nq[None])[0]) - float(hp(p, Np[None])[0])) > 0.1: continue
            # a plain continuation only: no third piece ends at the node (a diverge / merge has its own gore)
            if sum(1 for e in ends if np.linalg.norm(e[1] - Np) <= JOINT_TOL) != 2: continue
            Lt = min(TAPER_K * (p['half'] - q['half']), TAPER_MAX, 0.8 * q['line'].length)
            if Lt < 1.0: continue
            sq = Lt if np.linalg.norm(np.array(q['line'].coords[0]) - Nq) < np.linalg.norm(np.array(q['line'].coords[-1]) - Nq) else q['line'].length - Lt   # Lt from the joint
            Qp = np.array(q['line'].interpolate(sq).coords[0]); Q1 = np.array(q['line'].interpolate(min(q['line'].length, sq + 0.5)).coords[0]); Q0 = np.array(q['line'].interpolate(max(0.0, sq - 0.5)).coords[0])
            tt = (Q1 - Q0) / max(np.linalg.norm(Q1 - Q0), 1e-9); nn = np.array([-tt[1], tt[0]]) * q['half']
            for Cw in (np.array(Cp[0]), np.array(Cp[1])):
                # the wider deck's corner must still stand there, out in the open (not trimmed, not against another piece)
                if p['geom'].distance(Point(*Cw)) > 0.1 or any(r is not p and r is not q and not r['geom'].is_empty and r['geom'].distance(Point(*Cw)) < 1.0 for r in P): continue
                Cn = min((np.array(Cq[0]), np.array(Cq[1])), key=lambda c: np.linalg.norm(c - Cw))
                Pn = min((Qp + nn, Qp - nn), key=lambda c: np.linalg.norm(c - Cn))
                T0 = Polygon([tuple(Cw), tuple(Cn), tuple(Pn)])
                if not T0.is_valid or T0.area < 0.05: continue
                # the chord Cn - Pn misses the narrower deck's edge where its centreline curves: the hull with the deck's edge
                # strip closes that crack (a slit inside the deck, d4 at the T2 curb)
                T0 = unary_union([T0, q['geom'].intersection(T0.buffer(0.5))]).convex_hull
                T = T0.difference(p['geom']).difference(q['geom'])
                if T.is_empty or T.area < 0.05 or T.area < 0.5 * T0.area: continue
                h0 = float(hp(q, Nq[None])[0]); X = np.concatenate([shapely.get_coordinates(T), [Nq]])
                cut = list(p.get('stack_cut_R', [])) + list(q.get('stack_cut_R', []))
                for k in tree.query(T.buffer(STACK_GAP)):
                    r = P[k]
                    if r is p or r is q or r['geom'].is_empty: continue
                    dh = float(np.abs(hp(r, X) - h0).min())
                    if dh < 1.0: cut.append(r['geom'].buffer(0.02))
                    elif dh < SEP: cut.append(r['geom'].buffer(STACK_GAP))
                o = occ(T, GROUND_Y + h0 - (RN.DECK_DEPTH if h0 >= FILL_H else h0) - 0.1, GROUND_Y + h0 + PARAPET_H + 0.2)
                if not o.is_empty: cut.append(o)
                if cut: T = T.difference(unary_union(cut))
                comps = [c for c in (getattr(T, 'geoms', None) or [T]) if isinstance(c, Polygon) and c.area > 0.05 and c.distance(q['geom']) < 0.03]
                if not comps or sum(c.area for c in comps) < 0.9 * T.area: continue   # something else stands there: no taper
                T = unary_union(comps); merge_into(q, T); nt += 1; ta += T.area
                added.append(dict(owner=q['id'], other=p['id'], at=[round(float(Nq[0]), 1), round(float(Nq[1]), 1)], area_m2=round(T.area, 2), taper_m=round(Lt, 1), level_m=round(h0, 2)))
    log('width tapers at joints (close-out r4: wider into narrower, %.0f:1 [inf]): %d sides, %.1f m2' % (TAPER_K, nt, ta))
    wd = [a for a in added if 'taper_m' not in a]
    return dict(joints=n_j, filled=len(wd), area_m2=round(sum(a['area_m2'] for a in wd), 1), largest=sorted(wd, key=lambda a: -a['area_m2'])[:10],
                tapers=nt, taper_m2=round(ta, 1), taper_largest=sorted([a for a in added if 'taper_m' in a], key=lambda a: -a['area_m2'])[:10])


VOID_MAX = 5.0        # m2: an enclosed void between decks at one level up to this size is paved (a junction's leftover) [inf]
SLIT_DH = 1.0         # m: a slit / void between connected decks is filled where their raw levels differ by less than this (the
                      # round-4 blend's upper limit; unchanged in fix round 2) [inf]
SLIT_R = 0.5          # m: slits narrower than 2 x SLIT_R between connected decks at one level are paved (gore noses start
                      # where the two decks are 1 m apart: room for the two 0.4-m barriers) [inf]


def connected(p, q):
    """two pieces share an OSM node (one junction / merge / diverge; ramp pieces carry their whole way's nodes)"""
    a = p.get('_nd')
    if a is None: a = p['_nd'] = {x for x in p.get('nodes', []) if not isinstance(x, tuple)}
    b = q.get('_nd')
    if b is None: b = q['_nd'] = {x for x in q.get('nodes', []) if not isinstance(x, tuple)}
    return bool(a & b)


def slit_fill(P, occ, log):
    """close-out round 4 (with joint_wedges): the slits between two connected decks (a shared OSM node) whose ribbons part at a
    small angle - the gore of a diverge or merge, the inside of a bend - are deck while narrower than 2 x SLIT_R: the
    morphological close (mitre) of the two decks, less both, kept within SLIT_R of each; less any other piece in the stacking
    band, the stacked cuts and the assets' occupancy (as joint_wedges); and only where the two levels (raw, before the
    blend) differ by less than SLIT_DH (2-m slices along the owner's centreline): where the blend leaves more than
    STEP_TOL between them, the filled slit's far side is an edge of both (a median barrier with no gap), else a step face. r22 built a parapet on each side of
    such a slit from where it was 0.08 m wide: two barriers in one carriageway, 0.1-0.6 m apart (the verifier's 0.6 m rule
    counts them). Joins the piece of higher priority."""
    SEP = RN.DECK_DEPTH + RN.CLEAR_MIN
    tree = shapely.STRtree([q['geom'] for q in P]); added = []
    for i, p in enumerate(P):
        if p['src'] not in ('deck', 'ramp', 'plate') or p['geom'].is_empty: continue
        for j in tree.query(p['geom'].buffer(2 * SLIT_R)):
            q = P[j]
            if j <= i or q['src'] not in ('deck', 'ramp', 'plate') or q['geom'].is_empty: continue
            if q['geom'].distance(p['geom']) > 2 * SLIT_R: continue
            # connected decks are blended to one level (hb) where their raw levels differ by < SLIT_DH; two decks that
            # share no node (the gore nose of two ways that part without a common node, a way meeting the ITB plate) only
            # where they are already within STEP_TOL
            lim = SLIT_DH if connected(p, q) else STEP_TOL
            # the slit: the points between the two decks where the gap across (distance to one + to the other) is < 2 x SLIT_R
            # and the two raw levels agree within SLIT_DH, on a 0.1-m grid (a morphological close eroded back from the
            # gore's open mouth and left slivers along one side: dev build d6)
            U = unary_union([p['geom'], q['geom']]); D2 = 2 * SLIT_R
            cand = p['geom'].buffer(D2).intersection(q['geom'].buffer(D2)).difference(U)
            if cand.is_empty or cand.area < 2e-3: continue
            x0, z0, x1, z1 = cand.bounds
            Q = np.array(np.meshgrid(np.arange(x0, x1 + 0.1, 0.1), np.arange(z0, z1 + 0.1, 0.1))).reshape(2, -1).T
            Q = Q[shapely.contains_xy(cand, Q[:, 0], Q[:, 1])]
            if not len(Q): continue
            qp = shapely.points(Q)
            Q = Q[(shapely.distance(p['geom'], qp) + shapely.distance(q['geom'], qp) <= D2 + 0.02) & (np.abs(hp(p, Q) - hp(q, Q)) < lim)]
            if not len(Q): continue
            # between the two: the nearest points on them lie on opposite sides (not the corner outside where two decks meet)
            qp = shapely.points(Q)
            na = shapely.get_coordinates(shapely.shortest_line(p['geom'], qp)).reshape(-1, 2, 2)[:, 0]; nb = shapely.get_coordinates(shapely.shortest_line(q['geom'], qp)).reshape(-1, 2, 2)[:, 0]
            v1 = Q - na; v2 = Q - nb; cs = (v1 * v2).sum(1) / np.maximum(np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1), 1e-9)
            Q = Q[cs < -0.85]
            if not len(Q): continue
            # the raster's 0.1-m steps smoothed (they became stair-stepped parapet runs at a gore mouth: d7), then grown back
            # 0.06 m onto the two decks so it still touches both
            G = unary_union(shapely.box(Q[:, 0] - 0.12, Q[:, 1] - 0.12, Q[:, 0] + 0.12, Q[:, 1] + 0.12)).difference(U).simplify(0.1)
            G = G.buffer(0.06, join_style='mitre', mitre_limit=3.0).difference(U) if not G.is_empty else G
            if G.is_empty or G.area < 2e-3: continue
            own = p if prio_key(p) <= prio_key(q) else q
            keep = [G] if not G.is_empty else []
            if not keep: continue
            G = unary_union(keep); h0 = float(np.median(hp(own, shapely.get_coordinates(G))))
            cut = list(p.get('stack_cut_R', [])) + list(q.get('stack_cut_R', []))
            X = shapely.get_coordinates(G)
            for k in tree.query(G.buffer(STACK_GAP)):
                r = P[k]
                if r is p or r is q or r['geom'].is_empty: continue
                dh = float(np.abs(hp(r, X) - h0).min())
                if dh < 1.0: cut.append(r['geom'].buffer(0.02))
                elif dh < SEP: cut.append(r['geom'].buffer(STACK_GAP))
            o = occ(G, GROUND_Y + h0 - (RN.DECK_DEPTH if h0 >= FILL_H else h0) - 0.1, GROUND_Y + h0 + PARAPET_H + 0.2)
            if not o.is_empty: cut.append(o)
            if cut: G = G.difference(unary_union(cut))
            comps = [c for c in (getattr(G, 'geoms', None) or [G]) if isinstance(c, Polygon) and c.area > 2e-3 and c.distance(p['geom']) < 0.03 and c.distance(q['geom']) < 0.03]
            if not comps: continue
            G = unary_union(comps); merge_into(own, G)
            added.append(dict(owner=own['id'], other=(q if own is p else p)['id'], area_m2=round(G.area, 2), at=[round(c, 1) for c in G.representative_point().coords[0]], level_m=round(h0, 2)))
    log('slit fill (close-out r4: slits < %.1f m between connected decks at one level paved): %d pairs, %.1f m2 (largest %s)'
        % (2 * SLIT_R, len(added), sum(a['area_m2'] for a in added), max(added, key=lambda a: a['area_m2']) if added else None))
    # small voids enclosed by three or more decks at one level (a junction's leftover triangle, d8 at the T2 curb (-803, 326):
    # a parapet round a 1-m2 hole) are deck too, given to the adjacent piece of highest priority
    PU = [q for q in P if q['src'] in ('deck', 'ramp', 'plate') and not q['geom'].is_empty]
    U = unary_union([q['geom'] for q in PU]); voids = []
    for poly in (getattr(U, 'geoms', None) or [U]):
        if not isinstance(poly, Polygon): continue
        for ring in poly.interiors:
            Hh = Polygon(ring)
            if Hh.area > VOID_MAX or Hh.area < 0.05: continue   # hairline holes between decks read as inner edges anyway
            adj = [q for q in PU if q['geom'].distance(Hh) < 0.05]
            X = shapely.get_coordinates(Hh)
            if len(adj) < 2: continue
            hs = np.array([hp(q, X) for q in adj])
            if float((hs.max(0) - hs.min(0)).max()) >= SLIT_DH: continue
            h0 = float(np.median(hs)); G = Hh
            o = occ(G, GROUND_Y + h0 - (RN.DECK_DEPTH if h0 >= FILL_H else h0) - 0.1, GROUND_Y + h0 + PARAPET_H + 0.2)
            if not o.is_empty: G = G.difference(o)
            for r in PU:
                if any(r is a for a in adj) or r['geom'].is_empty or not r['geom'].intersects(G.buffer(STACK_GAP)): continue
                dh = float(np.abs(hp(r, X) - h0).min())
                if dh < RN.DECK_DEPTH + RN.CLEAR_MIN: G = G.difference(r['geom'].buffer(0.02 if dh < 1.0 else STACK_GAP))
            if G.is_empty or G.area < 2e-3: continue
            own = min(adj, key=prio_key); merge_into(own, G)
            voids.append(dict(owner=own['id'], area_m2=round(G.area, 2), at=[round(c, 1) for c in G.representative_point().coords[0]], pieces=len(adj)))
    log('junction voids (< %.0f m2, enclosed by decks at one level) paved: %d, %.1f m2' % (VOID_MAX, len(voids), sum(v['area_m2'] for v in voids)))
    return dict(pairs=len(added), area_m2=round(sum(a['area_m2'] for a in added), 1), largest=sorted(added, key=lambda a: -a['area_m2'])[:10],
                voids=len(voids), voids_m2=round(sum(v['area_m2'] for v in voids), 1), void_list=voids[:20])


def stack_trim(P, log):
    """trim()'s first part: same-level overlaps go to the higher-priority piece; stacked overlaps with less than deck +
    clearance are cut from the lower deck (stacked_cut) or refused and reported. Sets p['geom'] for every piece; returns
    the stacked cut records"""
    SEP = RN.DECK_DEPTH + RN.CLEAR_MIN; recs = []
    order = sorted(range(len(P)), key=lambda i: prio_key(P[i]))
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
            if np.median(dh) < 1.0: g = g.difference(q['geom'].buffer(0.02)); continue
            if 'walk' in (p['src'], q['src']): continue   # a sidewalk under a deck needs headroom, not road clearance (close-out r3)
            # two decks overlapping in plan with less than deck + clearance between them. Review round 2: over most of the
            # overlap (rule 'median': a diverge whose ribbons still overlap where one has begun to climb; the ITB loop's
            # lower outer roadway under its anchored departures leg) - the lower deck gives the overlap up, so the upper
            # deck's edge stands beside it instead of 1-5 m over it (+ STACK_GAP: the upper deck's parapet and soffit edge
            # overhang its ribbon; with 0.05 m, 1.0-1.3 m slivers stayed). Close-out round 3: over part of it (rule
            # 'partial': two ways side by side whose ribbons overlap at the edge while one climbs) - since fix 2 the level
            # solve holds the separation of such pairs where it can (roadways_net STK_*: 739695588 under 1205493778 /
            # 681667027), so what arrives here has an anchored way, a ramp, or a deficit beyond STK_CAP. The overlap is
            # sampled on a 1-m grid (its vertices alone missed the partial overlaps)
            x0, z0, x1, z1 = X.bounds
            G = np.array(np.meshgrid(np.arange(x0 + 0.5, x1, 1.0), np.arange(z0 + 0.5, z1, 1.0))).reshape(2, -1).T
            G = np.concatenate([G[shapely.contains_xy(X, G[:, 0], G[:, 1])] if len(G) else G.reshape(0, 2), pts])
            d = hp(p, G) - hp(q, G); bad = np.abs(d) < SEP
            if not bad.any(): continue
            rule = 'median' if np.median(dh) < SEP else 'partial'
            lower_is_p = (np.median(dhs) if rule == 'median' else np.median(d[bad])) < 0
            lo, up = (p, q) if lower_is_p else (q, p)
            new, rec = stacked_cut(lo, up, g if lower_is_p else q['geom'], q['geom'] if lower_is_p else g, X, G[bad], float(np.abs(d).min()), rule)
            if rec is None: continue
            recs.append(rec)
            if new is None:
                lo.setdefault('stacked_cut_refused', []).append(rec); continue
            if lower_is_p: g = new
            else: q['geom'] = new
            lo.setdefault('stacked_cut_by', []).append(str(up['id']) + ('' if rule == 'median' else ' (partial)'))
        p['geom'] = g; kept.append(i)
    ref = [r for r in recs if r.get('refused')]; nar = [r for r in recs if r.get('narrowed')]
    log('stacked cuts (the lower deck gives up the overlap, its edge %.1f m from the upper deck\'s): %d (%.0f m2; median rule %d, partial %d); '
        'refused, kept whole under the upper deck (low-clearance conflicts): %d %s; made although they narrow the deck (clash below %.1f m): %d %s'
        % (STACK_GAP, len(recs) - len(ref), sum(r['cut_m2'] for r in recs if not r.get('refused')), sum(1 for r in recs if r['rule'] == 'median' and not r.get('refused')),
           sum(1 for r in recs if r['rule'] == 'partial' and not r.get('refused')), len(ref), [(r['lower'], r['upper'], r['refused'], r['clearance_if_kept_m']) for r in ref],
           KEEP_CLEAR, len(nar), [(r['lower'], r['upper'], r['narrowed']) for r in nar]))
    return recs


def trim(P, TR, log, BODY=None):
    """same-level overlaps go to the higher-priority piece, stacked ones are cut along the upper deck's edge (stack_trim);
    then every piece minus the assets' occupancy in its band and minus the parts that run inside a building
    (enclosure_cuts, review round 2)"""
    recs = stack_trim(P, log)
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
                if not o.is_empty: oc = o.intersection(ch); cut.append(oc); bygrp.setdefault(g, []).append(oc)
        # the landside buildings as solids too (garages, RCC, hotel, CAC: a ramp that runs into a garage ends at its
        # facade; their surfaces alone miss a deck that passes between two of a garage's floors)
        if 'landside' in TR and not TR['landside']['solid'].is_empty:
            sol = TR['landside']['solid'].intersection(p['rib'].buffer(0.5))
            if not sol.is_empty: cut.append(sol); bygrp.setdefault('landside', []).append(sol)
        for (g, u), bd in (BODY or {}).items():
            sol = bd.intersection(p['rib'].buffer(0.5))
            if not sol.is_empty and sol.area > 0.05: cut.append(sol); bygrp.setdefault(g + '/' + u + ' inside', []).append(sol)
        if cut:
            # the deck stops ASSET_BUF short of an asset's occupancy; against the domestic group's curb (the T2 sidewalk
            # slab, whose kerb face the deck butts against at the curb level) only ASSET_BUF_DOM: with 0.10 m (+ the
            # occupancy's triangle edges) a 0.10-0.20 m slot ran along the whole T2 curb (buildings R3.12, close-out r3 fix 2)
            domc = {id(d) for d in bygrp.get('domestic', [])}
            dom = unary_union(bygrp['domestic']) if bygrp.get('domestic') else Polygon()
            rest = [c for c in cut if id(c) not in domc]
            C = unary_union([unary_union(rest).buffer(ASSET_BUF) if rest else Polygon(), dom.buffer(ASSET_BUF_DOM) if not dom.is_empty else Polygon()])
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

    def occ(region, y0, y1):
        """the assets' occupancy in band y0..y1 near a plan region, buffered as above (for the joint wedges)"""
        ch = region.buffer(0.5); rest, dom = [], []
        for g in BI.GROUPS:
            if g not in TR: continue
            o = BI.occupancy(TRN, g, ch.bounds, y0, y1, pad=0.5, tri_only=True)
            if not o.is_empty: (dom if g == 'domestic' else rest).append(o.intersection(ch))
        if 'landside' in TR and not TR['landside']['solid'].is_empty: rest.append(TR['landside']['solid'].intersection(ch))
        rest += [bd.intersection(ch) for bd in (BODY or {}).values()]
        rest = [r for r in rest if not r.is_empty]
        return unary_union([unary_union(rest).buffer(ASSET_BUF) if rest else Polygon(), unary_union(dom).buffer(ASSET_BUF_DOM) if dom else Polygon()])
    jw = joint_wedges(P, occ, log)
    jw['slits'] = slit_fill(P, occ, log)
    return recs, jw


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


def tri_lookup(T2, H3, X, cs=5.0, ref=None):
    """heights at plan points X (m, 2) on plan triangles T2 (n, 3, 2) with vertex heights H3 (n, 3): linear in each
    triangle; nan where no triangle covers the point; where several do (stacked decks), the first, or the one nearest
    in height to ref (m,) (close-out r4 fix round 2 self-checks)"""
    out = np.full(len(X), np.nan)
    if not len(T2) or not len(X): return out
    G = {}; mn = T2.min(1); mx = T2.max(1)
    for i in range(len(T2)):
        for gx in range(int(mn[i, 0] // cs), int(mx[i, 0] // cs) + 1):
            for gz in range(int(mn[i, 1] // cs), int(mx[i, 1] // cs) + 1): G.setdefault((gx, gz), []).append(i)
    byc = {}
    for i, c in enumerate(map(tuple, np.floor(X / cs).astype(np.int64))): byc.setdefault(c, []).append(i)
    for c, idx in byc.items():
        tl = G.get(c)
        if not tl: continue
        q = T2[tl]; a0 = q[:, 0]; v0 = q[:, 1] - a0; v1 = q[:, 2] - a0
        d_ = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]; ok = np.abs(d_) > 1e-12; dd = np.where(ok, d_, 1)
        idx = np.array(idx); px = X[idx, None, 0] - a0[None, :, 0]; pz = X[idx, None, 1] - a0[None, :, 1]
        uu = (px * v1[None, :, 1] - pz * v1[None, :, 0]) / dd; vv = (v0[None, :, 0] * pz - v0[None, :, 1] * px) / dd
        m = ok[None] & (uu >= -1e-6) & (vv >= -1e-6) & (uu + vv <= 1 + 1e-6)
        Hh = H3[None, tl, 0] + uu * (H3[None, tl, 1] - H3[None, tl, 0]) + vv * (H3[None, tl, 2] - H3[None, tl, 0])
        hit = m.any(1); j = np.argmax(m, 1) if ref is None else np.argmin(np.where(m, np.abs(Hh - ref[idx, None]), np.inf), 1)
        out[idx[hit]] = Hh[hit, j[hit]]
    return out


def vnormals(P, I):
    n = np.zeros_like(P)
    f = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    for k in range(3): np.add.at(n, I[:, k], f)
    l = np.linalg.norm(n, axis=1, keepdims=True); n = n / np.maximum(l, 1e-9)
    n[l[:, 0] < 1e-9] = (0.0, 1.0, 0.0)   # vertices no triangle uses (a soffit's subset): a unit normal (glTF validator, r22 LOD2: 29 errors)
    return n


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


STEP_TOL = 0.30       # m: two decks whose tops are within this of each other where they meet are one carriageway (no barrier
                      # between them; the higher one's step face closes the joint); a larger step is an edge of each, with a
                      # parapet on both (a median barrier). Close-out r4: the pair used to count as one carriageway when the
                      # median step over their whole contact was < 1 m, so steps of 0.3-5.9 m were left open over ~880 m of
                      # edge (the verifier's unguarded 0.44-0.63 m step in interchange_2_2) [inf: the verifier's +-0.3 m rule]
INNER_GAP = {0: 0.08, 1: 0.40, 2: 1.05}   # m per LOD: a neighbour this close continues the deck (the LOD's simplification + 0.05)
RUN_MIN, ACROSS, SHORT_DH = 2.0, 0.6, 1.0   # m: an outer chain shorter than RUN_MIN with a deck within SHORT_DH of its level
                             # ACROSS m beyond its middle and both ends is the side of a slit, or where the step between two
                             # decks crosses STEP_TOL: its face only (no parapet 'finger' in the lane) [inf]


def edge_runs(A, B, nbrs, h_self, against, gap=0.08, step=0.5):
    """a deck ring's segments (A -> B) split where their class changes: inner (a neighbouring deck within `gap` whose top is
    within STEP_TOL there: the deck continues, no fascia / parapet), against an asset (the edge face only), or outer.
    Close-out round 3 fix 2 (verifier v4): sampled every `step` m (a segment's midpoint class left a ~1 m parapet opening at
    the ITB lower level's sidewalk corner). Fix 2, buildings R3.12: an edge against an asset gets its fascia - the deck's edge
    face - but no parapet. Close-out round 4: the neighbour test is local (the step at each sample, any neighbour that
    qualifies), not a per-pair median. Returns (A, B, outer flags, against flags, neighbour index per run or -1, the ring
    segment of each run and the run's ends on it as fractions ta, tb)."""
    L = np.linalg.norm(B - A, axis=1); n = np.maximum(1, np.ceil(L / step).astype(int))
    seg = np.repeat(np.arange(len(A)), n); k = np.concatenate([np.arange(m) for m in n])
    t = (k + 0.5) / n[seg]; Mp = A[seg] + t[:, None] * (B - A)[seg]
    mp = shapely.points(Mp); hs = h_self(Mp)
    nbi = np.full(len(Mp), -1)
    for qi, q in enumerate(nbrs):
        m = (nbi < 0) & (shapely.distance(q['geom'], mp) < gap)
        if not m.any(): continue
        ii = np.nonzero(m)[0]; ok = np.abs(hb(q, Mp[ii]) - hs[ii]) < STEP_TOL
        nbi[ii[ok]] = qi
    inner = nbi >= 0
    ag = (shapely.distance(mp, against) < 0.12) if not against.is_empty else np.zeros(len(Mp), bool)
    cls = np.where(inner, 0, np.where(ag, 2, 1))   # 0 inner, 1 outer, 2 against an asset
    oa, ob, oc, on, oj, ot = [], [], [], [], [], []
    i0 = 0
    for j in range(len(A)):
        cj = cls[i0:i0 + n[j]]; nj = nbi[i0:i0 + n[j]]; i0 += n[j]
        cut = np.nonzero(np.diff(cj))[0] + 1   # sample indices where the class changes
        edges = np.concatenate([[0], cut, [n[j]]]) / n[j]
        for ta, tb in zip(edges[:-1], edges[1:]):
            i = min(int(round(ta * n[j])), n[j] - 1)
            oa.append(A[j] + ta * (B[j] - A[j])); ob.append(A[j] + tb * (B[j] - A[j])); oc.append(int(cj[i])); on.append(int(nj[i])); oj.append(j); ot.append((ta, tb))
    oc = np.array(oc); ot = np.array(ot).reshape(-1, 2)
    return np.array(oa), np.array(ob), oc == 1, oc == 2, np.array(on), np.array(oj, int), ot[:, 0], ot[:, 1]


def chain_len(flag, L):
    """per run: the length of the maximal cyclic chain of consecutive runs with the same flag value"""
    n = len(flag); out = np.zeros(n)
    if not n: return out
    if flag.all() or not flag.any(): out[:] = L.sum(); return out
    k0 = int(np.nonzero(flag != np.roll(flag, 1))[0][0])   # a chain start
    idx = np.roll(np.arange(n), -k0); i = 0
    while i < n:
        j = i
        while j + 1 < n and flag[idx[j + 1]] == flag[idx[i]]: j += 1
        out[idx[i:j + 1]] = L[idx[i:j + 1]].sum(); i = j + 1
    return out


def _bottoms(p, lod):
    """(plan triangles (n, 3, 2), per-corner underside heights above grade (n, 3)) of piece p at this LOD as build_piece
    builds it: the soffit (deck depth below the top) on triangles with a vertex at or above FILL_H, grade (0) under fill;
    cached (close-out round 5: the joint closures under the decks)"""
    c = p.setdefault('_bot', {})
    if lod in c: return c[lod]
    geom = p['geom'].simplify({0: 0.05, 1: 0.35, 2: 1.0}[lod])
    V, I = tri_polys(geom, {0: 6.0, 1: 16.0, 2: 30.0}[lod]) if not geom.is_empty else (np.zeros((0, 2)), np.zeros((0, 3), int))
    if not len(I): c[lod] = None; return None
    h = hb(p, V); sof = (h >= FILL_H)[I].any(1)
    c[lod] = (V[I], np.where(sof[:, None], np.maximum(h - RN.DECK_DEPTH, 0.0)[I], 0.0))
    return c[lod]


def build_piece(mb, p, P_all, lod, mat_deck, top=True):
    geom = p['geom'].simplify({0: 0.05, 1: 0.35, 2: 1.0}[lod])
    if geom.is_empty: return
    SEG = {0: 6.0, 1: 16.0, 2: 30.0}[lod]
    V, I = tri_polys(geom, SEG)
    if not len(I): return
    h = hb(p, V)
    if top:   # the plate's top is built by build_plate_top (bands, islands, crosswalks)
        lat, s = lateral(p, V)
        Pt = np.c_[V[:, 0], GROUND_Y + h, V[:, 1]]
        T = np.c_[0.5 + lat / max(p['lanes'] * RN.LANE_W, 1.0), s / DASH_CYCLE]
        mb.tris(p['unit'], lod, mat_deck, Pt, vnormals(Pt, I), T, I)
    # soffit (where the deck is on columns). Close-out r4 fix round 2 (verifier ver1, minor 6): on every triangle with a
    # vertex at or above FILL_H (r22 / r4: only where all three were, so the triangles crossing the FILL_H contour had no
    # underside - the deck box was open from below there, over two columns at 3.24 / 3.36 m), at the deck depth below the
    # top (not less than grade); where such a triangle meets one that is all fill, an abutment face from grade up to the
    # soffit closes the fill
    up = h >= FILL_H
    if up.any():
        sof = up[I].any(1); Ib = I[sof]
        if len(Ib):
            hs = np.maximum(h - RN.DECK_DEPTH, 0.0)
            Pb = np.c_[V[:, 0], GROUND_Y + hs, V[:, 1]]; Ib2 = Ib[:, [0, 2, 1]]
            mb.tris(p['unit'], lod, 'concrete', Pb, vnormals(Pb, Ib2), np.c_[V[:, 0] / 4, V[:, 1] / 4], Ib2)
            fill = I[~sof]
            if len(fill):
                ef = {tuple(sorted(e)) for t in fill for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0]))}
                for t in Ib:
                    for e, o in (((t[0], t[1]), t[2]), ((t[1], t[2]), t[0]), ((t[2], t[0]), t[1])):
                        if tuple(sorted(e)) not in ef: continue
                        a, b = V[e[0]], V[e[1]]; L = float(np.linalg.norm(b - a))
                        if L < 1e-6: continue
                        n2 = np.array([b[1] - a[1], -(b[0] - a[0])]) / L
                        if n2 @ (V[o] - a) < 0: n2 = -n2   # facing the span (the soffit triangle's side)
                        q4 = np.array([[a[0], GROUND_Y, a[1]], [b[0], GROUND_Y, b[1]], [b[0], GROUND_Y + hs[e[1]], b[1]], [a[0], GROUND_Y + hs[e[0]], a[1]]])
                        nrm = np.array([n2[0], 0.0, n2[1]]); fq = np.cross(q4[1] - q4[0], q4[2] - q4[0])
                        if fq @ nrm < 0: q4 = q4[[1, 0, 3, 2]]
                        mb.tris(p['unit'], lod, 'concrete', q4, np.repeat(nrm[None], 4, 0), np.array([[0, 0], [L / 4, 0], [L / 4, hs[e[1]] / 4], [0, hs[e[0]] / 4]]), np.array([[0, 1, 2], [0, 2, 3]]))
                        if lod == 0: es = p.setdefault('edge_stats', {}); es['abutment_m'] = es.get('abutment_m', 0.0) + L
    # edges: fascia (top -> soffit or grade) and parapets on the outer ones; close-out r4: the neighbours within reach (any
    # level: edge_runs decides per sample whether the deck continues into one of them)
    nbrs = [q for q in P_all if q is not p and not q['geom'].is_empty and q['geom'].distance(geom) < max(INNER_GAP[lod], ACROSS) + 0.2]
    against = p.get('against', Polygon())
    st = p.setdefault('edge_stats', {})
    def quad(q4, nrm, L, y0a, y0b, y1a, y1b):
        f = np.cross(q4[1] - q4[0], q4[2] - q4[0])
        if f @ nrm < 0 or (abs(f @ nrm) < 1e-9 and np.cross(q4[2] - q4[0], q4[3] - q4[0]) @ nrm < 0): q4 = q4[[1, 0, 3, 2]]
        mb.tris(p['unit'], lod, 'concrete', q4, np.repeat(nrm[None], 4, 0), np.array([[0, y0a / 4], [L / 4, y0b / 4], [L / 4, y1b / 4], [0, y1a / 4]]), np.array([[0, 1, 2], [0, 2, 3]]))
    parts = [x for x in (getattr(geom, 'geoms', None) or [geom]) if isinstance(x, Polygon)]
    for pi, poly in enumerate(parts):
        # the piece's other parts continue it as a neighbour would (close-out r4: a multi-part deck's parts that touch)
        own = [dict(p, geom=unary_union(parts[:pi] + parts[pi + 1:]))] if len(parts) > 1 else []
        for ring in [poly.exterior] + list(poly.interiors):
            # close-out r4 fix round 2 (verifier ver1, minor 2): the ring at the deck triangulation's own spacing (tri_polys
            # segmentizes the same polygon at SEG: the same boundary vertices), and the edge heights linear between hb() at
            # those vertices, as the deck's boundary edges are - r4 segmentized the rings at 8 m and evaluated hb() at the
            # run ends, so with the blend's non-linear levels the barrier feet left the deck (230 m floating > 0.02 m)
            R = np.array(shapely.segmentize(ring, SEG).coords)
            if len(R) < 3: continue
            hR = hb(p, R)
            A, B, outer, agf, nbr, sj, ta_, tb_ = edge_runs(R[:-1], R[1:], nbrs + own, lambda X: hb(p, X), against, gap=INNER_GAP[lod])
            ha = hR[sj] + ta_ * (hR[sj + 1] - hR[sj]); hb_ = hR[sj] + tb_ * (hR[sj + 1] - hR[sj])
            ba, bb = bottom_of(ha), bottom_of(hb_)
            Ls = np.linalg.norm(B - A, axis=1)
            # outward normals (plan): polygon exterior is ccw in shapely's (x, z) = clockwise seen from above with z south
            # (y up, x east, z south is left-handed in plan): pick the side by the containment test
            e2 = B - A; N2 = np.c_[e2[:, 1], -e2[:, 0]] / np.maximum(Ls, 1e-9)[:, None]
            flip = shapely.contains_xy(poly, *(0.5 * (A + B) + 0.05 * N2).T); N2[flip] *= -1
            # close-out r4: a short outer chain (< RUN_MIN) with a same-level deck ACROSS beyond its middle and both ends is
            # the side of a slit between decks (the r22 'fingers'): the edge face only
            cl = chain_len(outer, Ls)
            for k in np.nonzero(outer & (cl < RUN_MIN))[0]:
                pr = np.array([A[k] + 0.1 * (B[k] - A[k]) / max(Ls[k], 1e-9), 0.5 * (A[k] + B[k]), B[k] - 0.1 * (B[k] - A[k]) / max(Ls[k], 1e-9)]) + ACROSS * N2[k]
                hk = hb(p, pr)
                if all(any(q['geom'].contains(Point(*x)) and abs(float(hb(q, x[None])[0]) - hx) < SHORT_DH for q in nbrs + own) for x, hx in zip(pr, hk)):
                    outer[k] = False; agf[k] = True; st['slit_runs_dropped_m'] = st.get('slit_runs_dropped_m', 0.0) + float(Ls[k]) if lod == 0 else st.get('slit_runs_dropped_m', 0.0)
            if lod == 0 and top:
                # fix round 2 self-check (verifier ver1, minor 2): every parapet's foot against the deck's own top
                # triangles, every 0.5 m, 0.02 m inside the edge (base - deck: > 0 floats, < 0 buried)
                pk = np.nonzero(outer & ~agf & (np.maximum(ha, hb_) > 0.4))[0]
                if len(pk):
                    ns = np.maximum(2, np.ceil(Ls[pk] / 0.5).astype(int) + 1)
                    kk = np.repeat(pk, ns); tt = np.concatenate([np.linspace(0, 1, m) for m in ns])
                    X = A[kk] + tt[:, None] * (B[kk] - A[kk]) - 0.02 * N2[kk]
                    g = (ha[kk] + tt * (hb_[kk] - ha[kk])) - tri_lookup(V[I], h[I], X)
                    wl = np.repeat(Ls[pk] / ns, ns); ok = ~np.isnan(g)
                    fs = st.setdefault('foot', dict(samples=0, no_deck=0, float_gt002_m=0.0, buried_gt002_m=0.0, max_float_m=0.0, max_buried_m=0.0))
                    fs['samples'] += int(len(g)); fs['no_deck'] += int((~ok).sum())
                    if ok.any():
                        fs['float_gt002_m'] += float(wl[ok][g[ok] > 0.02].sum()); fs['buried_gt002_m'] += float(wl[ok][g[ok] < -0.02].sum())
                        fs['max_float_m'] = max(fs['max_float_m'], float(g[ok].max())); fs['max_buried_m'] = max(fs['max_buried_m'], float(-g[ok].min()))
            for k in range(len(A)):
                a, b = A[k], B[k]; L = float(Ls[k]); nrm = np.array([N2[k, 0], 0.0, N2[k, 1]])
                if not (outer[k] or agf[k]):
                    # inner: the higher deck's step face down to the neighbour's top (steps up to STEP_TOL; close-out r4)
                    if nbr[k] < 0 or lod == 2: continue
                    qa, qb = hb((nbrs + own)[nbr[k]], np.array([a, b]))
                    da, db = ha[k] - qa, hb_[k] - qb
                    # close-out round 5 (integration verifier, f3 / f6 residuals): the joint UNDER the decks. Where this deck's
                    # underside at the joint (its soffit, or its own abutment) is higher than the neighbour's (the neighbour's
                    # soffit after a 0.02-0.30 m step: a see-through slit; or grade under an all-fill neighbour: the hollow fill
                    # deck seen from under the span, 16.5 m at cross-piece fill joints), a vertical face from the neighbour's
                    # underside up to this one's closes it, facing into this deck's under-space (r4 built abutments only
                    # between triangles of ONE piece)
                    q_ = (nbrs + own)[nbr[k]]
                    if q_['id'] != p['id'] and lod < 2:
                        # probes 5 % in from the run's ends (at the ends themselves a polygon corner puts the probe outside both
                        # decks: c5 dev g2, 1,368 m unresolved), 0.06 m into this deck and 0.06 / INNER_GAP + 0.06 m into the
                        # neighbour (it may stand off by up to INNER_GAP: c5 dev g1 closed only 9.2 of the 16.5 m)
                        Xe = np.array([a + 0.05 * (b - a), b - 0.05 * (b - a)])
                        X2 = Xe - 0.06 * N2[k]
                        Tp, Tq = _bottoms(p, lod), _bottoms(q_, lod)
                        if Tp is not None and Tq is not None:
                            bp_ = tri_lookup(Tp[0], Tp[1], X2); bq_ = np.full(2, np.nan)
                            for off in (0.06, INNER_GAP[lod] + 0.06):
                                bq_ = np.where(np.isnan(bq_), tri_lookup(Tq[0], Tq[1], Xe + off * N2[k]), bq_)
                                if not np.isnan(bq_).any(): break
                            if np.isnan(bq_).any():
                                # c5 fix-round check (the last cross-piece fill joint, (-1607.7, 459.1), 4.4 m still open): edge_runs
                                # gives one neighbour per run, but a run's far end can abut ANOTHER piece (deck 35157100's 4.4-m run
                                # against ramp 735035451 ends on ramp 735035452, 0.92 m from the first): an unresolved probe takes
                                # the underside of the first other neighbour that has one at the probe point
                                for q2 in nbrs + own:
                                    if q2 is q_ or q2['id'] == p['id'] or not np.isnan(bq_).any(): continue
                                    T2_ = _bottoms(q2, lod)
                                    if T2_ is None: continue
                                    for off in (0.06, INNER_GAP[lod] + 0.06):
                                        b2 = tri_lookup(T2_[0], T2_[1], Xe + off * N2[k])
                                        bq_ = np.where(np.isnan(bq_), b2, bq_)
                            if (np.isnan(bp_).any() or np.isnan(bq_).any()) and lod == 0:
                                st['under_joint_unresolved_m'] = st.get('under_joint_unresolved_m', 0.0) + L
                            elif not (np.isnan(bp_).any() or np.isnan(bq_).any()) and (bp_ > 0.05).all() and (bp_ - bq_ > 0.02).any():
                                ya, yb = min(bq_[0], bp_[0]), min(bq_[1], bp_[1])
                                quad(np.array([[a[0], GROUND_Y + ya, a[1]], [b[0], GROUND_Y + yb, b[1]], [b[0], GROUND_Y + bp_[1], b[1]], [a[0], GROUND_Y + bp_[0], a[1]]]),
                                     -nrm, L, ya, yb, bp_[0], bp_[1])
                                if lod == 0:
                                    st['under_joint_m'] = st.get('under_joint_m', 0.0) + L
                                    if (bq_ < 0.05).any(): st['under_joint_to_grade_m'] = st.get('under_joint_to_grade_m', 0.0) + L
                        elif lod == 0 and Tp is not None:
                            st['under_joint_unresolved_m'] = st.get('under_joint_unresolved_m', 0.0) + L
                    if max(da, db) > 0.02:
                        if lod == 0:   # fix round 2: the step faces by height (the verifier's ledges inside a carriageway; the ITB lower sidewalk's kerb apart)
                            hk = max(da, db); bn = '0.02-0.05' if hk <= 0.05 else '0.05-0.10' if hk < 0.1 else '0.10-0.20' if hk < 0.2 else '0.20-0.30' if hk <= STEP_TOL + 0.01 else '>0.30'
                            if 'walk' in (p['src'], (nbrs + own)[nbr[k]]['src']): bn = 'walk_kerb'
                            sb = st.setdefault('step_face_bins_m', {}); sb[bn] = sb.get(bn, 0.0) + L
                            st.setdefault('step_face_sites', []).append((round(float(hk), 3), round(L, 2), [round(float(c), 1) for c in 0.5 * (a + b)], (nbrs + own)[nbr[k]]['id'], bool(connected(p, (nbrs + own)[nbr[k]]))))
                        da, db = max(da, 0.0), max(db, 0.0)
                        quad(np.array([[a[0], GROUND_Y + ha[k] - da, a[1]], [b[0], GROUND_Y + hb_[k] - db, b[1]], [b[0], GROUND_Y + hb_[k], b[1]], [a[0], GROUND_Y + ha[k], a[1]]]),
                             nrm, L, ha[k] - da, hb_[k] - db, ha[k], hb_[k])
                        if lod == 0: st['step_face_m'] = st.get('step_face_m', 0.0) + L
                    continue
                quad(np.array([[a[0], GROUND_Y + ba[k], a[1]], [b[0], GROUND_Y + bb[k], b[1]], [b[0], GROUND_Y + hb_[k], b[1]], [a[0], GROUND_Y + ha[k], a[1]]]), nrm, L, ba[k], bb[k], ha[k], hb_[k])
                top = max(ha[k], hb_[k])
                if agf[k]: continue   # against an asset (or a slit side): the edge face only
                if lod == 0: st['parapet_m'] = st.get('parapet_m', 0.0) + L
                if lod == 1 and top > 0.4:
                    # LOD1 parapet: the outer face only (the fascia carried up by PARAPET_H)
                    quad(np.array([[a[0], GROUND_Y + ha[k], a[1]], [b[0], GROUND_Y + hb_[k], b[1]], [b[0], GROUND_Y + hb_[k] + PARAPET_H, b[1]], [a[0], GROUND_Y + ha[k] + PARAPET_H, a[1]]]),
                         nrm, L, 0, 0, 0.8, 0.8)
                if lod == 0 and top > 0.4:
                    # parapet: a box on the edge, PARAPET_W inward; closed at the end of a chain (a barrier end / gore nose)
                    inn = -nrm[[0, 2]] * PARAPET_W
                    a2, b2 = a + inn, b + inn; H = PARAPET_H
                    box_p = [
                        (np.array([[a[0], GROUND_Y + ha[k], a[1]], [b[0], GROUND_Y + hb_[k], b[1]], [b[0], GROUND_Y + hb_[k] + H, b[1]], [a[0], GROUND_Y + ha[k] + H, a[1]]]), nrm),
                        (np.array([[b2[0], GROUND_Y + hb_[k], b2[1]], [a2[0], GROUND_Y + ha[k], a2[1]], [a2[0], GROUND_Y + ha[k] + H, a2[1]], [b2[0], GROUND_Y + hb_[k] + H, b2[1]]]), -nrm),
                        (np.array([[a[0], GROUND_Y + ha[k] + H, a[1]], [b[0], GROUND_Y + hb_[k] + H, b[1]], [b2[0], GROUND_Y + hb_[k] + H, b2[1]], [a2[0], GROUND_Y + ha[k] + H, a2[1]]]), np.array([0, 1.0, 0]))]
                    ed = np.array([b[0] - a[0], 0.0, b[1] - a[1]]) / max(L, 1e-9)
                    if not outer[k - 1]:
                        box_p.append((np.array([[a[0], GROUND_Y + ha[k], a[1]], [a2[0], GROUND_Y + ha[k], a2[1]], [a2[0], GROUND_Y + ha[k] + H, a2[1]], [a[0], GROUND_Y + ha[k] + H, a[1]]]), -ed))
                    if not outer[(k + 1) % len(A)]:
                        box_p.append((np.array([[b[0], GROUND_Y + hb_[k], b[1]], [b2[0], GROUND_Y + hb_[k], b2[1]], [b2[0], GROUND_Y + hb_[k] + H, b2[1]], [b[0], GROUND_Y + hb_[k] + H, b[1]]]), ed))
                    for qq, nn in box_p:
                        # winding: make the face normal agree with nn
                        f = np.cross(qq[1] - qq[0], qq[2] - qq[0])
                        if f @ nn < 0: qq = qq[[1, 0, 3, 2]]
                        Lq = float(np.linalg.norm(qq[1] - qq[0]))
                        mb.tris(p['unit'], lod, 'concrete', qq, np.repeat(nn[None], 4, 0), np.array([[0, 0], [Lq / 4, 0], [Lq / 4, H / 4], [0, H / 4]]), np.array([[0, 1, 2], [0, 2, 3]]))


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


def lower_strip(M):
    """the lower outer roadway's band on the straight section (world polygon): u over the straight, v from beyond the imaged
    outer edge to the plate's edge (island B's west edge) - the plate of LOWER_H in the level solve (close-out round 3)"""
    C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    s0, s1 = M['straight']
    return Polygon(RP.xz_of(np.array([[s0, M['v_cap'] - 5], [s1, M['v_cap'] - 5], [s1, M['gutter_v']], [s0, M['gutter_v']]]), C, du, dv))


def lower_walk(M, P, lower, log):
    """close-out round 3 (integration-2): the lower level's sidewalk along the plate's edge, from the lower roadway's inner
    edge to WALK_UNDER under the plate (photo i1: the lower level continues under the departures deck; OSM footway 1164416297,
    layer 1, runs ~16 m inside the plate edge at v ~ -48 - the depth is open, see WALK_UNDER) at the lower roadway's level + WALK_KERB, over the straight section where the lower roadway
    is: it closes the 0.4-0.6 m slit the stacked-deck trim leaves between the plate and the lower roadway (seen from the
    departures deck or from above, the lower level now continues under the plate's fascia and planter)"""
    C, du, dv = np.array(M['frame']['centre']), np.array(M['frame']['du']), np.array(M['frame']['dv'])
    s0, s1 = M['straight']; vg = M['gutter_v']
    hs = [L['h_m'] for L in M.get('lower', [])]
    if not hs: return None
    h = float(np.median(hs)) + WALK_KERB
    v0, v1 = vg - STACK_GAP - 0.4, vg + WALK_UNDER          # overlaps the lower roadway by 0.4 m (the same-level trim gives it to the roadway)
    rib = Polygon(RP.xz_of(np.array([[s0, v0], [s1, v0], [s1, v1], [s0, v1]]), C, du, dv))
    vm = 0.5 * (v0 + v1); pts = RP.xz_of(np.array([[s1, vm], [s0, vm]]), C, du, dv); ln = LineString(pts)
    log('lower level sidewalk along the plate edge: u %.1f..%.1f, v %.2f..%.2f (%.1f m under the plate), level %.2f m [inf]' % (s0, s1, v0, v1, WALK_UNDER, h))
    return dict(id='itb_lower_walk', src='walk', w=v1 - v0, lanes=0, oneway=True, anchor=None, layer=1, pts=pts, s=np.array([0.0, ln.length]), h=np.array([h, h]), nodes=[],
                name='ITB lower level sidewalk under the departures deck edge', kind='walk', line=ln, half=(v1 - v0) / 2, rib=rib, hmin=h, hmax=h)


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
            # island B is the deck-edge planter (close-out round 3, photo i1): planting at PLANTER_H in concrete walls
            planter = b['name'] == 'islandB'; ih = PLANTER_H if planter else ISLAND_H
            top(g, 'planter' if planter else 'island', ih, plainT)
            if lod < 2:   # kerb faces on the long sides (the island's ends stop at the straight section's ends)
                for poly in (getattr(g, 'geoms', None) or [g]):
                    if not isinstance(poly, Polygon): continue
                    R = np.array(poly.exterior.coords); A, B = R[:-1], R[1:]
                    for a, c in zip(A, B):
                        e = c - a; Lm = float(np.linalg.norm(e))
                        if Lm < 0.2: continue
                        nrm = np.array([e[1], -e[0]]) / Lm
                        if poly.contains(Point(*(0.5 * (a + c) + 0.05 * nrm))): nrm = -nrm
                        y0, y1 = GROUND_Y + p['hmin'], GROUND_Y + p['hmin'] + ih
                        q = np.array([[a[0], y0, a[1]], [c[0], y0, c[1]], [c[0], y1, c[1]], [a[0], y1, a[1]]]); n3 = np.array([nrm[0], 0.0, nrm[1]])
                        if np.cross(q[1] - q[0], q[2] - q[0]) @ n3 < 0: q = q[[1, 0, 3, 2]]
                        mb.tris(p['unit'], lod, 'concrete' if planter else 'island', q, np.repeat(n3[None], 4, 0), np.array([[0, 0], [Lm / 4, 0], [Lm / 4, ih / 4], [0, ih / 4]]), np.array([[0, 1, 2], [0, 2, 3]]))
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


def t2_curb_gap_check(P, TR, curb_h, h_dom, log, step=0.25, near=2.0):
    """close-out r3 fix 2 (buildings R3.12): the void between the domestic T2 curb sidewalk (the T2 unit's LOD0 up-facing
    triangles at the curb level) and the domestic departures deck top (pieces within 0.3 m of the deck level), as the plan
    distance from each point of the sidewalk's edge (every `step` m) to the deck; edge points within `near` m of the deck
    count (the curb side - the ends and the building side are farther off); limit 0.05 m"""
    T = TR['_lods'].get(('domestic', 'T2', 0))
    if T is None or not len(T): return dict(points=0, note='no domestic T2 LOD0')
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    S = T[(n[:, 1] > 0.95) & (np.abs(T[:, :, 1] - (GROUND_Y + curb_h)).max(1) < 0.06)]
    side = unary_union([Polygon(t[:, [0, 2]]).buffer(0.005) for t in S if Polygon(t[:, [0, 2]]).area > 1e-4]).buffer(-0.005)
    deck = unary_union([q['geom'] for q in P if q.get('unit') == 'domestic_departures' and not q['geom'].is_empty and abs(float(np.median(q['h'])) - h_dom) < 0.3])
    if side.is_empty or deck.is_empty: return dict(points=0, note='no T2 sidewalk / deck')
    pts = np.array([r.interpolate(s).coords[0] for g in (getattr(side, 'geoms', None) or [side]) for r in [g.exterior] for s in np.arange(0, r.length, step)])
    d = shapely.distance(deck, shapely.points(pts)); m = d < near
    if not m.any(): return dict(points=0, note='the deck is > %.1f m from the T2 sidewalk' % near)
    res = dict(points=int(m.sum()), median_void_m=round(float(np.median(d[m])), 3), max_void_m=round(float(d[m].max()), 3), at=np.round(pts[m][np.argmax(d[m])], 1).tolist(),
               over_0_05m=int((d[m] > 0.05).sum()), over_0_3m=int((d[m] > 0.3).sum()), overlap_m2=round(float(side.intersection(deck).area), 2), limit_m=0.05)
    log('T2 curb to domestic departures deck (R3.12): %d sidewalk edge points within %.0f m of the deck, void median %.3f / max %.3f m (at %s), %d over 0.05 m, %d over 0.3 m; plan overlap %.2f m2'
        % (res['points'], near, res['median_void_m'], res['max_void_m'], res['at'], res['over_0_05m'], res['over_0_3m'], res['overlap_m2']))
    return res


def parapet_check(mb, log, cs=5.0):
    """close-out round 4 self-check (the round-3 verifier's 'in-carriageway parapet' rule, stubs4): the LOD0 parapet tops
    (concrete triangles facing up, n.y > 0.9) sampled on a 0.25-m barycentric grid and deduplicated on a 0.2-m plan grid;
    a sample stands IN a carriageway when a road surface (deck_* / sidewalk tops) at its deck level (top - PARAPET_H,
    +-0.3 m) lies 0.6 m away in at least 7 of 8 directions - a barrier with the same deck on both sides. Reported as
    samples, ~metres (samples x 0.04 m2 / PARAPET_W) and 4-m clusters of >= 6 samples (~0.6 m)"""
    S, C = [], []
    for (u, l, mat), b in mb.d.items():
        if l != 0 or not b['P']: continue
        off = 0; deck = mat.startswith('deck') or mat == 'sidewalk'
        for P, I in zip(b['P'], b['I']):
            T = P[I - off]; off += len(P)
            if not (deck or mat == 'concrete') or not len(T): continue
            nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); a = np.linalg.norm(nn, axis=1) / 2; up = nn[:, 1] / (2 * a + 1e-12)
            if deck: S.append(T[(up > 0.5) & (a > 1e-5)])
            else: C.append(T[(up > 0.9) & (a > 1e-4)])
    if not S or not C: return dict(samples=0)
    S = np.concatenate(S); C = np.concatenate(C)
    Q = []
    for t in C:
        e = max(np.linalg.norm(t[1] - t[0]), np.linalg.norm(t[2] - t[0])); n = max(1, int(e / 0.25))
        ij = np.array([(i, j) for i in range(n + 1) for j in range(n + 1 - i)], float) / n
        Q.append(t[0] + ij[:, :1] * (t[1] - t[0]) + ij[:, 1:] * (t[2] - t[0]))
    Q = np.concatenate(Q); _, ix = np.unique(np.round(Q[:, [0, 2]] / 0.2).astype(np.int64), axis=0, return_index=True); Q = Q[ix]
    G = {}; mn = S[:, :, [0, 2]].min(1); mx = S[:, :, [0, 2]].max(1)
    for i in range(len(S)):
        for gx in range(int(mn[i, 0] // cs), int(mx[i, 0] // cs) + 1):
            for gz in range(int(mn[i, 1] // cs), int(mx[i, 1] // cs) + 1): G.setdefault((gx, gz), []).append(i)
    ang = np.linspace(0, 2 * np.pi, 8, endpoint=False); D = 0.6 * np.c_[np.cos(ang), np.sin(ang)]
    X = (Q[:, None, [0, 2]] + D[None]).reshape(-1, 2); lvl = np.repeat(Q[:, 1] - PARAPET_H, 8); hit = np.zeros(len(X), bool)
    byc = {}
    for i, c in enumerate(map(tuple, np.floor(X / cs).astype(np.int64))): byc.setdefault(c, []).append(i)
    for c, idx in byc.items():
        tl = G.get(c)
        if not tl: continue
        T = S[tl]; q = T[:, :, [0, 2]]; a0 = q[:, 0]; v0 = q[:, 1] - a0; v1 = q[:, 2] - a0
        d_ = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]; ok = np.abs(d_) > 1e-9; dd = np.where(ok, d_, 1)
        idx = np.array(idx); px = X[idx, None, 0] - a0[None, :, 0]; pz = X[idx, None, 1] - a0[None, :, 1]
        uu = (px * v1[None, :, 1] - pz * v1[None, :, 0]) / dd; vv = (v0[None, :, 0] * pz - v0[None, :, 1] * px) / dd
        m = ok[None] & (uu >= 0) & (vv >= 0) & (uu + vv <= 1)
        Hh = T[None, :, 0, 1] + uu * (T[None, :, 1, 1] - T[None, :, 0, 1]) + vv * (T[None, :, 2, 1] - T[None, :, 0, 1])
        hit[idx] = (m & (np.abs(Hh - lvl[idx, None]) < 0.3)).any(1)
    A = Q[hit.reshape(-1, 8).sum(1) >= 7]
    cl = []
    for r in A:
        for c in cl:
            if math.hypot(c[0] - r[0], c[1] - r[2]) < 4: c[3] += 1; break
        else: cl.append([r[0], r[2], r[1] - GROUND_Y - PARAPET_H, 1])
    cl = sorted([c for c in cl if c[3] >= 6], key=lambda c: -c[3])
    res = dict(samples=int(len(A)), of=int(len(Q)), approx_m=round(len(A) * 0.04 / PARAPET_W, 1), clusters=len(cl),
               top=[dict(at=[round(c[0], 1), round(c[1], 1)], deck_m=round(c[2], 2), approx_m=round(c[3] * 0.04 / PARAPET_W, 1)) for c in cl[:25]],
               rule='parapet-top samples (0.2 m) with the same deck level (+-0.3 m) 0.6 m away in >= 7 of 8 directions (the round-3 verifier\'s stubs4)')
    log('in-carriageway parapet (self-check, close-out r4): %d of %d parapet-top samples (~%.1f m), %d clusters >= 0.6 m; largest %s'
        % (res['samples'], res['of'], res['approx_m'], res['clusters'], res['top'][:5]))
    return res


def _mesh_tris(mb, lod, keep):
    """per (unit, material) the triangles (n, 3, 3) of one LOD whose material passes keep(mat)"""
    out = {}
    for (u, l, mat), b in mb.d.items():
        if l != lod or not b['P'] or not keep(mat): continue
        off = 0; Ts = []
        for P_, I_ in zip(b['P'], b['I']):
            if len(I_): Ts.append(P_[I_ - off])
            off += len(P_)
        if Ts: out[(u, mat)] = np.concatenate(Ts)
    return out


class _PlanGrid:
    """plan bucket grid over triangles (n, 3, 3) (x, y up, z): candidates near a point; heights of the triangles covering it"""

    def __init__(self, T, cs=4.0):
        self.T, self.cs = T, cs; Q = T[:, :, [0, 2]]; self.mn, self.mx = Q.min(1), Q.max(1); G = {}
        for i in range(len(T)):
            for gx in range(int(self.mn[i, 0] // cs), int(self.mx[i, 0] // cs) + 1):
                for gz in range(int(self.mn[i, 1] // cs), int(self.mx[i, 1] // cs) + 1): G.setdefault((gx, gz), []).append(i)
        self.G = {k: np.array(v) for k, v in G.items()}

    def cand(self, x, z, r=0.0):
        ids = set()
        for gx in range(int((x - r) // self.cs), int((x + r) // self.cs) + 1):
            for gz in range(int((z - r) // self.cs), int((z + r) // self.cs) + 1):
                if (gx, gz) in self.G: ids.update(self.G[(gx, gz)].tolist())
        if not ids: return np.zeros(0, int)
        ids = np.array(sorted(ids))
        m = (self.mn[ids, 0] <= x + r) & (self.mx[ids, 0] >= x - r) & (self.mn[ids, 1] <= z + r) & (self.mx[ids, 1] >= z - r)
        return ids[m]

    def heights(self, x, z):
        ids = self.cand(x, z); T = self.T[ids]; q = T[:, :, [0, 2]]
        a, b, c = q[:, 0], q[:, 1], q[:, 2]; v0 = b - a; v1 = c - a; d = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]; ok = np.abs(d) > 1e-9; dd = np.where(ok, d, 1)
        px = x - a[:, 0]; pz = z - a[:, 1]; u = (px * v1[:, 1] - pz * v1[:, 0]) / dd; v = (v0[:, 0] * pz - v0[:, 1] * px) / dd
        mm = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)
        return T[mm, 0, 1] + u[mm] * (T[mm, 1, 1] - T[mm, 0, 1]) + v[mm] * (T[mm, 2, 1] - T[mm, 0, 1])


def _vert_spans(T, x, z, tol=0.04):
    """height ranges of the vertical triangles T at the plan point (x, z) (those whose plan segment passes within tol)"""
    out = []
    for t in T:
        q = t[:, [0, 2]]; d = q.max(0) - q.min(0); ax = 0 if d[0] >= d[1] else 1
        lo, hi = q[:, ax].min(), q[:, ax].max(); pp = (x, z)[ax]
        if pp < lo - tol or pp > hi + tol: continue
        A = q[np.argmin(q[:, ax])]; B = q[np.argmax(q[:, ax])]; AB = B - A
        tt = float(np.clip(((np.array([x, z]) - A) @ AB) / (AB @ AB + 1e-12), 0, 1))
        if np.hypot(*(A + tt * AB - np.array([x, z]))) > tol: continue
        sv = (q[:, ax] - lo) / max(hi - lo, 1e-9); ys = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if (sv[i] - tt) * (sv[j] - tt) <= 0 and abs(sv[j] - sv[i]) > 1e-9:
                f = (tt - sv[i]) / (sv[j] - sv[i]); ys.append(t[i, 1] + f * (t[j, 1] - t[i, 1]))
            elif abs(sv[j] - sv[i]) <= 1e-9 and abs(sv[i] - tt) < 1e-3: ys += [t[i, 1], t[j, 1]]
        if ys: out.append((min(ys), max(ys)))
    return out


def soffit_check(mb, log, lod=0):
    """close-out round 5 self-check (integration verifier, f3 / f6 residuals: see-through slits under 0.02-0.30-m steps and no
    face where a soffit meets a neighbouring piece's fill deck): every boundary edge of the LOD's soffits (down-facing
    concrete, welded at 1 cm), sampled every 0.5 m, is CLOSED when a vertical concrete face passes within 0.04 m in plan and
    spans the soffit height (+-0.03 m), or another soffit continues 0.15 m outward within 0.15 m in height; else OPEN - 'into
    a hollow' when a deck / walk top lies 0.3 m outward above it (one looks from under the span into the hollow under a deck),
    else 'other' (e.g. the deck end over an at-grade road). The same rule as the round-4 verifier's soffit_close.py"""
    SOF, VER, TOP = [], [], []
    for (u, mat), T in _mesh_tris(mb, lod, lambda m: True).items():
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); a = np.linalg.norm(n, axis=1) / 2; up = n[:, 1] / (2 * a + 1e-12)
        if mat == 'concrete':
            SOF.append(T[(up < -0.9) & (a > 1e-5)]); VER.append(T[(np.abs(up) < 0.15) & (a > 1e-5)])
        if mat.startswith('deck') or mat in ('sidewalk', 'planter', 'island'): TOP.append(T[(up > 0.5) & (a > 1e-5)])
    if not SOF: return {}
    SOF, VER, TOP = np.concatenate(SOF), np.concatenate(VER), np.concatenate(TOP)
    GS, GV, GT = _PlanGrid(SOF), _PlanGrid(VER, 3.0), _PlanGrid(TOP)
    K = np.round(SOF / 0.01).astype(np.int64); E = {}
    for i in range(len(SOF)):
        for e in ((0, 1), (1, 2), (2, 0)):
            ka, kb = tuple(K[i, e[0]]), tuple(K[i, e[1]]); E.setdefault((min(ka, kb), max(ka, kb)), []).append((i, e))
    R = dict(face=0.0, soffit_continues=0.0, open_into_hollow=0.0, open_other=0.0); opens = []
    for key, l in E.items():
        if len(l) != 1: continue
        i, e = l[0]; t = SOF[i]; A, B = t[e[0]], t[e[1]]; Ln = float(np.hypot(B[0] - A[0], B[2] - A[2]))
        if Ln < 1e-3: continue
        c = t.mean(0); d = np.array([B[0] - A[0], B[2] - A[2]]) / Ln; nrm = np.array([-d[1], d[0]])
        mid = (np.array([A[0], A[2]]) + np.array([B[0], B[2]])) / 2
        if np.dot(np.array([c[0], c[2]]) - mid, nrm) > 0: nrm = -nrm
        ns = max(1, int(round(Ln / 0.5))); w = Ln / ns
        for j in range(ns):
            Pq = A + (B - A) * ((j + 0.5) / ns); x, z, y = Pq[0], Pq[2], Pq[1]
            ids = GV.cand(x, z, 0.05)
            if len(ids) and any(lo - 0.03 <= y <= hi + 0.03 for lo, hi in _vert_spans(VER[ids], x, z)): R['face'] += w; continue
            hs = GS.heights(x + nrm[0] * 0.15, z + nrm[1] * 0.15)
            if len(hs) and np.min(np.abs(hs - y)) < 0.15: R['soffit_continues'] += w; continue
            ht = GT.heights(x + nrm[0] * 0.3, z + nrm[1] * 0.3)
            kind = 'open_into_hollow' if len(ht) and ((ht > y) & (ht < y + 3.0)).any() else 'open_other'
            R[kind] += w
            if kind == 'open_into_hollow': opens.append([x, z, y - GROUND_Y, w])
    cl = []
    for o in opens:
        for c in cl:
            if np.hypot(c[0] - o[0], c[1] - o[1]) < 6: c[3] += o[3]; break
        else: cl.append(list(o))
    res = dict(rule='LOD%d soffit boundary edges every 0.5 m: closed by a vertical concrete face within 0.04 m spanning the soffit height, or a soffit '
                    'continuing 0.15 m outward within 0.15 m; open into a hollow when a deck / walk top lies 0.3 m outward above (close-out r5)' % lod,
               boundary_m=round(sum(R.values()), 1), **{k + '_m': round(v, 1) for k, v in R.items()},
               open_into_hollow_top=[dict(at=[round(float(c[0]), 1), round(float(c[1]), 1)], soffit_m=round(float(c[2]), 2), len_m=round(float(c[3]), 1))
                                     for c in sorted(cl, key=lambda c: -c[3])[:10]])
    log('soffit closure (self-check, close-out r5; LOD%d): boundary %.0f m - closed by a face %.1f m, soffit continues %.1f m, open into a hollow %.1f m, '
        'open other %.1f m; largest open-into-hollow %s' % (lod, res['boundary_m'], R['face'], R['soffit_continues'], R['open_into_hollow'], R['open_other'],
                                                             res['open_into_hollow_top'][:3]))
    return res


def grade_check(mb, log):
    """close-out r4 fix round 2 self-check (verifier ver1, major: the round-4 blend's grade waves were measured on the way
    profiles, not on the mesh): the AS-BUILT grade of every LOD0 deck-top triangle (deck_* materials, facing up, > 0.001
    m2; |gradient| = hypot(n.x, n.z) / n.y), area-weighted - max, area above 6 / 8 / 10 / 12 / 13.5 %, per unit - and the
    folds between welded neighbouring deck triangles (> 1 / 2 / 4 deg). stats.grade_max stays the profiles' maximum"""
    rows = []; folds = []
    for (u, mat), T in _mesh_tris(mb, 0, lambda m: m.startswith('deck')).items():
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); a = np.linalg.norm(n, axis=1) / 2; n = n / (2 * a[:, None] + 1e-12)
        k = (n[:, 1] > 0.7) & (a > 1e-3); T = T[k]; n = n[k]; a = a[k]
        g = np.hypot(n[:, 0], n[:, 2]) / n[:, 1] * 100
        rows += [(u, float(g[i]), float(a[i]), T[i].mean(0)) for i in range(len(T))]
        K = np.round(T / 0.01).astype(np.int64); E = {}
        for i in range(len(T)):
            for e0, e1 in ((0, 1), (1, 2), (2, 0)):
                E.setdefault(tuple(sorted((tuple(K[i, e0]), tuple(K[i, e1])))), []).append(i)
        for key, li in E.items():
            if len(li) != 2: continue
            ang = float(np.degrees(np.arccos(np.clip(n[li[0]] @ n[li[1]], -1, 1))))
            if ang > 1.0: folds.append((ang, u, float(np.linalg.norm(np.subtract(key[0], key[1]))) * 0.01, (np.add(key[0], key[1]) * 0.005)))
    if not rows: return dict(triangles=0)
    G = np.array([r[1] for r in rows]); A = np.array([r[2] for r in rows])
    th = (6, 8, 10, 12, 13.5)
    by = {}
    for u, g, a, c in rows:
        d = by.setdefault(u, dict(area_m2=0.0, max_pct=0.0, **{'over_%g_pct_m2' % t: 0.0 for t in th[1:4]}))
        d['area_m2'] += a; d['max_pct'] = max(d['max_pct'], g)
        for t in th[1:4]:
            if g > t: d['over_%g_pct_m2' % t] += a
    by = {u: {k: round(v, 1) for k, v in d.items()} for u, d in sorted(by.items())}
    top = []
    for u, g, a, c in sorted(rows, key=lambda r: -r[1]):
        if any(math.hypot(c[0] - t['at'][0], c[2] - t['at'][1]) < 15 for t in top): continue
        top.append(dict(pct=round(g, 1), unit=u, at=[round(float(c[0]), 1), round(float(c[2]), 1)], deck_m=round(float(c[1]) - GROUND_Y, 2)))
        if len(top) >= 10: break
    fa = np.array([f[0] for f in folds] or [0.0]); fl = np.array([f[2] for f in folds] or [0.0])
    res = dict(rule='LOD0 deck-top triangles (deck_* materials, n.y > 0.7, > 0.001 m2): |gradient| %, area-weighted; folds = angle between welded neighbours',
               triangles=len(rows), area_m2=round(float(A.sum()), 1), max_pct=round(float(G.max()), 2), top=top,
               over_pct_m2={'%g' % t: round(float(A[G > t].sum()), 1) for t in th}, by_unit=by,
               folds={'>%d_deg' % t: dict(n=int((fa > t).sum()), edge_m=round(float(fl[fa > t].sum()), 1)) for t in (1, 2, 4, 6)},
               fold_top=[dict(deg=round(f[0], 1), unit=f[1], at=[round(float(f[3][0]), 1), round(float(f[3][2]), 1)], edge_m=round(f[2], 1)) for f in sorted(folds, key=lambda f: -f[0])[:8]])
    # close-out r5 (integration verifier, residual 3): a fold REGRESSION gate - the folds' edge length over 4 / 6 deg against the
    # round-4 fix-2 build (28.9 / 23.3 m; r22 had 5 / 2 folds); the creases themselves are deferred (the warped junction surface)
    lim = {'>4_deg': FOLD_GATE_M[4], '>6_deg': FOLD_GATE_M[6]}
    res['fold_gate'] = dict(limit_edge_m=lim, ok=all(res['folds'][k]['edge_m'] <= v for k, v in lim.items()))
    if not res['fold_gate']['ok']: log('WARNING fold gate: %s over %s' % ({k: res['folds'][k]['edge_m'] for k in lim}, lim))
    log('mesh grades (self-check, close-out r4 fix round 2; LOD0 deck tops): max %.2f %% at %s, area > 8 / 10 / 12 / 13.5 %%: %s m2; folds > 1 / 2 / 4 deg: %s; '
        'units > 10 %%: %s' % (res['max_pct'], top[0], ' / '.join(str(res['over_pct_m2'][k]) for k in ('8', '10', '12', '13.5')),
                              ' / '.join('%d (%.0f m)' % (v['n'], v['edge_m']) for v in res['folds'].values()),
                              {u: d['over_10_pct_m2'] for u, d in by.items() if d['over_10_pct_m2'] > 0}))
    return res


FOLD_GATE_M = {4: 30.4, 6: 24.5}   # m of fold edge over 4 / 6 deg allowed: the r4 fix-2 build's 28.9 / 23.3 m + 5 % [our gate]


COL_TOP = 0.15   # m: a column runs this far up into the deck box above its soffit (fix round 2: 0.05 left 0.01-0.06 m of the
                 # blend's curvature between the column top and the soffit's linear triangles) [inf]


def column_soffit_check(mb, cols, log, tol=COL_TOP):
    """close-out r4 fix round 2 self-check (verifier ver1, minor 6): every LOD0 column's top reaches a down-facing concrete
    triangle (the soffit) of its unit - at the centre and 0.3 m round it the soffit lies between the column top - 1.05 m
    (the top stays inside the 1.2-m deck box) and the column top (no gap)"""
    S = {}
    for (u, mat), T in _mesh_tris(mb, 0, lambda m: m == 'concrete').items():
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); a = np.linalg.norm(n, axis=1) / 2
        S[u] = T[(n[:, 1] / (2 * a + 1e-12) < -0.9) & (a > 1e-4)]
    bad = []
    for c in cols:
        T = S.get(c['unit'], np.zeros((0, 3, 3)))
        X = np.asarray(c['xz'], float)[None] + 0.3 * np.array([[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]])
        y = tri_lookup(T[:, :, [0, 2]], T[:, :, 1], X, ref=np.full(len(X), GROUND_Y + c['soffit'])) if len(T) else np.full(len(X), np.nan)
        d = y - (GROUND_Y + c['soffit'])   # mesh soffit above (+) / below (-) the column's own soffit level
        if not ((np.nan_to_num(d, nan=9.0) <= tol) & (np.nan_to_num(d, nan=-9.0) >= tol - 1.05)).all():
            bad.append(dict(way=c['way'], xz=[round(float(v), 1) for v in c['xz']], soffit_m=round(c['soffit'], 2), off_m=[None if np.isnan(v) else round(float(v), 3) for v in d]))
        c['_soffit_off'] = float(np.nanmax(np.abs(d))) if not np.isnan(d).all() else None
    offs = [c.pop('_soffit_off') for c in cols]; offs = [o for o in offs if o is not None]
    res = dict(columns=len(cols), meeting_soffit=len(cols) - len(bad), column_top_above_soffit_m=tol, max_soffit_offset_m=round(max(offs or [0]), 3), bad=bad[:20])
    log('columns vs soffit (self-check, close-out r4 fix round 2): %d of %d reach a soffit triangle (top %.2f m into the deck box) at the centre and 0.3 m round it, '
        'largest soffit offset %.3f m; bad %s' % (res['meeting_soffit'], len(cols), tol, res['max_soffit_offset_m'], bad[:5] or 'none'))
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
                    hs = float(hb(p, q[None])[0]); soff = hs - RN.DECK_DEPTH
                    if soff < 2.0 or roads.intersects(disk) or solid.intersects(disk): continue
                    # lower decks / ramps under this one, and the other assets' triangles from grade to the soffit
                    low = False
                    for o in P:
                        if o is p or not o['geom'].intersects(disk): continue
                        if float(hb(o, q[None])[0]) < soff - 0.1: low = True; break
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
    # close-out round 3 (integration-2): the lower outer roadway held level at LOWER_H on the straight (photo i1; see LOWER_H)
    sol = RN.solve_levels(ways, grade, F, LV, log, overhead=overhead_of(TR), plates=[dict(poly=M['plate_poly'], h=h_itb, why='ITB L3 deck plate (NAIP 2024)'),
                                                                                    dict(poly=lower_strip(M), h=LOWER_H, why='ITB lower level (photo i1: level; clearance over the building-passage roads)')])
    for u in sol['unresolved']: log('  UNRESOLVED ' + json.dumps(u))
    chk = RN.checks(ways, sol['ramps'], log)
    P = pieces_of(ways, sol['ramps'])
    out = [p for p in P if not CORE.contains(Point(p['pts'].mean(0)))]
    P = [p for p in P if CORE.contains(Point(p['pts'].mean(0)))]
    log('outside the core box %s: %d pieces (%.0f m) not built (ground footprint only, as before)' % (CORE.bounds, len(out), sum(p['line'].length for p in out)))
    plate = plate_piece(M, h_itb); P.insert(0, plate)
    widen_lower(P, lower, M, log)
    walk = lower_walk(M, P, lower, log)
    if walk: P.append(walk)
    units = units_of(P)
    log('pieces %d (decks %d, ramp parts %d, plate 1), units %s' % (len(P), sum(1 for p in P if p['src'] == 'deck'), sum(1 for p in P if p['src'] == 'ramp'), units))
    BODY = enclosure_cuts(P, TR, F0, log)
    stk_recs, jw = trim(P, TR, log, BODY)
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
    blend = blend_neighbours(P, log)
    cols, cst = columns([p for p in P if p['src'] not in ('plate', 'walk')], TR, log)
    pcols = plate_columns(plate, P, TR, log); cols += pcols; cst['plate'] = len(pcols)
    BI.GROUPS[:] = groups0
    asph_naip, asph, nsamp = naip_asphalt([p for p in P if p['src'] not in ('plate', 'walk')])
    log('asphalt: NAIP 2024 median sRGB %s over %d samples -> base colour %s (x %.2f linear)' % (asph_naip, nsamp, asph, NAIP_ALBEDO))
    lite_naip, lite = naip_band(plate, M['outer'])
    log('outer light-concrete roadway: NAIP 2024 median sRGB %s -> base colour %s' % (lite_naip, lite))
    mats = {'concrete': dict(rgb=CONCRETE, rough=0.85, extras=dict(src='inf', note='cast-in-place concrete, light grey'))}
    for p in P:
        if p['src'] == 'plate': p['mat'] = None; continue
        if p['src'] == 'walk': p['mat'] = 'sidewalk'; continue
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
    mats['sidewalk'] = dict(rgb=CONCRETE, rough=0.85, extras=dict(src='inf', note='the ITB lower level sidewalk under the departures deck edge (close-out r3; photo i1; depth inferred - OSM footway 1164416297, layer 1, runs ~16 m further in at v ~ -48)'))
    pl_naip, pl_base = naip_band(plate, 'islandB')
    mats['planter'] = dict(rgb=pl_base, rough=0.95, extras=dict(src='obs colour (NAIP 2024 median over island B) / obs extent (NAIP R - G band, photo i1) / inf height %.2f m' % PLANTER_H,
                                                               note='the planter of pink-flowering shrubs along the departures deck edge (photo i1); was read as a red-painted kerb in review r2'))
    log('deck-edge planter (island B): NAIP 2024 median sRGB %s -> base colour %s' % (pl_naip, pl_base))
    mats['paint_white'] = dict(rgb=(226, 226, 220), rough=0.6, extras=dict(src='inf', note='crosswalk bars at the ITB curb ramps'))
    mb = MB()
    for l in (0, 1, 2):
        for p in P:
            if p['src'] == 'plate': build_piece(mb, p, P, l, None, top=False); build_plate_top(mb, p, l, mats)
            else: build_piece(mb, p, P, l, p['mat'] if (l < 2 or p['src'] == 'walk') else 'deck_plain')
        for c in cols: cylinder(mb, c['unit'], l, c['xz'], GROUND_Y - 0.05, GROUND_Y + c['soffit'] + COL_TOP, D_COL / 2, {0: 12, 1: 6, 2: 4}[l])
    gapchk = curb_gap_check(P, TR, M, LV['itb']['curb'], log)
    gapchk_t2 = t2_curb_gap_check(P, TR, LV['domestic']['curb'], sol['h_dom'], log)
    clr = clearance_check(mb, TR, log); clr_p = clearance_check(mb, TR, log, piers=True)
    pchk = parapet_check(mb, log)
    gchk = grade_check(mb, log)
    cchk = column_soffit_check(mb, cols, log)
    schk = soffit_check(mb, log)
    # close-out r4 self-check (dev build d9 lost two whole decks in a failed merge): pieces without deck although their
    # ribbon is large - every one is listed with the reason the trim gave it (asset / enclosure / stacked cuts)
    empty = [dict(id=p['id'], src=p['src'], rib_m2=round(p['rib'].area, 1), cut_by=p.get('cut_by'), stacked_cut_by=p.get('stacked_cut_by')) for p in P
             if p['src'] in ('deck', 'ramp') and p['geom'].area < 1.0 and p['rib'].area > 20.0]
    log('pieces with no deck left (ribbon > 20 m2): %s' % (empty or 'none'))
    edge = {k: round(sum(p.get('edge_stats', {}).get(k, 0.0) for p in P), 1) for k in ('parapet_m', 'step_face_m', 'slit_runs_dropped_m', 'abutment_m',
                                                                                     'under_joint_m', 'under_joint_to_grade_m', 'under_joint_unresolved_m')}
    edge['step_face_by_height_m'] = {b: round(sum(p.get('edge_stats', {}).get('step_face_bins_m', {}).get(b, 0.0) for p in P), 1) for b in ('0.02-0.05', '0.05-0.10', '0.10-0.20', '0.20-0.30', 'walk_kerb')}
    sites = sorted([x for p in P if p['src'] != 'walk' for x in p.get('edge_stats', {}).get('step_face_sites', []) if x[3] != 'itb_lower_walk'], key=lambda x: -x[0] * x[1])
    edge['step_face_top'] = [dict(h_m=x[0], len_m=x[1], at=x[2], neighbour=x[3], connected=x[4]) for x in sites[:15]]
    ft = [p['edge_stats']['foot'] for p in P if 'foot' in p.get('edge_stats', {})]
    edge['parapet_foot'] = dict(rule='parapet base vs the deck\'s own top triangles, every 0.5 m, 0.02 m inside the edge (close-out r4 fix round 2)',
                                samples=sum(f['samples'] for f in ft), no_deck=sum(f['no_deck'] for f in ft),
                                float_gt002_m=round(sum(f['float_gt002_m'] for f in ft), 1), buried_gt002_m=round(sum(f['buried_gt002_m'] for f in ft), 1),
                                max_float_m=round(max([f['max_float_m'] for f in ft] or [0]), 3), max_buried_m=round(max([f['max_buried_m'] for f in ft] or [0]), 3))
    log('LOD0 edges: parapet %.0f m, step faces %.0f m (inner joints with a step of 0.02-%.2f m; by height %s), slit sides given the edge face only %.1f m, abutment faces %.1f m; '
        'parapet feet: %s' % (edge['parapet_m'], edge['step_face_m'], STEP_TOL, edge['step_face_by_height_m'], edge['slit_runs_dropped_m'], edge['abutment_m'],
                              {k: v for k, v in edge['parapet_foot'].items() if k != 'rule'}))
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
                                                         level_m=LOWER_H, walk=dict(under_plate_m=WALK_UNDER, level_m=round(LOWER_H + WALK_KERB, 2), area_m2=round(walk['geom'].area, 1) if walk else 0),
                                                         note='the lower level (photo i1, close-out round 3): held level at LOWER_H on the straight; OSM layer 1, passes under the anchored departures leg past the straight')),
                 stacked=dict(solve=sol.get('stacked', []), cuts=stk_recs),
                 joint_wedges=jw, in_carriageway_parapet=pchk, pieces_without_deck=empty, edges_lod0=dict(edge, step_tol_m=STEP_TOL, inner_gap_m=INNER_GAP),
                 blend=blend, mesh_grades=gchk, columns_vs_soffit=cchk, soffit_closure=schk,
                 curb_gap=gapchk, curb_gap_t2=gapchk_t2, guideway_clearance=clr, guideway_pier_caps_over_decks=clr_p, deck_cut_inside_buildings_m2=body_cut, deck_left_inside_buildings_m2=body_left)
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
                 observed=['ITB departures deck plate: outline (kerb to the outer edge, the structural gap at the south end), island extents, the deck-edge planter (the NAIP R - G band) - NAIP 2024 relief-corrected (roadways_itb_plate.py, sheet BR-02)',
                           'ITB frontage levels (close-out round 3, integration-2): photo i1 (Kulikovsky 2007, CC BY 3.0, refs/cache/buildings/review_likeness/i1.jpg; reference only) shows the departures deck ending in a '
                           'planter of pink-flowering shrubs on its fascia, and in front of / below it a LOWER level (trees in planters on its outer edge, shelters, pedestrians) that continues under the deck '
                           'and is level along the facade: the outer light-concrete band is that lower level, not the departures deck; coping-to-coping step in i1 ~6.7 m (6.1-7.3; scale 9.0 px/m from the planter, '
                           'NAIP length 104 m = 935 px)',
                           'network topology / centrelines: OSM (ODbL)', 'asphalt and light-concrete colours: NAIP 2024 medians'],
                 inferred=['deck depth 1.2 m, shoulders 0.6 m, parapets 0.40 x 0.85 m, fill below a 3.2 m deck top, round columns 1.4 m at ~30 m (positions where clear)',
                           'ITB deck plate level: the ITB L3 deck top %.2f m (spec_itb level3.floor 11.5 [inf] - 0.15 kerb); the outer light-concrete roadway is the lower level (OSM ways 41015123 / 739695588) '
                           'held level at %.2f m on the straight (%s m built) = clearance %.1f m + deck %.1f m over the at-grade building-passage roads under it [inf: the lowest plausible; photo i1 reads ~1 m lower '
                           'relative to the plate], widened to the imaged band; its sidewalk continues %.1f m under the plate edge (%.2f m) and closes the former 0.4-0.6 m slit; the deck-edge planter %.2f m high; '
                           'island A height 0.15 m; lane counts (OSM minimum / width / 3.6 m); plate columns under the islands and the outer edge'
                           % (h_itb, LOWER_H, ' / '.join('%.2f' % L['h_m'] for L in M.get('lower', [])), RN.CLEAR_MIN, RN.DECK_DEPTH, WALK_UNDER, LOWER_H + WALK_KERB, PLANTER_H),
                           'levels other than the two curbs: screened solve with layer priors %s m and clearance %.1f m (roadways_net.py); at skewed crossings the separation is held '
                           'over the ribbons\' overlap (the per-crossing deficit, XS_*); stacked pairs (a ramp over or along a lower roadway) by lowering the lower way under the upper deck '
                           'over the whole overlap, within %.0f %% grade and above its clearance over at-grade roads (STK_*, close-out r3 fix 2); what is left goes to the trim\'s stacked cut along '
                           'the upper deck\'s edge, refused (and reported) where it would split the lower deck or leave < lanes x %.1f m'
                           % (RN.LAYER_H, RN.CLEAR_MIN, RN.STK_GRADE * 100, MIN_LANE_W),
                           'approach ramps: at-grade OSM roads lifted by the solve (ELL_G %.0f m)' % RN.ELL_G, 'lane counts / widths where OSM has none (class defaults)',
                           'lane markings (pattern, colours)',
                           'close-out round 4: the deck between two ways that continue each other at a shared node (the wedge between their flat caps), the slit or gore '
                           'between two decks narrower than %.1f m at one level, small voids enclosed by decks (< %.0f m2), a %.0f:1 width taper where a wider way continues into a '
                           'narrower one, and connected decks that touch side by side (not end to end) meeting halfway over %.0f m (their step taken out in full up to %.1f m, '
                           'none from %.1f m) - the per-way profiles disagree at junctions - geometry between OSM centrelines, no survey; fix round 2: '
                           'soffits on every triangle with a vertex above the %.1f-m fill level, with an abutment face where the fill begins [inf]'
                           % (2 * SLIT_R, VOID_MAX, TAPER_K, BLEND, BLEND_DH, 2 * BLEND_DH, FILL_H)],
                 unknown=['the domestic departures-curb height (%.3f m is the domestic asset placeholder [unk])' % LV['domestic']['curb'],
                          'every viaduct level: no structural drawings or survey; OSM gives only the layer order',
                          'the ITB lower level (arrivals) roadway: held level at %.2f m on the straight [inf: the lowest that clears the at-grade building-passage roads under it by %.1f m + the %.1f-m deck], '
                          'solved (and lowered under the stacked ramps, roadways_net STK_*) beyond it; photo i1 puts the step from the departures deck ~1 m larger than modelled (~6.7 m vs %.2f m), which would '
                          'mean the L3 deck ~1 m above spec_itb level3.floor 11.5 [inf, +-1.5] (the ITB group\'s value) or depressed building-passage roads - with the modelled pair the ITB loop\'s lower roadway '
                          'passes under its anchored departures legs (OSM 38853121 / 38853045) with less than %.1f m (stacked_cut_refused in the build record); settled in close-out round 3 only that the '
                          'band IS a lower level (photo i1), not the departures deck' % (LOWER_H, RN.CLEAR_MIN, RN.DECK_DEPTH, h_itb - LOWER_H, RN.CLEAR_MIN),
                          'how far the ITB lower level runs under the departures deck: modelled %.1f m (the sidewalk under its edge); OSM footway 1164416297 (layer 1) runs ~16 m inside the plate edge '
                          '(v ~ -48, under island A), so it likely runs much further in (no photo of the space under the deck)' % WALK_UNDER],
                 deviations=['decks over at-grade roads with less than %.1f m clearance: the anchored domestic loop (soffit %.2f m) - the curb placeholder, kept as the domestic asset has it'
                             % (RN.CLEAR_MIN, sol['h_dom'] - RN.DECK_DEPTH),
                             ('decks trimmed at the buildings\' bodies (review r2, finding 3): %s m2' % body_cut) + ('; Terminal 2: the roadway is cut at the T2 body until the domestic group moves the T2 '
                             'landside face (NAIP 2024: the departures roadway is open to the sky between the modelled T2 west wall and the curb canopy)' if any('T2' in k for k in body_cut) else
                             ' (T1 / T3 only: their curb-side shells; the T2 cut lifted after the domestic group moved the T2 landside face, close-out round 3)')]
                            + ['stacked pairs kept whole under an upper deck with less than %.1f m (a cut would split the lower deck or leave < lanes x %.1f m; fix 2, verifier v1): %s'
                               % (RN.CLEAR_MIN, MIN_LANE_W, '; '.join('%s under %s, %.2f m' % (r['lower'], r['upper'], r['clearance_if_kept_m']) for r in stk_recs if r.get('refused')) or 'none'),
                               'stacked cuts made although they narrow the lower deck (the decks would clash, < %.1f m): %s' % (KEEP_CLEAR, '; '.join('%s under %s: %s' % (r['lower'], r['upper'], r['narrowed'])
                               for r in stk_recs if r.get('narrowed')) or 'none')],
                 closeout_r4=dict(rule='deck edges: inner where a neighbour within %s m (LOD0/1/2) has its top within %.2f m there (else fascia + parapet on both: a median '
                                       'barrier); joint wedges, slit / gore fill, junction voids, width tapers and the connected-deck blend close the slits whose sides r22 '
                                       'built as parapets across the lanes (the round-3 verifier\'s major)' % (list(INNER_GAP.values()), STEP_TOL),
                                  in_carriageway_parapet_m=pchk.get('approx_m'), in_carriageway_clusters=pchk.get('clusters'), joint_wedges=dict((k, jw[k]) for k in ('joints', 'filled', 'area_m2', 'tapers', 'taper_m2')),
                                  slits=dict((k, jw['slits'][k]) for k in ('pairs', 'area_m2', 'voids', 'voids_m2')), edges_lod0={k: v for k, v in edge.items() if k != 'step_face_top'},
                                  pieces_without_deck=[e['id'] for e in empty],
                                  fix_round_2=dict(blend=blend, mesh_grade_max_pct=gchk.get('max_pct'), mesh_grade_over_pct_m2=gchk.get('over_pct_m2'),
                                                   mesh_grade_over_10_pct_by_unit={u: d['over_10_pct_m2'] for u, d in gchk.get('by_unit', {}).items()},
                                                   columns_meeting_soffit='%d of %d' % (cchk['meeting_soffit'], cchk['columns'])),
                                  closeout_r5=dict(soffit_closure={k: schk.get(k) for k in ('boundary_m', 'face_m', 'soffit_continues_m', 'open_into_hollow_m', 'open_other_m')},
                                                   under_joint_m=edge.get('under_joint_m'), under_joint_to_grade_m=edge.get('under_joint_to_grade_m'),
                                                   under_joint_unresolved_m=edge.get('under_joint_unresolved_m'),
                                                   mesh_folds=gchk.get('folds'), fold_gate=gchk.get('fold_gate'))),
                 verification=stats)
    BI.merge_manifest(entry, key='roadways')
    open(os.path.join(OUTD, 'roadways_build.log'), 'w').write('\n'.join(lines) + '\n')
    json.dump(dict(stats=stats, columns=[dict(unit=c['unit'], xz=[round(float(v), 2) for v in c['xz']], soffit=round(c['soffit'], 2), way=c['way']) for c in cols],
                   pieces=[dict(id=p['id'], src=p['src'], unit=p['unit'], anchor=p['anchor'], w=p['w'], lanes=p['lanes'], h=[round(p['hmin'], 2), round(p['hmax'], 2)], asset_cut_m2=p['asset_cut_m2'], cut_by=p['cut_by'], area_m2=round(p['geom'].area, 1)) for p in P]),
              open(os.path.join(OUTD, 'roadways_build.json'), 'w'), indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
