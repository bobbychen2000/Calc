"""Read converted aircraft models (data/models/*.sfom, written by tools/convert_models.py) in Python.

load(path) -> dict(head, pos (nv,3) float64 model metres, nrm (nv,3), uv (nv,2), zone (nv,) uint8, idx (nt,3),
                   tri_mat (nt,) material index per triangle, textures [PIL.Image RGBA])
Model frame (tools/convert_models.py): x forward (nose tip 0, aft negative), y up (fuselage centre line 0), z starboard.
"""
import gzip, io, json, struct
import numpy as np
from PIL import Image

ZONE = dict(base=0, fin=1, engine=2, gear=3, gdoor=4, glass=5, light=6, pylon=7, interior=8)


def load(path, textures=True):
    raw = gzip.decompress(open(path, 'rb').read())
    if raw[:4] != b'SFOM': raise ValueError('not an SFOM file: ' + path)
    _v, hl = struct.unpack('<II', raw[4:12]); head = json.loads(raw[12:12 + hl]); B = 12 + hl
    q, o, nv = head['quant'], head['offsets'], head['nv']
    pq = np.frombuffer(raw, dtype=np.uint16, count=nv * 3, offset=B + o['pos']).reshape(-1, 3)
    pos = np.array(q['pmin']) + pq * np.array(q['pscale'])
    nq = np.frombuffer(raw, dtype=np.int8, count=nv * 4, offset=B + o['nrm']).reshape(-1, 4)[:, :3] / 127.0
    uq = np.frombuffer(raw, dtype=np.uint16, count=nv * 2, offset=B + o['uv']).reshape(-1, 2)
    uv = np.array(q['umin']) + uq * np.array(q['uscale'])
    zone = np.frombuffer(raw, dtype=np.uint8, count=nv, offset=B + o['zone']).copy()
    idx = np.frombuffer(raw, dtype=np.uint16 if head['idxType'] == 'u16' else np.uint32, count=head['ni'], offset=B + o['idx']).reshape(-1, 3).astype(np.int64)
    tri_mat = np.zeros(len(idx), np.int32)
    for d in head['draws']:
        tri_mat[d['first'] // 3:(d['first'] + d['count']) // 3] = d['mat']
    tex = []
    if textures:
        for t in head['textures']:
            tex.append(Image.open(io.BytesIO(raw[B + t['offset']:B + t['offset'] + t['length']])).convert('RGBA'))
    return dict(head=head, pos=pos, nrm=nq, uv=uv, zone=zone, idx=idx, tri_mat=tri_mat, textures=tex, raw=raw, B=B)
