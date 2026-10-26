# Cross-area polish C: integration L11 hand-offs to suite and monuments

Items addressed to **suite** and **monuments** in `from_integration.md` (lighting run 2, L11, plus the L8-L10 ink-print
sections). Both were checked against the official photos (`ref/ana/`) and the in-flight photos omaat_f2 / f5 / f11 / f13 /
f40 / f60 (`ref/web/suite/`, gitignored; https://cdn.onemileatatime.com/wp-content/uploads/2020/01/ANA-First-Class-Suite-777-N.jpg).
Regression guard: an area's change is kept only if both raters score >= 8.5 with no high issue and neither drops more than
0.05 below its last score; at most 2 rated rounds per area.

## Suite (`09d_suite.js`) - medium, "reads cleaner than the in-flight photos": **done, kept**

Evidence held: on a black-hat thin-dark-line measure (closing 5 px, > 20 L, 930 px wide) q03 / q05 read 3.47 / 2.93 %
against 5.9-8.0 % for omaat_f2 / f5 / f11 / f13 / f40 (the integrator's own tool is not in git; the ratio, ~0.45x, agrees
with its 0.55-0.85x).

| item | change |
|---|---|
| 1. ottoman welt cushion / tray | `fSeam` #1d1a17 welt under the cushion; w18: 0.014 -> 0.008 tall (w17b: twice the f11 line) |
| 2. aisle box lid seam | 5 mm dark seam under the lid (lid not dropped: the seam alone reads, f11 L4) |
| 3. wardrobe / aisle wall joints | 5 mm dark reveal round the door leaf (door face 3 mm proud); split lines at the wood panel's edges, w18: flush, 3 mm, `fSplit` #2e2924 (w17b: black pen outline) |
| 3b. cap-to-shell joint (own addition, omaat_f40 / f5) | w17: 5 mm black box 2 mm proud -> w17a medium (black blade past the rounded shell ends); w18: 3 mm groove extruded from a rounded rect (r 0.021), 1 mm proud, `fCapJoint` #3a342e |
| 3c. console fascia / body joint (own addition, f11 / f40) | 6 mm dark line at y 0.48 on the seat-side face |
| 4. table underside | 6 mm dark strip 1 cm behind the black front lip |
| 5. SSAO quad rotation / ssaoIn | not done: `04_shaders.js` belongs to the lighting loop |

Thin dark-line share (own measure) q02 / q03 / q05: 7.65 / 3.47 / 2.93 % -> 7.92 / 3.63 / 3.22 % (w18). Rater B (own
measure) puts the renders at 3.3-8.0 % against 5.9-8.0 % for the photos. The lines are deliberately mid-dark rather than
black where the raters asked (cap groove, split lines), so the share rises less than the targets in from_integration.md
(q03 >= 1.8 % on the integrator's scale) may ask; that target is for the integrator to re-measure.
Triangles: about +200 per occupied suite unit (8 units); far LOD unchanged.

## Monuments (`10_mono.js`, shared one-line hook in `06_atlas.js`) - medium, ink-cloud print as smoke stains: **done, kept (round 1); round 2 reverted**

Evidence held: q03 top box (420-690 x 0-120) L178, range 105, h81 s0.01 against omaat_f13 print L202, range 25, h42
s0.12 and omaat_f40 strata L190, range 34, h42 s0.11.

- Round 1 (w21, kept): the clouds are now an atlas panel ('ink', 548 x 228 px over 5.9 x 2.5 m, ~1.1 cm / px, drawn by
  `inkPanel`, called from `buildAtlas`) multiplied onto a warm paper ground (`inkGround` #e9dbbf LAYER.atlasLit,
  `inkCloud` #c0b5a0): horizontal strata with speckled edges (smoothstep over 0.08 with a 5 cm speckle term), a varying
  wash inside, paper grain. The vertex-colour grid is gone; the wall keeps 4 columns x 0.1 m rows (fewer triangles).
  Print box: ink_aisle L200, range 30, h42 s0.088; ink_seated L202, range 34, s0.09. Integration targets range <= 40,
  L >= 185, h35-45, s0.07-0.13 met; fine >= 2 not met (0.6-0.8; most of the photo's 2.1 is grain / JPEG noise).
- Round 2 (w22, **reverted**): thinner strata (y / 0.14), crisper edges (ramp 0.035, speckle 0.18), 8 px pad, cooler
  colour. Rater A 8.7 (keep), rater B 8.8 -> 8.5 (medium: the higher-frequency field kept the old threshold, so the dark
  tone covered 62-82 % of the wall against 19-45 % in the photos; L201 -> 193). Under the guard `10_mono.js` is back to
  the w21 state. Next try, if anyone picks it up: the thinner strata with the threshold raised to ~0.52-0.54 (dark share
  35-45 %), a low-frequency envelope so ~35-40 % is open ground (w22a), domain warp against the blocky noise grid (w22b).

## Ratings

| area | before | round 1 (A / B) | round 2 (A / B) | result |
|---|---|---|---|---|
| suite | w16 8.7 / 8.9 | w17 8.7 / 8.9 | w18 **8.8 / 9.0** | kept (both rounds) |
| monuments | w20 8.6 / 8.7 | w21 **8.7 / 8.8** | w22 8.7 / 8.5 | round 1 kept, round 2 reverted |

No high or medium issue left in either area. Open lows: suite cap groove could go one step lighter (#4a433b, w18a/b);
w16 lows carried. Monuments: the w22 ink ideas above, white balance of the wall against the neutral ceiling (lighting),
hairlines where the monuments meet on the F front wall (w21b / w22b), the w18 lows.
