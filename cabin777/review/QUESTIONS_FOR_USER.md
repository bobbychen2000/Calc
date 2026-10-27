# Open questions for you: ANA 777-300ER cabin

These are the questions from the nine `review/qa/questions_<area>.md` files that are still open on 2026-10-27 (final ship), with
duplicates merged. Nothing is blocked on them. **Any item you skip keeps its current default.** You agreed to that rule for the earlier
questions on 2026-09-24.

- **[call]** means a preference. A word answers it, for example "official", "photos" or "keep".
- **[photo]** means a photo or drawing would settle it. Skip it if you have none.
- **[check]** means a look on your own phone or GPU, which the headless renderer cannot judge.
- **Decided (reversible)** marks a question the integrator settled while you were away. It ships as stated and is one
  switch to undo.
- Ids such as `econ Q26` are item numbers in `questions_econ.md`. The shell file has unnumbered bullets, so they are cited
  as `shell W3.n` (under "Wave 3"), `shell W3c.n` (under "Wave 3c") and `shell PB.n` (under "Polish B").

## If you only have a minute

These change the most pixels: lighting Q17 (one white balance for the whole aircraft or one per cabin; decided per cabin),
lighting Q5 (sun patches), lighting Q15 / Q16 (window-wall brightness), econ Q9 (economy fabric mix), econ Q6 (blankets in
bags at boarding), room Q6 (THE Room seat colour), lighting Q3 / Q8 (night levels) and exterior Q8 (wing grime).

## THE Suite (first): 4 open

- **suite Q7 [call] Cap colour.** ANA's official f_17313 shows neutral wood caps on the suite walls, but every in-flight photo
  shows olive-khaki. *Now:* a hue between the two. *Why it matters:* the caps run along every suite top and set the colour of
  the F cabin seen from the aisle.
- **suite Q6 [call] Doorway width.** The model's suite opening is about 0.64 m, but perspective photos (f60, f7) suggest about
  0.50 m. Widening the door leaves to about 0.57 m would close the gap. *Now:* 0.64 m. *Why:* the entrance looks more open
  than in the photos.
- **suite Q5 [call] Door-leaf shimmer.** The fluted leaves (15 slats each, against about 22 in reality) still shimmer at
  grazing angles. A striped texture would remove the shimmer but lose the real relief. *Now:* real geometry. *Why:* the
  shimmer shows when you walk the F aisle, mostly on phones.
- **suite Q8 [call] Made-up bed.** Should the bed show f57's neat turned-down corner or f58's rumpled sheet? *Now:* f57.
  *Why:* it only shows in the lie-flat view.

## THE Room (business): 8 open

- **room Q6 [call] Seat colour.** ANA's official photos (c_27313 / 27315) show a violet-grey sofa with strong contrast.
  Daylight trip reports show a neutral grey. *Now:* a neutral mid charcoal-grey, as in the in-flight photos. *Why:* the seat is the largest fabric area in the 64-seat cabin. Say "official" to match ANA's look.
- **room Q9 [call] Bedding bundle on forward-facing seats.** Every boarding photo shows the bagged duvet, pad and pillows on
  a rear-facing seat. *Now:* every seat gets the bundle, because ANA sets bedding at every seat [A]. *Why:* this decides
  what 32 of the 64 seats look like at boarding. The alternative is pillows only.
- **room Q15 [call] Comforter in bed mode.** Folded back across the full width (lalf_3), or loose over the pad into the
  footwell (tpg_81)? *Now:* loose. *Why:* it only shows in the lie-flat view.
- **room Q12 [call] Where the monument spine meets the aisle cap.** In c_27313 it meets the cap at its centre. In the model
  it meets 80 % of the way along, because centring it would make the rear-facing housing deeper and shorten that seat's
  footwell. *Now:* left as is, with the seat-number plaques at the cap ends. *Why:* every seat pair's aisle end shows it.
- **room Q20 [call] Belt colour.** The official c_27316 shows a teal belt. The 2021 kn_17 photo shows near-black slate.
  *Now:* near-black. *Why:* it is small and mostly covered by the bedding at boarding.
- **room Q18 [photo] Rear-facing bed length.** Both raters measure the full-width part of the bed at about 0.9 m in tpg_81,
  but the model has 0.66 m (from the head to the side-table corner). A Safran or ANA seat-plan dimension would settle it.
  *Now:* 0.66 m. *Why:* it sets the proportions of the rear-facing bed.
- **room Q7 [photo] Raised privacy panel.** "Close door" also raises the pop-up panel about 0.40 m out of the armrest
  ledge. That height and its finish are estimates, because no photo with the panel raised was found. *Why:* it only shows
  with the doors closed.
- **room Q19 [check] Real GPU.** On a real phone or GPU, check two things. Does the ash grain stay crisp at grazing angles
  (QA view q07)? Do the aisle doors stay free of aliasing (q06)? The headless renderer cannot show anisotropic filtering.
  *Why:* it affects the wood panels along both aisles.

## Premium Economy: 3 open

- **py Q10 [photo] Which seats get which trim.** ANA uses two trims. Trim A has a dash-weave back and cushion with petal
  "ears"; trim B has a petal back and cushion with dash-weave ears. *Now:* B on the centre block's aisle seats (D / G) and A
  everywhere else, from py_37302 and SANspotter's 26F / 26G. *Why:* it sets the pattern across the 24-seat cabin, and it is a
  one-line change. Tell us if you know the real rule (per row, per letter or random).
- **py Q11 [photo] Literature pocket.** It is an open tray in a dark recess, with a smile-shaped grey rim and a mesh across
  the lower bulge (san_26). Is it the same on every row? *Now:* every row except the bulkhead row 25. *Why:* it is a small
  part of the seat-back view.
- **py Q13 [photo] Seat-back to shell joint.** The model draws a thin recessed seam where the patterned back meets the grey
  shell, on both sides of every seat (py_37301 / 37303). Does the fabric tuck into the shell (as modelled) or sit on it with
  a piped edge? *Why:* it shows on every PY seat side. A close photo of a PY seat side would settle it.

## Economy: 10 open, 1 decided

- **econ Q9 [call] Fabric mix.** In-service photos show mostly petal-fleck and diamond seats, with few tick seats. ANA's own
  photos show all four fabrics about evenly. *Now:* 40 % fleck and 20 % each of tick, mosaic and diamond. *Why:* it sets the
  texture of the whole 116-seat cabin.
- **econ Q6 [call] Blankets in plastic bags at boarding.** Should every seat show bagged blankets (sans 13 / 14), or the clean
  cabin of the official photos? *Now:* clean cabin. *Why:* this is the economy boarding view. THE Room now shows its bagged
  bedding at boarding, so bags here would match it.
- **econ Q27 + Q28 [call] Lumbar pillows.** The y_47300 hero shot has one on every centre-block seat and on one side-block
  seat. y_47301 / 47303 show none on the side blocks, where the belts are laid out. *Now:* pillows on the 4-seat centre
  block only; the side blocks are bare with the belts draped (both raters' default). *Why:* it shows on every economy seat.
- **econ Q31 + Q32: decided (reversible): headrest height per block.** ANA's photos put the 6-way headrest high on the centre
  block (y_47300) and 3-6 cm lower on the 3-seat blocks (y_47301 / 47303 / 47306); one position cannot match both. The model
  sets it per block (3-seat 4.5 cm lower, 4-seat 3 cm higher), with one cover for all seats. *Why:* every headrest in the
  cabin. Say if it should be all at the top position or a per-seat mix.
- **econ Q30 [photo] Back height.** At the landmark-matched q17 camera the backs read ~6 cm tall, so the back is now 4.5 %
  shorter (top ~1.28 m). A published overall height for this Recaro seat would confirm it. *Why:* it sets the skyline of
  the economy cabin.
- **econ Q16 [photo] Aisle-end panel.** Under the aisle armrest of a regular row, is there an open frame (y_47303) or a solid
  white panel (y_47301)? *Now:* solid panel. *Why:* every aisle seat shows it in the aisle view.
- **econ Q26 [photo] Headrest cover width.** The head-on y_47300 gives about 0.22 m. In the y_47303 side view, the headrest
  wing hides half of our cover but not of the real one. Does the real cover wrap round the wings? *Now:* 0.22 m, flat.
  *Why:* it shows in views down the aisle.
- **econ Q18 [photo] Fabric close-ups.** The tiles are cut straight from your official photos. The diamond fabric comes from
  an oblique ~2 mm/px crop, so it is soft up close. A frontal close-up of a diamond seat (and of a fleck seat) would
  sharpen both. *Why:* it matters in close-up seated views.
- **econ Q7 [photo] Footrest hangers.** Are there two white hangers close together at the seat centre (sans 23), or a bowed
  arm that lands on the pedal joint (y_47304)? *Now:* two hangers at the centreline. *Why:* it only shows when seated.
- **econ Q11 [photo] Coat hook.** A rater sees an off-white mushroom knob on the hood side in sans 22. Which side is it on?
  *Now:* no knob. There is a round recess at the right, the default you accepted for econ Q1. *Why:* it is a tiny detail.
- **econ Q29 [photo] Belt colour.** y_47303 shows teal tongue straps; y_47300's side-block straps look dark. *Now:* teal on
  every seat (it measures right in q16 / q17). *Why:* a small detail on every seat.

## Ceiling and bins: 8 open

- **ceiling Q11 + Q6 (with monuments Q1) [photo] Which door do the LALF photos 133 / 134 show?** They show a dark bronze ceiling
  tray with downlights. The ceiling worker uses them for the door-3 bar. The monuments worker uses the same photos for a
  dark soffit in the door-2 passage. So doors 2 and 3 both have a dark ceiling now, and one of them is unverified. Is the
  dark tray at every door, or only at the bar? *Why:* it decides whether a large ceiling area at a door is dark or light.
- **ceiling Q13 + Q14 [photo] Centre-channel PSU depth.** THE Room's centre PSUs hang ~19 mm below the centre-bin doors,
  so from the door-3 cross aisle the door curve cuts their fittings into grey dashes (edge-on occlusion, nothing
  intersects). Is the real PSU panel flush with the door bottoms? *Now:* below, as c_27312 suggests at a grazing angle. If
  flush, the channel geometry would be reworked. *Why:* it shows at the door-3 bar view.
- **ceiling Q12 [photo] Ceilings at doors 1, 2, 4 and 5.** No photo of these was found. *Now:* a light dome with panel joints,
  recessed light strips, downlights, a speaker, an emergency light and a smoke detector. *Why:* you walk under them at every
  door.
- **ceiling Q5 [call] Ceiling gaspers over THE Room centre seats.** Photos show gaspers on THE Room seat shells and on the
  outboard ceiling band. Should the gaspers in the centre-bin channel over the D / G seats go? *Now:* kept, with one reading
  light and one gasper well per seat. *Why:* they are small details on the ceiling over the centre seats.
- **ceiling Q9 [photo] Cove grille slats.** Are they lit white, as c120 suggests? *Now:* light backlit slots. *Why:* the cove
  line runs the full length of both aisles.
- **ceiling Q8 [photo] Row placards.** c120 seems to show the row number, then a boxed seat-letter panel, then a
  standing-person pictogram. *Now:* the row number and one seat glyph per seat. *Why:* the placards show at every row. A
  clear close-up of an ANA 777 placard would settle it.
- **ceiling Q7 [photo] Economy centre PSU.** Is there a separate gasper row? *Now:* one raised dished housing with 4 dark
  sockets, then a smoked sign pill (b_sany_y22). *Why:* it is a small detail.
- **ceiling Q10 [photo] Vault fitting.** Is the bowed rounded rectangle on each vault panel in c120 a speaker or a recess?
  *Now:* a smooth vault-coloured speaker bezel with a slightly darker pocket. *Why:* it is repeated along the aisle ceiling.

## Sidewall, windows, doors and floors: 4 open

- **shell W3.1 + W3c.1 (with monuments Q7) [photo] Door viewing window.** It sits at the window belt, about 0.3 m aft of the door
  centre, from a face-on ANA door-lining video frame. Its size is 0.26 × 0.64 m (bottom 0.69 m, top 1.33 m). The raters
  disagree on its size and height. The R-side doors copy the L-side layout. *Why:* it shows on every Type A door you pass. A
  face-on photo from inside an ANA 777 L2 door (and an R door) would settle it.
- **shell W3.2 [photo] Floors at the door cross-aisles.** The model has grey vinyl inboard and brown carpet in the door bays at
  all five doors, but only door 2 is photographed (sans_09). *Why:* it decides the floor at each door.
- **shell PB.1 [photo] THE Suite carpet pattern.** The F floor and the door bays use THE Room's carpet tile (cut from
  c_27315), in F's own warm brown. The official f_17300 shows sparser, larger light flecks, but it looks like a rendering.
  *Now:* the J pattern. *Why:* the carpet covers the F aisle and the suite floors. A real in-flight photo of the THE Suite
  floor would decide whether F gets its own tile (an f_17300 crop is ready).
- **shell W3c.2 [call] Sidewall linen weave.** The walls are plain satin. A fine linen weave needs a new shared texture layer.
  *Now:* plain. *Why:* it shows only in close-ups of the wall. Say if it is worth adding.

## Galleys, lavatories and bar: 4 open

- **monuments Q8 + Q13 [photo] The door-3 bar's left bay.** The 2019 press render has a black blind pulled down over a
  wider left bay; OMAAT 2020 (omaat_j32, which turned out to be the bar) and KN Aviation show it raised with the ovens
  visible. *Now:* raised, rolled into a black head, with the 2020 oven column. *Why:* the bar is one of the cabin's
  signature spots.
- **monuments Q12 [photo] The door-2 welcome galley.** omaat_j32, which it was built from, is the door-3 bar. No photo
  shown to be the door-2 galley has been found (LALF 133 / 134 fit door 3 too). *Now:* the same face as the bar. *Why:* it
  is the first galley J passengers pass.
- **monuments Q10 (with Q5 / Q8) [photo] Rear galleys and lavatories (doors 4 and 5).** No photo of the new rear galley was
  found. *Now:* the seat-map layout, with two fore-aft galleys and a lav outboard of each. The galley inserts copy ANA's real
  snack-bar galley (satin inserts, ovens with yellow-green label windows, paired brewers). *Why:* they are what you see at
  the back of the cabin.
- **monuments Q11 (supersedes Q9) [call] Cabinet glass in the welcome galley.** The engine has no see-through material for
  monuments, so the smoked-glass door has no pane and its lit contents are toned down. Real photos show the contents through
  a light tint. *Now:* an open pane. Reflection strips were tried and read as wires. *Why:* the welcome galley at door 2.
  Say if lighting should add a transparent material.

## Outside view (wing and engine): 9 open

- **exterior Q8 [call] Wing grime.** The wing has a light photo-derived grime layer (~2.6 %) plus darkening at the hinges and
  trailing edge. Photos range from almost clean (KN46) to streaky (7250). Should it look recently washed or like a working
  airframe? *Why:* the wing fills the window view from the overwing rows.
- **exterior Q9 [call] Spinner colour.** It is mid grey with the white swirl (KN Aviation 7A close-up). An earlier note said
  black (JA796A). *Now:* grey. *Why:* it shows from the engine-side windows.
- **exterior Q12 [call] Fastener rows.** The flaps and spoilers carry faint dotted rivet lines, at about 0.94 of the panel
  tone. KN41 suggests about 0.80. Bolder rows look like stitching from a distance. *Now:* subtle.
- **exterior Q6 [call] GE mark.** It is a ring with the letters GE, low on the inboard fan cowl. No seat view shows it. Is it
  worth keeping? *Now:* modelled.
- **exterior Q11 [call] Shading baked for the day sun.** The canoe and nacelle shading assume the day sun direction. At
  sunset the mismatch is small. *Now:* tuned for day. Say if the day sun should move.
- **exterior Q5 [photo] Canoe (flap-track fairing) tail.** *Now:* a straight keel closing to a small rounded point (_7250).
  An over-wing photo from the left side (seats 13A-19A) of a 212-seat aircraft would settle it.
- **exterior Q13 [photo] Raked-tip upsweep.** The tip narrows to a ~0.20 m point and curls up 0.12 m (KN41). The raters
  think the leading edge sweeps up over a longer span. A photo from rows 17-20A looking straight out at the tip (JA795A if
  possible) would settle it.
- **exterior Q7 [photo] Registration darkness.** The photos range from near-black to dark slate. *Now:* near-black navy. A
  sunlit JA795A close-up would settle it.
- **exterior Q10 [photo] GE90 fan face.** A straight-on photo into an ANA GE90 inlet would let us check the blade ring and
  liner tone. *Now:* it follows LALF _136 and KN Aviation 7A _9.

## Lighting and moods: 10 open, 3 decided

The switches named below are in `src/12_scene.js` (`MOODS`, `LIGHT_TUNE`) and `src/04_shaders.js` (mainFS).

- **lighting Q17 (supersedes Q6): decided (reversible): one white balance per cabin.** ANA's official photos are cool in
  economy and PY (y_47303 / py_37301 whites B-R +17..+28), between in THE Room (c_27312 / 27316 +10) and neutral in THE
  Suite (f_17313 +1); in-flight photos are neutral to warm. The integrator followed each cabin's own official photos.
  *To undo:* `pyCool` 0 and `fjCool` `[0, 0, 0, 0]` in `MOODS.boarding`, and drop `hwK` / `zPY` in mainFS. *Why:* it sets the
  colour of every white surface in Boarding.
- **lighting Q18: decided (reversible): the hue change at the J / PY curtain stays.** The curtain hides it. *To soften:*
  lower `pyCool`.
- **lighting Q19: decided (reversible): the PY side partitions and J / PY bulkhead stay fully cool** (py_37302); only the
  PY rear wall is dialled back (0.4 of `pyW`).

- **lighting Q5 [call] Window sun patches: physical or toned down?** *Now:* physical but capped; on the PY seat back (q14)
  a sun patch reads about 1.5× the surrounding fabric. ANA's official PY photos show no patches. The alternative makes
  every sun patch in the cabin fainter. *Why:* it affects every sunlit seat and floor under the Day sky.
- **lighting Q3 + Q8 [call] Night levels.** Night is one neutral, near-grey level for the whole cabin. Two choices: add an extra
  "Night, warm" mood (gold cove line only, after sany_25)? And should economy be brighter than business at night (the photos
  show about 2×, and sany_40 is also cooler with faint cove lines)? *Now:* one level, set between the two. *Why:* it sets
  the whole cabin in the Night mood.
- **lighting Q4 [call] Level of the Blue mood.** The two in-service photos are exposed about 2× apart: SANspotter's dark
  economy (sany_47) and MileLion's lavender THE Suite (ml_DSC_1945). *Now:* between them. *Why:* it sets the Blue mood
  everywhere. Say which photo to follow, or send one of the blue phase in THE Room.
- **lighting Q15 + Q16 [call] Window-wall brightness.** The wall between and below the windows now darkens from the bin
  light to the window (L176-215), as in-flight photos and y_47303 / c_27300 show, at every distance (a distance gate made
  piers change as you walked). Some official renders keep it brighter (f_17313, f_17304), and so do c_27314 / y_47301 at
  the far wall. *Now:* `beltK` 0.62. *Why:* the whole sidewall in Boarding and Cruise. Say "renders" for 0.7, or 1 to turn
  it off.
- **lighting Q10 + Q13 + Q14 [check] Sharp-only effects on phones.** Contact shading (SSAO) and the rim highlights on PY /
  economy seats run only at the Sharp quality; phones open on Balanced without them. Should Balanced get them (about one
  more geometry pass, plus 3-4 % per pixel)? Should Sharp get a depth-aware blur (two full-screen passes) that would allow
  wider contact shading? *Why:* the contact lines where cushions meet shells (the weakest lighting sub-score). Your GPU
  would show whether it is affordable.
- **lighting Q7 [call] Cruise band.** LALF (lalf_room_119 / 120) shows a pale sky-blue band; tlfl_IMG_9217 and sany_22 show
  the saturated periwinkle the Cruise preset uses. *Now:* periwinkle. *Why:* it sets the Cruise mood. One preset or two?
- **lighting Q12 [call] Amber (Dining) at seat height.** ucr_the-room-cabin shows saturated amber ash panels (model s 0.67
  matches); Frequent Flier's two photos are much greyer. *Now:* ucr. *To change:* `lowTint: [1.0, 1.4, 2.2], lowGain: 0.7` in
  `MOODS.dining` (and `wake`).
- **lighting Q11 [call] Upper window tubs in Boarding.** With the shades open, the upper tub takes the sky's blue-grey, as
  in y_47303. *Now:* on. *To turn off:* `MOODS.boarding.tubSky` `[0, 1]`.
- **lighting Q20 [call] Economy headrest covers.** They take a steel-blue sheen at grazing angles (y_47303). *Now:*
  steel-blue. The earlier navy-violet look is `sheen` 1.35, `sheenTint` 0.3 and `SEATMAT.yCover` #141b44.
- **lighting Q9 [photo] Sunset through open shades.** The panes show a blue-grey cloud deck under an amber cabin (q21). Is a
  warm orange horizon expected? *Why:* only the Sunset sky.

**Open per area:** suite 4, room 8, PY 3, economy 10, ceiling 8, shell 4, monuments 4, exterior 9, lighting 10 (60 in all).
**Decided (reversible) by the integrator while you were away:** lighting Q17 (with Q6), Q18, Q19 and econ Q31 / Q32 (4).

## Already resolved (no answer needed)

**By your 2026-09-24 decisions** (`WORKER_BRIEF.md`, wave 2: "accepts these defaults"):
- **Explicit decisions:**
  - suite Q1: the centre suites stay 1.10 m wide (the 14 CFR 25.815 aisle width).
  - suite Q2 / Q3: the seat card now has "Raise divider" and "Close door" buttons.
  - monuments Q6: the door-3 lavs stay 1.05 m deep.
  - exterior Q1: the registration stays JA795A.
  - exterior Q4: the day sky is a deep-blue cruise sky.
  - lighting Q1 / shell Q2: Boarding stays white, and Cruise and Night carry the blue band.
  - room Q1-5: the evidence-based decisions.
- **Defaults accepted:** suite Q4, PY Q1-3, econ Q1-4, ceiling Q1-4, shell Q5 (an off-white PY / Y shade with a cream
  grip), monuments Q2-5, exterior Q2-3 and lighting Q2. Questions that were re-asked later with new evidence appear above
  under their new ids.

**Settled later by evidence, or superseded:**
- **shell Q1, Q3, Q4, Q6:** sourced. The pane centre is 1.02 m (Boeing D6-58329-2). The door lining comes from ANA lining
  frames. The door bays are carpeted and the galleys have vinyl.
- **room:**
  - Q8: the bundle has the blue duvet on top, as in the photos.
  - Q10: the pillow tone is set between the photos.
  - Q11: the monitor wall is done.
  - Q13 → Q17: the slippers are white in film.
  - Q14: the pillow check pattern is done.
  - Q16: the plaque numbers stay blue-lit.
  - Q21: points to Q18 / Q19.
  - Q20's request for a belt close-up in `test/qa.js` is a test-harness item.
- **py:**
  - Q4 and Q9 are answered by Q10 (two trims).
  - Q5 / Q7: the gooseneck is shown stowed, from the evidence.
  - Q6 → Q11.
  - Q8: the flap aspect is set between the photos.
- **econ:**
  - Q5 / Q14 / Q19: the cover colour is navy satin, and lighting added a grazing sheen (fede907).
  - Q3 / Q8 / Q10: the belts stay blue, the default you accepted, from the official y_47303.
  - Q12 → Q26.
  - Q13 → Q18.
  - Q15 is answered in Q17.
  - Q17 / Q20 / Q21 / Q23 → Q24: the cover was shortened on the evidence.
  - Q25 → Q27.
  - Q22 (a per-view FOV in `test/qa.js`) is a harness item left with the integrator.
- **ceiling:** Q2 → Q7. Q3 → Q6 / Q12.
- **monuments:** Q1 → ceiling Q11. Q4 → Q8. Q7 is merged into the shell door-window item. Q9 → Q11.
- **exterior:** Q3 → Q6.
- **Filed after 2026-10-25 and settled:**
  - suite Q9: the cap value shipped (`fCap` #777369; lit cap / wall 0.75, photo 0.74); both raters 8.8.
  - py Q12: the q13 framing is unchanged (pixel-aligned); the raters' old references came from an older lighting head.
  - lighting Q6 → Q17.
  - econ Q28 → Q27.
