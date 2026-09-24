#!/usr/bin/env python3
"""Measure livery layouts on a reference side view (official graphic or profile drawing, nose to the left; reference
only, images are not shipped): prints, for a colour, the upper and lower boundary of that colour at stations along the
body in the painter's design coordinates (sn = station / length, cabin eta = (y - cabin centre) / cabin half height).

Usage: python3 tools/liveries/measure_ref.py <image> --nose X --tail X --top Y --bot Y --color '#003366' [--tol 60]
  nose/tail: x (px) of the nose tip and the tail-cone tip; top/bot: y (px) of the cabin crown and keel at mid-cabin.
  --auto-body: also print the body outline (non-background extent) per station.
"""
import argparse
import numpy as np
from PIL import Image


def hexrgb(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('image'); ap.add_argument('--nose', type=float, required=True); ap.add_argument('--tail', type=float, required=True)
    ap.add_argument('--top', type=float, required=True); ap.add_argument('--bot', type=float, required=True)
    ap.add_argument('--color', action='append', default=[]); ap.add_argument('--tol', type=float, default=60)
    ap.add_argument('--n', type=int, default=40); ap.add_argument('--ymin', type=float, default=None); ap.add_argument('--ymax', type=float, default=None)
    ap.add_argument('--sample', action='append', default=[], help='x,y: print the colour there')
    a = ap.parse_args()
    im = np.asarray(Image.open(a.image).convert('RGB')).astype(float)
    yc = (a.top + a.bot) / 2; hh = (a.bot - a.top) / 2
    for sxy in a.sample:
        x, y = map(int, sxy.split(','))
        p = im[y - 2:y + 3, x - 2:x + 3].reshape(-1, 3).mean(0)
        print(f'sample {x},{y}: #{int(p[0]):02X}{int(p[1]):02X}{int(p[2]):02X}  sn={(x - a.nose) / (a.tail - a.nose):.3f} eta={(yc - y) / hh:.3f}')
    y0 = int(a.ymin) if a.ymin is not None else 0; y1 = int(a.ymax) if a.ymax is not None else im.shape[0]
    for c in a.color:
        col = hexrgb(c); d = np.abs(im - col).sum(-1) < a.tol
        print('colour', c)
        for sn in np.linspace(0, 1, a.n + 1):
            x = int(round(a.nose + sn * (a.tail - a.nose)))
            if x < 0 or x >= im.shape[1]: continue
            ys = np.where(d[y0:y1, x])[0] + y0
            if len(ys):
                print(f'  sn {sn:.3f}: eta {(yc - ys.min()) / hh:+.3f} .. {(yc - ys.max()) / hh:+.3f}  ({len(ys)} px)')
