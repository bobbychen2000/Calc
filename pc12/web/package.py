#!/usr/bin/env python3
"""Assemble the three.js viewer into a self-contained static bundle.

    python3 web/package.py                 # -> pc12/dist/
    python3 web/package.py --out /tmp/site --zip

Layout of the bundle (everything the page loads, nothing else):

    index.html          the viewer page; its config line is rewritten to {data: './data/', three: './three/'}:
                        the model is read from ./data/ next to the page and three.js r160 from ./three/
    three/              the three.js r160 files the viewer imports (build/three.module.min.js + the addons and their
                        relative imports), copied from web/three_local (a checkout of mrdoob/three.js r160, which the
                        tests use too).  No third-party origin at run time; --three cdn keeps the jsDelivr CDN instead.
    viewer/*.js, viewer.css, materials.json
    assets/             studio HDRI, 1k and a 512 px copy for phones (CC0, see assets/SOURCES.md)
    data/pc12.glb       EXT_meshopt_compression (gltf-transform meshopt, lossless on the already quantised data:
                        16-bit positions / 8-bit normals as in out/pc12.glb; ~10.5 -> ~3.6 MB, ~2 MB gzipped);
                        --no-meshopt ships out/pc12.glb as it is
    data/pc12_meta.json stats.glb_bytes / glb_encoding rewritten for the packaged GLB (the progress bar's fallback
                        total under gzip / brotli transfer encoding)
    data/pc12_ga.svg, pc12_sections.svg
    MANIFEST.json       file list with sizes and SHA-256, source commit, build time
    .nojekyll           (GitHub Pages: serve the files as they are)

Host the folder on any static web server (GitHub Pages, S3, `python3 -m http.server`); it must be served over
HTTP(S), not opened as file://.  ?data=<base>, ?glb=, ?meta= still override the data location.

The model files are taken from out/ (or --data); the viewer never hard-codes geometry, so a rebuilt
out/pc12.glb + out/pc12_meta.json just needs a re-run.  The meshopt step needs gltf-transform 4 (on PATH, in the
npx cache, or fetched by `npx @gltf-transform/cli@4`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

WEB = Path(__file__).resolve().parent            # pc12/web
ROOT = WEB.parent                                # pc12
THREE_CDN = "https://cdn.jsdelivr.net/npm/three@0.160.0/"
THREE_LOCAL = WEB / "three_local"
THREE_REVISION = "160"
THREE_MAIN = "build/three.module.min.js"         # what the import map maps 'three' to (index.html)
DATA_FILES = ["pc12.glb", "pc12_meta.json", "pc12_ga.svg", "pc12_sections.svg"]
VIEWER_EXT = {".js", ".css", ".json"}
CONFIG_RE = re.compile(r"<script>window\.PC12_CONFIG = \{[^<]*\};</script>")
BUNDLE_CONFIG = {"vendor": "<script>window.PC12_CONFIG = { data: './data/', three: './three/' };</script>",
                 "cdn": "<script>window.PC12_CONFIG = { data: './data/', three: 'cdn' };</script>"}
MESHOPT_ARGS = ["--level", "medium", "--quantize-position", "16", "--quantize-normal", "8"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str | None:
    try:
        rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "web", "out/pc12.glb", "out/pc12_meta.json"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return rev + ("+dirty" if dirty else "")
    except Exception:
        return None


# ----------------------------------------------------------------------------- module graph
# static imports / re-exports (line-anchored, so example code in comments is not picked up) and dynamic imports
STATIC_IMPORT_RE = re.compile(r"""^\s*(?:import|export)\b[^'"`;]*?\bfrom\s*['"]([^'"]+)['"]|^\s*import\s*['"]([^'"]+)['"]""", re.M)
DYNAMIC_IMPORT_RE = re.compile(r"""\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)""")
URL_RE = re.compile(r"""new URL\(\s*['"](\.{1,2}/[^'"]+)['"]\s*,\s*import\.meta\.url\s*\)""")


def module_specifiers(src: str) -> list[str]:
    out = [m.group(1) or m.group(2) for m in STATIC_IMPORT_RE.finditer(src)]
    return out + [m.group(1) for m in DYNAMIC_IMPORT_RE.finditer(src)]


def three_graph(viewer_dir: Path, three_root: Path) -> list[str]:
    """three.js files (relative to the three root) the viewer modules import, with the addons' own relative imports."""
    need, todo = {THREE_MAIN}, []
    for js in sorted(viewer_dir.glob("*.js")):
        for spec in module_specifiers(js.read_text(encoding="utf-8")):
            if spec.startswith("three/addons/"):
                todo.append("examples/jsm/" + spec[len("three/addons/"):])
    while todo:
        rel = todo.pop()
        if rel in need:
            continue
        need.add(rel)
        f = three_root / rel
        if not f.is_file():
            continue            # reported by verify()
        for spec in module_specifiers(f.read_text(encoding="utf-8")):
            if spec.startswith("."):
                todo.append(os.path.normpath(str(Path(rel).parent / spec)).replace(os.sep, "/"))
            elif spec.startswith("three/addons/"):
                todo.append("examples/jsm/" + spec[len("three/addons/"):])
    return sorted(need)


# ----------------------------------------------------------------------------- GLB
def glb_json(p: Path) -> dict:
    b = p.read_bytes()
    if b[:4] != b"glTF":
        raise ValueError(f"{p} is not a binary glTF")
    n = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + n])


def gltf_transform() -> list[str] | None:
    """gltf-transform 4: on PATH, in the npx cache, or through npx (may download it)."""
    exe = shutil.which("gltf-transform")
    if exe:
        return [exe]
    cached = sorted(glob.glob(os.path.expanduser("~/.npm/_npx/*/node_modules/@gltf-transform/cli/bin/cli.js")))
    node = shutil.which("node")
    if cached and node:
        return [node, cached[-1]]
    npx = shutil.which("npx")
    return [npx, "--yes", "@gltf-transform/cli@4"] if npx else None


def used_materials(j: dict) -> list[str]:
    mats = j.get("materials", [])
    return sorted({mats[p["material"]].get("name", "") for m in j.get("meshes", []) for p in m["primitives"] if "material" in p})


# Per primitive: the bounds of the vertices the triangles use (in the mesh node's parent frame), decoded with three's
# meshopt decoder.  Unreferenced vertices are ignored: gltf-transform drops them (fus_aft has 28, ~8 mm outside).
GEOMETRY_JS = r"""
import { readFileSync } from 'fs';
import { pathToFileURL } from 'url';
const { MeshoptDecoder } = await import(pathToFileURL(process.argv[2]).href);
await MeshoptDecoder.ready;
const CT = { 5120: [1, 'getInt8', 127], 5121: [1, 'getUint8', 255], 5122: [2, 'getInt16', 32767], 5123: [2, 'getUint16', 65535], 5125: [4, 'getUint32', 1], 5126: [4, 'getFloat32', 1] };
const NC = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };
function glb(p) {
  const b = readFileSync(p), n = b.readUInt32LE(12), j = JSON.parse(b.subarray(20, 20 + n).toString());
  const o = 20 + n, bl = b.readUInt32LE(o);
  return { j, bin: new Uint8Array(b.buffer, b.byteOffset + o + 8, bl) };
}
function accessor({ j, bin }, i) {
  const a = j.accessors[i], bv = j.bufferViews[a.bufferView], ext = bv.extensions && bv.extensions.EXT_meshopt_compression;
  const [size, get, norm] = CT[a.componentType], nc = NC[a.type];
  let data, stride = bv.byteStride || size * nc;
  if (ext) {
    data = new Uint8Array(ext.count * ext.byteStride);
    MeshoptDecoder.decodeGltfBuffer(data, ext.count, ext.byteStride, bin.subarray(ext.byteOffset || 0, (ext.byteOffset || 0) + ext.byteLength), ext.mode, ext.filter || 'NONE');
    stride = ext.byteStride;
  } else data = bin.subarray(bv.byteOffset || 0, (bv.byteOffset || 0) + bv.byteLength);
  const dv = new DataView(data.buffer, data.byteOffset, data.byteLength), off = a.byteOffset || 0;
  const k = a.normalized ? norm : 1;
  return (e, c) => { const v = dv[get](off + e * stride + c * size, true) / k; return a.normalized ? Math.max(v, -1) : v; };
}
function rot(q, v) {
  const [x, y, z, w] = q, [a, b, c] = v, ix = w * a + y * c - z * b, iy = w * b + z * a - x * c, iz = w * c + x * b - y * a, iw = -x * a - y * b - z * c;
  return [ix * w + iw * -x + iy * -z - iz * -y, iy * w + iw * -y + iz * -x - ix * -z, iz * w + iw * -z + ix * -y - iy * -x];
}
function bounds(p) {
  const g = glb(p), out = {};
  let tris = 0;
  for (const nd of g.j.nodes) {
    if (nd.mesh == null) continue;
    const t = nd.translation || [0, 0, 0], s = nd.scale || [1, 1, 1], q = nd.rotation || [0, 0, 0, 1];
    g.j.meshes[nd.mesh].primitives.forEach((pr, k) => {
      const P = accessor(g, pr.attributes.POSITION), I = accessor(g, pr.indices), n = g.j.accessors[pr.indices].count;
      const mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
      for (let e = 0; e < n; e++) {
        const i = I(e, 0), v = rot(q, [0, 1, 2].map((c) => s[c] * P(i, c)));
        for (let c = 0; c < 3; c++) { const x = t[c] + v[c]; if (x < mn[c]) mn[c] = x; if (x > mx[c]) mx[c] = x; }
      }
      tris += n / 3;
      out[nd.name + '/' + k] = [...mn, ...mx];
    });
  }
  return { out, tris };
}
const A = bounds(process.argv[3]), B = bounds(process.argv[4]);
let worst = 0, who = '';
for (const k in A.out) {
  if (!B.out[k]) { worst = Infinity; who = k + ' missing'; break; }
  const d = Math.max(...A.out[k].map((x, i) => Math.abs(x - B.out[k][i])));
  if (d > worst) { worst = d; who = k; }
}
console.log(JSON.stringify({ prims: [Object.keys(A.out).length, Object.keys(B.out).length], tris: [A.tris, B.tris], worst_mm: +(worst * 1000).toFixed(4), worst_prim: who }));
"""


def geometry_shift(a: Path, b: Path) -> dict | None:
    """Compare the triangles' vertex bounds of two GLBs (either may be meshopt-compressed); None without node."""
    node, dec = shutil.which("node"), THREE_LOCAL / "examples/jsm/libs/meshopt_decoder.module.js"
    if not node or not dec.is_file():
        return None
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / "geometry.mjs"
        js.write_text(GEOMETRY_JS)
        r = subprocess.run([node, str(js), str(dec), str(a), str(b)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"geometry check failed:\n{r.stderr[-2000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def meshopt(src: Path, dst: Path) -> dict:
    """EXT_meshopt_compression via gltf-transform, then check nothing the viewer reads changed: node names,
    transforms and extras (pivots), mesh names, the materials the meshes use.  (gltf-transform prunes materials no mesh
    uses, e.g. leftover livery slots; the viewer never looks those up.)"""
    cmd = gltf_transform()
    if not cmd:
        raise RuntimeError("gltf-transform not found: `npm i -g @gltf-transform/cli@4` (or install Node.js for npx), "
                           "or package with --no-meshopt")
    # dequantize first: gltf-transform's quantizer re-fits the node scale of already-quantised meshes that do not span
    # the full int16 range (the winglets, the dorsal fin: 0.02 -> 0.0137) without re-mapping their integers, which
    # shrinks them by up to ~4 mm; from float it re-quantises correctly (16-bit over each mesh: < 0.02 mm)
    with tempfile.TemporaryDirectory() as td:
        mid = Path(td) / "dequantized.glb"
        for args in (["dequantize", str(src), str(mid)], ["meshopt", str(mid), str(dst)] + MESHOPT_ARGS):
            r = subprocess.run(cmd + args, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"gltf-transform {args[0]} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    if not dst.is_file():
        raise RuntimeError("gltf-transform meshopt wrote nothing")
    a, b = glb_json(src), glb_json(dst)
    if "EXT_meshopt_compression" not in (b.get("extensionsRequired") or []):
        raise RuntimeError("meshopt output does not require EXT_meshopt_compression")

    def norm(v):              # JSON numbers as the viewer sees them (0 == 0.0 == -0.0)
        if isinstance(v, dict):
            return {k: norm(x) for k, x in v.items()}
        if isinstance(v, list):
            return [norm(x) for x in v]
        return round(float(v), 9) + 0.0 if isinstance(v, (int, float)) and not isinstance(v, bool) else v

    TRS = {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}   # glTF defaults (identity dropped)

    def key(n):
        # a mesh node's translation / scale is its KHR_mesh_quantization dequantisation, which gltf-transform may
        # re-fit to the mesh's own bounds: compared through the world boxes below instead
        trs = [n.get(k, d) for k, d in TRS.items()] if "mesh" not in n else [n.get("rotation", TRS["rotation"])]
        return json.dumps(norm([n.get("name"), *trs, n.get("matrix"), n.get("extras")]), sort_keys=True)
    if sorted(map(key, a["nodes"])) != sorted(map(key, b["nodes"])):
        raise RuntimeError("meshopt changed node names / transforms / extras")

    geo = geometry_shift(src, dst)
    if geo is None:
        print("meshopt: node or web/three_local's meshopt decoder missing: geometry not compared", file=sys.stderr)
    elif geo["prims"][0] != geo["prims"][1] or geo["tris"][0] != geo["tris"][1] or geo["worst_mm"] > 0.05:
        raise RuntimeError(f"meshopt changed the geometry: {geo}")
    if sorted(m.get("name", "") for m in a["meshes"]) != sorted(m.get("name", "") for m in b["meshes"]):
        raise RuntimeError("meshopt changed the meshes")
    if used_materials(a) != used_materials(b):
        raise RuntimeError("meshopt changed the materials the meshes use")
    dropped = sorted({m.get("name") for m in a.get("materials", [])} - {m.get("name") for m in b.get("materials", [])})
    return {"bytes_in": src.stat().st_size, "bytes_out": dst.stat().st_size, "pruned_unused_materials": dropped,
            "geometry": geo, "tool": " ".join(Path(c).name for c in cmd[:2])}


def build(out: Path, data: Path, materials: Path | None, three: str, use_meshopt: bool) -> tuple[list[Path], dict]:
    if out.exists():
        # only ever wipe a folder this script made (or an empty one)
        if any(out.iterdir()) and not (out / "MANIFEST.json").exists():
            sys.exit(f"refusing to overwrite {out}: it exists and has no MANIFEST.json from a previous package run")
        shutil.rmtree(out)
    (out / "viewer").mkdir(parents=True)
    (out / "assets").mkdir()
    (out / "data").mkdir()
    # placeholder, so a re-run may wipe the folder even if this run stops half-way (main() writes the real one)
    (out / "MANIFEST.json").write_text('{"about": "incomplete web/package.py run"}\n')
    info: dict = {}

    # page: the one config line differs from the repo copy
    html = (WEB / "index.html").read_text(encoding="utf-8")
    html, n = CONFIG_RE.subn(BUNDLE_CONFIG[three], html)
    if n != 1:
        sys.exit("web/index.html: could not find the window.PC12_CONFIG line to rewrite")
    (out / "index.html").write_text(html, encoding="utf-8")

    for p in sorted((WEB / "viewer").iterdir()):
        if p.is_file() and p.suffix in VIEWER_EXT:
            shutil.copy2(p, out / "viewer" / p.name)
    if materials:
        json.loads(materials.read_text())            # must be valid JSON
        shutil.copy2(materials, out / "viewer" / "materials.json")
    for p in sorted((WEB / "assets").iterdir()):
        if p.is_file():
            shutil.copy2(p, out / "assets" / p.name)

    # three.js r160, vendored from web/three_local
    if three == "vendor":
        if not (THREE_LOCAL / THREE_MAIN).is_file():
            sys.exit(f"{THREE_LOCAL}/{THREE_MAIN} missing: web/three_local must be a checkout of mrdoob/three.js r160 "
                     "(or package with --three cdn)")
        files = three_graph(out / "viewer", THREE_LOCAL)
        for rel in files:
            (out / "three" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(THREE_LOCAL / rel, out / "three" / rel)
        (out / "three" / "README.txt").write_text(
            f"three.js r{THREE_REVISION} (https://github.com/mrdoob/three.js, MIT licence, Copyright 2010-2023 Three.js "
            "Authors): the files the PC-12 viewer imports, copied unchanged by web/package.py.\n")
        info["three_files"] = files

    missing = [f for f in DATA_FILES if not (data / f).is_file()]
    if missing:
        sys.exit(f"missing model files in {data}: {', '.join(missing)} (run model/build.py and drawing.sheet first)")
    for f in DATA_FILES:
        if f == "pc12.glb" and use_meshopt:
            try:
                info["meshopt"] = meshopt(data / f, out / "data" / f)
            except RuntimeError as e:
                sys.exit(f"meshopt: {e}")
        else:
            shutil.copy2(data / f, out / "data" / f)
    # the progress bar's fallback total (gzip / brotli transfers report the compressed Content-Length)
    meta_p = out / "data" / "pc12_meta.json"
    meta = json.loads(meta_p.read_text())
    st = meta.setdefault("stats", {})
    st["glb_bytes"] = (out / "data" / "pc12.glb").stat().st_size
    st["glb_encoding"] = "EXT_meshopt_compression" if use_meshopt else "KHR_mesh_quantization"
    meta_p.write_text(json.dumps(meta, indent=1) + "\n")
    (out / ".nojekyll").write_text("")
    return sorted(p for p in out.rglob("*") if p.is_file()), info


BOOT_LIST_RE = re.compile(r"\[((?:\s*'[^']+',?)+)\s*\]\.forEach\(function \(u\) \{ link\('modulepreload', (base \+ )?u\); \}\)")


def verify(out: Path, three: str) -> list[str]:
    """Static checks: every import / asset URL resolves inside the bundle, three.js is vendored (or the CDN base is
    set), the boot script's modulepreload lists match the module graph, the data files are present and consistent."""
    errs = []
    html = (out / "index.html").read_text(encoding="utf-8")
    if BUNDLE_CONFIG[three] not in html:
        errs.append("index.html: bundle config line missing")
    if THREE_CDN not in html:
        errs.append("index.html: three.js CDN base missing (the boot script's CDN mode)")
    if f"'three': base + '{THREE_MAIN}'" not in html:
        errs.append(f"index.html: the import map does not map 'three' to {THREE_MAIN}")
    for m in re.finditer(r"""(?:src|href)="([^"#:]+)\"""", html):
        if not (out / m.group(1)).exists():
            errs.append(f"index.html references missing {m.group(1)}")
    for rel in ("assets/studio_small_09_1k.hdr", "assets/studio_small_09_512.hdr", "viewer/materials.json"):
        if f"'{rel}'" not in html:
            errs.append(f"index.html: no preload for {rel}")
        if not (out / rel).is_file():
            errs.append(f"{rel} missing")
    # module graph: viewer modules, their relative imports and the three.js files
    viewer_mods, three_mods = set(), set()
    for js in sorted((out / "viewer").glob("*.js")):
        viewer_mods.add("viewer/" + js.name)
        src = js.read_text(encoding="utf-8")
        for spec in module_specifiers(src):
            if spec.startswith("."):
                if not (js.parent / spec).resolve().is_file():
                    errs.append(f"{js.name}: import {spec} not in the bundle")
            elif spec.startswith("three/addons/"):
                three_mods.add("examples/jsm/" + spec[len("three/addons/"):])
            elif spec != "three":
                errs.append(f"{js.name}: bare import {spec!r} not in the import map")
        for m in URL_RE.finditer(src):
            if not (js.parent / m.group(1)).resolve().is_file():
                errs.append(f"{js.name}: asset {m.group(1)} not in the bundle")
        if "three_local" in src:
            errs.append(f"{js.name}: mentions three_local")
    graph = set(three_graph(out / "viewer", out / "three" if three == "vendor" else THREE_LOCAL))
    lists = BOOT_LIST_RE.findall(html)
    pre_viewer = {x for body, b in lists if not b for x in re.findall(r"'([^']+)'", body)}
    pre_three = {x for body, b in lists if b for x in re.findall(r"'([^']+)'", body)}
    if pre_viewer != viewer_mods:
        errs.append(f"index.html modulepreload (viewer) differs from the modules: missing {sorted(viewer_mods - pre_viewer)}, "
                    f"extra {sorted(pre_viewer - viewer_mods)}")
    if pre_three != graph:
        errs.append(f"index.html modulepreload (three) differs from the import graph: missing {sorted(graph - pre_three)}, "
                    f"extra {sorted(pre_three - graph)}")
    if three == "vendor":
        for rel in sorted(graph):
            if not (out / "three" / rel).is_file():
                errs.append(f"three/{rel} missing")
        main = out / "three" / THREE_MAIN
        if main.is_file() and f'"{THREE_REVISION}"' not in main.read_text(encoding="utf-8")[:400]:
            errs.append(f"three/{THREE_MAIN} is not r{THREE_REVISION}")
    # data
    meta = json.loads((out / "data" / "pc12_meta.json").read_text())
    if not meta.get("steps"):
        errs.append("data/pc12_meta.json has no build steps")
    glb = out / "data" / "pc12.glb"
    try:
        j = glb_json(glb)
        req = j.get("extensionsRequired") or []
        if (meta.get("stats") or {}).get("glb_bytes") != glb.stat().st_size:
            errs.append("data/pc12_meta.json stats.glb_bytes is not the packaged GLB's size")
        if "EXT_meshopt_compression" in req and "setMeshoptDecoder" not in (out / "viewer" / "model.js").read_text(encoding="utf-8"):
            errs.append("the GLB needs EXT_meshopt_compression but model.js sets no MeshoptDecoder")
    except ValueError as e:
        errs.append(str(e))
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "dist", help="bundle folder (default pc12/dist, gitignored)")
    ap.add_argument("--data", type=Path, default=ROOT / "out", help="folder with pc12.glb, pc12_meta.json and the drawing SVGs")
    ap.add_argument("--materials", type=Path, help="lookdev materials JSON to ship instead of web/viewer/materials.json "
                                                   "(e.g. render/lookdev_materials.json after a lookdev update)")
    ap.add_argument("--three", choices=["vendor", "cdn"], default="vendor",
                    help="vendor: copy three.js r160 from web/three_local into three/ (default); cdn: load it from jsDelivr")
    ap.add_argument("--no-meshopt", action="store_true", help="ship out/pc12.glb as it is (no EXT_meshopt_compression)")
    ap.add_argument("--zip", action="store_true", help="also write <out>.zip")
    a = ap.parse_args()
    out = a.out.resolve()
    files, info = build(out, a.data.resolve(), a.materials.resolve() if a.materials else None, a.three, not a.no_meshopt)
    errs = verify(out, a.three)
    manifest = {
        "about": "PC-12 PRO viewer static bundle (web/package.py)",
        "three": f"three/ (r{THREE_REVISION}, from web/three_local)" if a.three == "vendor" else THREE_CDN,
        "glb": info.get("meshopt") or "KHR_mesh_quantization (as built)",
        "commit": git_commit(),
        "built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "files": {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in files},
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    total = sum(v["bytes"] for v in manifest["files"].values())
    print(f"bundle {out}  ({len(files) + 1} files, {total / 1048576:.1f} MB)")
    for k, v in manifest["files"].items():
        if v["bytes"] > 200_000:
            print(f"  {k:36s} {v['bytes'] / 1048576:6.2f} MB")
    if info.get("meshopt"):
        m = info["meshopt"]
        print(f"meshopt: {m['bytes_in'] / 1048576:.2f} -> {m['bytes_out'] / 1048576:.2f} MB ({m['tool']}); "
              f"pruned unused materials: {', '.join(m['pruned_unused_materials']) or 'none'}")
    if a.zip:
        z = out.with_suffix(".zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for p in sorted(out.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(out))
        print(f"zip {z} ({z.stat().st_size / 1048576:.1f} MB)")
    if errs:
        print("VERIFY FAILED:", *errs, sep="\n  ")
        sys.exit(1)
    print("verify: OK (imports, modulepreloads, three.js " + ("vendored" if a.three == "vendor" else "CDN") + ", assets, data)")


if __name__ == "__main__":
    main()
