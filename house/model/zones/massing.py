"""Placeholder massing (pipeline test)."""
from model.kit import Geo, Part


def build():
    g = Geo()
    g.box('siding_lap', (0.3, 4.0, 0.0), (20.5, 18.6, 7.9))
    g.box('siding_lap', (0.0, 0.0, 0.0), (7.1, 6.2, 3.7))
    return [Part('massing_test', g)]
