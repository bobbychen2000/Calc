#!/usr/bin/env python3
"""Cabin-window rows of the real aircraft, measured on the manufacturers' own drawings.

Why: the livery painter paints cabin windows on the models whose artist source has none (or only painted ones), and fills
the windows of the fuselage plugs of stretched types (737-900 on the 737-800 model, 787-9/-10 on the 787-8, ...). Those
windows must sit where the real ones are: count, pitch, first / last window station and height on the fuselage. None of
the manufacturers publishes a window table in the airport-planning documents, but their drawings show the windows:

  Boeing   CAD 3-view drawings for airport planning ("accurate to within 6 inches"; MD-11: "~ +/-3 inches"),
           https://www.boeing.com/commercial/airports/3-view (DXF, or DWG converted with LibreDWG dwg2dxf 0.13.3).
           The side view draws every cabin window (10 x 14 in on the 737/757/767, 20 in pitch; 22 in on the 767 ...).
  Airbus   Aircraft Characteristics - Airport and Maintenance Planning (AC), 2-2-0 General Aircraft Dimensions side views
           (vector PDF, refs/cache/acap/).
  Embraer  Airport Planning Manuals (APM) 2.2 general dimensions side views (vector PDF).
  Bombardier / Airbus Canada  CRJ APM, A220 APP side views (vector PDF).

Method: every drawing is flattened to 2-D polylines; strokes that touch (shared end points) are merged into components;
components of window size (and proportions) that repeat along one horizontal line at a regular pitch are a window row.
The row is placed on the side view it belongs to: nose tip = the forward-most point of the outline at the row's height
band; crown and keel of the fuselage are the outline crossings above / below the row at each window station. Scale:
the document's units (Boeing CAD: inches, MD-11: feet), checked against the published fuselage length; PDFs (points):
from the side view's overall length and the published overall length (js/aircraft/types.js SPEC L).

Output: tools/liveries/windows_ref.json  {type: {src, n, s[] (window centres, m aft of the nose tip), pitch, w, h,
yf (window centre height as a fraction of the local fuselage height, 0 keel .. 1 crown), yfs[] per window, rows (upper
deck rows for 747 / A380), check}}. Reference drawings are not committed (refs/cache/, gitignored).

Usage: python3 tools/liveries/windows_ref.py [TYPE ...] [--plot DIR]
"""
import argparse, collections, json, math, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
CACHE = os.path.join(ROOT, 'refs', 'cache')
OUT = os.path.join(HERE, 'windows_ref.json')     # committed: the measured rows (numbers only; the drawings stay in refs/cache)
IN, FT = 0.0254, 0.3048

# type -> document. dxf: Boeing CAD 3-view (unit: metres per drawing unit); pdf: file + 1-based page. `note`: what the
# drawing is (figure / title) for the citation.
B3V = 'refs/cache/boeing3v/'
AC = 'refs/cache/acap/'
DOCS = {
    'b736': dict(dxf=B3V + '7376/737-600.dxf', unit=IN, note='Boeing CAD 3-view 737-600 (7376.zip)'),
    'b737': dict(dxf=B3V + '7377/737-700.dxf', unit=IN, note='Boeing CAD 3-view 737-700 (7377.zip)'),
    'b738': dict(dxf=B3V + '7378/737-800.dxf', unit=IN, note='Boeing CAD 3-view 737-800 (7378.zip)'),
    'b739': dict(dxf=B3V + '7379/737-900.dxf', unit=IN, note='Boeing CAD 3-view 737-900 (7379.zip, DWG -> DXF)'),
    'b37m': dict(dxf=B3V + '737_max7/737-7_3VIEW.dxf', unit=IN, note='Boeing CAD 3-view 737-7 (737_max7.zip, DWG -> DXF)'),
    'b38m': dict(dxf=B3V + '737_max8/737-8_3VIEW.dxf', unit=IN, note='Boeing CAD 3-view 737-8 (737_max8.zip, DWG -> DXF)'),
    'b39m': dict(dxf=B3V + '737_max9/737-9_3VIEW.dxf', unit=IN, note='Boeing CAD 3-view 737-9 (737_max9.zip, DWG -> DXF)'),
    'b3xm': dict(dxf=B3V + '737_max10/737-10_3VIEW.dxf', unit=IN, note='Boeing CAD 3-view 737-10 (737_max10.zip, DWG -> DXF)'),
    'b744': dict(dxf=B3V + '7474/747-400.dxf', unit=IN, note='Boeing CAD 3-view 747-400 (7474.zip)',
                 fill=[dict(deck=0, a=38.09, b=43.69, why='main-deck windows hidden by the wing in the side view')]),
    # 747-8: dwg2dxf writes an incomplete DXF (no model space); the entities are recovered from LibreDWG's JSON dump
    # (tools/liveries/dwg_json2dxf.py). The drawing is at a print scale: unit = 76.25 m / side-view length 4.2393 units
    # (nose 0.2584 .. tail 4.4977), refined by the door outlines against the ACAP door centres (D6-58326-3 §2.7.1 p.2-14)
    'b748': dict(dxf=B3V + '7478p/7478p3vue_recovered.dxf', unit=76.25 / 4.2393, pxm=80, cal=[9.5, 22.9, 34.7, 46.3, 60.8],
                 note='Boeing CAD 3-view 747-8 (7478p.zip, DWG -> JSON -> DXF)'),
    'b752': dict(dxf=B3V + '7572/757-200.dxf', unit=IN, note='Boeing CAD 3-view 757-200 (7572.zip)'),
    'b753': dict(dxf=B3V + '7573/757-300.dxf', unit=IN, note='Boeing CAD 3-view 757-300 (7573.zip)'),
    'b762': dict(dxf=B3V + '7672/767-200.dxf', unit=IN, note='Boeing CAD 3-view 767-200 (7672.zip)'),
    'b763': dict(dxf=B3V + '7673/767-300.dxf', unit=IN, note='Boeing CAD 3-view 767-300 (7673.zip)',
                 fill=[dict(deck=0, a=31.97, b=34.76, why='windows hidden by the wing in the side view')]),
    'b764': dict(dxf=B3V + '7674/767-400.dxf', unit=IN, note='Boeing CAD 3-view 767-400 (7674.zip)'),
    'b772': dict(dxf=B3V + '7772/777-200.dxf', unit=IN, note='Boeing CAD 3-view 777-200 (7772.zip)'),
    'b77l': dict(dxf=B3V + '7772/777-200.dxf', unit=IN, note='Boeing CAD 3-view 777-200 (7772.zip; -200LR same fuselage)'),
    'b773': dict(dxf=B3V + '7773/777-3-3v.dxf', unit=IN, note='Boeing CAD 3-view 777-300 (7773.zip)'),
    'b77w': dict(dxf=B3V + '7773/777-3-3v.dxf', unit=IN, note='Boeing CAD 3-view 777-300 (7773.zip; -300ER same fuselage)'),
    'b779': dict(dxf=B3V + '7779/7779.dxf', unit=IN, note='Boeing CAD 3-view 777-9 (7779.zip, DWG -> DXF)'),
    'b788': dict(dxf=B3V + '7878/7878.dxf', unit=IN, note='Boeing CAD 3-view 787-8 (7878.zip, DWG -> DXF)'),
    'b789': dict(dxf=B3V + '7879/7879.dxf', unit=IN, note='Boeing CAD 3-view 787-9 (7879.zip, DWG -> DXF)'),
    'b78x': dict(dxf=B3V + '78710/787-10.dxf', unit=IN, note='Boeing CAD 3-view 787-10 (78710.zip, DWG -> DXF)'),
    'md11': dict(dxf=B3V + 'md11/md11a-3v.dxf', unit=FT, note='Boeing CAD 3-view MD-11 (md11.zip)'),
    # Airbus AC 2-2-0 General Aircraft Dimensions (side view on sheet 1); page numbers of the PDF files in refs/cache/acap
    'a319': dict(pdf=AC + 'airbus_AC_A319_20250715.pdf', page=42, clip=(130, 150, 470, 285), dpi=2400, cal=[5.04, 25.81], note='Airbus AC A319 (15 Jul 2025) FIGURE-2-2-0-991-002-A01 sheet 1'),
    'a19n': dict(pdf=AC + 'airbus_AC_A319_20250715.pdf', page=46, clip=(130, 150, 470, 285), dpi=2400, cal=[5.04, 25.81], note='Airbus AC A319 (15 Jul 2025) FIGURE-2-2-0-991-008-A01 sheet 1 (A319neo)'),
    'a320': dict(pdf=AC + 'airbus_AC_A320_0624.pdf', page=40, cal=[5.04, 29.53], note='Airbus AC A320 (1 Jun 2024) FIGURE-2-2-0-991-004-A01 sheet 1'),
    'a20n': dict(pdf=AC + 'airbus_AC_A320_0624.pdf', page=44, cal=[5.04, 29.53], note='Airbus AC A320 (1 Jun 2024) FIGURE-2-2-0-991-009-A01 sheet 1 (A320neo)'),
    'a321': dict(pdf=AC + 'airbus_AC_A321_20250715.pdf', page=64, clip=(110, 150, 490, 285), dpi=2400, cal=[5.02, 13.84, 24.79, 36.58], note='Airbus AC A321 (15 Jul 2025) FIGURE-2-2-0-991-005-A01 sheet 1'),
    'a21n': dict(pdf=AC + 'airbus_AC_A321_20250715.pdf', page=68, clip=(110, 150, 490, 285), dpi=2400, cal=[5.02, 13.84, 24.79, 36.58], note='Airbus AC A321 (15 Jul 2025) FIGURE-2-2-0-991-010-A01 sheet 1 (A321neo)'),
    'a333': dict(pdf=AC + 'airbus_AC_A330_20251201.pdf', page=119, clip=(120, 150, 480, 270), cal=[5.85, 17.74, 35.96, 50.96], note='Airbus AC A330 (1 Dec 2025) FIGURE-2-7-0-991-006-B01 Door Location sheet 2 (A330-300/-900)'),
    'a332': dict(pdf=AC + 'airbus_AC_A330_20251201.pdf', page=117, clip=(120, 150, 480, 270), cal=[5.85, 14.56, 32.77, 45.63], note='Airbus AC A330 (1 Dec 2025) FIGURE-2-7-0-991-006-A01 Door Location sheet 2 (A330-200/-800)'),
    'a339': dict(pdf=AC + 'airbus_AC_A330_20251201.pdf', page=65, note='Airbus AC A330 (1 Dec 2025) FIGURE-2-2-0-991-011-A01 sheet 1 (A330-900)'),
    'a338': dict(pdf=AC + 'airbus_AC_A330_20251201.pdf', page=67, note='Airbus AC A330 (1 Dec 2025) FIGURE-2-2-0-991-012-A01 sheet 1 (A330-800)'),
    'a388': dict(pdf=AC + 'airbus_AC_A380_20251201.pdf', page=56, clip=(100, 225, 525, 390), override=dict(eta=0.565, yf=0.782, rows_eta=[-0.082], fus_h=8.56, note='heights read at the 4th upper-deck window (s 14.9 m, 1600 dpi, 126.8 px/m): crown 2161 px, upper row 2397, main row 2748, keel 3246 (dimension lines break the outline scan)'), cal=[20.94, 40.3, 49.19], fill=[dict(deck=1, a=27.81, b=46.97, why='main-deck windows hidden by the wing and engines in the side view')], note='Airbus AC A380 (1 Dec 2025) FIGURE-2-7-0-991-002-A01 Door Location sheet 2 (scale: upper-deck doors U1-U3 at 20.94 / 40.30 / 49.19 m; main deck M1-M5 6.32 / 16.50 / 32.68 / 44.74 / 53.63 m)'),
    'a359': dict(pdf=AC + 'airbus_AC_A350_20250715.pdf', page=49, cal=[6.82, 18.86, 37.93, 52.55], note='Airbus AC A350 (15 Jul 2025) FIGURE-2-2-0-991-001-A01 sheet 1 (A350-900; raster drawing)'),
    'a35k': dict(pdf=AC + 'airbus_AC_A350_20250715.pdf', page=51, cal=[6.82, 23.30, 42.38, 59.53], note='Airbus AC A350 (15 Jul 2025) 2-2-0 page 4 (A350-1000; raster drawing)'),
    # Bombardier CRJ Airport Planning Manuals, 00-02-01 General Airplane Dimensions (metric figure)
    'crj2': dict(pdf=AC + 'bombardier_CRJ200APMR8.pdf', page=25, clip=(140, 505, 500, 625), dpi=1200, note='Bombardier CRJ200 APM rev. 8, 00-02-01 Figure 2 (raster drawing)'),
    'crj7': dict(pdf=AC + 'bombardier_CRJ700APMR15.pdf', page=31, note='Bombardier CRJ700 APM rev. 15, General Airplane Dimensions (ba008a01)'),
    'crj9': dict(pdf=AC + 'bombardier_CRJ900APMR11.pdf', page=31, note='Bombardier CRJ900 APM rev. 11, General Airplane Dimensions (bapu5z01)'),
    # Embraer Airport Planning Manuals, 2.1 General Aircraft Dimensions
    'e75l': dict(pdf=AC + 'embraer_E175_APM_ntsb.pdf', page=31, note='Embraer 175 APM, Figure 2.1 General Aircraft Dimensions'),
    'e190': dict(pdf=AC + 'embraer_APM_190.pdf', page=30, note='Embraer 190 APM (May 2021), Figure 2.1 General Aircraft Dimensions'),
    'e195': dict(pdf=AC + 'embraer_APM_195.pdf', page=34, note='Embraer 195 APM, Figure 2.1 General Aircraft Dimensions'),
    # Airbus Canada A220 Airport Planning Publications
    'bcs1': dict(pdf=AC + 'airbus_A220-100APP.pdf', page=22, note='A220-100 APP, General aircraft dimensions'),
    'bcs3': dict(pdf=AC + 'airbus_A220-300APP.pdf', page=24, note='A220-300 APP, General aircraft dimensions'),
}


# ---------------------------------------------------------------- geometry sources
def dxf_polys(path):
    import ezdxf
    from ezdxf import path as ezpath
    doc = ezdxf.readfile(path)
    out = []
    def emit(e, depth=0):
        t = e.dxftype()
        if t in ('TEXT', 'MTEXT', 'DIMENSION', 'HATCH', 'SOLID', 'POINT', 'ATTDEF', 'ATTRIB', 'VIEWPORT', 'LEADER', 'MLEADER'): return
        if t == 'INSERT':
            if depth > 6: return
            try:
                for v in e.virtual_entities(): emit(v, depth + 1)
            except Exception: pass
            return
        try:
            p = ezpath.make_path(e)
            pts = np.array([(v.x, v.y) for v in p.flattening(0.02)])
        except Exception:
            return
        if len(pts) >= 2: out.append(pts)
    for e in doc.modelspace(): emit(e)
    return out


def pdf_polys(path, page):
    import pymupdf
    p = pymupdf.open(path)[page - 1]
    out = []
    H = p.rect.height
    for dr in p.get_drawings():
        for it in dr['items']:
            k = it[0]
            if k == 'l': pts = [it[1], it[2]]
            elif k == 'c':
                P0, P1, P2, P3 = it[1:5]
                pts = []
                for t in np.linspace(0, 1, 7):
                    a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t * t; d = t ** 3
                    pts.append(pymupdf.Point(a * P0.x + b * P1.x + c * P2.x + d * P3.x, a * P0.y + b * P1.y + c * P2.y + d * P3.y))
            elif k == 're':
                r = it[1]; pts = [r.tl, r.tr, r.br, r.bl, r.tl]
            elif k == 'qu':
                q = it[1]; pts = [q.ul, q.ur, q.lr, q.ll, q.ul]
            else: continue
            out.append(np.array([(q.x, H - q.y) for q in pts]))     # y up
    return out


def spec():
    js = r"""import { SPEC, TYPES } from './js/aircraft/types.js';
const o = {}; for (const k in SPEC) { const S = SPEC[k], T = TYPES[k]; o[k] = { L: S.L, doors: S.doors, R: T ? T.R : null, crown: S.crown || null, sill: S.sill || null }; }
console.log(JSON.stringify(o));"""
    r = subprocess.run(['node', '--no-warnings', '--input-type=module', '-e', js], cwd=ROOT, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


# ---------------------------------------------------------------- raster analysis (every document is rendered to ink)
def raster_dxf(polys, k, box=None):
    """draw the polylines at k px per drawing unit; returns (ink bool image, x0, y1) with px = (x - x0) * k,
    py = (y1 - y) * k"""
    from PIL import Image, ImageDraw
    P = np.vstack(polys); lo, hi = P.min(0), P.max(0)
    if box is not None: lo, hi = np.maximum(lo, box[0]), np.minimum(hi, box[1])
    Wd, Hd = int((hi[0] - lo[0]) * k) + 4, int((hi[1] - lo[1]) * k) + 4
    im = Image.new('L', (Wd, Hd), 0); d = ImageDraw.Draw(im)
    for p in polys:
        if p[:, 0].max() < lo[0] or p[:, 0].min() > hi[0] or p[:, 1].max() < lo[1] or p[:, 1].min() > hi[1]: continue
        q = [((x - lo[0]) * k + 2, (hi[1] - y) * k + 2) for x, y in p]
        d.line(q, fill=255, width=1)
    return np.asarray(im) > 0, lo[0] - 2 / k, hi[1] + 2 / k


def raster_pdf(path, page, dpi, clip=None):
    import pymupdf
    pg = pymupdf.open(path)[page - 1]
    cl = pymupdf.Rect(*clip) if clip else None
    pix = pg.get_pixmap(dpi=dpi, clip=cl, colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    return a < 150, (cl.x0 if cl else 0.0), (cl.y0 if cl else 0.0)


def window_blobs(ink, wmin, wmax):
    """closed outlines of window size: holes of the ink image (white interiors enclosed by ink)"""
    from scipy import ndimage
    filled = ndimage.binary_fill_holes(ink)
    holes = filled & ~ink
    lab, n = ndimage.label(holes)
    out = []
    for k, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None: continue
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if not (wmin <= w <= wmax and wmin <= h <= 3.2 * wmax and 0.8 < h / max(w, 1) < 3.2): continue
        area = (lab[sl] == k + 1).sum()
        if area < 0.5 * w * h: continue                 # a hole of window shape (rounded rectangle / circle), not a sliver
        out.append(dict(c=np.array([(sl[1].start + sl[1].stop) / 2, (sl[0].start + sl[0].stop) / 2]), w=w, h=h))
    return out


def rows_px(blobs, minn=8):
    """window rows: blobs of similar size along a straight line (the side views of the AC are drawn at the aircraft
    attitude, so a row may be slightly inclined); per row: centres xs, ys, the fitted line y = y0 + slope (x - xm)"""
    if not blobs: return []
    X = np.array([[b['c'][0], b['c'][1], b['w'], b['h']] for b in blobs], float)
    used = np.zeros(len(X), bool); out = []
    for i in np.argsort(-X[:, 3]):
        if used[i]: continue
        g = np.where((np.abs(X[:, 1] - X[i, 1]) < 0.7 * X[i, 3] + 1) & (np.abs(X[:, 2] - X[i, 2]) < 0.2 * X[i, 2] + 1.5)
                     & (np.abs(X[:, 3] - X[i, 3]) < 0.2 * X[i, 3] + 1.5) & ~used)[0]
        if len(g) < minn: continue
        # straight line through the group; drop outliers more than 0.25 window heights off it
        for _ in range(3):
            A_ = np.stack([X[g, 0], np.ones(len(g))], 1); sl, ic = np.linalg.lstsq(A_, X[g, 1], rcond=None)[0]
            ok = np.abs(X[g, 1] - (sl * X[g, 0] + ic)) < 0.25 * np.median(X[g, 3]) + 1
            g = g[ok]
            if len(g) < minn: break
        if len(g) < minn: continue
        used[g] = True
        o = np.argsort(X[g, 0]); g = g[o]
        xs = X[g, 0]; d = np.diff(xs); med = float(np.median(d))
        reg = float(np.mean(np.abs(d - med) < 0.1 * med))
        if reg < 0.5 or not (1.3 * np.median(X[g, 2]) < med < 4.5 * np.median(X[g, 2])): continue
        xm = float(xs.mean())
        out.append(dict(y=float(sl * xm + ic), slope=float(sl), xm=xm, n=int(len(g)), w=float(np.median(X[g, 2])), h=float(np.median(X[g, 3])), xs=xs, ys=X[g, 1],
                        pitch=med, reg=reg))
    return sorted(out, key=lambda r: -r['n'])


def trim_row(r):
    """drop short runs (< 3 windows) at the ends of a row that are separated by more than 2.5 pitches: flight-deck side
    windows or other window-sized outlines at the row height, not cabin windows"""
    xs, ys = r['xs'], r['ys']; p = r['pitch']
    runs = np.split(np.arange(len(xs)), np.where(np.diff(xs) > 2.5 * p)[0] + 1)
    while len(runs) > 1 and len(runs[0]) < 3: runs = runs[1:]
    while len(runs) > 1 and len(runs[-1]) < 3: runs = runs[:-1]
    keep = np.concatenate(runs)
    return dict(r, xs=xs[keep], ys=ys[keep], n=int(len(keep)))


def row_y(row, x):
    return row['y'] + row.get('slope', 0.0) * (np.asarray(x, float) - row.get('xm', 0.0))


def partial_windows(ink, row, occl_min=0.25):
    """windows partly hidden behind the wing root (hidden-line side views draw only their upper part): positions along
    the row where the upper outline of a window (template = mean of the complete windows) matches the ink, and that are
    at least half a pitch from a complete window"""
    import cv2
    W, H = int(round(row['w'])), int(round(row['h'])); y0 = row['y']; m = 3
    if abs(row.get('slope', 0.0)) * ink.shape[1] > 0.2 * H: return []       # inclined row: no template scan
    crops = []
    for x in row['xs']:
        x0, yt = int(round(x - W / 2)) - m, int(round(row_y(row, x) - H / 2)) - m
        c = ink[yt:yt + H + 2 * m, x0:x0 + W + 2 * m]
        if c.shape == (H + 2 * m, W + 2 * m): crops.append(c.astype(np.float32))
    if len(crops) < 4: return []
    T = np.mean(crops, 0)
    top = T[:int(m + 0.45 * H)]
    band = ink[int(y0 - H / 2) - m:int(y0 - H / 2) - m + top.shape[0] + 4, :].astype(np.float32)
    if band.shape[0] < top.shape[0]: return []
    r = cv2.matchTemplate(band, top, cv2.TM_CCOEFF_NORMED)
    score = r.max(0)
    xs_full = row['xs']; out = []
    pitch = row['pitch']
    cand = np.where(score > 0.62)[0]
    for x in cand:
        xc = x + top.shape[1] / 2
        if np.abs(xs_full - xc).min() < 0.6 * pitch: continue
        if out and abs(out[-1][0] - xc) < 0.6 * pitch:
            if score[x] > out[-1][1]: out[-1] = (xc, float(score[x]))
            continue
        # only between the first and last complete window (cabin), not at the ends
        if xc < xs_full.min() or xc > xs_full.max(): continue
        out.append((xc, float(score[x])))
    return out


def hidden_windows(ink, row, xs, doors=()):
    """windows hidden behind the wing in the side view: in a gap of the row longer than 1.6 pitches, the positions that
    continue the pitch are windows when the drawing shows an occluding stroke across the window band there (ink in more
    than half of the columns of the window box); a door or an exit in the gap is drawn as a few vertical strokes and is
    not filled"""
    out = []; p = row['pitch']; W, H = row['w'], row['h']
    for a, b in zip(xs[:-1], xs[1:]):
        g = b - a
        if g < 1.6 * p: continue
        n = int(round(g / p)) - 1
        for i in range(1, n + 1):
            x = a + g * i / (n + 1)
            if len(doors) and np.abs(np.asarray(doors) - x).min() < 1.2 * p: continue       # a door: no window
            y0 = float(row_y(row, x))
            box = ink[int(y0 - H / 2):int(y0 + H / 2) + 1, int(x - W / 2):int(x + W / 2) + 1]
            if not box.size: continue
            cols = box.any(0).mean()
            # an occluding wing / fairing crosses most of the window box; a single missing window (gap of two pitches)
            # with any stroke in its box is hidden by a dimension line
            if cols > 0.5 or (n == 1 and g < 2.4 * p and box.any()): out.append(x)
    return np.array(out)


def outline(ink, row, H_px):
    """nose tip / aft end of the side view and crown / keel at every window: the aircraft is the largest ink component
    crossing the row band"""
    from scipy import ndimage
    y0 = int(round(row['y'])); b0, b1 = max(0, int(y0 - 0.9 * H_px)), min(ink.shape[0], int(y0 + 0.9 * H_px))
    lab, n = ndimage.label(ink, structure=np.ones((3, 3), bool))
    xa, xb = int(row['xs'].min()), int(row['xs'].max()) + 1
    sub = lab[b0:b1, xa:xb]
    ids, cnt = np.unique(sub[sub > 0], return_counts=True)
    ac = ids[np.argmax(cnt)]
    A = lab == ac
    ys, xs = np.nonzero(A)
    nb = np.abs(ys - y0) < 0.5 * H_px
    nose, aft = xs[nb].min(), xs.max()
    crown, keel = [], []
    for x in row['xs']:
        yx = float(row_y(row, x))
        col = np.nonzero(A[:, int(round(x))])[0]
        col = col[np.abs(col - yx) < 0.8 * H_px]
        up = col[col < yx - 0.15 * H_px]; dn = col[col > yx + 0.15 * H_px]
        crown.append(up.min() if len(up) else np.nan); keel.append(dn.max() if len(dn) else np.nan)
    return float(nose), float(aft), np.array(crown, float), np.array(keel, float), A


def door_blobs(ink, row):
    """door outlines around the row: holes 1.5-5 window widths wide and 2.5-8 window heights tall that span the row"""
    from scipy import ndimage
    holes = ndimage.binary_fill_holes(ink) & ~ink
    lab, n = ndimage.label(holes)
    out = []
    for k, sl in enumerate(ndimage.find_objects(lab)):
        if sl is None: continue
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        if not (1.5 * row['w'] <= w <= 10 * row['w'] and 2.3 * row['h'] <= h <= 8 * row['h'] and h > w): continue
        if not (sl[0].start < float(row_y(row, (sl[1].start + sl[1].stop) / 2)) < sl[0].stop): continue
        if (lab[sl] == k + 1).sum() < 0.6 * w * h: continue
        out.append((sl[1].start + sl[1].stop) / 2)
    return np.sort(np.array(out))


def locate_pdf(path, page, dpi_want_px=28):
    """render the page, find the window row, re-render the side view around it so that a window is ~28 px wide"""
    ink0, _, _ = raster_pdf(path, page, 400)
    r0 = rows_px(window_blobs(ink0, 4, 40), 10)
    if not r0: return None
    m0 = r0[0]; ptpx = 72 / 400
    dpi = int(min(2400, max(600, 400 * dpi_want_px / max(m0['w'], 1))))
    span = (m0['xs'].max() - m0['xs'].min()) * ptpx
    clip = (max(0, m0['xs'].min() * ptpx - 0.45 * span), max(0, m0['y'] * ptpx - 0.3 * span), m0['xs'].max() * ptpx + 0.45 * span, m0['y'] * ptpx + 0.16 * span)
    ink, _, _ = raster_pdf(path, page, dpi, clip)
    return ink, dpi / 400, m0


def measure(t, D, S, plot=None):
    """window rows of type t on document D (see DOCS); scale / origin: DXF units + nose tip, or the published door
    stations `cal` matched to the door outlines of the drawing (least squares), else the published overall length"""
    path = os.path.join(ROOT, D['dxf'] if 'dxf' in D else D['pdf'])
    if not os.path.exists(path): return dict(error='document not available: ' + os.path.relpath(path, ROOT))
    R = S.get(t, {}).get('R') or 2.0; L = S.get(t, {}).get('L')
    if 'dxf' in D:
        polys = dxf_polys(path); u = D['unit']
        k = D.get('pxm', 80) * u
        ink, _, _ = raster_dxf(polys, k)
        mpp = u / k
        rows = rows_px(window_blobs(ink, int(0.12 / mpp), int(0.6 / mpp)), 8)
    else:
        if D.get('clip'):
            dpi = D.get('dpi', 1600); ink, _, _ = raster_pdf(path, D['page'], dpi, D['clip']); mpp = None
            rows = rows_px(window_blobs(ink, int(dpi / 250), int(dpi / 25)), 8)
        else:
            loc = locate_pdf(path, D['page'])
            if loc is None: return dict(error='no window row found')
            ink, sc, m0 = loc; mpp = None
            rows = rows_px(window_blobs(ink, int(0.6 * m0['w'] * sc), int(1.6 * m0['w'] * sc) + 2), 8)
    if not rows: return dict(error='no window row found')
    rows = [trim_row(r) for r in rows if r['n'] >= 8]
    main = rows[D.get('row', 0)] if D.get('row') is not None else rows[0]
    # stroke width -> window size at mid-stroke (the holes are the glass inside the drawn outline)
    lw = stroke_width(ink, main)
    main = dict(main, w=main['w'] + lw, h=main['h'] + lw)
    doors_px = door_blobs(ink, main)
    cal = None
    calw = None
    if D.get('cal') and len(doors_px) >= 2:
        c = np.array(D['cal'], float)
        if len(doors_px) == len(c): pairs = list(zip(doors_px, c))
        elif len(doors_px) > len(c):
            # more door-like outlines than main doors (over-wing exits): first and last are doors 1 and n; then every
            # outline within 0.5 m of a published door station after that first fit
            b0 = (c[-1] - c[0]) / (doors_px[-1] - doors_px[0]); a0 = c[0] - b0 * doors_px[0]
            pairs = [(x, c[int(np.argmin(np.abs(c - (a0 + b0 * x))))]) for x in doors_px if np.abs(c - (a0 + b0 * x)).min() < 0.5]
            if len({q for _, q in pairs}) < len(pairs): pairs = [(doors_px[0], c[0]), (doors_px[-1], c[-1])]
        else:
            # fewer doors found (a door hidden by the wing or a dimension line): match by the drawing's first-to-last
            # door proportion to the published stations
            d0 = (doors_px - doors_px[0]) / (doors_px[-1] - doors_px[0]); c0 = (c - c[0]) / (c[-1] - c[0])
            pairs = [(x, c[int(np.argmin(np.abs(c0 - q)))]) for x, q in zip(doors_px, d0)]
            if len({q for _, q in pairs}) < len(pairs): pairs = []
        if len(pairs) >= 2:
            xp = np.array([q[0] for q in pairs]); cp = np.array([q[1] for q in pairs])
            A_ = np.stack([xp, np.ones(len(xp))], 1); (b, a) = np.linalg.lstsq(A_, cp, rcond=None)[0]
            cal = dict(b=float(b), a=float(a), resid=float(np.abs(A_ @ np.array([b, a]) - cp).max()), used=[float(v) for v in cp])
            mpp = abs(b)
    H0 = 2.1 * R / mpp if mpp else 2.1 * R * (main['pitch'] / 0.53)
    nose, aft, crown, keel, A = outline(ink, main, H0)
    if mpp is None:
        mpp = L / (aft - nose)
    H_px = 2.1 * R / mpp * D.get('hscale', 1.0)
    nose, aft, crown, keel, A = outline(ink, main, H_px)
    to_s = (lambda x: cal['a'] + cal['b'] * x) if cal else (lambda x: (x - nose) * mpp)
    part = partial_windows(ink, main)
    xs_vis = np.sort(np.concatenate([main['xs'], [p[0] for p in part]])) if part else main['xs']
    hidden = hidden_windows(ink, main, xs_vis, doors_px)
    xs_all = np.sort(np.concatenate([xs_vis, hidden])) if len(hidden) else xs_vis
    s = to_s(xs_all)
    # barrel section: the 30th percentile of the local heights (the 747 hump and the tail taper are excluded)
    Hs = keel - crown; Hb = np.nanpercentile(Hs, 30); good = np.abs(Hs - Hb) < 0.03 * Hb
    eta = (((crown + keel) / 2) - row_y(main, main['xs'])) / (Hs / 2)
    res = dict(src=D['note'], n=int(len(xs_all)), n_full=int(main['n']), n_partial=len(part), n_hidden=int(len(hidden)), s=[round(float(v), 3) for v in s],
               partial=[round(float(to_s(p[0])), 3) for p in part], hidden=[round(float(to_s(x)), 3) for x in hidden],
               pitch=round(main['pitch'] * mpp, 4), w=round(main['w'] * mpp, 3), h=round(main['h'] * mpp, 3),
               eta=round(float(np.nanmedian(eta[good])), 3), yf=round(float((np.nanmedian(eta[good]) + 1) / 2), 3), nyf=int(good.sum()),
               fus_h=round(float(np.nanmedian(Hs[good]) * mpp), 3), L_draw=round(float((aft - nose) * mpp), 3), L_pub=L, mpp=mpp,
               doors=[round(float(to_s(x)), 3) for x in doors_px], nose_s=round(float(to_s(nose)), 3),
               scale=('door stations ' + str(cal['used']) + f' (max residual {cal["resid"]:.2f} m)') if cal else ('drawing units' if 'dxf' in D else 'overall length'))
    if D.get('cal') and not cal: res['warn'] = f'calibration doors: found {len(doors_px)}, expected {len(D["cal"])}; scale from the overall length'
    extra = []
    for r in rows:
        if r is rows[D.get('row', 0) or 0] or r['y'] == main['y']: continue
        if abs(r['y'] - main['y']) < 1.6 * H_px and r['n'] >= 8 and abs(r['w'] + lw - main['w']) < 0.4 * main['w'] and r['xs'].min() > nose:
            extra.append(dict(n=int(r['n']), s=[round(float(to_s(x)), 3) for x in r['xs']], pitch=round(r['pitch'] * mpp, 4),
                              w=round((r['w'] + lw) * mpp, 3), h=round((r['h'] + lw) * mpp, 3), dy=round(float((main['y'] - r['y']) * mpp), 3)))
    if extra: res['rows'] = extra
    # windows hidden by the wing drawn over the fuselage (checked on the plot): the gap [a, b] of the row (deck k) is
    # filled at the row's pitch; doors in the gap are removed later (tools/liveries/windows.py, published door stations)
    for k_, a_, b_, why_ in [(f['deck'], f['a'], f['b'], f['why']) for f in D.get('fill', [])]:
        row_ = res if k_ == 0 else res['rows'][k_ - 1]
        S_ = np.array(row_['s']); p_ = row_['pitch']
        lo_ = S_[S_ <= a_ + 0.05].max(); hi_ = S_[S_ >= b_ - 0.05].min(); n_ = int(round((hi_ - lo_) / p_)) - 1
        add_ = [round(float(lo_ + (hi_ - lo_) * i / (n_ + 1)), 3) for i in range(1, n_ + 1)]
        row_['s'] = sorted(row_['s'] + add_); row_['n'] = len(row_['s'])
        row_.setdefault('filled', []).append(dict(a=float(lo_), b=float(hi_), n=n_, why=why_))
    ov = D.get('override')
    if ov:          # values read by hand off the drawing where the automatic outline scan fails (documented in DOCS)
        for k_, v_ in ov.items():
            if k_ == 'rows_eta':
                for r_, e_ in zip(res.get('rows', []), v_): r_['eta'] = e_
            else: res[k_] = v_
        res['override'] = ov
    if plot:
        from PIL import Image, ImageDraw
        y0 = int(main['y']); b0, b1 = max(0, int(y0 - 1.3 * H_px)), min(ink.shape[0], int(y0 + 1.0 * H_px))
        x0, x1 = max(0, int(nose - 20)), min(ink.shape[1], int(aft + 20))
        im = Image.fromarray(np.where(ink[b0:b1, x0:x1], 0, 255).astype(np.uint8)).convert('RGB'); d = ImageDraw.Draw(im)
        box = lambda x, y, c: d.rectangle([x - x0 - main['w'] / 2, y - b0 - main['h'] / 2, x - x0 + main['w'] / 2, y - b0 + main['h'] / 2], outline=c, width=2)
        for x in main['xs']: box(x, y0, (255, 0, 0))
        for x in hidden: box(x, y0, (0, 200, 0))
        for x, sc_ in part: box(x, y0, (255, 150, 0))
        for x in doors_px: d.line([x - x0, y0 - b0 - 3 * main['h'], x - x0, y0 - b0 + 3 * main['h']], fill=(200, 0, 200), width=3)
        for r in extra:
            for sx in r['s']:
                xx = (sx - cal['a']) / cal['b'] if cal else sx / mpp + nose
                box(xx, main['y'] - r['dy'] / mpp, (0, 160, 255))
        for x, c, kk in zip(main['xs'], crown, keel):
            if not np.isnan(c): d.line([x - x0 - 4, c - b0, x - x0 + 4, c - b0], fill=(0, 0, 255), width=3)
            if not np.isnan(kk): d.line([x - x0 - 4, kk - b0, x - x0 + 4, kk - b0], fill=(0, 170, 0), width=3)
        d.line([nose - x0, 0, nose - x0, im.size[1]], fill=(200, 0, 200), width=2); d.line([aft - x0, 0, aft - x0, im.size[1]], fill=(200, 0, 200), width=2)
        sc2 = min(1.0, 3000 / im.size[0]); im = im.resize((int(im.size[0] * sc2), int(im.size[1] * sc2)), Image.LANCZOS)
        im.save(os.path.join(plot, f'ref_{t}.png'))
    return res


def stroke_width(ink, row):
    """line width of the window outlines (px): ink run length left of the first windows' holes"""
    ws = []
    for x in row['xs'][:12]:
        y = int(round(row['y'])); xi = int(round(x - row['w'] / 2)) - 1
        n = 0
        while xi - n >= 0 and ink[y, xi - n] and n < 40: n += 1
        if n: ws.append(n)
    return float(np.median(ws)) if ws else 0.0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('types', nargs='*'); ap.add_argument('--plot')
    a = ap.parse_args()
    S = spec()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for t in (a.types or list(DOCS)):
        D = DOCS[t]
        try:
            r = measure(t, D, S, a.plot)
        except Exception as e:
            r = dict(error=repr(e))
        old[t] = r
        if 'error' in r: print(f'{t:5s} {r["error"]}')
        else:
            if r.get('warn'): print('      WARN', r['warn'], 'doors', r['doors'])
            print(f'{t:5s} n {r["n"]:3d} ({r["n_full"]} + {r["n_partial"]} partial + {r["n_hidden"]} hidden) pitch {r["pitch"]:.3f} w {r["w"]:.3f} h {r["h"]:.3f} s {r["s"][0]:.2f}..{r["s"][-1]:.2f} yf {r["yf"]:.3f} eta {r["eta"]:.3f} '
                  f'fus_h {r["fus_h"]:.2f} L_draw {r["L_draw"]:.2f} (pub {r["L_pub"]})' + (f' +rows {[(x["n"], x["dy"]) for x in r.get("rows", [])]}' if r.get('rows') else ''))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(old, open(OUT, 'w'), indent=1)
