# House exterior reconstruction — project notes for Claude Code

A navigable, photoreal 3-D model of one real house's **exterior and grounds** (two-storey white modern-farmhouse new
build, standing-seam + shingle roofs, front porch, rear louvred pergola, pool, pool cabana, cedar fences, a huge oak),
rebuilt from its public listing photos and property video. Plain Python + numpy for the model, three.js r160 for the
viewer. Owner's brief (2026-11-26): "reconstruct a photoreal world 3d view", outside only is fine; white model
(白模) first, then the finished look (成片).

**Public repo:** the listing photos, video frames and anything cut from their pixels live only in the git-ignored
`house/refs/cache/` and `house/out/`. Never commit them, and do not write the property's address or the listing URL
into committed files.

## Commands (run from `house/`)
```bash
pip install numpy scipy pillow opencv-python-headless pycolmap trimesh shapely mapbox_earcut   # + torch (CPU) for vggt
# three.js r160 for the dev viewer: (cd /tmp && npm pack three@0.160.0 && tar xzf three-0.160.0.tgz) -> web/three_local/{build,examples}
python3 -I model/build.py                      # all zones -> out/house.glb + out/house_meta.json
python3 -I model/build.py --zones test_X --out test_X      # one zone alone (asset test scenes)
python3 -m http.server 8777 --directory .      # dev server the screenshot tool expects
node tools/shot.cjs OUT.png "view=front&still=1" 1400                    # headless render (software GL)
node tools/shot.cjs OUT.png "view=frames/seg002_043.jpg&mode=white" 1400 # through a registered reference camera
#   query: view=NAME | cam=x,y,z&tgt=x,y,z&fov=  mode=white  time=dusk  glb=F&meta=F  hq=N (refined still, N passes)
python3 -I tools/compare.py frames/seg002_043.jpg RENDER.png OUT.jpg all # model edges over the photo + side by side
python3 -I tools/measure.py tri|ray|proj|cams ...   # metres through the registered cameras
python3 -I tools/register.py solve                   # landmark bundle adjustment (survey/landmarks*.json)
python3 -I tools/crop.py IMG x0 y0 x1 y1 OUT.jpg [scale] [grid]          # crop with original-pixel ticks
```
Python that reads `refs/cache` is started with `-I` (downloaded media are untrusted input).

## Coordinates
World, metres: **X** right along the street (seen from the street), **Y** into the lot, **Z** up. Origin: in plan the
front-left eave corner of the roof (above the garage's front-left corner); Z = 0 at the driveway by the garage doors.
Side fences at X ≈ −2.7 / +27.8 (assumed 100 ft apart: this sets the scale, `survey/frame.json`). glTF / three:
(x, z, −y). Photos' "left / right" always as seen from the street.

## How the geometry is recovered
1. `tools/sfm.py` — COLMAP SfM on the drone video frames (one vertical drone move in front of the house: frames
   `seg002_033..053` low, `seg141_031..049` high; f = 1888 px). `tools/sfm_frame.py` makes it upright (vertical
   vanishing points) and lot-aligned (roof points) = frame **S**; `survey/frame.json` maps S to world metres.
2. `tools/register.py` — hand-picked landmarks (`survey/landmarks*.json`, original pixels) + a small bundle
   adjustment register the other images (the top-down aerial `photos/p30…` first, then ground photos).
   `refs/cache/cams_S.json` = all cameras; `model/frame.py world_cams()` gives them in metres.
3. `tools/vggt_run.py` / `vggt_align.py` — a multi-view network (CPU) for rough cameras of every image (starting
   guesses, "where should this point appear") and, via `tools/dsm.py`, a calibrated height map of the lot from the
   aerial photo (±0.2–0.4 m: rear roofs, cabana, yard levels, trees).
4. `survey/<zone>.json` — the zone surveys (front, rear, roof, sides, cabana_pool, site, materials): every element
   with pixel boxes and, where registered images show it, world coordinates.
5. `model/` — `kit.py` (flat-shaded primitives, UVs in metres), `massing_kit.py` (measured roof planes, walls that
   rise to the roof above them), asset kits (`openings.py`, `fixtures.py`, `plants.py`, `pool.py`, `furniture.py`),
   `zones/*.py` (each `build() -> [Part]`), `build.py`.
6. Check: render through the registered cameras and overlay on the photos (`tools/compare.py`).

## Model (`model/zones/`)
- `house.py`: roofs = a UNION of overlapping rectangular blocks (`UPPER` 5:12 shingle from eaves at 7.2, `LOWER`
  standing seam ~21 deg from eaves at 4.0; `massing_kit.hip_roof`, gable ends, flat caps `z_cap`).  Blocks overlap deeply
  so that inner ends are buried and real valleys appear; two blocks that merely touch show a false V.  Walls are
  `openings.Facade`s listed in `GROUND` / `UPPER_WALLS` (a = LEFT end seen from outside; openings as (builder, x, z, ...)
  along the wall), `roof_details` adds seams, ridge / hip caps and gutters on the eaves that are not buried,
  `roof_equipment` the solar arrays, skylights and vents read from the aerial.  Side walls carry no openings: no
  photograph shows them.
- `site.py`: ground levels, driveway, walk, lawns (`flat()`; world-anchored UVs), the street wall (the street runs
  ~6 deg off the house front: `wall_y`), fences and gates, rear patio + pergola + furniture, pool terrace, cabana,
  planting, a plain backdrop (neighbour masses, trees).
- Datums: street -0.5, garage slab 0.36, front lawn 0.38, main floor / porch / rear patio 1.0, rear lawn 0.55 (laundry
  end) .. 0.95, pool coping 1.25, cabana terrace 1.55, lower eaves 4.0, upper floor 4.4, upper eaves 7.2.
- The SUN stands on the REAR side of the lot (`build.SUN` az 351 from +Y toward +X, el 32: the aerial's shadows fall
  toward the street), so the street front is in open shade in the daylight photographs.

## How the photographs are used (owner 2026-11-27: "be smart about how you use the real image")
1. Geometry: cameras + overlays (above).  `tools/fit_world.py` fits a photo's camera directly on model points
   (`survey/pairs_world.json` -> `survey/cams_world.json`, which override the SfM cameras): the rear photo p26 is
   fitted this way (rms 3 px) and its rays corrected the rear openings.
2. Materials: `model/swatch.py` cuts small clean patches (shingles, driveway pavers) out of the aerial, straightens them
   on their plane at true scale, divides the light gradient away, makes them tile and gives them the material's mean
   albedo; the viewer lays them over the model's UVs (`Materials.setSwatches`).  No seams, the scene's own light.
   The owner preferred this to whole-photo projection ("crop a small texture and then replicate").
3. Whole-photo projection (`web/viewer/photo.js`, `build.PROJECTORS`, `?photo=1`; `model/ortho.py` = an untested
   seamless top-down bake) is a TEST layer, off by default and not packaged: cast photographs leave gaps wherever the
   camera did not see the surface, and carry their own shadows.  The first published version used it and the owner
   pointed at the gaps.
All swatch / projector images are written to `out/` (git-ignored) and only travel in the private bundle.

## Viewer (`web/`)
`viewer/stage.js` (renderer, sun + shadows, photo-matched cameras, `meter()`: the exposure opens up by 1.5x when the
view looks at the shaded side, as the photographs of the street front do), `sky.js` (analytic sky in display colours +
its lighting copy), `picture.js` (refined stills: jittered passes, sun disc, shadowed sky-light samples), `materials.js`
(GLB materials replaced by NAME from the look modules `looks/*.js`; textures are procedural, plus the swatches).
Light is calibrated on the photos: neutral tone curve, sunlit white wall ~245, open shade ~180 (before `meter()`) —
tune materials against the photos under this light, not the light against materials.
`python3 web/package.py` -> `dist/` (git-ignored): the Artifact layout (page without html / head / body tags, vendored
three.js through an import map, the GLB as base64 text parts, swatches as JPEGs); publish `dist/index.html` with
`dist/ARTIFACT.json`'s file map (a private Artifact; `--photo-layer` adds the projector photographs).
Software GL renders the full scene in ~2 min a frame: use `&hide=plants,trees,backdrop` or `--zones house` for quick checks.
