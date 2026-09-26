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
    # ---- interior (Stage 3: model/flightdeck.py, model/seats.py, model/cabin.py; PRO s/n 3001 photos in the
    #      git-ignored refs/cache, [M] = read off those photos, [E] = estimated).  render/lookdev.py SPEC holds the same
    #      values for Blender (check_lookdev() compares); EMISSIVE below makes the displays and cabin lights glow.
    # cabin executive seats: light neutral-grey leather (MSN 3008 through-glass read of photos 130 / 82)
    "leather":       ((0.45, 0.445, 0.435), 0.0, 0.55, dict(specular=0.8)),
    # crew-seat finish 'light' (seats.CREW_FINISHES): the MSN 3008 crew-seat grey seen through the side window (0517)
    "leather_dark":  ((0.30, 0.295, 0.29), 0.0, 0.55, dict(specular=0.8)),
    # crew seats, PRO s/n 3001: cream leather, anthracite back shell / headrest back, grey sheepskin, black base
    "leather_crew":       ((0.60, 0.55, 0.47), 0.0, 0.50, dict(specular=0.8)),
    "leather_crew_shell": ((0.042, 0.044, 0.048), 0.0, 0.50, dict(specular=0.8)),
    # sheepskin: warm mauve-grey fleece (AOPA / P1046408-10 [M], review r1 F3), a sheen lobe for the pile
    "sheepskin":          ((0.36, 0.33, 0.35), 0.0, 1.00, dict(specular=0.3, sheen_color=(0.62, 0.58, 0.62),
                                                              sheen_rough=0.45)),
    "seat_base_black":    ((0.022, 0.022, 0.025), 0.3, 0.45),
    "harness":            ((0.069, 0.072, 0.080), 0.0, 0.80, dict(specular=0.5)),       # dark grey webbing
    "seat_shell_dark":    ((0.060, 0.063, 0.070), 0.0, 0.55, dict(specular=0.7)),       # executive shroud, armrest
    "seat_tab_red":       ((0.45, 0.02, 0.02), 0.0, 0.40),                              # base-shroud pull tab
    "seat_back_shell":    ((0.15, 0.155, 0.165), 0.0, 0.55, dict(specular=0.7)),   # mid-grey exec back rear shell
    # flight deck: graphite panel face, brushed titanium-grey sub-panels / stack, grey leather hood, dark carpet
    "panel_dark":          ((0.040, 0.041, 0.044), 0.25, 0.48, dict(specular=0.5)),
    "panel_grey":          ((0.33, 0.305, 0.325), 0.18, 0.45),
    # light brushed silver: overhead panel face, yoke-hub centre insert (P1046406 / AOPA overhead, P1046408 yoke)
    "panel_silver":        ((0.46, 0.46, 0.45), 0.55, 0.32),
    "leather_glareshield": ((0.055, 0.055, 0.058), 0.0, 0.62, dict(specular=0.5)),
    "carpet_flightdeck":   ((0.045, 0.045, 0.050), 0.0, 0.95),
    "bezel_black":         ((0.010, 0.010, 0.012), 0.10, 0.32),
    # displays: dark glass; the page content is emissive (EMISSIVE) so the G3000 PRIME screens read as ON
    "screen":              ((0.004, 0.005, 0.007), 0.0, 0.05),
    "screen_sky":          ((0.005, 0.020, 0.080), 0.0, 0.10),
    "screen_ground":       ((0.050, 0.025, 0.010), 0.0, 0.10),
    "screen_map":          ((0.050, 0.042, 0.025), 0.0, 0.10),
    "screen_ui":           ((0.008, 0.010, 0.016), 0.0, 0.10),
    "screen_ui_hi":        ((0.030, 0.034, 0.042), 0.0, 0.10),
    "screen_green":        ((0.010, 0.060, 0.020), 0.0, 0.10),
    "screen_cyan":         ((0.008, 0.045, 0.070), 0.0, 0.10),
    "screen_white":        ((0.080, 0.080, 0.080), 0.0, 0.10),
    "light_amber":         ((0.90, 0.50, 0.05), 0.0, 0.20),           # annunciators / switch legends (lit)
    # PC-24-style yokes: gloss white hub, black grips
    "yoke_white":          ((0.78, 0.78, 0.77), 0.0, 0.22, dict(clearcoat=1.0, clearcoat_rough=0.06)),
    "grip_black":          ((0.018, 0.018, 0.020), 0.0, 0.62),
    # divider / lavatory / cabinets / FR34 header: dark grey-brown (smoked) walnut veneer under a gloss lacquer
    # (P1046406 [M]: sRGB ~90/80/77 in the cabin light)
    "veneer_walnut":       ((0.060, 0.047, 0.040), 0.0, 0.35, dict(clearcoat=1.0, clearcoat_rough=0.06)),
    # s/n 3001 orange curtains (divider, FR34): the amber read of P1046406 / 02 in the cabin light (review r1 F2)
    "curtain":             ((0.44, 0.19, 0.036), 0.0, 0.92, dict(specular=0.3)),
    "paint_red":           ((0.50, 0.015, 0.012), 0.0, 0.30, dict(clearcoat=1.0, clearcoat_rough=0.06)),  # T-handles
    # cabin floor: anthracite / navy ribbed carpet with the AI Orange aisle runner (P1046406 [M])
    "carpet":          ((0.022, 0.024, 0.032), 0.0, 0.95),
    "carpet_orange":   ((0.69, 0.25, 0.019), 0.0, 0.95),
    "carpet_light":    ((0.62, 0.62, 0.60), 0.0, 0.95),
    "carpet_grey":     ((0.26, 0.28, 0.30), 0.0, 0.95),
    "floor_panel":     ((0.20, 0.21, 0.22), 0.1, 0.60),
    # side ledges: dark anthracite satin top, gloss-black fascia band, anthracite kick panels, brushed trim
    "ledge_top":       ((0.024, 0.026, 0.030), 0.0, 0.40, dict(specular=0.5)),
    "ledge_panel":     ((0.060, 0.066, 0.078), 0.0, 0.55, dict(specular=0.5)),
    "gloss_black":     ((0.008, 0.008, 0.010), 0.0, 0.10, dict(clearcoat=1.0, clearcoat_rough=0.06)),
    "chrome_trim":     ((0.62, 0.62, 0.61), 1.0, 0.22),
    # headliner fittings, placards
    "psu_panel":       ((0.030, 0.031, 0.035), 0.1, 0.35),
    "light_cove":      ((0.90, 0.90, 0.88), 0.0, 0.30),
    "light_reading":   ((0.90, 0.88, 0.80), 0.0, 0.20),
    "placard_red":     ((0.55, 0.020, 0.015), 0.0, 0.35),
    # lavatory: white inside, gloss toilet shroud
    "lav_white":       ((0.84, 0.84, 0.82), 0.0, 0.35),
    "toilet_white":    ((0.88, 0.88, 0.88), 0.0, 0.12, dict(clearcoat=1.0, clearcoat_rough=0.06)),
    "toilet_bowl":     ((0.30, 0.31, 0.32), 0.0, 0.20),
    "lav_grey":        ((0.069, 0.072, 0.080), 0.0, 0.45),
    "upholstery_grey": ((0.092, 0.097, 0.105), 0.0, 0.60, dict(specular=0.6)),
    "net":             ((0.020, 0.020, 0.022), 0.0, 0.85),             # optional baggage net (non-PRO fit)
    "lining":        ((0.86, 0.84, 0.80), 0.0, 0.70),
    # flight-deck side-wall / headliner lining (interior.build_lining, x < STA cockpit_aft): mid grey, so the
    # windshield and side windows read as dark panes outdoors (photos 188 / 0517) and a lit grey cockpit in the hangar
    # (82)
    "lining_flightdeck": ((0.30, 0.30, 0.295), 0.0, 0.60),
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
# emissive factors (glTF emissiveFactor, linear): the G3000 PRIME page content and the cabin lights glow a little so
# the displays read as ON in the viewer and the renders (render/lookdev.py SPEC 'emission' carries the same colours)
EMISSIVE = {
    "screen":        (0.004, 0.006, 0.012),
    "screen_sky":    (0.02, 0.13, 0.70),
    "screen_ground": (0.20, 0.13, 0.05),
    "screen_map":    (0.34, 0.29, 0.16),
    "screen_ui":     (0.018, 0.024, 0.038),
    "screen_ui_hi":  (0.075, 0.085, 0.105),
    "screen_green":  (0.10, 0.65, 0.22),
    "screen_cyan":   (0.05, 0.48, 0.80),
    "screen_white":  (0.80, 0.80, 0.80),
    "light_amber":   (1.00, 0.55, 0.05),
    "light_cove":    (1.00, 0.95, 0.85),
    "light_reading": (1.00, 0.90, 0.72),
}
LOOKDEV_JSON = __import__("pathlib").Path(__file__).resolve().parents[1] / "render" / "lookdev_materials.json"


def check_lookdev(tol=2e-3, path=LOOKDEV_JSON):
    """Differences between MATERIALS / EMISSIVE and the photo-fitted glTF table render/lookdev_materials.json (base
    colour incl. alpha, metallic, roughness, clear coat, specular, emissive) for every material both define; [] =
    consistent (or no JSON)."""
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
                   specular=ext.get("specular", 1.0), emissive=tuple(EMISSIVE.get(name, (0.0, 0.0, 0.0))))
        want = dict(base=tuple(g["baseColorFactor"]), metallic=g["metallicFactor"], rough=g["roughnessFactor"],
                    clearcoat=g.get("clearcoatFactor", 0.0),
                    clearcoat_rough=g.get("clearcoatRoughnessFactor", 0.0) if g.get("clearcoatFactor") else 0.0,
                    specular=g.get("specularFactor", 1.0), emissive=tuple(g.get("emissiveFactor", (0.0, 0.0, 0.0))))
        for k in got:
            a, b = np.atleast_1d(got[k]), np.atleast_1d(want[k])
            if a.shape != b.shape or np.max(np.abs(a - b)) > tol:
                bad.append(f"{name}.{k}: model {got[k]} vs lookdev {want[k]}")
    return bad


def write_glb(parts: dict, path: str, quantize=True, meta=None):
    gb = GLBBuilder(quantize=quantize)
    for name, spec in MATERIALS.items():
        rgba, met, rough = spec[:3]
        gb.material(name, rgba, met, rough, emissive=EMISSIVE.get(name), double_sided=True,
                    ext=spec[3] if len(spec) > 3 else None)

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
