"""Close-out round 4 (8 Nov 2026), buildings track: manifest.json updates that a build does not write itself.

  - manifest.json#<group>.closeout_r4: the per-finding records of round 4 (out/buildings3d/c4/c4_manifest.json, written by
    this round; the builds keep the key since round 4: itb_manifest / dom_manifest / landside_manifest keep_renders);
  - #itb / #domestic .verification: re-read from out/buildings3d/{itb,domestic}_verify.json (the verify scripts were re-run
    after the builds when only checks changed - the vestibule door-surround allowance, the near-context back-face rays);
  - #tower.bytes / .verification: the tower was rebuilt with --no-manifest (build_tower.py rewrites the whole entry and would
    drop the hand-written close-out records): file sizes and the tower3d_verify summaries are patched in.
All under the manifest's flock (dom_manifest.merge). Run AFTER the builds:
    python3 tools/blender/c4_manifest.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import dom_manifest  # noqa: E402

OUT = os.path.join(ROOT, 'out', 'buildings3d')
DATA = os.path.join(ROOT, 'data', 'buildings3d')
C4 = os.path.join(OUT, 'c4', 'c4_manifest.json')


def itb_verification():
    p = os.path.join(OUT, 'itb_verify.json')
    if not os.path.exists(p): return None
    ver = json.load(open(p))
    key = [r for r in ver['checks'] if not r['ok']]
    return dict(tool='tools/blender/verify_itb.py', report='out/buildings3d/itb_verify.json (local)', n_checks=ver['n_checks'],
                n_fail=ver['n_fail'], failed=[r['check'] for r in key], tolerance=ver['tolerance'],
                checks=[{k: r[k] for k in ('check', 'model', 'drawing', 'dev', 'tol', 'ok', 'src')} for r in ver['checks']],
                plausibility=ver.get('plausibility'))


def main():
    rec = json.load(open(C4)) if os.path.exists(C4) else {}
    for key in ('domestic', 'itb', 'tower', 'landside'):
        def upd(old, key=key):
            old = old or {}
            if key in rec:
                old['closeout_r4'] = rec[key]
            if key == 'itb':
                v = itb_verification()
                if v is not None: old['verification'] = v
                old['bytes'] = os.path.getsize(os.path.join(DATA, 'itb.glb'))
            if key == 'domestic':
                p_ = os.path.join(OUT, 'domestic_verify.json')
                if os.path.exists(p_):
                    ver = json.load(open(p_))
                    old['verification'] = dict(tool='tools/blender/verify_domestic.py', report='out/buildings3d/domestic_verify.json (local)',
                                               n_checks=ver['n_checks'], n_fail=ver['n_fail'], failed=[r['check'] for r in ver['checks'] if not r['ok']],
                                               tolerance=ver['tolerance'],
                                               checks=[{k: r[k] for k in ('group', 'check', 'model', 'drawing', 'dev', 'tol', 'ok', 'src')} for r in ver['checks']],
                                               plausibility=ver.get('plausibility'), heights=ver.get('heights'))
            if key == 'tower':
                old['bytes'] = {'F1': os.path.getsize(os.path.join(DATA, 'tower_f1.glb')), 'F2': os.path.getsize(os.path.join(DATA, 'tower.glb')),
                                'lod2_only': os.path.getsize(os.path.join(DATA, 'tower_lod2.glb'))}
                tv = os.path.join(OUT, 'tower_verify.json')
                if os.path.exists(tv):
                    T = json.load(open(tv))
                    v = old.setdefault('verification', {})
                    for fam in ('F1', 'F2'):
                        if fam in T and T[fam].get('summary'): v[fam] = T[fam]['summary']
                    gv = {fam: T[fam].get('gltf_validator') for fam in ('F1', 'F2') if fam in T and T[fam].get('gltf_validator')}
                    if gv: v['gltf_validator'] = gv
            return old
        dom_manifest.merge(upd, key=key)
        print('manifest.json#%s: closeout_r4 %s' % (key, len(rec.get(key, [])) if key in rec else 'unchanged'))


if __name__ == '__main__':
    main()
