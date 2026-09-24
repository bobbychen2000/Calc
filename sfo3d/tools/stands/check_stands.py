"""Physical plausibility checks of data/sfo_stands.json (rewritten after review round 1, 24 Sep 2026).

Aircraft are the ENVELOPE of every type the app accepts on a stand (tools/stands/geom.py accepted_types: the
js/live/traffic.js standFits rule with the stand's class, span_max and len_max; planforms from the manufacturers'
airport-planning dimensions, tools/models/check_dims.py REF), all with the nose at the stand's nose point - not one
reference type per class. Bridges use the data geometry (OSM fixed walkway, rotunda, cab; the builder's stow pose)
with buffered footprints (geom.py: walkway 2.6 m, rotunda 4.9 m or the data's rotunda_max_r, tunnel 2.9 m, cab
3.3 x 3.6 m) - the app's own derived bridge geometry is checked by the drawing workflow's audit, not here.

  1. aircraft vs building (SFO Museum outlines): ISSUE when the envelope overlaps by > 0.5 m2.
  2. pavement: ISSUE when > 3 % of the envelope is unpaved in NAIP 2024 (vegetation class).
  3. aircraft vs aircraft, every pair within 170 m that is not mutually exclusive ('excl'): ISSUE when the envelopes
     overlap, or when they come within 3.0 m and the pair is not a 'tight_with' pair (SFO plans both at once; the
     builder limited span / length); NOTE below the ICAO stand clearance (Doc 9157 Part 2 s.3.4.4: 3.0 / 4.5 / 7.5 m).
  4. bridges:
     a. reach, docked: rotunda centre -> cab pivot (door - 3.0 m) within 9.846-41.381 m (Oshkosh AeroTech Jetway
        sell sheet 2025) for every type SFO / ADS-B put on the stand (obs_types): ISSUE; other accepted types: NOTE.
        L1 docks door 1; L2 only a door ahead of the wing root (e.g. the 767's 2L at 15.96 m, never an aft door).
     b. cab angle between tunnel and the fuselage normal at the door: WARN beyond the standard 92.5 deg, ISSUE beyond
        150 deg (no cab option).
     c. docked tunnel + cab vs the aircraft of other non-exclusive stands, and the docked tunnel (without cab) vs the
        docking type's own planform: ISSUE (> 0.5 m2).
     d. rest (stow) pose (outside the rotunda) vs the envelope of EVERY stand within 150 m (own, alternative and
        exclusive stands included, their aircraft taxi in while the bridge rests): ISSUE on any overlap; ISSUE when no
        stow pose exists. Fixed walkway + rotunda vs aircraft: ISSUE for the observed types (obs_types), NOTE for the
        rest of the accepted envelope.
     e. bridge vs bridge: fixed parts (walkway + rotunda) and rest poses of all bridges, same stand included: ISSUE
        on overlap > 0.5 m2; docked bridges of different non-exclusive stands must not overlap; rotundas closer than
        4.9 m: NOTE (the data's rotunda_max_r says how small that rotunda must be).
Exit status 1 if there are ISSUEs.  Usage: python3 tools/stands/check_stands.py [-q]
"""
import json, math, os, sys
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from common import ROOT, load_airport
import build_stands as BS
import geom as GM


def main(quiet=False):
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
    issues, notes, warns = [], [], []
    for s in S:
        p = ENV[s['name']]
        ov = p.intersection(bld).area
        if ov > 0.5: issues.append((s['name'], 'aircraft envelope overlaps the building %.1f m2' % ov))
        off = unpaved_frac(p)
        if off > 0.03: issues.append((s['name'], 'aircraft envelope %.0f %% over unpaved ground (NAIP)' % (100 * off)))
    n_pairs = 0
    for i, a in enumerate(S):
        for b in S[i + 1:]:
            if math.dist(a['nose'], b['nose']) > 170 or b['name'] in a.get('excl', []): continue
            n_pairs += 1
            dd = ENV[a['name']].distance(ENV[b['name']])
            need = max(BS.icao_clear(max(BS.REF[t]['span'] for t in GM.accepted_types(x))) for x in (a, b))
            tight = b['name'] in a.get('tight_with', [])
            if dd <= 0: issues.append((a['name'] + '|' + b['name'], 'aircraft envelopes overlap'))
            elif dd < 3.0 and not tight: issues.append((a['name'] + '|' + b['name'], 'PHYSICAL: clearance %.1f m < 3 m' % dd))
            elif dd < need: notes.append((a['name'] + '|' + b['name'], 'clearance %.1f m < ICAO %.1f m%s' % (dd, need, ' (tight pair SFO plans at once)' if tight else '')))
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
        obs = set(BS.ALIAS_T.get(t, t) for t in s.get('obs_types') or [])
        f, rt = GM.hv(s['hdg']), GM.rv(s['hdg'])
        worst = None
        for t in GM.accepted_types(s):
            k = GM.dock_door(t, b['door'])
            if k is None: continue
            dp = GM.door(s['nose'], s['hdg'], t, k)
            L = math.dist(pv, dp); ext = L - 3.0
            u = ((dp[0] - pv[0]) / L, (dp[1] - pv[1]) / L)
            cabp = (dp[0] - u[0] * 3.0, dp[1] - u[1] * 3.0)
            ang = abs(GM.angle(u, rt))
            tag = 'bridge %s L%d / %s' % (b['gate'], b['door'], t)
            if b.get('rotunda') and not (GM.EXT_MIN <= ext <= GM.EXT_MAX):
                (issues if t in obs else notes).append((s['name'], '%s: extension %.1f m outside %.1f-%.1f m' % (tag, ext, GM.EXT_MIN, GM.EXT_MAX)))
            if ang > GM.CAB_ROT_OPT: (issues if t in obs else notes).append((s['name'], '%s: cab turn %.0f deg > %.0f' % (tag, ang, GM.CAB_ROT_OPT)))
            elif ang > GM.CAB_ROT_STD and t in obs: warns.append((s['name'], '%s: cab turn %.0f deg > standard %.1f (needs the optional cab)' % (tag, ang, GM.CAB_ROT_STD)))
            wl, rot, tc = GM.bridge_parts(b, cabp)
            tun = LineString([pv, cabp]).buffer(GM.TUN_W / 2, cap_style=2).difference(Point(pv).buffer(rot_r(b)))
            own = BS.planform(s['nose'], s['hdg'], BS.type_cls(t), t)
            ov = tun.intersection(own).area
            if ov > 0.5: (issues if t in obs else notes).append((s['name'], '%s: docked tunnel over its own aircraft %.1f m2' % (tag, ov)))
            if worst is None or ext > worst[0]: worst = (ext, tc)
        if worst: docked[id(b)] = worst[1]
        for o in S:
            if o is s or o['name'] in s.get('excl', []) or math.dist(o['nose'], s['nose']) > 150: continue
            if id(b) in docked and docked[id(b)].intersection(ENV[o['name']]).area > 0.5:
                issues.append((s['name'], 'bridge %s L%d docked crosses the aircraft at %s' % (b['gate'], b['door'], o['name'])))
        # fixed walkway + rotunda vs aircraft: ISSUE for the types SFO / ADS-B put on the stands, NOTE for the rest of
        # the accepted envelope (the app parks every type at one nose point; real stop marks differ per type)
        for o in S:
            if math.dist(o['nose'], pv) > 150: continue
            eo = GM.envelope(o['nose'], o['hdg'], [BS.ALIAS_T.get(t, t) for t in o.get('obs_types') or []] or GM.accepted_types(o))
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
                # two walkways of one stand side by side (attach points ~2.6 m apart, e.g. A11 L2 / upper deck) form one
                # double corridor: a NOTE when only the walkways (not the rotundas) touch
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
                if shared: break              # a branch leaves its parent's walkway at its own rotunda
                if id(x) in rest and fixed[id(y)].intersection(rest[id(x)].difference(Point(x.get('rotunda') or x['attach']).buffer(rot_r(x) + 0.3))).area > 0.5:
                    issues.append((sa['name'] + '|' + sb['name'], 'bridge at rest overlaps the fixed walkway / rotunda of another'))
            if sa is not sb and sb['name'] not in sa.get('excl', []) and id(ba) in docked and id(bb) in docked:
                if docked[id(ba)].intersection(docked[id(bb)]).area > 0.5: issues.append((sa['name'] + '|' + sb['name'], 'docked bridges overlap'))
    print('%d stands, %d bridges (%d upper deck), %d aircraft pairs checked (excl pairs skipped)' % (
        len(S), sum(len(s['bridges']) for s in S), sum(len(s.get('bridges_upper', [])) for s in S), n_pairs))
    if not quiet:
        for n in notes: print('  note:', *n)
        for w in warns: print('  WARN:', *w)
    print('WARNINGS:', len(warns))
    print('ISSUES:', len(issues))
    for x in issues: print('  ', *x)
    return issues


if __name__ == '__main__':
    sys.exit(1 if main('-q' in sys.argv) else 0)
