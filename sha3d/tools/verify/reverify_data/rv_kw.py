"""Keyword / per-flight pattern scan of every committable file (counts per file only).
usage: python3 -I rv_kw.py REPO_DIR COMMITTABLE_LIST"""
import sys, os, re, json, gzip
from collections import Counter
REPO = sys.argv[1]; files = [l.strip() for l in open(sys.argv[2]) if l.strip()]
files += ['sha3d/refs/cache/osm_pinned/' + f for f in sorted(os.listdir(os.path.join(REPO, 'sha3d/refs/cache/osm_pinned')))]
sys.path.insert(0, os.path.join(REPO, 'sha3d/tools/law'))
import osm_sensitive as S
ZH = S._ZH; EN = S._EN
REG = re.compile(r'\bB-[0-9][0-9A-Z]{3}\b')                       # PRC registrations
CS = re.compile(r'\b(?:CES|CSH|CQH|DKH|CCA|CSN|CXA|CHH|CSZ|HXA|JYH|CDG|OKA|SJO|EPA)\d{1,4}[A-Z]?\b')   # callsigns
HEX = re.compile(r'"(?:hex|icao24|icao)"\s*:\s*"[0-9a-f]{6}"', re.I)
rows = []
for f in files:
    p = os.path.join(REPO, f)
    if not os.path.isfile(p):
        continue
    try:
        if f.endswith('.gz'):
            t = gzip.open(p, 'rt', encoding='utf-8', errors='replace').read()
        elif os.path.splitext(f)[1].lower() in ('.json', '.geojson', '.js', '.md', '.py', '.txt', '.csv', '.tsv', '.sh', '.html', '.svg') or f.endswith('.gitignore'):
            t = open(p, encoding='utf-8', errors='replace').read()
        else:
            continue
    except Exception:
        continue
    c = Counter()
    c['zh'] = len(ZH.findall(t)); c['en'] = len(EN.findall(t)); c['reg'] = len(REG.findall(t)); c['callsign'] = len(CS.findall(t)); c['hex'] = len(HEX.findall(t))
    if any(c.values()):
        rows.append((f, dict((k, v) for k, v in c.items() if v)))
for f, c in rows:
    print('%-72s %s' % (f, c))
# the pinned extract: tag rule on every kept feature, and names
G = json.load(open(os.path.join(REPO, 'sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson')))
print('pinned features matching the tag rule:', sum(1 for f in G['features'] if S.sensitive_reason(f['properties'].get('tags', {}))))
nm = Counter()
for f in G['features']:
    t = f['properties'].get('tags', {})
    for k, v in t.items():
        if (k.startswith('name') or k in ('operator', 'official_name', 'alt_name', 'brand', 'description', 'note')) and (ZH.search(v) or EN.search(v)):
            nm[next((kk for kk in ('highway', 'railway', 'waterway', 'route', 'public_transport', 'building', 'amenity', 'landuse') if kk in t), 'other')] += 1
print('pinned features whose name / operator matches a sensitive term, by class:', dict(nm))
