"""Write SOURCES.json for refs/cache/osm_pinned/ (committed), refs/cache/osm_pinned_raw/20261114/ (local only) and
refs/cache/geoid_egm2008/ (local). usage: python3 -I sha3d/tools/osm/write_sources.py SHA3D_DIR"""
import hashlib
import json
import os
import sys

root = sys.argv[1]
ODBL = ('API response header (every file): copyright="OpenStreetMap and contributors" '
        'attribution="http://www.openstreetmap.org/copyright" license="http://opendatacommons.org/licenses/odbl/1-0/"')


def files(d, skip=('SOURCES.json',)):
    out = []
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if f in skip or not os.path.isfile(p):
            continue
        b = open(p, 'rb').read()
        out.append({'file': f, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
    return out


raw = os.path.join(root, 'refs/cache/osm_pinned_raw/20261114')
log = [json.loads(l) for l in open(os.path.join(raw, 'download_log.jsonl'))]
pin = os.path.join(root, 'refs/cache/osm_pinned')
summ = json.load(open(os.path.join(pin, 'pin_summary.json')))
json.dump({
    'topic': 'osm_pinned',
    'what': ('Pinned OpenStreetMap extract of the SHA Live 3D detailed extent (convex hull of aerodrome relation '
             '21913346 + 1 km buffer, %.2f km2), sensitive features removed, clipped to the extent' % summ['extent']['area_km2']),
    'source': 'OpenStreetMap API 0.6: /relation/21913346/full, /map in 12 tiles over the extent bbox, and /relation/<id>/full '
              'for 3 multipolygons the tiles left incomplete',
    'requests': [{k: r[k] for k in ('url', 'start_utc', 'end_utc', 'http', 'bytes', 'sha256')} for r in log],
    'downloaded_utc': summ['downloaded_utc'],
    'database_state': ('as served by the API at the download times above; the newest element in the download is '
                       'dated %s. Every kept element is listed with its version in osm_elements.json.'
                       % summ['newest_element_timestamp']),
    'date_checked': '2026-11-14',
    'licence': 'ODbL 1.0 (Open Database License), https://opendatacommons.org/licenses/odbl/1-0/',
    'licence_quote': ODBL,
    'attribution': '(c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright',
    'odbl_notice': ('This extract is a Derivative Database of OpenStreetMap: (c) OpenStreetMap contributors, made available '
                    'under the Open Database License 1.0. Any derived database made from it must also be offered under the '
                    'ODbL 1.0; produced works (renders, images) need the attribution above.'),
    'redistributable': 'yes, under ODbL 1.0 with attribution (share-alike for derived databases)',
    # counts only (re-verify 2 R1, fix round 3): per class and per rule, nothing that describes a dropped feature
    'filter_note': ('Sensitive-feature filter applied before anything was written (docs/PLAN.md s.6b Q3 default; tag and '
                    'name rule in tools/law/osm_sensitive.py: military, armed police, police incl. surveillance cameras, '
                    'prison / detention, GNSS / geodetic stations). Dropped: %d element(s), %d by the tag rule and %d by '
                    'the second-order rules of tools/osm/pin_extract.py (on / along a dropped area or line, railway '
                    'points, non-passenger railway); %d vertex(es) that kept ways shared with dropped features removed '
                    '(rule g). Counts per class and per rule, the rule definitions and which classes each rule exempts '
                    'are in pin_summary.json (dropped_sensitive, vertices_removed, dropped_rules). No id, name, '
                    'position, size or distance of a dropped feature is written in this directory or in any committed '
                    'file; osm_elements.json lists no node that belongs only to dropped features. docs/phase1/qa_data.md.'
                    % (sum(summ['dropped_sensitive'].values()),
                       sum(v for k, v in summ['dropped_sensitive'].items() if k.split(':', 1)[1].split('_member')[0] in
                           ('military', 'armed_police', 'police', 'prison', 'gnss')),
                       sum(v for k, v in summ['dropped_sensitive'].items() if k.split(':', 1)[1].split('_member')[0] not in
                           ('military', 'armed_police', 'police', 'prison', 'gnss')),
                       sum(summ.get('vertices_removed', {}).values()))),
    'clip_note': 'every geometry clipped to extent_hull1km.geojson; property clipped=true where cut',
    'generator': 'tools/osm/fetch_osm.py (download) + tools/osm/pin_extract.py (merge, filter, clip; python3 -I)',
    'commit': 'meant to be committed (redistributable, filtered)',
    'files': files(pin),
}, open(os.path.join(pin, 'SOURCES.json'), 'w'), indent=1, ensure_ascii=False)

json.dump({
    'topic': 'osm_pinned_raw',
    'what': 'raw OSM API 0.6 responses behind refs/cache/osm_pinned/ (12 /map tiles + 4 relation/full)',
    'requests': log,
    'date_checked': '2026-11-14',
    'licence': 'ODbL 1.0', 'licence_quote': ODBL,
    'attribution': '(c) OpenStreetMap contributors',
    'redistributable': 'licence: yes (ODbL); project rule: NO - the raw tiles still contain the sensitive features '
                       'that osm_pinned/ removes. Keep local; never commit.',
    'untrusted': 'downloaded data; parsed only by python3 -I scripts outside this directory',
    'files': files(raw),
}, open(os.path.join(raw, 'SOURCES.json'), 'w'), indent=1)

geo = os.path.join(root, 'refs/cache/geoid_egm2008')
json.dump({
    'topic': 'geoid_egm2008',
    'what': 'window 31.0-31.4 N, 121.0-121.7 E of the NGA EGM2008 2.5-minute geoid grid (WGS 84 -> EGM2008 height), '
            'read by HTTP range requests (rasterio /vsicurl), values unmodified',
    'url': 'https://cdn.proj.org/us_nga_egm08_25.tif',
    'downloaded_utc': '2026-11-14T04:49:12Z',
    'date_checked': '2026-11-14',
    'licence': 'public domain (NGA)',
    'licence_quote': 'GeoTIFF tag TIFFTAG_COPYRIGHT: "Derived from work by NGA. Public Domain"; TIFFTAG_IMAGEDESCRIPTION: '
                     '"WGS 84 (EPSG:4979) to EGM2008 height (EPSG:3855). Converted from egm08_25.gtx (last modified at '
                     '2018/10/08)"',
    'redistributable': 'yes (public domain)',
    'use': 'tools/common/frame.py GEOID_N0 / gradient (bilinear N = 11.267 m at the scene origin)',
    'files': files(geo),
}, open(os.path.join(geo, 'SOURCES.json'), 'w'), indent=1)
print('ok')
