"""List Wikimedia Commons API search results: title, licence, artist, date, size. Usage: python3 -I commons_list.py f.json [...]"""
import json, sys, re
for f in sys.argv[1:]:
    d = json.load(open(f, encoding='utf-8'))
    if 'error' in d: print(f, 'ERROR', d['error'].get('info')); continue
    pages = (d.get('query') or {}).get('pages') or {}
    print('==', f, len(pages))
    for p in sorted(pages.values(), key=lambda p: p.get('index', 0)):
        ii = (p.get('imageinfo') or [{}])[0]; em = ii.get('extmetadata') or {}
        g = lambda k: re.sub(r'<[^>]+>', '', (em.get(k) or {}).get('value', ''))[:40]
        print(f"  {p['title'][5:][:95]} | {g('LicenseShortName')} | {g('Artist')} | {g('DateTimeOriginal')[:10]} | {ii.get('width')}x{ii.get('height')}")
