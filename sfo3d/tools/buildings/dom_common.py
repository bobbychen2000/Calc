"""Shared helpers for the domestic-terminal research tools (tools/buildings/dom_*.py).

* NAIP epoch rasters on the world grid (made by dom_naip_epochs.py; refs/cache/buildings/domestic/naip/, local only)
* SFO Museum footprints (data/sfo_airport.json, CDLA-Permissive-1.0) - read only
* FAA Digital Obstacle File records (refs/cache/lighting/DAILY_DOF_CSV.ZIP, DOF.CSV dated 2026-09-18)
* QA crops with a labelled world grid (x east, z south, metres from the ARP; frame ltp-nad83-2011, tools/geo_frame.py)
"""
import csv, io, json, os, sys, zipfile
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

NAIP_DIR = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'domestic', 'naip')
QA_DIR = os.path.join(ROOT, 'out', 'buildings', 'domestic')
DOF_ZIP = os.path.join(ROOT, 'refs', 'cache', 'lighting', 'DAILY_DOF_CSV.ZIP')
FT = 0.3048
_cache = {}


def epoch(year):
    """(image BGR uint8, meta) of the NAIP epoch raster; meta has x0, z0, res."""
    if year not in _cache:
        meta = json.load(open(os.path.join(NAIP_DIR, 'naip_epochs.json')))[str(year)]
        img = cv2.imread(os.path.join(NAIP_DIR, f'naip_{year}_dom.png'), cv2.IMREAD_COLOR)
        w = meta['window']
        _cache[year] = (img, dict(x0=w['x0'], z0=w['z0'], x1=w['x1'], z1=w['z1'], res=meta['res_m']))
    return _cache[year]


def w2p(meta, x, z):
    """world -> fractional pixel (col, row) with pixel centres at integer + 0.5 convention removed."""
    return (np.asarray(x) - meta['x0']) / meta['res'] - 0.5, (np.asarray(z) - meta['z0']) / meta['res'] - 0.5


def crop(year, x0, x1, z0, z1, res=None):
    """world-box crop (BGR) of an epoch, optionally resampled to `res` m/px; returns (img, (x0, z0, res))."""
    img, m = epoch(year)
    res = res or m['res']
    xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
    X, Z = np.meshgrid(xs, zs)
    c, r = w2p(m, X, Z)
    out = cv2.remap(img, c.astype(np.float32), r.astype(np.float32), cv2.INTER_LINEAR)
    return out, (x0, z0, res)


def gray(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)


def airport():
    return json.load(open(os.path.join(ROOT, 'data', 'sfo_airport.json')))


def footprints():
    """name -> list of outer rings ([x, z] lists) of the domestic buildings in the SFO Museum geometry."""
    D = airport(); out = {}
    for t in D['terminals']:
        if t['name'] != 'International Terminal': out[t['name']] = [p[0] for p in t['polys']]
    for b in D['boardingAreas']:
        if b['letter'] in 'BCDEF': out[b['name']] = [p[0] for p in b['polys']]
    return out


def load_dof(pred=None):
    """FAA DOF rows as dicts with world x, z (DOF horizontal datum WGS 84 -> world via GF.wgs84_to_world)."""
    rows = []
    with zipfile.ZipFile(DOF_ZIP) as zf:
        name = [n for n in zf.namelist() if n.upper().endswith('.CSV')][0]
        with zf.open(name) as f:
            for d in csv.DictReader(io.TextIOWrapper(f, encoding='latin-1')):
                lat, lon = float(d['LATDEC']), float(d['LONDEC'])
                if abs(lat - 37.615) > 0.02 or abs(lon + 122.385) > 0.03: continue
                x, z = GF.wgs84_to_world(lat, lon)
                r = dict(oas=d['OAS'], type=d['TYPE'].strip(), agl_ft=int(d['AGL']), amsl_ft=int(d['AMSL']),
                         acc=d['ACCURACY'].strip(), lighting=d['LIGHTING'].strip(), jdate=d['JDATE'].strip(),
                         study=d['FAA STUDY'].strip(), verified=d['VERIFIED STATUS'].strip(),
                         dmslat=d['DMSLAT'], dmslon=d['DMSLON'], lat=lat, lon=lon, x=round(x, 2), z=round(z, 2))
                if pred is None or pred(r): rows.append(r)
    return rows


def grid_overlay(img, origin, step=10, label=50, rings=(), pts=(), color=(0, 0, 255)):
    """draw a labelled world grid (x, z) + optional rings / points on a crop made by crop()."""
    x0, z0, res = origin
    im = img.copy(); H, W = im.shape[:2]
    P = lambda x, z: (int(round((x - x0) / res)), int(round((z - z0) / res)))
    gx0 = np.ceil(x0 / step) * step; gz0 = np.ceil(z0 / step) * step
    for g in np.arange(gx0, x0 + W * res, step):
        p = P(g, z0)[0]; major = abs(g / label - round(g / label)) < 1e-6
        cv2.line(im, (p, 0), (p, H), (0, 220, 255) if major else (140, 140, 140), 1)
        if major: cv2.putText(im, f'{g:.0f}', (p + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 160, 255), 1)
    for g in np.arange(gz0, z0 + H * res, step):
        p = P(x0, g)[1]; major = abs(g / label - round(g / label)) < 1e-6
        cv2.line(im, (0, p), (W, p), (0, 220, 255) if major else (140, 140, 140), 1)
        if major: cv2.putText(im, f'{g:.0f}', (2, p - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 160, 255), 1)
    for ring in rings:
        cv2.polylines(im, [np.array([P(*q) for q in ring], np.int32)], True, color, 1)
    for (x, z, txt) in pts:
        q = P(x, z); cv2.circle(im, q, 4, (255, 0, 255), 1)
        if txt: cv2.putText(im, txt, (q[0] + 5, q[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
    return im


def save_qa(name, img, quality=88):
    os.makedirs(QA_DIR, exist_ok=True)
    p = os.path.join(QA_DIR, name)
    cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, quality] if p.endswith('.jpg') else [])
    return p


# ---------------------------------------------------------------------------------------- airport-grid (s, t) crops
def crop_st(year, s0, s1, t0, t1, res=0.25):
    """crop in airport-grid coordinates (GF.world_to_st): columns = +s (ESE, 117.83 deg), rows = -t (row 0 = t1, i.e.
    NNE up). Returns (img, (s0, t1, res)); pixel (col, row) centre = (s0 + (col + .5) res, t1 - (row + .5) res)."""
    img, m = epoch(year)
    ss = np.arange(s0, s1, res) + res / 2; ts = t1 - (np.arange(0, t1 - t0, res) + res / 2)
    S, T = np.meshgrid(ss, ts)
    X = S * GF.V[0] + T * GF.U[0]; Z = -(S * GF.V[1] + T * GF.U[1])
    c, r = w2p(m, X, Z)
    return cv2.remap(img, c.astype(np.float32), r.astype(np.float32), cv2.INTER_LINEAR), (s0, t1, res)


def grid_overlay_st(img, origin, step=5, label=20, rings=(), color=(0, 0, 255)):
    """labelled (s, t) grid on a crop_st image; rings are world [x, z] lists."""
    s0, t1, res = origin
    im = img.copy(); H, W = im.shape[:2]
    P = lambda s, t: (int(round((s - s0) / res)), int(round((t1 - t) / res)))
    for g in np.arange(np.ceil(s0 / step) * step, s0 + W * res, step):
        p = P(g, t1)[0]; major = abs(g / label - round(g / label)) < 1e-6
        cv2.line(im, (p, 0), (p, H), (0, 220, 255) if major else (140, 140, 140), 1)
        if major: cv2.putText(im, f's{g:.0f}', (p + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 160, 255), 1)
    for g in np.arange(np.floor(t1 / step) * step, t1 - H * res, -step):
        p = P(s0, g)[1]; major = abs(g / label - round(g / label)) < 1e-6
        cv2.line(im, (0, p), (W, p), (0, 220, 255) if major else (140, 140, 140), 1)
        if major: cv2.putText(im, f't{g:.0f}', (2, p - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 160, 255), 1)
    for ring in rings:
        pts = [GF.world_to_st(x, z) for x, z in ring]
        cv2.polylines(im, [np.array([P(s, t) for s, t in pts], np.int32)], True, color, 1)
    return im
