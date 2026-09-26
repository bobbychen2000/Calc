"""Fetch and text-extract the landside-building sources (research support, tools/buildings/landside_*).

Usage:  python3 tools/buildings/landside_fetch.py URL NAME        -> refs/cache/buildings/landside/src/NAME(.html|.pdf) + .txt
        python3 tools/buildings/landside_fetch.py --txt FILE       -> re-extract text only
Downloads stay in refs/cache/ (gitignored; third-party content, reference only). HTML -> text with the stdlib
html.parser (scripts/styles dropped); PDF -> text with PyMuPDF, one "=== page N ===" marker per page.
"""
import html.parser
import os
import re
import subprocess
import sys

CACHE = os.path.join(os.path.dirname(__file__), '..', '..', 'refs', 'cache', 'buildings', 'landside', 'src')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'


class _T(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0

    def handle_starttag(self, tag, a):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip += 1
        if tag in ('p', 'br', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'td', 'th', 'section', 'article'):
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg') and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def html_text(path):
    p = _T(); p.feed(open(path, encoding='utf-8', errors='replace').read())
    t = ''.join(p.out)
    t = re.sub(r'[ \t\r\f\v]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return t.strip()


def pdf_text(path):
    import pymupdf
    doc = pymupdf.open(path)
    return '\n'.join(f'=== page {i + 1} ===\n' + pg.get_text() for i, pg in enumerate(doc))


def extract(path):
    with open(path, 'rb') as f:
        head = f.read(5)
    t = pdf_text(path) if head.startswith(b'%PDF') else html_text(path)
    open(os.path.splitext(path)[0] + '.txt', 'w').write(t)
    return t


def fetch(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    r = subprocess.run(['curl', '-sS', '-L', '-m', '180', '-A', UA, '-o', path, '-w', '%{http_code} %{content_type}', url],
                       capture_output=True, text=True)
    print(r.stdout, r.stderr.strip(), os.path.getsize(path) if os.path.exists(path) else 0, name)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        t = extract(path)
        print(len(t), 'chars of text')


if __name__ == '__main__':
    if sys.argv[1] == '--txt':
        for f in sys.argv[2:]:
            print(f, len(extract(f)))
    else:
        fetch(sys.argv[1], sys.argv[2])
