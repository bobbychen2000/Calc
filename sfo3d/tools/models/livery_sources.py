#!/usr/bin/env python3
"""Which openly-licensed livery textures fit the UV layouts of our converted aircraft models?

Our .sfom models (tools/convert_models.py) come from Ysurac/FlightAirMap-3dmodels (FAM) @0906d9b, whose glTF files were
exported from FlightGear aircraft (FGMEMBERS). The FAM repo pins each FlightGear source as a git submodule commit
(gitlink without .gitmodules). A FlightGear livery is a texture painted for one model's UV layout, so a livery fits our
model iff it was made for the same FlightGear model file that FAM exported.

Method (per model key):
  1. read the images embedded in the FAM .glb (the default livery that FAM baked in);
  2. find the FlightGear repo + pinned commit from the FAM gitlink (git ls-tree), and search that commit for a texture with
     the same file name; download it (blobless clone fetches blobs on demand) and compare pixels (64x64 grey, mean
     absolute difference; < 0.03 = same image). A match proves the UV layout is the FlightGear one;
  3. list every livery texture in the matched texture's directory with the same pixel size at the pinned commit
     (same model, same UV), and the liveries added at HEAD if the model geometry (*.ac) did not change since the pin;
  4. report the licence file of the FlightGear repo.

Inputs: refs/cache/src/fam3d (git clone https://github.com/Ysurac/FlightAirMap-3dmodels)
        refs/cache/src/fg/<repo> (git clone --filter=blob:none --no-checkout https://github.com/FGMEMBERS/<repo>)
Output: tools/models/out/livery_sources.json and a summary on stdout.
Usage:  python3 tools/models/livery_sources.py [--airlines UAL,SKW,...]
"""
import argparse, io, json, os, re, subprocess, sys
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
FAM = os.path.join(ROOT, 'refs', 'cache', 'src', 'fam3d')
FG = os.path.join(ROOT, 'refs', 'cache', 'src', 'fg')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'livery_sources.json')
sys.path.insert(0, os.path.join(ROOT, 'tools'))

# FAM directory -> (FAM submodule path, FGMEMBERS repo name)
SUBMODULE = {'a320': ('a320/A320-family', 'A320-family'), 'a333': ('a333/A330-300', 'A330-300'), 'a350': ('a350/A350XWB', 'A350XWB'),
             'a380': ('a380/A380-omega', 'A380-omega'), 'b744': ('b744/747-400', '747-400'), 'b748': ('b748/747-8i', '747-8i'),
             'b752': ('b752/757-200', '757-200'), 'b767': ('b767/767', '767'), 'b788': ('b788/787-8', '787-8'),
             'bcs1': ('bcs1/CSeries', 'CSeries'), 'crj2': ('crj2/CRJ-200', 'CRJ-200'), 'crj9': ('crj9/CRJ700-family', 'CRJ700-family'),
             'e190': ('e190/E-jet-family', 'E-jet-family'), 'md11': ('md11/MD-11', 'MD-11')}
# ICAO airline codes seen at SFO (DataSF landings Aug 2025 - Jul 2026, published + operating airlines) -> livery file name hints
SFO_AIRLINES = ['UAL', 'UAX', 'SKW', 'ASA', 'QXE', 'HAL', 'DAL', 'AAL', 'SWA', 'JBU', 'FFT', 'MXY', 'SCX', 'ACA', 'JZA', 'WJA', 'POE', 'EVA', 'AMX',
                'CPA', 'TAI', 'AVA', 'SIA', 'JAL', 'ANA', 'BAW', 'DLH', 'AIC', 'THY', 'VIR', 'AFR', 'CMP', 'TZP', 'KAL', 'SJX', 'PAL', 'CAL',
                'UAE', 'SWR', 'AAR', 'KLM', 'EIN', 'FBU', 'SAS', 'ANZ', 'QTR', 'TAP', 'APZ', 'FLE', 'ITY', 'CSN', 'HVN', 'FJI', 'CFG', 'CES',
                'QFA', 'IBE', 'CCA', 'LOT', 'LVL']


def git(repo, *args, binary=False):
    r = subprocess.run(['git', '-C', repo] + list(args), capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr.decode()[:300])
    return r.stdout if binary else r.stdout.decode()


def thumb(data):
    im = Image.open(io.BytesIO(data)).convert('L').resize((64, 64), Image.BILINEAR)
    return np.asarray(im, dtype=np.float32) / 255, Image.open(io.BytesIO(data)).size


def glb_images(path):
    from convert_models import load_glb
    js, blob = load_glb(path)
    out = []
    for i, im in enumerate(js.get('images', [])):
        bv = js['bufferViews'][im['bufferView']]
        d = blob[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
        out.append(dict(name=im.get('name') or f'image{i}', data=d))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--airlines', default=','.join(SFO_AIRLINES)); a = ap.parse_args()
    want = set(a.airlines.split(','))
    import convert_models as cm
    res = {}
    for key, (src, cfg) in cm.MODELS.items():
        rel = os.path.relpath(src, cm.FAM); famdir = rel.split('/')[0]
        sub, repo = SUBMODULE[famdir]; rp = os.path.join(FG, repo)
        pin = git(FAM, 'ls-tree', 'HEAD', sub).split()[2]
        files = git(rp, 'ls-tree', '-r', pin).splitlines()   # no -l: sizes would make a blobless clone fetch every blob
        imgs = {}
        for l in files:
            meta, path = l.split('\t')
            if re.search(r'\.(png|jpg|jpeg|dds|rgb)$', path, re.I): imgs[path] = meta.split()[2]
        lic = [p.split('\t')[1] for p in files if re.search(r'(^|/)(COPYING|LICENSE|License|LICENCE)[^/]*$', p.split('\t')[1])]
        ac_changed = git(rp, 'diff', '--stat', pin, 'HEAD', '--', '*.ac').strip()
        entry = dict(fam_source=rel, fg_repo=f'https://github.com/FGMEMBERS/{repo}', fg_pin=pin, licence_files=lic,
                     ac_changed_since_pin=bool(ac_changed), textures=[])
        for im in glb_images(os.path.join(FAM, rel)):
            t_src, size_src = thumb(im['data'])
            base = os.path.basename(im['name']) if im['name'] else ''
            cands = [p for p in imgs if base and os.path.basename(p).lower() == base.lower()]
            best = None
            for p in cands[:6]:
                t, sz = thumb(git(rp, 'show', f'{pin}:{p}', binary=True))
                d = float(np.abs(t - t_src).mean())
                if not best or d < best[1]: best = (p, d, sz)
            tex = dict(embedded=im['name'], size=size_src, match=best and dict(path=best[0], mad=round(best[1], 4), size=best[2]))
            if best and best[1] < 0.03 and re.search(r'liver', best[0], re.I):
                d0 = os.path.dirname(best[0])
                same_dir = sorted(p for p in imgs if os.path.dirname(p) == d0)
                tex['liveries_same_dir'] = same_dir
                tex['sfo_candidates'] = [p for p in same_dir if any(re.search(r'(^|[^A-Z])' + c + r'([^A-Z]|$)', os.path.basename(p).upper()) for c in want)]
                if not ac_changed:
                    head = [l.split('\t')[1] for l in git(rp, 'ls-tree', '-r', 'HEAD', '--', d0).splitlines()]
                    tex['added_at_head'] = sorted(set(p for p in head if re.search(r'\.(png|jpg|dds)$', p, re.I)) - set(same_dir))
            entry['textures'].append(tex)
        res[key] = entry
        ok = [t for t in entry['textures'] if t.get('liveries_same_dir')]
        sys.stdout.flush()
        print(f"{key:5s} {repo:14s} pin {pin[:8]} licence {lic} ac-changed-since-pin={bool(ac_changed)}")
        for t in entry['textures']:
            m = t['match']
            print(f"   {t['embedded']:28s} {str(t['size']):12s} -> " + (f"{m['path']} mad={m['mad']}" if m else 'no same-name texture in FG repo'))
            if t.get('sfo_candidates'): print('      SFO airline liveries in the same UV:', [os.path.basename(p) for p in t['sfo_candidates']])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, 'w'), indent=1)
    print('->', os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
