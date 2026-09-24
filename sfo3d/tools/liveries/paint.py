#!/usr/bin/env python3
"""Livery painter: paints a brand livery into a model's livery atlas (tools/liveries/atlas.py) as it is rendered for
one aircraft type (the type's fuselage plugs, wing-span and fin-height fit, js/aircraft/fit.js, are applied first, so
titles and cheatlines land where they belong on the stretched airframe and are not smeared by a plug).

Every atlas texel knows its point on the aircraft (model frame: x forward, nose tip 0; y up; z starboard; metres of the
source model), its part (fuselage, fin, tailplane, engine nacelle, pylon, wing tip, gear door) and the surface detail of
the neutral skin. A livery is a Python function (tools/liveries/liveries.py) that paints with the primitives of
`Canvas` in side-view terms: regions below / between curves along the body, bands, titles and symbols (re-drawn vector
art, tools/liveries/art.py) placed on the fuselage or the fin, part colours. The result is multiplied by the skin
detail (panel lines, door outlines), dark areas of the source skin are kept, and cabin windows stay windows (alpha 0 =
window glass, used for the cabin glow at night).

Colours are sRGB hex; compositing is done in linear light.
"""
import io, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, sfom
from raster import raster, dilate_fill, sample_bilinear
from common import srgb_to_lin, lin_to_srgb, hex_rgb


def lin(c):
    if isinstance(c, str): c = hex_rgb(c)
    return srgb_to_lin(np.asarray(c, float))


def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


class Canvas:
    def __init__(self, model_path, type_key=None, S=2048):
        m = sfom.load(model_path); h = m['head']; A = h['atlas']
        self.m, self.h, self.A, self.S = m, h, A, S
        self.key = h['key']; self.type = type_key
        app = common.app()
        f = app['types'][type_key]['fit'] if type_key else None
        self.fit = f
        T = app['types'][type_key] if type_key else app['types'][app['base'][h['key']]]
        sc = f['s'] if f else 1.0
        self.doors = [d / sc for d in T['doors']]
        self.T = T
        P = common.apply_stretch(m['pos'], m['zone'], f['stretch'] if f and f['stretch'] else None)
        self.P = P
        mats = h['mats']
        atl = np.array([mats[i].get('atlas', False) for i in m['tri_mat']])
        T = m['idx'][atl]
        tid, bary = raster(m['uv'][T] * S, S, S)
        ok = tid >= 0
        self.ok = ok; self.flat = np.flatnonzero(ok.reshape(-1))
        V = T[tid[ok]]; b = bary[ok]
        self._tri = np.flatnonzero(atl)[tid[ok]]; self._bary = b.astype(np.float32)
        self.pos = (P[V] * b[..., None]).sum(1)
        n = (m['nrm'][V] * b[..., None]).sum(1); self.nrm = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)
        # chart per texel -> part, texel size
        cm = np.full((S, S), -1, np.int32); f_ = S / A['size']
        for ci, c in enumerate(A['charts']):
            cm[int(c['y'] * f_):int((c['y'] + c['h']) * f_), int(c['x'] * f_):int((c['x'] + c['w']) * f_)] = ci
        ci = cm[ok]
        self.chart = ci
        parts = np.array([c['p'] for c in A['charts']] + ['keep'])
        self.part = parts[ci]
        self.sub = np.array([c['s'] for c in A['charts']] + [0])[ci]
        self.tex = 1.0 / (np.array([c['k'] for c in A['charts']] + [A['kpm']])[ci] * f_)   # texel size (m)
        # neutral skin: detail (linear ratio to the white level), keep-original areas, painted windows
        neu = m['textures'][0].resize((S, S), Image.BILINEAR)
        na = np.asarray(neu).astype(np.float32).reshape(-1, 4)[self.flat] / 255
        self.neutral = na[:, :3]; alpha = na[:, 3]
        wl = srgb_to_lin(A['white'])
        lum = self.neutral @ np.array([0.299, 0.587, 0.114])
        self.detail0 = np.clip(srgb_to_lin(lum) / wl, 0, 1.25)
        self.keep = np.clip(1 - np.abs(alpha - 0.75) / 0.12, 0, 1) * (alpha > 0.55)
        self.win = np.clip((0.55 - alpha) / 0.5, 0, 1)
        # geometry frames
        self.env = common.Envelope(P, m['idx'], m['zone'], float(-P[m['zone'] != 3][:, 0].min()))
        self.L = self.env.L
        self.s = -self.pos[:, 0]; self.y = self.pos[:, 1]; self.z = self.pos[:, 2]
        top, bot, hw = self.env.at(self.s)
        self.top, self.bot, self.hw = top, bot, hw
        self.yc = (top + bot) / 2; self.hh = np.maximum((top - bot) / 2, 0.05)
        self.eta = (self.y - self.yc) / self.hh
        self.H = self.env.mainTop - self.env.mainBot
        self.ycM = (self.env.mainTop + self.env.mainBot) / 2; self.hhM = self.H / 2
        nz = self.nrm[:, 2]
        self.side = np.where(np.abs(nz) > 0.3, np.sign(nz), np.sign(self.z + 1e-9))   # +1 starboard, -1 port
        self._windows()
        self._fin()
        self.eng = A['eng']
        self.reset()

    def reset(self):
        """start a new livery on the same airframe: bare white"""
        self.col = np.tile(lin('#FFFFFF') * 0.93, (len(self.flat), 1))
        self.detail = self.detail0.copy()
        self.notes = []

    # ------------------------------------------------------------------ frames
    def _windows(self):
        m = self.m; P = self.P; Z = m['zone']; idx = m['idx']
        C = P[idx].mean(1); s = -C[:, 0]; g = (Z[idx[:, 0]] == 5) & (s > 0.18 * self.L) & (s < 0.85 * self.L) & (np.abs(C[:, 2]) > 0.5)
        if self.A.get('winPainted') or g.sum() < 20:
            wy = self.y[self.win > 0.5]
            if len(wy) > 20:
                self.winY = float(np.median(wy)); self.winH = float(np.percentile(wy, 97) - np.percentile(wy, 3)); return
            self.winY = self.env.mainBot + 0.6 * self.H; self.winH = 0.33; return
        vy = P[idx[g]].reshape(-1, 3)[:, 1]
        self.winY = float(np.median(vy)); self.winH = float(np.percentile(vy, 95) - np.percentile(vy, 5))
        self.winH = min(max(self.winH, 0.25), 0.5)

    def _fin(self):
        f = self.part == 'fin'
        if f.sum() < 50:
            self.fin = None; return
        y = self.y[f]; s = self.s[f]
        yR = float(self.env.mainTop); yT = float(np.percentile(y, 99.7))
        bands = np.linspace(yR + 0.12 * (yT - yR), yT - 0.06 * (yT - yR), 10)
        le, te, yy = [], [], []
        for a, b in zip(bands[:-1], bands[1:]):
            q = (y >= a) & (y < b)
            if q.sum() < 10: continue
            le.append(np.percentile(s[q], 0.5)); te.append(np.percentile(s[q], 99.5)); yy.append((a + b) / 2)
        pl = np.polyfit(yy, le, 1); pt = np.polyfit(yy, te, 1)
        self.fin = dict(yR=yR, yT=yT, le=pl, te=pt)
        sl = np.polyval(pl, self.y); stt = np.polyval(pt, self.y)
        self.fu = (self.s - sl) / np.maximum(stt - sl, 0.3)
        self.fv = (self.y - yR) / (yT - yR)

    def finzone(self):
        """fin + rudder + the dorsal fillet on the tail cone"""
        if self.fin is None: return self.part == 'fin'
        sle0 = np.polyval(self.fin['le'], self.fin['yR'])
        dors = (self.part == 'fus') & (self.y > self.top + 0.03) & (self.s > sle0 - 0.25 * self.H * 3) & (np.abs(self.z) < 0.25 + 0.06 * self.hw)
        return (self.part == 'fin') | dors

    def fin_proper(self, margin=0.0):
        """the fin itself (behind the leading-edge line: not the dorsal fillet)"""
        if self.fin is None: return self.part == 'fin'
        return (self.part == 'fin') & (self.fu >= -0.02 - margin)

    def fuselage(self):
        return self.part == 'fus'

    # ------------------------------------------------------------------ helpers
    def aa(self, d, q=None):
        """coverage from a signed distance d (m, negative inside) at the texel size (q: texel subset of d)"""
        return np.clip(0.5 - d / (self.tex if q is None else self.tex[q]), 0, 1)

    def curve(self, pts, key='sn'):
        """y(s) of a smooth curve through control points [(sn, eta_or_y), ...]; key 'sn' = eta relative to the local
        section (eta -1 keel, 0 mid, +1 crown), 'abs' = absolute y (m), 'win' = offset from the window centre line in
        multiples of the cabin height"""
        P = np.array(pts, float)
        sn = self.s / self.L
        v = np.interp(sn, P[:, 0], P[:, 1])
        # smooth with a monotone cubic through the points
        try:
            from scipy.interpolate import PchipInterpolator
            v = PchipInterpolator(P[:, 0], P[:, 1], extrapolate=True)(np.clip(sn, P[0, 0], P[-1, 0]))
        except Exception: pass
        if key == 'sn': return self.yc + v * self.hh
        if key == 'cabin': return self.ycM + v * self.hhM
        if key == 'win': return self.winY + v * self.H
        return v

    def paint(self, alpha, color, where=None):
        a = np.clip(np.asarray(alpha, float), 0, 1)
        if where is not None: a = a * where
        if np.ndim(a) == 0: a = np.full(len(self.col), float(a))
        c = lin(color) if not (isinstance(color, np.ndarray) and color.ndim == 2) else color
        self.col = self.col * (1 - a[:, None]) + c * a[:, None]

    def paint_rgba(self, rgba_lin, where=None):
        a = rgba_lin[:, 3] if where is None else rgba_lin[:, 3] * where
        self.col = self.col * (1 - a[:, None]) + rgba_lin[:, :3] * a[:, None]

    def below(self, ycurve, color, where=None, soft=0.0):
        d = self.y - ycurve                     # < 0 below
        a = self.aa(d) if soft <= 0 else smooth(0.5 - d / soft)
        self.paint(a, color, where)

    def above(self, ycurve, color, where=None):
        self.paint(self.aa(ycurve - self.y), color, where)

    def band(self, ycurve, width, color, where=None):
        d = np.abs(self.y - ycurve) - width / 2
        self.paint(self.aa(d), color, where)

    def gradient(self, stops, t, where=None):
        """per-texel colour from a gradient: stops [(t, hex), ...], t array"""
        T = np.array([q[0] for q in stops]); C = np.array([lin(q[1]) for q in stops])
        t = np.clip(t, T[0], T[-1])
        col = np.stack([np.interp(t, T, C[:, k]) for k in range(3)], -1)
        a = np.ones(len(t)) if where is None else where.astype(float)
        self.col = self.col * (1 - a[:, None]) + col * a[:, None]

    # ------------------------------------------------------------------ polygons in design coordinates
    def coords(self, space):
        """per-texel design coordinates and their metric scales (m per unit) for antialiasing:
        'side' (sn = s/L, eta), 'fin' (fu, fv), 'abs' (s, y) metres, 'win' (sn, (y - winY) / H)"""
        if space == 'side': return self.s / self.L, self.eta, self.L, self.hh
        if space == 'cabin': return self.s / self.L, (self.y - self.ycM) / self.hhM, self.L, self.hhM
        if space == 'win': return self.s / self.L, (self.y - self.winY) / self.H, self.L, self.H
        if space == 'abs': return self.s, self.y, 1.0, 1.0
        if space == 'fin':
            F = self.fin; ch = np.maximum(np.polyval(F['te'], self.y) - np.polyval(F['le'], self.y), 0.3)
            return self.fu, self.fv, ch, F['yT'] - F['yR']
        raise ValueError(space)

    def poly_alpha(self, pts, space='side', sel=None):
        """antialiased coverage of a polygon [(a, b), ...] in design coordinates"""
        a, b, sa, sb = self.coords(space)
        if sel is None: sel = np.ones(len(a), bool)
        idx = np.flatnonzero(sel)
        out = np.zeros(len(a))
        if not len(idx): return out
        A = a[idx]; Bv = b[idx]
        SA = sa[idx] if np.ndim(sa) else np.full(len(idx), sa); SB = sb[idx] if np.ndim(sb) else np.full(len(idx), sb)
        P = np.asarray(pts, float)
        # bbox cull
        lo = P.min(0); hi = P.max(0); m = (A >= lo[0] - 0.05) & (A <= hi[0] + 0.05) & (Bv >= lo[1] - 0.05) & (Bv <= hi[1] + 0.05)
        if not m.any(): return out
        idx = idx[m]; A = A[m]; Bv = Bv[m]; SA = SA[m]; SB = SB[m]
        inside = np.zeros(len(A), bool); d2 = np.full(len(A), np.inf)
        n = len(P)
        for i in range(n):
            x0, y0 = P[i]; x1, y1 = P[(i + 1) % n]
            if True:
                cond = ((y0 > Bv) != (y1 > Bv)) & (A < (x1 - x0) * (Bv - y0) / ((y1 - y0) if y1 != y0 else 1e-12) + x0)
                inside ^= cond
            # distance to the segment in metres
            ex, ey = (x1 - x0) * SA, (y1 - y0) * SB; px, py = (A - x0) * SA, (Bv - y0) * SB
            L2 = ex * ex + ey * ey
            t = np.clip((px * ex + py * ey) / np.maximum(L2, 1e-12), 0, 1)
            d2 = np.minimum(d2, (px - t * ex) ** 2 + (py - t * ey) ** 2)
        sd = np.sqrt(d2) * np.where(inside, -1, 1)
        out[idx] = np.clip(0.5 - sd / self.tex[idx], 0, 1)
        return out

    def poly(self, pts, color, space='side', where=None):
        sel = where if where is not None else (self.finzone() if space == 'fin' else None)
        self.paint(self.poly_alpha(pts, space, sel), color)


    # ------------------------------------------------------------------ parts
    def engines(self, color, lip='#B9BDC2', lip_len=0.07, where=None):
        e = self.part == 'eng'
        if where is not None: e = e & where
        self.paint(e.astype(float), color)
        if lip and len(self.eng):
            for j, E in enumerate(self.eng):
                q = e & (self.sub == j)
                x1 = self.pos[q, 0].max() if q.any() else 0
                L = max(E['x1'] - E['x0'], 1.0)
                a = np.zeros(len(self.col)); a[q] = self.aa(-(self.pos[q, 0] - (x1 - lip_len * L)), q)
                self.paint(a, lip)

    def eng_angle(self):
        """per engine texel: angle around the nacelle axis, 0 = top, +90 = outboard (away from the fuselage)"""
        ang = np.full(len(self.col), np.nan)
        for j, E in enumerate(self.eng):
            q = (self.part == 'eng') & (self.sub == j)
            dz = self.z[q] - E['zc']; dy = self.y[q] - E['yc']
            out = np.sign(E['zc']) if abs(E['zc']) > 0.5 else 1
            ang[q] = np.degrees(np.arctan2(dz * out, dy))
        return ang

    def tips(self, color):
        self.paint((self.part == 'tip').astype(float), color)

    def hstab(self, color):
        self.paint((self.part == 'hstab').astype(float), color)

    def pylons(self, color):
        self.paint((self.part == 'pylon').astype(float), color)

    def gear_doors(self, color):
        self.paint((self.part == 'gdoor').astype(float), color)

    # ------------------------------------------------------------------ decals
    def decal(self, img, s0, yc, height, mode='text', where=None, width=None, s_anchor='start'):
        """place an RGBA image (PIL, sRGB) on the side of the body, `height` metres tall, centred at y = yc (array or
        scalar), starting at station s0 (mode 'text': reads left-to-right on both sides; 'mirror': same station mapping on
        both sides, so a symbol faces forward on both sides). s_anchor 'center' centres the image on s0."""
        im = np.asarray(img.convert('RGBA')).astype(np.float32) / 255
        hpx, wpx = im.shape[:2]
        w = width if width is not None else height * wpx / hpx
        if s_anchor == 'center': s0 = s0 - w / 2
        u = (self.s - s0) / w
        stb = self.side > 0
        if mode == 'text': u = np.where(stb, 1 - u, u)
        v = (np.asarray(yc) + height / 2 - self.y) / height
        inb = (u > -0.01) & (u < 1.01) & (v > -0.01) & (v < 1.01)
        if where is not None: inb &= where
        if not inb.any(): return
        prem = im.copy(); prem[..., :3] = srgb_to_lin(prem[..., :3]) * prem[..., 3:4]
        smp = sample_bilinear(prem, np.clip(u[inb], 0, 1), np.clip(v[inb], 0, 1), wrap=False)
        a = smp[:, 3]
        col = smp[:, :3] / np.maximum(a[:, None], 1e-6)
        self.col[inb] = self.col[inb] * (1 - a[:, None]) + col * a[:, None]

    def fin_decal(self, img, fu, fv, height, mode='mirror', shear=False, where=None, rotate=0.0):
        """place an image on the fin: centre at fin coordinates (fu along the chord 0 = LE .. 1 = TE, fv 0 = root ..
        1 = tip), `height` as a fraction of the fin height. Upright (not sheared) unless shear=True (follows the
        leading-edge sweep). mode 'mirror' faces forward on both sides."""
        if self.fin is None: return
        F = self.fin; H = F['yT'] - F['yR']
        yc = F['yR'] + fv * H
        sl = np.polyval(F['le'], yc); st = np.polyval(F['te'], yc)
        sc = sl + fu * (st - sl)
        im = np.asarray(img.convert('RGBA')).astype(np.float32) / 255
        hpx, wpx = im.shape[:2]; hm = height * H; wm = hm * wpx / hpx
        ds = self.s - sc
        if shear:
            ds = ds - (np.polyval(F['le'], self.y) - np.polyval(F['le'], yc))
        dy = self.y - yc
        if rotate:
            r = math.radians(rotate); ds, dy = ds * math.cos(r) + dy * math.sin(r), -ds * math.sin(r) + dy * math.cos(r)
        u = ds / wm + 0.5
        if mode == 'text': u = np.where(self.side > 0, 1 - u, u)
        v = 0.5 - dy / hm
        zone = self.finzone() if where is None else where
        inb = zone & (u > -0.01) & (u < 1.01) & (v > -0.01) & (v < 1.01)
        if not inb.any(): return
        prem = im.copy(); prem[..., :3] = srgb_to_lin(prem[..., :3]) * prem[..., 3:4]
        smp = sample_bilinear(prem, np.clip(u[inb], 0, 1), np.clip(v[inb], 0, 1), wrap=False)
        a = smp[:, 3]; col = smp[:, :3] / np.maximum(a[:, None], 1e-6)
        self.col[inb] = self.col[inb] * (1 - a[:, None]) + col * a[:, None]

    # ------------------------------------------------------------------ GPL source liveries
    def source_uv(self):
        """per texel: the UV of the same surface point in the ORIGINAL (pre-atlas) model, i.e. in the UV layout of the
        FlightGear / FlightAirMap source textures (triangles matched by their quantised vertex positions)"""
        if getattr(self, '_suv', None) is not None: return self._suv
        orig = sfom.load(os.path.join(common.ORIG, self.key + '.sfom'), textures=False)
        raw = self.m['raw']; h = self.h
        def qpos(mm, hh):
            q = hh['quant']; return np.round((mm['pos'] - np.array(q['pmin'])) / np.maximum(np.array(q['pscale']), 1e-12)).astype(np.int64)
        qa = qpos(self.m, h); qo = qpos(orig, orig['head'])
        key = lambda Q, I: [tuple(Q[I[t]].reshape(-1)) for t in range(len(I))]
        omap = {}
        for t, k in enumerate(key(qo, orig['idx'])): omap.setdefault(k, t)
        tris = np.unique(self._tri)
        amap = {}
        for t in tris:
            k = tuple(qa[self.m['idx'][t]].reshape(-1)); amap[t] = omap.get(k, -1)
        ot = np.array([amap[t] for t in self._tri]); okm = ot >= 0
        uv = np.zeros((len(self._tri), 2)); OU = orig['uv']; OI = orig['idx']
        uv[okm] = (OU[OI[ot[okm]]] * self._bary[okm][..., None]).sum(1)
        self._suv = (uv, okm)
        return self._suv

    def from_texture(self, img, where=None, keep_detail=False):
        """paint texels from a livery texture made for the source model's UV layout (e.g. a GPL FlightGear livery)"""
        uv, okm = self.source_uv()
        sel = okm if where is None else (okm & where)
        arr = np.asarray(img.convert('RGBA')).astype(np.float32) / 255
        smp = sample_bilinear(arr, uv[sel, 0] % 1.0, uv[sel, 1] % 1.0)
        a = smp[:, 3:4]
        self.col[sel] = self.col[sel] * (1 - a) + srgb_to_lin(smp[:, :3]) * a
        if not keep_detail: self.detail[sel] = np.where(a[:, 0] > 0.5, 1.0, self.detail[sel])
        return sel

    # ------------------------------------------------------------------ output
    def finish(self, white_detail=True):
        """apply skin detail, kept dark areas and windows; returns RGBA uint8 image (S x S)"""
        col = self.col * self.detail[:, None]
        orig = srgb_to_lin(self.neutral)
        col = col * (1 - self.keep[:, None]) + orig * self.keep[:, None]
        glass = lin('#14181D')
        col = col * (1 - self.win[:, None]) + glass * self.win[:, None]
        S = self.S
        img = np.zeros((S * S, 4), np.float32)
        img[self.flat, :3] = lin_to_srgb(col); img[self.flat, 3] = 1 - self.win
        img = img.reshape(S, S, 4)
        img, _ = dilate_fill(img, self.ok, radius=max(8, S // 128))
        return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------------- text
def text_image(text, font_path, px=400, color='#000000', spacing=0.0, stretch=1.0, italic_shear=0.0, stroke=0, stroke_color=None, pad=0.06):
    """render a title as an RGBA image: `px` = cap height region, spacing = extra letter spacing (fraction of px),
    stretch = horizontal scale, italic_shear = slant (dx/dy)"""
    f = ImageFont.truetype(font_path, px)
    widths = [f.getlength(ch) for ch in text]
    total = sum(widths) + spacing * px * (len(text) - 1)
    asc, desc = f.getmetrics()
    W = int(total + 2 * pad * px + abs(italic_shear) * (asc + desc)) + 4; Hh = asc + desc + int(2 * pad * px)
    im = Image.new('L', (W, Hh), 0); d = ImageDraw.Draw(im)
    x = pad * px + (abs(italic_shear) * (asc + desc) if italic_shear < 0 else 0)
    for ch, w in zip(text, widths):
        d.text((x, pad * px), ch, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
        x += w + spacing * px
    if italic_shear:
        im = im.transform(im.size, Image.AFFINE, (1, italic_shear, -italic_shear * Hh * 0.5, 0, 1, 0), Image.BICUBIC)
    bb = im.getbbox()
    if bb: im = im.crop((max(bb[0] - 4, 0), max(bb[1] - 4, 0), min(bb[2] + 4, im.size[0]), min(bb[3] + 4, im.size[1])))
    if stretch != 1.0: im = im.resize((max(1, int(im.size[0] * stretch)), im.size[1]), Image.LANCZOS)
    rgb = Image.new('RGBA', im.size, tuple(int(c * 255) for c in hex_rgb(color)) + (0,))
    rgb.putalpha(im)
    return rgb


def svg_image(svg, height_px=1024):
    import cairosvg
    png = cairosvg.svg2png(bytestring=svg.encode(), output_height=height_px)
    return Image.open(io.BytesIO(png)).convert('RGBA')


def bake(code, model_path, type_key, S=2048):
    import liveries
    L = liveries.LIVERIES[code]
    c = Canvas(model_path, type_key, S)
    L['paint'](c)
    return c.finish(), c


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('brand'); ap.add_argument('model'); ap.add_argument('--type'); ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--out', default='livery.webp'); ap.add_argument('--preview')
    a = ap.parse_args()
    img, c = bake(a.brand, a.model, a.type, a.size)
    img.save(a.out, 'WEBP', quality=90, method=6)
    print(a.out, os.path.getsize(a.out))
    if a.preview:
        import preview
        m, P = preview.load_for(a.model, a.type)
        preview.sheet(m, P, ['side', '34', 'stbd34', 'rear34'], img, 1000, 470, title=f'{a.brand} {a.type or ""}').save(a.preview)


def spline(ctrl, n=16, closed=False):
    """Catmull-Rom points through control points (for smooth outlines in design coordinates)"""
    P = np.asarray(ctrl, float)
    if closed: P = np.vstack([P[-1:], P, P[:2]])
    else: P = np.vstack([P[:1], P, P[-1:]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed: out.append(P[-2])
    return [tuple(q) for q in out]
