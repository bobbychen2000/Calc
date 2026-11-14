"""Compare docs/phase1/photos_credits.md with C2's cached live Commons API answer (api_25.json)
and B3's SOURCES.json. Usage: python3 -I rv_credits.py <sha3d>"""
import json, re, sys, html, urllib.parse
S = sys.argv[1]
api = json.load(open(f'{S}/refs/cache/verify_c2/commons/api_25.json'))['query']['pages']
api = list(api.values()) if isinstance(api, dict) else api
A = {}
for p in api:
    em = p['imageinfo'][0]['extmetadata']
    artist = re.sub(r'<[^>]+>', '', em.get('Artist', {}).get('value', ''))
    A[p['title'].replace('File:', '').replace('_', ' ')] = {
        'lic': em.get('LicenseShortName', {}).get('value'), 'artist': html.unescape(artist).strip(),
        'restr': em.get('Restrictions', {}).get('value'), 'attr': em.get('AttributionRequired', {}).get('value')}
md = open(f'{S}/docs/phase1/photos_credits.md', encoding='utf-8').read()
rows = [l for l in md.splitlines() if re.match(r'^\| \d\d \|', l)]
print('credit rows', len(rows), ' api files', len(A))
LURL = {'CC BY 4.0': 'https://creativecommons.org/licenses/by/4.0/', 'CC BY-SA 4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
        'CC BY-SA 3.0': 'https://creativecommons.org/licenses/by-sa/3.0/'}
seen = set()
for l in rows:
    c = [x.strip() for x in l.strip('|').split('|')]
    no, subj, title_cell, author, lic, date, mod = c
    m = re.match(r'\[(.+?)\]\((https://commons\.wikimedia\.org/wiki/File%3A[^)]+)\)', title_cell)
    title, url = m.group(1), m.group(2)
    url_title = urllib.parse.unquote(url.split('File%3A', 1)[1]).replace('_', ' ')
    a = A.get(title)
    seen.add(title)
    problems = []
    if not a:
        problems.append('title not in API answer')
    else:
        if url_title != title: problems.append(f'url title differs: {url_title}')
        lm = re.match(r'\[(.+?)\]\((.+?)\)', lic)
        if lm:
            if lm.group(1) != a['lic']: problems.append(f"licence {lm.group(1)} vs API {a['lic']}")
            if LURL.get(lm.group(1)) != lm.group(2): problems.append('licence URL mismatch')
        else:
            if not (a['lic'] == 'Public domain' and lic.startswith('Public domain')): problems.append(f"licence {lic[:30]} vs API {a['lic']}")
        an = a['artist']
        if author != an and author.split(' (')[0] != an and author not in an:
            problems.append(f'author {author!r} vs API {an!r}')
        if a['restr']: problems.append('restriction ' + a['restr'])
    if 'scaled' not in mod: problems.append('no modification note')
    print(no, 'OK' if not problems else problems)
print('API files not credited:', [t for t in A if t not in seen])
