import sys, numpy as np, rasterio
sys.path.insert(0, '.')
from qa_img import Raster, R, S2, umbra
def tci_img(scene, x0, z0, x1, z1, res=2.0, shift_en=(0, 0)):
    xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
    X, Z = np.meshgrid(xs, zs)
    ch = [Raster(f'{R}/s2/{S2[scene]}/TCI.tif', band=b, shift_en=shift_en).sample(X, Z) for b in (1, 2, 3)]
    img = np.clip(np.dstack(ch) / 255.0 * 1.6, 0, 1)
    return np.nan_to_num(img), (x0, x1, z1, z0)
_U = {}
def umb_img(x0, z0, x1, z1, res=1.0, shift_en=(3.4, 0)):
    key = shift_en
    if key not in _U: _U[key] = umbra(shift_en)
    xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
    X, Z = np.meshgrid(xs, zs)
    a = _U[key].sample(X, Z)
    a = np.clip(a / np.nanpercentile(a, 99), 0, 1)
    return np.nan_to_num(a), (x0, x1, z1, z0)
_FR = {}
def fullres_img(sub, x0, z0, x1, z1, res=0.3, shift_en=(3.4, 0)):
    import glob
    key = (sub, shift_en)
    if key not in _FR:
        _FR[key] = [Raster(p, shift_en=shift_en) for p in sorted(glob.glob(f'{R}/imagery/{sub}/*.tif'))]
    xs = np.arange(x0, x1, res) + res / 2; zs = np.arange(z0, z1, res) + res / 2
    X, Z = np.meshgrid(xs, zs)
    out = np.full(X.shape, np.nan)
    for r in _FR[key]:
        v = r.sample(X, Z); m = np.isnan(out) & np.isfinite(v); out[m] = v[m]
    a = np.clip(out / np.nanpercentile(out, 99.5), 0, 1) if np.isfinite(out).any() else out
    return np.nan_to_num(a), (x0, x1, z1, z0)
