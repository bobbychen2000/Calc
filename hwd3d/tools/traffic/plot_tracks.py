#!/usr/bin/env python3
"""Plot drawn ground tracks of the traffic harness over NAIP 2024 (hwd3d Phase 2, P3 debugging / verification tool).
Input: out/traffic/dump_<name>.json (replay_engine.mjs --dump; masked keys only, gitignored). Draws the taxi graph links,
the raw ADS-B fixes (dots: white = ground flag, cyan = ground by kinematics / runway contact, red = airborne) and the
drawn body path at 1 Hz (orange = along a taxi-graph route across a hole, yellow = Hermite / held), for the tracks
whose drawn gear left the pavement most often (or --keys). Output: out/traffic/plot_<name>_<i>.png.
usage: python3 -I hwd3d/tools/traffic/plot_tracks.py weekend [--n 6] [--keys k1,k2] [--box x0,z0,x1,z1]
"""
import argparse, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(HWD, 'tools', 'common'))
import hwd_frame as F  # noqa: E402

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('--n', type=int, default=6); ap.add_argument('--keys'); ap.add_argument('--box'); ap.add_argument('--pad', type=float, default=60)
    a = ap.parse_args()
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from PIL import Image; Image.MAX_IMAGE_PIXELS = None
    D = json.load(open(os.path.join(HWD, 'out', 'traffic', 'dump_%s.json' % a.name)))
    run = json.load(open(os.path.join(HWD, 'out', 'traffic', 'run_%s.json' % a.name)))
    G = json.load(open(os.path.join(HWD, 'data', 'hwd_taxigraph.json'))); A = json.load(open(os.path.join(HWD, 'data', 'hwd_airport.json')))
    gj = json.load(open(os.path.join(HWD, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.json'))); e0, n1, g = gj['origin_E'], gj['origin_N'], gj['pixel_size_m']
    def w2px(x, z):
        la, lo = F.world_to_ll(x, z); E, N = F.ll_to_utm10(la, lo); return (E - e0) / g - 0.5, (n1 - N) / g - 0.5
    xs = np.linspace(-1200, 1200, 7); zs = np.linspace(-1000, 1000, 7)
    W = np.array([(x, z) for x in xs for z in zs]); P = np.array([w2px(x, z) for x, z in W]); Mx = np.c_[W, np.ones(len(W))]
    coef, *_ = np.linalg.lstsq(Mx, P, rcond=None); T = lambda pts: np.asarray(pts, float).reshape(-1, 2) @ coef[:2] + coef[2]
    im = Image.open(os.path.join(HWD, 'refs', 'cache', 'naip', 'naip_2024_hwd_rgb.jpg')).convert('RGB')
    if a.keys: keys = a.keys.split(',')
    else:
        # rank by drawn off-pavement points: recompute cheaply = ground points far from any taxi link / apron is unknown here,
        # so rank by ground points count of tracks that the run listed in the worst cells
        score = {k: sum(1 for p in d['p'] if len(p) > 9 and p[9]) for k, d in D.items()}
        keys = [k for k, v in sorted(score.items(), key=lambda q: -q[1]) if v][:a.n]
    for i, k in enumerate(keys):
        d = D[k]; gp = [p for p in d['p'] if p[3]]
        if a.box: x0, z0, x1, z1 = map(float, a.box.split(','))
        else:
            if not gp: continue
            sel = [p for p in gp if len(p) > 9 and p[9]] or gp
            xs_ = [p[1] for p in sel]; zs_ = [p[2] for p in sel]
            x0, x1, z0, z1 = min(xs_) - a.pad, max(xs_) + a.pad, min(zs_) - a.pad, max(zs_) + a.pad
        c = T([[x0, z0], [x1, z1], [x0, z1], [x1, z0]]); c0, r0 = c.min(0); c1, r1 = c.max(0); c0, r0, c1, r1 = int(c0), int(r0), int(c1) + 1, int(r1) + 1
        crop = np.asarray(im.crop((c0, r0, c1, r1))).astype(float) / 255.0 * 0.8 + 0.1
        h, w = crop.shape[:2]; sc = max(1.0, 900 / max(w, h))
        fig = plt.figure(figsize=(w * sc / 100, h * sc / 100 + 0.6), dpi=100); ax = fig.add_axes([0, 0.6 / (h * sc / 100 + 0.6), 1, (h * sc / 100) / (h * sc / 100 + 0.6)])
        ax.imshow(crop, extent=(c0, c1, r1, r0))
        for l in G['links']:
            p = T(l['pts']); ax.plot(p[:, 0], p[:, 1], color='#3fd0ff' if not l.get('air') else '#c58cff', lw=0.8, alpha=0.8)
        for ap_ in A['aprons']:
            p = T(ap_['ring'] + [ap_['ring'][0]]); ax.plot(p[:, 0], p[:, 1], color='#7CFC00', lw=0.6, alpha=0.7)
        for o in A['hangars'] + A['buildings']:
            if len(o.get('ring') or []) >= 3: p = T(o['ring'] + [o['ring'][0]]); ax.plot(p[:, 0], p[:, 1], color='w', lw=0.5)
        fx = np.array([[f[1], f[2]] for f in d['fx']]) if d['fx'] else np.zeros((0, 2))
        if len(fx):
            col = ['#ffffff' if f[3] else '#00e5ff' if f[4] else '#ff3030' for f in d['fx']]; q = T(fx); ax.scatter(q[:, 0], q[:, 1], s=9, c=col, zorder=5, lw=0)
        pp = np.array([[p[1], p[2]] for p in d['p']]); q = T(pp)
        cols = ['#ff8a00' if p[4] else '#ffe100' if p[3] else '#ff00ff' for p in d['p']]
        ax.scatter(q[:, 0], q[:, 1], s=4, c=cols, zorder=6, lw=0)
        offp = np.array([[p[1], p[2]] for p in d['p'] if len(p) > 9 and p[9]])
        if len(offp): q2 = T(offp); ax.scatter(q2[:, 0], q2[:, 1], s=14, marker='x', c='#ff0000', zorder=7, lw=0.8)
        ax.set_xlim(c0, c1); ax.set_ylim(r1, r0); ax.axis('off')
        fig.text(0.01, 0.01, f'{a.name} track {i} ({d["type"]}, {d["cls"]}): fixes white=ground flag, cyan=ground (kinematics/contact), red=air; drawn orange=taxi route, yellow=ground, magenta=air, red x=a wheel off pavement; NAIP 2024 (USDA, public domain), OSM ODbL', fontsize=7, color='k')
        out = os.path.join(HWD, 'out', 'traffic', 'plot_%s_%d.png' % (a.name, i)); fig.savefig(out); plt.close(fig); print(out, k[:3] + '...', d['type'], len(gp), 'ground points')

if __name__ == '__main__':
    main()
