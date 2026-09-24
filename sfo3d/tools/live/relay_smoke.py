#!/usr/bin/env python3
"""End-to-end smoke test of a running relay (sfo_live_server.py, live or --replay). Standard library only.

  python3 tools/live/relay_smoke.py [http://127.0.0.1:8000] [seconds=60] [--delta]

Reads /api/stream for the given time and reports: events and their spacing, aircraft counts, which provider supplied
the positions, position ages, SFO surface/approach counts; with --delta it rebuilds the list from delta events and
compares it with /api/adsb at the end. Then checks /api/ping, /api/status, /api/metar, /api/routeset (for the callsigns
on the stream) and /api/gates (callsign and regional-alias matches for the aircraft on the stream).
Exit code 1 if an endpoint fails or the stream delivered nothing.
"""
import json, math, sys, time, urllib.request, gzip

args = [a for a in sys.argv[1:] if not a.startswith('--')]
BASE = (args[0] if args else 'http://127.0.0.1:8000').rstrip('/')
SECS = float(args[1]) if len(args) > 1 else 60.0
DELTA = '--delta' in sys.argv
ARP = (37.6188056, -122.3754167)
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path, data=None, timeout=30):
    req = urllib.request.Request(BASE + path, data=data, headers={'Accept-Encoding': 'gzip', 'Content-Type': 'application/json'})
    with NO_PROXY.open(req, timeout=timeout) as r:
        b = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            b = gzip.decompress(b)
        return r.status, r.headers.get('Content-Type'), b


def dist_nm(lat, lon):
    dy = (lat - ARP[0]) * 60.0
    dx = (lon - ARP[1]) * 60.0 * math.cos(math.radians(ARP[0]))
    return math.hypot(dx, dy)


def stream(delta=DELTA, by_seq=None):
    """-> (events, gaps between events, final state). by_seq: dict filled with {seq: {hex: (lat, lon)}}."""
    evs, t_prev, gaps = [], None, []
    state = {}
    req = urllib.request.Request(BASE + '/api/stream' + ('?delta=1' if delta else ''))
    t_end = time.time() + SECS
    with NO_PROXY.open(req, timeout=SECS + 30) as r:
        ev, data = None, []
        while time.time() < t_end:
            line = r.readline()
            if not line:
                break
            line = line.decode().rstrip('\n')
            if line.startswith('event:'):
                ev = line[6:].strip()
            elif line.startswith('data:'):
                data.append(line[5:].strip())
            elif line == '' and data:
                t = time.time()
                j = json.loads(''.join(data))
                data = []
                if t_prev is not None:
                    gaps.append(t - t_prev)
                t_prev = t
                if ev == 'adsb':
                    state = {a['hex']: a for a in j['ac']}
                elif ev == 'delta':
                    for a in j['ac']:
                        state[a['hex']] = a
                    for k in j.get('gone', []):
                        state.pop(k, None)
                evs.append((t, ev, j))
                if by_seq is not None:
                    by_seq[j['seq']] = {k: (a.get('lat'), a.get('lon'), a.get('flight'), a.get('_pt')) for k, a in state.items()}
    return evs, gaps, state


def q(a, f):
    a = sorted(a)
    return round(a[min(len(a) - 1, int(f * len(a)))], 2) if a else None


def main():
    fails = []
    st, ct, b = get('/api/ping')
    ping = json.loads(b)
    print('ping:', {k: ping.get(k) for k in ('v', 'mode', 'stream', 'delta', 'features')})
    ref = {}
    if DELTA:   # a full-list stream alongside: the delta-rebuilt state must equal it at every common seq
        import threading
        th = threading.Thread(target=stream, kwargs={'delta': False, 'by_seq': ref}, daemon=True)
        th.start()
    mine = {}
    evs, gaps, state = stream(by_seq=mine)
    if not evs:
        print('stream: NOTHING received')
        fails.append('stream')
    else:
        kinds = {}
        for _, e, _ in evs:
            kinds[e] = kinds.get(e, 0) + 1
        last = evs[-1][2]
        ac = list(state.values())
        src = {}
        for a in ac:
            src[a.get('_src')] = src.get(a.get('_src'), 0) + 1
        ages = [a['seen_pos'] for a in ac if 'seen_pos' in a]
        near = [a for a in ac if 'lat' in a and dist_nm(a['lat'], a['lon']) < 3]
        ground = [a for a in near if a.get('alt_baro') == 'ground']
        seqs = [j['seq'] for _, _, j in evs]
        print(f'stream: {len(evs)} events {kinds} in {SECS:.0f} s; spacing p50 {q(gaps, .5)} p90 {q(gaps, .9)} max {q(gaps, 1)} s;'
              f' seq {seqs[0]}..{seqs[-1]}')
        print(f'  aircraft {len(ac)} (payload total {last.get("total")}), source {last.get("_source")}; position from {src};'
              f' seen_pos p50 {q(ages, .5)} p90 {q(ages, .9)} s; within 3 NM {len(near)} ({len(ground)} on the ground,'
              f' vehicles {sum(1 for a in near if a.get("_veh"))})')
        print('  provenance _prov:', {p: sum(1 for a in ac if a.get('_prov') == p) for p in sorted({a.get('_prov') for a in ac})},
              '; surface fields dropped:', sum(1 for a in ac if a.get('_drop')))
        if DELTA:
            th.join(timeout=10)
            common = sorted(set(ref) & set(mine))
            bad = [sq for sq in common if ref[sq] != mine[sq]]
            print(f'  delta rebuild vs full stream: {len(common)} common seqs, {len(bad)} differ'
                  + (f' (first {bad[0]}: {len(set(ref[bad[0]]) ^ set(mine[bad[0]]))} key diffs)' if bad else ''))
            if bad or not common:
                fails.append('delta')
    _, _, b = get('/api/status')
    s = json.loads(b)
    for name, p in (s.get('providers') or {}).items():
        print(f'status {name}: req {p["requests"]} ok {p["ok"]} 429 {p["http429"]} err {p["errors"]} dup {p["duplicates"]}'
              f' lat p50 {p["latency_ms_p50"]} ms, start-now p50 {p["request_minus_now_s_p50"]} s, floor {p.get("floor_s")}'
              f' last10 {p.get("last_10min")} last_error {p["last_error"]}')
    print('status merge:', {k: s['merge'][k] for k in ('mode', 'seq', 'aircraft', 'position_from', 'vehicles', 'clients')},
          s['merge']['counters'])
    try:
        _, ct, b = get('/api/metar')
        print('metar:', b.decode()[:100].strip())
    except Exception as e:
        print('metar: FAILED', e)
        fails.append('metar')
    cs = sorted({(a.get('flight') or '').strip() for a in state.values() if a.get('flight') and 'lat' in a})
    planes = [{'callsign': c, 'lat': a['lat'], 'lng': a['lon']} for c in cs[:100]
              for a in [next(x for x in state.values() if (x.get('flight') or '').strip() == c)]]
    try:
        t0 = time.time()
        _, _, b = get('/api/routeset', json.dumps({'planes': planes}).encode(), timeout=120)
        rs = json.loads(b)
        known = [r for r in rs if r.get('_airport_codes_iata') != 'unknown']
        sfo = [r for r in known if r.get('_sfo')]
        print(f'routes: {len(rs)}/{len(planes)} answered in {time.time() - t0:.1f} s, {len(known)} known, {len(sfo)} via SFO,'
              f' plausible {sum(1 for r in known if r.get("plausible"))}; source {rs[0].get("_src") if rs else None};'
              f' e.g. {[(r["callsign"], r["_airport_codes_iata"]) for r in sfo[:5]]}')
    except Exception as e:
        print('routes: FAILED', e)
        fails.append('routes')
    try:
        _, _, b = get('/api/gates?cs=' + ','.join(cs), timeout=90)
        g = json.loads(b)
        if not g.get('enabled'):
            print('gates: disabled', g.get('reason'))
        else:
            import importlib.util, os
            spec = importlib.util.spec_from_file_location('S', os.path.join(os.path.dirname(__file__), '..', '..', 'sfo_live_server.py'))
            S = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(S)
            bc, al = g['byCallsign'], g['aliases']
            hit = [c for c in cs if S.norm_cs(c) in bc]
            parked = [(c, bc[S.norm_cs(c)]['stand']['name']) for c in hit if bc[S.norm_cs(c)].get('stand')]
            print(f'gates: fetched_at {g.get("fetched_at")} age {g.get("age_s")} s, records {g.get("records")}, error {g.get("error")};'
                  f' {len(bc)} callsigns, {len(g["byStand"])} stands with windows; {len(hit)}/{len(cs)} stream callsigns listed,'
                  f' {len(parked)} with a current stand, e.g. {parked[:6]}')
            for k, v in list(al.items())[:12]:
                print(f'  alias {k} -> {v["to"]} (candidates {v["candidates"]}, checks {v["checks"]}, score {v["score"]})')
    except Exception as e:
        print('gates: FAILED', e)
        fails.append('gates')
    if fails:
        print('FAILED:', fails)
        sys.exit(1)


if __name__ == '__main__':
    main()
