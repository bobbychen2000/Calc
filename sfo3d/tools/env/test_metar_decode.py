#!/usr/bin/env python3
"""Unit tests for tools/env/metar_decode.py on 58 real KSFO reports + FAA coding examples.

Fixtures (verbatim, provenance in each file header):
  fixtures/ksfo_recent_20260920_24.txt  30 METAR/SPECI from aviationweather.gov, fetched 2026-09-24T19:37Z
  fixtures/ksfo_archive_wx.txt          28 archived KSFO reports with weather (IEM ASOS archive), 2016-2026
Expected values below were written by hand from the report text and the coding rules of FAA Order JO 7900.5E
(chapter 13), not produced by the decoder.

Run:  python3 tools/env/test_metar_decode.py        (stdlib unittest; exit status 1 on failure)
"""
import math, os, sys, unittest
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import metar_decode as M


def _lines(name):
    with open(os.path.join(HERE, 'fixtures', name)) as f:
        return [l.rstrip('\n') for l in f if l.strip() and not l.startswith('#')]


RECENT = _lines('ksfo_recent_20260920_24.txt')
ARCHIVE = [l.split('|', 1) for l in _lines('ksfo_archive_wx.txt')]
REF = datetime(2026, 9, 24, 19, 37, 6, tzinfo=timezone.utc)

# time, (dir, spd, gust), vis_sm, sky [(cover, ft)], (T, Td), altim, SLP, (Ttenths, Tdtenths), ceiling, category, extra
N = None
RECENT_EXPECT = [
    ('241856', (30, 6, N), 10, [('SCT', 20000)], (22, 16), 29.89, 1012.0, (21.7, 16.1), N, 'VFR', {}),
    ('241756', (50, 4, N), 10, [('SCT', 20000)], (20, 15), 29.89, 1012.2, (20.0, 15.0), N, 'VFR',
     {'max_temp_6h_c': 20.6, 'min_temp_6h_c': 15.0, 'pressure_tendency': {'character': 1, 'change_hpa': 0.4}}),
    ('241156', (290, 6, N), 10, [('FEW', 20000)], (16, 12), 29.86, 1010.9, (15.6, 12.2), N, 'VFR',
     {'max_temp_6h_c': 17.8, 'min_temp_6h_c': 15.0, 'pressure_tendency': {'character': 8, 'change_hpa': 0.2}, 'maintenance': True}),
    ('240756', (N, 0, N), 10, [('FEW', 20000)], (18, 13), 29.86, 1011.2, (17.8, 12.8), N, 'VFR',
     {'max_temp_24h_c': 25.6, 'min_temp_24h_c': 12.8}),
    ('240656', (290, 5, N), 10, [('CLR', N)], (16, 12), 29.86, 1011.1, (16.1, 12.2), N, 'VFR', {}),
    ('240056', (290, 16, N), 10, [('FEW', 1500), ('FEW', 20000)], (22, 12), 29.85, 1010.6, (22.2, 12.2), N, 'VFR', {}),
    ('232356', (290, 15, N), 10, [('FEW', 800), ('SCT', 20000)], (25, 12), 29.86, 1011.0, (25.0, 11.7), N, 'VFR',
     {'max_temp_6h_c': 25.6, 'min_temp_6h_c': 16.7, 'pressure_tendency': {'character': 8, 'change_hpa': 1.4}}),
    ('231856', (50, 4, N), 10, [('FEW', 600)], (18, 14), 29.95, 1014.1, (17.8, 14.4), N, 'VFR',
     {'sensor_status': ['VISNO'], 'maintenance': True}),
    ('231722', (90, 4, N), 10, [('FEW', 400), ('SCT', 800)], (16, 13), 29.96, N, (16.1, 13.3), N, 'VFR', {}),
    ('231656', (N, 0, N), 10, [('FEW', 400), ('OVC', 700)], (16, 13), 29.96, 1014.6, (15.6, 13.3), 700, 'IFR', {}),
    ('231556', (140, 5, N), 10, [('FEW', 300), ('OVC', 500)], (14, 13), 29.95, 1014.3, (14.4, 13.3), 500, 'IFR', {}),
    ('231156', (N, 0, N), 10, [('FEW', 500), ('BKN', 800)], (13, 11), 29.92, 1013.2, (12.8, 11.1), 800, 'IFR',
     {'max_temp_6h_c': 14.4, 'min_temp_6h_c': 12.8, 'pressure_tendency': {'character': 6, 'change_hpa': 0.5}, 'maintenance': True}),
    ('230756', (240, 4, N), 10, [('FEW', 500), ('SCT', 1000)], (14, 12), 29.94, 1013.8, (13.9, 12.2), N, 'VFR',
     {'max_temp_24h_c': 19.4, 'min_temp_24h_c': 13.9}),
    ('230356', (270, 7, N), 10, [('FEW', 600), ('SCT', 900), ('BKN', 1100)], (14, 12), 29.94, 1013.9, (14.4, 12.2), 1100, 'MVFR', {}),
    ('230206', (270, 12, N), 10, [('FEW', 600), ('BKN', 1100)], (15, 12), 29.93, N, (15.0, 12.2), 1100, 'MVFR', {}),
    ('230056', (280, 15, 20), 10, [('FEW', 600), ('BKN', 1200)], (16, 12), 29.93, 1013.4, (15.6, 12.2), 1200, 'MVFR',
     {'peak_wind': {'dir_true_deg': 280, 'speed_kt': 26, 'time': '2357'}}),
    ('230027', (270, 15, N), 10, [('FEW', 600), ('BKN', 1100)], (16, 12), 29.93, N, (16.1, 12.2), 1100, 'MVFR',
     {'peak_wind': {'dir_true_deg': 280, 'speed_kt': 26, 'time': '2357'}}),
    ('222356', (280, 20, 26), 10, [('FEW', 600), ('FEW', 1700)], (17, 12), 29.93, 1013.4, (16.7, 12.2), N, 'VFR',
     {'peak_wind': {'dir_true_deg': 290, 'speed_kt': 26, 'time': '2356'}, 'pressure_tendency': {'character': 6, 'change_hpa': 1.0}}),
    ('221756', (250, 10, N), 10, [('FEW', 500), ('BKN', 1500)], (17, 12), 29.99, 1015.5, (17.2, 12.2), 1500, 'MVFR', {}),
    ('220756', (280, 7, N), 10, [('FEW', 700), ('BKN', 1300)], (15, 12), 29.96, 1014.4, (15.0, 12.2), 1300, 'MVFR',
     {'max_temp_24h_c': 20.0, 'min_temp_24h_c': 14.4, 'maintenance': True}),
    ('212356', (260, 14, 22), 10, [('FEW', 800), ('FEW', 2200)], (18, 12), 29.93, 1013.5, (18.3, 12.2), N, 'VFR',
     {'pressure_tendency': {'character': 5, 'change_hpa': 0.4}}),
    ('212004', (250, 11, 15), 10, [('FEW', 600), ('SCT', 2200)], (19, 12), 29.95, N, (18.9, 12.2), N, 'VFR', {}),
    ('211856', (260, 9, N), 10, [('FEW', 600), ('BKN', 2000), ('BKN', 2800)], (18, 12), 29.97, 1014.7, (17.8, 12.2), 2000, 'MVFR', {}),
    ('211756', (250, 7, N), 10, [('FEW', 600), ('BKN', 1700), ('OVC', 2600)], (17, 12), 29.97, 1015.0, (16.7, 11.7), 1700, 'MVFR', {}),
    ('211456', (230, 7, N), 10, [('FEW', 400), ('OVC', 1200)], (14, 12), 29.96, 1014.6, (14.4, 11.7), 1200, 'MVFR',
     {'pressure_tendency': {'character': 3, 'change_hpa': 0.9}}),
    ('210156', (280, 10, N), 10, [('FEW', 400), ('FEW', 2000), ('BKN', 15000), ('BKN', 18000)], (16, 12), 29.93, 1013.3, (15.6, 12.2), 15000, 'VFR', {}),
    ('202356', (300, 11, N), 10, [('FEW', 400), ('FEW', 1700), ('BKN', 15000), ('BKN', 18000)], (17, 13), 29.91, 1013.0, (17.2, 12.8), 15000, 'VFR', {}),
    ('202156', (280, 11, N), 10, [('FEW', 400), ('BKN', 1500), ('BKN', 15000)], (18, 12), 29.94, 1013.7, (17.8, 12.2), 1500, 'MVFR',
     {'pressure_rapid': 'falling'}),
    ('200356', (270, 12, 21), 10, [('FEW', 400), ('BKN', 900)], (14, 12), 29.97, 1014.9, (14.4, 12.2), 900, 'IFR', {}),
    ('200056', (290, 20, 27), 10, [('FEW', 300), ('SCT', 200 * 100)], (17, 12), 29.95, 1014.2, (16.7, 12.2), N, 'VFR',
     {'peak_wind': {'dir_true_deg': 290, 'speed_kt': 30, 'time': '0028'}}),
]


class Recent(unittest.TestCase):
    """The 30 reports from the last days (aviationweather.gov)."""

    def test_count(self):
        self.assertEqual(len(RECENT), 30)
        self.assertEqual(len(RECENT_EXPECT), 30)

    def test_each(self):
        for line, (tm, wind, vis, sky, tt, alt, slp, tg, ceil, cat, extra) in zip(RECENT, RECENT_EXPECT):
            with self.subTest(line=line):
                d = M.decode_metar(line, REF)
                self.assertIn(' %sZ ' % tm, line)
                self.assertEqual(d['station'], 'KSFO')
                self.assertEqual(d['type'], line.split()[0])
                self.assertEqual((d['time']['day'], d['time']['hour'], d['time']['minute']), (int(tm[:2]), int(tm[2:4]), int(tm[4:])))
                self.assertTrue(d['time']['utc'].startswith('2026-09-%s' % tm[:2]))
                w = d['wind']
                self.assertEqual((w['dir_true_deg'], w['speed_kt'], w['gust_kt']), wind)
                self.assertEqual(w['calm'], wind[1] == 0)
                self.assertAlmostEqual(d['visibility']['sm'], vis)
                self.assertAlmostEqual(d['visibility']['m'], vis * 1609.344)
                self.assertEqual([(s['cover'], s['height_ft']) for s in d['sky']], sky)
                self.assertEqual((d['temp_c'], d['dewpoint_c']), tt)
                self.assertAlmostEqual(d['altimeter_inhg'], alt)
                self.assertAlmostEqual(d['qnh_hpa'], round(alt * 33.8639, 1))
                self.assertEqual(d['rmk'].get('slp_hpa'), slp)
                self.assertEqual((d['rmk']['temp_c_tenths'], d['rmk']['dewpoint_c_tenths']), tg)
                self.assertEqual(d['ceiling_ft'], ceil)
                self.assertEqual(d['flight_category'], cat)
                self.assertEqual(d['rmk']['station_type'], 'AO2')
                for k, v in extra.items():
                    self.assertEqual(d['rmk'].get(k), v, k)
                self.assertNotIn('unparsed', d)
                self.assertNotIn('plain', d['rmk'])
                if 'COR' in line:
                    self.assertEqual(d['modifier'], ['COR'])

    def test_slp_matches_altimeter(self):
        # SLP and altimeter differ by < 2 hPa at a 13 ft station; the 9xx/10xx choice must follow the altimeter.
        for line in RECENT:
            d = M.decode_metar(line)
            if d['rmk'].get('slp_hpa'):
                self.assertLess(abs(d['rmk']['slp_hpa'] - d['qnh_hpa']), 2.0, line)


class Archive(unittest.TestCase):
    """28 archived KSFO reports with fog, mist, rain, drizzle, thunderstorms, hail, smoke, haze and rare remarks."""

    def d(self, key):
        for valid, line in ARCHIVE:
            if key in line:
                return M.decode_metar(line, datetime.strptime(valid, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)), valid
        raise KeyError(key)

    def test_count_and_clean(self):
        self.assertEqual(len(ARCHIVE), 28)
        for valid, line in ARCHIVE:
            d = M.decode_metar(line)
            self.assertNotIn('unparsed', d, line)
            self.assertNotIn('plain', d['rmk'], line)
            self.assertEqual(d['time']['hour'] * 100 + d['time']['minute'], int(valid[11:13]) * 100 + int(valid[14:16]))

    def test_fog_vv_rvr(self):
        d, _ = self.d('081356Z')
        self.assertEqual((d['visibility']['sm'], d['visibility']['prefix']), (0.25, 'M'))
        self.assertEqual(d['rvr'][0] | {}, {'runway': '28R', 'min_ft': 1000, 'min_prefix': None, 'max_ft': 1400, 'max_prefix': None,
                                           'unit': 'ft', 'tendency': None, 'raw': 'R28R/1000V1400FT'})
        self.assertEqual(d['weather'][0]['phenomena'], ['FG'])
        self.assertEqual([(s['cover'], s['height_ft']) for s in d['sky']], [('VV', 200)])
        self.assertEqual((d['ceiling_ft'], d['flight_category']), (200, 'LIFR'))
        self.assertEqual(d['rmk']['slp_hpa'], 1016.1)

    def test_rvr_plus(self):
        d, _ = self.d('021604Z')
        r = d['rvr'][0]
        self.assertEqual((r['min_ft'], r['min_prefix'], r['max_ft']), (6000, 'P', None))
        self.assertEqual((d['ceiling_ft'], d['flight_category']), (300, 'LIFR'))

    def test_surface_obscuration_not_ceiling(self):
        # [7900] 10.4a / 13.35: BKN000 = fog hiding 5-7/8 of the sky, a surface-based partial obscuration, not a ceiling.
        d, _ = self.d('070939Z')
        self.assertIsNone(d['ceiling_ft'])
        self.assertEqual(d['flight_category'], 'LIFR')
        self.assertEqual(d['rmk']['obscuration_layers'], [{'wx': 'FG', 'cover': 'BKN', 'height_ft': 0}])
        self.assertEqual(d['rvr'][0]['min_ft'], 1600)
        self.assertEqual(d['rvr'][0]['max_ft'], 3000)

    def test_partial_fog_sector(self):
        d, _ = self.d('070925Z')
        self.assertEqual(d['modifier'], ['COR'])
        w = d['weather'][0]
        self.assertEqual((w['descriptor'], w['phenomena']), ('PR', ['FG']))
        self.assertEqual(d['rmk']['vis_sector'], [{'dirs': ['NE', 'E'], 'sm': 0.25, 'prefix': 'M'}])
        self.assertEqual((d['rvr'][0]['min_ft'], d['rvr'][0]['max_ft'], d['rvr'][0]['max_prefix']), (1600, 6000, 'P'))
        self.assertEqual(d['flight_category'], 'MVFR')

    def test_tower_vis(self):
        d, _ = self.d('131956Z')
        self.assertEqual(d['rmk']['tower_vis_sm'], 6.0)
        self.assertEqual(d['visibility']['sm'], 0.5)
        self.assertEqual(d['weather'][0]['descriptor'], 'BC')
        self.assertEqual(d['rmk']['slp_hpa'], 1021.6)

    def test_bcfg_at_10sm_sector(self):
        d, _ = self.d('261243Z')
        self.assertEqual(d['visibility']['sm'], 10)
        self.assertEqual(d['rmk']['vis_sector'][0]['dirs'], ['NW'])
        self.assertEqual(d['rmk']['vis_sector'][0]['sm'], 0.5)
        self.assertEqual((d['ceiling_ft'], d['flight_category']), (400, 'LIFR'))

    def test_fog_in_gap(self):
        d, _ = self.d('150256Z')
        self.assertTrue(d['weather'][0]['vicinity'])
        self.assertEqual(d['weather'][0]['phenomena'], ['FG'])
        self.assertEqual(d['rmk']['fog_in_gap'], 'IN GAP W')
        self.assertEqual(d['rmk']['pressure_tendency'], {'character': 5, 'change_hpa': 0.0})

    def test_mist_low_overcast(self):
        d, _ = self.d('081703Z')
        self.assertEqual(d['visibility']['sm'], 0.75)
        self.assertEqual((d['ceiling_ft'], d['flight_category']), (200, 'LIFR'))

    def test_squall_heavy_rain(self):
        d, _ = self.d('251056Z')
        self.assertEqual((d['wind']['dir_true_deg'], d['wind']['speed_kt'], d['wind']['gust_kt']), (220, 36, 63))
        self.assertEqual([w['raw'] for w in d['weather']], ['+RA', 'BR', 'SQ'])
        self.assertEqual(d['weather'][0]['intensity'], 'heavy')
        self.assertEqual(d['rmk']['peak_wind'], {'dir_true_deg': 230, 'speed_kt': 63, 'time': '1053'})
        self.assertEqual(d['rmk']['slp_hpa'], 1002.6)
        self.assertEqual(d['rmk']['precip_hourly_in'], 0.16)
        self.assertEqual(d['flight_category'], 'IFR')

    def test_mixed_fraction_and_speci_rate(self):
        d, _ = self.d('170810Z')
        self.assertEqual(d['visibility']['sm'], 1.25)
        self.assertEqual(d['visibility']['raw'], '1 1/4SM')
        self.assertEqual(d['rmk']['wind_shift'], {'time': '0745', 'fropa': False})
        p = M.render_params(d)
        # P0036 over 14 minutes (08:10 SPECI after the 07:56 METAR) = 0.36 in * 25.4 * 60/14
        self.assertAlmostEqual(p['precip']['rate_mm_h'], round(0.36 * 25.4 * 60 / 14, 2))

    def test_thunderstorm_remarks(self):
        d, _ = self.d('180320Z')
        w = d['weather'][0]
        self.assertEqual((w['intensity'], w['descriptor'], w['precip']), ('light', 'TS', ['RA']))
        self.assertEqual([(s['cover'], s['height_ft'], s['type']) for s in d['sky']], [('SCT', 2900, None), ('BKN', 4400, 'CB'), ('OVC', 8000, None)])
        self.assertEqual(d['rmk']['lightning'], [{'frequency': 'FRQ', 'types': ['IC', 'CC', 'CG'], 'loc': 'SE'}])
        self.assertEqual(d['rmk']['phenomena'], [{'what': 'VCTS', 'loc': 'MOV N'}])
        self.assertEqual(d['rmk']['wx_events'], [{'wx': 'RA', 'event': 'begin', 'time': '02'}, {'wx': 'TS', 'event': 'begin', 'time': '20'}])
        p = M.render_params(d)
        self.assertTrue(p['lightning']['at_station'])
        self.assertEqual(p['lightning']['flashes_per_min'], 3.5)

    def test_occasional_lightning(self):
        d, _ = self.d('120056Z')
        self.assertEqual(d['visibility']['sm'], 2.5)
        self.assertEqual(d['rmk']['lightning'], [{'frequency': 'OCNL', 'types': ['IC'], 'loc': 'NE'}])
        self.assertEqual(d['rmk']['slp_hpa'], 1008.0)

    def test_vcts_haze(self):
        d, _ = self.d('260022Z')
        self.assertEqual([(w['vicinity'], w['descriptor']) for w in d['weather']], [(True, 'TS'), (False, None)])
        self.assertEqual(d['rmk']['wx_events'], [{'wx': 'RA', 'event': 'end', 'time': '22'}])
        p = M.render_params(d)
        self.assertTrue(p['lightning']['vicinity'])
        self.assertFalse(p['lightning']['at_station'])
        self.assertTrue(p['aerosol']['haze'])
        self.assertIsNone(p['precip'])
        self.assertTrue(p['surface']['precip_ended_this_hour'])

    def test_hail(self):
        d, _ = self.d('020448Z')
        self.assertEqual(d['weather'][0]['phenomena'], ['GR', 'RA'])
        self.assertEqual(d['rmk']['hail_size_in'], '<1/4')
        self.assertEqual(d['rmk']['wx_events'], [{'wx': 'GR', 'event': 'begin', 'time': '47'},
                                                 {'wx': 'TS', 'event': 'begin', 'time': '30'}, {'wx': 'TS', 'event': 'end', 'time': '48'}])
        self.assertEqual(d['rmk']['phenomena'], [{'what': 'TS', 'loc': 'DSIPTD'}])

    def test_drizzle(self):
        d, _ = self.d('301456Z')
        self.assertEqual(d['weather'][0]['raw'], '-DZ')
        self.assertEqual(d['rmk']['precip_3or6h_in'], 0.0)       # 60000 = trace
        self.assertEqual(d['rmk']['precip_hourly_in'], 0.0)      # P0000 = less than 0.01 in
        p = M.render_params(d)
        self.assertEqual(p['precip']['kind'], 'drizzle')
        d2, _ = self.d('261021Z')
        self.assertEqual(d2['visibility']['sm'], 2.5)

    def test_smoke(self):
        d, _ = self.d('271256Z')
        self.assertEqual(d['rmk']['obscuration_layers'], [{'wx': 'FU', 'cover': 'FEW', 'height_ft': 400}])
        d2, _ = self.d('112156Z')
        self.assertEqual(d2['rmk']['phenomena'], [{'what': 'FU', 'loc': 'DSNT E'}])
        self.assertEqual((d2['rmk']['temp_c_tenths'], d2['rmk']['dewpoint_c_tenths']), (30.0, 11.1))

    def test_surface_vis(self):
        d, _ = self.d('101915Z')
        self.assertEqual(d['rmk']['surface_vis_sm'], 1.0)
        self.assertEqual(d['visibility']['sm'], 0.75)

    def test_variable_ceiling(self):
        d, _ = self.d('280356Z')
        self.assertEqual(d['rmk']['cig_variable_ft'], (400, 1000))
        self.assertEqual((d['ceiling_ft'], d['flight_category']), (600, 'IFR'))

    def test_ceiling_second_location(self):
        d, _ = self.d('092256Z')
        self.assertEqual(d['rmk']['cig_second_location'], {'height_ft': 3000, 'loc': 'RWY L10'})

    def test_variable_visibility_mixed(self):
        d, _ = self.d('171624Z')
        self.assertEqual(d['rmk']['vis_variable_sm'], (0.5, 2.5))
        self.assertEqual(d['rmk']['vis_sector'], [{'dirs': ['E'], 'sm': 1.0, 'prefix': None}])
        self.assertEqual(d['rmk']['vis_other'], [{'sm': 3.0, 'loc': None}])
        d2, _ = self.d('130052Z')
        self.assertEqual(d2['visibility']['sm'], 1.75)
        self.assertEqual(d2['rmk']['vis_variable_sm'], (1.0, 3.0))

    def test_wind_variability(self):
        d, _ = self.d('082356Z')
        self.assertEqual((d['wind']['var_from'], d['wind']['var_to'], d['wind']['gust_kt']), (220, 280, 20))
        d2, _ = self.d('280736Z')
        self.assertEqual((d2['wind']['dir_true_deg'], d2['wind']['speed_kt'], d2['wind']['variable']), (None, 3, True))

    def test_sensor_status(self):
        d, _ = self.d('261756Z')
        self.assertEqual(d['rmk']['sensor_status'], ['CHINO RWY L10', 'VISNO'])
        self.assertTrue(d['rmk']['maintenance'])

    def test_pressure_rising_and_distant_lightning(self):
        d, _ = self.d('241049Z')
        self.assertEqual(d['rmk']['pressure_rapid'], 'rising')
        d2, _ = self.d('250956Z')
        self.assertEqual(d2['rmk']['lightning'], [{'frequency': None, 'types': [], 'loc': 'DSNT SW AND W'}])
        self.assertEqual(d2['rmk']['slp_hpa'], 1001.0)


class FaaExamples(unittest.TestCase):
    """Coding examples quoted in FAA Order JO 7900.5E chapter 13 (paragraph in each assertion)."""

    def test_groups(self):
        d = M.decode_metar('METAR KXXX 011755Z 27020G35KT 180V240 M1/4SM R01L/0600V1000FT R01L/M0600FT -FZDZ VCSH +FC '
                           'VV010 M05/ A2992 RMK AO2 PK WND 28045/15 WSHFT 30 FROPA TWR VIS 1 1/2 VIS 1/2V2 VIS NE 2 1/2 '
                           'VIS 2 1/2 RWY11 RAB05E30SNB20E55 TSB0159E30 CIG 005V010 FG SCT000 FU BKN020 BKN014 V OVC '
                           'CIG 002 RWY11 PRESFR SLP982 P0009 60217 T00261015 11001 21021 401001015 52032 PWINO FZRANO TSNO $')
        self.assertEqual((d['wind']['gust_kt'], d['wind']['var_from'], d['wind']['var_to']), (35, 180, 240))     # 13.10
        self.assertEqual((d['visibility']['sm'], d['visibility']['prefix']), (0.25, 'M'))                         # 13.11
        self.assertEqual((d['rvr'][0]['min_ft'], d['rvr'][0]['max_ft']), (600, 1000))                            # 13.12
        self.assertEqual((d['rvr'][1]['min_ft'], d['rvr'][1]['min_prefix']), (600, 'M'))
        self.assertEqual([w['raw'] for w in d['weather']], ['-FZDZ', 'VCSH', '+FC'])                              # 13.13
        self.assertTrue(d['weather'][2]['tornadic'])
        self.assertEqual((d['sky'][0]['cover'], d['sky'][0]['height_ft'], d['ceiling_ft']), ('VV', 1000, 1000))  # 13.14e
        self.assertEqual((d['temp_c'], d['dewpoint_c']), (-5, None))                                             # 13.15c
        r = d['rmk']
        self.assertEqual(r['peak_wind'], {'dir_true_deg': 280, 'speed_kt': 45, 'time': '15'})                    # 13.22
        self.assertEqual(r['wind_shift'], {'time': '30', 'fropa': True})                                         # 13.23
        self.assertEqual(r['tower_vis_sm'], 1.5)                                                                 # 13.24
        self.assertEqual(r['vis_variable_sm'], (0.5, 2.0))                                                       # 13.25
        self.assertEqual(r['vis_sector'], [{'dirs': ['NE'], 'sm': 2.5, 'prefix': None}])                         # 13.26
        self.assertEqual(r['vis_other'], [{'sm': 2.5, 'loc': 'RWY11'}])                                          # 13.27
        self.assertEqual(len(r['wx_events']), 6)                                                                 # 13.29/13.30
        self.assertEqual(r['wx_events'][4], {'wx': 'TS', 'event': 'begin', 'time': '0159'})
        self.assertEqual(r['cig_variable_ft'], (500, 1000))                                                      # 13.34
        self.assertEqual(r['obscuration_layers'], [{'wx': 'FG', 'cover': 'SCT', 'height_ft': 0},
                                                   {'wx': 'FU', 'cover': 'BKN', 'height_ft': 2000}])             # 13.35
        self.assertEqual(r['sky_variable'], [{'from': 'BKN', 'height_ft': 1400, 'to': 'OVC'}])                   # 13.36
        self.assertEqual(r['cig_second_location'], {'height_ft': 200, 'loc': 'RWY11'})                           # 13.38
        self.assertEqual(r['pressure_rapid'], 'falling')                                                         # 13.39
        self.assertEqual(r['slp_hpa'], 998.2)                                                                    # 13.40
        self.assertEqual(r['precip_hourly_in'], 0.09)                                                            # 13.46
        self.assertEqual(r['precip_3or6h_in'], 2.17)                                                             # 13.48
        self.assertEqual((r['temp_c_tenths'], r['dewpoint_c_tenths']), (2.6, -1.5))                             # 13.52
        self.assertEqual((r['max_temp_6h_c'], r['min_temp_6h_c']), (-0.1, -2.1))                                # 13.53/54
        self.assertEqual((r['max_temp_24h_c'], r['min_temp_24h_c']), (10.0, -1.5))                              # 13.55
        self.assertEqual(r['pressure_tendency'], {'character': 2, 'change_hpa': 3.2})                           # 13.56
        self.assertEqual(r['sensor_status'], ['PWINO', 'FZRANO', 'TSNO'])                                        # 13.57
        self.assertTrue(r['maintenance'])                                                                        # 13.58
        self.assertNotIn('plain', r)
        self.assertNotIn('unparsed', d)

    def test_aim_key_example(self):
        # AIM 7-1-28 key: METAR KPIT 091955Z COR 22015G25KT 3/4SM R28L/2600FT TSRA OVC010CB 18/16 A2992 RMK SLP045 T01820159
        d = M.decode_metar('METAR KPIT 091955Z COR 22015G25KT 3/4SM R28L/2600FT TSRA OVC010CB 18/16 A2992 RMK SLP045 T01820159')
        self.assertEqual(d['rmk']['slp_hpa'], 1004.5)             # "1004.5 hPa"
        self.assertEqual((d['rmk']['temp_c_tenths'], d['rmk']['dewpoint_c_tenths']), (18.2, 15.9))
        self.assertEqual((d['rvr'][0]['runway'], d['rvr'][0]['min_ft']), ('28L', 2600))
        self.assertEqual((d['ceiling_ft'], d['flight_category']), (1000, 'LIFR'))   # vis 3/4 < 1 -> LIFR (AIM 7-1-7)

    def test_flight_category_boundaries(self):
        # AIM 7-1-7: LIFR cig < 500 or vis < 1; IFR 500-<1000 or 1-<3; MVFR 1000-3000 or 3-5 inclusive; VFR otherwise.
        f = lambda s: M.decode_metar('KSFO 010056Z 28010KT ' + s + ' 15/10 A3000')['flight_category']
        self.assertEqual(f('1SM OVC005'), 'IFR')
        self.assertEqual(f('10SM OVC004'), 'LIFR')
        self.assertEqual(f('3SM BKN030'), 'MVFR')
        self.assertEqual(f('5SM BKN031'), 'MVFR')
        self.assertEqual(f('6SM BKN031'), 'VFR')
        self.assertEqual(f('2 1/2SM SCT010'), 'IFR')


class Taf(unittest.TestCase):
    def test_ksfo_taf(self):
        # aviationweather.gov /api/data/taf?ids=KSFO&format=raw, fetched 2026-09-24T19:3xZ
        t = M.decode_taf('TAF KSFO 241725Z 2418/2524 32010KT P6SM SCT200 FM242100 29016KT P6SM SCT200 FM250800 27015G23KT '
                         'P6SM SCT250 FM251200 28009KT P6SM SCT010 BKN250 FM252100 28018KT P6SM FEW250')
        self.assertEqual((t['station'], t['issued'], t['valid']), ('KSFO', '241725Z', '2418/2524'))
        self.assertEqual([p['change'] for p in t['periods']], ['BASE', 'FM', 'FM', 'FM', 'FM'])
        self.assertEqual(t['periods'][2]['wind']['gust_kt'], 23)
        self.assertEqual((t['periods'][0]['visibility']['sm'], t['periods'][0]['visibility']['prefix']), (6, 'P'))
        self.assertEqual(t['periods'][3]['ceiling_ft'], 25000)
        self.assertEqual([s['height_ft'] for s in t['periods'][3]['sky']], [1000, 25000])

    def test_tempo_prob(self):
        t = M.decode_taf('TAF KPIT 091730Z 0918/1024 15005KT 5SM HZ FEW020 WS010/31022KT FM091930 30015G25KT 3SM SHRA OVC015 '
                         'TEMPO 0920/0922 1/2SM +TSRA OVC008CB FM100100 27008KT 5SM SHRA BKN020 OVC040 PROB30 1004/1007 1SM -RA BR '
                         'FM101015 18005KT 6SM -SHRA OVC020 BECMG 1013/1015 P6SM NSW SKC')     # AIM 7-1-28 example
        ch = [(p['change'], p['from'], p['to']) for p in t['periods']]
        self.assertEqual(ch, [('BASE', '0918', None), ('FM', '091930', None), ('TEMPO', '0920', '0922'), ('FM', '100100', None),
                              ('PROB', '1004', '1007'), ('FM', '101015', None), ('BECMG', '1013', '1015')])
        self.assertEqual(t['periods'][0]['wind_shear'], {'height_ft': 1000, 'dir': 310, 'speed_kt': 22})
        self.assertEqual(t['periods'][4]['prob'], 30)
        self.assertEqual(t['periods'][2]['ceiling_ft'], 800)
        for p in t['periods']:
            self.assertNotIn('unparsed', p)


class Render(unittest.TestCase):
    def test_extinction_day(self):
        # Koschmieder with the ASOS contrast threshold 0.055: sigma = -ln(0.055)/V
        self.assertAlmostEqual(M.extinction_from_visibility(1609.344), -math.log(0.055) / 1609.344)
        self.assertAlmostEqual(M.extinction_from_visibility(16093.44), 1.8022e-4, places=7)

    def test_night_vs_day_ratio(self):
        # Rasmussen et al. 1999: for day visibility 0.5 mi the same object is seen "a little less than twice as far at night";
        # below 0.1 mi in daytime a 25-candle light is seen "more than 2.4 times as far".
        def night_vis_for(sigma):
            lo, hi = 1.0, 1e6
            for _ in range(200):
                mid = math.sqrt(lo * hi)
                if M.extinction_from_visibility(mid, night=True) > sigma:
                    lo = mid
                else:
                    hi = mid
            return mid
        for vd_mi, lo_r, hi_r in ((0.5, 1.85, 2.0), (0.1, 2.4, 2.6)):
            s = M.extinction_from_visibility(vd_mi * 1609.344)
            r = night_vis_for(s) / (vd_mi * 1609.344)
            self.assertTrue(lo_r < r < hi_r, (vd_mi, r))

    def test_layer_summation(self):
        d = M.decode_metar(RECENT[15])      # FEW006 BKN012
        p = M.render_params(d)
        few, bkn = p['cloud_layers']
        self.assertAlmostEqual(few['summation'], 1.25 / 8, places=3)
        self.assertAlmostEqual(bkn['summation'], 0.75)
        self.assertAlmostEqual(bkn['own_fraction'], round(1 - 0.25 / (1 - 1.25 / 8), 3))
        self.assertAlmostEqual(p['sun_visible_probability'], 0.25, places=3)

    def test_windsock(self):
        f = lambda kt: M.render_params(M.decode_metar('KSFO 010056Z 280%02dKT 10SM CLR 15/10 A3000' % kt))['wind']['windsock_extension']
        self.assertEqual(f(2), 0.0)
        self.assertEqual(f(3), 0.0)
        self.assertEqual(f(9), 0.5)
        self.assertEqual(f(15), 1.0)
        self.assertEqual(f(25), 1.0)

    def test_fog_params(self):
        d = M.decode_metar(ARCHIVE[0][1])
        p = M.render_params(d)
        self.assertEqual(p['fog']['kind'], 'fog')
        self.assertEqual(p['fog']['vertical_visibility_ft'], 200)
        self.assertGreater(p['extinction_per_m'], 0.007)       # M1/4SM: sigma > 2.9/402 m
        self.assertFalse(p['visibility_is_lower_bound'])
        self.assertTrue(M.render_params(M.decode_metar(RECENT[0]))['visibility_is_lower_bound'])

    def test_rain_microphysics(self):
        d = M.decode_metar('KSFO 010056Z 18010KT 3SM RA BR OVC010 12/11 A2990 RMK AO2 P0020')
        p = M.render_params(d)['precip']
        self.assertAlmostEqual(p['rate_mm_h'], 5.08)
        lam = 4.1 * 5.08 ** -0.21
        self.assertAlmostEqual(p['median_volume_diameter_mm'], round(3.67 / lam, 2))
        self.assertEqual(p['drops_per_m3_gt_0p5mm'], round(8000 / lam * math.exp(-0.5 * lam), 0))


if __name__ == '__main__':
    unittest.main(verbosity=1)
