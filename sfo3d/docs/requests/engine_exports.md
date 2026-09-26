# Requests from the three.js renderer port (live3.html), 24 Sep 2026

From: engine-port workflow (owner of `live3.html`, `js/three/**`, `vendor/**`, `tools/build3/**`, `tools/blender/**`,
`docs/research/engine_impl.md`). The new renderer runs the existing app **unchanged**: `live3.html`'s import map swaps
only `js/gl.js`, `js/renderer.js`, `js/scene.js` and `js/world/world.js` for three.js-backed stand-ins
(`js/three/compat/*`). Everything else (entry, app loop, traffic, physics, gates, UI, QA hooks, data) is imported as is.
That works today; the requests below keep it working while other workflows change those modules, and remove the few
places where the port has to replicate code.

## 1. Keep the renderer-facing surface of `js/live/app.js` stable (or tell us when it changes)

`js/three/renderer3.js` implements exactly what `app.js` uses of the old renderer and scene (read 24 Sep 2026):

| Object | Used by app.js |
|---|---|
| `Renderer` | `new Renderer(w, h, {msaa, shadowRes})`, `addProgram(name, vs, fs)`, `setupSky(env)` (synchronous; then `R.light.skyUp / skyHorizon / ground` are read and written), `extraCommon.uNight`, `progs.cloud`, `curCam`, `curRange`, `render(frame, cam, t, post)` returning `C` with `vpNear`, `pos`, `fov`, `present(w, h)`, `resize(w, h)` |
| `Scene` | `new Scene(R, world)`, `add(ac)`, `aircraft[]` (spliced directly), `staticLights[]` (functions returning sprite records), `gateSys`, `frame(t, camPos)`, `commit()` |
| `bakeGround(R, world, log, {aptRes, cityRes, sunOnly})` and `releaseAirportMap(world)` right after it | |
| `initGL(canvas)`, `gl.getExtension`, `gl.getParameter` | (25 Sep: the stand-in now answers `EXT_color_buffer_float` / anisotropy from a real probe, so the app's start-up check works again) |
| `post` passed to `render()` | `exposure` (day value; live3 derives its own night exposure, see §5.4), `sat`, `bloom`, `vignette`, `grain` |
| data read by the renderer directly | `world.details.masts` and `js/live/items.js MAST_H` (floodlight field, `js/three/flood.js`) |

If the real-time work adds renderer calls to `app.js` (for example new post settings or a new item type pushed to
`world.items`), please add them to this table or ping the engine workflow. Unknown `gl.*` calls are no-ops in the
stand-in, so nothing crashes, but the feature will be missing in live3.html.

**Better (optional):** split `app.js` into a renderer-independent controller (feeds, traffic, physics, UI glue, camera
views, `SFO.qa`) and a small renderer adapter. Then live3.html would not need the `js/renderer.js` / `js/scene.js`
swaps at all.

## 2. `js/live/signs.js`: export `locName` and the face list of `buildSigns`

`js/three/signs.js worldSignAtlasMap()` rebuilds the same face list as `buildSigns` (holds: mand, paint, loc; drs 1..12)
to get the atlas map, because `buildSigns` returns only `atlas: A.tex` and not `A.map`. It replicates `locName`
(signs.js line ~150, not exported). Please return `atlasMap: A.map` from `buildSigns` (one extra field), and export
`locName`. Then the replica can go.

## 3. Brand × model livery textures (`data/liveries/`): resolved, nothing required

Update 25 Sep 2026: the liveries workflow published `data/liveries/manifest.js` + `js/aircraft/liveries.js`, and
`LiveAircraft` (js/live/aircraft.js) now resolves the brand (js/live/lookup.js `resolveLivery`) and loads the texture
itself (`updateLiveryTexture()` -> `ac.livTex`). `js/three/aircraft.js` uses `ac.livTex` for the atlas draws (texture 0)
of the imported models, with the atlas alpha as painted cabin-window glass, exactly as `js/shaders/aircraft_real.js`
(uAtlas / uLivTex). The renderer's own manifest loader was removed. Please keep `updateLiveryTexture()`, `livTex` and
the draws' `atlas` flag (js/live/models.js) as they are, or tell us when they change.

Done for `docs/requests/liveries_windows.md` (25 Sep 2026): (1) neutral skins: `ac.livTex` with `ac._livNeutral` is drawn
like the model's atlas with the zone recolouring (`uLivTex = 0`); (2) freighters: `brandIsCargo(brand)` -> kind-1 glass
aft of the flight deck is shaded as a window plug in the top colour, no cabin light (ACR_FS `uNoCabin`). Checked in
`js/three/dev/envtest.html` (FDX 757). Observation for the liveries owner: with the FedEx livery the plugs come out as
purple dots on the white cabin band, because the top colour is the purple crown; plugs painted in the colour of the
surrounding skin (e.g. `uBelly` / the fuselage colour at the window line) would read closer to a real 757F. We will
follow whatever ACR_FS does. Please make `_livNeutral` a public field (e.g. `livNeutral`) when convenient; the three.js
path reads the underscore field today.

## 4. `js/live/gates.js`: nothing required

The bridges are drawn from `LiveGateSystem.items()` output (merged static mesh, per-frame mesh of the moving bridges
only, sign quads, GSE instances), so the rotunda / walkway / stow-pose changes requested in
`static_geometry_round1.md` appear in live3.html automatically. Keep `items()` returning
`{mesh, prog: 'obj' | 'sign' | 'objI'}` and `gateSys.sprites`, `gateSys.atlas.map`.

## 5. Review round 1 of the new renderer (25 Sep 2026): requests to other workflows

Fixed in `js/three/**` where the renderer could fix it; these need the owners of the files named.

### 5.1 `js/live/app.js` (real-time workflow): mark marker sprites; better, draw a generic airframe instead

`markerSprites()` (app.js ~269) pushes `{p, c, i: 120, s: 1.4}` for every track without a known type, including ground
aircraft 2 m above the apron. The reviewer found one 17 m from the camera drawn as a 110 px saturated disk in daylight.
live3.html now clamps every sprite to at most 12 px radius, caps its halo and fades markers out between 150 m and 60 m
from the camera. It recognises markers by `marker: true` or, until that flag exists, by "no `dir` and `s >= 0.6`"
(only the markers match today). Please (a) add `marker: true` to the marker records, and (b) better: for ground tracks
with an unknown or unsupported type, create a `LiveAircraft` with a generic procedural narrow-body airframe
(js/aircraft/fleet.js already builds procedural airframes; the 'generic business-jet' path in `modelNote` shows the
pattern) instead of `'marker'`, so an unknown aircraft on a stand is a solid body with shadows, not a light.

### 5.2 `js/live/app.js`: a fatal-error hook, and a visible message after load

`ui.fail(msg)` writes into the loading overlay, which `ui.ready()` removes, so after load the app's own
`webglcontextlost` handler shows nothing (and `body.lost` has no rule in live.css). live3.html dispatches a synthetic
`webglcontextlost` on WebGPU device loss (so the app stops its loop) and shows its own overlay (`#r3fatal`). Please add
`R.onFatal = (html) => ui.fail(html)` (or an equivalent) and make `ui.fail` work after load; the renderer will call it
for init failures and device loss instead of its own overlay.

### 5.3 `js/live/app.js`: dynamic resolution

Each change of the render scale reallocates every post-processing target and restarts TRAA's history. live3.html now
quantises the requested size to 1 / 0.85 / 0.72 / 0.6 / 0.5 / 0.4 of the canvas and applies a new step at most
every 8 s. The controller itself would do better with hysteresis and a GPU-time signal: its EMA measures the CPU time of
`tick()` (engine.md §2 verifier note), so a GPU-bound phone may never trip it.

### 5.4 `js/live/app.js`: night exposure

live3.html no longer uses the fixed night term of `applyEnv` (2.4). It keys the exposure on the total horizontal
illuminance (sun + sky from the sky model, + the apron floods converted to the sky model's units, `renderer3.js
LAMP_M`): lit concrete is placed at the display key whenever that gives more exposure than the app's day value (the
app's `post.exposure` with its night term removed, x 1.2). The app's night floor (`R.light` floors in `applyEnv`) is
read as lamp units and scaled the same way. Nothing to change; please keep `post.exposure` = the app's exposure and
the floor as `max(sky, floor)` on `R.light`, or tell us when they change.

### 5.5 Liveries workflow: United 737 MAX 9 title on the window line

Reviewer (25 Sep, render of `data/liveries/UAL/b738@b39m-hi.webp`): the window cut-outs ran through the 'UNITED'
letters. In the texture re-baked at 17:16 UTC the holes no longer cross the letters, but the title still sits on the
window line with the forward cabin windows omitted under it. United's 2019 livery puts the larger title above the
window belt; painted titles never cover passenger windows and windows never disappear under them. Please move the
titles off the window belt (check against United's livery drawing / photos), and add a bake-time check that title
pixels never overlap the window alpha mask and that the window row is complete.

### 5.6 Stands / airfield data: floodlight masts

The apron floodlight field (`js/three/flood.js`) uses the observed mast positions, but the mast height (27 m,
`items.js MAST_H`) and the luminaire aiming are inferred, and the level is the ICAO design value (20 lux on stands). If
SFO's apron lighting plan (mast heights, luminaire count / wattage / aiming) can be obtained, `details.mastMeta` would be
the place for it; the field follows automatically.
