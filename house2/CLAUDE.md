# Second house exterior reconstruction — project notes for Claude Code

The same method as `house/` (read `house/CLAUDE.md`: pipeline, coordinates, viewer, packaging) applied to a second
listing: a 2008 two-storey Craftsman (grey cedar shingle, white trim, tapered columns on stone piers, wraparound front
porch, complex hip roofs with 50 solar panels), an attached 3-car garage, ~1 acre of grounds: gated paver driveway,
front lawns with curved flagstone walks, rear flagstone patio, pool + spa, stone outdoor fireplace, BBQ kitchen, vine
arbor, synthetic lawn, play structure in a wood-chip yard, fenced vegetable beds. Owner's brief (2026-11-27): "Construct
<listing> using similar approach to the last one we built".

**Public repo:** the listing photos and anything cut from their pixels live only in the git-ignored
`house2/refs/cache/` and `house2/out/`. Never commit them, and do not write the property's address or the listing URL
into committed files (the folder is called house2 for that reason).

## Sources
- 30 listing photos in `refs/cache/photos/` (2500 px): `p29` near-nadir drone aerial of the whole lot (the plan),
  `p28` high oblique drone view of the rear, `hero` / `p01` the front porch, `p18`-`p27` the rear yard, pool, fireplace,
  play area, garden; the rest are interiors.
- Listing facts: house 4,800 sq ft on two levels + 789 sq ft attached 3-car garage, lot 1.03 acres (44,866 sq ft),
  50-panel solar system, built 2008.
- The property video (Vimeo, 183 s, 4K source) cannot be fetched from this server: Vimeo answers every request from
  it with a Cloudflare human-verification page (the first house's video downloaded before that started). The owner
  supplied its frames every 100 ms instead (a screen recording of the player, 1362 x 766):
  `refs/cache/frames_all/frames/frame_<ms>ms.jpg` + `frame_timing.csv`. Shots used for SfM (`tools/sfm.py SHOTS`,
  ranges clear of the cross-dissolves; masks over the player's bar, icons, the watermark and the title):
  approach 14-16 s, pool top-down 21.5-22.8, front 24-26, front roof 26.5-28.3, play area + pool 123.5-126.5,
  rear 130-138.5 (three moves), top-down 139-141.5, lawn 142-146, rear 153.5-156.5, high orbit 157.5-160.5.

## Commands (run from `house2/`)
As in `house/CLAUDE.md`, with `house2` paths: `python3 -I model/build.py`, `node tools/shot.cjs ...` (dev server:
`python3 -m http.server 8777 --directory .` from `house2/`), `python3 -I tools/crop.py ...`, `python3 web/package.py`.
`python3 -I tools/vggt_run.py refs/cache/vggt/run1.txt refs/cache/vggt/run1.npz` = cameras + points of the 13 exterior
photos (CPU, ~20 min).

## Surveys
`survey/roof.json`, `site.json`, `front.json`, `rear.json`: every element in ORIGINAL image pixels of its photo
(written and then overlay-checked by agents; positions good to a few px).

## Frame, cameras, heights (done 2026-11-27)
- SfM (COLMAP) on the video frames: model 1 = 90 frames of the rear / pool / play area / lawn / high orbit (frame S);
  `tools/sfm_frame.py` uprights it from the drone gimbal (camera x axes level: ~1 deg).  The front shots formed separate
  models (not used).
- Photos registered by guided learned matching (`tools/lg_reg.py`: DISK + LightGlue, kornia, CPU): the aerial p29 is
  warped into each near-nadir frame's view by a homography and matched there (winter vs spring, ~150 deg turned: raw
  matches fail); p28 / the rear ground photos match the orbit / rear frames directly.  Frame pixels take their 3-D
  point from the SfM points around them (inverse depth fitted as a local plane).  Saved cameras go to
  `refs/cache/cams_fixed.json`; `model/frame.py world_cams()` merges them.  p29: 794 inliers, 1.4 px; p28 (re-fit with k1 free on the 16 orbit frames): 406, 1.9 px, hand-picked pool corners
  4 / 9 px; p21: 272, 1.8 px.  The other rear ground photos stand where the video never flew: fit them on the model.
- World frame (`survey/frame.json`): X = the aerial's image right, Y = its image up (into the lot; the gate at the
  image bottom-left, driveway up the left edge; the STREET itself lies ~50 m south behind the tile-roofed neighbour,
  reached by a lane from the SW gate: ground.STREET), Z up; origin = the pool water's centre, Z = 0 = the pool deck.
  Scale 8.548 m per S unit from the pool = 20 x 40 ft (PV modules 0.798 m and the 6 ft raised beds agree within 3 %).
- Heights (tools/epi.py: an aerial pixel's ray drawn into p28 / a rear frame with height ticks): one-storey eaves
  3.1 (north porch) - 3.6 (patio wing), two-storey eaves 6.3-6.5, the core's hip apex ~8.5, the balcony gable 7.5-8.0,
  covered rear patio floor +0.15.  `model/roof_solve.py` -> `survey/roof_3d.json`: every roof plane of roof.json in 3-D
  (vertices on their aerial rays, planes, level eaves, pitch prior 28 deg; one-storey roofs never share vertices with
  two-storey ones).  Two-stage solve; corrections live in roof_solve.py: REPLACE (the diagonal entry-porch leg),
  PITCH_BLOCK / PITCH_PLANE (garage + north wing ~19 deg), RIDGE_Z (balcony gable 7.97), UNDER_WALL, garage_gable
  (symmetric 26 deg south gable).  roof_3d.json is the single source: roof_details reads it, and imports
  house.footprints / _planes / OPENINGS / entry_frame() (keep those names).
- Cameras fitted on the MODEL (photos the drone never saw): hero / p01 in survey/cams_world.json (pairs_world.json),
  every other photo / video frame in survey/photo_cams/<name>.cam.json (+ .pairs.json; tools/fit_world.py PAIRS OUT);
  model/frame.py world_cams() loads SfM < cams_fixed < cams_world < photo_cams (the last wins).

## Builder conventions (zones)
- `model/plan.py` is the shared plan: `aerial_xy(uv, z)` / `aerial_ring(poly, z)` (aerial pixel -> world at height z:
  ALWAYS pass the real height, p29 is a perspective view from 49 m), `site(id)` / `site_ring(id)` (site.json elements),
  `ground_z(x, y)` (terrain: REGIONS levels per surveyed area + a membrane between them), house datums FLOOR 0.45,
  REAR_PATIO_FLOOR, NCP_FLOOR, FRONT_PORCH_FLOOR, FRONT_WALK, EAVE_1 / EAVE_2.  Everything stands on ground_z.
- Zones (`model/zones/<zone>.py`, `build() -> [Part]`, optional `MATERIALS = {name: dict(color, roughness, ...)}`
  merged into the shared table; new names must not clash with `model/materials.py`).  Ownership: `ground` (terrain
  mesh, lawns / beds / flagstone / pavers / chips / gravel / turf surfaces, walks, steps, retaining walls, edging; may
  edit plan.py REGIONS / SLOPES), `pool` (pool, spa, coping, cover box, pool steps), `yard` (fireplace + seat wall,
  arbor + bar + BBQ kitchen, furniture, play structure + slides, vegetable garden + beds + fences + gates, small
  fixtures), `planting` (trees, shrubs, hedges, tree belts, bed plants, neighbours / backdrop), `house`
  (`zones/house.py` + `model/roof_solve.py`: walls, openings, doors, windows, garage doors, porches, columns on stone
  piers, railings, balcony, trim), `roof_details` (solar arrays, skylights, vents, chimneys, gutters, downspouts,
  ridge / hip caps).  Edit only your own files; ask for shared changes in your report.
- Triangle budgets (the phone tier must stay light): house 150k, roof_details 60k, ground 120k, pool 30k, yard 120k,
  planting 150k.  Flat-shaded primitives from `model/kit.py` / `model/massing_kit.py`; kits `model/pool.py`,
  `model/plants.py`, `model/furniture.py`, `model/fixtures.py`, `model/openings.py` came from house 1 (reuse, adapt
  in your own zone file).
- Verify by rendering through registered cameras: `python3 -I model/build.py --zones <zone> --out test_<zone>` (or
  several zones), then (dev server on 8777, from house2/) `node tools/shot.cjs OUT.png "view=<camera key>&mode=white
  &still=1&glb=test_<zone>.glb&meta=test_<zone>_meta.json" 1200` and `python3 -I tools/compare.py <camera key> OUT.png
  CMP.jpg edges [x0,y0,x1,y1]`.  Camera keys: `photos/p29_ddf5dc.jpg` (aerial), `photos/p28_7ae0dd.jpg` (high
  oblique from the NE over the play area), any photo in `refs/cache/cams_fixed.json`, and the video frames
  `frames_all/frames/frame_<ms>ms.jpg` (ms: pool top-down 21500-22700 step 300; play area + pool 123500-126500 step
  300; rear 130000-131800 / 132500-135500 / 136000-138400 step 300; top-down play 139000-141400 step 300; lawn
  142000-146000 step 400; rear low 153500-156500 step 300; high orbit 157500-160500 step 200).  The front photos
  (hero, p01) are not registered: fit them on the model with `tools/fit_world.py` (survey/pairs_world.json).
  Software GL: ~1-3 min a frame; render only what you need, 1000-1400 px wide, scratch files in out/tmp/ (ignored).
- Finished look: `model/swatch.py` cuts photo patches (straightened on their plane at true scale, delit, tiled, mean
  albedo set) into out/swatch_*.jpg (never committed) for full builds; the viewer's looks for house 2's material names
  are in `web/viewer/looks/house2.js` (unknown names fall back to the GLB's colour).  Packaging ships the whole viewer
  folder and every swatch the meta lists.  White-model-only bundle: `python3 web/package.py --white`.
- Artifact: https://claude.ai/artifact/4XqAGij5ZB9PctWLKJ86qx (private; v1 white model only, v2 the textured model with
  the white-model toggle; update it in place from a clean checkout's build: python3 web/package.py --model-dir DIR).
