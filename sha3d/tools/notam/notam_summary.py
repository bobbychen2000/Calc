"""Parse the CAAC eAIP monthly "NOTAM Summary" (checklist of NOTAM in force) for one aerodrome and derive the items a
simulator can apply (runway / taxiway / stand closures with their daily schedules, WIP areas, rapid-exit distances).

Input: a series PDF unpacked from the public eAIP summary zip (refs/cache/aip/eaip_notam_summary_<yyyy-mm>/extracted/F.pdf
holds the ZSSS aerodrome NOTAMs; A.pdf the AIRAC triggers). The PDF is untrusted: run with python3 -I. pdftotext
(poppler) does the text extraction.

Output (JSON on stdout or to a file): {"source": ..., "in_force_at": ..., "notams": [...], "sim": [...]}.
- notams: id, kind (NOTAMN/R/C), replaces, location, B/C (UTC, 'PERM', 'EST' flag), D (schedule text), E (text).
- sim: machine-applicable effects [inf: our reading of the NOTAM text], each with the NOTAM id as evidence:
    {"effect": "rwy_closed" | "rwy_no_landing" | "twy_closed" | "stand_closed" | "wip_area" | "rapid_exit_distances",
     "target": ..., "from_utc", "to_utc", "daily_utc": ["1700", "2200"] | null, "except": [...], "notam": id}

The derived file stays local (OD3: the eAIP publishes no licence; publish only short cited facts).

Usage: python3 -I tools/notam/notam_summary.py <series.pdf> <ICAO> [out.json]
"""
import json, re, subprocess, sys

HEAD = re.compile(r'^\s*([A-Z]) ?(\d{4}/\d{2})\s+A\)\s*([A-Z ]+?)\s*$')
KIND = re.compile(r'^\s*(NOTAM[NRC])\s+B\)\s*(\S+)\s+C\)\s*(\S+)')
REPL = re.compile(r'^\s*([A-Z]) ?(\d{4}/\d{2})\s+(?:D\)|E\))')


def pdf_text(path):
    return subprocess.run(['pdftotext', '-layout', path, '-'], check=True, capture_output=True).stdout.decode('utf-8')


def ts(s):
    """'2026/11/10/1700' -> '2026-11-10T17:00Z'; 'PERM' kept; trailing 'EST' flagged by the caller."""
    m = re.fullmatch(r'(\d{4})/(\d{2})/(\d{2})/(\d{2})(\d{2})(EST)?', s)
    if not m:
        return s, False
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}Z', bool(m.group(6))


def parse(text):
    lines = [l for l in text.split('\n') if not re.search(r'Page\s+\d+\s+of\s+\d+', l)]
    in_force = None
    m = re.search(r'still in force on (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', text)
    if m:
        in_force = m.group(1).replace(' ', 'T') + 'Z'
    notams, cur = [], None
    for l in lines:
        h = HEAD.match(l)
        if h:
            cur = {'id': f'{h.group(1)}{h.group(2)}', 'location': h.group(3).split(), 'kind': None, 'replaces': None,
                   'B': None, 'C': None, 'C_est': False, 'D': None, 'E': []}
            notams.append(cur); continue
        if cur is None:
            continue
        k = KIND.match(l)
        if k:
            cur['kind'] = k.group(1); cur['B'] = ts(k.group(2))[0]
            cur['C'], cur['C_est'] = ts(k.group(3)); continue
        r = REPL.match(l)
        if r and cur['kind'] in ('NOTAMR', 'NOTAMC') and cur['replaces'] is None:
            cur['replaces'] = f'{r.group(1)}{r.group(2)}'
        dm = re.search(r'D\)\s*(.+)$', l)
        if dm and not cur['E']:
            cur['D'] = dm.group(1).strip(); continue
        em = re.search(r'E\)\s*(.*)$', l)
        if em:
            cur['E'].append(em.group(1).strip()); continue
        if cur['E'] and l.strip():
            cur['E'].append(l.strip())
    for n in notams:
        n['E'] = ' '.join(n['E']).strip()
    return in_force, notams


def daily(d):
    m = re.fullmatch(r'(\d{4})-(\d{4})\s+DLY', d or '')
    return [m.group(1), m.group(2)] if m else None


def sim_effects(n):
    e, out = n['E'], []
    base = {'from_utc': n['B'], 'to_utc': n['C'], 'to_est': n['C_est'], 'daily_utc': daily(n['D']), 'notam': n['id']}
    m = re.search(r'\bRWY(\d{2}[LRC]?/\d{2}[LRC]?) CLSD', e)
    if m:
        x = dict(base, effect='rwy_closed', target=m.group(1))
        c = re.search(r'CROSS RWY\S+ VIA TWY ([A-Z0-9, ]+)', e)
        if c:
            x['crossing_via'] = [t.strip() for t in c.group(1).replace('.', '').split(',') if t.strip()]
        out.append(x)
    m = re.search(r'\bRWY(\d{2}[LRC]?/\d{2}[LRC]?) NOT AVBL FOR LANDING(?:,EXCEPT ([A-Z ,AND]+))?', e)
    if m:
        out.append(dict(base, effect='rwy_no_landing', target=m.group(1),
                        except_=[t for t in re.split(r'[ ,]+|AND', m.group(2) or '') if t]))
    if re.search(r'FLW TWY CLSD', e):
        out.append(dict(base, effect='twy_closed', target='see text', text=e))
    m = re.search(r'PARKING STAND NR\.?\s*([0-9A-Z,\-]+) CLSD', e)
    if m:
        out.append(dict(base, effect='stand_closed', target=m.group(1)))
    m = re.search(r'WIP WI FLW AREA:\s*(.+)$', e)
    if m:
        out.append(dict(base, effect='wip_area', target=m.group(1)))
    if 'RAPID EXIT TWY' in e and 'DISTANCE TO DTHR' in e:
        rows = re.findall(r'RWY(\d{2}[LRC]?)\s+TWY ([A-Z0-9]+)\s+([\d,]+)M', e)
        out.append(dict(base, effect='rapid_exit_distances',
                        target=[{'rwy': a, 'twy': b, 'dist_from_dthr_m': int(c.replace(',', ''))} for a, b, c in rows]))
    if re.search(r'VISUAL APPROACH OPERATION', e):
        v = re.search(r'VISIBILITY\s*:\s*MORE THAN (\d+)M,\s*CEILING:\s*(\d+)M', e)
        out.append(dict(base, effect='visual_approach', target={'vis_gt_m': int(v.group(1)), 'ceiling_ge_m': int(v.group(2))}
                        if v else 'see text'))
    for x in out:
        if 'except_' in x:
            x['except'] = x.pop('except_')
    return out


def main(pdf, icao, out=None):
    in_force, notams = parse(pdf_text(pdf))
    mine = [n for n in notams if icao in n['location']]
    res = {'source': pdf, 'in_force_at': in_force, 'icao': icao, 'n_notams_in_series': len(notams),
           'notams': mine, 'sim': [x for n in mine for x in sim_effects(n)]}
    s = json.dumps(res, indent=1, ensure_ascii=False)
    if out:
        open(out, 'w', encoding='utf-8').write(s + '\n')
    else:
        print(s)


if __name__ == '__main__':
    main(*sys.argv[1:])
