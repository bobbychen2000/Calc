# broad keyword / tag scan over every committed or committable data file (counts + matched tag key=value only)
import json, re, sys, os, glob
from collections import Counter
sys.path.insert(0, '/home/user/Calc/sha3d/tools/law'); import osm_sensitive as S
BROAD = re.compile(r'军|警|国防|国家安全|安全局|保密|机要|雷达|边检|边防|武装|看守|拘留|戒毒|监|兵|营区|navy|air ?force|barrack|defen[cs]e|armed|police|military|prison|jail|detention|gnss|cors|surveillance|radar|border|customs|immigration|security|安检|海关|移民', re.I)
files = ['/home/user/Calc/sha3d/refs/cache/osm_pinned/zsss_osm_pinned.geojson', '/home/user/Calc/sha3d/data/sha_airport.json',
         '/home/user/Calc/sha3d/data/sha_stands.json', '/home/user/Calc/sha3d/data/sha_taxigraph.json'] + sorted(glob.glob('/home/user/Calc/sha3d/data/meas/*.json')) + ['/home/user/Calc/sha3d/data/SOURCES_airport.json','/home/user/Calc/sha3d/data/SOURCES_stands.json']
for fn in files:
    d = json.load(open(fn))
    hits = Counter(); tagdicts = 0; sens = Counter()
    def walk(o, path=''):
        global tagdicts
        if isinstance(o, dict):
            # candidate tag dicts: contain OSM-ish keys
            if any(k in o for k in ('building','highway','aeroway','amenity','landuse','name','man_made','railway','waterway','office')):
                r = S.sensitive_reason({k: str(v) for k, v in o.items() if isinstance(v, (str, int, float))})
                if r: sens[r] += 1
            for k, v in o.items():
                if isinstance(v, str) and BROAD.search(v) and k not in ('licence','what','note','evidence','dropped_note','filter_note'):
                    hits[(k, BROAD.search(v).group(0).lower())] += 1
                walk(v, path + '/' + str(k))
        elif isinstance(o, list):
            for v in o: walk(v, path)
    walk(d)
    print(os.path.basename(fn), 'rule-sensitive:', dict(sens), '| broad keyword hits (key, term):', dict(hits.most_common(20)))
