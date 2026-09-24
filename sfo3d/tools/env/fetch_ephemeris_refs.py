#!/usr/bin/env python3
"""tools/env/fetch_ephemeris_refs.py

Downloads the raw reference data that tools/env/build_ephemeris_fixtures.mjs turns into
tools/env/fixtures/ephemeris_ref.json (the fixture tools/env/test_ephemeris.mjs checks ephemeris.mjs against).
Everything goes to refs/cache/sun_night/ (gitignored). Files that already exist are skipped (use --force to refetch).
Stdlib only. Run from anywhere: python3 tools/env/fetch_ephemeris_refs.py

Sources (all public, no key):
  - JPL Horizons API  https://ssd.jpl.nasa.gov/api/horizons.api  (DE441; observer table at the SFO ARP)
  - NOAA/GML Solar Calculator code  https://gml.noaa.gov/grad/solcalc/main.js
  - USNO Astronomical Applications  https://aa.usno.navy.mil/  (year tables, one-day data, Moon phases)
Be polite: Horizons queries are spaced 1 s apart; there are 20 of them.
"""
import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'refs', 'cache', 'sun_night')
FORCE = '--force' in sys.argv
LAT, LON, HKM = 37.6188056, -122.3754167, 0.004      # SFO ARP (js/geo.js; AirNav), field elevation 13.1 ft
DATES = [('2026-02-11', 8), ('2026-06-21', 7), ('2026-09-23', 7), ('2026-11-03', 8), ('2026-12-21', 8)]  # UTC offset of local midnight
UA = {'User-Agent': 'sfo3d-ephemeris-refs/1.0 (research script)'}


def get(url, path, binary=False):
    full = os.path.join(OUT, path)
    if os.path.exists(full) and not FORCE:
        return False
    os.makedirs(os.path.dirname(full), exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with open(full, 'wb') as f:
        f.write(data)
    print('fetched', path, len(data))
    return True


def horizons():
    for d, off in DATES:
        t0 = datetime.datetime.fromisoformat(d) + datetime.timedelta(hours=off)
        t1 = t0 + datetime.timedelta(hours=24)
        for body, name in (('10', 'sun'), ('301', 'moon')):
            for refr in ('AIRLESS', 'REFRACTED'):
                path = f'horizons/{name}_{d}_{refr.lower()}.json'
                if os.path.exists(os.path.join(OUT, path)) and not FORCE:
                    continue
                p = {'format': 'json', 'COMMAND': f"'{body}'", 'OBJ_DATA': 'NO', 'MAKE_EPHEM': 'YES',
                     'EPHEM_TYPE': 'OBSERVER', 'CENTER': "'coord@399'", 'COORD_TYPE': 'GEODETIC',
                     'SITE_COORD': f"'{LON},{LAT},{HKM}'", 'START_TIME': f"'{t0:%Y-%m-%d %H:%M}'",
                     'STOP_TIME': f"'{t1:%Y-%m-%d %H:%M}'", 'STEP_SIZE': "'60 m'", 'QUANTITIES': "'2,4,10,13,20,24'",
                     'APPARENT': refr, 'ANG_FORMAT': 'DEG', 'CSV_FORMAT': 'YES', 'TIME_DIGITS': 'SECONDS',
                     'EXTRA_PREC': 'YES', 'CAL_FORMAT': 'BOTH', 'TIME_TYPE': 'UT'}
                url = 'https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(p, safe="'@,")
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                    js = json.load(r)
                js['_url'] = url
                os.makedirs(os.path.join(OUT, 'horizons'), exist_ok=True)
                with open(os.path.join(OUT, path), 'w') as f:
                    json.dump(js, f)
                print('fetched', path)
                time.sleep(1.0)


def main():
    horizons()
    get('https://gml.noaa.gov/grad/solcalc/main.js', 'noaa_main.js')
    get('https://gml.noaa.gov/grad/solcalc/calcdetails.html', 'noaa_calcdetails.html')
    for task in (0, 1, 2, 3, 4):
        get('https://aa.usno.navy.mil/calculated/rstt/year?ID=AA&year=2026&task=%d&lat=37.6188&lon=-122.3754'
            '&label=SFO&tz=8.00&tz_sign=-1&submit=Get+Data' % task, 'usno_year_task%d.html' % task)
    get('https://aa.usno.navy.mil/api/moon/phases/year?year=2026', 'usno_moonphases_2026.json')
    for d, _ in DATES:
        name = 'usno_rstt_20260923.json' if d == '2026-09-23' else f'usno_rstt_{d}.json'
        get(f'https://aa.usno.navy.mil/api/rstt/oneday?date={d}&coords=37.6188,-122.3754&tz=-8&dst=true', name)
    get('https://aa.usno.navy.mil/faq/RST_defs', 'usno_rst_defs.html')
    get('https://datacenter.iers.org/data/latestVersion/bulletinA.txt', 'iers_bulletinA.txt')
    # USNO Circular 171 (illuminance model), US Government work, via the Internet Archive (DTIC ADA182110)
    get('https://archive.org/download/DTIC_ADA182110/DTIC_ADA182110.pdf', 'circ171.pdf')
    print('done; now run: node tools/env/build_ephemeris_fixtures.mjs && node tools/env/test_ephemeris.mjs')


if __name__ == '__main__':
    main()
