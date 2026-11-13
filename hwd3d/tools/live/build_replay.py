#!/usr/bin/env python3
"""Build the replay packs of Hayward Live 3D: real HWD traffic from adsb.lol recordings, for the app's replay mode
(the in-page fake relay, out/replay/replay_shim.js) and for the phone artifact (whose CSP blocks every live fetch).

Forked from sfo3d/tools/build3/replay_pack.py @ a967f9b. Kept: steps 1-4 and the v2 field-delta event encoding (each
event lists every aircraft present; an absent key is gone; p.d = [[key, {fields changed since this key's previous
record}, [fields removed]?], ...]). Changed: input = the committed adsb.lol rec_pack hours of sfo3d (no running relay
needed: a fresh clone can build a pack); the HWD window; D1 + --ident; METARs fetched from aviationweather.gov for the
window; hwd-pack/1 header fields (fork map 2.2); a leak check. Dropped: routes (none for GA), adsb.fi (never packed).

Source data: sfo3d/refs/cache/rec_pack/adsblol_*.jsonl.xz @ a967f9b - adsb.lol /v2 point-query answers recorded by
sfo3d's recorder, trimmed to 25 NM / 18,000 ft of SFO. HWD's ARP is 12.3 NM from SFO, so any window of <= 12.7 NM around
HWD lies wholly inside the trim. Licence ODbL 1.0 ("Contains information from ADSB.lol ...").

THE 46-S HOLES (read this before using a pack). The recorder polled adsb.lol about every 1.3 s until it was refused
(HTTP 429) after ~10 polls, then waited for the next minute (PLAN section 3; refs/cache/adsb/hwd_events.json): of each
minute only ~14 s are observed, then nothing for ~46 s (up to ~53 s). A pack therefore has bursts of events 1.3 s apart
and a hole of ~46 s every minute. The relay merge keeps a replay snapshot 75 s (REPLAY_SNAP_TTL), so aircraft do not
vanish in a hole; their records simply stop changing. The app must NOT dead-reckon across a hole (at 70 kt an aircraft
flies ~1.7 km in 46 s - a whole pattern leg) but display `lookahead_s` (60 s) behind the stream head, so that every hole
up to ~55 s lies between two real fixes and is interpolated (Hermite on the air, along the taxi graph on the ground,
data/hwd_taxigraph.json). The shim delivers the first `lookahead_s` of the window at once, so the first frame does not
wait. Each pack's meta lists its measured holes (`sampling`).

Windows (chosen with tools/live/rank_hours.py over all 111 rec_pack hours; counts as defined there: 'ground' = distinct
aircraft reporting ground within 1.5 km of the ARP, 'transitions' = ground -> airborne changes within 2.5 km seen between
consecutive fixes (the 46-s holes hide some), 'area' = distinct aircraft within 8 NM at <= 5,000 ft or on the ground):
  weekend  2026-11-08T20:00Z + 60 min  Sunday 12:00-13:00 PST: the most aircraft on the ground (26) and in the area (142)
                                      of any hour, 14 transitions (Sat 7 Nov 20Z: 22 / 125 / 19 is the close second)
  weekday  2026-11-09T21:00Z + 60 min  Monday 13:00-14:00 PST: pattern work, 18 transitions (2nd of all weekday hours;
                                      Wed 4 Nov 23Z has 19), 15 on the ground, 111 in the area
pack.json.gz = the weekend pack (default URL of the shim); pack_<name>.json.gz each; packs.json lists them.

Identity (D1; docs/phase2_fork_map.md 2.2, risk R11): --ident type-only (DEFAULT) strips flight, r, ownOp, year, squawk,
dbFlags, _mx from EVERY record and keys every aircraft as 'x' + 8 hex (salted HMAC, salt random per build and never
written); use it for anything that may be published (an artifact distributes the pack). --ident full keeps identity for
aircraft not flagged LADD/PIA (dbFlags & 12) and adds the local Mictronics `_mx`; local use only. Either way the pack is
generated into hwd3d/out/replay/ (gitignored) and never committed. A leak check walks every string of the written pack
and compares it with the original hex addresses, registrations and callsigns of the window (counts only are reported).

usage: python3 tools/live/build_replay.py                      # both presets, type-only
       python3 tools/live/build_replay.py --pack weekday --ident full
       python3 tools/live/build_replay.py --from 2026-11-07T19:00Z --minutes 45 --name sat
"""
import argparse, glob, gzip, json, math, os, re, shutil, sys, time, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import build_stream as B  # noqa: E402
import hwd_live_server as S  # noqa: E402
import recio  # noqa: E402

PRESETS = {'weekend': ('2026-11-08T20:00Z', 60.0, 'Sunday 8 Nov 2026, 12:00-13:00 PST (most aircraft on the field of the recording)'),
           'weekday': ('2026-11-09T21:00Z', 60.0, 'Monday 9 Nov 2026, 13:00-14:00 PST (weekday midday, pattern work)')}
DEFAULT_PACK = 'weekend'
RADIUS_NM = 8.0          # = the relay's area (D6 ~5 NM + 3 NM lead-in) [inf]
MAX_ALT_FT = 5000.0      # MSL; D6 shows < 3,000 ft AGL (= 3,052 ft MSL) - 1,950 ft of lead-in for descending traffic [inf]
LOOKAHEAD_S = 60.0       # fork map 2.1 / 2.2: display this far behind the stream head
# Record fields the app reads (fork map 2.1 contract; P3 normalizeAircraft)
KEEP = ('hex', 'type', 'flight', 'r', 't', 'desc', 'category', 'lat', 'lon', 'lastPosition', 'alt_baro', 'alt_geom',
        'gs', 'track', 'true_heading', 'mag_heading', 'track_rate', 'roll', 'baro_rate', 'geom_rate', 'squawk',
        'emergency', 'nav_altitude_mcp', 'nav_qnh', 'nic', 'nac_p', 'seen', 'seen_pos', 'mlat', 'tisb', 'dbFlags',
        '_pt', '_src', '_prov', '_veh', '_drop', '_masked', '_mx')
SHIM = os.path.join(HERE, 'replay_shim.js')
OUT = os.path.join(ROOT, 'out', 'replay')
ATTR = {'adsb': S.ATTRIBUTION['adsb'], 'metar': S.ATTRIBUTION['metar'], 'ident': S.ATTRIBUTION['ident']}


def iso(t): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))


def fetch_metars(t0, t1, wx_dir):
    """KHWD METARs observed in [t0 - 3 h, t1] (aviationweather.gov keeps "up to the previous 30 days of data"; one
    request per window, cached in out/replay/wx/). US Government work, public domain."""
    os.makedirs(wx_dir, exist_ok=True)
    fn = os.path.join(wx_dir, time.strftime('metar_khwd_%Y%m%dT%H%MZ', time.gmtime(t1)) + f'_{int((t1 - t0) / 3600) + 4}h.json')
    if not os.path.exists(fn):
        if time.time() - t1 > 29.5 * 86400:
            print('metar: window is older than the 30-day look-back of aviationweather.gov; no METAR in the pack')
            return []
        q = urllib.parse.urlencode({'ids': 'KHWD', 'format': 'json', 'date': iso(t1), 'hours': int((t1 - t0) / 3600) + 4})
        code, _, body = S.http_get(S.AWC + 'metar?' + q, timeout=30)
        if code != 200 or not body.strip().startswith(b'['):
            print('metar: HTTP', code, '- pack without METAR'); return []
        open(fn, 'wb').write(body)
    L = json.load(open(fn))
    return sorted(({'obsTime': m['obsTime'], 'rawOb': m['rawOb'], 'metarType': m.get('metarType')} for m in L
                   if m.get('rawOb') and t0 - 3 * 3600 <= m['obsTime'] <= t1), key=lambda m: -m['obsTime'])


def originals(rec, t0, t1, radius_nm, max_alt_ft, mx):
    """Identity strings of the window's original records (hex, registrations, callsigns, operators, Mictronics
    registrations) -> (all of them, those of LADD/PIA-flagged aircraft). For the leak check only: kept in memory,
    never written."""
    ids = {}; flagged = set()
    for t, pid, r in S.replay_records(rec, t0 - 120, t1):
        for a in S.window_filter(r['d'].get('ac'), radius_nm, max_alt_ft):
            hx = (a.get('hex') or '').lower()
            if not hx: continue
            s = ids.setdefault(hx, set()); s.add(hx)
            for k in ('r', 'flight', 'ownOp'):
                v = (a.get(k) or '').strip()
                if v: s.add(v.lower())
            if mx is not None:
                m = mx.lookup(hx, a.get('flight')) or {}
                if m.get('r'): s.add(m['r'].lower())
            try:
                if int(a.get('dbFlags') or 0) & 12: flagged.add(hx)
            except (TypeError, ValueError):
                pass
    allv = set().union(*ids.values()) if ids else set()
    flv = set().union(*(ids[h] for h in flagged)) if flagged else set()
    return allv, flv


def strings(o, acc):
    if isinstance(o, str): acc.add(o.strip().lower())
    elif isinstance(o, dict):
        for k, v in o.items(): strings(v, acc)
    elif isinstance(o, list):
        for v in o: strings(v, acc)
    return acc


def build(name, t0, minutes, desc, a, mx):
    t1 = t0 + minutes * 60.0
    st = {}; ev = []; state = {}; keys = set(); n_masked = set()
    for T, p in B.stream(t0, t1, a.rec, a.radius_nm, a.max_alt_ft, a.ident, a.ident == 'full', stats=st):
        rows = []
        for x in p.get('ac', []):
            r = {k: x[k] for k in KEEP if k in x}; h = r.get('hex')
            if h is None: continue
            keys.add(h)
            if r.get('_masked'): n_masked.add(h)
            o = state.get(h, {}); miss = object()
            ch = {k: v for k, v in r.items() if k != 'hex' and o.get(k, miss) != v}
            rm = [k for k in o if k not in r]
            rows.append([h, ch, rm] if rm else [h, ch]); state[h] = r
        q = {k: p[k] for k in ('now', 'dataNow', 'seq', '_source') if k in p}; q['d'] = rows
        ev.append({'T': round(T, 3), 'p': q})
    if not ev: sys.exit(f'{name}: no events in the window')
    gaps = sorted(st['gaps']); g = lambda f: round(gaps[min(len(gaps) - 1, int(f * len(gaps)))], 1) if gaps else None
    per = sorted(st['aircraft_per_poll'])
    metar = fetch_metars(t0, t1, os.path.join(a.out, 'wx'))
    sampling = {'ok_polls': st['ok_polls'], 'http429': B.http429_count(a.rec, t0, t1), 'events': len(ev),
                'gap_p50_s': g(0.5), 'gap_p90_s': g(0.9), 'max_gap_s': g(1.0),
                'gaps_over_30s': sum(1 for x in gaps if x > 30), 'gaps_over_55s': sum(1 for x in gaps if x > 55),
                'observed_s_per_min': round(sum(x for x in gaps if x <= 30) / max(1.0, minutes), 1),
                'aircraft_per_poll_median': per[len(per) // 2] if per else 0, 'aircraft_per_poll_max': per[-1] if per else 0}
    hours = sorted({time.strftime('%Y%m%d_%H', time.gmtime(t)) for t in (t0, t1 - 1)})
    attribution = [ATTR['adsb'], ATTR['metar']] + ([ATTR['ident']] if a.ident == 'full' and mx is not None else [])
    pack = {'v': 'hwd-pack/1', 'made_by': 'tools/live/build_replay.py', 'made_at': iso(time.time()), 'name': name,
            'desc': desc, 'source': {'rec_pack': 'sfo3d/refs/cache/rec_pack @ a967f9b', 'hours': hours,
                                     'provider': 'adsb.lol'},
            'licence': 'ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)', 'attribution': attribution,
            'attribution_map': {k: v for k, v in ATTR.items() if k != 'ident' or (a.ident == 'full' and mx is not None)},
            'from': ev[0]['T'], 'until': ev[-1]['T'], 'window': {'from': t0, 'until': t1}, 'lookahead_s': a.lookahead,
            'center': {'lat': S.ARP[0], 'lon': S.ARP[1], 'radius_nm': a.radius_nm},
            'filter': {'radius_nm': a.radius_nm, 'max_alt_ft': a.max_alt_ft, 'ground': True},
            'd1': {'rule': 'dbFlags & 4 (PIA) | dbFlags & 8 (LADD)', 'masked_aircraft': len(n_masked),
                   'flagged_aircraft': st.get('masked_flagged', 0), 'ident': a.ident},
            'ident': (mx.label() if (a.ident == 'full' and mx is not None and mx.ready) else None),
            'sampling': sampling, 'holes_note': 'adsb.lol recorder: ~14 s observed per minute, then a ~46 s hole; '
                                                'display lookahead_s behind and interpolate between real fixes',
            'events': ev, 'metar': metar}
    os.makedirs(a.out, exist_ok=True)
    fn = os.path.join(a.out, f'pack_{name}.json.gz')
    txt = json.dumps(pack, separators=(',', ':'))
    with gzip.open(fn, 'wt', compresslevel=9) as f: f.write(txt)
    # leak check: no string of the pack may equal an original identity it must not carry
    orig, flagged_ids = originals(a.rec, t0, t1, a.radius_nm, a.max_alt_ft, mx)
    found = strings(pack, set()) & orig
    if a.ident == 'full':     # full mode: none of the flagged aircraft's identities may appear
        bad = found & flagged_ids
        leak = {'mode': 'full', 'flagged_identities': len(flagged_ids), 'flagged_found': len(bad),
                'unflagged_identities_present': len(found - flagged_ids)}
        ok = not bad
    else:                     # type-only: no original identity at all
        leak = {'mode': 'type-only', 'original_identities': len(orig), 'found': len(found)}
        ok = not found
    meta = {k: v for k, v in pack.items() if k not in ('events', 'metar')}
    meta.update(file=os.path.basename(fn), bytes_gz=os.path.getsize(fn), bytes_json=len(txt), aircraft_keys=len(keys),
                metar_reports=len(metar), leak_check=dict(leak, ok=ok))
    json.dump(meta, open(os.path.join(a.out, f'pack_{name}_meta.json'), 'w'), indent=1)
    print(f'{fn}: {len(ev)} events {iso(pack["from"])} - {iso(pack["until"])}, {len(keys)} aircraft keys, '
          f'{len(n_masked)} masked, {len(metar)} METARs, {os.path.getsize(fn) / 1e6:.2f} MB gz ({len(txt) / 1e6:.1f} MB json); '
          f'sampling {sampling}; leak check {"OK" if ok else "FAILED"} {leak}')
    if not ok:
        os.remove(fn); sys.exit(f'{name}: leak check failed - pack deleted')
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--pack', choices=sorted(PRESETS) + ['all'], default='all')
    ap.add_argument('--from', dest='t_from'); ap.add_argument('--minutes', type=float, default=60.0)
    ap.add_argument('--name', help='name of a custom window (with --from)')
    ap.add_argument('--radius-nm', type=float, default=RADIUS_NM); ap.add_argument('--max-alt-ft', type=float, default=MAX_ALT_FT)
    ap.add_argument('--ident', choices=['type-only', 'full'], default='type-only')
    ap.add_argument('--lookahead', type=float, default=LOOKAHEAD_S)
    ap.add_argument('--rec', default=S.REC_PACK); ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    if not os.path.relpath(os.path.abspath(a.out), ROOT).startswith('out' + os.sep):
        sys.exit('--out must be under hwd3d/out/ (gitignored; never committed)')
    mx = S.Mictronics()
    while mx.enabled and not mx.ready and mx.err is None: time.sleep(0.2)
    if not mx.enabled: mx = None
    jobs = ([(a.name or 'custom', B.parse_t(a.t_from), a.minutes, f'custom window from {a.t_from}')] if a.t_from else
            [(n, B.parse_t(PRESETS[n][0]), PRESETS[n][1], PRESETS[n][2]) for n in (sorted(PRESETS) if a.pack == 'all' else [a.pack])])
    metas = [build(n, t0, m, d, a, mx) for n, t0, m, d in jobs]
    shutil.copyfile(SHIM, os.path.join(a.out, 'replay_shim.js'))
    idx_p = os.path.join(a.out, 'packs.json')
    idx = json.load(open(idx_p)) if os.path.exists(idx_p) else {'packs': {}}
    for m in metas:
        idx['packs'][m['name']] = {k: m[k] for k in ('file', 'desc', 'from', 'until', 'lookahead_s', 'bytes_gz',
                                                     'aircraft_keys', 'sampling', 'd1')}
    default = DEFAULT_PACK if os.path.exists(os.path.join(a.out, f'pack_{DEFAULT_PACK}.json.gz')) else metas[0]['name']
    shutil.copyfile(os.path.join(a.out, f'pack_{default}.json.gz'), os.path.join(a.out, 'pack.json.gz'))
    shutil.copyfile(os.path.join(a.out, f'pack_{default}_meta.json'), os.path.join(a.out, 'pack_meta.json'))
    idx.update(default=default, about='generated by tools/live/build_replay.py; never committed (hwd3d/.gitignore out/)')
    json.dump(idx, open(idx_p, 'w'), indent=1)
    print('default pack.json.gz =', default, '; shim ->', os.path.join(a.out, 'replay_shim.js'))


if __name__ == '__main__':
    main()
