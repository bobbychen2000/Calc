#!/usr/bin/env python3
"""Relay weather smoke test (environment_spec.md §13 step 0 "relay smoke test", §3.2-3.3; part of gate A-CLK).

Offline: sfo_live_server.http_get is replaced by a fake upstream that serves the real aviationweather.gov responses
saved on 2026-11-05 (tools/env/fixtures/awc_metar_ksfo_20261105T0300Z.json, awc_taf_ksfo_20261105T0300Z.json; US
Government work, public domain - NWS disclaimer https://www.weather.gov/disclaimer) and counts the requests.
Checks: the polling schedule (60 s from hh:59 to hh:03, 300 s otherwise, never below max-age), conditional requests
(If-None-Match with the ETag, 304 keeps the body), last-good on upstream errors, raw = rawOb lines newest first, the
TAF endpoint, dataNow (replay = recording clock), and that a replay never returns a report observed after the replay
time (A-CLK).
Run: python3 tools/env/test_relay_wx.py   (exit 1 on failure)
"""
import json, os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, ROOT)
import sfo_live_server as S   # noqa: E402

FAILS = []


def check(name, ok, info=''):
    print(('PASS' if ok else 'FAIL') + ' | ' + name + (' | ' + str(info) if info else ''))
    if not ok:
        FAILS.append(name)


METAR = open(os.path.join(HERE, 'fixtures', 'awc_metar_ksfo_20261105T0300Z.json'), 'rb').read()
TAF = open(os.path.join(HERE, 'fixtures', 'awc_taf_ksfo_20261105T0300Z.json'), 'rb').read()


class Upstream:
    def __init__(self):
        self.calls, self.mode = [], 'ok'

    def __call__(self, url, timeout=15.0, data=None, headers=None, method=None):
        self.calls.append((url, dict(headers or {})))
        if self.mode == 'down':
            return 503, {}, b'busy'
        body = METAR if '/metar?' in url else TAF
        etag = 'W/"m1"' if '/metar?' in url else 'W/"t1"'
        if (headers or {}).get('If-None-Match') == etag:
            return 304, {'etag': etag, 'cache-control': 'max-age=60'}, b''
        return 200, {'etag': etag, 'cache-control': 'max-age=60', 'content-type': 'application/json'}, body


def main():
    # ---- schedule
    base = 1793847600  # 2026-11-05T03:00:00Z
    ttl = {m: S.wx_ttl(base - 3600 + m * 60) for m in (55, 58, 59)} | {m: S.wx_ttl(base + m * 60) for m in (0, 3, 4, 30)}
    check('poll TTL: 300 s at :55/:58, 60 s at :59/:00/:03, 300 s at :04/:30', ttl == {55: 300, 58: 300, 59: 60, 0: 60, 3: 60, 4: 300, 30: 300}, ttl)
    # ---- live: conditional polling, cache, last good, raw ordering
    tmp = tempfile.mkdtemp(prefix='relaywx_')
    S.CACHE_DIR = tmp
    up = Upstream(); S.http_get = up
    m = S.Metar()
    r1 = m.get('KSFO', 'raw')
    raws = [x['rawOb'] for x in sorted(json.loads(METAR), key=lambda x: -x['obsTime'])]
    check('raw = rawOb lines, newest first (3 h)', r1[0].decode().split('\n') == raws and r1[1] == 'text/plain', len(raws))
    check('upstream asked for JSON hours=3', 'format=json&hours=3' in up.calls[0][0], up.calls[0][0])
    m.get('KSFO', 'json'); m.get('KSFO', 'raw')
    check('within the TTL: no further upstream request', len(up.calls) == 1, len(up.calls))
    m.up['metar']['t'] -= 400                      # TTL expired
    r2 = m.get('KSFO', 'json')
    check('after the TTL: conditional request with If-None-Match', up.calls[-1][1].get('If-None-Match') == 'W/"m1"', up.calls[-1][1])
    check('304 keeps the cached body', json.loads(r2[0]) == sorted(json.loads(METAR), key=lambda x: -x['obsTime']))
    up.mode = 'down'; m.up['metar']['t'] -= 400
    r3 = m.get('KSFO', 'raw')
    check('upstream down: last good report + X-Wx-Upstream-Error', r3[0].decode().split('\n') == raws and 'X-Wx-Upstream-Error' in r3[2], r3[2])
    up.mode = 'ok'
    t = m.taf('raw')
    check('/api/taf raw = rawTAF', t[0].decode() == json.loads(TAF)[0]['rawTAF'], t[0][:60])
    saved = [f for f in os.listdir(os.path.join(tmp, 'replay', 'wx')) if f.startswith('taf_ksfo_')]
    check('live TAF saved once for later replays', saved == ['taf_ksfo_20261105T0300Z.json'], saved)
    # ---- dataNow
    h = S.Hub('live')
    check('dataNow live = wall clock', abs(h.data_now_ms() - time.time() * 1000) < 1000)
    clk = S.Clock(wall0=time.time(), src0=1790185885.0, speed=1.0)
    h.clock = clk
    check('dataNow replay = recording clock (Clock.to_src)', abs(h.data_now_ms() - 1790185885000) < 2000, h.data_now_ms())
    # ---- replay: never a report observed after the replay time (A-CLK)
    os.makedirs(os.path.join(tmp, 'replay', 'wx'), exist_ok=True)
    T0 = 1790185885                                 # 2026-09-23T17:51:25Z (snapshot time)
    reps = [dict(obsTime=T0 - 3600 * k + d, rawOb='METAR KSFO %d' % (T0 - 3600 * k + d)) for k in range(-3, 5) for d in (-1740, 0)]
    json.dump(reps, open(os.path.join(tmp, 'replay', 'wx', 'metar_ksfo_test.json'), 'w'))
    bad, n = 0, 0
    for off in range(-7200, 7201, 600):
        mr = S.Metar(S.Clock(wall0=time.time(), src0=T0 + off, speed=1.0))
        try:
            L = json.loads(mr.get('KSFO', 'json')[0])
        except IOError:
            L = []
        n += 1
        bad += sum(1 for x in L if x['obsTime'] > T0 + off + 1)
    check('replay: no report observed after the replay time (25 replay instants)', bad == 0, '%d violations' % bad)
    json.dump([dict(json.loads(TAF)[0], issueTime='2026-09-23T17:20:00.000Z', validTimeFrom=T0 - 1800, validTimeTo=T0 + 86400)],
              open(os.path.join(tmp, 'replay', 'wx', 'taf_ksfo_20260923T1720Z.json'), 'w'))
    tr = S.Metar(S.Clock(wall0=time.time(), src0=T0, speed=1.0))
    check('replay /api/taf: the cached TAF in force at the replay time', tr.taf('json')[0].startswith(b'[{'))
    tr2 = S.Metar(S.Clock(wall0=time.time(), src0=T0 - 3600, speed=1.0))
    try:
        tr2.taf('raw'); ok = False
    except IOError:
        ok = True
    check('replay /api/taf: none before its issue time', ok)
    print('\n' + ('ALL PASSED' if not FAILS else 'FAILED: ' + ', '.join(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
