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
        refs=UA_REFS, colors={k: (v, 'official: United livery graphic PDF swatch' if k != 'white' else 'approx') for k, v in UA.items()},
        types=['A319', 'A320', 'A21N', 'B38M', 'B39M', 'B738', 'B739', 'B752', 'B753', 'B763', 'B764', 'B788', 'B789', 'B78X'],
        runtime=dict(top='#F7F8F8', belly='#D3D4D0', tail='#0033A0', tail2='#6CB2E2', eng='#0033A0', stripe='#0B233E', bellyLine=-0.45),
        status='layout measured on the official United livery graphic (737-800); other types scaled by fuselage length')
def united(c):
    _united(c)


@livery('UAL-X', name='United Express', version='2019 livery with UNITED EXPRESS titles', since=2019,
        refs=UA_REFS + ['layout of the EXPRESS title: approx (no official side view of a regional jet found yet)'],
        colors={k: (v, 'official (United livery graphic PDF)') for k, v in UA.items()},
        types=['E75L', 'E170', 'CRJ2', 'CRJ7'],
        runtime=dict(top='#F7F8F8', belly='#D3D4D0', tail='#0033A0', tail2='#6CB2E2', eng='#0033A0', stripe='#0B233E', bellyLine=-0.45),
        status='2019 design on regional jets (United release: applied to regional aircraft); EXPRESS title placement approx')
def united_express(c):
    _united(c, express=True)


# ================================================================================================ helpers
def base(c, color):
    c.paint(1.0, color)


def belly(c, pts, color, key='cabin', line=None, line_w=0.0):
    """colour below a smooth curve (control points (sn, eta)) on the body, optional line along the boundary"""
    y = c.curve(pts, key)
    c.below(y, color, where=c.fuselage())
    if line: c.band(y, line_w * c.H / 3.9, line, where=c.fuselage())
    return y


def fin_all(c, color, dorsal=True):
    c.paint((c.finzone() if dorsal else c.fin_proper()).astype(float), color)


def title(c, text, fam, weight, color, h_frac, s0, dy=0.0, spacing=0.05, stretch=1.0, italic=False, shear=0.0, anchor='start', where=None):
    """title `h_frac` x cabin height tall (cap height box), starting at station s0 (m), centred dy x H above the windows"""
    img = text_image(text, font(fam, weight, italic), 420, color, spacing=spacing, stretch=stretch, italic_shear=shear)
    h = h_frac * c.H
    c.decal(img, s0, c.winY + dy * c.H, h, mode='text', where=c.fuselage() if where is None else where, s_anchor=anchor)
    return h * img.size[0] / img.size[1]


def d1(c, k=0.0):
    """station of door 1 + k cabin heights"""
    return c.doors[0] + k * c.H


# ================================================================================================ United 2010 "Globe" (legacy variant)
@livery('UAL-G', name='United Airlines (2010-2019 "Globe" livery)', version='post-merger livery: white top, grey belly, gold/blue cheatline, gold globe on a blue tail', since=2010,
        refs=['FlightGear 737-800 UAL.png (GPL-2.0, FGMEMBERS/737-800 @9126249) as layout reference',
              'https://www.norebbo.com/united-airlines-livery/ (profile 737-900ER, reference only)'],
        colors=dict(blue=('#0E2D6E', 'approx'), gold=('#B8904F', 'approx'), gray=('#C5C8CC', 'approx')),
        types=['B738', 'B739', 'A319', 'A320'],
        runtime=dict(top='#F5F6F6', belly='#C5C8CC', tail='#0E2D6E', tail2='#B8904F', eng='#C5C8CC', stripe='#B8904F', bellyLine=-0.35),
        status='legacy variant (still on part of the fleet; no per-tail list, liveries.md §3.1): used only by per-registration override')
def united_globe(c):
    base(c, '#F5F6F6')
    y = belly(c, [(0, -1.2), (0.05, -0.85), (0.15, -0.55), (0.6, -0.52), (0.85, -0.4), (0.95, 0.2), (1.0, 0.6)], '#C5C8CC')
    c.band(y + 0.035 * c.H, 0.022 * c.H, '#B8904F', where=c.fuselage())
    c.band(y + 0.012 * c.H, 0.012 * c.H, '#0E2D6E', where=c.fuselage())
    title(c, 'UNITED', 'Montserrat', 800, '#0E2D6E', 0.17, d1(c, 0.55), dy=0.2, spacing=0.3)
    fin = c.fin_proper()
    fin_all(c, '#0E2D6E', dorsal=False)
    if c.fin is not None:
        c.fin_decal(art.united_globe(1024, bg='#0E2D6E', tile='#B8904F', ring='#FFFFFF'), 0.62, 0.12, 0.95, where=fin)
    c.engines('#C5C8CC'); c.tips('#0E2D6E'); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


# ================================================================================================ Delta
DL = dict(blue='#003366', red='#C01933', light='#E01933', dark='#991933', white='#F7F8F8')
DL_REFS = ['https://news.delta.com/delta-air-lines-logos-and-brand-guidelines (Delta Blue #003366, Delta Red #C01933, official palette image)',
           'https://waatbp.oneclub.org/wp-content/uploads/2024/08/Delta_Brand_Guidelines.pdf p.32 (Light Red #E01933, Dark Red #991933; third-party host)',
           'https://news.delta.com/mediakit/airbus-a321neo (official photos, A321neo N501DA: layout)',
           'https://deltamuseum.org/research/history/delta-brand/aircraft-livery/mainline-livery-1029-present (white DELTA title on the blue belly since May 2015)',
           'https://www.norebbo.com/delta-airlines-livery/ (A350-900 and ERJ-175 profiles; layout reference only)']
DL_BELLY = [(0.0, -1.3), (0.03, -0.95), (0.08, -0.78), (0.18, -0.64), (0.5, -0.62), (0.72, -0.66), (0.8, -0.78), (0.86, -1.0), (0.9, -1.5)]


def delta_widget(n=512, light=DL['light'], dark=DL['dark']):
    """Delta's widget as a two-tone triangle (left half light red, right half dark red), re-drawn"""
    return art.poly_image([([(0.5, 0.0), (0.0, 1.0), (0.5, 0.78)], light), ([(0.5, 0.0), (0.5, 0.78), (1.0, 1.0)], dark)], n, aspect=1.12)


def _delta(c, connection=False):
    base(c, DL['white'])
    belly(c, DL_BELLY, DL['blue'])
    # title: widget + DELTA above the windows, starting ~1.5 m (737) aft of door 1
    k = c.H / 3.9
    s0 = d1(c, 0.38)
    wimg = delta_widget()
    hW = 0.19 * c.H
    c.decal(wimg, s0, c.winY + 0.17 * c.H, hW, mode='mirror', where=c.fuselage())
    w = title(c, 'DELTA', 'Montserrat', 700, DL['blue'], 0.135, s0 + hW * 1.25, dy=0.165, spacing=0.34)
    if connection:
        title(c, 'CONNECTION', 'Montserrat', 600, DL['blue'], 0.06, s0 + hW * 1.25 + 0.02 * c.H, dy=0.02, spacing=0.3)
    # tail: navy with the widget (light red top face, dark red and red lower faces, navy V)
    fin = c.finzone()
    fin_all(c, DL['blue'])
    if c.fin is not None:
        c.poly([(0.02, 0.73), (1.08, 0.73), (1.08, 0.56), (0.62, 0.37), (0.13, 0.47)], DL['light'], 'fin', where=fin)
        c.poly([(0.13, 0.47), (0.58, 0.37), (0.64, -0.3), (0.26, -0.3)], DL['dark'], 'fin', where=fin)
        c.poly([(0.66, 0.36), (1.08, 0.54), (1.08, -0.3), (0.73, -0.3)], DL['red'], 'fin', where=fin)
        c.poly([(0.58, 0.37), (0.66, 0.36), (0.73, -0.3), (0.64, -0.3)], DL['blue'], 'fin', where=fin)
        c.poly([(0.62, 0.37), (1.08, 0.56), (1.08, 0.50), (0.66, 0.33)], DL['blue'], 'fin', where=fin)
    c.engines(DL['blue']); c.tips(DL['blue']); c.hstab('#DADCDE'); c.pylons('#E4E6E8'); c.gear_doors(DL['blue'])


@livery('DAL', name='Delta Air Lines', version='2007 "Onward and Upward" livery (white DELTA on the belly since 2015)', since=2007,
        refs=DL_REFS, colors={k: (v, 'official' if k in ('blue', 'red') else 'official brand guide (third-party host)' if k != 'white' else 'approx') for k, v in DL.items()},
        types=['A319', 'A320', 'A321', 'A21N', 'B738', 'B739', 'B752', 'B753', 'B763', 'B764', 'BCS1', 'BCS3', 'A332', 'A333', 'A339'],
        runtime=dict(top='#F7F8F8', belly='#003366', tail='#003366', tail2='#C01933', eng='#003366', bellyLine=-0.62),
        status='layout from official photos + profile reference; belly title not drawn')
def delta(c):
    _delta(c)


@livery('DAL-C', name='Delta Connection', version='Delta livery with DELTA CONNECTION titles', since=2007,
        refs=DL_REFS, colors={k: (v, 'official' if k in ('blue', 'red') else 'approx') for k, v in DL.items()},
        types=['E75L'],
        runtime=dict(top='#F7F8F8', belly='#003366', tail='#003366', tail2='#C01933', eng='#003366', bellyLine=-0.62),
        status='layout from the ERJ-175 profile reference')
def delta_connection(c):
    _delta(c, connection=True)


# ================================================================================================ American
AA = dict(silver='#CDD1D5', title='#36495A', blue='#0078D2', red='#C30019', sky='#4DB5E6', white='#F4F5F6', navy='#2B3D52')
AA_REFS = ['https://news.aa.com/news/news-details/2013/American-Airlines-Debuts-New-Modern-Look/default.aspx (silver mica, striped tail, flight symbol; photo s202.q4cdn.com/986123435/files/doc_news/2013/01/1/37446.jpg)',
           'https://simpleflying.com/american-airlines-updated-livery-many-unaware/ (2021 Silver Eagle grey paint)',
           'https://www.norebbo.com/american-airlines-livery/ (737-800 and ERJ-175 profiles; layout reference only)']


def aa_symbol(n=512):
    """American's flight symbol, simplified: red lower wing, blue upper wing with a sky-blue tip (re-drawn)"""
    return art.poly_image([([(0.05, 1.0), (0.42, 0.28), (0.62, 0.28), (0.36, 1.0)], AA['red']),
                           ([(0.42, 0.28), (0.66, 0.0), (0.98, 0.0), (0.62, 0.28)], AA['blue']),
                           ([(0.66, 0.0), (0.80, 0.0), (0.70, 0.12)], AA['sky'])], n, aspect=0.9)


def aa_stripes(c, where):
    """tail stripes: horizontal bands in side view (pitch 0.11 x fin height, white separators); blue ahead of a line from
    the fin tip (fu 0.6) to the root (fu 0.35), red behind it and on the aft fuselage"""
    if c.fin is None: return
    F = c.fin; Hf = F['yT'] - F['yR']; p = 0.11 * Hf; y0 = F['yR']
    f = np.mod((c.y - y0) / p, 1.0)
    stripe = (f > 0.30).astype(float)
    blue = c.fin_proper() & (c.fu < 0.35 + 0.25 * c.fv)
    c.paint(where.astype(float), '#E9EBED')
    c.paint(stripe * (where & ~blue), AA['red'])
    c.paint(stripe * (where & blue), '#1E56A8')
    c.paint(stripe * (where & blue) * (np.mod((c.y - y0) / p, 1.0) > 0.78), '#4A8AD8')


def _american(c, eagle=False):
    base(c, AA['silver'])
    s0 = d1(c, 0.3)
    hs = 0.40 * c.H
    c.decal(aa_symbol(), s0, c.winY + 0.02 * c.H, hs, mode='mirror', where=c.fuselage())
    title(c, 'American Eagle' if eagle else 'American', 'Montserrat', 500, AA['title'], 0.34 if not eagle else 0.26, s0 + 0.75 * hs, dy=0.02, spacing=0.0)
    fin = c.finzone()
    if c.fin is not None:
        sle0 = np.polyval(c.fin['le'], c.fin['yR'])
        # the stripe field: the fin and the aft fuselage behind a line from the fin leading edge root down to the tail cone
        aft = c.fuselage() & (c.s > sle0 - 0.3 * c.H + (c.ycM + c.hhM - c.y) * 1.2) & (c.y > c.ycM + 0.2 * c.hhM)
        aa_stripes(c, (c.fin_proper() | aft))
    c.engines(AA['silver'], lip='#B9BDC2'); c.tips(AA['silver']); c.hstab(AA['silver']); c.pylons(AA['silver'])


@livery('AAL', name='American Airlines', version='2013 livery, 2021 Silver Eagle paint', since=2013, refs=AA_REFS,
        colors=dict(silver=(AA['silver'], 'measured: official 2013 photo (37446.jpg), fuselage mid tone'), title=(AA['title'], 'approx'), blue=(AA['blue'], 'third-party (AA advertising guideline copy): unverified'),
                    red=(AA['red'], 'measured: official 2013 photo (flight symbol) #B81316, brightened; approx'), sky=(AA['sky'], 'approx')),
        types=['A319', 'A320', 'A321', 'A21N', 'B738', 'B38M', 'B788', 'B789'],
        runtime=dict(top='#CDD1D5', belly='#CDD1D5', tail='#0078D2', tail2='#C30019', eng='#CDD1D5'),
        status='layout from the official 2013 photo + profile reference; flight symbol simplified')
def american(c):
    _american(c)


@livery('AAL-E', name='American Eagle', version='American 2013 livery with American Eagle titles', since=2013, refs=AA_REFS,
        colors=dict(silver=(AA['silver'], 'measured (see AAL)')), types=['E75L'],
        runtime=dict(top='#CDD1D5', belly='#CDD1D5', tail='#0078D2', tail2='#C30019', eng='#CDD1D5'),
        status='layout from the ERJ-175 profile reference')
def american_eagle(c):
    _american(c, eagle=True)


# ================================================================================================ Alaska
AS = dict(midnight='#01285F', atlas='#0060BE', breeze='#1592C9', green='#8DBB5A', white='#F6F7F7')
AS_REFS = ['FlightGear 737-800 Models/Liveries-800/N563AS.png (GPL-2.0, github.com/FGMEMBERS/737-800 @9126249): fin of the 737 bakes',
           'https://news.alaskaair.com/alaska-airlines/about-brand-refresh/ (2016 refresh: tropical green, breeze, midnight, atlas, calm; official render 8697_ak_hero_plane_16x9 of N563AS: layout and measured colours)',
           'https://news.alaskaair.com/destinations/alaska-airlines-continues-international-expansion-with-new-flights-to-london-and-reykjavik-from-seattle-with-a-first-look-at-our-new-global-experience/ (narrow-body livery stays)']


def alaska_face(n=1024):
    """the Alaska Native portrait of the tail, simplified (re-drawn): fur ruff of the parka hood (light wisps over the
    top and sides), face in white with midnight shading, eyes, nose and a broad smile; the hood is the fin colour"""
    import math
    wisps = []
    for i in range(22):
        a = math.radians(-120 + 240 * i / 21)
        x, y = 50 + 40 * math.sin(a), 60 - 44 * math.cos(a)
        wisps.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="3.2" ry="9" transform="rotate({math.degrees(a):.0f} {x:.1f} {y:.1f})" fill="#DDEBF5"/>')
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">{''.join(wisps)}
<path d="M50 26 C70 26 79 44 78 62 C77 86 65 102 50 102 C35 102 23 86 22 62 C21 44 30 26 50 26 Z" fill="#FFFFFF"/>
<path d="M22 60 C24 76 30 90 44 100 C34 96 26 86 23 74 Z" fill="{AS['midnight']}"/>
<path d="M60 30 C70 34 76 46 77 58 C72 48 66 38 60 30 Z" fill="{AS['midnight']}"/>
<path d="M31 51 Q38 45 45 51 Q38 54 31 51 Z" fill="{AS['midnight']}"/>
<path d="M55 51 Q62 45 69 51 Q62 54 55 51 Z" fill="{AS['midnight']}"/>
<path d="M27 44 Q36 37 46 42" stroke="{AS['midnight']}" stroke-width="3.5" fill="none" stroke-linecap="round"/>
<path d="M54 42 Q64 37 73 44" stroke="{AS['midnight']}" stroke-width="3.5" fill="none" stroke-linecap="round"/>
<path d="M51 52 L46 69 Q51 72 56 69" stroke="{AS['midnight']}" stroke-width="3" fill="none" stroke-linecap="round"/>
<path d="M32 77 Q50 96 68 77 Q50 86 32 77 Z" fill="{AS['midnight']}"/>
<path d="M37 80 Q50 88 63 80" stroke="#FFFFFF" stroke-width="2.4" fill="none"/>
<path d="M30 70 Q33 74 36 72 M64 72 Q67 74 70 70" stroke="{AS['midnight']}" stroke-width="2" fill="none"/>
</svg>'''
    return art.svg(s, n)


FG_SRC = {'b738': ('737-800', '9126249', 'Models/Liveries-800/{}.png')}


def fg_texture(model, name):
    """a FlightGear livery texture (GPL-2.0) for a model built from that FlightGear model (same UV layout), read from the
    pinned commit of the FGMEMBERS clone in refs/cache/src/fg/ (docs/ATTRIBUTION_models.md)"""
    import subprocess, io as _io, os
    from PIL import Image
    import common
    repo, commit, pat = FG_SRC[model]
    data = subprocess.run(['git', 'show', f'{commit}:{pat.format(name)}'], cwd=os.path.join(common.ROOT, 'refs', 'cache', 'src', 'fg', repo),
                          capture_output=True, check=True).stdout
    return Image.open(_io.BytesIO(data))


def _alaska(c):
    base(c, AS['white'])
    fus = c.fuselage()
    # aft body midnight behind a sweeping boundary (from the belly behind the wing up to the fin root), bands green/breeze/atlas
    sw = [(0.55, -1.3), (0.62, -0.9), (0.70, -0.25), (0.78, 0.45), (0.84, 1.3)]
    P = np.array(sw)
    def boundary(offset):
        return [(a + offset, b) for a, b in sw]
    # region aft of the boundary (polygon closed around the aft body)
    reg = lambda off: boundary(off) + [(1.2, 2.0), (1.2, -2.0), (0.5 + off, -2.0)]
    c.poly(reg(0.0), AS['green'], 'cabin', where=fus)
    c.poly(reg(0.012), AS['breeze'], 'cabin', where=fus)
    c.poly(reg(0.026), AS['atlas'], 'cabin', where=fus)
    c.poly(reg(0.042), AS['midnight'], 'cabin', where=fus)
    # wordmark: italic, midnight, on the window line between door 1 and the wing
    title(c, 'Alaska', 'Kanit', 700, AS['midnight'], 0.42, d1(c, 0.45), dy=0.03, spacing=-0.02, italic=True)
    fin = c.finzone()
    fin_all(c, AS['midnight'])
    if c.fin is not None:
        c.poly([(-0.2, 0.05), (0.2, 0.08), (0.5, 0.35), (0.62, 0.62), (0.56, 0.62), (0.44, 0.38), (0.15, 0.13), (-0.2, 0.11)], AS['green'], 'fin', where=fin)
        c.poly([(-0.2, 0.11), (0.15, 0.13), (0.44, 0.38), (0.56, 0.62), (0.50, 0.62), (0.40, 0.42), (0.12, 0.18), (-0.2, 0.17)], AS['breeze'], 'fin', where=fin)
        c.fin_decal(alaska_face(), 0.64, 0.58, 0.8, where=c.fin_proper())
    if c.key == 'b738':
        # the 737 model is the FlightGear 737-800: its current-livery texture N563AS.png (GPL-2.0) fits the UV layout;
        # its tail (the artist's portrait) replaces the simplified one on the fin
        c.from_texture(fg_texture('b738', 'N563AS'), where=c.finzone())
    c.engines(AS['white'], lip='#B9BDC2')
    ang = c.eng_angle()
    c.paint(((c.part == 'eng') & (np.abs(ang) > 115)).astype(float), AS['midnight'])
    c.tips(AS['midnight']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


@livery('ASA', name='Alaska Airlines', version='2016 brand refresh (tail portrait, aurora sweep), also on Horizon / SkyWest E175s', since=2016, refs=AS_REFS,
        colors={k: (v, 'measured: official render 8697_ak_hero_plane (news.alaskaair.com)' if k != 'white' else 'approx') for k, v in AS.items()},
        types=['B737', 'B738', 'B739', 'B38M', 'B39M', 'A21N', 'E75L'],
        runtime=dict(top='#F6F7F7', belly='#F6F7F7', tail='#01285F', tail2='#8DBB5A', eng='#F6F7F7', stripe='#1592C9'),
        status='layout from the official render; portrait strongly simplified (re-drawn)')
def alaska(c):
    _alaska(c)


# ================================================================================================ Southwest
SW = dict(blue='#304CB2', red='#E31837', yellow='#F9B612', silver='#CCCCCC', white='#FFFFFF')
SW_REFS = ['https://investors.southwest.com/news-events/press-releases/detail/900/southwest-airlines-unveils-its-new-look-same-heart (2014 Heart livery: name on the fuselage, Heart on the belly, striped tail)',
           'https://www.dallasnews.com/business/airlines/2014/09/08/we-have-more-on-the-new-southwest-airlines-colors/ (colour names Bold Blue, Warm Red, Sunrise Yellow, Summit Silver)',
           'https://www.norebbo.com/southwest-airlines-livery/ (737-800 profile and colour chart; layout reference only)']


def _swa_bands(c, where):
    # diagonal bands parallel to the fin leading edge, sweeping from the lower aft body to the fin tip: yellow, red, blue
    if c.fin is None: return
    F = c.fin; le = F['le']
    slope = le[0]                                   # d(station)/d(height) of the fin LE
    u = c.s - slope * (c.y - F['yR'])               # station along the LE sweep
    s0 = np.polyval(le, F['yR']) - 0.62 * c.H       # yellow starts ahead of the fin LE root
    w = 0.30 * c.H
    c.paint(((u > s0) & (u <= s0 + w)) * where * 1.0, SW['yellow'])
    c.paint(((u > s0 + w) & (u <= s0 + 3.2 * w)) * where * 1.0, SW['red'])
    c.paint(((u > s0 + 3.2 * w)) * where * 1.0, SW['blue'])


@livery('SWA', name='Southwest Airlines', version='2014 "Heart" livery', since=2014, refs=SW_REFS,
        colors=dict(blue=(SW['blue'], 'third-party value for Bold Blue (PMS 2126 C): unverified'), red=(SW['red'], 'approx (Warm Red)'),
                    yellow=(SW['yellow'], 'third-party (Norebbo chart): unverified'), silver=(SW['silver'], 'approx (Summit Silver)')),
        types=['B737', 'B738', 'B38M'],
        runtime=dict(top='#304CB2', belly='#304CB2', tail='#E31837', tail2='#F9B612', eng='#304CB2'),
        status='layout from the profile reference; heart on the belly not drawn')
def southwest(c):
    base(c, SW['blue'])
    fus = c.fuselage()
    title(c, 'Southwest', 'Montserrat', 800, SW['white'], 0.46, d1(c, 0.4), dy=0.06, spacing=-0.01)
    aft = fus & (c.s > 0.62 * c.L)
    _swa_bands(c, aft | c.finzone())
    c.engines(SW['blue']); c.tips(SW['yellow']); c.hstab(SW['blue']); c.pylons(SW['silver'])


# ================================================================================================ JetBlue (2023 refresh)
JB = dict(blue='#2F3BD9', navy='#1B1F7A', mint='#6FE3E6', light='#9DB6FF', white='#FFFFFF')
JB_REFS = ['https://news.jetblue.com/latest-news/press-release-details/2023/JetBlue-Introduces-Its-Boldest-Bluest-Plane--Ever--With-Livery-Refresh-Reflecting-Its-Role-as-Industry-Disruptor/default.aspx (blue allover fuselage, tail pattern extended to body and belly, larger logo, colourful winglets)',
           'https://s202.q4cdn.com/521076508/files/design/thumbs/News/JetBlue-Mint-Livery.jpg (official photo, A321 N982JB, Mint pattern: layout and measured colours)']


def jetblue_tiles(c, where, s_start):
    """the tail pattern (rounded tiles, as on the 'Mint' A321 of the official photo) over the fin and the aft body"""
    cell = 0.62 * c.H * 0.5
    gx = np.floor((c.s - s_start) / cell); gy = np.floor((c.y - c.ycM) / cell)
    fx = (c.s - s_start) / cell - gx; fy = (c.y - c.ycM) / cell - gy
    h = (np.sin(gx * 12.9898 + gy * 78.233) * 43758.5453) % 1.0
    r = 0.28
    d = np.hypot(np.maximum(np.abs(fx - 0.5) - (0.5 - r - 0.04), 0), np.maximum(np.abs(fy - 0.5) - (0.5 - r - 0.04), 0)) - r
    tile = np.clip(0.5 - d * cell / c.tex, 0, 1) * where * (c.s > s_start)
    c.paint(tile * (h < 0.28), JB['mint'])
    c.paint(tile * ((h >= 0.28) & (h < 0.5)), JB['white'])
    c.paint(tile * ((h >= 0.5) & (h < 0.72)), JB['navy'])
    c.paint(tile * ((h >= 0.72) & (h < 0.84)), JB['light'])


@livery('JBU', name='JetBlue', version='2023 livery refresh (blue allover, tail pattern extended onto the body)', since=2023, refs=JB_REFS,
        colors={k: (v, 'measured: official photo JetBlue-Mint-Livery.jpg' if k != 'white' else 'approx') for k, v in JB.items()},
        types=['A320', 'A321', 'A21N', 'BCS3'],
        runtime=dict(top='#2F3BD9', belly='#2F3BD9', tail='#1B1F7A', tail2='#6FE3E6', eng='#2F3BD9'),
        status='the Mint tile pattern of the official photo on every airframe (patterns vary by aircraft: inf); fleet mid-transition from the white livery (inf: new livery rendered)')
def jetblue(c):
    base(c, JB['blue'])
    title(c, 'jetBlue', 'Nunito', 900, JB['white'], 0.48, d1(c, 0.45), dy=0.02, spacing=-0.01)
    fin = c.finzone()
    fin_all(c, JB['blue'])
    s_start = 0.74 * c.L
    jetblue_tiles(c, (c.fuselage() | fin), s_start)
    c.engines(JB['blue']); c.tips(JB['mint']); c.hstab(JB['blue']); c.pylons(JB['blue'])


# ================================================================================================ Frontier
FF = dict(green='#06876C', tail='#0A6B55', lime='#7AC943', white='#F6F7F7')
FF_REFS = ['https://news.flyfrontier.com/frontier-airlines-introduces-the-most-fuel-efficient-commercial-aircraft-among-any-us-airline/ (official photo 1920_a321neopic.jpg: FRONTIER title, greens measured)',
           'https://simpleflying.com/frontier-airlines-animal-tail-liveries-guide/ (animal tails per aircraft)']


def frontier_animal(n=1024):
    """a generic stylised animal (fox) for the tail: each Frontier aircraft has its own animal (not per-tail here)"""
    s = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<path d="M20 88 C22 60 34 44 50 40 L44 18 L58 34 L70 16 L70 40 C80 48 86 62 84 88 Z" fill="#D9772B"/>
<path d="M50 60 C58 58 66 62 70 70 L60 88 L42 88 Z" fill="#F4F1EA"/>
<circle cx="58" cy="50" r="3" fill="#2A2A2A"/><circle cx="72" cy="50" r="3" fill="#2A2A2A"/>
<path d="M62 62 L68 62 L65 66 Z" fill="#2A2A2A"/></svg>'''
    return art.svg(s, n)


@livery('FFT', name='Frontier Airlines', version='2014-15 livery: green FRONTIER title, animal on a green tail', since=2015, refs=FF_REFS,
        colors={k: (v, 'measured: official Frontier A321neo photo' if k != 'white' else 'approx') for k, v in FF.items()},
        types=['A320', 'A20N', 'A321', 'A21N'],
        runtime=dict(top='#F6F7F7', belly='#F6F7F7', tail='#0A6B55', tail2='#7AC943', eng='#06876C'),
        status='per-aircraft animal not modelled (a generic stylised animal on every tail)')
def frontier(c):
    base(c, FF['white'])
    title(c, 'FRONTIER', 'Montserrat', 800, FF['green'], 0.36, d1(c, 0.45), dy=0.03, spacing=0.02)
    fin = c.finzone(); fin_all(c, FF['tail'])
    c.fin_decal(frontier_animal(), 0.55, 0.45, 0.8, where=c.fin_proper())
    c.engines(FF['green']); c.tips(FF['lime']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


# ================================================================================================ Air Canada
AC = dict(black='#141414', red='#F01428', white='#F7F8F8')
AC_REFS = ['https://www.aircanada.com/content/dam/aircanada/portal/Legacy/foundation/ACF_Guidelines_en.pdf (AC Red #F01428 / PMS 1795 C, black)',
           'https://www.cbc.ca/news/business/air-canada-colours-1.3974114 (2017: tail, engines and undersides black, red maple leaf on the fin; Winkreative)',
           'https://www.norebbo.com/air-canada-livery/ (A321 profile; layout reference only)']


def ac_roundel(n=1024, ring=AC['red'], leaf=AC['red'], bg=None):
    """red ring with the maple leaf (Air Canada rondelle, re-drawn from the flag leaf)"""
    x, y = art._grid(n); px = 2.0 / n; r = np.hypot(x, y)
    ring_a = art._aa(r - 1, px) - art._aa(r - 0.9, px)
    leaf_img = np.asarray(art.maple_leaf(n, color=leaf, margin=0.28)).astype(np.float32)[..., 3] / 255
    layers = []
    if bg: layers.append((art._aa(r - 1, px), bg))
    layers += [(ring_a, ring), (leaf_img, leaf)]
    return art._rgba(layers, n, n)


def _aircanada(c, express=False):
    base(c, AC['white'])
    belly(c, [(0.0, -1.3), (0.04, -0.85), (0.1, -0.6), (0.5, -0.55), (0.8, -0.52), (0.9, -0.4), (1.0, -0.1)], AC['black'])
    w = title(c, 'AIR CANADA', 'Montserrat', 600, AC['black'], 0.17, d1(c, 0.5), dy=0.21, spacing=0.12)
    if express:
        title(c, 'EXPRESS', 'Montserrat', 600, AC['black'], 0.17, d1(c, 0.5) + w + 0.1 * c.H, dy=0.21, spacing=0.12)
    c.decal(ac_roundel(512), d1(c, 0.25), c.winY - 0.28 * c.H, 0.2 * c.H, mode='mirror', where=c.fuselage(), s_anchor='center')
    fin = c.finzone(); fin_all(c, AC['black'])
    c.fin_decal(ac_roundel(1024), 0.56, 0.5, 0.7, where=c.fin_proper())
    c.engines(AC['black']); c.tips(AC['black']); c.hstab(AC['white']); c.pylons('#E4E6E8'); c.gear_doors(AC['black'])


@livery('ACA', name='Air Canada', version='2017 livery (black tail, belly and engines; red maple-leaf rondelle)', since=2017, refs=AC_REFS,
        colors=dict(red=(AC['red'], 'official (Air Canada Foundation logo guideline)'), black=(AC['black'], 'official black, rendered as paint black'), white=(AC['white'], 'approx')),
        types=['A320', 'A321', 'B38M', 'BCS3', 'B789'],
        runtime=dict(top='#F7F8F8', belly='#141414', tail='#141414', tail2='#F01428', eng='#141414', bellyLine=-0.55),
        status='layout from the CBC description and the profile reference')
def aircanada(c):
    _aircanada(c)


@livery('ACA-X', name='Air Canada Express', version='2017 livery with AIR CANADA EXPRESS titles', since=2017, refs=AC_REFS,
        colors=dict(red=(AC['red'], 'official'), black=(AC['black'], 'official')), types=['CRJ9'],
        runtime=dict(top='#F7F8F8', belly='#141414', tail='#141414', tail2='#F01428', eng='#141414', bellyLine=-0.55),
        status='title placement approx')
def aircanada_express(c):
    _aircanada(c, express=True)


# ================================================================================================ WestJet
WS = dict(teal='#00A5A0', navy='#0C2340', blue='#1F5FA8', white='#F7F8F8', grey='#B9C0C7')
@livery('WJA', name='WestJet', version='2018 livery (teal tail with the stylised maple leaf, teal down onto the rear fuselage)', since=2018,
        refs=['https://westjet.mediaroom.com/2018-05-08-WestJet-unveils-its-Dreamliner-Spirit-of-Canada-to-the-world (livery reveal; gradual repaint)',
              'https://www.travelweek.ca/news/the-spirit-of-canada-new-look-for-westjets-livery-logo-and-cabin-interiors/ (teal extended onto the rear fuselage, leaf silhouette)',
              'https://thedesignair.net/2018/05/12/westjet-reveals-new-livery-and-impressive-787-long-haul-product/ (official press stills: logo and leaf)'],
        colors={k: (v, 'approx') for k, v in WS.items()}, types=['B737', 'B738', 'B38M', 'B789'],
        runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#00A5A0', tail2='#0C2340', eng='#F7F8F8'),
        status='layout from the descriptions and the official logo; colours approx (no official values found)')
def westjet(c):
    base(c, WS['white'])
    w = title(c, 'WESTJET', 'Montserrat', 800, WS['navy'], 0.16, d1(c, 0.5), dy=0.2, spacing=0.06)
    c.decal(art.maple_leaf(512, color=WS['teal']), d1(c, 0.5) + w + 0.05 * c.H, c.winY + 0.2 * c.H, 0.18 * c.H, mode='mirror', where=c.fuselage())
    fin = c.finzone()
    if c.fin is not None:
        sle0 = np.polyval(c.fin['le'], c.fin['yR'])
        aft = c.fuselage() & (c.s > sle0 - 0.2 * c.H + (c.ycM + c.hhM - c.y) * 0.9) & (c.y > c.ycM - 0.1 * c.hhM)
        c.paint((fin | aft).astype(float), WS['teal'])
        c.fin_decal(art.maple_leaf(1024, color=WS['navy']), 0.55, 0.55, 0.75, where=c.fin_proper())
        c.fin_decal(art.maple_leaf(1024, color=WS['blue'], margin=0.35), 0.58, 0.55, 0.75, where=c.fin_proper())
    c.engines(WS['white']); c.tips(WS['teal']); c.hstab(WS['white']); c.pylons('#E4E6E8')


# ================================================================================================ Aeromexico
AM = dict(navy='#0B2343', silver='#C5CBD3', red='#D22630', white='#F7F8F8')
def eagle_knight(n=1024):
    """the Caballero Aguila (eagle-knight head in profile) strongly simplified: silver helmet-beak, face, feathers"""
    s = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<path d="M18 30 C30 12 62 8 80 22 C88 30 86 44 78 50 L66 50 L70 60 C74 70 70 84 58 90 L30 90 C36 78 36 66 30 58 C20 52 12 42 18 30 Z" fill="#E6E9EE"/>
<path d="M18 30 L6 40 L20 42 Z" fill="#E6E9EE"/>
<path d="M40 56 C48 54 56 58 58 66 C60 74 56 82 48 86 L38 86 C42 76 42 66 40 56 Z" fill="#0B2343"/>
<circle cx="50" cy="34" r="4" fill="#0B2343"/>
<path d="M60 22 L84 18 M62 30 L88 28 M62 38 L86 40" stroke="#0B2343" stroke-width="3"/></svg>'''
    return art.svg(s, n)


@livery('AMX', name='Aeroméxico', version='Caballero Águila livery (navy tail; the 2024 updated eagle is being applied gradually)', since=2006,
        refs=['https://www.norebbo.com/aeromexico-livery/ (737-700 profile; layout reference only)',
              'https://www.breitflyte.com/post/aeromexico-unveils-new-aircraft-livery-as-part-of-90th-anniversary-celebration (2024 update, gradual: 404 at verification)'],
        colors={k: (v, 'approx') for k, v in AM.items()}, types=['B738', 'B38M', 'B39M', 'B789'],
        runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#0B2343', tail2='#C5CBD3', eng='#0B2343'),
        status='eagle-knight head strongly simplified; colours approx')
def aeromexico(c):
    base(c, AM['white'])
    title(c, 'AEROMEXICO', 'Montserrat', 700, AM['navy'], 0.16, d1(c, 0.5), dy=0.2, spacing=0.02)
    fin = c.finzone()
    if c.fin is not None:
        sle0 = np.polyval(c.fin['le'], c.fin['yR'])
        aft = c.fuselage() & (c.s > sle0 - 1.2 * c.H + (c.ycM + c.hhM - c.y) * 1.4)
        c.paint((fin | aft).astype(float), AM['navy'])
        y = c.curve([(0.25, -0.9), (0.5, -0.55), (0.7, -0.2), (0.82, 0.3)], 'cabin')
        c.band(y, 0.02 * c.H, AM['silver'], where=c.fuselage() & (c.s > 0.25 * c.L))
        c.fin_decal(eagle_knight(), 0.6, 0.62, 0.6, where=c.fin_proper())
    c.engines(AM['navy']); c.tips(AM['navy']); c.hstab(AM['white']); c.pylons('#E4E6E8')


# ================================================================================================ Hawaiian
HA = dict(purple='#4B2A7B', magenta='#C3257C', coral='#EE5A4B', lav='#8E6AAE', white='#F7F8F8', grey='#DADCE2')
def pualani(n=1024):
    """Pualani (the flower-crowned woman in profile), strongly simplified: face profile in white, dark hair, hibiscus"""
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">
<path d="M58 6 C84 10 96 34 92 60 C88 88 72 112 46 116 L40 96 C50 92 56 84 54 76 L60 70 L56 64 L62 58 L56 52 C60 44 58 34 50 30 C44 26 40 18 44 10 Z" fill="#2B1840"/>
<path d="M50 30 C58 34 60 44 56 52 L62 58 L56 64 L60 70 L54 76 C56 84 50 92 40 96 L30 116 L10 116 C22 100 26 84 24 70 C22 50 30 30 50 30 Z" fill="#FFFFFF"/>
<circle cx="78" cy="24" r="12" fill="{HA['coral']}"/><circle cx="66" cy="16" r="8" fill="{HA['coral']}"/><circle cx="86" cy="38" r="7" fill="{HA['magenta']}"/>
</svg>'''
    return art.svg(s, n)


@livery('HAL', name='Hawaiian Airlines', version='2017 livery (Pualani on a purple sunrise tail, lei flowers on the aft body)', since=2017,
        refs=['https://news.alaskaair.com/releases/hawaiian-airlines-unveils-new-brand-and-livery/ (1 May 2017: purple, fuchsia and coral; Pualani larger; lei)',
              'https://www.norebbo.com/hawaiian-airlines-livery/ (A321neo and A330-200 profiles; layout reference only)'],
        colors={k: (v, 'approx (names official: purple, fuchsia, coral)') for k, v in HA.items()}, types=['A21N', 'A332'],
        runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#4B2A7B', tail2='#C3257C', eng='#F7F8F8'),
        status='Pualani and the lei strongly simplified')
def hawaiian(c):
    base(c, HA['white'])
    title(c, 'HAWAIIAN', 'Montserrat', 700, HA['purple'], 0.15, d1(c, 0.5), dy=0.2, spacing=0.05)
    fin = c.finzone()
    if c.fin is not None:
        c.gradient([(-0.2, HA['magenta']), (0.35, HA['purple']), (1.0, '#3A1E66')], c.fv, where=fin)
        sle0 = np.polyval(c.fin['le'], c.fin['yR'])
        # lei: flowers along the aft body under the tail (magenta / purple / grey petals)
        aft = c.fuselage() & (c.s > sle0 - 1.6 * c.H) & (c.y < c.ycM + 0.4 * c.hhM)
        cell = 0.35 * c.H
        gx = np.floor(c.s / cell); gy = np.floor(c.y / cell)
        h = (np.sin(gx * 12.99 + gy * 78.23) * 43758.5) % 1.0
        fx = c.s / cell - gx - 0.5; fy = c.y / cell - gy - 0.5
        ang = np.arctan2(fy, fx); rr = np.hypot(fx, fy); petal = rr < 0.28 + 0.12 * np.cos(5 * ang)
        dens = np.clip((c.s - (sle0 - 1.6 * c.H)) / (1.6 * c.H), 0, 1)
        c.paint((aft & petal & (h < 0.45 * dens)).astype(float), HA['magenta'])
        c.paint((aft & petal & (h >= 0.45 * dens) & (h < 0.7 * dens)).astype(float), HA['lav'])
        c.fin_decal(pualani(), 0.62, 0.55, 0.85, where=c.fin_proper())
    c.engines(HA['white']); c.tips(HA['purple']); c.hstab(HA['white']); c.pylons('#E4E6E8')


# ================================================================================================ Sun Country
SY = dict(navy='#0A2A4A', orange='#F58220', yellow='#FDB813', white='#F7F8F8')
@livery('SCX', name='Sun Country Airlines', version='2018 livery (blue base, orange stripes, retained sun logo)', since=2018,
        refs=['https://www.startribune.com/first-look-at-the-new-paint-job-on-sun-country-s-airplanes/499049761 (2018 livery; not reachable at verification)'],
        colors={k: (v, 'approx') for k, v in SY.items()}, types=['B738'],
        runtime=dict(top='#0A2A4A', belly='#0A2A4A', tail='#0A2A4A', tail2='#F58220', eng='#0A2A4A'),
        status='from the text description only (no reference image fetched): approx')
def sun_country(c):
    base(c, SY['navy'])
    title(c, 'sun country', 'Montserrat', 700, SY['white'], 0.26, d1(c, 0.5), dy=0.05, spacing=0.0)
    fin = c.finzone()
    if c.fin is not None:
        for k, col in enumerate([SY['yellow'], SY['orange'], SY['orange']]):
            c.poly([(-0.3, 0.2 + 0.18 * k), (1.1, 0.5 + 0.18 * k), (1.1, 0.58 + 0.18 * k), (-0.3, 0.28 + 0.18 * k)], col, 'fin', where=fin)
        c.fin_decal(art.circle(512, color=SY['yellow']), 0.62, 0.78, 0.22, where=c.fin_proper())
    c.engines(SY['navy']); c.tips(SY['orange']); c.hstab(SY['navy']); c.pylons(SY['navy'])


# ================================================================================================ Breeze
BZ = dict(blue='#3E8EDE', navy='#1E2A69', light='#A9D4F5', white='#FFFFFF')
@livery('MXY', name='Breeze Airways', version='2021 livery (blue fuselage, navy tail with the light-blue check)', since=2021,
        refs=['https://www.airbus.com/en/newsroom/press-releases/2021-09-breeze-airways-reveals-new-a220-livery-confirms-order-for-20 (reveal, no description)',
              'https://www.norebbo.com/breeze-airways-livery/ (E190 profile and colour chart; layout reference only)'],
        colors={k: (v, 'third-party chart / approx: unverified') for k, v in BZ.items()}, types=['BCS3'],
        runtime=dict(top='#3E8EDE', belly='#3E8EDE', tail='#1E2A69', tail2='#A9D4F5', eng='#1E2A69'),
        status='layout from the profile reference')
def breeze(c):
    base(c, BZ['blue'])
    c.gradient([(0.0, '#4C9BE6'), (0.7, BZ['blue']), (1.0, '#2E62B8')], c.s / c.L, where=c.fuselage())
    title(c, 'Breeze', 'Nunito', 900, BZ['navy'], 0.3, d1(c, 0.6), dy=-0.05, spacing=0.02)
    fin = c.finzone()
    if c.fin is not None:
        sle0 = np.polyval(c.fin['le'], c.fin['yR'])
        aft = c.fuselage() & (c.s > sle0 - 0.5 * c.H + (c.ycM + c.hhM - c.y) * 0.6)
        c.paint((fin | aft).astype(float), BZ['navy'])
        c.poly([(0.05, 0.25), (0.35, 0.02), (1.0, 0.95), (0.8, 0.95), (0.35, 0.3), (0.2, 0.42)], BZ['light'], 'fin', where=fin)
    c.engines(BZ['navy']); c.tips(BZ['navy']); c.hstab(BZ['navy']); c.pylons(BZ['navy'])


# ================================================================================================ international carriers
# Most follow one pattern: white fuselage, titles over the windows forward, coloured tail with a symbol, optional belly
# colour / cheatline / aft sweep; std() builds them from a spec. Symbols are strongly simplified re-drawn marks.
def std(c, spec):
    base(c, spec.get('body', '#F7F8F8'))
    fus = c.fuselage()
    if spec.get('belly'):
        col, pts = spec['belly']; y = belly(c, pts, col)
        if spec.get('belly_line'): c.band(y, spec['belly_line'][1] * c.H, spec['belly_line'][0], where=fus)
    for col, pts, w in spec.get('cheat', []):
        c.band(c.curve(pts, 'cabin'), w * c.H, col, where=fus)
    for col, pts in spec.get('side_polys', []):
        c.poly(pts, col, 'cabin', where=fus)
    t = spec.get('title')
    if t:
        text, fam, wt, col, h = t[:5]; o = t[5] if len(t) > 5 else {}
        title(c, text, fam, wt, col, h, d1(c, o.get('k', 0.5)), dy=o.get('dy', 0.2), spacing=o.get('sp', 0.05), italic=o.get('it', False), stretch=o.get('st', 1.0))
    fin = c.finzone() if spec.get('dorsal', True) else c.fin_proper()
    if spec.get('tail'): fin_all(c, spec['tail'], dorsal=spec.get('dorsal', True))
    if spec.get('tail_grad') and c.fin is not None: c.gradient(spec['tail_grad'], c.fv, where=fin)
    if spec.get('aft') and c.fin is not None:
        col, k0, slope, ymin = spec['aft']
        sle0 = np.polyval(c.fin['le'], c.fin['yR'])
        aft = fus & (c.s > sle0 - k0 * c.H + (c.ycM + c.hhM - c.y) * slope) & (c.y > c.ycM + ymin * c.hhM)
        c.paint(aft.astype(float), col)
    for col, pts in spec.get('fin_polys', []):
        if c.fin is not None: c.poly(pts, col, 'fin', where=fin)
    if spec.get('fin_art') and c.fin is not None:
        img, fu, fv, h = spec['fin_art']; c.fin_decal(img() if callable(img) else img, fu, fv, h, where=c.fin_proper())
    if spec.get('extra'): spec['extra'](c)
    c.engines(spec.get('eng', '#F2F3F4'), lip=spec.get('lip', '#B9BDC2')); c.tips(spec.get('tips', spec.get('tail', '#DADCDE')))
    c.hstab(spec.get('hstab', '#DADCDE')); c.pylons(spec.get('pylon', '#E4E6E8'))


def reg_std(code, name, version, since, refs, colors, types, runtime, status, spec):
    LIVERIES[code] = dict(code=code, name=name, version=version, since=since, refs=refs, colors=colors, types=types, runtime=runtime,
                          status=status, paint=lambda c, s=spec: std(c, s))


def svg_mark(body, vb='0 0 100 100'):
    return lambda n=1024: art.svg(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{body}</svg>', n)


APPROX = 'approx (no official value found; from the reference image)'
NOR = 'https://www.norebbo.com/{}-livery/ (profile drawing; layout reference only)'

# ---- Cathay Pacific (2015 refresh)
reg_std('CPA', 'Cathay Pacific', '2015 livery (all-green tail with white brushwing, light grey band, name above the windows)', 2015,
        ['https://news.cathaypacific.com/new-era-begins-for-cathay-pacific-as-airline-unveils-changes-to-aircraft-livery-141164 (1 Nov 2015: "Cathay Pacific green, grey and white")', NOR.format('cathay-pacific')],
        dict(green=('#006564', APPROX), grey=('#C9CED1', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#C9CED1', tail='#006564', tail2='#FFFFFF', eng='#F2F3F4', bellyLine=-0.35), 'brushwing simplified',
        dict(belly=('#C9CED1', [(0, -1.2), (0.05, -0.6), (0.2, -0.35), (0.8, -0.35), (0.92, -0.1), (1, 0.3)]),
             title=('CATHAY PACIFIC', 'Libre Baskerville', 700, '#005C5A', 0.12, dict(k=0.55, dy=0.22, sp=0.02)), tail='#006564',
             fin_art=(svg_mark('<path d="M8 70 C30 40 60 30 92 18 C70 36 52 52 40 78 C34 64 22 62 8 70 Z" fill="#FFFFFF"/>'), 0.5, 0.45, 0.7),
             eng='#F2F3F4'))

# ---- EVA Air
reg_std('EVA', 'EVA Air', '2015 update (green tail with the orange globe, darker green belly)', 2015,
        ['https://www.airlinereporter.com/2015/11/eva-air-shows-off-new-livery-vision-future/ (darker green belly, orange removed from the rudder)'],
        dict(green=('#00674F', APPROX), orange=('#F29400', APPROX)), ['B789'],
        dict(top='#F7F8F8', belly='#2E5D4B', tail='#00674F', tail2='#F29400', eng='#F2F3F4', bellyLine=-0.55), 'from the description; globe simplified',
        dict(belly=('#2E5D4B', [(0, -1.2), (0.05, -0.8), (0.2, -0.55), (0.8, -0.55), (0.92, -0.3), (1, 0.2)]),
             cheat=[('#F29400', [(0.05, -0.72), (0.2, -0.47), (0.8, -0.47), (0.92, -0.22)], 0.02)],
             title=('EVA AIR', 'Montserrat', 800, '#00674F', 0.16, dict(k=0.55, dy=0.2, sp=0.1)), tail='#00674F',
             fin_art=(lambda n=1024: art.circle(n, color='#F29400'), 0.5, 0.5, 0.45)))

# ---- China Airlines
reg_std('CAL', 'China Airlines', 'plum-blossom tail (1995 identity), white fuselage', 1995,
        ['https://www.china-airlines.com/ (brand; not fetched)'], dict(pink=('#D8567E', APPROX), violet=('#6B3E8E', APPROX), blue=('#1D3A7A', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#D8567E', eng='#F2F3F4'), 'from knowledge only: approx',
        dict(title=('CHINA AIRLINES', 'Montserrat', 700, '#1D3A7A', 0.13, dict(k=0.55, dy=0.22, sp=0.04)),
             fin_art=(svg_mark(''.join(f'<ellipse cx="{50 + 26 * np.cos(a):.1f}" cy="{50 + 26 * np.sin(a):.1f}" rx="20" ry="13" transform="rotate({np.degrees(a):.0f} {50 + 26 * np.cos(a):.1f} {50 + 26 * np.sin(a):.1f})" fill="#D8567E"/>' for a in np.linspace(0, 2 * np.pi, 5, endpoint=False) - np.pi / 2) + '<circle cx="50" cy="50" r="10" fill="#6B3E8E"/>'), 0.5, 0.52, 0.62)))

# ---- Singapore Airlines
reg_std('SIA', 'Singapore Airlines', 'midnight-blue tail with the gold Kris bird, blue and gold cheatline', 1972,
        ['https://airlinegeeks.com/2026/08/21/livery-of-the-week-singapore-airlines/ (midnight blue and gold, essentially unchanged)'],
        dict(blue=('#1A2C5B', APPROX), gold=('#F2A900', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#1A2C5B', tail2='#F2A900', eng='#F2F3F4', stripe='#1A2C5B'), 'Kris bird simplified',
        dict(cheat=[('#1A2C5B', [(0.06, -0.5), (0.2, -0.42), (0.85, -0.42), (0.95, -0.2)], 0.05), ('#F2A900', [(0.06, -0.58), (0.2, -0.5), (0.85, -0.5), (0.95, -0.28)], 0.02)],
             title=('SINGAPORE AIRLINES', 'Montserrat', 700, '#1A2C5B', 0.11, dict(k=0.55, dy=0.22, sp=0.05)), tail='#1A2C5B',
             fin_art=(svg_mark('<path d="M20 78 C34 60 50 40 78 22 C70 40 62 52 50 60 C60 58 70 60 80 66 C64 70 48 72 36 82 Z" fill="#F2A900"/>'), 0.52, 0.5, 0.72)))

# ---- Korean Air (2025 identity)
reg_std('KAL', 'Korean Air', 'new identity 11 Mar 2025: metallic sky blue, KOREAN logotype, dark-blue taegeuk', 2025,
        ['https://samchui.com/2025/03/12/korean-air-unveils-new-corporate-identity-and-aircraft-livery/', NOR.format('korean-air') + ' (colour chart: #53AAE2, #051766; third party)'],
        dict(sky=('#53AAE2', 'third-party chart (Norebbo): unverified'), navy=('#051766', 'third-party chart (Norebbo): unverified')), ['B78X', 'B789'],
        dict(top='#53AAE2', belly='#E9EDF0', tail='#53AAE2', tail2='#051766', eng='#E9EDF0', bellyLine=-0.55),
        'fleet mid-transition from the 1984 livery (new livery rendered: inf)',
        dict(body='#53AAE2', belly=('#E6EAEE', [(0, -1.3), (0.06, -0.8), (0.2, -0.6), (0.8, -0.6), (0.92, -0.35), (1, 0.1)]),
             title=('KOREAN', 'Montserrat', 800, '#051766', 0.3, dict(k=0.45, dy=0.05, sp=0.04)), tail='#53AAE2',
             fin_art=(svg_mark('<circle cx="50" cy="50" r="44" fill="none" stroke="#051766" stroke-width="7"/><path d="M50 6 C74 6 74 50 50 50 C26 50 26 94 50 94" fill="none" stroke="#051766" stroke-width="9"/>'), 0.52, 0.5, 0.62), eng='#E6EAEE'))

# ---- ANA
reg_std('ANA', 'ANA', '"Triton Blue" livery (1982)', 1982,
        ['https://www.ana.co.jp/group/en/70th/archives/ap13/', NOR.format('ana') + ' (colour palette: #29239B, #00AFE3; third party)'],
        dict(dark=('#29239B', 'third-party chart: unverified'), light=('#00AFE3', 'third-party chart: unverified')), ['B788', 'B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#29239B', tail2='#00AFE3', eng='#F2F3F4', stripe='#29239B'), 'at SFO ANA flies the 777-300ER (procedural airframe; runtime colours)',
        dict(cheat=[('#29239B', [(0.06, -0.6), (0.3, -0.5), (0.7, -0.45), (0.86, 0.1), (0.9, 0.9)], 0.06), ('#00AFE3', [(0.3, -0.62), (0.7, -0.57), (0.86, -0.05), (0.9, 0.7)], 0.03)],
             title=('ANA', 'Montserrat', 800, '#29239B', 0.13, dict(k=0.4, dy=0.22, it=True)), tail='#29239B',
             fin_polys=[('#00AFE3', [(0.8, -0.3), (1.1, -0.3), (1.1, 1.1), (0.95, 1.1)])],
             extra=lambda c: c.fin_decal(text_image('ANA', font('Montserrat', 800, True), 420, '#FFFFFF'), 0.5, 0.52, 0.2, rotate=-55)))

# ---- Japan Airlines
reg_std('JAL', 'Japan Airlines', '2011 "Tsurumaru" crane livery', 2011,
        ['https://www.japantimes.co.jp/news/2011/03/01/business/jal-revives-crane-logo-in-return-to-basics/', NOR.format('japan-airlines')],
        dict(red=('#CC0000', APPROX)), ['B788', 'B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#CC0000', eng='#F2F3F4'), 'crane circle simplified',
        dict(title=('JAPAN AIRLINES', 'Montserrat', 800, '#1A1A1A', 0.15, dict(k=0.5, dy=0.2, it=True, sp=0.02)),
             fin_art=(svg_mark('<circle cx="50" cy="50" r="44" fill="#CC0000"/><path d="M50 14 C30 20 20 40 30 60 L42 50 L40 76 L50 62 L60 76 L58 50 L70 60 C80 40 70 20 50 14 Z" fill="#FFFFFF"/><circle cx="50" cy="30" r="6" fill="#CC0000"/>'), 0.55, 0.52, 0.5)))

# ---- Qantas (2016 Flying Kangaroo)
reg_std('QFA', 'Qantas', '2016 livery (red tail with the streamlined kangaroo, red wrapping onto the aft body)', 2016,
        [NOR.format('qantas') + ' (787-9 profile)'], dict(red=('#E40000', APPROX)), ['B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#E40000', tail2='#FFFFFF', eng='#F2F3F4'), 'kangaroo simplified',
        dict(title=('QANTAS', 'Montserrat', 800, '#1A1A1A', 0.16, dict(k=0.5, dy=0.2, sp=0.06)), tail='#E40000', aft=('#E40000', 0.6, -1.0, -1.0),
             fin_art=(svg_mark('<path d="M20 80 C30 60 44 50 60 46 L70 30 L74 44 C84 44 90 52 88 60 L70 58 C60 62 50 70 44 84 L36 70 Z" fill="#FFFFFF"/>'), 0.55, 0.5, 0.62)))

# ---- Philippine Airlines
reg_std('PAL', 'Philippine Airlines', 'flag-motif tail (blue and red triangles, yellow sun)', 1986,
        ['https://www.philippineairlines.com/ (brand; not fetched)'], dict(blue=('#1B3F94', APPROX), red=('#CE1126', APPROX), yellow=('#FCD116', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#1B3F94', tail2='#CE1126', eng='#F2F3F4'), 'approx; at SFO mostly the 777-300ER (procedural)',
        dict(title=('PHILIPPINE AIRLINES', 'Montserrat', 700, '#1B3F94', 0.11, dict(k=0.55, dy=0.22, sp=0.03)), tail='#F7F8F8',
             fin_polys=[('#1B3F94', [(-0.2, 0.55), (1.2, 0.55), (1.2, 1.2), (-0.2, 1.2)]), ('#CE1126', [(-0.2, -0.3), (1.2, -0.3), (1.2, 0.5), (-0.2, 0.5)]), ('#F7F8F8', [(-0.2, -0.3), (0.55, 0.52), (-0.2, 1.2)])],
             fin_art=(lambda n=1024: art.circle(n, color='#FCD116'), 0.15, 0.52, 0.18)))

# ---- Air France
reg_std('AFR', 'Air France', 'Eurowhite livery with the tricolour tail stripes', 2009,
        ['https://corporate.airfrance.com/ (brand; not fetched)'], dict(navy=('#002157', APPROX), red=('#E6192B', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#002157', eng='#F2F3F4'), 'approx',
        dict(title=('AIRFRANCE', 'Montserrat', 800, '#002157', 0.14, dict(k=0.5, dy=0.2, sp=0.08)),
             fin_polys=[('#002157', [(0.55, -0.3), (0.75, -0.3), (1.1, 0.6), (0.9, 0.6)]), ('#E6192B', [(0.8, -0.3), (0.95, -0.3), (1.2, 0.4), (1.05, 0.4)])],
             eng='#F2F3F4'))

# ---- British Airways (Chatham Dockyard)
def ba_flag(n=1024):
    """the Chatham Dockyard Union flag of the BA tail: wavy red/white/blue bands (simplified, re-drawn)"""
    s = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#FFFFFF"/>
<path d="M0 0 L100 0 L100 22 C70 32 40 18 0 30 Z" fill="#012169"/>
<path d="M0 44 C40 34 70 48 100 38 L100 56 C70 66 40 52 0 62 Z" fill="#C8102E"/>
<path d="M0 76 C40 66 70 80 100 70 L100 100 L0 100 Z" fill="#012169"/>
<path d="M0 30 C40 18 70 32 100 22 L100 28 C70 38 40 24 0 36 Z" fill="#C8102E"/></svg>'''
    return art.svg(s, n)


reg_std('BAW', 'British Airways', 'Chatham Dockyard Union-flag tail, midnight-blue belly, red speedwing', 1997,
        ['https://www.key.aero/article/how-british-airways-got-its-latest-livery', 'https://simpleflying.com/british-airways-livery-evolution/', NOR.format('british-airways') + ' (A350-1000, A380 profiles)'],
        dict(blue=('#01213F', APPROX), red=('#C8102E', APPROX)), ['A388'],
        dict(top='#F7F8F8', belly='#01213F', tail='#012169', tail2='#C8102E', eng='#01213F', bellyLine=-0.6), 'flag simplified',
        dict(belly=('#01213F', [(0, -1.3), (0.05, -0.85), (0.15, -0.62), (0.8, -0.6), (0.9, -0.5), (1, -0.2)]),
             title=('BRITISH AIRWAYS', 'Libre Baskerville', 700, '#01213F', 0.11, dict(k=0.55, dy=-0.05, sp=0.02)),
             fin_art=(ba_flag, 0.5, 0.5, 1.1), eng='#01213F', dorsal=False))

# ---- Lufthansa (2018)
def lh_crane(n=1024, fg='#FFFFFF'):
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="44" fill="none" stroke="{fg}" stroke-width="5"/>
<path d="M22 62 C34 50 44 42 52 30 C54 24 60 20 66 22 L62 28 C70 34 72 46 64 56 L80 70 L60 64 C50 70 38 70 22 62 Z" fill="{fg}"/></svg>'''
    return art.svg(s, n)


reg_std('DLH', 'Lufthansa', '2018 brand design (dark-blue tail wrapping onto the aft fuselage, white crane in a ring)', 2018,
        ['https://www.lufthansagroup.com/en/newsroom/releases/fleet/heritage-meets-the-future-lufthansa-presents-a-new-brand-design.html ("Dark blue becomes the leading brand color")',
         'https://www.dezeen.com/2018/02/05/lufthansa-airline-updates-yellow-100-year-old-logo-livery-redesign/'],
        dict(blue=('#05164D', 'third-party value: unverified')), ['A359', 'B748', 'A388', 'B744'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#05164D', tail2='#FFFFFF', eng='#05164D'),
        'fleet mid-transition (some 747-400 keep the old colours; new design rendered: inf)',
        dict(title=('Lufthansa', 'Libre Baskerville', 700, '#05164D', 0.2, dict(k=0.5, dy=0.15)), tail='#05164D', aft=('#05164D', 1.0, 0.9, -0.2),
             fin_art=(lh_crane, 0.52, 0.52, 0.62), eng='#05164D'))

# ---- Emirates (2023)
def uae_flag(n=1024):
    s = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#FFFFFF"/>
<path d="M0 100 L0 70 C30 60 60 30 100 0 L100 22 C70 44 44 70 20 100 Z" fill="#D71A21"/>
<path d="M36 100 C54 76 76 56 100 40 L100 58 C82 70 66 84 56 100 Z" fill="#018557"/>
<path d="M68 100 C78 88 88 80 100 74 L100 100 Z" fill="#000000"/></svg>'''
    return art.svg(s, n)


reg_std('UAE', 'Emirates', '2023 livery (waving UAE-flag tail, gold titles)', 2023,
        [NOR.format('emirates') + ' (A380 2023 profile; colour chart #E4AB2C titles, #018557 green: third party)'],
        dict(gold=('#E4AB2C', 'third-party chart: unverified'), red=('#D71A21', APPROX), green=('#018557', 'third-party chart: unverified')), ['A388'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#D71A21', tail2='#018557', eng='#F2F3F4'), 'Arabic title not drawn',
        dict(title=('Emirates', 'Libre Baskerville', 700, '#C9962E', 0.3, dict(k=0.8, dy=0.05)), fin_art=(uae_flag, 0.5, 0.5, 1.15), dorsal=False))

# ---- Turkish Airlines
reg_std('THY', 'Turkish Airlines', 'red tail with the goose in a white circle, grey tulip stripe', 2010,
        ['https://www.turkishairlines.com/ (brand; not fetched)'], dict(red=('#C70A0C', APPROX)), ['A359', 'B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#C70A0C', tail2='#FFFFFF', eng='#F2F3F4'), 'goose simplified',
        dict(title=('TURKISH AIRLINES', 'Montserrat', 700, '#23305C', 0.12, dict(k=0.55, dy=0.22, sp=0.03)), tail='#C70A0C', dorsal=False,
             cheat=[('#B5B9BF', [(0.35, -0.3), (0.6, -0.1), (0.8, 0.3)], 0.05)],
             fin_art=(svg_mark('<circle cx="50" cy="50" r="42" fill="#FFFFFF"/><path d="M24 58 C36 46 50 40 70 36 L80 28 L78 40 C70 50 56 56 40 58 L30 70 Z" fill="#C70A0C"/>'), 0.52, 0.52, 0.6)))

# ---- Virgin Atlantic (2019)
reg_std('VIR', 'Virgin Atlantic', '2019 "Flying Icons" livery (metallic silver fuselage, red tail, purple titles)', 2019,
        ['https://www.virgin.com/about-virgin/latest/hello-virgin-atlantics-new-flying-icons'], dict(red=('#DA0530', APPROX), purple=('#5B2C6F', APPROX), silver=('#C9CDD2', APPROX)),
        ['B789', 'A35K'], dict(top='#C9CDD2', belly='#C9CDD2', tail='#DA0530', tail2='#5B2C6F', eng='#DA0530'), 'flying icon figures not drawn',
        dict(body='#C9CDD2', title=('virgin atlantic', 'Montserrat', 700, '#5B2C6F', 0.22, dict(k=0.55, dy=0.1, it=True)), tail='#DA0530',
             fin_art=(lambda n=1024: text_image('virgin', font('Kalam', 700), 420, '#FFFFFF'), 0.55, 0.5, 0.16), eng='#DA0530'))

# ---- Air India (2023)
reg_std('AIC', 'Air India', '2023 livery (deep red, aubergine and gold; window-frame motif)', 2023,
        ['https://www.airindia.com/in/en/newsroom/press-release/a-new-air-india-is-unveiled--representing-bold-new-india-on-the-.html'],
        dict(red=('#B0182A', APPROX), aubergine=('#4B1A3A', APPROX), gold=('#C79A4B', APPROX)), [],
        dict(top='#F7F8F8', belly='#B0182A', tail='#B0182A', tail2='#C79A4B', eng='#F2F3F4', bellyLine=-0.6),
        'SFO fleet is 777 only (procedural airframe: runtime colours); fleet mid-transition',
        dict(title=('AIR INDIA', 'Montserrat', 700, '#B0182A', 0.16), tail='#B0182A'))

# ---- Air New Zealand
reg_std('ANZ', 'Air New Zealand', 'black tail with the white koru, black fern on the aft fuselage', 2012,
        [NOR.format('air-new-zealand') + ' (787-9 profile: the all-black variant)'], dict(black=('#111111', APPROX)), ['B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#111111', tail2='#FFFFFF', eng='#111111'), 'fern simplified to a black aft sweep',
        dict(title=('AIR NEW ZEALAND', 'Montserrat', 700, '#111111', 0.13, dict(k=0.55, dy=0.22, it=True, sp=0.03)), tail='#111111',
             aft=('#111111', 0.2, -0.6, -0.6),
             fin_art=(svg_mark('<path d="M50 10 C74 10 88 30 84 52 C80 72 60 80 46 70 C34 62 38 44 50 42 C58 40 62 50 56 56" fill="none" stroke="#FFFFFF" stroke-width="8"/>'), 0.55, 0.55, 0.6), eng='#111111'))

# ---- Avianca (TACA flies Avianca colours)
reg_std('AVA', 'Avianca', '2023 brand (lowercase avianca, brighter red; red tail and nacelles)', 2023,
        ['https://www.avianca.com/en/about-us/av-news/2023/october-18/', 'https://airlinegeeks.com/2026/07/31/livery-of-the-week-avianca/'],
        dict(red=('#E30613', APPROX)), ['A20N', 'A320'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#E30613', tail2='#FFFFFF', eng='#E30613'), 'fleet mid-transition (2023 brand rendered: inf)',
        dict(title=('avianca', 'Montserrat', 700, '#E30613', 0.34, dict(k=0.5, dy=0.05)), tail='#E30613',
             fin_art=(svg_mark('<circle cx="50" cy="50" r="30" fill="none" stroke="#FFFFFF" stroke-width="10"/><path d="M30 80 L70 20" stroke="#FFFFFF" stroke-width="10"/>'), 0.55, 0.5, 0.55), eng='#E30613'))

# ---- Volaris
reg_std('VOI', 'Volaris', 'white fuselage with purple / teal tail and titles', 2006,
        ['https://www.volaris.com/ (brand; not fetched)'], dict(purple=('#A12885', APPROX), teal=('#00A7B5', APPROX)), ['A20N', 'A21N', 'A320'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#A12885', tail2='#00A7B5', eng='#F2F3F4'), 'approx',
        dict(title=('volaris', 'Montserrat', 700, '#A12885', 0.3, dict(k=0.5, dy=0.05)), tail='#A12885', aft=('#A12885', 0.8, 0.8, -0.2),
             fin_polys=[('#00A7B5', [(-0.3, -0.3), (0.3, -0.3), (1.1, 0.8), (1.1, 1.1), (0.9, 1.1)])]))

# ---- Copa
reg_std('CMP', 'Copa Airlines', 'dark-blue tail with the gold Copa symbol', 2005,
        ['https://www.copaair.com/ (brand; not fetched)'], dict(blue=('#0E2D6E', APPROX), gold=('#C1A96F', APPROX)), ['B39M'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#0E2D6E', tail2='#C1A96F', eng='#0E2D6E'), 'approx',
        dict(title=('COPA AIRLINES', 'Montserrat', 700, '#0E2D6E', 0.14, dict(k=0.5, dy=0.2, sp=0.04)), tail='#0E2D6E',
             fin_art=(svg_mark('<circle cx="50" cy="50" r="38" fill="none" stroke="#C1A96F" stroke-width="8"/><path d="M26 50 L74 50 M50 26 L50 74" stroke="#C1A96F" stroke-width="8"/>'), 0.52, 0.5, 0.5), eng='#0E2D6E'))

# ---- KLM
reg_std('KLM', 'KLM', 'sky-blue upper fuselage, white belly, KLM crown on the tail', 2014,
        ['https://news.klm.com/ (brand; not fetched)'], dict(blue=('#00A1DE', APPROX), dark=('#003145', APPROX)), ['B78X', 'B789'],
        dict(top='#00A1DE', belly='#F7F8F8', tail='#00A1DE', tail2='#FFFFFF', eng='#00A1DE', bellyLine=-0.15), 'approx',
        dict(body='#00A1DE', belly=('#F7F8F8', [(0, -1.0), (0.06, -0.3), (0.2, -0.15), (0.85, -0.15), (0.95, 0.1), (1, 0.4)]),
             cheat=[('#003145', [(0.06, -0.33), (0.2, -0.18), (0.85, -0.18), (0.95, 0.07)], 0.015)],
             title=('KLM', 'Montserrat', 800, '#FFFFFF', 0.3, dict(k=0.6, dy=0.15)), tail='#00A1DE',
             fin_art=(lambda n=1024: text_image('KLM', font('Montserrat', 800), 420, '#FFFFFF'), 0.55, 0.45, 0.17), eng='#00A1DE'))

# ---- Swiss (777 at SFO: runtime colours only)
reg_std('SWR', 'Swiss', 'red tail with the white Swiss cross', 2011, ['https://www.swiss.com/ (brand; not fetched)'], dict(red=('#E3000F', APPROX)), [],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#E3000F', tail2='#FFFFFF', eng='#F2F3F4'), '777-300ER only at SFO (procedural)',
        dict(title=('SWISS', 'Montserrat', 800, '#E3000F', 0.18), tail='#E3000F'))

# ---- Asiana
reg_std('AAR', 'Asiana Airlines', 'grey / white fuselage, striped tail (yellow, red, blue, grey)', 2006,
        ['https://flyasiana.com/ (brand; not fetched)'], dict(grey=('#AAB0B5', APPROX), red=('#C8102E', APPROX), yellow=('#F2B705', APPROX), blue=('#1F4E9E', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#AAB0B5', tail='#AAB0B5', tail2='#C8102E', eng='#AAB0B5', bellyLine=-0.2), 'approx',
        dict(belly=('#AAB0B5', [(0, -1.1), (0.05, -0.4), (0.2, -0.2), (0.85, -0.2), (0.95, 0.1), (1, 0.4)]),
             title=('ASIANA AIRLINES', 'Montserrat', 700, '#6E7478', 0.12, dict(k=0.55, dy=0.22, sp=0.04)), tail='#F7F8F8',
             fin_polys=[(col, [(-0.3, 0.1 + 0.14 * k), (1.2, 0.1 + 0.14 * k), (1.2, 0.21 + 0.14 * k), (-0.3, 0.21 + 0.14 * k)]) for k, col in enumerate(['#1F4E9E', '#8C6BB1', '#C8102E', '#F2B705', '#AAB0B5', '#4FA3D1'])]))

# ---- Starlux
reg_std('SJX', 'Starlux Airlines', 'white fuselage, gold / dark titles and tail', 2020, ['https://www.starlux-airlines.com/ (brand; not fetched)'],
        dict(gold=('#B39664', APPROX), dark=('#3B3530', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#3B3530', tail2='#B39664', eng='#F2F3F4'), 'from knowledge only: approx',
        dict(title=('STARLUX', 'Libre Baskerville', 700, '#B39664', 0.14, dict(k=0.55, dy=0.2, sp=0.1)), tail='#3B3530',
             fin_art=(svg_mark('<path d="M50 10 L58 42 L90 50 L58 58 L50 90 L42 58 L10 50 L42 42 Z" fill="#B39664"/>'), 0.5, 0.55, 0.5)))

# ---- ZIPAIR
reg_std('TZP', 'ZIPAIR', 'white fuselage with grey / green ZIPAIR titles and tail', 2020, ['https://www.zipair.net/ (brand; not fetched)'],
        dict(green=('#34C6A0', APPROX), grey=('#6D7278', APPROX)), ['B788'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#6D7278', tail2='#34C6A0', eng='#F2F3F4'), 'from knowledge only: approx',
        dict(title=('ZIPAIR', 'Montserrat', 800, '#6D7278', 0.2, dict(k=0.6, dy=0.15)), tail='#6D7278',
             fin_polys=[('#34C6A0', [(-0.3, -0.3), (1.2, 0.3), (1.2, 0.45), (-0.3, -0.15)])]))

# ---- Aer Lingus (2019)
reg_std('EIN', 'Aer Lingus', '2019 livery (teal tail with the white shamrock)', 2019, ['https://www.aerlingus.com/ (brand; not fetched)'],
        dict(teal=('#006272', APPROX), light=('#2CC1C5', APPROX)), ['A333', 'A332'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#006272', tail2='#FFFFFF', eng='#F2F3F4'), 'approx',
        dict(title=('Aer Lingus', 'Montserrat', 700, '#006272', 0.2, dict(k=0.5, dy=0.15)), tail='#006272',
             fin_art=(svg_mark('<circle cx="50" cy="32" r="16" fill="#FFFFFF"/><circle cx="33" cy="54" r="16" fill="#FFFFFF"/><circle cx="67" cy="54" r="16" fill="#FFFFFF"/><path d="M50 58 L56 92 L48 92 Z" fill="#FFFFFF"/>'), 0.5, 0.5, 0.55)))

# ---- Qatar Airways
reg_std('QTR', 'Qatar Airways', 'grey fuselage, burgundy oryx on the tail', 2006,
        [NOR.format('qatar-airways') + ' (A350 profile; chart #BDC2C2 fuselage, #5C0631 oryx: third party)'],
        dict(grey=('#BDC2C2', 'third-party chart: unverified'), burgundy=('#5C0631', 'third-party chart: unverified')), ['A359'],
        dict(top='#BDC2C2', belly='#BDC2C2', tail='#BDC2C2', tail2='#5C0631', eng='#BDC2C2'), 'oryx simplified; Arabic script not drawn',
        dict(body='#C4C9CA', title=('QATAR', 'Libre Baskerville', 700, '#5C0631', 0.34, dict(k=0.4, dy=0.05)),
             fin_art=(svg_mark('<path d="M20 90 C30 60 50 44 70 40 L60 10 L78 36 L90 20 L84 44 C76 56 60 62 50 90 Z" fill="#5C0631"/>'), 0.6, 0.5, 0.8), eng='#C4C9CA'))

# ---- French bee
reg_std('FBU', 'French bee', 'white / blue gradient fuselage, blue tail', 2016, ['https://www.frenchbee.com/ (brand; not fetched)'],
        dict(blue=('#1CA3DC', APPROX)), ['A359'], dict(top='#F7F8F8', belly='#1CA3DC', tail='#1CA3DC', tail2='#FFFFFF', eng='#F2F3F4'), 'from knowledge only: approx',
        dict(title=('french bee', 'Nunito', 900, '#1CA3DC', 0.24, dict(k=0.6, dy=0.1)), tail='#1CA3DC', aft=('#1CA3DC', 2.0, -1.2, -1.2)))

# ---- SAS (2019)
reg_std('SAS', 'SAS', '2019 livery (silver-blue fuselage, dark-blue tail with SAS)', 2019, ['https://www.sasgroup.net/ (brand; not fetched)'],
        dict(blue=('#000C69', APPROX), silver=('#A3B2C2', APPROX)), ['A333', 'A359'],
        dict(top='#DDE3EA', belly='#A3B2C2', tail='#000C69', tail2='#FFFFFF', eng='#A3B2C2'), 'approx',
        dict(body='#E2E6EB', belly=('#A3B2C2', [(0, -1.2), (0.05, -0.6), (0.2, -0.4), (0.85, -0.4), (0.95, -0.1), (1, 0.3)]),
             title=('SCANDINAVIAN', 'Montserrat', 600, '#000C69', 0.1, dict(k=0.55, dy=0.22, sp=0.2)), tail='#000C69',
             fin_art=(lambda n=1024: text_image('SAS', font('Montserrat', 800), 420, '#C9D2DC'), 0.55, 0.45, 0.2)))

# ---- TAP
reg_std('TAP', 'TAP Air Portugal', '2017 livery (white; green and red on the tail)', 2017, ['https://www.flytap.com/ (brand; not fetched)'],
        dict(green=('#00A559', APPROX), red=('#EF2F24', APPROX)), ['A339'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#EF2F24', eng='#F2F3F4'), 'approx',
        dict(title=('TAP AIR PORTUGAL', 'Montserrat', 800, '#00A559', 0.13, dict(k=0.55, dy=0.2, sp=0.03)),
             fin_polys=[('#00A559', [(-0.3, -0.3), (0.5, -0.3), (1.1, 0.7), (1.1, 1.1), (0.7, 1.1)]), ('#EF2F24', [(0.55, -0.3), (1.2, -0.3), (1.2, 0.5)])]))

# ---- Air Premia
reg_std('APZ', 'Air Premia', 'white fuselage, dark navy tail', 2021, ['https://www.airpremia.com/ (brand; not fetched)'],
        dict(navy=('#0B1A3A', APPROX)), ['B789'], dict(top='#F7F8F8', belly='#F7F8F8', tail='#0B1A3A', tail2='#6BA4D8', eng='#F2F3F4'), 'from knowledge only: approx',
        dict(title=('AIR PREMIA', 'Montserrat', 700, '#0B1A3A', 0.13, dict(k=0.55, dy=0.2, sp=0.06)), tail='#0B1A3A'))

# ---- Flair
reg_std('FLE', 'Flair Airlines', 'white fuselage, purple tail and titles', 2021, ['https://flyflair.com/ (brand; not fetched)'],
        dict(purple=('#5F259F', APPROX), lime=('#C4D600', APPROX)), ['B38M'], dict(top='#F7F8F8', belly='#F7F8F8', tail='#5F259F', tail2='#C4D600', eng='#5F259F'), 'from knowledge only: approx',
        dict(title=('flair', 'Nunito', 900, '#5F259F', 0.34, dict(k=0.5, dy=0.05)), tail='#5F259F', eng='#5F259F'))

# ---- ITA Airways
reg_std('ITY', 'ITA Airways', '2021 livery (blue Savoia fuselage, white titles, tricolour tail)', 2021, ['https://www.ita-airways.com/ (brand; not fetched)'],
        dict(blue=('#0F2D6B', APPROX)), ['A339', 'A359'], dict(top='#0F2D6B', belly='#0F2D6B', tail='#0F2D6B', tail2='#FFFFFF', eng='#0F2D6B'), 'approx',
        dict(body='#1A3C85', title=('ITA', 'Montserrat', 800, '#FFFFFF', 0.3, dict(k=0.5, dy=0.1)), tail='#1A3C85',
             fin_polys=[('#009246', [(0.62, -0.3), (0.72, -0.3), (1.02, 1.1), (0.92, 1.1)]), ('#FFFFFF', [(0.72, -0.3), (0.82, -0.3), (1.12, 1.1), (1.02, 1.1)]), ('#CE2B37', [(0.82, -0.3), (0.92, -0.3), (1.22, 1.1), (1.12, 1.1)])], eng='#1A3C85'))

# ---- China Southern
reg_std('CSN', 'China Southern', 'blue tail with the red kapok flower', 1991, ['https://www.csair.com/ (brand; not fetched)'],
        dict(blue=('#0079C2', APPROX), red=('#E1261C', APPROX)), ['B789'], dict(top='#F7F8F8', belly='#F7F8F8', tail='#0079C2', tail2='#E1261C', eng='#F2F3F4'), 'approx',
        dict(title=('CHINA SOUTHERN', 'Montserrat', 700, '#0079C2', 0.12, dict(k=0.55, dy=0.22, sp=0.04)), tail='#0079C2',
             cheat=[('#0079C2', [(0.06, -0.45), (0.2, -0.4), (0.85, -0.4), (0.95, -0.2)], 0.03)],
             fin_art=(svg_mark(''.join(f'<ellipse cx="{50 + 22 * np.cos(a):.1f}" cy="{50 + 22 * np.sin(a):.1f}" rx="18" ry="10" transform="rotate({np.degrees(a):.0f} {50 + 22 * np.cos(a):.1f} {50 + 22 * np.sin(a):.1f})" fill="#E1261C"/>' for a in np.linspace(0, 2 * np.pi, 6, endpoint=False))), 0.5, 0.52, 0.5)))

# ---- China Eastern / Air China / EVA 777: runtime only
reg_std('CES', 'China Eastern', 'swallow logo on the tail (red / blue)', 2014, ['https://www.ceair.com/ (brand; not fetched)'], dict(red=('#C8102E', APPROX)), [],
        dict(top='#F7F8F8', belly='#1D4F91', tail='#F7F8F8', tail2='#C8102E', eng='#F2F3F4', bellyLine=-0.6), '777 only at SFO (procedural)', dict(tail='#F7F8F8'))
reg_std('CCA', 'Air China', 'red phoenix on a white tail', 1988, ['https://www.airchina.com/ (brand; not fetched)'], dict(red=('#C8102E', APPROX)), [],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#C8102E', eng='#F2F3F4'), '777 only at SFO (procedural)', dict(tail='#F7F8F8'))

# ---- Vietnam Airlines
reg_std('HVN', 'Vietnam Airlines', 'teal tail with the golden lotus', 2015, ['https://www.vietnamairlines.com/ (brand; not fetched)'],
        dict(teal=('#00677F', APPROX), gold=('#D6A23D', APPROX)), ['A359'], dict(top='#F7F8F8', belly='#00677F', tail='#00677F', tail2='#D6A23D', eng='#F2F3F4', bellyLine=-0.6), 'approx',
        dict(belly=('#00677F', [(0, -1.3), (0.06, -0.8), (0.2, -0.62), (0.85, -0.62), (0.95, -0.4), (1, 0)]),
             title=('VIETNAM AIRLINES', 'Montserrat', 700, '#00677F', 0.12, dict(k=0.55, dy=0.22, sp=0.03)), tail='#00677F',
             fin_art=(svg_mark('<path d="M50 20 C62 36 62 56 50 76 C38 56 38 36 50 20 Z M50 76 C36 70 24 56 20 40 C34 44 44 56 50 76 Z M50 76 C64 70 76 56 80 40 C66 44 56 56 50 76 Z" fill="#D6A23D"/>'), 0.5, 0.52, 0.55)))

# ---- Fiji Airways
reg_std('FJI', 'Fiji Airways', 'masi (tapa) pattern tail', 2013, ['https://www.fijiairways.com/ (brand; not fetched)'],
        dict(brown=('#4A2E20', APPROX), sand=('#C7A27A', APPROX)), ['A332', 'A333', 'A359'], dict(top='#F7F8F8', belly='#F7F8F8', tail='#4A2E20', tail2='#C7A27A', eng='#F2F3F4'), 'pattern simplified',
        dict(title=('FIJI AIRWAYS', 'Montserrat', 700, '#4A2E20', 0.13, dict(k=0.55, dy=0.2, sp=0.05)), tail='#C7A27A',
             fin_polys=[('#4A2E20', [(-0.3, 0.1 + 0.2 * k), (1.2, 0.1 + 0.2 * k), (1.2, 0.17 + 0.2 * k), (-0.3, 0.17 + 0.2 * k)]) for k in range(5)]))

# ---- Condor (2022 stripes)
reg_std('CFG', 'Condor', '2022 striped livery (each aircraft one colour; red "Passion" rendered)', 2022, ['https://www.condor.com/ (brand; not fetched)'],
        dict(red=('#E2001A', APPROX)), ['A339'], dict(top='#E2001A', belly='#F7F8F8', tail='#E2001A', tail2='#FFFFFF', eng='#F2F3F4'), 'colour varies per aircraft (inf: red)',
        dict(extra=lambda c: (c.paint((c.fuselage() | c.finzone()) * (np.mod((c.y - c.ycM) / (0.12 * c.H), 1.0) < 0.5) * 1.0, '#E2001A'),
                              title(c, 'Condor', 'Montserrat', 800, '#1A1A1A', 0.22, d1(c, 0.5), dy=0.15))))

# ---- Iberia (2013)
reg_std('IBE', 'Iberia', '2013 livery (red and yellow IB symbol on the tail)', 2013, ['https://www.iberia.com/ (brand; not fetched)'],
        dict(red=('#D7192D', APPROX), yellow=('#FCC200', APPROX)), ['A332'], dict(top='#F7F8F8', belly='#F7F8F8', tail='#D7192D', tail2='#FCC200', eng='#F2F3F4'), 'approx',
        dict(title=('IBERIA', 'Montserrat', 800, '#D7192D', 0.18, dict(k=0.55, dy=0.18, sp=0.05)),
             fin_polys=[('#D7192D', [(-0.3, 0.2), (1.2, 0.8), (1.2, 1.2), (-0.3, 1.2)]), ('#FCC200', [(-0.3, -0.3), (1.2, 0.3), (1.2, 0.7), (-0.3, 0.1)])]))

# ---- LOT
reg_std('LOT', 'LOT Polish Airlines', 'dark-blue tail with the crane in a circle', 2011, ['https://www.lot.com/ (brand; not fetched)'],
        dict(blue=('#11397E', APPROX)), ['B788', 'B789'], dict(top='#F7F8F8', belly='#F7F8F8', tail='#11397E', tail2='#FFFFFF', eng='#F2F3F4'), 'approx',
        dict(title=('LOT', 'Montserrat', 800, '#11397E', 0.2, dict(k=0.6, dy=0.15)), tail='#11397E', fin_art=(lh_crane, 0.52, 0.52, 0.55)))

# ---- cargo
reg_std('FDX', 'FedEx', 'FedEx Express livery (purple crown and tail, white lower fuselage, grey belly)', 1994, ['https://newsroom.fedex.com/ (brand; not fetched)'],
        dict(purple=('#4D148C', APPROX), orange=('#FF6600', APPROX)), ['B763', 'MD11', 'B752'],
        dict(top='#4D148C', belly='#C9CCD1', tail='#4D148C', tail2='#FF6600', eng='#F2F3F4', bellyLine=-0.5), 'approx',
        dict(side_polys=[('#4D148C', [(0.0, 0.35), (1.2, 0.35), (1.2, 2.0), (0.0, 2.0)])], belly=('#C9CCD1', [(0, -1.2), (0.1, -0.6), (0.9, -0.55), (1, -0.2)]),
             extra=lambda c: title(c, 'FedEx', 'Montserrat', 800, '#FFFFFF', 0.3, d1(c, 0.8), dy=0.3), tail='#4D148C'))
reg_std('UPS', 'UPS', 'brown tail and belly, gold shield, white upper fuselage', 2003, [NOR.format('ups')],
        dict(brown=('#351C15', APPROX), gold=('#FFB500', APPROX)), ['B763', 'B752', 'B748', 'B744', 'MD11'],
        dict(top='#F7F8F8', belly='#351C15', tail='#351C15', tail2='#FFB500', eng='#F2F3F4', bellyLine=-0.3), 'approx',
        dict(belly=('#351C15', [(0, -1.2), (0.1, -0.35), (0.6, -0.3), (0.85, 0.2), (1, 0.8)]), cheat=[('#FFB500', [(0.1, -0.3), (0.6, -0.25), (0.85, 0.25)], 0.02)],
             title=('Worldwide Services', 'Montserrat', 600, '#351C15', 0.1, dict(k=0.5, dy=0.2)), tail='#351C15',
             fin_art=(svg_mark('<path d="M20 12 L80 12 L80 60 C80 80 50 92 50 92 C50 92 20 80 20 60 Z" fill="#FFB500"/><path d="M26 18 L74 18 L74 58 C74 74 50 84 50 84 C50 84 26 74 26 58 Z" fill="#351C15"/>'), 0.55, 0.5, 0.45)))
