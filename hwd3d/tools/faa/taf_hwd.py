"""Extract HWD's based aircraft and airport operations from the FAA Terminal Area Forecast (TAF), 2025 edition.

Why: the FAA Form 5010 Airport Master Record (based aircraft, annual operations) is only served through the ADIP web
app, which needs a page-supplied Authorization header and loads Google reCAPTCHA; we do not script around that
(PLAN.md, web etiquette). The TAF is the FAA's own published dataset of the same quantities per airport and fiscal
year, offered as a plain download.

Source: https://taf.faa.gov/Downloads/APO100_TAF_Final_2025.zip (FAA APO-100, files dated 2026-03-20; taf.faa.gov:
"Fiscal Years 2025 to 2050 ... Publication: March 2026"), glossary https://taf.faa.gov/Downloads/Glossaryfor2025TAF.pdf.
Licence: U.S. Government work (17 U.S.C. 105), public domain.
Columns (glossary): single / jet / multi / helo / other = based GA aircraft by class ("operational and air worthy and
based at an airport for a majority of the year"); itn_ac / itn_at / itn_ga / itn_mil = itinerant air carrier / air
taxi & commuter / general aviation / military operations; loc_ga / loc_mil = local civil / military operations
("remain in the local traffic pattern, execute simulated instrument approaches or low passes ... or practice area
within a 20-mile radius"); tot_overs = overflights. Fiscal year = 1 Oct (previous year) - 30 Sep.
'scenario': not defined in the glossary. In the file, scenario 0 rows run to FY2024 and scenario 1 rows from FY2025 on,
so 0 = historical and 1 = forecast is INFERRED from that pattern, not stated by the FAA.

usage: python3 -I tools/faa/taf_hwd.py <dir with the extracted xlsx files> <zip path>
       -> refs/cache/faa/taf/taf2025_HWD.json
"""
import hashlib, json, os, sys
import openpyxl

LOC = 'HWD'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'refs', 'cache', 'faa', 'taf', 'taf2025_HWD.json')


def rows(path, key_cols):
    ws = openpyxl.load_workbook(path, read_only=True).worksheets[0]
    it = ws.iter_rows(values_only=True)
    hdr = [str(c).strip().lower() for c in next(it)]
    out = []
    for r in it:
        d = dict(zip(hdr, r))
        if str(d.get(key_cols, '')).strip() == LOC:
            out.append({k: (v.strip() if isinstance(v, str) else v) for k, v in d.items()})
    return out


def main(xdir, zpath):
    apt = rows(os.path.join(xdir, 'Airports.xlsx'), 'locid')
    ba = rows(os.path.join(xdir, 'BasedAircraft.xlsx'), 'locid')
    ops = rows(os.path.join(xdir, 'AirportsOperations.xlsx'), 'locid')
    for r in ba:
        r['total_based'] = sum(r[k] for k in ('single', 'jet', 'multi', 'helo', 'other'))
    for r in ops:
        r['total_ops'] = sum(r[k] for k in ('itn_ac', 'itn_at', 'itn_ga', 'itn_mil', 'loc_ga', 'loc_mil'))
        r['local_share'] = round((r['loc_ga'] + r['loc_mil']) / r['total_ops'], 3) if r['total_ops'] else None
    hist = lambda rs: [r for r in rs if r['scenario'] == 0]
    last_ba, last_ops = hist(ba)[-1], hist(ops)[-1]
    sha = hashlib.sha256(open(zpath, 'rb').read()).hexdigest()
    doc = {
        'source': 'FAA Terminal Area Forecast, 2025 edition (APO100_TAF_Final_2025.zip, publication March 2026)',
        'url': 'https://taf.faa.gov/Downloads/APO100_TAF_Final_2025.zip',
        'zip_sha256': sha,
        'licence': 'U.S. Government work (17 U.S.C. 105), public domain',
        'notes': ['Fiscal years (1 Oct - 30 Sep).',
                  'scenario 0 = historical, 1 = forecast: INFERRED from the row pattern (0 ends FY2024, 1 starts FY2025); '
                  'the glossary does not define the field.',
                  'Whether the TAF based-aircraft figures equal the Form 5010 entries is not verified.'],
        'latest_historical': {'based_aircraft': last_ba, 'operations': last_ops},
        'airport': apt,
        'based_aircraft': ba,
        'operations': ops,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(doc, f, indent=1, sort_keys=True)
        f.write('\n')
    print('FY%d based: %s' % (last_ba['ayear'], {k: last_ba[k] for k in ('single', 'jet', 'multi', 'helo', 'other', 'total_based')}))
    print('FY%d ops: %s' % (last_ops['ayear'], {k: last_ops[k] for k in ('itn_ac', 'itn_at', 'itn_ga', 'itn_mil', 'loc_ga', 'loc_mil', 'total_ops', 'local_share', 'tot_overs')}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
