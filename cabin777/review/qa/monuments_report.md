# Monuments area report (`src/10_mono.js`)

Scope: galleys, lavatory exteriors, the door-3 bar, closets, the flight-deck door, class bulkheads and J monument backs,
curtains, pockets, shared monitors, jump seats, and the Type A door-lining furniture.

The target of 8.5 was not reached. Scores rose from 5.8 / 6.3 to 7.2 / 7.7 over four rounds, the most the brief allows.
No high-severity issue is left.

## Scores (two independent raters per round)

| round | rater A (skeptic) | rater B (geometry first) | files |
|---|---|---|---|
| r2 (previous session) | 4.5 | — | `monuments_r2.json` |
| w1 | 5.8 | 6.3 | `monuments_w1a.json`, `monuments_w1b.json` |
| w2 | 5.8 | 6.8 | `monuments_w2a.json`, `monuments_w2b.json` |
| w3 | 6.3 | 7.3 | `monuments_w3a.json`, `monuments_w3b.json` |
| w4 | 7.2 | 7.7 | `monuments_w4a.json`, `monuments_w4b.json` |

Round-4 detail scores (A / B):

| detail | A | B |
|---|---|---|
| door-3 bar | 8.5 | 8.5 |
| welcome galley | 8 | 8.5 |
| door-2 aft monuments | 7.5 | 8 |
| F front, flight-deck door, door 1 | 7 | 7.5 |
| lav exteriors | 7.5 | 7.5 |
| F/J bulkhead, J face | 8 | 8 |
| J/PY bulkhead, PY face | 7.5 | 7.5 |
| door-4 group | 7.5 | 7.5 |
| rear (door 5) | 7 | 7.5 |
| galley inserts | 7 | 7.5 |
| curtains | 6.5 | 7 |
| jump seats and door linings | 7 | 7.5 |

After the round-4 rating, the last open medium issue was fixed and checked in renders: the untied PY-aft and rear curtains
were too narrow and too dark. That change has not been re-rated.

## What changed

- **Door-2 passage** (lalf_133/134, sp_09, OMAAT 32):
  - Across from the welcome galley is now a flat ash wall with aluminium-framed stowage flaps, red latches and two rails.
  - The 7K galley has ash lower doors.
  - A dark warm soffit with downlights and a vent grille runs across the cross-aisle.
- **Welcome galley:**
  - Bigger landscape monitor (0.86 × 0.49 m) with two open bays under it; the brewer stands inside the left bay.
  - Portrait monitors on charcoal (no longer navy) end panels.
  - Thick satin nosing, an ash head and cheeks, and an aluminium picture frame round the opening.
- **J backs of the door-2 forward monuments** (tpg_70/_71): cream laminate with centre wall boxes. All J wall boxes were
  raised to just under the bins.
- **F walls:** a sumi ink-cloud print baked into a 0.1 m vertex grid (tpg_147, omaatF_2). It replaces the stretched washi
  fibres, which read as marble. There is now one continuous front wall at z 7.40.
- **J/PY bulkhead**, rebuilt from The Alviator's 2026 in-service photos (alv_IMG_7207/7209):
  - The outboard panels are 1.8 m tall and open above to the bins.
  - Flat charcoal-framed monitors sit at 1.5 m.
  - Two grey fabric pouches sit at floor level, and the bassinet sticker is at 0.95 m.
- **Curtains:**
  - Deep-fold lofts with baked crease shading.
  - Tied bundles at 1.5 m for F front, F/J, the J lines and J/PY, in warm charcoal.
  - Wide untied drapes for the PY aft end (slate) and the rear of economy (light grey).
  - Every aisle is kept clear.
  - New curtain lines at the F front, both door-2 lines and the rear of economy.
- **THE Room lav doors:** plain ash, a white seam strip, a white grab handle and a lock slot, as in the only in-service
  photo (OMAAT 32). The bronze frame came from the press render and was removed.
- **Bar** (samchui_11 / ANA render): light grey-bronze posts, a bright steel counter nosing, a low guard rail, and clear
  bottles with blue labels.
- **Jump seats:**
  - Mid-grey on grey pedestals.
  - Now at 1L, 1R, 2L, 2R, 3L, 3R, 4R and 5L ×2, 5R. The closet and lav doors next to them were narrowed.
  - The door-5 pair follows the map.
- **Door linings:**
  - A full-width slide bustle with a ledge.
  - A girt bar with a red flag.
  - A horizontal lever inside a 0.5 m red arming arc with an arrowhead.
  - 5 mm door-gap seams.
  - These follow the shell worker's notes, then photo measurements.
- **Galleys:**
  - Smaller red turn-buttons.
  - Inset upper doors with labels and paddles.
  - Warm light-grey inserts, smoked oven windows with blue LEDs.
  - Door-1 depths follow the map, with caps up to the ceiling.
  - Stowage on the aft wall of the door-5 work aisle.
- **Triangles:** the monuments mesh went from 93.5k to 116.2k (+22.7k). Most of the increase is curtain folds, ink-wall
  grids, bays and door-lining details.

## Sources

- **Official:**
  - ANA seat map "new 212" (`ana_seatmap_73E.png`) and ANA official photos `ref/ana/py_37302`, `py_37303`, `y_47300`, `y_47302`.
  - ANA 2019 renders via Sam Chui: `samchui_10`, `samchui_11`.
- **In-service photos:**
  - Live and Let's Fly (`lalf_133/134`), One Mile at a Time (J `The-Room-32`, F `omaatF_2`), The Points Guy (`_70`, `_71`, `_147`, `_153`, `_154`).
  - thepointsanalyst (`tpa_IMG_0220/0260`), Frugal Flyer (`ffF_*`), SANspotter (`sp_09`), Thrifty Traveler maps.
  - The Alviator 2026 PY review (`alv_IMG_7182/7207/7209`).
  - All of these are in `ref/web/monuments*`, which is gitignored and never committed.
- **Labels:** each value in the code is labelled [V] (verified), [D] (derived) or [A] (approximated) in its comment.

## Open (decisions and photos needed; also in `questions_monuments.md`)

1. **Door-3 monument depth:** the model uses 1.05 m; the map suggests about 1.5–1.9 m. Following the map moves rows 17–27 aft.
2. **Door 4L attendant seat:** no free wall beside the wheelchair lav door; no photo.
3. **Door-2 passage orientation:** L2 or R2 for the LALF photos.
4. **In-service photos:** none found of the door-3 bar or the new rear galley.
5. **Low-severity items left:**
   - F ebony closet faces lack streaked grain; this needs a `LAYER_PARAMS` wood variant in shared `03_tex.js`.
   - The arming arc has no "OPEN" lettering.
6. **For integration** (`from_monuments.md`):
   - Move the q01, q11, q13 and q19 cameras.
   - Fold `monoLayoutQA` into `05_layout.js`.

Contact sheet: `monuments_before_after.jpg` (round-1 renders against round-4 renders, own renders only).

## Wave 3 (2026-10-24): rounds w5-w8

The wave stopped on the brief's rule: two rounds in a row gained less than 0.2 (w7 -0.1, w8 +0.1). The target of 8.5 was not
reached. No high-severity issue is left. The only high issue of the wave, the lining mirrored fore-aft (w7b), was fixed in w7
and confirmed fixed in w8.

| round | rater A | rater B | mean | files |
|---|---|---|---|---|
| w4 (wave 1 end) | 7.2 | 7.7 | 7.45 | `monuments_w4a/b.json` |
| w5 | 7.3 | 7.9 | 7.6 | `monuments_w5a/b.json` |
| w6 | 7.6 | 8.0 | 7.8 | `monuments_w6a/b.json` |
| w7 | 7.6 | 7.8 | 7.7 | `monuments_w7a/b.json` |
| w8 | 7.7 | 7.9 | 7.8 | `monuments_w8a/b.json` |

w8 detail scores (A / B): bar 7.5 / 7.5 (capped: no in-service photo), welcome galley 7.5 / 7.5, door-2 aft 8 / 8,
F front + door 1 7.5 / 7.5, lavs 7.5 / 7.5, F/J 8 / 8, J/PY 8 / 8, door 4 7.5 / 8, door 5 7.5 / 7.5, inserts 7.5 / 8,
curtains 7.5 / 7.5, jump seats + door linings 7.5 / 8 (B 6.5 in w7).

**Triangles:** the monuments mesh went from 116.2k to 130.1k (+12 %, inside the +25 % budget).

**Review cameras:** `review/qa/monuments_views.js` renders m01-m19, alongside the q01, q11, q13 and q19 views in `test/qa.js`.

### What changed
- **Type A door linings:**
  - Rebuilt to the corrected from_shell spec (w5): a cream handle housing with a pocket and a brushed-silver grip, and an r 0.29
    painted arc with a stop bar, an arrowhead and an OPEN label.
  - An arming window, a 1.0 m bustle with a sloped top and a gauge window, an assist bar with a crimson strap wrapped round it,
    jamb grips and an upper seam.
  - **Mirrored fore-aft in w7** after lalf_133/134 (door 2L). The photos look toward L2: the welcome galley is forward, next to
    the door-2 lavs (omaat_room_32), and the 2L jump seat is on the aft closet. They show the viewing window forward, the arming
    window upper aft and the arrowhead forward.
  - A crimson-magenta arc (w6) and a cream EXIT plate (w8).
  - **Open hand-off:** 07_shell.js must move its viewing window to `c - 0.28` (from_monuments.md, w7). Until then the
    housing covers the window.
- **Welcome galley:**
  - Warm charcoal body instead of black (omaat_room_32, kna_31_full).
  - The glass cabinet has a lit interior, shelves, a smoked lit pane with shelf shadows, a round latch boss and a single cream
    tag.
  - The brewer is silver.
- **Curtains:**
  - The F front has one loose untied drape per aisle, bunched at the centre-wall edge, in neutral grey (omaatF_40, ml_DSC_1914).
  - The rear and PY-aft curtains are wide, irregular-hem 13-fold drapes; the rear one is lighter.
- **Galleys:**
  - Lighter inserts (omaat_room_32 ovens #928e79).
  - The 2R jump seat sits on a flush full-height panel, with the deck, nosing and inserts split round it.
  - Varied labels, and drawers under the door-5 aft counter.
- **Other:**
  - The F walls and flight-deck corridor use striped ebony (LAYER.fWood).
  - The bar blind is grey.
  - The J placards sit just above the wall boxes.

### Sources (wave 3, all in gitignored `ref/web/monuments/`)
- Live and Let's Fly: lalf_133 and lalf_134 (door 2L and the welcome galley).
- One Mile at a Time: THE Room 32 and 37, and the First set (omaatF_40, 33).
- KN Aviation (kna_31_full), MileLion (ml_DSC_1914), Sam Chui (samchui_11, ANA's 2019 bar render) and TPG.

### Still open
- **Questions for the user** (`questions_monuments.md` 7-8): an in-service photo of the door-3 bar or the door-5 galley, and
  an R-side door lining photo.
- **Rated, not fixed (w8):**
  - The bar blind still reads black in the AO pocket (lighting).
  - The welcome tag has no pictogram.
  - The 2R deck stub reads like a cushion.
  - The faint seam in the m04 ash flap.
  - The ebony streaks are a little regular.
- **Not yet rated:** the w8 fixes (lit cabinet pane, F drape at the wall edge, EXIT plate).

## Wave 3b (2026-10-24): plateau breaker, rounds w9-w12

The wave stopped at the plateau breaker's 4-round cap. The target of 8.5 was not reached; the result is 8.1 / 8.3 (mean
8.2, from 7.75 at the w9 baseline). No high- or medium-severity issue is left on rater B's side. Rater A has one medium
issue (welcome-cabinet size and position). Gap analysis: `monuments_gap_w9.md`.

| round | rater A | rater B | mean | files |
|---|---|---|---|---|
| w9 (baseline on 51e3979) | 7.7 | 7.8 | 7.75 | `monuments_w9a/b.json` |
| w10 | 8.0 | 8.0 | 8.0 | `monuments_w10a/b.json` |
| w11 | 8.0 | 8.1 | 8.05 | `monuments_w11a/b.json` |
| w12 | 8.1 | 8.3 | 8.2 | `monuments_w12a/b.json` |

**w12 detail scores (A / B):**

| Detail | A | B |
|---|---|---|
| Bar | 7.7 | 7.9 |
| Welcome galley | 7.9 | 8.3 |
| Door-2 ash wall | 8.1 | 8.1 |
| F front + flight-deck door | 8.3 | 8.3 |
| Lavs | 7.5 | 7.6 |
| F/J | 8.0 | 8.0 |
| J/PY | 8.0 | 8.0 |
| Door 4 | 8.3 | 8.4 |
| Door 5 | 7.9 | 8.1 |
| Inserts | 8.2 | 8.3 |
| Curtains | 8.2 | 8.0 |
| Jump seats + linings | 8.2 | 8.2 |

**Triangles:** 130.1k -> 145.0k (+11 % this wave). That is +24.8 % on the wave-3 start of 116.2k, against a 25 % budget,
so there is no geometry headroom left.

### What changed (big-ticket items from the gap analysis)
- **Galley inserts, rebuilt after the only real photos of an ANA 777-300ER galley face** (SANspotter snack bar, sans_38 /
  sansY_44). These replace the generic brushed-mirror units:
  - Satin anodised aluminium.
  - Grey upper compartments.
  - Dark 4 mm gaps round every insert.
  - Ovens with yellow-green meal-label windows, a display and a lever latch.
  - Chunky copper-orange turn-button latches.
  - Paired narrow brewers with squat polished pots (the polish baked per lathe wedge), a basket drawer and a caution
    label.
- **Photo wear tile:** new layer 28 `g_alu`, a smudge and wipe mottle cut from the sansY_44 oven and sans_38 cart faces
  by `make_swatches.py g_alu()`. It is on every galley metal face.
- **Door-2 welcome galley:**
  - The recess is lined in light grey, with ash only as an outer skin.
  - The glass cabinet reads as smoked glass. The engine has no blended glass, so there is no pane quad: the interior is
    tinted about 0.75x mauve, with a bright pane bead and a deep top rail carrying the caution plate.
  - The monitor is flush.
  - The real brewer.
  - The tag has a pictogram.
- **Monument backs:** a J/PY panel band with joints and a satin bead (omaat_room_36). Satin edge guards on the lav and
  closet aisle corners.
- **Flight-deck door** (tpa_Image-2-3): brushed bolt frames, a hinge jamb, a kick panel, a chevron strip and a lock boss.
- **Smaller fixes:**
  - F cloud wall: horizontal strata at the photo's contrast. The hue stays warm-neutral, as sampled.
  - Darker jump seats.
  - Mid-grey lining grip pocket.
  - No 2R deck stub.
  - Bar bottles with necks and caps, rocks glasses and a near-black counter.
  - Brushed ash-wall flap frames.
- **After w12, unrated:** the bar bottles and tumblers are back to a dielectric mid grey (w12 A/B: at metalness 0.5 they
  rendered black). This changes materials only.

### Rated, not done
- **Galley frames:** aluminium perimeter frames with rivets on every insert, cart grips, and posts between carts (w12a
  gapWorth03 about +0.3; w12b about +0.15-0.2). Not done because the triangle budget is spent. It would need a texture
  route: a frame and rivet decal in the atlas, or a trim elsewhere.
- **Welcome-cabinet geometry** (w12a medium): in the photos the cabinet is about 0.62 m wide, abuts the monitor, and its
  top is level with the monitor's.
- **Small items:** brewer-pot facets, ash-wall flap spacing, the PY bassinet bar, and the jump-seat straps.
- **Arming arc:** rater A reads lalf_134 as crimson (146,47,60). The lalf_133 close-up reads pink-magenta, so the colour
  is kept at #b53a62. The two photos are under different light.

### Hand-offs and questions
- **Lighting** (`from_monuments.md`, wave 3b): recessed monument faces are crushed (bar blind, welcome recess), and the
  galley upper banks show a fog band.
- **Questions** 9-10 in `questions_monuments.md`: the cabinet glass tint, and a door-5 galley photo.
- **Sources** (gitignored `ref/web/monuments/`, listed in its INDEX.md):
  - SANspotter: sans_38, sansY_44, sans_09.
  - Live and Let's Fly: lalf_133 / 134.
  - One Mile at a Time: omaat_room_32 / 36, omaatF_2.
  - The Points Analyst / travelnerdco: tpa_Image-2-3.
  - KN Aviation: kn_31.

Contact sheet: `monuments_before_after_w3b.jpg` (w9 against w12, own renders only; it also includes the lighting
session's concurrent changes).

## Wave 3c (2026-10-24): confirm and polish, rounds w13-w15

The wave stopped at its 3-round cap at **A 8.4 / B 8.4** (mean 8.4, from 8.1 at the w13 baseline). The 8.5 target was
not quite reached. No high or medium issue is left; neither rater lists a change worth +0.3 (`gapWorth03` empty).

| round | rater A | rater B | mean | files |
|---|---|---|---|---|
| w13 (head 25ae23e: the w12 final plus the grey bar glassware) | 8.1 | 8.1 | 8.1 | `monuments_w13a/b.json` |
| w14 (74e228b + 2c1eb9d) | 8.3 | 8.3 | 8.3 | `monuments_w14a/b.json` |
| w15 (3368ba0) | 8.4 | 8.4 | 8.4 | `monuments_w15a/b.json` |

**w15 detail scores (A / B):**

| Detail | A | B |
|---|---|---|
| Bar | 8.2 | 8.4 |
| Welcome galley | 8.5 | 8.4 |
| Door-2 ash wall | 8.2 | 8.2 |
| F front + flight-deck door | 8.3 | 8.3 |
| Lavs | 7.8 | 8.0 |
| F/J | 8.4 | 8.3 |
| J/PY | 8.2 | 8.2 |
| Door 4 | 8.5 | 8.5 |
| Door 5 | 8.2 | 8.3 |
| Inserts | 8.4 | 8.4 |
| Curtains | 8.4 | 8.4 |
| Jump seats + linings | 8.3 | 8.3 |

**Triangles:** 145.0k -> 122.2k. Parts under 10 cm with bevels of 12 mm or less (latches, paddles, handles, tabs) are
now plain boxes (`gRBoxM`): a 1-segment `gRBox` costs 108 triangles against 12, and the bevel is sub-pixel from the
aisle. That freed 31k triangles, which paid for the galley frames.

### What changed
- **Galley realism** (the w12 gap item, sansY_44): every insert and compartment sits in a riveted aluminium perimeter
  frame (`aluFrame`, from `insertGap`). Riveted channel posts stand between the carts, with recessed grip slots and
  white M-number tags.
- **Brewer pots:** one 12-segment lathe with the polish baked per vertex (cos-azimuth), so there are no facet stripes
  (same triangle count). The cheeks are brighter steel.
- **Welcome cabinet** (w12a medium):
  - 0.62 m wide, abutting the monitor; the housing head reaches the monitor top and carries the cream tag.
  - The smoked interior is neutral, not plum (omaat_room_32).
  - A silver thumb-latch on a lens-shaped bulge.
- **Door-2 ash wall:** one flap per ~0.8 m ash panel, with a seam between the panels. Warm brushed-silver frames with
  rounded corners, and two red tabs on a silver plate (lalf_133).
- **Flight-deck door:** the kick panel is ~12 % of the door, with a wider hinge jamb and a larger lock housing.
- **Curtains:** the J (`curtainC`) and F/J (`curtainF`) curtains are cool navy-charcoal (c_27312, omaat_room_36).
  They were warm brown.
- **Bar:**
  - The bottles have a glass highlight.
  - The tumblers are smaller and open, with rims.
  - A flat edge band replaces the tube fence (samchui_render_11).
  - The arming arc is crimson `#c42a48`, between lalf_133 and lalf_134.
- **J lav doors** use the finer `ashDoor` layer.

### Rated, not done (all low)
- **Welcome latch:** reads as a vertical rectangle; the photos show a horizontal oval.
- **Welcome glass:** no reflection streak.
- **Welcome head:** 6-8 cm short of the photo's head height (A).
- **Ash-wall frames:** still flat strokes with no highlight; the red tabs are too bright (lalf_133 #66201a) and should
  straddle the top rail.
- **Fine ash elsewhere:** the bar doors and the door-2 ash wall are still on the coarser `ashGrain` layer.
- **Bar:** the tumbler bodies are opaque, with only a half rim visible, and the counter has no bright nosing band.
- **Galley frames:** low contrast against the faces (partly the lighting fog); the pull handles are flat slots.
- **Door-1 dark wood:** streak aliasing (handed to lighting). The raters read its hue as mauve against omaatF_2, but
  tpa_IMG_0260 [V] supports it, so the colour is kept.
- **Carry-overs:** the jump-seat straps (rods), the PY bassinet bar, and the matte brewer pots.

### Hand-offs
`from_monuments.md` (wave 3c) covers the upper-bank fog over the new frames, the q19 blow-out and the dark-wood
aliasing. There are no new questions.

Contact sheet: `monuments_before_after_w3c.jpg` (own renders, w13 against w15, same cameras).

## Wave 3d (2026-10-24): confirm and polish, rounds w16-w18

**Monuments meet the bar: w18 is A 8.5 / B 8.6 (mean 8.55), with no high or medium issue.** That is up from 8.4 / 8.4.
The wave stops here.

| round | rater A | rater B | mean | files |
|---|---|---|---|---|
| w16 (head 2e3ebfa: the w15 monuments, other areas newer) | 8.4 | 8.4 | 8.4 | `monuments_w16a/b.json` |
| w17 (3ea3f24 + e6d3072 + fed7fdc) | 8.4 | 8.5 | 8.45 | `monuments_w17a/b.json` |
| w18 (05d4cc2) | 8.5 | 8.6 | 8.55 | `monuments_w18a/b.json` |

**w18 detail scores (A / B):**

| Detail | A | B |
|---|---|---|
| Bar | 8.6 | 8.7 |
| Welcome galley | 8.6 | 8.5 |
| Door-2 ash wall | 8.6 | 8.7 |
| F front + flight-deck door | 8.3 | 8.3 |
| Lavs | 7.8 | 8.0 |
| F/J | 8.4 | 8.3 |
| J/PY | 8.4 | 8.4 |
| Door 4 | 8.6 | 8.6 |
| Door 5 | 8.3 | 8.4 |
| Inserts | 8.6 | 8.6 |
| Curtains | 8.4 | 8.4 |
| Jump seats + linings | 8.5 | 8.5 |

**Triangles:** 122.2k -> 122.1k. The cap was 145k.

### What changed
- **Rounded plates (`gPlate`):** `gRBox` clamps its radius to half the depth. Thin plates therefore never got the in-plane
  corner radius they asked for, which is why the ash-wall frames, the latch ovals and the cream tag read square. `gPlate`
  extrudes a rounded rectangle instead. The bins worker had a `gPlate` of their own and renamed it `binPlate`.
- **Door-2 ash wall (lalf_133):**
  - The frames have a radius of 0.08, stand 25 mm proud and carry symmetric full-length lit edges.
  - The flap openings have rounded corners.
  - Two dark red clips (`#6e2318`) straddle the top rail.
- **Welcome cabinet (omaat_room_32):**
  - The head is about 7 cm higher, so the tag sits above the monitor line. The head stays under the recess ceiling.
  - The latch is a horizontal oval with a vertical thumb-turn, in a round D-shaped boss.
  - The glass-reflection strips tried in w17 read as wires or sticks (w17a, medium) and were removed (see question 11).
- **Monument ash:** the bar, welcome-galley and ash-wall ash has its own layer 33, `monoAsh`. It uses the `j_ash` tile at
  gain 1.1. `ashGrain` read banded, and `ashDoor` (SD 3.3) read as plain laminate; layer 33 gives SD ~5.3. This needed
  small entries in the shared `03_tex.js`.
- **Bar (samchui_render_11):**
  - The counter front has a bright satin nosing band that wraps both ends, in place of the dark slab over a rail.
  - The tumblers are dark grey glass (#3b3e42 against the render's #383539). Each has a full rim ring, an inward-facing
    inner wall, a bright base and side glints.
- **Galleys (sansY_44):** the insert frames are darker (#8a867f). The cart grips and compartment paddles are proud bright bars over dark recesses.
- **Jump seats:** flat 45 mm webbing with buckles and a lap belt, where there were rods before.
- **J/PY bulkhead:** the bassinet bar is now two flush sockets.
- **Brewer pots:** the polish band has a wider range and a tighter highlight.
- **Door-2 passage soffit (from_ceiling w11):** a polished steel fascia on both open edges.

### Rated, not done (all low)
- **Ash grain:** still about half the photo contrast (2.8 % against 5.8 %), with a faint repeat about every 77 px on the
  m04 wall. Raising `PHOTO_GAIN[33]` to about 1.5 would probably add about 0.1.
- **Welcome pane:** no glass cue. Opaque streaks read as objects, so this needs a transparent material (question 11).
- **Bar nosing:** B reads it as flat white plastic and suggests a dark groove plus some metalness.
- **Tumbler glints:** they sit inset from the cup edges, so they read as stripes.
- **Insert frames:** still only a little darker than the faces.
- **Ash-wall highlights:** the lit strips stop before the corner arcs.
- **J lav doors:** the plainest detail (A 7.8). A suggests an occupancy indicator plate and edge trim.
- **Door-1 dark wood:** streak aliasing. This is a lighting hand-off; the hue stays as tpa_IMG_0260 [V].

### Hand-offs
`from_monuments.md` (wave 3c) still stands. The galley upper-bank fog, the q19 blow-out and the dark-wood aliasing are all
unchanged in w16-w18.

Contact sheet: `monuments_before_after_w3d.jpg` (own renders, w16 against w18, same cameras).

## Post-wave polish (polish A, 2026-10-25): integration hand-offs - bar held

Closed `from_integration.md` "F front drapes cool light grey" (third request; log: `fixed_polishA.md`).

| round | rater A | rater B | change |
|---|---|---|---|
| w19 | 8.6 | 8.6 | `curtainFF` #6d6b6b -> #544c46 (m02 drape L100 h229 -> L76 h30; omaat_f40 L64 h20) |
| w20 | **8.6** | **8.7** | `curtainFF` #4f4c4a near-neutral (w19a: coffee, too saturated; w19b: lavender) |

- The drapes now read dark neutral charcoal (m02 #4b4b4a L75, s0.02), matching omaat_f40 white-balanced to its wall.
  The lavender asked for in w19b came from f_17313, which is an ANA rendering; per the brief, renderings lose to real
  photos (omaat_f40, omaatF_2).
- The w18 lows are unchanged. Triangles unchanged.

## Post-wave polish (polish C, 2026-10-26): ink-cloud print - bar held

Closed `from_integration.md` "To monuments" ink-cloud print (L8-L11 medium; log: `fixed_polishC.md`).

| round | rater A | rater B | change |
|---|---|---|---|
| w21 | **8.7** | **8.8** | ink clouds as an atlas panel (`inkPanel`, 'ink' rect) on a warm paper ground (`inkGround` #e9dbbf atlasLit, `inkCloud` #c0b5a0); wall grid 4 columns |
| w22 | 8.7 | 8.5 | thinner strata, crisper edges, 8 px pad, cooler colour - **reverted** (B: dark tone over 62-82 % of the wall) |

- Print box ink_aisle / ink_seated: L200 / 202, range 30 / 34, h42 s0.09 (omaat_f13 L202-208, range 23-25, h42 s0.11).
- Triangles: the ink walls drop from a 0.1 m grid to 4 columns. `06_atlas.js` carries a one-line `inkPanel(g, put)` call.
- **Still open (low):** strata larger and rounder than f40's dry-brush fragments (see the w22 notes in fixed_polishC.md),
  the wall's warmth against the neutral ceiling (lighting), front-wall monument joint hairlines, the w18 lows.


## Post-wave polish (polish F, 2026-10-26): door-3 bar to the in-service face

Closed `from_integration.md` "Lighting run 3, L13 ... To monuments (medium)" (log: `fixed_polishF.md`).

| round | rater A | rater B | change |
|---|---|---|---|
| w22b | **8.7** | **8.9** | door-3 bar upper unit rebuilt to the in-service face (omaat_j32); kept, no high or medium issue |

- **Location check first.** OMAAT's ANA THE Room review (NH109 JFK-HND, Jan 2020, seat 15A) places omaat_j32 in "a small
  snack bar between the middle and rear business class cabins", which is door 3. A real 2019 Traffic News press photo
  (trafficnews.jp/photo/87790, ph18, "bar counter with refrigeration") shows the same charcoal carcass with a black blind
  down over the left bay, and KN Aviation (knav_31) shows the monitor over open bays with water bottles and the glass door
  beside a lav. Real photos beat the 2019 render for geometry, so the bar follows them.
- **Change (`buildBar`):** warm-charcoal carcass `barFace` #3a3835; the welcome galley's photo-derived face is now a
  shared `serviceFace(B, V, xL, o)` (control panel over two ovens, monitor over two open bays with the brewer, tall
  glass-door cabinet with latch, caution plate and tag), called at xL -1.04; blind rolled up into a black head; green
  brewer LED; six water bottles in the right bay (knav_31); counter `barTop` #0e0e0f r 0.4; the bottle shelf, the narrow
  fridge and the tumblers are gone. The door-2 welcome galley calls the same helper with the same numbers and is
  pixel-identical (q01 / q19 / q13 changed px 0).
- **Measured (q11):** upper face p10/50/90 4/30/186 -> 11/54/180 (omaat_j32 10/53/165); counter p50 79 -> 53 (photo
  31-39); ovens L136-138 (photo 140).
- **Triangles:** monuments mesh 119.6k -> 119.2k.
- **Still open (low):** the glass cabinet reads as open shelving (no smoked pane; needs a transparent material, see
  question 11), thin cabinet stiles, the control panel is a bright flat plate (photo: dark recessed switch field), the
  nosing is a flat white band (photo: rounded satin rail, B suggests #b8babc m 0.7), the open bays render crushed (L3 vs
  L11-12, mostly lighting), the lower ash doors L172 vs the photos' L130-161 (exposure). The door-2 welcome galley now
  shares the face; see question 12.

## Final confirm (2026-10-26, head 1430d42): bar held, no code change

| round | rater A | rater B | high / medium (monuments) |
|---|---|---|---|
| final | **8.7** | **8.8** | none / none |

- Since the last rated round (w22b, 5e5e561), only `04_shaders.js` and `12_scene.js` changed: lighting runs 3-4,
  L13-L14. The monument geometry, materials and atlas are unchanged.
- Pixel diff of q01/q11/q13/q19 and m02/m03/m05/m06/m09/m12 against 5e5e561: 0-2.6 % of pixels change by more than
  8 L, all of them window-belt light.
- **Triangles:** monuments mesh 119,228, unchanged from w22b.
- **Lighting hand-off:** rater A found one medium lighting issue, and I confirmed it. The L14 PY/Y seat-level cool light
  tints the door-4/5 galley lower faces lavender, B-R about -3 -> +7/+8 below 1.3 m. It is not scored against monuments
  and is routed to `from_monuments.md` ("Final confirm") with a fix.
- **Still open (low, both raters):**
  - the glass cabinet reads as open shelving;
  - the control panel and oven fronts are flat plates;
  - the bar nosing is a flat white band, not a satin rail;
  - the right open bay is crushed (lighting);
  - the w18-w21 lows.
- Ratings: `monuments_final_a.json`, `monuments_final_b.json`.

## Final confirm 2 (2026-10-27, head 8467f01): bar held, no code change

| round | rater A | rater B | high / medium (monuments) |
|---|---|---|---|
| confirm2 | **8.7** | **8.8** | none / none |

- Since the final confirm (1430d42) only lighting changed: `04_shaders.js`, `12_scene.js` and 4 lines of `07_shell.js`
  (lighting final touch, 71fdda1..8467f01). `10_mono.js` and `05_layout.js` are unchanged and the monuments mesh is
  still 119,228 triangles.
- **Diff, 1430d42 vs 8467f01:**
  - q01, q11, m01, m03, m05 and m06: 0-0.09 % of pixels with |dL|>8 and 0-0.4 % with |d(B-R)|>8.
  - m02 changes 1.6 % in L. That is the sidewall window reveal, which belongs to the shell.
  - The bar elements re-measure identically.
- **Routed lighting item ("Final confirm", galley lavender below 1.3 m): fixed, both raters.** White-pixel B-R,
  lower / upper band:

  | view | 1430d42 | 8467f01 |
  |---|---|---|
  | q19 | +7.3 / -3.5 | -4.5 / -3.5 |
  | m12 | +7.8 / -6.1 | -4.8 / -6.2 |
  | m09 | +5.4 / -6.7 | -2.5 / -6.7 |

  - Luminance is unchanged in all three views.
  - m09's gap of 4 is just over the target of 3. It is the white panel against the darker grey door-4 inserts (the
    5e5e561 baseline gap was 5.1), not a lighting split.
  - The J/PY partition lower half in q13 also lost its lavender: +20 -> +4 (rater A).
- **Earlier mediums** (L13 bar face, ink-print inversion, warm drapes, door-1 belt hot band): still fixed.
- **New low (lighting, not scored, optional):** the door-4/5 cart faces read slightly cool, B-R about -8 against -1
  to -5 on the upper wall. They are cool-neutral, not lavender (rater A).
- **Still open (low, carried):**
  - the glass cabinet reads as open shelving;
  - the control panel and oven fronts are flat plates;
  - the bar nosing is a flat white band;
  - the bays are crushed to L3 (lighting);
  - the bar soffit;
  - the w18-w21 lows.
- Ratings: `monuments_confirm2_a.json`, `monuments_confirm2_b.json`.
