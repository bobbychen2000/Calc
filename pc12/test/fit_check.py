"""Interference check: every interior/engine vertex must lie inside the OML (minus a margin)."""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import numpy as np
from model.build import build_parts
from model import fuselage as F
parts = build_parts()
MARGIN = 0.02
bad_any = False
for pid, p in parts.items():
    if p.step not in ("interior",) and not pid.startswith("eng_") and pid not in ("engine_mount",):
        continue
    V = np.vstack([m.V for m, _ in p.meshes])
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    inx = (x > 0.95) & (x < 14.36)
    ylim = np.where(inx, F.side_y(np.clip(x, 0.95, 14.36), z) - MARGIN, 0)
    outside = inx & ((np.abs(y) > ylim) | (z > F.z_top(np.clip(x, .95, 14.36)) - MARGIN) | (z < F.z_bot(np.clip(x, .95, 14.36)) + MARGIN))
    n = int(outside.sum())
    if n:
        bad_any = True
        worst = np.argmax(np.abs(y) - ylim + outside * 0)
        idx = np.nonzero(outside)[0]
        print(f"{pid:18s} {n:6d}/{len(V)} verts outside; x-range {x[idx].min():.2f}-{x[idx].max():.2f}, z-range {z[idx].min():.2f}-{z[idx].max():.2f}")
print("FIT OK" if not bad_any else "FIT FAIL")
