#!/usr/bin/env python3
"""Tests of the local identity overlay (OD4; docs/phase3/design.md s.3, s.7.2 P3-A):

  - tools/sim/observed_overlay.py on SYNTHETIC tables (placeholder airline XXX, registrations ZZ-SIM*, outside every real
    format): field allow-list, 'type' from the source field 't' (~ ^[A-Z][A-Z0-9]{1,3}$), the source 'icao' (24-bit
    address) never copied, no value matching ^[0-9a-f]{6}$, only consistent records with a t_sha, integer t_sha / sigma_s,
    flight number through data/lookup.js, a malformed or absent day -> None;
  - the same checks on the REAL local tables when refs/cache/observed_elsewhere exists (prints counts only, never a value);
  - the relay endpoint GET /api/observed_elsewhere?day=: {available: false} without files, a malformed day rejected (400),
    a non-loopback --host without --identity-lan -> {available: false}, with --identity-lan available; --no-identity off.

Run:  python3 -I sha3d/tools/sim/test_observed_overlay.py      (about 3 s; nothing leaves this machine)
"""
import importlib.util, json, os, re, shutil, socket, subprocess, sys, tempfile, time, unittest, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SHA3D = os.path.dirname(os.path.dirname(HERE))
RELAY = os.path.join(SHA3D, 'sha_live_server.py')
REAL_DIR = os.path.join(SHA3D, 'refs', 'cache', 'observed_elsewhere')
spec = importlib.util.spec_from_file_location('observed_overlay', os.path.join(HERE, 'observed_overlay.py'))
OV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(OV)

ALLOWED = {'uid', 'role', 'airline', 'cs', 'flight', 'reg', 'type', 'operator', 'far', 't_sha', 'sigma_s'}
TYPE_RX = re.compile(r'^[A-Z][A-Z0-9]{1,3}$')
HEX_RX = re.compile(r'^[0-9a-f]{6}$')
DAY = '2026-11-12'
SYN = {'day': DAY, 'window_utc': ['2026-11-11T20:00:00Z', '2026-11-12T20:00:00Z'], 'n': 5, 'licence': 'synthetic test data',
       'movements': [
           {'role': 'arr', 'airline': 'XXX', 'cs': 'XXXSIM1', 'r': 'ZZ-SIM1', 't': 'A320', 'icao': 'fff0a1', 'operator': 'Sim Air',
            'far': 'ZBAA', 't_sha': 1794460000, 'sigma_s': 300, 'consistency': 'track_consistent', 'evidence': {'k': 1}, 'segs': [[1, 2]],
            'first': {'t': 1}, 'last': {'t': 2}, 'est': {'M1': 1}, 'src': {'type': 'obs'}},
           {'role': 'dep', 'airline': 'XXX', 'cs': 'XXXSIM2', 'r': 'ZZ-SIM2', 't': 'b738', 'icao': 'fff0a2', 'operator': 'Sim Air',
            'far': 'ZGSZ', 't_sha': 1794470000.4, 'sigma_s': 420.6, 'consistency': 'far_end_match'},
           {'role': 'dep', 'airline': 'XXX', 'cs': 'XXXSIM3', 'r': 'ZZ-SIM3', 't': 'B738', 'icao': 'fff0a3', 'operator': 'Sim Air',
            'far': 'ZGSZ', 't_sha': 1794470000, 'sigma_s': 400, 'consistency': 'track_inconsistent'},
           {'role': 'arr', 'airline': 'XXX', 'cs': 'XXXSIM4', 'r': 'ZZ-SIM4', 't': 'A21N', 'icao': 'fff0a4', 'operator': 'Sim Air',
            'far': 'ZUUU', 't_sha': None, 'sigma_s': 400, 'consistency': 'track_consistent'},
           {'role': 'arr', 'airline': 'XXX', 'cs': 'fff0a5', 'r': 'ZZ-SIM5', 't': 'A21N', 'icao': 'fff0a5', 'operator': 'Sim Air',
            'far': 'ZUUU', 't_sha': 1794471000, 'sigma_s': 400, 'consistency': 'track_consistent'}]}


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def get(port, path):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open(f'http://127.0.0.1:{port}{path}', timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b''


class Relay:
    def __init__(self, ident_dir, *extra):
        self.port = free_port()
        self.state = tempfile.mkdtemp(prefix='sha_ovl_state_')
        env = dict(os.environ, NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost')
        self.p = subprocess.Popen([sys.executable, '-I', RELAY, '--port', str(self.port), '--quiet', '--no-metar', '--state-dir', self.state,
                                   '--identity-dir', ident_dir, *extra], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        shutil.rmtree(self.state, ignore_errors=True)


def assert_overlay(t, o, day):
    t.assertEqual((o['v'], o['day'], o['tier']), (1, day, 'oe'))
    t.assertEqual(set(o), {'v', 'day', 'tier', 'note', 'licence', 'records'})
    for r in o['records']:
        t.assertEqual(set(r), ALLOWED)
        t.assertRegex(r['type'], TYPE_RX)
        t.assertIn(r['role'], ('arr', 'dep'))
        t.assertIsInstance(r['t_sha'], int)
        t.assertIsInstance(r['sigma_s'], int)
        for v in r.values():
            if isinstance(v, str):
                t.assertIsNone(HEX_RX.match(v), 'a 6-hex value in the overlay')


class TestOverlayTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix='sha_ovl_syn_')
        with open(os.path.join(cls.dir, f'sha_observed_{DAY}.json'), 'w') as f:
            json.dump(SYN, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_synthetic(self):
        o = OV.overlay(DAY, self.dir)
        assert_overlay(self, o, DAY)
        self.assertEqual([r['reg'] for r in o['records']], ['ZZ-SIM1', 'ZZ-SIM2'])   # inconsistent / no t_sha / 6-hex cs dropped
        self.assertEqual(o['records'][1]['type'], 'B738')                            # from 't', upper-cased
        self.assertEqual((o['records'][1]['t_sha'], o['records'][1]['sigma_s']), (1794470000, 421))
        self.assertIsNone(o['records'][0]['flight'])                                 # XXX has no IATA designator
        self.assertNotIn('fff0a1', json.dumps(o))
        for bad in ('2026-11-11', '2026-1-12', '../x', '', None):
            self.assertIsNone(OV.overlay(bad, self.dir))
        self.assertEqual(OV.days(self.dir), [DAY])
        self.assertEqual(OV.days(os.path.join(self.dir, 'nope')), [])

    def test_flight_of(self):
        self.assertEqual(OV.flight_of('CES0501'), 'MU501')
        self.assertEqual(OV.flight_of('CSH9001'), 'FM9001')
        self.assertIsNone(OV.flight_of('XXXSIM1'))
        self.assertIsNone(OV.flight_of(None))

    @unittest.skipUnless(os.path.isdir(REAL_DIR) and OV.days(REAL_DIR), 'no local observed-elsewhere tables')
    def test_real_local_tables(self):
        for day in OV.days(REAL_DIR):
            o = OV.overlay(day, REAL_DIR)
            assert_overlay(self, o, day)
            with open(os.path.join(REAL_DIR, f'sha_observed_{day}.json')) as f:
                src = json.load(f)
            n = sum(1 for m in src['movements'] if m.get('consistency') in OV.CONSISTENT and m.get('t_sha') is not None)
            self.assertEqual(len(o['records']), n)
            addrs = {m['icao'] for m in src['movements'] if m.get('icao')}
            blob = json.dumps(o)
            self.assertFalse(any(a in blob for a in addrs), 'a 24-bit address reached the overlay')
            print(f'  local {day}: {len(o["records"])} records (= consistent with t_sha), allow-list ok, 0 addresses', file=sys.stderr)


class TestOverlayEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix='sha_ovl_syn_')
        with open(os.path.join(cls.dir, f'sha_observed_{DAY}.json'), 'w') as f:
            json.dump(SYN, f)
        cls.empty = tempfile.mkdtemp(prefix='sha_ovl_empty_')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)
        shutil.rmtree(cls.empty, ignore_errors=True)

    def test_endpoint(self):
        r = Relay(self.empty)
        try:
            code, body = get(r.port, f'/api/observed_elsewhere?day={DAY}')
            self.assertEqual((code, json.loads(body)['available']), (200, False))       # no files
        finally:
            r.stop()
        r = Relay(self.dir)
        try:
            code, body = get(r.port, f'/api/observed_elsewhere?day={DAY}')
            j = json.loads(body)
            self.assertTrue(j['available'])
            j.pop('available')
            assert_overlay(self, j, DAY)
            for bad in ('2026-11-1', 'x', '2026-11-12;rm', '%2e%2e'):
                code, body = get(r.port, '/api/observed_elsewhere?day=' + bad)
                self.assertEqual(code, 400, bad)
                self.assertFalse(json.loads(body)['available'])
            self.assertFalse(json.loads(get(r.port, '/api/observed_elsewhere?day=2026-11-10')[1])['available'])
        finally:
            r.stop()
        for extra, avail in ((('--host', '0.0.0.0'), False), (('--host', '0.0.0.0', '--identity-lan'), True), (('--no-identity',), False)):
            r = Relay(self.dir, *extra)
            try:
                self.assertEqual(json.loads(get(r.port, f'/api/observed_elsewhere?day={DAY}')[1])['available'], avail, extra)
            finally:
                r.stop()


if __name__ == '__main__':
    unittest.main(verbosity=2)
