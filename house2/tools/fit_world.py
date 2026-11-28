"""Fit a photo's camera directly on model points: pixel <-> world pairs read off the built model.

    python3 -I tools/fit_world.py            # solves every image of survey/pairs_world.json -> survey/cams_world.json
    python3 -I tools/fit_world.py PAIRS.json OUT.json    # the same for another pairs file (e.g. survey/photo_cams/p26.pairs.json)

survey/pairs_world.json: {image: {"pairs": [[u, v, X, Y, Z], ...], "free": ["f"]}}.  These cameras take precedence
over the SfM / landmark ones (model/frame.py world_cams): they are meant for photographs that the photo layer casts
onto the model, where agreement with the MODEL matters more than agreement with the other cameras."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import cams as C  # noqa: E402
from PIL import Image  # noqa: E402


def main(pairs=None, dst=None):
    pairs = pairs or os.path.join(HERE, 'survey', 'pairs_world.json')
    dst = dst or os.path.join(HERE, 'survey', 'cams_world.json')
    src = json.load(open(pairs))
    out = {}
    for name, e in src.items():
        w, h = Image.open(os.path.join(HERE, 'refs', 'cache', name)).size
        P = np.array([[p[2], p[3], p[4], p[0], p[1]] for p in e['pairs']], float)
        cam, rms = C.fit(P, w, h, free=tuple(e.get('free', ['f'])))
        r = C.project(cam, P[:, :3]) - P[:, 3:]
        print('%s  rms %.1f px  %s' % (name, rms, C.describe(cam)))
        for p, d in zip(e['pairs'], r):
            if np.hypot(*d) > 2.5 * max(rms, 1.0):
                print('   outlier %s  %.0f px' % (p, np.hypot(*d)))
        out[name] = dict(w=w, h=h, f=float(cam['f']), cx=float(cam['cx']), cy=float(cam['cy']), k1=float(cam.get('k1', 0.0) or 0.0),
                         R=np.round(cam['R'], 8).tolist(), C=np.round(cam['C'], 4).tolist(), rms=round(rms, 2))
    json.dump(out, open(dst, 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:3])
