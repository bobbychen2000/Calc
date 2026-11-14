#!/usr/bin/env python3
"""OD2 tier 2: which Hongqiao (ZSSS) movements of one local operating day can be given a real identity and real timing
from open ADS-B seen OUTSIDE the Shanghai coverage gap, and what SHA-side times can be inferred from them.

Inputs (all local, refs/cache/):
  observed_elsewhere/scan/cs_<date>_prod.json.gz  scan_callsigns.py output (adsb.lol globe_history, ODbL 1.0)
  routes_vrs/vrs_index.json.gz                    VRS standing data routes + airports (CC0 1.0)
  registry_mictronics/mictronics/indexedDB_old.zip Mictronics aircraft database (ODC-By 1.0)
  routes_wiki/{sha,pvg}_dest.json                 Wikipedia destination lists (CC BY-SA 4.0), pair-level check only

usage: python3 -I tools/adsb/observed_elsewhere.py 2026-11-12 [2026-11-10 ...]
Outputs:
  refs/cache/observed_elsewhere/sha_observed_<day>.json + .csv   LOCAL ONLY: per-flight identities (PLAN 6b, Q3)
  refs/cache/observed_elsewhere/calibration_<day>.json          LOCAL ONLY: per-flight validation residuals
  docs/phase1/observed_elsewhere_stats.json                     aggregate counts only (committable)

Operating day D (local, UTC+8) = 04:00 D .. 04:00 D+1 local = 20:00Z D-1 .. 20:00Z D, so it reads the UTC archive
days D-1 and D. Every SHA-side time is INFERRED; identity (callsign, ICAO address, registration, type) and the
far-end segment are OBSERVED (src 'obs').
"""
import collections, csv, datetime as dt, gzip, json, math, os, statistics as st, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import legs                                  # noqa: E402
from legs import gc_km, bearing, angdiff, xtrack_km   # noqa: E402

SHA3D = os.path.normpath(os.path.join(HERE, '..', '..'))
CACHE = os.path.join(SHA3D, 'refs', 'cache')
SCAN = os.path.join(CACHE, 'observed_elsewhere', 'scan')
OUT_LOCAL = os.path.join(CACHE, 'observed_elsewhere')
OUT_PUB = os.path.join(SHA3D, 'docs', 'phase1')
ZSSS = (31.19784885, 121.3362899)            # OD0 origin (centre of RWY 18L/36R, OSM way 16714125)
ZSPD = (31.1434, 121.805)                    # VRS airports
SHANGHAI = ('ZSSS', 'ZSPD')
MOVES_PER_DAY = 783.4                        # CAAC Jan-Sep 2026 mean (PLAN §1)
MEAN_06_24 = 44.6                            # PLAN §1 [inf]
TZ = 8 * 3600
INV_R, INV_DEG = 450.0, 15.0                 # inverse search: max distance from ZSSS, max track offset


def jload(p):
    with (gzip.open(p, 'rt') if p.endswith('.gz') else open(p)) as f:
        return json.load(f)


def utc(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc)


def day_window(day):
    d = dt.datetime.strptime(day, '%Y-%m-%d').replace(tzinfo=dt.timezone.utc)
    t0 = (d - dt.timedelta(hours=4)).timestamp()          # 20:00Z D-1 = 04:00 local D
    return t0, t0 + 86400


def family(t):
    if t is None: return 'unknown'
    if t in ('A318', 'A319', 'A320', 'A321', 'A19N', 'A20N', 'A21N'): return 'A320 family'
    if t.startswith('B3') or t in ('B736', 'B737', 'B738', 'B739'): return '737 family'
    if t in ('C919',): return 'C919'
    if t in ('AJ27', 'AJ21'): return 'C909 (ARJ21)'
    if t[:3] in ('A33', 'A35', 'A34', 'A38') or t[:3] in ('B77', 'B78', 'B74', 'B76') or t in ('A306', 'A30B', 'A310'):
        return 'wide-body'
    if t.startswith('E1') or t.startswith('E7') or t.startswith('E9'): return 'E-Jet'
    return 'other'


# ---------------------------------------------------------------------------------------------- loading + stitching
def load_days(day, vrs):
    d = dt.datetime.strptime(day, '%Y-%m-%d')
    files = [(d - dt.timedelta(days=1)).strftime('%Y.%m.%d'), d.strftime('%Y.%m.%d')]
    flights, detail, meta = [], {}, []
    for k, fd in enumerate(files):
        p = os.path.join(SCAN, f'cs_{fd}_prod.json.gz')
        x = jload(p)
        meta.append({k2: x[k2] for k2 in ('date', 'source', 'n_traces_scanned', 'n_traces_box', 'n_skipped_flags')})
        for f in x['flights']:
            f = dict(f); f['uid'] = f'{fd}:{f["id"]}'; f['parts'] = x['detail'].get(str(f['id']))
            flights.append(f)
    # stitch flights cut at 00:00Z: same aircraft + callsign, end of day 1 within 15 min of start of day 2
    by = collections.defaultdict(list)
    for f in flights:
        by[(f['icao'], f['cs'])].append(f)
    mid = dt.datetime.strptime(files[1], '%Y.%m.%d').replace(tzinfo=dt.timezone.utc).timestamp()
    drop = set()
    for key, fl in by.items():
        a = [f for f in fl if abs(f['segs'][-1][1][0] - mid) < 900 and f['uid'].startswith(files[0])]
        b = [f for f in fl if abs(f['segs'][0][0][0] - mid) < 900 and f['uid'].startswith(files[1])]
        if a and b and key[1]:
            x, y = a[0], b[0]
            x['segs'] = x['segs'] + y['segs']; x['arr'] = y['arr']; x['n'] += y['n']
            x['alt_max'] = max([v for v in (x['alt_max'], y['alt_max']) if v is not None], default=None)
            x['why'] = sorted(set(x['why']) | set(y['why']))
            if x['parts'] or y['parts']:
                x['parts'] = (x['parts'] or []) + (y['parts'] or [])
            x['stitched'] = True; drop.add(y['uid'])
    return [f for f in flights if f['uid'] not in drop], meta


# ---------------------------------------------------------------------------------------------- calibration
def pts_of(f):
    return [p for part in (f['parts'] or []) for p in part]


def mainland(lat, lon):
    """crude 'Chinese domestic airspace' test for a fix: mainland side of the Taiwan Strait / East China Sea [inf]"""
    return 18 <= lat <= 54 and 73 <= lon <= 122.6 and not (21.5 <= lat <= 25.6 and lon >= 119.6)


def calib_set(flights, A):
    """flights seen from take-off to landing at two different airports, > 200 km apart"""
    out = []
    for f in flights:
        if not (f['dep'] and f['arr']) or f['dep']['ap'] == f['arr']['ap']:
            continue
        a, b = A.get(f['dep']['ap']), A.get(f['arr']['ap'])
        if not a or not b:
            continue
        d = gc_km(a[2], a[3], b[2], b[3]); T = f['arr']['t'] - f['dep']['t']
        if d < 200 or T <= 0 or not (250 <= d / (T / 3600) <= 1000):
            continue
        cn = a[5] == 'CN' and b[5] == 'CN'
        out.append({'f': f, 'd': d, 'T': T, 'cn': cn, 'route': tuple(sorted((f['dep']['ap'], f['arr']['ap']))),
                    'dir': (f['dep']['ap'], f['arr']['ap']), 'a': a, 'b': b})
    return out


def robust_line(x, y, it=8):
    """y = a + b x by iteratively reweighted least squares (Huber), returns a, b, residuals"""
    w = [1.0] * len(x)
    a = b = 0.0
    for _ in range(it):
        sw = sum(w); mx = sum(wi * xi for wi, xi in zip(w, x)) / sw; my = sum(wi * yi for wi, yi in zip(w, y)) / sw
        sxx = sum(wi * (xi - mx) ** 2 for wi, xi in zip(w, x)); sxy = sum(wi * (xi - mx) * (yi - my) for wi, xi, yi in zip(w, x, y))
        b = sxy / sxx if sxx else 0.0; a = my - b * mx
        r = [yi - a - b * xi for xi, yi in zip(x, y)]
        s = 1.4826 * st.median([abs(v) for v in r]) or 1.0
        w = [1.0 if abs(v) <= 1.5 * s else 1.5 * s / abs(v) for v in r]
    return a, b, [yi - a - b * xi for xi, yi in zip(x, y)]


def q(v, p):
    v = sorted(v)
    if not v: return None
    k = (len(v) - 1) * p; i = int(k); j = min(i + 1, len(v) - 1)
    return v[i] + (v[j] - v[i]) * (k - i)


def errstats(e):
    e = [x / 60 for x in e]
    if not e: return {'n': 0}
    return {'n': len(e), 'median_min': round(q(e, .5), 1), 'mae_min': round(st.mean(abs(x) for x in e), 1),
            'p10_min': round(q(e, .1), 1), 'p90_min': round(q(e, .9), 1),
            'abs_p50_min': round(q([abs(x) for x in e], .5), 1), 'abs_p90_min': round(q([abs(x) for x in e], .9), 1)}


RBINS = [(40, 120), (120, 200), (200, 300), (300, 450), (450, 650), (650, 900), (900, 1300), (1300, 2000), (2000, 3500)]


def ev_samples(flights, A, end):
    """(r, dt) samples between an OBSERVED landing (end='arr': time to go) or take-off (end='dep': time since) and the
    coverage-segment entry/exit fixes of the same flight (plus its stored track, binned), one per flight and bin"""
    out = []
    for f in flights:
        ev = f[end]
        if not ev or ev['ap'] not in A:
            continue
        ap = A[ev['ap']]
        P = [s for seg in f['segs'] for s in seg] + pts_of(f)
        got = set()
        for p in P:
            if (end == 'arr' and p[0] >= ev['t']) or (end == 'dep' and p[0] <= ev['t']):
                continue
            r = gc_km(p[1], p[2], ap[2], ap[3]); dtt = abs(ev['t'] - p[0])
            if r < 40 or not (150 / 3600 <= r / dtt <= 1050 / 3600):
                continue
            k = next((i for i, (lo, hi) in enumerate(RBINS) if lo <= r < hi), None)
            if k is None or k in got:
                continue
            got.add(k)
            other = f['arr' if end == 'dep' else 'dep']
            out.append({'r': r, 'dt': dtt, 'ap': ev['ap'], 'cn': ap[5] == 'CN' and mainland(p[1], p[2]),
                        'route': tuple(sorted((ev['ap'], other['ap']))) if other else None, 'uid': f['uid']})
    return out


class TTG:
    """per distance bin: robust line dt = a + b r; residuals kept for the uncertainty"""
    def __init__(self, samples, min_n=12):
        self.bins = []
        for lo, hi in RBINS:
            s = [x for x in samples if lo <= x['r'] < hi]
            if len(s) < min_n:
                continue
            a, b, r = robust_line([x['r'] for x in s], [x['dt'] for x in s])
            self.bins.append((lo, hi, a, b, r, len(s)))

    def __call__(self, r):
        if not self.bins:
            return None
        for lo, hi, a, b, res, n in self.bins:
            if lo <= r < hi:
                return a + b * r
        lo, hi, a, b, res, n = self.bins[-1] if r >= self.bins[-1][1] else self.bins[0]
        return max(60.0, a + b * r)


class Model:
    """time-to-go (arr) or time-since-take-off (dep) model; class 'cn' (Chinese domestic airspace) or 'other'"""
    def __init__(self, samples):
        self.all = TTG(samples); self.cn = TTG([s for s in samples if s['cn']])

    def __call__(self, r, cn):
        m = self.cn if cn and self.cn.bins else self.all
        v = m(r)
        return v if v is not None else self.all(r)


def loao(samples, cls_cn):
    """leave-one-airport-out errors per distance bin for one class (cn or not): predicted - actual (s)"""
    S = [s for s in samples if s['cn'] == cls_cn]
    errs = collections.defaultdict(list)
    for ap in sorted({s['ap'] for s in S}):
        fit = Model([s for s in samples if s['ap'] != ap])
        for s in S:
            if s['ap'] == ap:
                k = next(i for i, (lo, hi) in enumerate(RBINS) if lo <= s['r'] < hi)
                errs[k].append(fit(s['r'], s['cn']) - s['dt'])
    return errs


# ---------------------------------------------------------------------------------------------- SHA flights
def leg_fit(f, legs_, A):
    """pick the DB route leg (X, Y) that best matches the observed fixes"""
    P = pts_of(f) or [s for seg in f['segs'] for s in seg]
    best = None
    for X, Y in legs_:
        a, b = A.get(X), A.get(Y)
        if not a or not b:
            continue
        xs, ats = [], []
        for p in P[:: max(1, len(P) // 60)]:
            xt, at = xtrack_km(p[1], p[2], a[2], a[3], b[2], b[3]); xs.append(abs(xt)); ats.append(at)
        med = st.median(xs)
        mono = (ats[-1] - ats[0]) if len(ats) > 1 else 0.0
        bad_ap = bool((f['dep'] and f['dep']['ap'] != X) or (f['arr'] and f['arr']['ap'] != Y))
        dleg = gc_km(a[2], a[3], b[2], b[3])
        out_of_leg = min(ats) < -0.15 or max(ats) > 1.15
        score = med / max(dleg, 300) + (5 if mono < -0.02 else 0) + (10 if bad_ap else 0) + (1 if out_of_leg else 0)
        if best is None or score < best[0]:
            best = (score, X, Y, med, mono, min(ats), max(ats), bad_ap, dleg)
    return best


def sha_movements(flights, R, A, models, wiki, HERE='ZSSS'):
    """movements at HERE (ZSSS, or ZSPD for the rotation cross-check) of flights whose DB route includes HERE"""
    m_arr, m_dep, air, air_cn, val_sig = models
    tag = 'sha_route' if HERE == 'ZSSS' else 'pvg_route'
    H = ZSSS if HERE == 'ZSSS' else ZSPD
    wk = 0 if HERE == 'ZSSS' else 1
    out = []
    for f in flights:
        if tag not in f['why']:
            continue
        aps = R[f['cs']][1].split('-')
        if aps.count(HERE) != 1:
            continue
        legs_ = [(aps[i], aps[i + 1]) for i in range(len(aps) - 1)]
        fit = leg_fit(f, legs_, A)
        if not fit:
            continue
        score, X, Y, med_xt, mono, at0, at1, bad_ap, dleg = fit
        other_leg = HERE not in (X, Y)
        if other_leg:                                   # observed on a leg that does not touch SHA (multi-leg number)
            i = aps.index(HERE); j = aps.index(Y)
            role = 'arr' if i > j else 'dep'
            far = aps[i - 1] if role == 'arr' else aps[i + 1]
        else:
            role = 'arr' if Y == HERE else 'dep'
            far = X if role == 'arr' else Y
        if far not in A:
            continue
        fa = A[far]; d_route = gc_km(fa[2], fa[3], *H)
        first, last = f['segs'][0][0], f['segs'][-1][1]
        obs_far = (f['dep'] if role == 'arr' else f['arr']) if not other_leg else None
        obs_sha = (f['arr'] if role == 'arr' else f['dep']) if not other_leg else None
        xt_lim = max(150.0, 0.2 * dleg)
        if other_leg:
            cons = 'other_leg' if (med_xt <= xt_lim and not bad_ap) else 'track_inconsistent'
        elif obs_far and obs_far['ap'] == far:
            cons = 'far_end_match'
        elif obs_far and obs_far['ap'] != far:
            cons = 'far_end_mismatch'
        elif obs_sha and obs_sha['ap'] not in SHANGHAI:
            cons = 'sha_end_mismatch'
        elif med_xt <= xt_lim and mono >= -0.02:
            cons = 'track_consistent'
        else:
            cons = 'track_inconsistent'
        est = {}
        if not other_leg and cons in ('far_end_match', 'track_consistent'):
            near = last if role == 'arr' else first
            r_near = gc_km(near[1], near[2], *H); cn = mainland(near[1], near[2])
            v = (m_arr if role == 'arr' else m_dep)(r_near, cn)
            if v is not None:
                k = next((i for i, (lo, hi) in enumerate(RBINS) if lo <= r_near < hi), len(RBINS) - 1)
                sig = val_sig[(role, cn)].get(k) or val_sig[(role, cn)].get(max(val_sig[(role, cn)], default=0))
                est['M2'] = {'t': round(near[0] + v if role == 'arr' else near[0] - v), 'r_km': round(r_near), 'cn': cn,
                             'sigma_s': sig}
            if obs_far and obs_far['ap'] == far:
                a, b, s1 = air_cn if fa[5] == 'CN' else air
                T = a + b * d_route
                est['M1'] = {'t': round(obs_far['t'] + T if role == 'arr' else obs_far['t'] - T), 'd_km': round(d_route),
                             'sigma_s': s1}
        pick = min((k for k in est if est[k]['sigma_s']), key=lambda k: est[k]['sigma_s'], default=None)
        al = f['cs'][:3]
        w = wiki.get(al)
        wflag = None
        if w:
            hs, ho = wiki_match(w[wk], fa), wiki_match(w[1 - wk], fa)
            me, ot = ('SHA', 'PVG') if HERE == 'ZSSS' else ('PVG', 'SHA')
            wflag = (f'listed_{me}_and_{ot}' if ho else f'listed_{me}') if hs else (f'listed_{ot}_only' if ho else 'not_listed')
        out.append({'uid': f['uid'], 'here': HERE, 'cs': f['cs'], 'airline': al, 'icao': f['icao'], 'r': f['r'], 't': f['t'],
                    'desc': f['desc'], 'route_db': R[f['cs']][1], 'role': role, 'far': far, 'd_route_km': round(d_route),
                    'consistency': cons, 'xtrack_med_km': round(med_xt), 'along': [round(at0, 2), round(at1, 2)],
                    'first': first, 'last': last, 'nseg': len(f['segs']), 'segs': f['segs'], 'alt_max': f['alt_max'],
                    'obs_far': obs_far, 'obs_sha_end': obs_sha, 'est': est, 'pick': pick, 'wiki_pair': wflag,
                    't_sha': est[pick]['t'] if pick else None, 'sigma_s': est[pick]['sigma_s'] if pick else None,
                    't_obs': first[0] if role == 'dep' else last[0],
                    'also_pvg_route': 'pvg_route' in f['why'], 'stitched': f.get('stitched', False)})
    return out


def dedupe(moves):
    """one record per callsign and role within 6 h (a flight split into two records): keep the longest coverage"""
    span = lambda m: m['segs'][-1][1][0] - m['segs'][0][0][0]
    out = []
    for m in sorted(moves, key=lambda m: -span(m)):
        if not any(o['cs'] == m['cs'] and o['role'] == m['role'] and abs(o['t_obs'] - m['t_obs']) < 6 * 3600 for o in out):
            out.append(m)
    return out


def rotation(moves, lo=20 * 60, hi=150 * 60):
    """internal DB check: for one aircraft, a Shanghai arrival (SHA or PVG per DB) followed 20-150 min later by a
    Shanghai departure. Same airport = consistent; SHA then PVG (or the reverse) = one of the two DB routes is wrong,
    or an unseen positioning flight. Only DB-consistent records with an inferred time are used."""
    ok = [m for m in moves if m['t_sha'] and m['consistency'] in ('far_end_match', 'track_consistent')]
    by = collections.defaultdict(list)
    for m in ok:
        by[m['icao']].append(m)
    c = collections.Counter(); turns = []; bad = []
    for h, ms in by.items():
        ms.sort(key=lambda m: m['t_sha'])
        for a, b in zip(ms, ms[1:]):
            if a['role'] != 'arr' or b['role'] != 'dep':
                continue
            g = b['t_sha'] - a['t_sha']
            if not lo <= g <= hi:
                continue
            k = f"{a['here']}->{b['here']}"
            c[k] += 1
            if a['here'] == b['here'] == 'ZSSS':
                turns.append(g)
            elif a['here'] != b['here']:
                bad.append((a['cs'], a['route_db'], b['cs'], b['route_db'], round(g / 60)))
    return {'pairs': dict(c), 'sha_turn_min': [round(x / 60) for x in turns], 'mixed_examples': bad[:40]}


# ---------------------------------------------------------------------------------------------- inverse (no DB)
def inverse(flights, R, A, t0, t1, big_aps):
    """DB-free search: flights whose coverage ENDS airborne heading for Shanghai (no landing seen, no later segment),
    or BEGINS airborne heading away from it, within 60-INV_R km, track within INV_DEG of the bearing to/from ZSSS. Then:
    what does the DB say? (scheduled airports = >= 30 VRS routes; those within 40 km of the ray short of Shanghai are
    listed, since the gap also hides Nanjing, Wuxi, Changzhou, Hangzhou, Ningbo ...)"""
    out = []
    for f in flights:
        if not f['cs']:
            continue
        for end in ('arr', 'dep'):
            if f[end]:
                continue
            p = f['segs'][-1][1] if end == 'arr' else f['segs'][0][0]
            if not (t0 <= p[0] < t1) or not isinstance(p[3], (int, float)) or p[5] is None:
                continue
            r = gc_km(p[1], p[2], *ZSSS)
            if not (60 <= r <= INV_R):
                continue
            brg = bearing(p[1], p[2], *ZSSS) if end == 'arr' else bearing(*ZSSS, p[1], p[2])
            if angdiff(p[5], brg) > INV_DEG:
                continue
            hdg = p[5] if end == 'arr' else (p[5] + 180) % 360
            before = []                                   # scheduled airports on the ray, nearer than Shanghai
            for icao in big_aps:
                if icao in SHANGHAI:
                    continue
                a = A[icao]; da = gc_km(p[1], p[2], a[2], a[3])
                if da < 30 or da > r - 30:
                    continue
                off = angdiff(bearing(p[1], p[2], a[2], a[3]), hdg)
                if off < 60 and da * math.sin(math.radians(off)) <= 40:
                    before.append(icao)
            rt = R[f['cs']][1].split('-') if f['cs'] in R else None
            if rt is None:
                db = 'not_in_db'
            elif 'ZSSS' in rt and 'ZSPD' in rt:
                db = 'db_both'
            elif 'ZSSS' in rt:
                db = 'db_sha'
            elif 'ZSPD' in rt:
                db = 'db_pvg'
            else:
                # explained by the DB if its airport (dest for 'arr', origin for 'dep') lies ahead on the ray
                x = rt[-1] if end == 'arr' else rt[0]
                db = 'db_other_unexplained'
                if x in A:
                    a = A[x]; da = gc_km(p[1], p[2], a[2], a[3]); off = angdiff(bearing(p[1], p[2], a[2], a[3]), hdg)
                    if gc_km(a[2], a[3], *ZSSS) <= 300 and da <= r + 100:
                        db = 'db_other_in_gap_yrd'          # another Yangtze-delta airport inside the gap
                    elif off <= 25 and da > r + 50:
                        db = 'db_other_beyond_shanghai'
                    elif off <= 25 and da <= r + 50:
                        db = 'db_other_short_of_shanghai'
            out.append({'uid': f['uid'], 'cs': f['cs'], 'icao': f['icao'], 'end': end, 'r_km': round(r), 'alt': p[3],
                        't': p[0], 'db': db, 'route_db': '-'.join(rt) if rt else None, 'airports_before': before[:6],
                        'type': f['t'], 'airline': f['cs'][:3]})
    return out


# ---------------------------------------------------------------------------------------------- registry
def registry_check(moves):
    z = zipfile.ZipFile(os.path.join(CACHE, 'registry_mictronics', 'mictronics', 'indexedDB_old.zip'))
    ac = {k.lower(): v for k, v in json.loads(z.read('aircrafts.json')).items()}
    ops = json.loads(z.read('operators.json'))
    c = collections.Counter(); seen = set()
    for m in moves:
        h = m['icao']
        if h in seen: continue
        seen.add(h)
        x = ac.get(h)
        c['aircraft'] += 1
        c['trace_has_reg'] += bool(m['r']); c['trace_has_type'] += bool(m['t'])
        if not x:
            c['not_in_mictronics'] += 1
            continue
        c['in_mictronics'] += 1
        if m['r']: c['reg_agree' if x.get('r') == m['r'] else 'reg_differ'] += 1
        else: c['reg_only_mictronics' if x.get('r') else 'reg_neither'] += 1
        if m['t']: c['type_agree' if x.get('t') == m['t'] else 'type_differ'] += 1
        else: c['type_only_mictronics' if x.get('t') else 'type_neither'] += 1
        if (m['r'] or x.get('r') or '').startswith('B-'): c['reg_B-'] += 1
    for m in moves:                                            # fill gaps from Mictronics (marked)
        x = ac.get(m['icao'])
        m['r_src'] = 'trace' if m['r'] else ('mictronics' if x and x.get('r') else None)
        m['t_src'] = 'trace' if m['t'] else ('mictronics' if x and x.get('t') else None)
        if not m['r'] and x: m['r'] = x.get('r') or None
        if not m['t'] and x: m['t'] = x.get('t') or None
        m['operator'] = ops.get(m['airline'], {}).get('n')
    return dict(c)


# ---------------------------------------------------------------------------------------------- Wikipedia pair check
WIKI_AL = {'CES': 'China Eastern Airlines', 'CSH': 'Shanghai Airlines', 'CQH': 'Spring Airlines', 'DKH': 'Juneyao Air',
           'CXA': 'XiamenAir', 'CSN': 'China Southern Airlines', 'CCA': 'Air China', 'CDG': 'Shandong Airlines',
           'CHH': 'Hainan Airlines', 'CSZ': 'Shenzhen Airlines', 'CUA': 'China United Airlines', 'AMU': 'Air Macau',
           'ANA': 'All Nippon Airways', 'AAR': 'Asiana Airlines', 'CPA': 'Cathay Pacific', 'UEA': 'Chengdu Airlines',
           'CAL': 'China Airlines', 'EVA': 'EVA Air', 'HBH': 'Hebei Airlines', 'CRK': 'Hong Kong Airlines',
           'JAL': 'Japan Airlines', 'KAL': 'Korean Air', 'LKE': 'Lucky Air', 'GCR': 'Tianjin Airlines',
           'TBA': 'Xizang Airlines', 'YZR': 'Suparna Airlines'}
LOC = {}


def norm(s):
    s = s.lower().replace('ü', 'u').replace("'", '')
    return ''.join(ch if ch.isalnum() else ' ' for ch in s)


def wiki_match(dests, ap):
    """does a Wikipedia destination name ('Beijing–Capital', 'Tokyo–Haneda', 'Xi'an') denote this VRS airport?"""
    nm = norm(ap[1] + ' ' + LOC.get(id(ap), ''))
    words = set(nm.split())
    for w in dests:
        parts = [norm(x).split() for x in w.replace('—', '–').split('–')]
        if not parts or not parts[0]:
            continue
        city = parts[0]
        if all(t in words for t in city if t not in ('shaanxi', 'guangxi', 'sichuan')) and \
                (len(parts) == 1 or all(t in words for t in parts[1])):
            return w
    return None


def load_wiki(A, locs):
    sha = jload(os.path.join(CACHE, 'routes_wiki', 'sha_dest.json'))
    pvg = jload(os.path.join(CACHE, 'routes_wiki', 'pvg_dest.json'))
    for k, v in A.items():
        LOC[id(v)] = locs.get(k, '')
    return {al: (sha.get(nm, {}).get('dests', []), pvg.get(nm, {}).get('dests', [])) for al, nm in WIKI_AL.items()}


def pair_check(R, A, wiki):
    c = collections.Counter(); ex = collections.defaultdict(list)
    for cs, (al, rt) in R.items():
        aps = rt.split('-')
        if al not in wiki:
            continue
        for here, k_here in (('ZSSS', 0), ('ZSPD', 1)):
            if here not in aps:
                continue
            i = aps.index(here)
            fars = [aps[j] for j in (i - 1, i + 1) if 0 <= j < len(aps) and aps[j] in A]
            for fa in fars[:1]:
                hit = wiki_match(wiki[al][k_here], A[fa]); ohit = wiki_match(wiki[al][1 - k_here], A[fa])
                k = 'listed_here' if hit else ('listed_other_airport_only' if ohit else 'listed_neither')
                c[f'{here}:{k}'] += 1
                if len(ex[f'{here}:{k}']) < 400:
                    ex[f'{here}:{k}'].append((cs, rt))
    return dict(sorted(c.items())), ex


# ---------------------------------------------------------------------------------------------- main
def run(day):
    vrs = jload(os.path.join(CACHE, 'routes_vrs', 'vrs_index.json.gz'))
    R, A = vrs['routes'], vrs['airports']
    wiki = load_wiki(A, vrs.get('airport_loc', {}))
    flights, meta = load_days(day, vrs)
    t0, t1 = day_window(day)
    # --- calibration (all flights of both UTC days seen at an airport) ---------------------------------------
    cal = calib_set(flights, A)
    VAL = ('RCTP', 'VHHH')                                 # held out for the validation the brief asks for
    fitc = [c for c in cal if c['route'] != VAL]
    air_all = robust_line([c['d'] for c in fitc], [c['T'] for c in fitc])
    cnc = [c for c in fitc if c['cn']]
    air_cn = robust_line([c['d'] for c in cnc], [c['T'] for c in cnc]) if len(cnc) >= 15 else air_all
    sig = lambda res: round(1.4826 * st.median([abs(x) for x in res]))
    air = (air_all[0], air_all[1], sig(air_all[2])); airc = (air_cn[0], air_cn[1], sig(air_cn[2]))
    S = {'arr': ev_samples(flights, A, 'arr'), 'dep': ev_samples(flights, A, 'dep')}
    Sfit = {k: [s for s in v if s['route'] != VAL] for k, v in S.items()}
    M = {k: Model(v) for k, v in Sfit.items()}
    # --- validation -----------------------------------------------------------------------------------------
    val = {'M1_hkg_tpe': [c['T'] - (air[0] + air[1] * c['d']) for c in cal if c['route'] == VAL]}
    for k in ('arr', 'dep'):
        e = collections.defaultdict(list)
        for s in S[k]:
            if s['route'] == VAL:
                e[next(i for i, (lo, hi) in enumerate(RBINS) if lo <= s['r'] < hi)].append(M[k](s['r'], s['cn']) - s['dt'])
        val[f'M2_{k}_hkg_tpe'] = dict(e)
    m1_cn = []
    for rt in sorted({c['route'] for c in cnc}):          # leave-one-route-out, Chinese domestic
        fit = [c for c in cnc if c['route'] != rt]
        if len(fit) < 10: continue
        a2, b2, _ = robust_line([c['d'] for c in fit], [c['T'] for c in fit])
        m1_cn += [c['T'] - (a2 + b2 * c['d']) for c in cnc if c['route'] == rt]
    val['M1_cn_loro'] = m1_cn
    val_sig = {}
    for k in ('arr', 'dep'):
        for cn in (True, False):
            e = loao(S[k], cn)
            val[f'M2_{k}_{"cn" if cn else "other"}_loao'] = {i: v for i, v in e.items()}
            val_sig[(k, cn)] = {i: round(1.4826 * st.median([abs(x) for x in v])) for i, v in e.items() if len(v) >= 8}
    # --- SHA movements ----------------------------------------------------------------------------------------
    models = (M['arr'], M['dep'], air, airc, val_sig)
    moves_all = dedupe(sha_movements(flights, R, A, models, wiki))
    pvg_all = dedupe(sha_movements(flights, R, A, models, wiki, HERE='ZSPD'))
    rot = rotation(moves_all + pvg_all)
    inwin = lambda m: t0 <= (m['t_sha'] if m['t_sha'] else m['t_obs']) < t1
    moves = [m for m in moves_all if inwin(m)]
    pvg = [m for m in pvg_all if inwin(m)]
    reg = registry_check(moves)
    big = collections.Counter()
    for cs, (al, rt) in R.items():
        for x in rt.split('-'): big[x] += 1
    big_aps = [k for k, v in big.items() if v >= 30 and k in A and 0 <= A[k][2] <= 60 and 60 <= A[k][3] <= 180]
    inv = inverse(flights, R, A, t0, t1, big_aps)
    pairs, pair_ex = pair_check(R, A, wiki)
    return dict(day=day, meta=meta, window=[t0, t1], cal=cal, pvg=pvg, rot=rot, air=air, air_cn=airc, n_cal_cn=len(cnc), val=val,
                val_sig=val_sig, samples={k: len(v) for k, v in S.items()},
                samples_cn={k: sum(s['cn'] for s in v) for k, v in S.items()}, moves=moves, reg=reg, inv=inv,
                pairs=pairs, pair_ex=pair_ex, nflights=len(flights), vrs_commit=vrs.get('commit'))


if __name__ == '__main__':
    import report_observed_elsewhere as rep   # noqa: E402  (aggregates, chart, local table)
    rep.main([run(d) for d in sys.argv[1:]])
