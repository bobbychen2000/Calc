# THE Room (room area) — photo-QA report

Owned file: `src/09c_room.js`. Shared-file edits, each named in its commit:
- `src/09_seats.js`: the J `SEATMAT` values, the room `seatEye` / `seatPickBox` / `seatBedCenter`, and the room seat plaques.
- `src/03_tex.js`: the layer-9 pillow check pattern and `LAYER_PARAMS` 9.
- `test/make_swatches.py`: the j_ash entry, which produced `tex/tex_j_ash.png` and `tex/sizes.json`.

## Scores

| round | rater A (skeptic) | rater B (geometry) | notes |
|---|---|---|---|
| r3 (start) | 5.5 | – | single rater, room_r3.json |
| w1 | – | – | skipped per brief; fixed room_r3's issues directly |
| w2 | 5.4 | 5.0 | new real in-flight photo set exposed new faults (O bench width, E ash slab, flap tone) |
| w3 | 6.4 | 6.3 | no high issues |
| w4 | 6.9 | 7.3 | no high issues; the only medium left in each rating was fixed after it (see below) |

The target of 8.5 was not reached. After 4 rounds, the gains per round were +1.0/+1.3 and then +0.5/+1.0. The w4 fixes (sofa roll, belt, header tone, softer duvet, charcoal footwell, card pocket) have not been re-rated.

## What changed (r3 → w4)
- **Tone:** shells, seat fabric and leather rendered at about 0.5x the photo luminance, so they were lifted. The headrest flap and header band are now the palest slate, as in the photos. The ash is lighter and near-neutral; its j_ash grain was re-cut straight and fine.
- **Geometry, rear-facing O seat:** it is now a 0.84 m bench with a narrow 0.24 aisle armrest carrying a ribbed, slotted ledge (tpg_31, tpg_42). It has a full-width back shell with a padded header band and a lamp in each corner. The back is shorter (0.545) with three soft grooves and a fabric fillet into the cushion.
- **Outer (window / centreline) console:** 0.085 deep, with a red life-vest tab and stowage. It also hides the 777 dado that intruded into the footwell (room_r3 high).
- **Monitor wall** (tpg_53 square-on, 1073 px/m):
  - 0.595 x 0.405 charcoal bezel.
  - Silver 0.49 sill with a drawer, green LED and navy literature pocket.
  - 0.43 cabinet.
  - Angled 0.15 m lamp wing with lamp and air nozzle.
  - Footwell mouths 0.475 wide, square under the monitors, with a 5 cm pillar.
  - Full-size safety card in a pocket beside the O footwell.
- **Side tables:** E's ash table covers only O's footwell (charcoal console aft of it). Both tables are an ash inlay in a charcoal rim with a silver lip.
- **Controls:** a grey plate with white-outline icon buttons (thumb wheel, filled blue lie-flat key, position pill). The gamepad handset has a large screen and D-pads, and sits on the monitor side for O.
- **Soft goods:**
  - White and blue check-jacquard pillows, flat and piped with a taupe reverse.
  - Visible teal belt and buckle.
  - Seat-front apron.
  - Bed mode: indigo quilted duvet that drapes over the mattress, with white and blue pillows.
- **Plaques:** dark glass with blue-lit numbers.
- **Triangles** (near LOD, one pair O+E + divider): 15,136 → 19,348 (+28 %). Far LOD pair: 544 → 568. Segment counts were trimmed on the small round parts.

## Remaining (from w4a / w4b, low)
- The control plate should sit on a slightly raised pod.
- The footwell pad nose is square (it should be rounded), and there is a grey step bar under it.
- The E footwell mouth is 0.435 and not centred under the E monitor.
  - The O footwell (−0.505..−0.03) and the 5 cm pillar leave no room to widen it toward the centre without moving the E monitor.
  - This is left as is: moving the monitor breaks the photo-measured sill/wing layout.
- q08, q09 and q10 in `test/qa.js` do not frame the same view as their paired photos. That is a harness issue for the integrator.

## Where raters were overruled
- **w2 A, "aisle-facing end of the side-table console should be ash (waterfall)":** not applied. c_27316 and tpg_53 show the seat-facing console face in charcoal with the controls on it. The ash seen in c_27312 is the aisle-end panel.
- **w2 B, footwell fixes:** applied; B's E-mouth values are constrained as described above.

## Sources
- ANA official photos `ref/ana/c_27300–27316`. 27300, 02, 03, 05, 07 and 08 are CG renderings; 27312–16 are real photos.
- About 150 in-flight photos downloaded by the raters to `ref/web/room/` (gitignored):
  - TPG (Zach Griff 2020): tpg_31, tpg_42, tpg_53, tpg_51, tpg_78
  - Thrifty Traveler: tt_*
  - flatbeds.com.au: fb_a96b7a65 (bed)
  - Frugal Flyer: ff_*17e-and-17f
  - God Save The Points: gstp_*-38 (controls)
  - r7aviation: r7_*
  - UpgradedPoints: up_*
- Every value in `09c_room.js` carries a [V] / [D] / [A] tag in its comment.

## Decisions (the user asked for judgement calls, not questions)
Recorded in `review/qa/questions_room.md`. Real photos win:
- the wrapped boarding duvet bundle is added
- the bed-mode duvet stays open
- the 0.84 m bench is kept
- the ledge stays darker brushed grey
- the plaques stay blue-lit

The handset was also finished after w4: a dark ring pad at one end, 4 coloured keys at the other, and a live screen image.

## Hand-offs
`review/qa/from_room.md`:
- **shell:** clip the dado in the J zone.
- **monuments:** FYI, the shared j_ash swatch was re-cut.

## Files
- Ratings: `review/qa/room_w2a.json`, `room_w2b.json`, `room_w3a.json`, `room_w3b.json`, `room_w4a.json`, `room_w4b.json`
- Contact sheet: `review/qa/room_before_after.jpg`

## Wave 3 (2026-10-24): w7-w11

| round | rater A (skeptic) | rater B (geometry) | main changes rated |
|---|---|---|---|
| w6 (start) | 7.0 | 7.6 | - |
| w7 | 7.4 | 7.6 | boarding bundle restored (e431338) |
| w8 | 7.7 | 7.9 | bed rebuilt, pillows, divider fins, monitor frame |
| w9 | 7.9 | 8.1 | quilted comforter, bed pillows, flange, bezel borders |
| w10 | 8.0 | 8.1 | pillow check, monument spine (B: high - over the 18D plaque) |
| w11 | 8.1 | 8.2 | spine stops at the cap, metal edges, O quilt |

Stopped by the brief's rule: two rounds in a row gained less than 0.2 (w10 +0.1/+0.0, w11 +0.1/+0.1). There was no
high-severity issue left in w11. Target 8.5 not reached. The w11 fixes (belt, plaques, cap tone, fabric/flap tone, spine
ends, O quilt phase) are committed but not rated.

**What changed**
- **Boarding bundle** (`roomBundle`), restored after e45db15 / 2bf64d9 removed it by mistake. A folded white pad with the
  blue duvet on top, in plastic, sits at the cushion front; the blue pillow rests on it, the white pillow stands behind
  toward the aisle, and a navy slipper pouch lies beside it (tpg_31, tpg_42, omaat_room_15).
- **Bed** (`roomBed`, `duvetSheet`).
  - The w6 mattress was one rectangle that ran through the side-table wall and into the neighbour's legroom. It now
    follows the seat, narrows beside the table and runs into the footwell wedge.
  - The duvet is a draped height-field cloth with soft folds, a box quilt on a ~0.33 m grid, a turned-down head and an
    aisle edge that rolls over the mattress (tpg_70/72/75).
  - The pillows are propped at 42/22 deg.
- **Pillows.** Plump, equal-size pillows; blue ~2.3 cm two-tone check with a grey flange that follows the outline.
- **Seat.** Piping round the back pad; the teal belt and buckle are visible again (they were buried in the tilted cushion).
- **Monument.**
  - The monitor frame runs up to the cabinet top, with borders 5.3 / 4.7 cm (tpg_53).
  - The top is split into O and E housings by a slim spine with a brushed-metal rail, with light metal top edges
    (c_27313/14).
  - The plaques sit at the cap ends; the cap is darker.
- **Centre divider.** Two slim charcoal fins with metal tops (c_27314), replacing the broad ash wall.
- **Triangles** (near pair O + E + divider): 19,264 → 22,980 (+19 %, budget +25 %). The bed variants are 15.4k (O) and
  12.9k (E), for the occupied seat only. The far LOD is unchanged.

**Shared-file edits** (each named in its commit)
- `09_seats.js`: SEATMAT `pillowBlue`, `mattress`, `jFabric`, `jHead`; the room plaque z and tile colour; `UNITS.roomBedE`.
- `03_tex.js`: `PHOTO_GAIN[19]` (ash grain, 2.0 → 3.4, also used by monuments' barAsh, noted in from_room.md) and
  `LAYER_PARAMS[9]` (pillow check, room only).

**Hand-offs** (from_room.md)
- Lighting: move the mood strip under the monitor from y 0.642 to y 0.580; the sill now spans 0.583-0.667.
- Monuments: FYI, the ash-grain gain changed.

**Still open** (w11a/b, medium unless marked)
- The spine meets the cap at 80 % of its length; in c_27313 it is at the centre. Fixing this means a deeper O housing
  (see questions_room.md).
- The O comforter's quilt is still weak in the high top view.
- Fabric and shells read cool. This is mostly lighting (rater notes for the integrator).
- Low:
  - the pillow and comforter jacquard are soft;
  - the ash grain still reads 0.6-0.8x the photos by B's measure (A: within range);
  - the pad renders near-white under the studio light.

**Sources added this wave:** TPG (Zach Griff 2020) b_tpg_1..93 and OMAAT a_omaat_room_10..31 / a_omaat_777j_* in
`ref/web/room/` (gitignored). Ratings: `room_w7a.json` … `room_w11b.json`. Before/after: `room_before_after.jpg`
(left: w7 renders, w8 for the beds; right: final).

## Wave 3b, plateau breaker (2026-10-24): w12-w15

| round | rater A (skeptic) | rater B (geometry) | rated head / main changes |
|---|---|---|---|
| w12 (start) | 8.1 | 8.2 | 4f006d2 (wave-3 final); gap analysis `room_gap_w12.json` |
| w13 | 8.2 | 8.3 | 4f992d5 / 6d288fe: real-photo ash tile, check jacquard, comforter material + shape, satin shells |
| w14 | 8.3 | 8.4 | e3e95f3 / 2b2f46b: O comforter to the table corner, ash door / cabinet split, banded jacquard, white slippers |
| w15 | 8.4 | 8.4 | 63f9336 / 89fd6bb: ash doors on their own layer, chrome buckle, bundle film, darker pillow |

Stopped at the 4-round cap of the plateau breaker; w13-w15 each gained +0.1, and the gap list holds nothing worth +0.3
(the remaining medium, door vs cabinet ash contrast in the cabin view, is partly lighting). Target 8.5 not reached;
no high-severity issue in any round. The post-w15 tweaks (ashDoor #ece7dc on PHOTO_GAIN[30] 0.5, ash grain 2.6 -> 2.2,
near-black webbing, glossier chrome, both raters' w15 asks) are verified in my renders but not rated.

**Gap analysis (w12)** ranked: (1) the ash tile came from the CG render c_27305 at 2.2 mm/px with no veneer banding;
(2) the comforter was plain glossy satin, lighter than the pillow; (3) O comforter shape (pie-crust hem, ripples, a
narrow tongue); (4) flap / fabric contrast 1.7-2.4 in the cabin vs 1.2-1.4; (5) belt colour and the spine T. It also found
that tpg_72, cited for the quilted comforter in earlier rounds, is a photo of the pyjamas.

**What changed**
- **Ash.** `tex_j_ash.png` re-cut from a real 1600 px close-up of the aisle-end panels (tpg_60, 0.32 m tile, ~0.9 mm/px,
  veneer bands kept). Aisle-end posts, door leaves and aisle panels use a pale, near-plain `ashDoor` on their own layer 30
  (same tile, low gain); cabinets, tables and inlays a darker greige `SEATMAT.ash` #b2a28b (c_27312 / 27314 / 27316).
- **Pillow + comforter jacquard.** New layer 29 `j_pillow`: a tone-on-tone check of ~1.4 cm squares set on the diagonal,
  fading in diagonal bands (kn_17 close-up; period 1.9 cm measured on tpg_46).
- **Comforter.** Matte #3f4799 (duvet / white pillow ~0.5, tpg_81), 3.5 cm edges, a long low hem wave, wider stitch dip
  (no aliasing ripples), wide over the whole wide part of the O bed up to the table corner, no folds in the footwell taper.
- **Seat.** Flap less glossy (r 0.55); dark grey-taupe pillow flange; pillow #3c4787 (kn_17 navy); near-black slate-teal
  belt to the seat crease with a chrome lift-lever buckle and the latch tongue on the cushion (kn_17, tpg_46).
- **Bundle.** Duvet at its real tone through the film with crease glints; white slippers in film (kn_17, tpg_76; question 17).
- **Shell / monument.** Satin charcoal shells and caps (r 0.34, lighting hand-off); flared spine T into the aisle cap
  (c_27313); plaque glow window inside its grey tile (was a navy box).
- **Triangles.** Near pair (O + E + divider) 22,980 -> ~23,100 (+0.5 %; wave-3 total +20 % of the +25 % budget). O bed
  variant 15.4k -> ~17.6k (occupied seat only). Far LOD unchanged.

**Shared-file edits** (each named in its commit): `03_tex.js` LAYER `jPillow` 29 / `ashDoor` 30, `N_LAYERS` 31,
`PHOTO_LAYERS` / `PHOTO_GAIN` / `LAYER_PARAMS` 29-30, `PHOTO_GAIN[19]`; `09_seats.js` SEATMAT ash / jHead / duvet /
pillowBlue / jShell / jCap and the room plaque quad; `make_swatches.py` j_ash (tpg_60) + j_pillow (synth); tiles
`tex_j_ash.png`, `tex_j_pillow.png`.

**Hand-offs** (`from_room.md`): monuments - the ash tile and gain changed (barAsh shares layer 19; layer 30 is available
for a plainer finish); integration - anisotropic filtering on the photo / detail arrays (q07 grazing-angle smear, q06
door aliasing; SwiftShader cannot show it, needs a real-GPU check); lighting - cool cast on shells and the over-saturated
pillow in the cabin views; aisle-facing faces possibly under-lit (door / cabinet luma 0.84-0.92 vs 0.6 in c_27312).

**Still open (w15a/b)**
- Medium: door vs cabinet ash contrast in the cabin views (partly lighting); B: grain blotchy at 2.6 (now 2.2, unrated).
- Low: pillows are rigid slabs (real ones pinch to thin corners); O comforter outline still crisp; the bundle film is
  mostly hidden under the pillow; the O bed's full-width part may be short (0.66 m vs ~0.9 m estimated from tpg_81) -
  needs a seat-plan dimension before the side table moves (question).

**Sources added this wave** (`ref/web/room/`, gitignored): TPG 2020 review re-downloaded (tpg_43..93, new numbering:
tpg_46 O pair with bundles, tpg_60 ash close-up, tpg_79 / 81-83 beds), KN Aviation 2021 (kn_*, kn_17 bundle close-up),
Live and Let's Fly (lalf_*), Turning Left for Less 2024 (tlfl_*), Sam Chui (sc_*). Ratings `room_w12a.json` ...
`room_w15b.json`, gap analysis `room_gap_w12.json`. Before / after: `room_before_after.jpg` (w12 start vs w15);
the wave-3 sheet is `room_before_after_w7-w11.jpg`.

## Wave 3c, confirm and polish (2026-10-24): w16 - target met

| round | rater A (skeptic) | rater B (geometry) | rated head / main changes |
|---|---|---|---|
| w16 | **8.5** | **8.5** | 06aea43: the post-w15 tweaks (ashDoor #ece7dc on layer 30 gain 0.5, ash grain 2.6 -> 2.2, near-black webbing, glossier chrome) |

**THE Room meets the bar:** both calibrated raters at 8.5, no high-severity issue (`room_w16a.json`, `room_w16b.json`;
rebuilt on the current head with the lighting loop's latest snapshot 918e366). What moved it: the door / cabinet split now
reads in the cabin (q06 door near-plain cream, hp 0.077 -> 0.042, cabinet / door 0.92 -> 0.81, c_27312 0.73) and the
lower grain gain removed the blotchy oak look (B's w15 medium). A withdrew the webbing complaint (c_27316 shows teal).

**Post-w16 (unrated):** bff7fba rebuilds the pillows as stuffed lenses (thickness ((1-u^2)(1-v^2))^0.42, pinched corners,
sides bowing in ~6 %, flat seam flange ring on the blue one), the low issue both raters carried since w14. Triangles
about equal to the old bevelled pillows. A endorsed the lens shape; B (who saw the code) would pinch the corners further.

**Still open (all low, w16a/b):**
- A medium: cabinet / table ash pinstripe at about half the photos' contrast (hp 0.040-0.046 vs 0.079-0.097), the
  1-4 cm veneer bands reading as wavy arcs, a little warm (R/B 1.24-1.27 vs 1.04-1.16 official). Suggested: re-cut
  `tex_j_ash` with HP 60 -> 20, ALONG 6 -> 14, then gain back toward 2.6 (shared with the doors and the bar). B instead
  rates the ash as fixed and matching (hp 0.048 vs 0.055); left as is.
- Low: blue pillow ~20 % large vs kn_8; bundle film hidden (only a 2-3 cm lip shows; move the pillows ~6 cm aft, wider
  glints); O comforter a crisp T (taper + edge wave); latch tongue floats ~3 cm from its stub; buckle has no highlight;
  aisle-end lower-panel seam missing; a dotted aliasing strip along the door-leaf top edge (q10).
- Lighting items handed to `from_room.md`.

**Sources added:** kn_8, kn_17, kn_20, kn_36, kn_41, omaat_room_13, omaat_room_15 re-downloaded to `ref/web/room/`
(gitignored).

## Post-wave polish (polish A, 2026-10-25): integration hand-offs - bar held

Closed the `from_integration.md` items addressed to room (log: `fixed_polishA.md`).

| round | rater A | rater B | rated head / changes |
|---|---|---|---|
| w17 | 8.5 | 8.5 | 7744d1c: shells / caps darker (jShell #434349, jCap #4b4b50, jShellIn #3e3e43); header band on the smooth satin layer |
| w18 | **8.5** | **8.5** | 0b28c7c: jShell #4a4b51 / jCap #4b4c51 (w17b: shaded near faces overshot dark); band colour back to #656b73 |

- **Shells:** q06 near faces L96 -> L79, caps L128 -> L105 (c_27312 L53-89 / L98); ash-to-shell 1.3-1.6 -> ~2. The
  integrator's "neutral" (s <= 0.08) was **not** taken: the official c_27312 / 27314 / 27315 shells are cool slate
  (h~220, s0.12-0.25), and official photos win for colour. Both raters agreed. The rim sheen lines survived (rim / face 1.26).
- **Header band:** the leather layer's dimples read as hammered metal at seat-eye range; on the plastic layer the band's
  local contrast is 0.034 (was 0.154, target <= 0.04).
- **Still open (low):** q09 shaded wall ~0.7-0.9x c_27314 (raters: mostly AO / lighting); band / flap 0.82 vs 0.89-1.05
  (optional jBand #6b717c); faint plastic stipple on the band; the w16 soft-goods lows; ash pinstripe contrast.
- Shared edits: SEATMAT jShell / jCap / jShellIn (`09_seats.js`). Triangles unchanged.

## Polish D (w19): integration L8-L11 hand-offs

w19 scored A 8.5 / B 8.5 with no high or medium issue (89168b6), so the change was kept.
- **Toe kick:** `KICK` (0.08 tall, 2 cm back, #1c1d20) under both aisle armrest housings and the ash monument ends,
  where the ash panel and frame now start at 0.08 (c_27312, omaat_room_4).
- **11A hairline:** it was the lit 45° chamfer of the low console block at the footwell mouth. The block now has square
  edges: 48 px > L200 -> 0.
- **Cap rails:** capRail is now a 9 mm round edge with 3 segments.
- **Tested and reverted:** shared jCap r 0.26. It added +16 L on a flat cap face in q09 and no measurable streak.
- **Open (low):** A suggests a 0.10 kick with a thin silver rail above it. B notes there is no bright lip where the ash
  meets the black base.
- Triangles: roomO / roomE 12.2k / 9.6k -> 13.4k / 11.0k per unit mesh. Ratings `room_w19a/b.json`. Log:
  `fixed_polishD.md`.

## Final confirm (2026-10-26): bar held on the final head

| round | rater A (skeptic) | rater B (geometry) | rated head |
|---|---|---|---|
| final | **8.5** | **8.5** | 1430d42 (lighting run 4 L14) |

- **Confirmed:** both raters score 8.5 with no high-severity issue (`room_final_a.json`, `room_final_b.json`). No code change.
- **What changed since w19 (89168b6):** nothing in room's files. `09c_room.js`, `03_tex.js`, `tex/` and the room `SEATMAT` keys are all untouched. Room regions match w19 within 1-3 L in all five views. The pixels that did change are in the window belt and sidewall (lighting runs 2-4, cooler belt, rim lobe now aft of THE Room only) and the door-3 bar in the q07 background (monuments).
- **Earlier high and medium issues:** none regressed. The header band, toe kick and 11A hairline fixes still hold.
- **Still open, low:** the ash pinstripe contrast, header band ~10 % dark, kick height and silver lip, and the rigid soft goods.
- **Lighting medium (A, not scored for room):** the q07 window-side shell post went from L103 to L75, against L114 in c_27316. Routed to `from_room.md` (final confirm).
- **Triangles:** unchanged since w19. roomO / roomE are 13.4k / 11.0k per unit mesh.
