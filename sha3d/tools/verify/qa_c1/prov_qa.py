import json
from collections import Counter
def check(name, recs):
    n = len(recs); c = Counter()
    srcv = Counter()
    for r in recs:
        if not isinstance(r, dict):
            c['not_dict'] += 1; continue
        if 'src' not in r: c['no_src'] += 1
        else: srcv[str(r['src'])[:40]] += 1
        if 'evidence' not in r and 'refs' not in r: c['no_evidence_or_refs'] += 1
        if 'evidence' not in r: c['no_evidence'] += 1
    print(f'{name:38s} n={n:5d}', dict(c), 'src values:', dict(srcv.most_common(6)))
A = json.load(open('/home/user/Calc/sha3d/data/sha_airport.json'))
for k in ['runways','taxiways','taxilanes','holds','aprons','helipads','buildings','navaids']:
    check('airport.'+k, A[k])
for k, v in A['surfaces'].items():
    check('airport.surfaces.'+k, v if isinstance(v, list) else [v])
for k, v in A['context'].items():
    check('airport.context.'+k, v if isinstance(v, list) else [v])
check('airport.control_tower', [A['control_tower']])
check('airport.aerodrome', [A['aerodrome']])
check('airport.extent', [A['extent']])
# runway sub-records
sub = []
for r in A['runways']:
    for e in r['ends']:
        for k, v in e.items():
            if isinstance(v, dict): sub.append(v)
check('airport.runways.ends.*', sub)
S = json.load(open('/home/user/Calc/sha3d/data/sha_stands.json'))
for k in ['stands','remote','unplaced','positions','spare_gates']:
    check('stands.'+k, S[k])
br = [b for s in S['stands'] for b in s['bridges']]
check('stands.stands[].bridges', br)
check('stands.stands[].push', [s['push'] for s in S['stands']])
T = json.load(open('/home/user/Calc/sha3d/data/sha_taxigraph.json'))
for k in ['nodes','links','runways','hold_inf','ways','aprons','leadins']:
    v = T[k]
    check('taxigraph.'+k, v)
print('taxigraph sample node', json.dumps(T['nodes'][0])[:300]); print('link', json.dumps(T['links'][0])[:400]); print('way', json.dumps(T['ways'][0])[:300]); print('edge', T['edges'][0]); print('hold_inf', json.dumps(T['hold_inf'][0])[:300])
print('remote sample', json.dumps(S['remote'][0])[:300]); print('positions', json.dumps(S['positions'][0])[:400]); print('spare', json.dumps(S['spare_gates'][0])[:300])
print('taxigraph licence/attrib', T['licence'], '|', T['attribution'], '| source', T['source'])
print('stands licence', S['licence'][:120], S['attribution'])
