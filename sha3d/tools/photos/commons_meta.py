"""Clean-up of Wikimedia Commons extmetadata fields for credits (B3, Fix round 1).

The Artist field can carry extra lines (e.g. an EXIF sentence "This photo was taken with ...") and DateTimeOriginal can
be free text ("Taken on 4 November 2016"), which garbled two contact-sheet captions. These helpers return the author's
name (first non-empty line) and a YYYY-MM[-DD] date, falling back to a date in the file title (e.g. "201611 ..." or
"29-DEC-2023 ...").
"""
import re

MONTHS = {m: i for i, m in enumerate(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'), 1)}


def clean_author(a):
    for line in (a or '').replace('\xa0', ' ').splitlines():
        if line.strip():
            return line.strip()
    return '?'


def clean_date(d, title=''):
    d = (d or '').replace('\xa0', ' ').strip()
    m = re.match(r'(\d{4})-(\d{2})(?:-(\d{2}))?', d)
    if m:
        return '-'.join(x for x in m.groups() if x)
    for s in (d, title):
        m = re.search(r'(\d{1,2})[ -]([A-Za-z]{3})[a-z]*[ -](\d{4})', s)
        if m and m.group(2).lower() in MONTHS:
            return f'{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}'
    m = re.search(r'(?:^|\D)((?:19|20)\d{2})(0[1-9]|1[0-2])(?:\D|$)', title)
    if m:
        return f'{m.group(1)}-{m.group(2)}'
    m = re.search(r'((?:19|20)\d{2})', d)
    return m.group(1) if m else ''
