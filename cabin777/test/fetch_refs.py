# Download the official ANA seat-page photos of the 777-300ER "new 212-seat" cabin into ref/ana/ (gitignored, reference
# only - never commit or embed them; test/make_swatches.py cuts the tracked tex/ tiles from them).
# Usage: python3 test/fetch_refs.py      (-> ref/ana/{f,c,py,y}_<id>-lang-multi.jpg + ref/sheet_{f,c,py,y}.jpg)
import os, re, subprocess, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.environ.get('REF_OUT') or os.path.join(root, 'ref', 'ana')
BASE = 'https://www.ana.co.jp/en/jp/guide/flight_service_info/int-service/'
PAGES = {'y': 'y/seat-b777_300er_new/', 'py': 'py/seat-b777_300er_new/', 'c': 'c/seat-777_300er/', 'f': 'f/seat-f-777_300er/'}


def get(url):
    # curl rather than urllib: it honours the sandbox proxy / CA settings (python's urllib got disconnected by ana.co.jp)
    return subprocess.run(['curl', '-sSL', '--retry', '3', '-m', '60', url], check=True, capture_output=True).stdout


def main():
    os.makedirs(out, exist_ok=True)
    n = 0
    for cls, page in PAGES.items():
        html = get(BASE + page).decode('utf-8', 'replace')
        for path in sorted(set(re.findall(r'/cont-image/[^"\'\s()\\]+\.(?:jpg|jpeg|png|webp)', html))):
            fn = os.path.join(out, f'{cls}_{os.path.basename(path)}')
            if not os.path.exists(fn):
                open(fn, 'wb').write(get('https://www.ana.co.jp' + path))
            n += 1
    print('ANA reference photos:', n, '->', out)
    try:
        from PIL import Image, ImageDraw
        import glob
        for cls in PAGES:
            fs = sorted(glob.glob(os.path.join(out, f'{cls}_*.jpg')))
            if not fs: continue
            W = 480
            th = [Image.open(f).convert('RGB') for f in fs]
            th = [im.resize((W, int(im.height * W / im.width))) for im in th]
            H = max(t.height for t in th); cols = 4; rows = (len(th) + cols - 1) // cols
            s = Image.new('RGB', (cols * W, rows * (H + 14)), 'white'); d = ImageDraw.Draw(s)
            for i, (t, f) in enumerate(zip(th, fs)):
                x, y = (i % cols) * W, (i // cols) * (H + 14)
                s.paste(t, (x, y + 14)); d.text((x + 2, y), os.path.basename(f), fill='black')
            s.save(os.path.join(root, 'ref', f'sheet_{cls}.jpg'), quality=85)
    except ImportError:
        print('(pip install pillow for contact sheets)')


if __name__ == '__main__':
    sys.exit(main())
