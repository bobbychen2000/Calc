#!/usr/bin/env python3
"""
hwd3d build of the pc12 model with a documented parameter override set (review fix round 2).

pc12/ is read-only for hwd3d (hwd3d/CLAUDE.md).  This script imports pc12's own builders unchanged
(Python run without bytecode, so nothing is written into pc12/), applies the overrides of
OVERRIDES[<set>] to module constants *before* building, and writes the GLB + meta into hwd3d/out/
(gitignored).  tools/models/pc12/import_pc12.mjs --variant=<dir> then copies the result into
js/aircraft/models/ with the provenance (pc12 commit, dirty flag, override set, sha256 of every
pc12 source file used and of this script).

    python3 -B tools/models/pc12/build_pc12_variant.py --set=none   # must reproduce pc12/out/pc12.glb
    python3 -B tools/models/pc12/build_pc12_variant.py --set=fr2    # window / door layout + dihedral
Each override cites what it is measured from; see docs/phase3_models.md section 4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HWD = HERE.parents[2]
REPO = HWD.parent
PC12 = REPO / "pc12"
sys.path.insert(0, str(PC12))

MBP = ("Pilatus 'PC-12 NGX Model Building Plan' "
       "(https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf)")

# --------------------------------------------------------------------------------------------
# Override sets.  Every value: what it replaces, the measurement, the source.  Stations in m aft of
# the pc12 datum (STA), water lines in m above the ground (pc12 model axes).
# --------------------------------------------------------------------------------------------
# Window / door layout (finding F1).  Measured on drawing 190.10.40.432 (MBP p.9), rasterised at
# 200 dpi: side view (seen from port) scale fitted to the 9 labelled frame lines EF1..FR40
# (328.44 px/m, nominal 1:24 = 328.08; residuals <= 0.43 px = 1.3 mm), x from the spinner tip at
# STA 0.39 (pc12's anchor, refs/mbp.py), z from the drawn ground line (the drawing's tail top then
# reads 4.266 m against the published 4.26).  Starboard: MBP p.5 livery sheet (to scale: its port
# windows agree with the drawing to <= 15 mm) -- see CROWN_OFFSET and the notes below.
#   port (drawing side view + p.5 port livery): airstair door centre 4.971 (outline 4.66-5.29, no
#     window), fixed windows 5.607 / 6.201 / 6.980, cargo door centre 8.242 (outline 7.55-8.94) with
#     its window at 7.961.  Window outline 0.295 x 0.380 m (interior 0.289 x 0.374 + line), centre
#     0.583 m below the cabin crown line.
#   starboard: p.5 livery: 5.339, exit window 6.192 (the exit bracketed), 6.967, 7.716, 8.469 [obs,
#     livery]; the drawing's partial starboard view (FR16 to ~STA 8.98) shows 5.602, exit 6.199,
#     6.978, 7.955 (the port stations mirrored) -- conflict recorded, the livery used (it is the only
#     full starboard side and the review's count source).  Exit outline (drawing): 0.48 x 0.64 m,
#     centre 0.569 m below the crown (STA 5.969-6.438).
# The model's cabin crown is 2.630 m; the drawing's 2.768 m (and its keel 0.938 vs 0.800): the
# pc12 cabin section sits 0.138 m low against the drawing while the nose (STA <= 3.0) and the
# propeller axis agree.  The windows / doors are placed relative to the model's crown (as on the
# drawing), not at the drawing's absolute water lines; the loft offset stays a pc12 owner item.
CROWN_MODEL = 2.630
CROWN_DRAWING = 2.768
FR2_LAYOUT = dict(
    WIN_HX=0.1475, WIN_HZ=0.190, WIN_R=0.065,
    WIN_CZ=round(CROWN_MODEL - 0.583, 3),                   # 2.047
    FIXED_WINDOWS={-1: [5.607, 6.201, 6.980], +1: [5.339, 6.967, 7.716, 8.469]},
    AIRSTAIR=dict(side=-1, cx=4.971, cz=1.775, hx=0.305, hz=0.675, r=0.09),   # 0.61 x 1.35 (sourced size)
    CARGO=dict(side=-1, cx=8.242, cz=1.780, hx=0.675, hz=0.660, r=0.10),      # 1.35 x 1.32 (sourced size)
    EXIT=dict(side=+1, cx=6.195, cz=round(CROWN_MODEL - 0.569, 3), hx=0.240, hz=0.320, r=0.07),
    DOOR_WINDOWS={"door_airstair": None, "door_cargo": 7.961, "exit_hatch": 6.195},
)
# Dihedral (finding F2).  Drawing 190.10.40.432 front view (track dimension 4530 -> 328.04 px/m, z from the
# tyre bottoms), port wing outline at BL 2.0-7.5: upper 1.355 ... 1.873, lower 1.105 ... 1.712 m; upper-line
# slope 5.28 deg over BL 3-7 (pc12's 4.5 deg reference plane gives 3.66 deg).  Least-squares fit of the
# reference-plane dihedral to the SHAPE of both outlines (each minus its mean offset): 6.2 deg, rms 6 mm
# (pc12 sections), top line 5.36 deg.  The plane is pivoted about the main-gear butt line (BL 2.265: Z_QC0
# 0.905 -> 0.837) so the gear trunnion, wells and gear-down geometry are unchanged.  The remaining constant
# offset (wing ~0.12 m lower than drawn, the same as the cabin section's 0.138 m) is a pc12 loft item.
FR2_WING = dict(DIHEDRAL_DEG=6.2, PIVOT_BL=2.265)

OVERRIDES = {
    "none": {},
    "fr2": {"layout": FR2_LAYOUT, "wing": FR2_WING},
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()


def source_hashes():
    files = sorted(list((PC12 / "cad").glob("*.py")) + list((PC12 / "model").glob("*.py")))
    tree = hashlib.sha256()
    out = {}
    for f in files:
        h = sha256_file(f)
        out[str(f.relative_to(REPO))] = h
        tree.update(f"{f.relative_to(REPO)} {h}\n".encode())
    return out, tree.hexdigest()


def apply_layout(o):
    from model import fuselage_parts as FP
    for k, v in o.items():
        if k == "DOOR_WINDOWS":
            continue
        setattr(FP, k, v)
    dw = o["DOOR_WINDOWS"]
    FP.DOOR_WINDOWS = dict(dw)
    # build_doors() passes window_cx=DOOR_WINDOWS[...] by key; None = a door without a window.
    # build_glazing() names the cabin-window part "9 fixed" with qty 9: keep its count honest.
    n = sum(len(v) for v in o["FIXED_WINDOWS"].values())
    orig_glazing = FP.build_glazing

    def build_glazing(parts_out):
        orig_glazing(parts_out)
        g = parts_out.get("glazing_cabin")
        if g is not None:
            g.name = f"Cabin windows ({n} fixed, stretched acrylic)"
            g.qty = n
    FP.build_glazing = build_glazing


def apply_wing(o, dihedral_deg):
    import numpy as np
    from model import wing as W
    d0 = W.DIHEDRAL
    d1 = np.radians(dihedral_deg)
    # same reference-plane height at the pivot butt line: Z_QC0 + y tan(D) unchanged at y = PIVOT_BL
    W.Z_QC0 = float(W.Z_QC0 + o["PIVOT_BL"] * (np.tan(d0) - np.tan(d1)))
    W.DIHEDRAL = float(d1)
    return {"DIHEDRAL_deg": [float(np.degrees(d0)), dihedral_deg], "Z_QC0": W.Z_QC0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="fr2", choices=sorted(OVERRIDES))
    ap.add_argument("--dihedral", type=float, default=None, help="reference-plane dihedral, deg (set fr2)")
    ap.add_argument("--out", default=str(HWD / "out" / "pc12_fr2"))
    ap.add_argument("--parts-only", action="store_true", help="build parts, print checks, write nothing")
    a = ap.parse_args()
    ov = OVERRIDES[a.set]
    applied = {}
    if "layout" in ov:
        apply_layout(ov["layout"])
        applied["layout"] = {k: v for k, v in ov["layout"].items()}
    if "wing" in ov:
        dih = a.dihedral if a.dihedral is not None else ov["wing"]["DIHEDRAL_DEG"]
        if dih is not None:
            applied["wing"] = dict(ov["wing"], **apply_wing(ov["wing"], dih))
    from model import build as B
    from model import wing as W
    from model.assemble import write_glb
    t0 = time.time()
    parts = B.build_parts()
    checks = B.verify(parts)
    for c in checks:
        print(f"  {c['check']:44s} official {c['official']:7.3f}  model {c['model']:7.3f}  delta {c['delta_mm']:+7.1f} mm")
    if a.parts_only:
        return
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    size, stats = write_glb(parts, str(out / "pc12.glb"),
                            meta={"model": "Pilatus PC-12 PRO", "units": "m", "datum": "STA 0 = 3.000 m fwd of firewall"})
    ids = list(parts.keys())
    bom = [{"id": k, "name": p.name, "step": p.step, "group": p.group, "qty": p.qty, "note": p.material_note,
            "tris": p.tri_count(), "info": p.info, "materials": sorted(set(m for _, m in p.meshes))}
           for k, p in parts.items()]
    files, tree = source_hashes()
    dirty = git("status", "--porcelain", "--", "pc12/cad", "pc12/model")
    meta = {
        "steps": [{"key": k, "title": t, "text": d, "parts": [p for p in ids if parts[p].step == k]} for k, t, d in B.STEPS],
        "bom": bom, "construction": B.construction(), "checks": checks,
        "stats": {"triangles": stats["triangles"], "vertices": stats["vertices"], "glb_bytes": size, "parts": len(parts)},
        "wing": {"semi_span": W.SEMI, "root_chord": W.C_ROOT, "tip_chord": W.C_TIP, "mac": W.MAC,
                 "lemac": W.LEMAC, "x_qc": W.X_QC, "dihedral_deg": float(__import__('numpy').degrees(W.DIHEDRAL)),
                 "z_qc0": W.Z_QC0},
        "_variant": {
            "set": a.set, "overrides": applied, "builder": "hwd3d/tools/models/pc12/build_pc12_variant.py",
            "builder_sha256": sha256_file(Path(__file__)),
            "pc12_commit": git("rev-parse", "HEAD"), "pc12_sources_dirty": bool(dirty),
            "pc12_sources_tree_sha256": tree, "pc12_sources": files,
            "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seconds": round(time.time() - t0, 1),
        },
    }
    (out / "pc12_meta.json").write_text(json.dumps(meta, separators=(",", ":")))
    print(f"parts {len(parts)}  triangles {stats['triangles']:,}  GLB {size/1e6:.2f} MB  ({time.time()-t0:.1f}s) -> {out}")


if __name__ == "__main__":
    main()
