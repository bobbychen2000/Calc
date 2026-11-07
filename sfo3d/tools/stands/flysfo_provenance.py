#!/usr/bin/env python3
"""Exactly which committed stand values derive from flysfo.com (SFO AODB) responses -> refs/cache/stands/flysfo_provenance.json.

Why (static round 3, 2026-11-05, lead's request on static-v5): the flysfo responses stay local (refs/cache/gate_truth/:
no published terms; listed with their SHA-256 in refs/MANIFEST.json). The stand generators are reproducible from
committed files (tools/stands/patch_stands.py: base build + P1 / P2 replay), but some of those committed files carry
values DERIVED from flysfo. This tool lists them, per file / stand / field, so that an owner decision on the flysfo
licence can be applied exactly (keep, or strip these and re-run), and it says which P1 additions ADS-B alone supports.

Sources of flysfo-derived values (read from the code that writes them):
  A. refs/cache/stands/sfo_stands_built_20260926.json = the BASE of data/sfo_stands.json (tools/stands/build_stands.py on
     the 14 flysfo snapshots of 24-25 Sep 2026 - lost on 2026-11-04, so the base cannot be regenerated):
     names / aodb (SFO's AODB stand names; name_src), classes (cls, cls_src 'sfo types', largest_type, span_max, len_max
     where the class came from SFO's plans), obs_types (SFO final-plan types UNION ADS-B types, build_stands.py; the
     split is in the lost stands_built.json), superseded_types / conflict_superseded, types_ok / types_ok_all_paths /
     tight_with / below_icao (neighbours SFO plans simultaneously), ADS-B evidence tied to SFO stand windows (resid.adsb,
     verified_by 'adsb', type_stops, conflict with adsb, stops_rejected).
  B. refs/cache/stands/patch_p1p2_replay.json (P1 / P2 on the local 4 Nov 18:01Z snapshot and, since close-out round 3
     (2026-11-06), the 5 Nov 02:49Z one): obs_types_aodb2 (types and SFO flight numbers), the P1 changes of obs_types /
     cls / cls_src / span_max / len_max / types_ok, excl_types, their fixup notes. patch_stands.py P8 (round 3) widens
     types_ok by family dominance - derived from these whitelists, so flysfo-derived too.
  C. refs/cache/stands/adsb_parked.json (tools/stands/adsb_parked.py): per stay the SFO match (stand, gate, flight,
     callsign, match, win, overlap_s, sfo_type). Since round 3 NO generator reads them: patch_stands.py P5 selects stays
     by geometry (on the stand's lead-in) and ADS-B type; paint_pave_naip.py identifies aircraft by ADS-B type / airline
     callsign.
Not flysfo: positions / headings / bridges (OSM, NAIP), P3-P7, the pavement / paint / details / landside data.
Usage: python3 tools/stands/flysfo_provenance.py
"""
import json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import patch_stands as PS  # noqa: E402

OUT = os.path.join(ROOT, 'refs', 'cache', 'stands', 'flysfo_provenance.json')
BASE_FIELDS = {   # field -> how build_stands.py derives it from the AODB (A.)
    'aodb': 'SFO AODB stand names served by the stand', 'name_src': 'SFO AODB stand name (with DataSF gate number)',
    'cls_src': 'class from the largest type SFO plans (cls_src starts with "sfo")', 'largest_type': 'largest SFO-planned type',
    'obs_types': 'SFO final-plan types UNION ADS-B parked types', 'superseded_types': 'types of superseded SFO plans',
    'conflict_superseded': 'superseded SFO plans vs the class', 'types_ok': 'whitelist from neighbours SFO plans simultaneously',
    'types_ok_all_paths': 'whitelist applies on SFO\'s allocation path', 'tight_with': 'neighbours SFO plans simultaneously',
    'below_icao': 'simultaneously planned pairs below the ICAO clearance', 'type_stops': 'ADS-B stops of stays matched to SFO windows',
    'stops_rejected': 'ADS-B stops of stays matched to SFO windows', 'conflict': 'ADS-B stays matched to SFO windows disagree',
}
ADSB_MATCH_FIELDS = ('stand', 'gate', 'flight', 'callsign', 'match', 'win', 'overlap_s', 'sfo_type')


def nonempty(v): return v not in (None, [], {}, '', False)


def main():
    D = json.load(open(PS.OUT + '.json')); R = json.load(open(PS.P12_REPLAY)); st = json.load(open(PS.ADSB_STAYS))['stays']
    per = {}
    for s in D['stands']:
        f = {}
        for k, why in BASE_FIELDS.items():
            v = s.get(k)
            if k == 'cls_src' and not str(v or '').startswith('sfo'): continue
            if k == 'name_src' and 'aodb' not in str(v or '').lower() and 'sfo' not in str(v or '').lower(): continue
            if nonempty(v): f[k] = 'base (Sep snapshots, lost): ' + why
        if (s.get('resid') or {}).get('adsb'): f['resid.adsb'] = 'base: ADS-B stays matched to SFO stand windows'
        if 'adsb' in (s.get('verified_by') or []): f['verified_by'] = 'base: "adsb" = stays matched to SFO stand windows'
        if s.get('cls_src', '').startswith('sfo'):
            f['cls'] = f['span_max'] = f['len_max'] = 'base (Sep snapshots, lost): class / limits from SFO-planned types'
        for k in (R['stands'].get(s['name']) or {}):
            f[k] = '4 Nov snapshot (local; replayed from refs/cache/stands/patch_p1p2_replay.json)' + (' - P1 / P2 change' if k in f else '')
        if f: per[s['name']] = f
    # P1 additions that ADS-B alone (geometric stays on the stand's lead-in, ADS-B type) corroborates
    fam_ok = defaultdict(set)
    for s in D['stands']:
        for v in st:
            t = v.get('type')
            if not t or not PS.dims(t): continue
            a, c = PS.local((v['x'], v['z']), s['nose'], s['hdg'])
            if abs(c) <= 1.5 and -45 < a < 8 and (v.get('hdg') is None or abs(PS.hdiff(v['hdg'], s['hdg'])) <= 10): fam_ok[s['name']].add(PS.ALIAS_T.get(t, t))
    p1 = []
    for n, r in sorted(R['stands'].items()):
        for t in sorted(r.get('obs_types_aodb2') or {}):
            p1.append({'stand': n, 'type': t, 'adsb_geometric': PS.ALIAS_T.get(t, t) in fam_ok.get(n, set())})
    adsb = [{'hex': v['hex'], 't0': v['t0'], **{k: v.get(k) is not None for k in ADSB_MATCH_FIELDS}} for v in st if v.get('stand') or v.get('flight')]
    out = {'what': 'committed values derived from flysfo.com (SFO AODB) responses; tool tools/stands/flysfo_provenance.py (see its header)',
           'snapshots_local': {'september_base': 'flysfo_api_flight-status_202609{24,25}*.json.gz (14 snapshots; LOST 2026-11-04)',
                               'patch_P1_P2': PS.FLYSFO_WINDOW2},
           'data/sfo_stands.json': {'stands_with_flysfo_fields': len(per), 'of': len(D['stands']), 'per_stand': per,
                                    'other': ['fixups[] entries of P1 / P2', 'remote[] / unplaced[] names and types (AODB stand list)']},
           'refs/cache/stands/patch_p1p2_replay.json': 'whole file (P1 / P2 results incl. SFO flight numbers in obs_types_aodb2)',
           'refs/cache/stands/sfo_stands_built_20260926.json': 'the base: the fields of A. (header)',
           'refs/cache/stands/adsb_parked.json': {'fields': list(ADSB_MATCH_FIELDS), 'stays_with_sfo_match': len(adsb), 'of': len(st),
                                                  'read_by_generators': 'none since round 3 (patch_stands P5 geometric; paint_pave_naip identity by ADS-B)'},
           'p1_types_adsb_corroborated': {'n': sum(r['adsb_geometric'] for r in p1), 'of': len(p1), 'rows': p1},
           'needs_local_snapshot_to_regenerate': ['patch_stands.py P1 / P2 live mode (--check); otherwise replayed',
                                                  'tools/stands/adsb_parked.py (the SFO match fields of C.)',
                                                  'tools/stands/build_stands.py (also needs the lost Sep snapshots / recording)']}
    json.dump(out, open(OUT, 'w'), indent=1)
    print('stands with flysfo-derived fields: %d of %d; P1 types corroborated by ADS-B geometry: %d of %d; adsb_parked stays with an SFO match: %d of %d' % (
        len(per), len(D['stands']), out['p1_types_adsb_corroborated']['n'], len(p1), len(adsb), len(st)))
    print('wrote', os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
