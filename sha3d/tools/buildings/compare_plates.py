"""Photo-match plates for the P2d building renders: a Wikimedia Commons photo above the render made from the matching
camera (jobs/buildings.mjs views p02 / p02_tower), with a credit strip. Proportions check only (nothing is traced or
textured from the photos).

usage: python3 -I tools/buildings/compare_plates.py RENDER_DIR OUT_DIR
  RENDER_DIR holds buildings_p02.png and buildings_p02_tower.png (or b_p02.png / b_p02_tower.png);
  writes OUT_DIR/buildings_compare_t1.png and OUT_DIR/buildings_compare_tower.png.

Photo: "202309 Terminal 1 of Shanghai Hongqiao Airport.jpg" by MNXANL, CC BY-SA 4.0
(https://commons.wikimedia.org/wiki/File:202309_Terminal_1_of_Shanghai_Hongqiao_Airport.jpg), 1920 px rendition, local copy
refs/cache/photos/commons_full/02_1920.jpg (docs/phase1/photos_credits.md no. 02). Modifications: cropped and scaled,
paired with our render, caption added. The plates are released under CC BY-SA 4.0 (share-alike of the photo).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PHOTO = os.path.join(ROOT, 'refs', 'cache', 'photos', 'commons_full', '02_1920.jpg')
CREDIT = ('Top: "202309 Terminal 1 of Shanghai Hongqiao Airport.jpg" by MNXANL, CC BY-SA 4.0 (Wikimedia Commons), cropped / scaled. '
          'Bottom: SHA Live 3D render from the matching camera (inferred forms). Plate: CC BY-SA 4.0.')


def font(sz):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def find(d, names):
    for n in names:
        p = os.path.join(d, n)
        if os.path.exists(p):
            return p
    raise SystemExit('missing render: ' + ' / '.join(names))


def plate(top, bottom, labels, out, width=1280):
    a = top.resize((width, round(top.height * width / top.width)), Image.LANCZOS)
    b = bottom.resize((width, round(bottom.height * width / bottom.width)), Image.LANCZOS)
    strip = 54
    im = Image.new('RGB', (width, a.height + b.height + strip), (24, 24, 24))
    im.paste(a, (0, 0)); im.paste(b, (0, a.height))
    d = ImageDraw.Draw(im); f = font(15); fs = font(12)
    for y, t in ((6, labels[0]), (a.height + 6, labels[1])):
        d.rectangle([6, y, 16 + d.textlength(t, font=f), y + 22], fill=(0, 0, 0))
        d.text((11, y + 3), t, fill=(255, 255, 255), font=f)
    words, line, lines = CREDIT.split(' '), '', []
    for w in words:
        if d.textlength(line + ' ' + w, font=fs) > width - 20:
            lines.append(line); line = w
        else:
            line = (line + ' ' + w).strip()
    lines.append(line)
    for i, t in enumerate(lines[:3]):
        d.text((10, a.height + b.height + 6 + 15 * i), t, fill=(210, 210, 210), font=fs)
    im.save(out, optimize=True)
    print('wrote', out, im.size)


def main():
    rd, od = sys.argv[1], sys.argv[2]
    ph = Image.open(PHOTO).convert('RGB')          # 1920 x 1440
    r_t1 = Image.open(find(rd, ['buildings_p02.png', 'b_p02.png'])).convert('RGB')        # 1280 x 960, same camera
    r_tw = Image.open(find(rd, ['buildings_p02_tower.png', 'b_p02_tower.png'])).convert('RGB')   # 960 x 720, 6 deg vfov
    # full-frame band around the terminal: rows 520-760 of the photo (= 347-507 of the 960 px render)
    band_p = ph.crop((0, 520, 1920, 760)); band_r = r_t1.crop((0, round(520 * 960 / 1440), 1280, round(760 * 960 / 1440)))
    plate(band_p, band_r, ['photo 02 (2023), rows 520-760', 'render, camera matched (vfov 55.0 deg, 4:3)'], os.path.join(od, 'buildings_compare_t1.png'))
    # tower: the render's 6 deg vertical field at 720 px = 120 px per deg; the photo's 1440 px / 55 deg = 26.2 px per deg
    k = (1440 / 55.0) / (720 / 6.0)                  # photo px per render px
    cx, cy = 777, 704 - 24.5 / 44.5 * 125           # tower axis column, tower mid-height row (24.5 m above the ground)
    w2, h2 = 960 * k / 2, 720 * k / 2
    crop = ph.crop((round(cx - w2), round(cy - h2), round(cx + w2), round(cy + h2)))
    plate(crop.resize((960, 720), Image.BICUBIC), r_tw, ['photo 02, tower (enlarged ~4.6x)', 'render, same camera, vfov 6 deg'], os.path.join(od, 'buildings_compare_tower.png'), width=960)


if __name__ == '__main__':
    main()
