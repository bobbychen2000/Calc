"""Access to the zone surveys (survey/<zone>.json): elements by id / type, with their measured world outlines."""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(zone):
    p = os.path.join(HERE, 'survey', zone + '.json')
    return json.load(open(p)) if os.path.exists(p) else {'elements': []}


def elements(zone, type=None, has_xyz=False):
    out = []
    for e in load(zone).get('elements', []):
        if type and e.get('type') not in ([type] if isinstance(type, str) else type):
            continue
        xyz = e.get('xyz')
        if has_xyz and not (isinstance(xyz, list) and len(xyz) >= 1 and isinstance(xyz[0], (list, tuple))):
            continue
        out.append(e)
    return out


def xyz(e):
    """The element's measured outline as an (n, 3) array (empty if it has none)."""
    v = e.get('xyz')
    try:
        a = np.asarray(v, float)
        return a.reshape(-1, 3) if a.size and a.shape[-1] == 3 else np.zeros((0, 3))
    except Exception:
        return np.zeros((0, 3))


def text(e):
    return ' '.join(str(e.get(k, '')) for k in ('id', 'desc', 'on')) + ' ' + json.dumps(e.get('attrs', {}))
