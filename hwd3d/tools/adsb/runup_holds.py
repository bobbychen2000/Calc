"""Stops of 30 s - 10 min before a departure at HWD (run-up areas, hold-short positions, line-up-and-wait) from the
pinned adsb.lol hours -> refs/cache/adsb/hwd_runup_holds.json (positions, durations, runway, type classes, counts;
default D1: no identity, no time stamp). New file (task G4).

Departures: the 'takeoff' events of events.py (runway episode or hidden transition, obs and inf). For each, the
aircraft's ground fixes (ground flag or ground by kinematics) in the LOOKBACK_S before the start of the take-off roll
(the first fix of the runway episode at >= ROLL_GS kt; for a hidden transition the last ground fix) are split into stops: maximal runs of
still fixes (gs < STILL_GS kt or no gs) that stay within BREAK_M m of the run median, separated by moving fixes.
Duration of a stop: observed = first to last still fix (lower bound, 'dur_lo'); upper bound 'dur_hi' = from the last
moving fix before it to the first moving fix after it (both within HOLE_MAX_S, else open = null). Polling holes of ~46 s
make the two differ (common.py). A stop is kept when dur_hi >= MIN_S (or dur_lo >= MIN_S) and dur_lo <= MAX_S. The scan
stops at a stop with dur_lo > MAX_S (the aircraft was parked: earlier stops belong to the parking) or at an airborne
fix (an earlier flight).
Labels: 'line_up' (on the departure runway's strip), 'runup_apron' (inside an OSM run-up apron: '10L Runup',
'28L Run-up', '28R Runup'), 'hold_short' (<= HOLD_R m of an OSM holding position), else the OSM label (taxiway, apron,
taxilane ...). order = 1 for the last stop before the roll, 2 for the one before, ...
Clusters: complete linkage of the stop positions cut at CL_DIAM_M.
Output fields (Phase 1 review, 2026-11-12): the transport class is 'feed' (not 'src', which in hwd3d means obs / inf);
per-stop durations are rounded to DUR_ROUND_S.
usage: python3 -I hwd3d/tools/adsb/runup_holds.py
"""
import math, os, sys
from collections import Counter
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                              # noqa: E402
import derive as DV                                             # noqa: E402
import events as EV                                             # noqa: E402

# Basis of each constant (Phase 1 review, 2026-11-12): 'chosen' = picked by me for HWD, sensitivity not tested.
LOOKBACK_S = 1800.0   # s: chosen; a taxi-out from the farthest HWD ramp plus a long run-up fits in 30 min
STILL_GS = 1.0        # kt: as parked_stays.py (task G4 "gs < 1 kt")
BREAK_M = 8.0         # m: as parked_stays.py (sfo3d BREAK_M)
MIN_S = 30.0          # s: chosen; the task's lower bound of a run-up / hold stop ("30 s - 10 min" in the header)
MAX_S = 600.0         # s: chosen; the upper bound (longer = parked)
HOLE_MAX_S = 120.0    # s: chosen; about two polling holes (~46 s, common.py) for the dur_hi bound
HOLD_R = 25.0         # m: chosen; a hold bar is 18-91 m from the runway centreline here and an aircraft waits behind it
CL_DIAM_M = 12.0      # m: chosen; about one GA wingspan, so a cluster = one waiting position
ROLL_GS = 10.0        # kt: chosen; faster than taxi on the runway entry turn, slower than the take-off roll
DUR_ROUND_S = 10      # committed per-stop durations are rounded to 10 s (they are known to +-~50 s anyway; D1, review)
RUNUP_APRONS = ('10L Runup', '28L Run-up', '28R Runup')


def stops_before(a, t_roll):
    idx = [i for i in np.where((a['t'] >= t_roll - LOOKBACK_S) & (a['t'] <= t_roll))[0]]
    runs = []; cur = []
    for i in idx:
        if not a['gk'][i]:
            if cur: runs.append(cur)
            runs.append('AIR'); cur = []; continue
        still = np.isnan(a['gs'][i]) or a['gs'][i] < STILL_GS
        if still and cur:
            w = cur[-40:]; mx = np.median(a['x'][w]); mz = np.median(a['z'][w])
            if math.hypot(a['x'][i] - mx, a['z'][i] - mz) > BREAK_M: runs.append(cur); cur = []
        if still: cur.append(i)
        else:
            if cur: runs.append(cur)
            cur = []
    if cur: runs.append(cur)
    out = []
    for r in reversed(runs):          # walk back from the roll
        if r == 'AIR': break
        t0, t1 = a['t'][r[0]], a['t'][r[-1]]
        lo = t1 - t0
        if lo > MAX_S: break
        prev = r[0] - 1; nxt = r[-1] + 1
        hi = None
        if prev >= 0 and nxt < len(a['t']) and t0 - a['t'][prev] <= HOLE_MAX_S and a['t'][nxt] - t1 <= HOLE_MAX_S:
            hi = a['t'][nxt] - a['t'][prev]
        if lo >= MIN_S or (hi is not None and hi >= MIN_S):
            out.append((r, lo, hi))
    return out


def _rnd(v):
    return None if v is None else int(DUR_ROUND_S * round(v / DUR_ROUND_S))


def roll_start(a, e):
    """start of the take-off roll: the first fix of the runway episode moving at >= ROLL_GS kt (so a line-up-and-wait
    stop at the start of the episode counts as a stop); hidden transition: its last ground fix."""
    if e.get('via') == 'runway_episode':
        m = (a['t'] >= e['t0']) & (a['t'] <= e['t1']) & (np.nan_to_num(a['gs'], nan=0) >= ROLL_GS)
        if m.any(): return float(a['t'][m][0])
        return e['t1']
    return e['t0']


def main():
    evs, cal, D, places = EV.run()
    T = D['tracks']
    deps = [e for e in evs if e['type'] == 'takeoff']
    holds = []
    for e in deps:
        a = T[e['hex']]
        t_roll = roll_start(a, e)
        S = stops_before(a, t_roll)
        for k, (r, lo, hi) in enumerate(S):
            good = [i for i in r if a['nacp'][i] >= 9] or r
            mx = float(np.median(a['x'][good])); mz = float(np.median(a['z'][good]))
            lab, det = places.label(mx, mz)
            hold = places.near_hold(mx, mz, HOLD_R)
            strip = a['strip'][r[len(r) // 2]]
            if strip and strip == e.get('rwy'): kind = 'line_up'
            elif lab == 'apron' and det in RUNUP_APRONS: kind = 'runup_apron'
            elif hold: kind = 'hold_short'
            else: kind = lab
            holds.append(dict(x=round(mx, 2), z=round(mz, 2), dur_lo=round(float(lo)), dur_hi=None if hi is None else round(float(hi)),
                              order=k + 1, rwy_end=e.get('end'), dep_src=e['src'], kind=kind, loc=lab, loc_detail=det,
                              hold_osm_id=None if not hold else hold[0], hold_m=None if not hold else round(hold[1], 1),
                              cls=a['cls'], type=a['type'], cat=a['cat'], feed=Counter(a['src'][i] for i in r).most_common(1)[0][0],
                              n=len(r), tower='open' if C.tower_open(a['t'][r[0]]) else 'closed', _hex=e['hex']))
    # clusters
    from scipy.cluster.hierarchy import linkage, fcluster
    P = np.array([[h['x'], h['z']] for h in holds])
    lab = fcluster(linkage(P, 'complete'), t=CL_DIAM_M, criterion='distance') if len(P) > 1 else np.ones(len(P), int)
    cl = []
    for k in sorted(set(lab)):
        M = [h for h, l in zip(holds, lab) if l == k]
        cx = float(np.median([h['x'] for h in M])); cz = float(np.median([h['z'] for h in M]))
        mid = [(h['dur_lo'] + (h['dur_hi'] if h['dur_hi'] is not None else h['dur_lo'])) / 2 for h in M]
        cl.append(dict(x=round(cx, 2), z=round(cz, 2), radius=round(max(math.hypot(h['x'] - cx, h['z'] - cz) for h in M), 2),
                       n=len(M), n_aircraft=len(set(h['_hex'] for h in M)), kinds=dict(Counter(h['kind'] for h in M).most_common()),
                       loc_detail=Counter(str(h['loc_detail']) for h in M).most_common(1)[0][0],
                       rwy_ends=dict(Counter(h['rwy_end'] or '?' for h in M).most_common()),
                       classes=dict(Counter(h['cls'] for h in M).most_common()),
                       dur_mid_median_s=round(float(np.median(mid))), dur_lo_median_s=round(float(np.median([h['dur_lo'] for h in M]))),
                       order_1_share=round(sum(h['order'] == 1 for h in M) / len(M), 2), src='obs'))
    cl.sort(key=lambda c: -c['n'])
    for i, c in enumerate(cl): c['id'] = 'H%03d' % (i + 1)
    mids = [(h['dur_lo'] + (h['dur_hi'] if h['dur_hi'] is not None else h['dur_lo'])) / 2 for h in holds]
    out = {'what': 'Stops of 30 s - 10 min before departures at HWD (tools/adsb/runup_holds.py): run-up pads, hold-short lines, '
                   'line-up-and-wait. Positions = GNSS antenna, world frame (hwd_frame.py). Aggregates only (default D1).',
           'licence': C.LICENCE, 'attribution': C.ATTRIBUTION,
           'source': 'sfo3d/refs/cache/rec_pack/adsblol_<hour>.jsonl.xz @ %s' % C.PACK_COMMIT, 'hours': C.HOURS, 'frame': C.F.FRAME_ID,
           'rules': {k: v for k, v in dict(globals()).items() if k.isupper() and isinstance(v, (int, float))},
           'rules_text': __doc__.split('usage:')[0].strip(),
           'summary': {'departures': len(deps), 'departures_with_a_stop': sum(1 for e in deps if stops_before(T[e['hex']], roll_start(T[e['hex']], e))),
                       'stops': len(holds), 'by_kind': dict(Counter(h['kind'] for h in holds).most_common()),
                       'by_kind_order1': dict(Counter(h['kind'] for h in holds if h['order'] == 1).most_common()),
                       'by_rwy_end': dict(Counter(h['rwy_end'] or '?' for h in holds).most_common()),
                       'runup_apron_by_name': dict(Counter(h['loc_detail'] for h in holds if h['kind'] == 'runup_apron').most_common()),
                       'by_class': dict(Counter(h['cls'] for h in holds).most_common()),
                       'dur_mid_s_hist': EV.hist(mids, [0, 30, 60, 90, 120, 180, 240, 300, 420, 600, 900]),
                       'dur_lo_s_hist': EV.hist([h['dur_lo'] for h in holds], [0, 30, 60, 90, 120, 180, 240, 300, 420, 600, 900]),
                       'dur_hi_open': sum(h['dur_hi'] is None for h in holds), 'clusters': len(cl)},
           'clusters': cl,
           'hold_fields': {'dur_lo / dur_hi': 'observed lower / upper bound of the stop duration (s), rounded to %d s in this '
                                              'file (cluster medians and histograms use the unrounded values)' % DUR_ROUND_S,
                           'dep_src': 'obs / inf of the departure event (events.py)',
                           'feed': 'dominant ADS-B transport / source class (1090 / UAT / TIS-B); not the obs/inf src of the project'},
           'holds': [dict({k: v for k, v in h.items() if not k.startswith('_')},
                          dur_lo=_rnd(h['dur_lo']), dur_hi=_rnd(h['dur_hi'])) for h in sorted(holds, key=lambda h: (h['x'], h['z']))]}
    n = C.write_json(os.path.join(C.OUT_DIR, 'hwd_runup_holds.json'), out)
    print('departures %d, stops %d, clusters %d -> %d bytes' % (len(deps), len(holds), len(cl), n))
    print(out['summary'])
    for c in cl[:12]: print(c)


if __name__ == '__main__':
    main()
