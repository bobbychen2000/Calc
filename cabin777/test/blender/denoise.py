"""OIDN denoise helper for render.py when this Blender's Cycles was built without OpenImageDenoise.

Runs in a normal python3 (numpy + the `oidn` wheel, e.g. `pip install --target ~/.cache/oidn-py oidn`), because the
wheel's TBB clashes with Blender's. Usage: python3 denoise.py W H color.f32 albedo.f32 normal.f32 out.f32
Inputs/outputs are raw little-endian float32 RGBA (Blender image.pixels order).
"""
import os
import sys

extra = os.environ.get('CABIN_OIDN_PATH')
if extra:
    sys.path.insert(0, extra)
import numpy as np
import oidn

w, h = int(sys.argv[1]), int(sys.argv[2])
load = lambda p: np.ascontiguousarray(np.fromfile(p, dtype=np.float32).reshape(h, w, 4)[:, :, :3])
col, alb, nrm = load(sys.argv[3]), load(sys.argv[4]), load(sys.argv[5])
out = np.zeros_like(col)
dev = oidn.NewDevice()
oidn.CommitDevice(dev)
f = oidn.NewFilter(dev, 'RT')
oidn.SetSharedFilterImage(f, 'color', col, oidn.FORMAT_FLOAT3, w, h)
oidn.SetSharedFilterImage(f, 'albedo', alb, oidn.FORMAT_FLOAT3, w, h)
oidn.SetSharedFilterImage(f, 'normal', nrm, oidn.FORMAT_FLOAT3, w, h)
oidn.SetSharedFilterImage(f, 'output', out, oidn.FORMAT_FLOAT3, w, h)
# the wheel does not wrap oidnSetFilter1b: HDR mode (emissive strips exceed 1.0) through its ctypes handle
import ctypes, glob as _g
_lib = ctypes.CDLL(_g.glob(os.path.join(os.path.dirname(oidn.__file__), 'lib.linux.x64', 'libOpenImageDenoise.so*'))[0])
_lib.oidnSetFilter1b.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_bool]
_lib.oidnSetFilter1b(f, b'hdr', True)
oidn.CommitFilter(f)
oidn.ExecuteFilter(f)
err = oidn.GetDeviceError(dev)
rgba = np.concatenate([out, np.ones((h, w, 1), np.float32)], axis=2)
rgba.astype(np.float32).tofile(sys.argv[6])
print('oidn', 'ok' if not err else err)
