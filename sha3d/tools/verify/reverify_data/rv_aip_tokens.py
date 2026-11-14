"""M2 / OD3: distinctive AIP (mirror) tokens in every committable text file, outside the AIP-notice blocks of the data
files. Counts per file and category only; never prints a value. usage:
python3 -I rv_aip_tokens.py SHA3D_DIR COMMITTABLE_LIST"""
import sys, os, os, re, json, gzip
from collections import Counter, defaultdict
ROOT = sys.argv[1]; files = [l.strip() for l in open(sys.argv[2]) if l.strip()]
files += ['sha3d/refs/cache/osm_pinned/' + f for f in sorted(os.listdir(os.path.join(ROOT, 'refs/cache/osm_pinned')))]
M = os.path.join(ROOT, 'refs/cache/aip/derived_aip_zsss')
txt = open(os.path.join(M, 'ad2_tables.txt'), encoding='utf-8').read() + '\n' + open(os.path.join(M, 'ad2_right_column.txt'), encoding='utf-8').read()
PAT = {
    'dimension AxB': r'\b\d{2,4}\s?[×x]\s?\d{2,4}\b',
    'PCR code': r'PCR\s?\d{3,4}/[RF]/[ABCD]/[WXYZ]/T',
    'frequency': r'\b1[1-3]\d\.\d{1,3}\b',
    'DMS coordinate': r'\bN\d{6}(?:\.\d+)?\s?E\d{7}(?:\.\d+)?\b',
    'slope %(len)': r'-?\d\.\d{1,2}\s?%\(\s?\d{2,4}m\)',
    'MAG bearing': r'\b\d{3}°\s?MAG\b',
    'GEO bearing': r'\b\d{3}\.\d{2}°\s?GEO\b',
    'TDZ elevation': r'TDZ\s\d\.\dm',
    'TL/TA': r'\bT[LA]\s\d{4}m',
}
tok = {k: set(m.group(0) for m in re.finditer(p, txt)) for k, p in PAT.items()}
# normalise for matching (spaces, x/×)
def norm(s): return re.sub(r'\s+', '', s).replace('x', '×')
ntok = {k: {norm(t) for t in v} for k, v in tok.items()}
print('mirror tokens per category:', {k: len(v) for k, v in tok.items()})
def strip_blocks(o):
    """remove dicts that carry the AIP notice"""
    if isinstance(o, dict):
        if isinstance(o.get('notice'), str) and 'AIP' in o['notice']:
            return '<AIP-BLOCK>'
        return {k: strip_blocks(v) for k, v in o.items()}
    if isinstance(o, list):
        return [strip_blocks(v) for v in o]
    return o
res = defaultdict(Counter); scanned = 0
for f in files:
    p = os.path.join(os.path.dirname(ROOT), f)
    if not os.path.isfile(p):
        continue
    ext = os.path.splitext(f)[1].lower()
    try:
        if f.endswith('.gz'):
            t = gzip.open(p, 'rt', encoding='utf-8', errors='replace').read()
        elif ext in ('.json', '.geojson', '.js', '.md', '.py', '.txt', '.csv', '.tsv', '.sh', '.html', '.svg', '') or f.endswith('.gitignore'):
            t = open(p, encoding='utf-8', errors='replace').read()
        else:
            continue
    except Exception:
        continue
    scanned += 1
    if ext == '.json' and f.startswith('sha3d/data/sha_'):
        t = json.dumps(strip_blocks(json.loads(t)), ensure_ascii=False)
    elif ext == '.js' and f.startswith('sha3d/data/sha_'):
        j = t[t.index('{'): t.rindex('}') + 1]
        t = json.dumps(strip_blocks(json.loads(j)), ensure_ascii=False)
    for k, p_ in PAT.items():
        for m in re.finditer(p_, t):
            if norm(m.group(0)) in ntok[k]:
                res[f][k] += 1
print('files scanned:', scanned)
for f, c in sorted(res.items()):
    print('  %-70s %s' % (f, dict(c)))
# stand list reconstruction
S = json.load(open(os.path.join(ROOT, 'data/sha_stands.json')))
AS = json.load(open(os.path.join(M, 'stands.json')))
aip = set(AS['stands']) if isinstance(AS['stands'], (list, dict)) else set()
osm = {s['name'] for s in S['stands']}; unp = {u['name'] for u in S['unplaced']}
osm_only = osm - aip
print('AIP designators %d; OSM names %d; unplaced %d; OSM-only (not in AIP) %d; unplaced == AIP - OSM: %s'
      % (len(aip), len(osm), len(unp), len(osm_only), unp == (aip - osm)))
print('sha_stands.json alone: any per-stand field telling AIP membership:', any(k for s in S['stands'] for k in s if 'aip' in k.lower()))
for f in files:
    p = os.path.join(os.path.dirname(ROOT), f)
    if not os.path.isfile(p) or os.path.splitext(f)[1] not in ('.md', '.json', '.js', '.py'):
        continue
    t = open(p, encoding='utf-8', errors='replace').read()
    n = sum(1 for d in osm_only if re.search(r'(?<![\w.])%s(?![\w.])' % re.escape(d), t))
    if n >= 10:
        print('  file naming >= 10 of the %d OSM-only designators: %s (%d)' % (len(osm_only), f, n))
