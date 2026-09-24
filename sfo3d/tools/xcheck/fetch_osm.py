"""Fetch OpenStreetMap aeroway / building / airfield-furniture features around KSFO from the Overpass API.

bbox (S, W, N, E) = 37.595, -122.405, 37.640, -122.350 (covers the airfield, terminals, cargo/maintenance areas).
Query: every node/way/relation with an `aeroway` key, a `building` key, or man_made in {tower, windsock, mast,
beacon} / a `navigationaid` or `airmark` key; `out meta geom` so each way carries its geometry, version, timestamp,
user and changeset (provenance for the licence notes and for "how old is this mapping").
Tries several public Overpass instances in turn (one polite request each; no retry loop hammering a server).
Writes the raw response to refs/cache/osm/overpass_ksfo_<UTC>.json and refs/cache/osm/overpass_ksfo_latest.json
(+ .meta.json with the endpoint, query, HTTP status and the response's osm3s.timestamp_osm_base).
Data (c) OpenStreetMap contributors, ODbL 1.0 - https://www.openstreetmap.org/copyright
Usage: python3 tools/xcheck/fetch_osm.py
"""
import datetime, hashlib, json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'refs', 'cache', 'osm')
BBOX = (37.595, -122.405, 37.640, -122.350)
# order: freshest first. Probed 24 Sep 2026 08:45 UTC: maps.mail.ru timestamp_osm_base = minutes old; overpass-api.de
# 2 days old (and 504 on the full query); overpass.private.coffee 2026-07-15 (stale, only a last resort).
ENDPOINTS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter',
             'https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter',
             'https://overpass.private.coffee/api/interpreter']
MAX_AGE_DAYS = 7   # reject an instance whose database is older than this (stale mirror)
UA = 'sfo3d-xcheck/1.0 (one-off research download)'
B = '(%.3f,%.3f,%.3f,%.3f)' % BBOX
QUERY = f"""[out:json][timeout:240];
(
  nwr["aeroway"]{B};
  nwr["building"]{B};
  nwr["man_made"~"^(tower|windsock|mast|beacon)$"]{B};
  nwr["navigationaid"]{B};
  nwr["airmark"]{B};
);
out meta geom;"""


def main():
    os.makedirs(OUT, exist_ok=True)
    for ep in ENDPOINTS:
        t0 = time.time()
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({'data': QUERY}).encode(),
                                         headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                body, st = r.read(), r.status
            d = json.loads(body)
            base = datetime.datetime.strptime(d['osm3s']['timestamp_osm_base'], '%Y-%m-%dT%H:%M:%SZ')
            age = (datetime.datetime.utcnow() - base).total_seconds() / 86400
            if age > MAX_AGE_DAYS:
                print('STALE', ep, d['osm3s']['timestamp_osm_base']); continue
        except Exception as e:  # noqa: BLE001 - report and try the next instance
            print('FAIL', ep, repr(e)[:200]); continue
        now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        fn = os.path.join(OUT, f'overpass_ksfo_{now}.json')
        open(fn, 'wb').write(body)
        open(os.path.join(OUT, 'overpass_ksfo_latest.json'), 'wb').write(body)
        meta = {'endpoint': ep, 'query': QUERY, 'status': st, 'utc': now, 'seconds': round(time.time() - t0, 1),
                'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'osm3s': d.get('osm3s'),
                'elements': len(d.get('elements', [])), 'file': os.path.basename(fn)}
        json.dump(meta, open(os.path.join(OUT, 'overpass_ksfo_latest.meta.json'), 'w'), indent=1)
        print(json.dumps(meta, indent=1)[:800])
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
