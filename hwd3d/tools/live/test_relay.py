#!/usr/bin/env python3
"""Offline unit tests for hwd_live_server.py: merge + hygiene, D1 masking, identity, the adsb.lol quota scheduler,
snapshot TTLs, static-serving rules, the HWD window, METAR (KHWD, replay cache) and the rec_pack reader. No network.

Forked from sfo3d/tools/live/test_relay.py @ a967f9b. Kept: the merge/hygiene tests (adapted to the HWD module) and the
scheduling tests. Changed: adsb.lol is on the 'budget' schedule (6.5-7.5 s, Quota). Dropped: gates, routes, FAA registry.
Added: D1, Mictronics, Quota, TTL, denied(), window_filter, Metar, recio (.xz).

  python3 tools/live/test_relay.py
"""
import glob, json, os, sys, tempfile, time, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools', 'live'))
import hwd_live_server as S  # noqa: E402
import recio  # noqa: E402

LOL, FI = S.PROVIDERS['adsblol'], S.PROVIDERS['adsbfi']
LAT, LON = S.ARP


def ac(hx, lat=LAT + 0.01, lon=LON, seen_pos=0.5, **kw):
    a = {'hex': hx, 'lat': lat, 'lon': lon, 'seen_pos': seen_pos, 'seen': seen_pos, 'type': 'adsb_icao', 'alt_baro': 1500,
         'gs': 90.0}
    a.update(kw)
    return a


def feed(hub, prov, now, lst, recv=None, ttl=None):
    hub.ingest(prov, now, recv or time.time(), {'now': now * 1000, 'ac': lst}, ttl=ttl)
    return {a['hex']: a for a in hub.latest['ac']}


class FakeMx:
    ready = True
    def lookup(self, hx, flight=None):
        out = {'aaa111': {'r': 'N100AA', 't': 'C172', 'd': 'CESSNA 172'}, 'bbb222': {'r': 'N200BB', 't': 'SR22'}}.get(hx, {})
        if (flight or '').startswith('EJA'):
            out = dict(out, op='NetJets')
        return out or None
    def label(self):
        return 'mictronics test'


class Merge(unittest.TestCase):
    def test_freshest_position_wins_and_identity_fills(self):
        h = S.Hub(); T = time.time()
        feed(h, FI, T - 1.0, [ac('abc123', lat=37.60, seen_pos=0.2, r='N1', t='C172', desc='CESSNA 172', flight='N1    ')])
        a = feed(h, LOL, T, [ac('abc123', lat=37.61, seen_pos=0.3, flight='N1    ')])['abc123']
        self.assertEqual(a['lat'], 37.61); self.assertEqual(a['_src'], 'lol'); self.assertEqual(a['_prov'], 'fi+lol')
        self.assertEqual(a['desc'], 'CESSNA 172'); self.assertEqual(a['r'], 'N1')
        self.assertAlmostEqual(a['_pt'], T - 0.3, places=2); self.assertNotIn('dst', a)

    def test_same_report_fill(self):
        h = S.Hub(); T = time.time()
        feed(h, FI, T, [ac('abc123', seen_pos=0.5, true_heading=90.0, nav_qnh=1011.2)])
        a = feed(h, LOL, T, [ac('abc123', seen_pos=0.45)])['abc123']
        self.assertEqual(a['true_heading'], 90.0); self.assertEqual(a['nav_qnh'], 1011.2)

    def test_mlat_held_and_jump(self):
        h = S.Hub(); T = time.time()
        feed(h, LOL, T, [ac('abc123', lat=37.600, seen_pos=5.0)])
        a = feed(h, FI, T, [ac('abc123', lat=37.700, seen_pos=0.1, type='mlat')])['abc123']
        self.assertEqual(a['lat'], 37.600)
        h2 = S.Hub()
        feed(h2, LOL, T - 40, [ac('abc123', lat=37.600, seen_pos=0.0, type='mlat', gs=10.0)])
        a2 = feed(h2, FI, T, [ac('abc123', lat=37.700, seen_pos=0.0, type='mlat', gs=10.0)])['abc123']
        self.assertEqual(a2['lat'], 37.600)

    def test_ground_hygiene_and_vehicle_sticky(self):
        h = S.Hub(); T = time.time()
        a = feed(h, FI, T, [ac('abc123', alt_baro='ground', track=118.0, true_heading=298.1, mlat=['track', 'gs'], gs=8)])['abc123']
        self.assertNotIn('track', a); self.assertNotIn('gs', a); self.assertEqual(a['_drop'], ['gs', 'track'])
        feed(h, LOL, T, [ac('a24f2b', alt_baro='ground', category='C2')])
        a = feed(h, LOL, T + 1, [ac('a24f2b', alt_baro='ground')])['a24f2b']
        self.assertEqual(a.get('_veh'), 1)

    def test_old_position_becomes_lastPosition_and_delta(self):
        h = S.Hub(); T = time.time()
        a = feed(h, FI, T, [ac('abc123', seen_pos=75.0)])['abc123']
        self.assertNotIn('lat', a); self.assertAlmostEqual(a['lastPosition']['seen_pos'], 75.0, delta=0.5)
        h = S.Hub()
        feed(h, LOL, T, [ac('a1'), ac('a2')])
        feed(h, LOL, T + 1, [ac('a1', lat=37.7, seen_pos=0.1), ac('a2', seen_pos=1.5)])
        self.assertEqual([x['hex'] for x in json.loads(h.delta)['ac']], ['a1'])
        feed(h, LOL, T + 2, [ac('a1', lat=37.7, seen_pos=1.1)])
        self.assertEqual(json.loads(h.delta)['gone'], ['a2'])


class D1(unittest.TestCase):
    def test_ladd_and_pia_masked_military_not(self):
        h = S.Hub(ident=FakeMx()); T = time.time()
        m = feed(h, LOL, T, [ac('aaa111', dbFlags=8, r='N100AA', t='C172', flight='N100AA  ', squawk='1200', ownOp='Me'),
                             ac('bbb222', dbFlags=4, t='SR22', flight='N200BB'),
                             ac('ccc333', dbFlags=1, r='N300CC', t='C182', flight='N300CC')])
        self.assertIn('ccc333', m)                                   # military bit only: not D1
        self.assertEqual(m['ccc333']['r'], 'N300CC')
        masked = [a for k, a in m.items() if k.startswith('x')]
        self.assertEqual(len(masked), 2)
        for a in masked:
            self.assertRegex(a['hex'], r'^x[0-9a-f]{8}$'); self.assertEqual(a['_masked'], 'd1')
            for f in S.D1_DROP:
                self.assertNotIn(f, a)
            self.assertIn('t', a)                                    # type stays
        blob = json.dumps(h.latest) + h.delta.decode() + h.full.decode()
        for s in ('aaa111', 'bbb222', 'N100AA', 'N200BB'):
            self.assertNotIn(s, blob)

    def test_sticky_stable_key_and_flag_from_other_provider(self):
        h = S.Hub(); T = time.time()
        m1 = feed(h, FI, T, [ac('ddd444', dbFlags=8, r='N4')])
        k = next(iter(m1))
        m2 = feed(h, LOL, T + 1, [ac('ddd444', r='N4', seen_pos=0.1)], ttl=0.5)   # adsb.lol has no flag; fi expired
        self.assertEqual(list(m2), [k])                               # same masked key, still masked
        self.assertNotIn('r', m2[k])
        h2 = S.Hub(); h2.d1.salt = h.d1.salt
        m3 = feed(h2, LOL, T, [ac('ddd444', r='N4')])
        self.assertIn('ddd444', m3)                                   # unflagged in a new session: not masked
        feed(h2, FI, T, [ac('ddd444', dbFlags=12)])
        self.assertIn(k, h2.latest['ac'][0]['hex'])                   # a flag from either provider masks it

    def test_late_flag_purges_ident_history_and_tells_clients(self):
        # fix round 1: a provider whose record lacks dbFlags publishes the identity first; when the flag arrives the identity
        # must leave /api/ident and the ?history buffer, and the next payload carries 'forget' for that key
        h = S.Hub(); T = time.time()
        m1 = feed(h, FI, T, [ac('a1b2c3', r='N999ZZ', flight='N999ZZ')])
        self.assertIn('a1b2c3', m1)
        self.assertIsNotNone(h.ident_of('a1b2c3'))
        m2 = feed(h, LOL, T + 1, [ac('a1b2c3', r='N999ZZ', flight='N999ZZ', dbFlags=8, seen_pos=0.1)])
        k = next(iter(m2)); self.assertTrue(k.startswith('x'))
        self.assertIsNone(h.ident_of('a1b2c3'))
        self.assertFalse(any(b'N999ZZ' in b or b'a1b2c3' in b for _, b in h.history))    # history purged, no forget in it
        self.assertNotIn(b'a1b2c3', h.full); self.assertNotIn(b'N999ZZ', h.full)           # nor in the full snapshot
        self.assertEqual(json.loads(h.forget_ev[1])['forget'], ['a1b2c3'])               # streams get a 'forget' event
        self.assertEqual(h.counters.get('d1_late_flag'), 1)

    def test_forget_reaches_pollers_and_every_pending_event(self):
        # fix round 2: the forget list also reaches /api/adsb pollers (?since=S, keys they could have seen), and a client
        # that missed two late-flag events gets both, not only the newest
        h = S.Hub(); T = time.time()
        feed(h, FI, T, [ac('a1b2c3', r='N999ZZ'), ac('d4e5f6', r='N888YY')])
        s_seen = h.seq                                                     # a poller's last answer: both keys public
        feed(h, LOL, T + 1, [ac('a1b2c3', r='N999ZZ', dbFlags=8, seen_pos=0.1), ac('d4e5f6', r='N888YY', seen_pos=0.1)])
        feed(h, LOL, T + 2, [ac('a1b2c3', dbFlags=8, seen_pos=0.1), ac('d4e5f6', r='N888YY', dbFlags=4, seen_pos=0.1)])
        self.assertEqual(h.forget_since(s_seen), ['a1b2c3', 'd4e5f6'])     # poller: both events
        self.assertEqual(h.forget_since(s_seen, polled=False), ['a1b2c3', 'd4e5f6'])   # SSE stream: both events
        self.assertEqual(h.forget_since(h.seq), [])                        # already up to date: nothing
        self.assertEqual(h.forget_since(0), [])                            # never polled: learns nothing
        j = json.loads(h.adsb_answer(s_seen)); self.assertEqual(j['forget'], ['a1b2c3', 'd4e5f6']); self.assertIn('ac', j)
        self.assertNotIn('forget', json.loads(h.adsb_answer(0))); self.assertNotIn(b'a1b2c3', h.adsb_answer(h.seq))
        h2 = S.Hub(); feed(h2, FI, T, [ac('aaaaaa', r='N1')]); s_before = h2.seq
        feed(h2, FI, T + 1, [ac('aaaaaa', r='N1'), ac('bbbbbb', r='N2')])
        feed(h2, LOL, T + 2, [ac('bbbbbb', r='N2', dbFlags=8, seen_pos=0.1)])
        self.assertEqual(h2.forget_since(s_before), [])                    # last answer before bbbbbb was published
        self.assertEqual(h2.forget_since(s_before + 1), ['bbbbbb'])

    def test_type_only_masks_everything_including_anonymous(self):
        h = S.Hub(d1=S.D1('type-only')); T = time.time()
        m = feed(h, LOL, T, [ac('eee555', r='N5', flight='N5'), ac('~1a2b3c', flight='N6', type='tisb_other')])
        self.assertEqual(len(m), 2)
        self.assertTrue(all(k.startswith('x') and 'flight' not in a and 'r' not in a for k, a in m.items()))

    def test_mictronics_fill_and_ident_subset(self):
        h = S.Hub(ident=FakeMx()); T = time.time()
        m = feed(h, LOL, T, [ac('aaa111', t='C172'), ac('bbb222', dbFlags=8, flight='EJA123'),
                             ac('fff666', flight='EJA42')])
        self.assertEqual(m['aaa111']['_mx'], {'r': 'N100AA', 't': 'C172', 'd': 'CESSNA 172'})
        self.assertEqual(m['fff666']['_mx'], {'op': 'NetJets'})
        k = next(k for k in m if k.startswith('x'))
        self.assertNotIn('_mx', m[k])
        self.assertEqual(h.ident_of('aaa111')['r'], 'N100AA'); self.assertEqual(h.ident_of('aaa111')['r_src'], 'mictronics')
        self.assertEqual(set(h.ident_of(k)), {'key', 'masked', 't', 'desc', 'category'})
        self.assertIsNone(h.ident_of('123456'))                        # not in the picture: no look-up service

    def test_mictronics_flags_not_used(self):
        h = S.Hub(); T = time.time()
        m = feed(h, LOL, T, [ac('abcdef', r='N9')])                    # no dbFlags: never masked in 'full' mode
        self.assertIn('abcdef', m)


class Quota(unittest.TestCase):
    def test_rolling_cap_period_and_persistence(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, 'q.json')
        q = S.Quota(p, 500, horizon=3600)
        self.assertEqual(q.cap, 475)
        T = time.time()
        self.assertAlmostEqual(q.period(6.5, T), max(6.5, 3600 / 475), places=6)
        for i in range(375):
            q.log.append(T - 3600 + i)
        self.assertEqual(q.left(T), 100); self.assertAlmostEqual(q.period(6.5, T), 36.0)
        q.note(T); q2 = S.Quota(p, 500)
        self.assertEqual(q2.left(T), 99)                               # reloaded from disk
        for i in range(99):
            q2.log.append(T)
        self.assertEqual(q2.left(T), 0)
        self.assertAlmostEqual(q2.next_allowed(T), T - 3600 + 86400 + 1, delta=0.1)   # oldest ages out of 24 h
        q2.block(T + 7200, 'per-day'); self.assertGreaterEqual(q2.next_allowed(T), T + 7200)

    def test_two_processes_share_the_file(self):
        # fix round 1: two relays on one IP: each re-reads the shared log before deciding, so both together stay in the cap
        d = tempfile.mkdtemp(); p = os.path.join(d, 'q.json')
        a, b = S.Quota(p, 500), S.Quota(p, 500); T = time.time()
        for i in range(300):
            a.note(T - 1000 + i)
        self.assertEqual(b.left(T), 475)                              # b's in-memory log is stale ...
        self.assertGreater(b.next_allowed(T), T - 1)                  # ... next_allowed merges the file first
        self.assertEqual(b.left(T), 175)
        for i in range(175):
            b.note(T - 500 + i)
        self.assertEqual(S.Quota(p, 500).left(T), 0)                  # the file holds both processes' requests
        self.assertGreater(a.next_allowed(T), T + 3600)

    def test_budget_schedule_and_retry_after_in_full(self):
        q = S.Quota('', 500)
        p = S.Poller(LOL, lambda *a: None, quota=q)
        for _ in range(30):
            p._schedule(100.0, 100.4, True)
            self.assertTrue(106.5 <= p.next_due <= 107.6, p.next_due)  # >= 6.5 s: under ~10 per minute
        p._schedule(100.0, 100.4, False, retry_after=7200, status=429)
        self.assertAlmostEqual(p.next_due - 100.4, 7200)               # not capped at 300 s as in sfo3d
        f = S.Poller(FI, lambda *a: None)
        f._schedule(1790000000.3, 1790000000.6, True)
        self.assertAlmostEqual(f.next_due, 1790000002.3, places=6)      # adsb.fi: every even second + 0.3 s

    def test_snapshot_ttl_follows_expected_period(self):
        h = S.Hub(); q = S.Quota('', 500, horizon=3600)
        T = time.time()
        for i in range(375):
            q.log.append(T - 100)
        h.pollers['adsblol'] = S.Poller(LOL, lambda *a: None, quota=q)  # 100 left -> 36 s period
        self.assertAlmostEqual(h.snap_ttl('adsblol'), 1.5 * 36 + 5, places=1)
        h.ingest(LOL, T - 50, T - 50, {'now': (T - 50) * 1000, 'ac': [ac('abc123')]})
        h._merge()
        self.assertEqual(len(h.latest['ac']), 1)                       # 50 s old snapshot still merged (TTL 59 s)


class Serving(unittest.TestCase):
    def test_denied(self):
        deny = ['/refs/cache/local/registry/mictronics_lookup.json', '/refs/cache/adsb/hwd_events.json',
                '/tools/live/recio.py', '/out/phase1/x.png', '/out/replay/.state/adsblol_quota.json', '/out/replay',
                '/out/replay/', '/out/rec/adsblol_20261113_03.jsonl.gz', '/.git/config', '/jobs/a.mjs',
                '/node_modules/x/y.js', '/x/../refs/cache/local/a', '/%2e%2e/sfo3d/x', '/docs/qa/ref/a.png',
                '/out%2fphase1/a.png', '/__pycache__/hwd_live_server.cpython-313.pyc', '/tools/live/__pycache__/recio.pyc']
        allow = ['/live.html', '/js/geo.js', '/data/hwd_taxigraph.json', '/out/replay/pack.json.gz',
                 '/out/replay/replay_shim.js', '/out/replay/wx/metar_khwd_20261108T2100Z_5h.json', '/']
        # fix round 1: an allow-list, compared case-insensitively (APFS / NTFS map /Refs to refs)
        deny += ['/Refs/cache/local/x', '/REFS/cache/adsb/hwd_events.json', '/OUT/replay/../phase2/a.png', '/Out/phase2/run.json',
                 '/Tools/live/recio.py', '/docs/phase2/phase2_run_job.mjs', '/tools/qa/phase2_run_ref.py', '/docs/ATTRIBUTION.md', '/hwd_live_server.py',
                 '/CLAUDE.md', '/package.json', '/livetest.mjs', '/Jobs/views.mjs']
        allow += ['/LIVE.HTML', '/JS/geo.js', '/dev/world.html', '/live.css']
        for p in deny:
            self.assertTrue(S.denied(p), p)
        for p in allow:
            self.assertFalse(S.denied(p), p)

    def test_window_filter(self):
        L = [ac('a', lat=LAT + 7.9 / 60, lon=LON), ac('b', lat=LAT + 8.2 / 60, lon=LON),
             ac('c', alt_baro=6000), ac('d', alt_baro='ground'), {'hex': 'e', 'seen': 1},
             {'hex': 'f', 'lastPosition': {'lat': LAT, 'lon': LON, 'seen_pos': 70}}]
        self.assertEqual([a['hex'] for a in S.window_filter(L, 8)], ['a', 'c', 'd', 'f'])
        self.assertEqual([a['hex'] for a in S.window_filter(L, 8, 5000)], ['a', 'd', 'f'])


class RecordGuard(unittest.TestCase):
    def test_record_dir_case_sensitive_and_git_ignored(self):
        # fix round 2: `Refs/Cache/Local/rec` is not refs/cache/local/ on Linux (and not gitignored): refused; anything in a
        # git work tree that git does not ignore: refused
        for p in ('Refs/Cache/Local/rec', 'OUT/REPLAY/rec', 'Out/rec', 'out/replay/rec', 'out/Replay/rec', 'tools/rec',
                  'refs/cache/adsb/rec', os.path.join(ROOT, '..', 'hwd_rec_probe')):
            self.assertFalse(S.record_dir_check(os.path.join(ROOT, p) if not os.path.isabs(p) else p)[0], p)
        for p in ('refs/cache/local/rec', 'out/rec'):
            self.assertTrue(S.record_dir_check(os.path.join(ROOT, p))[0], p)
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(S.record_dir_check(os.path.join(d, 'rec'))[0])   # outside any work tree


class Weather(unittest.TestCase):
    def test_ttl_schedule_brackets_hh54(self):
        base = 1794168000                                               # 2026-11-08T20:00:00Z
        self.assertEqual(S.wx_ttl(base + 58 * 60), 60); self.assertEqual(S.wx_ttl(base + 60), 60)
        self.assertEqual(S.wx_ttl(base + 30 * 60), 300); self.assertEqual(S.wx_ttl(base + 54 * 60), 300)

    def test_replay_cache_and_station(self):
        d = tempfile.mkdtemp(); T = 1794168000.0
        with open(os.path.join(d, 'metar_khwd_t.json'), 'w') as f:
            json.dump([{'obsTime': T - 360, 'rawOb': 'METAR KHWD 081954Z A'}, {'obsTime': T - 3960, 'rawOb': 'METAR KHWD 081854Z B'},
                       {'obsTime': T + 3240, 'rawOb': 'METAR KHWD 082054Z FUTURE'}], f)
        time.sleep(0.01)
        clk = S.Clock(time.time(), T, 1.0)
        m = S.Metar(clk, wx_dir=d)
        body, ctype, _ = m.get('KHWD', 'raw')
        self.assertEqual(body.decode().split('\n'), ['METAR KHWD 081954Z A', 'METAR KHWD 081854Z B'])   # never the future
        with self.assertRaises(ValueError):
            m.get('KOAK', 'raw')
        m2 = S.Metar(S.Clock(time.time(), T + 3 * 86400 * 365, 1.0), wx_dir=d)   # far outside AWC's 30 days: no fetch
        with self.assertRaises(IOError):
            m2.get('KHWD', 'json')


class RecPack(unittest.TestCase):
    def test_xz_reader_and_replay_records(self):
        fs = sorted(glob.glob(os.path.join(S.REC_PACK, 'adsblol_20261108_20.jsonl.xz')))
        if not fs:
            self.skipTest('rec_pack not present')
        r = next(recio.lines(fs[0]))
        self.assertIn('d', r); self.assertIn('ac', r['d'])
        t0 = S.parse_time('2026-11-08T20:10Z')
        recs = []
        for t, pid, rr in S.replay_records(S.REC_PACK, t0, t0 + 120):
            recs.append(t)
        self.assertTrue(recs and recs == sorted(recs) and recs[0] >= t0 and recs[-1] <= t0 + 120)
        self.assertEqual(list(recio.lines(os.path.join(S.REC_PACK, 'adsblol_20261105_00.jsonl.xz'))), [])   # empty hour


if __name__ == '__main__':
    unittest.main(verbosity=2)
