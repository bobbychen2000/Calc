#!/usr/bin/env python3
"""Aggregate FAA-registry statistics for the aircraft seen ON the HWD field in the adsb.lol recordings (no identities).

New for hwd3d (task G3c, 2026-11-12). The on-field definition and the per-aircraft attribute collection are copied from
hwd3d/tools/phase0/hwd_mix.py (Phase 0, base a967f9b) so the aircraft set is the same 243 aircraft:
  * ARP 37.65893166, -122.12173888 (NASR APT_BASE 2026-10-29), field elevation FE = 52 ft (AL-5015 / NASR 52.1);
  * a fix counts only with lat/lon and a usable alt_baro ('ground' -> FE);
  * box: within 5,556 m (3 nm) of the ARP and at or below FE + 3,000 ft; attributes (registration r, type t, dbFlags)
    are collected over all box fixes;
  * ON FIELD: at least one fix within 1,500 m of the ARP and below FE + 150 ft.
  `--onfield-only` reruns just this part and prints the count (Phase 0 measured 243) - no registry needed.

Join: the adsb.lol registration `r` (if it starts with 'N') against the registry lookup; otherwise the ICAO address
(hex, not '~'-prefixed) against the registry's Mode S hex. Both joins and their disagreements are counted.

Output (committable, aggregates only - default D1: no N-number, hex, callsign or owner):
  refs/cache/adsb/registry_mix_summary.json
Input: refs/cache/local/registry/registry_lookup.json (build_lookup.py), sfo3d/refs/cache/rec_pack/adsblol_*.jsonl.xz.
Licence of the output: contains information from ADSB.lol (ODbL 1.0) and the FAA registry (public domain).

usage: python3 -I hwd3d/tools/registry/registry_mix.py [--onfield-only] [--rec DIR] [--lookup PATH] [--out PATH]
"""
import argparse
import collections as C
import datetime as dt
import glob
import json
import lzma
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = os.path.dirname(HWD)
REC = os.path.join(REPO, 'sfo3d', 'refs', 'cache', 'rec_pack')
LOOKUP = os.path.join(HWD, 'refs', 'cache', 'local', 'registry', 'registry_lookup.json')
OUT = os.path.join(HWD, 'refs', 'cache', 'adsb', 'registry_mix_summary.json')
ARP = (37.65893166, -122.12173888)   # NASR APT_BASE 2026-10-29 (as hwd_mix.py)
FE = 52                              # ft, field elevation (as hwd_mix.py)
BOX_M, BOX_FT = 5556, 3000           # 3 nm, 3000 ft AGL (as hwd_mix.py)
FIELD_M, FIELD_FT = 1500, 150        # on field: < 1.5 km and < 150 ft AGL (as hwd_mix.py)


def dist(lat, lon):   # same flat-earth formula as hwd_mix.py
    dy = (lat - ARP[0]) * 111195
    dx = (lon - ARP[1]) * 111195 * math.cos(math.radians(ARP[0]))
    return math.hypot(dx, dy)


def onfield_aircraft(rec_dir):
    files = sorted(glob.glob(os.path.join(rec_dir, 'adsblol_*.jsonl.xz')))
    ac = {}
    for f in files:
        for line in lzma.open(f, 'rt'):
            r = json.loads(line)
            if r.get('code') != 200:
                continue
            for a in r['d'].get('ac', []):
                if 'lat' not in a:
                    continue
                d = dist(a['lat'], a['lon'])
                alt = a.get('alt_baro')
                altv = FE if alt == 'ground' else (alt if isinstance(alt, (int, float)) else None)
                if d > BOX_M or altv is None or altv > BOX_FT + FE:
                    continue
                x = ac.setdefault(a['hex'], {'r': set(), 't': set(), 'flags': 0, 'field': 0})
                if a.get('r'):
                    x['r'].add(a['r'])
                if a.get('t'):
                    x['t'].add(a['t'])
                x['flags'] |= a.get('dbFlags', 0)
                if d < FIELD_M and altv < FE + FIELD_FT:
                    x['field'] += 1
    return {h: x for h, x in ac.items() if x['field'] > 0}, files


def label(codes, group, code):
    c = codes.get(group, {}).get(str(code)) if code not in (None, '') else None
    if c is None:
        return '(blank)' if code in (None, '') else 'code %s (no label)' % code
    return c['label'] + ('' if c['verified'] else ' [label unverified]')


def summarise(onf, lk):
    codes = lk['codes']
    n_tab, hex_tab, models = lk['n'], lk['hex'], lk['models']
    res = C.Counter()
    rows = []          # (icao_type, registry row) for resolved aircraft; never written out per aircraft
    for h, x in onf.items():
        regs = sorted(r for r in x['r'] if r.upper().startswith('N'))
        by_reg = next((r.upper() for r in regs if r.upper() in n_tab), None)
        by_hex = hex_tab.get(h.lower()) if not h.startswith('~') else None
        if by_reg and by_hex and by_reg != by_hex:
            res['registration_and_hex_disagree'] += 1
        nn = by_reg or by_hex
        if by_reg:
            res['resolved_by_registration'] += 1
        elif by_hex:
            res['resolved_by_hex_only'] += 1
        elif h.startswith('~'):
            res['unresolved_anonymous_or_non_icao_address'] += 1
        elif x['r'] and not regs:
            res['unresolved_non_N_registration'] += 1
        elif regs:
            res['unresolved_N_registration_not_in_registry'] += 1
        else:
            res['unresolved_no_registration_hex_not_in_registry'] += 1
        if x['flags'] & 8:
            res['ladd_flagged'] += 1
            if nn:
                res['ladd_flagged_resolved'] += 1
        if nn:
            rows.append(('/'.join(sorted(x['t'])) or '(none)', n_tab[nn]))
    cnt = lambda it: dict(C.Counter(it).most_common())
    mm = lambda row: ('%s %s' % (models[row[0]][0], models[row[0]][1])).strip() or '(no ACFTREF row)'
    by_type = C.defaultdict(C.Counter)
    for t, row in rows:
        by_type[t][mm(row)] += 1
    n = len(onf)
    resolved = res['resolved_by_registration'] + res['resolved_by_hex_only']
    return {
        'n_onfield_aircraft': n,
        'resolution': dict(res, share_resolved=round(resolved / n, 4) if n else None),
        'mfr_model': cnt(mm(r) for _, r in rows),
        'icao_type_to_faa_model': {t: dict(c.most_common()) for t, c in sorted(by_type.items())},
        'type_aircraft': cnt(label(codes, 'type_aircraft', r[2]) for _, r in rows),
        'type_engine': cnt(label(codes, 'type_engine', r[3]) for _, r in rows),
        'registrant_type': cnt(label(codes, 'registrant_type', r[4]) for _, r in rows),
        'no_eng': cnt(str(models[r[0]][2]) for _, r in rows),
        'no_seats': cnt(str(models[r[0]][3]) for _, r in rows),
        'year_mfr_decade': cnt(('%ds' % (r[1] // 10 * 10)) if r[1] else '(blank)' for _, r in rows),
        'code_labels': codes.get('_note'),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--onfield-only', action='store_true', help='only count the on-field aircraft (no registry needed)')
    ap.add_argument('--rec', default=REC)
    ap.add_argument('--lookup', default=LOOKUP)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    if not a.onfield_only and not os.path.exists(a.lookup):
        sys.exit('missing %s: run fetch_registry.py and build_lookup.py first' % a.lookup)
    onf, files = onfield_aircraft(a.rec)
    print('recordings: %d files; on-field aircraft: %d (Phase 0 hwd_mix.py: 243)' % (len(files), len(onf)))
    if a.onfield_only:
        return
    lk = json.load(open(a.lookup))
    s = summarise(onf, lk)
    s = {'made_by': 'hwd3d/tools/registry/registry_mix.py %s' % dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d'),
         'inputs': {'recordings': '%s (%d files)' % (os.path.relpath(a.rec, REPO), len(files)),
                    'registry_zip_sha256': lk['input']['zip_sha256'],
                    'registry_members': {k: v for k, v in lk['input']['members'].items()
                                         if k in ('MASTER.txt', 'ACFTREF.txt')}},
         'onfield_definition': 'as hwd3d/tools/phase0/hwd_mix.py: >=1 fix < %d m from the ARP and < FE+%d ft '
                               '(alt_baro ground = FE %d ft); attributes over fixes < %d m and <= FE+%d ft'
                               % (FIELD_M, FIELD_FT, FE, BOX_M, BOX_FT),
         'privacy': 'aggregates only (default D1): no N-number, ICAO hex, callsign or owner name',
         **s}
    with open(a.out, 'w') as f:
        json.dump(s, f, indent=1)
    print('wrote', a.out, 'share resolved', s['resolution']['share_resolved'])


if __name__ == '__main__':
    main()
