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

## Lighting run 2, L7 (lighting 6.8 + integration 6.9 raters; from_* items addressed to lighting / integration)

Code: `04_shaders.js`, `12_scene.js` (no `13_app.js` change). The run started on 836b636 (polish B in). Snapshot commits
a8205ea..9d197db hold intermediate states (one fixer stopped by an outage after three candidates, a second one finished).
Renders in the scratchpad: qa/fixL7/before (836b636), after1-after5 (after5 = this commit; built into b_after5), extra mood
shots from qa/fixL7/tools/x.json (dd, d06, c06, blue06, bl16, n16, nF03). Tools: qa/fixL7/tools (cmp.py frame / thirds vs
photo, reg.py region boxes, mask.py stats over the changed pixels, samp.py, top.py, thin.py, crack.py).

Regression guard (qa/fixL7/tools/cmp.py: |model - photo| summed over the frame median, p5, p95, the thirds' mean L and
0.25 x the thirds' hue difference; lower is closer). Before (836b636) -> after (this commit):
- q06 169 -> 126; q20 76 -> 69; q03 270 -> 263; q13 65 -> 63; q09 116 -> 116; blue06 101 -> 85; q14 125 -> 122;
  q17 31 -> 31; dd 100 -> 85; bl16 176 -> 93; c06 216 -> 210; nF03 88 -> 88.
- Up at frame level, kept on the matched regions:
  - q15 23 -> 27: the bins (0-280 / 650-930, 0-90) L225 -> 218 against y_47300 L218, but p10 202 -> 189 (200) and B-R +4 -> +8
    (photo 0, the rater's ceiling +8); head-on covers (59,70,108) unchanged; the mid-row flaps that changed L78 -> 94 at
    the same pixels as y_47300's L106.
  - q16 28 -> 37: the bins L220 -> 210 (y_47301 209), wall (0-300, 100-200) B-R +5 -> +10 (+14), covers that changed L71 -> 89
    (y_47301 92 at the same pixels); the top third falls 196 -> 190 because the model's top third holds more bin area than the
    photo's.
  - q21 182 -> 186: the tubs (mid third 125 -> 127). The framing does not match ucr_the-room-cabin; the tub (620-660, 300-350)
    L117 s0.70 -> L135 s0.67 beside a pier at L190 (0.62 -> 0.71 of the pier; photo 0.85-0.93).
  - d06 55 -> 63 (binLift, below) and n16 180 -> 219 (screens off; the photo's economy night level is questions_lighting 8);
    neither is in the check set.
- Reverted: candidate 4's tub floor painted the closed blackout shades out of the dd windows (flat cream), and in Night /
  Blue it lit the tubs flat and pale (q20 tub pixels L28 -> 55 against ucr_room-night-lighting L23 at the same pixels;
  bl16, blue06, nF03 alike). It now acts on `MAT.reveal` only, in the amber moods only (below).
- Harness note: `test/qa.js` views depend on their order. Night (`applyMood('sleep')`) closes every shade and the per-view
  reset does not reopen them, so a run with q20 before q06 renders every later view with closed shades. Render in the
  canonical order (q20 then q21, which reopens them), as every set above was.

Rater issues (L7):
- lighting medium + integration HIGH, outboard bins brighter than the vault: lighting part done.
  - `binLo` 0.8 (Boarding, Cruise): the lower, inboard-down face of the outboard bin doors takes x0.8 hemi + bounce; the
    crest (N.y 0.6) keeps x1.
  - Box means, before -> after (photo): q06 right bins L216 -> 205 (c_27312 196), left 209 -> 207 (200), vault L232 (221);
    q16 bins 220 -> 210 (209); q15 bins 225 -> 218 (218); q13 ceiling 217 -> 214 (180); c06 right bins 188 -> 176 under a vault
    at L221.
  - Reverted the raters' 0.72: q15 bins went to L209, p10 177 (y_47300 evenly lit: L216, p10 200).
  - Not done: the extra Cruise x0.75 (questions_lighting 7 asks which in-flight look Cruise should follow). The vault and
    door albedo / grade levers are ceiling/bins' (from_integration.md).
- lighting medium, Boarding shaded whites neutral: done. hemiBot [0.36, 0.37, 0.40] -> [0.31, 0.35, 0.47], wash
  [0.25, 0.26, 0.28] -> [0.23, 0.255, 0.32], crown term x0.7 -> x1.1 (the raters' values).
  - The shaded whites move B-R +2..+5: q17 window band L175-195 +19 -> +22, L195-215 +4 -> +8; q14 L175-195 +9 -> +14;
    q16 wall #cacccf (+5) -> #c1c4cb (+10) vs y_47301 #c5cad3 (+14); q06 right bins +6 -> +11 (c_27312 +10).
  - Lit faces hold: q06 vault #e8e8e8, q15 head-on covers unchanged.
  - Not all the way to the photos' +11..+33: the ACES shoulder desaturates near-white faces. questions_lighting 6 asks
    whether Boarding should follow the cool official photos or the warm in-service ones.
- lighting medium, amber window tub burnt / near-black: done.
  - New `tubRef` in mainFS: where the window light is dim (sunset, closed shades), the recessed tub from just above the
    bezel to the crown keeps at least 0.7 (`LIGHT_TUNE.tubWash`) of the diffuse light of an unbaked cream face under a pier's
    hemi + wash.
  - It acts on `MAT.reveal` faces only (no layer, r 0.45): not on the shades, the tunnel lining or the seals. It acts only
    in the moods with `tub: true` (Dining, Sunrise).
  - q21 tub (620-660, 300-350) #b06a35 L117 s0.70 -> #ba7e3e L135 s0.67 (target >= L125, s <= 0.6: L met, s not quite; the
    pier is s0.46).
  - dd crowns (820-930, 165-215) L148 -> 165, high-pass 10.2 -> 5.5; the closed blackout shades keep their pleats.
- lighting medium, amber bins dark and over-saturated: partly. `binLift` [0.055, 0.04, 0.02] (0.6 of the raters' hemiBot
  step) on the lower hemisphere above ~1.6 m in the seat zones only (Dining, Sunrise).
  - dd right bins (640-930, 20-160) L106 -> 110; d06 left bins L93 s0.70 -> L102 s0.66, right 130 -> 135; q21 bins 141 -> 143.
  - Target L135-150, s0.50-0.58: not met.
  - The raters' full step on the whole hemiBot lifted the seat level and the door zones (q21 median 134 -> 142 vs ucr 86;
    d06 median 77 -> 89 vs kn_room_35 68): reverted to this partial lift.
- lighting medium + integration medium, sky hairline at the lens / lining junction: done by polish B (d2627ff). dd has 0
  sky-blue px in (600-930, 60-210), before and after.
- lighting low, Night cove lines neutral white: done.
  - led [0.030, 0.025, 0.020] -> [0.030, 0.021, 0.009]; mainFS caps the line's e at 0.5 when vaultE.y < 0.1. Also the vault
    cap 0.09 -> 0.045 (from_ceiling polish B: the raised seat-zone vault eFn bound across the vault at night).
  - q20 cove box (500-575, 0-120) L69 -> 47; its top-40 #797065 L114 -> #5c5241 L83 (warm).
  - q20 bottom third 43 -> 27 (ucr 33), mid third 29 -> 32 (41).
- lighting low, every screen lit at night: done. Night / Blue `scrOff` 0.7: each seat screen holds a hash in a 4 cm
  floor-plan mask (`buildScreenMask`) and screens under 0.7 go black. The nearest screen within 1.8 m that faces the eye
  stays on, with all the clusters `buildScreens` split it into (THE Suite's wide screen: after3 showed it half lit in
  nF03). Only lit screens spill.
  - bl16 p95 167 -> 116 (sany_47 81); blue06 p95 114 -> 107; n16 p95 180 -> 76 (sany_40 136; its lit screens are ~30 %,
    as the photo's, but the economy night level is lower than sany_40's: questions_lighting 8).
- lighting low, Blue door / galley zone blue: partly. monFill [0.06, 0.05, 0.035] -> [0.20, 0.16, 0.10]; the hemi, bounce
  and wash take x0.4 outside the seat zones (`monHemi`). bl16 door-4 box (600-700, 215-260) #393e6e h235 s0.48 ->
  #414262 h238 s0.33. That is greyer, but not the warm #5a4e48-#76644c target: the box is mostly the bulkhead under the blue
  cove and lens light. The galley end beyond it reads beige.
- integration medium, look-out exposure inverted: done. Past the lining (|x| 2.45-2.70) the interior exposure falls to x0.14
  (`LIGHT_TUNE.lookOut` 0.86). q12 left reveal (0-120) L228 (61 % clipped) -> L133 (target 110-140); frame clipped 19.6 % ->
  0 %; wing box L173 -> 171. Seated window views (|x| < 2.45) are unchanged.
- integration medium, night trough grille: done by polish B (troughRim e 0.19). q20 grille (515-575, 0-120) top-40 L114 /
  max 131 at the start of this run -> L83 / max 94 (target <= L135).
- integration medium, THE Room / Suite carpets: done by polish B (shell). Not a lighting item.
- integration medium, thin rim highlights: tried and reverted, handed to room / econ / py (SEATMAT roughness) in
  from_integration.md.
  - Three tries on the two cove line lights (`coveRim`):
    - x2.5 at rough < 0.5: the bin crests clipped and the q03 screen glared.
    - x4 below 1.5 m at rough < 0.5: the PY flaps went L72-82 -> 90-117 against py_37302's 61-87.
    - x4 at rounded edges only (nvar) at rough <= 0.36: no measurable change.
  - Thin share now: q06 1.03 -> 0.97 %, q16 0.64 -> 0.62, q13 0.17 -> 0.16, q17 0.47 -> 0.46, q09 0.42 -> 0.41, q15
    0.52 -> 0.52 (photos 1.10-2.50).
- integration low (z-fight dashes, toe-kick, footwell hairline, ink clouds): other areas' files, routed in
  from_integration.md ("lighting run 2, L7").

from_* items (to lighting / integration):
- from_econ w40-w42 (cover sheen at mid angles): done. The SHEEN lobe is (1 - N.V)^2 (was ^3), tinted 0.3 toward the
  fabric hue (0.5 put the q16 covers at s0.57 vs the photo's 0.37).
  - q16 covers that changed L71 -> 89 (y_47301 92 at the same pixels); q15 mid-row flaps L78 -> 94 (y_47300 106).
  - q15 head-on covers unchanged.
- from_econ w37-w39 (near pans dark): not changed this run.
- from_ceiling (polish B vault eFn vs the night cap): done (vaultE cap 0.045, above).
- from_shell w15 lows (door glass flat white, creams neutral, dado grille dark, band under the PY/Y tub lip): not
  changed this run.

## Lighting run 2, L8 (lighting 7.3 + integration 7.6 raters; from_* items addressed to lighting / integration)

Code: `04_shaders.js`, `12_scene.js`, `13_app.js` (SSAO only at the Sharp quality). The run started on b65def4. The econ
area committed w47-w51 during the run (`09a_econ.js`), so q15 / q16 / q17 / c15 are compared with base2 (this run's
lighting files from b65def4 on the econ tree of 9c93549), every other view with the b65def4 renders. Renders in the
scratchpad: qa/fixL8/before, base2, final (+ final2: q21 / dd / d06 after the last underside change), experiments
ss1-ss4 / f1-f4 (SSAO), v3, t1-t4 (half size, box means); tools in qa/fixL8/tools (metrics.py target boxes, cmp.py
frame / thirds vs photo, thindark.py, time.js, exp3.js).

Regression guard (cmp.py: |model - photo| over the frame median, p5, p95, the thirds' mean L and 0.25 x their hue
difference; lower is closer), before -> after:
- q03 263 -> 257; q06 126 -> 120; q13 63 -> 58; q14 122 -> 113; q15 30 -> 29; q16 49 -> 43; q17 45 -> 41; blue06 85 -> 83.
- q09 116 -> 119: p5 36 -> 34 (c_27314 36) and bottom third 114 -> 112 (photo 161, a framing mismatch), mid 106 -> 104
  (101) and top 176 -> 175 (169) closer. Kept: the SSAO's first cut (no AO-volume easing) took p5 to 25 (score 129); the
  easing over ao 0.4 -> 0.05 (below) holds it at 34.
- q20 69 -> 70 (0.9 % of pixels changed, |dL| > 6), q21 190 -> 192 (median and top third +1): within noise; q21 median
  135 against the rater's cap 138.
- Not check views: c06 210 -> 138 (lalf_room_119), dd 85 -> 83, d06 63 -> 68 (see the amber item).

Rater issues (L8):
- lighting medium, Cruise bins at Boarding levels: done. `MOODS.cruise` hemiBot [0.24, 0.24, 0.28] -> [0.18, 0.18,
  0.22], binLo 0.8 -> 0.45, new ctrLo 0.5 (the centre bins' doors / undersides, mainFS binK; 1 in every other mood) and
  fillLift 0.25. The raters' fit (binLo 0.65, fillLift 0.45, no ctrLo) gave c06 bins L155 / 161 and c15 L166 (v3).
  - c06 bins (binL / binR) L183 / 176 -> 113 / 141 (target 125-145; lalf_room_119 L98-116) under a vault at L218 (>= 190);
    top third 178 -> 142 (<= 150); mid / bottom thirds 102 / 75 -> 97 / 73.
  - c15 centre-bin underside (330-600, 0-60) L183 -> 131 (target 110-130), outboard bins 195 -> 167.
- lighting medium, amber bins dark and saturated from a seat: partly. binLift acts on the bin door faces only (outboard
  binO, centre cBin up to the bin tops at ~2.3 m; the flat undersides and PSU band keep the r4 level), at 2x the raters'
  step: [0.055, 0.04, 0.02] -> [0.22, 0.15, 0.07] (Dining, Sunrise). Before -> after (final2):
  - d06 (standing, door faces) left bins L102 s0.66 -> L113 s0.62, right L135 s0.60 -> L147 s0.56; median 81 -> 81 (cap 85).
  - dd (seated at 12H) left box L89 s0.69 -> L93 s0.67 (target >= 110, s <= 0.62: not met), right box L110 -> 108 (target
    125-140: not met), PSU band (450-600, 0-40) L78 -> 78 (cap 85); median 83 -> 82. cmp score dd 85 -> 83, d06 63 -> 68
    (top third 123 -> 130 vs kn_room_35 114: the lifted bin faces); q21 median 134 -> 135 (cap 138).
  - The dd boxes (seated at 12H) are mostly bin undersides seen from below, which the photos keep dark (ucr centre-bin
    underside L87, ff PSU band L65): lifting them with the doors took the dd left box to L110 s0.62 but the PSU band to
    L93 (cap 85; t2 x2), so the undersides stay at r4.
- lighting medium, Boarding crowns / lens band neutral: partly.
  - Crowns: done with a new term rather than the raters' x0.82 / tint (which moved q17 only +3 B-R: the crown mask needs
    down-facing faces). `tubSky` [1.0, 0.6] (Boarding): the upper tub (0.30-0.66 m over the pane centre, shade open) takes
    the day glow's hue (x the sky tint [0.92, 1.0, 1.18]) at 0.6 of its light. q17 (matched w47 camera; the raters' box
    was on the old one) crowns (390-450, 15-55) / (520-560, 30-70) #cdcfd1 L207 +3 / #b9babd L187 +4 -> #abb4bf L180 +20 /
    #a2a9b2 L169 +16 (y_47303 #a4a9be L170 +25; target L170-180, >= +18). The raters' sky tint on the crown window term is
    in; their x0.82 on the crown fill was replaced by the tub term.
  - Boarding sideLed [0.48, 0.53, 0.66] -> [0.50, 0.57, 0.78]: the q15 lens band (100-300, 132-150) stays L221 +4
    (target >= 226, >= +12). Not met: in q15 those rows hold the PSU underside, not the band (q15 frames the bins ~15 px
    lower than y_47300); the wall rows under it moved +3..+5 B-R.
  - q15 bins B-R +8 -> +6 (target <= +5), centre underside +7 -> +2; q16 wall #c1c4cb (+10) -> #babec5 (+11) (stays >= +9).
- lighting low, Blue vault: done. vault [0.025, 0.028, 0.10] -> [0.018, 0.020, 0.060] (the raters' [0.016, 0.018, 0.065]
  read L32 s0.71). blue06 vault (430-520, 0-60) #22266c L43 s0.68 -> #1b1e56 L34 s0.68 (target L28-32, s <= 0.65; sany_47
  #141631 L24 s0.58), frame median 29 (27-31).
- integration medium, contact / crevice darks (screen-space AO): done, below the targets.
  - Depth pre-pass at the canvas size (12_scene `depthTarget`, built in 12_scene since 01_gl.js is not lighting's; the
    shadow depth program; all opaque meshes) and `ssaoF` in mainFS: 8 taps on a 5 cm disc, snapped to depth texel
    centres, face-plane normal from the position derivatives, 6 mm + angle bias 0.25, range fade 0.05-0.10 m, strength 6,
    x0.9 on the diffuse ambient only (spec, emissive, sun, tubRef and the local lights out), fading out above 1.9-2.3 m,
    off on the window reveals and eased out where the AO volume is already low (ao 0.4 -> 0.05).
  - The raters' values (half size, strength 0.7, range 0.15, no angle bias) moved q06 1.81 -> 2.00 % and q13 0.55 -> 0.58.
    Half size drew stair-stepped bands on the bin faces; an unsnapped / unbiased disc drew dark crescents in every window
    tub; range 0.15 left grey halos on a wall ~10 cm behind the PY headrests (fixL8 ss1-f3).
  - Thin dark-line share (thindark.py) before -> after (photo): q06 1.81 -> 2.96 (c_27312 4.77, target 3.3), q13 0.55 ->
    0.91 (py_37302 2.77, target 1.8), q14 0.57 -> 0.58 (py_37301 3.15), q09 1.15 -> 1.62 (c_27314 3.14, target 2.2), q03
    0.63 -> 1.70 (f_17306 3.58), q15 3.91 -> 4.10, q16 2.85 -> 3.14 (economy within +-0.5).
  - Frame p5: q06 31 -> 28 (target <= 22), q13 46 -> 44 (<= 38). Aisle carpet core (495-545, 420-575) L55 -> 55 (within 3).
  - Stronger settings reached the targets (no AO easing: q06 3.46-3.76 %, q13 1.40-1.68, q09 2.58) but took q09's darks
    under the photo (p5 25-30 vs 36, score 116 -> 122-129), so the guard keeps this level.
  - Frame time (tools/time.js, SwiftShader, 390 x 844 css at DPR 1.5): q06 / q16 / q13 +9 / +10 / +9 % with the pass on;
    triangles 1.59 -> 3.14 M, draw calls 37 -> 71 (the pre-pass). It runs only at the Sharp quality (`scene.ssaoOn`,
    13_app.js): phones open on Balanced and pay nothing (questions_lighting 10).
- integration low, Boarding seat level too cool: partly. The r4 cool shadow light (hemiBot / wash) now acts on the window
  side only (mainFS coolW: faces within ~0.06-0.25 m of the lining facing in, the reveals, half on the outboard bin doors);
  the rest takes hemiBotN / washN = the pre-r4 [0.36, 0.37, 0.40] / [0.25, 0.26, 0.28], also in the reflected cabin.
  q06 seat zone (0-930, 200-400) B-R +16 -> +12 (target <= +11, c_27312 +8), p10 54 -> 51; shell tops (150-330, 250-300)
  +23 -> +18 (<= +15); q16 wall +10 -> +11 (>= +9).

from_* items (to lighting / integration):
- from_econ wave 3k-3m (q17 cover grazing tone): tried, not changed. The sheen tint 0.3 -> 0.1 at x1.3 (econ's
  suggestion; `LIGHT_TUNE.sheenTint` is now a key) took the near q17 cover from (147,152,183) to (174,178,195): lighter
  but greyer (B/R 1.24 -> 1.12, G/R 1.03 -> 1.02) against y_47303's (145,165,203) (B/R 1.40, G/R 1.14); the lobe adds white,
  not the photo's cyan (half-size t3). q15 cover E unchanged (L55).
- from_econ (far q16 covers dark, w43b-L1): not changed. from_econ wave 3k (window phase): layout, not lighting.
- from_econ w37-w39 (near pans), w27 (`photoBase` gain, shared 03_tex.js): not changed (carried).
- from_shell w15 lows, from_room w16 (1) / (3), from_py 6 / 9 / 10 / 11, from_monuments w13-15, from_exterior 18 / 19:
  not changed this run (carried).

## Lighting run 2, L9 (lighting 7.6 + integration 7.6 raters; from_* items addressed to lighting / integration)

Code: `04_shaders.js`, `12_scene.js` (`13_app.js` unchanged). The run started on db8e97b; no other area committed during it,
so every view is compared with that head's renders. Renders in the scratchpad: qa/fixL9/before (db8e97b), final (first
candidate), final2 (committed); experiments tss-tss7 (contact AO), tlow (Dining lowTint, Blue monFill); tools in
qa/fixL9/tools (m9.py target boxes, cmp.py frame / thirds vs photo, thinmask.py lost / new thin dark lines, time2.js,
qa_fast.js = test/qa.js with the idle loop stopped: same pixels, ~5x faster).

Regression guard (cmp.py: |model - photo| over the frame median, p5, p95, the thirds' mean L and 0.25 x their hue
difference; lower is closer), before -> after:
- Check views: q03 257 -> 258, q06 120 -> 121, q09 119 -> 121, q13 58 -> 60, q15 29 -> 29, q16 43 -> 45, q20 70 -> 69, q21
  192 -> 192, blue06 83 -> 82; also q14 114 -> 112, q17 41 -> 42, bl16 60 -> 61. All within +-2 (L8 treated +-2 as noise).
  - The first candidate (the raters' contact-AO values as given) scored q06 126, q16 47, q14 117, q03 259: frames 1-3 L
    lighter, since the ghost outlines it removes had darkened them. The AO-volume easing change below brought them back.
- Not check views: dd 83 -> 75 (ucr); d06 68 -> 77 (kn_room_35: its top third 130 -> 138 vs 114 is the lifted centre-bin
  doors, whose targets come from ucr and are met; see the amber item).

Rater issues (L9):
- lighting medium, amber centre-bin doors: done. New `u_ctrLift` (mainFS hemi: `u_binLift * max(binO, u_ctrLift * cBin)`),
  `MOODS.dining` / `wake` ctrLift 3 (1 elsewhere, where binLift is 0); binLift [0.22, 0.15, 0.07] unchanged.
  - dd centre-bin face (150-450, 20-90) #a3773f L125 s0.61 -> #b18a51 L143 s0.54 (target L140-150, s <= 0.58); dd left box
    (0-300, 30-110) L93 -> 113 (>= 110); dd PSU band (450-600, 0-40) L78 -> 78 (<= 85); dd median 82 -> 85.
  - d06 centre bins (0-380, 10-100) L113 -> 141 s0.52 (135-148); outboard (600-930, 10-110) L147 -> 147 (147 +-3); median
    81 -> 81 (<= 85). q21 median 135 -> 135 (135 +-2), bins L147 -> 147.
  - The L8 dd right-box target (125-140) is retired as asked (outboard underside / PSU field; ucr L72-78).
- lighting low, Blue THE Suite front bulkhead: done. mainFS `fWall` (aft-facing faces from u_fZone.x - 0.8 to + 0.1: the
  10_mono inkWall at z 7.40) keeps the full blue hemi / bounce / wash (`monK` in all three places) and half the warm
  monFill (the full fill still greyed it: #524a6a L79 s0.30; none read #25265c L42 against the photo's L69; tlow m0 / mh).
  - blueF03 bulkhead (420-520, 20-140) #463d49 L64 h284 s0.17 -> #3f3a64 L63 h246 s0.41 (target h240-260, s >= 0.35,
    L55-75; ml_DSC_1946 #4f3d71 L69 s0.46); (620-690, 20-140) #393032 L51 s0.16 -> #312c49 L48 h249 s0.39.
  - bl16 galley flanks (330-420, 230-260) s0.15 -> 0.15 (<= 0.25); door-4 box unchanged. Night keeps its fill (step on
    u_monHemi < 1).
- integration medium, contact-AO ghost outlines: done, by another route than the raters'. ssaoF now weights a tap
  `1 - smoothstep(ssaoIn x range, range, dl)` (full up to 2 cm, gone at 7 cm; `LIGHT_TUNE.ssao` [0.05, 6, 0.006, 0.07],
  `ssaoIn` 0.3), keeps the one fixed spiral (`ssaoDither` 0) and eases in over the AO volume 0.02-0.25 (`ssaoEase`, was
  0.05-0.4). A part 5 cm off a wall now counts 0.14 of a contact tap.
  - f_ink_seated row 320 beside the monitor (539-593) L68 -> 156 (target >= 130); row 316 L94 -> 106. q03 / q05: the
    stepped frame round the monitor is gone (no copies; crops qa/fixL9/c_P.png, c_K2.png).
  - q10 x 650 above the headrest flap: rows 396-408 L47 -> 58 (L8 87: 0.67x, target 0.7x: on the line); rows 378-384 73 ->
    64 (0.70x of L8 92): a soft shade, no detached band (c_q10f.png). The 0.05-0.4 easing gave 0.77x / 0.86x but left the
    check views 1-3 L light (above).
  - q06 thin dark-line share 2.96 -> 2.49 % (target >= 2.8 %: not met); aisle core (495-545, 420-575) L55 -> 55. The lines
    lost (thinmask.py, tm_q06.png) are the ghost bands under the cap rails and monitor tops, which the photos do not show.
  - Tried and not kept [D tss-tss5]: the raters' `pow(1 - dl / 0.10, 2)` at strength 4 (clean, but q06 / q13 / q03 thin share
    1.89 / 0.55 / 0.63 % and the frames 1-3 L lighter); `(1 - dl / 0.07)^2` x6 and x8 / 0.06 (no gain); the per-pixel disc
    turn (interleaved gradient noise, `ssaoDither` 1, also at 0.15 / 0.3 of a turn): without a blur pass it draws dot grain
    along every contact edge, under the monitor and on the cap rails (c_K2.png, c_P56.png). The raters' fallback, an R8 AO
    pass with a 4 x 4 depth-aware blur, is a new full-screen pass, which this run's phone budget rules out; with it the
    per-pixel turn could come back (the shader keeps the IGN code behind `ssaoDither`).
- lighting low, PY contact darks: partly. `ssaoF(P, Nf, kR)` scales the disc and range by kR = 1 + `ssaoLow` (0.5) below
  the headrests (0.85-1.05 m) and off the sidewall, as the raters gave.
  - Thin dark-line share q13 0.91 -> 0.73 % (target >= 1.5: not met; the ghost-outline fix above took the far taps that
    made part of it), q14 0.58 -> 0.66 % (>= 1.5: not met); q09 p5 34 -> 32 (>= 32); q15 4.10 -> 4.03, q16 3.14 -> 3.08 (+-0.5);
    no halo on the wall behind the q13 / q14 headrests (kR is 1 there).
  - Frame time at Sharp (time2.js, SwiftShader, 930 x 575, 6 frames each, before -> after): q06 9930 -> 9714 ms (-2.2 %), q16
    8672 -> 8732 (+0.7 %), q13 12330 -> 12496 (+1.3 %) (target within +2 %).
  - The gap is geometry (no cm-scale gaps at the PY seat joints): handed to py / room in from_integration.md (lighting run
    2, L9).
- integration low, Dining seat level too saturated: not changed; question 12 in questions_lighting.md. The raters' lowTint
  [1.0, 1.4, 2.2] (x0.8) took the dd ash leaf (190-310, 300-500) s0.67 -> 0.49 but L107 -> 121 and the q21 median 135 ->
  141, cmp q21 194 -> 226; at x0.7 s0.50 / L112 / q21 median 137 but q21 still 194 -> 206 (bottom third s0.57 -> 0.43 vs
  ucr 0.56); [1.0, 1.25, 1.7] s0.57, q21 212. The check view's photo (ucr_the-room-cabin, in service) has the ash at s0.61-0.72
  (#a1662e, #8a5635), the model's s0.67 sits inside it; only the ff photos are greyer. Bins s >= 0.6 unchanged.

from_* items (to lighting / integration): no new ones since L8. Carried, not changed this run: from_econ wave 3k-3m (q17
cover grazing tone), w43b-L1 (far q16 covers), w37-w39 (near pans), w27 (`photoBase` gain); from_shell w15 lows (door
glass, creams, dado grille, PY/Y tub lip band); from_room w16 (1) / (3); from_py 6 / 9 / 10 / 11; from_monuments w13-15;
from_exterior 17-19; from_ceiling w13 (door domes, bins clipping at QA framing).

## Lighting run 2, L10 (lighting 7.7 + integration 7.6 raters; from_* items addressed to lighting / integration)

Code: `04_shaders.js`, `12_scene.js` (`13_app.js` unchanged). The run started on 8b1ab84; no other area committed during it,
so every view is compared with that head's renders. Renders in the scratchpad: qa/fixL10/before (8b1ab84), a1 (lighting
items + the THE Room ssaoLow gate), after (committed); contact-AO experiments t0-t19 (tune.js variants on the qa cameras);
tools in qa/fixL10/tools (cmp.py frame / thirds vs photo, lm.py lighting target boxes, q10col.py flap column, steps.py
y_aisle_fwd row 300, thindark8.py / thin8.py the integration rater's thin dark-line / highlight shares, time4.js two-build
frame time).

Regression guard (cmp.py: |model - photo| over the frame median, p5, p95, the thirds' mean L and 0.25 x their hue
difference; lower is closer), before -> after:
- Check views: q03 258 -> 259, q06 121 -> 122, q09 121 -> 118, q13 60 -> 59, q15 29 -> 29, q16 45 -> 44, q20 69 -> 69, q21
  193 -> 193, blue06 82 -> 83; also q14 111 -> 111, q17 42 -> 43, bl16 61 -> 61, n16 242 -> 242, nF03 88 -> 89, d06 77 -> 77,
  dd 75 -> 76, c06 138 -> 139. All within +-1 except q09 (3 closer).
- Reverted on the guard: the contact-AO cap on the PY / economy seats (below 1.1 m aft of THE Room). With it q14 read 1 L
  lighter in every statistic (111 -> 116; the near seat shell lost its shade) and its thin dark-line share fell 0.66 ->
  0.57 %; the cap there is now off (q14 0.69 %, 111).

Rater issues (L10):
- lighting medium, low sun on dark materials turns khaki-olive: done. mainFS sun term: the 1.5 cap now acts on the
  patch's luminance (sun / (1 + max albedo), then x min(1, 1.5 / L)), not per channel, as the raters gave.
  - s06 shell patch core (80-200, 400-500, L >= 110) #84784e h47 s0.41 -> #9f7143 h30 s0.58 (target h <= 32, s >= 0.5);
    penumbra unchanged (L 80-110 h27 -> 26, L 50-80 h24 -> 24); s06 frame mean 85.1 -> 85.2, thirds 136 / 68 / 52 unchanged.
  - Guards: q03 frame mean 144.0 -> 144.2, q05 165.6 -> 165.6, q14 146.7 -> 146.6 (these include the contact-AO change);
    sF03 85.8 -> 85.9; s15 60.3 -> 60.2.
- lighting medium, Blue THE Suite interior at half the photos' level: done. `MOODS.blue.fLow` 2.5 (mainFS `u_fLow`: the
  seat-level light x fLow inside the THE Suite zone below 1.2-1.5 m, with the |x| fade at 2.75-2.95 m so the window
  console takes it too; 1 in every other mood).
  - blueF03: aisle-side box (640-740, 380-560) L16 -> 37 (target 35-42), table (400-620, 340-400) 20 -> 32 (32-40), aisle
    pier (700-750, 160-360) 22 -> 33 (28-45), window wall 96 -> 96 (96 +-3), front wall 63 -> 63 (63 +-3); window console
    (180-300, 440-520) 32 -> 50 (ml_DSC_1945 window console L47); frame mean 61.9 -> 69.1 (photos 75-82).
  - Ottoman (380-600, 400-500) 56 -> 81: over the raters' <= 75 guard. The raters' own patch with the narrower |x| fade read
    78 (their fblue25), so no gain <= 2.5 meets both the table (>= 32) and the ottoman (<= 75); 2.5 is kept for the box,
    table, pier and console. The ottoman top already reads high in Boarding (L117-127 vs omaat_f11 99-103), which points at
    its fabric albedo rather than the light; in ml_DSC_1945 the visible ottoman fabric sits under the table (L39-48), not
    in a comparable framing.
  - Guards: blue06 38.45 -> 38.58 mean (the contact-AO change; score 82 -> 83), blue15 28.38 -> 28.29, bl16 41.04 -> 41.00;
    Boarding / Cruise / Night / Amber take fLow 1 (q03, c06, nF03, n16, d06, dd within +-1 above).
- integration medium, stepped contact-AO bands and lost THE Suite contact lines: partly.
  1. Done: `ssaoLow` (kR) only aft of THE Room (`u_sLowZ` = 05_layout z20): the second band 3 cm above the headrest flaps is
     gone (q10 x 650 rows 380-384 L63 -> 86).
  2. Done: the disc and range capped at 16 px on screen (`LIGHT_TUNE.ssaoCap`; the raters gave 24 px, which left the flap
     band: t2 rows 398-410 L58), except on the PY / economy seats (guard above).
  3. Not done as given: the R8 AO target with the per-pixel turn and a 4 x 4 depth-aware blur adds two full-screen passes,
     which this run's brief rules out (question 13 in questions_lighting.md). Instead, 12 taps (`ssaoTaps`; every third only
     where the capped disc spans > 6-10 px, so the far cabin costs what the 8 taps cost) at strength 8 (was 6), window
     `ssaoIn` kept at 0.3.
  4. Targets:
     - q10 x 650 rows 378-410 mean L68 -> 82 (min 49 -> 52 at the flap's own contact line, rows 406-410 61-71; L8 69-78),
       rows 398-410 54 -> 75, rows 380-384 63 -> 86 (target >= 70); no stair at the flap end (qa/fixL10/c_final_q10.png).
     - y_aisle_fwd (-1.0, 1.65, 57.0, yaw 0, pitch -0.08) row 300, x 0-490: 13 steps > 6 L, max 101 -> 8 / 53 (without the
       AO 8 / 53; target no step > 60, count within +2) (c_final_yaf.png).
     - Thin dark-line share: q03 1.37 -> 1.51 % (target >= 1.7: not met), q05 1.22 -> 1.30 (>= 1.55: not met), q06 2.49 ->
       2.71 (2.4-2.7: on the line), q02 1.76 -> 1.72, q08 1.77 -> 1.89, q09 1.63 -> 1.61, q13 0.73 -> 0.89, q14 0.66 -> 0.69,
       q15 4.03 -> 4.17, q16 3.08 -> 3.19.
     - f_ink_seated row 320 (539-593) 156 -> 148 (target >= 130).
     - Frame time at Sharp: see below.
  - Tried and not kept [D fixL10 t1-t19]: 16 taps everywhere (frame time q06 / q16 / q03 +7 / +8 / +7 %); a 12 px cap
    (q03 thin share 1.08 %); the raters' ssaoIn 0.55 (q03 1.43-1.51 %, but the stepped ghost frame round the bulkhead
    monitor came back: f_ink_seated row 320 114-124); an exp(-k occ) response (q03 0.75 %); a 3.5 cm disc (y_aisle_fwd 21
    steps); the range left unscaled by the cap (f_ink 108, y_aisle_fwd max step 132); a tap weight by height over the face
    plane (f_ink 156-162 but q03 0.89-1.13 %); a softer cap ((cap / px)^0.5-0.7: q10 rows 398-410 61-67, y_aisle_fwd 12-16
    steps); no cap within 0.75 m of the eye (q14 kept, but y_aisle_fwd 19 steps, max 117). The THE Suite gap needs the wider
    window, which needs the blur pass (question 13).

from_* items (to lighting / integration): no new ones since L9. Carried, not changed this run: from_econ wave 3k-3m (q17
cover grazing tone), w43b-L1 (far q16 covers), w37-w39 (near pans), w27 (`photoBase` gain); from_shell w15 lows; from_room
w16 (1) / (3); from_py 6 / 9 / 10 / 11; from_monuments w13-15; from_exterior 17-19; from_ceiling w13. The day-pane glass
multiply (integration L10 low, shell + lighting) is handed to shell first in from_integration.md (lighting run 2, L10); the
lighting half (transmittance before aces()) follows once the tint lands.
