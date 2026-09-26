"""
Livery: the paint scheme of PC-12 PRO MSN 3008 (N81DW), the first PRO delivered (Pilatus news,
2025-09-26), reconstructed from the owner-selected photographs (refs/photos.json, git-ignored cache)
as flat colour boundaries.  No logos, lettering or registration marks are modelled.

Scheme (sheet L5, drawing/livery_profiles.py, draws it from THESE parameters):

  * base colour: deep metallic blue over the whole fuselage, dorsal, fin, rudder, wing upper surfaces,
    winglets, radar-pod body and the main-gear leg doors;
  * a light metallic blue swoosh: the whole lower cowling / lower nose, rising aft along the lower
    fuselage into a wide band through the cabin-window line that runs to the tail and across the lower
    rudder (region 'light');
  * white calligraphic pinstripes and swooshes: a thick white band from low on the cowling that rises
    aft and crosses the crown just aft of the cabin, a thin white line running parallel above it from
    the cowling, a thin white line along the lower edge of the light band to the rudder, and several
    strokes on the tail cone (STROKES); every white stroke is edged by a thin silver-champagne metallic
    outline (OUTLINE; photos 82 / 130 / 188);
  * white fin cap and bullet fairing, silver-grey metallic tailplane and elevators;
  * dark navy-charcoal wing (and winglet outboard-face) lower surfaces, belly fairing, flap-track fairings;
  * the PRO dark windshield mask ('trim_black', outline owned by model/cockpit_glazing.py);
  * polished spinner and exhaust stacks; black propeller blades with a white tip and a red band.

Representation -- the same curves drive the 2-D sheet and the 3-D painter:

  * every fuselage / fin colour boundary is a curve in SIDE PROJECTION (x, z): a surface point (x, y, z)
    takes the colour of (x, z), so a stroke that reaches the crown continues over it onto the other
    side; port and starboard are mirror images (the photos show the same scheme on both sides);
  * a STROKE is a centre line z = c(x) (pchip through the (x, z) knots) with a vertical half-height
    h(x) (pchip through the knots' h; h = 0 at a tapered end) -- the calligraphic width law; its field
    is |z - c(x)| - h(x) (negative inside);
  * a REGION is the band between two pchip curves bot(x) < z < top(x);
  * an OUTLINE is a white stroke grown by OUTLINE['width'] (the same centre line, half-height
    h + w s(h), s tapering the outline with the stroke's calligraphic ends): painted below the white
    strokes, only its rim shows;
  * the fin cap is the part of the fin / rudder above the pchip line FIN_CAP;
  * wing, winglet, tailplane, pod, gear and powerplant colours are per surface (SURFACES, STAB_BOOT,
    WINGLET_PIN, PROP_BANDS).

Paint priority (top first; the painter trims in this order, the rest takes BASE): PAINT_ORDER.  The viewer
primes every 'paint_*' material and 'trim_black' until its paint step; polished metal and the propeller
colours are not primed.  Colours: PALETTE holds the design colour (sRGB) of every livery material;
model/assemble.MATERIALS holds the same colours as linear PBR base colours (check_materials() compares).  The
colours, metallic / roughness and clear coats are the MSN 3008 photo fits of render/lookdev.py (its glTF table
render/lookdev_materials.json; assemble.check_lookdev() compares).

Coordinates: x station (m aft of datum), y butt line (+ starboard), z water line (m).  The knots were
measured by camera-matching two starboard photographs of MSN 3008 (ground 3/4 and air-to-air) and
rectifying them onto the fuselage side projection, cross-checked on the port nose photographs (private
overlays in the git-ignored refs/cache/overlays/).
"""
from __future__ import annotations

import numpy as np

from cad.mesh import Mesh, trim, pchip

# =====================================================================================================
# palette: design colour (sRGB, the flat drawing colour) -> PBR base colour (linear) for the glTF
# =====================================================================================================
PALETTE = {
    # name                sRGB      metallic roughness  description
    # (photo-fitted to MSN 3008 in render/lookdev.py -- hangar photo 130 pins the albedo, the outdoor photos 188 /
    # 0517 / N81DW the metallic flop; glTF metallic / roughness as in render/lookdev_materials.json)
    "paint_blue":        ("#13347D", 0.30, 0.50, "deep metallic blue (base colour)"),
    "paint_blue_light":  ("#8096C4", 0.50, 0.38, "light metallic (silver-)blue (lower nose, swoosh band)"),
    "paint_pinstripe":   ("#F3F4F5", 0.00, 0.30, "white pinstripes and swooshes"),
    "paint_champagne":   ("#BAAC95", 0.40, 0.38, "silver-champagne metallic outline of every white stroke"),
    "paint_white":       ("#F3F4F5", 0.00, 0.30, "white (fin cap, bullet fairing)"),
    "paint_wing_dark":   ("#18244B", 0.35, 0.42, "dark navy metallic (wing lower surfaces, belly fairing)"),
    "paint_silver":      ("#ADADAF", 0.55, 0.36, "silver-grey metallic (tailplane, elevators)"),
    "paint_black":       ("#1D1E21", 0.00, 0.30, "gloss black (radar-pod radome)"),
    "trim_black":        ("#19191D", 0.00, 0.50, "PRO windshield mask + glazing frames (anti-glare black)"),
    # de-ice boots (rubber, not paint): near-black glossy neoprene -- photos 188 sRGB 32/36/44 in shade, IMG_0459
    # ~(32-35, 43-51, 44-64); the Pilatus front render's wing front face (30-38, 36-44, 41-49)
    "deice_boot":        ("#1D1D1F", 0.00, 0.25, "wing / tailplane leading-edge de-ice boots (black rubber)"),
    "chrome":            ("#F3F5F6", 1.00, 0.035, "polished chrome (spinner)"),
    "exhaust_polished":  ("#BCAD95", 1.00, 0.06, "polished exhaust stacks (heat tint)"),
    "prop_blade":        ("#212123", 0.00, 0.45, "propeller blade (satin black composite)"),
    "prop_tip":          ("#E7E7E5", 0.00, 0.36, "propeller blade tip (white)"),
    "prop_band_red":     ("#8E2D0D", 0.00, 0.40, "propeller blade red band"),
}
# pre-existing materials of model/assemble.py that the livery uses unchanged
EXISTING = ("paint_white", "trim_black", "chrome", "prop_blade", "prop_tip", "deice_boot")
# flat colours for the drawings where the PBR base colour would mislead (polished metal renders from its
# reflections)
DRAWING_COLOR = {"chrome": "#C5CBD1", "exhaust_polished": "#B3AA9B"}


def srgb_to_linear(hexcol):
    """'#RRGGBB' -> linear-light (r, g, b) floats (IEC 61966-2-1)."""
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return tuple(float(round(v, 4)) for v in lin)


def linear_to_hex(rgb):
    c = [1.055 * v ** (1 / 2.4) - 0.055 if v > 0.0031308 else 12.92 * v for v in rgb[:3]]
    return "#" + "".join(f"{int(round(255 * min(max(v, 0.0), 1.0))):02X}" for v in c)


def material_table():
    """{name: ((r, g, b) linear, metallic, roughness)} of the livery palette (model/assemble.MATERIALS)."""
    return {k: (srgb_to_linear(v[0]), v[1], v[2]) for k, v in PALETTE.items()}


def drawing_color(name):
    """Flat sRGB colour a drawing uses for a material (palette, else the glTF material's base colour)."""
    if name in DRAWING_COLOR:
        return DRAWING_COLOR[name]
    if name in PALETTE:
        return PALETTE[name][0]
    from model.assemble import MATERIALS
    return linear_to_hex(MATERIALS[name][0])


# =====================================================================================================
# side-projection curves (x, z) -- fuselage, dorsal, fin, rudder
# =====================================================================================================
# STROKES: id -> (material, [(x, z_centre, h_half), ...]); h = 0 marks a tapered (calligraphic) end.
STROKES = {
    # thick white band: from low on the cowl front, dipping under the exhaust, then rising aft along the
    # fuselage side and sweeping up over the crown just aft of the last cabin window
    "B1": ("paint_pinstripe", [
        (1.050, 1.300, 0.000), (1.150, 1.275, 0.060), (1.300, 1.255, 0.075), (1.600, 1.222, 0.075),
        (2.000, 1.212, 0.063), (2.500, 1.248, 0.048), (3.000, 1.268, 0.044), (3.500, 1.341, 0.041),
        (4.000, 1.427, 0.038), (4.500, 1.560, 0.036), (5.000, 1.671, 0.036), (5.500, 1.792, 0.036),
        (6.000, 1.875, 0.036), (6.500, 1.985, 0.036), (7.000, 2.085, 0.037), (7.500, 2.190, 0.040),
        (8.000, 2.380, 0.048), (8.500, 2.597, 0.046), (8.850, 2.743, 0.042), (9.050, 2.847, 0.042)]),
    # (rev B had a navy line 'N1' between B1 and P1: photos 130 / 82 / 188 show the base blue there -- the dark band
    # seen under P1 in photo 82 moves against the stripes along the fuselage in 130, a reflection horizon, not paint
    # (render/lookdev.py measurements, material review round 1 F3); the white strokes are edged by OUTLINE instead)
    # thin white line above B1, curving up over the crown between the last two cabin windows
    "P1": ("paint_pinstripe", [
        (1.120, 1.420, 0.000), (1.300, 1.385, 0.013), (2.000, 1.340, 0.016), (2.500, 1.334, 0.017),
        (3.000, 1.396, 0.020), (3.500, 1.452, 0.021), (4.000, 1.557, 0.022), (4.500, 1.680, 0.022),
        (5.000, 1.802, 0.022), (5.500, 1.935, 0.022), (6.000, 2.070, 0.021), (6.500, 2.250, 0.020),
        (7.000, 2.440, 0.019), (7.500, 2.620, 0.017), (7.850, 2.770, 0.016), (8.050, 2.870, 0.016)]),
    # thin white line from under the cockpit along the lower edge of the light band to the rudder
    "P2": ("paint_pinstripe", [
        (2.600, 1.110, 0.000), (3.000, 1.153, 0.010), (3.500, 1.215, 0.012), (4.000, 1.278, 0.013),
        (4.500, 1.418, 0.014), (5.000, 1.490, 0.015), (5.500, 1.595, 0.016), (6.000, 1.665, 0.017),
        (6.500, 1.725, 0.018), (7.000, 1.775, 0.019), (7.500, 1.825, 0.020), (8.000, 1.870, 0.021),
        (9.000, 1.935, 0.023), (10.00, 1.985, 0.025), (11.00, 2.015, 0.027), (12.00, 2.030, 0.028),
        (13.00, 2.035, 0.028), (13.60, 2.035, 0.026), (14.10, 2.035, 0.000)]),
    # upper edge of the light band on the tail cone, descending aft from STA ~10.75 onto the rudder (review round 3,
    # R3-2: white peaks of the rectified stbd_ground / stbd_air photos, mean of the two cameras; they differ by 4-10 cm)
    "H1": ("paint_pinstripe", [
        (8.300, 2.390, 0.000), (8.800, 2.430, 0.016), (9.500, 2.448, 0.020), (10.50, 2.440, 0.022),
        (11.00, 2.420, 0.022), (11.50, 2.390, 0.022), (12.00, 2.360, 0.022), (12.50, 2.310, 0.021),
        (13.00, 2.220, 0.020), (13.50, 2.170, 0.019), (13.70, 2.145, 0.017), (13.90, 2.125, 0.012)]),
    # thin line above H1 rising aft to the crown
    "U1": ("paint_pinstripe", [
        (8.300, 2.400, 0.000), (8.800, 2.430, 0.010), (9.500, 2.490, 0.012), (10.00, 2.527, 0.013),
        (10.50, 2.635, 0.013), (10.80, 2.700, 0.012), (11.00, 2.760, 0.000)]),
    # diagonal across the light band, rising aft to the fin root, flattening aft of its crossing with H1 (R3-2 photo
    # peaks: STA 12.5 WL 2.42 / 2.41, 12.9 2.45 / 2.47 -- rev B rose to 2.54, 6-7 cm high)
    "X1": ("paint_pinstripe", [
        (8.400, 1.840, 0.000), (9.000, 1.905, 0.016), (10.00, 2.065, 0.019), (11.00, 2.225, 0.020),
        (11.50, 2.300, 0.020), (12.00, 2.370, 0.020), (12.50, 2.420, 0.019), (12.90, 2.460, 0.012),
        (13.05, 2.475, 0.000)]),
    # steeper diagonal from the fuselage side into the light band
    "X2": ("paint_pinstripe", [
        (8.500, 1.950, 0.000), (9.000, 2.110, 0.020), (9.500, 2.270, 0.022), (10.00, 2.420, 0.022),
        (10.40, 2.540, 0.018), (10.80, 2.640, 0.000)]),
    # ... and its reflection off the crown: a short, steeper stroke descending aft from the crown that fades out above
    # H1 (R3-2: the photos show it only at STA 10.5-11.2, WL 2.62-2.54; no separate line above H1 further aft)
    "X3": ("paint_pinstripe", [
        (10.60, 2.705, 0.000), (10.80, 2.660, 0.009), (11.00, 2.605, 0.011), (11.20, 2.550, 0.009),
        (11.40, 2.500, 0.000)]),
    # deep-blue counter-stroke splitting the light swoosh under P2 (from under the cockpit to the wing TE)
    "W1": ("paint_blue", [
        (3.800, 1.250, 0.000), (4.200, 1.285, 0.030), (4.500, 1.318, 0.060), (5.000, 1.350, 0.090),
        (5.500, 1.490, 0.080), (6.000, 1.600, 0.050), (6.500, 1.690, 0.022), (6.900, 1.745, 0.000)]),
    # stroke from the lower fuselage behind the wing, rising aft into P2
    "D1": ("paint_pinstripe", [
        (7.300, 1.260, 0.000), (7.800, 1.320, 0.012), (8.500, 1.460, 0.015), (9.000, 1.580, 0.017),
        (9.500, 1.700, 0.017), (10.00, 1.830, 0.016), (10.50, 1.950, 0.012), (10.80, 2.020, 0.000)]),
}

# REGIONS: id -> (material, top knots, bottom knots); the band bot(x) < z < top(x) over the knot range
REGIONS = {
    "light": ("paint_blue_light",
              [(1.000, 1.330), (1.500, 1.198), (2.000, 1.180), (2.500, 1.220), (3.000, 1.259), (3.500, 1.330),
               (4.000, 1.418), (4.500, 1.519), (5.000, 1.629), (5.500, 1.739), (6.000, 1.839), (6.500, 1.949),
               (7.000, 2.048), (7.500, 2.150), (8.000, 2.330), (8.500, 2.410), (9.000, 2.435), (10.00, 2.440),
               (10.50, 2.432), (11.00, 2.412), (11.50, 2.382), (12.00, 2.352), (12.50, 2.303), (13.00, 2.213),
               (13.50, 2.163), (13.70, 2.138), (14.40, 2.080)],
              [(1.000, 0.500), (4.200, 0.500), (4.650, 0.880), (5.000, 1.100), (5.500, 1.250), (6.000, 1.400),
               (6.500, 1.520), (7.000, 1.640), (7.300, 1.745), (7.600, 1.800), (8.000, 1.850), (9.000, 1.915),
               (10.00, 1.962), (11.00, 1.990), (12.00, 2.004), (13.00, 2.010), (14.40, 2.010)]),
}

# white fin cap: fin / rudder above this line (the bullet fairing is white all over).  Review round 3 (R3-1): both
# starboard photos rectified onto the fin plane show the white cap across the WHOLE fin chord below the bullet, its
# lower boundary rising gently aft (ground / air: STA 12.9 WL 3.545 / 3.62, 13.3 3.63 / 3.68, 13.9 3.735, 14.3 3.76),
# so the rudder top and the fixed fin tip are white too (rev B line rose steeply to WL 4.15 and left them blue)
FIN_CAP = [(12.600, 3.470), (12.900, 3.560), (13.300, 3.650), (13.700, 3.710), (14.100, 3.750), (14.400, 3.760)]
FIN_CAP_X0 = 12.0                     # the cap region starts on the fin (never on the dorsal / tail cone)

# paint priority, top first (the painter trims in this order; the rest is the base colour).  'paint_blue'
# in the order is the base colour painted as a counter-stroke over the light band (W1).
PAINT_ORDER = ("trim_black", "paint_white", "paint_pinstripe", "paint_champagne", "paint_blue", "paint_blue_light")
BASE = "paint_blue"

# silver-champagne outline of the white strokes (photo 82 edge profiles: 6-9 px ~ 8 mm on both edges of every white
# stroke, sRGB 189/184/182 beside the white's 222-227; 188: 172/165/156 beside 240; render/lookdev.py measurements).
# Each paint_pinstripe stroke grown by 'width' (side-projection z, like the strokes' half-heights) and painted just
# below the white: h_outline = h + width * min(1, h / taper_h), so the outline tapers out with a calligraphic end (and
# stops where the stroke is thinner than min_h); a blunt end (h > 0) gets a 'width' cap.  The exit ring (EXIT_MARK) is
# edged the same way.
OUTLINE = dict(material="paint_champagne", of="paint_pinstripe", width=0.008, taper_h=0.010, min_h=0.003)

# over-wing exit marking: white ring centred on the hatch seam (fuselage_parts.EXIT), starboard only
# (rectified ground photo: ring 5.975-6.475 x 1.88-2.545 outer, ~25 mm wide)
EXIT_MARK = dict(offset=0.000, half_width=0.0125)
EXIT_MARK_MAT = "paint_pinstripe"

# =====================================================================================================
# per-surface colours (wing, winglet, tailplane, pod, gear, powerplant)
# =====================================================================================================
SURFACES = dict(
    wing_upper="paint_blue", wing_lower="paint_wing_dark",       # incl. flaps, ailerons, tabs
    winglet_inboard="paint_blue", winglet_outboard="paint_wing_dark",
    stab_upper="paint_silver", stab_lower="paint_silver",         # incl. elevators
    boot="deice_boot",                                            # wing / tailplane leading edges (not paint)
    bullet="paint_white", dorsal=BASE, strakes=BASE,
    belly_fairing="paint_wing_dark", flap_fairings="paint_wing_dark",
    pod_body="paint_blue", pod_radome="paint_black",              # radome forward of details.POD_X_JOINT
    main_gear_door="paint_blue", nose_gear_door="paint_blue_light",
    spinner="chrome", exhaust="exhaust_polished",
    inlet_lip="chrome", inlet_mouth="inlet_dark",                 # chin inlet (powerplant.CHIN_INLET): polished lip
    blade_le="erosion",                                           # blade leading-edge erosion strip (metal)
)
STAB_BOOT = dict(upper=0.08, lower=0.06)      # tailplane LE boot, chord fractions (photos: black LE band)
# white pinstripe on the winglet's inboard face (IMG_0459): a CHORDWISE line along the root blend, from the pod
# joint to the trailing edge -- the winglet section at fraction s of the winglet path, chord fractions c0..c1
WINGLET_PIN = dict(s=0.30, c0=0.02, c1=1.00, half_width=0.008)
# propeller blade tip bands, radial extent measured inward from the tip (m): white tip, black gap, red band
# (hangar photo MSN-3008_130, upper blade against the ceiling: 17 / 11 / 12 px on a ~40 px = 0.13 m chord)
PROP_BANDS = (("prop_tip", 0.000, 0.060), ("prop_blade", 0.060, 0.095), ("prop_band_red", 0.095, 0.135))
# blade leading-edge erosion shield (SURFACES blade_le; nickel sheath on the composite blades): a band round the leading
# edge, BLADE_LE_STRIP['width'] (m, measured from the LE line) on each face, from r0 out to the red band's inner edge
BLADE_LE_STRIP = dict(r0=0.40, width=0.020)

# PRO dark cockpit mask: its outline is built by model/cockpit_glazing.py from the glazing planes, but the AFT EDGE
# is a livery item that differs between airframes (photos rectified onto the OML with the camera fits in
# refs/cache/overlays/livery/cams.json; sheet-L2 review):
#   MSN 3008  pro3008_stbd34 (stbd_ground camera) and pro3008_port34 (port_hangar_130): straight edge leaning
#             22-27 deg (bottom forward) from the top-aft corner STA ~4550 / WL ~2510 to STA ~4350 at the lower edge;
#             blue gap to the airstair door seam ~0.10 m at the top, ~0.27 m low
#   MSN 3010  leans ~12-16 deg once corrected against the vertical door jamb
#   MSN 3036  vertical edge, runs aft to within ~0.05 m of the door frame
#   MSN 3066  curved edge following the glass "D" (not a straight-edge scheme)
MASK_SCHEMES = {
    "MSN 3008": dict(aft_x=4.560, lean_deg=22.5, r_low_aft=0.060, r_top_aft=0.040),
    "MSN 3010": dict(aft_x=4.560, lean_deg=14.0, r_low_aft=0.060, r_top_aft=0.040),
    "MSN 3036": dict(aft_x=4.575, lean_deg=0.0, r_low_aft=0.040, r_top_aft=0.040),
}
MASK_SCHEME = "MSN 3008"          # the airframe this model carries (sheets L2 and L5)
MASK = MASK_SCHEMES[MASK_SCHEME]  # aft_x: aft edge at the mask's top line; lean_deg: bottom forward of the top

# wing-to-body fairing tables: single source model/details.py (Stage 2 rev B, fitted to the drawing):
# (station, footprint half-width), (station, bottom WL), side-view tail lobe, upper root-fillet plan outline
from model.details import (BELLY_FAIRING_HW, BELLY_FAIRING_BOT, BELLY_FAIRING_TAIL,  # noqa: E402,F401
                           BELLY_FAIRING_PLAN, BELLY_FAIRING_NOSE_EDGE)

# =====================================================================================================
# evaluation
# =====================================================================================================
_BIG = 1.0


class Stroke:
    """Calligraphic stroke: centre line c(x) and vertical half-height h(x), both pchip."""

    def __init__(self, sid, mat, knots):
        k = np.asarray(knots, float)
        self.id, self.mat, self.knots = sid, mat, k
        self.x0, self.x1 = float(k[0, 0]), float(k[-1, 0])
        self.c = pchip(k[:, 0], k[:, 1])
        self.h = pchip(k[:, 0], k[:, 2])

    def field(self, x, z):
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        xc = np.clip(x, self.x0, self.x1)
        f = np.abs(z - self.c(xc)) - np.maximum(self.h(xc), 0.0)
        return np.where((x >= self.x0) & (x <= self.x1), f, _BIG)

    def outline(self, n=240):
        """Closed (N, 2) outline in side projection (upper edge forward, lower edge back)."""
        xs = np.linspace(self.x0, self.x1, n)
        c, h = self.c(xs), np.maximum(self.h(xs), 0.0)
        return np.r_[np.c_[xs, c + h], np.c_[xs[::-1], (c - h)[::-1]]]


class Region:
    """Band between two pchip curves bot(x) < z < top(x)."""

    def __init__(self, rid, mat, top, bot):
        t, b = np.asarray(top, float), np.asarray(bot, float)
        self.id, self.mat, self.top_k, self.bot_k = rid, mat, t, b
        self.x0, self.x1 = max(t[0, 0], b[0, 0]), min(t[-1, 0], b[-1, 0])
        self.top, self.bot = pchip(t[:, 0], t[:, 1]), pchip(b[:, 0], b[:, 1])

    def field(self, x, z):
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        xc = np.clip(x, self.x0, self.x1)
        f = np.maximum(self.bot(xc) - z, z - self.top(xc))
        return np.where((x >= self.x0) & (x <= self.x1), f, _BIG)


class Outline:
    """OUTLINE rim of a white stroke st: the same centre line, half-height h + w min(1, h / taper_h) (the rim tapers out
    with a calligraphic end), extended by w beyond a blunt end (h > 0 there).  Painted below the white strokes, so
    only the w-wide rim shows.  Where the stroke is thinner than min_h (its last few cm to a tapered tip, where it is a
    hairline anyway) the rim stops: a rim round a vanishing tip only left zero-area slivers (dropped by the glTF
    writer -> pin holes, e.g. P1's tip on the chin-inlet lip)."""

    def __init__(self, st, mat, width, taper_h, min_h=0.003):
        self.id, self.mat, self.stroke, self.w, self.th = f"{st.id}~", mat, st, float(width), float(taper_h)
        xs = np.linspace(st.x0, st.x1, 4001)
        on = xs[np.asarray(st.h(xs)) >= min_h]
        a, b = (float(on[0]), float(on[-1])) if len(on) else (st.x0, st.x0)
        self.x0 = a - (self.w if a <= st.x0 else 0.0)
        self.x1 = b + (self.w if b >= st.x1 else 0.0)

    def c(self, x):
        return self.stroke.c(np.clip(x, self.stroke.x0, self.stroke.x1))

    def h(self, x):
        hs = np.maximum(self.stroke.h(np.clip(x, self.stroke.x0, self.stroke.x1)), 0.0)
        return hs + self.w * np.minimum(1.0, hs / self.th)

    def field(self, x, z):
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        f = np.abs(z - self.c(x)) - self.h(x)
        return np.where((x >= self.x0) & (x <= self.x1), f, _BIG)

    def outline(self, n=240):
        xs = np.linspace(self.x0, self.x1, n)
        c, h = self.c(xs), self.h(xs)
        return np.r_[np.c_[xs, c + h], np.c_[xs[::-1], (c - h)[::-1]]]


def _build():
    global _STROKES, _REGIONS, _OUTLINES, _CAP, L_, U_, B_, LIVERY_LINES
    _STROKES = {k: Stroke(k, m, v) for k, (m, v) in STROKES.items()}
    _REGIONS = {k: Region(k, m, t, b) for k, (m, t, b) in REGIONS.items()}
    _OUTLINES = {k: Outline(s, OUTLINE["material"], OUTLINE["width"], OUTLINE["taper_h"], OUTLINE["min_h"])
                 for k, s in _STROKES.items() if s.mat == OUTLINE["of"]} if OUTLINE.get("width", 0) > 0 else {}
    _CAP = pchip(*zip(*FIN_CAP))
    # legacy names (the first model's scheme exported its three curves)
    LIVERY_LINES = dict(strokes={k: v[1] for k, v in STROKES.items()},
                        regions={k: dict(top=v[1], bot=v[2]) for k, v in REGIONS.items()}, fin_cap=FIN_CAP)
    L_, U_ = _REGIONS["light"].bot, _REGIONS["light"].top      # light band lower / upper edge
    B_ = _STROKES["B1"].c                                      # main white band centre line


_STROKES = _REGIONS = _OUTLINES = _CAP = L_ = U_ = B_ = LIVERY_LINES = None
_build()
PIN = (-0.02, 0.02)                    # legacy name (the old scheme's pinstripe offsets); unused


def rebuild():
    """Re-evaluate the curves after STROKES / REGIONS / FIN_CAP were edited in place (fitting tools)."""
    _build()


def strokes():
    return dict(_STROKES)


def regions():
    return dict(_REGIONS)


def outlines():
    """{stroke id: Outline} of the white strokes (OUTLINE)."""
    return dict(_OUTLINES)


def fin_cap_line(x):
    return _CAP(np.clip(np.asarray(x, float), FIN_CAP[0][0], FIN_CAP[-1][0]))


def fin_cap_field(x, z):
    """Negative on the fin / rudder above the cap line (the caller restricts it to fin surfaces)."""
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    return np.where(x >= FIN_CAP_X0, fin_cap_line(x) - z, _BIG)


def side_fields(x, z, y=None, fin=False):
    """Side-projection paint fields {material: field} in PAINT_ORDER (negative inside; the strokes of one
    material are united).  fin=True adds the fin cap (fin / rudder surfaces only).  The mask
    (cockpit_glazing.surround_sdf) is valid on the forward fuselage only."""
    from model import cockpit_glazing as CG
    x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
    out = {m: np.full(x.shape, _BIG) for m in PAINT_ORDER}
    for s in _STROKES.values():
        out[s.mat] = np.minimum(out[s.mat], s.field(x, z))
    for r in _REGIONS.values():
        out[r.mat] = np.minimum(out[r.mat], r.field(x, z))
    for o in _OUTLINES.values():
        out[o.mat] = np.minimum(out[o.mat], o.field(x, z))
    if fin:
        out["paint_white"] = np.minimum(out["paint_white"], fin_cap_field(x, z))
    out["trim_black"] = CG.surround_sdf(x, np.zeros_like(x) if y is None else y, z)
    return out


def side_paint(x, z, fin=False, mask=True):
    """Index into PAINT_ORDER + (BASE,) of the topmost paint at side-projection points (x, z)."""
    F = side_fields(x, z, fin=fin)
    idx = np.full(np.shape(F[PAINT_ORDER[0]]), len(PAINT_ORDER), int)
    for i in range(len(PAINT_ORDER) - 1, -1, -1):
        if PAINT_ORDER[i] == "trim_black" and not mask:
            continue
        idx = np.where(F[PAINT_ORDER[i]] < 0, i, idx)
    return idx


# =====================================================================================================
# 3-D painter (Stage 3 adapts the part list and the surface splits; the interface is the first model's)
# =====================================================================================================
def fields(V, UV=None, fin=False):
    """Per-vertex paint fields of a fuselage / fin mesh (V (n, 3) model coordinates; UV unused)."""
    return side_fields(V[:, 0], V[:, 2], V[:, 1], fin=fin)


def region_fields(mat, cockpit=False, fin=False):
    """The paint regions of one material as lists of SMOOTH half-space fields f(V) (negative inside); a region is
    the intersection of its list, the material the union of its regions.  Strokes: x0 < x < x1 and
    c(x) - h(x) < z < c(x) + h(x) as two one-sided fields (the |z - c| - h form is V-shaped at the centre line:
    marching triangles lose strokes thinner than the skin grid there -- S3-11); regions: bot < z < top; the fin cap:
    z > FIN_CAP(x); the PRO mask: cockpit_glazing.surround_sdf; the over-wing exit ring (starboard)."""
    out = []

    def clip(fn, x0, x1):
        return lambda V: fn(np.clip(V[:, 0], x0, x1))

    for st in list(_STROKES.values()) + list(_OUTLINES.values()):
        if st.mat != mat:
            continue
        c, h = clip(st.c, st.x0, st.x1), clip(st.h, st.x0, st.x1)
        out.append([lambda V, a=st.x0: a - V[:, 0], lambda V, b=st.x1: V[:, 0] - b,
                    lambda V, c=c, h=h: (c(V) - np.maximum(h(V), 0.0)) - V[:, 2],
                    lambda V, c=c, h=h: V[:, 2] - (c(V) + np.maximum(h(V), 0.0))])
    for rg in _REGIONS.values():
        if rg.mat != mat:
            continue
        top, bot = clip(rg.top, rg.x0, rg.x1), clip(rg.bot, rg.x0, rg.x1)
        out.append([lambda V, a=rg.x0: a - V[:, 0], lambda V, b=rg.x1: V[:, 0] - b,
                    lambda V, bot=bot: bot(V) - V[:, 2], lambda V, top=top: V[:, 2] - top(V)])
    if mat == "paint_white" and fin:
        out.append([lambda V: FIN_CAP_X0 - V[:, 0], lambda V: fin_cap_line(V[:, 0]) - V[:, 2]])
    if mat == "trim_black" and cockpit:
        from model import cockpit_glazing as CG
        out.append([lambda V: CG.surround_sdf(V[:, 0], V[:, 1], V[:, 2])])
    if mat == EXIT_MARK_MAT or (mat == OUTLINE["material"] and EXIT_MARK_MAT == OUTLINE["of"] and _OUTLINES):
        from model.fuselage_parts import EXIT, rr
        o, w = EXIT_MARK["offset"], EXIT_MARK["half_width"] + (OUTLINE["width"] if mat != EXIT_MARK_MAT else 0.0)
        f = lambda V: rr((V[:, 0], V[:, 2]), EXIT)                                  # noqa: E731
        out.append([lambda V: 0.2 - V[:, 1] * EXIT["side"], lambda V: (o - w) - f(V), lambda V: f(V) - (o + w)])
    return out


def _extract(m: Mesh, fields):
    """Split m into (inside every field, the rest) with one sequential trim per field (fields re-evaluated on the
    trimmed pieces, cut vertices shared along each cut)."""
    piece, outs = m, []
    for f in fields:
        v = f(piece.V)
        if not (v < 0).any():
            return None, m
        if (v >= 0).any():
            outs.append(trim(piece, v, "positive"))
            piece = trim(piece, v, "negative")
        if piece.nf == 0:
            return None, m
    outs = [o for o in outs if o.nf]
    rest = Mesh.merge(outs) if outs else Mesh(np.zeros((0, 3)), np.zeros((0, 3), int))
    return piece, rest


def paint_mesh(m: Mesh, order=PAINT_ORDER, cockpit=False, fin=False, base=BASE):
    """Split one unpainted mesh into livery regions -> list of (mesh, material), topmost paint first.
    cockpit=False skips the PRO mask (it lies on the forward fuselage, the forward cabin skin and the upper cowl)."""
    out = []
    rest = m
    for mat in order:
        for fields in region_fields(mat, cockpit=cockpit, fin=fin):
            if rest.nf == 0:
                break
            inside, rest = _extract(rest, fields)
            if inside is not None and inside.nf:
                out.append((inside, mat))
    if rest.nf:
        out.append((rest, base))
    return out


def _split(m: Mesh, f, mat_neg, mat_pos):
    out = []
    a, b = trim(m, f, "negative"), trim(m, f, "positive")
    if a.nf:
        out.append((a, mat_neg))
    if b.nf:
        out.append((b, mat_pos))
    return out


# belly_fairing: only its root fillet is unpainted (the belly is not); door_frames: only the door-panel lips are
PAINTED = ["cowl_upper", "cowl_lower", "fus_fwd", "fus_center", "fus_aft", "fin", "rudder", "rudder_tab",
           "door_airstair", "door_cargo", "exit_hatch", "dorsal_fin", "chin_inlet", "strakes", "gear_door_NR",
           "gear_door_NL", "belly_fairing", "door_frames"]
FIN_PARTS = ("fin", "rudder", "rudder_tab")
# D3: the PRO mask (cockpit_glazing.surround_sdf) is painted on every skin it covers, so it runs on across the
# forward / centre fuselage joint (fuselage_parts.SPLIT_FWD) instead of stopping there
MASK_PARTS = ("fus_fwd", "fus_center", "cowl_upper")
UNPAINTED = "paint_white"          # the builders' unpainted skin material


def _radial_bands(mesh, r_of, bands, r_tip, default):
    """Split a blade into the tip bands.  bands run inward from the tip without gaps ((mat, a, b): a..b m inside the
    tip); each band edge is ONE single-sided trim at radius r_tip - b, re-evaluated on the piece left over (CONS-07: a
    V-shaped max() band field on the 40 mm radial grid moved the edges up to 11 mm).  The tip band has no outer
    limit.  Returns ([(mesh, mat)], rest): rest = the blade inside the last band (default material, not yet added)."""
    out, rest = [], mesh
    prev = 0.0
    for mat, a, b in bands:
        assert abs(a - prev) < 1e-12, "PROP_BANDS must be contiguous from the tip"
        prev = b
        if rest.nf == 0:
            break
        f = (r_tip - b) - r_of(rest.V)             # < 0: outboard of this band's inner edge
        outer = trim(rest, f, "negative")
        rest = trim(rest, f, "positive")
        if outer.nf:
            out.append((outer, mat))
    return out, rest


def blade_le_distance(V, k):
    """(radius along the pitch axis, distance from the leading-edge line) of points V on blade k (0-based), in the
    blade's own frame (powerplant.blade_geometry about the hub, thrust_rotation, blade k's clock angle)."""
    from model import powerplant as PP
    from cad.mesh import rotation_matrix
    _, rs, Pm = _blade_ref()
    R = PP.thrust_rotation() @ rotation_matrix((1, 0, 0), 2 * np.pi * k / PP.N_BLADES)
    q = (np.asarray(V, float) - PP.prop_hub()) @ R                  # R^T (V - hub)
    i_le = Pm.shape[1] // 2                                         # lower TE -> LE (xc = 0) ends the first half
    le = Pm[:, i_le, :]
    lx = np.interp(q[:, 2], le[:, 2], le[:, 0])
    ly = np.interp(q[:, 2], le[:, 2], le[:, 1])
    return q[:, 2], np.hypot(q[:, 0] - lx, q[:, 1] - ly)


_BLADE_REF = None


def _blade_ref():
    global _BLADE_REF
    if _BLADE_REF is None:
        from model import powerplant as PP
        _BLADE_REF = PP.blade_geometry()
    return _BLADE_REF


def _blade_le_strip(rest, k, r_out):
    """Split the erosion shield (BLADE_LE_STRIP, r0 .. r_out) off the plain blade piece (sequential trims)."""
    p = BLADE_LE_STRIP
    out = []
    r, _ = blade_le_distance(rest.V, k)
    inner = trim(rest, r - p["r0"], "negative")                    # root part: never shielded
    cand = trim(rest, r - p["r0"], "positive")
    if inner.nf:
        out.append((inner, "prop_blade"))
    if cand.nf:
        _, d = blade_le_distance(cand.V, k)
        le = trim(cand, d - p["width"], "negative")
        body = trim(cand, d - p["width"], "positive")
        if body.nf:
            out.append((body, "prop_blade"))
        if le.nf:
            r, _ = blade_le_distance(le.V, k)
            f = r - r_out                                           # the shield stops at the red band
            a, b = trim(le, f, "negative"), trim(le, f, "positive")
            if a.nf:
                out.append((a, SURFACES["blade_le"]))
            if b.nf:
                out.append((b, "prop_blade"))
    return out


def _winglet_pin(m, sgn):
    """Split WINGLET_PIN (the white chordwise line on the winglet's inboard face) off an inboard-face piece m of the
    winglet on side sgn: the band |d| <= half_width about the plane of the winglet section at path fraction s
    (the section sheet L5 draws: winglet_sections(40, 30)), chord c0..c1; sequential single-sided trims."""
    from model import wing as W
    p = WINGLET_PIN
    secs = W.winglet_sections(40, 30)
    sec = secs[int(round(p["s"] * (len(secs) - 1)))]
    le = sec.le * [1, sgn, 1]
    e_c = sec.e_c * [1, sgn, 1]
    e_t = np.asarray(sec.e_t, float) * [1, sgn, 1]
    n = np.cross(e_c, e_t)
    n /= np.linalg.norm(n)
    d = lambda mm: (mm.V - le) @ n                                  # noqa: E731
    xc = lambda mm: ((mm.V - le) @ e_c) / sec.chord                 # noqa: E731
    pieces, band = [], m
    for f in (lambda mm: d(mm) - p["half_width"], lambda mm: -d(mm) - p["half_width"],
              lambda mm: p["c0"] - xc(mm), lambda mm: xc(mm) - p["c1"]):
        v = f(band)
        out = trim(band, v, "positive")
        band = trim(band, v, "negative")
        if out.nf:
            pieces.append(out)
        if band.nf == 0:
            break
    return band, pieces


def _stab_boot(m):
    """Split the tailplane LE boot (STAB_BOOT: 8 % upper / 6 % lower chord, BL 0 -> the fixed-tip rib STAB_TIP_RIB, as
    sheet L5 draws stab_boot_outline) off a stabiliser skin piece; chordwise edge and span end trimmed in turn.
    Returns (boot, [rest pieces])."""
    from model import empennage as E
    def xc_field(mm):
        y = np.abs(mm.V[:, 1])
        le, te = E.stab_le(y), E.stab_te(y)
        xc = (mm.V[:, 0] - le) / np.maximum(te - le, 1e-3)
        return xc - np.where(mm.V[:, 2] >= E.STAB_Z, STAB_BOOT["upper"], STAB_BOOT["lower"])
    rest = []
    v = xc_field(m)
    boot = trim(m, v, "negative")
    r = trim(m, v, "positive")
    if r.nf:
        rest.append(r)
    if boot.nf:
        v = np.abs(boot.V[:, 1]) - E.STAB_TIP_RIB
        r = trim(boot, v, "positive")
        boot = trim(boot, v, "negative")
        if r.nf:
            rest.append(r)
    return boot, rest


def apply(parts):
    """Paint the built parts in place (meshes still carrying the unpainted skin material)."""
    for pid in PAINTED:
        if pid not in parts:
            continue
        p = parts[pid]
        new = []
        for m, mat in p.meshes:
            if mat == UNPAINTED and not getattr(m, "_no_paint", False):
                new += paint_mesh(m, cockpit=pid in MASK_PARTS, fin=pid in FIN_PARTS)
            else:
                new.append((m, mat))
        p.meshes = new
    if "stabilizer" in parts:                      # tailplane LE boot (STAB_BOOT) before the silver recolour
        new = []
        for m, mat in parts["stabilizer"].meshes:
            if mat != UNPAINTED:
                new.append((m, mat))
                continue
            boot, rest = _stab_boot(m)
            new += [(r, mat) for r in rest]
            if boot.nf:
                new.append((boot, SURFACES["boot"]))
        parts["stabilizer"].meshes = new
    recolor = {"tail_bullet": SURFACES["bullet"], "belly_fairing": SURFACES["belly_fairing"],
               "flap_fairings": SURFACES["flap_fairings"], "stabilizer": SURFACES["stab_upper"],
               "elevator_R": SURFACES["stab_upper"], "elevator_L": SURFACES["stab_upper"],
               "antennas": BASE, "propeller": SURFACES["spinner"]}
    for pid, mat in recolor.items():
        if pid in parts:
            parts[pid].meshes = [(m, mat if mm in (UNPAINTED, "paint_belly") else mm) for m, mm in parts[pid].meshes]
    # wings, control surfaces, winglets: upper (winglet: inboard) face blue, lower face dark (normal split)
    for pid in [k for k in parts if k.split("_")[0] in ("wing", "flap", "aileron", "ail", "winglet")]:
        wl = pid.startswith("winglet")
        up, lo = ((SURFACES["winglet_inboard"], SURFACES["winglet_outboard"]) if wl
                  else (SURFACES["wing_upper"], SURFACES["wing_lower"]))
        new = []
        for m, mat in parts[pid].meshes:
            if mat == "paint_belly" and pid.startswith("flap_canoes"):   # aft flap-track canoes (on the flaps)
                new.append((m, SURFACES["flap_fairings"]))
                continue
            if mat != UNPAINTED:
                new.append((m, mat))
                continue
            if wl:
                side = 1.0 if m.V[:, 1].mean() > 0 else -1.0
                f = -(m.N[:, 2] - side * m.N[:, 1])          # up / inboard-facing: negative
            else:
                f = -m.N[:, 2]
            pieces = _split(m, f, up, lo)
            if wl:                                       # WINGLET_PIN on the inboard face
                out = []
                for mm, mt in pieces:
                    if mt != up:
                        out.append((mm, mt))
                        continue
                    pin, rest = _winglet_pin(mm, int(side))
                    out += [(r, up) for r in rest]
                    if pin.nf:
                        out.append((pin, "paint_pinstripe"))
                pieces = out
            new += pieces
        parts[pid].meshes = new
    if "radar_pod" in parts:                       # body blue, radome black forward of the joint
        from model import details as D
        new = []
        for m, mat in parts["radar_pod"].meshes:
            if mat in (UNPAINTED, "paint_belly"):
                new += _split(m, m.V[:, 0] - D.POD_X_JOINT, SURFACES["pod_radome"], SURFACES["pod_body"])
            else:
                new.append((m, mat))
        parts["radar_pod"].meshes = new
    for pid in ("gear_main_R", "gear_main_L"):     # leg-mounted doors
        if pid in parts:
            parts[pid].meshes = [(m, SURFACES["main_gear_door"] if mm == UNPAINTED else mm)
                                 for m, mm in parts[pid].meshes]
    if "exhaust_stacks" in parts:
        parts["exhaust_stacks"].meshes = [(m, SURFACES["exhaust"] if mm == "exhaust" else mm)
                                          for m, mm in parts["exhaust_stacks"].meshes]
    # blade tip bands: radius about the THRUST axis (powerplant.prop_hub / thrust_dir: 2 deg down, 2 deg right, hub
    # off the centre line), not the untilted line (CONS-07); plus the LE erosion shield inboard of the bands
    from model import powerplant as PP
    hub, ax = PP.prop_hub(), PP.thrust_dir()

    def r_of(V):
        w = V - hub
        return np.linalg.norm(w - np.outer(w @ ax, ax), axis=1)

    for pid in [k for k in parts if k.startswith("blade_")]:
        blade = [m for m, mm in parts[pid].meshes if mm in ("prop_blade", "prop_tip")]
        other = [(m, mm) for m, mm in parts[pid].meshes if mm not in ("prop_blade", "prop_tip")]
        if blade:
            bands, rest = _radial_bands(Mesh.merge(blade), r_of, PROP_BANDS, PP.PROP_R, "prop_blade")
            if rest.nf:
                bands += _blade_le_strip(rest, int(pid.split("_")[1]) - 1, PP.PROP_R - PROP_BANDS[-1][2])
            parts[pid].meshes = bands + other
    return parts


def check_materials(tol=5e-3):
    """Differences between PALETTE and model/assemble.MATERIALS (empty list = consistent; tol covers the
    8-bit rounding of the sRGB hex values of the pre-existing materials)."""
    from model.assemble import MATERIALS
    bad = []
    for k, (rgb, met, rough) in material_table().items():
        if k not in MATERIALS:
            bad.append(f"{k}: missing from MATERIALS")
            continue
        r2, m2, g2 = MATERIALS[k][:3]
        if max(abs(a - b) for a, b in zip(rgb, r2[:3])) > tol or abs(met - m2) > 1e-6 or abs(rough - g2) > 1e-6:
            bad.append(f"{k}: palette {rgb} {met} {rough} vs MATERIALS {r2} {m2} {g2}")
    return bad
