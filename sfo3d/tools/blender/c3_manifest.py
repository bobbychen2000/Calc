"""Close-out round 3 (6 Nov 2026), buildings track: merge the per-finding dispositions into manifest.json#domestic / #itb /
#tower as `closeout_r3` (the landside group writes its own from tools/blender/landside_manifest.CLOSEOUT_R3 at build time).
Run AFTER the group builds (build_domestic.py / build_itb.py rewrite their entries; this adds one key under the manifest's
flock, dom_manifest.merge). Evidence numbers: out/buildings3d/c3/*.log, docs/research/buildings3d.md "Close-out round 3".

    python3 tools/blender/c3_manifest.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dom_manifest  # noqa: E402

C3 = os.path.join(HERE, '..', '..', 'out', 'buildings3d', 'c3', 'c3_manifest.json')   # the records (written by this round)
# close-out round 3, fix round 2 (verifier v1-v10): records per group -> manifest.json#<group>.closeout_r3_fix2 (the landside group
# writes its own from landside_manifest.CLOSEOUT_R3_FIX2 at build time; the builds keep both keys since fix 2)
C3F2 = os.path.join(HERE, '..', '..', 'out', 'buildings3d', 'c3f2', 'c3f2_manifest.json')


def main():
    for path, field in ((C3, 'closeout_r3'), (C3F2, 'closeout_r3_fix2')):
        if not os.path.exists(path): continue
        rec = json.load(open(path))
        for key in ('domestic', 'itb', 'tower', 'landside'):
            if key not in rec: continue

            def upd(old, items=rec[key], field=field):
                old = old or {}
                old[field] = items
                return old
            dom_manifest.merge(upd, key=key)
            print('manifest.json#%s.%s: %d records' % (key, field, len(rec[key])))


if __name__ == '__main__':
    main()
