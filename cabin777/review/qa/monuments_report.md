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
