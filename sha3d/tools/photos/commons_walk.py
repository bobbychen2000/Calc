# B3 (sha3d): Commons category walk. usage: python3 -I sha3d/tools/photos/commons_walk.py OUT_DIR 2 "Category:Shanghai Hongqiao International Airport"
"""Walk Commons categories (depth-limited), collect File: titles, then fetch imageinfo+extmetadata in batches.
usage: python3 -I commons_walk.py OUTDIR depth Category:A [Category:B ...]"""
import json, sys, time, urllib.request, urllib.parse, os
UA = "sha3d-airport-research/0.1 (non-commercial research; python-requests compatible)"
API = "https://commons.wikimedia.org/w/api.php"
out = sys.argv[1]; depth = int(sys.argv[2]); roots = sys.argv[3:]
os.makedirs(out, exist_ok=True)
def get(params):
    params = dict(params, format='json', maxlag='5')
    url = API + '?' + urllib.parse.urlencode(params)
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                t = r.read().decode('utf-8')
            time.sleep(2.0)
            return json.loads(t)
        except Exception as e:
            print('retry', i, e, file=sys.stderr); time.sleep(10 * (i + 1))
    raise SystemExit('failed ' + url)
seen_cats = set(); files = {}  # title -> set(categories)
queue = [(c, 0) for c in roots]
while queue:
    cat, d = queue.pop(0)
    if cat in seen_cats: continue
    seen_cats.add(cat)
    cont = {}
    while True:
        r = get(dict(action='query', list='categorymembers', cmtitle=cat, cmlimit='500', **cont))
        for m in r['query']['categorymembers']:
            if m['ns'] == 14 and d < depth: queue.append((m['title'], d + 1))
            elif m['ns'] == 6: files.setdefault(m['title'], set()).add(cat)
        if 'continue' in r: cont = {'cmcontinue': r['continue']['cmcontinue'], 'continue': r['continue']['continue']}
        else: break
    print('cat', d, cat, len(files), file=sys.stderr)
titles = sorted(files)
info = {}
for i in range(0, len(titles), 50):
    b = titles[i:i + 50]
    r = get(dict(action='query', titles='|'.join(b), prop='imageinfo', iiprop='url|size|mime|extmetadata|timestamp', iiurlwidth='640'))
    for p in r['query']['pages'].values():
        info[p['title']] = p
json.dump({'roots': roots, 'depth': depth, 'categories': sorted(seen_cats),
           'files': {t: {'cats': sorted(files[t]), 'page': info.get(t)} for t in titles}},
          open(os.path.join(out, 'walk.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('files', len(titles), 'cats', len(seen_cats), file=sys.stderr)
