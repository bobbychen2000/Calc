#!/usr/bin/env python3
"""Offline twin of the relay's SSE stream: replays adsb.lol recordings through hwd_live_server.py's own Hub (the same
merge + hygiene + Mictronics + D1 code the live relay runs), as fast as possible on a simulated clock, and yields every
published full payload (what /api/stream sends as `event: adsb`) with the time the relay would have sent it.

Forked from sfo3d/tools/live/build_stream.py @ a967f9b. Kept: the FakeTime trick (the Hub reads time.time(); here it is
set to each response's receive time `tr`) and the output line {"T": send time (epoch s, recording clock), "p": payload}.
Changed: imports hwd_live_server; input defaults to the committed rec_pack (.jsonl.xz); each response is cut to the HWD
window (relay window_filter: radius around the NASR ARP, optional altitude ceiling) before the merge, exactly as
`--replay` does; snapshot TTL = the relay's replay TTL (75 s, covers the recorder's 46-s holes); D1 mode and the
Mictronics lookup are parameters; also usable as a library (stream()). Dropped: the flysfo gates dumps.

Usage: python3 tools/live/build_stream.py --from 2026-11-08T20:00Z --until 2026-11-08T21:00Z [--radius-nm 8]
          [--max-alt-ft 5000] [--ident full|type-only] [--no-mictronics] --out out/replay/stream.jsonl.gz
The output holds identities unless --ident type-only: write it under out/ (gitignored) only.
"""
import argparse, datetime as dt, gzip, json, os, sys, time as _time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
import hwd_live_server as S  # noqa: E402


class FakeTime:
    def __init__(self): self.t = 0.0
    def time(self): return self.t
    def __getattr__(self, k): return getattr(_time, k)


def parse_t(s):
    if s is None: return None
    try: return float(s)
    except ValueError: return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def stream(t0, t1, rec=S.REC_PACK, radius_nm=S.RADIUS_NM, max_alt_ft=None, ident_mode='full', mictronics=True,
           salt=None, stats=None):
    """Yield (T, payload dict) for every published merge of the window. stats (dict) receives sampling counters."""
    ident = None
    if mictronics:
        ident = S.Mictronics()
        while ident.enabled and not ident.ready and ident.err is None:
            _time.sleep(0.2)                          # loaded before the clock is faked
    ft = FakeTime(); real = S.time; S.time = ft
    try:
        hub = S.Hub(mode='replay', ident=ident, d1=S.D1(ident_mode, salt=salt))
        last_seq = 0; last_tr = None
        st = stats if stats is not None else {}
        st.update(ok_polls=0, gaps=[], aircraft_per_poll=[])
        for t, pid, r in S.replay_records(rec, t0 - 120.0 if t0 else None, t1):
            ft.t = r.get('tr') or t
            d = dict(r['d']); d['ac'] = S.window_filter(d.get('ac') if 'ac' in d else d.get('aircraft'),
                                                           radius_nm, max_alt_ft)
            hub.ingest(S.PROVIDERS[pid], r['t'], ft.t, d, ttl=S.REPLAY_SNAP_TTL)
            if t0 is not None and ft.t < t0:
                last_tr = ft.t; continue              # warm-up: the 2 min before the window seed the merge memory
            st['ok_polls'] += 1; st['aircraft_per_poll'].append(len(d['ac']))
            if last_tr is not None: st['gaps'].append(ft.t - last_tr)
            last_tr = ft.t
            if hub.seq != last_seq:
                last_seq = hub.seq
                yield ft.t, json.loads(hub.full)
        st['counters'] = dict(hub.counters); st['masked_flagged'] = len(hub.d1.flagged)
    finally:
        S.time = real


def http429_count(rec, t0, t1):
    """HTTP 429 lines of the recorder in [t0, t1] (the rec_pack keeps failure lines too)."""
    import glob, re
    sys.path.insert(0, HERE); import recio
    n = 0
    for p in sorted(glob.glob(os.path.join(rec, 'adsblol_*.jsonl.*'))):
        h = re.search(r'_(\d{8}_\d{2})\.jsonl', p)
        hs = dt.datetime.strptime(h.group(1), '%Y%m%d_%H').replace(tzinfo=dt.timezone.utc).timestamp()
        if hs + 3600 < t0 or hs > t1: continue
        for r in recio.lines(p):
            if r.get('code') == 429 and t0 <= (r.get('tr') or r['t']) <= t1: n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='t0', required=True); ap.add_argument('--until', dest='t1', required=True)
    ap.add_argument('--rec', default=S.REC_PACK)
    ap.add_argument('--radius-nm', type=float, default=S.RADIUS_NM); ap.add_argument('--max-alt-ft', type=float)
    ap.add_argument('--ident', choices=['full', 'type-only'], default='full')
    ap.add_argument('--no-mictronics', action='store_true')
    ap.add_argument('--out', required=True)
    o = ap.parse_args()
    rel = os.path.relpath(os.path.abspath(o.out), ROOT)
    if not rel.startswith('out' + os.sep):
        sys.exit('--out must be under hwd3d/out/ (gitignored): the stream holds identities')
    os.makedirs(os.path.dirname(os.path.abspath(o.out)), exist_ok=True)
    st = {}; n = 0; first = last = None
    with gzip.open(o.out, 'wt') as f:
        for T, p in stream(parse_t(o.t0), parse_t(o.t1), o.rec, o.radius_nm, o.max_alt_ft, o.ident,
                           not o.no_mictronics, stats=st):
            f.write(json.dumps({'T': round(T, 3), 'p': p}, separators=(',', ':')) + '\n'); n += 1
            first = first or T; last = T
    print(f'{o.out}: {st.get("ok_polls")} responses -> {n} published events, '
          f'{_time.strftime("%H:%M:%S", _time.gmtime(first or 0))}-{_time.strftime("%H:%M:%S", _time.gmtime(last or 0))} '
          f'UTC; counters {st.get("counters")}')


if __name__ == '__main__':
    main()
