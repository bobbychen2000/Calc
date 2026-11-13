"""Observed type sample at SHA from Wikimedia Commons photo TITLES (no images read).

Reads the Commons API search results saved in sha3d/refs/cache/fleet/commons_livref/*.json, keeps files whose title says the
aircraft was photographed at / on approach to Shanghai Hongqiao (SHA), parses airline, type and registration from the title,
dedupes by registration within each photo set, and counts aircraft per type family.

This is a photographer-selected sample (spotters choose what to shoot and what to upload), so it is an indication of what
flies at SHA, not a traffic statistic. Usage: python3 -I commons_sha_sample.py <dir with the *.json> [--list]
"""
import json, glob, os, re, sys, collections

D = sys.argv[1]
LIST = '--list' in sys.argv
titles = {}
for f in sorted(glob.glob(os.path.join(D, '*.json'))):
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    q = d.get('query') or {}
    for x in q.get('search', []):
        titles[x['title'][5:]] = x.get('timestamp', '')
    for p in (q.get('pages') or {}).values():
        titles[p['title'][5:]] = ''

SHA = re.compile(r'(Shanghai Hongqiao|Shanghao Hongqiao|towards SHA|to SHA\b|at SHA\b|@SHA|- SHA \(|ZSSS)', re.I)
REG = re.compile(r'\b(B-[0-9A-Z]{4,5}|B-L[A-Z]{2}|HL\d{4}|JA\d{2,3}[A-Z0-9]{0,2}|VP-[A-Z]{3}|VH-[A-Z]{3}|N\d{1,5}[A-Z]{0,2})\b')
FAM = [  # (family, regex on the title)
    ('C919', r'C919|C-919'), ('C909 / ARJ21', r'C909|ARJ21|ARJ-21'),
    ('A320 family', r'A3(19|20|21)|A32[01]neo|A319neo|A321LR'),
    ('737 family', r'Boeing 737|737-[6-9]00|737 MAX|737-8 MAX|\b737\b'),
    ('A330', r'A330|A33[0-9]-'), ('A350', r'A350'), ('787', r'787'), ('777', r'777'), ('767', r'767'), ('747', r'747'),
    ('E-Jet', r'Embraer|E190|E195|ERJ'), ('A380', r'A380'), ('business jet', r'Gulfstream|Global|Challenger|Falcon|Legacy|Lineage|Citation|ACJ|BBJ'),
]
SETS = [('4300streetcar May/Jun 2025-26', r'on final approach to Shangha[io] Hongqiao (May 2026|June 2025)'),
        ('Benlisquare 2026-05-03', r'on final approach towards SHA'),
        ('other', r'.')]
rows = []
for t, ts in titles.items():
    if not SHA.search(t):
        continue
    fam = next((f for f, rx in FAM if re.search(rx, t)), None)
    reg = REG.search(t)
    yr = re.search(r'(20[12]\d)', t)
    st = next(s for s, rx in SETS if re.search(rx, t))
    if st.startswith('Benlisquare') and not yr:  # this set's DateTimeOriginal is 2026-05-03 (Commons extmetadata, search_*.json)
        yr = re.match(r'(2026)', '2026')
    airline = re.split(r'\s+(Airbus|Boeing|Comac|COMAC|Embraer)\b', t)[0].strip() if fam else ''
    rows.append(dict(title=t, fam=fam, reg=reg.group(1) if reg else None, year=yr.group(1) if yr else None, set=st, airline=airline))

print('titles matching SHA:', len(rows), '| with a type in the title:', sum(1 for r in rows if r['fam']))
for st, _ in SETS:
    seen = {}
    for r in rows:
        if r['set'] != st or not r['fam']:
            continue
        if st == 'other' and (r['year'] or '0') < '2023':
            continue
        seen[r['reg'] or r['title']] = r
    c = collections.Counter(r['fam'] for r in seen.values())
    n = sum(c.values())
    print('\n== set: %s  (distinct aircraft with a type: %d%s)' % (st, n, '; photos dated 2023+' if st == 'other' else ''))
    for fam, k in c.most_common():
        print('   %-14s %3d  %4.0f %%' % (fam, k, 100.0 * k / n))
    a = collections.Counter(r['airline'] for r in seen.values())
    print('   airlines:', ', '.join('%s %d' % x for x in a.most_common()))
    if LIST:
        for r in sorted(seen.values(), key=lambda r: r['fam']):
            print('     ', r['fam'], '|', r['title'][:110])

# all sets together, photos dated 2024 or later (or undated set titles of May 2026), one entry per registration
allr = {}
for r in rows:
    if not r['fam'] or (r['year'] or '0') < '2024':
        continue
    allr.setdefault(r['reg'] or r['title'], r)
c = collections.Counter(r['fam'] for r in allr.values()); n = sum(c.values())
print('\n== combined, 2024+ photos, distinct registrations: %d' % n)
for fam, k in c.most_common():
    print('   %-14s %3d  %4.0f %%' % (fam, k, 100.0 * k / n))
biz = [r['title'] for r in allr.values() if r['reg'] and r['reg'].startswith(('VP-', 'N'))]
print('   private / non-airline registrations:', biz)
