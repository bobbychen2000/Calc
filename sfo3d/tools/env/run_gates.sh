#!/bin/sh
# Environment core gates (docs/research/environment_spec.md §11.3, steps 0-1; docs/research/environment_impl.md):
# A-FIX, A-WX, A-SUN (unit), A-CLK + the relay smoke test and the reference Python decoder tests. No GPU, no network.
# Regenerate the inputs first when the sources change:
#   python3 tools/env/build_lighting_spec.py && python3 tools/env/build_metar_golden.py && python3 tools/env/build_env_presets_js.py
cd "$(dirname "$0")/../.." || exit 1
rc=0
run() { name=$1; shift; out=$("$@" 2>&1); r=$?; echo "$out" | tail -1 | sed "s/^/$name: /"; [ $r -ne 0 ] && { echo "$out" | grep -E '^FAIL' | head -20; rc=1; }; }
run "python decoder (38 tests)" python3 tools/env/test_metar_decode.py
run "A-SUN ephemeris (32 checks)" node --no-warnings tools/env/test_ephemeris.mjs
run "A-FIX fixtures" node --no-warnings tools/env/test_fixtures.mjs
run "A-WX JS decoder" node --no-warnings tools/env/test_metar_js.mjs
run "A-CLK + EnvState presets" node --no-warnings tools/env/test_env_state.mjs
run "relay smoke (A-CLK relay)" python3 tools/env/test_relay_wx.py
exit $rc
