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
from paint import text_image, text_shaped

LIVERIES = {}


def photo_ref(code, note=''):
    """citation of the reference photographs a design was measured on or checked against (tools/liveries/ref_photos.py:
    Wikimedia Commons, reference only, never shipped or traced)"""
    import ref_photos
    files = '; '.join(f'"{t}"' for t in ref_photos.REFS.get(code, []))
    return f'photo check (reference only, Wikimedia Commons files): {files}' + (f' ({note})' if note else '')


def livery(code, **meta):
    def reg(fn):
        LIVERIES[code] = dict(code=code, paint=fn, **meta); return fn
    return reg


def lin_hex(h):
    from common import srgb_to_lin, hex_rgb
    return srgb_to_lin(hex_rgb(h))


def title_box(c, text_img, height, s0, yc, mode='text', where=None):
    c.decal(text_img, s0, yc, height, mode=mode, where=c.fuselage() if where is None else where)


def lockup(c, items, s0, where=None):
    """a title lock-up that keeps its reading order on both sides (photos: Delta widget + DELTA + CONNECTION, UNITED
    EXPRESS): items [(img, height (m), y centre (m), station offset from s0 (m) or None = right after the previous item
    + gap, gap (m))]; laid out on the port side from s0 aft, mirrored as a block on the starboard side. Returns the
    block's station range."""
    placed = []; x = s0
    for img, h, yc, off, gap in items:
        w = h * img.size[0] / img.size[1]
        st = s0 + off if off is not None else x + gap
        placed.append((img, h, yc, st, w)); x = max(x, st + w)
    b0 = min(p[3] for p in placed); b1 = max(p[3] + p[4] for p in placed)
    for img, h, yc, st, w in placed:
        c.decal(img, st, yc, h, where=c.fuselage() if where is None else where, block=(b0, b1))
    return b0, b1


# ================================================================================================ United (2019 "blue")
UA = dict(rhapsody='#0B233E', united='#0033A0', gray='#D3D4D0', sky='#6CB2E2', white='#F7F8F8', express='#8E9396')
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
        # UNITED in United Blue and EXPRESS in grey, same cap height and baseline, one lock-up ABOVE the window row (photo of
        # the SkyWest E175 N86371 landing at SFO, Jan 2026, Wikimedia Commons, refs/cache/livref UAL-X_2, port side,
        # measured on the aircraft: lock-up from sn 0.21 to 0.55 of the fuselage length, cap height 0.25-0.28 of the
        # fuselage height, the letters' feet at the tops of the windows). Review round 1: the earlier lock-up was centred
        # on the windows and 0.55 L long.
        img = text_image('UNITED', f, 400, UA['united'], spacing=0.16, stretch=1.08)
        img2 = text_image('EXPRESS', f, 400, UA['express'], spacing=0.16, stretch=1.08)
        gap = 0.33 * k
        asp = (img.size[0] + img2.size[0]) / img.size[1]
        h = min(0.25 * c.H, (0.34 * c.L - gap) / asp)
        yc = c.winY + c.winH / 2 + 0.03 * c.H + h / 2
        lockup(c, [(img, h, yc, 0.0, 0.0), (img2, h * img2.size[1] / img.size[1], yc, None, gap)], 0.21 * c.L)
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
        refs=UA_REFS, colors={k: (v, 'official: United livery graphic PDF swatch' if k != 'white' else 'approx') for k, v in UA.items() if k != 'express'},
        types=['A319', 'A320', 'A21N', 'B38M', 'B39M', 'B738', 'B739', 'B752', 'B753', 'B763', 'B764', 'B788', 'B789', 'B78X'],
        runtime=dict(top='#F7F8F8', belly='#D3D4D0', tail='#0033A0', tail2='#6CB2E2', eng='#0033A0', stripe='#0B233E', bellyLine=-0.45),
        status='layout measured on the official United livery graphic (737-800); other types scaled by fuselage length')
def united(c):
    _united(c)


@livery('UAL-X', name='United Express', version='2019 livery with UNITED EXPRESS titles', since=2019,
        refs=UA_REFS + [photo_ref('UAL-X', 'UNITED blue + EXPRESS grey, same size, one line; N206SY in the first photo still wears the 2010 Globe livery')],
        colors={k: (v, 'official (United livery graphic PDF)' if k not in ('white', 'express') else 'approx (EXPRESS grey: from the photo)') for k, v in UA.items()},
        types=['E75L', 'E170', 'CRJ2', 'CRJ7'],
        runtime=dict(top='#F7F8F8', belly='#D3D4D0', tail='#0033A0', tail2='#6CB2E2', eng='#0033A0', stripe='#0B233E', bellyLine=-0.45),
        status='2019 design on regional jets (United release: applied to regional aircraft); title lock-up measured on a photo of an E175; fleet mid-transition (some SkyWest E175s still wear the 2010 Globe livery: not modelled per tail)')
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


def title_span(c, text, fam, weight, color, h_frac, s0, s1, dy=0.0, spacing=0.05, where=None, italic=False, shear=0.0, eta=None):
    """a title h_frac x H tall, stretched to span stations [s0, s1] (m), centred dy x H above the window centre line (or at
    cabin eta `eta`: (y - cabin centre) / cabin half height, for the double-deck types)"""
    img = text_image(text, font(fam, weight, italic), 420, color, spacing=spacing, italic_shear=shear)
    h = h_frac * c.H; w = s1 - s0
    img = img.resize((max(1, int(img.size[1] * w / h)), img.size[1]))
    yc = c.winY + dy * c.H if eta is None else c.ycM + eta * c.hhM
    c.decal(img, s0, yc, h, mode='text', where=c.fuselage() if where is None else where)


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
    # widget + DELTA (+ CONNECTION) as one lock-up: on the starboard side the widget stays ahead of DELTA in reading
    # order, i.e. aft of it (photo of the SkyWest E175 N310SY, starboard side, refs/cache/livref DAL-C_2); CONNECTION
    # below the window row, right-aligned with DELTA (N242SY port side, DAL-C_1: 0.07 H tall, 0.2 H below the windows)
    dimg = text_image('DELTA', font('Montserrat', 700), 420, DL['blue'], spacing=0.34)
    hD = 0.135 * c.H; wD = hD * dimg.size[0] / dimg.size[1]
    items = [(wimg, hW, c.winY + 0.17 * c.H, 0.0, 0.0), (dimg, hD, c.winY + 0.165 * c.H, hW * 1.25, 0.0)]
    if connection:
        cimg = text_image('CONNECTION', font('Montserrat', 500), 420, DL['blue'], spacing=0.36)
        hC = 0.066 * c.H; wC = hC * cimg.size[0] / cimg.size[1]
        items.append((cimg, hC, c.winY - 0.2 * c.H, hW * 1.25 + wD - wC, 0.0))
    lockup(c, items, s0)
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
        refs=DL_REFS + [photo_ref('DAL-C', 'CONNECTION below the window row')], colors={k: (v, 'official' if k in ('blue', 'red') else 'approx') for k, v in DL.items()},
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
    # American Eagle (photo of the SkyWest E175 N515SY, Wikimedia Commons, refs/cache/livref AAL-E_1): symbol and title sit
    # BELOW the window row (centre 0.21 H below the window centre, title cap height 0.27 H); mainline: across the windows
    hs = (0.34 if eagle else 0.40) * c.H; dy = -0.21 if eagle else 0.02
    c.decal(aa_symbol(), s0, c.winY + dy * c.H, hs, mode='mirror', where=c.fuselage())
    title(c, 'American Eagle' if eagle else 'American', 'Montserrat', 500, AA['title'], 0.34 if not eagle else 0.27, s0 + 0.75 * hs, dy=dy, spacing=0.0)
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


@livery('AAL-E', name='American Eagle', version='American 2013 livery with American Eagle titles', since=2013, refs=AA_REFS + [photo_ref('AAL-E', 'symbol and title below the window row')],
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
    cell = 0.46 * c.H              # tiles about half the cabin height (photo of N982JB: 0.4-0.5 H)
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
    if express:
        # AIR CANADA over the windows, the rondelle and EXPRESS on a second line below the windows, starting under CANADA
        # (photo of the Jazz CRJ900 C-FNJZ, Wikimedia Commons, refs/cache/livref ACA-X_1)
        t1 = text_image('AIR CANADA', font('Montserrat', 600), 420, AC['black'], spacing=0.12)
        t2 = text_image('EXPRESS', font('Montserrat', 600), 420, AC['black'], spacing=0.12)
        h1 = 0.17 * c.H; w1 = h1 * t1.size[0] / t1.size[1]; h2 = 0.12 * c.H
        lockup(c, [(t1, h1, c.winY + 0.21 * c.H, 0.0, 0.0), (ac_roundel(512), 0.14 * c.H, c.winY - 0.22 * c.H, 0.3 * w1, 0.0),
                   (t2, h2, c.winY - 0.22 * c.H, None, 0.04 * c.H)], d1(c, 0.5))
    else:
        title(c, 'AIR CANADA', 'Montserrat', 600, AC['black'], 0.17, d1(c, 0.5), dy=0.21, spacing=0.12)
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


@livery('ACA-X', name='Air Canada Express', version='2017 livery with AIR CANADA EXPRESS titles', since=2017, refs=AC_REFS + [photo_ref('ACA-X', 'AIR CANADA over the windows, rondelle + EXPRESS below them')],
        colors=dict(red=(AC['red'], 'official'), black=(AC['black'], 'official')), types=['CRJ9'],
        runtime=dict(top='#F7F8F8', belly='#141414', tail='#141414', tail2='#F01428', eng='#141414', bellyLine=-0.55),
        status='title placement approx')
def aircanada_express(c):
    _aircanada(c, express=True)


# ================================================================================================ WestJet
WS = dict(teal='#1C9AAA', teal_dark='#0B5F78', fin_teal='#2C9BAA', fin_white='#E3E8EA', navy='#17206A', title='#1B2466', white='#F7F8F8')
WS_PHOTOS = ('photo check (reference only, Wikimedia Commons): "C-GPFT Boeing 737 Max 8 Westjet LGW 20.5.24 (53734026042).jpg" (layout '
             'measured: title, aft teal, navy wedge, fin facets) and "C-FNWD - Boeing 737 MAX 8 - WestJet LIR 260225.jpg"')


@livery('WJA', name='WestJet', version='2018 livery (white body, WESTJET title, teal aft body with a navy wedge, faceted leaf tail)', since=2018,
        refs=['https://westjet.mediaroom.com/2018-05-08-WestJet-unveils-its-Dreamliner-Spirit-of-Canada-to-the-world (livery reveal; gradual repaint)',
              'https://www.travelweek.ca/news/the-spirit-of-canada-new-look-for-westjets-livery-logo-and-cabin-interiors/ (teal extended onto the rear fuselage, leaf silhouette)',
              WS_PHOTOS],
        colors={k: (v, 'measured on the photos (not an official value)') for k, v in WS.items()}, types=['B737', 'B738', 'B38M', 'B789'],
        runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#1C9AAA', tail2='#17206A', eng='#F7F8F8'),
        status='layout measured on a photo of a 737-8 (starboard); the halftone texture of the tail facets is drawn flat; colours from photos (approx)')
def westjet(c):
    base(c, WS['white'])
    fus = c.fuselage()
    # WESTJET over the windows, from 1.4 m aft of door 1 (photo: sn 0.157-0.36 on the 737-8, 0.28 H tall, centre 0.055 H
    # above the window centre), a heavy wide face (Montserrat 800 stretched: look-alike)
    title(c, 'WESTJET', 'Montserrat', 800, WS['title'], 0.28, d1(c, 0.36), dy=0.055, spacing=0.02, stretch=1.3)
    # aft body: teal behind the diagonal from the keel at sn 0.54 to the crown at sn 0.765 (gradient: lighter on top)
    aft = c.poly_alpha([(0.543, -1.6), (0.769, 1.0), (0.80, 1.8), (1.2, 1.8), (1.2, -1.6)], 'cabin', fus)
    t = np.clip(((c.y - c.ycM) / c.hhM + 1.0) / 2.0, 0, 1)
    tl, td = lin_hex(WS['teal']), lin_hex(WS['teal_dark'])
    col = td[None, :] + (tl - td)[None, :] * t[:, None]
    c.col = c.col * (1 - aft[:, None]) + col * aft[:, None]
    # navy wedge from the fin root down to an apex at sn 0.879, eta -0.39, closed aft by a white band
    c.poly([(0.80, 1.8), (0.879, -0.39), (0.886, -0.39), (0.935, 1.8)], WS['navy'], 'cabin', where=fus)
    c.poly([(0.879, -0.39), (0.892, -0.39), (0.945, 1.8), (0.93, 1.8)], WS['white'], 'cabin', where=fus)
    fin = c.finzone()
    if c.fin is not None:
        fin_all(c, WS['fin_teal'])
        # fin facets (fin coords fu 0 LE .. 1 TE, fv 0 root .. 1 tip), measured on the photo: white leaf facet, teal cap and
        # leading-edge band, small teal triangle at the leading edge, white chevron (root band + descending arm), navy below
        c.poly([(1.2, 0.57), (0.757, 0.53), (0.41, 0.78), (0.053, 0.545), (-0.2, 0.5), (-0.2, 0.06), (1.2, 0.30)], WS['fin_white'], 'fin', where=fin)
        c.poly([(-0.2, 0.43), (0.0, 0.41), (0.22, 0.18), (0.0, 0.26), (-0.2, 0.27)], WS['fin_teal'], 'fin', where=fin)
        c.poly([(-0.3, 0.02), (1.2, 0.26), (1.2, 0.315), (-0.3, 0.075)], WS['white'], 'fin', where=fin)
        c.poly([(-0.3, 0.02), (1.2, 0.26), (1.2, -0.5), (-0.3, -0.5)], WS['navy'], 'fin', where=fin)
        c.poly([(0.66, -0.5), (0.76, -0.5), (0.80, 0.245), (0.70, 0.23)], WS['white'], 'fin', where=fin)
        c.poly([(0.76, -0.5), (1.3, -0.5), (1.3, 0.29), (0.80, 0.245)], WS['fin_teal'], 'fin', where=fin)
    c.engines(WS['white']); c.tips(WS['navy']); c.hstab(WS['white']); c.pylons('#E4E6E8')


# ================================================================================================ Aeromexico
AM = dict(navy='#0B2343', blue='#2F63B8', red='#D22630', white='#F7F8F8', green='#006847')
AM_PHOTOS = ('photo check (reference only, Wikimedia Commons): "Aeroméxico Boeing 737-8 MAX XA-DAE on final approach to Boston July 2025.jpg" '
             '(layout measured: title, red swoosh, navy tail sweep, Caballero Aguila) and "Aeromexico Boeing 737-8 MAX (XA-SRA) at GDL.jpg"')


def eagle_knight(n=1024, fg='#FFFFFF', bg=AM['navy']):
    """the Caballero Aguila (eagle-warrior head facing forward: crest and beak, the warrior's face in the open beak,
    eight feather bars trailing aft), re-drawn from the 2025 photo of XA-DAE (the fin art as painted; the 2024 update is
    being applied gradually)"""
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="60 60 590 470">
<path d="M245 85 C330 70 450 72 510 95 C570 110 622 150 632 200 C600 175 565 160 530 158 C505 158 480 170 468 190 L418 196
 L408 440 L150 440 L150 362 L70 362 L70 248 L108 248 L160 198 Z" fill="{fg}"/>
<path d="M455 118 C480 112 505 115 525 128 C505 132 480 132 455 128 Z" fill="{bg}"/>
<rect x="150" y="194" width="84" height="11" rx="5" fill="{bg}"/><rect x="95" y="238" width="143" height="11" rx="5" fill="{bg}"/>
<rect x="55" y="276" width="247" height="11" rx="5" fill="{bg}"/><rect x="55" y="316" width="247" height="11" rx="5" fill="{bg}"/>
<rect x="135" y="357" width="237" height="11" rx="5" fill="{bg}"/><rect x="135" y="398" width="237" height="11" rx="5" fill="{bg}"/>
<path d="M230 452 L392 452 L378 478 L230 478 Z" fill="{fg}"/><path d="M230 490 L356 490 L340 515 L230 515 Z" fill="{fg}"/>
<path d="M425 215 C430 205 450 204 470 206 L540 206 C548 216 560 222 575 228 L578 262 L598 290 L580 300 L582 330 L575 332
 L578 360 C575 385 565 400 545 404 L455 404 C435 402 425 390 425 370 Z" fill="{fg}"/></svg>'''
    return art.svg(s, n)


def smallcaps_image(parts, fam, weight, px=420, color='#000000', spacing=0.04):
    """a wordmark in small caps: parts [(text, scale)], each run drawn on a common baseline (RGBA, sRGB)"""
    from PIL import Image, ImageDraw, ImageFont
    runs = [(t, ImageFont.truetype(font(fam, weight), int(px * k))) for t, k in parts]
    asc = max(f.getmetrics()[0] for _, f in runs); desc = max(f.getmetrics()[1] for _, f in runs)
    W = int(sum(f.getlength(t) + spacing * px * len(t) for t, f in runs) + 0.2 * px); H = asc + desc + 8
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im); x = 0.05 * px
    for t, f in runs:
        for ch in t:
            d.text((x, asc - f.getmetrics()[0] + 4), ch, font=f, fill=255); x += f.getlength(ch) + spacing * px
    bb = im.getbbox(); im = im.crop((bb[0] - 3, bb[1] - 3, bb[2] + 3, bb[3] + 3))
    out = Image.new('RGBA', im.size, tuple(int(v * 255) for v in __import__('common').hex_rgb(color)) + (0,)); out.putalpha(im)
    return out


@livery('AMX', name='Aeroméxico', version='Caballero Águila livery (white body, red swoosh, navy tail sweeping onto the aft body; the 2024 updated eagle is being applied gradually)', since=2006,
        refs=['https://www.norebbo.com/aeromexico-livery/ (737-700 profile; layout reference only)',
              'https://www.breitflyte.com/post/aeromexico-unveils-new-aircraft-livery-as-part-of-90th-anniversary-celebration (2024 update, gradual: 404 at verification)',
              AM_PHOTOS],
        colors={k: (v, 'approx (photo at dusk; not an official value)') for k, v in AM.items()}, types=['B738', 'B38M', 'B39M', 'B789'],
        runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#0B2343', tail2='#2F63B8', eng='#0B2343'),
        status='layout measured on a photo of a 737-8 (starboard); eagle re-drawn from the photo; colours approx')
def aeromexico(c):
    base(c, AM['white'])
    fus = c.fuselage()
    # AEROMEXICO in small caps (tall A and M), serif look-alike, over the windows from 1.4 m aft of door 1 (photo: baseline
    # 0.53, tall caps to 0.82 of the cabin half height above the centre; sn 0.144-0.303 on the 737-8)
    img = smallcaps_image([('A', 1.0), ('ERO', 0.78), ('M', 1.0), ('EXICO', 0.78)], 'Libre Baskerville', 700, color=AM['navy'], spacing=0.03)
    h = 0.29 * c.hhM; w = h * img.size[0] / img.size[1]
    s0 = d1(c, 0.35)
    c.decal(img, s0, c.ycM + 0.675 * c.hhM, h, mode='text', where=fus)
    # the small Mexican flag aft of the title
    fl = art.poly_image([([(0, 0), (1 / 3, 0), (1 / 3, 1), (0, 1)], AM['green']), ([(1 / 3, 0), (2 / 3, 0), (2 / 3, 1), (1 / 3, 1)], '#FFFFFF'),
                         ([(2 / 3, 0), (1, 0), (1, 1), (2 / 3, 1)], AM['red'])], 256, aspect=1.75)
    c.decal(fl, s0 + w + 0.2 * c.hhM, c.ycM + 0.6 * c.hhM, 0.15 * c.hhM, mode='mirror', where=fus)
    # red swoosh across the windows (photo): tapered line from sn 0.138 (under the title's front) down to eta 0.02, up over
    # the windows to eta 0.58 at sn 0.44 and back down to its aft point at sn 0.594
    P = np.array([(0.138, 0.15), (0.194, 0.02), (0.253, 0.03), (0.312, 0.18), (0.371, 0.42), (0.444, 0.58), (0.518, 0.53), (0.594, 0.39)])
    from scipy.interpolate import PchipInterpolator
    sn = c.s / c.L; q = fus & (sn > P[0, 0]) & (sn < P[-1, 0])
    yc = c.ycM + PchipInterpolator(P[:, 0], P[:, 1])(np.clip(sn, P[0, 0], P[-1, 0])) * c.hhM
    taper = np.sin(np.pi * np.clip((sn - P[0, 0]) / (P[-1, 0] - P[0, 0]), 0, 1)) ** 0.6
    wid = 0.055 * c.hhM * taper
    c.paint(c.aa(np.abs(c.y - yc) - wid / 2) * q, AM['red'])
    fin = c.finzone()
    if c.fin is not None:
        # navy tail sweeping down onto the aft body; a blue line under its lower edge (photo)
        E = [(0.62, 1.3), (0.665, 0.82), (0.712, 0.65), (0.759, 0.37), (0.806, 0.08), (0.841, -0.13), (0.882, -0.26), (0.918, -0.32), (0.95, -0.2), (1.02, 0.3)]
        y_e = c.curve(E, 'cabin')
        aftq = fus & (c.s / c.L > 0.62)
        c.band(y_e - 0.035 * c.hhM, 0.045 * c.hhM, AM['blue'], where=aftq & (c.s / c.L > 0.68) & (c.s / c.L < 0.94))
        c.paint(c.aa(y_e - c.y) * aftq, AM['navy'])
        fin_all(c, AM['navy'])
        from PIL import ImageOps
        c.fin_decal(ImageOps.mirror(eagle_knight()), 0.5, 0.42, 0.52, where=c.fin_proper())   # drawn facing aft: mirrored to face forward
    c.engines(AM['navy'], lip='#C5CBD3'); c.tips(AM['navy']); c.hstab(AM['white']); c.pylons('#E4E6E8')


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
SY = dict(orange='#F4511E', navy='#14207A', white='#F7F8F8')


def sy_sun(n=1024, disc=SY['orange'], ink=SY['navy']):
    """the Sun Country sun, re-drawn simplified from the photo: an orange disc with a navy ring of rays and a navy S"""
    rays = ''.join(f'<path d="M50 50 L{50 + 49 * np.cos(a - 0.09):.1f} {50 + 49 * np.sin(a - 0.09):.1f} L{50 + 49 * np.cos(a + 0.09):.1f} {50 + 49 * np.sin(a + 0.09):.1f} Z" fill="{ink}"/>'
                   for a in np.linspace(0, 2 * np.pi, 14, endpoint=False))
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="49" fill="{disc}"/>{rays}
<circle cx="50" cy="50" r="33" fill="{disc}"/><text x="50" y="68" font-family="DejaVu Sans" font-weight="bold" font-size="52" text-anchor="middle" fill="{ink}">S</text></svg>'''
    return art.svg(s, n)


@livery('SCX', name='Sun Country Airlines', version='2018 livery (orange forward body with the white title, white centre section, navy aft body and tail with the orange sun)', since=2018,
        refs=['https://www.startribune.com/first-look-at-the-new-paint-job-on-sun-country-s-airplanes/499049761 (2018 livery; not reachable at verification)',
              photo_ref('SCX', 'layout measured on the starboard side of the 737-800 N841SY')],
        colors={k: (v, 'approx (photo)') for k, v in SY.items()}, types=['B738'],
        runtime=dict(top='#F4511E', belly='#14207A', tail='#14207A', tail2='#F4511E', eng='#14207A'),
        status='layout measured on a photo of a 737-800 (orange sn 0-0.41 at the crown / 0.48 at the keel, navy aft of a diagonal from the keel at sn 0.69 to the fin root, orange line on the diagonal); contour pattern of the navy not drawn')
def sun_country(c):
    base(c, SY['white'])
    fus = c.fuselage()
    c.poly([(-0.2, -1.6), (-0.2, 1.6), (0.41, 1.6), (0.48, -1.6)], SY['orange'], 'cabin', where=fus)
    c.poly([(0.69, -1.6), (0.84, 1.6), (1.3, 1.6), (1.3, -1.6)], SY['navy'], 'cabin', where=fus)
    c.poly([(0.675, -1.6), (0.825, 1.6), (0.84, 1.6), (0.69, -1.6)], SY['orange'], 'cabin', where=fus)
    title_span(c, 'suncountry', 'Nunito', 900, '#FFFFFF', 0.42, 0.153 * c.L, 0.435 * c.L, 0.0, spacing=0.0)
    fin_all(c, SY['navy'])
    if c.fin is not None:
        c.fin_decal(sy_sun(), 0.48, 0.42, 0.78, where=c.fin_proper(), mode='text')
    c.engines(SY['navy']); c.tips(SY['navy']); c.hstab(SY['navy']); c.pylons(SY['navy'])


# ================================================================================================ Breeze
BZ = dict(blue='#3E8EDE', navy='#1E2A69', light='#A9D4F5', white='#FFFFFF')
@livery('MXY', name='Breeze Airways', version='2021 livery (blue fuselage, navy tail with the light-blue check)', since=2021,
        refs=['https://www.airbus.com/en/newsroom/press-releases/2021-09-breeze-airways-reveals-new-a220-livery-confirms-order-for-20 (reveal, no description)',
              'https://www.norebbo.com/breeze-airways-livery/ (E190 profile and colour chart; layout reference only)', photo_ref('MXY', 'white Breeze title on the blue body')],
        colors={k: (v, 'third-party chart / approx: unverified') for k, v in BZ.items()}, types=['BCS3'],
        runtime=dict(top='#3E8EDE', belly='#3E8EDE', tail='#1E2A69', tail2='#A9D4F5', eng='#1E2A69'),
        status='layout from the profile reference')
def breeze(c):
    base(c, BZ['blue'])
    c.gradient([(0.0, '#4C9BE6'), (0.7, BZ['blue']), (1.0, '#2E62B8')], c.s / c.L, where=c.fuselage())
    title(c, 'Breeze', 'Nunito', 900, BZ['white'], 0.3, d1(c, 0.6), dy=-0.05, spacing=0.02)   # white (photo of N204BZ)
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
        img, fu, fv, h = spec['fin_art'][:4]; mode = spec['fin_art'][4] if len(spec['fin_art']) > 4 else 'mirror'   # 'text' for lettering
        c.fin_decal(img() if callable(img) else img, fu, fv, h, where=c.fin_proper(), mode=mode)
    if spec.get('extra'): spec['extra'](c)
    c.engines(spec.get('eng', '#F2F3F4'), lip=spec.get('lip', '#B9BDC2')); c.tips(spec.get('tips', spec.get('tail', '#DADCDE')))
    c.hstab(spec.get('hstab', '#DADCDE')); c.pylons(spec.get('pylon', '#E4E6E8'))


def reg_std(code, name, version, since, refs, colors, types, runtime, status, spec):
    LIVERIES[code] = dict(code=code, name=name, version=version, since=since, refs=refs, colors=colors, types=types, runtime=runtime,
                          status=status, paint=lambda c, s=spec: std(c, s))


def svg_mark(body, vb='0 0 100 100'):
    return lambda n=1024: art.svg(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">{body}</svg>', n)


def photo_fin(pts, le, te, root, tip):
    """points measured on a reference photo's fin crop (x, y in % of the crop, x from the leading edge side, y down) ->
    fin design coordinates (fu 0 LE .. 1 TE along the local chord, fv 0 root .. 1 tip): le / te = ((x, y), (x, y)) two
    points on the leading / trailing edge lines, root / tip = y of the fin root and tip in the crop"""
    (lx0, ly0), (lx1, ly1) = le; (tx0, ty0), (tx1, ty1) = te
    out = []
    for x, y in pts:
        xl = lx0 + (y - ly0) * (lx1 - lx0) / (ly1 - ly0); xt = tx0 + (y - ty0) * (tx1 - tx0) / (ty1 - ty0)
        out.append(((x - xl) / (xt - xl), (root - y) / (root - tip)))
    return out


def flag_image(kind, n=256):
    """small national flags as painted next to titles / registrations (public symbols; simplified construction)"""
    from PIL import Image, ImageDraw
    if kind == 'JP':      # Japan: white field (thin grey keyline on a white body), red disc of 3/5 the height
        W, H = int(1.5 * n), n; im = Image.new('RGBA', (W * 4, H * 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W * 4 - 1, H * 4 - 1], fill='#FFFFFF', outline='#9A9EA3', width=max(4, n // 16))
        r = 0.3 * H * 4; d.ellipse([W * 2 - r, H * 2 - r, W * 2 + r, H * 2 + r], fill='#BC002D')
        return im.resize((W, H), Image.LANCZOS)
    raise ValueError(kind)


def outline_title(text, fam, weight, color, px=420, ring=0.42, stretch=1.0, spacing=0.05):
    """letters drawn as a thick outline with an open (white) core, as Fiji Airways' FIJI (photo): ink where the distance to
    the letter edge is < ring x the half stroke width"""
    from PIL import Image
    from scipy.ndimage import distance_transform_edt
    t = text_image(text, font(fam, weight), px, '#000000', spacing=spacing, stretch=stretch)
    a = np.asarray(t)[..., 3].astype(np.float32) / 255
    d = distance_transform_edt(a > 0.5)
    half = np.percentile(d[d > 0], 97)
    ink = np.clip((ring * half - d + 1.0), 0, 1) * a
    from common import hex_rgb
    out = np.zeros(a.shape + (4,), np.uint8); out[..., :3] = (np.array(hex_rgb(color)) * 255).astype(np.uint8); out[..., 3] = (ink * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


APPROX = 'approx (no official value found; from the reference image)'
NOR = 'https://www.norebbo.com/{}-livery/ (profile drawing; layout reference only)'

# ---- Cathay Pacific (2015 refresh)
def cx_brushwing(n=1024, fg='#FFFFFF', bg='#006564'):
    """Cathay Pacific's brushwing (re-drawn from the photo of B-LRA, starboard side, then mirrored so that the wing tip
    points forward): a crescent wing with a pointed lower tail, its upper part broken into brush strokes (gaps drawn in
    the background colour `bg`)"""
    gaps = ''.join(f'<path d="M{181 + 5.5 * k} {160 + 3 * k} C{193 + 6 * k} {232 + 2 * k} {214 + 6.5 * k} {292 + k} {238 + 8 * k} {322 + 5 * k}" '
                   f'stroke="{bg}" stroke-width="3.4" fill="none"/>' for k in range(1, 6))
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="160 140 380 420">
<path d="M178 158 C190 230 215 300 250 345 C280 385 310 425 335 455 L268 540 L360 470 C420 455 480 440 522 428 C470 400 380 370 320 345
 C280 320 250 270 235 230 C225 205 212 185 205 175 Z" fill="{fg}"/>{gaps}</svg>'''
    from PIL import ImageOps
    return ImageOps.mirror(art.svg(s, n))


CX_PHOTOS = ('photo check (reference only, Wikimedia Commons): "Cathay Pacific (B-LRU) Airbus A350-941 at Sydney Airport.jpg" (layout measured: '
             'title sn 0.126-0.331, 0.147 H, grey lower body from just below the windows, nose brushwing) and "(AUS-Victoria) Cathay Pacific Airbus A350-941 '
             'B-LRA @ YMML 2025-12-06.jpg" (brushwing)')


def cathay(c):
    base(c, '#F7F8F8')
    fus = c.fuselage()
    belly(c, [(0, -0.2), (0.05, 0.08), (0.12, 0.12), (0.85, 0.12), (0.95, 0.3), (1.0, 0.6)], '#C9CED1')
    title(c, 'CATHAY PACIFIC', 'Libre Baskerville', 700, '#005C5A', 0.147, d1(c, 0.24), dy=0.165, spacing=0.02)
    # small brushwing on the nose, below the flight deck (photo: sn 0.061-0.087, 0.29 H tall, centred 0.05 H below the windows)
    c.decal(cx_brushwing(512, fg='#006564', bg='#F7F8F8'), 0.061 * c.L, c.winY - 0.05 * c.H, 0.29 * c.H, mode='mirror', where=fus)
    fin_all(c, '#006564')
    if c.fin is not None:
        c.fin_decal(cx_brushwing(), 0.52, 0.42, 0.78, where=c.fin_proper())
    c.engines('#F2F3F4'); c.tips('#006564'); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['CPA'] = dict(code='CPA', name='Cathay Pacific', version='2015 livery (all-green tail with the white brushwing, grey lower body, name above the windows, brushwing on the nose)',
                       since=2015, refs=['https://news.cathaypacific.com/new-era-begins-for-cathay-pacific-as-airline-unveils-changes-to-aircraft-livery-141164 (1 Nov 2015: "Cathay Pacific green, grey and white")',
                                         NOR.format('cathay-pacific'), CX_PHOTOS],
                       colors=dict(green=('#006564', APPROX), grey=('#C9CED1', APPROX), title=('#005C5A', APPROX)), types=['A359'],
                       runtime=dict(top='#F7F8F8', belly='#C9CED1', tail='#006564', tail2='#FFFFFF', eng='#F2F3F4', bellyLine=0.12),
                       status='layout measured on photos of A350-900s; brushwing re-drawn from a photo; colours approx', paint=cathay)

# ---- EVA Air
reg_std('EVA', 'EVA Air', '2015 update (green tail with the orange globe, darker green belly)', 2015,
        ['https://www.airlinereporter.com/2015/11/eva-air-shows-off-new-livery-vision-future/ (darker green belly, orange removed from the rudder)'],
        dict(green=('#00674F', APPROX), title=('#249243', 'measured on the photo B-17887 (refs/cache/livref EVA_1)'), orange=('#F29400', APPROX)), ['B789'],
        dict(top='#F7F8F8', belly='#2E5D4B', tail='#00674F', tail2='#F29400', eng='#F2F3F4', bellyLine=-0.55), 'from the description; globe simplified',
        dict(belly=('#2E5D4B', [(0, -1.2), (0.05, -0.8), (0.2, -0.55), (0.8, -0.55), (0.92, -0.3), (1, 0.2)]),
             cheat=[('#F29400', [(0.05, -0.72), (0.2, -0.47), (0.8, -0.47), (0.92, -0.22)], 0.02)],
             extra=lambda c: title_span(c, 'EVA AIR', 'Montserrat', 800, '#249243', 0.2, 0.14 * c.L, 0.30 * c.L, 0.2, spacing=0.02, italic=True), tail='#00674F', tips='#F2F3F4',
             fin_art=(svg_mark('<circle cx="50" cy="50" r="46" fill="#FFFFFF"/><circle cx="50" cy="50" r="40" fill="none" stroke="#F29400" stroke-width="5"/>'
                               '<circle cx="50" cy="50" r="30" fill="#00674F"/><path d="M50 22 L55 45 L78 50 L55 55 L50 78 L45 55 L22 50 L45 45 Z" fill="#FFFFFF"/>'), 0.5, 0.55, 0.42)))

# ---- China Airlines
reg_std('CAL', 'China Airlines', 'plum-blossom tail (1995 identity), white fuselage', 1995,
        ['https://www.china-airlines.com/ (brand; not fetched)', photo_ref('CAL', 'A350-900s B-18906 / B-18918 (port side): CHINA AIRLINES sn 0.305-0.46 aft of door 2 above the windows, no Chinese title on this side, plum blossom on the fin')], dict(pink=('#D8567E', APPROX), violet=('#6B3E8E', APPROX), blue=('#1D3A7A', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#D8567E', eng='#F2F3F4'), 'title position measured on photos; blossom simplified; colours approx',
        dict(extra=lambda c: (title_span(c, 'CHINA AIRLINES', 'Libre Baskerville', 700, '#1D3A7A', 0.15, 0.305 * c.L, 0.46 * c.L, 0.20, spacing=0.02),
                              c.decal(art.circle(128, color='#D0202E'), 0.466 * c.L, c.winY + 0.20 * c.H, 0.07 * c.H, mode='mirror', where=c.fuselage())),
             cheat=[('#7F8FC6', [(0.02, -0.55), (0.1, -0.45), (0.3, -0.55), (0.5, -0.7)], 0.10)],
             fin_art=(svg_mark(''.join(f'<ellipse cx="{50 + 26 * np.cos(a):.1f}" cy="{50 + 26 * np.sin(a):.1f}" rx="20" ry="13" transform="rotate({np.degrees(a):.0f} {50 + 26 * np.cos(a):.1f} {50 + 26 * np.sin(a):.1f})" fill="#D8567E"/>' for a in np.linspace(0, 2 * np.pi, 5, endpoint=False) - np.pi / 2) + '<circle cx="50" cy="50" r="10" fill="#6B3E8E"/>'), 0.5, 0.52, 0.62)))

# ---- Singapore Airlines
SQ = dict(blue='#1A2C5B', gold='#CDA851', orange='#F28C28', band='#BFA058', red='#EF3340', white='#F7F8F8')
SQ_PHOTOS = ('photo check (reference only, Wikimedia Commons): "(SGP-Singapore) Singapore Airlines Airbus A350-941 9V-SHL @ WSSS 2025-11-19.jpg" '
             '(layout measured: navy window band, orange line and gold band from just aft of door 1 to the tail cone, title sn 0.127-0.414, '
             'orange trailing-edge stripe on the fin, Kris bird) and "Singapore Airlines Airbus A350 9V-SMK Singapore 2025 (01).jpg"')


def kris_bird(n=1024, color=SQ['gold']):
    """the Kris bird, strongly simplified (re-drawn from the photo): three parallel wing bands running down aft, bending
    down into nested hooks (drawn facing aft as seen on the starboard side, mirrored to face forward)"""
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="20 30 600 660"><g fill="none" stroke="{color}" stroke-width="50" stroke-linejoin="round">
<path d="M140 62 L408 330 Q432 360 420 402 L380 540"/>
<path d="M94 158 L338 402 Q360 428 350 462 L318 566 Q306 610 350 612 L420 612 Q470 612 492 560 L512 505"/>
<path d="M50 254 L262 466 Q284 492 274 526 L246 616 Q234 662 280 664 L430 664 Q510 664 548 580 L592 488"/></g></svg>'''
    from PIL import ImageOps
    return ImageOps.mirror(art.svg(s, n))


def singapore(c):
    base(c, SQ['white'])
    fus = c.fuselage()
    aft = fus & (c.s > 0.11 * c.L)
    for lo, hi, col in ((0.09, 0.375, SQ['blue']), (0.04, 0.075, SQ['orange']), (-0.125, 0.025, SQ['band'])):
        ya = c.curve([(0, lo), (1, lo)], 'sn'); yb = c.curve([(0, hi), (1, hi)], 'sn')
        c.paint(c.aa(np.maximum(ya - c.y, c.y - yb)) * aft, col)
    title_span(c, 'SINGAPORE AIRLINES', 'Montserrat', 600, SQ['blue'], 0.144, 0.127 * c.L, 0.414 * c.L, 0.155, spacing=0.12)
    fl = art.poly_image([([(0, 0), (1, 0), (1, 0.5), (0, 0.5)], SQ['red']), ([(0, 0.5), (1, 0.5), (1, 1), (0, 1)], '#FFFFFF')], 256, aspect=1.5)
    c.decal(fl, 0.425 * c.L, c.winY + 0.165 * c.H, 0.1 * c.H, mode='mirror', where=fus)
    fin_all(c, SQ['blue'])
    if c.fin is not None:
        c.poly([(0.955, -0.3), (1.3, -0.3), (1.3, 1.3), (0.955, 1.3)], SQ['orange'], 'fin', where=c.fin_proper())
        c.fin_decal(kris_bird(), 0.5, 0.5, 0.62, where=c.fin_proper())
    c.engines('#F2F3F4'); c.tips(SQ['blue']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['SIA'] = dict(code='SIA', name='Singapore Airlines', version='midnight-blue tail with the gold Kris bird; navy window band with orange and gold lines', since=1972,
                       refs=['https://airlinegeeks.com/2026/08/21/livery-of-the-week-singapore-airlines/ (midnight blue and gold, essentially unchanged)', SQ_PHOTOS],
                       colors={k: (v, 'measured on the photos (approx; not an official value)') for k, v in SQ.items()}, types=['A359'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#1A2C5B', tail2='#CDA851', eng='#F2F3F4', stripe='#1A2C5B'),
                       status='layout measured on photos of A350-900s; Kris bird re-drawn (simplified); title face a look-alike', paint=singapore)

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
             extra=lambda c: c.fin_decal(text_image('ANA', font('Montserrat', 800, True), 420, '#FFFFFF'), 0.5, 0.52, 0.2, rotate=-55, mode='text')))

# ---- Japan Airlines
JL_RED = '#CC0000'


def tsurumaru(n=1024, red=JL_RED):
    """JAL's Tsurumaru (crane circle), re-drawn from the photo of JA864J (refs/cache/livref JAL_1, fin crop): a red disc
    whose white centre is framed by the crane's two wings (the ring, with three white feather slits on each side); the
    head with its long beak points forward inside the top of the ring, the neck curves down in an S to the tail feathers
    at the bottom; white italic JAL in the lower red part. Drawn facing left (forward on the port side)."""
    from PIL import Image
    slit = lambda k, sgn: (f'<path d="M{50 + sgn * (40 - 5 * k)} {42 - 4 * k} C{50 + sgn * (40 - 4 * k)} {58 - 2 * k} {50 + sgn * (34 - 5 * k)} {68 - 2 * k} '
                           f'{50 + sgn * (24 - 5 * k)} {73 - k}" stroke="#FFFFFF" stroke-width="1.9" fill="none" stroke-linecap="round"/>')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<circle cx="50" cy="50" r="48" fill="{red}"/>
<path d="M50 7 C71 7 82 24 82 42 C82 58 71 69 58 72 L50 73 L42 72 C29 69 18 58 18 42 C18 24 29 7 50 7 Z" fill="#FFFFFF"/>
<path d="M61 21 C70 27 67 39 57 47 C49 54 45 62 49 72" stroke="{red}" stroke-width="6.5" fill="none" stroke-linecap="round"/>
<ellipse cx="60" cy="20.5" rx="7" ry="4.6" fill="{red}"/>
<path d="M55 18.5 L28 19.5 L55 23.5 Z" fill="{red}"/>
{''.join(slit(k, s) for k in range(3) for s in (-1, 1))}
</svg>"""
    img = art.svg(svg, n)
    t = text_image('JAL', font('Montserrat', 800, True), 420, '#FFFFFF', spacing=0.02)
    w = int(0.46 * n); h = int(w * t.size[1] / t.size[0])
    img.alpha_composite(t.resize((w, h), Image.LANCZOS), (int(0.5 * n - w / 2), int(0.83 * n - h / 2)))
    return img


def japan_airlines(c):
    base(c, '#F7F8F8')
    fus = c.fuselage()
    # title and the small flag after it (photo JA864J: title sn 0.16-0.43, the Hinomaru flag right after the S; the earlier
    # plain red dot is now the flag with its keyline)
    # (title + flag as one image: the flag follows the title in reading order on both sides; starboard order inf)
    from PIL import Image
    t = text_image('JAPAN AIRLINES', font('Montserrat', 800, True), 420, '#1A1A1A', spacing=0.06)
    fl = flag_image('JP'); fh = int(0.5 * t.size[1]); fl = fl.resize((int(fh * fl.size[0] / fl.size[1]), fh), Image.LANCZOS)
    gap = int(0.3 * t.size[1]); im = Image.new('RGBA', (t.size[0] + gap + fl.size[0], t.size[1]), (0, 0, 0, 0))
    im.alpha_composite(t); im.alpha_composite(fl, (t.size[0] + gap, int(0.12 * t.size[1])))
    h = 0.157 * c.H; w = 0.267 * c.L * im.size[0] / t.size[0]; im = im.resize((max(1, int(im.size[1] * w / h)), im.size[1]))
    c.decal(im, 0.156 * c.L, c.winY + 0.168 * c.H, h, mode='text', where=fus)
    fin_all(c, '#F7F8F8')
    if c.fin is not None:
        # crane circle: centre fu 0.52, fv 0.50, diameter 0.50 of the fin height (photo)
        c.fin_decal(tsurumaru(), 0.52, 0.50, 0.50, where=c.fin_proper())
    c.engines('#F2F3F4'); c.tips('#F2F3F4'); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['JAL'] = dict(code='JAL', name='Japan Airlines', version='2011 "Tsurumaru" crane livery', since=2011,
                       refs=['https://www.japantimes.co.jp/news/2011/03/01/business/jal-revives-crane-logo-in-return-to-basics/', NOR.format('japan-airlines'),
                             photo_ref('JAL', 'title sn 0.16-0.43 with the Japanese flag after it, Tsurumaru crane circle on a white fin')],
                       colors=dict(red=(JL_RED, APPROX)), types=['B788', 'B789'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#CC0000', eng='#F2F3F4'),
                       status='layout measured on a photo of a 787-9; crane circle re-drawn (vector) from the photo', paint=japan_airlines)

# ---- Qantas (2016 Flying Kangaroo)
reg_std('QFA', 'Qantas', '2016 livery (red tail with the streamlined kangaroo, red wrapping onto the aft body)', 2016,
        [NOR.format('qantas') + ' (787-9 profile)'], dict(red=('#E40000', APPROX)), ['B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#E40000', tail2='#FFFFFF', eng='#F2F3F4'), 'kangaroo simplified',
        dict(extra=lambda c: title_span(c, 'QANTAS', 'Montserrat', 700, '#3C3C3C', 0.22, 0.136 * c.L, 0.325 * c.L, 0.12, spacing=0.12), tail='#E40000', aft=('#E40000', 0.6, -1.0, -1.0),
             fin_art=(svg_mark('<path d="M20 80 C30 60 44 50 60 46 L70 30 L74 44 C84 44 90 52 88 60 L70 58 C60 62 50 70 44 84 L36 70 Z" fill="#FFFFFF"/>'), 0.55, 0.5, 0.62)))

# ---- Philippine Airlines
reg_std('PAL', 'Philippine Airlines', 'flag-motif tail (blue and red triangles, yellow sun)', 1986,
        ['https://www.philippineairlines.com/ (brand; not fetched)'], dict(blue=('#1B3F94', APPROX), red=('#CE1126', APPROX), yellow=('#FCD116', APPROX)), ['A359'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#1B3F94', tail2='#CE1126', eng='#F2F3F4'), 'approx; at SFO mostly the 777-300ER (procedural)',
        dict(extra=lambda c: title_span(c, 'Philippines', 'Montserrat', 800, '#1B3F94', 0.16, 0.12 * c.L, 0.30 * c.L, 0.17, spacing=0.0, italic=True), tail='#F7F8F8',
             fin_polys=[('#1B3F94', [(-0.2, 0.55), (1.2, 0.55), (1.2, 1.2), (-0.2, 1.2)]), ('#CE1126', [(-0.2, -0.3), (1.2, -0.3), (1.2, 0.5), (-0.2, 0.5)]), ('#F7F8F8', [(-0.2, -0.3), (0.55, 0.52), (-0.2, 1.2)])],
             fin_art=(lambda n=1024: art.circle(n, color='#FCD116'), 0.15, 0.52, 0.18)))

# ---- Air France
AF = dict(navy='#1B2A5A', red='#D2232A', white='#F7F8F8', gold='#C9A24B')


def air_france(c):
    base(c, AF['white'])
    fus = c.fuselage()
    # photo F-HUVE (refs/cache/livref AFR_2, port side): AIRFRANCE sn 0.135-0.385, letters' feet on the window tops; the
    # red slash right after the title
    # title + slash as one image, so the slash follows the title in reading order on both sides (photo: the slash is about
    # one letter wide, 0.35 of the cap height, on the baseline, right after the E)
    from PIL import Image, ImageDraw
    t = text_image('AIRFRANCE', font('Montserrat', 800), 420, AF['navy'], spacing=0.08)
    ch = t.size[1]; sw = int(0.95 * ch); gap = int(0.22 * ch); sh = int(0.36 * ch)
    im = Image.new('RGBA', (t.size[0] + gap + sw, ch), (0, 0, 0, 0)); im.alpha_composite(t)
    x0 = t.size[0] + gap; yb = ch - int(0.06 * ch)
    ImageDraw.Draw(im).polygon([(x0, yb), (x0 + int(0.7 * sw), yb), (x0 + sw, yb - sh), (x0 + int(0.3 * sw), yb - sh)], fill=AF['red'])
    h = 0.17 * c.H; w = 0.25 * c.L * im.size[0] / t.size[0]
    im = im.resize((max(1, int(im.size[1] * w / h)), im.size[1]))
    c.decal(im, 0.135 * c.L, c.winY + 0.20 * c.H, h, mode='text', where=fus)
    fin_all(c, AF['white'])
    if c.fin is not None:
        fin = c.fin_proper()
        # stripes parallel to the leading edge over the whole fin height (photo, chordwise fractions at mid height): navy
        # 0.12-0.40, navy 0.47-0.55, 0.60-0.64, 0.67-0.69; red 0.76-0.97 up to 0.72 of the fin height
        for a, b in ((0.12, 0.40), (0.47, 0.55), (0.60, 0.64), (0.67, 0.69)):
            c.poly([(a, -0.05), (b, -0.05), (b, 1.2), (a, 1.2)], AF['navy'], 'fin', where=fin)
        c.poly([(0.76, -0.05), (0.97, -0.05), (0.97, 0.66), (0.93, 0.72), (0.76, 0.72)], AF['red'], 'fin', where=fin)
        c.fin_decal(art.svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">' + ''.join(
            f'<circle cx="{50 + 38 * np.cos(a):.1f}" cy="{50 + 38 * np.sin(a):.1f}" r="7" fill="{AF["gold"]}"/>' for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)) + '</svg>', 256),
            0.30, 0.78, 0.09, where=fin)
    c.engines('#F2F3F4'); c.tips(AF['navy']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['AFR'] = dict(code='AFR', name='Air France', version='Eurowhite livery with the tricolour tail stripes', since=2009,
                       refs=['https://corporate.airfrance.com/ (brand; not fetched)', photo_ref('AFR', 'fin stripes parallel to the leading edge: one broad and three thin navy, one red on the lower aft fin; AIRFRANCE with the red slash')],
                       colors={k: (v, APPROX + '; measured on the photo') for k, v in AF.items()}, types=['A359'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#F7F8F8', tail2='#1B2A5A', eng='#F2F3F4'),
                       status='layout measured on a photo of an A350-900 (port side); colours approx', paint=air_france)

# ---- British Airways (Chatham Dockyard)
BA = dict(blue='#01213F', red='#E4002B', flagblue='#23408E', white='#F7F8F8')
BA_PHOTOS = ('photo check (reference only, Wikimedia Commons): "(GBR-London) British Airways Airbus A380-841 G-XLEH @ EGLL 2025-06-17.jpg" (layout '
             'measured: title between the decks sn 0.148-0.355, 0.156 H; speedwing ribbon at the upper-deck windows; blue belly; three ribbons '
             'of the Chatham Dockyard tail)')


def british_airways(c):
    base(c, BA['white'])
    fus = c.fuselage()
    belly(c, [(0, -0.55), (0.03, -0.64), (0.1, -0.68), (0.6, -0.68), (0.75, -0.62), (0.85, -0.5), (0.93, -0.2)], BA['blue'])
    title_span(c, 'BRITISH AIRWAYS', 'Libre Baskerville', 700, BA['blue'], 0.156, 0.148 * c.L, 0.355 * c.L, eta=0.127, spacing=0.02)
    # speedwing: red ribbon at the upper-deck window line, blue blade under its front (photo)
    c.poly([(0.103, 0.585), (0.125, 0.65), (0.20, 0.665), (0.232, 0.645), (0.20, 0.61), (0.125, 0.545)], BA['red'], 'cabin', where=fus)
    c.poly([(0.093, 0.47), (0.103, 0.36), (0.125, 0.16), (0.13, 0.14), (0.118, 0.30), (0.108, 0.43)], BA['flagblue'], 'cabin', where=fus)
    fin = c.fin_proper()
    fin_all(c, BA['white'], dorsal=False)
    if c.fin is not None:
        # Chatham Dockyard tail: three ribbons (red, blue, red) wide at the trailing edge, tapering forward (photo, port side)
        c.poly([(0.05, 0.47), (0.3, 0.52), (0.6, 0.62), (0.9, 0.76), (1.25, 0.92), (1.25, 0.49), (0.6, 0.46)], BA['red'], 'fin', where=fin)
        c.poly([(0.11, 0.32), (0.4, 0.36), (0.7, 0.39), (1.25, 0.44), (1.25, 0.20), (0.7, 0.24), (0.4, 0.28)], BA['flagblue'], 'fin', where=fin)
        c.poly([(0.06, 0.12), (0.4, 0.14), (0.7, 0.15), (1.25, 0.16), (1.25, -0.3), (0.6, -0.1), (0.3, 0.04)], BA['red'], 'fin', where=fin)
    c.engines(BA['blue']); c.tips(BA['blue']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['BAW'] = dict(code='BAW', name='British Airways', version='Chatham Dockyard Union-flag tail, midnight-blue belly, red / blue speedwing', since=1997,
                       refs=['https://www.key.aero/article/how-british-airways-got-its-latest-livery', 'https://simpleflying.com/british-airways-livery-evolution/',
                             NOR.format('british-airways') + ' (A350-1000, A380 profiles)', BA_PHOTOS],
                       colors={k: (v, APPROX) for k, v in BA.items()}, types=['A388'],
                       runtime=dict(top='#F7F8F8', belly='#01213F', tail='#F7F8F8', tail2='#E4002B', eng='#01213F', bellyLine=-0.68),
                       status='layout measured on a photo of the A380 (port side); tail ribbons and speedwing simplified; colours approx', paint=british_airways)

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
EK = dict(gold='#B8893B', red='#D71A21', green='#00843D', black='#1A1A1A', white='#F7F8F8')
EK_PHOTOS = ('photo check (reference only, Wikimedia Commons): "(GBR-London) Emirates Airbus A380-861 A6-EUH @ EGLL 2025-06-18.jpg" (layout measured: '
             'title sn 0.164-0.354 between the decks, Arabic title aft of it, flag stripes and the red band sweeping from the fin onto the body)')


def emirates(c):
    base(c, EK['white'])
    fus = c.fuselage()
    title_span(c, 'Emirates', 'Libre Baskerville', 700, EK['gold'], 0.30, 0.164 * c.L, 0.354 * c.L, eta=0.29, spacing=0.0)
    # Arabic title aft of the English one on the same line (photo A6-EUH, starboard: sn 0.375-0.45, about 0.6 of the English
    # height); Aref Ruqaa (OFL) as a look-alike of the calligraphy. Port side: same stations (inf)
    ar = text_shaped('الإمارات', font('Aref Ruqaa', 700), 300, EK['gold'], 'rtl')
    h = 0.20 * c.H; w = 0.075 * c.L; ar = ar.resize((max(1, int(ar.size[1] * w / h)), ar.size[1]))
    c.decal(ar, 0.375 * c.L, c.ycM + 0.29 * c.hhM, h, mode='text', where=fus)
    fin = c.fin_proper()
    fin_all(c, EK['white'], dorsal=False)
    if c.fin is not None:
        # UAE flag on the fin: green, white, black bands sloping with the fin, the red band along the leading edge
        # (photo, starboard: the stripes run from the trailing edge to the red band, which descends from 0.7 of the fin
        # height near mid-chord to the whole front third of the fin root)
        c.poly([(0.47, 1.3), (1.3, 1.3), (1.3, 0.64), (0.42, 0.66)], EK['green'], 'fin', where=fin)
        c.poly([(0.3, 0.44), (1.3, 0.47), (1.3, 0.19), (0.32, 0.12)], EK['black'], 'fin', where=fin)
        c.poly([(0.52, 0.70), (0.44, 0.60), (0.32, 0.44), (0.33, 0.0), (0.33, -0.4), (-0.4, -0.4), (-0.4, 0.3), (0.0, 0.46), (0.25, 0.60)], EK['red'], 'fin', where=fin)
        # the red band continues onto the body, down to the wing root (photo: crown sn 0.685-0.73, lower end sn 0.674-0.707 at eta 0.1)
        c.poly([(0.685, 1.3), (0.735, 1.3), (0.707, 0.10), (0.674, 0.10)], EK['red'], 'cabin', where=fus)
    c.engines('#F2F3F4'); c.tips(EK['red']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['UAE'] = dict(code='UAE', name='Emirates', version='livery with the UAE-flag tail and gold titles (as photographed on the A380 in 2025; the 2023 update is being applied gradually)',
                       since=1999, refs=[NOR.format('emirates') + ' (A380 2023 profile; colour chart #E4AB2C titles, #018557 green: third party)', EK_PHOTOS],
                       colors={k: (v, APPROX) for k, v in EK.items()}, types=['A388'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#D71A21', tail2='#00843D', eng='#F2F3F4'),
                       status='layout measured on a 2025 photo of the A380 (starboard); Arabic title in an OFL calligraphic look-alike; flag simplified', paint=emirates)

# ---- Turkish Airlines
reg_std('THY', 'Turkish Airlines', 'red tail with the goose in a white circle, grey tulip stripe', 2010,
        ['https://www.turkishairlines.com/ (brand; not fetched)'], dict(red=('#C70A0C', APPROX)), ['A359', 'B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#C70A0C', tail2='#FFFFFF', eng='#F2F3F4'), 'goose simplified',
        dict(extra=lambda c: title_span(c, 'TURKISH AIRLINES', 'Montserrat', 800, '#23305C', 0.15, 0.145 * c.L, 0.393 * c.L, 0.17, spacing=0.03),
             tail='#C70A0C', dorsal=False,
             cheat=[('#B5B9BF', [(0.35, -0.3), (0.6, -0.1), (0.8, 0.3)], 0.05)],
             fin_art=(svg_mark('<circle cx="50" cy="50" r="42" fill="#FFFFFF"/><path d="M24 58 C36 46 50 40 70 36 L80 28 L78 40 C70 50 56 56 40 58 L30 70 Z" fill="#C70A0C"/>'), 0.52, 0.52, 0.6)))

# ---- Virgin Atlantic (2019)
VS = dict(body='#EDEDEF', red='#DA0530', title='#2E2A48', white='#FFFFFF', flagblue='#012169', flagred='#C8102E')
VS_PHOTOS = photo_ref('VIR', 'layout: light silver body, large thin lowercase title across the windows sn 0.15-0.47 in dark purple (measured #2C344B '
                      'on the anti-aliased strokes), red tail with the large white Virgin signature over the middle of the fin, red continuing onto '
                      'the lower tail cone, red nacelles; the flying icon (a figure with the Union flag) and the type name on the nose')
TYPE_NAMES = dict(b789='BOEING 787-9', b788='BOEING 787-8', b78x='BOEING 787-10', a35k='AIRBUS A350-1000', a359='AIRBUS A350-900', a339='AIRBUS A330-900')


def union_flag(n=256):
    """Union flag (public symbol), simplified construction (St George cross over the saltires)"""
    W, H = 2 * n, n
    return art.svg(f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 30"><rect width="60" height="30" fill="{VS['flagblue']}"/>
<path d="M0 0 L60 30 M60 0 L0 30" stroke="#FFFFFF" stroke-width="6"/><path d="M0 0 L60 30 M60 0 L0 30" stroke="{VS['flagred']}" stroke-width="2"/>
<path d="M30 0 V30 M0 15 H60" stroke="#FFFFFF" stroke-width="10"/><path d="M30 0 V30 M0 15 H60" stroke="{VS['flagred']}" stroke-width="6"/></svg>""", H)


def flying_icon(n=512):
    """the nose 'flying icon' (a figure holding the Union flag), strongly simplified: a red outline figure leaning forward
    with the flag streaming behind (re-drawn from the photo of G-VOWS)"""
    from PIL import Image
    fig = art.svg(f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"><g fill="none" stroke="{VS['red']}" stroke-width="2.4" stroke-linecap="round">
<circle cx="12" cy="14" r="5"/><path d="M16 18 C28 26 40 30 52 30 M22 22 L10 36 M40 29 C44 40 40 50 30 54 M48 30 C54 40 58 46 70 50"/></g></svg>""", n)
    fl = union_flag(n // 3).rotate(-12, expand=True, resample=Image.BICUBIC)
    out = Image.new('RGBA', fig.size, (0, 0, 0, 0)); out.alpha_composite(fig)
    out.alpha_composite(fl.resize((int(fig.size[0] * 0.42), int(fig.size[0] * 0.42 * fl.size[1] / fl.size[0]))), (int(fig.size[0] * 0.52), 0))
    return out


def virgin(c):
    base(c, VS['body'])
    fus = c.fuselage()
    title_span(c, 'virgin atlantic', 'Montserrat', 500, VS['title'], 0.36, 0.15 * c.L, 0.47 * c.L, 0.02, spacing=0.0)
    # flying icon between the flight deck and door 1, just below the window line; the type name below door 1 (photo)
    lockup(c, [(flying_icon(), 0.30 * c.H, c.winY - 0.12 * c.H, 0.0, 0.0)], c.doors[0] - 0.55 * c.H)
    if c.type in TYPE_NAMES:
        lockup(c, [(text_image(TYPE_NAMES[c.type], font('Montserrat', 600), 420, '#6E6A78', spacing=0.1), 0.045 * c.H, c.winY - 0.42 * c.H, 0.0, 0.0)], c.doors[0] + 0.4 * c.H)
    fin_all(c, VS['red'])
    if c.fin is not None:
        sle0 = np.polyval(c.fin['le'], c.fin['yR'])
        # red wrapping from the fin root down onto the lower tail cone
        c.poly([(sle0 / c.L - 0.02, 1.4), (sle0 / c.L + 0.03, -0.2), (0.93, -1.3), (1.2, -1.3), (1.2, 1.4)], VS['red'], 'cabin', where=fus)
        # the signature: large, white, rising toward the trailing edge over the middle of the fin (photo: about half the fin
        # height including the underline, centre fu 0.55, fv 0.45)
        img = text_image('Virgin', font('Kalam', 700), 420, VS['white'])
        from PIL import Image
        sw = art.svg(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20"><path d="M4 16 C30 8 60 4 96 3" stroke="#FFFFFF" stroke-width="3.2" fill="none" stroke-linecap="round"/></svg>', img.size[0] // 5)
        sig = Image.new('RGBA', (img.size[0], int(img.size[1] * 1.35)), (0, 0, 0, 0)); sig.alpha_composite(img)
        sig.alpha_composite(sw.resize((img.size[0], int(img.size[0] * sw.size[1] / sw.size[0]))), (0, int(img.size[1] * 0.95)))
        c.fin_decal(sig, 0.60, 0.46, 0.25, rotate=16.0, mode='text', where=c.fin_proper())
    c.engines(VS['red']); c.tips(VS['red']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['VIR'] = dict(code='VIR', name='Virgin Atlantic', version='2019 "Flying Icons" livery (light silver fuselage, red tail with the Virgin signature, purple titles)', since=2019,
                       refs=['https://www.virgin.com/about-virgin/latest/hello-virgin-atlantics-new-flying-icons', VS_PHOTOS],
                       colors={k: (v, APPROX) for k, v in VS.items()}, types=['B789', 'A35K'],
                       runtime=dict(top='#EDEDEF', belly='#EDEDEF', tail='#DA0530', tail2='#2E2A48', eng='#DA0530'),
                       status='layout from photos of 787-9s (one at SFO); flying icon strongly simplified (one figure for every aircraft; each aircraft has its own); signature in a script look-alike', paint=virgin)

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
AV = dict(red='#E30613', dark='#B0101C', orange='#FD653C', white='#F7F8F8')  # orange: the coral-orange of the fin-root wedge, measured on the photo
AV_PHOTOS = photo_ref('AVA', 'layout: red aft body sweeping from the belly under the wing trailing edge up to the fin, red nacelles, lowercase title')


def avianca(c):
    base(c, AV['white'])
    fus = c.fuselage()
    title_span(c, 'avianca', 'Montserrat', 700, AV['red'], 0.30, 0.15 * c.L, 0.40 * c.L, 0.05, spacing=0.0)
    # red aft body: below a line from the keel at sn 0.62 up to the crown at the fin leading edge (photos of N962AV, HK-5366)
    c.poly([(0.62, -1.4), (0.80, 1.4), (1.2, 1.4), (1.2, -1.4)], AV['red'], 'cabin', where=fus)
    fin = c.finzone()
    fin_all(c, AV['red'])
    if c.fin is not None:
        c.poly([(0.35, -0.3), (1.3, -0.3), (1.3, 0.55)], AV['dark'], 'fin', where=fin)
        # photo N962AV (review round 1: no orange stripe along the body boundary): a white wedge along the lower leading
        # edge and a small coral-orange wedge below it where the fin meets the crown; white tip triangle at the leading edge
        c.poly([(-0.9, 0.02), (-0.05, 0.10), (0.06, 0.26), (-0.9, 0.10)], '#FFFFFF', 'fin', where=fin)
        c.poly([(-0.9, -0.08), (-0.25, -0.08), (-0.05, 0.10), (-0.9, 0.02)], AV['orange'], 'fin', where=fin)
        c.poly([(-0.2, 0.80), (0.12, 0.80), (0.10, 1.2), (-0.2, 1.2)], '#FFFFFF', 'fin', where=fin)
    c.engines(AV['red']); c.tips(AV['red']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['AVA'] = dict(code='AVA', name='Avianca', version='2023 brand (lowercase avianca, brighter red; red tail, red aft body and nacelles)', since=2023,
                       refs=['https://www.avianca.com/en/about-us/av-news/2023/october-18/', 'https://airlinegeeks.com/2026/07/31/livery-of-the-week-avianca/', AV_PHOTOS],
                       colors={k: (v, APPROX) for k, v in AV.items()}, types=['A20N', 'A320'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#E30613', tail2='#F47B20', eng='#E30613'),
                       status='layout from 2025 photos of A320neos; the tail symbol is not drawn; fleet mid-transition (2023 brand rendered: inf)', paint=avianca)

# ---- Volaris
VO = dict(navy='#1A1438', fin='#0B1024', magenta='#C4219E', pink='#E07BE6', violet='#D34BD8', lilac='#E6A0F0', white='#F7F8F8',
          cyan='#3FC5E8', sky='#A6D8F0', blue='#4FB8EE', lime='#C8E650', green='#3DDD3D', green2='#6FE040')
VO_PHOTOS = photo_ref('VOI', 'layout measured on N531VL (port side): navy lowercase title sn 0.187-0.462 across the windows, 0.45 H, starting aft of '
                      'door 1; volaris.com above the windows sn 0.645-0.775; near-black navy fin with the pixel cross large and low (cells 0.135 of the '
                      'fin height, centre fu 0.42 fv 0.38); magenta nacelles; N531VL with the Mexican flag below the windows aft of the wing')
# pixel cross cells (column, row from the top-left of a 7 x 6 grid, measured on the photo's fin crop) and colours
VO_CELLS = [(2, 0, 'cyan'), (1, 1, 'cyan'), (2, 1, 'sky'), (3, 1, 'blue'), (0, 2, 'violet'), (1, 2, 'pink'), (2, 2, 'white'), (3, 2, 'lime'),
            (4, 2, 'green2'), (1, 3, 'magenta'), (2, 3, 'lilac'), (3, 3, 'green'), (2, 4, 'violet')]


def volaris_cross(n=768):
    cells = [([((i) / 5, (j) / 5), ((i + 1) / 5, (j) / 5), ((i + 1) / 5, (j + 1) / 5), ((i) / 5, (j + 1) / 5)], VO[k] if k != 'white' else '#FFFFFF')
             for i, j, k in VO_CELLS]
    return art.poly_image(cells, n)


def volaris(c):
    base(c, VO['white'])
    fus = c.fuselage()
    s0 = max(0.187 * c.L, c.doors[0] + 0.55)                    # aft of door 1 (review round 1: the v sat on the door)
    title_span(c, 'volaris', 'Nunito', 900, VO['navy'], 0.45, s0, 0.462 * c.L, 0.0, spacing=0.0)
    img = text_image('volaris.com', font('Nunito', 800), 420, VO['navy'])
    lockup(c, [(img, 0.13 * c.H, c.winY + 0.22 * c.H, 0.0, 0.0)], 0.645 * c.L)
    fin_all(c, VO['fin'])
    if c.fin is not None:
        # 5 x 5 grid of cells 0.135 fin heights each: grid centre at fu 0.40, fv 0.38 (photo)
        c.fin_decal(volaris_cross(), 0.40, 0.38, 0.675, where=c.fin_proper())
    c.engines(VO['magenta']); c.tips(VO['fin']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['VOI'] = dict(code='VOI', name='Volaris', version='white fuselage, navy lowercase title, navy tail with the pixel cross, magenta nacelles', since=2018,
                       refs=['https://www.volaris.com/ (brand; not fetched)', VO_PHOTOS], colors={k: (v, APPROX + '; measured on the photo') for k, v in VO.items()},
                       types=['A20N', 'A21N', 'A320'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#0B1024', tail2='#C4219E', eng='#C4219E'),
                       status='layout measured on a photo of an A320neo; colours measured on the photo (approx)', paint=volaris)

# ---- Copa
CM = dict(navy='#0E2D6E', white='#F7F8F8')
CM_PHOTOS = photo_ref('CMP', 'layout: mixed-case CopaAirlines title forward, navy fin with the white curved lines of the Copa globe on its lower half')


def copa(c):
    base(c, CM['white'])
    title_span(c, 'CopaAirlines', 'Montserrat', 700, CM['navy'], 0.15, 0.15 * c.L, 0.34 * c.L, 0.17, spacing=0.0)
    fin = c.finzone()
    fin_all(c, CM['navy'])
    if c.fin is not None:
        # the Copa globe: white meridian arcs fanning over the lower fin (simplified)
        for k in range(6):
            t = k / 5.0
            pts = [(0.05 + 0.9 * t + 0.25 * (1 - v) * (0.5 - t), v) for v in np.linspace(-0.2, 0.62 - 0.1 * abs(t - 0.5), 12)]
            q = pts + [(x + 0.045, v) for x, v in reversed(pts)]
            c.poly(q, '#FFFFFF', 'fin', where=c.fin_proper())
    c.engines('#E4E6E8'); c.tips(CM['navy']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['CMP'] = dict(code='CMP', name='Copa Airlines', version='white fuselage, CopaAirlines title, navy tail with the Copa globe', since=2005,
                       refs=['https://www.copaair.com/ (brand; not fetched)', CM_PHOTOS], colors={k: (v, APPROX) for k, v in CM.items()}, types=['B39M'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#0E2D6E', tail2='#FFFFFF', eng='#E4E6E8'),
                       status='layout from photos of 737 MAX 9s; globe lines simplified; colours approx', paint=copa)

# ---- KLM
KL = dict(blue='#00A1DE', dark='#1E6FA8', white='#F7F8F8')
KL_PHOTOS = photo_ref('KLM', 'layout: blue upper body down to a dark line just below the windows, white lower body, white fin with the blue crown logo; blue measured #0EA6DB')


def klm_logo(n=1024, color=KL['blue']):
    img = text_image('KLM', font('Montserrat', 800), 420, color)
    from PIL import Image
    crown = art.svg(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><g fill="{color}"><circle cx="20" cy="28" r="7"/><circle cx="40" cy="22" r="7"/>
<circle cx="60" cy="22" r="7"/><circle cx="80" cy="28" r="7"/><rect x="46" y="2" width="8" height="14"/><rect x="43" y="6" width="14" height="5"/></g></svg>''', 256)
    W = img.size[0]; ch = int(crown.size[1] * W * 0.62 / crown.size[0])
    out = Image.new('RGBA', (W, img.size[1] + ch + 10), (0, 0, 0, 0))
    out.alpha_composite(crown.resize((int(W * 0.62), ch)), (int(W * 0.19), 0)); out.alpha_composite(img, (0, ch + 10))
    return out


def klm(c):
    base(c, KL['blue'])
    fus = c.fuselage()
    y = belly(c, [(0, -0.35), (0.06, -0.1), (0.15, -0.05), (0.85, -0.05), (0.95, 0.15), (1, 0.45)], KL['white'])
    c.band(y + 0.01 * c.H, 0.02 * c.H, KL['dark'], where=fus)
    title(c, 'KLM', 'Montserrat', 800, '#FFFFFF', 0.2, d1(c, 0.45), dy=0.2, spacing=0.05)
    title(c, 'Royal Dutch Airlines', 'Montserrat', 600, '#FFFFFF', 0.055, d1(c, 0.45) + 0.62 * c.H, dy=0.17, spacing=0.02)
    fin_all(c, KL['white'])
    if c.fin is not None: c.fin_decal(klm_logo(), 0.5, 0.5, 0.26, mode='text', where=c.fin_proper())
    c.engines('#DADDE1'); c.tips(KL['blue']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['KLM'] = dict(code='KLM', name='KLM', version='blue upper fuselage, white lower body, white tail with the blue KLM crown logo', since=2014,
                       refs=['https://news.klm.com/ (brand; not fetched)', KL_PHOTOS], colors={k: (v, 'approx (blue measured on the photo: #0EA6DB)') for k, v in KL.items()},
                       types=['B78X', 'B789'], runtime=dict(top='#00A1DE', belly='#F7F8F8', tail='#F7F8F8', tail2='#00A1DE', eng='#DADDE1', bellyLine=-0.05),
                       status='layout from photos of a 787-10 and a 787-9; crown simplified', paint=klm)

# ---- Swiss (777 at SFO: runtime colours only)
reg_std('SWR', 'Swiss', 'red tail with the white Swiss cross', 2011, ['https://www.swiss.com/ (brand; not fetched)'], dict(red=('#E3000F', APPROX)), [],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#E3000F', tail2='#FFFFFF', eng='#F2F3F4'), '777-300ER only at SFO (procedural)',
        dict(title=('SWISS', 'Montserrat', 800, '#E3000F', 0.18), tail='#E3000F',
             fin_art=(svg_mark('<path d="M38 14 H62 V38 H86 V62 H62 V86 H38 V62 H14 V38 H38 Z" fill="#FFFFFF"/>'), 0.5, 0.5, 0.42)))

# ---- Asiana
AA2 = dict(body='#ECE8E2', navy='#2B3A67', tan='#C9A36A', yellow='#F4B324', orange='#EE7B22', red='#D8262E', maroon='#8C2332', blue='#2F56A6')
AAR_PHOTOS = photo_ref('AAR', 'layout: champagne body, ASIANA AIRLINES title aft of door 1, tail in wide diagonal bands')


def asiana(c):
    base(c, AA2['body'])
    title_span(c, 'ASIANA AIRLINES', 'Montserrat', 700, AA2['navy'], 0.11, 0.13 * c.L, 0.30 * c.L, 0.2, spacing=0.03)
    fin = c.finzone()
    fin_all(c, AA2['tan'])
    if c.fin is not None:
        cols = [AA2['yellow'], AA2['orange'], AA2['red'], AA2['maroon'], AA2['blue']]
        for k, col in enumerate(cols):
            a = 0.78 - 0.2 * k
            c.poly([(-0.4, a + 0.5), (1.4, a - 0.25), (1.4, a - 0.45), (-0.4, a + 0.3)], col, 'fin', where=fin)
    c.engines('#DCDAD6'); c.tips(AA2['red']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['AAR'] = dict(code='AAR', name='Asiana Airlines', version='champagne fuselage, tail in the Asiana colour bands', since=2006,
                       refs=['https://flyasiana.com/ (brand; not fetched)', AAR_PHOTOS], colors={k: (v, APPROX) for k, v in AA2.items()}, types=['A359'],
                       runtime=dict(top='#ECE8E2', belly='#ECE8E2', tail='#F4B324', tail2='#D8262E', eng='#DCDAD6'),
                       status='layout from photos of A350-900s; tail bands simplified; colours approx', paint=asiana)

# ---- Starlux
SX = dict(body='#EEEDEB', dark='#2B2622', bronze='#4A3B2F', gold='#B39664')
SX_PHOTOS = photo_ref('SJX', 'layout: champagne-silver body, large STARLUX title, bronze lower body with a gold line sweeping aft, white tail with the gold emblem, dark nacelles')


def starlux(c):
    base(c, SX['body'])
    fus = c.fuselage()
    y = belly(c, [(0, -0.9), (0.08, -0.62), (0.4, -0.55), (0.7, -0.45), (0.9, -0.1), (1, 0.3)], SX['bronze'])
    c.band(y + 0.03 * c.H, 0.03 * c.H, SX['gold'], where=fus)
    title_span(c, 'STARLUX', 'Montserrat', 500, SX['dark'], 0.30, 0.13 * c.L, 0.36 * c.L, 0.1, spacing=0.08)
    fin_all(c, '#F4F3F0')
    if c.fin is not None:
        c.poly([(0.35, 0.62), (0.62, 0.70), (0.58, 0.48), (0.31, 0.40)], SX['bronze'], 'fin', where=c.fin_proper())
        c.poly([(0.52, 0.38), (0.78, 0.46), (0.74, 0.24), (0.48, 0.16)], SX['gold'], 'fin', where=c.fin_proper())
        c.fin_decal(art.svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="M50 5 L57 43 L95 50 L57 57 L50 95 L43 57 L5 50 L43 43 Z" fill="#B39664"/></svg>', 256),
                    0.30, 0.80, 0.12, where=c.fin_proper())
    c.engines(SX['dark']); c.tips(SX['gold']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['SJX'] = dict(code='SJX', name='Starlux Airlines', version='champagne-silver body, bronze belly with a gold line, white tail with the emblem', since=2020,
                       refs=['https://www.starlux-airlines.com/ (brand; not fetched)', SX_PHOTOS], colors={k: (v, APPROX) for k, v in SX.items()}, types=['A359'],
                       runtime=dict(top='#EEEDEB', belly='#4A3B2F', tail='#F4F3F0', tail2='#B39664', eng='#2B2622', bellyLine=-0.55),
                       status='layout from photos of A350-900s; emblem simplified; colours approx', paint=starlux)

# ---- ZIPAIR
ZP = dict(teal='#2FB5A0', black='#141414', white='#F4F5F5', grey='#6D7278')
ZP_PHOTOS = photo_ref('TZP', 'layout: teal line through the window row, large black serif ZIPAIR below it forward, pale tail with diagonal dashes')


def zipair(c):
    base(c, ZP['white'])
    fus = c.fuselage()
    q = fus & (c.s > c.doors[0] + 0.5)
    c.band(np.full(len(c.y), c.winY), 0.55 * c.winH, ZP['teal'], where=q)
    title_span(c, 'ZIPAIR', 'Libre Baskerville', 700, ZP['black'], 0.30, 0.11 * c.L, 0.34 * c.L, -0.27, spacing=0.02)
    fin_all(c, '#E6E9EA')
    if c.fin is not None:
        for i in range(7):
            for j in range(3):
                u0 = 0.15 + 0.28 * j + 0.06 * i; v0 = 0.12 + 0.12 * i
                col = ZP['teal'] if (i + j) % 3 == 0 else ZP['grey']
                c.poly([(u0, v0), (u0 + 0.2, v0 + 0.035), (u0 + 0.2, v0 + 0.055), (u0, v0 + 0.02)], col, 'fin', where=c.fin_proper())
    c.engines('#DADCDE'); c.tips(ZP['teal']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['TZP'] = dict(code='TZP', name='ZIPAIR', version='white body, teal window line, large black ZIPAIR, pale tail with dashes', since=2020,
                       refs=['https://www.zipair.net/ (brand; not fetched)', ZP_PHOTOS], colors={k: (v, APPROX) for k, v in ZP.items()}, types=['B788'],
                       runtime=dict(top='#F4F5F5', belly='#F4F5F5', tail='#E6E9EA', tail2='#2FB5A0', eng='#DADCDE'),
                       status='layout from photos of 787-8s; tail dashes simplified; colours approx', paint=zipair)

# ---- Aer Lingus (2019)
reg_std('EIN', 'Aer Lingus', '2019 livery (teal tail with the white shamrock)', 2019, ['https://www.aerlingus.com/ (brand; not fetched)'],
        dict(teal=('#006272', APPROX), light=('#2CC1C5', APPROX)), ['A333', 'A332'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#006272', tail2='#FFFFFF', eng='#F2F3F4'), 'approx',
        dict(title=('Aer Lingus', 'Montserrat', 700, '#006272', 0.2, dict(k=0.5, dy=0.15)), tail='#006272',
             fin_art=(svg_mark('<circle cx="50" cy="32" r="16" fill="#FFFFFF"/><circle cx="33" cy="54" r="16" fill="#FFFFFF"/><circle cx="67" cy="54" r="16" fill="#FFFFFF"/><path d="M50 58 L56 92 L48 92 Z" fill="#FFFFFF"/>'), 0.5, 0.5, 0.55)))

# ---- Qatar Airways
QR = dict(grey='#C4C9CA', burgundy='#5C0631', arabic='#4A5157')
# the oryx, measured on the fin of A7-AMI (refs/cache/livref QTR_1, starboard side, crop mirrored to the port side: x from
# the leading-edge side, % of the crop; LE (7, 88)-(70, 5), TE (62, 97)-(98, 2), root y 93, tip y 3); re-drawn as polygons
QR_FIN = dict(le=((7, 88), (70, 5)), te=((62, 97), (98, 2)), root=93, tip=3)
QR_ORYX = [
    [(96, 8), (60, 37.5), (56, 42), (93, 11.5)],                                   # upper horn
    [(90, 21.5), (56, 42.5), (54, 46), (88, 25)],                                   # lower horn
    [(58, 41), (62, 44), (76, 47), (67, 52), (75, 61), (72, 63), (69, 72), (72, 74), (68, 82), (71, 84), (64, 97), (52, 97),
     (44, 87), (38, 87), (32, 90), (27, 89), (26, 84), (21, 82), (25, 72), (31, 62), (40, 52), (48, 44)],   # head, neck and mane
]
QR_FACE = [(45, 53), (48, 57), (50, 55), (51, 58), (49, 66), (46, 73), (43, 79), (40, 82), (43, 84), (48, 79), (53, 71), (55, 62), (53, 53), (49, 50)]


def oryx_image(n=512, fg=QR['burgundy'], bg=QR['grey']):
    """the same oryx for the nacelles (upright, in a unit box)"""
    polys = [([(x / 100, y / 100) for x, y in P], fg) for P in QR_ORYX] + [([(x / 100, y / 100) for x, y in QR_FACE], bg)]
    img = art.poly_image(polys, n)
    return img.crop(img.getbbox())


def qatar(c):
    base(c, QR['grey'])
    fus = c.fuselage()
    # titles (photo A7-AMI, starboard): QATAR burgundy across the windows sn 0.12-0.33, 0.40 H; the Arabic title in dark grey
    # above the windows aft of it, sn 0.38-0.47, 0.17 H (Noto Kufi Arabic, OFL, as a look-alike of the lettering)
    title_span(c, 'QATAR', 'Libre Baskerville', 700, QR['burgundy'], 0.40, 0.12 * c.L, 0.33 * c.L, 0.02, spacing=0.12)
    ar = text_shaped('القطرية', font('Noto Kufi Arabic', 600), 300, QR['arabic'], 'rtl')
    lockup(c, [(ar, 0.17 * c.H, c.winY + 0.21 * c.H, 0.0, 0.0)], 0.38 * c.L)
    fin_all(c, QR['grey'])
    if c.fin is not None:
        fin = c.fin_proper()
        for P in QR_ORYX: c.poly(photo_fin(P, **QR_FIN), QR['burgundy'], 'fin', where=fin)
        c.poly(photo_fin(QR_FACE, **QR_FIN), QR['grey'], 'fin', where=fin)
    c.engines(QR['grey'])
    c.nacelle_decal(oryx_image(), fx=0.75, fy=0.5, height=0.45, sides='out')
    c.tips(QR['burgundy']); c.hstab('#C4C9CA'); c.pylons('#C4C9CA')


LIVERIES['QTR'] = dict(code='QTR', name='Qatar Airways', version='grey fuselage and fin with the burgundy oryx, QATAR and Arabic titles', since=2006,
                       refs=[NOR.format('qatar-airways') + ' (A350 profile; chart #BDC2C2 fuselage, #5C0631 oryx: third party)',
                             photo_ref('QTR', 'grey fin with the burgundy oryx, QATAR across the windows sn 0.12-0.33, Arabic title sn 0.38-0.47 above the windows, oryx on the nacelle')],
                       colors=dict(grey=(QR['grey'], 'third-party chart: unverified'), burgundy=(QR['burgundy'], 'third-party chart: unverified'), arabic=(QR['arabic'], APPROX)), types=['A359'],
                       runtime=dict(top='#C4C9CA', belly='#C4C9CA', tail='#C4C9CA', tail2='#5C0631', eng='#C4C9CA'),
                       status='layout measured on a photo of an A350-900 (starboard); oryx re-drawn as polygons; Arabic title in an OFL look-alike face; its station on the port side assumed the same (inf)', paint=qatar)

# ---- French bee
reg_std('FBU', 'French bee', 'white / blue gradient fuselage, blue tail', 2016, ['https://www.frenchbee.com/ (brand; not fetched)'],
        dict(blue=('#1CA3DC', APPROX)), ['A359'], dict(top='#F7F8F8', belly='#1CA3DC', tail='#1CA3DC', tail2='#FFFFFF', eng='#F2F3F4'), 'from knowledge only: approx',
        dict(title=('french bee', 'Nunito', 900, '#1CA3DC', 0.24, dict(k=0.6, dy=0.1)), tail='#1CA3DC', aft=('#1CA3DC', 2.0, -1.2, -1.2)))

# ---- SAS (2019)
reg_std('SAS', 'SAS', '2019 livery (silver-grey fuselage, dark-blue tail with SAS sweeping down the aft body)', 2019, ['https://www.sasgroup.net/ (brand; not fetched)', photo_ref('SAS', 'silver body, the dark blue of the tail continues down the aft body')],
        dict(blue=('#000C69', APPROX), silver=('#A3B2C2', APPROX)), ['A333', 'A359'],
        dict(top='#DDE3EA', belly='#A3B2C2', tail='#000C69', tail2='#FFFFFF', eng='#A3B2C2'), 'approx',
        dict(body='#CCD2DA', title=('SCANDINAVIAN', 'Montserrat', 600, '#000C69', 0.1, dict(k=0.55, dy=0.22, sp=0.2)), tail='#000C69',
             aft=('#000C69', 0.5, -0.9, -1.2),
             fin_art=(lambda n=1024: text_image('SAS', font('Montserrat', 800), 420, '#C9D2DC'), 0.55, 0.45, 0.2, 'text')))

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
FL = dict(body='#F2F1EC', black='#141414', green='#8DE089')
FL_PHOTOS = photo_ref('FLE', 'layout: cream body, very large black lowercase flair forward, black fin with a large green disc on its lower half')


def flair(c):
    base(c, FL['body'])
    title_span(c, 'flair', 'Nunito', 900, FL['black'], 0.55, 0.12 * c.L, 0.37 * c.L, -0.05, spacing=0.0)
    fin_all(c, FL['black'])
    if c.fin is not None:
        u = c.fu; v = c.fv
        disc = np.hypot((u - 0.62) * 1.0, (v - 0.22) * 1.35) < 0.42
        c.paint(disc & c.fin_proper(), FL['green'])
    c.engines('#E8E8E4'); c.tips(FL['green']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['FLE'] = dict(code='FLE', name='Flair Airlines', version='cream body, black flair title, black tail with the green disc', since=2023,
                       refs=['https://flyflair.com/ (brand; not fetched)', FL_PHOTOS], colors={k: (v, APPROX) for k, v in FL.items()}, types=['B38M'],
                       runtime=dict(top='#F2F1EC', belly='#F2F1EC', tail='#141414', tail2='#8DE089', eng='#E8E8E4'),
                       status='layout from 2023 and 2026 photos of 737 MAX 8s (the 2026 photo adds a black aft body on one aircraft: not drawn); colours approx', paint=flair)

# ---- ITA Airways
reg_std('ITY', 'ITA Airways', '2021 livery (blue Savoia fuselage, white titles, tricolour tail)', 2021, ['https://www.ita-airways.com/ (brand; not fetched)', photo_ref('ITY', 'medium Savoia blue body')],
        dict(blue=('#1766C4', APPROX)), ['A339', 'A359'], dict(top='#1766C4', belly='#1766C4', tail='#1766C4', tail2='#FFFFFF', eng='#1766C4'), 'approx',
        dict(body='#1766C4', title=('ITA', 'Montserrat', 800, '#FFFFFF', 0.3, dict(k=0.5, dy=0.1)), tail='#1766C4',
             fin_polys=[('#009246', [(0.62, -0.3), (0.72, -0.3), (1.02, 1.1), (0.92, 1.1)]), ('#FFFFFF', [(0.72, -0.3), (0.82, -0.3), (1.12, 1.1), (1.02, 1.1)]), ('#CE2B37', [(0.82, -0.3), (0.92, -0.3), (1.22, 1.1), (1.12, 1.1)])], eng='#1766C4'))

# ---- China Southern
CZ = dict(blue='#0079C2', red='#E1261C', title='#2F8FCB')


def cz_titles(c):
    """Chinese title forward (sn 0.15-0.26), CHINA SOUTHERN aft of it (sn 0.29-0.42), both above the windows (photos
    B-2728-class 787s, refs/cache/livref CSN_1 / CSN_2, starboard side: the characters run from the nose aft, i.e. they read
    right to left on the starboard side; on the port side they read left to right from the nose (inf: no port photo)).
    Chinese face: Noto Sans SC (OFL) as a look-alike."""
    zh = '中国南方航空'; fp = font('Noto Sans SC', 700)
    h = 0.15 * c.H; yc = c.winY + 0.22 * c.H
    def put(txt, where):
        img = text_shaped(txt, fp, 300, CZ['title'])
        w = 0.11 * c.L; img = img.resize((max(1, int(img.size[1] * w / h)), img.size[1]))
        c.decal(img, 0.15 * c.L, yc, h, mode='text', where=c.fuselage() & where)
    c.per_side(lambda w: put(zh, w), lambda w: put(zh[::-1], w))
    title_span(c, 'CHINA SOUTHERN', 'Libre Baskerville', 700, CZ['title'], 0.12, 0.29 * c.L, 0.42 * c.L, 0.22, spacing=0.03)


reg_std('CSN', 'China Southern', 'blue tail with the red kapok flower', 1991, ['https://www.csair.com/ (brand; not fetched)', photo_ref('CSN', 'Chinese title forward of CHINA SOUTHERN, both above the windows')],
        dict(blue=(CZ['blue'], APPROX), red=(CZ['red'], APPROX), title=(CZ['title'], 'measured on the photo (approx)')), ['B789'],
        dict(top='#F7F8F8', belly='#F7F8F8', tail='#0079C2', tail2='#E1261C', eng='#F2F3F4'), 'titles measured on photos (starboard); kapok flower simplified; colours approx',
        dict(extra=cz_titles, tail='#0079C2',
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

# ---- Fiji Airways (2013 masi livery)
FJ = dict(black='#1C1A1A', brown='#6E3222', white='#F7F8F8', ivory='#EFE9DE')
FJ_FIN = dict(le=((27, 95), (72, 3)), te=((72, 95), (97, 3)), root=95, tip=3)


def masi_medallion(n=1024, brown=FJ['brown'], ink=FJ['black'], light=FJ['ivory']):
    """the masi medallion of the Fiji Airways tail (photo DQ-FAI, refs/cache/livref FJI_1): a light ring patterned with
    black triangles and bars around a brown centre, a small light sunburst in the middle (re-drawn, simplified)"""
    parts = [f'<circle cx="50" cy="50" r="48" fill="{light}"/>', f'<circle cx="50" cy="50" r="31" fill="{brown}"/>']
    for k in range(16):
        a0 = 2 * np.pi * k / 16; a1 = 2 * np.pi * (k + 1) / 16; am = (a0 + a1) / 2
        if k % 2 == 0:   # triangle pointing inward
            P = [(50 + 46 * np.cos(a0), 50 + 46 * np.sin(a0)), (50 + 46 * np.cos(a1), 50 + 46 * np.sin(a1)), (50 + 34 * np.cos(am), 50 + 34 * np.sin(am))]
            parts.append('<path d="M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in P) + f' Z" fill="{ink}"/>')
        else:            # three bars
            for d in (-0.09, 0, 0.09):
                a = am + d
                parts.append(f'<line x1="{50 + 34 * np.cos(a):.1f}" y1="{50 + 34 * np.sin(a):.1f}" x2="{50 + 45 * np.cos(a):.1f}" y2="{50 + 45 * np.sin(a):.1f}" stroke="{ink}" stroke-width="2.2"/>')
    for k in range(12):
        a = 2 * np.pi * k / 12
        parts.append(f'<line x1="{50 + 6 * np.cos(a):.1f}" y1="{50 + 6 * np.sin(a):.1f}" x2="{50 + 15 * np.cos(a):.1f}" y2="{50 + 15 * np.sin(a):.1f}" stroke="{light}" stroke-width="2.6" stroke-linecap="round"/>')
    parts.append(f'<circle cx="50" cy="50" r="4" fill="{light}"/>')
    return art.svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">' + ''.join(parts) + '</svg>', n)


def masi_band(c, where, v0, v1, space='fin'):
    """a black masi band with light bars and triangles between fin heights v0..v1 (fin coords)"""
    c.poly([(-0.6, v0), (1.3, v0), (1.3, v1), (-0.6, v1)], FJ['black'], space, where=where)
    h = v1 - v0
    for k in range(14):
        u = -0.5 + 0.12 * k
        if k % 3 == 0:
            c.poly([(u, v0 + 0.15 * h), (u + 0.08, v0 + 0.15 * h), (u + 0.04, v1 - 0.2 * h)], FJ['ivory'], space, where=where)
        else:
            c.poly([(u, v0 + 0.1 * h), (u + 0.015, v0 + 0.1 * h), (u + 0.015, v1 - 0.1 * h), (u, v1 - 0.1 * h)], FJ['ivory'], space, where=where)


def fiji(c):
    base(c, FJ['white'])
    fus = c.fuselage()
    # FIJI: tall outline letters across the window row just aft of door 1 (photo: sn 0.16-0.285, 0.6 of the fuselage
    # height, centred on the windows); AIRWAYS below it, 0.13 H, spanning the middle of FIJI
    s0 = max(0.16 * c.L, c.doors[0] + 0.9)
    img = outline_title('FIJI', 'Montserrat', 700, FJ['black'], ring=0.68, stretch=0.62, spacing=0.12)
    h = 0.60 * c.H; w = min(0.125 * c.L, h * img.size[0] / img.size[1])
    img = img.resize((max(1, int(img.size[1] * w / h)), img.size[1]))
    lockup(c, [(img, h, c.winY, 0.0, 0.0)], s0)
    aw = text_image('AIRWAYS', font('Montserrat', 600), 420, FJ['black'], spacing=0.12)
    ha = 0.12 * c.H; wa = min(0.75 * w, ha * aw.size[0] / aw.size[1]); aw = aw.resize((max(1, int(aw.size[1] * wa / ha)), aw.size[1]))
    lockup(c, [(aw, ha, c.winY - h / 2 - 0.02 * c.H - ha / 2, 0.0, 0.0)], s0 + 0.18 * w)
    fin_all(c, FJ['brown'])
    if c.fin is not None:
        fin = c.finzone()
        masi_band(c, fin, 0.74, 1.3)                                     # tip band
        c.poly([(-0.6, -0.3), (0.12, -0.3), (0.0, 0.40), (-0.6, 0.40)], FJ['black'], 'fin', where=fin)   # forward root band
        for k in range(5):
            v = 0.02 + 0.075 * k
            c.poly([(-0.6, v), (0.1 - 0.0 * k, v), (0.1, v + 0.018), (-0.6, v + 0.018)], FJ['ivory'], 'fin', where=fin)
        c.fin_decal(masi_medallion(), 0.60, 0.37, 0.46, where=c.fin_proper())
    c.engines('#F2F3F4'); c.tips(FJ['black']); c.hstab('#DADCDE'); c.pylons('#E4E6E8')


LIVERIES['FJI'] = dict(code='FJI', name='Fiji Airways', version='2013 livery (large FIJI title, masi-pattern tail with the medallion)', since=2013,
                       refs=['https://www.fijiairways.com/ (brand; not fetched)', photo_ref('FJI', 'FIJI outline title 0.6 H across the windows from door 1, AIRWAYS below; brown fin with the masi medallion, black masi bands at the tip and the forward root')],
                       colors={k: (v, APPROX) for k, v in FJ.items()}, types=['A332', 'A333', 'A359'],
                       runtime=dict(top='#F7F8F8', belly='#F7F8F8', tail='#6E3222', tail2='#1C1A1A', eng='#F2F3F4'),
                       status='layout measured on a photo of an A350-900 (starboard); masi patterns simplified; colours approx', paint=fiji)

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
FX = dict(purple='#4D148C', orange='#FF6600', white='#F2F3F5', grey='#6D6E71')
FX_PHOTOS = photo_ref('FDX', 'layout measured on the port side of the MD-11F N591FE: white body, purple aft body behind a slash from the keel at sn 0.71 to the crown at sn 0.80, FedEx title sn 0.17-0.34, 0.5 H tall, Express below')


def fedex_word(px=420, fed=FX['purple'], ex=FX['orange']):
    """the FedEx wordmark as two colour runs (Fed + Ex) on one baseline (Montserrat 800: look-alike of the real face)"""
    from PIL import Image
    a = text_image('Fed', font('Montserrat', 800), px, fed, spacing=-0.02); b = text_image('Ex', font('Montserrat', 800), px, ex, spacing=-0.02)
    h = max(a.size[1], b.size[1]); out = Image.new('RGBA', (a.size[0] + b.size[0] - 6, h), (0, 0, 0, 0))
    out.alpha_composite(a, (0, h - a.size[1])); out.alpha_composite(b, (a.size[0] - 6, h - b.size[1]))
    return out


def fedex(c):
    base(c, FX['white'])
    fus = c.fuselage()
    fw = fedex_word(); h = 0.5 * c.H; w = h * fw.size[0] / fw.size[1]
    ex = text_image('Express', font('Montserrat', 500), 420, FX['grey'])
    he = 0.17 * c.H; we = he * ex.size[0] / ex.size[1]
    lockup(c, [(fw, h, c.ycM + 0.2 * c.hhM, 0.0, 0.0), (ex, he, c.ycM - 0.55 * c.hhM, w - we, 0.0)], 0.17 * c.L)
    c.poly([(0.71, -1.6), (0.80, 1.6), (1.3, 1.6), (1.3, -1.6)], FX['purple'], 'cabin', where=fus)
    fin_all(c, FX['purple'])
    if c.fin is not None:
        c.fin_decal(fedex_word(px=420, fed='#FFFFFF'), 0.5, 0.2, 0.18, mode='text', where=c.fin_proper())
    c.engines(FX['white']); c.tips(FX['purple']); c.hstab(FX['purple']); c.pylons('#E4E6E8')


LIVERIES['FDX'] = dict(code='FDX', name='FedEx', version='FedEx Express livery (white body, purple tail and aft body, FedEx title with Express)', since=1994,
                       refs=['https://newsroom.fedex.com/ (brand; not fetched)', FX_PHOTOS], colors={k: (v, APPROX) for k, v in FX.items()}, types=['B763', 'MD11', 'B752'],
                       runtime=dict(top='#F2F3F5', belly='#F2F3F5', tail='#4D148C', tail2='#FF6600', eng='#F2F3F5'),
                       status='layout measured on a photo of the MD-11F (port side); the earlier design showed the purple crown of the 1994 scheme, which the photo does not', paint=fedex)
UP = dict(brown='#351C15', gold='#FFB500', white='#F4F4F2', grey='#D9DADB')
UP_PHOTOS = photo_ref('UPS', 'layout measured on the port side of the 747-8F N627UP: white forward and lower body, brown aft body behind a gold '
                      'sweep from the crown at sn 0.48 down to the keel at sn 0.78, Worldwide Services title sn 0.11-0.30 above the windows, '
                      'shield with gold border and gold ups on the brown fin')


def ups_shield(n=1024, brown=UP['brown'], gold=UP['gold']):
    """the UPS shield as painted on the fin (photo N627UP): brown shield face with a gold border, the gold bow across its
    top, gold lowercase ups (re-drawn; Montserrat as a look-alike of the lettering)"""
    from PIL import Image
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 116">
<path d="M6 10 C30 2 70 2 94 10 L94 64 C94 88 72 104 50 113 C28 104 6 88 6 64 Z" fill="{gold}"/>
<path d="M12 22 C36 12 64 12 88 18 L88 63 C88 84 70 97 50 105 C30 97 12 84 12 63 Z" fill="{brown}"/>
<path d="M12 22 C36 12 64 12 88 18 L88 24 C64 18 36 18 12 30 Z" fill="{gold}"/></svg>"""
    img = art.svg(svg, n)
    t = text_image('ups', font('Montserrat', 800), 420, gold, spacing=-0.02)
    w = int(0.62 * img.size[0]); h = int(w * t.size[1] / t.size[0])
    img.alpha_composite(t.resize((w, h), Image.LANCZOS), (int(0.5 * img.size[0] - w / 2), int(0.52 * img.size[1] - h / 2)))
    return img


def ups(c):
    base(c, UP['white'])
    fus = c.fuselage()
    # the gold sweep: centre line from the crown at sn 0.48 curving down to the keel at sn 0.78; brown above / behind it
    sweep = [(0.46, 1.6), (0.48, 1.0), (0.58, 0.45), (0.68, -0.25), (0.78, -1.0), (0.80, -1.6)]
    P = np.array(sweep)
    from scipy.interpolate import PchipInterpolator
    f = PchipInterpolator(P[::-1, 1], P[::-1, 0])          # station of the sweep at a cabin eta
    eta = (c.y - c.ycM) / c.hhM
    s_b = f(np.clip(eta, -1.6, 1.6)) * c.L
    # band about 0.11 H wide across its direction; the sweep falls ~3 stations per unit of height, so ~0.35 H along the body
    w = 0.35 * c.H
    c.paint(c.aa(s_b + w / 2 - c.s) * fus, UP['brown'])                            # brown aft of the band
    c.paint(np.clip(c.aa(np.abs(c.s - s_b) - w / 2), 0, 1) * fus, UP['gold'])
    title_span(c, 'Worldwide Services', 'Montserrat', 600, UP['brown'], 0.16, 0.11 * c.L, 0.30 * c.L, 0.22, spacing=0.0, italic=True)
    fin_all(c, UP['brown'])
    if c.fin is not None:
        c.fin_decal(ups_shield(), 0.55, 0.60, 0.46, mode='text', where=c.fin_proper())
    c.engines(UP['grey']); c.tips(UP['brown']); c.hstab(UP['brown']); c.pylons(UP['grey'])


LIVERIES['UPS'] = dict(code='UPS', name='UPS', version='2003 livery (white forward body, brown aft body behind a gold sweep, brown tail with the gold shield)', since=2003,
                       refs=[NOR.format('ups'), UP_PHOTOS], colors={k: (v, APPROX) for k, v in UP.items()}, types=['B763', 'B752', 'B748', 'B744', 'MD11'],
                       runtime=dict(top='#F4F4F2', belly='#F4F4F2', tail='#351C15', tail2='#FFB500', eng='#D9DADB'),
                       status='layout measured on a photo of a 747-8F (port side); shield re-drawn: the photo shows the shield face brown with a gold '
                              'border and gold letters (not a gold-filled shield); colours approx', paint=ups)
# all-cargo operators: their SFO fleet (757-200 freighters, 767-300F, MD-11F, 747-400F / -8F) has no passenger cabin
# windows; the painter paints none and the renderer hides the models' cabin glass (manifest brands.<code>.cargo). The
# few crew-area windows of the freighters (747F upper deck) are not modelled.
for _c in ('FDX', 'UPS'): LIVERIES[_c]['cargo'] = True


# ================================================================================================ 777 family
# The 777s now have artist models (FlightGear 777-200ER / -300ER, tools/convert_models.py): the brands whose SFO fleet
# includes them (docs/research/liveries.md §1: DataSF landings by airline and model, "B773" = 777-300 / -300ER = ADS-B
# B77W; the recorder's airframes) get bakes on them. Designs are the brands' own (layout in fractions of the length and
# cabin height, so they carry over; checked on the renders, not on 777 photos unless stated).
FLEET_777 = {'UAL': ['B772', 'B77W'], 'EVA': ['B77W'], 'CPA': ['B77W'], 'JAL': ['B77W'], 'ANA': ['B77W'], 'BAW': ['B77W'],
             'AIC': ['B77W', 'B772'], 'AFR': ['B77W'], 'KAL': ['B77W'], 'ACA': ['B77W', 'B77L'], 'SWR': ['B77W'], 'CES': ['B77W'],
             'CCA': ['B77W'], 'PAL': ['B77W']}
for _c, _t in FLEET_777.items():
    LIVERIES[_c]['types'] = list(LIVERIES[_c].get('types', [])) + [t for t in _t if t not in LIVERIES[_c].get('types', [])]


# ================================================================================================ registrations
# Where each airline paints the registration (painted per aircraft at run time from its own tail number,
# js/live/aircraft.js + js/shaders/aircraft_real.js): sn = forward end of the registration + flag block as a fraction of
# the fuselage length from the nose (port side), dy = centre height above the window centre line in fuselage heights H
# (negative: below the windows), h = letter height / H, flag = national flag painted with it ('US', 'MX'), flag_first =
# the flag ahead of the letters on the port side. Measured on the reference photographs (refs/cache/livref, Wikimedia
# Commons, reference only; stations measured along the fuselage in the side views): src 'photo <file>'. Brands without a
# measurement use REG_DEFAULT (src 'inf': aft fuselage above the windows, where most of the photographed airlines paint it).
REG_DEFAULT = dict(sn=0.74, dy=0.18, h=0.10, flag=None, flag_first=False, src='inf (default: aft fuselage above the windows)')
REG = {
    'UAL': dict(sn=0.73, dy=0.20, h=0.12, flag='US', src='photo UAL_2 (737-8 N37440, starboard): N-number then the US flag aft of it, above the windows'),
    'UAL-X': dict(sn=0.65, dy=0.13, h=0.11, flag='US', src='photo UAL-X_2 (E175 N86371, port): above the windows aft of the wing, flag aft'),
    'UAL-G': dict(sn=0.73, dy=0.20, h=0.12, flag='US', src='as UAL (inf)'),
    'AAL': dict(sn=0.745, dy=-0.17, h=0.10, flag='US', flag_first=True, src='photo AAL_2 (A321 N913US, port): below the windows aft, flag ahead of it'),
    'AAL-E': dict(sn=0.745, dy=-0.17, h=0.10, flag='US', flag_first=True, src='as AAL (inf)'),
    'DAL': dict(sn=0.72, dy=0.20, h=0.10, flag='US', flag_first=True, src='photo DAL_1 (737-900 N884DN, port): flag then N-number above the windows aft'),
    'DAL-C': dict(sn=0.72, dy=0.20, h=0.10, flag='US', flag_first=True, src='as DAL (inf)'),
    'SWA': dict(sn=0.63, dy=0.20, h=0.10, src='photo SWA_1 (737-700 N273WN, port): above the windows at the start of the tail stripes'),
    'VOI': dict(sn=0.71, dy=-0.17, h=0.10, flag='MX', flag_first=True, src='photo VOI_1 (A320neo N531VL, port): Mexican flag then the registration below the windows'),
    'JAL': dict(sn=0.81, dy=0.15, h=0.10, src='photo JAL_1 (787-9 JA864J, port): above the windows ahead of the aft door'),
    'QTR': dict(sn=0.76, dy=-0.15, h=0.09, src='photo QTR_1 (A350-900 A7-AMI, starboard): below the windows aft'),
    'VIR': dict(sn=0.76, dy=-0.40, h=0.10, src='photo VIR_1 (787-9 G-VOWS, port): low on the aft fuselage'),
    'AFR': dict(sn=0.77, dy=0.08, h=0.07, src='photo AFR_2 (A350-900 F-HUVE, port): small, at the window line aft'),
    'UPS': dict(sn=0.72, dy=0.10, h=0.08, src='photo UPS_2 (747-8F N627UP, port): on the brown aft body'),
}
for _c, _L in LIVERIES.items():
    _L['reg'] = {**REG_DEFAULT, **REG.get(_c, {})}
