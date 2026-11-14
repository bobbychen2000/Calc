import sys, json, math, heapq, numpy as np
from collections import defaultdict, Counter
src = open('graph_qa3.py').read()
exec(src.split("cnt = Counter()")[0])
dep_li = []; arr_li = []
for sid in stand_ids:
    d, prev = dijkstra(Gd, sid)
    for e, (nodes, refs) in ends.items():
        reach = [n for n in nodes if n in d]; t = min(reach, key=lambda n: d[n]); p = path(prev, t)
        li = sum(Lb[x]['len'] for x in p if Lb[x]['kind'] == 'leadin')
        dep_li.append((li, N[sid]['ref'], e))
Ga = adj('arr')
rx_nodes = {}
for r in T['runways']:
    for c in r['connections']:
        if c.get('rapid_exit_for'): rx_nodes.setdefault(c['rapid_exit_for'], set()).add(c['node'])
for land, nodes in rx_nodes.items():
    for n0 in list(nodes)[:3]:
        d, prev = dijkstra(Ga, n0)
        for s in stand_ids:
            p = path(prev, s)
            # strip the final contiguous lead-in run into the stand
            k = len(p)
            while k > 0 and Lb[p[k - 1]]['kind'] == 'leadin': k -= 1
            li = sum(Lb[x]['len'] for x in p[:k] if Lb[x]['kind'] == 'leadin')
            arr_li.append((li, N[s]['ref'], land))
dl = np.array([x[0] for x in dep_li]); al = np.array([x[0] for x in arr_li])
print('departure routes using lead-in links after the push: %d of %d (> 20 m: %d), max %.0f m' % ((dl > 0).sum(), len(dl), (dl > 20).sum(), dl.max()))
print('arrival routes using other stands\' lead-in links before their own lead-in: %d of %d (> 20 m: %d), max %.0f m' % ((al > 0).sum(), len(al), (al > 20).sum(), al.max()))
print('worst dep', sorted(dep_li, reverse=True)[:6]); print('worst arr', sorted(arr_li, reverse=True)[:6])
# push links: chord vs own lead-in, axis deviation
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json')); by = {s['name']: s for s in S['stands']}
from shapely.geometry import LineString, Point
dev = []
for l in L:
    if l['kind'] != 'push': continue
    s = by[l['ref']]; li = LineString(s['leadin']); ch = LineString(l['pts'])
    hd = math.degrees(math.atan2(l['pts'][1][0] - l['pts'][0][0], -(l['pts'][1][1] - l['pts'][0][1]))) % 360
    back = (s['hdg'] + 180) % 360; dang = abs((hd - back + 180) % 360 - 180)
    maxdev = max(li.distance(Point(ch.interpolate(t, normalized=True))) for t in np.linspace(0, 1, 41))
    dev.append((round(maxdev, 1), round(dang, 1), l['ref'], round(l['len'])))
dev.sort(reverse=True)
dv = np.array([d[0] for d in dev]); da = np.array([d[1] for d in dev])
print('push chords: max distance from the stand\'s own lead-in: median %.1f m, > 10 m: %d, > 20 m: %d, max %.1f m' % (np.median(dv), (dv > 10).sum(), (dv > 20).sum(), dv.max()))
print('push chord direction vs stand axis (reverse heading): median %.1f deg, > 10 deg: %d, max %.1f' % (np.median(da), (da > 10).sum(), da.max()))
print('worst', dev[:10])
json.dump(dev, open('push_dev.json', 'w'))
