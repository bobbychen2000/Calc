"""Stationary stays of aircraft on the HWD field from the pinned adsb.lol hours, clustered into parking spots ->
refs/cache/adsb/hwd_parked_stays.json (positions, type designators, emitter categories, source classes, counts: no ICAO
address, registration, callsign or time stamp - default D1). Seeds the tie-down / ramp spot inference (PLAN D3).

Forked from sfo3d/tools/stands/adsb_parked.py @ a967f9b. Kept: per-aircraft maximal runs of on-ground reports that stay
within BREAK_M m of the run's running median (last 40 fixes), a gap of more than MAX_GAP s ends a run, position = median
of the reports with good NACp, spread = 90th percentile distance from it, provider = adsb.lol only (ODbL). Changed:
input = refs/cache/local/adsb/hwd_tracks.pkl (extract.py; HWD frame hwd_frame.wgs84_to_world); 'on ground' = the ground
flag or derive.py 'ground by kinematics'; a fix is still when gs < STILL_GS kt (or no gs) OR it lies within SPREAD_M m of
the run median (task G4: "gs < 1 kt or position spread < 3 m"); minimum duration MIN_STAY_S = 300 s (sfo3d 180 s); the
good-NACp set is NACp >= 9 (EPU < 30 m) when it has >= 3 fixes, else >= 8, else all; heading from the last taxi-in segment
(below) instead of the reported true_heading (which is kept as hdg_rep for comparison); no flysfo stand matching (SFO
only); identity fields dropped from the output (and, since the Phase 1 review, the exact stay duration dur_s and the
transport class is called 'feed', not 'src', which in hwd3d means obs / inf); OSM location labels and a NAIP 2024 NDVI pavement check per stay; stays
clustered into spots; signal starts / ends on the ground (the method of sfo3d/tools/imagery/adsb_ground_cells.py
'signal_end' @ a967f9b: a ground fix followed / preceded by >= SIG_GAP_S of no fix of that aircraft, here counting only
time the recorder was polling).

Heading from the taxi-in segment: scanning back from the stay's first fix (gaps <= 180 s), the last fix that is TAXI_MIN_M
to TAXI_MAX_M from the stay position; hdg_taxi = direction from it to the stay position (deg true). null when the aircraft
arrived through a polling hole from farther away, or the stay began with the signal (powered on in place). GA aircraft
are often pushed back into tie-downs by hand after shutdown, so hdg_taxi is the direction of arrival, not necessarily the
parked heading [inferred].
Spots: complete-linkage clustering (scipy) of the stay positions of stays with NACp median >= SPOT_NACP and spread90 <=
SPOT_SPREAD_M, cut at SPOT_DIAM_M (every pair of member stays within SPOT_DIAM_M: radius about SPOT_DIAM_M / 2 = 4 m).
A visit = consecutive stays of one aircraft in a spot without a fix farther than VISIT_LEAVE_M from the spot in between.
Sessions (round-1 re-check, 2026-11-12; round 2, 2026-11-13): stays and signal edges carry an opaque 'session' number -
one aircraft's continuous presence at one place (sessions()); spots list the sessions of their stays. A stay and its own
signal start / end are one session, and so is a parked aircraft's power cycle (signal end, then its next start at the same
place with no fix elsewhere in between, however long after); the same aircraft after taxiing away or flying is another.
The number is assigned by position, so it holds no time order and no identity (D1).
Note: positions are GNSS antenna positions, not the aircraft centre (common.py header).
usage: python3 -I hwd3d/tools/adsb/parked_stays.py
"""
import json, math, os, sys
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                              # noqa: E402
import derive as DV                                             # noqa: E402

F = C.F
# Basis of each constant (Phase 1 review, 2026-11-12): 'task' = the G4 task text; 'sfo3d' = value of sfo3d
# tools/stands/adsb_parked.py @ a967f9b; 'chosen' = picked by me for HWD, sensitivity not tested.
STILL_GS = 1.0        # kt: task G4 ("gs < 1 kt or position spread < 3 m")
SPREAD_M = 3.0        # m: task G4 (same quote)
BREAK_M = 8.0         # m: sfo3d BREAK_M; about the ADS-B fix noise p99 at NACp 8-9 (position_noise_per_fix in the output)
MAX_GAP = 900.0       # s: sfo3d MAX_GAP (15 min)
MIN_STAY_S = 300.0    # s: chosen (sfo3d 180 s); longer than the ~46 s polling hole x 6 so a stay spans several bursts
TAXI_MIN_M, TAXI_MAX_M = 8.0, 40.0   # m: chosen; a segment longer than the fix noise and shorter than a taxilane turn
SPOT_NACP = 8         # chosen: NACp 8 = EPU < 0.05 NM in DO-260B (from memory, not re-read); the fixes are better (output)
SPOT_SPREAD_M = 8.0   # m: chosen, = BREAK_M
SPOT_DIAM_M = 8.0     # m: chosen; about a GA single's fuselage length, so one spot = one parked aircraft
VISIT_LEAVE_M = 30.0  # m: chosen; leaving the spot by more than about two aircraft lengths counts as a new visit
SIG_GAP_S = 1800.0    # s: sfo3d adsb_ground_cells.py signal_end gap (30 min)
SIG_GS = 3.0          # kt: chosen; slower than a hand-pushed or towed aircraft
AREA_BUF_M = 50.0     # m: chosen; stays are kept inside the OSM aerodrome polygon + this margin (tie-downs at the fence)
NDVI_VEG = 0.2        # NAIP 2024 NDVI above this at a stay = vegetation (not pavement) [chosen threshold, inferred]
COMMIT_DROP = ('dur_s',)   # exact durations stay in the local file; committed stays carry dur_bucket (PLAN D1, review 2026-11-12)
# sessions (round-1 re-check, 2026-11-12: a stay and the signal start / end around it are one observation, not three;
# round-2 re-check, 2026-11-13: the 20-min time limit of round 1 split one uninterrupted presence in two - a signal start,
# 22 fixes within 10.6 m and the signal end 23.7 min later; a signal end and the same aircraft's next start at the same
# place with no fix anywhere in between - so there is no time limit now: only evidence that the aircraft left separates)
SESSION_R_M = 15.0      # m: consecutive events of one aircraft this close in place are one session unless the aircraft has a
                        # fix farther than VISIT_LEAVE_M from the earlier event, or off the ground, in between [chosen]. A
                        # signal end and the next signal start at the same place with no fix in between are one session
                        # (powered off and on while parked): the recording cannot show that it left.


def covered(polls, t0, t1, max_gap=60.0):
    """seconds of [t0, t1] during which the recorder was polling (poll intervals <= max_gap s)."""
    i0 = np.searchsorted(polls, t0); i1 = np.searchsorted(polls, t1)
    p = np.concatenate([[t0], polls[i0:i1], [t1]]); d = np.diff(p)
    return float(d[d <= max_gap].sum())


def stays_of(a, inside):
    """maximal still runs (indices) of one aircraft; inside = bool mask of fixes inside the area."""
    out = []; cur = []
    def flush():
        if len(cur) >= 3 and a['t'][cur[-1]] - a['t'][cur[0]] >= MIN_STAY_S: out.append(list(cur))
    for i in range(len(a['t'])):
        if not (a['gk'][i] and inside[i]):
            flush(); cur = []; continue
        if cur:
            w = cur[-40:]; mx = np.median(a['x'][w]); mz = np.median(a['z'][w])
            d = math.hypot(a['x'][i] - mx, a['z'][i] - mz)
            still = np.isnan(a['gs'][i]) or a['gs'][i] < STILL_GS or d <= SPREAD_M
            if not still or d > BREAK_M or a['t'][i] - a['t'][cur[-1]] > MAX_GAP:
                flush(); cur = []
                if not still: continue
        else:
            if not (np.isnan(a['gs'][i]) or a['gs'][i] < STILL_GS): continue
        cur.append(i)
    flush()
    return out


def describe(a, st, polls, places, naip):
    good = [i for i in st if a['nacp'][i] >= 9]
    gset = 'nacp>=9'
    if len(good) < 3: good = [i for i in st if a['nacp'][i] >= 8]; gset = 'nacp>=8'
    if len(good) < 3: good = list(st); gset = 'all'
    X = a['x'][good]; Z = a['z'][good]; mx = float(np.median(X)); mz = float(np.median(Z))
    d = np.hypot(X - mx, Z - mz)
    t0, t1 = a['t'][st[0]], a['t'][st[-1]]
    i0, i1 = st[0], st[-1]
    # how the stay began / ended
    def edge(i, step, t_):
        j = i + step
        if not (0 <= j < len(a['t'])): return 'signal'
        gap = abs(a['t'][j] - t_)
        if covered(polls, min(t_, a['t'][j]), max(t_, a['t'][j])) < 0.5 * gap and gap > 120: return 'outage'
        if gap > SIG_GAP_S: return 'signal'
        return 'moved' if math.hypot(a['x'][j] - mx, a['z'][j] - mz) > BREAK_M or not a['gk'][j] else 'gap'
    start = edge(i0, -1, t0); end = edge(i1, +1, t1)
    # heading from the taxi-in segment
    hdg = None; hdg_m = None
    j = i0 - 1; tl = t0
    while j >= 0 and tl - a['t'][j] <= 180:
        dd = math.hypot(a['x'][j] - mx, a['z'][j] - mz)
        if dd > TAXI_MAX_M: break
        if dd >= TAXI_MIN_M and a['gk'][j]:
            hdg = round(F.vec_hdg(mx - a['x'][j], mz - a['z'][j]), 1); hdg_m = round(dd, 1); break
        tl = a['t'][j]; j -= 1
    hr = [a['hdg'][i] for i in st if not np.isnan(a['hdg'][i])]
    hdg_rep = None; hdg_rep_R = None
    if hr: hdg_rep, hdg_rep_R = C.circ_mean(hr); hdg_rep = round(hdg_rep, 1); hdg_rep_R = round(hdg_rep_R, 3)
    feed = Counter(a['src'][i] for i in st).most_common(1)[0][0]
    nac = [a['nacp'][i] for i in st if a['nacp'][i] >= 0]
    lab, det = places.label(mx, mz)
    hold = places.near_hold(mx, mz)
    lt0 = C.local_dt(t0); lt1 = C.local_dt(t1)
    overnight = (t1 - t0) >= 3600 and any(C.local_dt(t).hour == 3 for t in np.arange(t0, t1, 1800.0))
    ndvi = None
    if naip is not None:
        ndvi = round(float(naip(mx, mz)), 3)
    return dict(x=round(mx, 2), z=round(mz, 2), spread50=round(float(np.percentile(d, 50)), 2),
                spread90=round(float(np.percentile(d, 90)), 2), n=len(st), n_good=len(good), pos_set=gset,
                dur_s=round(float(t1 - t0)), dur_bucket=C.dur_bucket(t1 - t0), start=start, end=end, overnight=bool(overnight),
                hdg_taxi=hdg, hdg_taxi_from_m=hdg_m, hdg_rep=hdg_rep, hdg_rep_R=hdg_rep_R,
                type=a['type'], cat=a['cat'], cls=a['cls'], cls_src=a['cls_src'], feed=feed,
                nacp_med=None if not nac else float(np.median(nac)), loc=lab, loc_detail=det,
                near_hold_m=None if not hold else round(hold[1], 1), naip2024_ndvi=ndvi,
                _t0=float(t0), _t1=float(t1), _dev=[(a['src'][i], int(a['nacp'][i]), float(math.hypot(a['x'][i] - mx, a['z'][i] - mz))) for i in st])


def load_ndvi():
    import importlib.util
    p = os.path.join(C.HWD, 'tools', 'imagery', 'common.py')
    spec = importlib.util.spec_from_file_location('imagery_common', p); IC = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(IC)
    if not os.path.exists(IC.geotiff_path('2024')): return None, None
    img, geo, src = IC.load_rgb('2024', prefer='tif')
    if img.shape[2] < 4: return None, None
    R = img[..., 0].astype(np.float32); N = img[..., 3].astype(np.float32)
    nd = (N - R) / np.maximum(N + R, 1)
    g = geo['g']

    def f(x, z):
        lat, lon = F.world_to_ll(x, z); E, Nn = F.ll_to_utm10(lat, lon)
        c = int(round((E - geo['e0']) / g - 0.5)); r = int(round((geo['n1'] - Nn) / g - 0.5))
        if not (1 <= r < nd.shape[0] - 1 and 1 <= c < nd.shape[1] - 1): return float('nan')
        return float(nd[r - 1:r + 2, c - 1:c + 2].mean())
    return f, os.path.relpath(src, C.HWD)


def signal_edges(hx, a, polls, inside):
    """ground fixes (gs < SIG_GS) inside the area where the signal ends / starts: >= SIG_GAP_S of polled time without
    a fix of this aircraft after / before them (the recording's start and end count as unknown, not as silence)."""
    out = []; t = a['t']; n = len(t)
    for i in range(n):
        if not (a['gk'][i] and inside[i]) or (not np.isnan(a['gs'][i]) and a['gs'][i] >= SIG_GS): continue
        for kind, j in (('end', i + 1), ('start', i - 1)):
            tn = t[j] if 0 <= j < n else (polls[-1] if kind == 'end' else polls[0])
            lo, hi = (t[i], tn) if kind == 'end' else (tn, t[i])
            if hi - lo < SIG_GAP_S: continue
            cov = covered(polls, lo, hi)
            if cov >= SIG_GAP_S:
                out.append(dict(kind=kind, x=round(float(a['x'][i]), 2), z=round(float(a['z'][i]), 2), type=a['type'],
                                cls=a['cls'], cat=a['cat'], feed=a['src'][i], nacp=int(a['nacp'][i]),
                                silent_bucket=C.dur_bucket(cov), _hex=hx, _t=float(t[i])))
    return out


RUNUP_APRONS = ('10L Runup', '28L Run-up', '28R Runup')     # OSM apron ref / name tags (refs/cache/osm/khwd_features.json)


def sessions(stays, sig, T):
    """one aircraft's continuous presence at one place: its stays and signal starts / ends, linked when consecutive in
    time, <= SESSION_R_M apart and with no fix of that aircraft farther than VISIT_LEAVE_M from the earlier event or off the
    ground in between (no time limit: a power cycle while parked, even overnight, is the same presence). Writes
    s['session'] / e['session']: an opaque number per session (numbered by the position of the session's first-listed
    event, so it carries no time order and no identity; the same aircraft after taxiing away or flying is another
    session). Returns the number of sessions."""
    ev = [(s['_hex'], s['_t0'], s['_t1'], s['x'], s['z'], s) for s in stays] + [(e['_hex'], e['_t'], e['_t'], e['x'], e['z'], e) for e in sig]
    par = list(range(len(ev)))

    def root(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    by = {}
    for i, e in enumerate(ev): by.setdefault(e[0], []).append(i)
    for hx in sorted(by):
        idx = sorted(by[hx], key=lambda i: (ev[i][1], ev[i][2]))
        a = T[hx]
        for i, j in zip(idx, idx[1:]):
            A, B = ev[i], ev[j]
            if math.hypot(A[3] - B[3], A[4] - B[4]) > SESSION_R_M: continue
            m = (a['t'] > A[2]) & (a['t'] < B[1])
            if m.any() and (np.hypot(a['x'][m] - A[3], a['z'][m] - A[4]).max() > VISIT_LEAVE_M or (~a['gk'][m]).any()): continue
            par[root(j)] = root(i)
    groups = {}
    for i in range(len(ev)): groups.setdefault(root(i), []).append(i)
    order = sorted(groups.values(), key=lambda g: min((round(ev[i][3], 2), round(ev[i][4], 2)) for i in g))
    for n, g in enumerate(order):
        for i in g: ev[i][5]['session'] = n + 1
    return len(order)


def spot_kind(M, lab, det, places, x, z):
    """what a spot most likely is [inferred from its place and members]: 'runup_or_hold' (OSM run-up apron, <= 25 m of an
    OSM holding position, or on a taxiway / runway), 'helicopter' (most member stays by helicopters), else 'parking'."""
    if (lab == 'apron' and det in RUNUP_APRONS) or places.near_hold(x, z) or lab in ('taxiway', 'runway'): return 'runup_or_hold'
    if sum(s['cls'] == 'helicopter' for s in M) * 2 > len(M): return 'helicopter'
    return 'parking'


def cluster(stays):
    from scipy.cluster.hierarchy import linkage, fcluster
    P = np.array([[s['x'], s['z']] for s in stays])
    if len(P) < 2: return np.ones(len(P), int)
    Zl = linkage(P, method='complete')
    return fcluster(Zl, t=SPOT_DIAM_M, criterion='distance')


def main():
    D = DV.load(); T = D['tracks']; polls = D['polls']
    cal = DV.calibrate(T); places = DV.Places()
    area = places.aerodrome.buffer(AREA_BUF_M)
    from shapely import contains_xy
    naip, naip_src = load_ndvi()
    stays = []; sig = []; hexes_with_stays = set()
    for hx, a in T.items():
        if np.hypot(a['x'], a['z']).min() > 2500: continue
        a['hex'] = hx; DV.derive(a, cal)
        inside = contains_xy(area, a['x'], a['z'])
        if not (a['gk'] & inside).any(): continue
        for st in stays_of(a, inside):
            s = describe(a, st, polls, places, naip); s['_hex'] = hx; stays.append(s); hexes_with_stays.add(hx)
        sig += signal_edges(hx, a, polls, inside)
    n_sessions = sessions(stays, sig, T)
    # ---- spots
    elig = [s for s in stays if (s['nacp_med'] or 0) >= SPOT_NACP and s['spread90'] <= SPOT_SPREAD_M]
    lab = cluster(elig)
    spots = []
    for k in sorted(set(lab)):
        M = [s for s, l in zip(elig, lab) if l == k]
        cx = float(np.median([s['x'] for s in M])); cz = float(np.median([s['z'] for s in M]))
        rad = max(math.hypot(s['x'] - cx, s['z'] - cz) for s in M)
        # visits
        vis = 0
        for hx in set(s['_hex'] for s in M):
            S = sorted([s for s in M if s['_hex'] == hx], key=lambda s: s['_t0'])
            a = T[hx]; vis += 1
            for p, q in zip(S, S[1:]):
                m = (a['t'] > p['_t1']) & (a['t'] < q['_t0'])
                if m.any() and (np.hypot(a['x'][m] - cx, a['z'][m] - cz).max() > VISIT_LEAVE_M or (~a['gk'][m]).any()):
                    vis += 1
        hs = [s['hdg_taxi'] for s in M if s['hdg_taxi'] is not None]
        hm = C.circ_mean(hs) if hs else (None, None)
        lab_, det = places.label(cx, cz)
        sig_n = Counter(e['kind'] for e in sig if math.hypot(e['x'] - cx, e['z'] - cz) <= SPOT_DIAM_M * 0.75)
        lat, lon = F.world_to_wgs84(cx, cz)
        spots.append(dict(x=round(cx, 2), z=round(cz, 2), lat_wgs84=round(lat, 7), lon_wgs84=round(lon, 7), radius=round(rad, 2),
                          n_stays=len(M), n_visits=vis, n_aircraft=len(set(s['_hex'] for s in M)),
                          sessions=sorted({s['session'] for s in M}),
                          classes=dict(Counter(s['cls'] for s in M).most_common()),
                          types=dict(Counter(s['type'] or '?' for s in M).most_common()),
                          cats=dict(Counter(s['cat'] or '?' for s in M).most_common()),
                          feeds=dict(Counter(s['feed'] for s in M).most_common()),
                          dur_buckets=dict(Counter(s['dur_bucket'] for s in M).most_common()),
                          observed_h=round(sum(s['dur_s'] for s in M) / 3600, 2), overnight_stays=sum(s['overnight'] for s in M),
                          hdg_taxi_mean=None if hm[0] is None else round(hm[0], 1), hdg_taxi_R=None if hm[1] is None else round(hm[1], 3),
                          n_hdg=len(hs), signal_starts=sig_n.get('start', 0), signal_ends=sig_n.get('end', 0),
                          loc=lab_, loc_detail=det, src='obs', kind=spot_kind(M, lab_, det, places, cx, cz), kind_src='inf',
                          evidence='%d ADS-B stays >= %.0f min (%d aircraft)' % (len(M), MIN_STAY_S / 60, len(set(s['_hex'] for s in M)))))
    spots.sort(key=lambda s: (-s['n_visits'], -s['n_stays']))
    for i, s in enumerate(spots): s['id'] = 'P%03d' % (i + 1)
    # ---- statistics: noise by source / NACp, locations, heading agreement
    dev = defaultdict(list); sp = defaultdict(list)
    for s in stays:
        for src, nac, dd in s['_dev']: dev['%s nacp %s' % (src, nac if nac >= 0 else 'none')].append(dd)
        if s['n'] >= 20: sp['%s nacp_med %s' % (s['feed'], 'none' if s['nacp_med'] is None else int(s['nacp_med']))].append(s['spread90'])
    noise = {k: {'n_fixes': len(v), 'p50_m': round(float(np.percentile(v, 50)), 2), 'p90_m': round(float(np.percentile(v, 90)), 2),
                 'p99_m': round(float(np.percentile(v, 99)), 2)} for k, v in sorted(dev.items()) if len(v) >= 20}
    spread = {k: {'n_stays': len(v), 'spread90_median_m': round(float(np.median(v)), 2), 'spread90_p90_m': round(float(np.percentile(v, 90)), 2)}
              for k, v in sorted(sp.items())}
    agree = [C.angdiff(s['hdg_taxi'], s['hdg_rep']) for s in stays if s['hdg_taxi'] is not None and s['hdg_rep'] is not None]
    locs = Counter(s['loc'] for s in stays)
    off = [s for s in stays if s['loc'] == 'off_osm_pavement']
    veg = [s for s in stays if s['naip2024_ndvi'] is not None and s['naip2024_ndvi'] > NDVI_VEG]
    rules = {k: v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, (int, float))}
    clean = lambda s: {k: v for k, v in s.items() if not k.startswith('_') and k not in COMMIT_DROP}
    out = {
        'what': 'Stationary stays (>= %.0f min) of aircraft on the HWD aerodrome from the pinned adsb.lol hours, and parking spots '
                'clustered from them (tools/adsb/parked_stays.py). Positions in the HWD world frame (x east, z south, m; '
                'hwd_frame.py) = GNSS antenna positions. Aggregates only (default D1): no ICAO address, registration, '
                'callsign or time stamp; stays carry a duration bucket, not times.' % (MIN_STAY_S / 60),
        'licence': C.LICENCE, 'attribution': C.ATTRIBUTION,
        'source': 'sfo3d/refs/cache/rec_pack/adsblol_<hour>.jsonl.xz @ %s' % C.PACK_COMMIT, 'hours': C.HOURS, 'frame': F.FRAME_ID,
        'osm': 'refs/cache/osm/khwd_features.json (ODbL, (c) OpenStreetMap contributors) for loc labels',
        'naip_ndvi': naip_src, 'rules': rules, 'rules_text': __doc__.split('usage:')[0].strip(),
        'stay_fields': {'x, z': 'median of the pos_set fixes (m)', 'spread50/90': 'percentile distance of those fixes from it (m)',
                        'n / n_good': 'fixes in the stay / in pos_set', 'dur_bucket': 'observed first-to-last-fix duration '
                        '(+-~50 s, polling holes) as a bucket; the exact seconds stay in the local file (D1)', 'start / end': "how the stay began / ended: moved (taxied in / out), "
                        "signal (the aircraft's signal started / ended there), outage (recorder not polling), gap (fix > 15 min "
                        "later at the same place)", 'overnight': 'covers 03:00 local',
                        'hdg_taxi': 'deg true from the last taxi-in segment (from hdg_taxi_from_m m away), else null',
                        'hdg_rep / hdg_rep_R': 'circular mean of reported true_heading during the stay / its resultant length',
                        'feed': 'dominant ADS-B transport / source class (1090 / UAT / TIS-B ...); not the obs/inf src of the project', 'nacp_med': 'median NACp',
                        'loc / loc_detail': 'OSM label (derive.Places) / OSM id, apron name or distance to mapped pavement',
                        'near_hold_m': 'distance to the nearest OSM holding position if <= 25 m',
                        'naip2024_ndvi': 'NAIP 2024 NDVI (3x3 px) at the stay (> %.1f: vegetation)' % NDVI_VEG,
                        'session': 'opaque session number (stays and signal_edges): one aircraft\'s continuous presence at one place (consecutive events <= %.0f m apart with no fix of it farther than %.0f m away or airborne in between, however long the gap: a power cycle while parked stays one session); numbered by position, not by time or aircraft; the same aircraft after it taxied away or flew is another session. Count sessions, not stays + signal edges, for independent observations' % (SESSION_R_M, VISIT_LEAVE_M)},
        'summary': {
            'stays': len(stays), 'aircraft_with_stays': len(hexes_with_stays), 'spots': len(spots), 'sessions': n_sessions,
            'spot_eligible_stays': len(elig), 'spots_with_2plus_visits': sum(1 for s in spots if s['n_visits'] >= 2),
            'spots_by_kind': dict(Counter(s['kind'] for s in spots).most_common()),
            'parking_spots_with_2plus_visits': sum(1 for s in spots if s['kind'] == 'parking' and s['n_visits'] >= 2),
            'stays_by_loc': dict(locs.most_common()),
            'stays_by_apron': dict(Counter(s['loc_detail'] for s in stays if s['loc'] == 'apron').most_common()),
            'stays_off_osm_pavement': len(off),
            'off_osm_pavement_dist_m': sorted(s['loc_detail'] for s in off),
            'stays_on_runway': locs.get('runway', 0), 'stays_on_taxiway': locs.get('taxiway', 0),
            'stays_near_hold_25m': sum(1 for s in stays if s['near_hold_m'] is not None),
            'stays_ndvi_vegetation': len(veg), 'stays_ndvi_vegetation_by_loc': dict(Counter(s['loc'] for s in veg)),
            'stays_by_class': dict(Counter(s['cls'] for s in stays).most_common()),
            'stays_by_feed': dict(Counter(s['feed'] for s in stays).most_common()),
            'stays_by_duration': dict(Counter(s['dur_bucket'] for s in stays).most_common()),
            'stays_start': dict(Counter(s['start'] for s in stays)), 'stays_end': dict(Counter(s['end'] for s in stays)),
            'stays_with_hdg_taxi': sum(1 for s in stays if s['hdg_taxi'] is not None),
            'hdg_taxi_vs_reported_deg': None if not agree else {'n': len(agree), 'p50': round(float(np.median(agree)), 1),
                                                                 'within_20deg': round(float(np.mean(np.array(agree) <= 20)), 3)},
            'signal_starts': sum(1 for e in sig if e['kind'] == 'start'), 'signal_ends': sum(1 for e in sig if e['kind'] == 'end')},
        'position_noise_per_fix': noise, 'stay_spread90_by_feed_nacp': spread,
        'spots': spots,
        'stays': [clean(s) for s in sorted(stays, key=lambda s: (s['x'], s['z']))],
        'signal_edges': [clean(e) for e in sorted(sig, key=lambda e: (e['kind'], e['x'], e['z']))],
    }
    n = C.write_json(os.path.join(C.OUT_DIR, 'hwd_parked_stays.json'), out)
    C.write_json(os.path.join(C.LOCAL, 'hwd_parked_stays_local.json'),
                 {'note': 'LOCAL ONLY (gitignored): holds ICAO addresses and times',
                  'stays': [{k: v for k, v in s.items() if k != '_dev'} for s in stays], 'signal_edges': sig}, compact=True)
    print('stays %d (%d aircraft), spots %d (%d with >= 2 visits), signal edges %d -> %d bytes' % (
        len(stays), len(hexes_with_stays), len(spots), out['summary']['spots_with_2plus_visits'], len(sig), n))
    print(json.dumps(out['summary'], indent=None)[:3000])


if __name__ == '__main__':
    main()
