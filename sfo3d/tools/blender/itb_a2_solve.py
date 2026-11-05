"""Camera of photo a2 (Commons "Aerial view of San Francisco International Airport station, September 2025", Pi.1415926535,
CC BY-SA 4.0; refs/cache/buildings/review_likeness/a2.jpg, 1920 x 1280, REFERENCE ONLY) solved from image <-> world
correspondences, for render_itb.view_a2g (review r1, 2026-11-05).

    python3 tools/blender/itb_a2_solve.py      -> prints the camera; out/buildings3d/itb_a2_camera.json

Identification (review r1 finding 3): a2 looks SSW over the Boarding Area G NNE face. Behind it the south apron, then Garage G
with the white BART / AirTrain station roof (NAIP x -1553..-1425, z 281..340) and its rounded EAST end (the "drum" at the left
end of the station building in a2: looking SSW, east is on the left), Garage A and the Grand Hyatt further back, the ITB north
roof tip at the left edge. Round 0 had read it as Boarding Area A from the ESE.

Step 1, plan: bearings of five features (ITB NW roof corner, pods G1 / G2 centres, the Garage G rounded east end, the Hyatt
centre) -> camera plan position, heading and focal length (residuals <= 16 px).
Step 2, 3-D: least squares (soft-L1) over x, z, h, azimuth, elevation, roll, f on the BA-G picks (roof edge / base at the
bump-out B1, roof edge at B3, the bump-out edges at their 6.5-m tops, pod ends) + the Hyatt top (44 m, inf).
The BA-G pier frame (s along WNW, t across SSW) is itb_pods.json piers.G; s / t of the picks are the SFO Museum outline vertices.
Pixel picks were read on 2x-4x zooms of a2 (+-3 px for the facade edges, +-10 px for the pod ends).
"""
import json
import os
import sys

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import itb_geom as G  # noqa: E402

P = G.PIERS['G']; C0 = np.array(P['centre_xz']); SA = np.array(P['s_axis']); TA = np.array(P['t_axis'])


def st(s, t, h):
    p = C0 + SA * s + TA * t
    return (float(p[0]), float(p[1]), h)


PICKS = [   # (world x, z (south), h), a2 pixel, label, weight-group
    (st(-69.6, -0.7, 17.0), (372, 864), 'roof edge at bump-out B1 west end'),
    (st(73.2, -0.7, 17.0), (1593, 923), 'roof edge at bump-out B3 east end'),
    (st(-69.6, -0.7, 0.0), (372, 1012), 'facade base at B1 west end'),
    (st(-60.4, 10.6, 22.4), (515, 792), 'pod G1 WNW end, top'),
    (st(66.6, 10.8, 22.2), (1565, 840), 'pod G2 WNW end, top'),
    (st(12.6, 24.8, 22.2), (1105, 820), 'pod G2 ESE end, top'),
    (st(-118.5, 24.5, 22.4), (45, 780), 'pod G1 ESE end, top'),
    (st(-53.8, -9.4, 6.5), (507, 955), 'bump-out B1 front, east edge at its top'),
    (st(88.9, -9.4, 6.5), (1735, 1003), 'bump-out B3 front, west edge at its top'),
    ((-1641.4, 651.3, 44.0), (1140, 215), 'Grand Hyatt centre, top (44 m inf)'),
]
CHECK = [((-1313.1, 254.2, 34.4), (160, 602), 'ITB roof NW corner (tip, 34.4)'),
         ((-1445.0, 344.0, 20.0), (845, 560), 'Garage G rounded east end (plan centre, h ~20 assumed)')]
W, H = 1920, 1280


def proj(q, X):
    cx, cz, ch, az, el, roll, f = q
    a, e, r = np.radians(az), np.radians(el), np.radians(roll)
    fwd = np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])      # (x, z south, h)
    right = np.array([np.cos(a), np.sin(a), 0.0])
    up = np.cross(fwd, right)
    right, up = right * np.cos(r) + up * np.sin(r), up * np.cos(r) - right * np.sin(r)
    d = np.asarray(X, float) - np.array([cx, cz, ch])
    zc = d @ fwd
    return np.stack([W / 2 + f * (d @ right) / zc, H / 2 - f * (d @ up) / zc], 1)


def solve():
    # step 1: plan bearings
    obs = [((-1313.1, 254.2), 160), ((-1301.0, 163.0), 280), ((-1414.0, 103.0), 1330), ((-1445.0, 344.0), 845), ((-1641.4, 651.3), 1140)]

    def rb(q):
        cx, cz, a0, f = q
        return [W / 2 + f * np.tan(np.arctan2(x - cx, -(z - cz)) - np.radians(a0)) - u for (x, z), u in obs]
    best = None
    for cx in np.arange(-2000, 500, 250):
        for cz in np.arange(-4000, 0, 250):
            a0 = np.degrees(np.arctan2(-1400 - cx, -(300 - cz)))
            for f in (3000, 8000, 15000):
                s = least_squares(rb, [cx, cz, a0, f])
                if 500 < s.x[3] < 60000 and (best is None or s.cost < best.cost): best = s
    cx, cz, a0, f = best.x
    # step 2: full camera
    X = np.array([p[0] for p in PICKS]); I = np.array([p[1] for p in PICKS], float)
    res = lambda q: (proj(q, X) - I).ravel()  # noqa: E731
    best2 = None
    for ch in (60, 95, 150, 250):
        el = -np.degrees(np.arctan2(ch, np.hypot(-1400 - cx, 150 - cz)))
        r = least_squares(res, [cx, cz, ch, a0, el, 0.0, f], loss='soft_l1', f_scale=5)
        if best2 is None or r.cost < best2.cost: best2 = r
    return best.x, best.fun, best2.x


if __name__ == '__main__':
    plan, plan_res, q = solve()
    print('plan: cam x %.1f z %.1f heading %.2f f %.0f px; bearing residuals %s px' % (*plan, np.round(plan_res, 1).tolist()))
    print('3-D : cam x %.1f z %.1f h %.1f az %.2f el %.2f roll %.2f f %.0f px (%.1f mm on 36 mm)' % (*q[:6], q[6], q[6] / W * 36))
    rows = []
    for (X, px, n) in PICKS + CHECK:
        pr = proj(q, [X])[0]
        rows.append(dict(label=n, world_xzh=list(X), photo_px=list(px), model_px=[round(float(pr[0]), 1), round(float(pr[1]), 1)],
                         err_px=round(float(np.hypot(*(pr - np.array(px)))), 1), used=(X, px, n) in PICKS))
        print('  %-52s photo %-12s model (%.0f, %.0f)  %s' % (n, px, pr[0], pr[1], '' if (X, px, n) in PICKS else '(check)'))
    out = os.path.join(G.ROOT, 'out', 'buildings3d', 'itb_a2_camera.json')
    json.dump(dict(photo='refs/cache/buildings/review_likeness/a2.jpg (1920 x 1280)', camera=dict(
        x=round(float(q[0]), 1), z=round(float(q[1]), 1), h=round(float(q[2]), 1), az=round(float(q[3]), 2), el=round(float(q[4]), 2),
        roll=round(float(q[5]), 2), f_px=round(float(q[6]), 0)), plan_step=dict(x=float(plan[0]), z=float(plan[1]), heading=float(plan[2]),
        f_px=float(plan[3]), residuals_px=np.round(plan_res, 1).tolist()), picks=rows), open(out, 'w'), indent=1)
    print('->', out)
