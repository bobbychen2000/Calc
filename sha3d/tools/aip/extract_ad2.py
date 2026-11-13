"""Extract text, tables, the stand list and the obstacle list from a cached AIP China AD 2 ZSSS PDF.

Usage (run with python3 -I; the PDF is untrusted data and stays in refs/cache):
    python3 -I tools/aip/extract_ad2.py "<path to AD 2 pdf>" <out_dir>

Writes into out_dir: ad2_layout.txt (pdftotext -layout), ad2_right_column.txt (English column of the
two-column AD 2.20-2.23 pages), ad2_tables.txt, stands.json (AD 2.20 3.2.6 stand limits table +
AD 2.20 3.2.2.3 VDGS table) and obstacles.json (AD 2.10). Nothing from the PDF is hard-coded here.
"""
import json, os, re, subprocess, sys
import pdfplumber

def expand(spec):
    out = []
    for tok in [t.strip() for t in spec.replace('，', ',').split(',') if t.strip()]:
        m = re.fullmatch(r'(\d+)-(\d+)', tok)
        out += [str(i) for i in range(int(m.group(1)), int(m.group(2)) + 1)] if m else [tok]
    return out

def stand_key(s):
    m = re.match(r'(\d+)(.*)', s)
    return (int(m.group(1)), m.group(2)) if m else (10**6, s)

def main(pdf_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    layout = os.path.join(out_dir, 'ad2_layout.txt')
    subprocess.run(['pdftotext', '-layout', pdf_path, layout], check=True)
    lines = open(layout, encoding='utf-8').read().split('\n')
    stands, vdgs, rows = {}, [], []
    with pdfplumber.open(pdf_path) as pdf, \
         open(os.path.join(out_dir, 'ad2_right_column.txt'), 'w', encoding='utf-8') as rc, \
         open(os.path.join(out_dir, 'ad2_tables.txt'), 'w', encoding='utf-8') as tf:
        pending = None
        for pn, page in enumerate(pdf.pages, start=1):
            w, h = page.width, page.height
            rc.write(f'\n===== page {pn} =====\n{page.crop((w * 0.49, 0, w, h)).extract_text() or ""}\n')
            for ti, table in enumerate(page.extract_tables()):
                tf.write(f'--- page {pn} table {ti}\n')
                for row in table:
                    cells = [(c or '').replace('\n', ' ').strip() for c in row]
                    tf.write(' | '.join(cells) + '\n')
                    rows.append((pn, cells))
    # stand limits table (AD 2.20 3.2.6): rows "<stands> | <wing span limit> | <fuselage> | Taxi in, Push back";
    # a stand list may wrap into the next row with empty limit cells (page breaks), so carry it forward.
    in_limits = False
    carry = None
    for pn, cells in rows:
        head = ' '.join(cells)
        if 'Wing span limits' in head and 'Enter or Exit' in head:
            in_limits = True; continue
        if in_limits and ('Combined stands group' in head or 'TP01' in head):
            in_limits = False
        if in_limits and len(cells) >= 2:
            ids, limit = cells[0], cells[1]
            if not limit and carry:
                for s in expand(ids): stands[s] = carry
                continue
            if limit:
                carry = limit
                for s in expand(ids.rstrip(',')): stands[s] = limit
        if ('docking guidance' in head.lower()) and len(cells) == 2 and re.match(r'^\d', cells[0]):
            vdgs += expand(cells[0])
    obstacles = []
    s = next(i for i, l in enumerate(lines) if 'AD 2.10' in l)
    e = next(i for i, l in enumerate(lines) if 'AD 2.11' in l and i > s)
    band = 'within 15 km'
    for i in range(s, e):
        if '15 to 50km' in lines[i]: band = '15-50 km'
        m = re.search(r'\s([A-Za-z_]+)\s+(\d{3})\s*/\s*([\d,]+)\s+([\d.]+)', lines[i])
        if m:
            obstacles.append({'type': m.group(1), 'mag_brg_deg': int(m.group(2)),
                              'dist_m': int(m.group(3).replace(',', '')), 'elev_m': float(m.group(4)),
                              'band': band, 'ref': 'centre of RWY18L/36R', 'layout_line': i + 1})
    st = sorted(stands, key=stand_key)
    json.dump({'source_pdf': os.path.basename(pdf_path), 'count': len(st), 'stands': st,
               'wingspan_limit_m': {k: stands[k] for k in st},
               'vdgs_stands': sorted(set(vdgs), key=stand_key)},
              open(os.path.join(out_dir, 'stands.json'), 'w'), indent=1, ensure_ascii=False)
    json.dump(obstacles, open(os.path.join(out_dir, 'obstacles.json'), 'w'), indent=1)
    print(f'stands: {len(st)}; VDGS stands: {len(set(vdgs))}; obstacle rows: {len(obstacles)}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
