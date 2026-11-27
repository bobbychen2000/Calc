"""Band contrast of a render (fix round 3, review_visual_fix2.md L9; buildings package). Not used by the app.

For each band of 20 rows centred at y (default 60, 120, 180, 240, 300 of a 1280 x 720 view_overview), prints
  - std: the review's measure, the luminance (Rec. 709) standard deviation in the band;
  - detail: the standard deviation of (L - Gaussian blur 6 px) divided by the band mean, i.e. the small-scale contrast of the
    ground with the low-frequency haze pattern removed. The review's std also counts the haze ramp itself: the far haze grows
    with the distance outside the detailed extent, so a band that crosses the extent edge has a bright-dark-bright profile
    that inflates its std (y = 180 in view_overview);
  - mean: the band's mean luminance (sRGB levels).
--terrace: the share of the frame covered by the smooth, untextured region rising from the bottom edge (the tower cab's head
terrace in view_towercab), as the mean over columns of the bottom run whose neighbouring pixels differ by < 2.5 levels.

    python3 -I tools/buildings/band_contrast.py [--rows 60,120,180,240,300] [--terrace] img.png [img2.png ...]
"""
import sys

import numpy as np
from PIL import Image, ImageFilter


def lum(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(float)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def bands(path, rows):
    L = lum(path)
    Lb = np.asarray(Image.fromarray(np.clip(L, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(float)
    out = []
    for y in rows:
        B = L[y - 10:y + 10]; H = (L - Lb)[y - 10:y + 10]
        out.append((y, B.std(), H.std() / max(B.mean(), 1e-6), B.mean()))
    return out


def terrace(path):
    L = lum(path); Hh, W = L.shape; fr = []
    for x in range(2, W - 2, 4):
        n = 1
        for y in range(Hh - 2, -1, -1):
            if abs(L[y, x] - L[y + 1, x]) < 2.5 and abs(L[y, x] - L[y, x - 2]) < 2.5 and abs(L[y, x] - L[y, x + 2]) < 2.5:
                n += 1
            else:
                break
        fr.append(n / Hh)
    return float(np.mean(fr)), np.percentile(fr, [10, 50, 90])


def main(argv):
    rows, ter, files = [60, 120, 180, 240, 300], False, []
    it = iter(argv)
    for a in it:
        if a == '--rows':
            rows = [int(v) for v in next(it).split(',')]
        elif a == '--terrace':
            ter = True
        else:
            files.append(a)
    for f in files:
        if ter:
            m, p = terrace(f)
            print('%s: terrace share %.1f %% (columns p10 / p50 / p90 %.1f / %.1f / %.1f %%)' % (f, 100 * m, *(100 * p)))
        else:
            print(f + ': ' + ' | '.join('y %d std %.1f detail %.3f mean %.0f' % b for b in bands(f, rows)))


if __name__ == '__main__':
    main(sys.argv[1:])
