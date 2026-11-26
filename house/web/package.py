#!/usr/bin/env python3
"""Package the viewer as a self-contained static bundle (also the claude.ai Artifact layout).

    python3 web/package.py [--out DIR]          # default house/dist/ (git-ignored)

DIR/index.html        the page WITHOUT doctype / html / head / body tags (an Artifact host wraps it in its own
                      skeleton); DIR/_local.html wraps it the same way for local tests.
DIR/viewer/           the viewer's modules and stylesheet (copied)
DIR/three/            the three.js r160 modules the viewer imports (from web/three_local), found by following imports
DIR/data/             house_meta.json (reference-photo cameras removed) and the model as base64 text parts
                      house.glb.b64.N.txt (the Artifact host serves no binary type but images, media and fonts)
DIR/ARTIFACT.json     publish manifest: page, files {published path: {from, contentType}}, sizes
Nothing cut from the listing photos goes into the bundle: the model's textures are procedural.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent
HOUSE = WEB.parent
TITLE = 'Farmhouse Exterior Model'
DESCRIPTION = 'A navigable 3-D reconstruction of a house exterior and its grounds, rebuilt from listing photos and video.'
B64_PART = 9_000_000          # characters per base64 text part (text files are limited to 16 MB)
TYPES = {'.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.txt': 'text/plain', '.html': 'text/html'}


def follow_imports(entry: Path, three_src: Path, seen: dict):
    """Copy list of three.js modules reachable from the viewer: {relative path under three/: source path}."""
    def visit(src: Path, rel: str):
        if rel in seen:
            return
        seen[rel] = src
        for m in re.finditer(r'''(?:from|import)\s*['"](\.{1,2}/[^'"]+)['"]''', src.read_text()):
            dep = (src.parent / m.group(1)).resolve()
            visit(dep, str(dep.relative_to(three_src.resolve())))
    for js in list((WEB / 'viewer').rglob('*.js')):
        for m in re.finditer(r'''from\s*['"]three/addons/([^'"]+)['"]''', js.read_text()):
            visit(three_src / 'examples' / 'jsm' / m.group(1), 'examples/jsm/' + m.group(1))
    return seen


def main():
    a = sys.argv[1:]
    out = Path(a[a.index('--out') + 1]) if '--out' in a else HOUSE / 'dist'
    if out.exists():
        shutil.rmtree(out)
    (out / 'data').mkdir(parents=True)
    shutil.copytree(WEB / 'viewer', out / 'viewer')
    three_src = WEB / 'three_local'
    mods = follow_imports(WEB / 'viewer' / 'main.js', three_src, {})
    (out / 'three' / 'build').mkdir(parents=True)
    shutil.copy(three_src / 'build' / 'three.module.min.js', out / 'three' / 'build' / 'three.module.min.js')
    for rel, src in mods.items():
        if rel.startswith('build/'):
            continue                                   # addons import 'three' through the import map
        dst = out / 'three' / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    # data: meta without the reference-photo cameras, model as base64 text parts
    meta = json.load(open(HOUSE / 'out' / 'house_meta.json'))
    meta.pop('cameras', None)
    json.dump(meta, open(out / 'data' / 'house_meta.json', 'w'), separators=(',', ':'))
    raw = (HOUSE / 'out' / meta.get('glb', 'house.glb')).read_bytes()
    text = base64.b64encode(raw).decode()
    step = B64_PART - B64_PART % 4
    parts = [text[i:i + step] for i in range(0, len(text), step)] or ['']
    assert base64.b64decode(''.join(parts)) == raw
    for i, p in enumerate(parts):
        (out / 'data' / f'house.glb.b64.{i}.txt').write_text(p)
    # the page
    src = (WEB / 'index.html').read_text()
    body = src[src.index('<body>') + 6:src.index('</body>')]
    body = re.sub(r'<script>window\.HOUSE_CONFIG = .*?</script>',
                  '<script>window.HOUSE_CONFIG = ' + json.dumps({'data': './data/', 'three': './three/', 'b64': {'house.glb': len(parts)},
                                                                  'threeBuild': 'build/three.module.min.js'}) + ';</script>', body, flags=re.S)
    page = ('<title>%s</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="stylesheet" href="viewer/viewer.css">\n' % TITLE) + body.strip() + '\n'
    (out / 'index.html').write_text(page)
    (out / '_local.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                                     '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                                     '</head><body>' + page + '</body></html>')
    files, total = {}, 0
    for f in sorted(out.rglob('*')):
        if f.is_file() and f.name not in ('index.html', '_local.html', 'ARTIFACT.json'):
            rel = str(f.relative_to(out))
            files[rel] = {'from': rel, 'contentType': TYPES.get(f.suffix, 'application/octet-stream'), 'bytes': f.stat().st_size}
            total += f.stat().st_size
    man = {'title': TITLE, 'description': DESCRIPTION, 'icon': 'house', 'page': 'index.html',
           'page_bytes': (out / 'index.html').stat().st_size, 'files': files, 'total_bytes': total}
    json.dump(man, open(out / 'ARTIFACT.json', 'w'), indent=1)
    print('bundle', out, '-', len(files), 'files, %.2f MB; model %.2f MB in %d base64 part(s)' % (total / 1e6, len(raw) / 1e6, len(parts)))
    big = [k for k, v in files.items() if v['bytes'] > 15_000_000]
    if big:
        print('TOO LARGE for one published file:', big)


if __name__ == '__main__':
    main()
