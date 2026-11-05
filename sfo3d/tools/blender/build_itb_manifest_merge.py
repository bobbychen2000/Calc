"""Adds the render list of tools/blender/render_itb.py to the "itb" key of data/buildings3d/manifest.json (file lock shared with
build_itb.py; no bpy needed)."""
import datetime
import fcntl
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PATH = os.path.join(ROOT, 'data', 'buildings3d', 'manifest.json')
VIEWS = {
    'west': 'orthographic west elevation, BI-02 view 1 frame; itb_cmp_west.png overlays the BI-02 lines',
    'i4': 'landside perspective approximating photo i4 (DimiCalifornia 2005, PD); itb_cmp_i4.png side by side',
    'i3': 'curb close-up approximating photo i3 (E. K. Joseph 2017, CC BY 2.0); itb_cmp_i3.png side by side',
    'a2g': 'photo a2 view (camera solved, review r1): the BA-G NNE face; itb_cmp_a2g.png side by side',
    'baa': 'aerial from the ESE over Boarding Area A (BI-04 view 2); no reference photo of BA-A (a2 shows BA-G)',
    'bag': 'aerial from the NNE at Boarding Area G with the pod-3 end box (photo d2 direction, BI-04 view 1)',
    'plan': 'orthographic roof plan, north up (BI-01 view 2)',
}


def add_renders(done, args):
    lst = []
    for v, r in done.items():
        if v not in VIEWS: continue
        lst.append(dict(view=v, file='out/buildings3d/itb_%s.png' % v, what=VIEWS[v], samples=args.samples,
                        note='local (out/ is gitignored); comparison sheets with photo pixels stay local'))
    with open(PATH + '.lock', 'a') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        cur = json.load(open(PATH)) if os.path.exists(PATH) else {}
        e = cur.get('itb') or {}
        old = {r['view']: r for r in e.get('renders', [])}
        for r in lst: old[r['view']] = r
        e['renders'] = list(old.values())
        chk = os.path.join(ROOT, 'out', 'buildings3d', 'itb_render_check.json')
        if 'west' in done and os.path.exists(chk):
            c = json.load(open(chk))
            e['render_check'] = {k: c[k] for k in ('px_per_m', 'n', 'wing_max_abs_dev_m', 'wing_mean_dev_m', 'centre_max_abs_dev_m', 'note')}
        e['renders_updated'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
        cur['itb'] = e
        tmp = PATH + '.itb.tmp'
        json.dump(cur, open(tmp, 'w'), indent=1)
        os.replace(tmp, PATH)
        fcntl.flock(lf, fcntl.LOCK_UN)
    try:
        os.remove(PATH + '.lock')
    except OSError:
        pass


def add_verification(path=os.path.join(ROOT, 'out', 'buildings3d', 'itb_verify.json')):
    """refresh the verification block of the "itb" entry from a re-run of tools/blender/verify_itb.py."""
    ver = json.load(open(path))
    with open(PATH + '.lock', 'a') as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        cur = json.load(open(PATH))
        e = cur['itb']
        e['verification'].update(n_checks=ver['n_checks'], n_fail=ver['n_fail'], failed=[r['check'] for r in ver['checks'] if not r['ok']],
                                 checks=[{k: r[k] for k in ('check', 'model', 'drawing', 'dev', 'tol', 'ok', 'src')} for r in ver['checks']],
                                 plausibility=ver.get('plausibility'))
        tmp = PATH + '.itb.tmp'
        json.dump(cur, open(tmp, 'w'), indent=1)
        os.replace(tmp, PATH)
        fcntl.flock(lf, fcntl.LOCK_UN)
    try:
        os.remove(PATH + '.lock')
    except OSError:
        pass


if __name__ == '__main__':
    add_verification()
