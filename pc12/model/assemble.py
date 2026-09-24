"""Assembly writer: parts -> glTF node tree (with hinge pivots and metadata)."""
from __future__ import annotations
import json
import numpy as np
from cad.glb import GLBBuilder, to_gl
from cad.mesh import Mesh

# PBR palette: name -> (rgba, metallic, roughness, extras)
MATERIALS = {
    "paint_white":   ((0.925, 0.930, 0.925), 0.0, 0.30),
    "paint_belly":   ((0.66, 0.69, 0.71), 0.0, 0.38),
    "paint_accent":  ((0.10, 0.17, 0.27), 0.0, 0.32),
    "paint_stripe":  ((0.72, 0.60, 0.18), 0.2, 0.35),
    "trim_black":    ((0.018, 0.019, 0.022), 0.0, 0.16),
    "glass":         ((0.035, 0.045, 0.055, 0.80), 0.0, 0.03),
    "glass_windshield": ((0.030, 0.042, 0.052, 0.82), 0.0, 0.02),
    "seal":          ((0.035, 0.035, 0.04), 0.0, 0.70),
    "seam":          ((0.16, 0.17, 0.18), 0.0, 0.60),
    "jamb":          ((0.58, 0.60, 0.61), 0.4, 0.45),
    "deice_boot":    ((0.13, 0.135, 0.14), 0.0, 0.75),
    "metal":         ((0.62, 0.64, 0.66), 0.85, 0.35),
    "metal_dark":    ((0.25, 0.26, 0.27), 0.8, 0.45),
    "steel":         ((0.72, 0.73, 0.74), 0.9, 0.25),
    "hot_section":   ((0.55, 0.42, 0.28), 0.85, 0.40),
    "exhaust":       ((0.36, 0.33, 0.31), 0.8, 0.55),
    "titanium":      ((0.60, 0.60, 0.58), 0.8, 0.40),
    "black":         ((0.03, 0.03, 0.035), 0.0, 0.55),
    "prop_blade":    ((0.045, 0.045, 0.05), 0.0, 0.45),
    "prop_tip":      ((0.92, 0.92, 0.90), 0.0, 0.40),
    "erosion":       ((0.70, 0.71, 0.72), 0.9, 0.30),
    "tire":          ((0.045, 0.045, 0.05), 0.0, 0.85),
    "wheel":         ((0.80, 0.81, 0.82), 0.6, 0.35),
    "gear_leg":      ((0.78, 0.79, 0.80), 0.7, 0.30),
    "chrome":        ((0.92, 0.93, 0.94), 1.0, 0.08),
    "zinc_chromate": ((0.62, 0.66, 0.22), 0.0, 0.60),
    "interior_green": ((0.36, 0.42, 0.26), 0.0, 0.65),
    "leather":       ((0.48, 0.42, 0.36), 0.0, 0.55),
    "leather_dark":  ((0.16, 0.15, 0.15), 0.0, 0.55),
    "carpet":        ((0.22, 0.22, 0.24), 0.0, 0.95),
    "lining":        ((0.86, 0.84, 0.80), 0.0, 0.70),
    "wood":          ((0.36, 0.22, 0.13), 0.0, 0.35),
    "panel_black":   ((0.05, 0.05, 0.055), 0.2, 0.40),
    "screen":        ((0.02, 0.05, 0.08), 0.0, 0.10),
    "screen_pfd":    ((0.03, 0.06, 0.10), 0.0, 0.08),
    "screen_mfd":    ((0.03, 0.06, 0.10), 0.0, 0.08),
    "screen_sdu":    ((0.03, 0.06, 0.10), 0.0, 0.08),
    "light_red":     ((0.9, 0.05, 0.05), 0.0, 0.2),
    "light_green":   ((0.05, 0.8, 0.2), 0.0, 0.2),
    "light_white":   ((0.95, 0.95, 0.95), 0.0, 0.1),
    "lens":          ((0.85, 0.87, 0.90, 0.5), 0.0, 0.05),
    "inlet_dark":    ((0.02, 0.02, 0.025), 0.0, 0.9),
    "composite":     ((0.20, 0.21, 0.22), 0.1, 0.55),
}


def write_glb(parts: dict, path: str, quantize=True, meta=None):
    gb = GLBBuilder(quantize=quantize)
    for name, spec in MATERIALS.items():
        rgba, met, rough = spec[:3]
        gb.material(name, rgba, met, rough, double_sided=True)

    ids = list(parts.keys())
    node_of = {}
    origin_of = {}
    children_of = {pid: [] for pid in ids}
    roots = []
    for pid in ids:
        p = parts[pid]
        origin_of[pid] = np.asarray(p.pivot["origin"], float) if p.pivot else np.zeros(3)

    # build nodes bottom-up: first meshes, then part nodes
    def make(pid):
        if pid in node_of:
            return node_of[pid]
        p = parts[pid]
        kids = []
        for k, (m, mat) in enumerate(p.meshes):
            if mat not in gb.mat_index:
                raise KeyError(f"unknown material {mat} in {pid}")
            kids.append(gb.mesh_node(f"{pid}#{k}", m, gb.mat_index[mat], origin=origin_of[pid]))
        for cid in [c for c in ids if parts[c].parent == pid]:
            kids.append(make(cid))
        parent_origin = origin_of[p.parent] if p.parent else np.zeros(3)
        t = to_gl(origin_of[pid] - parent_origin)
        extras = dict(part=pid, name=p.name, step=p.step, group=p.group, qty=p.qty,
                      note=p.material_note, explode=to_gl(np.asarray(p.explode, float)).tolist(),
                      tris=int(p.tri_count()), info=p.info)
        if p.pivot:
            pv = dict(p.pivot)
            pv["origin"] = to_gl(np.asarray(pv["origin"], float)).tolist()
            pv["axis"] = to_gl(np.asarray(pv["axis"], float)).tolist()
            extras["pivot"] = pv
        node_of[pid] = gb.node(pid, translation=t, children=kids, extras=extras)
        return node_of[pid]

    for pid in ids:
        if parts[pid].parent is None:
            roots.append(make(pid))
    root = gb.node("PC-12", children=roots, extras=meta or {})
    size = gb.write(path, [root])
    return size, gb.stats
