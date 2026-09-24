"""Fetch the X-Plane Scenery Gateway's recommended KSFO scenery pack and extract its apt.dat.

Source (Gateway public API, no key):
  https://gateway.x-plane.com/apiv1/airport/KSFO        -> airport record, `recommendedSceneryId`
  https://gateway.x-plane.com/apiv1/scenery/<id>        -> scenery record, `masterZipBlob` = base64 of a zip that holds
                                                           KSFO.txt (the apt.dat airport block), KSFO.dsf/.dsf.txt, ...
Writes (third-party data; refs/ is gitignored):
  refs/cache/xplane/airport_KSFO.json, scenery_<id>.json (blob stripped), scenery_<id>.zip, KSFO_<id>/ (unzipped),
  apt_<id>.dat (the apt.dat text) and fetch_log.json (URLs, HTTP status, UTC time, sha256).
Usage: python3 tools/xcheck/fetch_xplane.py [--id SCENERY_ID] [--force]
"""
import argparse, base64, datetime, hashlib, io, json, os, sys, urllib.request, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'refs', 'cache', 'xplane')
API = 'https://gateway.x-plane.com/apiv1'
UA = 'sfo3d-xcheck/1.0 (research; contact via repo owner)'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', type=int, help='scenery id (default: the airport record\'s recommendedSceneryId)')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = []
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    url = f'{API}/airport/KSFO'
    st, body = get(url)
    open(os.path.join(OUT, 'airport_KSFO.json'), 'wb').write(body)
    log.append({'url': url, 'status': st, 'utc': now, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    ap_rec = json.loads(body)['airport']
    sid = a.id or ap_rec['recommendedSceneryId']
    print('recommendedSceneryId', ap_rec['recommendedSceneryId'], '-> using', sid)
    zpath = os.path.join(OUT, f'scenery_{sid}.zip')
    if a.force or not os.path.exists(zpath):
        url = f'{API}/scenery/{sid}'
        st, body = get(url)
        rec = json.loads(body)['scenery']
        blob = base64.b64decode(rec.pop('masterZipBlob'))
        open(zpath, 'wb').write(blob)
        json.dump(rec, open(os.path.join(OUT, f'scenery_{sid}.json'), 'w'), indent=1)
        log.append({'url': url, 'status': st, 'utc': now, 'bytes': len(body), 'zip_sha256': hashlib.sha256(blob).hexdigest()})
    z = zipfile.ZipFile(zpath)
    xdir = os.path.join(OUT, f'KSFO_{sid}')
    z.extractall(xdir)
    names = z.namelist()
    print('zip members:', names)
    # members: KSFO.dat (apt.dat block), KSFO.txt (DSF as text), KSFO_Scenery_Pack.zip (the pack users download:
    # COPYING (GPL v2), README.txt, 'Earth nav data/apt.dat' (= KSFO.dat plus the 1500 jetway rows), the .dsf).
    # Use the pack's apt.dat: it is the file X-Plane loads and it is the superset.
    txt = None
    pk = [n for n in names if n.lower().endswith('_scenery_pack.zip')]
    if pk:
        pz = zipfile.ZipFile(io.BytesIO(z.read(pk[0])))
        pz.extractall(xdir)
        m = [n for n in pz.namelist() if n.endswith('Earth nav data/apt.dat')]
        if m: txt, src = pz.read(m[0]).decode('utf-8', 'replace'), pk[0] + ':' + m[0]
    if txt is None:
        src = [n for n in names if n.lower().endswith('.dat')][0]
        txt = z.read(src).decode('utf-8', 'replace')
    txt = txt.replace('\r\n', '\n')
    open(os.path.join(OUT, f'apt_{sid}.dat'), 'w').write(txt)
    print('apt.dat from', src, len(txt.splitlines()), 'lines; header:', txt.splitlines()[:2])
    json.dump(log, open(os.path.join(OUT, 'fetch_log.json'), 'w'), indent=1)


if __name__ == '__main__':
    sys.exit(main())
