"""Build sha3d/data/sha_stands.json and sha_stands.js (window.SHA_STANDS): the Shanghai Hongqiao (ZSSS) stands, their
size classes, jet bridges, remote / contact status and push-back options. Task A2 of Phase 1. Deterministic:

    python3 -I sha3d/tools/airport/build_stands.py [SHA3D_DIR]

Schema: sfo3d data/sfo_stands.json where it fits (stands[]: name, alias, nose [x, z], hdg, cls, src, bridges[];
remote[]; unplaced[]; positions[]), plus per-field provenance (src / evidence) as in data/sha_airport.json.

Inputs (all committed; the build runs from a clean checkout):
  refs/cache/osm_pinned/zsss_osm_pinned.geojson  OSM (ODbL): 164 parking_position ref nodes, 461 lead-in ways,
                                                 58 aeroway=gate nodes, terminals, aprons   [tools/airport/stand_geom.py]
  data/sha_airport.json                          A1 geometry: taxiways / taxilanes, surfaces, buildings
  data/meas/stand_s2.json                        parked aircraft per stand, Sentinel-2 stack 2023-2026 [stand_s2.py]
  data/meas/stand_sar.json                       jet bridges on the Umbra SAR scene 2024-06-02 [stand_sar.py] (optional)
  AIP_* below                                    short cited facts, AIP (mirror) EFF 2026-07-08 (OD3); when the local
                                                 mirror text exists every fact is probed in it (checks_at_build)
The AIP stand table (span limits) and VDGS list are NOT inputs: they are read from refs/cache/aip/derived_aip_zsss/
(local only) after the build, for agreement COUNTS only (checks_at_build.aip_agreement); no per-stand AIP value is written.

Reference point ("nose"): the OSM ref node = the end of the painted lead-in line as mapped. It is used as the nose tip of
the class reference aircraft (inf). Check on the Sentinel-2 stack: narrow-body fits put the nose a median 1 m behind it
(10 m pixels, spread several metres): not applied.
Size class (sfo3d classes B / C / CL / D / E / EL / F, tools/airport/acplan.py): from our own evidence only:
  1. geometry: the largest class whose reference planform, placed on this stand and on each neighbour (the same class:
     symmetric assumption), keeps >= CLEAR m from every neighbour planform and from buildings (alternative positions of
     the same group excluded) and whose tail stays >= TAIL_CLEAR m from apron taxilane / taxiway centrelines;
  2. imagery: parked aircraft fitted on the Sentinel-2 stack (data/meas/stand_s2.json): a wide-body (template D or
     larger) on >= 2 dates makes the stand wide-capable (obs); the class is then raised to the largest class that is
     geometrically feasible with the neighbours at their own classes, capped one class above the largest observed
     template (templates under-size in pier shadows);
  3. pairs that still overlap are written as 'excl' (cannot be used at the same time at full size).
"""
import datetime
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'common'))
import frame as F  # noqa: E402
from acplan import CLASS_MAX, CLS_REF, ORDER, class_planform, icao_clearance  # noqa: E402
from stand_geom import OsmStands, from_local, hdiff, stand_sort_key, to_local  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

OUT_JSON = os.path.join(ROOT, 'data/sha_stands.json')
OUT_JS = os.path.join(ROOT, 'data/sha_stands.js')
S2_MEAS = os.path.join(ROOT, 'data/meas/stand_s2.json')
SAR_MEAS = os.path.join(ROOT, 'data/meas/stand_sar.json')
AIP_TXT = os.path.join(ROOT, 'refs/cache/aip/derived_aip_zsss/ad2_right_column.txt')
AIP_STANDS_LOCAL = os.path.join(ROOT, 'refs/cache/aip/derived_aip_zsss/stands.json')
R2 = lambda v: round(float(v), 2)  # noqa: E731

CLEAR = 2.5         # m between parked planforms: the tightest code-C rows at SHA (38.5 m stop spacing, 35.8 m spans)
#                     leave 2.7 m; ICAO Annex 14 3.13.6 asks 4.5 m (code C) / 7.5 m (D-F) [reported, not enforced]
BLD_CLEAR = 3.0     # m from buildings (inf)
TAIL_CLEAR = 15.0   # m from the tail to an apron taxilane / taxiway centreline (inf: < half a code-C span)
ALT_OVERLAP = 0.30  # two stands whose class-C planforms overlap by more than this fraction = alternative positions
WIDE_SPACING = 50.0   # m (inf)
REF_SPAN = {'B': 27.3, 'C': 35.8, 'CL': 41.1, 'D': 47.6, 'E': 60.3, 'EL': 64.8, 'F': 68.4}   # acplan.CLS_REF spans
WIDE = {'D', 'E', 'EL', 'F'}

# ------------------------------------------------------------------------------------------- AIP (mirror) short facts
# AD 2.20 (local traffic regulations), AIP China EFF 2026-07-08, read in the unofficial mirror (OD3: short facts only).
AIP_FACTS = {
    'taxi_in_push_back': dict(text='All stands are "Taxi in, Push back" (AD 2.20 3.2.6 column "Enter or Exit").',
                              probe='Taxi in, Push back'),
    'stand_count': dict(text='161 stand designators incl. 6 combined / alternative positions (AD 2.20 3.2.6, 3.2.7); '
                             'no stand coordinates are published.', probe='Usage mode of combined stands'),
    'combined': dict(text='Combined stands: 215+216 -> 216E, 219+220 -> 220E, 280+281 -> 281E, 412+413 -> 413E '
                          '(AD 2.20 3.2.7).', probe='3.2.7 Usage mode of combined stands'),
    'adjacent': dict(text='Simultaneous operation of two aircraft at adjacent stands is forbidden (entry, push-out, or '
                          'one in and one out) (AD 2.20 3.2.2.1).', probe='Simutaneous operation of two aircrafts at'),
    'stop_before_leadin': dict(text='Arrival aircraft stop on the taxiway before turning onto the stand lead-in line, '
                                    'then enter slowly (AD 2.20 3.2.2.2).', probe='on TWYs before turning into stands lead-in lines'),
    'marshaller': dict(text='Stand-off (remote) and VIP stands: marshaller guidance; listed stands have a visual '
                            'docking guidance system (AD 2.20 3.2.2.3).', probe='stand-off stand or'),
    'follow_me_apron2': dict(text='Follow-me guidance into the stands of apron Nr. 2 except 232-235, 262-265, 286-290 '
                                  '(AD 2.20 3.2.3).', probe='taxi into stands of apron Nr.2( except stands Nr.'),
    'push_l12_l13_l14': dict(text='Stands 232-235 push back to a holding point on TWY L12, 262-265 on L13, 286-290 on '
                                  'L14, then start up and taxi to TWY D (AD 2.20 3.2.2.4 c-e).',
                             probe='For stands Nr.232-235, push back to holding point on'),
    'push_4xx': dict(text='Stands 401-416 (span < 65 m) push back to the holding point on TWY L11 (AD 2.20 3.2.2.4 g).',
                     probe='with wing span＜65m shall be pushed back to the'),
    'business': dict(text='Business stands 310-312; business aircraft with span >= 31 m park on a stand meeting the '
                          'span limit (AD 2.20 3.2.9).', probe='3.2.9 Business stands Nr.310-312 established'),
    'apu_bridge': dict(text='Aircraft on boarding-bridge stands must shut the APU and use bridge 400 Hz power and '
                            'pre-conditioned air (AD 2.20 3.5.1).', probe='The aircraft parking on boarding bridge stand shall'),
    'b748': dict(text='B747-8: normally stand 248 (or 250, 411, 511 with restrictions) (AD 2.20 2.5.1.2).',
                 probe='B747-8 can normally use stand Nr.248'),
}
# AIP-only designators (no OSM node): physical stands 414-416 and 514-516 (AIP mirror stand table; OSM has no node).
AIP_ONLY = ['414', '415', '416', '514', '515', '516']
AIP_OVERLAYS = ['216E', '220E', '281E', '404C', '408C', '413E']   # combined / alternative designators (AIP mirror)


def planform_poly(cls, nose, hdg, buf=0.0):
    polys = [Polygon([from_local(u, v, nose, hdg) for u, v in p]) for p in class_planform(cls)]
    g = unary_union(polys)
    return g.buffer(buf) if buf else g


def main():
    O = OsmStands(ROOT)
    A = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
    s2 = json.load(open(S2_MEAS)) if os.path.exists(S2_MEAS) else None
    sar = json.load(open(SAR_MEAS)) if os.path.exists(SAR_MEAS) else None
    aip_txt = open(AIP_TXT, encoding='utf-8').read() if os.path.exists(AIP_TXT) else None
    checks = {}

    stands = O.stands()
    positions = O.unref_dead_ends()
    names = [s['name'] for s in stands]
    byname = {s['name']: s for s in stands}

    # ------------------------------------------------------------------ obstacles and pavement
    bld = [Polygon(b['ring']).buffer(0) for b in A['buildings'] if b.get('ring') and len(b['ring']) >= 3]
    bld_u = unary_union(bld)
    aprons = unary_union([Polygon(a['ring']).buffer(0) for a in A['aprons']])
    twy_surf = unary_union([Polygon(p['ring'], p.get('holes') or []).buffer(0) for p in A['surfaces']['taxiway']])
    rwy_surf = unary_union([Polygon(p['ring']).buffer(0) for p in A['surfaces']['runway']])
    leadin_paths = {s['name']: O.trace_back(s['key']) for s in stands}
    leadin_u = unary_union([LineString(p).buffer(12) for p in leadin_paths.values() if p])
    paved = unary_union([aprons, twy_surf, rwy_surf, leadin_u])
    twl = [LineString(t['pts']) for t in A['taxiways'] + A['taxilanes'] if len(t['pts']) > 1]

    # ------------------------------------------------------------------ alternative groups (overlapping fuselages)
    def fus(n, L=30.0, hw=2.0, buf=3.0):
        st = byname[n]
        return Polygon([from_local(u, v, st['stop'], st['hdg']) for u, v in ((0, -hw), (-L, -hw), (-L, hw), (0, hw))]).buffer(buf)
    pc = {n: fus(n) for n in names}
    alt_pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if math.dist(byname[a]['stop'], byname[b]['stop']) > 60:
                continue
            if pc[a].intersects(pc[b]):
                alt_pairs.append((a, b, round(pc[a].intersection(pc[b]).area / pc[a].area, 2)))
    group = {n: {n} for n in names}
    for a, b, _ in alt_pairs:
        g = group[a] | group[b]
        for n in g:
            group[n] = g

    # ------------------------------------------------------------------ neighbours (lateral, stop-based, for reporting)
    def neighbours(s):
        L = R_ = None
        for t in stands:
            if t is s or t['name'] in group[s['name']] or abs(hdiff(s['hdg'], t['hdg'])) > 25:
                continue
            u, v = to_local(t['stop'], s['stop'], s['hdg'])
            if abs(u) > 30 or abs(v) < 12 or abs(v) > 110:
                continue
            if v < 0 and (L is None or v > L[1]): L = (t['name'], v)
            if v > 0 and (R_ is None or v < R_[1]): R_ = (t['name'], v)
        return L, R_

    near = {n: [m for m in names if m != n and m not in group[n]
                and math.dist(byname[n]['stop'], byname[m]['stop']) < 140] for n in names}

    def fits(n, cls, nb_cls, buf=CLEAR / 2):
        """class cls on stand n clear of each neighbour m at class nb_cls(m), of buildings and of taxilanes"""
        s = byname[n]
        P = planform_poly(cls, s['stop'], s['hdg'])
        Pb = P.buffer(buf)
        for m in near[n]:
            cm = nb_cls(m)
            if cm is None:
                continue
            Q = planform_poly(cm, byname[m]['stop'], byname[m]['hdg']).buffer(buf)
            if Pb.intersects(Q):
                return False, 'neighbour %s (%s)' % (m, cm)
        if P.distance(bld_u) < BLD_CLEAR:
            return False, 'building'
        # tail clearance to taxilanes: points of the planform behind the wing (u < -0.6 L of the class reference)
        Lc = CLS_REF[cls][1]
        tail = Polygon([from_local(u, v, s['stop'], s['hdg']) for u, v in
                        [(-0.62 * Lc, -CLS_REF[cls][2] * 0.2), (-Lc, -CLS_REF[cls][2] * 0.2),
                         (-Lc, CLS_REF[cls][2] * 0.2), (-0.62 * Lc, CLS_REF[cls][2] * 0.2)]])
        for l in twl:
            if tail.distance(l) < TAIL_CLEAR:
                return False, 'taxilane behind'
        return True, None

    # 1. symmetric geometry class (an upper bound)
    geo = {}
    geo_why = {}
    for n in names:
        best = None; why = None
        for c in ORDER:
            ok, w = fits(n, c, lambda m, c=c: c)
            if ok:
                best = c
            else:
                why = w; break
        geo[n] = best or 'B'; geo_why[n] = why
    # 2. imagery evidence
    s2st = (s2 or {}).get('stands', {})
    obs_wide = {}
    for n in names:
        r = s2st.get(n) or {}
        cc = r.get('calls_by_class') or {}
        nw = sum(cc.get(k, 0) for k in WIDE)
        mx = None
        for c in ['F', 'EL', 'E', 'D']:
            if sum(cc.get(k, 0) for k in ORDER[ORDER.index(c):]) >= 2:
                mx = c; break
        obs_wide[n] = (nw, mx, r.get('n_occupied'), r.get('n_valid'), cc)
    # prior: a stand spaced >= WIDE_SPACING m from its lateral neighbours (or from its one neighbour, the other side open)
    # is taken as designed for wide-bodies (class = the geometry class, at most EL); otherwise at most class C
    spacing = {}
    cls = {}
    for n in names:
        L, R_ = neighbours(byname[n])
        sp = [abs(x[1]) for x in (L, R_) if x]
        spacing[n] = sp
        wide_sp = bool(sp) and min(sp) >= WIDE_SPACING
        cap = 'EL' if wide_sp else 'C'
        cls[n] = ORDER[min(ORDER.index(geo[n]), ORDER.index(cap))]
    prior_cls = dict(cls)
    cls_src = {n: 'inf' for n in names}
    raised = {}
    for n in sorted(names, key=lambda n: -obs_wide[n][0]):
        nw, mx, _, _, _ = obs_wide[n]
        if nw >= 2 and mx:
            cap = ORDER[min(len(ORDER) - 1, ORDER.index(mx) + 1)]
            cur = cls[n]
            target = cur
            for c in ORDER[ORDER.index(cur):ORDER.index(cap) + 1]:
                ok, _ = fits(n, c, lambda m: cls[m])
                if ok:
                    target = c
            if ORDER.index(target) < ORDER.index('D'):
                # wide-body seen but no wide class fits next to the neighbours: keep D and mark the conflict below
                target = 'D'
            if target != cur:
                raised[n] = (cur, target)
            cls[n] = target
            cls_src[n] = 'obs'
        elif nw >= 2:
            cls_src[n] = 'obs'
    # 3. remaining overlaps -> excl
    excl = defaultdict(set)
    for n in names:
        for m in near[n]:
            if m < n:
                continue
            P = planform_poly(cls[n], byname[n]['stop'], byname[n]['hdg'])
            Q = planform_poly(cls[m], byname[m]['stop'], byname[m]['hdg'])
            if P.intersects(Q):
                excl[n].add(m); excl[m].add(n)
    for n in names:
        for m in group[n]:
            if m != n:
                excl[n].add(m)

    # ------------------------------------------------------------------ gates (OSM aeroway=gate) -> stands
    gates = O.gate_points()
    gate_by_ref = {g['ref']: g for g in gates}
    stand_refs2 = {int(n[1:3]) for n in names if re.match(r'^2\d\d$', n)}
    assoc = {}          # stand -> (gate, rule)
    used = set()
    for n in names:     # T2: stand 2nn <-> gate nn (rule from the SAA gate maps, phase 0; checked here: offsets below)
        m = re.match(r'^2(\d\d)$', n)
        if m and m.group(1).lstrip('0') in gate_by_ref:
            g = gate_by_ref[m.group(1).lstrip('0')]
            u, v = to_local(g['xz'], byname[n]['stop'], byname[n]['hdg'])
            if u > -6 and math.hypot(u, v) < 55:
                assoc[n] = (g, 'stand 2nn = OSM gate nn'); used.add(g['ref'])
    # elsewhere (T1): greedy nearest pairs, gate ahead of the stop (u > 0) within 56 m, each gate once
    pairs = []
    for n in names:
        if n in assoc or not n.startswith('1'):
            continue
        for g in gates:
            if g['ref'] in used:
                continue
            u, v = to_local(g['xz'], byname[n]['stop'], byname[n]['hdg'])
            d = math.hypot(u, v)
            if u > 0 and d < 56:
                pairs.append((d, n, g))
    for d, n, g in sorted(pairs, key=lambda t: t[0]):
        if n in assoc or g['ref'] in used:
            continue
        assoc[n] = (g, 'nearest OSM gate ahead of the stop (each gate once)'); used.add(g['ref'])
    spare_gates = [g for g in gates if g['ref'] not in used]
    gate_off = [to_local(assoc[n][0]['xz'], byname[n]['stop'], byname[n]['hdg']) for n in assoc]
    checks['gate_association'] = {
        'osm_gate_nodes': len(gates), 'associated': len(assoc),
        'by_rule': dict(Counter(r for _, r in assoc.values())),
        'gate_offset_from_stop_median_uv_m': [R2(sorted(o[0] for o in gate_off)[len(gate_off) // 2]),
                                              R2(sorted(o[1] for o in gate_off)[len(gate_off) // 2])],
        'gate_left_of_axis': sum(1 for o in gate_off if o[1] < 0),
        'unassociated_gate_refs': sorted([g['ref'] for g in spare_gates], key=lambda r: int(r) if r.isdigit() else 999)}

    # ------------------------------------------------------------------ bridges
    sarst = (sar or {}).get('stands', {})
    null = (sar or {}).get('null', {})
    thr = null.get('p95'); thr2 = null.get('bridge2_p95'); thrn = null.get('near_p95')
    term_polys = [g for f, g in O.terminal_polys() if f['properties']['tags'].get('name:en') in ('Terminal 1', 'Terminal 2')]
    term_u = unary_union(term_polys)

    def door_uv(c, k):
        L_ = CLS_REF[c][1]; hw = CLS_REF[c][3] / 2
        return (-(0.13 if k == 1 else 0.28) * L_, -(hw + 0.8))

    # spare gates (no stand of their own): each to the nearest wide stand within 45 m ahead -> a second bridge
    spare_to = {}
    for sg in spare_gates:
        best = None
        for n in names:
            if cls[n] not in WIDE:
                continue
            u, v = to_local(sg['xz'], byname[n]['stop'], byname[n]['hdg'])
            d = math.hypot(u, v)
            if -5 < u < 45 and abs(v) < 50 and (best is None or d < best[0]):
                best = (d, n)
        if best:
            spare_to[best[1]] = sg
    bridges, bridge_status = {}, {}
    for n in names:
        sr = sarst.get(n)
        g = assoc.get(n)
        st = byname[n]
        score = sr and sr.get('bridge_score'); near_s = sr and sr.get('near_score'); s2b = sr and sr.get('bridge2_score')
        if g is None and not (score is not None and thr is not None and score >= thr
                              and term_u.distance(Point(st['stop'])) < 75):
            if term_u.distance(Point(st['stop'])) > 75:
                bridge_status[n] = 'none'          # remote: no terminal within 75 m
            elif any(m in assoc for m in group[n] if m != n):
                bridge_status[n] = 'shared'        # alternative position of a stand with a gate: uses its bridge(s)
            elif score is not None and thr is not None and score < 0.5 * thr:
                bridge_status[n] = 'absent'        # no OSM gate and no SAR corridor signature
            else:
                bridge_status[n] = 'unclear'
            continue
        if score is not None and thr is not None and score >= thr:
            status, bsrc = 'present', 'obs'
        elif near_s is not None and thrn is not None and near_s >= thrn:
            status, bsrc = 'present_retracted', 'obs'
        else:
            status, bsrc = 'unclear', 'inf'
        if g is None:
            gpt = from_local(16.7, -21.8, st['stop'], st['hdg']); gref = None; grule = 'no OSM gate: median gate offset'
        else:
            gpt = g[0]['xz']; gref = g[0]['ref']; grule = g[1]
        # second bridge: a spare OSM gate (no stand of its own) within 45 m ahead of a wide stand, or the SAR L2 corridor
        second = None
        if cls[n] in WIDE:
            if n in spare_to:
                second = ('osm_spare_gate', spare_to[n])
            if second is None and s2b is not None and thr2 is not None and s2b >= thr2 and status == 'present':
                second = ('sar_l2_corridor', None)
        attach = term_u.boundary.interpolate(term_u.boundary.project(Point(gpt))) if term_u.distance(Point(gpt)) < 80 else None
        recs = []
        for k in (1, 2) if second else (1,):
            du, dv = door_uv(cls[n], k)
            cab = from_local(du, dv, st['stop'], st['hdg'])
            rot = gpt if k == 1 or second[1] is None else second[1]['xz']
            recs.append({
                'gate': (gref if k == 1 else (second[1]['ref'] if second[1] else None)), 'door': k,
                'attach': [R2(attach.x), R2(attach.y)] if attach is not None else None,
                'rotunda': [R2(rot[0]), R2(rot[1])],
                'rotunda_src': ('OSM aeroway=gate node (taken as the rotunda / end of the fixed link: in the SAR scene the '
                                'fixed links end there) [inf]' if (k == 1 and g) or (k == 2 and second[1]) else
                                'median OSM gate offset from the stop (16.7 m ahead, 21.8 m left) [inf]'),
                'cab': [R2(cab[0]), R2(cab[1])], 'cab_pose': 'docked (inf: door %d of the class reference aircraft)' % k,
                'walk': ([[R2(attach.x), R2(attach.y)], [R2(rot[0]), R2(rot[1])]] if attach is not None else None),
                'src': bsrc if k == 1 else ('obs' if second[0] == 'sar_l2_corridor' else 'inf'),
                'evidence': ({'umbra_2024_06_02': {'corridor_asymmetry': score, 'near_asymmetry': near_s,
                                                    'null_p95': thr, 'near_null_p95': thrn,
                                                    'sheet': 'docs/phase1/' + 'bridges_sar_%s.jpg'},
                              'osm_gate': gref, 'association': grule} if k == 1 else
                             {'second_bridge_rule': second[0], 'l2_corridor_asymmetry': s2b, 'null_p95': thr2}),
            })
        bridges[n] = recs
        bridge_status[n] = status

    # ------------------------------------------------------------------ areas, remote stands, push-back
    def area_of(n):
        st = byname[n]
        if n.startswith('1'):
            return 'T1 north face' if n in ('101', '102', '109', '110', '111', '112') else 'T1 west face'
        if n.startswith('2'):
            return 'T2 aprons Nr. 2'
        if n.startswith('3'):
            return 'business apron (north-east)' if int(n[:3]) <= 312 else 'east apron (north of T1)'
        if n.startswith('4'):
            return 'west remote apron (Apron Nr. 4)'
        if n.startswith('5'):
            return 'east remote apron (along TWY A / L01)'
        if n.startswith('6'):
            return 'south-west apron (Apron Nr. 6)'
        return 'other'

    def push_options(n):
        """inferred push-back: straight back along the stand axis to the taxilane the lead-in comes from, the tail then
        turned onto it in either direction (aircraft can leave towards either end unless an AIP rule restricts it)"""
        p = leadin_paths[n]
        st = byname[n]
        if not p:
            return None
        j = p[0]
        # taxilane direction at the junction: nearest taxiway / taxilane segment through j
        best = None
        for t in A['taxiways'] + A['taxilanes']:
            pts = t['pts']
            for a_, b_ in zip(pts[:-1], pts[1:]):
                seg = LineString([a_, b_])
                d = seg.distance(Point(j))
                if d < 3 and (best is None or d < best[0]):
                    best = (d, F.vec_hdg(b_[0] - a_[0], b_[1] - a_[1]), t.get('ref'), t['id'])
        u, v = to_local(j, st['stop'], st['hdg'])
        rec = {'junction': [R2(j[0]), R2(j[1])], 'push_dist_m': R2(-u), 'src': 'inf',
               'rule': 'push straight back along the stand axis to the taxilane the lead-in leaves, then turn the tail '
                       'onto it; nose direction after the push = opposite of the tail direction'}
        if best:
            h = best[1]
            rec.update({'taxilane': best[2] or best[3], 'tail_headings': [R2(h), R2((h + 180) % 360)]})
        return rec

    # ------------------------------------------------------------------ assemble
    out_stands = []
    pav_out = {}
    for s in stands:
        n = s['name']; c = cls[n]
        P = planform_poly(c, s['stop'], s['hdg'])
        outside = P.difference(paved).area / P.area
        pav_out[n] = outside
        L, R_ = neighbours(s)
        nw, mx, nocc, nval, cc = obs_wide[n]
        avail = None
        sp = spacing[n]
        if sp and c == 'B':
            avail = min(sp) - CLEAR
        span_max = R2(avail) if avail is not None and avail < CLASS_MAX[c][0] else None
        br = bridges.get(n, [])
        for b in br:
            if b['door'] == 1 and isinstance(b['evidence'].get('umbra_2024_06_02'), dict):
                grp = sar_group(n)
                b['evidence']['umbra_2024_06_02']['sheet'] = ('docs/phase1/bridges_sar_%s.jpg' % grp) if grp else None
        contact = bridge_status[n] in ('present', 'present_retracted', 'unclear', 'shared') and (
            bool(br) or bridge_status[n] == 'shared')
        rec = {
            'name': n, 'alias': [], 'nose': [R2(s['stop'][0]), R2(s['stop'][1])], 'hdg': R2(s['hdg']), 'cls': c,
            'src': 'obs' if cls_src[n] == 'obs' else 'inf',
            'area': area_of(n), 'contact': contact, 'bridge_status': bridge_status[n],
            'bridges': br,
            'gate': assoc[n][0]['ref'] if n in assoc else None,
            'pos_src': 'osm', 'name_src': 'osm',
            'osm': {'node': s['node'], 'version': s['version'], 'timestamp': s['timestamp'], 'leadin_way': s['way'],
                    'final_segment_m': R2(s['final_seg_m'])},
            'cls_src': cls_src[n],
            'cls_evidence': {
                'geometry_class': geo[n], 'geometry_limit': geo_why[n],
                'prior_class': prior_cls[n],
                'neighbours': {'left': L and [L[0], R2(-L[1])], 'right': R_ and [R_[0], R2(R_[1])]},
                's2_dates_valid': nval, 's2_dates_with_aircraft': nocc, 's2_template_calls': cc,
                's2_wide_calls': nw, 's2_largest_class_2plus': mx,
                'raised': list(raised[n]) if n in raised else None,
            },
            'span_max': span_max, 'len_max': None,
            'excl': sorted(excl[n], key=stand_sort_key), 'alt_group': sorted(group[n] - {n}, key=stand_sort_key) or None,
            'leadin': [[R2(x), R2(z)] for x, z in (leadin_paths[n] or [])],
            'push': push_options(n),
            'pavement_outside_frac': round(outside, 3),
            'occupancy_s2': (s2st.get(n) or {}).get('occupancy'),
            'aip_status': 'osm_only' if n in OSM_ONLY else 'aip+osm',
        }
        if n in OSM_ONLY:
            rec['flag'] = ('OSM-only ref: no such designator in the AIP (mirror) stand table EFF 2026-07-08 (the 2026 '
                           'chart notes "Stand number adjusted"); kept, flagged')
        out_stands.append(rec)
    remote = [{'name': r['name'], 'area': r['area'], 'cls': r['cls'], 'service': (
        'business (FBO / crew transfer)' if r['area'].startswith('business') else 'bus (inf)'), 'src': 'inf'}
        for r in out_stands if not r['contact']]

    unplaced = [{'name': n, 'kind': 'remote (AIP designator, no OSM node)', 'src': 'AIP (mirror)',
                 'reason': 'designator in the AIP (mirror) stand table; no OSM parking_position node and no stand '
                           'coordinates in the AIP: not placed. ' + UNPLACED_NOTE.get(n[0], '')} for n in AIP_ONLY]
    unplaced += [{'name': n, 'kind': 'combined / alternative position (AIP)', 'src': 'AIP (mirror)',
                  'reason': 'AIP (mirror) combined or alternative designator over neighbouring stands (AD 2.20 3.2.7); '
                            'no OSM node; not placed (the matcher may treat it as both base stands)'} for n in AIP_OVERLAYS]
    pos_out = []
    for p in positions:
        x, z = p['stop']
        note = POSITION_NOTE(x, z)
        pos_out.append({'x': R2(x), 'z': R2(z), 'hdg': R2(p['hdg']), 'ref': None, 'osm_way': p['way'],
                        'osm_way_version': p['way_version'], 'zone': note, 'src': 'obs',
                        'evidence': 'OSM aeroway=parking_position way ending away from any taxiway, no ref node',
                        's2_dates_with_aircraft': (s2st.get('osm-way-%d' % p['way']) or {}).get('n_occupied')})

    # ------------------------------------------------------------------ checks
    overl = []
    for i, a_ in enumerate(out_stands):
        for b_ in out_stands[i + 1:]:
            if b_['name'] in a_['excl'] or math.dist(a_['nose'], b_['nose']) > 160:
                continue
            P = planform_poly(a_['cls'], a_['nose'], a_['hdg']); Q = planform_poly(b_['cls'], b_['nose'], b_['hdg'])
            if P.intersects(Q):
                overl.append([a_['name'], b_['name']])
    below_icao = []
    for i, a_ in enumerate(out_stands):
        for b_ in out_stands[i + 1:]:
            if b_['name'] in a_['excl'] or math.dist(a_['nose'], b_['nose']) > 160:
                continue
            P = planform_poly(a_['cls'], a_['nose'], a_['hdg']); Q = planform_poly(b_['cls'], b_['nose'], b_['hdg'])
            d = P.distance(Q)
            req = max(icao_clearance(REF_SPAN[a_['cls']]), icao_clearance(REF_SPAN[b_['cls']]))
            if d < req:
                below_icao.append([a_['name'], b_['name'], R2(d), req])
    checks['planform_overlaps_outside_excl'] = overl
    checks['excl_pairs'] = sorted({tuple(sorted([a_['name'], m], key=stand_sort_key)) for a_ in out_stands for m in a_['excl']})
    checks['pairs_below_icao_clearance'] = {'n': len(below_icao), 'min_m': min((r[2] for r in below_icao), default=None),
                                            'note': 'ICAO Annex 14 3.13.6 (from memory): 4.5 m code C, 7.5 m D-F; '
                                                    'SHA rows are built tighter (CLEAR %.1f m used)' % CLEAR}
    checks['pavement'] = {'max_outside_frac': round(max(pav_out.values()), 3),
                          'stands_outside_gt_5pct': {n: round(v, 3) for n, v in pav_out.items() if v > 0.05},
                          'paved': 'OSM aprons + A1 taxiway surfaces (23 m) + runway + 12 m buffers of the lead-in lines'}
    checks['classes'] = dict(Counter(cls.values()))
    checks['class_src'] = dict(Counter(cls_src.values()))
    checks['bridge_status'] = dict(Counter(bridge_status.values()))
    checks['alt_pairs'] = alt_pairs
    # AIP probes
    if aip_txt:
        norm = lambda t: re.sub(r'\s+', '', t)  # noqa: E731
        nt = norm(aip_txt)
        checks['aip_probes'] = {k: norm(v['probe']) in nt for k, v in AIP_FACTS.items()}
    # local-only agreement with the AIP stand table / VDGS list (counts only; no AIP value is written)
    if os.path.exists(AIP_STANDS_LOCAL):
        checks['aip_agreement'] = aip_agreement(out_stands, json.load(open(AIP_STANDS_LOCAL)))

    meta_in = {}
    for pth in ('refs/cache/osm_pinned/zsss_osm_pinned.geojson', 'data/sha_airport.json', 'data/meas/stand_s2.json',
                'data/meas/stand_sar.json'):
        fp = os.path.join(ROOT, pth)
        if os.path.exists(fp):
            meta_in[pth] = hashlib.sha256(open(fp, 'rb').read()).hexdigest()[:16]
    out = {
        'what': 'Shanghai Hongqiao (ZSSS) stands for SHA Live 3D: positions, headings, size classes, jet bridges, contact '
                '/ remote status, push-back options (task A2). sfo3d stand schema where it fits.',
        'licence': A['licence'],
        'attribution': ['(c) OpenStreetMap contributors (ODbL 1.0) - https://www.openstreetmap.org/copyright',
                        'Contains modified Copernicus Sentinel data 2023-2026',
                        'Umbra SAR Open Data, Umbra Lab Inc (CC BY 4.0)',
                        'Short facts: AIP China AD 2 ZSSS (CAAC), EFF 2026-07-08, read in an unofficial mirror ("AIP (mirror)")'],
        'generator': 'tools/airport/build_stands.py', 'inputs_sha256_16': meta_in,
        'frame': F.FRAME_ID,
        'src_legend': A['src_legend'],
        'note': ('nose = the OSM stop node (end of the painted lead-in line as mapped), used as the nose tip of the class '
                 'reference aircraft [inf]; hdg = final lead-in segment (true deg); cls = sfo3d class (B / C / CL / D / E '
                 '/ EL / F, js/live/airport.js CLASS_MAX) from our geometry + Sentinel-2 parked-aircraft evidence (cls_src '
                 "'obs' = a wide-body was fitted on >= 2 Sentinel-2 dates); bridges[] from OSM gate nodes + the Umbra SAR "
                 "scene 2024-06-02 (src 'obs' = SAR corridor signature above the remote-stand null p95); excl = stands not "
                 'usable at the same time at full class; alt_group = alternative positions (overlapping fuselages)'),
        'class_max': {k: list(v) for k, v in CLASS_MAX.items()},
        'class_ref': {k: {'type': v[0], 'length_m': v[1], 'span_m': v[2]} for k, v in CLS_REF.items()},
        'params': {'clear_m': CLEAR, 'building_clear_m': BLD_CLEAR, 'tail_clear_m': TAIL_CLEAR,
                   'wide_spacing_m': WIDE_SPACING},
        'aip_facts': {k: {'text': v['text'], 'src': 'AIP (mirror)'} for k, v in AIP_FACTS.items()},
        'push_rules': {'general': 'all stands taxi-in / push-back (AIP (mirror) AD 2.20 3.2.6)',
                       'per_stand': 'stands[].push (inferred from the lead-in geometry)',
                       'aip_short_facts': ['push_l12_l13_l14', 'push_4xx', 'adjacent'],
                       'not_transcribed': 'the remaining AD 2.20 3.2.2.4-3.2.2.5 push-back / nose-direction rules and '
                                          'the end-of-push point table (AIP lists; local only, OD3)'},
        'stands': out_stands, 'remote': remote, 'unplaced': unplaced, 'positions': pos_out,
        'spare_gates': [{'ref': g['ref'], 'node': g['node'], 'xz': [R2(g['xz'][0]), R2(g['xz'][1])]} for g in spare_gates],
        'checks_at_build': checks,
        'counts': {'stands': len(out_stands), 'osm_ref_nodes': len(O.ref_nodes), 'osm_only_refs': len(OSM_ONLY),
                   'aip_only_unplaced': len(AIP_ONLY), 'aip_overlays_unplaced': len(AIP_OVERLAYS),
                   'positions_without_ref': len(pos_out), 'contact': sum(1 for r in out_stands if r['contact']),
                   'remote': len(remote), 'bridges': sum(len(r['bridges']) for r in out_stands),
                   'stands_with_2_bridges': sum(1 for r in out_stands if len(r['bridges']) == 2)},
    }
    s_json = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    open(OUT_JSON, 'w').write(s_json)
    open(OUT_JS, 'w').write('// generated by tools/airport/build_stands.py - ODbL 1.0: contains information from OpenStreetMap '
                            '(c) OpenStreetMap contributors; Copernicus Sentinel data; Umbra SAR Open Data (CC BY 4.0)\n'
                            'window.SHA_STANDS = ' + s_json + ';\n')
    print('classes', checks['classes'], 'src', checks['class_src'], 'raised', len(raised))
    print('bridges', checks['bridge_status'], 'counts', out['counts'])
    print('overlaps', overl, 'below ICAO', checks['pairs_below_icao_clearance']['n'])
    print('pavement', checks['pavement']['max_outside_frac'], checks['pavement']['stands_outside_gt_5pct'])
    print('gate assoc', checks['gate_association'])
    if 'aip_agreement' in checks:
        print('AIP agreement', json.dumps(checks['aip_agreement']))
    if aip_txt:
        print('probes', sum(checks['aip_probes'].values()), '/', len(checks['aip_probes']),
              [k for k, v in checks['aip_probes'].items() if not v])


def sar_group(n):
    m = re.match(r'^(\d+)', n)
    if not m:
        return None
    k = int(m.group(1))
    if n in ('101', '102', '109', '110', '111', '112'):
        return 't1_north'
    if 100 <= k < 200:
        return 't1_west'
    for name, a, b in (('t2_north', 218, 231), ('t2_middle_n', 232, 240), ('t2_west', 241, 256),
                       ('t2_middle_s', 257, 266), ('t2_south', 267, 285)):
        if a <= k <= b:
            return name
    return None


def aip_agreement(out_stands, aip):
    """local-only comparison with the AIP (mirror) span limits and VDGS list: COUNTS only"""
    def aip_cls(v):
        x = float(re.search(r'([\d.]+)', v).group(1)); strict = ('＜' in v) or ('<' in v)
        best = 'B'
        for c in ORDER:
            if (REF_SPAN[c] < x) if strict else (REF_SPAN[c] <= x + 0.05):
                best = c
        return best
    lim = aip.get('wingspan_limit_m', {}); vd = set(aip.get('vdgs_stands', []))
    n = ex = w1 = wn = 0; diffs = Counter()
    for r in out_stands:
        if r['name'] not in lim:
            continue
        a = aip_cls(lim[r['name']]); n += 1
        d = ORDER.index(r['cls']) - ORDER.index(a); diffs[d] += 1
        ex += d == 0; w1 += abs(d) <= 1; wn += (r['cls'] in WIDE) == (a in WIDE)
    ours = {r['name'] for r in out_stands if r['bridge_status'] in ('present', 'present_retracted')}
    contact = {r['name'] for r in out_stands if r['contact']}
    return {'stands_compared': n, 'class_exact': ex, 'class_within_one': w1, 'wide_vs_narrow_agree': wn,
            'class_diff_ours_minus_aip': {str(k): v for k, v in sorted(diffs.items())},
            'aip_class_mapping': 'AIP span limit -> the largest class whose reference span fits (REF_SPAN)',
            'vdgs_list_size': len(vd), 'vdgs_with_sar_bridge': len(vd & ours), 'vdgs_contact_ours': len(vd & contact),
            'sar_bridge_not_vdgs': len(ours - vd), 'contact_ours_not_vdgs': len(contact - vd),
            'vdgs_not_contact_ours': len(vd - contact),
            'note': 'computed at build time against refs/cache/aip/derived_aip_zsss/stands.json (local only, never '
                    'committed); counts only (OD3)'}


UNPLACED_NOTE = {
    '4': 'Location by stand order: south of 413 on the west remote apron (not placed).',
    '5': ('Location by stand order: between 511 and 517 on the east remote apron, where OSM has one lead-in without ref '
          '(positions[], next to the business-aviation terminal); not identified with a designator.'),
}


def POSITION_NOTE(x, z):
    if x > 800:
        return 'hangar apron (north-east hangars), no ref'
    if x > 400 and z > 900:
        return 'east remote apron between 511 and 517 (where the AIP has 514-516), no ref'
    return 'no ref'


OSM_ONLY = ['238A', '239', '240A', '258', '259A', '301', '302', '303', '304', '305', '306', '307', '308', '309', '604']

if __name__ == '__main__':
    main()
