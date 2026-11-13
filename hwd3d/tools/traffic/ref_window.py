#!/usr/bin/env python3
"""Reference data of one replay window for the offline traffic harness (tools/traffic/replay_engine.mjs). New (P3).

1. Offline event counts of the window: refs/cache/local/adsb/hwd_events_local.json (per-event rows of the Phase 1
   classifier tools/adsb/events.py; LOCAL ONLY, gitignored) filtered to events whose time lies in [from, until] of the
   pack -> counts by type, source and runway end. Only aggregate counts are written.
2. Leak list (D1 test): the identity strings - ICAO address, registration, callsign - of every aircraft flagged LADD or
   PIA (readsb dbFlags & 12) seen in the window's rec_pack hour(s) within the pack's radius. The harness checks that none
   of them appears in anything the engine outputs. The list holds per-aircraft identity, so it is written ONLY to
   hwd3d/out/traffic/ (gitignored: hwd3d/.gitignore 'out/') and never printed; the script prints counts.
usage: python3 -I hwd3d/tools/traffic/ref_window.py out/replay/pack_weekend_meta.json [--name weekend]
"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(HWD, 'tools', 'live')); sys.path.insert(0, os.path.join(HWD, 'tools', 'common'))
import recio  # noqa: E402
import hwd_frame as F  # noqa: E402

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('meta'); ap.add_argument('--name'); a = ap.parse_args()
    M = json.load(open(a.meta)); name = a.name or M['name']
    t0, t1 = M['from'], M['until']
    out = {'name': name, 'from': t0, 'until': t1, 'what': 'offline reference counts (tools/adsb/events.py events in the window)'}
    L = json.load(open(os.path.join(HWD, 'refs', 'cache', 'local', 'adsb', 'hwd_events_local.json')))['events']
    E = [e for e in L if t0 <= e['t'] <= t1]
    c = {}
    for e in E:
        r = c.setdefault(e['type'], {'total': 0, 'by_src': {}, 'by_end': {}})
        r['total'] += 1; r['by_src'][e['src']] = r['by_src'].get(e['src'], 0) + 1
        k = e.get('end') or '-'; r['by_end'][k] = r['by_end'].get(k, 0) + 1
    out['counts'] = dict(sorted(c.items())); out['events'] = len(E)
    out['aircraft_with_events'] = len(set(e['hex'] for e in E))
    # leak list
    R = M['center']['radius_nm'] * 1852.0; ids = set(); flagged = set()
    for h in M['source']['hours']:
        p = os.path.join(recio.REC_PACK, 'adsblol_%s.jsonl.xz' % h)
        for rec in recio.lines(p):
            for ac in ((rec.get('d') or {}).get('ac') or []):
                fl = ac.get('dbFlags') or 0
                if not (fl & 12) or ac.get('lat') is None: continue
                x, z = F.wgs84_to_world(ac["lat"], ac["lon"])
                if math.hypot(x, z) > R: continue
                flagged.add(ac['hex'])
                for k in ('hex', 'r', 'flight', 'ownOp'):
                    v = (ac.get(k) or '').strip()
                    if len(v) >= 3: ids.add(v.upper())
    os.makedirs(os.path.join(HWD, 'out', 'traffic'), exist_ok=True)
    json.dump(out, open(os.path.join(HWD, 'out', 'traffic', 'ref_%s.json' % name), 'w'), indent=1)
    json.dump({'note': 'LOCAL ONLY (gitignored out/): identity strings of LADD/PIA-flagged aircraft, for the D1 leak test', 'ids': sorted(ids)},
              open(os.path.join(HWD, 'out', 'traffic', 'leak_%s.json' % name), 'w'))
    print('%s: %d offline events in the window (%d aircraft); %d LADD/PIA-flagged aircraft, %d identity strings in the leak list'
          % (name, len(E), out['aircraft_with_events'], len(flagged), len(ids)))
    for k, v in out['counts'].items(): print('  %-24s %3d %s' % (k, v['total'], v['by_src']))

if __name__ == '__main__':
    main()
