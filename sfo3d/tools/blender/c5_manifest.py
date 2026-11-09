"""Close-out round 5 (9 Nov 2026), buildings track: manifest.json updates that a build does not write itself.

  - manifest.json#<group>.closeout_r5: the per-finding records of round 5 (out/buildings3d/c5/c5_manifest.json, written by
    this round; the builds keep the key: itb_manifest / dom_manifest / landside_manifest keep_renders);
  - #itb / #domestic .verification: re-read from out/buildings3d/{itb,domestic}_verify.json (verify_itb / verify_domestic were
    re-run after the builds against a fresh tools/blender/app_bridges.json dump - the runtime track keeps editing
    js/live/gates.js, so the dump's input hash moves although its content does not);
  - #landside .verification (incl. plausibility.airtrain_vs_buildings_lod0 / _lod2): re-read from out/buildings3d/landside_verify.json;
  - #roadways / #integration .closeout_r5: the per-finding records of the integration residuals (those two entries are written
    whole by build_roadways.py / b3d_integrate.py, so this runs after their last run).
All under the manifest's flock (dom_manifest.merge). Run AFTER the builds and the verify re-runs:
    python3 tools/blender/c5_manifest.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import dom_manifest  # noqa: E402
import c4_manifest  # noqa: E402

OUT = os.path.join(ROOT, 'out', 'buildings3d')
DATA = os.path.join(ROOT, 'data', 'buildings3d')
C5 = os.path.join(OUT, 'c5', 'c5_manifest.json')


def main():
    rec = json.load(open(C5)) if os.path.exists(C5) else {}
    for key in ('domestic', 'itb', 'landside', 'roadways', 'integration'):
        if key in ('roadways', 'integration') and key not in rec: continue   # (written whole by build_roadways / b3d_integrate: run after them)
        def upd(old, key=key):
            old = old or {}
            if key in rec:
                old['closeout_r5'] = rec[key]
            if key == 'itb':
                v = c4_manifest.itb_verification()
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
            if key == 'landside':
                p_ = os.path.join(OUT, 'landside_verify.json')
                if os.path.exists(p_):
                    ver = json.load(open(p_))   # the same summary landside_manifest.entry writes
                    old['verification'] = dict(tool='tools/blender/verify_landside.py', report='out/buildings3d/landside_verify.json (local)',
                                               n_checks=ver['n_checks'], n_fail=ver['n_fail'], failed=[r['check'] for r in ver['checks'] if not r['ok']],
                                               tolerance='0.5 m or 2 % unless stated', checks=ver['checks'], plans=ver.get('plans'),
                                               plausibility=ver.get('plausibility'))
            return old
        dom_manifest.merge(upd, key=key)
        print('manifest.json#%s: closeout_r5 %s' % (key, len(rec.get(key, [])) if key in rec else 'unchanged'))


if __name__ == '__main__':
    main()
