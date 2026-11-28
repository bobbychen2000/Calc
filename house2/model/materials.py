"""Plain PBR factors written into the GLB (a fallback for other glTF viewers): the web viewer replaces every
material by NAME with its own library (web/viewer/materials.js LIBRARY).  Names used by the builders must exist
in both tables; build.py reports any that do not."""
MATERIALS = {
    'siding_lap': dict(color=(0.87, 0.86, 0.83), roughness=0.72),
    'siding_shingle': dict(color=(0.18, 0.21, 0.26), roughness=0.85),        # grey cedar shingle (the siding swatch's mean, p21 / hero)
    'siding_bb': dict(color=(0.87, 0.86, 0.83), roughness=0.75),
    'trim_white': dict(color=(0.90, 0.89, 0.86), roughness=0.6),
    'soffit_white': dict(color=(0.81, 0.80, 0.77), roughness=0.8),
    'roof_seam': dict(color=(0.024, 0.028, 0.036), roughness=0.42, metallic=0.75),
    'roof_shingle': dict(color=(0.15, 0.15, 0.155), roughness=0.95),
    'roof_flat': dict(color=(0.042, 0.043, 0.047), roughness=0.9),
    'gutter_dark': dict(color=(0.014, 0.016, 0.018), roughness=0.5, metallic=0.6),
    'frame_black': dict(color=(0.009, 0.009, 0.010), roughness=0.5, metallic=0.2),
    'glass': dict(color=(0.012, 0.023, 0.033), roughness=0.06),
    'door_navy': dict(color=(0.012, 0.016, 0.033), roughness=0.45),
    'door_garage': dict(color=(0.88, 0.87, 0.84), roughness=0.6),
    'door_wood': dict(color=(0.105, 0.030, 0.014), roughness=0.55),
    'metal_awning': dict(color=(0.019, 0.021, 0.024), roughness=0.45, metallic=0.7),
    'chimney_white': dict(color=(0.87, 0.86, 0.83), roughness=0.75),
    'chimney_cap': dict(color=(0.018, 0.020, 0.023), roughness=0.45, metallic=0.7),
    'stone_veneer': dict(color=(0.19, 0.16, 0.12), roughness=0.9),         # piers / chimneys: grey-brown (veneer swatch mean)
    'bluestone': dict(color=(0.49, 0.47, 0.43), roughness=0.8),            # full-range flagstone (flagstone swatch mean)
    'paver_drive': dict(color=(0.25, 0.24, 0.22), roughness=0.9),
    'concrete': dict(color=(0.49, 0.47, 0.42), roughness=0.9),
    'coping': dict(color=(0.69, 0.66, 0.58), roughness=0.8),
    'pool_tile': dict(color=(0.028, 0.115, 0.275), roughness=0.3),
    'pool_water': dict(color=(0.041, 0.47, 0.67), roughness=0.05, alpha=0.86),
    'pergola_metal': dict(color=(0.044, 0.047, 0.051), roughness=0.5, metallic=0.5),
    'fence_wood': dict(color=(0.32, 0.10, 0.034), roughness=0.85),
    'lawn': dict(color=(0.078, 0.195, 0.025), roughness=1.0),
    'mulch': dict(color=(0.10, 0.042, 0.019), roughness=1.0),
    'soil': dict(color=(0.068, 0.045, 0.030), roughness=1.0),
    'ground_far': dict(color=(0.16, 0.20, 0.13), roughness=1.0),
    'asphalt': dict(color=(0.07, 0.07, 0.074), roughness=0.95),
    'light_fixture': dict(color=(0.007, 0.008, 0.008), roughness=0.5, metallic=0.4),
    'light_glow': dict(color=(1.0, 0.88, 0.62), roughness=0.4, emissive=(1.0, 0.7, 0.35)),
    'solar': dict(color=(0.004, 0.005, 0.008), roughness=0.25, metallic=0.3),
    'skylight_glass': dict(color=(0.34, 0.45, 0.54), roughness=0.08),
    'foliage': dict(color=(0.05, 0.14, 0.023), roughness=0.9),
    'foliage_dark': dict(color=(0.025, 0.068, 0.016), roughness=0.9),
    'foliage_gold': dict(color=(0.69, 0.38, 0.012), roughness=0.9),
    'foliage_red': dict(color=(0.37, 0.023, 0.012), roughness=0.9),
    'bark': dict(color=(0.11, 0.087, 0.061), roughness=1.0),
    'furniture_dark': dict(color=(0.034, 0.037, 0.042), roughness=0.7),
    'furniture_wood': dict(color=(0.25, 0.10, 0.037), roughness=0.7),
    'cushion': dict(color=(0.175, 0.16, 0.165), roughness=0.95),           # taupe-grey canvas (p22)
    'neighbor_wall': dict(color=(0.46, 0.49, 0.51), roughness=0.9),
    'neighbor_roof': dict(color=(0.107, 0.109, 0.117), roughness=0.95),
    'interior_glow': dict(color=(1.0, 0.76, 0.43), roughness=1.0, emissive=(1.0, 0.58, 0.25)),
}


def register(name, **spec):
    """Add (or override) a material from a builder module: register('brass', color=(..), roughness=.., metallic=..)."""
    MATERIALS[name] = dict(spec)
    return name
