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
