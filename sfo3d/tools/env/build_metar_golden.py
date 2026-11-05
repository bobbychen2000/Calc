#!/usr/bin/env python3
"""Golden vectors for the JS METAR/TAF port (js/env/wx/metar.js), gate A-WX of docs/research/environment_spec.md.

Runs the reference unit tests (tools/env/test_metar_decode.py: 38 tests on 58 real KSFO reports + FAA coding examples)
with metar_decode's public functions wrapped, and records every call the tests make (arguments + result). Adds, for
each of the 58 fixture reports and the 14 spec presets (tools/env/fixtures/env_presets.json), decode_metar with and
without a reference date and render_params by day and by night. The JS test (tools/env/test_metar_js.mjs) replays all
calls and requires deep-equal results (numbers equal within 1e-9 relative; Python tuples = JS arrays).

Run: python3 tools/env/build_metar_golden.py   -> tools/env/fixtures/metar_golden.json
"""
import copy, json, os, sys, unittest
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import metar_decode as M          # noqa: E402
import test_metar_decode as T     # noqa: E402  (same module object M inside: test imports `metar_decode as M`)

CALLS = []


def _ser(v):
    if isinstance(v, datetime):
        return {'__datetime__': v.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z') if v.tzinfo else v.isoformat() + 'Z', 'tz': bool(v.tzinfo)}
    return v


def wrap(name):
    fn = getattr(M, name)

    def w(*a, **kw):
        args = [copy.deepcopy(_ser(x)) for x in a]
        kws = {k: copy.deepcopy(_ser(v)) for k, v in kw.items()}
        r = fn(*a, **kw)
        CALLS.append({'fn': name, 'args': args, 'kwargs': kws, 'result': copy.deepcopy(r), 'from': 'unittest'})
        return r
    return w


def main():
    names = ('decode_metar', 'decode_taf', 'render_params', 'extinction_from_visibility')
    orig = {n: getattr(M, n) for n in names}
    for n in names:
        setattr(M, n, wrap(n))
    suite = unittest.defaultTestLoader.loadTestsFromModule(T)
    res = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w')).run(suite)
    for n in names:
        setattr(M, n, orig[n])
    if not res.wasSuccessful():
        sys.exit('reference tests failed - golden not written')
    n_tests = res.testsRun
    # every fixture report and preset: decode with / without ref, render by day / night
    extra = []
    REF = T.REF
    reports = [(l, REF) for l in T.RECENT] + [(line, datetime.strptime(valid, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)) for valid, line in T.ARCHIVE]
    presets = json.load(open(os.path.join(HERE, 'fixtures', 'env_presets.json')))['presets']
    for p in presets:
        raw = p['metar'] if p['metar'].startswith(('METAR', 'SPECI')) else 'METAR ' + p['metar']
        reports.append((raw, datetime.strptime(p['time_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)))
    for raw, ref in reports:
        d0 = M.decode_metar(raw)
        d1 = M.decode_metar(raw, ref)
        extra.append({'fn': 'decode_metar', 'args': [raw], 'kwargs': {}, 'result': d0, 'from': 'fixture'})
        extra.append({'fn': 'decode_metar', 'args': [raw, _ser(ref)], 'kwargs': {}, 'result': d1, 'from': 'fixture'})
        for night in (False, True):
            extra.append({'fn': 'render_params', 'args': [copy.deepcopy(d1)], 'kwargs': {'night': night}, 'result': M.render_params(d1, night=night), 'from': 'fixture'})
    out = {'schema': 'sfo3d.metar_golden.v1', 'generator': 'tools/env/build_metar_golden.py', 'reference': 'tools/env/metar_decode.py',
           'tests_run': n_tests, 'fixture_reports': len(T.RECENT) + len(T.ARCHIVE), 'preset_reports': len(presets),
           'calls': CALLS + extra}
    path = os.path.join(HERE, 'fixtures', 'metar_golden.json')
    with open(path, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print('reference tests run: %d (all passed); calls recorded: %d unittest + %d fixture -> %s (%d bytes)'
          % (n_tests, len(CALLS), len(extra), path, os.path.getsize(path)))


if __name__ == '__main__':
    main()
