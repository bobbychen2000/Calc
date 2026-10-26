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

## Wave 3c (w15, after lighting r1 2913db8)

9. **To lighting, low (A + B, repeat of item 6):** q14 still shows the bright rhombus sun patch on the 26B back (around
   x 500, y 330), and q13 still reads cobalt. Studio p8 now matches py_37301's saturation (S 0.24 vs 0.22), so most of
   the remaining cast is cabin light or tone. B also measures q13's trim-B backs as cooler (S 0.27 vs 0.36 in py_37302).
10. **To lighting, low (A):** on the q13b foreground seat top, the gaps between fabric blocks render very dark. The new
   low-pocket AO / crevice term may be reaching the fabric.
11. **To lighting, low (B):** the studio p8 back is darker than py_37301 (#667085 vs #94a2ba), while the cushion is
   close to the photo. Check the low-face AO weight on near-vertical seat backs.
12. **To other areas (B, from q13):** the carpet is royal blue and the curtains violet-blue, against charcoal in py_37302.

## Final confirm (py, on 1430d42): cool cast on PY fabric (to lighting)

- **Status:** PY passes (A 8.5 / B 8.5). This item is information for the integrator, not a blocker.
- **Evidence:** the studio views are pixel-identical to w19, yet the mean RGB of the cabin-view seat backs shifted blue at unchanged L:
  - q14 mid seat back (x 260-400, y 300-500): 115/126/146 -> 112/125/155. B/R went from 1.27 to 1.39.
  - q13 front seat back (x 200-330, y 420-560): B/R went from 1.36 to 1.49.
  - The ANA photos py_37301-03 measure B/R 1.22-1.36, so the fabric now reads denim/periwinkle rather than blue-grey.
- **Cause:** the cool PY/Y seat-level balance from L14 in `12_scene.js` / `04_shaders.js`.
- **Suggested fix:** cut the PY/Y seat-level cool tint by about a third, aiming for fabric B/R of about 1.30 in q14.
  - The sidewall would still keep most of its gain toward the photos: B−R went from 1 to 20 against 25-27 in the photos.
  - Do not compensate in `SEATMAT`.
- **Also noted (rater B, low):** a bright diamond-shaped sun patch on the q14 window-seat back.
