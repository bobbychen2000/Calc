"""OSM database state at a past instant, from the OSM editing API (fallback of tools/osm/fetch_osm.py when no Overpass
instance answers).

Forked from sfo3d/tools/xcheck/osm_attic_api.py @ a967f9b. Kept: the method (below) and the output form. Changed:
User-Agent names hwd3d; every API request is logged in REQUESTS (url, HTTP status, bytes, sha256, UTC time) so the fetch
meta can record per-request provenance (the editing API serves the live database, so its "database time" is the request
time).
2026-11-12: Overpass instances answered 502 / 504 / connection reset / timeout (see the fetch meta log).

Method (exact, not an approximation of Overpass' attic query):
  1. current data: GET /api/0.6/map?bbox=... on tiles (a tile over the API's node limit is split in 4);
  2. every changeset that touched the bbox after the date: GET /api/0.6/changesets?bbox=...&time=<date>,<t> paged back from
     now; for each, its osmChange (GET /api/0.6/changeset/<id>/download); per element the smallest version written after
     the date (element timestamps > date; a changeset open across the date can hold earlier edits);
  3. version at the date = that smallest version - 1 (0: created later, so absent); those versions are fetched by id+version
     (GET /api/0.6/nodes?nodes=<id>v<n>,... / ways / relations, 100 per request); elements never touched after the date
     are the current ones; nodes a way needs that step 1 did not return are fetched (current = state at the date when
     untouched); any element still dated after the date (changed by a changeset that did not touch the bbox, e.g. a
     node of a long way outside it) takes the last version of its history at or before the date;
  4. the predicate of the extract (tags, element type) and the bbox (nodes inside; ways with a segment meeting it; relations with a
     member inside) select the elements, written in Overpass `out meta geom` form (ways with `geometry`, `bounds`).
     Relations carry member geometry like Overpass `out geom`: member ways outside the map tiles are fetched (their
     version at the date, from their history, and their nodes).
Data (c) OpenStreetMap contributors, ODbL 1.0. API usage: one request at a time with a pause (OSM API usage policy,
https://operations.osmfoundation.org/policies/api/).
"""
import datetime, hashlib, json, os, time, urllib.error, urllib.request, xml.etree.ElementTree as ET
from shapely.geometry import LineString, Point, box

API = 'https://api.openstreetmap.org/api/0.6'
UA = 'hwd3d-osm/1.0 (one-off research download, date-pinned)'

CACHE = None      # set by the caller: directory for raw answers (a restart does not fetch them again; not committed)
REQUESTS = []     # provenance of every request made (or read from CACHE) in this run


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _get(url, raw=False, tries=4):
    fn = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ('.xml' if raw else '.json')) if CACHE else None
    if fn and os.path.exists(fn):
        b = open(fn, 'rb').read()
        REQUESTS.append({'url': url, 'status': 'cache', 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
                         'utc': datetime.datetime.fromtimestamp(os.path.getmtime(fn), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
        return b if raw else json.loads(b)
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=180) as r:
                b = r.read(); st = r.status; time.sleep(0.4)
                REQUESTS.append({'url': url, 'status': st, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'utc': _now()})
                if fn and '/changesets.json' not in url:        # the changeset list changes with time: never cached
                    os.makedirs(CACHE, exist_ok=True); open(fn, 'wb').write(b)
                return b if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            REQUESTS.append({'url': url, 'status': e.code, 'utc': _now()})
            if e.code in (400, 404, 410, 509): return {'error': e.code, 'body': e.read()[:300].decode('utf8', 'replace')}
            time.sleep(5 * (k + 1))
        except Exception as e:  # noqa: BLE001 - transient network error: retry politely
            REQUESTS.append({'url': url, 'status': 'error ' + repr(e)[:80], 'utc': _now()})
            time.sleep(5 * (k + 1))
    raise RuntimeError('OSM API failed: ' + url)


def _ts(s): return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')


def map_tiles(bbox, log, depth=0):
    s, w, n, e = bbox
    d = _get('%s/map.json?bbox=%.5f,%.5f,%.5f,%.5f' % (API, w, s, e, n))
    if 'error' in d:
        if depth >= 4: raise RuntimeError('map tile too dense: %s %s' % (bbox, d))
        out = []
        for i in range(2):
            for j in range(2):
                out += map_tiles((s + (n - s) * i / 2, w + (e - w) * j / 2, s + (n - s) * (i + 1) / 2, w + (e - w) * (j + 1) / 2), log, depth + 1)
        return out
    log.append('map %s: %d elements' % (bbox, len(d['elements'])))
    return d['elements']


def changesets_since(bbox, date, log):
    s, w, n, e = bbox; seen = {}; t2 = None
    while True:
        url = '%s/changesets.json?bbox=%.5f,%.5f,%.5f,%.5f&time=%s%s&limit=100' % (API, w, s, e, n, date, (',' + t2) if t2 else '')
        d = _get(url); cs = d.get('changesets', [])
        new = [c for c in cs if c['id'] not in seen]
        for c in new: seen[c['id']] = c
        if len(cs) < 100 or not new: break
        t2 = min(c['created_at'] for c in cs)
    log.append('changesets touching the bbox since %s: %d %s' % (date, len(seen), sorted(seen)[:50]))
    return sorted(seen)


def first_after(cs_ids, date, log):
    D = _ts(date); after = {}
    for k, cid in enumerate(cs_ids):
        x = _get('%s/changeset/%d/download' % (API, cid), raw=True)
        if isinstance(x, dict): log.append('changeset %d: %s' % (cid, x)); continue
        for act in ET.fromstring(x):
            for el in act:
                if el.tag not in ('node', 'way', 'relation'): continue
                if _ts(el.get('timestamp')) <= D: continue
                key = (el.tag, int(el.get('id'))); v = int(el.get('version'))
                after[key] = min(after.get(key, v), v)
    log.append('elements written after %s: %d' % (date, len(after)))
    return after


def fetch_versions(keys, log):
    """{(type, id): version} -> {(type, id): element}; version None = current"""
    out = {}
    for typ in ('node', 'way', 'relation'):
        ks = [(i, v) for (t, i), v in keys.items() if t == typ]
        for k in range(0, len(ks), 100):
            batch = ks[k:k + 100]
            q = ','.join('%d%s' % (i, ('v%d' % v) if v else '') for i, v in batch)
            d = _get('%s/%ss.json?%ss=%s' % (API, typ, typ, q))
            if 'error' in d:          # one redacted / missing version fails the batch: one by one
                for i, v in batch:
                    e = _get('%s/%s/%d%s.json' % (API, typ, i, ('/%d' % v) if v else ''))
                    if 'elements' in e: out[(typ, i)] = e['elements'][0]
                    else: log.append('missing %s %d v%s: %s' % (typ, i, v, e))
                continue
            for e in d['elements']: out[(e['type'], e['id'])] = e
    return out


def state_at(bbox, date, pred, log, types=('node', 'way', 'relation')):
    cur = {(e['type'], e['id']): e for e in map_tiles(bbox, log)}
    after = first_after(changesets_since(bbox, date, log), date, log)
    st = {k: v for k, v in cur.items() if k not in after}
    want = {k: v - 1 for k, v in after.items() if v > 1}
    # versions at the date: ways / relations whose earlier version may matter, and every node written later
    st.update(fetch_versions(want, log))
    st = {k: e for k, e in st.items() if e.get('visible', True)}
    # nodes of the ways at the date that are still missing (outside the tiles, never touched since): current = then
    miss = {('node', n): None for (t, i), e in st.items() if t == 'way' for n in e.get('nodes', []) if ('node', n) not in st}
    if miss:
        log.append('fetching %d untouched nodes outside the tiles' % len(miss)); st.update(fetch_versions(miss, log))
    # anything still written after the date (a node outside the bbox changed by a changeset that did not touch the bbox,
    # or deleted since): its version at the date from its history
    D = _ts(date)
    late = [k for k, e in st.items() if not e.get('visible', True) or ('timestamp' in e and _ts(e['timestamp']) > D)
            or (k[0] == 'node' and 'lat' not in e)]
    if late: log.append('history of %d elements written after the date outside the changeset scan' % len(late))
    for k in late:
        h = _get('%s/%s/%d/history.json' % (API, k[0], k[1]))
        vs = [e for e in h.get('elements', []) if _ts(e['timestamp']) <= D]
        if vs and vs[-1].get('visible', True): st[k] = vs[-1]
        else: st.pop(k, None)
    # member ways of the selected relations that the tiles did not return (outside the bbox): their version at the date
    # and their nodes, so that relations carry full member geometry like Overpass `out geom`
    rel_ways = {('way', m['ref']) for (t, i), e in st.items() if t == 'relation' and pred(e.get('tags') or {}, 'relation')
                for m in e.get('members', []) if m['type'] == 'way' and ('way', m['ref']) not in st}
    if rel_ways:
        log.append('fetching %d relation member ways outside the tiles' % len(rel_ways))
        for k in sorted(rel_ways):
            h = _get('%s/way/%d/history.json' % (API, k[1]))
            vs = [e for e in h.get('elements', []) if _ts(e['timestamp']) <= D]
            if vs and vs[-1].get('visible', True): st[k] = vs[-1]
        need = {('node', n): None for k in rel_ways if k in st for n in st[k].get('nodes', []) if ('node', n) not in st}
        if need:
            got = fetch_versions(need, log)
            for k, e in got.items():
                if _ts(e['timestamp']) > D:            # changed since the date: its version at the date
                    h = _get('%s/node/%d/history.json' % (API, k[1]))
                    vs = [x for x in h.get('elements', []) if _ts(x['timestamp']) <= D]
                    if not vs or not vs[-1].get('visible', True): continue
                    e = vs[-1]
                st[k] = e
    B = box(bbox[1], bbox[0], bbox[3], bbox[2])
    nodes = {i: e for (t, i), e in st.items() if t == 'node'}
    out = []
    for (t, i), e in sorted(st.items(), key=lambda kv: ({'node': 0, 'way': 1, 'relation': 2}[kv[0][0]], kv[0][1])):
        if t not in types or not pred(e.get('tags') or {}, t): continue
        meta = {k: e.get(k) for k in ('timestamp', 'version', 'changeset', 'user', 'uid')}
        if t == 'node':
            if not B.intersects(Point(e['lon'], e['lat'])): continue
            out.append({'type': 'node', 'id': i, 'lat': e['lat'], 'lon': e['lon'], **meta, **({'tags': e['tags']} if e.get('tags') else {})})
        elif t == 'way':
            g = [nodes.get(n) for n in e['nodes']]
            if any(x is None for x in g): log.append('way %d: %d nodes missing' % (i, sum(x is None for x in g))); continue
            pts = [(x['lon'], x['lat']) for x in g]
            geom = LineString(pts) if len(pts) >= 2 else Point(pts[0])
            if not B.intersects(geom): continue
            out.append({'type': 'way', 'id': i, 'bounds': {'minlat': min(p[1] for p in pts), 'minlon': min(p[0] for p in pts),
                                                         'maxlat': max(p[1] for p in pts), 'maxlon': max(p[0] for p in pts)},
                        'nodes': e['nodes'], 'geometry': [{'lat': p[1], 'lon': p[0]} for p in pts], **meta, 'tags': e.get('tags') or {}})
        else:
            mem = e.get('members', [])
            inside = any((m['type'] == 'node' and m['ref'] in nodes and B.intersects(Point(nodes[m['ref']]['lon'], nodes[m['ref']]['lat'])))
                         or (m['type'] == 'way' and ('way', m['ref']) in st) for m in mem)
            if not inside: continue
            mem = [dict(m) for m in mem]
            for m in mem:                 # member geometry as in Overpass `out geom`, where the member is known
                if m['type'] == 'way' and ('way', m['ref']) in st:
                    g = [nodes.get(n) for n in st[('way', m['ref'])].get('nodes', [])]
                    if g and all(x is not None for x in g): m['geometry'] = [{'lat': x['lat'], 'lon': x['lon']} for x in g]
                elif m['type'] == 'node' and m['ref'] in nodes:
                    m['lat'], m['lon'] = nodes[m['ref']]['lat'], nodes[m['ref']]['lon']
            out.append({'type': 'relation', 'id': i, 'members': mem, **meta, 'tags': e.get('tags') or {}})
    return out
