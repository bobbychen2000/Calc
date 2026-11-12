#!/usr/bin/env python3
"""Build a compact N-number lookup from the FAA Releasable Aircraft Database (local only, gitignored: default D1).

New for hwd3d (task G3c, 2026-11-12). The MASTER/ACFTREF join follows sfo3d/tools/models/build_brands.py @ a967f9b
(faa_models(): ACFTREF CODE -> MFR, MODEL; MASTER N-NUMBER + MFR MDL CODE), but here columns are found by header NAME
rather than position, and the script stops if an expected column is missing.

Input : refs/cache/local/registry/ReleasableAircraft.zip   (fetch_registry.py, or saved by hand by the owner)
        refs/cache/local/registry/ardata.pdf               (optional: FAA file layout, used to verify the code labels)
Output: refs/cache/local/registry/registry_lookup.json      (gitignored; holds N-numbers and Mode S hex codes)
  {"made_by", "input": {zip sha256, member dates}, "codes": {...labels + verified flags...},
   "fields": ["mfr","model","year","type_aircraft","type_engine","no_eng","no_seats","registrant_type"],
   "models": [[mfr, model, no_eng, no_seats, type_acft_ref, type_eng_ref], ...],   (ACFTREF rows actually used)
   "n":   {"N12345": [model_index, year, type_aircraft, type_engine, registrant_type], ...},
   "hex": {"a1b2c3": "N12345", ...}}                        (MASTER "MODE S CODE HEX", lower case)
  `load_lookup()` below expands a row into the 8 requested fields. No owner name or address is copied.

Column names expected (FAA ardata.pdf layout, as used by sfo3d build_brands.py; NOT re-read in this session because
registry.faa.gov refused the download on 2026-11-12). The script compares them with the real header row after
normalising (upper case, letters and digits only) and exits if one is absent:
  MASTER.txt : N-NUMBER, MFR MDL CODE, YEAR MFR, TYPE REGISTRANT, TYPE AIRCRAFT, TYPE ENGINE, MODE S CODE HEX
  ACFTREF.txt: CODE, MFR, MODEL, TYPE-ACFT, TYPE-ENG, NO-ENG, NO-SEATS

Code labels (CANDIDATES from memory of FAA ardata.pdf; unverified until the PDF is present). Raw codes are what the
lookup stores; the labels are only used for summaries. When ardata.pdf is present each label is searched in its text
(normalised) and marked "verified": true/false; summaries must show unverified labels as such.

usage: python3 -I hwd3d/tools/registry/build_lookup.py [--zip PATH] [--doc PATH] [--out PATH]
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
REG_DIR = os.path.join(HWD, 'refs', 'cache', 'local', 'registry')
ZIP = os.path.join(REG_DIR, 'ReleasableAircraft.zip')
DOC = os.path.join(REG_DIR, 'ardata.pdf')
OUT = os.path.join(REG_DIR, 'registry_lookup.json')
FIELDS = ['mfr', 'model', 'year', 'type_aircraft', 'type_engine', 'no_eng', 'no_seats', 'registrant_type']

MASTER_COLS = {'n': 'N-NUMBER', 'code': 'MFR MDL CODE', 'year': 'YEAR MFR', 'reg': 'TYPE REGISTRANT',
               'acft': 'TYPE AIRCRAFT', 'eng': 'TYPE ENGINE', 'hex': 'MODE S CODE HEX'}
REF_COLS = {'code': 'CODE', 'mfr': 'MFR', 'model': 'MODEL', 'acft': 'TYPE-ACFT', 'eng': 'TYPE-ENG',
            'no_eng': 'NO-ENG', 'no_seats': 'NO-SEATS'}

# candidate labels (see header): code -> label
CODES = {
    'registrant_type': {'1': 'Individual', '2': 'Partnership', '3': 'Corporation', '4': 'Co-Owned', '5': 'Government',
                        '7': 'LLC', '8': 'Non Citizen Corporation', '9': 'Non Citizen Co-Owned'},
    'type_aircraft': {'1': 'Glider', '2': 'Balloon', '3': 'Blimp/Dirigible', '4': 'Fixed wing single engine',
                      '5': 'Fixed wing multi engine', '6': 'Rotorcraft', '7': 'Weight-shift-control',
                      '8': 'Powered Parachute', '9': 'Gyroplane', 'H': 'Hybrid Lift', 'O': 'Other'},
    'type_engine': {'0': 'None', '1': 'Reciprocating', '2': 'Turbo-prop', '3': 'Turbo-shaft', '4': 'Turbo-jet',
                    '5': 'Turbo-fan', '6': 'Ramjet', '7': '2 Cycle', '8': '4 Cycle', '9': 'Unknown', '10': 'Electric',
                    '11': 'Rotary'},
}


def norm(s):
    return re.sub(r'[^A-Z0-9]', '', s.upper())


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_table(z, member, want):
    """Yield dicts {key: stripped value} for the wanted columns of a registry CSV member (found by header name)."""
    with z.open(member) as fh:
        r = csv.reader(io.TextIOWrapper(fh, encoding='utf-8-sig', errors='replace', newline=''))
        head = [norm(h) for h in next(r)]
        idx = {}
        for k, name in want.items():
            if norm(name) not in head:
                sys.exit('%s: column %r not found; header is %r' % (member, name, head))
            idx[k] = head.index(norm(name))
        for row in r:
            if not row:
                continue
            yield {k: (row[i].strip() if i < len(row) else '') for k, i in idx.items()}


def as_int(s):
    s = (s or '').strip()
    return int(s) if s.isdigit() else None


def verify_codes(doc):
    """Mark each candidate label verified if its normalised text occurs in ardata.pdf (needs pypdf)."""
    out = {g: {c: {'label': l, 'verified': False} for c, l in t.items()} for g, t in CODES.items()}
    note = 'ardata.pdf not present: labels are unverified candidates'
    if os.path.exists(doc):
        try:
            import pypdf
            text = norm(' '.join(p.extract_text() or '' for p in pypdf.PdfReader(doc).pages))
            for g in out.values():
                for c, v in g.items():
                    v['verified'] = norm(v['label']) in text
            note = 'labels searched in the text of ardata.pdf (sha256 %s); verified = found' % sha256(doc)
        except Exception as e:  # pypdf missing or PDF unreadable: keep labels unverified
            note = 'ardata.pdf present but not readable (%r): labels are unverified candidates' % e
    out['_note'] = note
    return out


def build(zip_path, doc_path):
    if not os.path.exists(zip_path):
        sys.exit('missing %s - run fetch_registry.py, or save the zip there by hand (see fetch_registry.py)' % zip_path)
    with zipfile.ZipFile(zip_path) as z:
        members = {i.filename: '%04d-%02d-%02dT%02d:%02d:%02d' % i.date_time for i in z.infolist()}
        ref = {r['code']: r for r in read_table(z, 'ACFTREF.txt', REF_COLS)}
        models, model_ix, n, hexmap = [], {}, {}, {}
        no_ref = 0
        for r in read_table(z, 'MASTER.txt', MASTER_COLS):
            if not r['n']:
                continue
            nn = 'N' + r['n'].upper()
            a = ref.get(r['code'])
            if a is None:
                no_ref += 1
                a = {'mfr': '', 'model': '', 'no_eng': '', 'no_seats': '', 'acft': '', 'eng': ''}
            key = r['code'] if r['code'] in ref else ''
            if key not in model_ix:
                model_ix[key] = len(models)
                models.append([a['mfr'], a['model'], as_int(a['no_eng']), as_int(a['no_seats']), a['acft'], a['eng']])
            # registration-level type codes from MASTER; fall back to the ACFTREF model codes when blank
            n[nn] = [model_ix[key], as_int(r['year']), r['acft'] or a['acft'], r['eng'] or a['eng'], r['reg']]
            hx = r['hex'].strip().lower()
            if re.fullmatch(r'[0-9a-f]{6}', hx):
                hexmap[hx] = nn
    return {
        'made_by': 'hwd3d/tools/registry/build_lookup.py %s' % dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
        'licence': 'derived from the FAA Releasable Aircraft Database (US Government work, public domain); kept local '
                   '(gitignored) because it holds per-aircraft identity (owner default D1)',
        'input': {'zip': os.path.basename(zip_path), 'zip_sha256': sha256(zip_path), 'members': members},
        'counts': {'registrations': len(n), 'models': len(models), 'hex': len(hexmap), 'master_rows_without_acftref': no_ref},
        'codes': verify_codes(doc_path),
        'fields': FIELDS,
        'row': ['model_index', 'year', 'type_aircraft', 'type_engine', 'registrant_type'],
        'model_row': ['mfr', 'model', 'no_eng', 'no_seats', 'type_acft_ref', 'type_eng_ref'],
        'models': models, 'n': n, 'hex': hexmap,
    }


class Lookup:
    """lk = Lookup(path); lk.get('N12345') -> {mfr, model, year, type_aircraft, type_engine, no_eng, no_seats,
    registrant_type} or None; lk.by_hex('a1b2c3') -> N-number or None."""

    def __init__(self, path=OUT):
        self.d = json.load(open(path))

    def get(self, nnum):
        row = self.d['n'].get((nnum or '').strip().upper())
        if row is None:
            return None
        m = self.d['models'][row[0]]
        return {'mfr': m[0], 'model': m[1], 'year': row[1], 'type_aircraft': row[2], 'type_engine': row[3],
                'no_eng': m[2], 'no_seats': m[3], 'registrant_type': row[4]}

    def by_hex(self, hx):
        return self.d['hex'].get((hx or '').strip().lower())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--zip', default=ZIP)
    ap.add_argument('--doc', default=DOC)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    d = build(a.zip, a.doc)
    with open(a.out, 'w') as f:
        json.dump(d, f, separators=(',', ':'))
    print('wrote %s  (%d registrations, %d models, %d hex, %.1f MB)' % (
        a.out, d['counts']['registrations'], d['counts']['models'], d['counts']['hex'], os.path.getsize(a.out) / 1e6))
    print('code labels:', d['codes']['_note'])
    bad = ['%s %s=%s' % (g, c, v['label']) for g, t in d['codes'].items() if g != '_note' for c, v in t.items()
           if not v['verified']]
    if bad:
        print('UNVERIFIED labels (%d): %s' % (len(bad), '; '.join(bad)))


if __name__ == '__main__':
    main()
