"""Brand livery definitions for the livery painter (tools/liveries/paint.py).

Each livery = metadata (brand code, name, livery version, references with URLs, colours with provenance) + a paint
function that draws the livery on a Canvas in side-view terms. Layouts are measured on the official reference named
in `refs` (fractions of the fuselage length / section, so they carry over between types); colours are official brand
values where the airline publishes them, else measured on the official reference image (`measured:` + the image), else
marked `approx` (unverified). Trademarks belong to their owners; titles and symbols are re-drawn (tools/liveries/art.py,
open fonts), non-commercial depiction.

Canvas coordinates: s = station aft of the nose (m), sn = s / L, y height (m), eta = (y - section centre) / section half
height (-1 keel, +1 crown), c.winY = cabin window centre line, c.H = cabin section height, c.doors = passenger door
centres (TYPES doors of the rendered type), c.fin (fu 0 LE .. 1 TE, fv 0 root .. 1 tip).
"""
import numpy as np
import art
from fonts import font
from paint import text_image

LIVERIES = {}


def livery(code, **meta):
    def reg(fn):
        LIVERIES[code] = dict(code=code, paint=fn, **meta); return fn
    return reg


def title_box(c, text_img, height, s0, yc, mode='text', where=None):
    c.decal(text_img, s0, yc, height, mode=mode, where=c.fuselage() if where is None else where)


# ================================================================================================ United (2019 "blue")
UA = dict(rhapsody='#0B233E', united='#0033A0', gray='#D3D4D0', sky='#6CB2E2', white='#F7F8F8')
UA_REFS = [
    'https://united.mediaroom.com/2019-04-24-Out-with-the-Gold-in-with-the-Blue-United-Airlines-Unveils-its-Next-Fleet-Paint-Design',
    'https://mma.prnewswire.com/media/876537/United_Livery_Graphic_pdf.jpg?p=original (United livery graphic, PDF: colour swatches, 737-800 side view)',
]
UA_SWOOP = [(0.0, -1.0), (0.046, -0.97), (0.079, -0.60), (0.111, -0.47), (0.162, -0.38), (0.195, -0.35), (0.279, -0.31), (0.40, -0.42),
            (0.532, -0.57), (0.616, -0.58), (0.699, -0.46), (0.783, -0.36), (0.823, -0.25), (0.866, 0.0), (0.905, 0.55), (0.93, 1.05), (1.0, 1.5)]


def _united(c, express=False):
    c.paint(1.0, UA['white'])
    fus = c.fuselage()
    sw = c.curve(UA_SWOOP)
    c.below(sw, UA['gray'], where=fus)
    c.band(sw + 0.0, 0.10 * c.H / 3.9, UA['rhapsody'], where=fus)
    # wordmark: United Blue, 0.335 x cabin height, centred 0.2 m (737) above the window line, starting 1.7 m (737) aft of door 1
    k = c.H / 3.9
    f = font('Montserrat', 800)
    if express:
        img = text_image('UNITED', f, 400, UA['united'], spacing=0.16, stretch=1.08)
        h = 0.30 * c.H
        s0 = c.doors[0] + 1.3 * k
        title_box(c, img, h, s0, c.winY + 0.2 * k)
        w = h * img.size[0] / img.size[1]
        img2 = text_image('EXPRESS', f, 400, UA['united'], spacing=0.16, stretch=1.08)
        title_box(c, img2, h * 0.42, s0 + w + 0.5 * k, c.winY + 0.2 * k - 0.29 * h)
    else:
        img = text_image('UNITED', f, 400, UA['united'], spacing=0.16, stretch=1.08)
        title_box(c, img, 0.335 * c.H, c.doors[0] + 1.7 * k, c.winY + 0.2 * k)
    # tail: blue gradient, lighter toward the tip (stops measured on the official graphic: fv 0.5 #002A86 .. tip #0872C6),
    # globe low on the fin (fu 0.59, fv 0.10, d = 0.96 fin h)
    fin = c.fin_proper()
    if c.fin is not None:
        c.gradient([(0.0, UA['united']), (0.3, UA['united']), (0.5, '#002A86'), (0.75, '#0048B2'), (1.0, '#0872C6')], c.fv, where=fin)
        c.fin_decal(art.united_globe(1024, bg=UA['united'], tile=UA['sky']), 0.59, 0.10, 0.96, where=fin)
    c.engines(UA['united'])
    c.tips(UA['united'])
    c.hstab('#DADCDE')
    c.pylons('#E4E6E8')


@livery('UAL', name='United Airlines', version='2019 "blue" livery (Rhapsody Blue swoop, Runway Gray belly, globe tail)', since=2019,
        refs=UA_REFS, colors={k: (v, 'official: United livery graphic PDF swatch' if k != 'white' else 'approx') for k, v in UA.items()})
def united(c):
    _united(c)


@livery('UAL-X', name='United Express', version='2019 livery with UNITED EXPRESS titles', since=2019,
        refs=UA_REFS + ['layout of the EXPRESS title: approx (no official side view of a regional jet found yet)'],
        colors={k: (v, 'official (United livery graphic PDF)') for k, v in UA.items()})
def united_express(c):
    _united(c, express=True)
