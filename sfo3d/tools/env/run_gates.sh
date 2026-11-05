#!/bin/sh
# Environment core gates (docs/research/environment_spec.md §11.3, steps 0-1; docs/research/environment_impl.md):
# A-FIX, A-WX, A-SUN (unit), A-CLK + the relay smoke test and the reference Python decoder tests; step 2: A-CTL,
# A-VIS1, A-PAPI1, A-NAV1, A-FLASH1; steps 3-4: the numeric halves of A-SUN (render), A-MOON, A-EXP, A-FOG, A-CLD,
# A-RAIN, A-WET, A-LTG (tools/env/test_sky.mjs). No GPU, no network.
# Regenerate the inputs first when the sources change:
#   python3 tools/env/build_lighting_spec.py && python3 tools/env/build_metar_golden.py && python3 tools/env/build_env_presets_js.py
cd "$(dirname "$0")/../.." || exit 1
rc=0
run() { name=$1; shift; out=$("$@" 2>&1); r=$?; echo "$out" | tail -1 | sed "s/^/$name: /"; [ $r -ne 0 ] && { echo "$out" | grep -E '^FAIL' | head -20; rc=1; }; }
run "python decoder (39 tests)" python3 tools/env/test_metar_decode.py
run "A-SUN ephemeris (32 checks)" node --no-warnings tools/env/test_ephemeris.mjs
run "A-FIX fixtures" node --no-warnings tools/env/test_fixtures.mjs
run "A-WX JS decoder" node --no-warnings tools/env/test_metar_js.mjs
run "A-CLK + EnvState presets" node --no-warnings tools/env/test_env_state.mjs
run "TAF forecast beyond the latest METAR (spec 3.3)" node --no-warnings tools/env/test_taf.mjs
run "relay smoke (A-CLK relay)" python3 tools/env/test_relay_wx.py
# step 2 (lighting controller, photometry, aircraft lights)
run "A-CTL controller (14 presets x 2 paths + table edges)" node --no-warnings tools/env/test_controller.mjs
run "A-VIS1, A-PAPI1, A-NAV1, A-FLASH1" node --no-warnings tools/env/test_lights.mjs
# steps 3-4 (sky, fog, clouds, exposure, rain, wetness, lightning: unit halves on the shader mirrors, js/env/atmo/)
run "A-SUN render, A-MOON, A-EXP, A-FOG, A-CLD, A-RAIN, A-WET, A-LTG, A-WIND (unit)" node --no-warnings tools/env/test_sky.mjs
exit $rc
