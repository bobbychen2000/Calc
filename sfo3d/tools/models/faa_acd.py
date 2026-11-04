#!/usr/bin/env python3
"""Read the FAA Aircraft Characteristics Database (ACD) spreadsheet and print the published dimensions of ICAO designators.

Source: FAA Office of Airports, Aircraft Characteristics Database, https://www.faa.gov/airports/engineering/aircraft_char_database
(download link .../aircraft_char_database/aircraft_data, an .xlsx; US Government work, public domain), cached at
refs/cache/faa/faa_aircraft_char_database.xlsx (fetched 4 Nov 2026). Columns used: ICAO_Code, Model_FAA,
Wingspan_ft_without_winglets_sharklets, Wingspan_ft_with_winglets_sharklets, Length_ft, Tail_Height_at_OEW_ft, Num_Engines,
LastUpdate. js/aircraft/fit.js BIZ (generic business-jet airframe) takes its length / span / height from this table.

No third-party parser is needed (the .xlsx is read as zipped XML).
Usage: python3 tools/models/faa_acd.py [ICAO ...]   (default: the business-jet designators of js/aircraft/fit.js)
"""
import json, os, sys, zipfile, xml.etree.ElementTree as ET

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
XLSX = os.path.join(ROOT, 'refs', 'cache', 'faa', 'faa_aircraft_char_database.xlsx')
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
FT = 0.3048
DEFAULT = ['GLF4', 'GLF5', 'GLF6', 'G280', 'GA5C', 'GA6C', 'GLEX', 'GL5T', 'GL7T', 'CL30', 'CL35', 'CL60', 'C56X', 'C68A', 'C700', 'C750',
           'C25A', 'C25B', 'C25C', 'C560', 'E55P', 'E545', 'E550', 'E135', 'E35L', 'E145', 'LJ45', 'LJ60', 'LJ75', 'FA7X', 'FA8X', 'F900',
           'F2TH', 'FA50', 'H25B', 'PC24', 'BE40', 'GALX', 'B752', 'B753', 'B763']


def col(ref): return ''.join(ch for ch in ref if ch.isalpha())


def read(path=XLSX):
    z = zipfile.ZipFile(path)
    ss = [''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS)]
    rows = ET.fromstring(z.read('xl/worksheets/sheet1.xml')).find('m:sheetData', NS).findall('m:row', NS)
    def val(c):
        v = c.find('m:v', NS)
        if v is None:
            t = c.find('m:is/m:t', NS); return t.text if t is not None else None
        return ss[int(v.text)] if c.get('t') == 's' else v.text
    head = {col(c.get('r')): val(c) for c in rows[0].findall('m:c', NS)}
    out = []
    for r in rows[1:]:
        d = {head.get(col(c.get('r'))): val(c) for c in r.findall('m:c', NS)}
        out.append(d)
    return out


def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def main():
    want = sys.argv[1:] or DEFAULT
    rows = read(); res = {}
    for d in rows:
        k = (d.get('ICAO_Code') or '').strip()
        if k not in want: continue
        sp0, sp1 = num(d.get('Wingspan_ft_without_winglets_sharklets')), num(d.get('Wingspan_ft_with_winglets_sharklets'))
        L, H = num(d.get('Length_ft')), num(d.get('Tail_Height_at_OEW_ft'))
        res.setdefault(k, []).append(dict(model=d.get('Model_FAA'), span=round(sp0 * FT, 2) if sp0 else None, spanWL=round(sp1 * FT, 2) if sp1 else None,
                                          L=round(L * FT, 2) if L else None, H=round(H * FT, 2) if H else None, eng=d.get('Num_Engines'), upd=d.get('LastUpdate')))
    for k in want: print(k, json.dumps(res.get(k)))
    return res


if __name__ == '__main__':
    main()
