"""Names, ids and tag values: can a dropped feature be found by text? Prints counts only.
usage: python3 -I rv2_names.py COMMITTABLE_LIST     (list of repo-relative paths, one per line; SHA3D_DIR optional)
1. every tag value of every kept feature of the pinned extract (all keys, linear features included, relation members
   resolved) against the sensitive regexes of tools/law/osm_sensitive.py and against the names of the dropped
   features (tag rule and second-order drops), whole name and distinctive parts;
2. kept relations that list a dropped element in their raw member list, by relation type;
3. every committable text file: dropped names / name parts, dropped element ids (whole numbers), and the ids of
   vertex nodes that belong only to dropped ways;
4. kept enforcement / camera-like tags the tag rule does not cover (speed cameras, enforcement relations, surveillance
   keys without man_made=surveillance);
5. a broad keyword scan of kept tag values (terms beyond the tag rule), by feature class and key.
Details (which name, which file) go to refs/cache/reverify_data2/names_local.json only.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv2_common as C  # noqa: E402

REPO = os.path.abspath(os.path.join(C.ROOT, '..'))
LIST = [l.strip() for l in open(sys.argv[1]) if l.strip()]
raw = C.Raw()
feats, els, ext = C.load_pinned()
CN = C.committed_nodes(raw, ext)   # kept ways' vertices as committed (fix round 3: rule g)
pinned = {(f['typ'], f['id']) for f in feats}
inv = json.load(open(os.path.join(C.LOCAL, 'inventory_local.json')))
NAME_KEYS = ('name', 'official_name', 'alt_name', 'old_name', 'short_name', 'operator', 'brand', 'designation', 'ref',
             'loc_name', 'int_name')


def names_of(t):
    return [v for k, v in t.items() if v and (k in NAME_KEYS or k.startswith('name:'))]


# generic place prefixes and organisation words removed before matching (a fixed, general list)
CUTS = ('上海市', '上海', '闵行区', '长宁区', '青浦区', '嘉定区', '普陀区', '有限公司', '股份', '集团', '管理局', '分局',
        '委员会', '办事处')
GENERIC = re.compile(r'^(公司|中心|大厦|大楼|广场|花园|小区|新村|路|街|号|门|站|线|区|市|局|队|园|院|所|校|楼)$')


def parts(name):
    """distinctive parts of a name: the whole name, CJK runs of >= 3 characters with generic affixes removed, and
    Latin words of >= 5 letters that are not generic"""
    out = {name}
    for run in re.findall(r'[一-鿿0-9]+', name):
        for cut in CUTS:
            run = run.replace(cut, '|')
        for p in run.split('|'):
            if len(p) >= 3 and not GENERIC.match(p):
                out.add(p)
    for w in re.findall(r'[A-Za-z]{5,}', name):
        if w.lower() not in ('shanghai', 'station', 'company', 'limited', 'road', 'street', 'district', 'office',
                             'prison', 'police', 'military', 'armed', 'detention'):   # class words of osm_sensitive.py
            out.add(w)
    return out


secret_names = {'tag_rule': set(), 'second_order': set()}
for grp in ('tag_rule', 'second_order'):
    for d in inv[grp]:
        for n in names_of(d['tags'] or {}):
            secret_names[grp] |= parts(n)
# 1. tag values of kept features
c1 = Counter()
loc1 = []
for f in feats:
    t = f['tags']
    for k, v in t.items():
        if not isinstance(v, str):
            continue
        if C.S._ZH.search(v) or C.S._EN.search(v) or C.S._PLA.search(v):
            c1['regex hit (%s)' % ('linear' if any(x in t for x in ('highway', 'railway', 'waterway')) or
                                   t.get('type') in ('route', 'route_master', 'public_transport') else 'other')] += 1
            loc1.append(dict(kind='regex', key=k, value=v, feat=(f['typ'], f['id'], C.cls(t))))
        for grp, S in secret_names.items():
            hit = [s for s in S if s in v]
            if hit:
                c1['dropped-name part in a kept tag value (%s)' % grp] += 1
                loc1.append(dict(kind='name_' + grp, key=k, value=v, parts=hit, feat=(f['typ'], f['id'], C.cls(t))))
print('1. kept tag values:', dict(c1) or 0)
# 2. relations with dropped members
c2 = Counter()
loc2 = []
dropped_ids = {(t, i) for (t, i) in raw.drop}
second_ids = {(d['typ'], d['id']) for d in inv['second_order']}
for rid, mem in raw.R.items():
    if ('relation', rid) not in pinned:
        continue
    dm = [(t, ref) for t, ref, role in mem if (t, ref) in dropped_ids or (t, ref) in second_ids]
    if dm:
        c2[raw.RT[rid].get('type', '?') + '/' + str(raw.RT[rid].get('route') or raw.RT[rid].get('boundary') or '')] += 1
        loc2.append(dict(rel=rid, tags=raw.RT[rid], dropped_members=dm))
print('2. kept relations with a dropped element in the raw member list:', dict(c2) or 0)
kept_rel_members = Counter()
for f in feats:
    if f['typ'] == 'relation' and 'members' in f['props']:
        for t, ref, role in f['props']['members']:
            if (t, ref) in dropped_ids or (t, ref) in second_ids:
                kept_rel_members['dropped element listed as a member of a kept relation'] += 1
print('   members listed in the pinned extract that are dropped:', dict(kept_rel_members) or 0)
# 3. committable text files
kept_nodes = {i for i, v in els['node']}
drop_way_nodes = set()
for (t, i) in list(dropped_ids) + list(second_ids):
    if t == 'way' and i in raw.W:
        drop_way_nodes.update(raw.W[i])
kept_way_nodes = set()
for f in feats:
    if f['typ'] == 'way':
        kept_way_nodes.update(CN.get(f['id'], []))
only_dropped_nodes = drop_way_nodes - kept_way_nodes - kept_nodes
id_tokens = {('tag_rule', str(i)) for t, i in dropped_ids} | {('second_order', str(i)) for t, i in second_ids} | \
    {('vertex_only_dropped', str(i)) for i in only_dropped_nodes}
id_re = re.compile(r'(?<![0-9.])[0-9]{6,12}(?![0-9])')
id_map = defaultdict(set)
for g, s in id_tokens:
    id_map[s].add(g)
c3 = Counter()
loc3 = []
nfiles = 0
for rel in LIST:
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p) or os.path.getsize(p) > 50e6:
        continue
    try:
        txt = open(p, encoding='utf-8').read()
    except (UnicodeDecodeError, OSError):
        continue
    nfiles += 1
    for grp, S in secret_names.items():
        for s in S:
            if s in txt:
                c3['%s name part in a committable file' % grp] += 1
                loc3.append(dict(file=rel, grp=grp, part=s, n=txt.count(s)))
    for m in set(id_re.findall(txt)):
        for g in id_map.get(m, ()):
            c3['%s id in a committable file' % g] += 1
            loc3.append(dict(file=rel, grp=g, id=m))
print('3. %d committable text files scanned:' % nfiles, dict(c3) or 0)
print('   (%d name parts from tag-rule drops, %d from second-order drops; %d ids, %d vertex-only nodes)' % (
    len(secret_names['tag_rule']), len(secret_names['second_order']), len(dropped_ids) + len(second_ids),
    len(only_dropped_nodes)))
# 4. camera / enforcement tags not covered by the tag rule
c4 = Counter()
for f in feats:
    t = f['tags']
    if t.get('highway') == 'speed_camera' or t.get('type') == 'enforcement' or t.get('enforcement'):
        c4['speed camera / enforcement'] += 1
    if any(k.startswith('surveillance') or k.startswith('camera') for k in t):
        c4['surveillance:* / camera:* key'] += 1
    if any('military' in str(v).lower() or 'police' in str(v).lower() for v in t.values()):
        c4['value containing military / police'] += 1
    if t.get('access') in ('military', 'official'):
        c4['access=military/official'] += 1
print('4. camera / enforcement-like kept tags:', dict(c4) or 0)
# 5. broad keyword scan (terms beyond the tag rule: border / immigration / radar / security ...), by feature class
BROAD = re.compile(r'军|警|国防|国家安全|安全局|保密|机要|雷达|边检|边防|武装|看守|拘留|戒毒|监狱|兵|营区|移民管理|出入境|navy|air ?force|'
                   r'barrack|defen[cs]e|armed|police|military|prison|jail|detention|gnss|cors|radar|immigration|border|'
                   r'security', re.I)
c5 = Counter()
for f in feats:
    for k, v in f['tags'].items():
        if isinstance(v, str) and BROAD.search(v):
            c5['%s (key %s)' % (C.cls(f['tags']), k)] += 1
print('5. broad keyword scan of kept tag values:', dict(c5) or 0)
C.save_local('names_local.json', dict(tag_values=loc1, relations=loc2, files=loc3))
