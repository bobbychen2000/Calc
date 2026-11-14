import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
sys.path.insert(0, '.'); sys.path.insert(0, '/home/user/Calc/sha3d/tools/common')
import frame as F
T = json.load(open('/home/user/Calc/sha3d/data/sha_taxigraph.json'))
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json'))
N = {n['id']: n for n in T['nodes']}; L = T['links']
# integrity
ids = [n['id'] for n in T['nodes']]; print('node ids unique', len(ids) == len(set(ids)))
bad_end = 0; zero = 0; lenmis = []
for l in L:
    a, b = N[l['a']], N[l['b']]
    p = l['pts']
    if math.dist(p[0], (a['x'], a['z'])) > 0.05 or math.dist(p[-1], (b['x'], b['z'])) > 0.05: bad_end += 1
    pl = sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))
    if pl < 0.5: zero += 1
    if abs(pl - l['len']) > 0.5: lenmis.append((l['id'], l['kind'], l['len'], round(pl, 1)))
print('links whose pts do not start/end at their nodes:', bad_end, '| links < 0.5 m:', zero, '| len mismatches:', len(lenmis), lenmis[:5])
deg = Counter()
for l in L: deg[l['a']] += 1; deg[l['b']] += 1
dead = [n for n in N if deg[n] == 1 and N[n]['kind'] == 'junction']
print('junction dead ends (degree 1):', len(dead))
print('isolated nodes:', [n for n in N if deg[n] == 0])
# duplicate nodes within 0.5 m
P = np.array([(N[i]['x'], N[i]['z']) for i in ids])
from scipy.spatial import cKDTree
pairs = cKDTree(P).query_pairs(0.5)
print('node pairs closer than 0.5 m (not merged):', len(pairs), [(ids[i], ids[j], N[ids[i]]['kind'], N[ids[j]]['kind']) for i, j in list(pairs)[:8]])
# directed adjacency
def adj(mode, allow_runway=False):
    G = defaultdict(list)
    for l in L:
        if l['status'] != 'open': continue
        if l['kind'] == 'runway' and not allow_runway: continue
        if l['kind'] == 'push':
            if mode == 'dep': G[l['a']].append((l['b'], l['len'], l['id']))
            continue
        if mode == 'dep' and l['use'] not in ('all', 'departure'): continue
        if mode == 'arr' and l['use'] not in ('all', 'arrival'): continue
        G[l['a']].append((l['b'], l['len'], l['id']))
        if l['dir'] == 'both': G[l['b']].append((l['a'], l['len'], l['id']))
    return G
def dijkstra(G, src, block_stands=True):
    d = {src: 0}; prev = {}; pq = [(0, src)]
    while pq:
        c, u = heapq.heappop(pq)
        if c > d[u]: continue
        if block_stands and u != src and N[u]['kind'] == 'stand': continue   # never route through another stand
        for v, w, lid in G[u]:
            if c + w < d.get(v, 1e18):
                d[v] = c + w; prev[v] = (u, lid); heapq.heappush(pq, (c + w, v))
    return d, prev
stand_node = {N[i].get('name') or N[i].get('ref') or N[i].get('stand'): i for i in N if N[i]['kind'] == 'stand'}
print('stand node keys sample', list(stand_node)[:3], [N[i] for i in N if N[i]['kind'] == 'stand'][:1])
rwy_nodes = defaultdict(set)
for i, n in N.items():
    if n['kind'] in ('rwy', 'rwy_end'): rwy_nodes[n['runway']].add(i)
Gd = adj('dep'); Ga = adj('arr')
fail_dep = Counter(); fail_arr = Counter()
stand_ids = [i for i in N if N[i]['kind'] == 'stand']
# departures: stand -> any node of each runway, without runway links
for sid in stand_ids:
    d, _ = dijkstra(Gd, sid)
    for r, nodes in rwy_nodes.items():
        if not any(x in d for x in nodes): fail_dep[r] += 1
# arrivals: from any runway node -> stand (reverse search from stand on reversed arrival graph)
Gr = defaultdict(list)
for u, lst in Ga.items():
    for v, w, lid in lst: Gr[v].append((u, w, lid))
for sid in stand_ids:
    d, _ = dijkstra(Gr, sid)
    for r, nodes in rwy_nodes.items():
        if not any(x in d for x in nodes): fail_arr[r] += 1
print('stands that cannot depart to a runway (no runway links used):', dict(fail_dep), '| cannot arrive from:', dict(fail_arr))
json.dump({'stand_ids': stand_ids}, open('graph_meta.json', 'w'))
