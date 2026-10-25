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

## QA r3, light group (lighting + integration raters; from_* items addressed to lighting / integration)

Code: `04_shaders.js`, `12_scene.js` in fede907. The integrator's snapshot commits 00948cd..0804d1c hold intermediate
states; fede907 is the final one. Renders are in the scratchpad: qa/fix_light/r3 (qa.js views) and r3x (moods / extra views).
Iterations: r3a-r3g. Tools and views: qa/fix_light/t3.

Rater issues (QA r3 light / integration):
- lighting HIGH, amber light ordering upside down (pale seat level under a dark overhead): done (fede907)
  - Dining / Sunrise: lowTint [1.0, 1.08, 1.2] x0.8 (raters' fit) and hemiBot x1.4.
  - The vault wash is floored at e 0.14 (`u_vaultE`), in a paler vault hue [0.32, 0.145, 0.047]; bandCut 0.2;
    sideWall [0.6, 2.2, 4.2].
  - dd (`__sit('12H',0.25,-0.05)`, shades closed): ash #b89c70 L160 s0.39 -> #8f602e L103 s0.68 (target L100-115,
    s0.65-0.72); wall at the window tops #b79970 L157 s0.38 -> #b07f50 L134 s0.54; bottom third 101 -> 79 (target <= 70).
  - d06: vault L68-73 s0.80 -> #c08d44 / #b98640, L140-147 s0.64; bins L147-160 (ucr L158).
  - q21 closed shades: pier L161-199 s0.32-0.42 -> L139-174 s0.57-0.65; the door dome holds (#d19849 -> #cd9e51 s0.60;
    ucr #c89552).
  - Not met: the rater's "ceiling between the bins" box in dd is the centre-bin underside / PSU band (from 12H the bins
    are overhead; the vault is out of frame). It reads #70431a-#7a4c23 L74-84 against the photo's undersides #855a2b
    L96; the rater's L150-170 target is the ucr vault strip, met in d06 / q21 instead. The wall at the window tops
    (L134 vs 140-158) is short too: sideWall / bandCut move it only 2-3 L, the band is mostly hemi / wash.
- lighting medium + integration HIGH, aisle carpet: done (fede907)
  - The 8-direction sweep (4 axis + 4 diagonal) is now 16 azimuths read bilinearly, still at one cell per layer. The
    raters' half-cell slope (63 deg rays) opened the economy row gaps, so it was dropped (from_econ w34). The lowest 5
    layers get two more i / k blur passes, and the carpet reads a 4-tap mean AO.
  - The pocket term acts only under the seat pans (ramp 0.0-0.12, floor 0.5 on the carpet); the r2 bounce cut is gone.
  - A 3 cm contact map adds the thin base line.
  - q06 aisle (500-590, 370-560): p10 20 -> 51, < 30 36 % -> 1 %, mean 50 -> 60. Row 520 edges 0.26x
    -> 0.86x (L49-53 vs 57-58) of the centre.
  - q10 aisle < 30 30 % -> 1 %; no periodic diagonal bands in q06 / q10 / s01.
  - computeAO: 1.1-1.35 s in headless Chromium under load, for 8, 12 or 16 azimuths alike. The azimuth count is not the
    cost.
  - The aisle level (60) sits over c_27312 (53.7) until shell darkens carpetJ (hand-off).
- integration medium, Y / PY legroom carpet crushed: done (fede907, with the pocket term above). q17 between rows
  #0a0e18 L14 p10 5 -> #131c32 L28 p10 10 (target L30-40, p10 >= 20; the box holds under-seat pixels); q13 PY carpet
  p10 14 -> 25, right aisle edge 16-23 -> 29-41; q15 bottom band < 30 26.1 % -> 27.3 % (y_47300 24.3 % in the same box;
  frame < 30 8.6 % vs 10.0 %, p5 22 vs 22).
- integration HIGH, economy cover sheen: done (fede907)
  - New `SHEEN` material flag (04_shaders.js; the top bit of the layer byte) and a (1 - N.V)^3 env lobe, gain
    `LIGHT_TUNE.sheen` 1.35. Econ already set `yCover: l: LAYER.none + SHEEN` (befdc88).
  - q17 flaps #465079 L81 / #414c73 L77 -> #737c9c L125 / #6e799a L122 s0.26-0.28 (target L130-150 s ~0.3; a higher
    gain takes q16 over y_47301); q16 covers L108-112 (y_47301 67-108).
  - q15 head-on flaps L57-80 -> L56-82 (unchanged).
- lighting medium, night upper cabin grey-cool: done (fede907)
  - The screen spill stops over 1.4-1.7 m; Night led x0.6; the cove / vault wash is capped at e 0.09.
  - q20 centre bins #424448 L68 h225 -> #33302c L49 h29; outboard #3c3e44 L63 h221 -> #2a2724 L40 h30; ceiling panel
    (520-600, 10-60) L117 -> L69; median 37 -> 32.
- lighting low, boarding window wall: done (fede907). sideLed [0.48, 0.53, 0.66]; q15 wall #d2d3d3 L210 -> #dfdfdf
  L222-223. Still neutral (B-R 0) where y_47300 reads B-R +9..11: the ACES shoulder desaturates it at L222.
- integration medium, vault darker than the bins: lighting part done (fede907). The bin AO floor is 0.85 -> 0.72, but the
  q06 / q16 bins are not AO-limited (q06 L221-223 before and after). The levers are the vault / door eFn: handed to
  ceiling/bins.
- integration low, q14 rhombus sun patch: partly (fede907)
  - The pane gate ramps over 0.75-1.3 of the superellipse radius (was a ~1 cm penumbra); PCF taps 2 texels apart; the
    sun cap is 1.5 (was 2.0).
  - Edges are visibly soft, but the patch still reads 1.48x the fabric (L207 on L140; target <= 1.3x). A lower cap would
    flatten every sun patch in the cabin: questions_lighting.md 5.
- lighting low, far-row snow (from_econ w27): done (fede907). Beyond 3-7 m the photo mip bias fades out and the tile
  contrast eases halfway to the tile mean (its 1x1 mip).
- lighting low, armrest gloss: not met. arm r 0.30 / armPad 0.38 (scratch build) plus cove x1.3 moved q15 armrest p99 only
  225 -> 229 (y_47300 254); LIGHT_TUNE.cove stays 1.0. The photo's streaks reflect the lit aisle vault, a broad area light
  the env model does not hold.
- lighting medium, lens / wall sky hairline: geometry; handed to ceiling/bins (from_integration.md).
- lighting + integration medium, THE Room shells slate / blue: handed to room (SEATMAT jShell / jCap / jShellIn, one
  merged neutral-darker value).
- lighting low + integration medium, THE Room carpet texture: handed to shell again (third time).
- integration medium, suite bed sheet; low, ottoman recess: handed to suite again (third time).
- integration low, door-3 bin-lip z-fight: handed to ceiling/bins again (third time).
- integration low, F drapes: handed to monuments again (third time).
- integration low, q01 camera: done by the integrator in 7c091e4 (`test/qa.js`).

from_* items (to lighting / integration):
- from_econ w14 / w19 / w23 / w27 + from_integration_cam (cover sheen lobe): done (fede907; SHEEN flag, see above)
- from_econ w27 / w31 (far-row snow): done (fede907). Far tick-row contrast in q16 (400-680, 130-230): p90 / p50
  1.64 -> 1.58, bright share 0.11 -> 0.09 (y_47301 1.62 / 0.10).
- from_econ w31 (layer 16 mip bias -0.25): done (fede907); it fades out with the others beyond 3-7 m.
- from_econ w34 (row gaps too light, seat-level lift 15-25 %): addressed (fede907). Econ rated the r3 snapshot with the
  63 deg AO sweep, which opened the gaps; the final sweep is back at 45 deg. q15 foreground pans (150-800, 500-575) are back
  from L75 to L68. Frame < 30 is 8.6 % (y_47300 10.0 %), p5 22 (22). The mid-row band (y 150-235) < 50 reads 5 % against
  17 % in y_47300; not changed further this round, pending econ's re-rating.
- from_econ w27 (`photoBase` gain argument, shared `03_tex.js`): open. It is a function change in a shared file, not a
  one-line key; econ already compensates in its colour.
- from_econ w27 (per-view FOV in `test/qa.js`): integrator (questions_econ 22).
- from_py 5 / 6 / 9 (q14 rhombus): partly (see above). from_py 6 / 9 (q13 cobalt): not changed. from_py 10 (q13b gaps
  dark): the crevice term is unchanged on vertical fabric; not re-measured. from_py 11 (studio p8): 14_studio.js light,
  not in this worker's files.
- from_room w16 (2) (shells light and cool): handed to room as a neutral darker SEATMAT value. (1) aisle doors and
  (3) pillow saturation: not changed.
- from_ceiling q01 camera: done by the integrator (7c091e4).
- from_ceiling w13 (bins clip): reply in from_integration.md (door eFn is the lever; AO floor 0.72 did not move them).
- from_exterior 17 (albedo-scaled exterior reflection is a no-op): not changed; exterior says nothing more is needed.
  18 (wing hairline aliasing, MSAA) and 19 (nav light on the upper tip, optional): not done.
- from_monuments w13-15 (q19 blow-out, door-1 fWood streaks): not re-rated this round.
- from_shell w15 (door glass flat white, creams neutral, dado grille dark): not changed this round.
