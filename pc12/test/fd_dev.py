"""Flight-deck development loop (first-principles flight deck): a dev GLB with the interior rebuilt from the current
code over a pickled base build, so a look / builder change is in the viewer in minutes instead of a full build.

    python3 test/fd_dev.py --save            # build every part once (refined, no bake) -> out/tmp/fp/parts_base.pkl
    python3 test/fd_dev.py [--out out/tmp/fp/dev.glb] [--no-ao]
                                             # the base parts + the interior rebuilt, refined and baked -> a GLB
                                             # (view it: test/fd_cap.py DIR --glb ../out/tmp/fp/dev.glb)

The dev GLB is NOT the shipped model: model/build.py builds that (both tiers, every check)."""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "model"))
BASE = ROOT / "out" / "tmp" / "fp" / "parts_base.pkl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "out" / "tmp" / "fp" / "dev.glb"))
    ap.add_argument("--no-ao", action="store_true")
    a = ap.parse_args()
    from model import build as B
    from cad import res
    t0 = time.time()
    PRE = BASE.with_name("parts_pre.pkl")
    if a.save:
        pre = {}
        B.interior.build_structure(pre)
        for mod in (B.fuselage_parts, B.wing, B.empennage, B.powerplant, B.gear):
            mod.build(pre)
        with open(PRE, "wb") as f:
            pickle.dump(pre, f, protocol=pickle.HIGHEST_PROTOCOL)
        parts = B.build_parts(ao=False)
        BASE.parent.mkdir(parents=True, exist_ok=True)
        with open(BASE, "wb") as f:
            pickle.dump(parts, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"saved {len(parts)} parts -> {BASE} ({time.time() - t0:.0f} s)")
        return
    from model import interior
    from model.assemble import write_glb
    with open(BASE, "rb") as f:
        parts = pickle.load(f)
    with open(PRE, "rb") as f:
        pre = pickle.load(f)
    had = set(pre)
    interior.build_interior(pre)                  # the interior parts from the current code (the doors' cabin-side
    new = {k: v for k, v in pre.items() if k not in had}     # pieces stay the base build's: track 1's)
    fine = B._low_fine(new)
    for pid, p in new.items():
        if pid in fine:
            with res.override(B.LOW_FINE_RES):
                res.refine_part(pid, p)
        else:
            res.refine_part(pid, p)
    parts.update(new)
    print(f"interior rebuilt + refined ({time.time() - t0:.0f} s)", flush=True)
    if not a.no_ao:
        B.bake_interior_ao(parts)
        print(f"baked ({time.time() - t0:.0f} s)", flush=True)
    order = {k: i for i, (k, *_) in enumerate(B.STEPS)}
    parts = {k: parts[k] for k in sorted(parts, key=lambda k: order.get(parts[k].step, 99))}
    size, stats = write_glb(parts, a.out, meta=B.glb_meta())
    print(f"{a.out}: {stats['triangles']:,} triangles, {size / 1e6:.1f} MB ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
