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
