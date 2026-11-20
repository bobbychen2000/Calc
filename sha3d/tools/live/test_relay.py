#!/usr/bin/env python3
"""Unit test of sha_live_server.py (stdlib unittest): starts the relay on a free port against a LOCAL mock of the
aviationweather.gov Data API and of the adsb.lol point API (nothing leaves this machine), then checks

  - /api/ping answers {"shalive": 1} with the features, the attribution and a generic User-Agent;
  - /api/metar?ids=ZSSS relays the mocked METARs: raw text kept, newest first, the lossy AWC JSON weather fields
    (wspd, visib, wdir ...) removed, format=raw gives the raw lines; other stations are refused (400);
  - the upstream is asked at most once per interval (cache), /api/taf likewise;
  - /api/adsb is OFF by default and then never contacts the provider;
  - with --adsb: only adsb_icao records are relayed and each is labelled src 'obs', other types are only counted; a
    second call inside 180 s does not contact the provider; the 180 s floor cannot be lowered;
  - every upstream request carries the generic User-Agent (no names, no e-mail, no repository URL);
  - static allow-list: the app is served, refs/ tools/ docs/ and the relay source are not; / redirects to live.html?relay=1.

Run:  python3 -I sha3d/tools/live/test_relay.py      (about 3 s)
"""
import json, os, re, socket, subprocess, sys, tempfile, threading, time, unittest, urllib.error, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
SHA3D = os.path.dirname(os.path.dirname(HERE))
RELAY = os.path.join(SHA3D, 'sha_live_server.py')

RAW_NEW = 'METAR ZSSS 140500Z 05002MPS 010V080 8000 -RA BKN020 19/17 Q1015 NOSIG'
RAW_OLD = 'METAR ZSSS 140200Z 01002MPS 340V040 4500 -RA BR BKN006 18/17 Q1017 BECMG TL0340 BKN011'
METARS = [  # AWC JSON shape (fields as served 2026-11-14), deliberately OLDEST FIRST to check the relay's sort
    {'icaoId': 'ZSSS', 'receiptTime': '2026-11-14T02:05:00.000Z', 'obsTime': 1794621600, 'reportTime': '2026-11-14T02:00:00.000Z',
     'temp': 18, 'dewp': 17, 'wdir': 10, 'wspd': 4, 'visib': 2.8, 'altim': 1017, 'metarType': 'METAR', 'rawOb': RAW_OLD,
     'clouds': [{'cover': 'BKN', 'base': 600}, {'cover': 'BKN', 'base': 1100}], 'fltCat': 'IFR'},
    {'icaoId': 'ZSSS', 'receiptTime': '2026-11-14T05:05:15.930Z', 'obsTime': 1794632400, 'reportTime': '2026-11-14T05:00:00.000Z',
     'temp': 19, 'dewp': 17, 'wdir': 50, 'wspd': 4, 'visib': '6+', 'altim': 1015, 'metarType': 'METAR', 'rawOb': RAW_NEW,
     'clouds': [{'cover': 'BKN', 'base': 2000}], 'fltCat': 'MVFR'},
]
TAF = [{'icaoId': 'ZSSS', 'issueTime': '2026-11-14T03:06:00.000Z', 'validTimeFrom': 1794636000, 'validTimeTo': 1794744000,
        'rawTAF': 'TAF ZSSS 140306Z 1406/1512 35004MPS 6000 BKN015 TX20/1406Z TX20/1506Z TN16/1421Z', 'fcsts': [{'wspd': 8}]}]
ADSB = {'now': 1794632400000, 'msg': 'No error', 'total': 4, 'ac': [
    {'hex': 'ABC123', 'type': 'adsb_icao', 'flight': 'TEST1   ', 'lat': 31.6, 'lon': 121.9, 'alt_baro': 36000, 'gs': 450.1, 'track': 90.0, 'seen_pos': 0.4, 'dst': 30.1, 'rssi': -20},
    {'hex': '780aaa', 'type': 'mlat', 'lat': 31.7, 'lon': 121.0, 'alt_baro': 30000, 'seen_pos': 1.0},
    {'hex': '~0001', 'type': 'other', 'lat': 31.2, 'lon': 121.3, 'alt_baro': 'ground', 'seen_pos': 1.0},
    {'hex': '780bbb', 'type': 'tisb_icao', 'lat': 31.1, 'lon': 121.4, 'alt_baro': 2000, 'seen_pos': 2.0},
]}
UA_RE = re.compile(r'^sha-live-3d-relay/\d+\.\d+ \(personal non-commercial visualisation; python-stdlib\)$')


class Mock:
    """Local stand-in for aviationweather.gov /api/data/{metar,taf} and adsb.lol /v2/point/...; logs every request."""

    def __init__(self):
        self.log = []
        mock = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                mock.log.append({'path': self.path, 'ua': self.headers.get('User-Agent'), 'headers': dict(self.headers)})
                if self.path.startswith('/api/data/metar?'):
                    body = json.dumps(METARS).encode()
                elif self.path.startswith('/api/data/taf?'):
                    body = json.dumps(TAF).encode()
                elif self.path.startswith('/v2/point/'):
                    body = json.dumps(ADSB).encode()
                else:
                    self.send_response(404); self.end_headers(); return
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.srv = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def hits(self, prefix):
        return [r for r in self.log if r['path'].startswith(prefix)]


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def get(port, path, redirect=True):
    """-> (status, headers, body); no proxy for 127.0.0.1."""
    handlers = [urllib.request.ProxyHandler({})] + ([] if redirect else [NoRedirect()])
    op = urllib.request.build_opener(*handlers)
    try:
        with op.open(f'http://127.0.0.1:{port}{path}', timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read() or b''


class Relay:
    def __init__(self, mock, *extra):
        self.port = free_port()
        self.state = tempfile.mkdtemp(prefix='sha_relay_state_')
        env = dict(os.environ, NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost')
        self.p = subprocess.Popen([sys.executable, '-I', RELAY, '--port', str(self.port), '--quiet', '--state-dir', self.state,
                                   '--awc-base', f'http://127.0.0.1:{mock.port}/api/data/', '--adsb-base', f'http://127.0.0.1:{mock.port}', *extra],
                                  env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        while time.time() - t0 < 15:
            try:
                if get(self.port, '/api/ping')[0] == 200:
                    return
            except Exception:
                time.sleep(0.1)
        self.stop()
        raise RuntimeError('relay did not start')

    def stop(self):
        self.p.terminate()
        try:
            self.p.wait(5)
        except subprocess.TimeoutExpired:
            self.p.kill()


class TestRelay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock = Mock()
        cls.relay = Relay(cls.mock)

    @classmethod
    def tearDownClass(cls):
        cls.relay.stop()
        cls.mock.srv.shutdown()

    def test_ping(self):
        for path in ('/api/ping', '/sha3d/api/ping'):
            code, hd, body = get(self.relay.port, path)
            self.assertEqual(code, 200)
            j = json.loads(body)
            self.assertEqual(j['shalive'], 1)
            self.assertEqual(j['mode'], 'live')
            self.assertTrue(j['features']['metar'])
            self.assertFalse(j['features']['adsb'])
            self.assertGreaterEqual(j['adsb_min_interval_s'], 180)
            self.assertIn('adsb', j['attribution'])
            self.assertIn('NOAA/NWS', j['attribution']['metar'])
            self.assertRegex(j['ua'], UA_RE)
            self.assertNotIn('adsb.lol', j['providers'])     # off by default

    def test_metar(self):
        code, hd, body = get(self.relay.port, '/sha3d/api/metar?ids=ZSSS&format=json')
        self.assertEqual(code, 200, body)
        L = json.loads(body)
        self.assertEqual([m['rawOb'] for m in L], [RAW_NEW, RAW_OLD])                  # newest first, raw text kept
        for m in L:
            self.assertEqual(set(m) - {'icaoId', 'metarType', 'obsTime', 'reportTime', 'receiptTime', 'rawOb'}, set())
            self.assertNotIn('wspd', m); self.assertNotIn('visib', m); self.assertNotIn('clouds', m)
        code, hd, body = get(self.relay.port, '/api/metar?ids=ZSSS')
        self.assertEqual(code, 200)
        self.assertEqual(body.decode().split('\n'), [RAW_NEW, RAW_OLD])
        for _ in range(3):
            get(self.relay.port, '/api/metar?ids=ZSSS&format=json')
        self.assertEqual(len(self.mock.hits('/api/data/metar')), 1, 'upstream asked more than once per 10 min')
        self.assertIn('ids=ZSSS', self.mock.hits('/api/data/metar')[0]['path'])
        code, hd, body = get(self.relay.port, '/api/metar?ids=KSFO&format=json')
        self.assertEqual(code, 400)
        self.assertEqual(len(self.mock.hits('/api/data/metar')), 1)

    def test_taf(self):
        code, hd, body = get(self.relay.port, '/api/taf?ids=ZSSS&format=json')
        self.assertEqual(code, 200)
        L = json.loads(body)
        self.assertEqual(L[0]['rawTAF'], TAF[0]['rawTAF'])
        self.assertNotIn('fcsts', L[0])
        get(self.relay.port, '/api/taf?ids=ZSSS')
        self.assertEqual(len(self.mock.hits('/api/data/taf')), 1)

    def test_adsb_off(self):
        code, hd, body = get(self.relay.port, '/api/adsb')
        j = json.loads(body)
        self.assertEqual(code, 200)
        self.assertFalse(j['enabled'])
        self.assertEqual(j['ac'], [])
        self.assertEqual(self.mock.hits('/v2/'), [])

    def test_static_and_deny(self):
        p = self.relay.port
        code, hd, body = get(p, '/', redirect=False)
        self.assertEqual(code, 302)
        self.assertEqual(hd.get('Location'), '/sha3d/live.html?relay=1')
        self.assertEqual(get(p, '/?t=2026-11-14T03:00:00Z', redirect=False)[1].get('Location'), '/sha3d/live.html?relay=1&t=2026-11-14T03:00:00Z')
        self.assertEqual(get(p, '/sha3d/live.html')[0], 200)
        self.assertEqual(get(p, '/sha3d/js/live/relay.js')[0], 200)
        self.assertEqual(get(p, '/sha3d/data/sha_stands.js')[0], 200)
        for bad in ('/sha3d/refs/cache/metar/SOURCES.json', '/sha3d/tools/wx/metar_zsss.py', '/sha3d/sha_live_server.py',
                    '/sha3d/docs/PLAN.md', '/sha3d/out/', '/sha3d/js/../refs/cache/metar/SOURCES.json', '/sha3d/js/%2e%2e/livetest.mjs',
                    '/sfo3d/sfo_live_server.py', '/pc12/CLAUDE.md', '/.git/config', '/sha3d/data/'):
            self.assertEqual(get(p, bad)[0], 404, bad)

    def test_user_agent(self):
        get(self.relay.port, '/api/metar?ids=ZSSS&format=json')
        self.assertTrue(self.mock.log)
        for r in self.mock.log:
            self.assertRegex(r['ua'] or '', UA_RE)
            for leak in ('github', '@', 'http://', 'https://', 'contact', 'mailto'):
                self.assertNotIn(leak, (r['ua'] or '').lower())
            self.assertNotIn('from', {k.lower() for k in r['headers']})


class TestRelayAdsb(unittest.TestCase):
    def test_adsb_on(self):
        mock = Mock()
        relay = Relay(mock, '--adsb', '--adsb-interval', '30', '--adsb-daily-max', '5')
        try:
            j = json.loads(get(relay.port, '/api/ping')[2])
            self.assertTrue(j['features']['adsb'])
            self.assertEqual(j['adsb_min_interval_s'], 180.0)        # 30 s was raised to the floor
            j = json.loads(get(relay.port, '/api/adsb')[2])
            self.assertTrue(j['enabled'])
            self.assertEqual(len(mock.hits('/v2/point/31.1978/121.3363/60')), 1)
            self.assertEqual([a['hex'] for a in j['ac']], ['abc123'])
            a = j['ac'][0]
            self.assertEqual((a['src'], a['_src'], a['type']), ('obs', 'adsb.lol', 'adsb_icao'))
            self.assertNotIn('dst', a); self.assertNotIn('rssi', a)
            self.assertAlmostEqual(a['_pt'], 1794632400 - 0.4, places=3)
            self.assertEqual(j['excluded'], {'mlat': 1, 'other': 1, 'tisb_icao': 1})
            self.assertEqual(j['upstream_total'], 4)
            self.assertGreater(j['next_request_in_s'], 170)
            for _ in range(3):
                j2 = json.loads(get(relay.port, '/api/adsb')[2])
            self.assertEqual(len(mock.hits('/v2/')), 1, 'adsb.lol asked twice within 180 s')
            self.assertEqual(j2['ac'], j['ac'])
            self.assertEqual(j2['requests_24h'], 1)
            for r in mock.log:
                self.assertRegex(r['ua'] or '', UA_RE)
            # the quota log survives a restart: a new relay on the same state dir does not ask again within 180 s
            relay.stop()
            relay2 = Relay(mock, '--adsb', '--state-dir', relay.state)
            try:
                j3 = json.loads(get(relay2.port, '/api/adsb')[2])
                self.assertEqual(len(mock.hits('/v2/')), 1)
                self.assertEqual(j3['requests_24h'], 1)
            finally:
                relay2.stop()
        finally:
            relay.stop()
            mock.srv.shutdown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
