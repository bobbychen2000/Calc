import json, re
A = json.load(open('/home/user/Calc/sha3d/refs/cache/aip/derived_aip_zsss/stands.json'))
O = json.load(open('/home/user/Calc/sha3d/refs/cache/aip/derived_aip_zsss/obstacles.json'))
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json'))
aip = set(A['stands']); print('AIP designators', len(aip), 'keys', list(A.keys()))
matched = {s['name'] for s in S['stands'] if s['aip_status'] == 'aip+osm'}
unpl = {u['name'] for u in S['unplaced']}
recon = matched | unpl
print('reconstructable from committed sha_stands.json:', len(recon), 'equal to AIP list:', recon == aip, 'missing', sorted(aip - recon), 'extra', sorted(recon - aip))
# VDGS
v = A.get('vdgs_stands'); print('vdgs type', type(v).__name__, len(v) if v else None)
vset = set(v) if isinstance(v, list) else set(v.keys()) if isinstance(v, dict) else set()
for fld in ('contact', 'bridge_status'):
    vals = {}
    for s in S['stands']:
        vals.setdefault(str(s.get(fld)), set()).add(s['name'])
    for k, names in vals.items():
        print(fld, k, len(names), 'of which VDGS', len(names & vset))
# wingspan limits per stand
w = A.get('wingspan_limit_m'); print('wingspan_limit type', type(w).__name__, len(w) if w else None)
if isinstance(w, dict):
    def num(x):
        m = re.findall(r'[\d.]+', str(x)); return float(m[-1]) if m else None
    eq = sum(1 for s in S['stands'] if s['span_max'] is not None and s['name'] in w and num(w[s['name']]) is not None and abs(num(w[s['name']]) - s['span_max']) < 0.05)
    from collections import Counter
    print('AIP limit value kinds', Counter(re.sub(r'[\d.]+','N',str(x)) for x in w.values()))
    print('stands whose committed span_max equals the AIP limit:', eq, 'span_max non-null:', sum(1 for s in S['stands'] if s['span_max'] is not None))
    print('sample', list(w.items())[:5])
# Obstacles: how many AIP obstacle rows appear in committed airport json
D = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
txt = json.dumps(D, ensure_ascii=False)
hits = 0
for o in O:
    pat = f"{o['dist_m']}"
    if re.search(r'\b%s\b' % re.escape(str(o['dist_m'])), txt) and re.search(r'\b%s\b' % re.escape(str(o['elev_m'])), txt):
        hits += 1
print('AIP obstacle rows (114) whose dist and elevation both appear in sha_airport.json:', hits)
# frequencies
for fn in ['/home/user/Calc/sha3d/data/sha_airport.json', '/home/user/Calc/sha3d/data/sha_stands.json', '/home/user/Calc/sha3d/data/sha_taxigraph.json']:
    t = open(fn).read()
    fr = sorted(set(re.findall(r'\b1[1-3]\d\.\d{1,3}\b(?= ?MHz)', t)))
    print(fn.split('/')[-1], 'MHz frequencies:', fr[:20], 'aip_mirror mentions', t.count('AIP (mirror)'))
