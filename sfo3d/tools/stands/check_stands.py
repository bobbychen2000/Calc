"""Physical plausibility checks of data/sfo_stands.json (rewritten in review rounds 1 and 2, 24 Sep 2026).

Aircraft geometry is the APP's (review round 2): tools/stands/geom.py reads js/aircraft/types.js (dump_types.mjs) -
the collision planform of js/live/ground.js inside() (fuselage rectangle, swept wing trapezoid, tailplane), the door
table and dock2 - and iterates over every ICAO designator the app knows. Two views are checked:

  DATA   what the data specifies: every type the stand accepts (class limits, span_max / len_max, types_ok whitelist),
         each at its per-family stop point (type_stops, ADS-B evidence) - ISSUES here are defects of the data.
  APP    what js/live/traffic.js does with it today (its standFits incl. the 'maxSpan >= 64 -> span <= 80' clause, no
         types_ok, one nose point for every type, parking up to 25 m short of the stop, traffic.js:693-698). APP
         findings are listed separately; they go away only with the changes requested in
         docs/requests/static_geometry_round2.md. Bridges as rendered by js/live/gates.js (derived rotundas / rest poses)
         are NOT modelled here (the request asks gates.js to use the data geometry checked below).

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
        stop: extension outside 9.846-41.381 m -> ISSUE for observed types (obs_types), NOTE for the other accepted.
     b. cab turn beyond 150 deg -> ISSUE (observed) / NOTE; beyond 92.5 deg -> WARN.
     c. rotunda swing (review round 2): the docked tunnel physically crossing its own fixed walkway -> ISSUE (observed
        types) / NOTE; a tunnel more than 87.5 deg from the walkway direction -> NOTE only, because the rotunda's
        neutral axis is not known (at the F pier the fixed walkways run along the facade and NAIP shows the parked
        tunnels pointing away from it, i.e. the neutral axis is not the walkway direction there).
     d. docked tunnel over the docking type's own planform, docked tunnel + cab over another non-exclusive stand's
        envelope: ISSUE.
     e. rest (stow) pose vs the envelope of every stand within 150 m (own, alternative and exclusive included) -> ISSUE;
        no stow pose -> ISSUE; fixed walkway + rotunda inside an aircraft: ISSUE for observed types, NOTE otherwise.
     f. bridge vs bridge (fixed parts, rest poses, docked bridges of non-exclusive stands) -> ISSUE; rotundas closer
        than 4.9 m -> NOTE with the data's rotunda_max_r.
Exit status 1 if there are DATA ISSUES.  Usage: python3 tools/stands/check_stands.py [-q] [--no-app]
"""
import json, math, os, sys
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from shapely.affinity import translate
from common import ROOT, load_airport
import build_stands as BS
import geom as GM

SHIFTS = (0.0, -5.0, -10.0, -15.0, -20.0, -25.0)     # traffic.js updatePark noseAlong clamp -25..0 m


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
    docked = {}
    for s, b in allb:
        if b['door'] == 3: continue            # A380 upper deck: not docked by the app model (bridges_upper)
        pv = b.get('rotunda') or b['attach']
        obs = obs_set(s)
        rt = GM.rv(s['hdg'])
        # walkway direction into the rotunda (for the swing check)
        wk = [tuple(q) for q in b.get('walk') or [] if math.dist(q, pv) > 1.0]
        wdir = None
        if b.get('rotunda') and wk:
            L_ = math.dist(wk[-1], pv); wdir = ((pv[0] - wk[-1][0]) / L_, (pv[1] - wk[-1][1]) / L_)
        own_walk = GM.bridge_parts(b, b['cab'])[0].difference(Point(pv).buffer(rot_r(b) + 0.5))
        worst = None
        for t in GM.accepted_types(s):
            k = GM.dock_door(t, b['door'])
            if k is None: continue
            nz = GM.nose_for(s, t)
            dp = GM.door(nz, s['hdg'], t, k)
            L = math.dist(pv, dp); ext = L - GM.PIVOT_TO_DOOR
            u = ((dp[0] - pv[0]) / L, (dp[1] - pv[1]) / L)
            cabp = (dp[0] - u[0] * GM.PIVOT_TO_DOOR, dp[1] - u[1] * GM.PIVOT_TO_DOOR)
            ang = abs(GM.angle(u, rt))
            tag = 'bridge %s L%d / %s' % (b['gate'], b['door'], t)
            bucket = issues if t in obs else notes
            if b.get('rotunda') and not (GM.EXT_MIN <= ext <= GM.EXT_MAX):
                bucket.append((s['name'], '%s: extension %.1f m outside %.1f-%.1f m' % (tag, ext, GM.EXT_MIN, GM.EXT_MAX)))
            if ang > GM.CAB_ROT_OPT: bucket.append((s['name'], '%s: cab turn %.0f deg > %.0f' % (tag, ang, GM.CAB_ROT_OPT)))
            elif ang > GM.CAB_ROT_STD and t in obs: warns.append((s['name'], '%s: cab turn %.0f deg > standard %.1f (needs the optional cab)' % (tag, ang, GM.CAB_ROT_STD)))
            if wdir:
                # the rotunda's neutral axis is not known (it need not be the walkway direction: at the F pier the
                # walkways run along the facade and the imaged tunnels point away from it); a swing beyond 87.5 deg from
                # the walkway is a NOTE, the tunnel physically crossing its own fixed walkway an ISSUE (below)
                sw = abs(GM.angle(wdir, u))
                if sw > GM.ROT_SWING: notes.append((s['name'], '%s: tunnel %.0f deg from the walkway direction (> %.1f; rotunda neutral axis unknown)' % (tag, sw, GM.ROT_SWING)))
            tw = LineString([pv, cabp]).buffer(GM.TUN_W / 2, cap_style=2).difference(Point(pv).buffer(rot_r(b) + 0.5)).intersection(own_walk).area
            if tw > 0.5: bucket.append((s['name'], '%s: docked tunnel crosses its own fixed walkway %.1f m2' % (tag, tw)))
            wl, rot, tc = GM.bridge_parts(b, cabp)
            tun = LineString([pv, cabp]).buffer(GM.TUN_W / 2, cap_style=2).difference(Point(pv).buffer(rot_r(b)))
            own = GM.planform(nz, s['hdg'], t, visual=True)
            ov = tun.intersection(own).area
            if ov > 0.5: bucket.append((s['name'], '%s: docked tunnel over its own aircraft %.1f m2' % (tag, ov)))
            if worst is None or ext > worst[0]: worst = (ext, tc)
        if worst: docked[id(b)] = worst[1]
        for o in S:
            if o is s or o['name'] in s.get('excl', []) or math.dist(o['nose'], s['nose']) > 150: continue
            if id(b) in docked and docked[id(b)].intersection(ENV[o['name']]).area > 0.5:
                issues.append((s['name'], 'bridge %s L%d docked crosses the aircraft at %s' % (b['gate'], b['door'], o['name'])))
        for o in S:
            if math.dist(o['nose'], pv) > 150: continue
            eo = unary_union([GM.planform(GM.nose_for(o, t), o['hdg'], t) for t in (obs_set(o) & set(GM.APP))]) if obs_set(o) & set(GM.APP) else ENV[o['name']]
            a_ = fixed[id(b)].intersection(eo).area
            if a_ > 0.3: issues.append((s['name'], 'bridge %s L%d fixed walkway / rotunda inside the aircraft of %s (observed types, %.1f m2)' % (b['gate'], b['door'], o['name'], a_)))
            elif fixed[id(b)].intersection(ENV[o['name']]).area > 0.3:
                notes.append((s['name'], 'bridge %s L%d fixed walkway / rotunda inside the accepted-type envelope of %s' % (b['gate'], b['door'], o['name'])))
        if id(b) in rest:
            rb = rest[id(b)].difference(Point(pv).buffer(rot_r(b) + 0.3))
            for o in S:
                if math.dist(o['nose'], pv) > 150: continue
                a_ = rb.intersection(ENV[o['name']]).area
                if a_ > 0.05: issues.append((s['name'], 'bridge %s L%d at rest overlaps the aircraft envelope of %s (%.1f m2)' % (b['gate'], b['door'], o['name'], a_)))
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
            for x, y in ((ba, bb), (bb, ba)):
                if shared: break
                if id(x) in rest and fixed[id(y)].intersection(rest[id(x)].difference(Point(x.get('rotunda') or x['attach']).buffer(rot_r(x) + 0.3))).area > 0.5:
                    issues.append((sa['name'] + '|' + sb['name'], 'bridge at rest overlaps the fixed walkway / rotunda of another'))
            if sa is not sb and sb['name'] not in sa.get('excl', []) and id(ba) in docked and id(bb) in docked:
                if docked[id(ba)].intersection(docked[id(bb)]).area > 0.5: issues.append((sa['name'] + '|' + sb['name'], 'docked bridges overlap'))
    # ---------------------------------------------------------------- APP view (js/live/traffic.js as it is today)
    if app:
        EA = {s['name']: GM.stand_env(s, app_rule=True, per_type=False) for s in S}
        for a, b in near:
            if b['name'] in a.get('excl', []): continue
            dd = EA[a['name']].distance(EA[b['name']])
            if dd < 3.0:
                big = [t for t in GM.accepted_types(a, True) + GM.accepted_types(b, True) if GM.APP[t]['span'] > 65.5]
                why = 'oversize clause (A380 / 747-8 / 777-9)' if big and GM.stand_env(a, per_type=False).distance(GM.stand_env(b, per_type=False)) >= 3.0 else 'one nose point for every type / no types_ok'
                app_issues.append((a['name'] + '|' + b['name'], 'app parks: clearance %.1f m < 3 m (%s)' % (dd, why)))
                continue
            # stop-short (traffic.js parks up to 25 m short of the stop): every combination of along offsets
            ea, eb = GM.stand_env(a, app_rule=False, per_type=False), GM.stand_env(b, app_rule=False, per_type=False)
            fa, fb = GM.hv(a['hdg']), GM.hv(b['hdg']); worst = None
            for sa_ in SHIFTS:
                A_ = translate(ea, fa[0] * sa_, fa[1] * sa_)
                for sb_ in SHIFTS:
                    if sa_ == 0 and sb_ == 0: continue
                    d_ = A_.distance(translate(eb, fb[0] * sb_, fb[1] * sb_))
                    if worst is None or d_ < worst[0]: worst = (d_, sa_, sb_)
            if worst and worst[0] < 3.0:
                app_issues.append((a['name'] + '|' + b['name'], 'app stop-short: clearance %.1f m with %s at %+.0f m, %s at %+.0f m' % (worst[0], a['name'], worst[1], b['name'], worst[2])))
    print('%d stands, %d bridges (%d upper deck), %d aircraft pairs checked (excl pairs skipped); aircraft geometry: js/aircraft/types.js (%d types)' % (
        len(S), sum(len(s['bridges']) for s in S), sum(len(s.get('bridges_upper', [])) for s in S), n_pairs, len(GM.APP)))
    if not quiet:
        for n in notes: print('  note:', *n)
        for w in warns: print('  WARN:', *w)
    print('WARNINGS:', len(warns))
    if app:
        print('APP ISSUES (current js/live/traffic.js behaviour; need docs/requests/static_geometry_round2.md):', len(app_issues))
        for x in app_issues: print('   ', *x)
    print('ISSUES:', len(issues))
    for x in issues: print('  ', *x)
    return issues


if __name__ == '__main__':
    sys.exit(1 if main('-q' in sys.argv, '--no-app' not in sys.argv) else 0)
