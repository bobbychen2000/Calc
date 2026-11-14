"""Fix-round check for QA C1 H2 / M6 (scratch, counts only): the QA route sets of graph_qa2/3 and rwy_use.py, routed
EDGE-BASED with the committed turn table (turns), use / dir rules, own lead-ins only for their stand, runway links only
if allowed. Metrics as the QA: routes that taxi along a runway; routes with a junction reversal > 120 deg (QA's
junction_turns: first / last segment of consecutive links); routes using other stands' lead-in links."""
import json, math, heapq, numpy as np
from collections import defaultdict, Counter
T = json.load(open('/home/user/Calc/sha3d/data/sha_taxigraph.json'))
N = {n['id']: n for n in T['nodes']}; L = T['links']; Lb = {l['id']: l for l in L}
adj = defaultdict(list)
for l in L:
    adj[l['a']].append(l); adj[l['b']].append(l)
allowed = {(a, b) for v, ps in T['turns'].items() for a, b in ps}
def junction_turns(lids, start):
    cur = start; prev_dir = None; out = []
    for lid in lids:
        l = Lb[lid]; p = l['pts'] if l['a'] == cur else l['pts'][::-1]; node = cur; cur = l['b'] if l['a'] == cur else l['a']
        if l['kind'] == 'push': prev_dir = None; continue
        d0 = np.subtract(p[1], p[0])
        if prev_dir is not None and np.linalg.norm(d0) > 0.5:
            out.append(math.degrees(math.acos(np.clip(np.dot(prev_dir, d0) / np.linalg.norm(prev_dir) / np.linalg.norm(d0), -1, 1))))
        d1 = np.subtract(p[-1], p[-2]); prev_dir = d1 if np.linalg.norm(d1) > 0.5 else prev_dir
    return out
def route(starts, goal, mode, stand, allow_runway=False):
    dist = {}; prev = {}; h = []
    for lid, v in starts:
        dist[(lid, v)] = Lb[lid]['len']; heapq.heappush(h, (Lb[lid]['len'], lid, v))
    while h:
        d, lid, v = heapq.heappop(h)
        if d > dist.get((lid, v), 1e18): continue
        if goal(lid, v):
            p = [lid]; st = (lid, v)
            while st in prev: st = prev[st]; p.append(st[0])
            return d, p[::-1]
        for lo in adj[v]:
            if (lid, lo['id']) not in allowed or lo['status'] != 'open': continue
            if lo['use'] == 'runway' and not allow_runway: continue
            if lo['use'] not in ('all', mode, 'stand', 'runway'): continue
            if lo.get('stand') and lo['stand'] != stand: continue
            w = lo['b'] if lo['a'] == v else lo['a']; nd = d + lo['len']
            if nd < dist.get((lo['id'], w), 1e18):
                dist[(lo['id'], w)] = nd; prev[(lo['id'], w)] = (lid, v); heapq.heappush(h, (nd, lo['id'], w))
    return None
# QA's take-off entry definition: connections within 450 m of the take-off end
ends = {}
for r in T['runways']:
    Lr = math.dist(r['ends'][0]['xz'], r['ends'][1]['xz'])
    for e in r['ends']:
        ends[e['end']] = {(c['link'], c['node']) for c in r['connections']
                          if ((c['s_m'] < 450) if e['end'] in ('18L', '18R') else (c['s_m'] > Lr - 459))}
stands = {n['ref']: i for i, n in N.items() if n['kind'] == 'stand'}
push = {l['ref']: l for l in L if l['kind'] == 'push'}
res = Counter(); ex = []
for allow in (False, True):
    for nm, sid in stands.items():
        pl = push[nm]
        for e, ent in ends.items():
            r = route([(pl['id'], pl['b'])], lambda lid, v: (lid, v) in ent, 'departure', nm, allow)
            k = 'dep_rwy_allowed' if allow else 'dep'
            res[k + '_total'] += 1
            if not r: res[k + '_no_route'] += 1; continue
            if any(Lb[x]['kind'] == 'runway' for x in r[1]): res[k + '_along_runway'] += 1
            if any(a > 120 for a in junction_turns(r[1], sid)): res[k + '_reversal_gt120'] += 1
            if any(Lb[x].get('stand') not in (None, nm) for x in r[1]): res[k + '_other_stand_leadin'] += 1
            res[k + '_leadin_m_after_push'] += sum(Lb[x]['len'] for x in r[1][1:] if Lb[x]['kind'] == 'leadin')
# arrivals from each rapid-exit connection (the QA set: 36 rapid-exit nodes in the old graph)
rx = [(c['link'], c['node'], c['rapid_exit_for']) for r in T['runways'] for c in r['connections'] if c.get('rapid_exit_for')]
for allow in (False, True):
    for lid, n0, land in rx:
        l = Lb[lid]; v = l['b'] if l['a'] == n0 else l['a']
        for nm, sid in stands.items():
            k = 'arr_rwy_allowed' if allow else 'arr'
            res[k + '_total'] += 1
            r = route([(lid, v)], lambda x, w, sid=sid: w == sid, 'arrival', nm, allow)
            if not r: res[k + '_no_route'] += 1; continue
            if any(Lb[x]['kind'] == 'runway' for x in r[1]): res[k + '_along_runway'] += 1
            if any(a > 120 for a in junction_turns(r[1], n0)): res[k + '_reversal_gt120'] += 1
            if any(Lb[x].get('stand') not in (None, nm) for x in r[1]): res[k + '_other_stand_leadin'] += 1
print(json.dumps(dict(sorted(res.items())), indent=1))
print('rapid-exit links (dir, use):', Counter((Lb[c[0]]['dir'], Lb[c[0]]['use']) for c in rx), 'runway links', Counter((l['dir'], l['use']) for l in L if l['kind'] == 'runway'))
print('lead-in links: own (stand-tagged)', sum(1 for l in L if l['kind'] == 'leadin' and l.get('stand')), '| reclassified apron lanes', sum(1 for l in L if l.get('osm_kind') == 'leadin'))
