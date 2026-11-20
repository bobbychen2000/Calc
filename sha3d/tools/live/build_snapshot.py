#!/usr/bin/env python3
"""Build data/sha_snapshot.js (window.SHA_SNAPSHOT) and data/sha_snapshot.json: the data of the app's 'snapshot' mode
(static page, no network): a recorded set of ZSSS METARs and the TAF in force, at one chosen instant, and the traffic
set (empty: open ADS-B does not cover Hongqiao; a replay pack of simulated, inferred traffic is Phase 3).

New for sha3d (sfo3d's data/snapshot.js mixed adsb.fi records - a licence conflict, arch.md s.3.9 - and is not forked).

  python3 -I tools/live/build_snapshot.py --fetch            download once from aviationweather.gov into
                                                           refs/cache/metar/snapshot_<yyyymmdd>/ (3 requests), then build
  python3 -I tools/live/build_snapshot.py [--dir DIR] [--at ISO]   build from the cached files only (deterministic)

The weather data are NOAA/NWS (AWC) data; the hosts state public domain for what they serve, the reports themselves are
issued by the CAAC aviation meteorological service; credit both and never present them as official (sources_sim.md
s.3.1). They may be committed with the attribution (refs/cache/metar/SOURCES.json: redistributable).
Only the identity / time fields and the raw text are kept (the AWC JSON weather fields are lossy for ZSSS).
"""
import argparse, datetime as dt, glob, hashlib, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))           # sha3d/
CACHE = os.path.join(ROOT, 'refs', 'cache', 'metar')
UA = 'sha-live-3d-tools/0.1 (personal non-commercial visualisation; python-stdlib)'    # generic: no names, no URL
AWC = 'https://aviationweather.gov/api/data/'
ATTRIBUTION = ('Weather: NOAA/NWS Aviation Weather Center (aviationweather.gov) data; the ZSSS reports are issued by the '
               'CAAC aviation meteorological service. Not official NOAA material.')
KEEP_M = ('icaoId', 'metarType', 'obsTime', 'reportTime', 'receiptTime', 'rawOb')
KEEP_T = ('icaoId', 'issueTime', 'validTimeFrom', 'validTimeTo', 'rawTAF')


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def fetch(url, path):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    open(path, 'wb').write(body)
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'url': url, 'downloaded_utc': iso(time.time())}


def do_fetch(at=None):
    now = time.time()
    d = os.path.join(CACHE, 'snapshot_' + time.strftime('%Y%m%d', time.gmtime(now)))
    os.makedirs(d, exist_ok=True)
    files = {}
    files['metar_24h.json'] = fetch(AWC + 'metar?ids=ZSSS&format=json&hours=24', os.path.join(d, 'metar_24h.json'))
    files['taf_current.json'] = fetch(AWC + 'taf?ids=ZSSS&format=json', os.path.join(d, 'taf_current.json'))
    # the TAF in force at the snapshot instant (time=issue&date=yyyymmdd_hhmm: the TAF issued last before that time;
    # sources_sim.md s.3.1)
    M = [m for m in json.load(open(os.path.join(d, 'metar_24h.json'))) if m.get('rawOb')]
    t = snapshot_instant(sorted(M, key=lambda m: m['obsTime']), at)
    stamp = time.strftime('%Y%m%d_%H%M', time.gmtime(t))
    files['taf_at_snapshot.json'] = fetch(AWC + f'taf?ids=ZSSS&format=json&time=issue&date={stamp}', os.path.join(d, 'taf_at_snapshot.json'))
    src = os.path.join(CACHE, 'SOURCES.json')
    S = json.load(open(src))
    for k, v in files.items():
        S['files'][os.path.basename(d) + '/' + k] = v
    S.setdefault('use_snapshot', 'tools/live/build_snapshot.py -> data/sha_snapshot.js (the app\'s snapshot mode)')
    json.dump(S, open(src, 'w'), indent=1, ensure_ascii=False)
    print('fetched', d, json.dumps(files, indent=1))
    return d


def snapshot_instant(M, at=None):
    """--at, else 12:15 local (04:15Z) on the last full local day in the window [inf choice: a daylight scene], never
    later than the latest report + 25 min. M sorted by obsTime."""
    if at:
        return dt.datetime.fromisoformat(at.replace('Z', '+00:00')).timestamp()
    last = M[-1]['obsTime']
    day = dt.datetime.fromtimestamp(last, dt.timezone.utc).replace(hour=4, minute=15, second=0, microsecond=0)
    while day.timestamp() > last + 25 * 60 or day.timestamp() < M[0]['obsTime'] + 3 * 3600:
        day -= dt.timedelta(days=1)
        if day.timestamp() < M[0]['obsTime']:
            return last + 15 * 60
    return day.timestamp()


def build(d, at=None):
    M = json.load(open(os.path.join(d, 'metar_24h.json')))
    T = []
    for f in ('taf_at_snapshot.json', 'taf_current.json'):
        p = os.path.join(d, f)
        if os.path.exists(p):
            try:
                T += json.load(open(p)) or []
            except ValueError:
                pass
    M = [{k: m[k] for k in KEEP_M if k in m} for m in M if m.get('icaoId') == 'ZSSS' and m.get('rawOb')]
    M.sort(key=lambda m: m['obsTime'])
    if not M:
        sys.exit('no METAR in ' + d)
    now = snapshot_instant(M, at)
    metars = [m for m in M if m['obsTime'] <= now]
    metars.sort(key=lambda m: m['obsTime'], reverse=True)
    seen, tafs = set(), []
    for t in T:
        if t.get('icaoId') != 'ZSSS' or not t.get('rawTAF') or t['rawTAF'] in seen:
            continue
        it = dt.datetime.fromisoformat(t['issueTime'].replace('Z', '+00:00')).timestamp()
        if it > now:
            continue                           # never a TAF issued after the snapshot
        seen.add(t['rawTAF'])
        tafs.append({'issued': iso(it), 'valid_from': iso(t['validTimeFrom']), 'valid_to': iso(t['validTimeTo']), 'raw': t['rawTAF']})
    tafs.sort(key=lambda x: x['issued'], reverse=True)
    out = {
        'what': 'SHA Live 3D snapshot mode: recorded ZSSS METARs and TAFs at one instant, and the traffic set (empty)',
        'generator': 'tools/live/build_snapshot.py', 'source_dir': os.path.relpath(d, ROOT),
        'now': int(now * 1000), 'now_utc': iso(now),
        'metars': metars, 'tafs': tafs,
        'traffic': {'kind': 'empty', 'ac': [], 'src': None,
                    'note': 'No recorded traffic: open ADS-B does not cover Hongqiao (docs/PLAN.md s.3). Phase 3 adds a replay '
                            'set of simulated traffic, every aircraft labelled inferred.'},
        'attribution': [ATTRIBUTION],
        'choice': 'snapshot instant = 12:15 local on the last full local day of the downloaded 24 h window (a daylight '
                  'scene) unless --at is given; reports after it are dropped [inf choice]',
    }
    js = '// generated by tools/live/build_snapshot.py - do not edit. ' + ATTRIBUTION + '\nwindow.SHA_SNAPSHOT = ' + \
         json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(os.path.join(ROOT, 'data', 'sha_snapshot.js'), 'w').write(js)
    json.dump(out, open(os.path.join(ROOT, 'data', 'sha_snapshot.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'data/sha_snapshot.js: now {out["now_utc"]}, {len(metars)} METARs ({metars[-1]["rawOb"][:24]} .. {metars[0]["rawOb"]}), '
          f'{len(tafs)} TAFs')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--dir', help='cached snapshot directory (default: the newest refs/cache/metar/snapshot_*)')
    ap.add_argument('--at', help='snapshot instant (UTC ISO)')
    a = ap.parse_args()
    d = do_fetch(a.at) if a.fetch else (a.dir or (sorted(glob.glob(os.path.join(CACHE, 'snapshot_*'))) or [None])[-1])
    if not d:
        sys.exit('no cached snapshot: run with --fetch')
    build(d, a.at)


if __name__ == '__main__':
    main()
