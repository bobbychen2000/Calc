"""Count destinations per airline in the 'Airport destination list' of a Wikipedia airport article (wikitext file).
Usage: python3 -I wiki_dest.py <wikitext file>"""
import re, sys, json
t = open(sys.argv[1], encoding='utf-8').read()
i = t.index('{{Airport destination list')
# find matching closing braces
depth, j = 0, i
while True:
    if t.startswith('{{', j): depth += 1; j += 2; continue
    if t.startswith('}}', j):
        depth -= 1; j += 2
        if depth == 0: break
        continue
    j += 1
block = t[i + len('{{Airport destination list'):j - 2]
block = re.sub(r'<ref[^>]*/>', '', block)
block = re.sub(r'<ref[^>]*>.*?</ref>', '', block, flags=re.S)
block = re.sub(r'<!--.*?-->', '', block, flags=re.S)
# strip nested templates except nowrap
block = re.sub(r'\{\{nowrap\|(.*?)\}\}', r'\1', block)
rows = [l.strip()[1:].strip() for l in block.split('\n') if l.strip().startswith('|')]
out = {}
for row in rows:
    m = re.match(r'\[\[([^|\]]*)(?:\|([^\]]*))?\]\]\s*\|(.*)$', row, flags=re.S)
    if not m: print('SKIP', row[:80]); continue
    al = (m.group(2) or m.group(1)).strip(); rest = m.group(3)
    links = re.findall(r'\[\[([^|\]]*)(?:\|([^\]]*))?\]\]', rest)
    dests = [b or a for a, b in links]
    seasonal = 'Seasonal' in rest
    out[al] = {'n': len(dests), 'dests': dests, 'has_seasonal_marker': seasonal}
for al, v in sorted(out.items(), key=lambda x: -x[1]['n']):
    print(f"{v['n']:4d}  {al}")
print('total airline rows', len(out), 'total airline-destination pairs', sum(v['n'] for v in out.values()))
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1) if len(sys.argv) > 2 else None
