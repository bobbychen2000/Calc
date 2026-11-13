"""Aircraft identity look-up from the Mictronics aircraft database (ODC-By 1.0), in place of the FAA registry download.

Why this source (2026-11-13): registry.faa.gov answers automated downloads of ReleasableAircraft.zip with an Akamai
"Access Denied" page, and we do not work around a site's bot filter; the Internet Archive copy of that file
(snapshot 2026-11-11T19:39:50Z) is unreachable here (the session's egress proxy closes web.archive.org tunnels).
Mictronics publishes a weekly export of its aircraft database - 24-bit address -> registration, ICAO type, model
description, flags - on GitHub under the Open Data Commons Attribution License (ODC-By 1.0, LICENSE in the repo:
"Aircraft database exports are made available under the Open Data Commons Attribution License").
It is NOT the FAA registry: it has no year of manufacture, engine or registrant fields, and its US entries are
compiled by Mictronics (source mix not stated in the repo). check() below measures its agreement with what the
aircraft at HWD themselves broadcast.

Source: https://github.com/Mictronics/aircraft-database (git, anonymous read), file indexedDB_old.zip ->
aircrafts.json {hex: {r, t, f, d}}, operators.json (ICAO operator designator -> name, country, callsign),
types.json (ICAO type -> description). Pinned commit below.
Outputs:
  refs/cache/local/registry/mictronics_lookup.json  (gitignored: per-aircraft identities, default D1)
  refs/cache/registry/mictronics_check.json         (committed: aggregate agreement at HWD, no identities)
Attribution (ODC-By 4.2/4.3): "Aircraft data: Mictronics aircraft database (https://www.mictronics.de/aircraft-database/),
Open Data Commons Attribution License 1.0".

usage: python3 -I tools/registry/mictronics_db.py fetch      # shallow git clone at PIN into refs/cache/local/registry/mictronics/
       python3 -I tools/registry/mictronics_db.py build      # local lookup
       python3 -I tools/registry/mictronics_db.py check      # aggregate agreement with the adsb.lol rec_pack (sfo3d)
"""
import collections, glob, hashlib, json, lzma, math, os, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = 'https://github.com/Mictronics/aircraft-database'
PIN = '479e4d016c596214c8ab853d8fdf3175ce6739d3'          # commit of 2026-11-08T08:58:50+01:00 (weekly export)
LOCAL = os.path.join(HWD, 'refs', 'cache', 'local', 'registry')
CLONE = os.path.join(LOCAL, 'mictronics')
LOOKUP = os.path.join(LOCAL, 'mictronics_lookup.json')
CHECK = os.path.join(HWD, 'refs', 'cache', 'registry', 'mictronics_check.json')
REC = os.path.normpath(os.path.join(HWD, '..', 'sfo3d', 'refs', 'cache', 'rec_pack'))
ARP = (37.65893166, -122.12173888)     # FAA NASR APT_BASE 2026-10-29 (same on-field rule as tools/phase0/hwd_mix.py)
FE = 52                                # field elevation ft (NASR)


def sh(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout.strip()


def fetch():
    os.makedirs(LOCAL, exist_ok=True)
    if not os.path.isdir(os.path.join(CLONE, '.git')):
        env = dict(os.environ, GIT_LFS_SKIP_SMUDGE='1')
        subprocess.run(['git', 'clone', '--depth', '1', '--no-checkout', REPO, CLONE], check=True, env=env)
    head = sh('git', '-C', CLONE, 'rev-parse', 'HEAD')
    if head != PIN:
        subprocess.run(['git', '-C', CLONE, 'fetch', '--depth', '1', 'origin', PIN], check=True)
    subprocess.run(['git', '-C', CLONE, 'checkout', PIN, '--', 'indexedDB_old.zip', 'LICENSE', 'README.md'], check=True)
    print('mictronics at', PIN)


def load_zip():
    z = zipfile.ZipFile(os.path.join(CLONE, 'indexedDB_old.zip'))
    get = lambda n: json.loads(z.read(n).decode('utf-8'))
    return get('aircrafts.json'), get('operators.json'), get('types.json'), get('dbversion.json'), \
        hashlib.sha256(open(os.path.join(CLONE, 'indexedDB_old.zip'), 'rb').read()).hexdigest()


def build():
    ac, ops, types, ver, sha = load_zip()
    doc = {'source': REPO, 'commit': PIN, 'zip_sha256': sha, 'dbversion': ver, 'licence': 'ODC-By 1.0',
           'aircraft': {k.lower(): [v.get('r', ''), v.get('t', ''), v.get('d', ''), v.get('f', '')] for k, v in ac.items()},
           'fields': ['registration', 'icao_type', 'description', 'flags'],
           'operators': ops, 'types': types}
    with open(LOOKUP, 'w') as f:
        json.dump(doc, f, separators=(',', ':'), sort_keys=True)
    print('lookup:', len(doc['aircraft']), 'aircraft,', len(ops), 'operators,', len(types), 'types ->', LOOKUP)


def dist(lat, lon):
    dy = (lat - ARP[0]) * 111195
    dx = (lon - ARP[1]) * 111195 * math.cos(math.radians(ARP[0]))
    return math.hypot(dx, dy)


def onfield():
    """Aircraft within 1.5 km of the ARP and below 150 ft AGL (or alt_baro 'ground'): hwd_mix.py's on-field rule."""
    seen = collections.defaultdict(lambda: {'r': set(), 't': set(), 'cs': set()})
    hours = sorted(glob.glob(os.path.join(REC, 'adsblol_*.jsonl.xz')))
    for f in hours:
        for line in lzma.open(f, 'rt'):
            r = json.loads(line)
            if r.get('code') != 200:
                continue
            for a in r['d'].get('ac', []):
                if 'lat' not in a:
                    continue
                alt = a.get('alt_baro')
                av = FE if alt == 'ground' else alt if isinstance(alt, (int, float)) else None
                if av is None or av > FE + 150 or dist(a['lat'], a['lon']) > 1500:
                    continue
                x = seen[a['hex']]
                if a.get('r'): x['r'].add(a['r'])
                if a.get('t'): x['t'].add(a['t'])
                cs = (a.get('flight') or '').strip()
                if cs: x['cs'].add(cs)
    return seen, [os.path.basename(h) for h in hours]


def check():
    ac, ops, types, ver, sha = load_zip()
    mic = {k.lower(): v for k, v in ac.items()}
    seen, hours = onfield()
    c = collections.Counter()
    for h, x in seen.items():
        if h.startswith('~'):
            c['non_icao_or_anonymous_address'] += 1
            continue
        m = mic.get(h)
        if not m:
            c['icao_address_not_in_db'] += 1
            continue
        c['icao_address_in_db'] += 1
        if x['r']:
            c['reg_agrees' if m['r'] in x['r'] else 'reg_differs'] += 1
        if x['t']:
            c['type_agrees' if m['t'] in x['t'] else 'type_differs'] += 1
        else:
            c['type_only_in_db' if m['t'] else 'type_in_neither'] += 1
        c['has_description' if m.get('d') else 'no_description'] += 1
    opc = collections.Counter()
    for x in seen.values():
        for cs in x['cs']:
            if len(cs) > 3 and cs[:3].isalpha() and cs[3:4].isdigit():
                opc['icao_callsign'] += 1
                opc['operator_named' if cs[:3] in ops else 'operator_unknown'] += 1
    doc = {'what': 'Agreement of the Mictronics aircraft database with what aircraft on the HWD field broadcast '
                   '(adsb.lol recordings); aggregate counts only, no identities (PLAN D1).',
           'mictronics': {'repo': REPO, 'commit': PIN, 'zip_sha256': sha, 'dbversion': ver, 'aircraft_in_db': len(mic),
                          'licence': 'ODC-By 1.0'},
           'recordings': {'dir': 'sfo3d/refs/cache/rec_pack (adsb.lol, ODbL 1.0)', 'hours': len(hours),
                          'first': hours[0], 'last': hours[-1]},
           'on_field_rule': 'within 1500 m of the NASR ARP and below 150 ft AGL or alt_baro ground (tools/phase0/hwd_mix.py)',
           'on_field_aircraft': len(seen), 'counts': dict(sorted(c.items())), 'callsigns': dict(sorted(opc.items())),
           'attribution': 'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL; '
                          'aircraft data: Mictronics aircraft database, Open Data Commons Attribution License 1.0'}
    os.makedirs(os.path.dirname(CHECK), exist_ok=True)
    with open(CHECK, 'w') as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write('\n')
    print(json.dumps(doc['counts']), json.dumps(doc['callsigns']))


if __name__ == '__main__':
    {'fetch': fetch, 'build': build, 'check': check}[sys.argv[1]]()
