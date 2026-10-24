# Exterior gap analysis, w8 (where the remaining 1.4-1.7 points are)

Inputs: r7 renders (`/tmp/claude-0/a1e20d29-972a-5952-b92a-3befff9d861e/scratchpad/r7/`, final build e05c5e2), the photos in
`ref/web/exterior/`, the w6/w7 ratings, and `src/11_exterior.js`. All samples are PIL means over 11x11 px (photos at native
size). L is Rec.709 luma (0-255).

## Summary

The raters keep docking small marks such as the GE script, placards and the strake. Those are real, but they are not why the
area sits at 7. At window range three whole-frame problems decide the score:

1. The wing is too dark and its near-far value gradient runs the wrong way.
2. Every skin is perfectly clean: residual tone variation is 1-1.5 % against 4-7 % in the photos.
3. The canoes have the wrong cross-section. They are round socks, where the real fairings are chined wedges with a bright top
   facet.

Fix those three first, then the GE script. Placards, the strake and the movable-surface tint barely register at window range.

| # | Change | File(s) | Cost | Expected gain (A / B) |
|---|---|---|---|---|
| 1 | Lift the wing albedo, roughen it, and make the near skin brightest | 11_exterior.js | 3 lines | +0.35 / +0.3 |
| 2 | Weathering layer: mottled grime, chordwise streaks, darker hinge zones | 11_exterior.js (+03_tex.js shared line, make_swatches) | ~40 lines | +0.35 / +0.3 |
| 3 | Canoe: chined wedge section, crisp facet shading, tip closing at mid-height to a point | 11_exterior.js | ~10 lines | +0.25 / +0.25 |
| 4 | GE swirl script monogram plus the small "GE" wordmark | 11_exterior.js | ~30 lines | +0.1 / +0.1 |
| 5 | Placards as ringed stencils, plus 4-6 small dark stencils on the flaps and spoilers | 11_exterior.js | ~10 lines | +0.05 / +0.05 |

Items 1-3 together are worth about +0.9 to +1.0, which would bring the area to about 7.8 / 8.0. Reaching 8.5 also needs the
lighting-owned sky and blue-cast items (`from_exterior.md` 8-11) and item 4.

---

## 1. Value and tone structure: the wing is ~20 % too dark relative to the clouds, and the near skin is the darkest part (highest impact)

**Evidence**

Wing skin luma against the brightest neutral in the frame (cloud deck or ground):

| Image | Near skin | Far / outboard skin | Cloud or ground | Wing / cloud |
|---|---|---|---|---|
| KN46 `a5_kn_*_46` (200,650) / (780,470) | **221** #dcdcdd | 207 #cecfd2 | cloud 230 (250,470) | **0.90-0.96** |
| KN41 `a5_kn_*_41` (300,420) / (760,300) | **195** #bbc3d0 | 147 #8395ae | cloud 228 (1100,700) | **0.65-0.86** |
| `b_alv_*_7250` (500,550) | 217 #cbdbe8 | - | ground 113 | wing is 1.9x the ground |
| render w19A (620,500) / (620,250) | **126** #747e93 | 152 #8e99a9 | cloud 206 (470,300) | **0.61-0.74** |
| render w17K (300,450) / (380,220) | 161 #9ba2ac | 155 #939cab | cloud 217 (780,300) | 0.71-0.79 |
| render w26K (560,270) | 162 #99a2b2 | - | cloud deck 212 (600,480) | **0.76: the wing is darker than the deck** |

- In every ANA photo the wing is the brightest large surface in the frame after the clouds. In the renders it is a mid grey,
  and in w26K and w30K the cloud deck below outshines it. That inverts the figure and ground: the wing reads as a grey cut-out
  laid on a bright backdrop.
- The near-far gradient is reversed. In the photos the near inboard skin is brightest: KN41 195 -> 147 toward the tip, KN46
  221 -> 207. In w19A the near skin is darkest (126 -> 152 outboard). The cause is grazing sky reflection: with r 0.5 the far
  skin picks up Fresnel sky, while the near skin is diffuse-only on a low albedo (`paint #636466`).
- The same grazing sky term makes the wing blue. w19A shows b-r +27..+33 against KN46 +1..+11 and KN41 +21 (KN41 has a deep
  blue sky). The wing reads as "clean flat CG grey-blue" largely for this reason; texture is the secondary cause.
- The `paint` albedo was tuned in w1 to an Air France photo (F-GSQR_1, comment at line 169). The ANA KN Aviation photos, which
  are the best-matched references, are 25-50 L brighter.

**Fix (11_exterior.js, lines 171-172)**

- `paint = { c: '#76787a', r: 0.62, m: 0.05 }`. This raises albedo about 1.2x in linear light. The higher roughness flattens
  the grazing Fresnel lift and the blue cast. Set `paintLow` to `#6d6f71`.
- Re-render w19A and w17K. Target near skin L 175-195 and wing/cloud 0.82-0.92. Check that the sun-side cowl and the w17K skin
  do not clip (L <= 235).
- If the near skin is still darker than the far skin, add a mild near-to-far albedo ramp inside the `paintVerts` callback:
  `f *= lerp(1.06, 0.94, clamp((sp - 6) / 22, 0, 1))`. This makes the inboard skin brighter. It is the baked equivalent of the
  photos' sun-lobe sheen, which is broad on rough paint.
- Keep the ink, gap and stripe colours as they are. The ink/skin contrast improves for free (ink #414e70 L 78 in w17K against
  skin 161 now, which goes to about 0.4 of the brighter skin, inside the photos' 0.07-0.41 range).

**Expected gain:** about +0.35 (A) / +0.3 (B). It touches all 8 day views and lifts "wing surface", "livery", "control
surfaces" and the overall realism impression at once.

## 2. Surface texture realism: the skin is 3-5x too uniform (grime, streaks, hinge-zone darkening)

**Evidence.** Residual luma SD after removing a planar gradient, on flat skin patches. Photos are downscaled to render pixel
density.

| Patch | Mean | Residual SD | p5 / p95 |
|---|---|---|---|
| KN41 flap + fixed skin (530-700, 500-640) | 173 | **4.5 %** | -8 / +6 |
| KN46 inboard skin (100-400, 560-700) | 213 | **4.1 %** | -13 / +7 |
| 7250 fixed skin (300-900, 560-680) | 224 | **3.6 %** | -18 / +6 |
| 7250 inboard flap (40-500, 620-900) | 218 | **7.1 %** | -24 / +8 |
| LALF 11A _136 cowl (50-450, 780-1050) | 123 | 5.1 % | -8 / +7 |
| render w17K near skin (200-460, 400-520) | 161 | **1.0 %** | -0 / +1 |
| render w17K mid skin (200-330, 230-330) | 172 | **1.5 %** | -3 / +4 |

- The photos are not noisy: the variation is skewed dark (p5 is 2-3x p95). It is grime, which is darker marks on a clean
  ground, not symmetric speckle.
- The 7250 inboard flap (behind the engine) shows mottled grey patches and chordwise streaks. LALF _136 shows horizontal
  streaks along the lower cowl, aft of the lip. KN41 shows soot at fastener heads and hinge fittings, e.g. (490,830).
- The existing +-7.5 % per-panel jitter cannot read as weathering. It is a few large flat steps per panel, and the wing mesh
  is too coarse for per-vertex grime.
- **Confirmed: "clean flat CG grey" is real and matters at window range.** w17A and w17K show about 60 % of the pane as
  featureless skin.

**Cheapest code path.** A triplanar weathering layer, using the engine's existing detail-layer system.

- **Gotcha.** The shader takes the albedo of layers >= 16 from the photo array whenever `u_photoOn` is set
  (04_shaders.js, around line 131). A new procedural layer 27 would get neutral grey from `buildPhotoLayers`, which means no
  albedo change in the shipped build. There is no free slot below 16. Pick one of these routes:
  - **(a) Preferred, keeps the "photo-derived" rule.** Add `27: 'ext_grime'` to `PHOTO_LAYERS` and have
    `test/make_swatches.py` write a synthesised tile, as it already does for `synth_py_back`. Make it a 4 m x 4 m physical tile,
    256 px (1.6 cm/px), luminance only:
    - ground 1.0
    - fbm mottling at 0.6-1.5 m scale, depth -6 %
    - streaks elongated 8:1 along the tile v axis, depth -4 to -10 %, covering ~25 %
    - sparse dark specks, about 1 per 0.3 m², -15 %
    - Calibrate it so a flat patch renders residual SD about 4 % with p5/p95 about -10/+5. The stats can be measured on
      7250 (40-500, 620-900) and KN41.

    Then set `N_LAYERS = 28`, `LAYER_PARAMS[27] = [0.25, 0.0, 1.0, 0.15]` and `PHOTO_GAIN[27] = 1.0` (one line per key in the
    shared 03_tex.js; say so in the commit message).
  - **(b) One shader line, owned by lighting.** Change the condition to `layer < 16 || layer >= 27 || u_photoOn < 0.5` and add
    a procedural `L[27]` in `buildDetailLayers` with the same recipe.
- **Axis check.** On the upper wing the normal is mostly +y, so the shader samples `q.xz`: tile u = world x (span), tile v =
  world z (chord, aft). Streaks along v therefore run chordwise, which is the airflow direction, as in the photos. This is the
  one weathering pattern that world-aligned triplanar gets right without UVs. On the cowl's side faces it samples `q.zy`, so
  stretch along u there as well, or accept isotropic mottling there.
- **11_exterior.js.**
  - Set `paint.l = 27` and `paintLow.l = 27`, and cowl `l = 27` at `PHOTO_GAIN` 0.6. The cowl is cleaner; LALF _136 is 5 %.
  - Leave `metal`, the ink, gaps and lines at layer 0.
  - Add one per-vertex term in the existing `paintVerts` callback: `f *= 1 - 0.06 * smooth(0.4, 0, Math.abs(xn - x0))`. This
    darkens a ~0.4 m band at the spoiler/flap hinge lines (the KN41 hinge fittings), plus -8 % on the inboard flap behind the
    engine (s 8-12 m).
- **Cost.** About 25 lines of Python plus 3 lines in 03_tex.js and 3 lines in 11_exterior.js. One texture fetch is already
  paid for by the triplanar path.

**Expected gain:** about +0.35 (A) / +0.3 (B). It lifts "wing surface detail" from 6.5 to about 7.5 and "nacelle colour" from
6.5-7.0 to about 7.3, and it removes the generic "CG" verdict that caps every other sub-score.

## 3. Silhouette: the canoe is the wrong cross-section (round sock), not just the wrong tail

**Evidence.** Crops: `/tmp/claude-0/-home-user-Calc/a1e20d29-972a-5952-b92a-3befff9d861e/scratchpad/c7250_inbd_canoe.png`
(7250 at original (0-600, 950-1350)) and
`/tmp/claude-0/-home-user-Calc/a1e20d29-972a-5952-b92a-3befff9d861e/scratchpad/w26K_canoe.png`.

- **Real (7250, inboard canoe).** The fairing is a chined wedge.
  - A flat upper facet, L **223-231** (#e0ebef at the mid canoe), meets a flat lower flank, L **120-130**, at a crisp ridge.
    The step happens within about 15 px of 2560 (vertical profile x=250: 213 -> 130 between y 1140 and 1160; x=400:
    226 -> 129 between y 1160 and 1180).
  - The ridge runs straight from the TE to the tip. The top facet narrows aft, and ridge and keel converge to a **sharp point
    at roughly mid-depth**.
  - A row of drain or fastener dots runs along the ridge, and a small dark stencil sits on the flank.
  - The ratio of the two facets, about 0.55, matches what both raters measured. The difference is that it is a step, not a
    gradient.
- **Render.**
  - `sec()` uses `r = min(w*0.46, d*0.44)`, which gives a near-elliptical section.
  - `shadeVerts(0.55 + 0.45*((n.y+1)/2)^1.3)` produces a soft gradient. In w26K the column x=600 runs 218 at the top, then 204,
    173, 136, 131, 127, then a **dark keel rim of 68** at y 385.
  - That rim, which comes from the rounded bottom curling into view, and the soft roll-off are what read as a "sock" or
    "boot".
  - The top line falls only 0.03 m per m aft of the TE, so the tip sits at the top of the pod.
  - The `+0.04` depth and `+0.03` width constants in `sec()` leave a 4 x 3 cm blunt face at the tip. It is visible as a round
    stub in `c_canoe_side.png`.
- **Size and placement are fine.** In w26K and w30K the pods are 0.30 of their length behind the TE, which is consistent with
  7250 and 7282. Do not resize them again.

**Fix (canoe loop, lines 284-297)**

- **Section.**
  - Set `r: Math.min(w * 0.12, d * 0.10)` to get box shoulders that give a crisp chine.
  - Narrow the lower half for a wedge: either scale `w` by `lerp(1, 0.55, ...)` on the lower ring points (a two-ring section
    if `gLoft` cannot taper), or, cheaper, keep the rounded rectangle with the small r and rely on the facet shading below.
- **Shading.** Replace the canoe `shadeVerts` with a step:
  `(p, n) => n[1] > 0.45 ? 1.0 : n[1] > -0.2 ? 0.56 : 0.48`. This gives a top facet at the paint value, flanks at 0.56 and a
  belly at 0.48. Paired with item 1's brighter paint, that lands at roughly top 215 / flank 120, as in 7250.
- **Tip at mid-height.** `topAt` for `xn > te`: subtract `0.42 * (0.85 * 1.0 + 0.04) * Math.pow((xn - te(cs)) / (x1 + RE - te(cs)), 1.2)`.
  This drops the top line by about 0.37 m at the tip, against 0.03 m now.
- **Tip point.** In `sec()` scale the constants by the size: `d = 0.85*rd + 0.04*Math.min(1, rd*4)` and
  `w = 0.46*rw + 0.03*Math.min(1, rw*4)`. Use a final cap section of `rw = rd = 0.02`.
- **Ridge dots (optional).** About 8 dark dots along the ridge using the `cowlPatch`-style `gSphere` used for the LE heads.

**Expected gain:** +0.25 / +0.25. The canoe sub-score moves from 5.5-6.0 to about 7.5, and it is visible in w19A, w26K, w30K
and w17A.

## 4. GE mark: the swirl script monogram (close-up only, but scored)

- **Confirmed** (rater A and B, knav `b5_knav_*_9` at (270-330, 855)).
  - The real mark is the GE swirl script in a ring with four flourish tips, plus a separate small "GE" wordmark. The render has
    block G and E letters in a ring (lines 339-350).
  - No passenger view shows it, because in w11A and w13A it is below the window sill. So it moves only "nacelle colour" (6.5-7.0)
    and only through the close-up.
- **Cheapest.** Keep the ring and replace the letter polylines with a script made of two Catmull-Rom tube paths through
  about 12 control points each:
  - a "G": an open loop with a tail curling in
  - an "E": a three-lobed scroll
  - four short comma-shaped flourishes from the ring inward at 45°, 135°, 225° and 315°

  Draw them with the existing `at(u, v)` cowl mapper and `gTube(..., 0.02, 4)` in `#2a2f3a`, ring R about 0.30 m. Add the
  wordmark as two 0.12 m block letters 0.45 m forward on the same line.
- **Expected gain:** +0.1 / +0.1.

## 5. Placards: tone them down to ringed stencils, and add a few dark stencils

- **Partly confirmed, minor.** At window range the placards read as pink specks (w17K (461,319) #ac7f89, b-r -35;
  B: #c5666e in w26K).
  - In KN41 the one visible placard, at (285,553), is a red **ring** with a light centre and a short black text line beside it.
  - KN41 and 7250 also show small black stencils near the spoilers and flaps (KN41 (310,545); "no step" lines), which the
    render lacks.
- **Fix.**
  - Draw each placard as a 0.16 m ring: a `gTube` circle in `#7a3a3c`, with no fill.
  - Add one 0.25 x 0.03 m dark `#3a3d42` dash beside each placard.
  - Add 4 more dashes per wing on the inboard flap and spoilers.
- **Expected gain:** +0.05.

---

## Recurring complaints: confirmed or rebutted

| Complaint | Verdict at window range |
|---|---|
| Clean flat CG grey skin | **Confirmed, top issue.** It comes mostly from value (item 1: too dark, blue, reversed gradient) and secondarily from no weathering (item 2: 1 % vs 4-7 % SD). |
| Movable-surface tint invisible | **Rebut / drop.** It actually renders (w19A spoiler 139 vs fixed skin 149, -7 %), and the photos show only -2 to -8 % (KN41 skin 187 / spoiler 177 / flap 172; KN46 221/219/212). It looks invisible because the skin has no other variation. Item 2 fixes the perception. Do not push the tint further. |
| Canoe reads as boot or sock | **Confirmed, but the diagnosis was wrong.** The w5-w7 tail rewrites (spike, blunt, bullet, straight keel) treated it as a profile problem. The persistent cause is the round section with a soft gradient and a dark keel rim, against a chined two-facet wedge in 7250 (item 3). |
| GE mark is block letters | Confirmed. Close-up only, so low leverage (item 4). |
| Placards read as red specks | Confirmed, minor (item 5). |
| Strake reads as a plank | **Rebut for scoring.** It is not visible in any QA view; B says so too. Leave it. |
| Engine visibility (w11A vs LALF 11A) | Not a model fix. The LALF photos are phone wide-angle shots taken with the camera against the window, so the cowl fills about 60 % of the frame. Size and geometry match _136 and _137. Do not rescale. |
| Panel-line crispness | Fine. The hierarchy (TE gap strongest, breaks faint) matches KN46 and 7250. Only B's dotted 0.014 m spoiler breaks in w19A remain; widening to 0.02 fixes that, at trivial cost. |
| Specular / sheen | Part of item 1. The grazing-sky Fresnel at r 0.5 is what makes the far wing brighter and bluer than the near wing. Raising roughness to 0.62 is the fix, not more gloss. LALF _136 and _137 do show cowl reflections, but cowl r 0.3 already has that. |
| Sunset / night colour casts | Lighting-owned (`from_exterior.md` 8-11). In s13A the left pane wing renders saturated navy-violet and the cowl lavender. These need fixing for 8.5, but in 12_scene.js, not 11_exterior.js. |
