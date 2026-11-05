# Curtain-wall glass measurements (engine close-out round 2, docs/research/engine_impl.md §4.8). Display sRGB values.
#   python3 tools/build3/glass_meas.py dev <OUT of job_glass.mjs>     # js/three/dev/glasstest.html renders (glass.json)
#   python3 tools/build3/glass_meas.py app <OUT of job_close2.mjs> [prefix c2]
# dev: the pane band (facade x = 15, G+5.3 .. G+13.1, z -40 .. 40) projected with each variant's camera (glass.json cam /
#      tgt), plus the shaded apron 4-8 m and the sunlit apron 45-60 m in front of the facade as references.
# app: the round-2 verifier's pane measure in gate:B20,130,1,24 (darker 60 % by luminance of x 20-170, y 295-330), the
#      low view gate:B20,70,1,6 (x 5-370, y 180-222), and 13 x 13 px around each aircraft light of close2.json navProbe.
# Writes <OUT>/glass_meas.json.
import sys, json, numpy as np
from PIL import Image
LW = np.array([0.2126, 0.7152, 0.0722])
def stats(px):
    L = px @ LW; dk = px[L <= np.percentile(L, 60)]
    return dict(px=int(len(px)), mean=px.mean(0).round(1).tolist(), dark60=dk.mean(0).round(1).tolist(), BmR=round(float(dk[:, 2].mean() - dk[:, 0].mean()), 1),
                GmR=round(float(dk[:, 1].mean() - dk[:, 0].mean()), 1), lum=round(float((dk @ LW).mean()), 1))
def load(f): return np.asarray(Image.open(f).convert('RGB')).astype(float)
mode, d = sys.argv[1], sys.argv[2]; out = {}
if mode == 'dev':
    from matplotlib.path import Path
    G = 3.0; fov = np.radians(50); W, H = 960, 540; R = json.load(open(f'{d}/glass.json'))
    yy, xx = np.mgrid[0:H, 0:W]; P = np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]
    for n, v in R['variants'].items():
        cp, tg = np.array(v.get('cam', R['probe']['cam'])), np.array(v.get('tgt', [45.0, G + 4, 0.0]))
        f = tg - cp; f /= np.linalg.norm(f); r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r); u = np.cross(r, f); t = np.tan(fov / 2)
        pr = lambda p: [W / 2 + (np.subtract(p, cp) @ r) / ((np.subtract(p, cp) @ f) * t) * H / 2, H / 2 - (np.subtract(p, cp) @ u) / ((np.subtract(p, cp) @ f) * t) * H / 2]
        mask = lambda x0, x1, y0, y1, z0=-40, z1=40, vert=True: Path([pr([x0, y0, z0]), pr([x0, y0, z1]), pr([x1, y1, z1]), pr([x1, y1, z0])] if vert else [pr([x0, G, z0]), pr([x0, G, z1]), pr([x1, G, z1]), pr([x1, G, z0])]).contains_points(P).reshape(H, W)
        im = load(f'{d}/glass_{n}.png'); m = mask(15, 15, G + 5.3, G + 13.1)
        out[n] = stats(im[m]); ma, ms = mask(19, 23, 0, 0, vert=False), mask(60, 75, 0, 0, vert=False)
        out[n]['shadeApron'] = im[ma].mean(0).round(1).tolist() if ma.sum() else None; out[n]['sunApron'] = im[ms].mean(0).round(1).tolist() if ms.sum() else None
        print(f"{n:16s}", out[n])
else:
    P = sys.argv[3] if len(sys.argv) > 3 else 'c2'; R = json.load(open(f'{d}/close2.json'))
    for v in R['views']:
        box = (5, 180, 370, 222) if v.startswith('gate_B20_low') else (20, 295, 170, 330)
        if v.startswith('gate_B20'):
            im = load(f'{d}/{P}_{v}.png'); out[v] = stats(im[box[1]:box[3], box[0]:box[2]].reshape(-1, 3)); print(f'{v:24s}', out[v])
    if 'navProbe' in R:
        im = load(f'{d}/{P}_day_ac8.png'); H, W, _ = im.shape; out['nav'] = []
        for s in R['navProbe']['sprites']:
            x, y = s['px']
            if not (0 <= x < W and 0 <= y < H): continue
            c = im[max(0, y - 6):y + 7, max(0, x - 6):x + 7].reshape(-1, 3)
            e = dict(c=s['c'], i=s['i'], s=s['s'], pos=s['pos'], px=s['px'], max=c.max(0).tolist(), mean=c.mean(0).round(1).tolist(),
                     greenDom=int(((c[:, 1] > c[:, 0] + 20) & (c[:, 1] > c[:, 2] + 10)).sum()), redDom=int(((c[:, 0] > c[:, 1] + 20) & (c[:, 0] > c[:, 2] + 20)).sum()))
            out['nav'].append(e); print('light', e)
json.dump(out, open(f'{d}/glass_meas.json', 'w'), indent=1)
