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
Albedos: measured against the viewer's light through the registered cameras -- the flagstone (0.50) matches p21 / p22 /
p26 / the hero; the ground materials by their ratio to the flagstone in the same image (the spring video's top-down
frames, the aerial -- exposed ~1.8x brighter than the viewer's light and in winter: its lawn and chips are not the
spring photographs' colours, which win), the walls / siding / lawn by boxes in the front photographs.  The patches are
~1 cm a pixel or coarser: the looks draw the near detail and take the patch's mean (house2.js swatchFade), so a patch's
job is its tone everywhere and its pattern beyond 10-25 m.
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


def vjoin(A, B, ov):
    """A above B, sharing ov rows cut along their best seam."""
    T = (1, 0, 2)
    return np.transpose(join(np.transpose(A, T), np.transpose(B, T), ov), T)


def _cut(e):
    """The minimum-error top-to-bottom path through an error strip e (h, ov): a soft mask, 1 left of the path."""
    h, ov = e.shape
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
    return (np.arange(ov)[None, :] < path[:, None]).astype(float)


def quilt(src, W, H, B, ov, seed=1, aug=False, cands=1500, best=6):
    """Image quilting (Efros & Freeman): a W x H texture laid from B x B blocks of the source(s), each block chosen at
    random among the `best` that continue their neighbours (overlap ov) and cut in along the minimum-error seam.  A
    larger texture than the photo gives: the tile's period grows, so a distinct stone or leaf no longer marks a lattice.
    src: one array or a list; aug: also the sources turned 90 / 180 / 270 deg and mirrored (patterns without a grain)."""
    import cv2
    rng = np.random.default_rng(seed)
    S = list(src) if isinstance(src, (list, tuple)) else [src]
    if aug:
        S = [np.rot90(a, k) for a in S for k in range(4)] + [np.rot90(a[:, ::-1], k) for a in S for k in range(4)]
    S = [np.ascontiguousarray(a, np.float32) for a in S if a.shape[0] > B and a.shape[1] > B]
    step = B - ov
    nx, ny = int(np.ceil((W - ov) / step)), int(np.ceil((H - ov) / step))
    out = np.zeros((ny * step + ov, nx * step + ov, 3), np.float32)
    for by in range(ny):
        for bx in range(nx):
            y0, x0 = by * step, bx * step
            si = rng.integers(len(S), size=cands)
            err = np.zeros(cands)
            blocks = []
            for j in range(cands):
                a = S[si[j]]
                yy, xx = rng.integers(a.shape[0] - B), rng.integers(a.shape[1] - B)
                blk = a[yy:yy + B, xx:xx + B]
                if bx:
                    err[j] += ((blk[:, :ov] - out[y0:y0 + B, x0:x0 + ov]) ** 2).sum()
                if by:
                    err[j] += ((blk[:ov, :] - out[y0:y0 + ov, x0:x0 + B]) ** 2).sum()
                blocks.append(blk)
            blk = blocks[int(rng.choice(np.argsort(err)[:best]))]
            m = np.ones((B, B))
            if bx:
                m[:, :ov] = np.minimum(m[:, :ov], 1 - _cut(((blk[:, :ov] - out[y0:y0 + B, x0:x0 + ov]) ** 2).sum(-1)))
            if by:
                m[:ov, :] = np.minimum(m[:ov, :], (1 - _cut(((blk[:ov, :] - out[y0:y0 + ov, x0:x0 + B]) ** 2).sum(-1).T)).T)
            if bx or by:
                m = cv2.GaussianBlur(m, (0, 0), 1.0)
            out[y0:y0 + B, x0:x0 + B] = blk * m[..., None] + out[y0:y0 + B, x0:x0 + B] * (1 - m[..., None])
    return out[:H, :W].astype(float)


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


def finish(a, mean_linear, contrast=1.0, sat=1.0, clip=None, chroma=None):
    """Give the patch the wanted mean colour (linear albedo), keeping its pattern (contrast: its strength, sat: the
    strength of its colour differences alone; clip (lo, hi): the brightness relative to the mean is bent softly into
    that range -- glints, pale lichen, deep joints; chroma: the colour differences (relative to the mean colour) bent
    softly under that size, so one vivid stone does not mark the tile's period); returns 8-bit sRGB."""
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
    if chroma:
        r = lin / m
        g = r.mean(-1, keepdims=True)
        c = r / np.maximum(g, 1e-4) - 1
        n = np.maximum(np.sqrt((c ** 2).sum(-1, keepdims=True)), 1e-6)
        c = c * chroma * np.tanh(n / chroma) / n
        lin = np.maximum(g * (1 + c), 0.002) * m
        lin = lin / lin.reshape(-1, 3).mean(0) * m
    lin = np.asarray(mean_linear, float) * (1 + contrast * (lin / m - 1))
    return (np.clip(lin, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)


def quad_rectify(src, quad, w_m, h_m, ppm):
    """A flat rectangle w_m x h_m seen in an unregistered photograph: its corners (TL, TR, BR, BL pixels) -> patch."""
    import cv2
    W, H = int(round(w_m * ppm)), int(round(h_m * ppm))
    M = cv2.getPerspectiveTransform(np.float32(quad), np.float32([[0, 0], [W, 0], [W, H], [0, H]]))
    return cv2.warpPerspective(src, M, (W, H), flags=cv2.INTER_CUBIC).astype(float)


# p24 (unregistered close-up of the fire terrace, open shade): the fireplace body's side face from the shoulder line
# (2.45 m) down to ~0.27 m (TL, TR, BR, BL pixels), and the seat wall's front face under its cap down to the paving
FP_SIDE = [(1782, 420), (2235, 438), (2235, 1168), (1782, 1150)]
SEAT = [(1361, 1239), (1974, 1386), (1974, 1611), (1361, 1367)]

PHOTOS = dict(p18='photos/p18_150f57.jpg', p22='photos/p22_50e8b3.jpg', p26='photos/p26_cacb52.jpg', p19='photos/p19_1e145e.jpg',
              p23='photos/p23_e4717a.jpg', p20='photos/p20_f249da.jpg', p27='photos/p27_8c90d5.jpg', p29='photos/p29_ddf5dc.jpg', p28='photos/p28_7ae0dd.jpg', p21='photos/p21_160d78.jpg',
              p01='photos/p01_768294.jpg', hero='photos/hero_721b4a.jpg', p24='photos/p24_5e2477.jpg')

# name, materials that wear it, pieces (joined side by side), texels per metre, light-gradient scale (m), contrast,
# mean albedo (linear; tuned under the viewer's light through the source camera).
# blur: px, for a source in deep shade; vblur: px along v only (courses finer than the patch can carry); clip (lo, hi),
# chroma: see finish(); sat: colour differences' strength; quilt: dict(size (m), block (m), overlap (m), aug, seed) lays
# a larger texture from blocks of all the pieces (quilt()); overlap: the wrap's overlap fraction (default 0.16).
# cols: columns of pieces (each stacked top to bottom, the columns side by side) instead of pieces in one row.
# piece: photo + px (a pixel on the surface: its ray finds the plane) + off (metres along u, v from that point to the
#        patch centre) + size (w, h metres) + rot (deg, turns u / v in the plane);  or photo + quad + size;  or photo +
#        plane=dict(z, rot, u=(u0, u1), v=(v0, v1)): a level world rectangle in the frame turned by rot about +Z;
#        flip: mirrored left-right.
# expect: the material the ray must hit (a moved wall or roof is reported, the swatch skipped).
SWATCHES = [
    # terrace flagstone, laid square to the pool: the looks lane samples it in plan turned by worldUV 0.80 rad (45.84 deg),
    # so the tile is cut in that frame (u' along the pool's width, v' along its length; plane pieces in metres there).
    # Three sunlit fields of the ground photos (64-300 px/m): p21's west terrace, p22's near band, p26's pool end.  The
    # slabs' own colours (rust, blue-grey, buff) kept: from the drone and across the terrace they are the pattern; the
    # most vivid rust slabs bent back (chroma) so they do not mark the 4 m period.  The front walks' names wear it too
    # r3: p21's field alone, as itself and turned 180 deg: a 4.9 x 6.2 m tile of crisp slabs and light joints (the
    # aerial's look).  The r2 tile (3.9 x 4.5 m) drew a lattice of one rust slab from the drone; p22's / p26's fields
    # are soft at this scale (no joints), so beside p21's they drew sharp / soft bands, and a quilt of 1.1 m blocks
    # broke the slabs into a blur.  More of the slabs' own contrast (the aerial: sd 41 against the render's 27; p26's
    # rust and blue-grey slabs), the most vivid rust bent back (chroma)
    dict(name='flagstone', mats=['bluestone', 'bluestone_walk', 'flagstone_walk', 'walk_flagstone'], ppm=64,
         delight=1.2, contrast=1.45, sat=1.3, clip=(0.5, 1.5), chroma=0.24,
         albedo=(0.5, 0.48, 0.44), expect='bluestone',
         cols=[[dict(photo='p21', plane=dict(z=0.0, rot=45.84, u=(-6.2, -3.75), v=(-6.2, 0.0)))],
               [dict(photo='p21', plane=dict(z=0.0, rot=45.84, u=(-6.2, -3.75), v=(-6.2, 0.0)), turn=2)]]),
    # pool coping: the pale stones of the near pool edge in p21 (u along the edge); near-white and neutral there (211
    # 212 213 against the render's 192 189 187)
    dict(name='coping', mats=['coping'], ppm=128, delight=0.8, contrast=0.8, albedo=(0.66, 0.655, 0.645),
         pieces=[dict(photo='p21', px=(700, 1300), off=(1.88, -1.227), size=(1.6, 0.26), rot=135)]),
    # roof: a south-facing plane of the entry wing in the aerial, between the vents.  The courses are 4 px apart in
    # the source and turned into bands and combs at a distance: they are blurred away along the slope (vblur), the
    # patch keeps the weathering's mottle; the drawn shingles of the looks carry the courses up close
    dict(name='shingle', mats=['roof_shingle', 'ridge_cap'], ppm=80, delight=0.5, contrast=0.8, clip=(0.65, 1.4),
         vblur=4.0,
         albedo=(0.24, 0.257, 0.28), expect='roof_shingle',
         pieces=[dict(photo='p29', px=(1240, 1160), off=(-1.25, -0.875), size=(3.0, 4.0))]),
    # cedar siding: the rear wall beside the balcony in p21 (in shade there: the shadow lines under the courses are
    # the photograph's, kept at half strength).  Its tone: the front's blue-grey (hero / p01: B / R ~1.3 in sRGB on the
    # upper storey, 88-97 102-111 121-128 in p01; p21's rear wall ~1.15).  The lower storey's names (should the house
    # zone give the porch walls one) wear the same patch: the looks tint them taupe (house2.js heightTint / taupe)
    dict(name='siding', mats=['siding_shingle', 'siding_lap', 'siding_taupe', 'siding_lap_taupe',
                              'siding_shingle_taupe'], ppm=110, delight=0.25, contrast=0.45, clip=(0.6, 1.5),
         albedo=(0.195, 0.222, 0.285), expect='siding_shingle',
         pieces=[dict(photo='p21', px=(1580, 760), off=(-0.24, -0.445), size=(2.2, 1.72))]),
    # driveway pavers: the sunlit field in front of the garage (aerial), clear of the bare trees' shadows
    dict(name='pavers', mats=['paver_drive'], ppm=64, delight=1.0, contrast=1.25, albedo=(0.43, 0.36, 0.295),
         expect='paver_drive',
         pieces=[dict(photo='p29', px=(250, 895), off=(0.0, 0.0), size=(3.2, 4.0))]),
    # grass: the pattern from the winter aerial, the colour of the spring photographs (p01's and the hero's sunlit front
    # lawn, p18's turf: yellow-green, little blue)
    # r3: +25 % (p01's sunlit lawn 144 167 77 against the render's 127 150 77 at the same flagstone; the hero alike)
    dict(name='lawn', mats=['lawn'], ppm=48, delight=0.6, contrast=1.15, clip=(0.7, 1.35), albedo=(0.205, 0.325, 0.072),
         expect='lawn', pieces=[dict(photo='p29', px=(400, 1440), off=(1.04, 1.67), size=(4.6, 3.8))]),
    # synthetic turf: p18's sunlit field 148 149 50 against the render's 127 136 60 -- yellower and brighter
    dict(name='turf', mats=['turf_synthetic'], ppm=48, delight=0.8, contrast=1.2, albedo=(0.21, 0.225, 0.028),
         expect='turf_synthetic', pieces=[dict(photo='p29', px=(1900, 1400), off=(0.25, -1.2), size=(2.5, 4.6))]),
    # bark mulch: sunlit beds read (140-157, 98-108, 75-81) in the hero / p27: orange-brown, not chocolate
    dict(name='mulch', mats=['mulch'], ppm=64, delight=0.5, contrast=1.2, albedo=(0.28, 0.13, 0.07),
         expect='mulch', pieces=[dict(photo='p29', px=(1400, 1480), off=(1.47, -1.69), size=(1.8, 2.0))]),
    # wood chips: the play yard in p19 at 160-330 px/m (two sunlit fields between the swing frame's legs and chains),
    # laid out larger by quilting (chips have no grain); golden tan: the spring video's top-down (frame 139.9 s, against
    # its flagstone) gives 0.52 0.35 0.25, the winter aerial a deeper orange
    dict(name='chips', mats=['wood_chips'], ppm=64, delight=0.4, contrast=1.1, sat=1.1, clip=(0.7, 1.5),
         albedo=(0.60, 0.42, 0.24), expect='wood_chips',
         quilt=dict(size=(4.0, 4.0), block=0.7, overlap=0.18, aug=True, seed=3),
         cols=[[dict(photo='p19', plane=dict(z=1.88, u=(14.95, 16.25), v=(-5.6, -2.35)))],
               [dict(photo='p19', plane=dict(z=1.88, u=(13.05, 13.7), v=(-6.5, -1.9)))]]),
    # the path round the play yard: grey crushed rock (p19: neutral grey in sun, blue only in the shade)
    # r3: p19's sunlit path 168 175 172 against the chips 228 193 147 -- 20 % lighter than r2, neutral
    dict(name='gravel', mats=['gravel_path'], ppm=64, delight=0.5, contrast=1.2, sat=0.4, albedo=(0.32, 0.325, 0.315),
         expect='gravel_path', pieces=[dict(photo='p29', px=(1810, 800), off=(-0.55, -1.0), size=(0.8, 3.4))]),
    # the vegetable garden's crushed stone: the two aisles between the beds (the whole garden lies in shade in the
    # aerial: the blue of the sky light is not the stone's colour; the fence's light streaks near its north side are
    # left out), quilted to a 3 m tile
    dict(name='crushed', mats=['crushed_stone'], ppm=64, delight=0.4, contrast=1.0, sat=0.25, clip=(0.6, 1.5),
         albedo=(0.17, 0.16, 0.145), expect='crushed_stone',
         quilt=dict(size=(3.0, 3.0), block=0.5, overlap=0.14, aug=True, seed=5),
         pieces=[dict(photo='p29', px=(2245, 287), off=(-1.2, 0.0), size=(2.0, 1.3)),
                 dict(photo='p29', px=(2109, 232), off=(0.0, -0.6), size=(1.2, 2.4))]),
    # the raised beds' soil (aerial: the south-west bed, which has no plant in it)
    dict(name='soil', mats=['yard_soil', 'soil'], ppm=64, delight=0.5, contrast=1.0, sat=0.6, clip=(0.5, 1.6),
         albedo=(0.085, 0.064, 0.047), expect='yard_soil',
         quilt=dict(size=(2.0, 2.0), block=0.45, overlap=0.12, aug=True, seed=7),
         pieces=[dict(photo='p29', px=(2043, 352), off=(0.0, 0.0), size=(1.5, 1.5))]),
    # the orchard's bare soil with leaf litter (aerial, between the trees' shadows: what is left of them clipped),
    # quilted to a 4 m tile (the 1.7 m one drew a lattice of the same dark marks); greyer than the aerial's winter
    # tone (p18's sunlit bank 130 111 105; the spring video 132 120 109 beside its turf)
    dict(name='litter', mats=['leaf_litter', 'orchard_soil'], ppm=48, delight=0.7, contrast=1.2,
         albedo=(0.25, 0.205, 0.14), expect='orchard_soil', clip=(0.65, 1.5),
         quilt=dict(size=(4.0, 4.0), block=0.8, overlap=0.2, aug=True, seed=17),
         pieces=[dict(photo='p29', px=(2220, 1060), off=(-0.45, 0.5), size=(2.0, 2.0)),
                 dict(photo='p29', px=(2215, 1175), off=(0.0, 0.0), size=(1.8, 1.0))]),
    # the retaining walls' grey split-face block: the wall behind the fire terrace in the (unregistered) close-up p24,
    # in open shade, ~170 px/m (a 6 in course = 26 px); mirrored to a longer piece.  Warm grey in the sun (p22: 122
    # 110 96), neutral in the shade (p24: 91 91 95)
    # (a little darker and warmer than r2: p22 / p26 / f143.6 read the walls darker than the render everywhere, partly
    # the hedges' shade the model does not cast).  The walls the ground lane names 'fieldstone' are grey block unless
    # the build also has 'wall_block' -- then 'fieldstone' is the real stacked stone (p22: the low terrace wall and the
    # stair cheeks are the fireplace's stone, only the upper tiers are block) and wears the stone patch below
    dict(name='wallblock', mats=['fieldstone', 'wall_block'], unless=dict(fieldstone='wall_block'), ppm=128,
         delight=0.45, contrast=0.85, sat=0.5, clip=(0.45, 1.6), albedo=(0.155, 0.14, 0.117), overlap=0.12,
         pieces=[dict(photo='p24', quad=[(0, 748), (245, 748), (245, 875), (0, 875)], size=(1.43, 0.74)),
                 dict(photo='p24', quad=[(0, 748), (245, 748), (245, 875), (0, 875)], size=(1.43, 0.74), flip=True)]),
    # fieldstone: the fireplace and its seat walls in the (unregistered) close-up p24, in open shade: the body's side
    # face (near-frontal, 1.25 m deep: 360 px/m across, 335 down; the shoulder line = 2.45 m) above the flowering
    # quince and left of it, and the seat wall's front face (0.46 m under its cap; ~3 m of it, seen obliquely: its
    # length set so the stones keep the side face's proportions).  Laid as three columns of whole stones -- the r2
    # quilt of 0.38 m blocks cut stones into smears ("camouflage").  Rust, buff, cream and slate stones in dark
    # joints; the mean: p21's shaded corner 140 114 89 (the r3 render 136 117 104: warmer, same level), p26's sunlit
    # side face tan; the hedge-shaded p22 front reads darker (the oak's shade, not the stone)
    dict(name='fieldstone', mats=['yard_fieldstone'], when=dict(fieldstone='wall_block'), ppm=160, delight=0.5,
         contrast=0.9, sat=1.0, clip=(0.4, 1.6), albedo=(0.235, 0.172, 0.12), overlap=0.1,
         cols=[[dict(photo='p24', quad=FP_SIDE, size=(1.25, 2.18), crop=(0.0, 1.25, 0.0, 0.82)),
                dict(photo='p24', quad=SEAT, size=(3.0, 0.46), crop=(0.35, 1.6, 0.0, 0.46))],
               [dict(photo='p24', quad=FP_SIDE, size=(1.25, 2.18), crop=(0.0, 0.74, 0.82, 2.10))],
               [dict(photo='p24', quad=SEAT, size=(3.0, 0.46), crop=(1.6, 2.85, 0.0, 0.46), flip=True),
                dict(photo='p24', quad=FP_SIDE, size=(1.25, 2.18), crop=(0.0, 1.25, 0.0, 0.82), flip=True)]]),
    # the piers, the chimneys and the house's stone base: the same quarry mix (hero / p01: warm brown-grey in the
    # porch's shade, muted), a shade darker and less colourful than the fireplace
    dict(name='veneer', mats=['stone_veneer'], ppm=160, delight=0.5, contrast=0.8, sat=0.8, clip=(0.45, 1.5),
         albedo=(0.20, 0.162, 0.122), overlap=0.1,
         cols=[[dict(photo='p24', quad=SEAT, size=(3.0, 0.46), crop=(1.6, 2.85, 0.0, 0.46)),
                dict(photo='p24', quad=FP_SIDE, size=(1.25, 2.18), crop=(0.0, 1.25, 0.0, 0.82), flip=True)],
               [dict(photo='p24', quad=FP_SIDE, size=(1.25, 2.18), crop=(0.0, 0.74, 0.82, 2.10), flip=True)],
               [dict(photo='p24', quad=FP_SIDE, size=(1.25, 2.18), crop=(0.0, 1.25, 0.0, 0.82)),
                dict(photo='p24', quad=SEAT, size=(3.0, 0.46), crop=(0.35, 1.6, 0.0, 0.46), flip=True)]]),
]


def make(cams, parts=None, debug=None, prefix='swatch_', only=None):
    """Cut every swatch: returns {material: {image, size}}.  debug: a folder that also receives the raw patches;
    prefix: the files' name prefix in out/ (a scratch run writes its own, the shared files stay as built);
    only: the names of the swatches to cut (all by default)."""
    from PIL import Image
    import cv2
    scene = Scene(parts) if parts is not None else Scene.cached()
    used = set(scene.mats)                    # the material names of this build (`when` / `unless` below)
    srcs, out = {}, {}

    def photo(k):
        if k not in srcs:
            p = os.path.join(HERE, 'refs', 'cache', PHOTOS[k])
            srcs[k] = np.asarray(Image.open(p).convert('RGB')) if os.path.exists(p) else None
        return srcs[k]

    def piece(S, pc, n):
        """One rectified, evened-out piece (mean 128), or None (photo missing, the surface not where it should be)."""
        ppm, src = S['ppm'], photo(pc['photo'])
        if src is None:
            return None
        cam = cams.get(PHOTOS[pc['photo']])
        if 'quad' in pc:
            w, h = pc['size']
            a = quad_rectify(src, pc['quad'], w, h, ppm)
        elif 'plane' in pc:                     # a level rectangle in the frame turned by rot (deg) about +Z
            P = pc['plane']
            r = np.radians(P.get('rot', 0.0))
            eu, ev = np.array([np.cos(r), np.sin(r), 0.0]), np.array([-np.sin(r), np.cos(r), 0.0])
            (u0, u1), (v0, v1) = P['u'], P['v']
            o = u0 * eu + v0 * ev + [0.0, 0.0, P['z']]
            c = o + eu * (u1 - u0) / 2 + ev * (v1 - v0) / 2
            hit = scene.ray(cam['C'], c - np.asarray(cam['C'], float)) if cam is not None else None
            if hit is None or (S.get('expect') and hit['mat'] != S['expect']) or abs(hit['p'][2] - P['z']) > 0.15:
                print('swatch %s: the plane piece %d of %s shows %s' % (S['name'], n, pc['photo'], hit and (hit['mat'], round(float(hit['p'][2]), 2))))
                return None
            a = rectify(src, cam, o, eu, ev, u1 - u0, v1 - v0, ppm)
        else:
            w, h = pc['size']
            hit = scene.cast(cam, pc['px']) if cam is not None else None
            if hit is None or (S.get('expect') and hit['mat'] != S['expect']):
                print('swatch %s: the pixel %s of %s shows %s' % (S['name'], pc['px'], pc['photo'], hit and hit['mat']))
                return None
            o, eu, ev = rect_axes(hit, 1.0, 1.0, pc.get('rot', 0.0))
            c = np.asarray(hit['p'], float) + pc['off'][0] * eu + pc['off'][1] * ev
            a = rectify(src, cam, c - eu * w / 2 - ev * h / 2, eu, ev, w, h, ppm)
        dark = (a.max(-1) < 1).mean()
        if dark > 0.003:
            print('swatch %s: piece %d of %s is %.1f %% outside the photograph' % (S['name'], n, pc['photo'], 100 * dark))
        if pc.get('crop'):                     # (x0, x1, y0, y1) metres from the patch's top-left corner
            x0, x1, y0, y1 = pc['crop']
            a = a[int(round(y0 * ppm)):int(round(y1 * ppm)), int(round(x0 * ppm)):int(round(x1 * ppm))]
        if pc.get('turn'):
            a = np.rot90(a, pc['turn'])
        if pc.get('flip'):
            a = a[:, ::-1]
        if debug:
            Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(
                os.path.join(debug, 'raw_%s_%d.jpg' % (S['name'], n)), quality=92)
        if S.get('blur') or pc.get('blur'):    # a very dark source: its 8-bit steps; or a sharper piece among soft ones
            a = cv2.GaussianBlur(np.ascontiguousarray(a), (0, 0), pc.get('blur') or S['blur'])
        if pc.get('sharpen'):                  # a softer piece among sharper ones: unsharp mask (amount, sigma px)
            k, sg = pc['sharpen']
            a = np.ascontiguousarray(a)
            a = np.clip(a + k * (a - cv2.GaussianBlur(a, (0, 0), sg)), 0, 255)
        if S.get('vblur'):                     # courses finer than the patch can carry: blurred along v only
            a = cv2.GaussianBlur(a, (0, 0), sigmaX=0.01, sigmaY=S['vblur'])
        a = delight(np.ascontiguousarray(a), S['delight'] * ppm)
        return a / a.reshape(-1, 3).mean(0) * 128.0

    for S in SWATCHES:
        if only and S['name'] not in only:
            continue
        ppm = S['ppm']
        cols = S.get('cols') or [[pc] for pc in S['pieces']]       # columns of pieces, each stacked top to bottom
        n, ok, C = 0, True, []
        for col in cols:
            ps = []
            for pc in col:
                a = piece(S, pc, n)
                n += 1
                if a is None:
                    ok = False
                    break
                ps.append(a)
            if not ok:
                break
            C.append(ps)
        if not ok:
            continue
        ov = max(8, int(0.1 * ppm))
        if S.get('quilt'):                         # a larger texture laid from blocks of every piece
            Q = S['quilt']
            a = quilt([p for ps in C for p in ps], int(Q['size'][0] * ppm), int(Q['size'][1] * ppm), int(Q['block'] * ppm),
                      int(Q.get('overlap', 0.25 * Q['block']) * ppm), Q.get('seed', 1), Q.get('aug', False))
        else:
            cc = []
            for ps in C:
                a = ps[0]
                for b in ps[1:]:
                    ww = min(a.shape[1], b.shape[1])
                    a = vjoin(a[:, :ww], b[:, :ww], ov)
                cc.append(a)
            a = cc[0]
            for b in cc[1:]:
                hh = min(a.shape[0], b.shape[0])
                a = join(a[:hh], b[:hh], ov)
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
        img = finish(t, S['albedo'], S.get('contrast', 1.0), S.get('sat', 1.0), S.get('clip'), S.get('chroma'))
        name = '%s%s.jpg' % (prefix, S['name'])
        Image.fromarray(img).save(os.path.join(HERE, 'out', name), quality=90)
        size = [round(img.shape[1] / ppm, 4), round(img.shape[0] / ppm, 4)]
        mats = [m for m in S['mats'] if not (m in S.get('unless', {}) and S['unless'][m] in used)]
        mats += [m for m, k in S.get('when', {}).items() if k in used]
        for m in mats:
            out[m] = dict(image=name, size=size)
        print('swatch %-11s %4d x %4d px  %.2f x %.2f m  -> %s' % (S['name'], img.shape[1], img.shape[0], size[0], size[1], ', '.join(mats)))
    return out
