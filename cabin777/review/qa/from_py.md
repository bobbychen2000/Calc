# Items from the PY worker

## To lighting + integration (`test/qa.js`)

1. **`q13_pyFront` cannot be rated** (py_r3 high issue): its camera sits in the J/PY bulkhead / curtain, so no PY seat
   front is visible. The monuments worker's `__rel('25C', 0.35, 1.75, -0.72, ...)` also works. The PY worker rated with
   a camera over the right aisle just aft of the bulkhead, looking aft toward the centre block. Its framing is closest to
   py_37302 (H/K pair and windows on the left, the centre block large on the right):
   `q13_pyFront: [\`__rel('25G', 0.52, 1.95, -0.35, Math.PI-0.35, -0.42)\`, ['py_37302'], 'PY cabin from the front']`
2. Optional: add a PY seat-back view (real photos ref/web/py san_05 / san_13 / alv_03):
   `q13b_pyBacks: [\`__rel('26H', 0.1, 1.45, 1.25, 0.05, -0.3)\`, ['py_37304'], 'PY seat backs, screens, pockets']`.

## To monuments (`src/10_mono.js`)

- Row 25 faces the J/PY bulkhead, which carries wall-mounted monitors and literature pockets (real photos ref/web/py
  alv_14 / alv_15 / san_03, and ANA py_37303). The monitors are already modelled (`monitor: true`); please check them
  against alv_14 (two monitors per seat pair at about eye height, with grey pockets below).

## Wave 3 (w5)

3. **To integration (`src/06_atlas.js`), low:** both w5 raters mark the two white seat-back placards under the PY screen
   as blank. Real placards (san_26, py_37304) are ~0.12 x 0.022 m, white with 2 small grey lines (JP + EN) and a pictogram
   at the left. Please add an atlas rect `pyPlacard` (2 lines of ~#707070 text on #e8e8e6). `09b_py.js` will then use
   `atlasUV('pyPlacard')` on the two quads at `on(0.60, 0.0115, +-0.113)` (currently plain `#e8e8e6`).
4. **To integration (`test/qa.js`), repeat of item 2:** still no rear-facing PY view, so the screen frame, the literature
   bucket, the footrest and the bottle bins are only rated in the studio. Suggested
   `q13b_pyBacks: [\`__rel('26H', 0.1, 1.45, 1.25, 0.05, -0.3)\`, ['py_37304'], 'PY seat backs']` (pairs with san_26).
5. **To lighting, low (w5 rater B):** q14 shows a hard-edged bright quadrilateral sun patch on the window-seat back;
   please soften the window sun footprint on seats (same as the q04 item in from_integration.md).

## Wave 3b (w11-w14)

6. **To lighting, low (w12-w14 A + B):** q14 still shows the bright rhombus sun patch on the far window-seat back (26B),
   and in q13 the PY cloth reads cobalt and the navy flaps royal blue. A puts that at about half exposure. The studio renders
   (neutral) match the photos' saturation (cushion S 0.16 vs 0.18), so no PY material was retuned for it.
7. **To integration (`src/06_atlas.js`), repeat of item 3:** the placards are still blank. Also, the new literature-pocket
   leaflet (`09b_py.js`, `gQuad(0.16, 0.07)` in the pocket mouth) could take an atlas rect `pyCard` (white, purple
   '777-300' header band, san_26 / b_san_20).
8. **Shared-file note:** PY added detail layer 31 `pyEar` in `03_tex.js` (LAYER, N_LAYERS 32, PHOTO_LAYERS / PHOTO_GAIN /
   PHOTO_ENC / LAYER_PARAMS, procedural fallback `L[31] = L[17]`), commit e3268a7. The next new layer is 32.
