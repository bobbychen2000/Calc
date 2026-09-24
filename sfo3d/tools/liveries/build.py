#!/usr/bin/env python3
"""Bake the brand liveries into every model / type they fly at SFO, and write the manifest.

Jobs: for each livery in tools/liveries/liveries.py, the ICAO types in its `types` list (the brand's SFO fleet: DataSF
SFO landings Aug 2025 - Jul 2026 by published/operating airline and model, docs/research/liveries.md §1.1, plus types
seen by our recorder) are mapped to TYPES keys (js/aircraft/types.js ICAO_TYPES) and models (js/aircraft/fit.js
TYPE_MODEL). Types rendered on the same model with the same fuselage plugs share one bake (painted on the most common of
them); types without an imported model (777 family) use the procedural airframe and its runtime colours instead.

Output: data/liveries/<BRAND>/<model>[@<type>]-{hi,mid,lo}.webp (2048 / 1024 / 512 px), data/liveries/manifest.json
(read by js/three/aircraft.js LiveryLibrary: entries[].brand/model/file) and data/liveries/manifest.js (same data, ES
module, js/aircraft/liveries.js). Models must be atlased first (tools/liveries/atlas.py).

Usage: python3 tools/liveries/build.py [BRAND ...] [--models b738,a320] [--no-manifest-only] [--preview DIR]
"""
import argparse, collections, json, os, sys, time
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import liveries
from paint import Canvas

SIZES = dict(hi=2048, mid=1024, lo=512)
QUALITY = dict(hi=88, mid=86, lo=84)


def plug_sig(A, t):
    f = A['types'][t]['fit']; p = f and f['plugs']
    return (round(p['d1'], 2), round(p['d2'], 2)) if p else None


def jobs(codes, only_models=None):
    A = common.app()
    out = collections.defaultdict(lambda: collections.defaultdict(list))   # model -> (plug sig) -> [(brand, type)]
    for code in codes:
        L = liveries.LIVERIES[code]
        for icao in L.get('types', []):
            t = A['icao'].get(icao)
            if not t: print(f'  {code}: {icao} not mapped to a type (marker)'); continue
            m = A['typeModel'].get(t)
            if not m: continue                        # procedural airframe (777 family)
            if only_models and m not in only_models: continue
            out[m][plug_sig(A, t)].append((code, t))
    return out


def save_all(img, base):
    files = {}
    os.makedirs(os.path.dirname(base), exist_ok=True)
    for res, n in SIZES.items():
        im = img if img.size[0] == n else img.resize((n, n), Image.LANCZOS)
        fn = f'{base}-{res}.webp'
        im.save(fn, 'WEBP', quality=QUALITY[res], method=6, alpha_quality=90)
        files[res] = os.path.relpath(fn, common.LIV).replace(os.sep, '/')
    return files


def group_rep(A, m, lst):
    types = sorted({t for _, t in lst}); return A['base'][m] if A['base'][m] in types else types[0]


def bake_jobs(codes, only, preview_dir=None):
    A = common.app()
    J = jobs(codes, only)
    for m, groups in J.items():
        path = os.path.join(common.MD, m + '.sfom')
        for sig, lst in groups.items():
            rep = group_rep(A, m, lst)
            t0 = time.time()
            c = Canvas(path, rep, SIZES['hi'])
            print(f'== {m} as {rep} (plugs {sig}): {len(set(b for b, _ in lst))} brands, canvas {time.time() - t0:.0f} s', flush=True)
            for code in sorted({b for b, _ in lst}):
                t1 = time.time()
                c.reset()
                liveries.LIVERIES[code]['paint'](c)
                img = c.finish()
                name = m if sig is None else f'{m}@{rep}'
                files = save_all(img, os.path.join(common.LIV, code, name))
                if preview_dir:
                    import preview
                    mm, P = preview.load_for(path, rep)
                    os.makedirs(preview_dir, exist_ok=True)
                    preview.sheet(mm, P, ['side', '34', 'stbd34', 'rear34'], img, 900, 420, title=f'{code} {name}').save(os.path.join(preview_dir, f'{code}_{name}.png'))
                print(f'   {code:6s} -> {files["hi"]} ({os.path.getsize(os.path.join(common.LIV, files["hi"])) // 1024} KB hi) {time.time() - t1:.0f} s', flush=True)


def write_manifest():
    """entries from the job table and the files present on disk (so several bake processes can run in parallel)"""
    A = common.app()
    J = jobs(list(liveries.LIVERIES))
    ent = {}
    for m, groups in J.items():
        for sig, lst in groups.items():
            rep = group_rep(A, m, lst)
            name = m if sig is None else f'{m}@{rep}'
            for code in sorted({b for b, _ in lst}):
                files = {r: f'{code}/{name}-{r}.webp' for r in SIZES}
                if not all(os.path.exists(os.path.join(common.LIV, f)) for f in files.values()): continue
                gtypes = sorted({t for b, t in lst if b == code} | {rep})
                rec = dict(types=gtypes, files=files, file=files['mid'], painted_as=rep,
                           bytes={r: os.path.getsize(os.path.join(common.LIV, f)) for r, f in files.items()})
                e = ent.setdefault((code, m), dict(brand=code, model=m, variants=[]))
                if sig is None: e.update(rec)
                else: e['variants'].append(rec)
    for e in ent.values():
        if not e.get('files') and e.get('variants'):
            v = e['variants'].pop(0); e.update(v)
    brands = {}
    for code, L in liveries.LIVERIES.items():
        brands[code] = dict(name=L['name'], livery=L['version'], since=L.get('since'), refs=L['refs'],
                            colors={k: v for k, v in L.get('colors', {}).items()}, status=L.get('status', ''),
                            types=L.get('types', []))
    out = dict(version=1, generator='tools/liveries/build.py', sizes=SIZES,
               note='Airline names, logos and liveries are trademarks of their owners; re-drawn for a non-commercial depiction.',
               entries=sorted(ent.values(), key=lambda e: (e['brand'], e['model'])), brands=brands)
    os.makedirs(common.LIV, exist_ok=True)
    json.dump(out, open(os.path.join(common.LIV, 'manifest.json'), 'w'), indent=1, ensure_ascii=False)
    with open(os.path.join(common.LIV, 'manifest.js'), 'w') as f:
        f.write('// Generated by tools/liveries/build.py - do not edit. Brand x model livery textures (see js/aircraft/liveries.js).\n')
        f.write('export const LIVERY_MANIFEST = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n')
    tot = collections.Counter(); n = 0
    for e in out['entries']:
        for v in [e] + e.get('variants', []):
            n += 1
            for r, b in (v.get('bytes') or {}).items(): tot[r] += b
    print('manifest:', len(out['entries']), 'entries,', n, 'textures;', ', '.join(f'{r} {b / 1e6:.1f} MB' for r, b in tot.items()))
    return out


def snapshot_files(res='lo'):
    """livery files the recorded snapshot (data/snapshot.js) needs, via the app's own brand lookup (node)"""
    import subprocess
    js = r"""
import { SNAPSHOT } from './data/snapshot.js';
import { liveryForAirline } from './js/live/lookup.js';
import { typeForIcao } from './js/aircraft/fit.js';
import { liveryTextureFor } from './js/aircraft/liveries.js';
const out = new Set();
for (const a of SNAPSHOT.ac) { const al = (a.flight || '').trim().slice(0, 3); const L = liveryForAirline(/^[A-Z]{3}$/.test(al) ? al : null, a.r, a.hex, a.t);
  const m = typeForIcao(a.t); if (!m || !m.m || !L.brand) continue; const f = liveryTextureFor(L.brand, m.m, m.t, '""" + res + r"""'); if (f) out.add(f.key); }
console.log(JSON.stringify([...out]));"""
    r = subprocess.run(['node', '--no-warnings', '--input-type=module', '-e', js], cwd=common.ROOT, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('brands', nargs='*'); ap.add_argument('--models'); ap.add_argument('--preview')
    ap.add_argument('--manifest-only', action='store_true'); ap.add_argument('--no-manifest', action='store_true')
    ap.add_argument('--list-snapshot', action='store_true')
    a = ap.parse_args()
    if a.list_snapshot:
        fs = snapshot_files('lo'); tot = sum(os.path.getsize(os.path.join(common.LIV, f)) for f in fs)
        print('\n'.join('data/liveries/' + f for f in fs)); print(f'# {len(fs)} files, {tot / 1e6:.2f} MB'); return
    codes = a.brands or [c for c in liveries.LIVERIES if liveries.LIVERIES[c].get('types')]
    only = set(a.models.split(',')) if a.models else None
    if not a.manifest_only: bake_jobs(codes, only, a.preview)
    if not a.no_manifest: write_manifest()


if __name__ == '__main__':
    main()
