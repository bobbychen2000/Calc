"""Hash every flight-deck mesh (model/flightdeck.build_flightdeck, per group / material: V, F, N, UV bytes) -- the
first-principles flight deck's refactors (A1: fd_detail_a split by area) must leave these byte-identical.
    python3 test/fd_identity.py > hashes.txt   (run on two trees, diff the outputs)"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import flightdeck  # noqa: E402

flightdeck._yokes = lambda acc: None      # the yokes (model/yoke3d.py, its own disk cache) use no fd_detail_a code

for grp, ms in sorted(flightdeck.build_flightdeck(groups=True).items()):
    for m, mat in sorted(ms, key=lambda t: t[1]):
        h = hashlib.sha256()
        for a in (m.V, m.F, m.N, m.UV):
            if a is not None:
                h.update(a.tobytes())
        print(f"{grp:12s} {mat:28s} {len(m.F):7d} {h.hexdigest()[:16]}")
