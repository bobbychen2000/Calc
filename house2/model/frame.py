"""World frame: metres, X right along the street, Y into the lot, Z up (see survey/frame.json for the origin).

The reference cameras are solved in the SfM frame S (tools/register.py); to_world() converts cameras and points.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME = json.load(open(os.path.join(HERE, 'survey', 'frame.json')))


def _rz():
    a = np.radians(FRAME['yaw_deg'])
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def to_world(P):
    P = np.asarray(P, float)
    return FRAME['scale'] * (P - np.array(FRAME['origin_S'])) @ _rz().T


def to_S(P):
    P = np.asarray(P, float)
    return (P / FRAME['scale']) @ _rz() + np.array(FRAME['origin_S'])


def cam_to_world(cam):
    c = dict(cam)
    c['C'] = to_world(cam['C'])
    c['R'] = np.asarray(cam['R'], float) @ _rz().T
    return c


def world_cams():
    """All registered cameras (refs/cache/cams_S.json, else the SfM frames alone) in world metres."""
    import sys
    sys.path.insert(0, HERE)
    from tools import cams as CAMS
    p = os.path.join(HERE, 'refs', 'cache', 'cams_S.json')
    if not os.path.exists(p):
        p = os.path.join(HERE, 'refs', 'cache', 'cams_sfm.json')
    out = {k: cam_to_world(c) for k, c in CAMS.load(p).items()}
    fixed = os.path.join(HERE, 'refs', 'cache', 'cams_fixed.json')     # photos registered later (tools/lg_reg.py --save)
    for k, c in CAMS.load(fixed).items():
        out[k] = cam_to_world(c)
    extra = os.path.join(HERE, 'survey', 'cams_world.json')          # cameras fitted on the model itself (tools/fit_world.py)
    if os.path.exists(extra):
        for k, c in json.load(open(extra)).items():
            out[k] = dict(c, R=np.array(c['R'], float), C=np.array(c['C'], float))
    return out
