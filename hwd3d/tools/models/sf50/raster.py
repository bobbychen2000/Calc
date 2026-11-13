"""
Small numpy z-buffer rasteriser for model checks (no GPU, no GL): orthographic or perspective camera, deferred
Phong shading with interpolated vertex normals, one alpha-blended glass layer, depth-edge outlines.

    cam = Camera.ortho(eye_dir, up, centre, half_height, W, H)  /  Camera.persp(eye, target, up, fov_deg, W, H)
    img = render(items, cam, ...) -> (H, W, 3) float [0, 1]
    items: [(V (n,3), F (m,3), N (n,3), rgba (4,), metallic, roughness)]   (any coordinates; z up is assumed for the sky)
"""
from __future__ import annotations
import numpy as np


class Camera:
    def __init__(self, R, eye, ortho, W, H, half_h=None, fov=None):
        self.R, self.eye, self.ortho, self.W, self.H = R, np.asarray(eye, float), ortho, W, H
        self.half_h, self.fov = half_h, fov

    @staticmethod
    def _basis(fwd, up):
        f = np.asarray(fwd, float)
        f = f / np.linalg.norm(f)
        r = np.cross(f, up)
        r = r / np.linalg.norm(r)
        u = np.cross(r, f)
        return np.stack([r, u, -f])          # rows: camera x, y, z (looking down -z)

    @classmethod
    def ortho(cls, view_dir, up, centre, half_h, W, H):
        R = cls._basis(view_dir, up)
        eye = np.asarray(centre, float) - 50.0 * np.asarray(view_dir, float) / np.linalg.norm(view_dir)
        return cls(R, eye, True, W, H, half_h=half_h)

    @classmethod
    def persp(cls, eye, target, up, fov_deg, W, H):
        R = cls._basis(np.asarray(target, float) - np.asarray(eye, float), up)
        return cls(R, eye, False, W, H, fov=np.radians(fov_deg))

    def project(self, P):
        """-> (px, py, depth) with depth > 0 in front of the camera."""
        q = (np.asarray(P, float) - self.eye) @ self.R.T
        d = -q[..., 2]
        if self.ortho:
            s = self.H / (2 * self.half_h)
            px = self.W / 2 + q[..., 0] * s
            py = self.H / 2 - q[..., 1] * s
        else:
            f = self.H / (2 * np.tan(self.fov / 2))
            dd = np.maximum(d, 1e-6)
            px = self.W / 2 + q[..., 0] * f / dd
            py = self.H / 2 - q[..., 1] * f / dd
        return px, py, d

    def view_dir_at(self, P):
        if self.ortho:
            return np.broadcast_to(-self.R[2], np.shape(P))
        v = np.asarray(P, float) - self.eye
        return v / np.linalg.norm(v, axis=-1, keepdims=True)


def _raster(px, py, pd, F, W, H, chunk=3_000_000):
    """Rasterise triangles; returns per-pixel (depth, tri, b1, b2) with depth=inf where empty."""
    zb = np.full(W * H, np.inf)
    tid = np.full(W * H, -1, np.int64)
    B1 = np.zeros(W * H)
    B2 = np.zeros(W * H)
    x0, x1, x2 = px[F[:, 0]], px[F[:, 1]], px[F[:, 2]]
    y0, y1, y2 = py[F[:, 0]], py[F[:, 1]], py[F[:, 2]]
    d0, d1, d2 = pd[F[:, 0]], pd[F[:, 1]], pd[F[:, 2]]
    ok = (d0 > 0) & (d1 > 0) & (d2 > 0)
    bx0 = np.floor(np.minimum(np.minimum(x0, x1), x2)).astype(np.int64)
    bx1 = np.ceil(np.maximum(np.maximum(x0, x1), x2)).astype(np.int64)
    by0 = np.floor(np.minimum(np.minimum(y0, y1), y2)).astype(np.int64)
    by1 = np.ceil(np.maximum(np.maximum(y0, y1), y2)).astype(np.int64)
    ok &= (bx1 >= 0) & (bx0 < W) & (by1 >= 0) & (by0 < H)
    bx0, by0 = np.maximum(bx0, 0), np.maximum(by0, 0)          # clip the boxes to the screen
    bx1, by1 = np.minimum(bx1, W - 1), np.minimum(by1, H - 1)
    area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    ok &= np.abs(area) > 1e-12
    size = np.maximum(bx1 - bx0, by1 - by0) + 1
    idx_all = np.nonzero(ok)[0]
    cls_edges = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 4096]
    for lo, hi in zip([0] + cls_edges[:-1], cls_edges):
        sel = idx_all[(size[idx_all] > lo) & (size[idx_all] <= hi)]
        if len(sel) == 0:
            continue
        s = hi
        oy, ox = np.meshgrid(np.arange(s), np.arange(s), indexing="ij")
        ox, oy = ox.ravel(), oy.ravel()
        per = max(1, chunk // (s * s))
        for k in range(0, len(sel), per):
            t = sel[k:k + per]
            X = bx0[t][:, None] + ox[None, :] + 0.5
            Y = by0[t][:, None] + oy[None, :] + 0.5
            ax, ay, bxx, byy, cx, cy = x0[t][:, None], y0[t][:, None], x1[t][:, None], y1[t][:, None], x2[t][:, None], y2[t][:, None]
            A = area[t][:, None]
            w1 = ((X - ax) * (cy - ay) - (cx - ax) * (Y - ay)) / A
            w2 = ((bxx - ax) * (Y - ay) - (X - ax) * (byy - ay)) / A
            w0 = 1 - w1 - w2
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            Xi = X.astype(np.int64)
            Yi = Y.astype(np.int64)
            m &= (Xi >= 0) & (Xi < W) & (Yi >= 0) & (Yi < H)
            if not m.any():
                continue
            # perspective-correct depth: interpolate 1/d in screen space
            inv = w0 / d0[t][:, None] + w1 / d1[t][:, None] + w2 / d2[t][:, None]
            D = 1.0 / np.maximum(inv, 1e-12)
            pix = (Yi * W + Xi)[m]
            dep = D[m]
            tt = np.broadcast_to(t[:, None], m.shape)[m]
            b1 = (w1 / d1[t][:, None] * D)[m]
            b2 = (w2 / d2[t][:, None] * D)[m]
            order = np.lexsort((dep, pix))
            pix, dep, tt, b1, b2 = pix[order], dep[order], tt[order], b1[order], b2[order]
            first = np.r_[True, pix[1:] != pix[:-1]]
            pix, dep, tt, b1, b2 = pix[first], dep[first], tt[first], b1[first], b2[first]
            better = dep < zb[pix]
            pix, dep, tt, b1, b2 = pix[better], dep[better], tt[better], b1[better], b2[better]
            zb[pix] = dep
            tid[pix] = tt
            B1[pix] = b1
            B2[pix] = b2
    return zb, tid, B1, B2


def _shade(cam, V, N, F, mat_of_tri, mats, zb, tid, B1, B2, light_dir, W, H, bg):
    out = np.tile(np.asarray(bg, float), (W * H, 1))
    hit = tid >= 0
    t = tid[hit]
    b1, b2 = B1[hit], B2[hit]
    b0 = 1 - b1 - b2
    f = F[t]
    n = b0[:, None] * N[f[:, 0]] + b1[:, None] * N[f[:, 1]] + b2[:, None] * N[f[:, 2]]
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    p = b0[:, None] * V[f[:, 0]] + b1[:, None] * V[f[:, 1]] + b2[:, None] * V[f[:, 2]]
    vdir = cam.view_dir_at(p)
    if vdir.ndim == 1:
        vdir = np.broadcast_to(vdir, p.shape)
    back = np.sum(n * vdir, 1) > 0
    n[back] *= -1
    mi = mat_of_tri[t]
    base = mats[mi, :3]
    metal = mats[mi, 4]
    rough = mats[mi, 5]
    L = np.asarray(light_dir, float)
    L = L / np.linalg.norm(L)
    L2 = np.array([-L[0], -L[1] * 0.6, 0.35])
    L2 /= np.linalg.norm(L2)
    ndl = np.clip(n @ L, 0, 1)
    ndl2 = np.clip(n @ L2, 0, 1)
    sky = 0.5 + 0.5 * n[:, 2]
    amb = 0.22 * sky + 0.16
    diff = (1 - metal)[:, None] * base * (amb + 0.75 * ndl + 0.22 * ndl2)[:, None]
    h = L - vdir
    h /= np.linalg.norm(h, axis=1, keepdims=True)
    shin = 2.0 / np.maximum(rough ** 2, 0.002)
    spec = np.clip(n * h, -1, 1).sum(1)
    spec = np.clip(spec, 0, 1) ** np.minimum(shin, 2000) * (0.04 + 0.5 * (1 - rough))
    spec_col = (metal[:, None] * base + (1 - metal)[:, None] * 0.6) * spec[:, None]
    # crude environment for metals: sky above, ground below
    env = np.where(n[:, 2:3] > 0, np.array([0.45, 0.52, 0.62]), np.array([0.10, 0.09, 0.08]))
    menv = metal[:, None] * base * env * (0.55 + 0.45 * np.abs(n[:, 2:3]))
    out[hit] = np.clip(diff + spec_col + menv, 0, 1)
    return out


def render(items, cam, bg=(1, 1, 1), light_dir=(-0.45, -0.35, 0.82), outline=True, glass_items=None, ssaa=1, srgb=True):
    """Materials are linear (glTF baseColorFactor); the image is sRGB-encoded at the end."""
    W, H = cam.W * ssaa, cam.H * ssaa
    cam2 = Camera(cam.R, cam.eye, cam.ortho, W, H, cam.half_h, cam.fov)

    def gather(its):
        Vs, Ns, Fs, mt, mats = [], [], [], [], []
        off = 0
        for k, (V, F, N, rgba, met, rough) in enumerate(its):
            Vs.append(V)
            Ns.append(N)
            Fs.append(F + off)
            mt.append(np.full(len(F), k))
            rgba = list(rgba) + [1.0] * (4 - len(rgba))
            mats.append(list(rgba) + [met, rough])
            off += len(V)
        if not Vs:
            return None
        return np.vstack(Vs), np.vstack(Ns), np.vstack(Fs), np.concatenate(mt), np.array(mats)

    V, N, F, mt, mats = gather(items)
    px, py, pd = cam2.project(V)
    zb, tid, B1, B2 = _raster(px, py, pd, F, W, H)
    col = _shade(cam2, V, N, F, mt, mats, zb, tid, B1, B2, light_dir, W, H, bg)
    if glass_items:
        g = gather(glass_items)
        if g is not None:
            gV, gN, gF, gmt, gmats = g
            gx, gy, gd = cam2.project(gV)
            gz, gt, gb1, gb2 = _raster(gx, gy, gd, gF, W, H)
            vis = (gt >= 0) & (gz < zb - 1e-4)
            gc = _shade(cam2, gV, gN, gF, gmt, gmats, gz, gt, gb1, gb2, light_dir, W, H, bg)
            a = gmats[gmt[np.maximum(gt, 0)], 3]
            a = np.where(vis, a, 0.0)[:, None]
            col = col * (1 - a) + gc * a
            zb = np.where(vis, gz, zb)
    img = col.reshape(H, W, 3)
    if srgb:
        img = np.where(img <= 0.0031308, 12.92 * img, 1.055 * np.clip(img, 0, None) ** (1 / 2.4) - 0.055)
    if outline:
        z = zb.reshape(H, W)
        zf = np.where(np.isinf(z), 1e6, z)
        scale = np.nanmedian(zf[zf < 1e5]) if (zf < 1e5).any() else 1.0
        dzx = np.abs(np.diff(zf, axis=1, prepend=zf[:, :1]))
        dzy = np.abs(np.diff(zf, axis=0, prepend=zf[:1, :]))
        thr = 0.012 * scale if not cam.ortho else 0.03
        edge = (dzx > thr) | (dzy > thr)
        img[edge] *= 0.35
    if ssaa > 1:
        img = img.reshape(cam.H, ssaa, cam.W, ssaa, 3).mean((1, 3))
    return img


def items_from_parts(parts, materials, skip=(), only=None):
    """Turn {id: Part} (pc12 Part records) into raster items; glass (alpha < 1) goes to a second list."""
    opaque, glass = [], []
    for pid, p in parts.items():
        if pid in skip or (only and not any(pid.startswith(o) for o in only)):
            continue
        for m, mat in p.meshes:
            rgba, met, rough = materials[mat]
            rgba = list(rgba) + [1.0] * (4 - len(rgba))
            it = (m.V, m.F, m.N, rgba, met, rough)
            (glass if rgba[3] < 1 else opaque).append(it)
    return opaque, glass
