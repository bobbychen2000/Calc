# Ceiling / bins area report

- **Scope:** aisle ceilings, cove light, grille, outboard and centre bins, latches, PSUs, signs, placards and EXIT signs.
- **Files:** `src/07b_ceiling.js` and `src/08_bins.js`. No shared files were edited.
- **Method:** four rounds of rating by two independent raters (A: skeptic; B: geometry first), with fixes after each round.
- **Rating files:** `ceiling_w{1..4}{a,b}.json`. The previous rating was `ceiling_r2.json` (6.3).

## Scores

| Round | Rater A (skeptic) | Rater B (geometry) | Mean |
|---|---|---|---|
| r2 (before this session) | 6.3 | 6.3 | 6.3 |
| w1 (fresh re-rate) | 5.2 | 6.2 | 5.7 |
| w2 | 6.1 | 7.1 | 6.6 |
| w3 | 6.8 | 7.5 | 7.15 |
| w4 | 7.2 | 7.8 | 7.5 |

- **Target not reached.** The target was 8.5 from both raters. Four rounds is the brief's limit. No high-severity issue is open after w3.
- **Last fixes not rated.** The medium and low w4 findings were fixed after the w4 rating, in commit bca62e5:
  - vault brightness next to the grille
  - PSU wells that read as grey stickers
  - white rings in the centre light well
  - brown ground in the sign windows
- **Round-1 scores dropped for a reason.** The raters downloaded about 45 real in-cabin photos into `ref/web/ceiling/` (gitignored), and those photos showed errors r2 had not caught.

## What changed (by evidence)

1. **Grille and cove light on the outboard edge only** (w1 high, both raters).
   - Five real photos show the slotted grille and cove light only along the outboard bin top, in both aisles: b_lalf_c119, b_sany_y12, b_sany_y22 (both aisles in one frame), thrifty_j_cabin-1 and sany_py_10.
   - The model had both edges. Now there is one grille per aisle and a plain centre-bin crease, and the centre-bin LED is replaced by a filler.
   - ANA's y_47301 seems to disagree (see the questions).
2. **The grille has fore-aft slots, not transverse slats** (w1 high, A).
   - The b_lalf_c119 close-up shows 4–5 longitudinal slots in segments with solid bridges.
   - The grille is now a slim 0.05 m strip with 4 mid-dark slits, 2 segments per panel, and a bridge on every panel joint.
3. **Cove diffuser band** (w2/w3 medium).
   - A near-white lit band 3–4× the grille width runs from the bin crest to the grille, as in c119 and y22.
   - The grille is at t 0.24.
   - The vault falls off from the grille toward the centre bin: lower emissive, plus a baked ×1.0 → ×0.84 colour falloff.
4. **Centre bin** (w1–w3).
   - The channel narrowed from 0.84 to 0.48 m, with broader door wraps. The 4-fitting well now fills about 0.67 of the channel, as in b_sany_y22 / y_47300.
   - The channel reads recessed (0.85 of the door tone; the photo gives 0.76–0.87).
   - The bin shading is continuous in the normal, which removed the w1 banding. The Catmull-Rom door section is kept.
5. **PSUs.**
   - Outboard: a recessed stadium well per window bay, across the band, holding 2 eyeball lights or 2 gaspers on alternate bays (thrifty_j_overhead-vent, b_lalf_c26). The old proud box is gone.
   - Centre: a light well and a gasper well with 4 fittings each, and a long smoked sign pill. The O2 plate outline and the unverified call button were removed.
   - The wells are dished and band-coloured.
6. **Signs.**
   - Flush smoked pill windows with amber icons and red accents (c26: a red ring on the no-smoking sign, a red arrow on the seat-belt sign). They replace the black proud pods.
   - The icon quad keeps the atlas aspect. This fixed a w3 high: a z-fight and stretched icons.
7. **Outboard doors.**
   - A top rail carries the row placard. It sits at RAIL_Y 2.105, so the placard faces the aisle. At 2.163 it had drawn edge-on (w2 high).
   - The latch is a true stadium. `gPlate` was added because `gRBox` squares its corners on thin plates.
   - Module seams are 6 mm flush hairlines instead of 12 mm dark gaps.
8. **Vault fittings.**
   - A rounded-rect speaker (0.34 × 0.10 m) with a perforated face (c119). Rater A withdrew their round-1 "slim strip" claim as a perspective artefact.
   - The emergency light is a light frame round a grey lens.
   - Panel joints are 8 mm and lighter.
9. **Artefacts.**
   - The zone-end header closures and the extended centre panel removed the sky leaks.
   - The bin body, band and wash lens now run the full module length.
   - The monument light panel is near flush.
   - EXIT sign housings are light and double-faced.
   - The door domes are lighter.

- **Triangles:** ceiling and bins went from 53.6k to 54.4k (+0.8k, +1.5 %). Everything new is instanced per module or per PSU, as before.
- **Before/after sheet:** `ceiling_before_after.jpg`, own renders only, 210 KB. The q06/q16 "before" frames also contain other areas' old state.

## Sources used (all real photos win over ANA renderings)

- **Official ANA photos** (ref/ana): y_47300, y_47301, py_37302, c_27312.
- **Real photos** (ref/web/ceiling, downloaded by the raters):
  - Live and Let's Fly (b_lalf_c119 ceiling/grille, b_lalf_c26 PSU + sign close-up)
  - SANspotter economy (b_sany_y10/y12/y22) and premium economy (sany_py_*)
  - Thrifty Traveler (thrifty_j_cabin-1, thrifty_j_overhead-vent)
  - Frugal Flyer (seat vents)
  - OMAAT
- **Boeing D6-58329-2:** the outboard bin lip at 1.58 m (the shell worker's measurement) agrees with the model's bin bottom at the sidewall (1.60 m). Not changed.
- **Code comments:** every value in the two files carries a [V], [D] or [A] tag and its photo.

## Open issues (w4, after the last fixes)

- **Centre channel is flat.** b_sany_y22 shows many raised transverse steps; the model has plain panels with irregular joints. (A, medium)
- **Outboard band lacks raised modules.** The stepped PSU modules and ribbed filler strips in thrifty_j_overhead-vent are not modelled. (A and B, low)
- **Vault joints are plain arcs.** In c119 they are raised ribs that sweep aft along the centre-bin crest. (B, cosmetic)
- **Centre door has no rail.** c119 shows a raised placard rail there. (B, cosmetic)
- **Light-blue hairline at the outboard band edge.** It is the blue sidewall wash lens (layer 12 → u_sideLed) at the bin/sidewall joint. The raters read it as sky. It is left as is: the c26 close-up shows a blue light strip in that place.
- **Door-area ceilings are unverified.** No photo was found (see the questions).

## Handed to other areas (`from_ceiling.md`)

- **Integration:** the q01_door1 camera (the q13 camera was already fixed). The raters also note that q15 no longer shows the ceiling.
- **Monuments:** the black-edged wood panel over the door-3 cross aisle. It belongs to `monuments`, not the ceiling.

## Questions for the user (`questions_ceiling.md`)

1. **Grille side.** Five real photos put the grille outboard. ANA's official y_47301 seems to put it by the centre bin. Is that photo mirrored or retouched?
2. **Centre PSU in economy.** Is there a close photo? The model uses a light well plus a gasper well, and Rater B reads y_47300 as confirming the two rows.
3. **Door-area ceilings.** Do you have any photo of a door-area (cross-aisle) ceiling?
4. **Centre-bin underside.** Is there a straight-up photo of it, to confirm the channel/bin width ratio?
5. **Ceiling gaspers over THE Room.** Should the centre-bin PSUs over THE Room middle seats keep gaspers? b_frugal_c_vents shows gaspers on the seat shell; thrifty shows overhead gaspers on the outboard band.

## Wave 3 (2026-10-24)

- **Start point:** w4 (A 7.2 / B 7.8). Six rounds, w5 to w10, which is the wave-3 cap.
- **Result:** A 8.4 / B 8.7, mean 8.55. No high or medium issue is open.
  - Rater B has met the 8.5 bar since w8. Rater A finished 0.1 short, with low issues only.
- **Rating files:** `ceiling_w{5..10}{a,b}.json`. Both raters were calibrated against their previous two files each round.

| Round | Rater A | Rater B | Mean |
|---|---|---|---|
| w5 (fresh, current head) | 7.0 | 7.9 | 7.45 |
| w6 | 7.6 | 8.2 | 7.9 |
| w7 | 7.9 | 8.3 | 8.1 |
| w8 | 8.1 | 8.5 | 8.3 |
| w9 | 8.3 | 8.6 | 8.45 |
| w10 | 8.4 | 8.7 | 8.55 |

- **No regression rounds.** The w5 drop of 0.05 is below the 0.3 guard, and no round scored below the previous one.
- **Triangles:** 414k → 488k instanced (+18 %; budget +25 %).
  - Most of the growth is in the shingled PSU strips, the PSU housings and the vault ribs.
  - Everything is still instanced per bin module or per PSU, except the ribs and the door-3 soffit, which are in the one `upper` mesh.
- **Before/after sheet:** `ceiling_before_after.jpg`, w5 against w10, own renders only, 169 KB.

### What changed (wave 3), by evidence

1. **Door-3 bar cross-aisle soffit** (w5a high).
   - The first real photos of a door-area ceiling, b_lalf_c133/c134 (liveandletsfly THE Room review), show a dark bronze ceiling, not the white dome.
   - The model now has a flat dark soffit from wall to wall (#4f4743) at y 2.43, and a #5c524d tray at y 2.40 with a mid-tone trim.
   - Fittings: 10 downlights, a louvre and a rimmed speaker grille.
   - The zone-end closures next to it are dark too, out over the cove, grille and bin-crest ends. That fixed the "white arcs" reported four times.
   - Only door 3 has the soffit, because no photo shows doors 1, 2, 4 or 5 (see the questions).
2. **Vault tone.**
   - The colour is #e6e4df. A baked falloff runs from x0.85 at the grille to x0.66 at the centre-bin crease, with a low eFn.
   - It is applied after the ribs and fittings, so they follow it.
   - Measured result: 0.79 → 0.59 of the cove band (c119/c120: 0.83 → 0.58).
3. **Raised joint ribs.**
   - Each rib has a light face (about 1.06x the vault) and an aft shadow lip. It starts at the grille frame and turns forward on R 0.3 m into a fore-aft crest rib along the centre bin (b_lalf_c120).
   - The vault arc is sampled at N 48.
4. **Cove band.**
   - The grille moved to t 0.29, with 3 segments per panel and backlit light slots.
   - The diffuser is 4 facets that follow the arc. A single flat chord sank behind the vault and read only 1–1.5x the grille; the facets read about 3–4x, as in c120 and rb_omaat_room37.
5. **PSU band.**
   - Shingled transverse strips, 8 per module, with a 5 mm self-lit step (y_47301 ribs, b_lalf_c26, rb_omaat_room23).
   - The light/gasper and sign units are raised housings.
   - The black lip slot became a thin mid-grey line.
6. **Economy centre PSU.**
   - One raised dished housing with 4 dark sockets, plus the sign pill on its own panel (b_sany_y22).
   - The channel is 6 stepped panels.
   - Tones lifted about 15 % to y_47300.
7. **Centre bin.**
   - A crest rail carries the placard, with 55 mm joint caps and gap lines and a dark groove against the vault (c120).
   - The door eFn ramps from y 1.75 toward the crest.
8. **Outboard bin.**
   - The latch is about 2:1 with a handle (c120, y_47301).
   - The skin and seam follow the Catmull-Rom curve, so the seam no longer kinks.
   - Seams are soft light beads.
   - Placard UVs are inset 3 px, which removed the plate outline. Seat pictograms are side-view glyphs.
9. **Vault speaker.** Gently bowed, at t 0.70, in vault tone with a lighter smooth face.

### Open (all low)

- **Crest-rail groove.** It is still faint, even after the move to x 0.724.
- **Vault speaker.** It needs a crisp shadow edge on the side away from the cove (c120).
- **Row-placard pictograms.** c120 seems to show a boxed seat-letter panel and a standing person, not seat glyphs. A clear placard photo would settle it.
- **Seams and shingle joints at QA distance.** Rater A finds them now a little too soft against y_47301, after w8 softened them on close-up evidence. The two pull in opposite directions; a 2–3 mm darker core is the suggested compromise.
- **Vault fore-aft streaks.**
  - They also show in the studio render (`d_up`), so not only the AO volume causes them.
  - Rater B's suggestion: analytic arc normals, with the falloff as a function of t instead of |x|.
- **Doors 1, 2, 4 and 5.** Their cross-aisle ceilings are unverified, and the q01 camera still cannot show them (integration owns `test/qa.js`; the camera is in `from_ceiling.md`).
- **Lighting.** w9a found that the crevice term darkened the strip under the outboard bins. The note is in `from_ceiling.md`, and the lighting work in r10 has mostly fixed it.

### Sources added in wave 3 (`ref/web/ceiling/`, gitignored)

- **liveandletsfly ANA 777-300ER THE Room review:** images 3–6, 11–13, 20, 26, 27, 119, 120, 124, 133, 134.
- **SANspotter economy:** y10–y52.
- **OMAAT THE Room:** 23, 31, 37.

## Wave 3c (2026-10-24): confirm and polish, w11–w13

- **Result:** A 8.5 / B 8.7 (mean 8.6) in w13. Both raters are at or above 8.5 and no high issue is open, so **the ceiling meets the bar.** The round cap is also reached.
- The one medium is the door-2 dark slab, which belongs to `10_mono.js`. Both raters left it out of the overall score.
- **Rating files:** `ceiling_w{11,12,13}{a,b}.json`. Each rater was calibrated against its two previous files and the other rater's latest.
- **Cameras:** `review/qa/ceiling_views.js` (new and committed).
  - v1–v13 cover the aisle ceilings, bins and PSUs.
  - v14/v15 are head-on placards.
  - d1/d1b, d2/d2b, d4/d4b and d5/d5b are the door cross-aisle ceilings, which were first rated in w11.
- **Renders:** each round rebuilt on the pulled head: w11 ee521f1, w12 9a81648, w13 7301cfe.

| Round | Rater A | Rater B | Mean | Note |
|---|---|---|---|---|
| w11 (fresh, current head) | 8.2 | 8.5 | 8.35 | Door 1/2/4/5 rated for the first time: A 6.5–7.0, B 7.1–7.4. The aisle ceiling was the same as w10. |
| w12 | 8.4 | 8.6 | 8.5 | |
| w13 | 8.5 | 8.7 | 8.6 | |

- **Regression guard:** the w11 drop of 0.2 from w10's 8.55 is under the 0.3 guard, and it came only from the newly rated door zones. No round regressed an issue.
- **Triangles:** measured as instanced totals (`upper` plus every bin mesh × instances), the same way at both heads.
  - w10: 487.6k. w13 + budget fix: 501.8k.
  - Against the 414k wave-3 start that is +21 %, inside the +25 % budget.
  - A full extruded seam core briefly took the count to 522.9k (+26 %). It became a face-only ribbon after w13, with the same look (pixel diff ≤ 35 L on ~350 px of v5).
- **Before/after sheet:** `ceiling_before_after_w13.jpg`, w11 against w13, own renders only.

### What changed (wave 3c), by evidence

1. **Door 1/2/4/5 domes** (w11 medium from both raters: "blank white placeholder", a flat 229–230 field).
   - Two transverse panel joints, each a rib with a shadow lip.
   - Light strips in recessed housings at e 0.55, and downlights with trim rings (c133).
   - On the crown: a speaker, an emergency light and a smoke detector.
   - Emission ramps instead of stepping, capped at 0.2 at the door wall.
   - A baked falloff from x0.90 to x0.64 that covers the fittings.
   - Door scores went from A 6.5–7.0 / B 7.1–7.4 to A 7.8 / B 8.0–8.2.
2. **Outboard zone-end closures at every door.** Before, only door 3 had them, and the dome stands about 0.1 m above the bin top.
3. **Crest-rail channel** (open since w9). Two red/green tests found why it never showed:
   - The groove boxes in `08_bins.js` sat under the vault edge, behind the rail.
   - Strips on the true arc sank behind the 48-segment sweep, which runs inside the arc near the rail.
   - It is now a quad on the sweep's last chord, 3 mm proud, tight against the rail, #86898e, with a light top line. Raters measured vault 164 → channel 119–129 → rail 247, as in c120.
4. **Row placards.** They now read row number, framed seat glyph, person, after the c120 '17' crop. Before, three seat strokes read as "⅄⅄⅄". Scores: A 7.4 → 8.6, B 8.0 → 8.8.
5. **Vault speaker.** A dark recess crescent along one long edge (c120): 129 on a 176 vault. Fittings scores: A 7.7 → 8.4, B 7.9 → 8.6.
6. **Bin seams.** A 2.5 mm darker core inside the light bead (y_47301). It shows in close views; at QA framing the bin exposure still washes it out (lighting).
7. **Build break fixed.**
   - 3ea3f24 (monuments) declared `function gPlate`, which clashed with `const gPlate` in `08_bins.js`.
   - The page never loaded until the bins copy was renamed `binPlate` (34b066a).

### Open (all low)

- **Dome crown tone.**
  - The bake runs from x0.90 to x0.64, but the crown renders 214–215 against 178 on the aisle vault. The ratio on screen is about 1.15, where 1.4 is intended.
  - The vault material is on the cove-LED layer (`l: 12`). The tonemap shoulder or the LED term probably lifts the dome regardless of base colour, so this went to lighting in `from_ceiling.md`.
  - If lighting can't fix it, lower the dome base colour to about 0.88x the vault.
- **Door-3 hairline.**
  - A 2 px line at 239 runs on the near edge of the dark soffit beside the vault.
  - It is not caused by the centre board: removing its 4 cm overlap changed nothing.
  - Suspects: the closure rim faces and the 3.1 m flat soffit edge. A red test is next.
- **Door-4 wedge.** A flat 248 wedge sits at the dome/monument-ceiling junction. Suggested: a closure between the DOME and MONOC profiles.
- **Crest channel seen head-on** (v15). Rater A finds it slightly heavy and slate blue. It is right at aisle angles.
- **Doors 1, 2, 4 and 5:** still no photo (questions 11 and 12). Door 2's dark soffit is 10_mono's and is handed off.
- **Lighting:** vault fore-aft terraces, and bins near-white at QA framing.

## Post-wave polish B (2026-10-25): from_integration items

- Done: sky hairline at the outboard lens / lining junction (lens 9 x 0.8 cm lapping behind the lining + backing strip; zero sky
  pixels day and night); lens size in the amber moods; aisle vault now brighter than the bins in the white moods (vault eFn
  0.11 / 0.06-0.13, q06 194 -> 229-232, c_27312 236; `doorC` eFn 0.07-0.12; outboard door #d6d8dc), with the ribs, speaker and
  emergency light on the vault's own emission so they follow it in every mood; crest channel #a9acb1 over 0.45 of the chord;
  trough bars e 0.19 (no longer white at night).
- Not a defect: the door-3 "bin-lip z-fight" is the J centre-channel PSU housings seen edge-on (three colour tests).
- Ratings: w14 A 8.2 / B 8.6 (fittings left behind, fixed), **w15 A 8.5 / B 8.8, no high / medium: the ceiling stays at the bar.**
- Handed to lighting: the night `vaultE` cap 0.09 now binds (night vault L29 -> ~63; from_ceiling.md).
- Details and the open lows: `fixed_polishB.md`. Triangles +936 (~+21.4 %).

## Polish E (2026-10-26): door-3 "bin lip" dashes (integration L7-L11)

- Not done, with evidence. Hiding meshes by name shows the dashes are `psuo2`, the THE Room centre-channel units of rows 15 / 16.
  The near centre-bin door's curved lower edge cuts them in z04 (the foreground bin is the centre bin, not the outboard bin).
  Drop 2 mm and recess 5 mm were both built and rendered with no visible change, and the run-end fix doesn't apply.
  Crops: `polishE/`; details: `fixed_polishE.md`.
- No ceiling change, so no w16 round: the ceiling stays at w15 A 8.5 / B 8.8.

## Final confirm (2026-10-26, head 1430d42)

- **Confirmed at the bar:** rater A scored 8.5 and rater B 8.7, with no high or medium issues (`ceiling_final_a.json`, `ceiling_final_b.json`). The w15 scores were A 8.5 / B 8.8.
- **Nothing regressed.** Both raters checked every earlier high and medium issue against the new lighting (W14A-1, W14A-2, F1), and all are still fixed. `07b_ceiling.js` and `08_bins.js` are unchanged since polish B, so no code changed.
- **Triangles:** 502,734 (bins 432,850 plus shell `upper` 69,884). This matches polish B, about +21.4 % over the wave-3 start.
- **Open lows, carried over:**
  - The outboard PSU band needs finer segmentation.
  - The vault/bin brightness ratio is 1.05–1.17; the photos give about 1.2–1.45. The suggested change is `BINMAT.door` #cfd2d6.
  - The speaker has no bezel outline.
  - The door-4 wedge.
  - The cove-side vault strip washes out to about 253. That is lighting, and y_47301 is 241–255 there too, so it is acceptable.
- Not re-rendered this round: d1b/d2b/d4b/d5b, v4, v8, v9, v14 and the night/amber views.

## Final confirm 2 (2026-10-27, head 8467f01)

- **Confirmed at the bar:** rater A 8.5, rater B 8.7, with no high or medium issues (`ceiling_confirm2_a.json`, `ceiling_confirm2_b.json`). The wave-1 final scores were A 8.5 / B 8.7.
- **The lighting final touch left the ceiling alone.** `07b_ceiling.js` and `08_bins.js` have not changed since 1430d42, and renders from both heads were diffed:
  - The ceiling views (v1, v2, v5, d5) are pixel-identical above the seat tops.
  - In the QA views, the changed pixels in the top band are the seats, the window reveals and the sidewall window tub. In q17 the top-band mean rose about 2.5, all from the window tub.
- **No code change and no lighting hand-off.** The earlier high and medium items (W14A-1 / F1 and W14A-2) are still fixed.
- **Open lows, carried over:**
  - The vault/bin ratio is 1.05–1.19; the photos give 1.17–1.45.
  - The outboard PSU joint rhythm is faint.
  - The speaker bezel outline does not read.
  - The crest channel has no dark core.
  - The door-4 wedge was not checked, because d4b was not rendered.
  - The far-side cove is a flat 253 wedge. That is lighting, noted and not scored.

## Integration lows (confirm 3, 2026-10-27)

- **Item:** L16 integration low, grey PSU fragments on the door-3 bin lip (z04, `setView([2.3, 1.62, 32.7], PI/2 - 0.45, 0.25)`, and q11_bar3).
- **Cause, z04:** the THE Room centre PSU units (`psuo2`, rows 15 / 16). Hiding `psuo*` removes the dashes. A material-tag
  render (housingC red, bandC green, doorC blue, lipGap magenta) shows every housing whole and the channel intact. Where a
  unit looks cut, the near (right) outboard bin door's lower edge crosses it along its silhouette at this grazing angle
  (confirmed with BINMAT.door tagged cyan). That is ordinary
  occlusion: no z-fighting and nothing poking through.
- **Cause, q11:** the dark dashes on the near outboard bin's aisle edge belong to `binL` itself (they survive tagging
  lip / lipLine / groove / seamCore / lipGap). They are the per-module door latches seen edge-on along the run.
- **Tested and reverted:** the 0.193 m F/J centre housings at x +-0.15 reach |x| 0.2465, 6.5 mm past the centre-door edge
  (0.24) and through the `lipGap` strip. Moving them to +-0.135 (8 mm clear) left the z04 crop visually unchanged, so it
  was not the cause and was not kept. The rater's "end the run 0.05 m short" fix does not apply: the units sit 0.65 m and
  2.5 m inside the zone.
- **Photo check:** c_27312 (official, J cabin from above) shows the outboard band fittings at a grazing angle as the same
  short grey dashes, so the look is consistent with the photos.
- **Result:** no code change, so no ceiling confirm-3 round (08_bins.js / 07b_ceiling.js unchanged; confirm2 A 8.5 / B 8.7
  stands). Triangles unchanged. Proposed to the integrator: retire the item as photo-consistent (questions_ceiling.md 14).
