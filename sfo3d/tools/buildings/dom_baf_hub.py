"""Boarding Area F hub: is the SFO Museum octagon the roof outline, and how high is the hub roof edge? [obs, low]

Review finding r1-22 (docs/drawings/buildings/review_backlog.json) asked for the octagonal hub to be drawn from NAIP. BD-01
draws the regular octagon fitted to the SFO Museum level-2 outline (draw_domestic.BAF_HUB_*, residual 0.01 m). This
script checks it against NAIP 2024 (single epoch):

  * every octagon face is searched for the strongest straight NAIP 2024 edge parallel to it (draw_lib.measure_edge, the
    deviation method of the README), at the face's predicted imaged position for heights h = 0..20 m with the BA-F
    two-epoch lean (draw_data.dom_lean('F'): 0.332 m/m east [obs/inf: along-face part assumed east]);
  * the faces where an arm joins the hub (NNE = NE arm, WNW = NW arm, ESE / SSE side = the S connector) are not free roof
    edges; a face is used when its edge is clean (ratio >= 1.5) and it is not an arm junction;
  * least squares on the free faces: imaged offset o_k(h=0) = delta + h * (lean . n_k): delta = uniform offset of the roof
    edge from the octagon (+ = outside), h = roof-edge height. The lean's direction is the main systematic: the run is
    repeated with the ITB frame-model direction (east + 0.34 north per east, draw_data.lean_frame) scaled to the same
    east component.
  * the imaged lantern-ring centre (draw_domestic.BAF_LANTERN_IMG) is compared with the imaged hub centre at the fitted h:
    the remainder is either an eccentric (flat) lantern or a raised one (height = remainder / lean).

Output: tools/buildings/dom_baf_hub.json (numbers only). usage: python3 tools/buildings/dom_baf_hub.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, 'dom_baf_hub.json')
ARM_FACES = {28.0: 'NE arm junction', 118.0: 'S connector side', 298.0: 'NW arm junction'}


def main():
    import draw_data as D
    import draw_domestic as DD
    from draw_lib import measure_edge, unit
    c = DD.BAF_HUB_C; oc = DD.octagon(c, DD.BAF_HUB_APO)
    lvE = D.dom_lean('F')[0]
    fr = D.lean_frame(c, 1.0); lvF = fr * (lvE[0] / fr[0])           # frame-model direction, same east component
    faces = []
    for k in range(8):
        p, q = np.array(oc[k]), np.array(oc[(k + 1) % 8]); n = unit((p + q) / 2 - c)
        hdg = round(float(np.degrees(np.arctan2(n[0], -n[1])) % 360), 1)
        r0 = measure_edge(p, q, n, shift=np.zeros(2), half=9.0)
        r10 = measure_edge(p, q, n, shift=lvE * 10.49, half=9.0)
        free = hdg not in ARM_FACES and r0 and r0['ratio'] >= 1.5
        faces.append(dict(normal_hdg=hdg, o_h0=r0['o'], ratio_h0=r0['ratio'], o_at_10_49=r10['o'], ratio_at_10_49=r10['ratio'],
                          role=ARM_FACES.get(hdg, 'free face'), used=bool(free), n=n.tolist()))
    fits = {}
    for nm, lv in (('east', lvE), ('frame_direction', lvF)):
        U = [f for f in faces if f['used']]
        A = np.array([[1.0, float(np.dot(lv, f['n']))] for f in U]); o = np.array([f['o_h0'] for f in U])
        (delta, h), *_ = np.linalg.lstsq(A, o, rcond=None)
        res = o - A @ np.array([delta, h])
        rms = float(np.sqrt(np.mean(res ** 2)))
        cov = np.linalg.inv(A.T @ A) * (res @ res) / max(1, len(o) - 2)
        ring = np.array(DD.BAF_LANTERN_IMG) - (c + lv * h)            # lantern ring vs imaged hub centre
        fits[nm] = dict(lean_per_m=[round(float(x), 3) for x in lv], delta=round(float(delta), 2), h=round(float(h), 2),
                        h_sd=round(float(np.sqrt(cov[1, 1])), 2), rms=round(rms, 2), faces=[f['normal_hdg'] for f in U],
                        residuals=[round(float(x), 2) for x in res],
                        lantern_offset_from_imaged_hub_centre=[round(float(x), 2) for x in ring],
                        lantern_rise_if_concentric=round(float(np.dot(ring, lv) / np.dot(lv, lv)), 1))
    for f in faces: f.pop('n')
    # 2020 (sun az ~267, |s20| 1.25 m per m, shadows to the E): the dark run E of the ring along the E-W line through its
    # imaged centre = the ring's own E rim + its cast shadow; a ring rising dh above the roof casts (1.25 - k20.x) dh
    # beyond its rim (k20.x ~0.11, the NE arm two-epoch lean) -> an upper bound on the rise
    import dom_common as C
    zc = DD.BAF_LANTERN_IMG[1]
    img, o = C.crop(2020, -1066.0, -1046.0, zc - 3.0, zc + 3.0, res=0.25)
    g = np.median(C.gray(img), 0); xs = o[0] + (np.arange(len(g)) + 0.5) * 0.25
    dark = xs[(g < 150) & (xs > -1062)]
    run = [float(dark.min()), float(dark.max())] if len(dark) else None
    sh = dict(dark_run_x=run, length=round(run[1] - run[0], 2) if run else None, per_m=round(1.25 - 0.107, 3),
              rise_upper_bound=round((run[1] - run[0]) / (1.25 - 0.107), 1) if run else None,
              note='2020 E-W luminance (median over z +-3 m), threshold 150 on a ~175 roof; the run includes the ring '
                   'rim itself, so the rise is at most this (a ~12 m rise would cast ~14 m)')
    rec = dict(ring_2020_shadow=sh,generated_by='tools/buildings/dom_baf_hub.py', date='2026-11-04', image='NAIP 2024 world raster 0.5 m (public domain)',
               hub=dict(centre=[float(x) for x in c], apothem=DD.BAF_HUB_APO, across_flats=round(2 * DD.BAF_HUB_APO, 2)),
               faces=faces, fits=fits,
               reading='the free faces put the roof edge on the SFO Museum octagon (|delta| < 0.5 m) at a height close to the '
                       'NE arm (10.49 m); the lantern ring is NOT where a flat concentric ring would be imaged: it would '
                       'need ~11-12 m of rise to be concentric, but its 2020 cast shadow bounds the rise to <= ~4.6 m, so it '
                       'is eccentric by ~4 m to the E (or the hub is not a regular octagon about that centre) [inf]; the '
                       'rise itself is not measured [unk]')
    json.dump(rec, open(OUT, 'w'), indent=1)
    for f in faces: print(f)
    for k, v in fits.items(): print(k, v)


if __name__ == '__main__':
    main()
