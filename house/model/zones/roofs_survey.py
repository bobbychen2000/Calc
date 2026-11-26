"""Roof planes straight from the roof survey's measured outlines (a first, automatic white model of the roofs:
the massing zone replaces it once the planes are cleaned up)."""
import numpy as np

from model import survey
from model.kit import Geo, Part
from model.massing_kit import RoofPlane, roof_planes


def material(e):
    t = survey.text(e).lower()
    if 'membrane' in t or 'flat roof' in t or "'flat'" in t:
        return 'roof_flat'
    if 'shingle' in t:
        return 'roof_shingle'
    if 'seam' in t or 'metal' in t:
        return 'roof_seam'
    return 'roof_shingle'


def planes():
    out = []
    for e in survey.elements('roof', 'roof_plane', has_xyz=True):
        p = survey.xyz(e)
        if len(p) >= 3:
            out.append(RoofPlane(e['id'], p, material(e)))
    return out


def build():
    g = Geo()
    ps = planes()
    roof_planes(g, ps)
    for p in ps:
        print('   %-34s %-12s pitch %5.1f  z %.2f..%.2f  %d pts' % (p.name, p.mat, p.pitch, p.pts[:, 2].min(), p.pts[:, 2].max(), len(p.pts)))
    return [Part('roofs_survey', g)]
