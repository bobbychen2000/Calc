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

## 3. Brand × model livery textures (`data/liveries/`)

`js/three/aircraft.js LiveryLibrary` loads `data/liveries/manifest.json` when it exists. Format assumed until the
livery workflow publishes one:

```json
{ "entries": [ { "brand": "UAL", "model": "b738", "file": "UAL/b738.png" } ] }
```

- `brand`: ICAO airline code of the brand painted on the airframe (not the callsign's operator, docs/research/liveries.md §2);
- `model`: the `.sfom` model key (`js/live/aircraft.js MODEL_BASE` keys);
- `file`: texture laid out on that model's UV set 0 (the first texture of the `.sfom`), sRGB, v down (no flip).

The brand is read from the track: `tr.brand`, `tr.livery.brand`, `tr.info.brand`, else `tr.cs.airline.icao`. When
`js/live/lookup.js` gains the registration → brand lookup, please put its result on `tr.brand` (and `tr.brandSrc`
'obs'/'inf'); the renderer picks it up without further changes. If the manifest uses another shape, tell us and we
adapt `LiveryLibrary.load`.

## 4. `js/live/gates.js`: nothing required

The bridges are drawn from `LiveGateSystem.items()` output (merged static mesh, per-frame mesh of the moving bridges
only, sign quads, GSE instances), so the rotunda / walkway / stow-pose changes requested in
`static_geometry_round1.md` appear in live3.html automatically. Keep `items()` returning
`{mesh, prog: 'obj' | 'sign' | 'objI'}` and `gateSys.sprites`, `gateSys.atlas.map`.
