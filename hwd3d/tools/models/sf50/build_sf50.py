#!/usr/bin/env python3 -B
"""
Cirrus SF50 Vision Jet -- own parametric model for hwd3d (Phase 3, M1).

    cd hwd3d && python3 -B tools/models/sf50/build_sf50.py      # -> js/aircraft/models/sf50.glb + sf50_meta.json
    python3 -B tools/models/sf50/render_checks.py               # -> docs/phase3/sf50_*.png (ortho + 3/4 views)

Uses the pc12 "loftkit" kernel read-only (pc12/cad, pc12/model/lifting.py, airfoil.py, parts.py): always run with -B
(no __pycache__ in pc12/).  Every dimension is tagged obs / inf in sf50_geom.py and listed with its source in
SF50_FACTS.md.

Frames.  Model axes: x = FS (m aft of the TCDS datum, 89 in ahead of the forward cabin bulkhead), y = butt line
(+ starboard), z = height above the ground with the aircraft static on its gear.  glTF axes (pc12/cad/glb.py to_gl):
X = starboard, Y = up, Z = aft.  The glTF ORIGIN is the model origin: fuselage station 0 (the TCDS datum, 0.900 m
ahead of the nose tip), butt line 0, ground plane.  The main-gear ground contact (js/aircraft/glb.js measures it from
the tyres) is at glTF (0, 0, 5.353) +- 1.707 in X.
"""
from __future__ import annotations
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                     # noqa: E402

import sf50_kernel as K                                # noqa: E402  (sets up the pc12 import path)
import sf50_geom as G                                  # noqa: E402
import sf50_fuselage, sf50_wing, sf50_tail, sf50_nacelle, sf50_gear, sf50_interior   # noqa: E402,E401
from sf50_assemble import write_glb                    # noqa: E402

HWD = HERE.parents[2]
REPO = HWD.parent
# --out-dir=<dir> writes the pair there instead (trial builds under hwd3d/out/, gitignored)
_OUT_DIR = next((Path(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--out-dir=")), HWD / "js/aircraft/models")
OUT_GLB = _OUT_DIR / "sf50.glb"
OUT_META = _OUT_DIR / "sf50_meta.json"


def source_state():
    """Provenance of the build inputs (fix round 2 of Phase 3a): tools/models is not committed, so a commit hash alone
    does not identify the builder. sha256 of every builder source and of the pc12 kernel files it imports, a combined tree
    hash, and whether each set differs from git HEAD (untracked / modified = working tree)."""
    files = sorted(HERE.glob("*.py")) + [REPO / "pc12/cad" / f for f in ("__init__.py", "mesh.py", "glb.py", "sdf2d.py")] + \
        [REPO / "pc12/model" / f for f in ("__init__.py", "lifting.py", "airfoil.py", "parts.py")]
    out, tree = {}, hashlib.sha256()
    for f in sorted(files, key=lambda f: str(f.relative_to(REPO))):   # tree hash over the paths in sorted order
        if not f.exists():
            continue
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        rel = str(f.relative_to(REPO))
        out[rel] = h
        tree.update(f"{rel} {h}\n".encode())

    def git(*a):
        try:
            return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()
        except Exception:
            return None
    st_builder = git("status", "--porcelain", "--", "hwd3d/tools/models/sf50")
    st_pc12 = git("status", "--porcelain", "--", "pc12/cad", "pc12/model")
    tracked = git("ls-files", "--", "hwd3d/tools/models/sf50")
    return {"sources_sha256": out, "sources_tree_sha256": tree.hexdigest(),
            "builder_state": ("working tree (uncommitted: tools/models/sf50 is not in git)" if not tracked else
                              ("working tree (modified since HEAD)" if st_builder else "committed (= HEAD)")),
            "builder_dirty": bool(st_builder) or not tracked, "pc12_kernel_dirty": bool(st_pc12),
            "rebuild": "cd hwd3d && python3 -B tools/models/sf50/build_sf50.py (deterministic: the same sources give the same GLB bytes)"}

STEPS = [
    ("fuselage", "Fuselage", "One-piece carbon shell lofted from four control lines (crown, keel, half-breadth, max-breadth "
     "water line) and a super-ellipse section law; openings cut by signed-distance trims."),
    ("glazing", "Glazing", "Two wrap-around windshield panes with a centre post; door window; starboard egress window; "
     "two further cabin windows per side."),
    ("doors", "Doors", "Clam-shell cabin door (upper half up, lower half down) and the aft baggage door, both on the left."),
    ("wing", "Wing", "Tapered low wing solved from the 18.18 m2 TCDS area and the 11.796 m span; NACA 23015 -> 23012 "
     "[inf]; de-ice boots; tip fairings with nav, strobe and landing lights."),
    ("controls_wing", "Flaps & ailerons", "Single-slotted flaps (15 / 39 deg, TCDS); ailerons UP 15 / DOWN 11.5 deg "
     "(TCDS) with the left trim tab and the right servo tab."),
    ("empennage", "V-tail & ventral fins", "38 deg V-tail, ruddervators (pitch UP 20 / DOWN 15, yaw +-9 deg, TCDS) with "
     "servo / trim tabs; ventral fins carrying the yaw-SAS surfaces."),
    ("powerplant", "Powerplant", "Williams FJ33-5A in the dorsal nacelle: heated inlet lip, fan, exhaust mixer."),
    ("gear", "Landing gear", "Trailing-link mains retract inward with a leg door each; castering nose gear retracts "
     "forward between two doors."),
    ("interior", "Cabin", "Panel, displays, seven seats, lining (seen through the glazing)."),
    ("details", "Systems & details", "Antennas, AOA vane, EVS camera, pitot probes, TKS spray bars, lights."),
]


def build_parts():
    parts = {}
    sf50_fuselage.build(parts)
    sf50_wing.build(parts)
    sf50_tail.build(parts)
    sf50_nacelle.build(parts)
    sf50_gear.build(parts)
    sf50_interior.build(parts)
    sf50_interior.build_details(parts)
    order = {k: i for i, (k, *_) in enumerate(STEPS)}
    ids = sorted(parts.keys(), key=lambda k: order.get(parts[k].step, 99))
    return {k: parts[k] for k in ids}


EXTERNAL_SKIP_STEPS = ("interior",)


def verify(parts):
    ext = [p for p in parts.values() if p.step not in EXTERNAL_SKIP_STEPS]
    V = np.vstack([m.V for p in ext for m, _ in p.meshes])
    vt = np.vstack([m.V for k, p in parts.items() if k.startswith(("vtail_", "ruddervator_")) for m, _ in p.meshes])
    tyres = {}
    for k in ("gear_main_L", "gear_main_R", "gear_nose"):
        T = np.vstack([m.V for m, mat in parts[k].meshes if mat == "tire"])
        lo = T[np.argmin(T[:, 2])]
        tyres[k] = lo
    track = tyres["gear_main_R"][1] - tyres["gear_main_L"][1]
    wb = 0.5 * (tyres["gear_main_R"][0] + tyres["gear_main_L"][0]) - tyres["gear_nose"][0]
    ys = np.linspace(0, G.WING_SEMI_REF, 2001)
    area = 2 * np.trapezoid(G.wing_chord(ys), ys)
    te_root = float(G.wing_x_le(G.Y_FUS) + G.wing_chord(G.Y_FUS) + G.te_fillet(G.Y_FUS))
    eng_len_ok = (G.NAC_X1 - sf50_nacelle.FAN_X) >= G.ENGINE_LEN * 0.80
    C = [
        ("Overall length", G.LENGTH, V[:, 0].max() - V[:, 0].min(), "FAA ACD 30.7 ft / AFM Fig 1-1 / EASA TCDS 9.36 m"),
        ("Wing span (overall)", G.SPAN, V[:, 1].max() - V[:, 1].min(), "FAA ACD 38.7 ft / AFM Fig 1-1 / Cirrus (EASA TCDS: 11.67 m)"),
        ("Overall height (static)", G.HEIGHT, V[:, 2].max(), "FAA ACD 10.9 ft / AFM Fig 1-1 / Cirrus 3.32 m"),
        ("Wing reference area (m^2)", G.WING_AREA, area, "EASA TCDS 18.18 m2 / AFM 195.7 sq ft"),
        ("Main-gear track (tyre contacts)", G.TRACK, track, "AFM Fig 1-1 front view 11.2 ft"),
        ("Wheelbase (tyre contacts)", G.WHEELBASE, wb, "[inf] AFM Fig 1-1 side view, scaled (no published figure)"),
        ("V-tail span, tip to tip", G.VTAIL_SPAN, vt[:, 1].max() - vt[:, 1].min(), "AFM Fig 1-1 top view 14.7 ft"),
        ("Nose -> wing root LE", G.X_WING_LE_ROOT_FROM_NOSE, G.X_LE_FUS - G.X_NOSE, "AFM Fig 1-1 top view 11.1 ft"),
        ("Nose -> wing root TE (fillet)", G.X_WING_TE_ROOT_FROM_NOSE, te_root - G.X_NOSE, "AFM Fig 1-1 top view 18.3 ft"),
        ("Fuselage max width (OML)", 66.8 * G.IN, 2 * float(G.half_w(4.4)), "[inf] AFM Fig 1-2 outline at uniform scale (cabin 61 in + walls)"),
        ("Main tyre diameter", 18.0 * G.IN, G.MAIN_TIRE_D, "AFM 8-26: 18 x 5.5"),
    ]
    out = []
    for name, target, got, src in C:
        out.append({"check": name, "source_value": round(float(target), 4), "model": round(float(got), 4),
                    "delta_mm": round(1000 * (float(got) - float(target)), 1), "source": src})
    out.append({"check": "Engine length fits the nacelle (fan face -> exit >= 0.8 x 42.7 in)", "source_value": round(G.ENGINE_LEN, 4),
                "model": round(G.NAC_X1 - sf50_nacelle.FAN_X, 4), "delta_mm": None, "source": "FAA TCDS E3GL", "ok": bool(eng_len_ok)})
    return out, tyres


def main():
    t0 = time.time()
    parts = build_parts()
    checks, tyres = verify(parts)
    main_contact_x = 0.5 * (tyres["gear_main_L"][0] + tyres["gear_main_R"][0])
    try:
        rev = subprocess.run(["git", "-C", str(HWD), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        rev = None
    frame = {
        "model_axes": "x = FS (m aft of the FAA TCDS A00018CH datum: 89 in ahead of the forward cabin bulkhead), "
                      "y = butt line (+ starboard), z = height above ground, static on the gear",
        "gltf_axes": "X = starboard (model y), Y = up (model z), Z = aft (model x)  (pc12/cad/glb.py to_gl)",
        "gltf_origin": "model origin: FS 0 (TCDS datum, 0.900 m ahead of the nose tip [inf]), butt line 0, ground plane",
        "nose_tip_fs": G.X_NOSE, "tail_end_fs": G.X_TAIL,
        "main_gear_contact_gl": [0.0, 0.0, round(float(main_contact_x), 4)],
        "main_gear_contacts_model": {k: np.round(v, 4).tolist() for k, v in tyres.items()},
        "rest_pose": "gear down and locked, flaps up, surfaces neutral, cabin / baggage doors closed, nose-gear doors CLOSED "
                     "in the geometry (their pivot seq 'down' opens them whenever the gear is down)",
    }
    meta = {"model": "Cirrus SF50 Vision Jet (type-generic, original neutral livery, no registration, no logos)",
            "units": "m", "frame": frame}
    OUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    size, stats, anchors = write_glb(parts, str(OUT_GLB), meta=meta)
    glb_sha = hashlib.sha256(OUT_GLB.read_bytes()).hexdigest()
    bom, pivots = [], []
    for k, p in parts.items():
        info = {kk: vv for kk, vv in p.info.items() if kk != "light_anchors"}
        bom.append({"id": k, "name": p.name, "step": p.step, "group": p.group, "qty": p.qty, "note": p.material_note,
                    "tris": p.tri_count(), "materials": sorted(set(m for _, m in p.meshes)), "parent": p.parent,
                    "info": info})
        if p.pivot:
            pv = {kk: (np.round(np.asarray(vv, float), 5).tolist() if kk in ("origin", "axis", "travel") else vv)
                  for kk, vv in p.pivot.items()}
            pv["origin_gl"] = np.round(K.to_gl(np.asarray(p.pivot["origin"], float)), 5).tolist()
            pv["axis_gl"] = np.round(K.to_gl(np.asarray(p.pivot["axis"], float)), 5).tolist()
            pivots.append({"part": k, "parent": p.parent, **pv})
    meta_out = {
        "_provenance": {"made_by": "hwd3d/tools/models/sf50/build_sf50.py (python3 -B; pc12/cad loftkit kernel, read-only)",
                        "repo_rev": rev, "repo_rev_note": "git HEAD when built; the builder itself is identified by builder_state / sources_tree_sha256",
                        **source_state(), "glb_sha256": glb_sha, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "facts": "hwd3d/tools/models/sf50/SF50_FACTS.md", "doc": "hwd3d/docs/phase3_sf50.md",
                        "licence": "own work (this repository); no third-party geometry or texture"},
        "model": meta["model"],
        "frame": frame,
        "steps": [{"key": k, "title": t, "text": d, "parts": [p for p in parts if parts[p].step == k]} for k, t, d in STEPS],
        "parts": bom,
        "pivots": pivots,
        "pivot_conventions": {
            "angles": "deg unless noted; door 'open' in rad (pc12 convention); right-handed rotation about 'axis' at 'origin'",
            "gear": "retract (deg) about axis; mains inward (about +x model / +Z glTF), nose forward (about +y model / +X glTF)",
            "gear_door": "nose doors: open (deg) with seq 'down' = open whenever the gear is down (AFM Fig 1-1 shows them open)",
            "flap": "rotation about a drop hinge below the lower surface, max 39 deg, settings 0/15/39 (TCDS); travel = 0",
            "aileron": "range [-15 UP, +11.5 DOWN] (TCDS), positive = trailing edge down, sign = side",
            "ruddervator": "kind 'ruddervator': pitchRange [-20 UP, +15 DOWN] (TCDS), side = +1 right / -1 left, yawGain 9 deg "
                           "(TCDS +-9); positive = TE toward the surface's lower (outboard-down) side; right yaw = right TE down, left TE up",
            "tab": "gearing x parent deflection; left aileron tab = trim (gearing 0, +-10 deg TCDS); right aileron servo tab "
                   "gearing -0.5 [inf]; ruddervator tabs gearing -0.4 [inf], range [-7, +18] (TCDS trim UP 7 / DOWN 18; + = TE down)",
            "rudder": "yaw-SAS surfaces on the ventral fins, range +-15 (TCDS 'Yaw SAS'), positive = TE to starboard",
            "door": "cabin door upper half opens up (-100 deg), lower half down (+100 deg), baggage door up; open in rad",
            "spin": "fan about the engine axis (FS +, 4 deg nose-down along the nacelle) [inf]",
        },
        "light_anchors": anchors,
        "light_anchor_note": "node extras light = kind (js/aircraft/glb.js KINDS: navL navR tail strobeL strobeR strobeTail "
                             "landL landR taxi; strobeTail is drawn in phase with the tip strobes); iceLight is kept as an "
                             "anchor, not drawn. The SF50 has no rotating beacons: anti-collision = 3 strobes (AFM Kinds of "
                             "Operation 'Anti-Collision Lights 3').",
        "reg_panels": {k: parts[k].info["reg_panel"] for k in ("reg_panel_L", "reg_panel_R")},
        "checks": checks,
        "stats": {"triangles": stats["triangles"], "vertices": stats["vertices"], "glb_bytes": size, "parts": len(parts)},
        "wing": {"semi_span_ref": G.WING_SEMI_REF, "c_root_bl0": round(float(G.C0), 4),
                 "c_tip_ref": round(float(G.wing_chord(G.WING_SEMI_REF)), 4), "le_sweep_deg": round(float(np.degrees(G.LE_SWEEP)), 2),
                 "dihedral_deg": round(float(np.degrees(G.DIHEDRAL)), 2), "x_le_bl0": round(float(G.X_LE0), 4),
                 "airfoils": "NACA 23015 (root) -> NACA 23012 (tip) [inf]"},
    }
    with open(OUT_META, "w") as f:
        json.dump(meta_out, f, indent=1)
    print(f"parts {len(parts)}  triangles {stats['triangles']:,}  vertices {stats['vertices']:,}  "
          f"GLB {size / 1e6:.2f} MB  ({time.time() - t0:.1f}s)")
    for c in checks:
        d = "" if c["delta_mm"] is None else f"delta {c['delta_mm']:+8.1f} mm"
        print(f"  {c['check']:44s} source {c['source_value']:8.3f}  model {c['model']:8.3f}  {d}")
    print("light anchors:", ", ".join(sorted(anchors)))
    return parts


if __name__ == "__main__":
    main()
