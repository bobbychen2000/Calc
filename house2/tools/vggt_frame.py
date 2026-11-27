"""World frame of the second house from its VGGT run (no SfM here: the property video could not be fetched).

    python3 -I tools/vggt_frame.py [SCALE_M_PER_UNIT]

Up = the normal of the ground plane fitted to the aerial's (p29) farthest points (lawns, drive, patio); +Y = the aerial
image's "up" direction laid on the ground (into the lot, away from the street at the image bottom), +X = image right;
origin = the ground plane under the aerial camera; metres = VGGT units x SCALE (survey/frame.json 'scale').
Writes survey/frame_vggt.json (superseded by the SfM frame: survey/frame.json), refs/cache/cams_world_vggt.json (every photo's camera in world metres, original pixels),
refs/cache/aerial_points.npz (the aerial's per-pixel points in world metres, original-pixel coordinates u, v).
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, 'refs', 'cache')
AERIAL = 'photos/p29_ddf5dc.jpg'


def main():
    old = json.load(open(os.path.join(HERE, 'survey', 'frame_vggt.json'))) if os.path.exists(os.path.join(HERE, 'survey', 'frame_vggt.json')) else {}
    scale = float(sys.argv[1]) if len(sys.argv) > 1 else float(old.get('scale', 50.0))
    d = np.load(os.path.join(CACHE, 'vggt', 'run1.npz'), allow_pickle=True)
    names = [str(n) for n in d['names']]
    ia = names.index(AERIAL)
    E, K, pad = d['extrinsic'], d['intrinsic'], d['pad']
    Rv = E[:, :, :3]
    Cv = np.einsum('nji,nj->ni', Rv, -E[:, :, 3])
    # ground plane of the aerial
    P = d['world_points'][ia].reshape(-1, 3)
    dep = d['depth'][ia].reshape(-1)
    w, h, nw, nh, left, top = [float(v) for v in pad[ia]]
    uu, vv = np.meshgrid(np.arange(518), np.arange(518))
    inside = ((uu >= left) & (uu < left + nw) & (vv >= top) & (vv < top + nh)).reshape(-1)
    Q = P[inside & (dep > np.percentile(dep[inside], 60))]
    for _ in range(6):
        c = Q.mean(0)
        _, _, Vt = np.linalg.svd(Q - c, full_matrices=False)
        n = Vt[2]
        r = (Q - c) @ n
        Q = Q[np.abs(r) < 2.5 * np.std(r)]
    if n @ Rv[ia][2] > 0:
        n = -n
    g0 = Q.mean(0)
    # axes: +Y = the aerial's image-up on the ground, +X = image right
    y = -Rv[ia][1]
    y = y - (y @ n) * n
    y /= np.linalg.norm(y)
    x = np.cross(y, n)
    R = np.stack([x, y, n])                          # VGGT -> world rotation (rows = world axes in VGGT coords)
    ca = Cv[ia]
    o = ca - ((ca - g0) @ n) * n                     # ground point under the aerial camera
    to_w = lambda p: (np.asarray(p) - o) @ R.T * scale          # noqa: E731
    frame = dict(scale=scale, R=R.tolist(), origin_vggt=o.tolist(), up_vggt=n.tolist(),
                 note='world = (p_vggt - origin_vggt) @ R.T * scale; X image-right, Y image-up of the aerial, Z up')
    json.dump(frame, open(os.path.join(HERE, 'survey', 'frame_vggt.json'), 'w'), indent=1)
    cams = {}
    for i, nm in enumerate(names):
        w, h, nw, nh, left, top = [float(v) for v in pad[i]]
        f = float(K[i, 0, 0] * w / nw)
        Rw = Rv[i] @ R.T                             # world -> camera
        cams[nm] = dict(w=int(w), h=int(h), f=f, cx=w / 2, cy=h / 2, k1=0.0, R=np.round(Rw, 8).tolist(),
                        C=np.round(to_w(Cv[i]), 4).tolist(), src='vggt run1')
    json.dump(cams, open(os.path.join(CACHE, 'cams_world_vggt.json'), 'w'), indent=1)
    # the aerial's points with their original-pixel coordinates
    w, h, nw, nh, left, top = [float(v) for v in pad[ia]]
    sel = inside.reshape(518, 518)
    u = (uu[sel] - left + 0.5) * w / nw
    v = (vv[sel] - top + 0.5) * h / nh
    Pw = to_w(d['world_points'][ia][sel])
    np.savez_compressed(os.path.join(CACHE, 'aerial_points.npz'), u=u, v=v, P=Pw.astype(np.float32))
    print('scale %.2f m/unit; aerial camera at %s, f %.0f px' % (scale, np.round(cams[AERIAL]['C'], 2), cams[AERIAL]['f']))
    for nm, c in cams.items():
        fwd = np.array(c['R'])[2]
        print('  %-24s C=%s  heading %6.1f  pitch %6.1f' % (nm.split('/')[-1], np.round(c['C'], 2),
              np.degrees(np.arctan2(fwd[0], fwd[1])), np.degrees(np.arcsin(fwd[2]))))


if __name__ == '__main__':
    main()
