import hashlib, json, os, subprocess, sys
C = '/home/user/Calc/sha3d/refs/cache'
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def files(d, skip=()):
    out = {}
    for n in sorted(os.listdir(d)):
        p = os.path.join(d, n)
        if os.path.isfile(p) and n != 'SOURCES.json' and n not in skip:
            out[n] = {'bytes': os.path.getsize(p), 'sha256': sha(p)}
    return out
def head(d): return subprocess.run(['git', '-C', d, 'log', '-1', '--format=%H %cI'], capture_output=True, text=True).stdout.strip()
W = lambda d, doc: (json.dump(doc, open(os.path.join(C, d, 'SOURCES.json'), 'w'), indent=1, ensure_ascii=False), print('wrote', d))
D = '2026-11-14'
W('routes_vrs', {
 'what': 'Virtual Radar Server standing data (callsign -> route, airports, airlines): shallow clone, blobless full-history clone (for git blame ages), and our derived index',
 'url': 'https://github.com/vradarserver/standing-data', 'retrieved': D, 'method': 'git clone --depth 1 (standing-data/), git clone --filter=blob:none (sd_hist/)',
 'commit': head(os.path.join(C, 'routes_vrs/standing-data')),
 'licence': 'CC0 1.0 Universal', 'licence_quote': 'LICENSE: "Creative Commons Legal Code / CC0 1.0 Universal"',
 'provenance_quote': 'README: "This repository holds CSV files built from the aviation data submitted by Virtual Radar Server users to the SDM site." (crowd-sourced; routes/schema-01/CREDITS.md lists the submitting users)',
 'redistributable': True,
 'derived': {'vrs_index.json.gz': 'tools/routes/vrs_routes.py build (callsign -> [airline, airports]; airports; airlines; airport_loc)',
             'blame_age.json': 'git blame --line-porcelain of routes/schema-01/<airline>-all.csv for 10 Chinese airlines (CHH blame failed); days since each SHA/PVG/other route line last changed (repo history starts 2022-08-26)'},
 'files': files(os.path.join(C, 'routes_vrs'))})
W('registry_mictronics', {
 'what': 'Mictronics aircraft database export (ICAO 24-bit address -> registration, ICAO type, description; operators; types): shallow git clone',
 'url': 'https://github.com/Mictronics/aircraft-database', 'retrieved': D, 'commit': head(os.path.join(C, 'registry_mictronics/mictronics')),
 'note': 'same pinned commit as hwd3d/tools/registry/mictronics_db.py (479e4d0, weekly export of 2026-11-08); file used: indexedDB_old.zip (dbversion 530)',
 'licence': 'Open Data Commons Attribution License 1.0 (ODC-By)', 'licence_quote': 'README: "Aircraft database exports are made available under the Open Data Commons Attribution License"',
 'attribution': 'Aircraft data: Mictronics aircraft database (https://www.mictronics.de/aircraft-database/), Open Data Commons Attribution License 1.0',
 'redistributable': 'yes, with attribution (ODC-By)'})
W('routes_wiki', {
 'what': 'English Wikipedia wikitext of the SHA and PVG airport articles; parsed "Airport destination list" (tools/fleet/wiki_dest.py) for the airline-destination pair check of the route DB',
 'urls': ['https://en.wikipedia.org/w/index.php?title=Shanghai_Hongqiao_International_Airport&action=raw',
          'https://en.wikipedia.org/w/index.php?title=Shanghai_Pudong_International_Airport&action=raw'],
 'retrieved': D, 'revisions': {'Shanghai_Hongqiao_International_Airport': '1385154959 (identical bytes to the fleet key copy of 2026-11-13; revinfo request got HTTP 429)',
                               'Shanghai_Pudong_International_Airport': '1385155113 (2026-11-12T04:14:39Z)'},
 'licence': 'CC BY-SA 4.0', 'licence_quote': "Wikipedia: 'Text is available under the Creative Commons Attribution-ShareAlike 4.0 License; additional terms may apply'",
 'redistributable': 'yes, CC BY-SA 4.0 with attribution; ShareAlike for adaptations', 'status': 'secondary', 'files': files(os.path.join(C, 'routes_wiki'))})
W('readsb_src', {
 'what': 'wiedehopf/readsb source (shallow clone), read only for the trace file format (README-json.md "trace jsons") and the leg-marker logic (globe_index.c)',
 'url': 'https://github.com/wiedehopf/readsb', 'retrieved': D, 'commit': head(os.path.join(C, 'readsb_src/readsb')),
 'licence': 'GPL-3.0-or-later', 'licence_quote': 'LICENSE: "This version of readsb is licensed under the GPL, v3 or any later version."',
 'redistributable': 'yes under GPL-3.0 (not needed: reference only, nothing copied into sha3d)'})
W('observed_elsewhere', {
 'what': 'LOCAL ONLY. scan/: per-day flight summaries in East/South-East Asia (lat 0-60 N, lon 60-180 E) from adsb.lol globe_history, with thinned tracks of SHA/PVG-route and fully observed flights (tools/adsb/scan_callsigns.py); sha_observed_<day>.json/.csv: per-flight SHA movements identified elsewhere with inferred SHA-side times (tools/adsb/observed_elsewhere.py)',
 'source': 'adsb.lol globe_history daily archive, GitHub releases of adsblol/globe_history_2026',
 'release_tags': ['v2026.11.09-planes-readsb-prod-0', 'v2026.11.10-planes-readsb-prod-0', 'v2026.11.11-planes-readsb-prod-0', 'v2026.11.12-planes-readsb-prod-0'],
 'url': 'https://github.com/adsblol/globe_history_2026/releases', 'retrieved': D,
 'licence': 'ODbL 1.0', 'licence_quote': 'license: ODbL 1.0 , use it freely, just keep it open. (https://www.adsb.lol/docs/open-data/historical/)',
 'other_inputs': 'VRS standing data (CC0 1.0, routes_vrs/), Mictronics aircraft database (ODC-By 1.0, registry_mictronics/)',
 'attribution': 'Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL; routes: Virtual Radar Server standing data (CC0); aircraft data: Mictronics aircraft database (ODC-By 1.0)',
 'redistributable': 'legally yes (ODbL derived database, share-alike), but WITHHELD: per-flight data observed elsewhere stays local until the owner sees a sample (PLAN 6b, Q3 working default); military/PIA/LADD aircraft (readsb dbFlags 1/4/8) were dropped at scan time',
 'files': {**files(os.path.join(C, 'observed_elsewhere')), **{'scan/' + k: v for k, v in files(os.path.join(C, 'observed_elsewhere', 'scan')).items()}}})
