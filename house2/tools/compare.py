"""Compare a viewer render with the reference image it was rendered for.

    python3 -I tools/compare.py <image rel. to refs/cache> RENDER.png OUT.jpg [mode] [x0,y0,x1,y1]

mode: 'edges' (default) the model's edges (cyan) drawn over the photo; 'blend' 50/50; 'side' photo | render;
'all' = edges above, side-by-side below.  The render is resized to the photo; a crop box (photo pixels) zooms in.
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def compare(img, render, out, mode='edges', box=None, width=1800):
    ph = cv2.imread(os.path.join(HERE, 'refs', 'cache', img))
    rd = cv2.imread(render)
    rd = cv2.resize(rd, (ph.shape[1], ph.shape[0]), interpolation=cv2.INTER_AREA)
    if box:
        x0, y0, x1, y1 = box
        ph, rd = ph[y0:y1, x0:x1], rd[y0:y1, x0:x1]
    k = width / ph.shape[1]
    ph = cv2.resize(ph, None, fx=k, fy=k, interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    rd = cv2.resize(rd, (ph.shape[1], ph.shape[0]), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)

    def edges():
        g = cv2.cvtColor(rd, cv2.COLOR_BGR2GRAY)
        e = cv2.Canny(g, 25, 70)
        e = cv2.dilate(e, np.ones((2, 2), np.uint8))
        o = (ph * 0.8).astype(np.uint8)
        o[e > 0] = (255, 255, 0)
        return o

    if mode == 'blend':
        res = cv2.addWeighted(ph, 0.5, rd, 0.5, 0)
    elif mode == 'side':
        res = np.hstack([ph, rd])
    elif mode == 'all':
        res = np.vstack([edges(), np.hstack([cv2.resize(ph, None, fx=0.5, fy=0.5), cv2.resize(rd, None, fx=0.5, fy=0.5)])])
    else:
        res = edges()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cv2.imwrite(out, res, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('wrote', out, res.shape[1], 'x', res.shape[0])


if __name__ == '__main__':
    a = sys.argv
    compare(a[1], a[2], a[3], a[4] if len(a) > 4 else 'edges', [int(v) for v in a[5].split(',')] if len(a) > 5 else None)
