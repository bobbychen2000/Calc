"""M2: where AIP-derived content sits in the data files, outside blocks that carry the AIP notice. Prints paths and
value types / counts only (no AIP values). usage: python3 -I rv_aip_struct.py SHA3D_DIR"""
import sys, os, json, re
from collections import Counter, defaultdict
ROOT = sys.argv[1]
def has_notice(d):
    return isinstance(d, dict) and isinstance(d.get('notice'), str) and 'AIP' in d['notice']
def aip_marked(d):
    if not isinstance(d, dict): return False
    refs = d.get('refs') or []
    s = ' '.join(str(d.get(k, '')) for k in ('src', 'evidence', 'height_src', 'width_src', 'rule', 'note', 'name_note', 'height_evidence', 'width_note'))
    return 'aip_mirror' in refs or 'AIP' in s
out = defaultdict(Counter); blocks = Counter()
def walk(o, path, inblock, marked):
    if isinstance(o, dict):
        if has_notice(o):
            blocks[re.sub(r'\[\d+\]', '[]', path)] += 1; inblock = True
        m = marked or aip_marked(o)
        for k, v in o.items():
            p = path + '.' + k
            if isinstance(v, (dict, list)):
                walk(v, p, inblock, m)
            else:
                if not inblock and (m or 'aip' in k.lower()):
                    out[re.sub(r'\[\d+\]', '[]', path)][(k, type(v).__name__)] += 1
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, '%s[%d]' % (path, i), inblock, marked)
for fn in ('sha_airport.json', 'sha_stands.json', 'sha_taxigraph.json'):
    D = json.load(open(os.path.join(ROOT, 'data', fn)))
    out.clear(); blocks.clear()
    walk(D, '', False, False)
    print('=====', fn, '| blocks with the AIP notice:', dict(blocks))
    for p, c in sorted(out.items()):
        keys = [k for (k, t) in c if t in ('int', 'float') and k not in ('x', 'z', 'area_m2', 'len_m', 'reach_m')]
        print('  %-55s numeric keys: %s' % (p[:55], sorted(set(keys))[:14]))
