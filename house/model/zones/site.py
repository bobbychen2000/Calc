"""Ground: placeholder slab until the lot plan is in."""
from model.kit import Geo, Part


def build():
    g = Geo()
    g.box('lawn', (-12, -14, -0.3), (40, 52, 0.0), faces='Z')
    return [Part('ground', g, group='site')]
