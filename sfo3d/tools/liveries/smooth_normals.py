#!/usr/bin/env python3
"""Patch the smoothed forward-fuselage normals (common.NORMAL_SMOOTH / common.smooth_normals) into converted models in
place (the normal block of the .sfom; nothing else changes). tools/liveries/atlas.py applies the same smoothing when it
rebuilds a model, so this is only needed for models that are not re-atlased.

Usage: python3 tools/liveries/smooth_normals.py [keys]   (default: every key in common.NORMAL_SMOOTH)"""
import gzip, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, sfom

for key in sys.argv[1:] or list(common.NORMAL_SMOOTH):
    path = os.path.join(common.MD, key + '.sfom'); m = sfom.load(path, textures=False)
    raw = bytearray(m['raw']); B = m['B']; o = m['head']['offsets']['nrm']; nv = m['head']['nv']
    N, n = common.smooth_normals(m['pos'], m['nrm'], m['zone'], common.NORMAL_SMOOTH[key])
    nq = np.frombuffer(bytes(raw[B + o:B + o + nv * 4]), np.int8).reshape(-1, 4).copy()
    nq[:, :3] = np.round(np.clip(N, -1, 1) * 127).astype(np.int8)
    raw[B + o:B + o + nv * 4] = nq.tobytes()
    open(path, 'wb').write(gzip.compress(bytes(raw), 9))
    print(key, 'smoothed', n, 'vertices')
