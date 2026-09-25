"""
Stage-2 smoke test: the CLEAN drawing set must build without the private reference data.

The public repository never contains refs/cache (Pilatus drawing, photos, camera fits), so every sheet module has
to fall back gracefully when it is missing.  This test disables the registered drawing (refs.mbp.load raises),
points the photo / camera / render caches at an empty directory and builds every registered sheet clean-only
into a temporary directory (the tracked out/drawings/ outputs are not touched).

    python3 test/stage2_noref.py            exit status 0 = every sheet built
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from refs import mbp

    def _no_reference(*_a, **_k):
        raise FileNotFoundError("reference disabled (no-reference smoke test)")

    mbp.load = _no_reference
    from drawing import master as M
    M.mbp_data.cache_clear()
    from drawing import lines_fit
    lines_fit.reference.cache_clear()

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="stage2_noref_"))
    empty = tmp / "empty_cache"
    M.OUT_CLEAN = tmp / "drawings"
    M.OUT_OVERLAY = tmp / "overlays"
    from drawing import livery_profiles as LP, openings_sheet as OS
    LP.CACHE = empty
    LP.LIV_CACHE = empty / "overlays" / "livery"
    OS.RENDER_FILE = empty / "photos" / "cand" / "none.webp"

    failed = []
    for sid, (mod, spec) in M.discover().items():
        try:
            ds, files = M.build_sheet(sid, mod, spec, clean_only=True, dpi=40, verbose=False)
            print(f"[{sid}] ok  ({len(files)} files)  " + "; ".join(m for m in ds.log if "reference" in m)[:160])
        except Exception as e:                  # noqa: BLE001
            traceback.print_exc()
            failed.append(sid)
            print(f"[{sid}] FAILED: {type(e).__name__}: {e}")
    print(f"outputs in {tmp}")
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("all sheets built without the reference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
