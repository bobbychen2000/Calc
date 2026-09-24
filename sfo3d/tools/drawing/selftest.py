"""Self-test of the automatic deviation measurement (measure.py): how often does it recover a KNOWN offset?

For a few regions, the Google imagery is resampled into a synthetic georeferenced tile whose content is displaced by a
known vector (and a second tile with zero displacement, to separate resampling noise). The same features are measured
on the original and on the tiles; for every sample the change of the measured offset should equal n . shift.
A sample "recovers" the shift when it is within 0.5 m of that. Per feature class this gives the fraction of automatic
picks that can be trusted - reported next to every deviation table in docs/drawings/report.md.
Tiles are written to out/draw/selftest/ (Google pixels: local only)."""
import json, os, collections
import numpy as np, cv2
from common import scene, OUT
import background, measure

REGIONS = [  # (name, x0, z0, x1, z1): terminal / boarding areas, west airfield, 28L/28R ends, runway 1L/1R area
    ('terminal-D-E', -900, -150, -550, 250), ('boarding-A-G', -1450, -150, -1100, 550),
    ('rwy-28-ends', 1250, 450, 1650, 850), ('rwy-1-ends', -800, 1050, -450, 1400), ('west-field', -1700, -900, -1300, -500)]
SHIFTS = [(0.8, -0.5), (2.0, -1.0)]


def tile(src, name, box, shift, res=0.3):
    d = os.path.join(OUT, 'selftest'); os.makedirs(d, exist_ok=True)
    x0, z0, x1, z1 = box
    img, valid, _ = src.raster(x0, z0, x1, z1, res)
    img[~valid] = 0
    f = f'{name}_{shift[0]:+.1f}_{shift[1]:+.1f}'
    cv2.imwrite(os.path.join(d, f + '.png'), img)
    A = [[1 / res, 0, -(x0 + shift[0]) / res - 0.5], [0, 1 / res, -(z0 + shift[1]) / res - 0.5]]
    json.dump(dict(image=f + '.png', world_to_pixel=A, res_m=res, name=f'self-test tile {f}'), open(os.path.join(d, f + '.json'), 'w'))
    return background.GeoImage(os.path.join(d, f + '.json'))


def run():
    S = scene(); g = background.sources().get('google')
    if g is None: print('  self-test skipped (no Google screenshots)'); return None
    F = measure.build_features(S)
    stats = collections.defaultdict(lambda: collections.Counter())
    for name, *box in REGIONS:
        t0 = tile(g, name, box, (0.0, 0.0)); tiles = [(sh, tile(g, name, box, sh)) for sh in SHIFTS]
        for f in F:
            if f['mode'] == 'disc': continue
            P = f['pts']
            inside = (P[:, 0] > box[0] + 12) & (P[:, 0] < box[2] - 12) & (P[:, 1] > box[1] + 12) & (P[:, 1] < box[3] - 12)
            if inside.sum() < 2: continue
            sub = dict(f, pts=P[inside], nrm=f['nrm'][inside], tan=f['tan'][inside])
            r = measure.measure_feature(sub, g); r0 = measure.measure_feature(sub, t0)
            c = stats[f['cls']]; c['samples'] += int(inside.sum())
            m0 = ~np.isnan(r['off']) & ~np.isnan(r0['off']); c['measured'] += int(m0.sum()); c['stable'] += int((np.abs(r0['off'][m0] - r['off'][m0]) < 0.5).sum())
            for sh, t1 in tiles:
                r1 = measure.measure_feature(sub, t1); exp = sub['nrm'] @ np.array(sh)
                m = m0 & ~np.isnan(r1['off']); key = f'{np.hypot(*sh):.1f}'
                c['n' + key] += int(m.sum()); c['rec' + key] += int((np.abs(r1['off'][m] - r0['off'][m] - exp[m]) < 0.5).sum())
    out = {}
    for k, v in stats.items():
        o = dict(v); o['stable_rate'] = v['stable'] / max(1, v['measured'])
        for sh in SHIFTS:
            key = f'{np.hypot(*sh):.1f}'; o['recovery_' + key] = v['rec' + key] / max(1, v['n' + key])
        out[k] = o
    json.dump(dict(shifts=SHIFTS, regions=REGIONS, select=os.environ.get('MEASURE_SELECT', 'nearest'), classes=out), open(os.path.join(OUT, 'selftest.json'), 'w'), indent=1)
    for k, v in sorted(out.items()):
        print(f'  {k:28s} samples {v["samples"]:5d} measured {v["measured"]:5d}  stable {v["stable_rate"]:.2f}  ' + '  '.join(f'recovered@{np.hypot(*sh):.1f}m {v["recovery_" + f"{np.hypot(*sh):.1f}"]:.2f}' for sh in SHIFTS))
    return out


if __name__ == '__main__':
    run()
