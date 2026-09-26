"""Physical plausibility checks of data/sfo_stands.json (rewritten in review rounds 1 and 2, 24 Sep 2026).

Aircraft geometry is the APP's (review round 2): tools/stands/geom.py reads js/aircraft/types.js (dump_types.mjs) -
the collision planform of js/live/ground.js inside() (fuselage rectangle, swept wing trapezoid, tailplane), the door
table and dock2 - and iterates over every ICAO designator the app knows. Two views are checked:

  DATA   what the data specifies: every type the stand accepts (class limits, span_max / len_max, types_ok whitelist),
         each at its per-family stop point (type_stops, ADS-B evidence) - ISSUES here are defects of the data.
  APP    what js/live/traffic.js does with it (review round 4: the working tree of 25 Sep 2026). For SFO's own allocation
         standFits(g, T, icao, strict=false) ignores types_ok, so every type within the class limits / span_max / len_max
         (types.js spans, no winglets) can be put there; the A380 / 747-8 clause applies only on `a380` stands; aircraft
         are placed at their per-family stop (stopAlong: type_stops). A pose short of the stop that would touch an occupied
         neighbour is sent to the stop at runtime (updatePark: tr.shortBlocked, set by GroundPhysics), so the old
         'stop-short' combinations are no longer checked. Bridges as rendered by js/live/gates.js (derived rotundas / rest
         poses) are NOT modelled here (docs/requests/static_geometry_round3.md / round4.md: gates.js must use the data
         geometry checked below).

DATA checks
  1. aircraft vs building (SFO Museum outlines): ISSUE when an envelope overlaps (> 0.5 m2) or comes within 2.0 m of
     the building (review round 2: F16 / F17 noses touched the Boarding Area F facade); NOTE within 3.5 m.
  2. pavement: ISSUE when > 3 % of the envelope is unpaved in NAIP 2024 (vegetation class).
  3. aircraft vs aircraft, every pair within 170 m that is not mutually exclusive ('excl'): ISSUE when the envelopes
     come within 3.0 m (physical minimum used here); NOTE below the ICAO stand clearance (Annex 14 3.13.6 / Doc 9157
     Part 2 s.3.4.4: code A/B 3 m, C 4.5 m, D-F 7.5 m; reducible for D-F only at the nose / with VDGS azimuth guidance).
  4. bridges (data geometry: OSM fixed walkway, rotunda, cab; the builder's stow pose; Oshkosh AeroTech Jetway sell
     sheet 2025: extension 9.846-41.381 m rotunda centre -> cab pivot, pivot -> door 2.4 m (geom.PIVOT_TO_DOOR),
     cab 92.5 deg standard / 150 deg optional, rotunda swing +-87.5 deg):
     a. docking: L1 -> door 1, L2 -> the type's dock2 (types.js; None = does not dock), the aircraft at its per-family
        stop; the cab faces the door, so the cab pivot is 2.4 m out from the door along the fuselage normal and the
        tunnel runs rotunda -> pivot: extension outside 9.846-41.381 m -> ISSUE for observed types (obs_types) when
        more than 1.0 m outside (WARN within 1.0 m: stop-point / rotunda uncertainty), NOTE for the other accepted.
     b. cab turn beyond 150 deg -> ISSUE (observed) / NOTE; beyond 92.5 deg -> WARN.
     c. rotunda swing (review round 4; sell sheet 'Rotunda swing 175 deg (87.5 cw / 87.5 ccw of centerline)'): the
        rotunda's centreline is set at installation and not published, so the test is neutral-axis-free - the rest pose
        and the docked pose of every type the bridge docks must fit into ONE 175 deg arc (else ISSUE), and that arc must
        not contain the direction back along the bridge's own fixed walkway +-25 deg (the tunnel would have to swing
        through the walkway: ISSUE). A docked or rest tunnel more than 87.5 deg from the walkway direction is reported
        once per bridge as a NOTE: at the F pier the walkways run along the facade and both the OSM / NAIP parked tunnels
        (79-95 deg) and the dockings SFO operates (123-138 deg) lie beyond 87.5 deg, so the walkway is not the centreline
        there. The docked tunnel physically crossing its own fixed walkway -> ISSUE (observed types) / NOTE.
     d. docked tunnel over the docking type's own planform, docked tunnel + cab over another non-exclusive stand's
        envelope: ISSUE.
     e. rest (stow) pose vs the envelope of every stand within 150 m (own, alternative and exclusive included) -> ISSUE;
        no stow pose -> ISSUE; rest pose over its own fixed walkway (outside the drum + 1 m) -> ISSUE (review round 4);
        rest pose closer than the ICAO clearance to the wings / engines / tailplane of an OBSERVED type -> WARN (listed
        evidence conflict); fixed walkway + rotunda inside an aircraft: ISSUE for observed types, NOTE otherwise.
     g. fixed walkway + rotunda vs the wings / engines / tailplane of every type the stand accepts on SFO's path (class
        limits), at its stop (review round 4): code A-C closer than the ICAO clearance (3.0 / 4.5 m; no relief for C)
        -> ISSUE; D-F closer than 3.0 m -> ISSUE, closer than 7.5 m -> WARN (ICAO 3.4.4(b): reducible over the part of
        the stand with VDGS azimuth guidance; SFO's VDGS coverage is not verified).
     h. extension (review round 4): beyond the longest Oshkosh unit (41.381 m) but within TK Elevator's published apron-
        drive range (14-50 m, reference points not stated) -> WARN 'manufacturer-dependent' (the per-bridge models are
        an Oshkosh-only inference); below 9.846 m (shorter than any published unit) stays an ISSUE.
     f. bridge vs bridge (fixed parts, rest poses, docked bridges of non-exclusive stands) -> ISSUE; rotundas closer
        than 4.9 m -> NOTE with the data's rotunda_max_r.
Exit status 1 if there are DATA ISSUES.  Usage: python3 tools/stands/check_stands.py [-q] [--no-app]
"""
import json, math, os, sys
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from common import ROOT, load_airport
import build_stands as BS
import geom as GM

TK_MAX = 50.0   # m, TK Elevator apron-drive bridges: "range of 14 to 50 meters" (product page; reference points not stated)


def swing_arc(angs, back, margin=25.0):
    """(width of the smallest arc covering all directions (deg), whether `back` +-margin lies inside that arc)"""
    if not angs: return 0.0, False
    A = sorted(a % 360 for a in angs)
    gaps = [(A[(i + 1) % len(A)] - A[i]) % 360 for i in range(len(A))] if len(A) > 1 else [360.0]
    i = max(range(len(gaps)), key=lambda k: gaps[k]); start = A[(i + 1) % len(A)]; width = 360.0 - gaps[i]
    if back is None: return width, False
    rel = (back - start) % 360
    return width, (rel <= width + margin or rel >= 360 - margin)


def obs_set(s):
    return set(GM.ALIAS.get(t, t) for t in s.get('obs_types') or [])


def main(quiet=False, app=True):
    d = json.load(open(os.path.join(ROOT, 'data', 'sfo_stands.json')))
    S = d['stands']; SN = {s['name']: s for s in S}
    D = load_airport()
    bld = unary_union([Polygon(p[0], p[1:]).buffer(0) for p in list(D['terminalComplex']) + [q for b in D['boardingAreas'] for q in b['polys']]])
    import cv2, numpy as np, shapely
    from common import Naip
    N = Naip()
    def unpaved_frac(poly):
        x0, z0, x1, z1 = poly.bounds
        im, (c0, r0) = N.crop(x0, z0, x1, z1)
        hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.int32)
        H, Sa, V = hsv[..., 0] * 2, hsv[..., 1] / 255.0, hsv[..., 2]
        bgr = im.astype(np.int32)
        bad = (H >= 50) & (H <= 170) & (Sa > 0.18) & (V > 40) & (bgr[..., 1] > bgr[..., 2] + 5) & ~((H >= 140) & (V > 150))  # green paint is paved
        cols, rows = np.meshgrid(np.arange(im.shape[1]) + c0, np.arange(im.shape[0]) + r0)
        X, Z = N.world(cols, rows)
        inside = shapely.contains_xy(poly, X, Z)
        return float(bad[inside].mean()) if inside.any() else 0.0
    ENV = {s['name']: GM.stand_env(s) for s in S}
    issues, notes, warns, app_issues = [], [], [], []
    for s in S:
        p = ENV[s['name']]
        ov = p.intersection(bld).area; db = p.distance(bld)
        if ov > 0.5: issues.append((s['name'], 'aircraft envelope overlaps the building %.1f m2' % ov))
        elif db < 2.0: issues.append((s['name'], 'aircraft envelope %.2f m from the building (< 2.0 m)' % db))
        elif db < 3.5: notes.append((s['name'], 'aircraft envelope %.1f m from the building' % db))
        off = unpaved_frac(p)
        if off > 0.03: issues.append((s['name'], 'aircraft envelope %.0f %% over unpaved ground (NAIP)' % (100 * off)))
    n_pairs = 0; near = []
    for i, a in enumerate(S):
        for b in S[i + 1:]:
            if math.dist(a['nose'], b['nose']) > 170: continue
            near.append((a, b))
            if b['name'] in a.get('excl', []): continue
            n_pairs += 1
            dd = ENV[a['name']].distance(ENV[b['name']])
            need = max(BS.icao_clear(max(BS.REF[t]['span'] for t in GM.accepted_types(x))) for x in (a, b))
            if dd < 3.0: issues.append((a['name'] + '|' + b['name'], 'PHYSICAL: clearance %.1f m < 3 m' % dd))
            elif dd < need: notes.append((a['name'] + '|' + b['name'], 'clearance %.1f m < ICAO %.1f m%s' % (dd, need, ' (types_ok / type_stops)' if (a.get('types_ok') or b.get('types_ok')) else '')))
    # ---------------------------------------------------------------- bridges
    allb = [(s, b) for s in S for b in s['bridges'] + s.get('bridges_upper', [])]
    def rot_r(b): return max(0.01, b['rotunda_max_r']) if b.get('rotunda_max_r') is not None else GM.ROT_R
    fixed = {}
    for s, b in allb:
        wl, rot, _ = GM.bridge_parts(b, b['cab'])
        if b.get('rotunda'):
            rot = Point(b['rotunda']).buffer(rot_r(b))
            if rot_r(b) < 1.2: issues.append((s['name'], 'bridge %s L%d: rotunda on another fixed walkway (room for r = %.2f m only)' % (b['gate'], b['door'], b.get('rotunda_max_r'))))
        fixed[id(b)] = unary_union([wl, rot])
    rest = {}
    for s, b in allb:
        if not b.get('stow'): issues.append((s['name'], 'bridge %s: no rest (stow) pose' % b['osm_id'])); continue
        rest[id(b)] = GM.bridge_parts(b, b['stow'])[2]
    docked = {}; dock_fp = {}
    CW = 1 if (d.get('cab_convention') or {}).get('cw_is', 'clockwise').startswith('clockwise') else -1
    sharers = {}
    for o in S:
        if o.get('shares_bridges_of'): sharers.setdefault(o['shares_bridges_of'], []).append(o)
    for s, b in allb:
        if b['door'] == 3: continue            # A380 upper deck: not docked by the app model (bridges_upper)
        pv = b.get('rotunda') or b['attach']
        e0, e1 = b.get('ext_range') or (GM.EXT_MIN, GM.EXT_MAX)
        out_ = set(b.get('dock_types_out') or [])
        # walkway direction into the rotunda (for the swing check)
        wk = [tuple(q) for q in b.get('walk') or [] if math.dist(q, pv) > 1.0]
        wdir = None
        if b.get('rotunda') and wk:
            L_ = math.dist(wk[-1], pv); wdir = ((pv[0] - wk[-1][0]) / L_, (pv[1] - wk[-1][1]) / L_)
        own_walk = GM.bridge_parts(b, b['cab'])[0].difference(Point(pv).buffer(rot_r(b) + 0.5))
        worst = None; dock_fp[id(b)] = {}; dirs = []; swmax = 0.0
        # the stand itself and the alternative positions that use its bridges (B5S -> B5 ...)
        for so in [s] + sharers.get(s['name'], []):
            obs = obs_set(so); rt = GM.rv(so['hdg'])
            for t in GM.accepted_types(so):
                k = GM.dock_door(t, b['door'])
                if k is None: continue
                nz = GM.nose_for(so, t)
                dp = GM.door(nz, so['hdg'], t, k)
                # docked, the cab faces the door squarely: the cab pivot sits PIVOT_TO_DOOR out from the door along the
                # fuselage normal (left side: -right), and the tunnel runs from the rotunda to that pivot
                cabp = (dp[0] - rt[0] * GM.PIVOT_TO_DOOR, dp[1] - rt[1] * GM.PIVOT_TO_DOOR)
                ext = math.dist(pv, cabp)
                u = ((cabp[0] - pv[0]) / max(ext, 1e-6), (cabp[1] - pv[1]) / max(ext, 1e-6))
                tag = 'bridge %s L%d / %s%s' % (b['gate'], b['door'], t, '' if so is s else ' on ' + so['name'])
                bucket = issues if t in obs else notes
                # review round 3: the bridge's own model range (ext_range), not 9.846-41.381 m; also without a rotunda
                if not (e0 - 1.0 <= ext <= e1 + 1.0):
                    # static fix-up: a documented decision that this bridge does not dock the type (stand_table.DOCK_OUT_DECIDED)
                    if t in (b.get('dock_out_why') or {}):
                        notes.append((s['name'], '%s: extension %.1f m - not docked by decision (%s)' % (tag, ext, b['dock_out_why'][t]))); continue
                    if t in obs and GM.EXT_MAX + 1.0 < ext <= TK_MAX:
                        warns.append((s['name'], '%s: extension %.1f m beyond every Oshkosh unit (41.4 m) - manufacturer-dependent (TK Elevator apron drives '
                                                 'reach 50 m, reference points not stated; SFO\'s bridge makers are not published)' % (tag, ext)))
                    elif t in obs: issues.append((s['name'], '%s: extension %.1f m outside the bridge model range %.1f-%.1f m (%s)' % (tag, ext, e0, e1, b.get('model') or 'no single model')))
                    elif t not in out_: notes.append((s['name'], '%s: extension %.1f m outside %.1f-%.1f m but not in dock_types_out' % (tag, ext, e0, e1)))
                    continue                    # it does not dock this type: the bridge stays at rest (checked below)
                if not (e0 <= ext <= e1) and t in obs:
                    warns.append((s['name'], '%s: extension %.1f m within 1.0 m outside %.1f-%.1f m (stop / rotunda uncertainty)' % (tag, ext, e0, e1)))
                # cab turn, signed (review round 3): 92.5 cw / 32.5 ccw standard, +-92.5 with the optional cab
                ang = CW * GM.angle(u, rt)
                opt = 'optional' in (b.get('cab_option') or '')
                if abs(ang) > GM.CAB_ROT_OPT: bucket.append((s['name'], '%s: cab turn %.0f deg > %.0f' % (tag, ang, GM.CAB_ROT_OPT)))
                elif not (-GM.CAB_CCW <= ang <= GM.CAB_CW) and not (opt and abs(ang) <= GM.CAB_OPT_HALF):
                    (warns if t in obs else notes).append((s['name'], '%s: cab turn %+.0f deg outside the standard %.1f cw / %.1f ccw (cab_option %s)' % (tag, ang, GM.CAB_CW, GM.CAB_CCW, b.get('cab_option'))))
                if b.get('rotunda'):
                    dirs.append(math.degrees(math.atan2(u[1], u[0])))
                    if wdir: swmax = max(swmax, abs(GM.angle(wdir, u)))
                tw = LineString([pv, cabp]).buffer(GM.TUN_W / 2, cap_style=2).difference(Point(pv).buffer(rot_r(b) + 0.5)).intersection(own_walk).area
                if tw > 0.5: bucket.append((s['name'], '%s: docked tunnel crosses its own fixed walkway %.1f m2' % (tag, tw)))
                wl, rot, tc = GM.bridge_parts(b, cabp)
                tun = LineString([pv, cabp]).buffer(GM.TUN_W / 2, cap_style=2).difference(Point(pv).buffer(rot_r(b)))
                own = GM.planform(nz, so['hdg'], t, visual=True)
                ov = tun.intersection(own).area
                if ov > 0.5: bucket.append((s['name'], '%s: docked tunnel over its own aircraft %.1f m2' % (tag, ov)))
                # review round 3: docked tunnel + cab inside the building (B2, A10, B10 were 1.1-2.2 m2)
                ob_g = tc.difference(Point(pv).buffer(rot_r(b) + 0.3)).intersection(bld); ob_ = ob_g.area
                # the SFO Museum outline is good to ~+-5 m (NAIP lean, review round 3): a graze under 1.5 m2 within 4 m of the
                # rotunda is a NOTE, anything larger or further out an ISSUE (observed types)
                if ob_ > 0.5:
                    near_rot = ob_ < 1.5 and ob_g.hausdorff_distance(Point(pv)) < rot_r(b) + 4.0
                    (notes if near_rot else bucket).append((s['name'], '%s: docked tunnel / cab inside the building %.1f m2%s' % (tag, ob_, ' (graze next to the rotunda, within the outline accuracy)' if near_rot else '')))
                dock_fp[id(b)].setdefault(t, []).append(tc)
                if worst is None or ext > worst[0]: worst = (ext, tc)
        dock_fp[id(b)] = {t: unary_union(v) for t, v in dock_fp[id(b)].items()}
        if worst: docked[id(b)] = worst[1]
        # review round 4: neutral-axis-free rotunda swing test (rest + every docking within ONE 175 deg arc, not through the
        # walkway); the 87.5 deg-from-walkway figure is reported once per bridge as a NOTE
        if b.get('rotunda'):
            if b.get('stow'):
                dirs.append(math.degrees(math.atan2(b['stow'][1] - pv[1], b['stow'][0] - pv[0])))
                if wdir:
                    us = ((b['stow'][0] - pv[0]), (b['stow'][1] - pv[1])); swmax = max(swmax, abs(GM.angle(wdir, us)))
            back = math.degrees(math.atan2(-wdir[1], -wdir[0])) if wdir else None
            width, inside = swing_arc(dirs, back)
            if width > 2 * GM.ROT_SWING + 0.05: issues.append((s['name'], 'bridge %s L%d: rest + docked tunnel directions span %.0f deg > the 175 deg rotunda swing' % (b['gate'], b['door'], width)))
            elif inside: issues.append((s['name'], 'bridge %s L%d: the tunnel would swing through its own fixed walkway between rest and docked' % (b['gate'], b['door'])))
            if swmax > GM.ROT_SWING: notes.append((s['name'], 'bridge %s L%d: tunnel up to %.0f deg from the walkway direction (arc of all poses %.0f deg; the walkway is not the rotunda centreline here)' % (b['gate'], b['door'], swmax, width)))
        for o in S:
            if o is s or o['name'] in s.get('excl', []) or math.dist(o['nose'], s['nose']) > 150: continue
            if id(b) in docked and docked[id(b)].intersection(ENV[o['name']]).area > 0.5:
                issues.append((s['name'], 'bridge %s L%d docked crosses the aircraft at %s' % (b['gate'], b['door'], o['name'])))
    for s, b in allb:
        pv = b.get('rotunda') or b['attach']
        for o in S:
            if math.dist(o['nose'], pv) > 150: continue
            eo = unary_union([GM.planform(GM.nose_for(o, t), o['hdg'], t) for t in (obs_set(o) & set(GM.APP))]) if obs_set(o) & set(GM.APP) else ENV[o['name']]
            a_ = fixed[id(b)].intersection(eo).area
            if a_ > 0.3: issues.append((s['name'], 'bridge %s L%d fixed walkway / rotunda inside the aircraft of %s (observed types, %.1f m2)' % (b['gate'], b['door'], o['name'], a_)))
            elif fixed[id(b)].intersection(ENV[o['name']]).area > 0.3:
                notes.append((s['name'], 'bridge %s L%d fixed walkway / rotunda inside the accepted-type envelope of %s' % (b['gate'], b['door'], o['name'])))
        # review round 4 (g): fixed walkway + rotunda vs the wings / engines / tailplane of every type on SFO's path
        for o in S:
            if math.dist(o['nose'], pv) > 120: continue
            worst_ = None
            for t in GM.accepted_types(dict(o, types_ok=None)):
                d_ = GM.wings(GM.nose_for(o, t), o['hdg'], t).distance(fixed[id(b)])
                need_ = GM.icao_clear(GM.APP[t]['span'])
                if d_ < need_ and (worst_ is None or d_ - need_ < worst_[0] - worst_[1]): worst_ = (d_, need_, t)
            if worst_:
                d_, need_, t = worst_
                bad = d_ < (need_ if need_ < 7.5 else 3.0)
                (issues if bad else warns).append((s['name'], 'bridge %s L%d fixed walkway / rotunda %.1f m from the wing / engine / tailplane of %s at %s (ICAO %.1f m%s)' % (
                    b['gate'], b['door'], d_, t, o['name'], need_, '' if bad else '; D-F: reducible with VDGS azimuth guidance, not verified')))
        if id(b) in rest:
            rb = rest[id(b)].difference(Point(pv).buffer(rot_r(b) + 0.3))
            ow = GM.bridge_parts(b, b['cab'])[0].difference(Point(pv).buffer(max(rot_r(b), GM.ROT_R) + 1.0)).intersection(rb).area
            if ow > 0.5: issues.append((s['name'], 'bridge %s L%d at rest lies on its own fixed walkway (%.1f m2)' % (b['gate'], b['door'], ow)))
            wo = [(GM.wings(GM.nose_for(o, t), o['hdg'], t).distance(rb), GM.icao_clear(GM.APP[t]['span']), t, o['name'])
                  for o in S if math.dist(o['nose'], pv) < 150 for t in obs_set(o) & set(GM.APP)]
            wo = [x for x in wo if x[0] < x[1]]
            if wo:
                x = min(wo, key=lambda x: x[0] - x[1])
                warns.append((s['name'], 'bridge %s L%d at rest %.1f m from the wing / engine / tailplane of %s (observed) at %s (ICAO %.1f m; evidence conflict)' % (b['gate'], b['door'], x[0], x[2], x[3], x[1])))
            for o in S:
                if math.dist(o['nose'], pv) > 150: continue
                a_ = rb.intersection(ENV[o['name']]).area
                if a_ > 0.05: issues.append((s['name'], 'bridge %s L%d at rest overlaps the aircraft envelope of %s (%.1f m2)' % (b['gate'], b['door'], o['name'], a_)))
            # review round 3: the rest pose must be a length the bridge's model can retract to, and outside the building
            e0 = (b.get('ext_range') or (GM.EXT_MIN, 0))[0]; Ls = math.dist(pv, b['stow'])
            if Ls < e0 - 0.05: issues.append((s['name'], 'bridge %s L%d rest length %.1f m < the model\'s retraction %.1f m' % (b['gate'], b['door'], Ls, e0)))
            ab = rb.intersection(bld).area
            if ab > 0.3: issues.append((s['name'], 'bridge %s L%d at rest inside the building %.1f m2' % (b['gate'], b['door'], ab)))
            # review round 3: another bridge DOCKED while this one rests - a sibling for the types this one does not dock,
            # any bridge of another stand for every type it docks
            for so, ob in allb:
                if ob is b or id(ob) not in dock_fp or math.dist(ob.get('rotunda') or ob['attach'], pv) > 90: continue
                for t, g in dock_fp[id(ob)].items():
                    if so is s and b['door'] <= 2 and GM.dock_door(t, b['door']) is not None and t not in (b.get('dock_types_out') or []): continue
                    a_ = g.intersection(rb).area
                    if a_ > 0.5:
                        (issues if t in obs_set(so) else notes).append((s['name'], 'bridge %s L%d at rest is crossed by %s L%d docked to %s (%.1f m2)' % (b['gate'], b['door'], so['name'], ob['door'], t, a_)))
                        break
    # review round 3: two bridges of one stand docked to the same type must not overlap
    for s in S:
        bs = [b for b in s['bridges'] if id(b) in dock_fp]
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                for t in set(dock_fp[id(bs[i])]) & set(dock_fp[id(bs[j])]):
                    a_ = dock_fp[id(bs[i])][t].intersection(dock_fp[id(bs[j])][t]).area
                    if a_ > 0.5: (issues if t in obs_set(s) else notes).append((s['name'], 'L%d and L%d docked to %s overlap %.1f m2' % (bs[i]['door'], bs[j]['door'], t, a_)))
    for i in range(len(allb)):
        for j in range(i + 1, len(allb)):
            (sa, ba), (sb, bb) = allb[i], allb[j]
            pa = ba.get('rotunda') or ba['attach']; pb = bb.get('rotunda') or bb['attach']
            if math.dist(pa, pb) > 90: continue
            if ba.get('rotunda') and bb.get('rotunda') and math.dist(pa, pb) < 2 * GM.ROT_R:
                notes.append((sa['name'] + '|' + sb['name'], 'rotundas %.1f m apart (< 4.9 m; rotunda_max_r %.2f / %.2f m)' % (math.dist(pa, pb), rot_r(ba), rot_r(bb))))
            ov = fixed[id(ba)].intersection(fixed[id(bb)]).area
            shared = ba['attach'] == bb['attach']      # branches of one walkway share the building end
            if ov > 0.5 and not shared:
                wa = GM.bridge_parts(ba, ba['cab'])[0]; wb = GM.bridge_parts(bb, bb['cab'])[0]
                rots = [Point(x['rotunda']).buffer(rot_r(x)) for x in (ba, bb) if x.get('rotunda')]
                rot_ov = sum(r.intersection(fixed[id(y)]).area for r, y in zip(rots, (bb, ba)))
                if sa is sb and rot_ov < 0.1 and wa.intersection(wb).area >= ov - 0.1:
                    notes.append((sa['name'], 'walkways L%d / L%d side by side (double corridor, %.1f m2 shared)' % (ba['door'], bb['door'], ov)))
                else: issues.append((sa['name'] + '|' + sb['name'], 'fixed walkways / rotundas overlap %.1f m2' % ov))
            if id(ba) in rest and id(bb) in rest:
                ov = rest[id(ba)].intersection(rest[id(bb)]).area
                if ov > 0.5: issues.append((sa['name'] + '|' + sb['name'], 'bridges at rest overlap %.1f m2' % ov))
                elif not shared:
                    dr = rest[id(ba)].difference(Point(pa).buffer(rot_r(ba) + 0.3)).distance(rest[id(bb)].difference(Point(pb).buffer(rot_r(bb) + 0.3)))
                    if dr < 1.0: notes.append((sa['name'] + '|' + sb['name'], 'rest poses %.2f m apart (< 1.0 m)' % dr))
            for x, y in ((ba, bb), (bb, ba)):
                if shared: break
                if id(x) in rest and fixed[id(y)].intersection(rest[id(x)].difference(Point(x.get('rotunda') or x['attach']).buffer(rot_r(x) + 0.3))).area > 0.5:
                    issues.append((sa['name'] + '|' + sb['name'], 'bridge at rest overlaps the fixed walkway / rotunda of another'))
            if sa is not sb and sb['name'] not in sa.get('excl', []) and id(ba) in docked and id(bb) in docked:
                if docked[id(ba)].intersection(docked[id(bb)]).area > 0.5: issues.append((sa['name'] + '|' + sb['name'], 'docked bridges overlap'))
    # ---------------------------------------------------------------- floodlight masts (review round 3)
    # data/sfo_details.json masts (OSM, observed; moved off the rendered building outline by build_airfield_details.py):
    # the pole + foundation (r 0.9 m, js/live/items.js) must stay clear of every aircraft a stand accepts, every bridge
    # (fixed parts, rest pose, docked to an accepted type) and the buildings
    DT = json.load(open(os.path.join(ROOT, 'data', 'sfo_details.json')))
    n_m = 0
    for mx, mz in DT.get('masts', []):
        pole = Point(mx, mz).buffer(0.9); n_m += 1; tag = 'mast (%.1f, %.1f)' % (mx, mz)
        if pole.intersection(bld).area > 0.05: issues.append((tag, 'inside the building outline'))
        for o in S:
            if math.dist(o['nose'], (mx, mz)) > 150: continue
            dd = ENV[o['name']].distance(pole)
            if dd <= 0: issues.append((tag, 'inside the aircraft envelope of %s' % o['name']))
            elif dd < 2.0: warns.append((tag, '%.1f m from the aircraft envelope of %s' % (dd, o['name'])))
        for so, b in allb:
            if math.dist(b.get('rotunda') or b['attach'], (mx, mz)) > 90: continue
            if fixed[id(b)].intersects(pole): issues.append((tag, 'on the fixed walkway / rotunda of %s L%d' % (so['name'], b['door'])))
            if id(b) in rest and rest[id(b)].intersects(pole): issues.append((tag, 'under the resting bridge %s L%d' % (so['name'], b['door'])))
            for t, g in dock_fp.get(id(b), {}).items():
                if g.intersects(pole):
                    (issues if t in obs_set(so) else notes).append((tag, 'crossed by %s L%d docked to %s' % (so['name'], b['door'], t))); break
    print('masts checked:', n_m)
    # ---------------------------------------------------------------- APP view (js/live/traffic.js as it is today)
    if app:
        # SFO's allocation path (standFits strict=false): class limits / span_max / len_max, no types_ok, per-family stops
        EA = {s['name']: GM.stand_env(s, app_rule=True, per_type=True) for s in S}
        for a, b in near:
            if b['name'] in a.get('excl', []): continue
            dd = EA[a['name']].distance(EA[b['name']])
            if dd < 3.0:
                tt = 'types_ok bypassed on SFO\'s path' if (a.get('types_ok') or b.get('types_ok')) and ENV[a['name']].distance(ENV[b['name']]) >= 3.0 else 'class limits'
                app_issues.append((a['name'] + '|' + b['name'], 'app (SFO allocation path) can park aircraft %.1f m apart (< 3 m; %s)' % (dd, tt)))
    print('%d stands, %d bridges (%d upper deck), %d aircraft pairs checked (excl pairs skipped); aircraft geometry: js/aircraft/types.js (%d types)' % (
        len(S), sum(len(s['bridges']) for s in S), sum(len(s.get('bridges_upper', [])) for s in S), n_pairs, len(GM.APP)))
    if not quiet:
        for n in notes: print('  note:', *n)
        for w in warns: print('  WARN:', *w)
    print('WARNINGS:', len(warns))
    if app:
        print('APP ISSUES (current js/live/traffic.js behaviour; see docs/requests/static_geometry_round4.md):', len(app_issues))
        for x in app_issues: print('   ', *x)
    print('ISSUES:', len(issues))
    for x in issues: print('  ', *x)
    return issues


if __name__ == '__main__':
    sys.exit(1 if main('-q' in sys.argv, '--no-app' not in sys.argv) else 0)
