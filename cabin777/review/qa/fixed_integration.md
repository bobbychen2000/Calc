# Items fixed by lighting + integration

- from_monuments 1 (QA cameras q01 / q11 / q13 inside monuments): done (49435dd)
- from_monuments 2 (fold monoLayoutQA into buildLayout): deferred until the monuments worker finishes (needs its wrapper removed in the same change)

## QA r1, light group (lighting + integration raters; from_* items addressed to lighting / integration)

Code: `04_shaders.js`, `12_scene.js` in 9bf8047 (earlier states in the snapshot commits 282136c..918e366). Renders: scratchpad qa/fix_light/r1 (qa.js views), r1e / r1x (moods).

- from_econ w10 HIGH (economy block darkened by the snapshot commits): done (9bf8047) - the low-AO bounce weight and the
  crevice term now act only below ~0.75 m on faces that do not look up; q15 fabric (300-600, 380-575) L61 -> 70,
  (200-400, 200-300) L87 -> 115; q18 hood region L144 -> 152 (r0 -> r1)
- from_econ w2 / w4 / w6 (seated-view hood / shells dark): done (9bf8047) - boarding exposure 1.38 + highlight tone
- from_econ w2 (hairline streak q15): done (r3 opaque LUT; 9bf8047 superellipse pane gate)
- from_econ w6 (photo fabrics smear on 45 deg faces): done (9bf8047) - triplanar exponent 10 for photo layers (>= 16)
- from_econ w6 (q15 camera) / from_exterior 5 (q23_wingK) / from_py 2 + 4 (q13b PY backs) / from_monuments 3 (q19): open -
  `test/qa.js` is outside this worker's file set (lighting = 04 / 12 / 13); integrator
- from_econ (layer-4 plastic normal amplitude, `03_tex.js`): open - shared file outside this worker's set; integrator
- from_exterior 8 (sunset wing royal blue): done (9bf8047) - sunset skyTop [0.28, 0.34, 0.60], extSun 0.25 (26K wing
  grey-blue, 19A wing no longer mauve)
- from_exterior 9 (beacon paints the canoes red): done (9bf8047) - exterior point light only on down-facing faces
- from_exterior 10 (sun-side cowl clips): not fixable in lighting without darkening the wing (#b6bcc2, fine); handed to
  exterior in from_integration.md (cowl albedo / roughness)
- from_exterior 11 (reveals / lining royal blue in cruise): done (9bf8047) - band and lens light x (1 - 0.75 reveal),
  lighter cruise band, lens terms only in the seat zones
- from_monuments 2 (fold monoLayoutQA into buildLayout): still deferred (`05_layout.js` + `10_mono.js`)
- from_py 3 (pyPlacard atlas rect, `06_atlas.js`): open - outside this worker's set; integrator
- from_py 5 / from_shell 3 / from_suite 2 (hard-edged / blocky sun patches): done (9bf8047) - rounded-pane superellipse gate
  (|dz| / hw in the LUT zone row), sun soft-clip 1 / (1 + max albedo), cap 2.0
- from_room w8 (screen strip inside the raised sill): done (9bf8047) - strip y 0.642 -> 0.580
- from_shell w5 (reveal glow flattens the upper tub): done (9bf8047) - down-facing faces 0.20-0.30 m above the pane centre
  keep 0.35 of the glow
- from_suite 1 (suite interior dark from the seat): done in r3 (fZone lift); r1 q03 median L155 (r0 133)
- from_suite 3 (layer-15 glow hue): done in r3 (ebc3f8a)

Rater issues (QA r1 light / integration):
- lighting high, night orange: done (9bf8047) - neutral cove / vault, cool-grey lens light down the wall, galley-zone fill,
  exposure 2.5 (q20 median L30 = ucr)
- lighting high, amber phase cut at 1.25 m: done (9bf8047) - lowTint [1.0, 1.35, 2.0], lowGain 0.6, sideWall = hemi share,
  sideLow 0.5 (d06 median L82 vs ucr 85, lower third L53)
- lighting medium, cruise band too dark / saturated: done (9bf8047) - c16 band L127-157 h228-233 (was L94-110 s0.55-0.69)
- lighting medium, economy upper cabin dark: done (9bf8047) - AO floor 0.85 above 1.9 m; q16 ceiling #c2c4c7 -> #dddee0,
  window wall -> #e4e5e5
- lighting / integration medium, no specular sheen: done in lighting (9bf8047, cove LED line lights); SEATMAT roughness
  (jShell / jCap / fShell / yShell -> 0.34) handed to room / suite / econ
- lighting low, q21 sunset panes grey: done (9bf8047) - blue deck; the +0.05 pitch for q21 is in `test/qa.js` (open)
- lighting low, q04 bed clipped: partly (9bf8047) - soft clip + cap; the bed albedo (L224 without sun) handed to suite
- integration high, compressed tonal range: done (9bf8047) - exposure 1.38 / 1.12, luminance tone (black toe + half
  S-curve above 0.5), low-pocket crevice term; q06 p99 248, >235 9.3 %, <30 3.6 %; q09 239 / 3.9 / 3.1; q16 242 / 3.3 / 1.2
- integration medium, boarding wall band grey: done (9bf8047) - sideLed [0.42, 0.46, 0.55], bandCut 0.15, reveal 1.9
- integration medium, band on the door linings: done (9bf8047) - lens / band / bin shade x seat-zone mask (LUT zone row)
- integration medium, cruise reveals blue + hue: done (9bf8047)
- integration medium, crevices too open: done (9bf8047) - low-pocket crevice term and low-face AO weight
- integration low, rectangular sun patches: done (9bf8047)
- integration medium yCover / low bin-lip z-fight: handed to econ / ceiling (from_integration.md)

## QA r2, light group (lighting + integration raters; from_* items addressed to lighting / integration)

Code: `04_shaders.js`, `12_scene.js`, `13_app.js` in b84b691 (the bulk landed in the snapshot commits 134ea40..766b441; b84b691 is the final state).
Renders: scratchpad qa/fix_light/r2base (head before), r2a / r2b / r2c / r2e (iterations), r2d + r2f (final; r2f = q06 / q13 / q16 on b84b691); views in
qa/fix_light/tools/views_all.json.

Rater issues (QA r2 light / integration):
- lighting HIGH, q21 amber phase pale and even: done (b84b691) - `u_fillLift` (0.15 in dining / sunrise) on the small-e
  fill lift, dining / wake vault [0.36, 0.135, 0.04] (G/R 0.38), lens core. q21 PSU band #b88c52 L145 -> #764c26 L82
  (ff_door-gap #603b1d L65, ucr #6f482a L79), door-dome ceiling #debe83 L193 s0.41 -> #d09748 L158 s0.65 (ucr #c89552
  L156 s0.59), pier #a16f39 L118 s0.64 -> #b18957 L142 s0.51 (ucr #bc895e L145). q21 median stays ~146 (rater target
  100-110): the frame is mostly the pale door-4 lining at seat level, which the integration medium below asks to be
  brighter (ucr ash L108-122); the ceiling / band / lens targets are met
- lighting medium, no IFE screen spill: done (b84b691) - the 6 screens nearest the eye as representative-point area lights
  (centre, normal, area read from the layer-13 quads of each seat unit), Night / Blue full, Dining half. nF03 right
  housing L6 -> L25 (ml_1919534 L32), ottoman L5 -> L20 (target ~15), q20 near shells L5 -> L16
- lighting medium, no full-blue phase: done (b84b691) - new mood `blue` ('Blue' chip, from MOODS in 13_app's picker):
  saturated blue cove / lens, dark blue-violet crown, lavender seat level, warm galley ends (monFill), screens spill
- lighting medium, lens never glows in the amber phase: done (b84b691) - `u_lensCore` [0, 0.55, 0.15] (dining / wake): the
  lens core clips pale yellow; the lens box size (~1 px at 930) handed to ceiling/bins (from_integration.md)
- lighting medium, THE Room carpet texture: handed to shell (+ shared 03_tex.js / make_swatches.py), from_integration.md
- lighting low, cruise wash short in THE Suite: done (b84b691) - cruise sideLow 0.10 -> 0.30, and the reveal test now uses
  the lining circle (faces recessed behind it), so the flat wall between the windows is no longer treated as reveal:
  cF03 belt column y145 #bbbcc8 -> #9097ca (B-R +58), y240 #cdcdd1 (+3) -> #b3b6d0 (+29) (ml_DSC_1939-1 +68 / +40)
- lighting low, strip too white: done (b84b691) - the strip mesh (built in 12_scene.js) takes '#ffc860'; q20 strip top-40
  #eee3c2 -> #f2e37f (ucr #ffee94 / #fde98c). SEATMAT.moodGlow is now unused (note to room)
- integration medium, contact shadows: done (b84b691) - floor / underside pocket term (`crevF`) and less bounce on occluded
  carpet, on a pocket AO (max of the AO at the carpet and 0.35 m up) so open aisles beside bulkheads keep their level;
  probe: ao 0.00-0.01 under a seat pan, 0.11-0.24 along the block edge, 0.46-0.52 in the aisle, ramp 0.02-0.28. q06 bottom
  band < 30 12.7 -> 16.6 % (c_27312 18.4), p25 50 -> 45 (37), frame p5 38 -> 30 (15); q13 < 30 5.1 -> 8.6 % (py_37302 7.4),
  p5 29 -> 18 (25); q16 20.2 -> 24.3 % (y_47301 11.0; the head was already over, the dark covers / carpet are econ / shell
  albedos). q15's band is seat-back fabric in this camera (no floor), so it moves little (econ owns the q15 camera). The
  raters' full-strength ramp (0.08-0.55) crushed the open aisles (q13 / q16 p5 8 / 10) and was not kept
- integration medium, amber seat level dim / fiery: done (b84b691) - dining lowGain 0.6 -> 1.4, lowTint [1.0, 1.42, 2.3],
  sideWall [0.4, 2.8, 7.0], sideLow 0.65; wake lowGain 1.4, lowTint [1.0, 1.4, 1.95]. dining_room ash #593717 L60 s0.74
  -> #916838 L109 s0.61 (ff_closed #ab7f58 L133, ucr #9a6330 s0.69); d06 seat-level ash L38-58 -> L75-102
- integration medium, jBand dimples: handed to room (from_integration.md)
- integration medium, suite bed sheet clipping: handed to suite (from_integration.md)
- integration low, door-3 bin-lip z-fight: handed to ceiling/bins again (from_integration.md)
- integration low, F drapes cool grey: handed to monuments (from_integration.md)
- integration low, strip clips / no pool: done (b84b691) - strip colour as above; pool 0.25 m x2.5. The console under the
  q20 strip stays p95 ~53 (ucr 156): in this camera the strip sits over the dark footwell / ottoman, not a console top
- integration low, no pocket under the ottoman: handed to suite (geometry; from_integration.md)

from_* items (to lighting / integration):
- from_econ w14 medium (row-distance darks lifted): done with the pocket term above (b84b691)
- from_econ w17 / w19 (photo mip bias): done (b84b691) - bias -0.5 on the photo layers; from_econ w23: layer 16 (y_tick)
  exempt (b84b691). The arrays were already 8x anisotropic (01_gl.js)
- from_econ w14 / w19 / w23 (cover sheen lobe): open - needs a material-specific lobe; the cove line lights (coveSpec) are
  the current sheen. Not done this round
- from_econ w17 (q16 near seat 2x light): not reproduced at the econ crop with the new q16 camera pending; open
- from_room w13a (anisotropic filtering on u_photo / u_detail): already on (8x, 01_gl.js textureArray); mip bias added
- from_room w12 / w16 (cabin white balance: shells cool, pillow saturated, aisle doors dark): not changed - the boarding
  light stays cool-neutral after c_27312 (walls #eaedf0, reveal sides #d7dbdf / #e2e5e8); see also from_shell w12
- from_shell w10a (closed blackout dark): done (b84b691) - shade row in the window LUT; nearPane only as far as the shade
  lets the window light in; sJ blackout 0.59-0.78 of the pier (omaat_room24 0.65)
- from_shell w10b / w12 (dark PY/Y tub crown): done (b84b691) - the reveal glow ended at 0.34 m above the pane centre, so
  the crown (0.36-0.56 m) took only hemiBot; it now takes the window light (`crown` term). oY crown 0.69 -> 0.86 of the pier, darkest just above the opening 0.71
- from_shell w12 / w15 (creams render neutral): not changed - c_27312's reveal sides and wall read cool-neutral, the
  cream samples are from in-service photos under warmer light; kept on the official photos
- from_shell w15 (door viewing-window glass flat white): not changed - the door glass is the cabin pane under winExp 4
  (day panes near-white, c_27316 #ffffff); a per-pane exposure is not in this round
- from_shell w15 (dado grille near black under the seats): not changed (AO under the seats; no photo value given)
- from_monuments w9b (bar blind black): resolved at head - q11 blind #1e1e21 L31 (ANA render #1c1921)
- from_monuments w9b / w13-15 (galley upper banks fogged white): done (b84b691) - the AO floor above 1.8 m acts only in the
  seat zones; q19 upper banks even grey
- from_monuments w13-15 (door-1 fWood streaks): mip bias / 8x aniso; not re-rated
- from_ceiling w9a (strip under the outboard bins dark): done in r1 (crevice term below 0.75 m only)
- from_ceiling w13 (door domes ignore the baked tone): explained, not changed - layer-12 emission is the LED colour x e and
  ignores the vertex tone by design (the bake only scales the 0.3 diffuse); the AO floor no longer lifts door zones
  (b84b691). Lever for ceiling: lower the dome eFn at the crown (from_integration.md)
- from_ceiling w13 (bins clip): reply in from_integration.md (BINMAT doorC / band emission lift is the lever)
- from_exterior 14 / 16 (albedo-blind grazing reflection): done (b84b691) - exterior specEnv x baked luminance / 0.39
  (0.5-1, metals exempt, not in the studio)
- from_exterior 15 (look-out framing): done (b84b691) - lookOut eye at the glass (side x 2.72, y 1.10, pitch -0.06);
  w26K now shows the registration under the shade rail
- from_py 9 / 6 (q14 rhombus sun patch, q13 cobalt): not changed this round
- from_py 10 (q13b fabric gaps dark), 11 (studio p8 back): not changed (studio light is 14_studio.js)
- test/qa.js camera items (from_econ, from_py, from_exterior 5): integrator / econ (from_integration_cam.md)
