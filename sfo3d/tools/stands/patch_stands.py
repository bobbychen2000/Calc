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
     aircraft on the axis (|lateral| <= 1.5 m, heading within 10 deg; round 3: stays selected by that geometry and their
     ADS-B type alone, no flysfo match) -> conflict_along {with: adsb, beyond: true} when
     n >= 2 or the 24-25 Sep build's residual of the stand agrees (> 1.5 m beyond), else `adsb_beyond` (evidence only).
  P6 (round 2, 2026-11-05) drum clearance as js/live/gates.js prepGeom: a rotunda closer than its 1.5 m drum + 0.2 m to
     a clearance outline (data/sfo_buildings + SFO Museum terminal / boarding areas + sky bridges), + 1.7 m to another
     drum or + 1.4 m to another fixed walkway moves straight off it by the deficit (<= 2.0 m); the rest pivot stays at
     `stow` unless that becomes shorter than the model's retraction (then at the retraction on the same line). 31
     rotundas (A10 L1: the check_stands ISSUE), = the bridges track's table (static_closeout.md s.5).
     Close-out round 3 (2026-11-06, finding static-8): with gates.js's own-strip exemption (OwnStrip, a port of
     js/live/gates.js ownStrip): an SFO Museum ring piece that traces the bridge's OWN fixed walkway (the Boarding Area B
     tip strips, which the 3-D domestic asset leaves to the bridges) is not building for that bridge. The nine B-pier moves
     of round 2 (B6, B11, B16, B19, B20, B24, B25, B26, B27 L1, ~1 m out along their own walkways) no longer happen: their
     rotunda / walk end / stow / stow_len are the OSM values again (= the bridges track's revert table, static_closeout.md
     "From bridges, round 2 second pass"); 22 rotundas move (B15 L1 / B11S keep theirs: their strips run 1.5 / 3.0 m < 5 m).
  P7 (round 2) rest pose vs the OSM parked cab (> 3 m apart): adopted when it passes the build's rest criteria, else
     `stow_osm` says why not (bridges_closeout.md s.1.7).
  P8 (close-out round 3, 2026-11-06, static-10) types_ok family dominance (traffic.js typesOkHas): a listed type admits the
     smaller members of its stop-point family - where their planform clears the neighbours by the ICAO stand clearance of
     their code, or by the listed type's own clearance where that is less, never by less than 3 m (fix round 2, verifier
     finding v6; round 1: 3 m only) - else `types_ok_dominated_unsafe`.
  P9 (close-out round 3, static-11) `antenna_ref`: per-family ADS-B position reference re-measured on the committed adsb.lol
     hours REC_HOURS (pinned, close-out round 3 fix round 2 / verifier finding v1: rec_pack/ keeps growing while the
     recorder runs, so reading every file there made each rerun differ).
  P11 (close-out round 3, static-12) fixed-walkway interior vertices out of the drawn outline (gates.js's A15 L1 nudge).
  P10 (close-out round 3, static-9) rest poses within the ICAO clearance of an observed type are re-chosen where a pose
     passes check_stands' rest tests and keeps the clearance (else `stow_icao` says why not).
  P13 (close-out round 5, 2026-11-08) `stop_open` at F19 / F20: families whose observed final stops (pinned adsb.lol hours)
     lie > 3 m off the drawn stop - evidence only, src inf, nothing moved (F19 B777: one airframe ~12 m short).
  Close-out round 5 also: P8 tests every neighbour TYPE with the larger code's ICAO clearance (capped by the listed
     dominating type's distance to that type); P10_ACCEPTED decided on same-harness all-hours replays (see its comment).
  Close-out round 3 also: P1 / P2 read the 5 Nov 02:49Z flysfo snapshot too (SFO allocated D5 to a B772, F19 to B38M,
     C8 B752 with C10 BCS3), and P2 counts an aircraft standing at the neighbour's stop (adsb.lol, the pinned REC_HOURS)
     inside a plan window of the type as parked together (static-10: F19 B772 / F20 B752); P6 has gates.js's own-strip
     exemption (static-8).
BASE: when build_stands.py can run again (its inputs restored), it writes refs/cache/stands/sfo_stands_built.json - point
BASE there and drop the patches it now does itself (P3 rotunda_max_r, P4, P5 are also in build_stands.py since 2026-11-04).

P1 / P2 REPLAY (round 2, 2026-11-05, review static-v5): the flysfo snapshot P1 / P2 read stays local (gate_truth/: no
published terms; listed with its SHA-256 in refs/MANIFEST.json), so a fresh clone could not regenerate the stand data.
When the snapshot is present, P1 / P2 run on it and their RESULT - per stand only the fields they set (P12_FIELDS:
obs_types_aodb2, obs_types, cls, cls_src, span_max, len_max, types_ok, excl_types and their fixup notes) plus the log -
is written to P12_REPLAY (refs/cache/stands/, committed). Without the snapshot (or with --replay) those recorded values
are applied instead; P3-P5 always run. The replay holds nothing that data/sfo_stands.json does not publish already, and
it names the snapshot (file + SHA-256) it came from; if the owner rules the flysfo-derived fields out, P12_REPLAY and
those fields go together. --check runs P1 / P2 on the snapshot and compares them with the replay. Exactly which committed
values derive from flysfo (base, replay, adsb_parked.json): tools/stands/flysfo_provenance.py ->
refs/cache/stands/flysfo_provenance.json (round 3).
Usage: python3 tools/stands/patch_stands.py [--replay | --check]   (then python3 tools/stands/check_stands.py)
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
FLYSFO_WINDOW2 = ['flysfo_api_flight-status_20261104T180142Z.json.gz',
                  'flysfo_api_flight-status_20261105T024944Z.json.gz']   # close-out round 3: + the 5 Nov 02:49Z snapshot (static-10)
REC_PACK = os.path.join(ROOT, 'refs', 'cache', 'rec_pack')                # committed adsb.lol hours (ODbL), P2 co-occupancy / P9
# the adsb.lol hours P2's co-occupancy and P9's antenna reference read, PINNED (close-out round 3 fix round 2, verifier
# finding v1): the 36 complete hours in rec_pack/ when P2 / P9 were first run (2026-11-06 ~05:40Z: 4 Nov 17Z - 6 Nov 04Z).
# rec_pack/ grows by one file per hour while the recorder runs; a new hour changes nothing until it is added here (as
# tools/imagery/adsb_ground_cells.py HOURS). A missing hour is an error, not a silent skip.
REC_HOURS = (['20261104_%02d' % h for h in range(17, 24)] + ['20261105_%02d' % h for h in range(24)]
             + ['20261106_%02d' % h for h in range(5)])
ADSB_STAYS = os.path.join(ROOT, 'refs', 'cache', 'stands', 'adsb_parked.json')
STAMP = 'fix-up 2026-11-04'
STAMP2 = 'fix-up 2026-11-05'
P12_REPLAY = os.path.join(ROOT, 'refs', 'cache', 'stands', 'patch_p1p2_replay.json')
P12_FIELDS = ('obs_types_aodb2', 'obs_types', 'cls', 'cls_src', 'span_max', 'len_max', 'types_ok', 'excl_types', 'fixup')
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


def note(o, txt, stamp=None): o.setdefault('fixup', []).append('%s: %s' % (stamp or STAMP, txt))


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


_STILL = []


def adsb_still():
    """stationary on-ground ADS-B reports (gs < 1 kt, NACp >= 8, position age <= 5 s) of the pinned adsb.lol hours REC_HOURS
    (refs/cache/rec_pack, ODbL): [(t, x, z, hex, callsign, type, heading)] - read once"""
    if _STILL: return _STILL
    import lzma
    miss = [h for h in REC_HOURS if not os.path.exists(os.path.join(REC_PACK, 'adsblol_%s.jsonl.xz' % h))]
    if miss: sys.exit('patch_stands: pinned adsb.lol hour(s) missing from %s: %s (tools/cache/restore.sh)' % (os.path.relpath(REC_PACK, ROOT), ', '.join(miss)))
    for fn in [os.path.join(REC_PACK, 'adsblol_%s.jsonl.xz' % h) for h in REC_HOURS]:
        with lzma.open(fn, 'rt') as f:
            for line in f:
                try: r = json.loads(line)
                except ValueError: continue
                for a in (r.get('d') or {}).get('ac') or []:
                    if a.get('alt_baro') != 'ground' or 'lat' not in a or (a.get('seen_pos') or 0) > 5: continue
                    if (a.get('gs') or 0) >= 1.0 or (a.get('nac_p') or 0) < 8: continue
                    x, z = _w84(a['lat'], a['lon'])
                    _STILL.append((r['t'] - (a.get('seen_pos') or 0), x, z, a['hex'], (a.get('flight') or '').strip(), a.get('t'), a.get('true_heading', a.get('track'))))
    _STILL.sort(key=lambda q: (q[0], q[3]))
    return _STILL


def _w84(la, lo):
    sys.path.insert(0, os.path.join(ROOT, 'tools')); import geo_frame as GF_
    return GF_.wgs84_to_world(la, lo)


def adsb_cooccupied(o, windows, iso):
    """aircraft standing at stand o's stop (|lateral| <= 3 m, -40 m < along < 8 m of its model nose: the antenna lies up to
    ~20 m behind the nose) for >= 60 s with >= 5 reports inside any of the windows -> ['hex callsign HH:MM-HH:MMZ']"""
    if not windows: return []
    st = adsb_still(); ts = [q[0] for q in st]; import bisect
    f = hdg_vec(o['hdg']); out = []
    for w in windows:
        a0, a1 = iso(w[0]), iso(w[1]); by = {}
        for q in st[bisect.bisect_left(ts, a0):bisect.bisect_right(ts, a1)]:
            al, la = local((q[1], q[2]), o['nose'], o['hdg'])
            if abs(la) <= 3.0 and -40.0 < al < 8.0: by.setdefault(q[3], []).append(q)
        for hx, qs in by.items():
            if len(qs) >= 5 and qs[-1][0] - qs[0][0] >= 60:
                out.append('%s %s %s-%sZ' % (hx, next((q[4] for q in qs if q[4]), ''), dt.datetime.utcfromtimestamp(qs[0][0]).strftime('%d %H:%M'),
                                              dt.datetime.utcfromtimestamp(qs[-1][0]).strftime('%H:%M')))
    return sorted(set(out))


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
                # close-out round 3 (finding static-10): SFO's PLAN may keep them apart while operations do not (delays):
                # an aircraft standing at the neighbour's stop (ADS-B, adsb.lol rec_pack, the pinned REC_HOURS) during a
                # plan window of this type here counts as parked together (F20: UAL2467 B752 at its stop 20:48-20:50Z
                # 4 Nov inside UAL2358 B772's F19 window 20:13-21:55Z)
                occ = [] if (d < PHYS or ov) else adsb_cooccupied(o, [w for w in mine if iso(w[0]) and iso(w[1])], iso)
                ov += len(occ)
                if occ: log.append('P2 %s %s vs %s: ADS-B shows %s at %s inside the plan window(s) of %s here' % (s['name'], tt, o['name'], '; '.join(occ[:3]), o['name'], tt))
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


# ------------------------------------------------------------------------------------------------ P6
WALK_HW = 1.3                 # gates.js WALK_W / 2 (fixed walkway 2.6 m)
# close-out round 3 (2026-11-06, finding static-8): js/live/gates.js ownStrip - a piece of an SFO Museum ring that traces
# the bridge's OWN fixed walkway (the Boarding Area B tip strips) is not building for that bridge (the 3-D domestic asset
# leaves those strips to the app's bridges). Same constants as gates.js.
STRIP_LEAN = 2.1                              # m, OSM / Museum roof lean (data bridge_geom_note: 1.3-2.1 m)
STRIP_W = 2 * WALK_HW + 2 * STRIP_LEAN        # walkway slab + the lean on both sides (6.8 m)
STRIP_HW = STRIP_W / 2
STRIP_MIN_L = 5.0                             # a walkway strip runs >= 5 m along the walkway (BA-B tip 6.3-50.8 m; pier-face bumps <= 3.3 m)
STRIP_FAR = 20.0


class OwnStrip:
    """Python port of js/live/gates.js ownStrip(W) (round 2 of the bridges track): W = the bridge's mapped walkway polyline
    ending at its data rotunda; mus = [(k, ring ndarray, matplotlib Path, bbox)] of the SFO Museum clearance rings.
    in_strip(x, z, k): the point of Museum ring k is the bridge's own walkway strip; edges: {(k, j)} Museum ring edges
    that are own-strip along their whole length (skipped by the nearest-outline search)"""
    def __init__(self, W, mus):
        self.seg = []
        for i in range(1, len(W)):
            A, B = np.array(W[i - 1], float), np.array(W[i], float); L = float(np.linalg.norm(B - A))
            if L > 0.01: self.seg.append((A, (B - A) / L, L))
        self.arc = list(np.cumsum([0.0] + [sg[2] for sg in self.seg])[:-1]); self.secs = {}; self.runs = {}; self.edges = set()
        if not self.seg: self.mus = {}; return
        Wa = np.array(W, float); a0, b0 = Wa.min(0) - STRIP_W; a1, b1 = Wa.max(0) + STRIP_W
        self.mus = {k: (r, pth) for k, r, pth, bb in mus if bb[0] < a1 and bb[2] > a0 and bb[1] < b1 and bb[3] > b0}
        for k in self.mus:
            R_, r0, last = [], None, None
            for i, (A, u, L) in enumerate(self.seg):
                for t in np.arange(0.0, L + 1e-6, 0.25):
                    own = any(iv[2] for iv in self.section(k, i, t)); sA = self.arc[i] + t
                    if own:
                        if r0 is None: r0 = sA
                        last = sA
                    elif r0 is not None: R_.append((r0, last)); r0 = None
            if r0 is not None: R_.append((r0, last))
            self.runs[k] = R_
        for k, (r, _) in self.mus.items():
            for j in range(len(r)):
                e0, e1 = r[j - 1], r[j]
                if self.near(*e0)[0] > STRIP_W or self.near(*e1)[0] > STRIP_W: continue
                n = max(1, int(math.ceil(math.dist(e0, e1) / 0.25))); allo, anyo = True, False
                for q in range(n + 1):
                    v = self.test(e0[0] + (e1[0] - e0[0]) * q / n, e0[1] + (e1[1] - e0[1]) * q / n, k)
                    if v is False: allo = False; break
                    if v: anyo = True
                if allo and anyo: self.edges.add((k, j))

    def near_v(self, P):
        best = np.full(len(P), 1e9)
        for A, u, L in self.seg:
            t = np.clip((P - A) @ u, 0, L); best = np.minimum(best, np.linalg.norm(A + np.outer(t, u) - P, axis=1))
        return best

    def near(self, x, z):
        best = None
        for i, (A, u, L) in enumerate(self.seg):
            t = min(L, max(0.0, (x - A[0]) * u[0] + (z - A[1]) * u[1])); d = math.hypot(A[0] + u[0] * t - x, A[1] + u[1] * t - z)
            if best is None or d < best[0]: best = (d, i, t)
        return best

    def section(self, k, i, t):
        A, u, L = self.seg[i]; tq = min(L, max(0.0, round(t / 0.25) * 0.25)); key = (k, i, tq)
        if key in self.secs: return self.secs[key]
        r, pth = self.mus[k]; c = A + u * tq; n = np.array([-u[1], u[0]])
        sv = np.round(np.arange(-STRIP_FAR - 0.1, STRIP_FAR + 0.15, 0.1), 1)
        ins = pth.contains_points(c + np.outer(sv, n))
        lo_idx = [j for j in range(len(sv)) if sv[j] <= -0.1][::-1]; hi_idx = [j for j in range(len(sv)) if sv[j] >= 0]
        lo = []
        for j in lo_idx:
            lo.append(j)
            if (not ins[j] and sv[j] < -STRIP_W - 0.5) or sv[j] < -STRIP_FAR: break
        hi = []
        for j in hi_idx:
            hi.append(j)
            if (not ins[j] and sv[j] > STRIP_W + 0.5) or sv[j] > STRIP_FAR: break
        F = lo[::-1] + hi; X = []; a = None; far = False
        dd = self.near_v(c + np.outer(sv[F], n))
        for q in range(len(F) + 1):
            inn = q < len(F) and ins[F[q]]; s_ = sv[F[q]] if q < len(F) else sv[F[-1]] + 0.1
            if inn:
                if a is None: a = s_; far = q == 0
                if not far and dd[q] > STRIP_W: far = True
            elif a is not None:
                b = s_ - 0.1; X.append((a, b, (not far) and q < len(F) and b >= -STRIP_HW and a <= STRIP_HW)); a = None
        self.secs[key] = X; return X

    def _at(self, i, t, o):
        t += o
        while t < 0 and i > 0: i -= 1; t += self.seg[i][2]
        while t > self.seg[i][2] and i < len(self.seg) - 1: t -= self.seg[i][2]; i += 1
        return None if (t < -1e-6 or t > self.seg[i][2] + 1e-6) else (i, t)

    def test(self, x, z, k):
        if k not in self.mus: return False
        c = self.near(x, z)
        if c is None or c[0] > STRIP_W: return False
        found = False
        for o in [0.0] + [v for oo in np.arange(0.25, STRIP_LEAN + 1e-6, 0.25) for v in (-oo, oo)]:
            q = self._at(c[1], c[2], o)
            if not q: continue
            i, t = q; A, u, L = self.seg[i]; tq = min(L, max(0.0, round(t / 0.25) * 0.25))
            sP = (x - A[0] - u[0] * tq) * -u[1] + (z - A[1] - u[1] * tq) * u[0]
            iv = next((v for v in self.section(k, i, t) if v[0] - 0.15 <= sP <= v[1] + 0.15), None)
            if iv:
                sA = self.arc[i] + tq
                if iv[2] and any(r1 - r0 >= STRIP_MIN_L and r0 - 0.01 <= sA <= r1 + 0.01 for r0, r1 in self.runs.get(k, [])): return True
                found = True
        return False if found else None

    def in_strip(self, x, z, k): return self.test(x, z, k) is True


def p6_drums(D, log):
    """round 2 (2026-11-05; bridges round 2 request, static_closeout.md s.5, orch-1): js/live/gates.js prepGeom moves a
    data rotunda straight off the nearest clearance outline / other drum / other fixed walkway by the deficit for its
    minimum 1.5 m drum (outlines + 0.2 m, drums + 1.5 m + 0.2 m, walkways + 1.3 m + 0.1 m; at most 2.0 m), because the
    OSM roof traces lean 1.3-2.1 m (bridge_geom_note) and 41 drums overlapped the SFO Museum terminal / boarding-area
    outlines the 3-D assets are built from (check_stands A10 L1 ISSUE). The data now says the same: the same rule, with
    the same outlines (data/sfo_buildings.json complex + parts incl. the sky bridges, SFO Museum terminalComplex /
    boardingAreas outer rings), computed for every bridge from the other bridges' data positions as gates.js does; the
    rest pivot stays at `stow` unless the move shortens the rest tunnel below the model's retraction, then it rests at the
    retraction on the same line (gates.js b.e0 = max(stow length, opR)). rotunda_src -> inferred."""
    Bd = json.load(open(os.path.join(ROOT, 'data', 'sfo_buildings.json'))); A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    rings = list(Bd['complex']) + [r for pp in Bd.get('parts', []) if pp.get('kind') != 'walkway' for r in pp['rings']]
    rings += [P[0] for P in A['terminalComplex']] + [P[0] for ba in A['boardingAreas'] for P in ba['polys']]
    rings += [r for pp in Bd.get('parts', []) if pp.get('kind') == 'walkway' for r in pp['rings']]       # sky bridges
    # ring index ranges as gates.js BLD: [0, NBLD) drawn outline, [NBLD, NCL) SFO Museum clearance rings, then sky bridges
    NBLD = len(Bd['complex']) + sum(len(pp['rings']) for pp in Bd.get('parts', []) if pp.get('kind') != 'walkway')
    NCL = NBLD + len(A['terminalComplex']) + sum(len(ba['polys']) for ba in A['boardingAreas'])
    from matplotlib.path import Path as _MPath
    RG = [np.array(r, float) for r in rings]
    PATHS = [_MPath(r) for r in RG]; BB = [(r[:, 0].min(), r[:, 1].min(), r[:, 0].max(), r[:, 1].max()) for r in RG]
    MUS = [(k, RG[k], PATHS[k], BB[k]) for k in range(NBLD, NCL) if len(RG[k]) >= 3]
    EDG = np.array([(k, j, r[j - 1][0], r[j - 1][1], r[j][0], r[j][1]) for k, r in enumerate(RG) if len(r) >= 3 for j in range(len(r))])
    allb = [(st, b) for st in D['stands'] for b in (st.get('bridges') or []) + (st.get('bridges_upper') or []) if b.get('rotunda')]
    STRIPS = {}
    def own_strip(b):
        if id(b) not in STRIPS:
            W = [list(q) for q in b.get("walk") or []] if len(b.get("walk") or []) >= 2 else [list(b.get("attach") or b["rotunda"])]
            if math.dist(W[-1], b['rotunda']) > 0.05: W.append(list(b['rotunda']))
            STRIPS[id(b)] = OwnStrip(W, MUS)
        return STRIPS[id(b)]
    def nearest_building(b, x, z):
        """gates.js nearestBuilding(x, z, false, b._strip): (d, point) of the nearest outline edge within ~24 m that is not
        the bridge's own walkway strip, d 0 when the point is inside a ring (an own-strip point of a Museum ring is not)"""
        own = own_strip(b)
        for k in range(len(RG)):
            bb = BB[k]
            if len(RG[k]) >= 3 and bb[0] <= x <= bb[2] and bb[1] <= z <= bb[3] and PATHS[k].contains_point((x, z)) \
                    and not (NBLD <= k < NCL and own.in_strip(x, z, k)): return 0.0, None
        E = EDG[(np.minimum(EDG[:, 2], EDG[:, 4]) < x + 24) & (np.maximum(EDG[:, 2], EDG[:, 4]) > x - 24) &
                (np.minimum(EDG[:, 3], EDG[:, 5]) < z + 24) & (np.maximum(EDG[:, 3], EDG[:, 5]) > z - 24)]
        if own.edges: E = E[[(int(e[0]), int(e[1])) not in own.edges for e in E]]
        if not len(E): return 1e9, None
        ex, ez = E[:, 4] - E[:, 2], E[:, 5] - E[:, 3]; L2 = np.maximum(ex * ex + ez * ez, 1e-12)
        t = np.clip(((x - E[:, 2]) * ex + (z - E[:, 3]) * ez) / L2, 0, 1); qx, qz = E[:, 2] + ex * t, E[:, 3] + ez * t
        d = np.hypot(qx - x, qz - z); i = int(np.argmin(d)); return float(d[i]), (float(qx[i]), float(qz[i]))
    def limits(b, x, z):
        out = []
        d, q = nearest_building(b, x, z)
        if q is not None and d < 24.0: out.append((d, 0.2, q, 'building'))
        own = b.get('walk') or []
        near = lambda p, q: math.dist(p, q) < 0.3
        for _, ob in allb:
            if ob is b: continue
            ro = ob['rotunda']
            if abs(ro[0] - x) < 30 and abs(ro[1] - z) < 30: out.append((math.dist(ro, (x, z)), DRUM_MIN + 0.2, tuple(ro), 'drum'))
            W = [list(q) for q in ob.get('walk') or []]
            if W and math.dist(W[-1], ro) > 0.05: W.append(list(ro))
            for i in range(1, len(W)):
                a_, b_ = W[i - 1], W[i]
                if min(a_[0], b_[0]) > x + 10 or max(a_[0], b_[0]) < x - 10 or min(a_[1], b_[1]) > z + 10 or max(a_[1], b_[1]) < z - 10: continue
                if math.dist(a_, (x, z)) < 0.6 or math.dist(b_, (x, z)) < 0.6: continue          # connector at this drum
                if any(near(p_, a_) for p_ in own) and any(near(p_, b_) for p_ in own): continue  # shared walkway
                ex, ez = b_[0] - a_[0], b_[1] - a_[1]; L2 = ex * ex + ez * ez or 1.0
                t = min(1.0, max(0.0, ((x - a_[0]) * ex + (z - a_[1]) * ez) / L2)); q = (a_[0] + ex * t, a_[1] + ez * t)
                out.append((math.dist(q, (x, z)), WALK_HW + 0.1, q, 'walkway'))
        return out
    moves = []
    for st, b in allb:                         # every shift from the other bridges' DATA positions (as gates.js)
        r0 = tuple(b['rotunda']); rot = r0; kinds = []
        for _ in range(12):
            worst, dfc = None, 0.005
            for d, extra, q, kind in limits(b, *rot):
                dd = DRUM_MIN + extra - d
                if dd > dfc: dfc, worst = dd, (q, kind)
            if not worst: break
            if worst[1] not in kinds: kinds.append(worst[1])
            dx, dz = rot[0] - worst[0][0], rot[1] - worst[0][1]; l = math.hypot(dx, dz) or 1.0
            rot = (rot[0] + dx / l * (dfc + 0.02), rot[1] + dz / l * (dfc + 0.02))
            sh = math.dist(rot, r0)
            if sh > 2.0: rot = (r0[0] + (rot[0] - r0[0]) * 2 / sh, r0[1] + (rot[1] - r0[1]) * 2 / sh); break
        if math.dist(rot, r0) > 0.005: moves.append((st, b, r0, rot, ' / '.join(kinds)))
    for st, b, r0, rot, why in moves:
        tag = '%s L%s' % (st['name'], b.get('door')) if b.get('gate') == st['name'] else "%s's bridge (gate %s)" % (st['name'], b.get('gate'))
        b['rotunda'] = [round(rot[0], 2), round(rot[1], 2)]
        w = [list(q) for q in b.get('walk') or []]
        if w and math.dist(w[-1], r0) < 0.05: w[-1] = b['rotunda']
        else: w.append(b['rotunda'])
        b['walk'] = w
        mv = math.dist(r0, rot); st_note = ''
        if b.get('stow'):
            e0 = (b.get('ext_range') or [GM.EXT_MIN])[0]; Ls = math.dist(b['rotunda'], b['stow'])
            if Ls < e0 - 0.005:
                u = ((b['stow'][0] - b['rotunda'][0]) / Ls, (b['stow'][1] - b['rotunda'][1]) / Ls); old_s = list(b['stow'])
                b['stow'] = [round(b['rotunda'][0] + u[0] * e0, 2), round(b['rotunda'][1] + u[1] * e0, 2)]
                st_note = '; stow %s -> %s (the rest tunnel %.2f m < the %s retraction %.3f m: rests at the retraction on the same line)' % (
                    old_s, b['stow'], Ls, b.get('model'), e0)
            b['stow_len'] = round(math.dist(b['rotunda'], b['stow']), 1)
        src = b.get('rotunda_src', '')
        b['rotunda_src'] = ('inferred: moved off the SFO Museum outline for a 1.5 m drum + 0.2 m (gates.js prepGeom); OSM roof lean; '
                            if 'inferred' not in src[:9] else '') + src + '; %s: moved %.2f m (patch_stands P6)' % (STAMP2, mv)
        note(b, 'rotunda moved %.2f m off the nearest %s for the 1.5 m drum (%s -> %s)%s' % (mv, why, list(r0), b['rotunda'], st_note), STAMP2)
        log.append('P6 %s rotunda %.2f m off the %s%s' % (tag, mv, why, ' + stow at the retraction' if st_note else ''))
    # drums of a moved rotunda and a neighbour now closer than their two radii + 0.2 m: both radii capped (gates.js
    # drumLimits: (d - 0.2) / 2; G3 / G4 / G7 / G8 L1-L2 4.4-4.6 m apart after the move)
    moved = {id(b) for _, b, _, _, _ in moves}
    for i, (sa, ba) in enumerate(allb):
        for sb, bb in allb[i + 1:]:
            if id(ba) not in moved and id(bb) not in moved: continue
            d = math.dist(ba['rotunda'], bb['rotunda']); ra, rb_ = ba.get('rotunda_max_r') or GM.ROT_R, bb.get('rotunda_max_r') or GM.ROT_R
            if d < ra + rb_ + 0.2:
                cap = round(max(DRUM_MIN, (d - 0.2) / 2), 2)
                for x, y in ((ba, bb), (bb, ba)):
                    if (x.get('rotunda_max_r') or GM.ROT_R) > cap:
                        x['rotunda_max_r'] = cap; note(x, 'rotunda_max_r %.2f m: %.2f m from the drum of %s L%s after P6' % (cap, d, y.get('gate'), y.get('door')), STAMP2)
                log.append('P6 drums %s L%s | %s L%s %.2f m apart: rotunda_max_r <= %.2f' % (ba.get('gate'), ba.get('door'), bb.get('gate'), bb.get('door'), d, cap))
    # the result must be a fixed point of the rule (gates.js moves nothing any more)
    left = [('%s L%s' % (st['name'], b.get('door')), round(max([DRUM_MIN + e - d for d, e, _, _ in limits(b, *b['rotunda'])] + [0]), 3)) for st, b in allb]
    left = [x for x in left if x[1] > 0.005]
    log.append('P6 %d rotundas moved; remaining deficits %s' % (len(moves), left or 'none'))


# ------------------------------------------------------------------------------------------------ P8
STAMP3 = 'fix-up 2026-11-06'





def p8_family_ok(D, log):
    """close-out round 3 (2026-11-06, finding static-10): a stand's types_ok also admits every smaller member of a listed
    type's stop-point family (same geom.FAMILY, span and length <= that type's), the rule js/live/traffic.js typesOkHas
    applies since round 2 (B38M under B39M at F19: SFO planned UAL626 B38M there 18:49-20:08Z 4 Nov and it parked) - so
    the checker's APP view (geom.accepted_types) and traffic.js stay one-to-one.
    A dominated type is NOT geometrically inside the listed one when its wing sits further forward (B77L under B77W: same
    span, 10 m shorter). Fix round 2 (verifier finding v6): such a type is added only where its planform at the stop
    clears the envelope of every stand within 120 m (not `excl`, and not a neighbour it blocks by excl_types) by the
    ICAO stand clearance of its own code (geom.icao_clear: 3.0 / 4.5 / 7.5 m) - or, where a listed type of the same
    family that dominates it already sits closer to that neighbour, by that listed type's clearance (SFO's own
    practice: the added type is never tighter than the type SFO plans / was seen there) - and never by less than 3 m
    (PHYS). Round 1 used PHYS alone, which admitted B77L at F19 3.02 m from F20's A320 and B737 at C11 4.44 m from
    C9's B762 (below code C's 4.5 m). The test is made against the neighbours' FINAL envelopes (their own additions
    included) and repeated until nothing more is removed, so the result does not depend on the stand order. The rest
    are listed in `types_ok_dominated_unsafe` {type: why} (traffic.js typesOkHas does not admit them).
    Close-out round 5 (2026-11-08, verifier finding of round 3 fix 2: the own-code rule let C11 B736 sit 5.11 m from C9's
    B762 although the pair needs code D's 7.5 m and C11's listed B738 keeps 5.77 m): the test is made PER NEIGHBOUR TYPE -
    the added type t at its stop against every type u the neighbour accepts (final lists, at u's stop; pairs either
    excl_types entry rules out are skipped) - with need = max(ICAO(t), ICAO(u)) (the larger code of the pair, as
    check_stands' pair rule), capped by the distance of the dominating listed type(s) of t (max over them) to that same u
    (SFO's practice: never tighter than the listed type there), never below 3 m."""
    S = {s['name']: s for s in D['stands']}
    cand = {}
    for s in D['stands']:
        ok = s.get('types_ok')
        if not ok: continue
        have = set(ok); add = {}
        for t, r in GM.APP.items():
            if t in have or not r.get('span'): continue
            ft = GM.FAMILY.get(t); dt_ = dims(t)
            if not ft or not dt_: continue
            doms = sorted(q for q in have if dims(q) and GM.FAMILY.get(ALIAS_T.get(q, q)) == ft
                          and dt_[0] <= dims(q)[0] + 1e-6 and dt_[1] <= dims(q)[1] + 1e-6)
            if doms: add[t] = doms
        if add: cand[s['name']] = add
    keep = {n: set(a) for n, a in cand.items()}
    PF = {}
    def pf(o, t):
        k = (o['name'], t)
        if k not in PF: PF[k] = GM.planform(GM.nose_for(o, t), o['hdg'], t)
        return PF[k]
    def types_of(o):
        """the types neighbour o accepts with its own final P8 additions (geom.accepted_types on the final types_ok)"""
        ts = sorted(set(o['types_ok']) | keep.get(o['name'], set())) if o.get('types_ok') else None
        return [u for u in GM.accepted_types(dict(o, types_ok=ts) if ts else o) if dims(u)]
    bad = {}
    while True:
        drop = []
        for n in sorted(keep):
            s = S[n]
            for t in sorted(keep[n]):
                pt = pf(s, t); it = GM.icao_clear(dims(t)[0]); hit = None
                for o in D['stands']:
                    if o is s or o['name'] in (s.get('excl') or []) or math.dist(o['nose'], s['nose']) > 120: continue
                    if t in ((s.get('excl_types') or {}).get(o['name']) or []): continue
                    ox = (o.get('excl_types') or {}).get(n) or []
                    if '@%s:%s' % (n, t) in ox: continue
                    for u in types_of(o):
                        if u in ox: continue
                        pu = pf(o, u); d_ = pt.distance(pu)
                        need_icao = max(it, GM.icao_clear(dims(u)[0]))      # the larger code of the pair
                        if d_ >= need_icao: continue
                        dq = max(pf(s, q).distance(pu) for q in cand[n][t])   # the dominating listed type(s) vs the same u
                        need = max(PHYS, min(need_icao, dq))
                        if d_ < need - 1e-6: hit = (o['name'], d_, need, need_icao, dq, u); break
                    if hit: break
                if hit: drop.append((n, t)); bad.setdefault(n, {})[t] = hit
        if not drop: break
        for n, t in drop: keep[n].discard(t)
    for s in D['stands']:
        n = s['name']
        if n not in cand: continue
        b_ = {t: v for t, v in (bad.get(n) or {}).items() if t not in keep[n]}
        if b_:
            s['types_ok_dominated_unsafe'] = {t: '%.1f m from the %s at %s (< %.1f m: ICAO %.1f m for the pair%s)' % (
                v[1], v[5], v[0], v[2], v[3], '' if v[2] >= v[3] else ', capped at the %.1f m of the listed type' % v[4]) for t, v in sorted(b_.items())}
            log.append('P8 %s family-dominated but too close to a neighbour, NOT added: %s' % (n, ', '.join(
                '%s (%s at %s %.1f m < %.1f)' % (t, v[5], v[0], v[1], v[2]) for t, v in sorted(b_.items()))))
        if keep[n]:
            s['types_ok'] = sorted(set(s['types_ok']) | keep[n])
            note(s, 'types_ok + %s (smaller members of a listed type\'s stop-point family that keep the ICAO stand clearance of the larger '
                    'code against every neighbour type, or the clearance of the listed type to it; traffic.js typesOkHas)' % ', '.join(sorted(keep[n])), STAMP3)
            log.append('P8 %s types_ok + %s' % (n, ', '.join(sorted(keep[n]))))


# ------------------------------------------------------------------------------------------------ P9
def p9_antenna_ref(D, log):
    """close-out round 3 (2026-11-06, finding static-11; realtime_closeout R3.1.3 / R3.3): the per-family ADS-B position
    reference (metres the reported position lies behind the nose) re-measured on the pinned adsb.lol hours REC_HOURS
    (refs/cache/rec_pack; fix round 2: was every file there, which grows hourly - verifier finding v1): stays = >= 180 s stationary (gs < 1 kt, NACp >= 8, within 8 m), median position; on a contact
    stand's axis (|lateral| <= 1.5 m, heading within 10 deg, -40 m < along < 10 m of the model nose); value = along minus
    the stand's stop for that family (type_stops, else the nose). Written to D['antenna_ref'] {family: {along_m (median,
    - = behind the nose), n, stands, iqr}} next to the 26 Sep build's FAM_REF - js/live/traffic.js ANT = 0.2 L puts the
    E-Jet antenna 6.3 m behind the nose, the recording 13 m: the antenna reference, not the type stops, carries the ~7 m"""
    st = adsb_still(); by = defaultdict(list)
    for q in st: by[q[3]].append(q)
    stays = []
    for hx, qs in by.items():
        cur = []
        def flush():
            if len(cur) >= 3 and cur[-1][0] - cur[0][0] >= 180:
                hd = [q[6] for q in cur if q[6] is not None]; ty = next((q[5] for q in cur if q[5]), None)
                stays.append((float(np.median([q[1] for q in cur])), float(np.median([q[2] for q in cur])), float(np.median(hd)) if hd else None, ty, hx))
        for q in qs:
            if cur and (math.dist(q[1:3], cur[0][1:3]) >= 8 or q[0] - cur[-1][0] > 600): flush(); cur = []
            cur.append(q)
        flush()
    fam = defaultdict(list)
    for x, z, h, ty, hx in stays:
        f_ = GM.FAMILY.get(ALIAS_T.get(ty, ty)) if ty else None
        if not f_ or h is None: continue
        best = None
        for s in D['stands']:
            a, c = local((x, z), s['nose'], s['hdg'])
            if abs(c) <= 1.5 and -40.0 < a < 10.0 and abs(hdiff(h, s['hdg'])) <= 10 and (best is None or abs(c) < abs(best[2])): best = (s, a, c)
        if not best: continue
        ts = ((best[0].get('type_stops') or {}).get(f_) or {}).get('along') or 0.0
        fam[f_].append((best[1] - ts, best[0]['name'], hx))
    out = {}
    for f_, rows in sorted(fam.items()):
        v = np.array([r[0] for r in rows])
        out[f_] = {'along_m': round(float(np.median(v)), 1), 'n': len(rows), 'stands': len({r[1] for r in rows}), 'aircraft': len({r[2] for r in rows}),
                   'iqr': [round(float(np.percentile(v, 25)), 1), round(float(np.percentile(v, 75)), 1)], 'sep_build': FAM_REF.get(f_)}
        log.append('P9 %s antenna %.1f m behind the nose (n %d stays, %d stands, IQR %s; 26 Sep build %s)' % (
            f_, -out[f_]['along_m'], len(rows), out[f_]['stands'], out[f_]['iqr'], FAM_REF.get(f_)))
    D['antenna_ref'] = {'what': 'per family: median ADS-B reported position along the stand axis relative to the nose at the stop (m, - = behind '
                                'the nose), the adsb.lol hours listed in `hours` (refs/cache/rec_pack/adsblol_<hour>.jsonl.xz, ODbL; pinned in '
                                'patch_stands.py REC_HOURS); obs (n < 5: weak). The position is the '
                                'GNSS antenna unless the transponder applies the DO-260B nose offset (A32x)', 'hours': list(REC_HOURS),
                        'families': out}


# ------------------------------------------------------------------------------------------------ P13
STAMP5 = 'fix-up 2026-11-08 (close-out round 5)'
STOP_OPEN_STANDS = ('F19', 'F20')   # the pair the close-out-3 verifier flagged (F19 wide-body stop vs F20)
STOP_OPEN_MIN = 3.0                 # m: |offset of the observed final stop from the drawn stop| recorded


def p13_stop_open(D, log):
    """close-out round 5 (2026-11-08, verifier finding of close-out 3 fix 2: F19's B772 / B77W are drawn 4.3-4.7 m from F20's
    types, but the one wide-body arrival recorded there stopped ~12 m further from the terminal): EVIDENCE ONLY, nothing moves.
    For the stands in STOP_OPEN_STANDS, every arrival in the pinned hours (REC_HOURS, adsb_still) whose LAST still group there
    lies on the stand axis (|lateral| <= 1.5 m, heading within 10 deg, -45 m < along < +10 m of the model nose) gives the nose
    offset from the drawn stop = antenna along - the family's antenna reference (P9 antenna_ref, n >= 5 only) - the type stop
    (type_stops[family].along, else 0). Families whose median offset exceeds STOP_OPEN_MIN are written to `stop_open`
    {family: {offset_m, n, aircraft, src: 'inf', why}}: an open item - too few airframes (and the antenna offset of one
    airframe is of the same order) to move the stop; the static pair checks still use the drawn stops, so for these
    families the drawn pair clearance is TIGHTER than observed (F19 B777 n = 1)."""
    AR = {f: v['along_m'] for f, v in (D.get('antenna_ref') or {}).get('families', {}).items() if v.get('n', 0) >= 5}
    st = adsb_still(); by = defaultdict(list)
    for q in st: by[q[3]].append(q)
    S = {s['name']: s for s in D['stands']}
    rows = defaultdict(lambda: defaultdict(list))
    for hx, qs in by.items():
        groups, cur = [], []
        for q in qs:
            if cur and (math.dist(q[1:3], cur[0][1:3]) >= 8 or q[0] - cur[-1][0] > 600): groups.append(cur); cur = []
            cur.append(q)
        if cur: groups.append(cur)
        for gi, g in enumerate(groups):
            if len(g) < 3: continue
            ty = next((q[5] for q in g if q[5]), None); f_ = GM.FAMILY.get(ALIAS_T.get(ty, ty)) if ty else None
            hd = [q[6] for q in g if q[6] is not None]
            if not f_ or not hd or f_ not in AR: continue
            x, z, h = float(np.median([q[1] for q in g])), float(np.median([q[2] for q in g])), float(np.median(hd))
            if any(G[0][0] - g[-1][0] < 1800 and math.dist(G[0][1:3], (x, z)) < 60 for G in groups[gi + 1:]): continue   # moved on: not the stop
            for n in STOP_OPEN_STANDS:
                s = S[n]; a, c = local((x, z), s['nose'], s['hdg'])
                if abs(c) <= 1.5 and -45.0 < a < 10.0 and abs(hdiff(h, s['hdg'])) <= 10:
                    ts = (((s.get('type_stops') or {}).get(f_) or {}).get('along')) or 0.0
                    rows[n][f_].append((a - AR[f_] - ts, '%s %s %s' % ((g[0][4] or hx), ty, dt.datetime.fromtimestamp(g[0][0], dt.timezone.utc).strftime('%d %b %H:%MZ'))))
    for n in STOP_OPEN_STANDS:
        rec = {}
        for f_, r in sorted(rows[n].items()):
            off = float(np.median([v for v, _ in r]))
            if abs(off) <= STOP_OPEN_MIN: continue
            rec[f_] = {'offset_m': round(off, 1), 'n': len(r), 'aircraft': [w for _, w in sorted(r, key=lambda q: q[1])], 'src': 'inf',
                       'why': ('ADS-B (adsb.lol, pinned REC_HOURS): the %s final stop%s lie%s %.1f m %s the drawn stop (antenna reference %.1f m, '
                               'P9); open item, not applied: %s' % (f_, 's' if len(r) > 1 else '', '' if len(r) > 1 else 's', abs(off),
                                                                    'short of' if off < 0 else 'beyond', -AR[f_],
                                                                    'n = %d airframe%s, per-airframe antenna offsets of the same order' % (len(r), 's' if len(r) > 1 else '')))}
            log.append('P13 %s %s final stop %+.1f m from the drawn stop (n %d: %s) - stop_open (inf), not applied' % (n, f_, off, len(r), '; '.join(w for _, w in r)))
        if rec:
            S[n]['stop_open'] = rec
            note(S[n], 'stop_open: %s (ADS-B final stops off the drawn stop; evidence only, inferred)' % ', '.join('%s %+.1f m n %d' % (f_, v['offset_m'], v['n']) for f_, v in rec.items()), STAMP5)


# ------------------------------------------------------------------------------------------------ P10
def _obs(o): return set(ALIAS_T.get(t, t) for t in o.get('obs_types') or []) & set(GM.APP)


def _arc(angs, back, margin=25.0):
    """check_stands.swing_arc: (width of the smallest arc holding all directions, whether `back` +-margin is inside it)"""
    A = sorted(a % 360 for a in angs)
    gaps = [(A[(i + 1) % len(A)] - A[i]) % 360 for i in range(len(A))] if len(A) > 1 else [360.0]
    i = max(range(len(gaps)), key=lambda k: gaps[k]); start = A[(i + 1) % len(A)]; width = 360.0 - gaps[i]
    if back is None: return width, False
    rel = (back - start) % 360
    return width, (rel <= width + margin or rel >= 360 - margin)


_WING = {}
# fix round 2 (verifier v7): re-choose rest poses for ACCEPTED-not-observed types too (+-30 deg, never further aft)?
# Decided OFF in close-out round 5 (2026-11-08) on SAME-HARNESS evidence. (The fix-round-2 reason - "UAL917's hits on G4
# L2's cab grew from 47 to 291-378 points" - compared two versions of tools/live/invariants.mjs: commit da29bab added
# the acHit box sampling, engine pieces and 3-D footprints after the fix-1 replay; on one harness UAL917's G4 L2 cab
# (317 points) and G4 L1 stair contact are identical with either setting and with the fix-1 data. Withdrawn.) All-hours
# replays on one frozen harness (invariants.mjs 2f6c5d9b, build_stream.py 93da6fe0, stream SP/r3/all f6ff7ceb), this
# data with P10_ACCEPTED False vs True (19 rests re-chosen). Frozen r3v code: bridge.hit_at_rest 852 -> 756 frames
# (KLM373 B772 A2 L2 tunnel, 33 frames, gone; UAL59 B772 G1 L2 107 -> 39 points), but overlap.gnd 902 -> 1115 (the
# stale-parked / arriving pairs at G13 and G10 last 77 / 136 frames longer), a new bridge contact (ANZ7 B789 G10 L1 cab,
# 10 frames), UAL917's G7 L2 walkway contact 113 -> 134 points, bridge.orphan 5,389 -> 5,797, lag.gnd_30m 40,820 ->
# 41,408: collision frames (bridge.hit.* + overlap.gnd) 2,970 -> 3,162. Shipping code (HEAD 47af104): every collision /
# clearance class identical (hit_at_rest 22 frames either way), bridge.orphan 5,549 -> 6,011, lag.gnd_30m 43,322 ->
# 43,923. By the owner's rule (no collisions / clipping first) the re-choice gains nothing on the shipping code and is
# worse in sum on the older one, and it would replace mapped (OSM / build) rest poses by inferred ones for types never
# seen there. So the data rests stay; check_stands keeps reporting the accepted-type cases (WARN) and the rest per
# occupant is gates.js's (static_closeout.md R5.2 / R6.2).
P10_ACCEPTED = False


def _wing(o, t):
    k = (o['name'], t)
    if k not in _WING: _WING[k] = GM.wings(GM.nose_for(o, t), o['hdg'], t)
    return _WING[k]


def p10_rest(D, log):
    """close-out round 3 (2026-11-06, finding static-9): a rest pose (stow) that comes closer to the wings / engines /
    tailplane of an OBSERVED type (at its stop, on any stand within 150 m) - fix round 2 (verifier v7): or of any type a
    stand within 150 m ACCEPTS that stays parked while the bridge rests (neighbours; own-stand types it does not dock) -
    than the ICAO stand clearance (check_stands
    WARN 'at rest ... evidence conflict': F14 / F17 / F19 / F21 L1 2.5-5.0 m from a B752, G8 L2 2.8 m from an E75L, G13 L3
    6.9 m from a B772) is re-chosen where a pose exists that passes check_stands' rest tests AND keeps the ICAO clearance:
    the cab pivot on a circle round the rotunda (every 1 deg within 120 deg of the present direction, lengths from the
    model's retraction to +4 m), clear of every stand envelope within 150 m (<= 0.05 m2), of the SFO Museum terminal
    (<= 0.3 m2), of its own fixed walkway (<= 0.5 m2), not crossed by another bridge docked to a type its stand accepts
    (> 0.5 m2; as P7), and the rest + docked directions still in one 175 deg rotunda swing arc that does not hold the way
    back along the walkway, and (fix round 2) no further aft along the own stand's axis than the present rest (the
    pushback tail swing) and, when only accepted-not-observed types are too close, within +-30 deg of the present direction
    (the all-hours replay). The nearest such direction is taken (stow_src says so, inferred); else `stow_icao` records the
    best clearance reachable and why the rest stays."""
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    bld = unary_union([Polygon(p[0], p[1:]).buffer(0) for p in list(A['terminalComplex']) + [q for b in A['boardingAreas'] for q in b['polys']]])
    S = D['stands']; ENV = {}; FP = {}; sharers = {}
    for o in S:
        if o.get('shares_bridges_of'): sharers.setdefault(o['shares_bridges_of'], []).append(o)
    allb = [(st, b) for st in S for b in (st.get('bridges') or []) + (st.get('bridges_upper') or [])]
    def env(o):
        if o['name'] not in ENV: ENV[o['name']] = GM.stand_env(o)
        return ENV[o['name']]
    def docked(so0, ob):
        """[(type, cab pivot, footprint)] of bridge ob docked to every accepted type of its stand (+ sharers), as check_stands"""
        if id(ob) in FP: return FP[id(ob)]
        out = []
        if ob.get('door') != 3:
            pv_ = ob.get('rotunda') or ob['attach']; e0_, e1_ = ob.get('ext_range') or (GM.EXT_MIN, GM.EXT_MAX)
            for so in [so0] + sharers.get(so0['name'], []):
                rt = GM.rv(so['hdg'])
                for t in GM.accepted_types(so):
                    k = GM.dock_door(t, ob['door'])
                    if k is None: continue
                    dp = GM.door(GM.nose_for(so, t), so['hdg'], t, k)
                    cabp = (dp[0] - rt[0] * GM.PIVOT_TO_DOOR, dp[1] - rt[1] * GM.PIVOT_TO_DOOR)
                    if not (e0_ - 1.0 <= math.dist(pv_, cabp) <= e1_ + 1.0): continue
                    out.append((t, so, cabp, GM.bridge_parts(ob, cabp)[2]))
        FP[id(ob)] = out
        return out
    def rot_r(b): return max(0.01, b['rotunda_max_r']) if b.get('rotunda_max_r') is not None else GM.ROT_R
    def orest(ob): return GM.bridge_parts(ob, ob['stow'])[2] if ob.get('stow') else Point(0, 0).buffer(0)
    FX = {}
    def ofixed(ob):
        if id(ob) not in FX:
            wl_, rot_, _ = GM.bridge_parts(ob, ob.get('cab') or ob.get('stow') or ob['attach'])
            FX[id(ob)] = unary_union([wl_] + ([Point(ob['rotunda']).buffer(rot_r(ob))] if ob.get('rotunda') else []))
        return FX[id(ob)]
    for st, b in allb:
        if not b.get('stow') or not b.get('rotunda') or b.get('door') == 3: continue
        pv = b['rotunda']
        near = [o for o in S if math.dist(o['nose'], pv) < 150]
        # fix round 2 (verifier finding v7): besides the OBSERVED types (round 1), every type a stand within 150 m ACCEPTS
        # that stays parked while this bridge rests - a neighbour's types, and the own stand's types this bridge does not
        # dock (an L2 bridge beside a narrow-body) - must keep the ICAO clearance from the rest pose (G3 L2: B738 accepted,
        # 1.8 m; its WARN had ended only because SFO's newer plan put no B738 there)
        own_ = {st['name']} | {o['name'] for o in sharers.get(st['name'], [])}
        def parked_while_resting(o, t):
            return not (o['name'] in own_ and GM.dock_door(t, b['door']) is not None and t not in (b.get('dock_types_out') or []))
        wingsl = [(_wing(o, t), GM.icao_clear(GM.APP[t]['span']), t, o['name'], t in _obs(o))
                  for o in near for t in sorted(set(GM.accepted_types(o)) | _obs(o))
                  if t in GM.APP and GM.APP[t].get('span') and (t in _obs(o) or (P10_ACCEPTED and parked_while_resting(o, t)))]
        U_ = {}
        for w, need, t, on, ob in wingsl: U_.setdefault(need, []).append(w)
        U_ = {k: unary_union(v) for k, v in U_.items()}
        def margin(rb):
            m_ = min([(u.distance(rb) - need, need) for need, u in U_.items()] or [(9e9, 0)])
            if m_[0] >= 0: return (m_[0], m_[0] + m_[1], None, None)
            return min([(w.distance(rb) - need, w.distance(rb), t + ('' if ob else ' (accepted, not observed)'), on) for w, need, t, on, ob in wingsl])
        def restgeom(c): return GM.bridge_parts(b, c)[2].difference(Point(pv).buffer(rot_r(b) + 0.3))
        m0 = margin(restgeom(b['stow']))
        if m0[0] >= 0: continue
        tag = '%s L%s' % (st['name'], b.get('door'))
        e0 = (b.get('ext_range') or (GM.EXT_MIN, GM.EXT_MAX))[0]
        own = GM.bridge_parts(b, b.get('cab') or b['stow'])[0].difference(Point(pv).buffer(max(rot_r(b), GM.ROT_R) + 1.0))
        W = b.get('walk') or []
        wdir = None
        if len(W) >= 2:
            a_, b_ = W[-2], W[-1]; l_ = math.dist(a_, b_)
            if l_ > 0.5: wdir = ((b_[0] - a_[0]) / l_, (b_[1] - a_[1]) / l_)
        back = math.degrees(math.atan2(-wdir[1], -wdir[0])) if wdir else None
        mine = [x for x in docked(st, b) if x[0] not in (b.get('dock_types_out') or [])]
        ddirs = [math.degrees(math.atan2(c[1] - pv[1], c[0] - pv[0])) for _, _, c, _ in mine]
        a0 = math.degrees(math.atan2(b['stow'][1] - pv[1], b['stow'][0] - pv[0]))
        others = [(so, ob) for so, ob in allb if ob is not b and math.dist(ob.get('rotunda') or ob['attach'], pv) <= 90]
        # fix round 2 (all-hours replay): never further AFT than the present rest along the own stand's axis - behind the stop
        # lies the taxi-in / pushback sweep, whose tail swing (not a static envelope) reached G4 L2 turned +43 deg (UAL917
        # B772 pushing back 5 Nov 06:54Z: 378 hit points on the cab vs 47 before)
        def aft(g):
            cs = [c for gg in getattr(g, 'geoms', [g]) for c in gg.exterior.coords]
            return min(local(c, st['nose'], st['hdg'])[0] for c in cs) if cs else 0.0
        aft0 = aft(restgeom(b['stow']))
        # fix round 2 (all-hours replay): when only ACCEPTED-not-observed types are inside the clearance, the rest stays near
        # its present (OSM / build) direction: turns up to +-30 deg only. With +-120 the replay's G4 L2 swung 75 deg along the
        # facade and UAL917 B772's real pushback (5 Nov 06:54Z) then took a path into G7 L2's walkway (452 hit points)
        rb0 = restgeom(b['stow'])
        obs_viol = any(ob and w.distance(rb0) < need for w, need, t, on, ob in wingsl)
        max_turn = 120 if obs_viol else 30
        best = None; best_m = m0
        for da in sorted(range(-max_turn, max_turn + 1), key=abs):
            ang = a0 + da
            for L in np.arange(e0, e0 + 4.01, 1.0):
                c = (pv[0] + L * math.cos(math.radians(ang)), pv[1] + L * math.sin(math.radians(ang)))
                rb = restgeom(c); m = margin(rb)
                if aft(rb) < aft0 - 0.5: continue
                if m[0] > best_m[0]: best_m = m + (c, da)
                if m[0] < 0: continue
                if rb.intersection(bld).area > 0.3 or rb.intersection(own).area > 0.5: continue
                if any(rb.intersection(env(o)).area > 0.05 for o in near): continue
                # fix round 2: clear of the other bridges' rest poses (> 0.5 m2) and fixed walkways / rotundas (check_stands)
                rfull = GM.bridge_parts(b, c)[2]
                if any(rfull.intersection(orest(ob)).area > 0.5 or (ob['attach'] != b['attach'] and rb.intersection(ofixed(ob)).area > 0.5)
                       for so, ob in others): continue
                w_, ins = _arc(ddirs + [ang], back)
                if w_ > 2 * GM.ROT_SWING + 0.05 or ins: continue
                crossed = False
                for so, ob in others:
                    for t, so_, cabp, g in docked(so, ob):
                        if so_ is st and b['door'] <= 2 and GM.dock_door(t, b['door']) is not None and t not in (b.get('dock_types_out') or []): continue
                        if g.intersection(rb).area > 0.5: crossed = True; break
                    if crossed: break
                if crossed: continue
                best = (c, da, L, m); break
            if best: break
        if best:
            c, da, L, m = best; old = list(b['stow']); rb = restgeom(c)
            m = min([(w.distance(rb) - need, w.distance(rb), t + ('' if ob else ' (accepted, not observed)'), on) for w, need, t, on, ob in wingsl])
            b['stow'] = [round(c[0], 2), round(c[1], 2)]; b['stow_len'] = round(L, 1)
            b['stow_src'] = ('inferred: close-out round 3 (P10) - the rest pose turned %+d deg so that the parked tunnel / cab keep the ICAO '
                             'clearance to every type parked near it (nearest: %.1f m from the %s at %s; was %.1f m from the %s at %s); passes '
                             'check_stands\' rest tests' % (da, m[1], m[2], m[3], m0[1], m0[2], m0[3]))
            note(b, 'stow %s -> %s (P10: %+d deg, %.1f m from the %s at %s, ICAO %.1f; was %.1f m from the %s at %s)' % (
                old, b['stow'], da, m[1], m[2], m[3], m[1] - m[0], m0[1], m0[2], m0[3]), STAMP3)
            log.append('P10 %s rest turned %+d deg: %.1f m from the %s at %s (ICAO %.1f; was %.1f m from the %s at %s)' % (
                tag, da, m[1], m[2], m[3], m[1] - m[0], m0[1], m0[2], m0[3]))
        else:
            b['stow_icao'] = {'clearance_m': round(m0[1], 1), 'need_m': round(m0[1] - m0[0], 1), 'type': m0[2], 'at': m0[3],
                              'best_reachable_m': round(best_m[1], 1) if len(best_m) > 4 else round(m0[1], 1),
                              'why': 'no rest direction within +-120 deg / retraction..+4 m keeps the ICAO clearance and passes the rest tests (envelopes, '
                                     'terminal, own walkway, docked bridges, rotunda swing): kept'}
            log.append('P10 %s rest %.1f m from the %s at %s (ICAO %.1f): no compliant rest pose (best reachable %.1f m), kept' % (
                tag, m0[1], m0[2], m0[3], m0[1] - m0[0], b['stow_icao']['best_reachable_m']))


# ------------------------------------------------------------------------------------------------ P11
def p11_walk_nudge(D, log):
    """close-out round 3 (2026-11-06, finding static-12): js/live/gates.js prepGeom moves an interior vertex of a fixed
    walkway straight out of the drawn terminal outline (data/sfo_buildings.json complex + non-walkway parts) when the 2.6 m
    slab of an adjacent segment (not the first, which leaves the building) lies in it - by <= 0.5 m per step, <= 2.0 m in
    all (the OSM roof lean), towards the nearest outline point of the deepest slab point (A15 L1: the OSM line runs along
    the pier face, half the slab in Boarding Area A for 4 m; gates.js nudged it 1.6 m). The data now carries the same
    vertex, so gates.js no longer has to (walk_src says so, inferred)."""
    from shapely.prepared import prep
    from shapely.ops import nearest_points
    out_ = outline(); po = prep(out_); bnd = out_.boundary
    for st in D['stands']:
        for b in (st.get('bridges') or []) + (st.get('bridges_upper') or []):
            W = [list(q) for q in b.get('walk') or []]
            if len(W) < 3: continue
            moved = 0.0
            def deepest(i):
                best = None
                for j0, j1 in ((i - 1, i), (i, i + 1)):
                    if j0 == 0: continue
                    A_, B_ = W[j0], W[j1]; L = math.dist(A_, B_)
                    if L < 0.05: continue
                    u = ((B_[0] - A_[0]) / L, (B_[1] - A_[1]) / L); v = (-u[1], u[0])
                    for t in np.arange(0.0, L + 1e-6, 0.25):
                        for w in (-1, -0.5, 0, 0.5, 1):
                            x, z = A_[0] + u[0] * t + v[0] * w * WALK_HW, A_[1] + u[1] * t + v[1] * w * WALK_HW
                            if not po.contains(Point(x, z)): continue
                            q = nearest_points(bnd, Point(x, z))[0]; d = math.hypot(q.x - x, q.y - z)
                            if best is None or d > best[0]: best = (d, x, z, (q.x, q.y))
                return best
            for i in range(1, len(W) - 1):
                v0 = list(W[i])
                for _ in range(16):
                    Dp = deepest(i)
                    if not Dp: break
                    l = math.hypot(Dp[3][0] - Dp[1], Dp[3][1] - Dp[2]) or 1.0; m = min(0.5, Dp[0] + 0.1)
                    nv = [W[i][0] + (Dp[3][0] - Dp[1]) / l * m, W[i][1] + (Dp[3][1] - Dp[2]) / l * m]
                    if math.dist(nv, v0) > 2.0: break
                    W[i] = nv
                mv = math.dist(W[i], v0)
                if mv > 0.005:
                    W[i] = [round(W[i][0], 2), round(W[i][1], 2)]; moved = max(moved, mv)
                    note(b, 'walk vertex %d %s -> %s (%.2f m out of the drawn terminal outline: the 2.6 m slab lay in it; gates.js prepGeom rule)' % (i, v0, W[i], mv), STAMP3)
            if moved:
                b['walk'] = W
                b['walk_src'] = 'inferred: OSM fixed-walkway way with interior vertices moved up to %.2f m out of the drawn terminal outline (patch_stands P11, = gates.js prepGeom; OSM roof lean)' % moved
                log.append('P11 %s L%s walkway vertex moved %.2f m out of the drawn outline' % (st['name'], b.get('door'), moved))


# ------------------------------------------------------------------------------------------------ P7
def p7_stow_osm(D, log):
    """round 2 (2026-11-05; bridges_closeout.md s.1.7 / review bridges-v5: rest poses far from the imaged parked pose -
    G13 L3 30.9 m, F15 L2 23.3, B15 L1 22.1, F22 L2 19.0, F11 L2 11.6 ...): for every bridge whose `stow` lies > 3 m from
    the OSM parked cab (cab_pose 'parked': the cab as mapped on the imagery), the imaged pose is tested with
    build_stands.py's own rest criteria - clear of the envelope of every stand within 150 m by 1 m, of the wings / engines
    / tailplane of their OBSERVED types by the ICAO stand clearance, of the SFO Museum terminal / boarding areas (<= 0.1 m2
    outside the drum), length within the model's operational range (the build's 30 m search cap is not applied: the
    imaged pose is evidence), and not crossed (> 0.5 m2) by any other bridge within 90 m docked to a type its stand
    accepts (check_stands' docked poses; a sibling is exempt for the types this bridge docks itself). Passing -> `stow` = the OSM cab (stow_src 'osm parked cab'); else `stow_osm` records the
    distance and the failed criteria, i.e. why the rest pose is not the imaged one."""
    A = json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))
    bld = unary_union([Polygon(p[0], p[1:]).buffer(0) for p in list(A['terminalComplex']) + [q for b in A['boardingAreas'] for q in b['polys']]])
    S = D['stands']; ENV = {}; FP = {}
    sharers = {}
    for o in S:
        if o.get('shares_bridges_of'): sharers.setdefault(o['shares_bridges_of'], []).append(o)
    allb = [(st, b) for st in S for b in (st.get('bridges') or []) + (st.get('bridges_upper') or [])]
    def dock_fp(so0, ob):
        """{type: footprint} of bridge ob docked to every accepted type of its stand (+ sharers), as check_stands"""
        if id(ob) in FP: return FP[id(ob)]
        out = {}
        if ob.get('door') != 3:
            pv_ = ob.get('rotunda') or ob['attach']; e0_, e1_ = ob.get('ext_range') or (GM.EXT_MIN, GM.EXT_MAX)
            for so in [so0] + sharers.get(so0['name'], []):
                rt = GM.rv(so['hdg'])
                for t in GM.accepted_types(so):
                    k = GM.dock_door(t, ob['door'])
                    if k is None: continue
                    dp = GM.door(GM.nose_for(so, t), so['hdg'], t, k)
                    cabp = (dp[0] - rt[0] * GM.PIVOT_TO_DOOR, dp[1] - rt[1] * GM.PIVOT_TO_DOOR)
                    if not (e0_ - 1.0 <= math.dist(pv_, cabp) <= e1_ + 1.0): continue
                    out.setdefault(t, []).append(GM.bridge_parts(ob, cabp)[2])
        FP[id(ob)] = {t: unary_union(v) for t, v in out.items()}
        return FP[id(ob)]
    for st in S:
        for b in (st.get('bridges') or []) + (st.get('bridges_upper') or []):
            if not (b.get('cab') and b.get('stow') and b.get('cab_pose') == 'parked'): continue
            d0 = math.dist(b['cab'], b['stow'])
            if d0 <= 3.0: continue
            pv = b['rotunda']; rr = b.get('rotunda_max_r') or GM.ROT_R
            tc = GM.bridge_parts(b, b['cab'])[2].difference(Point(pv).buffer(rr + 0.3))
            near = [o for o in S if math.dist(o['nose'], pv) < 150]
            for o in near:
                if o['name'] not in ENV: ENV[o['name']] = GM.stand_env(o)
            env = min((tc.distance(ENV[o['name']]), o['name']) for o in near)
            wo = [(GM.wings(GM.nose_for(o, t), o['hdg'], t).distance(tc) - GM.icao_clear(GM.APP[t]['span']), t, o['name'])
                  for o in near for t in sorted(set(o.get('obs_types') or []) & set(GM.APP))]
            wm = min(wo) if wo else None
            L = math.dist(pv, b['cab']); e0, e1 = b.get('ext_range') or (GM.EXT_MIN, GM.EXT_MAX); ab = tc.intersection(bld).area
            why = []
            if env[0] < 1.0: why.append('%.2f m from the envelope of %s (< 1 m)' % env if env[0] > 0 else 'overlaps the envelope of %s' % env[1])
            if wm and wm[0] < 0: why.append('%.1f m inside the ICAO clearance of the observed %s at %s' % (-wm[0], wm[1], wm[2]))
            if ab > 0.1: why.append('%.1f m2 in the SFO Museum terminal outline' % ab)
            if not (e0 - 0.05 <= L <= e1 + 0.05): why.append('length %.1f m outside the model range %.1f-%.1f m' % (L, e0, e1))
            for so, ob in allb:
                if ob is b or math.dist(ob.get('rotunda') or ob['attach'], pv) > 90: continue
                hit = None
                for t, g in dock_fp(so, ob).items():
                    if so is st and b['door'] <= 2 and GM.dock_door(t, b['door']) is not None and t not in (b.get('dock_types_out') or []): continue
                    a_ = g.intersection(tc).area
                    if a_ > 0.5: hit = (so['name'], ob.get('door'), t, a_); break
                if hit: why.append('crossed by %s L%s docked to %s (%.1f m2)' % hit)
            tag = '%s L%s' % (st['name'], b.get('door'))
            if not why:
                old = list(b['stow']); b['stow'] = [round(b['cab'][0], 2), round(b['cab'][1], 2)]; b['stow_len'] = round(L, 1)
                b['stow_src'] = 'osm parked cab (imaged rest pose; passes the build\'s rest criteria: envelope %.2f m, ICAO margin %s)' % (
                    env[0], '%+.1f m' % wm[0] if wm else 'n/a')
                note(b, 'stow %s -> the OSM parked cab %s (%.1f m away; the imaged rest pose passes the build\'s rest criteria)' % (old, b['stow'], d0), STAMP2)
                log.append('P7 %s stow -> OSM parked cab (%.1f m; envelope %.2f m, ICAO %s)' % (tag, d0, env[0], '%+.1f' % wm[0] if wm else 'n/a'))
            else:
                b['stow_osm'] = {'dist_m': round(d0, 1), 'osm_len_m': round(L, 1), 'why_not': why}
                log.append('P7 %s stow %.1f m from the OSM parked cab, kept: %s' % (tag, d0, '; '.join(why)))


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
        per = {}
        for v in st['stays']:
            # round 3 (2026-11-05): stays are selected by GEOMETRY only (on this stand's lead-in: the gate below) with the
            # ADS-B type - not by adsb_parked.py's flysfo stand match / sfo_type, so P5 needs no flysfo-derived value
            # (tools/stands/flysfo_provenance.py). Was: v['stand'] in the stand's AODB names, type else sfo_type.
            t = v.get('type') if dims(v.get('type') or '') else None
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


def _sha(fn):
    import hashlib
    h = hashlib.sha256()
    with open(fn, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def p12_live(D, log):
    """P1 + P2 on the flysfo snapshot -> the replay record (per stand: the P12_FIELDS they changed)"""
    import copy
    before = {s['name']: copy.deepcopy(s) for s in D['stands']}
    n0 = len(log)
    wins = p1_aodb(D, log)
    p2_excl_types(D, wins, log)
    rec = {}
    for s in D['stands']:
        b = before[s['name']]
        ch = {k: s[k] for k in s if b.get(k, '<absent>') != s[k]}
        assert set(ch) <= set(P12_FIELDS) and not (set(b) - set(s)), 'P1 / P2 changed fields outside P12_FIELDS: %s' % sorted(set(ch) - set(P12_FIELDS))
        if ch: rec[s['name']] = ch
    return {'what': 'results of tools/stands/patch_stands.py P1 / P2 (SFO AODB plan of 4 Nov 2026) - the stand fields they set; '
                    'replayed when the local flysfo snapshot is missing (fresh clone). Contains only values data/sfo_stands.json '
                    'publishes; licence of the flysfo-derived fields: owner decision open (docs/ATTRIBUTION.md)',
            'base': os.path.relpath(BASE, ROOT), 'base_sha256': _sha(BASE),
            'snapshots': [{'file': 'refs/cache/gate_truth/' + fn, 'sha256': _sha(os.path.join(ROOT, 'refs', 'cache', 'gate_truth', fn))} for fn in FLYSFO_WINDOW2],
            'fields': list(P12_FIELDS), 'stands': rec, 'log': log[n0:]}


def p12_replay(D, log):
    R = json.load(open(P12_REPLAY))
    assert R['base_sha256'] == _sha(BASE), 'P12_REPLAY was recorded on another BASE'
    S = {s['name']: s for s in D['stands']}
    for n, ch in R['stands'].items():
        S[n].update(ch)
    log.extend(R['log'])
    return R


def main():
    D = json.load(open(BASE)); log = []
    have = all(os.path.exists(os.path.join(ROOT, 'refs', 'cache', 'gate_truth', fn)) for fn in FLYSFO_WINDOW2)
    if '--check' in sys.argv:
        if not have: print('--check needs the local flysfo snapshot(s): %s' % ', '.join(FLYSFO_WINDOW2)); sys.exit(2)
        R = json.load(open(P12_REPLAY)); L = p12_live(json.load(open(BASE)), [])
        same = L['stands'] == R['stands'] and L['log'] == R['log'] and L['snapshots'] == R['snapshots']
        print('P1 / P2 on the snapshot %s the replay (%d stands)' % ('MATCH' if same else 'DIFFER FROM', len(R['stands']))); sys.exit(0 if same else 1)
    if have and '--replay' not in sys.argv:
        R = p12_live(D, log)
        json.dump(R, open(P12_REPLAY, 'w'), indent=0)        # key order kept: the replay re-inserts the fields in it
        p12_mode = 'live (snapshot present); replay written to %s' % os.path.relpath(P12_REPLAY, ROOT)
    else:
        R = p12_replay(D, log)
        p12_mode = 'replayed from %s (snapshot %s)' % (os.path.relpath(P12_REPLAY, ROOT), 'missing' if not have else 'ignored: --replay')
    print('P1 / P2:', p12_mode)
    p8_family_ok(D, log)
    p3_rotunda(D, log)
    p6_drums(D, log)
    p11_walk_nudge(D, log)
    p7_stow_osm(D, log)
    p10_rest(D, log)
    p5_beyond(D, log)
    p9_antenna_ref(D, log)
    p13_stop_open(D, log)
    p4_src(D, log)     # after P5: a new conflict_along makes an obs stand inf
    D['fixups'] = [{'stage': 'tools/stands/patch_stands.py', 'stamp': STAMP, 'base': os.path.relpath(BASE, ROOT),
                    'evidence': {'flysfo': FLYSFO_WINDOW2, 'flysfo_replay': os.path.relpath(P12_REPLAY, ROOT) + ' (P1 / P2 results, used when the snapshot is missing)',
                                 'adsb_stays': os.path.relpath(ADSB_STAYS, ROOT),
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
