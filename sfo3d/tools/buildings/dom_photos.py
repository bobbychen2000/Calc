"""Domestic terminals - reference photos from Wikimedia Commons (reference only, never shipped).

For each listed Commons file this fetches the file-description page (HTML, not the rate-limited API), extracts the
author, licence, date and camera metadata, and downloads a <=1920 px thumbnail via Special:FilePath. Everything goes
to refs/cache/buildings/domestic/photos/ (gitignored) with manifest.json (file, url, author, licence, date, notes).
Politeness: one request every 3 s, descriptive User-Agent without personal data.

usage: python3 tools/buildings/dom_photos.py
"""
import html, json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'domestic', 'photos')
UA = 'SFOLive3D-building-research/0.1 (offline research; contact via github repo)'
FILES = {  # Commons file name -> what it shows (from the category listing; checked visually afterwards)
    '2025-08-12 09 08 29 The front of Harvey Milk Terminal 1 viewed from AirTrain SFO at San Francisco International Airport in San Mateo County, California.jpg': 'T1 landside front from AirTrain',
    'San Francisco International Airport 2025.jpg': 'T1 (category Harvey Milk Terminal 1)',
    'SFO - San Francisco International Airport 2024.jpg': 'T1 (category Harvey Milk Terminal 1)',
    'San Francisco International Airport 1 2019-12-18.jpg': 'T1 (category Harvey Milk Terminal 1)',
    'Harvey Milk Terminal 1-9221.jpg': 'T1', 'Harvey Milk Terminal 1-9226.jpg': 'T1',
    'SFO Terminal 2 from AirTrain.jpg': 'T2 landside from AirTrain',
    '2009-0722-SFO-Terminal2.jpg': 'T2 2009', 'KSFO2.jpg': 'T2', 'KSFO3.jpg': 'T2', 'KSFO4.jpg': 'T2', 'KSFO9.jpg': 'T2',
    'SFO 2024-07-29 1.jpg': 'T2', 'SFO - June 2025 - Sarah Stierch.jpg': 'T2',
    'San Francisco Airport (12411820134).jpg': 'T3', 'Airside Connector IT-T3 (36416581855).jpg': 'T3 connector',
    'SFO AirTrain Terminal 3 intl faceNorthWest AP9083765.jpg': 'T3 AirTrain',
    'Aerial photographs of San Francisco International Airport (July 2022) - 1.jpg': 'aerial 2022',
    'Aerial photographs of San Francisco International Airport (July 2022) - 2.jpg': 'aerial 2022',
    'Aerial photographs of San Francisco International Airport (July 2022) - 3.jpg': 'aerial 2022',
    'Aerial photographs of San Francisco International Airport (July 2022) - 4.jpg': 'aerial 2022',
    'Aerial view of SFO, September 2022.JPG': 'aerial 2022', 'Aerial view of SFO from departing flight, September 2025.JPG': 'aerial 2025',
    'Aerial view of San Francisco International Airport station, September 2025.JPG': 'aerial 2025',
    'SFO-aerial-view-2585.jpg': 'aerial', 'SFO-aerial-view-2586.jpg': 'aerial',
}


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.geturl()


def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def parse(page):
    page = page.replace('&#95;', '_')
    cam = re.search(r'Camera location.*?(-?\d+\.\d+)[^\d-]+(-?\d+\.\d+)', page, re.S)
    def cell(idname):
        m = re.search(r'id="%s"[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>' % idname, page, re.S)
        return text(m.group(1))[:300] if m else None
    lic = re.findall(r'class="licensetpl_short"[^>]*>(.*?)<', page)
    licurl = re.findall(r'class="licensetpl_link"[^>]*>(.*?)<', page)
    return dict(author=cell('fileinfotpl_aut'), date=cell('fileinfotpl_date'), source=cell('fileinfotpl_src'),
                description=cell('fileinfotpl_desc'),
                camera=[float(cam.group(1)), float(cam.group(2))] if cam else None, licence=sorted(set(text(x) for x in lic)),
                licence_url=sorted(set(text(x) for x in licurl)))


def main():
    os.makedirs(OUT, exist_ok=True)
    mpath = os.path.join(OUT, 'manifest.json')
    man = json.load(open(mpath)) if os.path.exists(mpath) else {}
    for i, (fn, note) in enumerate(FILES.items()):
        if fn in man and os.path.exists(os.path.join(OUT, man[fn]['local'])) and man[fn].get('author'): continue
        q = urllib.parse.quote(fn.replace(' ', '_'))
        try:
            page, _ = get('https://commons.wikimedia.org/wiki/File:' + q); time.sleep(3)
            meta = parse(page.decode('utf-8', 'ignore'))
            img, final = get('https://commons.wikimedia.org/wiki/Special:FilePath/' + q + '?width=1920'); time.sleep(3)
        except Exception as e:
            print('FAIL', fn, e); time.sleep(10); continue
        local = f'p{i:02d}.jpg'
        open(os.path.join(OUT, local), 'wb').write(img)
        man[fn] = dict(local=local, url='https://commons.wikimedia.org/wiki/File:' + q, thumb=final, note=note, **meta)
        json.dump(man, open(mpath, 'w'), indent=1)
        print(local, fn[:70], meta['licence'], (meta['author'] or '')[:40], flush=True)


if __name__ == '__main__':
    main()
