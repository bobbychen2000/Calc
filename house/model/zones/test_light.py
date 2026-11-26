"""Lighting test scene: a white house-like block with a porch (posts + roof), an overhang and a fence on a lawn."""
from model.kit import Geo, Part

VIEWS = {'a': dict(label='A', pos=(-9.0, -13.0, 5.0), target=(4.0, 3.0, 1.6), fov=42)}


def build():
    g = Geo()
    g.box('lawn', (-30, -30, -0.2), (40, 40, 0.0), faces='Z')
    g.box('siding_lap', (0, 0, 0), (9, 7, 5.6))
    g.box('roof_shingle', (-0.6, -0.6, 5.6), (9.6, 7.6, 5.85))           # flat roof with an overhang
    g.box('bluestone', (0.5, -3.0, 0.0), (6.5, 0.0, 0.45))                # porch floor
    g.box('roof_seam', (0.2, -3.3, 2.9), (6.8, 0.0, 3.1))                 # porch roof
    for x in (0.7, 2.6, 4.4, 6.3):
        g.box('trim_white', (x - 0.14, -2.9, 0.45), (x + 0.14, -2.62, 2.9))
    g.box('frame_black', (2.9, -0.03, 0.45), (4.1, 0.0, 2.9))             # a door
    g.box('fence_wood', (11.0, -6.0, 0.0), (11.1, 8.0, 2.0))
    g.box('siding_lap', (12.5, 1.0, 0.0), (16.0, 5.0, 3.0))               # a second block: a gap in shade
    return [Part('light_test', g)]
