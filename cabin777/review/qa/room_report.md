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
