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
  refs/cache/observed_elsewhere/sample_for_owner.csv + README   LOCAL ONLY: 40-row spread sample for the owner's review
  docs/phase1/observed_elsewhere_stats.json                     aggregate counts only (committable)

Fix round 1 (docs/phase1/verify_research.md): DB-route flights are cut at coverage gaps longer than their leg air time
+ 30 min (the scan joins gaps up to 4 h); a record whose fix nearest SHA heads > 90 deg the wrong way is re-split or
rejected; M1 sigma comes from out-of-sample validation (Chinese far ends: leave-one-route-out; others: the larger of the
held-out HKG-TPE route and a route k-fold by distance); the M2 bias of a distance bin is removed only where that lowers
the nested out-of-sample sigma by >= 5 % and the bias is >= 2 min.

Operating day D (local, UTC+8) = 04:00 D .. 04:00 D+1 local = 20:00Z D-1 .. 20:00Z D, so it reads the UTC archive
days D-1 and D. Every SHA-side time is INFERRED; identity (callsign, ICAO address, registration, type) and the
far-end segment are OBSERVED (src 'obs').
"""
import collections, csv, datetime as dt, gzip, json, math, os, statistics as st, sys, zipfile, zlib
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
SPLIT_MARGIN_S = 1800                        # Fix 1: split a DB-route flight at a coverage gap > leg air time + 30 min
HEAD_MAX_DEG = 90.0                          # Fix 1: nearest fix must head towards (arr) / away from (dep) ZSSS
TERM_KM = 60.0                               # ... except inside the far-end terminal area, where the track says nothing


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


def leg_air_s(cs, R, A, air):
    """air time (s) of the longest leg of the callsign's DB route, from the M1 air-time line a + b d"""
    aps = R[cs][1].split('-')
    d = [gc_km(A[x][2], A[x][3], A[y][2], A[y][3]) for x, y in zip(aps, aps[1:]) if x in A and y in A]
    return air[0] + air[1] * max(d) if d else None


def split_gaps(flights, R, A, air):
    """Fix 1 (C2 finding 1): the scan joins coverage segments of one callsign across gaps of up to 4 h, so a short SHA
    round trip can hide inside one record (an arrival whose last fix is already on the next leg, or a departure whose
    first fix is still on the previous one). A single leg cannot leave coverage for longer than its whole air time, so a
    DB-route flight is cut at every gap > air time of its longest DB leg + 30 min (never more than the old 4 h).
    The observed take-off stays with the first piece and the observed landing with the last."""
    out, n_cut, n_fl = [], 0, 0
    for f in flights:
        segs, parts = f['segs'], f.get('parts')
        if not ({'sha_route', 'pvg_route'} & set(f['why'])) or f['cs'] not in R or len(segs) < 2 \
                or not parts or len(parts) != len(segs):
            out.append(f); continue
        T = leg_air_s(f['cs'], R, A, air)
        if T is None:
            out.append(f); continue
        thr = min(4 * 3600.0, T + SPLIT_MARGIN_S)
        groups = [[0]]
        for i in range(1, len(segs)):
            (groups.append([i]) if segs[i][0][0] - segs[i - 1][1][0] > thr else groups[-1].append(i))
        if len(groups) == 1:
            out.append(f); continue
        n_cut += len(groups) - 1; n_fl += 1
        for k, g in enumerate(groups):
            sub = dict(f)
            sub['segs'] = [segs[i] for i in g]; sub['parts'] = [parts[i] for i in g]
            sub['dep'] = f['dep'] if k == 0 else None
            sub['arr'] = f['arr'] if k == len(groups) - 1 else None
            sub['n'] = sum(len(p) for p in sub['parts'])
            alts = [p[3] for p in pts_of(sub) if isinstance(p[3], (int, float))]
            sub['alt_max'] = max(alts) if alts else None
            sub['uid'] = f['uid'] if k == 0 else f"{f['uid']}#{k}"
            sub['split'] = {'from': f['uid'], 'piece': k, 'of': len(groups), 'thr_s': round(thr)}
            out.append(sub)
    return out, {'flights_cut': n_fl, 'cuts': n_cut, 'rule': 'cut a SHA/PVG-route flight at a coverage gap longer '
                 'than the air time of its longest DB leg (M1 line) + 30 min, at most 4 h'}


def track_at(f, role):
    """track (deg) at the fix nearest SHA: the stored track there, else the course over the last (first) 2+ km"""
    P = pts_of(f) or [s for seg in f['segs'] for s in seg]
    if not P:
        return None
    seq = P[::-1] if role == 'arr' else P
    p0 = seq[0]
    for p in seq[:6]:
        if abs(p[0] - p0[0]) <= 120 and isinstance(p[5], (int, float)):
            return float(p[5])
    for p in seq[1:]:
        if gc_km(p[1], p[2], p0[1], p0[2]) >= 2:
            return bearing(p[1], p[2], p0[1], p0[2]) if role == 'arr' else bearing(p0[1], p0[2], p[1], p[2])
    return None


def trim_near_end(f, role):
    """drop the coverage segment nearest SHA in time order (arr: the last one, dep: the first one)"""
    g = dict(f)
    if role == 'arr':
        g['segs'], g['parts'], g['arr'] = f['segs'][:-1], (f['parts'] or [])[:-1] or None, None
    else:
        g['segs'], g['parts'], g['dep'] = f['segs'][1:], (f['parts'] or [])[1:] or None, None
    return g


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


def oe_stats(e):
    return errstats(e)


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


def loao(samples, cls_cn, labelled=False):
    """leave-one-airport-out errors per distance bin for one class (cn or not): predicted - actual (s).
    labelled=True returns (airport, route, error) triples for the nested bias check."""
    S = [s for s in samples if s['cn'] == cls_cn]
    errs = collections.defaultdict(list)
    for ap in sorted({s['ap'] for s in S}):
        fit = Model([s for s in samples if s['ap'] != ap])
        for s in S:
            if s['ap'] == ap:
                k = next(i for i, (lo, hi) in enumerate(RBINS) if lo <= s['r'] < hi)
                e = fit(s['r'], s['cn']) - s['dt']
                errs[k].append((ap, s['route'], e) if labelled else e)
    return errs


def bias_correct(lab, hold_route, min_n=8):
    """Fix 1 (C2 finding 6): out-of-sample bias of M2 per distance bin, and the error of the bias-corrected estimate.
    bias[k] = median leave-one-airport-out error in bin k (held-out validation route excluded, so that it stays a clean
    test). The corrected errors are NESTED: each airport's errors are corrected with the median of the OTHER airports'
    errors, so the sigma of the corrected estimate is still out of sample.
    Returns bias {k: s}, sigma_raw {k: s}, sigma_corr {k: s}, corrected errors {k: [s]}"""
    bias, s_raw, s_cor, cor = {}, {}, {}, {}
    for k, v in lab.items():
        v = [x for x in v if x[1] != hold_route]
        if len(v) < min_n:
            continue
        bias[k] = st.median([e for _, _, e in v])
        by = collections.defaultdict(list)
        for ap, _, e in v:
            by[ap].append(e)
        c = []
        for ap, es in by.items():
            rest = [e for a2, e2 in by.items() if a2 != ap for e in e2]
            b = st.median(rest) if len(rest) >= min_n else 0.0
            c += [e - b for e in es]
        s_raw[k] = round(1.4826 * st.median([abs(e) for _, _, e in v]))
        s_cor[k] = round(1.4826 * st.median([abs(e) for e in c]))
        cor[k] = c
    return bias, s_raw, s_cor, cor


BIAS_GAIN = 0.95     # remove a bin's bias only if that cuts the nested out-of-sample sigma by >= 5 % ...
BIAS_MIN_S = 120     # ... and the bias is at least 2 min (smaller ones did not help on the held-out HKG-TPE route)


def bias_used(bias, s_raw, s_cor):
    """bins where the bias is removed, and the sigma that goes with the estimate actually used"""
    use = {k: bias[k] for k in bias if s_cor[k] < BIAS_GAIN * s_raw[k] and abs(bias[k]) >= BIAS_MIN_S}
    sig = {k: (s_cor[k] if k in use else s_raw[k]) for k in s_raw}
    return use, sig


M1_DBINS = [(0, 800), (800, 1500), (1500, 2500), (2500, 20000)]


def m1_sigma_other(kfold, s_hkg, d):
    """M1 sigma for a non-Chinese far end: the larger of the held-out HKG-TPE value and the route-k-fold value for the
    route's distance bin (the error grows with distance; HKG-TPE is one 800 km route)"""
    for lo, hi in M1_DBINS:
        if lo <= d < hi:
            e = [abs(x) for dd, x in kfold if lo <= dd < hi]
            return max(s_hkg, round(1.4826 * st.median(e))) if len(e) >= 30 else s_hkg
    return s_hkg


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
    """movements at HERE (ZSSS, or ZSPD for the rotation cross-check) of flights whose DB route includes HERE.
    Fix 1: a record whose fix nearest SHA heads > 90 deg the wrong way (away from SHA for an arrival, towards it for a
    departure; not tested inside the far-end terminal area) is re-split by dropping the coverage segment nearest SHA
    until it heads the right way; if no segment is left it is rejected ('wrong_heading'). A record whose observed span
    exceeds the leg air time + 30 min is rejected ('span_too_long')."""
    tag = 'sha_route' if HERE == 'ZSSS' else 'pvg_route'
    out = []
    for f in flights:
        if tag not in f['why']:
            continue
        g, dropped, m = f, 0, None
        while True:
            m = one_movement(g, R, A, models, wiki, HERE)
            if m is None or m['consistency'] != 'wrong_heading' or len(g['segs']) < 2:
                break
            g = trim_near_end(g, m['role']); dropped += 1
        if m is None:
            continue
        m['resplit_dropped_segments'] = dropped
        out.append(m)
    return out


def one_movement(f, R, A, models, wiki, HERE):
    m_arr, m_dep, air, air_cn, val_sig, bias, m1_kfold = models
    H = ZSSS if HERE == 'ZSSS' else ZSPD
    wk = 0 if HERE == 'ZSSS' else 1
    aps = R[f['cs']][1].split('-')
    if aps.count(HERE) != 1:
        return None
    legs_ = [(aps[i], aps[i + 1]) for i in range(len(aps) - 1)]
    fit = leg_fit(f, legs_, A)
    if not fit:
        return None
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
        return None
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
    near = last if role == 'arr' else first
    r_near = gc_km(near[1], near[2], *H)
    trk = track_at(f, role)
    brg = bearing(near[1], near[2], *H) if role == 'arr' else bearing(*H, near[1], near[2])
    head_off = round(angdiff(trk, brg)) if trk is not None else None
    in_term = gc_km(near[1], near[2], fa[2], fa[3]) <= TERM_KM
    T_leg = air[0] + air[1] * d_route
    span = last[0] - first[0]
    if cons in ('far_end_match', 'track_consistent'):
        if head_off is not None and head_off > HEAD_MAX_DEG and not in_term:
            cons = 'wrong_heading'
        elif span > T_leg + SPLIT_MARGIN_S:
            cons = 'span_too_long'
    est = {}
    if not other_leg and cons in ('far_end_match', 'track_consistent'):
        cn = mainland(near[1], near[2])
        v = (m_arr if role == 'arr' else m_dep)(r_near, cn)
        if v is not None:
            k = next((i for i, (lo, hi) in enumerate(RBINS) if lo <= r_near < hi), len(RBINS) - 1)
            vs = val_sig[(role, cn)]
            kk = k if vs.get(k) else max(vs, default=0)
            sig = vs.get(kk)
            b = bias[(role, cn)].get(kk, 0.0)
            v = v - b                                   # out-of-sample bias of this bin removed (Fix 1)
            est['M2'] = {'t': round(near[0] + v if role == 'arr' else near[0] - v), 'r_km': round(r_near), 'cn': cn,
                         'sigma_s': sig, 'bias_removed_s': round(b), 'bin_km': list(RBINS[kk])}
        if obs_far and obs_far['ap'] == far:
            a, b2, s1 = air_cn if fa[5] == 'CN' else air
            if fa[5] != 'CN':
                s1 = m1_sigma_other(m1_kfold, s1, d_route)
            T = a + b2 * d_route
            est['M1'] = {'t': round(obs_far['t'] + T if role == 'arr' else obs_far['t'] - T), 'd_km': round(d_route),
                         'sigma_s': s1, 'class': 'cn' if fa[5] == 'CN' else 'other'}
    pick = min((k for k in est if est[k]['sigma_s']), key=lambda k: est[k]['sigma_s'], default=None)
    al = f['cs'][:3]
    w = wiki.get(al)
    wflag = None
    if w:
        hs, ho = wiki_match(w[wk], fa), wiki_match(w[1 - wk], fa)
        me, ot = ('SHA', 'PVG') if HERE == 'ZSSS' else ('PVG', 'SHA')
        wflag = (f'listed_{me}_and_{ot}' if ho else f'listed_{me}') if hs else (f'listed_{ot}_only' if ho else 'not_listed')
    return {'uid': f['uid'], 'here': HERE, 'cs': f['cs'], 'airline': al, 'icao': f['icao'], 'r': f['r'], 't': f['t'],
            'desc': f['desc'], 'route_db': R[f['cs']][1], 'role': role, 'far': far, 'd_route_km': round(d_route),
            'consistency': cons, 'xtrack_med_km': round(med_xt), 'along': [round(at0, 2), round(at1, 2)],
            'first': first, 'last': last, 'nseg': len(f['segs']), 'segs': f['segs'], 'alt_max': f['alt_max'],
            'obs_far': obs_far, 'obs_sha_end': obs_sha, 'est': est, 'pick': pick, 'wiki_pair': wflag,
            't_sha': est[pick]['t'] if pick else None, 'sigma_s': est[pick]['sigma_s'] if pick else None,
            't_obs': first[0] if role == 'dep' else last[0], 'near_km': round(r_near), 'head_off_deg': head_off,
            'near_in_far_terminal': in_term, 'span_s': round(span), 'leg_air_s': round(T_leg),
            'split': f.get('split'), 'archive': f['uid'].split(':')[0],
            'also_pvg_route': 'pvg_route' in f['why'], 'stitched': f.get('stitched', False)}


def dedupe(moves):
    """one record per callsign and role within 6 h (a flight split into two records): keep a DB-consistent record with
    an inferred time if there is one (Fix 1: a split can leave a wrong-leg piece that is longer), else the longest"""
    span = lambda m: m['segs'][-1][1][0] - m['segs'][0][0][0]
    out = []
    for m in sorted(moves, key=lambda m: (not (m['t_sha'] and m['consistency'] in ('far_end_match', 'track_consistent')),
                                          -span(m))):
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
    VAL = ('RCTP', 'VHHH')                                 # held out for the validation the brief asks for
    # --- Fix 1: cut DB-route flights at gaps longer than their leg air time + 30 min (air time from a first fit) ---
    cal0 = [c for c in calib_set(flights, A) if c['route'] != VAL]
    air0 = robust_line([c['d'] for c in cal0], [c['T'] for c in cal0])
    flights, split_info = split_gaps(flights, R, A, air0)
    # --- calibration (all flights of both UTC days seen at an airport) ---------------------------------------
    cal = calib_set(flights, A)
    fitc = [c for c in cal if c['route'] != VAL]
    air_all = robust_line([c['d'] for c in fitc], [c['T'] for c in fitc])
    cnc = [c for c in fitc if c['cn']]
    air_cn = robust_line([c['d'] for c in cnc], [c['T'] for c in cnc]) if len(cnc) >= 15 else air_all
    sig = lambda res: round(1.4826 * st.median([abs(x) for x in res]))
    S = {'arr': ev_samples(flights, A, 'arr'), 'dep': ev_samples(flights, A, 'dep')}
    Sfit = {k: [s for s in v if s['route'] != VAL] for k, v in S.items()}
    M = {k: Model(v) for k, v in Sfit.items()}
    # --- validation -----------------------------------------------------------------------------------------
    val = {'M1_hkg_tpe': [c['T'] - (air_all[0] + air_all[1] * c['d']) for c in cal if c['route'] == VAL]}
    m1_cn = []
    for rt in sorted({c['route'] for c in cnc}):          # leave-one-route-out, Chinese domestic
        fit = [c for c in cnc if c['route'] != rt]
        if len(fit) < 10: continue
        a2, b2, _ = robust_line([c['d'] for c in fit], [c['T'] for c in fit])
        m1_cn += [c['T'] - (a2 + b2 * c['d']) for c in cnc if c['route'] == rt]
    val['M1_cn_loro'] = m1_cn
    # 10-fold by route over all non-Chinese routes, by distance: feeds the M1 sigma of non-Chinese far ends
    # (m1_sigma_other = max(held-out HKG-TPE sigma, 1.4826 x median |error| in the route's distance band); Fix round 1)
    oth = [c for c in fitc if not c['cn']]
    m1_oth = []
    for fold in range(10):
        test = [c for c in oth if zlib.crc32('-'.join(c['route']).encode()) % 10 == fold]
        trn = [c for c in oth if zlib.crc32('-'.join(c['route']).encode()) % 10 != fold]
        if not test or len(trn) < 10: continue
        a3, b3, _ = robust_line([c['d'] for c in trn], [c['T'] for c in trn])
        m1_oth += [(c['d'], c['T'] - (a3 + b3 * c['d'])) for c in test]
    val['M1_other_route_kfold'] = m1_oth
    # Fix 1 (C2 finding 2): M1 sigma = 1.4826 x median |out-of-sample error|, not the fit's own residuals
    air = (air_all[0], air_all[1], sig(val['M1_hkg_tpe']))
    airc = (air_cn[0], air_cn[1], sig(val['M1_cn_loro']) if m1_cn else sig(air_cn[2]))
    m1_insample = {'other': sig(air_all[2]), 'cn': sig(air_cn[2])}
    for k in ('arr', 'dep'):
        e = collections.defaultdict(list)
        for s in S[k]:
            if s['route'] == VAL:
                e[next(i for i, (lo, hi) in enumerate(RBINS) if lo <= s['r'] < hi)].append(
                    (M[k](s['r'], s['cn']) - s['dt'], s['cn']))
        val[f'M2_{k}_hkg_tpe_cls'] = dict(e)
        val[f'M2_{k}_hkg_tpe'] = {i: [x for x, _ in v] for i, v in e.items()}
    val_sig, bias, bias_tab = {}, {}, {}
    for k in ('arr', 'dep'):
        for cn in (True, False):
            lab = loao(S[k], cn, labelled=True)
            nm = f'M2_{k}_{"cn" if cn else "other"}_loao'
            val[nm] = {i: [e for _, _, e in v] for i, v in lab.items()}
            b, s_raw, s_cor, cor = bias_correct(lab, VAL)
            use, sig_used = bias_used(b, s_raw, s_cor)
            val[nm + '_used'] = {i: (cor[i] if i in use else val[nm][i]) for i in cor}
            bias[(k, cn)] = use                            # only bins where removing the bias helps out of sample
            val_sig[(k, cn)] = sig_used                    # nested out-of-sample sigma of the estimate actually used
            bias_tab[nm] = {f'{RBINS[i][0]}-{RBINS[i][1]} km': {'bias_min': round(b[i] / 60, 1),
                                                                'sigma_raw_min': round(s_raw[i] / 60, 1),
                                                                'sigma_corrected_min': round(s_cor[i] / 60, 1),
                                                                'bias_removed': i in use,
                                                                'n': len(cor[i])} for i in sorted(b)}
    for k in ('arr', 'dep'):                               # the held-out route, corrected with the bias tables
        val[f'M2_{k}_hkg_tpe_corrected'] = {i: [x - bias[(k, cn)].get(i, 0.0) for x, cn in v]
                                            for i, v in val[f'M2_{k}_hkg_tpe_cls'].items()}
    # --- SHA movements ----------------------------------------------------------------------------------------
    models = (M['arr'], M['dep'], air, airc, val_sig, bias, m1_oth)
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
                split=split_info, m1_insample=m1_insample, bias_tab=bias_tab,
                m1_sigma={'cn_leave_one_route_out_s': airc[2], 'other_hkg_tpe_s': air[2], 'in_sample_s': m1_insample,
                          'other_used_by_route_km': {f'{lo}-{hi}': m1_sigma_other(m1_oth, air[2], (lo + hi) / 2)
                                                     for lo, hi in M1_DBINS},
                          'other_route_kfold_by_km': {f'{lo}-{hi}': oe_stats([x for d, x in m1_oth if lo <= d < hi])
                                                      for lo, hi in M1_DBINS}},
                val_sig=val_sig, samples={k: len(v) for k, v in S.items()},
                samples_cn={k: sum(s['cn'] for s in v) for k, v in S.items()}, moves=moves, reg=reg, inv=inv,
                pairs=pairs, pair_ex=pair_ex, nflights=len(flights), vrs_commit=vrs.get('commit'))


if __name__ == '__main__':
    import report_observed_elsewhere as rep   # noqa: E402  (aggregates, chart, local table)
    rep.main([run(d) for d in sys.argv[1:]])
