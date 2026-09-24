from common import *
from PIL import Image
import numpy as np, json
U = open(SP + 'uniq.txt').read().split()
out = {}
for f in U:
    name = f.split('/')[-1][:8]
    a = np.asarray(Image.open(f).convert('RGB')).astype(int)
    lum = a.mean(2)
    wht = (a.min(2) > 236)
    cands = []
    for y in range(1900, 2560):
        row = wht[y, 400:1110]
        r = 0; runs = []
        for x, v in enumerate(row):
            if v: r += 1
            else:
                if r >= 50: runs.append((x - r + 400, x - 1 + 400))
                r = 0
        if r >= 50: runs.append((len(row) - r + 400, len(row) - 1 + 400))
        for x0, x1 in runs:
            # thin bar: rows 4 px above and below mostly non-white, and darker outline within 3 px
            above = wht[y - 5, x0 + 10:x1 - 10].mean(); below = wht[y + 5, x0 + 10:x1 - 10].mean()
            if above < 0.3 and below < 0.3:
                cands.append((x1 - x0, y, x0, x1))
    if not cands: print(name, 'no bar'); continue
    cands.sort(reverse=True)
    L, y, x0, x1 = cands[0]
    # bar may be 3-5 px thick: take centre row of the block of rows with a similar run
    rows = [c[1] for c in cands if abs(c[2] - x0) < 4 and abs(c[3] - x1) < 4]
    yc = int(np.mean(rows))
    # ticks: columns with white pixels 8..24 px below (metric tick) / above (left end tick)
    down = [x for x in range(x0 + 4, x1 - 3) if wht[yc + 7:yc + 24, x].sum() > 10]
    up = [x for x in range(x0 - 3, x1 + 3) if wht[yc - 24:yc - 7, x].sum() > 10]
    out[name] = {'y': yc, 'x0': x0, 'x1': x1, 'down': [min(down), max(down)] if down else None, 'up': [min(up), max(up)] if up else None}
    print(name, out[name])
json.dump(out, open(SP + 'scalebars.json', 'w'), indent=1)
