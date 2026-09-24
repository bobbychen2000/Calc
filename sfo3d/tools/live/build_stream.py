#!/usr/bin/env python3
"""Offline twin of the relay's SSE stream: replays the recorder files through sfo_live_server.py's own Hub (the same
merge + hygiene code the live relay runs), as fast as possible on a simulated clock, and writes every published full
payload (what /api/stream sends as `event: adsb`) with the time the relay would have sent it.

Why: tools/live/replay_engine.mjs then feeds the app's traffic engine exactly the event sequence a browser would
have received live (every provider response that changed something = one SSE event), so metrics measured on the
replay are metrics of the real-time app, on real traffic.

Clock: the Hub reads time.time(); here it is patched to a fake clock set to each response's receive time `tr` (the
recorder logs request start `t` and receive time `tr`). Output lines: {"T": send time (epoch s), "p": payload}.
Usage: python3 tools/live/build_stream.py --from 2026-09-24T15:13Z [--until ...] [--out refs/cache/replay_day/stream.jsonl.gz]
"""
import argparse, datetime as dt, gzip, json, os, sys, time as _time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
import sfo_live_server as S  # noqa: E402


class FakeTime:
    def __init__(self): self.t = 0.0
    def time(self): return self.t
    def __getattr__(self, k): return getattr(_time, k)


def parse_t(s):
    if s is None: return None
    try: return float(s)
    except ValueError: return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='t0', required=True); ap.add_argument('--until', dest='t1')
    ap.add_argument('--rec', default=os.path.join(ROOT, 'refs/cache/rec'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'refs/cache/replay_day/stream.jsonl.gz'))
    ap.add_argument('--gates-every', type=float, default=60.0, help='also dump the relay /api/gates plan every N s (0 = off)')
    o = ap.parse_args()
    t0, t1 = parse_t(o.t0), parse_t(o.t1)
    ft = FakeTime(); S.time = ft
    hub = S.Hub(mode='replay')
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    n = pub = 0; last_seq = 0; first = last = None
    # SFO's plan as /api/gates would have served it at that time (cached flysfo snapshots <= 30 min after T; identity
    # clock). Slimmed to what the app uses (byCallsign stand windows, regional aliases) -> gates.jsonl.gz
    gates = S.Gates(enabled=True, hub=hub, replay_clock=S.Clock()) if o.gates_every > 0 else None
    gout = gzip.open(os.path.join(os.path.dirname(o.out), 'gates.jsonl.gz'), 'wt') if gates else None
    next_g = None
    with gzip.open(o.out, 'wt') as f:
        for t, pid, r in S.replay_records(o.rec, t0, t1):
            ft.t = r.get('tr') or t
            prov = S.PROVIDERS[pid]
            hub.ingest(prov, r['t'], ft.t, r['d'])
            n += 1
            if hub.seq != last_seq:
                last_seq = hub.seq; pub += 1
                f.write('{"T":%.3f,"p":' % ft.t + hub.full.decode() + '}\n')
                first = first or ft.t; last = ft.t
            if gates and (next_g is None or ft.t >= next_g):
                next_g = ft.t + o.gates_every
                P = gates.payload()
                slim = {'byCallsign': {k: {'stand': v['stand']} for k, v in P.get('byCallsign', {}).items() if v.get('stand')},
                        'aliases': {k: {'to': v.get('to')} for k, v in P.get('aliases', {}).items() if v.get('to')}}
                gout.write(json.dumps({'T': ft.t, 'gates': slim}, separators=(',', ':')) + '\n')
    if gout: gout.close()
    print(f'{o.out}: {n} provider responses -> {pub} published events, {S.time.strftime("%H:%M:%S", _time.gmtime(first or 0))}'
          f'-{_time.strftime("%H:%M:%S", _time.gmtime(last or 0))} UTC; counters {hub.counters}')


if __name__ == '__main__':
    main()
