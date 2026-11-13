# Phase 2, package P2: renderer and airport world

Written 2026-11-13 (resumed run; the interrupted run's checkpoint 0b0a4bb held the renderer fork, `site.js`, `grid.js`,
the first world build and the dev page; this run re-verified all of it, measured the paint and the light units on
NAIP 2024, corrected the markings, added the VASI / PAPI units, the unlit wind cones and the regional backdrop, and
wrote this report).

Labels as in the fork map: **[obs]** seen in a source or measured here, **[inf]** a rule, a default or a choice.

## 1. What exists and how to run it

| File | Role |
|---|---|
| `js/gl.js`, `js/math.js`, `js/geom.js`, `js/shaders/{common,env,objects,post,sprites}.js` | sfo3d renderer core, forked unchanged except the fork headers and the `uGroundRef` contact AO of `objects.js` |
| `js/renderer.js` | sfo3d renderer; default shadow cascade ends [60, 400, 2500] m for GA aircraft [inf]; render-item field `groundRef` |
| `js/scene.js` | `Scene` with generic drawables (`add` / `remove`), no `js/aircraft/**` import (fork map 2.5, risk R8) |
| `js/shaders/ground.js` | HWD ground: NAIP imagery off the pavement, procedural asphalt on it, the two runways analytic from the NASR ends |
| `js/world/site.js` | `buildSite(airport)`: the Node-pure site model of fork map 2.4 |
| `js/world/grid.js` | HWD runway-aligned grid (s along 10 -> 28, 119.857 deg true) |
| `js/world/earcut.js`, `js/world/textures.js` | forked unchanged |
| `js/world/tex/*` | NAIP textures: 0.6 m HWD mosaic downsampled (`make_naip_tex.py`), 24 km regional resampling (`fetch_region.py`) |
| `js/world/fixtures_naip.{json,js}` | VASI / PAPI unit positions measured on NAIP 2024 (`dev/measure_fixtures.py`) |
| `js/live/world.js` | `buildHwdWorld(R, airport, {site, quality, taxigraph})` + `releaseAirportMap` (fork map 2.4) |
| `js/live/airport.js` | pavement map (canvas, HWD grid, RG8) and the NAIP / regional texture loaders + affine fits |
| `js/live/markings.js` | all paint as decal geometry: runway markings, taxiway centrelines, hold markings, tie-down tees |
| `js/live/buildings.js` | 52 extruded footprints (34 hangars, tower, terminal, 14 other OSM buildings, fire station in 2 parts) |
| `js/live/lights.js` | windsock, 5 unlit wind cones, segmented circle, VASI / PAPI units with direction-dependent light sprites, beacon |
| `js/env/**` | sfo3d environment (sun, Moon, METAR, sky, fog, clouds, photocells), station KHWD; `render_env.js` = the env -> renderer glue of fork map 2.6 |
| `dev/world.html`, `dev/world.js` | dev page: the world only, named views, orbit / pinch camera, `window.HWDW.shot(view)` |
| `dev/shoot.mjs` | headless renders: `node dev/shoot.mjs [views] [--phone|--desktop] [--ground=procedural] [--t=ISO] [--prefix=]` |
| `dev/paint_dump.mjs`, `dev/naip_compare.py`, `dev/measure_paint.py`, `dev/measure_fixtures.py` | checks against NAIP 2024 (sections 4, 5) |

Run: `node dev/shoot.mjs` (from `hwd3d/`) writes `out/phase2/world_<view>_{desktop,phone}.png`; a browser can open
`dev/world.html` through any static server rooted at `hwd3d/` (`?view=`, `?ground=procedural`, `?q=low`, `?t=<ISO UTC>`,
`?metar=<raw>`). Named views: overview, thr10R, thr28L, green, west, tower, the approach views app28L / app10R / app10L /
app28R, telephoto light-test views zoom28L(_low/_high) / zoom10L(_low) / zoom10R, and top-down views top_*.

**Contract checks (run here).** `buildSite` in Node (no DOM): 3,580 x 3,000 raster at 0.5 m, 1,790 x 1,500 building
raster, built in 140 ms; it returns `rect, groundY, paved, surface, runwayAt, apronAt, building, buildingAt, hangars,
anchors {tower, aprons, windsock, thresholds}, stats` (plus `buildings`, `runways`, `aprons`, `rasters`). Every VASI /
PAPI unit and wind cone lies on `surface = 'grass'`; no building vertex lies on a runway or taxiway. `buildHwdWorld`
returns `items, site, towerPos, towerEye, textures, groundU, waterU (null), staticSprites(t), stats` and also `ready`,
`setWind`, `setGroundMode`, `lightEnv`, `inventory`; it registers the programs `ground, decal, obj, objI, paint, mark`.

**Sizes (measured on the dev page).** High tier: terrain 166,044 triangles in 156 culled chunks (10 m cells inside the
aerodrome, x1.1 growth to 40 km), pavement map 3,994 x 2,427 at 0.5 m, paint 8,062 triangles, buildings 910 triangles,
world build ~0.6 s; textures NAIP 3,186 x 2,711 (1.2 m) + region 3,000 x 3,000 (8 m). Low (phone) tier: terrain 126,720
triangles, map 1,997 x 1,214 at 1 m, NAIP 1,593 x 1,355 (2.4 m), region 1,500 x 1,500 (16 m). Affine world -> texture fit
residuals: 0.007 m (HWD mosaic), 0.28 m (24 km region).

## 2. Sources per element

| Element | Geometry source | src | Dimensions / look |
|---|---|---|---|
| Ground height | FAA NASR runway end / displaced-threshold elevations, linear along each runway (`geo.js rwySurfaceY`); elsewhere an inverse-square blend of the two runway profiles | obs at the 6 NASR points, inf between | runway cross-section flat [inf]; no 3DEP yet |
| Runway pavement | NASR end coordinates and widths (analytic rectangles in the shader) | obs | NAIP edge stripes within 0.12 m (Phase 1) |
| Taxiways / taxilanes | OSM centrelines (4 ways moved onto NAIP paint in Phase 1) with the Phase 1 widths | obs line, width obs on 6 ways, inf (AC 150/5300-13B defaults) on the rest | closed ways drawn weathered |
| Aprons, helipads | OSM polygons | obs | |
| Ground off the pavement | USDA NAIP 2024 (0.6 m mosaic at 1.2 / 2.4 m; regional 8 / 16 m) | obs (imagery) | section 3 |
| Runway markings | AC 150/5340-1M Chg 1 layout, checked against NAIP 2024 and corrected where the paint differs | inf (AC) / obs (measured) | section 4 |
| Taxiway centrelines | OSM centrelines, cut at the runway edges and at the hold markings | obs line | 6 in yellow (AC 4.2.5.1 minimum) [inf width] |
| Holding position markings (18) | Phase 1 holds: 16 bars measured on NAIP, 2 OSM nodes | obs position, direction obs 16 / inf 2 | Pattern A, 4 x 12 in lines, 3 ft dashes (AC 3.3.4.1, Fig. A-13; 12 in because HWD has an operating ATCT) |
| Green Ramp tie-down tees (66) | Phase 1 parking spots whose tee was seen on NAIP | obs | 6.0 / 4.8 m, 0.3 m line [inf width] |
| Hangars (34), other buildings (16) | OSM footprints | obs | heights [inf] except the tower (section 6) |
| Fire station | footprint read by eye on NAIP 2024 at the AL-5015 FIRE STATION block (the OSM node is 45 m off) | inf footprint | 7.0 / 4.0 m [inf]; overlay `out/phase2/cmp_fire.png` matches the roof |
| Windsock (lit), segmented circle | OSM node; NASR flags; NAIP | obs position | sock 12 ft, mast 5.5 m, circle 31.5 m (by eye; NAIP reads ~33 m) [inf] |
| Unlit wind cones (5) | AL-5015 "Wind Cone, unlit" symbols with a NAIP object at each (Phase 1 cross-check #7; re-checked here on 0.1 m resamplings) | obs position, identity from the chart symbol | 8 ft sock, 4.3 m mast [inf] |
| VASI 10R (V4R), 28L (V4L); PAPI 10L, 28R (P4L) | NAIP 2024 measurement (section 5); type, side, angle, TCH from NASR / CS | obs | unit boxes [inf]; light colour by viewing angle |
| Beacon (WG) | on the tower | inf (Phase 1 data) | 24 flashes / min [inf] |
| Sun, Moon, sky, fog, clouds | sfo3d env (Meeus ephemeris at the HWD ARP, METAR decoder, EnvState) | obs (ephemeris, METAR) / inf (sfo3d rules) | KHWD routine minute 54 [verify] |

## 3. Ground: NAIP imagery or procedural grass (rendered both ways)

Both were rendered on the same views (`out/phase2/world_*` = NAIP, `out/phase2/proc_*` = procedural, desktop 1280 x 720).

- **Procedural** (sfo3d's dry-grass shader): a uniform sandy plain. It has no city, no Bay, no roads; and the paved areas
  that OSM does not map (the roads and lots around the tower, the concrete pads at the Green Ramp edge, the 28L run-up
  shoulders) become grass, which is wrong.
- **NAIP 2024**: the field, the city of Hayward, the hills and the Bay are where they are; unmapped pavement shows as
  pavement. From the approach and overview heights it is clearly better.
- Its weakness is the near field: a 1.2 m texel (2.4 m on phones) covers 20-30 px at the tower cab (13.5 m eye height),
  so the ground just below the tower is soft. Two measures soften this, and neither invents content. First, vegetated
  imagery near the camera is drawn from a ~5 m low-pass of the photo times the procedural grass's fine luminance
  texture. Second, all imagery gets that fine texture once a texel covers more than ~2 px. The colour always comes
  from the photograph. The tower view is still visibly soft at its bottom edge (known gap 9).

**Decision: NAIP by default, everywhere off the pavement.** The pavement itself stays procedural asphalt, because the
photo has painted marks and parked aircraft baked in. The procedural ground remains in two cases: while the textures
load, and on `setGroundMode('procedural')`.

**Regional backdrop (new).** The committed 0.6 m mosaic covers only 3.8 x 3.3 km, and beyond it the old shader drew a flat
border colour. That read as a brown desert in the overview and the approach views. `js/world/tex/fetch_region.py`
made **one** request to the same public-domain USDA NAIP image service that Phase 1 used. It asked for a 24 x 24 km
resampling of the 2024 flights at 8 m (3,000 x 3,000 px, 2.49 MB JPEG; a 16 m 0.71 MB level for phones):
- The service query lists 28 quads in the box, all flown 2024-05-20, and 9 overview rasters without a year.
- A first request restricted to `year_ts = 2024` returned an all-black image, because at 8 m the service reads its
  overviews. The second request also admits the overviews.
- One quad over the open Bay has no imagery (614,316 px). It is filled by push-pull interpolation of the surrounding
  water and recorded in `naip2024.json` (`nodata_filled_px`).
- The raw response went to a fresh directory in the session scratchpad; its sha256 and the request are in
  `js/world/tex/naip2024.json`.

## 4. Markings: AC 150/5340-1M checked, then measured on NAIP

The full AC (Consolidated Chg 1, `refs/cache/local/faa/150-5340-1M-Chg-1-Airport-Markings.pdf`) was re-read for Table 2-1,
Table 2-2, Table 2-4, paras 2.3-2.9, 3.3.4 and 4.2.3 / 4.2.5, and Figures A-1, A-2, A-6, A-7, A-8, A-10 and A-13 (rendered
to images and read). Paragraph numbers in the code were corrected: the characteristics are 2.4.5, 2.5.5, 2.7.5 and 2.8.5,
not 2.x.4. Dimensions used:

| Marking | AC source | Value |
|---|---|---|
| Edge stripes | 2.8.5 | 36 in (10R/28L, >= 100 ft wide), 18 in (10L/28R); full length incl. displaced areas; end at an aligned taxiway |
| Centreline | 2.4.5, Fig. A-1 | 120 ft stripes / 80 ft gaps, 36 in (precision) / 18 in (non-precision), first stripe 390 ft from the threshold, adjusted at the midpoint (>= 80 / >= 40 ft) |
| Threshold stripes | 2.5.3, 2.5.5, Table 2-2 | 12 (150 ft) / 6 (75 ft), 150 x 5.75 ft, 5.75 ft gaps, 11.5 ft central gap, 20 ft from the threshold |
| Designation | 2.3, Fig. A-1, A-6 | letter 210-270 ft, number 290-350 ft; 60 x 20 ft glyphs, 5 ft vertical / 10 ft horizontal strokes, "1" 7 ft wide, 15 ft numeral spacing |
| Aiming point | Table 2-1, 2.6.3, 2.6.5 | precision runways only (10L/28R: non-precision and < 4,200 ft -> none); 1,020 ft; 30 ft wide, 72 ft apart |
| Touchdown zone | Table 2-1, 2.7.3.1, 2.7.5 | 75 x 6 ft bars, 5 ft spaces; groups at 520 / 1,520 / 2,020 / 2,520 / 3,020 ft; 900 ft no-marking zone each side of the midpoint -> at HWD (4,192 ft between thresholds) only the 3-bar group |
| Threshold bar | 2.9.1.2-2.9.1.5 | 10 ft, outboard edge on the threshold (displaced thresholds 10R / 28L; 10L has an aligned taxiway) |
| Displaced-threshold arrows | 2.9.2, Fig. A-7 | arrowheads 45 x 15 ft, 3 ft stroke, tips 5 ft before the threshold, 4 at W/4 (150 ft); centreline arrows 80 ft tail 1.5 ft wide + 45 ft head, every 200 ft, last tip 80 ft before the threshold |
| Demarcation bar + yellow arrowheads | 2.9.2.4, 2.9.3, Fig. A-8 / A-10 | 3 ft yellow bar at the runway end (10R, 28L: displaced threshold behind an aligned taxiway); yellow arrowheads, 4 (150 ft) / 3 (75 ft, 10L) |
| Holding position | 3.3.4.1, Fig. A-13 | Pattern A, 4 lines + 3 spaces of 12 in, 3 ft dashes, a dash centred on the taxiway centreline |
| Taxiway centreline | 4.2.5.1, 4.2.3.2.1 | 6 in yellow, ends at the runway edge |

**Checked against NAIP 2024.** `dev/naip_compare.py` overlays the paint triangles (`dev/paint_dump.mjs`) on NAIP
resampled to the runway axes at 0.15 m (`out/phase2/cmp_rwy{10R,28L,10L,28R}_end.png`). `dev/measure_paint.py` profiles
the paint along the axes (`out/phase2/naip_paint_measure.json`). Matched within ~1-2 ft:
- the threshold bars;
- the 10R / 28L / 28R stripes;
- all designators (after the 10L shift below);
- the TDZ 3-bar groups, which are the only TDZ bars painted;
- the aiming-point positions and widths;
- the centreline stripes;
- the arrowhead rows;
- the demarcation bars and yellow arrowheads;
- the 10R centreline arrows (tip ~83 ft against the AC's 80);
- the edge stripes.

Four deviations from the AC figures were measured and are now drawn as painted (`END_PAINT_OBS` in `markings.js`, src obs):

| End | AC | NAIP 2024 (measured) | Drawn |
|---|---|---|---|
| 10R, 28L aiming point | 100 ft long (2.6.5: 4,192 ft between thresholds < 4,200) | white runs 1,018.9-1,169.5 ft and 1,020.1-1,171.6 ft | 150 ft |
| 10L threshold stripes | from 20 ft | white run 27.9-178.1 ft (the superseded 30-ft practice that 2.5.3 mentions) | from 30 ft; designation and first centreline stripe +10 ft |
| 28L displaced-area arrows | last tip 80 ft before the threshold | head runs end ~72 ft before it; centroid comparison with 10R gives ~13 ft nearer | last tip 67 ft before the threshold, 200 ft pitch |
| 28R edge stripes | full length | start with the threshold stripes (a taxiway crosses the end) | from 20 ft past the end |

**Not drawn (seen on NAIP, geometry not measured):**
- the taxiway lead-on / lead-off lines that AC 4.2.3.3 curves onto the runways;
- the non-movement-area boundary markings (yellow solid + dashed) at several apron edges;
- the painted "H" circle and arcs at the north edge of the Green Ramp;
- the apron lead-in lines that OSM lacks.

No continuous taxiway edge lines were seen on the main taxiways (spot check of A, B, C and Z), so none are drawn. Hot
spots are chart symbols, not paint, and are not drawn.

## 5. Light units and markers measured on NAIP 2024

FAA NASR gives each VGSI's type, side, angle and TCH but no position. On NAIP 2024 the units are visible:
- VASI boxes as red-lens blobs with shadows on concrete pads;
- PAPI units as a row of 4 squares or bright tops on a pad.

The search windows were found by eye on 0.3 m strips beside each runway (`dev/measure_fixtures.py`, check crops
`out/phase2/fix_*.png`). Inside each window the units are measured as follows:
- VASI: top-hat on redness, blob centroids;
- 10L PAPI: brightness-profile maxima on the pad axis;
- 28R PAPI: bright-dot blobs, kept at least 5 m apart.

Along is measured from the end's threshold; across from the centreline, + = right of a pilot landing on that end.

| System (NASR code, angle, TCH) | Units: along m, across m | Notes |
|---|---|---|
| VASI 10R (V4R, 3.0 deg, 25 ft) | downwind bar 35.5 m, upwind 248.8 m; boxes at +38.9 / +42.9 m | bars 213 m = 700 ft apart; right side, as V4**R** says |
| VASI 28L (V4L, 4.0 deg, 35 ft) | downwind 91.7 m, upwind 244.2 m; boxes at -38.1 / -42.9 m | 152.5 m = 500 ft apart; left side |
| PAPI 10L (P4L, 3.0 deg, 29 ft) | 185.4 m; units -21.4, -28.3, -33.8, -40.4 m | inboard unit ~10 m (33 ft) from the edge, pitch ~6.3 m (+-1 m: the squares merge at 0.6 m) |
| PAPI 28R (P4L, 3.0 deg, 44 ft) | 279.3 m; units -26.5, -35.6, -44.8, -53.8 m | inboard 15.1 m (50 ft) from the edge, pitch 9.1 m (30 ft); the 4th unit is on a separate small pad |

The measured layout confirms the NASR code letters (boxes and side), which the Phase 1 data had decoded "from memory".

**Light model** (simple, Phase 4 replaces it):
- Direction-dependent sprites in a ±15° beam toward the approach.
- PAPI aiming angles GPA +30′ / +10′ / −10′ / −30′ from the unit nearest the runway outward (FAA JO 6850.2C
  Table 5-2, as verified in sfo3d `docs/research/airfield_lighting.md` V6). The white / red transition uses
  `photometry.js papiWhite` (AC 150/5345-28H 3.2.1).
- VASI bar transitions at GPA −0.25° (downwind) and +0.25° (upwind) [inf]. The on-path behaviour, near bar white and far
  bar red, follows FAA AIM 2-1-2 from memory [verify].
- Schedule from NASR LGT_SKED: VASI on while the tower is open (0700-2100 local) and from sunset to sunrise; PAPI off
  when the tower is closed.
- Intensities 12,000 cd by day and 2,400 cd at night, with a day display gain of 8 [all inf, tuned by eye].
- Checked on renders:
  - on the 28L 4.0° path at night the VASI shows near bar white, far bar red (`lightsN_zoom28L`);
  - 0.8° low it shows both bars red (`lights_zoom28L_low`);
  - on the 10L 3.0° path the PAPI shows 2 red (inboard) + 2 white (`lights_zoom10L`).

**Not placed**, with the reason:
- MIRL edge lights: a periodic-dot search 1.8-6 m outside all four runway edges found no 200-ft pattern; the fixtures are
  below NAIP's resolution.
- REIL 10R / 28L: candidate objects near the 28L threshold, ~13 m before it and 12-17 m from the edges, are not certain.
- Taxiway edge lights or reflectors.
- The segmented circle's L-shaped traffic-pattern indicators: seen on NAIP NW and SE of the circle, shape not measured.

**Renderer note for P4:** blended items (paint and light sprites) are drawn in the near range only (`cam.split`). Keep
the split at 2.5 km or more where the approach lights matter; the dev page uses 3 km for eye views.

## 6. Buildings

- **Footprints:** OSM (obs) for 50 buildings; the fire station from NAIP (inf). They match the NAIP roof edges in the
  overlays (`out/phase2/cmp_west_hangars.png`, `cmp_tower.png`, `cmp_fire.png`). Roof lean in NAIP is visible, and the
  footprints match the bases.
- **Heights:** only the tower's 15.85 m is sourced (OSM height). All others follow `site.js HEIGHT_RULES` [inf]:
  - T-hangar rows 4.5 m;
  - box hangars 6-12 m, scaled with the short side;
  - terminal 7.5 m;
  - other buildings 4.5 m;
  - fire station 7.0 / 4.0 m.
- **Tower eye:** top − 2.4 m [inf], 13.5 m above the ground.
- **Shapes [inf]:** low-pitch gable roofs on rectangular hangars, flat roofs elsewhere, and a dark glazing band on the
  tower. No doors and no detail (Phase 4).
- Phase 4 can calibrate the heights from the NAIP shadow lengths against the tower.

## 7. Environment

- **Forked from sfo3d** (`js/env/**`):
  - the sun and Moon from the Meeus ephemeris at the HWD ARP;
  - the station-agnostic METAR decoder, with the KHWD routine minute 54 [verify];
  - EnvState fog, clouds, wind and photocells;
  - the sky model.
- **`render_env.js applyEnvToRenderer`** does sfo3d's `applyEnv` work at the HWD field elevation: sky, fog, the low cloud
  slab, night ambient floors and the exposure ramp.
- It also turns the windsock and the 5 wind cones by the METAR wind and sets `world.lightEnv` for the light schedule.
- There is no TAF for KHWD (aviationweather.gov returns none).

## 8. Renders (headless Chromium, SwiftShader)

- **Named views** at 1280 x 720 and on a 390 x 844 phone viewport (DPR 2, rendered at scale 1.5 = 585 x 1,266, low tier):
  `out/phase2/world_{overview,thr10R,thr28L,green,west,tower}_{desktop,phone}.png`.
  - On portrait screens the dev camera moves orbit views back and widens eye views.
  - The phone overview looks along the runways (west, toward the Bay and OAK).
- **Light tests:** `out/phase2/lights_*` (day) and `lightsN_*` (2026-11-14 04:30Z, 20:30 local, tower open).
- **Procedural comparison:** `out/phase2/proc_*`.
- **NAIP overlays and measurements:** `out/phase2/cmp_*`, `fix_*`, `naip_paint_measure.json`.
- All were looked at.
- **Fixed after looking:**
  - procedural "patch repair" rectangles on the asphalt, which are not in any source, were removed;
  - the full-length dark rubber band on the runways was narrowed to the faint ~3-4 m deposits NAIP shows;
  - the flat brown world beyond the HWD mosaic was replaced by the regional NAIP backdrop;
  - the aiming points, 10L stripes and 28L arrows (section 4);
  - phone framing.

## 9. Known gaps and inferred values

1. No elevation source off the runways (USGS 3DEP not fetched). The field surface is a blend of the NASR runway
   profiles, and the hills east of Hayward are flat imagery.
2. Building heights, roof shapes and wall colours are inferred, except the tower height. There are no doors.
3. MIRL, REIL, taxiway lights and signs are not placed (no position source). The night field shows only the VASI / PAPI,
   the beacon and the windsock light.
4. The VASI aiming angles, all light intensities and the unit sizes are inferred. The windsock and cone sizes are
   remembered, not re-read (AC 150/5345-27 [verify]).
5. Lead-on / lead-off lines, non-movement boundary markings, the Green Ramp H circle and apron lead-in lines are not
   drawn (section 4).
6. Glyph stroke details of "2" and "R" follow Fig. A-6, which is not fully dimensioned. They match NAIP in position, not
   in every stroke.
7. The taxiway centreline width is the AC minimum of 6 in. NAIP cannot tell 6 from 12 in.
8. The beacon is on the tower roof [inf, Phase 1].
9. Near-field imagery is soft at the tower cab (section 3).
10. The regional backdrop's one Bay quad is interpolated water. The image service's resampling of the 2024 flights and
    its overviews is not the 0.6 m originals.
11. Light sprites follow the renderer's near-pass-only rule (section 5).
12. The NAIP credit for the regional texture is the same as for the mosaic: "Imagery: USDA NAIP". `docs/ATTRIBUTION.md`
    already lists NAIP. The orchestrator should confirm that the new file `js/world/tex/naip2024_region_*.jpg` is
    covered by it.
