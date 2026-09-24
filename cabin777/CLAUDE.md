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
- **Photo textures:** the user asked to reuse textures from ANA's official website photos.
  - The official photos are reference only and live in `ref/ana/` (gitignored; `python3 test/fetch_refs.py` re-downloads them). Web photos found during QA go to `ref/web/<area>/` (gitignored).
  - Patterns (fabrics, ash, wood, carpet) are small processed tiles cut from those photos by `test/make_swatches.py` into `tex/` (tracked). They are flattened, tileable and colour-relative, and `build.py` embeds them. The material colour in code still sets the mean colour.
  - Never embed or commit whole photos. The user's own photos (`photos/`, if any) may be used directly.
- **Deliverable:** publish as a claude.ai artifact.
  - The file is page content without html/head/body tags, with `<title>` first.
  - Fonts come only from Google Fonts; everything else is inline.
  - `dist/cabin.html` is already in that format.

## Build and test

```bash
pip install pillow numpy                                 # once (tests + swatches)
python3 test/fetch_refs.py                               # once: official ANA photos -> ref/ana (reference only)
python3 build.py                                         # -> dist/cabin.html (artifact body) + dist/test.html (standalone)
CABIN_DIST=/tmp/x python3 build.py                       # build somewhere else (parallel workers: never commit dist/)
node test/studio.js <out> review/spec_room.json          # studio renders of units (UNITS / STUDIO_UNITS)
node test/qa.js <out> 930 575 [view ...]                 # the 22 QA views + <out>/pairs.json (view -> ANA reference photo)
DPR=2 CABIN_PAGE=/tmp/x/test.html node test/qa.js ...     # 2x close-ups of another build
python3 test/make_swatches.py                            # re-cut the photo swatch tiles in tex/ (needs ref/)
node test/blender/export.js <out> test/blender/spec_review.json && blender -b -P test/blender/render.py -- <out>/<unit>.json --out <out>
                                                         # optional Cycles reality-check render (apt install blender)
```

- Playwright and Chromium are preinstalled at `/opt/node22/lib/node_modules/playwright` and `/opt/pw-browsers`. Headless SwiftShader takes about 20 s per page load and 10–30 s per 930×575 frame.
- In the tests, `window.__app` is the running App.
  - `__app.setView(pos, yaw, pitch)` places the camera. yaw 0 looks forward (−z), −π/2 looks right (+x).
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
- **09_seats.js:** the shared seat code.
  - `SEATMAT` (every seat material), `SEC`/`loftAt` helpers, `mirrorGeo`, per-kind helpers (`seatPickBox`, `seatEye`, `seatBedCenter`), `buildSeats`, the seat LOD system and the `UNITS` studio catalogue.
- **09a_econ.js / 09b_py.js / 09c_room.js / 09d_suite.js:** the product builders.
  - Recaro economy (`econSeat`/`econUnit`), ZIM premium economy (`pySeat`/`pyUnit`), the THE Room nested-pair parts (`roomPart('O'|'E')`, `roomDivider`) and THE Suite (`suiteUnit`), each with its far LOD and bed variants.
  - New materials for a product: `Object.assign(SEATMAT, {...})` at the top of that product's file.
- **10_mono.js:** lavatories, galleys, the door-3 self-service bar, closets, partitions, Type A door linings and jump seats.
- **11_exterior.js:** 777-300ER wing with raked tips, and the GE90-115B nacelles.
- **12_scene.js:** scene assembly, AO volume, shade states (`setWindow`, `setAllWindows`), moods, skies and rendering.
- **13_app.js:** camera modes (walk, seat, x-ray), picking, lie-flat, seat card, map, guided tour and UI.
- **14_studio.js:** studio renderer and extra review units: wing, ceiling slice, window shades, the door-3 bar group and the door-4 galley group.
- **page.html:** UI shell and styles. Its about panel lists the sources and approximations.

## Parallel work (several Claude sessions on one branch)

- Each worker owns a set of files and edits only those:
  - suite: `09d_suite.js`
  - room: `09c_room.js`
  - py/econ: `09a_econ.js` and `09b_py.js`
  - ceiling/bins: `07b_ceiling.js` and `08_bins.js`
  - shell (sidewall, windows, shades, floor): `07_shell.js`
  - monuments: `10_mono.js`
  - exterior: `11_exterior.js`
  - lighting/integration: `04_shaders.js`, `12_scene.js` and `13_app.js`
- Shared files take small, local edits only, one line per key: `SEATMAT` values in `09_seats.js`, and `PHOTO_GAIN`/`PHOTO_ENC`/`LAYER_PARAMS` in `03_tex.js`.
- When editing a shared file, say so in the commit message.
- Never commit `dist/`. Build with `CABIN_DIST` outside the repo; the integrator rebuilds `dist/`.
- Commit with explicit paths: `git commit -m ... -- <your files>`.
- Before pushing, run `git pull --rebase origin <branch>`. When resolving a conflict, keep both sides; the other side is another worker's area.
- Retry the push on rejection.

## Status

- **Unit pass 1 (done).** Every unit was rebuilt against the 41 official ANA photos, using colours sampled from them:
  - all four seat products
  - the ceiling and bins
  - the sidewall and windows
  - the monuments, including the door-3 bar
  - the wing and GE90
- **Photo swatch textures (done).** The fabric, ash, wood and carpet patterns come from `tex/`.
- **Adversarial photo QA** (`test/qa.js`, 22 views): raters score each area 0–10 against the ANA photos plus in-flight trip-report photos, then fixers work per file group.

  | Round | Suite | Room | PY | Econ | Ceiling | Sidewall | Monuments | Exterior | Lighting | Mean |
  |---|---|---|---|---|---|---|---|---|---|---|
  | 1 | 5 | 3.5 | 5 | 4.5 | 4.5 | 5.5 | 4 | 4.5 | 4.5 | 4.6 |
  | 2 | 5.8 | 6.5 | 4.5 | 5 | 6.3 | 6.6 | 4.5 | 5.2 | 4.5 | 5.4 |

  Round 3 is being rated. Target: every area at 8.5 or above with no high-severity issues.
- **Still to do:** run QA rounds until the target is met, then write the before/after sheet, update the about panel's sources and approximations, and publish `dist/cabin.html`.
