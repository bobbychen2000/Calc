"""B3: contact sheet of the Commons appearance references whose licence permits reuse (reuse_in_repo == 'yes').

usage: python3 -I sha3d/tools/photos/contact_sheet.py PHOTO_DIR OUT.jpg [subjects.json]
Each tile: the photo (scaled to fit 400x300, whole frame, not cropped), its number, subject, author, licence, date.
Files marked reference-only are left out. Full credits (licence URL, file page): docs/phase1/photos_credits.md
(tools/photos/credits.py). Fix round 1: author = first line of the Artist field, date cleaned (commons_meta.py).
"""
import json, sys, os, textwrap
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commons_meta import clean_author, clean_date   # noqa: E402
d, outp = sys.argv[1], sys.argv[2]
subj = json.load(open(sys.argv[3], encoding='utf-8')) if len(sys.argv) > 3 else {}
S = json.load(open(os.path.join(d, 'SOURCES.json'), encoding='utf-8'))
recs = [r for r in S['files'] if r['reuse_in_repo'] == 'yes']
TW, TH, CAP = 400, 300, 58
cols = 5; rows = (len(recs) + cols - 1) // cols
def font(sz):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f): return ImageFont.truetype(f, sz)
    return ImageFont.load_default()
F1, F2 = font(13), font(11)
CJK = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'      # for authors written in CJK script (DejaVu has no glyphs)
F2C = ImageFont.truetype(CJK, 11) if os.path.exists(CJK) else F2
fit = lambda txt: F2C if any(ord(c) > 0x2E7F for c in txt) else F2
W = cols * (TW + 8) + 8; H = rows * (TH + CAP + 8) + 8 + 46
sheet = Image.new('RGB', (W, H), (24, 24, 24)); dr = ImageDraw.Draw(sheet)
for i, r in enumerate(recs):
    im = Image.open(os.path.join(d, r['file'])).convert('RGB'); im.thumbnail((TW, TH))
    x = 8 + (i % cols) * (TW + 8); y = 8 + (i // cols) * (TH + CAP + 8)
    sheet.paste(im, (x + (TW - im.width) // 2, y + (TH - im.height) // 2))
    num = r['file'][:2]
    s = subj.get(num, r['title'][5:60])
    author = clean_author(r['author'])[:34]
    date = clean_date(r['date'], r['title'][5:])[:7]
    dr.text((x, y + TH + 3), f'{num}  {s}'[:58], fill=(255, 255, 255), font=F1)
    line2 = f'{author}, {r["licence"]}, {date}'[:66]
    dr.text((x, y + TH + 21), line2, fill=(200, 200, 200), font=fit(line2))
    dr.text((x, y + TH + 36), ('commons: ' + r['title'][5:])[:70], fill=(150, 150, 150), font=F2)
foot = ('Wikimedia Commons photos, each by its author under the licence shown (verified via the Commons API). Each photo is '
        'scaled down to fit its tile (whole frame, not cropped) and captioned by us. Full credits with licence URLs and '
        'file pages: docs/phase1/photos_credits.md. This compilation: CC BY-SA 4.0. GFDL-only files are left out.')
for k, line in enumerate(textwrap.wrap(foot, 190)): dr.text((8, H - 42 + 16 * k), line, fill=(220, 220, 220), font=F2)
sheet.save(outp, quality=85)
print('ok', outp, len(recs), 'photos', sheet.size)
