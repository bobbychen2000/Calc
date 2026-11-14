"""B3: fetch selected Wikimedia Commons photos (1280 px renditions) with per-file licence metadata from the API.

usage: python3 -I sha3d/tools/photos/commons_fetch.py OUT_DIR walk.json search.json "File:A.jpg" ["File:B.jpg" ...]
The licence, author and URLs come from the imageinfo/extmetadata that the API returned for each file (walk.json /
search.json, saved beside the photos). Writes OUT_DIR/<n>_<slug>.jpg and OUT_DIR/SOURCES.json.
"""
import json, sys, os, re, time, hashlib, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commons_meta import clean_author, clean_date   # noqa: E402  (Fix round 1)
UA = "sha3d-airport-research/0.1 (non-commercial research; python-requests compatible)"
out, walk, search = sys.argv[1], sys.argv[2], sys.argv[3]; titles = sys.argv[4:]
os.makedirs(out, exist_ok=True)
pages = {}
for t, v in json.load(open(walk, encoding='utf-8'))['files'].items(): pages[t] = (v['page'], v['cats'])
for q, d in json.load(open(search, encoding='utf-8')).items():
    for p in ((d.get('query') or {}).get('pages') or {}).values(): pages.setdefault(p['title'], (p, []))
REUSE = {'CC BY 4.0', 'CC BY-SA 4.0', 'CC BY-SA 3.0', 'CC BY 3.0', 'CC BY-SA 2.0', 'CC BY 2.0', 'CC0', 'Public domain'}
recs = []
for n, t in enumerate(titles, 1):
    p, cats = pages[t]; ii = p['imageinfo'][0]; em = ii.get('extmetadata') or {}
    g = lambda k: re.sub(r'<[^>]+>', '', (em.get(k) or {}).get('value', '')).strip()
    lic = g('LicenseShortName')
    thumb = ii.get('thumburl', '')
    url = re.sub(r'/\d+px-', '/1280px-', thumb) if ii.get('width', 0) > 1280 else ii['url']
    slug = re.sub(r'[^A-Za-z0-9]+', '_', t[5:].rsplit('.', 1)[0])[:60].strip('_')
    ext = '.png' if url.lower().endswith('.png') else '.jpg'
    fn = f'{n:02d}_{slug}{ext}'
    path = os.path.join(out, fn)
    if not os.path.exists(path):
        for i in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=120) as r:
                    data = r.read()
                break
            except Exception as e:
                print('retry', t, e, file=sys.stderr); time.sleep(15 * (i + 1))
        open(path, 'wb').write(data); time.sleep(2.5)
    reuse = lic in REUSE
    recs.append(dict(file=fn, title=t, page_url='https://commons.wikimedia.org/wiki/' + urllib.parse.quote(t.replace(' ', '_')),
                     original_url=ii['url'], fetched_url=url, original_size=[ii.get('width'), ii.get('height')],
                     author=clean_author(g('Artist')), artist_raw=g('Artist')[:300], credit=g('Credit')[:200], licence=lic, licence_url=g('LicenseUrl'),
                     attribution_required=g('AttributionRequired'), usage_terms=g('UsageTerms'),
                     date=clean_date(g('DateTimeOriginal'), t) or g('DateTimeOriginal')[:19], date_raw=g('DateTimeOriginal')[:60], description=g('ImageDescription')[:300], commons_categories=cats,
                     bytes=os.path.getsize(path), sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
                     reuse_in_repo='yes' if reuse else 'no',
                     reuse_note=('free licence; attribute author + licence (+ share-alike for BY-SA)' if reuse else
                                 'GFDL 1.2 or other: reference only, local (not CC BY-SA compatible for the contact sheet)')))
    print(fn, lic, '|', g('Artist')[:30])
json.dump(dict(what='Wikimedia Commons appearance references for ZSSS (B3); 1280 px renditions of the originals',
               retrieved='2026-11-14', api='https://commons.wikimedia.org/w/api.php (categorymembers + imageinfo/extmetadata; generator=search)',
               licence_note='per file (see each record: licence verified from the Commons API extmetadata LicenseShortName / LicenseUrl / Artist)',
               redistributable='per file: reuse_in_repo', files=recs),
          open(os.path.join(out, 'SOURCES.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
