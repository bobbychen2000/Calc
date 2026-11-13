#!/usr/bin/env python3
"""End-to-end smoke test of the HWD relay (hwd_live_server.py), runnable OFFLINE: by default it starts the relay itself
in replay mode on the committed adsb.lol rec_pack, reads /api/stream, and checks every endpoint and serving rule.

Forked from sfo3d/tools/live/relay_smoke.py @ a967f9b. Kept: the SSE reader, delta reconstruction compared with
/api/adsb, position-age and provider statistics. Changed: spawns the relay (--spawn, default) on a free port in 8700-8799;
HWD window counts; D1 checks (masked keys and fields); hole behaviour (the picture must not empty between the recorder's
bursts); /api/stream?history; /api/ident; static deny rules (refs/cache/local, out/ except out/replay, tools, dotfiles).
Dropped: routeset and gates checks.

  python3 tools/live/relay_smoke.py                       # spawn: --replay rec_pack --from 2026-11-08T20:00Z --speed 4
  python3 tools/live/relay_smoke.py --secs 60 --speed 1 --from 2026-11-09T21:00Z
  python3 tools/live/relay_smoke.py --url http://127.0.0.1:8000 --secs 60   # an already running relay (live or replay)
Exit code 1 if a check fails. Output: counts only (no identities).
"""
import argparse, gzip, json, math, os, re, socket, subprocess, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ARP = (37.65893166, -122.12173888)
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))
FAIL = []


def check(ok, what):
    print(('  ok   ' if ok else '  FAIL ') + what)
    if not ok:
        FAIL.append(what)


def get(base, path, timeout=30):
    req = urllib.request.Request(base + path, headers={'Accept-Encoding': 'gzip'})
    try:
        with NO_PROXY.open(req, timeout=timeout) as r:
            b = r.read()
            if r.headers.get('Content-Encoding') == 'gzip':
                b = gzip.decompress(b)
            return r.status, r.headers, b
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read() or b''


def free_port():
    for p in range(8700, 8800):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', p)); return p
            except OSError:
                continue
    raise SystemExit('no free port in 8700-8799')


def dist_nm(lat, lon):
    dy = (lat - ARP[0]) * 60.0; dx = (lon - ARP[1]) * 60.0 * math.cos(math.radians(ARP[0]))
    return math.hypot(dx, dy)


def stream(base, secs, delta, history=0):
    """-> list of (t, event, payload, state after it)."""
    evs, state = [], {}
    q = '?' + '&'.join(x for x in (('delta=1' if delta else ''), (f'history={history}' if history else '')) if x)
    req = urllib.request.Request(base + '/api/stream' + (q if q != '?' else ''))
    t_end = time.time() + secs
    with NO_PROXY.open(req, timeout=secs + 30) as r:
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
                j = json.loads(''.join(data)); data = []
                if ev == 'adsb':
                    state = {a['hex']: a for a in j['ac']}
                elif ev == 'delta':
                    for a in j['ac']:
                        state[a['hex']] = a
                    for k in j.get('gone', []):
                        state.pop(k, None)
                evs.append((time.time(), ev, j, dict(state)))
    return evs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url'); ap.add_argument('--secs', type=float, default=40.0)
    ap.add_argument('--from', dest='t_from', default='2026-11-08T20:00Z'); ap.add_argument('--speed', type=float, default=4.0)
    ap.add_argument('--keep', action='store_true', help='leave the spawned relay running')
    a = ap.parse_args()
    proc = None
    if a.url:
        base = a.url.rstrip('/')
    else:
        port = free_port(); base = f'http://127.0.0.1:{port}'
        cmd = [sys.executable, os.path.join(ROOT, 'hwd_live_server.py'), '--port', str(port), '--replay', 'rec_pack',
               '--from', a.t_from, '--speed', str(a.speed), '--quiet']
        print('spawn:', ' '.join(cmd[1:]))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(100):
            try:
                if get(base, '/api/ping', 2)[0] == 200:
                    break
            except OSError:
                time.sleep(0.2)
    try:
        run(base, a)
    finally:
        if proc and not a.keep:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print('\nRESULT:', 'PASS' if not FAIL else f'FAIL ({len(FAIL)}): ' + '; '.join(FAIL))
    sys.exit(1 if FAIL else 0)


def run(base, a):
    print('ping')
    code, _, b = get(base, '/api/ping'); p = json.loads(b)
    check(code == 200 and p.get('hwdlive') == 1, 'ping hwdlive == 1')
    check(p.get('features', {}).get('metar') == 'KHWD' and p['features'].get('taf') is None, 'features metar KHWD, taf null')
    check(p.get('features', {}).get('d1') == 'dbFlags & 12', 'features.d1')
    check(abs(p['center']['lat'] - ARP[0]) < 1e-6 and p['center']['radius_nm'] >= 8, 'center = HWD ARP, radius >= 8 nm')
    replay = p.get('mode') == 'replay'
    if replay:
        check(p['features']['replay']['lookahead_s'] == 60, 'replay lookahead_s 60')
    print(f'stream {a.secs:.0f} s (delta)')
    samples = []
    def sampler():
        t_end = time.time() + a.secs - 2
        while time.time() < t_end:
            time.sleep(2.0)
            try:
                c, _, bb = get(base, '/api/adsb'); jj = json.loads(bb)
                samples.append((jj['seq'], {x['hex'] for x in jj['ac']}))
            except OSError:
                pass
    import threading
    th = threading.Thread(target=sampler, daemon=True); th.start()
    evs = stream(base, a.secs, True)
    th.join(5)
    check(len(evs) >= 5, f'{len(evs)} stream events')
    kinds = {}
    for _, ev, _, _ in evs:
        kinds[ev] = kinds.get(ev, 0) + 1
    print('   events by kind', kinds)
    counts = [len(s) for _, _, _, s in evs]
    if counts:
        print(f'   aircraft per event: min {min(counts)} median {sorted(counts)[len(counts) // 2]} max {max(counts)}')
    # holes: the picture must not empty between bursts (snapshot TTL 75 s / speed)
    drops = sum(1 for i in range(1, len(counts)) if counts[i - 1] >= 5 and counts[i] == 0)
    check(drops == 0, f'no event emptied the picture between bursts (drops {drops})')
    if len(evs) > 2:
        gaps = sorted(evs[i][0] - evs[i - 1][0] for i in range(1, len(evs)))
        print(f'   gaps between events (wall s): p50 {gaps[len(gaps) // 2]:.1f}  max {gaps[-1]:.1f}')
    # delta reconstruction vs /api/adsb: samples taken during the stream, compared with the stream state at the same seq
    by_seq = {e[2]['seq']: set(e[3]) for e in evs}
    cmp = [(sq, keys == by_seq[sq]) for sq, keys in samples if sq in by_seq]
    check(bool(cmp) and all(ok for _, ok in cmp),
          f'delta reconstruction == /api/adsb at {sum(ok for _, ok in cmp)}/{len(cmp)} sampled seqs')
    code, _, b = get(base, '/api/adsb'); j = json.loads(b)
    recs = j['ac']
    far = [x for x in recs if x.get('lat') is not None and dist_nm(x['lat'], x['lon']) > (p['center']['radius_nm'] + 0.2)]
    check(not far, f'all {len(recs)} records inside the radius ({len(far)} outside)')
    masked = [x for x in recs if x.get('_masked')]
    check(all(re.fullmatch(r'x[0-9a-f]{8}', x['hex']) for x in masked), f'{len(masked)} masked records keyed x+8hex')
    leak = [x for x in masked if any(f in x for f in ('flight', 'r', 'ownOp', 'year', 'squawk', 'dbFlags', '_mx', '_dbalt'))]
    check(not leak, 'masked records carry no identity field')
    flagged_clear = [x for x in recs if not x.get('_masked') and (int(x.get('dbFlags') or 0) & 12)]
    check(not flagged_clear, 'no LADD/PIA-flagged record left unmasked')
    print('   sources', {s: sum(1 for x in recs if x.get('_src') == s) for s in {x.get('_src') for x in recs}},
          ' with _mx', sum(1 for x in recs if x.get('_mx')), ' ground', sum(1 for x in recs if x.get('alt_baro') == 'ground'))
    print('history')
    t0 = time.time(); h = stream(base, 1.5, False, history=60)
    check(len(h) >= 2 if len(evs) > 3 else True, f'?history=60 sent {len(h)} payloads at once ({time.time() - t0:.1f} s)')
    print('ident')
    if masked:
        code, _, b = get(base, '/api/ident?key=' + masked[0]['hex']); v = json.loads(b)
        check(code == 200 and v.get('masked') is True and set(v) <= {'key', 'masked', 't', 'desc', 'category'},
              'ident of a masked key: type only')
    clear = [x for x in recs if not x.get('_masked') and not x['hex'].startswith('~')]
    if clear:
        code, _, b = get(base, '/api/ident?key=' + clear[0]['hex'])
        check(code == 200 and json.loads(b).get('masked') is False, 'ident of an unmasked key answers')
    check(get(base, '/api/ident?key=000000')[0] == 404, 'ident of a key not in the picture: 404')
    print('metar')
    code, hd, b = get(base, '/api/metar?ids=KHWD&format=json')
    if code == 200:
        L = json.loads(b)
        dn = int(hd.get('X-Data-Now') or 0) / 1000
        check(bool(L) and all(m['obsTime'] <= dn + 1 for m in L) if replay else bool(L),
              f'metar: {len(L)} reports, newest {L[0]["rawOb"][:24] if L else None}' + (' (none after replay time)' if replay else ''))
    else:
        check(False, f'metar HTTP {code}: {b[:120]!r} (replay needs out/replay/wx/ from tools/live/build_replay.py)')
    check(get(base, '/api/metar?ids=KSFO')[0] == 400, 'metar of another station: 400')
    print('status / removed endpoints / serving rules')
    code, _, b = get(base, '/api/status'); s = json.loads(b)
    check(code == 200 and 'merge' in s, f'status: masked_now {s["merge"].get("masked_now")}, d1 {s["merge"].get("d1_mode")}')
    for e in ('/api/gates', '/api/routeset', '/api/taf'):
        check(get(base, e)[0] == 404, f'{e} 404')
    req = urllib.request.Request(base + '/?mode=replay')
    class NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *x, **k): return None
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedir)
    try:
        op.open(req, timeout=10); loc = None
    except urllib.error.HTTPError as e:
        loc = e.headers.get('Location') if e.code == 302 else None
    check(loc == 'live.html?mode=replay', f'/ -> 302 {loc}')
    for path in ('/refs/cache/local/registry/mictronics_lookup.json', '/refs/cache/adsb/hwd_events.json',
                 '/tools/live/recio.py', '/out/phase1/', '/out/replay/.state/adsblol_quota.json', '/.git/HEAD',
                 '/hwd3d/../refs/cache/local/registry/fetch_log.json', '/%2e%2e/sfo3d/CLAUDE.md'):
        check(get(base, path)[0] == 404, f'404 {path}')
    if os.path.exists(os.path.join(ROOT, 'out', 'replay', 'pack.json.gz')):
        check(get(base, '/out/replay/pack.json.gz')[0] == 200, '200 /out/replay/pack.json.gz')
    check(get(base, '/data/hwd_airport.json')[0] == 200, '200 /data/hwd_airport.json')


if __name__ == '__main__':
    main()
