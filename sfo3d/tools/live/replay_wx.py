#!/usr/bin/env python3
"""Weather / runway-configuration context for the traffic audit: KSFO METARs and the D-ATIS text.

Sources (both retrieved into refs/cache/replay/wx/, gitignored):
  * METAR: aviationweather.gov Data API, https://aviationweather.gov/api/data/metar?ids=KSFO&format=json&hours=N
    (NOAA/NWS Aviation Weather Center; US Government work).
  * D-ATIS: https://atis.info/api/KSFO (third-party mirror of the FAA D-ATIS; datis.clowd.io redirects there).
    Its terms were not found/checked [UNVERIFIED] -> poll sparingly (default every 10 min), research use only,
    never ship it in the app without checking.
Usage:
  python3 tools/live/replay_wx.py fetch            # one METAR (last 6 h) + one ATIS snapshot
  python3 tools/live/replay_wx.py poll [minutes]   # ATIS every 10 min (+ METAR hourly) for the given duration
  python3 tools/live/replay_wx.py show             # print the METAR/ATIS timeline (deduplicated)
"""
import glob, json, os, sys, time, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WX = os.path.join(ROOT, 'refs', 'cache', 'replay', 'wx')
UA = 'sfo-live-3d/0.1 (personal non-commercial research; traffic audit)'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch(hours=6, metar=True):
    os.makedirs(WX, exist_ok=True)
    ts = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    if metar:
        try:
            open(os.path.join(WX, f'metar_ksfo_{ts}.json'), 'wb').write(get(f'https://aviationweather.gov/api/data/metar?ids=KSFO&format=json&hours={hours}'))
        except Exception as e:
            print('metar', e, file=sys.stderr)
    try:
        open(os.path.join(WX, f'atis_ksfo_{ts}.json'), 'wb').write(get('https://atis.info/api/KSFO'))
    except Exception as e:
        print('atis', e, file=sys.stderr)


def timeline():
    """(metars {obsTime: dict}, atis {(code, time): dict}) from every cached file, including other agents' copies."""
    metars, atis = {}, {}
    for f in sorted(glob.glob(os.path.join(WX, 'metar_*.json')) + glob.glob(os.path.join(ROOT, 'refs', 'cache', 'feeds', 'metar_ksfo*.json'))):
        try:
            for m in json.load(open(f)):
                metars[m['obsTime']] = m
        except Exception:
            pass
    for f in sorted(glob.glob(os.path.join(WX, 'atis_*.json')) + glob.glob(os.path.join(ROOT, 'refs', 'cache', 'atc', 'datis_ksfo*.json'))):
        try:
            for a in json.load(open(f)):
                atis.setdefault((a['code'], a['time']), dict(a, first_seen=a.get('updatedAt')))
        except Exception:
            pass
    return metars, atis


def runway_config(text):
    """parse the approach/departure runways out of a D-ATIS text (FAA phraseology as seen in the SFO messages)."""
    import re
    t = text.upper()
    app = re.findall(r'(?:ILS|VISUAL|RNAV|LOC|GLS)[^.]*?RY\s*(\d+[LR])[^.]*?APP', t) + re.findall(r'APCHS? (?:IN USE )?(?:TO )?RWYS? ([\d LR,AND]+)', t)
    dep = re.findall(r'DEPG RWYS? ([\d LR,AND]+)', t)
    clsd = re.findall(r'RY ([\d LR,]+) CLSD', t)
    return dict(app=app, dep=dep, closed=clsd)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'show'
    if cmd == 'fetch':
        fetch()
    elif cmd == 'poll':
        until = time.time() + 60 * float(sys.argv[2] if len(sys.argv) > 2 else 240)
        k = 0
        while time.time() < until:
            fetch(metar=(k % 6 == 0)); k += 1
            time.sleep(600)
    else:
        M, A = timeline()
        for t in sorted(M):
            print(time.strftime('%H:%MZ', time.gmtime(t)), M[t]['rawOb'])
        for k in sorted(A, key=lambda k: A[k]['time']):
            a = A[k]; print(a['code'], a['time'], runway_config(a['datis']), a['datis'][:400])
