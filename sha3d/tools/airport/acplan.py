"""Simplified aircraft planforms for stand checks (task A2). Dimensions are public type figures (length, span, fuselage
width; Wikipedia / manufacturer brochures, rounded) [inf: the wing / tail layout is a generic proportional sketch, not a
manufacturer drawing]. Coordinates: u = metres ahead of the nose tip (so the aircraft occupies u in [-L, 0]),
v = metres to the right."""
import math

# class -> (reference type, length m, span m, fuselage width m, wing sweep deg) ; spans of the class limits as sfo3d
# (js/live/airport.js CLASS_MAX: B 28.5, C 36.5, CL 41.1, D 52, E 61, EL 65.5, F 80; lengths 37/45/54.5/62/68/77/80)
CLASS_MAX = {'B': (28.5, 37), 'C': (36.5, 45), 'CL': (41.1, 54.5), 'D': (52, 62), 'E': (61, 68), 'EL': (65.5, 77),
             'F': (80, 80)}
ORDER = ['B', 'C', 'CL', 'D', 'E', 'EL', 'F']
CLS_REF = {   # largest type of each class expected at SHA (reference planform)
    'B': ('AJ27', 33.5, 27.3, 3.1, 25),     # COMAC C909 (ARJ21-700)
    'C': ('A321', 44.5, 35.8, 3.95, 25),    # A321 (sharklets); A320 / B738 / C919 are shorter, same span class
    'CL': ('B753', 54.4, 41.1, 3.76, 25),   # 757-300 with winglets
    'D': ('B763', 54.9, 47.6, 5.03, 31),    # 767-300ER
    'E': ('A333', 63.7, 60.3, 5.64, 30),    # A330-300
    'EL': ('B77W', 73.9, 64.8, 6.2, 31.6),  # 777-300ER
    'F': ('B748', 76.3, 68.4, 6.5, 37.5),   # 747-8 (AIP: stand 248 is the B747-8 stand)
}
# templates for imagery fits (name, length, span, width, sweep)
TEMPLATES = [
    ('B', 33.5, 27.3, 3.1, 25), ('C38', 38.0, 35.8, 3.95, 25), ('C44', 44.5, 35.8, 3.95, 25),
    ('D', 54.9, 47.6, 5.03, 31), ('E', 63.7, 60.3, 5.64, 30), ('EL', 73.9, 64.8, 6.2, 31.6), ('F', 76.3, 68.4, 6.5, 37.5),
]
TEMPLATE_CLASS = {'B': 'B', 'C38': 'C', 'C44': 'C', 'D': 'D', 'E': 'E', 'EL': 'EL', 'F': 'F'}


def planform(L, span, w, sweep):
    """list of polygons (each a list of (u, v)) in nose-tip coordinates"""
    hw = w / 2
    fus = [(0, -hw * 0.6), (-0.06 * L, -hw), (-0.80 * L, -hw), (-L, -hw * 0.3), (-L, hw * 0.3), (-0.80 * L, hw),
           (-0.06 * L, hw), (0, hw * 0.6)]
    le_root = -0.36 * L; c_root = 0.17 * L; c_tip = 0.045 * L
    t = math.tan(math.radians(sweep))
    half = span / 2
    polys = [fus]
    for s in (-1, 1):
        tip_le = le_root - (half - hw) * t
        polys.append([(le_root, s * hw), (tip_le, s * half), (tip_le - c_tip, s * half), (le_root - c_root, s * hw)])
        # horizontal tail
        ht_half = 0.17 * span; ht_root = -0.86 * L; ht_c = 0.07 * L
        polys.append([(ht_root, s * hw * 0.7), (ht_root - ht_half * t, s * ht_half),
                      (ht_root - ht_half * t - 0.4 * ht_c, s * ht_half), (ht_root - ht_c, s * hw * 0.7)])
    return polys


def class_planform(cls):
    _, L, span, w, sw = CLS_REF[cls]
    return planform(L, span, w, sw)


def class_of(span, length):
    for c in ORDER:
        sp, L = CLASS_MAX[c]
        if span <= sp + 0.01 and length <= L + 0.01:
            return c
    return 'F'


def icao_clearance(span):
    """ICAO Annex 14 Vol I 3.13.6 aircraft-stand clearance by code letter (from memory, as sfo3d build_stands.py cites
    ICAO Doc 9157 Part 2 3.4.4): code A/B 3.0 m, C 4.5 m, D/E/F 7.5 m [inf]"""
    return 3.0 if span < 24 else 4.5 if span < 36 else 7.5
