"""Re-verify (Fix round 1) of B1. Independent re-count of the B1 local tables (re-verify of Fix round 1).

Usage: python3 -I rv_b1.py <observed_elsewhere dir> <ourairports airports.csv>
Prints aggregates; per-flight lines only to the terminal (never written to a file).
"""
import csv, json, math, sys, collections, statistics as st

D = sys.argv[1]
AP = {}
with open(sys.argv[2], newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['ident'] and len(r['ident']) == 4:
            try:
                AP[r['ident']] = (float(r['latitude_deg']), float(r['longitude_deg']))
            except ValueError:
                pass
SHA = (31.19785, 121.33629)
R = 6371.0088


def gc(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def brg(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def adiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def q(v, p):
    v = sorted(v)
    if not v:
        return None
    k = (len(v) - 1) * p
    i = int(k)
    return v[i] + (v[min(i + 1, len(v) - 1)] - v[i]) * (k - i)


FAM = {'A318': 'A320', 'A319': 'A320', 'A320': 'A320', 'A321': 'A320', 'A19N': 'A320', 'A20N': 'A320', 'A21N': 'A320',
       'B737': '737', 'B738': '737', 'B739': '737', 'B38M': '737', 'B39M': '737', 'C919': 'C919', 'AJ27': 'C909'}
WIDE = {'A332', 'A333', 'A339', 'A359', 'A35K', 'B788', 'B789', 'B78X', 'B772', 'B77W', 'B744', 'B748', 'A388'}

allid = []
for day in ('2026-11-10', '2026-11-12'):
    d = json.load(open(f'{D}/sha_observed_{day}.json'))
    m = d['movements']
    rows = list(csv.DictReader(open(f'{D}/sha_observed_{day}.csv', newline='', encoding='utf-8')))
    print(f'=== {day}: json {len(m)} rows, csv {len(rows)} rows')
    ident = [x for x in m if x['consistency'] in ('track_consistent', 'far_end_match')]
    withpick = [x for x in m if x['pick']]
    print(' identified (consistent):', len(ident), ' with method:', len(withpick),
          ' same set:', {x['uid'] for x in ident} == {x['uid'] for x in withpick})
    print(' csv with method:', sum(1 for r in rows if r['method']))
    roles = collections.Counter(x['role'] for x in ident)
    print(' arr/dep', roles['arr'], roles['dep'], ' share of 783.4: %.1f %%' % (100 * len(ident) / 783.4),
          ' of 802: %.1f %%' % (100 * len(ident) / 802))
    print(' consistency counts', dict(collections.Counter(x['consistency'] for x in m)))
    print(' distinct aircraft (icao)', len({x['icao'] for x in ident}), ' reg empty', sum(1 for x in ident if not x['r']),
          ' type empty', sum(1 for x in ident if not x['t']))
    dup = collections.Counter((x['cs'], x['role']) for x in ident)
    print(' duplicate callsign+role', sum(1 for v in dup.values() if v > 1))
    sig = [x['sigma_s'] / 60 for x in ident]
    print(' sigma min: P10 %.1f median %.1f P90 %.1f max %.1f' % (q(sig, .1), q(sig, .5), q(sig, .9), max(sig)))
    for thr in (5, 10, 15, 19, 20):
        print('   share sigma <= %d: %.1f %%' % (thr, 100 * sum(1 for s in sig if s <= thr + 1e-9) / len(sig)))
    print(' methods', dict(collections.Counter(x['pick'] for x in ident)))
    # M1 detail and method choice consistency
    m1 = [x for x in ident if x['pick'] == 'M1']
    print(' M1 far ends', dict(collections.Counter(x['far'] for x in m1)),
          ' M1 sigma (min)', sorted(round(x['sigma_s'] / 60, 1) for x in m1))
    bad_choice = 0
    for x in ident:
        e = x['est']
        if 'M1' in e and 'M2' in e:
            best = min(('M1', 'M2'), key=lambda k: e[k]['sigma_s'])
            if best != x['pick']:
                bad_choice += 1
        if x['sigma_s'] != e[x['pick']]['sigma_s']:
            bad_choice += 1
    n_both = sum(1 for x in ident if 'M1' in x['est'] and 'M2' in x['est'])
    print(' movements with both M1 and M2:', n_both, ' choice not the smaller sigma:', bad_choice)
    cn_m1 = collections.Counter()
    for x in ident:
        if 'M1' in x['est']:
            e1 = x['est']['M1']
            cn_m1[(e1.get('cn'), round(e1['sigma_s']))] += 1
    print(' M1 candidate sigma values (cn, s):', dict(cn_m1))
    m1_cn_pick = [x for x in m1 if x['est']['M1'].get('cn')]
    print(' M1 picks with Chinese far end:', len(m1_cn_pick))
    # Distance
    nk = [x['near_km'] for x in ident]
    print(' near_km P10 %.0f P25 %.0f med %.0f P75 %.0f P90 %.0f max %.0f; >900 %d; >1300 %d' % (
        q(nk, .1), q(nk, .25), q(nk, .5), q(nk, .75), q(nk, .9), max(nk), sum(1 for v in nk if v > 900),
        sum(1 for v in nk if v > 1300)))
    # Span check
    spans = []
    over4 = 0
    over_leg = 0
    for x in ident:
        t0 = x['segs'][0][0][0]
        t1 = x['segs'][-1][-1][0]
        span = t1 - t0
        spans.append(span)
        if span > 4 * 3600:
            over4 += 1
        if x.get('leg_air_s') and span > x['leg_air_s'] + 1800:
            over_leg += 1
    print(' span: max %.2f h, records > 4 h: %d, span > leg air + 30 min: %d' % (max(spans) / 3600, over4, over_leg))
    # Heading test (own): track at the fix nearest SHA vs bearing to/from SHA
    h90 = []
    for x in ident:
        if x['role'] == 'arr':
            fx = x['segs'][-1][-1]
            want = brg((fx[1], fx[2]), SHA)
        else:
            fx = x['segs'][0][0]
            want = (brg(SHA, (fx[1], fx[2])))
        trk = fx[5]
        if trk is None:
            continue
        off = adiff(trk, want)
        if off > 90:
            fe = AP.get(x['far'])
            dfar = gc((fx[1], fx[2]), fe) if fe else None
            h90.append((x['role'], x['far'], round(off), round(dfar) if dfar is not None else None,
                        round(gc((fx[1], fx[2]), SHA))))
    print(' own heading test > 90 deg:', len(h90))
    for h in h90:
        print('   ', h)
    # src / evidence completeness
    bad_src = 0
    bad_ev = 0
    vals = collections.Counter()
    for x in m:
        s = x.get('src')
        if not isinstance(s, dict) or not s:
            bad_src += 1
        else:
            for k, v in s.items():
                vals[(k, v)] += 1
                if v not in ('obs', 'inf', None):
                    bad_src += 1
            if s.get('sha_time') != 'inf' or s.get('role_at_ZSSS') != 'inf' or s.get('sha_airport') != 'inf':
                bad_src += 1
            if x['obs_far'] and s.get('far_end_event') != 'obs':
                bad_src += 1
        ev = x.get('evidence')
        if not isinstance(ev, dict) or not ev.get('adsb') or not ev.get('route') or (x['pick'] and not ev.get('sha_time')):
            bad_ev += 1
    print(' records with bad/missing src:', bad_src, ' bad/missing evidence:', bad_ev)
    print(' src value set:', sorted({v for (k, v) in vals}, key=str))
    # Types
    fam = collections.Counter()
    for x in ident:
        t = x['t']
        fam[FAM.get(t, 'wide' if t in WIDE else 'other:' + t)] += 1
    print(' families', dict(fam))
    # Hourly (local = UTC+8), 06-24
    hours = collections.Counter(((x['t_sha'] // 3600) + 8) % 24 for x in ident)
    print(' mean per hour 06-24 local: %.1f' % (sum(hours[h] for h in range(6, 24)) / 18))
    for x in ident:
        x['_day'] = day
    allid += ident

# Two-day type mix
fam = collections.Counter()
for x in allid:
    t = x['t']
    fam[FAM.get(t, 'wide' if t in WIDE else 'other:' + t)] += 1
n = len(allid)
print('=== both days: n', n, {k: '%.1f %%' % (100 * v / n) for k, v in fam.items()})

# Sequence test (own): same aircraft, consecutive SHA events
A, B = 1195.0, 4.42  # global M1 air-time line, s and s/km (B1 report: 1,182-1,207 s + 4.41-4.43 s/km)
by_ac = collections.defaultdict(list)
for x in allid:
    by_ac[x['icao']].append(x)
flags = []
ad_gaps = []
npairs = 0
for ac, xs in by_ac.items():
    xs.sort(key=lambda x: x['t_sha'])
    for a, b in zip(xs, xs[1:]):
        gap = (b['t_sha'] - a['t_sha']) / 60
        s2 = math.hypot(a['sigma_s'], b['sigma_s']) / 60
        if a['role'] == 'arr' and b['role'] == 'dep':
            ad_gaps.append(gap)
            if gap < 25 - 2 * s2:
                flags.append(('arr->dep', a['far'], b['far'], round(gap), round(s2, 1)))
        elif a['role'] == 'dep' and b['role'] == 'arr':
            npairs += 1
            fe = AP.get(a['far'])
            if not fe:
                continue
            dk = gc(SHA, fe)
            need = 2 * (A + B * dk) / 60 + 30
            if a['far'] == b['far'] and gap < need - 2 * s2:
                flags.append(('dep->arr', a['far'], b['far'], round(gap), round(need), round(s2, 1)))
            elif a['far'] != b['far']:
                fe2 = AP.get(b['far'])
                need2 = ((A + B * dk) + (A + B * gc(SHA, fe2))) / 60 + 30 if fe2 else need
                if gap < need2 - 2 * s2:
                    flags.append(('dep->arr diff far', a['far'], b['far'], round(gap), round(need2), round(s2, 1)))
        elif a['role'] == b['role'] and gap < 60:
            flags.append(('same role <60', a['role'], a['far'], b['far'], round(gap)))
print('=== sequence test: dep->arr pairs', npairs, ' arr->dep pairs', len(ad_gaps),
      ' arr->dep min %.0f P5 %.0f median %.0f' % (min(ad_gaps), q(ad_gaps, .05), q(ad_gaps, .5)))
print(' flags', len(flags))
for f_ in flags:
    print('  ', f_)
# Region counts
for day in ('2026-11-10', '2026-11-12'):
    xs = [x for x in allid if x['_day'] == day]
    print(day, 'far-end event observed', sum(1 for x in xs if x['obs_far']))
    print(day, 'M1 picks: far ends + route km', [(x['far'], round(gc(SHA, AP[x['far']]))) for x in xs if x['pick'] == 'M1'])
