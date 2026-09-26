"""Assembly writer: parts -> glTF node tree (with hinge pivots and metadata)."""
from __future__ import annotations
import json
import numpy as np
from cad.glb import GLBBuilder, to_gl
from cad.mesh import Mesh

# PBR palette: name -> (rgba, metallic, roughness[, ext]); ext = glTF PBR extensions (cad/glb.GLBBuilder.material):
# clearcoat / clearcoat_rough (KHR_materials_clearcoat), specular (KHR_materials_specular, F0 scale).
# The exterior finishes are the photo-fitted MSN 3008 values of render/lookdev_materials.json (render/lookdev.py
# SPEC -> glTF: metallic paints carry a LOWER metallic than the Blender flake model because glTF has no F82 tint,
# the clear coat carries the gloss); check_lookdev() compares the two tables.
CC = dict(clearcoat=1.0, clearcoat_rough=0.03)             # automotive / aviation clear coat over the paint
PAINT = dict(CC, specular=0.2)                             # base layer under the lacquer: low dielectric specular
MATERIALS = {
    "paint_white":   ((0.90, 0.905, 0.91), 0.0, 0.30, PAINT),       # gloss white (fin cap, bullet, doors' inner skin)
    "paint_belly":   ((0.62, 0.65, 0.67), 0.0, 0.32, PAINT),
    "paint_accent":  ((0.08, 0.14, 0.24), 0.0, 0.30, PAINT),
    "paint_stripe":  ((0.60, 0.50, 0.16), 0.5, 0.35, PAINT),
    # PRO anti-glare black: the cockpit mask AND the flight-deck glazing frame strips / windshield centre post
    # ('seal' is that frame; photos 130 / 82: frames and mask are one black surround).  Low-reflectance textured
    # finish, no clear coat (photo 82: no crisp LED-strip reflections on it).
    "trim_black":    ((0.010, 0.010, 0.012), 0.0, 0.50, dict(specular=0.16)),
    "seal":          ((0.010, 0.010, 0.012), 0.0, 0.50, dict(specular=0.16)),
    # cabin / cargo-door / exit windows: flush NGX panes with a thin, barely darker glossy edge (photos 130, 0517)
    "seal_cabin":    ((0.05, 0.055, 0.06), 0.0, 0.12),
    # thin glazing (plain glTF: a dark base carrying the reflections, alpha ~ 1 - transmittance)
    "glass":            ((0.02, 0.02, 0.02, 0.35), 0.0, 0.02),    # flight-deck side windows
    "glass_windshield": ((0.02, 0.02, 0.02, 0.30), 0.0, 0.02),    # heated laminated windshield
    "glass_cabin":      ((0.03, 0.035, 0.04, 0.45), 0.0, 0.02),   # two-ply acrylic cabin / door / exit windows
    "seam":          ((0.018, 0.018, 0.020), 0.0, 0.60, dict(specular=0.6)),   # dark door / hatch gap band
    "jamb":          ((0.22, 0.165, 0.085), 0.0, 0.70, dict(specular=0.6)),    # tan / khaki door jambs (photos 188, 82)
    "deice_boot":    ((0.012, 0.012, 0.014), 0.0, 0.25),          # glossy black neoprene, one crisp highlight
    "metal":         ((0.62, 0.64, 0.66), 0.85, 0.35),
    "metal_dark":    ((0.25, 0.26, 0.27), 0.8, 0.45),
    "steel":         ((0.72, 0.73, 0.74), 0.9, 0.25),
    "hot_section":   ((0.55, 0.42, 0.28), 0.85, 0.40),
    "exhaust":       ((0.36, 0.33, 0.31), 0.8, 0.55),
    "exhaust_soot":  ((0.006, 0.006, 0.006), 0.0, 0.60, dict(specular=0.16)),  # heat-blackened stack collar / inside
    "titanium":      ((0.60, 0.60, 0.58), 0.8, 0.40),
    "black":         ((0.028, 0.028, 0.032), 0.0, 0.50),
    "prop_blade":    ((0.015, 0.015, 0.017), 0.0, 0.45, dict(specular=0.5)),   # satin black composite
    "prop_tip":      ((0.80, 0.80, 0.78), 0.0, 0.36),
    "erosion":       ((0.66, 0.64, 0.60), 1.0, 0.22),             # nickel erosion sheath
    "tire":          ((0.028, 0.028, 0.029), 0.0, 0.45),           # black rubber, satin sheen
    "wheel":         ((0.62, 0.63, 0.64), 0.25, 0.35, dict(clearcoat=0.6, clearcoat_rough=0.03, specular=0.2)),
    "gear_leg":      ((0.72, 0.73, 0.74), 0.0, 0.32, dict(clearcoat=0.6, clearcoat_rough=0.03, specular=0.2)),
    "chrome":        ((0.90, 0.91, 0.92), 1.0, 0.035),             # polished spinner, oleo chrome, inlet lip
    "zinc_chromate": ((0.62, 0.66, 0.22), 0.0, 0.60),             # primer: internal structure only
    "gear_bay":      ((0.30, 0.31, 0.32), 0.0, 0.55, dict(specular=0.8)),      # grey wheel-well liners
    "interior_green": ((0.36, 0.42, 0.26), 0.0, 0.65),
    # MSN 3008 interior (photos 130 / 82 / 0517): light neutral-grey leather, mid-grey crew seats
    "leather":       ((0.45, 0.445, 0.435), 0.0, 0.55, dict(specular=0.8)),
    "leather_dark":  ((0.30, 0.295, 0.29), 0.0, 0.55, dict(specular=0.8)),
    "carpet":        ((0.22, 0.22, 0.24), 0.0, 0.95),
    "lining":        ((0.86, 0.84, 0.80), 0.0, 0.70),
    # flight-deck side-wall / headliner lining (interior.build_flightdeck_lining): mid grey, so the windshield and
    # side windows read as dark panes outdoors (photos 188 / 0517) and a lit grey cockpit in the hangar (82)
    "lining_flightdeck": ((0.30, 0.30, 0.295), 0.0, 0.60),
    "wood":          ((0.36, 0.22, 0.13), 0.0, 0.35),
    "panel_black":   ((0.05, 0.05, 0.055), 0.2, 0.40),
    "screen":        ((0.02, 0.05, 0.08), 0.0, 0.10),
    "screen_pfd":    ((0.03, 0.06, 0.10), 0.0, 0.08),
    "screen_mfd":    ((0.03, 0.06, 0.10), 0.0, 0.08),
    "screen_sdu":    ((0.03, 0.06, 0.10), 0.0, 0.08),
    "light_red":     ((0.9, 0.05, 0.05), 0.0, 0.2),
    "light_green":   ((0.05, 0.8, 0.2), 0.0, 0.2),
    "light_white":   ((0.95, 0.95, 0.95), 0.0, 0.1),
    "lens":          ((0.85, 0.87, 0.90, 0.15), 0.0, 0.02),       # clear polycarbonate light lens
    "inlet_dark":    ((0.018, 0.018, 0.022), 0.0, 0.85, dict(specular=0.6)),
    "composite":     ((0.20, 0.21, 0.22), 0.1, 0.55),
    # ---- livery: PC-12 PRO MSN 3008 (N81DW) scheme.  Linear base colours; model/livery.PALETTE holds the same colours
    # as sRGB design colours (livery.check_materials() compares); 'paint_*' + 'trim_black' are primed by the viewer
    # until its paint step, the polished metal and propeller colours are not.
    "paint_blue":       ((0.0066, 0.034, 0.205), 0.30, 0.50, PAINT),   # sRGB #13347D deep metallic blue (base)
    "paint_blue_light": ((0.215, 0.305, 0.55), 0.50, 0.38, PAINT),     # sRGB #8096C4 light metallic (silver-)blue
    "paint_pinstripe":  ((0.90, 0.905, 0.91), 0.0, 0.30, PAINT),       # sRGB #F3F4F5 white pinstripes / swooshes
    "paint_champagne":  ((0.49, 0.41, 0.30), 0.40, 0.38, PAINT),       # sRGB #BAAC95 8 mm pinstripe outlines
    "paint_wing_dark":  ((0.009, 0.018, 0.070), 0.35, 0.42, PAINT),    # sRGB #18244B dark navy wing lower surfaces
    "paint_silver":     ((0.42, 0.42, 0.43), 0.55, 0.36, PAINT),       # sRGB #ADADAF silver-grey tailplane
    "paint_black":      ((0.012, 0.013, 0.015), 0.0, 0.30, dict(CC, specular=0.0)),   # sRGB #1D1E21 gloss radome
    "exhaust_polished": ((0.50, 0.42, 0.30), 1.0, 0.06),               # sRGB #BCAD95 polished, heat-tinted stacks
    "prop_band_red":    ((0.27, 0.026, 0.004), 0.0, 0.40, dict(specular=0.4)),   # sRGB #8E2D0D deep signal red
}
LOOKDEV_JSON = __import__("pathlib").Path(__file__).resolve().parents[1] / "render" / "lookdev_materials.json"


def check_lookdev(tol=2e-3, path=LOOKDEV_JSON):
    """Differences between MATERIALS and the photo-fitted glTF table render/lookdev_materials.json (base colour incl.
    alpha, metallic, roughness, clear coat, specular) for every material both define; [] = consistent (or no JSON)."""
    try:
        table = json.loads(path.read_text())["materials"]
    except (OSError, ValueError, KeyError):
        return []
    bad = []
    for name, g in table.items():
        if name not in MATERIALS:
            continue
        rgba, met, rough, *rest = MATERIALS[name]
        ext = rest[0] if rest else {}
        rgba = tuple(rgba) + ((1.0,) if len(rgba) == 3 else ())
        got = dict(base=rgba, metallic=met, rough=rough, clearcoat=ext.get("clearcoat", 0.0),
                   clearcoat_rough=ext.get("clearcoat_rough", 0.0) if ext.get("clearcoat") else 0.0,
                   specular=ext.get("specular", 1.0))
        want = dict(base=tuple(g["baseColorFactor"]), metallic=g["metallicFactor"], rough=g["roughnessFactor"],
                    clearcoat=g.get("clearcoatFactor", 0.0),
                    clearcoat_rough=g.get("clearcoatRoughnessFactor", 0.0) if g.get("clearcoatFactor") else 0.0,
                    specular=g.get("specularFactor", 1.0))
        for k in got:
            a, b = np.atleast_1d(got[k]), np.atleast_1d(want[k])
            if a.shape != b.shape or np.max(np.abs(a - b)) > tol:
                bad.append(f"{name}.{k}: model {got[k]} vs lookdev {want[k]}")
    return bad


def write_glb(parts: dict, path: str, quantize=True, meta=None):
    gb = GLBBuilder(quantize=quantize)
    for name, spec in MATERIALS.items():
        rgba, met, rough = spec[:3]
        gb.material(name, rgba, met, rough, double_sided=True, ext=spec[3] if len(spec) > 3 else None)

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
