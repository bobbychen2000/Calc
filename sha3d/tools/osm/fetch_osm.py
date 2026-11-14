"""Fetch OSM API 0.6 data for the SHA detailed extent (polite: sequential, 1.5 s apart, generic User-Agent).

usage:
  python3 -I fetch_osm.py full OUT_DIR relation 21913346        -> OUT_DIR/relation_21913346_full.osm
  python3 -I fetch_osm.py map  OUT_DIR lon0 lat0 lon1 lat1 STEP  -> OUT_DIR/map_<bbox>.osm tiles of STEP degrees
Every request is appended to OUT_DIR/download_log.jsonl (url, UTC start/end, HTTP status, bytes, sha256). The responses
are untrusted data: this script only writes them to disk; parse them with python3 -I from a separate script.
"""
import datetime
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.request

API = 'https://api.openstreetmap.org/api/0.6/'
UA = 'sha3d-airport-pin/1.0 (offline research extract; python-urllib)'
CTX = ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE', '/root/.ccr/ca-bundle.crt'))


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get(url, path, log):
    t0 = now()
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=180) as r:
                data = r.read(); status = r.status
            break
        except Exception as e:  # noqa: BLE001
            print('retry', attempt, url, e, file=sys.stderr); time.sleep(5 * (attempt + 1))
    else:
        raise SystemExit('failed ' + url)
    with open(path, 'wb') as f:
        f.write(data)
    rec = dict(url=url, file=os.path.basename(path), start_utc=t0, end_utc=now(), http=status, bytes=len(data),
               sha256=hashlib.sha256(data).hexdigest())
    with open(log, 'a') as f:
        f.write(json.dumps(rec) + '\n')
    print(rec['file'], status, len(data))
    time.sleep(1.5)


mode, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
log = os.path.join(out, 'download_log.jsonl')
if mode == 'full':
    typ, oid = sys.argv[3], sys.argv[4]
    get(f'{API}{typ}/{oid}/full', os.path.join(out, f'{typ}_{oid}_full.osm'), log)
elif mode == 'map':
    lon0, lat0, lon1, lat1, step = map(float, sys.argv[3:8])
    nx = max(1, round((lon1 - lon0) / step + 0.4999)); ny = max(1, round((lat1 - lat0) / step + 0.4999))
    dx = (lon1 - lon0) / nx; dy = (lat1 - lat0) / ny
    for i in range(nx):
        for j in range(ny):
            b = (lon0 + i * dx, lat0 + j * dy, lon0 + (i + 1) * dx, lat0 + (j + 1) * dy)
            bb = ','.join(f'{v:.6f}' for v in b)
            get(f'{API}map?bbox={bb}', os.path.join(out, 'map_' + bb.replace(',', '_') + '.osm'), log)
