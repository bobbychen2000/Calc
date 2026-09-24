import sys; sys.path.insert(0, '.')
from common import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
def render(sim, W, H, bg=None, labels=True, width=2, gates=True):
    im = bg.copy() if bg is not None else Image.new('RGB', (W, H), (30, 30, 30))
    d = ImageDraw.Draw(im)
    def poly(r, col, w):
        P = sim.fwd(np.array(r, float)); pts = [tuple(p) for p in P] + [tuple(P[0])]
        d.line(pts, fill=col, width=w)
    for r in rings_all('runways'): poly(r, (255, 255, 255), width)
    for r in rings_all('taxiways'): poly(r, (230, 200, 40), max(1, width - 1))
    for r in rings_all('structures'): poly(r, (120, 200, 255), width)
    for r in rings_all('complex'): poly(r, (255, 60, 60), width)
    for r in rings_all('ba'): poly(r, (60, 255, 120), max(1, width - 1))
    try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)
    except Exception: f = None
    if gates:
        for g in D['gates']:
            if g.get('dup'): continue
            p = sim.fwd(np.array([[g['x'], g['z']]]))[0]
            col = (255, 255, 0) if g['level'] == 2 and not g['variant'] else (255, 120, 255)
            d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=col)
            if labels: d.text((p[0] + 4, p[1] - 7), g['name'], fill=col, font=f)
    if labels:
        for b in D['boardingAreas']:
            P = np.array(b['polys'][0][0], float).mean(0); p = sim.fwd(P[None])[0]
            d.text((p[0], p[1]), b['name'], fill=(60, 255, 120), font=f)
    return im
if __name__ == '__main__':
    # north-up overview of the terminal area, 1 px/m, origin offset
    x0, z0, x1, z1 = -1650, -320, -420, 980
    s = 1.0
    sim = Sim(s, 0, -x0 * s, -z0 * s)
    im = render(sim, int((x1 - x0) * s), int((z1 - z0) * s))
    d = ImageDraw.Draw(im)
    for x in range(-1600, -400, 100):
        p = sim.fwd(np.array([[x, z0]]))[0]; d.line([(p[0], 0), (p[0], im.size[1])], fill=(70, 70, 70)); d.text((p[0] + 2, 2), str(x), fill=(160, 160, 160))
    for z in range(-300, 1000, 100):
        p = sim.fwd(np.array([[x0, z]]))[0]; d.line([(0, p[1]), (im.size[0], p[1])], fill=(70, 70, 70)); d.text((2, p[1] + 2), str(z), fill=(160, 160, 160))
    im.save(SP + 'refmap.png')
