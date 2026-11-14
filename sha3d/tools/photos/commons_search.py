"""B3 (sha3d): Commons full-text file search with imageinfo. usage: python3 -I sha3d/tools/photos/commons_search.py OUT.json "query" ..."""
import json, sys, time, urllib.request, urllib.parse, os, re
UA = "sha3d-airport-research/0.1 (non-commercial research; python-requests compatible)"
API = "https://commons.wikimedia.org/w/api.php"
out = sys.argv[1]; qs = sys.argv[2:]
res = {}
for q in qs:
    params = dict(action='query', generator='search', gsrsearch=q, gsrnamespace='6', gsrlimit='50', prop='imageinfo',
                  iiprop='url|size|extmetadata', iiurlwidth='640', format='json', maxlag='5')
    url = API + '?' + urllib.parse.urlencode(params)
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                d = json.loads(r.read().decode('utf-8')); break
        except Exception as e:
            print('retry', q, e, file=sys.stderr); time.sleep(15 * (i + 1))
    res[q] = d; time.sleep(3)
    pages = (d.get('query') or {}).get('pages') or {}
    print('==', q, len(pages))
    for p in sorted(pages.values(), key=lambda p: p.get('index', 0)):
        ii = (p.get('imageinfo') or [{}])[0]; em = ii.get('extmetadata') or {}
        g = lambda k: re.sub(r'<[^>]+>', '', (em.get(k) or {}).get('value', '')).strip()
        print('  ', p['title'][5:][:90], '|', g('LicenseShortName'), '|', g('Artist')[:25], '|', g('DateTimeOriginal')[:10], '|', g('ImageDescription')[:80].replace('\n', ' '))
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
