# From exterior → lighting (`src/04_shaders.js`, `src/12_scene.js`)

Evidence photos are in `ref/web/exterior/` (gitignored; re-fetch URLs are in `review/qa/exterior_w1a.json` / `_w1b.json`).
The ANA ones are seat-confirmed: `lalf_ANA77W_NH212_136/137` (11A) and `alv_ANA77W_NH211_26K_*` (JA795A, 26K).

1. **Exterior ambient has no cloud-deck bounce (high).** In `mainFS`, the `u_exterior` branch is
   `amb = mix(u_skyBot, u_skyTop, N.y*.5+.5)`. That leaves every shaded side or underside of the wing, canoes, pylon and
   nacelle dark slate: canoe flanks away from the sun render about #4a5263. In photos they are lit by the white deck:
   shaded flank about #8090a0, belly #59636c, wing #c0ccd4 (`alv_*_7331`). At sunset the same term turns the canoes cream
   (#b6966a), brighter than the wing.
   **Fix:** for the exterior, use `amb = mix(u_cloudLit*0.55 (or a new u_extBounce per sky), u_skyTop, smoothstep(-0.6, 0.8, N.y))`.
   Then I can drop the hand-baked flank fills in `11_exterior.js` (the canoe ×1.25 and pylon ×1.6). Keep sunset's deck
   bounce dark and cool, about #2d3240 × 0.4.
2. **Day sky too pale at the window (medium).** The top of the pane is about #acc2d7 and the horizon #abb2bb. Cruise photos
   show #114892–#2472ca overhead with bright white cloud tops (F-GSQR_1/_2, `commons_Wing_of_a_Boeing`).
   **Fix:** `SKIES.day` zenith [0.03, 0.12, 0.48], horizon [0.35, 0.55, 0.88], haze [0.55, 0.66, 0.85] (haze confined to
   the lowest ~4°). Apply `winExp` only to the interior, or reduce it to about 1.2 near the window. The pale sky also
   flattens the white cowl, which is nearly sky-coloured now.
3. **Sunset (medium).** The upper sky is dusty pink and the deck bright beige (#c7b5a9). Photos show a blue upper sky, a
   narrow orange band, and a dark violet or near-black deck (`Emirates_77W_wing_view`, `yt_p97zMaCMWRg_*`,
   `alv_*_7282`: wing #496896 under a #527dc2 zenith).
   **Fix:** skyTop [0.18, 0.24, 0.55], zenith [0.08, 0.14, 0.42], haze [0.55, 0.40, 0.42] within 6° of the horizon,
   cloudLit [0.60, 0.40, 0.45], cloudShade [0.10, 0.08, 0.14]. Scale the grazing sun on the exterior by about 0.35 so
   the wing takes the sky colour, not warm brown.
4. **Night beacon (low).** `buildExterior` returns `lights` (nav and strobe). Real night views show the belly beacon
   washing the lower cowl red-orange (`yt_p97zMaCMWRg_EVA77W_night_beacon`). If you add a point-light term for blinking
   exterior lights on the exterior layer, I will push a beacon entry
   `{ p: [0, -2.5, 32.8], c: [3, 0.25, 0.1], s: 8, blink: 1.0 }`.
5. **QA views (low).** Every exterior QA view is on the A side. The right wing carries the ANA registration (JA795A),
   and the right engine's inboard strake faces the K windows. Please consider adding `q23_wingK: __look('26K')` to
   `test/qa.js`. (It is not my file; my scratch renders cover 11K/17K/26K/30K.)
6. **Exterior sun exposure headroom (medium, added in w3).** At the day sun of 5.2, even a #a6a9ad cowl albedo renders
   #dee0e1 on the sun side (13K, 11K). ACES saturates, so the split lines, pylon hump and falloff vanish; photos show
   #9fabb7–#a9c0ce with a clear gradient. The sunset cowl (s_13A) glows cream the same way. **Fix:** scale `u_sunCol`
   by about 0.6 for the exterior draw (`u_exterior = 1`), or give the exterior its own exposure of about 0.7 × winExp.
   The wing (#636466) is fine either way, since it renders #b6bcc2.

## Round w5 (after the user's answers)

7. **FYI, done by exterior at the user's direction ("use deep-blue sky").** These are small edits in your files; please
   keep them.
   - `04_shaders.js` skyFS: new `uniform float u_skyK`. When it is > 0, the horizon-to-zenith blend is
     `1 - exp(-skyK*h)`; otherwise it is the old `pow(h, 0.42)`, so sunset and night are unchanged.
   - `12_scene.js`: `G.set('u_skyK', sky.skyK || 0)` next to `u_zenith`. `SKIES.day` gets zenith [0.019, 0.05, 0.095],
     horizon [0.20, 0.37, 1.0] and skyK 12, fitted to the F-GSQR_1/_2 cruise gradient: #95bee8 at the horizon,
     #3b66a4 at 8.5°, #234879 at 15°, #193c60 overhead.
   - Aisle panes at winExp 3 still read near-white (checked on q06 and a q16-like view), so `winExp` is unchanged.
   - Thanks for extBounce, extSun and the `light` gain. Exterior dropped its hand-baked canoe and pylon flank fills and
     now pushes the belly beacon (`light: 8`, blink 3.3).

## Wave 3 (w5-w6 raters, both agree; to lighting)

8. **Sunset wing saturated royal blue (medium).** In s26K the skin renders #3a4474 and the canoes are deep navy. The dusk photo
   `alv_*_7282` shows a grey-blue wing, about #6f83b7. **Fix:** desaturate the exterior ambient at sunset, e.g. mix `u_skyTop`
   toward its luminance by ~0.5 for the exterior draw, or lower the `SKIES.sunset.skyTop` blue to about [0.22, 0.25, 0.42].
9. **Belly beacon paints the canoes red (low).** In n19A the canoes read as red-painted. The beacon (`light: 8` from
   `buildExterior`) should wash mainly the lower cowl and wing underside near the body. **Fix:** attenuate the exterior point
   light with distance squared beyond ~10 m, or cap it with `max(0, -N.y)` so the wash stays on undersides facing it. I can also
   lower `light` on my side if you prefer.
10. **Sun-side cowl still clips (medium, repeat of 6).** w11K cowl #dadfe2 flat across the lit face.
11. **Window reveals / lining royal blue in day views (low, shell + lighting).** Noted by rater B in every day view at cruise mood.

## Wave 3b (w8-w9 raters; to lighting)

12-13. **Withdrawn (w10).** The bright canoe keel band and the charcoal shade-side flanks were an exterior bug: since w8 the canoe
    lofts were inside out (a zero-size first ring defeats gLoft's orientation check, found by rater A w10). Fixed in 11_exterior.js.
    Nothing is needed from lighting.

14. **Grazing sky reflection reverses the wing's near-to-far gradient (medium, w11 rater B).** In w19A the near flap is L161 and the
    far skin L178. In KN41 the near skin is brightest (196) and the far skin falls to 129-145. Exterior already ramps the albedo
    1.12 -> 0.80 and raised the roughness to 0.72, but the far skin seen at grazing reflects `u_skyTop*1.2` regardless of the baked
    colour. **Fix:** in the exterior branch scale `specEnv` by the baked/base colour ratio (or by `v_col` luminance), and reflect
    the deeper zenith blue for R.y > 0.3.

## Wave 3c (w12 raters; to lighting / integration)

15. **Look-out framing in the aft K seats hides the registration under the shade rail (low, camera).** In w26K / w30K the app's
    `lookOut` (13_app.js) puts the eye 0.33 m inboard of the glass at y 1.16 with pitch ~-0.16; the shade rail then covers the
    top of the pane and JA795A is cut off. The JA795A seat-26K photos (alv `IMG_7345`, `IMG_7250`) are taken with the camera at
    the glass, looking ~20 deg down. **Fix:** in `lookOut`, eye `side * 2.72` and y 1.10, and lower the target 0.06 m (pitch
    about -0.22). The exterior review cameras (`review/qa/exterior_views.js`, w26K / w30K) already apply this offset and show the
    whole registration.
16. **Item 14 still open (medium).** w12: near flap L163, far skin L173 (w19A). A per-vertex roughness ramp (0.72 -> 0.92
    outboard, w12) only took ~4 L off the far skin, so the albedo-blind grazing `specEnv` term is the remaining lever.

## Wave 3d (w16 raters + gap analysis; to lighting)

17. **The albedo-scaled exterior sky reflection (8d7ae91, `04_shaders.js` ~l.443) is a no-op on the wing (low, FYI).** It divides
    the baked luma by 0.39 (the old #636466 paint). The wing is #76787a now (luma 0.47), so the factor clamps to 1 on nearly every
    wing vertex and w19A moved <= 1 L (r15 -> r16). The gap analyst also showed the near-far reversal was mostly diffuse (no exterior
    sun spec at all only took 5 L off the far skin), so exterior fixed it in albedo (w17 ramp 1.22 -> 0.66). **Fix:** renormalise to
    0.47, or drop the term; either way nothing more is needed from lighting for the near-far value.
18. **Long-hairline aliasing on the wing at 20-30 m (low, A artefacts).** The hinge / gap strips shimmer in w26K / w30K. Only MSAA
    or a supersampled exterior pass fixes it; exterior already widened the strips to the limit.
19. **Night nav light washes only down-facing faces (low).** The red/green tip light (`lights` from buildExterior, no `light` gain)
    could wash the upper raked tip faintly at night (point light within ~1.5 m). Optional.

## Final confirm (2026-10-26, head 1430d42): to lighting, low, optional

Exterior passes (A 8.5 / B 8.7), and the exterior itself is unchanged since w22. Both raters noted one low lighting item.
- **Problem.** The glass-keyed look-out exposure lifts the day exterior by 5-9 levels and weakens its cool cast. The w17K near wing
  is (214-217, 217-220, 222-225) against (187, 195, 208) in KN41, and B-R is 8 against 21. w19A (170/179/195) is within the
  photo range.
- **Fix if wanted.** Apply about -3 to -5 % exterior exposure, or a slightly cooler exterior fill, on day look-out views. Check
  that w19A stays in range.
- **Evidence.** The rating files `exterior_final_a.json` and `exterior_final_b.json` (lightingNotes).
- **Lighting final touch (71fdda1):** done, small: day look-out exterior exposure -4 % (SKIES.day lookExt); w17K near wing 217/219/224 -> 215/217/223 (on the tone shoulder); w19A in range.

## Final confirm 2 (2026-10-27, head 8467f01): to lighting, low, optional

Exterior passes (A 8.5 / B 8.7). The 71fdda1 lookExt -4 % lowered the w17K near wing only from 214/217/222 to 212/215/220, and
B-R is still 8. KN41 measures 181/193/210 on the upper panel (B-R 30) and about 165/174/186 on the mid panels (B-R 20-22).
- **Fix if wanted.** Use a cooler exterior fill on day look-out views (about B +6..8, R -4) instead of a further exposure cut.
  Keep w19A (170/179/195) in range.
- **Evidence.** The lightingNotes in `exterior_confirm2_a.json` and `exterior_confirm2_b.json`.
