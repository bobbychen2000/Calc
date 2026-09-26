#!/usr/bin/env python3
"""Offline unit tests for sfo_live_server.py (merge, hygiene, provenance, gates parsing, routes, scheduling).

  python3 tools/live/test_relay.py            # no network; uses the cached flysfo snapshots if present
"""
import gzip, glob, json, math, os, sys, time, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
import sfo_live_server as S  # noqa: E402

LOL, FI = S.PROVIDERS['adsblol'], S.PROVIDERS['adsbfi']


def ac(hx, lat=37.6, lon=-122.4, seen_pos=0.5, **kw):
    a = {'hex': hx, 'lat': lat, 'lon': lon, 'seen_pos': seen_pos, 'seen': seen_pos, 'type': 'adsb_icao', 'alt_baro': 3000, 'gs': 150.0}
    a.update(kw)
    return a


def feed(hub, prov, now, lst, recv=None):
    hub.ingest(prov, now, recv or time.time(), {'now': now * 1000, 'ac': lst})
    return {a['hex']: a for a in hub.latest['ac']}


class Merge(unittest.TestCase):
    def test_freshest_position_wins_and_identity_fills(self):
        h = S.Hub()
        T = time.time()
        feed(h, FI, T - 1.0, [ac('abc123', lat=37.60, seen_pos=0.2, r='N1', t='B738', desc='BOEING 737-800', ownOp='X', flight='UAL1  ')])
        m = feed(h, LOL, T, [ac('abc123', lat=37.61, seen_pos=0.3, flight='UAL1  ')])
        a = m['abc123']
        self.assertEqual(a['lat'], 37.61)                   # adsb.lol report is fresher (T-0.3 vs T-1.2)
        self.assertEqual(a['_src'], 'lol')
        self.assertEqual(a['_prov'], 'fi+lol')
        self.assertEqual(a['desc'], 'BOEING 737-800')      # identity from adsb.fi (adsb.lol omits desc/ownOp/year)
        self.assertEqual(a['r'], 'N1')
        self.assertAlmostEqual(a['_pt'], T - 0.3, places=2)
        self.assertNotIn('dst', a)

    def test_same_report_fill(self):
        h = S.Hub()
        T = time.time()
        feed(h, FI, T, [ac('abc123', seen_pos=0.5, true_heading=90.0, nav_qnh=1011.2)])
        a = feed(h, LOL, T, [ac('abc123', seen_pos=0.45)])['abc123']
        self.assertEqual(a['_src'], 'lol')
        self.assertEqual(a['true_heading'], 90.0)          # same report (0.05 s apart): missing fields filled
        self.assertEqual(a['nav_qnh'], 1011.2)
        h2 = S.Hub()
        feed(h2, FI, T - 3, [ac('abc123', seen_pos=0.5, true_heading=90.0)])
        a2 = feed(h2, LOL, T, [ac('abc123', seen_pos=0.4)])['abc123']
        self.assertNotIn('true_heading', a2)               # a different (older) report is not mixed in

    def test_mlat_held_while_adsb_is_fresh(self):
        h = S.Hub()
        T = time.time()
        feed(h, LOL, T, [ac('abc123', lat=37.600, seen_pos=5.0)])
        a = feed(h, FI, T, [ac('abc123', lat=37.700, seen_pos=0.1, type='mlat')])['abc123']
        self.assertEqual(a['lat'], 37.600)                 # MLAT position 4.9 s after an ADS-B one is ignored
        self.assertEqual(h.counters['mlat_held'] >= 1, True)

    def test_mlat_jump_rejected(self):
        h = S.Hub()
        T = time.time()
        feed(h, LOL, T - 40, [ac('abc123', lat=37.600, seen_pos=0.0, type='mlat', gs=10.0)])
        a = feed(h, FI, T, [ac('abc123', lat=37.700, seen_pos=0.0, type='mlat', gs=10.0)])['abc123']   # 11 km in 40 s at 10 kt
        self.assertEqual(a['lat'], 37.600)
        self.assertGreaterEqual(h.counters['mlat_jump'], 1)

    def test_ground_hygiene_and_vehicle_sticky(self):
        h = S.Hub()
        T = time.time()
        a = feed(h, FI, T, [ac('abc123', alt_baro='ground', track=118.0, true_heading=298.1, mlat=['track', 'gs'], gs=80)])['abc123']
        self.assertNotIn('track', a)
        self.assertNotIn('gs', a)                          # listed in mlat[] on the ground
        self.assertEqual(a['true_heading'], 298.1)
        self.assertEqual(a['_drop'], ['gs', 'track'])
        feed(h, LOL, T, [ac('a24f2b', alt_baro='ground', category='C1', flight='OPS34')])
        a = feed(h, LOL, T + 1, [ac('a24f2b', alt_baro='ground', flight='OPS34')])['a24f2b']   # no category now
        self.assertEqual(a.get('_veh'), 1)

    def test_non_icao_kept_and_split_when_apart(self):
        h = S.Hub()
        T = time.time()
        feed(h, FI, T, [ac('~ac72b7', lat=37.70)])
        m = feed(h, LOL, T, [ac('~ac72b7', lat=37.70)])
        self.assertIn('~ac72b7', m)
        self.assertEqual(m['~ac72b7']['_prov'], 'fi+lol')
        h2 = S.Hub()
        feed(h2, FI, T, [ac('~ac72b7', lat=37.70)])
        m2 = feed(h2, LOL, T, [ac('~ac72b7', lat=37.90)])   # 22 km apart: two different targets
        self.assertEqual(len([k for k in m2 if k.startswith('~ac72b7')]), 2)

    def test_old_position_becomes_lastPosition_and_stale_snapshot_ignored(self):
        h = S.Hub()
        T = time.time()
        a = feed(h, FI, T, [ac('abc123', seen_pos=75.0)])['abc123']
        self.assertNotIn('lat', a)
        self.assertAlmostEqual(a['lastPosition']['seen_pos'], 75.0, delta=0.5)
        h2 = S.Hub()
        feed(h2, FI, T - 100, [ac('def456')], recv=T - 100)
        m = feed(h2, LOL, T, [ac('abc123')])
        self.assertNotIn('def456', m)                      # adsb.fi snapshot older than SNAP_TTL

    def test_delta(self):
        h = S.Hub()
        T = time.time()
        feed(h, LOL, T, [ac('a1'), ac('a2')])
        feed(h, LOL, T + 1, [ac('a1', lat=37.7, seen_pos=0.1), ac('a2', seen_pos=1.5)])   # a2: same report, older age only
        d = json.loads(h.delta)
        self.assertEqual([x['hex'] for x in d['ac']], ['a1'])
        feed(h, LOL, T + 2, [ac('a1', lat=37.7, seen_pos=1.1)])
        d = json.loads(h.delta)
        self.assertEqual(d['gone'], ['a2'])


class Gates(unittest.TestCase):
    def test_norm_and_base(self):
        self.assertEqual(S.norm_cs('CAL003 '), 'CAL3')
        self.assertEqual(S.norm_cs('SKW249R'), 'SKW249R')
        self.assertEqual(S.stand_base('E10U'), 'E10')
        self.assertEqual(S.stand_base('41-08'), '41-08')
        self.assertTrue(S.type_match('E75L', {'E175'}))    # flysfo 'E175' vs ADS-B 'E75L' (SKW6274 = AAL6274)
        self.assertTrue(S.type_match('B738', {'B738'}))
        self.assertFalse(S.type_match('CRJ2', {'E175'}))

    def test_parse_cached_snapshot(self):
        fs = sorted(glob.glob(os.path.join(ROOT, 'refs', 'cache', 'gate_truth', 'flysfo_api_flight-status_2*.json.gz')))
        if not fs:
            self.skipTest('no cached flysfo snapshot')
        clock = S.Clock()
        g = S.Gates(enabled=True, replay_clock=None)
        g.enabled = True
        d = json.load(gzip.open(fs[0], 'rt'))
        t_file = S.Gates._file_time(fs[0])
        g._ingest(d, t_file, fs[0])
        # evaluate as if at the snapshot time: use a replay clock mapping wall now -> snapshot time
        g.replay = S.Clock(time.time(), t_file, 1.0)
        g._replay_load = lambda T: None
        p = g.payload()
        self.assertTrue(p['enabled'])
        e = p['byCallsign'].get('ASA7') or next(iter(p['byCallsign'].values()))
        self.assertIn('flights', e)
        # AAL2856 at B23 (gate_truth §5 #3, 07:30 UTC): its stand window must cover the snapshot time
        if 'AAL2856' in p['byCallsign'] and '07' in os.path.basename(fs[0]):
            st = p['byCallsign']['AAL2856'].get('stand')
            self.assertIsNotNone(st)
            self.assertEqual(st['base'], 'B23')
        self.assertTrue(any(v['now'] for v in p['byStand'].values()))


    def test_regional_alias_type_conflict_and_hold(self):
        # review round 2: QXE2139 (N670QX, E195 in the adsb.fi database; SFO and Horizon's all-E175 fleet say E75L) must map
        # to ASA2139 -- the database type flags, it does not veto -- and the alias is held once the aircraft is silent
        fs = sorted(glob.glob(os.path.join(ROOT, 'refs', 'cache', 'gate_truth', 'flysfo_api_flight-status_20260925T18*.json.gz')))
        if not fs:
            self.skipTest('no cached flysfo snapshot of 25 Sep 18Z')
        class Hub:
            live = {'QXE2139': {'t': 'E195', 'flight': 'QXE2139'}}
            def current_callsigns(self):
                return dict(self.live)
        hub = Hub()
        g = S.Gates(enabled=True, replay_clock=None, hub=hub)
        t_file = S.Gates._file_time(fs[0])
        g._ingest(json.load(gzip.open(fs[0], 'rt')), t_file, fs[0])
        g.replay = S.Clock(time.time(), t_file + 1800, 1.0)
        g._replay_load = lambda T: None
        a = g.payload()['aliases'].get('QXE2139')
        self.assertIsNotNone(a)
        self.assertEqual(a['to'], 'ASA2139')
        self.assertEqual(a['checks'].get('type'), 'family')   # E195 vs E75L: same family, a plausible database mis-entry
        # a different family is not the same flight (SKW750R CRJ2 vs DAL750 B752, 25 Sep 19:38Z), nor a suffixed callsign
        self.assertFalse(S.same_family('CRJ2', {'B752'}))
        self.assertTrue(S.same_family('E195', {'E175'}) or S.same_family('E195', {'E75L'}))
        hub.live = {}
        a2 = g.payload()['aliases'].get('QXE2139')
        self.assertIsNotNone(a2)
        self.assertTrue(a2.get('held'))
        self.assertEqual(a2['to'], 'ASA2139')


class Faa(unittest.TestCase):
    def test_model_strings(self):
        # FAA registry ACFTREF model strings seen on N-registered aircraft of the 24/25 Sep recording -> ICAO Doc 8643
        for mfr, model, t in (('BOEING', '737-8', 'B38M'), ('BOEING', '737-9', 'B39M'), ('BOEING', '737-824', 'B738'), ('BOEING', '737-800', 'B738'),
                              ('BOEING', '737-7H4', 'B737'), ('BOEING', '737-900ER', 'B739'), ('BOEING', '737-990ER', 'B739'), ('BOEING', '757-224', 'B752'),
                              ('BOEING', '757-33N', 'B753'), ('BOEING', '767-300F', 'B763'), ('BOEING', '767-332', 'B763'), ('BOEING', '777-222', 'B772'),
                              ('BOEING', '777-300ER', 'B77W'), ('BOEING', '777F', 'B77L'), ('BOEING', '787-9', 'B789'), ('BOEING', '787-10', 'B78X'),
                              ('AIRBUS', 'A320-232', 'A320'), ('AIRBUS', 'A320-251N', 'A20N'), ('AIRBUS S A S', 'A321-271NX', 'A21N'), ('AIRBUS', 'A321-231', 'A321'),
                              ('AIRBUS', 'A319-131', 'A319'), ('AIRBUS', 'A330-243', 'A332'), ('AIRBUS', 'A350-941', 'A359'), ('AIRBUS CANADA LP', 'BD-500-1A11', 'BCS3'),
                              ('C SERIES AIRCRAFT LTD', 'BD-500-1A10', 'BCS1'), ('EMBRAER S A', 'ERJ 170-200 LR', 'E75L'), ('YABORA INDUSTRIA AERON', 'ERJ 170-200 LL', 'E75L'),
                              ('EMBRAER', 'EMB-145LR', 'E145'), ('BOMBARDIER INC', 'CL-600-2B19', 'CRJ2'), ('MCDONNELL DOUGLAS', 'MD-11F', 'MD11'),
                              ('TEXTRON AVIATION INC', 'B300', None), ('AGUSTA SPA', 'A109S', None)):
            self.assertEqual(S.faa_icao(mfr, model), t, (mfr, model))

    def test_registry_n670qx(self):
        if not os.path.exists(os.path.join(S.FAA_DIR, 'MASTER.txt')):
            self.skipTest('no FAA registry copy in refs/cache/faa')
        R = S.FaaRegistry()
        while not R.ready and R.err is None:
            time.sleep(0.5)
        self.assertEqual(R.get('a8dd2c'), 'E75L')   # N670QX (adsb.fi database: E195)


class Routes(unittest.TestCase):
    def test_plausible(self):
        SFO = {'lat': 37.619, 'lon': -122.375}
        LAX = {'lat': 33.9425, 'lon': -118.408}
        MEL = {'lat': -37.6733, 'lon': 144.843}
        self.assertEqual(S.plausible(37.62, -122.37, [SFO, MEL])[0], True)       # at the origin
        self.assertEqual(S.plausible(47.45, -122.31, [SFO, LAX])[0], False)      # over Seattle: not SFO-LAX
        mid = (35.8, -120.4)
        self.assertEqual(S.plausible(mid[0], mid[1], [SFO, LAX]), (True, 0))

    def test_mirror_row(self):
        r = S.Routes('mirror', cache_dir='/nonexistent')
        r.routes_blob = b'\nCallsign,Code,Number,AirlineCode,AirportCodes\nUAL60,UAL,60,UAL,KSFO-YMML\n'
        r.airports = {'KSFO': {'name': 'San Francisco International Airport', 'icao': 'KSFO', 'iata': 'SFO', 'location': 'San Francisco',
                               'countryiso2': 'US', 'lat': 37.619, 'lon': -122.375, 'alt_feet': 13.0},
                      'YMML': {'name': 'Melbourne International Airport', 'icao': 'YMML', 'iata': 'MEL', 'location': 'Melbourne',
                               'countryiso2': 'AU', 'lat': -37.67, 'lon': 144.84, 'alt_feet': 434.0}}
        r.mirror_checked = time.time()
        res, src = r.lookup([{'callsign': 'UAL60', 'lat': 37.6, 'lng': -122.4}, {'callsign': 'ZZZ1', 'lat': 37.6, 'lng': -122.4}])
        by = {x['callsign']: x for x in res}
        self.assertEqual(by['UAL60']['_airport_codes_iata'], 'SFO-MEL')
        self.assertTrue(by['UAL60']['plausible'])
        self.assertEqual(by['UAL60']['_sfo'], 'origin')
        self.assertEqual(by['ZZZ1']['_airport_codes_iata'], 'unknown')


class RecIO(unittest.TestCase):
    def test_members_closed_and_open(self):
        """Two recorder runs appended to one hour file (a closed gzip member, then one still being written, larger
        than the 64 KiB read step): every line of both must be read (bug fixed 24 Sep: the 2nd member was lost)."""
        import tempfile, random as rnd
        sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
        import recio
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'adsbfi_20260101_00.jsonl.gz')
        w = S.RecordWriter(d)
        rnd.seed(1)
        blob = lambda: {'now': 1, 'ac': [{'hex': '%06x' % rnd.getrandbits(24), 'x': rnd.random()} for _ in range(50)]}
        for i in range(300):
            w.write('adsbfi', 1767225600 + i, 1767225600.2 + i, 200, {}, blob(), None)
        w.close()
        w2 = S.RecordWriter(d)
        for i in range(300, 700):
            w2.write('adsbfi', 1767225600 + i, 1767225600.2 + i, 200, {}, blob(), None)   # left open (flushed)
        ts = [r['t'] for r in recio.lines(p)]
        self.assertEqual(ts, [1767225600 + i for i in range(700)])
        w2.close()
        self.assertEqual(len(list(recio.lines(p))), 700)


class Schedule(unittest.TestCase):
    def test_adsbfi_even_slots_and_backoff(self):
        p = S.Poller(FI, lambda *a: None)
        t = 1790000000.9
        self.assertAlmostEqual(p._slot_after(t) % 2.0, 0.3, places=6)
        p._schedule(1790000000.3, 1790000000.6, True)
        self.assertAlmostEqual(p.next_due, 1790000002.3, places=6)
        p._schedule(1790000002.3, 1790000002.6, False)
        self.assertGreaterEqual(p.next_due - 1790000002.6, 4.0)
        self.assertAlmostEqual(p.next_due % 2.0, 0.3, places=6)

    def test_adsblol_jitter_and_429(self):
        p = S.Poller(LOL, lambda *a: None)
        for _ in range(50):
            p._schedule(100.0, 100.4, True)
            self.assertTrue(101.0 <= p.next_due <= 101.5)
        waits = []
        for _ in range(7):
            p._schedule(100.0, 100.4, False)
            waits.append(round(p.next_due - 100.4, 3))
        self.assertEqual(waits, [2.0, 4.0, 8.0, 16.0, 30.0, 30.0, 30.0])
        p._schedule(100.0, 100.4, False, retry_after=45)
        self.assertEqual(round(p.next_due - 100.4), 45)

    def test_adaptive_floor_after_429(self):
        p = S.Poller(LOL, lambda *a: None)
        for _ in range(4):                                  # four refusals: floor 2, 3, 4.5, 6.75 s
            p._schedule(100.0, 100.4, False, status=429)
        self.assertAlmostEqual(p.floor, 6.75)
        p._schedule(200.0, 200.2, True)                     # success: next request no sooner than 0.9 x floor
        self.assertAlmostEqual(p.next_due, 200.0 + 6.075, places=6)
        p._schedule(210.0, 210.4, False, status=429)        # first refusal after a success waits >= the raised floor
        self.assertAlmostEqual(p.next_due - 210.4, 6.075 * 1.5, places=6)
        for i in range(40):                                 # sustained successes decay it back to the normal cadence
            p._schedule(300.0 + i, 300.2 + i, True)
        self.assertEqual(p.floor, 0.0)
        self.assertTrue(339.0 + 1.0 <= p.next_due <= 339.0 + 1.5)
        q = S.Poller(LOL, lambda *a: None)
        q._schedule(100.0, 100.4, False, status=503)        # network/server errors back off but leave the floor alone
        self.assertEqual(q.floor, 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
