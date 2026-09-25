"""
loftkit.glb -- minimal glTF 2.0 binary writer with KHR_mesh_quantization.

Model axes (x aft, y starboard, z up) are converted to glTF / three.js axes:
    X = y (starboard), Y = z (up), Z = x (aft)
This is a cyclic permutation (a proper rotation) so triangle winding is kept.
"""
from __future__ import annotations
import json
import struct
import numpy as np

from .mesh import Mesh

FLOAT, BYTE, UBYTE, SHORT, USHORT, UINT = 5126, 5120, 5121, 5122, 5123, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


def to_gl(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 1], p[..., 2], p[..., 0]], -1)


def quat_to_gl(q_model):
    """Quaternion (x,y,z,w) expressed in model axes -> glTF axes."""
    x, y, z, w = q_model
    return [float(y), float(z), float(x), float(w)]


class GLBBuilder:
    def __init__(self, quantize=True):
        self.bin = bytearray()
        self.bufferViews, self.accessors = [], []
        self.meshes, self.materials, self.nodes = [], [], []
        self.mat_index = {}
        self.quantize = quantize
        self.stats = {"vertices": 0, "triangles": 0}

    # ------------------------------------------------------------- buffers
    def _align(self, n=4):
        while len(self.bin) % n:
            self.bin.append(0)

    def _view(self, data: bytes, target=None, stride=None):
        self._align(4)
        off = len(self.bin)
        self.bin += data
        bv = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            bv["target"] = target
        if stride:
            bv["byteStride"] = stride
        self.bufferViews.append(bv)
        return len(self.bufferViews) - 1

    def _accessor(self, view, ctype, count, typ, normalized=False, mn=None, mx=None):
        acc = {"bufferView": view, "componentType": ctype, "count": int(count), "type": typ}
        if normalized:
            acc["normalized"] = True
        if mn is not None:
            acc["min"] = [float(v) if ctype == FLOAT else int(v) for v in mn]
            acc["max"] = [float(v) if ctype == FLOAT else int(v) for v in mx]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    # ------------------------------------------------------------ materials
    def material(self, name, color, metallic=0.0, roughness=0.5, emissive=None,
                 double_sided=False, alpha=None, extras=None):
        if name in self.mat_index:
            return self.mat_index[name]
        c = list(color) + ([1.0] if len(color) == 3 else [])
        m = {"name": name,
             "pbrMetallicRoughness": {"baseColorFactor": [float(v) for v in c],
                                      "metallicFactor": float(metallic),
                                      "roughnessFactor": float(roughness)}}
        if emissive is not None:
            m["emissiveFactor"] = [float(v) for v in emissive]
        if double_sided:
            m["doubleSided"] = True
        if alpha is not None or c[3] < 1.0:
            m["alphaMode"] = "BLEND"
        if extras:
            m["extras"] = extras
        self.materials.append(m)
        self.mat_index[name] = len(self.materials) - 1
        return self.mat_index[name]

    # ---------------------------------------------------------------- meshes
    def mesh(self, name, mesh: Mesh, material: int, origin=(0, 0, 0)):
        """Add a mesh.  `origin` (model coords) is subtracted so the geometry is
        local to its parent node (used for hinge / pivot nodes).
        Returns (mesh_index, dequantisation translation, scale) in glTF axes."""
        V = to_gl(mesh.V - np.asarray(origin, float))
        N = to_gl(mesh.N)
        bad = ~np.isfinite(N).all(1)
        if bad.any():
            print(f"  [glb] {name}: {bad.sum()} non-finite normals repaired")
            N[bad] = [0.0, 1.0, 0.0]
        if not np.isfinite(V).all():
            raise ValueError(f"non-finite vertices in {name}")
        F = mesh.F.astype(np.int64)
        nv = len(V)
        if self.quantize:
            lo, hi = V.min(0), V.max(0)
            c = 0.5 * (lo + hi)
            h = np.maximum(0.5 * (hi - lo), 0.02)
            q = np.round((V - c) / h * 32767.0).clip(-32767, 32767).astype(np.int16)
            Q = q[F].astype(np.int64)
            e = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0])
        else:
            e = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]) * 1e6
        # drop zero-area triangles (a trim through existing vertices leaves slivers of zero area; Blender's custom
        # split normals go wrong on them -- specks in the renders); they cover no area, so nothing visible is lost
        keep = np.any(e != 0, axis=1)
        if keep.any():
            F = F[keep]
        self.stats["vertices"] += nv
        self.stats["triangles"] += len(F)
        attrs = {}
        if self.quantize:
            buf = np.zeros((nv, 4), np.int16)
            buf[:, :3] = q
            pv = self._view(buf.tobytes(), ARRAY_BUFFER, stride=8)
            attrs["POSITION"] = self._accessor(pv, SHORT, nv, "VEC3", True, q.min(0), q.max(0))
            # normals pre-multiplied by the node scale so the normal matrix undoes it
            Ns = N * h[None, :]
            Ns /= np.maximum(np.linalg.norm(Ns, axis=1, keepdims=True), 1e-12)
            nb = np.zeros((nv, 4), np.int8)
            nb[:, :3] = np.round(Ns * 127.0).clip(-127, 127).astype(np.int8)
            nvw = self._view(nb.tobytes(), ARRAY_BUFFER, stride=4)
            attrs["NORMAL"] = self._accessor(nvw, BYTE, nv, "VEC3", True)
            trs = (c, h)
        else:
            pv = self._view(V.astype(np.float32).tobytes(), ARRAY_BUFFER)
            attrs["POSITION"] = self._accessor(pv, FLOAT, nv, "VEC3", False, V.min(0), V.max(0))
            nvw = self._view(N.astype(np.float32).tobytes(), ARRAY_BUFFER)
            attrs["NORMAL"] = self._accessor(nvw, FLOAT, nv, "VEC3")
            trs = (np.zeros(3), np.ones(3))
        if nv < 65535:
            iv = self._view(F.astype(np.uint16).tobytes(), ELEMENT_ARRAY_BUFFER)
            ia = self._accessor(iv, USHORT, F.size, "SCALAR")
        else:
            iv = self._view(F.astype(np.uint32).tobytes(), ELEMENT_ARRAY_BUFFER)
            ia = self._accessor(iv, UINT, F.size, "SCALAR")
        self.meshes.append({"name": name, "primitives": [{"attributes": attrs, "indices": ia,
                                                          "material": material, "mode": 4}]})
        return len(self.meshes) - 1, trs

    # ----------------------------------------------------------------- nodes
    def node(self, name, mesh=None, translation=None, rotation=None, scale=None,
             children=None, extras=None):
        n = {"name": name}
        if mesh is not None:
            n["mesh"] = mesh
        if translation is not None:
            n["translation"] = [float(v) for v in translation]
        if rotation is not None:
            n["rotation"] = [float(v) for v in rotation]
        if scale is not None:
            n["scale"] = [float(v) for v in scale]
        if children:
            n["children"] = list(children)
        if extras:
            n["extras"] = extras
        self.nodes.append(n)
        return len(self.nodes) - 1

    def mesh_node(self, name, mesh: Mesh, material: int, origin=(0, 0, 0), extras=None):
        """Convenience: mesh + node carrying the dequantisation transform."""
        mi, (c, h) = self.mesh(name, mesh, material, origin)
        return self.node(name + ":geo", mesh=mi, translation=c, scale=h, extras=extras)

    # ------------------------------------------------------------------ write
    def write(self, path, roots, asset_extras=None):
        gltf = {
            "asset": {"version": "2.0", "generator": "loftkit (PC-12 build)"},
            "scene": 0,
            "scenes": [{"nodes": list(roots)}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "accessors": self.accessors,
            "bufferViews": self.bufferViews,
            "buffers": [{"byteLength": len(self.bin)}],
        }
        if self.quantize:
            gltf["extensionsUsed"] = ["KHR_mesh_quantization"]
            gltf["extensionsRequired"] = ["KHR_mesh_quantization"]
        if asset_extras:
            gltf["asset"]["extras"] = asset_extras
        js = json.dumps(gltf, separators=(",", ":")).encode("utf8")
        while len(js) % 4:
            js += b" "
        self._align(4)
        binb = bytes(self.bin)
        total = 12 + 8 + len(js) + 8 + len(binb)
        with open(path, "wb") as f:
            f.write(struct.pack("<4sII", b"glTF", 2, total))
            f.write(struct.pack("<I4s", len(js), b"JSON"))
            f.write(js)
            f.write(struct.pack("<I4s", len(binb), b"BIN\x00"))
            f.write(binb)
        return total
