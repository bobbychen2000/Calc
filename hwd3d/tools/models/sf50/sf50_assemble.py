"""
Assembly writer for the SF50: parts -> glTF 2.0 binary (KHR_mesh_quantization) with the pc12 node conventions:
  part node  : name = part id, translation = pivot origin relative to the parent part's origin (glTF axes),
               extras = {part, name, step, group, qty, note, tris, info, pivot?}
  mesh nodes : '<part>#<k>' children carrying the de-quantisation transform
  light nodes: 'light:<kind>' children, extras.light = '<kind>' (+ colour, src obs/inf, basis) - js/aircraft/glb.js reads these
  reg panels : part 'reg_panel_L/R', extras.info.reg_panel = {centre, normal, up, length, height} (model axes)
"""
from __future__ import annotations
import json
import struct
import numpy as np

from sf50_kernel import GLBBuilder, to_gl, MATERIALS


class SF50GLB(GLBBuilder):
    def write(self, path, roots, asset_extras=None, generator="loftkit (pc12/cad kernel) - hwd3d SF50 build"):
        gltf = {"asset": {"version": "2.0", "generator": generator}, "scene": 0, "scenes": [{"nodes": list(roots)}],
                "nodes": self.nodes, "meshes": self.meshes, "materials": self.materials,
                "accessors": self.accessors, "bufferViews": self.bufferViews, "buffers": [{"byteLength": len(self.bin)}]}
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


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


def light_src(a):
    """(src, basis) of a light anchor (fix round 3, finding V1): a 'src' field holds only 'obs' / 'inf' (the provenance rule
    of tools/check_airport.py); the evidence text goes to 'basis'. An anchor is a model position, so it is 'inf' unless its
    text says 'obs' and nothing inferred."""
    text = a.get("basis") or a.get("src")
    if text in ("obs", "inf"):
        return text, None
    src = "obs" if text and "[obs" in text and "inf" not in text else "inf"
    return src, text


def write_glb(parts, path, meta=None, quantize=True):
    gb = SF50GLB(quantize=quantize)
    used = sorted({mat for p in parts.values() for _, mat in p.meshes})
    for name in used:
        rgba, met, rough = MATERIALS[name]
        gb.material(name, rgba, met, rough, double_sided=True)
    ids = list(parts.keys())
    origin_of = {pid: (np.asarray(parts[pid].pivot["origin"], float) if parts[pid].pivot else np.zeros(3)) for pid in ids}
    node_of = {}
    anchors = {}

    def make(pid):
        if pid in node_of:
            return node_of[pid]
        p = parts[pid]
        kids = []
        for k, (m, mat) in enumerate(p.meshes):
            kids.append(gb.mesh_node(f"{pid}#{k}", m, gb.mat_index[mat], origin=origin_of[pid]))
        for cid in [c for c in ids if parts[c].parent == pid]:
            kids.append(make(cid))
        info = dict(p.info)
        la = info.pop("light_anchors", None)
        if la:
            for kind, a in la.items():
                pt = np.asarray(a["p"], float)
                src, basis = light_src(a)
                kids.append(gb.node(f"light:{kind}", translation=to_gl(pt - origin_of[pid]),
                                    extras={"light": kind, "colour": a.get("colour"), "src": src, "basis": basis}))
                anchors[kind] = {"p": pt.tolist(), "p_gl": to_gl(pt).tolist(), "part": pid, "colour": a.get("colour"),
                                 "src": src, "basis": basis}
        parent_origin = origin_of[p.parent] if p.parent else np.zeros(3)
        extras = dict(part=pid, name=p.name, step=p.step, group=p.group, qty=p.qty, note=p.material_note,
                      explode=to_gl(np.asarray(p.explode, float)).tolist(), tris=int(p.tri_count()), info=_jsonable(info))
        if p.pivot:
            pv = dict(p.pivot)
            pv["origin"] = to_gl(np.asarray(pv["origin"], float)).tolist()
            pv["axis"] = to_gl(np.asarray(pv["axis"], float)).tolist()
            extras["pivot"] = _jsonable(pv)
        node_of[pid] = gb.node(pid, translation=to_gl(origin_of[pid] - parent_origin), children=kids, extras=extras)
        return node_of[pid]

    roots = [make(pid) for pid in ids if parts[pid].parent is None]
    root = gb.node("SF50", children=roots, extras=_jsonable(meta or {}))
    size = gb.write(path, [root])
    return size, gb.stats, anchors
