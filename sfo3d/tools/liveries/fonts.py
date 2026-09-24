"""Open-licensed fonts for re-drawing airline titles (the wordmarks are approximated with SIL Open Font License fonts from
Google Fonts; no airline font or logo file is used). Fonts are downloaded once into refs/cache/fonts/ (gitignored) from
the Google Fonts CSS API, which serves TrueType to non-woff2 clients; every family used is OFL-1.1 (listed in
docs/ATTRIBUTION_models.md). font(family, weight, italic) -> path to a .ttf."""
import os, re, urllib.request
from common import ROOT

DIR = os.path.join(ROOT, 'refs', 'cache', 'fonts')
LOCAL = {  # system fallbacks (DejaVu / Liberation: free licences) when offline
    'sans': '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
}


def font(family, weight=700, italic=False):
    os.makedirs(DIR, exist_ok=True)
    fn = os.path.join(DIR, f"{family.replace(' ', '')}-{weight}{'i' if italic else ''}.ttf")
    if os.path.exists(fn): return fn
    q = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:ital,wght@{1 if italic else 0},{weight}"
    try:
        css = urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': 'Mozilla/4.0'}), timeout=30).read().decode()
        url = re.search(r'url\((https://[^)]+\.ttf)\)', css).group(1)
        data = urllib.request.urlopen(url, timeout=60).read()
        open(fn, 'wb').write(data)
        return fn
    except Exception as e:
        print('  font fetch failed', family, weight, italic, e)
        return LOCAL['sans']
