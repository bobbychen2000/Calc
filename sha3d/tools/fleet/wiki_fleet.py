"""Extract the current-fleet wikitable (aircraft name, in-service count, orders) from a Wikipedia airline article (wikitext).
Usage: python3 -I wiki_fleet.py <file.wikitext> [...]"""
import re, sys
def clean(s):
    s = re.sub(r'<ref[^>]*/>', '', s); s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'\{\{(?:nowrap|abbr|small)\|([^|}]*)(?:\|[^}]*)?\}\}', r'\1', s)
    s = re.sub(r'\{\{[^{}]*\}\}', '', s)
    s = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', s)
    s = re.sub(r"'''?", '', s); s = re.sub(r'<br\s*/?>', ' ', s); s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()
for f in sys.argv[1:]:
    t = open(f, encoding='utf-8').read()
    m = re.search(r'\n==+\s*(Current fleet|Fleet)\s*==+\n', t)
    print('=====', f.split('/')[-1], '(no fleet section)' if not m else '')
    if not m: continue
    sec = t[m.end():]
    tbl = re.search(r'\{\|.*?\n\|\}', sec, flags=re.S)
    if not tbl: print(clean(sec[:800])); continue
    rows = re.split(r'\n\|-[^\n]*', tbl.group(0))
    for r in rows[1:]:
        cells = [clean(c) for c in re.split(r'\n\||\|\||\n!|!!', '\n' + r.strip()) if clean(c)]
        cells = [re.sub(r'^(?:rowspan|colspan|style|align|class)[^|]*\|\s*', '', c) for c in cells]
        cells = [re.sub(r'^(rowspan|colspan|style)="?[^"|]*"?\s*', '', c) for c in cells]
        if cells: print('  ', ' | '.join(cells[:4])[:140])
