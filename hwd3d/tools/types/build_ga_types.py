#!/usr/bin/env python3
"""Published dimensions (FAA Aircraft Characteristics Database) of every ICAO type seen on the HWD field -> data/ga_types.json

Forked from sfo3d/tools/models/faa_acd.py @ a967f9b. Kept: the .xlsx read as zipped XML (no third-party parser), sheet 1
(ACD_Data), columns by header name, ft -> m with 0.3048. Changed: each row keeps its Excel row number (cell reference)
so every value names its source row; more columns (MTOW_lb, Rotor_Diameter_ft, Class, engine class, Manufacturer,
FAA_Designator, Remarks, LastUpdate); designators come from the HWD on-field type list, not from js/aircraft/fit.js;
output is a JSON file instead of printed lines; numbers that are binary-float artefacts in the sheet
(e.g. '33.200000000000003') are rounded to 0.001 ft; 'N/A' and blanks stay null.

Inputs
  sfo3d/refs/cache/faa/faa_aircraft_char_database.xlsx  FAA ACD ("Aircraft Characteristics Data, October 2024", modified
        2025-01-03 per docProps/core.xml; sha256 3e68848b...; fetched by sfo3d 2026-11-04 from
        https://www.faa.gov/airports/engineering/aircraft_char_database/aircraft_data ; US Government work, public domain)
  hwd3d/refs/cache/adsb/hwd_mix_summary.txt             line "TYPE MIX (on airfield):" (Phase 0 hwd_mix.py). That line
        is Counter.most_common(60), i.e. TRUNCATED to 60 entries; --recount (default) re-derives the full on-field type
        list from the recordings with hwd3d/tools/registry/registry_mix.py:onfield_aircraft (same definition, 243
        aircraft) and adds the missing designators with in_summary_list = false. Counts are aircraft, not fixes.
Match: ACD ICAO_Code == designator, else FAA_Designator == designator. No fuzzy or model-name matching: a designator
without a row stays null with a note (owner's rule: do not guess). The ACD has no helicopter rows at all (Class values:
Fixed-wing 385, Amphibian 2, Tiltrotor 1 in this edition).
Field definitions (ACD sheet Data_Dictionary, quoted in the output _meta): wingspan tip to tip without / with winglets
(two columns, both kept: which one applies to a given airframe is not decided here), full length, tail height at
operating empty weight, maximum takeoff gross weight (lb).

Output: hwd3d/data/ga_types.json (+ hwd3d/data/SOURCES.json entry, written by hand). Type designators and counts only
(default D1: no per-aircraft identity). Since the Phase 1 review (2026-11-12) _meta carries the ODbL licence URI and the
adsb.lol attribution (the counts are adsb.lol-derived; ODbL 4.2(b)/(c)), and a type without an ACD row has src 'none'
(src_legend) instead of null.
usage: python3 -I hwd3d/tools/types/build_ga_types.py [--no-recount]
"""
import argparse
import ast
import collections as C
import datetime as dt
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = os.path.dirname(HWD)
XLSX = os.path.join(REPO, 'sfo3d', 'refs', 'cache', 'faa', 'faa_aircraft_char_database.xlsx')
SUMMARY = os.path.join(HWD, 'refs', 'cache', 'adsb', 'hwd_mix_summary.txt')
OUT = os.path.join(HWD, 'data', 'ga_types.json')
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
FT = 0.3048           # m per international foot (exact)
LB = 0.45359237       # kg per avoirdupois pound (exact)
KEEP = ['ICAO_Code', 'FAA_Designator', 'Manufacturer', 'Model_FAA', 'Class', 'Physical_Class_Engine', 'Num_Engines',
        'Wingspan_ft_without_winglets_sharklets', 'Wingspan_ft_with_winglets_sharklets', 'Length_ft',
        'Tail_Height_at_OEW_ft', 'MTOW_lb', 'Rotor_Diameter_ft', 'Remarks', 'LastUpdate']
NUMERIC = {'Num_Engines', 'Wingspan_ft_without_winglets_sharklets', 'Wingspan_ft_with_winglets_sharklets', 'Length_ft',
           'Tail_Height_at_OEW_ft', 'MTOW_lb', 'Rotor_Diameter_ft'}
DICT_FIELDS = ['Wingspan_ft_without_winglets_sharklets', 'Wingspan_ft_with_winglets_sharklets', 'Length_ft',
               'Tail_Height_at_OEW_ft', 'MTOW_lb', 'ICAO_Code', 'FAA_Designator']


def col(ref):
    return ''.join(ch for ch in ref if ch.isalpha())


def sheet_rows(z, sheet, ss):
    """[(excel_row_number, {column_letter: value})] of one worksheet."""
    out = []
    for r in ET.fromstring(z.read(sheet)).find('m:sheetData', NS).findall('m:row', NS):
        cells = {}
        for c in r.findall('m:c', NS):
            v = c.find('m:v', NS)
            if v is None:
                t = c.find('m:is/m:t', NS)
                val = t.text if t is not None else None
            else:
                val = ss[int(v.text)] if c.get('t') == 's' else v.text
            cells[col(c.get('r'))] = val
        out.append((int(r.get('r')), cells))
    return out


def read_acd(path):
    z = zipfile.ZipFile(path)
    ss = [''.join(t.text or '' for t in si.iter('{%s}t' % NS['m']))
          for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS)]
    wb = z.read('xl/workbook.xml').decode()
    names = re.findall(r'<sheet name="([^"]+)"', wb)
    assert names[:2] == ['ACD_Data', 'Data_Dictionary'], names    # sheet1.xml / sheet2.xml (workbook.xml.rels)
    assert 'date1904' not in wb                                     # LastUpdate serials use the 1900 date system
    data = sheet_rows(z, 'xl/worksheets/sheet1.xml', ss)
    head = {k: v for k, v in data[0][1].items()}
    rows = [(n, {head.get(k): v for k, v in cells.items()}) for n, cells in data[1:]]
    dd = {}
    for n, cells in sheet_rows(z, 'xl/worksheets/sheet2.xml', ss):
        vals = [cells[k] for k in sorted(cells, key=lambda s: (len(s), s)) if cells[k]]
        if vals and vals[0] in DICT_FIELDS:
            dd[vals[0]] = {'Data_Dictionary_row': n, 'text': ' | '.join(vals[1:])}
    core = z.read('docProps/core.xml').decode()
    meta = {'title': (re.findall(r'<dc:title>([^<]*)', core) or [None])[0],
            'modified': (re.findall(r'<dcterms:modified[^>]*>([^<]*)', core) or [None])[0]}
    return rows, dd, meta


def num(v):
    try:
        return round(float(v), 3)
    except (TypeError, ValueError):
        return None


def listed_types(path):
    line = next(l for l in open(path) if l.startswith('TYPE MIX (on airfield):'))
    return [(t, n) for t, n in ast.literal_eval(line.split(':', 1)[1].strip())]


def recount():
    sys.path.insert(0, os.path.join(HWD, 'tools', 'registry'))
    from registry_mix import onfield_aircraft    # same on-field definition as hwd_mix.py
    onf, files = onfield_aircraft(os.path.join(REPO, 'sfo3d', 'refs', 'cache', 'rec_pack'))
    c = C.Counter('/'.join(sorted(x['t'])) or '(none)' for x in onf.values())
    return c, len(onf), len(files)


def entry(designator, row):
    n, d = row
    acd = {}
    for k in KEEP:
        v = d.get(k)
        v = v.strip() if isinstance(v, str) else v
        acd[k] = (num(v) if num(v) is not None else (v or None)) if k in NUMERIC else (v or None)
    if isinstance(acd['Num_Engines'], float) and acd['Num_Engines'].is_integer():
        acd['Num_Engines'] = int(acd['Num_Engines'])
    if acd['LastUpdate'] and acd['LastUpdate'].isdigit():   # Excel serial date, 1900 system (no date1904 in workbookPr)
        day = dt.date(1899, 12, 30) + dt.timedelta(days=int(acd['LastUpdate']))
        acd['LastUpdate'] = '%s (Excel serial %s)' % (day.isoformat(), acd['LastUpdate'])
    m = lambda k: round(acd[k] * FT, 3) if isinstance(acd[k], float) else None
    return {
        'wingspan_m': m('Wingspan_ft_without_winglets_sharklets'),
        'wingspan_winglets_m': m('Wingspan_ft_with_winglets_sharklets'),
        'length_m': m('Length_ft'),
        'tail_height_m': m('Tail_Height_at_OEW_ft'),
        'mtow_kg': round(acd['MTOW_lb'] * LB, 1) if isinstance(acd['MTOW_lb'], float) else None,
        'src': 'obs',
        'source': 'FAA ACD sheet ACD_Data row %d (%s = %s)' % (
            n, 'ICAO_Code' if acd['ICAO_Code'] == designator else 'FAA_Designator', designator),
        'acd_row': n,
        'acd': acd,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--no-recount', action='store_true', help='only the (truncated) summary list')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    rows, dd, meta = read_acd(XLSX)
    classes = C.Counter(d.get('Class') for _, d in rows)
    listed = listed_types(SUMMARY)
    want = C.OrderedDict((t, {'onfield_aircraft': n, 'in_summary_list': True}) for t, n in listed if t != '(none)')
    rc_note = 'not run (--no-recount)'
    if not a.no_recount:
        c, n_on, n_files = recount()
        mism = {t: (want[t]['onfield_aircraft'], c.get(t, 0)) for t in want if c.get(t, 0) != want[t]['onfield_aircraft']}
        for t, n in c.most_common():
            if t == '(none)':
                continue
            for part in t.split('/'):          # an aircraft that reported 2 designators counts for both
                if part not in want:
                    want[part] = {'onfield_aircraft': n, 'in_summary_list': False}
                    if '/' in t:
                        want[part]['note_count'] = 'aircraft reported several designators: %s' % t
        rc_note = ('recount over %d recording files: %d on-field aircraft (Phase 0: 243), %d distinct type strings, '
                   '%d without type; counts of listed types that differ from the summary: %s'
                   % (n_files, n_on, len([t for t in c if t != '(none)']), c.get('(none)', 0), mism or 'none'))
        print(rc_note)
    by_icao = {(d.get('ICAO_Code') or '').strip(): (n, d) for n, d in rows if d.get('ICAO_Code')}
    by_faa = {(d.get('FAA_Designator') or '').strip(): (n, d) for n, d in rows if d.get('FAA_Designator')}
    types = {}
    for t, info in want.items():
        row = by_icao.get(t) or by_faa.get(t)
        if row:
            types[t] = {**info, **entry(t, row)}
        else:
            types[t] = {**info, 'wingspan_m': None, 'wingspan_winglets_m': None, 'length_m': None, 'tail_height_m': None,
                        'mtow_kg': None, 'src': 'none', 'acd_row': None,
                        'note': 'no FAA ACD row with ICAO_Code or FAA_Designator %r: dimensions left null, not guessed '
                                '(context: this ACD edition has no helicopter rows at all)' % t}
    sha = hashlib.sha256(open(XLSX, 'rb').read()).hexdigest()
    out = {'_meta': {
        'made_by': 'hwd3d/tools/types/build_ga_types.py (task G3d, 2026-11-12)',
        'source': {'file': os.path.relpath(XLSX, REPO), 'sha256': sha, 'title': meta['title'], 'modified': meta['modified'],
                   'url': 'https://www.faa.gov/airports/engineering/aircraft_char_database/aircraft_data',
                   'fetched': '2026-11-04 (by sfo3d)', 'licence': 'US Government work (FAA, 17 U.S.C. 105), public domain',
                   'rows': len(rows), 'class_counts': dict(classes)},
        'field_definitions': dd,
        'units': 'ft and lb as published in the ACD (in "acd"); m = ft x 0.3048, kg = lb x 0.45359237 (exact factors), '
                 'rounded to 1 mm and 0.1 kg',
        'type_list': '%s line "TYPE MIX (on airfield)" (truncated to 60 entries) + recount: %s'
                     % (os.path.relpath(SUMMARY, REPO), rc_note),
        'matched': sum(1 for v in types.values() if v['acd_row']), 'missing': sorted(t for t, v in types.items()
                                                                                    if not v['acd_row']),
        'privacy': 'type designators and aircraft counts only (default D1)',
        'src_legend': {'obs': 'dimensions read from the FAA ACD row named in "source"',
                       'none': 'no FAA ACD row for this designator: dimensions are null, not guessed (see "note")'},
        'licence': 'Mixed: the dimensions (FAA ACD) are a U.S. Government work in the public domain; the on-field counts '
                   '(onfield_aircraft, note_count) are derived from adsb.lol data, made available under the Open Database '
                   'License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/), so this file is offered under the ODbL 1.0',
        'attribution': ['Contains information from ADSB.lol (https://adsb.lol), made available under the ODbL 1.0 '
                        '(https://opendatacommons.org/licenses/odbl/1-0/)',
                        'FAA Aircraft Characteristics Database (October 2024), U.S. Government work']},
        'types': types}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)
    print('wrote %s: %d types, %d with an ACD row, missing: %s' % (a.out, len(types), out['_meta']['matched'],
                                                                   ' '.join(out['_meta']['missing'])))


if __name__ == '__main__':
    main()
