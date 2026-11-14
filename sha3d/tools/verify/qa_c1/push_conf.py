import sys, json, math, numpy as np
sys.path.insert(0, '/home/user/Calc/sha3d/tools/common'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/airport')
import frame as F
from acplan import planform, CLS_REF
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json')); T = json.load(open('/home/user/Calc/sha3d/data/sha_taxigraph.json'))
by = {s['name']: s for s in S['stands']}
def pf(s):
    _, L, span, w, sw = CLS_REF[s['cls']]
    f = F.hdg_vec(s['hdg']); r = (-f[1], f[0]); nose = s['nose']
    return unary_union([Polygon([(nose[0] + u * f[0] + v * r[0], nose[1] + u * f[1] + v * r[1]) for u, v in p]) for p in planform(L, span, w, sw)])
P = {n: pf(s) for n, s in by.items()}
names = list(P); tree = STRtree([P[n] for n in names])
hits = []
for l in T['links']:
    if l['kind'] != 'push': continue
    me = l['ref']; ch = LineString(l['pts'])
    # aircraft path: the push moves the aircraft from its stand position to the junction; sweep the fuselage axis line
    # (nose point path) -> test against other stands' planforms (excluding own group)
    grp = set([me] + by[me]['excl'])
    others = [names[j] for j in tree.query(ch) if names[j] not in grp and P[names[j]].intersects(ch)]
    if others: hits.append((me, round(l['len']), others))
print('push links whose nose path crosses another stand\'s reference planform:', len(hits), 'of', sum(1 for l in T['links'] if l['kind'] == 'push'))
for h in hits[:25]: print('  ', h)
# primary lead-in vs leadins in taxigraph: does any lead-in (arrival path) cross other stands' planforms?
li_hits = []
for li in T['leadins']:
    ls = LineString(li['pts']); me = li['ref']; grp = set([me] + by[me]['excl'])
    o = [names[j] for j in tree.query(ls) if names[j] not in grp and P[names[j]].intersection(ls).length > 5]
    if o: li_hits.append((me, o))
print('primary lead-ins crossing another stand\'s planform by > 5 m:', len(li_hits), li_hits[:15])
