"""Where aircraft have been on the ground at HWD: ADS-B ground fixes of the pinned adsb.lol hours binned in 5 m cells,
moving and stationary counted apart (taxi-path density) -> refs/cache/adsb/hwd_ground_cells.json (aggregates only,
default D1; derived from adsb.lol data, ODbL 1.0).

Forked from sfo3d/tools/imagery/adsb_ground_cells.py @ a967f9b. Kept: 5 m cells in the world frame, fix selection
(on the ground, position age seen_pos <= 2 s, NACp >= 8, an aircraft: ICAO type not a readsb vehicle / obstacle
pseudo-type (NOT_AIRCRAFT) or ADS-B emitter category A1-A7), one count per (aircraft, cell) per 10 s so a parked aircraft
does not dominate, cell = [x, z] centre + counts + distinct aircraft. Changed: input = refs/cache/local/adsb/hwd_tracks.pkl
(extract.py: the HOURS pinned in common.py, all 111 files of the pack, not the 34 SFO hours); frame = hwd_frame.py
wgs84_to_world; 'on the ground' = the ground flag or derive.py 'ground by kinematics' (airborne flag, h <= GK_H ft,
gs < GK_GS kt; units without weight-on-wheels input); radius 2.5 km of the HWD ARP (sfo3d 4 km); counts split into
moving (gs >= MOVE_GS kt) and stationary (gs < MOVE_GS or no gs) and helicopter fixes; the signal_end list is not
repeated here (parked_stays.py 'signal_edges' has it, without identities).
Cell row: [x, z, n_move, n_still, n_aircraft, n_heli]. n_aircraft is a count of distinct ICAO addresses (no address is
written).
usage: python3 -I hwd3d/tools/adsb/ground_cells.py
"""
import math, os, sys
from collections import defaultdict
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                              # noqa: E402
import derive as DV                                             # noqa: E402

CELL = 5.0
MOVE_GS = 1.0
MAX_SEEN = 2.0
MIN_NACP = 8
R_MAX = 2500.0
DEDUP_S = 10.0
NOT_AIRCRAFT = {'SERV', 'GRND', 'EMER', 'TWR', 'BALL', 'UAV', 'SHIP', 'GYRO', 'ULAC', 'GLID', 'PARA'}   # sfo3d list
AIRCRAFT_CAT = {'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'}


def is_aircraft(a):
    t = a.get('type')
    if t: return t not in NOT_AIRCRAFT
    return a.get('cat') in AIRCRAFT_CAT


def main():
    D = DV.load(); T = D['tracks']; cal = DV.calibrate(T)
    cells = defaultdict(lambda: [0, 0, set(), 0]); last = {}
    n_fix = n_kin = 0; skipped = defaultdict(int)
    for hx, a in T.items():
        if np.hypot(a['x'], a['z']).min() > R_MAX: continue
        if not is_aircraft(a): skipped['not aircraft'] += 1; continue
        a['hex'] = hx; DV.derive(a, cal)
        heli = a['cls'] == 'helicopter'
        for i in np.where(a['gk'])[0]:
            if a['seen'][i] > MAX_SEEN: continue
            if a['nacp'][i] < MIN_NACP: continue
            x, z = a['x'][i], a['z'][i]
            if math.hypot(x, z) > R_MAX: continue
            mv = not np.isnan(a['gs'][i]) and a['gs'][i] >= MOVE_GS
            k = (int(math.floor(x / CELL)), int(math.floor(z / CELL)))
            key = (hx, k, mv)
            if a['t'][i] - last.get(key, -1e9) < DEDUP_S: continue
            last[key] = a['t'][i]
            c = cells[k]; c[0 if mv else 1] += 1; c[2].add(hx); c[3] += heli
            n_fix += 1; n_kin += not a['g'][i]
    rows = [[round((k[0] + 0.5) * CELL, 1), round((k[1] + 0.5) * CELL, 1), v[0], v[1], len(v[2]), v[3]] for k, v in sorted(cells.items())]
    out = {'what': 'ADS-B ground fixes of aircraft at HWD in 5 m cells (tools/adsb/ground_cells.py); row = [x, z (cell centre, '
                   'world m, hwd_frame.py), n_move (fixes with gs >= %.0f kt), n_still, n_aircraft (distinct), n_heli '
                   '(helicopter fixes)]; one fix per aircraft, cell and moving/still state per %.0f s' % (MOVE_GS, DEDUP_S),
           'licence': C.LICENCE, 'attribution': C.ATTRIBUTION,
           'source': 'sfo3d/refs/cache/rec_pack/adsblol_<hour>.jsonl.xz @ %s' % C.PACK_COMMIT, 'hours': C.HOURS,
           'frame': C.F.FRAME_ID, 'cell_m': CELL,
           'selection': 'ground flag or ground by kinematics (derive.py GK_H %.0f ft / GK_GS %.0f kt), seen_pos <= %.0f s, NACp >= %d, '
                        'aircraft type (not a vehicle pseudo-type) or category A1-A7, <= %.0f m from the ARP' % (DV.GK_H, DV.GK_GS, MAX_SEEN, MIN_NACP, R_MAX),
           'note': 'positions are GNSS antenna positions (not the aircraft centre); NACp 10 parked-fix scatter p50 0.55 m, p90 1.5 m '
                   '(hwd_parked_stays.json position_noise_per_fix)',
           'fixes': n_fix, 'fixes_ground_by_kinematics': n_kin, 'cells': rows,
           'totals': {'cells': len(rows), 'n_move': int(sum(r[2] for r in rows)), 'n_still': int(sum(r[3] for r in rows)),
                      'n_heli': int(sum(r[5] for r in rows))}}
    n = C.write_json(os.path.join(C.OUT_DIR, 'hwd_ground_cells.json'), out, compact=True)
    print('%d fixes (%d by kinematics), %d cells -> %d bytes; totals %s' % (n_fix, n_kin, len(rows), n, out['totals']))


if __name__ == '__main__':
    main()
