"""Median / mean colour of a rectangle of a cached image (sRGB 0-255 and linear 0-1).

    python3 -I tools/sample.py photos/p26_08c1ce.jpg x0 y0 x1 y1
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sample(name, x0, y0, x1, y1):
    im = np.asarray(Image.open(os.path.join(HERE, 'refs', 'cache', name)).convert('RGB').crop((x0, y0, x1, y1)), float)
    px = im.reshape(-1, 3)
    med, mean, sd = np.median(px, 0), px.mean(0), px.std(0)
    lin = np.where(med / 255 <= 0.04045, med / 255 / 12.92, ((med / 255 + 0.055) / 1.055) ** 2.4)
    return med, mean, sd, lin


if __name__ == '__main__':
    a = sys.argv
    med, mean, sd, lin = sample(a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]))
    print('median sRGB', med.round().astype(int).tolist(), '#%02x%02x%02x' % tuple(med.round().astype(int)),
          'mean', mean.round(1).tolist(), 'sd', sd.round(1).tolist(), 'linear', lin.round(4).tolist())
