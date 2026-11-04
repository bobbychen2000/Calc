"""Fetch the OpenStreetMap extracts the static-data generators read, AS OF A PINNED DATE (Overpass attic query).

Why pinned: the generators (tools/xcheck/parse_osm.py -> tools/build_airfield_details.py, tools/build_landside.py,
tools/stands/*, tools/imagery/paint_pave_naip.py, tools/live/build_taxigraph.py) were run on two Overpass downloads,
database 2026-09-24T09:07:42Z (airfield) and 2026-09-26T03:03:01Z (landside). OSM keeps changing (static review
2026-11-04: 5 taxiway ways deleted, 9 modified, 17 added, 29 landside ways changed since then), so an unpinned re-fetch
would silently change far more than a fix. Every extract is therefore fetched with Overpass `[date:"..."]` (the
database state at that instant) and cached under its date; later OSM edits enter the data only through the explicit,
evidence-listed update lists of the generators (e.g. build_airfield_details.OSM_UPDATES, which reads a second pinned
extract fetched with --date).

Extracts (EXTRACTS below):
  ksfo      bbox (S, W, N, E) 37.595, -122.405, 37.640, -122.350; every node/way/relation with an `aeroway` key, a
            `building` key, man_made in {tower, windsock, mast, beacon}, a `navigationaid` or `airmark` key.
            Pinned 2026-09-24T09:07:42Z (= the database of the 24 Sep download the data were built on).
  landside  bbox 37.600, -122.412, 37.640, -122.372 (the bbox of the 26 Sep download, recovered: see LAND_BBOX);
            ways highway=* and amenity=parking (+ their relations' member ways are not
            needed: build_landside reads ways only). Pinned 2026-09-26T03:03:01Z (database of the 26 Sep download).
`out meta geom`: each way carries its geometry, version, timestamp, user and changeset (provenance / licence notes).
The query is split into parts (one key each; buildings / highways in 4 tiles, a part no instance answers into 4 more,
twice at most) so that a busy public instance answers within its gateway timeout; parts are merged by (type, id) and sorted node < way < relation, id ascending - the order
of a single Overpass `out` - so the merged file is what one query would have returned.

Instances: tried in turn per part, with polite back-off (no tight retry loop). Probed 2026-11-04: maps.mail.ru answers
attic queries (intermittent 504 under load), overpass-api.de / lz4 / z reset the connection, kumi.systems is stale
(2026-07-28) and times out, private.coffee times out. An instance is accepted only if its database is newer than the
pinned date (attic queries need that).

Output: refs/cache/osm/overpass_<name>_at_<date>.json (+ .meta.json: query parts, endpoint per part, HTTP status,
server database time, sha256) and overpass_<name>_latest.meta.json pointing to it (the generators read that), plus
overpass_ksfo_latest.json (a copy, for older readers) when the pinned ksfo extract is fetched. These files are
committed (ODbL; refs/cache/osm/SOURCES.json; tools/cache/sync.py stages them).
Data (c) OpenStreetMap contributors, ODbL 1.0 - https://www.openstreetmap.org/copyright
Usage:
  python3 tools/xcheck/fetch_osm.py                      # both extracts at their pinned dates
  python3 tools/xcheck/fetch_osm.py --which ksfo --date 2026-11-04T18:00:00Z --parts aeroway   # the update extract
                                                       # read by build_airfield_details.OSM_UPDATES
"""
import argparse, datetime, hashlib, json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'refs', 'cache', 'osm')
ENDPOINTS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter',
             'https://overpass-api.de/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter',
             'https://overpass.private.coffee/api/interpreter']
UA = 'sfo3d-xcheck/1.1 (one-off research download, date-pinned)'


def _tiles(b, n=2):
    s, w, nn, e = b
    return [(s + (nn - s) * i / n, w + (e - w) * j / n, s + (nn - s) * (i + 1) / n, w + (e - w) * (j + 1) / n)
            for i in range(n) for j in range(n)]


def _bb(b):
    return '(%.4f,%.4f,%.4f,%.4f)' % b


KSFO_BBOX = (37.595, -122.405, 37.640, -122.350)
# landside bbox: the query of 26 Sep 2026 was not kept (its meta file was lost); this is the bbox that reproduces
# data/sfo_landside.json of that build exactly (searched on the reconstructed extract, 2026-11-04: every one of its
# 1574 ways intersects it, none of the 250 other ways of a larger extract does)
LAND_BBOX = (37.600, -122.412, 37.640, -122.372)
# parts: (name, Overpass filter with %s for the bbox, bbox); a part that no instance answers is split into 4 tiles
# (up to twice) - the result is the same set of elements
EXTRACTS = {
    'ksfo': {'date': '2026-09-24T09:07:42Z', 'bbox': KSFO_BBOX,
             'parts': [('aeroway', 'nwr["aeroway"]%s;', KSFO_BBOX)]
             + [('building_%d' % k, 'nwr["building"]%s;', t) for k, t in enumerate(_tiles(KSFO_BBOX))]
             + [('man_made', 'nwr["man_made"~"^(tower|windsock|mast|beacon)$"]%s;', KSFO_BBOX),
                ('navigationaid', 'nwr["navigationaid"]%s;', KSFO_BBOX),
                ('airmark', 'nwr["airmark"]%s;', KSFO_BBOX)]},
    'landside': {'date': '2026-09-26T03:03:01Z', 'bbox': LAND_BBOX,
                 'parts': [('highway_%d' % k, 'way["highway"]%s;', t) for k, t in enumerate(_tiles(LAND_BBOX))]
                 + [('parking', 'way["amenity"="parking"]%s;', LAND_BBOX)]},
}
TYPE_ORDER = {'node': 0, 'way': 1, 'relation': 2}
PARTS = os.path.join(OUT, '.parts')       # per-part answers (a restart does not fetch them again); not committed


def query(date, body):
    return '[out:json][timeout:180][date:"%s"];(%s);out meta geom;' % (date, body)


def fetch_part(q, date, log, attempts=3):
    pinned = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
    for attempt in range(attempts):
        for ep in ENDPOINTS:
            t0 = time.time()
            try:
                req = urllib.request.Request(ep, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=240) as r:
                    body, st = r.read(), r.status
                d = json.loads(body)
                base = datetime.datetime.strptime(d['osm3s']['timestamp_osm_base'], '%Y-%m-%dT%H:%M:%SZ')
                if base < pinned:
                    log.append('STALE %s %s' % (ep, d['osm3s']['timestamp_osm_base'])); print(log[-1], flush=True); continue
                if d.get('remark'):          # Overpass runtime error / timeout inside a 200 answer
                    log.append('REMARK %s %s' % (ep, d['remark'][:160])); print(log[-1], flush=True); continue
                return d, {'endpoint': ep, 'status': st, 'seconds': round(time.time() - t0, 1), 'bytes': len(body),
                           'server_base': d['osm3s']['timestamp_osm_base'], 'elements': len(d['elements'])}
            except Exception as e:  # noqa: BLE001 - report and try the next instance
                log.append('FAIL %s %s' % (ep, repr(e)[:160])); print(log[-1], flush=True)
        time.sleep(20 * (attempt + 1))
    return None, None


def get_part(name, pname, filt, bbox, date, log, parts, els, depth=0):
    tag = date.replace('-', '').replace(':', '')
    cache = os.path.join(PARTS, '%s_%s_%s.json' % (name, tag, pname))
    q = query(date, filt % _bb(bbox))
    if os.path.exists(cache):
        d = json.load(open(cache)); info = d.pop('_info')
    else:
        d, info = fetch_part(q, date, log)
        if d is None:
            if depth >= 2: print('GAVE UP on part', pname); return False
            print('splitting', pname, 'into 4 tiles', flush=True)
            return all(get_part(name, '%s_%d' % (pname, k), filt, t, date, log, parts, els, depth + 1) for k, t in enumerate(_tiles(bbox)))
        os.makedirs(PARTS, exist_ok=True); json.dump(dict(d, _info=info), open(cache, 'w'))
        time.sleep(3)
    for e in d['elements']: els[(e['type'], e['id'])] = e
    parts.append({'part': pname, 'query': q, **info}); print(name, pname, info, flush=True)
    return True


PRED = {   # the same selections as the Overpass parts, as predicates on the tags (for --via api)
    'ksfo': {'aeroway': lambda t: 'aeroway' in t, 'building': lambda t: 'building' in t,
             'man_made': lambda t: t.get('man_made') in ('tower', 'windsock', 'mast', 'beacon'),
             'navigationaid': lambda t: 'navigationaid' in t, 'airmark': lambda t: 'airmark' in t},
    'landside': {'highway': lambda t: 'highway' in t, 'parking': lambda t: t.get('amenity') == 'parking'},
}


def run(name, date, latest, only=None, via='overpass'):
    X = EXTRACTS[name]
    os.makedirs(OUT, exist_ok=True)
    els, parts, log = {}, [], []
    if via == 'api':
        import osm_attic_api as OA
        OA.CACHE = os.path.join(PARTS, 'api')
        keys = [k for k in PRED[name] if not only or any(k.startswith(o) for o in only)]
        pred = lambda t: any(PRED[name][k](t) for k in keys)
        types = ('way',) if name == 'landside' else ('node', 'way', 'relation')
        for e in OA.state_at(X['bbox'], date, pred, log, types): els[(e['type'], e['id'])] = e
        parts.append({'part': 'osm-api attic (%s)' % ', '.join(keys), 'endpoint': OA.API, 'method': OA.__doc__.split('Method')[1][:1400],
                      'elements': len(els)})
        print('\n'.join(log))
    else:
        for pname, filt, bbox in X['parts']:
            if only and not any(pname.startswith(o) for o in only): continue
            if not get_part(name, pname, filt, bbox, date, log, parts, els):
                print('\n'.join(log[-12:])); return 1
    elements = [els[k] for k in sorted(els, key=lambda k: (TYPE_ORDER[k[0]], k[1]))]
    tag = date.replace('-', '').replace(':', '')
    fn = 'overpass_%s%s_at_%s.json' % (name, ('_' + '_'.join(only)) if only else '', tag)
    res = {'version': 0.6, 'generator': 'tools/xcheck/fetch_osm.py (%s)' % ('OSM API attic reconstruction, osm_attic_api.py' if via == 'api' else 'Overpass attic, merged parts'),
           'osm3s': {'timestamp_osm_base': date, 'attic_date': date,
                     'copyright': 'The data included in this document is from www.openstreetmap.org. The data is made '
                                  'available under ODbL.'},
           'elements': elements}
    body = json.dumps(res, separators=(',', ':')).encode()
    open(os.path.join(OUT, fn), 'wb').write(body)
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    meta = {'file': fn, 'osm_base': date, 'parts_only': only, 'attic_date': date, 'bbox': X['bbox'], 'fetched_utc': now,
            'endpoint': sorted({p['endpoint'] for p in parts}), 'parts': parts, 'bytes': len(body),
            'sha256': hashlib.sha256(body).hexdigest(), 'elements': len(elements), 'log': log[-40:],
            'licence': 'ODbL 1.0, (c) OpenStreetMap contributors'}
    json.dump(meta, open(os.path.join(OUT, fn.replace('.json', '.meta.json')), 'w'), indent=1)
    if latest:
        json.dump(meta, open(os.path.join(OUT, 'overpass_%s_latest.meta.json' % name), 'w'), indent=1)
        if name == 'ksfo':
            open(os.path.join(OUT, 'overpass_ksfo_latest.json'), 'wb').write(body)
    print('wrote', fn, len(elements), 'elements', len(body) // 1024, 'KB')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--which', choices=sorted(EXTRACTS), action='append')
    ap.add_argument('--date', help='attic date (UTC, YYYY-MM-DDTHH:MM:SSZ); default: the pinned date of each extract')
    ap.add_argument('--no-latest', action='store_true', help='do not repoint overpass_<name>_latest.meta.json')
    ap.add_argument('--parts', nargs='*', help='only the parts whose name starts with one of these (e.g. aeroway); implies --no-latest')
    ap.add_argument('--via', choices=('overpass', 'api'), default='overpass',
                    help='api: rebuild the state at the date from the OSM editing API (tools/xcheck/osm_attic_api.py) when no '
                         'Overpass instance answers')
    a = ap.parse_args()
    rc = 0
    for name in a.which or sorted(EXTRACTS):
        date = a.date or EXTRACTS[name]['date']
        latest = not a.no_latest and not a.parts and date == EXTRACTS[name]['date']
        rc |= run(name, date, latest, a.parts, a.via)
    return rc


if __name__ == '__main__':
    sys.exit(main())
