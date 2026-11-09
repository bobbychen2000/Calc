"""Where AIRCRAFT have been on the ground at SFO: ADS-B ground fixes of the committed adsb.lol hours, binned in 5 m cells ->
refs/cache/stands/adsb_ground_cells.json (own output; derived from adsb.lol data, ODbL 1.0 - docs/ATTRIBUTION.md).

Why (close-out round 3, finding static-1): tools/imagery/paint_pave_naip.py lets NAIP 2024 decide pavement only inside a
candidate region (60 m round SFO Museum pavement / the inferred apron, OSM aprons, 40 m round OSM taxi centrelines, 60 m
round parking positions and the 4 Nov 17:43-21Z parked stays). The largest single off-pavement case of the realtime
all-hours replay (verify2 realtime: offpave.mask / .union 369,812 frames of 1,375,584 / 471,479) is UAL2480 B752 parked
for hours on the light concrete maintenance apron at (-1383, -1917): NAIP shows smooth grey pavement there, but no
source put it in the candidate region (no OSM apron, no stay in the 17:43-21Z window). Every cell an aircraft has stood
or taxied in is evidence that NAIP may decide there; NAIP still decides (grey + smooth, never a footprint).

Input: refs/cache/rec_pack/adsblol_<hour>.jsonl.xz (committed, ODbL; tools/cache/sync.py) - the HOURS pinned below, so
the output reproduces from the repository. adsb.fi records are not read (their terms forbid licensing derived data).
Fix selection: an aircraft (ICAO type `t` that is not a readsb vehicle / obstacle pseudo-type, paint_pave_naip
NOT_AIRCRAFT; or ADS-B emitter category A1-A7), on the ground (alt_baro 'ground'), position age <= 2 s, NACp >= 8
(EPU < 30 m; most SFO ground fixes are NACp 9-10, < 10 m), within 4 km of the ARP. Each (hex, cell) pair counts once per
10 s (a parked aircraft does not dominate). Output cells: [x, z] (cell centre, world m), n (fix count), a (aircraft).
Close-out round 7 (2026-11-09, realtime request C5.3): also `signal_end` - where an aircraft's position signal ENDED on the
ground: its last fix of the selection above with gs < SIG_GS kt, followed by no fresh position fix of that aircraft (any
altitude, seen_pos <= 5 s) for >= SIG_GAP_S within the pinned hours (the app keeps such an aircraft parked at that point
for hours: ASA503 B39M, 5 Nov 05:22Z, (-2090.5, -687.3), silent for 661 min). These points have one or two fixes (the
transponder goes off at the stop), so the cells above cannot show them. Rows [x, z, hex, type, callsign, t (unix s),
silent_s (to the next fix or the end of the pinned hours)]; paint_pave_naip uses them as parking footprints (inferred).
Usage: python3 tools/imagery/adsb_ground_cells.py
"""
import json, lzma, math, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

PACK = os.path.join(ROOT, 'refs', 'cache', 'rec_pack')
OUT = os.path.join(ROOT, 'refs', 'cache', 'stands', 'adsb_ground_cells.json')
# the complete adsb.lol hours in rec_pack/ on 2026-11-06 (4 Nov 17Z - 6 Nov 03Z); pinned for reproducibility
HOURS = ['20261104_%02d' % h for h in range(17, 24)] + ['20261105_%02d' % h for h in range(24)] + ['20261106_%02d' % h for h in range(4)]
CELL = 5.0
SIG_GAP_S = 1800.0   # s: silence after the last ground fix that makes it a signal end (close-out round 7)
SIG_GS = 3.0         # kt: the last fix is (almost) stationary
NOT_AIRCRAFT = {'SERV', 'GRND', 'EMER', 'TWR', 'BALL', 'UAV', 'SHIP', 'GYRO', 'ULAC', 'GLID', 'PARA'}
AIRCRAFT_CAT = {'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'}


def is_aircraft(a):
    t = a.get('t')
    if t: return t not in NOT_AIRCRAFT
    return a.get('category') in AIRCRAFT_CAT


def main():
    cells = defaultdict(lambda: [0, set()]); last = {}; n_rec = n_fix = 0; used = []
    lastpos = {}; lastgnd = {}; sig = []; t_end = None   # round 7: hex -> last fresh fix time / last qualifying ground fix
    for h in HOURS:
        fn = os.path.join(PACK, 'adsblol_%s.jsonl.xz' % h)
        if not os.path.exists(fn): print('missing hour', h); continue
        used.append(h)
        with lzma.open(fn, 'rt') as f:
            for line in f:
                try: r = json.loads(line)
                except ValueError: continue
                d = r.get('d') or {}; n_rec += 1
                t_end = r['t'] if t_end is None else max(t_end, r['t'])
                for a in d.get('ac') or d.get('aircraft') or []:
                    if 'lat' in a and (a.get('seen_pos') or 0) <= 5 and a.get('hex'):
                        tp = r['t'] - (a.get('seen_pos') or 0); g = lastgnd.get(a['hex'])
                        lp = lastpos.get(a['hex'], -1e18)
                        if tp > lp + 1.0:      # a new fix (a fix is repeated while seen_pos grows)
                            if g and abs(g[5] - lp) <= 1.0 and tp - lp >= SIG_GAP_S: sig.append(g + [round(tp - g[5])])
                            lastpos[a['hex']] = tp
                    if a.get('alt_baro') != 'ground' or 'lat' not in a or (a.get('seen_pos') or 0) > 2: continue
                    if (a.get('nac_p') or 0) < 8 or not is_aircraft(a): continue
                    x, z = GF.wgs84_to_world(a['lat'], a['lon'])
                    if math.hypot(x, z) > 4000: continue
                    k = (int(math.floor(x / CELL)), int(math.floor(z / CELL)))
                    t = r['t'] - (a.get('seen_pos') or 0)
                    if (a.get('gs') or 0) < SIG_GS: lastgnd[a['hex']] = [round(x, 1), round(z, 1), a['hex'], a.get('t'), (a.get('flight') or '').strip(), t]
                    else: lastgnd.pop(a['hex'], None)
                    if t - last.get((a['hex'], k), -1e9) < 10: continue
                    last[(a['hex'], k)] = t; c = cells[k]; c[0] += 1; c[1].add(a['hex']); n_fix += 1
    out = {'what': 'ADS-B ground fixes of aircraft at SFO in 5 m cells (tools/imagery/adsb_ground_cells.py); cell = [x, z] centre in the '
                   'world frame (js/geo.js), n = fixes (one per aircraft and cell per 10 s), a = distinct aircraft',
           'licence': 'ODbL 1.0 - derived from adsb.lol data (https://adsb.lol, ODbL); docs/ATTRIBUTION.md',
           'source': 'refs/cache/rec_pack/adsblol_<hour>.jsonl.xz', 'hours': used, 'frame': GF.FRAME_ID, 'cell_m': CELL,
           'selection': 'alt_baro ground, seen_pos <= 2 s, NACp >= 8, aircraft type (not a vehicle pseudo-type) or category A1-A7, < 4 km of the ARP',
           'records': n_rec, 'fixes': n_fix,
           'signal_end_what': 'close-out round 7: last ground fix (selection above, gs < %.0f kt) followed by >= %.0f s with no fresh position '
                              'fix of that aircraft in the pinned hours: [x, z, hex, type, callsign, t, silent_s]' % (SIG_GS, SIG_GAP_S),
           'signal_end': sorted(sig + [g + [round(t_end - g[5])] for h_, g in lastgnd.items() if abs(g[5] - lastpos.get(h_, -1e18)) <= 1.0 and t_end - g[5] >= SIG_GAP_S],
                                key=lambda q: (q[5], q[2])),
           'cells': [[round((k[0] + 0.5) * CELL, 1), round((k[1] + 0.5) * CELL, 1), v[0], len(v[1])] for k, v in sorted(cells.items())]}
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    print('%d hours, %d records, %d fixes, %d cells, %d signal ends -> %s' % (len(used), n_rec, n_fix, len(cells), len(out['signal_end']), os.path.relpath(OUT, ROOT)))


if __name__ == '__main__':
    main()
