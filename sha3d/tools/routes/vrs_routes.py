#!/usr/bin/env python3
"""Callsign -> route index from the Virtual Radar Server standing data (github.com/vradarserver/standing-data, CC0 1.0).

The standing data is "built from the aviation data submitted by Virtual Radar Server users to the SDM site" (README):
crowd-sourced, one current route per callsign, no validity dates, no days of operation. A route is a list of ICAO
airport codes, e.g. "ZBAA-ZSSS" or "ZBAA-ZSSS-ZJSY" for a multi-leg flight number.

usage:
  python3 -I tools/routes/vrs_routes.py build   SD_DIR OUT.json.gz   # SD_DIR = git clone of standing-data
  python3 -I tools/routes/vrs_routes.py stats   OUT.json.gz          # SHA / PVG route counts per airline
Output (local only, refs/cache/routes_vrs/): {"commit", "routes": {callsign: [airline, "AAAA-BBBB"]},
  "airports": {icao: [iata, name, lat, lon, alt_ft, country]}, "airlines": {icao: [name, iata]}, "airport_loc": {icao: location}}
"""
import collections, csv, glob, gzip, io, json, os, subprocess, sys

SHA, PVG = 'ZSSS', 'ZSPD'


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        yield from csv.DictReader(f)


def build(sd, out):
    routes, airports, airlines, loc = {}, {}, {}, {}
    for p in sorted(glob.glob(os.path.join(sd, 'routes', 'schema-01', '*', '*.csv'))):
        for r in read_csv(p):
            routes[r['Callsign']] = [r['AirlineCode'], r['AirportCodes']]
    for p in sorted(glob.glob(os.path.join(sd, 'airports', 'schema-01', '*', '*.csv'))):
        for r in read_csv(p):
            try:
                airports[r['ICAO'] or r['Code']] = [r['IATA'], r['Name'], float(r['Latitude']), float(r['Longitude']),
                                                    float(r['AltitudeFeet'] or 0), r['CountryISO2']]
                loc[r['ICAO'] or r['Code']] = r['Location']
            except ValueError:
                pass
    for r in read_csv(os.path.join(sd, 'airlines', 'schema-01', 'airlines.csv')):
        if r['ICAO']:
            airlines[r['ICAO']] = [r['Name'], r['IATA']]
    commit = subprocess.run(['git', '-C', sd, 'log', '-1', '--format=%H %cI'], capture_output=True, text=True).stdout.strip()
    doc = {'source': 'https://github.com/vradarserver/standing-data', 'commit': commit, 'licence': 'CC0 1.0',
           'routes': routes, 'airports': airports, 'airlines': airlines, 'airport_loc': loc}
    with gzip.open(out, 'wt') as f:
        json.dump(doc, f, separators=(',', ':'))
    print(f'{len(routes)} routes, {len(airports)} airports, {len(airlines)} airlines; commit {commit} -> {out}')


def load(path):
    with gzip.open(path, 'rt') as f:
        return json.load(f)


def touches(route, ap):
    return ap in route.split('-')


def stats(path):
    d = load(path)
    c = collections.Counter(); legs = collections.Counter()
    for cs, (al, rt) in d['routes'].items():
        aps = rt.split('-')
        for ap, k in ((SHA, 'SHA'), (PVG, 'PVG')):
            if ap in aps:
                c[(k, al)] += 1
                legs[(k, len(aps))] += 1
    for k in ('SHA', 'PVG'):
        tot = sum(v for (kk, _), v in c.items() if kk == k)
        top = sorted(((v, al) for (kk, al), v in c.items() if kk == k), reverse=True)[:30]
        print(k, tot, 'callsigns;', 'by #airports in route:', {n: v for (kk, n), v in legs.items() if kk == k})
        print('  ', ', '.join(f'{al} {v}' for v, al in top))


if __name__ == '__main__':
    {'build': lambda: build(sys.argv[2], sys.argv[3]), 'stats': lambda: stats(sys.argv[2])}[sys.argv[1]]()
