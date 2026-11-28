"""Material swatches cut from the reference photographs: a small clean patch of a real surface, straightened to
true scale on its plane, evened out (the photograph's light gradient divided away), made to tile, and given the
mean colour the material should have under the viewer's light.  The viewer lays them over the model with the
model's own UVs (metres), so they repeat without gaps and take the scene's light and shadows.

    make(cams, parts) -> {material: {image, size: [u metres, v metres]}}   (files written into out/, never committed)

House 2: every patch is named by a pixel of a registered photograph (SWATCHES).  The pixel's ray is cast into the
built model (Scene), which gives the surface's plane; the rectangle is laid in that plane along the kit's UV axes
(u horizontal, v up / up-slope; on the ground u = world X), so the rectified patch is at true scale and the right way
round for the model's metre UVs.  A photograph that is not registered can still give a patch from four hand-picked
corners of a flat rectangle of known size (`quad`: the fireplace's stone).  The patch is evened out (delight), made to
tile by a minimum-error cut through the overlap of its two ends (the period is searched so that courses meet), and
given its material's mean albedo (ALBEDO values tuned by rendering through the source cameras under the viewer's
light).  The terrace flagstone lies at 45 deg to the terrain's world-axis UVs: its square tile is re-sampled into the
world-aligned tile of sqrt(2) times its side, which the same pattern fills periodically (`diag`).
Albedos: the ground materials keep the ratios they have to the sunlit flagstone in the aerial (flagstone 0.50, which
matches p21 under the viewer's light); the aerial itself is exposed ~1.7x brighter than the viewer's light and is not
chased with albedos above what the materials can have.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PPM = 96                                             # texels per metre of the swatches


class Scene:
    """The built model's solid surfaces (no plants) for ray casts: which surface, plane and material a pixel shows."""

    def __init__(self, parts):
        T, N, M = [], [], []
        self.mats, self.parts = [], []
        for p in parts:
            if p.name.startswith('plant'):
                continue
            for m in p.geo.meshes():
                if not len(m.F):
                    continue
                V = np.asarray(m.V, float)
                tri = V[np.asarray(m.F, int)]
                T.append(tri)
                M.append(np.full(len(tri), len(self.mats)))
                self.mats.append(m.mat)
                self.parts.append(p.name)
        self.T = np.vstack(T)
        self.M = np.concatenate(M)
        self.e1, self.e2 = self.T[:, 1] - self.T[:, 0], self.T[:, 2] - self.T[:, 0]

    @classmethod
    def cached(cls):
        """For the scratch tools: build the zones once per process."""
        import importlib
        parts = []
        for z in ('ground', 'pool', 'yard', 'house', 'roof_details'):
            parts += importlib.import_module('model.zones.' + z).build()
        return cls(parts)

    def ray(self, C, d):
        """First hit of the ray C + t d: dict(p, n (toward the ray's origin), mat, part, t) or None."""
        C, d = np.asarray(C, float), np.asarray(d, float)
        h = np.cross(d, self.e2)
        a = (self.e1 * h).sum(1)
        ok = np.abs(a) > 1e-12
        f = 1.0 / np.where(ok, a, 1.0)
        s = C - self.T[:, 0]
        u = f * (s * h).sum(1)
        q = np.cross(s, self.e1)
        v = f * (q @ d)
        t = f * (self.e2 * q).sum(1)
        ok &= (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
        if not ok.any():
            return None
        i = np.flatnonzero(ok)[np.argmin(t[ok])]
        n = np.cross(self.e1[i], self.e2[i])
        n /= np.linalg.norm(n)
        if n @ d > 0:
            n = -n
        return dict(p=C + t[i] * d, n=n, mat=self.mats[self.M[i]], part=self.parts[self.M[i]], t=float(t[i]))

    def cast(self, cam, uv):
        sys.path.insert(0, os.path.join(HERE, 'tools'))
        import cams as CAMS
        d = np.asarray(CAMS.ray(cam, [uv])[1], float).reshape(-1, 3)[0]
        return self.ray(cam['C'], d)


def rect_axes(hit, w_m, h_m, rot=0.0):
    """The rectangle w_m x h_m centred on a hit, in its surface's plane: (origin, eu, ev).  eu is horizontal and ev
    up / up-slope as the kit's UVs run (on level ground: eu = world X); rot (deg) turns both in the plane."""
    n = np.asarray(hit['n'], float)
    if abs(n[2]) > 0.985:                      # ground: UVs are world x, y
        n = np.array([0.0, 0.0, 1.0])
        eu = np.array([1.0, 0.0, 0.0])
    else:
        eu = np.cross([0.0, 0.0, 1.0], n)
        eu /= np.linalg.norm(eu)
    ev = np.cross(n, eu)
    a = np.radians(rot)
    eu, ev = np.cos(a) * eu + np.sin(a) * ev, -np.sin(a) * eu + np.cos(a) * ev
    return np.asarray(hit['p'], float) - eu * w_m / 2 - ev * h_m / 2, eu, ev


def rectify(src, cam, origin, eu, ev, w_m, h_m, ppm=PPM):
    """Sample the photograph on the world rectangle origin + u eu + v ev (u in [0, w_m], v in [0, h_m]).
    Row 0 of the result is v = h_m (so that v runs up the image, as texture coordinates do)."""
    import cv2
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    import cams as CAMS
    W, H = int(round(w_m * ppm)), int(round(h_m * ppm))
    u, v = np.meshgrid((np.arange(W) + 0.5) / ppm, h_m - (np.arange(H) + 0.5) / ppm)
    P = np.asarray(origin, float) + u[..., None] * np.asarray(eu, float) + v[..., None] * np.asarray(ev, float)
    uv = CAMS.project(cam, P.reshape(-1, 3)).reshape(H, W, 2).astype(np.float32)
    return cv2.remap(src, uv[..., 0], uv[..., 1], cv2.INTER_CUBIC).astype(float)


def delight(a, sigma_px):
    """Divide the slow light gradient away (shade toward one side, a soft shadow), keep the pattern."""
    import cv2
    low = cv2.GaussianBlur(a, (0, 0), sigma_px, borderType=cv2.BORDER_REFLECT)
    return a / np.maximum(low, 1.0) * a.reshape(-1, 3).mean(0)


def _seam(A, B):
    """A and B cover the same strip (h, ov, 3): the minimum-error top-to-bottom path through it (image quilting);
    returns a mask (h, ov) that is 1 where A is kept (left of the path).  The path starts and ends mid-strip, so a
    tile wrapped the other way afterwards still meets itself."""
    e = ((A - B) ** 2).sum(-1)
    h, ov = e.shape
    big = e.max() * h + 1.0
    e = e.copy()
    lock = np.ones(ov, bool)
    lock[ov // 2] = False
    e[0, lock] += big
    e[-1, lock] += big
    c = e.copy()
    for y in range(1, h):
        p = c[y - 1]
        c[y] += np.minimum(p, np.minimum(np.r_[p[1:], np.inf], np.r_[np.inf, p[:-1]]))
    path = np.zeros(h, int)
    path[-1] = int(np.argmin(c[-1]))
    for y in range(h - 2, -1, -1):
        x = path[y + 1]
        lo, hi = max(0, x - 1), min(ov, x + 2)
        path[y] = lo + int(np.argmin(c[y, lo:hi]))
    m = (np.arange(ov)[None, :] < path[:, None]).astype(float)
    import cv2
    return cv2.GaussianBlur(m, (0, 0), 1.2, borderType=cv2.BORDER_REPLICATE)


def join(A, B, ov):
    """A | B side by side, A's last ov columns and B's first ov columns sharing a strip cut along its best seam."""
    m = _seam(A[:, -ov:], B[:, :ov])[..., None]
    return np.concatenate([A[:, :-ov], A[:, -ov:] * m + B[:, :ov] * (1 - m), B[:, ov:]], 1)


def wrap(a, ov_min, ov_max, period=None):
    """A horizontally periodic tile cut from a: the period P (W - ov_max .. W - ov_min) is the shift at which the
    patch best continues itself (courses and joints meet), the two ends are cut along the best seam of the overlap."""
    W = a.shape[1]
    if period is None:
        g = a.mean(-1)
        g = g - g.mean()
        best = None
        for P in range(W - ov_max, W - ov_min + 1):
            d = ((g[:, P:] - g[:, :W - P]) ** 2).mean()
            if best is None or d < best[0]:
                best = (d, P)
        period = best[1]
    P = period
    ov = W - P
    J = join(a, a, ov)                    # period P from column ov on
    s = min(max(ov, W // 2), J.shape[1] - P)
    return J[:, s:s + P]


def diag_tile(t):
    """A square tile (period P both ways) whose pattern lies at 45 deg -> the world-aligned tile of side P sqrt(2)."""
    import cv2
    P = t.shape[0]
    N = int(round(P * np.sqrt(2)))
    k = P * np.sqrt(2) / N
    x, y = np.meshgrid((np.arange(N) + 0.5) * k, (N - np.arange(N) - 0.5) * k)
    c = np.sqrt(0.5)
    u, v = (x * c + y * c) % P, (-x * c + y * c) % P
    pad = cv2.copyMakeBorder(t.astype(np.float32), 1, 1, 1, 1, cv2.BORDER_WRAP)
    return cv2.remap(pad, (u + 0.5).astype(np.float32), (P - v + 0.5).astype(np.float32), cv2.INTER_LINEAR).astype(float)


def finish(a, mean_linear, contrast=1.0, sat=1.0, clip=None):
    """Give the patch the wanted mean colour (linear albedo), keeping its pattern (contrast: its strength, sat: the
    strength of its colour differences alone; clip (lo, hi): the brightness relative to the mean is bent softly into
    that range -- glints, pale lichen, deep joints); returns 8-bit sRGB."""
    lin = (np.clip(a, 0, 255) / 255.0) ** 2.2
    m = lin.reshape(-1, 3).mean(0)
    if clip:
        L = np.maximum((lin / m).mean(-1, keepdims=True), 1e-4)
        lo, hi = clip
        g = np.log(L)
        Lc = np.exp(np.where(g > 0, np.log(hi) * np.tanh(g / np.log(hi)), np.log(lo) * np.tanh(g / np.log(lo))))
        lin = lin * Lc / L
        m = lin.reshape(-1, 3).mean(0)
    if sat != 1.0:
        r = lin / m
        g = r.mean(-1, keepdims=True)
        lin = np.maximum(g + sat * (r - g), 0.02) * m
    lin = np.asarray(mean_linear, float) * (1 + contrast * (lin / m - 1))
    return (np.clip(lin, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def quad_rectify(src, quad, w_m, h_m, ppm):
    """A flat rectangle w_m x h_m seen in an unregistered photograph: its corners (TL, TR, BR, BL pixels) -> patch."""
    import cv2
    W, H = int(round(w_m * ppm)), int(round(h_m * ppm))
    M = cv2.getPerspectiveTransform(np.float32(quad), np.float32([[0, 0], [W, 0], [W, H], [0, H]]))
    return cv2.warpPerspective(src, M, (W, H), flags=cv2.INTER_CUBIC).astype(float)


PHOTOS = dict(p18='photos/p18_150f57.jpg', p29='photos/p29_ddf5dc.jpg', p28='photos/p28_7ae0dd.jpg', p21='photos/p21_160d78.jpg',
              p01='photos/p01_768294.jpg', hero='photos/hero_721b4a.jpg', p24='photos/p24_5e2477.jpg')

# name, materials that wear it, pieces (joined side by side), texels per metre, light-gradient scale (m), contrast,
# mean albedo (linear; tuned under the viewer's light through the source camera).
# blur: px, for a source in deep shade; clip (lo, hi): see finish(); sat: colour differences' strength.
# piece: photo + px (a pixel on the surface: its ray finds the plane) + off (metres along u, v from that point to the
#        patch centre) + size (w, h metres) + rot (deg, turns u / v in the plane);  or photo + quad + size.
# expect: the material the ray must hit (a moved wall or roof is reported, the swatch skipped).
SWATCHES = [
    # terrace flagstone: sunlit slabs between the pool and the camera of p21; joints at 45 deg (the pool's axes)
    dict(name='flagstone', mats=['bluestone'], ppm=96, delight=1.6, contrast=1.6, sat=1.3, albedo=(0.5, 0.48, 0.44),
         diag=True, expect='bluestone',
         pieces=[dict(photo='p21', px=(700, 1300), off=(-0.45, 0.56), size=(2.6, 3.5), rot=45)]),
    # pool coping: the pale stones of the near pool edge in p21 (u along the edge)
    dict(name='coping', mats=['coping'], ppm=128, delight=0.8, contrast=0.8, albedo=(0.58, 0.57, 0.55),
         pieces=[dict(photo='p21', px=(700, 1300), off=(1.88, -1.227), size=(1.6, 0.26), rot=135)]),
    # roof: a south-facing plane of the entry wing in the aerial, between the vents.  The courses are 4 px apart in
    # the source: their contrast is kept low (it turned into bands and combs at a distance)
    dict(name='shingle', mats=['roof_shingle', 'ridge_cap'], ppm=80, delight=0.7, contrast=0.55, clip=(0.6, 1.5),
         albedo=(0.21, 0.23, 0.26), expect='roof_shingle',
         pieces=[dict(photo='p29', px=(1240, 1160), off=(-1.25, -0.875), size=(3.0, 4.0))]),
    # cedar siding: the rear wall beside the balcony in p21 (in shade there: the shadow lines under the courses are
    # the photograph's, kept at half strength)
    dict(name='siding', mats=['siding_shingle'], ppm=110, delight=0.25, contrast=0.5, clip=(0.6, 1.5),
         albedo=(0.25, 0.265, 0.29), expect='siding_shingle',
         pieces=[dict(photo='p21', px=(1580, 760), off=(-0.24, -0.445), size=(2.2, 1.72))]),
    # driveway pavers: the sunlit field in front of the garage (aerial), clear of the bare trees' shadows
    dict(name='pavers', mats=['paver_drive'], ppm=64, delight=1.0, contrast=1.25, albedo=(0.43, 0.36, 0.295),
         expect='paver_drive',
         pieces=[dict(photo='p29', px=(250, 895), off=(0.0, 0.0), size=(3.2, 4.0))]),
    # grass: the pattern from the winter aerial, the colour nearer the spring photographs (p18, hero)
    dict(name='lawn', mats=['lawn'], ppm=48, delight=0.8, contrast=1.5, albedo=(0.15, 0.185, 0.035),
         expect='lawn', pieces=[dict(photo='p29', px=(400, 1440), off=(1.04, 1.67), size=(4.6, 3.8))]),
    dict(name='turf', mats=['turf_synthetic'], ppm=48, delight=0.8, contrast=1.5, albedo=(0.2, 0.235, 0.03),
         expect='turf_synthetic', pieces=[dict(photo='p29', px=(1900, 1400), off=(0.25, -1.2), size=(2.5, 4.6))]),
    dict(name='mulch', mats=['mulch'], ppm=64, delight=0.5, contrast=1.2, albedo=(0.26, 0.105, 0.048),
         expect='mulch', pieces=[dict(photo='p29', px=(1400, 1480), off=(1.47, -1.69), size=(1.8, 2.0))]),
    dict(name='chips', mats=['wood_chips'], ppm=48, delight=0.8, contrast=1.5, albedo=(0.66, 0.5, 0.27),
         expect='gravel_path', pieces=[dict(photo='p29', px=(1810, 800), off=(1.48, -0.06), size=(2.3, 5.4))]),
    dict(name='gravel', mats=['gravel_path'], ppm=64, delight=0.5, contrast=1.3, albedo=(0.36, 0.41, 0.42),
         expect='gravel_path', pieces=[dict(photo='p29', px=(1810, 800), off=(-0.55, -1.0), size=(0.8, 3.4))]),
    # the vegetable garden's crushed stone: the aisle between the upper beds (the whole garden lies in shade in the
    # aerial: the blue of the sky light is not the stone's colour)
    dict(name='crushed', mats=['crushed_stone'], ppm=64, delight=0.4, contrast=1.0, sat=0.3, clip=(0.6, 1.6),
         albedo=(0.15, 0.17, 0.185), expect='crushed_stone',
         pieces=[dict(photo='p29', px=(2109, 232), off=(0.0, 0.0), size=(1.45, 3.9))]),
    # the orchard's bare soil with leaf litter (aerial, between the trees' shadows)
    dict(name='litter', mats=['leaf_litter', 'orchard_soil'], ppm=48, delight=0.7, contrast=1.2,
         albedo=(0.23, 0.175, 0.10), expect='orchard_soil',
         pieces=[dict(photo='p29', px=(2220, 1060), off=(-0.45, 0.5), size=(2.0, 2.0))]),
    # the retaining walls' grey split-face block: the wall along the synthetic lawn in p18 (in deep shade there)
    dict(name='wallblock', mats=['fieldstone'], ppm=96, delight=0.5, contrast=0.35, sat=0.15, blur=1.6, clip=(0.5, 1.7),
         albedo=(0.075, 0.073, 0.068), expect='fieldstone',
         pieces=[dict(photo='p18', px=(1950, 1020), off=(0.0, 0.05), size=(4.0, 0.72))]),
    # fieldstone: the fireplace's side face in the (unregistered) close-up p24: two rectangles of that face, 346 px/m
    # at its front corner, the body 1.25 m deep
    dict(name='fieldstone', mats=['yard_fieldstone', 'stone_veneer'], ppm=160, delight=0.6,
         contrast=0.8, clip=(0.3, 2.0), albedo=(0.235, 0.19, 0.14),
         pieces=[dict(photo='p24', quad=[(1787.5, 431), (2212.5, 452.5), (2212.5, 775), (1787.5, 762.5)], size=(1.15, 0.766)),
                 dict(photo='p24', quad=[(1787.5, 769), (2069, 777.5), (2069, 1100), (1787.5, 1099)], size=(0.76, 0.766))]),
]


def make(cams, parts=None, debug=None):
    """Cut every swatch: returns {material: {image, size}}.  debug: a folder that also receives the raw patches."""
    from PIL import Image
    scene = Scene(parts) if parts is not None else Scene.cached()
    srcs, out = {}, {}

    def photo(k):
        if k not in srcs:
            p = os.path.join(HERE, 'refs', 'cache', PHOTOS[k])
            srcs[k] = np.asarray(Image.open(p).convert('RGB')) if os.path.exists(p) else None
        return srcs[k]

    for S in SWATCHES:
        ppm, strips = S['ppm'], []
        for pc in S['pieces']:
            src = photo(pc['photo'])
            if src is None:
                break
            w, h = pc['size']
            if 'quad' in pc:
                a = quad_rectify(src, pc['quad'], w, h, ppm)
            else:
                cam = cams.get(PHOTOS[pc['photo']])
                hit = scene.cast(cam, pc['px']) if cam is not None else None
                if hit is None or (S.get('expect') and hit['mat'] != S['expect']):
                    print('swatch %s: the pixel %s of %s shows %s' % (S['name'], pc['px'], pc['photo'], hit and hit['mat']))
                    break
                o, eu, ev = rect_axes(hit, 1.0, 1.0, pc.get('rot', 0.0))
                c = np.asarray(hit['p'], float) + pc['off'][0] * eu + pc['off'][1] * ev
                a = rectify(src, cam, c - eu * w / 2 - ev * h / 2, eu, ev, w, h, ppm)
            if debug:
                Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(
                    os.path.join(debug, 'raw_%s_%d.jpg' % (S['name'], len(strips))), quality=92)
            if S.get('blur'):                      # a very dark source: its 8-bit steps and chroma noise
                import cv2
                a = cv2.GaussianBlur(a, (0, 0), S['blur'])
            a = delight(a, S['delight'] * ppm)
            strips.append(a / a.reshape(-1, 3).mean(0) * 128.0)
        else:
            a = strips[0]
            for b in strips[1:]:
                hh = min(a.shape[0], b.shape[0])
                a = join(a[:hh], b[:hh], max(8, int(0.1 * ppm)))
            H, W = a.shape[:2]
            fo = S.get('overlap', 0.16)
            t = wrap(a, max(6, int(0.5 * fo * W)), max(8, int(fo * W)))
            if S.get('diag'):                       # square: the second period forced to the first
                P = t.shape[1]
                if H - P < 6:
                    print('swatch %s: too short for a square tile' % S['name'])
                    continue
                t = wrap(np.transpose(t[:min(H, int(P * 1.25))], (1, 0, 2)), 0, 0, period=P).transpose(1, 0, 2)
                t = diag_tile(t)
            else:
                t = wrap(np.transpose(t, (1, 0, 2)), max(6, int(0.5 * fo * H)), max(8, int(fo * H))).transpose(1, 0, 2)
            img = finish(t, S['albedo'], S.get('contrast', 1.0), S.get('sat', 1.0), S.get('clip'))
            name = 'swatch_%s.jpg' % S['name']
            Image.fromarray(img).save(os.path.join(HERE, 'out', name), quality=90)
            size = [round(img.shape[1] / ppm, 4), round(img.shape[0] / ppm, 4)]
            for m in S['mats']:
                out[m] = dict(image=name, size=size)
            print('swatch %-11s %4d x %4d px  %.2f x %.2f m  -> %s' % (S['name'], img.shape[1], img.shape[0], size[0], size[1], ', '.join(S['mats'])))
    return out
