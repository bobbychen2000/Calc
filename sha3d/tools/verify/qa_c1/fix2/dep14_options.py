"""Fix round 2, H2 side effect: the two Phase-3 options for the 14 T2 stands that cannot depart under the OSM one-way
tags (docs/phase1/stands.md). Counts, stand names and graph link numbers only. Uses the independent edge-based router of
tools/verify/reverify_data/rv_route.py (theta 100 deg = the builder's 90 deg + 10 deg digitising tolerance).
usage: python3 -I dep14_options.py
Option A (push continues along the lane): the tug pushes on past the blocked one-way apron-lane segment(s) to the next
junction; modelled as those segments opened for the push only (the departure starts with push + segment(s)).
Option B (soft one-way rule): taxiing against oneway=yes on an apron lane is allowed for at most D metres in total per
route (D = 15, 30, 50 m tested); each stand's minimum is the length it needs.
"""
import os, sys, math, json
RV = '/home/user/Calc/sha3d/tools/verify/reverify_data/rv_route.py'
sys.argv = ['x', '/home/user/Calc/sha3d/data/sha_taxigraph.json', '/home/user/Calc/sha3d/data/sha_airport.json',
            '/home/user/Calc/sha3d/data/sha_stands.json']
exec(open(RV).read().split('# --- 1. the committed turn table')[0])
FAIL = '218 219 225 226 227 238A 239 240 240A 271 272 278 279 280'.split()
NEED = {'218': [823], '219': [823], '225': [827], '226': [827], '227': [827, 828], '238A': [836, 837], '239': [836],
        '240': [836], '240A': [836], '271': [815], '272': [815], '278': [812], '279': [812], '280': [812]}
lanes = {l['id']: l for l in L if l['kind'] == 'taxilane' and l['dir'] == 'ab'}


def dep_ends(nm, opened, theta=100.0):
    for i in opened:
        Lb[i]['dir'] = 'both'
    pl = push_of[nm]; n_ok = 0
    for end in ends:
        g = dep_goals(end, theta)
        if route([(pl, pl['b'])], lambda lid, v: (lid, v) in g, 'departure', nm, theta):
            n_ok += 1
    for i in opened:
        Lb[i]['dir'] = 'ab'
    return n_ok


print('one-way apron lanes in the graph: %d' % len(lanes))
print('baseline (no relaxation): stands reaching 4 / 4 take-off ends: %d of %d' % (sum(dep_ends(n, []) == 4 for n in FAIL), len(FAIL)))
extra = {}
for nm in FAIL:
    ids = NEED[nm]
    assert all(i in lanes for i in ids), (nm, ids)
    k = dep_ends(nm, ids)
    extra[nm] = sum(lanes[i]['len'] for i in ids)
    print('  %-4s needs lane(s) %s, %.1f m against the one-way direction -> %d / 4 ends; push %.0f m -> %.0f m with option A'
          % (nm, ids, extra[nm], k, push_of[nm]['len'], push_of[nm]['len'] + extra[nm]))
for D in (15.0, 30.0, 50.0):
    ok = [nm for nm in FAIL if extra[nm] <= D]
    print('option B, against one-way <= %.0f m per route: %d of %d stands depart to all 4 ends' % (D, len(ok), len(FAIL)))
print('distinct lane segments involved: %d (%.1f m in total)' % (len({i for v in NEED.values() for i in v}),
                                                                 sum(lanes[i]['len'] for i in {i for v in NEED.values() for i in v})))
