#!/usr/bin/env python3
"""Reference data of one replay window for the independent Phase 2 run (docs/phase2_run.md; QA only, not part of the app).
The OUTPUT holds per-aircraft identity strings (D1): write it ONLY under hwd3d/out/ (gitignored) or a scratch directory,
never into a committed file. It prints counts only.
- leak: identity strings (ICAO address, registration, callsign, ownOp, Mictronics registration) of every aircraft flagged
  LADD/PIA (readsb dbFlags & 12) seen within 8 NM of the HWD ARP in the window's rec_pack hour(s);
- ctrl: registrations / callsigns of UNflagged aircraft (positive control: the DOM scan must see some of them);
- offline: hexes (unflagged only) with Phase 1 offline HWD events inside [t0, t1], and the event counts by type.
Writes the JSON to OUT.json; prints counts only.
usage: python3 -I tools/qa/phase2_run_ref.py NAME FROM_ISO MINUTES out/phase2/ref_NAME.json
Needs the local-only working files refs/cache/local/registry/mictronics_lookup.json and
refs/cache/local/adsb/hwd_events_local.json (gitignored; a fresh clone cannot run it). Moved from docs/phase2/ to tools/qa/
in Phase 2 review fix round 1 (tools/ is never served by the relay) and given an output guard: OUT must lie under
hwd3d/out/ (not out/replay/, which the relay serves) or under the system temp directory.
"""
import sys, os, json, math, datetime as dt
HWD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))   # tools/qa -> hwd3d
sys.path.insert(0, os.path.join(HWD, 'tools', 'live')); sys.path.insert(0, os.path.join(HWD, 'tools', 'common'))
import recio  # noqa
import hwd_frame as F  # noqa

name, frm, minutes, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]


def _out_ok(path):
    import tempfile
    rp = os.path.realpath(path); outd = os.path.realpath(os.path.join(HWD, 'out'))
    tmp = os.path.realpath(tempfile.gettempdir())
    if rp.startswith(os.path.join(outd, 'replay') + os.sep): return False
    return rp.startswith(outd + os.sep) or rp.startswith(tmp + os.sep)


if not _out_ok(out):
    sys.exit('refused: the output holds identity strings (D1); write it under hwd3d/out/ (not out/replay/) or the temp directory, not %s' % out)
t0 = dt.datetime.fromisoformat(frm.replace('Z', '+00:00')).timestamp(); t1 = t0 + minutes * 60
R = 8 * 1852.0
hours = sorted({dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y%m%d_%H') for t in (t0, t1 - 1)})
MX = json.load(open(os.path.join(HWD, 'refs', 'cache', 'local', 'registry', 'mictronics_lookup.json')))['aircraft']
flag_hex, leak, ctrl, allhex = set(), set(), set(), set()
types = {}
for h in hours:
    p = os.path.join(recio.REC_PACK, 'adsblol_%s.jsonl.xz' % h)
    for rec in recio.lines(p):
        for ac in ((rec.get('d') or {}).get('ac') or []):
            if ac.get('lat') is None: continue
            x, z = F.wgs84_to_world(ac['lat'], ac['lon'])
            if math.hypot(x, z) > R: continue
            hx = (ac.get('hex') or '').lower(); allhex.add(hx)
            fl = ac.get('dbFlags') or 0
            if fl & 12: flag_hex.add(hx)
for h in hours:
    p = os.path.join(recio.REC_PACK, 'adsblol_%s.jsonl.xz' % h)
    for rec in recio.lines(p):
        for ac in ((rec.get('d') or {}).get('ac') or []):
            if ac.get('lat') is None: continue
            x, z = F.wgs84_to_world(ac['lat'], ac['lon'])
            if math.hypot(x, z) > R: continue
            hx = (ac.get('hex') or '').lower()
            vals = [(ac.get(k) or '').strip().upper() for k in ('hex', 'r', 'flight', 'ownOp')]
            if hx in flag_hex:
                for v in vals:
                    if len(v) >= 3: leak.add(v)
                m = MX.get(hx.upper()) or MX.get(hx)
                if m and m[0] and len(m[0]) >= 3: leak.add(m[0].upper())
            else:
                for v in vals[1:3]:
                    if len(v) >= 3: ctrl.add(v)
# a string shared by a flagged and an unflagged aircraft (e.g. a generic operator name) cannot be told apart in the DOM
amb = sorted(leak & ctrl)
E = json.load(open(os.path.join(HWD, 'refs', 'cache', 'local', 'adsb', 'hwd_events_local.json')))['events']
W = [e for e in E if t0 <= e['t'] <= t1]
cnt = {}
for e in W: cnt[e['type']] = cnt.get(e['type'], 0) + 1
ev_hex = sorted({e['hex'].lower() for e in W if e['hex'].lower() not in flag_hex})
json.dump({'note': 'LOCAL ONLY - identity strings for the D1 DOM scan; never commit', 'name': name, 'from': t0, 'until': t1, 'hours': hours,
           'leak': sorted(leak), 'ambiguous': amb, 'ctrl': sorted(ctrl), 'flagged_n': len(flag_hex), 'aircraft_n': len(allhex),
           'offline_counts': dict(sorted(cnt.items())), 'offline_hex': ev_hex, 'offline_n_aircraft': len({e['hex'] for e in W})}, open(out, 'w'))
print(json.dumps({'name': name, 'hours': hours, 'aircraft_within_8nm': len(allhex), 'flagged': len(flag_hex), 'leak_strings': len(leak),
                  'ambiguous': len(amb), 'ctrl_strings': len(ctrl), 'offline_events': len(W), 'offline_counts': cnt,
                  'offline_aircraft_unflagged': len(ev_hex)}))
