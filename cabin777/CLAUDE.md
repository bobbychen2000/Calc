# ANA 777-300ER cabin walk (THE Suite / THE Room)

An interactive 3D model of the inside of ANA's 777-300ER in its "new 212 seats" layout, as flown on some SFO–NRT (NH7/NH8) rotations:

- 8 THE Suite (first)
- 64 THE Room (business)
- 24 Premium Economy
- 116 Economy

It is a single self-contained HTML page. It runs on a custom WebGL2 engine with no libraries and is designed for phones first. The engine came from an earlier project, a United 787-9 cabin that was published as the claude.ai artifact "787-9 Cabin Walk", and was re-parameterised for the 777.

## How the user wants this built (follow these)

- **Don't assume; verify.** Check key facts against real sources: seat maps, reviews, maker and airline statements.
  - Label every claim as verified, derived or approximated. REFERENCE777.md holds the sheet with sources.
  - If a key original can't be obtained, ask the user for it rather than shipping a look-alike with a disclaimer.
- **Build unit by unit.** Render each unit on its own in the studio (`test/studio.js`), review the render, fix it, and only then assemble. Share the review renders with the user.
- **Run a visual QA loop** on the assembled cabin, fix what it finds, and re-render.
- **Detail matters.** The user pushed for more detail on ceilings and seats in the 787 project.
- **Photo textures:** the user suggested reusing textures from ANA photos found online.
  - Photos the user supplies can be used as a colour and pattern reference. Paint the textures procedurally from that reference.
  - Don't paste other people's copyrighted photos into a published page. The user's own photos are fine to use directly.
- **Deliverable:** publish as a claude.ai artifact.
  - The file is page content without html/head/body tags, with `<title>` first.
  - Fonts come only from Google Fonts; everything else is inline.
  - `dist/cabin.html` is already in that format.

## Build and test

```bash
python3 build.py                       # -> dist/cabin.html (artifact body) + dist/test.html (standalone page)
open dist/test.html                    # any WebGL2 browser
npm i -D playwright && npx playwright install chromium   # once, for headless renders
node test/studio.js out review/spec1.json               # studio renders of units (UNITS / STUDIO_UNITS)
node test/shot.js out 960 600 1 door1                   # assembled-cabin shots (VIEWS in the script)
node test/qa.js out 800 500                             # QA views  (NOTE: still the 787 list, rewrite for the 777)
python3 test/sheet.py out sheet.png 2                   # contact sheet of out/q*.png
```

- In the tests, `window.__app` is the running App.
  - `__app.setView(pos, yaw, pitch)` places the camera.
  - `__app.sit(seat, {instant:true})` sits in a seat.
  - `__app.renderNow()` renders a frame.
  - `studioRender(__app, geo, opts)` renders one unit (see `src/14_studio.js`).

## Coordinates

- **Axes:** metres. z is the distance aft of the nose (forward is −z). x is positive to the right and negative to the left. y is up, with the floor at 0.
- **Doors 1–5:** z = 5.40, 16.80, 32.70, 44.30 and 58.70. They are Type A, 42 × 74 in.
- **Fuselage section:** the interior trim circle has R = 2.935 m (5.87 m cabin), centred 0.92 m above the floor.
- **Windows:** 10 × 15 in glass, centred at y = 1.13, one per 21 in frame bay.

## Source files (`src/`, concatenated in name order by build.py)

- **00_math.js / 01_gl.js / 02_geo.js / 03_tex.js / 04_shaders.js:** the engine.
  - Math, and a WebGL2 wrapper with instancing.
  - Geometry primitives plus `Builder`, which bakes per-vertex colour and material.
  - Procedural detail layers.
  - Shaders: GGX shading, a shadow map, an AO volume, a window sun LUT, sky, glass and glows.
- **05_layout.js:** the ANA seat map, turned into seats, monuments, zones, windows and walkable areas.
  - Seat kinds are `suite`, `room`, `py` and `econ`.
  - THE Room seats belong to nested pairs: odd rows face rear in the outer column, even rows face forward in the aisle column.
- **06_atlas.js:** canvas atlas with seatback screens, signs, row placards, seat plaques and the washi-paper panel.
- **07_shell.js:** floor, sidewalls with window reveals, door surrounds, and window shades.
  - F/J windows get electric two-stage shades (sheer, then blackout). PY/Y windows get manual pull-down shades.
  - Shades are instanced; `shadeMats(w, fraction)` gives each instance its transform.
- **07b_ceiling.js:** curved aisle ceiling panels between the outboard and centre bins, with cove light. Also the door-area domes and monument ceilings.
- **08_bins.js:** 777 outboard pivot bins (4-frame modules) and double-sided centre bins (2-frame modules), PSUs and row placards.
- **09_seats.js:** seat models.
  - Recaro economy, ZIM premium economy, the THE Room nested-pair parts (`roomPart('O'|'E')`) and THE Suite (`suiteUnit`).
  - Also far LODs, bed variants, per-kind helpers (`seatPickBox`, `seatEye`, `seatBedCenter`), the seat LOD system, and the `UNITS` studio catalogue.
- **10_mono.js:** lavatories, galleys, the door-3 self-service bar, closets, partitions, Type A door linings and jump seats.
- **11_exterior.js:** 777-300ER wing with raked tips, and the GE90-115B nacelles.
- **12_scene.js:** scene assembly, AO volume, shade states (`setWindow`, `setAllWindows`), moods, skies and rendering.
- **13_app.js:** camera modes (walk, seat, x-ray), picking, lie-flat, seat card, map, guided tour and UI.
- **14_studio.js:** studio renderer and extra review units: wing, ceiling slice, window shades, the door-3 bar group and the door-4 galley group.
- **page.html:** UI shell and styles. Its about panel lists the sources and approximations.

## Status

**Done**

- Research is complete; see REFERENCE777.md.
- Layout, shell and shades, bins and ceiling, all four seat products, monuments, exterior and the app are wired up.
- The page builds and runs. It loads in about 18 s in headless SwiftShader; build time is about 1.7 s.

**First unit review** (`review/units-review-1.png`, `review/assembled-door1.png`) found these problems to fix next:

1. **THE Room reads as disjointed parts.**
   - The O seat's aisle corner has a tall 0.36 m-wide ash slab. It should be a low armrest ledge (0.66 m) with the pop-up privacy panel retracted inside.
   - The shells should read as continuous shoulder-height walls. Reviews say "walls along the aisle all have a slight curve", "beige wood panelling and muted dark grey finishes".
   - The seat "plinth" box makes each seat look like an armchair. The cushions should be thin ("as thick as ironing boards") on a dark recessed base.
   - The door-edge strips look like sticks.
2. **THE Suite's reclined seat back pokes through the aft wall.** Move the seat forward in `suiteUnit`: `S = M4.trs(seatX, 0, -0.42)`. Check that leg room to the ottoman still works.
3. **The wood detail layer is too strong and wavy, and the ash is too pale.** Tone down `LAYER_PARAMS[10]` (for example `[2.4, 0.12, 0.28, 0.25]`) and darken the ash to about `#bfae90`.
4. **Still to studio-review:**
   - `econ3`, `econ4`, `py2`, `py4`
   - `ceiling`, `windows`, `door3`, `galley4`, `wing`
5. **Rewrite `test/qa.js` views for the 777.** Suggested views:
   - door 1 and THE Suite, seat 1A, and 1A in lie-flat
   - THE Room main cabin, 11A, 12C, and the centre pair 11E/F
   - the bar at door 3
   - 17A window view of the wing and GE90
   - PY 25–27 and 26A
   - economy forward and aft, and 35C
   - rear galley, night mood, sunset, x-ray

   Then run the QA loop and publish.

**Open item:** no text source gives the Economy and Premium Economy fabric colour. Both are modelled as muted blue-grey and flagged in the about panel. If the user supplies photos, match their colours. ANA's official photos are `new212-01..07.jpg` on ana.co.jp's 777-300ER economy page. They are image-only, so ask the user to attach them.
