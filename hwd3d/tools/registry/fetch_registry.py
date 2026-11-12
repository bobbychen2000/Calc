#!/usr/bin/env python3
"""Download the FAA Releasable Aircraft Database (US civil aircraft registry) into hwd3d/refs/cache/local/registry/.

New for hwd3d (task G3c, 2026-11-12). No sfo3d file is forked: sfo3d/tools/models/build_brands.py @ a967f9b only reads
MASTER.txt / ACFTREF.txt from a copy someone downloaded by hand into sfo3d/refs/cache/faa/ (not in the repo).

Source (read 2026-11-12 on https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/
releasable_aircraft_download , link texts quoted):
  ZIP_URL "Download the Aircraft Registration Database (60MB)"  https://registry.faa.gov/database/ReleasableAircraft.zip
  DOC_URL "Download Documentation"                               https://registry.faa.gov/database/ardata.pdf
          (file layout and code tables; build_lookup.py checks its code labels against this PDF)
Licence: US Government work (17 U.S.C. 105), public domain. It is still NOT committed: owner's default D1
(docs/PLAN.md section 6a) keeps per-aircraft identity (N-number, owner name and address, Mode S hex) out of the repo.
The target directory refs/cache/local/ is gitignored (hwd3d/.gitignore).

Etiquette (owner's rule): one plain GET per file with Python's default urllib client (no custom headers, no retries
with other settings, no mirrors). registry.faa.gov answered HTTP 403 to automated requests on 2026-11-12. If it refuses
again, the refusal is appended to fetch_log.json and the script exits with status 2. Manual route for the owner:
open the FAA page above in a browser, save ReleasableAircraft.zip (and ardata.pdf) into
hwd3d/refs/cache/local/registry/, then run
    python3 -I hwd3d/tools/registry/fetch_registry.py --record-manual
which makes no network request: it only checks and hashes the files already there and logs them.

Outputs (all in refs/cache/local/registry/, gitignored):
  ReleasableAircraft.zip   the FAA zip as served (MASTER.txt, ACFTREF.txt, ENGINE.txt, DEREG.txt, ... inside)
  ardata.pdf               the FAA documentation
  fetch_log.json           every attempt: url, time (UTC), HTTP status or error, bytes, sha256, Last-Modified, zip members

usage: python3 -I hwd3d/tools/registry/fetch_registry.py [--force] [--no-doc] [--record-manual]
next:  python3 -I hwd3d/tools/registry/build_lookup.py
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT_DIR = os.path.join(HWD, 'refs', 'cache', 'local', 'registry')
LOG = os.path.join(OUT_DIR, 'fetch_log.json')
PAGE_URL = ('https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/'
            'releasable_aircraft_download')
ZIP_URL = 'https://registry.faa.gov/database/ReleasableAircraft.zip'
DOC_URL = 'https://registry.faa.gov/database/ardata.pdf'
FILES = {'ReleasableAircraft.zip': ZIP_URL, 'ardata.pdf': DOC_URL}
# members build_lookup.py needs (names as listed on the FAA page: "Master File", "Reference File")
NEEDED_MEMBERS = ('MASTER.txt', 'ACFTREF.txt')


def now():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def describe(path):
    """Size, sha256 and (for the zip) member list with sizes and dates, so a later build can name its input."""
    d = {'bytes': os.path.getsize(path), 'sha256': sha256(path)}
    if path.endswith('.zip'):
        if not zipfile.is_zipfile(path):
            d['error'] = 'not a zip file'
            return d
        with zipfile.ZipFile(path) as z:
            d['members'] = [{'name': i.filename, 'bytes': i.file_size,
                             'date': '%04d-%02d-%02dT%02d:%02d:%02d' % i.date_time} for i in z.infolist()]
        names = {m['name'] for m in d['members']}
        d['missing_members'] = [m for m in NEEDED_MEMBERS if m not in names]
    elif path.endswith('.pdf'):
        with open(path, 'rb') as f:
            d['pdf_magic_ok'] = f.read(5) == b'%PDF-'
    return d


def fetch(name, url, force):
    dst = os.path.join(OUT_DIR, name)
    rec = {'file': name, 'url': url, 'time': now(), 'client': 'python urllib default (%s)' % sys.version.split()[0]}
    if os.path.exists(dst) and not force:
        rec.update(status='skipped (file exists; --force to download again)', **describe(dst))
        return rec, True
    part = dst + '.part'
    try:
        with urllib.request.urlopen(url, timeout=600) as r, open(part, 'wb') as f:
            rec['http_status'] = r.status
            rec['last_modified'] = r.headers.get('Last-Modified')
            rec['content_type'] = r.headers.get('Content-Type')
            rec['content_length'] = r.headers.get('Content-Length')
            for b in iter(lambda: r.read(1 << 20), b''):
                f.write(b)
    except urllib.error.HTTPError as e:
        rec.update(http_status=e.code, status='refused' if e.code in (401, 403, 429) else 'http error',
                   reason=str(e.reason))
        if os.path.exists(part):
            os.remove(part)
        return rec, False
    except (urllib.error.URLError, OSError) as e:
        rec.update(status='network error', reason=repr(e))
        if os.path.exists(part):
            os.remove(part)
        return rec, False
    os.replace(part, dst)
    rec.update(status='downloaded', **describe(dst))
    ok = not rec.get('error') and not rec.get('missing_members') and rec.get('pdf_magic_ok', True)
    if not ok:
        rec['status'] = 'downloaded but content check failed'
    return rec, ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--force', action='store_true', help='download again even if the file exists')
    ap.add_argument('--no-doc', action='store_true', help='skip ardata.pdf')
    ap.add_argument('--record-manual', action='store_true',
                    help='no network: hash and log files the owner saved by hand into the target directory')
    a = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    log = json.load(open(LOG)) if os.path.exists(LOG) else {'page': PAGE_URL, 'attempts': []}
    results = []
    for name, url in FILES.items():
        if a.no_doc and name == 'ardata.pdf':
            continue
        if a.record_manual:
            p = os.path.join(OUT_DIR, name)
            rec = {'file': name, 'url': url, 'time': now(), 'status': 'manual download recorded' if os.path.exists(p)
                   else 'manual download missing'}
            if os.path.exists(p):
                rec.update(describe(p))
            ok = os.path.exists(p) and not rec.get('error') and not rec.get('missing_members')
        else:
            rec, ok = fetch(name, url, a.force)
        log['attempts'].append(rec)
        results.append((name, ok, rec))
        print('%-24s %-40s %s' % (name, rec.get('status'), rec.get('http_status', '')), flush=True)
        if not ok and name == 'ReleasableAircraft.zip' and not a.record_manual:
            break   # one refusal is the answer for this host: do not go on to the next file
    with open(LOG, 'w') as f:
        json.dump(log, f, indent=1)
    zip_ok = any(n == 'ReleasableAircraft.zip' and ok for n, ok, _ in results)
    if not zip_ok:
        print('\nThe registry zip is not available. Do not work around a refusal. Manual route: save\n  %s\n'
              'into %s (from the page %s),\nthen run fetch_registry.py --record-manual and build_lookup.py.'
              % (ZIP_URL, OUT_DIR, PAGE_URL))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
