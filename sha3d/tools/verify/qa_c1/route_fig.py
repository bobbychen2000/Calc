import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
src = open('graph_qa3.py').read()
exec(src.split("cnt = Counter()")[0])
from qa_plot import tci_img
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
Ga = adj('arr')
rx_nodes = {}
for r in T['runways']:
    for c in r['connections']:
        if c.get('rapid_exit_for'): rx_nodes.setdefault(c['rapid_exit_for'], []).append((c['node'], c.get('ref'), c['s_m']))
def route_pts(p, start):
    cur = start; pts = []
    for lid in p:
        l = Lb[lid]; q = l['pts'] if l['a'] == cur else l['pts'][::-1]; cur = l['b'] if l['a'] == cur else l['a']
        pts += q
    return np.array(pts)
# example A: arrival 36R via a rapid exit to a T1 west stand with reversal at H4/H1
ex_arr = None
for land in ('36R', '18L'):
    for n0, ref, s in sorted(rx_nodes[land], key=lambda q: str(q[1])):
        if not ref: continue
        d, prev = dijkstra(Ga, n0)
        for sid in stand_ids:
            p = path(prev, sid); jt = junction_turns(p, n0)
            if any(a > 120 and r == 'H4' for a, nn, k, r in jt): ex_arr = (n0, f'{ref} ({land})', sid, p, jt); break
        if ex_arr: break
    if ex_arr: break
# example B: departure 608 -> 18R
sid = next(i for i in stand_ids if N[i]['ref'] == '608'); d, prev = dijkstra(Gd, sid)
nodes, refs = ends['18R']; t = min([n for n in nodes if n in d], key=lambda n: d[n]); pB = path(prev, sid and t)
fig, axs = plt.subplots(1, 2, figsize=(18, 10))
for ax, (title, p, start) in zip(axs, ((f"arrival 36R: rapid exit {ex_arr[1]} -> stand {N[ex_arr[2]]['ref']} (shortest path)", ex_arr[3], ex_arr[0]), ("departure 608 -> 18R (shortest path after push)", pB, sid))):
    R = route_pts(p, start)
    x0, z0 = R.min(0) - 150; x1, z1 = R.max(0) + 150
    img, ext = tci_img('S2B', x0, z0, x1, z1, res=4.0)
    ax.imshow(img, extent=ext, interpolation='nearest')
    for l in L:
        q = np.array(l['pts']); c = {'taxiway': 'w', 'taxilane': 'c', 'leadin': 'y', 'push': 'm', 'runway': '0.5'}[l['kind']]
        ax.plot(q[:, 0], q[:, 1], '-', color=c, lw=0.4, alpha=0.6)
    cur = start
    for lid in p:
        l = Lb[lid]; q = np.array(l['pts'] if l['a'] == cur else l['pts'][::-1]); cur = l['b'] if l['a'] == cur else l['a']
        ax.plot(q[:, 0], q[:, 1], '-', color='red' if l['kind'] == 'leadin' else 'orange', lw=2.2)
    if ex_arr and p is ex_arr[3]:
        for a, node, k, r in ex_arr[4]:
            if a > 120: ax.plot(N[node]['x'], N[node]['z'], 'o', ms=14, mfc='none', mec='magenta', mew=2.5); ax.annotate(f'{a:.0f} deg reversal', (N[node]['x'], N[node]['z']), color='magenta', fontsize=10, xytext=(8, 8), textcoords='offset points')
    ax.set_xlim(x0, x1); ax.set_ylim(z1, z0); ax.set_title(title, fontsize=10); ax.tick_params(labelsize=7)
fig.suptitle('QA C1: taxi graph routes (Dijkstra on sha_taxigraph.json, open links, use rules). Route: orange = taxiway/taxilane links, red = links of kind "leadin". Background links: white taxiway, cyan taxilane, yellow leadin, magenta push.\nContains modified Copernicus Sentinel data 2026; (c) OpenStreetMap contributors (ODbL)', fontsize=9)
plt.tight_layout(); plt.savefig('/home/user/Calc/sha3d/docs/phase1/qa/qa_taxigraph_routes.jpg', dpi=75)
print('arr example', ex_arr[1], N[ex_arr[2]]['ref'], [(round(a), k, r) for a, n, k, r in ex_arr[4] if a > 120])
print('dep 608 leadin metres', sum(Lb[x]['len'] for x in pB if Lb[x]['kind'] == 'leadin'), 'total', sum(Lb[x]['len'] for x in pB))
