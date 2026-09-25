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
| `initGL(canvas)`, `gl.getExtension`, `gl.getParameter` | |

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
