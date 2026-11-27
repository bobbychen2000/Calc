"""World frame of the second house: metres, X = the aerial's image right, Y = its image up (into the lot, away from the
street at the image bottom), Z up; built from the VGGT run by tools/vggt_frame.py (survey/frame.json).  There is no
separate SfM frame here: the landmark solve (tools/register.py) works in world metres directly, so to_world / to_S /
cam_to_world are identities, kept for the tools shared with house/.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = json.load(open(os.path.join(HERE, 'survey', 'frame.json')))


def _rz():
    return np.eye(3)


def to_world(P):
    return np.asarray(P, float)


def to_S(P):
    return np.asarray(P, float)


def cam_to_world(cam):
    return dict(cam)


def world_cams():
    """All cameras in world metres: VGGT's (refs/cache/cams_world_vggt.json), replaced by the landmark solve's
    (refs/cache/cams_S.json) and by survey/cams_world.json where those exist."""
    import sys
    sys.path.insert(0, HERE)
    from tools import cams as CAMS
    out = {}
    for f in ('cams_world_vggt.json', 'cams_S.json'):           # the network's cameras, then the landmark solve's
        p = os.path.join(HERE, 'refs', 'cache', f)
        if os.path.exists(p):
            out.update({k: cam_to_world(c) for k, c in CAMS.load(p).items()})
    extra = os.path.join(HERE, 'survey', 'cams_world.json')          # cameras fitted on the model itself (tools/fit_world.py)
    if os.path.exists(extra):
        for k, c in json.load(open(extra)).items():
            out[k] = dict(c, R=np.array(c['R'], float), C=np.array(c['C'], float))
    return out
