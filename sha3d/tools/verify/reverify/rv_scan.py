"""Scan committable text files for per-flight identifiers from the local B1 tables.
Usage: python3 -I rv_scan.py <sha3d> [root ...]   (default roots: docs data). Prints file:line hits with context."""
import json, os, re, sys, collections, zlib
S = sys.argv[1]
L = os.path.join(S, 'refs/cache/observed_elsewhere')
IATA = {'CES': 'MU', 'CSH': 'FM', 'CQH': '9C', 'DKH': 'HO', 'CSN': 'CZ', 'CCA': 'CA', 'CXA': 'MF', 'CSZ': 'ZH',
        'CHH': 'HU', 'CDG': 'SC', 'CPA': 'CX', 'TBA': 'TV', 'AMU': 'NX', 'CUA': 'KN', 'JAL': 'JL', 'ANA': 'NH',
        'KAL': 'KE', 'AAR': 'OZ', 'CAL': 'CI', 'EVA': 'BR', 'CRK': 'HX', 'UEA': 'EU', 'HBH': 'NS', 'GCR': 'GS',
        'YZR': 'Y8', 'LKE': '8L', 'CBJ': 'JD'}
ids = collections.defaultdict(set)
for day in ('2026-11-10', '2026-11-12'):
    for x in json.load(open(f'{L}/sha_observed_{day}.json'))['movements']:
        cs = (x['cs'] or '').strip()
        if cs:
            ids['callsign'].add(cs)
            al, num = cs[:3], cs[3:]
            if al in IATA and num:
                ids['iata_fn'].add(IATA[al] + num)
        if x['r']: ids['registration'].add(x['r'])
        if x['icao']: ids['hex'].add(x['icao'].lower())
for k, v in ids.items():
    print(k, len(v))
pat = {k: re.compile(r'(?<![A-Za-z0-9])(' + '|'.join(sorted(map(re.escape, v), key=len, reverse=True)) + r')(?![A-Za-z0-9])',
                     re.I if k == 'hex' else 0) for k, v in ids.items()}
gen = {'callsign_like': re.compile(r'(?<![A-Za-z0-9])(CES|CSH|CQH|DKH|CSN|CCA|CXA|CSZ|CHH|CDG|CPA|TBA|AMU|CUA|JAL|ANA|KAL|AAR|CAL|EVA|CRK|UEA|HBH|GCR|YZR)\d{1,4}[A-Z]?(?![A-Za-z0-9])'),
       'iata_fn_like': re.compile(r'(?<![A-Za-z0-9])(MU|FM|9C|HO|CZ|CA|MF|ZH|HU|SC|CX|TV|NX|KN|JL|NH|KE|OZ|CI|BR|HX|EU|NS|GS)\s?\d{2,4}(?![A-Za-z0-9])'),
       'B_reg': re.compile(r'(?<![A-Za-z0-9])B-?[0-9][0-9A-Z]{3}(?![A-Za-z0-9])'),
       'JA_HL_reg': re.compile(r'(?<![A-Za-z0-9])(JA\d{3}[A-Z0-9]{1,2}|HL\d{4})(?![A-Za-z0-9])')}
hits = collections.Counter()
for root in (sys.argv[2:] or ['docs', 'data']):
    for dp, dn, fn in os.walk(os.path.join(S, root)):
        for f in fn:
            p = os.path.join(dp, f)
            if not f.endswith(('.md', '.json', '.js', '.csv', '.txt', '.svg', '.html', '.py')):
                continue
            txt = open(p, encoding='utf-8', errors='replace').read()
            for i, line in enumerate(txt.splitlines(), 1):
                for k, r in pat.items():
                    for m in r.finditer(line):
                        hits[(os.path.relpath(p, S), k)] += 1
                        if hits[(os.path.relpath(p, S), k)] <= 3:
                            print(f'EXACT {k}: {os.path.relpath(p, S)}:{i}: ...{line[max(0, m.start()-50):m.end()+30]}...')
                for k, r in gen.items():
                    for m in r.finditer(line):
                        hits[(os.path.relpath(p, S), k)] += 1
                        if hits[(os.path.relpath(p, S), k)] <= 3:
                            print(f'GEN {k}: {os.path.relpath(p, S)}:{i}: ...{line[max(0, m.start()-50):m.end()+30]}...')
print('--- hit counts'); [print(' ', k, v) for k, v in sorted(hits.items())]
