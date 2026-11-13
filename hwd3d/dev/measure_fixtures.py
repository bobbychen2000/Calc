#!/usr/bin/env python3
"""Locates the visual glide slope light units (VASI 10R / 28L, PAPI 10L / 28R) on NAIP 2024 (P2, Phase 2).

FAA NASR gives the type, side, glide angle and TCH of each system (VGSI_CODE V4R / V4L / P4L, VGSI_ANGLE, TCH) but no
position (data/hwd_airport.json runways[].vgsi.position = null). The units are visible on the committed NAIP 2024
mosaic (refs/cache/naip/naip_2024_hwd_rgb.jpg, USDA, public domain, 0.6 m pixels; flight 2024-05-20): VASI boxes with
red / white lenses on concrete pads, PAPI units as a row of 4 squares on one pad. Each search window below was found by
eye on 0.3 m resamplings of strips beside the runways (docs/phase2_world.md section 5); inside it, the units are the
connected blobs of a local top-hat (redness R - G for VASI with a 2.5 m background window; brightness for the 28R PAPI
unit tops with a 1.6 m window; 0.1 m resampling) and each blob's weighted centroid is its position; the 10L PAPI units
(large bright squares filling their pad) are the 4 maxima of the brightness profile across the runway on the pad axis. Positions are reported in runway coordinates (along from the
end's threshold, across from the centreline, + = right of a pilot landing on that end) and in world (x, z).

Writes js/world/fixtures_naip.json (consumed by js/live/lights.js) and out/phase2/fix_<id>.png (each window with the
detected centroids, for a visual check). Accuracy: NAIP pixel 0.6 m; centroids +-0.5 m [inf].

usage (from hwd3d/): python3 dev/measure_fixtures.py
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'imagery')); sys.path.insert(0, os.path.join(ROOT, 'tools', 'common'))
from common import NaipSampler  # noqa: E402
import hwd_frame as F  # noqa: E402

FT = 0.3048
OPP = {'10L': '28R', '28R': '10L', '10R': '28L', '28L': '10R'}


def xz(lat, lon):
    w = F.ll_to_world(lat, lon); return np.array([w[0], w[1]])


def frame(e):
    E = F.RWY_ENDS[e]; a = xz(E['lat'], E['lon']); b = xz(F.RWY_ENDS[OPP[e]]['lat'], F.RWY_ENDS[OPP[e]]['lon'])
    d = (b - a) / np.linalg.norm(b - a); r = np.array([-d[1], d[0]])
    t = xz(E['thrLat'], E['thrLon']) if E.get('thrLat') is not None else a
    return t, d, r


# search windows (runway coordinates of `end`, m: along from the threshold, across from the centreline, + = right)
WINDOWS = [
    # id, end, system, along0, along1, across0, across1, channel, expected units
    ('vasi_10R_downwind', '10R', 'VASI V4R', 25, 47, 33, 50, 'red', 2),
    ('vasi_10R_upwind', '10R', 'VASI V4R', 237, 259, 33, 50, 'red', 2),
    ('vasi_28L_downwind', '28L', 'VASI V4L', 80, 103, -50, -33, 'red', 2),
    ('vasi_28L_upwind', '28L', 'VASI V4L', 231, 254, -50, -33, 'red', 2),
    ('papi_10L', '10L', 'PAPI P4L', 179, 193, -48, -14, 'bright', 4),
    ('papi_28R', '28R', 'PAPI P4L', 273, 287, -62, -14, 'dot', 4),
]


def main():
    N = NaipSampler('2024', prefer='jpg')
    res = 0.1; out = {'source': 'NAIP 2024 (USDA, public domain) refs/cache/naip/naip_2024_hwd_rgb.jpg, flight 2024-05-20',
                      'made_by': 'hwd3d/dev/measure_fixtures.py', 'accuracy_m': 1.0, 'accuracy_note': 'VASI red-lens blobs +-0.5 m; PAPI units +-1 m (10L squares merge on a 0.6 m image)', 'units': []}
    for wid, end, system, a0, a1, c0, c1, chan, nexp in WINDOWS:
        t, d, r = frame(end)
        A = np.arange(a0, a1, res); C = np.arange(c0, c1, res); AA, CC = np.meshgrid(A, C)
        P = t[None, None, :] + d[None, None, :] * AA[..., None] + r[None, None, :] * CC[..., None]
        rgb = np.stack([N.sample_world(P[..., 0], P[..., 1], band=k) for k in range(3)], -1)
        g = rgb.mean(-1)
        v = (rgb[..., 0] - rgb[..., 1]) if chan == 'red' else g
        bg = ndi.median_filter(v, size=int((1.6 if chan == 'dot' else 2.5) / res))
        th = v - bg
        blobs = []
        if chan in ('red', 'dot'):
            # VASI: red-lens blobs of the local top-hat; 28R PAPI: the bright unit tops (small dots on a grey pad)
            thr = max(6.0, np.percentile(th, 99.0) * 0.45)
            lab, n = ndi.label(th > thr)
            for k in range(1, n + 1):
                m = lab == k; area = m.sum() * res * res
                if area < 0.15: continue
                w = th * m; sa = (w * AA).sum() / w.sum(); sc = (w * CC).sum() / w.sum()
                blobs.append({'along': sa, 'across': sc, 'area_m2': area, 'peak': float(th[m].max())})
            blobs.sort(key=lambda b: -b['peak'] * b['area_m2'])
            if chan == 'dot':   # PAPI units: >= 5 m apart across the runway (FAA spacing 20-30 ft)
                sel = []
                for b in blobs:
                    if all(abs(b['across'] - q['across']) >= 5.0 for q in sel): sel.append(b)
                blobs = sel
        else:
            # PAPI: the 4 units sit in a row across the runway on one pad. The pad's along position is the centroid of
            # the brightness excess over the window median; the units are the 4 strongest maxima (>= 5 m apart) of the
            # brightness profile across the runway, averaged over +-0.9 m along the pad axis.
            ex = np.clip(g - np.median(g), 0, None); pa = (ex * AA).sum() / ex.sum()
            band = np.abs(A - pa) <= 0.9
            pr = ndi.gaussian_filter1d(g[:, band].mean(1), 3)
            pk = [i for i in range(1, len(pr) - 1) if pr[i] >= pr[i - 1] and pr[i] >= pr[i + 1]]
            pk.sort(key=lambda i: -pr[i]); sel = []
            for i in pk:
                if all(abs(C[i] - C[j]) >= 5.0 for j in sel): sel.append(i)
                if len(sel) == nexp: break
            for i in sel:
                # refine the along position of the unit: centroid of the excess within +-1 m across of it
                rows = np.abs(C - C[i]) <= 1.0; e2 = ex[rows][:, np.abs(A - pa) <= 2.0]; a2 = A[np.abs(A - pa) <= 2.0]
                sa = float((e2.sum(0) * a2).sum() / max(1e-6, e2.sum())) if e2.sum() > 0 else pa
                blobs.append({'along': sa, 'across': float(C[i]), 'area_m2': 0.0, 'peak': float(pr[i])})
        keep = sorted(blobs[:nexp], key=lambda b: abs(b['across']))
        im = Image.fromarray(np.clip((rgb - rgb.min()) / (np.ptp(rgb) + 1e-6) * 255, 0, 255).astype(np.uint8)).resize((len(A) * 3, len(C) * 3), Image.NEAREST)
        dr = ImageDraw.Draw(im)
        for i, b in enumerate(keep):
            x = (b['along'] - a0) / res * 3; y = (b['across'] - c0) / res * 3
            dr.line([(x - 8, y), (x + 8, y)], fill=(0, 255, 255), width=1); dr.line([(x, y - 8), (x, y + 8)], fill=(0, 255, 255), width=1)
            dr.text((x + 6, y + 4), str(i + 1), fill=(0, 255, 255))
            wxz = t + d * b['along'] + r * b['across']
            out['units'].append({'id': f'{wid}_{i + 1}', 'system': system, 'end': end, 'group': wid,
                                 'along_thr_m': round(b['along'], 2), 'across_m': round(b['across'], 2),
                                 'x': round(float(wxz[0]), 2), 'z': round(float(wxz[1]), 2),
                                 'blob_area_m2': round(b['area_m2'], 2), 'src': 'obs'})
        dr.text((3, 3), f'{wid} ({system}) along {a0}-{a1} m from the {end} threshold, across {c0}..{c1} m; {chan}', fill=(255, 255, 0))
        im.save(os.path.join(ROOT, 'out', 'phase2', f'fix_{wid}.png'))
        print(wid, len(blobs), 'blobs ->', [(round(b['along'], 1), round(b['across'], 1), round(b['area_m2'], 2)) for b in keep])
    fn = os.path.join(ROOT, 'js', 'world', 'fixtures_naip.json')
    json.dump(out, open(fn, 'w'), indent=1); print('->', fn)
    js = os.path.join(ROOT, 'js', 'world', 'fixtures_naip.js')
    with open(js, 'w') as f:
        f.write('// GENERATED by hwd3d/dev/measure_fixtures.py from NAIP 2024 (USDA, public domain) - do not edit.\n'
                '// VASI / PAPI light-unit positions measured on refs/cache/naip/naip_2024_hwd_rgb.jpg (docs/phase2_world.md section 5).\n')
        f.write('export const FIXTURES_NAIP = ' + json.dumps(out, indent=1) + ';\n')
    print('->', js)


if __name__ == '__main__':
    main()
