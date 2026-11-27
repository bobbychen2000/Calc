#!/usr/bin/env python3
"""LOCAL ONLY (OD4): the identity overlay of one operating day from the gitignored observed-elsewhere tables.

  python3 -I tools/sim/observed_overlay.py --day 2026-11-12      prints the Overlay JSON on stdout (never writes a file)
  python3 -I tools/sim/observed_overlay.py --days                prints the days that have a local file

Reads refs/cache/observed_elsewhere/sha_observed_<day>.json and emits ONLY the allow-listed fields of design s.3 / s.7.1:

  {v: 1, day, tier: 'oe', note: 'observed elsewhere, SHA time inferred', licence, records: [{uid, role, airline, cs, flight,
   reg, type, operator, far, t_sha, sigma_s}]}

- only records with consistency in {track_consistent, far_end_match} and a t_sha;
- 'type' is copied from the source field 't' (ICAO type designator). The source field 'icao' is the 24-bit ADDRESS and is
  never read; nor are evidence, segs, first, last, est, src (review M12);
- 'flight' = IATA flight number from the callsign through data/lookup.js AIRLINES (ICAO -> 'Name|IATA');
- uid = '<day>:<index in the source list>' (an archive position, not an identity).

The relay (sha_live_server.py GET /api/observed_elsewhere?day=) imports this file by path. Nothing here is committed data:
the output must stay in memory, on the loopback relay, or under out/ (gitignored).
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))                 # sha3d/
OBS_DIR = os.path.join(ROOT, 'refs', 'cache', 'observed_elsewhere')
CONSISTENT = ('track_consistent', 'far_end_match')
FIELDS = ('uid', 'role', 'airline', 'cs', 'flight', 'reg', 'type', 'operator', 'far', 't_sha', 'sigma_s')
DAY_RX = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TYPE_RX = re.compile(r'^[A-Z][A-Z0-9]{1,3}$')
HEX24_RX = re.compile(r'^[0-9a-f]{6}$')   # lowercase: the source writes addresses lowercase; IATA numbers such as CAnnnn may be hex-like in upper case
LICENCE = 'ODbL 1.0 (adsb.lol), VRS CC0, Mictronics ODC-By'
NOTE = 'observed elsewhere, SHA time inferred'
_AL = None


def airlines():
    global _AL
    if _AL is None:
        with open(os.path.join(ROOT, 'data', 'lookup.js'), encoding='utf-8') as f:
            s = f.read()
        m = re.search(r'export const AIRLINES = (\{.*?\});', s, re.S)
        _AL = json.loads(m.group(1)) if m else {}
    return _AL


def flight_of(cs):
    """IATA flight number from an airline callsign (CESnnnn -> MUnnnn); None if the prefix has no IATA designator"""
    m = re.match(r'^([A-Z]{3})(\d{1,4}[A-Z]?)$', (cs or '').strip())
    if not m:
        return None
    v = airlines().get(m.group(1))
    if not v or '|' not in v:
        return None
    iata = v.split('|')[1].strip()
    num = m.group(2).lstrip('0') or '0'
    return iata + num if re.match(r'^[A-Z0-9]{2}$', iata) else None


def days(obs_dir=OBS_DIR):
    out = []
    try:
        for f in sorted(os.listdir(obs_dir)):
            m = re.match(r'^sha_observed_(\d{4}-\d{2}-\d{2})\.json$', f)
            if m:
                out.append(m.group(1))
    except OSError:
        pass
    return out


def overlay(day, obs_dir=OBS_DIR):
    """-> Overlay dict, or None when there is no local file for that day (or the day is malformed)"""
    if not DAY_RX.match(day or '') or day not in days(obs_dir):
        return None
    with open(os.path.join(obs_dir, f'sha_observed_{day}.json'), encoding='utf-8') as f:
        d = json.load(f)
    recs = []
    for i, m in enumerate(d.get('movements') or []):
        if m.get('consistency') not in CONSISTENT or m.get('t_sha') is None:
            continue
        t = (m.get('t') or '').strip().upper()
        if not TYPE_RX.match(t):
            continue
        cs = (m.get('cs') or '').strip() or None
        r = {'uid': f'{day}:{i}', 'role': m.get('role'), 'airline': m.get('airline'), 'cs': cs, 'flight': flight_of(cs),
             'reg': (m.get('r') or '').strip() or None, 'type': t, 'operator': m.get('operator') or None,
             'far': m.get('far') or None, 't_sha': int(round(float(m['t_sha']))), 'sigma_s': int(round(float(m.get('sigma_s') or 0)))}
        if r['role'] not in ('arr', 'dep'):
            continue
        # never a 6-hex value in any string field (the 24-bit address must not travel, review M12)
        if any(isinstance(v, str) and HEX24_RX.match(v) for k, v in r.items()):
            continue
        recs.append({k: r[k] for k in FIELDS})
    return {'v': 1, 'day': day, 'tier': 'oe', 'note': NOTE, 'licence': LICENCE, 'records': recs}


def main():
    ap = argparse.ArgumentParser(description='local identity overlay (OD4: never commit its output)')
    ap.add_argument('--day')
    ap.add_argument('--days', action='store_true')
    a = ap.parse_args()
    if a.days:
        print(json.dumps(days()))
        return
    o = overlay(a.day)
    sys.stdout.write(json.dumps(o if o is not None else {'available': False}, separators=(',', ':'), ensure_ascii=False))


if __name__ == '__main__':
    main()
