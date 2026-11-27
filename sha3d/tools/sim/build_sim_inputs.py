#!/usr/bin/env python3
"""Build data/sha_sim_inputs.js (window.SHA_SIM_INPUTS) + data/sha_sim_inputs.json + data/SOURCES_sim.json: the committed
inputs of the Phase 3 day plan (docs/phase3/design.md s.2.1, s.7.1 SimInputs; package P3-A).

  python3 -I tools/sim/build_sim_inputs.py           build (needs the local refs/cache inputs; deterministic)
  python3 -I tools/sim/build_sim_inputs.py --check   rebuild in memory and compare with the committed files (exit 1 on a diff)

AGGREGATES ONLY (OD4). The local observed-elsewhere tables (refs/cache/observed_elsewhere/sha_observed_<day>.json, never
committed) are read for counts: per airline x ICAO type, per airline international / HMT, same-airframe turnaround
quantiles and the continuation counts of the observed days. Every count cell below MIN_CELL (3) is merged ("other", and
pooled cells that stay small are folded into the most common type of their family), so that no committed number points
to one flight. No callsign, flight number, registration, 24-bit address or per-flight time of those tables is written.

The 'published' section holds rows of the open Hong Kong (DATA.GOV.HK) and Taipei Songshan (Taiwan OGDL v1.0) flight
information of 13 / 14 Nov 2026 (refs/cache/schedules_open/*/SOURCES.json: redistributable true, attribution below):
published schedule facts, not observed-elsewhere data (design s.3 allow-list, tools/sim/audit_identity.py). Their SHA
times are inferred (far-end time -/+ far taxi -/+ air time).

NOTAM effect records: ids, windows and targets only (OD3 short facts), from the local parse of the eAIP NOTAM Summary.
"""
import argparse, datetime as dt, hashlib, json, math, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))                  # sha3d/
REFS = os.path.join(ROOT, 'refs', 'cache')
OBS_DIR = os.path.join(REFS, 'observed_elsewhere')
OUT_JS = os.path.join(ROOT, 'data', 'sha_sim_inputs.js')
OUT_JSON = os.path.join(ROOT, 'data', 'sha_sim_inputs.json')
OUT_SRC = os.path.join(ROOT, 'data', 'SOURCES_sim.json')
BUILT = '2026-11-27'                 # spec date of this build (deterministic: not the wall clock)
OBS_DAYS = ('2026-11-10', '2026-11-12')
MIN_CELL = 3                         # design s.2.1: cells < 3 merged
CONSISTENT = ('track_consistent', 'far_end_match')
MAINLAND = ('ZB', 'ZG', 'ZH', 'ZJ', 'ZL', 'ZP', 'ZS', 'ZU', 'ZW', 'ZY')       # ICAO prefixes of mainland China
FOREIGN = ('CPA', 'CRK', 'AMU', 'CAL', 'EVA', 'KAL', 'AAR', 'JAL', 'ANA')     # carriers based outside the mainland (HMT / foreign)
T1_AIRLINES = ('CQH', 'HBH', 'CXA')  # 9C Spring, NS Hebei, MF XiamenAir: T1 island D domestic (SAA directory, field.md s.2.2) [obs; reading inf]
INTL_MAINLAND = ('CES', 'CSH', 'CCA')  # MU, FM, CA: their international / HMT flights at T1 (field.md s.2.2) [obs; reading inf]
WIDE = {'A332', 'A333', 'A338', 'A339', 'A359', 'A35K', 'B762', 'B763', 'B764', 'B772', 'B773', 'B77L', 'B77W', 'B788',
        'B789', 'B78X', 'B744', 'B748', 'A388', 'A306', 'MD11'}
FAMILY = [(re.compile(r'^(A19N|A20N|A21N|A318|A319|A320|A321)$'), 'A320 family'), (re.compile(r'^B3[789]M$|^B73[6789]$'), '737 family'),
          (re.compile(r'^C919$'), 'C919'), (re.compile(r'^(AJ27|C909|CRJ\d|E1\d\d|E75[LS])$'), 'regional')]
GEO = {'ZSSS': (31.19784885, 121.3362899), 'VHHH': (22.308919, 113.914603), 'RCSS': (25.069722, 121.5525)}  # deg (OurAirports; ZSSS = frame origin)
# IATA aircraft codes as TSA publishes them -> ICAO designators (IATA Airline Coding Directory, from memory: unverified)
IATA_TYPE = {'A330-300': 'A333', '333': 'A333', '332': 'A332', '781': 'B78X', '789': 'B789', '788': 'B788', '321': 'A321',
             '320': 'A320', '319': 'A319', '73G': 'B737', '73H': 'B738', '73K': 'B738', '738': 'B738', '359': 'A359'}


def family(t):
    if t in WIDE:
        return 'wide-body'
    for rx, f in FAMILY:
        if rx.match(t):
            return f
    return 'other'


def sha16(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]


WITHHELD = 'local, hash withheld (OD4: no fingerprint of an observed-elsewhere table in a committable file)'


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT)


def iso_ms(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def op_day(ms):
    """operating day (04:00-04:00 UTC+8) of an instant: the local date of t + 8 h - 4 h"""
    return dt.datetime.fromtimestamp(ms / 1000 + 4 * 3600, dt.timezone.utc).strftime('%Y-%m-%d')


def gc_km(a, b):
    (la1, lo1), (la2, lo2) = GEO[a], GEO[b]
    p1, p2, dl = math.radians(la1), math.radians(la2), math.radians(lo2 - lo1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return 6371.0088 * math.acos(min(1.0, max(-1.0, c)))


def airlines_table():
    """data/lookup.js AIRLINES (VRS standing data, CC0; forked from sfo3d): ICAO -> 'Name|IATA'"""
    s = open(os.path.join(ROOT, 'data', 'lookup.js'), encoding='utf-8').read()
    m = re.search(r'export const AIRLINES = (\{.*?\});', s, re.S)
    return json.loads(m.group(1))


def largest_remainder(weights, n):
    keys = sorted(weights)
    tot = sum(weights[k] for k in keys)
    if tot <= 0 or n <= 0:
        return {k: 0 for k in keys}
    raw = {k: weights[k] * n / tot for k in keys}
    out = {k: int(math.floor(raw[k])) for k in keys}
    rest = n - sum(out.values())
    for k in sorted(keys, key=lambda k: (-(raw[k] - out[k]), k))[:rest]:
        out[k] += 1
    return out


# ------------------------------------------------------------------------------------------------ local aggregates
def load_observed():
    days = {}
    for day in OBS_DAYS:
        p = os.path.join(OBS_DIR, f'sha_observed_{day}.json')
        if not os.path.exists(p):
            sys.exit(f'missing local input {rel(p)} (the observed-elsewhere tables are local only; run where refs/cache exists)')
        d = json.load(open(p))
        M = [m for m in d['movements'] if m.get('consistency') in CONSISTENT and m.get('t_sha') is not None]
        w0, w1 = [int(dt.datetime.fromisoformat(x.replace('Z', '+00:00')).timestamp()) for x in d['window_utc']]
        days[day] = {'M': M, 'w0': w0, 'w1': w1, 'path': p}
    return days


def is_intl(m):
    return not (m.get('far') or 'ZS')[:2] in MAINLAND


def local_hour(t, w0):
    return ((t - w0) // 3600 + 4) % 24


def continuations(M, w0):
    """the plan's continuation rule (design s.2.2 step 4), counted per airline: an observed departure whose arrival was not
    seen gets an inferred arrival unless it is before 11:00 local; an observed arrival whose departure was not seen gets an
    inferred departure unless it is after 19:00 local; two consecutive same-role movements get one between them."""
    by = {}
    for m in M:
        by.setdefault(m['r'], []).append(m)
    cont = {}
    for L in by.values():
        L.sort(key=lambda m: m['t_sha'])
        a = L[0]['airline']
        n = 0
        if L[0]['role'] == 'dep' and local_hour(L[0]['t_sha'], w0) >= 11:
            n += 1
        for x, y in zip(L, L[1:]):
            if x['role'] == y['role']:
                n += 1
        if L[-1]['role'] == 'arr' and local_hour(L[-1]['t_sha'], w0) < 19 and local_hour(L[-1]['t_sha'], w0) >= 4:
            n += 1
        cont[a] = cont.get(a, 0) + n
    return cont


def turn_pairs(days):
    g = []
    for D in days.values():
        by = {}
        for m in D['M']:
            by.setdefault(m['r'], []).append(m)
        for L in by.values():
            L.sort(key=lambda m: m['t_sha'])
            for x, y in zip(L, L[1:]):
                if x['role'] == 'arr' and y['role'] == 'dep' and y['t_sha'] - x['t_sha'] <= 6 * 3600:
                    g.append((y['t_sha'] - x['t_sha']) / 60.0)
    return g


def quantile(v, q):
    v = sorted(v)
    k = (len(v) - 1) * q
    f = math.floor(k)
    c = min(len(v) - 1, f + 1)
    return v[f] + (v[c] - v[f]) * (k - f)


def merge_cells(counts_by_airline, group_of):
    """cells < MIN_CELL -> 'other'; the merged cells pooled per group ('mainland' / 'foreign'); pooled cells that stay
    < MIN_CELL folded into the pool's most common type of their family (else of the pool)."""
    mix, pool, group_tot = {}, {}, {}
    for a, c in counts_by_airline.items():
        for t, n in c.items():
            gt = group_tot.setdefault(group_of(a), {})
            gt[t] = gt.get(t, 0) + n
    for a in sorted(counts_by_airline):
        c = counts_by_airline[a]
        keep = {t: n for t, n in c.items() if n >= MIN_CELL}
        other = sum(n for t, n in c.items() if n < MIN_CELL)
        for t, n in c.items():
            if n < MIN_CELL:
                pool.setdefault(group_of(a), {}).setdefault(t, 0)
                pool[group_of(a)][t] += n
        if other:
            keep['other'] = other
        mix[a] = dict(sorted(keep.items()))
    out_pool = {}
    for g, c in sorted(pool.items()):
        big = {t: n for t, n in c.items() if n >= MIN_CELL}
        small = {t: n for t, n in c.items() if n < MIN_CELL}
        gt = group_tot[g]
        for t, n in sorted(small.items()):
            # the group's most common type of the same family (all of the group's counts), else of the whole group
            fam = [k for k in gt if family(k) == family(t) and gt[k] >= MIN_CELL]
            tgt = max(fam, key=lambda k: (gt[k], k)) if fam else max(gt, key=lambda k: (gt[k], k))
            big[tgt] = big.get(tgt, 0) + n
        while len(big) > 1 and min(big.values()) < MIN_CELL:      # a pool too small to split: smallest into largest
            lo = min(big, key=lambda k: (big[k], k))
            n = big.pop(lo)
            hi = max(big, key=lambda k: (big[k], k))
            big[hi] += n
        out_pool[g] = dict(sorted(big.items()))
    return mix, out_pool


# ------------------------------------------------------------------------------------------------ published (tier 3)
def hhmm_on(date, hhmm, tz_h=8):
    y, mo, d = [int(x) for x in date.split('-')]
    h, mi = int(hhmm[:2]), int(hhmm[-2:])
    return int(dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone(dt.timedelta(hours=tz_h))).timestamp() * 1000)


def published_rows(params):
    """SHA rows of the open HKG and TSA flight information -> [{flight, codeshares, airline, role, far, tFar, tFarAct, day,
    tSha, tShaAct, type, typeSrc}]; SHA runway time = far-end time -/+ far taxi -/+ air time (inf)."""
    air = params['airTimeS']
    taxi = params['farTaxiS']
    rows, dropped = [], []
    hk = os.path.join(REFS, 'schedules_open', 'hkia')
    for f, arrival in (('hkia_2026-11-13_arrival-false.json', False), ('hkia_2026-11-13_arrival-true.json', True)):
        for blk in json.load(open(os.path.join(hk, f))):
            for r in blk['list']:
                ports = (r.get('origin') if arrival else r.get('destination')) or []
                if 'SHA' not in ports:
                    continue
                fl = [x['no'].replace(' ', '') for x in r['flight']]
                t_s = hhmm_on(blk['date'], r['time'])
                act = None
                m = re.search(r'(\d{2}):(\d{2})(?: \((\d{2})/(\d{2})/(\d{4})\))?', r.get('status') or '')
                if m and re.match(r'^(Dep|At gate|Arrived)', r.get('status') or ''):
                    dd = f'{m.group(5)}-{m.group(4)}-{m.group(3)}' if m.group(3) else blk['date']
                    act = hhmm_on(dd, m.group(1) + m.group(2))
                if arrival:      # HKG arrival = SHA departure
                    sha = lambda t: t - (taxi['HKG']['in'] + air['HKG']) * 1000
                    role = 'dep'
                else:
                    sha = lambda t: t + (taxi['HKG']['out'] + air['HKG']) * 1000
                    role = 'arr'
                rows.append({'flight': fl[0], 'codeshares': fl[1:], 'airline': r['flight'][0]['airline'], 'role': role,
                             'far': 'HKG', 'farDate': blk['date'], 'tFar': iso_ms(t_s), 'tFarAct': iso_ms(act) if act else None,
                             'tSha': sha(t_s), 'tShaAct': sha(act) if act else None, 'type': None, 'typeSrc': 'not published (HKIA)',
                             'src': 'DATA.GOV.HK hkia flight information', 'farTimeKind': 'scheduled / actual off-block or on-block at HKG [obs]'})
    ts = os.path.join(REFS, 'schedules_open', 'tsa')
    for f, toTSA in (('tsa_intl_arr_2026-11-14.json', True), ('tsa_intl_dep_2026-11-14.json', False)):
        L = [r for r in json.load(open(os.path.join(ts, f))) if (r['UpAirportCode'] == 'SHA' if toTSA else r['GoalAirportCode'] == 'SHA')]
        groups = {}
        for r in L:
            key = r['ExpectArrivalTime'] if toTSA else r['ExpectDepartureTime']
            groups.setdefault(key, []).append(r)
        for key, G in sorted(groups.items()):
            G.sort(key=lambda r: (r['Master'], r['AirLineIATA'] + r['AirLineNum']))
            op = G[0]
            if op['Master'] != '1':
                dropped.append('tsa row group without an operating (Master 1) row')
                continue
            date = '2026-' + op['AirFlyDate'][:2] + '-' + op['AirFlyDate'][2:]
            t_s = hhmm_on(date, key)
            done = ('已到' in op['AirFlyStatus']) if toTSA else ('已飛' in op['AirFlyStatus'])
            real = op['RealArrivalTime'] if toTSA else op['RealDepartureTime']
            act = hhmm_on(date, real) if done and real else None
            tp = (op['AirPlaneType'] or '').split('/')[0].strip()
            icao = IATA_TYPE.get(tp)
            if toTSA:
                sha = lambda t: t - (taxi['TSA']['in'] + air['TSA']) * 1000
                role = 'dep'
            else:
                sha = lambda t: t + (taxi['TSA']['out'] + air['TSA']) * 1000
                role = 'arr'
            rows.append({'flight': op['AirLineIATA'] + op['AirLineNum'],
                         'codeshares': [r['AirLineIATA'] + r['AirLineNum'] for r in G[1:]], 'airline': op['AirLineCode'],
                         'role': role, 'far': 'TSA', 'farDate': date, 'tFar': iso_ms(t_s), 'tFarAct': iso_ms(act) if act else None,
                         'tSha': sha(t_s), 'tShaAct': sha(act) if act else None, 'type': icao,
                         'typeSrc': (f'TSA AirPlaneType "{op["AirPlaneType"]}", first listed [obs]' if icao else 'not published (TSA)'),
                         'src': 'data.gov.tw TSA international flight information', 'farTimeKind': 'scheduled / actual arrival or departure at TSA [obs]'})
    out, outside = [], []
    for r in rows:
        r['tSha'] = int(round(r['tSha'] / 60000.0)) * 60000          # whole minutes (inferred anyway)
        if r['tShaAct'] is not None:
            r['tShaAct'] = int(round(r['tShaAct'] / 60000.0)) * 60000
        r['day'] = op_day(r['tSha'])
        if r['day'] != r['farDate']:
            outside.append(r)          # Q1b: shown on its own date only
            continue
        out.append(r)
    out.sort(key=lambda r: (r['far'], r['tSha'], r['flight']))
    hkg = [r for r in out if r['far'] == 'HKG']
    tsa = [r for r in out if r['far'] == 'TSA']
    return hkg, tsa, {'outside_own_date': len(outside), 'dropped': len(dropped),
                      'outside_note': 'rows whose inferred SHA time falls on another SHA operating day than the published far-end date are not used (owner default Q1b: own date only)'}


# ------------------------------------------------------------------------------------------------ NOTAM effects
def notam_records():
    p = os.path.join(REFS, 'notam', 'zsss_notams_2026-11.json')
    d = json.load(open(p))
    keep = {'F4548/26', 'F4549/26', 'F4550/26', 'F4551/26', 'F4552/26', 'F4313/26', 'F4301/26', 'F4275/26', 'F4276/26'}
    out = []
    for e in d['sim']:
        if e['notam'] not in keep:
            continue
        f = dt.datetime.fromisoformat(e['from_utc'].replace('Z', '+00:00'))
        to = dt.datetime.fromisoformat(e['to_utc'].replace('Z', '+00:00'))
        wins = []
        if e.get('daily_utc'):
            a, b = e['daily_utc']
            day = f.replace(hour=0, minute=0)
            while day <= to:
                s = day.replace(hour=int(a[:2]), minute=int(a[2:]))
                t = day.replace(hour=int(b[:2]), minute=int(b[2:]))
                if t <= s:
                    t += dt.timedelta(days=1)
                s, t = max(s, f), min(t, to)
                if t > s:
                    wins.append([int(s.timestamp() * 1000), int(t.timestamp() * 1000)])
                day += dt.timedelta(days=1)
        else:
            wins.append([int(f.timestamp() * 1000), int(to.timestamp() * 1000)])
        kind = e['effect']
        if kind in ('rwy_closed', 'rwy_no_landing'):
            target = {'runway': e['target'], 'crossingVia': e.get('crossing_via') or None, 'except': e.get('except') or None}
        elif kind == 'twy_closed':
            target = {'routesVariant': e['notam'][:5] if e['notam'] == 'F4552/26' else None,
                      'note': 'taxi links closed in the window (the route table variant data/sha_routes.json, package P3-B)'
                      if e['notam'] == 'F4552/26' else 'taxi links closed in the window (no route table variant: before the replay days)'}
        elif kind == 'stand_closed':
            target = {'stand': e['target']}
        elif kind == 'rapid_exit_distances':
            target = {'exits': e['target']}
        elif kind == 'wip_area':
            target = {'effect': 'works area north of the RWY 18L DTHR; no effect on movements (design s.2.5)'}
        else:
            target = None
        out.append({'id': e['notam'], 'kind': kind, 'target': target, 'from': e['from_utc'], 'to': e['to_utc'],
                    'daily': e.get('daily_utc'), 'windows': wins, 'src': 'obs'})
    out.sort(key=lambda r: r['id'])
    return out, d['in_force_at'], p


# ------------------------------------------------------------------------------------------------ build
def taxi_estimates():
    """median taxi lengths per side from the route table (P3-B data/sha_routes.json) -> taxi-in / taxi-out estimates (s)
    [inf: average taxi speed and fixed times]. Falls back to the design medians if the table is missing."""
    p = os.path.join(ROOT, 'data', 'sha_routes.json')
    stands = json.load(open(os.path.join(ROOT, 'data', 'sha_stands.json')))['stands']
    side = {s['name']: ('T1' if s['area'].startswith(('T1', 'east')) else 'BIZ' if s['area'].startswith('business') else 'T2') for s in stands}
    V, ARR_FIX, DEP_FIX = 7.0, 60, 390      # m/s average, s (lead-in + stop), s (push 120 + start-up 90 + queue / line-up 180) [inf]
    med = {}
    if os.path.exists(p):
        R = json.load(open(p))
        names = R['stands']

        def lens(keys, sd):
            v = []
            for k in keys:
                g = R['groups'].get(k)
                if not g:
                    continue
                for i, n in enumerate(names):
                    x = g['lenN'][i]
                    if side.get(n) == sd and x is not None and x > 0:
                        v.append(x / 100.0)
            return statistics.median(v) if v else None
        med = {'T1': {'dep': lens(['dep|18R|full|base', 'dep|36L|full|base'], 'T1'),
                      'arr': lens(['arr|18L:A3|n|base', 'arr|36R:A2|n|base'], 'T1')},
               'T2': {'dep': lens(['dep|18R|full|base', 'dep|36L|full|base'], 'T2'),
                      'arr': lens(['arr|18L:B4|n|base', 'arr|36R:B3|n|base'], 'T2')},
               'BIZ': {'dep': lens(['dep|18R|full|base', 'dep|36L|full|base'], 'BIZ'),
                       'arr': lens(['arr|18L:A3|n|base', 'arr|36R:A2|n|base'], 'BIZ')}}
    fb = {'T1': {'dep': 2500, 'arr': 1550}, 'T2': {'dep': 2261, 'arr': 4800}, 'BIZ': {'dep': 2300, 'arr': 1700}}
    out = {}
    for sd in ('T1', 'T2', 'BIZ'):
        dm = (med.get(sd) or {}).get('dep') or fb[sd]['dep']
        am = (med.get(sd) or {}).get('arr') or fb[sd]['arr']
        out[sd] = {'inS': int(round(am / V + ARR_FIX)), 'outS': int(round(dm / V + DEP_FIX)), 'medArrM': int(round(am)), 'medDepM': int(round(dm))}
    return out, {'avgTaxiMs': V, 'arrFixS': ARR_FIX, 'depFixS': DEP_FIX, 'routeTable': rel(p) if os.path.exists(p) else None,
                 'basis': 'median route length per side (route table: departures to 18R / 36L, arrivals from the first rapid exit on '
                          'the side) / 7 m/s average (design s.4.4 caps) + 60 s (arrival lead-in) or 390 s (push 120 + start-up 90 + '
                          'queue / line-up 180) [inf]',
                 'src': 'inf'}, (sha16(p) if os.path.exists(p) else None)


def build():
    stats = json.load(open(os.path.join(ROOT, 'docs', 'phase1', 'observed_elsewhere_stats.json')))
    hourly = json.load(open(os.path.join(ROOT, 'docs', 'phase1', 'sources_sim_hourly.json')))
    AL = airlines_table()
    days = load_observed()
    sd_stats = {d['day']: d for d in stats['days']}

    # ---- hourly profile (shape) and totals
    prof = hourly['identified_by_local_hour']
    profile = {'arr': prof['arr'], 'dep': prof['dep'], 'hour': 'local hour (UTC+8) 0..23', 'src': 'inf',
               'basis': 'shape of the identified observed-elsewhere movements per local hour, mean of 2026-11-10 / 12 '
                        '(docs/phase1/sources_sim_hourly.json identified_by_local_hour, aggregates); each role is scaled to half '
                        'the daily total (design s.2.2 step 1: the identified shape has more arrivals than departures, a '
                        'coverage artefact) [inf]'}
    totals = [
        {'from': '2026-01-01', 'to': '2026-10-24', 'perDay': 783.4, 'src': 'obs',
         'basis': 'CAAC airport statistics Jan-Sep 2026: 783.4 movements a day at SHA (docs/PLAN.md s.1, field.md)'},
        {'from': '2026-10-25', 'to': '2027-03-27', 'perDay': 802, 'src': 'sec',
         'basis': 'Winter 2026/27 season plan, 802 movements a day (secondary: news report, docs/PLAN.md s.1); the season '
                  'starts on the last Sunday of October (IATA)'},
    ]

    # ---- airline weights (design s.2.1 rev. 2, review M9)
    db = {}
    for d in stats['days']:
        for a, n in d['db_sha_callsigns_by_airline'].items():
            db[a] = max(db.get(a, 0), n)
    comp_by_day, ident_by_day = {}, {}
    for day in OBS_DAYS:
        S = sd_stats[day]
        ident = {}
        for m in days[day]['M']:
            ident[m['airline']] = ident.get(m['airline'], 0) + 1
        ident_by_day[day] = ident
        res = {a: max(0, S['db_sha_callsigns_by_airline'].get(a, 0) - S['distinct_callsigns_by_airline'].get(a, 0))
               for a in sorted(set(S['db_sha_callsigns_by_airline']) | set(S['distinct_callsigns_by_airline']))}
        tot = sum(res.values())
        comp_by_day[day] = {a: round(v / tot, 5) for a, v in sorted(res.items()) if v > 0}
    comp = {}
    for day in OBS_DAYS:
        for a, w in comp_by_day[day].items():
            comp[a] = comp.get(a, 0) + w / len(OBS_DAYS)
    comp = {a: round(w, 5) for a, w in sorted(comp.items())}

    # ---- type mix (aggregates, merged cells)
    counts = {}
    for day in OBS_DAYS:
        for m in days[day]['M']:
            c = counts.setdefault(m['airline'], {})
            c[m['t']] = c.get(m['t'], 0) + 1
    group_of = lambda a: 'foreign' if a in FOREIGN else 'mainland'
    mix_all, pool = merge_cells(counts, group_of)
    mix_comp = {}
    for a, c in mix_all.items():
        mix_comp[a] = {t: round(n * (0.5 if t in WIDE else 1.0), 1) for t, n in c.items()}
    pool_comp = {g: {t: round(n * (0.5 if t in WIDE else 1.0), 1) for t, n in c.items()} for g, c in pool.items()}

    # ---- full-day expectation of an observed-day plan: identified + continuations + complement x fill
    N = {'2026-11-10': 802, '2026-11-12': 802}
    full_share, full_mix = {}, {}
    cont_by_day = {}
    for day in OBS_DAYS:
        ident = ident_by_day[day]
        cont = continuations(days[day]['M'], days[day]['w0'])
        cont_by_day[day] = sum(cont.values())
        fill = max(0, N[day] - sum(ident.values()) - sum(cont.values()))
        q = largest_remainder(comp_by_day[day], fill)
        tot = {}
        for a in set(ident) | set(cont) | set(q):
            tot[a] = ident.get(a, 0) + cont.get(a, 0) + q.get(a, 0)
        T = sum(tot.values())
        for a, v in tot.items():
            full_share[a] = full_share.get(a, 0) + v / T / len(OBS_DAYS)
            # type mix of that airline in the full plan: observed (identified + continuations ~ identified mix) + fill (complement mix)
            fm = full_mix.setdefault(a, {})
            obs_n = ident.get(a, 0) + cont.get(a, 0)
            m_all = mix_all.get(a) or {'other': 1}
            m_c = mix_comp.get(a) or {'other': 1}
            sa, sc = sum(m_all.values()), sum(m_c.values())
            for t, n in m_all.items():
                fm[t] = fm.get(t, 0) + obs_n * n / sa
            for t, n in m_c.items():
                fm[t] = fm.get(t, 0) + q.get(a, 0) * n / sc
    full_share = {a: round(v, 5) for a, v in sorted(full_share.items()) if v > 0}
    full_mix = {a: {t: round(n, 1) for t, n in sorted(c.items()) if n > 0} for a, c in sorted(full_mix.items())}
    pool_full = pool

    # ---- international / HMT
    intl_target = 0.0633
    foreign_share = sum(w for a, w in full_share.items() if a in FOREIGN)
    main_share = sum(w for a, w in full_share.items() if a in INTL_MAINLAND)
    s_main = max(0.0, (intl_target - foreign_share) / main_share) if main_share else 0.0
    obs_intl = {}
    for day in OBS_DAYS:
        for m in days[day]['M']:
            if m['airline'] in INTL_MAINLAND and is_intl(m):
                obs_intl[m['airline']] = obs_intl.get(m['airline'], 0) + 1
    intl = {'share': {**{a: 1.0 for a in FOREIGN}, **{a: round(s_main, 4) for a in INTL_MAINLAND}}, 'src': 'inf',
            'target': intl_target,
            'basis': 'CAAC 2025: international 6,978 + HMT 10,905 of 282,692 movements = 6.3 % (docs/PLAN.md s.1); carriers based '
                     'outside the mainland are international / HMT by definition; MU, FM and CA get the common share that makes the '
                     'full-day expectation 6.3 % (design s.2.3) [inf]',
            'observedMainlandIntl2Days': sum(obs_intl.values())}

    # ---- turnaround
    g = turn_pairs(days)
    turnaround = {'p10': round(quantile(g, 0.1) * 60), 'p50': round(quantile(g, 0.5) * 60), 'p90': round(quantile(g, 0.9) * 60),
                  'minNarrowS': 35 * 60, 'minWideS': 60 * 60, 'maxPairS': 6 * 3600, 'nPairs': len(g), 'src': 'inf',
                  'basis': 'same-airframe arrival -> departure gaps <= 6 h (runway times) of the observed-elsewhere movements of '
                           '2026-11-10 / 12 (aggregate quantiles, seconds), applied as runway-time gaps (verification fix round 1, '
                           'F5); minimum turnaround narrow 35 min, wide 60 min (ground time, on-block to off-block) and the 6 h '
                           'pairing limit are design choices (design s.2.1, s.2.2 step 6) [inf]'}

    taxi, taxi_basis, routes16 = taxi_estimates()
    params = {
        'planVersion': 1, 'observedDays': list(OBS_DAYS), 'dayStartLocalH': 4, 'utcOffsetH': 8,
        'nightNoSched': {'fromLocalH': 1, 'toLocalH': 6, 'basis': 'no scheduled movement 01:00-05:59 local (caacnews 2023: no flights scheduled at night; PLAN s.6b Q10 e; AIP (mirror) AD 2.3) [inf]'},
        'bufferS': 600, 'bufferBasis': 'stand buffer [on-block - 10 min, off-block + 10 min] (design s.2.4) [inf]',
        'bizPerDay': 4, 'bizTypes': ['CL60', 'C68A', 'CL35', 'G280'],
        'bizBasis': 'business-aviation movements a day on the business apron, generic business jets (design s.2.3, 4 a day [inf]); types from js/aircraft/fit.js BIZ that fit the business stands (their span_max 22.4-26.1 m)',
        'earlyParkLocalH': 11, 'lateStayLocalH': 19,
        'contBasis': 'continuations of observed airframes (design s.2.2 step 4): an unseen arrival before an observed departure '
                     'before 11:00 local = parked from t0; an unseen departure after an observed arrival after 19:00 local = '
                     'stays to t1; otherwise an inferred movement at the drawn turnaround [inf]',
        'nightStopCapShare': 0.85, 'pairWindowS': 15 * 60,
        'serviceTurnAfterOnS': 30 * 60, 'serviceTurnBeforeOffS': 45 * 60, 'coldAfterS': 100 * 60,
        'serviceBasis': 'service windows: turn from on-block to on-block + 30 min and from off-block - 45 min; a ground time '
                        'longer than 100 min is cold in between (design s.4.3) [inf]',
        'taxi': taxi, 'taxiBasis': taxi_basis,
        'airTimeS': {k: int(round(statistics.mean(d['calibration']['air_time_fit_all']['a_s'] for d in stats['days'])
                                  + statistics.mean(d['calibration']['air_time_fit_all']['b_s_per_km'] for d in stats['days']) * gc_km('ZSSS', ap)))
                     for k, ap in (('HKG', 'VHHH'), ('TSA', 'RCSS'))},
        'airTimeBasis': 'air time = a + b x great-circle km from the observed-elsewhere calibration (observed_elsewhere_stats.json '
                        'days[].calibration.air_time_fit_all, mean of the two days: a 1,195 s, b 4.42 s/km, sigma ~414 s; '
                        'aggregate) [inf]',
        'farTaxiS': {'HKG': {'out': 15 * 60, 'in': 8 * 60}, 'TSA': {'out': 10 * 60, 'in': 5 * 60}},
        'farTaxiBasis': 'taxi time at the far end between its published off-block / on-block time and the runway [inf]',
        'standIns': {'C919': {'model': 'A320', 'spanM': 35.8, 'lenM': 38.9, 'note': '3D model: Airbus A320 stand-in (no C919 model until Phase 4)', 'src': 'COMAC C919 span 35.8 m, length 38.9 m [sec] (design s.2.3)'},
                     'AJ27': {'model': 'CRJ9', 'spanM': 27.3, 'lenM': 33.5, 'note': '3D model: Bombardier CRJ900 stand-in (no C909 model until Phase 4)', 'src': 'sha_stands.json class_ref.B (span 27.3 m, length 33.5 m) [sec]'},
                     'C909': {'model': 'CRJ9', 'spanM': 27.3, 'lenM': 33.5, 'note': '3D model: Bombardier CRJ900 stand-in (no C909 model until Phase 4)', 'src': 'as AJ27 [sec]'}},
        'refless': False,
        'reflessBasis': 'the 4 OSM positions without a ref (design s.2.4 overflow 2) are not used: they have no route in the route '
                        'table and no gate object [inf; deviation documented in docs/phase3/plan.md]',
        'crossSideRemoteFirst': True,
        'remoteFirstPermille': 50,
        'remoteFirstBasis': 'share (per mille) of ground visits planned on a remote stand first although a contact stand may be '
                            'free (airline, handling and bus-gate choices are not modelled); calibrated together with longRemoteS so '
                            'that the contact share is near the caacnews 2023 bridge rate of about 72 % (76.5 % in a peak week; '
                            'field.md s.3.1); verification fix round 1: 110 -> 50 with the runway-gap turnarounds [inf]',
        'longRemoteS': 4 * 3600,
        'longRemoteBasis': 'a ground visit occupying more than 4 h of the active day (06:00-01:00 local) tries its side\'s remote '
                           'stands first, keeping contact stands for turns (no towing is modelled, design s.2.4 towLong off); '
                           'verification fix round 1 [inf]',
        'pairPick': 'nearest',
        'rushCapPermille': 50,
        'pairBasis': 'rotation pairing (design s.2.2 step 6, verification fix round 1 F5): each pool arrival draws a runway-time '
                     'gap from the turnaround quantiles (at least taxi-in + minimum ground time + taxi-out); a departure takes '
                     'the ready airframe whose gap is nearest its drawn gap ("nearest"); without one, at most 50 per mille of '
                     'the fill departures take the not-yet-ready airframe with the smallest shortfall that has the minimum turn '
                     '(rushed, counted); otherwise the departure is a night-stopper [inf]',
    }
    hkg, tsa, pubinfo = published_rows(params)
    nrec, notam_at, notam_path = notam_records()

    def name_of(a):
        v = AL.get(a)
        return (v.split('|')[0] if v else a), ((v.split('|')[1] if v and '|' in v else None))
    airl = sorted(set(comp) | set(full_share) | {r['airline'] for r in hkg + tsa})
    airlines = {a: {'name': name_of(a)[0], 'iata': name_of(a)[1], 'group': group_of(a),
                    'terminal': 'T1' if a in T1_AIRLINES or a in FOREIGN else 'T2'} for a in airl}
    # names as the UI shows them (lookup.js has the registered names; short trading names here [inf])
    SHORT = {'CES': 'China Eastern', 'CSH': 'Shanghai Airlines', 'CQH': 'Spring Airlines', 'DKH': 'Juneyao Air', 'CCA': 'Air China',
             'CSN': 'China Southern', 'CXA': 'XiamenAir', 'CSZ': 'Shenzhen Airlines', 'CHH': 'Hainan Airlines', 'CDG': 'Shandong Airlines',
             'CPA': 'Cathay Pacific', 'TBA': 'Tibet Airlines', 'CUA': 'China United', 'KAL': 'Korean Air', 'GCR': 'Tianjin Airlines',
             'HBH': 'Hebei Airlines', 'AMU': 'Air Macau', 'JAL': 'Japan Airlines', 'UEA': 'Chengdu Airlines', 'ANA': 'All Nippon Airways',
             'CAL': 'China Airlines', 'EVA': 'EVA Air', 'CRK': 'Hong Kong Airlines', 'AAR': 'Asiana Airlines', 'YZR': 'Suparna Airlines'}
    for a, v in airlines.items():
        v['short'] = SHORT.get(a, v['name'])

    inputs = {
        'v': 1, 'built': BUILT, 'src': 'inf',
        'what': 'Committed inputs of the SHA Live 3D day plan (Phase 3): hourly profile, daily totals, airline weights and type '
                'mix (aggregates, cells < 3 merged), turnarounds, terminal rules, taxi estimates, delays, the published HKG / TSA '
                'rows of their own dates, NOTAM effect records. No observed-elsewhere identity, no per-flight time.',
        'generator': 'tools/sim/build_sim_inputs.py',
        'licence': {
            'aggregates': 'Aggregates derived from adsb.lol globe_history archives: ODbL 1.0. Contains information from ADSB.lol '
                          '(https://adsb.lol), made available under the ODbL. Routes: Virtual Radar Server standing data (CC0 1.0); '
                          'aircraft data: Mictronics aircraft database (ODC-By 1.0).',
            'published': 'Flight information: Airport Authority Hong Kong, via DATA.GOV.HK (DATA.GOV.HK Terms and Conditions of '
                         'Use); Flight information: Taipei Songshan Airport, Civil Aeronautics Administration (Taiwan), Open '
                         'Government Data License v1.0. Published schedule facts, not observed-elsewhere data.',
            'notams': 'CAAC eAIP NOTAM Summary (in force ' + notam_at + '): ids, windows and targets only (short cited facts, OD3).',
            'facts': 'CAAC airport statistics (totals), SAA airline directory (terminal rules): facts.',
        },
        'attribution': ['Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL',
                        'Flight information: Airport Authority Hong Kong, via DATA.GOV.HK',
                        'Flight information: Taipei Songshan Airport, CAA Taiwan, OGDL v1.0',
                        'NOTAM effects: CAAC eAIP NOTAM Summary, in force ' + notam_at + '; later NOTAMs not known'],
        'profile': profile, 'totals': totals,
        'weights': {'complement': comp, 'fullDay': full_share, 'complementByDay': comp_by_day, 'src': 'inf',
                    'basis': 'complement (observed days): share of (route-DB SHA callsigns - identified distinct callsigns) per airline '
                             '(observed_elsewhere_stats.json, aggregates), mean of the two days; fullDay (every other day): the '
                             'expected airline shares of a whole observed-day plan = identified + continuations + complement x fill, '
                             'mean of the two days (design s.2.1, review M9) [inf]'},
        'typeMix': {'complement': mix_comp, 'fullDay': full_mix, 'pool': {'complement': pool_comp, 'fullDay': pool_full}, 'src': 'inf',
                    'unit': 'relative weights (two-day counts; complement: wide-bodies x 0.5)',
                    'basis': 'ICAO type per airline of the identified movements of both observed days, cells < 3 merged into "other", '
                             'which draws from the pool of merged cells of the airline group (mainland / foreign; pooled cells < 3 '
                             'folded into the group\'s most common type of the same family); the wide-body share '
                             'is halved only in complement (the blind routes\' narrow-body bias, observed_elsewhere.md s.5.4); fullDay '
                             'mixes identified + continuations (identified mix) + fill (complement mix) (design s.2.1) [inf]'},
        'families': {t: family(t) for t in sorted({t for c in counts.values() for t in c} | {'AJ27', 'C909', 'CRJ9', 'B763', 'B788', 'A35K', 'B39M', 'A19N'})},
        'airlines': airlines,
        'turnaround': turnaround,
        'terminals': {'T1': list(T1_AIRLINES), 'intl': list(FOREIGN), 'intlMainland': list(INTL_MAINLAND),
                      'rule': 'T1 serves 9C, NS and MF (domestic) and every international or HMT flight; T2 serves all other '
                              'domestic flights (SAA airline directory, field.md s.2.2 [obs]; reading [inf])', 'src': 'inf'},
        'intl': intl,
        'delays': {'bands': [{'p': 0.80, 'minS': -600, 'maxS': 600}, {'p': 0.15, 'minS': 900, 'maxS': 3600}, {'p': 0.05, 'minS': 3600, 'maxS': 7200}],
                   'tiers': ['pub', 'inf'], 'src': 'inf',
                   'basis': '80 % within +-10 min, 15 % +15-60 min, 5 % +60-120 min (CAAC on-time statistics not read) for tier 3 rows '
                            'without a published actual time and tier 4 fill; never for tier 2 or continuations (design s.2.2 step 8, '
                            'review M10) [inf]'},
        'published': {'hkg': hkg, 'tsa': tsa, 'info': pubinfo, 'src': 'obs (far-end schedule); SHA times inf',
                      'what': 'published schedule facts, not observed-elsewhere data: flight numbers and far-end times of the open '
                              'Hong Kong (13 Nov 2026) and Taipei Songshan (14 Nov 2026) flight information; shown on their own date '
                              'only, labelled "published schedule", no registration; type only where TSA publishes it (owner default Q1b)',
                      'attribution': {'HKG': 'Flight information: Airport Authority Hong Kong, via DATA.GOV.HK',
                                      'TSA': 'Flight information: Taipei Songshan Airport, CAA Taiwan, OGDL v1.0'}},
        'notams': nrec, 'notamInForce': notam_at, 'notamNote': 'CAAC eAIP NOTAM Summary in force ' + notam_at + '; later NOTAMs not known',
        'params': params,
        'checks': {'identifiedPerDay': {d: len(days[d]['M']) for d in OBS_DAYS}, 'continuationsPerDay': cont_by_day,
                   'mergedCellRule': f'every per-airline x type count < {MIN_CELL} merged'},
    }
    ins = {
        'docs/phase1/observed_elsewhere_stats.json': sha16(os.path.join(ROOT, 'docs', 'phase1', 'observed_elsewhere_stats.json')),
        'docs/phase1/sources_sim_hourly.json': sha16(os.path.join(ROOT, 'docs', 'phase1', 'sources_sim_hourly.json')),
        'data/lookup.js': sha16(os.path.join(ROOT, 'data', 'lookup.js')),
        'data/sha_stands.json': sha16(os.path.join(ROOT, 'data', 'sha_stands.json')),
        'refs/cache/notam/zsss_notams_2026-11.json (local)': sha16(notam_path),
    }
    if routes16:
        ins['data/sha_routes.json'] = routes16
    for d in OBS_DAYS:                 # verification fix round 2, F20: no fingerprint of a local identity table is committed
        ins[f'refs/cache/observed_elsewhere/sha_observed_{d}.json (local)'] = WITHHELD
    for sub in ('hkia', 'tsa'):
        for f in sorted(os.listdir(os.path.join(REFS, 'schedules_open', sub))):
            if f.endswith('.json') and f != 'SOURCES.json':
                ins[f'refs/cache/schedules_open/{sub}/{f}'] = sha16(os.path.join(REFS, 'schedules_open', sub, f))
    inputs['inputs_sha256_16'] = ins
    return inputs


def sources(inputs):
    obs_src = json.load(open(os.path.join(OBS_DIR, 'SOURCES.json')))
    hk = json.load(open(os.path.join(REFS, 'schedules_open', 'hkia', 'SOURCES.json')))
    ts = json.load(open(os.path.join(REFS, 'schedules_open', 'tsa', 'SOURCES.json')))
    nt = json.load(open(os.path.join(REFS, 'notam', 'SOURCES.json')))
    files = []
    for d in OBS_DAYS:
        f = f'sha_observed_{d}.json'
        files.append({'path': 'refs/cache/observed_elsewhere/' + f, 'local_only': True, 'sha256': WITHHELD,
                      'url': obs_src['url'], 'retrieved': obs_src['retrieved'], 'licence': obs_src['licence'],
                      'licence_quote': obs_src['licence_quote'], 'used_for': 'aggregates only: type mix, intl counts, turnaround quantiles, continuation counts'})
    for sub, S in (('hkia', hk), ('tsa', ts)):
        for f, v in sorted(S['files'].items()):
            files.append({'path': f'refs/cache/schedules_open/{sub}/{f}', 'local_only': False, 'sha256': v['sha256'], 'url': v['url'],
                          'retrieved': S['downloaded_utc'], 'licence': S['licence'], 'licence_url': S['licence_url'],
                          'licence_quote': S['licence_quote'], 'attribution': S['attribution'], 'redistributable': S['redistributable'],
                          'used_for': 'section published (tier 3 rows of their own date)'})
    files.append({'path': 'refs/cache/notam/zsss_notams_2026-11.json', 'local_only': True,
                  'sha256': sha256(os.path.join(REFS, 'notam', 'zsss_notams_2026-11.json')),
                  'url': nt.get('url') or nt.get('source') or 'eAIP NOTAM Summary (CAAC)', 'retrieved': nt.get('downloaded_utc') or nt.get('date_checked'),
                  'licence': 'none published (treated as all rights reserved; OD3 short facts only)',
                  'licence_quote': nt.get('terms_quote') or nt.get('terms') or 'none published', 'used_for': 'notams: ids, windows, targets'})
    for p, use, lic, url in (
            ('docs/phase1/observed_elsewhere_stats.json', 'committed aggregates: route-DB and identified callsigns per airline, air-time calibration', 'ODbL 1.0 (adsb.lol derived), CC0 (VRS), ODC-By (Mictronics)', 'https://github.com/adsblol/globe_history_2026/releases'),
            ('docs/phase1/sources_sim_hourly.json', 'hourly profile shape (aggregates)', 'ODbL 1.0 (adsb.lol derived aggregates)', 'https://github.com/adsblol/globe_history_2026/releases'),
            ('data/lookup.js', 'airline names and IATA designators', 'CC0 1.0 (Virtual Radar Server standing data, forked from sfo3d)', 'https://github.com/vradarserver/standing-data'),
            ('data/sha_routes.json', 'taxi length medians per side (P3-B route table)', 'ODbL 1.0 (derived from OpenStreetMap)', None),
            ('data/sha_stands.json', 'stand sides (taxi estimates)', 'ODbL 1.0 (derived from OpenStreetMap)', None)):
        fp = os.path.join(ROOT, p)
        if os.path.exists(fp):
            files.append({'path': p, 'local_only': False, 'sha256': sha256(fp), 'url': url, 'licence': lic, 'used_for': use})
    return {
        'what': 'Sources of data/sha_sim_inputs.js / .json (Phase 3 day plan inputs, package P3-A)',
        'generator': 'tools/sim/build_sim_inputs.py', 'built': inputs['built'],
        'sections': {
            'profile, totals, weights, typeMix, turnaround, intl, checks': 'aggregates of the observed-elsewhere data (ODbL 1.0) and '
                'published facts; every count cell < 3 merged; no identity, no per-flight time',
            'published': 'published schedule facts, not observed-elsewhere data (HKG: DATA.GOV.HK terms; TSA: OGDL v1.0); the only '
                         'section where flight numbers occur; allow-listed by tools/sim/audit_identity.py only for flight numbers '
                         'that occur in refs/cache/schedules_open/',
            'notams': 'NOTAM effect records (ids, windows, targets) from the CAAC eAIP NOTAM Summary (OD3 short facts)',
            'params': 'design parameters [inf], each with its basis',
        },
        'attribution': inputs['attribution'],
        'files': files,
    }


def render(inputs):
    js = ('// generated by tools/sim/build_sim_inputs.py - do not edit. Aggregates (ODbL 1.0: contains information from ADSB.lol, '
          'https://adsb.lol) + published HKG (DATA.GOV.HK) / TSA (OGDL v1.0) rows + NOTAM effect records. No identities.\n'
          'window.SHA_SIM_INPUTS = ' + json.dumps(inputs, ensure_ascii=False, separators=(',', ':'), sort_keys=False) + ';\n')
    return js, json.dumps(inputs, ensure_ascii=False, indent=1) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    inputs = build()
    js, js_json = render(inputs)
    src = json.dumps(sources(inputs), ensure_ascii=False, indent=1) + '\n'
    if a.check:
        bad = [p for p, s in ((OUT_JS, js), (OUT_JSON, js_json), (OUT_SRC, src)) if not os.path.exists(p) or open(p, encoding='utf-8').read() != s]
        print('check:', 'identical' if not bad else 'DIFFERS: ' + ', '.join(rel(p) for p in bad))
        sys.exit(1 if bad else 0)
    open(OUT_JS, 'w', encoding='utf-8').write(js)
    open(OUT_JSON, 'w', encoding='utf-8').write(js_json)
    open(OUT_SRC, 'w', encoding='utf-8').write(src)
    P = inputs['published']
    print(f'{rel(OUT_JS)}: {len(js)} bytes; airlines {len(inputs["airlines"])}, complement {len(inputs["weights"]["complement"])}, '
          f'published HKG {len(P["hkg"])} + TSA {len(P["tsa"])} rows (outside own date {P["info"]["outside_own_date"]}), '
          f'NOTAM records {len(inputs["notams"])}; turnaround p10/p50/p90 '
          f'{inputs["turnaround"]["p10"] // 60}/{inputs["turnaround"]["p50"] // 60}/{inputs["turnaround"]["p90"] // 60} min; '
          f'intl share MU/FM/CA {inputs["intl"]["share"]["CES"]}; taxi {inputs["params"]["taxi"]}')


if __name__ == '__main__':
    main()
