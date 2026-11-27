#!/usr/bin/env python3
"""Build data/sha_snapshot.js (window.SHA_SNAPSHOT) and data/sha_snapshot.json: the data of the app's 'snapshot' mode
(static page, no network): a recorded set of ZSSS METARs and the TAF in force, at one chosen instant, and the traffic
set (empty: open ADS-B does not cover Hongqiao; a replay pack of simulated, inferred traffic is Phase 3).

New for sha3d (sfo3d's data/snapshot.js mixed adsb.fi records - a licence conflict, arch.md s.3.9 - and is not forked).

  python3 -I tools/live/build_snapshot.py --fetch            download once from aviationweather.gov into
                                                           refs/cache/metar/snapshot_<yyyymmdd>/ (3 requests), then build
  python3 -I tools/live/build_snapshot.py [--dir DIR] [--at ISO]   build from the cached files only (deterministic)
  python3 -I tools/live/build_snapshot.py --fetch-days     one-off pull (Phase 3, design s.7.2 P3-A / review L4) of the AWC
                                                           JSON METARs of the replay days that the local cache lacks
                                                           (DAY_PULLS: 2 requests, >= 10 min apart, the relay's own client
                                                           and User-Agent) into refs/cache/metar/awc_days/, then build

Every build also writes SHA_SNAPSHOT.days[] (Phase 3 replay days 10 / 12 / 13 / 14 / 20 Nov 2026, design s.7.1): the METAR /
SPECI of each operating day (04:00-04:00 UTC+8) plus a 2 h look-back, from every cached source (AWC JSON with receipt
times first, then the AWC raw text, then the IEM archive), with src and a 'complete' flag (routine reports every 30 min
with no gap over 60 min across the window); traffic = {kind: 'sim', day, planVersion} (the day plan, js/sim/plan.js).

The weather data are NOAA/NWS (AWC) data; the hosts state public domain for what they serve, the reports themselves are
issued by the CAAC aviation meteorological service; credit both and never present them as official (sources_sim.md
s.3.1). They may be committed with the attribution (refs/cache/metar/SOURCES.json: redistributable).
Only the identity / time fields and the raw text are kept (the AWC JSON weather fields are lossy for ZSSS).
"""
import argparse, datetime as dt, glob, hashlib, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))           # sha3d/
CACHE = os.path.join(ROOT, 'refs', 'cache', 'metar')
UA = 'sha-live-3d-tools/0.1 (personal non-commercial visualisation; python-stdlib)'    # generic: no names, no URL
AWC = 'https://aviationweather.gov/api/data/'
ATTRIBUTION = ('Weather: NOAA/NWS Aviation Weather Center (aviationweather.gov) data; the ZSSS reports are issued by the '
               'CAAC aviation meteorological service. Not official NOAA material.')
ATTRIBUTION_IEM = 'Weather archive: Iowa Environmental Mesonet, Iowa State University (replay days).'
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


# Phase 3 replay days (design s.7.1 SHA_SNAPSHOT.days[], s.7.2 P3-A): the operating day runs 04:00-04:00 UTC+8 =
# 20:00Z (D-1) .. 20:00Z (D); the runway timeline looks back 2 h before t0 (design s.1.4), so each day needs
# 18:00Z (D-1) .. 20:00Z (D). The local cache (refs/cache/metar: IEM to 13 Nov 23:50Z, AWC 30 d / 24 h to 14 Nov 05:25Z,
# snapshot_20261120 from 19 Nov 22:30Z) lacks 14 Nov after 05:25Z and 19 Nov 18:00-22:30Z, hence one AWC JSON pull per
# day (AWC keeps 30 days; 'date' = window end, 'hours' = look-back; sources_sim.md s.3.1).
DAY_PULLS = (('2026-11-14', '20261114_2000', 26), ('2026-11-20', '20261120_2000', 26))
AWC_GAP_S = 600.0               # at most one aviationweather.gov request per 10 min (sha3d CLAUDE.md "Feeds")


def _relay_client():
    """The relay's own client (sha_live_server.http_get: generic User-Agent, urllib, gzip) - imported by path because the
    tools run with python3 -I."""
    sys.path.insert(0, ROOT)
    try:
        import sha_live_server as R
    finally:
        sys.path.pop(0)
    return R.http_get, R.UA


def _last_awc_download(S):
    ts = []
    for f in S.get('files', {}).values():
        u = f.get('downloaded_utc')
        if u and 'aviationweather.gov' in f.get('url', ''):
            try:
                ts.append(dt.datetime.fromisoformat(u.replace('Z', '+00:00')).timestamp())
            except ValueError:
                pass
    return max(ts) if ts else 0.0


def do_fetch_days():
    """One request per missing day file; waits until >= 10 min after the last recorded AWC download (SOURCES.json, so
    the guard also holds across invocations). Raw responses are kept unchanged."""
    http_get, ua = _relay_client()
    d = os.path.join(CACHE, 'awc_days')
    os.makedirs(d, exist_ok=True)
    src = os.path.join(CACHE, 'SOURCES.json')
    for day, end, hours in DAY_PULLS:
        name = f'metar_{end}_h{hours}.json'
        path = os.path.join(d, name)
        if os.path.exists(path):
            print('cached', name)
            continue
        S = json.load(open(src))
        wait = _last_awc_download(S) + AWC_GAP_S - time.time()
        if wait > 0:
            print(f'waiting {wait:.0f} s (one aviationweather.gov request per 10 min)', flush=True)
            time.sleep(wait + 1)
        url = AWC + f'metar?ids=ZSSS&format=json&hours={hours}&date={end}'
        code, hd, body = http_get(url, timeout=30, headers={'Accept': 'application/json'})
        t = time.time()
        if code != 200 or not body.strip().startswith(b'['):
            S['files']['awc_days/' + name + '.error'] = {'url': url, 'downloaded_utc': iso(t), 'status': code}
            json.dump(S, open(src, 'w'), indent=1, ensure_ascii=False)
            sys.exit(f'AWC answered HTTP {code} for {url}: {body[:200]!r}')
        open(path, 'wb').write(body)
        S = json.load(open(src))
        S['files']['awc_days/' + name] = {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'url': url,
                                          'downloaded_utc': iso(t), 'user_agent': ua,
                                          'use': f'SHA_SNAPSHOT.days[] operating day {day} (18:00Z D-1 .. 20:00Z D)'}
        S['use_days'] = ('tools/live/build_snapshot.py -> data/sha_snapshot.js days[] (Phase 3 replay days: 10 / 12 / 13 / '
                         '14 / 20 Nov 2026; one-off pulls in awc_days/, design s.7.2 P3-A)')
        json.dump(S, open(src, 'w'), indent=1, ensure_ascii=False)
        print('fetched', name, len(body), 'bytes, HTTP', code, flush=True)


# ------------------------------------------------------------------------------------------------ replay days (Phase 3)
REPLAY_DAYS = ('2026-11-10', '2026-11-12', '2026-11-13', '2026-11-14', '2026-11-20')
LOOKBACK_H = 2                  # the runway timeline starts from a report up to 2 h before t0 (design s.1.4)
SNAPSHOT_DAY = '2026-11-20'     # the operating day of the snapshot instant (traffic.kind 'sim')
PLAN_VERSION = 1                # js/sim/rng.js PLAN_VERSION


def _norm(raw):
    return ' '.join((raw or '').replace('=', ' ').split())


def _rtype(raw):
    t = _norm(raw).split(' ')[0]
    return t if t in ('METAR', 'SPECI') else None


def gather_reports():
    """every cached ZSSS report -> {(obsTime, type): {obsTime, receiptTime, rawOb, src}}; AWC JSON (receipt time) first, then
    AWC raw text, then the IEM archive (no receipt time). IEM rows have no type: METAR at :00 / :30, else SPECI [inf: ZSSS
    reports every 30 min at :00 and :30, sources_sim.md s.3.2]."""
    out = {}

    def put(obs, rec, raw, src):
        raw = _norm(raw)
        typ = _rtype(raw)
        if not typ:
            typ = 'METAR' if time.gmtime(obs).tm_min in (0, 30) else 'SPECI'
            raw = typ + ' ' + raw
        k = (int(obs), typ)
        if k not in out:
            out[k] = {'obsTime': int(obs), 'receiptTime': rec, 'rawOb': raw, 'src': src}

    jfiles = sorted(glob.glob(os.path.join(CACHE, 'awc_days', '*.json'))) + sorted(glob.glob(os.path.join(CACHE, 'snapshot_*', 'metar_24h.json'))) + \
        [os.path.join(CACHE, 'awc_metar_zsss_24h.json')]
    for f in jfiles:
        if not os.path.exists(f):
            continue
        for m in json.load(open(f)):
            if m.get('icaoId') == 'ZSSS' and m.get('rawOb') and m.get('obsTime'):
                put(m['obsTime'], m.get('receiptTime'), m['rawOb'], 'awc')
    for f in sorted(glob.glob(os.path.join(CACHE, 'awc_30d', 'metar_raw_to_*.txt'))):
        mm = re.search(r'to_(\d{8})_(\d{4})', f)
        end = dt.datetime.strptime(mm.group(1) + mm.group(2), '%Y%m%d%H%M').replace(tzinfo=dt.timezone.utc)
        for line in open(f):
            line = line.strip()
            g = re.match(r'^(METAR|SPECI) ZSSS (\d{2})(\d{2})(\d{2})Z', line)
            if not g:
                continue
            dd, hh, mi = int(g.group(2)), int(g.group(3)), int(g.group(4))
            for back in range(0, 9):                      # the 168 h window ending at the file's 'to' time
                c = end - dt.timedelta(days=back)
                try:
                    cand = c.replace(day=dd, hour=hh, minute=mi, second=0, microsecond=0)
                except ValueError:
                    continue
                if end - dt.timedelta(hours=170) <= cand <= end:
                    put(cand.timestamp(), None, line, 'awc')
                    break
    for f in sorted(glob.glob(os.path.join(CACHE, 'iem_zsss', 'zsss_metar_*.csv'))):
        if not f.endswith('2026.csv') and not f.endswith('2025.csv'):
            continue
        with open(f) as fh:
            next(fh, None)
            for line in fh:
                parts = line.rstrip('\n').split(',', 2)
                if len(parts) < 3 or parts[0] != 'ZSSS' or not parts[2].startswith('ZSSS'):
                    continue
                t = dt.datetime.strptime(parts[1], '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone.utc).timestamp()
                put(t, None, parts[2], 'iem')
    return out


def build_days(reports):
    days = []
    L = sorted(reports.values(), key=lambda r: r['obsTime'])
    for day in REPLAY_DAYS:
        y, mo, d = (int(x) for x in day.split('-'))
        t0 = dt.datetime(y, mo, d, tzinfo=dt.timezone.utc).timestamp() - 4 * 3600      # 04:00 local = 20:00Z (D-1)
        t1 = t0 + 86400
        a = t0 - LOOKBACK_H * 3600
        sel = [r for r in L if a <= r['obsTime'] <= t1]
        routine = [r['obsTime'] for r in sel if r['rawOb'].startswith('METAR')]
        gaps = [y2 - y1 for y1, y2 in zip(routine, routine[1:])]
        maxgap = max(gaps) if gaps else None
        complete = bool(routine) and routine[0] <= a + 1800 and routine[-1] >= t1 - 1800 and maxgap is not None and maxgap <= 3600
        srcs = sorted({r['src'] for r in sel})
        src = srcs[0] if len(srcs) == 1 else 'awc+iem'
        n_rec = sum(1 for r in sel if r['receiptTime'])
        days.append({
            'day': day, 't0': int(t0 * 1000), 't1': int(t1 * 1000), 'from': int(a * 1000), 'src': src, 'complete': complete,
            'metars': [{'obsTime': r['obsTime'], 'receiptTime': r['receiptTime'], 'rawOb': r['rawOb']} for r in sel],
            'notes': f'operating day 04:00-04:00 UTC+8 plus {LOOKBACK_H} h look-back; {len(sel)} reports ({len(routine)} routine, '
                     f'{len(sel) - len(routine)} SPECI), {n_rec} with an AWC receipt time (the others become available at obsTime + '
                     f'20 min, design s.1.4); largest gap between routine reports {int(maxgap // 60) if maxgap else "-"} min; '
                     f'sources: {", ".join(srcs)}',
        })
    return days


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
        'traffic': {'kind': 'sim', 'day': SNAPSHOT_DAY, 'planVersion': PLAN_VERSION, 'ac': [], 'src': 'inf',
                    'note': 'No recorded traffic: open ADS-B does not cover Hongqiao (docs/PLAN.md s.3). The traffic is simulated '
                            'from the day plan of this operating day (js/sim/plan.js, Phase 3), every aircraft labelled inferred.'},
        'days': build_days(gather_reports()),
        'days_note': 'Phase 3 replay days (design s.7.1): METAR / SPECI of each operating day 04:00-04:00 UTC+8 plus a 2 h look-back; '
                     'receiptTime from the AWC JSON where cached, else null (IEM archive, AWC raw text)',
        'attribution': [ATTRIBUTION],
        'choice': 'snapshot instant = 12:15 local on the last full local day of the downloaded 24 h window (a daylight '
                  'scene) unless --at is given; reports after it are dropped [inf choice]',
    }
    if any(d['src'] != 'awc' for d in out['days']):
        out['attribution'].append(ATTRIBUTION_IEM)
    js = '// generated by tools/live/build_snapshot.py - do not edit. ' + ATTRIBUTION + '\nwindow.SHA_SNAPSHOT = ' + \
         json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(os.path.join(ROOT, 'data', 'sha_snapshot.js'), 'w').write(js)
    json.dump(out, open(os.path.join(ROOT, 'data', 'sha_snapshot.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'data/sha_snapshot.js: now {out["now_utc"]}, {len(metars)} METARs ({metars[-1]["rawOb"][:24]} .. {metars[0]["rawOb"]}), '
          f'{len(tafs)} TAFs; replay days: ' + ', '.join(f'{d["day"]} {len(d["metars"])} ({d["src"]}, complete {d["complete"]})' for d in out['days']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--dir', help='cached snapshot directory (default: the newest refs/cache/metar/snapshot_*)')
    ap.add_argument('--at', help='snapshot instant (UTC ISO)')
    ap.add_argument('--fetch-days', action='store_true', help='one-off AWC pull of the missing replay days (DAY_PULLS)')
    a = ap.parse_args()
    if a.fetch_days:
        do_fetch_days()
    d = do_fetch(a.at) if a.fetch else (a.dir or (sorted(glob.glob(os.path.join(CACHE, 'snapshot_*'))) or [None])[-1])
    if not d:
        sys.exit('no cached snapshot: run with --fetch')
    build(d, a.at)


if __name__ == '__main__':
    main()
