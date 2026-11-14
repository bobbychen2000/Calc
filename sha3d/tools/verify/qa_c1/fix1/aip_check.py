"""Fix-round check for QA C1 M2 (counts only).
usage: python3 -I aip_check.py [SHA3D_DIR]   (default /home/user/Calc/sha3d)
The patterns for the removed AIP values are read from the local, git-ignored refs/cache/aip_checks/patterns/
fix1_removed.json (labels -> list of strings); without that file only the structural checks run."""
import json, os, sys
ROOT = sys.argv[1] if len(sys.argv) > 1 else '/home/user/Calc/sha3d'
A = json.load(open(os.path.join(ROOT, 'data/sha_airport.json')))
S = json.load(open(os.path.join(ROOT, 'data/sha_stands.json')))
src = open(os.path.join(ROOT, 'tools/airport/build_airport.py'), encoding='utf-8').read()
txt = json.dumps(A, ensure_ascii=False)
print('stands with an aip_status key:', sum('aip_status' in s for s in S['stands']),
      '| stands with a flag mentioning AIP:', sum('AIP' in str(s.get('flag', '')) for s in S['stands']),
      '| unplaced names:', len(S['unplaced']), '| counts keys:', sorted(S['counts']))
def nums(o):
    if isinstance(o, dict): return sum(nums(v) for k, v in o.items() if k not in ('notice', 'fields', 'used_by', 'src', 'refs'))
    if isinstance(o, list): return sum(nums(v) for v in o)
    return 1 if isinstance(o, (int, float)) and not isinstance(o, bool) else 0
for r in A['runways']:
    print(r['id'], 'aip_facts keys', sorted(r['aip_facts']), '| numeric AIP values in the block:', nums(r['aip_facts']),
          '| AIP-type keys left outside the block:', [k for k in r if k in ('length_m', 'width_m', 'strip_m', 'resa_m', 'stopway_m',
          'clearway_m', 'grooved', 'rel_taxiways', 'lights_remarks', 'surface', 'shoulder_m', 'blast_pad_m')],
          '| end keys:', sorted(r['ends'][0]))
# The removed values are AIP (mirror) content: their search patterns live in a LOCAL file (refs/cache/* is git-ignored),
# never in this committed script (re-verify N3, fix round 2).
PAT = os.path.join(ROOT, 'refs/cache/aip_checks/patterns/fix1_removed.json')
if os.path.exists(PAT):
    removed = json.load(open(PAT, encoding='utf-8'))['patterns']
else:
    removed = {}
    print('removed-value check skipped: no local pattern file', PAT)
import re
def hit(p, t):
    """numeric patterns match as whole tokens only (not inside a longer number such as a coordinate)"""
    if re.fullmatch(r'[\d.×x]+', p):
        return re.search(r'(?<![\d.])' + re.escape(p) + r'(?!\d|\.\d)', t) is not None
    return p in t
for k, pats in removed.items():
    print('%-16s in sha_airport.json: %-5s in build_airport.py: %s' % (k, any(hit(p, txt) for p in pats),
                                                                      any(hit(p, src) for p in pats)))
print('licence mentions "not covered by the ODbL":', 'not covered by the ODbL' in A['licence'])
