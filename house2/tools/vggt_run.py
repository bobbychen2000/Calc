"""Run VGGT (CPU) on a list of images -> cameras, depth and point maps (reference geometry).

    python3 -I house/tools/vggt_run.py LIST.txt OUT.npz

LIST.txt: one image path per line (relative to house/refs/cache); the first image is the world frame.
The images are letterboxed into 518 x 518 (the loader's "pad" mode); OUT.npz records the mapping back to the
original pixels (scale, pad_left, pad_top per image).  Global attention over all frames' tokens is evaluated in
row chunks, so ~24 frames fit in ~12 GB of RAM without a GPU.
"""
import os
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

VGGT_DIR = '/home/user/facebookresearch/vggt'
sys.path.insert(0, VGGT_DIR)
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, 'refs', 'cache')

from vggt.models.vggt import VGGT  # noqa: E402
from vggt.utils.load_fn import load_and_preprocess_images  # noqa: E402
from vggt.utils.pose_enc import pose_encoding_to_extri_intri  # noqa: E402

ATTN_BYTES = 1.2e9      # largest attention-weight block held at once


def chunked_sdpa(q, k, v, attn_mask=None, dropout_p=0.0, is_causal=False, scale=None, **kw):
    """F.scaled_dot_product_attention in row chunks (same result, bounded memory)."""
    assert attn_mask is None and not is_causal
    n, d = q.shape[-2], q.shape[-1]
    s = (d ** -0.5) if scale is None else scale
    lead = int(np.prod(q.shape[:-2]))
    rows = max(16, int(ATTN_BYTES / (lead * k.shape[-2] * 4)))
    kt = k.transpose(-2, -1)
    out = torch.empty(q.shape[:-1] + (v.shape[-1],), dtype=q.dtype)
    for i in range(0, n, rows):
        a = (q[..., i:i + rows, :] * s) @ kt
        a = a.softmax(dim=-1)
        out[..., i:i + rows, :] = a @ v
        del a
    return out


def pad_map(path, target=518):
    w, h = Image.open(path).size
    if w >= h:
        nw, nh = target, round(h * (target / w) / 14) * 14
    else:
        nh, nw = target, round(w * (target / h) / 14) * 14
    return dict(w=w, h=h, nw=nw, nh=nh, left=(target - nw) // 2, top=(target - nh) // 2)


def main():
    lst, out = sys.argv[1], sys.argv[2]
    names = [l.strip() for l in open(lst) if l.strip() and not l.startswith('#')]
    paths = [os.path.join(CACHE, n) for n in names]
    torch.set_num_threads(os.cpu_count() or 4)
    F.scaled_dot_product_attention = chunked_sdpa
    t0 = time.time()
    model = VGGT.from_pretrained('facebook/VGGT-1B').eval()
    print('model loaded', round(time.time() - t0), 's', flush=True)
    images = load_and_preprocess_images(paths, mode='pad')
    print('images', tuple(images.shape), flush=True)
    with torch.no_grad():
        pred = model(images)
    print('forward', round(time.time() - t0), 's', flush=True)
    extri, intri = pose_encoding_to_extri_intri(pred['pose_enc'], images.shape[-2:])
    maps = [pad_map(p) for p in paths]
    np.savez_compressed(
        out,
        names=np.array(names),
        extrinsic=extri[0].numpy().astype(np.float64),           # (N, 3, 4) camera-from-world, OpenCV axes
        intrinsic=intri[0].numpy().astype(np.float64),           # (N, 3, 3) in the 518 x 518 letterboxed pixels
        depth=pred['depth'][0, ..., 0].numpy().astype(np.float32),
        depth_conf=pred['depth_conf'][0].numpy().astype(np.float32),
        world_points=pred['world_points'][0].numpy().astype(np.float32),
        world_points_conf=pred['world_points_conf'][0].numpy().astype(np.float32),
        pad=np.array([[m['w'], m['h'], m['nw'], m['nh'], m['left'], m['top']] for m in maps]),
    )
    print('saved', out, round(time.time() - t0), 's', flush=True)


if __name__ == '__main__':
    main()
