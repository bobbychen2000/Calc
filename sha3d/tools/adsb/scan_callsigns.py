#!/usr/bin/env python3
"""OD2 tier 2 ("observed elsewhere"): stream one adsb.lol globe_history day (GitHub release adsblol/globe_history_2026,
ODbL 1.0) and keep, for East/South-East Asia (lat 0-60 N, lon 60-180 E), every civil flight as a short summary, plus the
thinned track of every flight whose callsign is on a Hongqiao (ZSSS) or Pudong (ZSPD) route in the VRS standing data
(CC0), or that was seen from take-off to landing (calibration set for the timing model).

Streaming is the same as globe_scan.py (curl of the split .tar parts, tarfile in stream mode, ~3.5 GiB per day).
Nothing else is written. Military / PIA / LADD aircraft (readsb dbFlags & 1, 4, 8) are dropped before anything is kept.

usage: python3 -I tools/adsb/scan_callsigns.py 2026.11.12 OUT_DIR VRS_INDEX.json.gz [prod|staging]
Output (LOCAL ONLY, per-flight identities): OUT_DIR/cs_<date>_<kind>.json.gz =
  {date, source, n_traces_scanned, n_traces_box, n_skipped_flags, vrs_commit,
   flights: [{id, icao, r, t, desc, ownOp, year, cs, why, dep, arr, segs, n, alt_max}],   # summaries, all callsigns
   detail: {id: [[t, lat, lon, alt, gs, trk, vrate], ...] per part}}                         # selected flights only
"""
import gzip, json, os, re, sys, tarfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from globe_scan import Pipe, stream          # noqa: E402  (same streaming as the Phase 0 scan)
import legs                                   # noqa: E402

BOX = (0.0, 60.0, 60.0, 180.0)                # lat0, lat1, lon0, lon1
PRE = re.compile(rb"\n\[[\d.]+,(?:[0-5]?\d)\.\d+,(?:[6-9]\d|1[0-7]\d)\.")
SKIP_FLAGS = 1 | 4 | 8                        # military, PIA, LADD


def main():
    date, out, vrs_path = sys.argv[1], sys.argv[2], sys.argv[3]
    kind = sys.argv[4] if len(sys.argv) > 4 else 'prod'
    with gzip.open(vrs_path, 'rt') as f:
        vrs = json.load(f)
    sha = {cs for cs, (al, rt) in vrs['routes'].items() if 'ZSSS' in rt.split('-')}
    pvg = {cs for cs, (al, rt) in vrs['routes'].items() if 'ZSPD' in rt.split('-')}
    aps = legs.Airports(vrs['airports'])
    t0 = time.time(); n = nbox = nskip = 0; flights = []; detail = {}
    tf = tarfile.open(fileobj=Pipe(stream(date, kind)), mode='r|')
    for m in tf:
        if not m.isfile() or '/traces/' not in '/' + m.name.lstrip('./'):
            continue
        n += 1
        raw = tf.extractfile(m).read()
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
        if not PRE.search(raw):
            continue
        d = json.loads(raw)
        if (d.get('dbFlags') or 0) & SKIP_FLAGS:
            nskip += 1
            continue
        pts = [p for p in legs.points(d) if BOX[0] <= p[1] < BOX[1] and BOX[2] <= p[2] < BOX[3]]
        if not pts:
            continue
        nbox += 1
        for fl in legs.flights(pts, aps):
            cs = fl['cs']
            why = []
            if cs in sha: why.append('sha_route')
            if cs in pvg: why.append('pvg_route')
            if fl['dep'] and fl['arr'] and fl['dep']['ap'] != fl['arr']['ap']:
                why.append('both_ends')
            fid = len(flights)
            flights.append({'id': fid, 'icao': d.get('icao'), 'r': d.get('r'), 't': d.get('t'), 'desc': d.get('desc'),
                            'ownOp': d.get('ownOp'), 'year': d.get('year'), 'cs': cs, 'why': why, 'dep': fl['dep'],
                            'arr': fl['arr'], 'segs': fl['segs'], 'n': fl['n'], 'alt_max': fl['alt_max']})
            if why:
                detail[fid] = [legs.thin(p) for p in fl['parts']]
        if n % 20000 == 0:
            print(f'  {n} traces, {nbox} in box, {len(flights)} flights, {time.time()-t0:.0f}s', flush=True)
    res = {'date': date, 'source': f'adsb.lol globe_history {kind} (ODbL 1.0), release v{date}-planes-readsb-{kind}-0',
           'box': BOX, 'n_traces_scanned': n, 'n_traces_box': nbox, 'n_skipped_flags': nskip,
           'vrs_commit': vrs.get('commit'), 'flights': flights, 'detail': detail}
    os.makedirs(out, exist_ok=True)
    with gzip.open(os.path.join(out, f'cs_{date}_{kind}.json.gz'), 'wt') as f:
        json.dump(res, f, separators=(',', ':'))
    k = sum(1 for x in flights if 'sha_route' in x['why'])
    print(f'{date} {kind}: scanned {n} traces, {nbox} in box ({nskip} skipped by dbFlags), {len(flights)} flights, '
          f'{k} on SHA routes, {len(detail)} with detail, {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
