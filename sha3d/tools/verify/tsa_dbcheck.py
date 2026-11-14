import json, gzip, sys, os, collections, re
cache = sys.argv[1]
R = json.load(gzip.open(os.path.join(cache, 'routes_vrs', 'vrs_index.json.gz')))['routes']
c = collections.Counter()
for fn in ('tsa_intl_arr_2026-11-14.json', 'tsa_intl_dep_2026-11-14.json'):
    L = json.load(open(os.path.join(cache, 'schedules_open', 'tsa', fn)))
    for e in L:
        if 'SHA' not in (e['UpAirportCode'], e['GoalAirportCode']) and 'PVG' not in (e['UpAirportCode'], e['GoalAirportCode']):
            continue
        sh = e['UpAirportCode'] if e['UpAirportCode'] in ('SHA', 'PVG') else e['GoalAirportCode']
        cs = e['AirLineCode'] + str(int(e['AirLineNum']))
        rt = R.get(cs, [None, None])[1]
        truth = 'ZSSS' if sh == 'SHA' else 'ZSPD'
        res = 'not_in_db' if not rt else ('agree' if truth in rt.split('-') and ({'ZSSS','ZSPD'}-{truth}).isdisjoint(rt.split('-')) else 'disagree:' + rt)
        c[(sh, e['Master'] if 'Master' in e else '', e['AirFlyStatus'], res)] += 1
for k, n in sorted(c.items(), key=str): print(k, n)
