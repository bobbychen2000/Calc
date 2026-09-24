"""Visual check of a registration: crops around the predicted image positions of FAA runway ends and runway
centreline intersections, with the prediction marked."""
import sys, math
import numpy as np
from PIL import Image, ImageDraw
from common import *
from rectify import sim_of
from stview import st2w
lat0, lon0 = 37.6188056, -122.3754167
mlat = 110990.0; mlon = 111320.0 * math.cos(math.radians(lat0))
def dms(d, m): return d + m / 60
def w(lat, lon): return ((lon - lon0) * mlon, -(lat - lat0) * mlat)
ENDS = {'28R': w(dms(37, 36.812017), -dms(122, 21.428467)), '28L': w(dms(37, 36.702717), -dms(122, 21.500950)),
        '10L': w(dms(37, 37.724323), -dms(122, 23.603512)), '10R': w(dms(37, 37.577467), -dms(122, 23.586327)),
        '1L': w(dms(37, 36.473872), -dms(122, 22.975710)), '19R': w(dms(37, 37.588882), -dms(122, 22.236565)),
        '1R': w(dms(37, 36.379793), -dms(122, 22.862445)), '19L': w(dms(37, 37.640532), -dms(122, 22.026650))}
def inter(a1, a2, b1, b2):
    p, r = np.array(ENDS[a1]), np.array(ENDS[a2]) - np.array(ENDS[a1]); q, s = np.array(ENDS[b1]), np.array(ENDS[b2]) - np.array(ENDS[b1])
    t = np.cross(q - p, s) / np.cross(r, s); return tuple(p + r * t)
PTS = dict(ENDS)
PTS['X1L-10L'] = inter('1L', '19R', '10L', '28R'); PTS['X1L-10R'] = inter('1L', '19R', '10R', '28L')
PTS['X1R-10L'] = inter('1R', '19L', '10L', '28R'); PTS['X1R-10R'] = inter('1R', '19L', '10R', '28L')
if __name__ == '__main__':
    n = sys.argv[1]; half = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    U = open(SP + 'uniq.txt').read().split(); im = Image.open([u for u in U if n in u][0]).convert('RGB')
    S = sim_of(n); tiles = []
    for k, wp in PTS.items():
        p = S.fwd(np.array([wp]))[0]
        if not (half < p[0] < 1290 - half and 330 + half < p[1] < 2250 - half): continue
        c = im.crop((int(p[0]) - half, int(p[1]) - half, int(p[0]) + half, int(p[1]) + half)).resize((240, 240), Image.LANCZOS)
        d = ImageDraw.Draw(c); d.line([(110, 120), (130, 120)], fill=(255, 0, 0), width=2); d.line([(120, 110), (120, 130)], fill=(255, 0, 0), width=2)
        d.text((4, 4), k, fill=(255, 255, 0)); tiles.append(c)
    if not tiles: print('no FAA points in view'); sys.exit()
    sheet = Image.new('RGB', (240 * len(tiles), 240)); [sheet.paste(t, (i * 240, 0)) for i, t in enumerate(tiles)]
    sheet.save(SP + f'faa_{n}.png'); print(n, len(tiles), 'points')
