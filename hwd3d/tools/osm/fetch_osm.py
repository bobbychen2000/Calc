"""Fetch the OpenStreetMap extract of KHWD (Hayward Executive) AS OF A PINNED DATE (Overpass attic query), so that every
later run of the parsers sees exactly the same OSM data.

Forked from sfo3d/tools/xcheck/fetch_osm.py @ a967f9b. Kept: the design (Overpass `[date:"..."]` attic query, the query
split into parts merged by (type, id) in Overpass order node < way < relation, per-part cache, polite back-off over
several public instances, a part no instance answers is split into 4 tiles, the --via api fallback that rebuilds the
state at the date from the OSM editing API, meta file with endpoint / HTTP status / server database time / sha256).
Changed: one extract 'khwd' (bbox and keys below); paths under hwd3d/; per-part sha256 of the raw answer body; attempts
and split depth are options; the API fallback records every request (tools/osm/osm_attic_api.py REQUESTS);
`timestamp_osm_base` of the merged file is the pinned date (the state of the data) and the instances' own database times
are listed per part in the meta. Dropped: the SFO extracts (ksfo, landside) and the ksfo_latest copy.

Extract 'khwd'
--------------
bbox (S, W, N, E) = the OSM aerodrome way + 150 m on each side, rounded outward to 1e-5 deg:
  aeroway=aerodrome way 186495935 "Hayward Executive Airport" (icao KHWD), version 13 of 2025-03-13T08:25:40Z, 95 nodes,
  bounds 37.6531711, -122.1323685 .. 37.6659952, -122.1108065 (OSM API /way/186495935/full.json, read 2026-11-12; its
  history shows no edit after v13). 150 m = 0.0013515 deg of latitude, 0.0017000 deg of longitude (hwd_frame MLAT /
  MLON at the ARP). The fetch re-checks the aerodrome way inside the extract against AERO_BOUNDS (fails if it moved).
Parts (one key each; buildings in 4 tiles), all `out meta geom`, bbox filter:
  aeroway        nwr["aeroway"]                       (runways, taxiways, taxilanes, aprons, holds, hangars, helipads ...)
  prefixed_aeroway nwr[~"^[a-z_]+:aeroway$"~"."]      (lifecycle / area prefixes: disused:, abandoned:, construction:,
                                                      proposed:, area:aeroway ... - closed or former pavements)
  building_0..3  nwr["building"]                      (every building in the bbox; parse_osm.py flags airfield ones)
  man_made       nwr["man_made"~"^(tower|windsock|mast|beacon|flagpole)$"]
  navigationaid  nwr["navigationaid"]
  airmark        nwr["airmark"]
  highway        way["highway"~"^(service|footway)$"]  (airside roads: parse_osm.py keeps those meeting the aerodrome)
  barrier        nwr["barrier"~"^(fence|wall|gate|lift_gate|sliding_gate|swing_gate)$"]   (perimeter; gate variants
                 added to the brief's fence/wall/gate because airport gates are often tagged lift_gate / sliding_gate)
  amenity        nwr["amenity"]                       (fuel, fire_station, and any other amenity: FBO identification)
  landuse        nwr["landuse"]                       (parse_osm.py keeps those meeting the aerodrome)
  named          nw["name"][!"highway"]               (named POIs not covered above, e.g. FBO offices; nodes and ways
                                                      only: named relations in the bbox are the city boundary, bus and
                                                      rail routes and stop areas, whose `out geom` member geometry
                                                      would be megabytes; street names are not needed)
Pinned date: PIN_DATE = 2026-11-12T00:00:00Z (a fixed recent instant chosen on 2026-11-12; the server database must be
newer). An instance whose database is older than the pinned date is rejected (attic queries need that).

Instances (tried in turn per part): maps.mail.ru, overpass-api.de, overpass.private.coffee, overpass.kumi.systems.
Probed 2026-11-12 17:07-17:13Z: private.coffee timeout / 502, maps.mail.ru 504 "Dispatcher_Client::request_read_and_idx
::timeout" (server busy), overpass-api.de connection reset, kumi.systems timeout / 504. maps.mail.ru answered between
the 504s (17:17, 17:25Z), so the extract was fetched with --endpoints mail.ru and more attempts (the polite back-off of
20 s x attempt between rounds is kept). Fallback --via api (exact method in osm_attic_api.py).

Output: refs/cache/osm/overpass_khwd_at_<date>.json (+ .meta.json: query parts, endpoint per part, HTTP status, server
database time, sha256 of each raw answer and of the merged file) and overpass_khwd_latest.meta.json pointing to it
(parse_osm.py reads that). Committed (ODbL; refs/cache/osm/SOURCES.json). Per-part raw answers are cached in
refs/cache/osm/.parts/ (a restart reuses them; not committed, listed in hwd3d/.gitignore).
Contributor metadata (Phase 1 review, 2026-11-12): the committed merged extract drops the 'user' (display name) and
'uid' (account id) of every element (STRIP_FIELDS); type, id, version, timestamp and changeset are kept as provenance.
The meta records sha256_unstripped (the merged answer with those fields; it equals the sha256 the first fetch recorded)
and the unstripped copy is kept locally in .parts/<file>.full.json, which the --via api cross-check compares with.
Re-merging entirely from the .parts cache (no part fetched in this run) keeps the existing meta's fetched_utc and log
(the fetch provenance), so a re-run without network does not rewrite them. With --via api, every Overpass
part of the same date found in .parts is compared with the reconstruction (same elements, versions, tags, meta,
geometry) and the result is written to the meta (`overpass_crosscheck`).
Data (c) OpenStreetMap contributors, ODbL 1.0 - https://www.openstreetmap.org/copyright
Usage:
  python3 tools/osm/fetch_osm.py                         # Overpass, pinned date
  python3 tools/osm/fetch_osm.py --via api               # OSM editing API reconstruction of the same state
                                                         # (-> osmapi_khwd_at_<date>.json; when the Overpass extract of
                                                         # the date exists, both are compared and 'latest' is kept)
"""
import argparse, datetime, hashlib, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))            # hwd3d/
sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
import hwd_frame as G                                               # noqa: E402

OUT = os.path.join(ROOT, 'refs', 'cache', 'osm')
PARTS = os.path.join(OUT, '.parts')       # per-part answers (a restart does not fetch them again); not committed
ENDPOINTS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter',
             'https://overpass-api.de/api/interpreter',
             'https://overpass.private.coffee/api/interpreter',
             'https://overpass.kumi.systems/api/interpreter']
UA = 'hwd3d-osm/1.0 (one-off research download, date-pinned)'

PIN_DATE = '2026-11-12T00:00:00Z'
AERO_WAY = 186495935                                    # aeroway=aerodrome, name "Hayward Executive Airport" (see header)
AERO_VERSION = 13
AERO_BOUNDS = (37.6531711, -122.1323685, 37.6659952, -122.1108065)   # S, W, N, E of its 95 nodes (OSM API, v13)
BUFFER_M = 150.0
STRIP_FIELDS = ('user', 'uid')   # OSM contributor display name and account id: not needed by any parser (privacy, review 2026-11-12)
FETCHED = []                     # parts fetched over the network in this run (empty = merged from the .parts cache only)


def _bbox_plus(b, m):
    """bbox (S, W, N, E) grown by m metres on each side (hwd_frame metres per degree at the ARP), rounded outward 1e-5."""
    dl, dL = m / G.MLAT, m / G.MLON
    return (math.floor((b[0] - dl) * 1e5) / 1e5, math.floor((b[1] - dL) * 1e5) / 1e5,
            math.ceil((b[2] + dl) * 1e5) / 1e5, math.ceil((b[3] + dL) * 1e5) / 1e5)


KHWD_BBOX = _bbox_plus(AERO_BOUNDS, BUFFER_M)          # = (37.65181, -122.13407, 37.66735, -122.10910)


def _tiles(b, n=2):
    s, w, nn, e = b
    return [(s + (nn - s) * i / n, w + (e - w) * j / n, s + (nn - s) * (i + 1) / n, w + (e - w) * (j + 1) / n)
            for i in range(n) for j in range(n)]


def _bb(b):
    return '(%.5f,%.5f,%.5f,%.5f)' % b


MM = ('tower', 'windsock', 'mast', 'beacon', 'flagpole')
BARRIER = ('fence', 'wall', 'gate', 'lift_gate', 'sliding_gate', 'swing_gate')
EXTRACTS = {
    'khwd': {'date': PIN_DATE, 'bbox': KHWD_BBOX,
             'parts': [('aeroway', 'nwr["aeroway"]%s;', KHWD_BBOX),
                       ('prefixed_aeroway', 'nwr[~"^[a-z_]+:aeroway$"~"."]%s;', KHWD_BBOX)]
             + [('building_%d' % k, 'nwr["building"]%s;', t) for k, t in enumerate(_tiles(KHWD_BBOX))]
             + [('man_made', 'nwr["man_made"~"^(%s)$"]%%s;' % '|'.join(MM), KHWD_BBOX),
                ('navigationaid', 'nwr["navigationaid"]%s;', KHWD_BBOX),
                ('airmark', 'nwr["airmark"]%s;', KHWD_BBOX),
                ('highway', 'way["highway"~"^(service|footway)$"]%s;', KHWD_BBOX),
                ('barrier', 'nwr["barrier"~"^(%s)$"]%%s;' % '|'.join(BARRIER), KHWD_BBOX),
                ('amenity', 'nwr["amenity"]%s;', KHWD_BBOX),
                ('landuse', 'nwr["landuse"]%s;', KHWD_BBOX),
                ('named', 'nw["name"][!"highway"]%s;', KHWD_BBOX)]},
}
PRED = {   # the same selections as the Overpass parts, as predicates on the tags (for --via api); key = part name prefix
    'khwd': {'aeroway': lambda t: 'aeroway' in t,
             'prefixed_aeroway': lambda t: any(re.fullmatch(r'[a-z_]+:aeroway', k) and v for k, v in t.items()),
             'building': lambda t: 'building' in t,
             'man_made': lambda t: t.get('man_made') in MM,
             'navigationaid': lambda t: 'navigationaid' in t, 'airmark': lambda t: 'airmark' in t,
             'highway': lambda t: t.get('highway') in ('service', 'footway'),
             'barrier': lambda t: t.get('barrier') in BARRIER,
             'amenity': lambda t: 'amenity' in t, 'landuse': lambda t: 'landuse' in t,
             'named': lambda t: 'name' in t and 'highway' not in t},
}
PRED_TYPES = {'highway': ('way',), 'named': ('node', 'way')}   # parts restricted to some element types (Overpass way / nw)
TYPE_ORDER = {'node': 0, 'way': 1, 'relation': 2}


def query(date, body):
    return '[out:json][timeout:180][date:"%s"];(%s);out meta geom;' % (date, body)


def fetch_part(q, date, log, attempts):
    pinned = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
    for attempt in range(attempts):
        for ep in ENDPOINTS:
            t0 = time.time()
            try:
                req = urllib.request.Request(ep, data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=200) as r:
                    body, st = r.read(), r.status
                d = json.loads(body)
                base = datetime.datetime.strptime(d['osm3s']['timestamp_osm_base'], '%Y-%m-%dT%H:%M:%SZ')
                if base < pinned:
                    log.append('STALE %s %s' % (ep, d['osm3s']['timestamp_osm_base'])); print(log[-1], flush=True); continue
                if d.get('remark'):          # Overpass runtime error / timeout inside a 200 answer
                    log.append('REMARK %s %s' % (ep, d['remark'][:160])); print(log[-1], flush=True); continue
                return d, {'endpoint': ep, 'status': st, 'seconds': round(time.time() - t0, 1), 'bytes': len(body),
                           'sha256': hashlib.sha256(body).hexdigest(),
                           'server_base': d['osm3s']['timestamp_osm_base'], 'elements': len(d['elements']),
                           'utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
            except urllib.error.HTTPError as e:
                log.append('FAIL %s HTTP %d %s' % (ep, e.code, datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%SZ')))
                print(log[-1], flush=True)
            except Exception as e:  # noqa: BLE001 - report and try the next instance
                log.append('FAIL %s %s %s' % (ep, repr(e)[:140], datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%SZ')))
                print(log[-1], flush=True)
        time.sleep(20 * (attempt + 1))
    return None, None


def get_part(name, pname, filt, bbox, date, log, parts, els, attempts, max_depth, depth=0):
    tag = date.replace('-', '').replace(':', '')
    cache = os.path.join(PARTS, '%s_%s_%s.json' % (name, tag, pname))
    q = query(date, filt % _bb(bbox))
    if os.path.exists(cache):
        d = json.load(open(cache)); info = d.pop('_info')
    else:
        d, info = fetch_part(q, date, log, attempts)
        if d is None:
            if depth >= max_depth: print('GAVE UP on part', pname); return False
            print('splitting', pname, 'into 4 tiles', flush=True)
            return all(get_part(name, '%s_%d' % (pname, k), filt, t, date, log, parts, els, attempts, max_depth, depth + 1)
                       for k, t in enumerate(_tiles(bbox)))
        os.makedirs(PARTS, exist_ok=True); json.dump(dict(d, _info=info), open(cache, 'w')); FETCHED.append(pname)
        time.sleep(3)
    for e in d['elements']: els[(e['type'], e['id'])] = e
    parts.append({'part': pname, 'query': q, **info}); print(name, pname, info, flush=True)
    return True


def compare_overpass_parts(name, date, X, els, pred_key):
    """--via api: compare the reconstruction with every Overpass attic part of the same date that is cached in .parts
    (answered before the instances failed): same (type, id) set, versions, tags, meta and geometry for the elements the
    part selects. Parts fetched over the whole bbox are compared one by one; tiled parts (building_0..3) only as a set."""
    tag = date.replace('-', '').replace(':', '')
    out = {}
    groups = {}
    for pname, filt, bbox in X['parts']:
        groups.setdefault(re.sub(r'_\d+$', '', pname), []).append(pname)
    for key, pnames in groups.items():
        fns = [os.path.join(PARTS, '%s_%s_%s.json' % (name, tag, p)) for p in pnames]
        if not all(os.path.exists(f) for f in fns): continue
        ov = {}
        for f in fns:
            for e in json.load(open(f))['elements']: ov[(e['type'], e['id'])] = e
        api = {k: e for k, e in els.items() if pred_key(key, e.get('tags') or {}, e['type'])}
        def geo(e):
            if e['type'] == 'node': return (e['lat'], e['lon'])
            if e['type'] == 'way': return tuple((g['lat'], g['lon']) for g in e.get('geometry', []))
            return tuple((m['type'], m['ref'], m.get('role')) for m in e.get('members', []))
        com = set(ov) & set(api)
        out[key] = {'overpass': len(ov), 'api': len(api), 'only_overpass': len(set(ov) - set(api)), 'only_api': len(set(api) - set(ov)),
                    'version_diff': sum(ov[k].get('version') != api[k].get('version') for k in com),
                    'tag_diff': sum((ov[k].get('tags') or {}) != (api[k].get('tags') or {}) for k in com),
                    'meta_diff': sum(any(ov[k].get(f) != api[k].get(f) for f in ('timestamp', 'changeset', 'user', 'uid')) for k in com),
                    'geometry_diff': sum(geo(ov[k]) != geo(api[k]) for k in com),
                    'overpass_server_base': sorted({json.load(open(f))['_info']['server_base'] for f in fns})}
    return out


def compare_extracts(a, b):
    """two element lists of the same extract: keys, versions, tags, meta and geometry (incl. relation member geometry)"""
    A = {(e['type'], e['id']): e for e in a}; B = {(e['type'], e['id']): e for e in b}
    com = set(A) & set(B)
    def geo(e):
        if e['type'] == 'node': return (e['lat'], e['lon'])
        if e['type'] == 'way': return tuple((g['lat'], g['lon']) for g in e.get('geometry', []))
        return tuple((m['type'], m['ref'], m.get('role'), tuple((g['lat'], g['lon']) for g in m.get('geometry', [])))
                     for m in e.get('members', []))
    out = {'a': len(A), 'b': len(B), 'only_a': len(set(A) - set(B)), 'only_b': len(set(B) - set(A)),
           'version_diff': sum(A[k].get('version') != B[k].get('version') for k in com),
           'tag_diff': sum((A[k].get('tags') or {}) != (B[k].get('tags') or {}) for k in com),
           'geometry_diff': sum(geo(A[k]) != geo(B[k]) for k in com)}
    for f in ('timestamp', 'changeset', 'uid', 'user'):
        out[f + '_diff'] = sum(A[k].get(f) != B[k].get(f) for k in com)
    return out


def check_aerodrome(elements, log):
    """the aerodrome way that defines the bbox must be in the extract, at the expected version and bounds"""
    w = [e for e in elements if e['type'] == 'way' and e['id'] == AERO_WAY]
    if not w: return 'aerodrome way %d missing from the extract' % AERO_WAY
    g = w[0].get('geometry') or []
    b = (min(p['lat'] for p in g), min(p['lon'] for p in g), max(p['lat'] for p in g), max(p['lon'] for p in g))
    dev = max(abs(x - y) for x, y in zip(b, AERO_BOUNDS))
    msg = 'aerodrome way %d v%s, %d nodes, bounds %s, max deviation from AERO_BOUNDS %.1e deg' % (
        AERO_WAY, w[0].get('version'), len(g), b, dev)
    log.append(msg); print(msg)
    if w[0].get('version') != AERO_VERSION or dev > 1e-7:
        return 'aerodrome way changed: ' + msg
    if _bbox_plus(b, BUFFER_M) != KHWD_BBOX:
        return 'bbox of the extract no longer equals the aerodrome bbox + %g m' % BUFFER_M
    return None


def run(name, date, latest, only=None, via='overpass', attempts=2, max_depth=1):
    X = EXTRACTS[name]
    os.makedirs(OUT, exist_ok=True)
    els, parts, log = {}, [], []
    if via == 'api':
        import osm_attic_api as OA
        OA.CACHE = os.path.join(PARTS, 'api')
        keys = [k for k in PRED[name] if not only or any(k.startswith(o) for o in only)]
        def pred(t, typ=None):
            return any(PRED[name][k](t) and (typ is None or typ in PRED_TYPES.get(k, ('node', 'way', 'relation'))) for k in keys)
        for e in OA.state_at(X['bbox'], date, pred, log, ('node', 'way', 'relation')):
            els[(e['type'], e['id'])] = e
        reqs = OA.REQUESTS
        xc = compare_overpass_parts(name, date, X, els, pred_key=lambda k, t, typ: PRED[name][k](t) and typ in PRED_TYPES.get(k, ('node', 'way', 'relation')))
        if xc: log.append('cross-check against cached Overpass attic parts: %s' % json.dumps(xc))
        parts.append({'part': 'osm-api attic (%s)' % ', '.join(keys), 'endpoint': OA.API, 'overpass_crosscheck': xc,
                      'status': sorted({str(r['status']) for r in reqs}),
                      'server_base': 'live OSM database at request time (%s .. %s)' % (min(r['utc'] for r in reqs), max(r['utc'] for r in reqs)),
                      'method': OA.__doc__.split('Method')[1][:1600], 'elements': len(els), 'requests': reqs})
        print('\n'.join(log))
    else:
        for pname, filt, bbox in X['parts']:
            if only and not any(pname.startswith(o) for o in only): continue
            if not get_part(name, pname, filt, bbox, date, log, parts, els, attempts, max_depth):
                print('\n'.join(log[-12:])); return 1
    elements = [els[k] for k in sorted(els, key=lambda k: (TYPE_ORDER[k[0]], k[1]))]
    err = None if only else check_aerodrome(elements, log)
    if err: print('ERROR', err); return 2
    tag = date.replace('-', '').replace(':', '')
    fn = '%s_%s%s_at_%s.json' % ('overpass' if via == 'overpass' else 'osmapi', name, ('_' + '_'.join(only)) if only else '', tag)
    ovf = os.path.join(OUT, 'overpass_%s_at_%s.json' % (name, tag))
    ovf_full = os.path.join(PARTS, 'overpass_%s_at_%s.full.json' % (name, tag))
    if via == 'api' and not only and os.path.exists(ovf):
        # a merged Overpass extract of the same date exists: compare the whole reconstruction with it, keep it as 'latest'.
        # The committed extract has no user / uid (STRIP_FIELDS): compare with the local unstripped copy when present.
        cmp_f = ovf_full if os.path.exists(ovf_full) else ovf
        xc = compare_extracts(json.load(open(cmp_f))['elements'], elements)
        xc['overpass_file'] = os.path.relpath(cmp_f, OUT); xc['overpass_sha256'] = hashlib.sha256(open(cmp_f, 'rb').read()).hexdigest()
        if cmp_f == ovf: xc['note'] = 'compared with the committed extract, which has no %s: those diffs are not meaningful' % '/'.join(STRIP_FIELDS)
        parts[-1]['crosscheck_overpass_merged'] = xc
        log.append('cross-check against %s: %s' % (os.path.basename(ovf), json.dumps(xc))); print(log[-1])
        latest = False
    res = {'version': 0.6, 'generator': 'hwd3d/tools/osm/fetch_osm.py (%s)' % ('OSM API attic reconstruction, osm_attic_api.py' if via == 'api' else 'Overpass attic, merged parts'),
           'osm3s': {'timestamp_osm_base': date, 'attic_date': date,
                     'copyright': 'The data included in this document is from www.openstreetmap.org. The data is made '
                                  'available under ODbL.'},
           'elements': elements}
    body_full = json.dumps(res, separators=(',', ':')).encode()
    if via == 'overpass':
        os.makedirs(PARTS, exist_ok=True)
        open(os.path.join(PARTS, fn.replace('.json', '.full.json')), 'wb').write(body_full)    # local only (gitignored)
    res['elements'] = [{k: v for k, v in e.items() if k not in STRIP_FIELDS} for e in elements]
    body = json.dumps(res, separators=(',', ':')).encode()
    open(os.path.join(OUT, fn), 'wb').write(body)
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    log_keep = log[-60:]; old_meta = os.path.join(OUT, fn.replace('.json', '.meta.json'))
    if via == 'overpass' and not FETCHED and os.path.exists(old_meta):
        om = json.load(open(old_meta))       # merged from the cache only: keep the original fetch provenance
        if om.get('osm_base') == date and om.get('fetched_utc'):
            now = om['fetched_utc']; log_keep = om.get('log', log_keep)
            print('all parts from the .parts cache: kept fetched_utc %s and the fetch log of %s' % (now, os.path.basename(old_meta)))
    meta = {'file': fn, 'osm_base': date, 'parts_only': only, 'attic_date': date, 'bbox': X['bbox'],
            'bbox_def': 'aeroway=aerodrome way %d v%d bounds %s + %g m, rounded outward to 1e-5 deg' % (AERO_WAY, AERO_VERSION, list(AERO_BOUNDS), BUFFER_M),
            'fetched_utc': now, 'via': via,
            'endpoint': sorted({p['endpoint'] for p in parts}), 'parts': parts, 'bytes': len(body),
            'sha256': hashlib.sha256(body).hexdigest(), 'elements': len(elements),
            'stripped_fields': list(STRIP_FIELDS),
            'sha256_unstripped': hashlib.sha256(body_full).hexdigest(), 'bytes_unstripped': len(body_full),
            'strip_note': 'the committed extract omits the OSM contributor fields %s of every element (not needed by any parser; '
                          'OSM publishes them through its own API). sha256_unstripped is the merged answer with them; a local copy '
                          'is kept in refs/cache/osm/.parts/ (gitignored) for the --via api cross-check' % list(STRIP_FIELDS),
            'log': log_keep,
            'licence': 'ODbL 1.0, (c) OpenStreetMap contributors - https://opendatacommons.org/licenses/odbl/1-0/ ; https://www.openstreetmap.org/copyright'}
    json.dump(meta, open(os.path.join(OUT, fn.replace('.json', '.meta.json')), 'w'), indent=1)
    if latest:
        json.dump(meta, open(os.path.join(OUT, 'overpass_%s_latest.meta.json' % name), 'w'), indent=1)
    print('wrote', fn, len(elements), 'elements', len(body) // 1024, 'KB', 'sha256', meta['sha256'])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--which', choices=sorted(EXTRACTS), action='append')
    ap.add_argument('--date', help='attic date (UTC, YYYY-MM-DDTHH:MM:SSZ); default: the pinned date of each extract')
    ap.add_argument('--no-latest', action='store_true', help='do not repoint overpass_<name>_latest.meta.json')
    ap.add_argument('--parts', nargs='*', help='only the parts whose name starts with one of these (e.g. aeroway); implies --no-latest')
    ap.add_argument('--via', choices=('overpass', 'api'), default='overpass',
                    help='api: rebuild the state at the date from the OSM editing API (tools/osm/osm_attic_api.py) when no '
                         'Overpass instance answers')
    ap.add_argument('--attempts', type=int, default=2, help='rounds over all instances per part (default 2)')
    ap.add_argument('--split-depth', type=int, default=1, help='times a failing part is split into 4 tiles (default 1)')
    ap.add_argument('--endpoints', nargs='*', help='only the instances whose URL contains one of these (e.g. mail.ru)')
    a = ap.parse_args()
    if a.endpoints:
        ENDPOINTS[:] = [e for e in ENDPOINTS if any(k in e for k in a.endpoints)]
        print('instances:', ENDPOINTS)
    rc = 0
    for name in a.which or sorted(EXTRACTS):
        date = a.date or EXTRACTS[name]['date']
        latest = not a.no_latest and not a.parts and date == EXTRACTS[name]['date']
        rc |= run(name, date, latest, a.parts, a.via, a.attempts, a.split_depth)
    return rc


if __name__ == '__main__':
    sys.exit(main())
