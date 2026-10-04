#!/usr/bin/env python3
"""Package the three.js viewer as a claude.ai Artifact: a multi-file static page hosted in a locked-down iframe.

    python3 web/package_artifact.py                 # -> pc12/dist_artifact/ (gitignored)
    python3 web/package_artifact.py --out DIR       # e.g. a folder the publishing session may read (see ARTIFACT.json)

The folder is the web/package.py bundle (vendored three.js r160, the meshopt GLB, HDRIs, drawings) with:

    index.html              the page file of the Artifact.  The host wraps it in its own <!doctype html><html><head>...
                            <body> skeleton (charset, viewport-fit=cover viewport, a small reset), so it has no doctype,
                            html, head or body tags: the <title>, the stylesheet, the markup, then the config, boot and
                            module scripts (the boot script adds the import map after itself).  The description and the
                            icon are publish parameters (ARTIFACT.json), not tags.  Config: {data: './data/',
                            three: './three/', glbLow: 'pc12_low.glb', glbGz: 'pc12_glb.gz.bin',
                            glbGzLow: 'pc12_low_glb.gz.bin', b64: {file name: parts}}.
    data/pc12.glb           EXT_meshopt_compression (~15 MB, ~2.3M triangles, 16-bit normals): loaded where
                            WebAssembly compiles
    data/pc12_low.glb       the light tier (PC12_RES=1 + build.LOW_FINE, ~13 MB, ~1.9M triangles),
                            EXT_meshopt_compression: phones
    data/pc12_glb.gz.bin    gzip of the full model out/pc12.glb (KHR_mesh_quantization only, ~39 MB -> ~23 MB): the
                            host's CSP may refuse WebAssembly ('wasm-unsafe-eval'), which the meshopt decoder needs;
                            index.html then loads this file instead (desktops), unpacked while it streams
                            (DecompressionStream), and main.js falls back to it when the meshopt GLB fails to decode --
                            so a desktop without WebAssembly still gets the full resolution
    data/pc12_low_glb.gz.bin  the same for the light tier out/pc12_low.glb (~32 MB -> ~19 MB): phones without
                            WebAssembly
    *.glb / *.bin / *.hdr   published as base64 text (the host serves no binary media type but images, media and fonts):
                            x.b64.txt, or x.b64.0.txt, x.b64.1.txt, ... when the text would exceed B64_PART characters
                            (parts of equal length, whole 4-character groups); the originals are removed.  index.html
                            decodes them while they stream (PC12_CONFIG.b64 = {file name: parts}, B.stream)
    data/pc12_meta.json     + stats.glb_gz_bytes / glb_gz_encoding (the loading bar's total on the gzip path)
    MANIFEST.json           web/package.py's file list (bytes, SHA-256, commit), not published
    ARTIFACT.json           the publish manifest: every file with its published path, content type and bytes -- `page`
                            (index.html, the publish call's file_path) and `files` {published path: {from, contentType}}
                            (the call's `files`, sources relative to `root`) -- plus title, description and icon,
                            and `publishes`: the files split into groups of <= 64 MB (one publish call each, the page in
                            the first; later publishes to the same url add their files)
                            MANIFEST.json, ARTIFACT.json and local test pages (_host*.html, test/artifact_test.py) are
                            not published

Host limits checked here (decimal MB, the conservative reading): <= 255 files and <= 64 MB per publish call (the
bundle is split into `publishes` groups), <= 511 files and <= 256 MB per artifact version, <= 15 MB per binary / 16 MB
per text file, standard media types only; ~90 MB in 2026-10 (two publishes).  test/artifact_test.py serves the folder behind a host-like skeleton
with a strict CSP (with and without 'wasm-unsafe-eval') and checks both loading paths in headless Chromium.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package as P  # noqa: E402  (web/package.py)

TITLE = "PC-12 PRO Parametric Model"
ICON = "plane"                      # the publish call's `icon`: one generic word
GZ_NAME = "pc12_glb.gz.bin"                # gzip of the full model (desktops without WebAssembly)
GZ_LOW_NAME = "pc12_low_glb.gz.bin"        # gzip of the light tier (phones without WebAssembly)
B64_SUFFIXES = (".glb", ".bin", ".hdr")   # binary files the host would refuse: published as base64 text
B64_PART = 12_000_000                      # characters per part (the host's text limit is 16 MB a file)
CONTENT_TYPES = {                          # the host's served types (a file of any other type is an error)
    ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
    ".svg": "image/svg+xml", ".txt": "text/plain", ".md": "text/markdown",
}
TEXT_TYPES = ("text/", "application/json", "image/svg+xml")
MAX_FILES, MAX_BINARY, MAX_TEXT = 255, 15_000_000, 16_000_000      # per publish call / per file
MAX_PUBLISH = 64_000_000                   # bytes per publish call: the bundle goes up in groups of at most this
MAX_TOTAL, MAX_VERSION_FILES = 256_000_000, 511                     # per artifact version (all publishes)
WARN_TOTAL = 180_000_000                   # headroom warning
NOT_PUBLISHED = {"MANIFEST.json", "ARTIFACT.json", ".nojekyll"}
SKELETON = re.compile(r"<!doctype[^>]*>|</?(html|head|body)\b[^>]*>", re.I)
DARK_MEDIA = re.compile(r'@media \(prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\) \{([^}]*)\}\s*\}')
DARK_ATTR = re.compile(r':root\[data-theme="dark"\] \{([^}]*)\}')


def artifact_config(b64: dict[str, int]) -> str:
    return ("<script>window.PC12_CONFIG = { data: './data/', three: './three/', glbLow: 'pc12_low.glb', glbGz: '" + GZ_NAME + "', glbGzLow: '" + GZ_LOW_NAME + "', b64: "
            + json.dumps(b64, sort_keys=True) + " };</script>")


def to_base64(out: Path) -> dict[str, int]:
    """Replace the bundle's binary files by base64 text parts (module docstring); returns {file name: parts}."""
    parts = {}
    for f in sorted(p for p in out.rglob("*") if p.is_file() and p.suffix.lower() in B64_SUFFIXES):
        raw = f.read_bytes()
        text = base64.b64encode(raw)
        n = -(-len(text) // B64_PART)
        step = -(-len(text) // n // 4) * 4
        chunks = [text[i:i + step] for i in range(0, len(text), step)]
        if b"".join(chunks) != text or base64.b64decode(b"".join(chunks)) != raw:
            sys.exit(f"{f}: base64 parts do not decode to the file")
        names = [f"{f.name}.b64.txt"] if len(chunks) == 1 else [f"{f.name}.b64.{i}.txt" for i in range(len(chunks))]
        for name, c in zip(names, chunks):
            (f.parent / name).write_bytes(c)
        if f.name in parts:
            sys.exit(f"{f}: two binary files named {f.name}")
        parts[f.name] = len(chunks)
        f.unlink()
    return parts


def artifact_page(html: str, config: str) -> tuple[str, str]:
    """The bundle's index.html as an Artifact page file (see the module docstring), and its meta description."""
    html, n = re.subn(re.escape(P.BUNDLE_CONFIG["vendor"]), lambda _: config, html)
    if n != 1:
        sys.exit("index.html: the bundle's PC12_CONFIG line is missing")
    m = re.search(r"<head\b[^>]*>(.*)</head>\s*<body\b([^>]*)>(.*)</body>", html, re.S | re.I)
    if not m:
        sys.exit("index.html: no <head> ... </head><body> ... </body>")
    head, body_attrs, markup = m.groups()
    if body_attrs.strip():
        sys.exit(f"index.html: <body{body_attrs}> has attributes the host's skeleton would drop")
    desc = re.search(r'<meta name="description" content="([^"]*)">', head)
    # the host's skeleton brings the charset and viewport metas; the viewer's stylesheet sets color-scheme on :root;
    # the description and the icon are publish parameters (inside <body> they would do nothing)
    head = re.sub(r'^(<meta [^>]*>|<link rel="icon"[^>]*>)\n', "", head, flags=re.M)
    head, n = re.subn(r"<title>[^<]*</title>\n", "", head)
    if n != 1:
        sys.exit("index.html: expected one <title>")
    styles = re.findall(r'^<link rel="stylesheet"[^>]*>\n', head, re.M)
    scripts = re.sub(r'^<link rel="stylesheet"[^>]*>\n', "", head, flags=re.M).strip("\n")
    left = re.sub(r"<!--.*?-->|<script\b[^>]*>.*?</script>", "", scripts, flags=re.S).strip()
    if not styles or left:
        sys.exit(f"index.html: the head should hold the title, metas, links, comments and scripts only (left: {left[:80]!r})")
    page = f"<title>{TITLE}</title>\n" + "".join(styles) + markup.strip("\n") + "\n" + scripts + "\n"
    return page, desc.group(1) if desc else ""


def check_page(out: Path, html: str, config: str) -> list[str]:
    errs = []
    if not html.startswith(f"<title>{TITLE}</title>"):
        errs.append("index.html does not start with the <title>")
    for m in SKELETON.finditer(html):
        errs.append(f"index.html keeps a skeleton tag: {m.group(0)}")
    if config not in html:
        errs.append("index.html: artifact config line missing")
    for m in re.finditer(r"""(?:src|href)="([^"#:]+)\"""", html):
        if not (out / m.group(1)).exists():
            errs.append(f"index.html references missing {m.group(1)}")
    for need in ("type = 'importmap'", 'type="module" src="viewer/main.js"', 'rel="stylesheet" href="viewer/viewer.css"',
                 'id="loading"', "B.fetchGLB", "B.stream", "new WebAssembly.Module", "DecompressionStream"):
        if need not in html:
            errs.append(f"index.html: {need!r} missing")
    for bad in ("<meta ", 'rel="icon"'):
        if bad in html:
            errs.append(f"index.html: {bad!r} outside the host's <head>")
    if not html.index('rel="stylesheet"') < html.index('<div id="app"') < html.index("<script"):
        errs.append("index.html: not in the order title, stylesheet, markup, scripts")
    # dark theme: the OS setting (unless data-theme="light") and data-theme="dark" must define the same tokens
    css = (out / "viewer" / "viewer.css").read_text(encoding="utf-8")
    a, b = DARK_MEDIA.search(css), DARK_ATTR.search(css)
    decl = lambda s: [x.strip() for x in s.strip().splitlines()]  # noqa: E731
    if not (a and b) or decl(a.group(1)) != decl(b.group(1)) or css.count("@media (prefers-color-scheme") != 1:
        errs.append("viewer.css: the prefers-color-scheme dark block and :root[data-theme=\"dark\"] differ")
    return errs


def gzip_glb(src: Path, dst: Path) -> dict:
    raw = src.read_bytes()
    j = P.glb_json(src)
    if "EXT_meshopt_compression" in (j.get("extensionsUsed") or []):
        sys.exit(f"{src} uses EXT_meshopt_compression: the gzip fallback must be the plain KHR_mesh_quantization GLB")
    dst.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    if gzip.decompress(dst.read_bytes()) != raw:
        sys.exit(f"{dst}: does not unpack to {src}")
    return {"bytes_in": len(raw), "bytes_out": dst.stat().st_size}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=P.ROOT / "dist_artifact", help="folder (default pc12/dist_artifact, gitignored)")
    ap.add_argument("--data", type=Path, default=P.ROOT / "out", help="folder with pc12.glb, pc12_meta.json and the drawing SVGs")
    ap.add_argument("--materials", type=Path, help="lookdev materials JSON instead of web/viewer/materials.json")
    a = ap.parse_args()
    out, data = a.out.resolve(), a.data.resolve()

    # 1. the normal bundle (vendored three.js, meshopt GLB) and its checks
    files, info = P.build(out, data, a.materials.resolve() if a.materials else None, "vendor", True)
    errs = P.verify(out, "vendor")
    (out / ".nojekyll").unlink(missing_ok=True)       # GitHub Pages only

    # 2. the gzip fallbacks (full model for desktops, light tier for phones) + their sizes in the metadata
    gz = gzip_glb(data / "pc12.glb", out / "data" / GZ_NAME)
    gz_low = gzip_glb(data / "pc12_low.glb", out / "data" / GZ_LOW_NAME)
    meta_p = out / "data" / "pc12_meta.json"
    meta = json.loads(meta_p.read_text())
    meta["stats"]["glb_gz_bytes"] = gz["bytes_out"]
    meta["stats"]["glb_gz_encoding"] = "KHR_mesh_quantization, gzip"
    meta["stats"]["glb_gz_tier"] = "full"
    meta["stats"]["low"]["glb_gz_bytes"] = gz_low["bytes_out"]
    meta_p.write_text(json.dumps(meta, indent=1) + "\n")

    # 3. binary files -> base64 text, and the page file
    b64 = to_base64(out)
    config = artifact_config(b64)
    page, desc = artifact_page((out / "index.html").read_text(encoding="utf-8"), config)
    (out / "index.html").write_text(page, encoding="utf-8")
    errs += check_page(out, page, config)

    # 4. manifests: package.py's (provenance, and a re-run may wipe the folder) and the publish manifest
    all_files = sorted(p for p in out.rglob("*") if p.is_file() and p.name not in NOT_PUBLISHED
                       and not p.name.startswith("_host"))
    (out / "MANIFEST.json").write_text(json.dumps({
        "about": "PC-12 PRO viewer, claude.ai Artifact bundle (web/package_artifact.py)",
        "three": f"three/ (r{P.THREE_REVISION}, from web/three_local)",
        "glb": info.get("meshopt"), "glb_low": info.get("meshopt_low"), "glb_gz": {**gz, "file": f"data/{GZ_NAME}"},
        "glb_gz_low": {**gz_low, "file": f"data/{GZ_LOW_NAME}"},
        "commit": P.git_commit(), "built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "files": {str(p.relative_to(out)): {"bytes": p.stat().st_size, "sha256": P.sha256(p)} for p in all_files},
    }, indent=1) + "\n")
    pub, sizes, types = {}, {}, {}
    for p in all_files:
        rel = str(p.relative_to(out))
        ct = CONTENT_TYPES.get(p.suffix.lower())
        if ct is None:
            errs.append(f"{rel}: no standard media type for {p.suffix!r}")
            continue
        n = p.stat().st_size
        lim = MAX_TEXT if ct.startswith(TEXT_TYPES) else MAX_BINARY
        if n > lim:
            errs.append(f"{rel}: {n / 1e6:.2f} MB over the {lim / 1e6:.0f} MB limit")
        sizes[rel], types[rel] = n, ct
        if rel != "index.html":
            pub[rel] = {"from": rel, "contentType": ct}
    total = sum(sizes.values())
    if len(sizes) > MAX_VERSION_FILES:
        errs.append(f"{len(sizes)} files, over the {MAX_VERSION_FILES} per-version limit")
    if total > MAX_TOTAL:
        errs.append(f"{total / 1e6:.1f} MB, over the {MAX_TOTAL / 1e6:.0f} MB per-version limit")
    # publish groups: the page and the small files first, then the largest files first-fit, each group <= MAX_PUBLISH
    groups = [{"bytes": sizes.get("index.html", 0), "files": {}}]
    for rel in sorted(pub, key=lambda r: (sizes[r] > 1_000_000, -sizes[r], r)):
        g = next((g for g in groups if g["bytes"] + sizes[rel] <= MAX_PUBLISH and len(g["files"]) < MAX_FILES - 1), None)
        if g is None:
            groups.append(g := {"bytes": 0, "files": {}})
        g["files"][rel] = pub[rel]
        g["bytes"] += sizes[rel]
    art = {
        "about": "claude.ai Artifact publish manifest (web/package_artifact.py): publish `page` as file_path with `files` "
                 "and `root` (every `from` is relative to root; root must lie where the publishing session may read, "
                 "e.g. its scratchpad: package there with --out), plus title / description / icon",
        "title": TITLE, "description": desc, "icon": ICON, "root": str(out),
        "page": {"path": "index.html", "contentType": types.get("index.html"), "bytes": sizes.get("index.html")},
        "files": pub,
        "bytes": sizes, "count": len(sizes), "total_bytes": total,
        "publishes": groups,
        "glb": {"meshopt": meta["stats"]["glb_bytes"], "meshopt_low": meta["stats"]["low"]["glb_bytes"],
                "gzip_fallback": gz["bytes_out"], "plain_unpacked": gz["bytes_in"],
                "gzip_fallback_low": gz_low["bytes_out"], "plain_unpacked_low": gz_low["bytes_in"]},
        "base64": b64,
    }
    (out / "ARTIFACT.json").write_text(json.dumps(art, indent=1) + "\n")

    print(f"artifact bundle {out}: {len(sizes)} files (the page + {len(pub)}), {total:,} bytes ({total / 1e6:.1f} MB of the "
          f"host's {MAX_TOTAL / 1e6:.0f} MB per version), in {len(groups)} publish call(s) of "
          + ", ".join(f"{g['bytes'] / 1e6:.1f}" for g in groups) + " MB")
    if total > WARN_TOTAL:
        print(f"  WARNING: {total / 1e6:.1f} MB is within {(MAX_TOTAL - total) / 1e6:.1f} MB of the host's limit "
              f"(warning above {WARN_TOTAL / 1e6:.0f} MB)")
    print(f"  data/pc12.glb         {meta['stats']['glb_bytes']:>11,} bytes  EXT_meshopt_compression "
          f"({meta['stats'].get('triangles', 0):,} triangles)")
    print(f"  data/pc12_low.glb     {meta['stats']['low']['glb_bytes']:>11,} bytes  EXT_meshopt_compression, light tier "
          f"({meta['stats']['low'].get('triangles', 0):,} triangles)")
    print(f"  data/{GZ_NAME}  {gz['bytes_out']:>11,} bytes  gzip of the {gz['bytes_in']:,}-byte KHR_mesh_quantization "
          f"full model (desktops without WebAssembly)")
    print(f"  data/{GZ_LOW_NAME}  {gz_low['bytes_out']:>11,} bytes  gzip of the {gz_low['bytes_in']:,}-byte light tier "
          f"(phones without WebAssembly)")
    for k, v in sorted(sizes.items(), key=lambda kv: -kv[1])[:8]:
        print(f"    {k:34s} {v:>11,} bytes")
    print("  as base64 text: " + ", ".join(f"{k} ({v} part{'s' * (v > 1)})" for k, v in b64.items()))
    print(f"  publish manifest: {out / 'ARTIFACT.json'}")
    if errs:
        print("VERIFY FAILED:", *errs, sep="\n  ")
        sys.exit(1)
    print("verify: OK (bundle, page file, theme tokens, media types, host limits)")


if __name__ == "__main__":
    main()
