# Monuments gap analysis, w9: what would lift the area from ~7.8 to 8.5

Inputs: the w9 renders in /tmp/claude-0/w9 (930x575), ratings w7a to w8b, and the wave-3 report. Photos are in
ref/web/monuments. Stats come from PIL. L is luma (0-255). hpSD is the luminance high-pass SD (sigma-6 blur removed) as a
percentage of the mean, which measures surface texture.

Why the score has stalled: the last two waves fixed small, item-level things (tags, drapes, arcs). The four galley
details (door 1, door 4, door 5 and the inserts, scored 7.5-8) and the lav exteriors (7.5) still share three faults across
the whole surface:
- the aluminium reads dark and metallic, where the real metal is satin and pale;
- the beverage makers are black boxes;
- the large faces have no surface texture at all (hpSD 0.2-1 % against 5-20 % in the photos).

These faults cover most of the pixels in m01, m09, m12, q19 and m15. The bar is capped at about 7.5 because no photo of
it exists, so the gain has to come from the galleys.

## 1. Galley insert tone and material response (value structure). Expected gain about +0.3

**Evidence:**
- **Real inserts are satin, light warm grey, and lighter relative to the wall than ours.**
  - sansY_44: oven door (440,110,600,180) #776a55, L107; cart door (320,660,470,780) #918983, L138; wall laminate
    (150,220,260,330) L176. So oven/wall = 0.61 and cart/wall = 0.78.
  - omaat_room_32: stainless inserts (175,360,240,560) L146 are the brightest part of the welcome galley.
- **Ours render as dark brushed metal.**
  - m01 oven face (160,240,280,370): L50 = 69, p90 = 76.
  - m09 standard unit (160,240,310,380): L62, with regular horizontal hairlines (hpSD 7 %, all in one direction).
  - m03 welcome inserts (0,250,100,400): #464745, L70, against 146 in the photo.
- **Ours inverts the relationship between the upper and middle rows.** The upper compartments (galleyWhite, m01
  (300,60,420,180)) render at L142 with p90 up to 220, as a soft white gradient with rounded "frosted glass" corners. In
  sans_38 the upper row is grey stainless with frames, at L61, which is 0.81 of the wall.
- **The whole face reads too white.** m01 p10/50/90 = 14/94/219, against sans_38 23/76/165.

**Cheapest fix (10_mono.js, MONMAT only, no geometry):**
- `alu` becomes `{ c:'#bdb8ae', r:0.55, m:0.12, l:LAYER.plastic }` and `aluDark` becomes `{ c:'#aaa69d', r:0.55, m:0.12 }`.
  The satin anodised finish stops mirroring the dark environment and loses the brushed hairlines.
- Keep `LAYER.brushed` only on `steel`/`steelBright` trim.
- Give the upper compartment faces (buildGalley l.453, and the door-5 aft wall l.736-751) a new
  `compartment: { c:'#b4b1a9', r:0.5, m:0.1 }` instead of `galleyWhite`. Keep `galleyWhite` for the carcass, side walls
  and cap only. This also tones down the white blow-out band, which is partly a lighting issue.
- Target: oven/wall about 0.6-0.7 in m01 and m09.

## 2. Beverage makers and jugs: silhouette and material. Expected gain about +0.2

**Evidence:**
- **The real brewers are stainless boxes with a black window, not black boxes.**
  - sans_38 and sansY_44 (630-1000, 0-280): stainless boxes, frame #59544c, about the same tone as the jug #605a4e.
  - Each has a black window and a short black control strip on top, a fold-out stainless brew handle, and a bulbous
    stainless jug with a black handle.
- **Ours are solid black.** m01 (290,240,420,280) is #070a0a.
- **Our jugs read as stacks of grey discs.** This was flagged in w8a. m01 (340,330,385,390) is #444952. The cause is the
  12-sided `gCyl` with `MONMAT.steel` = `LAYER.brushed`: the brushed streaks wrap round the cylinder as horizontal rings.

**Cheapest fix (buildGalley t===1, l.441-448):**
- The head and the bay sides become `steel`. Only a 0.03 m top strip and the bay back stay `bevBlack`.
- Add a 2 mm `ovenGlass` window quad on the head.
- Replace the jug with a `gLathe` pot about 0.10 m across with a bulging profile (12 segments, about 250 tris) and a
  small `gTube` black handle.
- Give the jug a new `jug: { c:'#c9c8c4', r:0.2, m:0.9 }` with no detail layer.
- Cost: about 6 brewers, so +2k tris. This fits the 13 % headroom.
- Apply the same steel and ovenGlass change to the welcome galley brewer (l.318-319).

## 3. Surface texture on the large galley faces: grime mottle, frame channels and real-size latches. Expected gain about +0.15-0.2

**Evidence:**
- **The faces are dead flat.**
  - m01 upper compartments: hpSD 0.9 %. q19 aft waste flap (430,440,500,530): 2.6 %. m09 standard units: 7 %, but as
    regular hairlines.
  - The real faces carry soft smudge and wear mottle: sans_38 cart door 4.8 %, sansY_44 oven 10 %, sansY_44 cart 14 %.
- **The real inserts have structure ours lack.** Each sits in a light extruded aluminium frame about 15-20 mm wide, with a
  dark gap of about 4 mm. The ovens have large yellow-green label windows: sansY_44 label #666338.
- **Our latches are too small and the wrong colour.**
  - Real: chunky copper-orange anodised turn-buttons, about 35 x 50 mm with a round face (sansY_44 latch #59382d, lit
    highlights much warmer).
  - Ours (`copper`, 16 x 30 mm, #3b1512 in m01) read as dark red specks.

**Cheapest fix:**
- **New photo layer** `g_alu` = layer 28 in 03_tex.js (shared file, one line per key):
  - Set `N_LAYERS = 29`, add `28: 'g_alu'` to PHOTO_LAYERS, and set PHOTO_GAIN 0.35 and LAYER_PARAMS `[4, 0.02, 0.35, 0.3]`.
  - Cut it in make_swatches.py like `x_skin()`: sans_38.jpg box (610,715,740,800). That is the clean upper half of a cart
    door, without the handle or latch.
  - Process it with MedianFilter(3) and heavy-blur flattening, at about 0.25 m (130 px across a 0.3 m door).
  - Put it on `alu`, `aluDark` and `compartment` from item 1. The target is hpSD 4-6 % on m01, m09 and q19 faces.
- **Seams:** in buildGalley, add a dark 4 mm seam quad (`gQuad`, 2 tris each, `#2a2a2a`) round each insert. That is
  4 strips at o+0.001 behind the insert's 15 mm overhang, or a slightly larger dark gBox behind each insert (12 tris).
- **Latches:** enlarge `copper` latches to `gRBox(0.032, 0.05, 0.03)` with a 12-segment `gCyl` round face. Recolour
  `copper` to `{ c:'#b0532f', r:0.3, m:0.5 }` (lifted so it renders about #8a4a32). That is about 150 latches x 40 tris,
  roughly 6k.
- **Labels:** make the oven `card` labels larger and yellow-green (`#d6d48a`, 0.14 x 0.09 m, top-left of each oven door,
  as in sans_38).

## 4. Door-2 welcome galley: body tone and the glass cabinet, still flagged after two rounds. Expected gain about +0.15

**Evidence:**
- **The body is too dark.** omaat_room_32 charcoal stiles and panels: (925,300,955,600) #3f3a2d L58; (700,480,725,700)
  #343024 L47; lower frame L67. m03: (455,120,575,300) #22201e L32 and the stile (560,140,580,440) L24. That is about
  0.55x.
- **The pane is flat.** omaat_room_32 pane (740,190,900,700): p10/50/90 = 28/60/82, with boxes and papers visible.
  m03 pane (600,170,720,430) is a flat L70 (p10/p90 = 70/74). It reads as four equal grey panels, and nothing behind it
  shows.

**Cheapest fix (buildWelcomeGalley):**
- `welcomeChar` goes from `#5e5a52` to about `#7a7466` (the render compresses dark albedos about 0.55x).
- Darken the pane to `{ c:'#2e2c2a', r:0.08, m:0.2 }` with no emission.
- Move the 4 content boxes and 3 shelves to o+0.0895, just in front of the pane. Multiply their colours by about 0.55 so
  they read as seen through smoked glass, and give the boxes e 0.05.
- Add one 0.03 m vertical sheen quad near the hinge stile (`#77726c`, r 0.1). Do not tilt it: the tilted one read as a
  plank in w8.
- Add the black caution-text plate on the top rail (omaat_room_32 x780-900, y140-185). Use a 0.22 x 0.08 `bevBlack` quad
  with 3 thin `label` lines.
- Cost: under 100 tris.

## 5. Large flat lavatory, closet and partition faces: panel seams and edge trims. Expected gain about +0.1

**Evidence:**
- **Our faces have no texture or detail.** m15 J lav back (20,180,240,360) has hpSD 0.3 % (p10/p90 174/191), and the J
  closet back R (600,260,900,370) has 0.2 %. Apart from one literature pocket, each face is a blank cream plane.
- **The real J faces have seams and trims.** omaat_room_36 (470,200,690,285) shows hpSD 5.4 %, an inset-panel seam line
  about 1.1 m above the floor, and a dado and kick strip. The real lav corners have aluminium edge guards (tpa_Image-2-3:
  aluminium frames on every edge of the door-1 lavs and the cockpit door).
- m11 (the rear Y partition and lav faces) and m09 (the door-4 side walls) show the same blank planes.

**Cheapest fix (buildMon, monoBack, buildBulkhead):**
- Reuse the existing `seamJ` material and draw seams as 3 mm `gQuad` strips: a horizontal one at 1.1 m and a vertical one
  every about 1.2 m on monoBack faces wider than 0.9 m.
- Add a 25 mm `steel` corner-guard gBox on each aisle-side vertical edge of the lavs and closets, 0.1-1.9 m high
  (12 tris each).
- Add a 0.10 m `kick` strip at the floor on PY/Y lav faces.
- Cost: under 3k tris in total.
- Optional: put `LAYER.plastic` mottle on these faces through the item-3 `g_alu` layer at a lower albedo. This needs its
  own layer index because LAYER_PARAMS is per layer, so leave it for later.

## Not worth the effort now

- **Bar (capped at 7.5):** no in-service photo exists. Ask the user (questions_monuments.md item 7).
- **Ebony streaks (q01):** they match tpa_Image-2-3, which has the same strong horizontal streak figure. q01 hpSD is
  11.2 %. Leave it.
- **J-lav ash door (m17):** hpSD 4.6 % against lalf_096 9.9 % and kn_32 6.1 %. The contrast is fine. The waviness at
  1.86 m is minor.

## Budget and expected result

- **Triangles:** about +11k in total (item 2 2k, item 3 6k, item 5 3k), which takes 130k to about 141k.
- **Score:** items 1-4 are mostly MONMAT and quads, with one new swatch. All five together should lift the galley details
  from 7.5-8 to 8.5 and the lavs to 8. Overall that is about 8.3-8.5 against 7.8 now.
- **Order:** do items 1 and 2 first and re-rate. Item 3 needs the shared 03_tex.js edit.
