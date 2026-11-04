"""Post-build fix-up stage of the stand data: data/sfo_stands.json + .js = the build output of build_stands.py plus the
evidence-listed changes below (static close-out, 2026-11-04; docs/research/stands_rebuild.md s.16).

Why a separate stage: build_stands.py cannot be re-run since the container loss of 2026-11-04 - its inputs (the
14 September flysfo snapshots, the 24-25 Sep adsb.lol recording, refs/cache/stands/{naip_relief, redboxes_naip}.json,
NAIP 2022) are gone and cannot be fetched again (flysfo and ADS-B are not archives). Hand-editing the data is not
allowed, so every change is made here, reproducibly, from
  * BASE = refs/cache/stands/sfo_stands_built_20260926.json - the build output of 26 Sep 2026 (= data/sfo_stands.json as
    committed in 06ecf63 and unchanged to 8d13a5f, byte-identical; build_stands.py now writes this file too), and
  * evidence files that are kept in the repository (or listed with their SHA-256 in refs/MANIFEST.json):
    - SFO AODB plan of 4 Nov 2026: refs/cache/gate_truth/flysfo_api_flight-status_20261104T180142Z.json.gz
      (FLYSFO_WINDOW2; the snapshot list is pinned - a new snapshot changes nothing until it is added here);
    - ADS-B parked stays of 4 Nov 2026 17:43-21Z: refs/cache/stands/adsb_parked.json (tools/stands/adsb_parked.py on the
      adsb.lol recording, ODbL; rec_pack/ keeps the hours);
    - the terminal outline the app draws: data/sfo_buildings.json `complex` (+ SFO Museum terminal / boarding areas).
Every changed stand / bridge carries `fixup` notes; the file lists the stage in `fixups`.

Patches (static review 2026-11-04):
  P1 AODB window 2: types SFO plans on 4 Nov (newest version of each flight) join obs_types (`obs_types_aodb2`);
     a type larger than the class raises the class to that type's class, with span_max / len_max = the largest
     planned type (no type larger than SFO plans is admitted by the raise); types_ok (where set) takes the new types
     plus every type whose planform lies inside theirs (expand_ok, as build_stands). (A15 A332, D5 / C9 B763, F19 B772 /
     B752, C11 B738.)
  P2 conditional exclusion `excl_types` {neighbour: [types]}: a type on this stand that comes within the ICAO stand
     clearance of the neighbour's envelope and that SFO plans only with that neighbour free blocks the neighbour (and
     an occupied neighbour blocks those types here). F19: B772 (4.7 m from F20's envelope; 3 SFO windows, F20 free).
  P3 rotunda vs the building outline: rotunda_max_r also <= distance(rotunda, outline) - 0.2 m (the gap gates.js
     keeps); where that leaves less than the 1.5 m drum gates.js draws at least, the rotunda moves out along its
     outline (outward normal; the smallest move) until the full 2.45 m drum clears it by 0.2 m (src -> inferred).
  P4 obs / inf consistency: src obs only with independent verification - a stand with an unexplained or explained
     conflict_along (B22) or whose axis came from the same ADS-B that would verify it (axis_adsb, verified_by empty:
     D3 / D4 / D9) is src inf; rotunda_src of a moved OSM node says 'inferred'.
  P5 ADS-B stops BEYOND the model nose (build_stands dropped positive family residuals): from the 4 Nov stays, per
     family, median antenna along minus the family reference (build_stands, stands_rebuild s.15) > +1.5 m with the
     aircraft on the axis (|lateral| <= 1.5 m, heading within 10 deg) -> conflict_along {with: adsb, beyond: true} when
     n >= 2 or the 24-25 Sep build's residual of the stand agrees (> 1.5 m beyond), else `adsb_beyond` (evidence only).
BASE: when build_stands.py can run again (its inputs restored), it writes refs/cache/stands/sfo_stands_built.json - point
BASE there and drop the patches it now does itself (P3 rotunda_max_r, P4, P5 are also in build_stands.py since 2026-11-04).
Usage: python3 tools/stands/patch_stands.py   (then python3 tools/stands/check_stands.py)
"""
import datetime as dt, gzip, json, math, os, sys
from collections import Counter, defaultdict
import numpy as np
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import geom as GM  # noqa: E402

BASE = os.path.join(ROOT, 'refs', 'cache', 'stands', 'sfo_stands_built_20260926.json')
OUT = os.path.join(ROOT, 'data', 'sfo_stands')
FLYSFO_WINDOW2 = ['flysfo_api_flight-status_20261104T180142Z.json.gz']
ADSB_STAYS = os.path.join(ROOT, 'refs', 'cache', 'stands', 'adsb_parked.json')
STAMP = 'fix-up 2026-11-04'
CLASS_MAX = {'B': (28.5, 37), 'C': (36.5, 45), 'CL': (41.1, 54.5), 'D': (52, 62), 'E': (61, 68), 'EL': (65.5, 77), 'F': (80, 80)}
ORDER = ['B', 'C', 'CL', 'D', 'E', 'EL', 'F']
ALIAS_T = {'E175': 'E75L', 'B787': 'B789', 'B76W': 'B763', 'B75W': 'B752', 'E295': 'E195'}
# family ADS-B antenna references (m along the stand axis from the model nose; median over stands, build_stands.py
# fam_ref of the 26 Sep build, docs/research/stands_rebuild.md s.15)
FAM_REF = {'B737': -9.4, 'A320': -1.8, 'EJET': -13.4, 'A220': -5.7, 'CRJ': -9.4, 'B757': -16.0, 'B777': -13.9, 'B787': -13.5}
PHYS = 3.0
GAP = 0.2                     # gates.js keeps the drum 0.2 m off the terminal outline (docs/requests/bridges_static.md)
DRUM_MIN = 1.5                # gates.js never draws a drum below 1.5 m


def dims(t):
    t = ALIAS_T.get(t, t); r = GM.APP.get(t)
    if not r or not r['span']: return None
    return GM.span_app(t) if t in GM.WINGLET_SPAN else r['span'], r['L']


def type_cls(t):
    d = dims(t)
    if not d: return None
    for c in ORDER:
        sp, L = CLASS_MAX[c]
        if d[0] <= sp + 0.6 and d[1] <= L + 2: return c
    return 'F'


def hdg_vec(h): return (math.sin(math.radians(h)), -math.cos(math.radians(h)))


def local(p, stop, hdg):
    f = hdg_vec(hdg); rt = (math.cos(math.radians(hdg)), math.sin(math.radians(hdg)))
    d = (p[0] - stop[0], p[1] - stop[1]); return d[0] * f[0] + d[1] * f[1], d[0] * rt[0] + d[1] * rt[1]


def hdiff(a, b): return (a - b + 180.0) % 360.0 - 180.0


def note(o, txt): o.setdefault('fixup', []).append('%s: %s' % (STAMP, txt))


def expand_ok(s_, obs):
    """build_stands.expand_ok: the observed types plus every type whose planform at its per-family stop lies inside
    the envelope of the observed types (within 0.05 m)"""
    env = unary_union([GM.planform(GM.nose_for(s_, t), s_['hdg'], t) for t in obs])
    envb = env.buffer(0.05); out = set(obs)
    for t, r in GM.APP.items():
        if t in out or not r['span']: continue
        if GM.planform(GM.nose_for(s_, t), s_['hdg'], t).difference(envb).area < 0.01: out.add(t)
    return sorted(out)


def load_flysfo(fn):
    d = json.load(gzip.open(os.path.join(ROOT, 'refs', 'cache', 'gate_truth', fn)))
    recs = d.get('data') or d.get('flights') or d
    return recs if isinstance(recs, list) else []


# ------------------------------------------------------------------------------------------------ P1 / P2
def p1_aodb(D, log):
    newest = {}
    for fn in FLYSFO_WINDOW2:
        sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
        import gatecheck as G  # read-only flysfo reader
        for r in G.load_flysfo(os.path.join(ROOT, 'refs', 'cache', 'gate_truth', fn))[2]: newest[r['flight_id']] = r
    by = defaultdict(lambda: defaultdict(set)); wins = defaultdict(list)
    for r in newest.values():
        t = (r.get('aircraft_transport_type') or {}).get('icao_code')
        for s in r.get('stands') or []:
            n = s['stand']['stand_name']; by[n][t].add(r.get('flight_number') or r['flight_id'])
            wins[n].append((s.get('start_time'), s.get('end_time'), t, r.get('flight_id')))
    for s in D['stands']:
        names = list(s.get('aodb') or []) or [s['name']]
        planned = defaultdict(set)
        for n in names:
            for t, fl in by.get(n, {}).items():
                if t: planned[ALIAS_T.get(t, t)] |= fl
        new = sorted(t for t in planned if t not in set(ALIAS_T.get(x, x) for x in s.get('obs_types') or []) and dims(t))
        if not new: continue
        s['obs_types_aodb2'] = {t: sorted(planned[t])[:6] for t in new}
        s['obs_types'] = sorted(set(s.get('obs_types') or []) | set(new))
        big = max(new, key=lambda t: ORDER.index(type_cls(t)))
        c_new = type_cls(big)
        if ORDER.index(c_new) > ORDER.index(s['cls']):
            old = s['cls']; s['cls'] = c_new
            obs = [ALIAS_T.get(t, t) for t in s['obs_types'] if dims(t)]
            sp = max(dims(t)[0] for t in obs); L = max(dims(t)[1] for t in obs)
            s['span_max'] = round(sp, 2) if sp < CLASS_MAX[c_new][0] - 0.6 else s.get('span_max')
            s['len_max'] = round(L, 2) if L < CLASS_MAX[c_new][1] - 2 else s.get('len_max')
            s['cls_src'] = s.get('cls_src', '') + '; %s: %s -> %s (SFO plans %s here on 4 Nov 2026: %s); span_max / len_max = the largest planned type' % (
                STAMP, old, c_new, big, ', '.join(s['obs_types_aodb2'][big]))
            note(s, 'class %s -> %s from SFO\'s 4 Nov plan (%s)' % (old, c_new, ', '.join('%s %s' % (t, '/'.join(s['obs_types_aodb2'][t])) for t in new)))
            log.append('P1 %s class %s -> %s (%s)' % (s['name'], old, c_new, ', '.join(new)))
        else:
            for k, i in (('span_max', 0), ('len_max', 1)):
                if s.get(k) and max(dims(t)[i] for t in new) > s[k]:
                    s[k] = round(max(dims(t)[i] for t in new), 2); note(s, '%s raised to %.2f m for %s (SFO 4 Nov plan)' % (k, s[k], big))
            log.append('P1 %s new planned types %s (class %s kept)' % (s['name'], ', '.join(new), s['cls']))
        if s.get('types_ok'):
            add = [t for t in new if t in GM.APP]
            old_ok = list(s['types_ok'])
            s['types_ok'] = sorted(set(old_ok) | set(expand_ok(s, add)))
            note(s, 'types_ok + %s (SFO 4 Nov plan; expand_ok adds %s)' % (', '.join(add), ', '.join(sorted(set(s['types_ok']) - set(old_ok) - set(add))) or 'nothing'))
            log.append('P1 %s types_ok + %s' % (s['name'], ', '.join(sorted(set(s['types_ok']) - set(old_ok)))))
    return wins


def p2_excl_types(D, wins, log):
    S = {s['name']: s for s in D['stands']}
    for s in D['stands']:
        if not s.get('obs_types_aodb2'): continue
        for o in D['stands']:
            if o is s or o['name'] in (s.get('excl') or []) or math.dist(o['nose'], s['nose']) > 170: continue
            env_o = GM.stand_env(o)
            for t in s['obs_types_aodb2']:
                tt = ALIAS_T.get(t, t)
                if tt not in GM.APP: continue
                d = GM.planform(GM.nose_for(s, tt), s['hdg'], tt).distance(env_o)
                need = GM.icao_clear(dims(tt)[0])
                if d >= need: continue
                # SFO's own practice: the windows of this type here vs the neighbour's windows (same snapshot)
                mine = [w for n in (s.get('aodb') or [s['name']]) for w in wins.get(n, []) if ALIAS_T.get(w[2], w[2]) == tt]
                theirs = [w for n in (o.get('aodb') or [o['name']]) for w in wins.get(n, [])]
                def iso(x): return dt.datetime.fromisoformat(x).timestamp() if x else None
                ov = sum(1 for a in mine for b in theirs if iso(a[0]) and iso(b[0]) and min(iso(a[1]), iso(b[1])) - max(iso(a[0]), iso(b[0])) > 600)
                if d < PHYS or ov == 0:
                    for x, y in ((s, o), (o, s)):
                        x.setdefault('excl_types', {}).setdefault(y['name'], [])
                    s['excl_types'][o['name']] = sorted(set(s['excl_types'][o['name']]) | {tt})
                    o['excl_types'][s['name']] = sorted(set(o['excl_types'][s['name']]) | {'@' + s['name'] + ':' + tt})
                    note(s, '%s here blocks %s (%.1f m from its envelope < ICAO %.1f m; SFO\'s %d plan windows of %s here overlap none of %s)' % (
                        tt, o['name'], d, need, len(mine), tt, o['name']))
                    note(o, 'blocked while %s holds a %s (excl_types)' % (s['name'], tt))
                    log.append('P2 %s %s -> blocks %s (%.1f m, %d windows, %d overlaps)' % (s['name'], tt, o['name'], d, len(mine), ov))
                else:
                    log.append('P2 %s %s vs %s %.1f m < ICAO %.1f but SFO plans them together %d times: listed only' % (s['name'], tt, o['name'], d, need, ov))
    # where every type the class admits beyond the whitelist is now either clear of the neighbours by >= 3 m or covered by
    # excl_types, the whitelist is no longer needed on SFO's path: types_ok_all_paths is cleared (F19 / F20)
    for s in D['stands']:
        if not s.get('types_ok_all_paths'): continue
        bad = []
        for t in GM.accepted_types(dict(s, types_ok=None)):
            for on in s.get('tight_with') or []:
                o = S.get(on)
                if not o or t in (s.get('excl_types') or {}).get(on, []): continue
                d = GM.planform(GM.nose_for(s, t), s['hdg'], t).distance(GM.stand_env(dict(o, types_ok=None)))
                if d < PHYS: bad.append((t, on, round(d, 1)))
        log.append('P2 %s types_ok_all_paths kept: %d class types < 3 m from a tight neighbour without excl_types (e.g. %s)' % (s['name'], len(bad), bad[:3]) if bad
                   else 'P2 %s: every class type clears the tight neighbours or is in excl_types' % s['name'])


# ------------------------------------------------------------------------------------------------ P3
def outline():
    """the terminal outline js/live/gates.js keeps the bridges out of: data/sfo_buildings.json `complex` rings (each ring a
    filled outline, gates.js inRing) and the non-walkway `parts` rings (piers / halls)"""
    B = json.load(open(os.path.join(ROOT, 'data', 'sfo_buildings.json')))
    rings = list(B['complex']) + [r for p in B.get('parts', []) if p.get('kind') != 'walkway' for r in p['rings']]
    return unary_union([Polygon(r).buffer(0) for r in rings if len(r) >= 3])


def p3_rotunda(D, log):
    bld = outline(); bnd = bld.boundary
    for s in D['stands']:
        for b in (s.get('bridges') or []) + (s.get('bridges_upper') or []):
            r = b.get('rotunda')
            if not r: continue
            p = Point(r); dist = -1.0 if bld.contains(p) else bnd.distance(p)
            cap = dist - GAP
            if cap >= GM.ROT_R: continue
            tag = '%s L%s' % (s['name'], b.get('door'))
            if cap >= DRUM_MIN:
                if (b.get('rotunda_max_r') or GM.ROT_R) <= cap: continue        # already smaller (twin heads, G10)
                b['rotunda_max_r'] = round(min(b.get('rotunda_max_r') or GM.ROT_R, cap), 2)
                b['rotunda_src'] = b.get('rotunda_src', '') + '; drum radius limited by the terminal outline (%.2f m away)' % dist
                note(b, 'rotunda_max_r %.2f m: %.2f m from the terminal outline (gates.js gap 0.2 m)' % (b['rotunda_max_r'], dist))
                log.append('P3 %s rotunda_max_r -> %.2f (outline %.2f m)' % (tag, b['rotunda_max_r'], dist)); continue
            # move straight away from the outline (outward normal at the nearest outline point): the smallest move that
            # clears the full drum. (Along the tunnel would need 5.4 / 6.4 m at F9 / B2: their tunnels leave the facade at
            # 15-25 deg, so a move along them changes every docking extension; NAIP 2024 does not show the drum separately
            # from the roofs there - refs/cache/stands/view not restorable - so the position stays inferred.)
            from shapely.ops import nearest_points
            q0 = nearest_points(bnd, p)[0]; u = np.array([p.x - q0.x, p.y - q0.y])
            if np.linalg.norm(u) < 1e-6: continue
            u = u / np.linalg.norm(u) * (-1.0 if dist < 0 else 1.0)
            new = None
            for k in np.arange(0.05, 6.01, 0.05):
                q = np.array(r) + u * k
                if not bld.contains(Point(q)) and bnd.distance(Point(q)) >= GM.ROT_R + GAP: new = q; break
            if new is None: log.append('P3 %s: no rotunda position within 6 m clears the outline' % tag); continue
            mv = float(np.linalg.norm(new - np.array(r)))
            old = list(r); b['rotunda'] = [round(float(new[0]), 2), round(float(new[1]), 2)]
            w = [list(q) for q in b.get('walk') or []]
            if w and math.dist(w[-1], old) < 0.05: w[-1] = b['rotunda']
            else: w.append(b['rotunda'])
            b['walk'] = w
            if b.get('stow'): b['stow_len'] = round(math.dist(b['rotunda'], b['stow']), 1)
            b['rotunda_max_r'] = round(min(b.get('rotunda_max_r') or GM.ROT_R, GM.ROT_R), 2)
            b['rotunda_src'] = ('inferred: %s; moved %.1f m straight out from the terminal outline (data/sfo_buildings.json) so that the '
                                '2.45 m drum clears it by 0.2 m (was %.2f m from it)') % (b.get('rotunda_src', ''), mv, dist)
            note(b, 'rotunda moved %.2f m out from the terminal outline (was %.2f m away; drum 2.45 m + 0.2 m gap)' % (mv, dist))
            log.append('P3 %s rotunda moved %.2f m out (outline %.2f m)' % (tag, mv, dist))


# ------------------------------------------------------------------------------------------------ P4 / P5
def p4_src(D, log):
    for s in D['stands']:
        why = None
        if s.get('src') == 'obs' and s.get('conflict_along'):
            why = 'carries conflict_along (stands_rebuild s.13: such a stand is never src obs, even when a family stop explains it)'
        elif s.get('src') == 'obs' and s.get('axis_adsb') and not s.get('verified_by'):
            why = 'its axis comes from the ADS-B that would verify it (axis_adsb, verified_by empty): no independent observation'
        if why:
            s['src'] = 'inf'; s['src_note'] = why; note(s, 'src obs -> inf: ' + why); log.append('P4 %s obs -> inf' % s['name'])
        for b in (s.get('bridges') or []) + (s.get('bridges_upper') or []):
            rs = b.get('rotunda_src') or ''
            if rs.startswith('OSM node') and 'moved' in rs:
                b['rotunda_src'] = 'inferred: ' + rs; log.append('P4 %s L%s rotunda_src -> inferred (moved OSM node)' % (s['name'], b.get('door')))


def p5_beyond(D, log):
    st = json.load(open(ADSB_STAYS))
    D['_recheck'] = {}
    fam = lambda t: GM.FAMILY.get(ALIAS_T.get(t, t))
    for s in D['stands']:
        names = set(s.get('aodb') or []) | {s['name']}
        per = {}
        for v in st['stays']:
            if v.get('stand') not in names: continue
            t = v.get('type') if dims(v.get('type') or '') else v.get('sfo_type')
            fm = fam(t) if t else None
            if fm not in FAM_REF: continue
            a, c = local((v['x'], v['z']), s['nose'], s['hdg'])
            if abs(c) > 1.5 or not (-35 < a < 8) or (v.get('hdg') is not None and abs(hdiff(v['hdg'], s['hdg'])) > 10): continue
            if v['hex'] not in per or v['n_good'] > per[v['hex']][0]['n_good']: per[v['hex']] = (v, fm, a)
        if per: D['_recheck'][s['name']] = len(per)
        by = defaultdict(list)
        for v, fm, a in per.values(): by[fm].append((a - FAM_REF[fm], v))
        r26 = ((s.get('resid') or {}).get('adsb') or {})
        for fm, rows in by.items():
            d = float(np.median([r[0] for r in rows]))
            if d <= 1.5: continue
            ac = sorted('%s %s %s' % (v.get('reg'), v.get('type'), v.get('callsign')) for _, v in rows)
            # one airframe on one day is weak: it becomes a conflict only when the 24-25 Sep build's own ADS-B residual
            # of this stand (resid.adsb.along_med, all families; kept in the base file) also puts this family > 1.5 m
            # beyond the nose; otherwise it is recorded as `adsb_beyond` (evidence, src unchanged)
            sep = (r26.get('along_med') - FAM_REF[fm]) if r26.get('along_med') is not None else None
            strong = len(rows) >= 2 or (sep is not None and sep > 1.5)
            rec = {'with': 'adsb', 'beyond': True, 'family': fm, 'resid_along': round(d, 1), 'n': len(rows), 'aircraft': ac,
                   'sep_build_resid': round(sep, 1) if sep is not None else None,
                   'note': 'ADS-B (adsb.lol, 4 Nov 2026) %s aircraft stop %.1f m BEYOND the model nose (antenna median %.1f m vs family '
                           'reference %.1f m)%s; not moved' % (fm, d, d + FAM_REF[fm], FAM_REF[fm],
                                                               '; the 24-25 Sep stays (n=%d, all families) read %+.1f m' % (r26.get('n_aircraft', 0), sep) if sep is not None else '')}
            if not strong:
                s.setdefault('adsb_beyond', []).append(rec); note(s, 'adsb_beyond: one %s airframe %.1f m beyond the nose (not a conflict: n=1, not corroborated)' % (fm, d))
                log.append('P5 %s %s +%.1f m beyond the nose (n=1, Sep %s): adsb_beyond only (%s)' % (s['name'], fm, d, 'n/a' if sep is None else '%+.1f' % sep, '; '.join(ac)))
                continue
            if s.get('conflict_along'): s['conflict_along'].setdefault('also', []).append(rec)
            else: s['conflict_along'] = rec
            note(s, 'conflict_along: %s stop %.1f m beyond the nose (ADS-B n=%d%s)' % (fm, d, len(rows), '' if sep is None else ', Sep build %+.1f m' % sep))
            log.append('P5 %s %s +%.1f m beyond the nose (n=%d, Sep %s: %s)' % (s['name'], fm, d, len(rows), 'n/a' if sep is None else '%+.1f' % sep, '; '.join(ac)))


def main():
    D = json.load(open(BASE)); log = []
    wins = p1_aodb(D, log)
    p2_excl_types(D, wins, log)
    p3_rotunda(D, log)
    p5_beyond(D, log)
    p4_src(D, log)     # after P5: a new conflict_along makes an obs stand inf
    D['fixups'] = [{'stage': 'tools/stands/patch_stands.py', 'stamp': STAMP, 'base': os.path.relpath(BASE, ROOT),
                    'evidence': {'flysfo': FLYSFO_WINDOW2, 'adsb_stays': os.path.relpath(ADSB_STAYS, ROOT),
                                 'outline': 'data/sfo_buildings.json complex + non-walkway parts (js/live/gates.js BLD)'},
                    'why': 'build_stands.py inputs lost in the 2026-11-04 container loss; changes made reproducibly here, not by hand',
                    'evidence_status': ('verified_by adsb / resid.adsb / axis_adsb / type_stops of the 26 Sep build rest on the 24-25 Sep adsb.lol '
                                        'recording and the 14 Sep flysfo snapshots, and G12\'s second axis epoch on NAIP 2022 - all lost on '
                                        '2026-11-04 and not re-checkable; the 4 Nov stays put aircraft on the axis (|lateral| <= 1.5 m, '
                                        'heading within 10 deg) of %d stands: %s' % (len(D['_recheck']), ', '.join('%s (%d)' % kv for kv in sorted(D['_recheck'].items())))),
                    'log': log}]
    D['sources'] = dict(D.get('sources') or {}, sfo2='flysfo.com flight-status AODB, snapshot 2026-11-04T18:01Z (patch_stands.py P1/P2)',
                        adsb2='own ADS-B recording 2026-11-04 17:43-21Z, adsb.lol only (ODbL), stays by tools/stands/adsb_parked.py (P5)')
    D.pop('_recheck', None)
    json.dump(D, open(OUT + '.json', 'w'), separators=(',', ':'))
    open(OUT + '.js', 'w').write('// generated by tools/stands/build_stands.py + tools/stands/patch_stands.py - ODbL 1.0: contains information from '
                                 'OpenStreetMap (c) OpenStreetMap contributors (docs/ATTRIBUTION.md)\nexport const STANDS = '
                                 + json.dumps(D, separators=(',', ':')) + ';\n')
    print('\n'.join(log)); print('wrote data/sfo_stands.json / .js (%d patch lines)' % len(log))


if __name__ == '__main__':
    main()
