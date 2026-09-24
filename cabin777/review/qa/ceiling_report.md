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
